"""FE4: feat effects on Armor Class, passive scores, Stealth and senses
(docs/superpowers/plans/2026-10-11-feat-effects.md). Each feat follows its own edition's text under every
ruleset (effects are keyed by feat index). Governing sentences (catalog text, tags stripped):

  Dragon Hide (XGE)        "While you aren't wearing armor, you can calculate your AC as 13 + your Dexterity
                           modifier. You can use a shield and still gain this benefit."  -> an alternative
                           unarmored formula that competes with Unarmored Defense etc. (best of, never summed).
  Medium Armor Master PHB  "you can add 3, rather than 2, to your AC if you have a Dexterity of 16 or higher" and
                           "Wearing medium armor doesn't impose disadvantage on your Dexterity (Stealth) checks."
  Medium Armor Master XPHB "you can add 3, rather than 2 to your AC if you have a Dexterity score of 16 or higher"
                           (the Stealth clause is gone from the 2024 text).
  Dual Wielder (PHB)       "You gain a +1 bonus to AC while you are wielding a separate melee weapon in each hand."
  Revenant Blade (ERLW)    "While you are holding a double-bladed scimitar with two hands, you gain a +1 bonus to
                           Armor Class."
  Observant (PHB)          "You have a +5 bonus to your passive Wisdom (Perception) and passive Intelligence
                           (Investigation) scores."
  Keenness of the Stone Giant (BGG)
                           "You gain darkvision with a range of 60 feet. If you already have darkvision from
                           another source, its range increases by 60 feet."

Decision F-D3: a conditional AC bonus (Dual Wielder, Revenant Blade) applies only when ``equipment.wielded`` proves
the condition; otherwise the feat's static note states the rule and AC is unchanged.
Matrix: rule (which feat applies) x number x wielded state x ruleset x armor / shield x no-feat identity x
empty catalog x timing. The MAM cap reads the Dexterity SCORE (not the modifier).
"""
from perf_helpers import assert_fast, measure
import copy
import json
import re
import time
from pathlib import Path

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import equipment as equipment_mod
from engine import feat_effects as fe
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FE4 = ("dragon-hide-xge", "medium-armor-master-phb", "medium-armor-master-xphb", "dual-wielder-phb",
       "revenant-blade-erlw", "observant-phb", "keenness-of-the-stone-giant-bgg")


def _plain(node):
    out = []

    def walk(n):
        if isinstance(n, str):
            out.append(n)
        elif isinstance(n, dict):
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(node)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, " ".join(out))


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, feats=(), ruleset="mixed", background="acolyte", species="dwarf", added=(),
         base=None, worn=None, wielded=None, picks=None):
    """classes: (classId, level). feats: ASI picks, assigned to the ASI slots (4, 8, ...) of the first class."""
    entries = []
    for n, (cls, level) in enumerate(classes):
        choices = {}
        if n == 0:
            for slot, feat in zip([lv for lv in (4, 8, 12, 16, 19) if lv <= level], feats):
                choices[f"class:{cls}:{slot}:asi"] = [f"feat:{feat}"]
            choices.update(picks or {})
        entries.append({"classId": cls, "level": level, "choices": choices})
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": entries,
         "background": {"id": background, "choices": {}}, "species": {"id": species, "choices": {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added],
                       "skipped": False},
         "details": {}, "preferences": {}}
    if worn is not None:
        d["equipment"]["worn"] = worn
    if wielded is not None:
        d["equipment"]["wielded"] = wielded
    return resolve(d, catalog)


def _d(r):
    return r["derived"]


def _feat_ids(r):
    return [f["id"] for f in r["sheet"]["feats"]]


def _notes(r, feat):
    return next(f.get("notes", []) for f in r["sheet"]["feats"] if f["id"] == feat)


# ---------------------------------------------------------------- data


@pytest.mark.parametrize("index", FE4)
def test_quote_matches_catalog_text(catalog, index):
    assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    text = _plain(catalog.feats[index]["entries"])
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in text, (index, quote)


