"""Legality checks for a character Draft, plus the ability-bonus maths.

`chargen.build.build()` calls `validate()` first and only assembles a sheet
when it comes back empty — a draft is either legal or it is not, and an
illegal one is never silently repaired. Every failure is one human-readable
string naming the offending value and what was expected, specific enough for
a UI to show a player verbatim.

Why the ability-bonus maths lives here rather than in build.py: validating a
2024 background's ability pick and *applying* it are the same domain rule
seen from two sides, and the spell checks need the FINAL (post-bonus)
ability modifier to compute a prepared-spells limit. Keeping both in this
module lets `validate()` be self-contained and keeps build.py importing
validate (never the reverse).

Nothing here touches disk, the network, or the game's file-saving machinery
— the catalog is passed in.
"""

from __future__ import annotations

from chargen import rules

ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

# The two hit-point methods rules.hit_points() actually implements. Anything
# else silently took its `else` branch (max_then_average) before
# validate_hp_method() existed — see that function.
HP_METHODS = ("max_then_average", "max_then_max")

STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)

# 5e SRD point-buy: cost of raising a score from 8. 27 points to spend.
POINT_BUY_COST = {8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9}
POINT_BUY_BUDGET = 27

ROLL_MIN, ROLL_MAX = 3, 18

MIN_LEVEL, MAX_LEVEL = 1, 20

# The spellcasting ability of each SRD class. The four prepared casters and
# the four known casters all need one (a known caster still has a spell save
# DC / attack bonus); the four non-casters have none at all.
CASTING_ABILITY = {
    "Cleric": "WIS",
    "Druid": "WIS",
    "Paladin": "CHA",
    "Wizard": "INT",
    "Bard": "CHA",
    "Ranger": "WIS",
    "Sorcerer": "CHA",
    "Warlock": "CHA",
}


# ---------------------------------------------------------------------------
# ability bonuses (Global Finding 1)
# ---------------------------------------------------------------------------

def apply_ability_bonuses(
    base_scores: dict[str, int],
    race,
    subrace,
    background,
    choice_index: int | None,
    choice_assignment: dict[str, int] | None,
) -> dict[str, int]:
    """Every chosen piece contributes its own bonus mechanic, independent
    of any global ruleset. A race/subrace's fixed ability_bonuses apply
    if present; a background's weighted ability_choice applies if the
    background carries one. A character can legally mix pieces from
    different editions — mixing is flagged as an informational warning
    by build(), never rejected here. (Replaces the old draft["ruleset"]-
    gated branch: see docs/superpowers/specs/2026-08-25-character-builder-v2-design.md §B.1.)
    """
    final = dict(base_scores)
    for source in (race, subrace):
        if source is not None:
            for ability, bonus in (source.ability_bonuses or {}).items():
                final[ability] = final.get(ability, 0) + bonus
    if background is not None and background.ability_choice and choice_index is not None:
        pattern = background.ability_choice[choice_index]
        for ability, bonus in (choice_assignment or {}).items():
            if ability in pattern.options:
                final[ability] = final.get(ability, 0) + bonus
    return final


# ---------------------------------------------------------------------------
# individual checks
# ---------------------------------------------------------------------------

def validate_name(draft: dict) -> list[str]:
    if not str(draft.get("name") or "").strip():
        return ["character name is empty — a character needs a name"]
    return []


def validate_hp_method(draft: dict) -> list[str]:
    """`rules.hit_points()` dispatches on this string with an `if
    method == "max_then_max" ... else` — so every value that is not one of
    the two real ones, a typo very much included, quietly becomes
    "max_then_average" and the player is told nothing. A value that selects
    a rules branch may never fall through to a default.
    """
    method = draft.get("hp_method")
    if method is None or (method in HP_METHODS and isinstance(method, str)):
        # None/absent is the documented "use the default" case — build()
        # spells it `draft.get("hp_method") or "max_then_average"`.
        return []
    return [f"hp_method must be {' or '.join(repr(m) for m in HP_METHODS)}, "
            f"got {method!r}"]


