# Repo standard: Anthropic directory readiness

This repo is held to the checks Anthropic's directory applies to plugin bundles and MCP servers. `dev/check_plugin.py` and `claude plugin validate --strict` enforce what can be automated; the rest is a release checklist.

Sources: [plugin pre-submission checklist](https://claude.com/docs/plugins/pre-submission-checklist.md), [connector review criteria](https://claude.com/docs/connectors/building/review-criteria.md), [plugin publishing](https://code.claude.com/docs/en/plugins/publish.md).

## Automated (`dev/check_plugin.py`)

- Plugin name is lowercase kebab-case and not reserved.
- `plugin.json` has `description`, `author`, `version`, `license`; README has at least 40 words outside code blocks; `LICENSE` exists.
- No non-text files; no file over 256 KiB (images and fonts aside); 512 files or fewer; repo under 50 MiB.
- No `.npmrc`, `bunfig.toml` or `uv.toml`; no package launchers in `.mcp.json`; the server command uses plain arguments and `${CLAUDE_PLUGIN_ROOT}`.
- Every MCP tool has `title`, `readOnlyHint` or `destructiveHint`, a name of 64 characters or fewer, and write tools are `destructiveHint: true`.
- No secret-looking strings in tracked files.

## Release checklist (manual)

- [ ] Run **Validate** in the developer portal; fix every Blocking finding.
- [ ] Bump `version` in `plugin.json`, `pyproject.toml` and `server/corbel_mcp.py`; update `CHANGELOG.md`.
- [ ] Confirm the README documents everything the plugin runs, sends or fetches.
- [ ] Sandbox smoke test of every read tool; write tools tested only against sandbox.
- [ ] Repo is public before the listing goes live.
