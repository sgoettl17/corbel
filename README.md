# Corbel

Corbel lets Claude search and call the [Procore REST API](https://developers.procore.com/reference/rest/docs/rest-api-overview) (3,192 endpoints) through a local MCP server. It is **read-only by default**.

> Corbel is an independent, unofficial project. It is not affiliated with, endorsed by, or sponsored by Procore Technologies, Inc. "Procore" is a trademark of its owner.

## What it does

| Tool | Purpose | Changes data |
| --- | --- | --- |
| `corbel_search_endpoints` | Keyword search of the bundled endpoint index | No |
| `corbel_describe_endpoint` | Path, parameters and body fields for one endpoint | No |
| `corbel_get` | Call any GET endpoint, with optional pagination | No |
| `corbel_create` | Call a POST endpoint | Yes (only if writes are enabled) |
| `corbel_update` | Call a PUT or PATCH endpoint | Yes (only if writes are enabled) |
| `corbel_delete` | Call a DELETE endpoint | Yes (only if writes are enabled) |

The model finds an endpoint with `corbel_search_endpoints`, checks it with `corbel_describe_endpoint`, then calls it. The index covers every `/rest/` operation in Procore's published OpenAPI export.

## Install (Claude Code)

```bash
claude plugin marketplace add sgoettl17/corbel
claude plugin install corbel@sgoettl17-plugins
```

Claude Code asks for your Procore client ID, client secret and company ID. The secrets are stored in your system credential store, not in a settings file. Requires Python 3.10+ available as `python3`. No packages are installed.

## Procore credentials

Create a developer app in the Procore developer portal that uses the client credentials grant (a service account), grant it access to your company, and use its client ID and secret. Use the `sandbox` environment first. Corbel can only do what that app's permissions allow.

## Use with other MCP clients (Cursor and others)

Corbel is a standard stdio MCP server. Point the client at `python3 server/corbel_mcp.py` and set the environment variables `CORBEL_CLIENT_ID`, `CORBEL_CLIENT_SECRET`, `CORBEL_COMPANY_ID`, `CORBEL_ENVIRONMENT` (`production` or `sandbox`) and optionally `CORBEL_ALLOW_WRITES=true`. `CORBEL_ACCESS_TOKEN` can be set instead of the client ID and secret. See [docs/other-clients.md](docs/other-clients.md).

## Data handling

Corbel runs on your machine and calls only the Procore host for the environment you choose (`api.procore.com` or `sandbox.procore.com`, plus the matching login host). It sends nothing anywhere else and keeps no data after the process exits. Responses are returned to your MCP client, which sends them to its model. See [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md).

## Development

Dev tooling uses `uv`, `ruff` and `ty`. The shipped server uses only the Python standard library.

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run ty check
uv run pytest
uv run python dev/build_index.py path/to/procore-openapi.json   # regenerate spec/index
claude plugin validate . --strict
```

See [AGENTS.md](AGENTS.md) for the repo standard and [docs/standards.md](docs/standards.md) for the directory checklist this repo is held to.

## License

MIT. See [LICENSE](LICENSE).
