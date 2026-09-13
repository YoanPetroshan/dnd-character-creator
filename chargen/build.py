"""Draft -> a validated, game-playable character sheet.

`build(draft)` is the one entry point the HTTP API and the UI call. It takes
a Draft — the plain dict of ids and choices a UI collects — and returns
`(sheet, problems, warnings)`:

- `sheet` is a plain, YAML-safe dict in exactly the shape
  `skills/dnd/scripts/library.py` saves and the running game reads. Two real
  consumers pin that shape down: `engine.state.party_names()` finds the
  party by the `# <Name>` heading library renders from `sheet["name"]`, and
  `engine.local_context.read_hp()` reads the `**HP:** cur / max` line
  library renders from `sheet["combat"]`.
- `problems` is every legality failure, as strings a UI can show verbatim.
- `warnings` is informational only and never blocks a build — today this is
  exactly one kind of entry: the chosen race/subrace/background span more
  than one ruleset edition.

**build() never silently repairs an illegal draft.** If `problems` is
non-empty the sheet comes back as `{}` rather than a half-computed one: a
sheet derived from illegal inputs (a skill that doesn't exist, a level with
no rules row) is either a crash or nonsense, and handing a UI nonsense that
looks like a character is worse than handing it nothing plus the reasons.

Scope, deliberately: one class per character (multiclass is a later
feature — the sheet's `classes` list and `hit_dice` list are both plural
shapes that already accommodate it, but this task only ever fills one
entry); no Warlock pact slots (`pact_magic_slots` is always None).

Armour Class is deliberately *not* stored. The game derives it —
`char_state_derive.compute_ac()` reads the equipped items off the sheet
every time it needs an AC — and neither `char_state_schema.CombatStats` nor
`sheet_import.blank_sheet()` (the repo's two existing definitions of this
shape) has a field for it. What makes AC come out right is the `equipment`
list this module builds: the worn armour and the shield are marked
`equipped: True`, which is exactly what `compute_ac` looks for. Storing a
second copy here would only be a number that drifts the moment a character
changes armour in play. Unarmored Defense (Barbarian/Monk) is a documented
gap in that derivation, not something this module papers over.

This module imports nothing outside `chargen` and the standard library — no
flask, no engine, no library. `build()` only *produces* a dict; saving it is
somebody else's job.
"""

from __future__ import annotations

from chargen import rules, validate as V
from chargen.catalog import Catalog
from chargen.validate import CASTING_ABILITY, apply_ability_bonuses  # re-exported

__all__ = ["build", "apply_ability_bonuses", "CASTING_ABILITY"]


def _features(race, subrace, background, char_class, level: int) -> list[dict]:
    """Race traits, subrace traits, the background feature, and every class
    feature from level 1 up to and including `level`.

    Subrace traits are tagged "Race" like the race's own: the three sources
    a consumer distinguishes are Race / Background / Class, and a subrace is
    part of a character's race, not a fourth thing.

    Class features arrive from `ClassLevelRow.features` as bare name strings
    — the SRD's level table carries no description text at this layer — so
    their `description` is an empty string rather than an invented one.
    """
    out: list[dict] = []
    for source_obj in (race, subrace):
        for trait in getattr(source_obj, "traits", None) or []:
            out.append({"name": trait.name, "description": trait.text, "source": "Race"})

    feature = getattr(background, "feature", None)
    if feature is not None:
        out.append({"name": feature.name, "description": feature.text,
                    "source": "Background"})

    for row in char_class.levels:
        if row.level <= level:
            for name in row.features or []:
                out.append({"name": name, "description": "", "source": "Class"})
    return out


def _languages(race, background) -> list[str]:
    """Race languages plus the background's, deduplicated, order preserved.

    A background whose `languages` is an int is a *count* of free languages
    the player still has to pick, not a list of names — there is nothing to
    add, and inventing names is not this layer's business.
    """
    out: list[str] = []
    seen: set[str] = set()
    from_background = getattr(background, "languages", None)
    if not isinstance(from_background, list):
        from_background = []
    for language in list(getattr(race, "languages", None) or []) + from_background:
        if language not in seen:
            seen.add(language)
            out.append(language)
    return out


def _dedup(*lists) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for items in lists:
        for item in items or []:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return out


def _equipment(draft: dict, catalog, armor: dict | None) -> list[dict]:
    """The starting kit, plus whatever the draft actually put on, plus
    whatever the player actively chose (`chosen_weapons`/`chosen_gear`).

    Worn armor and a carried shield come back `equipped: True`; everything
    the class/background kit provides, and everything the player chose,
    comes back `equipped: False`, since the catalog's ItemRefs say nothing
    about what is worn. A chosen weapon/gear entry is guaranteed to be a
    dict with a catalogued id and, when present, a positive int quantity by
    the time this runs — `validate_equipment()` catches a malformed entry
    or an unknown id upfront, and `build()` returns early on any problem
    before ever reaching this function — so no problems handling is needed
    here. A chosen item that
    matches a row the class/background kit already grants (same name, same
    equipped state) merges into that row with summed quantity, rather than
    duplicating it.
    """
    out: list[dict] = []
    if armor is not None:
        out.append({"name": armor["name"], "equipped": True, "quantity": 1})
    if draft.get("shield"):
        out.append({"name": "Shield", "equipped": True, "quantity": 1})
    for item in catalog.starting_equipment(draft["class_id"], draft["background_id"]):
        out.append({"name": item.name, "equipped": False,
                    "quantity": int(item.quantity or 1)})

    weapons_by_id = {w.id: w for w in catalog.weapons()}
    gear_by_id = {g.id: g for g in catalog.gear()}
    chosen = (draft.get("chosen_weapons") or []) + (draft.get("chosen_gear") or [])
    for entry in chosen:
        item = weapons_by_id.get(entry["id"]) or gear_by_id.get(entry["id"])
        name = item.name
        quantity = int(entry.get("quantity", 1))
        existing = next((row for row in out
                         if row["name"] == name and not row["equipped"]), None)
        if existing is not None:
            existing["quantity"] += quantity
        else:
            out.append({"name": name, "equipped": False, "quantity": quantity})
    return out


