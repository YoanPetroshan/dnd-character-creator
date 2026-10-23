"""Split from official_source.py (Slice 11.0), unchanged code: feats."""
from __future__ import annotations

from pathlib import Path
import json
import re
from catalog.reference_data import (
    FEAT_FIXED_LANGUAGE_OVERRIDES, FEAT_SKILL_PICK_COUNT_OVERRIDES, LANGUAGE_NAMES, REPEATABLE_FEAT_OVERRIDES,
    ruleset_for_feat,
)
from .common import _ABILITY_KEYS, _ability_bonuses_from_5etools, _condition_immunities_from_5etools, _damage_modifiers_from_5etools, _senses_from_5etools, slug
from .innate_spells import _SPELL_SCHOOL_CODES, _clean_innate_spell_name, _innate_spell_ability
from .languages import _language_grants_from_5etools
from .proficiencies import _proficiencies_from_5etools, _proficiency_choices_from_5etools


# --- Feats (Phase 4c-i) ---
#
# UNLIKE races/subraces/traits/backgrounds above, there is NO bundled SRD
# feats file at all — the 2014 SRD has no feats mechanic — so
# load_official_feats() has no SRD counterpart to merge against in
# loader.py's load(): Catalog.feats is populated purely from this official
# data, and is simply an empty dict when official data hasn't been fetched
# on this machine (load_official_feats returns [] when feats.json is
# missing, see below), not a partial merge.
#
# Step 1 grounding (2026-09-27, against the real fetched feats.json): 305
# raw records, 0 carrying a "_copy" key — unlike races/backgrounds, this
# dataset has no _copy/_mod reprint shorthand at all, so every record is
# already complete and none are skipped for that reason (the `_copy` check
# below is kept anyway, matching every other loader in this module, in case
# a future data refresh introduces one). 47 feat names repeat across
# sourcebooks (e.g. "Alert" in both PHB and XPHB), but EVERY repeat is a
# distinct-source pair — confirmed exhaustively, not sampled, that no two
# records share both the same name AND the same source — so the same
# source-qualified index scheme races/backgrounds already use
# ("alert-phb", "alert-xphb") is collision-free here too.


