"""Query surface over the normalised SRD and official data.

`Catalog.load()` reads every real 2014 5e-bits file under
`chargen/data/srd/*.json`, normalises each record through `chargen.normalise`,
and exposes typed lookup/query methods over the result.

On top of that baseline, `_merge_official()` additively merges the official
(multi-sourcebook, mixed 2014/2024-edition) races, subraces and backgrounds
whenever `chargen.sources.has_official()` finds them — they live outside the
repo, in `chargen.sources.official_dir()`, and are put there by
`python3 -m chargen.sync --official`. On a machine that has never run that
fetch the merge is a safe no-op and the builder runs fully on SRD.

`load()` always loads the full 2014 SRD baseline regardless of the requested
`ruleset` — that data is real and must always be present — and the official
merge is likewise unfiltered: both editions' records are loaded and each
carries its own `.ruleset` field. No query method in this module filters by
ruleset.

A Draft carries no ruleset of its own to check those records against: each
chosen record's rules are applied per piece (a 2014 race brings its own
ability bonuses, a 2024 background brings its `ability_choice`), so any
combination is buildable. Picking pieces from different editions is
reported one layer up, by `chargen.validate.mixed_edition_warning()`, as a
non-blocking warning naming the pieces that disagree — never a problem.
"""

import json
from dataclasses import replace
from pathlib import Path

from chargen import normalise as N
from chargen.model import CharClass, ItemRef
from chargen.sources import has_official, official_dir, srd_dir

_OFFICIAL_FILES = {
    "races": "races.json",
    "backgrounds": "backgrounds.json",
}

_SRD_FILES = {
    "traits": "5e-SRD-Traits.json",
    "subraces": "5e-SRD-Subraces.json",
    "races": "5e-SRD-Races.json",
    "backgrounds": "5e-SRD-Backgrounds.json",
    "levels": "5e-SRD-Levels.json",
    "classes": "5e-SRD-Classes.json",
    "spells": "5e-SRD-Spells.json",
    "equipment": "5e-SRD-Equipment.json",
    "subclasses": "5e-SRD-Subclasses.json",
}

# Module-level cache keyed by ruleset string — a second load() with the same
# ruleset returns the cached instance instead of re-reading disk. Different
# ruleset values each get their own cache entry (and their own SRD read,
# since the baseline data doesn't vary by ruleset request today, but the
# requirement is "same call signature doesn't redundantly re-read", not "one
# read total across all rulesets").
_CACHE: dict[str, "Catalog"] = {}


def _read_json(path: Path):
    """Thin, monkeypatchable seam over disk reads — tests spy on this to
    prove caching actually avoids a second read."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _armor_from_5ebits(raw: dict) -> dict:
    """Armor isn't a Task 3 normalisation target (no Armor dataclass), so
    this is a small local helper that shapes each Armor-category Equipment
    entry into exactly what chargen.rules.armor_class()'s `armor` parameter
    expects: {"category": "light"|"medium"|"heavy", "base_ac": int, ...}."""
    cost = raw.get("cost")
    return {
        "id": raw["index"],
        "name": raw["name"],
        "category": raw["armor_category"].lower(),
        "base_ac": raw["armor_class"]["base"],
        "str_minimum": raw.get("str_minimum"),
        "stealth_disadvantage": raw.get("stealth_disadvantage"),
        "weight": raw.get("weight"),
        "cost": f"{cost['quantity']} {cost['unit']}" if cost else None,
    }


def _item_refs_from_5ebits_starting_equipment(raw_list: list[dict]) -> list[ItemRef]:
    """Same shape background_from_5ebits already normalises internally for a
    background's own starting equipment: [{"equipment": {...}, "quantity":
    int}, ...] -> [ItemRef, ...]. Reused here for a class's raw fixed list."""
    return [
        ItemRef(
            id=e["equipment"]["index"],
            name=e["equipment"]["name"],
            quantity=e.get("quantity", 1),
        )
        for e in raw_list or []
    ]


