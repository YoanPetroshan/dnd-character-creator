"""Feats' `skillToolLanguageProficiencies` (Skilled/PHB and Skilled/XPHB:
"choose any 3 from skills or tools") becomes one Choice of count N whose
options are every skill plus every tool.

Verified against the fetched feats.json: exactly 2 feats carry the key, both
`[{"choose": [{"count": 3, "from": ["anySkill", "anyTool"]}]}]`. No race
carries it; the only background that does (Custom Background/PHB) uses a
different, fixed-alternatives shape that is not converted. Backgrounds that
grant Skilled via `feats`: Charlatan, Noble, Scribe (XPHB), Archaeologist/EFA,
Chondathan Freebooter/FRHoF, Rewarded and Ruined (BMT)."""
import pytest

from catalog import choices as choices_mod
from catalog import reference_data
from catalog.loader import load
from catalog.official.feats import _skill_tool_choices_from_5etools
from catalog.official_source import has_official
from engine.resolve import resolve

SKILL_OR_TOOL = {"option_set_type": "any_skill_or_tool"}


# --- converter / option set (no official data needed) ------------------------

def test_converter_both_makes_skill_or_tool_envelope():
    raw = {"skillToolLanguageProficiencies": [{"choose": [{"count": 3, "from": ["anySkill", "anyTool"]}]}]}
    assert _skill_tool_choices_from_5etools(raw) == [{"choose": 3, "type": "proficiencies", "from": SKILL_OR_TOOL}]


def test_converter_single_kinds_reuse_existing_option_sets():
    s = {"skillToolLanguageProficiencies": [{"choose": [{"count": 2, "from": ["anySkill"]}]}]}
    t = {"skillToolLanguageProficiencies": [{"choose": [{"count": 1, "from": ["anyTool"]}]}]}
    assert _skill_tool_choices_from_5etools(s) == [{"choose": 2, "type": "proficiencies", "from": {"option_set_type": "any_skill"}}]
    assert _skill_tool_choices_from_5etools(t) == [{"choose": 1, "type": "proficiencies", "from": {"option_set_type": "any_tool"}}]


def test_converter_ignores_missing_and_unrecognised():
    assert _skill_tool_choices_from_5etools({}) == []
    assert _skill_tool_choices_from_5etools({"skillToolLanguageProficiencies": [{"anyLanguage": 2}]}) == []
    assert _skill_tool_choices_from_5etools({"skillToolLanguageProficiencies": [{"choose": [{"count": 0, "from": ["anySkill"]}]}]}) == []


def test_option_set_is_every_skill_then_every_tool():
    opts = choices_mod.build_choice_options(SKILL_OR_TOOL)
    ids = [o["id"] for o in opts]
    assert ids[: len(reference_data.SKILL_NAMES)] == list(reference_data.SKILL_NAMES)
    assert ids[len(reference_data.SKILL_NAMES):] == [t["index"] for t in reference_data.TOOLS]
    assert len(ids) == len(set(ids))


# --- real data -----------------------------------------------------------------

official = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

