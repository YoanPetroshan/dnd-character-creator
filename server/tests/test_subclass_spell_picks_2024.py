"""RP17 (F3, E13): 2024 subclass spell picks - the Savants, Improved Illusions, Magical Discoveries and the Circle of the
Land spell table. Ruleset "2024" only; mixed / 2014 are unchanged.

Governing texts (catalog.features, XPHB records; `reference_data.SUBCLASS_SPELL_PICKS_2024` and the Land entry of
`SUBCLASS_OPTIONS_2024` carry verbatim quotes, pinned by `test_quotes_match_catalog`):
  Abjuration / Divination / Evocation / Illusion Savant (Wizard 3)
      "Choose two Wizard spells from the <School> school, each of which must be no higher than level 2, and add them
      to your spellbook for free." / "whenever you gain access to a new level of spell slots in this class, you can add
      one Wizard spell from the <School> school to your spellbook for free. The chosen spell must be of a level for
      which you have spell slots."
  Improved Illusions (Illusionist 3)
      "You also know the Minor Illusion cantrip. If you already know it, you learn a different Wizard cantrip of your
      choice. The cantrip doesn't count against your number of cantrips known."
  Magical Discoveries (Lore Bard 6)
      "You learn two spells of your choice. These spells can come from the Cleric, Druid, or Wizard spell list or any
      combination thereof ... A spell you choose must be a cantrip or a spell for which you have spell slots, as shown
      in the Bard Features table. You always have the chosen spells prepared, ..."
  Circle of the Land Spells (Druid 3) / Nature's Ward (Druid 10)
      "Whenever you finish a Long Rest, choose one type of land: arid, polar, temperate, or tropical. ... you have the
      spells listed for your Druid level and lower prepared." / "You are immune to the Poisoned condition, and you have
      Resistance to a damage type associated with your current land choice in the Circle Spells feature, as shown in the
      Nature's Ward table." (Arid Fire, Polar Cold, Temperate Lightning, Tropical Poison)

Rule matrix:
  Savant card      `class:wizard:3:feature:<savant fid>`; count = filter entries reached: 2 at Wizard 3, +1 at 5 / 7 / 9 / 11
                   / 13 / 15 / 17 (the levels that open a new slot level); options = Wizard spells of the school, levels
                   1 .. min(highest Wizard slot level, the filters' levels) (the 2024 spellbook is level 1+, C4); the
                   `sources` filter applies; a spell in the effective spellbook is disabled "already in your spellbook"
                   and the book card disables a Savant pick ("chosen as ..."); the picks do not use the book's count
  Savant effect    valid picks join the effective book: sheet.spells[wizard].spellbook, the prepared card's options, the
                   Spell Mastery / Signature Spells options; removing the subclass or a level prunes without blocking
  Improved Illus.  the card exists only when Minor Illusion is already known elsewhere (Cantrips Known card, a feat
                   cantrip card, species / feat innate spells); it offers the other Wizard cantrips, never counts against
                   the cantrips known, is listed under the cantrips, and Minor Illusion is then not listed twice
  Discoveries      count 2 at Lore 6; Cleric / Druid / Wizard spells, level 0 .. the highest BARD slot level; always
                   prepared (alwaysPrepared, disabled on the Bard's own cards, reason "Magical Discoveries")
  Land             one required card (4 options); the picked land's spells at Druid 3 / 5 / 7 / 9 are always prepared;
                   unpicked: none; Nature's Ward (10): Poisoned immunity always, Resistance of the picked land only
  gates            2024 only; none below the record's level, without the subclass, with an SRD-only catalog or a catalog
                   without the converter keys; an empty card is `unavailable` (never blocks export)"""
from perf_helpers import assert_fast, measure
import copy
import time

import pytest

from catalog import official_source, reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import subclass_spells_2024
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

BOOK, PREPARED, CANTRIPS = "class:wizard:spellbook", "class:wizard:spells-known", "class:wizard:spells-cantrips"
MASTERY1, MASTERY2 = "class:wizard:18:spell-mastery-1", "class:wizard:18:spell-mastery-2"
SIGNATURE = "class:wizard:20:signature-spells"
SAVANT = {
    "abjurer-xphb": ("class:wizard:3:feature:abjurer-xphb-3-abjuration-savant", "abjuration"),
    "diviner-xphb": ("class:wizard:3:feature:diviner-xphb-3-divination-savant", "divination"),
    "evoker-xphb": ("class:wizard:3:feature:evoker-xphb-3-evocation-savant", "evocation"),
    "illusionist-xphb": ("class:wizard:3:feature:illusionist-xphb-3-illusion-savant", "illusion"),
}
EVO = SAVANT["evoker-xphb"][0]
IMPROVED = "class:wizard:3:feature:illusionist-xphb-3-improved-illusions"
DISCOVERIES = "class:bard:6:feature:lore-xphb-6-magical-discoveries"
LAND = "class:druid:3:feature:land-xphb-3-circle-of-the-land-spells"
LAND_FID = "land-xphb-3-circle-of-the-land-spells"
MI_CANTRIP = "feat:magic-initiate-xphb:spell-choice-5"  # the Magic Initiate (Wizard) cantrip card (two) of the Sage background
MI_VARIANT = {"feat:magic-initiate-xphb:spell-variant": ["wizard-spells"]}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", sources=(), background="sage-xphb", bg_choices=None, species=None, int_=16):
    """classes: (classId, level, subclassId | None, {cid: [picks]})."""
    entries = []
    for cls_id, level, sub, choices in classes:
        e = {"classId": cls_id, "level": level, "choices": choices}
        if sub:
            e["subclassId"] = sub
        entries.append(e)
    return {
        "ruleset": ruleset, "sources": list(sources),
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 12, "INT": int_, "WIS": 12, "CHA": 14}},
        "species": species or {"id": "human-xphb"},
        "background": {"id": background, "choices": bg_choices or {}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": entries,
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, sid):
    return next((o for o in card["options"] if o["id"] == sid), None)


