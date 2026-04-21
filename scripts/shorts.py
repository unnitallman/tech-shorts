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
    print(f"[publish] slug={args.slug} (not yet implemented)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print("[status] (not yet implemented)")
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
