"""MCP tool definitions for the Procore REST API.

Reads and writes are separate tools. Write tools are only registered when the user has enabled
writes in the plugin settings.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from client import ProcoreClient, ProcoreError
from mcp_stdio import Tool, ToolError
from spec_index import SpecIndex

API_DOCS = "https://developers.procore.com/reference/rest/docs/rest-api-overview"
MAX_OUTPUT_CHARS = 40_000
MAX_PAGES = 10
PAGE_SIZE = 100

OPERATION_ID = {"type": "string", "description": "operation_id from corbel_search_endpoints."}
PATH_PARAMS = {
    "type": "object",
    "description": "Values for the {placeholders} in the endpoint path, e.g. project_id.",
    "additionalProperties": {"type": ["string", "integer"]},
}
QUERY = {
    "type": "object",
    "description": "Query parameters. Nested objects become filters[key]=value; "
    "lists become key[]=value.",
}


def encode_query(params: dict[str, Any] | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []

    def add(key: str, value: Any) -> None:
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                add(f"{key}[{sub_key}]", sub_value)
        elif isinstance(value, list):
            for item in value:
                add(key if key.endswith("[]") else f"{key}[]", item)
        elif isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
        elif value is not None:
            pairs.append((key, str(value)))

    for key, value in (params or {}).items():
        add(key, value)
    return pairs


def expand_path(op: dict[str, Any], path_params: dict[str, Any] | None) -> str:
    provided = path_params or {}
    missing = [name for name in op["pp"] if name not in provided]
    if missing:
        raise ToolError(f"Missing path parameters: {', '.join(missing)} for {op['p']}")

    def replace(match: re.Match[str]) -> str:
        return urllib.parse.quote(str(provided[match.group(1)]), safe="")

    return re.sub(r"{(\w+)}", replace, op["p"])


def render(data: Any) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if len(text) > MAX_OUTPUT_CHARS:
        return (
            text[:MAX_OUTPUT_CHARS]
            + f"\n[truncated at {MAX_OUTPUT_CHARS} of {len(text)} characters; narrow the request "
            "with filters or a smaller per_page]"
        )
    return text


def summarize(op: dict[str, Any]) -> dict[str, Any]:
    return {k: op[k] for k in ("id", "m", "p", "s", "t")}


class ProcoreTools:
    def __init__(self, client: ProcoreClient, index: SpecIndex) -> None:
        self.client = client
        self.index = index

    def _operation(self, args: dict[str, Any], allowed: set[str], tool: str, hint: str) -> dict:
        op_id = args.get("operation_id", "")
        op = self.index.get(op_id)
        if op is None:
            raise ToolError(f"Unknown operation_id '{op_id}'. Use corbel_search_endpoints first.")
        if op["m"] not in allowed:
            raise ToolError(f"{op_id} is a {op['m'].upper()} endpoint; {hint}")
        return op

    def _call(self, op: dict[str, Any], args: dict[str, Any], body: Any = None) -> Any:
        path = expand_path(op, args.get("path_params"))
        query = encode_query(args.get("query"))
        try:
            data, _ = self.client.request(
                op["m"].upper(), path, query, body, args.get("company_id")
            )
        except ProcoreError as exc:
            raise ToolError(str(exc)) from exc
        return data

    # -- discovery -------------------------------------------------------------------------

    def search(self, args: dict[str, Any]) -> str:
        limit = min(int(args.get("limit", 15)), 50)
        found = self.index.search(
            args.get("query", ""), args.get("method"), args.get("area"), limit
        )
        if not found:
            return "No matching endpoints. Try broader words or call without 'area'."
        return render([summarize(op) for op in found])

    def describe(self, args: dict[str, Any]) -> str:
        op = self.index.get(args.get("operation_id", ""))
        if op is None:
            raise ToolError("Unknown operation_id. Use corbel_search_endpoints first.")
        return render(op)

    # -- reads and writes ------------------------------------------------------------------

    def get(self, args: dict[str, Any]) -> str:
        op = self._operation(
            args, {"get"}, "corbel_get", "use corbel_create, corbel_update or corbel_delete."
        )
        if not args.get("all_pages"):
            return render(self._call(op, args))
        max_pages = min(int(args.get("max_pages", 3)), MAX_PAGES)
        query = dict(args.get("query") or {})
        per_page = int(query.setdefault("per_page", PAGE_SIZE))
        results: list[Any] = []
        for page in range(1, max_pages + 1):
            query["page"] = page
            data = self._call(op, {**args, "query": query})
            if not isinstance(data, list):
                return render(data)  # not a paged list; return as-is
            results.extend(data)
            if len(data) < per_page:
                break
        return render(results)

    def create(self, args: dict[str, Any]) -> str:
        op = self._operation(args, {"post"}, "corbel_create", "use corbel_get/update/delete.")
        return render(self._call(op, args, args.get("body")))

    def update(self, args: dict[str, Any]) -> str:
        op = self._operation(args, {"put", "patch"}, "corbel_update", "use the matching tool.")
        return render(self._call(op, args, args.get("body")))

    def delete(self, args: dict[str, Any]) -> str:
        op = self._operation(args, {"delete"}, "corbel_delete", "use the matching tool.")
        return render(self._call(op, args))


def build_tools(client: ProcoreClient, index: SpecIndex, allow_writes: bool) -> list[Tool]:
    impl = ProcoreTools(client, index)
    common = {"path_params": PATH_PARAMS, "query": QUERY}
    company = {
        "company_id": {
            "type": "string",
            "description": "Override the configured Procore-Company-Id for this call.",
        }
    }
    tools = [
        Tool(
            "corbel_search_endpoints",
            "Search Procore API endpoints",
            "Search the bundled index of the Procore REST API "
            f"({API_DOCS}) by keyword and return matching operation_ids with method and path. "
            "Does not call Procore.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "e.g. 'rfis project'"},
                    "method": {"type": "string", "enum": ["get", "post", "put", "patch", "delete"]},
                    "area": {"type": "string", "description": "Tool area filter, e.g. 'Rfis'."},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["query"],
            },
            impl.search,
        ),
        Tool(
            "corbel_describe_endpoint",
            "Describe a Procore endpoint",
            "Return the path, parameters and request-body fields of one Procore endpoint from the "
            "bundled index. Does not call Procore.",
            {
                "type": "object",
                "properties": {"operation_id": OPERATION_ID},
                "required": ["operation_id"],
            },
            impl.describe,
        ),
        Tool(
            "corbel_get",
            "Read from Procore",
            f"Call a read-only (GET) endpoint of the Procore REST API ({API_DOCS}). Set all_pages "
            "to follow page/per_page pagination for list endpoints.",
            {
                "type": "object",
                "properties": {
                    "operation_id": OPERATION_ID,
                    **common,
                    "all_pages": {"type": "boolean"},
                    "max_pages": {"type": "integer", "minimum": 1, "maximum": MAX_PAGES},
                    **company,
                },
                "required": ["operation_id"],
            },
            impl.get,
        ),
    ]
    if allow_writes:
        body = {"body": {"type": "object", "description": "JSON request body."}}
        for name, title, verb, handler in (
            ("corbel_create", "Create in Procore", "POST (create)", impl.create),
            ("corbel_update", "Update in Procore", "PUT/PATCH (update)", impl.update),
            ("corbel_delete", "Delete from Procore", "DELETE", impl.delete),
        ):
            props = {"operation_id": OPERATION_ID, **common, **company}
            if name != "corbel_delete":
                props.update(body)
            tools.append(
                Tool(
                    name,
                    title,
                    f"Call a {verb} endpoint of the Procore REST API ({API_DOCS}). "
                    "Changes data in Procore.",
                    {"type": "object", "properties": props, "required": ["operation_id"]},
                    handler,
                    read_only=False,
                    annotations={"destructiveHint": True},
                )
            )
    return tools
