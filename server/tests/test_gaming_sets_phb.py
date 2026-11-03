"""RPX4 (Extra 4, D4): all four PHB gaming sets in the catalog and on every gaming-set card.

Governing source: Player's Handbook (2014) ch. 5, "Tools" table (p. 154), Gaming set: Dice set 1 sp, Dragonchess
set 1 gp (1/2 lb.), Playing card set 5 sp, Three-Dragon Ante set 1 gp; every other gaming set weighs nothing. The PHB
2024 Tools table has the same four sets. The SRD record of the Dice Set names Three-Dragon Ante as an example
("games such as Three-Dragon Ante"), pinned below. The local 5etools data holds no gaming-set item (only the
`Gaming Set` item type in items-base.json), so the two missing records come from the PHB table
(`reference_data.PHB_GAMING_SETS`).

Rule matrix:
  catalog.items: dice-set (SRD) | dragonchess-set (PHB, 1 gp, 0.5 lb) | playing-card-set (SRD) |
                 three-dragon-ante-set (PHB, 1 gp, 0 lb), all `tool_category` "Gaming Sets", in every ruleset
                 and for sources [] and ["srd"] (the catalog is ruleset- and source-independent).
  tool table (`reference_data.TOOLS`, the tool-proficiency cards): the same four ids, same category, same order.
  every gaming-set card offers exactly those four: background tool proficiency picks (Noble PHB "any gaming set",
  Carouser ABH), the 2024 Wayfarer nested equipment card, the Skilled feat's "any skill or tool" list, under
  mixed / 2014 / 2024.
  a picked set is the proficiency (`sheet.proficiencies.tools`) and, through the RP9 sentinel, the inventory item
  with its own weight (Dragonchess +0.5 lb, Three-Dragon Ante +0 lb).
  Degrade: a catalog without the extra items (patched) drops only them from item-backed cards.
"""
import pytest

from catalog import reference_data
from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

FOUR = ["dice-set", "dragonchess-set", "playing-card-set", "three-dragon-ante-set"]
PHB = {  # id: (cost quantity, unit, weight lb)
    "dice-set": (1, "sp", 0), "dragonchess-set": (1, "gp", 0.5),
    "playing-card-set": (5, "sp", 0), "three-dragon-ante-set": (1, "gp", 0),
}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(background="acolyte", ruleset="mixed", sources=(), eq=None, bg_choices=None, cls="fighter"):
    return {
        "ruleset": ruleset, "sources": list(sources),
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": background, "choices": bg_choices or {}},
        "equipment": {"choices": eq or {}, "added": [], "skipped": False},
        "classes": [{"classId": cls, "level": 1, "choices": {}}],
    }


def test_srd_record_names_three_dragon_ante_as_an_example(catalog):
    assert "Three-Dragon Ante" in " ".join(catalog.items["dice-set"]["desc"])


def test_catalog_items_and_tool_table_agree_on_the_four_sets(catalog):
    items = [k for k, v in catalog.items.items() if v.get("tool_category") == "Gaming Sets"]
    assert items == FOUR  # alphabetical, like the PHB table
    tools = [t["index"] for t in reference_data.TOOLS if t["category"] == "Gaming Sets"]
    assert tools == FOUR
    assert {t["index"]: t["name"] for t in reference_data.TOOLS if t["category"] == "Gaming Sets"} == {
        k: catalog.items[k]["name"] for k in FOUR}
    assert [catalog.items[k]["name"] for k in FOUR] == ["Dice Set", "Dragonchess Set", "Playing Card Set", "Three-Dragon Ante Set"]


@pytest.mark.parametrize("item_id,expect", sorted(PHB.items()))
def test_cost_weight_and_shape_match_the_phb_table(catalog, item_id, expect):
    item = catalog.items[item_id]
    assert (item["cost"]["quantity"], item["cost"]["unit"], item["weight"]) == expect
    assert item["equipment_category"]["index"] == "tools" and item["index"] == item_id and item["desc"]
    assert item["source"] in ("SRD", "PHB") and item["ruleset"] == "2014"


def test_srd_records_are_untouched_and_the_new_ones_are_phb(catalog):
    assert catalog.items["dice-set"]["source"] == "SRD" and catalog.items["playing-card-set"]["source"] == "SRD"
    assert catalog.items["dragonchess-set"]["source"] == "PHB" and catalog.items["three-dragon-ante-set"]["source"] == "PHB"


def _gaming_cards(res):
    return [c for c in res["choices"] if set(FOUR) & {o["id"] for o in c.get("options", [])}]


@needs_official
@pytest.mark.parametrize("sources", [(), ("srd", "phb")])
@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_every_background_gaming_card_offers_exactly_the_four(catalog, ruleset, sources):
    seen = 0
    for bg_id, bg in catalog.backgrounds.items():
        if not reference_data.ruleset_allows(bg, "background", ruleset):
            continue
        res = resolve(_draft(bg_id, ruleset, sources), catalog)
        for card in _gaming_cards(res):
            ids = [o["id"] for o in card["options"]]
            if card["id"] == "background:soldier-phb:equipment-choice-0":  # the PHB text itself: "bone dice or deck of cards"
                assert ids == ["dice-set", "playing-card-set"]
                continue
            assert ids == FOUR or set(ids) > set(FOUR), (bg_id, card["id"], ids)  # catalog-wide "any tool" is a superset
            if card["source"]["kind"] == "background" and "proficiency-choice" in card["id"] and set(ids) <= set(FOUR):
                seen += 1
    assert seen >= 1


