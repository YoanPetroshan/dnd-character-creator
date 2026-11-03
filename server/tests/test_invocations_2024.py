"""C7a: 2024 Eldritch Invocation card, counts, prerequisites, Pact as an invocation (XPHB).

XPHB text (Warlock, Eldritch Invocations):
  "You gain one invocation of your choice, such as Pact of the Tome." ... "If an invocation has a
  prerequisite, you must meet it to learn that invocation. For example, if an invocation requires you to be
  a level 5+ Warlock, you can select the invocation once you reach Warlock level 5." ... "You can't replace an
  invocation if it's a prerequisite for another invocation that you have." ... "You can't pick the same
  invocation more than once unless its description says otherwise."
  Agonizing Blast: "Choose one of your known Warlock cantrips that deals damage." Repelling Blast: "...that
  requires an attack roll." Repeatable: "Each time you do so, choose a different eligible cantrip."
  Count: the Invocations column of the Warlock table [1,3,3,3,5,5,6,6,7,7,7,8,8,8,9,9,9,10,10,10].

Matrix: ruleset (2024 / mixed / 2014) x Warlock level (1, 2, 5, 12, 15, 20) x prerequisite kind (none, level,
invocation, damaging cantrip, attack-roll cantrip) x repeat instances (~2, ~3 need the previous one) x fixed-point
pruning (Pact of the Blade -> Thirsting Blade -> Devouring Blade) x level-down count x SRD cards skipped under
2024 x sheet.features row x SRD-only catalog x helpers (strip ~k) x timing."""
from perf_helpers import assert_fast
import copy
import time

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import class_choices_2024, features
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

INV = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
CANT = "class:warlock:spells-cantrips"
BLADE, CHAIN, TOME = "opt-pact-of-the-blade-xphb", "opt-pact-of-the-chain-xphb", "opt-pact-of-the-tome-xphb"
AGON, REPEL, SPEAR = "opt-agonizing-blast-xphb", "opt-repelling-blast-xphb", "opt-eldritch-spear-xphb"
THIRST, DEVOUR, WITCH = "opt-thirsting-blade-xphb", "opt-devouring-blade-xphb", "opt-witch-sight-xphb"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(level, choices, ruleset="2024"):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 16}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": "warlock", "level": level, "choices": choices}],
    }


def _res(catalog, level, picks=None, cantrips=None, ruleset="2024", extra=None):
    ch = dict(extra or {})
    if picks is not None:
        ch[INV] = picks
    if cantrips is not None:
        ch[CANT] = cantrips
    return resolve(_draft(level, ch, ruleset), catalog)


def _card(res, cid=INV):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _pruned(res):
    return " | ".join(p["reason"] for p in res["pruned"] if p["choiceId"] == INV)


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith(("xphb-", "opt-")) or k.startswith("opt-") and not k.endswith("-xphb")}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare


@needs_data
def test_level_1_card_and_srd_cards_replaced(catalog):
    r = _res(catalog, 1)
    card = _card(r)
    assert card["count"] == 1 and card["status"] == "pending"
    enabled = sorted(o["id"] for o in card["options"] if not o.get("disabled"))
    assert enabled == sorted(["opt-armor-of-shadows-xphb", "opt-eldritch-mind-xphb", BLADE, CHAIN, TOME])
    assert _opt(card, AGON)["disabledReason"] == "requires warlock level 2"
    assert not [c for c in r["choices"] if ":invocations:eldritch-invocations" in c["id"] or c["id"].endswith("pact-boon")]
    r3 = _res(catalog, 3)
    assert not [c for c in r3["choices"] if c["id"].endswith(":pact-boon")]


@needs_data
def test_counts_follow_table(catalog):
    for lvl, n in [(1, 1), (2, 3), (5, 5), (7, 6), (12, 8), (15, 9), (18, 10), (20, 10)]:
        assert _card(_res(catalog, lvl))["count"] == n


