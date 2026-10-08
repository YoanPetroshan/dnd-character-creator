import pytest
# official_dir/has_official are imported FROM official_source (a
# re-export), not from chargen.sources directly — official_source.py is
# the one place that fixes sys.path so `chargen` (a sibling of server/,
# not a subpackage) is importable at all; importing chargen.sources
# directly here would fail with ModuleNotFoundError before that fix runs.
from catalog.official_source import (
    official_dir, has_official, load_official_races, load_official_backgrounds, load_official_feats,
)

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


# --- Task 3: fixed skill/tool/weapon/armor proficiency grants -------------
#
# Real-data shapes confirmed empirically (2026-09-23) against
# /Users/yoanpetrov/.claude/dnd/.data/official/races.json:
#   skillProficiencies -> Aetherborn (PSK) -> [{"intimidation": True}]
#   toolProficiencies  -> Naga (PSA)       -> [{"poisoner's kit": True}]
#   weaponProficiencies-> Dwarf (PHB)      -> [{"battleaxe|phb": True, ...}]
#   armorProficiencies -> Hobgoblin (VGM)  -> [{"light": True}]
# Choice-shaped entries ("choose": {...}, "any": N, "anyArtisansTool": N)
# never have value True, so they're naturally excluded by an `is True` check.


def test_fixed_skill_proficiency_lands_on_a_synthetic_trait():
    races, _, traits_by_index = load_official_races(official_dir())
    aetherborn = next(r for r in races if r["name"] == "Aetherborn")
    skill_traits = [
        traits_by_index[t["index"]] for t in aetherborn["traits"]
        if any(p["index"] == "skill-intimidation" for p in traits_by_index[t["index"]].get("proficiencies", []))
    ]
    assert len(skill_traits) == 1
    # The grant lands on the trait whose own prose actually describes it
    # ("Menacing": "You have proficiency in the {@skill Intimidation}
    # skill.") — not an arbitrary trait like "Age".
    assert skill_traits[0]["name"] == "Menacing"


def test_fixed_skill_proficiency_flows_through_resolve_into_the_sheet():
    # Proves the "zero-touch reuse" claim end-to-end for skills: resolve.py's
    # existing trait-proficiency-scanning code (engine/resolve.py ~line 957)
    # already reads trait.get("proficiencies", []) filtered by "skill-" and
    # folds it into sheet.proficiencies.skills, exactly like SRD's own Elf
    # "Keen Senses" trait already does — no resolve.py changes needed.
    from catalog.loader import load
    from engine.resolve import resolve

    catalog = load()
    draft = {
        "name": "Test Aetherborn", "sources": ["psk"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "aetherborn-psk", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 15, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 8}},
        "equipment": {"added": [], "skipped": False}, "details": {},
    }
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert "skill-intimidation" in resolution["sheet"]["proficiencies"]["skills"]


def test_fixed_tool_proficiency_lands_on_a_synthetic_trait_with_apostrophe_stripped():
    # Naga (PSA)'s "Poison Affinity" grants proficiency with the poisoner's
    # kit — id must match catalog items' own "poisoners-kit" (apostrophe
    # stripped, space -> hyphen), and the display name should read
    # "Poisoner's Kit" (title case, apostrophe preserved) not "Poisoner'S
    # Kit" (what a naive str.title() call would wrongly produce).
    races, _, traits_by_index = load_official_races(official_dir())
    naga = next(r for r in races if r["name"] == "Naga")
    all_profs = [p for t in naga["traits"] for p in traits_by_index[t["index"]].get("proficiencies", [])]
    tool_profs = [p for p in all_profs if p["index"] == "poisoners-kit"]
    assert len(tool_profs) == 1
    assert tool_profs[0]["name"] == "Poisoner's Kit"


def test_fixed_weapon_proficiency_strips_source_suffix_and_pluralizes():
    # Dwarf (PHB)'s "Dwarven Combat Training" grants battleaxe/handaxe/
    # light hammer/warhammer proficiency. Raw ids carry a "|phb" source
    # suffix that must be stripped, and the resulting ids must be
    # PLURALIZED to match the id convention the BUNDLED SRD data's own
    # identical trait already uses (chargen/data/srd/5e-SRD-Traits.json's
    # "dwarven-combat-training" trait: battleaxes/handaxes/light-hammers/
    # warhammers) — a DIFFERENT, separate id namespace from catalog.items'
    # own SINGULAR equipment ids ("battleaxe").
    races, _, traits_by_index = load_official_races(official_dir())
    dwarf = next(r for r in races if r["name"] == "Dwarf" and r.get("source") == "PHB")
    all_profs = [p for t in dwarf["traits"] for p in traits_by_index[t["index"]].get("proficiencies", [])]
    weapon_ids = {p["index"] for p in all_profs if p["index"] in {"battleaxes", "handaxes", "light-hammers", "warhammers"}}
    assert weapon_ids == {"battleaxes", "handaxes", "light-hammers", "warhammers"}


def test_light_crossbow_weapon_id_matches_resolve_pys_recognized_convention():
    # Ground: 5etools' "light crossbow|phb" must convert to the SAME id
    # engine/resolve.py's _categorize_proficiency recognizes via its own
    # _SPECIFIC_WEAPON_PROFICIENCY_IDS set ("crossbows-light"), not the
    # naive pluralized form ("light-crossbows") the generic _pluralize
    # path would otherwise produce — confirmed mismatched during Task 3's
    # review. No real fetched race happens to grant this weapon (checked
    # empirically), so this calls the conversion function directly with a
    # synthetic weaponProficiencies envelope in the exact raw shape Step 1
    # of this task's own docstring confirms 5etools uses.
    from catalog.official_source import _proficiencies_from_5etools
    race_raw = {"weaponProficiencies": [{"light crossbow|phb": True}]}
    profs = _proficiencies_from_5etools(race_raw)
    assert profs == [{"index": "crossbows-light", "name": "Crossbows light", "url": ""}]


def test_fixed_armor_proficiency_gets_the_dash_armor_suffix():
    # Hobgoblin (VGM)'s "Martial Training" grants light armor proficiency —
    # raw key is the bare category "light", converted id must match the
    # SRD class-proficiency convention ("light-armor", not "light").
    races, _, traits_by_index = load_official_races(official_dir())
    hobgoblin = next(r for r in races if r["name"] == "Hobgoblin" and r.get("source") == "VGM")
    all_profs = [p for t in hobgoblin["traits"] for p in traits_by_index[t["index"]].get("proficiencies", [])]
    assert any(p["index"] == "light-armor" for p in all_profs)


def test_choice_shaped_skill_proficiency_produces_no_fixed_grant():
    # Centaur (GGR/MPMM) uses {"choose": {"from": [...]}} — a player CHOICE,
    # not a fixed grant. Must NOT show up as a fixed proficiency entry on
    # any synthetic trait (that's Task 4's job, not this task's).
    races, _, traits_by_index = load_official_races(official_dir())
    centaur = next(r for r in races if r["name"] == "Centaur")
    all_profs = [p for t in centaur["traits"] for p in traits_by_index[t["index"]].get("proficiencies", [])]
    skill_indexes = {p["index"] for p in all_profs if p["index"].startswith("skill-")}
    assert skill_indexes == set()


def test_subrace_fixed_weapon_proficiency_lands_on_a_racial_trait():
    # Drow (PHB), a subrace of Elf (PHB), grants rapier/shortsword/hand
    # crossbow proficiency via "Drow Weapon Training" — subraces need the
    # exact same conversion+attachment treatment as races, onto their own
    # racial_traits (not the parent race's traits).
    _, subraces, traits_by_index = load_official_races(official_dir())
    drow = next(s for s in subraces if s["name"] == "Drow" and s["race"]["index"] == "elf-phb")
    all_profs = [p for t in drow["racial_traits"] for p in traits_by_index[t["index"]].get("proficiencies", [])]
    weapon_ids = {p["index"] for p in all_profs}
    assert {"rapiers", "shortswords", "hand-crossbows"} <= weapon_ids


# --- Task 4: skill/tool proficiency CHOICES, including the "any N" wildcard
#
# Real-data shapes confirmed empirically (2026-09-24) against
# /Users/yoanpetrov/.claude/dnd/.data/official/races.json:
#   enumerated list -> Centaur (GGR)     -> skillProficiencies [{"choose": {"from": [...]}}] (no "count" -> choose 1)
#   enumerated list -> Dwarf (PHB)       -> toolProficiencies  [{"choose": {"from": ["smith's tools", ...]}}]
#   any N wildcard  -> Hexblood (VRGR)   -> skillProficiencies [{"any": 2}]
#   any N wildcard  -> Autognome (AAG)   -> toolProficiencies  [{"any": 2}]
#   any artisan's tool -> Dwarf (Kaladesh, PSK) -> toolProficiencies [{"anyArtisansTool": 2}]
#   any musical instrument -> Satyr (MOT) -> toolProficiencies [{"anyMusicalInstrument": 1}]
#   both skill AND tool choices on ONE race -> Warforged (EFA) -> skillProficiencies [{"any": 1}], toolProficiencies [{"any": 1}]
# Confirmed empirically that no real entry ever mixes two choice-shapes (or
# a fixed True grant and a choice-shape) within the same skillProficiencies/
# toolProficiencies dict — so at most one skill-choice and one tool-choice
# envelope exist per race/subrace.