def test_entries_use_only_known_vocabulary_and_values():
    for index in FE4:
        assert set(fed.FEAT_EFFECTS[index]) <= fed.FEAT_EFFECT_KEYS
    assert fed.FEAT_EFFECTS["dragon-hide-xge"]["ac_formula"] == {"base": 13, "abilities": ["DEX"], "allows_shield": True}
    for index in ("medium-armor-master-phb", "medium-armor-master-xphb"):
        assert fed.FEAT_EFFECTS[index]["medium_armor_dex_cap"] == {"cap": 3, "min_dex_score": 16}
    assert fed.FEAT_EFFECTS["medium-armor-master-phb"]["medium_armor_stealth_ok"] is True
    assert "medium_armor_stealth_ok" not in fed.FEAT_EFFECTS["medium-armor-master-xphb"]
    assert fed.FEAT_EFFECTS["dual-wielder-phb"]["ac_bonus_if"] == {"bonus": 1, "wielded": "two-melee"}
    assert fed.FEAT_EFFECTS["revenant-blade-erlw"]["ac_bonus_if"] == {
        "bonus": 1, "wielded": {"item": "double-bladed-scimitar", "two_hands": True}}
    assert fed.FEAT_EFFECTS["observant-phb"]["passive_bonus"] == {"skill-perception": 5, "skill-investigation": 5}
    assert fed.FEAT_EFFECTS["keenness-of-the-stone-giant-bgg"]["senses_additive"] == {"darkvision": 60}


def test_the_xphb_observant_text_has_no_passive_bonus(catalog):
    """Observant (XPHB) is the proficiency-or-Expertise feat (FE6): no passive +5 in its own text."""
    assert "passive" not in _plain(catalog.feats["observant-xphb"]["entries"])
    assert "observant-xphb" in fed.FEAT_EFFECTS and "observant-xphb" not in fed.FEAT_PENDING  # FE6


def test_keenness_bonus_senses_in_the_raw_data_agree():
    from catalog.official.paths import official_dir
    root = official_dir()  # the bundle by default (B2)
    raw = [f for f in json.loads((root / "feats.json").read_text())["feat"] if f.get("bonusSenses")]
    assert [(f["name"], f["bonusSenses"]) for f in raw] == [("Keenness of the Stone Giant", [{"darkvision": 60}])]


# ---------------------------------------------------------------- pure engine


def _inst(catalog, *indexes):
    feats = [catalog.feats[i] for i in indexes]
    return fe.instances(feats, fed.FEAT_EFFECTS, [])


def test_pure_cap_reads_the_score_not_the_modifier(catalog):
    insts = _inst(catalog, "medium-armor-master-xphb")
    assert fe.medium_armor_dex_cap(insts, 16) == 3
    assert fe.medium_armor_dex_cap(insts, 15) is None
    assert fe.medium_armor_dex_cap([], 20) is None


def test_pure_armor_class_from_gear_cap_only_touches_medium_armor(catalog):
    half_plate, breastplate = catalog.items["half-plate-armor"], catalog.items["breastplate"]
    chain_mail, studded = catalog.items["chain-mail"], catalog.items["leather-armor"]
    assert equipment_mod.armor_class_from_gear([half_plate], 4, medium_dex_cap=3) == 18
    assert equipment_mod.armor_class_from_gear([half_plate], 4) == 17
    assert equipment_mod.armor_class_from_gear([breastplate], 4, medium_dex_cap=3) == 17
    assert equipment_mod.armor_class_from_gear([chain_mail], 4, medium_dex_cap=3) == 16   # heavy: no DEX at all
    assert equipment_mod.armor_class_from_gear([studded], 4, medium_dex_cap=3) == 15      # light: uncapped (11 + 4)


def test_pure_stealth_flag_drops_only_medium_armor(catalog):
    profs = {"all-armor"}
    scores = {"STR": 10}
    assert equipment_mod.armor_warnings([catalog.items["half-plate-armor"]], scores, profs)[1] is True
    assert equipment_mod.armor_warnings([catalog.items["half-plate-armor"]], scores, profs, True)[1] is False
    assert equipment_mod.armor_warnings([catalog.items["chain-mail"]], scores, profs, True)[1] is True   # heavy


# ---------------------------------------------------------------- Dragon Hide


