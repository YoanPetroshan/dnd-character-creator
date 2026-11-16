"""The feat helpers of resolve(): the feat pools, the ASI-or-feat walk, granted feats, option picks and their prerequisites.

Split from engine/resolve.py (S17); the text below is moved unchanged. `engine.resolve` re-exports every name.
"""
from __future__ import annotations

import re
from functools import lru_cache
from dataclasses import dataclass, field
from catalog import feat_effects_data
from catalog.choices import build_choice_template
from catalog.loader import Catalog
from i18n.messages import Msg, msg
from i18n.messages import msg as _format_msg
from catalog.official_source import slug, SAVE_ABILITY_NAMES
from catalog.reference_data import ruleset_allows
from . import asi as asi_mod
from . import class_choices_2024
from . import feat_effects as feat_effects_mod
from . import feat_spell_tables

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

def _base_holder(feat: dict, base: str, choices: list[dict], feats) -> dict | None:
    """The held copy of the base feat a dependent follows (RP5 / G5). F1: with several copies (Magic Initiate, a different
    list each time) it is the one whose list the dependent took; a copy whose list is fixed by its background has no
    stored pick, so it is the one left when no stored pick matches."""
    holders = [f for f in feats if f["index"] == base]
    if len(holders) < 2:
        return holders[0] if holders else None
    by_id = {c["id"]: c for c in choices}

    def picked(f):
        sel = (by_id.get(f"{_feat_cid_prefix(f)}:spell-variant") or {}).get("selected") or []
        return slug(sel[0]) if sel else None
    want = picked(feat)
    return (next((h for h in holders if want and picked(h) == want), None)
            or next((h for h in holders if picked(h) is None), None) or holders[0])

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
        other = _base_holder(feat, base, choices, feats)
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

_VISIBLE_SPELLS: dict = {}

def _visible_spell_ids(catalog: Catalog, sources, ruleset: str):
    """FX1: ids of the spells `_spell_visible` accepts, built once per (catalog, sources, ruleset) instead of
    once per `_spell_filter_options` call (6 per 2024 Bard 20 resolve over ~936 spells). The entry keeps a
    reference to the spells dict and its size, so a patched or reloaded catalog never reads a stale set.
    Returns None (caller falls back to per-spell checks) for unhashable `sources`."""
    try:
        key = (id(catalog.spells), len(catalog.spells), tuple(sorted(sources, key=str)) if sources else (), ruleset)
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
            candidates = getattr(follow_variants, "cards", {}).get(feat["index"])
            if candidates is not None:
                # F1: several base feats are held: the player chooses among the lists they picked
                offered_lists = [v for v in variants if slug(v) in candidates]
                templates.append({
                    "id": f"{prefix}:spell-variant", "source": source,
                    "label": msg("label-prefixed", head=feat["name"], tail=msg("label-spell-list")),
                    "description": msg("desc-spell-list"), "count": 1,
                    "options": [{"id": slug(v), "label": v} for v in offered_lists],
                })
            if chosen is None:
                continue
        elif variants:
            hinted = variant_hints.get(feat["index"])
            # VF4.1: a hint is a whole variant name (Magic Initiate "Cleric Spells") or the prefix of several (Strixhaven
            # Initiate "Lorehold" -> "Lorehold 1" .. "Lorehold 3": the college is fixed, the cantrip pair is still picked)
            offered = [v for v in variants if hinted and (v == hinted or v.startswith(f"{hinted} "))] or variants
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
                if tpl["options"] and all(o.get("disabled") for o in tpl["options"]):
                    # VF1.3: every score the feat may raise is already at its cap. PHB p.165 "Increase the chosen score by
                    # 1, to a maximum of 20": the +1 is simply lost, the feat is still taken. A card with no enabled
                    # option could never be settled (the character stayed blocked), so the options stay pickable; the
                    # pick changes nothing and the existing `pruned-ability-at-max` note says so.
                    for option in tpl["options"]:
                        option.pop("disabled", None)
                        option.pop("disabledReason", None)
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
    if isinstance(sources, frozenset):  # already lowercase (resolve() normalises draft.sources once)
        return source.lower() in sources
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

