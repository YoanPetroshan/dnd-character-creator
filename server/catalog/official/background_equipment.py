"""RP9 (C, E12): 2024 background starting equipment with real items and quantities.

`starting_equipment_options_2024_from_5etools(raw, proficiency_choices)` converts the `startingEquipment` of a
ruleset-2024 background record into SRD-shaped A/B envelopes flagged `keep_counts` (same flag and member shapes as
the C9b class packages). It is stored under the ADDITIVE catalog key `starting_equipment_options_2024`; the old
`starting_equipment_options` is untouched and mixed / 2014 keep reading it. `resolve()` reads the new key under
ruleset 2024 only.

Rules (the `Equipment:` line of the record is the governing text):
  * counts are kept ("2 Pouches", "5 Torches", "Oil (5 flasks)", "Parchment (10 sheets)");
  * "Robe" / "Arrows (20)" / "Bolts (20)" / "Iron Spikes": `reference_data.BACKGROUND_2024_EQUIPMENT_ITEM_MAP`;
  * "Holy Symbol" -> nested pick over the holy symbols ("(reliquary)" -> the Reliquary), "Arcane Focus (Crystal
    or Wand)" -> nested pick over the arcane foci narrowed by `from.only`;
  * a gaming set / artisan's tools / musical instrument: the sentinel `background-tool` when the background has a
    tool proficiency pick of that category ("same as above"), otherwise a nested pick of that category;
  * "Map" (no catalog item) -> a narrative `flavor-map` member;
  * the gold amount comes from the text line when it is there (text wins; Mulhorandi Tomb Raider lost its "26 GP"
    into a display name in the data);
  * anything else unmapped raises ValueError (strict, like C9a / C9b).
"""
from __future__ import annotations

import re

from catalog.reference_data import (
    BACKGROUND_2024_EQUIPMENT_ITEM_MAP,
    BACKGROUND_2024_NARRATIVE_ITEMS,
    BACKGROUND_TOOL_SENTINEL,
)

from .class_chassis import _counted, _strip_tags
from .common import slug
from .equipment import _equipment_bundle_member_from_5etools, _find_srd_equipment_item

# kind -> (tool category of catalog.reference_data.TOOLS, equipment category index, category name, description,
# sentinel label)
_TOOL_KINDS = {
    "gaming": ("Gaming Sets", "gaming-sets", "Gaming Sets", "a gaming set", "Gaming Set"),
    "artisan": ("Artisan's Tools", "artisans-tools", "Artisan's Tools", "an artisan's tool", "Artisan's Tools"),
    "instrument": ("Musical Instrument", "musical-instruments", "Musical Instruments", "a musical instrument",
                   "Musical Instrument"),
}
_EQUIPMENT_TYPE_KIND = {"setGaming": "gaming", "toolArtisan": "artisan", "instrumentMusical": "instrument"}
_NAME_KIND = {"gaming set": "gaming", "musical instrument": "instrument"}
_GOLD_AT_END = re.compile(r",?\s*(?:and\s+)?(\d+) GP\s*$")
_COUNT_IN_LABEL = re.compile(r"\((\d+)\s+(?:flasks?|sheets?)\)", re.I)


def _nested(category: str, name: str, desc: str, only: list[str] | None = None) -> dict:
    from_field = {"option_set_type": "equipment_category",
                  "equipment_category": {"index": category, "name": name, "url": ""}}
    if only:
        from_field["only"] = only
    return {"option_type": "choice", "choice": {"desc": desc, "choose": 1, "type": "equipment", "from": from_field}}


def _equipment_line(raw: dict) -> str:
    """The stripped `Equipment:` entry of the record ("" when it has none)."""
    for entry in raw.get("entries") or []:
        for item in (entry.get("items") or []) if isinstance(entry, dict) else []:
            if isinstance(item, dict) and str(item.get("name", "")).startswith("Equipment"):
                return _strip_tags(item.get("entry") or "")
    return ""


def _text_gold(line: str) -> dict[str, int]:
    """{letter: gold} of the `(A) ..., N GP; or (B) 50 GP` line."""
    segments = re.split(r"\(([A-Z])\)", line)[1:]
    out = {}
    for i in range(0, len(segments) - 1, 2):
        match = _GOLD_AT_END.search(segments[i + 1].split(";")[0].strip())
        if match:
            out[segments[i]] = int(match.group(1))
    return out


def _text_tokens(line: str, letter: str) -> list[str]:
    """The item tokens of package `letter` of the text line (the gold part removed)."""
    segments = re.split(r"\(([A-Z])\)", line)[1:]
    for i in range(0, len(segments) - 1, 2):
        if segments[i] == letter:
            seg = segments[i + 1].split(";")[0].strip()
            gold = _GOLD_AT_END.search(seg)
            return [t.strip() for t in re.split(r",\s*", seg[:gold.start()] if gold else seg) if t.strip()]
    return []


