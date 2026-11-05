"""XL baseline: the Markdown / YAML / PDF a draft produced BEFORE exports became bilingual.

``export_baseline.json`` holds one sha256 per (draft, format). With ``lang`` omitted or ``"bg"`` the exporters must
keep producing exactly these bytes (the PDF is compared after normalising /CreationDate and /ID, the only parts
fpdf2 varies between runs). Drafts: every KITCHEN_SINK + LONG draft of test_export_completeness (skipped when the
5etools data is absent, like there) and a few hand-built resolutions (nameless, details of every kind).

Regenerate only on purpose: ``WRITE_EXPORT_BASELINE=1 pytest tests/test_export_baseline.py`` (merges, keeps entries
of skipped drafts).
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re

import pytest

from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
from kitchen_sink import KITCHEN_SINK, base_draft, build, fill, skip_reason
from markdown_export import to_markdown
from pdf_export import to_pdf
from test_export_completeness import ALL_SPECS

BASELINE = pathlib.Path(__file__).with_name("export_baseline.json")


def normalise_pdf(data: bytes) -> bytes:
    data = re.sub(rb"/CreationDate\s*\(D:[^)]*\)", b"/CreationDate (D:X)", data)
    data = re.sub(rb"/ID\s*\[\s*<[0-9a-fA-F]*>\s*<[0-9a-fA-F]*>\s*\]", b"/ID [<X> <X>]", data)
    return data


def sha(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def _hand_resolution(**sheet_over) -> dict:
    from test_pdf_export import _sample_resolution
    res = _sample_resolution()
    res["sheet"].update(sheet_over)
    return res


HAND = {
    "hand-sample": lambda: _hand_resolution(),
    "hand-nameless": lambda: _hand_resolution(name="", classes=[], background=None, species=None),
    "hand-details": lambda: _hand_resolution(details={
        "alignment": "Neutral", "faith": "Tyr", "lifestyle": "Modest", "age": "30", "height": "6ft", "weight": "180",
        "eyes": "green", "skin": "tan", "hair": "black", "personalityTraits": "Brave", "ideals": "Honor",
        "bonds": "Family", "flaws": "Pride", "backstory": "Long story", "organizations": "Guild",
        "allies": "Bob", "enemies": "Eve", "notes": "None"}),
}


@pytest.fixture(scope="module")
def catalog():
    return load()


def outputs(res: dict) -> dict[str, str]:
    return {"markdown": sha(to_markdown(res)), "pdf": sha(normalise_pdf(to_pdf(res))), "yaml": sha(to_yaml(res))}


def _resolution(sid, catalog):
    if sid in HAND:
        return HAND[sid]()
    spec = ALL_SPECS[sid]
    reason = skip_reason(spec)
    if reason:
        pytest.skip(reason)
    draft = build(sid, catalog, resolve) if sid in KITCHEN_SINK else fill(base_draft(spec), catalog, spec["overrides"], resolve)
    return resolve(draft, catalog)


@pytest.mark.parametrize("sid", list(ALL_SPECS) + list(HAND))
def test_default_export_is_byte_identical_to_the_baseline(catalog, sid):
    got = outputs(_resolution(sid, catalog))
    stored = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    if os.environ.get("WRITE_EXPORT_BASELINE"):
        stored[sid] = got
        BASELINE.write_text(json.dumps(stored, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    assert sid in stored, f"no baseline for {sid}"
    assert got == stored[sid], f"{sid}: export bytes changed for {[k for k in got if got[k] != stored[sid][k]]}"