def validate_level(draft: dict) -> list[str]:
    level = draft.get("level")
    if not isinstance(level, int) or isinstance(level, bool):
        return [f"level {level!r} is not a whole number"]
    if not (MIN_LEVEL <= level <= MAX_LEVEL):
        return [f"level {level} is outside the playable range "
                f"{MIN_LEVEL}-{MAX_LEVEL}"]
    return []


def validate_ability_scores(draft: dict) -> list[str]:
    """The base (pre-bonus) scores must be legal for the method that
    produced them."""
    problems: list[str] = []
    scores = draft.get("ability_scores") or {}

    missing = [a for a in ABILITIES if a not in scores]
    if missing:
        problems.append(f"ability scores are missing: {', '.join(missing)}")
    extra = [a for a in scores if a not in ABILITIES]
    if extra:
        problems.append(f"unknown ability names in ability_scores: {', '.join(sorted(extra))}")

    present = {a: scores[a] for a in ABILITIES if a in scores}
    for ability, value in present.items():
        if not isinstance(value, int) or isinstance(value, bool):
            problems.append(f"{ability} score {value!r} is not a whole number")
    present = {a: v for a, v in present.items()
               if isinstance(v, int) and not isinstance(v, bool)}

    method = draft.get("ability_method")
    if method == "roll":
        for ability, value in present.items():
            if not (ROLL_MIN <= value <= ROLL_MAX):
                problems.append(
                    f"rolled {ability} score {value} is outside "
                    f"{ROLL_MIN}-{ROLL_MAX}")
    elif method == "standard_array":
        if missing or len(present) != len(ABILITIES):
            pass  # already reported; the multiset check would only add noise
        elif sorted(present.values(), reverse=True) != sorted(STANDARD_ARRAY, reverse=True):
            problems.append(
                "scores " + ", ".join(f"{a} {present[a]}" for a in ABILITIES)
                + " are not the standard array "
                + f"({', '.join(str(v) for v in STANDARD_ARRAY)}, in any order)")
    elif method == "point_buy":
        spent = 0
        costed = True
        for ability, value in present.items():
            if value not in POINT_BUY_COST:
                costed = False
                problems.append(
                    f"point-buy {ability} score {value} is outside "
                    f"{min(POINT_BUY_COST)}-{max(POINT_BUY_COST)}")
            else:
                spent += POINT_BUY_COST[value]
        if costed and spent > POINT_BUY_BUDGET:
            problems.append(
                f"point-buy scores cost {spent} points, more than the "
                f"{POINT_BUY_BUDGET} available")
    else:
        problems.append(
            f"ability_method {method!r} is not one of "
            "'roll', 'standard_array', 'point_buy'")

    return problems


def validate_race(draft: dict, catalog) -> tuple[object | None, object | None, list[str]]:
    """Resolve race and subrace, reporting anything that doesn't exist or
    doesn't belong together. Returns (race, subrace, problems)."""
    problems: list[str] = []
    race_id = draft.get("race_id")
    try:
        race = catalog.race(race_id)
    except KeyError:
        return None, None, [f"race {race_id!r} is not in the catalog"]

    subrace = None
    subrace_id = draft.get("subrace_id")
    if subrace_id:
        options = catalog.subraces(race.id)
        subrace = next((s for s in options if s.id == subrace_id), None)
        if subrace is None:
            names = ", ".join(s.id for s in options) or "none"
            problems.append(
                f"subrace {subrace_id!r} does not belong to race {race.name} "
                f"(options: {names})")

    # A 2014-style race may offer its own ability-score choice on top of its
    # fixed bonuses (Half-Elf: CHA +2, then "choose two other scores, each
    # +1"). The Draft has no field to express which abilities the player
    # picked, so this builder cannot apply it — and silently shorting the
    # character those points is exactly the kind of quiet repair build()
    # must never do. Report it instead; applying it needs a Draft-shape
    # change. This is a real gap in what the Draft can express, not an
    # edition mismatch — it stays a blocking problem regardless of which
    # other pieces are chosen. Only SRD-loaded (2014) race records ever
    # populate `ability_choice` at all (official/2024 race records always
    # set it to None — see chargen/normalise.py), so this needs no ruleset
    # check of its own.
    if getattr(race, "ability_choice", None):
        problems.append(
            f"{race.name} offers an ability score choice "
            f"({race.ability_choice}) that this draft cannot express yet — "
            "race ability-choice picks are not yet supported")

    return race, subrace, problems


