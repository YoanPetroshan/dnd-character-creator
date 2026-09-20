"""resolve(draft, catalog) -> Resolution — the single entry point for all
character-rules computation, per the architecture spec's engine contract
(docs/superpowers/specs/2026-09-16-builder-v2-architecture.md §3). One
fixed-order pass: sources → species ability bonuses → final ability scores
→ derived stats → choice generation/validation (§4a) — never iterates to a
fixpoint.

Single-class leveling (1-20) is in scope: draft.classes[0].subclassId is
read but never trusted to gate a feature choice unless it actually
matches, so any feature gated to a specific subclass is filtered out
rather than guessed at. Multiclass remains out of scope (see the plan's
Global Constraints). Equipment IS in scope as of Phase 2a — see
engine/equipment.py and the
_equipment_choice_templates/_gather_equipped_items/_fixed_equipment
functions below. Spellcasting IS in scope as of Phase 2c — see
engine/spells.py and the _spell_choice_templates function below.

Single-class leveling (1-20), subclass selection, and ASI choices ARE in
scope as of Phase 3a — see engine/asi.py, the _asi_choice_templates/
_apply_asi_progression functions, and SUBCLASS_UNLOCK_LEVEL in
catalog/reference_data.py. Multiclassing remains out of scope (Phase 3b).
"""
from __future__ import annotations

from catalog.choices import build_choice_template
from catalog.loader import Catalog
from . import asi as asi_mod
from . import derived as derived_mod
from . import equipment as equipment_mod
from . import spells as spells_mod

_DETAIL_FIELDS = (
    "alignment", "faith", "lifestyle",
    "age", "height", "weight", "eyes", "skin", "hair",
    "personalityTraits", "ideals", "bonds", "flaws",
    "backstory", "organizations", "allies", "enemies", "notes",
)


def _species_ability_bonuses(race: dict | None, subrace: dict | None) -> dict[str, int]:
    bonuses: dict[str, int] = {}
    for src in (race, subrace):
        if not src:
            continue
        for entry in src.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            bonuses[ab] = bonuses.get(ab, 0) + entry["bonus"]
    return bonuses


def _species_ability_bonus_choice_template(race: dict | None, subrace: dict | None, race_id: str | None) -> dict | None:
    """Half-Elf's ability_bonus_options (the only race/subrace in the
    bundled data with this field) needs a real Choice — this builds its
    template. Race is checked before subrace since ability_bonus_options
    could in principle appear on either (only race does in the bundled
    data, but this stays generic rather than hardcoding "half-elf")."""
    for src in (race, subrace):
        if not src or not src.get("ability_bonus_options"):
            continue
        envelope = src["ability_bonus_options"]
        cid = f"species:{race_id}:ability-bonus"
        source = {"kind": "species", "id": race_id, "label": race["name"] if race else ""}
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} ability score{'s' if choose != 1 else ''} to increase by 1."
        return build_choice_template(envelope, cid, source, "Ability Score Increase", description=description)
    return None


def _asi_granting_levels(catalog: Catalog, cls_id: str, max_level: int) -> list[int]:
    """ability_score_bonuses in a level row is a CUMULATIVE count, not a
    per-level flag — the actual ASI-granting levels are wherever the
    value increases from the previous level. Verified empirically while
    writing this plan: Fighter and Rogue both have real extra ASI levels
    (6/14 and 10) beyond the standard 4/8/12/16/19 every other class
    uses, and this diff-based approach correctly finds both."""
    levels: list[int] = []
    previous = 0
    for lvl in range(1, max_level + 1):
        row = catalog.class_level_row(cls_id, lvl)
        current = row.get("ability_score_bonuses", 0) if row else 0
        if current > previous:
            levels.append(lvl)
        previous = current
    return levels


