"""R9 (decision E14): the 2024 resource tail - XPHB class features with a use count or a recharge that were not
yet in `derived.classResources`. Ruleset "2024" only; mixed and 2014 must not change (the F0 golden guards the
bytes, a test below checks the ids). Written before the implementation.

No XPHB class table has a column for any of these (columns: barbarian rages / rage-damage / weapon-mastery, bard
bardic-die, cleric + paladin channel-divinity, druid wild-shape, fighter second-wind / weapon-mastery, monk
martial-arts / focus-points / unarmored-movement, ranger favored-enemy, rogue sneak-attack, sorcerer
sorcery-points, warlock invocations), so every number below is prose-only and lives in
`reference_data.RESOURCE_TAIL_2024` with the quoted text in the source comment. The minimum level is the level of
the XPHB feature record in the catalog; an SRD-only catalog (no XPHB feature records) gives no entries.

Rule matrix (XPHB texts read from the catalog on 2026-10-11; `test_reference_values_match_catalog_text` pins each
quote):

  Sorcerer
   Innate Sorcery (1): "You can use this feature twice, and you regain all expended uses of it when you finish a
     Long Rest." -> 2 uses, long. "The spell save DC of your Sorcerer spells increases by 1. You have Advantage
     on the attack rolls of Sorcerer spells you cast." Sorcery Incarnate (7): "If you have no uses of Innate
     Sorcery left, you can use it if you spend 2 Sorcery Points ... you can use up to two of your Metamagic
     options on each spell you cast." Arcane Apotheosis (20): "you can use one Metamagic option on each of your
     turns without spending Sorcery Points on it." (notes)
   Sorcerous Restoration (5): "When you finish a Short Rest, you can regain expended Sorcery Points, but no more
     than a number equal to half your Sorcerer level (round down). Once you use this feature, you can't do so
     again until you finish a Long Rest." -> 1 use, long, note with floor(level/2) (5 -> 2, 20 -> 10).
  Monk
   Uncanny Metabolism (2): "When you roll Initiative, you can regain all expended Focus Points. When you do so, roll
     your Martial Arts die, and regain a number of Hit Points equal to your Monk level plus the number rolled. Once
     you use this feature, you can't use it again until you finish a Long Rest." -> 1 use, long,
     details.heal "1<martial arts die>+<monk level>" (XPHB die: d6 at 2, d8 at 5, d10 at 11, d12 at 17).
  Cleric
   Divine Intervention (10): "As a Magic action, choose any Cleric spell of level 5 or lower that doesn't require a
     Reaction to cast. ... you cast that spell without expending a spell slot or needing Material components. You
     can't use this feature again until you finish a Long Rest." -> 1 use, long. Greater Divine Intervention (20):
     "you can choose Wish ... you can't use Divine Intervention again until you finish 2d4 Long Rests." (note)
  Paladin
   Paladin's Smite (2): "you can cast it without expending a spell slot, but you must finish a Long Rest before
     you can cast it in this way again." -> 1 use, long.
   Faithful Steed (5): "You can also cast the spell once without expending a spell slot, and you regain the
     ability to do so when you finish a Long Rest." -> 1 use, long.
  Ranger
   Tireless (10): "give yourself a number of Temporary Hit Points equal to 1d8 plus your Wisdom modifier (minimum of
     1). You can use this action a number of times equal to your Wisdom modifier (minimum of once), and you regain
     all expended uses when you finish a Long Rest." -> uses max(1, WIS), long; note 1d8 + max(1, WIS).
   Nature's Veil (14): "You can use this feature a number of times equal to your Wisdom modifier (minimum of
     once), and you regain all expended uses when you finish a Long Rest." -> uses max(1, WIS), long.
  Druid
   Wild Resurgence (5): "In addition, you can expend one use of Wild Shape (no action required) to give yourself a
     level 1 spell slot, but you can't do so again until you finish a Long Rest." -> 1 use, long (the first half,
     once on each of your turns, is in the note).
   Wild Companion (2), decision E9: "you can expend a spell slot or a use of Wild Shape to cast the Find Familiar
     spell without Material components" -> a NOTE only (no uses, no recharge); Find Familiar is not always prepared.
   Archdruid (20) Nature Magician: "Once you use this benefit, you can't do so again until you finish a Long Rest."
     -> 1 use, long.
  Rogue
   Stroke of Luck (20): "Once you use this feature, you can't use it again until you finish a Short or Long Rest."
     -> 1 use, short-or-long.
  Barbarian
   Persistent Rage (15): "When you roll Initiative, you can regain all expended uses of Rage. After you regain uses
     of Rage in this way, you can't do so again until you finish a Long Rest." -> 1 use, long.
  Wizard
   Signature Spells (20): "you can cast each of them once at level 3 without expending a spell slot. ... you can't
     cast them in this way again until you finish a Short or Long Rest." -> uses = number of picked signature
     spells (one cast each), short-or-long, the names in details.note; no entry while nothing is picked.

Scanned and skipped (no use count or recharge in the text): see ARCHITECTURE-CURRENT-STATE.md (R9 section).
"""
from perf_helpers import assert_fast
import copy

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", abilities=None, sources=()):
    base = {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": c, "level": lvl, "choices": ch} for c, lvl, *rest in classes for ch in [rest[0] if rest else {}]]
    d = {"ruleset": ruleset, "sources": list(sources), "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _ids(res):
    return [r["id"] for r in res["derived"]["classResources"]]


# (class, resource id, first level, uses, recharge)
TAIL = [
    ("sorcerer", "sorcerer:innate-sorcery", 1, 2, "long"),
    ("sorcerer", "sorcerer:sorcerous-restoration", 5, 1, "long"),
    ("monk", "monk:uncanny-metabolism", 2, 1, "long"),
    ("cleric", "cleric:divine-intervention", 10, 1, "long"),
    ("paladin", "paladin:paladin-s-smite", 2, 1, "long"),
    ("paladin", "paladin:faithful-steed", 5, 1, "long"),
    ("ranger", "ranger:tireless", 10, 1, "long"),      # WIS 10 -> modifier +0, minimum 1
    ("ranger", "ranger:nature-s-veil", 14, 1, "long"),
    ("druid", "druid:wild-resurgence", 5, 1, "long"),
    ("druid", "druid:nature-magician", 20, 1, "long"),
    ("rogue", "rogue:stroke-of-luck", 20, 1, "short-or-long"),
    ("barbarian", "barbarian:persistent-rage", 15, 1, "long"),
]


@needs_data
@pytest.mark.parametrize("cls,rid,first,uses,recharge", TAIL)
def test_resource_appears_at_the_feature_level_with_the_text_numbers(catalog, cls, rid, first, uses, recharge):
    res = _res(catalog, [(cls, first)])
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "class"
    assert r["uses"] == uses and r["recharge"] == recharge
    assert r["details"]["note"]
    assert _entry(_res(catalog, [(cls, first - 1)]), rid) is None if first > 1 else True


@needs_data
@pytest.mark.parametrize("cls,rid,first,uses,recharge", TAIL)
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_nothing_outside_ruleset_2024(catalog, ruleset, cls, rid, first, uses, recharge):
    res = _res(catalog, [(cls, 20)], ruleset)
    if rid in ("cleric:divine-intervention", "rogue:stroke-of-luck"):
        # W6: the SRD feature of the same name has its own 2014 entry (same id); it must not carry the 2024 text
        assert _entry(res, rid)["details"]["note"] != _entry(_res(catalog, [(cls, 20)], "2024"), rid)["details"]["note"]
    else:
        assert rid not in _ids(res)
    assert not [i for i in _ids(res) if i in {"druid:wild-companion", "wizard:signature-spells"}]


@needs_data
def test_reference_values_match_catalog_text(catalog):
    """Every number in RESOURCE_TAIL_2024 is backed by a quote of the imported XPHB feature text."""
    quotes = {
        "xphb-sorcerer-1-innate-sorcery": "You can use this feature twice, and you regain all expended uses of it when you finish a Long Rest.",
        "xphb-sorcerer-5-sorcerous-restoration": "half your Sorcerer level (round down)",
        "xphb-monk-2-uncanny-metabolism": "regain a number of Hit Points equal to your Monk level plus the number rolled",
        "xphb-cleric-10-divine-intervention": "You can't use this feature again until you finish a Long Rest.",
        "xphb-cleric-20-greater-divine-intervention": "2d4 Long Rests",
        "xphb-paladin-2-paladins-smite": "you must finish a Long Rest before you can cast it in this way again",
        "xphb-paladin-5-faithful-steed": "You can also cast the spell once without expending a spell slot",
        "xphb-ranger-10-tireless": "a number of times equal to your Wisdom modifier (minimum of once)",
        "xphb-ranger-14-natures-veil": "a number of times equal to your Wisdom modifier (minimum of once)",
        "xphb-druid-5-wild-resurgence": "but you can't do so again until you finish a Long Rest",
        "xphb-druid-2-wild-companion": "expend a spell slot or a use of Wild Shape to cast the Find Familiar spell",
        "xphb-druid-20-archdruid": "Once you use this benefit, you can't do so again until you finish a Long Rest.",
        "xphb-rogue-20-stroke-of-luck": "until you finish a Short or Long Rest",
        "xphb-barbarian-15-persistent-rage": "you can't do so again until you finish a Long Rest",
        "xphb-wizard-20-signature-spells": "until you finish a Short or Long Rest",
    }
    from catalog import reference_data
    for fid, quote in quotes.items():
        text = " ".join(x for x in catalog.features[fid]["desc"] if isinstance(x, str))
        assert quote in text, fid
    assert {s["feature"] for s in reference_data.RESOURCE_TAIL_2024} >= set(quotes) - {
        "xphb-cleric-20-greater-divine-intervention", "xphb-wizard-20-signature-spells"}
    levels = {s["feature"]: catalog.features[s["feature"]]["level"] for s in reference_data.RESOURCE_TAIL_2024}
    assert levels["xphb-sorcerer-1-innate-sorcery"] == 1 and levels["xphb-ranger-14-natures-veil"] == 14
    assert levels["xphb-druid-2-wild-companion"] == 2 and levels["xphb-barbarian-15-persistent-rage"] == 15


# ---- Sorcerer ---------------------------------------------------------------------------------------------

@needs_data
def test_innate_sorcery_notes_grow_with_sorcery_incarnate_and_arcane_apotheosis(catalog):
    note = lambda lvl: _entry(_res(catalog, [("sorcerer", lvl)]), "sorcerer:innate-sorcery")["details"]["note"]
    assert "save DC" in note(1) and "increases by 1" in note(1) and "Advantage" in note(1)
    assert "2 Sorcery Points" not in note(6) and "2 Sorcery Points" in note(7)
    assert "two Metamagic" in note(7) and "without spending Sorcery Points" not in note(19)
    assert "without spending Sorcery Points" in note(20)


@needs_data
@pytest.mark.parametrize("level,regain", [(5, 2), (6, 3), (9, 4), (20, 10)])
def test_sorcerous_restoration_regains_half_the_level_rounded_down(catalog, level, regain):
    r = _entry(_res(catalog, [("sorcerer", level)]), "sorcerer:sorcerous-restoration")
    assert f"({regain})" in r["details"]["note"] and "Short Rest" in r["details"]["note"]


@needs_data
def test_sorcerer_20_order_keeps_sorcery_points_first(catalog):
    ids = _ids(_res(catalog, [("sorcerer", 20)]))
    assert ids.index("sorcerer:sorcery-points") < ids.index("sorcerer:innate-sorcery") < ids.index("sorcerer:sorcerous-restoration")


# ---- Monk ------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("level,heal", [(2, "1d6+2"), (4, "1d6+4"), (5, "1d8+5"), (11, "1d10+11"), (17, "1d12+17"), (20, "1d12+20")])
def test_uncanny_metabolism_heals_level_plus_martial_arts_die(catalog, level, heal):
    r = _entry(_res(catalog, [("monk", level)]), "monk:uncanny-metabolism")
    assert r["details"]["heal"] == heal and "Focus Points" in r["details"]["note"] and "Initiative" in r["details"]["note"]


# ---- Cleric / Paladin ------------------------------------------------------------------------------------

@needs_data
def test_divine_intervention_and_greater_divine_intervention_note(catalog):
    n10 = _entry(_res(catalog, [("cleric", 10)]), "cleric:divine-intervention")["details"]["note"]
    n20 = _entry(_res(catalog, [("cleric", 20)]), "cleric:divine-intervention")["details"]["note"]
    assert "level 5 or lower" in n10 and "Wish" not in n10
    assert "Wish" in n20 and "2d4 Long Rests" in n20


@needs_data
def test_paladin_smite_and_steed_are_single_long_rest_casts(catalog):
    res = _res(catalog, [("paladin", 20)])
    smite, steed = _entry(res, "paladin:paladin-s-smite"), _entry(res, "paladin:faithful-steed")
    assert "Divine Smite" in smite["details"]["note"] and "Find Steed" in steed["details"]["note"]
    assert _entry(_res(catalog, [("paladin", 4)]), "paladin:faithful-steed") is None
    assert _entry(_res(catalog, [("paladin", 1)]), "paladin:paladin-s-smite") is None


# ---- Ranger ----------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("wis,mod,uses", [(6, -2, 1), (10, 0, 1), (16, 3, 3), (20, 5, 5)])
def test_tireless_and_natures_veil_use_wisdom_modifier_minimum_one(catalog, wis, mod, uses):
    res = _res(catalog, [("ranger", 14)], abilities={"WIS": wis})
    assert res["derived"]["abilityModifiers"]["WIS"] == mod
    tireless, veil = _entry(res, "ranger:tireless"), _entry(res, "ranger:nature-s-veil")
    assert tireless["uses"] == veil["uses"] == uses
    assert f"1d8 + {max(1, mod)}" in tireless["details"]["note"] and "Exhaustion" in tireless["details"]["note"]


# ---- Druid -----------------------------------------------------------------------------------------------

@needs_data
def test_wild_companion_is_a_note_not_a_free_spell(catalog):
    res = _res(catalog, [("druid", 2)])
    wc = _entry(res, "druid:wild-companion")
    assert wc["uses"] is None and wc["recharge"] is None and "unlimited" not in wc
    assert "Find Familiar" in wc["details"]["note"] and "spell slot or a use of Wild Shape" in wc["details"]["note"]
    assert "find-familiar-xphb" not in (res["sheet"]["spells"][0].get("alwaysPrepared") or [])
    assert _entry(_res(catalog, [("druid", 1)]), "druid:wild-companion") is None


@needs_data
def test_wild_resurgence_and_nature_magician(catalog):
    res = _res(catalog, [("druid", 20)])
    assert "level 1 spell slot" in _entry(res, "druid:wild-resurgence")["details"]["note"]
    assert "level 4" in _entry(res, "druid:nature-magician")["details"]["note"]
    assert _entry(_res(catalog, [("druid", 19)]), "druid:nature-magician") is None
    assert _entry(res, "druid:wild-shape")["uses"] == 4  # existing R3 entry untouched, Wild Shape not unlimited


# ---- Rogue / Barbarian -----------------------------------------------------------------------------------

@needs_data
def test_stroke_of_luck_and_persistent_rage(catalog):
    assert "20" in _entry(_res(catalog, [("rogue", 20)]), "rogue:stroke-of-luck")["details"]["note"]
    assert _entry(_res(catalog, [("rogue", 19)]), "rogue:stroke-of-luck") is None
    pr = _entry(_res(catalog, [("barbarian", 15)]), "barbarian:persistent-rage")
    assert "Rage" in pr["details"]["note"] and _entry(_res(catalog, [("barbarian", 14)]), "barbarian:persistent-rage") is None


# ---- Wizard Signature Spells -----------------------------------------------------------------------------

BOOK = ["shield-xphb", "magic-missile-xphb", "detect-magic-xphb", "identify-xphb", "mirror-image-xphb",
        "misty-step-xphb", "web-xphb", "counterspell-xphb", "fireball-xphb", "fly-xphb"]
SIG = "class:wizard:20:signature-spells"


def _wiz(catalog, picks):
    extra = {"class:wizard:spellbook": BOOK}
    if picks is not None:
        extra[SIG] = picks
    return _res(catalog, [("wizard", 20, extra)])


@needs_data
@pytest.mark.parametrize("picks,uses", [(["fireball-xphb", "fly-xphb"], 2), (["fireball-xphb"], 1)])
def test_signature_spells_resource_counts_the_picked_spells(catalog, picks, uses):
    r = _entry(_wiz(catalog, picks), "wizard:signature-spells")
    assert r["uses"] == uses and r["recharge"] == "short-or-long"
    assert ", ".join(catalog.spells[s]["name"] for s in picks) in r["details"]["note"]  # printed by the generic note path


@needs_data
def test_no_signature_resource_while_nothing_is_picked_or_below_20(catalog):
    assert _entry(_wiz(catalog, None), "wizard:signature-spells") is None
    res = _res(catalog, [("wizard", 19, {"class:wizard:spellbook": BOOK})])
    assert _entry(res, "wizard:signature-spells") is None


# ---- Multiclass, degrade, exports, timing ----------------------------------------------------------------

@needs_data
def test_multiclass_each_class_reads_its_own_level_and_modifier(catalog):
    res = _res(catalog, [("paladin", 5), ("sorcerer", 5), ("ranger", 10)], abilities={"WIS": 18})
    ids = _ids(res)
    assert {"paladin:paladin-s-smite", "paladin:faithful-steed", "sorcerer:innate-sorcery",
            "sorcerer:sorcerous-restoration", "ranger:tireless"} <= set(ids)
    assert _entry(res, "ranger:tireless")["uses"] == 4  # WIS 18 -> +4
    # class order is kept: paladin entries, then sorcerer's, then ranger's
    assert ids.index("paladin:faithful-steed") < ids.index("sorcerer:innate-sorcery") < ids.index("ranger:tireless")


@needs_data
def test_degrades_without_xphb_feature_records(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith("xphb-")}
    bare.class_2024_tables = {}
    for cls in ("sorcerer", "paladin", "druid", "rogue", "monk", "ranger", "cleric", "barbarian", "wizard"):
        res = _res(bare, [(cls, 20)])
        assert not [i for i in _ids(res) if i in {t[1] for t in TAIL} | {"druid:wild-companion", "wizard:signature-spells"}]
    assert _entry(_res(bare, [("sorcerer", 20)]), "sorcerer:sorcery-points")  # SRD numbers still there


@needs_data
def test_exports_print_the_notes_and_the_heal(catalog):
    res = _res(catalog, [("monk", 20)])
    line = resource_line(_entry(res, "monk:uncanny-metabolism"))
    assert line.startswith("Uncanny Metabolism: 1 (дълга почивка), ") and "лекуване 1d12+20" in line
    sorc = resource_line(_entry(_res(catalog, [("sorcerer", 5)]), "sorcerer:sorcerous-restoration"))
    assert "Short Rest" in sorc and "(2)" in sorc
    wc = resource_line(_entry(_res(catalog, [("druid", 2)]), "druid:wild-companion"))
    assert wc.startswith("Wild Companion: ") and "(дълга" not in wc


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2024"])
@pytest.mark.parametrize("cls", ["sorcerer", "paladin", "druid", "rogue"])
def test_resolve_stays_fast(catalog, cls, ruleset):
    import time
    draft = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {
        "STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 14, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": [{"classId": cls, "level": 20, "choices": {}}]}
    resolve(draft, catalog)
    laps = []
    for _ in range(20):
        t_run = time.perf_counter()
        resolve(draft, catalog)
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
