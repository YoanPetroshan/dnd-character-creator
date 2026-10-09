"""Slice 6: starting-equipment envelopes with equipment_category sets and
nested choices inside bundles (expanded in catalog.choices, cascaded in
resolve())."""
import pytest

from catalog.choices import build_equipment_choice, equipment_category_options
from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(class_id="paladin", background="acolyte", equipment_choices=None, **kw):
    draft = {
        "name": "T", "sources": ["srd"],
        "classes": [{"classId": class_id, "level": 1, "choices": {}}],
        "background": {"id": background, "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 15, "DEX": 10, "CON": 14, "INT": 10, "WIS": 12, "CHA": 13}},
        "equipment": {"choices": equipment_choices or {}, "added": [], "skipped": False},
        "details": {},
    }
    draft.update(kw)
    return draft


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


# --- catalog.choices ------------------------------------------------------

def test_category_expansion(catalog):
    ids = {o["id"] for o in equipment_category_options("holy-symbols", catalog.items)}
    assert ids == {"amulet", "emblem", "reliquary"}
    melee = {o["id"] for o in equipment_category_options("martial-melee-weapons", catalog.items)}
    assert "battleaxe" in melee and "longbow" not in melee and "club" not in melee
    assert "lute" in {o["id"] for o in equipment_category_options("musical-instruments", catalog.items)}
    assert equipment_category_options("no-such-category", catalog.items) is None


def test_unresolvable_nested_choice_is_dropped_not_guessed(catalog):
    env = {"choose": 1, "from": {"option_set_type": "options_array", "options": [
        {"option_type": "counted_reference", "count": 1, "of": {"index": "club", "name": "Club"}},
        {"option_type": "choice", "choice": {"desc": "x", "choose": 1, "from": {
            "option_set_type": "equipment_category", "equipment_category": {"index": "nope"}}}},
    ]}}
    tpl, deps = build_equipment_choice(env, "c", {}, "L", catalog.items)
    assert [o["id"] for o in tpl["options"]] == ["club"] and deps == {}


# --- resolve --------------------------------------------------------------

def test_no_equipment_envelope_is_dropped_for_any_srd_class_or_acolyte(catalog):
    for class_id in catalog.classes:
        res = resolve(_draft(class_id), catalog)
        dropped = [w["id"] for w in res["warnings"] if w["id"].startswith("equipment-envelope-dropped")]
        assert dropped == [], class_id
        notes = [c["id"] for c in res["choices"] if c["source"]["kind"] == "equipment" and "aren't available yet" in c["description"]]
        assert notes == [], class_id


def test_paladin_martial_weapon_and_shield_cascade(catalog):
    cid = "class:paladin:1:equipment-choice-0"
    res = resolve(_draft(), catalog)
    parent = _choice(res, cid)
    assert {o["id"] for o in parent["options"]} == {"any-martial-weapons+shield", "any-martial-weapons"}
    assert _choice(res, f"{cid}:0") is None and _choice(res, f"{cid}:1") is None  # nothing selected yet

    res = resolve(_draft(equipment_choices={cid: ["any-martial-weapons+shield"]}), catalog)
    sub = _choice(res, f"{cid}:0")
    assert sub["count"] == 1 and sub["status"] == "pending" and "longsword" in {o["id"] for o in sub["options"]}
    assert _choice(res, f"{cid}:1") is None
    assert res["pruned"] == []

    res = resolve(_draft(equipment_choices={cid: ["any-martial-weapons+shield"], f"{cid}:0": ["longsword"]}), catalog)
    chosen = {e["itemId"] for e in res["sheet"]["equipment"]["chosen"]}
    assert {"shield", "longsword"} <= chosen
    assert res["derived"]["armorClass"] == 18  # chain mail 16 + shield 2


def test_paladin_two_martial_weapons_alternative(catalog):
    cid = "class:paladin:1:equipment-choice-0"
    res = resolve(_draft(equipment_choices={cid: ["any-martial-weapons"], f"{cid}:1": ["longsword", "battleaxe"]}), catalog)
    sub = _choice(res, f"{cid}:1")
    assert sub["count"] == 2 and sub["status"] == "resolved"
    assert _choice(res, f"{cid}:0") is None
    chosen = {e["itemId"] for e in res["sheet"]["equipment"]["chosen"]}
    assert {"longsword", "battleaxe"} <= chosen and "shield" not in chosen
    assert res["derived"]["armorClass"] == 16


def test_stale_subchoice_selection_is_pruned_when_parent_changes(catalog):
    cid = "class:paladin:1:equipment-choice-0"
    res = resolve(_draft(equipment_choices={cid: ["any-martial-weapons"], f"{cid}:0": ["longsword"]}), catalog)
    assert [p["choiceId"] for p in res["pruned"]] == [f"{cid}:0"]


def test_acolyte_holy_symbol_is_offered_and_chosen(catalog):
    cid = "background:acolyte:equipment-choice-0"
    res = resolve(_draft(), catalog)
    assert {o["id"] for o in _choice(res, cid)["options"]} == {"amulet", "emblem", "reliquary"}
    res = resolve(_draft(equipment_choices={cid: ["emblem"]}), catalog)
    assert "emblem" in {e["itemId"] for e in res["sheet"]["equipment"]["chosen"]}


def test_single_nested_pick_options(catalog):
    cid = "class:barbarian:1:equipment-choice-0"
    res = resolve(_draft("barbarian", equipment_choices={cid: ["any-martial-melee-weapons"]}), catalog)
    sub = _choice(res, f"{cid}:0")
    ids = {o["id"] for o in sub["options"]}
    assert "battleaxe" in ids and "longbow" not in ids
    parent = _choice(res, cid)
    assert {o["id"] for o in parent["options"]} == {"greataxe", "any-martial-melee-weapons"}


def test_flat_category_envelopes(catalog):
    res = resolve(_draft("cleric"), catalog)
    holy = [c for c in res["choices"] if c["source"]["kind"] == "equipment" and {"amulet", "emblem"} <= {o["id"] for o in c["options"]}]
    assert len(holy) >= 2  # the class's holy symbol and Acolyte's
