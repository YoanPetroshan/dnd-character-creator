"""Slice 11b.3: /api/catalog/class lists the visible subclasses of a class.

Totals are from a script over the raw 5etools class files (2026-10-09): a
subclass is visible under "2014" when it is not a 2024 one, under "mixed" when
it is not the 2024 half of a 2014/2024 twin pair, under "2024" when it is not
the 2014 half of a pair."""
import pytest

from catalog.official_source import has_official_classes
from engine.resolve import _subclass_visible

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"]
VISIBLE = {  # class -> (2014, mixed, 2024)
    "barbarian": (9, 10, 10), "bard": (8, 10, 10), "cleric": (19, 19, 19), "druid": (7, 8, 8),
    "fighter": (10, 10, 10), "monk": (10, 10, 10), "paladin": (9, 10, 10), "ranger": (8, 9, 9),
    "rogue": (9, 10, 10), "sorcerer": (9, 10, 10), "warlock": (9, 9, 9), "wizard": (13, 13, 13),
}


@pytest.fixture(scope="module")
def client():
    import app as app_module
    return app_module.app.test_client()


def _subs(client, cls, query=""):
    resp = client.get(f"/api/catalog/class/{cls}{query}")
    assert resp.status_code == 200
    return resp.get_json()["subclasses"]


def _ids(subs):
    return [s["index"] for s in subs]


@needs_classes
def test_warlock_2014_lists_nine_without_2024_records(client):
    subs = _subs(client, "warlock", "?ruleset=2014")
    ids = _ids(subs)
    assert len(ids) == 9 and not [i for i in ids if i.endswith("-xphb")]
    assert "hexblade-xge" in ids and "fiend" in ids


@needs_classes
def test_warlock_2024_and_mixed_choose_one_version_of_a_twin(client):
    ids = _ids(_subs(client, "warlock", "?ruleset=2024"))
    assert "fiend-xphb" in ids and "fiend" not in ids
    ids = _ids(_subs(client, "warlock", "?ruleset=mixed"))
    assert "fiend" in ids and "fiend-xphb" not in ids
    assert _ids(_subs(client, "warlock")) == ids  # mixed is the default


@needs_classes
def test_sources_srd_only_leaves_the_srd_subclass(client):
    assert _ids(_subs(client, "warlock", "?sources=srd")) == ["fiend"]
    assert _ids(_subs(client, "cleric", "?sources=srd")) == ["life"]


@needs_classes
def test_sources_filter_keeps_srd_and_the_listed_books(client):
    subs = _subs(client, "warlock", "?sources=xge")
    assert {s["source"] for s in subs} == {"SRD", "XGE"}
    assert {"fiend", "hexblade-xge", "celestial-xge"} <= set(_ids(subs))


@needs_classes
def test_include_adds_a_hidden_selection_and_flags_it(client):
    subs = _subs(client, "warlock", "?ruleset=2014&include=fiend-xphb")
    hidden = [s for s in subs if s.get("hidden")]
    assert [s["index"] for s in hidden] == ["fiend-xphb"]
    assert len(subs) == 10
    visible = _subs(client, "warlock", "?ruleset=2014&include=hexblade-xge")
    assert len(visible) == 9 and not any(s.get("hidden") for s in visible)
    # an id of another class or an unknown id is ignored
    assert len(_subs(client, "warlock", "?ruleset=2014&include=berserker")) == 9
    assert len(_subs(client, "warlock", "?ruleset=2014&include=nope")) == 9


@needs_classes
def test_items_carry_source_and_ruleset_and_srd_comes_first(client):
    subs = _subs(client, "warlock", "?ruleset=2014")
    assert subs[0] == {"index": "fiend", "name": "Fiend", "source": "SRD", "ruleset": "2014"}
    rest = [s["name"] for s in subs[1:]]
    assert rest == sorted(rest)
    hexblade = next(s for s in subs if s["index"] == "hexblade-xge")
    assert hexblade == {"index": "hexblade-xge", "name": "The Hexblade", "source": "XGE", "ruleset": "2014"}


@needs_classes
@pytest.mark.parametrize("cls", CLASSES)
def test_per_class_counts(client, cls):
    for ruleset, expected in zip(("2014", "mixed", "2024"), VISIBLE[cls]):
        assert len(_subs(client, cls, f"?ruleset={ruleset}")) == expected, (cls, ruleset)


@needs_classes
def test_totals_across_the_twelve_classes(client):
    for i, (ruleset, total) in enumerate((("2014", 120), ("mixed", 128), ("2024", 128))):
        assert sum(VISIBLE[c][i] for c in CLASSES) == total
        assert sum(len(_subs(client, c, f"?ruleset={ruleset}")) for c in CLASSES) == total


def test_other_class_fields_are_kept(client):
    body = client.get("/api/catalog/class/warlock").get_json()
    assert body["index"] == "warlock" and body["hit_die"] == 8
    assert body["subclassUnlockLevel"] == 1 and "levelFeatureCounts" in body
    assert client.get("/api/catalog/class/nope").status_code == 404


@needs_classes
def test_subclass_visible_uses_twins_sources_and_ruleset():
    from catalog.loader import load
    cat = load()
    fiend, fiend24, hexblade = (cat.subclasses[i] for i in ("fiend", "fiend-xphb", "hexblade-xge"))
    assert _subclass_visible(cat, fiend, [], "mixed") and not _subclass_visible(cat, fiend24, [], "mixed")
    assert _subclass_visible(cat, fiend24, [], "2024") and not _subclass_visible(cat, fiend, [], "2024")
    assert not _subclass_visible(cat, fiend24, [], "2014")
    assert _subclass_visible(cat, hexblade, [], "2024")  # no 2024 twin: stays pickable
    assert not _subclass_visible(cat, hexblade, ["phb"], "mixed")
    # the other version's book is excluded by `sources`: the remaining one stays offered
    assert _subclass_visible(cat, fiend24, ["xphb"], "mixed") is False  # SRD 'fiend' is always allowed, so mixed still prefers it
    assert _subclass_visible(cat, fiend, ["xphb"], "2024") is False


# Imported subclasses per book (script-verified, see test_subclass_import).
IMPORTED_BY_SOURCE = {
    "XPHB": 48, "XGE": 31, "PHB": 28, "TCE": 26, "FRHoF": 8, "SCAG": 6, "PSA": 5, "EGW": 3,
    "DMG": 2, "VRGR": 2, "FTD": 2, "BGG": 1, "PSK": 1, "DSotDQ": 1,
}


@needs_classes
def test_catalog_sources_count_subclass_books(client):
    import app as app_module
    cat = app_module._catalog
    shown = {s["id"]: s["count"] for s in client.get("/api/catalog").get_json()["sources"]}
    for src, n in IMPORTED_BY_SOURCE.items():
        others = sum(1 for coll in (cat.races, cat.subraces, cat.backgrounds, cat.feats)
                     for r in coll.values() if r.get("source") == src)
        assert shown[src] == others + n, src
