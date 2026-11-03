"""W5b (gap audit F2): ``derived.speciesResources`` for the non-2024 species (SRD species, then the book species).

Every ``SPECIES_RESOURCES_2014`` entry quotes the catalog trait text (tags stripped) it models. Breath Weapon-like
traits are resources with ``dc`` / ``dice`` / ``details`` (decision D-2), never attack rows. The module is the W5a
``engine/species_resources.py``; these tests cover the table W5b added.
"""
from __future__ import annotations

import re

import pytest

import export_fields
from catalog import reference_data as ref
from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _plain(node):
    text = " ".join(node) if isinstance(node, list) else str(node)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\s+", " ", re.sub(r"\{@(\w+) ([^}]*)\}", tag, text))


def _res(catalog, species, level=1, ruleset="2014", picks=None, cls="fighter", base=None, subrace=None):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    choices = dict(picks or {})
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": {}}],
         "background": {"id": "acolyte", "choices": {}}, "species": {"id": species, "choices": choices, **({"subspeciesId": subrace} if subrace else {})},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [], "skipped": True}, "details": {}, "preferences": {}}
    return resolve(d, catalog)


def _by_name(res):
    return {r["name"]: r for r in res["derived"]["speciesResources"]}


def _anc(color):
    return {"species:dragonborn:trait:draconic-ancestry": [f"draconic-ancestry-{color}"]}


SRD_IDS = ("breath-weapon", "relentless-endurance", "lucky")


# ---------------------------------------------------------------- SRD data pins

@pytest.mark.parametrize("tid", SRD_IDS)
def test_srd_entry_quotes_match_catalog_trait_text(catalog, tid):
    spec = ref.SPECIES_RESOURCES_2014[tid]
    trait = catalog.traits[tid]
    assert trait["name"] == spec["name"]
    text = _plain(trait["desc"])
    assert spec["quotes"], tid
    for quote in spec["quotes"]:
        assert quote in text, (tid, quote)
    race = catalog.races[spec["race"]]
    assert race["ruleset"] == "2014" and "source" not in race  # an SRD record
    assert tid in [t["index"] for t in race["traits"]]


def test_srd_breath_weapon_structured_data_agrees_with_the_pinned_text(catalog):
    """The picked ancestry's structured breath weapon (area, save, damage) must agree with the dice progression and the
    once-per-rest rule pinned from the text."""
    spec = ref.SPECIES_RESOURCES_2014["breath-weapon"]
    progression = {str(lvl): dice for lvl, dice in spec["dice_by_level"]}
    colors = [k for k in catalog.traits if k.startswith("draconic-ancestry-")]
    assert len(colors) == 10
    for k in colors:
        bw = catalog.traits[k]["trait_specific"]["breath_weapon"]
        assert bw["damage"][0]["damage_at_character_level"] == progression, k
        assert bw["usage"] == {"type": "per rest", "times": spec["uses"]}, k
        assert bw["dc"]["dc_type"]["index"] in ("dex", "con") and bw["dc"]["success_type"] == "half", k


def test_scan_every_srd_species_trait_with_a_use_or_rest_rule_is_modelled_or_listed_skipped(catalog):
    skipped = {  # trait id -> why
        "infernal-legacy": "Tiefling: innate spells (hellish rebuke, darkness) are modelled as innate spells",
        "trance": "Elf: 4-hour rest, no uses",
        "tinker": "Rock Gnome: constructs a device, no use count or rest rule",
    }
    pat = re.compile(r"long rest|short rest|short or long rest|expended|times equal|can't (?:do so|use it) again|"
                     r"cannot use|per day|once per", re.I)
    srd_races = [r for r in catalog.races.values() if r.get("ruleset") == "2014" and "source" not in r]
    assert {r["index"] for r in srd_races} >= {"dragonborn", "half-orc", "halfling", "tiefling", "elf", "dwarf"}
    seen = 0
    for race in srd_races:
        refs = [t["index"] for t in race.get("traits") or []]
        for sub in catalog.subraces.values():
            if (sub.get("race") or {}).get("index") == race["index"]:
                refs += [t["index"] for t in sub.get("racial_traits") or []]
        for tid in refs:
            t = catalog.traits.get(tid)
            if t and pat.search(_plain(t["desc"])):
                seen += 1
                assert tid in ref.SPECIES_RESOURCES_2014 or tid in skipped, (tid, t["name"])
    assert seen >= 3