def _enabled(card):
    return [o["id"] for o in card["options"] if not o.get("disabled")]


def _entry(res, cls="wizard"):
    return next((e for e in res["sheet"]["spells"] if e["classId"] == cls), None)


def _ids(rows):
    return [r["id"] for r in rows]


def _pruned(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


def _wizard(level, sub, picks=None):
    return ("wizard", level, sub, dict(picks or {}))


def _book(catalog, level, sub, n=None, skip=(), **kw):
    """The first `n` (default: all) enabled book options at this level, so a draft can fill the spellbook card."""
    res = _res(catalog, [_wizard(level, sub)], **kw)
    card = _card(res, BOOK)
    ids = [i for i in _enabled(card) if i not in skip]
    return ids[: n or card["count"]]


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if "-xphb-" not in k}
    return bare


# ---- data -----------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    table = reference_data.SUBCLASS_SPELL_PICKS_2024
    assert set(table) == {
        "abjurer-xphb-3-abjuration-savant", "diviner-xphb-3-divination-savant", "evoker-xphb-3-evocation-savant",
        "illusionist-xphb-3-illusion-savant", "illusionist-xphb-3-improved-illusions", "lore-xphb-6-magical-discoveries"}
    for fid, spec in table.items():
        rec = catalog.features[fid]
        text = "\n".join(rec["desc"])
        assert rec["source"] == "XPHB"
        assert (rec["subclass"] or {}).get("index") == spec["subclass"], fid
        assert (rec["class"] or {}).get("index") == spec["class"], fid
        for q in spec["quotes"]:
            assert q in text, (fid, q)
        if spec["kind"] == "savant":
            assert f"from the {spec['school'].title()} school" in spec["quotes"][0]
    land = reference_data.SUBCLASS_OPTIONS_2024[LAND_FID]
    rec = catalog.features[LAND_FID]
    text = "\n".join(rec["desc"])
    for q in land["quotes"]:
        assert q in text
    ward = catalog.features[land["ward"]["feature"]]
    ward_text = "\n".join(ward["desc"])
    for q in land["ward"]["quotes"]:
        assert q in ward_text
    for key, o in land["options"].items():
        assert o["quote"] in text and o["ward_quote"] in ward_text, key
        assert o["ward_resist"] in ("fire", "cold", "lightning", "poison")


@needs_data
def test_converter_keeps_the_savant_filters_and_the_slot_level_rhythm(catalog):
    for sub_id, (cid, school) in SAVANT.items():
        entries = catalog.subclasses[sub_id]["spell_choices"]
        known = [e for e in entries if e["mode"] == "known"]
        assert [e["level"] for e in known] == [3, 3, 5, 7, 9, 11, 13, 15, 17], sub_id
        assert all(e["filter"]["school"] == [school] and e["filter"]["class"] == ["wizard"] for e in known)
        assert known[0]["filter"]["level"] == [0, 1, 2] and known[-1]["filter"]["level"] == list(range(10))
    # the level at which a new slot level opens is the level of every extra pick
    rows = catalog.class_level_row
    opens = [lv for lv in range(2, 21)
             if max(n for n in range(1, 10) if (rows("wizard", lv)["spellcasting"].get(f"spell_slots_level_{n}") or 0) > 0)
             > max(n for n in range(1, 10) if (rows("wizard", lv - 1)["spellcasting"].get(f"spell_slots_level_{n}") or 0) > 0)]
    assert opens == [3, 5, 7, 9, 11, 13, 15, 17]


@needs_data
def test_converter_keeps_lore_filters_and_the_land_tables(catalog):
    lore = catalog.subclasses["lore-xphb"]["spell_choices"]
    assert [(e["level"], e["mode"], e["filter"]["class"]) for e in lore] == [(6, "prepared", ["cleric", "druid", "wizard"])] * 2
    by_variant = catalog.subclasses["land-xphb"]["spells_by_variant"]
    assert set(by_variant) == {"arid", "polar", "temperate", "tropical"}
    arid = [(e["prerequisites"][0]["index"], e["spell"]["index"], e["mode"]) for e in by_variant["arid"]]
    assert arid == [("druid-3", "blur-xphb", "always"), ("druid-3", "burning-hands-xphb", "always"),
                    ("druid-3", "fire-bolt-xphb", "always"), ("druid-5", "fireball-xphb", "always"),
                    ("druid-7", "blight-xphb", "always"), ("druid-9", "wall-of-stone-xphb", "always")]
    # the tables of the feature text are the data: every spell name of a row is a spell of the variant
    text = [row for row in catalog.features[LAND_FID]["desc"] if "|" in row and "Druid Level" not in row]
    names = sorted(n.strip().lower().replace(" ", "-") + "-xphb" for row in text for n in row.split("|")[1].split(","))
    assert names == sorted(e["spell"]["index"] for v in by_variant.values() for e in v)
    # additive keys only on the XPHB subclasses that need them
    keyed = sorted(k for k, v in catalog.subclasses.items() if "spell_choices" in v or "spells_by_variant" in v)
    assert keyed == ["abjurer-xphb", "diviner-xphb", "evoker-xphb", "illusionist-xphb", "land-xphb", "lore-xphb"]


