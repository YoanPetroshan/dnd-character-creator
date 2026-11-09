"""Split from official_source.py (Slice 11.0), unchanged code: races."""
from __future__ import annotations

from pathlib import Path
import json
import re
from catalog.reference_data import ruleset_for_edition
from .common import _ability_bonus_options_from_5etools, _ability_bonuses_from_5etools, _condition_immunities_from_5etools, _damage_modifiers_from_5etools, _darkvision_from_5etools, _speed_from_5etools, slug
from .innate_spells import _innate_spells_from_5etools
from .proficiencies import _attach_choice_proficiencies, _attach_fixed_proficiencies, _proficiencies_from_5etools


def _species_feat_grants_from_5etools(raw: dict) -> list[dict]:
    """5etools race `feats`: `{"any": n}` (a feat of any eligible category:
    Custom Lineage, Variant Human) -> `{"count": n, "category": None}`;
    `{"anyFromCategory": {"category": [c], "count": n}}` (Human/XPHB's
    Versatile: an Origin feat) -> `{"count": n, "category": c}`. Any other
    shape is ignored. Only three real records carry the field."""
    grants = []
    for entry in raw.get("feats") or []:
        if not isinstance(entry, dict):
            continue
        if isinstance(entry.get("any"), int) and not isinstance(entry["any"], bool):
            grants.append({"count": entry["any"], "category": None})
            continue
        spec = entry.get("anyFromCategory")
        if isinstance(spec, dict):
            cats = [c for c in spec.get("category") or [] if isinstance(c, str)]
            count = spec.get("count", 1)
            if len(cats) == 1 and isinstance(count, int) and not isinstance(count, bool):
                grants.append({"count": count, "category": cats[0]})
    return grants


def _variant_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _mod_replaces_entry(version: dict) -> bool:
    """True when an explicit `_versions` item swaps out a base trait
    (`_mod.entries` mode replaceArr), i.e. it is one alternative among
    several rather than an optional addition (appendArr)."""
    mods = (version.get("_mod") or {}).get("entries")
    mods = mods if isinstance(mods, list) else [mods]
    return any(isinstance(m, dict) and m.get("mode") == "replaceArr" for m in mods)


def _variant_from_source(vid: str, name: str, src: dict, resist: list[str]) -> dict:
    """One variant: only the structured data keys a version can change.
    A key explicitly set to null is recorded in `removes`."""
    removes = [k for k in ("skillProficiencies", "darkvision", "additionalSpells", "speed") if k in src and src[k] is None]
    walk, _ = _speed_from_5etools(src.get("speed"))
    return {
        "id": vid, "name": name,
        "speed": walk,
        "darkvision": _darkvision_from_5etools(src),
        "resist": resist,
        "innate_spells": _innate_spells_from_5etools({"additionalSpells": src.get("additionalSpells") or []}),
        "skill_proficiencies": src.get("skillProficiencies") if isinstance(src.get("skillProficiencies"), list) else None,
        "removes": removes,
    }


def _race_variants_from_5etools(raw: dict) -> list[dict]:
    """Mutually exclusive alternatives of a race from its `_versions`:
    explicit versions that REPLACE a base trait (name = the text after "; ",
    e.g. "Drow Lineage") and abstract versions with `_implementations`
    (Dragonborn colours; name = the abstract name with `{{var}}` filled in,
    resist from the implementation or its `_variables`). Races without
    `_versions` (almost all) get []."""
    variants: list[dict] = []
    for version in raw.get("_versions") or []:
        if not isinstance(version, dict):
            continue
        if isinstance(version.get("_abstract"), dict):
            template = str(version["_abstract"].get("name") or raw["name"])
            for impl in version.get("_implementations") or []:
                if not isinstance(impl, dict):
                    continue
                variables = impl.get("_variables") or {}
                name = re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables.get(m.group(1), m.group(0))), template)
                resist = [r for r in (impl.get("resist") or variables.get("resist") or []) if isinstance(r, str)]
                variants.append(_variant_from_source(_variant_slug(name), name, impl, resist))
        elif isinstance(version.get("name"), str) and _mod_replaces_entry(version):
            name = version["name"].split("; ", 1)[-1]
            resist = [r for r in (version.get("resist") or []) if isinstance(r, str)]
            variants.append(_variant_from_source(_variant_slug(name), name, version, resist))
    return variants