def _apply_asi_progression(
    base_scores: dict[str, int], asi_levels: list[int], class_choices: dict, cls_id: str | None,
) -> tuple[dict[int, dict[str, int]], dict[str, int]]:
    """Walks ASI-granting levels in ascending order, applying each
    level's stored selection (if present and valid) to a running
    ability-score state. Returns (scores_by_level, final_scores):
    scores_by_level[lvl] is the state BEFORE that level's own ASI is
    applied (used by _asi_choice_templates to compute which options are
    disabled for that specific level's choice — a combo that's fine at
    level 4 might exceed the cap by level 8 once earlier ASIs stack),
    and final_scores is the state after every level's ASI has been
    applied — this becomes the actual final ability scores used for
    `modifiers` and everything derived from them."""
    combos = dict(asi_mod.asi_combinations())
    scores_by_level: dict[int, dict[str, int]] = {}
    running = dict(base_scores)
    for lvl in asi_levels:
        scores_by_level[lvl] = dict(running)
        cid = f"class:{cls_id}:{lvl}:asi"
        raw_selected = class_choices.get(cid) or []
        if isinstance(raw_selected, list) and len(raw_selected) == 1 and raw_selected[0] in combos:
            deltas = combos[raw_selected[0]]
            if not asi_mod.asi_exceeds_cap(deltas, running):
                running = asi_mod.apply_asi(deltas, running)
    return scores_by_level, running


def _class_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(cls.get("proficiency_choices", [])):
        cid = f"class:{cls_id}:1:prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"], "level": 1}
        provisional_label = "Skill Proficiencies" if envelope.get("type") == "proficiencies" else (envelope.get("type") or "Choice").title()
        tpl = build_choice_template(envelope, cid, source, provisional_label)
        if not tpl:
            continue
        # Some classes (Bard, Monk) have a SECOND proficiency_choices entry
        # also typed "proficiencies" that isn't actually a skill choice
        # (instruments/tools) — relabel based on what the resolved options
        # actually are, not the envelope's own (misleading) type field.
        if tpl["options"] and tpl["label"] == "Skill Proficiencies" and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = "Tool Proficiencies"
        templates.append(tpl)
    return templates


def _join_desc(desc) -> str | None:
    """Feature/trait 'desc' fields are lists of paragraph strings; choice
    envelopes never carry their own 'desc' except proficiency_choices (see
    Task 3's build_choice_template, which already handles a list there).
    This joins a parent object's desc for explicit passing as the
    'description' override, since the choice envelope itself has none."""
    if isinstance(desc, list):
        return " ".join(desc)
    return desc


def _sanitized_details(details_raw) -> dict | None:
    if not isinstance(details_raw, dict):
        return None
    result = {
        k: details_raw[k] for k in _DETAIL_FIELDS
        if isinstance(details_raw.get(k), str) and details_raw[k].strip()
    }
    return result if result else None


def _cumulative_feature_refs(
    catalog: Catalog, cls_id: str, subclass_id: str | None, max_level: int,
) -> list[tuple[int, dict]]:
    """Every class-level feature ref from level 1 through max_level, plus
    (once a subclass is selected) every subclass-level feature ref in the
    same range, each paired with the exact level it came from — needed so
    _feature_choice_templates can build a correctly level-suffixed choice
    id and source.level for each, not just always "1" as before Phase
    3a."""
    refs: list[tuple[int, dict]] = []
    for lvl in range(1, max_level + 1):
        row = catalog.class_level_row(cls_id, lvl)
        if row:
            refs.extend((lvl, ref) for ref in row.get("features", []))
    if subclass_id:
        for lvl in range(1, max_level + 1):
            srow = catalog.subclass_level_row(subclass_id, lvl)
            if srow:
                refs.extend((lvl, ref) for ref in srow.get("features", []))
    return refs


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[tuple[int, dict]], subclass_id: str | None,
) -> list[dict]:
    templates = []
    for lvl, ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated to a different subclass than the one selected (or none selected)
        envelope = (feature.get("feature_specific") or {}).get("subfeature_options")
        if not envelope:
            continue
        cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        # The subfeature_options envelope itself has no 'desc' key — the
        # description text lives on the parent feature (verified directly
        # against 5e-SRD-Features.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, feature["name"], description=_join_desc(feature.get("desc")))
        if tpl:
            templates.append(tpl)
    return templates


def _background_choice_templates(bg: dict, bg_id: str) -> list[dict]:
    templates = []
    envelope = bg.get("language_options")
    if envelope:
        cid = f"background:{bg_id}:languages"
        source = {"kind": "background", "id": bg_id, "label": bg["name"]}
        # language_options carries no 'desc' of its own, and the background
        # object has no separate summary text for it either — write a
        # plain, generic description rather than leaving it blank.
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} language{'s' if choose != 1 else ''} of your choice."
        tpl = build_choice_template(envelope, cid, source, "Languages", description=description)
        if tpl:
            templates.append(tpl)
    return templates


