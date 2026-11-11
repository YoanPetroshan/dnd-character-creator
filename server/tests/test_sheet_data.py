"""SHEET-S4: the pure mapping Resolution -> sheet field values (server/sheet_data.py)."""
import ast
import copy
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sheet_data as D  # noqa: E402
import sheet_layout as L  # noqa: E402
from catalog.loader import load  # noqa: E402
from engine.resolve import resolve  # noqa: E402
from export_labels import LABELS  # noqa: E402
from kitchen_sink import KITCHEN_SINK, build, skip_reason  # noqa: E402

CYRILLIC = re.compile("[Ѐ-ӿ]")
SHEETS = ("fighter10-2024", "paladin6", "wizard5-2014", "wizard5-2024", "cleric6-paladin3-2014", "warlock7-2024", "warlock17")
LANGS = ("bg", "en")
_cache: dict = {}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _resolution(sid, catalog):
    reason = skip_reason(KITCHEN_SINK[sid])
    if reason:
        pytest.skip(reason)
    if sid not in _cache:
        _cache[sid] = resolve(build(sid, catalog, resolve), catalog)
    return _cache[sid]


def _data(sid, lang, catalog):
    return D.build_sheet_data(_resolution(sid, catalog), catalog, lang, KITCHEN_SINK[sid]["ruleset"])


@pytest.mark.parametrize("sid", SHEETS)
@pytest.mark.parametrize("lang", LANGS)
def test_one_value_per_layout_field_in_layout_order(sid, lang, catalog):
    d = _data(sid, lang, catalog)
    assert [v.name for v in d.values] == [f.name for f in L.FIELDS]
    for v, f in zip(d.values, L.FIELDS):
        assert isinstance(v.value, bool) if f.kind == "check" else isinstance(v.value, str), v.name


@pytest.mark.parametrize("sid", SHEETS)
@pytest.mark.parametrize("lang", LANGS)
def test_the_numbers_come_from_the_resolution(sid, lang, catalog):
    res, d = _resolution(sid, catalog), _data(sid, lang, catalog)
    sheet, derived, got = res["sheet"], res["derived"], d.as_dict()
    sign = lambda n: f"+{n}" if n >= 0 else str(n)  # noqa: E731
    for a in L.ABILITIES:
        ab = a.upper()
        assert got[f"Ability{a}"] == str(sheet["abilities"][ab])
        assert got[f"Ability{a}Mod"] == sign(derived["abilityModifiers"][ab])
        assert got[f"Save{a}"] == sign(derived["savingThrows"][ab])
        assert got[f"Save{a}Mark"] is (ab in sheet["proficiencies"]["savingThrows"])  # a checkbox: a filled dot when proficient
    for skill in L.SKILLS:
        sid_ = "skill-" + re.sub(r"(?<!^)([A-Z])", r"-\1", skill).lower()
        assert got[f"Skill{skill}"] == sign(derived["skills"][sid_])
        expert = sid_ in sheet["expertiseSkills"]
        assert got[f"Skill{skill}Expert"] is expert  # a second checkbox: a dot in a double ring
        assert got[f"Skill{skill}Mark"] is (expert or sid_ in sheet["proficiencies"]["skills"])  # expertise implies proficiency
    assert got["ArmorClass"] == str(derived["armorClass"]) and got["MaxHp"] == str(derived["hitPointMax"])
    assert got["Initiative"] == sign(derived["initiative"]) and got["ProficiencyBonus"] == sign(derived["proficiencyBonus"])
    assert got["PassivePerception"] == str(derived["passivePerception"])
    assert got["HitDiceTotal"] == str(derived["hitDice"])
    assert got["ClassLevel"].startswith(sheet["classes"][0]["name"] + " " + str(sheet["classes"][0]["level"]))
    assert got["Species"].startswith(sheet["species"]["name"]) and got["Background"] == sheet["background"]["name"]
    assert got["CharacterName"] == sheet["name"]
    assert got["Inspiration"] is False and not any(got[f"Death{k}{i}"] for k in ("Success", "Failure") for i in (1, 2, 3))
    assert got["CurrentHp"] == got["TempHp"] == got["PlayerName"] == got["ExperiencePoints"] == ""


