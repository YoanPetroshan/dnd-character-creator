"""The species and background helpers of resolve(): ability bonuses, traits, damage modifiers, senses, speeds, innate spells, variants, size, feat grants and the choice templates they build.

Split from engine/resolve.py (S17); the text below is moved unchanged. `engine.resolve` re-exports every name.
"""
from __future__ import annotations

from catalog import feat_effects_data, reference_data
from catalog.choices import build_choice_template
from catalog.loader import Catalog
from i18n.messages import msg
from catalog.official_source import slug, SAVE_ABILITY_NAMES
from catalog.reference_data import SRD_TRAIT_EFFECTS
from . import feat_effects as feat_effects_mod
from .resolve_feats import _background_proficiency_choice_label, _feat_cid_prefix, _feat_offered, _feat_options, _feat_prerequisite_unmet_reason, _innate_entry_to_sheet, _join_desc, _race_name_key, _taken_reason

def _ability_sources(race: dict | None, subrace: dict | None) -> list[dict]:
    """Race and subrace as ability-score sources. A subrace flagged
    `overwrite_ability` (5etools `overwrite.ability`) REPLACES the race's
    scores — Draconblood/Ravenite Dragonborn, the MTF Tiefling bloodlines,
    the Half-Elf variants, and any named subrace of a race whose default
    form (nameless subrace) carried the scores, e.g. Human."""
    if subrace and subrace.get("overwrite_ability"):
        return [subrace]
    return [src for src in (race, subrace) if src]

def _species_ability_bonuses(race: dict | None, subrace: dict | None) -> dict[str, int]:
    bonuses: dict[str, int] = {}
    for src in _ability_sources(race, subrace):
        for entry in src.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            bonuses[ab] = bonuses.get(ab, 0) + entry["bonus"]
    return bonuses

def _species_damage_modifiers(race: dict | None, subrace: dict | None, feats: list[dict] | None = None,
                              chosen_resistances: list[str] | None = None) -> dict[str, list[str]]:
    """Merges resist/immune/vulnerable from race, subrace, AND (Phase 4c-i
    Task 5) every resolved granted feat, the same race-then-subrace-
    additions relationship _species_ability_bonuses already merges for
    ability score bonuses, now extended one step further. This goes
    beyond Task 5 (Phase 4a)'s original brief, which only mentions reading
    race.get("resist", []) — extended to also read subrace here because
    real fetched official data (races.json, confirmed 2026-09-24) has
    resist entries on SUBRACE records too: all four Genasi subraces
    (Air/Fire/Water/EEPC+MPMM) each grant a different elemental
    resistance, and Stout Halfling/PHB grants poison resistance — both
    only on the subrace, never the parent race. Reading race-only would
    silently drop these, the exact category of gap this plan already
    caught twice before (Task 3->3b, Task 4->4b for race-trait
    proficiencies) — disclosed here rather than repeating that pattern a
    third time. Deduplicates (preserving first-seen order) in case a
    value is ever repeated across race+subrace+feats, though not seen in
    real data today.

    `feats` (Phase 4c-i Task 5) is a list of resolved feat dicts — see
    _resolve_granted_feats — folded into the SAME race/subrace merge loop
    below rather than a separate parallel path, so a feat's resistance
    ADDS to whatever race/subrace already granted (deduplicated by the
    existing "if entry not in resistances" check), never replacing it.
    `feats=None` (every pre-existing call site before this task) behaves
    identically to the original two-argument signature — `*(feats or
    [])` contributes nothing when absent, so a character with no granted
    feats is a byte-identical safe no-op versus this function's Phase 4a
    behavior."""
    resistances: list[str] = []
    immunities: list[str] = []
    vulnerabilities: list[str] = []
    for src in (race, subrace, *(feats or [])):
        if not src:
            continue
        for entry in src.get("resist", []):
            if entry not in resistances:
                resistances.append(entry)
        for entry in src.get("immune", []):
            if entry not in immunities:
                immunities.append(entry)
        for entry in src.get("vulnerable", []):
            if entry not in vulnerabilities:
                vulnerabilities.append(entry)
    for entry in chosen_resistances or []:
        if entry not in resistances:
            resistances.append(entry)
    return {"resistances": resistances, "immunities": immunities, "vulnerabilities": vulnerabilities}

def _species_condition_immunities(race: dict | None, subrace: dict | None, feats: list[dict] | None = None) -> list[str]:
    """Same race+subrace(+feats, Phase 4c-i Task 5) merge as
    _species_damage_modifiers, for conditionImmune (e.g. Autognome/AAG's
    disease immunity). See that function's own docstring for the
    `feats=None`-is-a-safe-no-op reasoning."""
    immunities: list[str] = []
    for src in (race, subrace, *(feats or [])):
        if not src:
            continue
        for entry in src.get("condition_immune", []):
            if entry not in immunities:
                immunities.append(entry)
    return immunities

def _species_senses(race: dict | None, subrace: dict | None, catalog: Catalog, variant: dict | None = None) -> dict[str, int]:
    """Senses from the race and subrace: official records carry a numeric
    `darkvision`; bundled SRD races only have the descriptive "Darkvision"
    trait, mapped via reference_data.SRD_TRAIT_EFFECTS. Higher range wins."""
    senses: dict[str, int] = {}

    def add(kind: str, value) -> None:
        if isinstance(value, int) and value > senses.get(kind, 0):
            senses[kind] = value

    for src in (race, subrace, variant):
        if not src:
            continue
        if src is race and "darkvision" in (variant or {}).get("removes", []):
            continue  # e.g. Custom Lineage's Skill Proficiency variant
        add("darkvision", src.get("darkvision"))
    for effect in _srd_trait_effects(race, subrace):
        for kind, value in effect.get("senses", {}).items():
            add(kind, value)
    return senses

