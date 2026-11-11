"""Dev tool: write sample fillable character sheets (SHEET slices) so the owner can open them in a PDF viewer.

    .venv/bin/python scripts/dev_sample_sheets.py <output directory>

Writes paladin6 (Bulgarian and English), wizard5 (2014, Bulgarian) and a level-20 wizard (English and Bulgarian) built from
the kitchen-sink drafts of server/tests/kitchen_sink.py. Needs the bundled 5etools data for the kitchen-sink drafts that
use it (a sample is skipped with a message when its data is missing). Nothing is written inside the repository unless you
point the directory there.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "server"), str(ROOT / "server" / "tests")]

SAMPLES = (("paladin6", "bg"), ("paladin6", "en"), ("wizard5-2014", "bg"), ("wizard20-2014", "en"), ("wizard20-2014", "bg"))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    from catalog.loader import load
    from engine.resolve import resolve
    from kitchen_sink import KITCHEN_SINK, build, skip_reason
    import sheet_pdf

    catalog = load()
    created = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
    for sid, lang in SAMPLES:
        spec = KITCHEN_SINK[sid]
        reason = skip_reason(spec)
        if reason:
            print(f"skip {sid} ({lang}): {reason}")
            continue
        resolution = resolve(build(sid, catalog, resolve), catalog)
        data = sheet_pdf.to_sheet(resolution, lang, catalog, created, spec["ruleset"])
        target = out / f"sheet-{sid}-{lang}.pdf"
        target.write_bytes(data)
        print(f"wrote {target} ({len(data) // 1024} KB)")
    spec = KITCHEN_SINK_HALF_ORC = _half_orc_spec()
    reason = skip_reason(spec)
    if reason:
        print(f"skip half-orc: {reason}")
        return 0
    from kitchen_sink import base_draft, fill

    draft = fill(base_draft(spec), catalog, spec["overrides"], resolve)
    draft["name"] = "Корвин Тъмнокосия"
    resolution = resolve(draft, catalog)
    for lang in ("bg", "en"):  # a long species label: "Half-Orc (Variant; Mark of Finding)"
        target = out / f"sheet-halforc-mark-of-finding-{lang}.pdf"
        target.write_bytes(sheet_pdf.to_sheet(resolution, lang, catalog, created, "2014"))
        print(f"wrote {target}")
    return 0


def _half_orc_spec() -> dict:
    from kitchen_sink import _sub

    return _sub("rogue", 5, "2014", marks=("classes", "official"),
                origin=("half-orc-phb", "criminal", "half-orc-phb-variant;-mark-of-finding-erlw"))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