def test_enumerated_skill_choice_becomes_an_options_array_envelope_on_a_trait():
    races, _, traits_by_index = load_official_races(official_dir())
    centaur = next(r for r in races if r["name"] == "Centaur" and r.get("source") == "GGR")
    choice_traits = [
        traits_by_index[t["index"]] for t in centaur["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    # No "count" key in the raw data -> defaults to choose 1 (empirically the
    # only shape absent "count" ever takes for this field, unlike the
    # ability_bonus_options "amount" ambiguity from Task 2).
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "options_array"
    ids = {o["item"]["index"] for o in envelope["from"]["options"]}
    assert ids == {"skill-animal-handling", "skill-medicine", "skill-nature", "skill-survival"}


def test_enumerated_tool_choice_matches_catalog_items_ids():
    races, _, traits_by_index = load_official_races(official_dir())
    dwarf = next(r for r in races if r["name"] == "Dwarf" and r.get("source") == "PHB")
    choice_traits = [
        traits_by_index[t["index"]] for t in dwarf["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    assert envelope["choose"] == 1
    ids = {o["item"]["index"] for o in envelope["from"]["options"]}
    assert ids == {"smiths-tools", "brewers-supplies", "masons-tools"}
    names = {o["item"]["name"] for o in envelope["from"]["options"]}
    assert "Smith's Tools" in names  # apostrophe-safe title case, not "Smith'S Tools"


def test_any_n_skill_wildcard_uses_the_any_skill_option_set_type():
    races, _, traits_by_index = load_official_races(official_dir())
    hexblood = next(r for r in races if r["name"] == "Hexblood" and r.get("source") == "VRGR")
    choice_traits = [
        traits_by_index[t["index"]] for t in hexblood["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    assert envelope["choose"] == 2
    assert envelope["from"] == {"option_set_type": "any_skill"}


def test_any_n_tool_wildcard_uses_the_any_tool_option_set_type():
    races, _, traits_by_index = load_official_races(official_dir())
    autognome = next(r for r in races if r["name"] == "Autognome" and r.get("source") == "AAG")
    choice_traits = [
        traits_by_index[t["index"]] for t in autognome["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    assert envelope["choose"] == 2
    assert envelope["from"] == {"option_set_type": "any_tool"}


def test_any_artisans_tool_wildcard_narrows_by_tool_category():
    races, _, traits_by_index = load_official_races(official_dir())
    dwarf_kaladesh = next(r for r in races if r["name"] == "Dwarf (Kaladesh)" and r.get("source") == "PSK")
    choice_traits = [
        traits_by_index[t["index"]] for t in dwarf_kaladesh["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    assert envelope["choose"] == 2
    assert envelope["from"] == {"option_set_type": "any_tool", "tool_category": "Artisan's Tools"}


def test_any_musical_instrument_wildcard_narrows_by_tool_category():
    races, _, traits_by_index = load_official_races(official_dir())
    satyr = next(r for r in races if r["name"] == "Satyr" and r.get("source") == "MOT")
    choice_traits = [
        traits_by_index[t["index"]] for t in satyr["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    assert envelope["choose"] == 1
    assert envelope["from"] == {"option_set_type": "any_tool", "tool_category": "Musical Instrument"}


def test_race_with_both_a_skill_and_a_tool_choice_gets_two_separate_choice_traits():
    # Warforged (EFA)'s "Specialized Design" trait text grants BOTH "one
    # skill proficiency" and "one tool proficiency of your choice" as two
    # independent choices — SRD's own trait-level proficiency_choices shape
    # is a single dict per trait (unlike the class-level list-of-envelopes
    # shape), so these must land on two distinct synthetic traits, not
    # collide as one.
    races, _, traits_by_index = load_official_races(official_dir())
    warforged = next(r for r in races if r["name"] == "Warforged" and r.get("source") == "EFA")
    choice_traits = [
        traits_by_index[t["index"]] for t in warforged["traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 2
    set_types = {t["proficiency_choices"]["from"]["option_set_type"] for t in choice_traits}
    assert set_types == {"any_skill", "any_tool"}


def test_choice_shaped_proficiency_does_not_also_produce_a_fixed_grant():
    # A CHOICE must never show up as a fixed proficiency entry too (that's
    # Task 3's job, for `granted is True` entries only).
    races, _, traits_by_index = load_official_races(official_dir())
    hexblood = next(r for r in races if r["name"] == "Hexblood" and r.get("source") == "VRGR")
    all_profs = [p for t in hexblood["traits"] for p in traits_by_index[t["index"]].get("proficiencies", [])]
    assert all_profs == []


def test_subrace_any_n_choice_lands_on_a_racial_trait():
    # Mark of Making (ERLW), a subrace of Human (PHB), grants "choose 1 of
    # any artisan's tool" — subraces need the exact same choice-envelope
    # treatment as races, onto their own racial_traits. (Subrace records
    # don't carry their own "source" field — Task 1's known deferred
    # finding — so match by name alone; empirically unique in real data.)
    _, subraces, traits_by_index = load_official_races(official_dir())
    mark_of_making = next(s for s in subraces if s["name"] == "Mark of Making")
    choice_traits = [
        traits_by_index[t["index"]] for t in mark_of_making["racial_traits"]
        if traits_by_index[t["index"]].get("proficiency_choices")
    ]
    assert len(choice_traits) == 1
    envelope = choice_traits[0]["proficiency_choices"]
    assert envelope["choose"] == 1
    assert envelope["from"] == {"option_set_type": "any_tool", "tool_category": "Artisan's Tools"}


def test_race_damage_modifiers_and_condition_immunities_are_plain_string_lists():
    # Aasimar/VGM: fixed necrotic/radiant resistance, no immune/
    # vulnerable/conditionImmune of its own. Autognome/AAG: disease
    # condition immunity. Both confirmed against the real fetched
    # races.json (2026-09-24).
    races, _, _ = load_official_races(official_dir())
    aasimar_vgm = next(r for r in races if r["index"] == "aasimar-vgm")
    assert aasimar_vgm["resist"] == ["necrotic", "radiant"]
    assert aasimar_vgm["immune"] == []
    assert aasimar_vgm["vulnerable"] == []
    assert aasimar_vgm["condition_immune"] == []

    autognome = next(r for r in races if r["index"] == "autognome-aag")
    assert autognome["condition_immune"] == ["disease"]


def test_choice_shaped_resistance_is_filtered_out_not_mis_modeled():
    # Dragonborn/PHB's `resist` entry is {"choose": {"from": [...]}} — a
    # choice tied to draconic ancestry, not a fixed damage type.
    # Resolving that choice is out of scope for this pass-through
    # conversion (see _damage_modifiers_from_5etools' docstring); the
    # entry must be dropped, not coerced into a string or left to crash.
    races, _, _ = load_official_races(official_dir())
    dragonborn_phb = next(r for r in races if r["index"] == "dragonborn-phb")
    assert dragonborn_phb["resist"] == []


def test_subrace_damage_modifiers_are_independent_of_the_parent_race():
    # Stout Halfling/PHB grants poison resistance; the parent Halfling/PHB
    # race does not (confirmed against the real fetched races.json,
    # 2026-09-24) — subraces carry their own resist/immune/vulnerable/
    # condition_immune fields, read independently by
    # engine.resolve._species_damage_modifiers.
    races, subraces, _ = load_official_races(official_dir())
    halfling_phb = next(r for r in races if r["index"] == "halfling-phb")
    assert halfling_phb["resist"] == []
    stout = next(s for s in subraces if s["index"] == "halfling-phb-stout-phb")
    assert stout["resist"] == ["poison"]


def test_race_with_no_named_entries_but_a_fixed_grant_gets_a_dedicated_trait():
    # Defensive path: empirically NO real race/subrace hits this (all 66
    # with any proficiency field have a matching named entries item — see
    # module docstring), but the conversion must not silently drop a fixed
    # grant if a race ever has one with zero named entries.
    from catalog.official_source import _race_from_5etools

    raw = {
        "name": "Test Race", "source": "TEST", "size": ["M"],
        "entries": [],  # no named entries at all
        "skillProficiencies": [{"intimidation": True}],
    }
    traits_by_index = {}
    race = _race_from_5etools(raw, traits_by_index)
    assert len(race["traits"]) == 1
    trait = traits_by_index[race["traits"][0]["index"]]
    assert trait["name"] == "Automatic Proficiencies"
    assert trait["proficiencies"] == [{"index": "skill-intimidation", "name": "Skill: Intimidation", "url": ""}]


def test_innate_spells_mixed_at_will_and_daily_frequencies():
    # Yuan-ti Pureblood/VGM: level 1 "innate": {"1": ["animal friendship"]}
    # (a plain list -> at-will, confirmed against the real rules text) and
    # level 3 {"daily": {"1": ["suggestion"]}} (-> 1/day), fixed "cha"
    # ability (confirmed against the real fetched races.json, 2026-09-24).
    races, _, _ = load_official_races(official_dir())
    yti = next(r for r in races if r["index"] == "yuan-ti-pureblood-vgm")
    grants = {g["name"]: g for g in yti["innate_spells"]}
    assert grants["Animal Friendship"]["level"] == 1
    assert grants["Animal Friendship"]["uses"] == "at-will"
    assert grants["Animal Friendship"]["ability"] == "CHA"
    assert grants["Animal Friendship"]["variant"] is None
    assert grants["Suggestion"]["level"] == 3
    assert grants["Suggestion"]["uses"] == "1/day"


def test_innate_spells_choice_shaped_ability_is_preserved_as_a_candidate_list():
    # Aarakocra/MPMM: {"innate": {"3": ["gust of wind"]}, "ability":
    # {"choose": ["int", "wis", "cha"]}} — the MAJORITY real shape
    # (confirmed empirically, 2026-09-24), not resolved to a single
    # ability (no new choice-resolution machinery, same scope line Task 5
    # drew for choice-shaped resistances) but not dropped either.
    races, _, _ = load_official_races(official_dir())
    aarakocra = next(r for r in races if r["index"] == "aarakocra-mpmm")
    grants = aarakocra["innate_spells"]
    assert len(grants) == 1
    assert grants[0]["name"] == "Gust Of Wind"
    assert grants[0]["spell_id"] == "gust-of-wind"
    assert grants[0]["level"] == 3
    assert grants[0]["uses"] == "at-will"
    assert grants[0]["ability"] == {"choose": ["INT", "WIS", "CHA"]}


def test_innate_spells_with_a_non_srd_reference_still_gets_a_usable_spell_id_guess():
    # Triton/VGM's level-5 innate spell is "wall of water|xge" — a real
    # spell this project has no bundled DATA for (confirmed empirically,
    # 2026-09-24, part of Task 6's re-measured Step 2 finding: 9/102 real
    # innate references don't resolve against catalog.spells). official_source.py
    # itself does NOT touch the catalog (no Catalog import, by design —
    # see module docstring) — it just strips the "|xge" source decoration
    # and slugs the clean name; engine.resolve._species_innate_spells is
    # what actually attempts catalog resolution and degrades gracefully.
    races, _, _ = load_official_races(official_dir())
    triton_vgm = next(r for r in races if r["index"] == "triton-vgm")
    grants = {g["name"]: g for g in triton_vgm["innate_spells"]}
    assert grants["Wall Of Water"]["spell_id"] == "wall-of-water"
    assert grants["Wall Of Water"]["level"] == 5


def test_innate_spells_multi_entry_race_tags_each_grant_with_its_variant_name():
    # Tiefling/XPHB folds three mutually-exclusive 2024-style "fiendish
    # legacy" lineage options (Abyssal/Chthonic/Infernal) into ONE race
    # record's additionalSpells list, each entry carrying a "name" tag —
    # confirmed empirically (2026-09-24) that no subrace records exist for
    # these, so silently flattening all three together would misrepresent
    # the character as having every legacy's spells simultaneously. Each
    # grant is tagged with its variant instead, so it's never dropped OR
    # mis-modeled as unconditional.
    races, _, _ = load_official_races(official_dir())
    tiefling_xphb = next(r for r in races if r["index"] == "tiefling-xphb")
    variants = {g["variant"] for g in tiefling_xphb["innate_spells"]}
    assert variants == {"Abyssal", "Chthonic", "Infernal"}
    abyssal_grants = [g["name"] for g in tiefling_xphb["innate_spells"] if g["variant"] == "Abyssal"]
    assert sorted(abyssal_grants) == ["Hold Person", "Ray Of Sickness"]


def test_a_race_with_no_additional_spells_gets_an_empty_innate_spells_list():
    races, _, _ = load_official_races(official_dir())
    dwarf_phb = next(r for r in races if r["index"] == "dwarf-phb")
    assert dwarf_phb["innate_spells"] == []


def test_innate_spells_rest_wrapper_is_handled_the_same_as_daily_not_dropped():
    # Mark of Scribing/ERLW (a subrace of Gnome/PHB) is the ONE real
    # record in the whole dataset whose innate entry uses the "rest"
    # wrapper key instead of "daily" — level 1:
    # {"rest": {"1": ["comprehend languages"]}} (confirmed against the
    # real fetched races.json, 2026-09-24, found by code review after an
    # earlier pass's docstring wrongly claimed the wrapper was "ALWAYS
    # daily"). Comprehend Languages is a real, resolvable 2014 SRD spell
    # — before this fix it was silently dropped (fell through to the
    # ("at-will", []) fallback) with zero trace on the sheet. Level 3's
    # "magic mouth" uses the ordinary "daily" wrapper on the SAME record,
    # confirming both shapes coexist and are both preserved.
    races, subraces, _ = load_official_races(official_dir())
    scribing = next(s for s in subraces if s["index"] == "gnome-phb-mark-of-scribing-erlw")
    grants = {g["name"]: g for g in scribing["innate_spells"]}
    assert grants["Comprehend Languages"]["level"] == 1
    assert grants["Comprehend Languages"]["uses"] == "1/day"
    assert grants["Comprehend Languages"]["spell_id"] == "comprehend-languages"
    assert grants["Magic Mouth"]["level"] == 3
    assert grants["Magic Mouth"]["uses"] == "1/day"


def test_subrace_innate_spells_are_independent_of_the_parent_race():
    # Duergar/MTF (subrace of Dwarf/PHB) grants enlarge/reduce (3rd level)
    # and invisibility (5th level), both 1/day, fixed "int" ability — the
    # parent Dwarf/PHB race has no additionalSpells of its own (confirmed
    # against the real fetched races.json, 2026-09-24).
    races, subraces, _ = load_official_races(official_dir())
    dwarf_phb = next(r for r in races if r["index"] == "dwarf-phb")
    assert dwarf_phb["innate_spells"] == []
    duergar = next(s for s in subraces if s["index"] == "dwarf-phb-duergar-mtf")
    grants = {g["name"]: g for g in duergar["innate_spells"]}
    assert grants["Enlarge/Reduce"]["spell_id"] == "enlarge-reduce"
    assert grants["Enlarge/Reduce"]["level"] == 3
    assert grants["Invisibility"]["level"] == 5
    assert all(g["ability"] == "INT" for g in duergar["innate_spells"])


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 1) — scaffolding + fixed skill/tool
# proficiencies only. Backgrounds carry proficiencies/languages/equipment as
# DIRECT top-level fields in both the bundled SRD shape and the real 5etools
# shape (confirmed empirically, Step 1) — unlike races, no separate
# synthetic-trait indirection is needed here.
# ---------------------------------------------------------------------------

def test_loads_a_real_non_srd_background_with_a_source_qualified_id():
    # Acolyte is reprinted in both PHB and XPHB in the real fetched data
    # (confirmed empirically, Step 1) — the XPHB reprint must get its own
    # source-qualified id, distinct from the bundled SRD "acolyte" id.
    backgrounds = load_official_backgrounds(official_dir())
    acolyte_records = [b for b in backgrounds if b["name"] == "Acolyte"]
    assert len(acolyte_records) >= 1
    xphb_acolyte = next(b for b in acolyte_records if b["index"].endswith("-xphb"))
    assert xphb_acolyte["index"] == "acolyte-xphb"


def test_no_id_collides_with_the_bundled_srd_background_id():
    # Bundled SRD ids have no source suffix at all (e.g. "acolyte"), while
    # every official id is source-qualified (e.g. "acolyte-xphb") — by
    # construction these two id spaces can never intersect. Compare against
    # the raw SRD file directly (not catalog.backgrounds), same reasoning as
    # the equivalent race test above: loader.py's load() already merges
    # official backgrounds in, so reading catalog.backgrounds here would
    # trivially "pass" even if ids collided (the dict merge would just
    # silently drop one side).
    import json
    from pathlib import Path
    from catalog.loader import load
    srd_path = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd" / "5e-SRD-Backgrounds.json"
    with open(srd_path, encoding="utf-8") as f:
        srd_ids = {b["index"] for b in json.load(f)}
    official_backgrounds = load_official_backgrounds(official_dir())
    official_ids = {b["index"] for b in official_backgrounds}
    assert srd_ids.isdisjoint(official_ids)
    # Sanity: the merged catalog really does contain both id spaces.
    catalog = load()
    assert srd_ids <= catalog.backgrounds.keys()
    assert official_ids <= catalog.backgrounds.keys()


def test_background_copy_based_records_are_skipped_not_crashed_on():
    # Confirm the loader doesn't raise on the whole real dataset (known,
    # from empirical grounding, to contain _copy records), and that most of
    # the 135 real non-copy records survive.
    backgrounds = load_official_backgrounds(official_dir())
    assert len(backgrounds) > 100


def test_fixed_skill_and_tool_proficiency_land_directly_on_the_background_dict():
    # Aberrant Heir/EFA grants History + Intimidation skills and Disguise
    # Kit tool proficiency, all as fixed (non-choice) grants — confirmed
    # empirically against the real fetched backgrounds.json (Step 1).
    backgrounds = load_official_backgrounds(official_dir())
    aberrant_heir = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    prof_ids = {p["index"] for p in aberrant_heir["starting_proficiencies"]}
    assert {"skill-history", "skill-intimidation"} <= prof_ids
    assert "disguise-kit" in prof_ids


def test_background_srd_style_fields_present_and_correctly_shaped():
    backgrounds = load_official_backgrounds(official_dir())
    for b in backgrounds[:20]:  # spot-check a slice, not all 135 — this is a shape check
        assert "index" in b and "name" in b and "source" in b
        assert isinstance(b.get("starting_proficiencies", []), list)
        assert isinstance(b.get("languages", []), list)
        assert isinstance(b.get("starting_equipment", []), list)
        assert isinstance(b.get("starting_equipment_options", []), list)
        assert isinstance(b.get("feats", []), list)
        assert isinstance(b.get("feature"), dict)


def test_missing_official_data_returns_empty_list_not_crash(tmp_path):
    assert load_official_backgrounds(tmp_path) == []


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 2) — skill/tool proficiency CHOICES, including
# the "any N" wildcard. Real shapes grounded against the fetched
# backgrounds.json (2026-09-26) via the brief's own grounding command.
#
# Two genuine mismatches from races (Phase 4a Task 3/4), found empirically
# and NOT present in the brief's description, are handled here:
#
# 1. Backgrounds use an "anyGamingSet": N wildcard key races never carry
#    (17 real backgrounds, e.g. Noble/PHB, Criminal/PHB, Soldier/PHB) —
#    races' own _tool_choice_envelope_from_5etools only recognizes
#    "any"/"anyArtisansTool"/"anyMusicalInstrument", so reusing it verbatim
#    would silently drop this background's whole tool choice. Resolved via
#    the SAME any_tool option_set_type + tool_category filter mechanism
#    already used for the other two wildcards, pointed at reference_data's
#    existing "Gaming Sets" category — no changes to choices.py needed.
# 2. One background (Vizier/PSA) carries TWO wildcard keys at once
#    ({"anyArtisansTool": 1, "anyMusicalInstrument": 1}) — races never do
#    this (confirmed by that module's own docstring), and the race-side
#    function returns after the FIRST match, silently dropping the second.
#    Resolved by returning a list of every matching wildcard envelope,
#    which the plan's own `starting_proficiency_choices: list[dict]` field
#    already accommodates.
# 3. Most REAL enumerated tool `choose.from` lists (9 of 10 found) mix
#    literal tool names with generic category placeholders ("musical
#    instrument", "gaming set", and even the literal string
#    "anyArtisansTool" used as a from-list entry, e.g. Prismari
#    Student/SCC) — NOT a shape races ever had. Treating these as literal
#    tool names would invent fake, non-selectable options ("Musical
#    Instrument"). Resolved by expanding each recognized category token
#    into every real concrete tool of that category from reference_data,
#    so the resulting envelope is still a plain options_array — no new
#    envelope shape, per the brief.
# ---------------------------------------------------------------------------

def test_enumerated_tool_choice_on_a_background_becomes_an_options_array_choice():
    # Archaeologist/ToA: {"choose": {"from": ["navigator's tools", "cartographer's tools"]}}
    # — the one real enumerated tool choice made ONLY of literal tool names.
    backgrounds = load_official_backgrounds(official_dir())
    archaeologist_toa = next(b for b in backgrounds if b["index"] == "archaeologist-toa")
    choices = archaeologist_toa["starting_proficiency_choices"]
    assert len(choices) == 1
    envelope = choices[0]
    assert envelope["choose"] == 1
    options = envelope["from"]["options"]
    option_ids = {o["item"]["index"] for o in options}
    assert option_ids == {"navigators-tools", "cartographers-tools"}


def test_enumerated_skill_choice_coexists_with_a_fixed_skill_grant():
    # Cloistered Scholar/SCAG: {"history": True, "choose": {"from": ["arcana", "nature", "religion"]}}
    # — a fixed grant and a choice on the SAME raw entry. The fixed "history"
    # skill must land on starting_proficiencies (Task 1's job), and ONLY the
    # choice portion becomes a starting_proficiency_choices envelope.
    backgrounds = load_official_backgrounds(official_dir())
    cloistered_scholar = next(b for b in backgrounds if b["index"] == "cloistered-scholar-scag")
    fixed_ids = {p["index"] for p in cloistered_scholar["starting_proficiencies"]}
    assert "skill-history" in fixed_ids
    choices = cloistered_scholar["starting_proficiency_choices"]
    assert len(choices) == 1
    envelope = choices[0]
    assert envelope["choose"] == 1
    option_ids = {o["item"]["index"] for o in envelope["from"]["options"]}
    assert option_ids == {"skill-arcana", "skill-nature", "skill-religion"}


def test_any_n_skill_wildcard_choice_reuses_the_any_skill_option_set_type():
    # Custom Background/PHB: {"any": 2} — no enumerated list at all.
    backgrounds = load_official_backgrounds(official_dir())
    custom_bg = next(b for b in backgrounds if b["index"] == "custom-background-phb")
    choices = custom_bg["starting_proficiency_choices"]
    assert len(choices) == 1
    envelope = choices[0]
    assert envelope["choose"] == 2
    assert envelope["from"]["option_set_type"] == "any_skill"


def test_any_gaming_set_wildcard_tool_choice_is_a_new_shape_not_seen_on_races():
    # Noble/PHB: {"anyGamingSet": 1} — races never carry this key; confirms
    # it's resolved via any_tool + tool_category "Gaming Sets" all the same.
    backgrounds = load_official_backgrounds(official_dir())
    noble = next(b for b in backgrounds if b["index"] == "noble-phb")
    choices = noble["starting_proficiency_choices"]
    assert len(choices) == 1
    envelope = choices[0]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "any_tool"
    assert envelope["from"]["tool_category"] == "Gaming Sets"


def test_background_with_both_a_skill_and_a_tool_choice_gets_two_envelopes():
    # Inheritor/SCAG: skill choose{arcana,history,religion} AND tool
    # choose{"musical instrument","gaming set"} (the latter all generic
    # category placeholders — none are literal tool names).
    backgrounds = load_official_backgrounds(official_dir())
    inheritor = next(b for b in backgrounds if b["index"] == "inheritor-scag")
    choices = inheritor["starting_proficiency_choices"]
    assert len(choices) == 2
    skill_envelopes = [c for c in choices if c["from"].get("option_set_type") == "options_array"
                        and any(o["item"]["index"].startswith("skill-") for o in c["from"]["options"])]
    tool_envelopes = [c for c in choices if c not in skill_envelopes]
    assert len(skill_envelopes) == 1
    assert {o["item"]["index"] for o in skill_envelopes[0]["from"]["options"]} == {
        "skill-arcana", "skill-history", "skill-religion",
    }
    assert len(tool_envelopes) == 1
    tool_option_ids = {o["item"]["index"] for o in tool_envelopes[0]["from"]["options"]}
    # Expanded from the two generic category placeholders into every real
    # concrete tool of those categories — never a fake "Musical Instrument"
    # or "Gaming Set" option.
    assert "dice-set" in tool_option_ids and "playing-card-set" in tool_option_ids
    assert "lute" in tool_option_ids and "bagpipes" in tool_option_ids
    assert "musical-instrument" not in tool_option_ids
    assert "gaming-set" not in tool_option_ids


def test_a_background_with_two_simultaneous_any_wildcards_gets_both():
    # Vizier/PSA: {"anyArtisansTool": 1, "anyMusicalInstrument": 1} — races'
    # own envelope-building function returns after the FIRST match and would
    # silently drop the second; this must produce TWO envelopes.
    backgrounds = load_official_backgrounds(official_dir())
    vizier = next(b for b in backgrounds if b["index"] == "vizier-psa")
    choices = vizier["starting_proficiency_choices"]
    assert len(choices) == 2
    categories = {c["from"]["tool_category"] for c in choices}
    assert categories == {"Artisan's Tools", "Musical Instrument"}
    assert all(c["choose"] == 1 and c["from"]["option_set_type"] == "any_tool" for c in choices)


def test_background_with_neither_skill_nor_tool_choice_gets_an_empty_list():
    # Aberrant Heir/EFA (used by the fixed-proficiency test above) grants
    # only fixed skills/tools, no choice at all.
    backgrounds = load_official_backgrounds(official_dir())
    aberrant_heir = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    assert aberrant_heir["starting_proficiency_choices"] == []


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 3) — fixed and choice LANGUAGE grants, converted
# from languageProficiencies into bg["languages"] (fixed, SRD-shaped) and
# bg["language_options"] (a Choice envelope). Real shapes grounded against
# the fetched backgrounds.json (2026-09-26) via the brief's own dump
# command; see _language_grants_from_5etools' own docstring for the full
# empirical grounding, including a disclosed, known data-fidelity gap on
# exactly 1 of 56 real records (Feylost/WBtW) that the brief's three claimed
# shapes didn't anticipate.
# ---------------------------------------------------------------------------

def test_fixed_only_language_grant_has_no_choice_offered():
    # Rune Carver/BGG: {"giant": True} — a fixed grant, no choice at all
    # (confirmed empirically, 2026-09-26, the ONLY real record whose
    # languageProficiencies is a single fixed-only entry).
    backgrounds = load_official_backgrounds(official_dir())
    rune_carver = next(b for b in backgrounds if b["index"] == "rune-carver-bgg")
    assert rune_carver["languages"] == [{"index": "giant", "name": "Giant", "url": ""}]
    assert rune_carver["language_options"] is None


def test_any_standard_wildcard_reuses_the_resource_list_mechanism():
    # Athlete/MOT: {"anyStandard": 1} — the common wildcard-only shape (46
    # of 56 real records). Must source EVERY language via the SAME
    # resource_list mechanism SRD's own bundled Acolyte already uses —
    # option count matches len(reference_data.LANGUAGES) exactly, and no
    # new catalog/choices.py code is needed for this to resolve.
    from catalog import reference_data
    from catalog.choices import build_choice_options
    backgrounds = load_official_backgrounds(official_dir())
    athlete = next(b for b in backgrounds if b["index"] == "athlete-mot")
    assert athlete["languages"] == []
    envelope = athlete["language_options"]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "resource_list"
    options = build_choice_options(envelope["from"])
    assert len(options) == len(reference_data.LANGUAGES)


def test_enumerated_named_list_language_choice_with_other_handled_sanely():
    # Boros Legionnaire/GGR: {"choose": {"from": ["celestial", "draconic",
    # "goblin", "other"]}} — an enumerated choice with a literal "other"
    # entry (4 of 8 real choose.from lists carry one), no anyStandard on
    # the same entry at all.
    backgrounds = load_official_backgrounds(official_dir())
    boros = next(b for b in backgrounds if b["index"] == "boros-legionnaire-ggr")
    assert boros["languages"] == []
    envelope = boros["language_options"]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "options_array"
    option_ids = {o["item"]["index"] for o in envelope["from"]["options"]}
    assert option_ids == {"celestial", "draconic", "goblin", "other"}
    other_option = next(o for o in envelope["from"]["options"] if o["item"]["index"] == "other")
    assert other_option["item"]["name"] == "Other"


def test_fixed_grant_combined_with_a_separate_any_standard_entry():
    # Clan Crafter/SCAG: [{"dwarvish": True}, {"anyStandard": 1}] — a fixed
    # grant and a wildcard choice as TWO SEPARATE outer-list entries.
    # CORRECTED by Finding 2 of the final whole-branch review (2026-09-27):
    # this used to assert the additive reading (fixed Dwarvish AND a free
    # wildcard pick), matching this module's PREVIOUS docstring claim for
    # this exact record — that claim was wrong. Clan Crafter's real
    # published "Languages:" text is "Dwarvish or one of your choice if
    # you already speak Dwarvish": a single grant, conditionally
    # substituted, not an additional pick stacked on top. Only the fixed
    # Dwarvish grant is kept; no language_options envelope is offered at
    # all (see test_fixed_grant_combined_with_any_standard_on_the_same_entry
    # below for the genuinely-additive same-entry shape, Giant Foundling,
    # which is unaffected by this correction).
    backgrounds = load_official_backgrounds(official_dir())
    clan_crafter = next(b for b in backgrounds if b["index"] == "clan-crafter-scag")
    assert clan_crafter["languages"] == [{"index": "dwarvish", "name": "Dwarvish", "url": ""}]
    assert clan_crafter["language_options"] is None


def test_fixed_grant_combined_with_any_standard_on_the_same_entry():
    # Giant Foundling/BGG: [{"giant": True, "anyStandard": 1}] — a fixed
    # grant and a wildcard choice combined on the SAME single dict entry
    # (as opposed to Clan Crafter's two separate entries above) — both
    # must still be produced correctly.
    backgrounds = load_official_backgrounds(official_dir())
    giant_foundling = next(b for b in backgrounds if b["index"] == "giant-foundling-bgg")
    assert giant_foundling["languages"] == [{"index": "giant", "name": "Giant", "url": ""}]
    envelope = giant_foundling["language_options"]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "resource_list"


def test_any_standard_combined_with_a_named_list_on_the_same_entry_is_additive():
    # Haunted One/VRGR: {"anyStandard": 1, "choose": {"from": [8 exotic
    # languages]}} on the SAME entry — a FOURTH real shape the brief's
    # three claimed shapes didn't describe (found during this task, see
    # _language_grants_from_5etools' own docstring for the full empirical
    # grounding). This background's real published "Languages:" text
    # ("Choose two, one of which must be Abyssal, Celestial, ... or
    # Undercommon") confirms the ADDITIVE reading this function applies:
    # total choose count = anyStandard (1) + the list choice's own count
    # (1, defaulted) = 2, sourced via the same resource_list mechanism as
    # a plain wildcard (the flat Choice model can't express the "at least
    # one from the list" sub-constraint either way — disclosed, not a bug
    # this task can fix).
    backgrounds = load_official_backgrounds(official_dir())
    haunted_one = next(b for b in backgrounds if b["index"] == "haunted-one-vrgr")
    assert haunted_one["languages"] == []
    envelope = haunted_one["language_options"]
    assert envelope["choose"] == 2
    assert envelope["from"]["option_set_type"] == "resource_list"


def test_feylost_known_disclosed_language_fidelity_gap():
    # Feylost/WBtW: {"anyStandard": 1, "choose": {"from": ["elvish",
    # "gnomish", "goblin", "sylvan"]}} — the SAME combined shape as Haunted
    # One above, but Feylost's real published text ("One of your choice of
    # Elvish, Gnomish, Goblin, or Sylvan") wants choose:1 from exactly
    # those 4 languages, NOT choose:2 from all 16. This test pins the
    # CURRENT, disclosed behavior (additive, matching Haunted One's rule
    # uniformly) rather than silently guessing a per-background special
    # case — see _language_grants_from_5etools' docstring and the Task 3
    # report for the full disclosure. If a future task special-cases this
    # background, update this test to match the new, more-faithful
    # behavior rather than deleting the coverage.
    backgrounds = load_official_backgrounds(official_dir())
    feylost = next(b for b in backgrounds if b["index"] == "feylost-wbtw")
    assert feylost["languages"] == []
    envelope = feylost["language_options"]
    assert envelope["choose"] == 2  # real text wants 1 — known, disclosed gap
    assert envelope["from"]["option_set_type"] == "resource_list"  # real text wants a 4-item options_array


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 4) — the 2024-style ability-score-improvement
# choice. Real shape re-confirmed empirically (2026-09-26) against the
# fetched backgrounds.json: every one of the 60 real records with an
# `ability` field has EXACTLY 2 entries, both `{"choose": {"weighted":
# {"from": [3 abilities], "weights": [...]}}}` — weights always either
# [2, 1] (the split option: +2 to one of 3, +1 to a DIFFERENT one of the
# remaining 2) or [1, 1, 1] (the flat option: +1 to all three), from-pool
# size always 3, and the two entries' `from` lists always identical
# (zero exceptions). This is ONE universal mechanic with a per-background
# 3-ability pool, not a per-background varying shape — flattened here into
# up to 7 concrete, individually-selectable "bundle" options (6 ordered
# split combinations, P(3,2), plus 1 flat combination), matching how
# catalog/choices.py's existing "multiple" option type already bundles
# multiple sub-items (there: counted_reference equipment; here:
# ability_bonus) into one selectable option.
# ---------------------------------------------------------------------------

def test_background_ability_choice_offers_all_split_and_flat_combinations():
    # Aberrant Heir/EFA: STR/CON/CHA pool, confirmed against the real
    # fetched data above. 6 split combinations (3 choices of which ability
    # gets +2, times 2 remaining choices of which OTHER ability gets +1)
    # plus exactly 1 flat combination (all three +1, no further choice) —
    # 7 total, re-derived here, not just trusted from the plan's own memory.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    envelope = bg["ability_bonus_options"]
    assert envelope["choose"] == 1
    assert envelope["type"] == "ability_bonuses"
    assert envelope["from"]["option_set_type"] == "options_array"
    options = envelope["from"]["options"]
    assert len(options) == 7  # 6 split combinations + 1 flat combination


def test_background_ability_choice_options_are_multiple_bundles_of_ability_bonus_items():
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    options = bg["ability_bonus_options"]["from"]["options"]
    split_options = [o for o in options if len(o["items"]) == 2]
    flat_options = [o for o in options if len(o["items"]) == 3]
    assert len(split_options) == 6
    assert len(flat_options) == 1
    for opt in options:
        assert opt["option_type"] == "multiple"
        for item in opt["items"]:
            assert item["option_type"] == "ability_bonus"
            assert item["ability_score"]["index"] in {"str", "con", "cha"}


def test_background_ability_choice_split_combinations_are_all_distinct_ordered_pairs():
    # Every one of the 6 split options must be a distinct (high, low) pair
    # from the 3-ability pool — e.g. "STR +2, CON +1" is a DIFFERENT option
    # from "CON +2, STR +1", since a different ability gets the +2.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    options = bg["ability_bonus_options"]["from"]["options"]
    split_pairs = set()
    for opt in options:
        if len(opt["items"]) != 2:
            continue
        high = next(i for i in opt["items"] if i["bonus"] == 2)
        low = next(i for i in opt["items"] if i["bonus"] == 1)
        split_pairs.add((high["ability_score"]["index"], low["ability_score"]["index"]))
    assert split_pairs == {
        ("str", "con"), ("str", "cha"),
        ("con", "str"), ("con", "cha"),
        ("cha", "str"), ("cha", "con"),
    }


def test_background_ability_choice_flat_combination_is_plus_one_to_all_three():
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["name"] == "Aberrant Heir")
    options = bg["ability_bonus_options"]["from"]["options"]
    flat = next(o for o in options if len(o["items"]) == 3)
    assert {i["ability_score"]["index"] for i in flat["items"]} == {"str", "con", "cha"}
    assert all(i["bonus"] == 1 for i in flat["items"])


def test_background_with_no_ability_field_gets_no_options_envelope():
    # A background with no ability-score entries at all must stay a clean
    # None, not an empty/malformed dict — mirrors the race-side
    # test_race_with_no_ability_choice_gets_no_options_envelope precedent.
    backgrounds = load_official_backgrounds(official_dir())
    no_ability_bgs = [b for b in backgrounds if b["ability_bonus_options"] is None]
    assert len(no_ability_bgs) > 0  # sanity: not every background has the field


def test_all_60_real_ability_field_backgrounds_get_a_7_option_envelope():
    # Exhaustive check, not just the single Aberrant Heir spot-check above —
    # confirms the "universal mechanic" claim holds for every real record,
    # not just the one this task's tests happen to spot-check.
    backgrounds = load_official_backgrounds(official_dir())
    with_envelope = [b for b in backgrounds if b["ability_bonus_options"] is not None]
    assert len(with_envelope) == 60
    for bg in with_envelope:
        options = bg["ability_bonus_options"]["from"]["options"]
        assert len(options) == 7, bg["name"]


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 5) — the starting equipment PACKAGE CHOICE
# (A or B). Real shape grounded (2026-09-26) against the fetched
# backgrounds.json via the brief's own dump command, then verified
# EXHAUSTIVELY over all 135 real records (the brief's own "startingEquipment
# is a list with exactly one entry" assumption does not hold — see below).
#
# `startingEquipment` is a LIST of entries, not always length 1: 75/135 real
# records (e.g. Anthropologist/ToA) carry ONLY a `"_"`-keyed entry (fixed
# equipment, no package choice) and correctly produce NO envelope here — see
# test_background_with_only_fixed_equipment_gets_no_choice_envelope below.
# Key casing varies: lowercase `a`/`b` (42 records) or uppercase `A`/`B` (34
# records, 2024-era XPHB-sourced) — both handled. One record (Charlatan/PHB)
# has FOUR options (`a`/`b`/`c`/`d`). One record (Athlete/MOT) carries TWO
# independent a/b-keyed entries in its startingEquipment list — each must
# become its OWN "choose 1 of 2" envelope, not merged into one "choose 1 of
# 4" envelope (that would misrepresent two independent choices as one).
#
# Every real bundle-member shape found (10 total, exhaustive over every
# a/b/c/d-keyed bundle in all 135 records) is normalized to a uniform
# counted_reference sub-item so catalog/choices.py's EXISTING "multiple"
# bundle mechanism (_bundle_label_and_id) resolves every bundle unmodified —
# no choices.py changes needed. Three of those ten shapes ({"value": N}
# gold, {"special": ...} flavor-only gear, {"equipmentType": ...} category
# placeholders) synthesize a non-catalog reference; see
# _equipment_bundle_member_from_5etools's own docstring, and the Task 5
# report, for the disclosed consumption-path consequence (verified
# end-to-end in test_resolve.py: the choice itself renders correctly, but a
# synthetic member is silently dropped from the final sheet on selection,
# same as this engine's pre-existing, total absence of any gold/currency
# field at all — confirmed by grep, not something this task introduces).
# ---------------------------------------------------------------------------

def test_aberrant_heir_equipment_choice_is_a_two_option_bundle_choice():
    # Aberrant Heir/EFA: bundle A = dagger, disguise kit, costume,
    # traveler's clothes, 16 GP (1600 "value" = COPPER, confirmed: 1600 / 100
    # = 16, matching SRD's own bundled Acolyte convention — its pouch
    # "containsValue": 1500 in the raw 5etools data corresponds to SRD's own
    # starting_gold of exactly 15 gp). Bundle B = 50 GP only (5000 value).
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "aberrant-heir-efa")
    envelopes = bg["starting_equipment_options"]
    assert len(envelopes) == 1
    envelope = envelopes[0]
    assert envelope["choose"] == 1
    assert envelope["type"] == "equipment"
    assert envelope["from"]["option_set_type"] == "options_array"
    options = envelope["from"]["options"]
    assert len(options) == 2
    bundle_a, bundle_b = options
    assert bundle_a["option_type"] == "multiple"
    assert bundle_b["option_type"] == "multiple"
    a_ids = {i["of"]["index"] for i in bundle_a["items"]}
    assert a_ids == {"dagger", "disguise-kit", "clothes-costume", "clothes-travelers", "gp-16"}
    assert bundle_b["items"] == [
        {"option_type": "counted_reference", "count": 1, "of": {"index": "gp-50", "name": "50 GP"}},
    ]


def test_gold_value_is_converted_from_copper_to_gold_pieces_not_left_as_copper():
    # Getting the unit wrong makes every converted gold amount 100x wrong —
    # explicitly called out by the brief as a risk to verify, not assume.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "aberrant-heir-efa")
    options = bg["starting_equipment_options"][0]["from"]["options"]
    gold_only = next(o for o in options if len(o["items"]) == 1)
    assert gold_only["items"][0]["of"] == {"index": "gp-50", "name": "50 GP"}  # NOT "gp-5000"/"5000 GP"


def test_uppercase_ab_keys_are_handled_the_same_as_lowercase():
    # Acolyte/XPHB uses "A"/"B" (2024-era), not "a"/"b" (PHB-era) — confirmed
    # empirically, Step 1.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "acolyte-xphb")
    envelopes = bg["starting_equipment_options"]
    assert len(envelopes) == 1
    assert len(envelopes[0]["from"]["options"]) == 2


def test_charlatan_phb_gets_four_options_not_hardcoded_two():
    # Charlatan/PHB uses a/b/c/d, the one real 4-option record — handled
    # generically, not by assuming every background has exactly 2 options.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "charlatan-phb")
    options = bg["starting_equipment_options"][0]["from"]["options"]
    assert len(options) == 4


def test_athlete_mot_two_independent_ab_entries_become_two_separate_envelopes():
    # Athlete/MOT carries TWO a/b-keyed entries in its startingEquipment
    # list (pick a discus-or-ball, AND separately pick a charm-or-trophy) —
    # must be two independent "choose 1 of 2" envelopes, never flattened
    # into one "choose 1 of 4" envelope (which would let a player pick e.g.
    # "discus + charm" as ONE option instead of two separate choices).
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "athlete-mot")
    envelopes = bg["starting_equipment_options"]
    assert len(envelopes) == 2
    for envelope in envelopes:
        assert len(envelope["from"]["options"]) == 2
    first_ids = {i["of"]["index"] for i in envelopes[0]["from"]["options"][0]["items"]}
    second_ids = {i["of"]["index"] for i in envelopes[1]["from"]["options"][0]["items"]}
    assert first_ids != second_ids


def test_background_with_only_fixed_equipment_gets_no_choice_envelope():
    # Anthropologist/ToA's startingEquipment has only a "_"-keyed (fixed,
    # no-choice) entry — no a/b package choice at all. Its
    # starting_equipment_options must stay an empty list, not a malformed
    # or fabricated envelope.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "anthropologist-toa")
    assert bg["starting_equipment_options"] == []


def test_item_names_resolve_against_bundled_srd_equipment_ids_not_a_naive_slug():
    # "traveler's clothes"/"costume" don't match a naive slug of their
    # 5etools name against catalog.items (SRD's own ids are "clothes-
    # travelers"/"clothes-costume" — reversed word order) — must resolve via
    # a real name-based lookup, not silently mismatch or fall back to
    # synthetic ids for items that DO exist in the SRD catalog.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "aberrant-heir-efa")
    items = bg["starting_equipment_options"][0]["from"]["options"][0]["items"]
    by_index = {i["of"]["index"]: i["of"]["name"] for i in items}
    assert by_index["clothes-travelers"] == "Clothes, traveler's"
    assert by_index["clothes-costume"] == "Clothes, costume"


def test_unresolvable_item_name_gets_a_flagged_synthetic_reference_not_dropped():
    # Knight of the Gauntlet/FRHoF references a plain "holy symbol" — the
    # SRD equipment catalog only has holy symbols as an equipment_category
    # (amulet/emblem/reliquary), never a generic "Holy Symbol" item, so this
    # is genuinely unresolvable against catalog.items. Must still appear as
    # a real, correctly-labeled bundle member (flagged via the "unlisted-"
    # id prefix), never silently dropped from the bundle.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "knight-of-the-gauntlet-frhof")
    items = bg["starting_equipment_options"][0]["from"]["options"][0]["items"]
    holy_symbol = next(i for i in items if i["of"]["index"] == "unlisted-holy-symbol")
    assert holy_symbol["of"]["name"] == "Holy Symbol"


def test_equipment_type_category_placeholder_becomes_a_labeled_synthetic_reference():
    # Artisan/XPHB's bundle A includes {"equipmentType": "toolArtisan"} — a
    # nested "pick a specific artisan's tool" sub-choice smuggled inside an
    # otherwise-flat bundle, which catalog/choices.py's "multiple" mechanism
    # has no way to represent as a real nested choice (see
    # _bundle_label_and_id's own docstring) — represented here as a single,
    # clearly-labeled synthetic placeholder instead of silently dropping the
    # whole bundle option.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "artisan-xphb")
    items = bg["starting_equipment_options"][0]["from"]["options"][0]["items"]
    tool = next(i for i in items if i["of"]["index"] == "category-artisans-tools")
    assert tool["of"]["name"] == "Artisan's Tools"


def test_quantity_is_carried_onto_the_counted_reference_not_dropped():
    # Artisan/XPHB's bundle A includes {"item": "pouch|xphb", "quantity": 2}
    # — the quantity must land on the sub-item's `count`, not be silently
    # discarded (which would under-grant the bundle).
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "artisan-xphb")
    items = bg["starting_equipment_options"][0]["from"]["options"][0]["items"]
    pouch = next(i for i in items if i["of"]["index"] == "pouch")
    assert pouch["count"] == 2


def test_every_real_bundle_member_is_uniformly_a_counted_reference():
    # Exhaustive check: every real background's every equipment-choice
    # bundle member must be option_type "counted_reference" — the ONE
    # uniform shape catalog/choices.py's _bundle_label_and_id resolves for
    # a "multiple" bundle. Any other option_type here would silently break
    # that bundle's resolvability (_bundle_label_and_id returns None for a
    # non-uniform bundle).
    backgrounds = load_official_backgrounds(official_dir())
    checked_any = False
    for bg in backgrounds:
        for envelope in bg["starting_equipment_options"]:
            for option in envelope["from"]["options"]:
                assert option["option_type"] == "multiple"
                for item in option["items"]:
                    assert item["option_type"] == "counted_reference", bg["name"]
                    checked_any = True
    assert checked_any  # sanity: real data was actually exercised


# ---------------------------------------------------------------------------
# Backgrounds (final whole-branch review, Finding 1, 2026-09-27) — the
# FIXED, no-choice "_"-keyed startingEquipment list converts into real
# starting_equipment/starting_gold/starting_narrative_items instead of the
# hardcoded []/None placeholders Task 5 deliberately left behind. See
# _fixed_starting_equipment_from_5etools' own docstring for the full shape
# grounding.
# ---------------------------------------------------------------------------

def test_acolyte_phb_fixed_list_produces_real_equipment_gold_and_narrative():
    # Acolyte/PHB's "_" list (confirmed real, 2026-09-27): a holy symbol
    # (no SRD catalog match — a real item, but treated as narrative, same
    # as a flavor/category placeholder), 5x sticks of incense (flavor),
    # vestments (flavor), common clothes (a real catalog match), and a
    # pouch containing 1500 "copper" (15 gp).
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "acolyte-phb")
    assert bg["starting_equipment"] == [
        {"equipment": {"index": "clothes-common", "name": "Clothes, common"}, "quantity": 1},
    ]
    assert bg["starting_gold"] == {"quantity": 15, "unit": "gp"}
    assert bg["starting_narrative_items"] == [
        "holy symbol (a gift to you when you entered the priesthood)",
        "Sticks of incense",
        "Vestments",
    ]


def test_background_with_only_fixed_equipment_gets_real_equipment_not_a_placeholder():
    # Anthropologist/ToA carries ONLY a "_"-keyed entry (no a/b package
    # choice at all — see test_background_with_only_fixed_equipment_gets_
    # no_choice_envelope above, which covers starting_equipment_options'
    # own, unaffected, empty-list behavior). Before this fix this
    # background got ZERO starting equipment and ZERO gold, fixed or
    # chosen — sanity-checking that it now gets SOMETHING real.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "anthropologist-toa")
    assert bg["starting_equipment_options"] == []  # unaffected by this fix
    assert bg["starting_gold"] is not None
    assert bg["starting_gold"]["quantity"] > 0


def test_multiple_underscore_entries_in_one_record_are_all_collected():
    # Prismari Student/SCC (confirmed real, 2026-09-27): TWO separate
    # "_"-keyed entries in its startingEquipment list — one BEFORE its
    # artisan's-tools-or-instrument a/b choice (ink + ink pen), one AFTER
    # it (a school uniform, flavor, + a pouch containing 1000 copper =
    # 10gp). Both must be collected, not just the first found.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "prismari-student-scc")
    equipment_ids = {e["equipment"]["index"] for e in bg["starting_equipment"]}
    assert equipment_ids == {"ink-1-ounce-bottle", "ink-pen"}
    assert bg["starting_gold"] == {"quantity": 10, "unit": "gp"}
    assert bg["starting_narrative_items"] == ["School uniform"]


def test_sub_one_gp_fixed_amount_leaves_starting_gold_none_not_a_fabricated_zero():
    # Haunted One/VRGR and Investigator/VRGR (confirmed real, 2026-09-27):
    # their "_" list ends with a real 10-copper (1 silver piece) amount,
    # which floors to "gp-0" — this must NOT surface as
    # starting_gold == {"quantity": 0, ...}, the exact "fabricated zero is
    # worse than absent" anti-pattern the final whole-branch review's
    # Finding 1 exists to eliminate, just for a smaller amount. Sub-gp
    # coinage isn't tracked by this app; starting_gold stays None rather
    # than lying about it being zero.
    backgrounds = load_official_backgrounds(official_dir())
    for index in ("haunted-one-vrgr", "investigator-vrgr"):
        bg = next(b for b in backgrounds if b["index"] == index)
        assert bg["starting_gold"] is None


def test_contains_value_pouch_shape_converts_to_gold_same_as_bare_value():
    # The "_"-only gold shape ({"item": "pouch|phb", "containsValue": N} /
    # {"special": "purse", "containsValue": N}) must resolve to the SAME
    # synthetic gp-N reference the a/b choice bundles' bare {"value": N}
    # shape already produces (Task 5) — verified directly against
    # _equipment_bundle_member_from_5etools, not just through the
    # higher-level fixed-equipment conversion above.
    from catalog.official_source import _equipment_bundle_member_from_5etools
    pouch_member = _equipment_bundle_member_from_5etools({"item": "pouch|phb", "containsValue": 1500})
    assert pouch_member["of"]["index"] == "gp-15"
    purse_member = _equipment_bundle_member_from_5etools({"special": "purse", "containsValue": 2000})
    assert purse_member["of"]["index"] == "gp-20"


# ---------------------------------------------------------------------------
# Backgrounds (Phase 4b Task 6) — inert feat storage. Real shape confirmed
# against the fetched backgrounds.json (2026-09-27): `feats` is a list of
# single-key boolean-map dicts, `{"<feat-name>|<source>": True}`, the SAME
# convention skillProficiencies/toolProficiencies already use — but with
# one genuine divergence from the brief's own description: 4 real records
# (Haunted One/RHW, Investigator/RHW, Mist Wanderer, Spirit Medium) carry a
# SECOND, non-boolean entry alongside the plain grant,
# `{"anyFromCategory": {"category": ["DG"]}}` — a "pick any feat from
# category DG" wildcard this app has no feat catalog to resolve against
# (per the brief's own explicit instruction not to attempt that). Handled
# the same way _proficiencies_from_5etools already handles the identical
# "value is True vs. a dict/int" distinction for skill/tool wildcards: only
# `is True` entries are converted, so the wildcard entry is silently
# excluded by the SAME generic check, no anyFromCategory-specific code
# needed. This is a disclosed, deliberate exclusion (feats stay inert, no
# catalog to resolve a wildcard against), not a dropped grant of a kind
# this task claims to produce.
#
# CORRECTED by Finding 2 of the final whole-branch review (2026-09-27):
# `_feats_from_5etools` now returns (feats, feat_options) instead of a
# single list — see that function's own docstring. `feats` stays a
# single-element fixed grant for the 69/71 real records with exactly one
# True-valued entry (every test below except the multi-entry one), and
# `feat_options` is empty for all of them.
# ---------------------------------------------------------------------------

def test_feats_boolean_map_becomes_a_plain_list_of_stripped_feat_ids():
    # Aberrant Heir/EFA: {"feats": [{"aberrant dragonmark|efa": true}]} —
    # confirmed empirically, Step 1.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "aberrant-heir-efa")
    assert bg["feats"] == ["aberrant-dragonmark"]
    assert bg["feat_options"] == []
    # Finding 1 of the final whole-branch review (2026-09-28): feat_refs
    # recovers the source the bare slug above throws away.
    assert bg["feat_refs"] == ["aberrant-dragonmark-efa"]


def test_feats_with_no_field_at_all_gets_an_empty_list():
    backgrounds = load_official_backgrounds(official_dir())
    # Acolyte/PHB carries no `feats` field in the real data (its XPHB
    # reprint does — "magic initiate; cleric" — so PHB specifically is
    # used here to isolate the no-field case).
    bg = next(b for b in backgrounds if b["index"] == "acolyte-phb")
    assert bg["feats"] == []
    assert bg["feat_options"] == []
    assert bg["feat_refs"] == []


def test_feats_anyfromcategory_wildcard_is_excluded_not_crashed_on():
    # Haunted One/RHW carries a real fixed feat grant (Survivor) AND a
    # non-boolean anyFromCategory wildcard entry in the same list — the
    # wildcard must be silently excluded (no feat catalog to resolve it
    # against), while the fixed grant still comes through.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "haunted-one-rhw")
    assert bg["feats"] == ["survivor"]
    assert bg["feat_options"] == []
    assert bg["feat_refs"] == ["survivor-rhw"]


def test_feats_multiple_true_entries_are_alternatives_not_a_triple_grant():
    # Rewarded/BMT's real published text is "You gain the Lucky, Magic
    # Initiate, or Skilled feat (your choice)" — a CHOICE of one, not a
    # simultaneous grant of all three. CORRECTED by Finding 2 of the final
    # whole-branch review (2026-09-27): this test used to assert
    # bg["feats"] == ["lucky", "magic-initiate", "skilled"] (all three
    # granted at once), matching Task 6's original always-additive
    # behavior — that behavior over-granted. Now `feats` stays empty (no
    # unconditional grant) and the three candidates land in the new
    # `feat_options` field instead. Ruined/BMT (Alert/Skilled/Tough) is the
    # identical shape. feat_refs stays empty here too (Finding 1 of the
    # final whole-branch review, 2026-09-28) — these are unresolved
    # alternatives, not an actual grant to build a source-qualified ref
    # for.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "rewarded-bmt")
    assert bg["feats"] == []
    assert bg["feat_options"] == ["lucky", "magic-initiate", "skilled"]
    assert bg["feat_refs"] == []

    ruined = next(b for b in backgrounds if b["index"] == "ruined-bmt")
    assert ruined["feats"] == []
    assert ruined["feat_options"] == ["alert", "skilled", "tough"]
    assert ruined["feat_refs"] == []


# --- Finding 1 of the final whole-branch review (2026-09-28): feat_refs,
# the source-qualified parallel to `feats` that lets engine.resolve.
# _resolve_granted_feats recover the source a bare slug throws away
# --------------------------------------------------------------------------

def test_feat_refs_recovers_the_source_a_bare_slug_would_otherwise_lose():
    # Sailor/XPHB: {"tavern brawner|xphb" ... } -- real key is "tavern
    # brawler|xphb". Tavern Brawler exists in BOTH PHB and XPHB (an
    # ambiguous bare slug — see engine.resolve._resolve_granted_feats'
    # own docstring), so without feat_refs this grant is unresolvable from
    # `feats` alone; feat_refs disambiguates it exactly.
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "sailor-xphb")
    assert bg["feats"] == ["tavern-brawler"]
    assert bg["feat_refs"] == ["tavern-brawler-xphb"]


def test_feat_refs_lowercases_a_capitalized_real_grant_key():
    # Noble/XPHB is the ONE real record whose grant key is capitalized
    # ("Skilled|xphb", confirmed 2026-09-28) — slug() lowercases
    # unconditionally, so the ref must still come out "skilled-xphb", not
    # "Skilled-xphb".
    backgrounds = load_official_backgrounds(official_dir())
    bg = next(b for b in backgrounds if b["index"] == "noble-xphb")
    assert bg["feats"] == ["skilled"]
    assert bg["feat_refs"] == ["skilled-xphb"]


def test_feat_refs_recovers_the_source_for_the_semicolon_suffixed_variant_too():
    # The ";"-suffixed spell-list-restricted Magic Initiate variant (see
    # the semicolon-fix section above) must ALSO get a correct
    # source-qualified ref, not just a correct bare slug — the ";"-strip
    # happens before slugging for both true_feat_ids and true_feat_refs.
    backgrounds = load_official_backgrounds(official_dir())
    for bg_id in ("acolyte-xphb", "guide-xphb", "moonwell-pilgrim-frhof", "sage-xphb"):
        bg = next(b for b in backgrounds if b["index"] == bg_id)
        assert bg["feat_refs"] == ["magic-initiate-xphb"], f"{bg_id}: {bg['feat_refs']!r}"


# --- load_official_feats() scaffolding (Phase 4c-i Task 1) ---
#
# There is NO bundled SRD feats file at all — the 2014 SRD has no feats
# mechanic — so Catalog.feats (loader.py) is populated ONLY from this
# official data, with no SRD merge step, unlike races/backgrounds/traits.
#
# Step 1 grounding (2026-09-27, against the real fetched feats.json):
# 305 raw records, 0 carrying a "_copy" key (unlike races/backgrounds,
# this dataset has no _copy/_mod reprints at all — every record is
# already a complete, standalone entry), so all 305 survive conversion.
# 47 names repeat, but EVERY repeat is a distinct-source reprint pair
# (e.g. Alert/PHB + Alert/XPHB) — no same-source collision exists, so the
# source-qualified index scheme already used for races/backgrounds is
# collision-free here too, confirmed exhaustively, not sampled.


def test_loads_a_real_feat_with_a_source_qualified_id():
    feats = load_official_feats(official_dir())
    alert = next(f for f in feats if f["name"] == "Alert")
    assert alert["index"].endswith("-phb") or alert["index"].endswith("-xphb")  # ground the real source


def test_total_feat_count_matches_real_data():
    feats = load_official_feats(official_dir())
    assert len(feats) > 250  # sanity: most of the 305 real non-copy records survived (all 305 do, confirmed)


def test_category_is_preserved():
    feats = load_official_feats(official_dir())
    origin_feats = [f for f in feats if f.get("category") == "O"]
    assert len(origin_feats) == 35  # 35 real Origin-category feats, confirmed exhaustively (Step 1)


def test_no_same_source_name_collides_on_index():
    # 47 real feat names repeat across sourcebooks (e.g. Alert PHB/XPHB),
    # but never within the SAME source — confirmed exhaustively, Step 1.
    # Source-qualified indexes must therefore all be unique.
    feats = load_official_feats(official_dir())
    indexes = [f["index"] for f in feats]
    assert len(indexes) == len(set(indexes))


def test_placeholder_fields_present_but_empty_scaffolding_only():
    # Task 1 was scaffolding ONLY — ability bonuses/proficiencies/languages/
    # resistances (Tasks 2-5) and expertise/saving-throw-proficiencies
    # (Task 6) are now real conversions, not placeholders (see the Task 6
    # section below for feats that DO carry expertise/saving-throw data).
    # Alert/PHB just happens to have empty values for every one of these
    # fields in the real data, so this still locks in the shape (every key
    # present, right type) without asserting non-trivial content.
    feats = load_official_feats(official_dir())
    alert = next(f for f in feats if f["index"] == "alert-phb")
    assert alert["ability_bonuses"] == []
    assert alert["ability_bonus_options"] is None
    # proficiencies/proficiency_choices are now Task 3 real conversion
    # (Alert/PHB just happens to grant neither), not scaffolding.
    assert alert["proficiencies"] == []
    assert alert["proficiency_choices"] == []
    assert alert["languages"] == []
    assert alert["language_options"] is None
    assert alert["resist"] == []
    assert alert["immune"] == []
    assert alert["condition_immune"] == []
    assert alert["senses"] == {}
    assert alert["expertise_skills"] == []
    assert alert["saving_throw_proficiencies"] == []
    assert isinstance(alert["prerequisite"], list)
    assert isinstance(alert["entries"], list) and len(alert["entries"]) > 0


def test_missing_official_feats_data_returns_empty_list_not_crash(tmp_path):
    assert load_official_feats(tmp_path) == []


# --- load_official_feats() ability bonus grants (Phase 4c-i Task 2) -------
#
# Grounded (2026-09-28) against the real fetched feats.json: the "ability"
# field reuses the SAME {"choose": {"from": [...], "amount"/"count": N}}
# envelope races/backgrounds already use, sometimes a flat fixed bonus
# ({"cha": 1}, no "choose" at all) instead. Key finding: "Ability Score
# Improvement" itself carries TWO entries, one keyed "amount": 2 and one
# keyed "count": 2 — but BOTH are marked "hidden": true, meaning both
# represent the existing class-level ASI mechanic (out of scope this
# slice, per the design spec), not a live ability_bonus_options grant.
# Once hidden entries are excluded, every surviving amount/count value in
# the real data is 1 (or absent, defaulting to 1 — e.g. Epic Boons'
# "from"-only entries) — unlike races' Custom Lineage (amount=2, genuinely
# ambiguous), there's no live ambiguity between "amount" and "count" left
# to guess at for feats.


def test_actor_grants_a_fixed_charisma_bonus():
    feats = load_official_feats(official_dir())
    actor = next(f for f in feats if f["name"] == "Actor")
    assert actor["ability_bonuses"] == [{"ability_score": {"index": "cha", "name": "CHA", "url": ""}, "bonus": 1}]
    assert actor["ability_bonus_options"] is None


def test_athlete_offers_a_choice_of_str_or_dex():
    feats = load_official_feats(official_dir())
    athlete = next(f for f in feats if f["name"] == "Athlete")
    envelope = athlete["ability_bonus_options"]
    assert envelope["choose"] == 1
    assert envelope["type"] == "ability_bonuses"
    ids = {o["ability_score"]["index"] for o in envelope["from"]["options"]}
    assert ids == {"str", "dex"}
    assert athlete["ability_bonuses"] == []


def test_ability_score_improvement_feat_has_no_live_ability_bonus_grant():
    # Both of its real entries are marked "hidden": true (one "amount": 2,
    # one "count": 2) — they describe the existing class-level ASI
    # mechanic, not a feat-granted bonus to convert here.
    feats = load_official_feats(official_dir())
    asi = next(f for f in feats if f["name"] == "Ability Score Improvement")
    assert asi["ability_bonuses"] == []
    assert asi["ability_bonus_options"] is None


# --- load_official_feats() skill/tool/weapon/armor proficiency grants -----
# (Phase 4c-i Task 3)
#
# Grounded (2026-09-28) against the real fetched feats.json: only 12/305
# feats carry skillProficiencies, 10 toolProficiencies, 6 armorProficiencies,
# 4 weaponProficiencies. Skill/tool/armor all reuse the SAME shapes races/
# backgrounds already established (fixed True grants,
# _skill_choice_envelope_from_5etools/_tool_choice_envelope_from_5etools's
# "any"/"anyArtisansTool"/"anyMusicalInstrument"/"choose" envelopes,
# _proficiencies_from_5etools's armor category handling) — reused directly,
# unmodified, via _proficiencies_from_5etools/_proficiency_choices_from_5etools
# (the background-side list-of-envelopes function, needed here too: Prodigy
# carries a skill choice AND a tool wildcard simultaneously).
#
# Weapon is the one real divergence: 3 of the 4 real weaponProficiencies
# feats use broad CATEGORY keys ("firearms"/"martial"/"improvised") races
# never had as fixed grants (races only ever grant specific named weapons,
# e.g. "battleaxe|phb") — the generic pluralize path would produce wrong ids
# ("martials", "improviseds") for two of these, so _WEAPON_ID_OVERRIDES
# gained "martial"/"simple"/"improvised" entries (confirmed against
# 5e-SRD-Classes.json's own "simple-weapons"/"martial-weapons" ids for the
# first two; "improvised-weapons" has no bundled-SRD precedent but follows
# the same suffix convention, disclosed in _WEAPON_ID_OVERRIDES' own
# comment). The 4th, Weapon Master (PHB), uses a completely different
# "choose": {"fromFilter": "...", "count": 4} shape — a filter-query DSL
# string, not an enumerable "from" list — that no existing race/background
# choice machinery has ever modeled (races' own real Hobgoblin/VGM carries
# the identical fromFilter shape, silently unconverted today, a pre-existing
# gap outside this task's scope). Converting a filter-query DSL is a
# meaningfully bigger feature (a new option_set_type in catalog/choices.py)
# than this task's declared file scope (official_source.py +
# test_official_source.py only), so it is DELIBERATELY left unconverted
# here too — the fixed-grant loop's `is True` check already skips it
# harmlessly (a dict is never `is True`), so this is a disclosed omission,
# not a crash or silently-wrong data. See test below that locks this in.


def test_aberrant_anatomy_grants_a_fixed_skill_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Aberrant Anatomy" and f["source"] == "RHW")
    assert feat["proficiencies"] == [{"index": "skill-perception", "name": "Skill: Perception", "url": ""}]
    assert feat["proficiency_choices"] == []


def test_boon_of_skill_grants_every_skill_as_a_fixed_list():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Boon of Skill")
    assert len(feat["proficiencies"]) == 18
    assert all(p["index"].startswith("skill-") for p in feat["proficiencies"])


def test_keen_mind_xphb_offers_an_enumerated_skill_choice():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Keen Mind" and f["source"] == "XPHB")
    assert feat["proficiencies"] == []
    assert len(feat["proficiency_choices"]) == 1
    envelope = feat["proficiency_choices"][0]
    assert envelope["choose"] == 1
    assert envelope["type"] == "proficiencies"
    ids = {o["item"]["index"] for o in envelope["from"]["options"]}
    assert ids == {"skill-arcana", "skill-history", "skill-investigation", "skill-nature", "skill-religion"}


def test_echoing_soul_offers_a_wildcard_any_skill_choice():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Echoing Soul")
    envelope = feat["proficiency_choices"][0]
    assert envelope == {"choose": 1, "type": "proficiencies", "from": {"option_set_type": "any_skill"}}


def test_poisoner_grants_a_fixed_tool_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Poisoner" and f["source"] == "TCE")
    assert feat["proficiencies"] == [{"index": "poisoners-kit", "name": "Poisoner's Kit", "url": ""}]


def test_crafter_offers_an_enumerated_tool_choice_of_count_three():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Crafter")
    envelope = feat["proficiency_choices"][0]
    assert envelope["choose"] == 3
    assert len(envelope["from"]["options"]) == 8


def test_artificer_initiate_offers_a_wildcard_artisans_tool_choice():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Artificer Initiate")
    envelope = feat["proficiency_choices"][0]
    assert envelope == {"choose": 1, "type": "proficiencies",
                         "from": {"option_set_type": "any_tool", "tool_category": "Artisan's Tools"}}


def test_musician_offers_a_wildcard_musical_instrument_choice_of_three():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Musician")
    envelope = feat["proficiency_choices"][0]
    assert envelope == {"choose": 3, "type": "proficiencies",
                         "from": {"option_set_type": "any_tool", "tool_category": "Musical Instrument"}}


def test_prodigy_offers_both_a_skill_choice_and_a_tool_choice_simultaneously():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Prodigy")
    assert len(feat["proficiency_choices"]) == 2
    types = [env["from"]["option_set_type"] for env in feat["proficiency_choices"]]
    assert types == ["options_array", "any_tool"]


def test_heavily_armored_grants_fixed_heavy_armor_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Heavily Armored" and f["source"] == "PHB")
    assert feat["proficiencies"] == [{"index": "heavy-armor", "name": "Heavy armor", "url": ""}]


def test_lightly_armored_xphb_grants_light_armor_and_shield_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Lightly Armored" and f["source"] == "XPHB")
    indexes = {p["index"] for p in feat["proficiencies"]}
    assert indexes == {"light-armor", "shields"}


def test_gunner_grants_fixed_firearms_weapon_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Gunner")
    assert feat["proficiencies"] == [{"index": "firearms", "name": "Firearms", "url": ""}]


def test_martial_weapon_training_grants_fixed_martial_weapons_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Martial Weapon Training")
    assert feat["proficiencies"] == [{"index": "martial-weapons", "name": "Martial weapons", "url": ""}]


def test_tavern_brawler_xphb_grants_fixed_improvised_weapons_proficiency():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Tavern Brawler" and f["source"] == "XPHB")
    assert feat["proficiencies"] == [{"index": "improvised-weapons", "name": "Improvised weapons", "url": ""}]


def test_weapon_master_fromfilter_weapon_choice_is_a_disclosed_unconverted_gap():
    # See the section docstring above: a "choose"/"fromFilter" filter-query
    # DSL shape, never modeled by any existing race/background choice
    # machinery — deliberately left unconverted rather than guessed at.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Weapon Master" and f["source"] == "PHB")
    assert feat["proficiencies"] == []
    assert feat["proficiency_choices"] == []


# ---------------------------------------------------------------------------
# load_official_feats() language grants (Phase 4c-i Task 4) — reuses the SAME
# _language_grants_from_5etools conversion machinery built for backgrounds
# (Phase 4b Task 3) directly. Grounded (2026-09-28) against the real fetched
# feats.json: only 7/305 feats carry languageProficiencies at all.
#
# One real, necessary variant: every feat wildcard entry uses the key "any"
# (e.g. {"any": 1}), never backgrounds' "anyStandard" — confirmed, 0/7 feat
# records use "anyStandard" and 0/56 background records use "any" (checked
# both directions against the real fetched data), so
# _language_grants_from_5etools now reads either key with no ambiguity or
# collision risk to the already-covered background path.
#
# One real, disclosed gap: Harper Agent/FRHoF's {"thieves' cant": True} is
# NOT a recognized language slug in reference_data.LANGUAGES (Thieves' Cant
# is a secret argot, not one of the 16 standard/exotic D&D languages the SRD
# table models) — _language_ref_from_key already returns None for any
# unrecognized key (same fallback discipline documented on that function),
# so this fixed grant is silently dropped rather than guessed at. See
# test_harper_agent_thieves_cant_is_a_disclosed_unrecognized_language_gap
# below.
# ---------------------------------------------------------------------------


def test_fey_teleportation_grants_a_fixed_language_no_choice_offered():
    # Fey Teleportation/XGE: {"sylvan": True} — a single fixed-only entry,
    # structurally identical to backgrounds' Rune Carver case.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Fey Teleportation")
    assert feat["languages"] == [{"index": "sylvan", "name": "Sylvan", "url": ""}]
    assert feat["language_options"] is None


def test_echoing_soul_offers_an_any_wildcard_language_choice():
    # Echoing Soul/RHW: {"any": 1} — the feat-side wildcard key, reusing the
    # SAME resource_list mechanism as backgrounds' "anyStandard".
    from catalog import reference_data
    from catalog.choices import build_choice_options
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Echoing Soul")
    assert feat["languages"] == []
    envelope = feat["language_options"]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "resource_list"
    options = build_choice_options(envelope["from"])
    assert len(options) == len(reference_data.LANGUAGES)


def test_linguist_offers_an_any_wildcard_choice_of_three():
    # Linguist/PHB: {"any": 3} — same wildcard key, a higher count.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Linguist")
    assert feat["languages"] == []
    envelope = feat["language_options"]
    assert envelope["choose"] == 3
    assert envelope["from"]["option_set_type"] == "resource_list"


def test_symbiotic_being_offers_an_any_wildcard_language_choice():
    # Symbiotic Being/RHW: {"any": 1} — same shape as Echoing Soul/Prodigy.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Symbiotic Being")
    assert feat["languages"] == []
    envelope = feat["language_options"]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "resource_list"


def test_prodigy_also_offers_an_any_wildcard_language_choice():
    # Prodigy/XGE: {"any": 1} — Prodigy already has proficiency_choices
    # coverage (Task 3); this pins its SEPARATE language_options envelope.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Prodigy")
    assert feat["languages"] == []
    envelope = feat["language_options"]
    assert envelope["choose"] == 1
    assert envelope["from"]["option_set_type"] == "resource_list"


def test_cult_of_the_dragon_initiate_fixed_draconic_conditionally_substitutes_the_wildcard():
    # Cult of the Dragon Initiate/FRHoF: [{"draconic": True}, {"any": 1}] —
    # TWO separate outer-list entries, one fixed-only and one wildcard-only.
    # Real published text: "You know Draconic. If you already know Draconic
    # when you select this feat, you instead learn one language of your
    # choice" — the SAME "X, or Y if you already know X" conditional-
    # substitute shape backgrounds' Clan Crafter established, so this feat
    # hits the SAME saw_fixed_only_entry-and-saw_choice branch: only the
    # fixed Draconic grant is kept, no language_options envelope offered.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Cult of the Dragon Initiate")
    assert feat["languages"] == [{"index": "draconic", "name": "Draconic", "url": ""}]
    assert feat["language_options"] is None


def test_harper_agent_thieves_cant_is_a_disclosed_unrecognized_language_gap():
    # Harper Agent/FRHoF: {"thieves' cant": True} — Thieves' Cant is not a
    # recognized language slug in reference_data.LANGUAGES (it's a secret
    # argot, not one of the SRD's 16 standard/exotic languages), so this
    # fixed grant is silently dropped, same disclosed fallback
    # _language_ref_from_key already documents for any unrecognized key.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Harper Agent")
    assert feat["languages"] == []
    assert feat["language_options"] is None


# ---------------------------------------------------------------------------
# load_official_feats() resistances/immunities/condition immunities/senses
# (Phase 4c-i Task 5) — reuses the SAME _damage_modifiers_from_5etools/
# _condition_immunities_from_5etools conversion machinery built for races
# (Phase 4a Task 5) directly, confirmed dict-shape-agnostic (both already
# take a raw dict and read resist/immune/vulnerable/conditionImmune off it
# via .get, nothing race-specific despite living next to race-only code).
# `senses` is a brand-new field with no race-side precedent — races.json
# carries 0/160 records with a `senses` field at all (confirmed 2026-09-28),
# so this is feat-only conversion, built fresh.
#
# Grounded (2026-09-28) against the real fetched feats.json: 11/305 feats
# carry `resist`, 2 carry `immune`, 2 carry `conditionImmune`, 4 carry
# `senses` — a small surface. Of the 11 `resist` records, 6 use a plain
# string list (Boon of the Furious Storm, Boon of the Soul Drinker, Ember
# of the Fire Giant, Fury of the Frost Giant, Infernal Constitution, Mark
# of Storm) and 5 use the SAME CHOICE shape
# (`{"choose": {"from": [...]}}`) races' Dragonborn already exercises
# (Boon of Energy Resistance, Dragonscarred, Portal Jumper, Scion of the
# Outer Planes, Spell Resistant) — _damage_modifiers_from_5etools already
# filters non-string entries out (a disclosed, existing cut, not new here),
# so those 5 feats' `resist` lands empty, same as Dragonborn's on the race
# side. `senses` is always a list containing exactly one single-key dict
# (e.g. [{"blindsight": 15}]) across all 4 real records — never multiple
# list entries, never multiple keys on one entry — confirmed exhaustively,
# not sampled.
# ---------------------------------------------------------------------------


def test_ember_of_the_fire_giant_grants_a_fixed_fire_resistance():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Ember of the Fire Giant")
    assert feat["resist"] == ["fire"]
    assert feat["immune"] == []
    assert feat["condition_immune"] == []
    assert feat["senses"] == {}


def test_infernal_constitution_grants_two_fixed_resistances():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Infernal Constitution")
    assert feat["resist"] == ["cold", "poison"]


def test_choice_shaped_feat_resistance_is_a_disclosed_cut_not_a_crash():
    # Boon of Energy Resistance/EGW: {"choose": {"from": [9 damage types],
    # "count": 2}} — the SAME choice shape races' Dragonborn already
    # exercises (_damage_modifiers_from_5etools' own docstring). Resolving
    # that choice is out of scope for this pure-data-pass-through reuse, so
    # it must not crash and must not be silently mis-modeled as an
    # unconditional resistance — just filtered to empty, same as the race
    # side's own disclosed cut.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Boon of Energy Resistance")
    assert feat["resist"] == []


def test_boon_of_blazing_dawn_grants_a_fixed_immunity():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Boon of Blazing Dawn")
    assert feat["immune"] == ["radiant"]


def test_boon_of_poison_mastery_grants_both_immunity_and_condition_immunity():
    # The one real feat carrying BOTH immune and conditionImmune at once.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Boon of Poison Mastery")
    assert feat["immune"] == ["poison"]
    assert feat["condition_immune"] == ["poisoned"]


def test_boon_of_terror_grants_a_fixed_condition_immunity():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Boon of Terror")
    assert feat["condition_immune"] == ["frightened"]


def test_aberrant_anatomy_grants_blindsight_15():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Aberrant Anatomy")
    assert feat["senses"] == {"blindsight": 15}


def test_blind_fighting_and_skulker_both_grant_blindsight_10():
    # Skulker repeats across PHB (no senses field — the older Skulker never
    # granted blindsight) and XPHB (the 2024 reprint that does) —
    # confirmed 2026-09-28 against the real fetched feats.json, so the
    # XPHB record is selected explicitly by id, same "-source" disambig
    # convention every other reprint-aware test in this file already uses.
    feats = load_official_feats(official_dir())
    blind_fighting = next(f for f in feats if f["name"] == "Blind Fighting")
    skulker_xphb = next(f for f in feats if f["index"] == "skulker-xphb")
    assert blind_fighting["senses"] == {"blindsight": 10}
    assert skulker_xphb["senses"] == {"blindsight": 10}


def test_boon_of_truesight_grants_truesight_60():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Boon of Truesight")
    assert feat["senses"] == {"truesight": 60}


def test_a_feat_with_none_of_these_fields_gets_empty_defaults():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["name"] == "Alert")
    assert feat["resist"] == []
    assert feat["immune"] == []
    assert feat["condition_immune"] == []
    assert feat["senses"] == {}


# --- Feats (Phase 4c-i Task 6): expertise/saving-throw-proficiency grants,
# and the ";"-suffix background-feat-grant slug fix -------------------------
#
# expertise/savingThrowProficiencies real-data grounding (2026-09-28,
# against the real fetched feats.json): 7 real feats carry an `expertise`
# field (Aberrant Anatomy/RHW, Boon of Skill/XPHB, Boon of Terror/FRHoF,
# Echoing Soul/RHW, Prodigy/XGE, Skill Expert/TCE, Skill Expert/XPHB) — only
# 2 are FIXED (`{"<skill>": true}`); the other 5 are exclusively
# `{"anyProficientSkill": N}`, a CHOICE this app has no mechanism to
# resolve for an auto-granted feat (see _expertise_skills_from_5etools' own
# docstring) and so contribute nothing. Only 2 real feats carry a
# `savingThrowProficiencies` field at all (Resilient/PHB, Resilient/XPHB),
# and BOTH are exclusively choice-shaped (`{"choose": {"from": [...]}}`) —
# zero real fixed saving-throw-proficiency grants exist today, so this
# field converts to [] for every real feat, mirroring
# _background_ability_bonuses' own "always {} today, kept for symmetry"
# precedent.


def test_aberrant_anatomy_grants_a_fixed_perception_expertise():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["index"] == "aberrant-anatomy-rhw")
    assert feat["expertise_skills"] == ["skill-perception"]


def test_boon_of_terror_grants_a_fixed_intimidation_expertise():
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["index"] == "boon-of-terror-frhof")
    assert feat["expertise_skills"] == ["skill-intimidation"]


