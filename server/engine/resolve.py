"""resolve(draft, catalog) -> Resolution — the single entry point for all
character-rules computation, per the architecture spec's engine contract
(docs/superpowers/specs/2026-09-16-builder-v2-architecture.md §3). One
fixed-order pass: sources → species+background ability bonuses (both flow
into the SAME early pass — see _background_ability_bonuses, Phase 4b Task
4) → final ability scores → derived stats → choice generation/validation
(§4a) — never iterates to a fixpoint.

Leveling (1-20) is in scope: each resolved class's subclassId is read but
never trusted to gate a feature choice unless it actually matches, so any
feature gated to a specific subclass is filtered out rather than guessed
at. Equipment IS in scope as of Phase 2a — see engine/equipment.py and the
_equipment_choice_templates/_gather_equipped_items/_fixed_equipment
functions below. Spellcasting IS in scope as of Phase 2c — see
engine/spells.py and the _spell_choice_templates function below.

Single-class leveling (1-20), subclass selection, and ASI choices ARE in
scope as of Phase 3a — see engine/asi.py, the _asi_choice_templates/
_apply_asi_progression functions, and SUBCLASS_UNLOCK_LEVEL in
catalog/reference_data.py.

Multiclassing core IS in scope as of Phase 3b-i: draft.classes is a list
(not just a single class), resolved via resolved_classes with per-class
progression (its own level, subclass, ASIs, feature/spell choices), a
combined proficiency bonus and hit-dice string, and the multiclass-aware
proficiency rules — a PRIMARY class (resolved_classes[0], index 0) gets
its full normal grant and level-1 proficiency CHOICE, while every
SECONDARY class gets only its (usually smaller) multi_classing.*
fixed-proficiency grant and proficiency_choices choice (see
_multiclass_proficiency_choice_templates and the `rc["index"] == 0`
gating throughout resolve()), plus multiclass ability-score prerequisites
(_multiclass_prerequisite_problems). sheet["spells"] aggregates every
resolved class's spellcasting, not just the primary's.

A genuinely COMBINED spell-slot table across multiple caster classes IS in
scope as of Phase 3b-ii — see engine/spells.py's combined_caster_level/
multiclass_spell_slots/single_class_spell_slots/warlock_pact_magic_slots.
derived["spellSlots"] is the shared pool, but per PHB 164 the combined
round-down table is only used when MORE THAN ONE class grants spell
slots; with exactly one slot-granting class (even alongside other
non-caster classes), that class's own single-class progression is looked
up directly instead (see the `slot_granting_entries` branch below — fixed
post-review, since the round-down table silently undercounts a lone half
caster at every odd level). derived["warlockSpellSlots"] is Warlock's own
Pact Magic, looked up separately at Warlock's own class level and never
folded into either path above, per RAW. spellSaveDC/spellAttackBonus are
no longer top-level derived scalars — each caster in sheet["spells"] now
carries its own, since a multiclass character's casters each use their
own spellcasting ability. Still out of scope: pruning multiclass-related
warnings (Phase 3c).
"""
from __future__ import annotations

import re
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Any

from catalog import feat_effects_data, reference_data
from catalog.choices import build_choice_template, build_equipment_choice, pack_quantities, pack_units
from catalog.loader import Catalog
from i18n.messages import Msg, msg
from i18n.messages import msg as _format_msg
from catalog.official_source import slug, SAVE_ABILITY_NAMES
from catalog.reference_data import (
    ABILITIES, HEAVY_ARMOR_SPEED_EXEMPT_RACES, HEAVY_ARMOR_SPEED_EXEMPT_TRAITS, SPECIFIC_WEAPON_PROFICIENCY_IDS, SRD_TRAIT_EFFECTS, SUBCLASS_PROFICIENCIES, SUBCLASS_EXTRA_FEATURES,
    SUBCLASS_SPELLCASTING_ABILITY, SUBCLASS_SPELL_SCHOOL_LIMITS, wizard_spell_picks, ruleset_allows, subclass_unlock_level,
)
from . import asi as asi_mod
from . import attacks as attacks_mod
from . import class_choices_2024
from . import subclass_options_2024
from . import option_source as option_source_mod
from . import innate_uses, subclass_innate_2024
from . import subclass_spells_2024
from . import class_resources as class_resources_mod
from . import species_resources as species_resources_mod
from . import derived as derived_mod
from . import equipment as equipment_mod
from . import species_traits as species_traits_mod
from . import worn as worn_mod
from . import feat_effects as feat_effects_mod
from . import feat_spell_tables
from . import features as features_mod
from . import sheet_features as sheet_features_mod
from . import spells as spells_mod
from .normalize import normalize_draft
from .resolve_feats import (  # S17: moved to resolve_feats.py, re-exported here
    _ASI_EPIC_BOON_LEVEL,
    _ASI_EXCLUDED_FEAT_INDICES,
    _ASI_FEAT_CATEGORIES,
    _ASI_FEAT_CATEGORIES_DEFAULT,
    _ASI_GATE_PREREQUISITE_KEYS,
    _BATTLE_MASTER_FEATURE,
    _FEAT_GROUP_BY_CATEGORY,
    _FIGHTER_STYLE_FEATURE,
    _FIGHTING_STYLE_CATEGORIES,
    _FS_FEAT_CATEGORIES,
    _HeldFeatState,
    _KNOWN_PREREQUISITE_FEATURES,
    _LESSONS_REASON,
    _OPTION_PICK_CARDS,
    _PREREQ_MSG_MEMO,
    _PROFICIENCY_PREREQ_SATISFIERS,
    _SPELLCASTING_PREREQUISITE_FEATURES,
    _SRD_INVOCATIONS_FEATURE,
    _SRD_METAMAGIC_FEATURE,
    _STRUCTURED_FEAT_PREREQUISITE_KEYS,
    _VISIBLE_SPELLS,
    _XPHB_BATTLE_MASTER_FEATURE,
    _alt_is_verifiable,
    _alt_value_is_valid,
    _apply_asi_progression,
    _armor_category_msg,
    _asi_feat_in_pool,
    _asi_granting_levels,
    _asi_pick_honored,
    _background_proficiency_choice_label,
    _base_holder,
    _feat_ability_bonus_choice_templates,
    _feat_ability_bonus_deltas,
    _feat_ability_bonuses,
    _feat_ability_cap,
    _feat_build_position,
    _feat_choice_templates,
    _feat_cid_prefix,
    _feat_expertise_skills,
    _feat_extra_templates,
    _feat_group,
    _feat_group_order,
    _feat_innate_spells,
    _feat_instance_key,
    _feat_languages,
    _feat_lessons_templates,
    _feat_mark_spell_ids,
    _feat_name_key,
    _feat_offered,
    _feat_option_prerequisite_met,
    _feat_options,
    _feat_prerequisite_alt_met,
    _feat_prerequisite_failing_parts,
    _feat_prerequisite_problems,
    _feat_prerequisite_unmet_reason,
    _feat_proficiency_ids,
    _feat_ref_index,
    _feat_saving_throw_proficiencies,
    _feat_selected_choice_values,
    _feat_senses,
    _feat_source_allowed,
    _feat_spell_ability,
    _feat_spell_choice_templates,
    _feat_structured_prerequisite,
    _feature_prerequisite_met,
    _fi_seen_add,
    _freeze_msg_param,
    _innate_entry_to_sheet,
    _is_asi_eligible_feat,
    _join_desc,
    _lessons_card,
    _lowered_sources,
    _option_pick_options,
    _optional_feature_options,
    _prereq_msg,
    _proficiency_entry_key,
    _race_entry_met,
    _race_entry_phrase,
    _race_name_key,
    _resolve_asi_selected_feats,
    _resolve_granted_feats,
    _source_allowed,
    _spell_filter_description,
    _spell_filter_options,
    _spell_visible,
    _srd_style_options,
    _stored_asi_feat_pick,
    _taken_add,
    _taken_reason,
    _visible_spell_ids,
    _with_extra_metamagic,
    fed_option_picks,
)
from .resolve_species import (  # S17: moved to resolve_species.py, re-exported here
    _ALL_ALTERNATIVES,
    _FollowedVariants,
    _ability_sources,
    _apply_background_overlap,
    _apply_species_overlap,
    _background_ability_bonus_choice_template,
    _background_ability_bonus_deltas,
    _background_ability_bonuses,
    _background_choice_templates,
    _background_feat_grant_slots,
    _draconic_ancestry_row_label,
    _either_or_default_pick,
    _followed_variants,
    _held_race_state,
    _selected_species_alternative,
    _selected_species_spell_ability,
    _selected_species_variant,
    _species_ability_bonus_choice_template,
    _species_ability_bonuses,
    _species_alternatives,
    _species_cantrip_template,
    _species_choice_templates,
    _species_condition_immunities,
    _species_damage_modifiers,
    _species_draconic_ancestry_template,
    _species_equal_walk_modes,
    _species_feat_choice_template,
    _species_feat_grant_slots,
    _species_feat_pool,
    _species_innate_entries,
    _species_innate_spells,
    _species_senses,
    _species_size,
    _species_size_template,
    _species_speeds,
    _species_spell_ability_candidates,
    _species_spell_ability_template,
    _species_trait_spell_choices,
    _species_trait_spell_cid,
    _species_variant_template,
    _srd_trait_effects,
    _subrace_replaces_spell_trait,
)
from .resolve_spells import (  # S17: moved to resolve_spells.py, re-exported here
    MAX_SOURCES,
    _ARCANUM_LEVELS,
    _add_mark_options,
    _additional_secrets_options,
    _additional_secrets_templates,
    _apply_school_limit,
    _apply_secrets_cap,
    _effective_caster,
    _highest_spell_slot_level,
    _label_mark_options,
    _magical_secrets_options,
    _mystic_arcanum_templates,
    _normalised_sources,
    _spell_choice_templates,
    _spell_options,
    _spell_options_up_to,
    _subclass_spell_ids,
    _subclass_visible,
    _tag_spell_level_groups,
    _wizard_spellbook_template,
)
from .resolve_gates import (  # S17: moved to resolve_gates.py, re-exported here
    _ASI_FEAT_CID_RE,
    _BATTLE_MASTER_CID,
    _FEAT_PICK_GROUPS,
    _PICK_PREFIX,
    _SRD_METAMAGIC_CID,
    _expertise_selected_values,
    _gate_distinct_choices,
    _gate_duplicate_picks,
    _gate_duplicate_skill_picks,
    _gate_expertise_choices,
    _gate_feat_invocation_prereqs,
    _gate_invocation_choices,
    _gate_mastery_choices,
    _gate_positioned_proficiencies,
    _gate_save_picks,
    _invocation_unmet,
    _is_count_variable_choice,
    _is_expertise_choice,
    _is_mastery_choice,
    _is_skill_id,
    _mastery_filter_reason,
    _multiclass_prerequisite_problems,
    _prof_or_expertise_priors,
    _proficiency_grants,
    _save_grant_positions,
    _weapon_masteries,
)

_DETAIL_FIELDS = (
    "alignment", "faith", "lifestyle",
    "age", "height", "weight", "eyes", "skin", "hair",
    "personalityTraits", "ideals", "bonds", "flaws",
    "backstory", "organizations", "allies", "enemies", "notes",
)


_POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
_STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]


def _ability_method_problems(abilities: dict) -> list[dict]:
    """Blocking problems for a base-score set that cannot have come from the
    chosen generation method (frontend/src/pages/AbilitiesPage.tsx enforces the
    same limits in its controls). 'manual' is unchecked; a standard array whose
    six scores are all still 10 is the untouched default, not an error."""
    method = abilities.get("method")
    base = abilities.get("base") or {}
    scores = [base.get(ab, 10) for ab in ABILITIES]
    out: list[dict] = []
    if method == "pointbuy":
        if any(not 8 <= v <= 15 for v in scores):
            out.append({"id": "point-buy-out-of-range", "message": msg("point-buy-out-of-range")})
        else:
            spent = sum(_POINT_BUY_COST[v] for v in scores)
            if spent > 27:
                out.append({"id": "point-buy-over-budget", "message": msg("point-buy-over-budget", spent=spent)})
    elif method == "standard":
        if scores != [10] * 6 and sorted(scores, reverse=True) != _STANDARD_ARRAY:
            out.append({"id": "standard-array-mismatch", "message": msg("standard-array-mismatch")})
    elif method == "roll":
        if any(not 3 <= v <= 18 for v in scores):
            out.append({"id": "roll-out-of-range", "message": msg("roll-out-of-range")})
    return out


RULESETS = ("2014", "2024", "mixed")


def _asi_policy(ruleset: str, race: dict | None, subrace: dict | None, bg: dict | None) -> tuple[bool, bool, list[dict]]:
    """Which ability-score-increase sources apply under a ruleset:
    (species_on, background_on, warnings). Every conflict is a WARNING, never
    a problem - a house-rule mix must still export. "Species ASI" means ALL of
    it: fixed bonuses and choice templates on the species and subspecies
    (Half-Elf, VRGR lineages, Variant Human, subrace options)."""
    species_has = bool(_species_ability_bonuses(race, subrace)) or any(
        src.get("ability_bonus_options") for src in _ability_sources(race, subrace)
    )
    bg_has = bool(bg and bg.get("ability_bonus_options"))
    warnings: list[dict] = []
    if ruleset == "2014":
        if bg_has:
            warnings.append({
                "id": "ruleset-2014-background-asi-ignored",
                "message": msg("ruleset-2014-background-asi-ignored", name=bg["name"]),
            })
        return True, False, warnings
    if ruleset == "2024":
        if species_has:
            warnings.append({
                "id": "ruleset-2024-species-asi-ignored",
                "message": msg("ruleset-2024-species-asi-ignored"),
            })
        if bg:
            if not bg_has:
                warnings.append({
                    "id": "ruleset-2024-background-no-asi",
                    "message": msg("ruleset-2024-background-no-asi", name=bg["name"]),
                })
            if not (bg.get("feats") or bg.get("feat_options") or bg.get("feat_grants")):
                warnings.append({
                    "id": "ruleset-2024-background-no-origin-feat",
                    "message": msg("ruleset-2024-background-no-origin-feat", name=bg["name"]),
                })
        return False, True, warnings
    if bg_has and species_has:
        warnings.append({
            "id": "asi-double-dip-prevented",
            "message": msg("asi-double-dip-prevented"),
        })
        return False, True, warnings
    return True, True, warnings


def _needs_ravenloft(feat: dict) -> bool:
    """B3: the feat's data prerequisite names a campaign and it is Ravenloft (all nine RHW Dark Gift feats: `prerequisite:
    [{"campaign": ["Ravenloft"]}]`)."""
    return any(isinstance(p, dict) and "Ravenloft" in (p.get("campaign") or ()) for p in feat.get("prerequisite") or ())


def _dark_gift_ravenloft_warnings(feats: list[dict], sources) -> list[dict]:
    """B3 (owner decision 2026-11-09): a NON-BLOCKING warning for each held Dark Gift feat while the RHW book is switched off in
    `sources` (the app has no campaign setting; an empty `sources` list means every book is on). Nothing is removed or disabled."""
    if _source_allowed({"source": "RHW"}, sources):
        return []
    out, seen = [], set()
    for feat in feats:
        if feat["index"] in seen or not _needs_ravenloft(feat):
            continue
        seen.add(feat["index"])
        out.append({"id": f"dark-gift-needs-ravenloft-{feat['index']}", "message": msg("dark-gift-needs-ravenloft", feat=feat["name"])})
    return out


def _label_is(label, key: str) -> bool:
    """True when a card label is the tagged catalog message `key` (the engine compares labels by key, never by text, so
    the comparison does not depend on the wording or on the language)."""
    return getattr(label, "key", None) == key


def _provisional_choice_label(envelope: dict):
    """The first label of a class proficiency envelope; `_class_choice_templates` relabels a non-skill one afterwards."""
    kind = envelope.get("type")
    if kind == "proficiencies":
        return msg("label-skill-proficiencies")
    return kind.title() if kind else msg("label-choice")


def _class_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(cls.get("proficiency_choices", [])):
        cid = f"class:{cls_id}:1:prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"], "level": 1}
        tpl = build_choice_template(envelope, cid, source, _provisional_choice_label(envelope))
        if not tpl:
            continue
        # Some classes (Bard, Monk) have a SECOND proficiency_choices entry
        # also typed "proficiencies" that isn't actually a skill choice
        # (instruments/tools) — relabel based on what the resolved options
        # actually are, not the envelope's own (misleading) type field.
        if tpl["options"] and _label_is(tpl["label"], "label-skill-proficiencies") and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = msg("label-tool-proficiencies")
        templates.append(tpl)
    return templates


def _multiclass_proficiency_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    """Mirrors _class_choice_templates exactly, but sourced from
    multi_classing.proficiency_choices instead of the class's own
    top-level proficiency_choices — this is the EXTRA skill/tool choice
    a class grants when taken as a SECOND-OR-LATER class (confirmed
    empirically: Bard, Ranger, Rogue each have this; Bard has two
    envelopes — a skill choice and a musical-instrument choice)."""
    templates = []
    for i, envelope in enumerate(cls.get("multi_classing", {}).get("proficiency_choices", [])):
        cid = f"class:{cls_id}:multiclass-prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"]}
        tpl = build_choice_template(envelope, cid, source, _provisional_choice_label(envelope))
        if not tpl:
            continue
        if tpl["options"] and _label_is(tpl["label"], "label-skill-proficiencies") and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = msg("label-tool-proficiencies")
        templates.append(tpl)
    return templates


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
        for lvl, idx in SUBCLASS_EXTRA_FEATURES.get(subclass_id, []):
            if lvl <= max_level:
                refs.append((lvl, {"index": idx}))
    return refs


def _expertise_envelope(raw: dict) -> dict | None:
    """Flattens a feature's `expertise_options` into a plain
    {"choose", "from"} envelope. Bard's is already flat; Rogue's nests
    "two skills" and "one skill + thieves' tools" as alternatives, which all
    come down to the same rule: choose 2 proficient skills/tools. The
    proficiency restriction is applied afterwards (_gate_expertise_choices)."""
    options = (raw.get("from") or {}).get("options") or []
    nested = next((o for o in options if o.get("option_type") == "choice"), None)
    count = nested["choice"].get("choose", 2) if nested else raw.get("choose", 1)
    flat: list[dict] = []
    seen: set[str] = set()

    def collect(opts):
        for o in opts:
            if o.get("option_type") == "reference" and o["item"]["index"] not in seen:
                seen.add(o["item"]["index"])
                flat.append({"option_type": "reference", "item": {
                    "index": o["item"]["index"], "name": o["item"]["name"].replace("Skill: ", "")}})
            elif o.get("option_type") == "choice":
                collect((o["choice"].get("from") or {}).get("options") or [])
            elif o.get("option_type") == "multiple":
                collect(o.get("items") or [])

    collect(options)
    if not flat:
        return None
    return {"choose": count, "from": {"option_set_type": "options_array", "options": flat}}


def _string_options_envelope(raw: dict) -> dict:
    """enemy_type_options / terrain_type_options list bare strings."""
    opts = [{"option_type": "string", "string": str(o).capitalize()} for o in (raw.get("from") or {}).get("options") or []]
    return {"choose": raw.get("choose", 1), "from": {"option_set_type": "options_array", "options": opts}}


def _invocation_templates(catalog: Catalog, feature: dict, cid: str, source: dict, class_level: int) -> dict | None:
    row = catalog.class_level_row(source["id"], class_level) or {}
    count = (row.get("class_specific") or {}).get("invocations_known", 0)
    if not count:
        return None
    options = []
    for ref in feature["feature_specific"]["invocations"]:
        inv = catalog.features.get(ref["index"]) or {}
        label = ref["name"].replace("Eldritch Invocation: ", "")
        option = {"id": ref["index"], "label": label}
        desc = _join_desc(inv.get("desc"))
        if desc:
            option["description"] = desc
        options.append(option)
    return {
        "id": cid, "source": source, "label": feature["name"],
        "description": _join_desc(feature.get("desc")) or "", "count": count, "options": options,
    }


def _optional_progression_template(catalog: Catalog, feature: dict, cid: str, source: dict, class_level: int) -> dict | None:
    """Subclass picks from optionalfeatureProgression (maneuvers, runes, ...):
    the count is the progression value of the highest level reached; options
    with a level prerequisite above the class level are shown disabled."""
    spec = feature["feature_specific"]["optional_progression"]
    reached = [int(k) for k in spec["progression"] if int(k) <= class_level]
    if not reached:
        return None
    granted_ids = [oid for lvl, ids in (spec.get("required") or {}).items() if int(lvl) <= class_level
                   for oid in ids if oid in catalog.features]
    options = _optional_feature_options(catalog, spec["options"], granted_ids, class_level)
    description = _join_desc(feature.get("desc")) or ""
    tpl = {
        "id": cid, "source": source, "label": feature["name"], "description": description,
        "count": max(0, spec["progression"][str(max(reached))] - len(granted_ids)), "count_by_level": True,
        "options": options,
    }
    if granted_ids:
        tpl["granted"] = [{"id": oid, "label": catalog.features[oid]["name"]} for oid in granted_ids]
        names = ", ".join(g["label"] for g in tpl["granted"])
        tpl["description"] = (msg("desc-granted-automatically-after", text=description, names=names, n=len(granted_ids))
                              if description else msg("desc-granted-automatically", names=names, n=len(granted_ids)))
    return tpl


def _text_options_template(spec: dict, cid: str, source: dict, name: str, description,
                           sources=None, keep=()) -> dict:
    """Build-time pick among options that the feature text lists (Totem
    Spirit, Storm Aura...). Option ids are `<featureId>--<slug>`. G1: an option
    with its own `source` (Elk/Tiger, SCAG) follows draft.sources like other
    source-gated options: hidden when its source is off, unless already stored
    (then kept and flagged `hiddenByFilters`)."""
    options = []
    for opt in spec["options"]:
        hidden = not _source_allowed({"source": opt.get("source")}, sources)
        if hidden and opt["id"] not in keep:
            continue
        option = {"id": opt["id"], "label": opt["name"]}
        if hidden:
            option["hiddenByFilters"] = True
        desc = _join_desc(opt.get("desc"))
        if desc:
            option["description"] = desc
        options.append(option)
    return {"id": cid, "source": source, "label": name, "description": description or "",
            "count": spec.get("count", 1), "options": options}


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[tuple[int, dict]], subclass_id: str | None,
    class_level: int | None = None, skip_features: frozenset[str] | set[str] = frozenset(),
    sources=None, class_choices: dict | None = None,
) -> list[dict]:
    templates = []
    if class_level is None:
        class_level = max((lvl for lvl, _ in feature_refs), default=1)
    for lvl, ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature or ref["index"] in skip_features:  # C3: replaced by a fighting-style feat card
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated to a different subclass than the one selected (or none selected)
        specific = feature.get("feature_specific") or {}
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        description = _join_desc(feature.get("desc"))
        # The envelopes themselves have no 'desc' key (except the string
        # lists') — the description text lives on the parent feature
        # (verified directly against 5e-SRD-Features.json), so it must be
        # passed explicitly.
        if specific.get("subfeature_options"):
            cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
            tpl = build_choice_template(specific["subfeature_options"], cid, source, feature["name"], description=description)
            if tpl and feature["index"] in reference_data.SRD_METAMAGIC_FEATURES:  # G2: the TCE options
                tpl["options"] = _with_extra_metamagic(catalog, tpl["options"], "Metamagic: ")
        elif specific.get("expertise_options"):
            # "expertise-choice" in the cid is what the expertise gate and the
            # proficiency scans key off (the same marker feat expertise uses).
            envelope = _expertise_envelope(specific["expertise_options"])
            cid = f"class:{cls_id}:{lvl}:expertise-choice:{feature['index']}"
            tpl = build_choice_template(envelope, cid, source, feature["name"], description=description) if envelope else None
        elif specific.get("enemy_type_options"):
            cid = f"class:{cls_id}:{lvl}:enemy-type:{feature['index']}"
            tpl = build_choice_template(_string_options_envelope(specific["enemy_type_options"]), cid, source, feature["name"], description=description)
            if feature["index"] in reference_data.FAVORED_ENEMY_FEATURES_2014:  # VF7.3: the language that comes with each favored enemy
                templates.append(class_choices_2024.favored_enemy_language_template(cls_id, lvl, feature["index"], source))
        elif specific.get("terrain_type_options"):
            cid = f"class:{cls_id}:{lvl}:terrain-type:{feature['index']}"
            tpl = build_choice_template(_string_options_envelope(specific["terrain_type_options"]), cid, source, feature["name"], description=description)
        elif specific.get("invocations"):
            cid = f"class:{cls_id}:{lvl}:invocations:{feature['index']}"
            tpl = _invocation_templates(catalog, feature, cid, source, class_level)
        elif specific.get("optional_progression"):
            cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
            tpl = _optional_progression_template(catalog, feature, cid, source, class_level)
        elif specific.get("text_options"):
            cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
            stored = (class_choices or {}).get(cid)
            tpl = _text_options_template(specific["text_options"], cid, source, feature["name"], description,
                                         sources, stored if isinstance(stored, list) else ())
        else:
            continue
        if tpl:
            templates.append(tpl)
    return templates


