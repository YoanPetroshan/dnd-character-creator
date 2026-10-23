"""RPX2 (Extra 2, D4): SRD equipment packs weigh the sum of their SRD contents under mixed / 2014.

Governing source: SRD 5.1 / PHB 2014 "Equipment Packs": the packs list a cost and the items inside; no pack has a
weight of its own (the table shows none), so a pack weighs what its contents weigh. The catalog pack records carry
`contents` ([{item: {index}, quantity}]) and `weight: None`; every member exists with a numeric weight.

Rule matrix (lb, member sums verified against the catalog item weights):
  Burglar's 47.5 | Diplomat's 36 | Dungeoneer's 61.5 | Entertainer's 38 | Explorer's 59 | Priest's 18 | Scholar's 10
  mixed / 2014: granted / chosen / added pack entries count that weight in `carryingCapacity.carried` (qty multiplies).
  2024: unchanged, the RP8 PHB-2024 table weights (55 for Explorer's and so on), the SRD sum is never used.
  Only packs with weight None AND complete, numeric contents are computed (other records keep their own weight; a
  pack with an unknown or weightless member is left out rather than guessed).
  Mounts, vessels (weight None, no `contents`) stay 0: not carried gear.
  The catalog item record itself is untouched (weight stays None; contents are not added to the sheet entries).
"""
import pytest

from catalog import reference_data
from catalog.loader import load
from engine import derived
from engine.resolve import resolve

SRD_SUM = {"burglars-pack": 47.5, "diplomats-pack": 36, "dungeoneers-pack": 61.5, "entertainers-pack": 38,
           "explorers-pack": 59, "priests-pack": 18, "scholars-pack": 10}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset="mixed", added=(), cls="fighter", eq=None, sources=()):
    return {
        "ruleset": ruleset, "sources": list(sources),
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": eq or {}, "added": list(added), "skipped": False},
        "classes": [{"classId": cls, "level": 1, "choices": {}}],
    }


def _carried(res):
    return res["derived"]["carryingCapacity"]["carried"]


def test_every_srd_pack_has_no_weight_and_complete_weighted_contents(catalog):
    for pack_id in SRD_SUM:
        rec = catalog.items[pack_id]
        assert rec.get("weight") is None and rec["contents"], pack_id
        for m in rec["contents"]:
            member = catalog.items.get(m["item"]["index"])
            assert member is not None and isinstance(member.get("weight"), (int, float)), (pack_id, m)
            assert isinstance(m["quantity"], int) and m["quantity"] >= 1


def test_pack_weights_are_the_member_sums_and_only_for_packs(catalog):
    weights = derived.pack_weights_from_contents(catalog.items)
    assert weights == SRD_SUM
    assert "saddle-pack" not in weights  # own weight 15, no contents
    assert catalog.items["explorers-pack"].get("weight") is None  # the record itself is untouched


def test_pack_weights_degrade_on_incomplete_contents_and_never_override_a_weight():
    items = {
        "a-pack": {"weight": None, "contents": [{"item": {"index": "x"}, "quantity": 2}, {"item": {"index": "y"}, "quantity": 1}]},
        "x": {"weight": 1.5}, "y": {"weight": 0},
        "ghost-pack": {"weight": None, "contents": [{"item": {"index": "missing"}, "quantity": 1}]},
        "none-pack": {"weight": None, "contents": [{"item": {"index": "z"}, "quantity": 1}]}, "z": {"weight": None},
        "heavy-pack": {"weight": 15, "contents": [{"item": {"index": "x"}, "quantity": 1}]},
        "horse": {"weight": None}, "empty": {"weight": None, "contents": []},
    }
    assert derived.pack_weights_from_contents(items) == {"a-pack": 3}


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
@pytest.mark.parametrize("pack_id,weight", sorted(SRD_SUM.items()))
def test_added_pack_counts_its_contents_weight(catalog, ruleset, pack_id, weight):
    base = resolve(_draft(ruleset), catalog)
    res = resolve(_draft(ruleset, added=[{"itemId": pack_id, "qty": 1, "equipped": False}]), catalog)
    assert _carried(res) - _carried(base) == pytest.approx(weight)
    assert not any("contents" in e for k in ("granted", "chosen", "added") for e in res["sheet"]["equipment"][k])


def test_quantity_multiplies_and_srd_only_sources_agree(catalog):
    for src in ([], ["srd"]):
        res = resolve(_draft(added=[{"itemId": "scholars-pack", "qty": 3, "equipped": False}], sources=src), catalog)
        assert _carried(res) - _carried(resolve(_draft(sources=src), catalog)) == pytest.approx(30)


def test_class_package_pack_counts_under_mixed(catalog):
    """A chosen pack (a class equipment option) counts: every option holding a pack adds exactly its SRD sum."""
    base = resolve(_draft(), catalog)
    seen = {}
    for card in (c for c in base["choices"] if c["id"].startswith("class:fighter:1:equipment-choice")):
        for opt in card["options"]:
            if "pack" not in opt["id"]:
                continue
            alone = resolve(_draft(eq={card["id"]: [opt["id"]]}), catalog)
            chosen = {e["itemId"] for e in alone["sheet"]["equipment"]["chosen"]}
            (pack,) = [i for i in chosen if i in SRD_SUM]
            without = sum((catalog.items[i].get("weight") or 0) * e["qty"]
                          for e in alone["sheet"]["equipment"]["chosen"] for i in [e["itemId"]] if i != pack)
            seen[pack] = _carried(alone) - _carried(base) - without
    assert seen and all(v == pytest.approx(SRD_SUM[k]) for k, v in seen.items()), seen


def test_granted_pack_counts_under_mixed(catalog):
    """A fixed (granted) pack counts: any SRD class that grants one carries at least its SRD sum."""
    found = 0
    for cls in catalog.classes:
        res = resolve(_draft(cls=cls), catalog)
        parts = sum(SRD_SUM[e["itemId"]] * e.get("qty", 1) for e in res["sheet"]["equipment"]["granted"] if e["itemId"] in SRD_SUM)
        if parts:
            found += 1
            assert _carried(res) >= parts, cls
    assert found, "expected at least one class that grants a pack"


def test_2024_keeps_the_phb_table_weights(catalog):
    base = resolve(_draft("2024"), catalog)
    for pack_id, spec in reference_data.PACKS_2024.items():
        res = resolve(_draft("2024", added=[{"itemId": pack_id, "qty": 1, "equipped": False}]), catalog)
        assert _carried(res) - _carried(base) == pytest.approx(spec["weight"]), pack_id
    assert SRD_SUM["explorers-pack"] != reference_data.PACKS_2024["explorers-pack"]["weight"]


def test_mounts_and_vessels_stay_weightless(catalog):
    base = resolve(_draft(), catalog)
    res = resolve(_draft(added=[{"itemId": "mule", "qty": 1, "equipped": False}]), catalog)
    assert _carried(res) == _carried(base)