# ---------------------------------------------------------------- SRD behaviour

COLORS = {  # color -> (damage type, save, area), pinned from the SRD Draconic Ancestry table
    "black": ("acid", "DEX", "30-foot line"), "blue": ("lightning", "DEX", "30-foot line"),
    "brass": ("fire", "DEX", "30-foot line"), "bronze": ("lightning", "DEX", "30-foot line"),
    "copper": ("acid", "DEX", "30-foot line"), "gold": ("fire", "DEX", "15-foot cone"),
    "green": ("poison", "CON", "15-foot cone"), "red": ("fire", "DEX", "15-foot cone"),
    "silver": ("cold", "CON", "15-foot cone"), "white": ("cold", "CON", "15-foot cone"),
}


@pytest.mark.parametrize("color", sorted(COLORS))
def test_srd_dragonborn_breath_weapon_follows_the_picked_ancestry(catalog, color):
    dmg, save, area = COLORS[color]
    res = _res(catalog, "dragonborn", 6, picks=_anc(color), base={"CON": 16})
    bw = _by_name(res)["Breath Weapon"]
    pb = res["derived"]["proficiencyBonus"]
    assert bw["details"]["damageType"] == dmg and bw["details"]["save"] == save
    assert bw["details"]["shape"] == f"a {area}"
    assert bw["dc"] == 8 + 3 + pb and bw["dice"] == "3d6"
    assert bw["uses"] == 1 and bw["recharge"] == "short-or-long"
    assert dmg.capitalize() in bw["details"]["note"] and "3d6" in bw["details"]["note"]
    assert bw["traitId"] == "breath-weapon" and bw["speciesId"] == "dragonborn"
    assert bw["source"] == {"kind": "species", "id": "dragonborn", "label": "Dragonborn"}
    assert not any("Breath" in a.get("name", "") for a in res["derived"]["attacks"])  # D-2: not an attack row


@pytest.mark.parametrize("level,dice", [(1, "2d6"), (5, "2d6"), (6, "3d6"), (10, "3d6"), (11, "4d6"), (15, "4d6"),
                                        (16, "5d6"), (20, "5d6")])
def test_srd_dragonborn_breath_weapon_dice_by_level(catalog, level, dice):
    bw = _by_name(_res(catalog, "dragonborn", level, picks=_anc("red")))["Breath Weapon"]
    assert bw["dice"] == dice


def test_srd_dragonborn_without_a_pick_says_to_choose_the_ancestry(catalog):
    bw = _by_name(_res(catalog, "dragonborn", 1))["Breath Weapon"]
    assert bw["details"]["damageType"] is None and "shape" not in bw["details"] and "save" not in bw["details"]
    assert "Draconic Ancestry" in bw["details"]["note"] and "choose your Draconic Ancestry to see the damage type" in bw["details"]["note"]
    assert bw["dc"] == 8 + 0 + 2 and bw["dice"] == "2d6"


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_srd_resources_appear_under_2014_and_mixed(catalog, ruleset):
    assert "Breath Weapon" in _by_name(_res(catalog, "dragonborn", 1, ruleset=ruleset))
    assert "Relentless Endurance" in _by_name(_res(catalog, "half-orc", 1, ruleset=ruleset))


def test_half_orc_relentless_endurance_and_halfling_lucky(catalog):
    rel = _by_name(_res(catalog, "half-orc", 1))["Relentless Endurance"]
    assert rel["uses"] == 1 and rel["recharge"] == "long" and "1 Hit Point" in rel["details"]["note"]
    lucky = _by_name(_res(catalog, "halfling", 1))["Lucky"]
    assert lucky["uses"] is None and lucky["recharge"] is None and "reroll" in lucky["details"]["note"]


def test_species_without_table_traits_have_an_empty_list_under_2014(catalog):
    for sp in ("human", "elf", "dwarf", "tiefling", "gnome"):
        assert _res(catalog, sp, 5)["derived"]["speciesResources"] == [], sp


