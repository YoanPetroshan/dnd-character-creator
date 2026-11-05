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

import re
from functools import lru_cache
from dataclasses import dataclass, field

from catalog import feat_effects_data, reference_data
from catalog.choices import build_choice_template, build_equipment_choice, pack_quantities, pack_units
from catalog.loader import Catalog
from i18n.messages import msg
from catalog.official_source import slug, SAVE_ABILITY_NAMES
from catalog.reference_data import (
    ABILITIES, HEAVY_ARMOR_SPEED_EXEMPT_RACES, HEAVY_ARMOR_SPEED_EXEMPT_TRAITS, SPECIFIC_WEAPON_PROFICIENCY_IDS, SRD_TRAIT_EFFECTS, SUBCLASS_PROFICIENCIES, SUBCLASS_EXTRA_FEATURES,
    SUBCLASS_SPELLCASTING_ABILITY, SUBCLASS_SPELL_SCHOOL_LIMITS, wizard_spell_picks, ruleset_allows, subclass_unlock_level,
)
from . import asi as asi_mod
from . import attacks as attacks_mod
from . import class_choices_2024
from . import subclass_options_2024
from . import option_source as option_source_mod
from . import innate_uses, subclass_innate_2024
from . import subclass_spells_2024
from . import class_resources as class_resources_mod
from . import species_resources as species_resources_mod
from . import derived as derived_mod
from . import equipment as equipment_mod
from . import worn as worn_mod
from . import feat_effects as feat_effects_mod
from . import feat_spell_tables
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
            out.append({"id": "point-buy-out-of-range", "message": msg("point-buy-out-of-range")})
        else:
            spent = sum(_POINT_BUY_COST[v] for v in scores)
            if spent > 27:
                out.append({"id": "point-buy-over-budget", "message": msg("point-buy-over-budget", spent=spent)})
    elif method == "standard":
        if scores != [10] * 6 and sorted(scores, reverse=True) != _STANDARD_ARRAY:
            out.append({"id": "standard-array-mismatch", "message": msg("standard-array-mismatch")})
    elif method == "roll":
        if any(not 3 <= v <= 18 for v in scores):
            out.append({"id": "roll-out-of-range", "message": msg("roll-out-of-range")})
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


RULESETS = ("2014", "2024", "mixed")


def _asi_policy(ruleset: str, race: dict | None, subrace: dict | None, bg: dict | None) -> tuple[bool, bool, list[dict]]:
    """Which ability-score-increase sources apply under a ruleset:
    (species_on, background_on, warnings). Every conflict is a WARNING, never
    a problem - a house-rule mix must still export. "Species ASI" means ALL of
    it: fixed bonuses and choice templates on the species and subspecies
    (Half-Elf, VRGR lineages, Variant Human, subrace options)."""
    species_has = bool(_species_ability_bonuses(race, subrace)) or any(
        src.get("ability_bonus_options") for src in _ability_sources(race, subrace)
    )
    bg_has = bool(bg and bg.get("ability_bonus_options"))
    warnings: list[dict] = []
    if ruleset == "2014":
        if bg_has:
            warnings.append({
                "id": "ruleset-2014-background-asi-ignored",
                "message": msg("ruleset-2014-background-asi-ignored", name=bg["name"]),
            })
        return True, False, warnings
    if ruleset == "2024":
        if species_has:
            warnings.append({
                "id": "ruleset-2024-species-asi-ignored",
                "message": msg("ruleset-2024-species-asi-ignored"),
            })
        if bg:
            if not bg_has:
                warnings.append({
                    "id": "ruleset-2024-background-no-asi",
                    "message": msg("ruleset-2024-background-no-asi", name=bg["name"]),
                })
            if not (bg.get("feats") or bg.get("feat_options") or bg.get("feat_grants")):
                warnings.append({
                    "id": "ruleset-2024-background-no-origin-feat",
                    "message": msg("ruleset-2024-background-no-origin-feat", name=bg["name"]),
                })
        return False, True, warnings
    if bg_has and species_has:
        warnings.append({
            "id": "asi-double-dip-prevented",
            "message": msg("asi-double-dip-prevented"),
        })
        return False, True, warnings
    return True, True, warnings


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


def _feat_name_key(feat: dict) -> str:
    """Edition-independent identity of a feat (S2, decision D4): the
    lowercased name with a trailing " (...)" stripped, so Alert (PHB) and
    Alert (XPHB) share the key "alert"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", feat.get("name") or "").strip().lower()


def _taken_add(taken: dict, feats) -> dict:
    """Records feats as held in a `taken` map: `{catalog index: ""}` and
    `{"name:<name key>": "<Name>, <SOURCE>"}` (the label feeds the
    cross-edition disabled reason). First holder wins the label."""
    for f in feats:
        taken.setdefault(f["index"], "")
        taken.setdefault("name:" + _feat_name_key(f), f"{f.get('name')}, {f.get('source')}")
    return taken


def _taken_reason(feat: dict, taken) -> str | None:
    """None when `feat` may still be picked; otherwise the disabled reason.
    A `repeatable` feat is always allowed. The same catalog feat reads
    plain "already taken"; a same-name feat of another edition reads
    "already taken (Alert, XPHB)"."""
    if feat.get("repeatable") or not taken:
        return None
    if feat["index"] in taken:
        return msg("disabled-already-taken")
    label = taken.get("name:" + _feat_name_key(feat))
    return msg("disabled-already-taken-from", where=label) if label is not None else None


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


def _feat_build_position(feat: dict, class_order) -> tuple[int, int] | None:
    """F3a-5: where a granted feat sits in the build: (class position, class level) for ASI feats (their ASI level)
    and Lessons of the First Ones feats (Warlock 2); None for origin feats (background / species)."""
    order = list(class_order)
    if feat.get("_asi_cid"):
        return class_choices_2024.card_position({"id": feat["_asi_cid"], "source": {"kind": "class"}}, order)
    if feat.get("_inv_cid"):
        holder = feat.get("_inv_class") or "warlock"  # RP20: a Lessons pick held through Eldritch Adept sits at that ASI
        return (order.index(holder) if holder in order else len(order), feat.get("_asi_level") or 2)
    return None


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
            if src is race and "additionalSpells" in (variant or {}).get("removes", []):
                continue  # e.g. Kobold's Craftiness / Defiance legacies
            innate.append(_innate_entry_to_sheet(entry, catalog))
    for entry in (variant or {}).get("innate_spells", []):
        innate.append(_innate_entry_to_sheet(entry, catalog))
    for effect in _srd_trait_effects(race, subrace):
        for entry in effect.get("innate_spells", []):
            innate.append(_innate_entry_to_sheet(entry, catalog))
    # G6: the race and its subrace may both list the same at-will cantrip (Tiefling and its MTF subraces: Thaumaturgy); an
    # identical entry adds nothing, so only the first is kept.
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


def _innate_entry_to_sheet(entry: dict, catalog: Catalog) -> dict:
    """One catalog innate-spell entry -> sheet shape, resolving spell_id
    against catalog.spells (spellId None + fallback name when absent)."""
    spell_id = catalog.resolve_spell_id(entry["spell_id"])
    spell = catalog.spells.get(spell_id)
    return {
        "spellId": spell_id if spell else None,
        "name": spell["name"] if spell else entry["name"],
        "level": entry["level"],
        "uses": entry["uses"],
        "ability": entry["ability"],
        "variant": entry["variant"],
    }


def _feat_cid_prefix(feat: dict) -> str:
    """Same cid prefix _feat_choice_templates scopes a feat's choices under."""
    return feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"


def _followed_variants(feats: list[dict], raw_choices: dict) -> dict[str, str | None]:
    """G5: {dependent feat index: variant slug} for the held feats that FOLLOW another held feat's spell list. A feat whose
    effect entry has ``ability_from`` (RP5) and that has `spell_variants` of its own (Magic Connoisseur: "Choose a level 1
    and a level 2 spell from the same list you selected for the Magic Initiate feat's cantrips") takes the list the base
    feat picked; it then has no `:spell-variant` card of its own. The value is None while the base feat's list is not
    picked yet (the dependent offers no spell cards until it is) or when the picked list is not one of the dependent's.
    `raw_choices` is the union of the draft's raw selections (every cid is unique across classes / background / species).
    Only the base's variant card is read; a base feat that is not held leaves the dependent with its own card."""
    out: dict[str, str | None] = {}
    for feat in feats:
        base = feat_effects_mod.ability_from(feat_effects_data.FEAT_EFFECTS.get(feat.get("index")))
        if not base or not feat.get("spell_variants") or feat["index"] in out:
            continue
        holders = [f for f in feats if f["index"] == base and f.get("spell_variants")]
        if not holders:
            continue
        own = {slug(v) for v in feat["spell_variants"]}
        picked = None
        for holder in holders:
            valid = [slug(v) for v in holder["spell_variants"]]
            raw = raw_choices.get(f"{_feat_cid_prefix(holder)}:spell-variant")
            picked = next((slug(x) for x in raw if isinstance(x, str) and slug(x) in valid), None) if isinstance(raw, list) else None
            if picked:
                break
        out[feat["index"]] = picked if picked in own else None
    return out


def _feat_spell_ability(feat: dict, ability, choices: list[dict], feats=(), _follow: bool = True):
    """Resolves a feat's spellcasting ability for the sheet.
    - "inherit": the ability the feat increased (its :ability-bonus choice):
      the picked ability, the candidate list while pending, or None if the
      feat has no such choice.
    - {"choose": [...]}: the ability picked in its `{prefix}:spell-ability`
      choice, else the dict unchanged (pending).
    - {"sameAsFeat": ref}: the ability of the OTHER held feat `ref` (e.g.
      Magic Connoisseur follows Magic Initiate); None if that feat isn't held.
    Anything else (a fixed "CHA", None) passes through.
    RP5: a feat whose effect entry has ``ability_from`` (Adept of the Robes, Outlands Envoy, Warlike Familiar, Magic
    Connoisseur) takes the ability chosen for that base feat while the base feat is held."""
    base = feat_effects_mod.ability_from(feat_effects_data.FEAT_EFFECTS.get(feat.get("index")))
    if base and _follow:
        other = next((f for f in feats if f["index"] == base), None)
        first = next((e["ability"] for e in ((other or {}).get("innate_spells") or []) + ((other or {}).get("spell_choices") or [])
                      if e.get("ability") is not None), None)
        if other is not None and first is not None:
            return _feat_spell_ability(other, first, choices, feats, _follow=False)
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


def _feat_innate_spells(feats: list[dict], catalog: Catalog, choices: list[dict], patches: dict | None = None,
                        follow_variants: dict | None = None) -> list[dict]:
    """Sheet innate-spell entries granted by feats (fixed names), each
    tagged with its featId. Not filtered by character level, matching
    the race behaviour."""
    out: list[dict] = []
    by_id = {c["id"]: c for c in choices}
    for feat in feats:
        prefix = _feat_cid_prefix(feat)
        variant_choice = by_id.get(f"{prefix}:spell-variant")
        chosen = slug(variant_choice["selected"][0]) if variant_choice and variant_choice.get("selected") else None
        if feat["index"] in (follow_variants or {}):  # G5: the list is the base feat's (Magic Connoisseur)
            chosen = follow_variants[feat["index"]]

        def applies(variant):
            return variant is None or slug(variant) == chosen

        for entry in feat.get("innate_spells", []) or []:
            if not applies(entry.get("variant")):
                continue
            sheet_entry = _innate_entry_to_sheet(entry, catalog)
            sheet_entry["variant"] = None
            sheet_entry["ability"] = _feat_spell_ability(feat, entry["ability"], choices, feats)
            sheet_entry["featId"] = feat["index"]
            patch = (patches or {}).get((feat["index"], entry["spell_id"]))  # RP5 cross-feat modifications
            if patch:
                sheet_entry["uses"] = patch.get("uses", sheet_entry["uses"])
                if patch.get("note"):
                    sheet_entry["note"] = patch["note"]
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


def _spell_visible(catalog: Catalog, spell: dict, sources=None, ruleset: str = "mixed") -> bool:
    """Whether a spell may be offered under the draft's sources and ruleset.
    Sources: the shared `_source_allowed`. "2014" hides 2024-book spells;
    when a spell exists in both versions (`catalog.spell_twins`) "2024" keeps
    only the 2024 one and "mixed" (and anything unknown) only the 2014 one,
    unless the other version's book is itself excluded by `sources`. Purely
    an offer filter - resolve() still honours any catalog spell id."""
    if not _source_allowed(spell, sources) or not ruleset_allows(spell, "spell", ruleset):
        return False
    twin = catalog.spells.get(catalog.spell_twins.get(spell["index"]))
    if twin is None or ruleset == "2014" or not _source_allowed(twin, sources):
        return True
    is_2024 = (spell.get("ruleset") or "2014") == "2024"
    return is_2024 if ruleset == "2024" else not is_2024


def _subclass_visible(catalog: Catalog, sub: dict, sources=None, ruleset: str = "mixed") -> bool:
    """Whether a subclass may be offered under the draft's sources and ruleset
    (same twin rule as `_spell_visible`, over `catalog.subclass_twins`): a
    2014/2024 pair shows its 2014 record under "mixed" (and unknown values),
    its 2024 record under "2024", unless the other version's book is excluded
    by `sources`; "2014" hides 2024 records. A subclass without a twin is
    shown under every ruleset except 2014-hides-2024. Purely an offer filter -
    resolve() accepts any catalog subclass of the class."""
    if not _source_allowed(sub, sources) or not ruleset_allows(sub, "subclass", ruleset):
        return False
    twin = catalog.subclasses.get(catalog.subclass_twins.get(sub["index"]))
    if twin is None or ruleset == "2014" or not _source_allowed(twin, sources):
        return True
    is_2024 = (sub.get("ruleset") or "2014") == "2024"
    return is_2024 if ruleset == "2024" else not is_2024


_VISIBLE_SPELLS: dict = {}


def _visible_spell_ids(catalog: Catalog, sources, ruleset: str):
    """FX1: ids of the spells `_spell_visible` accepts, built once per (catalog, sources, ruleset) instead of
    once per `_spell_filter_options` call (6 per 2024 Bard 20 resolve over ~936 spells). The entry keeps a
    reference to the spells dict and its size, so a patched or reloaded catalog never reads a stale set.
    Returns None (caller falls back to per-spell checks) for unhashable `sources`."""
    try:
        key = (id(catalog.spells), len(catalog.spells), tuple(sources) if sources else (), ruleset)
        hash(key)
    except TypeError:
        return None
    hit = _VISIBLE_SPELLS.get(key)
    if hit is not None and hit[0] is catalog.spells:
        return hit[1]
    ids = frozenset(sp["index"] for sp in catalog.spells.values() if _spell_visible(catalog, sp, sources, ruleset))
    if len(_VISIBLE_SPELLS) >= 16:
        _VISIBLE_SPELLS.clear()
    _VISIBLE_SPELLS[key] = (catalog.spells, ids)
    return ids