def mixed_edition_warning(race, subrace, background) -> str | None:
    """None if every chosen piece shares one ruleset (or there's nothing
    to compare). Otherwise one Bulgarian sentence naming which pieces
    disagree. Class/subclass are deliberately excluded — the catalog has
    no official 2024 class data yet (a disclosed Task 10 cut), so every
    class/subclass is ruleset "2014" today and would never contribute
    real variance."""
    pieces = [(p, label) for p, label in (
        (race, race.name if race else None),
        (subrace, subrace.name if subrace else None),
        (background, background.name if background else None),
    ) if p is not None]
    editions = {p.ruleset for p, _ in pieces}
    if len(editions) <= 1:
        return None
    named = ", ".join(f"{label} ({p.ruleset})" for p, label in pieces)
    return f"тази комбинация смесва издания — {named} — героят е валиден, но не следва изцяло едни правила"


def validate_background(draft: dict, catalog) -> tuple[object | None, list[str]]:
    background_id = draft.get("background_id")
    try:
        return catalog.background(background_id), []
    except KeyError:
        return None, [f"background {background_id!r} is not in the catalog"]


def validate_class(draft: dict, catalog) -> tuple[object | None, dict | None, list[str]]:
    """Resolve class and subclass. Subclass *level gating* is deliberately
    not checked: the SRD subclass data carries no unlock level, and this
    module never invents a rule it cannot look up."""
    problems: list[str] = []
    class_id = draft.get("class_id")
    try:
        char_class = catalog.class_(class_id)
    except KeyError:
        return None, None, [f"class {class_id!r} is not in the catalog"]

    subclass = None
    subclass_id = draft.get("subclass_id")
    if subclass_id:
        options = catalog.subclasses(char_class.id)
        subclass = next((s for s in options if s["id"] == subclass_id), None)
        if subclass is None:
            names = ", ".join(s["id"] for s in options) or "none"
            problems.append(
                f"subclass {subclass_id!r} does not belong to {char_class.name} "
                f"(options: {names})")
    return char_class, subclass, problems


def validate_skills(draft: dict, char_class, background=None) -> list[str]:
    """Class skill picks: the right count, all from the class's own option
    list, no duplicates — and none of them a skill the background already
    grants for free, which would spend a class pick on a proficiency the
    character has either way."""
    problems: list[str] = []
    picks = list(draft.get("skill_picks") or [])
    granted = list(getattr(background, "skill_proficiencies", None) or [])
    choice = getattr(char_class, "skill_choice", None) or {}
    count = choice.get("count")
    options = list(choice.get("options") or [])

    duplicates = sorted({s for s in picks if picks.count(s) > 1})
    if duplicates:
        problems.append(
            f"duplicate skill picks for {char_class.name}: {', '.join(duplicates)}")

    if count is not None and len(picks) != count:
        problems.append(
            f"{char_class.name} picks exactly {count} skill(s), "
            f"but {len(picks)} were chosen ({', '.join(picks) or 'none'})")

    for skill in picks:
        if options and skill not in options:
            problems.append(
                f"skill {skill!r} is not a valid choice for {char_class.name} "
                f"(options: {', '.join(options)})")
        if skill in granted:
            problems.append(
                f"skill {skill!r} is already granted by the "
                f"{background.name} background — pick a different one, "
                "choosing it again wastes the class pick")
    return problems