def _feat_from_5etools(raw: dict) -> dict | None:
    """Task 1 (this task) is scaffolding ONLY: the shape below carries every
    field a later task in this same plan will populate (ability bonuses —
    Task 2; proficiencies — Task 3; languages — Task 4; resistances/
    immunities/senses — Task 5; expertise/saving-throw proficiencies/
    prerequisite checking — Task 6), each left as an empty/None placeholder
    for now, mirroring the exact scaffold-first-populate-later pattern both
    Phase 4a's load_official_races() and Phase 4b's load_official_backgrounds()
    used for their own first tasks. `entries` is carried through raw and
    unconverted — display-only for now, same "pure data pass-through" scope
    line _damage_modifiers_from_5etools' docstring draws elsewhere in this
    module."""
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    name_slug = slug(raw["name"])
    index = f"{name_slug}-{source}"
    fixed_languages, language_options = _language_grants_from_5etools(raw)
    for lang_id in FEAT_FIXED_LANGUAGE_OVERRIDES.get(index, []):  # FE6 (B4)
        if all(lang["index"] != lang_id for lang in fixed_languages):
            fixed_languages = fixed_languages + [{"index": lang_id, "name": LANGUAGE_NAMES[lang_id], "url": ""}]
    proficiency_choices = _proficiency_choices_from_5etools(raw) + _skill_tool_choices_from_5etools(raw)
    if index in FEAT_SKILL_PICK_COUNT_OVERRIDES:  # FE6 (B3): the text says two skills, the data one
        proficiency_choices = [
            {**env, "choose": FEAT_SKILL_PICK_COUNT_OVERRIDES[index]}
            if env.get("from", {}).get("option_set_type") == "any_skill" else env
            for env in proficiency_choices]
    # Task 5: resist/immune/senses — reuses the SAME race-side
    # _damage_modifiers_from_5etools/_condition_immunities_from_5etools
    # conversion machinery UNCHANGED (both already read off a generic raw
    # dict via .get, nothing race-specific despite living next to
    # race-only code — see _background_from_5etools' own docstring for
    # this same reuse precedent). Feats carry no `vulnerable` field in the
    # real data (0/305, confirmed 2026-09-28), so that third return value
    # is discarded here rather than added to the scaffold. `senses` has no
    # race-side counterpart to reuse — see _senses_from_5etools' own
    # docstring.
    feat_resist, feat_immune, _feat_vulnerable = _damage_modifiers_from_5etools(raw)
    feat_innate_spells, feat_spell_choices, feat_spell_variants = _feat_spells_from_5etools(raw, index)

    return {
        "index": index,
        "name": raw["name"],
        "source": raw.get("source", ""),
        "ruleset": ruleset_for_feat(raw),
        "category": raw.get("category", ""),
        "repeatable": bool(raw.get("repeatable")) or index in REPEATABLE_FEAT_OVERRIDES,
        "entries": raw.get("entries", []),
        "prerequisite": raw.get("prerequisite", []),  # Task 6 (prerequisite checking)
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _feat_ability_bonus_options_from_5etools(raw.get("ability", [])),
        # FE2 (B1): the score ceiling of this feat's increase. 5etools carries it as
        # `ability[].max` (30 on every Epic Boon); every other feat says "to a maximum of 20".
        "ability_cap": _feat_ability_cap_from_5etools(raw.get("ability", [])),
        # Task 3: skill/tool/weapon/armor proficiencies — reuses the SAME
        # race/background-side conversion machinery UNCHANGED
        # (_proficiencies_from_5etools/_proficiency_choices_from_5etools
        # read generic dicts, never actually race/background-specific
        # despite their parameter names — see _background_from_5etools'
        # own docstring for this same precedent). The background-side
        # list-returning _proficiency_choices_from_5etools (not races'
        # trait-attaching _attach_choice_proficiencies, which needs a
        # traits list feats don't have) is the right fit here: a feat can
        # carry a skill choice AND a tool choice simultaneously (Prodigy/
        # XGE, confirmed real), so a flat list of envelopes is required,
        # exactly what that function already returns. One real, disclosed
        # gap: Weapon Master (PHB)'s weaponProficiencies uses a
        # "choose"/"fromFilter" filter-query DSL shape no existing choice
        # machinery models (see _WEAPON_ID_OVERRIDES' own comment for the
        # fixed-grant side of this same weapon-category divergence) — left
        # unconverted, not guessed at; see test_official_source.py's
        # Task 3 section docstring for the full reasoning.
        "proficiencies": _proficiencies_from_5etools(raw),
        "proficiency_choices": proficiency_choices,
        # Task 4: language grants — reuses the SAME background-side
        # _language_grants_from_5etools conversion machinery directly (see
        # that function's own docstring for the "any"/"anyStandard" key
        # variant this reuse required, and test_official_source.py's Task 4
        # section for the full real-data grounding, including the one
        # disclosed unrecognized-language gap, Harper Agent's "thieves'
        # cant").
        "languages": fixed_languages,
        "language_options": language_options,
        "resist": feat_resist,
        "immune": feat_immune,
        "condition_immune": _condition_immunities_from_5etools(raw),
        "senses": _senses_from_5etools(raw),
        "expertise_skills": _expertise_skills_from_5etools(raw),
        "saving_throw_proficiencies": _saving_throw_proficiencies_from_5etools(raw),
        "expertise_choices": _expertise_choices_from_5etools(raw),
        "saving_throw_choices": _saving_throw_choices_from_5etools(raw),
        # feat-additional-spells plan: fixed spell-name grants only (see
        # _feat_innate_spells_from_5etools).
        "innate_spells": feat_innate_spells,
        "spell_choices": feat_spell_choices,
        "spell_variants": feat_spell_variants,
        # RP19: the spell tables keyed by spell slot level (`sN`), which `_feat_spells_from_5etools` skips.
        "slot_spells": _feat_slot_spell_table(raw, "prepared"),
        "expanded_spells": _feat_slot_spell_table(raw, "expanded"),
    }


