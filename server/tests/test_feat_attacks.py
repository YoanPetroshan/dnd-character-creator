"""FE5: feat effects on the attack rows (docs/superpowers/plans/2026-10-11-feat-effects.md). Each feat follows its
own edition's text under every ruleset (entries are keyed by feat index). Decisions: F-D2 (optional or conditional
riders never fold into ``damage``: a row note carries the computed number), F-D5 (Dual Wielder XPHB + the Two-Weapon
Fighting style adds the modifier), F-D6 (the Unarmed Strike row exists only when a feat improves it; a Monk keeps one
row with the best die and the alternatives in the notes).

Governing sentences (catalog text, tags stripped; every one is pinned by ``test_quote_matches_catalog_text``):

  Savage Attacker PHB   "Once per turn when you roll damage for a melee weapon attack, you can reroll the weapon's
                        damage dice and use either total."            -> note on melee weapon rows
  Savage Attacker XPHB  "Once per turn when you hit a target with a weapon, you can roll the weapon's damage dice
                        twice and use either roll against the target." -> note on every weapon row
  Great Weapon Master PHB   "Before you make a melee attack with a heavy weapon that you are proficient with, you can
                        choose to take a -5 penalty to the attack roll. If the attack hits, you add +10 ..."
  Great Weapon Master XPHB  "The extra damage equals your Proficiency Bonus." (Heavy property, Attack action) -> note
                        "+PB damage"; ``damage`` never contains it.
  Sharpshooter PHB      the same -5 / +10 for "a ranged weapon that you are proficient with"; XPHB has no number.
  Crossbow Expert XPHB  "you can add your ability modifier to the damage of the extra attack if that attack is with a
                        crossbow that has the Light property and you aren't already adding that modifier"
                        -> the hand crossbow row gets ``offhandDamage`` with the modifier.
  Crossbow Expert PHB   "you can use a bonus action to attack with a hand crossbow you are holding" (FE12: official
                        Sage Advice - the ability modifier IS added to that bonus attack's damage; the "no modifier
                        unless negative" restriction belongs to two-weapon fighting only)
                        -> the hand crossbow row gets ``offhandDamage`` with the modifier (PHB and XPHB alike).
  Dual Wielder PHB      "You can use two-weapon fighting even when the one-handed melee weapons you are wielding
                        aren't light."                                  -> ``offhandDamage`` on non-Light one-handed rows
  Dual Wielder XPHB     "... with a different weapon, which must be a Melee weapon that lacks the Two-Handed
                        property. You don't add your ability modifier to the extra attack's damage unless that
                        modifier is negative."                          -> same, Two-Weapon Fighting adds it (F-D5)
  Tavern Brawler PHB    "Your unarmed strike uses a d4 for damage."
  Tavern Brawler XPHB   "you can deal Bludgeoning damage equal to 1d4 plus your Strength modifier instead of the
                        normal damage of an Unarmed Strike"
  Unarmed Fighting XPHB "1d6 plus your Strength modifier ... If you aren't holding any weapons or a Shield when you
                        make the attack roll, the d6 becomes a d8."
  Dragon Hide (XGE)     claws: "slashing damage equal to 1d4 + your Strength modifier".
  Revenant Blade (ERLW) "A double-bladed scimitar has the finesse property when you wield it."
  Piercer / Slasher / Crusher (TCE and XPHB)   "... an attack that deals piercing / slashing / bludgeoning damage".
  Polearm Master PHB / XPHB   item lists; the d4 butt-end attack uses the row's ability modifier.
  Charger PHB (+5) / XPHB (1d8), Gunner (firearms), Elven Accuracy (DEX, INT, WIS, CHA attacks), Orcish Fury, Poisoner
  (DC 14 / 8 + increased ability modifier + PB), Bomber (Thrown), Boon of Irresistible Offense (ignore resistance;
  extra damage = the increased score).

Matrix: rule (which row gets which note) x number (computed value in the note) x ruleset (mixed / 2014 / 2024) x
grant source (ASI, background, Fighting Style card) x wielded hands x Monk x no-feat identity x empty catalog x timing.
"""
from perf_helpers import assert_fast
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import Catalog, load
from catalog.official_source import has_official, has_official_classes
from engine import attacks as attacks_mod
from engine import feat_effects as fe
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FE5 = tuple(sorted(i for i in fed._ATTACK_EFFECTS))


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


def _res(catalog, classes, feats=(), ruleset="mixed", background="acolyte", species="human", added=(), base=None,
         wielded=None, picks=None, species_picks=None):
    """classes: (classId, level). feats: ASI picks, assigned to the ASI slots (4, 8, ...) of the first class."""
    entries = []
    for n, (cls, level) in enumerate(classes):
        choices = {}
        if n == 0:
            slots = [lv for lv in (4, 8, 12, 16, 19) if lv <= level]
            if feats and str(feats[0]).startswith("boon-"):   # Epic Boons need level 19: use the last slot
                slots = slots[-1:]
            for slot, feat in zip(slots, feats):
                choices[f"class:{cls}:{slot}:asi"] = [f"feat:{feat}"]
            choices.update(picks or {})
        entries.append({"classId": cls, "level": level, "choices": choices})
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": entries,
         "background": {"id": background, "choices": {}}, "species": {"id": species, "choices": species_picks or {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added],
                       "skipped": False},
         "details": {}, "preferences": {}}
    if wielded is not None:
        d["equipment"]["wielded"] = wielded
    return resolve(d, catalog)