def _species_choice_templates(catalog: Catalog, race: dict, race_id: str, subrace: dict | None) -> list[dict]:
    templates = []
    trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
    for ref in trait_refs:
        trait = catalog.traits.get(ref["index"])
        if not trait:
            continue
        envelope = (trait.get("trait_specific") or {}).get("subtrait_options")
        if not envelope:
            continue
        cid = f"species:{race_id}:trait:{trait['index']}"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        # subtrait_options carries no 'desc' of its own — the description
        # text lives on the parent trait (verified directly against
        # 5e-SRD-Traits.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, trait["name"], description=_join_desc(trait.get("desc")))
        if tpl:
            templates.append(tpl)

    # Race/subrace bonus-language choices (e.g. Human, Half-Elf) use the
    # same options_array shape as everything else build_choice_options
    # already handles, so this is a real Choice, not just a warning.
    for src, src_id in ((race, race_id), (subrace, subrace.get("index") if subrace else None)):
        if not src:
            continue
        envelope = src.get("language_options")
        if not envelope:
            continue
        cid = f"species:{race_id}:languages"
        if src is subrace:
            cid = f"species:{race_id}:subspecies:{src_id}:languages"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} additional language{'s' if choose != 1 else ''} of your choice."
        tpl = build_choice_template(envelope, cid, source, "Bonus Language", description=description)
        if tpl:
            templates.append(tpl)

    return templates


def _asi_option_label(deltas: list[tuple[str, int]]) -> str:
    return " and ".join(f"{ab} +{delta}" for ab, delta in deltas)


def _asi_choice_templates(
    cls_id: str, cls_name: str, asi_levels: list[int], scores_by_level: dict[int, dict[str, int]],
) -> list[dict]:
    templates = []
    for lvl in asi_levels:
        current_scores = scores_by_level.get(lvl, {})
        options = []
        for option_id, deltas in asi_mod.asi_combinations():
            option = {"id": option_id, "label": _asi_option_label(deltas)}
            if asi_mod.asi_exceeds_cap(deltas, current_scores):
                option["disabled"] = True
                option["disabledReason"] = "would exceed the ability score cap of 20"
            options.append(option)
        cid = f"class:{cls_id}:{lvl}:asi"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": "Ability Score Improvement",
            "description": "Increase one ability score by 2, or two ability scores by 1 each.",
            "count": 1,
            "options": options,
        })
    return templates


def _equipment_choice_templates(entity: dict, source_kind: str, source_id: str, source_label: str) -> tuple[list[dict], int]:
    templates = []
    dropped_envelopes = 0
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        tpl = build_choice_template(envelope, cid, source, "Starting Equipment")
        if not tpl:
            dropped_envelopes += 1
            continue
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (tpl["description"] + " (Note: one or more of the original options for this choice aren't available yet and have been left out.)").strip()
        templates.append(tpl)
    return templates, dropped_envelopes


def _spell_options(catalog: Catalog, cls_id: str, spell_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if s["level"] == spell_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: s["name"])
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _spell_options_up_to(catalog: Catalog, cls_id: str, max_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if 1 <= s["level"] <= max_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _highest_spell_slot_level(spellcasting: dict) -> int:
    highest = 0
    for n in range(1, 10):
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0:
            highest = n
    return highest


def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int, class_level: int,
) -> list[dict]:
    if not level_row:
        return []
    spellcasting = level_row.get("spellcasting") or {}
    templates = []
    # No `level` in source — these choices span every level a spellcaster
    # has reached (count grows as they level up), so they're not anchored
    # to one specific level the way a feature/ASI choice is.
    source = {"kind": "class", "id": cls_id, "label": cls["name"]}

    cantrips_known = spellcasting.get("cantrips_known", 0)
    if cantrips_known > 0:
        envelope = {"choose": cantrips_known, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, cls_id, spell_level=0),
        }}
        cid = f"class:{cls_id}:spells-cantrips"
        description = f"Choose {cantrips_known} cantrip{'s' if cantrips_known != 1 else ''} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, "Cantrips Known", description=description)
        if tpl:
            templates.append(tpl)

    known_count = spells_mod.known_spell_count(level_row, ability_modifier, class_level=class_level, cls_id=cls_id)
    if known_count > 0:
        max_spell_level = _highest_spell_slot_level(spellcasting)
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": _spell_options_up_to(catalog, cls_id, max_spell_level),
        }}
        cid = f"class:{cls_id}:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None
        label = "Spells Known" if is_known_caster else "Prepared Spells"
        verb = "know" if is_known_caster else "prepare"
        level_word = "spell" if max_spell_level == 1 else f"level-{max_spell_level}-or-lower spell"
        description = f"Choose {known_count} {level_word}{'s' if known_count != 1 else ''} to {verb} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
            templates.append(tpl)

    return templates