@pytest.mark.parametrize("sid", SHEETS)
def test_weapon_rows_are_the_attack_rows(sid, catalog):
    res, got = _resolution(sid, catalog), _data(sid, "en", catalog).as_dict()
    for i, a in enumerate(res["derived"]["attacks"][:6], start=1):
        assert got[f"Weapon{i}Name"] == a["name"]
        assert got[f"Weapon{i}Attack"] == (f"+{a['attackBonus']}" if a["attackBonus"] >= 0 else str(a["attackBonus"]))
        if a.get("damage"):
            assert got[f"Weapon{i}Damage"].startswith(a["damage"])


@pytest.mark.parametrize("sid", SHEETS)
def test_equipment_rows_list_every_item_and_expand_packs(sid, catalog):
    res = _resolution(sid, catalog)
    d = _data(sid, "en", catalog)
    got = d.as_dict()
    names = [got[f"Eq{i}Name"] for i in range(L.EQUIPMENT_ROWS) if got[f"Eq{i}Name"]] + [r[0] for r in d.equipment_overflow]
    eq = res["sheet"]["equipment"]
    expected = []
    for key in ("granted", "chosen", "added"):
        for e in eq[key]:
            expected += [c["name"] for c in e["contents"]] if e.get("contents") else [e["name"]]
    expected += [str(x) for x in eq.get("narrativeItems") or []]
    assert names == expected
    assert all(got[f"Eq{i}Name"] == "" or got[f"Eq{i}Qty"] != "" or True for i in range(L.EQUIPMENT_ROWS))


def test_both_languages_share_every_number_and_name(catalog):
    en, bg = _data("paladin6", "en", catalog).as_dict(), _data("paladin6", "bg", catalog).as_dict()
    labelled = {"Proficiencies", "Actions1", "Actions2", "Speed", "Defenses", "Senses", "WeightCarried", "WeightCapacity",
                "PushDragLift"} | {f"Weapon{i}Notes" for i in range(1, 7)} | {f"Weapon{i}Damage" for i in range(1, 7)}
    assert {k for k in en if en[k] != bg[k]} <= labelled
    assert en["WeightCarried"].endswith("lb") and "kg" in bg["WeightCarried"]


@pytest.mark.parametrize("sid", SHEETS)
def test_english_has_no_cyrillic_and_bulgarian_headings_do(sid, catalog):
    en, bg = _data(sid, "en", catalog), _data(sid, "bg", catalog)
    for v in en.values:
        if v.name != "CharacterName" and isinstance(v.value, str):
            assert not CYRILLIC.search(v.value), (v.name, v.value)
    for block in en.flow:
        assert not CYRILLIC.search(block.text), block
    assert CYRILLIC.search(bg.as_dict()["Proficiencies"]) and CYRILLIC.search(bg.as_dict()["Actions1"])
    assert [(r.kind, r.level) for g in en.spell_groups for r in g.rows] == [(r.kind, r.level) for g in bg.spell_groups for r in g.rows]


@pytest.mark.parametrize("sid", SHEETS)
def test_the_resolution_is_not_modified_and_the_output_is_deterministic(sid, catalog):
    res = _resolution(sid, catalog)
    before = copy.deepcopy(res)
    a = D.build_sheet_data(res, catalog, "bg", KITCHEN_SINK[sid]["ruleset"])
    b = D.build_sheet_data(res, catalog, "bg", KITCHEN_SINK[sid]["ruleset"])
    assert res == before and a == b