def _rows(r):
    return r["derived"]["attacks"]


def _row(r, item):
    return next(a for a in _rows(r) if a["itemId"] == item)


def _has(r, item, fragment):
    return any(fragment in n for n in _row(r, item)["notes"])


def _mod(r, ability):
    return r["derived"]["abilityModifiers"][ability]


def _feat_ids(r):
    return [f["id"] for f in r["sheet"]["feats"]]


# ---------------------------------------------------------------- data


@pytest.mark.parametrize("index", FE5)
def test_quote_matches_catalog_text(catalog, index):
    assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    text = _plain(catalog.feats[index]["entries"])
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in text, (index, quote)


def test_there_are_32_attack_feats_and_every_one_has_an_effect(catalog):
    attack = {i for i, kinds in fed.FEAT_KINDS.items() if "attack" in kinds}
    assert len(attack) == 32
    assert attack <= set(fed.FEAT_EFFECTS), sorted(attack - set(fed.FEAT_EFFECTS))
    for index in attack:
        effect = fed.FEAT_EFFECTS[index]
        assert set(effect) <= fed.FEAT_EFFECT_KEYS
        assert effect.keys() & {"attack_notes", "unarmed", "offhand", "finesse_items"}, index


ROW = {"itemId": "longsword", "ability": "STR", "proficient": True, "damage": "1d8+3", "damageType": "slashing",
       "notes": []}
ENV = {"pb": 3, "str_mod": 3, "dex_mod": 2, "cha_mod": 1, "str_score": 17, "dex_score": 14, "cha_score": 12}


@pytest.mark.parametrize("index", FE5)
def test_every_attack_note_template_renders_with_and_without_a_chosen_ability(index):
    for entry in fed.FEAT_EFFECTS[index].get("attack_notes", []):
        for increased in (None, "STR"):
            env = {**ENV, "inc_mod": 3 if increased else None, "inc_score": 17 if increased else None}
            text = fe.row_note(entry["text"], env, ROW)
            assert "{" not in text and "}" not in text, (index, text)
        when = entry["when"]
        for w in (when if isinstance(when, list) else [when]):
            fe._matches(w, ROW, {"melee": True, "ranged": False, "weapon": True, "props": set()})  # no unknown predicate


def test_the_unarmed_entries_carry_every_field():
    for index in ("tavern-brawler-phb", "tavern-brawler-xphb", "unarmed-fighting-xphb", "dragon-hide-xge"):
        u = fed.FEAT_EFFECTS[index]["unarmed"]
        assert {"name", "die", "type", "ability", "notes"} <= set(u) and u["ability"] == "STR"
    assert fed.FEAT_EFFECTS["unarmed-fighting-xphb"]["unarmed"]["die_free_hands"] == "1d8"
    assert fed.FEAT_EFFECTS["dragon-hide-xge"]["unarmed"]["type"] == "slashing"


def test_the_firearms_are_the_dmg_ranged_ammunition_loading_martial_weapons(catalog):
    firearms = {k for k, v in catalog.items.items()
                if v.get("source") == "DMG" and v.get("weapon_range") == "Ranged"
                and (v.get("equipment_category") or {}).get("index") == "weapon"}
    assert firearms == set(attacks_mod.FIREARM_ITEM_IDS) == {"musket", "pistol"}


# ---------------------------------------------------------------- Savage Attacker


def test_savage_attacker_xphb_from_soldier_notes_every_weapon_row(catalog):
    r = _res(catalog, [("fighter", 1)], ruleset="2024", background="soldier-xphb", species="human-xphb",
             added=["longsword", "longbow", "dagger"], base={"STR": 14, "DEX": 14})
    assert "savage-attacker-xphb" in _feat_ids(r)
    for item in ("longsword", "longbow", "dagger"):
        assert _has(r, item, "Savage Attacker: once per turn when you hit")


def test_savage_attacker_phb_only_melee_weapon_rows(catalog):
    r = _res(catalog, [("fighter", 4)], ["savage-attacker-phb"], added=["longsword", "longbow"])
    assert _has(r, "longsword", "Savage Attacker")
    assert not _has(r, "longbow", "Savage Attacker")


def test_savage_attacker_never_changes_damage(catalog):
    base = _res(catalog, [("fighter", 4)], ["alert-phb"], added=["longsword"])
    r = _res(catalog, [("fighter", 4)], ["savage-attacker-phb"], added=["longsword"])
    assert _row(r, "longsword")["damage"] == _row(base, "longsword")["damage"]


# ---------------------------------------------------------------- Great Weapon Master, Sharpshooter


def test_gwm_xphb_note_has_the_proficiency_bonus_and_damage_is_unchanged(catalog):
    r = _res(catalog, [("fighter", 8)], ["great-weapon-master-xphb"], ruleset="2024", base={"STR": 16},
             added=["greataxe", "longsword"])
    pb = r["derived"]["proficiencyBonus"]
    assert pb == 3
    greataxe = _row(r, "greataxe")
    assert f"Great Weapon Master: +{pb} damage when you hit with this Heavy weapon" in " ".join(greataxe["notes"])
    assert greataxe["damage"] == f"1d12+{_mod(r, 'STR')}"           # F-D2: the rider is not in `damage`
    assert not _has(r, "longsword", "Heavy weapon")                  # not Heavy
    assert _has(r, "longsword", "Hew")                               # any Melee weapon