def _feat_slot_spell_table(raw: dict, mechanism: str) -> dict[int, list[str]]:
    """RP19: the `sN` keys (N = spell slot level) of one additionalSpells mechanism as {N: [spell slug]}.
    `prepared` carries the eight Unearthed Arcana Arcane Adept tables ("you thereafter always have the spells listed
    for that level and lower prepared"), `expanded` the twelve Spells of the Mark tables ("added to that feature's
    spell list"). Only plain spell names convert; the slugs resolve against the catalog at engine time."""
    table: dict[int, list[str]] = {}
    for entry in raw.get("additionalSpells") or []:
        block = entry.get(mechanism) if isinstance(entry, dict) else None
        if not isinstance(block, dict):
            continue
        for key, items in block.items():
            if not (len(key) > 1 and key[0] == "s" and key[1:].isdigit() and isinstance(items, list)):
                continue
            names = [slug(_clean_innate_spell_name(i)) for i in items if isinstance(i, str) and _clean_innate_spell_name(i)]
            if names:
                table.setdefault(int(key[1:]), []).extend(n for n in names if n not in table.get(int(key[1:]), []))
    return table


# Rune Shaper lists 14 runes but the rule is "know half your proficiency
# bonus" — a flat list would misrepresent it, so it is skipped.
_FEAT_SPELLS_SKIP = {"rune-shaper-bgg"}

# The feat's own text decides which spellcasting-ability rule applies, since
# the raw additionalSpells `ability` is often missing or a generic choose list.
_INHERIT_ABILITY_RE = re.compile(r"spellcasting ability[^.]*?\bis the ability increased by this feat", re.I)
_SAME_AS_FEAT_ABILITY_RE = re.compile(r"spellcasting ability[^.]*?chosen for your [^.]*?feat", re.I)


def _feat_spell_ability_override(raw: dict, index: str | None = None) -> str | dict | None:
    """Returns {"sameAsFeat": "<feat index>"} when the feat text says its
    spellcasting ability is the one chosen for another feat (and its
    prerequisites name exactly one feat), "inherit" when the text says it is
    the ability increased by this feat (and the feat has an ability
    increase), else None (no override)."""
    text = json.dumps(raw.get("entries") or [])
    if _SAME_AS_FEAT_ABILITY_RE.search(text):
        refs = [ref for prereq in (raw.get("prerequisite") or []) if isinstance(prereq, dict)
                for ref in (prereq.get("feat") or []) if isinstance(ref, str)]
        if len(refs) == 1:
            name, _, src = refs[0].partition("|")
            return {"sameAsFeat": f"{slug(name)}-{src.strip().lower()}"}
    if _INHERIT_ABILITY_RE.search(text) and raw.get("ability"):
        return "inherit"
    return None


def _feat_spell_uses_and_items(mechanism: str, level_value) -> list[tuple[str, list]]:
    """Feat-side counterpart of _innate_spell_uses_and_names (left
    untouched for races): returns (uses, items) pairs for ONE
    additionalSpells[mechanism][level_key] value. A plain list means
    at-will for innate/known and "prepared" for prepared; dict wrappers
    "will", "daily"/"rest" (every count key, including "1e") and "ritual"
    are recognised; anything else is skipped."""
    if isinstance(level_value, list):
        return [("prepared" if mechanism == "prepared" else "at-will", level_value)]
    out: list[tuple[str, list]] = []
    if isinstance(level_value, dict):
        for wrapper, value in level_value.items():
            if wrapper == "will" and isinstance(value, list):
                out.append(("at-will", value))
            elif wrapper in ("daily", "rest") and isinstance(value, dict):
                for items in value.values():
                    if isinstance(items, list):
                        out.append(("1/day", items))
            elif wrapper == "ritual" and isinstance(value, list):
                out.append(("ritual", value))
    return out


