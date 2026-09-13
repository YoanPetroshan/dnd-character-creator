"""Tests for chargen/catalog.py — query methods over the normalised SRD data.

All queries here run against the real 2014 5e-bits files under
chargen/data/srd/*.json (no fixtures), since Catalog.load() always reads
that real data regardless of the requested ruleset (see catalog.py's module
docstring for the ruleset-scheduling rationale).

Task 10 note: chargen.sources.official_dir() may genuinely have real data on
THIS machine (chargen/sync.py --official was actually run here, per the
plan's Decision log — outside the repo, gitignored). Tests that assert exact
SRD-only baseline counts (9 races, 1 background) must not depend on that
ambient machine state — they explicitly patch has_official() to False so
they pass identically whether or not this machine has ever run the official
fetch. Tests that specifically exercise the official merge use their own
small fixture dir instead (see the "official-data merge" section below).
"""

from unittest import mock

import pytest

from chargen import catalog as C
from chargen import rules as R
from chargen.catalog import Catalog


@pytest.fixture(autouse=True)
def _clear_catalog_cache():
    """Every test gets a clean module-level cache, so tests that monkeypatch
    _read_json (the caching test) don't leak a poisoned/mocked instance to
    later tests, and so no test's result depends on prior test order."""
    Catalog._clear_cache()
    yield
    Catalog._clear_cache()


@pytest.fixture(scope="module")
def catalog():
    # Isolated from ambient official data that may genuinely exist on this
    # machine (see module docstring) — this fixture always represents the
    # SRD-only baseline, regardless of what chargen.sources.official_dir()
    # holds on disk right now.
    with mock.patch.object(C, "has_official", return_value=False):
        Catalog._clear_cache()
        c = Catalog.load()
    return c


# ---------------------------------------------------------------------------
# races / subraces
# ---------------------------------------------------------------------------


def test_races_returns_all_nine_srd_races(catalog):
    races = catalog.races()
    assert len(races) == 9
    ids = {r.id for r in races}
    assert "dwarf" in ids and "human" in ids


def test_race_lookup_by_id(catalog):
    dwarf = catalog.race("dwarf")
    assert dwarf.name == "Dwarf"


def test_race_unknown_id_raises_keyerror_with_id_in_message(catalog):
    with pytest.raises(KeyError) as exc_info:
        catalog.race("nonexistent-id")
    assert "nonexistent-id" in str(exc_info.value)


def test_subraces_filtered_by_parent_race(catalog):
    dwarf_subraces = catalog.subraces("dwarf")
    assert [s.id for s in dwarf_subraces] == ["hill-dwarf"]
    # a race with no SRD subraces returns an empty list, not an error
    assert catalog.subraces("human") == []


# ---------------------------------------------------------------------------
# backgrounds
# ---------------------------------------------------------------------------


def test_backgrounds_returns_the_one_srd_background(catalog):
    backgrounds = catalog.backgrounds()
    assert [b.id for b in backgrounds] == ["acolyte"]


def test_background_unknown_id_raises_keyerror_with_id_in_message(catalog):
    with pytest.raises(KeyError) as exc_info:
        catalog.background("nonexistent-id")
    assert "nonexistent-id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# classes / subclasses / level rows
# ---------------------------------------------------------------------------


def test_classes_returns_all_twelve_srd_classes(catalog):
    classes = catalog.classes()
    assert len(classes) == 12
    ids = {c.id for c in classes}
    assert "wizard" in ids and "fighter" in ids


def test_class_unknown_id_raises_keyerror_with_id_in_message(catalog):
    with pytest.raises(KeyError) as exc_info:
        catalog.class_("nonexistent-id")
    assert "nonexistent-id" in str(exc_info.value)


def test_subclasses_wizard_has_school_of_evocation(catalog):
    subs = catalog.subclasses("wizard")
    assert {"id": "evocation", "name": "Evocation"} in subs


def test_subclasses_unknown_class_returns_empty_list(catalog):
    assert catalog.subclasses("nonexistent-id") == []


def test_level_row_wizard_5_has_prof_bonus_3(catalog):
    row = catalog.level_row("wizard", 5)
    assert row.level == 5
    assert row.proficiency_bonus == 3


def test_level_row_unknown_combination_raises_keyerror_naming_both(catalog):
    with pytest.raises(KeyError) as exc_info:
        catalog.level_row("wizard", 99)
    message = str(exc_info.value)
    assert "wizard" in message
    assert "99" in message


# ---------------------------------------------------------------------------
# spells
# ---------------------------------------------------------------------------


def test_spells_wizard_level_3_contains_fireball(catalog):
    results = catalog.spells(cls="Wizard", level=3)
    names = {s.name for s in results}
    assert "Fireball" in names