def test_gwm_xphb_heavy_ranged_weapons_too(catalog):
    r = _res(catalog, [("fighter", 4)], ["great-weapon-master-xphb"], ruleset="2024", base={"STR": 16},
             added=["longbow", "shortbow"])
    assert _has(r, "longbow", "Great Weapon Master: +2 damage")      # the Heavy property is all the text asks for
    assert not _has(r, "shortbow", "Great Weapon Master")


def test_gwm_phb_minus_5_plus_10_only_on_proficient_heavy_melee(catalog):
    r = _res(catalog, [("wizard", 4)], ["great-weapon-master-phb"], added=["greataxe", "glaive", "longsword"])
    # a Wizard is proficient with neither martial weapon
    assert not _row(r, "greataxe")["proficient"]
    assert not _has(r, "greataxe", "-5")
    f = _res(catalog, [("fighter", 4)], ["great-weapon-master-phb"], base={"STR": 16}, added=["greataxe", "longsword", "longbow"])
    assert _has(f, "greataxe", "take -5 to the attack roll; if it hits, +10 damage")
    assert not _has(f, "longsword", "-5")            # not heavy
    assert not _has(f, "longbow", "-5")              # ranged
    assert _has(f, "longsword", "bonus action")      # the critical hit / kill attack: any melee weapon
    assert _row(f, "greataxe")["damage"] == f"1d12+{_mod(f, 'STR')}"


def test_sharpshooter_phb_only_on_proficient_ranged_weapons(catalog):
    r = _res(catalog, [("fighter", 4)], ["sharpshooter-phb"], added=["longbow", "greataxe"])
    assert _has(r, "longbow", "take -5 to the attack roll; if it hits, +10 damage")
    assert _has(r, "longbow", "no disadvantage at long range")
    assert not _has(r, "greataxe", "Sharpshooter")
    w = _res(catalog, [("wizard", 4)], ["sharpshooter-phb"], added=["longbow"])   # not proficient with the longbow
    assert not _has(w, "longbow", "-5") and _has(w, "longbow", "long range")


def test_sharpshooter_xphb_has_no_number(catalog):
    r = _res(catalog, [("fighter", 4)], ["sharpshooter-xphb"], ruleset="2024", base={"DEX": 14},
             added=["longbow", "crossbow-hand"])
    for item in ("longbow", "crossbow-hand"):
        assert _has(r, item, "Sharpshooter: ignores Half and Three-Quarters Cover")
        assert not _has(r, item, "-5")


# ---------------------------------------------------------------- Crossbow Expert, Dual Wielder


def test_crossbow_expert_xphb_hand_crossbow_gets_the_modifier_on_the_extra_attack(catalog):
    r = _res(catalog, [("fighter", 4)], ["crossbow-expert-xphb"], ruleset="2024", base={"DEX": 16},
             added=["crossbow-hand", "crossbow-light"])
    dex = _mod(r, "DEX")
    hand = _row(r, "crossbow-hand")
    assert hand["offhandDamage"] == f"1d6+{dex}" and hand["damage"] == f"1d6+{dex}"
    assert _has(r, "crossbow-hand", "Crossbow Expert (Dual Wielding)")
    assert _row(r, "crossbow-light")["offhandDamage"] is None        # the light crossbow lacks the Light property
    assert _has(r, "crossbow-light", "Crossbow Expert: ignore the Loading property")
    assert not _has(r, "crossbow-light", "Dual Wielding")


def test_hand_crossbow_has_no_offhand_row_without_the_feat(catalog):
    r = _res(catalog, [("fighter", 4)], ["alert-phb"], base={"DEX": 16}, added=["crossbow-hand"])
    assert _row(r, "crossbow-hand")["offhandDamage"] is None


def test_crossbow_expert_phb_notes_and_proficiency_gate(catalog):
    f = _res(catalog, [("fighter", 4)], ["crossbow-expert-phb"], base={"DEX": 16}, added=["crossbow-hand", "longbow"])
    assert _has(f, "crossbow-hand", "ignore the loading quality")
    assert _has(f, "crossbow-hand", "hand crossbow you are holding")
    assert not _has(f, "longbow", "Crossbow Expert")
    # FE12: the PHB bonus attack is not two-weapon fighting (Sage Advice): its damage adds the modifier
    dex = _mod(f, "DEX")
    assert dex > 0 and _row(f, "crossbow-hand")["offhandDamage"] == f"1d6+{dex}"
    assert _row(f, "longbow")["offhandDamage"] is None
    assert _has(f, "crossbow-hand", "bonus action attack")
    assert _has(f, "crossbow-hand", "adds your ability modifier")


def test_crossbow_expert_phb_bonus_attack_with_a_negative_modifier_and_other_crossbows(catalog):
    r = _res(catalog, [("fighter", 4)], ["crossbow-expert-phb"], base={"DEX": 8}, added=["crossbow-hand", "crossbow-light"])
    dex = _mod(r, "DEX")
    assert dex < 0
    assert _row(r, "crossbow-hand")["offhandDamage"] == f"1d6{dex}"
    assert _row(r, "crossbow-light")["offhandDamage"] is None             # only the hand crossbow is named