def test_prodigy_anyproficientskill_choice_contributes_no_fixed_expertise():
    # Prodigy/XGE's real `expertise` field is exclusively
    # `[{"anyProficientSkill": 1}]` — a CHOICE, not a fixed grant. No choice
    # mechanism exists for an auto-granted feat (see
    # _expertise_skills_from_5etools' own docstring), so this must convert
    # to an empty list, not crash and not guess a skill.
    feats = load_official_feats(official_dir())
    feat = next(f for f in feats if f["index"] == "prodigy-xge")
    assert feat["expertise_skills"] == []


def test_resilient_choice_shaped_saving_throw_contributes_no_fixed_grant():
    # Both real Resilient records (PHB, XPHB) are exclusively
    # `[{"choose": {"from": [...]}}]` — no fixed ability-keyed entry at
    # all, so saving_throw_proficiencies must be [] for both, not a guess
    # at which ability the choice might resolve to.
    feats = load_official_feats(official_dir())
    for feat in feats:
        if feat["name"] == "Resilient":
            assert feat["saving_throw_proficiencies"] == []


def test_no_real_feat_has_a_fixed_saving_throw_proficiency_today():
    # Exhaustive real-data check (2026-09-28): confirms the "always []
    # today" claim above isn't narrowly checked against Resilient alone.
    feats = load_official_feats(official_dir())
    assert all(f["saving_throw_proficiencies"] == [] for f in feats)