def _srd_trait_effects(race: dict | None, subrace: dict | None) -> list[dict]:
    """reference_data.SRD_TRAIT_EFFECTS entries for every trait of the race
    and subrace. Keyed by trait id: the bundled SRD ids plus, since W1, four official
    trait ids (the Dwarven Toughness variants), so official records can match too."""
    effects = []
    for src in (race, subrace):
        if not src:
            continue
        for ref in list(src.get("traits", [])) + list(src.get("racial_traits", [])):
            if ref["index"] in SRD_TRAIT_EFFECTS:
                effects.append(SRD_TRAIT_EFFECTS[ref["index"]])
    return effects

def _species_speeds(race: dict | None, subrace: dict | None, variant: dict | None = None) -> dict[str, int]:
    """{walk, fly?, swim?, climb?}: a selected variant's walk speed (Wood Elf
    lineage: 35) overrides the race's, the subrace's overrides both;
    non-walk modes merge (subrace wins per mode); a `true` mode means
    "equal to your walking speed"."""
    if not race:
        return {}
    walk = race.get("speed") if isinstance(race.get("speed"), int) else None
    if variant and isinstance(variant.get("speed"), int):
        walk = variant["speed"]
    if subrace and isinstance(subrace.get("speed"), int):
        walk = subrace["speed"]
    if walk is None:
        return {}
    modes = {**(race.get("movement") or {}), **((subrace or {}).get("movement") or {})}
    speeds = {"walk": walk}
    for mode, value in modes.items():
        speeds[mode] = walk if value is True else value
    return speeds

def _species_equal_walk_modes(race: dict | None, subrace: dict | None) -> list[str]:
    """WF: the species movement modes stored as `true` ("equal to your walking speed"). `_species_speeds`
    seeds them with the BASE walk (keeps the key order); resolve() recomputes them from the FINAL walk."""
    if not race:
        return []
    modes = {**(race.get("movement") or {}), **((subrace or {}).get("movement") or {})}
    return [mode for mode, value in modes.items() if value is True]

def _subrace_replaces_spell_trait(race: dict, subrace: dict | None, catalog: Catalog, entry: dict) -> bool:
    """F1: True when the subrace's entries replace (5etools `data.overwrite`, kept as `overwrites_traits`) a trait of the
    parent race whose text names this innate spell: the PHB Tiefling's Infernal Legacy (Thaumaturgy, Hellish Rebuke,
    Darkness) is replaced by every MTF legacy and by the SCAG Devil's Tongue / Hellfire / Winged variants."""
    names = {n.lower() for n in (subrace or {}).get("overwrites_traits") or []}
    if not names:
        return False
    spell = str(entry.get("name") or "").lower()
    for ref in race.get("traits", []):
        if ref.get("name", "").lower() in names:
            text = " ".join((catalog.traits.get(ref["index"]) or {}).get("desc") or []).lower()
            if spell and spell in text:
                return True
    return False

_ALL_ALTERNATIVES = "*"

def _species_innate_spells(race: dict | None, subrace: dict | None, catalog: Catalog,
                           variant: dict | None = None, alt: str | None = None, ability: str | None = None) -> list[dict]:
    """The species' innate-spell sheet entries (`_species_innate_entries`), with the F1 resolution of the two open picks:
    `alt` is the picked alternative cantrip (Astral Elf: exactly one of three; None = not picked yet, so none of them) and
    `ability` the picked spellcasting ability for the entries whose data lists candidates (`{"choose": [INT, WIS, CHA]}`):
    the picked one, else None (never the raw candidate dict; the card lists the candidates)."""
    out = []
    for entry in _species_innate_entries(race, subrace, catalog, variant, alt):
        raw = entry["ability"]
        if isinstance(raw, dict) and raw.get("choose"):
            entry = {**entry, "ability": ability if ability in raw["choose"] else None}
        out.append(entry)
    return out

