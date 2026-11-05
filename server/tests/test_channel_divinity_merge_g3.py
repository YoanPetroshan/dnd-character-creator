"""G3: the merged Cleric + Paladin Channel Divinity keeps BOTH classes' notes; the Divine Intervention lockouts are pinned.

Governing texts:
  PHB 164 (multiclassing, Channel Divinity): the features of two classes are one feature; the extra class only adds
  effect options, not uses (`class_resources._merge_channel_divinity`: one entry, uses = max, first class on a tie).
  Before G3 the entry kept only the winning class's note, so a Cleric 6 / Paladin 3 lost the Sacred Weapon and Turn the
  Unholy sentences.
  SRD cleric `divine-intervention` (10): "If your deity intervenes, you can't use this feature again for 7 days.
  Otherwise, you can use it again after you finish a long rest." (+ `divine-intervention-improvement`, 20: "your call for
  intervention succeeds automatically, no roll required").
  XPHB cleric 20 Greater Divine Intervention: "If you do so, you can't use Divine Intervention again until you finish
  2d4 Long Rests." Both lockouts were already in the notes (W6, R9); they stay notes, not a recharge: the 7 days follow a
  success only and the 2d4 Long Rests follow a Wish only, which the X2 vocabulary (`other` = a condition in the note) cannot
  carry as a base recharge, so `recharge` stays "long".

Rule matrix (merge):
  note      more than one class with a note: "<Class>: <note> | <Class>: <note>" in class order; a lone note is unchanged
  uses      unchanged (max over the classes, first class on a tie); `details.classes` unchanged
  2024      unchanged: separate per-class pools, no label
  single    a single-class character is unchanged"""
import copy
import re

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import class_resources
from engine.resolve import resolve
from export_fields import resource_line
from perf_helpers import assert_fast, measure

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2014"):
    return {"ruleset": ruleset, "sources": [],
            "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 14, "CHA": 14}},
            "species": {"id": "human"}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [], "skipped": False},
            "classes": [{"classId": c, "level": lv, **({"subclassId": sub} if sub else {}), "choices": {}}
                        for c, lv, sub in classes]}


def _cds(res):
    return [r for r in res["derived"]["classResources"] if r["name"] == "Channel Divinity"]


def _only(res):
    cds = _cds(res)
    assert len(cds) == 1
    return cds[0]


def _dc(note):
    """The save DC moves with the total level (proficiency bonus): compare notes with the number masked."""
    return re.sub(r"save DC \d+", "save DC N", note)


def _alone(catalog, cls, level, sub, ruleset="2014"):
    return _only(resolve(_draft([(cls, level, sub)], ruleset), catalog))


# ---- merge ---------------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_both_notes_are_kept_class_labelled(catalog, ruleset):
    merged = _only(resolve(_draft([("cleric", 6, "life"), ("paladin", 3, "devotion")], ruleset), catalog))
    cleric = _alone(catalog, "cleric", 6, "life", ruleset)["details"]["note"]
    paladin = _alone(catalog, "paladin", 3, "devotion", ruleset)["details"]["note"]
    assert "Preserve Life" in cleric and "Sacred Weapon" in paladin and "Turn the Unholy" in paladin
    assert _dc(merged["details"]["note"]) == _dc(f"Cleric: {cleric} | Paladin: {paladin}")
    assert "save DC 14 (your cleric spell save DC)" in merged["details"]["note"]  # Cleric 6 + Paladin 3: level 9, PB +4
    assert "save DC 14 (your paladin spell save DC)" in merged["details"]["note"]
    assert merged["details"]["classes"] == ["cleric", "paladin"]
    assert (merged["uses"], merged["recharge"], merged["classId"]) == (2, "short-or-long", "cleric")  # unchanged rule


@needs_data
def test_label_order_follows_the_class_order_and_the_tie_winner_is_the_first_class(catalog):
    merged = _only(resolve(_draft([("paladin", 3, "devotion"), ("cleric", 2, "life")]), catalog))
    paladin = _alone(catalog, "paladin", 3, "devotion")["details"]["note"]
    cleric = _alone(catalog, "cleric", 2, "life")["details"]["note"]
    assert (merged["uses"], merged["classId"]) == (1, "paladin")
    assert _dc(merged["details"]["note"]) == _dc(f"Paladin: {paladin} | Cleric: {cleric}")
    assert merged["details"]["classes"] == ["paladin", "cleric"]


@needs_data
def test_the_merged_entry_keeps_its_place_and_nothing_else_moves(catalog):
    res = resolve(_draft([("cleric", 6, "life"), ("paladin", 3, "devotion")]), catalog)
    names = [r["name"] for r in res["derived"]["classResources"]]
    assert names.count("Channel Divinity") == 1
    single = [r["name"] for r in resolve(_draft([("cleric", 6, "life")]), catalog)["derived"]["classResources"]]
    assert names[:len(single)] == single  # the Cleric's resources first, Channel Divinity where it was


