"""resolve(draft, catalog) -> Resolution — the single entry point for all
character-rules computation, per the architecture spec's engine contract
(docs/superpowers/specs/2026-09-16-builder-v2-architecture.md §3). One
fixed-order pass: sources → species+background ability bonuses (both flow
into the SAME early pass — see _background_ability_bonuses, Phase 4b Task
4) → final ability scores → derived stats → choice generation/validation
(§4a) — never iterates to a fixpoint.

Leveling (1-20) is in scope: each resolved class's subclassId is read but
never trusted to gate a feature choice unless it actually matches, so any
feature gated to a specific subclass is filtered out rather than guessed
at. Equipment IS in scope as of Phase 2a — see engine/equipment.py and the
_equipment_choice_templates/_gather_equipped_items/_fixed_equipment
functions below. Spellcasting IS in scope as of Phase 2c — see
engine/spells.py and the _spell_choice_templates function below.

Single-class leveling (1-20), subclass selection, and ASI choices ARE in
scope as of Phase 3a — see engine/asi.py, the _asi_choice_templates/
_apply_asi_progression functions, and SUBCLASS_UNLOCK_LEVEL in
catalog/reference_data.py.

Multiclassing core IS in scope as of Phase 3b-i: draft.classes is a list
(not just a single class), resolved via resolved_classes with per-class
progression (its own level, subclass, ASIs, feature/spell choices), a
combined proficiency bonus and hit-dice string, and the multiclass-aware
proficiency rules — a PRIMARY class (resolved_classes[0], index 0) gets
its full normal grant and level-1 proficiency CHOICE, while every
SECONDARY class gets only its (usually smaller) multi_classing.*
fixed-proficiency grant and proficiency_choices choice (see
_multiclass_proficiency_choice_templates and the `rc["index"] == 0`
gating throughout resolve()), plus multiclass ability-score prerequisites
(_multiclass_prerequisite_problems). sheet["spells"] aggregates every
resolved class's spellcasting, not just the primary's.

A genuinely COMBINED spell-slot table across multiple caster classes IS in
scope as of Phase 3b-ii — see engine/spells.py's combined_caster_level/
multiclass_spell_slots/single_class_spell_slots/warlock_pact_magic_slots.
derived["spellSlots"] is the shared pool, but per PHB 164 the combined
round-down table is only used when MORE THAN ONE class grants spell
slots; with exactly one slot-granting class (even alongside other
non-caster classes), that class's own single-class progression is looked
up directly instead (see the `slot_granting_entries` branch below — fixed
post-review, since the round-down table silently undercounts a lone half
caster at every odd level). derived["warlockSpellSlots"] is Warlock's own
Pact Magic, looked up separately at Warlock's own class level and never
folded into either path above, per RAW. spellSaveDC/spellAttackBonus are
no longer top-level derived scalars — each caster in sheet["spells"] now
carries its own, since a multiclass character's casters each use their
own spellcasting ability. Still out of scope: pruning multiclass-related
warnings (Phase 3c).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from catalog.choices import build_choice_template, build_equipment_choice
from catalog.loader import Catalog
from catalog.official_source import slug, SAVE_ABILITY_NAMES
from catalog.reference_data import (
    ABILITIES, SPECIFIC_WEAPON_PROFICIENCY_IDS, SRD_TRAIT_EFFECTS, SUBCLASS_PROFICIENCIES, SUBCLASS_EXTRA_FEATURES,
)
from . import asi as asi_mod
from . import attacks as attacks_mod
from . import derived as derived_mod
from . import equipment as equipment_mod
from . import features as features_mod
from . import sheet_features as sheet_features_mod
from . import spells as spells_mod
from .normalize import normalize_draft

_DETAIL_FIELDS = (
    "alignment", "faith", "lifestyle",
    "age", "height", "weight", "eyes", "skin", "hair",
    "personalityTraits", "ideals", "bonds", "flaws",
    "backstory", "organizations", "allies", "enemies", "notes",
)


_POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
_STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]


def _ability_method_problems(abilities: dict) -> list[dict]:
    """Blocking problems for a base-score set that cannot have come from the
    chosen generation method (frontend/src/pages/AbilitiesPage.tsx enforces the
    same limits in its controls). 'manual' is unchecked; a standard array whose
    six scores are all still 10 is the untouched default, not an error."""
    method = abilities.get("method")
    base = abilities.get("base") or {}
    scores = [base.get(ab, 10) for ab in ABILITIES]
    out: list[dict] = []
    if method == "pointbuy":
        if any(not 8 <= v <= 15 for v in scores):
            out.append({"id": "point-buy-out-of-range", "message": "Point buy scores must be between 8 and 15."})
        else:
            spent = sum(_POINT_BUY_COST[v] for v in scores)
            if spent > 27:
                out.append({"id": "point-buy-over-budget", "message": f"Point buy allows 27 points but these scores cost {spent}."})
    elif method == "standard":
        if scores != [10] * 6 and sorted(scores, reverse=True) != _STANDARD_ARRAY:
            out.append({"id": "standard-array-mismatch", "message": "The standard array is 15, 14, 13, 12, 10, 8, each used once."})
    elif method == "roll":
        if any(not 3 <= v <= 18 for v in scores):
            out.append({"id": "roll-out-of-range", "message": "Rolled scores (4d6, drop the lowest) must be between 3 and 18."})
    return out


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


def _resolve_granted_feats(
    granted_feat_ids: list[str], catalog: Catalog, granted_feat_refs: list[str] | None = None,
) -> list[dict]:
    """Resolves a background's granted-feat ids (bare, source-less slugs
    — e.g. "mark-of-storm" — see official_source._feats_from_5etools'
    own docstring for why the source suffix is stripped there) against
    catalog.feats, which is keyed "slug-source" (e.g. "mark-of-storm-
    efa"). This was the ONLY mechanism resolve() had to know a character
    actually "has" a feat until the ASI-or-feat mechanic (2026-09-29)
    added its sibling, _resolve_asi_selected_feats, for a feat taken at a
    class's ASI level — a background's `feats` field, previously pure inert pass-through
    (Phase 4b Task 6: "no effect application, nothing else in this
    function reads them"), is now also read here for its mechanical
    resist/immune/condition_immune/senses effects.

    `granted_feat_refs` (Finding 1 of the final whole-branch review,
    2026-09-28), when given, is a list PARALLEL to `granted_feat_ids` —
    official_source._feats_from_5etools' new `feat_refs` field, an exact
    "slug-source" catalog id (e.g. "tavern-brawler-xphb") built from the
    SAME raw grant key the bare slug was stripped from, so the source
    that was thrown away building the bare id is recovered here. For each
    index, an exact match against catalog.feats by this ref is tried
    FIRST — that's an unambiguous, exact lookup, not a guess: the ref
    names the specific source-variant the raw data itself grants. Only
    when no ref is available at that index (None/missing — e.g. a
    shorter or absent `granted_feat_refs`, as every hand-authored test
    dict in this file's own tests builds via `_grant_synthetic_feat`) or
    the ref doesn't match any real catalog feat (e.g. a future data
    anomaly) does resolution fall back to the bare-slug logic below.
    `granted_feat_refs=None` (every call site before this task, and any
    future caller that doesn't have one) is a byte-identical no-op vs.
    the original bare-slug-only behavior.

    The bare-slug fallback matches by comparing each catalog feat's OWN
    name run through the same bare slugging _feats_from_5etools already
    applies to the grant side, not by string-prefixing the "slug-source"
    index — prefix matching risks a false match when one feat's slug is
    itself a prefix of another's (e.g. a hypothetical "Mark of Storm II"
    would prefix-match a "mark-of-storm" grant).

    When a bare slug (with no usable ref) matches feats in MORE THAN ONE
    source (9 real bare slugs — Alert, Healer, Lucky, Magic Initiate,
    Savage Attacker, Skilled, Tavern Brawler, Tough, all PHB+XPHB
    reprints, plus Aberrant Dragonmark/EFA+ERLW — confirmed 2026-09-28
    against the real fetched data), which specific source-variant a
    background actually grants can't be determined from the bare id
    alone, so it's skipped entirely rather than guessing a source. This
    guard is now reached far less often than before Finding 1's fix: 28
    of the 70 real unambiguous single-feat background grants used to hit
    it purely because their `feat_refs` didn't exist yet, even though the
    raw data named an exact source all along (e.g. Sailor/XPHB's "tavern
    brawler|xphb" now resolves via its ref to tavern-brawler-xphb
    directly, never reaching this fallback at all). The guard is kept —
    a background could in principle still name only a bare slug with no
    recoverable source (no real case today) — general rather than
    special-cased to today's data.

    A DIFFERENT, previously undisclosed failure mode (Phase 4c-i Task 6,
    found by Task 5's own review): 4 real backgrounds (Acolyte/XPHB,
    Guide/XPHB, Moonwell Pilgrim/FRHoF, Sage/XPHB) grant a ";"-suffixed
    spell-list-restricted Magic Initiate variant (e.g. "magic initiate;
    cleric|xphb") that used to slug to "magic-initiate;-cleric" — matching
    ZERO catalog feats, not "more than one." Fixed at the source
    (official_source._feats_from_5etools now strips the ";"-suffix before
    slugging, so these grants recover as plain "magic-initiate", and its
    ref as "magic-initiate-xphb") rather than here — see that function's
    own docstring for the full grounding. With Finding 1's fix, these 4
    records now resolve EXACTLY via their ref (Magic Initiate/XPHB is a
    real, unambiguous catalog entry) — they no longer fall into the
    bare-slug ambiguity guard above at all, a further improvement Finding
    1 incidentally brings along.

    Uses catalog.official_source.slug() (made public this task) rather
    than re-implementing that exact three-.replace() body inline a second
    time — a real drift risk given how much this task already had to
    reason about that function's exact behavior for the semicolon-strip
    fix above (the ";"-strip itself lives in _feats_from_5etools, which
    strips before calling slug() — slug() itself is unchanged; a
    duplicated copy here could easily have drifted from either)."""
    by_bare_slug: dict[str, list[dict]] = {}
    for feat in catalog.feats.values():
        by_bare_slug.setdefault(slug(feat["name"]), []).append(feat)
    refs = granted_feat_refs or []
    resolved = []
    for i, feat_id in enumerate(granted_feat_ids):
        ref = refs[i] if i < len(refs) else None
        if ref and ref in catalog.feats:
            resolved.append(catalog.feats[ref])
            continue
        matches = by_bare_slug.get(feat_id, [])
        if len(matches) == 1:
            resolved.append(matches[0])
    return resolved


def _feat_ability_bonuses(feats: list[dict]) -> dict[str, int]:
    """Feat-sourced counterpart to _species_ability_bonuses/
    _background_ability_bonuses (Phase 4c-i Task 6) — sums each resolved
    granted feat's own FIXED `ability_bonuses` (feat["ability_bonuses"],
    populated by official_source._ability_bonuses_from_5etools — the SAME
    {"ability_score": {"index": ...}, "bonus": ...} shape race/background
    already use) into the SAME flat {ability: total_bonus} dict those two
    functions already produce, so all three sources fold into ONE final
    ability score via simple addition at the call site (see resolve()'s
    "Final ability scores" section, which now also feeds resolved granted
    feats into this same early pass, not just species/background).

    A feat's CHOICE portion (ability_bonus_options, e.g. a hypothetical
    "+1 to one of two abilities" feat) is deliberately NOT read here —
    this function stays "fixed grants only", mirroring
    _background_ability_bonuses' own scope exactly. That choice portion is
    now handled (Phase 4c-ii Task 2, closing the gap this docstring used to
    describe) by a separate early pass right alongside this function's own
    call site in resolve()'s "Final ability scores" section, via
    _feat_ability_bonus_choice_templates/_feat_ability_bonus_deltas — kept
    apart from this function for the same reason species/background keep
    their own fixed-vs-choice ability-bonus logic in two separate
    functions each."""
    bonuses: dict[str, int] = {}
    for feat in feats:
        for entry in feat.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            bonuses[ab] = bonuses.get(ab, 0) + entry["bonus"]
    return bonuses


def _feat_proficiency_ids(feats: list[dict]) -> list[str]:
    """Flattens every resolved granted feat's FIXED `proficiencies`
    entries (feat["proficiencies"], the SAME {"index": ...}-dict-list
    shape race traits'/backgrounds' own starting_proficiencies already
    use) into a plain list of raw ids. The caller feeds this into the
    SAME two merge points race-trait/background proficiency grants
    already feed: skill-prefixed ids into proficient_skills, everything
    else through _categorize_proficiency.

    A feat's CHOICE portion (proficiency_choices, e.g. Crafter/XPHB's and
    Musician/XPHB's tool pick) is deliberately NOT read here — this
    function stays "fixed grants only", mirroring _feat_ability_bonuses'
    own scope. That choice portion is handled separately (Phase 4c-ii Task
    1, closing the gap this docstring used to describe) by
    _feat_choice_templates, which builds a real, selectable Choice for it
    instead."""
    ids: list[str] = []
    for feat in feats:
        ids.extend(p["index"] for p in feat.get("proficiencies", []))
    return ids


def _feat_languages(feats: list[dict]) -> list[str]:
    """Flattens every resolved granted feat's FIXED `languages` entries
    (feat["languages"], the SAME {"index": ...}-dict-list shape race/
    background `languages` already use) into a plain list of language
    ids — merged by the caller into the SAME `fixed_languages` list
    race+background languages already combine into.

    A feat's CHOICE portion (language_options, e.g. a hypothetical
    "learn any one language" feat) is deliberately NOT read here — this
    function stays "fixed grants only", mirroring _feat_ability_bonuses'/
    _feat_proficiency_ids' own scope. That choice portion is handled
    separately (Phase 4c-ii Task 2, closing the gap this docstring used to
    describe) by _feat_choice_templates, which builds a real, selectable
    Choice for it instead."""
    return [lang["index"] for feat in feats for lang in feat.get("languages", [])]


def _feat_expertise_skills(feats: list[dict]) -> list[str]:
    """Flattens every resolved granted feat's FIXED `expertise_skills`
    (official_source._expertise_skills_from_5etools' own "skill-{slug}"
    ids) into sheet.expertiseSkills — a brand-new sheet field (Phase 4c-i
    Task 6) with no race/background-side precedent to merge against
    (expertise is a feat-only mechanic in the bundled+official data
    today, confirmed by grep). Deduplicates (preserving first-seen order)
    in case two granted feats ever named the same skill, though not seen
    in real data today (only 2 real feats carry a fixed entry at all —
    see _expertise_skills_from_5etools' own docstring — and no background
    grants both)."""
    skills: list[str] = []
    for feat in feats:
        for skill_id in feat.get("expertise_skills", []):
            if skill_id not in skills:
                skills.append(skill_id)
    return skills


def _feat_saving_throw_proficiencies(feats: list[dict]) -> list[str]:
    """Flattens every resolved granted feat's FIXED
    `saving_throw_proficiencies` (already-uppercased ability ids, e.g.
    "CON" — official_source._saving_throw_proficiencies_from_5etools) into
    a plain list; the caller merges this into sheet.proficiencies.
    savingThrows alongside the class-granted entries already there (the
    field was class-only before this task). Deduplicates (preserving
    first-seen order), same reasoning as _feat_expertise_skills.

    Real-data note: both real feats with this field (Resilient/PHB,
    Resilient/XPHB) are choice-shaped in the raw data, so
    official_source.py's own conversion returns [] for them today (see
    that module's docstring) — this function's actual effect is exercised
    end to end by synthetic feat data in tests, not by a real background
    grant, until a sourcebook adds a feat with a genuinely FIXED
    saving-throw-proficiency grant."""
    throws: list[str] = []
    for feat in feats:
        for ab in feat.get("saving_throw_proficiencies", []):
            if ab not in throws:
                throws.append(ab)
    return throws


def _feat_senses(feats: list[dict]) -> dict[str, int]:
    """Merges `senses` from every resolved granted feat into a flat
    {sense_type: range} dict — a NEW sheet field with no race-side
    precedent to merge against (races.json carries 0/160 records with a
    `senses` field at all, confirmed 2026-09-28 — Phase 4a's race work
    genuinely never modeled senses, not a gap this task needs to close on
    the race side), so this is purely feat-sourced for now.

    When two feats grant the SAME sense type (e.g. two sources of
    blindsight), the HIGHER range wins — confirmed D&D 5e RAW (multiple
    sources of the same special sense, e.g. darkvision, don't stack
    additively; the longer range applies, unless a specific ability
    explicitly states otherwise, which none of the real granted-feat
    senses data does), not assumed. This mirrors real data too: Blind
    Fighting/XPHB and Skulker/XPHB both grant exactly blindsight 10."""
    senses: dict[str, int] = {}
    for feat in feats:
        for sense_type, value in feat.get("senses", {}).items():
            if sense_type not in senses or value > senses[sense_type]:
                senses[sense_type] = value
    return senses


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
        add("darkvision", src.get("darkvision"))
    for effect in _srd_trait_effects(race, subrace):
        for kind, value in effect.get("senses", {}).items():
            add(kind, value)
    return senses


def _srd_trait_effects(race: dict | None, subrace: dict | None) -> list[dict]:
    """reference_data.SRD_TRAIT_EFFECTS entries for every trait of the race
    and subrace (bundled SRD only; official trait ids never match)."""
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


def _species_innate_spells(race: dict | None, subrace: dict | None, catalog: Catalog,
                           variant: dict | None = None) -> list[dict]:
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
            innate.append(_innate_entry_to_sheet(entry, catalog))
    for entry in (variant or {}).get("innate_spells", []):
        innate.append(_innate_entry_to_sheet(entry, catalog))
    for effect in _srd_trait_effects(race, subrace):
        for entry in effect.get("innate_spells", []):
            innate.append(_innate_entry_to_sheet(entry, catalog))
    return innate


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


def _innate_entry_to_sheet(entry: dict, catalog: Catalog) -> dict:
    """One catalog innate-spell entry -> sheet shape, resolving spell_id
    against catalog.spells (spellId None + fallback name when absent)."""
    spell = catalog.spells.get(entry["spell_id"])
    return {
        "spellId": entry["spell_id"] if spell else None,
        "name": spell["name"] if spell else entry["name"],
        "level": entry["level"],
        "uses": entry["uses"],
        "ability": entry["ability"],
        "variant": entry["variant"],
    }


def _feat_cid_prefix(feat: dict) -> str:
    """Same cid prefix _feat_choice_templates scopes a feat's choices under."""
    return feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"


def _feat_spell_ability(feat: dict, ability, choices: list[dict], feats=(), _follow: bool = True):
    """Resolves a feat's spellcasting ability for the sheet.
    - "inherit": the ability the feat increased (its :ability-bonus choice):
      the picked ability, the candidate list while pending, or None if the
      feat has no such choice.
    - {"choose": [...]}: the ability picked in its `{prefix}:spell-ability`
      choice, else the dict unchanged (pending).
    - {"sameAsFeat": ref}: the ability of the OTHER held feat `ref` (e.g.
      Magic Connoisseur follows Magic Initiate); None if that feat isn't held.
    Anything else (a fixed "CHA", None) passes through."""
    if isinstance(ability, dict) and ability.get("choose"):
        choice = next((c for c in choices if c["id"] == f"{_feat_cid_prefix(feat)}:spell-ability"), None)
        if choice and choice.get("selected"):
            return choice["selected"][0].upper()
        return ability
    if isinstance(ability, dict) and "sameAsFeat" in ability:
        if not _follow:
            return ability
        other = next((f for f in feats if f["index"] == ability["sameAsFeat"]), None)
        if other is None:
            return None
        first = next((e["ability"] for e in (other.get("innate_spells") or []) + (other.get("spell_choices") or [])
                      if e.get("ability") is not None), None)
        if first is None:
            return None
        return _feat_spell_ability(other, first, choices, feats, _follow=False)
    if ability != "inherit":
        return ability
    cid = f"{_feat_cid_prefix(feat)}:ability-bonus"
    choice = next((c for c in choices if c["id"] == cid), None)
    if choice is None:
        return None
    if choice.get("selected"):
        return choice["selected"][0].upper()
    return {"choose": [o["id"].upper() for o in choice["options"]]}


