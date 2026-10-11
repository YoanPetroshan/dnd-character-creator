"""FE2: the ability-score ceiling of a feat's own increase (docs/superpowers/plans/2026-10-11-feat-effects.md,
4.3). Governing text (5etools `feats.json`, the `ability` records; the feat bodies do not repeat it):

  Resilient (XPHB)  "Increase the chosen ability score by 1, to a maximum of 20."   (the same sentence in PHB)
  Epic Boons (32)   `ability[].max` = 30: "Increase one ability score of your choice by 1, to a maximum of 30."
                    Boon of Terror (FRHoF) is fixed Charisma with the same `max` 30.
  Every other feat  the ordinary 20.

Rule matrix (what applies) x number x source:
  cap of the feat       20 for 2014 and ordinary 2024 feats, 30 for the Epic Boons (catalog `ability_cap`)
  where the feat sits   ASI slot (the per-level walk skips a delta that does not fit), background / species grant
                        (no per-level gate: the delta is clamped, B2), Custom Lineage and Variant Human half-feats
  what the cap touches  the feat's OWN delta only. ASI combos stay capped at 20 (even for a character holding a
                        Boon); species and background ability bonuses are not feats and are not clamped.
  option state          an option whose ability is at the feat's cap is disabled "already at maximum (N)"
                        (B9), reading the level's running scores (ASI) or the pre-feat scores (origin); a stored
                        pick of such an option is dropped through the generic pass with a `pruned` entry
  prerequisite check    a feat's own prerequisite is checked without the delta that was APPLIED, never the raw one
  range problem         the 1-30 range check on the pre-feat scores is unchanged
Mixed / 2014 outputs change on purpose only for the B2 case (a half-feat at 20 used to give 21)."""
import json

import pytest

from catalog import official_source as official
from catalog.loader import load
from engine import asi as asi_mod
from engine.resolve import _feat_prerequisite_problems, resolve

