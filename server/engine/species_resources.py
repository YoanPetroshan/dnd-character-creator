"""W5a (F2): ``derived.speciesResources``, species traits with a use count, a rest rule or numbers.

Pure: driven by ``reference_data.SPECIES_RESOURCES`` (keyed by catalog trait id, quote-pinned by the tests) and the
species the character holds. The entry shape is the class / feat resource shape minus ``classId``, plus ``traitId``
and ``speciesId``, with ``source = {kind: "species", id: <species id>, label: <species name>}``. Breath Weapon-like
traits are resources with ``dc`` / ``dice`` and ``details`` (decision D-2), never attack rows."""
from __future__ import annotations

from catalog import reference_data


def _slug(text: str) -> str:
    return "-".join("".join(ch if ch.isalnum() else " " for ch in text.lower()).split())


def _dice_for(table: tuple, level: int) -> str:
    dice = table[0][1]
    for first, value in table:
        if level >= first:
            dice = value
    return dice


_ABILITY_WORD = {"STR": "Strength", "DEX": "Dexterity", "CON": "Constitution", "INT": "Intelligence", "WIS": "Wisdom",
                 "CHA": "Charisma"}


def _spec_for(tid: str) -> dict | None:
    return reference_data.SPECIES_RESOURCES.get(tid) or reference_data.SPECIES_RESOURCES_2014.get(tid)


def _selected(choices, choice_id: str) -> str | None:
    for c in choices or []:
        if c.get("id") == choice_id and c.get("selected"):
            return c["selected"][0]
    return None


def _unpicked_note(template: str, srd: bool) -> str:
    """WF: the note template of an ancestry-typed trait while the ancestry is not picked: the damage type is dropped from
    the sentence and the player is told what to choose. The SRD Dragonborn also lacks the save and the area."""
    if srd:
        template = template.replace("exhale in {shape}, {save} saving throw, ", "exhale destructive energy, ")
    template = template.replace(" {damage_type} damage", " damage").replace(" ({damage_type})", "")
    return template + "; choose your Draconic Ancestry to see the damage type" + (", area and save" if srd else "")


def resources(catalog, race: dict | None, race_id: str | None, subrace: dict | None, variant: dict | None,
              total_level: int, pb: int, modifiers: dict, walk_speed: int | None, choices=None) -> list[dict]:
    """One entry per table trait the species (race + subrace trait refs) holds at the character's total level.
    `choices`: the resolved choice cards (the SRD Dragonborn's Draconic Ancestry and the PHB Dragonborn's resistance
    pick live there, not on a species variant)."""
    if not race or not race_id:
        return []
    refs = list(race.get("traits") or []) + list((subrace or {}).get("racial_traits") or [])
    out: list[dict] = []
    seen: set[str] = set()
    for ref in refs:
        tid = ref.get("index")
        spec = _spec_for(tid)
        if not spec or tid in seen or spec["race"] != race_id or tid not in catalog.traits:
            continue
        seen.add(tid)
        if total_level < spec.get("level", 1):
            continue
        con_mod = modifiers.get("CON", 0)
        values = {"pb": pb, "two_pb": 2 * pb, "level": total_level, "con_mod": con_mod,
                  "speed_part": f" ({walk_speed} feet)" if walk_speed else "", "hop": 5 * pb,
                  "half_level_up": (total_level + 1) // 2, "con_temp": max(1, con_mod),
                  "shift_temp": max(1, total_level + con_mod)}
        details: dict = {}
        entry = {"id": f"species:{race_id}:{_slug(spec['name'])}", "speciesId": race_id, "traitId": tid,
                 "source": {"kind": "species", "id": race_id, "label": race.get("name") or race_id},
                 "name": spec["name"], "uses": pb if spec["uses"] == "pb" else spec["uses"],
                 "recharge": spec["recharge"]}
        if spec.get("dc"):
            entry["dc"] = 8 + modifiers.get(spec["dc"], 0) + pb
            if spec.get("save"):
                details["save"] = spec["save"]
        srd_breath = None
        unpicked_ancestry = False
        note_template = spec["note"]
        if spec.get("srd_ancestry"):  # SRD Dragonborn: the picked ancestry subtrait carries the save, area and damage type
            sub_id = _selected(choices, f"species:{race_id}:trait:draconic-ancestry")
            srd_breath = ((catalog.traits.get(sub_id) or {}).get("trait_specific") or {}).get("breath_weapon") if sub_id else None
            if srd_breath:
                save = srd_breath["dc"]["dc_type"]["index"].upper()
                area = srd_breath["area_of_effect"]
                details["save"] = save
                values["save"] = _ABILITY_WORD[save]
                details["shape"] = values["shape"] = f"a {area['size']}-foot {area['type']}"
            else:
                values["save"] = "a saving throw (set by your Draconic Ancestry)"
                values["shape"] = "the area set by your Draconic Ancestry"
        if spec.get("dice_by_level"):
            entry["dice"] = values["dice"] = _dice_for(spec["dice_by_level"], total_level)
        if spec.get("die"):
            entry["die"] = spec["die"]
        if spec.get("shape"):
            details["shape"] = values["shape"] = spec["shape"]
        phb_row = None
        if spec.get("phb_ancestry"):  # B1: the PHB Dragonborn's Draconic Ancestry card (the dragon colour) decides all three
            phb_row = reference_data.DRACONIC_ANCESTRY_PHB.get(_selected(choices, f"species:{race_id}:draconic-ancestry"))
            if phb_row:
                details["save"] = phb_row["save"]
                values["save"] = _ABILITY_WORD[phb_row["save"]]
                length = f"{phb_row['length']}-foot {phb_row['shape']}"
                details["shape"] = values["shape"] = (f"a {length} that is {phb_row['width']} feet wide" if phb_row["width"]
                                                      else f"a {length}")
        if spec.get("damage_type") == "ancestry":
            picked = ((variant or {}).get("resist") or [None])[0]
            if phb_row:
                picked = phb_row["damage"]
            if not picked and srd_breath:
                picked = srd_breath["damage"][0]["damage_type"]["index"]
            elif not picked:  # PHB Dragonborn: the species resistance pick is the ancestry's damage type
                picked = _selected(choices, f"species:{race_id}:resistance")
            details["damageType"] = picked
            if picked:
                values["damage_type"] = picked.capitalize()
            else:
                unpicked_ancestry = True
                values["damage_type"] = ""
        if spec.get("heal"):
            details["heal"] = spec["heal"].format(**values)
        if spec.get("giant_ancestry"):
            boon = reference_data.GIANT_ANCESTRY_2024.get((variant or {}).get("id"))
            values["ancestry"] = (f"{boon['name']}: {boon['note'].format(**values)}" if boon
                                  else "choose a Giant Ancestry")
        if unpicked_ancestry:  # WF: no ancestry yet: say so instead of splicing placeholder words into the sentence
            note_template = _unpicked_note(note_template, bool(spec.get("srd_ancestry") and not srd_breath))
        if phb_row:
            note_template = spec["note_picked"]
        details["note"] = note_template.format(**values)
        entry["details"] = details
        out.append(entry)
    return out