def test_wiring_removed_gives_no_resources(catalog, monkeypatch):
    monkeypatch.setattr(ref, "SPECIES_RESOURCES_2014", {})
    assert _res(catalog, "dragonborn", 5, picks=_anc("red"))["derived"]["speciesResources"] == []


def test_degrades_when_the_picked_ancestry_trait_is_missing_from_the_catalog(catalog, monkeypatch):
    patched = dict(catalog.traits)
    patched.pop("draconic-ancestry-red")
    monkeypatch.setattr(catalog, "traits", patched)
    bw = _by_name(_res(catalog, "dragonborn", 6, picks=_anc("red")))["Breath Weapon"]
    assert bw["details"]["damageType"] is None and bw["dice"] == "3d6"


def test_degrades_when_the_trait_is_missing_from_the_catalog(catalog, monkeypatch):
    patched = dict(catalog.traits)
    patched.pop("relentless-endurance")
    monkeypatch.setattr(catalog, "traits", patched)
    assert "Relentless Endurance" not in _by_name(_res(catalog, "half-orc", 1))


def test_extra_blocks_list_the_srd_resources(catalog):
    blocks = export_fields.extra_blocks(_res(catalog, "dragonborn", 6, picks=_anc("green")))
    idx = blocks.index(("h2", "Ресурси от расата"))
    lines = [t for kind, t in blocks[idx + 1:] if kind == "bullet"]
    assert any("Breath Weapon" in l and "3d6" in l and "ТС" in l for l in lines)


# ================================================================ commit 2: the book species

BOOK_IDS = [t for t, s in ref.SPECIES_RESOURCES_2014.items() if t not in SRD_IDS]