def _fixed_equipment(entries: list[dict], item_lookup: dict) -> list[dict]:
    result = []
    for entry in entries:
        equipment_ref = entry.get("equipment") or {}
        item_id = equipment_ref.get("index")
        item = item_lookup.get(item_id) if item_id else None
        if not item:
            continue
        result.append({"itemId": item_id, "name": item["name"], "qty": entry.get("quantity", 1)})
    return result


def _gather_equipped_items(
    equipment_choices: list[dict], added_entries: list[dict], item_lookup: dict,
) -> list[dict]:
    equipped: list[dict] = []
    for choice in equipment_choices:
        for selected_id in choice["selected"]:
            for item_id in selected_id.split("+"):
                item = item_lookup.get(item_id)
                if item:
                    equipped.append(item)
    for entry in added_entries:
        if not isinstance(entry, dict) or not entry.get("equipped"):
            continue
        item_id = entry.get("itemId")
        item = item_lookup.get(item_id) if isinstance(item_id, str) else None
        if item:
            equipped.append(item)
    return equipped


def _chosen_equipment(equipment_choices: list[dict], item_lookup: dict) -> list[dict]:
    result: list[dict] = []
    for choice in equipment_choices:
        for selected_id in choice["selected"]:
            for item_id in selected_id.split("+"):
                item = item_lookup.get(item_id)
                if item:
                    result.append({"itemId": item_id, "name": item["name"], "qty": 1})
    return result


