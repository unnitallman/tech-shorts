#!/usr/bin/env python3
"""tech-shorts CLI — scaffold, publish, and status commands."""

import argparse
import sys


def cmd_new(args: argparse.Namespace) -> int:
    from datetime import date
    from pathlib import Path

    slug = args.slug
    today = date.today().isoformat()
    path = Path("posts") / f"{today}-{slug}.md"
    if path.exists():
        print(f"error: {path} already exists", file=sys.stderr)
        return 1

    template = (
        "---\n"
        f'title: "TODO replace with real title"\n'
        f"slug: {slug}\n"
        "tags: []\n"
        "cover_image: null\n"
        "canonical: hashnode\n"
        "series: null\n"
        "published: false\n"
        "---\n"
        "\n"
        "Write the post body here.\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template, encoding="utf-8")
    print(f"created {path}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    from datetime import datetime, timezone
    from pathlib import Path

    from scripts.post import (
        load_post,
        content_hash,
        extract_local_images,
        rewrite_images_for_api,
    )
    from scripts.state import State
    from scripts.hashnode import Hashnode
    from scripts.devto import Devto

    # 1. Locate the post file
    matches = list(Path("posts").glob(f"*{args.slug}.md"))
    if not matches:
        print(f"error: no post matching slug {args.slug!r} in posts/", file=sys.stderr)
        return 1
    if len(matches) > 1:
        print(f"error: multiple posts match slug {args.slug!r}: {matches}", file=sys.stderr)
        return 1
    post_path = matches[0]

    post = load_post(post_path)
    slug = post.metadata["slug"]
    title = post.metadata["title"]
    tags = post.metadata.get("tags", []) or []
    cover_local = post.metadata.get("cover_image")
    is_published = bool(post.metadata.get("published"))

    # 2. Content-hash based idempotency
    state = State(Path(".state/published.json"))
    current_state = state.get(slug)
    current_hash = content_hash(post)
    if (
        current_state.get("content_hash") == current_hash
        and current_state.get("hashnode", {}).get("post_id")
        and (not is_published or current_state.get("devto", {}).get("post_id"))
    ):
        print(f"[publish] {slug}: up to date (hash match)")
        return 0

    # 3. Upload images — one pass, both platforms reuse the Hashnode CDN URLs
    hn = Hashnode()
    local_images = extract_local_images(post)
    image_map: dict[str, str] = {}
    for rel_path in local_images:
        p = Path(rel_path)
        if not p.exists():
            print(f"warn: image {rel_path} not found; skipping upload", file=sys.stderr)
            continue
        cdn_url = hn.upload_image(p)
        image_map[rel_path] = cdn_url
        print(f"[publish] uploaded {rel_path} -> {cdn_url}")

    body_for_api = rewrite_images_for_api(post.content, image_map)
    cover_cdn = image_map.get(cover_local) if cover_local else None

    # 4. Hashnode branch
    hn_state = current_state.get("hashnode", {})
    hn_post_id = hn_state.get("post_id")
    hn_draft_id = hn_state.get("draft_id")
    hn_url: str | None = hn_state.get("url")

    if not is_published:
        # Draft path
        if hn_draft_id:
            hn.update_draft(
                draft_id=hn_draft_id, title=title,
                content_markdown=body_for_api, tags=tags, cover_image_url=cover_cdn,
            )
            print(f"[publish] updated Hashnode draft {hn_draft_id}")
        else:
            hn_draft_id = hn.create_draft(
                title=title, content_markdown=body_for_api, tags=tags,
                series_slug=post.metadata.get("series"), cover_image_url=cover_cdn,
            )
            print(f"[publish] created Hashnode draft {hn_draft_id}")
        new_hn_state = {"draft_id": hn_draft_id}
        if hn_post_id:
            new_hn_state["post_id"] = hn_post_id
        if hn_url:
            new_hn_state["url"] = hn_url
        state.update(slug, {
            "hashnode": new_hn_state,
            "content_hash": current_hash,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        state.save()
        print(f"[publish] done (draft). Preview in Hashnode dashboard.")
        return 0

    # Published=true path
    if hn_post_id:
        result = hn.update_post(
            post_id=hn_post_id, title=title, content_markdown=body_for_api,
            tags=tags, cover_image_url=cover_cdn,
        )
        print(f"[publish] updated Hashnode post {hn_post_id}")
    else:
        if not hn_draft_id:
            # Edge case: published=true on a never-published post.
            # Create a draft first, then publish.
            hn_draft_id = hn.create_draft(
                title=title, content_markdown=body_for_api, tags=tags,
                series_slug=post.metadata.get("series"), cover_image_url=cover_cdn,
            )
        result = hn.publish_draft(hn_draft_id)
        print(f"[publish] promoted Hashnode draft to post {result['post_id']}")
    hn_post_id = result["post_id"]
    hn_url = result["url"]

    # 5. dev.to cross-post (only reached when published=true)
    dt = Devto()
    devto_state = current_state.get("devto", {})
    devto_post_id = devto_state.get("post_id")
    try:
        if devto_post_id:
            dt_result = dt.update_article(
                post_id=devto_post_id, title=title,
                body_markdown=body_for_api, tags=tags,
                canonical_url=hn_url, cover_image_url=cover_cdn,
            )
            print(f"[publish] updated dev.to article {devto_post_id}")
        else:
            dt_result = dt.create_article(
                title=title, body_markdown=body_for_api,
                tags=tags, canonical_url=hn_url, cover_image_url=cover_cdn,
                published=True,
            )
            print(f"[publish] created dev.to article {dt_result['post_id']}")
        devto_final = dt_result
    except Exception as e:
        # Partial success: persist Hashnode state, let user retry dev.to later.
        print(f"error: dev.to cross-post failed: {e}", file=sys.stderr)
        state.update(slug, {
            "hashnode": {
                "draft_id": hn_draft_id,
                "post_id": hn_post_id,
                "url": hn_url,
            },
            "content_hash": current_hash,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        state.save()
        print(f"[publish] Hashnode succeeded: {hn_url}")
        print(f"[publish] re-run to retry dev.to.")
        return 2

    # 6. Full-success state write
    state.update(slug, {
        "hashnode": {
            "draft_id": hn_draft_id,
            "post_id": hn_post_id,
            "url": hn_url,
        },
        "devto": devto_final,
        "content_hash": current_hash,
        "published_at": current_state.get("published_at", datetime.now(timezone.utc).isoformat()),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    state.save()
    print(f"[publish] done: {hn_url}  |  {devto_final['url']}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from pathlib import Path

    from scripts.post import load_post
    from scripts.state import State

    posts_dir = Path("posts")
    if not posts_dir.exists():
        print("(no posts/ directory)")
        return 0

    state = State(Path(".state/published.json"))

    rows: list[tuple[str, str, str, str]] = []
    for p in sorted(posts_dir.glob("*.md")):
        post = load_post(p)
        slug = post.metadata["slug"]
        is_published = bool(post.metadata.get("published"))
        s = state.get(slug)
        hn = s.get("hashnode", {})
        dt = s.get("devto", {})

        if is_published and hn.get("post_id"):
            status = "published"
        elif hn.get("draft_id") or hn.get("post_id"):
            status = "draft"
        else:
            status = "unpublished"
        hn_mark = "✓" if hn.get("post_id") or hn.get("draft_id") else "—"
        dt_mark = "✓" if dt.get("post_id") else "—"
        rows.append((p.name, status, hn_mark, dt_mark))

    if not rows:
        print("(no posts)")
        return 0

    w = max(len(r[0]) for r in rows) + 2
    for name, status, hn_mark, dt_mark in rows:
        print(f"{name:<{w}} {status:<12} hashnode {hn_mark}  devto {dt_mark}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="shorts", description="tech-shorts publishing CLI")
    sub = p.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="scaffold a new post with frontmatter template")
    p_new.add_argument("slug", help="URL slug for the post")
    p_new.set_defaults(func=cmd_new)

    p_pub = sub.add_parser("publish", help="publish or update a post")
    p_pub.add_argument("slug", help="URL slug of the post to publish")
    p_pub.set_defaults(func=cmd_publish)

    p_st = sub.add_parser("status", help="list posts and publish state")
    p_st.set_defaults(func=cmd_status)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