def _species_innate_entries(race: dict | None, subrace: dict | None, catalog: Catalog,
                            variant: dict | None = None, alt: str | None = None) -> list[dict]:
    """Merges innate_spells from BOTH race and subrace — same race-then-
    subrace-additions relationship _species_damage_modifiers already
    merges (subraces carry their OWN additionalSpells independently, e.g.
    Duergar/MTF subrace of Dwarf grants enlarge/reduce + invisibility that
    the parent Dwarf/PHB race does not) — and resolves each grant's
    spell_id against catalog.spells.

    Resolvability (Task 6's empirical measurement, re-measured 2026-09-24
    against the REAL shipped pipeline — load_official_races() followed by
    resolving each returned reference against catalog.spells, exactly
    what this function does, over the real fetched races.json, races AND
    subraces): 93/102 (91.2%) of real innate-spell references resolve
    cleanly against the bundled 2014 SRD spell catalog — most sourcebook
    races' innate spells genuinely ARE 2014-era SRD spells, confirming
    the brief's "plausible" scenario, so this is implemented as full
    resolution rather than a narrow cut. (An earlier pass measured
    99/108 by counting raw JSON references directly — that count was
    wrong on two counts: it included records _race_from_5etools/
    _subrace_from_5etools filter out via the "_copy" check before they
    ever reach this code, and it predated the fix for a "rest"-wrapper
    innate entry, see official_source._innate_spell_uses_and_names, that
    used to be silently dropped rather than counted.) The remaining
    9/102 (8.8%) reference spells genuinely absent from the bundled SRD
    list (Hex, Tenser's Floating Disk, Ice Knife, Wall of Water, Crown of
    Madness, Ray of Sickness x2, Armor of Agathys, Searing Smite — real
    spells from sourcebooks this project has not imported spell DATA
    for, an explicitly out-of-scope gap per the design spec, not a bug
    in this conversion). For those, spellId is None and
    level/school/other full-record fields that only catalog.spells could
    supply are simply not available — but `name` is ALWAYS populated
    (official_source.py's own cleaned, title-cased fallback) so the grant
    is visible on the sheet rather than silently dropped."""
    innate: list[dict] = []
    for src in (race, subrace):
        if not src:
            continue
        for entry in src.get("innate_spells", []):
            # A race with lineage variants (Elf/Tiefling XPHB) lists every
            # lineage's spells tagged with its name; only the selected
            # variant's own grants (below) apply.
            if src is race and race.get("variants") and entry.get("variant") is not None:
                continue
            if src is race and "additionalSpells" in (variant or {}).get("removes", []):
                continue  # e.g. Kobold's Craftiness / Defiance legacies
            if src is race and _subrace_replaces_spell_trait(race, subrace, catalog, entry):
                continue  # F1: the MTF / SCAG Tiefling legacies replace Infernal Legacy
            if entry.get("alt") and alt != _ALL_ALTERNATIVES and entry["alt"] != alt:
                continue  # F1: one of several alternative cantrips (Astral Elf): only the picked one
            innate.append(_innate_entry_to_sheet(entry, catalog))
    for entry in (variant or {}).get("innate_spells", []):
        innate.append(_innate_entry_to_sheet(entry, catalog))
    for effect in _srd_trait_effects(race, subrace):
        for entry in effect.get("innate_spells", []):
            innate.append(_innate_entry_to_sheet(entry, catalog))
    # G6: the race and its subrace may both list the same entry (the SCAG "Variant; Infernal Legacy" repeats the PHB
    # Tiefling's whole set, and replaces nothing); an identical entry adds nothing, so only the first is kept.
    return [e for i, e in enumerate(innate) if e not in innate[:i]]

def _species_trait_spell_choices(race: dict | None, subrace: dict | None, catalog: Catalog,
                                 choices: list[dict]) -> list[dict]:
    """Sheet innate-spell entries for SRD race traits whose
    `trait_specific.spell_options` Choice was answered (High Elf Cantrip):
    an at-will spell, cast with the ability in SRD_TRAIT_EFFECTS."""
    by_id = {c["id"]: c for c in choices}
    out = []
    for src in (race, subrace):
        if not src:
            continue
        for ref in list(src.get("traits", [])) + list(src.get("racial_traits", [])):
            trait = catalog.traits.get(ref["index"]) or {}
            if not (trait.get("trait_specific") or {}).get("spell_options"):
                continue
            choice = by_id.get(_species_trait_spell_cid(race, ref["index"]))
            ability = SRD_TRAIT_EFFECTS.get(ref["index"], {}).get("spell_ability")
            for sid in (choice or {}).get("selected", []):
                spell = catalog.spells.get(sid)
                if spell:
                    out.append({"spellId": sid, "name": spell["name"], "level": 1, "uses": "at-will",
                                "ability": ability, "variant": None})
    return out

def _species_trait_spell_cid(race: dict | None, trait_index: str) -> str:
    return f"species:{race['index'] if race else ''}:trait:{trait_index}:cantrip"

class _FollowedVariants(dict):
    """`_followed_variants`' result: {dependent feat index: variant slug | None}, plus `cards` = {dependent feat index:
    [candidate list slugs]} for a dependent that has its OWN list card (F1: the character holds more than one base feat)."""
    cards: dict[str, list[str]]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.cards = {}

def _followed_variants(feats: list[dict], raw_choices: dict, variant_hints: dict | None = None,
                       hinted_feats=()) -> "_FollowedVariants":
    """G5: {dependent feat index: variant slug} for the held feats that FOLLOW another held feat's spell list. A feat whose
    effect entry has ``ability_from`` (RP5) and that has `spell_variants` of its own (Magic Connoisseur: "Choose a level 1
    and a level 2 spell from the same list you selected for the Magic Initiate feat's cantrips") takes the list the base
    feat picked; it then has no `:spell-variant` card of its own. The value is None while the base feat's list is not
    picked yet (the dependent offers no spell cards until it is) or when the picked list is not one of the dependent's.
    `raw_choices` is the union of the draft's raw selections (every cid is unique across classes / background / species).
    Only the base's variant card is read; a base feat that is not held leaves the dependent with its own card.
    F1: (a) a base feat whose list is FIXED by its background (`variant_hints`, the single-option card: Acolyte's Magic
    Initiate Cleric) counts as picked though it was never clicked, for the holders in `hinted_feats`; (b) with MORE THAN ONE
    base feat held (XPHB Magic Initiate is repeatable, a different list each time) the dependent gets its own
    `:spell-variant` card limited to the lists the holders picked (`.cards`), and follows that pick."""
    out = _FollowedVariants()
    hints = variant_hints or {}
    for feat in feats:
        base = feat_effects_mod.ability_from(feat_effects_data.FEAT_EFFECTS.get(feat.get("index")))
        if not base or not feat.get("spell_variants") or feat["index"] in out:
            continue
        holders = [f for f in feats if f["index"] == base and f.get("spell_variants")]
        if not holders:
            continue
        own = {slug(v) for v in feat["spell_variants"]}
        picks: list[str] = []
        for holder in holders:
            valid = [slug(v) for v in holder["spell_variants"]]
            raw = raw_choices.get(f"{_feat_cid_prefix(holder)}:spell-variant")
            picked = next((slug(x) for x in raw if isinstance(x, str) and slug(x) in valid), None) if isinstance(raw, list) else None
            hint = hints.get(holder["index"])
            if picked is None and hint and any(holder is h for h in hinted_feats) and slug(hint) in valid:
                picked = slug(hint)  # the background fixes the list: a single-option card
            if picked and picked not in picks:
                picks.append(picked)
        if len(holders) == 1:
            out[feat["index"]] = picks[0] if picks and picks[0] in own else None
            continue
        candidates = [x for x in picks if x in own]
        raw = raw_choices.get(f"{_feat_cid_prefix(feat)}:spell-variant")
        chosen = next((slug(x) for x in raw if isinstance(x, str) and slug(x) in candidates), None) if isinstance(raw, list) else None
        out[feat["index"]] = chosen
        out.cards[feat["index"]] = candidates
    return out