pytestmark = pytest.mark.skipif(not (official.has_official() and official.has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
VH = "species:human-phb:subspecies:human-phb-variant-phb:feat-0"          # Variant Human's free feat card
CL = "species:custom-lineage-tce:feat-0"                                  # Custom Lineage's free feat card


@pytest.fixture(scope="module")
def catalog():
    return load()


def _asi(cls, lvl):
    return f"class:{cls}:{lvl}:asi"


def _draft(classes, base, species=None, ruleset="mixed", background="acolyte", prereqs=False):
    scores = {a: 10 for a in ABS}
    scores.update(base)
    return {"name": "t", "ruleset": ruleset, "sources": [], "classes": classes,
            "background": {"id": background, "choices": {}}, "species": species or {"id": "human-xphb", "choices": {}},
            "abilities": {"method": "manual", "base": scores},
            "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
            "preferences": {"usePrerequisites": {"feats": prereqs}} if prereqs else {}}


def _fighter(level, choices):
    return [{"classId": "fighter", "level": level, "choices": choices}]


def _choice(r, cid):
    return next((c for c in r["choices"] if c["id"] == cid), None)


def _opt(r, cid, opt_id):
    return next(o for o in _choice(r, cid)["options"] if o["id"] == opt_id)


def _scores(r):
    return r["sheet"]["abilities"]


def _boon(catalog, feat, pick, base, ruleset="2024", prereqs=False):
    """Fighter 19 taking `feat` at the level 19 slot with its ability pick; returns (resolved, ability cid)."""
    cid = f"{_asi('fighter', 19)}:feat:{feat}:ability-bonus"
    choices = {_asi("fighter", 19): [f"feat:{feat}"]}
    if pick:
        choices[cid] = [pick]
    return resolve(_draft(_fighter(19, choices), base, ruleset=ruleset, prereqs=prereqs), catalog), cid


# ---------------------------------------------------------------- data


def _raw_feats():
    with open(official.official_dir() / "feats.json", encoding="utf-8") as f:
        return json.load(f)["feat"]


def test_catalog_cap_is_30_for_every_epic_boon_and_20_for_the_rest(catalog):
    raw_boons = {(r["name"], r["source"]) for r in _raw_feats() if r.get("category") == "EB"}
    assert len(raw_boons) == 32
    for index, feat in catalog.feats.items():
        assert feat["ability_cap"] == (30 if feat["category"] == "EB" else 20), index


def test_catalog_cap_follows_the_raw_max_record(catalog):
    with_max = {f"{r['name']}|{r['source']}" for r in _raw_feats() if any("max" in e for e in r.get("ability", []))}
    capped = {f"{f['name']}|{f['source']}" for f in catalog.feats.values() if f["ability_cap"] != 20}
    assert capped == with_max and len(capped) == 32


def test_resilient_text_states_the_cap_of_twenty():
    for r in _raw_feats():
        if r["name"] == "Resilient":
            entries = [e for a in r["ability"] for e in [a["choose"].get("entry", "")] if e]
            assert any("to a maximum of 20" in e for e in entries), r["source"]


def test_asi_math_takes_a_cap_and_defaults_to_twenty():
    assert asi_mod.asi_exceeds_cap([("STR", 1)], {"STR": 20}) is True
    assert asi_mod.asi_exceeds_cap([("STR", 1)], {"STR": 20}, cap=30) is False
    assert asi_mod.asi_exceeds_cap([("STR", 1)], {"STR": 30}, cap=30) is True
    assert asi_mod.clamped_delta("STR", 1, {"STR": 20}) == 0
    assert asi_mod.clamped_delta("STR", 1, {"STR": 19}) == 1
    assert asi_mod.clamped_delta("STR", 2, {"STR": 19}) == 1          # partial room
    assert asi_mod.clamped_delta("STR", 1, {"STR": 25}) == 0          # already above: never lowered
    assert asi_mod.clamped_delta("STR", 1, {"STR": 20}, cap=30) == 1


# ---------------------------------------------------------------- B1: Epic Boons reach 30


def test_boon_of_fortitude_raises_a_strength_of_20_to_21(catalog):
    r, _ = _boon(catalog, "boon-of-fortitude-xphb", "str", {"STR": 20})
    assert _scores(r)["STR"] == 21
    assert "boon-of-fortitude-xphb" in [f["id"] for f in r["sheet"]["feats"]]


def test_boon_goes_up_to_30_and_no_further(catalog):
    r, cid = _boon(catalog, "boon-of-fortitude-xphb", "str", {"STR": 29})
    assert _scores(r)["STR"] == 30
    r, cid = _boon(catalog, "boon-of-fortitude-xphb", "str", {"STR": 30})
    assert _scores(r)["STR"] == 30
    opt = _opt(r, cid, "str")
    assert opt["disabled"] and opt["disabledReason"] == "already at maximum (30)"
    assert not _opt(r, cid, "dex").get("disabled")


def test_boon_option_is_open_at_20_and_a_pick_below_the_cap_is_kept(catalog):
    r, cid = _boon(catalog, "boon-of-fortitude-xphb", None, {"STR": 20, "DEX": 12})
    assert not _opt(r, cid, "str").get("disabled")


def test_boon_of_terror_fixed_charisma_also_reaches_21(catalog):
    r, _ = _boon(catalog, "boon-of-terror-frhof", None, {"CHA": 20})
    assert _scores(r)["CHA"] == 21


def test_boon_at_the_cap_pick_is_pruned(catalog):
    r, cid = _boon(catalog, "boon-of-fortitude-xphb", "str", {"STR": 30})
    entry = next(p for p in r["pruned"] if p["choiceId"] == cid)
    assert "STR is already at maximum (30)" in entry["reason"]
    assert _choice(r, cid)["status"] == "pending"
    assert r["problems"] == []


def test_combos_stay_at_twenty_even_with_a_boon_at_another_level(catalog):
    """The Boon's 30 belongs to the Boon: a +2 ASI combo at 19 is still skipped (and disabled)."""
    choices = {_asi("fighter", 4): ["str-plus-2"], _asi("fighter", 19): ["feat:boon-of-fortitude-xphb"],
               f"{_asi('fighter', 19)}:feat:boon-of-fortitude-xphb:ability-bonus": ["dex"]}
    r = resolve(_draft(_fighter(19, choices), {"STR": 19, "DEX": 10}, ruleset="2024"), catalog)
    assert _scores(r)["STR"] == 19                       # 19 + 2 would be 21: the combo does not apply
    assert _opt(r, _asi("fighter", 4), "str-plus-2")["disabled"]
    assert _scores(r)["DEX"] == 11


# ---------------------------------------------------------------- ASI slot: ordinary feats stay at 20


def test_resilient_xphb_does_nothing_for_a_constitution_of_20(catalog):
    cid = f"{_asi('fighter', 4)}:feat:resilient-xphb:ability-bonus"
    choices = {_asi("fighter", 4): ["feat:resilient-xphb"], cid: ["con"]}
    r = resolve(_draft(_fighter(4, choices), {"CON": 20}, ruleset="2024"), catalog)
    assert _scores(r)["CON"] == 20
    opt = _opt(r, cid, "con")
    assert opt["disabled"] and opt["disabledReason"] == "already at maximum (20)"
    assert not _opt(r, cid, "str").get("disabled")
    assert any(p["choiceId"] == cid for p in r["pruned"])


def test_resilient_option_reads_the_running_score_of_its_own_level(catalog):
    """Fighter 8: CON 18 + a +2 ASI at 4 = 20, so the Resilient taken at 8 has CON closed; at 4 it was open."""
    cid8 = f"{_asi('fighter', 8)}:feat:resilient-xphb:ability-bonus"
    choices = {_asi("fighter", 4): ["con-plus-2"], _asi("fighter", 8): ["feat:resilient-xphb"], cid8: ["con"]}
    r = resolve(_draft(_fighter(8, choices), {"CON": 18}, ruleset="2024"), catalog)
    assert _scores(r)["CON"] == 20
    assert _opt(r, cid8, "con")["disabledReason"] == "already at maximum (20)"
    assert not _opt(r, cid8, "dex").get("disabled")


def test_asi_half_feat_below_the_cap_still_applies(catalog):
    cid = f"{_asi('fighter', 4)}:feat:resilient-xphb:ability-bonus"
    choices = {_asi("fighter", 4): ["feat:resilient-xphb"], cid: ["con"]}
    r = resolve(_draft(_fighter(4, choices), {"CON": 19}, ruleset="2024"), catalog)
    assert _scores(r)["CON"] == 20
    assert not _opt(r, cid, "con").get("disabled")


# ---------------------------------------------------------------- B2: origin half-feats stop at 20


def test_variant_human_half_feat_stops_at_20(catalog):
    """Athlete (PHB): 'Increase your Strength or Dexterity score by 1, to a maximum of 20.' Was 21 (B2)."""
    cid = f"{VH}:feat:athlete-phb:ability-bonus"
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb", "choices": {VH: ["feat:athlete-phb"], cid: ["str"]}}
    r = resolve(_draft(_fighter(1, {}), {"STR": 20}, species=species), catalog)
    assert _scores(r)["STR"] == 20
    assert _opt(r, cid, "str")["disabledReason"] == "already at maximum (20)"
    assert not _opt(r, cid, "dex").get("disabled")
    assert any(p["choiceId"] == cid for p in r["pruned"])


def test_variant_human_half_feat_below_the_cap_still_adds(catalog):
    cid = f"{VH}:feat:athlete-phb:ability-bonus"
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb", "choices": {VH: ["feat:athlete-phb"], cid: ["str"]}}
    r = resolve(_draft(_fighter(1, {}), {"STR": 14}, species=species), catalog)
    assert _scores(r)["STR"] == 15                       # 14 + the feat's +1 (the variant's own +1 picks are not made)
    assert not _opt(r, cid, "str").get("disabled")


def test_custom_lineage_half_feat_stops_at_20(catalog):
    """Custom Lineage grants a feat of your choice; the half-feat still ends at 20 whatever the lineage added."""
    cid = f"{CL}:feat:athlete-phb:ability-bonus"
    species = {"id": "custom-lineage-tce",
               "choices": {"species:custom-lineage-tce:ability-bonus": ["str"], CL: ["feat:athlete-phb"], cid: ["str"]}}
    r = resolve(_draft(_fighter(1, {}), {"STR": 18}, species=species), catalog)
    assert _scores(r)["STR"] == 20                      # 18 + 2 (lineage, not a feat) = 20; the feat adds nothing
    assert _opt(r, cid, "str")["disabledReason"] == "already at maximum (20)"


def test_custom_lineage_lineage_bonus_is_not_clamped(catalog):
    """The cap belongs to the feat: Custom Lineage's own +2 on a 19 still lands (21), as before FE2."""
    species = {"id": "custom-lineage-tce", "choices": {"species:custom-lineage-tce:ability-bonus": ["str"]}}
    r = resolve(_draft(_fighter(1, {}), {"STR": 19}, species=species), catalog)
    assert _scores(r)["STR"] == 21


def test_background_feat_without_an_increase_changes_nothing(catalog):
    r = resolve(_draft(_fighter(1, {}), {"STR": 20, "CON": 20}, background="criminal-xphb", ruleset="2024"), catalog)
    assert "alert" in r["sheet"]["grantedFeats"]
    assert _scores(r)["STR"] == 20 and _scores(r)["CON"] == 20


def test_species_origin_feat_with_no_increase_changes_nothing(catalog):
    cid = "species:human-xphb:feat-0"
    species = {"id": "human-xphb", "choices": {cid: ["feat:alert-xphb"]}}
    r = resolve(_draft(_fighter(1, {}), {"DEX": 20}, species=species, ruleset="2024"), catalog)
    assert _scores(r)["DEX"] == 20


# ---------------------------------------------------------------- origin clamp, with an increase on a background feat


def test_a_background_granted_half_feat_is_clamped(catalog):
    """No shipped background grants a feat with an increase, so Criminal (XPHB) is re-pointed at Actor (XPHB,
    fixed +1 Charisma) in a copy of the catalog."""
    import copy
    cat = copy.copy(catalog)
    cat.backgrounds = copy.deepcopy(catalog.backgrounds)
    cat.backgrounds["criminal-xphb"]["feat_refs"] = ["actor-xphb"]
    cat.backgrounds["criminal-xphb"]["feats"] = ["actor"]
    r = resolve(_draft(_fighter(1, {}), {"CHA": 20}, background="criminal-xphb", ruleset="2024"), cat)
    assert "actor" in r["sheet"]["grantedFeats"]
    assert _scores(r)["CHA"] == 20                    # Actor's fixed +1 Charisma does not pass 20
    r = resolve(_draft(_fighter(1, {}), {"CHA": 12}, background="criminal-xphb", ruleset="2024"), cat)
    assert _scores(r)["CHA"] == 13


# ---------------------------------------------------------------- prerequisite of the feat itself


def test_prerequisite_uses_the_applied_delta_not_the_raw_one():
    """Synthetic feat: 'Charisma 20' prerequisite with a fixed +1 Charisma that was clamped away at 20. Subtracting
    the raw +1 would test 19 < 20 and report a prerequisite that the character does meet."""
    feat = {"index": "x-test", "name": "X", "prerequisite": [{"ability": [{"cha": 20}]}],
            "ability_bonuses": [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 1}]}
    scores = {a: 10 for a in ABS}
    scores["CHA"] = 20
    raw = _feat_prerequisite_problems([feat], 5, scores, True)
    assert [p["id"] for p in raw] == ["feat-prerequisite-unmet-x-test"]          # the old false positive
    applied = _feat_prerequisite_problems([feat], 5, scores, True, None, {"feat:x-test": []})
    assert applied == []
    applied_one = _feat_prerequisite_problems([feat], 5, {**scores, "CHA": 21}, True, None, {"feat:x-test": [("CHA", 1)]})
    assert applied_one == []


def test_applied_origin_increase_is_still_subtracted_for_its_own_prerequisite(catalog):
    """Actor (XPHB): prerequisite Charisma 13, fixed +1 Charisma. With the preference on, the card offers it at
    Charisma 13 and the applied +1 (to 14) is not what satisfies the prerequisite: no problem is reported."""
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb", "choices": {VH: ["feat:actor-xphb"]}}
    r = resolve(_draft(_fighter(4, {}), {"CHA": 13}, species=species, prereqs=True), catalog)
    assert "actor-xphb" in r["sheet"]["grantedFeats"] or "actor" in r["sheet"]["grantedFeats"]
    assert _scores(r)["CHA"] == 14
    assert not any(p["id"] == "feat-prerequisite-unmet-actor-xphb" for p in r["problems"])


def test_cap_skipped_asi_feat_does_not_report_a_false_prerequisite(catalog):
    """An ASI feat whose fixed +1 was skipped at the cap must not have that +1 subtracted again for its own check."""
    choices = {_asi("fighter", 4): ["feat:actor-xphb"]}
    r = resolve(_draft(_fighter(4, choices), {"CHA": 20}, ruleset="2024", prereqs=True), catalog)
    assert _scores(r)["CHA"] == 20
    assert not any(p["id"] == "feat-prerequisite-unmet-actor-xphb" for p in r["problems"])


# ---------------------------------------------------------------- range check and identity


def test_range_problem_is_unchanged(catalog):
    r = resolve(_draft(_fighter(1, {}), {"STR": 31}), catalog)
    assert any(p["id"] == "ability-out-of-range-STR" for p in r["problems"])
    r = resolve(_draft(_fighter(1, {}), {"STR": 30}), catalog)
    assert not any(p["id"].startswith("ability-out-of-range") for p in r["problems"])


def test_a_feat_less_draft_is_identical(catalog):
    r = resolve(_draft(_fighter(8, {_asi("fighter", 4): ["str-plus-2"]}), {"STR": 15}), catalog)
    assert _scores(r)["STR"] == 17
