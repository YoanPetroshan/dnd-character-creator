"""Geometry of the fillable character sheet (plan docs/superpowers/plans/2026-11-10-fillable-character-sheet.md).

Everything here is DATA in the reference's US Letter points (612 x 792, origin bottom-left, y up), measured with
scripts/dev_extract_sheet_layout.py from the owner's reference sheets. Only OUR numbers and OUR names are kept (clean
ASCII, no dots, unique); nothing of the reference file is copied. The renderer places the A4 page with one uniform
transform (``a4_rect`` / ``a4_size``: scale ``s = 595.28 / 612``, centred vertically); field rectangles, font sizes and
frames all go through it.

Pure Python, no imports besides the standard library (the module is imported by the offline engine too).
"""
from __future__ import annotations

from dataclasses import dataclass

LETTER_W, LETTER_H = 612.0, 792.0
A4_W, A4_H = 595.28, 841.89
SCALE = A4_W / LETTER_W
OFFSET_Y = (A4_H - LETTER_H * SCALE) / 2.0

Rect = tuple[float, float, float, float]


def a4_rect(rect: Rect) -> Rect:
    """Letter rectangle (x0, y0, x1, y1, origin bottom-left) -> A4 rectangle in PDF user space."""
    x0, y0, x1, y1 = rect
    return (x0 * SCALE, y0 * SCALE + OFFSET_Y, x1 * SCALE, y1 * SCALE + OFFSET_Y)


def a4_point(x: float, y: float) -> tuple[float, float]:
    return (x * SCALE, y * SCALE + OFFSET_Y)


def a4_size(points: float) -> float:
    """A length (font size, line width, padding) in Letter points -> A4 points."""
    return points * SCALE


@dataclass(frozen=True)
class Widget:
    page: int  # 1-based sheet page of the template (1-4 fixed pages, 5 = the spell page template)
    rect: Rect


@dataclass(frozen=True)
class Field:
    name: str  # ASCII, no dots, unique in the document
    kind: str  # "text" | "multi" | "check"
    widgets: tuple[Widget, ...]  # more than one: the same field shown on several pages (one shared value)
    align: str = "left"  # "left" | "center"
    size: float = 8.0  # default font size in Letter points (the renderer may shrink long text)


@dataclass(frozen=True)
class Frame:
    name: str
    page: int
    rect: Rect
    title: str  # label key under LABELS[lang]["sheet"] ("" = no title)
    members: tuple[str, ...]  # field names drawn inside this frame on this page


def _r(x0: float, y0: float, x1: float, y1: float) -> Rect:
    return (x0, y0, x1, y1)


_FIELDS: list[Field] = []


def _add(name: str, kind: str, rects: dict[int, Rect] | Rect, page: int = 1, align: str = "left", size: float = 8.0) -> None:
    if isinstance(rects, tuple):
        rects = {page: rects}
    _FIELDS.append(Field(name, kind, tuple(Widget(p, r) for p, r in sorted(rects.items())), align, size))


# ---- identity header: one field with a widget per page (page 4 only has the character name) ----
_add("CharacterName", "text", {1: _r(47.5, 710.3, 220.6, 731.2), 2: _r(47.3, 711.3, 220.5, 732.2),
                                3: _r(47.3, 711.3, 220.5, 732.2), 4: _r(49.3, 710.8, 222.5, 731.7)}, size=12.0)
for _name, _x0, _x1, _y in (("ClassLevel", 270.7, 492.0, 728.3), ("PlayerName", 495.0, 568.2, 728.3), ("Species", 270.7, 400.7, 702.2),
                            ("Background", 403.7, 513.7, 702.2), ("ExperiencePoints", 516.7, 568.2, 702.2)):
    _add(_name, "text", {1: _r(_x0, _y, _x1, _y + 14.1), 2: _r(_x0, _y + 1.0, _x1, _y + 15.1), 3: _r(_x0, _y + 1.0, _x1, _y + 15.1)}, size=8.0)