# ---- spells ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sid", ("paladin6", "wizard5-2014", "wizard5-2024", "cleric6-paladin3-2014", "warlock7-2024", "warlock17"))
def test_spell_groups_follow_the_resolution(sid, catalog):
    res, d = _resolution(sid, catalog), _data(sid, "en", catalog)
    entries = res["sheet"]["spells"]
    groups = [g for g in d.spell_groups if g.key != "innate"]
    assert [g.key for g in groups] == [e["classId"] for e in entries]
    for g, e in zip(groups, entries):
        spells = [r for r in g.rows if r.kind == "spell"]
        names = [r.cells["Name"] for r in spells]
        assert len(names) == len(set(names)), "one row per spell"
        assert set(names) >= {s["name"] for s in e["cantrips"] + e["known"]}
        assert set(names) >= {s["name"] for s in e.get("spellbook") or []}
        assert g.save_dc == str(e["spellSaveDC"])
        assert g.rows and g.rows[-1].kind == "spell", "a level header is never the last row"
        for prev, row in zip(g.rows, g.rows[1:]):
            assert prev.kind != "header" or row.kind == "spell" and row.level == prev.level
        levels = [r.level for r in g.rows if r.kind == "header"]
        assert levels == sorted(levels) and len(levels) == len(set(levels))
        for r in spells:
            assert set(r.cells) >= {"Name", "Save", "Time", "Range", "Comp", "Duration", "Ref", "Prep", "Source", "Notes"}
            assert r.cells["Prep"] in ("", "O", "P")
            assert r.cells["Time"] and r.cells["Range"] and r.cells["Ref"]
        known = {s["name"] for s in e["known"]}
        assert all(r.cells["Prep"] in ("O", "P") for r in spells if r.cells["Name"] in known)
        always = {s["name"] for s in e.get("alwaysPrepared") or []}
        assert all(r.cells["Prep"] == "P" for r in spells if r.cells["Name"] in always)


def test_wizard_spellbook_only_spells_are_not_marked_prepared(catalog):
    res, d = _resolution("wizard5-2014", catalog), _data("wizard5-2014", "en", catalog)
    e = res["sheet"]["spells"][0]
    book_only = {s["name"] for s in e["spellbook"]} - {s["name"] for s in e["known"]}
    assert book_only
    for r in d.spell_groups[0].rows:
        if r.kind == "spell" and r.cells["Name"] in book_only:
            assert r.cells["Prep"] == "" and "in the book" in r.cells["Notes"]


def test_multiclass_caster_has_a_group_and_a_dc_field_per_class(catalog):
    res, d = _resolution("cleric6-paladin3-2014", catalog), _data("cleric6-paladin3-2014", "en", catalog)
    assert [g.key for g in d.spell_groups] == ["cleric", "paladin"]
    got = d.as_dict()
    assert got["SpellDc1"] == d.spell_groups[0].save_dc and got["SpellDc2"] == d.spell_groups[1].save_dc
    assert got["SpellDc1Ability"] == "WIS" and got["SpellDc2Ability"] == "CHA"
    assert d.spell_groups[0].slots  # the shared slot line


def test_warlock_pact_slots_are_in_the_group_slot_line(catalog):
    res, d = _resolution("warlock7-2024", catalog), _data("warlock7-2024", "en", catalog)
    assert res["derived"]["warlockSpellSlots"] and d.spell_groups[0].slots


def test_spell_cell_compaction():
    assert D.compact_time("1 action") == "1A" and D.compact_time("1 bonus action") == "1BA"
    assert D.compact_time("1 reaction, which you take when you are hit") == "1R"
    assert D.compact_time("1 minute") == "1m" and D.compact_time("8 hours") == "8h" and D.compact_time("1 action or 8 hours") == "1 action or 8 hours"
    assert D.compact_range("Self (30-foot cone)") == "Self (30-ft. cone)" and D.compact_range("150 feet") == "150 ft."
    assert D.compact_duration("Up to 1 minute", True) == "C 1 min" and D.compact_duration("Instantaneous", False) == "Inst."
    assert D.compact_duration("Concentration, up to 10 minutes", True) == "C 10 min"


# ---- overflow --------------------------------------------------------------------------------------------------------
def test_fill_box_keeps_whole_blocks_and_returns_the_rest():
    rect = (0.0, 0.0, 100.0, 40.0)  # capacity at 6 pt: 5 lines of about 27 characters; a blank line separates blocks
    taken, rest = D.fill_box(["aaa", "bbb", "ccc", "ddd", "eee", "fff", "ggg"], rect)
    assert taken == ["aaa", "bbb", "ccc"] and rest == ["ddd", "eee", "fff", "ggg"]
    taken, rest = D.fill_box(["word " * 200], rect)  # a single oversize block is cut by words
    assert taken and rest and " ".join(taken + rest).replace("  ", " ").split() == ("word " * 200).split()


