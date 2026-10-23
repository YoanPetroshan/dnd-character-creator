"""C9b: 2024 class starting equipment packages (XPHB), ruleset 2024 only.

Governing text: the `entries` line of every XPHB class record's `startingEquipment` (read from the
5etools class files on 2026-10-11; the 2024 PHB markdown carries only the ch. 6 item tables and the
pack contents, not the per-class lines). Choose A or B (Fighter A, B or C); gold is "GP":

  Barbarian (A) Greataxe, 4 Handaxes, Explorer's Pack, 15 GP | (B) 75 GP
  Bard      (A) Leather Armor, 2 Daggers, Musical Instrument of your choice, Entertainer's Pack, 19 GP | (B) 90 GP
  Cleric    (A) Chain Shirt, Shield, Mace, Holy Symbol, Priest's Pack, 7 GP | (B) 110 GP
  Druid     (A) Leather Armor, Shield, Sickle, Druidic Focus (Quarterstaff), Explorer's Pack,
            Herbalism Kit, 9 GP | (B) 50 GP
  Fighter   (A) Chain Mail, Greatsword, Flail, 8 Javelins, Dungeoneer's Pack, 4 GP |
            (B) Studded Leather Armor, Scimitar, Shortsword, Longbow, 20 Arrows, Quiver,
            Dungeoneer's Pack, 11 GP | (C) 155 GP
  Monk      (A) Spear, 5 Daggers, Artisan's Tools or Musical Instrument chosen for the tool
            proficiency above, Explorer's Pack, 11 GP | (B) 50 GP
  Paladin   (A) Chain Mail, Shield, Longsword, 6 Javelins, Holy Symbol, Priest's Pack, 9 GP | (B) 150 GP
  Ranger    (A) Studded Leather Armor, Scimitar, Shortsword, Longbow, 20 Arrows, Quiver,
            Druidic Focus (sprig of mistletoe), Explorer's Pack, 7 GP | (B) 150 GP
  Rogue     (A) Leather Armor, 2 Daggers, Shortsword, Shortbow, 20 Arrows, Quiver, Thieves' Tools,
            Burglar's Pack, 8 GP | (B) 100 GP
  Sorcerer  (A) Spear, 2 Daggers, Arcane Focus (crystal), Dungeoneer's Pack, 28 GP | (B) 50 GP
  Warlock   (A) Leather Armor, Sickle, 2 Daggers, Arcane Focus (orb), Book (occult lore),
            Scholar's Pack, 15 GP | (B) 100 GP
  Wizard    (A) 2 Daggers, Arcane Focus (Quarterstaff), Robe, Spellbook, Scholar's Pack, 5 GP | (B) 55 GP

Name -> catalog item map (the catalog is the SRD item list): "Arrows (20)" -> ONE `arrow` (the catalog item is already a 20-pack; F3a-6), "Robe" ->
`robes`, "Spellbook" -> `spellbook`, "Druidic Focus (Quarterstaff)" -> `quarterstaff`, "Holy Symbol"
-> a nested pick over the Holy Symbol table (Amulet / Emblem / Reliquary, PHB ch. 6), "Musical
Instrument" -> a nested pick over the instruments, the Monk's tool -> the sentinel `monk-tool` (the
item of the tool proficiency pick). Decision E8: quantities are kept ONLY on this 2024 class path
(`ChoiceOption.quantities`); the SRD / mixed bundles stay qty 1.

Data defect handled on purpose (text wins, same rule as E9): the Cleric A record says
`"value": 7000` (70 GP) while its own entries line says "7 GP".

Cases: converter (12 classes, no placeholder member, gold equals the entries text, A/B/C shape) |
resolve (card, quantities, gold, nested picks, AC, Monk sentinel, Wizard spellbook, Ranger arrows) |
B options give only gold | secondary class has no equipment card | mixed / 2014 unchanged (the F0
golden covers them byte for byte; spot-checked here) | SRD-only catalog keeps the SRD packages |
G2 worn / wielded interplay | speed."""
import re
import time

import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official import class_chassis
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue",
           "sorcerer", "warlock", "wizard"]

