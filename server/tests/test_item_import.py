"""Slice 11c: mundane weapons/armor from items-base.json.

Counts are from a script over the raw file (2026-10-09): 230 base items, 125 of
weapon/armor type; 101 are SRD (`srd`/`srd52`); of the 24 left, 16 are modern or
futuristic firearms with their XDMG reprints (skipped) and 3 have rarity
"unknown", leaving 5 imported items."""
import pytest

from catalog import choices as choices_mod
from catalog.loader import load
from catalog.official import items as items_mod
from catalog.official_source import items_base_file
from engine.resolve import resolve

needs_items = pytest.mark.skipif(items_base_file() is None, reason="items-base.json not available")
IMPORTED = {"double-bladed-scimitar", "hoopak", "musket", "pistol", "yklwa"}


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def client():
    import app as app_module
    return app_module.app.test_client()


def _raw(name="Blade", type_="M", **extra):
    raw = {"name": name, "source": "XGE", "type": type_, "rarity": "none", "weight": 3, "value": 1500,
           "weaponCategory": "martial", "dmg1": "1d8", "dmgType": "S"}
    raw.update(extra)
    return raw


def test_weapon_mapping():
    item = items_mod._item_from_5etools(_raw(property=["V", "F"], dmg2="1d10"))
    assert item["equipment_category"] == {"index": "weapon", "name": "Weapon"}
    assert (item["weapon_category"], item["weapon_range"], item["category_range"]) == ("Martial", "Melee", "Martial Melee")
    assert item["damage"] == {"damage_dice": "1d8", "damage_type": {"index": "slashing", "name": "Slashing"}}
    assert item["two_handed_damage"]["damage_dice"] == "1d10"
    assert [p["index"] for p in item["properties"]] == ["versatile", "finesse"]
    assert item["cost"] == {"quantity": 15, "unit": "gp"} and item["range"] == {"normal": 5}
    assert item["source"] == "XGE" and item["ruleset"] == "2014"


def test_ranged_thrown_and_cost_units():
    bow = items_mod._item_from_5etools(_raw(type_="R", range="80/320", value=25, property=["A", "LD"]))
    assert bow["weapon_range"] == "Ranged" and bow["range"] == {"normal": 80, "long": 320}
    assert bow["cost"] == {"quantity": 25, "unit": "cp"}
    assert items_mod._cost(1000) == {"quantity": 10, "unit": "gp"} and items_mod._cost(50) == {"quantity": 5, "unit": "sp"}
    spear = items_mod._item_from_5etools(_raw(property=["T"], range="20/60"))
    assert spear["range"] == {"normal": 5} and spear["throw_range"] == {"normal": 20, "long": 60}


def test_armor_mapping():
    medium = items_mod._item_from_5etools({"name": "Plate-ish", "source": "XGE", "type": "MA", "rarity": "none", "ac": 14,
                                           "strength": "13", "stealth": True, "weight": 20, "value": 7500})
    assert medium["armor_category"] == "Medium" and medium["armor_class"] == {"base": 14, "dex_bonus": True, "max_bonus": 2}
    assert medium["str_minimum"] == 13 and medium["stealth_disadvantage"] is True
    shield = items_mod._item_from_5etools({"name": "Buckler", "source": "XGE", "type": "S", "rarity": "none", "ac": 1, "weight": 2, "value": 500})
    assert shield["armor_category"] == "Shield" and shield["armor_class"] == {"base": 1, "dex_bonus": False}
    heavy = items_mod._item_from_5etools({"name": "Slab", "source": "XGE", "type": "HA", "rarity": "none", "ac": 17, "weight": 60})
    assert heavy["armor_class"] == {"base": 17, "dex_bonus": False} and heavy["str_minimum"] == 0


def test_eligibility_filters():
    for extra in ({"rarity": "rare"}, {"rarity": "unknown"}, {"srd": True}, {"srd52": True}, {"age": "modern"}, {"age": "futuristic"}):
        assert items_mod._item_from_5etools(_raw(**extra)) is None
    assert items_mod._item_from_5etools(_raw(type_="INS")) is None
    assert items_mod._item_from_5etools(_raw(age="renaissance")) is not None


