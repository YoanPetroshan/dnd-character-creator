"""RPF: 2024-only item weight overrides (PHB 2024 ch. 6 tables vs the SRD records), applied in carried weight.

Compared every item the 2024 packages / backgrounds / packs use (and the weapon, armor, tool and gear tables) with the
catalog: only the loose Rope (SRD 10 lb, PHB 2024 5 lb) and the Warhammer (SRD 2 lb, PHB 2024 5 lb) differ.
  2024: carried weight uses ITEM_WEIGHTS_2024 for those ids; a pack stays at its table weight (contents never summed).
  mixed / 2014: unchanged (SRD weights; the F0 golden covers it)."""
import pytest

from catalog import reference_data
from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _carried(catalog, ruleset, items):
    d = {"ruleset": ruleset, "sources": [],
         "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
         "species": {"id": "human"}, "background": {"id": "acolyte"},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": q, "equipped": False} for i, q in items], "skipped": True},
         "classes": [{"classId": "fighter", "level": 1, "choices": {}}]}
    base = dict(d, equipment={"choices": {}, "added": [], "skipped": True})
    carried = lambda draft: resolve(draft, catalog)["derived"]["carryingCapacity"]["carried"]
    return round(carried(d) - carried(base), 2)  # only the added items (class / background grants cancel out)


def test_table_only_holds_real_differences(catalog):
    assert reference_data.ITEM_WEIGHTS_2024 == {"rope-hempen-50-feet": 5, "warhammer": 5}
    for item_id, w in reference_data.ITEM_WEIGHTS_2024.items():
        assert catalog.items[item_id]["weight"] != w  # an override that equals the catalog would be dead data


def test_rope_and_warhammer_under_2024(catalog):
    assert _carried(catalog, "2024", [("rope-hempen-50-feet", 2)]) == 10
    assert _carried(catalog, "2024", [("warhammer", 1)]) == 5


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_srd_weights_outside_2024(catalog, ruleset):
    assert _carried(catalog, ruleset, [("rope-hempen-50-feet", 2)]) == 20
    assert _carried(catalog, ruleset, [("warhammer", 1)]) == 2


def test_pack_weight_wins_and_is_not_double_counted(catalog):
    assert _carried(catalog, "2024", [("explorers-pack", 1), ("rope-hempen-50-feet", 1)]) == 55 + 5