def _feat_innate_spells(feats: list[dict], catalog: Catalog, choices: list[dict]) -> list[dict]:
    """Sheet innate-spell entries granted by feats (fixed names), each
    tagged with its featId. Not filtered by character level, matching
    the race behaviour."""
    out: list[dict] = []
    by_id = {c["id"]: c for c in choices}
    for feat in feats:
        prefix = _feat_cid_prefix(feat)
        variant_choice = by_id.get(f"{prefix}:spell-variant")
        chosen = slug(variant_choice["selected"][0]) if variant_choice and variant_choice.get("selected") else None

        def applies(variant):
            return variant is None or slug(variant) == chosen

        for entry in feat.get("innate_spells", []) or []:
            if not applies(entry.get("variant")):
                continue
            sheet_entry = _innate_entry_to_sheet(entry, catalog)
            sheet_entry["variant"] = None
            sheet_entry["ability"] = _feat_spell_ability(feat, entry["ability"], choices, feats)
            sheet_entry["featId"] = feat["index"]
            out.append(sheet_entry)
        for i, sc in enumerate(feat.get("spell_choices", []) or []):
            if not applies(sc.get("variant")):
                continue
            choice = by_id.get(f"{prefix}:spell-choice-{i}")
            if not choice:
                continue
            for sid in choice.get("selected", []):
                spell = catalog.spells.get(sid)
                if not spell:
                    continue
                out.append({
                    "spellId": sid, "name": spell["name"], "level": sc["level"], "uses": sc["uses"],
                    "ability": _feat_spell_ability(feat, sc["ability"], choices, feats),
                    "variant": None, "featId": feat["index"],
                })
    return out


def _spell_filter_options(catalog: Catalog, flt: dict) -> list[dict]:
    """Catalog spells matching a parsed feat spell filter (see
    official_source._parse_spell_filter), sorted by (level, name), as
    reference options."""
    matches = []
    for sp in catalog.spells.values():
        if "level" in flt and sp["level"] not in flt["level"]:
            continue
        if "class" in flt and not any(c["index"] in flt["class"] for c in sp.get("classes", [])):
            continue
        if "school" in flt and (sp.get("school") or {}).get("index") not in flt["school"]:
            continue
        if flt.get("ritual") and not sp.get("ritual"):
            continue
        matches.append(sp)
    matches.sort(key=lambda sp: (sp["level"], sp["name"]))
    return [{"option_type": "reference", "item": {"index": sp["index"], "name": sp["name"]}} for sp in matches]


def _spell_filter_description(count: int, flt: dict) -> str:
    level = flt.get("level")
    if level == [0]:
        core = "cantrip"
    else:
        core = (f"level {' or '.join(str(x) for x in level)} " if level else "") + "spell"
    if count != 1:
        core += "s"
    noun = core
    if flt.get("school"):
        noun = " or ".join(x.title() for x in flt["school"]) + " " + noun
    if flt.get("class"):
        noun += " from the " + " or ".join(x.title() for x in flt["class"]) + " list"
    if flt.get("ritual"):
        noun += " with the Ritual tag"
    return f"Choose {count} {noun}."


def _feat_spell_choice_templates(
    feats: list[dict], catalog: Catalog, origin: str | None = None,
    raw_selections: dict | None = None, variant_hints: dict | None = None, total_level: int = 0,
) -> list[dict]:
    """Spell Choices for feats' `spell_choices` plus, for feats with
    mutually exclusive `spell_variants`, the variant picker
    (`{prefix}:spell-variant`). Dependent choices (`{prefix}:spell-choice-{i}`,
    i = position in the FULL spell_choices list, stable across variants)
    are built only for the variant selected in `raw_selections` (the raw
    Draft selections of the owner: background choices or the owning
    class's choices). `variant_hints` ({feat index: variant name}) restricts
    a background-granted variant feat to a single option."""
    raw_selections = raw_selections or {}
    variant_hints = variant_hints or {}
    templates = []
    for feat in feats:
        prefix = origin if origin is not None else f"feat:{feat['index']}"
        source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
        if origin is not None and feat.get("_asi_level") is not None:
            source["level"] = feat["_asi_level"]
        abil = next((e["ability"] for e in (feat.get("innate_spells") or []) + (feat.get("spell_choices") or [])
                     if isinstance(e.get("ability"), dict) and e["ability"].get("choose")), None)
        if abil:
            templates.append({
                "id": f"{prefix}:spell-ability", "source": source,
                "label": f"{feat['name']}: Spellcasting Ability",
                "description": "Choose this feat's spellcasting ability.", "count": 1,
                "options": [{"id": a.lower(), "label": SAVE_ABILITY_NAMES[a.lower()]} for a in abil["choose"]],
            })
        chosen = None
        variants = feat.get("spell_variants") or []
        if variants:
            hinted = variant_hints.get(feat["index"])
            offered = [v for v in variants if v == hinted] or variants
            options = []
            for name in offered:
                fixed = [e["name"] for e in feat.get("innate_spells", []) if e.get("variant") == name]
                options.append({"id": slug(name), "label": f"{name} ({', '.join(fixed)})" if fixed else name})
            vcid = f"{prefix}:spell-variant"
            templates.append({
                "id": vcid, "source": source, "label": f"{feat['name']}: Spell List",
                "description": "Choose which spell list this feat draws from.",
                "count": 1, "options": options,
            })
            raw = raw_selections.get(vcid)
            raw = [x for x in raw if isinstance(x, str)] if isinstance(raw, list) else []
            valid = {o["id"] for o in options}
            chosen = next((x for x in raw if x in valid), None)
            if chosen is None:
                continue  # dependent templates only appear once a variant is picked
        for i, sc in enumerate(feat.get("spell_choices", []) or []):
            if sc.get("variant") is not None and slug(sc["variant"]) != chosen:
                continue
            count = sc["count"]
            if sc.get("count_by_level"):
                count = sum(n for lvl, n in sc["count_by_level"].items() if int(lvl) <= total_level)
            if sc.get("filter"):
                options = _spell_filter_options(catalog, sc["filter"])
                description = _spell_filter_description(count, sc["filter"])
                kind = "Cantrip" if sc["filter"].get("level") == [0] else "Spell"
            else:
                options = [
                    {"option_type": "reference", "item": {"index": sid, "name": catalog.spells[sid]["name"]}}
                    for sid in (sc.get("from") or []) if sid in catalog.spells
                ]
                count = min(count, len(options))
                description = f"Choose {count} spell{'s' if count != 1 else ''} from the listed options."
                kind = "Spell"
            if not options or count < 1:
                continue
            envelope = {"choose": count, "from": {"option_set_type": "options_array", "options": options}}
            tpl = build_choice_template(
                envelope, f"{prefix}:spell-choice-{i}", source, f"{feat['name']}: {kind}", description=description,
            )
            if tpl:
                if sc.get("count_by_level"):
                    tpl["count_by_level"] = sc["count_by_level"]
                templates.append(tpl)
    return templates


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
            description = "Choose one ability score improvement option."
        else:
            bonus = options[0].get("bonus", 1) if options else 1
            description = f"Choose {choose} ability score{'s' if choose != 1 else ''} to increase by {bonus}."
        return build_choice_template(envelope, cid, source, "Ability Score Increase", description=description)
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
    description = f"Choose {choose} ability score improvement option{'s' if choose != 1 else ''}."
    return build_choice_template(envelope, cid, source, "Ability Score Improvement", description=description)


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


def _feat_ability_bonus_choice_templates(feats: list[dict], origin: str | None = None) -> list[tuple[dict, dict]]:
    """Feat-side counterpart to _background_ability_bonus_choice_template/
    _species_ability_bonus_choice_template (Phase 4c-ii Task 2) — plural,
    unlike those two, because `feats` is itself a list (a background can in
    principle grant more than one feat via `feat_refs`), not a single
    `bg`/`race`. Built and applied EARLY in resolve()'s "Final ability
    scores" section, exactly like its species/background siblings — NOT
    inside _feat_choice_templates below, whose own language_options block
    is safe to build lazily (a language selection never feeds final
    ability scores) while an ability-bonus selection does, and final_scores
    must already reflect it by the time that early pass runs. The built
    templates are also appended to choice_templates later (mirroring
    background_ability_choice_tpl/species_ability_choice_tpl's own
    "compute once early, append later" pattern) so the choice is still
    visible to the player, not just silently applied.

    Returns (template, feat) pairs rather than bare templates — Finding 3
    of the final whole-branch review (2026-09-28): the cid this function
    builds (f"feat:{feat['index']}:ability-bonus") used to be reconstructed
    a SECOND time by resolve()'s own `feats_by_ability_bonus_cid` lookup
    dict, to map a selected cid back to its feat. Two independent
    constructions of the same string format is a silent-desync risk — if
    one changed and not the other, the lookup would quietly return nothing
    (the Choice would show as resolved but apply zero effect, and nothing
    would catch it). Returning the feat alongside its own template lets
    the caller build that lookup (or just iterate paired) directly off
    this return value instead, so there's only ever one place the cid
    format is written.

    `origin`, when given, replaces the default `feat:{feat['index']}`
    prefix in every cid this call builds. Only ever pass a non-None
    origin when `feats` has exactly ONE entry — origin-scoping a
    multi-feat list would collide all of them onto the same prefix,
    which is never the actual call shape either background or ASI call
    sites use. Defaults to None (unchanged Phase 4c-ii behavior, the
    `feat:{index}:...` shape background-granted feats already use).

    Final whole-branch review (2026-09-28), Important #1: an ASI-origin
    feat's cascaded ability-bonus card (and _feat_choice_templates'
    sibling proficiency/language cards below) used to render with a bare
    generic label ("Ability Score Increase") and no level, making two
    different feats' cascaded cards on ClassPage indistinguishable. Two
    fixes, both here: (1) the label is now prefixed with the feat's own
    name (e.g. "Skill Expert: Ability Score Increase") so the card is
    self-identifying regardless of level display; (2) when `origin` is
    given, the feat dict is the one `_resolve_asi_selected_feats` builds,
    which always carries `_asi_level` (the ASI-granting level this pick
    was made at) — that level is copied onto `source["level"]` so
    ChoiceCard's existing `source.level != null` display (already used
    for class-kind sources) picks it up for free. A background-granted
    feat's cascaded choice (no `origin`) has no natural "level" to show
    and is left without one, same as before."""
    pairs: list[tuple[dict, dict]] = []
    for feat in feats:
        envelope = feat.get("ability_bonus_options")
        if not envelope:
            continue
        cid_prefix = origin if origin is not None else f"feat:{feat['index']}"
        cid = f"{cid_prefix}:ability-bonus"
        source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
        if origin is not None and feat.get("_asi_level") is not None:
            source["level"] = feat["_asi_level"]
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} ability score{'s' if choose != 1 else ''} to increase by 1."
        label = f"{feat['name']}: Ability Score Increase"
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
            pairs.append((tpl, feat))
    return pairs


def _feat_ability_bonus_deltas(envelope: dict) -> dict[str, list[tuple[str, int]]]:
    """Feat-side counterpart to _background_ability_bonus_deltas — but NOT
    a direct reuse of it (confirmed by reading
    _feat_ability_bonus_options_from_5etools, catalog/official_source.py,
    fresh for this task): a feat's ability_bonus_options envelope uses the
    SAME simple, non-bundled "ability_bonus" option shape species' own
    Half-Elf choice already uses (_ability_bonus_options_from_5etools),
    NOT background's "multiple"-bundle shape
    (_ability_bonus_options_from_5etools_weighted_pair) — every option is a
    single {"option_type": "ability_bonus", "ability_score": {...},
    "bonus": ...} entry, never a bundle of several under an "items" key.
    _background_ability_bonus_deltas reads exactly that "items" key, which
    a plain ability_bonus option simply doesn't have, so it would silently
    return [] for every feat option — hence this small, disclosed variant
    instead of a direct call.

    No `built_options`/zip-by-position needed either (unlike the
    background version): build_choice_options (catalog/choices.py) sets a
    plain ability_bonus option's id to `option["ability_score"]["index"]`
    directly, so the raw envelope's own option IS already keyed by the
    same id build_choice_template produces — reading it straight off the
    envelope is simpler and can't drift out of sync with a separate
    built_options list the way a position-based zip could."""
    raw_options = envelope.get("from", {}).get("options", [])
    deltas_by_id: dict[str, list[tuple[str, int]]] = {}
    for raw_opt in raw_options:
        if raw_opt.get("option_type") != "ability_bonus":
            continue
        ability_score = raw_opt.get("ability_score") or {}
        index = ability_score.get("index")
        if not index:
            continue
        deltas_by_id[index] = [(index.upper(), raw_opt.get("bonus", 1))]
    return deltas_by_id


def _asi_granting_levels(catalog: Catalog, cls_id: str, max_level: int) -> list[int]:
    """ability_score_bonuses in a level row is a CUMULATIVE count, not a
    per-level flag — the actual ASI-granting levels are wherever the
    value increases from the previous level. Verified empirically while
    writing this plan: Fighter and Rogue both have real extra ASI levels
    (6/14 and 10) beyond the standard 4/8/12/16/19 every other class
    uses, and this diff-based approach correctly finds both."""
    levels: list[int] = []
    previous = 0
    for lvl in range(1, max_level + 1):
        row = catalog.class_level_row(cls_id, lvl)
        current = row.get("ability_score_bonuses", 0) if row else 0
        if current > previous:
            levels.append(lvl)
        previous = current
    return levels


@dataclass
class _HeldFeatState:
    """What the character already holds when an ASI-level feat pick is
    checked: feats (by catalog index), their categories, proficiency ids and
    whether any class has the Spellcasting/Pact Magic feature. One shared
    instance is accumulated through the ASI walk; per-level copies are the
    snapshots option templates read."""
    feat_indices: set[str] = field(default_factory=set)
    feat_categories: set[str] = field(default_factory=set)
    proficiency_ids: set[str] = field(default_factory=set)
    has_spellcasting_feature: bool = False

    def copy(self) -> "_HeldFeatState":
        return _HeldFeatState(
            set(self.feat_indices), set(self.feat_categories), set(self.proficiency_ids),
            self.has_spellcasting_feature,
        )

    def add_feat(self, feat: dict) -> None:
        self.feat_indices.add(feat["index"])
        if feat.get("category"):
            self.feat_categories.add(feat["category"])
        self.proficiency_ids.update(_feat_proficiency_ids([feat]))


def _apply_asi_progression(
    base_scores: dict[str, int], asi_levels: list[int], class_choices: dict, cls_id: str | None,
    asi_feats_by_cid: dict[str, dict] | None = None,
    feat_deltas_by_cid: dict[str, list[tuple[str, int]]] | None = None,
    total_level: int = 0, use_feat_prerequisites: bool = False,
    held: "_HeldFeatState | None" = None, held_by_level: dict[int, "_HeldFeatState"] | None = None,
) -> tuple[dict[int, dict[str, int]], dict[str, int], set[str]]:
    """Walks ASI-granting levels in ascending order, applying each
    level's stored selection (if present and valid) to a running
    ability-score state. Returns (scores_by_level, final_scores,
    prerequisite_blocked_feat_cids): scores_by_level[lvl] is the state
    BEFORE that level's own ASI is applied (used by _asi_choice_templates
    to compute which options are disabled for that specific level's
    choice — a combo that's fine at level 4 might exceed the cap by level
    8 once earlier ASIs stack), and final_scores is the state after every
    level's ASI has been applied — this becomes the actual final ability
    scores used for `modifiers` and everything derived from them.

    The selection is deduped first (same `dict.fromkeys` discipline the
    generic choice pass uses), so a duplicated single pick like
    ["str-plus-2", "str-plus-2"] applies instead of silently not applying
    while the generic pass shows it resolved.

    ASI-or-feat Task 3: `asi_feats_by_cid` (a level's `class:{cls_id}:{lvl}:asi`
    cid -> the feat picked there instead of a combo) and
    `feat_deltas_by_cid` (that feat's total ability-bonus delta: fixed
    ability_bonuses + its own already-chosen ability_bonus_options pick)
    both come from _resolve_asi_selected_feats. A feat pick is handled
    exactly like a combo pick, at that level's own point in the walk:
    - If its option would be shown disabled at THIS level (prerequisite
      unmet against these same running scores, via the same
      _feat_option_prerequisite_met helper _asi_choice_templates uses),
      the feat is not applied at all; its cid is returned in
      prerequisite_blocked_feat_cids so resolve() can leave it out of
      `resolved_feats` (none of its other effects apply either) and
      report it.
    - Otherwise its delta is applied only if it doesn't push any score
      over 20 (asi_mod.asi_exceeds_cap, the SAME check combos get). The
      feat itself still counts as taken; only the increase is skipped.
      (The background-side equivalent — a background-granted feat's own
      ability bonus, folded into `feat_bonuses` before this walk — stays
      uncapped: a pre-existing Phase 4c-ii gap, out of this plan's scope.)

    What keeps scores in range: resolve()'s 1-30 range check runs BEFORE
    this walk, on the pre-ASI scores, and nothing re-checks afterwards.
    This walk never needs it, because every delta it applies — combo or
    feat — is cap-gated at 20, so it never raises any score above
    max(20, that score's pre-walk value).

    With no feat maps passed (or empty ones) the feat branch is never
    taken and this is the combo-only behavior."""
    combos = dict(asi_mod.asi_combinations())
    asi_feats_by_cid = asi_feats_by_cid or {}
    feat_deltas_by_cid = feat_deltas_by_cid or {}
    scores_by_level: dict[int, dict[str, int]] = {}
    blocked_feat_cids: set[str] = set()
    running = dict(base_scores)
    for lvl in asi_levels:
        scores_by_level[lvl] = dict(running)
        if held_by_level is not None:
            held_by_level[lvl] = held.copy() if held else _HeldFeatState()
        cid = f"class:{cls_id}:{lvl}:asi"
        raw_selected = class_choices.get(cid) or []
        selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str))) if isinstance(raw_selected, list) else []
        if len(selected) == 1 and selected[0] in combos:
            deltas = combos[selected[0]]
            if not asi_mod.asi_exceeds_cap(deltas, running):
                running = asi_mod.apply_asi(deltas, running)
        elif cid in asi_feats_by_cid:
            if not _feat_option_prerequisite_met(asi_feats_by_cid[cid], total_level, running, use_feat_prerequisites, held):
                blocked_feat_cids.add(cid)
                continue
            if held is not None:
                held.add_feat(asi_feats_by_cid[cid])
            deltas = feat_deltas_by_cid.get(cid, [])
            if deltas and not asi_mod.asi_exceeds_cap(deltas, running):
                running = asi_mod.apply_asi(deltas, running)
    return scores_by_level, running, blocked_feat_cids


def _feat_source_allowed(feat: dict, sources) -> bool:
    """The SAME draft.sources filter resolve() applies to a race or
    background record, for a feat: no filtering when `sources` is empty or
    absent; a record with no source, or an "SRD" one, is always allowed;
    otherwise its source must be in the allowed list (case-insensitive)."""
    if not sources:
        return True
    allowed_sources = {s.lower() for s in sources if isinstance(s, str)}
    feat_source = feat.get("source") or ""
    return not (feat_source and feat_source.upper() != "SRD" and feat_source.lower() not in allowed_sources)