def _parse_spell_filter(text: str) -> dict | None:
    """Parses a 5etools spell query ("level=1|school=E;D") into
    {"level": [int], "class": [lowercase], "school": [full lowercase
    names], "ritual": True}. Any unrecognised key (or malformed value)
    makes the whole filter unusable -> None."""
    result: dict = {}
    for part in text.split("|"):
        if "=" not in part:
            return None
        key, value = part.split("=", 1)
        key = key.strip().lower()
        values = [v.strip().lower() for v in value.split(";") if v.strip()]
        if key == "level":
            try:
                result["level"] = [int(v) for v in values]
            except ValueError:
                return None
        elif key == "class":
            result["class"] = values
        elif key == "school":
            schools = [_SPELL_SCHOOL_CODES.get(v.upper()) for v in values]
            if not schools or None in schools:
                return None
            result["school"] = schools
        elif key == "components & miscellaneous":
            if "ritual" not in values:
                return None
            result["ritual"] = True
        else:
            return None
    return result or None


def _feat_spells_from_5etools(raw: dict, index: str) -> tuple[list[dict], list[dict], list[str]]:
    """Converts a feat's additionalSpells into (innate_spells,
    spell_choices, spell_variants). innate_spells: race-shaped entries for
    fixed spell names (string items) under innate/known/prepared with
    level key "_" or a character-level digit. spell_choices: one entry
    per {"choose": ...} item: {variant, level, uses, ability, count,
    filter, from} — a query string becomes `filter`, a
    {"from": [names], "count": n} dict becomes `from` (slugs). Multi-entry
    feats whose entries ALL carry a "name" are mutually exclusive variants
    (Magic Initiate's spell lists...): every grant/choice is tagged with
    its entry name and spell_variants lists the names. A multi-entry feat
    without names (Cold Caster) keeps only its first entry (disclosed).
    Skipped: `expanded`, slot-level "sN" keys, unparseable filters, and
    the _FEAT_SPELLS_SKIP feats."""
    if index in _FEAT_SPELLS_SKIP:
        return [], [], []
    entries = [e for e in (raw.get("additionalSpells") or []) if isinstance(e, dict)]
    variants: list[str] = []
    if len(entries) > 1:
        if all(isinstance(e.get("name"), str) for e in entries):
            variants = [e["name"] for e in entries]
        else:
            entries = entries[:1]
    results: list[dict] = []
    choices: list[dict] = []
    folded: dict[tuple, dict] = {}
    override = _feat_spell_ability_override(raw, index)
    for entry in entries:
        variant = entry["name"] if variants else None
        ability = "inherit" if entry.get("ability") == "inherit" else _innate_spell_ability(entry.get("ability"))
        if isinstance(override, dict):
            ability = override
        elif override == "inherit" and (ability is None or isinstance(ability, dict)):
            ability = "inherit"
        for mechanism in ("innate", "known", "prepared"):
            block = entry.get(mechanism)
            if not isinstance(block, dict):
                continue
            for key, level_value in block.items():
                if key == "_":
                    level = None
                elif key.isdigit():
                    level = int(key)
                else:
                    continue
                for uses, items in _feat_spell_uses_and_items(mechanism, level_value):
                    for item in items:
                        if isinstance(item, dict) and "choose" in item:
                            spec = item["choose"]
                            base = {"variant": variant, "level": level, "uses": uses, "ability": ability}
                            if isinstance(spec, str):
                                parsed = _parse_spell_filter(spec)
                                if parsed is None:
                                    pass
                                elif mechanism == "prepared" and key.isdigit():
                                    # Level-scaled picks (Ritual Caster XPHB: keys 1/5/9/13/17)
                                    # fold into ONE choice whose count grows with level.
                                    fold_key = (variant, uses, repr(parsed))
                                    if fold_key in folded:
                                        folded[fold_key]["count_by_level"][key] = item.get("count", 1)
                                    else:
                                        folded[fold_key] = {
                                            **base, "level": None, "count": item.get("count", 1),
                                            "filter": parsed, "from": None,
                                            "count_by_level": {key: item.get("count", 1)},
                                        }
                                        choices.append(folded[fold_key])
                                else:
                                    choices.append({**base, "count": item.get("count", 1), "filter": parsed, "from": None})
                            elif isinstance(spec, dict) and isinstance(spec.get("from"), list):
                                names = [slug(_clean_innate_spell_name(n)) for n in spec["from"] if isinstance(n, str)]
                                choices.append({**base, "count": spec.get("count", 1), "filter": None, "from": names})
                            continue
                        if not isinstance(item, str):
                            continue
                        clean = _clean_innate_spell_name(item)
                        if not clean:
                            continue
                        results.append({
                            "name": clean.title(), "spell_id": slug(clean), "level": level,
                            "uses": uses, "ability": ability, "variant": variant,
                        })
    return results, choices, variants


