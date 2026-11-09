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