def test_prerequisite_field_is_preserved_raw_for_task_6_structured_checking():
    # Confirms the scaffold's raw prerequisite pass-through (Task 1) is
    # still intact and unconverted — engine/resolve.py's own
    # _feat_structured_prerequisite/_feat_prerequisite_alt_met (Task 6)
    # read this raw 5etools shape directly, not a normalized one.
    feats = load_official_feats(official_dir())
    actor = next(f for f in feats if f["index"] == "actor-xphb")
    assert actor["prerequisite"] == [{"level": 4, "ability": [{"cha": 13}]}]


# --- The ";"-suffix background-feat-grant slug fix (Task 6, found by Task
# 5's own review) ------------------------------------------------------------
#
# 4 real background records (Acolyte/XPHB, Guide/XPHB, Moonwell Pilgrim/
# FRHoF, Sage/XPHB) grant a spell-list-restricted Magic Initiate variant,
# e.g. `{"magic initiate; cleric|xphb": true}` — the ONLY grant keys in the
# whole real dataset containing a literal ";" (confirmed exhaustively,
# 2026-09-28). Before this fix, `_feats_from_5etools` slugged this key
# VERBATIM ("magic-initiate;-cleric"), which matched ZERO catalog feats —
# a silent, undisclosed "wrong slug, no match at all" failure, distinct
# from the already-disclosed "matches feats in more than one source"
# ambiguity guard every OTHER plain "magic initiate|<source>" grant hits.


