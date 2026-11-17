"""S12 (DATA-02): the clean-clone smoke script's pinned catalog counts are the ones of the test suite (the single source
`test_data_precedence.FULL`) and of the bundled catalog, so a data update cannot leave the smoke test with stale pins."""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

from catalog.loader import load
from catalog.official import paths
from test_data_precedence import FULL

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "smoke_clean_clone.py"


def _smoke():
    spec = importlib.util.spec_from_file_location("smoke_clean_clone_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_smoke_pins_are_read_from_test_data_precedence():
    assert _smoke().PINNED_COUNTS == FULL


@pytest.mark.skipif(paths.data_source() != "bundled", reason="the pins are those of the bundled data")
def test_the_pins_equal_the_bundled_catalog():
    cat = load()
    assert {k: len(getattr(cat, k)) for k in FULL} == FULL
