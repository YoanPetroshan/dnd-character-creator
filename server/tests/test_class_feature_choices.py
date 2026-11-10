"""Slice 5: class-feature choices beyond subfeature_options (expertise, ranger
enemy/terrain types, Eldritch Invocations), subclass spells (always prepared /
Fiend expanded list) and fixed subclass proficiency grants. Expected values come
from the 5e SRD rules, not from the code under test."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, base=None, background="acolyte"):
    return {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": background, "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 16, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **(base or {})}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }


def _cls(cid, level, subclass=None, choices=None):
    e = {"classId": cid, "level": level, "choices": choices or {}}
    if subclass:
        e["subclassId"] = subclass
    return e


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


ROGUE_SKILLS = ["skill-acrobatics", "skill-stealth", "skill-perception", "skill-insight"]
EXP1 = "class:rogue:1:expertise-choice:rogue-expertise-1"
EXP2 = "class:rogue:6:expertise-choice:rogue-expertise-2"


def _rogue(level, expertise=None, expertise2=None):
    ch = {"class:rogue:1:prof-choice-0": ROGUE_SKILLS}
    if expertise is not None:
        ch[EXP1] = expertise
    if expertise2 is not None:
        ch[EXP2] = expertise2
    return _cls("rogue", level, choices=ch)


# ---- expertise -------------------------------------------------------------

def test_rogue_expertise_offered_at_1_and_6(catalog):
    r1 = resolve(_draft([_rogue(1)]), catalog)
    c = _choice(r1, EXP1)
    assert c and c["count"] == 2 and c["status"] == "pending"
    assert _choice(r1, EXP2) is None
    assert _choice(resolve(_draft([_rogue(6)]), catalog), EXP2)["count"] == 2


def test_expertise_options_only_proficient_enabled(catalog):
    c = _choice(resolve(_draft([_rogue(1)]), catalog), EXP1)
    enabled = {o["id"] for o in c["options"] if not o.get("disabled")}
    # Acolyte grants insight + religion; the rogue picked four more.
    assert enabled == set(ROGUE_SKILLS) | {"skill-religion", "thieves-tools"}
    assert next(o for o in c["options"] if o["id"] == "skill-arcana")["disabledReason"] == "not proficient"


def test_rogue_expertise_selection_feeds_sheet_and_skills(catalog):
    r = resolve(_draft([_rogue(1, ["skill-stealth", "skill-acrobatics"])]), catalog)
    assert r["sheet"]["expertiseSkills"] == ["skill-stealth", "skill-acrobatics"]
    # DEX 16 -> +3, proficiency +2 doubled
    assert r["derived"]["skills"]["skill-stealth"] == 7
    assert r["derived"]["skills"]["skill-perception"] == 2  # WIS 10 +0, proficient, not expert
    assert _choice(r, EXP1)["status"] == "resolved"
    # Expertise is not a proficiency grant.
    assert r["sheet"]["proficiencies"]["skills"].count("skill-stealth") == 1


def test_rogue_expertise_thieves_tools(catalog):
    r = resolve(_draft([_rogue(1, ["skill-stealth", "thieves-tools"])]), catalog)
    assert "thieves-tools" in r["sheet"]["expertiseSkills"]
    assert r["derived"]["skills"]["skill-stealth"] == 7


def test_expertise_in_nonproficient_skill_is_dropped(catalog):
    r = resolve(_draft([_rogue(1, ["skill-arcana", "skill-stealth"])]), catalog)
    assert r["sheet"]["expertiseSkills"] == ["skill-stealth"]
    assert any(p["choiceId"] == EXP1 for p in r["pruned"])
    assert _choice(r, EXP1)["status"] == "pending"


def test_expertise_dropped_when_proficiency_removed(catalog):
    d = _draft([_rogue(1, ["skill-stealth", "skill-acrobatics"])])
    d["classes"][0]["choices"]["class:rogue:1:prof-choice-0"] = ["skill-acrobatics", "skill-perception", "skill-insight", "skill-athletics"]
    r = resolve(d, catalog)
    assert r["sheet"]["expertiseSkills"] == ["skill-acrobatics"]


def test_same_skill_in_both_expertise_choices_counts_once(catalog):
    r = resolve(_draft([_rogue(6, ["skill-stealth", "skill-acrobatics"], ["skill-stealth", "skill-perception"])]), catalog)
    assert r["sheet"]["expertiseSkills"] == ["skill-stealth", "skill-acrobatics", "skill-perception"]


def test_bard_expertise_levels(catalog):
    def bard(level):
        return resolve(_draft([_cls("bard", level)]), catalog)
    assert not [c for c in bard(2)["choices"] if "expertise" in c["id"]]
    ids3 = [c["id"] for c in bard(3)["choices"] if "expertise" in c["id"]]
    assert ids3 == ["class:bard:3:expertise-choice:bard-expertise-1"]
    assert len([c for c in bard(10)["choices"] if "expertise" in c["id"]]) == 2
    assert _choice(bard(3), ids3[0])["count"] == 2


# ---- ranger enemy / terrain -----------------------------------------------

def test_ranger_favored_enemy_and_terrain_choices(catalog):
    r = resolve(_draft([_cls("ranger", 6)]), catalog)
    enemy = [c for c in r["choices"] if ":enemy-type:" in c["id"]]
    terrain = [c for c in r["choices"] if ":terrain-type:" in c["id"]]
    assert [c["id"] for c in enemy] == ["class:ranger:1:enemy-type:favored-enemy-1-type", "class:ranger:6:enemy-type:favored-enemy-2-types"]
    assert [c["id"] for c in terrain] == ["class:ranger:1:terrain-type:natural-explorer-1-terrain-type", "class:ranger:6:terrain-type:natural-explorer-2-terrain-types"]
    assert all(c["count"] == 1 for c in enemy + terrain)
    assert {o["id"] for o in enemy[0]["options"]} >= {"aberrations", "beasts", "undead", "humanoids"}
    assert {o["id"] for o in terrain[0]["options"]} == {"arctic", "coast", "desert", "forest", "grassland", "mountain", "swamp"}


def test_ranger_enemy_selection_resolves_and_is_not_a_proficiency(catalog):
    d = _draft([_cls("ranger", 1, choices={"class:ranger:1:enemy-type:favored-enemy-1-type": ["undead"]})])
    r = resolve(d, catalog)
    assert _choice(r, "class:ranger:1:enemy-type:favored-enemy-1-type")["status"] == "resolved"
    assert not any("undead" in v for v in r["sheet"]["proficiencies"].values())
    assert not r["pruned"]


def test_ranger_14_has_three_enemy_choices(catalog):
    r = resolve(_draft([_cls("ranger", 14)]), catalog)
    assert len([c for c in r["choices"] if ":enemy-type:" in c["id"]]) == 3
    assert len([c for c in r["choices"] if ":terrain-type:" in c["id"]]) == 3  # levels 1, 6, 10


# ---- subclass spells ------------------------------------------------------

def _always(res, cls_id):
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == cls_id)
    return [s["id"] for s in entry["alwaysPrepared"]]


def test_life_cleric_domain_spells_by_level(catalog):
    assert _always(resolve(_draft([_cls("cleric", 1, "life")]), catalog), "cleric") == ["bless", "cure-wounds"]
    assert _always(resolve(_draft([_cls("cleric", 4, "life")]), catalog), "cleric") == [
        "bless", "cure-wounds", "lesser-restoration", "spiritual-weapon"]
    assert _always(resolve(_draft([_cls("cleric", 5, "life")]), catalog), "cleric")[-2:] == ["beacon-of-hope", "revivify"]


def test_domain_spells_do_not_use_up_prepared_slots(catalog):
    plain = resolve(_draft([_cls("cleric", 5)], {"WIS": 16}), catalog)
    life = resolve(_draft([_cls("cleric", 5, "life")], {"WIS": 16}), catalog)
    assert _choice(plain, "class:cleric:spells-known")["count"] == _choice(life, "class:cleric:spells-known")["count"] == 8  # WIS +3 + 5
    assert _always(plain, "cleric") == []


def test_domain_spells_are_marked_in_prepared_options(catalog):
    life = resolve(_draft([_cls("cleric", 5, "life")]), catalog)
    bless = next(o for o in _choice(life, "class:cleric:spells-known")["options"] if o["id"] == "bless")
    assert bless["disabled"] and "always prepared" in bless["disabledReason"]


def test_devotion_paladin_oath_spells(catalog):
    assert _always(resolve(_draft([_cls("paladin", 2)]), catalog), "paladin") == []
    r = resolve(_draft([_cls("paladin", 5, "devotion")]), catalog)
    assert _always(r, "paladin") == ["protection-from-evil-and-good", "sanctuary", "lesser-restoration", "zone-of-truth"]


def test_land_druid_circle_spells_need_terrain_choice(catalog):
    base = resolve(_draft([_cls("druid", 3, "land")]), catalog)
    assert _always(base, "druid") == []
    sel = resolve(_draft([_cls("druid", 3, "land", {"class:druid:2:feature:circle-of-the-land": ["circle-of-the-land-arctic"]})]), catalog)
    assert _always(sel, "druid") == ["hold-person", "spike-growth"]


def test_fiend_expanded_list_goes_into_options_not_always_prepared(catalog):
    r1 = resolve(_draft([_cls("warlock", 1, "fiend")]), catalog)
    ids1 = {o["id"] for o in _choice(r1, "class:warlock:spells-known")["options"]}
    assert {"burning-hands", "command"} <= ids1
    assert "blindness-deafness" not in ids1  # needs warlock 3
    assert _always(r1, "warlock") == []
    r3 = resolve(_draft([_cls("warlock", 3, "fiend")]), catalog)
    assert {"blindness-deafness", "scorching-ray"} <= {o["id"] for o in _choice(r3, "class:warlock:spells-known")["options"]}
    plain = resolve(_draft([_cls("warlock", 1)]), catalog)
    assert "burning-hands" not in {o["id"] for o in _choice(plain, "class:warlock:spells-known")["options"]}


def test_fiend_expanded_spell_can_be_selected(catalog):
    d = _draft([_cls("warlock", 1, "fiend", {"class:warlock:spells-known": ["burning-hands", "hellish-rebuke"]})])
    r = resolve(d, catalog)
    assert _choice(r, "class:warlock:spells-known")["selected"] == ["burning-hands", "hellish-rebuke"]


# ---- subclass proficiency grants -------------------------------------------

def test_life_cleric_gets_heavy_armor(catalog):
    assert "heavy-armor" in resolve(_draft([_cls("cleric", 1, "life")]), catalog)["sheet"]["proficiencies"]["armor"]
    assert "heavy-armor" not in resolve(_draft([_cls("cleric", 1)]), catalog)["sheet"]["proficiencies"]["armor"]


# ---- eldritch invocations --------------------------------------------------

INV = "class:warlock:2:invocations:eldritch-invocations"


def test_invocations_count_follows_level_table(catalog):
    assert _choice(resolve(_draft([_cls("warlock", 1)]), catalog), INV) is None
    for level, n in [(2, 2), (4, 2), (5, 3), (6, 3), (7, 4), (9, 5), (12, 6), (15, 7), (18, 8)]:  # VF4.4: the PHB table (the SRD Levels file had 3 at L4 and 4 at L6)
        assert _choice(resolve(_draft([_cls("warlock", level)]), catalog), INV)["count"] == n, level


def test_invocation_prerequisites_disable_options(catalog):
    c = _choice(resolve(_draft([_cls("warlock", 2)]), catalog), INV)
    assert len(c["options"]) == 32
    opts = {o["id"]: o for o in c["options"]}
    assert not opts["eldritch-invocation-armor-of-shadows"].get("disabled")
    assert opts["eldritch-invocation-mire-the-mind"]["disabled"]  # level 5
    assert opts["eldritch-invocation-agonizing-blast"]["disabled"]  # needs eldritch blast
    assert opts["eldritch-invocation-book-of-ancient-secrets"]["disabled"]  # needs Pact of the Tome
    assert opts["eldritch-invocation-armor-of-shadows"]["label"] == "Armor of Shadows"


def test_invocation_prereqs_met_by_cantrip_and_pact(catalog):
    ch = {
        "class:warlock:spells-cantrips": ["eldritch-blast", "mage-hand"],
        "class:warlock:3:feature:pact-boon": ["pact-of-the-tome"],
    }
    c = _choice(resolve(_draft([_cls("warlock", 5, choices=ch)]), catalog), INV)
    opts = {o["id"]: o for o in c["options"]}
    assert not opts["eldritch-invocation-agonizing-blast"].get("disabled")
    assert not opts["eldritch-invocation-book-of-ancient-secrets"].get("disabled")
    assert not opts["eldritch-invocation-mire-the-mind"].get("disabled")
    assert opts["eldritch-invocation-voice-of-the-chain-master"]["disabled"]  # wrong pact
    assert opts["eldritch-invocation-bewitching-whispers"]["disabled"]  # level 7


def test_invocation_selection_pruned_when_prereq_lost(catalog):
    ch = {INV: ["eldritch-invocation-agonizing-blast", "eldritch-invocation-armor-of-shadows"]}
    r = resolve(_draft([_cls("warlock", 2, choices=ch)]), catalog)
    c = _choice(r, INV)
    assert c["selected"] == ["eldritch-invocation-armor-of-shadows"]
    assert any(p["choiceId"] == INV for p in r["pruned"])
    assert not any(p["id"].startswith("over-selected") for p in r["problems"])


def test_invocation_overcount_after_level_down_is_pruned_not_problem(catalog):
    ch = {INV: ["eldritch-invocation-armor-of-shadows", "eldritch-invocation-beast-speech", "eldritch-invocation-devils-sight"]}
    r = resolve(_draft([_cls("warlock", 2, choices=ch)]), catalog)
    assert len(_choice(r, INV)["selected"]) == 2
    assert not any(p["id"].startswith("over-selected") for p in r["problems"])
