"""Converts the wider, multi-sourcebook 5etools-src race/subrace/background
data (fetched by `python3 -m chargen.sync --official` into
chargen.sources.official_dir(), never committed to this repo — see that
module and chargen/sync.py for the fetch/licensing details this module
inherits without re-litigating) into the SAME dict shape
catalog/loader.py already produces for the bundled 2014 SRD data. This is
a from-scratch v2-native normalizer — it does NOT reuse chargen.catalog's
own normalizer (chargen.normalise.race_from_5etools etc.), because that
targets chargen's own frozen dataclasses, a different, incompatible
object model from the raw dicts catalog/choices.py and engine/resolve.py
read throughout. Only chargen.sources' pure path/existence helpers are
shared.

Every record's id is source-qualified (e.g. "aasimar-vgm") using the raw
5etools "source" field lowercased, so a reprint across multiple books
(Aasimar in VGM, then MPMM, then XPHB) produces multiple distinct
records, and nothing here can ever collide with a bundled SRD id (SRD ids
have no source suffix at all).

Subrace ids are additionally scoped by their parent race's own id (e.g.
"aasimar-vgm-fallen-vgm"), not just their own (name, source) — empirically
confirmed against the real fetched data that (name, source) alone is NOT
globally unique for subraces: "Ixalan"/PSX names a subrace of both
Goblin/PSZ and Vampire/PSZ, and "Variant; Mark of Finding"/ERLW names a
subrace of both Half-Orc/PHB and Human/PHB. Scoping by parent race id
resolves both collisions.

_copy/_mod-based records (5etools' own "defined as another record plus a
diff" shorthand) are skipped — real, but a bounded, disclosed cut, same
scope decision v1's own chargen/normalise.py already made for the same
reason (see that module's docstring). Subrace records with no "name"
field are also skipped: empirically these are "SRD-complete" placeholder
markers (e.g. for Human/Half-Elf/Half-Orc/Tiefling/Dragonborn in the PHB)
that carry no selectable content of their own, not real subraces.

chargen lives at the repo root, a SIBLING of server/ — not a subpackage
of it. Every real way this server runs (`cd server && python app.py` in
production, `cd server && pytest` for tests) has `server/` as the
working directory, which does not put the repo root on sys.path. The
insert below is what makes `from chargen.sources import ...` resolve —
this module is the ONLY place in the whole codebase that imports
chargen.sources directly; official_dir/has_official are re-exported
from here (see the import line right below) so every caller (loader.py,
every test) imports them FROM catalog.official_source instead, and
never needs to know chargen lives one level up at all.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

_repo_root = Path(__file__).resolve().parents[2]  # server/catalog/official_source.py -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from chargen.sources import official_dir, has_official  # noqa: E402  (must follow the sys.path fix above)


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("'", "")


def _ability_bonuses_from_5etools(ability_list: list[dict]) -> list[dict]:
    """Converts 5etools' `ability` field (a list of dicts, each either a
    flat {"cha": 2, ...} fixed-bonus map or containing a "choose" sub-key)
    into SRD-shaped ability_bonuses — ONLY the fixed-bonus portion; the
    choose-N portion is out of scope for this task (a later task in this
    plan adds ability_bonus_options), since SRD keeps these as two
    distinct fields (ability_bonuses vs ability_bonus_options) and so does
    this module, for the same reason: build_choice_template only ever
    looks at ability_bonus_options, and _species_ability_bonuses only
    ever looks at ability_bonuses — keeping them separate here means both
    existing functions need no changes."""
    bonuses = []
    for entry in ability_list or []:
        for key, val in entry.items():
            if key == "choose":
                continue
            bonuses.append({"ability_score": {"index": key, "name": key.upper(), "url": ""}, "bonus": val})
    return bonuses


def _ability_bonus_options_from_5etools(ability_list: list[dict]) -> dict | None:
    """Converts the CHOOSE portion of 5etools' `ability` field into the
    SAME ability_bonus_options envelope shape SRD's Half-Elf record
    already uses ({"choose": N, "type": "ability_bonuses", "from": {...}})
    — this is exactly what build_choice_template/build_choice_options
    (catalog/choices.py) and _species_ability_bonus_choice_template
    (engine/resolve.py) already know how to consume, unmodified. A race
    can carry BOTH a fixed bonus (handled separately, by
    _ability_bonuses_from_5etools, from the SAME entry) and this choice
    envelope at once — e.g. Aetherborn: fixed +2 CHA, plus choose 2 of
    {STR,DEX,CON,INT,WIS} for +1 each — since SRD keeps ability_bonuses
    and ability_bonus_options as two independent fields, and so do the
    two functions here (_species_ability_bonuses/
    _species_ability_bonus_choice_template read them independently too).

    Only entries shaped {"choose": {"from": [...], "count": N}} are
    handled — confirmed empirically (2026-09-23, against the real fetched
    races.json) that every race-level entry using "choose" matches this
    shape, EXCEPT TCE's "Custom Lineage" pseudo-race, which uses
    {"from": [...], "amount": 2} instead of "count": a fundamentally
    different, more flexible ASI split (TCE's actual rule: +2 to one
    ability OR +1 to two) that this simple choose-N-for-+1-each envelope
    can't represent either way. Entries without a "count" key are
    skipped rather than guessed at (silently defaulting a missing
    "count" to 1 would misrepresent Custom Lineage's real mechanics) —
    same out-of-scope reasoning as the "weighted" shape seen on
    backgrounds (Phase 4b), not races, which this also doesn't handle."""
    for entry in ability_list or []:
        choose = entry.get("choose")
        if not choose or "count" not in choose:
            continue
        from_list = choose.get("from", [])
        count = choose["count"]
        options = [
            {"option_type": "ability_bonus", "ability_score": {"index": ab, "name": ab.upper(), "url": ""}, "bonus": 1}
            for ab in from_list
        ]
        return {"choose": count, "type": "ability_bonuses", "from": {"option_set_type": "options_array", "options": options}}
    return None


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
    index = f"{_slug(raw['name'])}-{source}"

    size_map = {"S": "Small", "M": "Medium", "L": "Large"}
    sizes = raw.get("size") or ["M"]
    size = size_map.get(sizes[0], "Medium")

    race_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, race_ref, [], traits_by_index)

    return {
        "index": index, "name": raw["name"],
        "speed": raw.get("speed") if isinstance(raw.get("speed"), int) else 30,
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "ability_bonus_options": _ability_bonus_options_from_5etools(raw.get("ability", [])),
        "alignment": "", "age": "", "size": size, "size_description": "",
        "languages": [], "language_desc": "",
        "traits": trait_refs,
        "source": raw.get("source", ""),  # NEW field, SRD races don't have it (implicitly "SRD") — Task 6 uses this for filtering/labeling
    }