# trait id -> why it is not a resource. Every non-SRD, non-2024 species (and subspecies) trait whose text matches the
# use / rest pattern below is either in SPECIES_RESOURCES_2014 or here (the scan test fails on a new, unlisted one).
SKIPPED_BOOK_TRAITS = {
    "aarakocra-mpmm-trait-0": "Flight: armor restriction wording, no uses",
    "aetherborn-psk-trait-7": "Gift of the Aetherborn: hit point maximum penalty over days, no use count",
    "fairy-mpmm-trait-2": "Flight: armor restriction wording, no uses",
    "fairy-wbtw-trait-1": "Flight: armor restriction wording, no uses",
    "githyanki-mpmm-trait-0": "Astral Knowledge: proficiency swap per long rest, no uses",
    "harengon-mpmm-trait-3": "Lucky Footwork: reaction d4 with no use count",
    "harengon-wbtw-trait-3": "Lucky Footwork: reaction d4 with no use count",
    "lizardfolk-vgm-trait-4": "Cunning Artisan: downtime crafting during a short rest",
    "owlin-scc-trait-2": "Flight: armor restriction wording, no uses",
    "vampire-psz-trait-3": "Blood Thirst: no use count",
    "verdan-ai-trait-3": "Black Blood Healing: Hit Die reroll, no use count",
    "astral-elf-aag-trait-6": "Astral Trance: rest-duration rule, no uses",
    "autognome-aag-trait-5": "Sentry's Rest: rest-duration rule, no uses",
    "eladrin-mpmm-trait-6": "Trance: rest-duration rule, no uses",
    "elf-(kaladesh)-psk-trait-7": "Trance: rest-duration rule, no uses",
    "elf-phb-trait-5": "Trance: rest-duration rule, no uses",
    "sea-elf-mpmm-trait-7": "Trance: rest-duration rule, no uses",
    "shadar-kai-mpmm-trait-6": "Trance: rest-duration rule, no uses",
    "thri-kreen-aag-trait-5": "Sleepless: rest-duration rule, no uses",
    "warforged-erlw-trait-4": "Sentry's Rest: rest-duration rule, no uses",
    "aarakocra-mpmm-trait-2": "Wind Caller: innate spell grant (its uses belong to the spell, not a species resource)",
    "aasimar-dmg-trait-4": "Celestial Legacy: innate spell grant (its uses belong to the spell, not a species resource)",
    "deep-gnome-mpmm-trait-2": "Gift of the Svirfneblin: innate spell grant (its uses belong to the spell, not a species resource)",
    "duergar-mpmm-trait-2": "Duergar Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "dwarf-phb-duergar-mtf-trait-3": "Duergar Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "dwarf-phb-mark-of-warding-erlw-trait-1": "Wards and Seals: innate spell grant (its uses belong to the spell, not a species resource)",
    "elf-(zendikar)-psz-mul-daya-nation-psz-trait-0": "Mul Daya Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "elf-phb-drow-phb-trait-2": "Drow Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "elf-phb-eladrin-dmg-trait-1": "Fey Step: innate spell grant (its uses belong to the spell, not a species resource)",
    "elf-phb-mark-of-shadow-erlw-trait-1": "Shape Shadows: innate spell grant (its uses belong to the spell, not a species resource)",
    "elf-phb-pallid-egw-trait-1": "Blessing of the Moon Weaver: innate spell grant (its uses belong to the spell, not a species resource)",
    "fairy-mpmm-trait-1": "Fairy Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "fairy-wbtw-trait-2": "Fairy Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "firbolg-mpmm-trait-0": "Firbolg Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "firbolg-vgm-trait-2": "Firbolg Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-eepc-air-eepc-trait-1": "Mingle with the Wind: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-eepc-earth-eepc-trait-1": "Merge with Stone: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-eepc-fire-eepc-trait-2": "Reach to the Blaze: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-eepc-water-eepc-trait-3": "Call to the Wave: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-mpmm-air-mpmm-trait-2": "Mingle with the Wind: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-mpmm-earth-mpmm-trait-1": "Merge with Stone: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-mpmm-fire-mpmm-trait-1": "Reach to the Blaze: innate spell grant (its uses belong to the spell, not a species resource)",
    "genasi-mpmm-water-mpmm-trait-3": "Call to the Wave: innate spell grant (its uses belong to the spell, not a species resource)",
    "gith-mtf-githyanki-mtf-trait-3": "Githyanki Psionics: innate spell grant (its uses belong to the spell, not a species resource)",
    "gith-mtf-githzerai-mtf-trait-2": "Githzerai Psionics: innate spell grant (its uses belong to the spell, not a species resource)",
    "githyanki-mpmm-trait-1": "Githyanki Psionics: innate spell grant (its uses belong to the spell, not a species resource)",
    "githzerai-mpmm-trait-0": "Githzerai Psionics: innate spell grant (its uses belong to the spell, not a species resource)",
    "gnome-phb-mark-of-scribing-erlw-trait-1": "Scribe's Insight: innate spell grant (its uses belong to the spell, not a species resource)",
    "half-elf-phb-variant;-mark-of-detection-erlw-trait-1": "Magical Detection: innate spell grant (its uses belong to the spell, not a species resource)",
    "half-elf-phb-variant;-mark-of-storm-erlw-trait-2": "Headwinds: innate spell grant (its uses belong to the spell, not a species resource)",
    "half-orc-phb-variant;-mark-of-finding-erlw-trait-2": "Finder's Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "halfling-phb-lotusden-egw-trait-0": "Child of the Wood: innate spell grant (its uses belong to the spell, not a species resource)",
    "halfling-phb-mark-of-healing-erlw-trait-1": "Healing Touch: innate spell grant (its uses belong to the spell, not a species resource)",
    "halfling-phb-mark-of-hospitality-erlw-trait-1": "Innkeeper's Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "hexblood-vrgr-trait-5": "Hex Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "human-phb-mark-of-handling-erlw-trait-1": "Primal Connection: innate spell grant (its uses belong to the spell, not a species resource)",
    "human-phb-mark-of-making-erlw-trait-2": "Spellsmith: innate spell grant (its uses belong to the spell, not a species resource)",
    "human-phb-mark-of-passage-erlw-trait-2": "Magical Passage: innate spell grant (its uses belong to the spell, not a species resource)",
    "human-phb-mark-of-sentinel-erlw-trait-1": "Guardian's Shield: innate spell grant (its uses belong to the spell, not a species resource)",
    "human-phb-variant;-mark-of-finding-erlw-trait-2": "Finder's Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "rimekin-lfl-trait-0": "Cold Fire Magic: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-baalzebul-mtf-trait-0": "Legacy of Maladomini: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-dispater-mtf-trait-0": "Legacy of Dis: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-fierna-mtf-trait-0": "Legacy of Phlegethos: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-glasya-mtf-trait-0": "Legacy of Malbolge: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-levistus-mtf-trait-0": "Legacy of Stygia: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-mammon-mtf-trait-0": "Legacy of Minauros: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-mephistopheles-mtf-trait-0": "Legacy of Cania: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-trait-4": "Infernal Legacy: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-variant;-devils-tongue-scag-trait-1": "Devil's Tongue: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-variant;-hellfire-scag-trait-1": "Hellfire: innate spell grant (its uses belong to the spell, not a species resource)",
    "tiefling-phb-zariel-mtf-trait-0": "Legacy of Avernus: innate spell grant (its uses belong to the spell, not a species resource)",
    "triton-mpmm-trait-2": "Control Air and Water: innate spell grant (its uses belong to the spell, not a species resource)",
    "triton-vgm-trait-4": "Control Air and Water: innate spell grant (its uses belong to the spell, not a species resource)",
    "yuan-ti-mpmm-trait-4": "Serpentine Spellcasting: innate spell grant (its uses belong to the spell, not a species resource)",
    "yuan-ti-pureblood-vgm-trait-3": "Innate Spellcasting: innate spell grant (its uses belong to the spell, not a species resource)",
}


