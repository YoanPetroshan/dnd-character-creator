"""R8: SRD Eldritch Invocation effects (decision D6).

RAW (SRD 5.1 Warlock invocations), checked against catalog.features text:
- Armor of Shadows: mage armor on yourself at will. Modelled as an AC candidate
  formula 13 + DEX (best formula wins, never stacked with Unarmored Defense).
- Devil's Sight: see normally in darkness, magical or not, 120 ft. Modelled as
  senses.devilsSight 120; darkvision is not overridden.
- "cast X at will" -> innate spell at-will; "cast X once using a warlock spell
  slot ... until you finish a long rest" -> innate spell "1/long rest".
- Beguiling Influence: Deception and Persuasion proficiency.
- Agonizing Blast: Charisma modifier added to eldritch blast damage (resource bonus).
- Level-down: an invocation whose prerequisite is lost is pruned by the gate and
  its effect disappears.
Rule matrix: AC (armor of shadows alone / with Unarmored Defense / with body armor),
skills, senses, innate at-will vs 1/long rest, resource bonus, level-down, table
verified against the SRD feature text and spell ids.
"""
import dataclasses
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from engine.resolve import resolve

INV = "class:warlock:2:invocations:eldritch-invocations"
P = "eldritch-invocation-"


@pytest.fixture(scope="module")
def full_catalog():
    return load()


@pytest.fixture(scope="module")
def catalog(full_catalog):
    """The Warlock's fixed starting kit includes leather armor, and the engine counts every
    granted item as worn (decision D3), so Armor of Shadows could never apply. These tests use a
    catalog copy whose Warlock has no fixed kit, i.e. a warlock who wears no armor."""
    classes = dict(full_catalog.classes)
    classes["warlock"] = {**classes["warlock"], "starting_equipment": []}
    return dataclasses.replace(full_catalog, classes=classes)


def _draft(classes, base=None, equipment=None):
    return {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **(base or {})}},
        "equipment": equipment or {"choices": {}, "added": [], "skipped": False}, "details": {},
    }


def _warlock(level, picks, extra_choices=None):
    ch = {INV: [P + p for p in picks], **(extra_choices or {})}
    return {"classId": "warlock", "level": level, "choices": ch}


def _innate(r, spell):
    return [e for e in r["sheet"]["innateSpells"] if e["spellId"] == spell]


def test_armor_of_shadows_and_devils_sight(catalog):
    r = resolve(_draft([_warlock(2, ["armor-of-shadows", "devils-sight"])], {"DEX": 14}), catalog)
    assert r["derived"]["armorClass"] == 15  # 13 + DEX 2 (human +1)
    assert r["sheet"]["senses"]["devilsSight"] == 120
    assert "darkvision" not in r["sheet"]["senses"]
    e = _innate(r, "mage-armor")
    assert len(e) == 1 and e[0]["uses"] == "at-will" and e[0]["ability"] == "CHA"
    assert e[0]["source"] == "Eldritch Invocation"


def test_without_invocations_nothing_changes(catalog):
    r = resolve(_draft([_warlock(2, [])], {"DEX": 14}), catalog)
    assert r["derived"]["armorClass"] == 12
    assert "devilsSight" not in r["sheet"]["senses"]
    assert r["sheet"]["innateSpells"] == []


def test_warlock_starting_kit_leather_armor_switches_formula_off(full_catalog):
    # Documents the D3 limitation: the granted leather armor counts as worn (11 + DEX 2 = 13).
    r = resolve(_draft([_warlock(2, ["armor-of-shadows"])], {"DEX": 14}), full_catalog)
    assert r["derived"]["armorClass"] == 13


def test_armor_of_shadows_body_armor_wins_formula_off(catalog):
    eq = {"choices": {}, "added": [{"itemId": "chain-mail", "qty": 1, "equipped": True}], "skipped": False}
    r = resolve(_draft([_warlock(2, ["armor-of-shadows"])], {"DEX": 14}, eq), catalog)
    assert r["derived"]["armorClass"] == 16


def test_beguiling_influence_skills(catalog):
    r = resolve(_draft([_warlock(2, ["beguiling-influence"])]), catalog)
    skills = r["sheet"]["proficiencies"]["skills"]
    assert "skill-deception" in skills and "skill-persuasion" in skills
    assert r["derived"]["skills"]["skill-deception"] == r["derived"]["skills"]["skill-persuasion"]


def test_agonizing_blast_resource_bonus(catalog):
    # CHA 15 + human 1 = 16 -> +3
    ch = {"class:warlock:spells-cantrips": ["eldritch-blast", "mage-hand"]}
    r = resolve(_draft([_warlock(2, ["agonizing-blast"], ch)], {"CHA": 15}), catalog)
    res = [x for x in r["derived"]["classResources"] if x["name"] == "Agonizing Blast"]
    assert len(res) == 1 and res[0]["bonus"] == 3 and res[0]["details"]["spell"] == "eldritch-blast"


