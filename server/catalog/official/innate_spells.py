"""Split from official_source.py (Slice 11.0), unchanged code: innate_spells."""
from __future__ import annotations

from .common import slug


def _clean_innate_spell_name(raw: str) -> str:
    """Strips 5etools' spell-reference decorations from an
    additionalSpells.innate spell-name string: a trailing "|source" (e.g.
    "light|xphb", confirmed against Elf/XPHB's Drow legacy) and a trailing
    "#c"/"#<digit>" render tag (e.g. "hellish rebuke#2", confirmed against
    Tiefling/PHB — 5etools uses this to mark "display as a cantrip" vs.
    "display as cast at a specific slot level"; it does not change which
    catalog spell this resolves to, so it's dropped along with "|source").
    Confirmed empirically (2026-09-24) against every real innate-spell
    reference in races.json that both decorations only ever appear as a
    SUFFIX, never combined with anything else worth preserving."""
    return raw.split("|", 1)[0].split("#", 1)[0].strip()


def _innate_spell_uses_and_names(level_value) -> tuple[str, list[str]]:
    """Converts ONE additionalSpells[].innate[level] value into a
    (uses-label, raw spell-name list) pair.

    Confirmed empirically (2026-09-24, re-verified 2026-09-24 after a code
    review caught a counterexample the first pass missed) against every
    real race AND subrace innate-spell entry in races.json: three shapes
    exist at this level —
    - a plain list of spell-name strings (e.g. Firbolg/MPMM's level-1
      entry, `["detect magic", "disguise self"]`) — no frequency wrapper
      at all means the real 5e rule is "at will" (e.g. Firbolg can cast
      Detect Magic/Disguise Self on itself at will; Yuan-Ti's Animal
      Friendship at will), confirmed against 5etools' own convention and
      cross-checked against the actual PHB/MPMM rules text for several of
      these races.
    - `{"daily": {"1": [...]}}` — usable a limited number of times per
      long rest. This is the overwhelming majority shape (96/97 real
      dict-wrapped entries across races AND subraces).
    - `{"rest": {"1": [...]}}` — the ONE real exception (Mark of
      Scribing/ERLW, a subrace of Gnome/PHB, level 1: `{"rest": {"1":
      ["comprehend languages"]}}`). The PREVIOUS version of this
      docstring claimed the wrapper key was "ALWAYS daily" — that claim
      was false, disproven by this exact record in this exact file.
      Mark of Scribing's own flavor text ("you can also cast comprehend
      languages once with this trait, and you regain the ability to cast
      it when you finish a short OR long rest") confirms "rest" means a
      short-or-long-rest recharge, a real but slightly more generous
      mechanic than "daily"'s long-rest-only cadence. This module still
      only models two uses-labels ("at-will" and "1/day"), so "rest" is
      treated identically to "daily" here — "1/day" undercounts the true
      short-rest cadence slightly but is far more accurate than the
      previous behavior (silently dropping the spell entirely). Modeling
      a distinct "short rest" uses-label is out of scope for this pass.
      In both shapes the inner count key is ALWAYS "1" for every real
      `innate` entry in the whole dataset — so this module only needs to
      model "1/day", not a general N/day. (5etools' OTHER field, `known`,
      also uses a "rest" wrapper on a few races — e.g. Firbolg/VGM,
      Eladrin/DMG, Mark of Handling/ERLW — but `known` is a different
      mechanic, out of scope for this task; see module-level Task 6
      docstring.)

    A shape this doesn't recognize (defensively, not seen in real data)
    returns ("at-will", []) rather than raising, so a future data update
    with an unanticipated shape silently contributes zero spells instead
    of crashing the whole conversion."""
    if isinstance(level_value, list):
        return "at-will", [n for n in level_value if isinstance(n, str)]
    if isinstance(level_value, dict):
        wrapper = level_value.get("daily")
        if not isinstance(wrapper, dict):
            wrapper = level_value.get("rest")
        if isinstance(wrapper, dict):
            names = wrapper.get("1")
            if isinstance(names, list):
                return "1/day", [n for n in names if isinstance(n, str)]
    return "at-will", []


def _innate_spell_ability(ability_raw) -> str | dict | None:
    """Converts additionalSpells[].ability — the spellcasting ability
    innate spells use for save DC/attack bonus — into either a fixed
    ability index string ("CHA") or, for the MAJORITY real shape
    (confirmed empirically, 2026-09-24: roughly three-quarters of real
    innate-spell-carrying entries use this, not the fixed-string form),
    a `{"choose": [...]}` list of candidate abilities the player picks
    from (e.g. Aarakocra/MPMM: `{"choose": ["int", "wis", "cha"]}`).

    Race candidate lists are carried through as descriptive data. For feats
    the list is resolved by engine.resolve's `{prefix}:spell-ability`
    Choice (see _feat_spell_choice_templates); feat text can also override
    it via _feat_spell_ability_override."""
    if isinstance(ability_raw, str):
        return ability_raw.upper()
    if isinstance(ability_raw, dict) and isinstance(ability_raw.get("choose"), list):
        options = [a.upper() for a in ability_raw["choose"] if isinstance(a, str)]
        if options:
            return {"choose": options}
    return None