SOURCES = ["srd", "phb", "xphb", "efa", "frhof", "bmt"]
N_SKILLS = len(reference_data.SKILL_NAMES)
N_TOOLS = len(reference_data.TOOLS)


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species=None, background="acolyte", level=1, choices=None, bg_choices=None):
    return {
        "name": "T", "sources": SOURCES,
        "classes": [{"classId": "fighter", "level": level, "choices": choices or {}}],
        "background": {"id": background, "choices": bg_choices or {}},
        "species": species or {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


ASI = "class:fighter:4:asi"
ASI_SUB = ASI + ":feat:skilled-xphb:proficiency-choice-0"
SPECIES_FEAT = "species:human-xphb:feat-0"
SPECIES_SUB = SPECIES_FEAT + ":feat:skilled-xphb:proficiency-choice-0"
BG_SUB = "feat:skilled-xphb:proficiency-choice-0"


@official
def test_both_skilled_feats_convert(catalog):
    for fid in ("skilled-phb", "skilled-xphb"):
        assert catalog.feats[fid]["proficiency_choices"] == [{"choose": 3, "type": "proficiencies", "from": SKILL_OR_TOOL}]


@official
def test_only_skilled_feats_carry_the_choice(catalog):
    holders = sorted(k for k, f in catalog.feats.items() for e in f["proficiency_choices"] if e["from"].get("option_set_type") == "any_skill_or_tool")
    assert holders == ["skilled-phb", "skilled-xphb"]


@official
def test_asi_origin_scoped_templates(catalog):
    # Skilled is not ASI-eligible in real data (only category G is; Skilled is
    # '' / O), so the ASI cid shape is exercised at template level.
    from engine.resolve import _feat_choice_templates
    origin = "class:fighter:4:asi:feat:skilled-xphb"
    feat = {**catalog.feats["skilled-xphb"], "_asi_level": 4}
    (tpl,) = _feat_choice_templates([feat], origin=origin)
    assert tpl["id"] == ASI_SUB and tpl["count"] == 3
    assert tpl["label"] == "Skilled: Skill or Tool Proficiency"
    assert tpl["source"]["kind"] == "feat" and tpl["source"]["level"] == 4
    assert len(tpl["options"]) == N_SKILLS + N_TOOLS


@official
def test_skilled_as_species_feat(catalog):
    sp = lambda sel: {"id": "human-xphb", "choices": sel}
    res = resolve(_draft(species=sp({SPECIES_FEAT: ["feat:skilled-xphb"]})), catalog)
    ch = _choice(res, SPECIES_SUB)
    assert ch and ch["count"] == 3 and len(ch["options"]) == N_SKILLS + N_TOOLS
    res = resolve(_draft(species=sp({SPECIES_FEAT: ["feat:skilled-xphb"], SPECIES_SUB: ["skill-stealth", "skill-arcana", "lute"]})), catalog)
    prof = res["sheet"]["proficiencies"]
    assert {"skill-stealth", "skill-arcana"} <= set(prof["skills"])
    assert "lute" in prof["tools"]


@official
@pytest.mark.parametrize("bg", ["charlatan-xphb", "noble-xphb", "scribe-xphb"])
def test_background_granted_skilled_has_picks(catalog, bg):
    res = resolve(_draft(background=bg), catalog)
    ch = _choice(res, BG_SUB)
    assert ch and ch["count"] == 3 and ch["status"] == "pending"
    sel = {BG_SUB: ["skill-nature", "skill-religion", "dice-set"]}
    res = resolve(_draft(background=bg, bg_choices=sel), catalog)
    assert _choice(res, BG_SUB)["status"] == "resolved"
    prof = res["sheet"]["proficiencies"]
    assert {"skill-nature", "skill-religion"} <= set(prof["skills"])
    assert "dice-set" in prof["tools"]


@official
def test_picks_are_pruned_when_the_feat_changes(catalog):
    picks = ["skill-arcana", "skill-history", "thieves-tools"]
    sel = {SPECIES_FEAT: ["feat:alert-xphb"], SPECIES_SUB: picks}
    res = resolve(_draft(species={"id": "human-xphb", "choices": sel}), catalog)
    assert SPECIES_SUB in [p["choiceId"] for p in res["pruned"]]
    assert "skill-arcana" not in res["sheet"]["proficiencies"]["skills"]
    assert "thieves-tools" not in res["sheet"]["proficiencies"]["tools"]


@official
def test_background_picks_are_pruned_when_background_changes(catalog):
    sel = {BG_SUB: ["skill-arcana", "skill-history", "thieves-tools"]}
    res = resolve(_draft(background="soldier-xphb", bg_choices=sel), catalog)
    assert BG_SUB in [p["choiceId"] for p in res["pruned"]]
    assert "thieves-tools" not in res["sheet"]["proficiencies"]["tools"]


@official
def test_unknown_option_and_over_selection_are_rejected(catalog):
    sel = {SPECIES_FEAT: ["feat:skilled-xphb"], SPECIES_SUB: ["skill-arcana", "skill-history", "thieves-tools", "skill-stealth"]}
    res = resolve(_draft(species={"id": "human-xphb", "choices": sel}), catalog)
    assert any(p["id"] == f"over-selected-{SPECIES_SUB}" for p in res["problems"])
    sel[SPECIES_SUB] = ["not-a-thing", "skill-history"]
    res = resolve(_draft(species={"id": "human-xphb", "choices": sel}), catalog)
    assert _choice(res, SPECIES_SUB)["selected"] == ["skill-history"]


@official
def test_already_proficient_skill_is_not_double_counted(catalog):
    # Acolyte grants Insight and Religion; Skilled picking Insight again is
    # accepted as a pick (same as every other feat proficiency choice) but
    # the sheet lists the skill once.
    sel = {SPECIES_FEAT: ["feat:skilled-xphb"], SPECIES_SUB: ["skill-insight", "skill-arcana", "skill-history"]}
    res = resolve(_draft(species={"id": "human-xphb", "choices": sel}), catalog)
    skills = res["sheet"]["proficiencies"]["skills"]
    assert skills.count("skill-insight") == 1
