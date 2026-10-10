"""F2-A: resource `details` that the export line used to drop are printed in plain Bulgarian."""
from export_fields import resource_line

_BASE = {"name": "X", "uses": 2, "recharge": "long"}


def _line(details, **extra):
    return resource_line({**_BASE, "details": details, **extra})


def test_rage_resistances_list_damage_types():
    line = _line({"damageBonus": 2, "resistances": ["bludgeoning", "piercing", "slashing"]})
    assert "съпротива: дробящи, пробождащи, режещи" in line


def test_totem_bear_resistances_summarised():
    types = ["acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
             "poison", "radiant", "slashing", "thunder"]
    assert "съпротива: всички видове щета освен психична" in _line({"resistances": types})


def test_short_rest_regains():
    assert "1 използване се възстановява при кратка почивка" in _line({"shortRestRegains": 1})


def test_spell_slot_and_bonus_action_regains():
    assert "слот за заклинание" in _line({"spellSlotRegainsUse": True})
    assert "бонус действие" in _line({"bonusActionRegainsOne": True})


def test_arcane_recovery_and_slot_costs():
    line = _line({"maxSlotLevel": 5, "onShortRest": True})
    assert "при кратка почивка" in line and "слотове до ниво 5" in line
    assert "слот ниво 1 за 2 т., слот ниво 2 за 3 т." in _line({"slotCosts": {1: 2, 2: 3}})


def test_wild_shape_forms_fly_swim():
    line = _line({"maxCr": "1", "knownForms": 6, "fly": True, "swim": True})
    assert "известни форми: 6" in line and "летене" in line and "плуване" in line
    assert line.endswith("макс. CR 1")
    assert "летене" not in _line({"fly": False, "swim": False})