def _resolve_asi_selected_feats(
    resolved_classes: list[dict], catalog: Catalog, sources=None,
    taken_indices: set[str] | None = None, skipped_duplicates: list[dict] | None = None,
) -> tuple[list[dict], dict[str, list[tuple[str, int]]]]:
    """ASI-or-feat Task 3: the ASI-level counterpart to
    _resolve_granted_feats (background grants). Reads each resolved
    class's OWN `class_choices` for a `class:{cls_id}:{lvl}:asi` selection
    (deduped first) naming a `feat:{index}` option (offered by
    _asi_choice_templates) rather than an ASI-combo id, at every
    ASI-granting level that class has actually reached. Returns
    (asi_feat_picks, feat_deltas_by_cid):

    - asi_feat_picks: resolved feat dicts, each a shallow COPY of the
      catalog record (never the shared record itself) tagged with
      `_asi_cid` (the level's ASI cid), `_asi_level`, and
      `_asi_origin = f"{cid}:feat:{index}"` — the prefix passed as Task 1's
      `origin` param wherever this feat's own choice templates are built,
      so the same feat taken at two classes/levels never collides on cid.
      These are CANDIDATES: _apply_asi_progression decides, at each
      pick's own level, whether its prerequisite is met; resolve() then
      appends only the picks that weren't blocked to `resolved_feats`, so
      every generic feat-effects consumer picks them up unchanged.
    - feat_deltas_by_cid: that level's total ability-bonus delta (fixed
      `ability_bonuses` + the feat's own already-selected
      `ability_bonus_options` pick, if any), for _apply_asi_progression to
      apply at the right point in its per-level walk. Only levels with a
      non-empty delta get an entry.

    Task 4 (ASI-or-feat) fix round 1: an earlier version of this function
    also returned a 3rd value, `chosen_ability_deltas_by_origin`, meant to
    feed _feat_prerequisite_problems' self-bonus subtraction for
    ASI-selected feats too. Removed: it was provably either redundant or
    actively wrong. A pick only ever reaches `resolved_feats` (and
    therefore _feat_prerequisite_problems) after ALREADY passing
    _apply_asi_progression's own gate, which checks that SAME pick's
    prerequisite against that level's running scores with the pick's own
    delta excluded by construction (the delta hasn't been applied yet when
    the gate runs) — so re-subtracting it a second time in
    _feat_prerequisite_problems is never needed for a delta that WAS
    applied. Worse, for a delta that was cap-skipped (Task 3's
    asi_exceeds_cap: the feat is still granted, but that specific
    ability-score increase wasn't applied because the score was already at
    20), re-subtracting a delta that was never actually applied to
    final_scores produces a FALSE POSITIVE "prerequisite unmet" problem.
    See _feat_prerequisite_problems' own docstring for the full
    explanation of why only background-granted feats need this parameter.

    The sub-choice selection is validated exactly like resolve()'s own
    early background-feat ability-bonus pass (dedupe, keep only enabled
    option ids, cap to `count`), and its cid comes from the SAME
    _feat_ability_bonus_choice_templates call that builds the visible
    template — never reconstructed by hand here (Finding 3, 2026-09-28).

    Only a feat that _asi_choice_templates would actually offer
    (_is_asi_eligible_feat, and allowed by draft.sources via
    _feat_source_allowed) is resolved; a hand-edited draft naming some
    other catalog feat is ignored here just as the generic choice pass
    ignores it (it isn't a valid option id).

    Duplicate prevention: a non-`repeatable` feat already in
    `taken_indices` (the background's granted feats) or picked at an
    EARLIER ASI level is skipped — the first pick wins, a later duplicate
    isn't applied — and appended to `skipped_duplicates` (when given) so
    resolve() can report it."""
    asi_feat_picks: list[dict] = []
    seen: set[str] = set(taken_indices or ())
    feat_deltas_by_cid: dict[str, list[tuple[str, int]]] = {}
    for rc in resolved_classes:
        cls_id, cls, level, class_choices = rc["cls_id"], rc["cls"], rc["level"], rc["class_choices"]
        if not (cls_id and cls):
            continue
        for lvl in _asi_granting_levels(catalog, cls_id, level):
            cid = f"class:{cls_id}:{lvl}:asi"
            raw_selected = class_choices.get(cid) or []
            if not isinstance(raw_selected, list):
                continue
            selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
            if not (len(selected) == 1 and selected[0].startswith("feat:")):
                continue
            catalog_feat = catalog.feats.get(selected[0][len("feat:"):])
            if not (catalog_feat and _is_asi_eligible_feat(catalog_feat) and _feat_source_allowed(catalog_feat, sources)):
                continue
            if catalog_feat["index"] in seen and not catalog_feat.get("repeatable"):
                if skipped_duplicates is not None:
                    skipped_duplicates.append({"feat": catalog_feat, "cid": cid, "level": lvl, "cls": cls})
                continue
            seen.add(catalog_feat["index"])
            origin = f"{cid}:feat:{catalog_feat['index']}"
            feat = {**catalog_feat, "_asi_cid": cid, "_asi_level": lvl, "_asi_origin": origin}
            asi_feat_picks.append(feat)

            deltas = [(e["ability_score"]["index"].upper(), e["bonus"]) for e in feat.get("ability_bonuses", [])]
            for ability_tpl, _ in _feat_ability_bonus_choice_templates([feat], origin=origin):
                valid_ids = {o["id"] for o in ability_tpl["options"] if not o.get("disabled")}
                raw_sub = class_choices.get(ability_tpl["id"]) or []
                deduped = list(dict.fromkeys(s for s in raw_sub if isinstance(s, str)))
                chosen = [s for s in deduped if s in valid_ids][: ability_tpl["count"]]
                deltas_by_option = _feat_ability_bonus_deltas(feat["ability_bonus_options"])
                for opt_id in chosen:
                    deltas.extend(deltas_by_option.get(opt_id, []))
            if deltas:
                feat_deltas_by_cid[cid] = deltas
    return asi_feat_picks, feat_deltas_by_cid


def _class_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(cls.get("proficiency_choices", [])):
        cid = f"class:{cls_id}:1:prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"], "level": 1}
        provisional_label = "Skill Proficiencies" if envelope.get("type") == "proficiencies" else (envelope.get("type") or "Choice").title()
        tpl = build_choice_template(envelope, cid, source, provisional_label)
        if not tpl:
            continue
        # Some classes (Bard, Monk) have a SECOND proficiency_choices entry
        # also typed "proficiencies" that isn't actually a skill choice
        # (instruments/tools) — relabel based on what the resolved options
        # actually are, not the envelope's own (misleading) type field.
        if tpl["options"] and tpl["label"] == "Skill Proficiencies" and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = "Tool Proficiencies"
        templates.append(tpl)
    return templates


def _multiclass_proficiency_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    """Mirrors _class_choice_templates exactly, but sourced from
    multi_classing.proficiency_choices instead of the class's own
    top-level proficiency_choices — this is the EXTRA skill/tool choice
    a class grants when taken as a SECOND-OR-LATER class (confirmed
    empirically: Bard, Ranger, Rogue each have this; Bard has two
    envelopes — a skill choice and a musical-instrument choice)."""
    templates = []
    for i, envelope in enumerate(cls.get("multi_classing", {}).get("proficiency_choices", [])):
        cid = f"class:{cls_id}:multiclass-prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"]}
        provisional_label = "Skill Proficiencies" if envelope.get("type") == "proficiencies" else (envelope.get("type") or "Choice").title()
        tpl = build_choice_template(envelope, cid, source, provisional_label)
        if not tpl:
            continue
        if tpl["options"] and tpl["label"] == "Skill Proficiencies" and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = "Tool Proficiencies"
        templates.append(tpl)
    return templates


def _join_desc(desc) -> str | None:
    """Feature/trait 'desc' fields are lists of paragraph strings; choice
    envelopes never carry their own 'desc' except proficiency_choices (see
    Task 3's build_choice_template, which already handles a list there).
    This joins a parent object's desc for explicit passing as the
    'description' override, since the choice envelope itself has none."""
    if isinstance(desc, list):
        return " ".join(desc)
    return desc


def _sanitized_details(details_raw) -> dict | None:
    if not isinstance(details_raw, dict):
        return None
    result = {
        k: details_raw[k] for k in _DETAIL_FIELDS
        if isinstance(details_raw.get(k), str) and details_raw[k].strip()
    }
    return result if result else None


def _cumulative_feature_refs(
    catalog: Catalog, cls_id: str, subclass_id: str | None, max_level: int,
) -> list[tuple[int, dict]]:
    """Every class-level feature ref from level 1 through max_level, plus
    (once a subclass is selected) every subclass-level feature ref in the
    same range, each paired with the exact level it came from — needed so
    _feature_choice_templates can build a correctly level-suffixed choice
    id and source.level for each, not just always "1" as before Phase
    3a."""
    refs: list[tuple[int, dict]] = []
    for lvl in range(1, max_level + 1):
        row = catalog.class_level_row(cls_id, lvl)
        if row:
            refs.extend((lvl, ref) for ref in row.get("features", []))
    if subclass_id:
        for lvl in range(1, max_level + 1):
            srow = catalog.subclass_level_row(subclass_id, lvl)
            if srow:
                refs.extend((lvl, ref) for ref in srow.get("features", []))
        for lvl, idx in SUBCLASS_EXTRA_FEATURES.get(subclass_id, []):
            if lvl <= max_level:
                refs.append((lvl, {"index": idx}))
    return refs


def _expertise_envelope(raw: dict) -> dict | None:
    """Flattens a feature's `expertise_options` into a plain
    {"choose", "from"} envelope. Bard's is already flat; Rogue's nests
    "two skills" and "one skill + thieves' tools" as alternatives, which all
    come down to the same rule: choose 2 proficient skills/tools. The
    proficiency restriction is applied afterwards (_gate_expertise_choices)."""
    options = (raw.get("from") or {}).get("options") or []
    nested = next((o for o in options if o.get("option_type") == "choice"), None)
    count = nested["choice"].get("choose", 2) if nested else raw.get("choose", 1)
    flat: list[dict] = []
    seen: set[str] = set()

    def collect(opts):
        for o in opts:
            if o.get("option_type") == "reference" and o["item"]["index"] not in seen:
                seen.add(o["item"]["index"])
                flat.append({"option_type": "reference", "item": {
                    "index": o["item"]["index"], "name": o["item"]["name"].replace("Skill: ", "")}})
            elif o.get("option_type") == "choice":
                collect((o["choice"].get("from") or {}).get("options") or [])
            elif o.get("option_type") == "multiple":
                collect(o.get("items") or [])

    collect(options)
    if not flat:
        return None
    return {"choose": count, "from": {"option_set_type": "options_array", "options": flat}}


def _string_options_envelope(raw: dict) -> dict:
    """enemy_type_options / terrain_type_options list bare strings."""
    opts = [{"option_type": "string", "string": str(o).capitalize()} for o in (raw.get("from") or {}).get("options") or []]
    return {"choose": raw.get("choose", 1), "from": {"option_set_type": "options_array", "options": opts}}


def _invocation_templates(catalog: Catalog, feature: dict, cid: str, source: dict, class_level: int) -> dict | None:
    row = catalog.class_level_row(source["id"], class_level) or {}
    count = (row.get("class_specific") or {}).get("invocations_known", 0)
    if not count:
        return None
    options = []
    for ref in feature["feature_specific"]["invocations"]:
        inv = catalog.features.get(ref["index"]) or {}
        label = ref["name"].replace("Eldritch Invocation: ", "")
        option = {"id": ref["index"], "label": label}
        desc = _join_desc(inv.get("desc"))
        if desc:
            option["description"] = desc
        options.append(option)
    return {
        "id": cid, "source": source, "label": feature["name"],
        "description": _join_desc(feature.get("desc")) or "", "count": count, "options": options,
    }


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[tuple[int, dict]], subclass_id: str | None,
    class_level: int | None = None,
) -> list[dict]:
    templates = []
    if class_level is None:
        class_level = max((lvl for lvl, _ in feature_refs), default=1)
    for lvl, ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated to a different subclass than the one selected (or none selected)
        specific = feature.get("feature_specific") or {}
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        description = _join_desc(feature.get("desc"))
        # The envelopes themselves have no 'desc' key (except the string
        # lists') — the description text lives on the parent feature
        # (verified directly against 5e-SRD-Features.json), so it must be
        # passed explicitly.
        if specific.get("subfeature_options"):
            cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
            tpl = build_choice_template(specific["subfeature_options"], cid, source, feature["name"], description=description)
        elif specific.get("expertise_options"):
            # "expertise-choice" in the cid is what the expertise gate and the
            # proficiency scans key off (the same marker feat expertise uses).
            envelope = _expertise_envelope(specific["expertise_options"])
            cid = f"class:{cls_id}:{lvl}:expertise-choice:{feature['index']}"
            tpl = build_choice_template(envelope, cid, source, feature["name"], description=description) if envelope else None
        elif specific.get("enemy_type_options"):
            cid = f"class:{cls_id}:{lvl}:enemy-type:{feature['index']}"
            tpl = build_choice_template(_string_options_envelope(specific["enemy_type_options"]), cid, source, feature["name"], description=description)
        elif specific.get("terrain_type_options"):
            cid = f"class:{cls_id}:{lvl}:terrain-type:{feature['index']}"
            tpl = build_choice_template(_string_options_envelope(specific["terrain_type_options"]), cid, source, feature["name"], description=description)
        elif specific.get("invocations"):
            cid = f"class:{cls_id}:{lvl}:invocations:{feature['index']}"
            tpl = _invocation_templates(catalog, feature, cid, source, class_level)
        else:
            continue
        if tpl:
            templates.append(tpl)
    return templates


def _background_proficiency_choice_label(envelope: dict) -> str:
    """Background proficiency-choice envelopes (unlike races') don't come
    attached to a named trait to borrow a label from — backgrounds have no
    trait concept at all — so the label is derived from the envelope's own
    shape instead: any_skill, or an options_array whose first option is a
    "skill-"-prefixed reference, is a Skill Proficiency choice; any_tool (at
    any tool_category, including the None/unnarrowed "any" wildcard) or an
    options_array of anything else is a Tool Proficiency choice. Every real
    envelope official_source.py's _proficiency_choices_from_5etools
    produces is one or the other — there is no third shape."""
    from_field = envelope.get("from", {})
    set_type = from_field.get("option_set_type")
    if set_type == "any_skill":
        return "Skill Proficiency"
    if set_type == "any_tool":
        category = from_field.get("tool_category")
        return f"Tool Proficiency ({category})" if category else "Tool Proficiency"
    options = from_field.get("options", [])
    first_index = (options[0].get("item") or {}).get("index", "") if options else ""
    return "Skill Proficiency" if first_index.startswith("skill-") else "Tool Proficiency"


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
        description = f"Choose {choose} language{'s' if choose != 1 else ''} of your choice."
        tpl = build_choice_template(envelope, cid, source, "Languages", description=description)
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
        description = f"Choose {choose} proficienc{'ies' if choose != 1 else 'y'} of your choice."
        tpl = build_choice_template(prof_envelope, cid, source, label, description=description)
        if tpl:
            templates.append(tpl)

    return templates


def _feat_choice_templates(feats: list[dict], origin: str | None = None) -> list[dict]:
    """A granted feat's own choice-shaped fields, mirrored from
    _background_choice_templates' proficiency-choice/language blocks above
    (same build_choice_template call, same cid/source/label/description
    shape). Handles `proficiency_choices` (Phase 4c-ii Task 1, e.g.
    Crafter/XPHB's real "choose 3 of 8 artisan's tools" grant) and
    `language_options` (Phase 4c-ii Task 2, same "resource_list" envelope
    shape backgrounds' own language_options already uses — confirmed
    against official_source.py: a feat's language_options is built by the
    SAME _language_grants_from_5etools conversion backgrounds use). A
    feat's `ability_bonus_options` is deliberately NOT handled here — see
    _feat_ability_bonus_choice_templates' own docstring for why that one
    field needs a separate, EARLY pass instead (it feeds final ability
    scores, which are already computed by the time this function is even
    called). The ":proficiency-choice"/":languages" substrings in each cid
    are load-bearing for the same reason they are in
    _background_choice_templates' own cids (see that function's own
    comment): they're what the merge-site fixes elsewhere in this file use
    to recognize a feat-sourced proficiency or language selection.

    `origin`, when given, replaces the default `feat:{feat['index']}`
    prefix in every cid this call builds. Only ever pass a non-None
    origin when `feats` has exactly ONE entry — origin-scoping a
    multi-feat list would collide all of them onto the same prefix,
    which is never the actual call shape either background or ASI call
    sites use. Defaults to None (unchanged Phase 4c-ii behavior, the
    `feat:{index}:...` shape background-granted feats already use).

    Final whole-branch review (2026-09-28), Important #1: same two fixes
    as _feat_ability_bonus_choice_templates' own docstring above —
    (1) every label built here is now prefixed with the feat's own name
    (e.g. "Skill Expert: Skill Proficiency") so a cascaded card is
    self-identifying, applied to BOTH the ASI-origin path AND the
    background-granted path (a background-granted feat's cascaded choice
    on BackgroundPage has the exact same ambiguity problem); (2) when
    `origin` is given, `source["level"]` is set from the feat dict's own
    `_asi_level` (set by _resolve_asi_selected_feats) so ChoiceCard's
    existing level display picks it up. A background-granted feat (no
    `origin`) has no natural level and stays unset."""
    templates = []
    for feat in feats:
        cid_prefix = origin if origin is not None else f"feat:{feat['index']}"
        feat_level = feat.get("_asi_level") if origin is not None else None
        language_envelope = feat.get("language_options")
        if language_envelope:
            cid = f"{cid_prefix}:languages"
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            if feat_level is not None:
                source["level"] = feat_level
            choose = language_envelope.get("choose", 1)
            description = f"Choose {choose} language{'s' if choose != 1 else ''} of your choice."
            label = f"{feat['name']}: Languages"
            tpl = build_choice_template(language_envelope, cid, source, label, description=description)
            if tpl:
                templates.append(tpl)

        for i, prof_envelope in enumerate(feat.get("proficiency_choices", []) or []):
            cid = f"{cid_prefix}:proficiency-choice-{i}"
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            if feat_level is not None:
                source["level"] = feat_level
            base_label = _background_proficiency_choice_label(prof_envelope)
            label = f"{feat['name']}: {base_label}"
            choose = prof_envelope.get("choose", 1)
            description = f"Choose {choose} proficienc{'ies' if choose != 1 else 'y'} of your choice."
            tpl = build_choice_template(prof_envelope, cid, source, label, description=description)
            if tpl:
                templates.append(tpl)

        # Skill Expert-style expertise picks and Resilient's saving-throw
        # pick (see official_source._expertise_choices_from_5etools /
        # _saving_throw_choices_from_5etools). Deliberately NOT named
        # "proficiency-choice" so the proficiency merge branch in resolve()
        # never feeds these ids to _categorize_proficiency.
        for i, env in enumerate(feat.get("expertise_choices", []) or []):
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            if feat_level is not None:
                source["level"] = feat_level
            choose = env.get("choose", 1)
            description = f"Choose {choose} skill{'s' if choose != 1 else ''} you are proficient in to gain Expertise."
            tpl = build_choice_template(env, f"{cid_prefix}:expertise-choice-{i}", source, f"{feat['name']}: Expertise", description=description)
            if tpl:
                templates.append(tpl)

        for i, env in enumerate(feat.get("saving_throw_choices", []) or []):
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            if feat_level is not None:
                source["level"] = feat_level
            choose = env.get("choose", 1)
            description = f"Choose {choose} ability{'s' if choose != 1 else ''} to gain saving throw proficiency in."
            tpl = build_choice_template(env, f"{cid_prefix}:save-choice-{i}", source, f"{feat['name']}: Saving Throw", description=description)
            if tpl:
                templates.append(tpl)
    return templates


def _feat_selected_choice_values(choices: list[dict], marker: str) -> list[str]:
    """Selected option ids of every feat-sourced Choice whose cid contains
    `marker` (":expertise-choice-" / ":save-choice-"), deduped in order."""
    out: list[str] = []
    for c in choices:
        if c["source"]["kind"] == "feat" and marker in c["id"]:
            for sel in c.get("selected", []):
                if sel not in out:
                    out.append(sel)
    return out


def _is_expertise_choice(choice: dict) -> bool:
    """Feat expertise picks (`...:expertise-choice-N`) and class-feature ones
    (Rogue/Bard, `class:...:expertise-choice:{feature}`)."""
    return choice["source"]["kind"] in ("feat", "class") and "expertise-choice" in choice["id"]


def _expertise_selected_values(choices: list[dict]) -> list[str]:
    out: list[str] = []
    for c in choices:
        if _is_expertise_choice(c):
            for sel in c.get("selected", []):
                if sel not in out:
                    out.append(sel)
    return out


def _gate_expertise_choices(choices: list[dict], proficient_skills: set[str]) -> list[dict]:
    """Restrict every feat- or class-sourced Expertise Choice to skills (and,
    for the Rogue, tools) the character is proficient in. Mutates `choices` in place (entries replaced by index);
    returns non-blocking pruned entries for selections that were dropped."""
    pruned: list[dict] = []
    for i, c in enumerate(choices):
        if not _is_expertise_choice(c):
            continue
        options = [
            o if (o["id"] in proficient_skills or o.get("disabled"))
            else {**o, "disabled": True, "disabledReason": "not proficient"}
            for o in c["options"]
        ]
        selected = c.get("selected", [])
        kept = [s for s in selected if s in proficient_skills]
        dropped = [s for s in selected if s not in proficient_skills]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = ", ".join(labels.get(d, d) for d in dropped)
            pruned.append({
                "choiceId": c["id"],
                "reason": f"'{c['label']}': {names} is no longer a proficient skill; the Expertise selection was ignored.",
            })
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
    return pruned


def _invocation_unmet(inv: dict, warlock_level: int, pacts: set[str], cantrips: set[str]) -> str | None:
    """Why an Eldritch Invocation's prerequisites are not met, or None."""
    for req in inv.get("prerequisites") or []:
        kind = req.get("type")
        if kind == "level" and warlock_level < req.get("level", 0):
            return f"requires warlock level {req['level']}"
        if kind == "feature" and req.get("feature", "").rsplit("/", 1)[-1] not in pacts:
            return "requires " + req["feature"].rsplit("/", 1)[-1].replace("-", " ").title().replace(" Of ", " of ").replace(" The ", " the ")
        if kind == "spell" and req.get("spell", "").rsplit("/", 1)[-1] not in cantrips:
            return "requires the " + req["spell"].rsplit("/", 1)[-1].replace("-", " ") + " cantrip"
    return None