# class -> {letter: (member ids in order, {id: qty} for qty != 1, gold)}
EXPECTED = {
    "barbarian": {"A": (["greataxe", "handaxe", "explorers-pack", "gp-15"], {"handaxe": 4}), "B": (["gp-75"], {})},
    "bard": {"A": (["leather-armor", "dagger", "any-musical-instruments", "entertainers-pack", "gp-19"], {"dagger": 2}),
             "B": (["gp-90"], {})},
    "cleric": {"A": (["chain-shirt", "shield", "mace", "any-holy-symbols", "priests-pack", "gp-7"], {}),
               "B": (["gp-110"], {})},
    "druid": {"A": (["leather-armor", "shield", "sickle", "quarterstaff", "explorers-pack", "herbalism-kit", "gp-9"], {}),
              "B": (["gp-50"], {})},
    "fighter": {"A": (["chain-mail", "greatsword", "flail", "javelin", "dungeoneers-pack", "gp-4"], {"javelin": 8}),
                "B": (["studded-leather-armor", "scimitar", "shortsword", "longbow", "arrow", "quiver",
                       "dungeoneers-pack", "gp-11"], {}),
                "C": (["gp-155"], {})},
    "monk": {"A": (["spear", "dagger", "monk-tool", "explorers-pack", "gp-11"], {"dagger": 5}), "B": (["gp-50"], {})},
    "paladin": {"A": (["chain-mail", "shield", "longsword", "javelin", "any-holy-symbols", "priests-pack", "gp-9"],
                      {"javelin": 6}), "B": (["gp-150"], {})},
    "ranger": {"A": (["studded-leather-armor", "scimitar", "shortsword", "longbow", "arrow", "quiver",
                      "sprig-of-mistletoe", "explorers-pack", "gp-7"], {}), "B": (["gp-150"], {})},
    "rogue": {"A": (["leather-armor", "dagger", "shortsword", "shortbow", "arrow", "quiver", "thieves-tools",
                     "burglars-pack", "gp-8"], {"dagger": 2}), "B": (["gp-100"], {})},
    "sorcerer": {"A": (["spear", "dagger", "crystal", "dungeoneers-pack", "gp-28"], {"dagger": 2}), "B": (["gp-50"], {})},
    "warlock": {"A": (["leather-armor", "sickle", "dagger", "orb", "book", "scholars-pack", "gp-15"], {"dagger": 2}),
                "B": (["gp-100"], {})},
    "wizard": {"A": (["dagger", "quarterstaff", "robes", "spellbook", "scholars-pack", "gp-5"], {"dagger": 2}),
               "B": (["gp-55"], {})},
}
PLACEHOLDER = ("unlisted-", "category-", "flavor-")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls="fighter", level=1, ruleset="2024", eq=None, scores=None, classes=None, choices=None, added=(), **extra):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": scores or {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": eq or {}, "added": list(added), "skipped": False, **extra},
        "classes": classes or [{"classId": cls, "level": level, "choices": choices or {}}],
    }


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _cid(cls):
    return f"class:{cls}:1:equipment-choice-0"


def _option(catalog_or_res, cls, letter):
    """The A/B/C option of a class overlay (index 0/1/2)."""
    envelope = catalog_or_res.classes_2024[cls]["starting_equipment_options"][0]
    return envelope["from"]["options"]["ABC".index(letter)]


def _opt_id(res, cls, letter):
    return _card(res, _cid(cls))["options"]["ABC".index(letter)]["id"]


def _chosen(res):
    return {e["itemId"]: e["qty"] for e in res["sheet"]["equipment"]["chosen"]}


def _members(option):
    return [(m["of"]["index"], m.get("count", 1)) for m in option["items"] if m["option_type"] == "counted_reference"
            ] + [("choice:" + m["choice"]["from"]["equipment_category"]["index"], 1)
                 for m in option["items"] if m["option_type"] == "choice"]


# ------------------------------------------------------------------ converter

@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_converter_replaces_the_srd_package_and_has_no_placeholder_member(catalog, cid):
    cls = catalog.classes_2024[cid]
    assert cls["starting_equipment"] == []
    assert cls["starting_equipment_options"] != catalog.classes[cid]["starting_equipment_options"]
    envelopes = cls["starting_equipment_options"]
    assert len(envelopes) == 1 and envelopes[0]["keep_counts"] is True
    options = envelopes[0]["from"]["options"]
    assert len(options) == (3 if cid == "fighter" else 2)
    for option in options:
        for member in option["items"]:
            if member["option_type"] == "counted_reference":
                index = member["of"]["index"]
                assert not index.startswith(PLACEHOLDER), (cid, index)
                assert index.startswith("gp-") or index == class_chassis.MONK_TOOL_SENTINEL or index in catalog.items, (cid, index)
            else:
                assert member["option_type"] == "choice"