def _subrace_from_5etools(raw: dict, race_ids: set[str], traits_by_index: dict[str, dict]) -> dict | None:
    if "_copy" in raw or "name" not in raw:
        return None
    race_name = raw.get("raceName")
    race_source = raw.get("raceSource")
    if not race_name or not race_source:
        return None
    race_index = f"{_slug(race_name)}-{race_source.lower()}"
    if race_index not in race_ids:
        return None  # dangling reference — not seen in real data, but skip rather than crash

    source = (raw.get("source") or "unknown").lower()
    index = f"{race_index}-{_slug(raw['name'])}-{source}"

    subrace_ref = [{"index": index, "name": raw["name"], "url": ""}]
    trait_refs = _trait_refs_from_entries(raw.get("entries", []), index, [], subrace_ref, traits_by_index)

    return {
        "index": index, "name": raw["name"],
        "race": {"index": race_index, "name": race_name, "url": ""},
        "desc": "",
        "ability_bonuses": _ability_bonuses_from_5etools(raw.get("ability", [])),
        "racial_traits": trait_refs,
        "url": "",
    }


def load_official_races(official_dir: Path) -> tuple[list[dict], list[dict], dict[str, dict]]:
    races_path = official_dir / "races.json"
    if not races_path.exists():
        return [], [], {}
    with open(races_path, encoding="utf-8") as f:
        data = json.load(f)

    traits_by_index: dict[str, dict] = {}
    races = []
    for raw in data.get("race", []):
        converted = _race_from_5etools(raw, traits_by_index)
        if converted is not None:
            races.append(converted)

    race_ids = {r["index"] for r in races}
    subraces = []
    for raw in data.get("subrace", []):
        converted = _subrace_from_5etools(raw, race_ids, traits_by_index)
        if converted is not None:
            subraces.append(converted)

    return races, subraces, traits_by_index
