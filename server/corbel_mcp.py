"""Corbel: stdio MCP server for the Procore REST API. Run with: python corbel_mcp.py"""

from __future__ import annotations

import sys

from client import ProcoreClient
from config import Config
from mcp_stdio import McpServer
from spec_index import SpecIndex
from tools import build_tools

VERSION = "0.1.0"


def build_server(config: Config, client: ProcoreClient | None = None) -> McpServer:
    tools = build_tools(client or ProcoreClient(config), SpecIndex(), config.allow_writes)
    return McpServer("corbel", VERSION, tools)


def main() -> None:
    try:
        config = Config.from_env()
    except ValueError as exc:
        print(f"corbel: configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    build_server(config).serve()


if __name__ == "__main__":
    main()