def test_spells_wizard_level_3_excludes_cure_wounds(catalog):
    # Verify against the real data first: Cure Wounds is genuinely not on
    # Wizard's class list in the SRD (Bard/Cleric/Druid/Paladin/Ranger only).
    all_spells = catalog.spells()
    cure_wounds = next(s for s in all_spells if s.name == "Cure Wounds")
    assert "Wizard" not in cure_wounds.classes

    results = catalog.spells(cls="Wizard", level=3)
    names = {s.name for s in results}
    assert "Cure Wounds" not in names


def test_spells_level_zero_is_a_real_filter_not_falsy_no_filter(catalog):
    cantrips = catalog.spells(level=0)
    assert len(cantrips) > 0
    assert all(s.level == 0 for s in cantrips)
    # confirm it's genuinely filtering, not silently returning everything
    assert len(cantrips) < len(catalog.spells())


def test_spells_school_filter_is_case_insensitive(catalog):
    lower = catalog.spells(school="evocation")
    proper = catalog.spells(school="Evocation")
    assert len(lower) == len(proper) > 0


def test_spells_search_is_case_insensitive_substring_on_name(catalog):
    # "fireball" (lowercase) matches both "Fireball" and "Delayed Blast
    # Fireball" — a genuine substring match, not a coincidence to hide.
    results = catalog.spells(search="fireball")
    assert {s.name for s in results} == {"Fireball", "Delayed Blast Fireball"}

    exact = catalog.spells(search="Fireball")
    assert {s.name for s in exact} == {s.name for s in results}


def test_spells_filters_compose_as_and_not_or(catalog):
    wizard_spells = catalog.spells(cls="Wizard")
    wizard_evocation = catalog.spells(cls="Wizard", school="Evocation")
    assert len(wizard_evocation) > 0
    assert set(s.id for s in wizard_evocation) < set(s.id for s in wizard_spells)
    assert all(s.school == "Evocation" for s in wizard_evocation)


# ---------------------------------------------------------------------------
# weapons
# ---------------------------------------------------------------------------


def test_weapons_no_filter_returns_all_37(catalog):
    assert len(catalog.weapons()) == 37


def test_weapons_category_simple_excludes_longsword(catalog):
    simple = catalog.weapons(category="simple")
    assert "Longsword" not in {w.name for w in simple}


def test_weapons_category_martial_includes_longsword(catalog):
    martial = catalog.weapons(category="martial")
    assert "Longsword" in {w.name for w in martial}


def test_weapons_category_matching_is_case_insensitive(catalog):
    lower = catalog.weapons(category="martial")
    proper = catalog.weapons(category="Martial")
    assert {w.id for w in lower} == {w.id for w in proper}
    assert len(lower) > 0


# ---------------------------------------------------------------------------
# armor
# ---------------------------------------------------------------------------


def test_armor_returns_twelve_entries_excluding_shield(catalog):
    entries = catalog.armor()
    assert len(entries) == 12
    assert all(e["category"] in {"light", "medium", "heavy"} for e in entries)
    assert not any(e["category"] == "shield" for e in entries)
    assert not any(e["name"] == "Shield" for e in entries)


def test_armor_entry_shape_feeds_rules_armor_class(catalog):
    leather = next(e for e in catalog.armor() if e["id"] == "leather-armor")
    ac = R.armor_class(dex_mod=3, armor=leather, shield=False)
    # Leather Armor: base_ac 11, light -> full dex bonus, uncapped.
    assert ac == 14

    plate = next(e for e in catalog.armor() if e["id"] == "plate-armor")
    ac_heavy = R.armor_class(dex_mod=3, armor=plate, shield=True)
    # Plate: base_ac 18, heavy -> no dex bonus; +2 for shield.
    assert ac_heavy == 20


# ---------------------------------------------------------------------------
# gear
# ---------------------------------------------------------------------------


def test_gear_covers_adventuring_gear_tools_and_mounts(catalog):
    items = catalog.gear()
    # 116 Adventuring Gear + 31 Tools + 40 Mounts and Vehicles = 187
    assert 150 < len(items) < 237
    assert all(item.quantity == 1 for item in items)


# ---------------------------------------------------------------------------
# starting_equipment
# ---------------------------------------------------------------------------


def test_starting_equipment_fighter_acolyte_is_acolytes_kit(catalog):
    # Real data check: Fighter's raw starting_equipment list is empty in the
    # SRD (Fighter's real kit lives in the choice-based
    # starting_equipment_options, out of scope for this task) — so the
    # combined result is exactly Acolyte's own starting equipment.
    items = catalog.starting_equipment("fighter", "acolyte")
    names = {i.name for i in items}
    assert names == {i.name for i in catalog.background("acolyte").starting_equipment}
    assert "Pouch" in names


