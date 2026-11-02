"""Static checks mirroring Anthropic's directory rules that `claude plugin validate` skips.

Usage: uv run python dev/check_plugin.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "spec-source"}
TEXT_SUFFIXES = {
    ".py",
    ".json",
    ".md",
    ".toml",
    ".txt",
    ".yml",
    ".yaml",
    ".lock",
    ".png",
    ".env",
    "",
}
BANNED_FILES = {".npmrc", "bunfig.toml", "uv.toml"}
LAUNCHERS = ("npx", "bunx", "pnpm", "yarn", "uvx", "pipx", "uv")
SECRET_PATTERN = re.compile(r"(client_secret|api[_-]?key|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}")
MAX_FILE_BYTES = 256 * 1024
MAX_FILES = 512
MAX_REPO_BYTES = 50 * 1024 * 1024


def plugin_files() -> list[Path]:
    return [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS)
    ]


def main() -> int:
    problems: list[str] = []
    files = plugin_files()
    if len(files) > MAX_FILES:
        problems.append(f"{len(files)} files exceeds {MAX_FILES}")
    if sum(f.stat().st_size for f in files) > MAX_REPO_BYTES:
        problems.append("repo exceeds 50 MiB")
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        if f.name in BANNED_FILES:
            problems.append(f"{rel}: package-manager config file")
        if f.suffix not in TEXT_SUFFIXES:
            problems.append(f"{rel}: non-text file type")
        if f.stat().st_size > MAX_FILE_BYTES:
            problems.append(f"{rel}: over 256 KiB")
        if f.suffix in {".py", ".json", ".md", ".toml", ".env"} and SECRET_PATTERN.search(
            f.read_text(encoding="utf-8", errors="replace")
        ):
            problems.append(f"{rel}: looks like a hard-coded secret")

    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}[a-z0-9]", manifest["name"]):
        problems.append("plugin name must be lowercase kebab-case")
    for key in ("description", "author", "version", "license", "homepage"):
        if not manifest.get(key):
            problems.append(f"plugin.json missing {key}")
    readme = re.sub(r"```.*?```", "", (ROOT / "README.md").read_text(encoding="utf-8"), flags=re.S)
    if len(readme.split()) < 40:
        problems.append("README under 40 words outside code blocks")
    for secret_key, spec in manifest.get("userConfig", {}).items():
        if re.search(r"secret|token|password|key", secret_key) and not spec.get("sensitive"):
            problems.append(f"userConfig.{secret_key} should be sensitive")

    mcp = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    for name, server in mcp["mcpServers"].items():
        if server.get("command") in LAUNCHERS:
            problems.append(f"mcp server {name}: package launcher '{server['command']}'")
        if not all("${CLAUDE_PLUGIN_ROOT}" in a for a in server.get("args", [])[:1]):
            problems.append(f"mcp server {name}: first arg must start at ${{CLAUDE_PLUGIN_ROOT}}")

    sys.path[:0] = [str(ROOT / "server")]
    from client import ProcoreClient
    from config import Config
    from spec_index import SpecIndex
    from tools import build_tools

    for tool in build_tools(ProcoreClient(Config()), SpecIndex(), allow_writes=True):
        info = tool.describe()
        hints = info["annotations"]
        if len(info["name"]) > 64 or not info["title"]:
            problems.append(f"tool {info['name']}: bad name/title")
        if "readOnlyHint" not in hints:
            problems.append(f"tool {info['name']}: missing readOnlyHint")
        if not hints["readOnlyHint"] and not hints.get("destructiveHint"):
            problems.append(f"tool {info['name']}: write tool must set destructiveHint")

    known_ops = SpecIndex().operations
    for doc in [*ROOT.glob("skills/*/SKILL.md"), *ROOT.glob("commands/*.md")]:
        rel = doc.relative_to(ROOT).as_posix()
        text = doc.read_text(encoding="utf-8")
        front = re.match(r"---\n(.*?)\n---\n", text, flags=re.S)
        if not front or "description:" not in front.group(1):
            problems.append(f"{rel}: missing front matter description")
        elif doc.name == "SKILL.md" and f"name: {doc.parent.name}\n" not in front.group(1) + "\n":
            problems.append(f"{rel}: skill name must match its folder")
        for op_id in re.findall(r"`(Rest[A-Za-z0-9]+)`", text):
            if op_id not in known_ops:
                problems.append(f"{rel}: unknown operation_id {op_id}")

    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{len(files)} files checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
