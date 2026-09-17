"""Builds Choice-shaped templates (id, source, label, description, count,
options) from the SRD's "choose N of..." envelopes, per the architecture
spec's central abstraction (docs/superpowers/specs/2026-09-16-builder-v2-architecture.md
§1-2). Handles the two option_set_type shapes Phase 1 needs:
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
combined option, but only when every item inside it is a plain
counted_reference — a bundle containing its own nested sub-choice returns
None for that one option, same "skip rather than fake it" discipline as
everything else in this module.
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
    """A 'multiple' option's items are themselves option-shaped. Only
    resolvable if EVERY sub-item is a plain counted_reference — a nested
    'choice' (e.g. "a martial weapon and a shield", where "a martial
    weapon" is its own sub-choice) makes the whole bundle unrepresentable
    in this phase's flat Choice model, so this returns None rather than
    silently dropping the sub-choice's meaning.
    """
    if not items:
        return None
    label_parts = []
    id_parts = []
    for sub in items:
        if sub.get("option_type") != "counted_reference":
            return None
        of = sub["of"]
        count = sub.get("count", 1)
        label_parts.append(f"{count}x {of['name']}" if count != 1 else of["name"])
        id_parts.append(of["index"])  # quantities are not part of the id — see plan's Global Constraints
    return " + ".join(label_parts), "+".join(id_parts)


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
