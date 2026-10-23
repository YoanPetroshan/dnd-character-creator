"""C7c-3: Lessons of the First Ones (decision E7) under ruleset 2024 (XPHB).

XPHB text: "You have received knowledge from an elder entity of the multiverse, allowing you to gain one Origin feat of
your choice. Repeatable. You can gain this invocation more than once. Each time you do so, choose a different Origin
feat." Level 2 prerequisite; instance k needs instance k-1 (E4).

Rule matrix (text -> engine):
  card      class:warlock:invocation:<instance id>:feat, one per selected instance, options `feat:<index>` of category
            O offered for the sources / ruleset; disabled: held by the background / species / an earlier pick ("already
            taken", the S2 name map), chosen by another Lessons instance ("already chosen for Lessons of the First
            Ones", also for repeatable feats: "a different Origin feat").
  order     resolved in the F1 walk at (Warlock class index, level 2): the LATER pick of a duplicate pair is the one
            skipped (problem feat-duplicate-...); a Lessons pick before an ASI pick of a higher level wins, an earlier
            class's ASI pick beats a later class's Lessons.
  effects   sheet.feats entry origin "invocation", level 2; the feat's own choices cascade under the pick's origin
            (Skilled picks, Magic Initiate variant and spells); removing the invocation (or the level) prunes the pick.
Matrix: instance x duplicate source (background / other instance / ASI / other class) x cascade (Skilled, Magic
Initiate) x stored pick validity x level-down x ruleset x SRD-only x timing."""
import io

import pytest

from catalog.loader import load
from c7c_helpers import (  # noqa: F401
    AGON, BLADE, BLADE_W, CANT, CHAIN, EB, FB, INV, KNOWN, LESSONS, LONGSWORD, MI, REPEL, SPEAR, THIRST, TOME, TOME_C, TOME_R,
    TTD, X, _card, _dependent_ids, _draft, _l, _opt, _problem_ids, _pruned, _res, _resource, _srd_only, needs_data, tcid,
    time_resolve,
)
from engine import class_choices_2024
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


# ---- Lessons of the First Ones ---------------------------------------------------------------------------------------


@needs_data
def test_lessons_card_offers_origin_feats_only(catalog):
    r = _res(catalog, 2, [_l()])
    card = _card(r, tcid(_l(), "feat"))
    assert card["count"] == 1 and card["source"]["kind"] == "class"
    ids = {o["id"] for o in card["options"]}
    assert {"feat:alert-xphb", "feat:magic-initiate-xphb", "feat:skilled-xphb", "feat:tough-xphb"} <= ids
    assert all(catalog.feats[i[len("feat:"):]]["category"] == "O" for i in ids)
    assert "feat:grappler-xphb" not in ids
    assert [c["id"] for c in _res(catalog, 2, [_l(), _l(2)])["choices"] if c["id"].endswith(":feat")] \
        == [tcid(_l(), "feat"), tcid(_l(2), "feat")]  # one card per selected instance


@needs_data
def test_lessons_feat_lands_on_the_sheet_with_origin_invocation(catalog):
    r = _res(catalog, 2, [_l()], extra={tcid(_l(), "feat"): ["feat:alert-xphb"]})
    feat = next(f for f in r["sheet"]["feats"] if f["id"] == "alert-xphb")
    assert feat["origin"] == "invocation" and feat["level"] == 2
    assert "alert-xphb" in r["sheet"]["grantedFeats"]
    assert _card(r, tcid(_l(), "feat"))["status"] == "resolved"


@needs_data
def test_lessons_feat_cascades_its_own_choices(catalog):
    r = _res(catalog, 2, [_l()], extra={tcid(_l(), "feat"): ["feat:skilled-xphb"]})
    cascade = [c for c in r["choices"] if c["id"].startswith(tcid(_l(), "feat") + ":")]
    assert len(cascade) == 1 and cascade[0]["count"] == 3 and cascade[0]["source"]["kind"] == "feat"
    picks = {cascade[0]["id"]: ["skill-stealth", "skill-arcana", "skill-history"]}
    r2 = _res(catalog, 2, [_l()], extra={tcid(_l(), "feat"): ["feat:skilled-xphb"], **picks})
    skills = r2["sheet"]["proficiencies"]["skills"]
    assert {"skill-stealth", "skill-arcana", "skill-history"} <= set(skills)
    assert next(f for f in r2["sheet"]["feats"] if f["id"] == "skilled-xphb")["choice"]