class Catalog:
    """In-memory, query-only view over the normalised SRD data."""

    def __init__(self, ruleset: str):
        self.ruleset = ruleset

        srd = srd_dir()

        traits_raw = _read_json(srd / _SRD_FILES["traits"])
        traits_by_index = {t["index"]: t for t in traits_raw}

        subraces_raw = _read_json(srd / _SRD_FILES["subraces"])
        self._subraces = [N.subrace_from_5ebits(r, traits_by_index) for r in subraces_raw]

        races_raw = _read_json(srd / _SRD_FILES["races"])
        self._races = [
            N.race_from_5ebits(r, traits_by_index, subraces=self._subraces) for r in races_raw
        ]
        self._race_by_id = {r.id: r for r in self._races}

        backgrounds_raw = _read_json(srd / _SRD_FILES["backgrounds"])
        self._backgrounds = [N.background_from_5ebits(r) for r in backgrounds_raw]
        self._background_by_id = {b.id: b for b in self._backgrounds}

        levels_raw = _read_json(srd / _SRD_FILES["levels"])
        classes_raw = _read_json(srd / _SRD_FILES["classes"])
        self._classes_raw_by_id = {c["index"]: c for c in classes_raw}
        self._classes: list[CharClass] = []
        for c in classes_raw:
            levels = N.class_level_rows_from_5ebits(levels_raw, c["index"])
            self._classes.append(N.class_from_5ebits(c, levels))
        self._class_by_id = {c.id: c for c in self._classes}

        self._spells = [N.spell_from_5ebits(r) for r in _read_json(srd / _SRD_FILES["spells"])]

        equipment_raw = _read_json(srd / _SRD_FILES["equipment"])
        self._weapons = [
            N.weapon_from_5ebits(r)
            for r in equipment_raw
            if r["equipment_category"]["name"] == "Weapon"
        ]
        self._armor = [
            _armor_from_5ebits(r)
            for r in equipment_raw
            if r["equipment_category"]["name"] == "Armor" and r.get("armor_category") != "Shield"
        ]
        self._gear = [
            ItemRef(id=r["index"], name=r["name"], quantity=1)
            for r in equipment_raw
            if r["equipment_category"]["name"] not in ("Weapon", "Armor")
        ]

        self._subclasses_raw = _read_json(srd / _SRD_FILES["subclasses"])

        self._merge_official()
        # Both sources are in `self._races`/`self._subraces` by now — link
        # each subrace onto its parent Race's own `.subraces` field, which is
        # what the API serialises and the UI reads. See _attach_subraces().
        self._attach_subraces()

    # -- loading / caching ---------------------------------------------

    @classmethod
    def load(cls, ruleset: str = "2024") -> "Catalog":
        if ruleset not in _CACHE:
            _CACHE[ruleset] = cls(ruleset)
        return _CACHE[ruleset]

    @classmethod
    def _clear_cache(cls) -> None:
        """Test-only escape hatch — production code never needs this."""
        _CACHE.clear()

    def _attach_subraces(self) -> None:
        """Rebuild every Race with its own subraces attached to `.subraces`.

        Two separate things have always found a race's subraces:
        `catalog.subraces(race_id)`, which filters `self._subraces` at query
        time, and the `Race.subraces` FIELD — and only the field is what the
        HTTP API serialises and the builder UI reads to decide whether to
        offer a subrace dropdown. The SRD path populated the field at
        construction time (race_from_5ebits takes a `subraces=` argument),
        but nothing attached the merged official subraces, so 92 of the 96
        subraces in a fully-fetched catalog were reachable by query and
        unreachable from the API/UI. This runs after the merge, over both
        sources at once, so the two ways of asking can no longer disagree.

        `Race` is frozen, so this replaces the objects rather than mutating
        them — and `_race_by_id` is rebuilt from the replacements, never
        left pointing at the pre-replace ones.
        """
        by_parent: dict[str, list] = {}
        for subrace in self._subraces:
            by_parent.setdefault(subrace.parent_race_id, []).append(subrace)
        self._races = [replace(r, subraces=by_parent.get(r.id, [])) for r in self._races]
        self._race_by_id = {r.id: r for r in self._races}

    def _merge_official(self) -> None:
        """Merge the official (2014+2024, multi-sourcebook) data when it is
        installed. A safe no-op whenever has_official() is False — the SRD
        baseline built above is untouched, and every query keeps returning
        exactly what it always did (see test_merge_official_is_a_safe_noop_*
        in tests/test_chargen_catalog.py).

        When chargen.sources.official_dir() is populated (by `python3 -m
        chargen.sync --official`), this reads races.json/backgrounds.json
        and normalises them through the already-proven *_from_5etools
        functions in chargen.normalise, additively extending the SRD lists
        built above — the official ids are source-qualified
        (e.g. "dwarf-phb"/"dwarf-xphb") so they never collide with or
        overwrite an SRD id like "dwarf". _copy/_mod-based records are
        skipped by the normalizers themselves (returning None), a disclosed
        cut documented on race_from_5etools/subrace_from_5etools/
        background_from_5etools.

        Classes and spells are intentionally left untouched here — no
        *_from_5etools normalizer exists for the 2024 class/spell shapes,
        and chargen/sync.py --official deliberately does not fetch
        class/*.json or spells/sources.json for the same reason (see that
        module's docstring). The SRD already fully covers the 2014-ruleset
        classes/spells the active campaign uses.
        """
        if not has_official():
            return

        d = official_dir()

        races_path = d / _OFFICIAL_FILES["races"]
        if races_path.exists():
            races_data = _read_json(races_path)
            self._races.extend(N.races_from_5etools(races_data.get("race", [])))
            self._subraces.extend(N.subraces_from_5etools(races_data.get("subrace", [])))

        backgrounds_path = d / _OFFICIAL_FILES["backgrounds"]
        if backgrounds_path.exists():
            backgrounds_data = _read_json(backgrounds_path)
            self._backgrounds.extend(
                N.backgrounds_from_5etools(backgrounds_data.get("background", []))
            )

        # self._race_by_id / self._background_by_id were built earlier in
        # __init__, from the SRD-only lists that existed before this method
        # ran — rebuild them now from the combined lists, or every official
        # race/background just added above would be invisible to race()/
        # background() lookups by id. self._subraces has no _by_id dict —
        # subraces(race_id) already filters self._subraces at query time,
        # so nothing to rebuild there.
        self._race_by_id = {r.id: r for r in self._races}
        self._background_by_id = {b.id: b for b in self._backgrounds}

    # -- races ------------------------------------------------------------

    def races(self) -> list:
        return list(self._races)

    def race(self, id: str):
        try:
            return self._race_by_id[id]
        except KeyError:
            raise KeyError(f"no race {id!r} in catalog") from None

    def subraces(self, race_id: str) -> list:
        return [s for s in self._subraces if s.parent_race_id == race_id]

    # -- backgrounds --------------------------------------------------------

    def backgrounds(self) -> list:
        return list(self._backgrounds)

    def background(self, id: str):
        try:
            return self._background_by_id[id]
        except KeyError:
            raise KeyError(f"no background {id!r} in catalog") from None

    # -- classes --------------------------------------------------------

    def classes(self) -> list:
        return list(self._classes)

    def class_(self, id: str):
        try:
            return self._class_by_id[id]
        except KeyError:
            raise KeyError(f"no class {id!r} in catalog") from None

    def subclasses(self, class_id: str) -> list[dict]:
        return [
            {"id": r["index"], "name": r["name"]}
            for r in self._subclasses_raw
            if r["class"]["index"] == class_id
        ]

    def level_row(self, class_id: str, level: int):
        char_class = self.class_(class_id)
        for row in char_class.levels:
            if row.level == level:
                return row
        raise KeyError(f"no level {level} row for class {class_id!r}")

    # -- spells --------------------------------------------------------

    def spells(self, cls: str | None = None, level: int | None = None,
               school: str | None = None, search: str | None = None) -> list:
        result = self._spells
        if cls is not None:
            result = [s for s in result if cls in s.classes]
        if level is not None:
            result = [s for s in result if s.level == level]
        if school is not None:
            needle = school.lower()
            result = [s for s in result if s.school.lower() == needle]
        if search is not None:
            needle = search.lower()
            result = [s for s in result if needle in s.name.lower()]
        return result

    # -- equipment --------------------------------------------------------

    def weapons(self, category: str | None = None) -> list:
        if category is None:
            return list(self._weapons)
        needle = category.lower()
        return [w for w in self._weapons if (w.category or "").lower() == needle]

    def armor(self) -> list[dict]:
        return list(self._armor)

    def gear(self) -> list[ItemRef]:
        return list(self._gear)

    def starting_equipment(self, class_id: str, background_id: str) -> list[ItemRef]:
        """Combine a class's own fixed starting-equipment list (raw
        `starting_equipment` on the class record — often empty in the real
        SRD data, e.g. Fighter's is `[]` because Fighter's real kit lives in
        the choice-based `starting_equipment_options`, which this task does
        not resolve) with the background's already-normalised
        `starting_equipment` (real ItemRefs, e.g. Acolyte's holy symbol/
        clothes/pouch/money). For Fighter+Acolyte today this means the
        return value is exactly Acolyte's own starting equipment."""
        self.class_(class_id)  # validate id, informative KeyError on miss
        background = self.background(background_id)
        class_raw = self._classes_raw_by_id.get(class_id, {})
        class_items = _item_refs_from_5ebits_starting_equipment(
            class_raw.get("starting_equipment", [])
        )
        return class_items + list(background.starting_equipment)
