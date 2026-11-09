"""Split from official_source.py (Slice 11.0), unchanged code: languages."""
from __future__ import annotations

from catalog.reference_data import LANGUAGES
from .common import slug


_LANGUAGES_BY_INDEX = {lang["index"]: lang for lang in LANGUAGES}


def _language_ref_from_key(key: str, extra_names: dict[str, str] | None = None) -> dict | None:
    """Looks up a 5etools language slug (a fixed-grant object key like
    "giant", or a choose.from list entry like "deep speech") against
    reference_data.LANGUAGES, returning the SRD-shaped {index, name, url}
    reference, or None if it isn't a recognized language slug (not seen in
    real data — every real key/entry confirmed, 2026-09-26, against the
    brief's own dump command, resolves to a LANGUAGES index once run
    through the same slug() every other name in this module already
    uses — e.g. "Deep Speech"/"deep speech" -> "deep-speech", matching
    LANGUAGES' own entry)."""
    lang = _LANGUAGES_BY_INDEX.get(slug(key))
    if lang is None:
        if extra_names and slug(key) in extra_names:  # VF2.4: a Primordial dialect named by a species record (display name only)
            return {"index": slug(key), "name": extra_names[slug(key)], "url": ""}
        return None
    return {"index": lang["index"], "name": lang["name"], "url": ""}


def _language_choice_option_from_5etools(name: str, other: tuple = ()) -> dict | list[dict]:
    """Converts ONE entry of a background language choice's `choose.from`
    list into an options_array 'reference' option — the SAME mechanism
    _skill_choice_envelope_from_5etools/_tool_choice_envelope_from_5etools
    already use for their own enumerated lists. A literal "other" entry (4
    of 8 real choose.from lists carry it, e.g. Boros Legionnaire/GGR)
    means "or any other language of your choice" in the source text;
    since this Choice model has no free-text option, it's represented as
    its own distinctly labeled "Other" option (per the brief's own
    guidance), not silently dropped or folded into the full language
    list, which would make it indistinguishable from a real anyStandard
    wildcard option."""
    if name.lower() == "other":
        if other:  # VF2.4: the species record names the language in its text (Simic Hybrid: Elvish or Vedalken)
            return [{"option_type": "reference", "item": {"index": slug(n), "name": n, "url": ""}} for n in other]
        return {"option_type": "reference", "item": {"index": "other", "name": "Other", "url": ""}}
    lang = _language_ref_from_key(name)
    if lang is not None:
        return {"option_type": "reference", "item": lang}
    # Unrecognized language name — not seen in real data (every non-"other"
    # choose.from entry matches a reference_data.LANGUAGES slug exactly,
    # confirmed empirically, 2026-09-26) — best-effort slug/title-case
    # rather than silently dropping the option, same "disclosed, not
    # exercised" fallback discipline as e.g. the armor-category branch in
    # _proficiencies_from_5etools above.
    return {"option_type": "reference", "item": {"index": slug(name), "name": name.title(), "url": ""}}


