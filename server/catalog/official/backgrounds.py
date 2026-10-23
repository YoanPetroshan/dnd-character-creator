"""Split from official_source.py (Slice 11.0), unchanged code: backgrounds."""
from __future__ import annotations

from pathlib import Path
import json
from catalog.reference_data import ruleset_for_edition
from .common import _ability_bonus_options_from_5etools_weighted_pair, slug
from .background_equipment import starting_equipment_options_2024_from_5etools
from .equipment import _fixed_starting_equipment_from_5etools, _starting_equipment_options_from_5etools
from .feats import _feat_variant_hints_from_5etools
from .languages import _language_grants_from_5etools
from .proficiencies import _proficiencies_from_5etools, _proficiency_choices_from_5etools


def _feats_from_5etools(raw: dict) -> tuple[list[str], list[str], list[str]]:
    """Converts a background's `feats` field — confirmed empirically
    (Step 1, 2026-09-27) to be a list of single-key boolean-map dicts,
    `{"<feat name>|<source>": True}`, the SAME convention
    skillProficiencies/toolProficiencies already use — into a plain list
    of feat ids: `|source` stripped, the remaining name run through the
    same `slug()` every other |source-suffixed field already gets.

    Pure inert data pass-through: no resolution against a feat catalog
    (none exists in this app yet), no prerequisite checking, no effect
    application.

    Semicolon-suffixed spell-list variant names (Phase 4c-i Task 6 fix,
    found by Task 5's own review): 4 real records (Acolyte/XPHB, Guide/
    XPHB, Moonwell Pilgrim/FRHoF, Sage/XPHB) grant not plain "magic
    initiate|xphb" but a spell-list-restricted variant, e.g. "magic
    initiate; cleric|xphb" — confirmed against the real fetched
    backgrounds.json (2026-09-28) to be the ONLY grant keys in the whole
    dataset containing a literal ";" (checked exhaustively, not assumed
    from this one case). catalog.feats has no record named "Magic
    Initiate; Cleric" at all — the real Magic Initiate feat record is
    named plain "Magic Initiate" in both PHB and XPHB (confirmed against
    feats.json) — so slugging the ";"-suffixed grant key verbatim used to
    produce "magic-initiate;-cleric", which matched ZERO catalog feats
    and was silently dropped by engine.resolve._resolve_granted_feats'
    own "no match" path (a DIFFERENT failure mode from that function's
    disclosed "ambiguous source, more than one match" guard — this was
    "wrong slug, no match at all"). The "; <spell list>" suffix names
    which spell list the grant is restricted to — modeling that
    restriction would mean granting specific spells/cantrips, which
    `additionalSpells` being out of scope for this plan (design
    spec; feats' spell grants were later added separately, see
    _feat_spells_from_5etools) already rules out — so the fix here is only to recover the
    grant as PLAIN "Magic Initiate" (stripping everything from the first
    ";" onward before slugging), not to model the restriction itself.
    Once fixed, these 4 records resolve exactly like the OTHER plain
    "magic initiate|xphb"/"magic initiate|phb" grants already do: still
    silently skipped, but via the SAME already-disclosed "matches feats
    in more than one source" ambiguity guard every other plain Magic
    Initiate grant hits (Magic Initiate has both a PHB and an XPHB
    record) — not a new, separate zero-match gap. No effect on this
    task's own ability_bonuses/proficiencies/languages/resist/immune/
    senses/expertise_skills/saving_throw_proficiencies output either way
    (confirmed: neither real Magic Initiate record carries any of those
    fields today), but fixing the slug itself (rather than only
    documenting the gap) keeps this function's output honest about what
    the grant actually names, and avoids the same ";"-suffix pattern
    silently breaking a FUTURE feat variant that does carry one of those
    fields.

    Returns (feats, feat_options, feat_refs) — fixed a "one true grant"
    alternatives split, Finding 2 of the final whole-branch review
    (2026-09-27):
    Task 6's original version combined EVERY `is True` entry additively
    into one `feats` list, which is correct for 69 of 71 real records
    (exactly one `is True` entry each) but wrong for the other two —
    Rewarded/BMT: `[{"lucky|phb": True}, {"magic initiate|phb": True},
    {"skilled|phb": True}]`, whose real published text is "You gain the
    Lucky, Magic Initiate, or Skilled feat (your choice)" — a CHOICE of
    one, not a grant of all three; Ruined/BMT is the identical shape
    (Alert/Skilled/Tough). Additive combination was silently over-
    granting both — inert today (feats aren't a mechanic yet, Phase 4c's
    job) but would silently over-grant once Phase 4c starts consuming
    this data for real. `feat_options` carries the "one of these"
    alternatives for that 2-record case, mirroring the fixed-vs-choice
    field pairs this same module already uses everywhere else
    (starting_proficiencies/starting_proficiency_choices, languages/
    language_options, ability_bonuses/ability_bonus_options) rather than
    inventing a new convention. `feats` stays a single-element list for
    every real record with exactly one grant (unchanged from before), and
    both lists are empty together only when the background has no `feats`
    field, or only a wildcard entry (see below), at all.

    Only `is True` entries are considered in the first place — the SAME
    filter _proficiencies_from_5etools already applies to exclude choice/
    wildcard envelopes without needing to special-case their key names.
    This matters here too: 4 real records (Haunted One/RHW, Investigator/
    RHW, Mist Wanderer, Spirit Medium) carry a SECOND entry alongside
    their plain grant, `{"anyFromCategory": {"category": [...]}}` — a
    "pick any feat from category X" wildcard whose value is a dict, not
    True. That entry is excluded by this same `is True` check, not by
    name — a wildcard feat grant like this has nothing to resolve against
    without a feat catalog, so it's silently dropped rather than guessed
    at (disclosed here, not a bug: still out of scope).

    Returns a THIRD value, `feat_refs` (Finding 1 of the final whole-branch
    review, 2026-09-28): a source-qualified reference list, parallel to
    `feats` (empty whenever `feats` itself is empty, e.g. the alternatives
    branch below), built as `slug(bare_name) + "-" + source.lower()` — the
    EXACT SAME "slug(name)-source" convention this module already uses to
    build every catalog feat's own `index` (see _feat_from_5etools) —
    rather than the bare, source-stripped slug `true_feat_ids` above
    throws the source away to produce.

    Root cause this fixes: the raw grant key ALREADY names the source
    (e.g. "tavern brawler|xphb"), but `true_feat_ids` above discards
    everything after "|" before slugging, leaving engine.resolve.
    _resolve_granted_feats nothing to disambiguate with when a bare slug
    matches feats in more than one source (9 real slugs do — see that
    function's own docstring) — 28 of 70 real unambiguous single-feat
    grants were hitting that ambiguity guard and being silently skipped
    even though the source was known all along. `feat_refs` recovers it:
    resolve.py tries an exact match against catalog.feats by this
    "slug-source" id FIRST, falling back to the existing bare-slug/
    ambiguity logic only when no ref is available (hand-authored test
    data built without this field) or the ref doesn't match any real
    catalog feat.

    One real grant key is capitalized ("Skilled|xphb", Noble/XPHB,
    confirmed 2026-09-28) — `slug()` lowercases unconditionally, so
    `slug("Skilled")` -> "skilled" and the resulting ref ("skilled-xphb")
    matches catalog.feats' own index exactly, same as every lowercase
    grant key."""
    true_feat_ids: list[str] = []
    true_feat_refs: list[str] = []
    for entry in raw.get("feats") or []:
        for feat_key, granted in entry.items():
            if granted is True:
                # "|" splits the source suffix off FIRST (kept for
                # feat_refs below), then ";"-strip BEFORE slugging (see
                # docstring above): recovers the base feat name from a
                # spell-list-restricted variant like "magic initiate;
                # cleric" -> "magic initiate", the only real pattern this
                # dataset uses a literal ";" for.
                name_part, _, source_part = feat_key.partition("|")
                bare_name = name_part.split(";", 1)[0].strip()
                bare_slug = slug(bare_name)
                true_feat_ids.append(bare_slug)
                source_part = source_part.strip().lower()
                true_feat_refs.append(f"{bare_slug}-{source_part}" if source_part else "")

    if len(true_feat_ids) > 1:
        # More than one simultaneous True-valued entry means ALTERNATIVES
        # ("one of these"), not a simultaneous grant of every one of them
        # — see docstring above. Rewarded/Ruined (BMT) are the only two
        # real records this branch is exercised by. feat_refs stays empty
        # here too, mirroring `feats` itself — these candidates are
        # unresolved alternatives, not an actual grant to resolve against
        # the catalog (see engine.resolve._resolve_granted_feats' own
        # "feat_options candidates are NOT resolved for effects" comment).
        return [], true_feat_ids, []
    return true_feat_ids, [], true_feat_refs


