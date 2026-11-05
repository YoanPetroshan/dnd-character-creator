"""G6: additive `usesMax` / `recharge` on `sheet.innateSpells[]`, parsed ONLY from the entry's `uses` text; and the PHB Tiefling
Thaumaturgy cantrip (the `known` block of `additionalSpells`).

Rule matrix (the `uses` text of the entry -> fields; the class-resource recharge vocabulary):
  "N/day"                   usesMax N, recharge "long"          (1/day: PHB Tiefling Hellish Rebuke / Darkness, feats ...)
  "N/long rest"             usesMax N, recharge "long"          (2024 Glamour / Psi Warrior 1, Archfey max(1, CHA mod), RP5 PB)
  "N/short rest"            usesMax N, recharge "short"
  "N/short or long rest"    usesMax N, recharge "short-or-long" (2024 Diviner The Third Eye)
  everything else           neither field: "at-will", "prepared", "always prepared", "ritual", "ritual only", "1 Focus Point"
                            (a resource cost, no rest), unparseable text, 0
  A count that depends on PB or an ability modifier is already a number in the text when the entry is built ("{pb}/long
  rest", "{cha_min1}/long rest"), so the parse sees "3/long rest".
Nothing else on the entry changes (the new keys are the only difference), the markdown / PDF lines are unchanged.

Thaumaturgy (PHB Tiefling): the vendored races.json gives the PHB Tiefling `additionalSpells[0].known {"1":
["thaumaturgy#c"]}` next to the `innate` Hellish Rebuke (3) and Darkness (5); the converter read only `innate`, so the
cantrip was on the sheet nowhere. The SRD Tiefling already had it (Infernal Legacy in `SRD_TRAIT_EFFECTS`, at will)."""
import copy
import json

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes, official_dir
from catalog.official.innate_spells import _known_cantrips
from engine.innate_uses import parse_uses, with_limit
from engine.resolve import resolve
from markdown_export import to_markdown
from perf_helpers import assert_fast, measure

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species="human", cls="wizard", level=5, ruleset="2014", sub=None, subclass=None, cha=16, choices=None):
    return {"ruleset": ruleset, "sources": [],
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": cha}},
            "species": {"id": species, **({"subspeciesId": sub} if sub else {})}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": cls, "level": level, **({"subclassId": subclass} if subclass else {}),
                         "choices": dict(choices or {})}]}


def _innate(catalog, **kw):
    return resolve(_draft(**kw), catalog)["sheet"]["innateSpells"]


def _by_name(entries):
    return {e["name"]: e for e in entries}


# ---- the parser -----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("1/day", (1, "long")), ("2/day", (2, "long")), ("1/long rest", (1, "long")), ("3/long rest", (3, "long")),
    ("12/long rest", (12, "long")), ("1/short rest", (1, "short")), ("2/short or long rest", (2, "short-or-long")),
    ("1/short or long rest", (1, "short-or-long")), (" 1/day ", (1, "long")), ("1 / day", (1, "long")),
    ("1/Long Rest", (1, "long")),
])
def test_parse_uses_reads_a_count_and_a_rest(text, expected):
    assert parse_uses(text) == expected


@pytest.mark.parametrize("text", [
    "at-will", "prepared", "always prepared", "ritual", "ritual only", "1 Focus Point", "", "1/", "/day", "0/day",
    "PB/long rest", "once per day", "1/week", "1/turn", "many/day", "1.5/day", None, 3, ["1/day"],
])
def test_parse_uses_leaves_everything_else_without_a_limit(text):
    assert parse_uses(text) is None


def test_with_limit_is_additive_and_returns_the_entry_unchanged_when_there_is_no_limit():
    base = {"spellId": "darkness", "name": "Darkness", "level": 5, "uses": "1/day", "ability": "CHA", "variant": None}
    out = with_limit(base)
    assert out == {**base, "usesMax": 1, "recharge": "long"} and "usesMax" not in base  # the input is not mutated
    assert list(out)[:len(base)] == list(base)  # existing keys keep their order
    at_will = {**base, "uses": "at-will"}
    assert with_limit(at_will) is at_will