def validate_ability_choice(draft: dict, background) -> list[str]:
    """The background ability pick (Global Finding 1 / finding 2).

    Only meaningful when the chosen background itself carries an
    `ability_choice` (2024-style backgrounds do; 2014 backgrounds carry
    none at all, so the draft's index/assignment are ignored there rather
    than rejected). Checked against the background's own data, not a
    global `draft["ruleset"]` — that field no longer exists on the Draft;
    see `validate_race()`'s Half-Elf check above for the same pattern.
    """
    if background is None:
        return []
    # A 2014-style background carries no ability_choice at all — nothing to
    # pick, so the draft's index/assignment are ignored, not rejected. (This
    # was two guards: the second, `if not choices`, was unreachable behind
    # the first, and its message still spoke of a `draft["ruleset"]` of
    # "2024" that the Draft no longer has.)
    choices = list(getattr(background, "ability_choice", None) or [])
    if not choices:
        return []

    problems: list[str] = []
    index = draft.get("ability_choice_index")

    if not isinstance(index, int) or isinstance(index, bool) or not (0 <= index < len(choices)):
        return [f"ability_choice_index {index!r} is not one of the "
                f"{len(choices)} ability options {background.name} offers "
                f"(expected 0-{len(choices) - 1})"]

    chosen = choices[index]
    assignment = draft.get("ability_choice_assignment")
    if not isinstance(assignment, dict) or not assignment:
        return [f"ability_choice_assignment is missing — {background.name} "
                f"option {index} assigns {chosen.weights} across "
                f"{len(chosen.weights)} of {', '.join(chosen.options)}"]

    for ability in assignment:
        if ability not in chosen.options:
            problems.append(
                f"ability {ability!r} is not one of the abilities "
                f"{background.name} option {index} may boost "
                f"(options: {', '.join(chosen.options)})")

    if len(assignment) != len(chosen.weights):
        problems.append(
            f"{background.name} option {index} boosts exactly "
            f"{len(chosen.weights)} distinct abilities, but "
            f"{len(assignment)} were assigned "
            f"({', '.join(sorted(assignment)) or 'none'})")

    if sorted(assignment.values()) != sorted(chosen.weights):
        problems.append(
            f"the assigned bonuses {sorted(assignment.values(), reverse=True)} "
            f"do not match {background.name} option {index}'s "
            f"{sorted(chosen.weights, reverse=True)} — each bonus is used "
            "exactly once, on a different ability")

    return problems


def _validate_chosen_items(draft: dict, field: str, label: str,
                           known_ids: set[str], problems: list[str]) -> None:
    """Shape-check one chosen-items Draft field, then catalog-check what's
    left. Appends to `problems`; never raises.

    The shape check has to come first: a malformed entry (a bare string
    instead of a dict, a non-int quantity) used to crash `validate_equipment()`
    or `build()`'s `_equipment()` with an uncaught exception — an HTTP 500
    rather than a problems entry. Same bug class as the non-int
    `ability_choice_index` this module already guards against. The builder's
    own tray only ever emits well-formed entries, but the CLI and the HTTP
    API both accept a hand-written Draft.

    `quantity` is optional and defaults to 1 when absent; when present it
    must be a positive int, so a 0 or negative quantity is rejected here
    instead of silently reaching the sheet as a negative equipment row.
    """
    raw = draft.get(field)
    if raw is None:
        return
    if not isinstance(raw, list):
        problems.append(f"{field} must be a list, got {type(raw).__name__}")
        return

    for entry in raw:
        if not isinstance(entry, dict):
            problems.append(
                f"{field} entry {entry!r} must be an object with an 'id'")
            continue
        item_id = entry.get("id")
        if not isinstance(item_id, str) or not item_id:
            problems.append(f"{field} entry {entry!r} has no usable 'id'")
            continue
        if "quantity" in entry:
            quantity = entry["quantity"]
            if (not isinstance(quantity, int) or isinstance(quantity, bool)
                    or quantity < 1):
                problems.append(
                    f"chosen item {item_id!r} has an invalid quantity "
                    f"{quantity!r} — a positive whole number, or leave it out")
                continue
        if item_id not in known_ids:
            problems.append(f"{label} {item_id!r} is not in the catalog")