def test_starting_equipment_concatenates_a_class_kit_with_the_backgrounds(catalog):
    """The other branch: Wizard's raw starting_equipment is NOT empty (a
    Spellbook), so the result must be the class's own items followed by the
    background's, not one silently replacing the other."""
    class_items = catalog._classes_raw_by_id["wizard"]["starting_equipment"]
    assert class_items, "fixture assumption: Wizard has a non-empty class kit"

    items = catalog.starting_equipment("wizard", "acolyte")
    names = [i.name for i in items]
    background_names = [i.name for i in catalog.background("acolyte").starting_equipment]
    assert names == ["Spellbook"] + background_names


def test_starting_equipment_unknown_class_raises_keyerror(catalog):
    with pytest.raises(KeyError):
        catalog.starting_equipment("nonexistent-id", "acolyte")


# ---------------------------------------------------------------------------
# ruleset scheduling / official-data merge
# ---------------------------------------------------------------------------


def test_load_always_loads_srd_baseline_regardless_of_ruleset(monkeypatch):
    monkeypatch.setattr(C, "has_official", lambda: False)
    catalog_2024 = Catalog.load(ruleset="2024")
    assert len(catalog_2024.races()) == 9
    assert catalog_2024.ruleset == "2024"


def test_merge_official_is_a_safe_noop_when_official_data_absent(catalog, monkeypatch):
    monkeypatch.setattr(C, "has_official", lambda: False)
    # Should not raise, should not change any query results.
    catalog._merge_official()
    assert len(catalog.races()) == 9


def test_no_official_dir_is_unchanged_regression(monkeypatch):
    """The no-official-data path — Catalog.load() must still return exactly
    the 9 SRD races and the 1 SRD background (Acolyte), unaffected by Task
    10's _merge_official() wiring. has_official() is explicitly forced to
    False here (rather than relying on ambient absence) because this
    machine may genuinely have real official data on disk from an actual
    `chargen.sync --official` run — this test's job is to prove the code
    path, not the ambient environment."""
    monkeypatch.setattr(C, "has_official", lambda: False)
    Catalog._clear_cache()
    c = Catalog.load(ruleset="no-official-regression")
    assert len(c.races()) == 9
    assert [b.id for b in c.backgrounds()] == ["acolyte"]


# ---------------------------------------------------------------------------
# official-data merge, real wiring (Task 10) — small hand-written fixture
# files, not the real network-fetched catalog.
# ---------------------------------------------------------------------------

_FIXTURE_RACES_JSON = {
    "race": [
        {"name": "Dwarf", "source": "PHB", "ability": [{"con": 2}],
         "size": ["M"], "speed": 25, "entries": []},
        {"name": "Elf", "source": "XPHB", "edition": "one",
         "size": ["M"], "speed": 30, "entries": []},
        # _copy-based record — must be skipped, not merged as a blank race.
        {"name": "Amonkhet", "source": "PSA",
         "_copy": {"name": "Variant", "source": "PHB", "raceName": "Human"}},
    ],
    "subrace": [
        {"name": "Hill", "source": "PHB", "raceName": "Dwarf", "raceSource": "PHB",
         "ability": [{"wis": 1}], "entries": []},
    ],
}

_FIXTURE_BACKGROUNDS_JSON = {
    "background": [
        {"name": "Sage", "source": "XPHB", "edition": "one",
         "skillProficiencies": [{"arcana": True, "history": True}]},
    ],
}


@pytest.fixture()
def official_fixture_dir(tmp_path, monkeypatch):
    """Populate a scratch official_dir() with small hand-written fixtures
    and point chargen.catalog.official_dir() (and has_official()) at it —
    never the real network-fetched catalog."""
    import json

    d = tmp_path / "official"
    d.mkdir()
    (d / "races.json").write_text(json.dumps(_FIXTURE_RACES_JSON))
    (d / "backgrounds.json").write_text(json.dumps(_FIXTURE_BACKGROUNDS_JSON))

    monkeypatch.setattr(C, "official_dir", lambda: d)
    monkeypatch.setattr(C, "has_official", lambda: True)
    return d


def test_merge_official_widens_races_with_source_qualified_ids(official_fixture_dir):
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-races")

    ids = {r.id for r in c.races()}
    # Original 9 SRD races still present, unqualified.
    assert "dwarf" in ids
    assert "human" in ids
    # New fixture races, source-qualified, additive alongside SRD's "dwarf".
    assert "dwarf-phb" in ids
    assert "elf-xphb" in ids
    assert len(c.races()) == 9 + 2

    dwarf_phb = c.race("dwarf-phb")
    assert dwarf_phb.ruleset == "2014"
    assert dwarf_phb.source == "PHB"

    elf_xphb = c.race("elf-xphb")
    assert elf_xphb.ruleset == "2024"
    assert elf_xphb.source == "XPHB"