def test_dragon_hide_unarmored_is_thirteen_plus_dex(catalog):
    r = _res(catalog, [("fighter", 4)], ["dragon-hide-xge"], species="dragonborn", base={"DEX": 14})
    assert "dragon-hide-xge" in _feat_ids(r)
    assert _d(r)["armorClass"] == 15   # 13 + 2 (a plain unarmored 10 + 2 is 12)


def test_dragon_hide_keeps_a_shield(catalog):
    r = _res(catalog, [("fighter", 4)], ["dragon-hide-xge"], species="dragonborn", base={"DEX": 14},
             added=["shield"], worn={"armor": None, "shield": True})
    assert _d(r)["armorClass"] == 17


def test_dragon_hide_is_best_of_with_monk_unarmored_defense(catalog):
    # Monk 10 + DEX 2 + WIS 4 = 16 beats Dragon Hide 15; the formulas are never summed.
    r = _res(catalog, [("monk", 4)], ["dragon-hide-xge"], species="dragonborn", base={"DEX": 14, "WIS": 18})
    assert _d(r)["armorClass"] == 16
    r = _res(catalog, [("monk", 4)], ["dragon-hide-xge"], species="dragonborn", base={"DEX": 14, "WIS": 10})
    assert _d(r)["armorClass"] == 15   # Dragon Hide beats 12


def test_dragon_hide_does_nothing_in_armor(catalog):
    r = _res(catalog, [("fighter", 4)], ["dragon-hide-xge"], species="dragonborn", base={"DEX": 14},
             added=["chain-mail"], worn={"armor": "chain-mail"})
    assert _d(r)["armorClass"] == 16


def test_dragon_hide_has_a_claws_note(catalog):
    r = _res(catalog, [("fighter", 4)], ["dragon-hide-xge"], species="dragonborn")
    assert any("1d4" in n and "slashing" in n for n in _notes(r, "dragon-hide-xge"))


# ---------------------------------------------------------------- Medium Armor Master


@pytest.mark.parametrize("dex,expected", [(16, 18), (18, 18), (15, 17), (14, 17), (12, 16)])
def test_mam_phb_raises_the_cap_with_dex_score_16(catalog, dex, expected):
    # half plate 15 + min(DEX mod, cap): DEX 16/18 -> mod 3/4 -> capped at 3 (18); DEX 15 -> mod 2 (17).
    r = _res(catalog, [("fighter", 4)], ["medium-armor-master-phb"], base={"DEX": dex},
             added=["half-plate-armor"], worn={"armor": "half-plate-armor"})
    assert _d(r)["armorClass"] == expected


def test_mam_without_the_feat_is_unchanged(catalog):
    r = _res(catalog, [("fighter", 4)], base={"DEX": 16}, added=["half-plate-armor"], worn={"armor": "half-plate-armor"})
    assert _d(r)["armorClass"] == 17


def test_mam_xphb_cap_counts_the_final_dex_score(catalog):
    """XPHB offers +1 DEX with the feat: DEX 15 + 1 = 16 qualifies (the score after the feat)."""
    r = _res(catalog, [("fighter", 4)], ["medium-armor-master-xphb"], ruleset="2024", base={"DEX": 15},
             added=["half-plate-armor"], worn={"armor": "half-plate-armor"},
             picks={"class:fighter:4:asi:feat:medium-armor-master-xphb:ability-bonus": ["dex"]})
    assert "medium-armor-master-xphb" in _feat_ids(r)
    assert _d(r)["armorClass"] == 18   # DEX 16, mod +3, cap 3 -> 15 + 3


def test_mam_cap_does_not_apply_to_light_or_heavy_armor(catalog):
    r = _res(catalog, [("fighter", 4)], ["medium-armor-master-phb"], base={"DEX": 16},
             added=["chain-mail"], worn={"armor": "chain-mail"})
    assert _d(r)["armorClass"] == 16


def test_mam_phb_removes_stealth_disadvantage_of_medium_armor(catalog):
    kw = dict(added=["half-plate-armor"], worn={"armor": "half-plate-armor"})
    assert _d(_res(catalog, [("fighter", 4)], **kw))["stealthDisadvantage"] is True
    assert _d(_res(catalog, [("fighter", 4)], ["medium-armor-master-phb"], **kw))["stealthDisadvantage"] is False


