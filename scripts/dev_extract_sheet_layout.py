"""Dev tool for the fillable sheet: print the widget rectangles of a reference character-sheet PDF as Python
literals, page by page (name, Letter-point rect, field flags, alignment, whether it is a button).

    .venv/bin/python scripts/dev_extract_sheet_layout.py /path/to/reference.pdf [--page N]

The reference PDF (the owner's D&D Beyond export) stays OUTSIDE the repository, and so does this tool's output:
server/sheet_layout.py holds only our own numbers (our names, our frames), measured with this script. Read only:
nothing is written.
"""
from __future__ import annotations

import sys

from pypdf import PdfReader


def widgets(path: str):
    reader = PdfReader(path)
    for number, page in enumerate(reader.pages, start=1):
        annots = page.get("/Annots")
        for annot in (annots.get_object() if annots is not None else []):
            annot = annot.get_object()
            if annot.get("/Subtype") != "/Widget":
                continue
            x0, y0, x1, y1 = (float(v) for v in annot["/Rect"])
            rect = (round(min(x0, x1), 1), round(min(y0, y1), 1), round(max(x0, x1), 1), round(max(y0, y1), 1))
            yield {
                "page": number,
                "name": str(annot.get("/T", "")),
                "rect": rect,
                "ff": int(annot.get("/Ff", 0) or 0),
                "q": annot.get("/Q"),
                "button": annot.get("/FT") == "/Btn",
                "size": [round(float(v), 1) for v in reader.pages[number - 1].mediabox[2:]],
            }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    only = int(argv[argv.index("--page") + 1]) if "--page" in argv else None
    last = 0
    for w in widgets(argv[1]):
        if only and w["page"] != only:
            continue
        if w["page"] != last:
            last = w["page"]
            print(f"# page {last} {w['size'][0]:g} x {w['size'][1]:g} pt")
        kind = "check" if w["button"] else ("multi" if w["ff"] & 4096 else "text")
        print(f"({w['name']!r}, {w['rect']}, {kind!r}, q={w['q']}),")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