SCAN_PATTERN = re.compile(r"long rest|short rest|short or long rest|expended|times equal|can't (?:do so|use it) again|"
                          r"cannot use|per day|once per|once on each|once you (?:use|shift|create|cast)|can't (?:use|cast) "
                          r"(?:this|that|it)|can't cast", re.I)


@needs_official
@pytest.mark.parametrize("tid", BOOK_IDS)
def test_book_entry_quotes_match_catalog_trait_text(catalog, tid):
    spec = ref.SPECIES_RESOURCES_2014[tid]
    trait = catalog.traits[tid]
    assert trait["name"] == spec["name"]
    text = _plain(trait["desc"])
    assert spec["quotes"], tid
    for quote in spec["quotes"]:
        assert quote in text, (tid, quote)
    race = catalog.races[spec["race"]]
    assert race["ruleset"] == "2014" and "source" in race  # a book record, never a 2024 one
    held = [t["index"] for t in race["traits"]]
    for sub in catalog.subraces.values():
        if (sub.get("race") or {}).get("index") == spec["race"]:
            held += [t["index"] for t in sub.get("racial_traits") or []]
    assert tid in held


@needs_official
def test_every_book_entry_states_its_rest_and_use_rule_in_the_text(catalog):
    """`uses` / `recharge` come from the pinned text: a PB entry quotes the proficiency-bonus count, a rest entry its rest."""
    for tid in BOOK_IDS:
        spec = ref.SPECIES_RESOURCES_2014[tid]
        text = _plain(catalog.traits[tid]["desc"]).lower()
        if spec["recharge"] is None:  # WF: note-only (the Lucky duplicates): no use count, no rest rule
            assert spec["uses"] is None, tid
        elif spec["recharge"] == "long":
            assert "long rest" in text, tid
        elif spec["recharge"] in ("turn", "combat", "other"):  # X2: the non-rest limits, pinned by test_x2_turn_combat_rage_recharges.py
            assert spec["uses"] == 1 and spec["recharge"] in ref.RESOURCE_RECHARGES, tid
        else:
            assert spec["recharge"] == "short-or-long" and "short" in text and "long rest" in text, tid
        if spec["uses"] == "pb":
            assert "proficiency bonus" in text, tid


@needs_official
def test_scan_every_book_species_trait_with_a_use_or_rest_rule_is_modelled_or_listed_skipped(catalog):
    seen = set()
    for race in catalog.races.values():
        if race.get("ruleset") == "2024" or "source" not in race:
            continue
        held = [t["index"] for t in race.get("traits") or []]
        for sub in catalog.subraces.values():
            if (sub.get("race") or {}).get("index") == race["index"]:
                held += [t["index"] for t in sub.get("racial_traits") or []]
        for tid in held:
            t = catalog.traits.get(tid)
            if t and SCAN_PATTERN.search(_plain(t["desc"])):
                seen.add(tid)
                assert tid in ref.SPECIES_RESOURCES_2014 or tid in SKIPPED_BOOK_TRAITS, (tid, t["name"])
    assert len(seen) >= 120
    assert not set(SKIPPED_BOOK_TRAITS) & set(ref.SPECIES_RESOURCES_2014)
    assert set(SKIPPED_BOOK_TRAITS) <= seen  # no stale skip entry