def test_semicolon_suffixed_magic_initiate_variant_recovers_the_base_feat_slug():
    backgrounds = load_official_backgrounds(official_dir())
    for bg_id in ("acolyte-xphb", "guide-xphb", "moonwell-pilgrim-frhof", "sage-xphb"):
        bg = next(b for b in backgrounds if b["index"] == bg_id)
        # Recovered as the PLAIN base feat slug — matching exactly what a
        # plain "magic initiate|<source>" grant (no ";" suffix) already
        # produces elsewhere in the real data — not left semicolon-mangled.
        assert bg["feats"] == ["magic-initiate"], f"{bg_id}: {bg['feats']!r}"


def test_no_other_real_background_feat_grant_key_contains_a_semicolon():
    # Confirms the ";"-strip fix is scoped to the real pattern it targets
    # (Magic Initiate's spell-list variants) and isn't silently truncating
    # some OTHER, unrelated real feat name that happens to contain a ";" —
    # exhaustive check, not sampled: every other real grant key converts
    # identically whether or not the ";"-strip is applied.
    backgrounds = load_official_backgrounds(official_dir())
    semicolon_bearing_bg_ids = {"acolyte-xphb", "guide-xphb", "moonwell-pilgrim-frhof", "sage-xphb"}
    for bg in backgrounds:
        if bg["index"] in semicolon_bearing_bg_ids:
            continue
        for feat_id in bg["feats"] + bg["feat_options"]:
            assert ";" not in feat_id, f"{bg['index']}: unexpected semicolon in {feat_id!r}"