def test_crossbow_expert_both_editions_add_the_modifier_once(catalog):
    for feat in ("crossbow-expert-phb", "crossbow-expert-xphb"):
        row = _row(_res(catalog, [("fighter", 4)], [feat], base={"DEX": 16}, added=["crossbow-hand"]), "crossbow-hand")
        assert row["offhandDamage"] == row["damage"]                    # the modifier is in it exactly once
        assert row["offhandDamage"].count("+") == 1


def test_dual_wielder_phb_offhand_for_a_non_light_one_handed_weapon(catalog):
    r = _res(catalog, [("fighter", 4)], ["dual-wielder-phb"], base={"STR": 16}, added=["longsword", "greataxe", "shortsword"],
             wielded={"main": "longsword", "off": "shortsword"})
    mod = _mod(r, "STR")
    assert mod > 0
    assert _row(r, "longsword")["offhandDamage"] == "1d8"             # no positive modifier without Two-Weapon Fighting
    assert _row(r, "greataxe")["offhandDamage"] is None               # two-handed
    assert _row(r, "shortsword")["offhandDamage"] == "1d6"            # Light: the base rule, unchanged
    assert _has(r, "longsword", "Dual Wielder: two-weapon fighting is allowed")
    assert not _has(r, "shortsword", "Dual Wielder")                  # already Light


def test_no_dual_wielder_means_no_offhand_for_a_longsword(catalog):
    r = _res(catalog, [("fighter", 4)], ["alert-phb"], base={"STR": 16}, added=["longsword"])
    assert _row(r, "longsword")["offhandDamage"] is None


def test_dual_wielder_phb_negative_modifier_still_applies(catalog):
    r = _res(catalog, [("fighter", 4)], ["dual-wielder-phb"], base={"STR": 6}, species="dwarf", added=["longsword"])
    assert _mod(r, "STR") < 0
    assert _row(r, "longsword")["offhandDamage"] == f"1d8{_mod(r, 'STR'):+d}"


def test_dual_wielder_xphb_non_light_row_and_two_weapon_fighting_adds_the_modifier(catalog):
    plain = _res(catalog, [("fighter", 4)], ["dual-wielder-xphb"], ruleset="2024", base={"STR": 16},
                 added=["longsword", "greataxe", "rapier"])
    mod = _mod(plain, "STR")
    assert _row(plain, "longsword")["offhandDamage"] == "1d8"
    assert _row(plain, "greataxe")["offhandDamage"] is None
    assert _has(plain, "longsword", "after attacking with a Light weapon")
    assert not _has(plain, "greataxe", "Dual Wielder")
    twf = _res(catalog, [("fighter", 4)], ["dual-wielder-xphb"], ruleset="2024", base={"STR": 16},
               added=["longsword"], picks={"class:fighter:1:fighting-style": ["feat:two-weapon-fighting-xphb"]})
    assert "two-weapon-fighting-xphb" in _feat_ids(twf)
    assert _row(twf, "longsword")["offhandDamage"] == f"1d8+{mod}"      # F-D5


def test_dual_wielder_phb_with_the_srd_two_weapon_fighting_style_adds_the_modifier(catalog):
    twf = _res(catalog, [("fighter", 4)], ["dual-wielder-phb"], base={"STR": 16}, added=["longsword"],
               picks={"class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-two-weapon-fighting"]})
    assert _row(twf, "shortsword" if False else "longsword")["offhandDamage"] != "1d8"
    assert _row(twf, "longsword")["offhandDamage"] == f"1d8+{_mod(twf, 'STR')}"


# ---------------------------------------------------------------- Unarmed Strike (F-D6)


def test_no_unarmed_row_without_such_a_feat(catalog):
    r = _res(catalog, [("fighter", 4)], ["alert-phb"], added=["longsword"])
    assert [a["itemId"] for a in _rows(r)] == ["longsword"]
    assert all(a["itemId"] != attacks_mod.UNARMED_STRIKE_ID for a in _rows(_res(catalog, [("fighter", 1)])))


def test_tavern_brawler_xphb_fighter_gets_a_proficient_d4_plus_strength_row(catalog):
    r = _res(catalog, [("fighter", 1)], ruleset="2024", background="sailor-xphb", base={"STR": 16, "DEX": 10})
    assert "tavern-brawler-xphb" in _feat_ids(r)
    u = _row(r, attacks_mod.UNARMED_STRIKE_ID)
    mod = _mod(r, "STR")
    assert u["damage"] == f"1d4+{mod}" and u["damageType"] == "bludgeoning" and u["ability"] == "STR"
    assert u["proficient"] is True and u["attackBonus"] == mod + r["derived"]["proficiencyBonus"]
    assert any("reroll a 1" in n for n in u["notes"]) and any("push" in n for n in u["notes"])
    assert "Martial Arts" not in u["notes"]


def test_tavern_brawler_phb_row_and_a_dex_character_still_uses_strength(catalog):
    r = _res(catalog, [("fighter", 4)], ["tavern-brawler-phb"], base={"STR": 10, "DEX": 18})
    u = _row(r, attacks_mod.UNARMED_STRIKE_ID)
    assert u["ability"] == "STR" and u["damage"] == f"1d4{_mod(r, 'STR'):+d}".replace("+0", "")
    assert any("grapple" in n for n in u["notes"])