@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_every_class_package_matches_the_text(catalog, cid):
    for letter, (ids, quantities) in EXPECTED[cid].items():
        members = _members(_option(catalog, cid, letter))
        got_ids = [("any-" + i[7:] if i.startswith("choice:") else i) for i, _ in members]
        # nested picks are listed after the counted members in _members; compare as multisets
        assert sorted(got_ids) == sorted(ids), (cid, letter)
        got_q = {i: n for i, n in members if n != 1}
        assert got_q == quantities, (cid, letter)


@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_gold_equals_the_entries_text(catalog, cid):
    text = catalog.class_2024_records[cid]["starting_equipment"]["entries"][0]
    segments = re.split(r"\(([ABC])\)", text)[1:]
    by_letter = {segments[i]: segments[i + 1] for i in range(0, len(segments), 2)}
    assert set(by_letter) == set(EXPECTED[cid])
    for letter, segment in by_letter.items():
        text_gold = int(re.search(r"(\d+) GP", segment).group(1))
        ids = [i for i, _ in _members(_option(catalog, cid, letter))]
        gold = [int(i[3:]) for i in ids if i.startswith("gp-")]
        assert gold == [text_gold], (cid, letter)


@needs_data
def test_cleric_gold_follows_the_text_not_the_defective_value(catalog):
    assert catalog.class_2024_records["cleric"]["starting_equipment"]["defaultData"][0]["A"][-1] == {"value": 7000}
    assert ("gp-7", 1) in _members(_option(catalog, "cleric", "A"))


@needs_data
def test_background_converter_is_untouched_by_the_class_path(catalog):
    from catalog.official import equipment
    with pytest.raises(KeyError):  # the plural Monk member still crashes the BACKGROUND converter (E12 scope)
        equipment._starting_equipment_options_from_5etools(
            {"startingEquipment": catalog.class_2024_records["monk"]["starting_equipment"]["defaultData"]})


# -------------------------------------------------------------------- resolve

@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_every_class_shows_one_package_card_with_a_b(catalog, cid):
    res = resolve(_draft(cid), catalog)
    card = _card(res, _cid(cid))
    assert card["count"] == 1 and len(card["options"]) == (3 if cid == "fighter" else 2)
    assert card["description"] and "GP" in card["description"] and "{@" not in card["description"]
    assert _card(res, f"class:{cid}:1:equipment-choice-1") is None
    assert [w for w in res["warnings"] if w["id"].startswith("equipment-envelope-dropped")] == []


@needs_data
def test_fighter_has_three_options_and_c_is_155_gold(catalog):
    res = resolve(_draft("fighter"), catalog)
    base = res["sheet"]["startingGold"]
    labels = [o["label"] for o in _card(res, _cid("fighter"))["options"]]
    assert labels[2] == "155 GP"
    res = resolve(_draft("fighter", eq={_cid("fighter"): [_opt_id(res, "fighter", "C")]}), catalog)
    assert res["sheet"]["startingGold"] == base + 155
    assert _chosen(res) == {}


@needs_data
def test_barbarian_a_quantities_and_gold(catalog):
    base = resolve(_draft("barbarian"), catalog)
    opt = _opt_id(base, "barbarian", "A")
    res = resolve(_draft("barbarian", eq={_cid("barbarian"): [opt]}), catalog)
    assert _chosen(res) == {"greataxe": 1, "handaxe": 4, "explorers-pack": 1}
    assert res["sheet"]["startingGold"] == base["sheet"]["startingGold"] + 15
    assert any(o.get("quantities") == {"handaxe": 4} for o in _card(res, _cid("barbarian"))["options"])
    # inventory / weight use the quantity: 4 handaxes
    assert res["sheet"]["equipment"]["chosen"][1]["qty"] == 4


@needs_data
def test_fighter_a_javelins_and_ranger_a_arrows_keep_their_quantity(catalog):
    base = resolve(_draft("fighter"), catalog)
    res = resolve(_draft("fighter", eq={_cid("fighter"): [_opt_id(base, "fighter", "A")]}), catalog)
    assert _chosen(res)["javelin"] == 8 and _chosen(res)["chain-mail"] == 1
    base = resolve(_draft("ranger"), catalog)
    res = resolve(_draft("ranger", eq={_cid("ranger"): [_opt_id(base, "ranger", "A")]}), catalog)
    assert _chosen(res)["arrow"] == 1 and _chosen(res)["quiver"] == 1 and _chosen(res)["sprig-of-mistletoe"] == 1