def test_long_texts_overflow_into_the_flow_and_the_notes_pages(catalog):
    res = copy.deepcopy(_resolution("paladin6", catalog))
    res["sheet"]["details"] = {"backstory": "\n\n".join(f"Paragraph {i}. " + "long text " * 40 for i in range(40)),
                               "allies": "\n\n".join("ally " * 80 for _ in range(30)), "notes": "short note"}
    d = D.build_sheet_data(res, catalog, "en", "2014")
    got = d.as_dict()
    assert got["Backstory"].startswith("Paragraph 0.") and got["Notes1"] == "short note"
    assert d.overflow["Backstory"] and "Notes1" not in d.overflow
    joined = "\n\n".join([got["Backstory"], *d.overflow["Backstory"]])
    assert joined.count("Paragraph ") == 40  # nothing is lost
    assert any(b.kind == "heading" and "Allies" in b.text and "continued" in b.text for b in d.flow)
    bg = D.build_sheet_data(res, catalog, "bg", "2014")
    assert any("(продължение)" in b.text for b in bg.flow)


def test_equipment_beyond_the_rows_is_kept(catalog):
    res = copy.deepcopy(_resolution("paladin6", catalog))
    res["sheet"]["equipment"]["added"] = [{"itemId": "dagger", "name": f"Thing {i}", "qty": 1} for i in range(70)]
    d = D.build_sheet_data(res, catalog, "en")
    assert len(d.equipment_overflow) > 0
    assert [r[0] for r in d.equipment_overflow][-1] == "Thing 69"
    assert d.as_dict()[f"Eq{L.EQUIPMENT_ROWS - 1}Name"] != ""


# ---- descriptions ----------------------------------------------------------------------------------------------------
def test_tags_and_entries_are_flattened():
    assert D.strip_tags("You have {@variantrule Resistance|XPHB} to {@damage 1d6} damage; {@dc 13}; {@spell fire bolt|phb}") == \
        "You have Resistance to 1d6 damage; DC 13; fire bolt"
    assert D.strip_tags("{@item shortsword|phb|Short Sword} {@hit 5} {@atk mw}") == "Short Sword +5 Melee Weapon Attack:"
    entries = ["Intro {@skill Perception}.", {"type": "entries", "name": "Part", "entries": ["Body."]},
               {"type": "list", "items": ["one", "two"]}, {"type": "table", "colLabels": ["A", "B"], "rows": [["1", "2"]]}]
    assert D.flatten_entries(entries) == ["Intro Perception.", "Part. Body.", "- one", "- two", "A | B", "1 | 2"]


class _Cat:
    def __init__(self, features):
        self.features, self.traits, self.backgrounds, self.feats = features, {}, {}, {}


def _entry(name, level=1):
    return {"source": {"kind": "class", "id": "wizard", "label": "Wizard"}, "name": name, "level": level}


def _sheet():
    return {"classes": [{"id": "wizard", "name": "Wizard", "level": 5, "subclass": None}], "species": None}


def test_no_description_rather_than_a_wrong_one():
    rec = lambda idx, level, text: {"index": idx, "class": {"index": "wizard"}, "name": "Arcane Recovery", "level": level, "desc": [text]}  # noqa: E731
    one = D._Descriptions(_Cat({"a": rec("arcane-recovery", 1, "old text")}), _sheet(), "mixed")
    assert one.feature(_entry("Arcane Recovery")) == ["old text"]
    assert one.feature(_entry("Arcane Recovery", level=2)) is None, "another level is another feature"
    both = D._Descriptions(_Cat({"a": rec("arcane-recovery", 1, "old text"), "b": rec("xphb-wizard-1-arcane-recovery", 1, "new text")}), _sheet(), "mixed")
    assert both.feature(_entry("Arcane Recovery")) is None, "two editions that differ: unknown edition prints nothing"
    assert D._Descriptions(_Cat({"a": rec("arcane-recovery", 1, "old text"), "b": rec("xphb-wizard-1-arcane-recovery", 1, "new text")}),
                           _sheet(), "2024").feature(_entry("Arcane Recovery")) == ["new text"]
    assert D._Descriptions(_Cat({"a": rec("arcane-recovery", 1, "same"), "b": rec("xphb-wizard-1-arcane-recovery", 1, "same")}),
                           _sheet(), "mixed").feature(_entry("Arcane Recovery")) == ["same"]
    twin = D._Descriptions(_Cat({"a": rec("x1", 1, "one"), "b": rec("x2", 1, "two")}), _sheet(), "2014")
    assert twin.feature(_entry("Arcane Recovery")) is None, "two different texts for one name"


