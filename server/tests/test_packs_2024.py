"""RP8 (D): 2024 equipment pack contents and carried weight (ruleset 2024 only).

Governing source: Player's Handbook (2024) ch. 6, "Equipment Packs" table (lb.) and the pack item lists. Data is
item ids and numbers (`reference_data.PACKS_2024`), no sentences.

Rule matrix:
  weight (lb): Burglar's 42 | Diplomat's 39 | Dungeoneer's 55 | Entertainer's 58.5 | Explorer's 55 | Priest's 29 | Scholar's 22
  2024: a pack entry (granted / chosen / added) carries `contents` [{itemId, name, qty}]; the pack stays one item;
        carried weight uses the table weight (the SRD pack records weigh nothing).
  mixed / 2014: no `contents`; the weight is the SRD contents sum since RPX2 (tests/test_packs_srd_weights.py).
  every member id exists in the catalog; an unknown pack member is skipped (degrade).
  exports: YAML keeps `contents`; Markdown and PDF print "(съдържа: ...)" after the pack.
"""
import io

import pytest
import yaml
from pypdf import PdfReader

import export_fields
from catalog import reference_data
from catalog.loader import load
from engine import derived
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

TABLE = {"burglars-pack": 42, "diplomats-pack": 39, "dungeoneers-pack": 55, "entertainers-pack": 58.5,
         "explorers-pack": 55, "priests-pack": 29, "scholars-pack": 22}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset="2024", added=(), cls="fighter", eq=None):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": eq or {}, "added": list(added), "skipped": False},
        "classes": [{"classId": cls, "level": 1, "choices": {}}],
    }


def _carried(res):
    return res["derived"]["carryingCapacity"]["carried"]


def _added(res, item):
    return next(e for e in res["sheet"]["equipment"]["added"] if e["itemId"] == item)


def test_table_matches_the_phb_weights_and_every_member_exists(catalog):
    assert {k: v["weight"] for k, v in reference_data.PACKS_2024.items()} == TABLE
    for pack_id, spec in reference_data.PACKS_2024.items():
        assert pack_id in catalog.items
        for item_id, qty in spec["contents"]:
            assert item_id in catalog.items, (pack_id, item_id)
            assert isinstance(qty, int) and qty >= 1


def test_srd_member_weights_differ_from_the_table_and_the_table_wins(catalog):
    """Explorer's: the SRD rope weighs 10 lb, so the member sum (60) is not the table weight (55)."""
    spec = reference_data.PACKS_2024["explorers-pack"]
    member_sum = sum(q * (catalog.items[i].get("weight") or 0) for i, q in spec["contents"])
    assert member_sum != spec["weight"]
    assert catalog.items["explorers-pack"].get("weight") is None


@pytest.mark.parametrize("pack_id,weight", sorted(TABLE.items()))
def test_added_pack_under_2024_has_contents_and_table_weight(catalog, pack_id, weight):
    base = resolve(_draft(), catalog)
    res = resolve(_draft(added=[{"itemId": pack_id, "qty": 1, "equipped": False}]), catalog)
    entry = _added(res, pack_id)
    assert [(c["itemId"], c["qty"]) for c in entry["contents"]] == reference_data.PACKS_2024[pack_id]["contents"]
    assert all(c["name"] == catalog.items[c["itemId"]]["name"] for c in entry["contents"])
    assert _carried(res) - _carried(base) == pytest.approx(weight)
    assert [e["itemId"] for e in res["sheet"]["equipment"]["added"]] == [pack_id]  # not expanded into the inventory


def test_two_packs_double_the_weight(catalog):
    base = resolve(_draft(), catalog)
    res = resolve(_draft(added=[{"itemId": "scholars-pack", "qty": 2, "equipped": False}]), catalog)
    assert _carried(res) - _carried(base) == pytest.approx(44)


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_have_no_contents_and_the_srd_sum_weight(catalog, ruleset):
    base = resolve(_draft(ruleset), catalog)
    res = resolve(_draft(ruleset, added=[{"itemId": "explorers-pack", "qty": 1, "equipped": False}]), catalog)
    assert "contents" not in _added(res, "explorers-pack")
    assert _carried(res) - _carried(base) == 59  # RPX2: the SRD Explorer's Pack weighs its contents' sum (was 0)
    assert not any("contents" in e for k in ("granted", "chosen", "added") for e in res["sheet"]["equipment"][k])


def test_fighter_package_a_dungeoneers_pack_adds_55(catalog):
    cid = "class:fighter:1:equipment-choice-0"
    base = resolve(_draft(), catalog)
    option = next(o["id"] for o in next(c for c in base["choices"] if c["id"] == cid)["options"] if "dungeoneers-pack" in o["id"])
    without_pack_weight = sum(
        (catalog.items[i].get("weight") or 0) * q for i, q in
        [("chain-mail", 1), ("greatsword", 1), ("flail", 1), ("javelin", 8)])
    res = resolve(_draft(eq={cid: [option]}), catalog)
    chosen = {e["itemId"]: e for e in res["sheet"]["equipment"]["chosen"]}
    assert [c["itemId"] for c in chosen["dungeoneers-pack"]["contents"]][:2] == ["backpack", "caltrops"]
    assert _carried(res) - _carried(base) == pytest.approx(without_pack_weight + 55)


def test_derived_weight_override_only_applies_when_given(catalog):
    entries = [{"itemId": "explorers-pack", "qty": 1}]
    assert derived.equipment_weight(entries, catalog.items) == 0
    assert derived.equipment_weight(entries, catalog.items, {"explorers-pack": 55}) == 55
    assert derived.equipment_weight([{"itemId": "dart", "qty": 4}], catalog.items, {"explorers-pack": 55}) == 1


def test_missing_member_is_skipped_and_srd_only_degrades(catalog):
    from engine.resolve import _with_pack_contents
    items = {"explorers-pack": {"name": "Explorer's Pack"}, "backpack": {"name": "Backpack"}}
    out = _with_pack_contents([{"itemId": "explorers-pack", "name": "Explorer's Pack", "qty": 1},
                               {"itemId": "dart", "name": "Dart", "qty": 1}], items)
    assert out[0]["contents"] == [{"itemId": "backpack", "name": "Backpack", "qty": 1}]
    assert "contents" not in out[1]


def _res(catalog):
    return resolve(_draft(added=[{"itemId": "explorers-pack", "qty": 1, "equipped": False}]), catalog)


def test_suffix_helper_text():
    entry = {"contents": [{"itemId": "backpack", "name": "Backpack", "qty": 1}, {"itemId": "oil-flask", "name": "Oil", "qty": 2}]}
    assert export_fields.pack_contents_suffix(entry) == " (съдържа: Backpack, Oil x2)"
    assert export_fields.pack_contents_suffix({}) == ""


def test_markdown_pdf_and_yaml_carry_the_contents(catalog):
    res = _res(catalog)
    suffix = export_fields.pack_contents_suffix(_added(res, "explorers-pack"))
    assert suffix.startswith(" (съдържа: Backpack, Bedroll, ")
    assert "съдържа" in to_markdown(res) and suffix in to_markdown(res)
    text = " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "съдържа: Backpack, Bedroll" in text
    doc = yaml.safe_load(to_yaml(res))
    assert doc["equipment"]["added"][0]["contents"][0] == {"itemId": "backpack", "name": "Backpack", "qty": 1}
