# tech-shorts

Short-form technical blog source. Publishes to [unnitallman.hashnode.dev](https://unnitallman.hashnode.dev) with automatic dev.to cross-post.

## Setup

1. `cp .env.example .env` and fill in the three values.
2. `uv sync` to install Python deps.
3. Write a post: `posts/YYYY-MM-DD-slug.md` with frontmatter (see existing posts for template).
4. Publish: `uv run scripts/shorts.py publish <slug>`.

## Commands

- `uv run scripts/shorts.py new <slug>` — scaffold a new post with frontmatter template
- `uv run scripts/shorts.py publish <slug>` — idempotent publish to Hashnode + dev.to
- `uv run scripts/shorts.py status` — list posts and their publish state

## Workflow

1. Write in `posts/<date>-<slug>.md` with `published: false` in frontmatter.
2. `uv run scripts/shorts.py publish <slug>` → pushes to Hashnode as draft; returns preview URL.
3. Review on Hashnode. Edit locally. Re-run publish — state is idempotent, updates in place.
4. When happy, flip `published: true` and re-run. Goes live on Hashnode + cross-posts to dev.to.