def _book(catalog, species, level=1, **kw):
    return _by_name(_res(catalog, species, level, **kw))


@needs_official
@pytest.mark.parametrize("level,pb", [(1, 2), (5, 3), (9, 4), (13, 5), (17, 6)])
def test_pb_uses_scale_with_the_proficiency_bonus(catalog, level, pb):
    for species, name in (("astral-elf-aag", "Starlight Step"), ("autognome-aag", "Built for Success"),
                          ("eladrin-mpmm", "Fey Step"), ("firbolg-mpmm", "Hidden Step"), ("harengon-mpmm", "Rabbit Hop"),
                          ("kenku-mpmm", "Kenku Recall"), ("reborn-vrgr", "Knowledge from a Past Life")):
        r = _book(catalog, species, level)[name]
        assert r["uses"] == pb and r["recharge"] == "long", (species, name)


@needs_official
@pytest.mark.parametrize("species,name", [
    ("firbolg-vgm", "Hidden Step"), ("goblin-vgm", "Fury of the Small"), ("goliath-vgm", "Stone's Endurance"),
    ("hobgoblin-vgm", "Saving Face"), ("kobold-vgm", "Grovel, Cower, and Beg"), ("leonin-mot", "Daunting Roar"),
    ("lizardfolk-vgm", "Hungry Jaws"), ("shifter-erlw", "Shifting")])
def test_fixed_single_use_recharged_by_a_short_or_long_rest(catalog, species, name):
    r = _book(catalog, species)[name]
    assert r["uses"] == 1 and r["recharge"] == "short-or-long"


@needs_official
@pytest.mark.parametrize("species,name", [
    ("half-orc-phb", "Relentless Endurance"), ("orc-mpmm", "Relentless Endurance"), ("orc-(ixalan)-psx", "Relentless Endurance"),
    ("minotaur-(amonkhet)-psa", "Relentless Endurance"), ("kender-dsotdq", "Fearless"), ("hexblood-vrgr", "Eerie Token"),
    ("vedalken-ggr", "Partially Amphibious"), ("aasimar-vgm", "Healing Hands")])
def test_fixed_single_use_recharged_by_a_long_rest(catalog, species, name):
    r = _book(catalog, species)[name]
    assert r["uses"] == 1 and r["recharge"] == "long"


@needs_official
def test_numbers_in_the_notes_follow_the_character(catalog):
    kw = dict(base={"CON": 16})
    goliath = _res(catalog, "goliath-mpmm", 5, **kw)
    con = goliath["derived"]["abilityModifiers"]["CON"]
    assert f"({con:+d})" in _by_name(goliath)["Stone's Endurance"]["details"]["note"]
    assert "10 feet" not in _book(catalog, "harengon-mpmm", 9)["Rabbit Hop"]["details"]["note"]
    assert "20 feet" in _book(catalog, "harengon-mpmm", 9)["Rabbit Hop"]["details"]["note"]  # 5 x PB 4
    assert "4 Temporary Hit Points" in _book(catalog, "orc-mpmm", 9)["Adrenaline Rush"]["details"]["note"]
    assert "6 Temporary Hit Points (2 times" in _book(catalog, "shifter-mpmm", 5)["Shifting"]["details"]["note"]  # 2 x PB 3
    shifter = _res(catalog, "shifter-erlw", 4, **kw)  # level + CON modifier
    assert f"{4 + shifter['derived']['abilityModifiers']['CON']} Temporary Hit Points" in _by_name(shifter)["Shifting"]["details"]["note"]
    low = _res(catalog, "lizardfolk-vgm", 1, base={"CON": 1})  # a CON modifier below 1 still gives 1
    assert low["derived"]["abilityModifiers"]["CON"] < 1
    assert "gain 1 Temporary Hit Points" in _by_name(low)["Hungry Jaws"]["details"]["note"]
    liz = _res(catalog, "lizardfolk-vgm", 1, **kw)
    assert f"gain {liz['derived']['abilityModifiers']['CON']} Temporary Hit Points" in _by_name(liz)["Hungry Jaws"]["details"]["note"]
    assert "level (7)" in _book(catalog, "aasimar-vgm", 7, subrace="aasimar-vgm-fallen-vgm")["Necrotic Shroud"]["details"]["note"]
    assert _book(catalog, "aasimar-vgm", 7)["Healing Hands"]["details"]["heal"] == "7"
    assert _book(catalog, "aasimar-mpmm", 9)["Healing Hands"]["details"]["heal"] == "4d4"