# ---- Savants ----------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,count", [(3, 2), (4, 2), (5, 3), (6, 3), (7, 4), (8, 4), (9, 5), (11, 6), (13, 7),
                                         (15, 8), (16, 8), (17, 9), (20, 9)])
def test_savant_count_follows_the_slot_levels(catalog, level, count):
    card = _card(_res(catalog, [_wizard(level, "evoker-xphb")]), EVO)
    assert card["count"] == count and card["source"] == {"kind": "class", "id": "wizard", "label": "Wizard", "level": 3}
    assert card["status"] == "pending" and card["label"] == "Evocation Savant"


@needs_data
@pytest.mark.parametrize("sub_id", sorted(SAVANT))
def test_savant_options_are_wizard_spells_of_the_school(catalog, sub_id):
    cid, school = SAVANT[sub_id]
    card = _card(_res(catalog, [_wizard(3, sub_id)]), cid)
    assert card["options"]
    for o in card["options"]:
        spell = catalog.spells[o["id"]]
        assert spell["school"]["index"] == school and any(c["index"] == "wizard" for c in spell["classes"]), o["id"]
        assert spell["level"] in (1, 2)  # no cantrip (the 2024 book is level 1+), no level 3 at Wizard 3
        assert o["group"] == f"spell-level-{spell['level']}"
    # every visible wizard spell of the school and levels 1-2 is offered
    expected = {s["index"] for s in catalog.spells.values()
                if s["level"] in (1, 2) and s["school"]["index"] == school and any(c["index"] == "wizard" for c in s["classes"])
                and s.get("ruleset") == "2024"}
    assert expected <= {o["id"] for o in card["options"]}
    assert "shield-xphb" in {o["id"] for o in _card(_res(catalog, [_wizard(3, "abjurer-xphb")]), SAVANT["abjurer-xphb"][0])["options"]}


@needs_data
def test_savant_levels_grow_with_the_slots(catalog):
    for level, top in [(3, 2), (5, 3), (9, 5), (17, 9)]:
        card = _card(_res(catalog, [_wizard(level, "evoker-xphb")]), EVO)
        assert {catalog.spells[o["id"]]["level"] for o in card["options"]} == set(range(1, top + 1)), level
    assert "fireball-xphb" not in {o["id"] for o in _card(_res(catalog, [_wizard(3, "evoker-xphb")]), EVO)["options"]}
    assert "fireball-xphb" in {o["id"] for o in _card(_res(catalog, [_wizard(5, "evoker-xphb")]), EVO)["options"]}


@needs_data
def test_savant_respects_the_sources_filter(catalog):
    everything = {o["id"] for o in _card(_res(catalog, [_wizard(5, "evoker-xphb")]), EVO)["options"]}
    only_xphb = {o["id"] for o in _card(_res(catalog, [_wizard(5, "evoker-xphb")], sources=["xphb"]), EVO)["options"]}
    assert "cacophonic-shield-frhof" in everything and "cacophonic-shield-frhof" not in only_xphb
    assert "fireball-xphb" in only_xphb and only_xphb < everything
    # a stored pick the filter now hides stays offered (the usual `keep` rule)
    kept = _card(_res(catalog, [_wizard(5, "evoker-xphb", {EVO: ["cacophonic-shield-frhof"]})], sources=["xphb"]), EVO)
    assert kept["selected"] == ["cacophonic-shield-frhof"]


@needs_data
def test_savant_picks_join_the_spellbook_and_the_prepared_card(catalog):
    base = _res(catalog, [_wizard(3, "evoker-xphb")])
    picks = [i for i in _enabled(_card(base, EVO))][:2]
    plain = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: _book(catalog, 3, "evoker-xphb", skip=picks)})])
    res = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: _book(catalog, 3, "evoker-xphb", skip=picks), EVO: picks})])
    card = _card(res, EVO)
    assert card["selected"] == picks and card["status"] == "resolved"
    # the book card is still complete with its own count (the Savant picks do not use it)
    assert _card(res, BOOK)["status"] == "resolved" and len(_card(res, BOOK)["selected"]) == _card(res, BOOK)["count"]
    assert set(_ids(_entry(res)["spellbook"])) == set(_card(res, BOOK)["selected"]) | set(picks)
    assert not set(picks) & set(_ids(_entry(plain)["spellbook"]))
    # preparable: the prepared card offers them, and only them on top of the book
    offered = {o["id"] for o in _card(res, PREPARED)["options"]}
    assert set(picks) <= offered
    assert not set(picks) & {o["id"] for o in _card(plain, PREPARED)["options"]}
    prepared = _res(catalog, [_wizard(3, "evoker-xphb", {
        BOOK: _book(catalog, 3, "evoker-xphb", skip=picks), EVO: picks, PREPARED: picks})])
    assert _card(prepared, PREPARED)["selected"] == picks and set(_ids(_entry(prepared)["known"])) == set(picks)
    assert prepared["problems"] == []