def test_choice_shaped_expertise_and_saving_throw_become_envelopes():
    feats = {f["index"]: f for f in load_official_feats(official_dir())}
    assert feats["skill-expert-xphb"]["expertise_choices"] == [
        {"choose": 1, "type": "proficiencies", "from": {"option_set_type": "any_skill"}}
    ]
    assert feats["aberrant-anatomy-rhw"]["expertise_choices"] == []  # fixed grant only
    options = feats["resilient-xphb"]["saving_throw_choices"][0]["from"]["options"]
    assert [o["item"]["index"] for o in options] == ["str", "dex", "con", "int", "wis", "cha"]
    assert feats["actor-xphb"]["saving_throw_choices"] == []


# --- feats' additionalSpells: fixed spell names (feat-additional-spells plan, slice 1) ---

def _feats_by_id():
    return {f["index"]: f for f in load_official_feats(official_dir())}


def test_feat_innate_spells_inherit_ability_and_daily_use():
    feats = _feats_by_id()
    assert feats["telepathic-xphb"]["innate_spells"] == [
        {"name": "Detect Thoughts", "spell_id": "detect-thoughts", "level": None, "uses": "1/day",
         "ability": "inherit", "variant": None}
    ]


def test_feat_innate_spells_strip_source_suffix_and_at_will():
    spells = _feats_by_id()["telekinetic-xphb"]["innate_spells"]
    assert [(s["name"], s["uses"], s["ability"]) for s in spells] == [("Mage Hand", "at-will", "inherit")]