# ---- page 1: abilities, saves, skills ----
ABILITIES = ("Str", "Dex", "Con", "Int", "Wis", "Cha")
_SCORE_Y = (609.3, 532.3, 456.0, 379.0, 302.7, 226.4)
_MOD_Y = (589.5, 512.5, 436.2, 359.2, 282.9, 206.7)
for _i, _a in enumerate(ABILITIES):
    _add(f"Ability{_a}", "text", _r(36.8, _SCORE_Y[_i], 77.8, _SCORE_Y[_i] + 25.5), align="center", size=18.0)
    _add(f"Ability{_a}Mod", "text", _r(46.4, _MOD_Y[_i], 67.7, _MOD_Y[_i] + 12.8), align="center", size=10.0)
    _y = 650.4 - 13.5 * _i
    _add(f"Save{_a}Mark", "text", _r(99.6, _y, 109.0, _y + 8.7), align="center", size=8.0)
    _add(f"Save{_a}", "text", _r(111.0, _y, 128.5, _y + 8.6), align="center", size=8.0)

SKILLS = ("Acrobatics", "AnimalHandling", "Arcana", "Athletics", "Deception", "History", "Insight", "Intimidation",
          "Investigation", "Medicine", "Nature", "Perception", "Performance", "Persuasion", "Religion", "SleightOfHand",
          "Stealth", "Survival")
for _i, _s in enumerate(SKILLS):
    _y = 480.8 - 13.5 * _i
    _add(f"Skill{_s}Mark", "text", _r(99.7, _y - 0.5, 109.0, _y + 8.2), align="center")
    _add(f"Skill{_s}", "text", _r(110.5, _y, 128.0, _y + 8.6), align="center")
    _add(f"Skill{_s}Ability", "text", _r(178.0, _y, 200.4, _y + 8.6), align="left", size=7.0)
for _i, _y in enumerate((237.2, 222.8, 209.2), start=1):
    _add(f"CustomSkill{_i}Mark", "text", _r(99.7, _y - 0.7, 109.0, _y + 7.9), align="center")
    _add(f"CustomSkill{_i}Bonus", "text", _r(110.5, _y, 128.0, _y + 8.7), align="center")
    _add(f"CustomSkill{_i}Name", "text", _r(132.0, _y - 0.5, 200.4, _y + 8.7), size=7.0)

_add("SaveNotes", "multi", _r(98.9, 520.8, 200.6, 562.2), size=7.0)
for _name, _y in (("PassivePerception", 149.0), ("PassiveInsight", 119.0), ("PassiveInvestigation", 88.2)):
    _add(_name, "text", _r(38.8, _y, 60.0, _y + 16.6), align="center", size=10.0)
_add("Senses", "multi", _r(37.8, 38.0, 197.6, 79.3), size=7.0)

# ---- page 1: combat block ----
_add("Initiative", "text", _r(238.0, 614.3, 272.5, 645.8), align="center", size=16.0)
_add("ArmorClass", "text", _r(334.3, 609.4, 376.4, 643.4), align="center", size=18.0)
_add("Defenses", "multi", _r(231.6, 548.5, 381.2, 582.1), size=7.0)
_add("Inspiration", "check", _r(229.7, 501.7, 247.7, 519.7))
_add("ProficiencyBonus", "text", _r(227.8, 465.5, 249.1, 482.0), align="center", size=11.0)
_add("SpellDc1", "text", _r(227.7, 424.9, 249.0, 441.5), align="center", size=11.0)
_add("SpellDc1Ability", "text", _r(253.0, 428.4, 281.0, 438.6), align="center", size=7.0)
_add("SpellDc2Ability", "text", _r(331.0, 428.4, 359.0, 438.6), align="center", size=7.0)
_add("SpellDc2", "text", _r(363.0, 424.9, 384.2, 441.5), align="center", size=11.0)
_add("Speed", "multi", _r(236.2, 371.2, 377.4, 401.7), size=8.0)
_add("MaxHp", "text", _r(426.8, 612.5, 463.2, 640.8), align="center", size=16.0)
_add("CurrentHp", "text", _r(473.3, 611.2, 521.2, 642.6), align="center", size=16.0)
_add("TempHp", "text", _r(531.9, 613.2, 568.3, 641.4), align="center", size=16.0)
_add("HitDiceTotal", "text", _r(438.4, 572.2, 486.2, 586.3), align="center", size=8.0)
_add("HitDiceSpent", "text", _r(422.7, 548.8, 486.1, 569.7), align="center", size=8.0)
for _i, _x in enumerate((537.4, 550.2, 563.1), start=1):
    _add(f"DeathSuccess{_i}", "check", _r(_x, 569.3, _x + 9.3, 581.6))
    _add(f"DeathFailure{_i}", "check", _r(_x, 554.2, _x + 9.3, 566.5))