def _gate_invocation_choices(choices: list[dict], resolved_classes: list[dict], catalog: Catalog) -> list[dict]:
    """Disable Eldritch Invocation options whose prerequisites (warlock
    level, Pact Boon, Eldritch Blast) are unmet and drop stale selections of
    them. Mutates `choices` in place; returns non-blocking pruned entries."""
    pruned: list[dict] = []
    for i, c in enumerate(choices):
        if c["source"]["kind"] != "class" or ":invocations:" not in c["id"]:
            continue
        cls_id = c["source"]["id"]
        level = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == cls_id), 0)
        pacts = {sel for o in choices if o["source"].get("id") == cls_id and ":feature:" in o["id"] for sel in o["selected"]}
        cantrips = {sel for o in choices if o["id"] == f"class:{cls_id}:spells-cantrips" for sel in o["selected"]}
        options, unmet_ids = [], {}
        for o in c["options"]:
            reason = _invocation_unmet(catalog.features.get(o["id"]) or {}, level, pacts, cantrips)
            if reason:
                unmet_ids[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": reason}
            options.append(o)
        selected = [s for s in c["selected"] if s not in unmet_ids]
        dropped = [unmet_ids[s] for s in c["selected"] if s in unmet_ids]
        if dropped:
            pruned.append({
                "choiceId": c["id"],
                "reason": f"'{c['label']}': {', '.join(dropped)} no longer meets its prerequisites and was ignored.",
            })
        choices[i] = {**c, "options": options, "selected": selected,
                      "status": "resolved" if len(selected) == c["count"] else "pending"}
    return pruned


def _subclass_spell_ids(catalog: Catalog, cls_id: str, subclass_id: str | None, class_level: int,
                        feature_ids: set[str], mode: str) -> list[str]:
    """Spells from the subclass's `spells` list whose prerequisites (class
    level, and for Circle of the Land the chosen terrain feature) are met,
    for subclasses behaving as `mode` ("always" prepared / "expanded" list)."""
    from catalog import reference_data
    if not subclass_id or reference_data.SUBCLASS_SPELL_MODE.get(subclass_id, "always") != mode:
        return []
    out: list[str] = []
    for entry in (catalog.subclasses.get(subclass_id) or {}).get("spells") or []:
        spell_id = (entry.get("spell") or {}).get("index")
        if spell_id not in catalog.spells or spell_id in out:
            continue
        ok = True
        for req in entry.get("prerequisites") or []:
            if req.get("type") == "level":
                prefix, _, num = req["index"].rpartition("-")
                if prefix != cls_id or not num.isdigit() or class_level < int(num):
                    ok = False
            elif req.get("type") == "feature" and req["index"] not in feature_ids:
                ok = False
        if ok:
            out.append(spell_id)
    return out


def _species_variant_template(race: dict | None, race_id: str | None) -> dict | None:
    """The lineage / ancestry pick for a race with `variants` (2024 Elf,
    Tiefling, Gnome, Goliath, Dragonborn colours, Shifter, ...)."""
    if not (race and race_id and race.get("variants")):
        return None
    return {
        "id": f"species:{race_id}:variant",
        "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": "Lineage / Ancestry",
        "description": "Choose which lineage, ancestry or legacy this species has.",
        "count": 1,
        "options": [{"id": v["id"], "label": v["name"]} for v in race["variants"]],
    }


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


def _species_choice_templates(catalog: Catalog, race: dict, race_id: str, subrace: dict | None) -> list[dict]:
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
        if prof_envelope:
            prof_cid = f"species:{race_id}:trait:{trait['index']}:proficiency-choice"
            prof_source = {"kind": "species", "id": race_id, "label": race["name"]}
            prof_choose = prof_envelope.get("choose", 1)
            prof_description = f"Choose {prof_choose} proficienc{'ies' if prof_choose != 1 else 'y'} of your choice."
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
                description=f"Choose {lang_choose} additional language{'s' if lang_choose != 1 else ''} of your choice.",
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
        description = f"Choose {choose} additional language{'s' if choose != 1 else ''} of your choice."
        tpl = build_choice_template(envelope, cid, source, "Bonus Language", description=description)
        if tpl:
            templates.append(tpl)

    # Damage-resistance choices (Dragonborn ancestry, 2024 Tiefling legacy).
    # A race whose variants fix the resistance (Dragonborn colour, Tiefling
    # legacy) is decided by the variant pick instead of a separate choice.
    variant_decides_resistance = any(v.get("resist") for v in race.get("variants") or [])
    for src, src_id in ((race, race_id), (subrace, subrace.get("index") if subrace else None)):
        envelope = src.get("resist_options") if src else None
        if not envelope or (src is race and variant_decides_resistance):
            continue
        cid = f"species:{race_id}:resistance" if src is race else f"species:{race_id}:subspecies:{src_id}:resistance"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        tpl = build_choice_template(envelope, cid, source, "Damage Resistance", description="Choose the damage type you resist.")
        if tpl:
            templates.append(tpl)

    return templates


def _species_feat_pool(catalog: Catalog, category: str | None, sources) -> list[dict]:
    """Feats a species feat grant may be spent on. An explicit category
    ("O": Human/XPHB's Origin feat) offers exactly that category; `None`
    (the "any" grant of Variant Human and Custom Lineage) offers feats with
    no category (the 2014 books), General and Origin ones, minus the literal
    "Ability Score Improvement" entry. Epic Boon, Dragonmark, Fighting
    Style and Dragon-gift categories stay out. Filtered by draft.sources
    like every feat, sorted by name."""
    allowed = {category} if category is not None else {"", "G", "O"}
    pool = [
        f for f in catalog.feats.values()
        if (f.get("category") or "") in allowed and f["name"] != "Ability Score Improvement"
        and _feat_source_allowed(f, sources)
    ]
    pool.sort(key=lambda f: f["name"])
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


def _species_feat_choice_template(
    race: dict, race_id: str, cid: str, grant: dict, catalog: Catalog, sources, scores: dict[str, int],
    total_level: int, use_prereqs: bool, held: "_HeldFeatState", taken: set[str],
) -> dict:
    """One Choice for a species feat grant. A failed prerequisite wins over
    "already taken" as the disabled reason; the check uses the character's
    scores before any feat bonus and the total level (permissive, like the
    ASI pre-walk)."""
    options = []
    for feat in _species_feat_pool(catalog, grant["category"], sources):
        option = {"id": f"feat:{feat['index']}", "label": feat["name"]}
        reason = _feat_prerequisite_unmet_reason(feat, total_level, scores, use_prereqs, held, catalog)
        if reason:
            option["disabled"] = True
            option["disabledReason"] = reason
        elif feat["index"] in taken and not feat.get("repeatable"):
            option["disabled"] = True
            option["disabledReason"] = "already taken"
        options.append(option)
    count = grant["count"]
    noun = "an Origin feat" if grant["category"] == "O" else "a feat"
    return {
        "id": cid, "source": {"kind": "species", "id": race_id, "label": race["name"]},
        "label": "Origin Feat" if grant["category"] == "O" else "Feat",
        "description": f"Choose {noun}." if count == 1 else f"Choose {count} feats.",
        "count": count, "options": options,
    }


def _resolve_species_selected_feats(template: dict, species_choices: dict, catalog: Catalog,
                                    problems: list[dict]) -> list[dict]:
    """The feats a species template's stored selection names: deduped, only
    enabled options, capped to the count. Each is a shallow COPY of the
    catalog record tagged `_species_origin = "{choice id}:feat:{index}"`
    (the cid prefix of its own cascaded choices). A stored pick of a
    disabled option is not applied and is reported (`feat-duplicate-...`
    for "already taken", `feat-prerequisite-unmet-...` otherwise)."""
    raw = species_choices.get(template["id"])
    raw = list(dict.fromkeys(s for s in raw if isinstance(s, str))) if isinstance(raw, list) else []
    by_id = {o["id"]: o for o in template["options"]}
    picked = []
    for option_id in raw:
        option = by_id.get(option_id)
        feat = catalog.feats.get(option_id[len("feat:"):]) if option else None
        if not feat:
            continue
        if option.get("disabled"):
            if option.get("disabledReason") == "already taken":
                problems.append({
                    "id": f"feat-duplicate-{feat['index']}-{template['id']}",
                    "message": f"{feat['name']} was already taken, so the pick at {template['source']['label']} isn't applied.",
                })
            else:
                problems.append({
                    "id": f"feat-prerequisite-unmet-{feat['index']}",
                    "message": f"{feat['name']}'s prerequisite isn't met, so the {template['source']['label']} pick isn't applied.",
                })
            continue
        picked.append(feat)
    return [
        {**feat, "_species_origin": f"{template['id']}:feat:{feat['index']}"} for feat in picked[: template["count"]]
    ]



def _multiclass_prerequisite_problems(resolved_classes: list[dict], final_scores: dict[str, int], use_prerequisites: bool) -> list[dict]:
    """Checks every resolved class's multi_classing.prerequisites (a plain
    list, ALL must be met) or multi_classing.prerequisite_options (an
    options-array, "choose N of these" — Fighter is the only SRD class
    with this shape, STR-or-DEX) against the character's final ability
    scores. Applies to EVERY class, not just secondary ones — the SRD
    prerequisite is a two-way gate (both the class you already have and
    the class you're adding need their own prerequisite met), which
    matches this loop iterating over all of resolved_classes, not just
    index > 0. Never hides the class — only appends a problem.

    A character with fewer than two actually-resolved classes isn't
    multiclassing at all, so the check never applies to them regardless of
    the preference's value — otherwise a single-class character (e.g. a
    lone Wizard with low INT) would get a spurious
    multiclass-prerequisite-unmet problem for a class they aren't even
    multiclassing into."""
    if not use_prerequisites:
        return []
    if len([rc for rc in resolved_classes if rc["cls"]]) < 2:
        return []
    problems = []
    for rc in resolved_classes:
        cls, cls_id = rc["cls"], rc["cls_id"]
        if not (cls and cls_id):
            continue
        mc = cls.get("multi_classing", {})
        prereqs = mc.get("prerequisites")
        prereq_options = mc.get("prerequisite_options")
        if prereqs:
            met = all(final_scores.get(p["ability_score"]["index"].upper(), 0) >= p["minimum_score"] for p in prereqs)
        elif prereq_options:
            options = prereq_options.get("from", {}).get("options", [])
            choose = prereq_options.get("choose", 1)
            met_count = sum(
                1 for opt in options
                if final_scores.get(opt["ability_score"]["index"].upper(), 0) >= opt["minimum_score"]
            )
            met = met_count >= choose
        else:
            met = True  # no prerequisite data at all — nothing to fail
        if not met:
            problems.append({
                "id": f"multiclass-prerequisite-unmet-{cls_id}",
                "message": f"{cls['name']}'s multiclassing prerequisite isn't met.",
            })
    return problems


# The feat-prerequisite keys the BACKGROUND second pass
# (_feat_prerequisite_problems) can verify against final_scores/total_level
# alone: just level and ability. Every other real key (campaign, other,
# otherSummary, feature, race, proficiency, feat, background,
# spellcasting*, featCategory, exclusiveFeatCategory) is not checked there.
# NEVER widen this set: it would give false problems for ASI-gated picks.
# The ASI walk and option reasons use the wider _ASI_GATE_PREREQUISITE_KEYS
# below, which also needs the held-feat state.
_STRUCTURED_FEAT_PREREQUISITE_KEYS = {"level", "ability"}
# Keys the ASI-level gate (the walk + option reasons) can verify. A superset
# of _STRUCTURED_FEAT_PREREQUISITE_KEYS, which the background second pass
# (_feat_prerequisite_problems) keeps using — never widen that one.
_ASI_GATE_PREREQUISITE_KEYS = {"level", "ability", "feat", "spellcasting2020", "feature", "proficiency", "featCategory"}

# Which held app proficiency ids satisfy a 5etools prerequisite proficiency
# entry. Real data has exactly these five shapes.
_PROFICIENCY_PREREQ_SATISFIERS = {
    ("armor", "light"): {"light-armor", "all-armor"},
    ("armor", "medium"): {"medium-armor", "all-armor"},
    ("armor", "heavy"): {"heavy-armor", "all-armor"},
    ("armor", "shield"): {"shields"},
    ("weaponGroup", "martial"): {"martial-weapons"},
}


def _proficiency_entry_key(entry):
    if isinstance(entry, dict) and len(entry) == 1:
        return next(iter(entry.items()))
    return None


def _feat_ref_index(ref: str) -> str:
    """A 5etools "name|source" feat reference -> its catalog index."""
    name, _, source = ref.partition("|")
    return f"{slug(name)}-{source.lower()}"


def _alt_value_is_valid(key: str, value) -> bool:
    if key == "level":
        return isinstance(value, int)
    if key == "feat":
        return isinstance(value, list) and bool(value) and all(isinstance(r, str) and "|" in r for r in value)
    if key == "featCategory":
        return isinstance(value, list) and bool(value) and all(isinstance(c, str) for c in value)
    if key == "proficiency":
        return isinstance(value, list) and bool(value) and all(
            _proficiency_entry_key(e) in _PROFICIENCY_PREREQ_SATISFIERS for e in value
        )
    if key == "spellcasting2020":
        return isinstance(value, bool)
    if key == "feature":
        return (
            isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and v in ("Spellcasting", "Pact Magic") for v in value)
        )
    return True  # ability shape is tolerated as before


def _alt_is_verifiable(alt, supported_keys) -> bool:
    return (
        isinstance(alt, dict) and set(alt.keys()) <= supported_keys
        and all(_alt_value_is_valid(k, v) for k, v in alt.items())
    )


def _feat_structured_prerequisite(feat: dict, supported_keys=None) -> list[dict] | None:
    """Returns feat["prerequisite"] (a 5etools-shaped list of alternative
    requirement objects — met if ANY ONE alternative is fully met, exactly
    like multi_classing.prerequisite_options' own "choose N of these"
    OR-semantics above) when EVERY alternative in it is verifiable under
    `supported_keys` (key subset and valid value shapes). Returns None (no
    problem ever raised) when the feat has no prerequisite data at all,
    OR when ANY alternative carries a key this app can't check (campaign,
    feature, proficiency, feat, race, background, spellcasting*,
    featCategory/exclusiveFeatCategory, other, otherSummary).

    Deliberately an ALL-or-nothing gate per feat, not a per-alternative
    partial check: an OR-of-alternatives prerequisite where one
    alternative is verifiable and another isn't (e.g. Purple Dragon
    Commandant/FRHoF: "level 4 + Purple Dragon Rook feat" OR "martial
    weapon-group proficiency" — confirmed real, 2026-09-28) can't be
    soundly evaluated: verifying only the checkable alternative and
    failing it would be a FALSE "unmet" whenever the unverifiable
    alternative is actually the one the character satisfies. Skipping the
    whole feat in that case is the same "disclosed non-enforcement, not a
    silently wrong enforcement" choice this task's brief calls for
    generally, not narrowly special-cased to fully-non-structured feats.

    `supported_keys` defaults to level/ability (background second pass);
    the ASI gate passes _ASI_GATE_PREREQUISITE_KEYS. Real-data shapes
    (2026-10-08): of the 94 ASI-eligible feats, 50 are entirely
    level/ability; the other 44 use feat / spellcasting2020 / feature /
    proficiency / featCategory, enforced only by the ASI gate. Level/ability
    examples — everything
    from single-alternative ("Ability Score Improvement": level 4 only) to
    multi-alternative OR shapes (Athlete/Charger/Grappler/etc.: level 4 +
    (STR 13 OR DEX 13), two separate alternative objects) — both are
    handled identically by _feat_prerequisite_alt_met's own per-alternative
    check below."""
    prereq = feat.get("prerequisite") or []
    if not prereq:
        return None
    if supported_keys is None:
        supported_keys = _STRUCTURED_FEAT_PREREQUISITE_KEYS
    if not all(_alt_is_verifiable(alt, supported_keys) for alt in prereq):
        return None
    return prereq


def _feat_prerequisite_alt_met(
    alt: dict, total_level: int, final_scores: dict[str, int], held: "_HeldFeatState | None" = None,
) -> bool:
    """Checks ONE alternative requirement object (both its "level" and
    "ability" keys must be satisfied together — AND within an
    alternative, exactly like _multiclass_prerequisite_problems' own
    `all(...)` over a class's plain `prerequisites` list). `ability`'s own
    value is a LIST of single-key {ability: minimum} dicts — real data's
    only multi-entry case (Ritual Caster/PHB: `[{"int": 13}, {"wis":
    13}]`, published text "Intelligence or Wisdom 13 or higher") is
    itself an OR of independent options, not a simultaneous requirement to
    meet every one, confirmed against the real published feat text — so
    meeting ANY ONE entry in the list satisfies this alt's own ability
    requirement."""
    level_req = alt.get("level")
    if isinstance(level_req, int) and total_level < level_req:
        return False
    ability_req = alt.get("ability")
    if ability_req:
        if not any(
            final_scores.get(ab.upper(), 0) >= minimum
            for entry in ability_req if isinstance(entry, dict)
            for ab, minimum in entry.items()
        ):
            return False
    held = held or _HeldFeatState()
    if "feat" in alt and not any(_feat_ref_index(r) in held.feat_indices for r in alt["feat"]):
        return False
    if (alt.get("spellcasting2020") or "feature" in alt) and not held.has_spellcasting_feature:
        return False
    if "featCategory" in alt and not any(c in held.feat_categories for c in alt["featCategory"]):
        return False
    if not all(
        held.proficiency_ids & _PROFICIENCY_PREREQ_SATISFIERS[_proficiency_entry_key(e)]
        for e in alt.get("proficiency", [])
    ):
        return False
    return True


def _feat_instance_key(feat: dict) -> str:
    """A per-INSTANCE key for a resolved feat dict (Task 4, ASI-or-feat).
    The SAME catalog feat (same `feat['index']`) can be picked at TWO
    different ASI instances — two different classes, or two different
    levels of the same class — each with its OWN chosen ability-bonus
    sub-choice (e.g. Grappler taken at both Fighter 4 and Ranger 8, one
    instance +1 STR, the other +1 DEX). A bare-index-keyed dict would
    collide the two instances' deltas, silently overwriting one with the
    other. `_asi_origin` (Task 1's origin param, set by
    _resolve_asi_selected_feats) is exactly the unique cid prefix
    _feat_ability_bonus_choice_templates already scopes that instance's own
    choice templates under, so reusing it here as the dict key is
    guaranteed to match. A background-granted feat carries no `_asi_origin`
    (there's only ever one instance of a given background grant), so it
    falls back to its bare `feat:{index}` — the SAME default cid prefix
    _feat_ability_bonus_choice_templates itself uses for an un-scoped
    (origin=None) call."""
    return feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"


