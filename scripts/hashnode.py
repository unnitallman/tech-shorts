"""Hashnode GraphQL client — drafts, posts, image upload."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


API_URL = "https://gql.hashnode.com/"


class HashnodeError(RuntimeError):
    pass


class Hashnode:
    def __init__(self, token: str | None = None, publication_id: str | None = None) -> None:
        self.token = token or os.environ["HASHNODE_API_TOKEN"]
        self.publication_id = publication_id or os.environ["HASHNODE_PUBLICATION_ID"]
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.token,
            "Content-Type": "application/json",
        })

    # ---------- GraphQL transport ----------

    def _gql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        r = self.session.post(API_URL, json={"query": query, "variables": variables}, timeout=30)
        r.raise_for_status()
        body = r.json()
        if "errors" in body:
            raise HashnodeError(body["errors"])
        return body["data"]

    # ---------- Drafts ----------

    def create_draft(self, *, title: str, content_markdown: str, tags: list[str], series_slug: str | None, cover_image_url: str | None) -> str:
        query = """
        mutation CreateDraft($input: CreateDraftInput!) {
          createDraft(input: $input) { draft { id } }
        }
        """
        input_: dict[str, Any] = {
            "publicationId": self.publication_id,
            "title": title,
            "contentMarkdown": content_markdown,
            "tags": [{"slug": t, "name": t} for t in tags],
        }
        if cover_image_url:
            input_["coverImageOptions"] = {"coverImageURL": cover_image_url}
        if series_slug:
            input_["seriesId"] = self._series_id(series_slug)
        data = self._gql(query, {"input": input_})
        return data["createDraft"]["draft"]["id"]

    def update_draft(self, *, draft_id: str, title: str, content_markdown: str, tags: list[str], cover_image_url: str | None) -> None:
        query = """
        mutation UpdateDraft($input: UpdateDraftInput!) {
          updateDraft(input: $input) { draft { id } }
        }
        """
        input_: dict[str, Any] = {
            "id": draft_id,
            "title": title,
            "contentMarkdown": content_markdown,
            "tags": [{"slug": t, "name": t} for t in tags],
        }
        if cover_image_url:
            input_["coverImageOptions"] = {"coverImageURL": cover_image_url}
        self._gql(query, {"input": input_})

    def publish_draft(self, draft_id: str) -> dict[str, str]:
        """Promote a draft to a public post. Returns {post_id, url}."""
        query = """
        mutation PublishDraft($input: PublishDraftInput!) {
          publishDraft(input: $input) { post { id url } }
        }
        """
        data = self._gql(query, {"input": {"draftId": draft_id}})
        post = data["publishDraft"]["post"]
        return {"post_id": post["id"], "url": post["url"]}

    # ---------- Live posts ----------

    def update_post(self, *, post_id: str, title: str, content_markdown: str, tags: list[str], cover_image_url: str | None) -> dict[str, str]:
        query = """
        mutation UpdatePost($input: UpdatePostInput!) {
          updatePost(input: $input) { post { id url } }
        }
        """
        input_: dict[str, Any] = {
            "id": post_id,
            "title": title,
            "contentMarkdown": content_markdown,
            "tags": [{"slug": t, "name": t} for t in tags],
        }
        if cover_image_url:
            input_["coverImageOptions"] = {"coverImageURL": cover_image_url}
        data = self._gql(query, {"input": input_})
        post = data["updatePost"]["post"]
        return {"post_id": post["id"], "url": post["url"]}

    # ---------- Helpers ----------

    def _series_id(self, slug: str) -> str:
        query = """
        query SeriesBySlug($host: String!, $slug: String!) {
          publication(host: $host) {
            series(slug: $slug) { id }
          }
        }
        """
        # host inferred from publication; requires env — keep simple for v1
        raise HashnodeError("Series support not implemented in v1 — set series: null in frontmatter.")

    # ---------- Image upload ----------

    def upload_image(self, path: Path) -> str:
        """Upload a local image to Hashnode's CDN, return the public URL."""
        # Hashnode provides a signed-URL flow:
        # 1) mutation generateUploadURL(input) → signed url
        # 2) PUT the file bytes to that url
        # 3) the returned "url" (from step 1) is the public CDN URL once uploaded
        query = """
        mutation GenerateUploadURL($input: GenerateUploadURLInput!) {
          generateUploadURL(input: $input) { url signedURL }
        }
        """
        variables = {"input": {"filename": path.name, "contentType": _content_type_for(path)}}
        data = self._gql(query, variables)
        signed = data["generateUploadURL"]["signedURL"]
        public_url = data["generateUploadURL"]["url"]
        with open(path, "rb") as f:
            r = requests.put(signed, data=f.read(), headers={"Content-Type": _content_type_for(path)}, timeout=60)
            r.raise_for_status()
        return public_url


def _content_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
