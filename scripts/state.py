"""Persistent state for published posts — .state/published.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class State:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, dict[str, Any]] = {}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                self.data = json.load(f)

    def get(self, slug: str) -> dict[str, Any]:
        return self.data.get(slug, {})

    def set(self, slug: str, value: dict[str, Any]) -> None:
        self.data[slug] = value

    def update(self, slug: str, partial: dict[str, Any]) -> None:
        """Shallow-merge partial into the existing entry."""
        current = self.data.get(slug, {})
        current.update(partial)
        self.data[slug] = current

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, sort_keys=True)
            f.write("\n")