def _spell_filter_options(catalog: Catalog, flt: dict, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    """Catalog spells matching a parsed feat spell filter (see
    official_source._parse_spell_filter), sorted by (level, name), as
    reference options. Spells in `keep` (already-selected ids) stay offered
    even when the ruleset/sources would hide them."""
    visible = _visible_spell_ids(catalog, sources, ruleset)
    matches = []
    for sp in catalog.spells.values():
        if sp["index"] not in keep:
            shown = _spell_visible(catalog, sp, sources, ruleset) if visible is None else sp["index"] in visible
            if not shown:
                continue
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


def _spell_filter_description(count: int, flt: dict):
    """"Choose 2 cantrips from the Cleric list." as a tagged message: the noun is built from nested pieces (count, level,
    school, class list, Ritual tag) so each language orders them its own way."""
    level = flt.get("level")
    if level == [0]:
        noun = msg("noun-cantrip", n=count)
    elif level:
        noun = msg("noun-spell-levels", n=count, levels=list(level))
    else:
        noun = msg("noun-spell", n=count)
    if flt.get("school"):
        noun = msg("noun-school", schools=[x.title() for x in flt["school"]], noun=noun)
    if flt.get("class"):
        noun = msg("noun-from-list", noun=noun, classes=[x.title() for x in flt["class"]])
    if flt.get("ritual"):
        noun = msg("noun-ritual", noun=noun)
    return msg("desc-choose-noun", count=count, noun=noun)


def _feat_spell_choice_templates(
    feats: list[dict], catalog: Catalog, origin: str | None = None,
    raw_selections: dict | None = None, variant_hints: dict | None = None, total_level: int = 0,
    sources=None, ruleset: str = "mixed", follow_variants: dict | None = None,
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
                "label": msg("label-prefixed", head=feat["name"], tail=msg("label-spellcasting-ability")),
                "description": msg("desc-spell-ability"), "count": 1,
                "options": [{"id": a.lower(), "label": SAVE_ABILITY_NAMES[a.lower()]} for a in abil["choose"]],
            })
        chosen = None
        variants = feat.get("spell_variants") or []
        if variants and feat["index"] in (follow_variants or {}):
            # G5: the list is the base feat's pick (`_followed_variants`): no card of its own, and no spell cards until
            # the base feat has picked a list this feat offers.
            chosen = follow_variants[feat["index"]]
            if chosen is None:
                continue
        elif variants:
            hinted = variant_hints.get(feat["index"])
            offered = [v for v in variants if v == hinted] or variants
            options = []
            for name in offered:
                fixed = [e["name"] for e in feat.get("innate_spells", []) if e.get("variant") == name]
                options.append({"id": slug(name), "label": f"{name} ({', '.join(fixed)})" if fixed else name})
            vcid = f"{prefix}:spell-variant"
            variant_card = {
                "id": vcid, "source": source, "label": msg("label-prefixed", head=feat["name"], tail=msg("label-spell-list")),
                "description": msg("desc-spell-list"),
                "count": 1, "options": options,
            }
            if feat.get("repeatable") and len(variants) > 1:
                # WF: XPHB Magic Initiate "You can take this feat more than once, but you must choose a different spell
                # list each time." A background-fixed list (Genie Touched: Wizard) is held even before it is clicked.
                variant_card["distinctGroup"] = f"{feat['index']}:spell-variant"
                if len(options) == 1:
                    variant_card["distinctFixed"] = [options[0]["id"]]
            templates.append(variant_card)
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
                picked = raw_selections.get(f"{prefix}:spell-choice-{i}")
                options = _spell_filter_options(
                    catalog, sc["filter"], sources, ruleset,
                    keep={x for x in picked if isinstance(x, str)} if isinstance(picked, list) else (),
                )
                description = _spell_filter_description(count, sc["filter"])
                kind = msg("label-cantrip") if sc["filter"].get("level") == [0] else msg("label-spell")
            else:
                listed = dict.fromkeys(catalog.resolve_spell_id(sid) for sid in (sc.get("from") or []))
                options = [
                    {"option_type": "reference", "item": {"index": sid, "name": catalog.spells[sid]["name"]}}
                    for sid in listed if sid
                ]
                count = min(count, len(options))
                description = msg("desc-listed-spells", n=count)
                kind = msg("label-spell")
            if not options or count < 1:
                continue
            envelope = {"choose": count, "from": {"option_set_type": "options_array", "options": options}}
            tpl = build_choice_template(
                envelope, f"{prefix}:spell-choice-{i}", source, msg("label-prefixed", head=feat["name"], tail=kind), description=description,
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


def _feat_ability_cap(feat: dict) -> int:
    """The ceiling of a feat's own ability increase: 20, or 30 for an Epic Boon (catalog `ability_cap`, FE2)."""
    return feat.get("ability_cap") or asi_mod.ASI_CAP


def _feat_ability_bonus_choice_templates(
    feats: list[dict], origin: str | None = None, scores: dict[str, int] | None = None,
) -> list[tuple[dict, dict]]:
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
        description = msg("desc-asi-increase", n=choose, bonus=1)
        label = msg("label-prefixed", head=feat["name"], tail=msg("label-ability-score-increase"))
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
            if scores is not None:
                cap = _feat_ability_cap(feat)
                deltas_by_option = _feat_ability_bonus_deltas(envelope)
                for option in tpl["options"]:
                    if asi_mod.asi_exceeds_cap(deltas_by_option.get(option["id"], []), scores, cap):
                        option["disabled"] = True
                        option["disabledReason"] = msg("disabled-feat-ability-max", cap=cap)
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
    # Race gate (5etools `race` prerequisite): lowercased species name with a
    # trailing " (...)" stripped, lowercased subspecies name plus each token
    # of its index, the species size, and whether the character can cast at
    # least one spell (a Spellcasting feature or an innate species spell).
    race_names: set[str] = field(default_factory=set)
    subrace_names: set[str] = field(default_factory=set)
    size: str | None = None
    can_cast_spell: bool = False
    # C3: the character has a "Fighting Style" class feature (any class, any
    # edition's feature of that name). Gates the Fighting Style feats (FS, FS:P,
    # FS:R) at Ability Score Improvements and the 5etools `feature: Fighting Style`
    # prerequisite.
    fighting_style: bool = False

    def copy(self) -> "_HeldFeatState":
        return _HeldFeatState(
            set(self.feat_indices), set(self.feat_categories), set(self.proficiency_ids),
            self.has_spellcasting_feature, set(self.race_names), set(self.subrace_names),
            self.size, self.can_cast_spell, self.fighting_style,
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
    cap_skipped_feat_cids: set[str] | None = None,
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
      over the FEAT'S cap (asi_mod.asi_exceeds_cap, the check combos get,
      with `cap` = the feat's own `ability_cap`: 20, or 30 for an Epic
      Boon, FE2). Combos always stay at 20. The feat itself still counts
      as taken; only the increase is skipped, and the cid is added to
      `cap_skipped_feat_cids` (when given) so resolve() knows which delta
      was NOT applied. (The background / species side — an origin feat's
      bonus, folded into `feat_bonuses` before this walk — is clamped at
      the same cap in resolve(), FE2 / B2.)

    What keeps scores in range: resolve()'s 1-30 range check runs BEFORE
    this walk, on the pre-ASI scores, and nothing re-checks afterwards.
    This walk never needs it, because every delta it applies — combo or
    feat — is cap-gated (20, or 30 for an Epic Boon), so it never raises
    any score above max(that cap, that score's pre-walk value).

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
            if deltas:
                if asi_mod.asi_exceeds_cap(deltas, running, _feat_ability_cap(asi_feats_by_cid[cid])):
                    if cap_skipped_feat_cids is not None:
                        cap_skipped_feat_cids.add(cid)
                else:
                    running = asi_mod.apply_asi(deltas, running)
    return scores_by_level, running, blocked_feat_cids


def _source_allowed(record: dict, sources) -> bool:
    """The ONE draft.sources filter, shared by species, subspecies,
    backgrounds and feats: no filtering when `sources` is empty or absent; a
    record with no source, or an "SRD" one, is always allowed; otherwise its
    source must be in the allowed list (case-insensitive)."""
    if not sources:
        return True
    source = record.get("source") or ""
    if not source or source.upper() == "SRD":
        return True
    try:
        allowed_sources = _lowered_sources(tuple(sources))
    except TypeError:  # unhashable junk in a hand-edited draft: no cache
        allowed_sources = {s.lower() for s in sources if isinstance(s, str)}
    return source.lower() in allowed_sources


@lru_cache(maxsize=64)
def _lowered_sources(sources: tuple) -> frozenset:
    """FX1: the lowered allowed-source set, built once per distinct `sources` tuple (it used to be rebuilt on
    every `_source_allowed` call, ~100k calls per 2024 Bard 20 resolve)."""
    return frozenset(s.lower() for s in sources if isinstance(s, str))


def _feat_source_allowed(feat: dict, sources) -> bool:
    return _source_allowed(feat, sources)


def _feat_offered(feat: dict, sources, ruleset: str = "mixed") -> bool:
    """A feat that may be offered (and honored) as an option: allowed by
    draft.sources and visible under the draft's ruleset. G1: under 2024 a Fighting
    Style feat of another book than XPHB (Arcane Warrior, AU) needs its book in an
    explicit source list; the 2024 book lists exactly its own Fighting Style feats."""
    if (ruleset == "2024" and (feat.get("category") or "") in _FS_FEAT_CATEGORIES and feat.get("source") != "XPHB"
            and not any(isinstance(s, str) and s.lower() == (feat.get("source") or "").lower() for s in sources or [])):
        return False
    return _source_allowed(feat, sources) and ruleset_allows(feat, "feat", ruleset)


def _fi_seen_add(seen: dict[str, str], catalog: Catalog, feat: dict, stored, ruleset: str) -> None:
    """RP4 (A4): under ruleset 2024 a held Fighting Initiate style joins `seen` as `name:<style>` at the feat's
    position, so a LATER Fighting Style feat card / ASI pick of the same-named FS feat is the duplicate (first holder
    wins). Only a valid stored pick of the six fighter styles counts; mixed / 2014 are untouched (FE9 `pruned` path)."""
    if ruleset != "2024" or not isinstance(stored, list):
        return
    spec = (fed_option_picks(feat) or {})
    if spec.get("kind") != "fighting-style":
        return
    options = _srd_style_options(catalog, _FIGHTER_STYLE_FEATURE)
    pick = next((x for x in stored if isinstance(x, str) and x in options), None)
    if pick:
        seen.setdefault("name:" + options[pick], f"{options[pick].title()}, Fighting Initiate")


def fed_option_picks(feat: dict) -> dict | None:
    from catalog import feat_effects_data
    return (feat_effects_data.FEAT_EFFECTS.get(feat.get("index")) or {}).get("option_picks")


def _resolve_asi_selected_feats(
    resolved_classes: list[dict], catalog: Catalog, sources=None,
    taken_indices: dict[str, str] | None = None, skipped_duplicates: list[dict] | None = None,
    ruleset: str = "mixed", fighting_style: bool = False,
    before_level=None, taken_before_cid: dict[str, dict[str, str]] | None = None, after_feat=None,
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
    (_is_asi_eligible_feat for the ruleset and ASI slot level, and allowed
    by draft.sources via _feat_offered) is resolved; a hand-edited draft naming some
    other catalog feat is ignored here just as the generic choice pass
    ignores it (it isn't a valid option id).

    Duplicate prevention: a non-`repeatable` feat already in
    `taken_indices` (the background's granted feats) or picked at an
    EARLIER ASI level is skipped — the first pick wins, a later duplicate
    isn't applied — and appended to `skipped_duplicates` (when given) so
    resolve() can report it.

    F1: the walk is one ordered pass shared with the C3 fighting-style cards.
    `before_level(rc, upto_level_or_None, seen)` is called before each ASI level (and
    with None after the class's last one) so the cards of levels <= that level resolve
    first against the same `seen` map; `taken_before_cid[cid]` receives a snapshot of
    `seen` before each ASI level (what its options read for "already taken").
    RP20: `after_feat(rc, level, feat, seen)` is called right after an accepted pick (Eldritch Adept's Lessons of the
    First Ones resolves its Origin feat there, at the feat's own position)."""
    asi_feat_picks: list[dict] = []
    seen: dict[str, str] = dict(taken_indices or {})
    feat_deltas_by_cid: dict[str, list[tuple[str, int]]] = {}
    for rc in resolved_classes:
        cls_id, cls, level, class_choices = rc["cls_id"], rc["cls"], rc["level"], rc["class_choices"]
        if not (cls_id and cls):
            continue
        for lvl in _asi_granting_levels(catalog, cls_id, level):
            cid = f"class:{cls_id}:{lvl}:asi"
            if before_level:
                before_level(rc, lvl, seen)
            if taken_before_cid is not None:
                taken_before_cid[cid] = dict(seen)
            raw_selected = class_choices.get(cid) or []
            if not isinstance(raw_selected, list):
                continue
            selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
            if not (len(selected) == 1 and selected[0].startswith("feat:")):
                continue
            catalog_feat = catalog.feats.get(selected[0][len("feat:"):])
            if not (catalog_feat and _asi_pick_honored(catalog_feat, sources, ruleset, lvl, fighting_style)):
                continue
            if _taken_reason(catalog_feat, seen):
                if skipped_duplicates is not None:
                    skipped_duplicates.append({"feat": catalog_feat, "cid": cid, "level": lvl, "cls": cls})
                continue
            _taken_add(seen, [catalog_feat])
            origin = f"{cid}:feat:{catalog_feat['index']}"
            _fi_seen_add(seen, catalog, catalog_feat, class_choices.get(f"{origin}:fighting-style"), ruleset)  # RP4
            feat = {**catalog_feat, "_asi_cid": cid, "_asi_level": lvl, "_asi_origin": origin}
            asi_feat_picks.append(feat)
            if after_feat:
                after_feat(rc, lvl, feat, seen)

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
        if before_level:
            before_level(rc, None, seen)
    return asi_feat_picks, feat_deltas_by_cid


def _label_is(label, key: str) -> bool:
    """True when a card label is the tagged catalog message `key` (the engine compares labels by key, never by text, so
    the comparison does not depend on the wording or on the language)."""
    return getattr(label, "key", None) == key


def _provisional_choice_label(envelope: dict):
    """The first label of a class proficiency envelope; `_class_choice_templates` relabels a non-skill one afterwards."""
    kind = envelope.get("type")
    if kind == "proficiencies":
        return msg("label-skill-proficiencies")
    return kind.title() if kind else msg("label-choice")


def _class_choice_templates(cls: dict, cls_id: str) -> list[dict]:
    templates = []
    for i, envelope in enumerate(cls.get("proficiency_choices", [])):
        cid = f"class:{cls_id}:1:prof-choice-{i}"
        source = {"kind": "class", "id": cls_id, "label": cls["name"], "level": 1}
        tpl = build_choice_template(envelope, cid, source, _provisional_choice_label(envelope))
        if not tpl:
            continue
        # Some classes (Bard, Monk) have a SECOND proficiency_choices entry
        # also typed "proficiencies" that isn't actually a skill choice
        # (instruments/tools) — relabel based on what the resolved options
        # actually are, not the envelope's own (misleading) type field.
        if tpl["options"] and _label_is(tpl["label"], "label-skill-proficiencies") and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = msg("label-tool-proficiencies")
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
        tpl = build_choice_template(envelope, cid, source, _provisional_choice_label(envelope))
        if not tpl:
            continue
        if tpl["options"] and _label_is(tpl["label"], "label-skill-proficiencies") and not all(o["id"].startswith("skill-") for o in tpl["options"]):
            tpl["label"] = msg("label-tool-proficiencies")
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


def _optional_feature_options(catalog: Catalog, option_ids, skip=(), class_level: int | None = None) -> list[dict]:
    """The options of an optionalfeatureProgression list (`opt-*` records): label = name; an option with a level
    prerequisite above `class_level` is disabled (FE9: `class_level` None = no level check, the Martial Adept list)."""
    options = []
    for opt_id in option_ids:
        opt = catalog.features.get(opt_id)
        if not opt or opt_id in skip:
            continue
        option = {"id": opt_id, "label": opt["name"]}
        desc = _join_desc(opt.get("desc"))
        if desc:
            option["description"] = desc
        need = opt.get("prerequisite_level")
        if need and class_level is not None and need > class_level:
            option["disabled"] = True
            option["disabledReason"] = msg("disabled-requires-level", level=need)
        options.append(option)
    return options


def _optional_progression_template(catalog: Catalog, feature: dict, cid: str, source: dict, class_level: int) -> dict | None:
    """Subclass picks from optionalfeatureProgression (maneuvers, runes, ...):
    the count is the progression value of the highest level reached; options
    with a level prerequisite above the class level are shown disabled."""
    spec = feature["feature_specific"]["optional_progression"]
    reached = [int(k) for k in spec["progression"] if int(k) <= class_level]
    if not reached:
        return None
    granted_ids = [oid for lvl, ids in (spec.get("required") or {}).items() if int(lvl) <= class_level
                   for oid in ids if oid in catalog.features]
    options = _optional_feature_options(catalog, spec["options"], granted_ids, class_level)
    description = _join_desc(feature.get("desc")) or ""
    tpl = {
        "id": cid, "source": source, "label": feature["name"], "description": description,
        "count": max(0, spec["progression"][str(max(reached))] - len(granted_ids)), "count_by_level": True,
        "options": options,
    }
    if granted_ids:
        tpl["granted"] = [{"id": oid, "label": catalog.features[oid]["name"]} for oid in granted_ids]
        names = ", ".join(g["label"] for g in tpl["granted"])
        tpl["description"] = (msg("desc-granted-automatically-after", text=description, names=names, n=len(granted_ids))
                              if description else msg("desc-granted-automatically", names=names, n=len(granted_ids)))
    return tpl


def _text_options_template(spec: dict, cid: str, source: dict, name: str, description,
                           sources=None, keep=()) -> dict:
    """Build-time pick among options that the feature text lists (Totem
    Spirit, Storm Aura...). Option ids are `<featureId>--<slug>`. G1: an option
    with its own `source` (Elk/Tiger, SCAG) follows draft.sources like other
    source-gated options: hidden when its source is off, unless already stored
    (then kept and flagged `hiddenByFilters`)."""
    options = []
    for opt in spec["options"]:
        hidden = not _source_allowed({"source": opt.get("source")}, sources)
        if hidden and opt["id"] not in keep:
            continue
        option = {"id": opt["id"], "label": opt["name"]}
        if hidden:
            option["hiddenByFilters"] = True
        desc = _join_desc(opt.get("desc"))
        if desc:
            option["description"] = desc
        options.append(option)
    return {"id": cid, "source": source, "label": name, "description": description or "",
            "count": spec.get("count", 1), "options": options}


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[tuple[int, dict]], subclass_id: str | None,
    class_level: int | None = None, skip_features: frozenset[str] | set[str] = frozenset(),
    sources=None, class_choices: dict | None = None,
) -> list[dict]:
    templates = []
    if class_level is None:
        class_level = max((lvl for lvl, _ in feature_refs), default=1)
    for lvl, ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature or ref["index"] in skip_features:  # C3: replaced by a fighting-style feat card
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
            if tpl and feature["index"] in reference_data.SRD_METAMAGIC_FEATURES:  # G2: the TCE options
                tpl["options"] = _with_extra_metamagic(catalog, tpl["options"], "Metamagic: ")
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
        elif specific.get("optional_progression"):
            cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
            tpl = _optional_progression_template(catalog, feature, cid, source, class_level)
        elif specific.get("text_options"):
            cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
            stored = (class_choices or {}).get(cid)
            tpl = _text_options_template(specific["text_options"], cid, source, feature["name"], description,
                                         sources, stored if isinstance(stored, list) else ())
        else:
            continue
        if tpl:
            templates.append(tpl)
    return templates


def _background_proficiency_choice_label(envelope: dict):
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
        return msg("label-skill-proficiency")
    if set_type == "any_skill_or_tool":
        return msg("label-skill-or-tool-proficiency")
    if set_type == "any_tool":
        category = from_field.get("tool_category")
        return msg("label-tool-proficiency-category", category=category) if category else msg("label-tool-proficiency")
    options = from_field.get("options", [])
    first_index = (options[0].get("item") or {}).get("index", "") if options else ""
    return msg("label-skill-proficiency") if first_index.startswith("skill-") else msg("label-tool-proficiency")


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


def _feat_choice_templates(feats: list[dict], origin: str | None = None, items: dict | None = None,
                           catalog: Catalog | None = None, ruleset: str = "mixed") -> list[dict]:
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
            description = msg("desc-feat-languages", n=choose)
            label = msg("label-prefixed", head=feat["name"], tail=msg("label-languages"))
            tpl = build_choice_template(language_envelope, cid, source, label, description=description)
            if tpl:
                templates.append(tpl)

        replacement_tpl = class_choices_2024.feat_replacement_language_template(feat, cid_prefix, feat_level)  # RP3
        if replacement_tpl and not language_envelope:
            templates.append(replacement_tpl)

        for i, prof_envelope in enumerate(feat.get("proficiency_choices", []) or []):
            cid = f"{cid_prefix}:proficiency-choice-{i}"
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            if feat_level is not None:
                source["level"] = feat_level
            base_label = _background_proficiency_choice_label(prof_envelope)
            label = msg("label-prefixed", head=feat["name"], tail=base_label)
            choose = prof_envelope.get("choose", 1)
            description = msg("desc-feat-proficiencies", n=choose)
            tpl = build_choice_template(prof_envelope, cid, source, label, description=description)
            if tpl:
                if feat_effects_data.FEAT_EFFECTS.get(feat["index"], {}).get("prof_or_expertise"):
                    tpl["profOrExpertise"] = True  # FE6: an already proficient skill becomes Expertise (F-D4)
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
            description = msg("desc-feat-expertise", n=choose)
            tpl = build_choice_template(env, f"{cid_prefix}:expertise-choice-{i}", source,
                                        msg("label-prefixed", head=feat["name"], tail=msg("label-expertise")), description=description)
            if tpl:
                if feat_effects_data.FEAT_EFFECTS.get(feat["index"], {}).get("lacks_expertise"):
                    tpl["lacksExpertise"] = True  # FE6 (B7): the feat's own text, whatever the ruleset
                templates.append(tpl)

        for i, env in enumerate(feat.get("saving_throw_choices", []) or []):
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            if feat_level is not None:
                source["level"] = feat_level
            choose = env.get("choose", 1)
            description = msg("desc-feat-saves", n=choose)
            tpl = build_choice_template(env, f"{cid_prefix}:save-choice-{i}", source,
                                        msg("label-prefixed", head=feat["name"], tail=msg("label-saving-throw")), description=description)
            if tpl:
                templates.append(tpl)
        templates += _feat_extra_templates(feat, cid_prefix, feat_level, items, catalog, ruleset)  # FE7, FE8, FE9, RP20
    return templates


# FE9: card suffix, label and description per `option_picks` kind.
# (the label tail is the rules term and stays English; the description is a tagged message built from the count)
_OPTION_PICK_CARDS = {
    "fighting-style": ("fighting-style", "Fighting Style", lambda n: msg("desc-pick-fighting-style", n=n)),
    "maneuver": ("maneuvers", "Maneuvers", lambda n: msg("desc-pick-maneuver", n=n)),
    "metamagic": ("metamagic", "Metamagic", lambda n: msg("desc-pick-metamagic", n=n)),
    "invocation": ("invocation", "Eldritch Invocation", lambda n: msg("desc-pick-invocation", n=n)),
}
_FIGHTER_STYLE_FEATURE = "fighter-fighting-style"
_BATTLE_MASTER_FEATURE = "battle-master-phb-3-battle-master"
_SRD_METAMAGIC_FEATURE = "metamagic-1"


def _with_extra_metamagic(catalog: Catalog, options: list[dict], prefix: str) -> list[dict]:
    """G2: the SRD Metamagic options (the eight PHB ones) plus the 2014 options the SRD lacks that the vendored data has
    (Seeking Spell and Transmuted Spell, TCE; `catalog.features` holds them only with the official data), in name order.
    `prefix` is the SRD label prefix ("Metamagic: " on the Sorcerer cards, none on the Metamagic Adept feat card)."""
    extra = [f for f in catalog.features.values()
             if "MM" in (f.get("feature_types") or []) and f.get("ruleset") == "2014" and f["index"].startswith("opt-")]
    if not extra:
        return options
    new = []
    for rec in extra:
        option = {"id": rec["index"], "label": prefix + rec["name"]}
        desc = _join_desc(rec.get("desc"))
        if desc:
            option["description"] = desc
        new.append(option)
    return sorted(options + new, key=lambda o: o["label"].removeprefix(prefix))
_SRD_INVOCATIONS_FEATURE = "eldritch-invocations"


_XPHB_BATTLE_MASTER_FEATURE = "battle-master-xphb-3-battle-master"


def _option_pick_options(catalog: Catalog, kind: str, ruleset: str = "mixed") -> list[dict]:
    """FE9 (V5-V8): the option pool of an `option_picks` feat. Fighting style: the SRD fighter styles (the TCE styles
    are not imported); maneuver: the Battle Master (PHB) list, i.e. PHB + TCE maneuvers; metamagic: the SRD Metamagic
    options; invocation: the SRD invocations (prerequisites are enforced late, by `_gate_feat_invocation_prereqs`).
    RP20 (A3): under ruleset 2024 the 2024 class lists replace them ("the versions of things in this book replace
    versions from older books"): invocation = the 28 XPHB invocations, metamagic = the 10 XPHB options (with their Sorcery
    Point cost), maneuver = the 20 maneuvers of the XPHB Battle Master. A catalog without those records keeps the FE9
    pool. Fighting Initiate keeps the SRD styles (no 2024 style-option records exist)."""
    if ruleset == "2024":
        if kind == "invocation":
            records = class_choices_2024.invocation_records(catalog)
            if records:
                return [{"id": r["index"], "label": r["name"], **({"description": _join_desc(r["desc"])} if r.get("desc") else {})}
                        for r in records]
        elif kind == "metamagic":
            records = class_choices_2024.metamagic_records(catalog)
            if records:
                return class_choices_2024.metamagic_options(records)
        elif kind == "maneuver":
            spec = ((catalog.features.get(_XPHB_BATTLE_MASTER_FEATURE) or {}).get("feature_specific") or {}).get("optional_progression")
            options = _optional_feature_options(catalog, (spec or {}).get("options") or [])
            if options:
                return options
    if kind == "maneuver":
        spec = ((catalog.features.get(_BATTLE_MASTER_FEATURE) or {}).get("feature_specific") or {}).get("optional_progression")
        return _optional_feature_options(catalog, (spec or {}).get("options") or [])
    if kind == "invocation":
        refs = ((catalog.features.get(_SRD_INVOCATIONS_FEATURE) or {}).get("feature_specific") or {}).get("invocations") or []
        options = []
        for ref in refs:
            inv = catalog.features.get(ref["index"]) or {}
            option = {"id": ref["index"], "label": ref["name"].replace("Eldritch Invocation: ", "")}
            desc = _join_desc(inv.get("desc"))
            if desc:
                option["description"] = desc
            options.append(option)
        return options
    prefix, feature_id = (("Fighting Style: ", _FIGHTER_STYLE_FEATURE) if kind == "fighting-style"
                          else ("Metamagic: ", _SRD_METAMAGIC_FEATURE))
    refs = (((catalog.features.get(feature_id) or {}).get("feature_specific") or {}).get("subfeature_options") or {}) \
        .get("from", {}).get("options", [])
    options = []
    for ref in refs:
        rec = catalog.features.get((ref.get("item") or {}).get("index") or "")
        if not rec:
            continue
        option = {"id": rec["index"], "label": rec["name"].removeprefix(prefix)}
        desc = _join_desc(rec.get("desc"))
        if desc:
            option["description"] = desc
        options.append(option)
    return _with_extra_metamagic(catalog, options, "") if kind == "metamagic" else options


def _feat_extra_templates(feat: dict, cid_prefix: str, feat_level: int | None = None, items: dict | None = None,
                          catalog: Catalog | None = None, ruleset: str = "mixed") -> list[dict]:
    """FE7: the cards a feat's effect entry asks for, under the same `<prefix>:<kind>` cids as its other
    cascaded cards (so the feat-kind merge sites and the page filters route them without change). Called for every
    feat instance by `_feat_choice_templates`, i.e. at all five sites (background, species, Fighting Style,
    Lessons, ASI).
      * `resist_choice`  -> `:resistance-choice` (the picks join damageModifiers.resistances);
      * `damage_type_choice` -> `:damage-type` (a repeatable feat taken again must pick a different type:
        `distinctGroup`, enforced by `_gate_distinct_choices`);
      * `variant_choice` -> `:<suffix>` (Strike of the Giants `:giant-type`).
    FE8 (`items` = the catalog items): `weapon_proficiency_choice` -> `:weapon-choice` (Weapon Master PHB: the picks
    join the proficient weapons, see `_feat_weapon_proficiencies`); `mastery_choice` -> `:weapon-mastery` (Weapon Master
    XPHB: gated by `_gate_mastery_choices`, joins sheet.weaponMasteries).
    FE9 (`catalog`): `option_picks` -> the feat's own option card (`_OPTION_PICK_SUFFIX`): Fighting Initiate's fighter
    style, Martial Adept's maneuvers, Metamagic Adept's options, Eldritch Adept's invocation (+ its spellcasting
    ability); see `_option_pick_options` and `_gate_option_picks`.
    Scion's resistance has no card: it follows the `:spell-variant` pick."""
    effect = feat_effects_data.FEAT_EFFECTS.get(feat["index"]) or {}
    source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
    if feat_level is not None:
        source["level"] = feat_level
    templates = []

    def card(suffix: str, label, description, count: int, options: list[dict], **extra) -> dict:
        return {"id": f"{cid_prefix}:{suffix}", "source": dict(source), "label": msg("label-prefixed", head=feat["name"], tail=label),
                "description": description, "count": count, "options": options, **extra}

    def types(ids):
        return [{"id": t, "label": t.capitalize()} for t in ids]

    spec = effect.get("resist_choice")
    if spec:
        n = spec["count"]
        templates.append(card(
            "resistance-choice", msg("label-damage-resistance"), msg("desc-resist-types", n=n), n, types(spec["options"])))
    spec = effect.get("damage_type_choice")
    if spec:
        extra = {"distinctGroup": feat_effects_mod._name_key(feat)} if spec.get("distinct_across_repeats") else {}
        templates.append(card("damage-type", msg("label-damage-type"), msg("desc-damage-type"), 1,
                              types(spec["options"]), **extra))
    spec = effect.get("variant_choice")
    if spec:
        templates.append(card(spec["suffix"], spec["label"], spec["description"], 1,
                              [{"id": o["id"], "label": o["label"]} for o in spec["options"]]))
    spec = effect.get("option_picks")
    if spec and catalog is not None:
        options = _option_pick_options(catalog, spec["kind"], ruleset)
        if options:
            n = spec["count"]
            suffix, label, describe = _OPTION_PICK_CARDS[spec["kind"]]
            templates.append(card(suffix, label, describe(n), n, options))
            if spec["kind"] == "invocation":
                templates.append(card("invocation-ability", msg("label-spellcasting-ability"),
                                      msg("desc-invocation-ability"), 1,
                                      [{"id": a.lower(), "label": name} for a, name in
                                       (("INT", "Intelligence"), ("WIS", "Wisdom"), ("CHA", "Charisma"))]))
    for key, suffix, make_label, make_desc in (
            ("weapon_proficiency_choice", "weapon-choice", lambda: msg("label-weapon-proficiencies"),
             lambda n: msg("desc-weapon-proficiency-choice", n=n)),
            ("mastery_choice", "weapon-mastery", lambda: msg("label-weapon-mastery"),
             lambda n: msg("desc-weapon-mastery-feat", n=n))):
        spec = effect.get(key)
        if not spec or not items:
            continue
        cats = {c.capitalize() for c in spec["categories"]}
        options = []
        for item in items.values():
            if item.get("equipment_category", {}).get("index") != "weapon" or item.get("weapon_category") not in cats:
                continue
            if key == "mastery_choice":
                if item.get("mastery"):
                    options.append({"id": item["index"], "label": f"{item['name']} ({item['mastery']})"})
            else:
                options.append({"id": item["index"], "label": item["name"]})
        if options:
            n = spec["count"]
            templates.append(card(suffix, make_label(), make_desc(n), n, options))
    return templates


def _gate_distinct_choices(choices: list[dict], class_order: list[str] = ()) -> list[dict]:
    """FE7: cards flagged `distinctGroup` (Elemental Adept: "you must choose a different damage type" each time)
    may not repeat an option across the instances of the same feat group (both editions share the group). Walk order
    is origin feats first, then ASI feat cards by (class order, ASI level); the later pick is the duplicate: its option
    is disabled "already chosen for <feat> (n)" (n = which instance holds it) and a stored duplicate is dropped with a
    `pruned` entry. Mutates `choices` in place; returns the pruned entries."""
    indexes = [i for i, c in enumerate(choices) if c.get("distinctGroup")]
    if not indexes:
        return []

    def walk_key(i: int):
        m = _ASI_FEAT_CID_RE.match(choices[i]["id"])
        if not m:
            return (0, 0, 0, i)
        cls_id = m.group(1)
        return (1, class_order.index(cls_id) if cls_id in class_order else len(class_order), int(m.group(2)), i)

    pruned_by_index: dict[int, dict] = {}
    dependents: list[str] = []
    held: dict[str, dict[str, int]] = {}  # group -> {option id: instance number}
    count: dict[str, int] = {}
    for i in sorted(indexes, key=walk_key):
        c = choices[i]
        group = c["distinctGroup"]
        count[group] = count.get(group, 0) + 1
        taken = held.setdefault(group, {})
        name = c["source"]["label"]
        options = [o if o.get("disabled") or o["id"] not in taken
                   else {**o, "disabled": True, "disabledReason": msg("disabled-already-chosen-for-n", name=name, n=taken[o["id"]])}
                   for o in c["options"]]
        kept = [s for s in c.get("selected", []) if s not in taken]
        dropped = [s for s in c.get("selected", []) if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            pruned_by_index[i] = {"choiceId": c["id"], "reason": msg(
                "pruned-distinct-duplicate", label=c["label"], names=[labels.get(d, d) for d in dropped], name=name,
                n=taken[dropped[0]])}
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
        for s in kept:
            taken[s] = count[group]
        for fixed in c.get("distinctFixed", []):  # WF: a list the background fixes is held by this instance
            taken.setdefault(fixed, count[group])
        if dropped and c["id"].endswith(":spell-variant"):  # WF: the spell picks of the dropped list go with it
            dependents.append(c["id"][:-len("spell-variant")] + "spell-choice-")
    if dependents:
        choices[:] = [c for c in choices if not any(c["id"].startswith(d) for d in dependents)]
    return [pruned_by_index[i] for i in sorted(pruned_by_index)]


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


_ASI_FEAT_CID_RE = re.compile(r"^class:([^:]+):(\d+):asi:feat:")


def _prof_or_expertise_priors(choices: list[dict], resolved_feats: list[dict], fixed_origin_skills: set[str],
                              class_order: list[str]) -> dict[str, set[str]]:
    """FE6 (F-D4): for every card flagged `profOrExpertise` (Keen Mind / Observant XPHB: "If you lack proficiency
    in the chosen skill, you gain proficiency in it, and if you already have proficiency in it, you gain
    Expertise in it"), the skills the character is already proficient in AT THE CARD'S POSITION: origin sources
    (background, species, origin feats) first, then cards and ASI feats at or before its (class order, class
    level), an ASI feat after the class feature of its level, and the flagged cards before it. A later grant of
    the same skill never converts the pick. Returns {card id: skill ids}."""
    flagged = [c for c in choices if c.get("profOrExpertise")]
    if not flagged:
        return {}
    last = (len(class_order) + 1, 0)

    def pos(c: dict):
        return class_choices_2024.card_position(c, class_order) or last

    order = {c["id"]: n for n, c in enumerate(sorted(flagged, key=lambda c: (pos(c), c["id"])))}
    priors: dict[str, set[str]] = {}
    for card in flagged:
        here, rank = pos(card), order[card["id"]]
        prior = set(fixed_origin_skills)
        for c in choices:
            if c is card or c["source"]["kind"] not in ("class", "species", "background", "feat") or "expertise-choice" in c["id"]:
                continue
            if c.get("profOrExpertise"):
                before = order[c["id"]] < rank
            else:
                before = pos(c) <= here
            if before:
                prior.update(s for s in c["selected"] if s.startswith("skill-"))
        for f in resolved_feats:  # fixed skill grants of ASI feats sit at their ASI level
            if f.get("_asi_cid") and (_feat_build_position(f, class_order) or last) <= here:
                prior.update(p for p in _feat_proficiency_ids([f]) if p.startswith("skill-"))
        priors[card["id"]] = prior
    return priors


def _proficiency_grants(choices: list[dict], catalog: Catalog, resolved_classes: list[dict], resolved_feats: list[dict],
                        bg: dict | None, race: dict | None, subrace: dict | None, xphb_effects, class_order: list[str],
                        ) -> list[tuple[tuple[int, int], str]]:
    """RP12: the FIXED skill / tool proficiency grants of the build as (position, proficiency id): origin sources
    (background, species traits, origin feats) at (-1, 0); a class's fixed proficiencies at (class position, 1); a
    subclass's fixed grants (`SUBCLASS_PROFICIENCIES`) at (class position, 3) (every 2024 subclass starts at 3);
    ASI and Lessons feats at their build position; the RP2 XPHB effects (Mercy) at their feature record's level."""
    origin = (-1, 0)
    grants: list[tuple[tuple[int, int], str]] = []
    if bg:
        grants += [(origin, p["index"]) for p in bg.get("starting_proficiencies", [])]
    if race:
        for ref in list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else []):
            trait = catalog.traits.get(ref["index"])
            if trait:
                grants += [(origin, p["index"]) for p in trait.get("proficiencies", [])]
    for f in resolved_feats:
        pos = _feat_build_position(f, class_order) or origin
        grants += [(pos, p) for p in _feat_proficiency_ids([f])]
    for rc in resolved_classes:
        if not rc["cls"] or rc["cls_id"] not in class_order:
            continue
        at = class_order.index(rc["cls_id"])
        fixed = rc["cls"].get("proficiencies", []) if at == 0 else rc["cls"].get("multi_classing", {}).get("proficiencies", [])
        grants += [((at, 1), p["index"]) for p in fixed]
        grants += [((at, 3), p) for p in SUBCLASS_PROFICIENCIES.get(rc["subclass_id"], [])]
    for cls_id, _lvl, effect in xphb_effects:
        if cls_id in class_order:
            level = (catalog.features.get(effect.get("feature_id")) or {}).get("level") or 1
            grants += [((class_order.index(cls_id), level), p)
                       for p in list(effect.get("skills") or []) + list(effect.get("proficiencies") or [])]
    return grants


def _gate_duplicate_skill_picks(choices: list[dict], class_order: list[str]) -> list[dict]:
    """RPF (PHB: you can't gain the same proficiency twice, pick another): generic skill duplicates between the
    ordinary class / species / multiclass proficiency pick cards, all rulesets. The cards are walked in (class order,
    class level) order, origin (species) first and a multiclass card at (its class, 1); a card keeps the skills held
    by the cards before it out of its options ("already proficient") and drops a stored duplicate with a
    non-blocking `pruned` entry. Skill ids only; expertise, Keen Mind style (`profOrExpertise`) and the positioned
    subclass picks have their own gates. Mutates `choices`; returns the pruned entries."""
    last = (len(class_order) + 1, 0)

    def eligible(c: dict) -> bool:
        return (c["source"]["kind"] in ("class", "species") and "expertise-choice" not in c["id"]
                and ("prof-choice-" in c["id"] or "proficiency-choice" in c["id"])
                and not c.get("profOrExpertise") and not class_choices_2024.is_positioned_proficiency_card(c)
                and any(o["id"].startswith("skill-") for o in c["options"]))

    cards = sorted((c for c in choices if eligible(c)),
                   key=lambda c: (class_choices_2024.proficiency_position(c, class_order) or last, c["id"]))
    pruned: list[dict] = []
    held: set[str] = set()
    for card in cards:
        i = next(n for n, c in enumerate(choices) if c["id"] == card["id"])
        c = choices[i]
        dup = [s for s in c["selected"] if s in held]
        options = [o if o.get("disabled") or o["id"] not in held
                   else {**o, "disabled": True, "disabledReason": msg("disabled-already-proficient")} for o in c["options"]]
        kept = [s for s in c["selected"] if s not in held]
        if dup:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            pruned.append({"choiceId": c["id"], "reason": msg(
                "pruned-proficient", label=c["label"], names=[labels.get(d, d) for d in dup])})
        choices[i] = {**c, "options": options, "selected": kept, "status": "resolved" if len(kept) == c["count"] else "pending"}
        held.update(s for s in kept if s.startswith("skill-"))
    return pruned


def _gate_positioned_proficiencies(choices: list[dict], catalog: Catalog, resolved_classes: list[dict],
                                   resolved_feats: list[dict], bg: dict | None, race: dict | None,
                                   subrace: dict | None, xphb_effects, class_order: list[str]) -> list[dict]:
    """C6b-2 + F3a-4, generalised by RP12 into "positioned proficiency picks": Primal Knowledge and the subclass skill
    / tool picks (Lore, Student of War, Otherworldly Glamour). They are walked in (class order, class level) order.
    Each pick sees everything gained at or before its position (fixed grants, other cards, ASI feats, earlier
    positioned picks): such options are disabled "already proficient" and a stored duplicate is dropped with a
    `pruned` entry. The picks that come later then see its choice the same way
    (`class_choices_2024.gate_after_positioned_pick`). A grant that comes later never converts a pick. Mutates
    `choices`; returns the pruned entries."""
    cards = [c for c in choices if class_choices_2024.is_positioned_proficiency_card(c)]
    if not cards:
        return []
    last = (len(class_order) + 1, 0)
    grants = _proficiency_grants(choices, catalog, resolved_classes, resolved_feats, bg, race, subrace, xphb_effects, class_order)
    pruned: list[dict] = []
    held: set[str] = set()  # the (kept) picks of the positioned cards walked so far
    for card in sorted(cards, key=lambda c: (class_choices_2024.proficiency_position(c, class_order) or last, c["id"])):
        pos = class_choices_2024.proficiency_position(card, class_order) or last
        prior = {pid for at, pid in grants if at <= pos} | held
        for c in choices:
            if (c["source"]["kind"] not in ("class", "species", "background", "feat") or "expertise-choice" in c["id"]
                    or class_choices_2024.is_positioned_proficiency_card(c)):
                continue
            at = class_choices_2024.proficiency_position(c, class_order)
            if at is None or at > pos:
                continue
            is_prof_card = "prof-choice-" in c["id"] or "proficiency-choice" in c["id"]
            prior.update(s for s in c["selected"] if s.startswith("skill-") or is_prof_card)
        if class_choices_2024.is_primal_knowledge_card(card):
            pruned += class_choices_2024.gate_primal_knowledge(choices, prior)
            name = "Primal Knowledge"
        else:
            pruned += class_choices_2024.gate_positioned_card(choices, card["id"], prior)
            name = catalog.features[class_choices_2024.pick_spec_for_card(card)["feature"]]["name"]
        picked = set(next(c for c in choices if c["id"] == card["id"])["selected"])
        held |= picked
        if picked:
            pruned += class_choices_2024.gate_after_positioned_pick(choices, class_order, pos, picked, name)
    return pruned


def _save_grant_positions(catalog: Catalog, resolved_feats: list[dict], choices: list[dict], class_feature_list,
                          xphb_effects, ruleset: str, class_order: list[str], class_saves: list[str],
                          ) -> list[tuple[tuple[int, int], str]]:
    """RP12: every saving throw proficiency of the build as (position, ability): the first class's saves at (0, 1),
    origin / ASI feats and Resilient-style `save-choice` cards at their position, class features (Diamond Soul,
    Slippery Mind ...) at their feature record's level."""
    origin = (-1, 0)
    out = [((0, 1), ab) for ab in class_saves]
    for f in resolved_feats:
        out += [(_feat_build_position(f, class_order) or origin, ab) for ab in f.get("saving_throw_proficiencies", [])]
    for c in choices:
        if c["source"]["kind"] == "feat" and ":save-choice-" in c["id"]:
            pos = class_choices_2024.proficiency_position(c, class_order) or origin
            out += [(pos, a.upper()) for a in c["selected"]]
    for cls_id, lvl, idx in class_feature_list:
        if cls_id not in class_order:
            continue
        granted = features_mod.save_proficiencies(features_mod.active_effects([(cls_id, lvl, idx)]), [idx], ruleset)
        level = (catalog.features.get(idx) or {}).get("level") or lvl
        out += [((class_order.index(cls_id), level), ab) for ab in granted]
    for cls_id, _lvl, effect in xphb_effects:
        if cls_id in class_order and effect.get("save_proficiency"):
            level = (catalog.features.get(effect.get("feature_id")) or {}).get("level") or 1
            grant = effect["save_proficiency"]
            out += [((class_order.index(cls_id), level), ab) for ab in (ABILITIES if grant == "all" else grant)]
    return out


def _gate_save_picks(choices: list[dict], catalog: Catalog, resolved_classes: list[dict], resolved_feats: list[dict],
                     class_feature_list, xphb_effects, ruleset: str, class_saves: list[str],
                     proficient_save_abilities: list[str]) -> list[dict]:
    """RP12 Gloom Stalker 7 Iron Mind: "You gain proficiency in Wisdom saving throws. If you already have this
    proficiency, you instead gain proficiency in Intelligence or Charisma saving throws (your choice)." "Already" =
    gained at or before the card's position (class order, class level). Without it the card is removed and Wisdom is
    added outright (a stored pick is reported); with it the card stays, the saves already held are disabled and the
    pick is added to `proficient_save_abilities` (mutated). Returns the pruned entries."""
    cards = [c for c in choices if class_choices_2024.is_save_pick_card(c)]
    if not cards:
        return []
    class_order = [rc["cls_id"] for rc in resolved_classes if rc["cls"]]
    grants = _save_grant_positions(catalog, resolved_feats, choices, class_feature_list, xphb_effects, ruleset,
                                   class_order, class_saves)
    pruned: list[dict] = []
    for card in cards:
        spec = class_choices_2024.pick_spec_for_card(card)
        pos = class_choices_2024.proficiency_position(card, class_order)
        prior = {ab for at, ab in grants if at <= pos}
        if spec["fixed"] not in prior:
            choices[:] = [c for c in choices if c["id"] != card["id"]]
            if card["selected"]:
                pruned.append({"choiceId": card["id"], "reason": msg("pruned-iron-mind", label=card["label"])})
            if spec["fixed"] not in proficient_save_abilities:
                proficient_save_abilities.append(spec["fixed"])
            continue
        pruned += class_choices_2024.gate_positioned_card(choices, card["id"], {ab.lower() for ab in prior})
        for sel in next(c for c in choices if c["id"] == card["id"])["selected"]:
            if sel.upper() not in proficient_save_abilities:
                proficient_save_abilities.append(sel.upper())
    return pruned


def _gate_expertise_choices(
    choices: list[dict], proficient_skills: set[str], fixed_expertise=(), class_order: list[str] = (),
    ruleset: str = "mixed", poe_priors: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Restrict every feat- or class-sourced Expertise Choice to skills (and,
    for the Rogue, tools) the character is proficient in. Mutates `choices` in place (entries replaced by index);
    returns non-blocking pruned entries for selections that were dropped.

    C6b-1: a card flagged `lacksExpertise` (2024 Deft Explorer, Ranger 9: "with which you lack
    Expertise") also disables, and drops stored picks of, skills that already have Expertise from
    an earlier source. The walk order is fixed Expertise from feats (`fixed_expertise`), origin
    feat cards, then class cards and ASI feat cards by (position in `class_order`, class level;
    F3a-3: an ASI feat card sits at its ASI level, after the class feature of the same level); the
    later pick is the duplicate. Decision E1 (revised 2026-10-11): under ruleset 2024 every
    Expertise card behaves as flagged (Bard, Rogue, Scholar, feat cards too); outside 2024 only
    flagged cards do (none in practice), an unflagged duplicate is simply wasted."""
    pruned_by_index: dict[int, dict] = {}  # reported in `choices` order, whatever the walk order
    poe_priors = poe_priors or {}
    indexes = [i for i, c in enumerate(choices) if _is_expertise_choice(c) or c["id"] in poe_priors]

    def walk_key(i: int):
        c = choices[i]
        if c["source"]["kind"] == "feat":
            m = _ASI_FEAT_CID_RE.match(c["id"])
            if not m:
                return (0, 0, 0, 0, i)  # origin feats come first
            cls_id = m.group(1)
            return (1, class_order.index(cls_id) if cls_id in class_order else len(class_order), int(m.group(2)), 1, i)
        cls_id = c["source"].get("id")
        return (1, class_order.index(cls_id) if cls_id in class_order else len(class_order), c["source"].get("level") or 0, 0, i)

    have: set[str] = set(fixed_expertise)
    for i in sorted(indexes, key=walk_key):
        c = choices[i]
        if c["id"] in poe_priors:
            # FE6: a proficiency-or-Expertise card. Any skill may be picked (an unproficient one just becomes a
            # proficiency); a pick already proficient at the card's position is Expertise, and under 2024 (E1
            # revised) may not repeat an Expertise skill.
            prior = poe_priors[c["id"]]
            options = [o if o.get("disabled") or not (ruleset == "2024" and o["id"] in prior and o["id"] in have)
                       else {**o, "disabled": True, "disabledReason": msg("disabled-has-expertise")} for o in c["options"]]
            kept = [s for s in c.get("selected", []) if not (ruleset == "2024" and s in prior and s in have)]
            dropped = [s for s in c.get("selected", []) if s not in kept]
            if dropped:
                labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
                names = [labels.get(d, d) for d in dropped]
                pruned_by_index[i] = {"choiceId": c["id"],
                                      "reason": msg("pruned-expertise-already", label=c["label"], names=names)}
            choices[i] = {**c, "options": options, "selected": kept,
                          "status": "resolved" if len(kept) == c["count"] else "pending"}
            have.update(s for s in kept if s in prior)
            continue
        # User decision 2026-10-11: under 2024 EVERY Expertise card forbids a skill that already has Expertise
        # (stricter than RAW on purpose: a pick is never wasted). mixed / 2014 keep the flag-only behavior.
        lacks = ruleset == "2024" or bool(c.get("lacksExpertise"))
        options = []
        for o in c["options"]:
            if o.get("disabled"):
                options.append(o)
            elif o["id"] not in proficient_skills:
                options.append({**o, "disabled": True, "disabledReason": msg("disabled-not-proficient")})
            elif lacks and o["id"] in have:
                options.append({**o, "disabled": True, "disabledReason": msg("disabled-has-expertise")})
            else:
                options.append(o)
        enabled = {o["id"] for o in options if not o.get("disabled")}
        selected = c.get("selected", [])
        kept = [s for s in selected if s in enabled or (s in proficient_skills and not lacks)]
        dropped = [s for s in selected if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = [labels.get(d, d) for d in dropped]
            lost_profs = [d for d in dropped if d not in proficient_skills]
            if lost_profs:
                reason = msg("pruned-expertise-not-proficient", label=c["label"], names=names)
            else:
                reason = msg("pruned-expertise-already-chosen", label=c["label"], names=names)
            pruned_by_index[i] = {"choiceId": c["id"], "reason": reason}
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
        have.update(kept)
    return [pruned_by_index[i] for i in sorted(pruned_by_index)]


def _invocation_unmet(inv: dict, warlock_level: int, pacts: set[str], cantrips: set[str]) -> str | None:
    """Why an Eldritch Invocation's prerequisites are not met, or None."""
    for req in inv.get("prerequisites") or []:
        kind = req.get("type")
        if kind == "level" and warlock_level < req.get("level", 0):
            return msg("disabled-requires-warlock-level", level=req["level"])
        if kind == "feature" and req.get("feature", "").rsplit("/", 1)[-1] not in pacts:
            return msg("disabled-requires", name=req["feature"].rsplit("/", 1)[-1].replace("-", " ").title().replace(" Of ", " of ").replace(" The ", " the "))
        if kind == "spell" and req.get("spell", "").rsplit("/", 1)[-1] not in cantrips:
            return msg("disabled-requires-cantrip", spell=req["spell"].rsplit("/", 1)[-1].replace("-", " "))
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
        if class_choices_2024.is_invocation_card_2024(c):  # C7a: prerequisites incl. Pacts inside the card
            cantrips = [sel for o in choices if o["id"] == f"class:{cls_id}:spells-cantrips" for sel in o["selected"]]
            choices[i], more = class_choices_2024.gate_invocations(
                catalog, c, level, cantrips, class_choices_2024.tome_picks(choices)["cantrips"],  # C7c: Tome cantrips count
                class_choices_2024.feat_tome_picks(choices)["cantrips"])  # RP20: so do those of a Tome held through Eldritch Adept
            pruned += more
            continue
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
                "reason": msg("pruned-invocation-prereq", label=c["label"], names=dropped),
            })
        choices[i] = {**c, "options": options, "selected": selected,
                      "status": "resolved" if len(selected) == c["count"] else "pending"}
    return pruned


def _gate_feat_invocation_prereqs(choices: list[dict], resolved_classes: list[dict], catalog: Catalog) -> list[dict]:
    """FE9 Eldritch Adept: "If the invocation has a prerequisite of any kind, you can choose that invocation only if
    you're a warlock who meets the prerequisite." The `:invocation` feat card's options are disabled with the
    warlock prerequisite reason (a non-Warlock has level 0, no Pact and no cantrips, so every invocation with a
    prerequisite is closed) and a stored pick of one is dropped with a `pruned` entry. Pacts of a 2024 Warlock
    (invocations) count as the matching 2014 Pact. Mutates `choices`; returns the pruned entries."""
    cards = [i for i, c in enumerate(choices) if c["source"]["kind"] == "feat" and c["id"].endswith(":invocation")]
    if not cards:
        return []
    level = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == "warlock" and rc["cls"]), 0)
    pacts = {sel for o in choices if o["source"].get("id") == "warlock" and ":feature:" in o["id"] for sel in o["selected"]}
    for o in choices:
        if class_choices_2024.is_invocation_card_2024(o):
            pacts |= {m.group(0)[len("opt-"):-len("-xphb")] for sel in o["selected"]
                      if (m := re.match(r"^opt-pact-of-the-(?:blade|chain|tome)-xphb", sel))}
    cantrips = {sel for o in choices if o["id"] == "class:warlock:spells-cantrips" for sel in o["selected"]}
    # RP20: the XPHB records carry `prerequisite_2024` (Warlock level, optional feature, damaging / attack cantrip);
    # the Warlock's own picks (Pacts included) and cantrips (+ Pact of the Tome cantrips) are what the feat's pick is
    # checked against, a non-Warlock has level 0 and none of them
    held_2024 = [sel for o in choices if class_choices_2024.is_invocation_card_2024(o) for sel in o["selected"]]
    cantrips_2024 = sorted(cantrips) + class_choices_2024.tome_picks(choices)["cantrips"]
    pruned = []
    for i in cards:
        c = choices[i]
        unmet, options = {}, []
        for o in c["options"]:
            if o.get("disabled"):
                reason = None
            elif o["id"].startswith("opt-") and o["id"].endswith("-xphb"):
                reason = class_choices_2024.invocation_unmet(catalog, o["id"], level, set(held_2024), cantrips_2024)
            else:
                reason = _invocation_unmet(catalog.features.get(o["id"]) or {}, level, pacts, cantrips)
            if reason:
                unmet[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": reason}
            options.append(o)
        kept = [s for s in c["selected"] if s not in unmet]
        if len(kept) != len(c["selected"]):
            pruned.append({"choiceId": c["id"], "reason": msg(
                "pruned-eldritch-adept-prereq", label=c["label"], names=[unmet[s] for s in c["selected"] if s in unmet])})
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
    return pruned


_PICK_PREFIX = re.compile(r"^(?:Fighting Style|Metamagic|Eldritch Invocation):\s*")
_FEAT_PICK_GROUPS = {":fighting-style": "style", ":maneuvers": "maneuver", ":metamagic": "metamagic", ":invocation": "invocation"}
_SRD_METAMAGIC_CID = re.compile(r"^class:sorcerer:\d+:feature:metamagic-\d+$")
_BATTLE_MASTER_CID = re.compile(r"^class:fighter:\d+:feature:battle-master-(?:phb|xphb)-3-battle-master$")


def _gate_duplicate_picks(choices: list[dict], catalog: Catalog, class_order: list[str],
                          srd_style_cids: set[str], fs_cids: set[str]) -> list[dict]:
    """FE9: one option cannot be held twice across the cards that offer the same family of options (Fighting Initiate's
    "the one you choose must be different", and the same logic for maneuvers, Metamagic and invocations, which a feat
    can learn on top of the class's own list). Families: fighting styles (SRD class cards, 2024 Fighting Style feat
    cards, Fighting Initiate), maneuvers (Battle Master, Martial Adept), Metamagic (Sorcerer SRD / 2024, Metamagic
    Adept), invocations (Warlock, Eldritch Adept). Cards are walked in build order (origin feats first, then by
    (class index, level), a class card before the ASI of its level) and the later holder is the duplicate: its option
    is disabled "already taken (<name>, <holder>)" and a stored duplicate is dropped with a `pruned` entry. Options are
    compared by name, so the 2014 and 2024 editions of one option are the same. Fighting Style feat cards (the feat is
    already resolved) and the 2024 invocation card only hold options. Mutates `choices`; returns the pruned entries."""
    def info(c):
        src, cid = c["source"], c["id"]
        if src["kind"] == "feat":
            for suffix, group in _FEAT_PICK_GROUPS.items():
                if cid.endswith(suffix):
                    return group, True, src["label"]
            return None
        if src["kind"] != "class":
            return None
        if cid in srd_style_cids:
            return "style", True, "SRD"
        if cid in fs_cids:
            return "style", False, None
        if _BATTLE_MASTER_CID.match(cid):
            return "maneuver", True, "Battle Master"
        if _SRD_METAMAGIC_CID.match(cid) or cid == class_choices_2024.metamagic_cid():
            return "metamagic", True, "Sorcerer"
        if ":invocations:" in cid and src.get("id") == "warlock":
            return "invocation", not class_choices_2024.is_invocation_card_2024(c), "Warlock"
        return None

    def position(i):
        c = choices[i]
        m = _ASI_FEAT_CID_RE.match(c["id"])
        slot = lambda cls: class_order.index(cls) if cls in class_order else len(class_order)  # noqa: E731
        if c["source"]["kind"] == "feat":
            return (1, slot(m.group(1)), int(m.group(2)), 1, i) if m else (0, 0, 0, 0, i)
        return (1, slot(c["source"].get("id")), c["source"].get("level") or 0, 0, i)

    def key_and_name(group, option_id, label):
        if group == "style":
            if option_id.startswith("feat:"):
                feat = catalog.feats.get(option_id[len("feat:"):])
                return (_feat_name_key(feat), feat["name"], feat.get("source")) if feat else (option_id, option_id, None)
            name = _PICK_PREFIX.sub("", (catalog.features.get(option_id) or {}).get("name") or label).strip()
            return name.lower(), name, None
        name = re.sub(r"\s*\([^)]*\)\s*$", "", _PICK_PREFIX.sub("", label)).strip()
        return name.lower(), name, None

    members = [(i, *found) for i, c in enumerate(choices) if (found := info(c))]
    feat_groups = {g for i, g, _m, _h in members if choices[i]["source"]["kind"] == "feat"}
    members = [m for m in members if m[1] in feat_groups]  # no feat pick, no change: class lists stay as they were
    if not members:
        return []
    held: dict[str, dict[str, str]] = {}  # options held by any card, read by the feat cards
    held_by_feat: dict[str, dict[str, str]] = {}  # options held by a feat card, read by the class cards
    pruned = []
    for i, group, modifiable, holder in sorted(members, key=lambda m: position(m[0])):
        c = choices[i]
        is_feat = c["source"]["kind"] == "feat"
        taken = (held if is_feat else held_by_feat).setdefault(group, {})
        labels = {o["id"]: o["label"] for o in c["options"]}
        picks = [(s, *key_and_name(group, s, labels.get(s, s))) for s in c["selected"]]  # (id, key, name, feat source)
        if modifiable:
            options = [{**o, "disabled": True, "disabledReason": msg("disabled-already-taken-from", where=taken[key])}
                       if (key := key_and_name(group, o["id"], o["label"])[0]) in taken and not o.get("disabled") else o
                       for o in c["options"]]
            dropped = [p for p in picks if p[1] in taken]
            picks = [p for p in picks if p[1] not in taken]
            if dropped:
                pruned.append({"choiceId": c["id"], "reason": msg(
                    "pruned-already-taken", label=c["label"], names=[p[2] for p in dropped], where=taken[dropped[0][1]])})
            if dropped or any(a is not b for a, b in zip(options, c["options"])):
                ids = [p[0] for p in picks]
                choices[i] = {**c, "options": options, "selected": ids,
                              "status": "resolved" if len(ids) == c["count"] else "pending"}
        for _id, key, name, feat_source in picks:
            label = f"{name}, {holder or feat_source or 'feat'}"
            held.setdefault(group, {}).setdefault(key, label)
            if is_feat:
                held_by_feat.setdefault(group, {}).setdefault(key, label)
    return pruned


def _subclass_spell_ids(catalog: Catalog, cls_id: str, subclass_id: str | None, class_level: int,
                        feature_ids: set[str], mode: str, variant: str | None = None, ruleset: str = "mixed") -> list[str]:
    """Spells from the subclass's `spells` list whose prerequisites (class
    level, and for Circle of the Land the chosen terrain feature) are met,
    for entries behaving as `mode` ("always" prepared / "expanded" list). An
    entry's own `mode` (imported subclasses, one of which can carry both)
    wins over `SUBCLASS_SPELL_MODE` (SRD records), default "always". RP17: `variant` (Circle of the Land's picked
    land) adds the entries of the record's `spells_by_variant[variant]`."""
    from catalog import reference_data
    if not subclass_id:
        return []
    subclass_mode = reference_data.SUBCLASS_SPELL_MODE.get(subclass_id, "always")
    out: list[str] = []
    sub_record = catalog.subclasses.get(subclass_id) or {}
    for entry in (sub_record.get("spells") or []) + ((sub_record.get("spells_by_variant") or {}).get(variant) or [] if variant else []):
        if (entry.get("mode") or subclass_mode) != mode:
            continue
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
    if mode == "always" and ruleset == "2024":  # RP18: the "prepared" innate entries (Great Old One Eldritch Hex)
        out += [sid for sid in subclass_innate_2024.prepared_spell_ids(catalog, sub_record, cls_id, class_level) if sid not in out]
    return out


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
    for src, src_id in ((race, race_id), (subrace, subrace.get("index") if subrace else None)):
        envelope = src.get("resist_options") if src else None
        if not envelope or (src is race and variant_decides_resistance):
            continue
        cid = f"species:{race_id}:resistance" if src is race else f"species:{race_id}:subspecies:{src_id}:resistance"
        source = {"kind": "species", "id": race_id, "label": race["name"]}
        tpl = build_choice_template(envelope, cid, source, msg("label-damage-resistance"), description=msg("desc-resist-type"))
        if tpl:
            templates.append(tpl)

    return templates


def _species_feat_pool(catalog: Catalog, category: str | None, sources, ruleset: str = "mixed", keep=()) -> list[dict]:
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
    flags it `hiddenByFilters`)."""
    allowed = {category} if category is not None else {"", "G", "O"}
    kept = {k[len("feat:"):] for k in keep if isinstance(k, str) and k.startswith("feat:")}
    pool = [
        f for f in catalog.feats.values()
        if (f.get("category") or "") in allowed and f["name"] != "Ability Score Improvement"
        and (_feat_offered(f, sources, ruleset) or f["index"] in kept)
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
    for feat, option in _feat_options(_species_feat_pool(catalog, grant["category"], sources, ruleset, keep), ruleset):
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
    count = grant["count"]
    noun = (msg("noun-origin-feat") if grant["category"] == "O"
            else msg("noun-dark-gift-feat") if grant["category"] == "DG" else msg("noun-feat"))
    return {
        "id": cid, "source": {"kind": kind, "id": race_id, "label": race["name"]},
        "label": msg("label-origin-feat") if grant["category"] == "O" else msg("label-feat"),
        "description": msg("desc-species-feat", noun=noun) if count == 1 else msg("desc-species-feats", count=count),
        "count": count, "options": options,
    }


def _resolve_species_selected_feats(template: dict, species_choices: dict, catalog: Catalog,
                                    problems: list[dict], background_grant: bool = False) -> list[dict]:
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
            # `disabledReason` is a Msg (a str subclass whose text is the English wording), so this plain text check
            # still works; do not rebuild it with `+` / f-strings or the tag is lost (tests/test_i18n_disabled.py)
            if str(option.get("disabledReason")).startswith("already taken"):
                problems.append({
                    "id": f"feat-duplicate-{feat['index']}-{template['id']}",
                    "message": msg("feat-duplicate-at-source", feat=feat["name"], source=template["source"]["label"]),
                })
            else:
                problems.append({
                    "id": f"feat-prerequisite-unmet-{feat['index']}",
                    "message": msg("feat-prerequisite-unmet-pick", feat=feat["name"], source=template["source"]["label"]),
                })
            continue
        picked.append(feat)
    # W4: a background feat grant reuses this machinery; `_background_grant` only changes the sheet's `origin`.
    return [
        {**feat, "_species_origin": f"{template['id']}:feat:{feat['index']}",
         **({"_background_grant": True} if background_grant else {})} for feat in picked[: template["count"]]
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
                "message": msg("multiclass-prerequisite-unmet", cls=cls["name"]),
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
_ASI_GATE_PREREQUISITE_KEYS = {
    "level", "ability", "feat", "spellcasting2020", "feature", "proficiency", "featCategory",
    "race", "spellcasting", "spellcastingFeature",
}


def _race_name_key(name: str) -> str:
    """Lowercased, trailing " (...)" stripped: "Vampire (Ixalan)" -> "vampire"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", name).strip().lower()


def _held_race_state(race: dict | None, subrace: dict | None, size: str | None) -> tuple[set[str], set[str], str | None]:
    race_names = {_race_name_key(race["name"])} if race and race.get("name") else set()
    subrace_names: set[str] = set()
    if subrace:
        if subrace.get("name"):
            subrace_names.add(subrace["name"].strip().lower())
        subrace_names.update(t for t in (subrace.get("index") or "").lower().split("-") if t)
    return race_names, subrace_names, size

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


_SPELLCASTING_PREREQUISITE_FEATURES = ("Spellcasting", "Pact Magic")
_KNOWN_PREREQUISITE_FEATURES = _SPELLCASTING_PREREQUISITE_FEATURES + ("Fighting Style",)


def _feature_prerequisite_met(features, held: "_HeldFeatState") -> bool:
    """A 5etools `feature` prerequisite (a list of feature names, any one will do):
    Spellcasting / Pact Magic = the character has a spellcasting feature, Fighting
    Style = the character has a Fighting Style feature (C3)."""
    return any(
        held.fighting_style if name == "Fighting Style" else held.has_spellcasting_feature
        for name in features
    )


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
    if key in ("spellcasting2020", "spellcasting", "spellcastingFeature"):
        return isinstance(value, bool)
    if key == "race":
        return isinstance(value, list) and bool(value) and all(
            isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"] for e in value
        )
    if key == "feature":
        return (
            isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and v in _KNOWN_PREREQUISITE_FEATURES for v in value)
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
    featCategory/exclusiveFeatCategory, other, otherSummary; the ASI gate
    passes _ASI_GATE_PREREQUISITE_KEYS, which since A4 also covers race,
    spellcasting and spellcastingFeature).

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


def _race_entry_met(entry: dict, held: "_HeldFeatState") -> bool:
    name = _race_name_key(entry["name"])
    if name == "small race":
        return held.size == "Small"
    if name not in held.race_names:
        return False
    subrace = entry.get("subrace")
    return not subrace or (isinstance(subrace, str) and _race_name_key(subrace) in held.subrace_names)


def _race_entry_phrase(entry: dict):
    if entry.get("displayEntry") and isinstance(entry["displayEntry"], str):
        return entry["displayEntry"]
    name = entry["name"].title()
    subrace = entry.get("subrace")
    if isinstance(subrace, str) and subrace:
        name = f"{subrace.title()} {name}"
    return msg("prereq-race", name=name)


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
    if alt.get("spellcasting2020") and not held.has_spellcasting_feature:
        return False
    if "feature" in alt and not _feature_prerequisite_met(alt["feature"], held):
        return False
    if alt.get("spellcastingFeature") and not held.has_spellcasting_feature:
        return False
    if alt.get("spellcasting") and not held.can_cast_spell:
        return False
    if "race" in alt and not any(_race_entry_met(e, held) for e in alt["race"]):
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
    applied_fixed_deltas_by_instance: dict[str, list[tuple[str, int]]] | None = None,
) -> list[dict]:
    """FE2: `applied_fixed_deltas_by_instance` (keyed by _feat_instance_key) says what a feat's FIXED increase
    really added to `final_scores`: clamped for an origin feat at its cap (B2), nothing for an ASI feat skipped
    at its cap. When an instance is listed, that is subtracted instead of the raw `ability_bonuses`, so a
    delta that never landed is not subtracted (the false positive the ASI-or-feat review found). Chosen deltas
    (`chosen_ability_deltas_by_instance`) are now the applied ones too.

    Structural precedent: _multiclass_prerequisite_problems above — same
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
        applied_fixed = (applied_fixed_deltas_by_instance or {}).get(_feat_instance_key(feat))
        if applied_fixed is not None:
            fixed_deltas = applied_fixed
        else:
            fixed_deltas = [(e["ability_score"]["index"].upper(), e["bonus"]) for e in feat.get("ability_bonuses", [])]
        for ab, delta in fixed_deltas:
            scores_without_own_bonus[ab] = scores_without_own_bonus.get(ab, 0) - delta
        # Task 4: subtract THIS feat's own CHOSEN ability-bonus delta back
        # out too, same discipline, keyed by this feat's own instance.
        for ab_key, delta in chosen_ability_deltas_by_instance.get(_feat_instance_key(feat), []):
            scores_without_own_bonus[ab_key] = scores_without_own_bonus.get(ab_key, 0) - delta
        if not any(_feat_prerequisite_alt_met(alt, total_level, scores_without_own_bonus) for alt in prereq):
            problems.append({
                "id": f"feat-prerequisite-unmet-{feat['index']}",
                "message": msg("feat-prerequisite-unmet", feat=feat["name"]),
            })
    return problems


def _asi_option_label(deltas: list[tuple[str, int]]) -> str:
    return " and ".join(f"{ab} +{delta}" for ab, delta in deltas)


# Feat categories offered at an ASI level, by ruleset (5etools codes: ""
# = the category-less 2014 books, G General, O Origin, EB Epic Boon).
# "2014" -> 2014 books + General (after ruleset_allows that is the Unearthed
# Arcana G feats); "2024" -> General + Origin; "mixed"/unknown -> all three.
# Epic Boons are added separately, only at slot level 19 and never under
# 2014. Fighting Style, Dragonmark and Dragon-gift categories stay out.
_ASI_FEAT_CATEGORIES = {"2014": {"", "G"}, "2024": {"G", "O"}}
_ASI_FEAT_CATEGORIES_DEFAULT = {"", "G", "O"}
_ASI_EPIC_BOON_LEVEL = 19
_ASI_CID_RE = re.compile(r"^class:[^:]+:\d+:asi$")
_ASI_EXCLUDED_FEAT_INDICES = {"ability-score-improvement-xphb"}
# F1: only plain FS feats are ASI-eligible. Blessed Warrior (FS:P) and Druidic Warrior
# (FS:R) require the level-2 Paladin / Ranger Fighting Style feature itself, so they come
# only from the Paladin / Ranger fighting-style cards.
_FIGHTING_STYLE_CATEGORIES = {"FS"}
_FS_FEAT_CATEGORIES = {"FS", "FS:P", "FS:R"}  # every Fighting Style feat category (cards, effects)


def _is_asi_eligible_feat(feat: dict, ruleset: str = "mixed", slot_level: int = 4, fighting_style: bool = False) -> bool:
    """Whether `feat` may be taken in place of an Ability Score Improvement
    at class level `slot_level` under `ruleset` (structural eligibility; the
    draft.sources / ruleset-visibility filter is _feat_offered, prerequisites
    are checked separately). The literal "Ability Score Improvement" entry is
    excluded because it duplicates this app's own ASI-combo mechanic. Shared
    by _asi_feat_pool (which options to offer) and _resolve_asi_selected_feats
    (which selections to honor) so the two can't drift apart.

    C3 (U3): the Fighting Style feats (FS only, F1) are eligible under 2024 and
    mixed when the character has a Fighting Style feature (`fighting_style`), never
    under 2014. The 2014 chassis keeps its SRD fighting-style subfeatures instead."""
    if feat["index"] in _ASI_EXCLUDED_FEAT_INDICES or feat["name"] == "Ability Score Improvement":
        return False
    category = feat.get("category") or ""
    if category in _FIGHTING_STYLE_CATEGORIES:
        return fighting_style and ruleset != "2014"
    if category == "EB":
        return ruleset != "2014" and slot_level >= _ASI_EPIC_BOON_LEVEL
    return category in _ASI_FEAT_CATEGORIES.get(ruleset, _ASI_FEAT_CATEGORIES_DEFAULT)


_FEAT_GROUP_BY_CATEGORY = {"EB": "epic-boon", "G": "general", "O": "origin", "": "feat-2014"}


def _feat_group(feat: dict) -> str:
    return _FEAT_GROUP_BY_CATEGORY.get(feat.get("category") or "", "general")


def _feat_group_order(ruleset: str) -> list[str]:
    """Display order of feat groups: 2014 shows its own books first, the
    other rulesets lead with the newest content."""
    if ruleset == "2014":
        return ["feat-2014", "general"]
    return ["epic-boon", "general", "origin", "feat-2014"]


def _feat_options(feats: list[dict], ruleset: str) -> list[tuple[dict, dict]]:
    """[(feat, option)] for a picker: grouped (`group`), ordered by group
    then (name, source), labelled "Name (SOURCE)" only when the name occurs
    twice in `feats`. Disabled state is added by the caller; options keep
    their position either way."""
    order = _feat_group_order(ruleset)
    rank = {g: i for i, g in enumerate(order)}
    ordered = sorted(feats, key=lambda f: (rank.get(_feat_group(f), len(rank)), f["name"], f.get("source") or ""))
    counts: dict[str, int] = {}
    for f in ordered:
        counts[f["name"]] = counts.get(f["name"], 0) + 1
    out = []
    for f in ordered:
        label = f["name"] if counts[f["name"]] == 1 else f"{f['name']} ({f.get('source') or '?'})"
        out.append((f, {"id": f"feat:{f['index']}", "label": label, "group": _feat_group(f)}))
    return out


def _asi_feat_in_pool(feat: dict, sources, ruleset: str, slot_level: int, fighting_style: bool = False) -> bool:
    return _is_asi_eligible_feat(feat, ruleset, slot_level, fighting_style) and _feat_offered(feat, sources, ruleset)


def _asi_pick_honored(feat: dict, sources, ruleset: str, slot_level: int, fighting_style: bool = False) -> bool:
    """Whether a stored feat pick at an ASI slot is applied: it is in the
    filtered pool, OR it is structurally eligible at that slot under the
    permissive "mixed" rules (so switching ruleset/sources never silently
    drops an already-chosen feat; the pick is kept and warned about, F2).
    Used by both the option template and the resolver."""
    return (_asi_feat_in_pool(feat, sources, ruleset, slot_level, fighting_style)
            or _is_asi_eligible_feat(feat, "mixed", slot_level, fighting_style))


def _asi_feat_pool(
    catalog: Catalog, sources, ruleset: str, slot_level: int, keep_index: str | None = None, fighting_style: bool = False,
) -> list[dict]:
    """The feats offered at an ASI slot: structurally eligible AND allowed by
    draft.sources / the ruleset. `keep_index` (the already-selected feat) is
    appended, as a COPY tagged `_hidden_by_filters`, when it is honored
    (_asi_pick_honored) but not in the pool."""
    pool = [f for f in catalog.feats.values() if _asi_feat_in_pool(f, sources, ruleset, slot_level, fighting_style)]
    kept = catalog.feats.get(keep_index) if keep_index else None
    if kept and all(f['index'] != kept['index'] for f in pool) and _asi_pick_honored(kept, sources, ruleset, slot_level, fighting_style):
        pool.append({**kept, "_hidden_by_filters": True})
    return pool


def _stored_asi_feat_pick(class_choices: dict | None, cid: str) -> str | None:
    """The single stored `feat:<index>` pick at an ASI cid, deduped exactly
    like _apply_asi_progression and _resolve_asi_selected_feats read it."""
    raw = (class_choices or {}).get(cid) or []
    if not isinstance(raw, list):
        return None
    selected = list(dict.fromkeys(s for s in raw if isinstance(s, str)))
    if len(selected) == 1 and selected[0].startswith("feat:"):
        return selected[0][len("feat:"):]
    return None


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
    if len(prereq) == 1:
        parts = _feat_prerequisite_failing_parts(prereq[0], total_level, scores, held, catalog)
        if parts:
            return msg("disabled-prereq-unmet-requires", parts=parts)
    return msg("disabled-prereq-unmet")


def _armor_category_msg(value):
    """The armor category word of an armor proficiency prerequisite ("light" / "medium" / "heavy") as a nested message."""
    if value == "light":
        return msg("armor-category-light")
    if value == "medium":
        return msg("armor-category-medium")
    return msg("armor-category-heavy")


def _feat_prerequisite_failing_parts(
    alt: dict, total_level: int, scores: dict[str, int], held: "_HeldFeatState | None", catalog: Catalog | None,
) -> list[str]:
    parts: list = []
    level_req = alt.get("level")
    if isinstance(level_req, int) and total_level < level_req:
        parts.append(msg("prereq-level", level=level_req))
    ability_req = alt.get("ability")
    if ability_req and not _feat_prerequisite_alt_met({"ability": ability_req}, total_level, scores, held):
        parts.append(msg("prereq-any-of", items=[
            f"{ab.upper()} {minimum}"
            for entry in ability_req if isinstance(entry, dict) for ab, minimum in entry.items()
        ]))
    if alt.get("spellcasting2020") and not (held and held.has_spellcasting_feature):
        parts.append(msg("prereq-spellcasting-or-pact"))
    if "feature" in alt and not (held and _feature_prerequisite_met(alt["feature"], held)):
        parts.append(
            msg("prereq-fighting-style") if alt["feature"] == ["Fighting Style"] else msg("prereq-spellcasting-or-pact")
        )
    if alt.get("spellcastingFeature") and not (held and held.has_spellcasting_feature):
        parts.append(msg("prereq-spellcasting"))
    if alt.get("spellcasting") and not (held and held.can_cast_spell):
        parts.append(msg("prereq-cast-spell"))
    if "race" in alt and not (held and any(_race_entry_met(e, held) for e in alt["race"])):
        parts.append(msg("prereq-any-of", items=[_race_entry_phrase(e) for e in alt["race"]]))
    if "featCategory" in alt and not any(c in (held.feat_categories if held else ()) for c in alt["featCategory"]):
        parts.append(msg("prereq-dragonmark") if alt["featCategory"] == ["D"] else msg("prereq-feat-category"))
    for entry in alt.get("proficiency", []):
        satisfiers = _PROFICIENCY_PREREQ_SATISFIERS[_proficiency_entry_key(entry)]
        if not (held and held.proficiency_ids & satisfiers):
            kind, value = _proficiency_entry_key(entry)
            if kind == "weaponGroup":
                parts.append(msg("prereq-martial"))
            elif value == "shield":
                parts.append(msg("prereq-shield"))
            else:
                parts.append(msg("prereq-armor-proficiency", category=_armor_category_msg(value)))
    if "feat" in alt and not _feat_prerequisite_alt_met({"feat": alt["feat"]}, total_level, scores, held):
        names = []
        for ref in alt["feat"]:
            record = (catalog.feats.get(_feat_ref_index(ref)) if catalog else None)
            names.append(msg("prereq-feat", name=record["name"] if record else ref.partition("|")[0].title()))
        parts.append(msg("prereq-any-of", items=names))
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
    taken_by_level: dict[int, dict[str, str]] | None = None,
    held_by_level: dict[int, "_HeldFeatState"] | None = None,
    ruleset: str = "mixed", class_choices: dict | None = None,
) -> list[dict]:
    # `class_choices`: this class's stored selections; an already-picked feat
    # stays offered (flagged `hiddenByFilters`) when ruleset/sources hide it.
    # `taken_by_level`: per ASI level, the feat indices already held from a
    # background grant or an earlier ASI pick — offered disabled unless the
    # feat is `repeatable`.
    # `sources` is draft.sources: feat options are filtered exactly like a
    # race/background record (see _feat_source_allowed). SRD-only drafts
    # therefore get zero feat options — the 2014 SRD has no feats.
    pools: dict[tuple[bool, bool], list[dict]] = {}
    templates = []
    for lvl in asi_levels:
        cid = f"class:{cls_id}:{lvl}:asi"
        epic = lvl >= _ASI_EPIC_BOON_LEVEL
        fighting_style = bool((held_by_level or {}).get(lvl) and held_by_level[lvl].fighting_style)  # C3
        if (epic, fighting_style) not in pools:
            pools[(epic, fighting_style)] = _asi_feat_pool(catalog, sources, ruleset, lvl, fighting_style=fighting_style)
        general_feats = pools[(epic, fighting_style)]
        keep_index = _stored_asi_feat_pick(class_choices, cid)
        if keep_index and not any(f["index"] == keep_index for f in general_feats):
            kept_pool = _asi_feat_pool(catalog, sources, ruleset, lvl, keep_index, fighting_style)
            general_feats = general_feats + [f for f in kept_pool if f.get("_hidden_by_filters")]
        current_scores = scores_by_level.get(lvl, {})
        options = []
        for option_id, deltas in asi_mod.asi_combinations():
            option = {"id": option_id, "label": _asi_option_label(deltas), "group": "asi"}
            if asi_mod.asi_exceeds_cap(deltas, current_scores):
                option["disabled"] = True
                option["disabledReason"] = msg("disabled-ability-cap-20")
            options.append(option)
        for feat, option in _feat_options(general_feats, ruleset):
            if feat.get("_hidden_by_filters"):
                option["hiddenByFilters"] = True
            reason = _feat_prerequisite_unmet_reason(
                feat, total_level, current_scores, use_prerequisites,
                (held_by_level or {}).get(lvl) or _HeldFeatState(), catalog,
            )
            if reason:
                option["disabled"] = True
                option["disabledReason"] = reason
            elif _taken_reason(feat, (taken_by_level or {}).get(lvl)):
                option["disabled"] = True
                option["disabledReason"] = _taken_reason(feat, (taken_by_level or {}).get(lvl))
            options.append(option)
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": msg("label-asi"),
            "description": msg("desc-asi"),
            "count": 1,
            "options": options,
        })
    return templates


# C3: 2024 Fighting Style as a feat choice. XPHB Fighter (level 1), Paladin and
# Ranger (level 2) "gain a Fighting Style feat of your choice"; the XPHB Champion's
# "Additional Fighting Style" (level 7) grants another one. Under ruleset 2024 only
# (mixed and 2014 keep the SRD fighting-style subfeatures, U9) these features'
# cards are feat cards: cid `class:<cls>:<lvl>:fighting-style`, options
# `feat:<index>` from `_feat_options`, prerequisite / duplicate states as for ASI
# feats. The picked feat is tagged like an ASI feat (`_asi_origin`, `_asi_level`) plus
# `_fs_cid`, so cid prefixes, instance keys, cascaded choices and sheet.feats work.
_FS_FEATURE_INDICES = frozenset({
    "fighter-fighting-style", "paladin-fighting-style", "ranger-fighting-style",
    "additional-fighting-style", "champion-xphb-7-additional-fighting-style",
})
_FS_CLASS_CATEGORIES = {"fighter": ("FS",), "paladin": ("FS", "FS:P"), "ranger": ("FS", "FS:R")}


def _class_has_fighting_style(catalog: Catalog, rc: dict) -> bool:
    """Whether the class (and subclass) feature list up to the class level has a
    feature named "Fighting Style" (the 5etools `Fighting Style` prerequisite)."""
    for _lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        sub = feature.get("subclass")
        if sub and sub.get("index") != rc["subclass_id"]:
            continue
        if feature.get("name") == "Fighting Style":
            return True
    return False


def _fighting_style_pool(catalog: Catalog, cls_id: str, sources, ruleset: str) -> list[dict]:
    cats = _FS_CLASS_CATEGORIES.get(cls_id, ())
    return [f for f in catalog.feats.values() if f.get("category") in cats and _feat_offered(f, sources, ruleset)]


def _fighting_style_slots(catalog: Catalog, rc: dict, sources, ruleset: str) -> list[tuple[str, int, str]]:
    """[(cid, class level, feature index)] of the class's fighting-style feat cards,
    by level. Empty outside ruleset 2024, for other classes, and when the catalog
    offers no Fighting Style feat (SRD-only data, sources without XPHB): the SRD
    subfeature card stays then."""
    if ruleset != "2024" or rc["cls_id"] not in _FS_CLASS_CATEGORIES or not rc["cls"]:
        return []
    if not _fighting_style_pool(catalog, rc["cls_id"], sources, ruleset):
        return []
    slots: dict[str, tuple[str, int, str]] = {}
    for lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
        if ref["index"] not in _FS_FEATURE_INDICES:
            continue
        feature = catalog.features.get(ref["index"])
        sub = (feature or {}).get("subclass")
        if not feature or (sub and sub.get("index") != rc["subclass_id"]):
            continue
        cid = f"class:{rc['cls_id']}:{lvl}:fighting-style"
        slots.setdefault(cid, (cid, lvl, ref["index"]))
    return sorted(slots.values(), key=lambda slot: slot[1])


def _srd_fighting_style_slots(catalog: Catalog, rc: dict, replaced: set[str]) -> list[tuple[str, int, str]]:
    """G1: [(cid, class level, feature index)] of the SRD "Fighting Style" /
    "Additional Fighting Style" subfeature cards the class has (the ones not replaced by
    a 2024 feat card). Their picks take part in the fighting-style duplicate check."""
    slots = []
    for lvl, ref in _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"]):
        feature = catalog.features.get(ref["index"])
        if not feature or ref["index"] in replaced:
            continue
        sub = feature.get("subclass")
        if sub and sub.get("index") != rc["subclass_id"]:
            continue
        if feature.get("name") in ("Fighting Style", "Additional Fighting Style") \
                and (feature.get("feature_specific") or {}).get("subfeature_options"):
            slots.append((f"class:{rc['cls_id']}:{lvl}:feature:{feature['index']}", lvl, feature["index"]))
    return slots


def _srd_style_options(catalog: Catalog, feature_index: str) -> dict[str, str]:
    """{option feature id: name key} of an SRD fighting-style card ("Fighting Style:
    Dueling" -> "dueling", the key `_feat_name_key` gives the feat "Dueling")."""
    opts = ((catalog.features[feature_index].get("feature_specific") or {})
            .get("subfeature_options", {}).get("from", {}).get("options", []))
    out = {}
    for o in opts:
        item = (o.get("item") or {}).get("index")
        feat = catalog.features.get(item or "")
        if feat:
            out[item] = re.sub(r"^Fighting Style:\s*", "", feat["name"]).strip().lower()
    return out


class _FightingStyleResolver:
    """The feats picked at the fighting-style cards (see above), resolved in ONE order
    with the ASI picks (F1): by (class index, class level), a card before the ASI of the
    same level. `__call__(rc, upto_level_or_None, seen)` is the `before_level` hook of
    `_resolve_asi_selected_feats`: it resolves the not-yet-done cards of `rc` whose level
    is <= `upto_level` (all of them for None) against `seen` (background, species and
    every pick at an earlier position, whatever its kind), so the LATER pick is the
    duplicate. `taken_by_cid[cid]` = `seen` before that card, the map its options read
    for the "already taken" state. A duplicate is skipped and appended to
    `skipped_duplicates`. Any FS-category feat of the class is honored (a pick hidden by
    sources/ruleset stays, like an ASI pick); anything else is ignored and lands in
    `pruned` through the generic stale-selection pass."""

    def __init__(self, slots_by_class: dict[int, list[tuple[str, int, str]]], catalog: Catalog,
                 skipped_duplicates: list[dict], srd_slots_by_class: dict[int, list[tuple[str, int, str]]] | None = None,
                 skipped_srd: list[dict] | None = None):
        self.slots_by_class = slots_by_class
        self.srd_slots_by_class = srd_slots_by_class or {}
        self.skipped_srd = skipped_srd if skipped_srd is not None else []
        self.catalog = catalog
        self.skipped_duplicates = skipped_duplicates
        self.picks: list[dict] = []
        self.taken_by_cid: dict[str, dict[str, str]] = {}
        self._done: set[str] = set()

    def __call__(self, rc: dict, upto_level: int | None, seen: dict[str, str]) -> None:
        cats = _FS_CLASS_CATEGORIES.get(rc["cls_id"], ())
        slots = sorted([(c, l, i, False) for c, l, i in self.slots_by_class.get(rc["index"], [])]
                       + [(c, l, i, True) for c, l, i in self.srd_slots_by_class.get(rc["index"], [])],
                       key=lambda t: t[1])
        for cid, lvl, _idx, is_srd in slots:
            if cid in self._done or (upto_level is not None and lvl > upto_level):
                continue
            self._done.add(cid)
            self.taken_by_cid[cid] = dict(seen)
            if is_srd:  # G1: an SRD style pick is held by its name key (first holder wins)
                raw = rc["class_choices"].get(cid)
                options = _srd_style_options(self.catalog, _idx)
                pick = next((x for x in (raw if isinstance(raw, list) else []) if isinstance(x, str) and x in options), None)
                if pick:
                    key = "name:" + options[pick]
                    if key in seen:
                        self.skipped_srd.append({"option": pick, "cid": cid, "level": lvl, "cls": rc["cls"],
                                                 "name": self.catalog.features[pick]["name"]})
                    else:
                        seen[key] = f"{options[pick].title()}, SRD"
                continue
            feat_index = _stored_asi_feat_pick(rc["class_choices"], cid)
            feat = self.catalog.feats.get(feat_index) if feat_index else None
            if not feat or feat.get("category") not in cats:
                continue
            if _taken_reason(feat, seen):
                self.skipped_duplicates.append({"feat": feat, "cid": cid, "level": lvl, "cls": rc["cls"]})
                continue
            _taken_add(seen, [feat])
            self.picks.append({**feat, "_fs_cid": cid, "_asi_level": lvl, "_asi_origin": f"{cid}:feat:{feat['index']}"})


def _fighting_style_templates(
    catalog: Catalog, rc: dict, slots: list[tuple[str, int, str]], sources, ruleset: str, total_level: int,
    scores: dict[str, int], use_prerequisites: bool, held: "_HeldFeatState", taken_by_cid: dict[str, dict[str, str]],
) -> list[dict]:
    """One feat card per fighting-style slot of the class (see above)."""
    cls_id = rc["cls_id"]
    cats = _FS_CLASS_CATEGORIES.get(cls_id, ())
    holder = held.copy()
    holder.fighting_style = True  # the character is gaining the feature right here
    templates = []
    for cid, lvl, feature_index in slots:
        feats = _fighting_style_pool(catalog, cls_id, sources, ruleset)
        keep_index = _stored_asi_feat_pick(rc["class_choices"], cid)
        kept = catalog.feats.get(keep_index) if keep_index else None
        if kept and kept.get("category") in cats and all(f["index"] != kept["index"] for f in feats):
            feats.append({**kept, "_hidden_by_filters": True})
        options = []
        for feat, option in _feat_options(feats, ruleset):
            option.pop("group", None)
            if feat.get("_hidden_by_filters"):
                option["hiddenByFilters"] = True
            reason = (
                _feat_prerequisite_unmet_reason(feat, total_level, scores, use_prerequisites, holder, catalog)
                or _taken_reason(feat, taken_by_cid.get(cid))
            )
            if reason:
                option["disabled"] = True
                option["disabledReason"] = reason
            options.append(option)
        feature = catalog.features[feature_index]
        text_feature = catalog.features.get(f"xphb-{cls_id}-{lvl}-fighting-style") or (
            feature if feature_index.startswith("champion-xphb") else {})
        templates.append({
            "id": cid, "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": lvl},
            "label": feature["name"],
            "description": _join_desc(text_feature.get("desc")) or msg("desc-fighting-style-feat"),
            "count": 1, "options": options,
        })
    return templates


# C7c (decision E7): Lessons of the First Ones. XPHB Warlock invocation "gain one Origin feat of your choice ... Each time
# you do so, choose a different Origin feat." Under ruleset 2024 every SELECTED instance (`<id>`, `<id>~2`, ...) has an
# Origin-feat card, cid `class:warlock:invocation:<instance>:feat`. The picked feat is tagged like an ASI feat
# (`_asi_origin` = `<card cid>:<feat index>`, `_asi_level` 2) plus `_inv_cid`, so cid prefixes, cascaded choices and
# sheet.feats work.
LESSONS_LEVEL = 2
_LESSONS_REASON = msg("disabled-already-chosen-lessons")


def _lessons_slots(catalog: Catalog, resolved_classes: list[dict], ruleset: str) -> dict[int, list[tuple[str, str]]]:
    """{class index: [(card cid, invocation instance id)]} of the selected Lessons instances (2024 Warlock)."""
    out = {}
    for rc in resolved_classes:
        if rc["cls"] and rc["cls_id"] == "warlock":
            instances = class_choices_2024.lessons_instances(catalog, rc, ruleset)
            if instances:
                out[rc["index"]] = [(class_choices_2024.dependent_cid(i, "feat"), i) for i in instances]
    return out


class _LessonsResolver:
    """The Origin feats picked at the Lessons cards, resolved in the F1 walk (see `_FightingStyleResolver`): hooked
    into `before_level`, position (class index, level 2), against `seen` (background, species and every pick at an
    earlier position). Two Lessons instances never share a feat, repeatable or not ("a different Origin feat"); the
    LATER pick of a duplicate is skipped (`skipped_duplicates`). `taken_by_cid[cid]` = `seen` before that card;
    `picked[cid]` = the feat index it holds. Any category O feat is honored (a pick hidden by sources / ruleset
    stays); anything else lands in `pruned` through the generic stale-selection pass."""

    def __init__(self, slots_by_class: dict[int, list[tuple[str, str]]], catalog: Catalog, skipped_duplicates: list[dict]):
        self.slots_by_class = slots_by_class
        self.catalog = catalog
        self.skipped_duplicates = skipped_duplicates
        self.picks: list[dict] = []
        self.taken_by_cid: dict[str, dict[str, str]] = {}
        self.picked: dict[str, str] = {}
        self._done: set[str] = set()
        self._own: set[str] = set()

    def __call__(self, rc: dict, upto_level: int | None, seen: dict[str, str]) -> None:
        if upto_level is not None and upto_level < LESSONS_LEVEL:
            return
        for cid, _inst in self.slots_by_class.get(rc["index"], []):
            if cid in self._done:
                continue
            self._done.add(cid)
            self.taken_by_cid[cid] = dict(seen)
            feat_index = _stored_asi_feat_pick(rc["class_choices"], cid)
            feat = self.catalog.feats.get(feat_index) if feat_index else None
            if not feat or feat.get("category") != "O":
                continue
            key = _feat_name_key(feat)
            if key in self._own or _taken_reason(feat, seen):
                self.skipped_duplicates.append({"feat": feat, "cid": cid, "level": LESSONS_LEVEL, "cls": rc["cls"]})
                continue
            self._own.add(key)
            _taken_add(seen, [feat])
            self.picked[cid] = feat["index"]
            self.picks.append({**feat, "_inv_cid": cid, "_asi_level": LESSONS_LEVEL, "_asi_origin": f"{cid}:{feat['index']}"})


class _FeatLessonsResolver:
    """RP20 (A3c): Lessons of the First Ones held through Eldritch Adept (2024: the feat's one invocation). The Origin
    feat is resolved in the F1 walk right after the Eldritch Adept ASI feat (`after_feat`), against the same `seen`
    map, so the LATER holder of a feat is the duplicate. The pick needs Warlock level 2 (the invocation's
    prerequisite, read at the final level like `_gate_feat_invocation_prereqs`) and yields to a Lessons the Warlock
    holds itself (the gate disables the same option). The RAW stored selection decides (the late gates never drop a
    Lessons pick that passes these checks). `slots[feat origin]` = (card cid, rc class id, ASI level)."""

    def __init__(self, catalog: Catalog, ruleset: str, warlock_level: int, class_holds_lessons: bool, skipped_duplicates: list[dict]):
        self.catalog = catalog
        self.active = ruleset == "2024" and warlock_level >= 2 and not class_holds_lessons
        self.ruleset = ruleset
        self.skipped_duplicates = skipped_duplicates
        self.picks: list[dict] = []
        self.slots: dict[str, tuple[str, str, int]] = {}
        self.taken_by_cid: dict[str, dict[str, str]] = {}
        self.picked: dict[str, str] = {}

    def __call__(self, rc: dict, lvl: int, feat: dict, seen: dict[str, str]) -> None:
        spec = fed_option_picks(feat) or {}
        if not self.active or spec.get("kind") != "invocation":
            return
        pool = {o["id"] for o in _option_pick_options(self.catalog, "invocation", self.ruleset)}
        card = f"{feat['_asi_origin']}:invocation"
        stored = rc["class_choices"].get(card)
        first = next((x for x in (stored if isinstance(stored, list) else []) if isinstance(x, str) and x in pool), None)
        if first != class_choices_2024.LESSONS_ID:
            return
        cid = class_choices_2024.dependent_cid(first, "feat", card + ":")
        self.slots[feat["_asi_origin"]] = (cid, rc["cls_id"], lvl)
        self.taken_by_cid[cid] = dict(seen)
        index = _stored_asi_feat_pick(rc["class_choices"], cid)
        pick = self.catalog.feats.get(index) if index else None
        if not pick or pick.get("category") != "O":
            return
        if _taken_reason(pick, seen):
            self.skipped_duplicates.append({"feat": pick, "cid": cid, "level": lvl, "cls": rc["cls"]})
            return
        _taken_add(seen, [pick])
        self.picked[cid] = pick["index"]
        self.picks.append({**pick, "_inv_cid": cid, "_inv_class": rc["cls_id"], "_ea_asi_cid": feat["_asi_cid"], "_asi_level": lvl,
                           "_asi_origin": f"{cid}:{pick['index']}"})


def _feat_lessons_templates(
    catalog: Catalog, rc: dict, resolver: "_FeatLessonsResolver", asi_feat: dict, card_source: dict, sources, ruleset: str,
    total_level: int, scores: dict[str, int], use_prerequisites: bool, held: "_HeldFeatState",
) -> list[dict]:
    """RP20: the Origin-feat card of an Eldritch Adept pick of Lessons of the First Ones (the resolver registered it);
    `card_source` is the source of the feat's own `:invocation` card."""
    slot = resolver.slots.get(asi_feat["_asi_origin"])
    if not slot:
        return []
    cid, _cls, _lvl = slot
    return [_lessons_card(catalog, rc, cid, class_choices_2024.LESSONS_ID, dict(card_source), sources, ruleset, total_level, scores,
                          use_prerequisites, held, resolver.taken_by_cid, resolver.picked)]


def _lessons_templates(
    catalog: Catalog, rc: dict, slots: list[tuple[str, str]], sources, ruleset: str, total_level: int,
    scores: dict[str, int], use_prerequisites: bool, held: "_HeldFeatState", taken_by_cid: dict[str, dict[str, str]],
    picked: dict[str, str],
) -> list[dict]:
    """One Origin-feat card per selected Lessons instance (see above)."""
    source = {"kind": "class", "id": "warlock", "label": rc["cls"]["name"], "level": LESSONS_LEVEL}
    return [_lessons_card(catalog, rc, cid, inst, dict(source), sources, ruleset, total_level, scores, use_prerequisites, held,
                          taken_by_cid, picked) for cid, inst in slots]


def _lessons_card(catalog: Catalog, rc: dict, cid: str, inst: str, source: dict, sources, ruleset: str, total_level: int,
                  scores: dict[str, int], use_prerequisites: bool, held: "_HeldFeatState", taken_by_cid: dict[str, dict[str, str]],
                  picked: dict[str, str]) -> dict:
    """One Origin-feat card for the Lessons instance `inst` held at `cid` (the Warlock's card or, RP20, a feat's)."""
    feats = [f for f in catalog.feats.values() if f.get("category") == "O" and _feat_offered(f, sources, ruleset)]
    keep_index = _stored_asi_feat_pick(rc["class_choices"], cid)
    kept = catalog.feats.get(keep_index) if keep_index else None
    if kept and kept.get("category") == "O" and all(f["index"] != kept["index"] for f in feats):
        feats.append({**kept, "_hidden_by_filters": True})
    others = {catalog.feats[i]["index"]: _feat_name_key(catalog.feats[i]) for c, i in picked.items() if c != cid and i in catalog.feats}
    options = []
    for feat, option in _feat_options(feats, ruleset):
        option.pop("group", None)
        if feat.get("_hidden_by_filters"):
            option["hiddenByFilters"] = True
        reason = (
            _LESSONS_REASON if feat["index"] in others or _feat_name_key(feat) in others.values() else None
        ) or _taken_reason(feat, taken_by_cid.get(cid)) or _feat_prerequisite_unmet_reason(
            feat, total_level, scores, use_prerequisites, held, catalog)
        if reason:
            option["disabled"] = True
            option["disabledReason"] = reason
        options.append(option)
    record = catalog.features.get(class_choices_2024.invocation_base_id(inst)) or {}
    return {
        "id": cid, "source": source,
        "label": class_choices_2024.instance_label(catalog, inst),
        "description": _join_desc(record.get("desc")) or msg("desc-origin-feat"),
        "count": 1, "options": options,
    }


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
        envelope = {**envelope, "keep_counts": True}  # RPX3: the counts of the rules text, in every ruleset (was 2024 only)
        if items is not None and _envelope_needs_expansion(envelope):
            tpl, dependents = build_equipment_choice(envelope, cid, source, msg("label-starting-equipment"), items)
            if tpl and dependents:
                dependents_by_choice[cid] = dependents
        else:
            tpl = build_choice_template(envelope, cid, source, msg("label-starting-equipment"))
        if not tpl:
            dropped_envelopes += 1
            continue
        if items is not None:  # RPX3: "20 arrows" is one catalog arrow pack
            for option in tpl["options"]:
                if option.get("quantities"):
                    option["quantities"] = pack_quantities(option["quantities"], items)
                    if not option["quantities"]:
                        del option["quantities"]
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (msg("desc-equipment-note", text=tpl["description"]) if tpl["description"]
                                  else msg("desc-equipment-note-only"))
        templates.append(tpl)
    return templates, dropped_envelopes, dependents_by_choice


def _spell_options(catalog: Catalog, cls_id: str, spell_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if s["level"] == spell_level and any(c["index"] == cls_id for c in s.get("classes", []))
        and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    matches.sort(key=lambda s: s["name"])
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _spell_options_up_to(catalog: Catalog, cls_id: str, max_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if 1 <= s["level"] <= max_level and any(c["index"] == cls_id for c in s.get("classes", []))
        and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _magical_secrets_options(catalog: Catalog, cls_id: str, max_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    """RP16 (SRD Bard Magical Secrets): every spell of level 0 .. `max_level` that sits on some class list but not
    on `cls_id`'s own (the own list is offered anyway; its cantrips live on the Cantrips card). A spell on no class
    list is not "from any class"."""
    matches = [
        s for s in catalog.spells.values()
        if s["level"] <= max_level and s.get("classes") and not any(c["index"] == cls_id for c in s["classes"])
        and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _additional_secrets_options(catalog: Catalog, max_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    """RPX1 (SRD Lore Bard 6 Additional Magical Secrets): every spell of level 0 .. `max_level` that sits on some class
    list ("two spells of your choice from any class", the Bard's own included). A spell on no class list is not
    "from a class"."""
    matches = [
        s for s in catalog.spells.values()
        if s["level"] <= max_level and s.get("classes") and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]


def _additional_secrets_templates(catalog: Catalog, rc: dict, spellcasting: dict, sources, ruleset: str, stored) -> list[dict]:
    """RPX1: the Lore Bard's Additional Magical Secrets card (mixed / 2014): count 2, spells of any class of a level the
    BARD table can cast (`spellcasting` is the Bard's own level row) and cantrips. The picks are not counted against
    Spells Known and not part of the RP16 cap; `class_choices_2024.gate_additional_secrets` keeps them apart from the
    Bard's other spell cards. A stored pick hidden by `sources` stays offered."""
    if not class_choices_2024.additional_secrets_applies(catalog, rc, ruleset):
        return []
    spec = reference_data.ADDITIONAL_SECRETS_2014
    feature = catalog.features[spec["feature"]]
    kept = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
    cid = class_choices_2024.additional_secrets_cid(catalog)
    envelope = {"choose": spec["count"], "from": {
        "option_set_type": "options_array",
        "options": _additional_secrets_options(catalog, _highest_spell_slot_level(spellcasting), sources, ruleset, kept)}}
    source = {"kind": "class", "id": rc["cls_id"], "label": rc["cls"]["name"], "level": feature.get("level") or 6}
    description = msg("desc-additional-secrets", text=" ".join(feature.get("desc") or []))
    tpl = build_choice_template(envelope, cid, source, spec["label"], description=description)
    if tpl is None:
        return []
    _tag_spell_level_groups(catalog, tpl)
    return [tpl]


def _apply_secrets_cap(catalog: Catalog, tpl: dict, cls_id: str, cap: int, stored, on_list: set[str] = frozenset()) -> None:
    """RP16: at most `cap` of the known spells may be off the class's own list (2 per Magical Secrets feature
    reached). Walks the stored picks in order like the generic pass (valid, deduplicated, first `count`); an
    off-list pick over the cap is disabled, so the generic pass drops it as a non-blocking `pruned` entry and it
    does not take a count slot. At the cap the other off-list options are disabled. `on_list` (RP19): the Spells of
    the Mark spells, which are on the class's list for this character. Mutates `tpl`."""
    def off_list(option_id: str) -> bool:
        return option_id not in on_list and not any(c["index"] == cls_id for c in (catalog.spells.get(option_id) or {}).get("classes", []))

    reason = msg("disabled-magical-secrets-used", cap=cap)
    valid = {o["id"] for o in tpl["options"] if not o.get("disabled")}
    stored_ids = [x for x in dict.fromkeys(stored if isinstance(stored, list) else []) if isinstance(x, str) and x in valid]
    accepted, used, excess = [], 0, []
    for x in stored_ids:
        if len(accepted) >= tpl["count"]:
            break
        if off_list(x):
            if used >= cap:
                excess.append(x)
                continue
            used += 1
        accepted.append(x)
    for opt in tpl["options"]:
        if off_list(opt["id"]) and not opt.get("disabled") and (opt["id"] in excess or (used >= cap and opt["id"] not in accepted)):
            opt["disabled"] = True
            opt["disabledReason"] = reason


def _feat_mark_spell_ids(catalog: Catalog, feats: list[dict], max_level: int) -> list[str]:
    """RP19: catalog ids (both editions of a spell, the visibility filter picks one) of the Spells of the Mark tables
    of the held feats, rows up to `max_level`."""
    out: list[str] = []
    for slug_ in feat_spell_tables.mark_spell_slugs(feats, max_level):
        sid = catalog.resolve_spell_id(slug_)
        for cand in (sid, catalog.spell_twins.get(sid)):
            if cand and cand in catalog.spells and cand not in out:
                out.append(cand)
    return out


def _highest_spell_slot_level(spellcasting: dict) -> int:
    highest = 0
    for n in range(1, 10):
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0:
            highest = n
    return highest


def _raise_walk_speed(speeds: dict[str, int], bonus: int) -> dict[str, int]:
    """F1: "Your speed increases by X feet" (Fast Movement, Unarmored Movement) raises the
    walking speed only; swim, fly, climb and burrow keep their own values."""
    if not bonus or "walk" not in speeds:
        return speeds
    return {**speeds, "walk": speeds["walk"] + bonus}


def _heavy_armor_speed_penalty(speeds: dict[str, int], penalty: int) -> dict[str, int]:
    """W1: armor below its Strength requirement reduces the walking speed by 10 ft (floor 0); other modes keep their value."""
    if not penalty or "walk" not in speeds:
        return speeds
    return {**speeds, "walk": max(0, speeds["walk"] - penalty)}


def _heavy_armor_speed_exempt(race: dict | None, subrace: dict | None) -> bool:
    """W1: "Your speed is not reduced by wearing heavy armor." -- a pinned trait of the race / subrace (dwarf-phb,
    Kaladesh) or the SRD dwarf race (reference_data.HEAVY_ARMOR_SPEED_EXEMPT_*). Dwarf (XPHB) has none."""
    if race and race.get("index") in HEAVY_ARMOR_SPEED_EXEMPT_RACES:
        return True
    for src in (race, subrace):
        for ref in list((src or {}).get("traits", [])) + list((src or {}).get("racial_traits", [])):
            if ref["index"] in HEAVY_ARMOR_SPEED_EXEMPT_TRAITS:
                return True
    return False


def _is_mastery_choice(tpl: dict) -> bool:
    """C2 class Weapon Mastery cards and (FE8) Weapon Master (XPHB)'s feat card share the `:weapon-mastery` suffix."""
    return tpl["source"]["kind"] in ("class", "feat") and tpl["id"].endswith(":weapon-mastery")


def _is_count_variable_choice(tpl: dict) -> bool:
    """True for the spell choices whose allowed count follows the class
    level table / casting modifier (see _spell_choice_templates), so a
    stored over-count is staleness rather than a malformed Draft. Broader than
    the frontend `isSpellChoiceId` in frontend/src/pages/ClassPage.tsx (which
    only sorts spell cards into the Spells tab): this also covers level-scaled
    feat spell picks, Weapon Mastery and Eldritch Invocations, which the
    frontend does not treat as spell cards."""
    if tpl.get("count_by_level"):
        return True  # level-scaled feat spell picks (Ritual Caster) and Elemental Attunement: over-count is staleness
    if _is_mastery_choice(tpl):
        return True  # C2: Weapon Mastery count follows the class table (FE8: and the feat card's proficiency gate)
    if tpl["source"]["kind"] == "class" and ":invocations:" in tpl["id"]:
        return True  # Eldritch Invocations known follow the warlock level table
    if class_choices_2024.is_dependent_choice(tpl):
        return True  # C7c: invocation dependents (targets, Tome, pact weapon, Lessons feat) follow the spell cards / inventory; RP20: also the Eldritch Adept's
    if class_choices_2024.is_additional_secrets_card(tpl):
        return True  # RPX1: the offered spell levels follow the Bard table (and the sources filter)
    if subclass_spells_2024.is_pick_card(tpl):
        return True  # RP17: Savants (count and spell levels follow the Wizard table), Improved Illusions, Magical Discoveries
    # C6d: Spell Mastery / Signature Spells picks follow the spellbook and the class level
    return tpl["source"]["kind"] == "class" and tpl["id"].endswith(
        (":spells-cantrips", ":spells-known", ":spellbook", ":spell-mastery-1", ":spell-mastery-2", ":signature-spells"))


def _tag_spell_level_groups(catalog: Catalog, tpl: dict) -> None:
    """Set `group` = "spell-level-N" on each spell option (catalog spell
    level) so the picker can render level headings."""
    for opt in tpl["options"]:
        spell = catalog.spells.get(opt["id"])
        if spell is not None:
            opt["group"] = f"spell-level-{spell['level']}"


def _apply_school_limit(
    catalog: Catalog, tpl: dict, limit: dict, class_level: int, cls_id: str, stored, problems_out: list | None,
) -> None:
    """2014 third-caster school limit on the known-spells card (see
    _spell_choice_templates). Mutates `tpl`."""
    schools = set(limit["schools"])
    free = len([lvl for lvl in limit["free_at"] if lvl <= class_level])

    def inside(option_id: str) -> bool:
        return ((catalog.spells.get(option_id) or {}).get("school") or {}).get("index") in schools

    for opt in tpl["options"]:
        opt["group"] = "school" if inside(opt["id"]) else "any-school"
    tpl["options"].sort(key=lambda o: o["group"] != "school")  # stable: keeps (level, name) inside each group
    valid = {o["id"] for o in tpl["options"] if not o.get("disabled")}
    picked = [x for x in dict.fromkeys(stored if isinstance(stored, list) else []) if isinstance(x, str) and x in valid]
    picked = picked[: tpl["count"]]
    outside = [x for x in picked if not inside(x)]
    if len(outside) >= free:
        for opt in tpl["options"]:
            if opt["group"] == "any-school" and not opt.get("disabled") and opt["id"] not in picked:
                opt["disabled"] = True
                opt["disabledReason"] = msg("disabled-school-limit", free=free, schools=list(limit["schools"]))
    if len(outside) > free and problems_out is not None:
        problems_out.append({
            "id": f"subclass-spell-school-limit-{cls_id}",
            "message": msg("subclass-spell-school-limit", n=len(outside), school_a=limit["schools"][0], school_b=limit["schools"][-1], free=free),
        })


def _effective_caster(catalog: Catalog, rc: dict, ruleset: str = "mixed") -> tuple[str, dict, str] | None:
    """(spellcasting ability, spellcasting dict, spell-list class id) of a
    resolved class entry, or None. A class with its own spellcasting uses its
    level row; otherwise a subclass with a third-caster `spellcasting` block
    (Eldritch Knight, Arcane Trickster) at class level >= 3 yields ability INT
    and a SYNTHETIC dict (`cantrips_known`, `spells_known`, `spell_slots_level_N`,
    `spells_kind`) shaped like a class level row's `spellcasting`. The
    synthetic dict is only handed to _spell_choice_templates; it never lands
    in `rc["level_row"]`. Under ruleset "2024" a class with an XPHB progression
    (`catalog.class_2024_progressions`) gets a COPY of its spellcasting dict
    with the cantrip count, the fixed prepared-spell count (`spells_known`,
    `spells_kind: "prepared"`) from those tables and, for a Paladin/Ranger,
    the round-up slots (caster level ceil(level / 2), slots from level 1)."""
    cls, cls_id, level = rc["cls"], rc["cls_id"], rc["level"]
    ability = spells_mod.spellcasting_ability(cls) if cls else None
    if ability:
        row = rc.get("level_row")
        if not row:
            return None
        sc = row.get("spellcasting") or {}
        prog = catalog.class_2024_progressions.get(cls_id) if ruleset == "2024" else None
        if prog and 1 <= level <= 20:
            sc = dict(sc)
            if prog["cantrips"]:
                sc["cantrips_known"] = prog["cantrips"][level - 1]
            sc["spells_known"] = prog["prepared"][level - 1]
            sc["spells_kind"] = "prepared"
            for n, count in spells_mod.single_class_spell_slots(catalog, cls_id, level, None, ruleset).items():
                sc[f"spell_slots_level_{n}"] = count
        return ability, sc, cls_id
    block = (rc.get("subclass") or {}).get("spellcasting")
    if not (isinstance(block, dict) and block.get("progression") == "1/3") or level < 3:
        return None
    try:
        sc = {"cantrips_known": block["cantrips"][level - 1], "spells_known": block["spells"][level - 1],
              "spells_kind": block.get("kind", "known")}
        for n, count in enumerate(block["slots"][level - 1], start=1):
            sc[f"spell_slots_level_{n}"] = count
    except (KeyError, IndexError, TypeError):
        return None
    return str(block.get("ability", "INT")).upper(), sc, str(block.get("list_class") or "wizard")


def _wizard_spellbook_template(
    catalog: Catalog, cls: dict, cls_id: str, spellcasting: dict, class_level: int, sources, ruleset: str,
    source: dict, keep: set[str], stored, mark_ids: list[str] = (),
) -> dict:
    """C4: the Wizard's spellbook choice (cid `class:wizard:spellbook`, both
    rulesets). XPHB / PHB: six level 1 spells at Wizard level 1, +2 for every
    later Wizard level, each of a level the character has spell slots for. Count
    follows the class level, so it is count-variable (`_is_count_variable_choice`,
    level-down reports `pruned`, never a blocking problem)."""
    count = 6 + 2 * (class_level - 1)
    max_spell_level = _highest_spell_slot_level(spellcasting)
    options = _spell_options_up_to(catalog, cls_id, max_spell_level, sources, ruleset, keep)
    added = _add_mark_options(catalog, options, mark_ids, max_spell_level, sources, ruleset, keep)  # RP19 Spells of the Mark
    envelope = {"choose": count, "from": {"option_set_type": "options_array", "options": options}}
    noun = (msg("noun-spell-levels", n=count, levels=[1]) if max_spell_level == 1
            else msg("noun-spell-upto", n=count, max=max_spell_level))
    description = msg("desc-spellbook", count=count, noun=noun)
    tpl = build_choice_template(envelope, f"class:{cls_id}:spellbook", source, msg("label-spellbook"), description=description)
    _tag_spell_level_groups(catalog, tpl)
    _label_mark_options(tpl, added)
    return tpl


def _add_mark_options(catalog: Catalog, options: list[dict], mark_ids: list[str], max_level: int, sources, ruleset: str,
                      keep=()) -> set[str]:
    """RP19: appends the Spells of the Mark spells (level 1 .. `max_level`, visible under the draft's sources and
    ruleset or already picked) that the class list does not offer yet to `options`, sorted like the rest. Returns the
    ids added (the ones to label)."""
    present = {o["item"]["index"] for o in options}
    added: set[str] = set()
    for sid in mark_ids:
        spell = catalog.spells.get(sid)
        if not spell or sid in present or not 1 <= spell["level"] <= max_level:
            continue
        if sid not in keep and not _spell_visible(catalog, spell, sources, ruleset):
            continue
        options.append({"option_type": "reference", "item": {"index": sid, "name": spell["name"]}})
        present.add(sid)
        added.add(sid)
    if added:
        options.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
    return added


def _label_mark_options(tpl: dict, added: set[str]) -> None:
    for opt in tpl["options"]:
        if opt["id"] in added:
            opt["label"] = f"{opt['label']} ({feat_spell_tables.MARK_LABEL})"


def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int, class_level: int,
    expanded_spell_ids: list[str] = (), always_prepared: dict[str, str] | None = None,
    sources=None, ruleset: str = "mixed", class_choices: dict | None = None, list_class_id: str | None = None,
    school_limit: dict | None = None, problems_out: list | None = None, secrets_cap: int = 0,
    subclass_id: str | None = None, mark_ids: list[str] = (),
) -> list[dict]:
    """`sources`/`ruleset` (the draft's) decide which catalog spells are
    offered; spells already selected in `class_choices` stay offered either
    way, so changing the ruleset never silently drops a pick. `list_class_id`
    (default: `cls_id`) is the class whose spell list is offered (a third
    caster uses the wizard list). `school_limit` (2014 Eldritch Knight /
    Arcane Trickster, `reference_data.SUBCLASS_SPELL_SCHOOL_LIMITS`) splits the
    known-spells card into `school` / `any-school` groups, locks the outside
    options once the stored picks use up the free slots, and appends a
    `subclass-spell-school-limit-<cls>` problem to `problems_out` when the
    stored picks exceed them. `secrets_cap` (RP16, SRD Bard Magical Secrets under mixed / 2014, from
    `class_choices_2024.magical_secrets_cap_2014`) adds the other classes' spells and cantrips to the known-spells
    card and limits how many of the picks may come from outside the class's own list. `subclass_id` (RP17, ruleset
    2024): the Wizard's selected subclass; a Savant card (free spellbook spells) is built after the spellbook card and
    its valid picks join the effective book (prepared card, Spell Mastery, Signature Spells). `mark_ids` (RP19): catalog
    ids of the held Mark feats' table spells (both editions of a spell); the ones up to this class's highest slot level
    join the spell list the cards offer, labelled "(Spells of the Mark)"."""
    if not level_row:
        return []
    spellcasting = level_row.get("spellcasting") or {}
    list_id = list_class_id or cls_id
    list_name = (catalog.classes.get(list_id) or cls)["name"]
    # An always-prepared spell and its 2014/2024 twin are the same spell.
    always_ids = dict(always_prepared or {})
    for sid, why in list(always_ids.items()):
        twin = catalog.spell_twins.get(sid)
        if twin:
            always_ids.setdefault(twin, why)
    templates = []
    # No `level` in source — these choices span every level a spellcaster
    # has reached (count grows as they level up), so they're not anchored
    # to one specific level the way a feature/ASI choice is.
    source = {"kind": "class", "id": cls_id, "label": cls["name"]}

    def _kept(cid: str) -> set[str]:
        picked = (class_choices or {}).get(cid)
        return {x for x in picked if isinstance(x, str)} if isinstance(picked, list) else set()

    cantrips_known = spellcasting.get("cantrips_known", 0)
    if cantrips_known > 0:
        envelope = {"choose": cantrips_known, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, list_id, 0, sources, ruleset, _kept(f"class:{cls_id}:spells-cantrips")),
        }}
        cid = f"class:{cls_id}:spells-cantrips"
        description = msg("desc-cantrips-from-list", n=cantrips_known, list=list_name)
        tpl = build_choice_template(envelope, cid, source, msg("label-cantrips-known"), description=description)
        if tpl:
            _tag_spell_level_groups(catalog, tpl)
            for opt in tpl["options"]:
                if opt["id"] in always_ids:
                    opt["disabled"] = True
                    opt["disabledReason"] = msg("disabled-always-prepared", source=always_ids[opt["id"]])
            templates.append(tpl)

    known_count = spells_mod.known_spell_count(level_row, ability_modifier, class_level=class_level, cls_id=cls_id)
    # C4: only the Wizard class has a spellbook (Eldritch Knight / Arcane
    # Trickster are fighter/rogue classes with list_class_id "wizard" and are
    # not affected). The prepared card then draws from the stored book.
    wizard_book: list[str] | None = None
    if cls_id == "wizard" and list_id == "wizard" and class_level >= 1 and _highest_spell_slot_level(spellcasting) > 0:
        book_tpl = _wizard_spellbook_template(
            catalog, cls, cls_id, spellcasting, class_level, sources, ruleset, source, _kept(f"class:{cls_id}:spellbook"),
            (class_choices or {}).get(f"class:{cls_id}:spellbook"), mark_ids,
        )
        templates.append(book_tpl)
        valid_book = {o["id"] for o in book_tpl["options"]}
        stored_book = (class_choices or {}).get(f"class:{cls_id}:spellbook")
        stored_book = list(dict.fromkeys(x for x in stored_book if isinstance(x, str))) if isinstance(stored_book, list) else []
        # Same rule as the generic pass: first `count` valid picks.
        wizard_book = [x for x in stored_book if x in valid_book][: book_tpl["count"]]
        if ruleset == "2024" and subclass_id:  # RP17: Abjuration / Divination / Evocation / Illusion Savant
            savant_tpl = subclass_spells_2024.savant_template(
                catalog, {"cls": cls, "cls_id": cls_id, "level": class_level, "subclass_id": subclass_id}, ruleset,
                _highest_spell_slot_level(spellcasting), wizard_book,
                lambda flt, keep: _spell_filter_options(catalog, flt, sources, ruleset, keep), class_choices)
            if savant_tpl is not None:
                templates.append(savant_tpl)
                savant_picks = subclass_spells_2024.effective_savant_picks(savant_tpl, (class_choices or {}).get(savant_tpl["id"]))
                for opt in book_tpl["options"]:  # the spellbook card may not repeat a free Savant spell
                    if opt["id"] in savant_picks and not opt.get("disabled"):
                        opt["disabled"] = True
                        opt["disabledReason"] = msg("disabled-chosen-as", label=savant_tpl["label"])
                wizard_book = wizard_book + [x for x in savant_picks if x not in wizard_book]
    # C6d (2024): Wizard 18 Spell Mastery / Wizard 20 Signature Spells; their picks are always prepared
    pick_templates: list[dict] = []
    if wizard_book is not None:
        pick_templates, pick_always = class_choices_2024.wizard_spell_pick_templates(
            catalog, class_level, wizard_book, source, ruleset, class_choices)
        for sid, why in pick_always.items():
            for key in (sid, catalog.spell_twins.get(sid)):
                if key:
                    always_ids.setdefault(key, why)
    if known_count > 0:
        max_spell_level = _highest_spell_slot_level(spellcasting)
        if wizard_book is not None:
            option_list = [{"option_type": "reference", "item": {"index": sid, "name": catalog.spells[sid]["name"]}} for sid in wizard_book]
            option_list.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
        else:
            option_list = _spell_options_up_to(catalog, list_id, max_spell_level, sources, ruleset, _kept(f"class:{cls_id}:spells-known"))
        present = {o["item"]["index"] for o in option_list}
        mark_added = (_add_mark_options(catalog, option_list, mark_ids, max_spell_level, sources, ruleset,
                                        _kept(f"class:{cls_id}:spells-known"))
                      if wizard_book is None else set())  # RP19 Spells of the Mark
        present |= mark_added
        for sid in (expanded_spell_ids if wizard_book is None else ()):  # e.g. Fiend Expanded Spell List
            spell = catalog.spells[sid]
            if sid not in present and 1 <= spell["level"] <= max_spell_level:
                option_list.append({"option_type": "reference", "item": {"index": sid, "name": spell["name"]}})
        if secrets_cap and wizard_book is None and list_id == cls_id:  # RP16: SRD Magical Secrets (levels 10 / 14 / 18)
            option_list += [o for o in _magical_secrets_options(
                catalog, cls_id, max_spell_level, sources, ruleset, _kept(f"class:{cls_id}:spells-known"))
                if o["item"]["index"] not in present]
        option_list.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": option_list,
        }}
        cid = f"class:{cls_id}:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None and spellcasting.get("spells_kind", "known") == "known"
        label = msg("label-spells-known") if is_known_caster else msg("label-prepared-spells")
        noun = (msg("noun-spell", n=known_count) if max_spell_level == 1
                else msg("noun-spell-upto", n=known_count, max=max_spell_level))
        if wizard_book is None:
            description = (msg("desc-spells-know", n=known_count, noun=noun, list=list_name) if is_known_caster
                           else msg("desc-spells-prepare", n=known_count, noun=noun, list=list_name))
        elif wizard_book:
            description = (msg("desc-spells-know-book", n=known_count, noun=noun) if is_known_caster
                           else msg("desc-spells-prepare-book", n=known_count, noun=noun))
        else:
            description = msg("desc-spellbook-first")
        if secrets_cap and wizard_book is None and list_id == cls_id:
            description = msg("desc-spells-secrets", text=description, cap=secrets_cap)
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl is not None and mark_added:
            _label_mark_options(tpl, mark_added)
        if tpl is None and wizard_book is not None and not wizard_book:
            # build_choice_template returns None for an empty option list; an
            # empty spellbook must still show the (option-less) prepared card.
            tpl = {"id": cid, "source": source, "label": label, "description": description, "count": known_count, "options": []}
        if tpl:
            _tag_spell_level_groups(catalog, tpl)
            for opt in tpl["options"]:
                if opt["id"] in always_ids:
                    opt["disabled"] = True
                    opt["disabledReason"] = msg("disabled-always-prepared", source=always_ids[opt["id"]])
            if school_limit:
                _apply_school_limit(catalog, tpl, school_limit, class_level, cls_id,
                                    (class_choices or {}).get(cid), problems_out)
            if secrets_cap and wizard_book is None and list_id == cls_id:
                _apply_secrets_cap(catalog, tpl, cls_id, secrets_cap, (class_choices or {}).get(cid), mark_added)
            templates.append(tpl)

    return templates + pick_templates


# C2: 2024 Weapon Mastery. XPHB class feature at level 1 of Barbarian, Fighter,
# Paladin, Ranger and Rogue (each class of a multiclass character grants its own).
# Count: the class table's "weapon-mastery" column (Barbarian, Fighter), else a
# fixed 2 (Paladin, Ranger, Rogue: "two kinds of weapons", no table column).
_MASTERY_FIXED_COUNT = {"paladin": 2, "ranger": 2, "rogue": 2}
_MASTERY_CLASSES = ("barbarian", "fighter", "paladin", "ranger", "rogue")


def _mastery_filter_reason(cls_id: str, item: dict) -> str | None:
    """Why the class's Weapon Mastery filter excludes a weapon, or None.
    Barbarian: Simple or Martial Melee. Fighter, Paladin, Ranger and Rogue: Simple or Martial (every
    weapon); F3a-8: the XPHB Rogue text is "two kinds of weapons of your choice with which you have
    proficiency", so only the proficiency gate limits the Rogue."""
    if cls_id == "barbarian" and item.get("weapon_range") != "Melee":
        return msg("disabled-melee-only")
    return None


def _weapon_mastery_template(catalog: Catalog, rc: dict, ruleset: str) -> list[dict]:
    """Weapon Mastery choice for one class (see above), only under ruleset "2024".
    Built EARLY with the class-filter reasons; the proficiency check needs the
    final weapon-proficiency set and is applied late by `_gate_mastery_choices`
    (same build-early / gate-late pattern as the expertise and invocation gates).
    No card when the catalog has no weapon with a mastery or no count is known."""
    cls_id = rc.get("cls_id")
    if ruleset != "2024" or cls_id not in _MASTERY_CLASSES or not rc.get("cls"):
        return []
    count = _MASTERY_FIXED_COUNT.get(cls_id)
    if count is None:
        values = (getattr(catalog, "class_2024_tables", None) or {}).get(cls_id, {}).get("weapon-mastery")
        level = rc["level"]
        if not values or not 0 < level <= len(values):
            return []
        count = values[level - 1]
    options = []
    for item in catalog.items.values():
        if item.get("equipment_category", {}).get("index") != "weapon" or not item.get("mastery"):
            continue
        option = {"id": item["index"], "label": f"{item['name']} ({item['mastery']})"}
        reason = _mastery_filter_reason(cls_id, item)
        if reason:
            option.update(disabled=True, disabledReason=reason)
        options.append(option)
    if not options or not count:
        return []
    return [{
        "id": f"class:{cls_id}:weapon-mastery",
        "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": 1},
        "label": msg("label-weapon-mastery"),
        "description": msg("desc-weapon-mastery-class", count=count),
        "count": count,
        "options": options,
    }]


def _gate_mastery_choices(choices: list[dict], catalog: Catalog, proficient_weapons: set[str]) -> list[dict]:
    """Disable Weapon Mastery options the character is not proficient with, drop stale
    selections of them, and only then cut the rest to the card's count (F1: the generic
    pass leaves mastery picks un-truncated, so a non-proficient pick never costs a valid
    one its place). Mutates `choices`; returns non-blocking pruned, each naming its reason."""
    pruned: list[dict] = []
    mastered: set[str] = set()  # FE8: weapons already mastered by a class card; the feat card (walked last) may not repeat them
    for i, c in sorted(((i, c) for i, c in enumerate(choices) if _is_mastery_choice(c)),
                       key=lambda ic: ic[1]["source"]["kind"] == "feat"):
        is_feat = c["source"]["kind"] == "feat"
        options, lacking, repeated = [], {}, {}
        for o in c["options"]:
            item = catalog.items.get(o["id"])
            if item and not o.get("disabled") and not attacks_mod.weapon_is_proficient(item, proficient_weapons):
                lacking[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": msg("disabled-not-proficient")}
            elif is_feat and not o.get("disabled") and o["id"] in mastered:
                repeated[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": msg("disabled-already-mastered")}
            options.append(o)
        dup = [repeated[s] for s in c["selected"] if s in repeated and s not in lacking]
        if dup:
            pruned.append({"choiceId": c["id"], "reason": msg("pruned-mastered-through-class", label=c["label"], names=dup)})
        proficient = [s for s in c["selected"] if s not in lacking and s not in repeated]
        selected = proficient[: c["count"]]
        dropped = [lacking[s] for s in c["selected"] if s in lacking]
        if dropped:
            pruned.append({
                "choiceId": c["id"],
                "reason": msg("pruned-weapon-not-proficient", label=c["label"], names=dropped),
            })
        overflow = proficient[c["count"]:]
        if overflow:
            names = [(catalog.items.get(d) or {}).get("name", d) for d in overflow]
            pruned.append({
                "choiceId": c["id"],
                "reason": msg("pruned-count-overflow", id=c["id"], count=c["count"], n=len(overflow), names=names),
            })
        choices[i] = {**c, "options": options, "selected": selected,
                      "status": "resolved" if len(selected) == c["count"] else "pending"}
        if not is_feat:
            mastered.update(selected)
    return pruned


def _weapon_masteries(choices: list[dict], catalog: Catalog) -> list[dict]:
    """sheet.weaponMasteries: every selected mastery weapon, first-seen order, deduped."""
    out: list[dict] = []
    for c in choices:
        if not _is_mastery_choice(c):  # class cards, then (FE8) Weapon Master (XPHB)'s feat card
            continue
        for sel in c["selected"]:
            item = catalog.items.get(sel)
            if item and item.get("mastery") and all(m["itemId"] != sel for m in out):
                out.append({"itemId": sel, "name": item["name"], "mastery": item["mastery"]})
    return out


# Warlock level at which each Mystic Arcanum spell level is gained (identical
# in the 2014 and 2024 books); the SRD `mystic_arcanum_level_N` column is the
# gate, this table only names the level used in the cid.
_ARCANUM_LEVELS = {6: 11, 7: 13, 8: 15, 9: 17}


def _mystic_arcanum_templates(catalog: Catalog, rc: dict, sources=None, ruleset: str = "mixed", class_choices: dict | None = None) -> list[dict]:
    """Warlock Mystic Arcanum (D11): one ordinary single-pick choice per
    arcanum spell level whose `class_specific.mystic_arcanum_level_N` is >= 1
    at the current Warlock level, always from the Warlock list (also in a
    multiclass). A spell already stored stays offered, as for other spell
    options."""
    if rc.get("cls_id") != "warlock" or not rc.get("cls"):
        return []
    specific = ((rc.get("level_row") or {}).get("class_specific")) or {}
    templates = []
    for spell_level, gained_at in _ARCANUM_LEVELS.items():
        if (specific.get(f"mystic_arcanum_level_{spell_level}") or 0) < 1:
            continue
        cid = f"class:warlock:{gained_at}:mystic-arcanum-{spell_level}"
        stored = (class_choices or {}).get(cid)
        keep = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
        envelope = {"choose": 1, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, "warlock", spell_level, sources, ruleset, keep),
        }}
        source = {"kind": "class", "id": "warlock", "label": rc["cls"]["name"], "level": gained_at}
        tpl = build_choice_template(
            envelope, cid, source, msg("label-feature-level", name="Mystic Arcanum", level=spell_level),
            description=msg("desc-mystic-arcanum", level=spell_level),
        )
        if tpl:
            _tag_spell_level_groups(catalog, tpl)
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
        qty = entry.get("quantity", 1)
        result.append({"itemId": item_id, "name": item["name"],
                       "qty": pack_units(item, qty) if isinstance(qty, int) and not isinstance(qty, bool) else qty})  # RPX3
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


def _monk_tool_pick(choices: list[dict]) -> str | None:
    """C9b: the Monk's tool proficiency pick (one of the Artisan's Tools / Musical Instrument ids),
    which the Monk starting-equipment package hands out as an item."""
    tool_ids = {t["index"] for t in reference_data.TOOLS}
    for c in choices:
        if (c["id"].startswith("class:monk:1:prof-choice-") and c["selected"]
                and any(o["id"] in tool_ids for o in c["options"])):
            return c["selected"][0]
    return None


def _background_tool_pick(choices: list[dict], bg_id: str | None, item_lookup: dict) -> str | None:
    """RP9: the tool picked by the background's own tool proficiency card (`background:<id>:proficiency-choice-*` with
    tool options), as a catalog item id; None when nothing is picked or the tool has no catalog item (the
    sentinel member then stays a narrative item)."""
    tool_ids = {t["index"] for t in reference_data.TOOLS}
    prefix = f"background:{bg_id}:proficiency-choice-"
    for c in choices:
        if (bg_id and c["id"].startswith(prefix) and c["selected"] and any(o["id"] in tool_ids for o in c["options"])):
            return c["selected"][0] if c["selected"][0] in item_lookup else None
    return None


def _chosen_equipment(equipment_choices: list[dict], item_lookup: dict, monk_tool: str | None = None,
                      background_tool: str | None = None) -> list[dict]:
    """The catalog items of the selected equipment bundles. A bundle option may carry `quantities`
    ({item id: n}, 2024 packages only, decisions E8 / RP9); everything else is qty 1. The Monk
    sentinel stands for `monk_tool` (the item of the tool proficiency pick), the background sentinel (RP9) for
    `background_tool`."""
    result: list[dict] = []
    for choice in equipment_choices:
        options_by_id = {opt["id"]: opt for opt in choice.get("options", [])}
        for selected_id in choice["selected"]:
            quantities = (options_by_id.get(selected_id) or {}).get("quantities") or {}
            for item_id in selected_id.split("+"):
                if item_id == reference_data.MONK_TOOL_SENTINEL:
                    item_id = monk_tool or ""
                elif item_id == reference_data.BACKGROUND_TOOL_SENTINEL:
                    item_id = background_tool or ""
                item = item_lookup.get(item_id)
                if item:
                    result.append({"itemId": item_id, "name": item["name"], "qty": quantities.get(item_id, 1)})
    return result


def _with_pack_contents(entries: list[dict], item_lookup: dict) -> list[dict]:
    """RP8 (ruleset 2024 only): an entry of a PHB 2024 equipment pack gets `contents`
    ([{itemId, name, qty}], PACKS_2024 order; members missing from the catalog are skipped). The pack stays one item."""
    out = []
    for entry in entries:
        pack = reference_data.PACKS_2024.get(entry.get("itemId"))
        if pack is None:
            out.append(entry)
            continue
        contents = [{"itemId": i, "name": item_lookup[i]["name"], "qty": q}
                    for i, q in pack["contents"] if i in item_lookup]
        out.append({**entry, "contents": contents})
    return out


def _selected_gold_and_narrative_items(equipment_choices: list[dict], monk_tool: str | None = None,
                                       background_tool: str | None = None) -> tuple[int, list[str]]:
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
                elif item_id == reference_data.MONK_TOOL_SENTINEL:
                    if not monk_tool:  # C9b: no tool proficiency pick yet -> the label is a narrative item
                        narrative_items.append(zipped[i] if zipped else "Artisan's Tools or Musical Instrument")
                elif item_id == reference_data.BACKGROUND_TOOL_SENTINEL:
                    if not background_tool:  # RP9: no tool proficiency pick (yet) -> the label is a narrative item
                        narrative_items.append(zipped[i] if zipped else "Tool (same as the tool proficiency)")
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


def _class_feature_list(
    catalog: Catalog, resolved_classes: list[dict], choices: list[dict] | None = None, feats: list[dict] | None = None,
) -> list[tuple[str, int, str]]:
    """(class_id, class_level, feature_index) for every class/subclass
    feature the character has, plus selected feature options (e.g. a
    chosen Fighting Style) read from `choices` when given, plus (C3) the
    resolved Fighting Style feats in `feats` (picked at a fighting-style card or an
    ASI) under their feat index, so CLASS_FEATURE_EFFECTS can key on `defense-xphb`."""
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
            lvl = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == src.get("id")), 0)
            for sel in [g["id"] for g in c.get("granted") or []] + list(c.get("selected") or []):
                out.append((src["id"], lvl, sel))
    first = next((rc for rc in resolved_classes if rc["cls_id"] and rc["cls"]), None)
    for c in choices or []:  # FE9 Fighting Initiate: the picked fighter style counts as a class feature (its effect, G1 names)
        if (c.get("source") or {}).get("kind") == "feat" and c["id"].endswith(":" + _OPTION_PICK_CARDS["fighting-style"][0]) and first:
            rc = next((r for r in resolved_classes if c["id"].startswith(f"class:{r['cls_id']}:")), first)
            out += [(rc["cls_id"], rc["level"], sel) for sel in c.get("selected") or []]
    for feat in feats or []:
        if feat.get("category") in _FS_FEAT_CATEGORIES and first:
            origin = feat.get("_asi_origin") or ""
            rc = next((r for r in resolved_classes if origin.startswith(f"class:{r['cls_id']}:")), first)
            out.append((rc["cls_id"], rc["level"], feat["index"]))
    return out


