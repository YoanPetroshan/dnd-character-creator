import json

import pytest

from engine.rules import lookup


INDEX = {
    "entries": [
        {"name": "Goblin Boss", "kind": "monster", "file": "bestiary-xmm.json",
         "key": "monster", "pos": 0, "source": "XMM"},
        {"name": "Goblin Warrior", "kind": "monster", "file": "bestiary-xmm.json",
         "key": "monster", "pos": 1, "source": "XMM"},
        {"name": "Bag of Holding", "kind": "item", "file": "items.json",
         "key": "item", "pos": 0, "source": "XDMG"},
        {"name": "Fireball", "kind": "spell", "file": "spells-xphb.json",
         "key": "spell", "pos": 0, "source": "XPHB"},
    ],
    "count": 4,
}


# Fixture for the find() fuzzy/substring regression tests (code review
# findings on lookup.py). Reproduces the real-corpus shape: a near-exact
# pluralization match ("Opportunity Attack(s)"), a short unrelated heading
# that is a substring of a longer query ("Attack" inside "Sneak Attack"),
# and a short unrelated heading that difflib scores deceptively high against
# a genuinely-relevant longer name ("Mapping" vs "Grappling Hook (2 GP)").
RULES_INDEX = {
    "entries": [
        {"name": "Opportunity Attacks", "kind": "rule", "file": "phb.md",
         "line": 1040, "source": "Player's Handbook (2024)"},
        {"name": "Attack", "kind": "rule", "file": "dmg.md",
         "line": 9284, "source": "Dungeon Master's Guide (2024)"},
        {"name": "Grappling Hook (2 GP)", "kind": "rule", "file": "phb.md",
         "line": 3148, "source": "Player's Handbook (2024)"},
        {"name": "Mapping", "kind": "rule", "file": "yawning.md",
         "line": 1, "source": "Tales from the Yawning Portal"},
    ],
    "count": 4,
}


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "bestiary-xmm.json").write_text(json.dumps({
        "monster": [
            {"name": "Goblin Boss", "source": "XMM", "cr": "1", "ac": [17],
             "hp": {"average": 21}, "str": 10, "dex": 15, "con": 12,
             "int": 10, "wis": 9, "cha": 10,
             "action": [{"name": "Scimitar",
                        "entries": ["{@atk mw} +4 to hit, {@damage 1d6+2} slashing."]}]},
            {"name": "Goblin Warrior", "source": "XMM", "cr": "1/4", "ac": [15],
             "hp": {"average": 7}},
        ]
    }), encoding="utf-8")
    (tmp_path / "items.json").write_text(json.dumps({
        "item": [{"name": "Bag of Holding", "source": "XDMG", "rarity": "uncommon",
                  "entries": ["Holds a lot. See {@variantrule Sphere|XPHB} for area rules."]}]
    }), encoding="utf-8")
    (tmp_path / "spells-xphb.json").write_text(json.dumps({
        "spell": [{"name": "Fireball", "source": "XPHB", "level": 3, "school": "V",
                  "entries": ["Each creature makes a Dexterity save, taking "
                              "{@damage 8d6} Fire damage on a failed save."]}]
    }), encoding="utf-8")
    (tmp_path / "loot.json").write_text(json.dumps({
        "individual": [
            {"name": "CR 0-4", "crMin": 0, "crMax": 4, "table": [{"min": 1, "max": 30}]},
            {"name": "CR 5-10", "crMin": 5, "crMax": 10, "table": []},
        ]
    }), encoding="utf-8")
    return tmp_path


def test_find_exact_match():
    e = lookup.find("Goblin Boss", index=INDEX)
    assert e["kind"] == "monster"
    assert e["pos"] == 0


def test_find_is_case_insensitive():
    assert lookup.find("goblin boss", index=INDEX)["name"] == "Goblin Boss"


def test_find_fuzzy_matches_close_name():
    assert lookup.find("Goblin Bos", index=INDEX)["name"] == "Goblin Boss"


def test_find_respects_kind_filter():
    assert lookup.find("Bag of Holding", kind="monster", index=INDEX) is None
    assert lookup.find("Bag of Holding", kind="item", index=INDEX) is not None


def test_find_unknown_returns_none():
    assert lookup.find("Tarrasque", index=INDEX) is None


def test_fetch_record_pulls_the_right_entry(data_dir):
    entry = lookup.find("Goblin Warrior", index=INDEX)
    rec = lookup.fetch_record(entry, data_dir)
    assert rec["name"] == "Goblin Warrior"
    assert rec["cr"] == "1/4"


def test_format_monster_includes_key_stats(data_dir):
    entry = lookup.find("Goblin Boss", index=INDEX)
    rec = lookup.fetch_record(entry, data_dir)
    out = lookup.format_monster(rec)
    assert "Goblin Boss" in out
    assert "AC" in out and "17" in out
    assert "HP" in out and "21" in out
    assert "CR 1" in out
    assert "Scimitar" in out


def test_format_monster_strips_5etools_markup(data_dir):
    entry = lookup.find("Goblin Boss", index=INDEX)
    rec = lookup.fetch_record(entry, data_dir)
    out = lookup.format_monster(rec)
    assert "{@" not in out
    assert "1d6+2" in out


def test_format_generic_includes_entries(data_dir):
    entry = lookup.find("Bag of Holding", index=INDEX)
    rec = lookup.fetch_record(entry, data_dir)
    out = lookup.format_generic(rec)
    assert "Bag of Holding" in out
    assert "Holds a lot." in out