@needs_data
def test_savant_and_book_do_not_repeat_a_spell(catalog):
    book = _book(catalog, 3, "evoker-xphb")
    shared = next(i for i in book if catalog.spells[i]["school"]["index"] == "evocation")
    res = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: book, EVO: [shared]})])
    savant = _card(res, EVO)
    assert _opt(savant, shared)["disabled"] and _opt(savant, shared)["disabledReason"] == "already in your spellbook"
    assert savant["selected"] == [] and _pruned(res, EVO)  # stored duplicate: non-blocking pruned, not a problem
    assert res["problems"] == []
    # the other direction: a Savant pick is closed on the book card
    free = [i for i in _enabled(_card(res, EVO))][0]
    res2 = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: book[:3], EVO: [free]})])
    assert _opt(_card(res2, BOOK), free)["disabled"]
    assert _opt(_card(res2, BOOK), free)["disabledReason"] == "chosen as Evocation Savant"


def _action_savant_spell(catalog, res0):
    return next(i for i in _enabled(_card(res0, EVO)) if catalog.spells[i]["level"] == 1
                and catalog.spells[i]["casting_time"] == "1 action")


@needs_data
def test_savant_picks_feed_spell_mastery_and_signature(catalog):
    res0 = _res(catalog, [_wizard(20, "evoker-xphb")])
    low = _action_savant_spell(catalog, res0)
    other = next(i for i in _enabled(_card(res0, EVO)) if catalog.spells[i]["level"] == 3 and i != "fireball-xphb")
    picks = {BOOK: _book(catalog, 20, "evoker-xphb", skip=[low, other, "fireball-xphb"]), EVO: [low, other, "fireball-xphb"]}
    res = _res(catalog, [_wizard(20, "evoker-xphb", picks)])
    assert not {low, other, "fireball-xphb"} & set(_card(res, BOOK)["selected"])
    sig = _card(res, SIGNATURE)
    assert {"fireball-xphb", other} <= {o["id"] for o in sig["options"]}  # level 3 Savant spells, not in the book card
    res_sig = _res(catalog, [_wizard(20, "evoker-xphb", {**picks, SIGNATURE: ["fireball-xphb"]})])
    assert _card(res_sig, SIGNATURE)["selected"] == ["fireball-xphb"]
    assert "fireball-xphb" in _ids(_entry(res_sig)["signatureSpells"]) and "fireball-xphb" in _ids(_entry(res_sig)["alwaysPrepared"])
    # Spell Mastery takes a level 1 Savant spell with a casting time of an action
    mastery = _card(res, MASTERY1)
    assert low in {o["id"] for o in mastery["options"]}
    res_m = _res(catalog, [_wizard(20, "evoker-xphb", {**picks, MASTERY1: [low]})])
    assert _card(res_m, MASTERY1)["selected"] == [low] and low in _ids(_entry(res_m)["spellMastery"])
    assert res_m["problems"] == []


@needs_data
def test_removing_the_savant_source_prunes_the_dependants_without_blocking(catalog):
    res0 = _res(catalog, [_wizard(20, "evoker-xphb")])
    fb = "fireball-xphb"
    low = _action_savant_spell(catalog, res0)
    picks = {BOOK: _book(catalog, 20, "evoker-xphb", skip=[low, fb]), EVO: [low, fb],
             MASTERY1: [low], SIGNATURE: [fb], PREPARED: [low, fb]}
    full = _res(catalog, [_wizard(20, "evoker-xphb", picks)])
    assert _card(full, SIGNATURE)["selected"] == [fb] and _card(full, MASTERY1)["selected"] == [low]
    assert fb in _ids(_entry(full)["alwaysPrepared"])
    for sub in (None, "diviner-xphb"):  # no subclass at all, or another school's Savant
        gone = _res(catalog, [_wizard(20, sub, picks)])
        assert _card(gone, SIGNATURE)["selected"] == [] and _card(gone, MASTERY1)["selected"] == []
        assert fb not in _ids(_entry(gone)["spellbook"]) and fb not in _ids(_entry(gone)["alwaysPrepared"])
        assert gone["problems"] == []
        assert _pruned(gone, SIGNATURE) and _pruned(gone, MASTERY1) and _pruned(gone, PREPARED)
    stale = _res(catalog, [_wizard(20, None, picks)])
    assert _pruned(stale, EVO)  # the Savant card is gone: the stored cid is reported, not blocking


@needs_data
def test_leveling_down_prunes_surplus_savant_picks(catalog):
    res = _res(catalog, [_wizard(5, "evoker-xphb")])
    three = _enabled(_card(res, EVO))[:3]
    keep = _book(catalog, 3, "evoker-xphb", skip=three)
    res3 = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: keep, EVO: three})])
    card = _card(res3, EVO)
    assert card["selected"] == three[:2] and card["status"] == "resolved"
    assert _pruned(res3, EVO) and res3["problems"] == []
    # a level-3 spell is no longer offered at 3: dropped, still not a problem
    fireball = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: keep, EVO: ["fireball-xphb"]})])
    assert _card(fireball, EVO)["selected"] == [] and _pruned(fireball, EVO) and fireball["problems"] == []


@needs_data
def test_savant_attaches_to_the_feature_row(catalog):
    picks = _enabled(_card(_res(catalog, [_wizard(3, "evoker-xphb")]), EVO))[:2]
    res = _res(catalog, [_wizard(3, "evoker-xphb", {EVO: picks})])
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Evocation Savant")
    assert sorted(row["choice"]) == sorted(catalog.spells[p]["name"] for p in picks)