_add("Proficiencies", "multi", _r(414.0, 359.9, 579.6, 512.9), size=7.0)
_add("Actions1", "multi", _r(226.0, 198.4, 399.6, 329.2), size=7.0)
_add("Actions2", "multi", _r(404.8, 198.5, 578.4, 329.4), size=7.0)
for _i in range(1, 7):
    _y = 146.7 - 20.3 * (_i - 1)
    _add(f"Weapon{_i}Name", "text", _r(225.0, _y, 335.0, _y + 14.0), size=8.0)
    _add(f"Weapon{_i}Attack", "text", _r(342.3, _y, 372.2, _y + 14.0), align="center", size=8.0)
    _add(f"Weapon{_i}Damage", "text", _r(378.3, _y, 439.2, _y + 14.0), size=7.0)
    _add(f"Weapon{_i}Notes", "text", _r(443.8, _y, 578.0, _y + 14.0), size=6.0)

# ---- pages 2 and 3: features flow, coins, carrying, equipment ----
_FEATURE_COLS = ((36.1, 210.6), (218.6, 393.1), (400.0, 574.5))
for _i, (_x0, _x1) in enumerate(_FEATURE_COLS, start=1):
    _add(f"Features{_i}", "multi", _r(_x0, 315.5, _x1, 656.0), page=2, size=7.0)
    _add(f"Features{_i + 3}", "multi", _r(_x0, 315.5, _x1, 656.0), page=3, size=7.0)
for _i, (_n, _y) in enumerate((("Cp", 250.1), ("Sp", 221.2), ("Ep", 192.4), ("Gp", 163.8), ("Pp", 135.0))):
    _add(f"Coins{_n}", "text", _r(38.0, _y, 91.4, _y + 17.6), page=2, align="center", size=10.0)
for _n, _y in (("WeightCarried", 101.3), ("WeightCapacity", 73.1), ("PushDragLift", 43.9)):
    _add(_n, "text", _r(37.3, _y, 103.0, _y + 14.0), page=2, align="center", size=8.0)

_EQ_PITCH = 14.89
_EQ_COLUMNS = (  # (name x0, x1), (qty x0, x1), (weight x0, x1) per equipment column
    (2, (112.2, 267.5), (271.8, 301.9), (306.0, 335.8)),
    (2, (349.5, 505.7), (509.5, 539.2), (543.7, 573.5)),
    (3, (36.5, 231.5), (235.8, 265.9), (270.0, 299.8)),
    (3, (312.5, 507.6), (511.5, 541.2), (545.7, 575.5)),
)
_EQ_ROWS = (15, 11, 15, 15)  # rows 0-14, 15-25 (page 2), 26-40, 41-55 (page 3)
EQUIPMENT_ROWS = sum(_EQ_ROWS)
_n = 0
for (_page, _nm, _qt, _wt), _count in zip(_EQ_COLUMNS, _EQ_ROWS):
    for _k in range(_count):
        _y = 252.9 - _EQ_PITCH * _k
        _add(f"Eq{_n}Name", "text", _r(_nm[0], _y, _nm[1], _y + 14.1), page=_page, size=8.0)
        _add(f"Eq{_n}Qty", "text", _r(_qt[0], _y, _qt[1], _y + 14.1), page=_page, align="center", size=8.0)
        _add(f"Eq{_n}Weight", "text", _r(_wt[0], _y, _wt[1], _y + 14.1), page=_page, align="center", size=8.0)
        _n += 1
for _i in range(1, 4):  # attuned items: blank, filled by hand
    _y = 88.3 - 14.9 * (_i - 1) - 14.1
    _add(f"Attuned{_i}Name", "text", _r(349.5, _y, 505.7, _y + 14.1), page=2, size=8.0)
    _add(f"Attuned{_i}Qty", "text", _r(509.5, _y, 539.2, _y + 14.1), page=2, align="center", size=8.0)
    _add(f"Attuned{_i}Weight", "text", _r(543.7, _y, 573.5, _y + 14.1), page=2, align="center", size=8.0)

# ---- page 4: appearance and story ----
for _i, _n in enumerate(("Gender", "Age", "Size", "Height", "Weight")):
    _x0 = (265.8, 338.5, 398.6, 458.4, 520.3)[_i]
    _x1 = (335.8, 395.9, 455.6, 517.6, 573.0)[_i]
    _add(f"Body{_n}", "text", _r(_x0, 729.4, _x1, 747.6), page=4, size=8.0)