@needs_data
def test_cleric_a_nested_holy_symbol_pick_and_armor_class(catalog):
    cid = _cid("cleric")
    base = resolve(_draft("cleric", scores={"STR": 10, "DEX": 18, "CON": 12, "INT": 10, "WIS": 14, "CHA": 10}), catalog)
    assert _card(base, f"{cid}:0") is None  # nothing selected yet
    opt = _opt_id(base, "cleric", "A")
    scores = {"STR": 10, "DEX": 18, "CON": 12, "INT": 10, "WIS": 14, "CHA": 10}
    res = resolve(_draft("cleric", scores=scores, eq={cid: [opt]}), catalog)
    sub = _card(res, f"{cid}:0")
    assert {o["id"] for o in sub["options"]} == {"amulet", "emblem", "reliquary"} and sub["status"] == "pending"
    res = resolve(_draft("cleric", scores=scores, eq={cid: [opt], f"{cid}:0": ["emblem"]}), catalog)
    assert {"chain-shirt": 1, "shield": 1, "mace": 1, "emblem": 1, "priests-pack": 1}.items() <= _chosen(res).items()
    assert res["derived"]["armorClass"] == 13 + 2 + 2  # chain shirt + DEX capped at +2 + shield
    assert res["pruned"] == []


@needs_data
def test_bard_a_nested_instrument_pick_has_ten_options(catalog):
    cid = _cid("bard")
    base = resolve(_draft("bard"), catalog)
    res = resolve(_draft("bard", eq={cid: [_opt_id(base, "bard", "A")]}), catalog)
    sub = _card(res, f"{cid}:0")
    assert len(sub["options"]) == 10 and "lute" in {o["id"] for o in sub["options"]}
    res = resolve(_draft("bard", eq={cid: [_opt_id(base, "bard", "A")], f"{cid}:0": ["lute"]}), catalog)
    assert {"leather-armor": 1, "dagger": 2, "lute": 1, "entertainers-pack": 1}.items() <= _chosen(res).items()


@needs_data
def test_paladin_a_has_nested_holy_symbol_and_six_javelins(catalog):
    cid = _cid("paladin")
    base = resolve(_draft("paladin"), catalog)
    res = resolve(_draft("paladin", eq={cid: [_opt_id(base, "paladin", "A")], f"{cid}:0": ["amulet"]}), catalog)
    assert _chosen(res)["javelin"] == 6 and _chosen(res)["amulet"] == 1
    assert res["derived"]["armorClass"] == 16 + 2  # chain mail + shield


@needs_data
def test_monk_a_grants_the_tool_of_the_proficiency_pick(catalog):
    cid = _cid("monk")
    base = resolve(_draft("monk"), catalog)
    opt = _opt_id(base, "monk", "A")
    picks = {"class:monk:1:prof-choice-1": ["smiths-tools"]}
    res = resolve(_draft("monk", choices=picks, eq={cid: [opt]}), catalog)
    assert _chosen(res) == {"spear": 1, "dagger": 5, "smiths-tools": 1, "explorers-pack": 1}
    assert res["sheet"]["startingGold"] == base["sheet"]["startingGold"] + 11
    assert not any("Artisan" in n for n in res["sheet"]["equipment"]["narrativeItems"])
    instrument = {"class:monk:1:prof-choice-1": ["lute"]}
    res = resolve(_draft("monk", choices=instrument, eq={cid: [opt]}), catalog)
    assert _chosen(res)["lute"] == 1


@needs_data
def test_monk_a_without_a_tool_pick_is_a_narrative_item(catalog):
    base = resolve(_draft("monk"), catalog)
    res = resolve(_draft("monk", eq={_cid("monk"): [_opt_id(base, "monk", "A")]}), catalog)
    assert _chosen(res) == {"spear": 1, "dagger": 5, "explorers-pack": 1}
    assert any("tool proficiency" in n for n in res["sheet"]["equipment"]["narrativeItems"])


@needs_data
def test_wizard_a_grants_a_spellbook_and_robes(catalog):
    base = resolve(_draft("wizard"), catalog)
    res = resolve(_draft("wizard", eq={_cid("wizard"): [_opt_id(base, "wizard", "A")]}), catalog)
    assert _chosen(res) == {"dagger": 2, "quarterstaff": 1, "robes": 1, "spellbook": 1, "scholars-pack": 1}
    assert res["sheet"]["startingGold"] == base["sheet"]["startingGold"] + 5
    assert not any(n for n in res["sheet"]["equipment"]["narrativeItems"] if "robe" in n.lower())


