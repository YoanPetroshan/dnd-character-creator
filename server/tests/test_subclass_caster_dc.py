"""Round-2 audit F14: subclass-only casters (Arcane Trickster, Eldritch Knight,
Monk Shadow/Elements) get a spell save DC/attack from the subclass's ability."""
import pytest

from catalog.loader import load
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _entry(catalog, cls, sub, level=3):
    base = {"STR": 10, "DEX": 10, "CON": 10, "INT": 16, "WIS": 14, "CHA": 8}
    r = resolve({
        "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": {}}],
        "abilities": {"method": "manual", "base": base},
    }, catalog)
    return next((e for e in r["sheet"]["spells"] if e["classId"] == cls), None)


@needs_official
@pytest.mark.parametrize("cls,sub,mod", [
    ("rogue", "arcane-trickster-phb", 3),   # INT 16
    ("rogue", "arcane-trickster-xphb", 3),
    ("monk", "shadow-xphb", 2),              # WIS 14
    ("monk", "elements-xphb", 2),
])
def test_subclass_only_caster_has_dc_and_attack(catalog, cls, sub, mod):
    e = _entry(catalog, cls, sub)
    assert e is not None and e["alwaysPrepared"]
    assert e["spellSaveDC"] == 8 + 2 + mod
    assert e["spellAttackBonus"] == 2 + mod


def test_real_caster_unchanged(catalog):
    e = _entry(catalog, "wizard", None, 1)
    assert e is None or e["spellSaveDC"] is not None
