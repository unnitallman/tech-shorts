import json
import argparse
from pathlib import Path

from scripts.shorts import cmd_status


def test_status_prints_each_post_with_state(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "posts").mkdir()
    (tmp_path / ".state").mkdir()

    # Post 1: published on both
    (tmp_path / "posts" / "2026-04-21-foo.md").write_text(
        "---\ntitle: Foo\nslug: foo\ntags: []\npublished: true\n---\n\nbody\n"
    )
    # Post 2: draft only
    (tmp_path / "posts" / "2026-04-22-bar.md").write_text(
        "---\ntitle: Bar\nslug: bar\ntags: []\npublished: false\n---\n\nbody\n"
    )
    # State: foo is published on both, bar has hashnode draft only
    state = {
        "foo": {"hashnode": {"post_id": "h1"}, "devto": {"post_id": "d1"}, "content_hash": "sha256:x"},
        "bar": {"hashnode": {"draft_id": "hd1"}, "content_hash": "sha256:y"},
    }
    (tmp_path / ".state" / "published.json").write_text(json.dumps(state))

    rc = cmd_status(argparse.Namespace())
    assert rc == 0
    out = capsys.readouterr().out
    assert "foo" in out
    assert "bar" in out
    assert "published" in out
    assert "draft" in out