def _species_ability_bonus_choice_template(race: dict | None, subrace: dict | None, race_id: str | None) -> dict | None:
    """Half-Elf's ability_bonus_options (the only race/subrace in the
    bundled data with this field) needs a real Choice — this builds its
    template. Race is checked before subrace since ability_bonus_options
    could in principle appear on either (only race does in the bundled
    data, but this stays generic rather than hardcoding "half-elf")."""
    for src in _ability_sources(race, subrace):
        if not src.get("ability_bonus_options"):
            continue
        envelope = src["ability_bonus_options"]
        cid = f"species:{race_id}:ability-bonus"
        source = {"kind": "species", "id": race_id, "label": race["name"] if race else ""}
        choose = envelope.get("choose", 1)
        options = envelope.get("from", {}).get("options", [])
        if options and all(o.get("option_type") == "multiple" for o in options):
            description = msg("desc-asi-option-one")
        else:
            bonus = options[0].get("bonus", 1) if options else 1
            description = msg("desc-asi-increase", n=choose, bonus=bonus)
        return build_choice_template(envelope, cid, source, msg("label-ability-score-increase"), description=description)
    return None

def _background_ability_bonuses(bg: dict | None) -> dict[str, int]:
    """Mirrors _species_ability_bonuses' shape for backgrounds (Phase 4b
    Task 4). Always returns {} — backgrounds never grant a FIXED,
    non-choice ability bonus; confirmed empirically against the real
    fetched backgrounds.json (2026-09-26): every one of the 60 real
    records with an `ability` field uses the `choose`/"weighted" shape
    exclusively (see _ability_bonus_options_from_5etools_weighted_pair,
    catalog/official_source.py), never a flat `{"str": 2}`-style fixed
    entry. This function exists mainly for symmetry with
    _species_ability_bonuses and to make explicit, in code, that ability
    bonuses now flow from BOTH species and background through the SAME
    early ability-score pass below (see the "Final ability scores"
    comment) — not because any real data currently needs it to do
    anything."""
    return {}

def _background_ability_bonus_choice_template(bg: dict | None, bg_id: str | None) -> dict | None:
    """Mirrors _species_ability_bonus_choice_template for the 2024-style
    background ability-score-improvement choice (Phase 4b Task 4). bg's
    `ability_bonus_options` envelope (built by
    _ability_bonus_options_from_5etools_weighted_pair — None for SRD's
    bundled Acolyte and any background with no `ability` field, a safe
    no-op) is flattened into up to 7 ordinary selectable "bundle" options
    (6 "+2 to one of a 3-ability pool, +1 to a different one" split
    combinations, plus 1 "+1 to all three" flat combination) — see that
    function's own docstring for the full derivation."""
    if not bg or not bg.get("ability_bonus_options"):
        return None
    envelope = bg["ability_bonus_options"]
    cid = f"background:{bg_id}:ability-bonus"
    source = {"kind": "background", "id": bg_id, "label": bg["name"] if bg else ""}
    choose = envelope.get("choose", 1)
    description = msg("desc-asi-improvement-options", n=choose)
    return build_choice_template(envelope, cid, source, msg("label-asi"), description=description)

def _background_ability_bonus_deltas(envelope: dict, built_options: list[dict]) -> dict[str, list[tuple[str, int]]]:
    """Maps each ability-bonus bundle option's id (as computed by
    catalog.choices' build_choice_template/_bundle_label_and_id, from this
    SAME envelope) to its concrete (ability, delta) pairs — e.g.
    "str-2+con-1" -> [("STR", 2), ("CON", 1)]. Read directly off the raw
    envelope's own option `items` (ability_score + bonus, still fully
    structured there) rather than re-deriving the id via a second,
    independent implementation of _bundle_label_and_id's algorithm, which
    would risk silently diverging from it. Paired by POSITION with
    `built_options`: both this function's `envelope['from']['options']`
    and build_choice_template's own internal walk over that exact same
    list iterate in the same order, and every option this envelope ever
    contains is a pure ability_bonus 'multiple' bundle (by construction of
    _ability_bonus_options_from_5etools_weighted_pair) — so
    build_choice_options never drops one as unresolvable, and the two
    lists always stay aligned 1:1."""
    raw_options = envelope.get("from", {}).get("options", [])
    deltas_by_id: dict[str, list[tuple[str, int]]] = {}
    for raw_opt, built_opt in zip(raw_options, built_options):
        items = raw_opt.get("items") if raw_opt.get("option_type") == "multiple" else [raw_opt]
        deltas_by_id[built_opt["id"]] = [
            (item["ability_score"]["index"].upper(), item.get("bonus", 1))
            for item in items or []
        ]
    return deltas_by_id