def _feat_prerequisite_problems(
    feats: list[dict], total_level: int, final_scores: dict[str, int], use_prerequisites: bool,
    chosen_ability_deltas_by_instance: dict[str, list[tuple[str, int]]] | None = None,
) -> list[dict]:
    """Structural precedent: _multiclass_prerequisite_problems above — same
    "only check if the preference is on," same "append a problem, NEVER
    block or hide the underlying grant" (a feat with an unmet prerequisite
    still fully applies its effects; this only surfaces a `problems` entry
    for the player to see), same per-item problem id convention
    (f"multiclass-prerequisite-unmet-{cls_id}" there ->
    f"feat-prerequisite-unmet-{feat_id}" here).

    Takes already-RESOLVED feat dicts (mirrors _multiclass_prerequisite_
    problems taking already-resolved `resolved_classes`, not raw class
    ids + catalog) rather than (catalog, feat_ids) — resolve() already
    computes `resolved_feats` once, early, via _resolve_granted_feats (the
    Task 6 hoist — see resolve()'s own comment at that call site), and
    every OTHER feat-effects function added by this same task
    (_feat_ability_bonuses, _feat_proficiency_ids, _feat_languages,
    _feat_expertise_skills, _feat_saving_throw_proficiencies) already
    takes that same already-resolved list rather than re-resolving it a
    second time — this stays consistent with that, rather than the
    (catalog, feat_ids) shape floated at plan-writing time before the
    current code (and its actual resolution point) was read fresh.

    Finding 2 of the final whole-branch review (2026-09-28): `final_scores`
    is ALREADY post-hoist (Task 6) — it includes every resolved granted
    feat's own `ability_bonuses`, folded in during the SAME early
    ability-score pass species/background bonuses feed (see resolve()'s
    "Final ability scores" comment, and _feat_ability_bonuses' own
    docstring). Checking feat F's prerequisite against that score
    unmodified would let F's OWN ability bonus satisfy F's OWN
    prerequisite — e.g. Actor/XPHB (real: CHA +1 fixed bonus, prerequisite
    CHA >= 13) could bootstrap its own gate using the CHA+1 it itself
    grants, which is wrong: a prerequisite is checked against the
    character BEFORE the feat being considered is applied. No CURRENT
    real background grant happens to combine a self-satisfying bonus+
    prerequisite this way (so this was latent, not visibly broken), but 7
    real XPHB feats have exactly this shape (Actor, Crossbow Expert,
    Defensive Duelist, Great Weapon Master, Keen Mind, Sharpshooter,
    Skulker — confirmed 2026-09-28) and it will matter the moment feats
    become player-selectable (the deliberately-deferred "ASI or feat"
    mechanic).

    Fixed by subtracting each feat's OWN ability_bonuses back out of
    final_scores before checking THAT feat's own prerequisite — a
    per-feat, per-check adjustment (computed fresh for each feat in the
    loop, not shared across feats): a DIFFERENT simultaneously-granted
    feat's bonus, or species'/background's own bonus, legitimately still
    counts, since it isn't F's own contribution being subtracted.

    Task 4 (ASI-or-feat) extends this SAME discipline to a feat's own
    CHOSEN ability_bonus_options delta, via the new
    `chosen_ability_deltas_by_instance` param — keyed by _feat_instance_key
    (see its own docstring), NOT bare `feat['index']`, since the same
    catalog feat picked at two different ASI instances (two classes, or
    two levels of one class) each carries its OWN chosen delta. 10 real
    General feats combine an ability prerequisite with a choice-shaped
    ability bonus (Athlete, Charger, Dual Wielder, Grappler, Inspiring
    Leader, Observant, Polearm Master, Ritual Caster, Sentinel, Speedy),
    confirmed 2026-09-28.

    Fix round 1 (reviewer finding): this param is fed ONLY
    resolve()'s early background-feat ability-choice pass's own
    chosen-only deltas (keyed by bare `feat:{index}`) — deliberately
    NEVER anything derived from an ASI-selected feat. An ASI-selected
    feat's own prerequisite is already checked, using that level's own
    running scores with that pick's own delta excluded by construction
    (the check runs inside _apply_asi_progression's per-level gate,
    BEFORE the delta is applied), and a pick that fails that gate is
    filtered out of `resolved_feats` before this function ever sees it.
    An earlier version of this fix ALSO built and merged in a dict from
    _resolve_asi_selected_feats (a since-removed 3rd return value,
    `chosen_ability_deltas_by_origin`) — proven wrong: for a pick whose
    delta was cap-skipped (asi_exceeds_cap: the feat still applies, but
    that specific ability-score increase doesn't, because the score was
    already at the 20 cap), re-subtracting a delta that was never
    actually added to `final_scores` produces a false "prerequisite
    unmet" problem for a feat whose prerequisite is genuinely fine. Only
    a background-granted feat needs this explicit subtraction at all,
    since it has no equivalent per-level gate — its own chosen bonus is
    applied unconditionally, with nothing else ever checking whether its
    prerequisite held before that bonus landed."""
    if not use_prerequisites:
        return []
    chosen_ability_deltas_by_instance = chosen_ability_deltas_by_instance or {}
    problems = []
    for feat in feats:
        prereq = _feat_structured_prerequisite(feat)
        if prereq is None:
            continue  # no prerequisite data, or a shape this app can't verify — never enforced, not guessed at
        # Subtract THIS feat's own ability_bonuses back out — see docstring
        # above. A fresh copy per feat: other feats' own bonuses (and
        # species'/background's) are left untouched in `final_scores`
        # itself and in every other feat's own check this same loop runs.
        scores_without_own_bonus = dict(final_scores)
        for entry in feat.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            scores_without_own_bonus[ab] = scores_without_own_bonus.get(ab, 0) - entry["bonus"]
        # Task 4: subtract THIS feat's own CHOSEN ability-bonus delta back
        # out too, same discipline, keyed by this feat's own instance.
        for ab_key, delta in chosen_ability_deltas_by_instance.get(_feat_instance_key(feat), []):
            scores_without_own_bonus[ab_key] = scores_without_own_bonus.get(ab_key, 0) - delta
        if not any(_feat_prerequisite_alt_met(alt, total_level, scores_without_own_bonus) for alt in prereq):
            problems.append({
                "id": f"feat-prerequisite-unmet-{feat['index']}",
                "message": f"{feat['name']}'s prerequisite isn't met.",
            })
    return problems


def _asi_option_label(deltas: list[tuple[str, int]]) -> str:
    return " and ".join(f"{ab} +{delta}" for ab, delta in deltas)


def _is_asi_eligible_feat(feat: dict) -> bool:
    # "General"-category feats (category == "G") double as the "take a feat
    # instead" branch of an ASI choice. The literal "Ability Score
    # Improvement" catalog entry is excluded because it duplicates this
    # app's own hardcoded ASI-combo mechanic, not a distinct choice. Shared
    # by _asi_choice_templates (which options to offer) and
    # _resolve_asi_selected_feats (which selections to honor) so the two
    # can't drift apart.
    return feat.get("category") == "G" and feat["name"] != "Ability Score Improvement"


def _feat_prerequisite_unmet_reason(
    feat: dict, total_level: int, scores: dict[str, int], use_prerequisites: bool,
    held: "_HeldFeatState | None" = None, catalog: Catalog | None = None,
) -> str | None:
    """None when the ASI-level gate lets the feat through (prerequisites
    off, no structured prerequisite verifiable under
    _ASI_GATE_PREREQUISITE_KEYS, or any alternative met); otherwise
    "prerequisite not met", with ": requires ..." appended when there is
    exactly one alternative. Shared by the ASI walk and the option
    templates so the two always agree."""
    if not use_prerequisites:
        return None
    prereq = _feat_structured_prerequisite(feat, _ASI_GATE_PREREQUISITE_KEYS)
    if prereq is None:
        return None
    if any(_feat_prerequisite_alt_met(alt, total_level, scores, held) for alt in prereq):
        return None
    reason = "prerequisite not met"
    if len(prereq) == 1:
        parts = _feat_prerequisite_failing_parts(prereq[0], total_level, scores, held, catalog)
        if parts:
            reason += ": requires " + "; ".join(parts)
    return reason


def _feat_prerequisite_failing_parts(
    alt: dict, total_level: int, scores: dict[str, int], held: "_HeldFeatState | None", catalog: Catalog | None,
) -> list[str]:
    parts: list[str] = []
    level_req = alt.get("level")
    if isinstance(level_req, int) and total_level < level_req:
        parts.append(f"character level {level_req}")
    ability_req = alt.get("ability")
    if ability_req and not _feat_prerequisite_alt_met({"ability": ability_req}, total_level, scores, held):
        parts.append(" or ".join(
            f"{ab.upper()} {minimum}"
            for entry in ability_req if isinstance(entry, dict) for ab, minimum in entry.items()
        ))
    if (alt.get("spellcasting2020") or "feature" in alt) and not (held and held.has_spellcasting_feature):
        parts.append("the Spellcasting or Pact Magic feature")
    if "featCategory" in alt and not any(c in (held.feat_categories if held else ()) for c in alt["featCategory"]):
        parts.append("a Dragonmark feat" if alt["featCategory"] == ["D"] else "a feat of a required category")
    for entry in alt.get("proficiency", []):
        satisfiers = _PROFICIENCY_PREREQ_SATISFIERS[_proficiency_entry_key(entry)]
        if not (held and held.proficiency_ids & satisfiers):
            kind, value = _proficiency_entry_key(entry)
            if kind == "weaponGroup":
                parts.append("martial weapon proficiency")
            else:
                parts.append(f"{value} armor proficiency" if value != "shield" else "shield proficiency")
    if "feat" in alt and not _feat_prerequisite_alt_met({"feat": alt["feat"]}, total_level, scores, held):
        names = []
        for ref in alt["feat"]:
            record = (catalog.feats.get(_feat_ref_index(ref)) if catalog else None)
            names.append(f"the {record['name']} feat" if record else f"the {ref.partition('|')[0].title()} feat")
        parts.append(" or ".join(names))
    return parts


def _feat_option_prerequisite_met(
    feat: dict, total_level: int, scores: dict[str, int], use_prerequisites: bool,
    held: "_HeldFeatState | None" = None,
) -> bool:
    """Whether an ASI-level feat option is ENABLED as far as its
    prerequisite goes, against a given level's running scores and held
    state. See _feat_prerequisite_unmet_reason."""
    return _feat_prerequisite_unmet_reason(feat, total_level, scores, use_prerequisites, held) is None


def _asi_choice_templates(
    cls_id: str, cls_name: str, asi_levels: list[int], scores_by_level: dict[int, dict[str, int]],
    catalog: Catalog, total_level: int, use_prerequisites: bool, sources=None,
    taken_by_level: dict[int, set[str]] | None = None,
    held_by_level: dict[int, "_HeldFeatState"] | None = None,
) -> list[dict]:
    # `taken_by_level`: per ASI level, the feat indices already held from a
    # background grant or an earlier ASI pick — offered disabled unless the
    # feat is `repeatable`.
    # `sources` is draft.sources: feat options are filtered exactly like a
    # race/background record (see _feat_source_allowed). SRD-only drafts
    # therefore get zero feat options — the 2014 SRD has no feats.
    general_feats = [
        f for f in catalog.feats.values() if _is_asi_eligible_feat(f) and _feat_source_allowed(f, sources)
    ]
    general_feats.sort(key=lambda f: f["name"])
    templates = []
    for lvl in asi_levels:
        current_scores = scores_by_level.get(lvl, {})
        options = []
        for option_id, deltas in asi_mod.asi_combinations():
            option = {"id": option_id, "label": _asi_option_label(deltas)}
            if asi_mod.asi_exceeds_cap(deltas, current_scores):
                option["disabled"] = True
                option["disabledReason"] = "would exceed the ability score cap of 20"
            options.append(option)
        for feat in general_feats:
            option = {"id": f"feat:{feat['index']}", "label": feat["name"]}
            reason = _feat_prerequisite_unmet_reason(
                feat, total_level, current_scores, use_prerequisites,
                (held_by_level or {}).get(lvl) or _HeldFeatState(), catalog,
            )
            if reason:
                option["disabled"] = True
                option["disabledReason"] = reason
            elif feat["index"] in (taken_by_level or {}).get(lvl, ()) and not feat.get("repeatable"):
                option["disabled"] = True
                option["disabledReason"] = "already taken"
            options.append(option)
        cid = f"class:{cls_id}:{lvl}:asi"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": "Ability Score Improvement",
            "description": "Increase one ability score by 2, or two ability scores by 1 each — or take a feat instead.",
            "count": 1,
            "options": options,
        })
    return templates


def _envelope_needs_expansion(envelope: dict) -> bool:
    """True for starting-equipment envelopes that reference an
    equipment_category set, directly or through a nested option_type
    "choice" (alone or inside a "multiple" bundle)."""
    from_field = envelope.get("from") or {}
    if from_field.get("option_set_type") == "equipment_category":
        return True
    for opt in from_field.get("options", []):
        members = opt.get("items", []) if opt.get("option_type") == "multiple" else [opt]
        if any(m.get("option_type") == "choice" for m in members):
            return True
    return False


def _equipment_choice_templates(
    entity: dict, source_kind: str, source_id: str, source_label: str, items: dict | None = None,
) -> tuple[list[dict], int, dict[str, dict[str, list[dict]]]]:
    """Returns (templates, dropped envelope count, dependents) where
    dependents is {choice id: {option id: [follow-up templates]}} for
    options that contain a nested pick (see catalog.choices.
    build_equipment_choice); resolve() adds them once that option is
    selected."""
    templates = []
    dependents_by_choice: dict[str, dict[str, list[dict]]] = {}
    dropped_envelopes = 0
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        if items is not None and _envelope_needs_expansion(envelope):
            tpl, dependents = build_equipment_choice(envelope, cid, source, "Starting Equipment", items)
            if tpl and dependents:
                dependents_by_choice[cid] = dependents
        else:
            tpl = build_choice_template(envelope, cid, source, "Starting Equipment")
        if not tpl:
            dropped_envelopes += 1
            continue
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (tpl["description"] + " (Note: one or more of the original options for this choice aren't available yet and have been left out.)").strip()
        templates.append(tpl)
    return templates, dropped_envelopes, dependents_by_choice


def _spell_options(catalog: Catalog, cls_id: str, spell_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if s["level"] == spell_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: s["name"])
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _spell_options_up_to(catalog: Catalog, cls_id: str, max_level: int) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if 1 <= s["level"] <= max_level and any(c["index"] == cls_id for c in s.get("classes", []))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _highest_spell_slot_level(spellcasting: dict) -> int:
    highest = 0
    for n in range(1, 10):
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0:
            highest = n
    return highest


def _is_count_variable_choice(tpl: dict) -> bool:
    """True for the spell choices whose allowed count follows the class
    level table / casting modifier (see _spell_choice_templates), so a
    stored over-count is staleness rather than a malformed Draft. Mirrors
    `isSpellChoice` in frontend/src/pages/ClassPage.tsx."""
    if tpl.get("count_by_level"):
        return True  # level-scaled feat spell picks (Ritual Caster): over-count is staleness
    if tpl["source"]["kind"] == "class" and ":invocations:" in tpl["id"]:
        return True  # Eldritch Invocations known follow the warlock level table
    return tpl["source"]["kind"] == "class" and tpl["id"].endswith((":spells-cantrips", ":spells-known"))


def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int, class_level: int,
    expanded_spell_ids: list[str] = (), always_prepared: dict[str, str] | None = None,
) -> list[dict]:
    if not level_row:
        return []
    spellcasting = level_row.get("spellcasting") or {}
    templates = []
    # No `level` in source — these choices span every level a spellcaster
    # has reached (count grows as they level up), so they're not anchored
    # to one specific level the way a feature/ASI choice is.
    source = {"kind": "class", "id": cls_id, "label": cls["name"]}

    cantrips_known = spellcasting.get("cantrips_known", 0)
    if cantrips_known > 0:
        envelope = {"choose": cantrips_known, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, cls_id, spell_level=0),
        }}
        cid = f"class:{cls_id}:spells-cantrips"
        description = f"Choose {cantrips_known} cantrip{'s' if cantrips_known != 1 else ''} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, "Cantrips Known", description=description)
        if tpl:
            templates.append(tpl)

    known_count = spells_mod.known_spell_count(level_row, ability_modifier, class_level=class_level, cls_id=cls_id)
    if known_count > 0:
        max_spell_level = _highest_spell_slot_level(spellcasting)
        option_list = _spell_options_up_to(catalog, cls_id, max_spell_level)
        present = {o["item"]["index"] for o in option_list}
        for sid in expanded_spell_ids:  # e.g. Fiend Expanded Spell List
            spell = catalog.spells[sid]
            if sid not in present and 1 <= spell["level"] <= max_spell_level:
                option_list.append({"option_type": "reference", "item": {"index": sid, "name": spell["name"]}})
        option_list.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": option_list,
        }}
        cid = f"class:{cls_id}:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None
        label = "Spells Known" if is_known_caster else "Prepared Spells"
        verb = "know" if is_known_caster else "prepare"
        level_word = "spell" if max_spell_level == 1 else f"level-{max_spell_level}-or-lower spell"
        description = f"Choose {known_count} {level_word}{'s' if known_count != 1 else ''} to {verb} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
            for opt in tpl["options"]:
                if opt["id"] in (always_prepared or {}):
                    opt["disabled"] = True
                    opt["disabledReason"] = f"always prepared ({always_prepared[opt['id']]})"
            templates.append(tpl)

    return templates


def _fixed_equipment(entries: list[dict], item_lookup: dict) -> list[dict]:
    result = []
    for entry in entries:
        equipment_ref = entry.get("equipment") or {}
        item_id = equipment_ref.get("index")
        item = item_lookup.get(item_id) if item_id else None
        if not item:
            continue
        result.append({"itemId": item_id, "name": item["name"], "qty": entry.get("quantity", 1)})
    return result


def _gather_equipped_items(
    equipment_choices: list[dict], added_entries: list[dict], item_lookup: dict,
) -> list[dict]:
    equipped: list[dict] = []
    for choice in equipment_choices:
        for selected_id in choice["selected"]:
            for item_id in selected_id.split("+"):
                item = item_lookup.get(item_id)
                if item:
                    equipped.append(item)
    for entry in added_entries:
        if not isinstance(entry, dict) or not entry.get("equipped"):
            continue
        item_id = entry.get("itemId")
        item = item_lookup.get(item_id) if isinstance(item_id, str) else None
        if item:
            equipped.append(item)
    return equipped


def _chosen_equipment(equipment_choices: list[dict], item_lookup: dict) -> list[dict]:
    result: list[dict] = []
    for choice in equipment_choices:
        for selected_id in choice["selected"]:
            for item_id in selected_id.split("+"):
                item = item_lookup.get(item_id)
                if item:
                    result.append({"itemId": item_id, "name": item["name"], "qty": 1})
    return result


def _selected_gold_and_narrative_items(equipment_choices: list[dict]) -> tuple[int, list[str]]:
    """A small, disclosed second pass over the SAME selected-equipment ids
    _gather_equipped_items/_chosen_equipment already iterate (each
    selected_id split on "+"), reading the parts THOSE functions
    deliberately skip because they aren't real catalog.items entries.
    official_source.py synthesizes exactly three such non-catalog "of"
    references for 5etools bundle members with no catalog equivalent —
    gp-{amount} (a gold value), flavor-{slug} ({"special": ...} flavor
    text), and category-{slug}/unlisted-{slug} (an {"equipmentType": ...}
    category placeholder or an unrecognized item name) — see that module's
    _equipment_bundle_member_from_5etools/_counted_reference_for_item_name
    docstrings. This does NOT change what item_lookup.get(item_id) returns
    or how real catalog items are matched; it only recovers the gold
    amount and narrative label from the ids those functions already saw
    and silently dropped.

    catalog/choices.py's own _bundle_label_and_id builds a bundle option's
    "+"-joined id and " + "-joined label from the SAME per-member loop, in
    the SAME order (id_parts.append(...)/label_parts.append(...) side by
    side) — so zipping a selected option's id.split("+") against its own
    label.split(" + ") recovers each member's real display label, rather
    than re-deriving a lossy one from the synthetic id's slug."""
    gold = 0
    narrative_items: list[str] = []
    for choice in equipment_choices:
        options_by_id = {opt["id"]: opt for opt in choice.get("options", [])}
        for selected_id in choice["selected"]:
            option = options_by_id.get(selected_id)
            if option is None:
                continue
            id_parts = selected_id.split("+")
            label_parts = option["label"].split(" + ")
            zipped = label_parts if len(label_parts) == len(id_parts) else None
            for i, item_id in enumerate(id_parts):
                if item_id.startswith("gp-"):
                    amount = item_id[len("gp-"):]
                    if amount.isdigit():
                        gold += int(amount)
                elif item_id.startswith(("flavor-", "category-", "unlisted-")):
                    # zipped is None only if an item's own name literally
                    # contains "+" or " + ", throwing off the split — falls
                    # back to a slug-derived label rather than dropping it.
                    narrative_items.append(zipped[i] if zipped else item_id.split("-", 1)[1].replace("-", " "))
    return gold, narrative_items


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
                opt["disabledReason"] = f"already granted by {bg['name']}"


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
                opt["disabledReason"] = f"already granted by {race['name']}"


def _class_feature_list(catalog: Catalog, resolved_classes: list[dict], choices: list[dict] | None = None) -> list[tuple[str, int, str]]:
    """(class_id, class_level, feature_index) for every class/subclass
    feature the character has, plus selected feature options (e.g. a
    chosen Fighting Style) read from `choices` when given."""
    out: list[tuple[str, int, str]] = []
    for rc in resolved_classes:
        if not rc["cls"] or not rc["cls_id"]:
            continue
        for _lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
            feature = catalog.features.get(ref["index"])
            sub = (feature or {}).get("subclass")
            if sub and sub.get("index") != rc["subclass_id"]:
                continue
            out.append((rc["cls_id"], rc["level"], ref["index"]))
    for c in choices or []:
        src = c.get("source") or {}
        if src.get("kind") == "class" and ":feature:" in c["id"]:
            for sel in c.get("selected") or []:
                lvl = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == src.get("id")), 0)
                out.append((src["id"], lvl, sel))
    return out


