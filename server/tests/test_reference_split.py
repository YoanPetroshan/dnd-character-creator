"""S17 (audit MAINT-01): catalog/reference_data.py is a facade over the topic modules of catalog/reference/.

The split was proven by comparing the facade with the old single module name by name (196 names, equal values, same
iteration order); these tests keep the structure: every name a topic module defines is reachable through the facade, the
"catalog.reference_data:NAME" strings of DATA_OVERRIDES still resolve, and no topic module grows back into a monolith."""
from __future__ import annotations

import importlib
import pathlib
import types

from catalog import reference_data as facade
from catalog.reference_data import DATA_OVERRIDES

PACKAGE = pathlib.Path(__file__).resolve().parents[1] / "catalog" / "reference"
MODULES = sorted(p.stem for p in PACKAGE.glob("*.py") if p.stem != "__init__")


def test_the_facade_is_small_and_the_topic_modules_stay_below_1000_lines():
    assert len((PACKAGE.parent / "reference_data.py").read_text(encoding="utf-8").splitlines()) < 40
    sizes = {m: len((PACKAGE / f"{m}.py").read_text(encoding="utf-8").splitlines()) for m in MODULES}
    assert len(MODULES) >= 10 and max(sizes.values()) < 1000, sizes


def test_every_public_name_of_a_topic_module_is_reachable_through_the_facade():
    for name in MODULES:
        module = importlib.import_module(f"catalog.reference.{name}")
        for attr, value in vars(module).items():
            if attr.startswith("__") or isinstance(value, types.ModuleType) or attr == "annotations":
                continue
            assert hasattr(facade, attr), (name, attr)


def test_a_name_defined_in_several_topic_modules_has_its_last_binding_in_the_facade():
    # the W8 tails rebind SUBCLASS_TAIL_2014_BOOKS in four modules and class_options adds the X2 rows: the facade shows the last
    last = importlib.import_module("catalog.reference.class_options")
    assert facade.SUBCLASS_TAIL_2014_BOOKS is last.SUBCLASS_TAIL_2014_BOOKS
    assert len(facade.SUBCLASS_TAIL_2014_BOOKS) > 100


def _where_strings(node):
    if isinstance(node, str):
        if node.startswith("catalog.reference_data:"):
            yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _where_strings(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _where_strings(v)


def test_the_where_strings_of_data_overrides_resolve_through_the_facade():
    wheres = list(_where_strings(DATA_OVERRIDES))
    assert len(wheres) >= 3
    for where in wheres:
        module_name, _, attr = where.partition(":")
        assert hasattr(importlib.import_module(module_name), attr), where
