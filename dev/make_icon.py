"""Generate the plugin icon (a stepped corbel bracket) as a 512x512 PNG using only the stdlib."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 512
BG = (24, 38, 61)
FG = (242, 169, 0)
OUT = Path(__file__).resolve().parent.parent / "assets" / "icon.png"


def in_bracket(x: int, y: int) -> bool:
    wall = 96 <= x < 176 and 96 <= y < 416  # vertical wall
    steps = any(176 <= x < 176 + 80 * (i + 1) and 96 + 80 * i <= y < 176 + 80 * i for i in range(4))
    return wall or steps


def chunk(kind: bytes, data: bytes) -> bytes:
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))


def main() -> None:
    rows = bytearray()
    for y in range(SIZE):
        rows.append(0)
        for x in range(SIZE):
            rows.extend(FG if in_bracket(x, y) else BG)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + chunk(b"IEND", b"")
    )
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(png)
    print(f"wrote {OUT} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