def test_feat_innate_spells_numeric_level_keys_and_choose_ability():
    feat = _feats_by_id()["mark-of-storm-efa"]
    by_name = {s["name"]: s for s in feat["innate_spells"]}
    assert by_name["Thunderclap"]["level"] is None and by_name["Thunderclap"]["uses"] == "at-will"
    assert by_name["Gust Of Wind"]["level"] == 3 and by_name["Gust Of Wind"]["uses"] == "1/day"
    assert all(s["ability"] == {"choose": ["INT", "WIS", "CHA"]} for s in feat["innate_spells"])
    assert len(feat["innate_spells"]) == 2  # expanded is not modelled


def test_feat_prepared_maps_to_prepared_and_first_entry_fallback():
    feats = _feats_by_id()
    assert [(s["name"], s["uses"]) for s in feats["cloying-mists-abh"]["innate_spells"]] == [("Fog Cloud", "prepared")]
    assert [(s["name"], s["uses"]) for s in feats["cold-caster-frhof"]["innate_spells"]] == [("Ray Of Frost", "at-will")]


def test_feat_innate_spells_skipped_deferred_and_slot_keyed():
    feats = _feats_by_id()
    assert feats["rune-shaper-bgg"]["innate_spells"] == []
    assert feats["magic-initiate-xphb"]["innate_spells"] == []  # only filter choices, no fixed spells
    assert feats["abjuration-adept-au"]["innate_spells"] == []  # slot-level keys
    assert [s["name"] for s in feats["fey-touched-xphb"]["innate_spells"]] == ["Misty Step"]  # filter items ignored