def _feat_variant_hints_from_5etools(raw: dict) -> dict[str, str]:
    """A background grant like "magic initiate; cleric|xphb" names a
    spell-list-restricted variant. Returns {feat ref: "<Name> Spells"}
    (e.g. {"magic-initiate-xphb": "Cleric Spells"}) for those grants."""
    hints: dict[str, str] = {}
    for entry in raw.get("feats") or []:
        for feat_key, granted in entry.items():
            if granted is not True:
                continue
            name_part, _, source_part = feat_key.partition("|")
            base, sep, variant = name_part.partition(";")
            if not sep or not variant.strip() or not source_part.strip():
                continue
            hints[f"{slug(base.strip())}-{source_part.strip().lower()}"] = f"{variant.strip().title()} Spells"
    return hints


def _expertise_skills_from_5etools(raw: dict) -> list[str]:
    """Converts feats.json's `expertise` field — a list of single-key
    dicts, either {"<skill>": True} (a FIXED grant) or
    {"anyProficientSkill": N} (a CHOICE of N already-proficient skills to
    gain expertise in) — into a plain list of skill ids, `skill-{slug}`
    (the SAME id shape _proficiencies_from_5etools already produces for
    sheet.proficiencies.skills, so sheet.expertiseSkills entries line up
    with them 1:1, and both can be rendered/compared the same way).

    Only `is True` fixed entries convert; the anyProficientSkill choice
    portion has no choice mechanism to resolve against today and is
    silently excluded here — the same "pure data pass-through, no choice
    resolution" scope line _ability_bonuses_from_5etools already draws
    for its own choose-N sibling field (ability_bonus_options). Feats
    themselves ARE fully player-selectable as of the ASI-or-feat plan
    (2026-09-28+) — via a background's fixed/chosen `feats` grant (see
    engine.resolve._resolve_granted_feats) AND via free selection of any
    of the 94 General feats at a class level that grants an Ability Score
    Improvement (see engine.resolve._resolve_asi_selected_feats) — this
    docstring previously said no feat-selection UI existed at all, which
    predates that plan and is now stale; only the anyProficientSkill
    CHOICE within an already-selected feat is unconverted, not feat
    selection itself.

    The anyProficientSkill CHOICE portion is converted separately by
    _expertise_choices_from_5etools (closes the Skill Expert gap the
    ASI-or-feat final review disclosed).

    Confirmed against the real fetched feats.json (2026-09-28): 7 real
    records carry this field (Aberrant Anatomy/RHW, Boon of Skill/XPHB,
    Boon of Terror/FRHoF, Echoing Soul/RHW, Prodigy/XGE, Skill Expert/TCE,
    Skill Expert/XPHB) — only 2 (Aberrant Anatomy: perception; Boon of
    Terror: intimidation) are fixed; the other 5 are exclusively
    anyProficientSkill and contribute nothing here."""
    skills = []
    for entry in raw.get("expertise") or []:
        for key, val in entry.items():
            if val is True:
                skills.append(f"skill-{slug(key)}")
    return skills


