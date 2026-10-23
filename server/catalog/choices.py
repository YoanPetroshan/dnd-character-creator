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
are NOT resolved by build_choice_options (it has no item catalog); Slice 6's
build_equipment_choice (bottom of this module) expands them, and nested
option_type "choice" picks inside bundles, using the Equipment catalog.
A "multiple" bundle
(e.g. "leather armor, a longbow, and 20 arrows") IS resolved, as one
combined option by build_choice_options, but only when every item inside it is uniformly a plain
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


def _bundle_quantities(items: list[dict]) -> dict[str, int]:
    """C9b: {item id: count} for the counted members of a bundle whose count is not 1 (2024 class
    packages only; the ids of a bundle never carry quantities)."""
    return {sub["of"]["index"]: sub["count"] for sub in items
            if sub.get("option_type") == "counted_reference" and sub.get("count", 1) != 1}


def pack_units(item: dict | None, count: int) -> int:
    """RPX3: units of a catalog item for a counted phrase of the rules text. Ammunition records are already packs
    (arrow / crossbow bolt / sling bullet 20, blowgun needle 50: `quantity` on the item), so "20 arrows" is ONE unit
    of the catalog `arrow` (F3a-6, the same rule as the 2024 packages); a count that is not a multiple rounds up."""
    pack = (item or {}).get("quantity")
    if isinstance(pack, int) and not isinstance(pack, bool) and pack > 1:
        return max(1, -(-count // pack))
    return count


def pack_quantities(quantities: dict[str, int], items: dict) -> dict[str, int]:
    """`quantities` with the ammunition packs converted by `pack_units`; entries that become 1 are dropped."""
    out = {i: pack_units(items.get(i), n) for i, n in quantities.items()}
    return {i: n for i, n in out.items() if n != 1}


def _flatten_nested_tool_choice(opt: dict) -> list[dict]:
    """RP7 (E11c): the options of one nested `option_type: "choice"` of a PROFICIENCY envelope (the SRD Monk's
    "artisan's tools" / "musical instrument" alternatives) as flat {id, label, group} entries. `group` is the
    catalog tool category; a member the catalog tool table does not know is dropped (the SRD data lists Disguise Kit
    and Forgery Kit among the artisan's tools, the tool table does not class them so)."""
    tools = {t["index"]: t for t in reference_data.TOOLS}
    out = []
    for sub in ((opt.get("choice") or {}).get("from") or {}).get("options", []):
        item = sub.get("item") if sub.get("option_type") == "reference" else None
        tool = tools.get(item["index"]) if item else None
        if tool is not None:
            out.append({"id": tool["index"], "label": item["name"], "group": tool["category"]})
    return out


def build_choice_options(from_field: dict, keep_counts: bool = False, flatten_nested: bool = False) -> list[dict] | None:
    """Returns [{id, label}] for this option set, or None if it can't be
    resolved from bundled Phase 1 data (equipment_category, or a
    resource_list type other than languages). `keep_counts` (C9b, decision E8) adds
    `quantities: {item id: n}` to a bundle option that has counts other than 1.
    `flatten_nested` (RP7, set by build_choice_template for proficiency envelopes only) flattens a nested
    `option_type: "choice"` into the option list; otherwise such an option is skipped as before."""
    set_type = from_field.get("option_set_type")

    if set_type == "options_array":
        options = []
        for opt in from_field.get("options", []):
            if opt.get("option_type") == "choice" and flatten_nested:
                options.extend(o for o in _flatten_nested_tool_choice(opt) if all(o["id"] != e["id"] for e in options))
                continue
            if opt.get("option_type") == "multiple":
                bundle = _bundle_label_and_id(opt.get("items", []))
                if bundle is None:
                    continue
                label, option_id = bundle
                quantities = _bundle_quantities(opt.get("items", [])) if keep_counts else {}
                options.append({"id": option_id, "label": label, **({"quantities": quantities} if quantities else {})})
                continue
            label = _option_label(opt)
            if label is None:
                continue
            if keep_counts and opt.get("option_type") == "counted_reference" and opt.get("count", 1) != 1:
                label = f"{opt['count']}x {label}"  # RPX3: same label as the expanded path ("2x Handaxe")
            if opt.get("option_type") == "ability_bonus":
                option_id = opt["ability_score"]["index"]
                options.append({"id": option_id, "label": label})
                continue
            item = opt.get("item") or opt.get("of")
            option_id = item["index"] if item else label.lower().replace(" ", "-")
            single = _bundle_quantities([opt]) if keep_counts else {}  # RPX3: "two handaxes" is one counted option
            options.append({"id": option_id, "label": label, **({"quantities": single} if single else {})})
        return options if options else None

    if set_type == "resource_list":
        url = from_field.get("resource_list_url", "")
        if url.rstrip("/").endswith("languages"):
            return [{"id": lang["index"], "label": lang["name"]} for lang in reference_data.LANGUAGES]
        return None  # an unrecognized resource type — nothing else is bundled in Phase 1

    if set_type == "any_skill":
        return [{"id": s_id, "label": name} for s_id, name in reference_data.SKILL_NAMES.items()]

    if set_type == "any_skill_or_tool":
        # Skilled-style "any N from skills or tools": every skill, then every tool.
        return [{"id": s_id, "label": name} for s_id, name in reference_data.SKILL_NAMES.items()] + [
            {"id": t["index"], "label": t["name"]} for t in reference_data.TOOLS
        ]

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
    options = build_choice_options(envelope.get("from", {}), keep_counts=bool(envelope.get("keep_counts")),
                                   flatten_nested=envelope.get("type") == "proficiencies")
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


# --- Starting equipment: equipment_category sets and nested sub-choices ----
#
# The SRD references item sets by category index ("holy-symbols",
# "martial-melee-weapons", ...) but bundles no category file, so membership is
# derived from each Equipment.json item's own fields.

def _item_in_category(item: dict, category: str) -> bool | None:
    """True/False for a recognised category index, None for an unknown one."""
    if category in ("holy-symbols", "arcane-foci", "druidic-foci"):
        return (item.get("gear_category") or {}).get("index") == category
    if category == "musical-instruments":
        return item.get("tool_category") == "Musical Instrument"
    if category == "gaming-sets":  # RP9: 2024 background gaming set / artisan's tools picks
        return item.get("tool_category") == "Gaming Sets"
    if category == "artisans-tools":
        return item.get("tool_category") == "Artisan's Tools"
    weapon_sets = {
        "simple-weapons": ("Simple", None), "martial-weapons": ("Martial", None),
        "simple-melee-weapons": ("Simple", "Melee"), "martial-melee-weapons": ("Martial", "Melee"),
        "simple-ranged-weapons": ("Simple", "Ranged"), "martial-ranged-weapons": ("Martial", "Ranged"),
    }
    if category in weapon_sets:
        weapon_category, weapon_range = weapon_sets[category]
        return (item.get("weapon_category") == weapon_category
                and (weapon_range is None or item.get("weapon_range") == weapon_range))
    return None


def equipment_category_options(category: str, items: dict[str, dict]) -> list[dict] | None:
    """[{id, label}] for every catalog item in the category, or None when the
    category is not recognised or matches nothing."""
    options = []
    for item in items.values():
        if item.get("source", "SRD") != "SRD":
            continue  # imported sourcebook items never change a starting-equipment option set
        member = _item_in_category(item, category)
        if member is None:
            return None
        if member:
            options.append({"id": item["index"], "label": item["name"]})
    return options or None


def _equipment_category_index(from_field: dict) -> str | None:
    if from_field.get("option_set_type") != "equipment_category":
        return None
    return (from_field.get("equipment_category") or {}).get("index")


def _capitalise(text: str) -> str:
    return text[:1].upper() + text[1:]


def build_equipment_choice(
    envelope: dict, choice_id: str, source: dict, label: str, items: dict[str, dict],
) -> tuple[dict | None, dict[str, list[dict]]]:
    """Starting-equipment envelope -> (template, dependents).

    - A top-level `equipment_category` set becomes a flat list of its items.
    - An option_type "choice" option (e.g. "any simple weapon"), alone or as
      a member of a "multiple" bundle (e.g. "a martial weapon and a shield"),
      becomes a placeholder option whose id lists its fixed members and
      `any-<category>` for each nested pick. Choosing it makes the nested
      picks real follow-up Choices, returned in `dependents` as
      {option_id: [sub-template, ...]} with ids `{choice_id}:{j}` (j counts
      nested picks across the whole envelope, so it is stable whichever
      option is selected). The caller adds them once that option is selected.
    Options that can't be resolved are left out (same discipline as
    build_choice_template); template is None when nothing survives."""
    from_field = envelope.get("from", {})
    category = _equipment_category_index(from_field)
    desc = envelope.get("desc") or ""
    if category is not None:
        options = equipment_category_options(category, items)
        if options is None:
            return None, {}
        return {
            "id": choice_id, "source": source, "label": label, "description": desc,
            "count": envelope.get("choose", 1), "options": options,
        }, {}
    if from_field.get("option_set_type") != "options_array":
        return None, {}

    options: list[dict] = []
    dependents: dict[str, list[dict]] = {}
    seen: set[str] = set()
    slot_index = 0
    keep_counts = bool(envelope.get("keep_counts"))  # C9b: only the 2024 class packages set it
    for opt in from_field.get("options", []):
        members = opt.get("items") if opt.get("option_type") == "multiple" else [opt]
        id_parts: list[str] = []
        label_parts: list[str] = []
        subs: list[dict] = []
        resolvable = bool(members)
        for member in members or []:
            mtype = member.get("option_type")
            if mtype == "counted_reference":
                count = member.get("count", 1)
                name = member["of"]["name"]
                id_parts.append(member["of"]["index"])
                label_parts.append(f"{count}x {name}" if count != 1 else name)
            elif mtype == "reference":
                id_parts.append(member["item"]["index"])
                label_parts.append(member["item"]["name"])
            elif mtype == "choice":
                nested = member.get("choice") or {}
                this_slot = slot_index  # counted even when unresolvable, so ids stay stable
                slot_index += 1
                nested_category = _equipment_category_index(nested.get("from", {}))
                nested_options = equipment_category_options(nested_category, items) if nested_category else None
                only = (nested.get("from") or {}).get("only")  # RP9: e.g. "Arcane Focus (Crystal or Wand)"
                if nested_options is not None and only:
                    nested_options = [o for o in nested_options if o["id"] in only] or None
                if nested_options is None:
                    resolvable = False
                    continue
                nested_desc = nested.get("desc") or "an item"
                id_parts.append(f"any-{nested_category}")
                label_parts.append(_capitalise(nested_desc))
                subs.append({
                    "id": f"{choice_id}:{this_slot}", "source": source,
                    "label": f"{label}: {_capitalise(nested_desc)}",
                    "description": f"Choose {nested.get('choose', 1)}: {nested_desc}.",
                    "count": nested.get("choose", 1), "options": nested_options,
                })
            else:
                resolvable = False
        if not resolvable:
            continue
        option_id = "+".join(id_parts)
        if option_id in seen:
            continue
        seen.add(option_id)
        quantities = _bundle_quantities(members) if keep_counts else {}
        options.append({"id": option_id, "label": " + ".join(label_parts),
                        **({"quantities": quantities} if quantities else {})})
        if subs:
            dependents[option_id] = subs
    if not options:
        return None, {}
    return {
        "id": choice_id, "source": source, "label": label, "description": desc,
        "count": envelope.get("choose", 1), "options": options,
    }, dependents
