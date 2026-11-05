"""G4: irregular recharges (Limited Wish, Necrotic Husk), Power Surge as a resource, Four Elements discipline ki costs on
the Ki entry, Rune Knight runes as resources.

Governing texts (vendored 5etools data, quoted verbatim in `reference_data` and pinned below):
  Limited Wish (Genie 14, TCE)   "Once you use this feature, you can't use it again until you finish 1d4 long rests."
  Necrotic Husk (Undead 10, VRGR) "Once you use this reaction, you can't do so again until you finish 1d4 long rests."
       -> uses 1, recharge "other" (X2: the condition is written out in the note), details.recharges "1d4 long rests"
  Power Surge (War Magic 6, XGE) "a maximum number of power surges equal to your Intelligence modifier (minimum of one)";
       "Whenever you finish a long rest, your number of power surges resets to one"; "If you end a short rest with no
       power surges, you gain one"; dispel magic / counterspell: "you gain one power surge"
       -> uses = max(1, INT modifier), recharge "other", details.recharges names the three refills (the pool never refills
       "to the maximum")
  Four Elements (PHB)            each discipline record: "You can spend N ki points to cast <spell>." (16 records with a ki
       cost; Elemental Attunement has none); picked disciplines list their base cost in the Ki entry
  Rune Knight (TCE)              every rune: "Once you invoke this rune, you can't do so again until you finish a short or
       long rest."; Master of Runes (15): "invoke each rune you know ... twice, rather than once"; "If a rune requires a
       saving throw, your Rune Magic save DC equals 8 + your proficiency bonus + your Constitution modifier" (Fire: Strength
       save, Stone: Wisdom save)

Rule matrix: rulesets mixed / 2014 only (mixed with a 2014 class equals 2014; 2024 has none of these subclasses); picks only
(no pick, no discipline cost, no rune resource; a stale pick gives nothing); Lunar phase stays a note (decision Q17)."""
import copy
import re

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line
from perf_helpers import assert_fast, measure

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

FE_CARD = "class:monk:3:feature:four-elements-phb-3-way-of-the-four-elements"
RK_CARD = "class:fighter:3:feature:rune-knight-tce-3-rune-knight"

# Independent expectations, from the books (not read from the tables).
DISCIPLINE_COSTS = {
    "opt-breath-of-winter-phb": 6, "opt-clench-of-the-north-wind-phb": 3, "opt-eternal-mountain-defense-phb": 5,
    "opt-fangs-of-the-fire-snake-phb": 1, "opt-fist-of-four-thunders-phb": 2, "opt-flames-of-the-phoenix-phb": 4,
    "opt-gong-of-the-summit-phb": 3, "opt-mist-stance-phb": 4, "opt-ride-the-wind-phb": 4,
    "opt-river-of-hungry-flame-phb": 5, "opt-rush-of-the-gale-spirits-phb": 2, "opt-shape-the-flowing-river-phb": 1,
    "opt-sweeping-cinder-strike-phb": 2, "opt-unbroken-air-phb": 2, "opt-water-whip-phb": 2,
    "opt-wave-of-rolling-earth-phb": 6,
}
RUNES = {"opt-cloud-rune-tce": "Cloud Rune", "opt-fire-rune-tce": "Fire Rune", "opt-frost-rune-tce": "Frost Rune",
         "opt-hill-rune-tce": "Hill Rune", "opt-stone-rune-tce": "Stone Rune", "opt-storm-rune-tce": "Storm Rune"}