def _skill_tool_choices_from_5etools(raw: dict) -> list[dict]:
    """feats.json's `skillToolLanguageProficiencies` — Skilled/PHB and
    Skilled/XPHB are the only real carriers, both
    `[{"choose": [{"count": 3, "from": ["anySkill", "anyTool"]}]}]` — as
    `proficiency_choices`-style envelopes appended after the ordinary skill/
    tool ones (so their cids are `...:proficiency-choice-<i>` and the existing
    merge sites route picked skills to skills and tools to tools). `from`
    lists with both anySkill and anyTool use the any_skill_or_tool option
    set; a lone one reuses any_skill / any_tool. A `from` naming
    anyLanguage (no real feat does) is not converted."""
    envelopes = []
    for entry in raw.get("skillToolLanguageProficiencies") or []:
        groups = entry.get("choose")
        if isinstance(groups, dict):
            groups = [groups]
        for group in groups or []:
            n = group.get("count", 1)
            kinds = set(group.get("from") or [])
            if not isinstance(n, int) or isinstance(n, bool) or n < 1 or "anyLanguage" in kinds:
                continue
            if kinds == {"anySkill", "anyTool"}:
                set_type = "any_skill_or_tool"
            elif kinds == {"anySkill"}:
                set_type = "any_skill"
            elif kinds == {"anyTool"}:
                set_type = "any_tool"
            else:
                continue
            envelopes.append({"choose": n, "type": "proficiencies", "from": {"option_set_type": set_type}})
    return envelopes


def _expertise_choices_from_5etools(raw: dict) -> list[dict]:
    """The CHOICE portion of feats.json's `expertise` field —
    `{"anyProficientSkill": N}` — as a `proficiency_choices`-style envelope
    ({"choose": N, "from": {"option_set_type": "any_skill"}}) that
    engine.resolve._feat_choice_templates turns into a real, selectable
    Choice. Closes the gap _expertise_skills_from_5etools' docstring
    discloses (Skill Expert, Prodigy, Boon of Skill, Echoing Soul).

    The options here are every skill; they are gated to proficient skills
    by engine.resolve._gate_expertise_choices."""
    envelopes = []
    for entry in raw.get("expertise") or []:
        n = entry.get("anyProficientSkill")
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            envelopes.append({"choose": n, "type": "proficiencies", "from": {"option_set_type": "any_skill"}})
    return envelopes


def _saving_throw_choices_from_5etools(raw: dict) -> list[dict]:
    """The CHOICE portion of feats.json's `savingThrowProficiencies` field —
    `{"choose": {"from": ["str", ...], "count"?: N}}` (Resilient/PHB and
    /XPHB) — as an options_array envelope whose option ids are the bare
    lowercase ability keys; engine.resolve uppercases a selection before
    merging it into the saving-throw proficiency list."""
    envelopes = []
    for entry in raw.get("savingThrowProficiencies") or []:
        choose = entry.get("choose")
        if not isinstance(choose, dict):
            continue
        options = [
            {"option_type": "reference", "item": {"index": k, "name": SAVE_ABILITY_NAMES[k], "url": ""}}
            for k in choose.get("from", [])
            if k in SAVE_ABILITY_NAMES
        ]
        if options:
            envelopes.append({
                "choose": choose.get("count", 1),
                "type": "proficiencies",
                "from": {"option_set_type": "options_array", "options": options},
            })
    return envelopes


SAVE_ABILITY_NAMES = {
    "str": "Strength", "dex": "Dexterity", "con": "Constitution",
    "int": "Intelligence", "wis": "Wisdom", "cha": "Charisma",
}