def _apply_background_overlap(class_templates: list[dict], bg: dict | None) -> None:
    if not bg:
        return
    granted = {p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-")}
    if not granted:
        return
    for tpl in class_templates:
        for opt in tpl["options"]:
            if opt["id"] in granted:
                opt["disabled"] = True
                opt["disabledReason"] = f"already granted by {bg['name']}"


def _apply_species_overlap(class_templates: list[dict], race: dict | None, subrace: dict | None, catalog: Catalog) -> None:
    """Mirrors _apply_background_overlap: race/subrace traits can grant a
    skill proficiency for free (e.g. Elf's Keen Senses grants
    skill-perception), and a class's own skill-choice list can include that
    same skill (e.g. Rogue's prof-choice-0). Without this, a player could
    spend a class choice slot on a skill they already have for free, with
    no disabled flag or warning — this closes that gap the same way the
    background path already does."""
    if not race:
        return
    trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
    granted: set[str] = set()
    for ref in trait_refs:
        trait = catalog.traits.get(ref["index"])
        if not trait:
            continue
        granted.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
    if not granted:
        return
    for tpl in class_templates:
        for opt in tpl["options"]:
            if opt["id"] in granted:
                opt["disabled"] = True
                opt["disabledReason"] = f"already granted by {race['name']}"


def resolve(draft: dict, catalog: Catalog) -> dict:
    problems: list[dict] = []
    warnings: list[dict] = []

    classes_raw = draft.get("classes")
    if classes_raw is None:
        classes_raw = []
    elif not isinstance(classes_raw, list):
        problems.append({"id": "malformed-classes", "message": "'classes' must be a list."})
        classes_raw = []
    classes = [c for c in classes_raw if isinstance(c, dict)]
    if len(classes) != len(classes_raw):
        problems.append({"id": "malformed-class-entry", "message": "one or more entries in 'classes' were not objects and were ignored."})

    if len(classes) > 1:
        problems.append({"id": "multiclass-unsupported", "message": "Multiclassing isn't supported yet — pick a single class."})
        classes = classes[:1]

    cls_entry = classes[0] if classes else None
    cls_id = cls_entry.get("classId") if cls_entry else None
    subclass_id = cls_entry.get("subclassId") if cls_entry else None
    level = 1
    if cls_entry:
        raw_level = cls_entry.get("level", 1)
        try:
            level = int(raw_level)
        except (TypeError, ValueError):
            problems.append({"id": "level-unsupported", "message": f"Level {raw_level!r} isn't a valid number; using 1 instead."})
            level = 1
        if not (1 <= level <= 20):
            problems.append({"id": "level-unsupported", "message": f"Level {level} is out of the 1-20 range; using 1 instead."})
            level = 1

    cls = catalog.classes.get(cls_id) if cls_id else None
    if cls_id and not cls:
        problems.append({"id": "unknown-class", "message": f"Unknown class '{cls_id}'."})

    subclass = catalog.subclasses.get(subclass_id) if subclass_id else None
    if subclass_id and not subclass:
        problems.append({"id": "unknown-subclass", "message": f"Unknown subclass '{subclass_id}'."})
        subclass_id = None
    elif subclass and cls_id and subclass.get("class", {}).get("index") != cls_id:
        problems.append({
            "id": "subclass-mismatch",
            "message": f"'{subclass['name']}' isn't a subclass of the selected class.",
        })
        subclass_id = None

    background_raw = draft.get("background")
    if background_raw is not None and not isinstance(background_raw, dict):
        problems.append({"id": "malformed-background", "message": "'background' must be an object."})
        background_raw = {}
    background_dict = background_raw or {}
    bg_id = background_dict.get("id")
    bg = catalog.backgrounds.get(bg_id) if bg_id else None
    if bg_id and not bg:
        problems.append({"id": "unknown-background", "message": f"Unknown background '{bg_id}'."})

    species_raw = draft.get("species")
    if species_raw is not None and not isinstance(species_raw, dict):
        problems.append({"id": "malformed-species", "message": "'species' must be an object."})
        species_raw = {}
    species = species_raw or {}
    race_id = species.get("id")
    race = catalog.races.get(race_id) if race_id else None
    if race_id and not race:
        problems.append({"id": "unknown-species", "message": f"Unknown species '{race_id}'."})

    subrace_id = species.get("subspeciesId")
    subrace = catalog.subraces.get(subrace_id) if subrace_id else None
    if subrace_id and not subrace:
        problems.append({"id": "unknown-subspecies", "message": f"Unknown subspecies '{subrace_id}'."})
    elif subrace and subrace.get("race", {}).get("index") != race_id:
        problems.append({
            "id": "subspecies-mismatch",
            "message": f"'{subrace['name']}' isn't a subspecies of the selected species.",
        })
        subrace = None

    # Final ability scores: base + species bonuses (2014-rules placement —
    # backgrounds don't grant ability bonuses in this ruleset; see spec §4).
    base_scores = (draft.get("abilities") or {}).get("base") or {}
    species_bonuses = _species_ability_bonuses(race, subrace)
    species_ability_choice_tpl = _species_ability_bonus_choice_template(race, subrace, race_id)
    if species_ability_choice_tpl:
        species_choices_raw = species.get("choices") if isinstance(species.get("choices"), dict) else {}
        valid_ability_ids = {o["id"] for o in species_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = species_choices_raw.get(species_ability_choice_tpl["id"]) or []
        # Dedupe BEFORE capping to `count` and applying bonuses — otherwise a
        # duplicate selection (e.g. ["str", "str"]) would apply the same
        # ability's bonus twice with no problem reported.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_abilities = [s for s in deduped_selected if s in valid_ability_ids][: species_ability_choice_tpl["count"]]
        for ab_id in selected_abilities:
            ab_key = ab_id.upper()
            species_bonuses[ab_key] = species_bonuses.get(ab_key, 0) + 1  # bundled data's `bonus` is always 1; if a future data source varies this, look it up from the option instead of hardcoding 1 here
    final_scores: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        raw = base_scores.get(ab, 10)
        try:
            base_score = int(raw)
        except (TypeError, ValueError):
            problems.append({"id": f"ability-invalid-{ab}", "message": f"{ab} score {raw!r} isn't a valid number; using 10 instead."})
            base_score = 10
        final_scores[ab] = base_score + species_bonuses.get(ab, 0)
    for ab, score in final_scores.items():
        if not (1 <= score <= 30):
            problems.append({"id": f"ability-out-of-range-{ab}", "message": f"{ab} score {score} is out of the 1-30 range."})

    class_choices_raw = cls_entry.get("choices") if cls_entry else None
    class_choices = class_choices_raw if isinstance(class_choices_raw, dict) else {}

    asi_levels: list[int] = []
    if cls and cls_id:
        asi_levels = _asi_granting_levels(catalog, cls_id, level)
    asi_scores_by_level, final_scores = _apply_asi_progression(final_scores, asi_levels, class_choices, cls_id)

    modifiers = derived_mod.ability_modifiers(final_scores)
    prof_bonus_row = catalog.class_level_row(cls_id, level) if cls and cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2

    # Choice templates from every source.
    choice_templates: list[dict] = []
    level_row = None
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.class_level_row(cls_id, level)
        feature_refs = _cumulative_feature_refs(catalog, cls_id, subclass_id, level)
        choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], feature_refs, subclass_id)
        choice_templates += _asi_choice_templates(cls_id, cls["name"], asi_levels, asi_scores_by_level)
        spell_ability = spells_mod.spellcasting_ability(cls)
        if spell_ability and level_row:
            choice_templates += _spell_choice_templates(catalog, cls, cls_id, level_row, modifiers[spell_ability], class_level=level)
    if bg and bg_id:
        choice_templates += _background_choice_templates(bg, bg_id)
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)
        if species_ability_choice_tpl:
            choice_templates.append(species_ability_choice_tpl)
    if cls and cls_id:
        cls_equipment_templates, cls_dropped = _equipment_choice_templates(cls, "class", cls_id, cls["name"])
        choice_templates += cls_equipment_templates
        if cls_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-class-{cls_id}",
                "message": f"{cls['name']}'s starting equipment has {cls_dropped} choice(s) that can't be shown yet and were left out.",
            })
    if bg and bg_id:
        bg_equipment_templates, bg_dropped = _equipment_choice_templates(bg, "background", bg_id, bg["name"])
        choice_templates += bg_equipment_templates
        if bg_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-background-{bg_id}",
                "message": f"{bg['name']}'s starting equipment has {bg_dropped} choice(s) that can't be shown yet and were left out.",
            })

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)
    _apply_species_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], race, subrace, catalog)

    # Apply the draft's own selections onto each template to get a real Choice.
    equipment_raw = draft.get("equipment")
    equipment_dict = equipment_raw if isinstance(equipment_raw, dict) else {}
    equipment_choices_raw = equipment_raw.get("choices") if isinstance(equipment_raw, dict) else None
    if equipment_choices_raw is not None and not isinstance(equipment_choices_raw, dict):
        problems.append({"id": "malformed-equipment-choices", "message": "'equipment.choices' must be an object."})
        equipment_choices_raw = None

    details = _sanitized_details(draft.get("details"))

    all_selections: dict[str, list[str]] = {}
    if cls_entry:
        all_selections.update(cls_entry.get("choices") or {})
    all_selections.update(background_dict.get("choices") or {})
    all_selections.update(species.get("choices") or {})
    all_selections.update(equipment_choices_raw or {})

    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        # Dedupe (preserving first-occurrence order) so this generic pass
        # agrees with the early species-ability-bonus pass above, which
        # dedupes the same underlying selection before applying bonuses.
        raw_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected = [s for s in raw_selected if s in valid_ids]
        if len(selected) > tpl["count"]:
            problems.append({
                "id": f"over-selected-{tpl['id']}",
                "message": f"'{tpl['label']}' allows {tpl['count']} selection(s) but {len(selected)} were submitted.",
            })
            selected = selected[: tpl["count"]]
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})

    added_raw = equipment_dict.get("added")
    if added_raw is None:
        added_raw = []
    elif not isinstance(added_raw, list):
        problems.append({"id": "malformed-equipment-added", "message": "'equipment.added' must be a list."})
        added_raw = []

    added_resolved = []
    for entry in added_raw:
        if not isinstance(entry, dict):
            continue
        item_id = entry.get("itemId")
        item = catalog.items.get(item_id) if isinstance(item_id, str) else None
        if not item:
            continue
        added_resolved.append({
            "itemId": item_id, "name": item["name"],
            "qty": entry.get("qty", 1), "equipped": bool(entry.get("equipped", False)),
        })

    equipment_choices = [c for c in choices if c["source"]["kind"] == "equipment"]
    equipped_items = _gather_equipped_items(equipment_choices, added_raw if isinstance(added_raw, list) else [], catalog.items)
    chosen_equipment = _chosen_equipment(equipment_choices, catalog.items)

    cantrip_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:spells-cantrips"), None) if cls_id else None
    known_spells_choice = next((c for c in choices if c["id"] == f"class:{cls_id}:spells-known"), None) if cls_id else None

    def _spell_summaries(choice: dict | None) -> list[dict]:
        if not choice:
            return []
        return [
            {"id": sid, "name": catalog.spells[sid]["name"], "level": catalog.spells[sid]["level"]}
            for sid in choice["selected"] if sid in catalog.spells
        ]

    spell_ability = spells_mod.spellcasting_ability(cls) if cls else None
    has_spellcasting_this_level = bool(cantrip_choice or known_spells_choice)
    spells_summary = None
    spell_save_dc = None
    spell_attack_bonus = None
    if has_spellcasting_this_level and spell_ability:
        spells_summary = {"cantrips": _spell_summaries(cantrip_choice), "known": _spell_summaries(known_spells_choice)}
        spell_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[spell_ability])
        spell_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[spell_ability])

    granted_equipment = []
    if cls:
        granted_equipment += _fixed_equipment(cls.get("starting_equipment", []), catalog.items)
    if bg:
        granted_equipment += _fixed_equipment(bg.get("starting_equipment", []), catalog.items)

    for granted in granted_equipment:
        granted_item = catalog.items.get(granted["itemId"])
        if granted_item:
            equipped_items.append(granted_item)

    # Derived stats.
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class":
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            proficient_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))

    proficient_save_abilities = [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])]

    hit_die = cls.get("hit_die") if cls else None
    hp_type = (draft.get("preferences") or {}).get("hitPointType")
    if hp_type not in ("fixed", "manual"):
        hp_type = "fixed"
    hp_rolls_raw = cls_entry.get("hpRolls") if cls_entry else None
    hp_rolls = {k: v for k, v in hp_rolls_raw.items() if isinstance(v, int)} if isinstance(hp_rolls_raw, dict) else {}
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    skills = derived_mod.skill_scores(modifiers, list(proficient_skills), prof_bonus)
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_at_level(hit_die, modifiers["CON"], level, hp_type, hp_rolls),
        "hitDice": f"{level}d{hit_die}" if hit_die else None,
        "armorClass": equipment_mod.armor_class_from_gear(equipped_items, modifiers["DEX"]),
        "speed": race.get("speed") if race else None,
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills),
        "spellSaveDC": spell_save_dc,
        "spellAttackBonus": spell_attack_bonus,
    }

    fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + \
        [lang["index"] for lang in (race.get("languages", []) if race else [])]
    chosen_languages = [
        s for c in choices
        if c["source"]["kind"] in ("background", "species") and c["id"].endswith(":languages")
        for s in c["selected"]
    ]

    sheet = {
        "name": draft.get("name") or "",
        "level": level if cls else 0,
        "class": {
            "id": cls_id, "name": cls["name"],
            "subclass": {"id": subclass_id, "name": subclass["name"]} if subclass_id and subclass else None,
        } if cls else None,
        "background": {"id": bg_id, "name": bg["name"]} if bg else None,
        "species": {
            "id": race_id, "name": race["name"],
            "subspecies": {"id": subrace_id, "name": subrace["name"]} if subrace else None,
        } if race else None,
        "abilities": final_scores,
        "proficiencies": {
            "skills": sorted(proficient_skills),
            "savingThrows": proficient_save_abilities,
            "languages": sorted(set(fixed_languages + chosen_languages)),
        },
        "equipment": {"granted": granted_equipment, "chosen": chosen_equipment, "added": added_resolved},
        "spells": spells_summary,
        "details": details,
    }

    return {
        "sheet": sheet,
        "choices": choices,
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": [],
    }