# ---- PHB Tiefling Thaumaturgy -----------------------------------------------------------------------------------------

@needs_data
def test_the_vendored_phb_tiefling_grants_thaumaturgy_in_known():
    races = json.load(open(official_dir() / "races.json", encoding="utf-8"))["race"]
    phb = next(r for r in races if r["name"] == "Tiefling" and r["source"] == "PHB")
    (block,) = phb["additionalSpells"]
    assert block["known"] == {"1": ["thaumaturgy#c"]} and block["ability"] == "cha"
    assert block["innate"] == {"3": {"daily": {"1": ["hellish rebuke#2"]}}, "5": {"daily": {"1": ["darkness"]}}}


def test_known_cantrips_converter():
    assert _known_cantrips({"1": ["thaumaturgy#c"]}, "CHA", None) == [
        {"name": "Thaumaturgy", "spell_id": "thaumaturgy", "level": 1, "uses": "at-will", "ability": "CHA", "variant": None}]
    two = _known_cantrips({"1": ["thaumaturgy|xphb#c", "poison spray|xphb#c"]}, {"choose": ["INT", "WIS", "CHA"]}, "Abyssal")
    assert [e["spell_id"] for e in two] == ["thaumaturgy", "poison-spray"] and {e["variant"] for e in two} == {"Abyssal"}
    # every other `known` shape is a different mechanic and stays out
    assert _known_cantrips({"1": ["alarm", "mage armor"]}, "INT", None) == []                       # no #c (Mark of Warding)
    assert _known_cantrips({"1": {"rest": {"1": ["misty step"]}}}, "CHA", None) == []                # rest wrapper (Eladrin)
    assert _known_cantrips({"1": {"_": [{"choose": "level=0|class=Wizard"}]}}, "INT", None) == []    # a pick (High Elf)
    assert _known_cantrips({"x": ["light#c"]}, "CHA", None) == [] and _known_cantrips(None, "CHA", None) == []


@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_phb_tiefling_sheet_has_thaumaturgy_and_the_two_daily_spells(catalog, ruleset):
    names = _by_name(_innate(catalog, species="tiefling-phb", ruleset=ruleset))
    assert list(names) == ["Thaumaturgy", "Hellish Rebuke", "Darkness"]
    thaum = names["Thaumaturgy"]
    assert (thaum["uses"], thaum["level"], thaum["ability"], thaum["spellId"]) == ("at-will", 1, "CHA", "thaumaturgy")
    assert "usesMax" not in thaum and "recharge" not in thaum
    for name, level in (("Hellish Rebuke", 3), ("Darkness", 5)):
        e = names[name]
        assert (e["level"], e["uses"], e["usesMax"], e["recharge"], e["ability"]) == (level, "1/day", 1, "long", "CHA")


@needs_data
def test_the_srd_tiefling_still_has_it_once(catalog):
    names = [e["name"] for e in _innate(catalog, species="tiefling")]
    assert names == ["Thaumaturgy", "Hellish Rebuke", "Darkness"]


@needs_data
def test_a_tiefling_subrace_does_not_list_thaumaturgy_twice(catalog):
    # MTF Zariel: its own `known` Thaumaturgy is the same grant as the race's; the identical entry is kept once
    entries = _innate(catalog, species="tiefling-phb", sub="tiefling-phb-zariel-mtf")
    names = [e["name"] for e in entries]
    assert names.count("Thaumaturgy") == 1 and {"Searing Smite", "Branding Smite"} <= set(names)
    # a subrace with another cantrip adds it next to the race's Thaumaturgy
    levistus = [e["name"] for e in _innate(catalog, species="tiefling-phb", sub="tiefling-phb-levistus-mtf")]
    assert "Ray Of Frost" in [n.title() for n in levistus] and levistus.count("Thaumaturgy") == 1