@needs_official
def test_noble_gaming_set_pick_offers_all_four_and_grants_the_proficiency(catalog):
    res = resolve(_draft("noble-phb", sources=("phb",)), catalog)
    card = next(c for c in res["choices"] if c["id"].startswith("background:noble-phb:") and "proficiency-choice" in c["id"])
    assert [o["id"] for o in card["options"]] == FOUR
    res = resolve(_draft("noble-phb", sources=("phb",), bg_choices={card["id"]: ["dragonchess-set"]}), catalog)
    assert "dragonchess-set" in res["sheet"]["proficiencies"]["tools"] and res["problems"] == []


@needs_official
def test_wayfarer_2024_nested_card_offers_all_four_and_the_pick_is_the_item(catalog):
    cid = "background:wayfarer-xphb:equipment-choice-0"
    res = resolve(_draft("wayfarer-xphb", "2024"), catalog)
    a = next(o["id"] for o in next(c for c in res["choices"] if c["id"] == cid)["options"] if o["id"] != "gp-50")
    res = resolve(_draft("wayfarer-xphb", "2024", eq={cid: [a]}), catalog)
    nested = next(c for c in res["choices"] if c["id"] == cid + ":0")
    assert [o["id"] for o in nested["options"]] == FOUR
    base = res["derived"]["carryingCapacity"]["carried"]
    for item_id, (_q, _u, weight) in PHB.items():
        r = resolve(_draft("wayfarer-xphb", "2024", eq={cid: [a], cid + ":0": [item_id]}), catalog)
        chosen = {e["itemId"]: e for e in r["sheet"]["equipment"]["chosen"]}
        assert chosen[item_id]["qty"] == 1 and r["problems"] == []
        assert r["derived"]["carryingCapacity"]["carried"] - base == pytest.approx(weight)


@needs_official
def test_soldier_2024_same_as_above_gaming_set_is_the_picked_dragonchess_set(catalog):
    cid = "background:soldier-xphb:equipment-choice-0"
    prof = next(c["id"] for c in resolve(_draft("soldier-xphb", "2024"), catalog)["choices"]
                if c["id"].startswith("background:soldier-xphb:") and "proficiency-choice" in c["id"])
    base = resolve(_draft("soldier-xphb", "2024", bg_choices={prof: ["dice-set"]}), catalog)
    a = next(o["id"] for o in next(c for c in base["choices"] if c["id"] == cid)["options"] if o["id"] != "gp-50")
    res = resolve(_draft("soldier-xphb", "2024", eq={cid: [a]}, bg_choices={prof: ["dragonchess-set"]}), catalog)
    chosen = {e["itemId"]: e for e in res["sheet"]["equipment"]["chosen"]}
    assert "dragonchess-set" in chosen and "dice-set" not in chosen
    assert "dragonchess-set" in res["sheet"]["proficiencies"]["tools"]


def test_skill_or_tool_and_any_tool_option_sets_have_the_four():
    """The Skilled feat ("any 3 from skills or tools") and every tool-category-less `any_tool` list."""
    from catalog import choices as choices_mod
    for from_field in ({"option_set_type": "any_skill_or_tool"}, {"option_set_type": "any_tool"},
                       {"option_set_type": "any_tool", "tool_category": "Gaming Sets"}):
        ids = [o["id"] for o in choices_mod.build_choice_options(from_field)]
        assert [i for i in ids if i in FOUR] == FOUR, from_field


def test_api_items_lists_the_new_sets_for_every_ruleset():
    import app as app_mod
    client = app_mod.app.test_client()
    for ruleset in ("mixed", "2014", "2024"):
        rows = client.get(f"/api/items?category=tools&q=set&ruleset={ruleset}").get_json()["items"]
        assert {r["id"] for r in rows} >= {"dragonchess-set", "three-dragon-ante-set"}, ruleset


@needs_official
def test_patched_catalog_without_the_extra_sets_degrades(catalog):
    patched = load()
    for k in ("dragonchess-set", "three-dragon-ante-set"):
        patched.items.pop(k)
    res = resolve(_draft("wayfarer-xphb", "2024"), patched)
    assert res["problems"] == []
    cid = "background:wayfarer-xphb:equipment-choice-0"
    a = next(o["id"] for o in next(c for c in res["choices"] if c["id"] == cid)["options"] if o["id"] != "gp-50")
    nested = next(c for c in resolve(_draft("wayfarer-xphb", "2024", eq={cid: [a]}), patched)["choices"] if c["id"] == cid + ":0")
    assert [o["id"] for o in nested["options"]] == ["dice-set", "playing-card-set"]
