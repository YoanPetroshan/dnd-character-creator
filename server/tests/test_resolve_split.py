"""S17 (audit MAINT-01), step 2: engine/resolve.py shed its self-contained helper clusters into resolve_feats.py,
resolve_species.py, resolve_spells.py and resolve_gates.py (text moved unchanged). `engine.resolve` re-exports every moved name,
so `from engine.resolve import _spell_visible` and `resolve_mod._PREREQ_MSG_MEMO` keep working. A test that patches a moved
function must patch it in the module where it is used (the module that calls it), as test_w4_background_feats.py does."""
from __future__ import annotations

import importlib
import pathlib
import types

import engine.resolve as resolve_mod

ENGINE = pathlib.Path(__file__).resolve().parents[1] / "engine"
CLUSTERS = ("resolve_feats", "resolve_species", "resolve_spells", "resolve_gates")


def test_resolve_py_is_smaller_and_the_clusters_are_not_monoliths():
    assert len((ENGINE / "resolve.py").read_text(encoding="utf-8").splitlines()) < 3600
    for name in CLUSTERS:
        assert len((ENGINE / f"{name}.py").read_text(encoding="utf-8").splitlines()) < 2000, name


def test_every_name_a_cluster_defines_is_the_same_object_in_engine_resolve():
    for name in CLUSTERS:
        module = importlib.import_module(f"engine.{name}")
        for attr, value in vars(module).items():
            if attr.startswith("__") or isinstance(value, types.ModuleType) or getattr(value, "__module__", None) != module.__name__:
                continue  # only what the cluster itself defines (functions, classes)
            assert getattr(resolve_mod, attr) is value, (name, attr)


def test_the_clusters_do_not_import_engine_resolve():
    """No cycle: the clusters are leaves, resolve.py imports them."""
    for name in CLUSTERS:
        text = (ENGINE / f"{name}.py").read_text(encoding="utf-8")
        assert "from .resolve import" not in text and "import resolve" not in text.replace("resolve_", ""), name
