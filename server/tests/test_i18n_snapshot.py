"""I1: the frozen English message snapshot (tests/golden/messages_en_snapshot.json.gz) must stay identical.

The snapshot was taken from the engine BEFORE any message conversion (see tests/i18n_zoo.py). Every later i18n slice
(I2-I5: engine emission sites become tagged `Msg` values) must keep it byte-for-byte equal. A diff here is an executor
error: stop and report; never regenerate (the file only grows through `i18n_zoo.py --append`).
"""
from __future__ import annotations

import json
import re

import pytest

import i18n_zoo as zoo

pytestmark = pytest.mark.skipif(bool(zoo.NEEDS_DATA), reason=f"5etools data missing: {', '.join(zoo.NEEDS_DATA)}")

CHUNKS = 8

# Message sites (id pattern || message pattern, from the AST scan of the engine) that no zoo case can reach with the
# real catalog: dead after normalize_draft (resolve repeats a check normalize already made), or reachable only with
# data the bundle does not have. Listed on purpose so a new unreachable site shows up as a failure here.
KNOWN_GAPS = {
    # resolve() re-checks a level / ability score that normalize_draft has already coerced: unreachable
    r"level\-unsupported  ||  Level\ .*?\ for\ '.*?'\ isn't\ a\ valid\ number;\ using\ 1\ instead\.",
    r"ability\-invalid\-.*?  ||  .*?\ score\ .*?\ isn't\ a\ valid\ number;\ using\ 10\ instead\.",
    # a species / background feat pick whose feat has a structured prerequisite: no Origin feat in the data has one
    r"feat\-prerequisite\-unmet\-.*?  ||  .*?'s\ prerequisite\ isn't\ met,\ so\ the\ .*?\ pick\ isn't\ applied\.",
    r"feat\-prerequisite\-unmet\-.*?  ||  .*?'s\ prerequisite\ isn't\ met\.",
}


@pytest.fixture(scope="module")
def catalog():
    return zoo.load()


@pytest.fixture(scope="module")
def cases(catalog):
    return zoo.zoo(catalog)


@pytest.fixture(scope="module")
def stored():
    return zoo.load_snapshot()


def test_snapshot_file_present(stored):
    assert stored, "tests/golden/messages_en_snapshot.json.gz is missing (freeze it with i18n_zoo.py --freeze)"


def test_every_stored_case_is_still_in_the_zoo(stored, cases):
    assert not sorted(set(stored) - set(cases)), "the snapshot only grows: a zoo case was removed or renamed"


def test_every_zoo_case_is_stored(stored, cases):
    assert not sorted(set(cases) - set(stored)), "new zoo case: add it with i18n_zoo.py --append"


@pytest.mark.parametrize("chunk", range(CHUNKS))
def test_english_messages_are_identical_to_the_snapshot(chunk, stored, cases, catalog):
    names = sorted(stored)[chunk::CHUNKS]
    changed = {}
    for name in names:
        now = zoo.case_leaves(cases[name], zoo.catalog_for(name, catalog))
        if now != stored[name]:
            changed[name] = [k for k in stored[name] if now[k] != stored[name][k]]
    assert not changed, f"{len(changed)} zoo case(s) changed (English text must stay identical): {dict(list(changed.items())[:5])}"


def test_zoo_holds_every_golden_draft_in_all_four_variants(stored):
    golden = zoo.golden_drafts()
    assert len(golden) >= 251
    for name in golden:
        for prefix in ("g", "clear", "half", "r2024"):
            assert f"{prefix}/{name}" in stored, f"{prefix}/{name}"


def test_zoo_holds_the_2024_kitchen_sinks(stored, catalog):
    import kitchen_sink as ks
    sinks = [sid for sid, spec in ks.KITCHEN_SINK.items() if spec["ruleset"] == "2024" and not ks.skip_reason(spec)]
    assert len(sinks) >= 5
    for sid in sinks:
        assert f"ks2024/{sid}" in stored and f"ks2024-as-2014/{sid}" in stored


def test_every_trigger_produces_some_message(stored):
    silent = [n for n in zoo.TRIGGERS
              if not any(stored[f"t/{n}"][k] for k in ("problems", "warnings", "pruned", "exportGate"))]
    assert not silent, f"triggers that no longer trigger anything: {silent}"


def test_trigger_catalog_variants_exist():
    assert set(zoo.TRIGGER_CATALOG.values()) <= set(zoo.CATALOG_VARIANTS)


def test_problem_and_warning_families_are_covered_except_the_known_gaps(stored):
    covered, uncovered = zoo.coverage(stored)
    assert len(covered) + len(uncovered) >= 87, "the AST scan found fewer msg(...) problem/warning sites than at I2"
    assert set(uncovered.values()) == KNOWN_GAPS, sorted(set(uncovered.values()) ^ KNOWN_GAPS)


def test_snapshot_leaves_are_plain_json_text(stored):
    leaf = stored["t/ability-out-of-range-final-suffix"]
    assert leaf["problems"] and "still outside 1-30" in leaf["problems"][0][1]  # the engine appends to a message in place
    json.dumps(stored)  # strings and containers only


def test_snapshot_never_regenerates():
    with pytest.raises(SystemExit):
        zoo.main(["--regenerate"])
    with pytest.raises(SystemExit, match="never regenerated"):
        zoo.freeze()


def test_zoo_size_floor(stored):
    pr = {re.sub(r"\d+", "N", re.sub(r"'[^']*'", "Q", r)) for leaf in stored.values() for _i, r in leaf["pruned"]}
    assert len(stored) >= 1100 and len(pr) >= 150