def test_unarmed_fighting_d6_with_a_note_and_d8_when_both_hands_are_proven_empty(catalog):
    picks = {"class:fighter:1:fighting-style": ["feat:unarmed-fighting-xphb"]}
    unknown = _res(catalog, [("fighter", 1)], ruleset="2024", base={"STR": 16}, picks=picks, added=["longsword"])
    assert "unarmed-fighting-xphb" in _feat_ids(unknown)
    mod = _mod(unknown, "STR")
    u = _row(unknown, attacks_mod.UNARMED_STRIKE_ID)
    assert u["damage"] == f"1d6+{mod}"
    assert any("the 1d6 becomes a 1d8 when no weapon or Shield is held" in n for n in u["notes"])
    empty = _res(catalog, [("fighter", 1)], ruleset="2024", base={"STR": 16}, picks=picks, added=["longsword"], wielded={})
    assert _row(empty, attacks_mod.UNARMED_STRIKE_ID)["damage"] == f"1d8+{mod}"
    sword = _res(catalog, [("fighter", 1)], ruleset="2024", base={"STR": 16}, picks=picks, added=["longsword"],
                 wielded={"main": "longsword"})
    assert _row(sword, attacks_mod.UNARMED_STRIKE_ID)["damage"] == f"1d6+{mod}"
    shield = _res(catalog, [("fighter", 1)], ruleset="2024", base={"STR": 16}, picks=picks, added=["shield"],
                  wielded={"off": "shield"})
    assert _row(shield, attacks_mod.UNARMED_STRIKE_ID)["damage"] == f"1d6+{mod}"   # a Shield counts as held


def test_unarmed_fighting_d8_when_the_only_held_item_is_neither_weapon_nor_shield(catalog):
    picks = {"class:fighter:1:fighting-style": ["feat:unarmed-fighting-xphb"]}
    r = _res(catalog, [("fighter", 1)], ruleset="2024", base={"STR": 16}, picks=picks, added=["torch"],
             wielded={"main": "torch"})
    assert _row(r, attacks_mod.UNARMED_STRIKE_ID)["damage"].startswith("1d8")


def test_dragon_hide_claws_are_slashing_d4_plus_strength(catalog):
    r = _res(catalog, [("fighter", 4)], ["dragon-hide-xge"], species="dragonborn", base={"STR": 14, "DEX": 12})
    u = _row(r, attacks_mod.UNARMED_STRIKE_ID)
    assert u["damageType"] == "slashing" and u["damage"] == f"1d4+{_mod(r, 'STR')}"
    assert any("claws" in n for n in u["notes"])


def test_two_unarmed_feats_best_die_wins_the_others_are_alternatives(catalog):
    r = _res(catalog, [("fighter", 8)], ["dragon-hide-xge", "tavern-brawler-phb"], species="dragonborn",
             base={"STR": 14})
    assert {"dragon-hide-xge", "tavern-brawler-phb"} <= set(_feat_ids(r))
    rows = [a for a in _rows(r) if a["itemId"] == attacks_mod.UNARMED_STRIKE_ID]
    assert len(rows) == 1
    assert rows[0]["damage"].startswith("1d4")
    assert any(n.startswith("Alternative: ") for n in rows[0]["notes"])


def test_monk_with_tavern_brawler_has_one_row_and_martial_arts_wins(catalog):
    r = _res(catalog, [("monk", 5)], ["tavern-brawler-phb"], base={"STR": 10, "DEX": 16})
    rows = [a for a in _rows(r) if a["itemId"] == attacks_mod.UNARMED_STRIKE_ID]
    assert len(rows) == 1
    u = rows[0]
    assert u["ability"] == "DEX" and u["damage"].startswith("1d6")          # Martial Arts d6 at Monk 5 (2014 chassis)
    assert "Martial Arts" in u["notes"]
    assert "Alternative: Tavern Brawler 1d4 bludgeoning" in u["notes"]


def test_monk_4_ties_the_tavern_brawler_d4_and_martial_arts_comes_first(catalog):
    t = _res(catalog, [("monk", 4)], ["tavern-brawler-phb"], base={"STR": 10, "DEX": 16})
    u = _row(t, attacks_mod.UNARMED_STRIKE_ID)
    assert u["damage"].startswith("1d4") and u["notes"][0] == "Martial Arts"


def test_monk_with_unarmed_fighting_d8_beats_the_martial_arts_d6(catalog):
    picks = {"class:fighter:1:fighting-style": ["feat:unarmed-fighting-xphb"]}
    r = _res(catalog, [("fighter", 1), ("monk", 1)], ruleset="2024", base={"STR": 13, "DEX": 16}, picks=picks,
             wielded={})
    assert "unarmed-fighting-xphb" in _feat_ids(r)
    rows = [a for a in _rows(r) if a["itemId"] == attacks_mod.UNARMED_STRIKE_ID]
    assert len(rows) == 1
    u = rows[0]
    assert u["damage"].startswith("1d8") and u["ability"] == "DEX"         # a Monk may use Dexterity for the strike
    assert "Alternative: Martial Arts 1d6 bludgeoning" in u["notes"]
    assert "Martial Arts" not in u["notes"]
    unknown = _res(catalog, [("fighter", 1), ("monk", 1)], ruleset="2024", base={"STR": 13, "DEX": 16}, picks=picks)
    u2 = _row(unknown, attacks_mod.UNARMED_STRIKE_ID)                       # hands unknown: d6 ties, Martial Arts first
    assert u2["damage"].startswith("1d6") and u2["notes"][0] == "Martial Arts"