def _saving_throw_proficiencies_from_5etools(raw: dict) -> list[str]:
    """Converts feats.json's `savingThrowProficiencies` field into a plain
    list of ability ids ("STR", "DEX", ...) for a FIXED grant — only an
    `is True` ability-keyed entry counts; a `{"choose": {"from": [...]}}`
    entry (a CHOICE of which ability gains the proficiency) is out of
    scope, the same reasoning _expertise_skills_from_5etools' own
    anyProficientSkill exclusion uses just above.

    The choice-shaped portion (Resilient) is converted separately by
    _saving_throw_choices_from_5etools (closes the gap the ASI-or-feat
    final review disclosed).

    Confirmed against the real fetched feats.json (2026-09-28): only 2
    real records carry this field at all (Resilient/PHB, Resilient/XPHB),
    and BOTH are exclusively choice-shaped (`[{"choose": {"from": ["str",
    ... ]}}]` — pick one of six) with no fixed entry at all. This
    function's fixed-only conversion therefore returns [] for every real
    feat today — mirrors _background_ability_bonuses' own "always {}
    today, kept for symmetry and to make the merge point explicit"
    precedent: the conversion is implemented generally (not narrowly
    special-cased to today's all-choice reality) so a future sourcebook
    feat that DOES carry a fixed saving-throw grant is picked up without
    any further code change here."""
    throws = []
    for entry in raw.get("savingThrowProficiencies") or []:
        for key, val in entry.items():
            if val is True and key in _ABILITY_KEYS:
                throws.append(key.upper())
    return throws


def _feat_ability_cap_from_5etools(ability_list: list[dict]) -> int:
    """The highest `max` of the feat's `ability` records, else the ordinary 20.
    A hidden record (the ASI feat's two descriptive entries) never counts."""
    caps = [e["max"] for e in ability_list or [] if not e.get("hidden") and isinstance(e.get("max"), int)]
    return max(caps) if caps else 20


def _feat_ability_bonus_options_from_5etools(ability_list: list[dict]) -> dict | None:
    """Feat-side counterpart to _ability_bonus_options_from_5etools (races)
    — reuses the SAME output envelope shape, but with a small necessary
    variant on which "choose" entries it accepts, grounded against the
    real fetched feats.json (2026-09-28, Task 2):

    - Entries marked "hidden": true are skipped entirely. The only real
      case is "Ability Score Improvement" itself, which carries TWO such
      entries (one "amount": 2, one "count": 2) — both describing the
      EXISTING class-level ASI mechanic, not a feat-granted bonus; wiring
      that connection is explicitly out of scope for this slice (design
      spec).
    - Both "amount" and "count" are accepted as the count key (unlike
      races' _ability_bonus_options_from_5etools, which only accepts
      "count" — races' one real "amount" case, Custom Lineage, is
      genuinely ambiguous at amount=2, between +2-to-one and +1-to-two).
      For feats, once hidden entries are excluded, every surviving
      amount/count value in the real data is 1 — no live ambiguity to
      guess at, confirmed exhaustively.
    - A missing amount/count key (common on Epic Boon feats, which only
      carry "from" plus a separate top-level "max" score cap this simple
      envelope doesn't model) defaults to 1 — "pick one ability from this
      list, +1" — matching every such real entry's actual text."""
    for entry in ability_list or []:
        if entry.get("hidden"):
            continue
        choose = entry.get("choose")
        if not isinstance(choose, dict):
            continue
        from_list = choose.get("from", [])
        if not from_list:
            continue
        count = choose.get("amount", choose.get("count", 1))
        options = [
            {"option_type": "ability_bonus", "ability_score": {"index": ab, "name": ab.upper(), "url": ""}, "bonus": 1}
            for ab in from_list
        ]
        return {"choose": count, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}
    return None


def load_official_feats(official_dir: Path) -> list[dict]:
    feats_path = official_dir / "feats.json"
    if not feats_path.exists():
        return []
    with open(feats_path, encoding="utf-8") as f:
        data = json.load(f)
    feats = []
    for raw in data.get("feat", []):
        converted = _feat_from_5etools(raw)
        if converted is not None:
            feats.append(converted)
    return feats
