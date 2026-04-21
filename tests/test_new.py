import os
from pathlib import Path

from scripts.shorts import cmd_new
import argparse


def test_new_creates_post_file_with_frontmatter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "posts").mkdir()

    args = argparse.Namespace(slug="my-first-post")
    rc = cmd_new(args)
    assert rc == 0

    files = list((tmp_path / "posts").glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "slug: my-first-post" in content
    assert "published: false" in content
    assert "tags: []" in content
    assert files[0].name.endswith("my-first-post.md")
