"""Builds Choice-shaped templates (id, source, label, description, count,
options) from the SRD's "choose N of..." envelopes, per the architecture
spec's central abstraction (docs/superpowers/specs/2026-09-16-builder-v2-architecture.md
§1-2). Handles the option_set_type shapes this project needs:
`options_array` (an explicit option list — the common case) and
`resource_list` for languages specifically (Backgrounds.json's
language_options references "/api/2014/languages", which isn't bundled as
its own SRD file — resolved from reference_data.LANGUAGES instead, since
that's pure open-content SRD data, not sourcebook material).
`equipment_category`-based option sets (used by starting_equipment_options)
are still NOT resolved here — every case that would need it in the bundled
data is also nested inside an unrepresentable option_type "choice" (see
build_choice_options' "multiple" handling below), so there's nothing to
gain by solving only half of that problem in Phase 2a. A "multiple" bundle
(e.g. "leather armor, a longbow, and 20 arrows") IS resolved, as one
combined option, but only when every item inside it is uniformly a plain
counted_reference OR uniformly an ability_bonus (Phase 4b Task 4 — see
below) — a bundle containing its own nested sub-choice, or a mix of item
types, returns None for that one option, same "skip rather than fake it"
discipline as everything else in this module.

Phase 4a (sourcebook races) adds two more: `any_skill` and `any_tool`
(optionally narrowed by a `tool_category` key). Both are a genuinely
different shape from every case above — the envelope carries NO options
list of its own at all (a sourcebook race's "choose 2 skills of your
choice" is a real 5etools "any": N wildcard, not an enumerated list), so
the full candidate set is sourced from reference_data.SKILL_NAMES/TOOLS
instead of from `from_field` itself. An enumerated race skill/tool choice
(e.g. "choose 1 of {Perception, Stealth, Survival}") needs no new shape at
all — official_source.py builds it as a plain `options_array`, the exact
same mechanism every other choice in this module already uses.

Phase 4b Task 4 (the 2024-style background ability-score-improvement
choice) reuses the "multiple" bundle mechanism above for a NEW sub-item
shape: bundles of `ability_bonus` items (e.g. "STR +2, CON +1", or
"STR +1, CON +1, CHA +1") instead of `counted_reference` equipment items —
see _bundle_label_and_id's own docstring for exactly which shapes are, and
aren't, resolvable.
"""
from __future__ import annotations

from . import reference_data


def _option_label(option: dict) -> str | None:
    option_type = option.get("option_type")
    if option_type == "reference":
        return option["item"]["name"]
    if option_type == "counted_reference":
        return option["of"]["name"]
    if option_type == "string":
        return option["string"]
    if option_type == "ability_bonus":
        return f"{option['ability_score']['name']} +{option.get('bonus', 1)}"
    return None  # score_prerequisite, multiple, etc. — not used by any Phase 1 choice


def _bundle_label_and_id(items: list[dict]) -> tuple[str, str] | None:
    """A 'multiple' option's items are themselves option-shaped. Resolvable
    when EVERY sub-item is EITHER a plain counted_reference (the original,
    Phase 1-era equipment-bundle case, e.g. "leather armor, a longbow, and
    20 arrows") OR an ability_bonus (Phase 4b Task 4's background
    ability-score-improvement bundles, e.g. "STR +2, CON +1") — but not a
    mix of the two, and never a nested 'choice' (e.g. "a martial weapon
    and a shield", where "a martial weapon" is its own sub-choice), which
    makes the whole bundle unrepresentable in this phase's flat Choice
    model. Returns None rather than silently dropping meaning in either
    unresolvable case.
    """
    if not items:
        return None
    sub_types = {sub.get("option_type") for sub in items}
    if sub_types == {"counted_reference"}:
        label_parts = []
        id_parts = []
        for sub in items:
            of = sub["of"]
            count = sub.get("count", 1)
            label_parts.append(f"{count}x {of['name']}" if count != 1 else of["name"])
            id_parts.append(of["index"])  # quantities are not part of the id — see plan's Global Constraints
        return " + ".join(label_parts), "+".join(id_parts)
    if sub_types == {"ability_bonus"}:
        label_parts = []
        id_parts = []
        for sub in items:
            ability = sub["ability_score"]
            bonus = sub.get("bonus", 1)
            label_parts.append(f"{ability['name']} +{bonus}")
            id_parts.append(f"{ability['index']}-{bonus}")
        return " + ".join(label_parts), "+".join(id_parts)
    return None


def build_choice_options(from_field: dict) -> list[dict] | None:
    """Returns [{id, label}] for this option set, or None if it can't be
    resolved from bundled Phase 1 data (equipment_category, or a
    resource_list type other than languages)."""
    set_type = from_field.get("option_set_type")

    if set_type == "options_array":
        options = []
        for opt in from_field.get("options", []):
            if opt.get("option_type") == "multiple":
                bundle = _bundle_label_and_id(opt.get("items", []))
                if bundle is None:
                    continue
                label, option_id = bundle
                options.append({"id": option_id, "label": label})
                continue
            label = _option_label(opt)
            if label is None:
                continue
            if opt.get("option_type") == "ability_bonus":
                option_id = opt["ability_score"]["index"]
                options.append({"id": option_id, "label": label})
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            options.append({"id": option_id, "label": label})
        return options if options else None

    if set_type == "resource_list":
        url = from_field.get("resource_list_url", "")
        if url.rstrip("/").endswith("languages"):
            return [{"id": lang["index"], "label": lang["name"]} for lang in reference_data.LANGUAGES]
        return None  # an unrecognized resource type — nothing else is bundled in Phase 1

    if set_type == "any_skill":
        return [{"id": s_id, "label": name} for s_id, name in reference_data.SKILL_NAMES.items()]

    if set_type == "any_tool":
        category = from_field.get("tool_category")
        return [
            {"id": t["index"], "label": t["name"]}
            for t in reference_data.TOOLS
            if category is None or t["category"] == category
        ]

    return None  # equipment_category and anything else — Phase 2+


def build_choice_template(
    envelope: dict,
    choice_id: str,
    source: dict,
    label: str,
    description: str | None = None,
) -> dict | None:
    """envelope is a raw "choose N of..." dict (has 'choose' and 'from').
    Returns a Choice template WITHOUT 'selected'/'status' — the engine adds
    those once it has the Draft's actual selections — or None if the option
    set can't be resolved from bundled Phase 1 data."""
    options = build_choice_options(envelope.get("from", {}))
    if options is None:
        return None
    desc = description if description is not None else envelope.get("desc")
    if isinstance(desc, list):
        desc = " ".join(desc)
    return {
        "id": choice_id,
        "source": source,
        "label": label,
        "description": desc or "",
        "count": envelope.get("choose", 1),
        "options": options,
    }
