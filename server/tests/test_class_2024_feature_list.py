"""C5: under ruleset 2024 the class-feature rows of sheet.features (and so every export)
come from the XPHB per-level lists (`catalog.class_2024_level_features`) instead of the
SRD refs; the SRD choice-bearing features keep their picks through
`sheet_features.SRD_TO_XPHB_FEATURE`. 2014 and mixed are unchanged; subclass rows are
unchanged.

Matrix: ruleset (2024 / 2014 / mixed) x data (real XPHB lists / SRD-only catalog) x level
boundary (Fighter 1 -> 2, Bard 1 -> 2 -> 3, Fighter 8 -> 9) x multiclass x choice family
(weapon mastery, fighting style, expertise, metamagic, invocations, favored enemy; unmapped:
pact boon, natural explorer, which keep their SRD row)."""
from perf_helpers import assert_fast
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import sheet_features
from engine.resolve import resolve

needs_classes = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="5etools data not available")

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue",
           "sorcerer", "warlock", "wizard"]


def _draft(classes):
    return {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {k: 10 for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }


def _cls(cid, level, subclass=None, choices=None):
    e = {"classId": cid, "level": level, "choices": choices or {}}
    if subclass:
        e["subclassId"] = subclass
    return e


@pytest.fixture(scope="module")
def catalog():
    return load()


def _d(classes, ruleset="2024"):
    d = _draft(classes)
    d["ruleset"] = ruleset
    d["sources"] = ["srd", "xphb"]
    return d


def _rows(res, kind="class", cls=None):
    return [f for f in res["sheet"]["features"]
            if f["source"]["kind"] == kind and (cls is None or f["source"]["id"] == cls)]


def _names(res, cls=None):
    return [f["name"] for f in _rows(res, cls=cls)]


@needs_classes
def test_fighter_2_has_tactical_mind_under_2024_only(catalog):
    n24 = _names(resolve(_d([_cls("fighter", 2)]), catalog))
    assert "Tactical Mind" in n24 and "Action Surge" in n24 and "Second Wind" in n24
    for rs in ("2014", "mixed"):
        n = _names(resolve(_d([_cls("fighter", 2)], rs), catalog))
        assert "Tactical Mind" not in n and "Action Surge (1 use)" in n


@needs_classes
def test_default_ruleset_is_unchanged(catalog):
    d = _draft([_cls("fighter", 2)])
    assert "Tactical Mind" not in _names(resolve(d, catalog))


@needs_classes
def test_fighter_1_weapon_mastery_and_fighting_style_carry_their_picks(catalog):
    d = _d([_cls("fighter", 1, choices={
        "class:fighter:weapon-mastery": ["longsword", "crossbow-light", "handaxe"],
        "class:fighter:1:fighting-style": ["feat:defense-xphb"]})])
    res = resolve(d, catalog)
    by = {f["name"]: f for f in _rows(res)}
    assert by["Weapon Mastery"]["choice"] == ["Longsword (Sap)", "Crossbow, light (Slow)", "Handaxe (Vex)"]
    assert by["Fighting Style"]["choice"] == ["Defense"]
    assert "choice" not in by["Second Wind"]
    assert [f["name"] for f in _rows(res)] == ["Fighting Style", "Second Wind", "Weapon Mastery"]


@needs_classes
def test_barbarian_1_lists_the_xphb_features(catalog):
    n = _names(resolve(_d([_cls("barbarian", 1)]), catalog))
    assert n == ["Rage", "Unarmored Defense", "Weapon Mastery"]


@needs_classes
def test_placeholders_and_asi_rows_stay_out(catalog):
    res = resolve(_d([_cls("fighter", 20, "champion")]), catalog)
    names = _names(res)
    assert not any(n.startswith(("Ability Score", "Epic Boon", "Subclass Feature")) or n.endswith("Subclass") for n in names)
    assert names.count("Indomitable") == 3 and names.count("Action Surge") == 2


@needs_classes
def test_level_gating_at_boundaries(catalog):
    f1, f2 = (_rows(resolve(_d([_cls("fighter", n)]), catalog)) for n in (1, 2))
    assert {f["name"] for f in f2} - {f["name"] for f in f1} == {"Action Surge", "Tactical Mind"}
    assert max(f["level"] for f in f1) == 1
    f8, f9 = (_names(resolve(_d([_cls("fighter", n)]), catalog)) for n in (8, 9))
    assert "Indomitable" not in f8 and "Tactical Master" not in f8
    assert "Indomitable" in f9 and "Tactical Master" in f9
    levels = [f["level"] for f in _rows(resolve(_d([_cls("fighter", 20)]), catalog))]
    assert levels == sorted(levels)


@needs_classes
def test_multiclass_each_class_uses_its_own_list(catalog):
    res = resolve(_d([_cls("fighter", 2), _cls("wizard", 2)]), catalog)
    assert _names(res, "fighter") == ["Fighting Style", "Second Wind", "Weapon Mastery", "Action Surge", "Tactical Mind"]
    assert _names(res, "wizard") == ["Spellcasting", "Ritual Adept", "Arcane Recovery", "Scholar"]
    assert [f["source"]["id"] for f in _rows(res)] == ["fighter"] * 5 + ["wizard"] * 4


@needs_classes
def test_subclass_rows_are_unchanged(catalog):
    d = _d([_cls("fighter", 3, "champion")])
    sub24 = [f for f in resolve(d, catalog)["sheet"]["features"] if f["source"]["kind"] == "subclass"]
    d["ruleset"] = "mixed"
    submixed = [f for f in resolve(d, catalog)["sheet"]["features"] if f["source"]["kind"] == "subclass"]
    assert sub24 == submixed and sub24[0]["name"] == "Improved Critical"


@needs_classes
def test_champion_additional_fighting_style_keeps_its_pick(catalog):
    d = _d([_cls("fighter", 10, "champion", {
        "class:fighter:1:fighting-style": ["feat:defense-xphb"],
        "class:fighter:10:fighting-style": ["feat:archery-xphb"]})])
    res = resolve(d, catalog)
    assert next(f for f in _rows(res) if f["name"] == "Fighting Style")["choice"] == ["Defense"]
    sub = next(f for f in _rows(res, "subclass") if f["name"] == "Additional Fighting Style")
    assert sub["choice"] == ["Archery"]


@needs_classes
def test_expertise_metamagic_invocations_favored_enemy_attach_by_ordinal(catalog):
    profs = {"class:bard:1:prof-choice-0": ["skill-stealth", "skill-persuasion", "skill-performance"]}  # 5 proficient skills with Acolyte
    res = resolve(_d([_cls("bard", 10, choices=profs)]), catalog)
    exp = [f for f in _rows(res) if f["name"] == "Expertise"]
    assert [f["level"] for f in exp] == [2, 9]  # XPHB levels, SRD cards at 3 and 10
    assert all(f.get("choice") is None for f in exp)  # nothing picked yet
    picks, taken = {}, set()  # 2024: no Expertise card may repeat a skill, so the picks are disjoint
    for c in (c for c in res["choices"] if "expertise-choice" in c["id"]):
        picks[c["id"]] = [o["id"] for o in c["options"] if not o.get("disabled") and o["id"] not in taken][:c["count"]]
        taken.update(picks[c["id"]])
    d = _d([_cls("bard", 10, choices={**profs, **picks})])
    exp = [f for f in _rows(resolve(d, catalog)) if f["name"] == "Expertise"]
    assert all(f.get("choice") for f in exp)


@needs_classes
def test_unmapped_choice_features_keep_their_srd_row(catalog):
    # C7a: under 2024 the Pacts are invocations, so the SRD Pact Boon card is gone; an SRD-only catalog keeps it.
    res = resolve(_d([_cls("warlock", 3)]), catalog)
    assert not [c for c in res["choices"] if c["id"].endswith(":pact-boon")]
    assert "Eldritch Invocations" in _names(res) and "Pact Magic" in _names(res)
    bare_wl = copy.copy(catalog)
    bare_wl.features = {k: v for k, v in catalog.features.items() if not k.endswith("-xphb")}
    bare_wl.class_2024_records = {}
    bare_wl.class_2024_level_features = {}
    res = resolve(_d([_cls("warlock", 3)]), bare_wl)
    picks = {c["id"]: [c["options"][0]["id"]] for c in res["choices"] if c["id"].endswith(":pact-boon")}
    assert picks
    res = resolve(_d([_cls("warlock", 3, choices=picks)]), bare_wl)
    pb = next(f for f in _rows(res) if f["name"] == "Pact Boon")
    assert pb["level"] == 3 and pb["choice"]
    # C6b-1: the SRD Ranger cards are gone under 2024 (Deft Explorer / R4 replace them), so there
    # is no terrain or enemy pick to attach; the SRD fallback row remains for an SRD-only catalog.
    res = resolve(_d([_cls("ranger", 1)]), catalog)
    assert not [c for c in res["choices"] if ":terrain-type:" in c["id"] or ":enemy-type:" in c["id"]]
    bare = copy.copy(catalog)
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    res = resolve(_d([_cls("ranger", 1)]), bare)
    picks = {c["id"]: [c["options"][0]["id"]] for c in res["choices"] if ":terrain-type:" in c["id"] or ":enemy-type:" in c["id"]}
    assert picks


def _autofill(catalog, cls, level):
    """Pick the first enabled options of every feature-attached card, twice (gates)."""
    picks: dict = {}
    for _ in range(3):
        res = resolve(_d([_cls(cls, level, choices=picks)]), catalog)
        for c in res["choices"]:
            cid = c["id"]
            if c["source"]["kind"] != "class" or c["selected"] or c.get("pending") is False and c.get("granted"):
                continue
            if any(k in cid for k in (":feature:", ":expertise-choice:", ":enemy-type:", ":terrain-type:", ":invocations:",
                                      ":fighting-style", ":weapon-mastery")):
                free = [o["id"] for o in c["options"] if not o.get("disabled")]
                if free:
                    picks[cid] = free[:c["count"]]
    return picks, resolve(_d([_cls(cls, level, choices=picks)]), catalog)


@needs_classes
@pytest.mark.parametrize("cls", CLASSES)
def test_every_choice_bearing_feature_keeps_its_choice_under_2024(catalog, cls):
    _picks, res = _autofill(catalog, cls, 20)
    shown = {c for f in res["sheet"]["features"] for c in f.get("choice", [])}
    checked = 0
    for c in res["choices"]:
        cid = c["id"]
        if c["source"]["kind"] != "class" or not any(
                k in cid for k in (":feature:", ":expertise-choice:", ":enemy-type:", ":terrain-type:",
                                   ":invocations:", ":fighting-style", ":weapon-mastery")):
            continue
        labels = {o["id"]: o["label"] for o in c["options"]}
        for sel in list(c["selected"]):
            label = labels.get(sel, sel)
            assert label in shown or label.split(": ", 1)[-1] in shown, (cid, label)
            checked += 1
    # Classes with a feature-attached card at all must have exercised the check.
    expected = {"fighter", "paladin", "ranger", "barbarian", "rogue", "bard", "sorcerer", "warlock"}
    if cls in expected:
        assert checked > 0


def test_srd_only_catalog_falls_back_to_srd_features(catalog):
    bare = copy.copy(catalog)
    bare.class_2024_level_features = {}
    res = resolve(_d([_cls("fighter", 2)]), bare)
    assert _names(res) == ["Fighting Style", "Second Wind", "Action Surge (1 use)"]
    assert "Tactical Mind" not in _names(res)


def test_mapping_table_only_names_real_srd_ids_and_xphb_names(catalog):
    for (cls, srd_id), (name, ordinal) in sheet_features.SRD_TO_XPHB_FEATURE.items():
        assert srd_id in catalog.features and catalog.features[srd_id]["class"]["index"] == cls
        if catalog.class_2024_level_features:
            xnames = [catalog.features[i]["name"] for lvl in sorted(catalog.class_2024_level_features[cls])
                      for i in catalog.class_2024_level_features[cls][lvl]]
            assert xnames.count(name) > ordinal, (cls, srd_id)
    for srd_id in (*sheet_features.SRD_CHOICE_FEATURES_WITHOUT_XPHB, *sheet_features.SRD_CHOICE_FEATURES_REPLACED_2024):
        assert srd_id in catalog.features


def test_every_srd_class_level_choice_feature_is_mapped_or_listed_unmapped(catalog):
    mapped = {k[1] for k in sheet_features.SRD_TO_XPHB_FEATURE}
    covered = (mapped | set(sheet_features.SRD_CHOICE_FEATURES_WITHOUT_XPHB)
               | set(sheet_features.SRD_CHOICE_FEATURES_REPLACED_2024))
    for i, f in catalog.features.items():
        fs = f.get("feature_specific") or {}
        if i.startswith("xphb-") or f.get("subclass") or not fs:
            continue
        assert i in covered, f"{i} carries a choice but is neither mapped nor listed as unmapped"


@needs_classes
def test_exports_follow_the_xphb_list(catalog):
    from export_fields import extra_blocks
    from markdown_export import to_markdown
    res = resolve(_d([_cls("fighter", 2)]), catalog)
    bullets = [t for k, t in extra_blocks(res) if k == "bullet"]
    assert any(b.startswith("Tactical Mind (ниво 2)") for b in bullets)
    assert "Tactical Mind" in to_markdown(res)
    res14 = resolve(_d([_cls("fighter", 2)], "2014"), catalog)
    assert "Tactical Mind" not in to_markdown(res14)


@needs_classes
def test_resolve_timing_fighter_and_wizard_20(catalog):
    for cls in ("fighter", "wizard"):
        d = _d([_cls(cls, 20)])
        resolve(d, catalog)
        laps = []
        for _ in range(20):
            t_run = time.perf_counter()
            resolve(d, catalog)
            laps.append(time.perf_counter() - t_run)
        assert_fast(laps)
