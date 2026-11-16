"""S14 (audit TEST-03): the oracle of tools/chartest and the fuzz generator of test_resolve_fuzz.py are tied together.

20 seeded random drafts are settled like the fuzz test does and then checked by every rule of the character-test oracle
(`tools.chartest.checks`); a failed rule must be listed in `tools/chartest/known_gaps.json`, otherwise the test fails with
the seed (reproduce with `gen_draft(seed, load())`). Run more seeds: `FUZZ_ORACLE_N=200 pytest test_fuzz_oracle.py`."""
from __future__ import annotations

import os

import pytest

import test_resolve_fuzz as fz
from engine.resolve import resolve
from tools.chartest import checks, runner
from tools.chartest.spec import CharSpec, have_data

pytestmark = pytest.mark.skipif(not have_data(), reason="5etools data missing (classes / official)")

N = int(os.environ.get("FUZZ_ORACLE_N", "20"))


def _spec(seed: int, draft: dict) -> CharSpec:
    classes = [[c["classId"], c["level"], c.get("subclassId")] for c in draft["classes"]]
    return CharSpec(id=f"fuzz-{seed}", ruleset=draft["ruleset"], classes=classes)


@pytest.fixture(scope="module")
def catalog():
    return fz.load()


def test_the_oracle_finds_no_unknown_gap_in_the_fuzz_drafts(catalog):
    gaps = runner.load_known_gaps()
    unknown, settled_n, ran = [], 0, 0
    for seed in range(N):
        draft = fz.gen_draft(seed, catalog)
        try:
            filled = fz.settle(draft, catalog)
        except fz.Settle:
            continue  # a draft that never settles is the business of test_resolve_fuzz
        settled_n += 1
        res = resolve(filled, catalog)
        spec = _spec(seed, filled)
        results = checks.run_checks(filled, res)
        ran += len(results)
        for r in results:
            if not r["ok"] and runner.known_gap(r, spec, gaps) is None:
                unknown.append(f"seed={seed} {r['check']}: expected {str(r['expected'])[:120]} / actual {str(r['actual'])[:120]}")
    assert settled_n >= N // 2, f"only {settled_n} of {N} drafts settled"
    assert ran >= 10 * settled_n, f"the oracle ran only {ran} checks on {settled_n} drafts"
    assert unknown == [], "\n".join(unknown)


def test_a_corrupted_value_in_a_fuzz_draft_is_caught_and_is_not_a_known_gap(catalog):
    """Non-vacuity: the same loop fails when the resolution is wrong."""
    draft = fz.settle(fz.gen_draft(3, catalog), catalog)
    res = resolve(draft, catalog)
    res["derived"]["hitPointMax"] += 7
    failed = [r for r in checks.run_checks(draft, res) if not r["ok"]]
    assert failed
    gaps = runner.load_known_gaps()
    assert any(runner.known_gap(r, _spec(3, draft), gaps) is None for r in failed)