@needs_data
def test_options_28_plus_repeat_instances(catalog):
    card = _card(_res(catalog, 5))
    ids = [o["id"] for o in card["options"]]
    base = [i for i in ids if "~" not in i]
    assert len(base) == 28
    for rep in (AGON, REPEL, SPEAR, "opt-lessons-of-the-first-ones-xphb"):
        assert [f"{rep}~{k}" in ids for k in (2, 3, 4, 5)] == [True] * 4
        assert f"{rep}~6" not in ids
    assert f"{BLADE}~2" not in ids
    assert _opt(card, AGON + "~2")["label"] == "Agonizing Blast (2)"
    assert ids.index(AGON + "~2") == ids.index(AGON) + 1  # instances follow their base


@needs_data
def test_damage_cantrip_prerequisite(catalog):
    for cants, ok in [(None, False), (["minor-illusion-xphb"], False), (["eldritch-blast-xphb"], True),
                      (["toll-the-dead-xphb"], True)]:
        opt = _opt(_card(_res(catalog, 2, cantrips=cants)), AGON)
        assert bool(opt.get("disabled")) is (not ok)
    assert "deals damage" in _opt(_card(_res(catalog, 2)), AGON)["disabledReason"]
    r = _res(catalog, 2, picks=[AGON, TOME], cantrips=["eldritch-blast-xphb"])
    assert AGON in _card(r)["selected"]
    r = _res(catalog, 2, picks=[AGON, TOME], cantrips=["minor-illusion-xphb"])
    assert _card(r)["selected"] == [TOME] and "Agonizing Blast" in _pruned(r)


@needs_data
def test_attack_roll_cantrip_prerequisite(catalog):
    opt = _opt(_card(_res(catalog, 2, cantrips=["toll-the-dead-xphb"])), REPEL)
    assert opt["disabled"] and "attack roll" in opt["disabledReason"]
    assert not _opt(_card(_res(catalog, 2, cantrips=["eldritch-blast-xphb"])), REPEL).get("disabled")
    assert not _opt(_card(_res(catalog, 2, cantrips=["toll-the-dead-xphb"])), AGON).get("disabled")


@needs_data
def test_pact_chain_and_fixed_point_pruning(catalog):
    r = _res(catalog, 5, picks=[BLADE, THIRST, TOME])
    assert _card(r)["selected"] == [BLADE, THIRST, TOME] and not _pruned(r)
    r = _res(catalog, 5, picks=[THIRST, TOME])
    assert _card(r)["selected"] == [TOME]
    assert "Thirsting Blade" in _pruned(r)
    assert _opt(_card(r), THIRST)["disabledReason"] == "requires Pact of the Blade"
    r = _res(catalog, 12, picks=[DEVOUR, THIRST, TOME, CHAIN])  # Blade missing: Thirsting then Devouring fall
    assert _card(r)["selected"] == [TOME, CHAIN]
    assert "Devouring Blade" in _pruned(r) and "Thirsting Blade" in _pruned(r)
    r = _res(catalog, 12, picks=[BLADE, DEVOUR, TOME])  # Thirsting missing
    assert _card(r)["selected"] == [BLADE, TOME]
    r = _res(catalog, 12, picks=[BLADE, THIRST, DEVOUR])
    assert _card(r)["selected"] == [BLADE, THIRST, DEVOUR]


@needs_data
def test_repeat_instances_need_previous(catalog):
    c = ["eldritch-blast-xphb", "toll-the-dead-xphb"]
    card = _card(_res(catalog, 5, cantrips=c))
    assert _opt(card, AGON + "~2")["disabled"] and "Agonizing Blast first" in _opt(card, AGON + "~2")["disabledReason"]
    r = _res(catalog, 5, picks=[AGON + "~2", TOME], cantrips=c)
    assert _card(r)["selected"] == [AGON, TOME]  # RP21: the stored repeat follows the missing base (renumbered)
    r = _res(catalog, 5, picks=[AGON, AGON + "~2", TOME], cantrips=c)
    assert _card(r)["selected"] == [AGON, AGON + "~2", TOME]
    # F3a-2a: three instances need three eligible cantrips
    r = _res(catalog, 5, picks=[AGON, AGON + "~2", AGON + "~3"], cantrips=c + ["poison-spray-xphb"])
    assert _card(r)["selected"] == [AGON, AGON + "~2", AGON + "~3"]
    r = _res(catalog, 5, picks=[AGON + "~3", AGON + "~2"], cantrips=c)  # RP21: base missing, the instances close the gap
    assert _card(r)["selected"] == [AGON + "~2", AGON]


