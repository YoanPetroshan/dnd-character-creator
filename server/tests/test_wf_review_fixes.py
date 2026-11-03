"""WF: fixes for the read-only review of W1-W5b."""
from __future__ import annotations

import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, species, sub=None, cls="fighter", level=5, ruleset="mixed", base=None, added=(), background="acolyte",
         species_choices=None, bg_choices=None, class_choices=None, extra=None):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    sp = {"id": species, "choices": species_choices or {}}
    if sub:
        sp["subspeciesId"] = sub
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": class_choices or {}}],
         "background": {"id": background, "choices": bg_choices or {}}, "species": sp,
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added], "skipped": True},
         "details": {}, "preferences": {}}
    d.update(extra or {})
    return resolve(d, catalog)


# ---------------------------------------------------------------- (1) equal-to-walk species modes

EQUAL_MODES = [
    ("aarakocra-mpmm", None, "fly"), ("dhampir-rhw", None, "climb"), ("dhampir-vrgr", None, "climb"),
    ("fairy-mpmm", None, "fly"), ("fairy-wbtw", None, "fly"), ("giff-aag", None, "swim"),
    ("hadozee-aag", None, "climb"), ("lizardfolk-mpmm", None, "swim"), ("owlin-scc", None, "fly"),
    ("sea-elf-mpmm", None, "swim"), ("tabaxi-mpmm", None, "climb"), ("triton-mpmm", None, "swim"),
    ("genasi-mpmm", "genasi-mpmm-water-mpmm", "swim"),
]


@pytest.mark.parametrize("species,sub,mode", EQUAL_MODES)
def test_equal_mode_follows_heavy_armor_penalty(catalog, species, sub, mode):
    base = _res(catalog, species, sub)["derived"]["speeds"]["walk"]
    s = _res(catalog, species, sub, added=["chain-mail"], base={"STR": 12})["derived"]["speeds"]
    if mode == "fly":  # X1: the species text bans the flying speed in heavy armor, so it is removed, not lowered
        assert s["walk"] == base - 10 and "fly" not in s, s
        return
    assert s["walk"] == base - 10 and s[mode] == base - 10, s


@pytest.mark.parametrize("species,sub,mode", EQUAL_MODES)
def test_equal_mode_follows_walk_bonus(catalog, species, sub, mode):
    base = _res(catalog, species, sub)["derived"]["speeds"]["walk"]
    s = _res(catalog, species, sub, cls="barbarian", level=5)["derived"]["speeds"]
    assert s["walk"] == base + 10 and s[mode] == base + 10, s


@pytest.mark.parametrize("species,sub,mode", EQUAL_MODES)
def test_equal_mode_plain(catalog, species, sub, mode):
    s = _res(catalog, species, sub)["derived"]["speeds"]
    assert s[mode] == s["walk"]


def test_equal_mode_floor_zero_and_unaffected_numeric(catalog):
    s = _res(catalog, "sea-elf-mpmm", added=["plate-armor"], base={"STR": 8})["derived"]["speeds"]
    assert s["walk"] == 20 and s["swim"] == 20
    # a numeric swim (Triton-like numbers are not "equal to walk") keeps its value
    s2 = _res(catalog, "human", added=["chain-mail"], base={"STR": 12})["derived"]["speeds"]
    assert "swim" not in s2


# ---------------------------------------------------------------- (2) Magic Initiate: a different list each time
# XPHB Magic Initiate, entry "Repeatable": "You can take this feat more than once, but you must choose a different
# spell list each time."  PHB 2014 Magic Initiate has no such sentence and `repeatable` false (not repeatable at all).

MI_QUOTE = "you must choose a different spell list each time"
MI = "magic-initiate-xphb"
BG_V = "feat:magic-initiate-xphb:spell-variant"
SP_V = "species:human-xphb:feat-0:feat:magic-initiate-xphb:spell-variant"
ASI_V = "class:fighter:4:asi:feat:magic-initiate-xphb:spell-variant"
SP_PICK = {"species:human-xphb:feat-0": ["feat:magic-initiate-xphb"]}


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opts(card):
    return {o["id"]: o for o in card["options"]}


def test_quote_pins(catalog):
    import json
    assert MI_QUOTE in json.dumps(catalog.feats["magic-initiate-xphb"]["entries"])
    assert catalog.feats["magic-initiate-xphb"]["repeatable"] is True
    assert catalog.feats["magic-initiate-phb"]["repeatable"] is False
    assert "different spell list" not in json.dumps(catalog.feats["magic-initiate-phb"]["entries"])


def test_genie_wizard_blocks_wizard_in_species_copy(catalog):
    res = _res(catalog, "human-xphb", ruleset="2024", level=1, background="genie-touched-frhof",
               species_choices=SP_PICK, extra={"sources": ["srd", "phb", "xphb", "frhof"]})
    o = _opts(_card(res, SP_V))
    assert o["wizard-spells"]["disabled"] and "already chosen for Magic Initiate (1)" in o["wizard-spells"]["disabledReason"]
    assert not o["cleric-spells"].get("disabled") and not o["druid-spells"].get("disabled")
    first = _card(res, BG_V)  # the fixed Wizard card itself is not blocked by its own list
    assert not _opts(first)["wizard-spells"].get("disabled")