def test_mam_phb_keeps_stealth_disadvantage_of_heavy_armor(catalog):
    r = _res(catalog, [("fighter", 4)], ["medium-armor-master-phb"], added=["chain-mail"], worn={"armor": "chain-mail"})
    assert _d(r)["stealthDisadvantage"] is True


def test_mam_xphb_text_has_no_stealth_clause_so_it_stays_true(catalog):
    """V11: the 2024 text only has the Dexterous Wearer cap; medium armor keeps its Stealth disadvantage."""
    assert "Stealth" not in _plain(catalog.feats["medium-armor-master-xphb"]["entries"])
    r = _res(catalog, [("fighter", 4)], ["medium-armor-master-xphb"], ruleset="2024",
             added=["half-plate-armor"], worn={"armor": "half-plate-armor"})
    assert "medium-armor-master-xphb" in _feat_ids(r)
    assert _d(r)["stealthDisadvantage"] is True


def test_mam_phb_is_edition_keyed_under_2024(catalog):
    """A 2014 feat keeps its own text under ruleset 2024 only when selected; here it is hidden by the ruleset
    filter and (A2) keeps its effect, so the cap still applies."""
    r = _res(catalog, [("fighter", 4)], ["medium-armor-master-phb"], ruleset="2014", base={"DEX": 16},
             added=["half-plate-armor"], worn={"armor": "half-plate-armor"})
    assert _d(r)["armorClass"] == 18 and _d(r)["stealthDisadvantage"] is False


# ---------------------------------------------------------------- Dual Wielder (conditional AC, F-D3)

SHORT_SWORDS = ["longsword", "shortsword"]


def _dw(catalog, wielded, added=("longsword", "shortsword", "shield", "greatsword"), worn=None, feats=("dual-wielder-phb",)):
    return _res(catalog, [("fighter", 4)], list(feats), base={"DEX": 14}, added=list(added),
                worn=worn if worn is not None else {"armor": None, "shield": False}, wielded=wielded)


def test_dual_wielder_with_two_melee_weapons_wielded_adds_one(catalog):
    base = _dw(catalog, {"main": "longsword", "off": "shortsword"}, feats=())
    r = _dw(catalog, {"main": "longsword", "off": "shortsword"})
    assert "dual-wielder-phb" in _feat_ids(r)
    assert _d(r)["armorClass"] == _d(base)["armorClass"] + 1 == 13   # 10 + 2 + 1


def test_dual_wielder_with_a_shield_in_the_off_hand_gets_nothing(catalog):
    r = _dw(catalog, {"main": "longsword", "off": "shield"}, worn={"armor": None, "shield": True})
    assert _d(r)["armorClass"] == 14   # 10 + 2 + shield 2, no +1


def test_dual_wielder_with_one_weapon_gets_nothing(catalog):
    assert _d(_dw(catalog, {"main": "longsword", "off": None}))["armorClass"] == 12


def test_dual_wielder_with_a_two_handed_weapon_gets_nothing(catalog):
    assert _d(_dw(catalog, {"main": "greatsword", "off": "shortsword"}))["armorClass"] == 12


def test_dual_wielder_without_wielded_hands_is_a_note_not_a_number(catalog):
    r = _res(catalog, [("fighter", 4)], ["dual-wielder-phb"], base={"DEX": 14}, added=SHORT_SWORDS,
             worn={"armor": None, "shield": False})
    assert _d(r)["armorClass"] == 12
    assert any("+1 AC" in n and "separate melee weapon in each hand" in n for n in _notes(r, "dual-wielder-phb"))


def test_dual_wielder_bonus_stacks_with_armor(catalog):
    r = _dw(catalog, {"main": "longsword", "off": "shortsword"}, added=("longsword", "shortsword", "leather-armor"),
            worn={"armor": "leather-armor", "shield": False})
    assert _d(r)["armorClass"] == 11 + 2 + 1


# ---------------------------------------------------------------- Revenant Blade


