"""FX3: cross-feat modifications (``modifies`` in the feat effect table).

Catalog sentences (tags stripped):
  greater-aberrant-mark-efa  "When you use the Aberrant Fortitude benefit of your Aberrant Dragonmark feat, you can roll
                              1d6 instead of 1d4. You also now regain your use of Aberrant Fortitude whenever you finish
                              a Short Rest or Long Rest."
  greater-mark-of-<x>-efa    "When you use the <Intuition> benefit of your Mark of <X> feat, you can roll 1d6 instead of 1d4."

Rule matrix: the patch applies only while BOTH feats are held; the base feat alone is unchanged; the greater feat
alone keeps its own entry; a held ERLW Aberrant Dragonmark (a different feat) is not patched."""
import pytest

from catalog import feat_effects_data as fed
from engine import feat_effects as fe

NUM = {"pb": 3, "con_mod": 2, "wis_mod": 1}


def _inst(index):
    return {"feat": {"index": index, "name": index}, "index": index, "prefix": f"feat:{index}", "origin": "background",
            "effect": fed.FEAT_EFFECTS[index], "increased": None, "resist": [], "pick_text": None}


def _fortitude(insts):
    return next(r for r in fe.resources(insts, NUM) if r["name"] == "Aberrant Fortitude")


def test_base_aberrant_fortitude_alone():
    r = _fortitude([_inst("aberrant-dragonmark-efa")])
    assert r["recharge"] == "long" and "1d4" in r["details"]["note"]


def test_greater_aberrant_mark_patches_fortitude():
    r = _fortitude([_inst("aberrant-dragonmark-efa"), _inst("greater-aberrant-mark-efa")])
    assert r["recharge"] == "short-or-long" and "1d6" in r["details"]["note"] and "1d4" not in r["details"]["note"]
    assert r["uses"] == 1


def test_greater_alone_and_erlw_base_are_not_patched():
    names = [r["name"] for r in fe.resources([_inst("greater-aberrant-mark-efa")], NUM)]
    assert names == ["Mark of Inspiration"]
    erlw = fe.notes([_inst("aberrant-dragonmark-erlw"), _inst("greater-aberrant-mark-efa")], NUM)
    assert all("1d6" not in t for t in erlw["feat:aberrant-dragonmark-erlw"])


MARKS = sorted(i[len("greater-"):] for i in fed.FEAT_EFFECTS if i.startswith("greater-mark-of-"))


@pytest.mark.parametrize("mark", MARKS)
def test_greater_mark_turns_the_intuition_die_into_1d6(mark):
    base = fe.notes([_inst(mark)], NUM)[f"feat:{mark}"]
    both = fe.notes([_inst(mark), _inst("greater-" + mark)], NUM)[f"feat:{mark}"]
    assert "1d6" in both[0] and "1d4" not in " ".join(both)
    assert "1d6" not in " ".join(base)


def test_twelve_marks_and_every_greater_mark_names_its_base():
    assert len(MARKS) == 12
    for greater in ("greater-" + m for m in MARKS):
        assert list(fed.FEAT_EFFECTS[greater]["modifies"]) == [greater[len("greater-"):]]