def test_convert_skips_srd_names_twins_and_resolves_ids():
    raws = [
        _raw("Light Crossbow", "R"),  # SRD "Crossbow, light"
        _raw("Blade"), _raw("Blade", source="XPHB", type="M|XPHB"),  # 2024 twin of a kept 2014 item
        _raw("Old", reprintedAs=["New|XPHB"]), _raw("New", source="XPHB", type="M|XPHB"),
        _raw("Solo", source="XPHB", type="M|XPHB"),  # a 2024 item with no 2014 counterpart
        _raw("Dagger", source="XGE"),  # name of an SRD item
    ]
    out = items_mod.convert_items(raws, {"longsword"})
    assert sorted(out) == ["blade", "old", "solo-xphb"]
    assert out["solo-xphb"]["ruleset"] == "2024" and out["blade"]["index"] == "blade"
    clash = items_mod.convert_items([_raw("Blade")], {"blade"})
    assert list(clash) == ["blade-xge"]


@needs_items
def test_real_items_are_imported_and_srd_wins(catalog):
    imported = {i for i, it in catalog.items.items() if it.get("source") != "SRD"}
    assert imported == IMPORTED
    assert "light-crossbow" not in catalog.items and "crossbow-light" in catalog.items
    assert catalog.items["longsword"]["source"] == "SRD" and catalog.items["longsword"]["damage"]["damage_dice"] == "1d8"
    assert catalog.items["chain-mail"]["armor_class"]["base"] == 16
    assert catalog.items["musket"]["cost"] == {"quantity": 500, "unit": "gp"}


@needs_items
def test_api_items_lists_sources_and_filters(client):
    rows = client.get("/api/items?q=yklwa").get_json()["items"]
    assert rows == [{"id": "yklwa", "name": "Yklwa", "category": "weapon", "source": "ToA", "ruleset": "2014"}]
    assert client.get("/api/items?q=yklwa&sources=phb").get_json()["items"] == []
    assert len(client.get("/api/items?q=yklwa&sources=toa").get_json()["items"]) == 1
    assert client.get("/api/items?q=yklwa&ruleset=2024").get_json()["items"][0]["id"] == "yklwa"  # 2014 items stay usable
    longsword = client.get("/api/items?q=longsword&sources=phb").get_json()["items"]
    assert longsword[0]["source"] == "SRD"
    assert client.get("/api/items?q=light%20crossbow").get_json()["items"] == []


@needs_items
def test_starting_equipment_categories_ignore_imported_items(catalog):
    srd_only = {k: v for k, v in catalog.items.items() if v.get("source") == "SRD"}
    for category in ("martial-weapons", "simple-weapons", "martial-melee-weapons", "simple-ranged-weapons"):
        assert (choices_mod.equipment_category_options(category, catalog.items)
                == choices_mod.equipment_category_options(category, srd_only))
    martial = choices_mod.equipment_category_options("martial-weapons", catalog.items)
    assert "double-bladed-scimitar" not in {o["id"] for o in martial}


def _gear(cls, item):
    return {
        "name": "T", "sources": [], "classes": [{"classId": cls, "level": 1, "subclassId": None, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 12, "CON": 14, "INT": 10, "WIS": 12, "CHA": 10}},
        "equipment": {"choices": {}, "skipped": False, "added": [{"itemId": item, "qty": 1, "equipped": True}]},
    }


@needs_items
def test_imported_weapon_attacks_use_category_proficiency(catalog):
    attack = lambda cls: next(a for a in resolve(_gear(cls, "double-bladed-scimitar"), catalog)["derived"]["attacks"]  # noqa: E731
                              if a["itemId"] == "double-bladed-scimitar")
    assert attack("fighter")["proficient"] is True and attack("fighter")["damage"].startswith("2d4")
    assert attack("wizard")["proficient"] is False
    musket = next(a for a in resolve(_gear("fighter", "musket"), catalog)["derived"]["attacks"] if a["itemId"] == "musket")
    assert musket["ability"] == "DEX" and musket["damageType"] == "piercing"


@needs_items
def test_existing_item_ids_resolve_unchanged(catalog):
    res = resolve(_gear("fighter", "longsword"), catalog)
    assert any(a["itemId"] == "longsword" for a in res["derived"]["attacks"])
