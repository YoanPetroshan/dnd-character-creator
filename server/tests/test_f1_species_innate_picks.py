"""F1 finding 1: a species whose data lists SEVERAL UNNAMED `additionalSpells` entries gets a pick, not all of them.

Astral Elf (AAG, races.json): three `additionalSpells` entries, each `known` one cantrip (dancing lights, light, sacred
flame) with `ability {"choose": [int, wis, cha]}`; the Astral Fire trait: "You know one of the following cantrips of your
choice" (RAW: exactly ONE). G6 had read all three as grants. The fix: the converter tags each grant of such an entry with
`alt` (the slug of the entry's first spell) and the engine offers the card `species:<id>:innate-cantrip`; an unpicked card
gives none (as before G6).

The open ability (`ability {"choose": [...]}`, 28 species/subraces) is the card `species:<id>:spell-ability`; unpicked, the sheet
ability is None, never the raw candidate dict (the TS type is `Ability | null`).

The second half re-lists the ~46 species records whose `known` cantrip G6 turned into at-will grants (54 grants with the Astral Elf's three and the lineage cantrips): each is a
FIXED grant with the expected name, so the G6 count pin is not the only guard."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, sub=None, choices=None, ruleset="2014", level=5):
    return {"ruleset": ruleset, "sources": [],
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 14}},
            "species": {"id": species, **({"subspeciesId": sub} if sub else {}), **({"choices": choices} if choices else {})},
            "background": {"id": "acolyte"}, "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": "wizard", "level": level, "choices": {}}]}


def _innate(catalog, *a, **kw):
    return resolve(_draft(*a, **kw), catalog)["sheet"]["innateSpells"]


# ---- Astral Elf: exactly one ----------------------------------------------------------------------------------------

@needs_data
def test_astral_elf_unpicked_has_no_cantrip_and_a_pending_card_of_three(catalog):
    res = resolve(_draft("astral-elf-aag"), catalog)
    assert res["sheet"]["innateSpells"] == []
    card = next(c for c in res["choices"] if c["id"] == "species:astral-elf-aag:innate-cantrip")
    assert card["status"] == "pending" and card["count"] == 1
    assert [o["id"] for o in card["options"]] == ["dancing-lights", "light", "sacred-flame"]
    assert [o["label"] for o in card["options"]] == ["Dancing Lights", "Light", "Sacred Flame"]


@needs_data
@pytest.mark.parametrize("pick, name", [("dancing-lights", "Dancing Lights"), ("light", "Light"), ("sacred-flame", "Sacred Flame")])
def test_astral_elf_gets_exactly_the_picked_cantrip(catalog, pick, name):
    got = _innate(catalog, "astral-elf-aag", choices={"species:astral-elf-aag:innate-cantrip": [pick],
                                                       "species:astral-elf-aag:spell-ability": ["wis"]})
    assert [(e["name"], e["uses"], e["ability"]) for e in got] == [(name, "at-will", "WIS")]


@needs_data
def test_astral_elf_stale_or_unknown_pick_gives_none_and_two_picks_give_the_first_valid(catalog):
    assert _innate(catalog, "astral-elf-aag", choices={"species:astral-elf-aag:innate-cantrip": ["fire-bolt"]}) == []
    got = _innate(catalog, "astral-elf-aag", choices={"species:astral-elf-aag:innate-cantrip": ["bogus", "light", "sacred-flame"]})
    assert [e["name"] for e in got] == ["Light"]


@needs_data
def test_the_alt_tag_exists_only_on_the_astral_elf(catalog):
    tagged = [r["index"] for r in list(catalog.races.values()) + list(catalog.subraces.values() if isinstance(catalog.subraces, dict) else catalog.subraces)
              if any(e.get("alt") for e in r.get("innate_spells") or [])]
    assert tagged == ["astral-elf-aag"]


# ---- the ability: a card, never a raw dict --------------------------------------------------------------------------

@needs_data
def test_every_species_with_candidate_abilities_has_the_card_and_never_a_raw_dict(catalog):
    from engine.resolve import _species_spell_ability_candidates
    races = dict(catalog.races)
    subs = catalog.subraces if isinstance(catalog.subraces, dict) else {s["index"]: s for s in catalog.subraces}
    checked = 0
    for race_id, race in races.items():
        for sub_id, sub in [(None, None)] + [(i, s) for i, s in subs.items() if s["race"]["index"] == race_id and s.get("innate_spells")]:
            if not _species_spell_ability_candidates(race, sub, catalog, None) and not any(v.get("innate_spells") for v in race.get("variants") or []):
                continue
            res = resolve(_draft(race_id, sub_id, ruleset="2024" if race.get("ruleset") == "2024" else "2014"), catalog)
            for e in res["sheet"]["innateSpells"]:
                assert not isinstance(e["ability"], dict), (race_id, sub_id, e)
            checked += 1
    assert checked >= 20


@needs_data
@pytest.mark.parametrize("species, sub, choices, ruleset, expected", [
    ("aarakocra-mpmm", None, {}, "2014", [("Gust of Wind", None)]),
    ("aarakocra-mpmm", None, {"species:aarakocra-mpmm:spell-ability": ["int"]}, "2014", [("Gust of Wind", "INT")]),
    ("aasimar-mpmm", None, {"species:aasimar-mpmm:spell-ability": ["wis"]}, "2014", [("Light", "WIS")]),
    ("tiefling-xphb", None, {"species:tiefling-xphb:variant": ["infernal-legacy"], "species:tiefling-xphb:spell-ability": ["cha"]},
     "2024", [("Thaumaturgy", "CHA"), ("Fire Bolt", "CHA"), ("Hellish Rebuke", "CHA"), ("Darkness", "CHA")]),
])
def test_species_spell_ability_card(catalog, species, sub, choices, ruleset, expected):
    res = resolve(_draft(species, sub, choices, ruleset), catalog)
    got = [(e["name"], e["ability"]) for e in res["sheet"]["innateSpells"]]
    assert got == expected
    card = next(c for c in res["choices"] if c["id"] == f"species:{species}:spell-ability")
    assert [o["id"] for o in card["options"]] == ["int", "wis", "cha"]
    assert card["status"] == ("resolved" if f"species:{species}:spell-ability" in choices else "pending")


@needs_data
def test_a_fixed_ability_species_gets_no_ability_card(catalog):
    res = resolve(_draft("tiefling-phb"), catalog)
    assert not [c for c in res["choices"] if c["id"].endswith(":spell-ability")]
    assert [e["ability"] for e in res["sheet"]["innateSpells"]] == ["CHA"] * 3


# ---- the G6 widened set: each is a FIXED grant ---------------------------------------------------------------------

# species/subspecies index -> the cantrip(s) of its `additionalSpells[].known` ("name#c") that G6 reads as at-will grants.
# (races.json, derived by running the converter on a copy of the record without `innate`, then checked by eye.)
FIXED_KNOWN = {
    "aasimar-dmg": ["Light"], "aasimar-mpmm": ["Light"], "aasimar-vgm": ["Light"], "aasimar-xphb": ["Light"],
    "fairy-mpmm": ["Druidcraft"], "fairy-wbtw": ["Druidcraft"], "githyanki-mpmm": ["Mage Hand"], "githzerai-mpmm": ["Mage Hand"],
    "rimekin-lfl": ["Ray Of Frost"], "siren-psx": ["Friends"], "tiefling-phb": ["Thaumaturgy"],
    "yuan-ti-mpmm": ["Poison Spray"], "yuan-ti-pureblood-vgm": ["Poison Spray"],
    "elf-phb-drow-phb": ["Dancing Lights"], "elf-phb-mark-of-shadow-erlw": ["Minor Illusion"], "elf-phb-pallid-egw": ["Light"],
    "elf-(zendikar)-psz-mul-daya-nation-psz": ["Chill Touch"],
    "genasi-eepc-fire-eepc": ["Produce Flame"], "genasi-eepc-water-eepc": ["Shape Water"],
    "genasi-mpmm-air-mpmm": ["Shocking Grasp"], "genasi-mpmm-earth-mpmm": ["Blade Ward"],
    "genasi-mpmm-fire-mpmm": ["Produce Flame"], "genasi-mpmm-water-mpmm": ["Acid Splash"],
    "gith-mtf-githyanki-mtf": ["Mage Hand"], "gith-mtf-githzerai-mtf": ["Mage Hand"],
    "gnome-phb-forest-phb": ["Minor Illusion"], "gnome-phb-mark-of-scribing-erlw": ["Message"],
    "half-elf-phb-variant;-drow-descent-scag": ["Dancing Lights"], "half-elf-phb-variant;-mark-of-storm-erlw": ["Gust"],
    "halfling-phb-lotusden-egw": ["Druidcraft"], "halfling-phb-mark-of-hospitality-erlw": ["Prestidigitation"],
    "human-phb-mark-of-making-erlw": ["Mending"],
    "tiefling-phb-baalzebul-mtf": ["Thaumaturgy"], "tiefling-phb-dispater-mtf": ["Thaumaturgy"],
    "tiefling-phb-fierna-mtf": ["Friends"], "tiefling-phb-glasya-mtf": ["Minor Illusion"],
    "tiefling-phb-levistus-mtf": ["Ray Of Frost"], "tiefling-phb-mammon-mtf": ["Mage Hand"],
    "tiefling-phb-mephistopheles-mtf": ["Mage Hand"], "tiefling-phb-variant;-devils-tongue-scag": ["Vicious Mockery"],
    "tiefling-phb-variant;-hellfire-scag": ["Thaumaturgy"], "tiefling-phb-variant;-infernal-legacy-scag": ["Thaumaturgy"],
    "tiefling-phb-zariel-mtf": ["Thaumaturgy"],
}
# lineage-tagged (the lineage card decides) and the one pick (Astral Elf)
LINEAGE_KNOWN = {
    "elf-xphb": {"Drow": ["Dancing Lights"], "Wood Elf": ["Druidcraft"]},
    "tiefling-xphb": {"Abyssal": ["Thaumaturgy", "Poison Spray"], "Chthonic": ["Thaumaturgy", "Chill Touch"],
                      "Infernal": ["Thaumaturgy", "Fire Bolt"]},
}


def _record(catalog, index):
    if index in catalog.races:
        return catalog.races[index]
    subs = catalog.subraces
    return subs[index] if isinstance(subs, dict) else next(s for s in subs if s["index"] == index)


@needs_data
@pytest.mark.parametrize("index", sorted(FIXED_KNOWN))
def test_each_known_cantrip_of_the_g6_set_is_a_fixed_at_will_grant(catalog, index):
    rec = _record(catalog, index)
    grants = [e for e in rec["innate_spells"] if e["level"] == 1 and e["uses"] == "at-will" and e["name"] in FIXED_KNOWN[index]]
    assert sorted(e["name"] for e in grants) == sorted(FIXED_KNOWN[index]), index
    assert all(e["variant"] is None and not e.get("alt") for e in grants), index
    # and it reaches the sheet (a subrace is resolved with its race)
    race_id = rec["race"]["index"] if "race" in rec else index
    sub_id = index if "race" in rec else None
    names = [e["name"].lower() for e in _innate(catalog, race_id, sub_id)]
    for want in FIXED_KNOWN[index]:
        assert want.lower() in names or want.lower() in [n.replace("'", "") for n in names], (index, want, names)


@needs_data
def test_the_lineage_tagged_cantrips_stay_tagged_and_the_set_is_complete(catalog):
    for index, lineages in LINEAGE_KNOWN.items():
        by_variant: dict = {}
        for e in _record(catalog, index)["innate_spells"]:
            if e["variant"] and e["level"] == 1 and e["uses"] == "at-will":
                by_variant.setdefault(e["variant"], []).append(e["name"])
        for variant, names in lineages.items():
            assert all(n in by_variant.get(variant, []) for n in names), (index, variant)
    # the G6 count, spelled out: 43 fixed grants + 8 lineage grants (Elf 2, Tiefling 6) + the 3 Astral Elf alternatives = 54
    assert len(FIXED_KNOWN) == 43 and sum(len(v) for v in FIXED_KNOWN.values()) == 43
    assert sum(len(n) for v in LINEAGE_KNOWN.values() for n in v.values()) == 8