@needs_data
def test_savant_gates_and_degrade(catalog):
    assert _card(_res(catalog, [_wizard(2, "evoker-xphb")]), EVO) is None  # below the record's level
    assert _card(_res(catalog, [_wizard(3, None)]), EVO) is None  # no subclass
    assert _card(_res(catalog, [_wizard(3, "diviner-xphb")]), EVO) is None  # another subclass
    for ruleset in ("mixed", "2014"):  # a stored XPHB subclass is hidden: no card, byte-identical to no Savant
        assert _card(_res(catalog, [_wizard(3, "evoker-xphb")], ruleset=ruleset), EVO) is None
    srd = resolve(_draft([_wizard(3, "evoker-xphb")]), _srd_only(catalog))
    assert _card(srd, EVO) is None
    bare = copy.copy(catalog)
    bare.subclasses = {k: {kk: vv for kk, vv in v.items() if kk != "spell_choices"} for k, v in catalog.subclasses.items()}
    assert _card(resolve(_draft([_wizard(3, "evoker-xphb")]), bare), EVO) is None
    # Eldritch Knight / a Fighter next to a Wizard keep their own cards
    multi = _res(catalog, [_wizard(3, "evoker-xphb"), ("fighter", 3, "eldritch-knight-xphb", {})])
    assert _card(multi, EVO) is not None


@needs_data
def test_savant_with_nothing_to_offer_is_unavailable_not_blocking(catalog):
    patched = copy.copy(catalog)
    patched.spells = {k: v for k, v in catalog.spells.items() if (v.get("school") or {}).get("index") != "evocation"}
    patched.spell_twins = {k: v for k, v in catalog.spell_twins.items() if k in patched.spells and v in patched.spells}
    res = resolve(_draft([_wizard(3, "evoker-xphb")]), patched)
    card = _card(res, EVO)
    assert card["options"] == [] and card["status"] == "unavailable"


# ---- Improved Illusions -----------------------------------------------------------------------

def _illusionist(level=3, cantrips=None, extra=None):
    picks = dict(extra or {})
    if cantrips is not None:
        picks[CANTRIPS] = cantrips
    return _wizard(level, "illusionist-xphb", picks)


@needs_data
def test_improved_illusions_needs_minor_illusion_known_elsewhere(catalog):
    res = _res(catalog, [_illusionist()])
    assert _card(res, IMPROVED) is None  # Minor Illusion is simply known (the subclass grant)
    assert "minor-illusion-xphb" in _ids(_entry(res)["alwaysPrepared"])


@needs_data
def test_improved_illusions_when_the_cantrips_card_holds_minor_illusion(catalog):
    res0 = _res(catalog, [_illusionist()])
    cantrips_card = _card(res0, CANTRIPS)
    assert not _opt(cantrips_card, "minor-illusion-xphb").get("disabled")  # no longer closed by the subclass grant
    others = [i for i in _enabled(cantrips_card) if i not in ("minor-illusion-xphb", "minor-illusion")][:2]
    res = _res(catalog, [_illusionist(cantrips=["minor-illusion-xphb"] + others)])
    card = _card(res, IMPROVED)
    assert card["count"] == 1 and card["status"] == "pending"
    assert _opt(card, "minor-illusion-xphb") is None  # "a different Wizard cantrip"
    assert all(catalog.spells[o["id"]]["level"] == 0 and o["group"] == "spell-level-0" for o in card["options"])
    held = set(["minor-illusion-xphb"] + others)
    assert all(_opt(card, h) is None or _opt(card, h)["disabledReason"] == "already known" for h in held)
    extra = next(o["id"] for o in card["options"] if not o.get("disabled"))
    res2 = _res(catalog, [_illusionist(cantrips=["minor-illusion-xphb"] + others, extra={IMPROVED: [extra]})])
    assert _card(res2, IMPROVED)["selected"] == [extra] and _card(res2, IMPROVED)["status"] == "resolved"
    entry = _entry(res2)
    cantrip_ids = _ids(entry["cantrips"])
    assert extra in cantrip_ids and "minor-illusion-xphb" in cantrip_ids
    assert _card(res2, CANTRIPS)["count"] == _card(res0, CANTRIPS)["count"]  # not counted against the cantrips known
    assert "minor-illusion-xphb" not in _ids(entry["alwaysPrepared"])  # not listed twice
    row = next(f for f in res2["sheet"]["features"] if f["name"] == "Improved Illusions")
    assert row["choice"] == [catalog.spells[extra]["name"]]


@needs_data
def test_improved_illusions_when_a_feat_cantrip_card_holds_minor_illusion(catalog):
    res = _res(catalog, [_illusionist()], bg_choices=MI_VARIANT)
    assert _opt(_card(res, MI_CANTRIP), "minor-illusion-xphb") is not None
    assert _card(res, IMPROVED) is None
    res2 = _res(catalog, [_illusionist()], bg_choices={**MI_VARIANT, MI_CANTRIP: ["minor-illusion-xphb"]})
    card = _card(res2, IMPROVED)
    assert card is not None and _opt(card, "minor-illusion-xphb") is None
    assert "minor-illusion-xphb" not in _ids(_entry(res2)["alwaysPrepared"])


@needs_data
def test_improved_illusions_innate_sources_and_removal(catalog):
    card = {"id": IMPROVED, "source": {"kind": "class", "id": "wizard", "label": "Wizard", "level": 3},
            "label": "Improved Illusions", "description": "", "count": 1,
            "options": [{"id": "mage-hand-xphb", "label": "Mage Hand"}, {"id": "light-xphb", "label": "Light"}],
            "selected": ["mage-hand-xphb"], "status": "resolved"}
    choices = [dict(card)]
    pruned = subclass_spells_2024.gate_improved_illusions(choices, catalog, ["something-else"])
    assert choices == [] and len(pruned) == 1 and pruned[0]["choiceId"] == IMPROVED  # not known: card removed, pick reported
    choices = [dict(card)]
    assert subclass_spells_2024.gate_improved_illusions(choices, catalog, ["minor-illusion"]) == []  # species / feat innate (2014 id)
    assert choices[0]["selected"] == ["mage-hand-xphb"]
    choices = [dict(card)]
    pruned = subclass_spells_2024.gate_improved_illusions(choices, catalog, ["minor-illusion-xphb", "mage-hand-xphb"])
    assert choices[0]["selected"] == [] and choices[0]["status"] == "pending" and len(pruned) == 1
    assert next(o for o in choices[0]["options"] if o["id"] == "mage-hand-xphb")["disabledReason"] == "already known"