def _resolve_species_selected_feats(template: dict, species_choices: dict, catalog: Catalog,
                                    problems: list[dict], background_grant: bool = False) -> list[dict]:
    """The feats a species template's stored selection names: deduped, only
    enabled options, capped to the count. Each is a shallow COPY of the
    catalog record tagged `_species_origin = "{choice id}:feat:{index}"`
    (the cid prefix of its own cascaded choices). A stored pick of a
    disabled option is not applied and is reported (`feat-duplicate-...`
    for "already taken", `feat-prerequisite-unmet-...` otherwise)."""
    raw = species_choices.get(template["id"])
    raw = list(dict.fromkeys(s for s in raw if isinstance(s, str))) if isinstance(raw, list) else []
    by_id = {o["id"]: o for o in template["options"]}
    picked = []
    for option_id in raw:
        option = by_id.get(option_id)
        feat = catalog.feats.get(option_id[len("feat:"):]) if option else None
        if not feat:
            continue
        if option.get("disabled"):
            # `disabledReason` is a Msg (a str subclass whose text is the English wording), so this plain text check
            # still works; do not rebuild it with `+` / f-strings or the tag is lost (tests/test_i18n_disabled.py)
            if str(option.get("disabledReason")).startswith("already taken"):
                problems.append({
                    "id": f"feat-duplicate-{feat['index']}-{template['id']}",
                    "message": msg("feat-duplicate-at-source", feat=feat["name"], source=template["source"]["label"]),
                })
            else:
                problems.append({
                    "id": f"feat-prerequisite-unmet-{feat['index']}",
                    "message": msg("feat-prerequisite-unmet-pick", feat=feat["name"], source=template["source"]["label"]),
                })
            continue
        picked.append(feat)
    # W4: a background feat grant reuses this machinery; `_background_grant` only changes the sheet's `origin`.
    return [
        {**feat, "_species_origin": f"{template['id']}:feat:{feat['index']}",
         **({"_background_grant": True} if background_grant else {})} for feat in picked[: template["count"]]
    ]


def _asi_option_label(deltas: list[tuple[str, int]]) -> str:
    return " and ".join(f"{ab} +{delta}" for ab, delta in deltas)


_ASI_CID_RE = re.compile(r"^class:[^:]+:\d+:asi$")


def _asi_feat_pool(
    catalog: Catalog, sources, ruleset: str, slot_level: int, keep_index: str | None = None, fighting_style: bool = False,
) -> list[dict]:
    """The feats offered at an ASI slot: structurally eligible AND allowed by
    draft.sources / the ruleset. `keep_index` (the already-selected feat) is
    appended, as a COPY tagged `_hidden_by_filters`, when it is honored
    (_asi_pick_honored) but not in the pool."""
    pool = [f for f in catalog.feats.values() if _asi_feat_in_pool(f, sources, ruleset, slot_level, fighting_style)]
    kept = catalog.feats.get(keep_index) if keep_index else None
    if kept and all(f['index'] != kept['index'] for f in pool) and _asi_pick_honored(kept, sources, ruleset, slot_level, fighting_style):
        pool.append({**kept, "_hidden_by_filters": True})
    return pool


def _asi_choice_templates(
    cls_id: str, cls_name: str, asi_levels: list[int], scores_by_level: dict[int, dict[str, int]],
    catalog: Catalog, total_level: int, use_prerequisites: bool, sources=None,
    taken_by_level: dict[int, dict[str, str]] | None = None,
    held_by_level: dict[int, "_HeldFeatState"] | None = None,
    ruleset: str = "mixed", class_choices: dict | None = None,
) -> list[dict]:
    # `class_choices`: this class's stored selections; an already-picked feat
    # stays offered (flagged `hiddenByFilters`) when ruleset/sources hide it.
    # `taken_by_level`: per ASI level, the feat indices already held from a
    # background grant or an earlier ASI pick — offered disabled unless the
    # feat is `repeatable`.
    # `sources` is draft.sources: feat options are filtered exactly like a
    # race/background record (see _feat_source_allowed). SRD-only drafts
    # therefore get zero feat options — the 2014 SRD has no feats.
    pools: dict[tuple[bool, bool], list[dict]] = {}
    prereq_memo: dict = {}  # VF7.4
    templates = []
    for lvl in asi_levels:
        cid = f"class:{cls_id}:{lvl}:asi"
        epic = lvl >= _ASI_EPIC_BOON_LEVEL
        fighting_style = bool((held_by_level or {}).get(lvl) and held_by_level[lvl].fighting_style)  # C3
        if (epic, fighting_style) not in pools:
            pools[(epic, fighting_style)] = _asi_feat_pool(catalog, sources, ruleset, lvl, fighting_style=fighting_style)
        general_feats = pools[(epic, fighting_style)]
        keep_index = _stored_asi_feat_pick(class_choices, cid)
        if keep_index and not any(f["index"] == keep_index for f in general_feats):
            kept_pool = _asi_feat_pool(catalog, sources, ruleset, lvl, keep_index, fighting_style)
            general_feats = general_feats + [f for f in kept_pool if f.get("_hidden_by_filters")]
        current_scores = scores_by_level.get(lvl, {})
        options = []
        for option_id, deltas in asi_mod.asi_combinations():
            option = {"id": option_id, "label": _asi_option_label(deltas), "group": "asi"}
            if asi_mod.asi_exceeds_cap(deltas, current_scores):
                option["disabled"] = True
                option["disabledReason"] = msg("disabled-ability-cap-20")
            options.append(option)
        held_here = (held_by_level or {}).get(lvl) or _HeldFeatState()  # VF7.4: once per level, not once per feat
        taken_here = (taken_by_level or {}).get(lvl)
        for feat, option in _feat_options(general_feats, ruleset):
            if feat.get("_hidden_by_filters"):
                option["hiddenByFilters"] = True
            reason = _feat_prerequisite_unmet_reason(
                feat, total_level, current_scores, use_prerequisites, held_here, catalog, prereq_memo,
            )
            if reason:
                option["disabled"] = True
                option["disabledReason"] = reason
            elif taken := _taken_reason(feat, taken_here):
                option["disabled"] = True
                option["disabledReason"] = taken
            options.append(option)
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": msg("label-asi"),
            "description": msg("desc-asi"),
            "count": 1,
            "options": options,
        })
    return templates


# C3: 2024 Fighting Style as a feat choice. XPHB Fighter (level 1), Paladin and
# Ranger (level 2) "gain a Fighting Style feat of your choice"; the XPHB Champion's
# "Additional Fighting Style" (level 7) grants another one. Under ruleset 2024 only
# (mixed and 2014 keep the SRD fighting-style subfeatures, U9) these features'
# cards are feat cards: cid `class:<cls>:<lvl>:fighting-style`, options
# `feat:<index>` from `_feat_options`, prerequisite / duplicate states as for ASI
# feats. The picked feat is tagged like an ASI feat (`_asi_origin`, `_asi_level`) plus
# `_fs_cid`, so cid prefixes, instance keys, cascaded choices and sheet.feats work.
_FS_FEATURE_INDICES = frozenset({
    "fighter-fighting-style", "paladin-fighting-style", "ranger-fighting-style",
    "additional-fighting-style", "champion-xphb-7-additional-fighting-style",
})
_FS_CLASS_CATEGORIES = {"fighter": ("FS",), "paladin": ("FS", "FS:P"), "ranger": ("FS", "FS:R")}


def _class_has_fighting_style(catalog: Catalog, rc: dict) -> bool:
    """Whether the class (and subclass) feature list up to the class level has a
    feature named "Fighting Style" (the 5etools `Fighting Style` prerequisite)."""
    for _lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        sub = feature.get("subclass")
        if sub and sub.get("index") != rc["subclass_id"]:
            continue
        if feature.get("name") == "Fighting Style":
            return True
    return False


def _fighting_style_pool(catalog: Catalog, cls_id: str, sources, ruleset: str) -> list[dict]:
    cats = _FS_CLASS_CATEGORIES.get(cls_id, ())
    return [f for f in catalog.feats.values() if f.get("category") in cats and _feat_offered(f, sources, ruleset)]


def _fighting_style_slots(catalog: Catalog, rc: dict, sources, ruleset: str) -> list[tuple[str, int, str]]:
    """[(cid, class level, feature index)] of the class's fighting-style feat cards,
    by level. Empty outside ruleset 2024, for other classes, and when the catalog
    offers no Fighting Style feat (SRD-only data, sources without XPHB): the SRD
    subfeature card stays then."""
    if ruleset != "2024" or rc["cls_id"] not in _FS_CLASS_CATEGORIES or not rc["cls"]:
        return []
    if not _fighting_style_pool(catalog, rc["cls_id"], sources, ruleset):
        return []
    slots: dict[str, tuple[str, int, str]] = {}
    for lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
        if ref["index"] not in _FS_FEATURE_INDICES:
            continue
        feature = catalog.features.get(ref["index"])
        sub = (feature or {}).get("subclass")
        if not feature or (sub and sub.get("index") != rc["subclass_id"]):
            continue
        cid = f"class:{rc['cls_id']}:{lvl}:fighting-style"
        slots.setdefault(cid, (cid, lvl, ref["index"]))
    return sorted(slots.values(), key=lambda slot: slot[1])


def _srd_fighting_style_slots(catalog: Catalog, rc: dict, replaced: set[str]) -> list[tuple[str, int, str]]:
    """G1: [(cid, class level, feature index)] of the SRD "Fighting Style" /
    "Additional Fighting Style" subfeature cards the class has (the ones not replaced by
    a 2024 feat card). Their picks take part in the fighting-style duplicate check."""
    slots = []
    for lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
        feature = catalog.features.get(ref["index"])
        if not feature or ref["index"] in replaced:
            continue
        sub = feature.get("subclass")
        if sub and sub.get("index") != rc["subclass_id"]:
            continue
        if feature.get("name") in ("Fighting Style", "Additional Fighting Style") \
                and (feature.get("feature_specific") or {}).get("subfeature_options"):
            slots.append((f"class:{rc['cls_id']}:{lvl}:feature:{feature['index']}", lvl, feature["index"]))
    return slots


class _FightingStyleResolver:
    """The feats picked at the fighting-style cards (see above), resolved in ONE order
    with the ASI picks (F1): by (class index, class level), a card before the ASI of the
    same level. `__call__(rc, upto_level_or_None, seen)` is the `before_level` hook of
    `_resolve_asi_selected_feats`: it resolves the not-yet-done cards of `rc` whose level
    is <= `upto_level` (all of them for None) against `seen` (background, species and
    every pick at an earlier position, whatever its kind), so the LATER pick is the
    duplicate. `taken_by_cid[cid]` = `seen` before that card, the map its options read
    for the "already taken" state. A duplicate is skipped and appended to
    `skipped_duplicates`. Any FS-category feat of the class is honored (a pick hidden by
    sources/ruleset stays, like an ASI pick); anything else is ignored and lands in
    `pruned` through the generic stale-selection pass."""

    def __init__(self, slots_by_class: dict[int, list[tuple[str, int, str]]], catalog: Catalog,
                 skipped_duplicates: list[dict], srd_slots_by_class: dict[int, list[tuple[str, int, str]]] | None = None,
                 skipped_srd: list[dict] | None = None):
        self.slots_by_class = slots_by_class
        self.srd_slots_by_class = srd_slots_by_class or {}
        self.skipped_srd = skipped_srd if skipped_srd is not None else []
        self.catalog = catalog
        self.skipped_duplicates = skipped_duplicates
        self.picks: list[dict] = []
        self.taken_by_cid: dict[str, dict[str, str]] = {}
        self._done: set[str] = set()

    def __call__(self, rc: dict, upto_level: int | None, seen: dict[str, str]) -> None:
        cats = _FS_CLASS_CATEGORIES.get(rc["cls_id"], ())
        slots = sorted([(c, l, i, False) for c, l, i in self.slots_by_class.get(rc["index"], [])]
                       + [(c, l, i, True) for c, l, i in self.srd_slots_by_class.get(rc["index"], [])],
                       key=lambda t: t[1])
        for cid, lvl, _idx, is_srd in slots:
            if cid in self._done or (upto_level is not None and lvl > upto_level):
                continue
            self._done.add(cid)
            self.taken_by_cid[cid] = dict(seen)
            if is_srd:  # G1: an SRD style pick is held by its name key (first holder wins)
                raw = rc["class_choices"].get(cid)
                options = _srd_style_options(self.catalog, _idx)
                pick = next((x for x in (raw if isinstance(raw, list) else []) if isinstance(x, str) and x in options), None)
                if pick:
                    key = "name:" + options[pick]
                    if key in seen:
                        self.skipped_srd.append({"option": pick, "cid": cid, "level": lvl, "cls": rc["cls"],
                                                 "name": self.catalog.features[pick]["name"]})
                    else:
                        seen[key] = f"{options[pick].title()}, SRD"
                continue
            feat_index = _stored_asi_feat_pick(rc["class_choices"], cid)
            feat = self.catalog.feats.get(feat_index) if feat_index else None
            if not feat or feat.get("category") not in cats:
                continue
            if _taken_reason(feat, seen):
                self.skipped_duplicates.append({"feat": feat, "cid": cid, "level": lvl, "cls": rc["cls"]})
                continue
            _taken_add(seen, [feat])
            self.picks.append({**feat, "_fs_cid": cid, "_asi_level": lvl, "_asi_origin": f"{cid}:feat:{feat['index']}"})


def _fighting_style_templates(
    catalog: Catalog, rc: dict, slots: list[tuple[str, int, str]], sources, ruleset: str, total_level: int,
    scores: dict[str, int], use_prerequisites: bool, held: "_HeldFeatState", taken_by_cid: dict[str, dict[str, str]],
) -> list[dict]:
    """One feat card per fighting-style slot of the class (see above)."""
    cls_id = rc["cls_id"]
    cats = _FS_CLASS_CATEGORIES.get(cls_id, ())
    holder = held.copy()
    holder.fighting_style = True  # the character is gaining the feature right here
    templates = []
    for cid, lvl, feature_index in slots:
        feats = _fighting_style_pool(catalog, cls_id, sources, ruleset)
        keep_index = _stored_asi_feat_pick(rc["class_choices"], cid)
        kept = catalog.feats.get(keep_index) if keep_index else None
        if kept and kept.get("category") in cats and all(f["index"] != kept["index"] for f in feats):
            feats.append({**kept, "_hidden_by_filters": True})
        options = []
        for feat, option in _feat_options(feats, ruleset):
            option.pop("group", None)
            if feat.get("_hidden_by_filters"):
                option["hiddenByFilters"] = True
            reason = (
                _feat_prerequisite_unmet_reason(feat, total_level, scores, use_prerequisites, holder, catalog)
                or _taken_reason(feat, taken_by_cid.get(cid))
            )
            if reason:
                option["disabled"] = True
                option["disabledReason"] = reason
            options.append(option)
        feature = catalog.features[feature_index]
        text_feature = catalog.features.get(f"xphb-{cls_id}-{lvl}-fighting-style") or (
            feature if feature_index.startswith("champion-xphb") else {})
        templates.append({
            "id": cid, "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": lvl},
            "label": feature["name"],
            "description": _join_desc(text_feature.get("desc")) or msg("desc-fighting-style-feat"),
            "count": 1, "options": options,
        })
    return templates


# C7c (decision E7): Lessons of the First Ones. XPHB Warlock invocation "gain one Origin feat of your choice ... Each time
# you do so, choose a different Origin feat." Under ruleset 2024 every SELECTED instance (`<id>`, `<id>~2`, ...) has an
# Origin-feat card, cid `class:warlock:invocation:<instance>:feat`. The picked feat is tagged like an ASI feat
# (`_asi_origin` = `<card cid>:<feat index>`, `_asi_level` 2) plus `_inv_cid`, so cid prefixes, cascaded choices and
# sheet.feats work.
LESSONS_LEVEL = 2


def _lessons_slots(catalog: Catalog, resolved_classes: list[dict], ruleset: str) -> dict[int, list[tuple[str, str]]]:
    """{class index: [(card cid, invocation instance id)]} of the selected Lessons instances (2024 Warlock)."""
    out = {}
    for rc in resolved_classes:
        if rc["cls"] and rc["cls_id"] == "warlock":
            instances = class_choices_2024.lessons_instances(catalog, rc, ruleset)
            if instances:
                out[rc["index"]] = [(class_choices_2024.dependent_cid(i, "feat"), i) for i in instances]
    return out


class _LessonsResolver:
    """The Origin feats picked at the Lessons cards, resolved in the F1 walk (see `_FightingStyleResolver`): hooked
    into `before_level`, position (class index, level 2), against `seen` (background, species and every pick at an
    earlier position). Two Lessons instances never share a feat, repeatable or not ("a different Origin feat"); the
    LATER pick of a duplicate is skipped (`skipped_duplicates`). `taken_by_cid[cid]` = `seen` before that card;
    `picked[cid]` = the feat index it holds. Any category O feat is honored (a pick hidden by sources / ruleset
    stays); anything else lands in `pruned` through the generic stale-selection pass."""

    def __init__(self, slots_by_class: dict[int, list[tuple[str, str]]], catalog: Catalog, skipped_duplicates: list[dict]):
        self.slots_by_class = slots_by_class
        self.catalog = catalog
        self.skipped_duplicates = skipped_duplicates
        self.picks: list[dict] = []
        self.taken_by_cid: dict[str, dict[str, str]] = {}
        self.picked: dict[str, str] = {}
        self._done: set[str] = set()
        self._own: set[str] = set()

    def __call__(self, rc: dict, upto_level: int | None, seen: dict[str, str]) -> None:
        if upto_level is not None and upto_level < LESSONS_LEVEL:
            return
        for cid, _inst in self.slots_by_class.get(rc["index"], []):
            if cid in self._done:
                continue
            self._done.add(cid)
            self.taken_by_cid[cid] = dict(seen)
            feat_index = _stored_asi_feat_pick(rc["class_choices"], cid)
            feat = self.catalog.feats.get(feat_index) if feat_index else None
            if not feat or feat.get("category") != "O":
                continue
            key = _feat_name_key(feat)
            if key in self._own or _taken_reason(feat, seen):
                self.skipped_duplicates.append({"feat": feat, "cid": cid, "level": LESSONS_LEVEL, "cls": rc["cls"]})
                continue
            self._own.add(key)
            _taken_add(seen, [feat])
            self.picked[cid] = feat["index"]
            self.picks.append({**feat, "_inv_cid": cid, "_asi_level": LESSONS_LEVEL, "_asi_origin": f"{cid}:{feat['index']}"})


class _FeatLessonsResolver:
    """RP20 (A3c): Lessons of the First Ones held through Eldritch Adept (2024: the feat's one invocation). The Origin
    feat is resolved in the F1 walk right after the Eldritch Adept ASI feat (`after_feat`), against the same `seen`
    map, so the LATER holder of a feat is the duplicate. The pick needs Warlock level 2 (the invocation's
    prerequisite, read at the final level like `_gate_feat_invocation_prereqs`) and yields to a Lessons the Warlock
    holds itself (the gate disables the same option). The RAW stored selection decides (the late gates never drop a
    Lessons pick that passes these checks). `slots[feat origin]` = (card cid, rc class id, ASI level)."""

    def __init__(self, catalog: Catalog, ruleset: str, warlock_level: int, class_holds_lessons: bool, skipped_duplicates: list[dict]):
        self.catalog = catalog
        self.active = ruleset == "2024" and warlock_level >= 2 and not class_holds_lessons
        self.ruleset = ruleset
        self.skipped_duplicates = skipped_duplicates
        self.picks: list[dict] = []
        self.slots: dict[str, tuple[str, str, int]] = {}
        self.taken_by_cid: dict[str, dict[str, str]] = {}
        self.picked: dict[str, str] = {}

    def __call__(self, rc: dict, lvl: int, feat: dict, seen: dict[str, str]) -> None:
        spec = fed_option_picks(feat) or {}
        if not self.active or spec.get("kind") != "invocation":
            return
        pool = {o["id"] for o in _option_pick_options(self.catalog, "invocation", self.ruleset)}
        card = f"{feat['_asi_origin']}:invocation"
        stored = rc["class_choices"].get(card)
        first = next((x for x in (stored if isinstance(stored, list) else []) if isinstance(x, str) and x in pool), None)
        if first != class_choices_2024.LESSONS_ID:
            return
        cid = class_choices_2024.dependent_cid(first, "feat", card + ":")
        self.slots[feat["_asi_origin"]] = (cid, rc["cls_id"], lvl)
        self.taken_by_cid[cid] = dict(seen)
        index = _stored_asi_feat_pick(rc["class_choices"], cid)
        pick = self.catalog.feats.get(index) if index else None
        if not pick or pick.get("category") != "O":
            return
        if _taken_reason(pick, seen):
            self.skipped_duplicates.append({"feat": pick, "cid": cid, "level": lvl, "cls": rc["cls"]})
            return
        _taken_add(seen, [pick])
        self.picked[cid] = pick["index"]
        self.picks.append({**pick, "_inv_cid": cid, "_inv_class": rc["cls_id"], "_ea_asi_cid": feat["_asi_cid"], "_asi_level": lvl,
                           "_asi_origin": f"{cid}:{pick['index']}"})


def _lessons_templates(
    catalog: Catalog, rc: dict, slots: list[tuple[str, str]], sources, ruleset: str, total_level: int,
    scores: dict[str, int], use_prerequisites: bool, held: "_HeldFeatState", taken_by_cid: dict[str, dict[str, str]],
    picked: dict[str, str],
) -> list[dict]:
    """One Origin-feat card per selected Lessons instance (see above)."""
    source = {"kind": "class", "id": "warlock", "label": rc["cls"]["name"], "level": LESSONS_LEVEL}
    return [_lessons_card(catalog, rc, cid, inst, dict(source), sources, ruleset, total_level, scores, use_prerequisites, held,
                          taken_by_cid, picked) for cid, inst in slots]


def _envelope_needs_expansion(envelope: dict) -> bool:
    """True for starting-equipment envelopes that reference an
    equipment_category set, directly or through a nested option_type
    "choice" (alone or inside a "multiple" bundle)."""
    from_field = envelope.get("from") or {}
    if from_field.get("option_set_type") == "equipment_category":
        return True
    for opt in from_field.get("options", []):
        members = opt.get("items", []) if opt.get("option_type") == "multiple" else [opt]
        if any(m.get("option_type") == "choice" for m in members):
            return True
    return False


def _equipment_choice_templates(
    entity: dict, source_kind: str, source_id: str, source_label: str, items: dict | None = None,
) -> tuple[list[dict], int, dict[str, dict[str, list[dict]]]]:
    """Returns (templates, dropped envelope count, dependents) where
    dependents is {choice id: {option id: [follow-up templates]}} for
    options that contain a nested pick (see catalog.choices.
    build_equipment_choice); resolve() adds them once that option is
    selected."""
    templates = []
    dependents_by_choice: dict[str, dict[str, list[dict]]] = {}
    dropped_envelopes = 0
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        envelope = {**envelope, "keep_counts": True}  # RPX3: the counts of the rules text, in every ruleset (was 2024 only)
        if items is not None and _envelope_needs_expansion(envelope):
            tpl, dependents = build_equipment_choice(envelope, cid, source, msg("label-starting-equipment"), items)
            if tpl and dependents:
                dependents_by_choice[cid] = dependents
        else:
            tpl = build_choice_template(envelope, cid, source, msg("label-starting-equipment"))
        if not tpl:
            dropped_envelopes += 1
            continue
        if items is not None:  # RPX3: "20 arrows" is one catalog arrow pack
            for option in tpl["options"]:
                if option.get("quantities"):
                    option["quantities"] = pack_quantities(option["quantities"], items)
                    if not option["quantities"]:
                        del option["quantities"]
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (msg("desc-equipment-note", text=tpl["description"]) if tpl["description"]
                                  else msg("desc-equipment-note-only"))
        templates.append(tpl)
    return templates, dropped_envelopes, dependents_by_choice


def _raise_walk_speed(speeds: dict[str, int], bonus: int) -> dict[str, int]:
    """F1: "Your speed increases by X feet" (Fast Movement, Unarmored Movement) raises the
    walking speed only; swim, fly, climb and burrow keep their own values."""
    if not bonus or "walk" not in speeds:
        return speeds
    return {**speeds, "walk": speeds["walk"] + bonus}


def _heavy_armor_speed_penalty(speeds: dict[str, int], penalty: int) -> dict[str, int]:
    """W1: armor below its Strength requirement reduces the walking speed by 10 ft (floor 0); other modes keep their value."""
    if not penalty or "walk" not in speeds:
        return speeds
    return {**speeds, "walk": max(0, speeds["walk"] - penalty)}


def _heavy_armor_speed_exempt(race: dict | None, subrace: dict | None) -> bool:
    """W1: "Your speed is not reduced by wearing heavy armor." -- a pinned trait of the race / subrace (dwarf-phb,
    Kaladesh) or the SRD dwarf race (reference_data.HEAVY_ARMOR_SPEED_EXEMPT_*). Dwarf (XPHB) has none."""
    if race and race.get("index") in HEAVY_ARMOR_SPEED_EXEMPT_RACES:
        return True
    for src in (race, subrace):
        for ref in list((src or {}).get("traits", [])) + list((src or {}).get("racial_traits", [])):
            if ref["index"] in HEAVY_ARMOR_SPEED_EXEMPT_TRAITS:
                return True
    return False