# Cap on `pruned` entries returned (a draft with 50k stale keys must not echo all of them).
MAX_PRUNED_REPORTED = 200


def resolve(draft: dict, catalog: Catalog) -> dict:
    draft, problems = normalize_draft(draft)
    warnings: list[dict] = []

    classes_raw = draft.get("classes")
    if classes_raw is None:
        classes_raw = []
    elif not isinstance(classes_raw, list):
        problems.append({"id": "malformed-classes", "message": msg("malformed-classes")})
        classes_raw = []
    classes = [c for c in classes_raw if isinstance(c, dict)]
    if len(classes) != len(classes_raw):
        problems.append({"id": "malformed-class-entry", "message": msg("malformed-class-entry")})

    seen_class_ids: set[str] = set()
    deduped_classes: list[dict] = []
    for c in classes:
        cid_check = c.get("classId")
        if cid_check in seen_class_ids:
            problems.append({"id": "duplicate-class", "message": msg("duplicate-class", cls=cid_check)})
            continue
        if cid_check is not None:
            seen_class_ids.add(cid_check)
        deduped_classes.append(c)
    classes = deduped_classes

    resolved_classes: list[dict] = []
    subclass_pruned: list[dict] = []
    for idx, entry in enumerate(classes):
        entry_cls_id = entry.get("classId")
        entry_subclass_id = entry.get("subclassId")
        entry_level = 1
        raw_level = entry.get("level", 1)
        try:
            entry_level = int(raw_level)
        except (TypeError, ValueError):
            problems.append({"id": "level-unsupported", "message": msg("level-invalid-number", value=raw_level, cls=entry_cls_id)})
            entry_level = 1
        if not (1 <= entry_level <= 20):
            problems.append({"id": "level-unsupported", "message": msg("level-out-of-range", level=entry_level, cls=entry_cls_id)})
            entry_level = 1

        entry_cls = catalog.classes.get(entry_cls_id) if entry_cls_id else None
        if entry_cls and draft.get("ruleset") == "2024":  # C9a: XPHB chassis (raw string, as O2)
            entry_cls = catalog.classes_2024.get(entry_cls_id, entry_cls)
        if entry_cls_id and not entry_cls:
            problems.append({"id": "unknown-class", "message": msg("unknown-class", id=entry_cls_id)})

        entry_subclass = catalog.subclasses.get(entry_subclass_id) if entry_subclass_id else None
        if entry_subclass_id and not entry_subclass:
            problems.append({"id": "unknown-subclass", "message": msg("unknown-subclass", id=entry_subclass_id)})
            entry_subclass_id = None
        elif entry_subclass and entry_cls_id and entry_subclass.get("class", {}).get("index") != entry_cls_id:
            problems.append({
                "id": "subclass-mismatch",
                "message": msg("subclass-mismatch", subclass=entry_subclass["name"], cls=entry_cls_id),
            })
            entry_subclass_id = None

        unlock_level = subclass_unlock_level(entry_cls_id, draft.get("ruleset"))  # ruleset is validated further down; only "2024" matters here
        if entry_subclass and unlock_level and entry_level < unlock_level:
            # Round-2 F4: level-down leaves `subclassId` in the draft (the UI only
            # hides the select). Below the unlock level it must not apply.
            subclass_pruned.append({
                "choiceId": f"class:{entry_cls_id}:subclass",
                "reason": msg("pruned-subclass-unlocks", subclass=entry_subclass["name"], cls=entry_cls_id, level=unlock_level),
            })
            entry_subclass = None
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
        problems.append({"id": "total-level-exceeded", "message": msg("total-level-exceeded", total=total_level)})

    primary = resolved_classes[0] if resolved_classes else None
    cls_id = primary["cls_id"] if primary else None
    cls = primary["cls"] if primary else None
    subclass_id = primary["subclass_id"] if primary else None
    subclass = primary["subclass"] if primary else None
    level = primary["level"] if primary else 1
    class_choices = primary["class_choices"] if primary else {}

    background_raw = draft.get("background")
    if background_raw is not None and not isinstance(background_raw, dict):
        problems.append({"id": "malformed-background", "message": msg("malformed-background")})
        background_raw = {}
    background_dict = background_raw or {}
    bg_id = background_dict.get("id")
    bg = catalog.backgrounds.get(bg_id) if bg_id else None
    if bg_id and not bg:
        problems.append({"id": "unknown-background", "message": msg("unknown-background", id=bg_id)})
    elif bg and not _source_allowed(bg, draft.get("sources")):
        # Round-2 F3: hidden by the Sources filter is a picker filter only
        # (like ruleset); the record still resolves, with a warning. Only ids
        # absent from the full catalog are `unknown-background` problems.
        warnings.append({
            "id": "source-hidden-background",
            "message": msg("source-hidden", name=bg["name"]),
        })

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
        problems.append({"id": "malformed-species", "message": msg("malformed-species")})
        species_raw = {}
    species = species_raw or {}
    race_id = species.get("id")
    race = catalog.races.get(race_id) if race_id else None
    if race_id and not race:
        problems.append({"id": "unknown-species", "message": msg("unknown-species", id=race_id)})
    elif race and not _source_allowed(race, draft.get("sources")):
        warnings.append({
            "id": "source-hidden-species",
            "message": msg("source-hidden", name=race["name"]),
        })

    subrace_id = species.get("subspeciesId")
    subrace = catalog.subraces.get(subrace_id) if subrace_id else None
    if subrace_id and not subrace:
        problems.append({"id": "unknown-subspecies", "message": msg("unknown-subspecies", id=subrace_id)})
    elif subrace and race_id and not race:
        subrace = None  # the species itself is unknown (reported above): no cascading mismatch
    elif subrace and (not race or subrace.get("race", {}).get("index") != race_id):
        problems.append({
            "id": "subspecies-mismatch",
            "message": msg("subspecies-mismatch", name=subrace["name"]),
        })
        subrace = None
    elif subrace and not _source_allowed(subrace, draft.get("sources")):
        # Subspecies carry their own book (Duergar is MTF under PHB Dwarf);
        # like a source-hidden species it still resolves, with a warning.
        warnings.append({
            "id": "source-hidden-subspecies",
            "message": msg("source-hidden", name=subrace["name"]),
        })

    # Read here (before the per-class loop) so _asi_choice_templates can use
    # it below; `use_prereqs` (multiclass) is derived from the SAME dict
    # further down, near _multiclass_prerequisite_problems.
    species_choices_raw = species.get("choices") if isinstance(species.get("choices"), dict) else {}
    # Slice 8b: the selected lineage / ancestry / legacy of a race with `variants`.
    species_variant = _selected_species_variant(race, species_choices_raw, race_id)
    species_size = _species_size(race, species_choices_raw, race_id)
    use_prerequisites_prefs = (draft.get("preferences") or {}).get("usePrerequisites", {})
    use_feat_prereqs = bool(use_prerequisites_prefs.get("feats"))

    held = _HeldFeatState()
    for bg_feat in background_feats:
        held.add_feat(bg_feat)
    # Pre-walk inputs use the FINAL character (same simplification as
    # total_level): permissive, never a false disable.
    held.has_spellcasting_feature = any(
        rc["cls"] and spells_mod.single_class_spell_slots(catalog, rc["cls_id"], rc["level"], rc["subclass_id"], draft.get("ruleset"))
        for rc in resolved_classes
    )
    held.fighting_style = any(_class_has_fighting_style(catalog, rc) for rc in resolved_classes if rc["cls"] and rc["cls_id"])  # C3
    held.race_names, held.subrace_names, held.size = _held_race_state(race, subrace, species_size)
    held.can_cast_spell = held.has_spellcasting_feature or bool(
        _species_innate_spells(race, subrace, catalog, species_variant)
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
    ruleset = draft.get("ruleset")
    if ruleset is None:
        ruleset = "mixed"
    elif ruleset not in RULESETS:
        warnings.append({"id": "ruleset-invalid", "message": msg("ruleset-invalid", ruleset=ruleset)})
        ruleset = "mixed"
    if ruleset == "2024":  # RP21: the stored invocation picks follow their repeat instance (`<id>~k`) when the base goes
        for rc in resolved_classes:
            if rc["cls_id"] == "warlock" and rc["cls"]:
                rc["class_choices"] = class_choices_2024.renumber_invocation_instances(catalog, rc, ruleset, rc["class_choices"])
    species_asi_on, background_asi_on, asi_warnings = _asi_policy(ruleset, race, subrace, bg)
    warnings += asi_warnings
    species_bonuses = _species_ability_bonuses(race, subrace) if species_asi_on else {}
    species_ability_choice_tpl = (
        _species_ability_bonus_choice_template(race, subrace, race_id) if species_asi_on else None
    )
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
    background_clamped_notes: list[dict] = []  # RP1
    background_ability_choice_tpl = _background_ability_bonus_choice_template(bg, bg_id) if background_asi_on else None
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

    # RP1 (X1): PHB 2024 background step: "None of these increases can raise a score above 20." The 2024 species
    # increase is off, so the background step sits on the base scores. Only the 2024 ruleset clamps (the 2014 rules
    # have no such sentence); the lost part is a non-blocking `pruned` entry like the FX7 feat clamp.
    if ruleset == "2024" and background_ability_choice_tpl and background_bonuses:
        for ab_key in derived_mod.ABILITIES:
            delta = background_bonuses.get(ab_key, 0)
            if delta <= 0:
                continue
            try:
                raw_base = int(base_scores.get(ab_key, 10))
            except (TypeError, ValueError):
                raw_base = 10
            applied = asi_mod.clamped_delta(ab_key, delta, {ab_key: raw_base + species_bonuses.get(ab_key, 0)})
            if applied < delta:
                background_bonuses[ab_key] = applied
                background_clamped_notes.append({
                    "choiceId": background_ability_choice_tpl["id"],
                    "reason": msg("pruned-ability-at-max", name=bg["name"], ab=ab_key, cap=asi_mod.ASI_CAP)})

    # Slice 8a: feats a species grants (Human/XPHB's Origin feat, Variant
    # Human's and Custom Lineage's free feat). Resolved BEFORE the ASI walk
    # so a species pick makes the same feat unavailable at an ASI level
    # (precedence: background -> species -> ASI levels, first pick wins).
    # Checked against the scores before any feat bonus and a snapshot of what
    # the character holds from the background alone.
    species_feat_templates: list[dict] = []
    species_feats: list[dict] = []
    bg_grant_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}
    bg_feat_slots = _background_feat_grant_slots(bg, bg_id)

    def _origin_choices_raw(feat: dict) -> dict:  # where a granted feat's cascaded picks are stored
        return bg_grant_choices_raw if feat.get("_background_grant") else species_choices_raw
    if race or bg_feat_slots:
        pre_feat_scores = {}
        for ab in derived_mod.ABILITIES:
            try:
                raw_base = int(base_scores.get(ab, 10))
            except (TypeError, ValueError):
                raw_base = 10
            pre_feat_scores[ab] = raw_base + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0)
        species_held_snapshot = held.copy()
        taken_feat_indices = _taken_add({}, background_feats)
        # W4: the background's own feat grant cards come first (precedence background -> species -> ASI) and reuse
        # the species feat card machinery; their feats join `species_feats` (the "origin pick feats" list) tagged
        # `_background_grant`, so the S2 duplicate map, the ASI pre-walk and the cascaded choices all see them.
        slots = [(c, g, "background", bg, bg_id, bg_grant_choices_raw) for c, g in bg_feat_slots]
        if race:
            slots += [(c, g, "species", race, race_id, species_choices_raw) for c, g in _species_feat_grant_slots(race, subrace, race_id)]
        for slot_cid, grant, slot_kind, owner, owner_id, owner_raw in slots:
            tpl = _species_feat_choice_template(
                owner, owner_id, slot_cid, grant, catalog, draft.get("sources"), pre_feat_scores, total_level,
                use_feat_prereqs, species_held_snapshot, taken_feat_indices, ruleset,
                keep=owner_raw.get(slot_cid) if isinstance(owner_raw.get(slot_cid), list) else (), kind=slot_kind,
            )
            species_feat_templates.append(tpl)
            picked = _resolve_species_selected_feats(tpl, owner_raw, catalog, problems, background_grant=slot_kind == "background")
            for feat in picked:
                if not _feat_offered(feat, draft.get("sources"), ruleset):
                    warnings.append({
                        "id": f"feat-hidden-by-filters-{slot_cid}",
                        "message": msg("feat-hidden-by-filters", feat=feat["name"]),
                    })
            species_feats += picked
            _taken_add(taken_feat_indices, picked)
    for species_feat in species_feats:
        held.add_feat(species_feat)

    # C3: 2024 fighting-style feat cards (precedence: background, species, then
    # fighting-style cards and ASI picks together by class level, F1; first pick wins).
    fs_slots_by_class = {
        rc["index"]: _fighting_style_slots(catalog, rc, draft.get("sources"), ruleset)
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    skipped_duplicate_fs_feats: list[dict] = []
    srd_fs_slots_by_class = {
        rc["index"]: _srd_fighting_style_slots(catalog, rc, {idx for _c, _l, idx in fs_slots_by_class.get(rc["index"], [])})
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    skipped_srd_styles: list[dict] = []
    fs_resolver = _FightingStyleResolver(fs_slots_by_class, catalog, skipped_duplicate_fs_feats,
                                         srd_fs_slots_by_class, skipped_srd_styles)
    skipped_duplicate_lessons: list[dict] = []  # C7c
    lessons_slots_by_class = _lessons_slots(catalog, resolved_classes, ruleset)
    lessons_resolver = _LessonsResolver(lessons_slots_by_class, catalog, skipped_duplicate_lessons)
    skipped_duplicate_ea_lessons: list[dict] = []  # RP20
    ea_lessons = _FeatLessonsResolver(
        catalog, ruleset, next((rc["level"] for rc in resolved_classes if rc["cls_id"] == "warlock" and rc["cls"]), 0),
        any(lessons_slots_by_class.values()), skipped_duplicate_ea_lessons)

    def walk_hook(rc, upto_level, seen):  # one ordered walk: fighting-style cards, Lessons feats, then the ASI picks
        fs_resolver(rc, upto_level, seen)
        lessons_resolver(rc, upto_level, seen)
    skipped_duplicate_asi_feats: list[dict] = []
    walk_seen0 = _taken_add({}, background_feats + species_feats)
    for sf in species_feats:  # RP4: an origin Fighting Initiate style is held before every class card
        _fi_seen_add(walk_seen0, catalog, sf, _origin_choices_raw(sf).get(f"{sf['_species_origin']}:fighting-style"), ruleset)
    asi_taken_before_cid: dict[str, dict[str, str]] = {}
    # F1: fighting-style cards and ASI picks resolve in one pass, ordered by (class
    # index, class level); the later pick is the duplicate.
    asi_feat_picks, asi_feat_deltas_by_cid = _resolve_asi_selected_feats(
        resolved_classes, catalog, draft.get("sources"),
        taken_indices=walk_seen0,
        skipped_duplicates=skipped_duplicate_asi_feats, ruleset=ruleset, fighting_style=held.fighting_style,
        before_level=walk_hook, taken_before_cid=asi_taken_before_cid, after_feat=ea_lessons,
    )
    fs_feats, fs_taken_by_cid = fs_resolver.picks, fs_resolver.taken_by_cid
    raw_all_choices: dict = {}  # G5: every raw selection of the draft (cids never collide across owners)
    for rc_ in resolved_classes:
        raw_all_choices.update(rc_["class_choices"])
    raw_all_choices.update(bg_grant_choices_raw)
    raw_all_choices.update(species_choices_raw)
    variant_follow = _followed_variants(background_feats + species_feats + fs_feats + asi_feat_picks, raw_all_choices)
    lessons_feats = lessons_resolver.picks + ea_lessons.picks  # RP20: Lessons held through Eldritch Adept follow the Warlock's
    for dup in skipped_srd_styles:  # G1
        problems.append({
            "id": f"fighting-style-duplicate-{dup['option']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for dup in skipped_duplicate_fs_feats:
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["feat"]["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for fs_feat in fs_feats:
        held.add_feat(fs_feat)
        if not _feat_offered(fs_feat, draft.get("sources"), ruleset):
            warnings.append({
                "id": f"feat-hidden-by-filters-{fs_feat['_fs_cid']}",
                "message": msg("feat-hidden-by-filters", feat=fs_feat["name"]),
            })
    for dup in skipped_duplicate_lessons + skipped_duplicate_ea_lessons:  # C7c, RP20
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["feat"]["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for lessons_feat in lessons_feats:
        held.add_feat(lessons_feat)
        if not _feat_offered(lessons_feat, draft.get("sources"), ruleset):
            warnings.append({
                "id": f"feat-hidden-by-filters-{lessons_feat['_inv_cid']}",
                "message": msg("feat-hidden-by-filters", feat=lessons_feat["name"]),
            })

    for dup in skipped_duplicate_asi_feats:
        problems.append({
            "id": f"feat-duplicate-{dup['feat']['index']}-{dup['cid']}",
            "message": msg("feat-duplicate-at-level", feat=dup["feat"]["name"], cls=dup["cls"]["name"], level=dup["level"]),
        })
    for pick in asi_feat_picks:
        if not _asi_feat_in_pool(pick, draft.get("sources"), ruleset, pick["_asi_level"], held.fighting_style):
            warnings.append({
                "id": f"feat-hidden-by-filters-{pick['_asi_cid']}",
                "message": msg("feat-hidden-by-filters", feat=pick["name"]),
            })
    asi_feats_by_cid = {f["_asi_cid"]: f for f in asi_feat_picks}
    prerequisite_blocked_asi_feat_cids: set[str] = set()
    cap_skipped_asi_feat_cids: set[str] = set()  # FE2: ASI feats whose increase did not fit under their cap

    # FE2 (B2): origin feats (background, then species) have no per-level gate to skip at, so each one's
    # delta is CLAMPED to the room left under its own cap (20, or 30 for an Epic Boon) on the scores it lands on:
    # base + species + background bonuses, then the earlier origin feats. Only the feat's delta is clamped, never
    # the species / background bonuses themselves. ASI-selected feats: see _apply_asi_progression.
    feat_bonuses: dict[str, int] = {}
    origin_running: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        try:
            raw_base = int(base_scores.get(ab, 10))
        except (TypeError, ValueError):
            raw_base = 10
        origin_running[ab] = raw_base + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0)
    applied_fixed_deltas_by_instance: dict[str, list[tuple[str, int]]] = {}  # what was really added, per feat instance

    def _apply_origin_delta(feat: dict, ab_key: str, delta: int) -> int:
        applied = asi_mod.clamped_delta(ab_key, delta, origin_running, _feat_ability_cap(feat))
        if applied:
            feat_bonuses[ab_key] = feat_bonuses.get(ab_key, 0) + applied
            origin_running[ab_key] = origin_running.get(ab_key, 10) + applied
        return applied

    fixed_clamped_notes: list[dict] = []  # FX7: fixed increases that did not fit under the cap (non-blocking `pruned`)

    def _apply_origin_fixed(feat: dict) -> None:
        applied_list = []
        for ab_key, delta in _feat_ability_bonuses([feat]).items():
            applied = _apply_origin_delta(feat, ab_key, delta)
            applied_list.append((ab_key, applied))
            if delta > 0 and applied < delta:
                fixed_clamped_notes.append({
                    "choiceId": feat.get("_species_origin") or f"feat:{feat['index']}",
                    "reason": msg("pruned-ability-at-max-delta", name=feat["name"], ab=ab_key, cap=_feat_ability_cap(feat),
                                  delta=delta)})
        applied_fixed_deltas_by_instance[_feat_instance_key(feat)] = applied_list

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
    feat_ability_choice_pairs: list[tuple[dict, dict]] = []
    feat_ability_choice_tpls: list[dict] = []
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
    feat_background_choices_raw = background_dict.get("choices") if isinstance(background_dict.get("choices"), dict) else {}

    def _apply_chosen_origin_deltas(source_feat: dict, feat_ability_tpl: dict, raw_choices: dict) -> None:
        # Options at the feat's cap are already disabled in the template (scores = the pre-feat scores), so a
        # stored pick of one is dropped here and pruned later by the generic pass.
        valid_feat_ability_ids = {o["id"] for o in feat_ability_tpl["options"] if not o.get("disabled")}
        raw_selected = raw_choices.get(feat_ability_tpl["id"]) or []
        # Same dedupe-before-cap-and-apply discipline as species'/background's own passes above.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_feat_abilities = [s for s in deduped_selected if s in valid_feat_ability_ids][: feat_ability_tpl["count"]]
        feat_ability_deltas = _feat_ability_bonus_deltas(source_feat["ability_bonus_options"])
        instance_chosen_deltas: list[tuple[str, int]] = []
        for ab_id in selected_feat_abilities:
            for ab_key, delta in feat_ability_deltas.get(ab_id, []):
                applied = _apply_origin_delta(source_feat, ab_key, delta)
                if applied:
                    instance_chosen_deltas.append((ab_key, applied))
        if instance_chosen_deltas:
            background_chosen_ability_deltas_by_instance[_feat_instance_key(source_feat)] = instance_chosen_deltas

    for background_feat in background_feats:
        _apply_origin_fixed(background_feat)
        for feat_ability_tpl, source_feat in _feat_ability_bonus_choice_templates([background_feat], scores=dict(origin_running)):
            feat_ability_choice_pairs.append((feat_ability_tpl, source_feat))
            feat_ability_choice_tpls.append(feat_ability_tpl)
            _apply_chosen_origin_deltas(source_feat, feat_ability_tpl, feat_background_choices_raw)
    # Species-granted feats: the same pass, selections read from
    # species.choices under each feat's own `_species_origin` prefix.
    species_feat_ability_tpls: list[dict] = []
    for species_feat in species_feats:
        _apply_origin_fixed(species_feat)
        for feat_ability_tpl, source_feat in _feat_ability_bonus_choice_templates(
            [species_feat], origin=species_feat["_species_origin"], scores=dict(origin_running),
        ):
            species_feat_ability_tpls.append(feat_ability_tpl)
            _apply_chosen_origin_deltas(source_feat, feat_ability_tpl, _origin_choices_raw(species_feat))

    final_scores: dict[str, int] = {}
    for ab in derived_mod.ABILITIES:
        raw = base_scores.get(ab, 10)
        try:
            base_score = int(raw)
        except (TypeError, ValueError):
            problems.append({"id": f"ability-invalid-{ab}", "message": msg("ability-invalid-number", ab=ab, value=raw)})
            base_score = 10
        final_scores[ab] = base_score + species_bonuses.get(ab, 0) + background_bonuses.get(ab, 0) + feat_bonuses.get(ab, 0)
    for ab in derived_mod.ABILITIES:
        if isinstance(base_scores.get(ab), int) and not isinstance(base_scores.get(ab), bool) and base_scores[ab] > 20:
            warnings.append({"id": f"ability-above-20-{ab}", "message": msg("ability-above-20", ab=ab, value=base_scores[ab])})
    for ab, score in final_scores.items():
        if 1 <= score <= 30:
            continue
        reported = next((p for p in problems if p["id"] == f"ability-out-of-range-{ab}"), None)  # normalize may have reported the base already
        if reported is None:
            problems.append({"id": f"ability-out-of-range-{ab}", "message": msg("ability-out-of-range", ab=ab, score=score)})
        elif reported["message"].key == "ability-out-of-range-clamped":  # WF: the clamped base plus bonuses still leaves the sheet out of range
            # (a tagged rebuild, not `+=`: a string operation would drop the tag; same text as "... final" not in message)
            reported["message"] = msg("ability-out-of-range-clamped-final", final=score, **reported["message"].params)

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
            held=held, held_by_level=rc_held_by_level, cap_skipped_feat_cids=cap_skipped_asi_feat_cids,
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
                "message": msg("feat-prerequisite-unmet-at-level", feat=blocked_feat["name"], cls=rc_cls["name"],
                               level=blocked_feat["_asi_level"]),
            })
        rc["asi_levels"] = rc_asi_levels  # stashed for Task 4's prerequisite check convenience, and for sheet assembly

        if rc["index"] == 0:
            choice_templates += _class_choice_templates(rc_cls, rc_cls_id)
        else:
            choice_templates += _multiclass_proficiency_choice_templates(rc_cls, rc_cls_id)
        rc_level_row = catalog.class_level_row(rc_cls_id, rc_level)
        rc["level_row"] = rc_level_row
        feature_refs = _cumulative_feature_refs(catalog, rc_cls_id, rc_subclass_id, rc_level)
        rc_fs_slots = fs_slots_by_class.get(rc["index"], [])
        choice_templates += _feature_choice_templates(
            catalog, rc_cls_id, rc_cls["name"], feature_refs, rc_subclass_id, class_level=rc_level,
            skip_features={idx for _cid, _lvl, idx in rc_fs_slots} | class_choices_2024.replaced_srd_features(catalog, rc_cls_id, ruleset),
            sources=draft.get("sources"), class_choices=rc_class_choices,
        )
        choice_templates += class_choices_2024.expertise_templates(catalog, rc, ruleset)  # C6b-1
        choice_templates += class_choices_2024.language_templates(catalog, rc, ruleset)  # C6b-2
        choice_templates += class_choices_2024.primal_knowledge_templates(catalog, rc, ruleset)  # C6b-2
        choice_templates += class_choices_2024.subclass_pick_templates(catalog, rc, ruleset)  # RP12
        choice_templates += subclass_options_2024.templates(catalog, rc, ruleset)  # RP13
        choice_templates += class_choices_2024.metamagic_templates(catalog, rc, ruleset)  # C6c-1
        choice_templates += class_choices_2024.invocation_templates(catalog, rc, ruleset)  # C7a
        for tpl in choice_templates:  # G1: SRD style options already held (feat or earlier SRD style)
            held_names = fs_taken_by_cid.get(tpl["id"])
            if held_names and any(tpl["id"] == c for c, _l, _i in srd_fs_slots_by_class.get(rc["index"], [])):
                names = _srd_style_options(catalog, tpl["id"].rsplit(":", 1)[1])
                for opt in tpl["options"]:
                    label = held_names.get("name:" + names.get(opt["id"], "\0"))
                    if label is not None:
                        opt["disabled"] = True
                        opt["disabledReason"] = msg("disabled-already-taken-from", where=label)
        choice_templates += _fighting_style_templates(  # C3
            catalog, rc, rc_fs_slots, draft.get("sources"), ruleset, total_level, final_scores, use_feat_prereqs, held,
            fs_taken_by_cid,
        )
        choice_templates += _lessons_templates(  # C7c
            catalog, rc, lessons_slots_by_class.get(rc["index"], []), draft.get("sources"), ruleset, total_level, final_scores,
            use_feat_prereqs, held, lessons_resolver.taken_by_cid, lessons_resolver.picked)
        for lessons_feat in lessons_feats:  # the Origin feat's own choices under its origin
            if lessons_feat["_asi_origin"].startswith(f"class:{rc_cls_id}:") and lessons_feat.get("_ea_asi_cid") not in rc_blocked_feat_cids:
                choice_templates += _feat_choice_templates([lessons_feat], origin=lessons_feat["_asi_origin"], items=catalog.items, catalog=catalog, ruleset=ruleset)
                choice_templates += _feat_spell_choice_templates(
                    [lessons_feat], catalog, origin=lessons_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
                )
        for fs_feat in fs_feats:  # cascaded choices (Blessed / Druidic Warrior cantrips) under the pick's origin
            if fs_feat["_asi_origin"].startswith(f"class:{rc_cls_id}:"):
                choice_templates += _feat_choice_templates([fs_feat], origin=fs_feat["_asi_origin"], items=catalog.items, catalog=catalog, ruleset=ruleset)
                choice_templates += _feat_spell_choice_templates(
                    [fs_feat], catalog, origin=fs_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
                )
        choice_templates += _asi_choice_templates(
            rc_cls_id, rc_cls["name"], rc_asi_levels, rc_asi_scores_by_level, catalog, total_level, use_feat_prereqs,
            draft.get("sources"),
            taken_by_level={lvl: asi_taken_before_cid.get(f"class:{rc_cls_id}:{lvl}:asi", {}) for lvl in rc_asi_levels},
            held_by_level=rc_held_by_level, ruleset=ruleset, class_choices=rc_class_choices,
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
                asi_feat_templates = _feat_choice_templates([asi_feat], origin=asi_feat["_asi_origin"], items=catalog.items, catalog=catalog, ruleset=ruleset)
                choice_templates += asi_feat_templates
                ea_card = next((t for t in asi_feat_templates if t["id"] == asi_feat["_asi_origin"] + ":invocation"), None)
                if ea_card:  # RP20: Eldritch Adept's Lessons of the First Ones has an Origin-feat card
                    choice_templates += _feat_lessons_templates(
                        catalog, rc, ea_lessons, asi_feat, ea_card["source"], draft.get("sources"), ruleset, total_level, final_scores,
                        use_feat_prereqs, held)
                choice_templates += _feat_spell_choice_templates(
                    [asi_feat], catalog, origin=asi_feat["_asi_origin"], raw_selections=rc_class_choices,
                    total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
                )
                choice_templates += [  # FE2: options at the feat's cap read this level's running scores
                    tpl for tpl, _ in _feat_ability_bonus_choice_templates(
                        [asi_feat], origin=asi_feat["_asi_origin"],
                        scores=rc_asi_scores_by_level.get(asi_feat["_asi_level"], {}),
                    )
                ]

    asi_selected_feats = [f for f in asi_feat_picks if f["_asi_cid"] not in prerequisite_blocked_asi_feat_cids]
    lessons_feats = [f for f in lessons_feats if f.get("_ea_asi_cid") not in prerequisite_blocked_asi_feat_cids]  # RP20
    resolved_feats = background_feats + species_feats + fs_feats + lessons_feats + asi_selected_feats

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
    # FE2: the fixed increase to subtract is the one that was APPLIED (clamped for an origin feat, skipped
    # for an ASI feat at its cap), never the raw one.
    for skipped_cid in cap_skipped_asi_feat_cids:
        applied_fixed_deltas_by_instance[_feat_instance_key(asi_feats_by_cid[skipped_cid])] = []
        skipped_feat = asi_feats_by_cid[skipped_cid]
        if _feat_ability_bonuses([skipped_feat]):  # FX7: a fixed increase was dropped at the cap (the chosen card says so itself)
            fixed_names = ", ".join(_feat_ability_bonuses([skipped_feat]))
            fixed_clamped_notes.append({
                "choiceId": skipped_cid,
                "reason": msg("pruned-ability-at-max", name=skipped_feat["name"], ab=fixed_names,
                              cap=_feat_ability_cap(skipped_feat))})
    problems += _feat_prerequisite_problems(
        resolved_feats, total_level, final_scores, use_feat_prereqs, background_chosen_ability_deltas_by_instance,
        applied_fixed_deltas_by_instance,
    )

    # Primal Champion et al.: fixed ability-score feature bonuses, applied
    # after ASIs and prerequisite checks (the 24 cap is theirs alone).
    # RP2: under 2024 the XPHB fixed-effect table (Body and Mind, Primal Champion cap 25, ...) joins the SRD one.
    xphb_effects = features_mod.xphb_effects_2024(catalog, resolved_classes, ruleset)
    ability_effects = features_mod.class_effects(_class_feature_list(catalog, resolved_classes), xphb_effects)
    pruned_ability_notes = features_mod.ability_bonus_losses(final_scores, ability_effects)
    final_scores = features_mod.apply_ability_bonuses(final_scores, ability_effects)
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
    warlock_spell_ctx: tuple[list[str], set[str]] | None = None  # RP20: (known cantrips, spells the Warlock owns) for Eldritch Adept
    for rc in resolved_classes:
        rc_cls, rc_cls_id, rc_level, rc_level_row = rc["cls"], rc["cls_id"], rc["level"], rc.get("level_row")
        if not (rc_cls and rc_cls_id):
            continue
        choice_templates += _mystic_arcanum_templates(catalog, rc, draft.get("sources"), ruleset, rc["class_choices"])
        choice_templates += _weapon_mastery_template(catalog, rc, ruleset)
        choice_templates += class_choices_2024.class_option_templates(catalog, rc, ruleset)  # C6a / C6c-2
        caster = _effective_caster(catalog, rc, ruleset)
        if caster:
            spell_ability, spell_dict, list_class_id = caster
            extra_cantrips = class_choices_2024.class_option_extra_cantrips(catalog, rc, ruleset)  # C6a Thaumaturge / Magician
            if extra_cantrips and spell_dict.get("cantrips_known", 0) > 0:
                spell_dict = {**spell_dict, "cantrips_known": spell_dict["cantrips_known"] + extra_cantrips}
            raw_feature_ids = {
                sel for cid, sels in rc["class_choices"].items() if ":feature:" in cid and isinstance(sels, list)
                for sel in sels if isinstance(sel, str)
            }
            sub_name = rc["subclass"]["name"] if rc["subclass"] else ""
            # C6d (2024): class always-prepared spells (Ranger Hunter's Mark, ...) and Bard Magical Secrets
            class_always = class_choices_2024.always_prepared_class_spells(catalog, rc_cls_id, rc_level, rc_cls["name"], ruleset)
            secrets_ids = [
                o["item"]["index"] for flt in class_choices_2024.magical_secrets_filters(
                    catalog, rc_cls_id, rc_level, _highest_spell_slot_level(spell_dict), ruleset)
                for o in _spell_filter_options(
                    catalog, flt, draft.get("sources"), ruleset,
                    {x for x in (rc["class_choices"].get(f"class:{rc_cls_id}:spells-known") or []) if isinstance(x, str)})
            ]
            land_variant = subclass_options_2024.picked_variant(catalog, rc, rc["class_choices"])  # RP17 Circle of the Land
            sub_always = {sid: f"{sub_name}" for sid in
                          _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "always", land_variant, ruleset)}
            options_fn = lambda flt, keep: _spell_filter_options(catalog, flt, draft.get("sources"), ruleset, keep)  # noqa: E731
            if subclass_spells_2024.improved_illusions_applies(catalog, rc, ruleset):
                # RP17: a Minor Illusion pick on the Cantrips card is allowed (Improved Illusions then adds a cantrip);
                # unpicked, the subclass grant keeps listing it
                for sid in subclass_spells_2024.minor_illusion_ids(catalog):
                    sub_always.pop(sid, None)
                tpl_ = subclass_spells_2024.cantrip_template(catalog, rc, ruleset, options_fn, rc["class_choices"])
                if tpl_:
                    choice_templates.append(tpl_)
            discoveries_tpl, discoveries_always = subclass_spells_2024.discoveries_template(  # RP17 Lore Bard 6
                catalog, rc, ruleset, _highest_spell_slot_level(spell_dict), {**class_always, **sub_always}, options_fn,
                rc["class_choices"])
            if discoveries_tpl:
                choice_templates.append(discoveries_tpl)
            spell_templates = _spell_choice_templates(
                catalog, rc_cls, rc_cls_id, {"spellcasting": spell_dict}, modifiers[spell_ability], class_level=rc_level,
                expanded_spell_ids=_subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "expanded")
                + secrets_ids,
                always_prepared={**class_always, **sub_always, **discoveries_always},
                subclass_id=rc["subclass_id"],
                sources=draft.get("sources"), ruleset=ruleset, class_choices=rc["class_choices"],
                list_class_id=list_class_id,
                school_limit=SUBCLASS_SPELL_SCHOOL_LIMITS.get(rc["subclass_id"] or "") if list_class_id != rc_cls_id else None,
                problems_out=problems,
                secrets_cap=class_choices_2024.magical_secrets_cap_2014(catalog, rc_cls_id, rc_level, ruleset),
                mark_ids=_feat_mark_spell_ids(catalog, resolved_feats, _highest_spell_slot_level(spell_dict)),
            )
            class_choices_2024.label_magical_secrets(catalog, spell_templates, rc_cls_id, rc_level, ruleset)
            choice_templates += spell_templates
            choice_templates += _additional_secrets_templates(  # RPX1: SRD Lore Bard 6
                catalog, rc, spell_dict, draft.get("sources"), ruleset, rc["class_choices"].get(class_choices_2024.additional_secrets_cid(catalog)))
            if rc_cls_id == "warlock":  # C7c: target cantrips, Pact of the Tome, pact weapon
                kept_tome = {x for cid_ in (class_choices_2024.dependent_cid(class_choices_2024.TOME_ID, k) for k in ("cantrips", "rituals"))
                             for x in (rc["class_choices"].get(cid_) if isinstance(rc["class_choices"].get(cid_), list) else [])
                             if isinstance(x, str)}
                owned_spells = set(class_always) | set(
                    _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc_level, raw_feature_ids, "always", ruleset=ruleset))
                choice_templates += class_choices_2024.invocation_dependent_templates(
                    catalog, rc, ruleset, spell_templates,
                    lambda flt: _spell_filter_options(catalog, flt, draft.get("sources"), ruleset, kept_tome), owned_spells)
                known_, prepared_ = class_choices_2024.warlock_spell_picks(spell_templates, rc["class_choices"])
                warlock_spell_ctx = (known_, owned_spells | set(known_) | set(prepared_))

    asi_levels = primary.get("asi_levels", []) if primary else []
    level_row = primary.get("level_row") if primary else None
    if bg and bg_id:
        choice_templates += _background_choice_templates(bg, bg_id)
        choice_templates += class_choices_2024.origin_language_templates(bg, bg_id, ruleset)  # C8
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
        total_level=total_level, sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
    )
    choice_templates += _feat_choice_templates(background_feats, items=catalog.items, catalog=catalog, ruleset=ruleset)  # ASI-selected feats' templates: built origin-scoped in the per-class loop
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
        choice_templates += _feat_choice_templates([species_feat], origin=origin, items=catalog.items, catalog=catalog, ruleset=ruleset)
        choice_templates += _feat_spell_choice_templates(
            [species_feat], catalog, origin=origin, raw_selections=_origin_choices_raw(species_feat), total_level=total_level,
            sources=draft.get("sources"), ruleset=ruleset, follow_variants=variant_follow,
        )
    choice_templates += species_feat_ability_tpls
    if race and race_id:
        species_variant_tpl = _species_variant_template(race, race_id)
        if species_variant_tpl:
            choice_templates.append(species_variant_tpl)
        species_size_tpl = _species_size_template(race, race_id)
        if species_size_tpl:
            choice_templates.append(species_size_tpl)
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace, species_variant)
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
                "message": msg("equipment-envelope-dropped", name=cls["name"], n=cls_dropped),
            })
    if bg and bg_id:
        # RP9 (C, E12): under ruleset 2024 the 2024 envelope (real items and quantities) replaces the old one; the cid
        # and the A/B structure are the same
        bg_equipment_src = bg
        if ruleset == "2024" and bg.get("starting_equipment_options_2024"):
            bg_equipment_src = {**bg, "starting_equipment_options": bg["starting_equipment_options_2024"]}
        bg_equipment_templates, bg_dropped, bg_dependents = _equipment_choice_templates(
            bg_equipment_src, "background", bg_id, bg["name"], catalog.items)
        equipment_dependents.update(bg_dependents)
        choice_templates += bg_equipment_templates
        if bg_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-background-{bg_id}",
                "message": msg("equipment-envelope-dropped", name=bg["name"], n=bg_dropped),
            })

    _apply_background_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], bg)
    _apply_species_overlap([t for t in choice_templates if t["source"]["kind"] == "class"], race, subrace, catalog)

    # Apply the draft's own selections onto each template to get a real Choice.
    equipment_raw = draft.get("equipment")
    equipment_dict = equipment_raw if isinstance(equipment_raw, dict) else {}
    equipment_choices_raw = equipment_raw.get("choices") if isinstance(equipment_raw, dict) else None
    if equipment_choices_raw is not None and not isinstance(equipment_choices_raw, dict):
        problems.append({"id": "malformed-equipment-choices", "message": msg("malformed-equipment-choices")})
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

    # RP20 (A3b): the dependents of an Eldritch Adept pick (target cantrips, Pact of the Tome, Pact of the Blade) under
    # ruleset 2024: the C7c builders with the feat card as the holder. Built here because every feat card exists now
    # and the target options are the Warlock's known cantrips.
    warlock_level = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == "warlock" and rc["cls"]), 0)
    feat_inv_holders = class_choices_2024.feat_invocation_holders(catalog, choice_templates, all_selections, warlock_level, ruleset)
    if feat_inv_holders:
        known_cantrips, owned_by_warlock = warlock_spell_ctx or ([], set())
        choice_templates += class_choices_2024.feat_dependent_templates(
            catalog, feat_inv_holders, known_cantrips, owned_by_warlock,
            lambda flt, kept: _spell_filter_options(catalog, flt, draft.get("sources"), ruleset, kept))

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
    # RP5: a feat that reuses another held feat's spellcasting ability has no ability card of its own; a stored pick on it
    # becomes a non-blocking `pruned` entry through the stale-selection pass below.
    held_feat_indexes = {f["index"] for f in resolved_feats}
    no_own_ability_card = {
        f"{_feat_cid_prefix(f)}:spell-ability" for f in resolved_feats
        if feat_effects_mod.ability_from(feat_effects_data.FEAT_EFFECTS.get(f["index"])) in held_feat_indexes}
    if no_own_ability_card:
        choice_templates = [tpl for tpl in choice_templates if tpl["id"] not in no_own_ability_card]
    current_template_ids = {tpl["id"] for tpl in choice_templates}
    pruned = subclass_pruned + [
        {"choiceId": choice_id, "reason": msg("pruned-stale", id=choice_id)}
        for choice_id, selected in all_selections.items()
        if selected and choice_id not in current_template_ids
    ]
    pruned += background_clamped_notes + fixed_clamped_notes + pruned_ability_notes
    # A stored feat pick at an ASI slot that is not among that slot's options
    # (structurally ineligible there, e.g. an Epic Boon below level 19) is
    # ignored; say so instead of leaving the card silently pending.
    template_option_ids = {tpl["id"]: {o["id"] for o in tpl["options"]} for tpl in choice_templates if _ASI_CID_RE.match(tpl["id"])}
    for choice_id, option_ids in template_option_ids.items():
        stored = all_selections.get(choice_id)
        if not isinstance(stored, list):
            continue
        for item in dict.fromkeys(s for s in stored if isinstance(s, str) and s.startswith("feat:")):
            if item not in option_ids:
                feat_record = catalog.feats.get(item[len("feat:"):])
                name = feat_record["name"] if feat_record else item
                pruned.append({
                    "choiceId": choice_id,
                    "reason": msg("pruned-asi-feat-ineligible", name=name),
                })
    choices: list[dict] = []
    for tpl in choice_templates:
        valid_ids = {o["id"] for o in tpl["options"] if not o.get("disabled")}
        raw_selected = all_selections.get(tpl["id"]) or []  # `or []` guards a JSON null value too
        # Dedupe (preserving first-occurrence order) so this generic pass
        # agrees with the early species-ability-bonus pass above, which
        # dedupes the same underlying selection before applying bonuses.
        raw_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        if tpl.get("granted"):
            # Granted automatically (e.g. Elemental Attunement): an old stored
            # pick of it is redundant, not a loss, so it is dropped silently.
            granted = {g["id"] for g in tpl["granted"]}
            raw_selected = [s for s in raw_selected if s not in granted]
        selected = [s for s in raw_selected if s in valid_ids]
        if _is_count_variable_choice(tpl):
            # A spellcaster's allowed count shrinks on level-down (or when
            # the casting modifier drops) while the choice id stays the
            # same, and spells above the class's highest slot level stop
            # being offered — both leave stale selections in the Draft.
            # Report them as non-blocking `pruned` entries (keep the first
            # `count` valid selections), not an over-selected problem.
            if not _is_mastery_choice(tpl) and not class_choices_2024.is_invocation_card_2024(tpl):
                # F1: mastery truncates after the proficiency gate; F3a-9: the 2024 invocation card after its prerequisite gate
                selected = selected[: tpl["count"]]
            dropped = [s for s in raw_selected if s not in selected]
            if dropped:
                names = [(catalog.spells.get(d) or catalog.items.get(d) or {}).get("name", d) for d in dropped]
                if _is_mastery_choice(tpl):  # F1: here only options the class filter / catalog no longer offers
                    if tpl["source"]["kind"] == "class":
                        reason = msg("pruned-mastery-unavailable-class", label=tpl["label"], names=names)
                    else:
                        reason = msg("pruned-mastery-unavailable-feat", label=tpl["label"], names=names)
                elif class_choices_2024.is_dependent_choice(tpl):
                    names = [
                        (catalog.spells.get(d) or catalog.items.get(d) or catalog.feats.get(d[len("feat:"):]) or {}).get("name", d)
                        for d in dropped]  # C7c
                    reason = msg("pruned-no-longer-available", label=tpl["label"], names=names)
                else:
                    reason = msg("pruned-count-overflow", id=tpl["id"], count=tpl["count"], n=len(dropped), names=names)
                    if tpl["id"] == "class:wizard:spells-known":
                        # F2-B: the prepared card offers only spellbook spells, so a pick the
                        # card no longer offers is missing from the book, not over the count.
                        outside = [d for d in dropped if d not in valid_ids]
                        if outside:
                            outside_names = [(catalog.spells.get(d) or {}).get("name", d) for d in outside]
                            rest = [d for d in dropped if d in valid_ids]
                            if rest:
                                rest_names = [(catalog.spells.get(d) or {}).get("name", d) for d in rest]
                                reason = msg("pruned-wizard-not-in-spellbook-and-over", id=tpl["id"], n=len(outside),
                                             names=outside_names, m=len(rest), count=tpl["count"], rest=rest_names)
                            else:
                                reason = msg("pruned-wizard-not-in-spellbook", id=tpl["id"], n=len(outside), names=outside_names)
                pruned.append({"choiceId": tpl["id"], "reason": reason})
        else:
            # F3a-1: a stored pick the card does not offer at all (e.g. a 2014 equipment bundle after switching to
            # the 2024 packages, which reuse the cid) is reported instead of vanishing. ASI feat picks have their
            # own entry above.
            offered = {o["id"] for o in tpl["options"]}
            gone = [s for s in raw_selected if s not in offered
                    and not (s.startswith("feat:") and _ASI_CID_RE.match(tpl["id"]))]
            if gone:
                def _pick_name(pick):
                    def _one(part):
                        rec = catalog.items.get(part) or catalog.spells.get(part) or catalog.feats.get(part) or {}
                        return rec.get("name", part)
                    return " + ".join(_one(p) for p in pick.split("+")) if "+" in pick else _one(pick)
                pruned.append({
                    "choiceId": tpl["id"],
                    "reason": msg("pruned-no-longer-offered", label=tpl["label"], names=[_pick_name(g) for g in gone]),
                })
            if tpl["source"]["kind"] == "class" and _ASI_CID_RE.match(tpl["id"]):
                # RPF: a stored ASI pick whose option is offered but disabled (cap 20 after a ruleset / species switch,
                # a feat prerequisite) is reported with the option's own reason instead of leaving the card pending silently.
                for o in tpl["options"]:
                    if o.get("disabled") and o["id"] in raw_selected:
                        pruned.append({"choiceId": tpl["id"], "reason": msg(
                            "pruned-asi-option-closed", label=tpl["label"], option=o["label"],
                            why=o.get("disabledReason", msg("disabled-not-available")))})
            if tpl["source"]["kind"] == "feat" and tpl["id"].endswith(":ability-bonus"):
                # FE2 (B9): a stored pick of an option closed by the feat's ability cap is reported, not lost silently.
                closed = [o for o in tpl["options"] if o.get("disabled") and o["id"] in raw_selected]
                if closed:
                    pruned.append({
                        "choiceId": tpl["id"],
                        "reason": msg("pruned-ability-closed", label=tpl["label"], items=[
                            msg("pruned-ability-closed-item", ab=o["id"].upper(), why=o.get("disabledReason", msg("disabled-not-available")))
                            for o in closed]),
                    })
            if len(selected) > tpl["count"]:
                problems.append({
                    "id": f"over-selected-{tpl['id']}",
                    "message": msg("over-selected", label=tpl["label"], count=tpl["count"], submitted=len(selected)),
                })
                selected = selected[: tpl["count"]]
        status = "resolved" if len(selected) == tpl["count"] else "pending"
        choices.append({**tpl, "selected": selected, "status": status})

    added_raw = equipment_dict.get("added")
    if added_raw is None:
        added_raw = []
    elif not isinstance(added_raw, list):
        problems.append({"id": "malformed-equipment-added", "message": msg("malformed-equipment-added")})
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
    monk_tool = _monk_tool_pick(choices)  # C9b
    background_tool = _background_tool_pick(choices, bg_id, catalog.items) if bg else None  # RP9
    chosen_equipment = _chosen_equipment(equipment_choices, catalog.items, monk_tool, background_tool)

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
    selected_gold, narrative_items = _selected_gold_and_narrative_items(equipment_choices, monk_tool, background_tool)
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

    def _spell_summary(sid: str) -> dict | None:
        spell = catalog.spells.get(sid)
        return {"id": sid, "name": spell["name"], "level": spell["level"]} if spell else None

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
    if ruleset == "2024":  # RP17: Improved Illusions applies only when Minor Illusion is known from another source
        pruned += subclass_spells_2024.gate_improved_illusions(choices, catalog, [
            e["spellId"] for e in (_species_innate_spells(race, subrace, catalog, species_variant)
                                   + _species_trait_spell_choices(race, subrace, catalog, choices)
                                   + _feat_innate_spells(resolved_feats, catalog, choices, follow_variants=variant_follow)) if e.get("spellId")])
    selections_now = {c["id"]: c["selected"] for c in choices}
    for rc in resolved_classes:
        rc_cls, rc_cls_id = rc["cls"], rc["cls_id"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_cantrip_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-cantrips"), None)
        rc_known_spells_choice = next((c for c in choices if c["id"] == f"class:{rc_cls_id}:spells-known"), None)
        feature_ids = {idx for cid_, lvl_, idx in _class_feature_list(catalog, [rc], choices)}
        always_ids = _subclass_spell_ids(catalog, rc_cls_id, rc["subclass_id"], rc["level"], feature_ids, "always",
                                         subclass_options_2024.picked_variant(catalog, rc, selections_now), ruleset)
        if ruleset == "2024" and subclass_spells_2024.improved_illusions_applies(catalog, rc, ruleset):
            # RP17: Minor Illusion known elsewhere (the Improved Illusions card exists) is not listed twice
            known_elsewhere = any((found := subclass_spells_2024.spec_for_card(c)) and found[1]["kind"] == "cantrip"
                                  for c in choices)
            if known_elsewhere:
                always_ids = [sid for sid in always_ids if sid not in subclass_spells_2024.minor_illusion_ids(catalog)]
        if rc_cls_id == "bard":  # RP17: Lore 6 Magical Discoveries picks are always prepared
            always_ids = always_ids + [sid for sid in subclass_spells_2024.picked_spells(choices, "discoveries")
                                       if sid not in always_ids]
        # C6d (2024): class grants (Hunter's Mark, ...) and the Wizard's Spell Mastery / Signature picks
        always_ids = always_ids + [
            sid for sid in class_choices_2024.always_prepared_class_spells(catalog, rc_cls_id, rc["level"], "", ruleset)
            if sid not in always_ids]
        wizard_pick_keys: dict[str, list[dict]] = {}
        if rc_cls_id == "wizard":  # C6d (2024) / RP15 (SRD Spell Mastery, not always prepared)
            for slug_, spec in wizard_spell_picks(ruleset).items():
                card = next((c for c in choices if c["id"] == class_choices_2024.spell_pick_cid(slug_, spec)), None)
                if card:
                    wizard_pick_keys.setdefault(spec["sheet_key"], []).extend(_spell_summaries(card))
                    if spec.get("always_prepared", True):
                        always_ids = always_ids + [s["id"] for s in _spell_summaries(card) if s["id"] not in always_ids]
        if not (rc_cantrip_choice or rc_known_spells_choice or always_ids):
            continue
        rc_caster = _effective_caster(catalog, rc, ruleset)
        rc_spell_ability = (rc_caster[0] if rc_caster else None) or spells_mod.spellcasting_ability(rc_cls) or SUBCLASS_SPELLCASTING_ABILITY.get(rc["subclass_id"] or "")
        rc_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        rc_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        arcanum = []
        if rc_cls_id == "warlock":
            for ch in choices:
                if ":mystic-arcanum-" in ch["id"] and ch["id"].startswith("class:warlock:") and ch["selected"]:
                    spell = catalog.spells.get(ch["selected"][0])
                    if spell:
                        arcanum.append({"level": spell["level"], "id": spell["index"], "name": spell["name"]})
        spells_summary.append({
            "classId": rc_cls_id,
            **({"mysticArcanum": arcanum} if rc_cls_id == "warlock" else {}),
            "cantrips": _spell_summaries(rc_cantrip_choice) + (  # RP17: Improved Illusions (not counted in the cantrips known)
                [s for sid in subclass_spells_2024.picked_spells(choices, "cantrip") if (s := _spell_summary(sid))]
                if rc_cls_id == "wizard" else []),
            "known": _spell_summaries(rc_known_spells_choice) + (  # RPX1: Additional Magical Secrets (not counted in Spells Known)
                _spell_summaries(next((c for c in choices if class_choices_2024.is_additional_secrets_card(c)), None))
                if rc_cls_id == "bard" else []),
            **({"spellbook": _spell_summaries(next((c for c in choices if c["id"] == "class:wizard:spellbook"), None))
                + [s for sid in subclass_spells_2024.picked_spells(choices, "savant") if (s := _spell_summary(sid))]}  # RP17 Savants
               if rc_cls_id == "wizard" else {}),
            **wizard_pick_keys,
            **({"pactOfTheTome": [s for kind in ("cantrips", "rituals") for s in _spell_summaries(
                next((c for c in choices if c["id"] == class_choices_2024.dependent_cid(class_choices_2024.TOME_ID, kind)), None))]}
               if rc_cls_id == "warlock" and any(c["id"] == class_choices_2024.dependent_cid(class_choices_2024.TOME_ID, "cantrips") for c in choices) else {}),
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
    slot_entries = [(rc["cls_id"], rc["level"], rc["subclass_id"]) for rc in resolved_classes if rc["cls"]]
    spell_slots, warlock_slots = spells_mod.spell_slots_for(catalog, slot_entries, ruleset)
    slot_granting_class_ids = spells_mod.slot_granting_classes(catalog, slot_entries, ruleset)

    granted_equipment = []
    if cls:
        granted_equipment += _fixed_equipment(cls.get("starting_equipment", []), catalog.items)
    if bg:
        granted_equipment += _fixed_equipment(bg.get("starting_equipment", []), catalog.items)

    if ruleset == "2024":  # RP8: pack contents (the pack stays one item) and table weights
        granted_equipment = _with_pack_contents(granted_equipment, catalog.items)
        chosen_equipment = _with_pack_contents(chosen_equipment, catalog.items)
        added_resolved = _with_pack_contents(added_resolved, catalog.items)

    for granted in granted_equipment:
        granted_item = catalog.items.get(granted["itemId"])
        if granted_item:
            equipped_items.append(granted_item)

    # G2: optional worn / wielded model. Absent -> `equipped_items` is untouched.
    inventory: dict[str, dict] = {}
    for entry in granted_equipment + chosen_equipment + added_resolved:
        inv_item = catalog.items.get(entry["itemId"])
        if inv_item:
            slot = inventory.setdefault(entry["itemId"], {"item": inv_item, "qty": 0})
            slot["qty"] += entry.get("qty", 1) if isinstance(entry.get("qty", 1), int) else 1
    # C7c + F3a-2c: the Pact of the Blade weapon is conjured, so it need not be in the inventory; it always gets an
    # attack row, built from the catalog item.
    pact_weapon_id = class_choices_2024.selected_pact_weapon(choices)
    if pact_weapon_id and catalog.items.get(pact_weapon_id) and all(i["index"] != pact_weapon_id for i in equipped_items):
        equipped_items.append(catalog.items[pact_weapon_id])
    gear = worn_mod.apply(equipped_items, equipment_dict, inventory, catalog.items)
    equipped_items = gear.items
    warnings += gear.warnings
    pruned += gear.pruned

    pruned += class_choices_2024.gate_additional_secrets(choices, catalog)  # RPX1: SRD Lore Bard 6, apart from the other spell cards
    # Derived stats.
    pruned += _gate_duplicate_skill_picks(choices, [rc["cls_id"] for rc in resolved_classes if rc["cls"]])  # RPF
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
        if (c["source"]["kind"] in ("class", "species", "background", "feat") and "expertise-choice" not in c["id"]
                and not class_choices_2024.is_positioned_proficiency_card(c)):  # C6b-2 / RP12: gated against the others below
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))
    fixed_origin_skills: set[str] = set()  # F3a-4: grants that predate every class level
    if bg:
        proficient_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
        fixed_origin_skills.update(p["index"] for p in bg.get("starting_proficiencies", []) if p["index"].startswith("skill-"))
    if race:
        trait_refs = list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else [])
        for ref in trait_refs:
            trait = catalog.traits.get(ref["index"])
            if not trait:
                continue
            proficient_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
            fixed_origin_skills.update(p["index"] for p in trait.get("proficiencies", []) if p["index"].startswith("skill-"))
    # Phase 4c-i Task 6: a granted feat's own FIXED skill-proficiency grant
    # (e.g. a hypothetical background-granted Skilled/Prodigy-style feat)
    # feeds this SAME set, mirroring the bg/race passes just above — see
    # _feat_proficiency_ids' own docstring for why only fixed grants (not
    # a feat's own proficiency_choices) are read.
    feat_proficiency_ids = _feat_proficiency_ids(resolved_feats)
    proficient_skills.update(p for p in feat_proficiency_ids if p.startswith("skill-"))
    fixed_origin_skills.update(p for f in resolved_feats if not f.get("_asi_cid")
                               for p in _feat_proficiency_ids([f]) if p.startswith("skill-"))
    # C6b-2 + F3a-4 + RP12: the positioned picks (Primal Knowledge, the subclass skill / tool picks) yield only to
    # proficiencies gained at or before them; the picks that come later see theirs as already proficient instead.
    pk_class_order = [rc["cls_id"] for rc in resolved_classes if rc["cls"]]
    pruned += _gate_positioned_proficiencies(
        choices, catalog, resolved_classes, resolved_feats, bg, race, subrace, xphb_effects, pk_class_order)
    for c in choices:
        if class_choices_2024.is_positioned_proficiency_card(c):
            proficient_skills.update(s for s in c["selected"] if s.startswith("skill-"))

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
        elif "weapon" in prof_id or prof_id in _SPECIFIC_WEAPON_PROFICIENCY_IDS or prof_id in reference_data.FEAT_WEAPON_PROFICIENCY_IDS:
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
        if c["source"]["kind"] == "class" and ("prof-choice-" in c["id"] or class_choices_2024.is_positioned_proficiency_card(c)):
            for s in c["selected"]:  # RP12: Student of War's Artisan's Tools pick is positioned like the Monk's level 1 pick
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

    for c in choices:  # FE8: Weapon Master (PHB) picks are weapon proficiencies (filed straight into the weapon set)
        if c["source"]["kind"] == "feat" and c["id"].endswith(":weapon-choice"):
            proficient_weapons.update(reference_data.weapon_proficiency_id(s) for s in c["selected"])

    for effect in class_choices_2024.selected_class_option_effects(choices):  # C6a Protector / Warden
        for prof_id in effect.get("proficiencies", []):
            _categorize_proficiency(prof_id)

    for rc in resolved_classes:
        if not rc["cls"]:
            continue
        for prof_id in SUBCLASS_PROFICIENCIES.get(rc["subclass_id"], []):
            _categorize_proficiency(prof_id)
        if rc["index"] == 0:
            for p in rc["cls"].get("proficiencies", []):  # C9a: the 2024 chassis dict already holds XPHB lists
                _categorize_proficiency(p["index"])
        else:
            for p in rc["cls"].get("multi_classing", {}).get("proficiencies", []):
                _categorize_proficiency(p["index"])

    # Expertise needs the full proficiency picture (skills, plus the Rogue's
    # thieves' tools), so it is gated only after every grant above is in.
    # R8: the invocation gate runs first so Beguiling Influence's skills count for expertise.
    pruned += _gate_mastery_choices(choices, catalog, proficient_weapons)  # C2
    pruned += _gate_invocation_choices(choices, resolved_classes, catalog)
    inv_card = next((c for c in choices if class_choices_2024.is_invocation_card_2024(c)), None)
    if inv_card:  # C7c: dependents of an instance the gate dropped go with it
        pruned += class_choices_2024.prune_invocation_dependents(choices, inv_card["selected"])
    pruned += _gate_feat_invocation_prereqs(choices, resolved_classes, catalog)  # FE9 Eldritch Adept
    pruned += _gate_duplicate_picks(  # FE9 Fighting Initiate, Martial Adept, Metamagic Adept, Eldritch Adept
        choices, catalog, [rc["cls_id"] for rc in resolved_classes if rc["cls"]],
        {cid for slots in srd_fs_slots_by_class.values() for cid, _l, _i in slots},
        {cid for slots in fs_slots_by_class.values() for cid, _l, _i in slots})
    pruned += class_choices_2024.prune_feat_invocation_dependents(choices)  # RP20: dependents of a pick the gates removed
    invocation_effects = features_mod.invocation_effects(
        choices, {rc["cls_id"]: rc["level"] for rc in resolved_classes if rc["cls"]}, catalog)
    proficient_skills.update(features_mod.invocation_skills(invocation_effects))
    proficient_skills.update(features_mod.class_skill_proficiencies(xphb_effects))  # RP2 Mercy
    for prof_id in features_mod.class_other_proficiencies(xphb_effects):
        _categorize_proficiency(prof_id)
    poe_priors = _prof_or_expertise_priors(
        choices, resolved_feats, fixed_origin_skills, [rc["cls_id"] for rc in resolved_classes if rc["cls"]])  # FE6
    pruned += _gate_distinct_choices(choices, [rc["cls_id"] for rc in resolved_classes if rc["cls"]])  # FE7
    pruned += _gate_expertise_choices(
        choices, proficient_skills | proficient_tools, _feat_expertise_skills(resolved_feats),
        [rc["cls_id"] for rc in resolved_classes if rc["cls"]], ruleset, poe_priors)
    # C6b-2 + C8: origin and class language cards yield to fixed languages and to the other cards.
    # F3a-5: class fixed languages and Lessons / ASI feat languages count from their (class, level) position on, so
    # an earlier pick wins and the later duplicate is blamed; origin feats, species, background and Common come first.
    lang_class_order = [rc["cls_id"] for rc in resolved_classes if rc["cls"]]
    fixed_languages = [lang["index"] for lang in (bg.get("languages", []) if bg else [])] + \
        [lang["index"] for lang in (race.get("languages", []) if race else [])] + \
        _feat_languages([f for f in resolved_feats if not _feat_build_position(f, lang_class_order)]) + \
        class_choices_2024.fixed_origin_languages(ruleset)  # C8: Common
    positioned_languages = class_choices_2024.fixed_class_language_entries(catalog, resolved_classes, ruleset) + [
        (pos, lang["index"]) for f in resolved_feats if (pos := _feat_build_position(f, lang_class_order))
        for lang in f.get("languages", [])]
    pruned += class_choices_2024.gate_languages(choices, fixed_languages, lang_class_order, positioned_languages)

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
        if hp_type == "manual" and isinstance(rc_hp_rolls_raw, dict):
            # Round-2 F11: a roll outside 1..hit die is replaced by the average
            # (derived.hit_point_gain_per_level) - say so instead of staying silent.
            first_rolled_level = 2 if not hp_class_entries else 1
            for lvl in range(first_rolled_level, rc["level"] + 1):
                if str(lvl) not in rc_hp_rolls_raw:
                    continue
                roll = rc_hp_rolls_raw[str(lvl)]
                if not (isinstance(roll, int) and not isinstance(roll, bool) and 1 <= roll <= rc_hit_die):
                    warnings.append({
                        "id": f"hp-roll-invalid-{rc['cls_id']}-{lvl}",
                        "message": msg("hp-roll-invalid", cls=rc["cls_id"], level=lvl, die=rc_hit_die),
                    })
        hp_class_entries.append({"hit_die": rc_hit_die, "level": rc["level"], "hp_rolls": rc_hp_rolls})
    class_feature_list = _class_feature_list(catalog, resolved_classes, choices, resolved_feats)
    effects = (features_mod.class_effects(class_feature_list, xphb_effects) + invocation_effects
               + subclass_options_2024.effects(choices)  # RP13 Aspect of the Wilds, Elemental Affinity
               + subclass_options_2024.ward_effects(catalog, resolved_classes, choices))  # RP17 Nature's Ward
    # R5: Diamond Soul / Slippery Mind grants (the latter depends on the ruleset).
    for ab in features_mod.save_proficiencies(effects, [idx for _, _, idx in class_feature_list], ruleset):
        if ab not in proficient_save_abilities:
            proficient_save_abilities.append(ab)
    pruned += _gate_save_picks(  # RP12 Iron Mind
        choices, catalog, resolved_classes, resolved_feats, class_feature_list, xphb_effects, ruleset,
        [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])], proficient_save_abilities)
    saves = derived_mod.saving_throws(modifiers, proficient_save_abilities, prof_bonus)
    aura = features_mod.save_bonus(effects, modifiers)  # R5: Aura of Protection
    if aura:
        saves = {ab: value + aura for ab, value in saves.items()}
    class_levels = {rc["cls_id"]: rc["level"] for rc in resolved_classes if rc["cls"]}
    jack, remarkable = features_mod.half_proficiency(effects)
    # F-D9 (FX refinement): XPHB Jack of All Trades covers only checks that use a skill proficiency you lack
    # (never Initiative). Remarkable Athlete is left as it was in every ruleset: only the SRD feature id is
    # mapped, and the XPHB Champion never carried the effect.
    initiative_jack, initiative_remarkable = jack, remarkable
    if ruleset == "2024":
        initiative_jack = False
    poe_expertise = [sel for c in choices if c["id"] in poe_priors for sel in c["selected"] if sel in poe_priors[c["id"]]]
    expertise_all = list(dict.fromkeys(
        _feat_expertise_skills(resolved_feats) + _expertise_selected_values(choices) + poe_expertise))
    skills = derived_mod.skill_scores(
        modifiers, list(proficient_skills), prof_bonus, expertise_all, jack, remarkable,
    )
    # C6a Thaumaturge / Magician: bonus = max(minimum, WIS modifier) on the listed INT skills,
    # added to the skill totals (never to passive checks, none of these skills has one).
    for effect in class_choices_2024.selected_class_option_effects(choices):
        bonus = effect.get("skill_bonus")
        if bonus:
            amount = max(bonus["minimum"], modifiers[bonus["ability"]])
            for skill_id in bonus["skills"]:
                skills[skill_id] += amount
    speeds = _species_speeds(race, subrace, species_variant)
    worn_armor = any(i.get("equipment_category", {}).get("index") == "armor" for i in equipped_items)  # body armor or shield
    if speeds and not worn_armor:
        speeds = _raise_walk_speed(speeds, features_mod.speed_bonus(effects, class_levels))  # Unarmored Movement
    fast = features_mod.speed_bonus_unless_heavy(effects, equipped_items)  # R5: Fast Movement
    if speeds and fast:
        speeds = _raise_walk_speed(speeds, fast)
    if speeds and features_mod.speed_bonus_flat(effects):  # RP2 Glory 7 Aura of Alacrity
        speeds = _raise_walk_speed(speeds, features_mod.speed_bonus_flat(effects))
    feat_inst = feat_effects_mod.instances(resolved_feats, feat_effects_data.FEAT_EFFECTS, choices)  # FE1
    if speeds and feat_effects_mod.walk_bonus(feat_inst):  # Mobile, Speedy, Boon of Speed, ... (walk only)
        speeds = _raise_walk_speed(speeds, feat_effects_mod.walk_bonus(feat_inst))
    speed_exempt = _heavy_armor_speed_exempt(race, subrace)  # W1
    speeds = _heavy_armor_speed_penalty(  # W1: after every walk bonus, before the "equal to your walking speed" modes
        speeds, 0 if speed_exempt else equipment_mod.armor_speed_penalty(
            equipped_items, final_scores, equipment_mod.counted_body_armor_id(equipped_items)))  # WH: the suit AC counts
    if speeds.get("walk"):  # WF: species "equal to your walking speed" modes follow the FINAL walk (bonuses, penalty)
        for mode in _species_equal_walk_modes(race, subrace):
            speeds = {**speeds, mode: speeds["walk"]}
    fly_bans = equipment_mod.fly_armor_bans(  # X1: "can't use this flying speed" in medium / heavy armor (the counted suit)
        race, subrace, equipped_items, equipment_mod.counted_body_armor_id(equipped_items))
    if fly_bans:
        speeds = {mode: value for mode, value in speeds.items() if mode != "fly"}
    if speeds.get("walk") and features_mod.swim_equals_walk(effects):  # C7b Gift of the Depths
        speeds = {**speeds, "swim": max(speeds.get("swim", 0), speeds["walk"])}
    if speeds.get("walk") and features_mod.climb_equals_walk(effects):  # RP2 Thief, Roving
        speeds = {**speeds, "climb": max(speeds.get("climb", 0), speeds["walk"])}
    if speeds.get("walk") and feat_effects_mod.climb_equals_walk(feat_inst):  # FE1 Athlete (XPHB)
        speeds = {**speeds, "climb": max(speeds.get("climb", 0), speeds["walk"])}
    feat_init_bonus, feat_init_pb = feat_effects_mod.initiative_parts(feat_inst)
    base_speed = speeds.get("walk")
    # Attacks, carrying capacity and armor warnings (Slice 9). Size is the
    # selected species size (Slice 8d), else the race's own, else Medium.
    weapon_proficiencies = proficient_armor | proficient_weapons
    feat_numbers = feat_effects_mod.numbers_for(modifiers, final_scores, prof_bonus, sum(class_levels.values()))  # FE3
    attacks = attacks_mod.attacks_from_gear(
        equipped_items, modifiers, prof_bonus, proficient_weapons,
        {**features_mod.attack_styles(effects), **feat_effects_mod.attack_flags(feat_inst)},  # FE5 off-hand attacks, Finesse
        gear.hands, pact_weapon=pact_weapon_id,
    )
    class_resources = class_resources_mod.resources_for(
        catalog, resolved_classes, modifiers, prof_bonus, ruleset, choices=choices, warnings_out=warnings)
    is_monk = class_levels.get("monk", 0) >= 1
    martial_arts = next((r for r in class_resources if r["id"] == "monk:martial-arts"), None) if is_monk else None
    martial_arts_die = martial_arts and martial_arts.get("die")
    feat_unarmed = feat_effects_mod.unarmed_spec(feat_inst, gear.hands, equipped_items, martial_arts_die, monk=is_monk)  # FE5, F-D6
    if is_monk or feat_unarmed:  # R2: the Monk's unarmed strike (never deduped against gear); FE5: or a feat's
        attacks = attacks + [attacks_mod.unarmed_strike(modifiers, prof_bonus, martial_arts_die, feat_unarmed, monk=is_monk)]
    attacks = class_resources_mod.annotate_attacks(attacks, class_resources, equipped_items)
    if pact_weapon_id:  # C7c: Thirsting Blade, Eldritch Smite, ... notes on the pact weapon's row
        pact_notes = class_choices_2024.pact_weapon_row_notes(
            [sel for _cls, sel in features_mod.selected_invocation_ids(choices)] + features_mod.selected_feat_invocation_ids(choices))
        attacks = [{**a, "notes": a["notes"] + [n for n in pact_notes if n not in a["notes"]]} if a["itemId"] == pact_weapon_id else a
                   for a in attacks]
    attacks = feat_effects_mod.annotate_attacks(attacks, equipped_items, feat_inst, feat_numbers)  # FE5 (F-D2 notes)
    weapon_masteries = _weapon_masteries(choices, catalog)
    attacks = attacks_mod.annotate_mastery(attacks, weapon_masteries)  # C2
    armor_problems, stealth_disadvantage = equipment_mod.armor_warnings(
        equipped_items, final_scores, weapon_proficiencies, feat_effects_mod.medium_armor_stealth_ok(feat_inst), speed_exempt,
        equipment_mod.counted_body_armor_id(equipped_items))  # FE4, W1, WH
    warnings += armor_problems
    warnings += [equipment_mod.fly_armor_warning(ban) for ban in fly_bans]  # X1
    carrying = derived_mod.carrying_summary(
        final_scores.get("STR", 10), species_size or (race or {}).get("size") or "Medium",
        granted_equipment + chosen_equipment + added_resolved, catalog.items,
        ({**reference_data.ITEM_WEIGHTS_2024, **{k: v["weight"] for k, v in reference_data.PACKS_2024.items()}}
         if ruleset == "2024" else derived_mod.pack_weights_from_contents(catalog.items)),  # RPX2: SRD packs = contents sum
    )
    feat_passive = feat_effects_mod.passive_bonus(feat_inst)  # FE4 Observant (PHB): passive scores only
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_multiclass(hp_class_entries, modifiers["CON"], hp_type)
        + features_mod.hp_bonus(effects, class_levels)
        + sum(e.get("hp_per_level", 0) for e in _srd_trait_effects(race, subrace)) * sum(class_levels.values())
        + feat_effects_mod.hp_bonus(feat_inst, sum(class_levels.values())),
        "hitDice": " + ".join(f"{rc['level']}d{rc['cls']['hit_die']}" for rc in resolved_classes if rc["cls"] and rc["cls"].get("hit_die")) or None,
        "armorClass": equipment_mod.armor_class_from_gear(
            equipped_items, modifiers["DEX"], features_mod.ac_formulas(effects) + feat_effects_mod.ac_formulas(feat_inst),
            modifiers, features_mod.armored_ac_bonus(effects),
            medium_dex_cap=feat_effects_mod.medium_armor_dex_cap(feat_inst, final_scores.get("DEX", 10)),  # FE4
        ) + feat_effects_mod.ac_bonus(feat_inst, gear.hands, equipped_items),  # FE4 (needs equipment.wielded)
        "speed": base_speed,  # walking speed; `speeds` carries every mode
        "speeds": speeds,
        "initiative": derived_mod.initiative(modifiers, prof_bonus, initiative_jack, initiative_remarkable,
                                         feat_init_bonus + features_mod.class_initiative_bonus(effects, modifiers), feat_init_pb),
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills) + feat_passive.get("skill-perception", 0),
        "passiveInsight": derived_mod.passive_skill(skills, "skill-insight"),
        "passiveInvestigation": derived_mod.passive_skill(skills, "skill-investigation")
        + feat_passive.get("skill-investigation", 0),
        "spellSlots": spell_slots,
        "warlockSpellSlots": warlock_slots,
        "slotGrantingClasses": slot_granting_class_ids,
        "attacks": attacks,
        "attacksPerAction": class_resources_mod.attacks_per_action(resolved_classes),
        "classResources": class_resources,
        "featResources": feat_effects_mod.resources(feat_inst, feat_numbers),  # FE3
        "speciesResources": species_resources_mod.resources(  # W5a, W5b (choices: SRD Dragonborn ancestry, PHB resistance pick)
            catalog, race, race_id, subrace, species_variant, sum(class_levels.values()), prof_bonus, modifiers, base_speed,
            choices),
        "carryingCapacity": carrying,
        "stealthDisadvantage": stealth_disadvantage,
    }

    # fixed_languages: computed with the class language gate above (Phase 4c-i Task 6 feat grants included)
    chosen_languages = [
        s for c in choices
        if (c["source"]["kind"] in ("background", "species", "feat") and c["id"].endswith(":languages"))
        or class_choices_2024.is_class_language_card(c)  # C6b-2
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
    chosen_resistances += features_mod.class_resistances(effects)  # RP2
    chosen_resistances += feat_effects_mod.resistances(  # FE7: resistance picks of the held feats (Scion follows its plane)
        feat_effects_mod.instances(resolved_feats, feat_effects_data.FEAT_EFFECTS, choices))
    damage_modifiers = _species_damage_modifiers(race, subrace, resolved_feats, chosen_resistances)
    condition_immunities = _species_condition_immunities(race, subrace, resolved_feats)
    for cond in features_mod.class_condition_immunities(effects):  # RPF Archfey 10, Nature's Ward
        if cond not in condition_immunities:
            condition_immunities.append(cond)
    senses = _species_senses(race, subrace, catalog, species_variant)
    for sense_kind, sense_range in _feat_senses(resolved_feats).items():
        if sense_range > senses.get(sense_kind, 0):
            senses[sense_kind] = sense_range
    for sense_kind, sense_range in features_mod.invocation_senses(invocation_effects).items():  # R8
        if sense_range > senses.get(sense_kind, 0):
            senses[sense_kind] = sense_range
    senses = feat_effects_mod.add_senses(senses, feat_inst)  # FE4 Keenness of the Stone Giant (adds to the final range)
    senses = features_mod.class_senses(senses, effects)  # RP2 Darkvision +60, Blindsight 30
    innate_spells = (_species_innate_spells(race, subrace, catalog, species_variant)
                     + _species_trait_spell_choices(race, subrace, catalog, choices)
                     + _feat_innate_spells(resolved_feats, catalog, choices, feat_effects_mod.innate_patches(feat_inst, feat_numbers), follow_variants=variant_follow)
                     + [{**_innate_entry_to_sheet(e, catalog), "featId": e["featId"], "source": e["source_label"], "note": e["note"]}  # RP19
                        for e in feat_spell_tables.adept_entries(resolved_feats, feat_spell_tables.highest_slot_level(spell_slots, warlock_slots))]
                     + [{**_innate_entry_to_sheet(e, catalog), "source": e["source_label"],
                         **({"note": e["note"]} if e.get("note") else {})}
                        for e in features_mod.invocation_innate_entries(invocation_effects) + features_mod.feat_tome_entries(choices)]
                     + [{**_innate_entry_to_sheet(e, catalog), "source": e["source_label"],  # RP18
                         **({"note": e["note"]} if e.get("note") else {})}
                        for e in subclass_innate_2024.innate_entries(catalog, resolved_classes, ruleset, modifiers)])
    innate_spells = [innate_uses.with_limit(e) for e in innate_spells]  # G6: usesMax + recharge from the `uses` text

    refs_by_class = {
        rc["cls_id"]: _cumulative_feature_refs(catalog, rc["cls_id"], rc["subclass_id"], rc["level"])
        for rc in resolved_classes if rc["cls"] and rc["cls_id"]
    }
    sheet_feats = sheet_features_mod.feats_summary(resolved_feats, choices, feat_effects_mod.notes(feat_inst, feat_numbers))

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
            "size": species_size,
        } if race else None,
        "abilities": final_scores,
        "proficiencies": {
            "skills": sorted(proficient_skills),
            "savingThrows": proficient_save_abilities,
            "languages": sorted(set(fixed_languages + [lang for _pos, lang in positioned_languages] + chosen_languages)),
            "armor": sorted(proficient_armor),
            "weapons": sorted(proficient_weapons),
            "tools": sorted(proficient_tools),
        },
        "startingGold": starting_gold,
        "equipment": {
            "granted": granted_equipment, "chosen": chosen_equipment, "added": added_resolved,
            "narrativeItems": narrative_items, "slots": gear.slots,
            **({"worn": gear.worn} if gear.worn else {}), **({"wielded": gear.wielded} if gear.wielded else {}),
        },
        "spells": spells_summary,
        "details": details,
        "damageModifiers": damage_modifiers,
        "conditionImmunities": condition_immunities,
        "innateSpells": innate_spells,
        # Background grants keep their bare-slug ids (unchanged); a feat
        # taken at an ASI level is appended by its full catalog index
        # (e.g. "actor-xphb") — the exact id it was selected by.
        "grantedFeats": granted_feats + [f["index"] for f in species_feats] + [f["index"] for f in fs_feats] + [f["index"] for f in lessons_feats] + [f["index"] for f in asi_selected_feats],
        "featOptions": feat_options,
        "senses": senses,
        "expertiseSkills": expertise_all,
        "features": sheet_features_mod.build_features(
            catalog, resolved_classes, refs_by_class, race, race_id, subrace, bg, bg_id, resolved_feats, choices,
            ruleset=ruleset,
        ),
        "feats": sheet_feats,
        "weaponMasteries": weapon_masteries,
    }

    choices = class_choices_2024.mark_unavailable(choices, ruleset)  # F3a-2b: uncompletable new 2024 cards do not block
    choices = option_source_mod.annotate_choices(catalog, choices)  # SK10 (Y2): `source` on feat / spell / feature options

    if len(pruned) > MAX_PRUNED_REPORTED:  # F2-D: cap last, so every gate's entries count and the marker ends the list
        extra = len(pruned) - MAX_PRUNED_REPORTED
        pruned = pruned[:MAX_PRUNED_REPORTED] + [{
            "choiceId": "pruned-more",
            "reason": msg("pruned-more", extra=extra),
        }]

    return {
        "sheet": sheet,
        # F2-C: `count_by_level` is an internal template key (count-variable test), not API shape.
        "choices": [{k: v for k, v in c.items() if k not in ("count_by_level", "lacksExpertise", "profOrExpertise", "distinctGroup", "distinctFixed")} for c in choices],
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": pruned,
    }