@needs_data
def test_druid_a_quarterstaff_is_the_druidic_focus(catalog):
    base = resolve(_draft("druid"), catalog)
    res = resolve(_draft("druid", eq={_cid("druid"): [_opt_id(base, "druid", "A")]}), catalog)
    assert {"quarterstaff": 1, "sickle": 1, "herbalism-kit": 1, "shield": 1, "leather-armor": 1}.items() <= _chosen(res).items()
    assert res["derived"]["armorClass"] == 11 + 2 + 2  # leather + DEX 14 + shield


@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_gold_option_gives_only_gold(catalog, cid):
    """The last option (B, Fighter C) is gold only."""
    base = resolve(_draft(cid), catalog)
    letter = "C" if cid == "fighter" else "B"
    res = resolve(_draft(cid, eq={_cid(cid): [_opt_id(base, cid, letter)]}), catalog)
    assert _chosen(res) == {}
    gold = int(EXPECTED[cid][letter][0][0][3:])
    assert res["sheet"]["startingGold"] == base["sheet"]["startingGold"] + gold
    assert res["pruned"] == []


@needs_data
def test_stale_nested_pick_is_pruned_when_the_package_changes(catalog):
    cid = _cid("cleric")
    base = resolve(_draft("cleric"), catalog)
    res = resolve(_draft("cleric", eq={cid: [_opt_id(base, "cleric", "B")], f"{cid}:0": ["emblem"]}), catalog)
    assert [p["choiceId"] for p in res["pruned"]] == [f"{cid}:0"]


@needs_data
def test_secondary_class_has_no_equipment_card(catalog):
    res = resolve(_draft(classes=[{"classId": "fighter", "level": 1, "choices": {}},
                                  {"classId": "wizard", "level": 1, "choices": {}}]), catalog)
    assert _card(res, _cid("fighter")) is not None
    assert not [c for c in res["choices"] if c["id"].startswith("class:wizard:") and "equipment" in c["id"]]


@needs_data
@pytest.mark.parametrize("cid", CLASSES)
def test_package_a_raises_no_armor_warning(catalog, cid):
    """Every class is proficient with the armor and shield of its own package A."""
    cardid = _cid(cid)
    base = resolve(_draft(cid), catalog)
    eq = {cardid: [_opt_id(base, cid, "A")]}
    picks = {"monk": {"class:monk:1:prof-choice-1": ["lute"]}}.get(cid)
    res = resolve(_draft(cid, eq=eq, choices=picks), catalog)
    for nested in range(2):  # fill the nested holy symbol / instrument pick when there is one
        sub = _card(res, f"{cardid}:{nested}")
        if sub:
            eq[sub["id"]] = [sub["options"][0]["id"]]
    res = resolve(_draft(cid, eq=eq, choices=picks), catalog)
    problems = res["warnings"] + res["problems"]
    assert [p["id"] for p in problems if p["id"].startswith("armor-")] == [], cid
    assert res["pruned"] == []


@needs_data
def test_ranger_a_armor_warnings_and_weight(catalog):
    base = resolve(_draft("ranger"), catalog)
    res = resolve(_draft("ranger", eq={_cid("ranger"): [_opt_id(base, "ranger", "A")]}), catalog)
    assert res["derived"]["armorClass"] == 12 + 2  # studded leather + DEX 14
    assert res["derived"]["carryingCapacity"]["carried"] > base["derived"]["carryingCapacity"]["carried"]


@needs_data
def test_worn_wielded_interplay_with_a_package(catalog):
    cid = _cid("fighter")
    base = resolve(_draft("fighter"), catalog)
    eq = {cid: [_opt_id(base, "fighter", "A")]}
    auto = resolve(_draft("fighter", eq=eq), catalog)
    assert auto["derived"]["armorClass"] == 16
    attacks = {a["itemId"] for a in auto["derived"]["attacks"]}
    assert {"greatsword", "flail", "javelin"} <= attacks
    # wear nothing explicitly: worn.armor null drops the chain mail
    bare = resolve(_draft("fighter", eq=eq, worn={"armor": None, "shield": False}), catalog)
    assert bare["derived"]["armorClass"] == 10 + 2
    # wield only the greatsword
    wielded = resolve(_draft("fighter", eq=eq, wielded={"main": "greatsword", "off": None}), catalog)
    assert {a["itemId"] for a in wielded["derived"]["attacks"]} >= {"greatsword"}