def _rb(catalog, wielded, **kw):
    return _res(catalog, [("fighter", 4)], ["revenant-blade-erlw"], species="elf", base={"DEX": 12},   # elf +2 DEX
                added=["double-bladed-scimitar", "shield", "dagger"], worn={"armor": None, "shield": False},
                wielded=wielded, **kw)


def test_revenant_blade_held_with_two_hands_adds_one(catalog):
    r = _rb(catalog, {"main": "double-bladed-scimitar", "off": None})
    assert "revenant-blade-erlw" in _feat_ids(r)
    assert _d(r)["armorClass"] == 13   # 10 + 2 + 1


def test_revenant_blade_in_the_off_hand_with_an_empty_main_hand_counts(catalog):
    assert _d(_rb(catalog, {"main": None, "off": "double-bladed-scimitar"}))["armorClass"] == 13


def test_revenant_blade_needs_both_hands_on_it(catalog):
    assert _d(_rb(catalog, {"main": "double-bladed-scimitar", "off": "dagger"}))["armorClass"] == 12


def test_revenant_blade_not_wielded_or_other_weapon_gets_nothing(catalog):
    assert _d(_rb(catalog, {"main": "dagger", "off": None}))["armorClass"] == 12
    assert _d(_rb(catalog, {"main": None, "off": None}))["armorClass"] == 12


def test_revenant_blade_without_wielded_hands_is_a_note(catalog):
    r = _res(catalog, [("fighter", 4)], ["revenant-blade-erlw"], species="elf", base={"DEX": 12},
             added=["double-bladed-scimitar"], worn={"armor": None, "shield": False})
    assert _d(r)["armorClass"] == 12
    notes = _notes(r, "revenant-blade-erlw")
    assert any("double-bladed scimitar with two hands" in n for n in notes)


# ---------------------------------------------------------------- Observant (PHB)


def test_observant_phb_adds_five_to_passive_perception_and_investigation_only(catalog):
    base = _res(catalog, [("fighter", 4)], base={"WIS": 14, "INT": 12})
    r = _res(catalog, [("fighter", 4)], ["observant-phb"], base={"WIS": 14, "INT": 12})
    assert "observant-phb" in _feat_ids(r)
    assert _d(r)["passivePerception"] == _d(base)["passivePerception"] + 5
    assert _d(r)["passiveInvestigation"] == _d(base)["passiveInvestigation"] + 5
    assert _d(r)["passiveInsight"] == _d(base)["passiveInsight"]


def test_observant_phb_leaves_the_skill_totals_alone(catalog):
    base = _res(catalog, [("fighter", 4)], base={"WIS": 14, "INT": 12})
    r = _res(catalog, [("fighter", 4)], ["observant-phb"], base={"WIS": 14, "INT": 12})
    for skill in ("skill-perception", "skill-investigation", "skill-insight"):
        assert _d(r)["skills"][skill] - _d(base)["skills"][skill] in (0, 1)   # at most the +1 ability from the feat
    # the ability increase is the only change: passive = 10 + skill + 5
    assert _d(r)["passivePerception"] == 10 + _d(r)["skills"]["skill-perception"] + 5


def test_observant_xphb_has_no_passive_bonus(catalog):
    r = _res(catalog, [("fighter", 4)], ["observant-xphb"], ruleset="2024", base={"WIS": 14, "INT": 12})
    assert "observant-xphb" in _feat_ids(r)
    assert _d(r)["passivePerception"] == 10 + _d(r)["skills"]["skill-perception"]


# ---------------------------------------------------------------- Keenness of the Stone Giant


def _keen(catalog, species, **kw):
    r = _res(catalog, [("fighter", 8)], ["strike-of-the-giants-bgg", "keenness-of-the-stone-giant-bgg"],
             species=species, base={"STR": 16}, **kw)
    assert "keenness-of-the-stone-giant-bgg" in _feat_ids(r), r["problems"] if "problems" in r else None
    return r


def test_keenness_gives_darkvision_60_to_a_species_without(catalog):
    assert _keen(catalog, "human")["sheet"]["senses"]["darkvision"] == 60   # (the SRD human has none)