# C2: 2024 Weapon Mastery. XPHB class feature at level 1 of Barbarian, Fighter,
# Paladin, Ranger and Rogue (each class of a multiclass character grants its own).
# Count: the class table's "weapon-mastery" column (Barbarian, Fighter), else a
# fixed 2 (Paladin, Ranger, Rogue: "two kinds of weapons", no table column).
_MASTERY_FIXED_COUNT = {"paladin": 2, "ranger": 2, "rogue": 2}
_MASTERY_CLASSES = ("barbarian", "fighter", "paladin", "ranger", "rogue")


def _weapon_mastery_template(catalog: Catalog, rc: dict, ruleset: str) -> list[dict]:
    """Weapon Mastery choice for one class (see above), only under ruleset "2024".
    Built EARLY with the class-filter reasons; the proficiency check needs the
    final weapon-proficiency set and is applied late by `_gate_mastery_choices`
    (same build-early / gate-late pattern as the expertise and invocation gates).
    No card when the catalog has no weapon with a mastery or no count is known."""
    cls_id = rc.get("cls_id")
    if ruleset != "2024" or cls_id not in _MASTERY_CLASSES or not rc.get("cls"):
        return []
    count = _MASTERY_FIXED_COUNT.get(cls_id)
    if count is None:
        values = (getattr(catalog, "class_2024_tables", None) or {}).get(cls_id, {}).get("weapon-mastery")
        level = rc["level"]
        if not values or not 0 < level <= len(values):
            return []
        count = values[level - 1]
    options = []
    for item in catalog.items.values():
        if item.get("equipment_category", {}).get("index") != "weapon" or not item.get("mastery"):
            continue
        option = {"id": item["index"], "label": f"{item['name']} ({item['mastery']})"}
        reason = _mastery_filter_reason(cls_id, item)
        if reason:
            option.update(disabled=True, disabledReason=reason)
        options.append(option)
    if not options or not count:
        return []
    return [{
        "id": f"class:{cls_id}:weapon-mastery",
        "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": 1},
        "label": msg("label-weapon-mastery"),
        "description": msg("desc-weapon-mastery-class", count=count),
        "count": count,
        "options": options,
    }]


def _fixed_equipment(entries: list[dict], item_lookup: dict) -> list[dict]:
    result = []
    for entry in entries:
        equipment_ref = entry.get("equipment") or {}
        item_id = equipment_ref.get("index")
        item = item_lookup.get(item_id) if item_id else None
        if not item:
            continue
        qty = entry.get("quantity", 1)
        result.append({"itemId": item_id, "name": item["name"],
                       "qty": pack_units(item, qty) if isinstance(qty, int) and not isinstance(qty, bool) else qty})  # RPX3
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


def _monk_tool_pick(choices: list[dict]) -> str | None:
    """C9b: the Monk's tool proficiency pick (one of the Artisan's Tools / Musical Instrument ids),
    which the Monk starting-equipment package hands out as an item."""
    tool_ids = {t["index"] for t in reference_data.TOOLS}
    for c in choices:
        if (c["id"].startswith("class:monk:1:prof-choice-") and c["selected"]
                and any(o["id"] in tool_ids for o in c["options"])):
            return c["selected"][0]
    return None


def _background_tool_pick(choices: list[dict], bg_id: str | None, item_lookup: dict) -> str | None:
    """RP9: the tool picked by the background's own tool proficiency card (`background:<id>:proficiency-choice-*` with
    tool options), as a catalog item id; None when nothing is picked or the tool has no catalog item (the
    sentinel member then stays a narrative item)."""
    tool_ids = {t["index"] for t in reference_data.TOOLS}
    prefix = f"background:{bg_id}:proficiency-choice-"
    for c in choices:
        if (bg_id and c["id"].startswith(prefix) and c["selected"] and any(o["id"] in tool_ids for o in c["options"])):
            return c["selected"][0] if c["selected"][0] in item_lookup else None
    return None


def _chosen_equipment(equipment_choices: list[dict], item_lookup: dict, monk_tool: str | None = None,
                      background_tool: str | None = None) -> list[dict]:
    """The catalog items of the selected equipment bundles. A bundle option may carry `quantities`
    ({item id: n}, 2024 packages only, decisions E8 / RP9); everything else is qty 1. The Monk
    sentinel stands for `monk_tool` (the item of the tool proficiency pick), the background sentinel (RP9) for
    `background_tool`."""
    result: list[dict] = []
    for choice in equipment_choices:
        options_by_id = {opt["id"]: opt for opt in choice.get("options", [])}
        for selected_id in choice["selected"]:
            quantities = (options_by_id.get(selected_id) or {}).get("quantities") or {}
            for item_id in selected_id.split("+"):
                if item_id == reference_data.MONK_TOOL_SENTINEL:
                    item_id = monk_tool or ""
                elif item_id == reference_data.BACKGROUND_TOOL_SENTINEL:
                    item_id = background_tool or ""
                item = item_lookup.get(item_id)
                if item:
                    result.append({"itemId": item_id, "name": item["name"], "qty": quantities.get(item_id, 1)})
    return result


def _with_pack_contents(entries: list[dict], item_lookup: dict) -> list[dict]:
    """RP8 (ruleset 2024 only): an entry of a PHB 2024 equipment pack gets `contents`
    ([{itemId, name, qty}], PACKS_2024 order; members missing from the catalog are skipped). The pack stays one item."""
    out = []
    for entry in entries:
        pack = reference_data.PACKS_2024.get(entry.get("itemId"))
        if pack is None:
            out.append(entry)
            continue
        contents = [{"itemId": i, "name": item_lookup[i]["name"], "qty": q}
                    for i, q in pack["contents"] if i in item_lookup]
        out.append({**entry, "contents": contents})
    return out


def _selected_gold_and_narrative_items(equipment_choices: list[dict], monk_tool: str | None = None,
                                       background_tool: str | None = None) -> tuple[int, list[str]]:
    """A small, disclosed second pass over the SAME selected-equipment ids
    _gather_equipped_items/_chosen_equipment already iterate (each
    selected_id split on "+"), reading the parts THOSE functions
    deliberately skip because they aren't real catalog.items entries.
    official_source.py synthesizes exactly three such non-catalog "of"
    references for 5etools bundle members with no catalog equivalent —
    gp-{amount} (a gold value), flavor-{slug} ({"special": ...} flavor
    text), and category-{slug}/unlisted-{slug} (an {"equipmentType": ...}
    category placeholder or an unrecognized item name) — see that module's
    _equipment_bundle_member_from_5etools/_counted_reference_for_item_name
    docstrings. This does NOT change what item_lookup.get(item_id) returns
    or how real catalog items are matched; it only recovers the gold
    amount and narrative label from the ids those functions already saw
    and silently dropped.

    catalog/choices.py's own _bundle_label_and_id builds a bundle option's
    "+"-joined id and " + "-joined label from the SAME per-member loop, in
    the SAME order (id_parts.append(...)/label_parts.append(...) side by
    side) — so zipping a selected option's id.split("+") against its own
    label.split(" + ") recovers each member's real display label, rather
    than re-deriving a lossy one from the synthetic id's slug."""
    gold = 0
    narrative_items: list[str] = []
    for choice in equipment_choices:
        options_by_id = {opt["id"]: opt for opt in choice.get("options", [])}
        for selected_id in choice["selected"]:
            option = options_by_id.get(selected_id)
            if option is None:
                continue
            id_parts = selected_id.split("+")
            label_parts = option["label"].split(" + ")
            zipped = label_parts if len(label_parts) == len(id_parts) else None
            for i, item_id in enumerate(id_parts):
                if item_id.startswith("gp-"):
                    amount = item_id[len("gp-"):]
                    if amount.isdigit():
                        gold += int(amount)
                elif item_id == reference_data.MONK_TOOL_SENTINEL:
                    if not monk_tool:  # C9b: no tool proficiency pick yet -> the label is a narrative item
                        narrative_items.append(zipped[i] if zipped else "Artisan's Tools or Musical Instrument")
                elif item_id == reference_data.BACKGROUND_TOOL_SENTINEL:
                    if not background_tool:  # RP9: no tool proficiency pick (yet) -> the label is a narrative item
                        narrative_items.append(zipped[i] if zipped else "Tool (same as the tool proficiency)")
                elif item_id.startswith(("flavor-", "category-", "unlisted-")):
                    # zipped is None only if an item's own name literally
                    # contains "+" or " + ", throwing off the split — falls
                    # back to a slug-derived label rather than dropping it.
                    narrative_items.append(zipped[i] if zipped else item_id.split("-", 1)[1].replace("-", " "))
    return gold, narrative_items


def _class_feature_list(
    catalog: Catalog, resolved_classes: list[dict], choices: list[dict] | None = None, feats: list[dict] | None = None,
) -> list[tuple[str, int, str]]:
    """(class_id, class_level, feature_index) for every class/subclass
    feature the character has, plus selected feature options (e.g. a
    chosen Fighting Style) read from `choices` when given, plus (C3) the
    resolved Fighting Style feats in `feats` (picked at a fighting-style card or an
    ASI) under their feat index, so CLASS_FEATURE_EFFECTS can key on `defense-xphb`."""
    out: list[tuple[str, int, str]] = []
    for rc in resolved_classes:
        if not rc["cls"] or not rc["cls_id"]:
            continue
        for _lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
            feature = catalog.features.get(ref["index"])
            sub = (feature or {}).get("subclass")
            if sub and sub.get("index") != rc["subclass_id"]:
                continue
            out.append((rc["cls_id"], rc["level"], ref["index"]))
    for c in choices or []:
        src = c.get("source") or {}
        if src.get("kind") == "class" and ":feature:" in c["id"]:
            lvl = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == src.get("id")), 0)
            for sel in [g["id"] for g in c.get("granted") or []] + list(c.get("selected") or []):
                out.append((src["id"], lvl, sel))
    first = next((rc for rc in resolved_classes if rc["cls_id"] and rc["cls"]), None)
    for c in choices or []:  # FE9 Fighting Initiate: the picked fighter style counts as a class feature (its effect, G1 names)
        if (c.get("source") or {}).get("kind") == "feat" and c["id"].endswith(":" + _OPTION_PICK_CARDS["fighting-style"][0]) and first:
            rc = next((r for r in resolved_classes if c["id"].startswith(f"class:{r['cls_id']}:")), first)
            out += [(rc["cls_id"], rc["level"], sel) for sel in c.get("selected") or []]
    for feat in feats or []:
        if feat.get("category") in _FS_FEAT_CATEGORIES and first:
            origin = feat.get("_asi_origin") or ""
            rc = next((r for r in resolved_classes if origin.startswith(f"class:{r['cls_id']}:")), first)
            out.append((rc["cls_id"], rc["level"], feat["index"]))
    return out


# Cap on `pruned` entries returned (a draft with 50k stale keys must not echo all of them).
MAX_PRUNED_REPORTED = 200


def _stale_pick_label(catalog: Catalog, pick: str) -> str:
    """VF7.7c: the label a stale stored pick (one the card no longer offers) is shown with in Bulgarian: the name of the feature,
    language, ... the id stands for, "<N> gp" for a gold pick, else the id spelled as words ("any-martial-weapons" ->
    "Any martial weapons"). English keeps printing the id (frozen text); see the `label-stale-pick` message."""
    feature = catalog.features.get(pick)
    if feature and feature.get("name"):
        return str(feature["name"])
    for lang in reference_data.LANGUAGES:
        if lang["index"] == pick:
            return lang["name"]
    gold = re.fullmatch(r"gp-(\d+)", pick)
    if gold:
        return f"{gold.group(1)} gp"
    words = re.sub(r"[-_]+", " ", pick).strip()
    return words[:1].upper() + words[1:]


def _stale_pick_name(catalog: Catalog, pick: str, feats: bool = True):
    """The name of a dropped pick: the catalog record's name (items, spells, feats), else a `label-stale-pick` message."""
    record = catalog.items.get(pick) or catalog.spells.get(pick) or (catalog.feats.get(pick) if feats else None)
    if record and record.get("name"):
        return record["name"]
    return msg("label-stale-pick", id=pick, label=_stale_pick_label(catalog, pick))


@dataclass(slots=True)
class ResolveState:
    """Everything the passes of resolve() hand to each other. A field is written by the pass that computes it and read by the
    later passes that need it; a field nobody has written yet raises AttributeError, so a pass cannot read what is not there."""
    draft: Any
    catalog: Catalog
    classes: Any = field(init=False)
    cls: Any = field(init=False)
    cls_id: Any = field(init=False)
    primary: Any = field(init=False)
    problems: Any = field(init=False)
    resolved_classes: Any = field(init=False)
    subclass_pruned: Any = field(init=False)
    total_level: Any = field(init=False)
    warnings: Any = field(init=False)
    background_dict: Any = field(init=False)
    background_feats: Any = field(init=False)
    bg: Any = field(init=False)
    bg_id: Any = field(init=False)
    feat_options: Any = field(init=False)
    granted_feats: Any = field(init=False)
    held: Any = field(init=False)
    race: Any = field(init=False)
    race_id: Any = field(init=False)
    species: Any = field(init=False)
    species_alt: Any = field(init=False)
    species_choices_raw: Any = field(init=False)
    species_size: Any = field(init=False)
    species_spell_ability: Any = field(init=False)
    species_variant: Any = field(init=False)
    subrace: Any = field(init=False)
    subrace_id: Any = field(init=False)
    use_feat_prereqs: Any = field(init=False)
    use_prerequisites_prefs: Any = field(init=False)
    background_ability_choice_tpl: Any = field(init=False)
    background_bonuses: Any = field(init=False)
    background_clamped_notes: Any = field(init=False)
    base_scores: Any = field(init=False)
    ruleset: Any = field(init=False)
    species_ability_choice_tpl: Any = field(init=False)
    species_bonuses: Any = field(init=False)
    _origin_choices_raw: Any = field(init=False)
    bg_grant_choices_raw: Any = field(init=False)
    either_or_defaults: Any = field(init=False)
    species_feat_templates: Any = field(init=False)
    species_feats: Any = field(init=False)
    asi_feat_deltas_by_cid: Any = field(init=False)
    asi_feat_picks: Any = field(init=False)
    asi_feats_by_cid: Any = field(init=False)
    asi_taken_before_cid: Any = field(init=False)
    cap_skipped_asi_feat_cids: Any = field(init=False)
    ea_lessons: Any = field(init=False)
    fs_feats: Any = field(init=False)
    fs_slots_by_class: Any = field(init=False)
    fs_taken_by_cid: Any = field(init=False)
    lessons_feats: Any = field(init=False)
    lessons_resolver: Any = field(init=False)
    lessons_slots_by_class: Any = field(init=False)
    prerequisite_blocked_asi_feat_cids: Any = field(init=False)
    srd_fs_slots_by_class: Any = field(init=False)
    variant_follow: Any = field(init=False)
    applied_fixed_deltas_by_instance: Any = field(init=False)
    background_chosen_ability_deltas_by_instance: Any = field(init=False)
    feat_ability_choice_tpls: Any = field(init=False)
    final_scores: Any = field(init=False)
    fixed_clamped_notes: Any = field(init=False)
    species_feat_ability_tpls: Any = field(init=False)
    asi_selected_feats: Any = field(init=False)
    choice_templates: Any = field(init=False)
    modifiers: Any = field(init=False)
    prof_bonus: Any = field(init=False)
    pruned_ability_notes: Any = field(init=False)
    resolved_feats: Any = field(init=False)
    xphb_effects: Any = field(init=False)
    equipment_dependents: Any = field(init=False)
    warlock_spell_ctx: Any = field(init=False)
    choices: Any = field(init=False)
    details: Any = field(init=False)
    equipment_dict: Any = field(init=False)
    pruned: Any = field(init=False)
    added_resolved: Any = field(init=False)
    chosen_equipment: Any = field(init=False)
    equipped_items: Any = field(init=False)
    gear: Any = field(init=False)
    granted_equipment: Any = field(init=False)
    narrative_items: Any = field(init=False)
    pact_weapon_id: Any = field(init=False)
    slot_granting_class_ids: Any = field(init=False)
    spell_slots: Any = field(init=False)
    spells_summary: Any = field(init=False)
    starting_gold: Any = field(init=False)
    warlock_slots: Any = field(init=False)
    fixed_languages: Any = field(init=False)
    invocation_effects: Any = field(init=False)
    poe_priors: Any = field(init=False)
    positioned_languages: Any = field(init=False)
    proficient_armor: Any = field(init=False)
    proficient_save_abilities: Any = field(init=False)
    proficient_skills: Any = field(init=False)
    proficient_tools: Any = field(init=False)
    proficient_weapons: Any = field(init=False)
    class_levels: Any = field(init=False)
    effects: Any = field(init=False)
    expertise_all: Any = field(init=False)
    hp_class_entries: Any = field(init=False)
    hp_type: Any = field(init=False)
    initiative_jack: Any = field(init=False)
    initiative_remarkable: Any = field(init=False)
    saves: Any = field(init=False)
    skills: Any = field(init=False)
    derived: Any = field(init=False)
    feat_inst: Any = field(init=False)
    feat_numbers: Any = field(init=False)
    weapon_masteries: Any = field(init=False)


def _pass_classes(rs: ResolveState) -> None:
    """Sources, normalised draft, class entries -> resolved_classes, total level, primary class."""
    catalog = rs.catalog
    draft = rs.draft
    draft, problems = normalize_draft(draft)
    warnings: list[dict] = []
    # API-02: `sources` is read once into a bounded lowercase set that every filter below receives
    sources_set, too_many_sources = _normalised_sources(draft.get("sources"))
    if sources_set is not None:
        draft["sources"] = sources_set
    if too_many_sources:
        warnings.append({"id": "sources-too-many", "message": msg("sources-too-many", max=MAX_SOURCES)})

    classes_raw = draft.get("classes")
    if classes_raw is None:
        classes_raw = []
    elif not isinstance(classes_raw, list):
        problems.append({"id": "malformed-classes", "message": msg("malformed-classes")})
        classes_raw = []
    classes = [c for c in classes_raw if isinstance(c, dict)]
    if len(classes) != len(classes_raw):
        problems.append({"id": "malformed-class-entry", "message": msg("malformed-class-entry")})

    seen_class_ids: set[str] = set()
    deduped_classes: list[dict] = []
    for c in classes:
        cid_check = c.get("classId")
        if cid_check in seen_class_ids:
            problems.append({"id": "duplicate-class", "message": msg("duplicate-class", cls=cid_check)})
            continue
        if cid_check is not None:
            seen_class_ids.add(cid_check)
        deduped_classes.append(c)
    classes = deduped_classes

    resolved_classes: list[dict] = []
    subclass_pruned: list[dict] = []
    for idx, entry in enumerate(classes):
        entry_cls_id = entry.get("classId")
        entry_subclass_id = entry.get("subclassId")
        entry_level = entry.get("level", 1)  # G8: an int, normalize_draft coerced it (or the key is absent: 1)
        if not (1 <= entry_level <= 20):
            problems.append({"id": "level-unsupported", "message": msg("level-out-of-range", level=entry_level, cls=entry_cls_id)})
            entry_level = 1

        entry_cls = catalog.classes.get(entry_cls_id) if entry_cls_id else None
        if entry_cls and draft.get("ruleset") == "2024":  # C9a: XPHB chassis (raw string, as O2)
            entry_cls = catalog.classes_2024.get(entry_cls_id, entry_cls)
        if entry_cls_id and not entry_cls:
            problems.append({"id": "unknown-class", "message": msg("unknown-class", id=entry_cls_id)})

        entry_subclass = catalog.subclasses.get(entry_subclass_id) if entry_subclass_id else None
        if entry_subclass_id and not entry_subclass:
            problems.append({"id": "unknown-subclass", "message": msg("unknown-subclass", id=entry_subclass_id)})
            entry_subclass_id = None
        elif entry_subclass and entry_cls_id and entry_subclass.get("class", {}).get("index") != entry_cls_id:
            problems.append({
                "id": "subclass-mismatch",
                "message": msg("subclass-mismatch", subclass=entry_subclass["name"], cls=entry_cls_id),
            })
            entry_subclass_id = None

        unlock_level = subclass_unlock_level(entry_cls_id, draft.get("ruleset"))  # ruleset is validated further down; only "2024" matters here
        if entry_subclass and unlock_level and entry_level < unlock_level:
            # Round-2 F4: level-down leaves `subclassId` in the draft (the UI only
            # hides the select). Below the unlock level it must not apply.
            subclass_pruned.append({
                "choiceId": f"class:{entry_cls_id}:subclass",
                "reason": msg("pruned-subclass-unlocks", subclass=entry_subclass["name"], cls=entry_cls_id, level=unlock_level),
            })
            entry_subclass = None
            entry_subclass_id = None

        entry_choices_raw = entry.get("choices")
        entry_class_choices = entry_choices_raw if isinstance(entry_choices_raw, dict) else {}

        resolved_classes.append({
            "index": idx, "cls_id": entry_cls_id, "cls": entry_cls, "level": entry_level,
            "subclass_id": entry_subclass_id, "subclass": entry_subclass, "class_choices": entry_class_choices,
        })

    # Computed AFTER the per-class loop above (not from raw `classes`), so
    # this reflects each entry's CLAMPED/validated level — an out-of-range
    # submitted level (e.g. 25) is reset to 1 by that loop, and this check
    # must agree with the level that's actually used everywhere else in
    # resolve(), not the raw, never-used submitted value.
    total_level = sum(rc["level"] for rc in resolved_classes)
    if total_level > 20:
        problems.append({"id": "total-level-exceeded", "message": msg("total-level-exceeded", total=total_level)})

    primary = resolved_classes[0] if resolved_classes else None
    cls_id = primary["cls_id"] if primary else None
    cls = primary["cls"] if primary else None
    subclass_id = primary["subclass_id"] if primary else None
    subclass = primary["subclass"] if primary else None
    level = primary["level"] if primary else 1
    class_choices = primary["class_choices"] if primary else {}
    rs.classes = classes
    rs.cls = cls
    rs.cls_id = cls_id
    rs.draft = draft
    rs.primary = primary
    rs.problems = problems
    rs.resolved_classes = resolved_classes
    rs.subclass_pruned = subclass_pruned
    rs.total_level = total_level
    rs.warnings = warnings


def _pass_background(rs: ResolveState) -> None:
    """The background, its granted feats and feat options."""
    catalog = rs.catalog
    draft = rs.draft
    problems = rs.problems
    warnings = rs.warnings
    background_raw = draft.get("background")
    if background_raw is not None and not isinstance(background_raw, dict):
        problems.append({"id": "malformed-background", "message": msg("malformed-background")})
        background_raw = {}
    background_dict = background_raw or {}
    bg_id = background_dict.get("id")
    bg = catalog.backgrounds.get(bg_id) if bg_id else None
    if bg_id and not bg:
        problems.append({"id": "unknown-background", "message": msg("unknown-background", id=bg_id)})
    elif bg and not _source_allowed(bg, draft.get("sources")):
        # Round-2 F3: hidden by the Sources filter is a picker filter only
        # (like ruleset); the record still resolves, with a warning. Only ids
        # absent from the full catalog are `unknown-background` problems.
        warnings.append({
            "id": "source-hidden-background",
            "message": msg("source-hidden", name=bg["name"]),
        })

    # Phase 4b Task 6: a background's `feats` field lands on the sheet as a
    # list of bare ids unchanged — no prerequisite checking here. Always a
    # list (never null), mirroring damage_modifiers/condition_immunities/
    # innate_spells' own "always present, empty when absent" convention.
    # Phase 4c-i Task 5: no longer PURELY inert — resolved (best-effort;
    # see _resolve_granted_feats) against catalog.feats so each granted
    # feat's resist/immune/condition_immune/senses can be folded into the
    # SAME sheet fields race/subrace already populate. Phase 4c-i Task 6
    # HOISTS this resolution from its old position (right before sheet
    # assembly, well after ability scores and proficiencies were already
    # finalized) up to HERE — right after `bg` itself is resolved, and
    # before species/ability-score/proficiency processing below — because
    # this task adds MORE feat-granted effect types (ability bonuses,
    # proficiencies, languages, expertise, saving throws) that need to
    # flow into the SAME early merge points species/background bonuses
    # and race/background proficiencies already feed, not a separate,
    # later, parallel path. `resolved_feats` (used throughout the rest of
    # resolve()) is a real structural relocation of existing Task 5 logic,
    # not new resolution behavior.
    granted_feats = list(bg.get("feats", [])) if bg else []
    # Finding 2 of the final whole-branch review (2026-09-27): a background
    # whose real `feats` data is an "alternatives" grant (Rewarded/Ruined,
    # BMT — "gain Lucky, Magic Initiate, or Skilled, your choice") now
    # contributes nothing to `granted_feats` and instead surfaces its
    # candidates here, kept distinct from an actual grant for the same
    # inert-pass-through reason `feat_options` itself exists in
    # official_source.py — see that field's own docstring. feat_options
    # candidates are NOT resolved for effects — they're unresolved
    # alternatives, not something the character actually has yet.
    feat_options = list(bg.get("feat_options", [])) if bg else []
    # Finding 1 of the final whole-branch review (2026-09-28): `feat_refs`
    # is a THIRD, source-qualified parallel to `granted_feats` (see
    # official_source._feats_from_5etools' own docstring) — passed through
    # so _resolve_granted_feats can try an exact "slug-source" match
    # before falling back to its bare-slug ambiguity logic. Bundled SRD
    # backgrounds and hand-authored test dicts carry no `feat_refs` key at
    # all, so this defaults to `[]`, a safe no-op (see that function's own
    # docstring for why `granted_feat_refs=None`/empty behaves identically
    # to before this fix).
    granted_feat_refs = list(bg.get("feat_refs", [])) if bg else []
    background_feats = _resolve_granted_feats(granted_feats, catalog, granted_feat_refs)
    rs.background_dict = background_dict
    rs.background_feats = background_feats
    rs.bg = bg
    rs.bg_id = bg_id
    rs.feat_options = feat_options
    rs.granted_feats = granted_feats


