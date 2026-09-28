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

from catalog.choices import build_choice_template
from catalog.loader import Catalog
from catalog.official_source import slug
from . import asi as asi_mod
from . import derived as derived_mod
from . import equipment as equipment_mod
from . import spells as spells_mod

_DETAIL_FIELDS = (
    "alignment", "faith", "lifestyle",
    "age", "height", "weight", "eyes", "skin", "hair",
    "personalityTraits", "ideals", "bonds", "flaws",
    "backstory", "organizations", "allies", "enemies", "notes",
)


def _species_ability_bonuses(race: dict | None, subrace: dict | None) -> dict[str, int]:
    bonuses: dict[str, int] = {}
    for src in (race, subrace):
        if not src:
            continue
        for entry in src.get("ability_bonuses", []):
            ab = entry["ability_score"]["index"].upper()
            bonuses[ab] = bonuses.get(ab, 0) + entry["bonus"]
    return bonuses


def _species_damage_modifiers(race: dict | None, subrace: dict | None, feats: list[dict] | None = None) -> dict[str, list[str]]:
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
    efa"). This is the ONLY mechanism resolve() has today to know a
    character actually "has" a feat: no ASI-feat-choice or standalone
    feat-selection exists yet (confirmed by grep, 2026-09-28) — a
    background's `feats` field, previously pure inert pass-through
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


def _species_innate_spells(race: dict | None, subrace: dict | None, catalog: Catalog) -> list[dict]:
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
            spell = catalog.spells.get(entry["spell_id"])
            innate.append({
                "spellId": entry["spell_id"] if spell else None,
                "name": spell["name"] if spell else entry["name"],
                "level": entry["level"],
                "uses": entry["uses"],
                "ability": entry["ability"],
                "variant": entry["variant"],
            })
    return innate


def _species_ability_bonus_choice_template(race: dict | None, subrace: dict | None, race_id: str | None) -> dict | None:
    """Half-Elf's ability_bonus_options (the only race/subrace in the
    bundled data with this field) needs a real Choice — this builds its
    template. Race is checked before subrace since ability_bonus_options
    could in principle appear on either (only race does in the bundled
    data, but this stays generic rather than hardcoding "half-elf")."""
    for src in (race, subrace):
        if not src or not src.get("ability_bonus_options"):
            continue
        envelope = src["ability_bonus_options"]
        cid = f"species:{race_id}:ability-bonus"
        source = {"kind": "species", "id": race_id, "label": race["name"] if race else ""}
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} ability score{'s' if choose != 1 else ''} to increase by 1."
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
        deltas_by_id[built_opt["id"]] = [
            (item["ability_score"]["index"].upper(), item["bonus"])
            for item in raw_opt.get("items", [])
        ]
    return deltas_by_id


