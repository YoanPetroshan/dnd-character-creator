"""RP21 (X2, open question 5): repeat-instance renumbering of the XPHB Eldritch Invocations (decision D3 = renumber).

Rule (XPHB, Agonizing Blast / Eldritch Spear / Repelling Blast / Lessons of the First Ones are "Repeatable"; the
instances are the engine's `<id>`, `<id>~2`, `<id>~3`): "Each time you do so, choose a different eligible cantrip" /
"a different Origin feat". The instances of one invocation are interchangeable, so when the BASE instance is removed
from the stored picks the stored picks FOLLOW the instance (`<id>~2` becomes `<id>`, `~3` becomes `~2`), and the
dependent picks keyed by the instance (target cantrip `class:warlock:invocation:<inst>:cantrip`, the Lessons feat
`...:feat` and its cascade `...:feat:<index>:...`) move with it. Before RP21 the repeat was dropped ("take Agonizing
Blast first") together with its target.

Rule matrix (rows = stored shape, all ruleset 2024, Warlock):
  base removed, ~2 stays              ~2 -> base, its target -> base target; the old base target is gone
  base removed, ~2 and ~3 hold picks  ~2 -> base, ~3 -> ~2, picks follow, ~3 card gone
  a middle instance removed           the gap is closed the same way ([AGON, AGON~3] -> [AGON, AGON~2])
  no gap                              nothing changes (identity)
  several invocations                 each base is renumbered on its own, list order and other picks untouched
  Lessons (feat + cascade)            the feat pick and every key under its cid move
  level-down                          an instance beyond the count is dropped, never renumbered into range
  late gate (cantrips / structure)    a pick the gate removes is NOT a stored removal: no renumbering
  mixed / 2014 / SRD-only catalog     untouched (the instances exist only under 2024)
  Eldritch Adept (feat-held)          no instances (RP20 pool has none): nothing renumbers, `~k` ids stay invalid
  the draft is never mutated; the result is stable when the client echoes the renumbered selection back.
"""
import copy

import pytest

from catalog.loader import load
from c7c_helpers import (  # noqa: F401
    AGON, CANT, CHAIN, EB, INV, LESSONS, MI, REPEL, SPEAR, TOME, TTD, _card, _dependent_ids, _draft, _l, _pruned, _res,
    _resource, _srd_only, needs_data, tcid, time_resolve,
)
from engine import class_choices_2024
from engine.resolve import resolve

PS, CT = "poison-spray-xphb", "chill-touch-xphb"
CANTS = [EB, TTD, PS]  # a Warlock 5 knows three cantrips; all deal damage (three Agonizing Blast instances)


@pytest.fixture(scope="module")
def catalog():
    return load()


def _t(inst, k=None):
    return tcid(inst if k is None else f"{inst}~{k}", "cantrip")


def _sel(res, cid):
    card = _card(res, cid)
    return None if card is None else card["selected"]


# ---- the pure helper ----------------------------------------------------------------------------------------------


def _rc(catalog, level=5):
    return {"cls_id": "warlock", "cls": catalog.classes["warlock"], "level": level}


@needs_data
@pytest.mark.parametrize("stored,expected", [
    ([AGON + "~2"], [AGON]),
    ([AGON + "~2", AGON + "~3"], [AGON, AGON + "~2"]),
    ([AGON + "~3", AGON + "~2"], [AGON + "~2", AGON]),  # list order stays, ids follow
    ([AGON, AGON + "~3"], [AGON, AGON + "~2"]),
    ([AGON + "~3"], [AGON]),
    ([AGON, AGON + "~2"], [AGON, AGON + "~2"]),
    ([AGON, AGON + "~2", AGON + "~3"], [AGON, AGON + "~2", AGON + "~3"]),
    ([TOME, AGON + "~2", CHAIN, SPEAR + "~2", SPEAR + "~3"], [TOME, AGON, CHAIN, SPEAR, SPEAR + "~2"]),  # per base
    ([AGON + "~2", AGON + "~2"], [AGON, AGON]),  # a duplicated stored id is mapped like any other (the card dedupes it)
    ([TOME, CHAIN], [TOME, CHAIN]),
    ([], []),
])
def test_renumbering_of_the_stored_invocation_list(catalog, stored, expected):
    cc = {INV: stored}
    out = class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog), "2024", cc)
    assert out[INV] == expected
    assert cc[INV] == stored  # the input is never mutated


@needs_data
def test_instances_beyond_the_count_are_not_renumbered_into_range(catalog):
    # Warlock 2 has count 3: `~4` is not an offered option, so it is neither renumbered nor does it count as an instance
    cc = {INV: [AGON + "~2", AGON + "~4"]}
    out = class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog, 2), "2024", cc)
    assert out[INV] == [AGON, AGON + "~4"]


