"""S3: option descriptions the engine writes itself, from structured data or in our own words (never the book's text):
the species lineage / ancestry summary (+ the book row text stored as `variants[].text`), the Circle of the Land spell list,
Elemental Affinity. English is the Msg text; the Bulgarian is rendered from the message catalog (i18n/catalog/option_texts.py).
Only the book row text (`variants[].text`, one paragraph per line) goes through the `choice-texts` overlay, line by line."""
from __future__ import annotations

from catalog.reference.subclass_picks import DTYPE_MSG
from i18n.messages import msg



def _metres(feet: int) -> str:
    value = round(feet * 0.3, 1)
    return str(int(value)) if value == int(value) else str(value).replace(".", ",")


def variant_summary(variant: dict):
    """The generated summary line of a species variant (speed, Darkvision, Resistance, innate spells), or None."""
    parts = []
    if isinstance(variant.get("speed"), int):
        parts.append(msg("opt-speed", n=variant["speed"], m=_metres(variant["speed"])))
    if isinstance(variant.get("darkvision"), int) and variant["darkvision"]:
        parts.append(msg("opt-darkvision", n=variant["darkvision"], m=_metres(variant["darkvision"])))
    if variant.get("resist"):
        parts.append(msg("opt-resist", types=[DTYPE_MSG[t]() for t in variant["resist"] if t in DTYPE_MSG]))
    if variant.get("innate_spells"):
        parts.append(msg("opt-spells", spells=[msg("opt-spell", name=s["name"], level=s["level"]) for s in variant["innate_spells"]]))
    return msg("opt-summary", parts=parts) if parts else None


def variant_description(variant: dict):
    """summary line + "\\n" + the book row text; either alone; None when there is neither."""
    summary, text = variant_summary(variant), variant.get("text") or ""
    if summary and text:
        return msg("opt-variant", summary=summary, text=text)
    return summary or text or None


def affinity_description(damage: str):
    return msg("opt-affinity", dtype=DTYPE_MSG[damage]())


def land_description(catalog, variant: str):
    """The spells a land gives, by Druid level, from the subclass `spells_by_variant`; None when the data has none."""
    sub = catalog.subclasses.get("land-xphb") or {}
    by_level: dict[int, list[str]] = {}
    for entry in (sub.get("spells_by_variant") or {}).get(variant) or []:
        level = next((int(p["index"].rsplit("-", 1)[1]) for p in entry.get("prerequisites") or [] if p.get("type") == "level"), None)
        spell = catalog.spells.get((entry.get("spell") or {}).get("index"))
        if level is not None and spell:
            by_level.setdefault(level, []).append(spell["name"])
    if not by_level:
        return None
    return msg("opt-land", levels=[msg("opt-land-level", level=lv, names=names) for lv, names in sorted(by_level.items())])
