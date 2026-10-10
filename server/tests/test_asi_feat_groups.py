"""A3: feat options are grouped and sorted for phones: ASI combos first
(group "asi"), then feat groups; same-name feats get a " (SOURCE)" label."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset, level=4, species=None, choices=None):
    return {
        "ruleset": ruleset, "sources": [],
        "classes": [{"classId": "fighter", "level": level, "choices": choices or {}}],
        "species": species or {"id": "human"}, "background": {"id": "acolyte"},
    }


def _opts(ruleset, catalog, level=4, slot=None):
    r = resolve(_draft(ruleset, level), catalog)
    return next(c for c in r["choices"] if c["id"] == f"class:fighter:{slot or level}:asi")["options"]


def _feats(opts):
    return [o for o in opts if o["id"].startswith("feat:")]


def test_combos_come_first_with_asi_group(catalog):
    opts = _opts("mixed", catalog)
    assert all(o.get("group") == "asi" for o in opts[:21])
    assert all(not o["id"].startswith("feat:") for o in opts[:21])
    assert all(o["id"].startswith("feat:") for o in opts[21:])


def test_group_order_and_first_ids(catalog):
    mixed = _feats(_opts("mixed", catalog))
    groups = [o["group"] for o in mixed]
    assert [g for i, g in enumerate(groups) if i == 0 or g != groups[i - 1]] == ["general", "origin", "feat-2014"]
    assert [o["id"] for o in mixed[:3]] == ["feat:abjuration-adept-au", "feat:actor-xphb", "feat:arcane-warrior-au"]
    y2014 = _feats(_opts("2014", catalog))
    gs = [o["group"] for o in y2014]
    assert [g for i, g in enumerate(gs) if i == 0 or g != gs[i - 1]] == ["feat-2014", "general"]
    assert [o["id"] for o in y2014[:3]] == [
        "feat:aberrant-dragonmark-erlw", "feat:actor-phb", "feat:adept-of-the-black-robes-dsotdq"]
    boons = _feats(_opts("2024", catalog, 19))
    assert [o["id"] for o in boons[:3]] == [
        "feat:boon-of-blazing-dawn-abh", "feat:boon-of-bloodshed-frhof", "feat:boon-of-bountiful-health-frhof"]
    gs = [o["group"] for o in boons]
    assert [g for i, g in enumerate(gs) if i == 0 or g != gs[i - 1]] == ["epic-boon", "general", "origin"]


def test_sorted_by_name_then_source_inside_groups(catalog):
    for ruleset in ("mixed", "2014", "2024"):
        by_group: dict = {}
        for o in _feats(_opts(ruleset, catalog)):
            f = catalog.feats[o["id"][len("feat:"):]]
            by_group.setdefault(o["group"], []).append((f["name"], f["source"]))
        for keys in by_group.values():
            assert keys == sorted(keys)


def test_source_suffix_only_for_duplicate_names(catalog):
    def with_suffix(opts):
        return [o for o in _feats(opts) if o["label"].endswith(")") and " (" in o["label"]]
    mixed = _feats(_opts("mixed", catalog))
    suffixed = with_suffix(mixed)
    assert len(suffixed) == 92
    alert = [o["label"] for o in mixed if o["label"].startswith("Alert")]
    assert sorted(alert) == ["Alert (PHB)", "Alert (XPHB)"]
    assert with_suffix(_opts("2014", catalog)) == []
    assert with_suffix(_opts("2024", catalog)) == []
    assert with_suffix(_opts("2024", catalog, 19)) == []


def test_species_feat_options_grouped(catalog):
    r = resolve(_draft("2024", 1, {"id": "human-xphb"}), catalog)
    opts = next(c for c in r["choices"] if c["id"] == "species:human-xphb:feat-0")["options"]
    assert {o["group"] for o in opts} == {"origin"}
    names = [(catalog.feats[o["id"][5:]]["name"], catalog.feats[o["id"][5:]]["source"]) for o in opts]
    assert names == sorted(names)
