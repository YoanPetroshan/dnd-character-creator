#!/usr/bin/env python3
"""Generate the placeholder PWA icons in frontend/public/icons/ (functional only, not a design).

    .venv/bin/python scripts/make_pwa_icons.py

A plain white hexagon on the accent colour of frontend/src/styles/tokens.css (--color-accent). Output (committed):
  icon-192.png, icon-512.png            "any" icons (the hexagon fills about 70 % of the square)
  icon-maskable-192.png, -512.png       "maskable" icons: full-bleed background, the hexagon inside the 80 % safe zone
  apple-touch-icon.png                  180x180, opaque (iOS does not accept transparency)
A designer replaces the PNGs (same names and sizes); nothing else refers to how they were made.
"""
from __future__ import annotations

import math
import pathlib
import re
import struct
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "public" / "icons"
TOKENS = ROOT / "frontend" / "src" / "styles" / "tokens.css"
SAMPLES = 3  # 3x3 samples per pixel for smooth edges


def accent() -> tuple[int, int, int]:
    m = re.search(r"--color-accent:\s*#([0-9a-fA-F]{6})", TOKENS.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("--color-accent not found in tokens.css")
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def png(size: int, pixels: bytes) -> bytes:
    """An 8-bit RGB PNG from raw rows (stdlib only: no Pillow needed for this developer tool)."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    rows = b"".join(b"\x00" + pixels[y * size * 3:(y + 1) * size * 3] for y in range(size))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def icon(size: int, glyph_fraction: float) -> bytes:
    """Accent-coloured square with a white regular hexagon (point up) whose circumradius is glyph_fraction/2 of the side."""
    bg = accent()
    c = size / 2
    r = size * glyph_fraction / 2
    apothem = r * math.sqrt(3) / 2  # distance from the centre to each side
    normals = [(math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i))) for i in range(6)]

    def inside(x: float, y: float) -> bool:
        return all((x - c) * nx + (y - c) * ny <= apothem for nx, ny in normals)

    out = bytearray()
    for y in range(size):
        for x in range(size):
            if abs(x + 0.5 - c) > r or abs(y + 0.5 - c) > r:
                out += bytes(bg)
                continue
            hit = sum(inside(x + (i + 0.5) / SAMPLES, y + (j + 0.5) / SAMPLES) for i in range(SAMPLES) for j in range(SAMPLES))
            k = hit / (SAMPLES * SAMPLES)
            out += bytes(round(255 * k + ch * (1 - k)) for ch in bg)
    return png(size, bytes(out))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        (OUT / f"icon-{size}.png").write_bytes(icon(size, 0.70))
        (OUT / f"icon-maskable-{size}.png").write_bytes(icon(size, 0.50))  # inside the 80 % safe circle
    (OUT / "apple-touch-icon.png").write_bytes(icon(180, 0.66))
    for p in sorted(OUT.glob("*.png")):
        print(f"{p.relative_to(ROOT)} {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
