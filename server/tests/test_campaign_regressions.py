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
