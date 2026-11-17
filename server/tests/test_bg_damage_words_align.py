"""S07 (audit I18N-02, Q3 = B): the Bulgarian exports keep the English damage types and words ("slashing", "off hand",
"versatile", "range"); the fillable sheet is aligned to them instead of the other way round, so one language no longer has
two spellings of the same thing.

Known and left as it is (it would move export_baseline.json): the Rage row of a class resource still writes its damage
types with the Bulgarian words in the Markdown / PDF / sheet alike (`resource_detail_parts`), so it agrees with itself."""
from __future__ import annotations

import re

import pytest

import export_fields
import sheet_data
from catalog.loader import load
from engine.resolve import resolve
from export_fields import extra_blocks
from kitchen_sink import KITCHEN_SINK, build, skip_reason
from markdown_export import to_markdown

CYRILLIC = re.compile("[Ѐ-ӿ]")
IDS = [i for i in ("barbarian20-2014", "fighter10-2024", "paladin6", "warlock7-2024", "sorcerer17-2024") if i in KITCHEN_SINK]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _resolution(sid, catalog):
    if skip_reason(KITCHEN_SINK[sid]):
        pytest.skip("data missing")
    return resolve(build(sid, catalog, resolve), catalog)


@pytest.mark.parametrize("sid", IDS)
def test_the_sheet_weapon_damage_cells_use_the_english_damage_type_like_the_markdown(catalog, sid):
    res = _resolution(sid, catalog)
    md = to_markdown(res, "bg")
    for name, _bonus, damage, _notes in sheet_data._weapon_rows(res, catalog, "bg"):
        if not damage:
            continue
        assert not CYRILLIC.search(damage), (sid, name, damage)
    for a in res["derived"].get("attacks") or []:
        if a.get("damage") and a.get("damageType"):
            assert f"{a['damage']} {a['damageType']}" in md  # the Markdown line, as before
            rows = {r[0]: r for r in sheet_data._weapon_rows(res, catalog, "bg")}
            assert rows[a["name"]][2] == f"{a['damage']} {a['damageType']}"


@pytest.mark.parametrize("sid", IDS)
def test_the_sheet_and_the_markdown_write_the_resistance_block_the_same_way(catalog, sid):
    res = _resolution(sid, catalog)
    sheet = res["sheet"]
    from_sheet = sheet_data._defenses(sheet, "bg")
    from_blocks = [text for kind, text in extra_blocks(res, "bg") if kind == "bullet" and ": " in text
                   and any(text.startswith(export_fields.label("bg", k) + ":") for k in ("dmgResistances", "dmgImmunities", "dmgVulnerabilities", "conditionImmunities"))]
    assert from_sheet == from_blocks


def test_a_bulgarian_sheet_cantrip_names_its_damage_type_in_english(catalog):
    res = _resolution("warlock7-2024", catalog)
    rows = sheet_data._weapon_rows(res, catalog, "bg")
    eldritch = [r for r in rows if "Eldritch Blast" in r[0] or "eldritch" in r[0].lower()]
    assert eldritch, [r[0] for r in rows]
    assert all(not CYRILLIC.search(r[2]) and "force" in r[2] for r in eldritch), eldritch


@pytest.mark.parametrize("sid", IDS)
def test_the_english_sheet_is_unchanged_by_the_alignment(catalog, sid):
    res = _resolution(sid, catalog)
    for _name, _b, damage, _n in sheet_data._weapon_rows(res, catalog, "en"):
        assert not CYRILLIC.search(damage)