@needs_official
def test_level_gated_book_traits_appear_at_their_level(catalog):
    for species, name, lvl, picks in [("aasimar-mpmm", "Celestial Revelation", 3, None),
                                      ("dragonborn-(chromatic)-ftd", "Chromatic Warding", 5, None),
                                      ("dragonborn-(gem)-ftd", "Gem Flight", 5, None),
                                      ("dragonborn-(metallic)-ftd", "Metallic Breath Weapon", 5, None)]:
        assert name not in _book(catalog, species, lvl - 1), name
        r = _book(catalog, species, lvl)[name]
        assert r["uses"] == 1 and r["recharge"] == "long", name


@needs_official
def test_subspecies_traits_need_the_subspecies_pick(catalog):
    assert "Fey Step" not in _book(catalog, "elf-phb", 1)
    r = _book(catalog, "elf-phb", 1, subrace="elf-phb-eladrin-mtf")["Fey Step"]
    assert r["uses"] == 1 and r["recharge"] == "short-or-long" and r["speciesId"] == "elf-phb"
    assert "Fey Step" not in _book(catalog, "elf-phb", 1, subrace="elf-phb-drow-phb")
    assert "Blessing of the Raven Queen" in _book(catalog, "elf-phb", 1, subrace="elf-phb-shadar-kai-mtf")
    assert "Forceful Presence" in _book(catalog, "dragonborn-phb", 1, subrace="dragonborn-phb-draconblood-egw")
    assert "Vengeful Assault" in _book(catalog, "dragonborn-phb", 1, subrace="dragonborn-phb-ravenite-egw")
    assert "Forceful Presence" not in _book(catalog, "dragonborn-phb", 1, subrace="dragonborn-phb-ravenite-egw")


@needs_official
@pytest.mark.parametrize("fam,variant,dmg", [("chromatic", "black", "acid"), ("chromatic", "red", "fire"),
                                             ("gem", "amethyst", "force"), ("gem", "topaz", "necrotic"),
                                             ("metallic", "silver", "cold"), ("metallic", "gold", "fire")])
def test_ftd_dragonborn_breath_weapon_has_dc_dice_and_the_variant_damage_type(catalog, fam, variant, dmg):
    species = f"dragonborn-({fam})-ftd"
    for level, dice in ((1, "1d10"), (5, "2d10"), (11, "3d10"), (17, "4d10")):
        res = _res(catalog, species, level, picks={f"species:{species}:variant": [f"dragonborn-{fam}-{variant}"]}, base={"CON": 14})
        bw = _by_name(res)["Breath Weapon"]
        pb = res["derived"]["proficiencyBonus"]
        con = res["derived"]["abilityModifiers"]["CON"]
        assert bw["dice"] == dice and bw["dc"] == 8 + con + pb and bw["uses"] == pb and bw["recharge"] == "long"
        assert bw["details"]["damageType"] == dmg and bw["details"]["save"] == "DEX"
        assert not any("Breath" in a.get("name", "") for a in res["derived"]["attacks"])  # D-2


@needs_official
def test_ftd_breath_weapon_area_differs_by_family(catalog):
    assert "30-foot line" in _book(catalog, "dragonborn-(chromatic)-ftd")["Breath Weapon"]["details"]["note"]
    assert "15-foot cone" in _book(catalog, "dragonborn-(gem)-ftd")["Breath Weapon"]["details"]["note"]
    assert "15-foot cone" in _book(catalog, "dragonborn-(metallic)-ftd")["Breath Weapon"]["details"]["note"]


