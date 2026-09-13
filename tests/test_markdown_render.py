import markdown_render

SHEET = {
    "name": "Torvin Bracewell",
    "player": "",
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
    "features_traits": [{"name": "Second Wind", "description": "Once per rest...",
                         "source": "Class"}],
    "backstory": "A soldier from the border wars.",
    "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 15, "pp": 0},
    "equipment": [{"name": "Chain Shirt", "equipped": True, "quantity": 1},
                  {"name": "Longsword", "equipped": False, "quantity": 1}],
    "spellcasting": [], "spells": [], "spell_slots": {},
}
DERIVED = {
    "ac": 15, "initiative": 2, "proficiency_bonus": 2, "passive_perception": 11,
    "ability_mods": {"STR": 3, "DEX": 2, "CON": 2, "INT": 0, "WIS": 1, "CHA": -1},
    "skills": {"Athletics": 5, "Intimidation": 1},
    "saves": {"STR": 5, "DEX": 2, "CON": 4, "INT": 0, "WIS": 1, "CHA": -1},
    "spellcasting": None,
}


def test_render_includes_name_heading():
    out = markdown_render.render(SHEET, DERIVED)
    assert out.startswith("# Torvin Bracewell\n")


def test_render_includes_hp_line():
    out = markdown_render.render(SHEET, DERIVED)
    assert "**HP:** 12 / 12" in out


def test_render_includes_ac_and_combat_stats():
    out = markdown_render.render(SHEET, DERIVED)
    assert "**AC:** 15" in out
    assert "**Initiative:** +2" in out
    assert "**Speed:** 30" in out
    assert "**Passive Perception:** 11" in out


def test_render_includes_ability_scores_and_mods():
    out = markdown_render.render(SHEET, DERIVED)
    assert "**STR** 16 (+3)" in out


def test_render_includes_skills_with_bonus():
    out = markdown_render.render(SHEET, DERIVED)
    assert "Athletics" in out and "+5" in out


def test_render_includes_equipment_and_features_and_backstory():
    out = markdown_render.render(SHEET, DERIVED)
    assert "Chain Shirt" in out
    assert "Second Wind" in out
    assert "A soldier from the border wars." in out


def test_render_omits_spellcasting_section_for_non_caster():
    out = markdown_render.render(SHEET, DERIVED)
    assert "## Spellcasting" not in out


def test_render_includes_spellcasting_section_for_caster():
    caster_sheet = dict(SHEET)
    caster_sheet["classes"] = [{"cls": "Cleric", "subclass": "Life", "level": 1}]
    caster_sheet["spells"] = [{"name": "Cure Wounds", "cls": "Cleric", "prepared": True}]
    caster_derived = dict(DERIVED)
    caster_derived["spellcasting"] = {"ability": "WIS", "save_dc": 13, "attack_bonus": 5}
    out = markdown_render.render(caster_sheet, caster_derived)
    assert "## Spellcasting" in out
    assert "Cure Wounds" in out
    assert "**Save DC** 13" in out