def test_monk_without_such_a_feat_is_identical_to_r2(catalog):
    r = _res(catalog, [("monk", 5)], ["alert-phb"], base={"DEX": 16})
    u = _row(r, attacks_mod.UNARMED_STRIKE_ID)
    assert u["notes"] == ["Martial Arts"] and u["damageType"] == "bludgeoning"


# ---------------------------------------------------------------- Revenant Blade


def test_revenant_blade_scimitar_uses_dexterity_when_better(catalog):
    r = _res(catalog, [("fighter", 4)], ["revenant-blade-erlw"], species="elf", base={"STR": 10, "DEX": 16},
             added=["double-bladed-scimitar", "greatsword"])
    s = _row(r, "double-bladed-scimitar")
    assert s["ability"] == "DEX" and s["damage"] == f"2d4+{_mod(r, 'DEX')}"
    assert _has(r, "double-bladed-scimitar", "Revenant Blade: Finesse")
    assert _row(r, "greatsword")["ability"] == "STR"


def test_without_revenant_blade_the_scimitar_uses_strength(catalog):
    r = _res(catalog, [("fighter", 4)], ["alert-phb"], species="elf", base={"STR": 10, "DEX": 16},
             added=["double-bladed-scimitar"])
    assert _row(r, "double-bladed-scimitar")["ability"] == "STR"


# ---------------------------------------------------------------- Piercer, Slasher, Crusher


@pytest.mark.parametrize("feat,ruleset,dtype,fragment", [
    ("piercer-tce", "mixed", "piercing", "Piercer"), ("slasher-tce", "mixed", "slashing", "Slasher"),
    ("crusher-tce", "mixed", "bludgeoning", "Crusher"),
    ("piercer-xphb", "2024", "piercing", "Piercer"), ("slasher-xphb", "2024", "slashing", "Slasher"),
    ("crusher-xphb", "2024", "bludgeoning", "Crusher"),
])
def test_damage_type_feats_note_only_rows_of_that_type(catalog, feat, ruleset, dtype, fragment):
    items = ["rapier", "longsword", "mace", "dagger"]
    r = _res(catalog, [("fighter", 4)], [feat], ruleset=ruleset, base={"STR": 14, "DEX": 14}, added=items)
    for item in items:
        row = _row(r, item)
        assert _has(r, item, fragment) == (row["damageType"] == dtype), (feat, item)
    assert any(_row(r, i)["damageType"] == dtype for i in items)


def test_crusher_also_covers_the_unarmed_strike_and_slasher_the_claws(catalog):
    r = _res(catalog, [("fighter", 8)], ["tavern-brawler-phb", "crusher-tce"], base={"STR": 14})
    assert _has(r, attacks_mod.UNARMED_STRIKE_ID, "Crusher")
    s = _res(catalog, [("fighter", 8)], ["dragon-hide-xge", "slasher-tce"], species="dragonborn", base={"STR": 14})
    assert _has(s, attacks_mod.UNARMED_STRIKE_ID, "Slasher")
    assert not _has(s, attacks_mod.UNARMED_STRIKE_ID, "Crusher")


# ---------------------------------------------------------------- Polearm Master, Charger


def test_polearm_master_phb_item_lists_and_the_butt_end_damage(catalog):
    r = _res(catalog, [("fighter", 4)], ["polearm-master-phb"], base={"STR": 16},
             added=["glaive", "pike", "quarterstaff", "spear", "longsword"])
    mod = _mod(r, "STR")
    for item in ("glaive", "quarterstaff", "spear"):
        assert _has(r, item, f"opposite end: 1d4+{mod} bludgeoning"), item
        assert _has(r, item, "provoke an opportunity attack")
    assert _has(r, "pike", "provoke an opportunity attack") and not _has(r, "pike", "opposite end")
    assert not _has(r, "longsword", "Polearm Master")


def test_polearm_master_xphb_quarterstaff_spear_and_heavy_reach(catalog):
    r = _res(catalog, [("fighter", 4)], ["polearm-master-xphb"], ruleset="2024", base={"STR": 16},
             added=["glaive", "pike", "quarterstaff", "spear", "longsword", "whip"])
    mod = _mod(r, "STR")
    for item in ("glaive", "pike", "quarterstaff", "spear"):   # the pike has Heavy and Reach (PHB's pole strike list differs)
        assert _has(r, item, f"Pole Strike): after the Attack action, a Bonus Action attack with the opposite end: 1d4+{mod}"), item
        assert _has(r, item, "Reactive Strike")
    for item in ("longsword", "whip"):
        assert not _has(r, item, "Polearm Master"), item
    assert sum(1 for n in _row(r, "glaive")["notes"] if "Polearm Master" in n) == 2