def _pass_species(rs: ResolveState) -> None:
    """Species, subspecies, variant, the held-feat state and the pre-walk proficiency grants."""
    background_feats = rs.background_feats
    bg = rs.bg
    catalog = rs.catalog
    draft = rs.draft
    problems = rs.problems
    resolved_classes = rs.resolved_classes
    warnings = rs.warnings
    # ASI-or-feat Task 3: a feat a class took INSTEAD of an ASI joins the
    # SAME `resolved_feats` list (assembled right after the per-class ASI
    # loop below, once each pick's prerequisite has been checked at its own
    # level), so every generic feat-effects consumer (proficiencies,
    # languages, expertise, saving throws, senses, damage modifiers,
    # condition immunities, prerequisite problems) applies it with no
    # special-casing. `background_feats` is kept apart for exactly the
    # three places where an ASI-selected feat must NOT be handled the
    # background way: its ability bonus (fixed + chosen) is applied inside
    # _apply_asi_progression's per-level walk via `asi_feat_deltas_by_cid`,
    # not in the early flat `feat_bonuses` pass (that would double-apply it
    # and put it before earlier levels' cap checks); and its own choice
    # templates are built origin-scoped in the per-class loop, not with the
    # default un-scoped `feat:{index}:...` cids (which would duplicate them).
    species_raw = draft.get("species")
    if species_raw is not None and not isinstance(species_raw, dict):
        problems.append({"id": "malformed-species", "message": msg("malformed-species")})
        species_raw = {}
    species = species_raw or {}
    race_id = species.get("id")
    race = catalog.races.get(race_id) if race_id else None
    if race_id and not race:
        problems.append({"id": "unknown-species", "message": msg("unknown-species", id=race_id)})
    elif race and not _source_allowed(race, draft.get("sources")):
        warnings.append({
            "id": "source-hidden-species",
            "message": msg("source-hidden", name=race["name"]),
        })

    subrace_id = species.get("subspeciesId")
    subrace = catalog.subraces.get(subrace_id) if subrace_id else None
    if subrace_id and not subrace:
        problems.append({"id": "unknown-subspecies", "message": msg("unknown-subspecies", id=subrace_id)})
    elif subrace and race_id and not race:
        subrace = None  # the species itself is unknown (reported above): no cascading mismatch
    elif subrace and (not race or subrace.get("race", {}).get("index") != race_id):
        problems.append({
            "id": "subspecies-mismatch",
            "message": msg("subspecies-mismatch", name=subrace["name"]),
        })
        subrace = None
    elif subrace and not _source_allowed(subrace, draft.get("sources")):
        # Subspecies carry their own book (Duergar is MTF under PHB Dwarf);
        # like a source-hidden species it still resolves, with a warning.
        warnings.append({
            "id": "source-hidden-subspecies",
            "message": msg("source-hidden", name=subrace["name"]),
        })

    # Read here (before the per-class loop) so _asi_choice_templates can use
    # it below; `use_prereqs` (multiclass) is derived from the SAME dict
    # further down, near _multiclass_prerequisite_problems.
    species_choices_raw = species.get("choices") if isinstance(species.get("choices"), dict) else {}
    # Slice 8b: the selected lineage / ancestry / legacy of a race with `variants`.
    species_variant = _selected_species_variant(race, species_choices_raw, race_id)
    species_size = _species_size(race, species_choices_raw, race_id)
    species_alt = _selected_species_alternative(race, subrace, catalog, species_choices_raw, race_id)  # F1
    species_spell_ability = _selected_species_spell_ability(race, subrace, catalog, species_variant, species_choices_raw, race_id)  # F1
    use_prerequisites_prefs = (draft.get("preferences") or {}).get("usePrerequisites", {})
    use_feat_prereqs = bool(use_prerequisites_prefs.get("feats"))

    held = _HeldFeatState()
    for bg_feat in background_feats:
        held.add_feat(bg_feat)
    # Pre-walk inputs use the FINAL character (same simplification as
    # total_level): permissive, never a false disable.
    held.has_spellcasting_feature = any(
        rc["cls"] and spells_mod.single_class_spell_slots(catalog, rc["cls_id"], rc["level"], rc["subclass_id"], draft.get("ruleset"))
        for rc in resolved_classes
    )
    held.fighting_style = any(_class_has_fighting_style(catalog, rc) for rc in resolved_classes if rc["cls"] and rc["cls_id"])  # C3
    held.race_names, held.subrace_names, held.size = _held_race_state(race, subrace, species_size)
    held.can_cast_spell = held.has_spellcasting_feature or bool(
        _species_innate_spells(race, subrace, catalog, species_variant, species_alt, species_spell_ability)
    )
    # FIXED proficiency grants only (class, race/subrace traits, background);
    # proficiency CHOICE selections aren't available before the ASI walk.
    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        class_profs = (
            rc["cls"].get("proficiencies", []) if rc["index"] == 0
            else rc["cls"].get("multi_classing", {}).get("proficiencies", [])
        )
        held.proficiency_ids.update(p["index"] for p in class_profs)
    if race:
        for ref in list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else []):
            trait = catalog.traits.get(ref["index"])
            if trait:
                held.proficiency_ids.update(p["index"] for p in trait.get("proficiencies", []))
    if bg:
        held.proficiency_ids.update(p["index"] for p in bg.get("starting_proficiencies", []))
    rs.held = held
    rs.race = race
    rs.race_id = race_id
    rs.species = species
    rs.species_alt = species_alt
    rs.species_choices_raw = species_choices_raw
    rs.species_size = species_size
    rs.species_spell_ability = species_spell_ability
    rs.species_variant = species_variant
    rs.subrace = subrace
    rs.subrace_id = subrace_id
    rs.use_feat_prereqs = use_feat_prereqs
    rs.use_prerequisites_prefs = use_prerequisites_prefs


def _pass_abilities(rs: ResolveState) -> None:
    """Ruleset, ASI policy, species and background ability bonuses."""
    background_dict = rs.background_dict
    bg = rs.bg
    bg_id = rs.bg_id
    catalog = rs.catalog
    draft = rs.draft
    problems = rs.problems
    race = rs.race
    race_id = rs.race_id
    resolved_classes = rs.resolved_classes
    species_choices_raw = rs.species_choices_raw
    subrace = rs.subrace
    warnings = rs.warnings
    # Final ability scores: base + species bonuses + background bonuses +
    # feat bonuses. Backgrounds DO grant ability bonuses as of Phase 4b
    # Task 4 — the 2024-style ability-score-improvement choice (see
    # _background_ability_bonus_choice_template below) — so background
    # selections flow into this SAME early pass alongside species' own,
    # exactly like species_bonuses does just below. Phase 4c-i Task 6:
    # `resolved_feats` (already computed above, right after `bg` itself)
    # is a THIRD source into this same pass, via _feat_ability_bonuses —
    # that function stays fixed-grants-only by design (mirroring
    # _background_ability_bonuses' own scope). The feat's CHOICE portion
    # (ability_bonus_options) is no longer an unhandled gap: it's the
    # FOURTH source folded in just below via feat_ability_choice_tpls
    # (Phase 4c-ii Task 2).
    base_scores = (draft.get("abilities") or {}).get("base") or {}
    problems += _ability_method_problems(draft.get("abilities") or {})
    ruleset = draft.get("ruleset")
    if ruleset is None:
        ruleset = "mixed"
    elif ruleset not in RULESETS:
        warnings.append({"id": "ruleset-invalid", "message": msg("ruleset-invalid", ruleset=ruleset)})
        ruleset = "mixed"
    if ruleset == "2024":  # RP21: the stored invocation picks follow their repeat instance (`<id>~k`) when the base goes
        for rc in resolved_classes:
            if rc["cls_id"] == "warlock" and rc["cls"]:
                rc["class_choices"] = class_choices_2024.renumber_invocation_instances(catalog, rc, ruleset, rc["class_choices"])
    species_asi_on, background_asi_on, asi_warnings = _asi_policy(ruleset, race, subrace, bg)
    warnings += asi_warnings
    species_bonuses = _species_ability_bonuses(race, subrace) if species_asi_on else {}
    species_ability_choice_tpl = (
        _species_ability_bonus_choice_template(race, subrace, race_id) if species_asi_on else None
    )
    if species_ability_choice_tpl:
        valid_ability_ids = {o["id"] for o in species_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = species_choices_raw.get(species_ability_choice_tpl["id"]) or []
        # Dedupe BEFORE capping to `count` and applying bonuses — otherwise a
        # duplicate selection (e.g. ["str", "str"]) would apply the same
        # ability's bonus twice with no problem reported.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_abilities = [s for s in deduped_selected if s in valid_ability_ids][: species_ability_choice_tpl["count"]]
        # Deltas come from the option itself: +1 for the SRD Half-Elf and
        # `count` choices, +2 for `amount: 2` choices, and +2/+1 or +1/+1/+1
        # bundles for VRGR lineages. Env is the race's or subrace's, whichever
        # supplied the template.
        env_src = next(src for src in _ability_sources(race, subrace) if src.get("ability_bonus_options"))
        species_deltas = _background_ability_bonus_deltas(env_src["ability_bonus_options"], species_ability_choice_tpl["options"])
        for ab_id in selected_abilities:
            for ab_key, delta in species_deltas.get(ab_id, []):
                species_bonuses[ab_key] = species_bonuses.get(ab_key, 0) + delta

    background_bonuses = _background_ability_bonuses(bg)
    background_clamped_notes: list[dict] = []  # RP1
    background_ability_choice_tpl = _background_ability_bonus_choice_template(bg, bg_id) if background_asi_on else None
    if background_ability_choice_tpl:
        background_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}
        valid_bundle_ids = {o["id"] for o in background_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = background_choices_raw.get(background_ability_choice_tpl["id"]) or []
        # Same dedupe-before-cap-and-apply discipline as species' own pass
        # just above.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_bundles = [s for s in deduped_selected if s in valid_bundle_ids][: background_ability_choice_tpl["count"]]
        bundle_deltas = _background_ability_bonus_deltas(bg["ability_bonus_options"], background_ability_choice_tpl["options"])
        for bundle_id in selected_bundles:
            for ab_key, delta in bundle_deltas.get(bundle_id, []):
                background_bonuses[ab_key] = background_bonuses.get(ab_key, 0) + delta

    # RP1 (X1): PHB 2024 background step: "None of these increases can raise a score above 20." The 2024 species
    # increase is off, so the background step sits on the base scores. Only the 2024 ruleset clamps (the 2014 rules
    # have no such sentence); the lost part is a non-blocking `pruned` entry like the FX7 feat clamp.
    if ruleset == "2024" and background_ability_choice_tpl and background_bonuses:
        for ab_key in derived_mod.ABILITIES:
            delta = background_bonuses.get(ab_key, 0)
            if delta <= 0:
                continue
            try:
                raw_base = int(base_scores.get(ab_key, 10))
            except (TypeError, ValueError):
                raw_base = 10
            applied = asi_mod.clamped_delta(ab_key, delta, {ab_key: raw_base + species_bonuses.get(ab_key, 0)})
            if applied < delta:
                background_bonuses[ab_key] = applied
                background_clamped_notes.append({
                    "choiceId": background_ability_choice_tpl["id"],
                    "reason": msg("pruned-ability-at-max", name=bg["name"], ab=ab_key, cap=asi_mod.ASI_CAP)})
    rs.background_ability_choice_tpl = background_ability_choice_tpl
    rs.background_bonuses = background_bonuses
    rs.background_clamped_notes = background_clamped_notes
    rs.base_scores = base_scores
    rs.problems = problems
    rs.ruleset = ruleset
    rs.species_ability_choice_tpl = species_ability_choice_tpl
    rs.species_bonuses = species_bonuses
    rs.warnings = warnings


def _pass_origin_feats(rs: ResolveState) -> None:
    """Feats granted by the species and the background feat slots."""
    background_bonuses = rs.background_bonuses
    background_dict = rs.background_dict
    background_feats = rs.background_feats
    base_scores = rs.base_scores
    bg = rs.bg
    bg_id = rs.bg_id
    catalog = rs.catalog
    draft = rs.draft
    held = rs.held
    problems = rs.problems
    race = rs.race
    race_id = rs.race_id
    ruleset = rs.ruleset
    species_bonuses = rs.species_bonuses
    species_choices_raw = rs.species_choices_raw
    subrace = rs.subrace
    total_level = rs.total_level
    use_feat_prereqs = rs.use_feat_prereqs
    warnings = rs.warnings
    # Slice 8a: feats a species grants (Human/XPHB's Origin feat, Variant
    # Human's and Custom Lineage's free feat). Resolved BEFORE the ASI walk
    # so a species pick makes the same feat unavailable at an ASI level
    # (precedence: background -> species -> ASI levels, first pick wins).
    # Checked against the scores before any feat bonus and a snapshot of what
    # the character holds from the background alone.
    species_feat_templates: list[dict] = []
    species_feats: list[dict] = []
    either_or_defaults: dict[str, list[str]] = {}  # F1: {card id: [plain feat option id]} for an unpicked either-or card
    bg_grant_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}
    bg_feat_slots = _background_feat_grant_slots(bg, bg_id)

    def _origin_choices_raw(feat: dict) -> dict:  # where a granted feat's cascaded picks are stored
        return bg_grant_choices_raw if feat.get("_background_grant") else species_choices_raw
    if race or bg_feat_slots:
        pre_feat_scores = {}
        for ab in derived_mod.ABILITIES:
            try:
                raw_base = int(base_scores.get(ab, 10))
            except (TypeError, ValueError):
                raw_base = 10
            pre_feat_scores[ab] = raw_base + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0)
        species_held_snapshot = held.copy()
        taken_feat_indices = _taken_add({}, background_feats)
        # W4: the background's own feat grant cards come first (precedence background -> species -> ASI) and reuse
        # the species feat card machinery; their feats join `species_feats` (the "origin pick feats" list) tagged
        # `_background_grant`, so the S2 duplicate map, the ASI pre-walk and the cascaded choices all see them.
        slots = [(c, g, "background", bg, bg_id, bg_grant_choices_raw) for c, g in bg_feat_slots]
        if race:
            slots += [(c, g, "species", race, race_id, species_choices_raw) for c, g in _species_feat_grant_slots(race, subrace, race_id)]
        for slot_cid, grant, slot_kind, owner, owner_id, owner_raw in slots:
            tpl = _species_feat_choice_template(
                owner, owner_id, slot_cid, grant, catalog, draft.get("sources"), pre_feat_scores, total_level,
                use_feat_prereqs, species_held_snapshot, taken_feat_indices, ruleset,
                keep=owner_raw.get(slot_cid) if isinstance(owner_raw.get(slot_cid), list) else (), kind=slot_kind,
            )
            species_feat_templates.append(tpl)
            default_pick = _either_or_default_pick(tpl, grant, owner_raw)
            if default_pick:  # F1: no stored pick on an either-or card: the plain feat (Survivor / Sharp Eye)
                owner_raw = {**owner_raw, slot_cid: [default_pick]}
                either_or_defaults[slot_cid] = [default_pick]
            picked = _resolve_species_selected_feats(tpl, owner_raw, catalog, problems, background_grant=slot_kind == "background")
            for feat in picked:
                if not _feat_offered(feat, draft.get("sources"), ruleset):
                    warnings.append({
                        "id": f"feat-hidden-by-filters-{slot_cid}",
                        "message": msg("feat-hidden-by-filters", feat=feat["name"]),
                    })
            species_feats += picked
            _taken_add(taken_feat_indices, picked)
    for species_feat in species_feats:
        held.add_feat(species_feat)
    rs._origin_choices_raw = _origin_choices_raw
    rs.bg_grant_choices_raw = bg_grant_choices_raw
    rs.either_or_defaults = either_or_defaults
    rs.species_feat_templates = species_feat_templates
    rs.species_feats = species_feats