@needs_data
def test_level_does_not_filter_the_known_cantrip_like_the_other_species_grants(catalog):
    # the species grants are not filtered by character level (the class level only decides the leveled grants' text)
    assert "Thaumaturgy" in [e["name"] for e in _innate(catalog, species="tiefling-phb", level=1)]


@needs_data
def test_2024_tiefling_and_elf_lineages_get_their_known_cantrips(catalog):
    tiefling = _by_name(_innate(catalog, species="tiefling-xphb", ruleset="2024",
                                choices={}))  # no lineage picked: the variant-tagged grants stay hidden
    assert "Thaumaturgy" not in tiefling
    res = resolve({**_draft(species="tiefling-xphb", ruleset="2024"),
                   "species": {"id": "tiefling-xphb", "choices": {"species:tiefling-xphb:variant": ["infernal-legacy"]}}}, catalog)
    names = [e["name"] for e in res["sheet"]["innateSpells"]]
    assert sorted(names) == ["Darkness", "Fire Bolt", "Hellish Rebuke", "Thaumaturgy"]


@needs_data
def test_other_species_cantrips_from_known_are_on_the_sheet_too(catalog):
    # the fix is the converter's `known` reading, so every species with a fixed "#c" cantrip gains it (listed in ARCHITECTURE)
    drow = [e["name"] for e in _innate(catalog, species="elf-xphb", ruleset="2024")]
    assert "Dancing Lights" not in drow  # a lineage-tagged grant stays hidden until the lineage is picked
    aasimar = _by_name(_innate(catalog, species="aasimar-dmg"))
    assert aasimar["Light"]["uses"] == "at-will" and aasimar["Light"]["ability"] == "CHA"
    assert "usesMax" not in aasimar["Light"] and aasimar["Lesser Restoration"]["usesMax"] == 1


# ---- the sheet: every source of innate spells ---------------------------------------------------------------------------

@needs_data
def test_additive_only_the_two_keys_differ(catalog):
    res = resolve(_draft(species="tiefling-phb"), catalog)
    for e in res["sheet"]["innateSpells"]:
        stripped = {k: v for k, v in e.items() if k not in ("usesMax", "recharge")}
        assert set(stripped) == {"spellId", "name", "level", "uses", "ability", "variant"}
        assert ("usesMax" in e) == ("recharge" in e)


@needs_data
def test_ritual_only_always_prepared_focus_point_and_at_will_have_no_limit(catalog):
    wild = _by_name(_innate(catalog, cls="barbarian", level=3, ruleset="2024", subclass="wild-heart-xphb"))
    assert {e["uses"] for e in wild.values()} == {"ritual only"} and not any("usesMax" in e or "recharge" in e for e in wild.values())
    shadow = _by_name(_innate(catalog, cls="monk", level=3, ruleset="2024", subclass="shadow-xphb"))
    assert shadow["Darkness"]["uses"] == "1 Focus Point" and "usesMax" not in shadow["Darkness"]


@needs_data
@pytest.mark.parametrize("cls, level, sub, name, uses, usesmax, recharge", [
    ("bard", 6, "glamour-xphb", "Command", "1/long rest", 1, "long"),
    ("fighter", 18, "psi-warrior-xphb", "Telekinesis", "1/long rest", 1, "long"),
    ("wizard", 10, "diviner-xphb", "See Invisibility", "1/short or long rest", 1, "short-or-long"),
])
def test_2024_subclass_innate_spells(catalog, cls, level, sub, name, uses, usesmax, recharge):
    e = _by_name(_innate(catalog, cls=cls, level=level, ruleset="2024", subclass=sub))[name]
    assert (e["uses"], e["usesMax"], e["recharge"]) == (uses, usesmax, recharge)