def _background_choice_templates(bg: dict, bg_id: str) -> list[dict]:
    templates = []
    envelope = bg.get("language_options")
    if envelope:
        cid = f"background:{bg_id}:languages"
        source = {"kind": "background", "id": bg_id, "label": bg["name"]}
        # language_options carries no 'desc' of its own, and the background
        # object has no separate summary text for it either — write a
        # plain, generic description rather than leaving it blank.
        choose = envelope.get("choose", 1)
        description = msg("desc-feat-languages", n=choose)
        tpl = build_choice_template(envelope, cid, source, msg("label-languages"), description=description)
        if tpl:
            templates.append(tpl)

    # Skill/tool proficiency CHOICES (Phase 4b Task 2) — as opposed to
    # starting_proficiencies' fixed grants. A background can carry more than
    # one of these at once (a skill choice AND a tool choice together, e.g.
    # Inheritor/SCAG — or even two simultaneous tool wildcards, e.g.
    # Vizier/PSA's anyArtisansTool + anyMusicalInstrument), hence the index
    # in the cid, mirroring every other multi-envelope choice_templates loop
    # in this file (e.g. _asi_choice_templates' per-level cids). The
    # ":proficiency-choice" substring is load-bearing, not decorative — same
    # convention _species_choice_templates already established for the
    # identical purpose: it's what the merge-site fix below (the sheet-
    # proficiency scan) uses to recognize a background-sourced proficiency
    # selection.
    for i, prof_envelope in enumerate(bg.get("starting_proficiency_choices", []) or []):
        cid = f"background:{bg_id}:proficiency-choice-{i}"
        source = {"kind": "background", "id": bg_id, "label": bg["name"]}
        label = _background_proficiency_choice_label(prof_envelope)
        choose = prof_envelope.get("choose", 1)
        description = msg("desc-feat-proficiencies", n=choose)
        tpl = build_choice_template(prof_envelope, cid, source, label, description=description)
        if tpl:
            templates.append(tpl)

    return templates

def _species_variant_template(race: dict | None, race_id: str | None) -> dict | None:
    """The lineage / ancestry pick for a race with `variants` (2024 Elf,
    Tiefling, Gnome, Goliath, Dragonborn colours, Shifter, ...)."""
    if not (race and race_id and race.get("variants")):
        return None
    return {
        "id": f"species:{race_id}:variant",
        "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": msg("label-lineage"),
        "description": msg("desc-lineage"),
        "count": 1,
        "options": [{"id": v["id"], "label": v["name"]} for v in race["variants"]],
    }

def _species_alternatives(race: dict | None, subrace: dict | None, catalog: Catalog) -> list[dict]:
    """F1: the alternative cantrips of a species whose data lists several unnamed `additionalSpells` entries (Astral Elf:
    Dancing Lights / Light / Sacred Flame), as [{"id": slug, "name"}] in data order."""
    out: list[dict] = []
    for src in (race, subrace):
        for entry in (src or {}).get("innate_spells") or []:
            alt = entry.get("alt")
            if alt and all(o["id"] != alt for o in out):
                out.append({"id": alt, "name": _innate_entry_to_sheet(entry, catalog)["name"]})
    return out

def _species_cantrip_template(race: dict | None, subrace: dict | None, catalog: Catalog, race_id: str | None) -> dict | None:
    """F1: the pick of ONE of the alternative cantrips (Astral Elf: Astral Fire) ."""
    options = _species_alternatives(race, subrace, catalog) if race and race_id else []
    if not options:
        return None
    return {
        "id": f"species:{race_id}:innate-cantrip",
        "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": msg("label-species-cantrip"),
        "description": msg("desc-species-cantrip"),
        "count": 1,
        "options": [{"id": o["id"], "label": o["name"]} for o in options],
    }

def _selected_species_alternative(race: dict | None, subrace: dict | None, catalog: Catalog, species_choices: dict,
                                  race_id: str | None) -> str | None:
    """The picked alternative cantrip id, or None (unpicked / not offered)."""
    tpl = _species_cantrip_template(race, subrace, catalog, race_id)
    raw = species_choices.get(tpl["id"]) if tpl else None
    valid = {o["id"] for o in (tpl or {}).get("options", [])}
    return next((x for x in raw if isinstance(x, str) and x in valid), None) if isinstance(raw, list) else None

def _species_spell_ability_candidates(race: dict | None, subrace: dict | None, catalog: Catalog,
                                      variant: dict | None) -> list[str]:
    """F1: the candidate spellcasting abilities (data: `ability: {"choose": [...]}`) of the species' innate entries, in
    data order; [] when every entry has a fixed ability or there is none."""
    out: list[str] = []
    for entry in _species_innate_entries(race, subrace, catalog, variant, _ALL_ALTERNATIVES):
        raw = entry["ability"]
        if isinstance(raw, dict):
            out += [a for a in raw.get("choose") or [] if a not in out]
    return out

def _species_spell_ability_template(race: dict | None, subrace: dict | None, catalog: Catalog, variant: dict | None,
                                    race_id: str | None) -> dict | None:
    """F1: the spellcasting-ability pick of a species whose innate spells list candidates (MPMM Aasimar / Firbolg ...,
    XPHB Elf / Tiefling lineages, Genasi): one pick for all the species' spells, the way the rules text says "choose the
    ability when you select the ...". Same card shape as a feat's `:spell-ability`."""
    options = _species_spell_ability_candidates(race, subrace, catalog, variant) if race and race_id else []
    if not options:
        return None
    return {
        "id": f"species:{race_id}:spell-ability",
        "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": msg("label-prefixed", head=race["name"], tail=msg("label-spellcasting-ability")),
        "description": msg("desc-species-spell-ability"), "count": 1,
        "options": [{"id": a.lower(), "label": SAVE_ABILITY_NAMES[a.lower()]} for a in options],
    }

