"""G1-6 (S1 exactness): `derived.slotGrantingClasses` lists the classes that grant
shared-pool spell slots at their current level, so the SPA can say "(общи за всички
класове)" exactly when more than one does. Pact Magic classes never join the pool; a
class is tested against its real slot table at its level (Paladin 1 has none in 2014,
2024 half casters have slots from level 1), a third-caster subclass from its own table."""
import pytest

from catalog.loader import load
from engine.resolve import resolve
from engine.spells import slot_granting_classes


@pytest.fixture(scope="module")
def catalog():
    return load()


def _granting(catalog, classes, ruleset="mixed"):
    return slot_granting_classes(catalog, classes, ruleset)


def test_only_classes_that_grant_shared_slots(catalog):
    assert _granting(catalog, [("wizard", 5), ("cleric", 3)]) == ["wizard", "cleric"]
    assert _granting(catalog, [("wizard", 5), ("fighter", 3)]) == ["wizard"]
    assert _granting(catalog, [("wizard", 5), ("warlock", 2)]) == ["wizard"]       # Pact Magic is separate
    assert _granting(catalog, [("wizard", 5), ("paladin", 1)]) == ["wizard"]       # Paladin 1 has no slots (2014)
    assert _granting(catalog, [("wizard", 5), ("paladin", 2)]) == ["wizard", "paladin"]
    assert _granting(catalog, [("paladin", 1), ("ranger", 1)]) == []
    assert _granting(catalog, [("wizard", 5), ("paladin", 1)], "2024") == ["wizard", "paladin"]
    assert _granting(catalog, [("fighter", 3)]) == []
    assert _granting(catalog, [("warlock", 5)]) == []


def test_resolve_exposes_it(catalog):
    r = resolve({"classes": [{"classId": "wizard", "level": 3}, {"classId": "cleric", "level": 2},
                             {"classId": "fighter", "level": 1}],
                 "species": {"id": "human"}, "background": {"id": "acolyte"}}, catalog)
    assert r["derived"]["slotGrantingClasses"] == ["wizard", "cleric"]
    r = resolve({"classes": [{"classId": "wizard", "level": 3}], "species": {"id": "human"},
                 "background": {"id": "acolyte"}}, catalog)
    assert r["derived"]["slotGrantingClasses"] == ["wizard"]
    r = resolve({"classes": [], "species": {"id": "human"}, "background": {"id": "acolyte"}}, catalog)
    assert r["derived"]["slotGrantingClasses"] == []