def _background_from_5etools(raw: dict) -> dict | None:
    """Converts one raw 5etools background record into the SAME dict shape
    catalog/loader.py already produces for the bundled SRD Acolyte
    background (confirmed empirically, Step 1: index, name,
    starting_proficiencies, language_options, languages,
    starting_equipment, starting_gold, starting_equipment_options,
    feature, source) — plus two NEW fields: `feats` (mirroring races' own
    `source` precedent, populated by this plan's later Task 6), and
    `starting_proficiency_choices` (Task 2 — the CHOICE portion of
    skillProficiencies/toolProficiencies, as opposed to the fixed grants
    `starting_proficiencies` already carries; see
    _proficiency_choices_from_5etools).

    Unlike races, backgrounds carry skillProficiencies/toolProficiencies
    as the exact same length-1-list-of-booleans shape
    _proficiencies_from_5etools already converts for races (confirmed
    empirically, Step 1, against a real XPHB Acolyte record) — that
    function reads only skillProficiencies/toolProficiencies/
    weaponProficiencies/armorProficiencies off whatever dict it's given
    (via .get, all optional) and was never actually race-specific despite
    its `race_raw` parameter name, so it's called here UNCHANGED, no
    signature change needed. (Backgrounds carry no weapon/armor
    proficiency fields in the real data, so those two loops simply no-op
    for every background record — confirmed empirically, Step 1: no
    weaponProficiencies/armorProficiencies key appears on any real
    background.)

    `language_options`/`languages` (Task 3 — fixed and choice-shaped
    language grants; see _language_grants_from_5etools for the full shape
    grounding, including a disclosed data-fidelity gap on 1 of 56 real
    records, and a Finding-2 correction to that function's own additive-
    combination rule) are now populated. `ability_bonus_options` (Task 4 —
    the 2024-style weighted ability-score-improvement choice; see
    _ability_bonus_options_from_5etools_weighted_pair) is now populated
    too. `starting_equipment_options` (Task 5 — the A/B-style starting
    equipment PACKAGE CHOICE; see _starting_equipment_options_from_5etools
    for the full shape grounding, including a disclosed gap in what
    happens after a bundle with a synthetic/non-catalog member is
    selected) is now populated. `starting_equipment`/`starting_gold` (the
    FIXED, no-choice `"_"`-keyed equipment list 74/135 real backgrounds
    carry — e.g. Anthropologist/ToA has ONLY this, no package choice at
    all) — a real, disclosed gap Task 5 deliberately left as a follow-up
    (its own brief scoped it to the package CHOICE specifically) — are now
    also populated, fixed by Finding 1 of the final whole-branch review
    (2026-09-27); see _fixed_starting_equipment_from_5etools for the full
    shape grounding. That same function also returns this record's fixed-
    grant NARRATIVE items (flavor-only gear / category placeholders /
    no-catalog-match items from the `"_"` list), carried on the new
    `starting_narrative_items` field — engine/resolve.py merges this with
    its own selection-driven narrative items (previously the ONLY source
    of sheet.equipment.narrativeItems) into one list. `feats`/
    `feat_options` (Task 6, corrected by Finding 2 — see
    _feats_from_5etools for the full shape grounding, including a
    disclosed exclusion of a non-boolean "anyFromCategory" wildcard entry
    this app has no feat catalog to resolve against, and the fixed-vs-
    alternatives split that replaces Task 6's original always-additive
    behavior) are now populated too — pure inert data, no mechanical
    effect. `feature` is left empty: engine/resolve.py
    never reads a
    background's `feature` field for anything mechanical today (confirmed
    by grep, Step 1) — SRD's own bundled backgrounds carry rich flavor
    text there that resolve.py still never consumes, so leaving it empty
    here is consistent with the existing bundled-data behavior, not a new
    gap this task introduces.

    _copy-based records are skipped, same reasoning as races (see module
    docstring)."""
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    name_slug = slug(raw["name"])
    index = f"{name_slug}-{source}"
    fixed_languages, language_options = _language_grants_from_5etools(raw)
    fixed_equipment, fixed_gold, fixed_narrative_items = _fixed_starting_equipment_from_5etools(raw)
    feats, feat_options, feat_refs = _feats_from_5etools(raw)

    proficiency_choices = _proficiency_choices_from_5etools(raw)
    ruleset = ruleset_for_edition(raw)
    # RP9 (C, E12): additive 2024 starting-equipment envelope (real items and quantities); the old key is untouched.
    extra_2024 = ({"starting_equipment_options_2024": starting_equipment_options_2024_from_5etools(raw, proficiency_choices)}
                  if ruleset == "2024" else {})

    return {
        "index": index,
        "name": raw["name"],
        "starting_proficiencies": _proficiencies_from_5etools(raw),
        "starting_proficiency_choices": proficiency_choices,
        "language_options": language_options,
        "languages": fixed_languages,
        "starting_equipment": fixed_equipment,
        "starting_gold": fixed_gold,
        "starting_equipment_options": _starting_equipment_options_from_5etools(raw),
        "starting_narrative_items": fixed_narrative_items,
        "feature": {"name": "", "desc": []},  # not read mechanically by resolve.py today, see docstring above
        "ability_bonus_options": _ability_bonus_options_from_5etools_weighted_pair(raw.get("ability", [])),
        "source": raw.get("source", ""),
        "ruleset": ruleset,
        **extra_2024,
        "feats": feats,
        "feat_options": feat_options,
        # Finding 1 of the final whole-branch review (2026-09-28): a
        # source-qualified parallel to `feats` — see _feats_from_5etools'
        # own docstring. engine.resolve._resolve_granted_feats tries this
        # FIRST (exact match against catalog.feats), falling back to the
        # bare-slug/ambiguity logic only when it's absent or doesn't match
        # (e.g. hand-authored test data built without this field).
        "feat_refs": feat_refs,
        # feat-additional-spells plan: {feat ref: variant name} for
        # spell-list-restricted grants ("magic initiate; cleric|xphb").
        "feat_variant_hints": _feat_variant_hints_from_5etools(raw),
    }


def load_official_backgrounds(official_dir: Path) -> list[dict]:
    bg_path = official_dir / "backgrounds.json"
    if not bg_path.exists():
        return []
    with open(bg_path, encoding="utf-8") as f:
        data = json.load(f)
    backgrounds = []
    for raw in data.get("background", []):
        converted = _background_from_5etools(raw)
        if converted is not None:
            backgrounds.append(converted)
    return backgrounds
