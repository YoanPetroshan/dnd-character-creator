"""S14 (TEST-02): the baseline writers are guarded (see baseline_guard.py)."""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

import baseline_guard as G

HERE = pathlib.Path(__file__).resolve().parent
WRITERS = ("test_export_baseline.py", "test_sheet_baseline.py", "test_service_baseline.py")


def test_writing_is_refused_when_ci_is_set(monkeypatch, tmp_path):
    monkeypatch.setenv("CI", "true")
    target = tmp_path / "b.json"
    with pytest.raises(G.BaselineWriteRefused):
        G.write_baseline(target, {"a": 1}, {}, "test")
    assert not target.exists()


def test_writing_works_outside_ci_and_prints_the_change(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("CI", raising=False)
    target = tmp_path / "b.json"
    G.write_baseline(target, {"a": 2, "c": 3}, {"a": 1, "b": 9}, "test")
    assert json.loads(target.read_text()) == {"a": 2, "c": 3}
    out = capsys.readouterr().out
    assert "+1 new [c]" in out and "-1 removed [b]" in out and "~1 changed [a]" in out


def test_the_summary_of_identical_dicts_is_all_zero():
    assert G.change_summary({"a": 1}, {"a": 1}) == "+0 new [], -0 removed [], ~0 changed []"


@pytest.mark.parametrize("name", WRITERS)
def test_every_baseline_test_writes_through_the_guard(name):
    tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
    text = ast.unparse(tree)
    assert "baseline_guard" in text, f"{name} must import baseline_guard"
    assert "write_baseline(" in text or "refuse_in_ci(" in text, f"{name} must call the guard before writing"
    assert ".write_text(" not in text.replace("BASELINE.read_text", ""), f"{name} writes a baseline without the guard"