def _language_grants_from_5etools(raw: dict, extra_names: dict[str, str] | None = None,
                                  other: tuple = ()) -> tuple[list[dict], dict | None]:
    """Converts a background's `languageProficiencies` field into
    (fixed_grants, language_options_envelope) — the SRD-shaped
    `bg["languages"]` / `bg["language_options"]` fields resolve.py already
    reads (engine/resolve.py's fixed_languages list-comprehension and
    _background_choice_templates' language_options handling — confirmed
    UNCHANGED by this task, see this module's test coverage and
    test_resolve.py's own background-language tests).

    `languageProficiencies` is a list of dicts; confirmed empirically
    (2026-09-26, via the brief's own dump command against the real
    fetched backgrounds.json, 56 of 56 real records with this field) to
    combine three key shapes, sometimes on the SAME dict entry:
      - a literal language slug -> True: a FIXED grant (e.g.
        {"giant": True} — Rune Carver/BGG, Giant Foundling/BGG).
      - "anyStandard": N: a WILDCARD choice ("choose N of any language",
        49/56 records) — semantically identical to SRD's own bundled
        Acolyte language_options, so it reuses that SAME resource_list
        mechanism verbatim (zero new catalog/choices.py code).
      - "choose": {"from": [...]}: an ENUMERATED choice of N (N default
        1) — 8/56 records; 6 of those 8 carry NO "anyStandard" on the same
        entry and become a plain options_array envelope, the same
        mechanism every other enumerated choice in this module already
        uses.
    Multiple dict entries in the outer list do NOT always combine
    additively — CORRECTED by Finding 2 of the final whole-branch review
    (2026-09-27), which disproved this docstring's own previous claim
    that Clan Crafter/SCAG's {"dwarvish": True} + {"anyStandard": 1}, as
    TWO separate list entries, means "fixed Dwarvish AND a free pick".
    Clan Crafter's real published "Languages:" text (read directly off
    its own `entries`, not inferred) is "Dwarvish or one of your choice
    if you already speak Dwarvish" — a SINGLE grant, conditionally
    SUBSTITUTED, not an additional pick stacked on top. Confirmed
    empirically that Clan Crafter is the ONLY real background whose
    languageProficiencies has more than one OUTER-LIST entry at all (every
    other multi-key combination, e.g. Giant Foundling/BGG below, packs
    everything onto a SINGLE dict entry instead) — so this correction
    changes behavior for exactly the one record it was wrong about, and
    cannot affect any other real record. The distinguishing signal used
    below: when a SEPARATE list entry contributes ONLY a fixed grant (no
    wildcard/choose of its own on that same entry) and another separate
    entry contributes a wildcard/choose, that split-across-entries shape
    reads as "X, or Y if condition" — only the fixed grant is kept, the
    wildcard is dropped entirely. A fixed grant COMBINED WITH a wildcard
    on the SAME dict entry (Giant Foundling/BGG: {"giant": True,
    "anyStandard": 1}, real text "Giant AND one other language of your
    choice") is unaffected by this change and still combines additively,
    exactly as before — see
    test_fixed_grant_combined_with_any_standard_on_the_same_entry.

    KNOWN, DISCLOSED DATA-FIDELITY GAP (found during this task, 2026-09-26
    — NOT one of the brief's three claimed shapes, and NOT a resolve.py
    consumption-path bug, so NOT subject to this plan's Task-1b/2b
    "spin off a dedicated follow-up task" precedent): exactly 2 of 56 real
    records — Feylost/WBtW and Haunted One/VRGR — combine "anyStandard"
    AND "choose" on the SAME dict entry, a FOURTH shape the brief never
    describes. Their real published "Languages:" flavor text (read
    directly off their own `entries`, not inferred) gives this identical
    JSON shape CONTRADICTORY meanings:
      - Haunted One/VRGR: "Choose two, one of which must be Abyssal,
        Celestial, ... or Undercommon" — an ADDITIVE combination (1 free
        pick + 1 pick constrained to the list = 2 total), matching this
        function's general combining rule below exactly.
      - Feylost/WBtW: "One of your choice of Elvish, Gnomish, Goblin, or
        Sylvan" — a SINGLE pick from just the 4-item list; here the
        accompanying "anyStandard": 1 key does NOT represent an
        independent second grant — the real text has no second pick at
        all.
    No rule derivable from the JSON shape alone satisfies both (checked:
    neither "always additive" nor "choose's own count overrides
    anyStandard" fits both records). This function treats the combination
    as ADDITIVE (total = anyStandard + choose's count, sourced via the
    SAME resource_list mechanism as a plain anyStandard wildcard) —
    correct for Haunted One, but produces an over-generous choose:2 (of
    all 16 languages) for Feylost instead of its real choose:1 (of
    exactly its 4 named languages). This is the one known exception,
    affecting exactly 1 of 56 real background records with a
    languageProficiencies field. Note the underlying flat "choose N from
    set S" Choice model can't express Haunted One's real "at least one
    from subset X" sub-constraint under EITHER reading, so neither record
    is fully representable in this model regardless of which reading is
    picked — disclosed here, and in the Task 3 report, for the controller
    to decide whether it's worth a dedicated follow-up."""
    # VF2.4 (species records only; backgrounds and feats pass nothing): `extra_names` = Primordial dialect keys
    # ({"auran": true}) that become fixed grants; `other` = the language names the record's text gives for its
    # `other: true` flag (a fixed grant) or for an "other" entry of a `choose.from` list.
    fixed: list[dict] = []
    any_count = 0
    choose_count = 0
    choose_options: list[dict] = []
    saw_choice = False
    saw_fixed_only_entry = False  # a separate list entry granting a fixed language with no wildcard/choose of its own on that same entry — see docstring

    for entry in raw.get("languageProficiencies") or []:
        if not isinstance(entry, dict):
            continue
        entry_granted_fixed = False
        for key, value in entry.items():
            if key in ("anyStandard", "choose"):
                continue
            if key == "other" and value is True:
                for name in other:
                    fixed.append({"index": slug(name), "name": name, "url": ""})
                    entry_granted_fixed = True
                continue
            if value is True:
                lang = _language_ref_from_key(key, extra_names)
                if lang is not None:
                    fixed.append(lang)
                    entry_granted_fixed = True

        entry_has_wildcard = False
        # "anyStandard" is backgrounds' own wildcard key; "any" is the
        # feat-side synonym (Task 4 grounding, 2026-09-28, against the real
        # fetched feats.json — every one of the 7 real feats with a
        # languageProficiencies wildcard uses "any", never "anyStandard";
        # confirmed 0/56 real background records use "any" either, so
        # reading both keys here is collision-free for the already-covered
        # background path).
        any_n = entry.get("anyStandard", entry.get("any"))
        if isinstance(any_n, int) and not isinstance(any_n, bool):
            any_count += any_n
            saw_choice = True
            entry_has_wildcard = True

        choose = entry.get("choose")
        if isinstance(choose, dict):
            choose_count += choose.get("count", 1)
            saw_choice = True
            entry_has_wildcard = True
            for name in choose.get("from", []):
                opt = _language_choice_option_from_5etools(name, other)
                choose_options.extend(opt if isinstance(opt, list) else [opt])

        if entry_granted_fixed and not entry_has_wildcard:
            saw_fixed_only_entry = True

    if saw_fixed_only_entry and saw_choice:
        # "X, or Y if you already know X" (Clan Crafter/SCAG, the only real
        # record this fires for) — the wildcard/enumerated portion read
        # from a DIFFERENT entry than the fixed grant is a conditional
        # SUBSTITUTE for it, not an additional pick — see docstring above.
        return fixed, None

    if not saw_choice:
        return fixed, None

    total = any_count + choose_count
    if any_count == 0 and choose_options:
        # A pure enumerated list, no wildcard slot at all — the common
        # "choose N of {named list}" shape (6 of 8 real 'choose' records).
        envelope = {"choose": total, "type": "languages",
                    "from": {"option_set_type": "options_array", "options": choose_options}}
    else:
        # A wildcard is present, alone or combined with a named list (see
        # this function's own docstring for the combined case's known,
        # disclosed fidelity gap) — reuses SRD's own bundled Acolyte
        # language_options mechanism verbatim.
        envelope = {"choose": total, "type": "languages",
                    "from": {"option_set_type": "resource_list", "resource_list_url": "/api/2014/languages"}}
    return fixed, envelope