def _pass_feat_walk(rs: ResolveState) -> None:
    """Fighting-style cards, Lessons feats and ASI-selected feats in one ordered walk."""
    _origin_choices_raw = rs._origin_choices_raw
    background_feats = rs.background_feats
    bg = rs.bg
    bg_grant_choices_raw = rs.bg_grant_choices_raw
    catalog = rs.catalog
    draft = rs.draft
    held = rs.held
    problems = rs.problems
    resolved_classes = rs.resolved_classes
    ruleset = rs.ruleset
    species_choices_raw = rs.species_choices_raw
    species_feats = rs.species_feats
    warnings = rs.warnings
    # C3: 2024 fighting-style feat cards (precedence: background, species, then
    # fighting-style cards and ASI picks together by class level, F1; first pick wins).
    fs_slots_by_class = {
        rc["index"]: _fighting_style_slots(catalog, rc, draft.get("sources"), ruleset)
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    skipped_duplicate_fs_feats: list[dict] = []
    srd_fs_slots_by_class = {
        rc["index"]: _srd_fighting_style_slots(catalog, rc, {idx for _c, _l, idx in fs_slots_by_class.get(rc["index"], [])})
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    skipped_srd_styles: list[dict] = []
    fs_resolver = _FightingStyleResolver(fs_slots_by_class, catalog, skipped_duplicate_fs_feats,
                                         srd_fs_slots_by_class, skipped_srd_styles)
    skipped_duplicate_lessons: list[dict] = []  # C7c
    lessons_slots_by_class = _lessons_slots(catalog, resolved_classes, ruleset)
    lessons_resolver = _LessonsResolver(lessons_slots_by_class, catalog, skipped_duplicate_lessons)
    skipped_duplicate_ea_lessons: list[dict] = []  # RP20
    ea_lessons = _FeatLessonsResolver(
        catalog, ruleset, next((rc["level"] for rc in resolved_classes if rc["cls_id"] == "warlock" and rc["cls"]), 0),
        any(lessons_slots_by_class.values()), skipped_duplicate_ea_lessons)

    def walk_hook(rc, upto_level, seen):  # one ordered walk: fighting-style cards, Lessons feats, then the ASI picks
        fs_resolver(rc, upto_level, seen)
        lessons_resolver(rc, upto_level, seen)
    skipped_duplicate_asi_feats: list[dict] = []
    walk_seen0 = _taken_add({}, background_feats + species_feats)
    for sf in species_feats:  # RP4: an origin Fighting Initiate style is held before every class card
        _fi_seen_add(walk_seen0, catalog, sf, _origin_choices_raw(sf).get(f"{sf['_species_origin']}:fighting-style"), ruleset)
    asi_taken_before_cid: dict[str, dict[str, str]] = {}
    # F1: fighting-style cards and ASI picks resolve in one pass, ordered by (class
    # index, class level); the later pick is the duplicate.
    asi_feat_picks, asi_feat_deltas_by_cid = _resolve_asi_selected_feats(
        resolved_classes, catalog, draft.get("sources"),
        taken_indices=walk_seen0,
        skipped_duplicates=skipped_duplicate_asi_feats, ruleset=ruleset, fighting_style=held.fighting_style,
        before_level=walk_hook, taken_before_cid=asi_taken_before_cid, after_feat=ea_lessons,
    )
    fs_feats, fs_taken_by_cid = fs_resolver.picks, fs_resolver.taken_by_cid
    raw_all_choices: dict = {}  # G5: every raw selection of the draft (cids never collide across owners)
    for rc_ in resolved_classes:
        raw_all_choices.update(rc_["class_choices"])
    raw_all_choices.update(bg_grant_choices_raw)
    raw_all_choices.update(species_choices_raw)
    variant_follow = _followed_variants(background_feats + species_feats + fs_feats + asi_feat_picks, raw_all_choices,
                                        (bg.get("feat_variant_hints") if bg else None) or {}, background_feats)
    lessons_feats = lessons_resolver.picks + ea_lessons.picks  # RP20: Lessons held through Eldritch Adept follow the Warlock's
    for dup in skipped_srd_styles:  # G1
        problems.append({
            "id": f"fighting-style-duplicate-{dup['option']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for dup in skipped_duplicate_fs_feats:
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["feat"]["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for fs_feat in fs_feats:
        held.add_feat(fs_feat)
        if not _feat_offered(fs_feat, draft.get("sources"), ruleset):
            warnings.append({
                "id": f"feat-hidden-by-filters-{fs_feat['_fs_cid']}",
                "message": msg("feat-hidden-by-filters", feat=fs_feat["name"]),
            })
    for dup in skipped_duplicate_lessons + skipped_duplicate_ea_lessons:  # C7c, RP20
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["feat"]["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for lessons_feat in lessons_feats:
        held.add_feat(lessons_feat)
        if not _feat_offered(lessons_feat, draft.get("sources"), ruleset):
            warnings.append({
                "id": f"feat-hidden-by-filters-{lessons_feat['_inv_cid']}",
                "message": msg("feat-hidden-by-filters", feat=lessons_feat["name"]),
            })

    for dup in skipped_duplicate_asi_feats:
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["feat"]["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for pick in asi_feat_picks:
        if not _asi_feat_in_pool(pick, draft.get("sources"), ruleset, pick["_asi_level"], held.fighting_style):
            warnings.append({
                "id": f"feat-hidden-by-filters-{pick['_asi_cid']}",
                "message": msg("feat-hidden-by-filters", feat=pick["name"]),
            })
    asi_feats_by_cid = {f["_asi_cid"]: f for f in asi_feat_picks}
    prerequisite_blocked_asi_feat_cids: set[str] = set()
    cap_skipped_asi_feat_cids: set[str] = set()  # FE2: ASI feats whose increase did not fit under their cap
    rs.asi_feat_deltas_by_cid = asi_feat_deltas_by_cid
    rs.asi_feat_picks = asi_feat_picks
    rs.asi_feats_by_cid = asi_feats_by_cid
    rs.asi_taken_before_cid = asi_taken_before_cid
    rs.cap_skipped_asi_feat_cids = cap_skipped_asi_feat_cids
    rs.ea_lessons = ea_lessons
    rs.fs_feats = fs_feats
    rs.fs_slots_by_class = fs_slots_by_class
    rs.fs_taken_by_cid = fs_taken_by_cid
    rs.lessons_feats = lessons_feats
    rs.lessons_resolver = lessons_resolver
    rs.lessons_slots_by_class = lessons_slots_by_class
    rs.prerequisite_blocked_asi_feat_cids = prerequisite_blocked_asi_feat_cids
    rs.srd_fs_slots_by_class = srd_fs_slots_by_class
    rs.variant_follow = variant_follow


def _pass_origin_ability_deltas(rs: ResolveState) -> None:
    """Ability deltas of the origin feats and the scores before the ASI walk."""
    _origin_choices_raw = rs._origin_choices_raw
    background_bonuses = rs.background_bonuses
    background_dict = rs.background_dict
    background_feats = rs.background_feats
    base_scores = rs.base_scores
    problems = rs.problems
    species_bonuses = rs.species_bonuses
    species_feats = rs.species_feats
    warnings = rs.warnings
    # FE2 (B2): origin feats (background, then species) have no per-level gate to skip at, so each one's
    # delta is CLAMPED to the room left under its own cap (20, or 30 for an Epic Boon) on the scores it lands on:
    # base + species + background bonuses, then the earlier origin feats. Only the feat's delta is clamped, never
    # the species / background bonuses themselves. ASI-selected feats: see _apply_asi_progression.
    feat_bonuses: dict[str, int] = {}
    origin_running: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        try:
            raw_base = int(base_scores.get(ab, 10))
        except (TypeError, ValueError):
            raw_base = 10
        origin_running[ab] = raw_base + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0)
    applied_fixed_deltas_by_instance: dict[str, list[tuple[str, int]]] = {}  # what was really added, per feat instance

    def _apply_origin_delta(feat: dict, ab_key: str, delta: int) -> int:
        applied = asi_mod.clamped_delta(ab_key, delta, origin_running, _feat_ability_cap(feat))
        if applied:
            feat_bonuses[ab_key] = feat_bonuses.get(ab_key, 0) + applied
            origin_running[ab_key] = origin_running.get(ab_key, 10) + applied
        return applied

    fixed_clamped_notes: list[dict] = []  # FX7: fixed increases that did not fit under the cap (non-blocking `pruned`)

    def _apply_origin_fixed(feat: dict) -> None:
        applied_list = []
        for ab_key, delta in _feat_ability_bonuses([feat]).items():
            applied = _apply_origin_delta(feat, ab_key, delta)
            applied_list.append((ab_key, applied))
            if delta > 0 and applied < delta:
                fixed_clamped_notes.append({
                    "choiceId": feat.get("_species_origin") or f"feat:{feat['index']}",
                    "reason": msg("pruned-ability-at-max-delta", name=feat["name"], ab=ab_key, cap=_feat_ability_cap(feat),
                                  delta=delta)})
        applied_fixed_deltas_by_instance[_feat_instance_key(feat)] = applied_list

    # Phase 4c-ii Task 2: a FOURTH source into this same early pass — a
    # background-granted feat's own ability_bonus_options CHOICE (as
    # opposed to _feat_ability_bonuses' fixed-only grant, folded in via
    # `feat_bonuses` above). `feats` (plural) means more than one template
    # can exist at once in principle, hence a loop rather than the
    # single-`if` shape species/background use above. A feat has no
    # section of its own in the Draft — every real and synthetic
    # background-granted feat's own Choice selections live under the SAME
    # `background.choices` dict the background's own choices already use
    # (confirmed against test_selecting_the_crafter_tool_choice_reaches_
    # the_sheet's exact draft shape, Phase 4c-ii Task 1) — hence reading
    # from `background_choices_raw` here too, not a separate dict.
    #
    # `_feat_ability_bonus_choice_templates` returns (template, feat) pairs
    # rather than bare templates precisely so each feat is looked up
    # directly off its own pair here, instead of this call site
    # reconstructing the "feat:{index}:ability-bonus" cid a second time to
    # build its own lookup dict — see that function's own docstring
    # (Finding 3 of the final whole-branch review, 2026-09-28) for the
    # silent-desync risk that duplication used to carry.
    feat_ability_choice_pairs: list[tuple[dict, dict]] = []
    feat_ability_choice_tpls: list[dict] = []
    # Task 4 (ASI-or-feat): this SAME loop already computes each
    # background-granted feat's own selected ability-bonus ids and their
    # deltas (feeding `feat_bonuses` above) — also record them here, keyed
    # by _feat_instance_key(source_feat) (a background grant has no
    # `_asi_origin`, so this is its bare `feat:{index}`), so
    # _feat_prerequisite_problems can subtract a feat's own CHOSEN bonus
    # back out before checking THAT feat's own prerequisite, exactly like
    # it already does for a feat's FIXED ability_bonuses. Passed to
    # _feat_prerequisite_problems' `chosen_ability_deltas_by_instance` param
    # BELOW UNMIXED with anything ASI-derived (fix round 1: an earlier
    # version also merged in a dict built from _resolve_asi_selected_feats,
    # which was removed as provably redundant-or-wrong — see
    # _feat_prerequisite_problems' own docstring for why only a
    # background-granted feat's own chosen bonus needs this explicit
    # subtraction at all).
    background_chosen_ability_deltas_by_instance: dict[str, list[tuple[str, int]]] = {}
    feat_background_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}

    def _apply_chosen_origin_deltas(source_feat: dict, feat_ability_tpl: dict, raw_choices: dict) -> None:
        # Options at the feat's cap are already disabled in the template (scores = the pre-feat scores), so a
        # stored pick of one is dropped here and pruned later by the generic pass.
        valid_feat_ability_ids = {o["id"] for o in feat_ability_tpl["options"] if not o.get("disabled")}
        raw_selected = raw_choices.get(feat_ability_tpl["id"]) or []
        # Same dedupe-before-cap-and-apply discipline as species'/background's own passes above.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_feat_abilities = [s for s in deduped_selected if s in valid_feat_ability_ids][: feat_ability_tpl["count"]]
        feat_ability_deltas = _feat_ability_bonus_deltas(source_feat["ability_bonus_options"])
        instance_chosen_deltas: list[tuple[str, int]] = []
        for ab_id in selected_feat_abilities:
            for ab_key, delta in feat_ability_deltas.get(ab_id, []):
                applied = _apply_origin_delta(source_feat, ab_key, delta)
                if applied:
                    instance_chosen_deltas.append((ab_key, applied))
        if instance_chosen_deltas:
            background_chosen_ability_deltas_by_instance[_feat_instance_key(source_feat)] = instance_chosen_deltas

    for background_feat in background_feats:
        _apply_origin_fixed(background_feat)
        for feat_ability_tpl, source_feat in _feat_ability_bonus_choice_templates([background_feat], scores=dict(origin_running)):
            feat_ability_choice_pairs.append((feat_ability_tpl, source_feat))
            feat_ability_choice_tpls.append(feat_ability_tpl)
            _apply_chosen_origin_deltas(source_feat, feat_ability_tpl, feat_background_choices_raw)
    # Species-granted feats: the same pass, selections read from
    # species.choices under each feat's own `_species_origin` prefix.
    species_feat_ability_tpls: list[dict] = []
    for species_feat in species_feats:
        _apply_origin_fixed(species_feat)
        for feat_ability_tpl, source_feat in _feat_ability_bonus_choice_templates(
            [species_feat], origin=species_feat["_species_origin"], scores=dict(origin_running),
        ):
            species_feat_ability_tpls.append(feat_ability_tpl)
            _apply_chosen_origin_deltas(source_feat, feat_ability_tpl, _origin_choices_raw(species_feat))

    final_scores: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        base_score = base_scores.get(ab, 10)  # G8: an int, normalize_draft coerced it (or the key is absent: 10)
        final_scores[ab] = base_score + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0) + feat_bonuses.get(ab, 0)
    for ab in derived_mod.ABILITIES:
        if isinstance(base_scores.get(ab), int) and not isinstance(base_scores.get(ab), bool) and base_scores[ab] > 20:
            warnings.append({"id": f"ability-above-20-{ab}", "message": msg("ability-above-20", ab=ab, value=base_scores[ab])})
        elif final_scores[ab] > 20 and isinstance(base_scores.get(ab), int):
            # VF1.9: the FINAL score (manual base + species + background + origin-feat bonuses; the later ASI walk caps at 20 and
            # Primal Champion / Epic Boon raise it on purpose, so they are not looked at) is above the usual cap. The manual
            # score is an override and is kept; this only says so.
            warnings.append({"id": f"ability-final-above-20-{ab}",
                             "message": msg("ability-final-above-20", ab=ab, value=final_scores[ab], base=base_scores[ab])})
    for ab, score in final_scores.items():
        if 1 <= score <= 30:
            continue
        reported = next((p for p in problems if p["id"] == f"ability-out-of-range-{ab}"), None)  # normalize may have reported the base already
        if reported is None:
            problems.append({"id": f"ability-out-of-range-{ab}", "message": msg("ability-out-of-range", ab=ab, score=score)})
        elif reported["message"].key == "ability-out-of-range-clamped":  # WF: the clamped base plus bonuses still leaves the sheet out of range
            # (a tagged rebuild, not `+=`: a string operation would drop the tag; same text as "... final" not in message)
            reported["message"] = msg("ability-out-of-range-clamped-final", final=score, **reported["message"].params)
    rs.applied_fixed_deltas_by_instance = applied_fixed_deltas_by_instance
    rs.background_chosen_ability_deltas_by_instance = background_chosen_ability_deltas_by_instance
    rs.feat_ability_choice_tpls = feat_ability_choice_tpls
    rs.final_scores = final_scores
    rs.fixed_clamped_notes = fixed_clamped_notes
    rs.species_feat_ability_tpls = species_feat_ability_tpls


def _pass_class_asi_loop(rs: ResolveState) -> None:
    """Per-class templates and the ASI progression, resolved feats, prerequisites, bonuses, modifiers, proficiency bonus."""
    applied_fixed_deltas_by_instance = rs.applied_fixed_deltas_by_instance
    asi_feat_deltas_by_cid = rs.asi_feat_deltas_by_cid
    asi_feat_picks = rs.asi_feat_picks
    asi_feats_by_cid = rs.asi_feats_by_cid
    asi_taken_before_cid = rs.asi_taken_before_cid
    background_chosen_ability_deltas_by_instance = rs.background_chosen_ability_deltas_by_instance
    background_feats = rs.background_feats
    cap_skipped_asi_feat_cids = rs.cap_skipped_asi_feat_cids
    catalog = rs.catalog
    draft = rs.draft
    ea_lessons = rs.ea_lessons
    final_scores = rs.final_scores
    fixed_clamped_notes = rs.fixed_clamped_notes
    fs_feats = rs.fs_feats
    fs_slots_by_class = rs.fs_slots_by_class
    fs_taken_by_cid = rs.fs_taken_by_cid
    held = rs.held
    lessons_feats = rs.lessons_feats
    lessons_resolver = rs.lessons_resolver
    lessons_slots_by_class = rs.lessons_slots_by_class
    prerequisite_blocked_asi_feat_cids = rs.prerequisite_blocked_asi_feat_cids
    problems = rs.problems
    resolved_classes = rs.resolved_classes
    ruleset = rs.ruleset
    species_feats = rs.species_feats
    srd_fs_slots_by_class = rs.srd_fs_slots_by_class
    total_level = rs.total_level
    use_feat_prereqs = rs.use_feat_prereqs
    use_prerequisites_prefs = rs.use_prerequisites_prefs
    variant_follow = rs.variant_follow
    choice_templates: list[dict] = []
    for rc in resolved_classes:
        rc_held_by_level: dict[int, _HeldFeatState] = {}
        rc_cls, rc_cls_id, rc_level, rc_subclass_id = rc["cls"], rc["cls_id"], rc["level"], rc["subclass_id"]
        rc_class_choices = rc["class_choices"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_asi_levels = _asi_granting_levels(catalog, rc_cls_id, rc_level)
        rc_asi_scores_by_level, final_scores, rc_blocked_feat_cids = _apply_asi_progression(
            final_scores, rc_asi_levels, rc_class_choices, rc_cls_id,
            asi_feats_by_cid, asi_feat_deltas_by_cid, total_level, use_feat_prereqs,
            held=held, held_by_level=rc_held_by_level, cap_skipped_feat_cids=cap_skipped_asi_feat_cids,
        )
        prerequisite_blocked_asi_feat_cids |= rc_blocked_feat_cids
        # A feat picked at an ASI level whose option is disabled there
        # (prerequisite unmet at THAT level's running scores — the same
        # data the option's `disabled` flag is computed from) is not
        # applied at all, exactly like an over-cap combo pick; reported
        # here so the player sees why, since unlike an over-cap combo it
        # may not be obvious from the option list alone.
        for blocked_cid in sorted(rc_blocked_feat_cids):
            blocked_feat = asi_feats_by_cid[blocked_cid]
            problems.append({
                "id": f"feat-prerequisite-unmet-{blocked_feat['index']}",
                "message": msg("feat-prerequisite-unmet-at-level", feat=blocked_feat["name"], cls=rc_cls["name"],
                               level=blocked_feat["_asi_level"]),
            })
        rc["asi_levels"] = rc_asi_levels  # stashed for Task 4's prerequisite check convenience, and for sheet assembly

        if rc["index"] == 0:
            choice_templates += _class_choice_templates(rc_cls, rc_cls_id)
        else:
            choice_templates += _multiclass_proficiency_choice_templates(rc_cls, rc_cls_id)
        rc_level_row = catalog.class_level_row(rc_cls_id, rc_level)
        rc["level_row"] = rc_level_row
        feature_refs = _cumulative_feature_refs(catalog, rc_cls_id, rc_subclass_id, rc_level)
        rc_fs_slots = fs_slots_by_class.get(rc["index"], [])
        choice_templates += _feature_choice_templates(
            catalog, rc_cls_id, rc_cls["name"], feature_refs, rc_subclass_id, class_level=rc_level,
            skip_features={idx for _cid, _lvl, idx in rc_fs_slots} | class_choices_2024.replaced_srd_features(catalog, rc_cls_id, ruleset),
            sources=draft.get("sources"), class_choices=rc_class_choices,
        )
        choice_templates += class_choices_2024.expertise_templates(catalog, rc, ruleset)  # C6b-1
        choice_templates += class_choices_2024.language_templates(catalog, rc, ruleset)  # C6b-2
        choice_templates += class_choices_2024.primal_knowledge_templates(catalog, rc, ruleset)  # C6b-2
        choice_templates += class_choices_2024.subclass_pick_templates(catalog, rc, ruleset)  # RP12
        choice_templates += subclass_options_2024.templates(catalog, rc, ruleset)  # RP13
        choice_templates += class_choices_2024.metamagic_templates(catalog, rc, ruleset)  # C6c-1
        choice_templates += class_choices_2024.invocation_templates(catalog, rc, ruleset)  # C7a
        for tpl in choice_templates:  # G1: SRD style options already held (feat or earlier SRD style)
            held_names = fs_taken_by_cid.get(tpl["id"])
            if held_names and any(tpl["id"] == c for c, _l, _i in srd_fs_slots_by_class.get(rc["index"], [])):
                names = _srd_style_options(catalog, tpl["id"].rsplit(":", 1)[1])
                for opt in tpl["options"]:
                    label = held_names.get("name:" + names.get(opt["id"], "\0"))
                    if label is not None:
                        opt["disabled"] = True
                        opt["disabledReason"] = msg("disabled-already-taken-from", where=label)
        choice_templates += _fighting_style_templates(  # C3
            catalog, rc, rc_fs_slots, draft.get("sources"), ruleset, total_level, final_scores, use_feat_prereqs, held,
            fs_taken_by_cid,
        )
        choice_templates += _lessons_templates(  # C7c
            catalog, rc, lessons_slots_by_class.get(rc["index"], []), draft.get("sources"), ruleset, total_level, final_scores,
            use_feat_prereqs, held, lessons_resolver.taken_by_cid, lessons_resolver.picked)
        for lessons_feat in lessons_feats:  # the Origin feat's own choices under its origin
            if lessons_feat["_asi_origin"].startswith(f"class:{rc_cls_id}:") and lessons_feat.get("_ea_asi_cid") not in rc_blocked_feat_cids:
                choice_templates += _feat_choice_templates([lessons_feat], origin=lessons_feat["_asi_origin"], items=catalog.items, catalog=catalog, ruleset=ruleset)
                choice_templates += _feat_spell_choice_templates(
                    [lessons_feat], catalog, origin=lessons_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
                )
        for fs_feat in fs_feats:  # cascaded choices (Blessed / Druidic Warrior cantrips) under the pick's origin
            if fs_feat["_asi_origin"].startswith(f"class:{rc_cls_id}:"):
                choice_templates += _feat_choice_templates([fs_feat], origin=fs_feat["_asi_origin"], items=catalog.items, catalog=catalog, ruleset=ruleset)
                choice_templates += _feat_spell_choice_templates(
                    [fs_feat], catalog, origin=fs_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
                )
        choice_templates += _asi_choice_templates(
            rc_cls_id, rc_cls["name"], rc_asi_levels, rc_asi_scores_by_level, catalog, total_level, use_feat_prereqs,
            draft.get("sources"),
            taken_by_level={lvl: asi_taken_before_cid.get(f"class:{rc_cls_id}:{lvl}:asi", {}) for lvl in rc_asi_levels},
            held_by_level=rc_held_by_level, ruleset=ruleset, class_choices=rc_class_choices,
        )
        # ASI-or-feat Task 3: a feat THIS class took at one of its own ASI
        # levels cascades its own choice-shaped content right here, scoped
        # under that feat's `_asi_origin` (Task 1's `origin` param, one feat
        # per call as that param requires). The selections live in this
        # class's own `class_choices`, already merged into `all_selections`
        # below; the generic "feat"-kind merge sites (skills, tools,
        # languages) pick them up by source.kind + cid substring unchanged.
        # The ability-bonus template's selection was already applied via
        # _resolve_asi_selected_feats/_apply_asi_progression above — it's
        # built again here (same function, same cid) only to be shown. A
        # prerequisite-blocked pick cascades nothing: it isn't applied.
        for asi_feat in asi_feat_picks:
            if asi_feat["_asi_cid"] in rc_blocked_feat_cids:
                continue
            if asi_feat["_asi_origin"].startswith(f"class:{rc_cls_id}:"):
                asi_feat_templates = _feat_choice_templates([asi_feat], origin=asi_feat["_asi_origin"], items=catalog.items, catalog=catalog, ruleset=ruleset)
                choice_templates += asi_feat_templates
                ea_card = next((t for t in asi_feat_templates if t["id"] == asi_feat["_asi_origin"] + ":invocation"), None)
                if ea_card:  # RP20: Eldritch Adept's Lessons of the First Ones has an Origin-feat card
                    choice_templates += _feat_lessons_templates(
                        catalog, rc, ea_lessons, asi_feat, ea_card["source"], draft.get("sources"), ruleset, total_level, final_scores,
                        use_feat_prereqs, held)
                choice_templates += _feat_spell_choice_templates(
                    [asi_feat], catalog, origin=asi_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
                )
                choice_templates += [  # FE2: options at the feat's cap read this level's running scores
                    tpl for tpl, _ in _feat_ability_bonus_choice_templates(
                        [asi_feat], origin=asi_feat["_asi_origin"],
                        scores=rc_asi_scores_by_level.get(asi_feat["_asi_level"], {}),
                    )
                ]

    asi_selected_feats = [f for f in asi_feat_picks if f["_asi_cid"] not in prerequisite_blocked_asi_feat_cids]
    lessons_feats = [f for f in lessons_feats if f.get("_ea_asi_cid") not in prerequisite_blocked_asi_feat_cids]  # RP20
    resolved_feats = background_feats + species_feats + fs_feats + lessons_feats + asi_selected_feats

    use_prereqs = bool(use_prerequisites_prefs.get("multiclass"))
    problems += _multiclass_prerequisite_problems(resolved_classes, final_scores, use_prereqs)
    # Phase 4c-i Task 6: a NEW sibling key on the SAME usePrerequisites
    # dict the multiclass toggle already uses (`use_prerequisites_prefs`,
    # read once before the per-class loop above so _asi_choice_templates
    # could also use it via `use_feat_prereqs`) — not a separate
    # preferences shape. `final_scores` here is already POST-ASI-progression
    # (the loop above reassigns it via _apply_asi_progression before this
    # line runs), matching what a player's actual final character sheet
    # shows.
    #
    # Task 4 (ASI-or-feat): passes ONLY the background-side dict built
    # above (background_chosen_ability_deltas_by_instance, keyed by bare
    # `feat:{index}`) — nothing ASI-derived is merged in here (fix round
    # 1). An ASI-selected feat's own prerequisite is already checked
    # earlier, inside _apply_asi_progression's per-level gate (Task 3),
    # against that level's own running scores with the pick's own delta
    # excluded by construction (the gate runs BEFORE that delta is
    # applied) — a pick that fails that gate is filtered out of
    # `resolved_feats` entirely and never reaches this call. So an
    # ASI-origin feat here has ALREADY had its own bonus's influence on
    # its own prerequisite correctly excluded; re-subtracting it a second
    # time via this parameter would be redundant at best (the delta WAS
    # applied, so it's already legitimately excluded by the gate's own
    # scores) and wrong at worst (if the delta was cap-skipped by
    # asi_exceeds_cap — the feat still granted, but that specific
    # increase never applied — subtracting a delta that was never added
    # to `final_scores` produces a false "prerequisite unmet"). Only a
    # background-granted feat needs the explicit subtraction this
    # function does, since it has no equivalent per-level gate.
    # FE2: the fixed increase to subtract is the one that was APPLIED (clamped for an origin feat, skipped
    # for an ASI feat at its cap), never the raw one.
    for skipped_cid in cap_skipped_asi_feat_cids:
        applied_fixed_deltas_by_instance[_feat_instance_key(asi_feats_by_cid[skipped_cid])] = []
        skipped_feat = asi_feats_by_cid[skipped_cid]
        if _feat_ability_bonuses([skipped_feat]):  # FX7: a fixed increase was dropped at the cap (the chosen card says so itself)
            fixed_names = ", ".join(_feat_ability_bonuses([skipped_feat]))
            fixed_clamped_notes.append({
                "choiceId": skipped_cid,
                "reason": msg("pruned-ability-at-max", name=skipped_feat["name"], ab=fixed_names,
                              cap=_feat_ability_cap(skipped_feat))})
        fixed_abs = set(_feat_ability_bonuses([skipped_feat]))
        lost_choice = [ab for ab, _ in asi_feat_deltas_by_cid.get(skipped_cid, []) if ab not in fixed_abs]
        if lost_choice:  # VF1.3: the chosen +1 of a feat whose every ability is at the cap is lost (the feat is still taken)
            fixed_clamped_notes.append({
                "choiceId": f"{skipped_feat['_asi_origin']}:ability-bonus",
                "reason": msg("pruned-ability-at-max", name=skipped_feat["name"], ab=", ".join(lost_choice),
                              cap=_feat_ability_cap(skipped_feat))})
    problems += _feat_prerequisite_problems(
        resolved_feats, total_level, final_scores, use_feat_prereqs, background_chosen_ability_deltas_by_instance,
        applied_fixed_deltas_by_instance,
    )

    # Primal Champion et al.: fixed ability-score feature bonuses, applied
    # after ASIs and prerequisite checks (the 24 cap is theirs alone).
    # RP2: under 2024 the XPHB fixed-effect table (Body and Mind, Primal Champion cap 25, ...) joins the SRD one.
    xphb_effects = features_mod.xphb_effects_2024(catalog, resolved_classes, ruleset)
    ability_effects = features_mod.class_effects(_class_feature_list(catalog, resolved_classes), xphb_effects)
    pruned_ability_notes = features_mod.ability_bonus_losses(final_scores, ability_effects)
    final_scores = features_mod.apply_ability_bonuses(final_scores, ability_effects)
    modifiers = derived_mod.ability_modifiers(final_scores)
    # Prof bonus is confirmed class-agnostic at a given level (per the
    # design spec's empirical check), so any resolved class's level table
    # can be used to look it up — but it must be looked up at TOTAL level
    # (summed across every class), not any single class's own level.
    # `total_level` here reuses the SAME variable computed above (from
    # resolved_classes' clamped/validated levels) for the
    # total-level-exceeded check.
    prof_bonus_lookup_cls_id = next((rc["cls_id"] for rc in resolved_classes if rc["cls"]), None)
    prof_bonus_row = catalog.class_level_row(prof_bonus_lookup_cls_id, total_level) if prof_bonus_lookup_cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2
    rs.asi_selected_feats = asi_selected_feats
    rs.choice_templates = choice_templates
    rs.final_scores = final_scores
    rs.lessons_feats = lessons_feats
    rs.modifiers = modifiers
    rs.problems = problems
    rs.prof_bonus = prof_bonus
    rs.pruned_ability_notes = pruned_ability_notes
    rs.resolved_feats = resolved_feats
    rs.xphb_effects = xphb_effects


def _pass_spell_and_choice_templates(rs: ResolveState) -> None:
    """Spell choices per class and the remaining choice templates (background, species, class, equipment)."""
    _origin_choices_raw = rs._origin_choices_raw
    background_ability_choice_tpl = rs.background_ability_choice_tpl
    background_dict = rs.background_dict
    background_feats = rs.background_feats
    bg = rs.bg
    bg_id = rs.bg_id
    catalog = rs.catalog
    choice_templates = rs.choice_templates
    cls = rs.cls
    cls_id = rs.cls_id
    draft = rs.draft
    feat_ability_choice_tpls = rs.feat_ability_choice_tpls
    modifiers = rs.modifiers
    primary = rs.primary
    problems = rs.problems
    race = rs.race
    race_id = rs.race_id
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    species_ability_choice_tpl = rs.species_ability_choice_tpl
    species_choices_raw = rs.species_choices_raw
    species_feat_ability_tpls = rs.species_feat_ability_tpls
    species_feat_templates = rs.species_feat_templates
    species_feats = rs.species_feats
    species_variant = rs.species_variant
    subrace = rs.subrace
    total_level = rs.total_level
    variant_follow = rs.variant_follow
    warnings = rs.warnings
    # Spell choices need `modifiers` (for spellcasting-ability-driven known-
    # spell counts), which isn't final until EVERY class's ASI progression
    # has run — hence this is a SECOND loop over resolved_classes, not
    # merged into the loop above.
    warlock_spell_ctx: tuple[list[str], set[str]] | None = None  # RP20: (known cantrips, spells the Warlock owns) for Eldritch Adept
    for rc in resolved_classes:
        rc_cls, rc_cls_id, rc_level, rc_level_row = rc["cls"], rc["cls_id"], rc["level"], rc.get("level_row")
        if not (rc_cls and rc_cls_id):
            continue
        choice_templates += _mystic_arcanum_templates(catalog, rc, draft.get("sources"), ruleset, rc["class_choices"])
        choice_templates += _weapon_mastery_template(catalog, rc, ruleset)
        choice_templates += class_choices_2024.class_option_templates(catalog, rc, ruleset)  # C6a / C6c-2
        caster = _effective_caster(catalog, rc, ruleset)
        if caster:
            spell_ability, spell_dict, list_class_id = caster
            extra_cantrips = class_choices_2024.class_option_extra_cantrips(catalog, rc, ruleset)  # C6a Thaumaturge / Magician
            extra_cantrips += class_choices_2024.subclass_extra_cantrips(catalog, rc, ruleset)  # VF7.2 2014 Circle of the Land
            if extra_cantrips and spell_dict.get("cantrips_known", 0) > 0:
                spell_dict = {**spell_dict, "cantrips_known": spell_dict["cantrips_known"] + extra_cantrips}
            raw_feature_ids = {
                sel for cid, sels in rc["class_choices"].items() if ":feature:" in cid and isinstance(sels, list)
                for sel in sels if isinstance(sel, str)
            }
            sub_name = rc["subclass"]["name"] if rc["subclass"] else ""
            # C6d (2024): class always-prepared spells (Ranger Hunter's Mark, ...) and Bard Magical Secrets
            class_always = class_choices_2024.always_prepared_class_spells(catalog, rc_cls_id, rc_level, rc_cls["name"], ruleset)
            secrets_ids = [
                o["item"]["index"] for flt in class_choices_2024.magical_secrets_filters(
                    catalog, rc_cls_id, rc_level, _highest_spell_slot_level(spell_dict), ruleset)
                for o in _spell_filter_options(
                    catalog, flt, draft.get("sources"), ruleset,
                    {x for x in (rc["class_choices"].get(f"class:{rc_cls_id}:spells-known") or []) if isinstance(x, str)})
            ]
            land_variant = subclass_options_2024.picked_variant(catalog, rc, rc["class_choices"])  # RP17 Circle of the Land
            sub_always = {sid: f"{sub_name}" for sid in
                          _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "always", land_variant, ruleset)}
            options_fn = lambda flt, keep: _spell_filter_options(catalog, flt, draft.get("sources"), ruleset, keep)  # noqa: E731
            if subclass_spells_2024.improved_illusions_applies(catalog, rc, ruleset):
                # RP17: a Minor Illusion pick on the Cantrips card is allowed (Improved Illusions then adds a cantrip);
                # unpicked, the subclass grant keeps listing it
                for sid in subclass_spells_2024.minor_illusion_ids(catalog):
                    sub_always.pop(sid, None)
                tpl_ = subclass_spells_2024.cantrip_template(catalog, rc, ruleset, options_fn, rc["class_choices"])
                if tpl_:
                    choice_templates.append(tpl_)
            discoveries_tpl, discoveries_always = subclass_spells_2024.discoveries_template(  # RP17 Lore Bard 6
                catalog, rc, ruleset, _highest_spell_slot_level(spell_dict), {**class_always, **sub_always}, options_fn,
                rc["class_choices"])
            if discoveries_tpl:
                choice_templates.append(discoveries_tpl)
            spell_templates = _spell_choice_templates(
                catalog, rc_cls, rc_cls_id, {"spellcasting": spell_dict}, modifiers[spell_ability], class_level=rc_level,
                expanded_spell_ids=_subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "expanded")
                + secrets_ids,
                always_prepared={**class_always, **sub_always, **discoveries_always},
                subclass_id=rc["subclass_id"],
                sources=draft.get("sources"), ruleset=ruleset, class_choices=rc["class_choices"],
                list_class_id=list_class_id,
                school_limit=SUBCLASS_SPELL_SCHOOL_LIMITS.get(rc["subclass_id"] or "") if list_class_id != rc_cls_id else None,
                problems_out=problems,
                secrets_cap=class_choices_2024.magical_secrets_cap_2014(catalog, rc_cls_id, rc_level, ruleset),
                mark_ids=_feat_mark_spell_ids(catalog, resolved_feats, _highest_spell_slot_level(spell_dict)),
            )
            class_choices_2024.label_magical_secrets(catalog, spell_templates, rc_cls_id, rc_level, ruleset)
            choice_templates += spell_templates
            choice_templates += _additional_secrets_templates(  # RPX1: SRD Lore Bard 6
                catalog, rc, spell_dict, draft.get("sources"), ruleset, rc["class_choices"].get(class_choices_2024.additional_secrets_cid(catalog)))
            if rc_cls_id == "warlock":  # C7c: target cantrips, Pact of the Tome, pact weapon
                kept_tome = {x for cid_ in (class_choices_2024.dependent_cid(class_choices_2024.TOME_ID, k) for k in ("cantrips", "rituals"))
                             for x in (rc["class_choices"].get(cid_) if isinstance(rc["class_choices"].get(cid_), list) else [])
                             if isinstance(x, str)}
                owned_spells = set(class_always) | set(
                    _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "always", ruleset=ruleset))
                choice_templates += class_choices_2024.invocation_dependent_templates(
                    catalog, rc, ruleset, spell_templates,
                    lambda flt: _spell_filter_options(catalog, flt, draft.get("sources"), ruleset, kept_tome), owned_spells)
                known_, prepared_ = class_choices_2024.warlock_spell_picks(spell_templates, rc["class_choices"])
                warlock_spell_ctx = (known_, owned_spells | set(known_) | set(prepared_))

    asi_levels = primary.get("asi_levels", []) if primary else []
    level_row = primary.get("level_row") if primary else None
    if bg and bg_id:
        choice_templates += _background_choice_templates(bg, bg_id)
        choice_templates += class_choices_2024.origin_language_templates(bg, bg_id, ruleset)  # C8
        if background_ability_choice_tpl:
            choice_templates.append(background_ability_choice_tpl)
    # Phase 4c-ii Task 1: `resolved_feats` is already computed above (right
    # after `bg` itself is resolved) regardless of whether `bg` is present —
    # it defaults to `[]` when there's no background, so this call is a
    # safe no-op in that case, not gated behind `if bg and bg_id` like the
    # background-choice-templates call just above.
    choice_templates += _feat_spell_choice_templates(
        background_feats, catalog,
        raw_selections=background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {},
        variant_hints=(bg.get("feat_variant_hints") if bg else None) or {},
        total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
    )
    choice_templates += _feat_choice_templates(background_feats, items=catalog.items, catalog=catalog, ruleset=ruleset)  # ASI-selected feats' templates: built origin-scoped in the per-class loop
    # Phase 4c-ii Task 2: `feat_ability_choice_tpls` was already built (and
    # applied to `feat_bonuses`) EARLY, in the "Final ability scores"
    # section above — appended here, unconditionally, mirroring exactly how
    # background_ability_choice_tpl/species_ability_choice_tpl (also built
    # early) get appended to choice_templates at their own call sites,
    # rather than rebuilding the templates a second time here.
    choice_templates += feat_ability_choice_tpls
    for species_tpl in species_feat_templates:
        choice_templates.append(species_tpl)
    for species_feat in species_feats:
        origin = species_feat["_species_origin"]
        choice_templates += _feat_choice_templates([species_feat], origin=origin, items=catalog.items, catalog=catalog, ruleset=ruleset)
        choice_templates += _feat_spell_choice_templates(
            [species_feat], catalog, origin=origin, raw_selections=_origin_choices_raw(species_feat), total_level=total_level,
            sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
        )
    choice_templates += species_feat_ability_tpls
    if race and race_id:
        species_variant_tpl = _species_variant_template(race, race_id)
        if species_variant_tpl:
            choice_templates.append(species_variant_tpl)
        species_size_tpl = _species_size_template(race, race_id)
        if species_size_tpl:
            choice_templates.append(species_size_tpl)
        for species_spell_tpl in (_species_cantrip_template(race, subrace, catalog, race_id),  # F1
                                  _species_spell_ability_template(race, subrace, catalog, species_variant, race_id)):
            if species_spell_tpl:
                choice_templates.append(species_spell_tpl)
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace, species_variant)
        draconic_tpl = _species_draconic_ancestry_template(race, race_id, subrace, species_choices_raw)  # B1
        if draconic_tpl:
            choice_templates.append(draconic_tpl)
        if species_ability_choice_tpl:
            choice_templates.append(species_ability_choice_tpl)
    equipment_dependents: dict[str, dict[str, list[dict]]] = {}
    if cls and cls_id:
        cls_equipment_templates, cls_dropped, cls_dependents = _equipment_choice_templates(
            cls, "class", cls_id, cls["name"], catalog.items)
        equipment_dependents.update(cls_dependents)
        choice_templates += cls_equipment_templates
        if cls_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-class-{cls_id}",
                "message": msg("equipment-envelope-dropped", name=cls["name"], n=cls_dropped),
            })
    if bg and bg_id:
        # RP9 (C, E12): under ruleset 2024 the 2024 envelope (real items and quantities) replaces the old one; the cid
        # and the A/B structure are the same
        bg_equipment_src = bg
        if ruleset == "2024" and bg.get("starting_equipment_options_2024"):
            bg_equipment_src = {**bg, "starting_equipment_options": bg["starting_equipment_options_2024"]}
        bg_equipment_templates, bg_dropped, bg_dependents = _equipment_choice_templates(
            bg_equipment_src, "background", bg_id, bg["name"], catalog.items)
        equipment_dependents.update(bg_dependents)
        choice_templates += bg_equipment_templates
        if bg_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-background-{bg_id}",
                "message": msg("equipment-envelope-dropped", name=bg["name"], n=bg_dropped),
            })

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)
    _apply_species_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], race, subrace, catalog)
    rs.choice_templates = choice_templates
    rs.equipment_dependents = equipment_dependents
    rs.warlock_spell_ctx = warlock_spell_ctx


