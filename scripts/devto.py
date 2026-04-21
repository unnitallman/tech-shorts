"""dev.to REST client — create and update articles."""

from __future__ import annotations

import os
from typing import Any

import requests


API_BASE = "https://dev.to/api"


class DevtoError(RuntimeError):
    pass


class Devto:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ["DEVTO_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({
            "api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
        })

    def create_article(self, *, title: str, body_markdown: str, tags: list[str], canonical_url: str, cover_image_url: str | None, published: bool = True) -> dict[str, Any]:
        payload = {
            "article": {
                "title": title,
                "body_markdown": body_markdown,
                "tags": tags[:4],  # dev.to max 4 tags
                "canonical_url": canonical_url,
                "published": published,
            }
        }
        if cover_image_url:
            payload["article"]["main_image"] = cover_image_url
        r = self.session.post(f"{API_BASE}/articles", json=payload, timeout=30)
        if r.status_code >= 400:
            raise DevtoError(f"{r.status_code} {r.text}")
        data = r.json()
        return {"post_id": str(data["id"]), "url": data["url"]}

    def update_article(self, *, post_id: str, title: str, body_markdown: str, tags: list[str], canonical_url: str, cover_image_url: str | None) -> dict[str, Any]:
        payload = {
            "article": {
                "title": title,
                "body_markdown": body_markdown,
                "tags": tags[:4],
                "canonical_url": canonical_url,
            }
        }
        if cover_image_url:
            payload["article"]["main_image"] = cover_image_url
        r = self.session.put(f"{API_BASE}/articles/{post_id}", json=payload, timeout=30)
        if r.status_code >= 400:
            raise DevtoError(f"{r.status_code} {r.text}")
        data = r.json()
        return {"post_id": str(data["id"]), "url": data["url"]}