def _known_cantrips(known, ability, variant) -> list[dict]:
    """G6: the fixed cantrips of an `additionalSpells[].known` block ("known": {"1": ["thaumaturgy#c"]}, the PHB Tiefling's
    Thaumaturgy, the Drow's Dancing Lights, the Aasimar's Light ...) as at-will innate grants, with the entry's ability and
    variant tag. Only a plain string flagged "#c" (5etools' cantrip tag) is read; every other `known` shape is a different
    mechanic and stays out: a spell without "#c" (Eladrin Misty Step, Mark of Warding Alarm / Mage Armor, Deep Gnome),
    a `rest` / `choose` object (the High Elf's cantrip pick, Firbolg Hidden Step ...)."""
    out: list[dict] = []
    if not isinstance(known, dict):
        return out
    for level_key, names in known.items():
        try:
            level = int(level_key)
        except (TypeError, ValueError):
            continue
        if not isinstance(names, list):
            continue
        for raw_name in names:
            if not (isinstance(raw_name, str) and raw_name.endswith("#c")):
                continue
            clean = _clean_innate_spell_name(raw_name)
            if clean:
                out.append({"name": clean.title(), "spell_id": slug(clean), "level": level, "uses": "at-will",
                            "ability": ability, "variant": variant})
    return out


def _innate_spells_from_5etools(race_raw: dict) -> list[dict]:
    """Converts 5etools' `additionalSpells` field into a flat list of
    innate-spell grants — ONLY the `innate` sub-key of each entry (this
    task's actual scope, "Innate spellcasting"); the sibling `known`/
    `prepared`/`expanded` sub-keys are a real but DIFFERENT mechanic
    (always-known cantrips/spells, Warlock-style always-prepared lists,
    and Mark-of-X's "adds spells to your class spell list" respectively —
    confirmed present in the real data, e.g. Aasimar's Light cantrip
    lives in `known`, not `innate`) and are a disclosed, narrower cut,
    not modeled by this function.

    `additionalSpells` is a LIST, not a single dict — confirmed
    empirically (2026-09-24) that most real races have exactly one entry,
    but a real few (Elf/XPHB: Drow/High Elf/Wood Elf; Tiefling/XPHB:
    Abyssal/Chthonic/Infernal — both reviewer-confirmed to actually reach
    this code and exercise this path end-to-end) have MULTIPLE entries,
    each carrying a "name" tag, representing mutually exclusive
    player-chosen variants (2024-style "lineage" options folded into one
    race record rather than modeled as separate subraces — confirmed no
    subrace records exist for these). Elf/LFL (Lorwyn/Shadowmoor) also has
    this multi-entry shape in the raw data, but it's a "_copy"-based
    record (see module docstring / _race_from_5etools) that
    _race_from_5etools filters out before this function is ever called on
    it — it was wrongly cited here as a "confirmed" example in an earlier
    pass despite never actually being exercised by this pipeline; dropped
    from this list for that reason. Silently flattening every entry's
    grants together would misrepresent a character as having ALL variants
    at once, which is worse than a disclosed cut. Instead, every grant is
    tagged with its source entry's `variant` name (None for the ordinary
    single-entry case, which is the overwhelming majority) so a consumer
    can group/filter by variant — this still doesn't build real choice-
    resolution machinery (same scope line as _innate_spell_ability), it
    just avoids losing or misrepresenting the data.

    Each returned dict: {"name" (title-cased fallback display name,
    catalog.spells is not imported by this module — see engine/resolve.py
    for the final catalog-backed name/spellId resolution), "spell_id"
    (naive slug guess), "level" (character level it becomes available),
    "uses" ("at-will" | "1/day"), "ability" (see
    _innate_spell_ability), "variant" (str | None)}."""
    results: list[dict] = []
    for entry in race_raw.get("additionalSpells") or []:
        if not isinstance(entry, dict):
            continue
        variant = entry.get("name") if isinstance(entry.get("name"), str) else None
        ability = _innate_spell_ability(entry.get("ability"))
        results.extend(_known_cantrips(entry.get("known"), ability, variant))  # G6
        innate = entry.get("innate")
        if not isinstance(innate, dict):
            continue
        for level_key, level_value in innate.items():
            try:
                level = int(level_key)
            except (TypeError, ValueError):
                continue  # defensive — every real level key is a plain int string
            uses, raw_names = _innate_spell_uses_and_names(level_value)
            for raw_name in raw_names:
                clean = _clean_innate_spell_name(raw_name)
                if not clean:
                    continue
                results.append({
                    "name": clean.title(),
                    "spell_id": slug(clean),
                    "level": level,
                    "uses": uses,
                    "ability": ability,
                    "variant": variant,
                })
    return results


_SPELL_SCHOOL_CODES = {
    "A": "abjuration", "C": "conjuration", "D": "divination", "E": "enchantment",
    "V": "evocation", "I": "illusion", "N": "necromancy", "T": "transmutation",
}