def test_merge_official_skips_copy_based_race(official_fixture_dir):
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-copy-skip")
    ids = {r.id for r in c.races()}
    assert not any(i.startswith("amonkhet") for i in ids)
    assert len(c.races()) == 9 + 2  # Amonkhet's _copy record excluded


def test_merge_official_subrace_linked_to_qualified_parent_race(official_fixture_dir):
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-subrace")
    hill_subraces = c.subraces("dwarf-phb")
    assert len(hill_subraces) == 1
    assert hill_subraces[0].name == "Hill Dwarf"
    assert hill_subraces[0].parent_race_id == "dwarf-phb"


def test_merge_official_widens_backgrounds_with_correct_ruleset(official_fixture_dir):
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-backgrounds")

    ids = {b.id for b in c.backgrounds()}
    assert "acolyte" in ids  # original SRD background untouched
    assert "sage-xphb" in ids
    assert len(c.backgrounds()) == 1 + 1

    sage = c.background("sage-xphb")
    assert sage.ruleset == "2024"
    assert set(sage.skill_proficiencies) == {"Arcana", "History"}


def test_merge_official_race_by_id_lookup_rebuilt(official_fixture_dir):
    """_race_by_id is built in __init__ BEFORE _merge_official() runs — if
    it isn't rebuilt afterward, race()/background() lookups on newly merged
    official entries would raise KeyError even though races()/backgrounds()
    list them."""
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-by-id")
    # Would raise KeyError if _race_by_id / _background_by_id were stale.
    assert c.race("dwarf-phb").name == "Dwarf"
    assert c.background("sage-xphb").name == "Sage"


def test_merge_official_attaches_subraces_to_their_parent_race_field(
        official_fixture_dir):
    """The bug this pins: `Race.subraces` is the field the HTTP API
    serialises and builder.html reads to decide whether to offer a subrace
    dropdown, and `race_from_5etools` hardcodes it empty. The separate
    `catalog.subraces(race_id)` query DID find the merged official subraces,
    which is why this went unnoticed — the field and the query disagreed."""
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-subrace-field")

    dwarf_phb = c.race("dwarf-phb")
    assert [s.name for s in dwarf_phb.subraces] == ["Hill Dwarf"]
    # The field and the query method must now agree, for every race.
    for race in c.races():
        assert [s.id for s in race.subraces] == [s.id for s in c.subraces(race.id)]
    # Nothing is stranded: every merged subrace hangs off exactly one race.
    assert sum(len(r.subraces) for r in c.races()) == len(c._subraces)


def test_merge_official_keeps_the_srd_races_own_subraces(official_fixture_dir):
    """Attaching the official ones must not overwrite the four SRD races
    that already had theirs."""
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-srd-subraces-kept")
    assert [s.name for s in c.race("dwarf").subraces] == ["Hill Dwarf"]
    assert [s.name for s in c.race("elf").subraces] == ["High Elf"]


def test_srd_only_races_still_carry_their_subraces(catalog):
    """The SRD baseline attached subraces at construction time; the merge-time
    attachment must not regress that on a machine with no official data."""
    assert sum(len(r.subraces) for r in catalog.races()) == 4
    assert [s.name for s in catalog.race("dwarf").subraces] == ["Hill Dwarf"]


def test_race_by_id_returns_the_subrace_attached_objects(official_fixture_dir):
    """Race is frozen, so attachment replaces the objects — _race_by_id must
    be rebuilt from the replacements, not left pointing at the originals."""
    Catalog._clear_cache()
    c = Catalog.load(ruleset="official-fixture-attach-by-id")
    assert c.race("dwarf-phb") is next(r for r in c.races() if r.id == "dwarf-phb")
    assert c.race("dwarf-phb").subraces


# ---------------------------------------------------------------------------
# caching
# ---------------------------------------------------------------------------


def test_second_load_with_same_ruleset_does_not_re_read_disk(monkeypatch):
    calls = []
    real_read_json = C._read_json

    def spy(path):
        calls.append(path)
        return real_read_json(path)

    monkeypatch.setattr(C, "_read_json", spy)

    Catalog.load(ruleset="2014-cache-test")
    first_call_count = len(calls)
    assert first_call_count > 0

    Catalog.load(ruleset="2014-cache-test")
    assert len(calls) == first_call_count  # no additional reads


def test_different_rulesets_each_get_their_own_cache_entry(monkeypatch):
    calls = []
    real_read_json = C._read_json

    def spy(path):
        calls.append(path)
        return real_read_json(path)

    monkeypatch.setattr(C, "_read_json", spy)

    Catalog.load(ruleset="ruleset-a")
    after_first = len(calls)
    Catalog.load(ruleset="ruleset-b")
    assert len(calls) > after_first  # a different ruleset key does read again
