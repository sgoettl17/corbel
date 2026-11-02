"""Load and search the bundled, sharded Procore endpoint index (spec/index)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

DEFAULT_DIR = Path(__file__).resolve().parent.parent / "spec" / "index"


class SpecIndex:
    def __init__(self, directory: Path = DEFAULT_DIR) -> None:
        self.directory = directory
        self._ops: dict[str, dict[str, Any]] | None = None

    @property
    def operations(self) -> dict[str, dict[str, Any]]:
        if self._ops is None:
            manifest = json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))
            ops: dict[str, dict[str, Any]] = {}
            for shard in manifest["shards"]:
                text = (self.directory / shard["file"]).read_text(encoding="utf-8")
                for op in json.loads(text):
                    ops[op["id"]] = op
            self._ops = ops
        return self._ops

    def get(self, operation_id: str) -> dict[str, Any] | None:
        return self.operations.get(operation_id)

    def areas(self) -> list[str]:
        return sorted({"/".join(op["t"].split("/")[:2]) for op in self.operations.values()})

    def search(
        self, query: str, method: str | None = None, area: str | None = None, limit: int = 15
    ) -> list[dict[str, Any]]:
        terms = [t for t in re.split(r"[^a-z0-9]+", query.lower()) if t]
        scored: list[tuple[int, dict[str, Any]]] = []
        for op in self.operations.values():
            if method and op["m"] != method.lower():
                continue
            if area and area.lower() not in op["t"].lower():
                continue
            haystack = f"{op['s']} {op['p']} {op['t']} {op['d']}".lower()
            score = 0
            for term in terms:
                if term in op["s"].lower():
                    score += 4
                if term in op["p"].lower() or term in op["t"].lower():
                    score += 2
                if term in haystack:
                    score += 1
            if score and (not terms or all(t in haystack for t in terms)):
                scored.append((score, op))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["p"], pair[1]["m"]))
        return [op for _, op in scored[:limit]]