def _feat_ability_bonus_choice_templates(feats: list[dict]) -> list[tuple[dict, dict]]:
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
    format is written."""
    pairs: list[tuple[dict, dict]] = []
    for feat in feats:
        envelope = feat.get("ability_bonus_options")
        if not envelope:
            continue
        cid = f"feat:{feat['index']}:ability-bonus"
        source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
        choose = envelope.get("choose", 1)
        description = f"Choose {choose} ability score{'s' if choose != 1 else ''} to increase by 1."
        tpl = build_choice_template(envelope, cid, source, "Ability Score Increase", description=description)
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


def _apply_asi_progression(
    base_scores: dict[str, int], asi_levels: list[int], class_choices: dict, cls_id: str | None,
) -> tuple[dict[int, dict[str, int]], dict[str, int]]:
    """Walks ASI-granting levels in ascending order, applying each
    level's stored selection (if present and valid) to a running
    ability-score state. Returns (scores_by_level, final_scores):
    scores_by_level[lvl] is the state BEFORE that level's own ASI is
    applied (used by _asi_choice_templates to compute which options are
    disabled for that specific level's choice — a combo that's fine at
    level 4 might exceed the cap by level 8 once earlier ASIs stack),
    and final_scores is the state after every level's ASI has been
    applied — this becomes the actual final ability scores used for
    `modifiers` and everything derived from them."""
    combos = dict(asi_mod.asi_combinations())
    scores_by_level: dict[int, dict[str, int]] = {}
    running = dict(base_scores)
    for lvl in asi_levels:
        scores_by_level[lvl] = dict(running)
        cid = f"class:{cls_id}:{lvl}:asi"
        raw_selected = class_choices.get(cid) or []
        if isinstance(raw_selected, list) and len(raw_selected) == 1 and raw_selected[0] in combos:
            deltas = combos[raw_selected[0]]
            if not asi_mod.asi_exceeds_cap(deltas, running):
                running = asi_mod.apply_asi(deltas, running)
    return scores_by_level, running


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
    return refs


def _feature_choice_templates(
    catalog: Catalog, cls_id: str, cls_name: str, feature_refs: list[tuple[int, dict]], subclass_id: str | None,
) -> list[dict]:
    templates = []
    for lvl, ref in feature_refs:
        feature = catalog.features.get(ref["index"])
        if not feature:
            continue
        feature_subclass = feature.get("subclass")
        if feature_subclass and feature_subclass.get("index") != subclass_id:
            continue  # subclass-gated to a different subclass than the one selected (or none selected)
        envelope = (feature.get("feature_specific") or {}).get("subfeature_options")
        if not envelope:
            continue
        cid = f"class:{cls_id}:{lvl}:feature:{feature['index']}"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        # The subfeature_options envelope itself has no 'desc' key — the
        # description text lives on the parent feature (verified directly
        # against 5e-SRD-Features.json), so it must be passed explicitly.
        tpl = build_choice_template(envelope, cid, source, feature["name"], description=_join_desc(feature.get("desc")))
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


def _feat_choice_templates(feats: list[dict]) -> list[dict]:
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
    to recognize a feat-sourced proficiency or language selection."""
    templates = []
    for feat in feats:
        language_envelope = feat.get("language_options")
        if language_envelope:
            cid = f"feat:{feat['index']}:languages"
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            choose = language_envelope.get("choose", 1)
            description = f"Choose {choose} language{'s' if choose != 1 else ''} of your choice."
            tpl = build_choice_template(language_envelope, cid, source, "Languages", description=description)
            if tpl:
                templates.append(tpl)

        for i, prof_envelope in enumerate(feat.get("proficiency_choices", []) or []):
            cid = f"feat:{feat['index']}:proficiency-choice-{i}"
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            label = _background_proficiency_choice_label(prof_envelope)
            choose = prof_envelope.get("choose", 1)
            description = f"Choose {choose} proficienc{'ies' if choose != 1 else 'y'} of your choice."
            tpl = build_choice_template(prof_envelope, cid, source, label, description=description)
            if tpl:
                templates.append(tpl)
    return templates


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

    return templates


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


# The set of feat-prerequisite keys this app can actually verify — see
# _feat_structured_prerequisite's own docstring for the full real-data
# grounding (85/305 real feats carry a prerequisite made ENTIRELY of these
# two keys; every other real key — campaign, other, otherSummary,
# feature, race, proficiency, feat, background, spellcasting/
# spellcasting2020/spellcastingFeature, featCategory/
# exclusiveFeatCategory — is left unmodeled and never enforced).
_STRUCTURED_FEAT_PREREQUISITE_KEYS = {"level", "ability"}