def test_keenness_adds_sixty_to_existing_darkvision(catalog):
    r = _keen(catalog, "dwarf")
    base = _res(catalog, [("fighter", 8)], species="dwarf")
    assert base["sheet"]["senses"]["darkvision"] == 60
    assert r["sheet"]["senses"]["darkvision"] == 120


def test_keenness_is_added_after_a_longer_feat_or_invocation_source(catalog):
    senses = fe.add_senses({"darkvision": 120, "devilsSight": 120}, _inst(catalog, "keenness-of-the-stone-giant-bgg"))
    assert senses == {"darkvision": 180, "devilsSight": 120}


def test_keenness_leaves_other_senses_alone(catalog):
    senses = fe.add_senses({"blindsight": 10}, _inst(catalog, "keenness-of-the-stone-giant-bgg"))
    assert senses == {"blindsight": 10, "darkvision": 60}


# ---------------------------------------------------------------- identity, empty catalog, duplicates


def test_no_feat_drafts_are_unchanged(catalog):
    r = _res(catalog, [("fighter", 4)], base={"DEX": 16, "WIS": 14}, added=["half-plate-armor", "shield"],
             worn={"armor": "half-plate-armor", "shield": True})
    assert _d(r)["armorClass"] == 15 + 2 + 2 and _d(r)["stealthDisadvantage"] is True
    assert _d(r)["passivePerception"] == 10 + _d(r)["skills"]["skill-perception"]


def test_stray_duplicates_never_double_ac_or_senses(catalog):
    two = [catalog.feats["dual-wielder-phb"], catalog.feats["dual-wielder-phb"]]
    insts = fe.instances(two, fed.FEAT_EFFECTS, [])
    hands = {"main": "longsword", "off": "shortsword"}
    items = [catalog.items["longsword"], catalog.items["shortsword"]]
    assert fe.ac_bonus(insts, hands, items) == 1
    keen = fe.instances([catalog.feats["keenness-of-the-stone-giant-bgg"]] * 2, fed.FEAT_EFFECTS, [])
    assert fe.add_senses({}, keen) == {"darkvision": 60}
    obs = fe.instances([catalog.feats["observant-phb"]] * 2, fed.FEAT_EFFECTS, [])
    assert fe.passive_bonus(obs) == {"skill-perception": 5, "skill-investigation": 5}


def test_empty_catalog_feat_paths_are_a_no_op(catalog):
    assert fe.ac_formulas([]) == [] and fe.ac_bonus([], None, []) == 0 and fe.passive_bonus([]) == {}
    assert fe.add_senses({"darkvision": 60}, []) == {"darkvision": 60}
    assert fe.medium_armor_stealth_ok([]) is False


def test_empty_feat_catalog_resolves_with_the_plain_numbers():
    bare = copy.copy(load())
    bare.feats = {}
    r = _res(bare, [("fighter", 4)], ["medium-armor-master-phb", "observant-phb"], base={"DEX": 16, "WIS": 14},
             added=["half-plate-armor"], worn={"armor": "half-plate-armor"})
    assert _d(r)["armorClass"] == 17 and _d(r)["stealthDisadvantage"] is True
    assert _d(r)["passivePerception"] == 10 + _d(r)["skills"]["skill-perception"]


def _laps(catalog, classes, feats, **kw):
    return measure(lambda: _res(catalog, classes, feats, **kw))


def test_resolve_stays_fast_with_defense_feats(catalog):
    gear = dict(added=["half-plate-armor", "longsword", "shortsword"], worn={"armor": "half-plate-armor"},
                wielded={"main": "longsword", "off": "shortsword"}, base={"DEX": 16})
    feats = ["medium-armor-master-phb", "dual-wielder-phb", "observant-phb", "dragon-hide-xge"]
    for laps in (_laps(catalog, [("fighter", 20)], feats, ruleset="mixed", **gear),
               _laps(catalog, [("fighter", 20)], ["medium-armor-master-xphb"], ruleset="2024", **gear),
               _laps(catalog, [("wizard", 20)], ["observant-phb", "dual-wielder-phb"], ruleset="mixed")):
        assert_fast(laps)