def validate_equipment(draft: dict, catalog) -> list[str]:
    """Every equipment-related id on the draft — worn armor, chosen
    weapons, chosen gear — must actually exist in the catalog, and every
    chosen entry must be well formed. Checked upfront here, alongside every
    other legality check, so `build()`'s `_equipment()` can later assume
    every entry it's handed is a dict with a known id and a usable
    quantity."""
    problems: list[str] = []

    armor_id = draft.get("equipped_armor_id")
    if armor_id and not any(a["id"] == armor_id for a in catalog.armor()):
        problems.append(f"armor {armor_id!r} is not in the catalog")

    _validate_chosen_items(draft, "chosen_weapons", "weapon",
                           {w.id for w in catalog.weapons()}, problems)
    _validate_chosen_items(draft, "chosen_gear", "gear item",
                           {g.id for g in catalog.gear()}, problems)

    return problems


def validate_spells(draft: dict, catalog, char_class, final_scores: dict[str, int] | None,
                    level: int) -> list[str]:
    """Spells must be on the class's own list, castable at this level, named
    only once, and within the class's limits.

    Cantrips and levelled spells share one Draft list (`spells_known` /
    `spells_prepared`), but they are counted against different limits, as
    the rules have it: `rules.known_spells_limit` /
    `rules.spells_prepared_limit` cap the LEVELLED spells only, and
    `ClassLevelRow.cantrips_known` caps the cantrips. The split is made by
    looking each chosen spell's real level up in the catalog — which this
    function does anyway, for the spell-slot check — so the one list needs
    no extra Draft field to be counted correctly.

    (It used to be counted as one combined total against the levelled-spell
    limit alone. That rejected legal characters: a level 3 Cleric with WIS
    16 who takes the 3 cantrips the SRD grants them plus their 6 prepared
    spells was told "9 were chosen" against a limit of 6.)
    """
    problems: list[str] = []
    known = list(draft.get("spells_known") or [])
    prepared = list(draft.get("spells_prepared") or [])
    name = char_class.name

    prepared_limit = None
    if final_scores is not None:
        ability = CASTING_ABILITY.get(name)
        ability_mod = rules.ability_modifier(final_scores[ability]) if ability else 0
        prepared_limit = rules.spells_prepared_limit(name, level, ability_mod)
    known_limit = rules.known_spells_limit(name, level)

    is_prepared_caster = rules.spells_prepared_limit(name, level, 0) is not None
    is_known_caster = known_limit is not None

    if not is_prepared_caster and not is_known_caster:
        if known or prepared:
            problems.append(
                f"{name} is not a spellcaster, but the draft lists "
                f"{len(known) + len(prepared)} spell(s): "
                f"{', '.join(known + prepared)}")
        return problems

    if is_prepared_caster and known:
        problems.append(
            f"{name} prepares spells rather than knowing them — put "
            f"{', '.join(known)} in spells_prepared, not spells_known")
    if is_known_caster and prepared:
        problems.append(
            f"{name} knows spells rather than preparing them — put "
            f"{', '.join(prepared)} in spells_known, not spells_prepared")

    chosen = prepared if is_prepared_caster else known

    # Mirrors validate_skills()' duplicate check: naming one spell twice
    # burns two of a limited number of slots on a single spell and puts it
    # on the sheet twice.
    duplicates = sorted({s for s in chosen if chosen.count(s) > 1})
    if duplicates:
        problems.append(
            f"duplicate spell picks for {name}: {', '.join(duplicates)}")

    try:
        level_row = catalog.level_row(char_class.id, level)
    except (KeyError, AttributeError):
        level_row = None
    slots = dict(getattr(level_row, "spell_slots", None) or {})
    cantrips_known = getattr(level_row, "cantrips_known", None)

    # The per-spell checks come FIRST, so the counts below can be split by
    # each spell's real level instead of lumping cantrips in with levelled
    # spells. A name the catalog doesn't know is reported here and then left
    # out of both counts — its level is unknowable, and guessing it into one
    # bucket would produce a second, wrong message about the same spell.
    by_name = {s.name: s for s in catalog.spells(cls=name)}
    cantrips_chosen: list[str] = []
    levelled_chosen: list[str] = []
    for spell_name in chosen:
        spell = by_name.get(spell_name)
        if spell is None:
            problems.append(
                f"spell {spell_name!r} is not on the {name} spell list")
            continue
        if spell.level == 0:
            cantrips_chosen.append(spell_name)
            if not cantrips_known:
                problems.append(
                    f"a level {level} {name} knows no cantrips, so "
                    f"{spell_name!r} cannot be taken")
        else:
            levelled_chosen.append(spell_name)
            if not slots.get(spell.level):
                problems.append(
                    f"{spell_name!r} is a level {spell.level} spell, but a level "
                    f"{level} {name} has no level {spell.level} spell slots")

    count = len(levelled_chosen)
    if is_prepared_caster and prepared_limit is not None and count > prepared_limit:
        problems.append(
            f"a level {level} {name} can prepare {prepared_limit} spell(s), "
            f"but {count} were chosen")
    if is_known_caster and known_limit is not None and count > known_limit:
        problems.append(
            f"a level {level} {name} knows {known_limit} spell(s), "
            f"but {count} were chosen")

    # The cantrips have their own, separate cap. Only checked when the level
    # table actually carries one; a falsy cantrips_known is the "knows no
    # cantrips" case already reported per-spell above.
    if cantrips_known and len(cantrips_chosen) > cantrips_known:
        problems.append(
            f"a level {level} {name} knows {cantrips_known} cantrip(s), "
            f"but {len(cantrips_chosen)} were chosen")

    return problems