for _i, _n in enumerate(("Alignment", "Faith", "Skin", "Eyes", "Hair")):
    _x0 = (265.8, 337.1, 398.6, 458.4, 520.3)[_i]
    _x1 = (334.3, 395.9, 455.6, 517.6, 573.0)[_i]
    _add(f"Body{_n}", "text", _r(_x0, 703.2, _x1, 721.4), page=4, size=8.0)
for _n, _rect in (("Allies", _r(228.2, 448.3, 389.7, 664.4)), ("Personality", _r(418.6, 613.0, 571.4, 661.6)),
                  ("Ideals", _r(418.6, 557.9, 571.4, 592.5)), ("Bonds", _r(418.6, 502.5, 571.4, 537.1)),
                  ("Appearance", _r(36.5, 448.3, 197.9, 517.1)), ("Flaws", _r(418.6, 447.8, 571.4, 482.3)),
                  ("Backstory", _r(37.1, 42.5, 198.5, 406.5)), ("Notes1", _r(228.0, 42.3, 396.6, 406.3)),
                  ("Notes2", _r(404.6, 41.9, 573.3, 405.8))):
    _add(_n, "multi", _rect, page=4, size=7.0)
PORTRAIT_RECT: Rect = _r(38.6, 521.7, 196.4, 663.7)  # a drawn frame only (no field: the player pastes a picture)

# ---- page 5: spell page template ----
SPELL_PAGE = 5
SPELL_SLOTS = 50  # one slot = one line of the grid: a level header or a spell
SPELL_SLOT_TOP = 640.1
SPELL_SLOT_PITCH = 11.75
SPELL_SLOT_HEIGHT = 10.8
SPELL_COLUMNS = (  # (key, x0, x1, align): Prep, Name, Source, Save/Atk, Time, Range, Comp, Duration, Ref, Notes
    ("Prep", 29.0, 39.9, "center"), ("Name", 41.9, 148.1, "left"), ("Source", 149.0, 230.9, "left"),
    ("Save", 231.7, 256.9, "center"), ("Time", 257.7, 276.6, "center"), ("Range", 277.5, 319.4, "left"),
    ("Comp", 320.1, 341.8, "center"), ("Duration", 342.7, 387.9, "left"), ("Ref", 388.8, 422.1, "left"),
    ("Notes", 422.6, 578.8, "left"),
)
SPELL_HEADER_FIELDS = (("Ability", 283.8, 711.4, 348.6, 735.8), ("SaveDc", 384.5, 711.4, 449.3, 735.8),
                       ("Attack", 468.0, 711.4, 532.8, 735.8), ("Class", 47.5, 705.9, 256.0, 726.8))


def spell_slot_y(slot: int) -> tuple[float, float]:
    """(y0, y1) of a spell-grid slot, slot 0 being the first line under the column titles."""
    y1 = SPELL_SLOT_TOP - SPELL_SLOT_PITCH * slot
    return (y1 - SPELL_SLOT_HEIGHT, y1)


def spell_fields(n: int, page: int = SPELL_PAGE) -> tuple[Field, ...]:
    """The fields of spell page number ``n`` (1, 2, ...): names are ``Spell<n>_...``, so every page has its own."""
    out = [Field(f"Spell{n}_{key}", "text", (Widget(page, _r(x0, y0, x1, y1)),), "center", 9.0 if key != "Class" else 8.0)
           for key, x0, y0, x1, y1 in SPELL_HEADER_FIELDS]
    for slot in range(SPELL_SLOTS):
        y0, y1 = spell_slot_y(slot)
        for key, x0, x1, align in SPELL_COLUMNS:
            out.append(Field(f"Spell{n}_{slot:02d}_{key}", "text", (Widget(page, _r(x0, y0, x1, y1)),), align, 6.5))
    return tuple(out)


FIELDS: tuple[Field, ...] = tuple(_FIELDS)
FIELDS_BY_NAME: dict[str, Field] = {f.name: f for f in FIELDS}
PAGES = (1, 2, 3, 4, SPELL_PAGE)


def fixed_page_fields(page: int) -> tuple[Field, ...]:
    return tuple(f for f in FIELDS if any(w.page == page for w in f.widgets))