@needs_data
def test_improved_illusions_pick_is_reported_when_minor_illusion_is_dropped(catalog):
    res0 = _res(catalog, [_illusionist()])
    others = [i for i in _enabled(_card(res0, CANTRIPS)) if i not in ("minor-illusion-xphb",)][:2]
    extra = _enabled(_card(_res(catalog, [_illusionist(cantrips=["minor-illusion-xphb"] + others)]), IMPROVED))[0]
    res = _res(catalog, [_illusionist(cantrips=others, extra={IMPROVED: [extra]})])
    assert _card(res, IMPROVED) is None and _pruned(res, IMPROVED) and res["problems"] == []
    assert extra not in _ids(_entry(res)["cantrips"])


@needs_data
def test_improved_illusions_gates(catalog):
    for ruleset in ("mixed", "2014"):
        res = _res(catalog, [_illusionist(cantrips=["minor-illusion-xphb"])], ruleset=ruleset)
        assert _card(res, IMPROVED) is None
    assert _card(_res(catalog, [_wizard(3, "evoker-xphb", {CANTRIPS: ["minor-illusion-xphb"]})]), IMPROVED) is None
    assert _card(_res(catalog, [_illusionist(2)]), IMPROVED) is None
    assert _card(resolve(_draft([_illusionist(cantrips=["minor-illusion-xphb"])]), _srd_only(catalog)), IMPROVED) is None


# ---- Magical Discoveries ----------------------------------------------------------------------

def _lore(level, picks=None):
    return ("bard", level, "lore-xphb", dict(picks or {}))


@needs_data
def test_discoveries_card_levels_and_lists(catalog):
    assert _card(_res(catalog, [_lore(5)]), DISCOVERIES) is None
    card = _card(_res(catalog, [_lore(6)]), DISCOVERIES)
    assert card["count"] == 2 and card["status"] == "pending" and card["source"]["level"] == 6
    lists = {"cleric", "druid", "wizard"}
    for o in card["options"]:
        spell = catalog.spells[o["id"]]
        assert spell["level"] <= 3 and {c["index"] for c in spell["classes"]} & lists, o["id"]
        assert o["group"] == f"spell-level-{spell['level']}"
    ids = {o["id"] for o in card["options"]}
    assert {"fireball-xphb", "cure-wounds-xphb", "entangle-xphb", "fire-bolt-xphb", "guidance-xphb"} <= ids  # cantrips and level 3
    assert not {i for i in ids if catalog.spells[i]["level"] > 3}
    assert "vicious-mockery-xphb" not in ids  # a Bard-only spell is not on the three lists
    top = _card(_res(catalog, [_lore(10)]), DISCOVERIES)
    assert {catalog.spells[o["id"]]["level"] for o in top["options"]} == set(range(0, 6))
    assert _card(_res(catalog, [_lore(20)]), DISCOVERIES)["count"] == 2


@needs_data
def test_discoveries_are_always_prepared_and_closed_on_the_bard_cards(catalog):
    res = _res(catalog, [_lore(6, {DISCOVERIES: ["cure-wounds-xphb", "mage-hand-xphb"]})])
    assert _card(res, DISCOVERIES)["status"] == "resolved"
    always = _entry(res, "bard")["alwaysPrepared"]
    assert {"cure-wounds-xphb", "mage-hand-xphb"} <= set(_ids(always))
    prepared = _opt(_card(res, "class:bard:spells-known"), "cure-wounds-xphb")  # a spell of both the Bard and Cleric lists
    assert prepared["disabled"] and prepared["disabledReason"] == "always prepared (Magical Discoveries)"
    cantrip = _opt(_card(res, "class:bard:spells-cantrips"), "mage-hand-xphb")
    assert cantrip["disabled"] and cantrip["disabledReason"] == "always prepared (Magical Discoveries)"
    # a stored Prepared Spells pick of the same spell is dropped, never blocking
    res2 = _res(catalog, [_lore(6, {DISCOVERIES: ["cure-wounds-xphb", "fireball-xphb"],
                                    "class:bard:spells-known": ["cure-wounds-xphb"]})])
    assert _card(res2, "class:bard:spells-known")["selected"] == [] and res2["problems"] == []
    assert _pruned(res2, "class:bard:spells-known")


