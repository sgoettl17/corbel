"""Read-only smoke test against a real Procore environment (sandbox by default).

Reads CORBEL_CLIENT_ID, CORBEL_CLIENT_SECRET and CORBEL_COMPANY_ID from the environment.
Never prints credentials or response bodies, only counts and status.

Usage: uv run python dev/live_smoke.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "server")]

from client import ProcoreError  # noqa: E402
from config import Config  # noqa: E402
from corbel_mcp import build_server  # noqa: E402


def call(server, name: str, arguments: dict) -> dict:
    reply = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    return reply["result"]


def main() -> int:
    os.environ.setdefault("CORBEL_ENVIRONMENT", "sandbox")
    try:
        config = Config.from_env()
    except Exception as exc:
        print(f"FAIL config: {exc}")
        return 1
    print(f"environment={config.environment} company_id set={bool(config.company_id)}")
    server = build_server(config)

    checks = [
        ("companies", "RestV10CompaniesGet", {"per_page": 5}),
        ("projects", "RestV10ProjectsGet", {"company_id": config.company_id, "per_page": 5}),
    ]
    failures = 0
    for label, operation_id, query in checks:
        try:
            result = call(server, "corbel_get", {"operation_id": operation_id, "query": query})
        except ProcoreError as exc:
            print(f"FAIL {label}: {exc}")
            failures += 1
            continue
        if result.get("isError"):
            print(f"FAIL {label}: {result['content'][0]['text'][:200]}")
            failures += 1
            continue
        data = json.loads(result["content"][0]["text"])
        count = len(data) if isinstance(data, list) else "n/a"
        print(f"OK   {label}: {count} record(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
