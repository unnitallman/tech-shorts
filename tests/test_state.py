import json
from pathlib import Path

import pytest

from scripts.state import State


def test_empty_state_file_is_ok(tmp_path):
    s = State(tmp_path / "state.json")
    assert s.get("nonexistent") == {}


def test_set_and_get_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    s = State(path)
    s.set("foo-slug", {"hashnode": {"post_id": "abc"}})
    s.save()

    # Reload from disk
    s2 = State(path)
    assert s2.get("foo-slug") == {"hashnode": {"post_id": "abc"}}


def test_save_writes_pretty_json(tmp_path):
    path = tmp_path / "state.json"
    s = State(path)
    s.set("x", {"a": 1})
    s.save()
    raw = path.read_text()
    assert "\n" in raw  # pretty-printed, not one-line
    parsed = json.loads(raw)
    assert parsed == {"x": {"a": 1}}


def test_update_merges_rather_than_replaces(tmp_path):
    s = State(tmp_path / "state.json")
    s.set("slug", {"hashnode": {"post_id": "abc"}})
    s.update("slug", {"devto": {"post_id": "xyz"}})
    assert s.get("slug") == {
        "hashnode": {"post_id": "abc"},
        "devto": {"post_id": "xyz"},
    }