def test_agonizing_blast_without_eldritch_blast_is_pruned(catalog):
    r = resolve(_draft([_warlock(2, ["agonizing-blast"])], {"CHA": 15}), catalog)
    assert not [x for x in r["derived"]["classResources"] if x["name"] == "Agonizing Blast"]


def test_sign_of_ill_omen_and_level_down(catalog):
    r = resolve(_draft([_warlock(9, ["sign-of-ill-omen"])]), catalog)
    e = _innate(r, "bestow-curse")
    assert len(e) == 1 and e[0]["uses"] == "1/long rest" and e[0]["level"] == 3
    r = resolve(_draft([_warlock(4, ["sign-of-ill-omen"])]), catalog)
    assert _innate(r, "bestow-curse") == []
    assert any(p["choiceId"] == INV for p in r["pruned"])


def test_notes_for_text_only_invocations(catalog):
    ch = {"class:warlock:spells-cantrips": ["eldritch-blast", "mage-hand"],
          "class:warlock:3:feature:pact-boon": ["pact-of-the-blade"]}
    r = resolve(_draft([_warlock(5, ["thirsting-blade", "repelling-blast"], ch)]), catalog)
    names = {x["name"]: x for x in r["derived"]["classResources"]}
    assert "note" in names["Thirsting Blade"]["details"]
    assert "note" in names["Repelling Blast"]["details"]


def test_armor_of_shadows_vs_unarmored_defense_best_no_stack(catalog):
    # DEX 14+1 = +2, CON 16+1 = +3: Barbarian 10+2+3 = 15 beats 13+2 = 15 (tie), never 18.
    classes = [{"classId": "barbarian", "level": 1, "choices": {}}, _warlock(2, ["armor-of-shadows"])]
    r = resolve(_draft(classes, {"DEX": 14, "CON": 16}), catalog)
    assert r["derived"]["armorClass"] == 15
    # CON 12+1 = +1: Barbarian 13, Armor of Shadows 15 wins
    r = resolve(_draft(classes, {"DEX": 14, "CON": 12}), catalog)
    assert r["derived"]["armorClass"] == 15
    # CON 20+1 = +5: Barbarian 17 wins
    r = resolve(_draft(classes, {"DEX": 14, "CON": 20}), catalog)
    assert r["derived"]["armorClass"] == 17


# ---- the table is verified against the SRD text and spell ids ---------------

def test_every_table_entry_matches_srd_text_and_spells(full_catalog):
    catalog = full_catalog
    for fid, eff in reference_data.INVOCATION_EFFECTS.items():
        assert fid.startswith(P) and fid in catalog.features, fid
        text = " ".join(catalog.features[fid]["desc"]).lower()
        spell = eff.get("innate_spell")
        if spell:
            sp = catalog.spells[spell["spell"]]
            assert sp["level"] == spell["level"], fid
            assert f"cast {sp['name'].lower()}" in text, fid
            if spell["uses"] == "at-will":
                assert "at will" in text, fid
            else:
                assert spell["uses"] == "1/long rest"
                assert "once using a warlock spell slot" in text and "long rest" in text, fid
        if "skills" in eff:
            for s in eff["skills"]:
                assert s.split("-", 1)[1] in text, fid
        if "senses" in eff:
            assert "120 feet" in text, fid


def test_innate_spell_entries_cover_plan_list():
    expected = {
        "armor-of-shadows": "mage-armor", "ascendant-step": "levitate", "beast-speech": "speak-with-animals",
        "eldritch-sight": "detect-magic", "fiendish-vigor": "false-life", "mask-of-many-faces": "disguise-self",
        "misty-visions": "silent-image", "otherworldly-leap": "jump", "master-of-myriad-forms": "alter-self",
        "thief-of-five-fates": "bane", "mire-the-mind": "slow", "sign-of-ill-omen": "bestow-curse",
        "bewitching-whispers": "compulsion", "dreadful-word": "confusion", "minions-of-chaos": "conjure-elemental",
        "sculptor-of-flesh": "polymorph", "chains-of-carceri": "hold-monster", "whispers-of-the-grave": "speak-with-dead",
        "visions-of-distant-realms": "arcane-eye",
    }
    got = {k[len(P):]: v["innate_spell"]["spell"] for k, v in reference_data.INVOCATION_EFFECTS.items() if "innate_spell" in v}
    assert got == expected


def test_resolve_speed_warlock_17(catalog):
    picks = ["armor-of-shadows", "devils-sight", "beguiling-influence", "ascendant-step", "sign-of-ill-omen",
             "whispers-of-the-grave", "visions-of-distant-realms", "master-of-myriad-forms", "minions-of-chaos"]
    d = _draft([_warlock(17, picks)])
    resolve(d, catalog)
    t = time.perf_counter()
    for _ in range(20):
        resolve(d, catalog)
    assert (time.perf_counter() - t) / 20 < 0.05
