"""C9a: the 2024 (XPHB) class chassis proficiencies as full class dicts.

`convert_class_chassis_2024(records, srd_classes)` turns the XPHB class records
(`catalog.class_2024_records`: starting proficiencies, multiclass proficiencies, saving
throws) into `{class id: full merged class dict}`: `{**srd_class, ...overlay}`. The SRD dicts
are never mutated. The overlay keys are `proficiencies`, `proficiency_choices` and
`multi_classing` (the SRD prerequisites are kept; the proficiency lists are replaced), all in
the SRD shapes, so every consumer (`resolve()`'s class loop, the choice templates, the
proficiency block, the API) reads them unchanged. Equipment keys stay the SRD ones (C9b).

Mapping of the 5etools strings is strict: anything unmapped raises ValueError, so a data
change cannot silently drop a grant.

C9b adds the starting-equipment packages (`_class_equipment_options_2024`): the overlay's
`starting_equipment_options` is the XPHB A/B(/C) package envelope (flag `keep_counts`, decision E8)
and `starting_equipment` is []. A class record without usable `defaultData` keeps the SRD equipment."""
from __future__ import annotations

import re

from catalog.reference_data import (
    CLASS_2024_EQUIPMENT_ITEM_MAP,
    MARTIAL_FINESSE_LIGHT_PROFICIENCY_ID,
    MARTIAL_LIGHT_PROFICIENCY_ID,
    MONK_TOOL_SENTINEL,
    SKILL_NAMES,
    TOOLS,
    proficiency_label,
)

from .common import slug
from .equipment import _equipment_bundle_member_from_5etools
from .proficiencies import _skill_choice_envelope_from_5etools, _tool_choice_envelope_from_5etools

_ARMOR = {"light": "light-armor", "medium": "medium-armor", "heavy": "heavy-armor", "shield": "shields"}
_WEAPON = {"simple": "simple-weapons", "martial": "martial-weapons"}
_FILTER_PROPERTY = re.compile(r"\{@filter [^|}]*\|items\|type=martial weapon\|property=([a-z;]+)\}")
_FILTER_PROPERTY_IDS = {
    frozenset({"finesse", "light"}): MARTIAL_FINESSE_LIGHT_PROFICIENCY_ID,
    frozenset({"light"}): MARTIAL_LIGHT_PROFICIENCY_ID,
}
_TOOL_WILDCARD_CATEGORY = {"anyArtisansTool": "Artisan's Tools", "anyMusicalInstrument": "Musical Instrument"}
_NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def _entry(index: str) -> dict:
    if index.startswith("saving-throw-"):
        return {"index": index, "name": f"Saving Throw: {index[13:].upper()}", "url": ""}  # the SRD spelling
    return {"index": index, "name": proficiency_label(index), "url": ""}


def _armor_ids(values) -> list[str]:
    out = []
    for value in values or []:
        if value not in _ARMOR:
            raise ValueError(f"unmapped XPHB armor proficiency {value!r}")
        out.append(_ARMOR[value])
    return out


def _weapon_ids(values) -> list[str]:
    out = []
    for value in values or []:
        if value in _WEAPON:
            out.append(_WEAPON[value])
            continue
        match = _FILTER_PROPERTY.search(value) if isinstance(value, str) else None
        pseudo = _FILTER_PROPERTY_IDS.get(frozenset(match.group(1).split(";"))) if match else None
        if pseudo is None:
            raise ValueError(f"unmapped XPHB weapon proficiency {value!r}")
        out.append(pseudo)
    return out


