"""Check Procore's published OpenAPI spec for changes and optionally rebuild the index.

Usage:
    uv run python dev/update_spec.py                 report only; exit 10 if the spec changed
    uv run python dev/update_spec.py --write         also rebuild spec/index
    uv run python dev/update_spec.py --summary FILE  write a Markdown change summary

A cheap ETag comparison skips the 60 MB download when nothing changed. When the ETag differs, the
spec is downloaded and compared by a hash of the indexed content, so a spec that only changed its
generated-at timestamp is reported as unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

import build_index

MANIFEST = build_index.OUT_DIR / "manifest.json"
CHANGED_EXIT_CODE = 10
TIMEOUT_SECONDS = 300


def fetch_etag(url: str) -> str:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.headers.get("ETag", "")


def download(url: str) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".json") as handle:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            while chunk := response.read(1 << 20):
                handle.write(chunk)
        handle.seek(0)
        return json.load(handle)


def indexed_ids() -> set[str]:
    ids: set[str] = set()
    for shard in build_index.OUT_DIR.glob("*.json"):
        if shard.name != "manifest.json":
            ids.update(op["id"] for op in json.loads(shard.read_text(encoding="utf-8")))
    return ids


def summary(added: list[str], removed: list[str], manifest: dict, new_manifest: dict) -> str:
    lines = [
        "## Procore OpenAPI spec update",
        "",
        f"- Source: {build_index.SOURCE_URL}",
        f"- Spec generated: {manifest.get('source_created_at')} -> "
        f"{new_manifest['source_created_at']}",
        f"- Operations: {manifest.get('operation_count')} -> {new_manifest['operation_count']}",
        f"- Added: {len(added)}, removed: {len(removed)}",
        "",
        "Review removed operations against `skills/` and `commands/` (the CI checker fails if "
        "they still reference one). Release notes: https://developers.procore.com/changelog",
    ]
    for title, ids in (("Added", added), ("Removed", removed)):
        if ids:
            lines += ["", f"### {title}", "", *(f"- `{i}`" for i in ids[:200])]
            if len(ids) > 200:
                lines.append(f"- ...and {len(ids) - 200} more")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="rebuild spec/index when changed")
    parser.add_argument("--force", action="store_true", help="skip the ETag shortcut")
    parser.add_argument("--summary", type=Path, help="write a Markdown summary here")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    etag = fetch_etag(build_index.SOURCE_URL)
    if etag and etag == manifest.get("source_etag") and not args.force:
        print(f"Up to date (ETag {etag}).")
        return 0

    spec = download(build_index.SOURCE_URL)
    records = build_index.collect(spec)
    if build_index.fingerprint(records) == manifest.get("fingerprint"):
        print("Spec content unchanged (only the ETag or timestamp differs).")
        return 0

    new_ids = {r["id"] for r in records}
    old_ids = indexed_ids()
    added, removed = sorted(new_ids - old_ids), sorted(old_ids - new_ids)
    if args.write:
        new_manifest = build_index.build(spec, etag)
    else:
        new_manifest = {
            "source_created_at": spec["info"].get("x-created-at"),
            "operation_count": len(records),
        }
    text = summary(added, removed, manifest, new_manifest)
    if args.summary:
        args.summary.write_text(text, encoding="utf-8")
    print(text)
    return CHANGED_EXIT_CODE


if __name__ == "__main__":
    sys.exit(main())
