"""RP19 (A2, open question 14, + Spells of the Mark): feat spell tables keyed by spell slot level. Pure functions.

Arcane Adept (8 Unearthed Arcana feats): "When you have spell slots of a level specified in the <School> Adept Spells
table, you thereafter always have the spells listed for that level and lower prepared." The converter keeps the table as
``slot_spells`` {slot level: [spell slug]}; the highest slot level is the larger of the shared pool and the Pact Magic
slot level, and every spell of the rows up to it becomes a ``sheet.innateSpells`` entry (always prepared, no class).

Spells of the Mark (12 EFA feats): "If you have the Spellcasting or Pact Magic class feature, the spells on the Mark of
<X> Spells table are added to that feature's spell list." The converter keeps the table as ``expanded_spells``; the
caller adds the spells up to each class's own highest castable level to that class's spell cards."""
from __future__ import annotations

ALWAYS_PREPARED = "always prepared"
MARK_LABEL = "Spells of the Mark"


def highest_slot_level(spell_slots: dict, pact_slots: dict) -> int:
    """The highest spell slot level of the character: the shared pool or the Pact Magic slots (both keyed by the slot
    level as a string, nonzero counts only)."""
    return max((int(k) for k in (*spell_slots, *pact_slots)), default=0)


def adept_entries(feats: list[dict], highest: int) -> list[dict]:
    """Catalog-shaped innate entries for the held feats' ``slot_spells`` rows 1..`highest`."""
    out: list[dict] = []
    for feat in feats:
        table = feat.get("slot_spells") or {}
        for level in sorted(n for n in table if n <= highest):
            for spell in table[level]:
                out.append({
                    "spell_id": spell, "name": spell.replace("-", " ").title(), "level": None, "uses": ALWAYS_PREPARED,
                    "ability": None, "variant": None, "source_label": feat["name"], "featId": feat["index"],
                    "note": f"{feat['name']}: spell slot level {level} row",
                })
    return out


def mark_spell_slugs(feats: list[dict], max_level: int) -> list[str]:
    """The ``expanded_spells`` slugs of the held feats up to spell level `max_level` (the highest slot level of ONE
    spellcasting class), without repeats."""
    out: list[str] = []
    for feat in feats:
        table = feat.get("expanded_spells") or {}
        for level in sorted(n for n in table if n <= max_level):
            out += [s for s in table[level] if s not in out]
    return out