def test_charger_notes_carry_their_numbers_and_leave_damage_alone(catalog):
    p = _res(catalog, [("fighter", 4)], ["charger-phb"], base={"STR": 16}, added=["longsword", "longbow"])
    assert _has(p, "longsword", "+5 damage on a hit (not included in the damage shown)")
    assert not _has(p, "longbow", "Charger")
    assert _row(p, "longsword")["damage"] == f"1d8+{_mod(p, 'STR')}"
    x = _res(catalog, [("fighter", 4)], ["charger-xphb"], ruleset="2024", base={"STR": 16}, added=["longsword", "longbow"])
    assert _has(x, "longsword", "+1d8 damage or push it up to 10 feet")
    assert not _has(x, "longbow", "Charger")


# ---------------------------------------------------------------- Gunner, Elven Accuracy, Orcish Fury, Poisoner, Bomber


def test_gunner_makes_firearms_proficient_and_notes_them(catalog):
    r = _res(catalog, [("wizard", 4)], ["gunner-tce"], base={"DEX": 14}, added=["pistol", "musket", "crossbow-hand"])
    for item in ("pistol", "musket"):
        assert _row(r, item)["proficient"] is True, item          # firearms proficiency from the feat
        assert _has(r, item, "Gunner: ignore the loading property")
    assert not _has(r, "crossbow-hand", "Gunner")
    assert "firearms" in r["sheet"]["proficiencies"]["weapons"]
    plain = _res(catalog, [("wizard", 4)], ["alert-phb"], base={"DEX": 14}, added=["pistol"])
    assert _row(plain, "pistol")["proficient"] is False


def test_elven_accuracy_only_on_dex_int_wis_cha_attacks(catalog):
    r = _res(catalog, [("fighter", 4)], ["elven-accuracy-xge"], species="elf", base={"STR": 10, "DEX": 16},
             added=["rapier", "greatsword", "longbow"])
    assert _has(r, "rapier", "Elven Accuracy")       # finesse with DEX 16
    assert _has(r, "longbow", "Elven Accuracy")
    assert not _has(r, "greatsword", "Elven Accuracy")   # STR


def test_orcish_fury_row_note_names_the_extra_die(catalog):
    r = _res(catalog, [("fighter", 4)], ["orcish-fury-xge"], species="half-orc", base={"STR": 16},
             added=["greatsword", "longsword", "net"])
    assert _has(r, "greatsword", "+1d6 slashing extra damage (once per short or long rest)")
    assert _has(r, "longsword", "+1d8 slashing extra damage")
    assert not any("Orcish Fury" in n for n in _row(r, "net")["notes"])    # no damage die


def test_poisoner_tce_fixed_dc_and_xphb_uses_the_increased_ability(catalog):
    t = _res(catalog, [("fighter", 4)], ["poisoner-tce"], added=["dagger"])
    assert _has(t, "dagger", "DC 14 Constitution save")
    # FX2: the creature must SUCCEED on the save, or take the damage (the note once said it fails)
    assert _has(t, "dagger", "must succeed on a DC 14 Constitution save or take 2d8 poison damage")
    assert not _has(t, "dagger", "fails a DC 14")
    x = _res(catalog, [("fighter", 4)], ["poisoner-xphb"], ruleset="2024", base={"DEX": 14, "INT": 14},
             added=["dagger"], picks={"class:fighter:4:asi:feat:poisoner-xphb:ability-bonus": ["int"]})
    pb = x["derived"]["proficiencyBonus"]
    assert _has(x, "dagger", f"DC {8 + _mod(x, 'INT') + pb} Constitution save")
    pending = _res(catalog, [("fighter", 4)], ["poisoner-xphb"], ruleset="2024", added=["dagger"])
    assert _has(pending, "dagger", "DC (choose the ability) Constitution save")


def test_bomber_notes_thrown_weapons(catalog):
    r = _res(catalog, [("fighter", 4)], ["bomber-abh"], added=["dagger", "handaxe", "longsword"])
    assert _has(r, "dagger", "Bomber") and _has(r, "handaxe", "Bomber")
    assert not _has(r, "longsword", "Bomber")


def test_boon_of_irresistible_offense_notes_resistance_and_the_increased_score(catalog):
    r = _res(catalog, [("fighter", 19)], ["boon-of-irresistible-offense-xphb"], ruleset="2024", base={"STR": 18},
             added=["longsword"], picks={"class:fighter:19:asi:feat:boon-of-irresistible-offense-xphb:ability-bonus": ["str"]})
    assert "boon-of-irresistible-offense-xphb" in _feat_ids(r)
    score = r["sheet"]["abilityScores"]["STR"] if "abilityScores" in r["sheet"] else None
    assert _has(r, "longsword", "your slashing damage always ignores Resistance")
    assert _has(r, "longsword", "extra damage equal to ")
    note = next(n for n in _row(r, "longsword")["notes"] if "extra damage equal to" in n)
    assert "choose" not in note
    if score is not None:
        assert f"equal to {score}" in note
    pending = _res(catalog, [("fighter", 19)], ["boon-of-irresistible-offense-xphb"], ruleset="2024", added=["longsword"])
    assert _has(pending, "longsword", "(choose the ability)")


# ---------------------------------------------------------------- engine invariants


