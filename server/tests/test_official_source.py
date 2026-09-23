import pytest
# official_dir/has_official are imported FROM official_source (a
# re-export), not from chargen.sources directly — official_source.py is
# the one place that fixes sys.path so `chargen` (a sibling of server/,
# not a subpackage) is importable at all; importing chargen.sources
# directly here would fail with ModuleNotFoundError before that fix runs.
from catalog.official_source import official_dir, has_official, load_official_races

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


def test_loads_a_real_non_srd_race_with_a_source_qualified_id():
    races, subraces, traits_by_index = load_official_races(official_dir())
    aasimar_records = [r for r in races if r["name"] == "Aasimar"]
    assert len(aasimar_records) >= 1  # VGM, MPMM, DMG, XPHB reprints — several distinct records
    vgm_aasimar = next(r for r in aasimar_records if r["index"].endswith("-vgm"))
    assert vgm_aasimar["index"] == "aasimar-vgm"
    assert vgm_aasimar["speed"] == 30
    assert vgm_aasimar["ability_bonuses"] == [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 2}]


def test_srd_style_fields_present_and_correctly_shaped():
    races, subraces, traits_by_index = load_official_races(official_dir())
    for r in races[:20]:  # spot-check a slice, not all 144 — this is a shape check, not exhaustive
        assert "index" in r and "name" in r and "speed" in r
        assert isinstance(r.get("ability_bonuses", []), list)
        assert isinstance(r.get("languages", []), list)
        assert isinstance(r.get("traits", []), list)


def test_no_id_collides_with_a_bundled_srd_race_id():
    from catalog.loader import load
    catalog = load()
    # Bundled SRD ids have no source suffix at all (e.g. "dwarf"), while every
    # official id is source-qualified (e.g. "aasimar-vgm") — by construction
    # these two id spaces can never intersect. Compare against the raw SRD
    # file directly (not catalog.races) since loader.py's load() already
    # merges official races in by the time this test runs.
    import json
    from pathlib import Path
    srd_path = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd" / "5e-SRD-Races.json"
    with open(srd_path, encoding="utf-8") as f:
        srd_ids = {r["index"] for r in json.load(f)}
    official_races, _, _ = load_official_races(official_dir())
    official_ids = {r["index"] for r in official_races}
    assert srd_ids.isdisjoint(official_ids)
    # Sanity: the merged catalog really does contain both id spaces.
    assert srd_ids <= catalog.races.keys()
    assert official_ids <= catalog.races.keys()


def test_copy_based_records_are_skipped_not_crashed_on():
    # Confirm the loader doesn't raise on the whole real dataset, which is
    # known (from empirical grounding) to contain _copy/_mod records.
    races, subraces, traits_by_index = load_official_races(official_dir())
    assert len(races) > 100  # sanity: most of the ~160 real records survived


def test_loads_a_real_subrace_with_a_race_scoped_id():
    # Empirically confirmed: subrace (name, source) pairs are NOT globally
    # unique — e.g. "Ixalan"/PSX applies to both Goblin/PSZ and Vampire/PSZ,
    # and "Variant; Mark of Finding"/ERLW applies to both Half-Orc/PHB and
    # Human/PHB — so the subrace id must be scoped by its parent race's own
    # id, not just (name, source).
    races, subraces, traits_by_index = load_official_races(official_dir())
    fallen_records = [s for s in subraces if s["name"] == "Fallen"]
    assert len(fallen_records) >= 1
    fallen = next(s for s in fallen_records if s["index"].startswith("aasimar-vgm-"))
    assert fallen["race"]["index"] == "aasimar-vgm"
    assert fallen["ability_bonuses"] == [{"ability_score": {"index": "str", "name": "STR", "url": ""}, "bonus": 1}]


def test_subrace_records_missing_a_name_are_skipped_not_crashed_on():
    # Empirically confirmed: some subrace records (e.g. the Human/Half-Elf/
    # Half-Orc/Tiefling/Dragonborn PHB "placeholder" entries marking that a
    # race is already SRD-complete) have no "name" field at all — these are
    # not real selectable subraces and must be skipped, not crash the loader.
    races, subraces, traits_by_index = load_official_races(official_dir())
    assert all("name" in s for s in subraces)


def test_all_subraces_reference_a_race_that_was_actually_loaded():
    races, subraces, traits_by_index = load_official_races(official_dir())
    race_ids = {r["index"] for r in races}
    for s in subraces:
        assert s["race"]["index"] in race_ids