@needs_data
def test_helper_is_identity_outside_2024_and_without_a_card(catalog):
    cc = {INV: [AGON + "~2"], _t(AGON, 2): [TTD]}
    assert class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog), "mixed", cc) is cc
    assert class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog), "2014", cc) is cc
    assert class_choices_2024.renumber_invocation_instances(_srd_only(catalog), _rc(catalog), "2024", cc) is cc
    rc = {"cls_id": "wizard", "cls": catalog.classes["wizard"], "level": 5}
    assert class_choices_2024.renumber_invocation_instances(catalog, rc, "2024", cc) is cc
    assert class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog), "2024", {INV: "garbage"})[INV] == "garbage"


@needs_data
def test_dependent_keys_move_and_stale_keys_are_replaced(catalog):
    cc = {INV: [AGON + "~2", AGON + "~3"], _t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS], "class:warlock:spells-cantrips": CANTS}
    out = class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog), "2024", cc)
    assert out[_t(AGON)] == [TTD] and out[_t(AGON, 2)] == [PS] and _t(AGON, 3) not in out
    assert out["class:warlock:spells-cantrips"] == CANTS
    # the old base had a target, the old ~2 none: the base card starts empty (picks follow the instance)
    cc2 = {INV: [AGON + "~2"], _t(AGON): [EB]}
    assert _t(AGON) not in class_choices_2024.renumber_invocation_instances(catalog, _rc(catalog), "2024", cc2)


# ---- Agonizing Blast / Eldritch Spear / Repelling Blast through resolve() -----------------------------------------


@needs_data
def test_base_removed_the_second_instance_becomes_the_base_with_its_target(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD]}
    r = _res(catalog, 5, [AGON + "~2"], CANTS, extra=extra)
    assert _sel(r, INV) == [AGON]
    assert _dependent_ids(r) == [_t(AGON)]
    assert _sel(r, _t(AGON)) == [TTD]  # ~2's pick, not the removed base's Eldritch Blast
    assert _resource(r, "Agonizing Blast")["details"]["spell"] == TTD
    assert _resource(r, "Agonizing Blast (2)") is None
    assert [p for p in r["pruned"] if p["choiceId"] in (INV, _t(AGON, 2))] == []
    assert not [p for p in r["problems"] if "over-selected" in p["id"] or "invocation" in p["id"]]


@needs_data
def test_base_removed_while_the_second_and_third_hold_targets(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS]}
    r = _res(catalog, 5, [AGON + "~2", AGON + "~3", TOME], CANTS, extra=extra)
    assert _sel(r, INV) == [AGON, AGON + "~2", TOME]
    assert _dependent_ids(r)[:2] == [_t(AGON), _t(AGON, 2)] and _card(r, _t(AGON, 3)) is None
    assert _sel(r, _t(AGON)) == [TTD] and _sel(r, _t(AGON, 2)) == [PS]
    assert _resource(r, "Agonizing Blast")["details"]["spell"] == TTD
    assert _resource(r, "Agonizing Blast (2)")["details"]["spell"] == PS
    assert _resource(r, "Agonizing Blast (3)") is None


@needs_data
def test_a_middle_instance_removed_closes_the_gap(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS]}
    r = _res(catalog, 5, [AGON, AGON + "~3"], CANTS, extra=extra)
    assert _sel(r, INV) == [AGON, AGON + "~2"]
    assert _sel(r, _t(AGON)) == [EB] and _sel(r, _t(AGON, 2)) == [PS] and _card(r, _t(AGON, 3)) is None


@needs_data
def test_no_gap_nothing_moves(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD]}
    r = _res(catalog, 5, [AGON, AGON + "~2"], CANTS, extra=extra)
    assert _sel(r, INV) == [AGON, AGON + "~2"] and _sel(r, _t(AGON)) == [EB] and _sel(r, _t(AGON, 2)) == [TTD]


@needs_data
@pytest.mark.parametrize("inv", [SPEAR, REPEL])
def test_spear_and_repelling_blast_follow_too(catalog, inv):
    second = PS if inv == SPEAR else CT  # Spear: damage, range 10+ (Poison Spray 30 ft); Repelling: attack roll (Chill Touch)
    extra = {_t(inv): [EB], _t(inv, 2): [second]}
    r = _res(catalog, 5, [inv + "~2"], [EB, second, MI], extra=extra)
    assert _sel(r, INV) == [inv] and _sel(r, _t(inv)) == [second] and _card(r, _t(inv, 2)) is None


@needs_data
def test_each_base_is_renumbered_on_its_own_and_other_picks_keep_their_place(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD], _t(SPEAR): [EB], _t(SPEAR, 2): [PS]}
    r = _res(catalog, 5, [TOME, AGON + "~2", CHAIN, SPEAR + "~2"], CANTS, extra=extra)
    assert _sel(r, INV) == [TOME, AGON, CHAIN, SPEAR]
    assert _sel(r, _t(AGON)) == [TTD] and _sel(r, _t(SPEAR)) == [PS]