def _pass_collect_choices(rs: ResolveState) -> None:
    """Selections, dependents, stale picks and the resolved choices."""
    background_clamped_notes = rs.background_clamped_notes
    background_dict = rs.background_dict
    catalog = rs.catalog
    choice_templates = rs.choice_templates
    draft = rs.draft
    either_or_defaults = rs.either_or_defaults
    equipment_dependents = rs.equipment_dependents
    fixed_clamped_notes = rs.fixed_clamped_notes
    problems = rs.problems
    pruned_ability_notes = rs.pruned_ability_notes
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    species = rs.species
    subclass_pruned = rs.subclass_pruned
    warlock_spell_ctx = rs.warlock_spell_ctx
    # Apply the draft's own selections onto each template to get a real Choice.
    equipment_raw = draft.get("equipment")
    equipment_dict = equipment_raw if isinstance(equipment_raw, dict) else {}
    equipment_choices_raw = equipment_raw.get("choices") if isinstance(equipment_raw, dict) else None
    if equipment_choices_raw is not None and not isinstance(equipment_choices_raw, dict):
        problems.append({"id": "malformed-equipment-choices", "message": msg("malformed-equipment-choices")})
        equipment_choices_raw = None

    details = _sanitized_details(draft.get("details"))

    all_selections: dict[str, list[str]] = {}
    # Every class's own choice ids are scoped by cls_id (e.g.
    # "class:fighter:..." vs "class:wizard:...") and never collide across
    # two different classes' choice sets, so merging every resolved
    # class's submitted choices here (not just the primary/classes[0]'s)
    # is safe — and necessary, since the generic choice-resolution loop
    # below reads selections only from this dict.
    for rc in resolved_classes:
        all_selections.update(rc["class_choices"])
    all_selections.update(background_dict.get("choices") or {})
    all_selections.update(species.get("choices") or {})
    all_selections.update(equipment_choices_raw or {})
    all_selections.update(either_or_defaults)  # F1: the default is shown as the card's selection (the draft is not touched)

    # RP20 (A3b): the dependents of an Eldritch Adept pick (target cantrips, Pact of the Tome, Pact of the Blade) under
    # ruleset 2024: the C7c builders with the feat card as the holder. Built here because every feat card exists now
    # and the target options are the Warlock's known cantrips.
    warlock_level = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == "warlock" and rc["cls"]), 0)
    feat_inv_holders = class_choices_2024.feat_invocation_holders(catalog, choice_templates, all_selections, warlock_level, ruleset)
    if feat_inv_holders:
        known_cantrips, owned_by_warlock = warlock_spell_ctx or ([], set())
        choice_templates += class_choices_2024.feat_dependent_templates(
            catalog, feat_inv_holders, known_cantrips, owned_by_warlock,
            lambda flt, kept: _spell_filter_options(catalog, flt, draft.get("sources"), ruleset, kept))

    # A selection stored in the Draft for a choice id that no longer
    # exists among the CURRENTLY reachable choice_templates (because the
    # player leveled down or cleared a subclass selection) is stale — it
    # was never deleted from the Draft (the architecture deliberately
    # never mutates the Draft — see Phase 3a design spec §7), so it just
    # silently stopped being read. This is the first time anything
    # surfaces that to the player instead of leaving it invisible.
    # (SET_SPECIES/SET_SUBSPECIES/SET_BACKGROUND/SET_CLASS all reset
    # `choices: {}` in the frontend reducer, so a species/background/
    # primary-class change can never itself leave a stale selection
    # behind — those paths never reach here.)
    # Nested starting-equipment picks (e.g. the martial weapon in "a martial
    # weapon and a shield") only exist once their parent option is selected.
    if equipment_dependents:
        expanded_templates = []
        for tpl in choice_templates:
            expanded_templates.append(tpl)
            option_deps = equipment_dependents.get(tpl["id"])
            if option_deps:
                parent_valid = {o["id"] for o in tpl["options"]}
                raw_parent = all_selections.get(tpl["id"])
                raw_parent = raw_parent if isinstance(raw_parent, list) else []
                parent_selected = [s for s in dict.fromkeys(raw_parent) if isinstance(s, str) and s in parent_valid]
                for option_id in parent_selected[: tpl["count"]]:
                    expanded_templates.extend(option_deps.get(option_id, []))
        choice_templates = expanded_templates
    # RP5: a feat that reuses another held feat's spellcasting ability has no ability card of its own; a stored pick on it
    # becomes a non-blocking `pruned` entry through the stale-selection pass below.
    held_feat_indexes = {f["index"] for f in resolved_feats}
    no_own_ability_card = {
        f"{_feat_cid_prefix(f)}:spell-ability" for f in resolved_feats
        if feat_effects_mod.ability_from(feat_effects_data.FEAT_EFFECTS.get(f["index"])) in held_feat_indexes}
    if no_own_ability_card:
        choice_templates = [tpl for tpl in choice_templates if tpl["id"] not in no_own_ability_card]
    current_template_ids = {tpl["id"] for tpl in choice_templates}
    pruned = subclass_pruned + [
        {"choiceId": choice_id, "reason": msg("pruned-stale", id=choice_id)}
        for choice_id, selected in all_selections.items()
        if selected and choice_id not in current_template_ids
    ]
    pruned += background_clamped_notes + fixed_clamped_notes + pruned_ability_notes
    # A stored feat pick at an ASI slot that is not among that slot's options
    # (structurally ineligible there, e.g. an Epic Boon below level 19) is
    # ignored; say so instead of leaving the card silently pending.
    template_option_ids = {tpl["id"]: {o["id"] for o in tpl["options"]} for tpl in choice_templates if _ASI_CID_RE.match(tpl["id"])}
    for choice_id, option_ids in template_option_ids.items():
        stored = all_selections.get(choice_id)
        if not isinstance(stored, list):
            continue
        for item in dict.fromkeys(s for s in stored if isinstance(s, str) and s.startswith("feat:")):
            if item not in option_ids:
                feat_record = catalog.feats.get(item[len("feat:"):])
                name = feat_record["name"] if feat_record else item
                pruned.append({
                    "choiceId": choice_id,
                    "reason": msg("pruned-asi-feat-ineligible", name=name),
                })
    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        # Dedupe (preserving first-occurrence order) so this generic pass
        # agrees with the early species-ability-bonus pass above, which
        # dedupes the same underlying selection before applying bonuses.
        raw_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        if tpl.get("granted"):
            # Granted automatically (e.g. Elemental Attunement): an old stored
            # pick of it is redundant, not a loss, so it is dropped silently.
            granted = {g["id"] for g in tpl["granted"]}
            raw_selected = [s for s in raw_selected if s not in granted]
        selected = [s for s in raw_selected if s in valid_ids]
        if _is_count_variable_choice(tpl):
            # A spellcaster's allowed count shrinks on level-down (or when
            # the casting modifier drops) while the choice id stays the
            # same, and spells above the class's highest slot level stop
            # being offered — both leave stale selections in the Draft.
            # Report them as non-blocking `pruned` entries (keep the first
            # `count` valid selections), not an over-selected problem.
            if not _is_mastery_choice(tpl) and not class_choices_2024.is_invocation_card_2024(tpl):
                # F1: mastery truncates after the proficiency gate; F3a-9: the 2024 invocation card after its prerequisite gate
                selected = selected[: tpl["count"]]
            dropped = [s for s in raw_selected if s not in selected]
            if dropped:
                names = [_stale_pick_name(catalog, d, feats=False) for d in dropped]  # VF7.7c
                if _is_mastery_choice(tpl):  # F1: here only options the class filter / catalog no longer offers
                    if tpl["source"]["kind"] == "class":
                        reason = msg("pruned-mastery-unavailable-class", label=tpl["label"], names=names)
                    else:
                        reason = msg("pruned-mastery-unavailable-feat", label=tpl["label"], names=names)
                elif class_choices_2024.is_dependent_choice(tpl):
                    names = [
                        (catalog.spells.get(d) or catalog.items.get(d) or catalog.feats.get(d[len("feat:"):]) or {}).get("name", d)
                        for d in dropped]  # C7c
                    reason = msg("pruned-no-longer-available", label=tpl["label"], names=names)
                else:
                    reason = msg("pruned-count-overflow", id=tpl["id"], count=tpl["count"], n=len(dropped), names=names)
                    if tpl["id"] == "class:wizard:spells-known":
                        # F2-B: the prepared card offers only spellbook spells, so a pick the
                        # card no longer offers is missing from the book, not over the count.
                        outside = [d for d in dropped if d not in valid_ids]
                        if outside:
                            outside_names = [(catalog.spells.get(d) or {}).get("name", d) for d in outside]
                            rest = [d for d in dropped if d in valid_ids]
                            if rest:
                                rest_names = [(catalog.spells.get(d) or {}).get("name", d) for d in rest]
                                reason = msg("pruned-wizard-not-in-spellbook-and-over", id=tpl["id"], n=len(outside),
                                             names=outside_names, m=len(rest), count=tpl["count"], rest=rest_names)
                            else:
                                reason = msg("pruned-wizard-not-in-spellbook", id=tpl["id"], n=len(outside), names=outside_names)
                pruned.append({"choiceId": tpl["id"], "reason": reason})
        else:
            # F3a-1: a stored pick the card does not offer at all (e.g. a 2014 equipment bundle after switching to
            # the 2024 packages, which reuse the cid) is reported instead of vanishing. ASI feat picks have their
            # own entry above.
            offered = {o["id"] for o in tpl["options"]}
            gone = [s for s in raw_selected if s not in offered
                    and not (s.startswith("feat:") and _ASI_CID_RE.match(tpl["id"]))]
            if gone:
                def _pick_name(pick):
                    if "+" in pick:  # VF7.7c: a bundle; the parts stay tagged so Bulgarian shows their labels
                        return msg("label-pick-join", parts=[_stale_pick_name(catalog, p) for p in pick.split("+")])
                    return _stale_pick_name(catalog, pick)
                pruned.append({
                    "choiceId": tpl["id"],
                    "reason": msg("pruned-no-longer-offered", label=tpl["label"], names=[_pick_name(g) for g in gone]),
                })
            if tpl["source"]["kind"] == "class" and _ASI_CID_RE.match(tpl["id"]):
                # RPF: a stored ASI pick whose option is offered but disabled (cap 20 after a ruleset / species switch,
                # a feat prerequisite) is reported with the option's own reason instead of leaving the card pending silently.
                for o in tpl["options"]:
                    if o.get("disabled") and o["id"] in raw_selected:
                        pruned.append({"choiceId": tpl["id"], "reason": msg(
                            "pruned-asi-option-closed", label=tpl["label"], option=o["label"],
                            why=o.get("disabledReason", msg("disabled-not-available")))})
            if tpl["source"]["kind"] == "feat" and tpl["id"].endswith(":ability-bonus"):
                # FE2 (B9): a stored pick of an option closed by the feat's ability cap is reported, not lost silently.
                closed = [o for o in tpl["options"] if o.get("disabled") and o["id"] in raw_selected]
                if closed:
                    pruned.append({
                        "choiceId": tpl["id"],
                        "reason": msg("pruned-ability-closed", label=tpl["label"], items=[
                            msg("pruned-ability-closed-item", ab=o["id"].upper(), why=o.get("disabledReason", msg("disabled-not-available")))
                            for o in closed]),
                    })
            if len(selected) > tpl["count"]:
                problems.append({
                    "id": f"over-selected-{tpl['id']}",
                    "message": msg("over-selected", label=tpl["label"], count=tpl["count"], submitted=len(selected)),
                })
                selected = selected[: tpl["count"]]
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})
    rs.choices = choices
    rs.details = details
    rs.equipment_dict = equipment_dict
    rs.pruned = pruned


