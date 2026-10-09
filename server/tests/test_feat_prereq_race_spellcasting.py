"""A4: the ASI-level gate verifies the race, spellcasting and
spellcastingFeature prerequisites of the (newly offered) 2014 feats."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species="human", subspecies=None, cls="fighter", level=4, ruleset="2014", choices=None):
    sp = {"id": species}
    if subspecies:
        sp["subspeciesId"] = subspecies
    return {
        "ruleset": ruleset, "sources": [],
        "classes": [{"classId": cls, "level": level, "choices": choices or {}}],
        "species": sp, "background": {"id": "acolyte"},
        "preferences": {"usePrerequisites": {"feats": True}},
        "abilities": {"method": "manual", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def _opt(catalog, feat, **kw):
    level = kw.get("level", 4)
    r = resolve(_draft(**kw), catalog)
    tpl = next(c for c in r["choices"] if c["id"] == f"class:{kw.get('cls', 'fighter')}:{level}:asi")
    return next(o for o in tpl["options"] if o["id"] == f"feat:{feat}"), r


def test_race_gated_feat_disabled_for_wrong_race(catalog):
    o, _ = _opt(catalog, "dragon-fear-xge")
    assert o["disabled"] is True
    assert o["disabledReason"] == "prerequisite not met: requires a Dragonborn character"


def test_race_gated_feat_enabled_for_matching_race(catalog):
    assert not _opt(catalog, "prodigy-xge")[0].get("disabled")  # human is in its list
    assert not _opt(catalog, "dragon-fear-xge", species="dragonborn")[0].get("disabled")
    assert not _opt(catalog, "squat-nimbleness-xge", species="halfling")[0].get("disabled")  # Small race


def test_subrace_gate(catalog):
    assert _opt(catalog, "fey-teleportation-xge", species="elf", subspecies="high-elf")[0].get("disabled") is None
    o, _ = _opt(catalog, "wood-elf-magic-xge", species="elf", subspecies="high-elf")
    assert o["disabled"] is True
    assert not _opt(catalog, "wood-elf-magic-xge", species="elf-phb", subspecies="elf-phb-wood-phb")[0].get("disabled")


def test_spellcasting_prerequisite(catalog):
    o, _ = _opt(catalog, "war-caster-phb")
    assert o["disabled"] is True and "spell" in o["disabledReason"]
    assert not _opt(catalog, "war-caster-phb", cls="wizard")[0].get("disabled")


def test_innate_spell_species_can_cast(catalog):
    # Tiefling (SRD) has innate spells (thaumaturgy) -> "ability to cast at least one spell".
    assert not _opt(catalog, "war-caster-phb", species="tiefling")[0].get("disabled")


def test_human_fighter_has_17_of_18_race_gated_feats_disabled(catalog):
    r = resolve(_draft(), catalog)
    tpl = next(c for c in r["choices"] if c["id"] == "class:fighter:4:asi")
    gated = [f["index"] for f in catalog.feats.values() if any("race" in a for a in (f.get("prerequisite") or []))]
    assert len(gated) == 18
    opts = {o["id"]: o for o in tpl["options"]}
    disabled = [g for g in gated if opts[f"feat:{g}"].get("disabled")]
    assert len(disabled) == 17
    assert "prodigy-xge" not in disabled


def test_prereqs_off_everything_enabled(catalog):
    d = _draft()
    d["preferences"] = {"usePrerequisites": {"feats": False}}
    r = resolve(d, catalog)
    tpl = next(c for c in r["choices"] if c["id"] == "class:fighter:4:asi")
    assert not next(o for o in tpl["options"] if o["id"] == "feat:dragon-fear-xge").get("disabled")


def test_wrong_race_pick_is_blocked_with_problem(catalog):
    r = resolve(_draft(choices={"class:fighter:4:asi": ["feat:dragon-fear-xge"]}), catalog)
    assert any(p["id"] == "feat-prerequisite-unmet-dragon-fear-xge" for p in r["problems"])
    assert not any("dragon-fear" in str(f) for f in r["sheet"]["feats"])