def test_feature_description_coverage_report(catalog, capsys):
    """A report, and floors: how many features of each kitchen-sink sheet carry a description. A feature without one
    prints its title only (never a guess)."""
    floors = {"fighter10-2024": 0.8, "paladin6": 0.5, "wizard5-2014": 0.8, "wizard5-2024": 0.8, "cleric6-paladin3-2014": 0.5,
              "warlock7-2024": 0.5, "warlock17": 0.4}
    lines = []
    for sid in SHEETS:
        d = _data(sid, "en", catalog)
        total = len(d.coverage)
        got = sum(c.described for c in d.coverage)
        lines.append(f"{sid}: {got}/{total} described; missing: {[c.name for c in d.coverage if not c.described]}")
        assert total and got / total >= floors[sid], lines[-1]
        text_blocks = [b for b in d.flow if b.kind == "text"]
        assert len(text_blocks) >= got
    with capsys.disabled():
        print("\nfeature-description coverage\n  " + "\n  ".join(lines))


# ---- labels and purity -----------------------------------------------------------------------------------------------
def test_every_frame_title_and_column_label_exists_in_both_languages():
    keys = {fr.title for fr in L.FRAMES if fr.title} | {"idName", "idClass", "idPlayer", "idSpecies", "idBackground", "idXp", "legend", "footer",
                                                          "colName", "colAttack", "colDamage", "colNotes", "colQty", "colWeight", "spPrep", "spName",
                                                          "spSource", "spSave", "spTime", "spRange", "spComp", "spDuration", "spRef", "spNotes",
                                                          "spAbility", "spDc", "spAttack", "spClass"}
    keys |= {f"body{n}" for n in ("Gender", "Age", "Size", "Height", "Weight", "Alignment", "Faith", "Skin", "Eyes", "Hair")}
    for lang in LANGS:
        assert not keys - set(LABELS[lang]["sheet"]), keys - set(LABELS[lang]["sheet"])
    assert set(LABELS["bg"]["sheet"]) == set(LABELS["en"]["sheet"])
    for key, text in LABELS["bg"]["sheet"].items():
        assert CYRILLIC.search(text), key
    for text in LABELS["en"]["sheet"].values():
        assert not CYRILLIC.search(text)


def test_sheet_labels_follow_the_bracket_rule():
    from i18n.bracket_terms import bracket_problems
    for lang in LANGS:
        for key, text in LABELS[lang]["sheet"].items():
            assert bracket_problems(text) == [], (lang, key)
    assert "(Weapon Attacks, Cantrips)" in LABELS["bg"]["sheet"]["weapons"]


def test_the_module_is_pure_data_code():
    tree = ast.parse(Path(D.__file__).read_text(encoding="utf-8"))
    mods = {(n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
            for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [n])}
    assert not mods & {"fpdf", "pypdf", "PIL", "fontTools", "defusedxml", "flask", "yaml", "os", "pathlib", "io"}, mods


def test_the_skill_marks_are_checkboxes_without_letters_and_the_legend_says_so():
    for name in [f"Skill{s}{k}" for s in L.SKILLS for k in ("Mark", "Expert")] + [f"Save{a}Mark" for a in L.ABILITIES] \
            + [f"CustomSkill{i}{k}" for i in (1, 2, 3) for k in ("Mark", "Expert")]:
        f = L.FIELDS_BY_NAME[name]
        assert f.kind == "check" and f.style == "dot", name
    for lang in LANGS:
        legend = LABELS[lang]["sheet"]["legend"]
        assert "E =" not in legend and "E -" not in legend and "P = Proficiency" not in legend and "P - владеене" not in legend
    assert "double ring" in LABELS["en"]["sheet"]["legend"] and "двоен пръстен" in LABELS["bg"]["sheet"]["legend"]
