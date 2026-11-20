#!/usr/bin/env python3
"""Generate the PWA icons in frontend/public/icons/.

    .venv/bin/python scripts/make_pwa_icons.py

The d20 line mark of the header brand (frontend/src/App.tsx, viewBox 32: outer hexagon, inner triangle, seven edges
between them) drawn as strokes in --color-page on a --color-highlight (brand green) background (first occurrence of each in
frontend/src/styles/tokens.css, i.e. the light theme). The stroke is 5.5 % of the mark's box, with round joins.
Output (committed):
  icon-192.png, icon-512.png            "any" icons (the mark's box is 62 % of the square)
  icon-maskable-192.png, -512.png       "maskable" icons: full-bleed background, the mark's box is 50 % (inside the safe zone)
  apple-touch-icon.png                  180x180, opaque (iOS does not accept transparency), the box is 62 %
A designer can replace the PNGs (same names and sizes); nothing else refers to how they were made.
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


def token(name: str) -> tuple[int, int, int]:
    m = re.search(rf"--{name}:\s*#([0-9a-fA-F]{{6}})", TOKENS.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"--{name} not found in tokens.css")
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# The mark in the 32x32 viewBox of the header brand (App.tsx): outer polygon, inner triangle, 7 segments.
OUTER = [(16, 2.5), (28.5, 9.5), (28.5, 22.5), (16, 29.5), (3.5, 22.5), (3.5, 9.5)]
INNER = [(16, 9.5), (22.5, 20.5), (9.5, 20.5)]
SEGMENTS = [
    ((16, 2.5), (16, 9.5)),
    ((28.5, 9.5), (22.5, 20.5)),
    ((3.5, 9.5), (9.5, 20.5)),
    ((3.5, 22.5), (9.5, 20.5)),
    ((28.5, 22.5), (22.5, 20.5)),
    ((16, 29.5), (9.5, 20.5)),
    ((16, 29.5), (22.5, 20.5)),
]
LINES = [(OUTER[i], OUTER[(i + 1) % 6]) for i in range(6)] + [(INNER[i], INNER[(i + 1) % 3]) for i in range(3)] + SEGMENTS
STROKE = 0.055  # of the mark's box


def dist_to_segment(px: float, py: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def png(size: int, pixels: bytes) -> bytes:
    """An 8-bit RGB PNG from raw rows (stdlib only: no Pillow needed for this developer tool)."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    rows = b"".join(b"\x00" + pixels[y * size * 3:(y + 1) * size * 3] for y in range(size))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def icon(size: int, box_fraction: float) -> bytes:
    """Brand-green square with the d20 mark in the page colour; the 32-unit viewBox of the mark is box_fraction of the side."""
    bg = token("color-highlight")  # the site's brand green (owner, 2026-11-20)
    fg = token("color-page")
    box = size * box_fraction
    scale = box / 32
    ox = oy = (size - box) / 2
    half = STROKE * box / 2
    # the lines in pixel coordinates
    lines = [(((ax * scale + ox), (ay * scale + oy)), ((bx * scale + ox), (by * scale + oy))) for (ax, ay), (bx, by) in LINES]

    def near(x: float, y: float) -> float:
        return min(dist_to_segment(x, y, a, b) for a, b in lines)

    out = bytearray()
    for y in range(size):
        for x in range(size):
            if x + 1 < ox or x > ox + box or y + 1 < oy or y > oy + box:
                out += bytes(bg)
                continue
            d = near(x + 0.5, y + 0.5)
            if d > half + 1:
                k = 0.0
            elif d < half - 1:
                k = 1.0
            else:
                hit = sum(near(x + (i + 0.5) / SAMPLES, y + (j + 0.5) / SAMPLES) <= half for i in range(SAMPLES) for j in range(SAMPLES))
                k = hit / (SAMPLES * SAMPLES)
            out += bytes(round(f * k + b * (1 - k)) for f, b in zip(fg, bg))
    return png(size, bytes(out))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        (OUT / f"icon-{size}.png").write_bytes(icon(size, 0.62))
        (OUT / f"icon-maskable-{size}.png").write_bytes(icon(size, 0.50))
    (OUT / "apple-touch-icon.png").write_bytes(icon(180, 0.62))
    for p in sorted(OUT.glob("*.png")):
        print(f"{p.relative_to(ROOT)} {p.stat().st_size} bytes")


if __name__ == "__main__":
    main()
