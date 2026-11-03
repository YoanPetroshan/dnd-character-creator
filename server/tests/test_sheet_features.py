"""Slice 7: sheet.features / sheet.feats."""
import pytest

from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, race="human", subrace=None, background="acolyte", base=None, species_choices=None):
    species = {"id": race, "choices": species_choices or {}}
    if subrace:
        species["subspeciesId"] = subrace
    return {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": background, "choices": {}}, "species": species,
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **(base or {})}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }


def _cls(cid, level, subclass=None, choices=None):
    e = {"classId": cid, "level": level, "choices": choices or {}}
    if subclass:
        e["subclassId"] = subclass
    return e


def _feat(res, name, kind=None):
    return next((f for f in res["sheet"]["features"] if f["name"] == name and (kind is None or f["source"]["kind"] == kind)), None)


def test_fighter_class_features_by_level(catalog):
    r = resolve(_draft([_cls("fighter", 3, "champion", {"class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-defense"]})]), catalog)
    feats = r["sheet"]["features"]
    by_name = {f["name"]: f for f in feats if f["source"]["kind"] in ("class", "subclass")}
    assert by_name["Second Wind"]["level"] == 1
    assert by_name["Action Surge (1 use)"]["level"] == 2
    assert by_name["Improved Critical"]["level"] == 3 and by_name["Improved Critical"]["source"] == {"kind": "subclass", "id": "champion", "label": "Champion"}
    assert by_name["Second Wind"]["source"] == {"kind": "class", "id": "fighter", "label": "Fighter"}
    assert "Indomitable" not in by_name  # level 9
    assert not any(n.startswith("Ability Score Improvement") for n in by_name)
    assert [f["level"] for f in feats if f["source"]["kind"] == "class"] == sorted(f["level"] for f in feats if f["source"]["kind"] == "class")


def test_selected_feature_option_is_attached_as_choice(catalog):
    r = resolve(_draft([_cls("fighter", 1, choices={"class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-defense"]})]), catalog)
    assert _feat(r, "Fighting Style")["choice"] == ["Defense"]
    assert "choice" not in _feat(r, "Second Wind")


def test_pending_feature_choice_has_no_choice_key(catalog):
    r = resolve(_draft([_cls("fighter", 1)]), catalog)
    assert "choice" not in _feat(r, "Fighting Style")


def test_metamagic_and_pact_boon(catalog):
    r = resolve(_draft([_cls("sorcerer", 3, choices={"class:sorcerer:3:feature:metamagic-1": ["metamagic-careful-spell", "metamagic-quickened-spell"]})]), catalog)
    assert _feat(r, "Metamagic")["choice"] == ["Careful Spell", "Quickened Spell"]
    r = resolve(_draft([_cls("warlock", 3, choices={"class:warlock:3:feature:pact-boon": ["pact-of-the-tome"]})]), catalog)
    assert _feat(r, "Pact Boon")["choice"] == ["Pact of the Tome"]


def test_expertise_and_invocations_choices_listed(catalog):
    r = resolve(_draft([_cls("rogue", 1, choices={
        "class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-athletics"],
        "class:rogue:1:expertise-choice:rogue-expertise-1": ["skill-stealth", "thieves-tools"]})]), catalog)
    assert _feat(r, "Expertise")["choice"] == ["Stealth", "Thieves' Tools"]
    r = resolve(_draft([_cls("warlock", 2, choices={"class:warlock:2:invocations:eldritch-invocations": ["eldritch-invocation-devils-sight"]})]), catalog)
    assert _feat(r, "Eldritch Invocations")["choice"] == ["Devil's Sight"]


def test_multiclass_features_grouped_per_class(catalog):
    r = resolve(_draft([_cls("fighter", 2), _cls("rogue", 1)]), catalog)
    kinds = [(f["source"]["id"]) for f in r["sheet"]["features"] if f["source"]["kind"] == "class"]
    assert kinds == sorted(kinds, key=["fighter", "rogue"].index)  # fighter block, then rogue block
    assert _feat(r, "Sneak Attack")["level"] == 1


def test_race_traits_and_subrace_traits(catalog):
    r = resolve(_draft([_cls("fighter", 1)], race="dwarf", subrace="hill-dwarf"), catalog)
    names = {f["name"] for f in r["sheet"]["features"] if f["source"]["kind"] == "species"}
    assert {"Darkvision", "Dwarven Resilience", "Dwarven Toughness"} <= names
    assert _feat(r, "Darkvision")["source"] == {"kind": "species", "id": "dwarf", "label": "Dwarf"}


def test_species_trait_choice_is_attached(catalog):
    r = resolve(_draft([_cls("fighter", 1)], race="dragonborn"), catalog)
    anc = next(c for c in r["choices"] if ":trait:draconic-ancestry" in c["id"])
    pick = anc["options"][0]
    r = resolve(_draft([_cls("fighter", 1)], race="dragonborn", species_choices={anc["id"]: [pick["id"]]}), catalog)
    assert _feat(r, "Draconic Ancestry")["choice"] == [pick["label"]]


def test_background_feature(catalog):
    r = resolve(_draft([_cls("fighter", 1)]), catalog)
    assert _feat(r, "Shelter of the Faithful", "background")["source"]["id"] == "acolyte"


def _bg_feat_ids(catalog):
    return catalog


@needs_official
def test_feats_from_background_and_asi_in_features_and_feats(catalog):
    d = _draft([_cls("fighter", 4, choices={"class:fighter:4:asi": ["feat:athlete-xphb"]})], background="acolyte-xphb")
    d["sources"] = ["srd", "phb", "xphb"]
    r = resolve(d, catalog)
    ids = {f["id"]: f for f in r["sheet"]["feats"]}
    assert ids["athlete-xphb"]["name"] == "Athlete" and ids["athlete-xphb"]["level"] == 4 and ids["athlete-xphb"]["origin"] == "asi"
    assert ids["magic-initiate-xphb"]["origin"] == "background" and ids["magic-initiate-xphb"]["level"] is None
    assert {f["name"] for f in r["sheet"]["features"] if f["source"]["kind"] == "feat"} >= {"Athlete", "Magic Initiate"}
    assert r["sheet"]["grantedFeats"]  # unchanged
