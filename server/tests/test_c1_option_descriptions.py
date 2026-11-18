"""C1: options that used to drop their English rules text now carry `description` (flattened plain text):
SRD `subfeature_options` kinds (fighting styles 2014/mixed, pact boon, hunter's prey, ...) and the 2024 Fighting Style
feat options. The ASI feat options stay text-less (fetched lazily elsewhere)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import kitchen_sink as ks  # noqa: E402
from catalog.loader import load  # noqa: E402
from catalog.official_source import has_official, has_official_classes  # noqa: E402
from engine.resolve import resolve  # noqa: E402


def _draft(cls, level, ruleset, sub=None):
    spec = ks._sub(cls, level, ruleset)
    return ks.fill(ks.base_draft({**spec, "classes": [(cls, level, sub)]}), load(), {}, resolve)


def _cards(res, kind):
    return [c for c in res["choices"] if kind in c["id"]]


@pytest.mark.parametrize("cls,level", [("fighter", 1), ("paladin", 2), ("ranger", 2)])
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_fighting_style_options_carry_text(cls, level, ruleset):
    res = resolve(_draft(cls, level, ruleset), load())
    cards = [c for c in res["choices"] if c["id"].startswith(f"class:{cls}:") and "fighting-style" in c["id"]]
    assert cards
    for card in cards:
        assert card["options"]
        for o in card["options"]:
            assert o.get("description"), o["id"]


def test_pact_boon_and_other_srd_kinds_carry_text():
    cat = load()
    res = resolve(_draft("warlock", 3, "2014"), cat)
    card = next(c for c in res["choices"] if "pact-boon" in c["id"])
    assert all(o.get("description") for o in card["options"])
    res = resolve(_draft("ranger", 3, "2014"), cat)
    hunters = [c for c in res["choices"] if "hunters-prey" in c["id"]]
    assert all(o.get("description") for c in hunters for o in c["options"])


@pytest.mark.skipif(not (has_official() and has_official_classes()), reason="official data missing")
@pytest.mark.parametrize("cls,level", [("fighter", 1), ("paladin", 2), ("ranger", 2)])
def test_2024_fighting_style_options_carry_text(cls, level):
    res = resolve(_draft(cls, level, "2024"), load())
    cards = [c for c in res["choices"] if c["id"].startswith(f"class:{cls}:") and c["id"].endswith(":fighting-style")]
    assert cards
    for card in cards:
        assert card["options"]
        for o in card["options"]:
            assert o["id"].startswith("feat:")
            assert o.get("description") and len(o["description"]) < 2500, o["id"]
