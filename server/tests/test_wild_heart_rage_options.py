"""G1-7: Path of the Wild Heart per-rage options (XPHB), shown in the Rage resource.

Catalog text (feature `wild-heart-xphb-3-rage-of-the-wilds`): "Whenever you activate
your Rage, you gain one of the following options of your choice." Bear / Eagle / Wolf;
level 14 `wild-heart-xphb-14-power-of-the-wilds`: Falcon / Lion / Ram. The choice is made
each rage, so it is information, not a build choice: `details.perRageOptions` lists
{name, effect} (effect = catalog text without the "Name." prefix), only for ruleset
2024 with the Wild Heart subclass at level 3 (Rage of the Wilds) / 14 (Power of the Wilds).
Not shown for other subclasses, other rulesets, or below the feature's level."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official_classes
from engine.resolve import resolve
from export_fields import resource_detail_parts

pytestmark = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _rage(catalog, level, ruleset="2024", sub="wild-heart-xphb"):
    d = {"ruleset": ruleset, "sources": [], "species": {"id": "human"}, "background": {"id": "acolyte"},
         "classes": [{"classId": "barbarian", "level": level, **({"subclassId": sub} if sub else {}), "choices": {}}]}
    r = resolve(d, catalog)
    return next(x for x in r["derived"]["classResources"] if x["name"] == "Rage")


def test_level_3_lists_bear_eagle_wolf(catalog):
    opts = _rage(catalog, 3)["details"]["perRageOptions"]
    assert [o["name"] for o in opts] == ["Bear", "Eagle", "Wolf"]
    assert opts[0]["effect"].startswith("While your Rage is active, you have Resistance to every damage type except Force")
    assert "Disengage and Dash" in opts[1]["effect"]
    assert "Advantage on attack rolls against any enemy" in opts[2]["effect"]


def test_level_14_adds_power_of_the_wilds(catalog):
    assert [o["name"] for o in _rage(catalog, 13)["details"]["perRageOptions"]] == ["Bear", "Eagle", "Wolf"]
    opts = _rage(catalog, 14)["details"]["perRageOptions"]
    assert [o["name"] for o in opts] == ["Bear", "Eagle", "Wolf", "Falcon", "Lion", "Ram"]
    assert "Fly Speed" in opts[3]["effect"]


@pytest.mark.parametrize("ruleset,sub", [("mixed", "wild-heart-xphb"), ("2014", "wild-heart-xphb"),
                                         ("2024", None), ("2024", "berserker-xphb")])
def test_absent_elsewhere(catalog, ruleset, sub):
    assert "perRageOptions" not in _rage(catalog, 14, ruleset, sub)["details"]


def test_readable_fragment(catalog):
    frag = [p for p in resource_detail_parts(_rage(catalog, 3)["details"]) if "Bear" in p]
    assert len(frag) == 1 and frag[0].startswith("при всяка ярост една от опциите: Bear: While your Rage")
    assert "; Eagle: " in frag[0] and "; Wolf: " in frag[0]