def test_stored_duplicate_list_is_pruned_with_its_spell_picks(catalog):
    choices = dict(SP_PICK)
    choices[SP_V] = ["wizard-spells"]
    res = _res(catalog, "human-xphb", ruleset="2024", background="genie-touched-frhof", species_choices=choices,
               extra={"sources": ["srd", "phb", "xphb", "frhof"]})
    card = _card(res, SP_V)
    assert card["selected"] == [] and card["status"] == "pending"
    assert any(p["choiceId"] == SP_V and "already chosen for Magic Initiate (1)" in p["reason"] for p in res["pruned"])
    assert not [c for c in res["choices"] if c["id"].startswith(SP_V[:-len("spell-variant")] + "spell-choice-")]
    assert not any(p["choiceId"] == SP_V and p.get("blocking") for p in res["pruned"])


def test_species_pick_then_asi_copy_blocks_taken_list(catalog):
    c = dict(SP_PICK)
    c[SP_V] = ["cleric-spells"]
    res = _res(catalog, "human-xphb", ruleset="2024", level=4, background="genie-touched-frhof", species_choices=c,
               class_choices={"class:fighter:4:asi": ["feat:magic-initiate-xphb"]},
               extra={"sources": ["srd", "phb", "xphb", "frhof"]})
    o = _opts(_card(res, ASI_V))
    assert o["wizard-spells"]["disabled"] and o["cleric-spells"]["disabled"] and not o["druid-spells"].get("disabled")
    assert "(2)" in o["cleric-spells"]["disabledReason"]


def test_single_copy_is_unrestricted(catalog):
    res = _res(catalog, "human-xphb", ruleset="2024", level=4, background="acolyte",
               class_choices={"class:fighter:4:asi": ["feat:magic-initiate-xphb"]})
    o = _opts(_card(res, ASI_V))
    assert not any(x.get("disabled") for x in o.values()) and len(o) == 3


def test_2014_magic_initiate_is_not_repeatable_and_has_no_distinct_group(catalog):
    res = _res(catalog, "human", ruleset="2014", level=4, background="acolyte",
               class_choices={"class:fighter:4:asi": ["feat:magic-initiate-phb"]})
    assert not any("distinctGroup" in c or "distinctFixed" in c for c in res["choices"])


# ---------------------------------------------------------------- (3) the two Lucky duplicates

@pytest.mark.parametrize("species,tid", [("halfling-phb", "halfling-phb-trait-2"), ("kor-psz", "kor-psz-trait-7")])
def test_lucky_duplicates_are_note_only_resources(catalog, species, tid):
    res = _res(catalog, species, ruleset="2014", background="acolyte")
    entry = next(e for e in res["derived"]["speciesResources"] if e["traitId"] == tid)
    assert entry["name"] == "Lucky" and entry["uses"] is None and entry["recharge"] is None
    assert "reroll the die" in entry["details"]["note"]


def test_no_other_trait_is_word_for_word_a_modelled_one(catalog):
    from catalog import reference_data as ref
    import re
    table = {**ref.SPECIES_RESOURCES, **ref.SPECIES_RESOURCES_2014}

    def norm(t):
        d = " ".join(t["desc"]) if isinstance(t["desc"], list) else str(t["desc"])
        return re.sub(r"\s+", " ", re.sub(r"\{@\w+ ([^}|]*)[^}]*\}", r"\1", d)).strip().lower()
    modelled = {norm(catalog.traits[t]) for t in table if t in catalog.traits}
    missing = [t for t, tr in catalog.traits.items() if t not in table and norm(tr) in modelled
               and (tr.get("races") or tr.get("subraces"))]
    assert missing == []


# ---------------------------------------------------------------- (4) clamped base plus species bonus

def test_clamped_base_plus_species_bonus_message_names_the_final_score(catalog):
    res = _res(catalog, "half-orc", ruleset="2014", base={"STR": 31})
    msgs = [p["message"] for p in res["problems"] if p["id"] == "ability-out-of-range-STR"]
    assert len(msgs) == 1
    assert res["derived"]["abilityModifiers"]["STR"] == 11 and "32" in msgs[0] and "using 30 instead" in msgs[0]
    assert "final STR score is 32" in msgs[0]


def test_clamped_base_without_bonus_keeps_the_plain_message(catalog):
    res = _res(catalog, "human-xphb", ruleset="2024", base={"CHA": 99})
    msgs = [p["message"] for p in res["problems"] if p["id"] == "ability-out-of-range-CHA"]
    assert len(msgs) == 1 and "final" not in msgs[0] and "using 30 instead" in msgs[0]


# ---------------------------------------------------------------- (5) Breath Weapon note before the ancestry is picked

@pytest.mark.parametrize("species", ["dragonborn", "dragonborn-phb", "dragonborn-xphb", "dragonborn-(chromatic)-ftd",
                                     "dragonborn-(gem)-ftd", "dragonborn-(metallic)-ftd"])
def test_breath_weapon_note_unpicked_reads_well(catalog, species):
    res = _res(catalog, species, ruleset="2014", level=6)
    note = next(e for e in res["derived"]["speciesResources"] if e["name"] == "Breath Weapon")["details"]["note"]
    assert "choose your Draconic Ancestry to see the damage type" in note
    for bad in ("saving throw (set by", "saving throw saving", "the Draconic Ancestry's type", "(choose the ancestry)",
                "the area set by", "{", "  "):
        assert bad not in note, (species, note)
    assert " damage on a failed save" in note and "d" in note


def test_srd_breath_weapon_picked_is_unchanged(catalog):
    res = _res(catalog, "dragonborn", ruleset="2014", level=6,
               species_choices={"species:dragonborn:trait:draconic-ancestry": ["draconic-ancestry-red"]})
    note = next(e for e in res["derived"]["speciesResources"] if e["name"] == "Breath Weapon")["details"]["note"]
    assert "choose" not in note and "Fire" in note and "3d6" in note
