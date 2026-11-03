"""RPX3 (Extra 3, D4): the counts of the starting-equipment text under mixed / 2014 (they were qty 1; E8 limited
counts to the 2024 packages).

Governing text: the `desc` of every SRD class equipment envelope (and the 5etools background equipment lines), read
from the catalog in `test_rule_text_is_pinned`. The data keeps the counts (`counted_reference.count`), the converter
used to drop them for every ruleset but 2024.

Rule matrix (SRD classes, level 1, the option that holds the phrase -> catalog item: qty):
  Barbarian  "(a) two handaxes or (b) any simple weapon"       -> handaxe: 2
  Fighter    "(a) a light crossbow and 20 bolts or (b) two handaxes" -> handaxe: 2; the bolts stay ONE pack
  Paladin    "(a) five javelins or (b) any simple melee weapon" -> javelin: 5
  Ranger     "(a) two shortswords or (b) two simple melee weapons" -> shortsword: 2
  Ammunition ("20 arrows", "20 bolts" of Cleric / Fighter / Rogue / Sorcerer / Warlock): the catalog `arrow` /
             `crossbow-bolt` are already 20-packs (item `quantity` 20, F3a-6), so the phrase is ONE unit, like the
             2024 packages. Never 20 (that would be 400 arrows and 20 lb).
  Fixed starting equipment (no choice): Barbarian four javelins (4), Monk 10 darts (10), Rogue / Sorcerer two daggers
             (2) are already right; the Ranger's fixed 20 arrows was qty 20 (a 400-arrow stack) and is now ONE pack.
  Weight (`carryingCapacity.carried`) and the inventory follow the quantity; option ids and card ids do NOT change
  (a stored pick survives); the 2024 packages are untouched (their quantities and ids are the C9b / RP9 ones).
"""
import pytest

from catalog import choices as choices_mod
from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

# (class, card id, option id, item, qty, quoted phrase of the card description)
OPTIONS = [
    ("barbarian", "class:barbarian:1:equipment-choice-1", "handaxe", "handaxe", 2, "two handaxes"),
    ("fighter", "class:fighter:1:equipment-choice-2", "handaxe", "handaxe", 2, "two handaxes"),
    ("paladin", "class:paladin:1:equipment-choice-1", "javelin", "javelin", 5, "five javelins"),
    ("ranger", "class:ranger:1:equipment-choice-1", "shortsword", "shortsword", 2, "two shortswords"),
]
AMMO_BUNDLES = [  # (class, card id, the 20-ammo bundle option id, ammo item, quoted phrase)
    ("fighter", "class:fighter:1:equipment-choice-0", "leather-armor+longbow+arrow", "arrow", "20 arrows"),
    ("fighter", "class:fighter:1:equipment-choice-2", "crossbow-light+crossbow-bolt", "crossbow-bolt", "20 bolts"),
    ("cleric", "class:cleric:1:equipment-choice-2", "crossbow-light+crossbow-bolt", "crossbow-bolt", "20 bolts"),
    ("sorcerer", "class:sorcerer:1:equipment-choice-0", "crossbow-light+crossbow-bolt", "crossbow-bolt", "20 bolts"),
    ("warlock", "class:warlock:1:equipment-choice-0", "crossbow-light+crossbow-bolt", "crossbow-bolt", "20 bolts"),
    ("rogue", "class:rogue:1:equipment-choice-1", "shortbow+arrow", "arrow", "20 arrows"),
]
FIXED = [("barbarian", "javelin", 4), ("monk", "dart", 10), ("rogue", "dagger", 2), ("sorcerer", "dagger", 2),
         ("warlock", "dagger", 2), ("ranger", "arrow", 1)]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls, eq=None, ruleset="mixed", sources=()):
    return {
        "ruleset": ruleset, "sources": list(sources),
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": eq or {}, "added": [], "skipped": False},
        "classes": [{"classId": cls, "level": 1, "choices": {}}],
    }


def _card(res, cid):
    return next(c for c in res["choices"] if c["id"] == cid)


def _chosen(res):
    return {e["itemId"]: e for e in res["sheet"]["equipment"]["chosen"]}


def _carried(res):
    return res["derived"]["carryingCapacity"]["carried"]


@pytest.mark.parametrize("cls,cid,opt,item,qty,phrase", OPTIONS)
def test_rule_text_is_pinned(catalog, cls, cid, opt, item, qty, phrase):
    card = _card(resolve(_draft(cls), catalog), cid)
    assert phrase in card["description"], card["description"]
    assert catalog.items[item]["weight"] is not None


