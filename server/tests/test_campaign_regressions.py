"""Regressions for the REAL-BUG findings of the verification campaign (VF slices, docs/CAMPAIGN-PROTOCOL.md).

Each test was written failing first (the failing spec of the finding), then the engine was fixed. One section per fix;
the data quotes are pinned against the vendored 5etools records so a data refresh that changes a rule fails here."""
from __future__ import annotations

import json
import pathlib

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="official data not fetched")

DATA = pathlib.Path(__file__).resolve().parents[1] / "data" / "official"
ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2014", species="human", subspecies=None, scores=None, background="acolyte", sources=(), added=(),
           class_choices=None):
    entries = []
    for i, spec in enumerate(classes):
        e = {"classId": spec[0], "level": spec[1], "choices": dict((class_choices or {}).get(i, {}))}
        if len(spec) > 2 and spec[2]:
            e["subclassId"] = spec[2]
        entries.append(e)
    base = {a: 10 for a in ABS}
    base.update(scores or {})
    sp = {"id": species, "choices": {}}
    if subspecies:
        sp["subspeciesId"] = subspecies
    return {"name": "t", "ruleset": ruleset, "sources": list(sources), "classes": entries,
            "background": {"id": background, "choices": {}}, "species": sp,
            "abilities": {"method": "manual", "base": base},
            "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added], "skipped": False},
            "details": {}}


# ---------------------------------------------------------------- VF1.1 TCE Glory Paladin 7 Aura of Alacrity
def test_vf1_1_data_quote_tce_aura_of_alacrity():
    recs = json.load(open(DATA / "class" / "class-paladin.json"))["subclassFeature"]
    tce = next(r for r in recs if r["name"] == "Aura of Alacrity" and r["source"] == "TCE")
    assert tce["level"] == 7 and tce["subclassShortName"] == "Glory"
    assert "Your walking speed increases by 10 feet." in tce["entries"][1]


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_vf1_1_glory_tce_7_adds_ten_feet_of_walking_speed(catalog, ruleset):
    base = _draft([("paladin", 7, "glory-tce")], ruleset=ruleset)
    other = _draft([("paladin", 7, "devotion")], ruleset=ruleset)
    glory = resolve(base, catalog)["derived"]["speeds"]
    plain = resolve(other, catalog)["derived"]["speeds"]
    assert glory["walk"] == plain["walk"] + 10


def test_vf1_1_glory_tce_6_has_no_bonus(catalog):
    a = resolve(_draft([("paladin", 6, "glory-tce")]), catalog)["derived"]["speeds"]
    b = resolve(_draft([("paladin", 6, "devotion")]), catalog)["derived"]["speeds"]
    assert a["walk"] == b["walk"]


# ---------------------------------------------------------------- VF1.2 a spell id starting with "skill-" is not a skill
def _skill_ids(catalog):
    from catalog import reference_data
    return set(reference_data.SKILL_ABILITY)


def test_vf1_2_skill_empowerment_is_a_spell_not_a_skill(catalog):
    """spells-xge.json Skill Empowerment is a spell; the engine took every selected id starting with 'skill-' as a skill."""
    spells = json.load(open(DATA / "spells" / "spells-xge.json"))["spell"]
    assert any(s["name"] == "Skill Empowerment" and s["level"] == 5 for s in spells)
    for ruleset in ("2014", "mixed", "2024"):
        d = _draft([("bard", 9)], ruleset=ruleset)
        d["classes"][0]["choices"] = {"class:bard:spells-known": ["skill-empowerment"]}
        res = resolve(d, catalog)
        card = next(c for c in res["choices"] if c["id"] == "class:bard:spells-known")
        assert "skill-empowerment" in card["selected"], ruleset
        skills = res["sheet"]["proficiencies"]["skills"]
        assert "skill-empowerment" not in skills, ruleset
        assert set(skills) <= _skill_ids(catalog), ruleset
        assert "skill-empowerment" not in {k for k in res["derived"]["skills"]}, ruleset


def test_vf1_2_no_skill_option_of_a_proficiency_card_is_blocked_by_a_spell_id(catalog):
    """The duplicate-skill gate reads the picked skills of other cards: a Bard 9 with the spell picked offers the same
    skill options (none disabled for a 'duplicate' of the spell id) as without it."""
    def options(pick):
        d = _draft([("bard", 9)], ruleset="2014")
        if pick:
            d["classes"][0]["choices"] = {"class:bard:spells-known": ["skill-empowerment"]}
        res = resolve(d, catalog)
        return {c["id"]: [(o["id"], o.get("disabled")) for o in c["options"]] for c in res["choices"]
                if c["options"] and all(o["id"].startswith("skill-") and o["id"] != "skill-empowerment" for o in c["options"])}
    assert options(True) == options(False)


# ---------------------------------------------------------------- VF1.3 a feat's ability-bonus card at the 20 cap
def _all20(catalog, feat, ruleset="2014", species="dragonborn-(metallic)-ftd", pick=None, cls=("barbarian", 4), extra=None):
    d = _draft([cls], ruleset=ruleset, scores={a: 20 for a in ABS}, species=species)
    choices = {f"class:{cls[0]}:{cls[1]}:asi": [f"feat:{feat}"]}
    if pick:
        choices[f"class:{cls[0]}:{cls[1]}:asi:feat:{feat}:ability-bonus"] = pick
    d["classes"][0]["choices"] = choices
    return resolve(d, catalog)


@pytest.mark.parametrize("feat,ab", [("warlike-familiar-au", "str"), ("transmutation-adept-au", "int")])
def test_vf1_3_half_feat_card_is_satisfiable_with_every_score_at_20(catalog, feat, ab):
    """PHB p.165 "Increase the chosen score by 1, to a maximum of 20": at 20 the +1 is lost, the feat is still taken and the
    card can be settled (it stayed pending with every option disabled)."""
    cid = f"class:barbarian:4:asi:feat:{feat}:ability-bonus"
    pending = next(c for c in _all20(catalog, feat)["choices"] if c["id"] == cid)
    assert pending["status"] == "pending" and pending["options"] and not any(o.get("disabled") for o in pending["options"])
    res = _all20(catalog, feat, pick=[ab])
    card = next(c for c in res["choices"] if c["id"] == cid)
    assert card["status"] == "resolved" and card["selected"] == [ab]
    assert res["sheet"]["abilities"] == {a: 20 for a in ABS}
    assert any(feat in json.dumps(f) for f in res["sheet"]["feats"])
    notes = [p for p in res["pruned"] if p["choiceId"] == cid]
    assert len(notes) == 1 and f"{ab.upper()} is already at maximum (20)" in notes[0]["reason"]
    assert res["problems"] == []


def test_vf1_3_partial_cap_still_disables_only_the_capped_options(catalog):
    d = _draft([("barbarian", 4)], ruleset="2014", scores={**{a: 14 for a in ABS}, "STR": 20, "DEX": 20}, species="dragonborn-(metallic)-ftd")
    d["classes"][0]["choices"] = {"class:barbarian:4:asi": ["feat:athlete-phb"]}
    d["abilities"]["base"]["DEX"] = 14
    res = resolve(d, catalog)
    card = next(c for c in res["choices"] if c["id"].endswith("athlete-phb:ability-bonus"))
    flags = {o["id"]: bool(o.get("disabled")) for o in card["options"]}
    assert flags == {"str": True, "dex": False}
    d["abilities"]["base"]["DEX"] = 20
    d["classes"][0]["choices"] = {"class:barbarian:4:asi": ["feat:warlike-familiar-au"]}
    res = resolve(d, catalog)
    card = next(c for c in res["choices"] if c["id"].endswith("warlike-familiar-au:ability-bonus"))
    flags = {o["id"]: bool(o.get("disabled")) for o in card["options"]}
    assert flags["str"] and flags["dex"] and not flags["con"]


def test_vf1_3_chartest_t3_specs_now_settle():
    """The two campaign specs (t3-030 2014, t3-056 2024) were FillStuck."""
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from tools.chartest import matrix, spec as spec_mod
    catalog = load()
    for spec_id in ("t3-030-ability-limits-high-2014", "t3-056-ability-limits-high-2024"):
        s = next(x for x in matrix.generate("T3", 0) if x.id == spec_id)
        spec_mod.resolve_spec(s, catalog)  # raises FillStuck when the card cannot be settled


# ---------------------------------------------------------------- VF1.4 Draconblood / Ravenite replace Damage Resistance
def test_vf1_4_data_both_egw_subraces_overwrite_damage_resistance():
    subs = [r for r in json.load(open(DATA / "races.json"))["subrace"]
            if r.get("raceName") == "Dragonborn" and r.get("source") == "EGW" and r["name"] in ("Draconblood", "Ravenite")]
    assert len(subs) == 2
    for r in subs:
        assert r["resist"] is None
        assert "Damage Resistance" in [e.get("data", {}).get("overwrite") for e in r["entries"] if isinstance(e, dict)]


@pytest.mark.parametrize("sub", ["dragonborn-phb-draconblood-egw", "dragonborn-phb-ravenite-egw"])
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_vf1_4_no_resistance_card_and_no_pick_based_resistance(catalog, sub, ruleset):
    res = resolve(_draft([("wizard", 1)], ruleset=ruleset, species="dragonborn-phb", subspecies=sub), catalog)
    ids = [c["id"] for c in res["choices"] if c["source"]["kind"] == "species"]
    assert "species:dragonborn-phb:resistance" not in ids
    assert "species:dragonborn-phb:draconic-ancestry" in ids  # the breath weapon still follows the ancestry card
    assert res["sheet"]["damageModifiers"]["resistances"] == []


def test_vf1_4_the_phb_dragonborn_and_other_subraces_keep_the_resistance_card(catalog):
    res = resolve(_draft([("wizard", 1)], species="dragonborn-phb"), catalog)
    assert "species:dragonborn-phb:resistance" in [c["id"] for c in res["choices"]]


# ---------------------------------------------------------------- VF1.5 / VF1.6 innate spells: the frequency of the trait text
# Verified against races.json before the code. A bare `innate` level list has no frequency wrapper; the converter read it as
# at-will. The trait entries of the same record state the limit:
#   Aarakocra MPMM Wind Caller, Firbolg MPMM, Genasi (Earth) MPMM Merge with Stone, Variant Mark of Detection / Finding,
#   Mark of Healing: "Once you cast ... you can't ... again until you finish a long rest";
#   Yuan-ti MPMM / VGM: "You can cast animal friendship an unlimited number of times" (genuinely at-will, unchanged).
# `known: {"1": {"rest": {"1": [...]}}}` (Firbolg VGM, Eladrin DMG, Mark of Handling) is read as one cast per short or long rest.
def _entries_text(rec) -> str:
    out = []

    def walk(e):
        if isinstance(e, str):
            out.append(e)
        elif isinstance(e, dict):
            for k in ("entries", "items", "rows"):
                for x in e.get(k) or []:
                    walk(x)
        elif isinstance(e, list):
            for x in e:
                walk(x)
    walk(rec.get("entries") or [])
    return "\n".join(out)


def _races_json():
    return json.load(open(DATA / "races.json"))


def _record(kind, name, source, race=None):
    return next(r for r in _races_json()[kind] if r.get("name") == name and r.get("source") == source
                and (race is None or r.get("raceName") == race))


def test_vf1_5_data_the_trait_texts_state_the_limits():
    must = [("race", "Aarakocra", "MPMM", None, "you can't do so again until you finish a long rest"),
            ("race", "Firbolg", "MPMM", None, "you can't cast that spell with it again until you finish a long rest"),
            ("subrace", "Earth", "MPMM", "Genasi", "you can't do so again until you finish a long rest"),
            ("subrace", "Variant; Mark of Detection", "ERLW", "Half-Elf", "you can't cast that spell with it again until you finish a long rest"),
            ("subrace", "Variant; Mark of Finding", "ERLW", "Half-Orc", "you can't cast that spell with it again until you finish a long rest"),
            ("subrace", "Variant; Mark of Finding", "ERLW", "Human", "you can't cast that spell with it again until you finish a long rest"),
            ("subrace", "Mark of Healing", "ERLW", None, "you can't cast that spell with it again until you finish a long rest"),
            ("race", "Firbolg", "VGM", None, "you can't cast it again with this trait until you finish a short or long rest"),
            ("subrace", "Eladrin", "DMG", None, "You regain the ability to do so when you finish a short or long rest"),
            ("subrace", "Mark of Handling", "ERLW", None, "you can't cast that spell with it again until you finish a short or long rest")]
    for kind, name, source, race, quote in must:
        assert quote in _entries_text(_record(kind, name, source, race)), (name, source)
    for name, source in (("Yuan-Ti", "MPMM"), ("Yuan-ti Pureblood", "VGM")):
        assert "unlimited number of times" in _entries_text(_record("race", name, source))


def _innate(catalog, species, subspecies=None):
    res = resolve(_draft([("wizard", 3)], species=species, subspecies=subspecies, ruleset="2014"), catalog)
    return {e["spellId"]: e for e in res["sheet"]["innateSpells"]}