def _text_count(token: str) -> int:
    """The quantity a text token states: a leading number ("2 Pouches"), "(N flasks|sheets|days)"; "20 Arrows" and
    "20 Bolts" are ONE unit of the 20-pack catalog item; otherwise 1."""
    if re.match(r"20 (Arrows|Bolts)\b", token):
        return 1
    lead = re.match(r"(\d+) ", token)
    inner = re.search(r"\((\d+)\s+(?:flasks?|sheets?|days)", token)
    return int(lead.group(1)) if lead else int(inner.group(1)) if inner else 1


def _tool_categories(proficiency_choices: list[dict]) -> set[str]:
    """The tool categories of the background's `any_tool` proficiency picks."""
    return {(e.get("from") or {}).get("tool_category") for e in proficiency_choices or []
            if (e.get("from") or {}).get("option_set_type") == "any_tool" and (e.get("from") or {}).get("tool_category")}


def _tool_member(kind: str, categories: set[str]) -> dict:
    category, index, name, desc, label = _TOOL_KINDS[kind]
    if category in categories:
        return _counted(BACKGROUND_TOOL_SENTINEL, f"{label} (same as the tool proficiency)")
    return _nested(index, name, desc)


def _member(raw, categories: set[str]) -> dict:
    """One 5etools package member -> an options_array member."""
    if isinstance(raw, dict) and "value" in raw:
        gold = raw["value"] // 100
        return _counted(f"gp-{gold}", f"{gold} GP")
    if isinstance(raw, dict) and "equipmentType" in raw:
        kind = _EQUIPMENT_TYPE_KIND.get(raw["equipmentType"])
        if kind is None:
            raise ValueError(f"unmapped background starting equipment member {raw!r}")
        return _tool_member(kind, categories)
    if isinstance(raw, dict) and "item" not in raw:
        raise ValueError(f"unmapped background starting equipment member {raw!r}")
    item = raw if isinstance(raw, str) else raw["item"]
    name = item.split("|", 1)[0].strip().lower()
    display = "" if isinstance(raw, str) else (raw.get("displayName") or "")
    quantity = 1 if isinstance(raw, str) else raw.get("quantity")
    if quantity is None:
        match = _COUNT_IN_LABEL.search(display)
        quantity = int(match.group(1)) if match else 1
    if name in _NAME_KIND:
        return _tool_member(_NAME_KIND[name], categories)
    if name == "holy symbol":
        if "reliquary" in display.lower():
            return _counted("reliquary", "Reliquary")
        return _nested("holy-symbols", "Holy Symbols", "a holy symbol")
    if name == "arcane focus":
        inner = re.search(r"\(([^)]*)\)", display)
        only = [slug(p) for p in re.split(r"\s+or\s+|,", inner.group(1)) if p.strip()] if inner else None
        return _nested("arcane-foci", "Arcane Foci", "an arcane focus", only)
    if name in BACKGROUND_2024_NARRATIVE_ITEMS:
        label = BACKGROUND_2024_NARRATIVE_ITEMS[name]
        return _counted(f"flavor-{slug(label)}", label, quantity)
    mapped = BACKGROUND_2024_EQUIPMENT_ITEM_MAP.get(name)
    if mapped:
        index, per_unit, label = mapped
        return _counted(index, label, per_unit * quantity)
    srd = _find_srd_equipment_item(name)
    if srd is None:
        raise ValueError(f"unmapped background starting equipment member {raw!r}")
    return _counted(srd["index"], srd["name"], quantity)


def starting_equipment_options_2024_from_5etools(raw: dict, proficiency_choices: list[dict]) -> list[dict]:
    """The 2024 A/B envelopes of one background record (see the module docstring); [] without a package."""
    categories = _tool_categories(proficiency_choices)
    line = _equipment_line(raw)
    text_gold = _text_gold(line)
    envelopes = []
    for entry in raw.get("startingEquipment") or []:
        keys = sorted((k for k in entry if k.lower() in ("a", "b", "c", "d")), key=str.lower)
        if not keys:
            continue
        options = []
        for key in keys:
            items = [_member(m, categories) for m in entry[key]]
            tokens = _text_tokens(line, key.upper())
            item_slots = [i for i, m in enumerate(items) if not m.get("of", {}).get("index", "").startswith("gp-")]
            if tokens and len(tokens) == len(item_slots):
                # the text states the quantities: it wins over the data (Scribe lost "3 flasks" and "12 sheets")
                for slot, token in zip(item_slots, tokens):
                    if items[slot]["option_type"] == "counted_reference" and items[slot]["of"]["index"] != BACKGROUND_TOOL_SENTINEL:
                        items[slot] = {**items[slot], "count": _text_count(token)}
            gold = text_gold.get(key.upper())
            have_gold = [i for i, m in enumerate(items) if m.get("of", {}).get("index", "").startswith("gp-")]
            if gold is not None:
                gold_member = _counted(f"gp-{gold}", f"{gold} GP")
                if have_gold:
                    items[have_gold[0]] = gold_member
                else:
                    items.append(gold_member)
            options.append({"option_type": "multiple", "items": items})
        envelopes.append({
            "desc": line, "choose": 1, "type": "equipment", "keep_counts": True,
            "from": {"option_set_type": "options_array", "options": options},
        })
    return envelopes
