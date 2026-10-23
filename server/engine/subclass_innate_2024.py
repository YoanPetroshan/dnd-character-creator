"""RP18 (F4): innate spells of the XPHB subclasses, ruleset "2024" only.

  Wild Heart (Beast Sense, Speak with Animals, Commune with Nature as Rituals), Glamour (Command), Psi Warrior
  (Telekinesis), Warrior of Shadow (Darkness for a Focus Point), Archfey (Misty Step), Diviner (See Invisibility)
      -> `sheet.innateSpells` entries, source = the subclass name
  Great Old One (Hex)  "You always have the Hex spell prepared." -> an always-prepared spell, not a free cast

The data is `reference_data.SUBCLASS_INNATE_2024` (what the text means, verbatim quotes pinned by tests) plus the
catalog subclass record's `innate_spells` (converter key of `catalog/official/subclasses.py`: which spell at which class
level). An entry needs the XPHB feature record, the selected subclass and the class level at that record's level, so an
SRD-only catalog, a catalog without the converter key, mixed / 2014 or a missing subclass give nothing. Pure: resolve()
turns the raw entries into sheet entries (`_innate_entry_to_sheet`)."""
from __future__ import annotations

from catalog import reference_data


def _data_spells(catalog, spec: dict, record: dict) -> list[str]:
    """Catalog spell ids of `spec` that the subclass record's `innate_spells` data lists at the feature's level."""
    sub = catalog.subclasses.get(spec["subclass"]) or {}
    at_level = {e["spell"] for e in sub.get("innate_spells") or []
                if (e["level"] if e["level"] is not None else record["level"]) == record["level"]}
    out = []
    for slug_ in spec["spells"]:
        spell_id = catalog.resolve_spell_id(slug_ + "-xphb")
        if spell_id in at_level and spell_id in catalog.spells:
            out.append(spell_id)
    return out


def _applicable(catalog, resolved_classes: list[dict], ruleset: str, mode: str):
    """[(feature id, spec, feature record, class level)] of the `mode` entries whose subclass is selected and level reached."""
    if ruleset != "2024":
        return []
    out = []
    for fid, spec in reference_data.SUBCLASS_INNATE_2024.items():
        if spec["mode"] != mode:
            continue
        record = catalog.features.get(fid)
        if not record:
            continue
        for rc in resolved_classes:
            if (rc.get("cls") and rc.get("cls_id") == spec["class"] and rc.get("subclass_id") == spec["subclass"]
                    and rc["level"] >= (record.get("level") or 1)):
                out.append((fid, spec, record, rc["level"]))
                break
    return out


def innate_entries(catalog, resolved_classes: list[dict], ruleset: str, modifiers: dict[str, int]) -> list[dict]:
    """Raw innate-spell entries (catalog shape, plus `note` and `source_label` = the subclass name) in table order."""
    out = []
    for fid, spec, record, _level in _applicable(catalog, resolved_classes, ruleset, "innate"):
        sub = catalog.subclasses[spec["subclass"]]
        for spell_id in _data_spells(catalog, spec, record):
            out.append({
                "spell_id": spell_id, "name": catalog.spells[spell_id]["name"], "level": record["level"],
                "uses": spec["uses"].format(cha_min1=max(1, modifiers.get("CHA", 0))),
                "ability": spec["ability"], "variant": None, "note": spec.get("note"), "source_label": sub["name"]})
    return out


def prepared_spell_ids(catalog, sub_record: dict, cls_id: str, class_level: int) -> list[str]:
    """Spells the subclass always prepares through its `prepared` innate entries (Eldritch Hex). Only a record that carries
    the converter key (an XPHB subclass) can match; the caller decides the ruleset by which subclass is selected."""
    out = []
    for fid, spec in reference_data.SUBCLASS_INNATE_2024.items():
        record = catalog.features.get(fid)
        if (spec["mode"] != "prepared" or not record or spec["subclass"] != sub_record.get("index")
                or spec["class"] != cls_id or class_level < (record.get("level") or 1)):
            continue
        out += [s for s in _data_spells(catalog, spec, record) if s not in out]
    return out