def _is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _tools(entries) -> tuple[list[str], list[dict]]:
    """toolProficiencies -> (fixed tool ids, choice envelopes). A list of several wildcard entries
    is a set of ALTERNATIVES (the Monk's Artisan's Tool OR Musical Instrument): one options_array
    envelope holding every tool of those categories. One entry with a wildcard is one pick."""
    fixed: list[str] = []
    wild: list[tuple[str, int]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            raise ValueError(f"unmapped XPHB tool proficiency {entry!r}")
        for key, value in entry.items():
            if value is True:
                fixed.append(slug(key))
            elif key in _TOOL_WILDCARD_CATEGORY and _is_count(value):
                wild.append((key, value))
            else:
                raise ValueError(f"unmapped XPHB tool proficiency {key!r}: {value!r}")
    if len(wild) > 1 and len(entries) == len(wild):
        if len({n for _, n in wild}) != 1:
            raise ValueError("alternative tool wildcards with different counts")
        categories = {_TOOL_WILDCARD_CATEGORY[k] for k, _ in wild}
        options = [{"option_type": "reference", "item": {"index": t["index"], "name": t["name"], "url": ""}}
                   for t in TOOLS if t["category"] in categories]
        return fixed, [{"desc": "Choose one tool: an Artisan's Tool or a Musical Instrument.", "choose": wild[0][1],
                        "type": "proficiencies", "from": {"option_set_type": "options_array", "options": options}}]
    envelopes = []
    for key, count in wild:
        envelope = _tool_choice_envelope_from_5etools({key: count})
        envelope["desc"] = f"Choose {_NUMBER_WORDS.get(count, count)} {_TOOL_WILDCARD_CATEGORY[key].lower()}."
        envelopes.append(envelope)
    return fixed, envelopes


def _skill_envelopes(entries) -> list[dict]:
    out = []
    for entry in entries or []:
        envelope = _skill_choice_envelope_from_5etools(entry) if isinstance(entry, dict) else None
        if envelope is None:
            raise ValueError(f"unmapped XPHB skill proficiency {entry!r}")
        count = _NUMBER_WORDS.get(envelope["choose"], envelope["choose"])
        if envelope["from"]["option_set_type"] == "any_skill":
            envelope["desc"] = f"Choose any {count} skills."
        else:
            names = [SKILL_NAMES.get(o["item"]["index"], o["item"]["name"]) for o in envelope["from"]["options"]]
            envelope["desc"] = f"Choose {count} skills from {', '.join(names)}."
        out.append(envelope)
    return out


def _gained(block: dict, save_ids: list[str]) -> tuple[list[dict], list[dict]]:
    fixed_tools, tool_choices = _tools(block.get("toolProficiencies"))
    ids = _armor_ids(block.get("armor")) + _weapon_ids(block.get("weapons")) + fixed_tools + save_ids
    return [_entry(i) for i in ids], _skill_envelopes(block.get("skills")) + tool_choices


# ---- C9b: starting equipment packages ------------------------------------------------------

_NESTED_PICKS = {  # the nested "choice" member: (category index, category name, description)
    "holy symbol": ("holy-symbols", "Holy Symbols", "a holy symbol"),  # PHB ch. 6 table: Amulet / Emblem / Reliquary
    "instrumentMusical": ("musical-instruments", "Musical Instruments", "a musical instrument"),
}
_TAG = re.compile(r"\{@\w+ ([^}]*)\}")
_GOLD = re.compile(r"(\d+) GP")


def _nested_pick(key: str) -> dict:
    category, name, desc = _NESTED_PICKS[key]
    return {"option_type": "choice", "choice": {"desc": desc, "choose": 1, "type": "equipment", "from": {
        "option_set_type": "equipment_category",
        "equipment_category": {"index": category, "name": name, "url": ""}}}}


def _counted(index: str, name: str, count: int = 1) -> dict:
    return {"option_type": "counted_reference", "count": count, "of": {"index": index, "name": name, "url": ""}}


def _item_name_and_quantity(raw) -> tuple[str, int]:
    item = raw if isinstance(raw, str) else raw.get("item", "")
    return item.split("|", 1)[0].strip().lower(), (1 if isinstance(raw, str) else raw.get("quantity", 1))


def _equipment_member(raw) -> dict:
    """One 5etools package member -> an options_array member (counted_reference or nested choice)."""
    if isinstance(raw, dict):
        if "equipmentTypes" in raw:  # the Monk's "Artisan's Tools or Musical Instrument" (plural key)
            return _counted(MONK_TOOL_SENTINEL, "Artisan's Tools or Musical Instrument (chosen for the tool proficiency)")
        if raw.get("equipmentType") == "instrumentMusical":
            return _nested_pick("instrumentMusical")
        if raw.get("special") == "Spellbook":
            return _counted("spellbook", "Spellbook")
    if isinstance(raw, str) or "item" in raw:
        name, quantity = _item_name_and_quantity(raw)
        if name == "holy symbol":
            return _nested_pick("holy symbol")
        mapped = CLASS_2024_EQUIPMENT_ITEM_MAP.get(name)
        if mapped:
            index, per_unit = mapped
            label = {"arrow": "Arrows (20)", "robes": "Robes", "quarterstaff": "Druidic Focus (Quarterstaff)"}.get(index, index)
            return _counted(index, label, per_unit * quantity)
    member = _equipment_bundle_member_from_5etools(raw)
    index = member["of"]["index"] if member.get("option_type") == "counted_reference" else ""
    if index.startswith(("unlisted-", "category-", "flavor-")):
        raise ValueError(f"unmapped XPHB starting equipment member {raw!r}")
    return member


def _strip_tags(text: str) -> str:
    def plain(match):
        parts = match.group(1).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return _TAG.sub(plain, text)


def _class_equipment_options_2024(raw: dict) -> list[dict] | None:
    """The XPHB `startingEquipment` -> [one SRD-shaped envelope] (A/B, Fighter A/B/C), or None when
    the record has no usable package (the SRD equipment is then kept). Gold comes from the data,
    unless the record's own `entries` line gives another amount: the text wins (the Cleric A value
    is 7000 cp = 70 GP while its line says "7 GP")."""
    data = (raw or {}).get("defaultData") or []
    if not (data and isinstance(data[0], dict)):
        return None
    entries = [e for e in (raw.get("entries") or []) if isinstance(e, str)]
    text = _strip_tags(entries[0]) if entries else ""
    segments = re.split(r"\(([A-Z])\)", text)[1:]
    text_gold = {segments[i]: _GOLD.search(segments[i + 1]) for i in range(0, len(segments) - 1, 2)}
    options = []
    for letter in sorted(k for k in data[0] if len(k) == 1 and k.isalpha()):
        items = []
        for member in data[0][letter]:
            if isinstance(member, dict) and "value" in member:
                match = text_gold.get(letter)
                gold = int(match.group(1)) if match else member["value"] // 100
                items.append(_counted(f"gp-{gold}", f"{gold} GP"))
            else:
                items.append(_equipment_member(member))
        options.append({"option_type": "multiple", "items": items})
    if not options:
        return None
    return [{"desc": text, "choose": 1, "type": "equipment", "keep_counts": True,
             "from": {"option_set_type": "options_array", "options": options}}]


def convert_class_chassis_2024(records: dict, srd_classes: dict) -> dict[str, dict]:
    """{class id: full merged class dict} for every XPHB record that has an SRD class."""
    out: dict[str, dict] = {}
    for cls_id, record in (records or {}).items():
        srd = (srd_classes or {}).get(cls_id)
        if srd is None:
            continue
        saves = [f"saving-throw-{a}" for a in record.get("saving_throws") or []]
        proficiencies, choices = _gained(record.get("starting_proficiencies") or {}, saves)
        mc_proficiencies, mc_choices = _gained((record.get("multiclassing") or {}).get("proficienciesGained") or {}, [])
        out[cls_id] = {
            **srd,
            "proficiencies": proficiencies,
            "proficiency_choices": choices,
            "multi_classing": {**(srd.get("multi_classing") or {}),
                               "proficiencies": mc_proficiencies, "proficiency_choices": mc_choices},
        }
        equipment = _class_equipment_options_2024(record.get("starting_equipment") or {})
        if equipment is not None:  # C9b
            out[cls_id]["starting_equipment_options"] = equipment
            out[cls_id]["starting_equipment"] = []
    return out


# ---- C6d: XPHB class `additionalSpells` ----------------------------------------------------

# Spells that the XPHB data lists as always prepared but whose text does not say so.
# Druid 2 Find Familiar (decision E9): Wild Companion only reads "As a Magic action, you can expend a
# spell slot or a use of Wild Shape to cast the Find Familiar spell without Material components."; the
# spell is never "always prepared", so it is not granted. (Druid 1 Speak with Animals stays: Druidic says
# "you always have the Speak with Animals spell prepared".)
_NOT_ALWAYS_PREPARED = {("druid", 2): {"find-familiar"}}


def convert_class_spell_grants_2024(records: dict, resolve_spell) -> dict[str, dict]:
    """{class id: {"always": {class level: [spell ids]}, "expanded": {level key: parsed filter}}}
    from the raw `additional_spells` of the XPHB class records. `resolve_spell` maps a spell slug
    to a catalog spell id or None (the `|xphb` spells resolve to `-xphb` ids). Spells that do not
    resolve and filters that do not parse are dropped (an SRD-only catalog gives {}); classes
    with nothing left are omitted. `expanded` keys are the XPHB ones: a class level ("10") or
    "s<N>" for spell slot level N."""
    from .feats import _parse_spell_filter

    out: dict[str, dict] = {}
    for cls_id, record in (records or {}).items():
        always: dict[int, list[str]] = {}
        expanded: dict[str, dict] = {}
        for block in record.get("additional_spells") or []:
            if not isinstance(block, dict):
                continue
            prepared = block.get("prepared") if isinstance(block.get("prepared"), dict) else {}
            for level_key, names in prepared.items():
                if not (str(level_key).isdigit() and isinstance(names, list)):
                    continue
                level = int(level_key)
                for name in names:
                    if not isinstance(name, str):
                        continue
                    base = slug(name.split("|")[0])
                    if base in _NOT_ALWAYS_PREPARED.get((cls_id, level), ()):
                        continue
                    spell_id = resolve_spell(base + "-xphb") or resolve_spell(base)
                    if spell_id and spell_id not in always.setdefault(level, []):
                        always[level].append(spell_id)
            for level_key, items in (block.get("expanded") or {}).items() if isinstance(block.get("expanded"), dict) else ():
                for item in items if isinstance(items, list) else []:
                    text = item.get("all") if isinstance(item, dict) else None
                    parsed = _parse_spell_filter(text) if isinstance(text, str) else None
                    if parsed:
                        expanded[str(level_key)] = parsed
        always = {lvl: ids for lvl, ids in always.items() if ids}
        if always or expanded:
            out[cls_id] = {"always": always, "expanded": expanded}
    return out