def _selected_species_spell_ability(race: dict | None, subrace: dict | None, catalog: Catalog, variant: dict | None,
                                    species_choices: dict, race_id: str | None) -> str | None:
    tpl = _species_spell_ability_template(race, subrace, catalog, variant, race_id)
    raw = species_choices.get(tpl["id"]) if tpl else None
    valid = {o["id"] for o in (tpl or {}).get("options", [])}
    pick = next((x for x in raw if isinstance(x, str) and x in valid), None) if isinstance(raw, list) else None
    return pick.upper() if pick else None

def _selected_species_variant(race: dict | None, species_choices: dict, race_id: str | None) -> dict | None:
    """The race variant named by the stored selection (the first valid id),
    or None when unpicked / unknown."""
    if not (race and race_id and race.get("variants")):
        return None
    raw = species_choices.get(f"species:{race_id}:variant")
    if not isinstance(raw, list):
        return None
    by_id = {v["id"]: v for v in race["variants"]}
    return next((by_id[s] for s in raw if isinstance(s, str) and s in by_id), None)

def _draconic_ancestry_row_label(row: tuple) -> str:
    return f"{row[0]}: {row[1]}, {row[2]}"  # the verbatim table cells: "Red: Fire, 15 ft. cone (Dex. save)"

def _species_draconic_ancestry_template(race: dict | None, race_id: str | None, subrace: dict | None,
                                        species_choices: dict) -> dict | None:
    """B1: the PHB Dragonborn's Draconic Ancestry (the dragon colour), one of the 10 table rows
    (`reference_data.DRACONIC_ANCESTRY_PHB`). The resistance pick (`species:<id>:resistance`, a damage type) does not name
    the dragon (fire = Brass, Gold, Red), so the card follows it: once a valid resistance is picked only the colours of
    that damage type are offered (a stored colour of another type is then reported as `pruned-no-longer-offered` and the
    card is pending). The EGW subraces (Draconblood, Ravenite) replace the Damage Resistance and Draconic Ancestry traits
    and keep the breath weapon, which the ancestry table still decides: all ten colours, not filtered."""
    if not (race and race_id in reference_data.DRACONIC_ANCESTRY_RACES):
        return None
    options = list(reference_data.DRACONIC_ANCESTRY_PHB.items())
    replaced = {n.lower() for n in (subrace or {}).get("overwrites_traits") or []}
    if "draconic ancestry" not in replaced:
        raw = species_choices.get(f"species:{race_id}:resistance")
        pick = next((x for x in raw if isinstance(x, str)), None) if isinstance(raw, list) else None
        if pick in {row["damage"] for _, row in options}:
            options = [(cid, row) for cid, row in options if row["damage"] == pick]
    return {
        "id": f"species:{race_id}:draconic-ancestry",
        "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": msg("label-dragon-colour"),
        "description": msg("desc-dragon-colour"),
        "count": 1,
        "options": [{"id": cid, "label": _draconic_ancestry_row_label(row["row"])} for cid, row in options],
    }

def _species_size_template(race: dict | None, race_id: str | None) -> dict | None:
    """The size pick for a race that lists more than one size (Small or Medium)."""
    if not (race and race_id and race.get("size_options")):
        return None
    return {
        "id": f"species:{race_id}:size",
        "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": msg("label-size"),
        "description": msg("desc-size"),
        "count": 1,
        "options": [{"id": s.lower(), "label": s} for s in race["size_options"]],
    }

def _species_size(race: dict | None, species_choices: dict, race_id: str | None) -> str | None:
    """The sheet's species size: the selected one for a race with size
    options (None while unpicked), otherwise the race's own size."""
    if not race:
        return None
    options = race.get("size_options") or []
    if not options:
        return race.get("size") or "Medium"
    raw = species_choices.get(f"species:{race_id}:size")
    if isinstance(raw, list):
        by_id = {s.lower(): s for s in options}
        return next((by_id[s] for s in raw if isinstance(s, str) and s in by_id), None)
    return None

