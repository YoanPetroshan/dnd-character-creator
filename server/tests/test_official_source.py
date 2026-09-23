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


def test_ability_choice_race_gets_both_fixed_and_choice_envelopes():
    # Aetherborn (PSK): a fixed +2 CHA plus a SEPARATE choose-2-of-5 choice
    # for +1 each — confirmed against the real fetched data (2026-09-23) to
    # match this exact shape: {"cha": 2, "choose": {"from": [...], "count": 2}}.
    races, _, _ = load_official_races(official_dir())
    aetherborn = next(r for r in races if r["name"] == "Aetherborn")
    assert aetherborn["ability_bonuses"] == [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 2}]
    assert aetherborn["ability_bonus_options"]["choose"] == 2
    assert {o["ability_score"]["index"] for o in aetherborn["ability_bonus_options"]["from"]["options"]} == {"str", "dex", "con", "int", "wis"}


def test_ability_choice_envelope_matches_srd_shape_exactly():
    # Same envelope shape catalog/choices.py's build_choice_options already
    # knows how to consume for SRD's Half-Elf (Phase 3b) — option_type
    # "ability_bonus", one option per candidate ability, each worth +1.
    races, _, _ = load_official_races(official_dir())
    aetherborn = next(r for r in races if r["name"] == "Aetherborn")
    envelope = aetherborn["ability_bonus_options"]
    assert envelope["type"] == "ability_bonuses"
    assert envelope["from"]["option_set_type"] == "options_array"
    for option in envelope["from"]["options"]:
        assert option["option_type"] == "ability_bonus"
        assert option["bonus"] == 1
        assert set(option["ability_score"].keys()) == {"index", "name", "url"}


def test_race_with_no_ability_choice_gets_no_options_envelope():
    # Aasimar (VGM) is a plain fixed +2 CHA/+1 WIS, no "choose" sub-entry —
    # ability_bonus_options must stay None, not an empty/malformed dict.
    races, _, _ = load_official_races(official_dir())
    aasimar = next(r for r in races if r["index"] == "aasimar-vgm")
    assert aasimar["ability_bonus_options"] is None


def test_custom_lineage_amount_shape_is_not_silently_mishandled():
    # TCE's "Custom Lineage" uses {"from": [...], "amount": 2} instead of a
    # "count" key — a fundamentally different, more flexible ASI split (+2
    # to one ability OR +1 to two) that this task's simple choose-N-for-+1-
    # each envelope cannot represent. Confirmed empirically (2026-09-23)
    # this is the ONLY race-level entry with "choose" but no "count". Must
    # be skipped (None), not guessed at via a wrong default count.
    races, _, _ = load_official_races(official_dir())
    custom_lineage = next(r for r in races if r["name"] == "Custom Lineage")
    assert custom_lineage["ability_bonus_options"] is None