DC_RUNES = {"opt-fire-rune-tce", "opt-stone-rune-tce"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls, sub, level, picks=None, ruleset="2014", base=None, sources=()):
    return {"ruleset": ruleset, "sources": list(sources),
            "abilities": {"method": "manual", "base": base or {"STR": 10, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}},
            "species": {"id": "human"}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": cls, "subclassId": sub, "level": level, "choices": dict(picks or {})}]}


def _res(catalog, cls, sub, level, picks=None, ruleset="2014", base=None):
    return resolve(_draft(cls, sub, level, picks, ruleset, base), catalog)


def _by_id(res):
    return {r["id"]: r for r in res["derived"]["classResources"]}


def _text(catalog, fid):
    return "\n".join(catalog.features[fid]["desc"])


# ---- quote pins ------------------------------------------------------------------------------------------------

@needs_data
def test_recharge_texts_are_in_the_records(catalog):
    assert "Once you use this feature, you can't use it again until you finish 1d4 long rests." in _text(catalog, "genie-tce-14-limited-wish")
    assert "Once you use this reaction, you can't do so again until you finish 1d4 long rests." in _text(catalog, "undead-vrgr-10-necrotic-husk")
    for spec in reference_data.SUBCLASS_TAIL_2014_BOOKS:
        if spec["feature"] in ("genie-tce-14-limited-wish", "undead-vrgr-10-necrotic-husk"):
            assert spec["details"] == {"recharges": "1d4 long rests"} and spec["recharge"] == "other" and spec["uses"] == 1
            assert spec["details"]["recharges"] in _text(catalog, spec["feature"])
            assert "1d4 long rests" in spec["note"]  # X2: "other" names its condition in the note


@needs_data
def test_power_surge_texts_are_in_the_record(catalog):
    text = _text(catalog, "war-xge-6-power-surge")
    for phrase in ("a maximum number of power surges equal to your Intelligence modifier (minimum of one)",
                   "Whenever you finish a long rest, your number of power surges resets to one",
                   "Whenever you successfully end a spell with dispel magic or counterspell, you gain one power surge",
                   "If you end a short rest with no power surges, you gain one power surge"):
        assert phrase in text
    spec = next(s for s in reference_data.SUBCLASS_TAIL_2014_BOOKS if s["feature"] == "war-xge-6-power-surge")
    assert (spec["uses"], spec["recharge"]) == ("@int_min1", "other")
    assert spec["details"]["recharges"] in spec["note"]


@needs_data
def test_discipline_table_quotes_are_in_their_records_and_costs_agree(catalog):
    table = reference_data.ELEMENTAL_DISCIPLINES_2014
    assert {k: v["cost"] for k, v in table["options"].items()} == DISCIPLINE_COSTS
    for oid, spec in table["options"].items():
        record = _text(catalog, oid)
        assert spec["name"] == catalog.features[oid]["name"], oid
        for quote in spec["quotes"]:
            assert quote in record, (oid, quote)
        # the cost is the number in the first quoted sentence ("spend N ki point(s)")
        assert f"spend {spec['cost']} ki point" in spec["quotes"][0], oid
    # Elemental Attunement is granted and its text names no ki cost
    assert "ki point" not in _text(catalog, "opt-elemental-attunement-phb")
    # every PHB optional feature whose text spends ki points is in the table (nothing silently skipped)
    costed = {k for k, f in catalog.features.items() if k.startswith("opt-") and k.endswith("-phb")
              and "ki point" in "\n".join(f["desc"])}
    assert costed == set(table["options"])
    card_options = {o["id"] for o in _res(catalog, "monk", "four-elements-phb", 17)["choices"]
                    if o["id"] == FE_CARD for o in o["options"]}
    assert card_options == set(DISCIPLINE_COSTS)  # the card offers exactly the 16 costed disciplines


@needs_data
def test_rune_table_quotes_are_in_their_records(catalog):
    table = reference_data.RUNE_KNIGHT_RUNES_2014
    assert {k: v["name"] for k, v in table["options"].items()} == RUNES
    for oid, spec in table["options"].items():
        record = _text(catalog, oid)
        assert catalog.features[oid]["name"] == spec["name"]
        for quote in spec["quotes"]:
            assert quote in record, (oid, quote)
        assert ("dc" in spec) == (oid in DC_RUNES), oid
        # a DC only where the record names a saving throw
        assert bool(re.search(r"(succeed on an?|make an?) \w+ saving throw", record)) == (oid in DC_RUNES), oid
    for fid, quote in table["master_quotes"]:
        assert quote.rstrip(".") in _text(catalog, fid)
    card = next(c for c in _res(catalog, "fighter", "rune-knight-tce", 15)["choices"] if c["id"] == RK_CARD)
    assert {o["id"] for o in card["options"]} == set(RUNES)


# ---- Limited Wish / Necrotic Husk / Power Surge ----------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_limited_wish_and_necrotic_husk_recharge_other(catalog, ruleset):
    res = _by_id(_res(catalog, "warlock", "genie-tce", 14, ruleset=ruleset))
    lw = res["warlock:limited-wish"]
    assert (lw["uses"], lw["recharge"]) == (1, "other") and lw["details"]["recharges"] == "1d4 long rests"
    assert "until you finish 1d4 long rests" in lw["details"]["note"]
    nh = _by_id(_res(catalog, "warlock", "undead-vrgr", 10, ruleset=ruleset))["warlock:necrotic-husk"]
    assert (nh["uses"], nh["recharge"]) == (1, "other") and nh["details"]["recharges"] == "1d4 long rests"
    assert "1d4 long rests" in nh["details"]["note"]


@needs_data
def test_limited_wish_and_necrotic_husk_below_their_level_and_in_2024(catalog):
    assert "warlock:limited-wish" not in _by_id(_res(catalog, "warlock", "genie-tce", 13))
    assert "warlock:necrotic-husk" not in _by_id(_res(catalog, "warlock", "undead-vrgr", 9))
    for sub in ("genie-tce", "undead-vrgr"):
        ids = _by_id(_res(catalog, "warlock", sub, 20, ruleset="2024"))
        assert "warlock:limited-wish" not in ids and "warlock:necrotic-husk" not in ids


@needs_data
@pytest.mark.parametrize("intelligence, uses", [(8, 1), (10, 1), (14, 2), (20, 5)])
def test_power_surge_pool_follows_the_intelligence_modifier(catalog, intelligence, uses):
    base = {"STR": 10, "DEX": 14, "CON": 14, "INT": intelligence, "WIS": 10, "CHA": 10}
    ps = _by_id(_res(catalog, "wizard", "war-xge", 6, base=base))["wizard:power-surge"]
    assert ps["uses"] >= 1  # minimum of one
    mod = _res(catalog, "wizard", "war-xge", 6, base=base)["derived"]["abilityModifiers"]["INT"]
    assert ps["uses"] == max(1, mod)
    assert ps["recharge"] == "other"
    assert ps["details"]["recharges"] in ps["details"]["note"]
    assert f"at most {ps['uses']} power surges" in ps["details"]["note"]
    assert "damage equal to 3 (half your Wizard level)" in ps["details"]["note"]


@needs_data
def test_power_surge_absent_below_6_other_subclass_and_2024(catalog):
    assert "wizard:power-surge" not in _by_id(_res(catalog, "wizard", "war-xge", 5))
    assert "wizard:power-surge" not in _by_id(_res(catalog, "wizard", "evocation", 20))
    assert "wizard:power-surge" not in _by_id(_res(catalog, "wizard", "war-xge", 20, ruleset="2024"))


# ---- Four Elements ----------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("oid, cost", sorted(DISCIPLINE_COSTS.items()))
def test_each_discipline_lists_its_ki_cost_on_the_ki_entry(catalog, oid, cost):
    level = 17  # every discipline's level requirement is met
    ki = _by_id(_res(catalog, "monk", "four-elements-phb", level, {FE_CARD: [oid]}))["monk:ki"]
    assert ki["details"]["disciplineKiCosts"] == {oid: cost}
    name = catalog.features[oid]["name"]
    assert f"Elemental disciplines: {name} ({cost} ki" in ki["details"]["note"]
    assert ki["uses"] == 17 and ki["recharge"] == "short"  # the Ki entry itself is unchanged


@needs_data
def test_several_disciplines_in_pick_order_and_the_extra_ki_text(catalog):
    picks = ["opt-unbroken-air-phb", "opt-fist-of-four-thunders-phb", "opt-fangs-of-the-fire-snake-phb"]
    ki = _by_id(_res(catalog, "monk", "four-elements-phb", 17, {FE_CARD: picks}))["monk:ki"]
    assert list(ki["details"]["disciplineKiCosts"]) == picks
    note = ki["details"]["note"]
    assert note.index("Unbroken Air") < note.index("Fist of Four Thunders") < note.index("Fangs of the Fire Snake")
    assert "Unbroken Air (2 ki; 1 more ki point per extra 1d10 bludgeoning damage)" in note
    assert "Fangs of the Fire Snake (1 ki; 1 more ki point when the attack hits: extra 1d10 fire damage)" in note
    assert "Fist of Four Thunders (2 ki)" in note
    assert note.startswith("Flurry of Blows")  # the earlier Ki sentences are kept


@needs_data
def test_no_pick_no_key_and_the_disciple_entry_names_the_ki_entry(catalog):
    res = _by_id(_res(catalog, "monk", "four-elements-phb", 17))
    assert "disciplineKiCosts" not in res["monk:ki"]["details"] and "Elemental disciplines" not in res["monk:ki"]["details"]["note"]
    assert "costs of the picked disciplines are on the Ki entry" in res["monk:disciple-of-the-elements"]["details"]["note"]


@needs_data
def test_stale_discipline_pick_gives_nothing_and_other_subclass_none(catalog):
    # level 3 offers one pick of the 16, but a pick with a level requirement (Breath of Winter, 17) is not offered
    res = _by_id(_res(catalog, "monk", "four-elements-phb", 3, {FE_CARD: ["opt-breath-of-winter-phb"]}))
    assert "disciplineKiCosts" not in res["monk:ki"]["details"]
    other = _by_id(_res(catalog, "monk", "open-hand", 17, {FE_CARD: ["opt-fist-of-four-thunders-phb"]}))
    assert "disciplineKiCosts" not in other["monk:ki"].get("details", {})


@needs_data
def test_four_elements_2014_equals_mixed_and_2024_has_none(catalog):
    picks = {FE_CARD: ["opt-fist-of-four-thunders-phb", "opt-water-whip-phb"]}
    mixed = _by_id(_res(catalog, "monk", "four-elements-phb", 11, picks, ruleset="mixed"))["monk:ki"]
    only = _by_id(_res(catalog, "monk", "four-elements-phb", 11, picks, ruleset="2014"))["monk:ki"]
    assert mixed == only and mixed["details"]["disciplineKiCosts"] == {"opt-fist-of-four-thunders-phb": 2, "opt-water-whip-phb": 2}
    ki24 = _by_id(_res(catalog, "monk", "four-elements-phb", 11, picks, ruleset="2024")).get("monk:focus-points", {})
    assert "disciplineKiCosts" not in (ki24.get("details") or {})


@needs_data
def test_four_elements_ki_line_in_the_export(catalog):
    picks = {FE_CARD: ["opt-fist-of-four-thunders-phb"]}
    ki = _by_id(_res(catalog, "monk", "four-elements-phb", 6, picks))["monk:ki"]
    for lang in ("en", "bg"):
        line = resource_line(ki, lang)
        assert "Elemental disciplines: Fist of Four Thunders (2 ki)" in line and line.count("Fist of Four Thunders") == 1


# ---- Rune Knight --------------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("oid, name", sorted(RUNES.items()))
@pytest.mark.parametrize("level, uses", [(7, 1), (10, 1), (14, 1), (15, 2), (20, 2)])
def test_each_rune_is_a_resource_with_one_use_and_two_from_master_of_runes(catalog, oid, name, level, uses):
    if oid in ("opt-hill-rune-tce", "opt-storm-rune-tce") and level < 7:
        pytest.skip("level requirement")
    res = _res(catalog, "fighter", "rune-knight-tce", level, {RK_CARD: [oid]})
    entry = _by_id(res)[f"fighter:rune-carver-{name.lower().replace(' ', '-')}"]
    assert entry["name"] == f"Rune Carver: {name}" and entry["source"]["kind"] == "subclass"
    assert (entry["uses"], entry["recharge"]) == (uses, "short-or-long")
    con = res["derived"]["abilityModifiers"]["CON"]
    pb = res["derived"]["proficiencyBonus"]
    if oid in DC_RUNES:
        assert entry["dc"] == 8 + pb + con and f"DC {entry['dc']}" in entry["details"]["note"]
    else:
        assert "dc" not in entry and "DC" not in entry["details"]["note"]


@needs_data
def test_rune_dc_equals_the_rune_carver_note_dc(catalog):
    res = _res(catalog, "fighter", "rune-knight-tce", 10, {RK_CARD: ["opt-fire-rune-tce", "opt-stone-rune-tce"]},
               base={"STR": 16, "DEX": 12, "CON": 18, "INT": 8, "WIS": 10, "CHA": 8})
    by = _by_id(res)
    dc = 8 + 4 + 4  # PB 4 at level 10, CON +4
    assert by["fighter:rune-carver-fire-rune"]["dc"] == by["fighter:rune-carver-stone-rune"]["dc"] == dc
    assert f"Rune Magic save DC {dc}" in by["fighter:rune-carver"]["details"]["note"]


@needs_data
def test_runes_follow_the_picks_in_pick_order_and_the_five_at_level_15(catalog):
    picks = ["opt-storm-rune-tce", "opt-cloud-rune-tce", "opt-fire-rune-tce", "opt-hill-rune-tce", "opt-stone-rune-tce"]
    res = _res(catalog, "fighter", "rune-knight-tce", 15, {RK_CARD: picks})
    names = [r["name"] for r in res["derived"]["classResources"] if r["name"].startswith("Rune Carver: ")]
    assert names == ["Rune Carver: Storm Rune", "Rune Carver: Cloud Rune", "Rune Carver: Fire Rune", "Rune Carver: Hill Rune",
                     "Rune Carver: Stone Rune"]
    ids = [r["id"] for r in res["derived"]["classResources"]]
    assert ids.index("fighter:rune-carver") < ids.index("fighter:rune-carver-storm-rune")  # after the Rune Carver entry
    assert len(set(ids)) == len(ids)


@needs_data
def test_no_pick_no_rune_resource_and_other_subclass_none(catalog):
    assert not [r for r in _res(catalog, "fighter", "rune-knight-tce", 15)["derived"]["classResources"]
                if r["name"].startswith("Rune Carver: ")]
    other = _res(catalog, "fighter", "champion", 15, {RK_CARD: ["opt-fire-rune-tce"]})
    assert not [r for r in other["derived"]["classResources"] if r["name"].startswith("Rune Carver: ")]


@needs_data
def test_stale_rune_pick_and_levels_below_the_card(catalog):
    # Hill / Storm need Fighter 7: at level 6 the pick is not on the card
    res = _res(catalog, "fighter", "rune-knight-tce", 6, {RK_CARD: ["opt-hill-rune-tce"]})
    assert not [r for r in res["derived"]["classResources"] if r["name"].startswith("Rune Carver: ")]
    res = _res(catalog, "fighter", "rune-knight-tce", 2, {RK_CARD: ["opt-fire-rune-tce"]})
    assert not [r for r in res["derived"]["classResources"] if r["name"].startswith("Rune Carver: ")]


@needs_data
def test_runes_2014_equals_mixed_and_2024_has_none(catalog):
    picks = {RK_CARD: ["opt-fire-rune-tce", "opt-frost-rune-tce"]}
    a = _res(catalog, "fighter", "rune-knight-tce", 12, picks, ruleset="mixed")["derived"]["classResources"]
    b = _res(catalog, "fighter", "rune-knight-tce", 12, picks, ruleset="2014")["derived"]["classResources"]
    assert a == b and sum(r["name"].startswith("Rune Carver: ") for r in a) == 2
    c = _res(catalog, "fighter", "rune-knight-tce", 12, picks, ruleset="2024")["derived"]["classResources"]
    assert not [r for r in c if r["name"].startswith("Rune Carver: ")]


@needs_data
def test_rune_export_line(catalog):
    res = _res(catalog, "fighter", "rune-knight-tce", 15, {RK_CARD: ["opt-fire-rune-tce"]})
    fire = _by_id(res)["fighter:rune-carver-fire-rune"]
    line = resource_line(fire, "en")
    assert line.startswith("Rune Carver: Fire Rune: 2, DC 15") or line.startswith("Rune Carver: Fire Rune: 2, ")
    assert "While wearing or carrying the inscribed object" in line and line.count("Strength saving throw") == 1


def test_unlisted_tables_have_no_other_keys():
    """The tables are the whole rule: option keys only the documented fields."""
    for spec in reference_data.ELEMENTAL_DISCIPLINES_2014["options"].values():
        assert set(spec) <= {"name", "cost", "quotes", "more"}
    for spec in reference_data.RUNE_KNIGHT_RUNES_2014["options"].values():
        assert set(spec) <= {"name", "quotes", "note", "dc"}


# ---- timing -----------------------------------------------------------------------------------------------------------

@needs_data
def test_timing(catalog):
    draft = _draft("fighter", "rune-knight-tce", 15, {RK_CARD: ["opt-fire-rune-tce", "opt-stone-rune-tce", "opt-hill-rune-tce",
                                                                "opt-storm-rune-tce", "opt-cloud-rune-tce"]})
    assert_fast(measure(lambda: resolve(copy.deepcopy(draft), catalog)), "fighter 15 rune knight with five runes")
    draft = _draft("monk", "four-elements-phb", 17, {FE_CARD: ["opt-fist-of-four-thunders-phb", "opt-water-whip-phb"]})
    assert_fast(measure(lambda: resolve(copy.deepcopy(draft), catalog)), "monk 17 four elements with two disciplines")