@needs_data
def test_a_removed_base_with_no_stored_target_leaves_the_card_open(catalog):
    r = _res(catalog, 5, [AGON + "~2"], CANTS, extra={_t(AGON): [EB]})
    assert _sel(r, INV) == [AGON]
    card = _card(r, _t(AGON))
    assert card["selected"] == [] and card["status"] == "pending"  # the removed base's Eldritch Blast does not stay


@needs_data
def test_the_result_is_stable_when_the_client_echoes_it_back(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS]}
    r1 = _res(catalog, 5, [AGON + "~2", AGON + "~3"], CANTS, extra=extra)
    echo = {_t(AGON): _sel(r1, _t(AGON)), _t(AGON, 2): _sel(r1, _t(AGON, 2))}
    r2 = _res(catalog, 5, _sel(r1, INV), CANTS, extra=echo)
    assert _sel(r2, INV) == _sel(r1, INV)
    assert [(c["id"], c["selected"]) for c in r2["choices"] if c["id"].startswith("class:warlock:invocation:")] == \
        [(c["id"], c["selected"]) for c in r1["choices"] if c["id"].startswith("class:warlock:invocation:")]


@needs_data
def test_the_draft_is_not_mutated(catalog):
    d = _draft(5, [AGON + "~2", AGON + "~3"], CANTS, extra={_t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS]})
    before = copy.deepcopy(d)
    resolve(d, catalog)
    assert d == before


# ---- level-down / late gate ----------------------------------------------------------------------------------------


@needs_data
def test_level_down_drops_the_instance_beyond_the_count_without_renumbering(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS]}
    extra[_t(AGON, 4)] = [PS]
    r = _res(catalog, 2, [AGON, AGON + "~2", AGON + "~4"], [EB, TTD], extra=extra)  # Warlock 2: count 3, `~4` is not offered
    assert _sel(r, INV) == [AGON, AGON + "~2"]
    assert _sel(r, _t(AGON)) == [EB] and _sel(r, _t(AGON, 2)) == [TTD]
    assert _card(r, _t(AGON, 3)) is None and _card(r, _t(AGON, 4)) is None


@needs_data
def test_level_down_and_base_removed_together(catalog):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD], _t(AGON, 3): [PS]}
    extra[_t(AGON, 4)] = [PS]
    r = _res(catalog, 2, [AGON + "~2", AGON + "~4"], [EB, TTD], extra=extra)  # ~4 is not offered at count 3
    assert _sel(r, INV) == [AGON]
    assert _sel(r, _t(AGON)) == [TTD] and _dependent_ids(r) == [_t(AGON)]


@needs_data
def test_level_1_has_no_repeat_instances_at_all(catalog):
    r = _res(catalog, 1, [AGON + "~2"], CANTS, extra={_t(AGON, 2): [TTD]})
    assert _sel(r, INV) == [] and _dependent_ids(r) == []


@needs_data
def test_a_gate_drop_is_not_a_stored_removal(catalog):
    # the late gate (needs k eligible cantrips) removes ~2: the base keeps its pick, nothing is renumbered
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD]}
    r = _res(catalog, 5, [AGON, AGON + "~2"], [EB, MI], extra=extra)
    assert _sel(r, INV) == [AGON] and _sel(r, _t(AGON)) == [EB] and _card(r, _t(AGON, 2)) is None
    # the last damaging cantrip goes: the whole chain falls and the targets are pruned, nothing survives as the base
    r2 = _res(catalog, 5, [AGON, AGON + "~2"], [MI], extra=extra)
    assert _sel(r2, INV) == [] and _dependent_ids(r2) == []


@needs_data
def test_the_target_stays_unique_after_renumbering(catalog):
    # ~2 and ~3 stored the same cantrip: after the move the base wins it, the next instance keeps it disabled
    extra = {_t(AGON, 2): [TTD], _t(AGON, 3): [TTD]}
    r = _res(catalog, 5, [AGON + "~2", AGON + "~3"], CANTS, extra=extra)
    assert _sel(r, _t(AGON)) == [TTD] and _sel(r, _t(AGON, 2)) == []


# ---- Lessons of the First Ones (the feat pick and its cascade) ------------------------------------------------------


def _lessons_cascade(catalog, level, inst, feat, picks):
    """The cid of the first cascade card of the Lessons instance `inst` after it took `feat`."""
    r = _res(catalog, level, [_l()], extra={tcid(_l(), "feat"): [feat]})
    return next(c["id"] for c in r["choices"] if c["id"].startswith(tcid(_l(), "feat") + ":")).replace(_l(), inst)


