"""Build the sharded endpoint index shipped in spec/index from a Procore OpenAPI export.

Usage: uv run python dev/build_index.py PATH_TO_OPENAPI.json

The output is compact, human-readable JSON. Every shard stays well under the 256 KiB per-file
limit that Anthropic's plugin directory enforces.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "spec" / "index"
SHARD_LIMIT_BYTES = 180_000
METHODS = ("get", "post", "put", "patch", "delete")
DESC_LIMIT = 280


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "misc"


def short(text: str | None, limit: int = DESC_LIMIT) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def schema_type(schema: dict[str, Any] | None) -> str:
    schema = schema or {}
    kind = schema.get("type", "any")
    if kind == "array":
        return f"array<{schema_type(schema.get('items'))}>"
    return str(kind)


def compact_operation(path: str, method: str, op: dict[str, Any]) -> dict[str, Any]:
    tags = op.get("tags") or ["Uncategorized"]
    record: dict[str, Any] = {
        "id": op["operationId"],
        "m": method,
        "p": path,
        "t": tags[0],
        "s": short(op.get("summary"), 120),
        "d": short(op.get("description")),
    }
    path_params: list[str] = []
    query: list[list[Any]] = []
    for param in op.get("parameters", []):
        entry = [param["name"], schema_type(param.get("schema")), bool(param.get("required"))]
        if param.get("in") == "path":
            path_params.append(param["name"])
        elif param.get("in") == "query":
            query.append(entry)
    record["pp"] = path_params or re.findall(r"{(\w+)}", path)
    if query:
        record["q"] = query
    body = op.get("requestBody")
    if body:
        content = body.get("content", {})
        media = "application/json" if "application/json" in content else next(iter(content), "")
        schema = content.get(media, {}).get("schema", {})
        record["b"] = {
            "ct": media,
            "req": schema.get("required", []),
            "props": [[k, schema_type(v)] for k, v in schema.get("properties", {}).items()],
        }
    return record


def collect(spec: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for path, item in spec["paths"].items():
        if not path.startswith("/rest/"):
            continue  # oauth endpoints are handled by the auth module, not exposed as tools
        for method in METHODS:
            op = item.get(method)
            if isinstance(op, dict) and "operationId" in op:
                records.append(compact_operation(path, method, op))
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate operationId in spec")
    return records


def write_shards(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        area = "/".join(rec["t"].split("/")[:2])
        groups.setdefault(area, []).append(rec)

    for old in OUT_DIR.glob("*.json"):
        old.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    shards = []
    for area, items in sorted(groups.items()):
        for part, chunk in enumerate(chunk_by_size(items), start=1):
            name = f"{slug(area)}-{part}.json"
            (OUT_DIR / name).write_text(
                json.dumps(chunk, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
            )
            shards.append({"file": name, "area": area, "count": len(chunk)})
    return shards


def chunk_by_size(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = [[]]
    size = 0
    for rec in items:
        rec_size = len(json.dumps(rec, ensure_ascii=False))
        if chunks[-1] and size + rec_size > SHARD_LIMIT_BYTES:
            chunks.append([])
            size = 0
        chunks[-1].append(rec)
        size += rec_size
    return chunks


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    records = collect(spec)
    shards = write_shards(records)
    manifest = {
        "source": spec["info"].get("title"),
        "source_created_at": spec["info"].get("x-created-at"),
        "operation_count": len(records),
        "shards": shards,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    print(f"{len(records)} operations in {len(shards)} shards -> {OUT_DIR}")


if __name__ == "__main__":
    main()
