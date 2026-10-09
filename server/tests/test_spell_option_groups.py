"""Round-2 audit F8: class spell choices carry a per-option `group` so the
picker can show "Заклинания ниво N"/"Трикове" headings."""
import pytest

from catalog.loader import load
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


def _choices(catalog, cls, level):
    r = resolve({"classes": [{"classId": cls, "level": level, "choices": {}}]}, catalog)
    return {c["id"]: c for c in r["choices"]}


def test_spell_options_have_level_groups(catalog):
    ch = _choices(catalog, "wizard", 5)
    cantrips = ch["class:wizard:spells-cantrips"]["options"]
    assert cantrips and all(o["group"] == "spell-level-0" for o in cantrips)
    known = ch["class:wizard:spells-known"]["options"]
    for o in known:
        lvl = catalog.spells[o["id"]]["level"]
        assert o["group"] == f"spell-level-{lvl}"
    levels = [int(o["group"].rsplit("-", 1)[1]) for o in known]
    assert levels == sorted(levels)  # consecutive grouping


def test_non_spell_options_have_no_group(catalog):
    ch = _choices(catalog, "fighter", 4)
    asi = ch["class:fighter:4:asi"]["options"]
    assert all("group" not in o for o in asi)
