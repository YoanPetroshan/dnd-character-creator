from catalog.loader import load
from catalog.official_source import items_base_file, has_official, has_official_classes, has_official_spells


def test_load_returns_expected_counts():
    catalog = load()
    assert len(catalog.classes) == 12
    if has_official_classes():  # Slice 11b: +164 subclasses, +1089 features, +671 rows (script-verified)
        # +76 optional-feature records (11b.6), +173 XPHB class features (C1, script-verified)
        assert len(catalog.features) == 407 + 1089 + 76 + 173 + 38 + 2  # +38 XPHB EI/MM (C6c-1), +2 TCE Metamagic (G2)
        assert len(catalog.levels) == 290 + 671
        assert len(catalog.subclasses) == 12 + 164
    else:
        assert len(catalog.features) == 407
        assert len(catalog.levels) == 290
        assert len(catalog.subclasses) == 12
    # Bundled SRD counts for races/subraces/traits/backgrounds are exact —
    # byte-identical when official sourcebook data hasn't been fetched on
    # this machine. When it has (as on this dev machine), load() merges in
    # the wider official race/subrace/trait/background data, so these
    # become lower bounds instead.
    if has_official():
        assert len(catalog.races) >= 9
        assert len(catalog.subraces) >= 4
        assert len(catalog.traits) >= 38
        assert len(catalog.backgrounds) >= 100  # 1 SRD + ~135 official (Phase 4b Task 1)
        assert len(catalog.feats) > 250  # official-only, no SRD merge — 2014 SRD has no feats (Phase 4c-i Task 1)
    else:
        assert len(catalog.races) == 9
        assert len(catalog.subraces) == 4
        assert len(catalog.traits) == 38
        assert len(catalog.backgrounds) == 1
        assert len(catalog.feats) == 0  # no bundled SRD feats file at all — trivially empty, not a partial merge


def test_classes_indexed_by_srd_index():
    catalog = load()
    assert "fighter" in catalog.classes
    assert catalog.classes["fighter"]["name"] == "Fighter"
    assert catalog.classes["fighter"]["hit_die"] == 10


def test_class_level_row_returns_base_class_row_only():
    catalog = load()
    row = catalog.class_level_row("fighter", 1)
    assert row is not None
    assert row["level"] == 1
    assert "subclass" not in row


def test_class_level_row_excludes_subclass_rows_at_a_colliding_level():
    # Wizard's own level-2 row (arcane-tradition feature) and Evocation's
    # subclass-level-2 row (evocation-savant/sculpt-spells) both exist
    # with class.index == "wizard" and level == 2 — this is the exact
    # ambiguity this task fixes. class_level_row must return the base
    # row, never the subclass one.
    catalog = load()
    row = catalog.class_level_row("wizard", 2)
    assert row is not None
    assert "subclass" not in row
    assert any(f["index"] == "arcane-tradition" for f in row["features"])


def test_class_level_row_unknown_class_or_level_is_none():
    catalog = load()
    assert catalog.class_level_row("not-a-class", 1) is None
    assert catalog.class_level_row("fighter", 99) is None


def test_subclass_level_row_returns_the_subclass_specific_row():
    catalog = load()
    row = catalog.subclass_level_row("evocation", 2)
    assert row is not None
    assert row["level"] == 2
    assert any(f["index"] == "evocation-savant" for f in row["features"])


def test_subclass_level_row_unknown_subclass_or_level_is_none():
    catalog = load()
    assert catalog.subclass_level_row("not-a-subclass", 2) is None
    assert catalog.subclass_level_row("evocation", 99) is None


def test_subraces_of_returns_only_that_races_subraces():
    catalog = load()
    dwarf_subraces = catalog.subraces_of("dwarf")
    assert [s["index"] for s in dwarf_subraces] == ["hill-dwarf"]
    assert catalog.subraces_of("human") == []


def test_backgrounds_contains_the_bundled_srd_acolyte():
    # Previously named "..._contains_only_acolyte" — no longer accurate once
    # official sourcebook backgrounds are merged in (Phase 4b Task 1); the
    # one guarantee that still holds is that the bundled SRD "acolyte" id is
    # always present, official data or not.
    catalog = load()
    assert "acolyte" in catalog.backgrounds
    if not has_official():
        assert list(catalog.backgrounds.keys()) == ["acolyte"]


def test_items_indexed_by_srd_index_covers_all_categories():
    catalog = load()
    assert len(catalog.items) == 237 + 2 + (5 if items_base_file() else 0)  # Slice 11c: 5 sourcebook items; RPX4: +2 PHB gaming sets
    assert catalog.items["chain-mail"]["armor_category"] == "Heavy"
    assert catalog.items["longbow"]["weapon_category"] == "Martial"
    assert catalog.items["dungeoneers-pack"]["equipment_category"]["index"] == "adventuring-gear"


def test_spells_indexed_by_index():
    catalog = load()
    # 319 SRD spells; with the sourcebook spell files present, 936 in total (Slice 11a)
    assert len(catalog.spells) == (936 if has_official_spells() else 319)
    assert catalog.spells["fireball"]["name"] == "Fireball"
    assert catalog.spells["fireball"]["level"] == 3


def test_feats_indexed_by_source_qualified_index_official_only_no_srd_merge():
    # 2014 SRD has no feats mechanic at all, unlike races/subraces/traits/
    # backgrounds, so Catalog.feats has no bundled-file half of the merge —
    # it's populated purely from official sourcebook data (Phase 4c-i Task 1).
    catalog = load()
    if not has_official():
        assert catalog.feats == {}
        return
    assert "alert-phb" in catalog.feats
    assert catalog.feats["alert-phb"]["name"] == "Alert"