@needs_data
@pytest.mark.parametrize("cha, expected", [(8, 1), (10, 1), (12, 1), (14, 2), (16, 3), (20, 5)])
def test_archfey_misty_step_count_follows_the_charisma_modifier(catalog, cha, expected):
    e = _by_name(_innate(catalog, cls="warlock", level=3, ruleset="2024", subclass="archfey-xphb", cha=cha))["Misty Step"]
    assert e["uses"] == f"{expected}/long rest" and (e["usesMax"], e["recharge"]) == (expected, "long")


@needs_data
@pytest.mark.parametrize("level, pb", [(4, 2), (5, 3), (9, 4), (13, 5), (17, 6)])
def test_greater_mark_of_healing_computes_the_proficiency_bonus_count(catalog, level, pb):
    """RP5: the Greater Mark makes Cure Wounds "a number of times equal to your Proficiency Bonus": the patched text is
    "<pb>/long rest" by the time the entry is built, so usesMax is the character's proficiency bonus. The base Mark alone is 1/day."""
    draft = _draft(cls="fighter", level=level, ruleset="mixed",
                   choices={"class:fighter:4:asi": ["feat:greater-mark-of-healing-efa"]})
    draft["background"] = {"id": "house-jorasco-heir-efa"}  # the base Mark comes from the House background
    res = resolve(draft, catalog)
    cure = next(e for e in res["sheet"]["innateSpells"] if e["name"] == "Cure Wounds")
    assert res["derived"]["proficiencyBonus"] == pb
    assert cure["uses"] == f"{pb}/long rest" and (cure["usesMax"], cure["recharge"]) == (pb, "long")
    base = _draft(cls="fighter", level=level, ruleset="mixed")
    base["background"] = {"id": "house-jorasco-heir-efa"}
    cure = next(e for e in resolve(base, catalog)["sheet"]["innateSpells"] if e["name"] == "Cure Wounds")
    assert (cure["uses"], cure["usesMax"], cure["recharge"]) == ("1/day", 1, "long")


@needs_data
def test_feat_entries_one_per_day_get_a_limit_and_the_prepared_ones_do_not(catalog):
    res = resolve(_draft(cls="fighter", level=4, choices={"class:fighter:4:asi": ["feat:telepathic-xphb"]}, ruleset="2024"), catalog)
    entry = next(e for e in res["sheet"]["innateSpells"] if e.get("featId") == "telepathic-xphb")
    assert (entry["uses"], entry["usesMax"], entry["recharge"]) == ("1/day", 1, "long")


@needs_data
def test_warlock_invocation_entries_are_at_will_without_a_limit(catalog):
    res = resolve(_draft(cls="warlock", level=5, choices={"class:warlock:2:invocations:eldritch-invocations": [
        "eldritch-invocation-armor-of-shadows", "eldritch-invocation-mask-of-many-faces"]}), catalog)
    assert res["sheet"]["innateSpells"]
    for e in res["sheet"]["innateSpells"]:
        assert e["uses"] != "at-will" or ("usesMax" not in e and "recharge" not in e)


@needs_data
def test_exports_do_not_print_the_new_fields(catalog):
    res = resolve(_draft(species="tiefling-phb"), catalog)
    md = to_markdown(res)
    assert "usesMax" not in md and "recharge" not in md
    line = next(l for l in md.splitlines() if l.startswith("- Hellish Rebuke"))
    assert "1/day" in line and line.count("1/day") == 1  # the uses text is the only place the count is printed
    assert any(l.startswith("- Thaumaturgy (at-will") for l in md.splitlines())


def test_types_ts_declares_both_keys():
    import pathlib
    text = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "types.ts").read_text(encoding="utf-8")
    spell = text[text.index("export interface SheetInnateSpell "):]
    spell = spell[:spell.index("\n}")]
    assert 'usesMax?: number;' in spell and 'recharge?: "long" | "short" | "short-or-long";' in spell


@needs_data
def test_timing(catalog):
    draft = _draft(species="tiefling-phb", sub="tiefling-phb-zariel-mtf")
    assert_fast(measure(lambda: resolve(copy.deepcopy(draft), catalog)), "wizard 5 tiefling with a subrace")