@needs_data
def test_lessons_magic_initiate_cascades_the_spell_cards(catalog):
    feat = {tcid(_l(), "feat"): ["feat:magic-initiate-xphb"]}
    r = _res(catalog, 2, [_l()], extra=feat)
    variant = next(c for c in r["choices"] if c["id"].endswith(":spell-variant") and c["id"].startswith("class:warlock:invocation:"))
    assert variant["source"]["kind"] == "feat"
    prefix = variant["id"][: -len(":spell-variant")]
    assert prefix == f"{tcid(_l(), 'feat')}:magic-initiate-xphb"  # card cid + feat index (the plan's origin shape)
    picks = {**feat, variant["id"]: ["cleric-spells"], prefix + ":spell-ability": ["cha"]}
    r2 = _res(catalog, 2, [_l()], extra=picks)
    spell_cards = [c for c in r2["choices"] if c["id"].startswith(prefix + ":spell-choice-")]
    assert sorted(c["count"] for c in spell_cards) == [1, 2]
    for card in spell_cards:
        picks[card["id"]] = [o["id"] for o in card["options"] if not o.get("disabled")][: card["count"]]
    r3 = _res(catalog, 2, [_l()], extra=picks)
    innate = [e for e in r3["sheet"]["innateSpells"] if e.get("featId") == "magic-initiate-xphb"]
    assert len(innate) == 3 and {e["uses"] for e in innate} == {"at-will", "1/day"}
    # the invocation goes: the whole cascade goes with it, as stale picks
    r4 = _res(catalog, 2, [CHAIN], extra=picks)
    assert not [e for e in r4["sheet"]["innateSpells"] if e.get("featId") == "magic-initiate-xphb"]
    assert _pruned(r4, variant["id"])


@needs_data
def test_a_second_instance_cannot_take_the_same_feat(catalog):
    extra = {tcid(_l(), "feat"): ["feat:alert-xphb"], tcid(_l(2), "feat"): ["feat:alert-xphb"]}
    r = _res(catalog, 2, [_l(), _l(2)], extra=extra)
    second = _card(r, tcid(_l(2), "feat"))
    assert "already chosen for Lessons of the First Ones" in _opt(second, "feat:alert-xphb")["disabledReason"]
    assert second["selected"] == []
    assert [f["id"] for f in r["sheet"]["feats"]].count("alert-xphb") == 1
    # a repeatable feat (Magic Initiate) is still a duplicate between two Lessons ("a different Origin feat")
    extra2 = {tcid(_l(), "feat"): ["feat:magic-initiate-xphb"], tcid(_l(2), "feat"): ["feat:magic-initiate-xphb"]}
    r2 = _res(catalog, 2, [_l(), _l(2)], extra=extra2)
    assert _card(r2, tcid(_l(2), "feat"))["selected"] == []
    # the first instance cannot take what the second one holds
    extra3 = {tcid(_l(2), "feat"): ["feat:alert-xphb"]}
    r3 = _res(catalog, 2, [_l(), _l(2)], extra=extra3)
    assert _opt(_card(r3, tcid(_l(), "feat")), "feat:alert-xphb")["disabled"]


@needs_data
def test_a_feat_from_the_background_is_already_taken(catalog):
    r = _res(catalog, 2, [_l()], bg="criminal-xphb", extra={tcid(_l(), "feat"): ["feat:alert-xphb"]})
    card = _card(r, tcid(_l(), "feat"))
    assert "already taken" in _opt(card, "feat:alert-xphb")["disabledReason"]
    assert card["selected"] == []
    assert [f["id"] for f in r["sheet"]["feats"]].count("alert-xphb") == 1


@needs_data
def test_a_repeatable_background_feat_may_be_taken_again_by_lessons(catalog):
    r = _res(catalog, 2, [_l()], bg="acolyte-xphb", extra={tcid(_l(), "feat"): ["feat:magic-initiate-xphb"]})  # Acolyte: Magic Initiate (Cleric)
    assert not _opt(_card(r, tcid(_l(), "feat")), "feat:magic-initiate-xphb").get("disabled")
    assert [f["origin"] for f in r["sheet"]["feats"] if f["id"] == "magic-initiate-xphb"] == ["background", "invocation"]


@needs_data
def test_lessons_pick_is_pruned_with_its_invocation(catalog):
    stored = {tcid(_l(), "feat"): ["feat:alert-xphb"]}
    r = _res(catalog, 2, [CHAIN], extra=stored)
    assert _card(r, tcid(_l(), "feat")) is None
    assert "no longer applies" in _pruned(r, tcid(_l(), "feat"))
    assert "alert-xphb" not in [f["id"] for f in r["sheet"]["feats"]]
    # level-down: Lessons needs Warlock level 2
    r1 = _res(catalog, 1, [_l()], extra=stored)
    assert "alert-xphb" not in [f["id"] for f in r1["sheet"]["feats"]] and _card(r1, tcid(_l(), "feat")) is None