@needs_data
def test_discoveries_ignore_spells_the_class_already_has_prepared(catalog):
    card = _card(_res(catalog, [_lore(20)]), DISCOVERIES)
    option = _opt(card, "power-word-heal-xphb") or _opt(card, "word-of-recall-xphb")
    assert catalog.spells["power-word-heal-xphb"]["classes"]  # Bard 20 always prepares it
    heal = _opt(card, "power-word-heal-xphb")
    assert heal is None or heal["disabled"]  # the Bard-only spell is not on the lists anyway; never a free pick
    assert option is None or option["id"] != "power-word-heal-xphb" or option.get("disabled")
    # the class grant appears as `taken` for a spell that IS on a list: Contact Other Plane style (Warlock only) is n/a;
    # verified through the pure function instead
    rc = {"cls": {"name": "Bard"}, "cls_id": "bard", "level": 6, "subclass_id": "lore-xphb"}
    options = lambda flt, keep: [{"option_type": "reference", "item": {"index": "cure-wounds-xphb", "name": "Cure Wounds"}},
                                 {"option_type": "reference", "item": {"index": "fireball-xphb", "name": "Fireball"}}]
    tpl, grants = subclass_spells_2024.discoveries_template(catalog, rc, "2024", 3, {"cure-wounds-xphb": "Bard"}, options, {})
    assert _opt(tpl, "cure-wounds-xphb")["disabledReason"] == "always prepared (Bard)" and grants == {}


@needs_data
def test_discoveries_gates(catalog):
    assert _card(_res(catalog, [("bard", 6, "valor-xphb", {})]), DISCOVERIES) is None
    assert _card(_res(catalog, [("bard", 6, None, {})]), DISCOVERIES) is None
    for ruleset in ("mixed", "2014"):
        assert _card(_res(catalog, [_lore(6)], ruleset=ruleset), DISCOVERIES) is None
    assert _card(resolve(_draft([_lore(6)]), _srd_only(catalog)), DISCOVERIES) is None
    # a stored pick of a removed subclass is reported, not blocking, and no longer prepared
    res = _res(catalog, [("bard", 6, "valor-xphb", {DISCOVERIES: ["fireball-xphb", "fire-bolt-xphb"]})])
    assert _pruned(res, DISCOVERIES) and "fireball-xphb" not in _ids(_entry(res, "bard")["alwaysPrepared"])


@needs_data
def test_discoveries_leveling_down_prunes(catalog):
    res = _res(catalog, [_lore(5, {DISCOVERIES: ["fireball-xphb", "fire-bolt-xphb"]})])
    assert _card(res, DISCOVERIES) is None and _pruned(res, DISCOVERIES) and res["problems"] == []


# ---- Circle of the Land ----------------------------------------------------------------------

def _land(level, land=None, picks=None):
    p = dict(picks or {})
    if land:
        p[LAND] = [f"{LAND_FID}--{land}"]
    return ("druid", level, "land-xphb", p)


@needs_data
def test_land_card(catalog):
    assert _card(_res(catalog, [_land(2)]), LAND) is None
    card = _card(_res(catalog, [_land(3)]), LAND)
    assert card["count"] == 1 and card["status"] == "pending"
    assert [o["label"] for o in card["options"]] == ["Arid", "Polar", "Temperate", "Tropical"]
    assert [o["id"] for o in card["options"]] == [f"{LAND_FID}--{k}" for k in ("arid", "polar", "temperate", "tropical")]
    assert _card(_res(catalog, [("druid", 3, "moon-xphb", {})]), LAND) is None
    assert _card(_res(catalog, [("druid", 3, None, {})]), LAND) is None


@needs_data
@pytest.mark.parametrize("land,level,expected", [  # plus the Druid's own Speak with Animals
    ("arid", 3, {"blur-xphb", "burning-hands-xphb", "fire-bolt-xphb"}),
    ("arid", 5, {"blur-xphb", "burning-hands-xphb", "fire-bolt-xphb", "fireball-xphb"}),
    ("arid", 9, {"blur-xphb", "burning-hands-xphb", "fire-bolt-xphb", "fireball-xphb", "blight-xphb", "wall-of-stone-xphb"}),
    ("polar", 3, {"fog-cloud-xphb", "hold-person-xphb", "ray-of-frost-xphb"}),
    ("polar", 7, {"fog-cloud-xphb", "hold-person-xphb", "ray-of-frost-xphb", "sleet-storm-xphb", "ice-storm-xphb"}),
    ("temperate", 5, {"misty-step-xphb", "shocking-grasp-xphb", "sleep-xphb", "lightning-bolt-xphb"}),
    ("tropical", 9, {"acid-splash-xphb", "ray-of-sickness-xphb", "web-xphb", "stinking-cloud-xphb", "polymorph-xphb",
                     "insect-plague-xphb"}),
])
def test_land_spells_by_druid_level(catalog, land, level, expected):
    res = _res(catalog, [_land(level, land)])
    assert set(_ids(_entry(res, "druid")["alwaysPrepared"])) == expected | {"speak-with-animals-xphb"}


@needs_data
def test_land_without_a_pick_gives_no_spells_and_switching_moves_them(catalog):
    res = _res(catalog, [_land(5)])
    assert _ids(_entry(res, "druid")["alwaysPrepared"]) == ["speak-with-animals-xphb"]  # the class grant only
    arid = _res(catalog, [_land(5, "arid")])
    polar = _res(catalog, [_land(5, "polar")])
    assert "fireball-xphb" in _ids(_entry(arid, "druid")["alwaysPrepared"])
    assert "fireball-xphb" not in _ids(_entry(polar, "druid")["alwaysPrepared"])
    assert "sleet-storm-xphb" in _ids(_entry(polar, "druid")["alwaysPrepared"])
    # the Druid's own card closes the spell it already has prepared
    assert _opt(_card(polar, "class:druid:spells-known"), "fog-cloud-xphb")["disabledReason"] == "always prepared (Circle of the Land)"
    assert not _opt(_card(arid, "class:druid:spells-known"), "fog-cloud-xphb").get("disabled")
    row = next(f for f in arid["sheet"]["features"] if f["name"] == "Circle of the Land Spells")
    assert row["choice"] == ["Arid"]