def _resist_options_from_5etools(raw: dict) -> dict | None:
    """The `resist: [{"choose": {"from": [...]}}]` shape (Dragonborn
    ancestry, 2024 Tiefling legacy, Reborn) as a Choice envelope of
    damage-type strings; fixed string entries stay in `resist`."""
    for entry in raw.get("resist") or []:
        if not isinstance(entry, dict):
            continue
        choose = entry.get("choose")
        if not isinstance(choose, dict) or not choose.get("from"):
            continue
        options = [{"option_type": "string", "string": str(t).capitalize()} for t in choose["from"] if isinstance(t, str)]
        if options:
            return {"choose": choose.get("count", 1), "type": "damage_resistances",
                    "from": {"option_set_type": "options_array", "options": options}}
    return None


_NAMELESS_SKIP_KEYS = frozenset({
    "source", "raceName", "raceSource", "page", "srd", "basicRules", "reprintedAs", "hasFluff",
    "hasFluffImages", "_versions", "_copy", "otherSources", "alias", "soundClip", "name", "overwrite",
})


def _merge_nameless_subraces(data: dict) -> tuple[list[dict], list[dict]]:
    """5etools models a race's default form as a nameless subrace (PHB
    Human: the +1-to-everything lives there; Dragonborn/Half-Elf/
    Half-Orc/Tiefling carry only reprint metadata). Fold each into its
    parent race and return (races, named subraces). Because the nameless
    form is the ALTERNATIVE to any named subrace, a parent that gained
    ability scores this way has them replaced (overwrite.ability) by every
    named subrace, as in 5etools."""
    races = [dict(r) for r in data.get("race", [])]
    by_key = {(r.get("name"), r.get("source")): r for r in races}
    named = []
    ability_merged_parents = set()
    for sub in data.get("subrace", []):
        if sub.get("name"):
            named.append(sub)
            continue
        parent = by_key.get((sub.get("raceName"), sub.get("raceSource")))
        if parent is None or "_copy" in parent:
            continue
        for key, value in sub.items():
            if key in _NAMELESS_SKIP_KEYS:
                continue
            if key not in parent:
                parent[key] = value
            elif isinstance(parent[key], list) and isinstance(value, list):
                parent[key] = parent[key] + value
            elif key == "darkvision" and isinstance(value, int) and isinstance(parent[key], int):
                parent[key] = max(parent[key], value)
            if key == "ability":
                ability_merged_parents.add((parent.get("name"), parent.get("source")))
    for i, sub in enumerate(named):
        if (sub.get("raceName"), sub.get("raceSource")) in ability_merged_parents:
            named[i] = {**sub, "overwrite": {**(sub.get("overwrite") or {}), "ability": True}}
    return races, named