def _species_choice_templates(catalog: Catalog, race: dict, race_id: str, subrace: dict | None,
                              variant: dict | None = None) -> list[dict]:
    templates = []
    trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
    for ref in trait_refs:
        trait = catalog.traits.get(ref["index"])
        if not trait:
            continue
        # PRE-EXISTING gap (predates this plan, affects bundled SRD data
        # unconditionally): this loop read subtrait_options below but never
        # a trait's proficiency_choices field, so Half-Elf's real "Skill
        # Versatility" trait (choose 2 of every skill) and Dwarf's real
        # "Tool Proficiency" trait (choose 1 of smith's/brewer's/mason's
        # tools) never produced a Choice the player could even see. Checked
        # first (not after the subtrait_options block's own `continue`,
        # which would otherwise skip traits — like both of these — that
        # have proficiency_choices but no subtrait_options). The
        # ":proficiency-choice" cid suffix is load-bearing, not decorative:
        # it keeps this id distinct from the subtrait_options block's id
        # for the same trait below (avoiding a collision if a trait ever
        # had both fields), and it's the substring the merge-site fix below
        # uses to tell a genuine proficiency choice apart from a
        # subtrait_options selection (e.g. Dragonborn's Draconic Ancestry
        # damage-type pick, which is NOT a proficiency).
        prof_envelope = trait.get("proficiency_choices")
        # A variant that nulls `skillProficiencies` (Custom Lineage's
        # Darkvision, Kobold's Defiance / Draconic Sorcery) drops the race's
        # skill choice, which official_source mints as this dedicated trait.
        if prof_envelope and "skillProficiencies" in (variant or {}).get("removes", []) \
                and ref["index"].endswith("-trait-choice-skill-proficiency"):
            prof_envelope = None
        if prof_envelope:
            prof_cid = f"species:{race_id}:trait:{trait['index']}:proficiency-choice"
            prof_source = {"kind": "species", "id": race_id, "label": race["name"]}
            prof_choose = prof_envelope.get("choose", 1)
            prof_description = msg("desc-feat-proficiencies", n=prof_choose)
            prof_tpl = build_choice_template(
                prof_envelope, prof_cid, prof_source, trait["name"], description=prof_description
            )
            if prof_tpl:
                templates.append(prof_tpl)

        # Trait-level bonus language (SRD High Elf's Extra Language).
        lang_envelope = trait.get("language_options")
        if lang_envelope:
            lang_choose = lang_envelope.get("choose", 1)
            lang_tpl = build_choice_template(
                lang_envelope, f"species:{race_id}:trait:{trait['index']}:languages",
                {"kind": "species", "id": race_id, "label": race["name"]}, trait["name"],
                description=msg("desc-bonus-languages", n=lang_choose),
            )
            if lang_tpl:
                templates.append(lang_tpl)

        # Trait-level spell pick (SRD High Elf Cantrip).
        spell_envelope = (trait.get("trait_specific") or {}).get("spell_options")
        if spell_envelope:
            spell_tpl = build_choice_template(
                spell_envelope, _species_trait_spell_cid(race, trait["index"]),
                {"kind": "species", "id": race_id, "label": race["name"]}, trait["name"],
                description=_join_desc(trait.get("desc")),
            )
            if spell_tpl:
                templates.append(spell_tpl)

        envelope = (trait.get("trait_specific") or {}).get("subtrait_options")
        if not envelope:
            continue
        cid = f"species:{race_id}:trait:{trait['index']}"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        # subtrait_options carries no 'desc' of its own — the description
        # text lives on the parent trait (verified directly against
        # 5e-SRD-Traits.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, trait["name"], description=_join_desc(trait.get("desc")))
        if tpl:
            templates.append(tpl)

    # Race/subrace bonus-language choices (e.g. Human, Half-Elf) use the
    # same options_array shape as everything else build_choice_options
    # already handles, so this is a real Choice, not just a warning.
    for src, src_id in ((race, race_id), (subrace, subrace.get("index") if subrace else None)):
        if not src:
            continue
        envelope = src.get("language_options")
        if not envelope:
            continue
        cid = f"species:{race_id}:languages"
        if src is subrace:
            cid = f"species:{race_id}:subspecies:{src_id}:languages"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        choose = envelope.get("choose", 1)
        description = msg("desc-bonus-languages", n=choose)
        tpl = build_choice_template(envelope, cid, source, msg("label-bonus-language"), description=description)
        if tpl:
            templates.append(tpl)

    # Damage-resistance choices (Dragonborn ancestry, 2024 Tiefling legacy).
    # A race whose variants fix the resistance (Dragonborn colour, Tiefling
    # legacy) is decided by the variant pick instead of a separate choice.
    variant_decides_resistance = any(v.get("resist") for v in race.get("variants") or [])
    # VF1.4: a subrace whose own entry replaces the race's "Damage Resistance" trait (5etools `data.overwrite`, kept as
    # `overwrites_traits`: EGW Draconblood and Ravenite) has no resistance pick of the race either.
    resistance_replaced = "damage resistance" in {n.lower() for n in (subrace or {}).get("overwrites_traits") or []}
    for src, src_id in ((race, race_id), (subrace, subrace.get("index") if subrace else None)):
        envelope = src.get("resist_options") if src else None
        if not envelope or (src is race and (variant_decides_resistance or resistance_replaced)):
            continue
        cid = f"species:{race_id}:resistance" if src is race else f"species:{race_id}:subspecies:{src_id}:resistance"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        tpl = build_choice_template(envelope, cid, source, msg("label-damage-resistance"), description=msg("desc-resist-type"))
        if tpl:
            templates.append(tpl)

    return templates

def _species_feat_pool(catalog: Catalog, category: str | None, sources, ruleset: str = "mixed", keep=(),
                       include=()) -> list[dict]:
    """Feats a species feat grant may be spent on. An explicit category
    ("O": Human/XPHB's Origin feat) offers exactly that category; `None`
    (the "any" grant of Variant Human and Custom Lineage) offers feats with
    no category (the 2014 books), General and Origin ones, minus the literal
    "Ability Score Improvement" entry. Epic Boon, Dragonmark, Fighting
    Style and Dragon-gift categories stay out. Filtered by draft.sources
    like every feat (display order: see _feat_options). (Unlike _asi_feat_pool this ignores the
    ruleset's category rules beyond _feat_offered: a 2024 "any" grant still
    lists the 2014 category-less feats that ruleset_allows lets through.)
    `keep`: stored option ids (`feat:<index>`); one whose category fits the
    grant stays in the pool even when ruleset/sources hide it (the caller
    flags it `hiddenByFilters`). G7: `include` (catalog feat indexes) joins the pool whatever its category: the plain feat
    of an either-or grant ("Survivor or a Dark Gift feat"). F1: it is offered whatever the sources / ruleset filters say (the
    caller flags it `hiddenByFilters`), so a background that is held always has its plain feat."""
    allowed = {category} if category is not None else {"", "G", "O"}
    kept = {k[len("feat:"):] for k in keep if isinstance(k, str) and k.startswith("feat:")}
    pool = [
        f for f in catalog.feats.values()
        if (((f.get("category") or "") in allowed and f["name"] != "Ability Score Improvement") or f["index"] in include)
        and (_feat_offered(f, sources, ruleset) or f["index"] in kept or f["index"] in include)
    ]
    return pool