# ---- rows: groups of fields that sit on one line; rows of a group must not overlap ----
def _rows() -> dict[str, tuple[tuple[str, ...], ...]]:
    rows: dict[str, tuple[tuple[str, ...], ...]] = {
        "saves": tuple((f"Save{a}Mark", f"Save{a}") for a in ABILITIES),
        "skills": tuple((f"Skill{s}Mark", f"Skill{s}", f"Skill{s}Ability") for s in SKILLS),
        "custom_skills": tuple((f"CustomSkill{i}Mark", f"CustomSkill{i}Bonus", f"CustomSkill{i}Name") for i in (1, 2, 3)),
        "weapons": tuple((f"Weapon{i}Name", f"Weapon{i}Attack", f"Weapon{i}Damage", f"Weapon{i}Notes") for i in range(1, 7)),
        "attuned": tuple((f"Attuned{i}Name", f"Attuned{i}Qty", f"Attuned{i}Weight") for i in (1, 2, 3)),
    }
    start = 0
    for label, count in zip(("equipment_p2_left", "equipment_p2_right", "equipment_p3_left", "equipment_p3_right"), _EQ_ROWS):
        rows[label] = tuple((f"Eq{i}Name", f"Eq{i}Qty", f"Eq{i}Weight") for i in range(start, start + count))
        start += count
    return rows


ROW_GROUPS = _rows()
_ROWNAMES = {key: tuple(name for row in rows for name in row) for key, rows in ROW_GROUPS.items()}
_IDENT = ("CharacterName", "ClassLevel", "PlayerName", "Species", "Background", "ExperiencePoints")