def _spells(draft: dict, char_class, is_prepared_caster: bool,
            is_known_caster: bool) -> list[dict]:
    if is_prepared_caster:
        return [{"name": n, "cls": char_class.name, "prepared": True}
                for n in draft.get("spells_prepared") or []]
    if is_known_caster:
        return [{"name": n, "cls": char_class.name, "prepared": False}
                for n in draft.get("spells_known") or []]
    return []


def build(draft: dict, catalog: Catalog | None = None) -> tuple[dict, list[str], list[str]]:
    """Turn a Draft into (sheet, problems, warnings).

    `catalog` defaults to `Catalog.load()` — the requested-ruleset-based
    default this used to have is gone along with draft["ruleset"] itself;
    Catalog.load() has always loaded the full SRD+official baseline
    regardless of what ruleset it's asked for (see chargen/catalog.py's
    own module docstring), so this was never really selecting anything.

    problems: the character cannot legally be built until every one of
      these is resolved.
    warnings: informational only, never blocks a build. Today this is
      exactly one kind of entry — the chosen race/subrace/background span
      more than one ruleset edition.
    """
    if catalog is None:
        catalog = Catalog.load()

    problems, warnings = V.validate(draft, catalog)
    if problems:
        return {}, problems, warnings

    # -- everything below is reached only for a fully legal draft ---------

    level: int = draft["level"]
    race = catalog.race(draft["race_id"])
    subrace = None
    if draft.get("subrace_id"):
        subrace = next(s for s in catalog.subraces(race.id)
                       if s.id == draft["subrace_id"])
    background = catalog.background(draft["background_id"])
    char_class = catalog.class_(draft["class_id"])
    subclass = None
    if draft.get("subclass_id"):
        subclass = next(s for s in catalog.subclasses(char_class.id)
                        if s["id"] == draft["subclass_id"])
    level_row = catalog.level_row(char_class.id, level)

    scores = apply_ability_bonuses(
        draft["ability_scores"], race, subrace, background,
        draft.get("ability_choice_index"), draft.get("ability_choice_assignment"))

    con_mod = rules.ability_modifier(scores["CON"])

    armor = None
    if draft.get("equipped_armor_id"):
        armor = next(a for a in catalog.armor() if a["id"] == draft["equipped_armor_id"])
    hp = rules.hit_points(char_class.hit_die, con_mod, level,
                          method=draft.get("hp_method") or "max_then_average")

    casting_ability = CASTING_ABILITY.get(char_class.name)
    is_prepared_caster = rules.spells_prepared_limit(char_class.name, level, 0) is not None
    is_known_caster = rules.known_spells_limit(char_class.name, level) is not None
    is_caster = is_prepared_caster or is_known_caster

    sheet = {
        "name": str(draft["name"]).strip(),
        "race": subrace.name if subrace is not None else race.name,
        "background": background.name,
        "alignment": draft.get("alignment") or "",
        "player": draft.get("player") or "",
        "classes": [{
            "cls": char_class.name,
            "subclass": subclass["name"] if subclass else "",
            "level": level,
        }],
        "ability_scores": {a: scores[a] for a in V.ABILITIES},
        "combat": {
            "hp_current": hp,
            "hp_max": hp,
            "hp_temp": 0,
            "speed": race.speed,
            "death_saves": {"successes": 0, "failures": 0},
            "hit_dice": [{"cls": char_class.name, "die": char_class.hit_die, "used": 0}],
        },
        "proficiencies": {
            "saving_throws": list(char_class.saving_throws),
            # The class picks plus what the background grants outright:
            # Acolyte's Insight/Religion are proficiencies the character
            # really has, and char_state_derive reads this one list to
            # decide whether a skill check gets the proficiency bonus.
            "skills": _dedup(draft.get("skill_picks"),
                             background.skill_proficiencies),
            "armor": list(char_class.armor),
            "weapons": list(char_class.weapons),
            "tools": _dedup(char_class.tools, background.tool_proficiencies),
            "languages": _languages(race, background),
        },
        "conditions": {
            "inspiration": False,
            "exhaustion": 0,
            "active": [],
            "attunement": [],
            "weapon_mastery": [],
        },
        "personality": {"traits": "", "ideals": "", "bonds": "", "flaws": ""},
        "features_traits": _features(race, subrace, background, char_class, level),
        "backstory": draft.get("backstory") or "",
        "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
        "equipment": _equipment(draft, catalog, armor),
        "misc_items": [],
        "spellcasting": (
            [{"cls": char_class.name, "ability": casting_ability}]
            if is_caster and casting_ability else []
        ),
        "spells": _spells(draft, char_class, is_prepared_caster, is_known_caster),
        "spell_slots": (
            {lvl: {"max": count, "used": 0}
             for lvl, count in sorted((level_row.spell_slots or {}).items())}
            if is_caster else {}
        ),
        "pact_magic_slots": None,
    }
    return sheet, [], warnings