def _feat_structured_prerequisite(feat: dict) -> list[dict] | None:
    """Returns feat["prerequisite"] (a 5etools-shaped list of alternative
    requirement objects — met if ANY ONE alternative is fully met, exactly
    like multi_classing.prerequisite_options' own "choose N of these"
    OR-semantics above) when EVERY alternative in it consists SOLELY of
    "level" and/or "ability" keys — the only two prerequisite shapes this
    app can verify against final_scores/total_level. Returns None (no
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

    85/305 real feats (2026-09-28) are entirely level/ability — everything
    from single-alternative ("Ability Score Improvement": level 4 only) to
    multi-alternative OR shapes (Athlete/Charger/Grappler/etc.: level 4 +
    (STR 13 OR DEX 13), two separate alternative objects) — both are
    handled identically by _feat_prerequisite_alt_met's own per-alternative
    check below."""
    prereq = feat.get("prerequisite") or []
    if not prereq:
        return None
    if not all(
        isinstance(alt, dict) and set(alt.keys()) <= _STRUCTURED_FEAT_PREREQUISITE_KEYS
        for alt in prereq
    ):
        return None
    return prereq


def _feat_prerequisite_alt_met(alt: dict, total_level: int, final_scores: dict[str, int]) -> bool:
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
    return True