@needs_data
def test_carried_quantity_reaches_the_inventory_weight(catalog):
    base = resolve(_draft("fighter"), catalog)
    res = resolve(_draft("fighter", eq={_cid("fighter"): [_opt_id(base, "fighter", "A")]}), catalog)
    javelin = catalog.items["javelin"]["weight"]
    other = resolve(_draft("fighter", eq={_cid("fighter"): [_opt_id(base, "fighter", "A")]}, added=[
        {"itemId": "javelin", "qty": 1, "equipped": False}]), catalog)
    delta = other["derived"]["carryingCapacity"]["carried"] - res["derived"]["carryingCapacity"]["carried"]
    assert delta == pytest.approx(javelin)  # 1 more javelin on top of the 8 from the package
    package = res["derived"]["carryingCapacity"]["carried"] - base["derived"]["carryingCapacity"]["carried"]
    assert package >= 8 * javelin


# -------------------------------------------------------- isolation / degrade

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_keep_the_srd_packages_with_the_text_counts(catalog, ruleset):
    res = resolve(_draft("fighter", ruleset=ruleset), catalog)
    card = _card(res, "class:fighter:1:equipment-choice-0")
    assert card is not None
    # RPX3: the SRD envelopes carry the counts of the text under mixed / 2014 too (Fighter: two handaxes); the
    # ammunition packs ("20 arrows") stay one unit and the SRD data itself carries no keep_counts flag.
    quantified = {(c["id"], o["id"]): o["quantities"] for c in res["choices"] for o in c["options"] if "quantities" in o}
    assert quantified == {("class:fighter:1:equipment-choice-2", "handaxe"): {"handaxe": 2}}
    assert _card(res, "class:fighter:1:equipment-choice-3") is not None  # the four SRD Fighter envelopes
    srd = catalog.classes["fighter"]["starting_equipment_options"]
    assert all("keep_counts" not in e for e in srd)
    paladin = resolve(_draft("paladin", ruleset=ruleset), catalog)
    assert {o["id"] for o in _card(paladin, "class:paladin:1:equipment-choice-0")["options"]} == {
        "any-martial-weapons+shield", "any-martial-weapons"}


def test_srd_only_catalog_keeps_the_srd_equipment(monkeypatch):
    monkeypatch.setattr(official_source, "class_dir", lambda: None)
    cat = load()
    assert cat.classes_2024 == {}
    res = resolve(_draft("paladin"), cat)
    assert {o["id"] for o in _card(res, "class:paladin:1:equipment-choice-0")["options"]} == {
        "any-martial-weapons+shield", "any-martial-weapons"}
    wiz = resolve(_draft("wizard"), cat)
    assert "spellbook" in _chosen(wiz) or any(e["itemId"] == "spellbook" for e in wiz["sheet"]["equipment"]["granted"])


@needs_data
def test_a_record_without_default_data_keeps_the_srd_equipment(catalog):
    records = {k: dict(v) for k, v in catalog.class_2024_records.items()}
    records["fighter"] = {**records["fighter"], "starting_equipment": {}}
    out = class_chassis.convert_class_chassis_2024(records, catalog.classes)
    assert out["fighter"]["starting_equipment_options"] == catalog.classes["fighter"]["starting_equipment_options"]
    assert out["fighter"]["starting_equipment"] == catalog.classes["fighter"]["starting_equipment"]
    assert out["cleric"]["starting_equipment_options"][0]["keep_counts"] is True


@needs_data
def test_unmapped_member_raises(catalog):
    records = {"fighter": {**catalog.class_2024_records["fighter"], "starting_equipment": {
        "defaultData": [{"A": [{"item": "gizmo of nothing|xphb"}]}], "entries": []}}}
    with pytest.raises(ValueError):
        class_chassis.convert_class_chassis_2024(records, catalog.classes)


@needs_data
def test_timing_reference_characters(catalog):
    cases = [
        _draft("fighter", level=20), _draft("wizard", level=20), _draft("cleric"),
        _draft("monk", eq={_cid("monk"): ["spear+dagger+monk-tool+explorers-pack+gp-11"]}),
    ]
    for ruleset in ("2024", "mixed"):
        for draft in cases:
            draft = {**draft, "ruleset": ruleset}
            resolve(draft, catalog)
            start = time.perf_counter()
            for _ in range(20):
                resolve(draft, catalog)
            assert (time.perf_counter() - start) / 20 < 0.05
