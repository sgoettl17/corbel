"""Minimal Model Context Protocol server over stdio (newline-delimited JSON-RPC 2.0).

Only the tools capability is implemented. The module has no dependencies so the plugin needs no
install step.
"""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")


class ToolError(Exception):
    """Raised by a tool handler; reported to the model as an error result with this message."""


@dataclass
class Tool:
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], str]
    read_only: bool = True
    annotations: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> dict[str, Any]:
        hints = {"title": self.title, "readOnlyHint": self.read_only, **self.annotations}
        if not self.read_only:
            hints.setdefault("destructiveHint", True)
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": hints,
        }


class McpServer:
    def __init__(self, name: str, version: str, tools: list[Tool]) -> None:
        self.name = name
        self.version = version
        self.tools = {tool.name: tool for tool in tools}

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Return the JSON-RPC response for a request, or None for a notification."""
        method = message.get("method")
        msg_id = message.get("id")
        if msg_id is None:
            return None  # notifications (e.g. notifications/initialized) need no reply
        try:
            result = self._dispatch(method, message.get("params") or {})
        except KeyError:
            return _error(msg_id, -32601, f"Method not found: {method}")
        except ValueError as exc:
            return _error(msg_id, -32602, str(exc))
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _dispatch(self, method: str | None, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            requested = params.get("protocolVersion")
            version = requested if requested in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
            return {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.name, "version": self.version},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [tool.describe() for tool in self.tools.values()]}
        if method == "tools/call":
            return self._call_tool(params)
        raise KeyError(method)

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(params.get("name", ""))
        if tool is None:
            raise ValueError(f"Unknown tool: {params.get('name')}")
        try:
            text = tool.handler(params.get("arguments") or {})
            return {"content": [{"type": "text", "text": text}], "isError": False}
        except ToolError as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}

    def serve(self) -> None:
        stdin, stdout = sys.stdin, sys.stdout
        for stream in (stdin, stdout):
            if isinstance(stream, io.TextIOWrapper):
                stream.reconfigure(encoding="utf-8")
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                stdout.write(json.dumps(_error(None, -32700, "Parse error")) + "\n")
                stdout.flush()
                continue
            response = self.handle(message)
            if response is not None:
                stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                stdout.flush()


def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}