def _join_desc(desc) -> str | None:
    """Feature/trait 'desc' fields are lists of paragraph strings; choice
    envelopes never carry their own 'desc' except proficiency_choices (see
    Task 3's build_choice_template, which already handles a list there).
    This joins a parent object's desc for explicit passing as the
    'description' override, since the choice envelope itself has none."""
    if isinstance(desc, list):
        return " ".join(desc)
    return desc

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

# Feat categories offered at an ASI level, by ruleset (5etools codes: ""
# = the category-less 2014 books, G General, O Origin, EB Epic Boon).
# "2014" -> 2014 books + General (after ruleset_allows that is the Unearthed
# Arcana G feats); "2024" -> General + Origin; "mixed"/unknown -> all three.
# Epic Boons are added separately, only at slot level 19 and never under
# 2014. Fighting Style, Dragonmark and Dragon-gift categories stay out.
_ASI_FEAT_CATEGORIES = {"2014": {"", "G"}, "2024": {"G", "O"}}

_ASI_FEAT_CATEGORIES_DEFAULT = {"", "G", "O"}

_ASI_EPIC_BOON_LEVEL = 19

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

_PREREQ_MSG_MEMO: dict = {}

def _freeze_msg_param(value):
    if isinstance(value, Msg):
        return ("msg", value.key, str(value))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_msg_param(v) for v in value)
    return value

def _prereq_msg(key: str, /, **params) -> Msg:
    """VF7.4: `msg()` for the feat-prerequisite reasons, formatted once per distinct (key, params) and shared (a `Msg` is
    immutable text plus its key / params, the same instance is safe to hand to several options). The same reason repeats for
    every unmet feat at every ASI level, so formatting dominated the ASI templates (7,945 formats for one Fighter 19)."""
    key_ = (key, tuple((k, _freeze_msg_param(v)) for k, v in params.items()))
    hit = _PREREQ_MSG_MEMO.get(key_)
    if hit is None:
        if len(_PREREQ_MSG_MEMO) > 20000:
            _PREREQ_MSG_MEMO.clear()
        hit = _PREREQ_MSG_MEMO[key_] = _format_msg(key, **params)
    return hit

def _feat_prerequisite_unmet_reason(
    feat: dict, total_level: int, scores: dict[str, int], use_prerequisites: bool,
    held: "_HeldFeatState | None" = None, catalog: Catalog | None = None, prereq_memo: dict | None = None,
) -> str | None:
    """None when the ASI-level gate lets the feat through (prerequisites
    off, no structured prerequisite verifiable under
    _ASI_GATE_PREREQUISITE_KEYS, or any alternative met); otherwise
    "prerequisite not met", with ": requires ..." appended when there is
    exactly one alternative. Shared by the ASI walk and the option
    templates so the two always agree."""
    if not use_prerequisites:
        return None
    msg = _prereq_msg  # VF7.4: shared, formatted once per distinct (key, params); the call sites stay literal for the catalog scans
    if prereq_memo is None:
        prereq = _feat_structured_prerequisite(feat, _ASI_GATE_PREREQUISITE_KEYS)
    else:  # VF7.4: the structured prerequisite is a pure function of the feat, parsed once per walk instead of once per level
        index = feat["index"]
        if index not in prereq_memo:
            prereq_memo[index] = _feat_structured_prerequisite(feat, _ASI_GATE_PREREQUISITE_KEYS)
        prereq = prereq_memo[index]
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
    msg = _prereq_msg  # VF7.4 (see _feat_prerequisite_unmet_reason)
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

_LESSONS_REASON = msg("disabled-already-chosen-lessons")

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