def _feat_prerequisite_problems(
    feats: list[dict], total_level: int, final_scores: dict[str, int], use_prerequisites: bool,
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
    counts, since it isn't F's own contribution being subtracted."""
    if not use_prerequisites:
        return []
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
        if not any(_feat_prerequisite_alt_met(alt, total_level, scores_without_own_bonus) for alt in prereq):
            problems.append({
                "id": f"feat-prerequisite-unmet-{feat['index']}",
                "message": f"{feat['name']}'s prerequisite isn't met.",
            })
    return problems


def _asi_option_label(deltas: list[tuple[str, int]]) -> str:
    return " and ".join(f"{ab} +{delta}" for ab, delta in deltas)


def _asi_choice_templates(
    cls_id: str, cls_name: str, asi_levels: list[int], scores_by_level: dict[int, dict[str, int]],
) -> list[dict]:
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
        cid = f"class:{cls_id}:{lvl}:asi"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": "Ability Score Improvement",
            "description": "Increase one ability score by 2, or two ability scores by 1 each.",
            "count": 1,
            "options": options,
        })
    return templates


def _equipment_choice_templates(entity: dict, source_kind: str, source_id: str, source_label: str) -> tuple[list[dict], int]:
    templates = []
    dropped_envelopes = 0
    for i, envelope in enumerate(entity.get("starting_equipment_options", [])):
        cid = f"{source_kind}:{source_id}:1:equipment-choice-{i}" if source_kind == "class" else f"{source_kind}:{source_id}:equipment-choice-{i}"
        source = {"kind": "equipment", "id": source_id, "label": source_label}
        if source_kind == "class":
            source["level"] = 1
        tpl = build_choice_template(envelope, cid, source, "Starting Equipment")
        if not tpl:
            dropped_envelopes += 1
            continue
        original_option_count = len((envelope.get("from") or {}).get("options", []))
        if original_option_count and len(tpl["options"]) < original_option_count:
            tpl["description"] = (tpl["description"] + " (Note: one or more of the original options for this choice aren't available yet and have been left out.)").strip()
        templates.append(tpl)
    return templates, dropped_envelopes


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


def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int, class_level: int,
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
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": _spell_options_up_to(catalog, cls_id, max_spell_level),
        }}
        cid = f"class:{cls_id}:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None
        label = "Spells Known" if is_known_caster else "Prepared Spells"
        verb = "know" if is_known_caster else "prepare"
        level_word = "spell" if max_spell_level == 1 else f"level-{max_spell_level}-or-lower spell"
        description = f"Choose {known_count} {level_word}{'s' if known_count != 1 else ''} to {verb} from the {cls['name']} spell list."
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl:
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
        for opt in tpl["options"]:
            if opt["id"] in granted:
                opt["disabled"] = True
                opt["disabledReason"] = f"already granted by {race['name']}"


def resolve(draft: dict, catalog: Catalog) -> dict:
    problems: list[dict] = []
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
    resolved_feats = _resolve_granted_feats(granted_feats, catalog, granted_feat_refs)

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
    feat_bonuses = _feat_ability_bonuses(resolved_feats)
    base_scores = (draft.get("abilities") or {}).get("base") or {}
    species_bonuses = _species_ability_bonuses(race, subrace)
    species_ability_choice_tpl = _species_ability_bonus_choice_template(race, subrace, race_id)
    if species_ability_choice_tpl:
        species_choices_raw = species.get("choices") if isinstance(species.get("choices"), dict) else {}
        valid_ability_ids = {o["id"] for o in species_ability_choice_tpl["options"] if not o.get("disabled")}
        raw_selected = species_choices_raw.get(species_ability_choice_tpl["id"]) or []
        # Dedupe BEFORE capping to `count` and applying bonuses — otherwise a
        # duplicate selection (e.g. ["str", "str"]) would apply the same
        # ability's bonus twice with no problem reported.
        deduped_selected = list(dict.fromkeys(s for s in raw_selected if isinstance(s, str)))
        selected_abilities = [s for s in deduped_selected if s in valid_ability_ids][: species_ability_choice_tpl["count"]]
        for ab_id in selected_abilities:
            ab_key = ab_id.upper()
            species_bonuses[ab_key] = species_bonuses.get(ab_key, 0) + 1  # bundled data's `bonus` is always 1; if a future data source varies this, look it up from the option instead of hardcoding 1 here

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
    feat_ability_choice_pairs = _feat_ability_bonus_choice_templates(resolved_feats)
    feat_ability_choice_tpls = [tpl for tpl, _ in feat_ability_choice_pairs]
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
            for ab_id in selected_feat_abilities:
                for ab_key, delta in feat_ability_deltas.get(ab_id, []):
                    feat_bonuses[ab_key] = feat_bonuses.get(ab_key, 0) + delta

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
        rc_cls, rc_cls_id, rc_level, rc_subclass_id = rc["cls"], rc["cls_id"], rc["level"], rc["subclass_id"]
        rc_class_choices = rc["class_choices"]
        if not (rc_cls and rc_cls_id):
            continue
        rc_asi_levels = _asi_granting_levels(catalog, rc_cls_id, rc_level)
        rc_asi_scores_by_level, final_scores = _apply_asi_progression(final_scores, rc_asi_levels, rc_class_choices, rc_cls_id)
        rc["asi_levels"] = rc_asi_levels  # stashed for Task 4's prerequisite check convenience, and for sheet assembly

        if rc["index"] == 0:
            choice_templates += _class_choice_templates(rc_cls, rc_cls_id)
        else:
            choice_templates += _multiclass_proficiency_choice_templates(rc_cls, rc_cls_id)
        rc_level_row = catalog.class_level_row(rc_cls_id, rc_level)
        rc["level_row"] = rc_level_row
        feature_refs = _cumulative_feature_refs(catalog, rc_cls_id, rc_subclass_id, rc_level)
        choice_templates += _feature_choice_templates(catalog, rc_cls_id, rc_cls["name"], feature_refs, rc_subclass_id)
        choice_templates += _asi_choice_templates(rc_cls_id, rc_cls["name"], rc_asi_levels, rc_asi_scores_by_level)

    use_prerequisites_prefs = (draft.get("preferences") or {}).get("usePrerequisites", {})
    use_prereqs = bool(use_prerequisites_prefs.get("multiclass"))
    problems += _multiclass_prerequisite_problems(resolved_classes, final_scores, use_prereqs)
    # Phase 4c-i Task 6: a NEW sibling key on the SAME usePrerequisites
    # dict the multiclass toggle already uses (confirmed fresh, this task
    # — `use_prerequisites_prefs` above is that exact dict), not a
    # separate preferences shape. `final_scores` here is already
    # POST-ASI-progression (the loop above reassigns it via
    # _apply_asi_progression before this line runs), matching what a
    # player's actual final character sheet shows.
    use_feat_prereqs = bool(use_prerequisites_prefs.get("feats"))
    problems += _feat_prerequisite_problems(resolved_feats, total_level, final_scores, use_feat_prereqs)

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
            choice_templates += _spell_choice_templates(catalog, rc_cls, rc_cls_id, rc_level_row, modifiers[spell_ability], class_level=rc_level)

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
    choice_templates += _feat_choice_templates(resolved_feats)
    # Phase 4c-ii Task 2: `feat_ability_choice_tpls` was already built (and
    # applied to `feat_bonuses`) EARLY, in the "Final ability scores"
    # section above — appended here, unconditionally, mirroring exactly how
    # background_ability_choice_tpl/species_ability_choice_tpl (also built
    # early) get appended to choice_templates at their own call sites,
    # rather than rebuilding the templates a second time here.
    choice_templates += feat_ability_choice_tpls
    if race and race_id:
        choice_templates += _species_choice_templates(catalog, race, race_id, subrace)
        if species_ability_choice_tpl:
            choice_templates.append(species_ability_choice_tpl)
    if cls and cls_id:
        cls_equipment_templates, cls_dropped = _equipment_choice_templates(cls, "class", cls_id, cls["name"])
        choice_templates += cls_equipment_templates
        if cls_dropped:
            warnings.append({
                "id": f"equipment-envelope-dropped-class-{cls_id}",
                "message": f"{cls['name']}'s starting equipment has {cls_dropped} choice(s) that can't be shown yet and were left out.",
            })
    if bg and bg_id:
        bg_equipment_templates, bg_dropped = _equipment_choice_templates(bg, "background", bg_id, bg["name"])
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
        if len(selected) > tpl["count"]:
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
        if not (rc_cantrip_choice or rc_known_spells_choice):
            continue
        rc_spell_ability = spells_mod.spellcasting_ability(rc_cls)
        rc_save_dc = spells_mod.spell_save_dc(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        rc_attack_bonus = spells_mod.spell_attack_bonus(prof_bonus, modifiers[rc_spell_ability]) if rc_spell_ability else None
        spells_summary.append({
            "classId": rc_cls_id,
            "cantrips": _spell_summaries(rc_cantrip_choice),
            "known": _spell_summaries(rc_known_spells_choice),
            "spellSaveDC": rc_save_dc,
            "spellAttackBonus": rc_attack_bonus,
        })

    # Spell-slot pool (Phase 3b-ii, fixed post-review): per PHB 164, the
    # COMBINED multiclass table (full casters contribute their own level,
    # half casters level // 2, looked up in a full caster's own table) is
    # only the correct rule when MORE THAN ONE class actually grants spell
    # slots. A character with exactly one slot-granting class — even
    # alongside other non-caster classes (e.g. Fighter/Paladin) — uses
    # that ONE class's own single-class progression directly; rounding a
    # lone half caster's level down and looking it up in the shared table
    # silently undercounts its slots at every odd level. Warlock's Pact
    # Magic is always looked up separately at Warlock's OWN class level,
    # never folded into either path above, per RAW (see engine/spells.py's
    # PACT_MAGIC_CLASSES/warlock_pact_magic_slots docstrings).
    caster_level_entries = [(rc["cls_id"], rc["level"]) for rc in resolved_classes if rc["cls"]]
    # Classification by class-id set membership alone (cls_id in
    # FULL_CASTER_CLASSES | HALF_CASTER_CLASSES) is wrong: a half caster
    # (Paladin/Ranger) has no Spellcasting feature at all until level 2, so
    # a level-1 Paladin/Ranger grants ZERO slots despite being in
    # HALF_CASTER_CLASSES. The real test is whether the class ACTUALLY
    # grants a nonzero slot table at its own current level —
    # single_class_spell_slots returns {} (falsy) when it doesn't, so this
    # list comprehension counts only classes with a genuine, current slot
    # grant (fixed post-final-review; see docstring above). Warlock (and
    # any other PACT_MAGIC_CLASSES) is excluded here too: its own class-
    # level row DOES carry nonzero spell_slots_level_N entries (that's its
    # Pact Magic progression), but those must never be folded into this
    # shared pool — Warlock is handled entirely separately below.
    slot_granting_entries = [
        (cls_id, level) for cls_id, level in caster_level_entries
        if cls_id not in spells_mod.PACT_MAGIC_CLASSES
        and spells_mod.single_class_spell_slots(catalog, cls_id, level)
    ]
    if len(slot_granting_entries) == 1:
        only_cls_id, only_level = slot_granting_entries[0]
        spell_slots = spells_mod.single_class_spell_slots(catalog, only_cls_id, only_level)
    else:
        shared_combined_level = spells_mod.combined_caster_level(caster_level_entries)
        spell_slots = spells_mod.multiclass_spell_slots(catalog, shared_combined_level)
    warlock_entry = next((rc for rc in resolved_classes if rc["cls_id"] in spells_mod.PACT_MAGIC_CLASSES and rc["cls"]), None)
    warlock_level_row = catalog.class_level_row(warlock_entry["cls_id"], warlock_entry["level"])["spellcasting"] if warlock_entry else None
    warlock_slots = spells_mod.warlock_pact_magic_slots(warlock_level_row)

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
        if c["source"]["kind"] in ("class", "species", "background", "feat"):
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
    _SPECIFIC_WEAPON_PROFICIENCY_IDS = {
        "shortswords", "clubs", "crossbows-light", "daggers", "darts", "hand-crossbows",
        "javelins", "longswords", "maces", "quarterstaffs", "rapiers", "scimitars",
        "sickles", "slings", "spears",
        "battleaxes", "handaxes", "light-hammers", "warhammers", "shortbows", "longbows",
    }

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
        if rc["index"] == 0:
            for p in rc["cls"].get("proficiencies", []):
                _categorize_proficiency(p["index"])
        else:
            for p in rc["cls"].get("multi_classing", {}).get("proficiencies", []):
                _categorize_proficiency(p["index"])

    # Phase 4c-i Task 6: was class-only (primary class's saving_throws
    # field) — a granted feat's own FIXED saving-throw-proficiency grant
    # (see _feat_saving_throw_proficiencies' own docstring for why real
    # data contributes nothing here today) now extends this SAME list,
    # deduped so a feat naming an ability the class already covers
    # doesn't produce a duplicate entry in derived.savingThrows/
    # sheet.proficiencies.savingThrows.
    proficient_save_abilities = [st["index"].upper() for st in (cls.get("saving_throws", []) if cls else [])]
    for ab in _feat_saving_throw_proficiencies(resolved_feats):
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
    skills = derived_mod.skill_scores(modifiers, list(proficient_skills), prof_bonus)
    derived = {
        "abilityModifiers": modifiers,
        "proficiencyBonus": prof_bonus,
        "hitPointMax": derived_mod.hit_point_max_multiclass(hp_class_entries, modifiers["CON"], hp_type),
        "hitDice": " + ".join(f"{rc['level']}d{rc['cls']['hit_die']}" for rc in resolved_classes if rc["cls"] and rc["cls"].get("hit_die")) or None,
        "armorClass": equipment_mod.armor_class_from_gear(equipped_items, modifiers["DEX"]),
        "speed": race.get("speed") if race else None,
        "savingThrows": saves,
        "skills": skills,
        "passivePerception": derived_mod.passive_perception(skills),
        "spellSlots": spell_slots,
        "warlockSpellSlots": warlock_slots,
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
    damage_modifiers = _species_damage_modifiers(race, subrace, resolved_feats)
    condition_immunities = _species_condition_immunities(race, subrace, resolved_feats)
    senses = _feat_senses(resolved_feats)
    innate_spells = _species_innate_spells(race, subrace, catalog)

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
        "grantedFeats": granted_feats,
        "featOptions": feat_options,
        "senses": senses,
        "expertiseSkills": _feat_expertise_skills(resolved_feats),
    }

    return {
        "sheet": sheet,
        "choices": choices,
        "derived": derived,
        "problems": problems,
        "warnings": warnings,
        "pruned": pruned,
    }
