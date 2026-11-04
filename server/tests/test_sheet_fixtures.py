"""SK5: fixture resolutions for the frontend sheet tests.

`frontend/src/__fixtures__/<id>.json` are dumps of kitchen-sink resolutions (the `sheetSections` vitest tests read
them). The committed files must equal a fresh dump, like the types-drift and golden guards; regenerate them with

    SHEET_FIXTURES_REGEN=1 python -m pytest tests/test_sheet_fixtures.py

A fixture is ``{"id", "ruleset", "base", "resolution"}``: ``base`` is the draft's base ability scores (the Abilities
columns need it), ``resolution`` is resolve()'s output with ``choices`` emptied (the sheet does not read the choice
cards; the lists are large).
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest

from catalog.loader import load
from engine.resolve import resolve
from kitchen_sink import KITCHEN_SINK, build, skip_reason

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "__fixtures__"
FIXTURE_IDS = ["warlock7-2024", "bard10-2014", "fighter4-2024", "wizard20-2024", "rogue6-2024"]


def dump(sid: str, catalog) -> str:
    draft = build(sid, catalog, resolve)
    res = resolve(draft, catalog)
    doc = {
        "id": sid,
        "ruleset": draft["ruleset"],
        "base": draft["abilities"]["base"],
        "resolution": {**res, "choices": []},
    }
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n"


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.mark.parametrize("sid", FIXTURE_IDS)
def test_fixture_is_a_known_kitchen_sink_draft(sid):
    assert sid in KITCHEN_SINK


@pytest.mark.parametrize("sid", FIXTURE_IDS)
def test_committed_fixture_equals_a_fresh_dump(catalog, sid):
    reason = skip_reason(KITCHEN_SINK[sid])
    if reason:
        pytest.skip(reason)
    path = FIXTURE_DIR / f"{sid}.json"
    fresh = dump(sid, catalog)
    if os.environ.get("SHEET_FIXTURES_REGEN") == "1":
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(fresh, encoding="utf-8")
    assert path.exists(), f"missing fixture {path.name}: run with SHEET_FIXTURES_REGEN=1"
    assert path.read_text(encoding="utf-8") == fresh, (
        f"{path.name} is stale: regenerate with SHEET_FIXTURES_REGEN=1 python -m pytest tests/test_sheet_fixtures.py"
    )


def test_every_fixture_file_is_committed_and_parses():
    """Independent of the 5etools data: the files exist and have the documented shape."""
    for sid in FIXTURE_IDS:
        doc = json.loads((FIXTURE_DIR / f"{sid}.json").read_text(encoding="utf-8"))
        assert doc["id"] == sid and set(doc["base"]) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
        assert {"sheet", "derived"} <= set(doc["resolution"]) and doc["resolution"]["choices"] == []
    on_disk = {p.stem for p in FIXTURE_DIR.glob("*.json")}
    assert on_disk == set(FIXTURE_IDS), on_disk ^ set(FIXTURE_IDS)
