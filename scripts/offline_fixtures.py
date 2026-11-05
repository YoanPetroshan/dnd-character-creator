#!/usr/bin/env python3
"""Emit the inputs of the offline (Pyodide in Node) equivalence test as JSON, built natively from the test helpers.

    .venv/bin/python scripts/offline_fixtures.py <out.json>

Output: {"exports": {id: {"draft": ...} | {"resolution": ...}}, "requests": [{name, method, url, body (base64 or
null), ctype}]}. The 52 export ids are those of server/tests/export_baseline.json (kitchen-sink / long drafts as
drafts, the hand-built ones as resolutions). The expected hashes are NOT emitted: the test reads
export_baseline.json and service_baseline.json itself. Needs the bundled official data (the default).
"""
from __future__ import annotations

import base64
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "server" / "tests"))

from catalog.loader import load  # noqa: E402
from engine.resolve import resolve  # noqa: E402
from kitchen_sink import KITCHEN_SINK, base_draft, build, fill, skip_reason  # noqa: E402
from service_requests import REQUESTS  # noqa: E402
from test_export_baseline import HAND  # noqa: E402
from test_export_completeness import ALL_SPECS  # noqa: E402


def main(out: str) -> None:
    catalog = load()
    exports = {}
    for sid in ALL_SPECS:
        spec = ALL_SPECS[sid]
        reason = skip_reason(spec)
        if reason:
            raise SystemExit(f"{sid}: {reason}")
        draft = build(sid, catalog, resolve) if sid in KITCHEN_SINK else fill(base_draft(spec), catalog, spec["overrides"], resolve)
        exports[sid] = {"draft": draft}
    for sid, make in HAND.items():
        exports[sid] = {"resolution": make()}
    requests = [{"name": n, "method": m, "url": u, "body": None if b is None else base64.b64encode(b).decode(), "ctype": c}
                for n, m, u, b, c in REQUESTS]
    pathlib.Path(out).write_text(json.dumps({"exports": exports, "requests": requests}), encoding="utf-8")
    print(f"{len(exports)} export cases, {len(requests)} requests -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