@needs_data
@pytest.mark.parametrize("land,damage", [("arid", "fire"), ("polar", "cold"), ("temperate", "lightning"), ("tropical", "poison")])
def test_natures_ward_resistance_follows_the_land(catalog, land, damage):
    at9 = _res(catalog, [_land(9, land)])
    assert damage not in at9["sheet"]["damageModifiers"]["resistances"]  # Nature's Ward starts at Druid 10
    res = _res(catalog, [_land(10, land)])
    mods = res["sheet"]["damageModifiers"]
    assert damage in mods["resistances"]
    assert "poisoned" in res["sheet"]["conditionImmunities"]
    other = {"fire", "cold", "lightning", "poison"} - {damage}
    assert not other & set(mods["resistances"])


@needs_data
def test_natures_ward_poison_immunity_does_not_need_a_land_and_degrades(catalog):
    res = _res(catalog, [_land(10)])
    assert "poisoned" in res["sheet"]["conditionImmunities"]
    assert not {"fire", "cold", "lightning", "poison"} & set(res["sheet"]["damageModifiers"]["resistances"])
    for ruleset in ("mixed", "2014"):
        res = _res(catalog, [_land(10, "arid")], ruleset=ruleset)
        assert _card(res, LAND) is None and "fire" not in res["sheet"]["damageModifiers"]["resistances"]
        assert "fireball-xphb" not in _ids((_entry(res, "druid") or {}).get("alwaysPrepared", []))
    srd = resolve(_draft([_land(10, "arid")]), _srd_only(catalog))
    assert _card(srd, LAND) is None


# ---- surfaces and timing ----------------------------------------------------------------------

@needs_data
def test_new_cards_are_count_variable_and_unavailable_aware(catalog):
    from engine import class_choices_2024
    from engine.resolve import _is_count_variable_choice
    res = _res(catalog, [_wizard(3, "evoker-xphb")])
    savant = _card(res, EVO)
    assert _is_count_variable_choice(savant) and class_choices_2024.is_new_2024_class_card(savant)
    lore = _card(_res(catalog, [_lore(6)]), DISCOVERIES)
    assert _is_count_variable_choice(lore) and class_choices_2024.is_new_2024_class_card(lore)
    land = _card(_res(catalog, [_land(3)]), LAND)
    assert not _is_count_variable_choice(land) and class_choices_2024.is_new_2024_class_card(land)
    empty = {**savant, "options": [], "selected": [], "status": "pending"}
    assert class_choices_2024.mark_unavailable([empty], "2024")[0]["status"] == "unavailable"
    assert class_choices_2024.mark_unavailable([empty], "mixed")[0]["status"] == "pending"


def test_frontend_routes_the_new_spell_cards_to_the_spells_tab():
    import pathlib
    import re
    text = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "ClassPage.tsx").read_text()
    start = text.index("function isSpellChoiceId")
    body = text[start: text.index("\n}\n", start)]
    literal = re.search(r"/(:feature:[^/]*savant[^/]*)/\.test\(choiceId\)", body)
    assert literal, "ClassPage.isSpellChoiceId has no pattern for the subclass spell cards"
    pattern = re.compile(literal.group(1))  # the same syntax in JS and Python for this pattern
    for cid in (EVO, IMPROVED, DISCOVERIES, *[v[0] for v in SAVANT.values()]):
        assert pattern.search(cid), cid
    for cid in (LAND, "class:wizard:3:feature:abjurer-xphb-3-abjurer", "class:wizard:3:feature:illusionist-xphb-3-illusionist",
                "class:bard:3:feature:lore-xphb-3-bonus-proficiencies"):
        assert not pattern.search(cid), cid


@needs_data
def test_exports_carry_the_savant_spells_and_the_new_cards(catalog):
    from markdown_export import to_markdown
    picks = _enabled(_card(_res(catalog, [_wizard(3, "evoker-xphb")]), EVO))[:2]
    res = _res(catalog, [_wizard(3, "evoker-xphb", {BOOK: _book(catalog, 3, "evoker-xphb", skip=picks), EVO: picks})])
    md = to_markdown(res)
    for p in picks:
        assert catalog.spells[p]["name"] in md
    land = to_markdown(_res(catalog, [_land(10, "arid")]))
    assert "Fire" in land or "fire" in land


@needs_data
def test_resolve_stays_fast(catalog):
    drafts = {
        "Fighter 20 mixed": _draft([("fighter", 20, None, {})], ruleset="mixed"),
        "Fighter 20 2024": _draft([("fighter", 20, None, {})]),
        "Wizard 20 mixed": _draft([_wizard(20, None)], ruleset="mixed"),
        "Wizard 20 2024": _draft([_wizard(20, None)]),
        "Bard 20 mixed": _draft([("bard", 20, None, {})], ruleset="mixed"),
        "Bard 20 2024": _draft([("bard", 20, None, {})]),
        "Evoker 17": _draft([_wizard(17, "evoker-xphb", {EVO: ["fireball-xphb"]})]),
        "Illusionist 20": _draft([_illusionist(20, cantrips=["minor-illusion-xphb"])]),
        "Lore 20": _draft([_lore(20, {DISCOVERIES: ["fireball-xphb", "fire-bolt-xphb"]})]),
        "Land 10": _draft([_land(10, "arid")]),
    }
    for name, d in drafts.items():
        resolve(d, catalog)
        assert_fast(measure(lambda: resolve(d, catalog)), name)