def test_format_generic_strips_5etools_markup(data_dir):
    entry = lookup.find("Bag of Holding", index=INDEX)
    rec = lookup.fetch_record(entry, data_dir)
    out = lookup.format_generic(rec)
    assert "{@" not in out
    assert "Sphere" in out  # kept the display segment, dropped the |XPHB source tag


def test_spell_lookup_resolves_from_the_users_own_corpus(data_dir):
    entry = lookup.find("Fireball", kind="spell", index=INDEX)
    assert entry is not None
    rec = lookup.fetch_record(entry, data_dir)
    out = lookup.format_generic(rec)
    assert "8d6" in out
    assert "{@" not in out


@pytest.mark.parametrize("raw,expected", [
    ("{@damage 8d6} Fire damage", "8d6 Fire damage"),
    ("See {@variantrule Sphere|XPHB} for details", "See Sphere for details"),
    ("{@hazard burning|XPHB}", "burning"),
    ("no markup here", "no markup here"),
])
def test_strip_tags(raw, expected):
    assert lookup.strip_tags(raw) == expected


def test_loot_table_selects_by_cr(data_dir):
    table = lookup.loot_table(3, kind="individual", directory=data_dir)
    assert table["name"] == "CR 0-4"
    assert lookup.loot_table(7, kind="individual", directory=data_dir)["name"] == "CR 5-10"


def test_loot_table_out_of_range_returns_none(data_dir):
    assert lookup.loot_table(99, kind="individual", directory=data_dir) is None


# --- Code review regression tests ---------------------------------------
#
# Finding 1: _flatten's dict-name branch injected value["name"] raw, never
# through strip_tags — so action names like "Fire Breath {@recharge 5}"
# (confirmed on 24% of bestiary-xmm.json monsters, essentially every dragon)
# leaked literal {@...} markup into monster stat blocks.
def test_flatten_dict_name_strips_markup(tmp_path):
    (tmp_path / "bestiary-dragon.json").write_text(json.dumps({
        "monster": [
            {"name": "Adult Test Dragon", "source": "XMM", "cr": "17", "ac": [19],
             "hp": {"average": 195}, "str": 27, "dex": 10, "con": 25,
             "int": 16, "wis": 15, "cha": 24,
             "action": [{"name": "Fire Breath {@recharge 5}",
                        "entries": ["Each creature in the area takes "
                                    "{@damage 16d6} Fire damage."]}]},
        ]
    }), encoding="utf-8")
    entry = {"name": "Adult Test Dragon", "kind": "monster", "file": "bestiary-dragon.json",
             "key": "monster", "pos": 0, "source": "XMM"}
    rec = lookup.fetch_record(entry, tmp_path)
    out = lookup.format_monster(rec)
    assert "{@" not in out
    assert "Fire Breath" in out


# Finding 3: format_monster printed CR as a raw Python dict repr whenever a
# monster has a lair/variant CR (5etools represents that as
# {"cr": "...", "xpLair": ...} — confirmed on 7% of monsters across both
# bestiary files, including nearly every Adult/Ancient dragon).
def test_format_monster_unwraps_cr_dict(tmp_path):
    (tmp_path / "bestiary-lair.json").write_text(json.dumps({
        "monster": [
            {"name": "Ancient Test Dragon", "source": "XMM",
             "cr": {"cr": "24", "xpLair": 62000}, "ac": [22],
             "hp": {"average": 546}},
        ]
    }), encoding="utf-8")
    entry = {"name": "Ancient Test Dragon", "kind": "monster", "file": "bestiary-lair.json",
             "key": "monster", "pos": 0, "source": "XMM"}
    rec = lookup.fetch_record(entry, tmp_path)
    out = lookup.format_monster(rec)
    assert "CR 24" in out
    assert "xpLair" not in out
    assert "{'cr'" not in out


# Finding 2: the substring-containment tier added to rescue "Grappling" ran
# unconditionally before difflib and could win on any substring match no
# matter how short or unrelated, regressing common queries like
# "Opportunity Attack" and "Sneak Attack".
def test_find_high_confidence_fuzzy_match_is_not_overridden_by_substring():
    # "Opportunity Attack" vs "Opportunity Attacks" is a near-exact,
    # high-confidence difflib match (ratio ~0.97) and must win outright.
    e = lookup.find("Opportunity Attack", kind="rule", index=RULES_INDEX)
    assert e is not None
    assert e["name"] == "Opportunity Attacks"


def test_find_low_confidence_fuzzy_does_not_return_unrelated_short_match():
    # No "Sneak Attack" heading exists in the fixture (or the real corpus).
    # The short, unrelated "Attack" heading is a substring of the query, but
    # that must not be treated as a match — the honest answer is "not found".
    assert lookup.find("Sneak Attack", kind="rule", index=RULES_INDEX) is None


def test_find_rescues_low_confidence_fuzzy_with_substring_match():
    # difflib's best guess for "Grappling" is the unrelated "Mapping"
    # (ratio 0.75, higher than the genuinely relevant candidate). The
    # substring rescue must return "Grappling Hook (2 GP)" — never "Mapping".
    e = lookup.find("Grappling", kind="rule", index=RULES_INDEX)
    assert e is not None
    assert e["name"] == "Grappling Hook (2 GP)"