@pytest.mark.parametrize("cls,cid,phrase", sorted({(c, i, p) for c, i, _o, _it, p in AMMO_BUNDLES}))
def test_ammunition_phrase_is_pinned(catalog, cls, cid, phrase):
    assert phrase in _card(resolve(_draft(cls), catalog), cid)["description"]


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
@pytest.mark.parametrize("sources", [(), ("srd",)])
@pytest.mark.parametrize("cls,cid,opt,item,qty,phrase", OPTIONS)
def test_counted_option_has_quantity_inventory_and_weight(catalog, ruleset, sources, cls, cid, opt, item, qty, phrase):
    base = resolve(_draft(cls, ruleset=ruleset, sources=sources), catalog)
    option = next(o for o in _card(base, cid)["options"] if o["id"] == opt)
    assert option["quantities"] == {item: qty}
    assert option["label"].startswith(f"{qty}x ")
    res = resolve(_draft(cls, {cid: [opt]}, ruleset, sources), catalog)
    entry = _chosen(res)[item]
    assert entry["qty"] == qty
    assert _carried(res) - _carried(base) == pytest.approx(qty * catalog.items[item]["weight"])
    assert _card(res, cid)["status"] == "resolved" and not res["pruned"]


@pytest.mark.parametrize("cls,cid,opt,ammo,phrase", AMMO_BUNDLES)
def test_twenty_ammunition_is_one_pack_not_twenty(catalog, cls, cid, opt, ammo, phrase):
    assert catalog.items[ammo]["quantity"] == 20
    base = resolve(_draft(cls), catalog)
    option = next(o for o in _card(base, cid)["options"] if o["id"] == opt)
    assert ammo not in option.get("quantities", {})
    res = resolve(_draft(cls, {cid: [opt]}), catalog)
    assert _chosen(res)[ammo]["qty"] == 1


def test_no_srd_option_carries_an_ammunition_quantity(catalog):
    for cls in catalog.classes:
        res = resolve(_draft(cls), catalog)
        for card in res["choices"]:
            for o in card.get("options", []):
                assert not {"arrow", "crossbow-bolt", "sling-bullet", "blowgun-needle"} & set(o.get("quantities", {})), (cls, card["id"])


@pytest.mark.parametrize("cls,item,qty", FIXED)
def test_fixed_starting_equipment_quantities(catalog, cls, item, qty):
    res = resolve(_draft(cls), catalog)
    granted = {e["itemId"]: e for e in res["sheet"]["equipment"]["granted"]}
    assert granted[item]["qty"] == qty


def test_ranger_fixed_arrows_weigh_one_pack(catalog):
    res = resolve(_draft("ranger"), catalog)
    granted = {e["itemId"]: e for e in res["sheet"]["equipment"]["granted"]}
    assert granted["arrow"]["qty"] == 1 and catalog.items["arrow"]["weight"] == 1


def test_option_and_card_ids_do_not_change_so_a_stored_pick_survives(catalog):
    """The quantity lives next to the id; picks made before RPX3 resolve to the same option."""
    cid = "class:fighter:1:equipment-choice-2"
    res = resolve(_draft("fighter", {cid: ["handaxe"]}), catalog)
    assert _card(res, cid)["selected"] == ["handaxe"] and _chosen(res)["handaxe"]["qty"] == 2


def test_pack_units_rule():
    arrow = {"quantity": 20}
    assert choices_mod.pack_units(arrow, 20) == 1 and choices_mod.pack_units(arrow, 40) == 2
    assert choices_mod.pack_units(arrow, 25) == 2 and choices_mod.pack_units(arrow, 5) == 1  # rounds up, never 0
    assert choices_mod.pack_units({"quantity": None}, 4) == 4 and choices_mod.pack_units({}, 4) == 4
    assert choices_mod.pack_units(None, 3) == 3
    assert choices_mod.pack_quantities({"arrow": 20, "handaxe": 2}, {"arrow": arrow, "handaxe": {}}) == {"handaxe": 2}


@needs_official
def test_background_counts_follow_the_text_under_mixed(catalog):
    """A 5etools background keeps its counts under mixed too (Criminal XPHB: two daggers, two pouches)."""
    cid = "background:criminal-xphb:equipment-choice-0"
    d = _draft("fighter")
    d["background"] = {"id": "criminal-xphb"}
    base = resolve(d, catalog)
    option = next(o for o in _card(base, cid)["options"] if o["quantities"] if "dagger" in o["quantities"])
    assert option["quantities"] == {"dagger": 2, "pouch": 2}
    d["equipment"]["choices"] = {cid: [option["id"]]}
    res = resolve(d, catalog)
    assert _chosen(res)["dagger"]["qty"] == 2 and _chosen(res)["pouch"]["qty"] == 2


@needs_official
def test_2024_packages_are_untouched(catalog):
    """The C9b quantities (Fighter A: four? handaxes / javelins) keep their ids and counts under 2024."""
    cid = "class:fighter:1:equipment-choice-0"
    base = resolve(_draft("fighter", ruleset="2024"), catalog)
    opts = {o["id"]: o.get("quantities") for o in _card(base, cid)["options"]}
    assert {"handaxe": 2} in opts.values() or {"javelin": 8} in opts.values()
    for oid, q in opts.items():
        res = resolve(_draft("fighter", {cid: [oid]}, ruleset="2024"), catalog)
        for item, n in (q or {}).items():
            assert _chosen(res)[item]["qty"] == n