LONG = ("1/day", 1, "long")
EITHER = ("1/short or long rest", 1, "short-or-long")
AT_WILL = ("at-will", None, None)

# (species, subspecies) -> {spell id: (uses, usesMax, recharge)}
VF1_EXPECTED = {
    ("aarakocra-mpmm", None): {"gust-of-wind": LONG},
    ("firbolg-mpmm", None): {"detect-magic": LONG, "disguise-self": LONG},
    ("genasi-mpmm", "genasi-mpmm-earth-mpmm"): {"blade-ward": AT_WILL, "pass-without-trace": LONG},
    ("half-elf-phb", "half-elf-phb-variant;-mark-of-detection-erlw"): {
        "detect-magic": LONG, "detect-poison-and-disease": LONG, "see-invisibility": LONG},
    ("half-orc-phb", "half-orc-phb-variant;-mark-of-finding-erlw"): {"hunters-mark": LONG, "locate-object": LONG},
    ("human-phb", "human-phb-variant;-mark-of-finding-erlw"): {"hunters-mark": LONG, "locate-object": LONG},
    ("halfling-phb", "halfling-phb-mark-of-healing-erlw"): {"cure-wounds": LONG, "lesser-restoration": LONG},
    ("firbolg-vgm", None): {"detect-magic": EITHER, "disguise-self": EITHER},
    ("elf-phb", "elf-phb-eladrin-dmg"): {"misty-step": EITHER},
    ("human-phb", "human-phb-mark-of-handling-erlw"): {"animal-friendship": EITHER, "speak-with-animals": EITHER},
}


@pytest.mark.parametrize("key", sorted(VF1_EXPECTED, key=str))
def test_vf1_5_6_innate_frequency_follows_the_record(catalog, key):
    got = _innate(catalog, *key)
    for spell_id, (uses, mx, recharge) in VF1_EXPECTED[key].items():
        assert spell_id in got, (key, spell_id, sorted(got))
        e = got[spell_id]
        assert e["uses"] == uses, (key, spell_id, e["uses"])
        assert e.get("usesMax") == mx and e.get("recharge") == recharge, (key, spell_id)


@pytest.mark.parametrize("species", ["yuan-ti-mpmm", "yuan-ti-pureblood-vgm"])
def test_vf1_5_unlimited_animal_friendship_stays_at_will(catalog, species):
    got = _innate(catalog, species)
    assert got["animal-friendship"]["uses"] == "at-will" and "usesMax" not in got["animal-friendship"]
    assert got["suggestion"]["uses"] == "1/day"


def test_vf1_5_phb_tiefling_cantrip_and_other_at_will_cantrips_do_not_move(catalog):
    got = _innate(catalog, "tiefling-phb")
    assert got["thaumaturgy"]["uses"] == "at-will"
    assert got["hellish-rebuke"]["uses"] == "1/day"


def test_vf1_5_every_bare_innate_list_is_either_at_will_by_text_or_limited_by_text():
    """Exhaustive over the vendored records: every bare list entry (no frequency wrapper) of races and subraces is in
    VF1_EXPECTED (limited) or is one of the two Yuan-ti records ("unlimited number of times")."""
    seen = set()
    for kind in ("race", "subrace"):
        for r in _races_json()[kind]:
            for ent in r.get("additionalSpells") or []:
                inn = ent.get("innate")
                if isinstance(inn, dict) and any(isinstance(v, list) for v in inn.values()):
                    seen.add((r["name"], r.get("source"), r.get("raceName")))
    assert seen == {("Aarakocra", "MPMM", None), ("Firbolg", "MPMM", None), ("Yuan-Ti", "MPMM", None),
                    ("Yuan-ti Pureblood", "VGM", None), ("Earth", "MPMM", "Genasi"),
                    ("Variant; Mark of Detection", "ERLW", "Half-Elf"), ("Variant; Mark of Finding", "ERLW", "Half-Orc"),
                    ("Variant; Mark of Finding", "ERLW", "Human"), ("Mark of Healing", "ERLW", "Halfling")}


# ---------------------------------------------------------------- VF1.7 Primal Strike / Divine Strike damage types in the exports
def _strike_result(catalog, cls, level, cid, option):
    d = _draft([(cls, level)], ruleset="2024", species="human-xphb", scores={"WIS": 16})
    d["classes"][0]["choices"] = {cid: [option]}
    return resolve(d, catalog)


def test_vf1_7_primal_strike_damage_types_reach_markdown_and_pdf(catalog):
    import markdown_export
    import pdf_export
    from export_labels import label
    res = _strike_result(catalog, "druid", 7, "class:druid:7:feature:xphb-druid-7-elemental-fury", "xphb-druid-7-primal-strike")
    strike = next(r for r in res["derived"]["classResources"] if r["name"] == "Primal Strike")
    assert strike["details"]["damageTypes"] == "Cold, Fire, Lightning, or Thunder"
    for lang in ("en", "bg"):
        line = label(lang, "damageTypesLine", types=strike["details"]["damageTypes"])
        assert "Cold, Fire, Lightning, or Thunder" in line
        md = markdown_export.to_markdown(res, lang=lang) if "lang" in markdown_export.to_markdown.__code__.co_varnames else markdown_export.to_markdown(res)
        assert line in md, lang
    assert label("en", "damageTypesLine", types="X") == "damage types: X"
    assert label("bg", "damageTypesLine", types="X") == "типове щети: X"


def test_vf1_7_divine_strike_uses_the_same_fragment(catalog):
    import markdown_export
    from export_labels import label
    res = _strike_result(catalog, "cleric", 7, "class:cleric:7:feature:xphb-cleric-7-blessed-strikes", "xphb-cleric-7-divine-strike")
    strike = next(r for r in res["derived"]["classResources"] if r["name"] == "Divine Strike")
    assert label("bg", "damageTypesLine", types=strike["details"]["damageTypes"]) in markdown_export.to_markdown(res)


# ---------------------------------------------------------------- VF1.8 PHB Dwarf lists Tool Proficiency once
def test_vf1_8_data_phb_dwarf_has_one_tool_proficiency_entry():
    d = _record("race", "Dwarf", "PHB")
    assert [e["name"] for e in d["entries"] if isinstance(e, dict) and e.get("name") == "Tool Proficiency"] == ["Tool Proficiency"]


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_vf1_8_dwarf_phb_tool_proficiency_listed_once_with_the_pick(catalog, ruleset):
    cid = "species:dwarf-phb:trait:dwarf-phb-trait-choice-tool-proficiency:proficiency-choice"
    d = _draft([("wizard", 1)], ruleset=ruleset, species="dwarf-phb")
    d["species"]["choices"] = {cid: ["smiths-tools"]}
    res = resolve(d, catalog)
    tools = [f for f in res["sheet"]["features"] if f["name"] == "Tool Proficiency"]
    assert len(tools) == 1
    assert tools[0].get("choice") == ["Smith's Tools"]  # the pick label stays on the single entry
    unpicked = [f for f in resolve(_draft([("wizard", 1)], ruleset=ruleset, species="dwarf-phb"), catalog)["sheet"]["features"]
                if f["name"] == "Tool Proficiency"]
    assert len(unpicked) == 1 and "choice" not in unpicked[0]


def test_vf1_8_no_species_lists_a_proficiency_choice_name_twice(catalog):
    """Every species and subspecies of the catalog: a synthetic proficiency-choice trait never repeats the name of the
    species' own trait (the dwarf-phb case). (Other repeated names are a subrace replacing a race trait, e.g. Draconblood's
    Draconic Ancestry, and are not this defect.)"""
    from collections import Counter
    bad = []
    for rid, race in catalog.races.items():
        subs = [None] + [s["index"] for s in catalog.subraces.values() if (s.get("race") or {}).get("index") == rid]
        for sub in subs:
            d = _draft([("wizard", 1)], ruleset="2014", species=rid, subspecies=sub)
            res = resolve(d, catalog)
            names = Counter(f["name"] for f in res["sheet"]["features"] if f["source"]["kind"] == "species")
            dup = [n for n, c in names.items() if c > 1 and n in ("Tool Proficiency", "Skill Proficiency")]
            if dup:
                bad.append((rid, sub, dup))
    assert bad == []


# ---------------------------------------------------------------- VF1.9 (a) a final score above 20, (b) an unknown equipment item
def _warning_ids(res):
    return [w["id"] for w in res["warnings"]]


def test_vf1_9a_final_score_above_20_from_base_plus_species_bonus_warns(catalog):
    """Manual scores stay an override; the cap-20 note fires for the FINAL score too (campaign t3-018 / t3-019: 19 + 2, 20 + 2)."""
    d = _draft([("fighter", 1)], ruleset="2014", species="dwarf", subspecies="hill-dwarf", scores={"CON": 19, "WIS": 20})
    res = resolve(d, catalog)
    final = res["sheet"]["abilities"]
    assert final["CON"] == 21 and final["WIS"] == 21  # Hill Dwarf: CON +2, WIS +1; the engine keeps the manual override
    ids = _warning_ids(res)
    assert "ability-final-above-20-CON" in ids and "ability-final-above-20-WIS" in ids
    assert len(ids) == len(set(ids))
    msg_ = next(w["message"] for w in res["warnings"] if w["id"] == "ability-final-above-20-CON")
    assert "CON" in msg_ and "21" in msg_ and "19" in msg_


def test_vf1_9a_no_warning_at_or_below_20_and_no_double_report_above_a_base_over_20(catalog):
    res = resolve(_draft([("fighter", 1)], ruleset="2014", species="dwarf", subspecies="hill-dwarf", scores={"CON": 18}), catalog)
    assert res["sheet"]["abilities"]["CON"] == 20
    assert not [i for i in _warning_ids(res) if "above-20" in i]
    res = resolve(_draft([("fighter", 1)], ruleset="2014", scores={"STR": 22}), catalog)  # base 22: the existing base warning only
    assert [i for i in _warning_ids(res) if "above-20" in i] == ["ability-above-20-STR"]


def test_vf1_9a_primal_champion_and_epic_boons_are_not_reported(catalog):
    """Barbarian 20 (Primal Champion +4, cap 24) with 20 STR: the class feature, not a manual score, raises it."""
    res = resolve(_draft([("barbarian", 20)], ruleset="2014", scores={"STR": 19}), catalog)  # Human +1 = 20, Primal Champion +4 = 24
    assert res["sheet"]["abilities"]["STR"] == 24
    assert not [i for i in _warning_ids(res) if "above-20" in i]


def test_vf1_9_messages_exist_in_both_languages():
    from i18n.messages import msg, render
    final = msg("ability-final-above-20", ab="CON", value=21, base=19)
    assert "CON" in final and "21" in final and "19" in final
    bg = render(final, "bg")
    assert bg != str(final) and "21" in bg and "CON" in bg
    item = msg("equipment-unknown-item", item="plate")
    assert "plate" in item and "plate" in render(item, "bg") and render(item, "bg") != str(item)


def test_vf1_9b_unknown_equipment_item_warns_instead_of_vanishing(catalog):
    d = _draft([("fighter", 3)], ruleset="2024", species="human-xphb", added=["plate", "plate-armor"])
    res = resolve(d, catalog)
    ids = _warning_ids(res)
    assert ids.count("equipment-unknown-item-0") == 1 and "equipment-unknown-item-1" not in ids
    assert [e["itemId"] for e in res["sheet"]["equipment"]["added"]] == ["plate-armor"] if "added" in res["sheet"]["equipment"] else True
    assert "plate" in next(w["message"] for w in res["warnings"] if w["id"] == "equipment-unknown-item-0")
    assert res["problems"] == []


def test_vf1_9b_no_warning_for_known_items(catalog):
    res = resolve(_draft([("fighter", 1)], added=["longsword"]), catalog)
    assert not [i for i in _warning_ids(res) if i.startswith("equipment-unknown-item")]


# ---------------------------------------------------------------- VF2.1 species natural armor / flat AC bonuses
import re as _re  # noqa: E402


def _plain(text) -> str:
    """5etools text with the {@tag shown|...} markup reduced to the shown word(s)."""
    s = " ".join(text) if isinstance(text, list) else text
    return _re.sub(r"\{@\w+ ([^|}]*)[^}]*\}", r"\1", s)


def _race_strings(name, source):
    rec = next(r for r in _races_json()["race"] if r["name"] == name and r["source"] == source)
    out = []

    def walk(o):
        if isinstance(o, str):
            out.append(_plain(o))
        elif isinstance(o, dict):
            for v in o.get("entries", []) + o.get("items", []) + ([o["entry"]] if "entry" in o else []):
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(rec.get("entries", []))
    return out