def _pass_equipment_and_spells(rs: ResolveState) -> None:
    """Added items, gear, gold, spell summaries, slots, inventory and worn items."""
    bg = rs.bg
    bg_id = rs.bg_id
    catalog = rs.catalog
    choices = rs.choices
    cls = rs.cls
    equipment_dict = rs.equipment_dict
    modifiers = rs.modifiers
    problems = rs.problems
    prof_bonus = rs.prof_bonus
    pruned = rs.pruned
    race = rs.race
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    species_alt = rs.species_alt
    species_spell_ability = rs.species_spell_ability
    species_variant = rs.species_variant
    subrace = rs.subrace
    variant_follow = rs.variant_follow
    warnings = rs.warnings
    added_raw = equipment_dict.get("added")
    if added_raw is None:
        added_raw = []
    elif not isinstance(added_raw, list):
        problems.append({"id": "malformed-equipment-added", "message": msg("malformed-equipment-added")})
        added_raw = []

    added_resolved = []
    for entry_index, entry in enumerate(added_raw):
        if not isinstance(entry, dict):
            continue
        item_id = entry.get("itemId")
        item = catalog.items.get(item_id) if isinstance(item_id, str) else None
        if not item:
            # VF1.9: an unknown item id (a typo, or an item of a book the catalog lacks) was dropped without a word
            warnings.append({"id": f"equipment-unknown-item-{entry_index}",
                             "message": msg("equipment-unknown-item", item=str(item_id))})
            continue
        added_resolved.append({
            "itemId": item_id, "name": item["name"],
            "qty": entry.get("qty", 1), "equipped": bool(entry.get("equipped", False)),
        })

    equipment_choices = [c for c in choices if c["source"]["kind"] == "equipment"]
    equipped_items = _gather_equipped_items(equipment_choices, added_raw if isinstance(added_raw, list) else [], catalog.items)
    monk_tool = _monk_tool_pick(choices)  # C9b
    background_tool = _background_tool_pick(choices, bg_id, catalog.items) if bg else None  # RP9
    chosen_equipment = _chosen_equipment(equipment_choices, catalog.items, monk_tool, background_tool)

    # starting_gold is SRD's own fixed per-background field, shape
    # {"quantity": N, "unit": "gp"} (confirmed against the bundled SRD
    # Backgrounds file) — present on every SRD/official background but,
    # until now, never read anywhere. A selected gp-{amount} bundle member
    # (see _selected_gold_and_narrative_items) adds on top of it rather
    # than replacing it, since a background can offer BOTH (e.g. SRD's own
    # Acolyte grants a fixed 15 gp with no equipment-choice gold at all,
    # while an official background's own bundle may carry gold only in the
    # selectable option, with its fixed field left None).
    fixed_gold = (bg.get("starting_gold") or {}).get("quantity", 0) if bg else 0
    selected_gold, narrative_items = _selected_gold_and_narrative_items(equipment_choices, monk_tool, background_tool)
    starting_gold = fixed_gold + selected_gold

    # bg["starting_narrative_items"] (Finding 1 of the final whole-branch
    # review, official_source.py's _fixed_starting_equipment_from_5etools)
    # carries the FIXED "_"-keyed list's own flavor/category/no-catalog-
    # match members (e.g. Acolyte/PHB's holy symbol, incense, vestments) —
    # previously narrative_items only ever came from a SELECTED
    # equipment-choice bundle member. Fixed items are prepended so they
    # read as "always granted" ahead of whatever the player separately
    # chose.
    narrative_items = list(bg.get("starting_narrative_items", [])) + narrative_items if bg else narrative_items

    def _spell_summary(sid: str) -> dict | None:
        spell = catalog.spells.get(sid)
        return {"id": sid, "name": spell["name"], "level": spell["level"]} if spell else None

    def _spell_summaries(choice: dict | None) -> list[dict]:
        if not choice:
            return []
        return [
            {"id": sid, "name": catalog.spells[sid]["name"], "level": catalog.spells[sid]["level"]}
            for sid in choice["selected"] if sid in catalog.spells
        ]

    # sheet["spells"] aggregates across EVERY resolved class with
    # spellcasting, not just the primary one — a secondary caster's
    # selections previously never reached the sheet (or any export) because
    # only the primary's cls_id was ever looked up. One entry per class that
    # actually has a cantrip and/or known-spell Choice this level; a
    # non-caster (or a caster below its first spell-granting level)
    # contributes no entry at all, so this stays [] rather than padding out
    # with empty per-class placeholders.
    spells_summary: list[dict] = []
    if ruleset == "2024":  # RP17: Improved Illusions applies only when Minor Illusion is known from another source
        pruned += subclass_spells_2024.gate_improved_illusions(choices, catalog, [
            e["spellId"] for e in (_species_innate_spells(race, subrace, catalog, species_variant, species_alt, species_spell_ability)
                                   + _species_trait_spell_choices(race, subrace, catalog, choices)
                                   + _feat_innate_spells(resolved_feats, catalog, choices, follow_variants=variant_follow)) if e.get("spellId")])
    selections_now = {c["id"]: c["selected"] for c in choices}
    for rc in resolved_classes:
        rc_cls, rc_cls_id = rc["cls"], rc["cls_id"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_cantrip_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-cantrips"), None)
        rc_known_spells_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-known"), None)
        feature_ids = {idx for cid_, lvl_, idx in _class_feature_list(catalog, [rc], choices)}
        always_ids = _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc["level"], feature_ids, "always",
                                         subclass_options_2024.picked_variant(catalog, rc, selections_now), ruleset)
        if ruleset == "2024" and subclass_spells_2024.improved_illusions_applies(catalog, rc, ruleset):
            # RP17: Minor Illusion known elsewhere (the Improved Illusions card exists) is not listed twice
            known_elsewhere = any((found := subclass_spells_2024.spec_for_card(c)) and found[1]["kind"] == "cantrip"
                                  for c in choices)
            if known_elsewhere:
                always_ids = [sid for sid in always_ids if sid not in subclass_spells_2024.minor_illusion_ids(catalog)]
        if rc_cls_id == "bard":  # RP17: Lore 6 Magical Discoveries picks are always prepared
            always_ids = always_ids + [sid for sid in subclass_spells_2024.picked_spells(choices, "discoveries")
                                       if sid not in always_ids]
        # C6d (2024): class grants (Hunter's Mark, ...) and the Wizard's Spell Mastery / Signature picks
        always_ids = always_ids + [
            sid for sid in class_choices_2024.always_prepared_class_spells(catalog, rc_cls_id, rc["level"], "", ruleset)
            if sid not in always_ids]
        wizard_pick_keys: dict[str, list[dict]] = {}
        if rc_cls_id == "wizard":  # C6d (2024) / RP15 (SRD Spell Mastery, not always prepared)
            for slug_, spec in wizard_spell_picks(ruleset).items():
                card = next((c for c in choices if c["id"] == class_choices_2024.spell_pick_cid(slug_, spec)), None)
                if card:
                    wizard_pick_keys.setdefault(spec["sheet_key"], []).extend(_spell_summaries(card))
                    if spec.get("always_prepared", True):
                        always_ids = always_ids + [s["id"] for s in _spell_summaries(card) if s["id"] not in always_ids]
        if not (rc_cantrip_choice or rc_known_spells_choice or always_ids):
            continue
        rc_caster = _effective_caster(catalog, rc, ruleset)
        rc_spell_ability = (rc_caster[0] if rc_caster else None) or spells_mod.spellcasting_ability(rc_cls) or SUBCLASS_SPELLCASTING_ABILITY.get(rc["subclass_id"] or "")
        rc_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        rc_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        arcanum = []
        if rc_cls_id == "warlock":
            for ch in choices:
                if ":mystic-arcanum-" in ch["id"] and ch["id"].startswith("class:warlock:") and ch["selected"]:
                    spell = catalog.spells.get(ch["selected"][0])
                    if spell:
                        arcanum.append({"level": spell["level"], "id": spell["index"], "name": spell["name"]})
        spells_summary.append({
            "classId": rc_cls_id,
            **({"mysticArcanum": arcanum} if rc_cls_id == "warlock" else {}),
            "cantrips": _spell_summaries(rc_cantrip_choice) + (  # RP17: Improved Illusions (not counted in the cantrips known)
                [s for sid in subclass_spells_2024.picked_spells(choices, "cantrip") if (s := _spell_summary(sid))]
                if rc_cls_id == "wizard" else []),
            "known": _spell_summaries(rc_known_spells_choice) + (  # RPX1: Additional Magical Secrets (not counted in Spells Known)
                _spell_summaries(next((c for c in choices if class_choices_2024.is_additional_secrets_card(c)), None))
                if rc_cls_id == "bard" else []),
            **({"spellbook": _spell_summaries(next((c for c in choices if c["id"] == "class:wizard:spellbook"), None))
                + [s for sid in subclass_spells_2024.picked_spells(choices, "savant") if (s := _spell_summary(sid))]}  # RP17 Savants
               if rc_cls_id == "wizard" else {}),
            **wizard_pick_keys,
            **({"pactOfTheTome": [s for kind in ("cantrips", "rituals") for s in _spell_summaries(
                next((c for c in choices if c["id"] == class_choices_2024.dependent_cid(class_choices_2024.TOME_ID, kind)), None))]}
               if rc_cls_id == "warlock" and any(c["id"] == class_choices_2024.dependent_cid(class_choices_2024.TOME_ID, "cantrips") for c in choices) else {}),
            # Subclass spells (Life domain, oath spells, ...): always
            # prepared, outside the known/prepared limits.
            "alwaysPrepared": [
                {"id": sid, "name": catalog.spells[sid]["name"], "level": catalog.spells[sid]["level"]} for sid in always_ids
            ],
            "spellSaveDC": rc_save_dc,
            "spellAttackBonus": rc_attack_bonus,
        })

    # Spell-slot pools: see spells.spell_slots_for for the single-class vs
    # combined multiclass rule and the separate Warlock Pact Magic pool.
    slot_entries = [(rc["cls_id"], rc["level"], rc["subclass_id"]) for rc in resolved_classes if rc["cls"]]
    spell_slots, warlock_slots = spells_mod.spell_slots_for(catalog, slot_entries, ruleset)
    slot_granting_class_ids = spells_mod.slot_granting_classes(catalog, slot_entries, ruleset)

    granted_equipment = []
    if cls:
        granted_equipment += _fixed_equipment(cls.get("starting_equipment", []), catalog.items)
    if bg:
        granted_equipment += _fixed_equipment(bg.get("starting_equipment", []), catalog.items)

    if ruleset == "2024":  # RP8: pack contents (the pack stays one item) and table weights
        granted_equipment = _with_pack_contents(granted_equipment, catalog.items)
        chosen_equipment = _with_pack_contents(chosen_equipment, catalog.items)
        added_resolved = _with_pack_contents(added_resolved, catalog.items)

    for granted in granted_equipment:
        granted_item = catalog.items.get(granted["itemId"])
        if granted_item:
            equipped_items.append(granted_item)

    # G2: optional worn / wielded model. Absent -> `equipped_items` is untouched.
    inventory: dict[str, dict] = {}
    for entry in granted_equipment + chosen_equipment + added_resolved:
        inv_item = catalog.items.get(entry["itemId"])
        if inv_item:
            slot = inventory.setdefault(entry["itemId"], {"item": inv_item, "qty": 0})
            slot["qty"] += entry.get("qty", 1) if isinstance(entry.get("qty", 1), int) else 1
    # C7c + F3a-2c: the Pact of the Blade weapon is conjured, so it need not be in the inventory; it always gets an
    # attack row, built from the catalog item.
    pact_weapon_id = class_choices_2024.selected_pact_weapon(choices)
    if pact_weapon_id and catalog.items.get(pact_weapon_id) and all(i["index"] != pact_weapon_id for i in equipped_items):
        equipped_items.append(catalog.items[pact_weapon_id])
    gear = worn_mod.apply(equipped_items, equipment_dict, inventory, catalog.items)
    equipped_items = gear.items
    warnings += gear.warnings
    pruned += gear.pruned
    rs.added_resolved = added_resolved
    rs.chosen_equipment = chosen_equipment
    rs.equipped_items = equipped_items
    rs.gear = gear
    rs.granted_equipment = granted_equipment
    rs.narrative_items = narrative_items
    rs.pact_weapon_id = pact_weapon_id
    rs.pruned = pruned
    rs.slot_granting_class_ids = slot_granting_class_ids
    rs.spell_slots = spell_slots
    rs.spells_summary = spells_summary
    rs.starting_gold = starting_gold
    rs.warlock_slots = warlock_slots
    rs.warnings = warnings


def _pass_proficiencies(rs: ResolveState) -> None:
    """Skills, armor, weapons, tools, languages and the gates over them."""
    bg = rs.bg
    catalog = rs.catalog
    choices = rs.choices
    cls = rs.cls
    fs_slots_by_class = rs.fs_slots_by_class
    pruned = rs.pruned
    race = rs.race
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    srd_fs_slots_by_class = rs.srd_fs_slots_by_class
    subrace = rs.subrace
    xphb_effects = rs.xphb_effects
    pruned += class_choices_2024.gate_additional_secrets(choices, catalog)  # RPX1: SRD Lore Bard 6, apart from the other spell cards
    # Derived stats.
    pruned += _gate_duplicate_skill_picks(choices, [rc["cls_id"] for rc in resolved_classes if rc["cls"]])  # RPF
    proficient_skills: set[str] = set()
    for c in choices:
        # "background" added here (Phase 4b Task 2): a background's own
        # skill-proficiency CHOICE (as opposed to its fixed
        # starting_proficiencies, read separately just below) previously had
        # no path into proficient_skills at all — the exact same "new
        # choice-producing feature needs an equally-new consumer path" gap
        # Phase 4a Task 4b already found and fixed for species. Safe to add
        # unconditionally: the only OTHER background-kind choice is the
        # language choice, whose selected values are language ids, never
        # "skill-"-prefixed, so this filter still excludes them.
        # Expertise picks are not proficiency grants (they must already be
        # proficient), so they never feed this set.
        if (c["source"]["kind"] in ("class", "species", "background", "feat") and "expertise-choice" not in c["id"]
                and not class_choices_2024.is_positioned_proficiency_card(c)):  # C6b-2 / RP12: gated against the others below
            proficient_skills.update(s for s in c["selected"] if _is_skill_id(s))
    fixed_origin_skills: set[str] = set()  # F3a-4: grants that predate every class level
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
        fixed_origin_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            proficient_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
            fixed_origin_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
    # Phase 4c-i Task 6: a granted feat's own FIXED skill-proficiency grant
    # (e.g. a hypothetical background-granted Skilled/Prodigy-style feat)
    # feeds this SAME set, mirroring the bg/race passes just above — see
    # _feat_proficiency_ids' own docstring for why only fixed grants (not
    # a feat's own proficiency_choices) are read.
    feat_proficiency_ids = _feat_proficiency_ids(resolved_feats)
    proficient_skills.update(p for p in feat_proficiency_ids if p.startswith("skill-"))
    fixed_origin_skills.update(p for f in resolved_feats if not f.get("_asi_cid")
                               for p in _feat_proficiency_ids([f]) if p.startswith("skill-"))
    # C6b-2 + F3a-4 + RP12: the positioned picks (Primal Knowledge, the subclass skill / tool picks) yield only to
    # proficiencies gained at or before them; the picks that come later see theirs as already proficient instead.
    pk_class_order = [rc["cls_id"] for rc in resolved_classes if rc["cls"]]
    pruned += _gate_positioned_proficiencies(
        choices, catalog, resolved_classes, resolved_feats, bg, race, subrace, xphb_effects, pk_class_order)
    for c in choices:
        if class_choices_2024.is_positioned_proficiency_card(c):
            proficient_skills.update(s for s in c["selected"] if _is_skill_id(s))

    proficient_armor: set[str] = set()
    proficient_weapons: set[str] = set()
    proficient_tools: set[str] = set()

    # The brief's original heuristic only carved out "shortswords" as the
    # one non-generic weapon-category id, reasoning from a check against
    # Fighter+Rogue's proficiencies alone. A full empirical scan of every
    # SRD class's top-level `proficiencies` (not just the two classes this
    # task's tests exercise) turns up 14 more specific-weapon proficiency
    # ids that don't contain the substring "weapon" — without this set
    # they'd be wrongly bucketed into `tools` for any class whose primary
    # (level-1) proficiency grant names an individual weapon rather than a
    # broad category (e.g. Bard's rapiers/longswords/shortswords/
    # hand-crossbows, Wizard's daggers/darts/slings/quarterstaffs/
    # crossbows-light). Verified against 5e-SRD-Classes.json directly.
    # Task 3b addendum: this set was originally built from an empirical scan
    # of SRD *classes* only (see comment above). Once race/subrace traits
    # also started feeding `_categorize_proficiency` (below), a second scan
    # of every SRD trait's `proficiencies` (5e-SRD-Traits.json) turned up
    # more specific-weapon ids the class-only scan never exercised: Dwarven
    # Combat Training's battleaxes/handaxes/light-hammers/warhammers, and
    # Elf Weapon Training's shortbows/longbows. Without these, real bundled
    # SRD trait grants would be silently miscategorized into `tools`.
    _SPECIFIC_WEAPON_PROFICIENCY_IDS = SPECIFIC_WEAPON_PROFICIENCY_IDS

    def _categorize_proficiency(prof_id: str) -> None:
        if prof_id.startswith("skill-") or prof_id.startswith("saving-throw-"):
            return  # skills handled by proficient_skills elsewhere; saving
            # throws by proficient_save_abilities — a class's top-level
            # `proficiencies` field mixes saving-throw-* entries in with its
            # armor/weapon grants (confirmed for every SRD class), so this
            # guard is needed or they'd fall through to the tools bucket.
        if "armor" in prof_id or prof_id == "shields":
            proficient_armor.add(prof_id)
        elif "weapon" in prof_id or prof_id in _SPECIFIC_WEAPON_PROFICIENCY_IDS or prof_id in reference_data.FEAT_WEAPON_PROFICIENCY_IDS:
            proficient_weapons.add(prof_id)
        else:
            proficient_tools.add(prof_id)

    # PRE-EXISTING gap (predates this plan, affects bundled SRD data
    # unconditionally, not just sourcebook races): the skill-scanning pass
    # above reads `trait_refs` but only forwards skill- prefixed ids into
    # `proficient_skills` — any tool/weapon/armor grant on a race/subrace
    # trait (e.g. SRD Dwarf's "Dwarven Combat Training", which grants
    # battleaxe/handaxe/light-hammer/warhammer proficiency) never reached
    # sheet.proficiencies. This second pass recomputes the identical
    # `trait_refs` (a small, disclosed duplication, matching this file's
    # existing tolerance for it elsewhere, e.g. `_class_label()`) and
    # categorizes every non-skill entry via the same `_categorize_proficiency`
    # used for class-level grants below.
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            for p in trait.get("proficiencies", []):
                if not p["index"].startswith("skill-"):
                    _categorize_proficiency(p["index"])

    # PRE-EXISTING gap (predates this plan, genuinely separate from the
    # race/subrace trait-scanning gap fixed just above): the skill-scanning
    # pass near the top of this function reads `bg.get("starting_proficiencies",
    # [])` but only forwards skill- prefixed ids into `proficient_skills` — any
    # tool/weapon/armor grant on a background (e.g. sourcebook Acolyte's
    # Calligrapher's Supplies) never reached sheet.proficiencies. This second
    # pass recategorizes every non-skill entry via the same
    # `_categorize_proficiency` used for race traits and class-level grants.
    if bg:
        for p in bg.get("starting_proficiencies", []):
            if not p["index"].startswith("skill-"):
                _categorize_proficiency(p["index"])

    # Phase 4c-i Task 6: a granted feat's own FIXED non-skill proficiency
    # grant (e.g. Tavern Brawler/XPHB's improvised-weapon proficiency)
    # feeds the SAME `_categorize_proficiency` used for race/background
    # grants just above — `feat_proficiency_ids` was already computed
    # once, earlier, for the proficient_skills pass, reused here rather
    # than recomputed.
    for p_id in feat_proficiency_ids:
        if not p_id.startswith("skill-"):
            _categorize_proficiency(p_id)

    # Gating on `c["source"]["kind"] == "class"` alone is too broad — it also
    # covers feature subfeature choices, ASI choices, and spell choices
    # (cantrips/known spells), none of which are proficiency choices. A
    # selected spell like `mage-armor` would otherwise be fed into
    # `_categorize_proficiency`, whose substring check ("armor" in prof_id)
    # miscategorizes it into `armor` right next to real armor proficiencies.
    # The two real proficiency-choice id shapes are
    # `class:{cls_id}:1:prof-choice-{i}` (primary class's level-1 choice)
    # and `class:{cls_id}:multiclass-prof-choice-{i}` (this class's
    # multiclass-only choice) — both, and only those, contain the substring
    # "prof-choice-" (verified character-by-character: the primary id's
    # "...:1:prof-choice-0" contains ":prof-choice-", but the multiclass
    # id's "...:multiclass-prof-choice-0" does NOT — the character before
    # "prof-choice-" there is "-", not ":" — so a leading-colon substring
    # check would miss the multiclass pattern; "prof-choice-" without the
    # colon is what actually matches both, confirmed against every cid
    # pattern generated in this file).
    for c in choices:
        if c["source"]["kind"] == "class" and ("prof-choice-" in c["id"] or class_choices_2024.is_positioned_proficiency_card(c)):
            for s in c["selected"]:  # RP12: Student of War's Artisan's Tools pick is positioned like the Monk's level 1 pick
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "species" and "proficiency-choice" in c["id"]:
            # Narrowed to the "proficiency-choice" id substring (set by
            # _species_choice_templates above) so a species-sourced
            # subtrait_options selection (e.g. Dragonborn's Draconic
            # Ancestry damage-type/ancestry pick) or bonus-language
            # selection never reaches _categorize_proficiency, which has no
            # "is this even a real proficiency id" guard and would silently
            # miscategorize a string like "fire" or a language id into the
            # tools bucket.
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "background" and "proficiency-choice" in c["id"]:
            # Phase 4b Task 2's background equivalent of the species branch
            # right above — same reasoning, same "proficiency-choice"
            # substring convention (set by _background_choice_templates),
            # narrowed the same way so the background's OTHER kind=
            # "background" choice (its language choice, selected values are
            # language ids) never reaches _categorize_proficiency. Without
            # this branch, a selected TOOL from a background's tool
            # proficiency choice (e.g. Archaeologist/ToA's Navigator's
            # Tools-or-Cartographer's Tools pick) would resolve as a valid
            # Choice selection yet never reach sheet.proficiencies.tools —
            # confirmed by tracing it end to end while writing this task,
            # not assumed from the Choice template existing (a selected
            # SKILL from the same mechanism already reaches the sheet via
            # the "background" addition to proficient_skills above, so only
            # the non-skill/tool half of this wiring was actually missing).
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "feat" and "proficiency-choice" in c["id"]:
            # Phase 4c-ii Task 1's feat equivalent of the species/background
            # branches above — same reasoning, same "proficiency-choice"
            # substring convention (set by _feat_choice_templates), e.g.
            # Crafter/XPHB's selected tool(s) (Artisan/XPHB's feat grant)
            # reaching sheet.proficiencies.tools.
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)

    for c in choices:  # FE8: Weapon Master (PHB) picks are weapon proficiencies (filed straight into the weapon set)
        if c["source"]["kind"] == "feat" and c["id"].endswith(":weapon-choice"):
            proficient_weapons.update(reference_data.weapon_proficiency_id(s) for s in c["selected"])

    for effect in class_choices_2024.selected_class_option_effects(choices):  # C6a Protector / Warden
        for prof_id in effect.get("proficiencies", []):
            _categorize_proficiency(prof_id)

    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        for prof_id in SUBCLASS_PROFICIENCIES.get(rc["subclass_id"], []):
            _categorize_proficiency(prof_id)
        if rc["index"] == 0:
            for p in rc["cls"].get("proficiencies", []):  # C9a: the 2024 chassis dict already holds XPHB lists
                _categorize_proficiency(p["index"])
        else:
            for p in rc["cls"].get("multi_classing", {}).get("proficiencies", []):
                _categorize_proficiency(p["index"])

    # Expertise needs the full proficiency picture (skills, plus the Rogue's
    # thieves' tools), so it is gated only after every grant above is in.
    # R8: the invocation gate runs first so Beguiling Influence's skills count for expertise.
    pruned += _gate_mastery_choices(choices, catalog, proficient_weapons)  # C2
    pruned += _gate_invocation_choices(choices, resolved_classes, catalog)
    inv_card = next((c for c in choices if class_choices_2024.is_invocation_card_2024(c)), None)
    if inv_card:  # C7c: dependents of an instance the gate dropped go with it
        pruned += class_choices_2024.prune_invocation_dependents(choices, inv_card["selected"])
    pruned += _gate_feat_invocation_prereqs(choices, resolved_classes, catalog)  # FE9 Eldritch Adept
    pruned += _gate_duplicate_picks(  # FE9 Fighting Initiate, Martial Adept, Metamagic Adept, Eldritch Adept
        choices, catalog, [rc["cls_id"] for rc in resolved_classes if rc["cls"]],
        {cid for slots in srd_fs_slots_by_class.values() for cid, _l, _i in slots},
        {cid for slots in fs_slots_by_class.values() for cid, _l, _i in slots})
    pruned += class_choices_2024.prune_feat_invocation_dependents(choices)  # RP20: dependents of a pick the gates removed
    invocation_effects = features_mod.invocation_effects(
        choices, {rc["cls_id"]: rc["level"] for rc in resolved_classes if rc["cls"]}, catalog)
    proficient_skills.update(features_mod.invocation_skills(invocation_effects))
    proficient_skills.update(features_mod.class_skill_proficiencies(xphb_effects))  # RP2 Mercy
    for prof_id in features_mod.class_other_proficiencies(xphb_effects):
        _categorize_proficiency(prof_id)
    poe_priors = _prof_or_expertise_priors(
        choices, resolved_feats, fixed_origin_skills, [rc["cls_id"] for rc in resolved_classes if rc["cls"]])  # FE6
    pruned += _gate_distinct_choices(choices, [rc["cls_id"] for rc in resolved_classes if rc["cls"]])  # FE7
    pruned += class_choices_2024.gate_favored_enemies(choices)  # VF7.3
    pruned += _gate_expertise_choices(
        choices, proficient_skills | proficient_tools, _feat_expertise_skills(resolved_feats),
        [rc["cls_id"] for rc in resolved_classes if rc["cls"]], ruleset, poe_priors)
    # C6b-2 + C8: origin and class language cards yield to fixed languages and to the other cards.
    # F3a-5: class fixed languages and Lessons / ASI feat languages count from their (class, level) position on, so
    # an earlier pick wins and the later duplicate is blamed; origin feats, species, background and Common come first.
    lang_class_order = [rc["cls_id"] for rc in resolved_classes if rc["cls"]]
    # VF2.4: the fixed languages of an official subrace (High Elf, Deep Gnome ...) count like the race's
    fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + \
        [lang["index"] for lang in (race.get("languages", []) if race else [])] + \
        [lang["index"] for lang in ((subrace or {}).get("languages") or [])] + \
        _feat_languages([f for f in resolved_feats if not _feat_build_position(f, lang_class_order)]) + \
        class_choices_2024.fixed_origin_languages(ruleset, bg)  # C8: Common (VF7.1: also a 2024 background under mixed)
    positioned_languages = class_choices_2024.fixed_class_language_entries(catalog, resolved_classes, ruleset) + [
        (pos, lang["index"]) for f in resolved_feats if (pos := _feat_build_position(f, lang_class_order))
        for lang in f.get("languages", [])]
    pruned += class_choices_2024.gate_languages(choices, fixed_languages, lang_class_order, positioned_languages)

    # Phase 4c-i Task 6: was class-only (primary class's saving_throws
    # field) — a granted feat's own FIXED saving-throw-proficiency grant
    # (see _feat_saving_throw_proficiencies' own docstring for why real
    # data contributes nothing here today) now extends this SAME list,
    # deduped so a feat naming an ability the class already covers
    # doesn't produce a duplicate entry in derived.savingThrows/
    # sheet.proficiencies.savingThrows.
    proficient_save_abilities = [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])]
    for ab in _feat_saving_throw_proficiencies(resolved_feats) + [
        a.upper() for a in _feat_selected_choice_values(choices, ":save-choice-")
    ]:
        if ab not in proficient_save_abilities:
            proficient_save_abilities.append(ab)
    rs.fixed_languages = fixed_languages
    rs.invocation_effects = invocation_effects
    rs.poe_priors = poe_priors
    rs.positioned_languages = positioned_languages
    rs.proficient_armor = proficient_armor
    rs.proficient_save_abilities = proficient_save_abilities
    rs.proficient_skills = proficient_skills
    rs.proficient_tools = proficient_tools
    rs.proficient_weapons = proficient_weapons
    rs.pruned = pruned


