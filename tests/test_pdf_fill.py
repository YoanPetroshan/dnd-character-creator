from pathlib import Path

from pypdf import PdfReader

import pdf_fill

SHEET = {
    "name": "Torvin Bracewell",
    "player": "Yoan",
    "race": "Human",
    "background": "Soldier",
    "alignment": "Lawful Good",
    "classes": [{"cls": "Fighter", "subclass": "", "level": 1}],
    "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                       "INT": 10, "WIS": 12, "CHA": 8},
    "combat": {"hp_current": 12, "hp_max": 12, "hp_temp": 0, "speed": 30,
              "death_saves": {"successes": 0, "failures": 0},
              "hit_dice": [{"cls": "Fighter", "die": 10, "used": 0}]},
    "proficiencies": {"saving_throws": ["STR", "CON"],
                      "skills": ["Athletics", "Intimidation"],
                      "armor": ["Light Armor"], "weapons": ["Simple Weapons"],
                      "tools": [], "languages": ["Common"]},
    "personality": {"traits": "Brave", "ideals": "Honor",
                    "bonds": "My squad", "flaws": "Reckless"},
    "features_traits": [{"name": "Second Wind", "description": "", "source": "Class"}],
    "backstory": "A soldier from the border wars.",
    "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 15, "pp": 0},
    "equipment": [{"name": "Chain Shirt", "equipped": True, "quantity": 1},
                  {"name": "Longsword", "equipped": False, "quantity": 1}],
    "spellcasting": [], "spells": [], "spell_slots": {},
}
DERIVED = {
    "ac": 15, "initiative": 2, "proficiency_bonus": 2, "passive_perception": 11,
    "ability_mods": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
    "skills": {"Acrobatics": 2, "Animal Handling": 1, "Arcana": 0, "Athletics": 5,
              "Deception": -1, "History": 0, "Insight": 1, "Intimidation": 1,
              "Investigation": 0, "Medicine": 1, "Nature": 0, "Perception": 1,
              "Performance": -1, "Persuasion": -1, "Religion": 0,
              "Sleight of Hand": 2, "Stealth": 2, "Survival": 1},
    "saves": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
    "spellcasting": None,
}


def _fill_and_read_fields():
    data = pdf_fill.fill(SHEET, DERIVED)
    import io
    reader = PdfReader(io.BytesIO(data))
    fields = reader.get_fields() or {}
    return {k: (v.get("/V") if isinstance(v, dict) else None) for k, v in fields.items()}


def test_fill_returns_pdf_bytes():
    data = pdf_fill.fill(SHEET, DERIVED)
    assert data[:4] == b"%PDF"


def test_fill_identity_fields():
    values = _fill_and_read_fields()
    assert values["CharacterName"] == "Torvin Bracewell"
    assert values["PlayerName"] == "Yoan"
    assert values["Race "] == "Human"
    assert values["Background"] == "Soldier"
    assert values["Alignment"] == "Lawful Good"
    assert values["ClassLevel"] == "Fighter 1"


def test_fill_ability_scores_and_mods():
    values = _fill_and_read_fields()
    assert values["STR"] == "16"
    assert values["STRmod"] == "+3"
    assert values["DEXmod "] == "+2"
    # the real quirk in this PDF's own field naming — not a typo in this code
    assert values["CHamod"] == "-1"


def test_fill_saves_and_skills():
    values = _fill_and_read_fields()
    assert values["ST Strength"] == "+5"
    assert values["Athletics"] == "+5"
    assert values["Animal"] == "+1"


def test_fill_combat_stats():
    values = _fill_and_read_fields()
    assert values["AC"] == "15"
    assert values["Initiative"] == "+2"
    assert values["Speed"] == "30"
    assert values["HPMax"] == "12"
    assert values["HPCurrent"] == "12"
    assert values["Passive"] == "11"
    assert values["ProfBonus"] == "+2"


def test_fill_equipment_and_backstory_text_blobs():
    values = _fill_and_read_fields()
    assert "Chain Shirt" in values["Equipment"]
    assert "Longsword" in values["Equipment"]
    assert values["Backstory"] == "A soldier from the border wars."


def test_fill_leaves_spell_fields_untouched_for_non_caster():
    values = _fill_and_read_fields()
    assert values.get("Spellcasting Class 2") in (None, "")


def test_fill_populates_spellcasting_for_caster():
    caster_sheet = dict(SHEET)
    caster_sheet["classes"] = [{"cls": "Cleric", "subclass": "Life", "level": 1}]
    caster_derived = dict(DERIVED)
    caster_derived["spellcasting"] = {"ability": "WIS", "save_dc": 13, "attack_bonus": 5}
    data = pdf_fill.fill(caster_sheet, caster_derived)
    import io
    reader = PdfReader(io.BytesIO(data))
    fields = reader.get_fields() or {}
    values = {k: (v.get("/V") if isinstance(v, dict) else None) for k, v in fields.items()}
    assert values["Spellcasting Class 2"] == "Cleric"
    assert values["SpellcastingAbility 2"] == "WIS"
    assert values["SpellSaveDC  2"] == "13"
    assert values["SpellAtkBonus 2"] == "+5"