@needs_data
def test_level_down_count_and_level_prereq(catalog):
    picks = [BLADE, TOME, CHAIN, "opt-armor-of-shadows-xphb", "opt-eldritch-mind-xphb"]
    r = _res(catalog, 4, picks=picks)  # level 4: table says 3
    assert _card(r)["count"] == 3 and _card(r)["selected"] == picks[:3]
    assert any(p["choiceId"] == INV for p in r["pruned"])
    assert not [p for p in r["problems"] if "over-selected" in p["id"]]
    r = _res(catalog, 14, picks=[WITCH])
    assert _opt(_card(r), WITCH)["disabledReason"] == "requires warlock level 15" and _card(r)["selected"] == []
    assert _card(_res(catalog, 15, picks=[WITCH]))["selected"] == [WITCH]


@needs_data
def test_sheet_features_row_lists_picks(catalog):
    c = ["eldritch-blast-xphb"]
    r = _res(catalog, 5, picks=[AGON, AGON + "~2", BLADE], cantrips=c + ["toll-the-dead-xphb"])
    row = next(f for f in r["sheet"]["features"] if f["name"] == "Eldritch Invocations")
    assert row["level"] == 1
    text = str(row)
    assert "Agonizing Blast (2)" in text and "Pact of the Blade" in text


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_other_rulesets_keep_srd_cards(catalog, ruleset):
    r = _res(catalog, 3, ruleset=ruleset)
    ids = [c["id"] for c in r["choices"]]
    assert INV not in ids
    assert any(":invocations:eldritch-invocations" in i for i in ids)
    assert any(i.endswith(":pact-boon") for i in ids)


@needs_data
def test_srd_only_catalog_keeps_srd_cards(catalog):
    r = _res(_srd_only(catalog), 3)
    ids = [c["id"] for c in r["choices"]]
    assert INV not in ids
    assert any(":invocations:eldritch-invocations" in i for i in ids)
    assert any(i.endswith(":pact-boon") for i in ids)


def test_instance_id_helpers():
    assert class_choices_2024.invocation_base_id("opt-agonizing-blast-xphb~3") == "opt-agonizing-blast-xphb"
    assert class_choices_2024.invocation_base_id("opt-x-xphb") == "opt-x-xphb"
    choices = [{"id": INV, "source": {"kind": "class", "id": "warlock"}, "selected": [AGON, AGON + "~2"]}]
    assert features.selected_invocation_ids(choices) == [("warlock", AGON), ("warlock", AGON)]
    assert features.selected_invocation_instances(choices) == [("warlock", AGON), ("warlock", AGON + "~2")]


@needs_data
def test_timing(catalog):
    picks = [BLADE, THIRST, DEVOUR, TOME, CHAIN, AGON, AGON + "~2", "opt-lessons-of-the-first-ones-xphb", WITCH, "opt-eldritch-mind-xphb"]
    c = ["eldritch-blast-xphb", "toll-the-dead-xphb"]
    for lvl, pk in [(17, picks[:9]), (20, picks)]:
        _res(catalog, lvl, picks=pk, cantrips=c)
        laps = []
        for _ in range(20):
            t_run = time.perf_counter()
            _res(catalog, lvl, picks=pk, cantrips=c)
            laps.append(time.perf_counter() - t_run)
        assert_fast(laps)