def _pass_hp_saves_skills(rs: ResolveState) -> None:
    """Hit points, saving throws and skill scores."""
    catalog = rs.catalog
    choices = rs.choices
    classes = rs.classes
    cls = rs.cls
    draft = rs.draft
    invocation_effects = rs.invocation_effects
    modifiers = rs.modifiers
    poe_priors = rs.poe_priors
    prof_bonus = rs.prof_bonus
    proficient_save_abilities = rs.proficient_save_abilities
    proficient_skills = rs.proficient_skills
    pruned = rs.pruned
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    warnings = rs.warnings
    xphb_effects = rs.xphb_effects
    hp_type = (draft.get("preferences") or {}).get("hitPointType")
    if hp_type not in ("fixed", "manual"):
        hp_type = "fixed"
    hp_class_entries = []
    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        rc_hit_die = rc["cls"].get("hit_die")
        if rc_hit_die is None:
            continue
        rc_hp_rolls_raw = classes[rc["index"]].get("hpRolls") if rc["index"] < len(classes) else None
        rc_hp_rolls = {k: v for k, v in rc_hp_rolls_raw.items() if isinstance(v, int) and not isinstance(v, bool)} if isinstance(rc_hp_rolls_raw, dict) else {}
        if hp_type == "manual" and isinstance(rc_hp_rolls_raw, dict):
            # Round-2 F11: a roll outside 1..hit die is replaced by the average
            # (derived.hit_point_gain_per_level) - say so instead of staying silent.
            first_rolled_level = 2 if not hp_class_entries else 1
            for lvl in range(first_rolled_level, rc["level"] + 1):
                if str(lvl) not in rc_hp_rolls_raw:
                    continue
                roll = rc_hp_rolls_raw[str(lvl)]
                if not (isinstance(roll, int) and not isinstance(roll, bool) and 1 <= roll <= rc_hit_die):
                    warnings.append({
                        "id": f"hp-roll-invalid-{rc['cls_id']}-{lvl}",
                        "message": msg("hp-roll-invalid", cls=rc["cls_id"], level=lvl, die=rc_hit_die),
                    })
        hp_class_entries.append({"hit_die": rc_hit_die, "level": rc["level"], "hp_rolls": rc_hp_rolls})
    class_feature_list = _class_feature_list(catalog, resolved_classes, choices, resolved_feats)
    effects = (features_mod.class_effects(class_feature_list, xphb_effects) + invocation_effects
               + subclass_options_2024.effects(choices)  # RP13 Aspect of the Wilds, Elemental Affinity
               + subclass_options_2024.ward_effects(catalog, resolved_classes, choices))  # RP17 Nature's Ward
    # R5: Diamond Soul / Slippery Mind grants (the latter depends on the ruleset).
    for ab in features_mod.save_proficiencies(effects, [idx for _, _, idx in class_feature_list], ruleset):
        if ab not in proficient_save_abilities:
            proficient_save_abilities.append(ab)
    pruned += _gate_save_picks(  # RP12 Iron Mind
        choices, catalog, resolved_classes, resolved_feats, class_feature_list, xphb_effects, ruleset,
        [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])], proficient_save_abilities)
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    aura = features_mod.save_bonus(effects, modifiers)  # R5: Aura of Protection
    if aura:
        saves = {ab: value + aura for ab, value in saves.items()}
    class_levels = {rc["cls_id"]: rc["level"] for rc in resolved_classes if rc["cls"]}
    jack, remarkable = features_mod.half_proficiency(effects)
    # F-D9 (FX refinement): XPHB Jack of All Trades covers only checks that use a skill proficiency you lack
    # (never Initiative). Remarkable Athlete is left as it was in every ruleset: only the SRD feature id is
    # mapped, and the XPHB Champion never carried the effect.
    initiative_jack, initiative_remarkable = jack, remarkable
    if ruleset == "2024":
        initiative_jack = False
    poe_expertise = [sel for c in choices if c["id"] in poe_priors for sel in c["selected"] if sel in poe_priors[c["id"]]]
    expertise_all = list(dict.fromkeys(
        _feat_expertise_skills(resolved_feats) + _expertise_selected_values(choices) + poe_expertise))
    skills = derived_mod.skill_scores(
        modifiers, list(proficient_skills), prof_bonus, expertise_all, jack, remarkable,
    )
    # C6a Thaumaturge / Magician: bonus = max(minimum, WIS modifier) on the listed INT skills,
    # added to the skill totals (never to passive checks, none of these skills has one).
    for effect in class_choices_2024.selected_class_option_effects(choices):
        bonus = effect.get("skill_bonus")
        if bonus:
            amount = max(bonus["minimum"], modifiers[bonus["ability"]])
            for skill_id in bonus["skills"]:
                skills[skill_id] += amount
    rs.class_levels = class_levels
    rs.effects = effects
    rs.expertise_all = expertise_all
    rs.hp_class_entries = hp_class_entries
    rs.hp_type = hp_type
    rs.initiative_jack = initiative_jack
    rs.initiative_remarkable = initiative_remarkable
    rs.pruned = pruned
    rs.saves = saves
    rs.skills = skills


def _pass_speed_attacks_derived(rs: ResolveState) -> None:
    """Speeds, attacks, carrying and the derived block."""
    added_resolved = rs.added_resolved
    catalog = rs.catalog
    choices = rs.choices
    chosen_equipment = rs.chosen_equipment
    class_levels = rs.class_levels
    effects = rs.effects
    equipped_items = rs.equipped_items
    final_scores = rs.final_scores
    gear = rs.gear
    granted_equipment = rs.granted_equipment
    hp_class_entries = rs.hp_class_entries
    hp_type = rs.hp_type
    initiative_jack = rs.initiative_jack
    initiative_remarkable = rs.initiative_remarkable
    modifiers = rs.modifiers
    pact_weapon_id = rs.pact_weapon_id
    prof_bonus = rs.prof_bonus
    proficient_armor = rs.proficient_armor
    proficient_weapons = rs.proficient_weapons
    race = rs.race
    race_id = rs.race_id
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    saves = rs.saves
    skills = rs.skills
    slot_granting_class_ids = rs.slot_granting_class_ids
    species_size = rs.species_size
    species_variant = rs.species_variant
    spell_slots = rs.spell_slots
    subrace = rs.subrace
    warlock_slots = rs.warlock_slots
    warnings = rs.warnings
    speeds = _species_speeds(race, subrace, species_variant)
    worn_armor = any(i.get("equipment_category", {}).get("index") == "armor" for i in equipped_items)  # body armor or shield
    if speeds and not worn_armor:
        speeds = _raise_walk_speed(speeds, features_mod.speed_bonus(effects, class_levels))  # Unarmored Movement
    fast = features_mod.speed_bonus_unless_heavy(effects, equipped_items)  # R5: Fast Movement
    if speeds and fast:
        speeds = _raise_walk_speed(speeds, fast)
    if speeds and features_mod.speed_bonus_flat(effects):  # RP2 Glory 7 Aura of Alacrity
        speeds = _raise_walk_speed(speeds, features_mod.speed_bonus_flat(effects))
    feat_inst = feat_effects_mod.instances(resolved_feats, feat_effects_data.FEAT_EFFECTS, choices)  # FE1
    if speeds and feat_effects_mod.walk_bonus(feat_inst):  # Mobile, Speedy, Boon of Speed, ... (walk only)
        speeds = _raise_walk_speed(speeds, feat_effects_mod.walk_bonus(feat_inst))
    speed_exempt = _heavy_armor_speed_exempt(race, subrace)  # W1
    speeds = _heavy_armor_speed_penalty(  # W1: after every walk bonus, before the "equal to your walking speed" modes
        speeds, 0 if speed_exempt else equipment_mod.armor_speed_penalty(
            equipped_items, final_scores, equipment_mod.counted_body_armor_id(equipped_items)))  # WH: the suit AC counts
    if speeds.get("walk"):  # WF: species "equal to your walking speed" modes follow the FINAL walk (bonuses, penalty)
        for mode in _species_equal_walk_modes(race, subrace):
            speeds = {**speeds, mode: speeds["walk"]}
    fly_bans = equipment_mod.fly_armor_bans(  # X1: "can't use this flying speed" in medium / heavy armor (the counted suit)
        race, subrace, equipped_items, equipment_mod.counted_body_armor_id(equipped_items))
    if fly_bans:
        speeds = {mode: value for mode, value in speeds.items() if mode != "fly"}
    if speeds.get("walk") and features_mod.swim_equals_walk(effects):  # C7b Gift of the Depths
        speeds = {**speeds, "swim": max(speeds.get("swim", 0), speeds["walk"])}
    if speeds.get("walk") and features_mod.climb_equals_walk(effects):  # RP2 Thief, Roving
        speeds = {**speeds, "climb": max(speeds.get("climb", 0), speeds["walk"])}
    if speeds.get("walk") and feat_effects_mod.climb_equals_walk(feat_inst):  # FE1 Athlete (XPHB)
        speeds = {**speeds, "climb": max(speeds.get("climb", 0), speeds["walk"])}
    feat_init_bonus, feat_init_pb = feat_effects_mod.initiative_parts(feat_inst)
    feat_init_pb = feat_init_pb or bool(species_traits_mod.rows(race, subrace, reference_data.SPECIES_INITIATIVE_PB))  # VF2.2 Hare-Trigger
    base_speed = speeds.get("walk")
    # Attacks, carrying capacity and armor warnings (Slice 9). Size is the
    # selected species size (Slice 8d), else the race's own, else Medium.
    weapon_proficiencies = proficient_armor | proficient_weapons
    feat_numbers = feat_effects_mod.numbers_for(modifiers, final_scores, prof_bonus, sum(class_levels.values()))  # FE3
    attacks = attacks_mod.attacks_from_gear(
        equipped_items, modifiers, prof_bonus, proficient_weapons,
        {**features_mod.attack_styles(effects), **feat_effects_mod.attack_flags(feat_inst)},  # FE5 off-hand attacks, Finesse
        gear.hands, pact_weapon=pact_weapon_id,
    )
    class_resources = class_resources_mod.resources_for(
        catalog, resolved_classes, modifiers, prof_bonus, ruleset, choices=choices, warnings_out=warnings)
    is_monk = class_levels.get("monk", 0) >= 1
    martial_arts = next((r for r in class_resources if r["id"] == "monk:martial-arts"), None) if is_monk else None
    martial_arts_die = martial_arts and martial_arts.get("die")
    feat_unarmed = feat_effects_mod.unarmed_spec(feat_inst, gear.hands, equipped_items, martial_arts_die, monk=is_monk)  # FE5, F-D6
    unarmed_type = next((r["type"] for r in species_traits_mod.rows(race, subrace, reference_data.SPECIES_UNARMED_TYPE)), None)  # VF7.5 Lupin
    if is_monk or feat_unarmed:  # R2: the Monk's unarmed strike (never deduped against gear); FE5: or a feat's
        unarmed = attacks_mod.unarmed_strike(modifiers, prof_bonus, martial_arts_die, feat_unarmed, monk=is_monk)
    else:  # VF7.5: every other character has the plain Unarmed Strike (1 + Strength, bludgeoning)
        unarmed = attacks_mod.basic_unarmed_strike(modifiers, prof_bonus)
    if unarmed_type and unarmed["damageType"] == "bludgeoning":
        unarmed = {**unarmed, "damageType": unarmed_type}
    attacks = attacks + [unarmed]
    natural = species_traits_mod.rows(race, subrace, reference_data.SPECIES_NATURAL_WEAPONS)  # VF7.5 Bite, Claws, Horns, Talons ...
    variant_weapon = reference_data.SPECIES_VARIANT_NATURAL_WEAPONS.get((race_id, species_variant["id"])) if race_id and species_variant else None
    attacks = attacks + [attacks_mod.natural_weapon_row(spec, modifiers, prof_bonus) for spec in natural + ([variant_weapon] if variant_weapon else [])]
    attacks = class_resources_mod.annotate_attacks(attacks, class_resources, equipped_items)
    if pact_weapon_id:  # C7c: Thirsting Blade, Eldritch Smite, ... notes on the pact weapon's row
        pact_notes = class_choices_2024.pact_weapon_row_notes(
            [sel for _cls, sel in features_mod.selected_invocation_ids(choices)] + features_mod.selected_feat_invocation_ids(choices))
        attacks = [{**a, "notes": a["notes"] + [n for n in pact_notes if n not in a["notes"]]} if a["itemId"] == pact_weapon_id else a
                   for a in attacks]
    attacks = feat_effects_mod.annotate_attacks(attacks, equipped_items, feat_inst, feat_numbers)  # FE5 (F-D2 notes)
    weapon_masteries = _weapon_masteries(choices, catalog)
    attacks = attacks_mod.annotate_mastery(attacks, weapon_masteries)  # C2
    armor_problems, stealth_disadvantage = equipment_mod.armor_warnings(
        equipped_items, final_scores, weapon_proficiencies, feat_effects_mod.medium_armor_stealth_ok(feat_inst), speed_exempt,
        equipment_mod.counted_body_armor_id(equipped_items))  # FE4, W1, WH
    warnings += armor_problems
    warnings += [equipment_mod.fly_armor_warning(ban) for ban in fly_bans]  # X1
    carrying = derived_mod.carrying_summary(
        final_scores.get("STR", 10), species_size or (race or {}).get("size") or "Medium",
        granted_equipment + chosen_equipment + added_resolved, catalog.items,
        ({**reference_data.ITEM_WEIGHTS_2024, **{k: v["weight"] for k, v in reference_data.PACKS_2024.items()}}
         if ruleset == "2024" else derived_mod.pack_weights_from_contents(catalog.items)),  # RPX2: SRD packs = contents sum
        size_steps=int(species_traits_mod.counts_as_one_size_larger(race, subrace, catalog.traits)),  # VF2.3 Powerful Build and kin
    )
    feat_passive = feat_effects_mod.passive_bonus(feat_inst)  # FE4 Observant (PHB): passive scores only
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_multiclass(hp_class_entries, modifiers["CON"], hp_type)
        + features_mod.hp_bonus(effects, class_levels)
        + sum(e.get("hp_per_level", 0) for e in _srd_trait_effects(race, subrace)) * sum(class_levels.values())
        + feat_effects_mod.hp_bonus(feat_inst, sum(class_levels.values())),
        "hitDice": " + ".join(f"{rc['level']}d{rc['cls']['hit_die']}" for rc in resolved_classes if rc["cls"] and rc["cls"].get("hit_die")) or None,
        "armorClass": equipment_mod.armor_class_from_gear(
            equipped_items, modifiers["DEX"], features_mod.ac_formulas(effects) + feat_effects_mod.ac_formulas(feat_inst),
            modifiers, features_mod.armored_ac_bonus(effects),
            medium_dex_cap=feat_effects_mod.medium_armor_dex_cap(feat_inst, final_scores.get("DEX", 10)),  # FE4
            species_ac=equipment_mod.species_ac_specs(race, subrace),  # VF2.1
        ) + feat_effects_mod.ac_bonus(feat_inst, gear.hands, equipped_items),  # FE4 (needs equipment.wielded)
        "speed": base_speed,  # walking speed; `speeds` carries every mode
        "speeds": speeds,
        "initiative": derived_mod.initiative(modifiers, prof_bonus, initiative_jack, initiative_remarkable,
                                         feat_init_bonus + features_mod.class_initiative_bonus(effects, modifiers), feat_init_pb),
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills) + feat_passive.get("skill-perception", 0),
        "passiveInsight": derived_mod.passive_skill(skills, "skill-insight"),
        "passiveInvestigation": derived_mod.passive_skill(skills, "skill-investigation")
        + feat_passive.get("skill-investigation", 0),
        "spellSlots": spell_slots,
        "warlockSpellSlots": warlock_slots,
        "slotGrantingClasses": slot_granting_class_ids,
        "attacks": attacks,
        "attacksPerAction": class_resources_mod.attacks_per_action(resolved_classes),
        "classResources": class_resources,
        "featResources": feat_effects_mod.resources(feat_inst, feat_numbers),  # FE3
        "speciesResources": species_resources_mod.resources(  # W5a, W5b (choices: SRD Dragonborn ancestry, PHB resistance pick)
            catalog, race, race_id, subrace, species_variant, sum(class_levels.values()), prof_bonus, modifiers, base_speed,
            choices),
        "carryingCapacity": carrying,
        "stealthDisadvantage": stealth_disadvantage,
    }
    rs.derived = derived
    rs.feat_inst = feat_inst
    rs.feat_numbers = feat_numbers
    rs.warnings = warnings
    rs.weapon_masteries = weapon_masteries


def _pass_rest(rs: ResolveState) -> dict:
    """The remaining sections of the old single function."""
    added_resolved = rs.added_resolved
    asi_selected_feats = rs.asi_selected_feats
    bg = rs.bg
    bg_id = rs.bg_id
    catalog = rs.catalog
    choices = rs.choices
    chosen_equipment = rs.chosen_equipment
    derived = rs.derived
    details = rs.details
    draft = rs.draft
    effects = rs.effects
    expertise_all = rs.expertise_all
    feat_inst = rs.feat_inst
    feat_numbers = rs.feat_numbers
    feat_options = rs.feat_options
    final_scores = rs.final_scores
    fixed_languages = rs.fixed_languages
    fs_feats = rs.fs_feats
    gear = rs.gear
    granted_equipment = rs.granted_equipment
    granted_feats = rs.granted_feats
    invocation_effects = rs.invocation_effects
    lessons_feats = rs.lessons_feats
    modifiers = rs.modifiers
    narrative_items = rs.narrative_items
    positioned_languages = rs.positioned_languages
    problems = rs.problems
    proficient_armor = rs.proficient_armor
    proficient_save_abilities = rs.proficient_save_abilities
    proficient_skills = rs.proficient_skills
    proficient_tools = rs.proficient_tools
    proficient_weapons = rs.proficient_weapons
    pruned = rs.pruned
    race = rs.race
    race_id = rs.race_id
    resolved_classes = rs.resolved_classes
    resolved_feats = rs.resolved_feats
    ruleset = rs.ruleset
    species_alt = rs.species_alt
    species_feats = rs.species_feats
    species_size = rs.species_size
    species_spell_ability = rs.species_spell_ability
    species_variant = rs.species_variant
    spell_slots = rs.spell_slots
    spells_summary = rs.spells_summary
    starting_gold = rs.starting_gold
    subrace = rs.subrace
    subrace_id = rs.subrace_id
    total_level = rs.total_level
    variant_follow = rs.variant_follow
    warlock_slots = rs.warlock_slots
    warnings = rs.warnings
    weapon_masteries = rs.weapon_masteries
    # fixed_languages: computed with the class language gate above (Phase 4c-i Task 6 feat grants included)
    chosen_languages = [
        s for c in choices
        if (c["source"]["kind"] in ("background", "species", "feat") and c["id"].endswith(":languages"))
        or class_choices_2024.is_class_language_card(c)  # C6b-2
        for s in c["selected"]
    ]

    # granted_feats/feat_options/resolved_feats are now computed much
    # earlier (Phase 4c-i Task 6 hoist — right after `bg` itself is
    # resolved, see that call site's own comment) so this task's
    # ability-bonus/proficiency/language/expertise/saving-throw merges
    # could feed the SAME early passes species/background/race already
    # feed. damage_modifiers/condition_immunities/senses (Task 5) still
    # read `resolved_feats` here, unchanged — only WHERE it's computed
    # moved, not what these three lines do.
    chosen_resistances = [
        v for c in choices
        if c["source"]["kind"] == "species" and c["id"].endswith(":resistance")
        for v in c["selected"]
    ]
    # SRD trait effects (Dwarven Resilience, Hellish Resistance) and the
    # damage type of a selected Draconic Ancestry subtrait.
    chosen_resistances += (species_variant or {}).get("resist") or []
    for effect in _srd_trait_effects(race, subrace):
        chosen_resistances += effect.get("resist", [])
    for c in choices:
        if c["source"]["kind"] != "species" or ":trait:" not in c["id"]:
            continue
        for sel in c["selected"]:
            damage = ((catalog.traits.get(sel) or {}).get("trait_specific") or {}).get("damage_type")
            if damage:
                chosen_resistances.append(damage["index"])
    chosen_resistances += features_mod.class_resistances(effects)  # RP2
    chosen_resistances += feat_effects_mod.resistances(  # FE7: resistance picks of the held feats (Scion follows its plane)
        feat_effects_mod.instances(resolved_feats, feat_effects_data.FEAT_EFFECTS, choices))
    damage_modifiers = _species_damage_modifiers(race, subrace, resolved_feats, chosen_resistances)
    condition_immunities = _species_condition_immunities(race, subrace, resolved_feats)
    for cond in features_mod.class_condition_immunities(effects):  # RPF Archfey 10, Nature's Ward
        if cond not in condition_immunities:
            condition_immunities.append(cond)
    senses = _species_senses(race, subrace, catalog, species_variant)
    for sense_kind, sense_range in _feat_senses(resolved_feats).items():
        if sense_range > senses.get(sense_kind, 0):
            senses[sense_kind] = sense_range
    for sense_kind, sense_range in features_mod.invocation_senses(invocation_effects).items():  # R8
        if sense_range > senses.get(sense_kind, 0):
            senses[sense_kind] = sense_range
    senses = feat_effects_mod.add_senses(senses, feat_inst)  # FE4 Keenness of the Stone Giant (adds to the final range)
    senses = features_mod.class_senses(senses, effects)  # RP2 Darkvision +60, Blindsight 30
    innate_spells = (_species_innate_spells(race, subrace, catalog, species_variant, species_alt, species_spell_ability)
                     + _species_trait_spell_choices(race, subrace, catalog, choices)
                     + _feat_innate_spells(resolved_feats, catalog, choices, feat_effects_mod.innate_patches(feat_inst, feat_numbers), follow_variants=variant_follow)
                     + [{**_innate_entry_to_sheet(e, catalog), "featId": e["featId"], "source": e["source_label"], "note": e["note"]}  # RP19
                        for e in feat_spell_tables.adept_entries(resolved_feats, feat_spell_tables.highest_slot_level(spell_slots, warlock_slots))]
                     + [{**_innate_entry_to_sheet(e, catalog), "source": e["source_label"],
                         **({"note": e["note"]} if e.get("note") else {})}
                        for e in features_mod.invocation_innate_entries(invocation_effects) + features_mod.feat_tome_entries(choices)]
                     + [{**_innate_entry_to_sheet(e, catalog), "source": e["source_label"],  # RP18
                         **({"note": e["note"]} if e.get("note") else {})}
                        for e in subclass_innate_2024.innate_entries(catalog, resolved_classes, ruleset, modifiers)])
    innate_spells = [innate_uses.with_limit(e) for e in innate_spells]  # G6: usesMax + recharge from the `uses` text

    refs_by_class = {
        rc["cls_id"]: _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"])
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    warnings += _dark_gift_ravenloft_warnings(resolved_feats, draft.get("sources"))
    sheet_feats = sheet_features_mod.feats_summary(resolved_feats, choices, feat_effects_mod.notes(feat_inst, feat_numbers))

    sheet = {
        "name": draft.get("name") or "",
        "level": total_level if resolved_classes else 0,
        "classes": [
            {
                "id": rc["cls_id"], "name": rc["cls"]["name"], "level": rc["level"],
                "subclass": {"id": rc["subclass_id"], "name": rc["subclass"]["name"]} if rc["subclass_id"] and rc["subclass"] else None,
            }
            for rc in resolved_classes if rc["cls"]
        ],
        "background": {"id": bg_id, "name": bg["name"]} if bg else None,
        "species": {
            "id": race_id, "name": race["name"],
            "subspecies": {"id": subrace_id, "name": subrace["name"]} if subrace else None,
            "variant": {"id": species_variant["id"], "name": species_variant["name"]} if species_variant else None,
            "size": species_size,
        } if race else None,
        "abilities": final_scores,
        "proficiencies": {
            "skills": sorted(proficient_skills),
            "savingThrows": proficient_save_abilities,
            "languages": sorted(set(fixed_languages + [lang for _pos, lang in positioned_languages] + chosen_languages)),
            "armor": sorted(proficient_armor),
            "weapons": sorted(proficient_weapons),
            "tools": sorted(proficient_tools),
        },
        "startingGold": starting_gold,
        "equipment": {
            "granted": granted_equipment, "chosen": chosen_equipment, "added": added_resolved,
            "narrativeItems": narrative_items, "slots": gear.slots,
            **({"worn": gear.worn} if gear.worn else {}), **({"wielded": gear.wielded} if gear.wielded else {}),
        },
        "spells": spells_summary,
        "details": details,
        "damageModifiers": damage_modifiers,
        "conditionImmunities": condition_immunities,
        "innateSpells": innate_spells,
        # Background grants keep their bare-slug ids (unchanged); a feat
        # taken at an ASI level is appended by its full catalog index
        # (e.g. "actor-xphb") — the exact id it was selected by.
        "grantedFeats": granted_feats + [f["index"] for f in species_feats] + [f["index"] for f in fs_feats] + [f["index"] for f in lessons_feats] + [f["index"] for f in asi_selected_feats],
        "featOptions": feat_options,
        "senses": senses,
        "expertiseSkills": expertise_all,
        "features": sheet_features_mod.build_features(
            catalog, resolved_classes, refs_by_class, race, race_id, subrace, bg, bg_id, resolved_feats, choices,
            ruleset=ruleset, species_variant=species_variant,
        ),
        "feats": sheet_feats,
        "weaponMasteries": weapon_masteries,
    }

    choices = class_choices_2024.mark_unavailable(choices, ruleset)  # F3a-2b: uncompletable new 2024 cards do not block
    choices = option_source_mod.annotate_choices(catalog, choices)  # SK10 (Y2): `source` on feat / spell / feature options

    if len(pruned) > MAX_PRUNED_REPORTED:  # F2-D: cap last, so every gate's entries count and the marker ends the list
        extra = len(pruned) - MAX_PRUNED_REPORTED
        pruned = pruned[:MAX_PRUNED_REPORTED] + [{
            "choiceId": "pruned-more",
            "reason": msg("pruned-more", extra=extra),
        }]

    return {
        "sheet": sheet,
        # F2-C: `count_by_level` is an internal template key (count-variable test), not API shape.
        "choices": [{k: v for k, v in c.items() if k not in ("count_by_level", "lacksExpertise", "profOrExpertise", "distinctGroup", "distinctFixed")} for c in choices],
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": pruned,
    }


def resolve(draft: dict, catalog: Catalog) -> dict:
    rs = ResolveState(draft, catalog)
    _pass_classes(rs)
    _pass_background(rs)
    _pass_species(rs)
    _pass_abilities(rs)
    _pass_origin_feats(rs)
    _pass_feat_walk(rs)
    _pass_origin_ability_deltas(rs)
    _pass_class_asi_loop(rs)
    _pass_spell_and_choice_templates(rs)
    _pass_collect_choices(rs)
    _pass_equipment_and_spells(rs)
    _pass_proficiencies(rs)
    _pass_hp_saves_skills(rs)
    _pass_speed_attacks_derived(rs)
    return _pass_rest(rs)
