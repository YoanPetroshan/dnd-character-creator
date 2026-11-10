"""SHEET-S10 baseline: the fillable sheet's bytes for a fixed set of drafts, both languages, at a fixed creation date.

``sheet_baseline.json`` holds one sha256 per (draft, language) of the RAW bytes of ``to_sheet(..., created=CREATED)`` (the
date is the only time-dependent part and is fixed, so nothing is normalised). The same hashes are checked inside
Pyodide by the offline equivalence test (frontend/src/offline/equivalence.test.mjs, harness.sheets). A change to the layout,
the labels, the data mapping, fpdf2 / pypdf or the fonts moves them: look at the sheets (scripts/dev_sample_sheets.py)
and only then regenerate, on purpose and merge-only (entries of skipped drafts stay):

    WRITE_SHEET_BASELINE=1 pytest tests/test_sheet_baseline.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
from datetime import datetime, timezone

import pytest

import sheet_pdf
from catalog.loader import load
from engine.resolve import resolve
from kitchen_sink import KITCHEN_SINK, base_draft, build, fill, skip_reason
from test_export_baseline import HAND
from test_export_completeness import ALL_SPECS

BASELINE = pathlib.Path(__file__).with_name("sheet_baseline.json")
CREATED = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
LANGS = ("bg", "en")
SHEET_IDS = ("paladin6", "wizard5-2014", "wizard5-2024", "fighter10-2024", "warlock7-2024", "cleric6-paladin3-2014",
             "wizard20-2014", "barbarian20-2014", "sorcerer17-2024", "monk14", "hand-sample", "hand-nameless", "hand-details")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="module")
def catalog():
    return load()


def render(sid, lang, catalog):
    if sid in HAND:
        return sheet_pdf.to_sheet(HAND[sid](), lang, catalog, CREATED, None)
    spec = ALL_SPECS[sid]
    reason = skip_reason(spec)
    if reason:
        pytest.skip(reason)
    draft = build(sid, catalog, resolve) if sid in KITCHEN_SINK else fill(base_draft(spec), catalog, spec["overrides"], resolve)
    return sheet_pdf.to_sheet(resolve(draft, catalog), lang, catalog, CREATED, draft.get("ruleset"))


def test_the_baseline_ids_exist():
    assert all(s in ALL_SPECS or s in HAND for s in SHEET_IDS)


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("sid", SHEET_IDS)
def test_the_sheet_bytes_match_the_baseline(catalog, sid, lang):
    got = sha(render(sid, lang, catalog))
    key = f"{sid}:{lang}"
    stored = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    if os.environ.get("WRITE_SHEET_BASELINE") == "1":
        stored[key] = got  # merge-only: other entries stay
        BASELINE.write_text(json.dumps(stored, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return
    assert key in stored, f"no baseline for {key}"
    assert got == stored[key], f"{key}: the sheet bytes changed"