# trait id -> (record name, source, kind, base, abilities, sentence quoted from the record)
VF2_1 = {
    "autognome-aag-trait-1": ("Autognome", "AAG", "unarmored", 13, ("DEX",),
                              "While you aren't wearing armor, your base Armor Class is 13 + your Dexterity modifier."),
    "thri-kreen-aag-trait-2": ("Thri-kreen", "AAG", "unarmored", 13, ("DEX",),
                               "While you aren't wearing armor, your carapace gives you a base Armor Class of 13 + your Dexterity modifier."),
    "goblin-psz-trait-5": ("Goblin", "PSZ", "unarmored", 11, ("DEX",),
                           "when you are wearing no armor, your AC is equal to 11 + your Dexterity modifier."),
    "lizardfolk-mpmm-trait-4": ("Lizardfolk", "MPMM", "natural", 13, ("DEX",),
                                "When you aren't wearing armor, your base AC is 13 + Dexterity modifier. You can use your natural armor to "
                                "determine your AC if the armor you wear would leave you with a lower AC."),
    "lizardfolk-vgm-trait-7": ("Lizardfolk", "VGM", "natural", 13, ("DEX",),
                               "When you aren't wearing armor, your AC is 13 + your Dexterity modifier. You can use your natural armor to "
                               "determine your AC if the armor you wear would leave you with a lower AC."),
    "locathah-lr-trait-2": ("Locathah", "LR", "natural", 12, ("DEX",),
                            "When you aren't wearing armor, your AC is 12 + your Dexterity modifier. You can use your natural armor to "
                            "determine your AC if the armor you wear would leave you with a lower AC."),
    "loxodon-ggr-trait-5": ("Loxodon", "GGR", "natural", 12, ("CON",),
                            "When you aren't wearing armor, your AC is 12 + your Constitution modifier. You can use your natural armor to "
                            "determine your AC if the armor you wear would leave you with a lower AC."),
    "tortle-mpmm-trait-3": ("Tortle", "MPMM", "fixed", 17, (),
                            "Your shell provides you a base AC of 17 (your Dexterity modifier doesn't affect this number). "
                            "You can't wear light, medium, or heavy armor, but if you are using a shield, you can apply the shield's bonus as normal."),
    "tortle-ttp-trait-6": ("Tortle", "TTP", "fixed", 17, (),
                           "it gives you a base AC of 17 (your Dexterity modifier doesn't affect this number). You gain no benefit from "
                           "wearing armor, but if you are using a shield, you can apply the shield's bonus as normal."),
    "lizardfolk-dmg-trait-1": ("Lizardfolk", "DMG", "flat", 3, (), "granting you a +3 bonus to Armor Class."),
    "troglodyte-dmg-trait-3": ("Troglodyte", "DMG", "flat", 1, (), "Your thick hide grants you a +1 bonus to Armor Class."),
    "warforged-erlw-trait-5": ("Warforged", "ERLW", "flat", 1, (), "You gain a +1 bonus to Armor Class."),
    "warforged-efa-trait-1": ("Warforged", "EFA", "flat", 1, (), "You gain a +1 bonus to your Armor Class."),
}


def test_vf2_1_the_table_is_exactly_the_records(catalog):
    from catalog import reference_data as ref
    assert set(ref.SPECIES_AC) == set(VF2_1), set(ref.SPECIES_AC) ^ set(VF2_1)
    for tid, (name, source, kind, base, abilities, sentence) in VF2_1.items():
        entry = ref.SPECIES_AC[tid]
        assert (entry["kind"], entry["base"], tuple(entry["abilities"]), entry["quote"]) == (kind, base, abilities, sentence), tid
        assert any(sentence in s for s in _race_strings(name, source)), (tid, "quote not in the record")
        assert tid in [t["index"] for t in catalog.races[tid.rsplit("-trait-", 1)[0]]["traits"]]


def test_vf2_1_no_other_unconditional_ac_text_in_the_species_records():
    """Every race record sentence that states a base AC / a flat AC bonus is in the table or listed here as conditional / not an
    AC of the character (shifted forms, Shell Defense withdrawn, a Prestidigitation device with AC 5, the Simic Carapace pick)."""
    from catalog import reference_data as ref
    covered = {(v[0], v[1]) for v in VF2_1.values()}
    allowed_other = {("Shifter", "EFA"), ("Shifter", "MPMM"), ("Gnome", "XPHB"), ("Simic Hybrid", "GGR")}
    found = set()
    for rec in _races_json()["race"]:
        for s in _race_strings(rec["name"], rec["source"]):
            if _re.search(r"\bAC\b|Armor Class", s):
                found.add((rec["name"], rec["source"]))
    # Tortle holds a second AC sentence (Shell Defense) next to its table row
    assert found - covered == allowed_other, found - covered - allowed_other
    assert ref.SPECIES_AC


AC_ITEMS = {"leather": "leather-armor", "chain": "chain-mail", "plate": "plate-armor", "shield": "shield"}


def _ac(catalog, species, scores, added=(), classes=(("fighter", 1),), ruleset="2014"):
    d = _draft(list(classes), ruleset=ruleset, species=species, scores=scores, added=added)
    return resolve(d, catalog)["derived"]["armorClass"]


@pytest.mark.parametrize("species,scores,armor,expected", [
    # unarmored formula only without armor: Autognome / Thri-kreen 13 + DEX (+2), Goblin PSZ 11 + DEX
    ("autognome-aag", {"DEX": 14}, (), 15), ("autognome-aag", {"DEX": 14}, ("shield",), 17),
    ("autognome-aag", {"DEX": 14}, ("leather-armor",), 13), ("autognome-aag", {"DEX": 14}, ("chain-mail",), 16),
    ("thri-kreen-aag", {"DEX": 14}, (), 15), ("thri-kreen-aag", {"DEX": 14}, ("leather-armor", "shield"), 15),
    ("goblin-psz", {"DEX": 14}, (), 13), ("goblin-psz", {"DEX": 14}, ("chain-mail",), 16),
    # natural armor, better of natural and worn armor, shield as normal: Lizardfolk 13 + DEX, Locathah 12 + DEX, Loxodon 12 + CON
    ("lizardfolk-mpmm", {"DEX": 14}, (), 15), ("lizardfolk-vgm", {"DEX": 14}, (), 15),
    ("lizardfolk-mpmm", {"DEX": 14}, ("leather-armor",), 15), ("lizardfolk-mpmm", {"DEX": 14}, ("plate-armor",), 18),
    ("lizardfolk-mpmm", {"DEX": 14}, ("shield",), 17), ("lizardfolk-mpmm", {"DEX": 14}, ("leather-armor", "shield"), 17),
    ("lizardfolk-mpmm", {"DEX": 14}, ("plate-armor", "shield"), 20),
    ("locathah-lr", {"DEX": 14}, (), 14), ("locathah-lr", {"DEX": 14}, ("leather-armor",), 14), ("locathah-lr", {"DEX": 14}, ("chain-mail",), 16),
    ("loxodon-ggr", {"CON": 14, "DEX": 8}, (), 15), ("loxodon-ggr", {"CON": 14, "DEX": 8}, ("leather-armor", "shield"), 17),  # GGR Loxodon CON +2
    ("loxodon-ggr", {"CON": 14}, ("chain-mail",), 16),
    # Tortle: base AC 17, DEX does not affect it, armor gives no benefit, a shield adds
    ("tortle-mpmm", {"DEX": 14}, (), 17), ("tortle-mpmm", {"DEX": 8}, (), 17), ("tortle-mpmm", {"DEX": 14}, ("shield",), 19),
    ("tortle-ttp", {"DEX": 14}, (), 17), ("tortle-ttp", {"DEX": 14}, ("plate-armor",), 17), ("tortle-ttp", {"DEX": 14}, ("plate-armor", "shield"), 19),
    # flat bonuses, also in armor
    ("lizardfolk-dmg", {"DEX": 14}, (), 15), ("lizardfolk-dmg", {"DEX": 14}, ("leather-armor",), 16),
    ("troglodyte-dmg", {"DEX": 14}, (), 13), ("troglodyte-dmg", {"DEX": 14}, ("chain-mail", "shield"), 19),
    ("warforged-erlw", {"DEX": 14}, (), 13), ("warforged-erlw", {"DEX": 14}, ("plate-armor",), 19),
    # unchanged
    ("human", {"DEX": 14}, (), 12), ("human", {"DEX": 14}, ("leather-armor",), 13),
])
def test_vf2_1_species_ac(catalog, species, scores, armor, expected):
    got = _ac(catalog, species, scores, armor)
    assert got == expected, (species, scores, armor, got)


def test_vf2_1_warforged_efa_plus_one_under_2024(catalog):
    assert _ac(catalog, "warforged-efa", {"DEX": 14}, (), ruleset="2024") == 13
    assert _ac(catalog, "warforged-efa", {"DEX": 14}, ("plate-armor",), ruleset="2024") == 19


def test_vf2_1_the_best_formula_wins_never_summed(catalog):
    # Monk Unarmored Defense 10 + DEX + WIS (+4) = 16 against the lizardfolk 13 + DEX = 15: the better one, not both
    assert _ac(catalog, "lizardfolk-mpmm", {"DEX": 14, "WIS": 18}, (), classes=(("monk", 1),)) == 16
    # the Barbarian 10 + DEX + CON (14 -> +2) = 14 loses against 15
    assert _ac(catalog, "lizardfolk-mpmm", {"DEX": 14, "CON": 14}, (), classes=(("barbarian", 1),)) == 15
    # the Tortle's fixed 17 against a Monk 10 + DEX + WIS = 16
    assert _ac(catalog, "tortle-mpmm", {"DEX": 14, "WIS": 18}, (), classes=(("monk", 1),)) == 17


def test_vf2_1_the_flat_bonus_adds_to_the_best_formula(catalog):
    # Lizardfolk (DMG) +3 on top of the Monk formula 16
    assert _ac(catalog, "lizardfolk-dmg", {"DEX": 14, "WIS": 18}, (), classes=(("monk", 1),)) == 19


# ---------------------------------------------------------------- VF2.2 Harengon Hare-Trigger
VF2_2 = {"harengon-mpmm-trait-1": ("Harengon", "MPMM"), "harengon-wbtw-trait-1": ("Harengon", "WBtW")}
HARE_TRIGGER = "You can add your proficiency bonus to your initiative rolls."


def test_vf2_2_table_is_exactly_the_records(catalog):
    from catalog import reference_data as ref
    assert set(ref.SPECIES_INITIATIVE_PB) == set(VF2_2)
    for tid, (name, source) in VF2_2.items():
        assert ref.SPECIES_INITIATIVE_PB[tid]["quote"] == HARE_TRIGGER
        assert HARE_TRIGGER in _race_strings(name, source), tid
        trait = next(t for t in catalog.races[tid.rsplit("-trait-", 1)[0]]["traits"] if t["index"] == tid)
        assert trait["name"] == "Hare-Trigger"
    # no other race record states a proficiency-bonus initiative
    hits = {(r["name"], r["source"]) for r in _races_json()["race"]
            if any(_re.search(r"proficiency bonus to (your )?initiative", s) for s in _race_strings(r["name"], r["source"]))}
    assert hits == set(VF2_2.values())


def _init(catalog, species, classes=(("fighter", 1),), scores=None, ruleset="2014", **kw):
    d = _draft(list(classes), ruleset=ruleset, species=species, scores={"DEX": 14, **(scores or {})}, **kw)
    return resolve(d, catalog)["derived"]


@pytest.mark.parametrize("species", ["harengon-mpmm", "harengon-wbtw"])
@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_vf2_2_harengon_adds_the_proficiency_bonus_to_initiative(catalog, species, ruleset):
    der = _init(catalog, species, ruleset=ruleset)
    other = _init(catalog, "dwarf", ruleset=ruleset)  # control: no initiative trait
    dex = der["abilityModifiers"]["DEX"]
    assert der["initiative"] == dex + der["proficiencyBonus"] == dex + 2
    assert other["initiative"] == other["abilityModifiers"]["DEX"]


def test_vf2_2_the_bonus_grows_with_the_proficiency_bonus(catalog):
    der = _init(catalog, "harengon-mpmm", classes=(("fighter", 9),))
    assert der["proficiencyBonus"] == 4 and der["initiative"] == der["abilityModifiers"]["DEX"] + 4


def test_vf2_2_it_replaces_the_half_bonus_of_jack_of_all_trades(catalog):
    # Jack of All Trades (Bard 2) adds half the bonus only to a check that lacks the proficiency bonus: with Hare-Trigger it has it
    bard = _init(catalog, "harengon-mpmm", classes=(("bard", 2),))
    assert bard["initiative"] == bard["abilityModifiers"]["DEX"] + bard["proficiencyBonus"]
    plain = _init(catalog, "dwarf", classes=(("bard", 2),))
    assert plain["initiative"] == plain["abilityModifiers"]["DEX"] + 1


