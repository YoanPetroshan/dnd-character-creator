"""T0: the controlled rebaseline of the frozen English message snapshot (i18n_zoo.rebaseline), on a synthetic zoo.

The real snapshot file is never touched here. The registry itself is pinned: it is append-only."""
from __future__ import annotations

import gzip
import json

import pytest

import i18n_zoo as zoo

PINNED = ("F1", "F1b", "VF1")  # extend (append) in the same commit as every new SNAPSHOT_REBASELINES entry


def _leaf(msg="x", extra=None):
    return {"problems": [["p1", msg]], "warnings": [], "pruned": [], "disabled": {"c | o": "d"}, "cards": {"c": ["L", "D"]},
            "exportGate": [], **(extra or {})}


STORED = {"a/one": _leaf(), "a/two": _leaf(), "b/three": _leaf()}


def _setup(tmp_path, table, now):
    """now: case -> leaves the 'engine' emits today."""
    path = tmp_path / "snap.json.gz"
    zoo._write(STORED, path)
    cases = {n: n for n in STORED}
    return dict(rebaselines=table, cases=cases, leaves_for=lambda n, d: now.get(n, STORED[n]),
                stored=json.load(gzip.open(path, "rt")), path=path, out=lambda *_: None), path


def _stored(path):
    return json.load(gzip.open(path, "rt"))


def _table(cases, paths):
    return {"T": {"cases": cases, "paths": paths, "why": "test"}}


def test_registry_is_append_only_and_well_formed():
    assert tuple(zoo.SNAPSHOT_REBASELINES) == PINNED
    for spec in zoo.SNAPSHOT_REBASELINES.values():
        assert spec["cases"] and spec["paths"] and spec["why"]


def test_unlisted_change_fails_the_snapshot_compare_and_the_rebaseline(tmp_path):
    now = {"a/one": _leaf("changed")}
    kw, path = _setup(tmp_path, _table(["a/one"], [r"^nothing$"]), now)
    assert zoo.diff_paths(STORED["a/one"], now["a/one"]) == ["problems[0][1]"]  # what the snapshot test would report
    with pytest.raises(zoo.RebaselineError):
        zoo.rebaseline("T", **kw)
    assert _stored(path) == STORED


def test_change_in_an_unmatched_case_fails_even_when_the_path_is_allowed(tmp_path):
    now = {"b/three": _leaf("changed")}
    kw, path = _setup(tmp_path, _table(["a/*"], [r"^problems"]), now)
    with pytest.raises(zoo.RebaselineError):
        zoo.rebaseline("T", **kw)
    assert _stored(path) == STORED


def test_listed_change_passes_only_after_the_rebaseline_writes_it(tmp_path):
    now = {"a/one": _leaf("changed"), "a/two": _leaf("changed")}
    kw, path = _setup(tmp_path, _table(["a/*"], [r"^problems\[0\]\[1\]$"]), now)
    assert any(zoo.diff_paths(STORED[n], now[n]) for n in now)  # before: the snapshot compare fails
    rep = zoo.rebaseline("T", **kw)
    assert sorted(rep["changed"]) == ["a/one", "a/two"] and not rep["violations"]
    after = _stored(path)
    assert after["a/one"] == now["a/one"] and after["b/three"] == STORED["b/three"]
    assert not any(zoo.diff_paths(after[n], now.get(n, STORED[n])) for n in after)  # after: the compare passes


def test_dry_run_writes_nothing_and_reports_violations_without_raising(tmp_path):
    now = {"a/one": _leaf("changed", {"warnings": [["w", "new"]]})}
    kw, path = _setup(tmp_path, _table(["a/*"], [r"^problems"]), now)
    before = path.read_bytes()
    lines = []
    kw["out"] = lines.append
    rep = zoo.rebaseline("T", dry_run=True, **kw)
    assert path.read_bytes() == before and rep["violations"] == {"a/one": ["warnings"]}
    assert any("DISALLOWED warnings" in line for line in lines)


def test_removing_a_stored_case_is_refused_even_in_a_dry_run(tmp_path):
    kw, path = _setup(tmp_path, _table(["*"], [r"."]), {})
    kw["cases"] = {n: n for n in STORED if n != "b/three"}
    for dry in (True, False):
        with pytest.raises(zoo.RebaselineError, match="only grows"):
            zoo.rebaseline("T", dry_run=dry, **kw)
    assert _stored(path) == STORED


def test_new_zoo_cases_are_not_added_by_a_rebaseline(tmp_path):
    kw, path = _setup(tmp_path, _table(["*"], [r"."]), {})
    kw["cases"] = {**kw["cases"], "z/new": "z/new"}
    zoo.rebaseline("T", **kw)
    assert set(_stored(path)) == set(STORED)


def test_unknown_slice_raises(tmp_path):
    kw, _ = _setup(tmp_path, {}, {})
    with pytest.raises(KeyError):
        zoo.rebaseline("nope", **kw)


def test_diff_paths_shapes():
    assert zoo.diff_paths({"a": [1, 2]}, {"a": [1, 3]}) == ["a[1]"]
    assert zoo.diff_paths({"a": [1]}, {"a": [1, 2]}) == ["a"]
    assert zoo.diff_paths({"d": {"x | y": "1"}}, {"d": {}}) == ["d.x | y"]


def test_cli_still_has_no_regenerate_and_rejects_bad_rebaseline_usage():
    for argv in (["--regenerate"], ["--rebaseline"], ["--rebaseline", "X", "--oops"]):
        with pytest.raises(SystemExit):
            zoo.main(argv)
    with pytest.raises(SystemExit, match="unknown rebaseline"):
        zoo.main(["--rebaseline", "NOPE", "--dry-run"])