def _trait_refs_from_entries(entries: list, id_prefix: str, race_ref: list[dict], subrace_ref: list[dict],
                              traits_by_index: dict[str, dict]) -> list[dict]:
    """Mints one synthetic trait per top-level `entries` item, added to
    traits_by_index (mutated in place, mirroring how the SRD loader builds
    one shared traits_by_index dict up front) so the existing
    trait-rendering/proficiency-scanning code in resolve.py (which already
    reads catalog.traits by id, already handles a trait with no
    `proficiencies` field correctly per Phase 3b-i) picks these up with
    zero changes. Subsequent tasks in this plan ADD proficiencies/resist/
    spells fields onto these same synthetic trait dicts — this task only
    creates them with description text."""
    trait_refs = []
    for i, entry in enumerate(entries or []):
        if not isinstance(entry, dict) or not entry.get("name"):
            continue  # skip bare strings / unnamed entries — not real traits
        trait_id = f"{id_prefix}-trait-{i}"
        desc_lines = [e for e in entry.get("entries", []) if isinstance(e, str)]
        traits_by_index[trait_id] = {
            "index": trait_id, "races": race_ref, "subraces": subrace_ref,
            "name": entry["name"], "desc": desc_lines, "proficiencies": [], "url": "",
        }
        trait_refs.append({"index": trait_id, "name": entry["name"], "url": ""})
    return trait_refs


def _race_from_5etools(raw: dict, traits_by_index: dict[str, dict]) -> dict | None:
    if "_copy" in raw:
        return None
    source = (raw.get("source") or "unknown").lower()
    index = f"{slug(raw['name'])}-{source}"

    size_map = {"S": "Small", "M": "Medium", "L": "Large"}
    sizes = raw.get("size") or ["M"]
    size = size_map.get(sizes[0], "Medium")
    # More than one listed size (30 races, always ["S","M"]): the player picks.
    size_options = list(dict.fromkeys(size_map[s] for s in sizes if s in size_map)) if len(sizes) > 1 else []

    race_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, race_ref, [], traits_by_index)
    _attach_fixed_proficiencies(_proficiencies_from_5etools(raw), trait_refs, index, race_ref, [], traits_by_index)
    _attach_choice_proficiencies(raw, trait_refs, index, race_ref, [], traits_by_index)

    resist, immune, vulnerable = _damage_modifiers_from_5etools(raw)
    walk, movement = _speed_from_5etools(raw.get("speed"))

    return {
        "index": index, "name": raw["name"],
        "speed": walk if walk is not None else 30,
        "movement": movement,  # non-walk modes: {fly|swim|climb: int | True (= walking speed)}
        "darkvision": _darkvision_from_5etools(raw),
        "resist_options": _resist_options_from_5etools(raw),
        "feat_grants": _species_feat_grants_from_5etools(raw),
        "variants": _race_variants_from_5etools(raw),
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", []), raw.get("lineage")),
        "alignment": "", "age": "", "size": size, "size_options": size_options, "size_description": "",
        "languages": [], "language_desc": "",
        "traits": trait_refs,
        "source": raw.get("source", ""),  # NEW field, SRD races don't have it (implicitly "SRD") — Task 6 uses this for filtering/labeling
        "ruleset": ruleset_for_edition(raw),
        # NEW fields (Task 5), 5etools' own field names — see
        # _damage_modifiers_from_5etools/_condition_immunities_from_5etools
        # docstrings for the shape confirmed against real data.
        "resist": resist, "immune": immune, "vulnerable": vulnerable,
        "condition_immune": _condition_immunities_from_5etools(raw),
        # NEW field (Task 6) — see _innate_spells_from_5etools' docstring
        # for the shape and its empirically-grounded scope (innate only,
        # not known/prepared/expanded). engine.resolve._species_innate_spells
        # merges this with the subrace's own innate_spells and resolves
        # spell_id against catalog.spells (this module has no Catalog
        # access, by design — see module docstring).
        "innate_spells": _innate_spells_from_5etools(raw),
    }


def _overwritten_trait_names(raw: dict) -> list[str]:
    """F1: names of the parent-race traits the subrace's entries replace: `entries[].data.overwrite` (a trait name string)."""
    out: list[str] = []
    for entry in raw.get("entries") or []:
        name = ((entry.get("data") or {}).get("overwrite")) if isinstance(entry, dict) else None
        if isinstance(name, str) and name not in out:
            out.append(name)
    return out


