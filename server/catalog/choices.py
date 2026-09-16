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
are NOT resolved here — equipment choices are out of scope until Phase 2,
so any envelope needing that path returns None, and every caller must skip
a None result entirely rather than emit a partial or broken choice.
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
    return None  # score_prerequisite, multiple, etc. — not used by any Phase 1 choice


def build_choice_options(from_field: dict) -> list[dict] | None:
    """Returns [{id, label}] for this option set, or None if it can't be
    resolved from bundled Phase 1 data (equipment_category, or a
    resource_list type other than languages)."""
    set_type = from_field.get("option_set_type")

    if set_type == "options_array":
        options = []
        for opt in from_field.get("options", []):
            label = _option_label(opt)
            if label is None:
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            options.append({"id": option_id, "label": label})
        return options

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