# ---- frames: the boxes the renderer draws around groups of fields (Letter points; title = label key) ----
FRAMES: tuple[Frame, ...] = (
    Frame("identity", 1, (43.5, 692.2, 572.2, 746.4), "", _IDENT),
    Frame("identity", 2, (43.3, 693.2, 572.2, 747.4), "", _IDENT),
    Frame("identity", 3, (43.3, 693.2, 572.2, 747.4), "", _IDENT),
    Frame("identity", 4, (45.3, 700.8, 226.5, 735.7), "", ("CharacterName",)),
    Frame("ability_str", 1, (26.0, 585.5, 89.0, 652.8), "abilityStr", ("AbilityStr", "AbilityStrMod")),
    Frame("ability_dex", 1, (26.0, 508.5, 89.0, 575.8), "abilityDex", ("AbilityDex", "AbilityDexMod")),
    Frame("ability_con", 1, (26.0, 432.2, 89.0, 499.5), "abilityCon", ("AbilityCon", "AbilityConMod")),
    Frame("ability_int", 1, (26.0, 355.2, 89.0, 422.5), "abilityInt", ("AbilityInt", "AbilityIntMod")),
    Frame("ability_wis", 1, (26.0, 278.9, 89.0, 346.2), "abilityWis", ("AbilityWis", "AbilityWisMod")),
    Frame("ability_cha", 1, (26.0, 202.7, 89.0, 269.9), "abilityCha", ("AbilityCha", "AbilityChaMod")),
    Frame("saves", 1, (94.9, 514.8, 204.6, 678.1), "saves", _ROWNAMES["saves"] + ("SaveNotes",)),
    Frame("skills", 1, (95.7, 198.5, 204.4, 501.4), "skills", _ROWNAMES["skills"] + _ROWNAMES["custom_skills"]),
    Frame("senses", 1, (33.8, 28.0, 201.6, 171.6), "senses", ("PassivePerception", "PassiveInsight", "PassiveInvestigation", "Senses")),
    Frame("initiative", 1, (228.0, 604.3, 282.5, 649.8), "initiative", ("Initiative",)),
    Frame("armor_class", 1, (324.0, 588.0, 386.0, 653.0), "armorClass", ("ArmorClass",)),
    Frame("defenses", 1, (227.6, 538.5, 385.2, 586.1), "defenses", ("Defenses",)),
    Frame("inspiration", 1, (223.7, 497.7, 347.7, 523.7), "inspiration", ("Inspiration",)),
    Frame("proficiency_bonus", 1, (221.8, 461.5, 349.1, 486.0), "proficiencyBonus", ("ProficiencyBonus",)),
    Frame("spell_dc", 1, (221.7, 408.0, 390.2, 445.5), "spellSaveDc", ("SpellDc1", "SpellDc1Ability", "SpellDc2Ability", "SpellDc2")),
    Frame("speed", 1, (232.2, 361.2, 381.4, 405.7), "speed", ("Speed",)),
    Frame("hit_points", 1, (420.8, 598.0, 574.3, 656.6), "hitPoints", ("MaxHp", "CurrentHp", "TempHp")),
    Frame("hit_dice", 1, (413.0, 518.0, 494.5, 596.0), "hitDice", ("HitDiceTotal", "HitDiceSpent")),
    Frame("death_saves", 1, (497.4, 531.0, 576.4, 596.0), "deathSaves", tuple(f"Death{k}{i}" for k in ("Success", "Failure") for i in (1, 2, 3))),
    Frame("proficiencies", 1, (410.0, 349.9, 583.6, 516.9), "proficiencies", ("Proficiencies",)),
    Frame("actions", 1, (222.0, 188.4, 582.4, 333.4), "actions", ("Actions1", "Actions2")),
    Frame("weapons", 1, (221.0, 35.2, 582.0, 174.7), "weapons", _ROWNAMES["weapons"]),
    Frame("features_1", 2, (34.1, 313.5, 212.6, 658.0), "", ("Features1",)),
    Frame("features_4", 3, (34.1, 313.5, 212.6, 658.0), "", ("Features4",)),
    Frame("features_2", 2, (216.6, 313.5, 395.1, 658.0), "", ("Features2",)),
    Frame("features_5", 3, (216.6, 313.5, 395.1, 658.0), "", ("Features5",)),
    Frame("features_3", 2, (398.0, 313.5, 576.5, 658.0), "", ("Features3",)),
    Frame("features_6", 3, (398.0, 313.5, 576.5, 658.0), "", ("Features6",)),
    Frame("coins", 2, (34.0, 132.0, 106.5, 286.0), "coins", tuple(f"Coins{n}" for n in ("Cp", "Sp", "Ep", "Gp", "Pp"))),
    Frame("carrying", 2, (33.3, 17.0, 106.5, 130.0), "carrying", ("WeightCarried", "WeightCapacity", "PushDragLift")),
    Frame("equipment_left", 2, (108.2, 24.0, 339.8, 281.0), "equipment", _ROWNAMES["equipment_p2_left"]),
    Frame("equipment_right", 2, (345.5, 102.0, 577.5, 281.0), "equipment", _ROWNAMES["equipment_p2_right"]),
    Frame("attuned", 2, (345.5, 24.0, 577.5, 98.3), "attuned", _ROWNAMES["attuned"]),
    Frame("equipment_left", 3, (32.5, 24.0, 303.8, 281.0), "equipment", _ROWNAMES["equipment_p3_left"]),
    Frame("equipment_right", 3, (308.5, 24.0, 579.5, 281.0), "equipment", _ROWNAMES["equipment_p3_right"]),
    Frame("body", 4, (261.8, 692.0, 577.0, 751.6), "", tuple(f"Body{n}" for n in ("Gender", "Age", "Size", "Height", "Weight", "Alignment", "Faith", "Skin", "Eyes", "Hair"))),
    Frame("allies", 4, (224.2, 438.3, 393.7, 668.4), "allies", ("Allies",)),
    Frame("personality", 4, (414.6, 603.0, 575.4, 665.6), "personality", ("Personality",)),
    Frame("ideals", 4, (414.6, 547.9, 575.4, 596.5), "ideals", ("Ideals",)),
    Frame("bonds", 4, (414.6, 492.5, 575.4, 541.1), "bonds", ("Bonds",)),
    Frame("appearance", 4, (32.5, 438.3, 201.9, 521.1), "appearance", ("Appearance",)),
    Frame("flaws", 4, (414.6, 437.8, 575.4, 486.3), "flaws", ("Flaws",)),
    Frame("backstory", 4, (33.1, 32.5, 202.5, 410.5), "backstory", ("Backstory",)),
    Frame("notes1", 4, (224.0, 32.3, 398.6, 410.3), "notes", ("Notes1",)),
    Frame("notes2", 4, (402.6, 31.9, 577.3, 409.8), "notes", ("Notes2",)),
    Frame("spell_header", 5, (43.0, 689.5, 560.0, 742.0), "", ()),
    Frame("spell_grid", 5, (25.0, 49.0, 582.0, 652.0), "", ()),
)
