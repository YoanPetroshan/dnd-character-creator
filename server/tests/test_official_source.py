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
        "name": "Test Aetherborn", "sources": ["srd"],
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