@needs_data
def test_lessons_follow_with_the_feat_and_its_cascade(catalog):
    skilled = tcid(_l(2), "feat")
    cascade2 = _lessons_cascade(catalog, 5, _l(2), "feat:skilled-xphb", None)
    assert cascade2.startswith(skilled + ":")
    skills = ["skill-stealth", "skill-arcana", "skill-history"]
    extra = {tcid(_l(), "feat"): ["feat:alert-xphb"], skilled: ["feat:skilled-xphb"], cascade2: skills,
             tcid(_l(3), "feat"): ["feat:magic-initiate-xphb"]}
    r = _res(catalog, 5, [_l(2), _l(3)], CANTS, extra=extra)
    assert _sel(r, INV) == [_l(), _l(2)]
    assert _sel(r, tcid(_l(), "feat")) == ["feat:skilled-xphb"]  # the old base's Alert is gone
    new_cascade = cascade2.replace(_l(2), _l())
    assert _sel(r, new_cascade) == skills
    assert {"skill-stealth", "skill-arcana", "skill-history"} <= set(r["sheet"]["proficiencies"]["skills"])
    assert _sel(r, tcid(_l(2), "feat")) == ["feat:magic-initiate-xphb"]
    ids = [f["id"] for f in r["sheet"]["feats"]]
    assert "skilled-xphb" in ids and "magic-initiate-xphb" in ids and "alert-xphb" not in ids
    assert _card(r, tcid(_l(3), "feat")) is None


@needs_data
def test_lessons_without_a_gap_are_untouched(catalog):
    extra = {tcid(_l(), "feat"): ["feat:alert-xphb"], tcid(_l(2), "feat"): ["feat:skilled-xphb"]}
    r = _res(catalog, 5, [_l(), _l(2)], CANTS, extra=extra)
    assert _sel(r, tcid(_l(), "feat")) == ["feat:alert-xphb"] and _sel(r, tcid(_l(2), "feat")) == ["feat:skilled-xphb"]


# ---- mixed / 2014 / SRD-only catalog / Eldritch Adept ---------------------------------------------------------------


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_are_untouched(catalog, ruleset):
    extra = {_t(AGON): [EB], _t(AGON, 2): [TTD]}
    d = _draft(5, [AGON + "~2"], CANTS, extra=extra, ruleset=ruleset, bg="acolyte")
    before = copy.deepcopy(d)
    r = resolve(d, catalog)
    assert d == before
    assert _card(r, INV) is None and _dependent_ids(r) == []


@needs_data
def test_srd_only_catalog_is_untouched(catalog):
    r = _res(_srd_only(catalog), 5, [AGON + "~2"], CANTS, extra={_t(AGON, 2): [TTD]})
    assert _card(r, INV) is None and _dependent_ids(r) == []


@needs_data
def test_eldritch_adept_has_no_instances_so_nothing_renumbers(catalog):
    # RP20: the feat takes ONE invocation, its pool has no `~k` option; a stored `~2` is invalid and is never moved
    ea = "eldritch-adept-tce"
    ea_inv = f"class:warlock:4:asi:feat:{ea}:invocation"
    ch = {"class:warlock:4:asi": [f"feat:{ea}"], f"class:warlock:4:asi:feat:{ea}:invocation-ability": ["cha"],
          ea_inv: [AGON + "~2"], f"{ea_inv}:{AGON}:cantrip": [PS]}
    r = _res(catalog, 5, [CHAIN], CANTS, extra=ch)
    card = _card(r, ea_inv)
    assert AGON + "~2" not in [o["id"] for o in card["options"]] and card["selected"] == []
    assert _card(r, f"{ea_inv}:{AGON}:cantrip") is None  # the feat holds no Agonizing Blast, so no card, no move
    ch[ea_inv] = [AGON]
    r2 = _res(catalog, 5, [CHAIN], CANTS, extra=ch)
    assert _card(r2, f"{ea_inv}:{AGON}:cantrip")["selected"] == [PS]


# ---- timing -----------------------------------------------------------------------------------------------------------


@needs_data
def test_warlock_20_with_ten_invocations_and_a_removed_base_stays_fast(catalog):
    picks = [TOME, CHAIN, AGON + "~2", AGON + "~3", SPEAR + "~2", REPEL, _l(2), _l(3), X_MIND, X_ARMOR]
    extra = {_t(AGON, 2): [TTD], _t(AGON, 3): [PS], _t(SPEAR, 2): [EB], _t(REPEL): [CT]}
    d = _draft(20, picks, [EB, TTD, PS, CT], extra=extra)
    r = resolve(d, catalog)
    assert _sel(r, INV)[:4] == [TOME, CHAIN, AGON, AGON + "~2"]
    assert time_resolve(d, catalog, 20) < 50


X_MIND, X_ARMOR = "opt-eldritch-mind-xphb", "opt-armor-of-shadows-xphb"
