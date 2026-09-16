"""resolve(draft, catalog) -> Resolution — the single entry point for all
character-rules computation, per the architecture spec's engine contract
(docs/superpowers/specs/2026-09-16-builder-v2-architecture.md §3). One
fixed-order pass: sources → species ability bonuses → final ability scores
→ derived stats → choice generation/validation (§4a) — never iterates to a
fixpoint.

Phase 1 scope: single class, level 1 only. Multiclass, leveling above 1,
subclass selection, and equipment are all out of scope (see the plan's
Global Constraints) — draft.classes[0].subclassId is read but never
trusted to gate a feature choice unless it actually matches, so any
level-1 feature gated to a specific subclass is filtered out rather than
guessed at.
"""
from __future__ import annotations

from catalog.choices import build_choice_template
from catalog.loader import Catalog
from . import derived as derived_mod


def _species_ability_bonuses(race: dict | None, subrace: dict | None) -> dict[str, int]:
    bonuses: dict[str, int] = {}
    for src in (race, subrace):
        if not src:
            continue
        for entry in src.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            bonuses[ab] = bonuses.get(ab, 0) + entry["bonus"]
    return bonuses


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


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[dict], subclass_id: str | None,
) -> list[dict]:
    templates = []
    for ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated, and Phase 1 never has a trusted subclass pick
        envelope = (feature.get("feature_specific") or {}).get("subfeature_options")
        if not envelope:
            continue
        cid = f"class:{cls_id}:1:feature:{feature['index']}"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": 1}
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
    if cls_entry and cls_entry.get("level", 1) != 1:
        problems.append({"id": "level-unsupported", "message": "Only level 1 is supported in this version."})

    cls = catalog.classes.get(cls_id) if cls_id else None
    if cls_id and not cls:
        problems.append({"id": "unknown-class", "message": f"Unknown class '{cls_id}'."})

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
    if race and race.get("ability_bonus_options"):
        problems.append({
            "id": "species-ability-choice-unsupported",
            "message": f"{race['name']}'s ability-score choice isn't supported yet — no bonus from it was applied.",
        })
    if subrace and subrace.get("ability_bonus_options"):
        problems.append({
            "id": "species-ability-choice-unsupported",
            "message": f"{subrace['name']}'s ability-score choice isn't supported yet — no bonus from it was applied.",
        })
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

    modifiers = derived_mod.ability_modifiers(final_scores)
    prof_bonus = 2  # fixed at level 1 for every class, per the SRD level tables

    # Choice templates from every source.
    choice_templates: list[dict] = []
    if cls and cls_id:
        choice_templates += _class_choice_templates(cls, cls_id)
        level_row = catalog.level_row(cls_id, 1)
        if level_row:
            choice_templates += _feature_choice_templates(catalog, cls_id, cls["name"], level_row.get("features", []), subclass_id)
    if bg and bg_id:
        choice_templates += _background_choice_templates(bg, bg_id)
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)

    # Apply the draft's own selections onto each template to get a real Choice.
    all_selections: dict[str, list[str]] = {}
    if cls_entry:
        all_selections.update(cls_entry.get("choices") or {})
    all_selections.update(background_dict.get("choices") or {})
    all_selections.update(species.get("choices") or {})

    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        selected = [s for s in raw_selected if s in valid_ids]
        if len(selected) > tpl["count"]:
            problems.append({
                "id": f"over-selected-{tpl['id']}",
                "message": f"'{tpl['label']}' allows {tpl['count']} selection(s) but {len(selected)} were submitted.",
            })
            selected = selected[: tpl["count"]]
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})

    # Derived stats.
    proficient_skills: set[str] = set()
    for c in choices:
        if c["source"]["kind"] == "class":
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))

    proficient_save_abilities = [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])]

    hit_die = cls.get("hit_die") if cls else None
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    skills = derived_mod.skill_scores(modifiers, list(proficient_skills), prof_bonus)
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max(hit_die, modifiers["CON"]),
        "hitDice": f"1d{hit_die}" if hit_die else None,
        "armorClass": derived_mod.armor_class(modifiers["DEX"]),
        "speed": race.get("speed") if race else None,
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills),
    }

    fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + \
        [lang["index"] for lang in (race.get("languages", []) if race else [])]
    chosen_languages = [s for c in choices if c["source"]["kind"] == "background" for s in c["selected"]]

    sheet = {
        "name": draft.get("name") or "",
        "level": 1 if cls else 0,
        "class": {"id": cls_id, "name": cls["name"]} if cls else None,
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
    }

    return {
        "sheet": sheet,
        "choices": choices,
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": [],
    }
