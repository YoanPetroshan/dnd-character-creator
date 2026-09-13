import sheet_derive
from chargen.catalog import Catalog

CATALOG = Catalog.load()


def _fighter_sheet_and_draft():
    """A level-1 Human Fighter (Soldier background), no armor equipped —
    matches build.py's own sheet shape so this test doubles as a shape check."""
    sheet = {
        "name": "Torvin Bracewell",
        "race": "Human",
        "background": "Soldier",
        "classes": [{"cls": "Fighter", "subclass": "", "level": 1}],
        "ability_scores": {"STR": 16, "DEX": 14, "CON": 14,
                           "INT": 10, "WIS": 12, "CHA": 8},
        "proficiencies": {
            "saving_throws": ["STR", "CON"],
            "skills": ["Athletics", "Intimidation"],
            "armor": ["Light Armor", "Medium Armor", "Heavy Armor", "Shields"],
            "weapons": ["Simple Weapons", "Martial Weapons"],
            "tools": [],
            "languages": ["Common"],
        },
        "equipment": [],
    }
    draft = {"equipped_armor_id": None, "shield": False}
    return sheet, draft


def test_ac_no_armor_is_10_plus_dex_mod():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # DEX 14 -> mod +2 -> AC 12 unarmored
    assert out["ac"] == 12


def test_ac_with_equipped_armor():
    sheet, draft = _fighter_sheet_and_draft()
    chain_shirt = next(a for a in CATALOG.armor() if a["name"] == "Chain Shirt")
    draft = {"equipped_armor_id": chain_shirt["id"], "shield": True}
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # Chain Shirt: base_ac 13, medium armor -> dex capped at +2 -> 13+2=15, +2 shield -> 17
    assert out["ac"] == 15 + 2


def test_proficiency_bonus_level_1():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    assert out["proficiency_bonus"] == 2


def test_skill_bonus_proficient_vs_not():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # Athletics (STR, proficient): mod +3, prof +2 -> +5
    assert out["skills"]["Athletics"] == 5
    # Acrobatics (DEX, not proficient): mod +2, no prof -> +2
    assert out["skills"]["Acrobatics"] == 2


def test_save_bonus_proficient_vs_not():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # STR save (proficient): mod +3, prof +2 -> +5
    assert out["saves"]["STR"] == 5
    # DEX save (not proficient): mod +2, no prof -> +2
    assert out["saves"]["DEX"] == 2


def test_passive_perception():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    # Perception (WIS 12 -> mod +1, not proficient) -> 10 + 1 = 11
    assert out["passive_perception"] == 11


def test_non_caster_has_no_spellcasting_block():
    sheet, draft = _fighter_sheet_and_draft()
    out = sheet_derive.derive(sheet, CATALOG, draft)
    assert out["spellcasting"] is None


def test_caster_has_spellcasting_block():
    sheet = {
        "name": "Sylwen Nightbrook",
        "race": "Wood Elf",
        "background": "Acolyte",
        "classes": [{"cls": "Cleric", "subclass": "Life", "level": 1}],
        "ability_scores": {"STR": 10, "DEX": 12, "CON": 14,
                           "INT": 10, "WIS": 16, "CHA": 12},
        "proficiencies": {
            "saving_throws": ["WIS", "CHA"], "skills": ["Insight", "Religion"],
            "armor": [], "weapons": [], "tools": [], "languages": [],
        },
        "equipment": [],
    }
    draft = {"equipped_armor_id": None, "shield": False}
    out = sheet_derive.derive(sheet, CATALOG, draft)
    assert out["spellcasting"] is not None
    assert out["spellcasting"]["ability"] == "WIS"
    # WIS 16 -> mod +3, prof +2 -> DC 8+2+3=13, atk +2+3=5
    assert out["spellcasting"]["save_dc"] == 13
    assert out["spellcasting"]["attack_bonus"] == 5