def _subrace_from_5etools(raw: dict, race_ids: set[str], traits_by_index: dict[str, dict]) -> dict | None:
    if "_copy" in raw or "name" not in raw:
        return None
    race_name = raw.get("raceName")
    race_source = raw.get("raceSource")
    if not race_name or not race_source:
        return None
    race_index = f"{slug(race_name)}-{race_source.lower()}"
    if race_index not in race_ids:
        return None  # dangling reference — not seen in real data, but skip rather than crash

    source = (raw.get("source") or "unknown").lower()
    index = f"{race_index}-{slug(raw['name'])}-{source}"

    subrace_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, [], subrace_ref, traits_by_index)
    _attach_fixed_proficiencies(_proficiencies_from_5etools(raw), trait_refs, index, [], subrace_ref, traits_by_index)
    _attach_choice_proficiencies(raw, trait_refs, index, [], subrace_ref, traits_by_index)

    resist, immune, vulnerable = _damage_modifiers_from_5etools(raw)
    walk, movement = _speed_from_5etools(raw.get("speed"))

    return {
        "index": index, "name": raw["name"],
        "race": {"index": race_index, "name": race_name, "url": ""},
        "source": raw.get("source", ""),
        "desc": "",
        "speed": walk,  # walk-speed override of the parent race, None = inherit
        "movement": movement,
        "darkvision": _darkvision_from_5etools(raw),
        "resist_options": _resist_options_from_5etools(raw),
        "feat_grants": _species_feat_grants_from_5etools(raw),
        # 5etools `overwrite.ability`: this subrace's scores REPLACE the race's.
        "overwrite_ability": bool((raw.get("overwrite") or {}).get("ability")),
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", [])),
        "racial_traits": trait_refs,
        "url": "",
        # NEW fields (Task 5) — subraces carry resist/immune/vulnerable/
        # conditionImmune independently of their parent race (e.g. each
        # Genasi subrace grants a different elemental resistance; Stout
        # Halfling grants poison resistance) — see
        # engine.resolve._species_damage_modifiers, which merges race and
        # subrace values together.
        "resist": resist, "immune": immune, "vulnerable": vulnerable,
        "condition_immune": _condition_immunities_from_5etools(raw),
        # NEW field (Task 6) — subraces carry their OWN additionalSpells
        # independently of their parent race (confirmed empirically,
        # 2026-09-24: 50/98 real subraces carry the field, e.g. all nine
        # real Tiefling MTF fiend-patron subraces and Duergar/MTF — the
        # same race-then-subrace-additions relationship Task 5 already
        # established for resist/immune/vulnerable).
        "innate_spells": _innate_spells_from_5etools(raw),
        # F1: the parent-race traits this subrace's own entries REPLACE (5etools `entries[].data.overwrite`, e.g. the MTF
        # Tiefling legacies replace "Infernal Legacy"); engine.resolve._species_innate_spells drops the race's innate
        # spells that trait granted.
        "overwrites_traits": _overwritten_trait_names(raw),
    }


def load_official_races(official_dir: Path) -> tuple[list[dict], list[dict], dict[str, dict]]:
    races_path = official_dir / "races.json"
    if not races_path.exists():
        return [], [], {}
    with open(races_path, encoding="utf-8") as f:
        data = json.load(f)

    traits_by_index: dict[str, dict] = {}
    races = []
    raw_races, raw_subraces = _merge_nameless_subraces(data)
    for raw in raw_races:
        converted = _race_from_5etools(raw, traits_by_index)
        if converted is not None:
            races.append(converted)

    race_ids = {r["index"] for r in races}
    race_rulesets = {r["index"]: r["ruleset"] for r in races}
    subraces = []
    for raw in raw_subraces:
        converted = _subrace_from_5etools(raw, race_ids, traits_by_index)
        if converted is not None:
            converted["ruleset"] = race_rulesets[converted["race"]["index"]]  # subspecies inherit the species' ruleset
            subraces.append(converted)

    return races, subraces, traits_by_index