# ---------------------------------------------------------------- VF2.3 "count as one size larger" (Powerful Build and kin)
# race record -> trait name (every race record whose entries say it; found by scanning races.json, `_copy` records are not imported)
VF2_3 = {
    "bugbear-erlw": "Powerful Build", "bugbear-mpmm": "Powerful Build", "bugbear-vgm": "Powerful Build",
    "centaur-ggr": "Equine Build", "centaur-mpmm": "Equine Build",
    "firbolg-mpmm": "Powerful Build", "firbolg-vgm": "Powerful Build",
    "giff-aag": "Hippo Build",
    "goliath-mpmm": "Little Giant", "goliath-vgm": "Powerful Build", "goliath-xphb": "Powerful Build",
    "loxodon-ggr": "Powerful Build",
    "orc-erlw": "Powerful Build", "orc-mpmm": "Powerful Build", "orc-vgm": "Powerful Build",
}


def test_vf2_3_data_every_record_with_the_text(catalog):
    raw = {f"{r['name'].lower().replace(' ', '-')}-{r['source'].lower()}": r for r in _races_json()["race"]}
    found = {}
    for rid, rec in raw.items():
        if "_copy" in rec:
            continue
        for s in _race_strings(rec["name"], rec["source"]):
            if _re.search(r"count as one size larger when determining your carrying (capacity|weight)", s):
                found[rid] = s
    assert set(found) == set(VF2_3), set(found) ^ set(VF2_3)
    assert "carrying weight" in found["goliath-mpmm"]  # the record's own wording of the MPMM Little Giant
    # the same scan over the imported trait texts, by trait: the engine reads these, not a name list
    by_catalog = {rid for rid, r in catalog.races.items()
                  if any(_re.search(r"count as one size larger when determining your carrying (capacity|weight)",
                                    " ".join(catalog.traits[t["index"]]["desc"])) for t in r["traits"])}
    assert by_catalog == set(VF2_3)
    assert not any(" ".join(catalog.traits[t["index"]]["desc"]).count("size larger when determining") for s in catalog.subraces.values()
                   for t in s["racial_traits"])


def _carry(catalog, species, ruleset="2014", strength=14):
    res = resolve(_draft([("fighter", 1)], ruleset=ruleset, species=species, scores={"STR": strength}), catalog)
    return res["derived"]["carryingCapacity"], res["sheet"]["abilities"], res


@pytest.mark.parametrize("species", sorted(VF2_3))
@pytest.mark.parametrize("ruleset", ["2014", "2024"])
def test_vf2_3_capacity_and_push_drag_lift_double(catalog, species, ruleset):
    cc, _a, res = _carry(catalog, species, ruleset)
    strength = res["sheet"]["abilities"]["STR"]
    size = res["sheet"]["species"]["size"]
    assert size == "Medium", (species, size)  # the table below relies on Medium -> Large (x2)
    assert cc["capacity"] == strength * 15 * 2 and cc["pushDragLift"] == strength * 15 * 4, (species, cc, strength)


def test_vf2_3_control_species_without_the_trait_are_unchanged(catalog):
    for species in ("human", "dwarf", "halfling", "tortle-mpmm", "lizardfolk-mpmm", "goblin-mpmm"):
        cc, _a, res = _carry(catalog, species)
        strength = res["sheet"]["abilities"]["STR"]
        size = res["sheet"]["species"]["size"] or "Medium"
        assert cc["capacity"] == strength * 15 * (0.5 if size == "Tiny" else 1), (species, cc)


def test_vf2_3_the_size_ladder_for_derived():
    from engine import derived
    assert derived.carrying_capacity(10, "Medium", size_steps=1) == 300      # Large x2
    assert derived.carrying_capacity(10, "Small", size_steps=1) == 150       # Medium x1
    assert derived.carrying_capacity(10, "Tiny", size_steps=1) == 150        # Small x1
    assert derived.carrying_capacity(10, "Large", size_steps=1) == 600       # Huge x4
    assert derived.carrying_capacity(10, "Gargantuan", size_steps=1) == 1200  # no size above Gargantuan: x8 stays
    assert derived.carrying_capacity(10, "Huge") == 600 and derived.carrying_capacity(10, "Gargantuan") == 1200
    assert derived.carrying_summary(10, "Medium", [], {}, size_steps=1)["pushDragLift"] == 600


# ---------------------------------------------------------------- VF2.4 fixed species languages and language picks of official species
_LANG_POOL = {"common", "dwarvish", "elvish", "giant", "gnomish", "goblin", "halfling", "orc", "abyssal", "celestial", "draconic",
              "deep speech", "infernal", "primordial", "sylvan", "undercommon"}
_LANG_DIALECTS = {"auran", "aquan", "ignan", "terran"}   # Primordial dialects named by the records; not in the pick pool
_LANG_NON_KEYS = {"other", "anyStandard", "any", "choose"}


def _species_records():
    """(catalog id, kind, record) of every non-copy race / subrace of races.json that carries languageProficiencies."""
    from catalog.official.common import slug
    out = []
    for r in _races_json()["race"]:
        if "_copy" not in r and r.get("languageProficiencies"):
            out.append((f"{slug(r['name'])}-{r['source'].lower()}", "race", r))
    for r in _races_json()["subrace"]:
        if "_copy" not in r and r.get("name") and r.get("languageProficiencies"):
            rid = f"{slug(r['raceName'])}-{r['raceSource'].lower()}"
            out.append((f"{rid}-{slug(r['name'])}-{r['source'].lower()}", "subrace", r))
    return out


def test_vf2_4_data_no_2024_species_record_carries_fixed_languages():
    xphb = [r["name"] for r in _races_json()["race"] if r["source"] == "XPHB" and r.get("languageProficiencies")]
    assert xphb == []   # 2024 species give no languages: the origin gives Common plus two picks
    assert [r["name"] for r in _races_json()["race"] if r["source"] in ("EFA", "MPMM", "FTD") and r.get("languageProficiencies")] == []


def test_vf2_4_the_other_language_names_are_exactly_the_records_with_other(catalog):
    from catalog import reference_data as ref
    wanted = set()
    for cid, kind, rec in _species_records():
        has_other = any(e.get("other") or "other" in (e.get("choose") or {}).get("from", []) for e in rec["languageProficiencies"])
        if has_other and cid in (catalog.races if kind == "race" else catalog.subraces):
            wanted.add(cid)
    assert set(ref.SPECIES_OTHER_LANGUAGES) == wanted, set(ref.SPECIES_OTHER_LANGUAGES) ^ wanted
    by_id = {cid: (kind, rec) for cid, kind, rec in _species_records()}
    for cid, row in ref.SPECIES_OTHER_LANGUAGES.items():
        kind, rec = by_id[cid]
        strings = []

        def walk(o):
            if isinstance(o, str):
                strings.append(_plain(o))
            elif isinstance(o, dict):
                for v in o.get("entries", []) + o.get("items", []) + ([o["entry"]] if "entry" in o else []):
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(rec.get("entries", []))
        assert any(row["quote"] in s for s in strings), (cid, row["quote"])
        for name in row["names"]:
            assert name.split(" ")[0] in row["quote"], (cid, name)   # the name is written in the quoted sentence
            assert ref.LANGUAGE_NAMES[_slug(name)] == name


def _slug(name: str) -> str:
    from catalog.official.common import slug
    return slug(name)


def test_vf2_4_the_dialect_names_are_display_names_only():
    from catalog import reference_data as ref
    for key, name in (("auran", "Auran"), ("aquan", "Aquan"), ("ignan", "Ignan"), ("terran", "Terran")):
        assert ref.LANGUAGE_NAMES[key] == name
    assert len(ref.LANGUAGES) == 16 and not _LANG_DIALECTS & {l["index"] for l in ref.LANGUAGES}   # the pick pool is unchanged


def _expected_fixed(cid, rec, catalog):
    from catalog import reference_data as ref
    out = set()
    for e in rec["languageProficiencies"]:
        for k, v in e.items():
            if v is True and k not in _LANG_NON_KEYS:
                out.add(_slug(k))
        if e.get("other"):
            out |= {_slug(n) for n in ref.SPECIES_OTHER_LANGUAGES[cid]["names"]}
    return out


def _lang_ids(res):
    return set(res["sheet"]["proficiencies"]["languages"])


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_vf2_4_every_official_species_has_its_fixed_languages(catalog, ruleset):
    checked = 0
    for cid, kind, rec in _species_records():
        if kind == "race":
            if cid not in catalog.races:
                continue
            d = _draft([("wizard", 1)], ruleset=ruleset, species=cid)
        else:
            if cid not in catalog.subraces:
                continue
            d = _draft([("wizard", 1)], ruleset=ruleset, species=catalog.subraces[cid]["race"]["index"], subspecies=cid)
        res = resolve(d, catalog)
        expect = _expected_fixed(cid, rec, catalog)
        assert expect <= _lang_ids(res), (cid, ruleset, expect - _lang_ids(res))
        checked += 1
    assert checked >= 60


def test_vf2_4_the_named_findings(catalog):
    kenku = _lang_ids(resolve(_draft([("wizard", 1)], species="kenku-dmg"), catalog))
    assert {"common", "auran"} <= kenku
    tiefling = _lang_ids(resolve(_draft([("wizard", 1)], species="tiefling-phb"), catalog))
    assert {"common", "infernal"} <= tiefling
    # Troglodyte: "Troglodyte" only, no Common
    trog = _lang_ids(resolve(_draft([("wizard", 1)], species="troglodyte-dmg"), catalog))
    assert trog == {"troglodyte"}
    # Tortle (TTP) Aquan + Common; Locathah the same
    assert {"common", "aquan"} <= _lang_ids(resolve(_draft([("wizard", 1)], species="tortle-ttp"), catalog))
    # Deep Gnome (DMG): Gnomish, Terran, Undercommon (no Common)
    assert _lang_ids(resolve(_draft([("wizard", 1)], species="gnome-(deep)-dmg"), catalog)) == {"gnomish", "terran", "undercommon"}


def _lang_cards(res):
    return {c["id"]: c for c in res["choices"] if c["id"].endswith(":languages") and c["source"]["kind"] == "species"}


def test_vf2_4_language_pick_cards_of_the_official_species(catalog):
    res = resolve(_draft([("wizard", 1)], species="human-phb"), catalog)
    card = _lang_cards(res)["species:human-phb:languages"]
    assert card["count"] == 1 and card["status"] == "pending" and len(card["options"]) == 16
    assert "common" in _lang_ids(res)
    half = _lang_cards(resolve(_draft([("wizard", 1)], species="half-elf-phb"), catalog))
    assert half["species:half-elf-phb:languages"]["count"] == 1
    # two picks: Changeling (ERLW) and Aetherborn (PSK) say "anyStandard: 2"
    for sp in ("changeling-erlw", "aetherborn-psk"):
        assert _lang_cards(resolve(_draft([("wizard", 1)], species=sp), catalog))[f"species:{sp}:languages"]["count"] == 2, sp
    # a subrace pick (High Elf PHB: "one extra language of your choice")
    high = resolve(_draft([("wizard", 1)], species="elf-phb", subspecies="elf-phb-high-phb"), catalog)
    assert _lang_cards(high)["species:elf-phb:subspecies:elf-phb-high-phb:languages"]["count"] == 1
    # the pick is a language of the character
    d = _draft([("wizard", 1)], species="human-phb")
    d["species"]["choices"] = {"species:human-phb:languages": ["draconic"]}
    assert "draconic" in _lang_ids(resolve(d, catalog))


def test_vf2_4_simic_hybrid_other_is_vedalken(catalog):
    card = _lang_cards(resolve(_draft([("wizard", 1)], species="simic-hybrid-ggr"), catalog))["species:simic-hybrid-ggr:languages"]
    assert [o["id"] for o in card["options"]] == ["elvish", "vedalken"] and card["count"] == 1


def test_vf2_4_srd_species_are_unchanged(catalog):
    res = resolve(_draft([("wizard", 1)], species="half-elf"), catalog)
    assert _lang_ids(res) == {"common", "elvish"} and "species:half-elf:languages" in _lang_cards(res)


def test_vf2_4_a_2014_species_keeps_its_languages_under_2024_and_the_origin_picks_stay(catalog):
    res = resolve(_draft([("wizard", 1)], ruleset="2024", species="tiefling-phb", background="acolyte"), catalog)
    assert {"common", "infernal"} <= _lang_ids(res)


def test_vf2_4_the_frontend_language_names_mirror_the_backend_table():
    """Every language id a sheet can hold has the same display name in `frontend/src/logic/labels.ts` (game content is not translated)."""
    import re
    from catalog import reference_data as ref
    labels = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "logic" / "labels.ts").read_text(encoding="utf-8")
    block = labels.split("export const LANGUAGE_NAMES: Record<string, string> = {", 1)[1].split("};", 1)[0]
    front = {m.group(1) or m.group(2): m.group(3).replace("\\'", "'") for m in
             re.finditer(r'^\s*(?:"([a-z-]+)"|([a-z]+)): "((?:[^"\\]|\\.)*)",\s*$', block, re.M)}
    assert front == ref.LANGUAGE_NAMES


# ---------------------------------------------------------------- VF2.4b ordinary species / background language cards are gated
def _lang_cards_all(res):
    return {c["id"]: c for c in res["choices"] if c["id"].endswith(":languages")}


def _disabled(card):
    return {o["id"] for o in card["options"] if o.get("disabled")}


