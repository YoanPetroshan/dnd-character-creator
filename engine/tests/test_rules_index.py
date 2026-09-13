import json

import pytest

from engine.rules import index as rules_index


@pytest.fixture
def fake_json_dir(tmp_path):
    d = tmp_path / "JSON"
    d.mkdir()
    (d / "bestiary-xmm.json").write_text(json.dumps({
        "monster": [
            {"name": "Goblin Boss", "source": "XMM", "cr": "1",
             "ac": [17], "hp": {"average": 21}},
            {"name": "Goblin Warrior", "source": "XMM", "cr": "1/4",
             "ac": [15], "hp": {"average": 7}},
        ]
    }), encoding="utf-8")
    (d / "bestiary-xge.json").write_text(json.dumps({
        "monster": [
            {"name": "Tiny Servant", "source": "XGE", "cr": "1/8",
             "ac": [15], "hp": {"average": 10}},
            # Real shape from 5etools: "same as Dire Wolf, with these text
            # edits" — no ac/hp/actions of its own. Must be excluded.
            {"name": "Hound of Ill Omen", "source": "XGE",
             "_copy": {"name": "Dire Wolf", "source": "MM",
                       "_mod": {"*": {"mode": "replaceTxt"}}}},
        ]
    }), encoding="utf-8")
    (d / "trapshazards.json").write_text(json.dumps({
        "trap": [{"name": "Poison Darts", "source": "XDMG", "trapHazType": "MECH"}],
        "hazard": [{"name": "Brown Mold", "source": "XDMG"}],
    }), encoding="utf-8")
    (d / "spells-xphb.json").write_text(json.dumps({
        "spell": [{"name": "Charm Monster", "source": "XPHB", "level": 4,
                  "entries": ["2024 PHB text."]}]
    }), encoding="utf-8")
    (d / "spells-xge.json").write_text(json.dumps({
        "spell": [{"name": "Charm Monster", "source": "XGE", "level": 4,
                  "entries": ["2017 Xanathar's text — must lose to XPHB."]}]
    }), encoding="utf-8")
    return d


@pytest.fixture
def fake_books(tmp_path):
    root = tmp_path / "content"
    (root / "Books").mkdir(parents=True)
    (root / "Books" / "phb.md").write_text(
        "# Player's Handbook\n\n## Grappling\n\nRules text.\n\n## Shoving\n\nMore text.\n",
        encoding="utf-8",
    )
    return root


def test_indexes_monsters_by_name(fake_json_dir):
    entries = rules_index.index_json_sources(fake_json_dir)
    monsters = {e["name"] for e in entries if e["kind"] == "monster"}
    # Goblin Boss/Warrior from the primary MM 2025 bestiary, Tiny Servant
    # from the supplementary XGE file — merged into one "monster" kind.
    assert monsters == {"Goblin Boss", "Goblin Warrior", "Tiny Servant"}


def test_indexes_traps_and_hazards_separately(fake_json_dir):
    entries = rules_index.index_json_sources(fake_json_dir)
    kinds = {e["kind"] for e in entries}
    assert "trap" in kinds
    assert "hazard" in kinds


def test_missing_source_file_is_skipped_not_fatal(tmp_path):
    empty = tmp_path / "JSON"
    empty.mkdir()
    assert rules_index.index_json_sources(empty) == []


def test_skips_unresolved_copy_stubs(fake_json_dir):
    entries = rules_index.index_json_sources(fake_json_dir)
    names = {e["name"] for e in entries}
    assert "Hound of Ill Omen" not in names, (
        "a _copy stub has no ac/hp/actions of its own — indexing it would "
        "make lookup return a broken, half-empty stat block"
    )


def test_skipped_copy_stubs_are_reported(fake_json_dir):
    skipped: list[str] = []
    rules_index.index_json_sources(fake_json_dir, skipped=skipped)
    assert skipped == ["Hound of Ill Omen"]


def test_name_collision_resolves_to_the_earlier_listed_source(fake_json_dir):
    """spells-xphb.json (2024) is listed before spells-xge.json (2017) in
    JSON_SOURCES — both define "Charm Monster". find() returns whichever
    entry comes first in the index, so build order IS the priority order."""
    entries = rules_index.index_json_sources(fake_json_dir)
    charm_entries = [e for e in entries if e["name"] == "Charm Monster"]
    assert len(charm_entries) == 2
    assert charm_entries[0]["file"] == "spells-xphb.json"


def test_indexes_markdown_headings(fake_books):
    entries = rules_index.index_markdown_books(fake_books)
    names = {e["name"] for e in entries}
    assert "Grappling" in names
    assert "Shoving" in names
    assert all(e["kind"] == "rule" for e in entries)


def test_build_index_writes_and_reloads(fake_json_dir, fake_books, tmp_path):
    out = tmp_path / "index.json"
    data = rules_index.build_index(fake_json_dir, fake_books, out)
    assert out.exists()
    assert data["count"] == len(data["entries"])
    reloaded = rules_index.load_index(out)
    assert reloaded["count"] == data["count"]


def test_load_missing_index_returns_empty(tmp_path):
    assert rules_index.load_index(tmp_path / "nope.json") == {"entries": [], "count": 0}