@needs_data
def test_a_repeat_instance_without_the_base_instance_becomes_the_base(catalog):
    # RP21 (open question 5, D3): the stored picks follow the instance; this used to drop the repeat and its feat
    r = _res(catalog, 2, [_l(2)], extra={tcid(_l(2), "feat"): ["feat:alert-xphb"]})
    assert _card(r, tcid(_l(2), "feat")) is None
    assert _card(r, INV)["selected"] == [_l()]
    assert _card(r, tcid(_l(), "feat"))["selected"] == ["feat:alert-xphb"]
    assert "alert-xphb" in [f["id"] for f in r["sheet"]["feats"]]


@needs_data
def test_a_non_origin_feat_stored_at_a_lessons_card_is_ignored(catalog):
    r = _res(catalog, 2, [_l()], extra={tcid(_l(), "feat"): ["feat:grappler-xphb"]})
    assert _card(r, tcid(_l(), "feat"))["selected"] == []
    assert "grappler-xphb" not in [f["id"] for f in r["sheet"]["feats"]]


@needs_data
def test_order_an_earlier_lessons_pick_beats_a_later_asi_pick(catalog):
    """F1 order: Lessons (Warlock level 2) resolves before the level 4 ASI, so the ASI pick is the duplicate."""
    extra = {tcid(_l(), "feat"): ["feat:alert-xphb"], "class:warlock:4:asi": ["feat:alert-xphb"]}
    r = _res(catalog, 4, [_l()], extra=extra)
    feats = [(f["id"], f["origin"]) for f in r["sheet"]["feats"] if f["id"] == "alert-xphb"]
    assert feats == [("alert-xphb", "invocation")]
    assert any(i.startswith("feat-duplicate-alert-xphb-class:warlock:4:asi") for i in _problem_ids(r))
    asi = _card(r, "class:warlock:4:asi")
    assert _opt(asi, "feat:alert-xphb")["disabled"]


@needs_data
def test_order_an_earlier_class_asi_pick_beats_a_later_lessons_pick(catalog):
    """Fighter is class index 0: its level 4 ASI resolves before the Warlock's Lessons (index 1)."""
    fighter = {"classId": "fighter", "level": 4, "choices": {"class:fighter:4:asi": ["feat:alert-xphb"]}}
    r = _res(catalog, 2, [_l()], extra={tcid(_l(), "feat"): ["feat:alert-xphb"]}, classes_before=[fighter])
    feats = [(f["id"], f["origin"]) for f in r["sheet"]["feats"] if f["id"] == "alert-xphb"]
    assert feats == [("alert-xphb", "asi")]
    assert any(i.startswith("feat-duplicate-alert-xphb-class:warlock:invocation:") for i in _problem_ids(r))


# ---- ruleset isolation, degrade, timing ----------------------------------------------------------------------------------


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_lessons_outside_ruleset_2024(catalog, ruleset):
    r = _res(catalog, 5, [_l()], [EB, MI], extra={tcid(_l(), "feat"): ["feat:alert-xphb"]}, ruleset=ruleset, bg="acolyte")
    assert _dependent_ids(r) == []
    assert not [f for f in r["sheet"]["feats"] if f["origin"] == "invocation"]


@needs_data
def test_srd_only_catalog_degrades(catalog):
    r = _res(_srd_only(catalog), 5, [_l()], [EB, MI], extra={tcid(_l(), "feat"): ["feat:alert-xphb"]})
    assert _dependent_ids(r) == []


@needs_data
def test_timing_warlock_20_with_tome_and_lessons_and_big_classes(catalog):
    picks = [TOME, BLADE, THIRST, AGON, f"{AGON}~2", SPEAR, REPEL, _l(), _l(2), X.format("devils-sight")]
    extra = {
        TOME_C: [FB, "light-xphb", "guidance-xphb"], TOME_R: ["find-familiar-xphb", "detect-magic-xphb"], BLADE_W: ["longsword"],
        tcid(AGON, "cantrip"): [EB], tcid(f"{AGON}~2", "cantrip"): [FB], tcid(SPEAR, "cantrip"): [EB],
        tcid(REPEL, "cantrip"): [EB], tcid(_l(), "feat"): ["feat:alert-xphb"], tcid(_l(2), "feat"): ["feat:tough-xphb"],
    }
    d = _draft(20, picks, [EB, MI, "mage-hand-xphb", "chill-touch-xphb"], extra=extra, added=LONGSWORD)
    r = resolve(d, catalog)
    assert _card(r, INV)["status"] == "resolved" and len(_dependent_ids(r)) >= 9
    assert time_resolve(d, catalog) < 50
    for cls in ("fighter", "wizard"):
        for rs in ("mixed", "2024"):
            dd = {"ruleset": rs, "sources": [], "species": {"id": "human-xphb"}, "background": {"id": "soldier-xphb"},
                  "abilities": {"method": "manual", "base": {a: 14 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
                  "equipment": {"choices": {}, "added": [], "skipped": False},
                  "classes": [{"classId": cls, "level": 20, "choices": {}}]}
            assert time_resolve(dd, catalog) < 50
