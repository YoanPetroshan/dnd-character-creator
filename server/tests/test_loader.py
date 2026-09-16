from catalog.loader import load


def test_load_returns_expected_counts():
    catalog = load()
    assert len(catalog.classes) == 12
    assert len(catalog.races) == 9
    assert len(catalog.subraces) == 4
    assert len(catalog.backgrounds) == 1
    assert len(catalog.traits) == 38
    assert len(catalog.features) == 407
    assert len(catalog.levels) == 290
    assert len(catalog.subclasses) == 12


def test_classes_indexed_by_srd_index():
    catalog = load()
    assert "fighter" in catalog.classes
    assert catalog.classes["fighter"]["name"] == "Fighter"
    assert catalog.classes["fighter"]["hit_die"] == 10


def test_level_row_returns_the_matching_class_and_level():
    catalog = load()
    row = catalog.level_row("fighter", 1)
    assert row is not None
    assert row["level"] == 1
    assert row["prof_bonus"] == 2
    feature_names = {f["name"] for f in row["features"]}
    assert "Fighting Style" in feature_names
    assert "Second Wind" in feature_names


def test_level_row_returns_none_for_unknown_class_or_level():
    catalog = load()
    assert catalog.level_row("not-a-class", 1) is None
    assert catalog.level_row("fighter", 99) is None


def test_subraces_of_returns_only_that_races_subraces():
    catalog = load()
    dwarf_subraces = catalog.subraces_of("dwarf")
    assert [s["index"] for s in dwarf_subraces] == ["hill-dwarf"]
    assert catalog.subraces_of("human") == []


def test_backgrounds_contains_only_acolyte():
    catalog = load()
    assert list(catalog.backgrounds.keys()) == ["acolyte"]