def resolve(draft: dict, catalog: Catalog) -> dict:
    draft, problems = normalize_draft(draft)
    warnings: list[dict] = []

    classes_raw = draft.get("classes")
    if classes_raw is None:
        classes_raw = []
    elif not isinstance(classes_raw, list):
        problems.append({"id": "malformed-classes", "message": "'classes' must be a list."})
        classes_raw = []
    classes = [c for c in classes_raw if isinstance(c, dict)]
    if len(classes) != len(classes_raw):
        problems.append({"id": "malformed-class-entry", "message": "one or more entries in 'classes' were not objects and were ignored."})

    seen_class_ids: set[str] = set()
    deduped_classes: list[dict] = []
    for c in classes:
        cid_check = c.get("classId")
        if cid_check in seen_class_ids:
            problems.append({"id": "duplicate-class", "message": f"'{cid_check}' appears more than once in classes — only the first entry is used."})
            continue
        if cid_check is not None:
            seen_class_ids.add(cid_check)
        deduped_classes.append(c)
    classes = deduped_classes

    resolved_classes: list[dict] = []
    for idx, entry in enumerate(classes):
        entry_cls_id = entry.get("classId")
        entry_subclass_id = entry.get("subclassId")
        entry_level = 1
        raw_level = entry.get("level", 1)
        try:
            entry_level = int(raw_level)
        except (TypeError, ValueError):
            problems.append({"id": "level-unsupported", "message": f"Level {raw_level!r} for '{entry_cls_id}' isn't a valid number; using 1 instead."})
            entry_level = 1
        if not (1 <= entry_level <= 20):
            problems.append({"id": "level-unsupported", "message": f"Level {entry_level} for '{entry_cls_id}' is out of the 1-20 range; using 1 instead."})
            entry_level = 1

        entry_cls = catalog.classes.get(entry_cls_id) if entry_cls_id else None
        if entry_cls_id and not entry_cls:
            problems.append({"id": "unknown-class", "message": f"Unknown class '{entry_cls_id}'."})

        entry_subclass = catalog.subclasses.get(entry_subclass_id) if entry_subclass_id else None
        if entry_subclass_id and not entry_subclass:
            problems.append({"id": "unknown-subclass", "message": f"Unknown subclass '{entry_subclass_id}'."})
            entry_subclass_id = None
        elif entry_subclass and entry_cls_id and entry_subclass.get("class", {}).get("index") != entry_cls_id:
            problems.append({
                "id": "subclass-mismatch",
                "message": f"'{entry_subclass['name']}' isn't a subclass of '{entry_cls_id}'.",
            })
            entry_subclass_id = None

        entry_choices_raw = entry.get("choices")
        entry_class_choices = entry_choices_raw if isinstance(entry_choices_raw, dict) else {}

        resolved_classes.append({
            "index": idx, "cls_id": entry_cls_id, "cls": entry_cls, "level": entry_level,
            "subclass_id": entry_subclass_id, "subclass": entry_subclass, "class_choices": entry_class_choices,
        })

    # Computed AFTER the per-class loop above (not from raw `classes`), so
    # this reflects each entry's CLAMPED/validated level — an out-of-range
    # submitted level (e.g. 25) is reset to 1 by that loop, and this check
    # must agree with the level that's actually used everywhere else in
    # resolve(), not the raw, never-used submitted value.
    total_level = sum(rc["level"] for rc in resolved_classes)
    if total_level > 20:
        problems.append({"id": "total-level-exceeded", "message": f"Total character level {total_level} exceeds the 20-level cap."})

    primary = resolved_classes[0] if resolved_classes else None
    cls_id = primary["cls_id"] if primary else None
    cls = primary["cls"] if primary else None
    subclass_id = primary["subclass_id"] if primary else None
    subclass = primary["subclass"] if primary else None
    level = primary["level"] if primary else 1
    class_choices = primary["class_choices"] if primary else {}

    background_raw = draft.get("background")
    if background_raw is not None and not isinstance(background_raw, dict):
        problems.append({"id": "malformed-background", "message": "'background' must be an object."})
        background_raw = {}
    background_dict = background_raw or {}
    bg_id = background_dict.get("id")
    bg = catalog.backgrounds.get(bg_id) if bg_id else None
    if bg_id and not bg:
        problems.append({"id": "unknown-background", "message": f"Unknown background '{bg_id}'."})
    elif bg and draft.get("sources"):
        # Mirrors the race-side source filter immediately below, exactly
        # (Phase 4a Task 7): a filtered-out record and a genuinely-
        # nonexistent one are indistinguishable from the player's point of
        # view ("not a valid choice right now") — reuse the same
        # "unknown-background" problem id rather than introduce a new one.
        # Bundled SRD backgrounds have no 'source' field at all (implicitly
        # SRD), so they're always allowed regardless of draft.sources; only
        # an official background whose book isn't in the allowed list gets
        # rejected.
        bg_source = bg.get("source") or ""
        allowed_sources = {s.lower() for s in draft["sources"] if isinstance(s, str)}
        if bg_source and bg_source.upper() != "SRD" and bg_source.lower() not in allowed_sources:
            problems.append({"id": "unknown-background", "message": f"Unknown background '{bg_id}'."})
            bg = None

    # Phase 4b Task 6: a background's `feats` field lands on the sheet as a
    # list of bare ids unchanged — no prerequisite checking here. Always a
    # list (never null), mirroring damage_modifiers/condition_immunities/
    # innate_spells' own "always present, empty when absent" convention.
    # Phase 4c-i Task 5: no longer PURELY inert — resolved (best-effort;
    # see _resolve_granted_feats) against catalog.feats so each granted
    # feat's resist/immune/condition_immune/senses can be folded into the
    # SAME sheet fields race/subrace already populate. Phase 4c-i Task 6
    # HOISTS this resolution from its old position (right before sheet
    # assembly, well after ability scores and proficiencies were already
    # finalized) up to HERE — right after `bg` itself is resolved, and
    # before species/ability-score/proficiency processing below — because
    # this task adds MORE feat-granted effect types (ability bonuses,
    # proficiencies, languages, expertise, saving throws) that need to
    # flow into the SAME early merge points species/background bonuses
    # and race/background proficiencies already feed, not a separate,
    # later, parallel path. `resolved_feats` (used throughout the rest of
    # resolve()) is a real structural relocation of existing Task 5 logic,
    # not new resolution behavior.
    granted_feats = list(bg.get("feats", [])) if bg else []
    # Finding 2 of the final whole-branch review (2026-09-27): a background
    # whose real `feats` data is an "alternatives" grant (Rewarded/Ruined,
    # BMT — "gain Lucky, Magic Initiate, or Skilled, your choice") now
    # contributes nothing to `granted_feats` and instead surfaces its
    # candidates here, kept distinct from an actual grant for the same
    # inert-pass-through reason `feat_options` itself exists in
    # official_source.py — see that field's own docstring. feat_options
    # candidates are NOT resolved for effects — they're unresolved
    # alternatives, not something the character actually has yet.
    feat_options = list(bg.get("feat_options", [])) if bg else []
    # Finding 1 of the final whole-branch review (2026-09-28): `feat_refs`
    # is a THIRD, source-qualified parallel to `granted_feats` (see
    # official_source._feats_from_5etools' own docstring) — passed through
    # so _resolve_granted_feats can try an exact "slug-source" match
    # before falling back to its bare-slug ambiguity logic. Bundled SRD
    # backgrounds and hand-authored test dicts carry no `feat_refs` key at
    # all, so this defaults to `[]`, a safe no-op (see that function's own
    # docstring for why `granted_feat_refs=None`/empty behaves identically
    # to before this fix).
    granted_feat_refs = list(bg.get("feat_refs", [])) if bg else []
    background_feats = _resolve_granted_feats(granted_feats, catalog, granted_feat_refs)
    # ASI-or-feat Task 3: a feat a class took INSTEAD of an ASI joins the
    # SAME `resolved_feats` list (assembled right after the per-class ASI
    # loop below, once each pick's prerequisite has been checked at its own
    # level), so every generic feat-effects consumer (proficiencies,
    # languages, expertise, saving throws, senses, damage modifiers,
    # condition immunities, prerequisite problems) applies it with no
    # special-casing. `background_feats` is kept apart for exactly the
    # three places where an ASI-selected feat must NOT be handled the
    # background way: its ability bonus (fixed + chosen) is applied inside
    # _apply_asi_progression's per-level walk via `asi_feat_deltas_by_cid`,
    # not in the early flat `feat_bonuses` pass (that would double-apply it
    # and put it before earlier levels' cap checks); and its own choice
    # templates are built origin-scoped in the per-class loop, not with the
    # default un-scoped `feat:{index}:...` cids (which would duplicate them).
    species_raw = draft.get("species")
    if species_raw is not None and not isinstance(species_raw, dict):
        problems.append({"id": "malformed-species", "message": "'species' must be an object."})
        species_raw = {}
    species = species_raw or {}
    race_id = species.get("id")
    race = catalog.races.get(race_id) if race_id else None
    if race_id and not race:
        problems.append({"id": "unknown-species", "message": f"Unknown species '{race_id}'."})
    elif race and draft.get("sources"):
        # A filtered-out record and a genuinely-nonexistent one are
        # indistinguishable from the player's point of view ("not a valid
        # choice right now") — reuse the same problem id rather than
        # introduce a new one. Bundled SRD races have no 'source' field at
        # all (implicitly SRD), so they're always allowed regardless of
        # draft.sources; only an official race whose book isn't in the
        # allowed list gets rejected.
        race_source = race.get("source") or ""
        allowed_sources = {s.lower() for s in draft["sources"] if isinstance(s, str)}
        if race_source and race_source.upper() != "SRD" and race_source.lower() not in allowed_sources:
            problems.append({"id": "unknown-species", "message": f"Unknown species '{race_id}'."})
            race = None

    subrace_id = species.get("subspeciesId")
    subrace = catalog.subraces.get(subrace_id) if subrace_id else None
    if subrace_id and not subrace:
        problems.append({"id": "unknown-subspecies", "message": f"Unknown subspecies '{subrace_id}'."})
    elif subrace and (not race or subrace.get("race", {}).get("index") != race_id):
        problems.append({
            "id": "subspecies-mismatch",
            "message": f"'{subrace['name']}' isn't a subspecies of the selected species.",
        })
        subrace = None

    # Read here (before the per-class loop) so _asi_choice_templates can use
    # it below; `use_prereqs` (multiclass) is derived from the SAME dict
    # further down, near _multiclass_prerequisite_problems.
    species_choices_raw = species.get("choices") if isinstance(species.get("choices"), dict) else {}
    # Slice 8b: the selected lineage / ancestry / legacy of a race with `variants`.
    species_variant = _selected_species_variant(race, species_choices_raw, race_id)
    use_prerequisites_prefs = (draft.get("preferences") or {}).get("usePrerequisites", {})
    use_feat_prereqs = bool(use_prerequisites_prefs.get("feats"))

    held = _HeldFeatState()
    for bg_feat in background_feats:
        held.add_feat(bg_feat)
    # Pre-walk inputs use the FINAL character (same simplification as
    # total_level): permissive, never a false disable.
    held.has_spellcasting_feature = any(
        rc["cls"] and spells_mod.single_class_spell_slots(catalog, rc["cls_id"], rc["level"])
        for rc in resolved_classes
    )
    # FIXED proficiency grants only (class, race/subrace traits, background);
    # proficiency CHOICE selections aren't available before the ASI walk.
    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        class_profs = (
            rc["cls"].get("proficiencies", []) if rc["index"] == 0
            else rc["cls"].get("multi_classing", {}).get("proficiencies", [])
        )
        held.proficiency_ids.update(p["index"] for p in class_profs)
    if race:
        for ref in list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else []):
            trait = catalog.traits.get(ref["index"])
            if trait:
                held.proficiency_ids.update(p["index"] for p in trait.get("proficiencies", []))
    if bg:
        held.proficiency_ids.update(p["index"] for p in bg.get("starting_proficiencies", []))

    # Final ability scores: base + species bonuses + background bonuses +
    # feat bonuses. Backgrounds DO grant ability bonuses as of Phase 4b
    # Task 4 — the 2024-style ability-score-improvement choice (see
    # _background_ability_bonus_choice_template below) — so background
    # selections flow into this SAME early pass alongside species' own,
    # exactly like species_bonuses does just below. Phase 4c-i Task 6:
    # `resolved_feats` (already computed above, right after `bg` itself)
    # is a THIRD source into this same pass, via _feat_ability_bonuses —
    # that function stays fixed-grants-only by design (mirroring
    # _background_ability_bonuses' own scope). The feat's CHOICE portion
    # (ability_bonus_options) is no longer an unhandled gap: it's the
    # FOURTH source folded in just below via feat_ability_choice_tpls
    # (Phase 4c-ii Task 2).
    base_scores = (draft.get("abilities") or {}).get("base") or {}
    problems += _ability_method_problems(draft.get("abilities") or {})
    species_bonuses = _species_ability_bonuses(race, subrace)
    species_ability_choice_tpl = _species_ability_bonus_choice_template(race, subrace, race_id)
    if species_ability_choice_tpl:
        valid_ability_ids = {o["id"] for o in species_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = species_choices_raw.get(species_ability_choice_tpl["id"]) or []
        # Dedupe BEFORE capping to `count` and applying bonuses — otherwise a
        # duplicate selection (e.g. ["str", "str"]) would apply the same
        # ability's bonus twice with no problem reported.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_abilities = [s for s in deduped_selected if s in valid_ability_ids][: species_ability_choice_tpl["count"]]
        # Deltas come from the option itself: +1 for the SRD Half-Elf and
        # `count` choices, +2 for `amount: 2` choices, and +2/+1 or +1/+1/+1
        # bundles for VRGR lineages. Env is the race's or subrace's, whichever
        # supplied the template.
        env_src = next(src for src in _ability_sources(race, subrace) if src.get("ability_bonus_options"))
        species_deltas = _background_ability_bonus_deltas(env_src["ability_bonus_options"], species_ability_choice_tpl["options"])
        for ab_id in selected_abilities:
            for ab_key, delta in species_deltas.get(ab_id, []):
                species_bonuses[ab_key] = species_bonuses.get(ab_key, 0) + delta

    background_bonuses = _background_ability_bonuses(bg)
    background_ability_choice_tpl = _background_ability_bonus_choice_template(bg, bg_id)
    if background_ability_choice_tpl:
        background_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}
        valid_bundle_ids = {o["id"] for o in background_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = background_choices_raw.get(background_ability_choice_tpl["id"]) or []
        # Same dedupe-before-cap-and-apply discipline as species' own pass
        # just above.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_bundles = [s for s in deduped_selected if s in valid_bundle_ids][: background_ability_choice_tpl["count"]]
        bundle_deltas = _background_ability_bonus_deltas(bg["ability_bonus_options"], background_ability_choice_tpl["options"])
        for bundle_id in selected_bundles:
            for ab_key, delta in bundle_deltas.get(bundle_id, []):
                background_bonuses[ab_key] = background_bonuses.get(ab_key, 0) + delta

    # Slice 8a: feats a species grants (Human/XPHB's Origin feat, Variant
    # Human's and Custom Lineage's free feat). Resolved BEFORE the ASI walk
    # so a species pick makes the same feat unavailable at an ASI level
    # (precedence: background -> species -> ASI levels, first pick wins).
    # Checked against the scores before any feat bonus and a snapshot of what
    # the character holds from the background alone.
    species_feat_templates: list[dict] = []
    species_feats: list[dict] = []
    if race:
        pre_feat_scores = {}
        for ab in derived_mod.ABILITIES:
            try:
                raw_base = int(base_scores.get(ab, 10))
            except (TypeError, ValueError):
                raw_base = 10
            pre_feat_scores[ab] = raw_base + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0)
        species_held_snapshot = held.copy()
        taken_feat_indices = {f["index"] for f in background_feats}
        for slot_cid, grant in _species_feat_grant_slots(race, subrace, race_id):
            tpl = _species_feat_choice_template(
                race, race_id, slot_cid, grant, catalog, draft.get("sources"), pre_feat_scores, total_level,
                use_feat_prereqs, species_held_snapshot, taken_feat_indices,
            )
            species_feat_templates.append(tpl)
            picked = _resolve_species_selected_feats(tpl, species_choices_raw, catalog, problems)
            species_feats += picked
            taken_feat_indices |= {f["index"] for f in picked}
    for species_feat in species_feats:
        held.add_feat(species_feat)

    skipped_duplicate_asi_feats: list[dict] = []
    asi_feat_picks, asi_feat_deltas_by_cid = _resolve_asi_selected_feats(
        resolved_classes, catalog, draft.get("sources"),
        taken_indices={f["index"] for f in background_feats + species_feats}, skipped_duplicates=skipped_duplicate_asi_feats,
    )
    for dup in skipped_duplicate_asi_feats:
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": f"{dup['feat']['name']} was already taken, so the pick at {dup['cls']['name']} level {dup['level']} isn't applied.",
        })
    asi_feats_by_cid = {f["_asi_cid"]: f for f in asi_feat_picks}
    # Walk order of every ASI cid (class order, then level) — the "first
    # pick wins" order _resolve_asi_selected_feats applies duplicates in.
    asi_feat_order = {
        f"class:{rc['cls_id']}:{lvl}:asi": n
        for n, (rc, lvl) in enumerate(
            (rc, lvl) for rc in resolved_classes if rc["cls_id"] and rc["cls"]
            for lvl in _asi_granting_levels(catalog, rc["cls_id"], rc["level"])
        )
    }
    prerequisite_blocked_asi_feat_cids: set[str] = set()

    feat_bonuses = _feat_ability_bonuses(background_feats + species_feats)  # ASI-selected feats' bonuses: see _apply_asi_progression

    # Phase 4c-ii Task 2: a FOURTH source into this same early pass — a
    # background-granted feat's own ability_bonus_options CHOICE (as
    # opposed to _feat_ability_bonuses' fixed-only grant, folded in via
    # `feat_bonuses` above). `feats` (plural) means more than one template
    # can exist at once in principle, hence a loop rather than the
    # single-`if` shape species/background use above. A feat has no
    # section of its own in the Draft — every real and synthetic
    # background-granted feat's own Choice selections live under the SAME
    # `background.choices` dict the background's own choices already use
    # (confirmed against test_selecting_the_crafter_tool_choice_reaches_
    # the_sheet's exact draft shape, Phase 4c-ii Task 1) — hence reading
    # from `background_choices_raw` here too, not a separate dict.
    #
    # `_feat_ability_bonus_choice_templates` returns (template, feat) pairs
    # rather than bare templates precisely so each feat is looked up
    # directly off its own pair here, instead of this call site
    # reconstructing the "feat:{index}:ability-bonus" cid a second time to
    # build its own lookup dict — see that function's own docstring
    # (Finding 3 of the final whole-branch review, 2026-09-28) for the
    # silent-desync risk that duplication used to carry.
    feat_ability_choice_pairs = _feat_ability_bonus_choice_templates(background_feats)
    feat_ability_choice_tpls = [tpl for tpl, _ in feat_ability_choice_pairs]
    # Task 4 (ASI-or-feat): this SAME loop already computes each
    # background-granted feat's own selected ability-bonus ids and their
    # deltas (feeding `feat_bonuses` above) — also record them here, keyed
    # by _feat_instance_key(source_feat) (a background grant has no
    # `_asi_origin`, so this is its bare `feat:{index}`), so
    # _feat_prerequisite_problems can subtract a feat's own CHOSEN bonus
    # back out before checking THAT feat's own prerequisite, exactly like
    # it already does for a feat's FIXED ability_bonuses. Passed to
    # _feat_prerequisite_problems' `chosen_ability_deltas_by_instance` param
    # BELOW UNMIXED with anything ASI-derived (fix round 1: an earlier
    # version also merged in a dict built from _resolve_asi_selected_feats,
    # which was removed as provably redundant-or-wrong — see
    # _feat_prerequisite_problems' own docstring for why only a
    # background-granted feat's own chosen bonus needs this explicit
    # subtraction at all).
    background_chosen_ability_deltas_by_instance: dict[str, list[tuple[str, int]]] = {}
    if feat_ability_choice_tpls:
        feat_background_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}
        for feat_ability_tpl, source_feat in feat_ability_choice_pairs:
            valid_feat_ability_ids = {o["id"] for o in feat_ability_tpl["options"] if not o.get("disabled")}
            raw_selected = feat_background_choices_raw.get(feat_ability_tpl["id"]) or []
            # Same dedupe-before-cap-and-apply discipline as species'/
            # background's own passes above.
            deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
            selected_feat_abilities = [s for s in deduped_selected if s in valid_feat_ability_ids][: feat_ability_tpl["count"]]
            feat_ability_deltas = _feat_ability_bonus_deltas(source_feat["ability_bonus_options"])
            instance_chosen_deltas: list[tuple[str, int]] = []
            for ab_id in selected_feat_abilities:
                for ab_key, delta in feat_ability_deltas.get(ab_id, []):
                    feat_bonuses[ab_key] = feat_bonuses.get(ab_key, 0) + delta
                    instance_chosen_deltas.append((ab_key, delta))
            if instance_chosen_deltas:
                background_chosen_ability_deltas_by_instance[_feat_instance_key(source_feat)] = instance_chosen_deltas
    # Species-granted feats: the same pass, selections read from
    # species.choices under each feat's own `_species_origin` prefix.
    species_feat_ability_tpls: list[dict] = []
    for species_feat in species_feats:
        for feat_ability_tpl, source_feat in _feat_ability_bonus_choice_templates([species_feat], origin=species_feat["_species_origin"]):
            species_feat_ability_tpls.append(feat_ability_tpl)
            valid_feat_ability_ids = {o["id"] for o in feat_ability_tpl["options"] if not o.get("disabled")}
            raw_selected = species_choices_raw.get(feat_ability_tpl["id"]) or []
            deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
            selected_feat_abilities = [s for s in deduped_selected if s in valid_feat_ability_ids][: feat_ability_tpl["count"]]
            feat_ability_deltas = _feat_ability_bonus_deltas(source_feat["ability_bonus_options"])
            instance_chosen_deltas = []
            for ab_id in selected_feat_abilities:
                for ab_key, delta in feat_ability_deltas.get(ab_id, []):
                    feat_bonuses[ab_key] = feat_bonuses.get(ab_key, 0) + delta
                    instance_chosen_deltas.append((ab_key, delta))
            if instance_chosen_deltas:
                background_chosen_ability_deltas_by_instance[_feat_instance_key(source_feat)] = instance_chosen_deltas

    final_scores: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        raw = base_scores.get(ab, 10)
        try:
            base_score = int(raw)
        except (TypeError, ValueError):
            problems.append({"id": f"ability-invalid-{ab}", "message": f"{ab} score {raw!r} isn't a valid number; using 10 instead."})
            base_score = 10
        final_scores[ab] = base_score + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0) + feat_bonuses.get(ab, 0)
    for ab, score in final_scores.items():
        if not (1 <= score <= 30):
            problems.append({"id": f"ability-out-of-range-{ab}", "message": f"{ab} score {score} is out of the 1-30 range."})

    choice_templates: list[dict] = []
    for rc in resolved_classes:
        rc_held_by_level: dict[int, _HeldFeatState] = {}
        rc_cls, rc_cls_id, rc_level, rc_subclass_id = rc["cls"], rc["cls_id"], rc["level"], rc["subclass_id"]
        rc_class_choices = rc["class_choices"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_asi_levels = _asi_granting_levels(catalog, rc_cls_id, rc_level)
        rc_asi_scores_by_level, final_scores, rc_blocked_feat_cids = _apply_asi_progression(
            final_scores, rc_asi_levels, rc_class_choices, rc_cls_id,
            asi_feats_by_cid, asi_feat_deltas_by_cid, total_level, use_feat_prereqs,
            held=held, held_by_level=rc_held_by_level,
        )
        prerequisite_blocked_asi_feat_cids |= rc_blocked_feat_cids
        # A feat picked at an ASI level whose option is disabled there
        # (prerequisite unmet at THAT level's running scores — the same
        # data the option's `disabled` flag is computed from) is not
        # applied at all, exactly like an over-cap combo pick; reported
        # here so the player sees why, since unlike an over-cap combo it
        # may not be obvious from the option list alone.
        for blocked_cid in sorted(rc_blocked_feat_cids):
            blocked_feat = asi_feats_by_cid[blocked_cid]
            problems.append({
                "id": f"feat-prerequisite-unmet-{blocked_feat['index']}",
                "message": (
                    f"{blocked_feat['name']}'s prerequisite isn't met at {rc_cls['name']} level "
                    f"{blocked_feat['_asi_level']}, so it isn't applied."
                ),
            })
        rc["asi_levels"] = rc_asi_levels  # stashed for Task 4's prerequisite check convenience, and for sheet assembly

        if rc["index"] == 0:
            choice_templates += _class_choice_templates(rc_cls, rc_cls_id)
        else:
            choice_templates += _multiclass_proficiency_choice_templates(rc_cls, rc_cls_id)
        rc_level_row = catalog.class_level_row(rc_cls_id, rc_level)
        rc["level_row"] = rc_level_row
        feature_refs = _cumulative_feature_refs(catalog, rc_cls_id, rc_subclass_id, rc_level)
        choice_templates += _feature_choice_templates(catalog, rc_cls_id, rc_cls["name"], feature_refs, rc_subclass_id, class_level=rc_level)
        choice_templates += _asi_choice_templates(
            rc_cls_id, rc_cls["name"], rc_asi_levels, rc_asi_scores_by_level, catalog, total_level, use_feat_prereqs,
            draft.get("sources"),
            taken_by_level={
                lvl: {f["index"] for f in background_feats + species_feats}
                | {f["index"] for f in asi_feat_picks if asi_feat_order.get(f["_asi_cid"], 1 << 30) < asi_feat_order.get(f"class:{rc_cls_id}:{lvl}:asi", -1)}
                for lvl in rc_asi_levels
            },
            held_by_level=rc_held_by_level,
        )
        # ASI-or-feat Task 3: a feat THIS class took at one of its own ASI
        # levels cascades its own choice-shaped content right here, scoped
        # under that feat's `_asi_origin` (Task 1's `origin` param, one feat
        # per call as that param requires). The selections live in this
        # class's own `class_choices`, already merged into `all_selections`
        # below; the generic "feat"-kind merge sites (skills, tools,
        # languages) pick them up by source.kind + cid substring unchanged.
        # The ability-bonus template's selection was already applied via
        # _resolve_asi_selected_feats/_apply_asi_progression above — it's
        # built again here (same function, same cid) only to be shown. A
        # prerequisite-blocked pick cascades nothing: it isn't applied.
        for asi_feat in asi_feat_picks:
            if asi_feat["_asi_cid"] in rc_blocked_feat_cids:
                continue
            if asi_feat["_asi_origin"].startswith(f"class:{rc_cls_id}:"):
                choice_templates += _feat_choice_templates([asi_feat], origin=asi_feat["_asi_origin"])
                choice_templates += _feat_spell_choice_templates(
                    [asi_feat], catalog, origin=asi_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level,
                )
                choice_templates += [
                    tpl for tpl, _ in _feat_ability_bonus_choice_templates([asi_feat], origin=asi_feat["_asi_origin"])
                ]

    asi_selected_feats = [f for f in asi_feat_picks if f["_asi_cid"] not in prerequisite_blocked_asi_feat_cids]
    resolved_feats = background_feats + species_feats + asi_selected_feats

    use_prereqs = bool(use_prerequisites_prefs.get("multiclass"))
    problems += _multiclass_prerequisite_problems(resolved_classes, final_scores, use_prereqs)
    # Phase 4c-i Task 6: a NEW sibling key on the SAME usePrerequisites
    # dict the multiclass toggle already uses (`use_prerequisites_prefs`,
    # read once before the per-class loop above so _asi_choice_templates
    # could also use it via `use_feat_prereqs`) — not a separate
    # preferences shape. `final_scores` here is already POST-ASI-progression
    # (the loop above reassigns it via _apply_asi_progression before this
    # line runs), matching what a player's actual final character sheet
    # shows.
    #
    # Task 4 (ASI-or-feat): passes ONLY the background-side dict built
    # above (background_chosen_ability_deltas_by_instance, keyed by bare
    # `feat:{index}`) — nothing ASI-derived is merged in here (fix round
    # 1). An ASI-selected feat's own prerequisite is already checked
    # earlier, inside _apply_asi_progression's per-level gate (Task 3),
    # against that level's own running scores with the pick's own delta
    # excluded by construction (the gate runs BEFORE that delta is
    # applied) — a pick that fails that gate is filtered out of
    # `resolved_feats` entirely and never reaches this call. So an
    # ASI-origin feat here has ALREADY had its own bonus's influence on
    # its own prerequisite correctly excluded; re-subtracting it a second
    # time via this parameter would be redundant at best (the delta WAS
    # applied, so it's already legitimately excluded by the gate's own
    # scores) and wrong at worst (if the delta was cap-skipped by
    # asi_exceeds_cap — the feat still granted, but that specific
    # increase never applied — subtracting a delta that was never added
    # to `final_scores` produces a false "prerequisite unmet"). Only a
    # background-granted feat needs the explicit subtraction this
    # function does, since it has no equivalent per-level gate.
    problems += _feat_prerequisite_problems(
        resolved_feats, total_level, final_scores, use_feat_prereqs, background_chosen_ability_deltas_by_instance,
    )

    # Primal Champion et al.: fixed ability-score feature bonuses, applied
    # after ASIs and prerequisite checks (the 24 cap is theirs alone).
    final_scores = features_mod.apply_ability_bonuses(
        final_scores, features_mod.active_effects(_class_feature_list(catalog, resolved_classes)),
    )
    modifiers = derived_mod.ability_modifiers(final_scores)
    # Prof bonus is confirmed class-agnostic at a given level (per the
    # design spec's empirical check), so any resolved class's level table
    # can be used to look it up — but it must be looked up at TOTAL level
    # (summed across every class), not any single class's own level.
    # `total_level` here reuses the SAME variable computed above (from
    # resolved_classes' clamped/validated levels) for the
    # total-level-exceeded check.
    prof_bonus_lookup_cls_id = next((rc["cls_id"] for rc in resolved_classes if rc["cls"]), None)
    prof_bonus_row = catalog.class_level_row(prof_bonus_lookup_cls_id, total_level) if prof_bonus_lookup_cls_id else None
    prof_bonus = prof_bonus_row["prof_bonus"] if prof_bonus_row else 2

    # Spell choices need `modifiers` (for spellcasting-ability-driven known-
    # spell counts), which isn't final until EVERY class's ASI progression
    # has run — hence this is a SECOND loop over resolved_classes, not
    # merged into the loop above.
    for rc in resolved_classes:
        rc_cls, rc_cls_id, rc_level, rc_level_row = rc["cls"], rc["cls_id"], rc["level"], rc.get("level_row")
        if not (rc_cls and rc_cls_id):
            continue
        spell_ability = spells_mod.spellcasting_ability(rc_cls)
        if spell_ability and rc_level_row:
            raw_feature_ids = {
                sel for cid, sels in rc["class_choices"].items() if ":feature:" in cid and isinstance(sels, list)
                for sel in sels if isinstance(sel, str)
            }
            sub_name = rc["subclass"]["name"] if rc["subclass"] else ""
            choice_templates += _spell_choice_templates(
                catalog, rc_cls, rc_cls_id, rc_level_row, modifiers[spell_ability], class_level=rc_level,
                expanded_spell_ids=_subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "expanded"),
                always_prepared={
                    sid: f"{sub_name}" for sid in
                    _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "always")
                },
            )

    asi_levels = primary.get("asi_levels", []) if primary else []
    level_row = primary.get("level_row") if primary else None
    if bg and bg_id:
        choice_templates += _background_choice_templates(bg, bg_id)
        if background_ability_choice_tpl:
            choice_templates.append(background_ability_choice_tpl)
    # Phase 4c-ii Task 1: `resolved_feats` is already computed above (right
    # after `bg` itself is resolved) regardless of whether `bg` is present —
    # it defaults to `[]` when there's no background, so this call is a
    # safe no-op in that case, not gated behind `if bg and bg_id` like the
    # background-choice-templates call just above.
    choice_templates += _feat_spell_choice_templates(
        background_feats, catalog,
        raw_selections=background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {},
        variant_hints=(bg.get("feat_variant_hints") if bg else None) or {},
        total_level=total_level,
    )
    choice_templates += _feat_choice_templates(background_feats)  # ASI-selected feats' templates: built origin-scoped in the per-class loop
    # Phase 4c-ii Task 2: `feat_ability_choice_tpls` was already built (and
    # applied to `feat_bonuses`) EARLY, in the "Final ability scores"
    # section above — appended here, unconditionally, mirroring exactly how
    # background_ability_choice_tpl/species_ability_choice_tpl (also built
    # early) get appended to choice_templates at their own call sites,
    # rather than rebuilding the templates a second time here.
    choice_templates += feat_ability_choice_tpls
    for species_tpl in species_feat_templates:
        choice_templates.append(species_tpl)
    for species_feat in species_feats:
        origin = species_feat["_species_origin"]
        choice_templates += _feat_choice_templates([species_feat], origin=origin)
        choice_templates += _feat_spell_choice_templates(
            [species_feat], catalog, origin=origin, raw_selections=species_choices_raw, total_level=total_level,
        )
    choice_templates += species_feat_ability_tpls
    if race and race_id:
        species_variant_tpl = _species_variant_template(race, race_id)
        if species_variant_tpl:
            choice_templates.append(species_variant_tpl)
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)
        if species_ability_choice_tpl:
            choice_templates.append(species_ability_choice_tpl)
    equipment_dependents: dict[str, dict[str, list[dict]]] = {}
    if cls and cls_id:
        cls_equipment_templates, cls_dropped, cls_dependents = _equipment_choice_templates(
            cls, "class", cls_id, cls["name"], catalog.items)
        equipment_dependents.update(cls_dependents)
        choice_templates += cls_equipment_templates
        if cls_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-class-{cls_id}",
                "message": f"{cls['name']}'s starting equipment has {cls_dropped} choice(s) that can't be shown yet and were left out.",
            })
    if bg and bg_id:
        bg_equipment_templates, bg_dropped, bg_dependents = _equipment_choice_templates(
            bg, "background", bg_id, bg["name"], catalog.items)
        equipment_dependents.update(bg_dependents)
        choice_templates += bg_equipment_templates
        if bg_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-background-{bg_id}",
                "message": f"{bg['name']}'s starting equipment has {bg_dropped} choice(s) that can't be shown yet and were left out.",
            })

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)
    _apply_species_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], race, subrace, catalog)

    # Apply the draft's own selections onto each template to get a real Choice.
    equipment_raw = draft.get("equipment")
    equipment_dict = equipment_raw if isinstance(equipment_raw, dict) else {}
    equipment_choices_raw = equipment_raw.get("choices") if isinstance(equipment_raw, dict) else None
    if equipment_choices_raw is not None and not isinstance(equipment_choices_raw, dict):
        problems.append({"id": "malformed-equipment-choices", "message": "'equipment.choices' must be an object."})
        equipment_choices_raw = None

    details = _sanitized_details(draft.get("details"))

    all_selections: dict[str, list[str]] = {}
    # Every class's own choice ids are scoped by cls_id (e.g.
    # "class:fighter:..." vs "class:wizard:...") and never collide across
    # two different classes' choice sets, so merging every resolved
    # class's submitted choices here (not just the primary/classes[0]'s)
    # is safe — and necessary, since the generic choice-resolution loop
    # below reads selections only from this dict.
    for rc in resolved_classes:
        all_selections.update(rc["class_choices"])
    all_selections.update(background_dict.get("choices") or {})
    all_selections.update(species.get("choices") or {})
    all_selections.update(equipment_choices_raw or {})

    # A selection stored in the Draft for a choice id that no longer
    # exists among the CURRENTLY reachable choice_templates (because the
    # player leveled down or cleared a subclass selection) is stale — it
    # was never deleted from the Draft (the architecture deliberately
    # never mutates the Draft — see Phase 3a design spec §7), so it just
    # silently stopped being read. This is the first time anything
    # surfaces that to the player instead of leaving it invisible.
    # (SET_SPECIES/SET_SUBSPECIES/SET_BACKGROUND/SET_CLASS all reset
    # `choices: {}` in the frontend reducer, so a species/background/
    # primary-class change can never itself leave a stale selection
    # behind — those paths never reach here.)
    # Nested starting-equipment picks (e.g. the martial weapon in "a martial
    # weapon and a shield") only exist once their parent option is selected.
    if equipment_dependents:
        expanded_templates = []
        for tpl in choice_templates:
            expanded_templates.append(tpl)
            option_deps = equipment_dependents.get(tpl["id"])
            if option_deps:
                parent_valid = {o["id"] for o in tpl["options"]}
                raw_parent = all_selections.get(tpl["id"])
                raw_parent = raw_parent if isinstance(raw_parent, list) else []
                parent_selected = [s for s in dict.fromkeys(raw_parent) if isinstance(s, str) and s in parent_valid]
                for option_id in parent_selected[: tpl["count"]]:
                    expanded_templates.extend(option_deps.get(option_id, []))
        choice_templates = expanded_templates
    current_template_ids = {tpl["id"] for tpl in choice_templates}
    pruned = [
        {"choiceId": choice_id, "reason": f"'{choice_id}' no longer applies to the current character and was ignored."}
        for choice_id, selected in all_selections.items()
        if selected and choice_id not in current_template_ids
    ]

    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        # Dedupe (preserving first-occurrence order) so this generic pass
        # agrees with the early species-ability-bonus pass above, which
        # dedupes the same underlying selection before applying bonuses.
        raw_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected = [s for s in raw_selected if s in valid_ids]
        if _is_count_variable_choice(tpl):
            # A spellcaster's allowed count shrinks on level-down (or when
            # the casting modifier drops) while the choice id stays the
            # same, and spells above the class's highest slot level stop
            # being offered — both leave stale selections in the Draft.
            # Report them as non-blocking `pruned` entries (keep the first
            # `count` valid selections), not an over-selected problem.
            selected = selected[: tpl["count"]]
            dropped = [s for s in raw_selected if s not in selected]
            if dropped:
                names = ", ".join(catalog.spells[d]["name"] if d in catalog.spells else d for d in dropped)
                pruned.append({
                    "choiceId": tpl["id"],
                    "reason": (
                        f"'{tpl['id']}' now allows {tpl['count']} selection(s); "
                        f"{len(dropped)} stored selection(s) no longer fit and were ignored: {names}."
                    ),
                })
        elif len(selected) > tpl["count"]:
            problems.append({
                "id": f"over-selected-{tpl['id']}",
                "message": f"'{tpl['label']}' allows {tpl['count']} selection(s) but {len(selected)} were submitted.",
            })
            selected = selected[: tpl["count"]]
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})

    added_raw = equipment_dict.get("added")
    if added_raw is None:
        added_raw = []
    elif not isinstance(added_raw, list):
        problems.append({"id": "malformed-equipment-added", "message": "'equipment.added' must be a list."})
        added_raw = []

    added_resolved = []
    for entry in added_raw:
        if not isinstance(entry, dict):
            continue
        item_id = entry.get("itemId")
        item = catalog.items.get(item_id) if isinstance(item_id, str) else None
        if not item:
            continue
        added_resolved.append({
            "itemId": item_id, "name": item["name"],
            "qty": entry.get("qty", 1), "equipped": bool(entry.get("equipped", False)),
        })

    equipment_choices = [c for c in choices if c["source"]["kind"] == "equipment"]
    equipped_items = _gather_equipped_items(equipment_choices, added_raw if isinstance(added_raw, list) else [], catalog.items)
    chosen_equipment = _chosen_equipment(equipment_choices, catalog.items)

    # starting_gold is SRD's own fixed per-background field, shape
    # {"quantity": N, "unit": "gp"} (confirmed against the bundled SRD
    # Backgrounds file) — present on every SRD/official background but,
    # until now, never read anywhere. A selected gp-{amount} bundle member
    # (see _selected_gold_and_narrative_items) adds on top of it rather
    # than replacing it, since a background can offer BOTH (e.g. SRD's own
    # Acolyte grants a fixed 15 gp with no equipment-choice gold at all,
    # while an official background's own bundle may carry gold only in the
    # selectable option, with its fixed field left None).
    fixed_gold = (bg.get("starting_gold") or {}).get("quantity", 0) if bg else 0
    selected_gold, narrative_items = _selected_gold_and_narrative_items(equipment_choices)
    starting_gold = fixed_gold + selected_gold

    # bg["starting_narrative_items"] (Finding 1 of the final whole-branch
    # review, official_source.py's _fixed_starting_equipment_from_5etools)
    # carries the FIXED "_"-keyed list's own flavor/category/no-catalog-
    # match members (e.g. Acolyte/PHB's holy symbol, incense, vestments) —
    # previously narrative_items only ever came from a SELECTED
    # equipment-choice bundle member. Fixed items are prepended so they
    # read as "always granted" ahead of whatever the player separately
    # chose.
    narrative_items = list(bg.get("starting_narrative_items", [])) + narrative_items if bg else narrative_items

    def _spell_summaries(choice: dict | None) -> list[dict]:
        if not choice:
            return []
        return [
            {"id": sid, "name": catalog.spells[sid]["name"], "level": catalog.spells[sid]["level"]}
            for sid in choice["selected"] if sid in catalog.spells
        ]

    # sheet["spells"] aggregates across EVERY resolved class with
    # spellcasting, not just the primary one — a secondary caster's
    # selections previously never reached the sheet (or any export) because
    # only the primary's cls_id was ever looked up. One entry per class that
    # actually has a cantrip and/or known-spell Choice this level; a
    # non-caster (or a caster below its first spell-granting level)
    # contributes no entry at all, so this stays [] rather than padding out
    # with empty per-class placeholders.
    spells_summary: list[dict] = []
    for rc in resolved_classes:
        rc_cls, rc_cls_id = rc["cls"], rc["cls_id"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_cantrip_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-cantrips"), None)
        rc_known_spells_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-known"), None)
        feature_ids = {idx for cid_, lvl_, idx in _class_feature_list(catalog, [rc], choices)}
        always_ids = _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc["level"], feature_ids, "always")
        if not (rc_cantrip_choice or rc_known_spells_choice or always_ids):
            continue
        rc_spell_ability = spells_mod.spellcasting_ability(rc_cls)
        rc_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        rc_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        spells_summary.append({
            "classId": rc_cls_id,
            "cantrips": _spell_summaries(rc_cantrip_choice),
            "known": _spell_summaries(rc_known_spells_choice),
            # Subclass spells (Life domain, oath spells, ...): always
            # prepared, outside the known/prepared limits.
            "alwaysPrepared": [
                {"id": sid, "name": catalog.spells[sid]["name"], "level": catalog.spells[sid]["level"]} for sid in always_ids
            ],
            "spellSaveDC": rc_save_dc,
            "spellAttackBonus": rc_attack_bonus,
        })

    # Spell-slot pools: see spells.spell_slots_for for the single-class vs
    # combined multiclass rule and the separate Warlock Pact Magic pool.
    spell_slots, warlock_slots = spells_mod.spell_slots_for(
        catalog, [(rc["cls_id"], rc["level"]) for rc in resolved_classes if rc["cls"]],
    )

    granted_equipment = []
    if cls:
        granted_equipment += _fixed_equipment(cls.get("starting_equipment", []), catalog.items)
    if bg:
        granted_equipment += _fixed_equipment(bg.get("starting_equipment", []), catalog.items)

    for granted in granted_equipment:
        granted_item = catalog.items.get(granted["itemId"])
        if granted_item:
            equipped_items.append(granted_item)

    # Derived stats.
    proficient_skills: set[str] = set()
    for c in choices:
        # "background" added here (Phase 4b Task 2): a background's own
        # skill-proficiency CHOICE (as opposed to its fixed
        # starting_proficiencies, read separately just below) previously had
        # no path into proficient_skills at all — the exact same "new
        # choice-producing feature needs an equally-new consumer path" gap
        # Phase 4a Task 4b already found and fixed for species. Safe to add
        # unconditionally: the only OTHER background-kind choice is the
        # language choice, whose selected values are language ids, never
        # "skill-"-prefixed, so this filter still excludes them.
        # Expertise picks are not proficiency grants (they must already be
        # proficient), so they never feed this set.
        if c["source"]["kind"] in ("class", "species", "background", "feat") and "expertise-choice" not in c["id"]:
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            proficient_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
    # Phase 4c-i Task 6: a granted feat's own FIXED skill-proficiency grant
    # (e.g. a hypothetical background-granted Skilled/Prodigy-style feat)
    # feeds this SAME set, mirroring the bg/race passes just above — see
    # _feat_proficiency_ids' own docstring for why only fixed grants (not
    # a feat's own proficiency_choices) are read.
    feat_proficiency_ids = _feat_proficiency_ids(resolved_feats)
    proficient_skills.update(p for p in feat_proficiency_ids if p.startswith("skill-"))

    proficient_armor: set[str] = set()
    proficient_weapons: set[str] = set()
    proficient_tools: set[str] = set()

    # The brief's original heuristic only carved out "shortswords" as the
    # one non-generic weapon-category id, reasoning from a check against
    # Fighter+Rogue's proficiencies alone. A full empirical scan of every
    # SRD class's top-level `proficiencies` (not just the two classes this
    # task's tests exercise) turns up 14 more specific-weapon proficiency
    # ids that don't contain the substring "weapon" — without this set
    # they'd be wrongly bucketed into `tools` for any class whose primary
    # (level-1) proficiency grant names an individual weapon rather than a
    # broad category (e.g. Bard's rapiers/longswords/shortswords/
    # hand-crossbows, Wizard's daggers/darts/slings/quarterstaffs/
    # crossbows-light). Verified against 5e-SRD-Classes.json directly.
    # Task 3b addendum: this set was originally built from an empirical scan
    # of SRD *classes* only (see comment above). Once race/subrace traits
    # also started feeding `_categorize_proficiency` (below), a second scan
    # of every SRD trait's `proficiencies` (5e-SRD-Traits.json) turned up
    # more specific-weapon ids the class-only scan never exercised: Dwarven
    # Combat Training's battleaxes/handaxes/light-hammers/warhammers, and
    # Elf Weapon Training's shortbows/longbows. Without these, real bundled
    # SRD trait grants would be silently miscategorized into `tools`.
    _SPECIFIC_WEAPON_PROFICIENCY_IDS = SPECIFIC_WEAPON_PROFICIENCY_IDS

    def _categorize_proficiency(prof_id: str) -> None:
        if prof_id.startswith("skill-") or prof_id.startswith("saving-throw-"):
            return  # skills handled by proficient_skills elsewhere; saving
            # throws by proficient_save_abilities — a class's top-level
            # `proficiencies` field mixes saving-throw-* entries in with its
            # armor/weapon grants (confirmed for every SRD class), so this
            # guard is needed or they'd fall through to the tools bucket.
        if "armor" in prof_id or prof_id == "shields":
            proficient_armor.add(prof_id)
        elif "weapon" in prof_id or prof_id in _SPECIFIC_WEAPON_PROFICIENCY_IDS:
            proficient_weapons.add(prof_id)
        else:
            proficient_tools.add(prof_id)

    # PRE-EXISTING gap (predates this plan, affects bundled SRD data
    # unconditionally, not just sourcebook races): the skill-scanning pass
    # above reads `trait_refs` but only forwards skill- prefixed ids into
    # `proficient_skills` — any tool/weapon/armor grant on a race/subrace
    # trait (e.g. SRD Dwarf's "Dwarven Combat Training", which grants
    # battleaxe/handaxe/light-hammer/warhammer proficiency) never reached
    # sheet.proficiencies. This second pass recomputes the identical
    # `trait_refs` (a small, disclosed duplication, matching this file's
    # existing tolerance for it elsewhere, e.g. `_class_label()`) and
    # categorizes every non-skill entry via the same `_categorize_proficiency`
    # used for class-level grants below.
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            for p in trait.get("proficiencies", []):
                if not p["index"].startswith("skill-"):
                    _categorize_proficiency(p["index"])

    # PRE-EXISTING gap (predates this plan, genuinely separate from the
    # race/subrace trait-scanning gap fixed just above): the skill-scanning
    # pass near the top of this function reads `bg.get("starting_proficiencies",
    # [])` but only forwards skill- prefixed ids into `proficient_skills` — any
    # tool/weapon/armor grant on a background (e.g. sourcebook Acolyte's
    # Calligrapher's Supplies) never reached sheet.proficiencies. This second
    # pass recategorizes every non-skill entry via the same
    # `_categorize_proficiency` used for race traits and class-level grants.
    if bg:
        for p in bg.get("starting_proficiencies", []):
            if not p["index"].startswith("skill-"):
                _categorize_proficiency(p["index"])

    # Phase 4c-i Task 6: a granted feat's own FIXED non-skill proficiency
    # grant (e.g. Tavern Brawler/XPHB's improvised-weapon proficiency)
    # feeds the SAME `_categorize_proficiency` used for race/background
    # grants just above — `feat_proficiency_ids` was already computed
    # once, earlier, for the proficient_skills pass, reused here rather
    # than recomputed.
    for p_id in feat_proficiency_ids:
        if not p_id.startswith("skill-"):
            _categorize_proficiency(p_id)

    # Gating on `c["source"]["kind"] == "class"` alone is too broad — it also
    # covers feature subfeature choices, ASI choices, and spell choices
    # (cantrips/known spells), none of which are proficiency choices. A
    # selected spell like `mage-armor` would otherwise be fed into
    # `_categorize_proficiency`, whose substring check ("armor" in prof_id)
    # miscategorizes it into `armor` right next to real armor proficiencies.
    # The two real proficiency-choice id shapes are
    # `class:{cls_id}:1:prof-choice-{i}` (primary class's level-1 choice)
    # and `class:{cls_id}:multiclass-prof-choice-{i}` (this class's
    # multiclass-only choice) — both, and only those, contain the substring
    # "prof-choice-" (verified character-by-character: the primary id's
    # "...:1:prof-choice-0" contains ":prof-choice-", but the multiclass
    # id's "...:multiclass-prof-choice-0" does NOT — the character before
    # "prof-choice-" there is "-", not ":" — so a leading-colon substring
    # check would miss the multiclass pattern; "prof-choice-" without the
    # colon is what actually matches both, confirmed against every cid
    # pattern generated in this file).
    for c in choices:
        if c["source"]["kind"] == "class" and "prof-choice-" in c["id"]:
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "species" and "proficiency-choice" in c["id"]:
            # Narrowed to the "proficiency-choice" id substring (set by
            # _species_choice_templates above) so a species-sourced
            # subtrait_options selection (e.g. Dragonborn's Draconic
            # Ancestry damage-type/ancestry pick) or bonus-language
            # selection never reaches _categorize_proficiency, which has no
            # "is this even a real proficiency id" guard and would silently
            # miscategorize a string like "fire" or a language id into the
            # tools bucket.
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "background" and "proficiency-choice" in c["id"]:
            # Phase 4b Task 2's background equivalent of the species branch
            # right above — same reasoning, same "proficiency-choice"
            # substring convention (set by _background_choice_templates),
            # narrowed the same way so the background's OTHER kind=
            # "background" choice (its language choice, selected values are
            # language ids) never reaches _categorize_proficiency. Without
            # this branch, a selected TOOL from a background's tool
            # proficiency choice (e.g. Archaeologist/ToA's Navigator's
            # Tools-or-Cartographer's Tools pick) would resolve as a valid
            # Choice selection yet never reach sheet.proficiencies.tools —
            # confirmed by tracing it end to end while writing this task,
            # not assumed from the Choice template existing (a selected
            # SKILL from the same mechanism already reaches the sheet via
            # the "background" addition to proficient_skills above, so only
            # the non-skill/tool half of this wiring was actually missing).
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)
        elif c["source"]["kind"] == "feat" and "proficiency-choice" in c["id"]:
            # Phase 4c-ii Task 1's feat equivalent of the species/background
            # branches above — same reasoning, same "proficiency-choice"
            # substring convention (set by _feat_choice_templates), e.g.
            # Crafter/XPHB's selected tool(s) (Artisan/XPHB's feat grant)
            # reaching sheet.proficiencies.tools.
            for s in c["selected"]:
                if not s.startswith("skill-"):
                    _categorize_proficiency(s)

    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        for prof_id in SUBCLASS_PROFICIENCIES.get(rc["subclass_id"], []):
            _categorize_proficiency(prof_id)
        if rc["index"] == 0:
            for p in rc["cls"].get("proficiencies", []):
                _categorize_proficiency(p["index"])
        else:
            for p in rc["cls"].get("multi_classing", {}).get("proficiencies", []):
                _categorize_proficiency(p["index"])

    # Expertise needs the full proficiency picture (skills, plus the Rogue's
    # thieves' tools), so it is gated only after every grant above is in.
    pruned += _gate_expertise_choices(choices, proficient_skills | proficient_tools)
    pruned += _gate_invocation_choices(choices, resolved_classes, catalog)

    # Phase 4c-i Task 6: was class-only (primary class's saving_throws
    # field) — a granted feat's own FIXED saving-throw-proficiency grant
    # (see _feat_saving_throw_proficiencies' own docstring for why real
    # data contributes nothing here today) now extends this SAME list,
    # deduped so a feat naming an ability the class already covers
    # doesn't produce a duplicate entry in derived.savingThrows/
    # sheet.proficiencies.savingThrows.
    proficient_save_abilities = [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])]
    for ab in _feat_saving_throw_proficiencies(resolved_feats) + [
        a.upper() for a in _feat_selected_choice_values(choices, ":save-choice-")
    ]:
        if ab not in proficient_save_abilities:
            proficient_save_abilities.append(ab)

    hp_type = (draft.get("preferences") or {}).get("hitPointType")
    if hp_type not in ("fixed", "manual"):
        hp_type = "fixed"
    hp_class_entries = []
    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        rc_hit_die = rc["cls"].get("hit_die")
        if rc_hit_die is None:
            continue
        rc_hp_rolls_raw = classes[rc["index"]].get("hpRolls") if rc["index"] < len(classes) else None
        rc_hp_rolls = {k: v for k, v in rc_hp_rolls_raw.items() if isinstance(v, int)} if isinstance(rc_hp_rolls_raw, dict) else {}
        hp_class_entries.append({"hit_die": rc_hit_die, "level": rc["level"], "hp_rolls": rc_hp_rolls})
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    effects = features_mod.active_effects(_class_feature_list(catalog, resolved_classes, choices))
    class_levels = {rc["cls_id"]: rc["level"] for rc in resolved_classes if rc["cls"]}
    jack, remarkable = features_mod.half_proficiency(effects)
    expertise_all = list(dict.fromkeys(_feat_expertise_skills(resolved_feats) + _expertise_selected_values(choices)))
    skills = derived_mod.skill_scores(
        modifiers, list(proficient_skills), prof_bonus, expertise_all, jack, remarkable,
    )
    speeds = _species_speeds(race, subrace, species_variant)
    worn_armor = any(i.get("equipment_category", {}).get("index") == "armor" for i in equipped_items)  # body armor or shield
    if speeds and not worn_armor:
        speed_bonus = features_mod.speed_bonus(effects, class_levels)
        speeds = {mode: value + speed_bonus for mode, value in speeds.items()}
    base_speed = speeds.get("walk")
    # Attacks, carrying capacity and armor warnings (Slice 9). Size is the
    # species' size (Slice 8d's size choice will override it); no species = Medium.
    weapon_proficiencies = proficient_armor | proficient_weapons
    attacks = attacks_mod.attacks_from_gear(
        equipped_items, modifiers, prof_bonus, proficient_weapons, features_mod.attack_styles(effects),
    )
    armor_problems, stealth_disadvantage = equipment_mod.armor_warnings(equipped_items, final_scores, weapon_proficiencies)
    warnings += armor_problems
    carrying = derived_mod.carrying_summary(
        final_scores.get("STR", 10), (race or {}).get("size") or "Medium",
        granted_equipment + chosen_equipment + added_resolved, catalog.items,
    )
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_multiclass(hp_class_entries, modifiers["CON"], hp_type)
        + features_mod.hp_bonus(effects, class_levels)
        + sum(e.get("hp_per_level", 0) for e in _srd_trait_effects(race, subrace)) * sum(class_levels.values()),
        "hitDice": " + ".join(f"{rc['level']}d{rc['cls']['hit_die']}" for rc in resolved_classes if rc["cls"] and rc["cls"].get("hit_die")) or None,
        "armorClass": equipment_mod.armor_class_from_gear(
            equipped_items, modifiers["DEX"], features_mod.ac_formulas(effects), modifiers,
            features_mod.armored_ac_bonus(effects),
        ),
        "speed": base_speed,  # walking speed; `speeds` carries every mode
        "speeds": speeds,
        "initiative": derived_mod.initiative(modifiers, prof_bonus, jack, remarkable),
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills),
        "passiveInsight": derived_mod.passive_skill(skills, "skill-insight"),
        "passiveInvestigation": derived_mod.passive_skill(skills, "skill-investigation"),
        "spellSlots": spell_slots,
        "warlockSpellSlots": warlock_slots,
        "attacks": attacks,
        "carryingCapacity": carrying,
        "stealthDisadvantage": stealth_disadvantage,
    }

    fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + \
        [lang["index"] for lang in (race.get("languages", []) if race else [])] + \
        _feat_languages(resolved_feats)  # Phase 4c-i Task 6 — see that function's own docstring
    chosen_languages = [
        s for c in choices
        if c["source"]["kind"] in ("background", "species", "feat") and c["id"].endswith(":languages")
        for s in c["selected"]
    ]

    # granted_feats/feat_options/resolved_feats are now computed much
    # earlier (Phase 4c-i Task 6 hoist — right after `bg` itself is
    # resolved, see that call site's own comment) so this task's
    # ability-bonus/proficiency/language/expertise/saving-throw merges
    # could feed the SAME early passes species/background/race already
    # feed. damage_modifiers/condition_immunities/senses (Task 5) still
    # read `resolved_feats` here, unchanged — only WHERE it's computed
    # moved, not what these three lines do.
    chosen_resistances = [
        v for c in choices
        if c["source"]["kind"] == "species" and c["id"].endswith(":resistance")
        for v in c["selected"]
    ]
    # SRD trait effects (Dwarven Resilience, Hellish Resistance) and the
    # damage type of a selected Draconic Ancestry subtrait.
    chosen_resistances += (species_variant or {}).get("resist") or []
    for effect in _srd_trait_effects(race, subrace):
        chosen_resistances += effect.get("resist", [])
    for c in choices:
        if c["source"]["kind"] != "species" or ":trait:" not in c["id"]:
            continue
        for sel in c["selected"]:
            damage = ((catalog.traits.get(sel) or {}).get("trait_specific") or {}).get("damage_type")
            if damage:
                chosen_resistances.append(damage["index"])
    damage_modifiers = _species_damage_modifiers(race, subrace, resolved_feats, chosen_resistances)
    condition_immunities = _species_condition_immunities(race, subrace, resolved_feats)
    senses = _species_senses(race, subrace, catalog, species_variant)
    for sense_kind, sense_range in _feat_senses(resolved_feats).items():
        if sense_range > senses.get(sense_kind, 0):
            senses[sense_kind] = sense_range
    innate_spells = (_species_innate_spells(race, subrace, catalog, species_variant)
                     + _species_trait_spell_choices(race, subrace, catalog, choices)
                     + _feat_innate_spells(resolved_feats, catalog, choices))

    refs_by_class = {
        rc["cls_id"]: _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"])
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    sheet_feats = sheet_features_mod.feats_summary(resolved_feats, choices)

    sheet = {
        "name": draft.get("name") or "",
        "level": total_level if resolved_classes else 0,
        "classes": [
            {
                "id": rc["cls_id"], "name": rc["cls"]["name"], "level": rc["level"],
                "subclass": {"id": rc["subclass_id"], "name": rc["subclass"]["name"]} if rc["subclass_id"] and rc["subclass"] else None,
            }
            for rc in resolved_classes if rc["cls"]
        ],
        "background": {"id": bg_id, "name": bg["name"]} if bg else None,
        "species": {
            "id": race_id, "name": race["name"],
            "subspecies": {"id": subrace_id, "name": subrace["name"]} if subrace else None,
            "variant": {"id": species_variant["id"], "name": species_variant["name"]} if species_variant else None,
        } if race else None,
        "abilities": final_scores,
        "proficiencies": {
            "skills": sorted(proficient_skills),
            "savingThrows": proficient_save_abilities,
            "languages": sorted(set(fixed_languages + chosen_languages)),
            "armor": sorted(proficient_armor),
            "weapons": sorted(proficient_weapons),
            "tools": sorted(proficient_tools),
        },
        "startingGold": starting_gold,
        "equipment": {
            "granted": granted_equipment, "chosen": chosen_equipment, "added": added_resolved,
            "narrativeItems": narrative_items,
        },
        "spells": spells_summary,
        "details": details,
        "damageModifiers": damage_modifiers,
        "conditionImmunities": condition_immunities,
        "innateSpells": innate_spells,
        # Background grants keep their bare-slug ids (unchanged); a feat
        # taken at an ASI level is appended by its full catalog index
        # (e.g. "actor-xphb") — the exact id it was selected by.
        "grantedFeats": granted_feats + [f["index"] for f in species_feats] + [f["index"] for f in asi_selected_feats],
        "featOptions": feat_options,
        "senses": senses,
        "expertiseSkills": expertise_all,
        "features": sheet_features_mod.build_features(
            catalog, resolved_classes, refs_by_class, race, race_id, subrace, bg, bg_id, resolved_feats, choices,
        ),
        "feats": sheet_feats,
    }

    return {
        "sheet": sheet,
        "choices": choices,
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": pruned,
    }