@needs_official
def test_metallic_second_breath_weapon_has_a_dc_but_no_invented_dice(catalog):
    r = _by_name(_res(catalog, "dragonborn-(metallic)-ftd", 5, base={"CON": 14}))["Metallic Breath Weapon"]
    res = _res(catalog, "dragonborn-(metallic)-ftd", 5, base={"CON": 14})
    assert r["dc"] == 8 + res["derived"]["proficiencyBonus"] + res["derived"]["abilityModifiers"]["CON"] and "dice" not in r and "save" not in r["details"]


@needs_official
def test_phb_dragonborn_breath_weapon_takes_its_damage_type_from_the_resistance_pick(catalog):
    res = _res(catalog, "dragonborn-phb", 6, picks={"species:dragonborn-phb:resistance": ["fire"]}, base={"CON": 12})
    bw = _by_name(res)["Breath Weapon"]
    con = res["derived"]["abilityModifiers"]["CON"]
    assert bw["details"]["damageType"] == "fire" and bw["dice"] == "3d6" and bw["dc"] == 8 + con + res["derived"]["proficiencyBonus"]
    assert bw["uses"] == 1 and bw["recharge"] == "short-or-long" and "save" not in bw["details"]
    unpicked = _by_name(_res(catalog, "dragonborn-phb", 1))["Breath Weapon"]
    assert unpicked["details"]["damageType"] is None and "choose your Draconic Ancestry to see the damage type" in unpicked["details"]["note"]


@needs_official
def test_leonin_roar_dc_and_aasimar_shroud_dc(catalog):
    res = _res(catalog, "leonin-mot", 5, base={"CON": 14})
    roar = _by_name(res)["Daunting Roar"]
    assert roar["dc"] == 8 + res["derived"]["proficiencyBonus"] + res["derived"]["abilityModifiers"]["CON"]
    assert roar["details"]["save"] == "WIS"
    res = _res(catalog, "aasimar-vgm", 5, subrace="aasimar-vgm-fallen-vgm", base={"CHA": 16})
    shroud = _by_name(res)["Necrotic Shroud"]
    assert shroud["dc"] == 8 + res["derived"]["proficiencyBonus"] + res["derived"]["abilityModifiers"]["CHA"]
    assert shroud["details"]["save"] == "CHA"


@needs_official
def test_eladrin_fey_step_and_kender_taunt_do_not_invent_a_dc(catalog):
    assert "dc" not in _book(catalog, "eladrin-mpmm", 5)["Fey Step"]  # the casting ability is chosen when you select the race
    assert "dc" not in _book(catalog, "kender-dsotdq", 5)["Taunt"]


def test_book_entries_use_the_resource_shape_minus_class_id(catalog):
    for r in _res(catalog, "dragonborn-(chromatic)-ftd", 11)["derived"]["speciesResources"]:
        assert "classId" not in r and r["id"].startswith("species:dragonborn-(chromatic)-ftd:")
        assert {"id", "name", "uses", "recharge", "source", "speciesId", "traitId", "details"} <= set(r)


def test_species_without_a_modelled_trait_stay_empty(catalog):
    for sp in ("elf-phb", "gnome-phb", "dwarf-phb"):  # X2: Tabaxi and Bugbear moved to the table (non-rest recharges)
        assert _res(catalog, sp, 5)["derived"]["speciesResources"] == [], sp


def test_book_wiring_removed_gives_no_resources(catalog, monkeypatch):
    monkeypatch.setattr(ref, "SPECIES_RESOURCES_2014", {})
    assert _res(catalog, "astral-elf-aag", 5)["derived"]["speciesResources"] == []


@needs_official
def test_book_entry_degrades_when_its_trait_is_missing_from_the_catalog(catalog, monkeypatch):
    patched = dict(catalog.traits)
    patched.pop("astral-elf-aag-trait-5")
    monkeypatch.setattr(catalog, "traits", patched)
    assert _res(catalog, "astral-elf-aag", 5)["derived"]["speciesResources"] == []


@needs_official
def test_book_resources_reach_the_exports(catalog):
    blocks = export_fields.extra_blocks(_res(catalog, "astral-elf-aag", 5))
    idx = blocks.index(("h2", "Ресурси от расата"))
    lines = [t for kind, t in blocks[idx + 1:] if kind == "bullet"]
    assert any("Starlight Step" in l and "3" in l and "дълга почивка" in l for l in lines)