def _species_feat_grant_slots(race: dict | None, subrace: dict | None, race_id: str | None) -> list[tuple[str, dict]]:
    """[(choice id, {"count", "category"})] for the race's and the
    subrace's `feat_grants`, in that order."""
    if not (race and race_id):
        return []
    slots = [(f"species:{race_id}:feat-{i}", grant) for i, grant in enumerate(race.get("feat_grants") or [])]
    if subrace:
        slots += [
            (f"species:{race_id}:subspecies:{subrace['index']}:feat-{i}", grant)
            for i, grant in enumerate(subrace.get("feat_grants") or [])
        ]
    return slots

def _background_feat_grant_slots(bg: dict | None, bg_id: str | None) -> list[tuple[str, dict]]:
    """W4: [(choice id, {"count", "category"})] for a background's `feat_grants` (Mist Wanderer, Spirit Medium: a
    Dark Gift feat of your choice). The picks are stored in `background.choices` under `background:<id>:feat-<i>`."""
    if not (bg and bg_id):
        return []
    return [(f"background:{bg_id}:feat-{i}", grant) for i, grant in enumerate(bg.get("feat_grants") or [])]

def _species_feat_choice_template(
    race: dict, race_id: str, cid: str, grant: dict, catalog: Catalog, sources, scores: dict[str, int],
    total_level: int, use_prereqs: bool, held: "_HeldFeatState", taken: dict[str, str], ruleset: str = "mixed",
    keep=(), kind: str = "species",
) -> dict:
    """One Choice for a species feat grant. A failed prerequisite wins over
    "already taken" as the disabled reason; the check uses the character's
    scores before any feat bonus and the total level (permissive, like the
    ASI pre-walk)."""
    options = []
    include = tuple(grant.get("include") or ())
    for feat, option in _feat_options(_species_feat_pool(catalog, grant["category"], sources, ruleset, keep, include), ruleset):
        if not _feat_offered(feat, sources, ruleset):
            option["hiddenByFilters"] = True
        reason = _feat_prerequisite_unmet_reason(feat, total_level, scores, use_prereqs, held, catalog)
        if reason:
            option["disabled"] = True
            option["disabledReason"] = reason
        elif _taken_reason(feat, taken):
            option["disabled"] = True
            option["disabledReason"] = _taken_reason(feat, taken)
        options.append(option)
    options.sort(key=lambda o: o["id"][len("feat:"):] not in include)  # G7: the plain feat of an either-or grant leads (stable)
    count = grant["count"]
    noun = (msg("noun-origin-feat") if grant["category"] == "O"
            else msg("noun-dark-gift-feat") if grant["category"] == "DG" else msg("noun-feat"))
    return {
        "id": cid, "source": {"kind": kind, "id": race_id, "label": race["name"]},
        "label": msg("label-origin-feat") if grant["category"] == "O" else msg("label-feat"),
        "description": (msg("desc-feat-or-dark-gift", name=catalog.feats[include[0]]["name"]) if include and include[0] in catalog.feats
                        else msg("desc-species-feat", noun=noun) if count == 1 else msg("desc-species-feats", count=count)),
        "count": count, "options": options,
    }

def _either_or_default_pick(template: dict, grant: dict, raw_choices: dict) -> str | None:
    """F1: the option id an either-or feat card (G7: Haunted One / Investigator, "Survivor or a Dark Gift feat") takes when
    the draft stores NO pick for it: the plain feat (`include[0]`), as before G7, so a saved draft or a sources filter that
    hides every Dark Gift never loses it. A stored pick of any kind (even a stale one) is left alone."""
    include = grant.get("include") or ()
    if not include:
        return None
    stored = raw_choices.get(template["id"])
    if isinstance(stored, list) and any(isinstance(x, str) for x in stored):
        return None
    option = next((o for o in template["options"] if o["id"] == f"feat:{include[0]}"), None)
    return option["id"] if option and not option.get("disabled") else None

def _held_race_state(race: dict | None, subrace: dict | None, size: str | None) -> tuple[set[str], set[str], str | None]:
    race_names = {_race_name_key(race["name"])} if race and race.get("name") else set()
    subrace_names: set[str] = set()
    if subrace:
        if subrace.get("name"):
            subrace_names.add(subrace["name"].strip().lower())
        subrace_names.update(t for t in (subrace.get("index") or "").lower().split("-") if t)
    return race_names, subrace_names, size

def _apply_background_overlap(class_templates: list[dict], bg: dict | None) -> None:
    if not bg:
        return
    granted = {p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-")}
    if not granted:
        return
    for tpl in class_templates:
        if "expertise-choice" in tpl["id"]:
            continue  # expertise needs skills the character already has
        for opt in tpl["options"]:
            if opt["id"] in granted:
                opt["disabled"] = True
                opt["disabledReason"] = msg("disabled-granted-by", name=bg["name"])

def _apply_species_overlap(class_templates: list[dict], race: dict | None, subrace: dict | None, catalog: Catalog) -> None:
    """Mirrors _apply_background_overlap: race/subrace traits can grant a
    skill proficiency for free (e.g. Elf's Keen Senses grants
    skill-perception), and a class's own skill-choice list can include that
    same skill (e.g. Rogue's prof-choice-0). Without this, a player could
    spend a class choice slot on a skill they already have for free, with
    no disabled flag or warning — this closes that gap the same way the
    background path already does."""
    if not race:
        return
    trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
    granted: set[str] = set()
    for ref in trait_refs:
        trait = catalog.traits.get(ref["index"])
        if not trait:
            continue
        granted.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
    if not granted:
        return
    for tpl in class_templates:
        if "expertise-choice" in tpl["id"]:
            continue
        for opt in tpl["options"]:
            if opt["id"] in granted:
                opt["disabled"] = True
                opt["disabledReason"] = msg("disabled-granted-by", name=race["name"])
