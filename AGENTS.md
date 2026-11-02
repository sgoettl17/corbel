# AGENTS.md

Guidance for AI agents (and humans) working in this repo.

## What this is

Corbel: a Claude Code plugin that bundles a stdio MCP server for the Procore REST API. The repo root is the plugin root. It must stay valid for Anthropic's plugin directory. See `docs/standards.md`.

## Layout

- `.claude-plugin/plugin.json`, `marketplace.json`, `.mcp.json`: plugin manifest and server launch.
- `server/`: the MCP server. Standard library only. Flat modules, imported by name.
  - `mcp_stdio.py` protocol, `client.py` HTTP and auth, `spec_index.py` index search, `tools.py` tools, `corbel_mcp.py` entry point.
- `spec/index/`: generated endpoint shards. Never edit by hand; regenerate with `dev/build_index.py`.
- `dev/`: tooling that is not part of the runtime. `tests/`: pytest with a fake transport, no network.

## Rules

1. Python tooling is always `uv`, `ruff` and `ty`. Config lives in `pyproject.toml` only.
2. The shipped server must not add dependencies, a launcher (`uv run`, `npx`), compiled or minified code, or binary files.
3. Reads and writes stay in separate tools. Every tool has a `title`, accurate description and annotations. Tool names are 64 characters or fewer.
4. Tool descriptions say what the tool does; they never instruct the model how to behave.
5. Every non-image file stays under 256 KiB; the plugin stays at 512 files or fewer; the repo stays under 50 MiB.
6. Never commit credentials, `.env` files or the full OpenAPI export.
7. Before finishing a change run: `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run pytest`, `uv run python dev/check_plugin.py`, `claude plugin validate . --strict`.

## Procore concepts an agent needs

- Procore organizes data under a **company**, which has **projects**. Most endpoints need `company_id` (also sent as the `Procore-Company-Id` header) and many need `project_id`.
- Endpoints are versioned in the path (`/rest/v1.0/...`, `/rest/v2.0/...`). Several versions of a resource can coexist; prefer the newest unless a field you need is missing.
- Lists use `page` and `per_page` (max 100) query parameters.
- Typical flow: `corbel_search_endpoints` -> `corbel_describe_endpoint` -> `corbel_get`.
