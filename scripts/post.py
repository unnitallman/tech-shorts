"""Pure helpers for loading posts, hashing content, and extracting images."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import frontmatter


IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def load_post(path: Path) -> frontmatter.Post:
    """Read a markdown post with YAML frontmatter."""
    with open(path, encoding="utf-8") as f:
        return frontmatter.load(f)


def content_hash(post: frontmatter.Post) -> str:
    """Deterministic sha256 over frontmatter + body (used for idempotency)."""
    canonical = frontmatter.dumps(post).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"sha256:{digest}"


def extract_local_images(post: frontmatter.Post) -> list[str]:
    """Collect all local (non-HTTP) image paths from cover_image + markdown body."""
    out: list[str] = []
    cover = post.metadata.get("cover_image")
    if cover and not cover.startswith(("http://", "https://")):
        out.append(cover)
    for match in IMAGE_MD_RE.finditer(post.content):
        url = match.group(1).strip()
        if not url.startswith(("http://", "https://")):
            out.append(url)
    # Preserve order, drop duplicates
    seen: set[str] = set()
    deduped: list[str] = []
    for p in out:
        if p not in seen:
            deduped.append(p)
            seen.add(p)
    return deduped


def rewrite_images_for_api(body: str, mapping: dict[str, str]) -> str:
    """Replace local image paths with uploaded CDN URLs. mapping: local_path -> cdn_url."""
    out = body
    for local_path, cdn_url in mapping.items():
        out = out.replace(local_path, cdn_url)
    return out
