"""F1 finding 2: a subrace whose entries replace a race trait (5etools `entries[].data.overwrite`) drops the race's innate
spells that trait granted. The PHB Tiefling's Infernal Legacy (races.json: "You know the thaumaturgy cantrip. ... hellish
rebuke ... darkness ...") is replaced by each of the 8 MTF legacies that carry the flag and by the SCAG Devil's Tongue,
Hellfire and Winged variants ("This trait replaces the Infernal Legacy trait."). Asmodeus (no entries at all) and the SCAG
"Variant; Infernal Legacy" (no flag) keep it; the latter repeats the whole set in its own additionalSpells (identical
entries are listed once)."""
import json

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes, official_dir
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="5etools official data not available")


def _draft(species="human", cls="wizard", level=5, ruleset="2014", sub=None, choices=None, cha=16):
    return {"ruleset": ruleset, "sources": [],
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": cha}},
            "species": {"id": species, **({"subspeciesId": sub} if sub else {})}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": cls, "level": level, "choices": dict(choices or {})}]}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _spells(catalog, sub, level=5):
    sheet = resolve(_draft(species="tiefling-phb", sub=sub, level=level), catalog)["sheet"]
    return [(e["name"], e["uses"]) for e in sheet["innateSpells"]]


PHB = [("Thaumaturgy", "at-will"), ("Hellish Rebuke", "1/day"), ("Darkness", "1/day")]
EXPECTED = {
    None: PHB,
    "tiefling-phb-asmodeus-mtf": PHB,
    "tiefling-phb-variant;-infernal-legacy-scag": PHB,
    "tiefling-phb-baalzebul-mtf": [("Thaumaturgy", "at-will"), ("Ray Of Sickness", "1/day"), ("Crown Of Madness", "1/day")],
    "tiefling-phb-dispater-mtf": [("Thaumaturgy", "at-will"), ("Disguise Self", "1/day"), ("Detect Thoughts", "1/day")],
    "tiefling-phb-fierna-mtf": [("Friends", "at-will"), ("Charm Person", "1/day"), ("Suggestion", "1/day")],
    "tiefling-phb-glasya-mtf": [("Minor Illusion", "at-will"), ("Disguise Self", "1/day"), ("Invisibility", "1/day")],
    "tiefling-phb-levistus-mtf": [("Ray Of Frost", "at-will"), ("Armor Of Agathys", "1/day"), ("Darkness", "1/day")],
    "tiefling-phb-mammon-mtf": [("Mage Hand", "at-will"), ("Floating Disk", "1/day"), ("Arcane Lock", "1/day")],
    "tiefling-phb-mephistopheles-mtf": [("Mage Hand", "at-will"), ("Burning Hands", "1/day"), ("Flame Blade", "1/day")],
    "tiefling-phb-zariel-mtf": [("Thaumaturgy", "at-will"), ("Searing Smite", "1/day"), ("Branding Smite", "1/day")],
    "tiefling-phb-variant;-devils-tongue-scag": [("Vicious Mockery", "at-will"), ("Charm Person", "1/day"), ("Enthrall", "1/day")],
    "tiefling-phb-variant;-hellfire-scag": [("Thaumaturgy", "at-will"), ("Burning Hands", "1/day"), ("Darkness", "1/day")],
    "tiefling-phb-variant;-winged-scag": [],
}


@needs_data
@pytest.mark.parametrize("sub", list(EXPECTED))
def test_exact_innate_spells_per_tiefling_subrace(catalog, sub):
    got = _spells(catalog, sub)
    want = EXPECTED[sub]
    # the names the catalog does not know are title-cased fallbacks ("Ray Of Sickness"); compare case-insensitively
    assert [(n.lower(), u) for n, u in got] == [(n.lower(), u) for n, u in want], sub


@needs_data
def test_fierna_does_not_keep_infernal_legacy_and_zariel_does_not_keep_hellish_rebuke(catalog):
    fierna = [n for n, _ in _spells(catalog, "tiefling-phb-fierna-mtf")]
    assert not {"Thaumaturgy", "Hellish Rebuke", "Darkness"} & set(fierna)
    zariel = [n for n, _ in _spells(catalog, "tiefling-phb-zariel-mtf")]
    assert "Hellish Rebuke" not in zariel and "Darkness" not in zariel and zariel.count("Thaumaturgy") == 1


@needs_data
def test_every_subrace_flag_comes_from_the_data(catalog):
    flagged = {s["index"] for s in catalog.subraces.values() if s.get("overwrites_traits")} if isinstance(catalog.subraces, dict) \
        else {s["index"] for s in catalog.subraces if s.get("overwrites_traits")}
    tiefling = {i for i in flagged if i.startswith("tiefling-phb-")}
    assert tiefling == {i for i in EXPECTED if i and i not in ("tiefling-phb-asmodeus-mtf", "tiefling-phb-variant;-infernal-legacy-scag")}
    raw = json.load(open(official_dir() / "races.json", encoding="utf-8"))
    for r in raw["subrace"]:
        if r.get("raceName") == "Tiefling" and r.get("name") and r["source"] in ("MTF", "SCAG"):
            marked = any(isinstance(e, dict) and (e.get("data") or {}).get("overwrite") == "Infernal Legacy" for e in r.get("entries") or [])
            idx = f"tiefling-phb-{r['name'].lower().replace(' ', '-').replace(chr(39), '')}-{r['source'].lower()}"
            assert marked == (idx in tiefling), idx


@needs_data
def test_only_the_spell_granting_trait_matters(catalog):
    """A replaced trait that does not name the spell removes nothing (the rule reads the replaced trait's text)."""
    from engine.resolve import _subrace_replaces_spell_trait
    race = catalog.races["tiefling-phb"]
    sub = {"overwrites_traits": ["Hellish Resistance"]}
    assert not _subrace_replaces_spell_trait(race, sub, catalog, {"name": "Darkness"})
    sub = {"overwrites_traits": ["Infernal Legacy"]}
    assert _subrace_replaces_spell_trait(race, sub, catalog, {"name": "Darkness"})
    assert not _subrace_replaces_spell_trait(race, sub, catalog, {"name": "Fireball"})
    assert not _subrace_replaces_spell_trait(race, None, catalog, {"name": "Darkness"})