# --- feats' additionalSpells: variants (slice 4) ---

def test_spell_variants_listed_for_multi_entry_feats():
    feats = _feats_by_id()
    assert feats["magic-initiate-xphb"]["spell_variants"] == ["Cleric Spells", "Druid Spells", "Wizard Spells"]
    scion = feats["scion-of-the-outer-planes-sato"]
    assert len(scion["spell_variants"]) == 5
    chaotic = [s for s in scion["innate_spells"] if s["variant"] == "Chaotic Outer Plane"]
    assert [s["name"] for s in chaotic] == ["Minor Illusion"]
    assert feats["telepathic-xphb"]["spell_variants"] == []


def test_variant_choice_entries_carry_variant_and_choose_from_lists():
    feats = _feats_by_id()
    mi = feats["magic-initiate-xphb"]["spell_choices"]
    assert {c["variant"] for c in mi} == {"Cleric Spells", "Druid Spells", "Wizard Spells"}
    solinari = [c for c in feats["initiate-of-high-sorcery-dsotdq"]["spell_choices"]
                if c["variant"] == "Solinari" and c["from"]]
    assert solinari[0]["filter"] is None and solinari[0]["count"] == 2
    assert solinari[0]["from"] == ["comprehend-languages", "detect-evil-and-good", "protection-from-evil-and-good", "shield"]


def test_background_feat_variant_hint_for_restricted_magic_initiate():
    from catalog.official_source import load_official_backgrounds
    bgs = {b["index"]: b for b in load_official_backgrounds(official_dir())}
    assert bgs["acolyte-xphb"]["feat_variant_hints"] == {"magic-initiate-xphb": "Cleric Spells"}
    assert bgs["astral-drifter-aag"]["feat_variant_hints"] == {}


def test_ritual_caster_xphb_folds_level_scaled_counts_into_one_choice():
    choices = _feats_by_id()["ritual-caster-xphb"]["spell_choices"]
    assert len(choices) == 1
    assert choices[0]["filter"] == {"level": [1], "ritual": True}
    assert choices[0]["count_by_level"] == {"1": 2, "5": 1, "9": 1, "13": 1, "17": 1}


def test_magic_connoisseur_catalog_shape():
    mc = _feats_by_id()["magic-connoisseur-au"]
    assert mc["innate_spells"] == []
    assert mc["spell_variants"] == ["Cleric Spells", "Druid Spells", "Wizard Spells"]
    got = [(c["variant"], c["filter"]["level"], c["filter"]["class"]) for c in mc["spell_choices"]]
    assert got == [(v, [lvl], [v.split()[0].lower()]) for v in mc["spell_variants"] for lvl in (1, 2)]
    for c in mc["spell_choices"]:
        assert (c["uses"], c["ability"], c["count"], c["from"]) == ("1/day", "inherit", 1, None)


def test_light_bringer_catalog_shape():
    lb = _feats_by_id()["light-bringer-abh"]
    assert lb["spell_variants"] == ["Light", "Cleric Cantrip"]
    assert [(s["name"], s["spell_id"], s["uses"], s["variant"]) for s in lb["innate_spells"]] == [
        ("Light", "light", "at-will", "Light")]
    assert len(lb["spell_choices"]) == 1
    c = lb["spell_choices"][0]
    assert (c["variant"], c["filter"], c["count"], c["uses"]) == (
        "Cleric Cantrip", {"level": [0], "class": ["cleric"]}, 1, "at-will")
