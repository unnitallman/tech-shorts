from pathlib import Path

from scripts.post import load_post, content_hash, extract_local_images


FIXTURE = Path(__file__).parent / "fixtures" / "sample-post.md"


def test_load_post_parses_frontmatter():
    post = load_post(FIXTURE)
    assert post.metadata["slug"] == "sample-post"
    assert post.metadata["published"] is False
    assert post.metadata["tags"] == ["test", "fixture"]
    assert "This is the body" in post.content


def test_content_hash_is_deterministic():
    post = load_post(FIXTURE)
    h1 = content_hash(post)
    h2 = content_hash(post)
    assert h1 == h2
    assert h1.startswith("sha256:")
    assert len(h1) == len("sha256:") + 64


def test_content_hash_changes_with_content():
    post = load_post(FIXTURE)
    h_before = content_hash(post)
    post.content = post.content + "\nnew line"
    h_after = content_hash(post)
    assert h_before != h_after


def test_extract_local_images_returns_relative_paths():
    post = load_post(FIXTURE)
    imgs = extract_local_images(post)
    assert "images/sample-post/diagram.png" in imgs
    assert not any(p.startswith("http") for p in imgs)


def test_extract_local_images_includes_cover():
    post = load_post(FIXTURE)
    imgs = extract_local_images(post)
    assert "images/sample-post/cover.png" in imgs


def test_rewrite_images_for_api_replaces_local_paths():
    from scripts.post import rewrite_images_for_api
    from pathlib import Path

    body = "![a](images/x/a.png) ![b](https://cdn/b.png)"
    mapping = {"images/x/a.png": "https://cdn.hashnode.com/uploaded-a.png"}
    out = rewrite_images_for_api(body, mapping)
    assert "https://cdn.hashnode.com/uploaded-a.png" in out
    assert "https://cdn/b.png" in out
    assert "images/x/a.png" not in out