def _picks(draft, species=None, background=None):
    if species:
        draft["species"]["choices"] = dict(species)
    if background:
        draft["background"]["choices"] = dict(background)
    return draft


def test_vf2_4b_a_known_fixed_language_is_disabled_in_the_background_card(catalog):
    res = resolve(_draft([("wizard", 1)], species="human"), catalog)   # SRD Human knows Common
    bg = _lang_cards_all(res)["background:acolyte:languages"]
    assert _disabled(bg) == {"common"}
    assert next(o for o in bg["options"] if o["id"] == "common")["disabledReason"]
    # PHB Tiefling: Common and Infernal
    res = resolve(_draft([("wizard", 1)], species="tiefling-phb"), catalog)
    assert _disabled(_lang_cards_all(res)["background:acolyte:languages"]) == {"common", "infernal"}


def test_vf2_4b_the_species_card_does_not_offer_what_the_species_gives(catalog):
    res = resolve(_draft([("wizard", 1)], species="half-elf-phb"), catalog)
    card = _lang_cards_all(res)["species:half-elf-phb:languages"]
    assert _disabled(card) == {"common", "elvish"}
    res = resolve(_draft([("wizard", 1)], species="elf-phb", subspecies="elf-phb-high-phb"), catalog)
    assert _disabled(_lang_cards_all(res)["species:elf-phb:subspecies:elf-phb-high-phb:languages"]) == {"common", "elvish"}


def test_vf2_4b_a_stored_duplicate_pick_is_dropped_with_a_pruned_entry(catalog):
    d = _picks(_draft([("wizard", 1)], species="human"), background={"background:acolyte:languages": ["common", "draconic"]})
    res = resolve(d, catalog)
    bg = _lang_cards_all(res)["background:acolyte:languages"]
    assert bg["selected"] == ["draconic"] and bg["status"] == "pending"
    assert [p["choiceId"] for p in res["pruned"]] == ["background:acolyte:languages"]
    assert res["sheet"]["proficiencies"]["languages"] == ["common", "draconic"]


def test_vf2_4b_species_picks_win_against_the_background_and_the_same_language_twice_is_one(catalog):
    d = _picks(_draft([("wizard", 1)], species="human"), species={"species:human:languages": ["draconic"]},
               background={"background:acolyte:languages": ["draconic", "elvish"]})
    res = resolve(d, catalog)
    cards = _lang_cards_all(res)
    assert cards["species:human:languages"]["selected"] == ["draconic"] and cards["species:human:languages"]["status"] == "resolved"
    assert cards["background:acolyte:languages"]["selected"] == ["elvish"] and "draconic" in _disabled(cards["background:acolyte:languages"])
    assert res["sheet"]["proficiencies"]["languages"] == ["common", "draconic", "elvish"]
    # a clean choice stays resolved and unpruned
    ok = resolve(_picks(_draft([("wizard", 1)], species="human"), species={"species:human:languages": ["draconic"]},
                        background={"background:acolyte:languages": ["elvish", "giant"]}), catalog)
    assert not ok["pruned"] and all(c["status"] == "resolved" for c in _lang_cards_all(ok).values())


def test_vf2_4b_the_filler_style_first_enabled_picks_give_distinct_languages(catalog):
    """The T1 finding: 3 picks (Acolyte 2 + Human 1) ended as 2 languages. Choosing the first enabled option of each card in turn
    now gives Common (fixed) plus three distinct languages."""
    d = _draft([("wizard", 1)], species="human-phb")
    for _ in range(4):
        res = resolve(d, catalog)
        for cid, card in _lang_cards_all(res).items():
            if card["status"] == "pending":
                pick = [o["id"] for o in card["options"] if not o.get("disabled")][: card["count"]]
                (d["species"] if card["source"]["kind"] == "species" else d["background"])["choices"][cid] = pick
    res = resolve(d, catalog)
    assert len(res["sheet"]["proficiencies"]["languages"]) == 4 and all(c["status"] == "resolved" for c in _lang_cards_all(res).values())


# ---------------------------------------------------------------- VF2.5 a subspecies' replaced race traits are not listed
def _species_features(res):
    return [f["name"] for f in res["sheet"]["features"] if f["source"]["kind"] == "species"]


def _overwriting_subraces(catalog):
    return {sid: s for sid, s in catalog.subraces.items() if s.get("overwrites_traits")}


def test_vf2_5_the_pairs(catalog):
    pairs = _overwriting_subraces(catalog)
    assert len(pairs) == 33   # 33 official subraces replace at least one race trait (56 replaced trait names)
    assert sum(len(s["overwrites_traits"]) for s in pairs.values()) == 56


def test_vf2_5_every_replaced_race_trait_is_listed_only_as_the_subraces_own(catalog):
    checked = 0
    for sid, sub in _overwriting_subraces(catalog).items():
        race = catalog.races[sub["race"]["index"]]
        res = resolve(_draft([("wizard", 1)], species=race["index"], subspecies=sid), catalog)
        names = _species_features(res)
        own = [t["name"] for t in sub["racial_traits"]]
        race_names = [t["name"] for t in race["traits"]]
        for replaced in sub["overwrites_traits"]:
            if replaced in own:
                # the subspecies' own trait stays, once per trait of that name in the subspecies
                assert names.count(replaced) == own.count(replaced), (sid, replaced, names)
            else:
                assert replaced not in names, (sid, replaced, names)
            checked += 1
        # nothing else of the race is lost
        for name in race_names:
            if name not in sub["overwrites_traits"] and not name.startswith("Skill Proficiency") and name != "Tool Proficiency":
                assert name in names, (sid, name)
    assert checked == 56


def test_vf2_5_draconblood_and_ravenite(catalog):
    for sid, own in (("dragonborn-phb-draconblood-egw", "Forceful Presence"), ("dragonborn-phb-ravenite-egw", "Vengeful Assault")):
        names = _species_features(resolve(_draft([("wizard", 1)], species="dragonborn-phb", subspecies=sid), catalog))
        assert "Damage Resistance" not in names and own in names and names.count("Draconic Ancestry") == 1, (sid, names)
        assert "Breath Weapon" in names
    # the PHB base Dragonborn and its other lineages keep the race's traits
    base = _species_features(resolve(_draft([("wizard", 1)], species="dragonborn-phb"), catalog))
    assert "Damage Resistance" in base and base.count("Draconic Ancestry") == 1


def test_vf2_5_tiefling_legacy_replaces_infernal_legacy(catalog):
    fierna = _species_features(resolve(_draft([("wizard", 1)], species="tiefling-phb", subspecies="tiefling-phb-fierna-mtf"), catalog))
    assert "Infernal Legacy" not in fierna and "Legacy of Phlegethos" in fierna and "Hellish Resistance" in fierna
    asmodeus = _species_features(resolve(_draft([("wizard", 1)], species="tiefling-phb", subspecies="tiefling-phb-asmodeus-mtf"), catalog))
    assert "Infernal Legacy" in asmodeus   # no replacing entry: kept


def test_vf2_5_custom_lineage_variable_trait_darkvision_lists_no_skill_proficiency(catalog):
    def variant_draft(variant):
        d = _draft([("wizard", 1)], species="custom-lineage-tce")
        if variant:
            d["species"]["choices"] = {"species:custom-lineage-tce:variant": [variant]}
        return d
    names = _species_features(resolve(variant_draft("darkvision"), catalog))
    assert "Variable Trait" in names and "Skill Proficiency" not in names, names
    skill = _species_features(resolve(variant_draft("skill-proficiency"), catalog))
    assert "Skill Proficiency" in skill and "Variable Trait" in skill
    # no variant picked yet: both choices are possible, the entry stays until the pick
    assert "Skill Proficiency" in _species_features(resolve(variant_draft(None), catalog))


def test_vf2_5_kobold_variants_that_drop_the_skill_pick_list_no_skill_proficiency(catalog):
    def names(variant):
        d = _draft([("wizard", 1)], species="kobold-mpmm")
        d["species"]["choices"] = {"species:kobold-mpmm:variant": [variant]}
        return _species_features(resolve(d, catalog))
    assert "Skill Proficiency" in names("craftiness")
    assert "Skill Proficiency" not in names("defiance") and "Skill Proficiency" not in names("draconic-sorcery")


# ---------------------------------------------------------------- VF2.6 Mark of Scribing: comprehend languages recharges on a short or long rest
def test_vf2_6_data_only_mark_of_scribing_uses_the_innate_rest_wrapper():
    wrappers = []
    for rec in _races_json()["race"] + _races_json()["subrace"]:
        for entry in rec.get("additionalSpells") or []:
            for level, value in (entry.get("innate") or {}).items():
                if isinstance(value, dict) and "rest" in value:
                    wrappers.append((rec["name"], rec["source"], level))
    assert wrappers == [("Mark of Scribing", "ERLW", "1")]
    rec = next(r for r in _races_json()["subrace"] if r.get("name") == "Mark of Scribing")
    text = " ".join(_plain(e) for e in rec["entries"][1]["entries"])
    assert ("You can also cast comprehend languages once with this trait, and you regain the ability to cast it when you finish "
            "a short or long rest.") in text
    assert "cast the magic mouth spell with this trait, and you regain the ability to cast it when you finish a long rest" in text


def test_vf2_6_comprehend_languages_is_once_per_short_or_long_rest(catalog):
    res = resolve(_draft([("wizard", 5)], species="gnome-phb", subspecies="gnome-phb-mark-of-scribing-erlw"), catalog)
    by_spell = {e["spellId"]: e for e in res["sheet"]["innateSpells"]}
    comprehend = by_spell["comprehend-languages"]
    assert (comprehend["uses"], comprehend["usesMax"], comprehend["recharge"]) == ("1/short or long rest", 1, "short-or-long")
    # Magic Mouth (3rd level): "when you finish a long rest" -> unchanged
    mouth = by_spell["magic-mouth"]
    assert (mouth["uses"], mouth["usesMax"], mouth["recharge"]) == ("1/day", 1, "long")
    assert by_spell["message"]["uses"] == "at-will"


# ---------------------------------------------------------------- VF4.1 SCC Student backgrounds fix the Strixhaven Initiate college
def _backgrounds_json():
    return json.load(open(DATA / "backgrounds.json"))["background"]