def test_a_lone_note_stays_unlabelled():
    """Both classes normally have a sentence; if only one does (a catalog without the records), that note is kept as it was."""
    def cd(cls, label, uses, note):
        details = {"note": note} if note else {}
        return {"id": f"{cls}:channel-divinity", "classId": cls, "source": {"kind": "class", "id": cls, "label": label},
                "name": "Channel Divinity", "uses": uses, "recharge": "short-or-long", "details": details}
    out = class_resources._merge_channel_divinity([cd("cleric", "Cleric", 2, "Turn Undead"), cd("paladin", "Paladin", 1, None)])
    assert len(out) == 1 and out[0]["details"] == {"note": "Turn Undead", "classes": ["cleric", "paladin"]}
    out = class_resources._merge_channel_divinity([cd("cleric", "Cleric", 2, "A"), cd("paladin", "Paladin", 1, "B")])
    assert out[0]["details"]["note"] == "Cleric: A | Paladin: B"
    only = [cd("cleric", "Cleric", 2, "A")]
    assert class_resources._merge_channel_divinity(only) == only


@needs_data
def test_single_class_is_unchanged(catalog):
    for cls, sub, lvl in (("cleric", "life", 6), ("paladin", "devotion", 3)):
        cd = _alone(catalog, cls, lvl, sub)
        assert "classes" not in cd["details"] and not cd["details"]["note"].startswith(("Cleric:", "Paladin:"))


@needs_data
def test_2024_keeps_separate_pools_without_labels(catalog):
    res = resolve(_draft([("cleric", 6, "life-xphb"), ("paladin", 3, "glory-xphb")], "2024"), catalog)
    cds = _cds(res)
    assert [c["classId"] for c in cds] == ["cleric", "paladin"]
    assert all("classes" not in c["details"] and not (c["details"].get("note") or "").startswith(("Cleric:", "Paladin:"))
               for c in cds)


@needs_data
def test_export_line_prints_both_notes(catalog):
    res = resolve(_draft([("cleric", 6, "life"), ("paladin", 3, "devotion")]), catalog)
    line = resource_line(_only(res), "en")
    assert "Cleric: Turn Undead" in line and "Paladin: " in line and "Sacred Weapon" in line


@needs_data
def test_resolve_stays_fast(catalog):
    draft = _draft([("cleric", 11, "life"), ("paladin", 7, "devotion")])
    resolve(copy.deepcopy(draft), catalog)
    assert_fast(measure(lambda: resolve(copy.deepcopy(draft), catalog)), "cleric 11 / paladin 7 merged Channel Divinity")


# ---- Divine Intervention: the lockout texts (already notes since W6 / R9; pinned here) ---------------------------------

@needs_data
def test_the_lockout_texts_are_in_the_records(catalog):
    srd = "\n".join(catalog.features["divine-intervention"]["desc"])
    assert "If your deity intervenes, you can't use this feature again for 7 days." in srd
    assert "Otherwise, you can use it again after you finish a long rest." in srd
    assert "roll percentile dice. If you roll a number equal to or lower than your cleric level" in srd
    assert "your call for intervention succeeds automatically, no roll required" in "\n".join(
        catalog.features["divine-intervention-improvement"]["desc"])
    greater = "\n".join(catalog.features["xphb-cleric-20-greater-divine-intervention"]["desc"])
    assert "you can't use Divine Intervention again until you finish 2d4 Long Rests." in greater
    assert "Wish" in greater


@needs_data
@pytest.mark.parametrize("level", [10, 15, 19, 20])
def test_2014_note_states_the_roll_and_the_seven_days(catalog, level):
    res = resolve(_draft([("cleric", level, "life")]), catalog)
    di = next(r for r in res["derived"]["classResources"] if r["id"] == "cleric:divine-intervention")
    note = di["details"]["note"]
    assert f"{level} or lower (your Cleric level)" in note and "can't use this again for 7 days" in note
    assert "otherwise you can use it again after a long rest" in note
    assert ("succeeds automatically, no roll required" in note) == (level == 20)
    assert (di["uses"], di["recharge"]) == (1, "long")  # the 7 days follow a success only: a note, not a recharge


@needs_data
@pytest.mark.parametrize("level", [10, 19, 20])
def test_2024_note_states_the_wish_lockout_from_level_20(catalog, level):
    res = resolve(_draft([("cleric", level, "life-xphb")], "2024"), catalog)
    di = next(r for r in res["derived"]["classResources"] if r["id"] == "cleric:divine-intervention")
    assert ("you can't use Divine Intervention again until you finish 2d4 Long Rests" in di["details"]["note"]) == (level == 20)
    assert (di["uses"], di["recharge"]) == (1, "long")


def test_reference_quotes_are_the_ones_pinned_above():
    spec = next(s for s in reference_data.RESOURCE_TAIL_2014 if s.get("feature") == "divine-intervention")
    assert any("7 days" in q for _fid, q in spec["quotes"])