def test_unarmed_strike_without_a_feat_is_the_r2_row():
    row = attacks_mod.unarmed_strike({"STR": 3, "DEX": 1}, 2, "d6")
    assert row["damage"] == "1d6+3" and row["notes"] == ["Martial Arts"] and row["damageType"] == "bludgeoning"
    assert attacks_mod.unarmed_strike({"STR": 0, "DEX": 0}, 2, None)["damage"] == "1"


def test_pure_unarmed_spec_picks_the_best_die_and_prefers_martial_arts_on_a_tie(catalog):
    insts = fe.instances([catalog.feats["tavern-brawler-phb"], catalog.feats["dragon-hide-xge"]], fed.FEAT_EFFECTS, [])
    spec = fe.unarmed_spec(insts, None, [], "d4", monk=True)
    assert spec["die"] is None and spec["notes"][0] == "Martial Arts"       # d4 ties: Martial Arts first
    spec = fe.unarmed_spec(insts, None, [], "d6", monk=True)
    assert spec["die"] is None
    spec = fe.unarmed_spec(insts, None, [], None, monk=False)
    assert spec["die"] == "1d4" and spec["type"] == "bludgeoning"           # the first feat held wins the tie
    assert fe.unarmed_spec([], None, [], "d6", monk=True) is None


def test_pure_attack_flags(catalog):
    insts = fe.instances([catalog.feats[i] for i in ("dual-wielder-phb", "crossbow-expert-xphb", "revenant-blade-erlw")],
                         fed.FEAT_EFFECTS, [])
    flags = fe.attack_flags(insts)
    assert flags == {"offhand_non_light": True, "offhand_dw2024": False, "offhand_light_crossbow_mod": True,
                     "offhand_hand_crossbow_mod": False, "finesse_items": frozenset({"double-bladed-scimitar"})}
    assert fe.attack_flags([]) == {"offhand_non_light": False, "offhand_dw2024": False,
                                   "offhand_light_crossbow_mod": False, "offhand_hand_crossbow_mod": False,
                                   "finesse_items": frozenset()}


def test_pure_attack_flags_crossbow_expert_phb(catalog):
    insts = fe.instances([catalog.feats["crossbow-expert-phb"]], fed.FEAT_EFFECTS, [])
    flags = fe.attack_flags(insts)
    assert flags["offhand_hand_crossbow_mod"] is True and flags["offhand_light_crossbow_mod"] is False


def test_weapon_attack_flags_are_off_by_default():
    sword = {"index": "longsword", "name": "Longsword", "equipment_category": {"index": "weapon"}, "weapon_range": "Melee",
             "weapon_category": "Martial", "properties": [{"index": "versatile"}],
             "damage": {"damage_dice": "1d8", "damage_type": {"index": "slashing"}},
             "two_handed_damage": {"damage_dice": "1d10", "damage_type": {"index": "slashing"}}}
    base = attacks_mod.weapon_attack(sword, {"STR": 3}, 2, {"martial-weapons"}, {})
    assert base["offhandDamage"] is None
    dw = attacks_mod.weapon_attack(sword, {"STR": 3}, 2, {"martial-weapons"}, {"offhand_non_light": True})
    assert dw["offhandDamage"] == "1d8"
    dw_twf = attacks_mod.weapon_attack(sword, {"STR": 3}, 2, {"martial-weapons"},
                                       {"offhand_dw2024": True, "two_weapon_fighting": True})
    assert dw_twf["offhandDamage"] == "1d8+3"


def test_a_feat_less_draft_has_identical_rows_to_a_draft_with_a_non_attack_feat(catalog):
    a = _res(catalog, [("fighter", 4)], [], added=["longsword", "longbow", "dagger"])
    b = _res(catalog, [("fighter", 4)], ["alert-phb"], added=["longsword", "longbow", "dagger"])
    assert _rows(a) == _rows(b)


def test_empty_catalog_degrades_to_no_feat_effects():
    """No official data: catalog.feats is empty, so no instance exists and every FE5 path is a no-op."""
    insts = fe.instances([], fed.FEAT_EFFECTS, [])
    assert fe.annotate_attacks([ROW], [], insts, {}) == [ROW]
    assert fe.unarmed_spec(insts, None, [], None) is None
    assert fe.attack_flags(insts)["finesse_items"] == frozenset()


def test_hidden_kept_feat_keeps_its_attack_notes(catalog):
    """A2: a pick kept while its source is filtered out of the sheet's feat list still counts as held."""
    r = _res(catalog, [("fighter", 4)], ["savage-attacker-phb"], ruleset="2024", added=["longsword"])
    assert "savage-attacker-phb" in _feat_ids(r)
    assert _has(r, "longsword", "Savage Attacker")


def test_resolve_stays_fast_with_attack_feats(catalog):
    feats = ["great-weapon-master-xphb", "polearm-master-xphb", "crusher-xphb", "dual-wielder-xphb", "piercer-xphb"]
    items = ["glaive", "greataxe", "longsword", "rapier", "mace", "longbow", "crossbow-hand", "dagger"]
    _res(catalog, [("fighter", 19)], feats, ruleset="2024", base={"STR": 16, "DEX": 14}, added=items)  # warm up
    laps = []
    for _ in range(10):
        t_run = time.perf_counter()
        _res(catalog, [("fighter", 19)], feats, ruleset="2024", base={"STR": 16, "DEX": 14}, added=items)
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