# ---------------------------------------------------------------------------
# the whole draft
# ---------------------------------------------------------------------------

def validate(draft: dict, catalog) -> tuple[list[str], list[str]]:
    """Every legality problem with `draft`, as human-readable strings, plus
    informational warnings that never block a build.

    An empty `problems` list means the draft is fully legal. Checks that
    depend on an earlier one resolving (spells need the class; the prepared
    limit needs the final ability scores) are skipped when that earlier
    check failed — everything independent is still reported, so a caller
    sees all the real problems in one pass rather than one per round trip.
    """
    score_problems = validate_ability_scores(draft)
    race, subrace, race_problems = validate_race(draft, catalog)
    background, background_problems = validate_background(draft, catalog)
    char_class, _subclass, class_problems = validate_class(draft, catalog)
    choice_problems = validate_ability_choice(draft, background)

    problems: list[str] = []
    warnings: list[str] = []
    problems += validate_name(draft)
    problems += validate_hp_method(draft)
    problems += validate_level(draft)
    problems += score_problems
    problems += race_problems
    problems += background_problems
    problems += class_problems
    problems += choice_problems
    problems += validate_equipment(draft, catalog)

    edition_warning = mixed_edition_warning(race, subrace, background)
    if edition_warning:
        warnings.append(edition_warning)

    if char_class is not None:
        problems += validate_skills(draft, char_class, background)

    level = draft.get("level")
    final_scores = None
    if not score_problems and not choice_problems and race is not None:
        final_scores = apply_ability_bonuses(
            draft.get("ability_scores") or {}, race, subrace,
            background, draft.get("ability_choice_index"),
            draft.get("ability_choice_assignment"))

    if char_class is not None and isinstance(level, int) and not isinstance(level, bool) \
            and MIN_LEVEL <= level <= MAX_LEVEL:
        problems += validate_spells(draft, catalog, char_class, final_scores, level)

    return problems, warnings