def _flat_text(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return " ".join(_flat_text(i) for i in x)
    if isinstance(x, dict):
        return " ".join(_flat_text(v) for v in x.values())
    return ""


_COLLEGES = ("Lorehold", "Prismari", "Quandrix", "Silverquill", "Witherbloom")


def test_vf4_1_data_the_student_backgrounds_name_their_college_in_the_feat_sentence():
    recs = {r["name"]: r for r in _backgrounds_json() if r["source"] == "SCC"}
    for college in _COLLEGES:
        rec = recs[f"{college} Student"]
        assert rec["feats"] == [{"strixhaven initiate|scc": True}]  # the data carries no variant, only the text does
        assert f"You gain the {{@feat Strixhaven Initiate|SCC}} feat and must choose {college} within it." in _flat_text(rec["entries"])


def test_vf4_1_the_fixed_variant_sentences_are_exactly_the_pinned_set():
    """Every background whose text fixes a feat variant ('must choose X within it' / 'must choose X for the feat'):
    the five SCC students and Astral Drifter (AAG; fixed to Cleric in VF6). Nothing else in the data says it."""
    import re
    found = sorted(r["name"] for r in _backgrounds_json()
                   if re.search(r"must choose \w+ (within it|for the feat)", _flat_text(r.get("entries"))))
    assert found == ["Astral Drifter", "Lorehold Student", "Prismari Student", "Quandrix Student", "Silverquill Student",
                     "Witherbloom Student"]


@pytest.mark.parametrize("college", _COLLEGES)
def test_vf4_1_student_background_fixes_the_college_card(catalog, college):
    bid = f"{college.lower()}-student-scc"
    assert catalog.backgrounds[bid]["feat_variant_hints"] == {"strixhaven-initiate-scc": college}
    res = resolve(_draft([("fighter", 1)], ruleset="mixed", background=bid), catalog)
    card = next(c for c in res["choices"] if c["id"] == "feat:strixhaven-initiate-scc:spell-variant")
    assert [o["id"] for o in card["options"]] == [f"{college.lower()}-{n}" for n in (1, 2, 3)]


def test_vf4_1_a_stored_foreign_college_is_not_taken(catalog):
    """The t1-070 finding: a Lorehold Student got Witherbloom spells. A stored Witherbloom pick is now ignored."""
    d = _draft([("fighter", 1)], ruleset="mixed", background="lorehold-student-scc")
    d["background"]["choices"] = {"feat:strixhaven-initiate-scc:spell-variant": ["witherbloom-1"],
                                  "feat:strixhaven-initiate-scc:spell-ability": ["int"]}
    res = resolve(d, catalog)
    card = next(c for c in res["choices"] if c["id"] == "feat:strixhaven-initiate-scc:spell-variant")
    assert card["status"] == "pending"
    names = {e["spellId"] for e in res["sheet"].get("innateSpells", [])}
    assert not names & {"chill-touch", "druidcraft", "spare-the-dying"}
    d["background"]["choices"]["feat:strixhaven-initiate-scc:spell-variant"] = ["lorehold-2"]
    res = resolve(d, catalog)
    known = {s["id"] if isinstance(s, dict) and "id" in s else s.get("spellId") for s in res["sheet"].get("innateSpells", [])}
    assert {"light", "thaumaturgy"} <= known


# ---------------------------------------------------------------- VF4.2 background language pick "other"
_BG_OTHER = {  # background index -> (the language the record's own Languages line names for "other", the sentence)
    "boros-legionnaire-ggr": ("Minotaur", "Choose one of Celestial, Draconic, Goblin, or Minotaur"),
    "golgari-agent-ggr": ("Kraul", "Choose one of Elvish, Giant, or Kraul"),
    "izzet-engineer-ggr": ("Vedalken", "Choose one of Draconic, Goblin, or Vedalken"),
    "selesnya-initiate-ggr": ("Loxodon", "Choose one of Elvish, Loxodon, or Sylvan"),
}


def _language_lines(rec):
    out = []

    def walk(o):
        if isinstance(o, dict):
            if str(o.get("name", "")).startswith("Languages"):
                out.append(_flat_text(o.get("entry")))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(rec["entries"])
    return out


def test_vf4_2_data_exactly_four_backgrounds_carry_other_and_their_text_names_it():
    from catalog.official.common import slug
    found = {}
    for r in _backgrounds_json():
        for e in r.get("languageProficiencies") or []:
            if e.get("other") or "other" in (e.get("choose") or {}).get("from", []):
                found[f"{slug(r['name'])}-{r['source'].lower()}"] = r
    assert sorted(found) == sorted(_BG_OTHER)
    for bid, (name, sentence) in _BG_OTHER.items():
        assert sentence in _language_lines(found[bid]), bid


@pytest.mark.parametrize("bid", sorted(_BG_OTHER))
def test_vf4_2_the_other_option_is_the_named_language(catalog, bid):
    from catalog import reference_data as ref
    name, sentence = _BG_OTHER[bid]
    listed = [n.strip().rstrip(".") for n in sentence.replace("Choose one of ", "").replace(", or ", ", ").replace(" or ", ", ").split(", ")]
    opts = catalog.backgrounds[bid]["language_options"]["from"]["options"]
    assert [o["item"]["name"] for o in opts] == listed and name in listed
    assert "other" not in [o["item"]["index"] for o in opts]
    assert ref.LANGUAGE_NAMES[name.lower()] == name
    d = _draft([("fighter", 1)], ruleset="2014", background=bid)
    card_id = f"background:{bid}:languages"
    d["background"]["choices"] = {card_id: [name.lower()]}
    res = resolve(d, catalog)
    assert name.lower() in res["sheet"]["proficiencies"]["languages"] and "other" not in res["sheet"]["proficiencies"]["languages"]
    card = next(c for c in res["choices"] if c["id"] == card_id)
    assert [o["id"] for o in card["options"]] == [n.lower() for n in listed] and card["status"] == "resolved"


def test_vf4_2_no_background_offers_or_grants_other_as_a_language(catalog):
    """The scan the finding asked for: no catalog background offers or grants the placeholder id."""
    for bid, bg in catalog.backgrounds.items():
        assert "other" not in [x["index"] if isinstance(x, dict) else x for x in bg.get("languages") or []], bid
        opts = ((bg.get("language_options") or {}).get("from") or {}).get("options") or []
        assert "other" not in [o["item"]["index"] for o in opts], bid


def test_vf4_2_the_reference_table_is_the_pinned_set():
    from catalog import reference_data as ref
    assert set(ref.BACKGROUND_OTHER_LANGUAGES) == set(_BG_OTHER)
    for bid, row in ref.BACKGROUND_OTHER_LANGUAGES.items():
        assert row["names"] == [_BG_OTHER[bid][0]] and row["quote"] == _BG_OTHER[bid][1]


# ---------------------------------------------------------------- VF4.3 2014 Paladin: "any simple melee weapon"
_SRD_DIR = pathlib.Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"


def _srd_class_equipment():
    out = []
    for cls in json.load(open(_SRD_DIR / "5e-SRD-Classes.json")):
        for i, env in enumerate(cls.get("starting_equipment_options") or []):
            for opt in env["from"].get("options", []) if env["from"].get("option_set_type") == "options_array" else []:
                nested = opt.get("choice") if opt.get("option_type") == "choice" else None
                if nested:
                    out.append((cls["index"], i, env["desc"], nested["desc"], nested["from"]["equipment_category"]["index"]))
    return out


def test_vf4_3_data_the_phb_paladin_line_says_simple_melee():
    recs = json.load(open(DATA / "class" / "class-paladin.json"))["class"]
    phb = next(r for r in recs if r["name"] == "Paladin" and r["source"] == "PHB")
    assert {"a": [{"item": "javelin|phb", "quantity": 5}], "b": [{"equipmentType": "weaponSimpleMelee"}]} in phb["startingEquipment"]["defaultData"]
    srd = [row for row in _srd_class_equipment() if row[0] == "paladin" and "melee" in row[2]]
    # the SRD record disagrees with its own description: (b) any simple MELEE weapon, category simple-weapons
    assert srd == [("paladin", 1, "(a) five javelins or (b) any simple melee weapon", "any simple weapon", "simple-weapons")]


def test_vf4_3_every_other_srd_weapon_pick_agrees_with_its_description():
    """The audit: the description's melee / simple / martial words match the category in every SRD class except the Paladin."""
    bad = []
    for cid, _, desc, nested_desc, cat in _srd_class_equipment():
        if "weapon" not in nested_desc:
            continue
        want = ("martial" if "martial" in desc else "simple") + ("-melee" if "melee" in desc else "") + "-weapons"
        if cat != want:
            bad.append((cid, desc, cat))
    assert bad == [("paladin", "(a) five javelins or (b) any simple melee weapon", "simple-weapons")]


def test_vf4_3_paladin_pick_offers_only_simple_melee_weapons(catalog):
    res = resolve(_draft([("paladin", 1)], ruleset="2014"), catalog)
    card = next(c for c in res["choices"] if c["id"] == "class:paladin:1:equipment-choice-1")
    assert [o["id"] for o in card["options"]] == ["javelin", "any-simple-melee-weapons"]
    d = _draft([("paladin", 1)], ruleset="2014")
    d["equipment"]["choices"] = {"class:paladin:1:equipment-choice-1": ["any-simple-melee-weapons"]}
    res = resolve(d, catalog)
    sub = next(c for c in res["choices"] if c["id"].startswith("class:paladin:1:equipment-choice-1:"))
    offered = {o["id"] for o in sub["options"]}
    assert "club" in offered and "mace" in offered and "sling" not in offered and "dart" not in offered
    assert all(catalog.items[i]["weapon_range"] == "Melee" and catalog.items[i]["weapon_category"] == "Simple" for i in offered)
    # the Druid and Ranger lines already name the melee category
    druid = next(c for c in resolve(_draft([("druid", 1)], ruleset="2014"), catalog)["choices"] if c["id"] == "class:druid:1:equipment-choice-1")
    assert [o["id"] for o in druid["options"]] == ["scimitar", "any-simple-melee-weapons"]


# ---------------------------------------------------------------- VF4.4 2014 Warlock invocations known (and the SRD Levels audit)
_PHB_INVOCATIONS = [0, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8]
_PHB_METAMAGIC = [0, 0] + [2] * 7 + [3] * 7 + [4] * 4


def _srd_level_rows():
    rows = {}
    for r in json.load(open(_SRD_DIR / "5e-SRD-Levels.json")):
        if "subclass" not in r:
            rows.setdefault(r["class"]["index"], {})[r["level"]] = r
    return rows


def _phb_class(name):
    return next(c for c in json.load(open(DATA / "class" / f"class-{name.lower()}.json"))["class"]
                if c["name"] == name and c["source"] == "PHB")


def _progression(p):
    if isinstance(p, list):
        return p
    out, cur = [], 0
    for level in range(1, 21):
        cur = p.get(str(level), cur)
        out.append(cur)
    return out


def test_vf4_4_data_the_phb_table_and_the_srd_levels_defect():
    warlock = _phb_class("Warlock")
    ofp = next(o for o in warlock["optionalfeatureProgression"] if o["name"] == "Eldritch Invocations")
    assert ofp["progression"] == _PHB_INVOCATIONS
    srd = [_srd_level_rows()["warlock"][lv]["class_specific"]["invocations_known"] for lv in range(1, 21)]
    assert srd == [0, 2, 2, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7, 7, 7, 8, 8, 8]   # the SRD file: L4 and L6 one too many
    sorc = next(o for o in _phb_class("Sorcerer")["optionalfeatureProgression"] if o["name"] == "Metamagic")
    assert _progression(sorc["progression"]) == _PHB_METAMAGIC


def test_vf4_4_the_srd_levels_audit_lists_exactly_three_mismatches():
    """Every counted feature of the SRD Levels file (cantrips known, spells known, invocations known, metamagic known)
    against the PHB class file progressions, every class and level."""
    rows = _srd_level_rows()
    bad = []
    for cid, by_level in rows.items():
        cls = _phb_class(cid.title())
        checks = []
        if "cantripProgression" in cls:
            checks.append(("cantrips_known", "spellcasting", cls["cantripProgression"]))
        if "spellsKnownProgression" in cls:
            checks.append(("spells_known", "spellcasting", cls["spellsKnownProgression"]))
        for o in cls.get("optionalfeatureProgression", []):
            key = {"Eldritch Invocations": "invocations_known", "Metamagic": "metamagic_known"}.get(o["name"])
            if key:
                checks.append((key, "class_specific", _progression(o["progression"])))
        for key, section, table in checks:
            for lv in range(1, 21):
                got = by_level[lv].get(section, {}).get(key)
                if got != table[lv - 1]:
                    bad.append((cid, key, lv, got, table[lv - 1]))
    assert bad == [("sorcerer", "metamagic_known", 16, 4, 3), ("warlock", "invocations_known", 4, 3, 2),
                   ("warlock", "invocations_known", 6, 4, 3)]


def test_vf4_4_the_catalog_levels_follow_the_phb_table(catalog):
    for lv in range(1, 21):
        assert catalog.class_level_row("warlock", lv)["class_specific"]["invocations_known"] == _PHB_INVOCATIONS[lv - 1], lv
        assert catalog.class_level_row("sorcerer", lv)["class_specific"]["metamagic_known"] == _PHB_METAMAGIC[lv - 1], lv


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_vf4_4_the_warlock_invocation_card_counts_follow_the_phb_table(catalog, ruleset):
    for lv in range(2, 21):
        res = resolve(_draft([("warlock", lv)], ruleset=ruleset), catalog)
        card = next(c for c in res["choices"] if c["id"] == "class:warlock:2:invocations:eldritch-invocations")
        assert card["count"] == _PHB_INVOCATIONS[lv - 1], (ruleset, lv)


def test_vf4_4_the_fix_table_equals_the_class_file_progressions():
    from catalog import reference_data as ref
    assert ref.SRD_LEVELS_COUNT_FIXES == {("warlock", "invocations_known"): _PHB_INVOCATIONS, ("sorcerer", "metamagic_known"): _PHB_METAMAGIC}


# ---------------------------------------------------------------- VF6 Astral Drifter Magic Initiate is the Cleric list
def test_vf6_data_astral_drifter_text_fixes_cleric():
    rec = next(r for r in _backgrounds_json() if r["name"] == "Astral Drifter")
    assert rec["feats"] == [{"magic initiate|phb": True}]  # the data carries no variant, only the text does
    assert ("You gain the {@feat Magic Initiate||Magic Initiate feat} from the {@book Player's Handbook|PHB} "
            "and must choose cleric for the feat.") in _flat_text(rec["entries"])


def test_vf6_astral_drifter_card_is_the_cleric_list(catalog):
    assert catalog.backgrounds["astral-drifter-aag"]["feat_variant_hints"] == {"magic-initiate-phb": "Cleric Spells"}
    res = resolve(_draft([("fighter", 1)], ruleset="mixed", background="astral-drifter-aag"), catalog)
    card = next(c for c in res["choices"] if c["id"] == "feat:magic-initiate-phb:spell-variant")
    assert [o["id"] for o in card["options"]] == ["cleric-spells"]


def test_vf6_a_stored_foreign_list_is_ignored_and_cleric_unlocks_the_spell_picks(catalog):
    d = _draft([("fighter", 1)], ruleset="mixed", background="astral-drifter-aag")
    vid = "feat:magic-initiate-phb:spell-variant"
    d["background"]["choices"] = {vid: ["wizard-spells"]}
    res = resolve(d, catalog)
    card = next(c for c in res["choices"] if c["id"] == vid)
    assert card["status"] == "pending"
    assert not [c for c in res["choices"] if ":magic-initiate-phb:spell-choice-" in c["id"]]
    d["background"]["choices"] = {vid: ["cleric-spells"]}
    res = resolve(d, catalog)
    picks = [c for c in res["choices"] if ":magic-initiate-phb:spell-choice-" in c["id"]]
    assert sorted(c["count"] for c in picks) == [1, 2]
    assert "sacred-flame" in {o["id"] for c in picks if c["count"] == 2 for o in c["options"]}
    assert "bless" in {o["id"] for c in picks if c["count"] == 1 for o in c["options"]}
    assert "magic-missile" not in {o["id"] for c in picks for o in c["options"]}


# ---------------------------------------------------------------- VF7.1 languages of 2024 backgrounds under mixed
# The Opus final review: mixed + human-xphb + soldier-xphb (and goliath-mpmm / astral-elf-aag + any XPHB background) had
# NO language at all. Data check (VF7): the MPMM / AAG / FTD / ... species records carry neither `languageProficiencies`
# nor any trait text about languages (the "Common and one other language" sentence exists only in records that also
# carry `languageProficiencies`: Custom Lineage, Tabaxi VGM, Warforged ERLW), so the species side stays silent; the 2024
# BACKGROUND side is a book rule (PHB 2024 "Choose Languages", C8) that follows the background's own edition.
def _species_json():
    return json.load(open(DATA / "races.json"))["race"]


def test_vf7_1_data_no_silent_species_has_a_language_sentence():
    """(a) of the review is empty: of the species without `languageProficiencies` none says 'speak, read, and write'."""
    silent = [r for r in _species_json() if not r.get("languageProficiencies")]
    assert len(silent) == 85  # 70 of them are imported (153 official species in the catalog)
    with_sentence = {(r["name"], r["source"]) for r in silent if "speak, read, and write" in _flat_text(r.get("entries"))}
    assert with_sentence == set()  # (the Plane Shift / Ravnica ones sit in records that carry languageProficiencies or in `subrace`)
    for r in silent:
        if r["source"] in ("MPMM", "AAG", "XPHB", "EFA", "RHW", "VRGR", "FTD", "DMG", "WBtW", "LFL", "DSotDQ", "SCC"):
            assert "language" not in _flat_text(r.get("entries")).replace("languages you knew in life", "").replace(
                "share a language", "").replace("non-thri-kreen languages", "").replace("one language to", "") \
                or r["name"] in ("Skeleton", "Zombie", "Thri-kreen", "Dragonborn (Gem)"), r["name"]


def _langs(res):
    return res["sheet"]["proficiencies"]["languages"]


def _origin_card(res):
    return next((c for c in res["choices"] if c["id"] == "origin:languages"), None)


@pytest.mark.parametrize("species", ["human-xphb", "goliath-mpmm", "astral-elf-aag", "dwarf-xphb"])
def test_vf7_1_mixed_xphb_background_gives_common_and_the_two_picks(catalog, species):
    res = resolve(_draft([("fighter", 1)], ruleset="mixed", species=species, background="soldier-xphb"), catalog)
    assert _langs(res) == ["common"], species
    card = _origin_card(res)
    assert card and card["count"] == 2 and card["status"] == "pending"
    assert "common" not in {o["id"] for o in card["options"]}


def test_vf7_1_mixed_picks_land_on_the_sheet_and_a_duplicate_of_a_known_language_is_pruned(catalog):
    d = _draft([("fighter", 1)], ruleset="mixed", species="goliath-mpmm", background="soldier-xphb")
    d["background"]["choices"] = {"origin:languages": ["dwarvish", "elvish"]}
    assert _langs(resolve(d, catalog)) == ["common", "dwarvish", "elvish"]


def test_vf7_1_mixed_never_double_counts_common(catalog):
    res = resolve(_draft([("fighter", 1)], ruleset="mixed", species="human-phb", background="soldier-xphb"), catalog)
    assert _langs(res).count("common") == 1
    species_card = next(c for c in res["choices"] if c["id"] == "species:human-phb:languages")
    assert next(o for o in species_card["options"] if o["id"] == "common").get("disabled")
    # a species pick that the origin card also picks: the species wins, the origin duplicate is pruned
    d = _draft([("fighter", 1)], ruleset="mixed", species="human-phb", background="soldier-xphb")
    d["species"]["choices"] = {"species:human-phb:languages": ["dwarvish"]}
    d["background"]["choices"] = {"origin:languages": ["dwarvish", "elvish"]}
    res = resolve(d, catalog)
    assert _langs(res) == ["common", "dwarvish", "elvish"]
    assert "origin:languages" in {p["choiceId"] for p in res["pruned"]}


def test_vf7_1_mixed_with_a_2014_background_and_2014_ruleset_stay_as_they_were(catalog):
    """Data-silent: no origin card for a 2014 background under mixed; under 2014 the XPHB background's languages stay
    unmodelled (its ASI is ignored there too: ruleset-2014-background-asi-ignored)."""
    res = resolve(_draft([("fighter", 1)], ruleset="mixed", species="goliath-mpmm", background="soldier-phb"), catalog)
    assert _origin_card(res) is None and _langs(res) == []
    res = resolve(_draft([("fighter", 1)], ruleset="2014", species="human-xphb", background="soldier-xphb"), catalog)
    assert _origin_card(res) is None and _langs(res) == []


def test_vf7_1_2024_is_unchanged(catalog):
    res = resolve(_draft([("fighter", 1)], ruleset="2024", species="human-xphb", background="soldier-xphb"), catalog)
    assert _langs(res) == ["common"] and _origin_card(res)["count"] == 2


# ---------------------------------------------------------------- VF7.2 2014 Circle of the Land "Bonus Cantrip"
# SRD 5.1 (chargen/data/srd/5e-SRD-Features.json "bonus-cantrip"): "When you choose this circle at 2nd level, you learn one
# additional druid cantrip of your choice." PHB (class-druid.json subclassFeature, Land, level 2): "You learn one additional
# druid cantrip of your choice. This cantrip doesn't count against the number of druid cantrips you know."
def test_vf7_2_data_quotes_land_bonus_cantrip():
    srd = next(f for f in json.load(open(DATA.parents[2] / "chargen" / "data" / "srd" / "5e-SRD-Features.json"))
               if f["index"] == "bonus-cantrip")
    assert "you learn one additional druid cantrip of your choice" in " ".join(srd["desc"])
    recs = json.load(open(DATA / "class" / "class-druid.json"))["subclassFeature"]
    phb = next(r for r in recs if r["name"] == "Bonus Cantrip" and r["source"] == "PHB" and r["subclassShortName"] == "Land")
    assert phb["level"] == 2
    assert ("You learn one additional druid cantrip of your choice. This cantrip doesn't count against the number of "
            "druid cantrips you know.") in _flat_text(phb["entries"])


def _cantrip_card(res, cls):
    return next(c for c in res["choices"] if c["id"] == f"class:{cls}:spells-cantrips")


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("level,table", [(2, 2), (3, 2), (4, 3), (7, 3), (10, 4), (20, 4)])
def test_vf7_2_land_druid_cantrip_card_counts_one_more(catalog, ruleset, level, table):
    """PHB Druid table: cantrips known 2 (levels 1-3), 3 (4-9), 4 (10+); the Land druid knows one more from level 2."""
    land = resolve(_draft([("druid", level, "land")], ruleset=ruleset), catalog)
    moon = resolve(_draft([("druid", level, "moon-phb")], ruleset=ruleset), catalog)
    assert _cantrip_card(moon, "druid")["count"] == table
    assert _cantrip_card(land, "druid")["count"] == table + 1


def test_vf7_2_druid_1_and_other_classes_are_unchanged(catalog):
    assert _cantrip_card(resolve(_draft([("druid", 1)]), catalog), "druid")["count"] == 2
    # a Land druid multiclassed into another caster: only the druid card moves
    res = resolve(_draft([("druid", 2, "land"), ("wizard", 1)]), catalog)
    assert _cantrip_card(res, "druid")["count"] == 3 and _cantrip_card(res, "wizard")["count"] == 3


def test_vf7_2_the_extra_pick_reaches_the_sheet_and_2024_land_is_untouched(catalog):
    d = _draft([("druid", 2, "land")], class_choices={0: {"class:druid:spells-cantrips": ["guidance", "druidcraft", "shillelagh"]}})
    res = resolve(d, catalog)
    assert _cantrip_card(res, "druid")["status"] == "resolved"
    assert [c["id"] for c in res["sheet"]["spells"][0]["cantrips"]] == ["guidance", "druidcraft", "shillelagh"] or \
        sorted(c["id"] for c in res["sheet"]["spells"][0]["cantrips"]) == ["druidcraft", "guidance", "shillelagh"]
    res = resolve(_draft([("druid", 3, "land-xphb")], ruleset="2024"), catalog)
    assert _cantrip_card(res, "druid")["count"] == 2  # XPHB: 2 cantrips at level 3, no Bonus Cantrip


def test_vf7_2_a_2014_circle_under_ruleset_2024_keeps_its_old_count(catalog):
    """Documented: the 2014 SRD circle under the 2024 chassis is outside the XPHB tables, so the bump is mixed / 2014 only."""
    res = resolve(_draft([("druid", 3, "land")], ruleset="2024"), catalog)
    assert _cantrip_card(res, "druid")["count"] == 2


# ---------------------------------------------------------------- VF7.3 2014 Ranger Favored Enemy: the language and distinct types
# PHB (class-ranger.json classFeature, Favored Enemy, level 1): "When you gain this feature, you also learn one language of your
# choice that is spoken by your favored enemies, if they speak one at all. You choose one additional favored enemy, as well as an
# associated language, at 6th and 14th level." (the vendored SRD record has no language sentence; the humanoid alternative "select
# two races of humanoid" still says "one language" per gain, so each of the three gains asks for one).
def test_vf7_3_data_quote_phb_favored_enemy_language():
    recs = json.load(open(DATA / "class" / "class-ranger.json"))["classFeature"]
    phb = next(r for r in recs if r["name"] == "Favored Enemy" and r["source"] == "PHB")
    text = _flat_text(phb["entries"])
    assert ("When you gain this feature, you also learn one language of your choice that is spoken by your favored enemies, "
            "if they speak one at all. You choose one additional favored enemy, as well as an associated language, at 6th "
            "and 14th level.") in text
    assert "you can select two races of {@filter humanoid" in text


_FE = {1: "favored-enemy-1-type", 6: "favored-enemy-2-types", 14: "favored-enemy-3-enemies"}


def _fe_cards(res):
    types = {c["id"]: c for c in res["choices"] if ":enemy-type:" in c["id"]}
    langs = {c["id"]: c for c in res["choices"] if ":languages:favored-enemy-" in c["id"]}
    return types, langs


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
@pytest.mark.parametrize("level,gains", [(1, [1]), (5, [1]), (6, [1, 6]), (13, [1, 6]), (14, [1, 6, 14]), (20, [1, 6, 14])])
def test_vf7_3_one_language_card_per_favored_enemy_gain(catalog, ruleset, level, gains):
    res = resolve(_draft([("ranger", level, "hunter")], ruleset=ruleset), catalog)
    _types, langs = _fe_cards(res)
    assert sorted(langs) == sorted(f"class:ranger:{lv}:languages:{_FE[lv]}" for lv in gains)
    for c in langs.values():
        assert c["count"] == 1 and c["status"] == "pending"
        assert len(c["options"]) == 16
        assert c["source"]["kind"] == "class" and c["source"]["id"] == "ranger"


def test_vf7_3_picked_languages_reach_the_sheet_and_gate_each_other(catalog):
    cid = lambda lv: f"class:ranger:{lv}:languages:{_FE[lv]}"  # noqa: E731
    d = _draft([("ranger", 14, "hunter")], class_choices={0: {cid(1): ["draconic"], cid(6): ["sylvan"], cid(14): ["abyssal"]}})
    res = resolve(d, catalog)
    assert {"draconic", "sylvan", "abyssal"} <= set(res["sheet"]["proficiencies"]["languages"])
    # a duplicate (the SRD Human / Acolyte already give some): a later card cannot repeat an earlier pick
    d = _draft([("ranger", 14, "hunter")], class_choices={0: {cid(1): ["draconic"], cid(6): ["draconic"]}})
    res = resolve(d, catalog)
    _types, langs = _fe_cards(res)
    assert next(o for o in langs[cid(6)]["options"] if o["id"] == "draconic")["disabled"]
    assert langs[cid(6)]["selected"] == [] and cid(6) in {p["choiceId"] for p in res["pruned"]}


def test_vf7_3_no_language_card_under_2024_or_for_other_classes(catalog):
    res = resolve(_draft([("ranger", 14, "hunter-xphb")], ruleset="2024"), catalog)
    assert not _fe_cards(res)[1]
    res = resolve(_draft([("fighter", 14)]), catalog)
    assert not _fe_cards(res)[1]


def test_vf7_3_taken_enemy_types_are_disabled_later_and_stored_duplicates_pruned(catalog):
    cid = lambda lv: f"class:ranger:{lv}:enemy-type:{_FE[lv]}"  # noqa: E731
    d = _draft([("ranger", 14, "hunter")], class_choices={0: {cid(1): ["undead"], cid(6): ["undead"], cid(14): ["beasts"]}})
    res = resolve(d, catalog)
    types, _langs = _fe_cards(res)
    assert types[cid(1)]["selected"] == ["undead"]
    six = {o["id"]: o for o in types[cid(6)]["options"]}
    assert six["undead"]["disabled"] and six["undead"]["disabledReason"] == "already taken"
    assert not six["beasts"].get("disabled")
    assert types[cid(6)]["selected"] == [] and types[cid(6)]["status"] == "pending"
    assert cid(6) in {p["choiceId"] for p in res["pruned"]}
    fourteen = {o["id"]: o for o in types[cid(14)]["options"]}
    assert fourteen["undead"]["disabled"] and not fourteen["beasts"].get("disabled")  # level 6 lost its duplicate, beasts is open
    assert types[cid(14)]["selected"] == ["beasts"]
    # humanoids may be taken again: the text lets you pick two races of humanoid
    d = _draft([("ranger", 6, "hunter")], class_choices={0: {cid(1): ["humanoids"], cid(6): ["humanoids"]}})
    types, _ = _fe_cards(resolve(d, catalog))
    assert types[cid(6)]["selected"] == ["humanoids"]
    assert not next(o for o in types[cid(6)]["options"] if o["id"] == "humanoids").get("disabled")


# ---------------------------------------------------------------- VF7.4 prerequisites on: the ASI templates stay cheap
# Spec t2-126-fig19-sor1-mixed (Fighter 19 Rune Knight / Sorcerer 1, seven ASI feats, usePrerequisites.feats on) cost 58-93 ms
# in the review (22 ms with prerequisites off): 8,875 `_feat_prerequisite_unmet_reason` calls and 7,945 message formats per resolve.
# Now the structured prerequisite is parsed once per walk and the reason messages are formatted once per distinct (key, params).
# Measured here (best of 25, warm): 11.9 ms -> 9.6 ms with prerequisites on (6.7 ms off), message formats 1630 -> 265.
def _perf_spec_draft(catalog):
    from tools.chartest.runner import find_spec
    from tools.chartest.spec import resolve_spec
    spec = find_spec("t2-126-fig19-sor1-mixed", catalog)[0]
    draft, _res = resolve_spec(spec, catalog, resolve)
    assert draft["preferences"]["usePrerequisites"]["feats"] is True
    return draft


def test_vf7_4_prerequisites_on_resolve_stays_fast(catalog):
    from perf_helpers import assert_fast, measure
    draft = _perf_spec_draft(catalog)
    resolve(draft, catalog)
    assert_fast(measure(lambda: resolve(draft, catalog), runs=15), "t2-126-fig19-sor1-mixed with prerequisites", limit_ms=40.0)


def test_vf7_4_prerequisite_reasons_are_formatted_once_not_per_option(catalog, monkeypatch):
    """Deterministic guard (no clock): a warm resolve of the spec formats few messages (1630 before the fix, 265 after)."""
    import i18n.messages as messages
    draft = _perf_spec_draft(catalog)
    resolve(draft, catalog)
    calls = []
    real = messages.format_template
    monkeypatch.setattr(messages, "format_template", lambda t, p: calls.append(t) or real(t, p))
    resolve(draft, catalog)
    assert len(calls) < 600, len(calls)


def test_vf7_4_output_is_unchanged_by_the_memo(catalog):
    """Same reasons with the memo cold and warm, and the shared Msg objects still localise per call."""
    from engine import resolve as resolve_mod
    from i18n.messages import localize
    draft = _perf_spec_draft(catalog)
    resolve_mod._PREREQ_MSG_MEMO.clear()
    cold = json.dumps(resolve(draft, catalog), sort_keys=True, default=str)
    warm = json.dumps(resolve(draft, catalog), sort_keys=True, default=str)
    assert cold == warm
    res = resolve(draft, catalog)
    bg = json.dumps(localize(res, "bg"), ensure_ascii=False)
    again = json.dumps(localize(resolve(draft, catalog), "bg"), ensure_ascii=False)
    assert bg == again


# ---------------------------------------------------------------- VF7.5 Unarmed Strike and species natural weapons
# Book rule (PHB p.195 "Unarmed Strike" / PHB 2024 "Unarmed Strike", NOT in the vendored data): an unarmed strike deals bludgeoning
# damage equal to 1 + your Strength modifier and you are proficient with it. The species records pin the "normal" part: "instead of
# the bludgeoning damage normal for an unarmed strike". Natural weapons: the table `reference_data.SPECIES_NATURAL_WEAPONS`,
# one entry per species trait id with the sentence it was read from (the die, type and ability are re-derived from that sentence
# by this test, so the table cannot drift from the data).
def _trait_text(catalog, trait_id):
    return " ".join(catalog.traits[trait_id]["desc"])


def test_vf7_5_natural_weapon_table_matches_the_trait_sentences(catalog):
    from catalog import reference_data as ref
    import re
    assert len(ref.SPECIES_NATURAL_WEAPONS) == 21
    for tid, spec in ref.SPECIES_NATURAL_WEAPONS.items():
        text = _trait_text(catalog, tid)
        assert spec["quote"] in text, tid
        quote = spec["quote"]
        assert re.search(r"\{@damage " + re.escape(spec["die"]) + r"\}", quote), tid
        assert spec["type"] in quote.lower() or tid == "aarakocra-dmg-trait-1" and spec["type"] == "slashing", tid
        want = {"STR": "Strength", "CON": "Constitution"}[spec["ability"]]
        if spec["ability"] == "CON":
            assert "Constitution modifier" in text, tid
        else:
            assert "Constitution modifier, instead of your Strength" not in text, tid
            assert want in text or tid == "aarakocra-dmg-trait-1", tid


def test_vf7_5_every_species_trait_that_says_unarmed_strike_or_natural_weapon_is_in_the_table_or_listed(catalog):
    """Scan of the 153 imported species: a trait whose text says "natural weapon" / "make unarmed strikes" is modelled here or
    explicitly deferred below (with the reason in ARCHITECTURE VF7.5)."""
    from catalog import reference_data as ref
    import re
    deferred = {"dhampir-rhw-trait-3": None}
    hits = set()
    for rid, race in catalog.races.items():
        for ref_ in race.get("traits") or []:
            text = _trait_text(catalog, ref_["index"])
            if re.search(r"natural weapon|make unarmed strikes|unarmed strikes, which deal", text, re.I):
                hits.add(ref_["index"])
    modelled = set(ref.SPECIES_NATURAL_WEAPONS)
    assert hits <= modelled | {"loxodon-ggr-trait-1"}, sorted(hits - modelled)
    assert modelled - hits <= {"dhampir-rhw-trait-3"}, sorted(modelled - hits)


def _attacks(res):
    return res["derived"]["attacks"]


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_vf7_5_everyone_has_an_unarmed_strike_row(catalog, ruleset):
    res = resolve(_draft([("fighter", 5)], ruleset=ruleset, scores={"STR": 16}), catalog)
    (row,) = [a for a in _attacks(res) if a["itemId"] == "unarmed-strike"]
    assert row["name"] == "Unarmed Strike" and row["ability"] == "STR" and row["proficient"] is True
    assert row["attackBonus"] == 3 + 3 and row["damage"] == "1+3" and row["damageType"] == "bludgeoning" and row["range"] == "5"
    assert _attacks(res) == [row]  # no weapons carried


def test_vf7_5_strength_modifier_only_and_gear_rows_come_first(catalog):
    d = _draft([("fighter", 1)], scores={"STR": 8, "DEX": 18}, added=("longsword",))
    rows = _attacks(resolve(d, catalog))
    assert [r["itemId"] for r in rows] == ["longsword", "unarmed-strike"]
    assert rows[-1]["damage"] == "1-1" and rows[-1]["attackBonus"] == -1 + 2  # DEX is never used by a plain unarmed strike


def test_vf7_5_monk_keeps_exactly_one_unarmed_row(catalog):
    for ruleset in ("2014", "2024"):
        rows = [a for a in _attacks(resolve(_draft([("monk", 5)], ruleset=ruleset, scores={"DEX": 16}), catalog)) if "unarmed" in a["itemId"]]
        assert len(rows) == 1 and rows[0]["notes"] == ["Martial Arts"] and rows[0]["ability"] == "DEX"


_NATURAL = [  # (species, class level 5 Fighter, expected row name, die, damage type, ability)
    ("lizardfolk-vgm", "Bite", "1d6", "piercing", "STR"), ("lizardfolk-mpmm", "Bite", "1d6", "slashing", "STR"),
    ("tabaxi-vgm", "Cat's Claws", "1d4", "slashing", "STR"), ("tabaxi-mpmm", "Cat's Claws", "1d6", "slashing", "STR"),
    ("minotaur-mpmm", "Horns", "1d6", "piercing", "STR"), ("minotaur-ggr", "Horns", "1d6", "piercing", "STR"),
    ("tortle-mpmm", "Claws", "1d6", "slashing", "STR"), ("tortle-ttp", "Claws", "1d4", "slashing", "STR"),
    ("aarakocra-eepc", "Talons", "1d4", "slashing", "STR"), ("aarakocra-mpmm", "Talons", "1d6", "slashing", "STR"),
    ("centaur-mpmm", "Hooves", "1d6", "bludgeoning", "STR"), ("satyr-mpmm", "Ram", "1d6", "bludgeoning", "STR"),
    ("gnoll-dmg", "Bite", "1d4", "piercing", "STR"), ("leonin-mot", "Claws", "1d4", "slashing", "STR"),
    ("dhampir-vrgr", "Vampiric Bite", "1d4", "piercing", "CON"),
]


@pytest.mark.parametrize("species,name,die,dtype,ability", _NATURAL)
def test_vf7_5_species_natural_weapon_rows(catalog, species, name, die, dtype, ability):
    scores = {"STR": 16, "CON": 14, "DEX": 10}
    res = resolve(_draft([("fighter", 5)], ruleset="mixed", species=species, scores=scores), catalog)
    rows = {a["name"]: a for a in _attacks(res)}
    assert set(rows) == {"Unarmed Strike", name}, species
    row = rows[name]
    mod = res["derived"]["abilityModifiers"][ability]
    assert row["ability"] == ability and row["proficient"] is True and row["damageType"] == dtype
    assert row["damage"] == f"{die}{mod:+d}" and row["attackBonus"] == mod + 3 and row["range"] == "5"
    assert row["itemId"].startswith("natural-") and row["itemId"] != "unarmed-strike"
    assert rows["Unarmed Strike"]["damageType"] == "bludgeoning" and rows["Unarmed Strike"]["damage"].startswith("1+")


def test_vf7_5_lupin_unarmed_strikes_deal_slashing_and_shifter_longtooth_is_a_variant_row(catalog):
    res = resolve(_draft([("fighter", 5)], ruleset="2024", species="lupin-rhw"), catalog)
    assert [(a["name"], a["damageType"]) for a in _attacks(res)] == [("Unarmed Strike", "slashing")]
    for sp in ("shifter-mpmm", "shifter-efa"):
        d = _draft([("fighter", 5)], ruleset="mixed", species=sp)
        d["species"]["choices"] = {f"species:{sp}:variant": ["longtooth"]}
        rows = {a["name"]: a for a in _attacks(resolve(d, catalog))}
        assert set(rows) == {"Unarmed Strike", "Longtooth"}, sp
        assert rows["Longtooth"]["damage"] == "1d6" and rows["Longtooth"]["damageType"] == "piercing", sp
        assert any("shifted" in n for n in rows["Longtooth"]["notes"])
        d["species"]["choices"] = {f"species:{sp}:variant": ["beasthide"]}
        assert {a["name"] for a in _attacks(resolve(d, catalog))} == {"Unarmed Strike"}


def test_vf7_5_a_unarmed_feat_still_replaces_the_row_and_nothing_is_duplicated(catalog):
    res = resolve(_draft([("fighter", 4)], ruleset="2014", species="tabaxi-vgm",
                         class_choices={0: {"class:fighter:4:asi": ["feat:tavern-brawler-phb"]}}), catalog)
    rows = _attacks(res)
    assert [r["itemId"] for r in rows].count("unarmed-strike") == 1
    assert len({r["itemId"] for r in rows}) == len(rows)


def test_vf7_5_variant_and_lupin_quotes_are_pinned_in_the_records(catalog):
    from catalog import reference_data as ref
    for sid, src in (("shifter-mpmm", "MPMM"), ("shifter-efa", "EFA")):
        text = _flat_text(next(r["entries"] for r in _species_json() if r["name"] == "Shifter" and r["source"] == src))
        assert ref.SPECIES_VARIANT_NATURAL_WEAPONS[(sid, "longtooth")]["quote"] in text, sid
    for tid, spec in ref.SPECIES_UNARMED_TYPE.items():
        assert spec["quote"] in _trait_text(catalog, tid)
