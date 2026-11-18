"""The Bulgarian content overlay: store (hash, fallbacks), the spell-detail route, the translators' validator and the
offline pack. Every test uses a fixture overlay in a tmp dir, never the real server/data/i18n files."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

import service
from i18n.content import spells as tool
from i18n.content import tool as generic_tool
from i18n.content import store

ROOT = pathlib.Path(__file__).resolve().parents[2]

EN = {"desc": ["A bright streak deals 8d6 fire damage in a 20-foot radius.", "It ignites objects."],
      "higherLevel": ["The damage increases by 1d6 per slot level above 3."], "material": "A tiny ball of bat guano.",
      "castingCondition": None}
RECORD = {"index": "x", "name": "X", "desc": EN["desc"], "higher_level": EN["higherLevel"], "material": EN["material"], "casting_condition": None}


def good(**over):
    rec = {"id": "x", "hash": store.source_hash(EN),
           "desc": ["Ярка ивица нанася 8d6 щета от огън в радиус 20 фута (6 м).", "Запалва предмети."],
           "higherLevel": ["Щетата се увеличава с 1d6 на ниво над 3."], "material": "Малко топче прилепов гуано.",
           "castingCondition": None}
    rec.update(over)
    return rec


@pytest.fixture
def overlay_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "I18N_DIR", tmp_path)
    store.load_overlay.cache_clear()
    (tmp_path / "bg").mkdir()
    yield tmp_path
    store.load_overlay.cache_clear()


def write(overlay_dir, data):
    (overlay_dir / "bg" / "spells.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    store.load_overlay.cache_clear()


# --- store -----------------------------------------------------------------------------------------------------------

def test_source_hash_is_sha1_of_the_sorted_english_json():
    import hashlib

    expected = hashlib.sha1(json.dumps(EN, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert store.source_hash(EN) == expected
    assert store.source_hash({**EN, "desc": ["changed"]}) != expected


def test_a_missing_overlay_file_is_empty(overlay_dir):
    assert store.load_overlay("spells", "bg") == {}
    assert store.load_overlay("nothing", "bg") == {}


def test_overlay_applies_when_the_hash_matches(overlay_dir):
    write(overlay_dir, {"x": {k: v for k, v in good().items() if k != "id"}})
    out = store.overlay_spell(RECORD, {"name": "X", "desc": ["en"]}, "bg")
    assert out["textLang"] == "bg" and out["desc"] == good()["desc"] and out["higherLevel"] == good()["higherLevel"]
    assert out["material"] == good()["material"] and out.get("castingCondition") is None and out["name"] == "X"


def test_null_material_and_condition_stay_english(overlay_dir):
    write(overlay_dir, {"x": {**{k: v for k, v in good().items() if k != "id"}, "material": None}})
    out = store.overlay_spell(RECORD, {"material": "A tiny ball of bat guano.", "castingCondition": "c"}, "bg")
    assert out["textLang"] == "bg" and out["material"] == "A tiny ball of bat guano." and out["castingCondition"] == "c"


def test_stale_entry_falls_back_to_english(overlay_dir):
    write(overlay_dir, {"x": {**{k: v for k, v in good().items() if k != "id"}, "hash": "0" * 40}})
    out = store.overlay_spell(RECORD, {"desc": ["en"]}, "bg")
    assert out == {"desc": ["en"], "textLang": "en"}


def test_missing_entry_falls_back_to_english(overlay_dir):
    assert store.overlay_spell(RECORD, {"desc": ["en"]}, "bg")["textLang"] == "en"


def test_english_ignores_the_overlay(overlay_dir):
    write(overlay_dir, {"x": {k: v for k, v in good().items() if k != "id"}})
    assert store.overlay_spell(RECORD, {"desc": ["en"]}, "en") == {"desc": ["en"], "textLang": "en"}


# --- the route -------------------------------------------------------------------------------------------------------

def _detail(query=None):
    status, _ctype, _headers, body = service.handle("GET", "/api/spells/fireball", query)
    return status, json.loads(body)


def test_spell_detail_serves_the_overlay_in_bg(overlay_dir):
    spell = service._catalog.spells["fireball"]
    fields = store.spell_fields(spell)
    write(overlay_dir, {"fireball": {"hash": store.source_hash(fields), "desc": ["Огнена топка."] * len(fields["desc"]),
                                      "higherLevel": ["Повече."] * len(fields["higherLevel"]), "material": None, "castingCondition": None}})
    status, data = _detail("lang=bg")
    assert status == 200 and data["textLang"] == "bg" and data["desc"][0] == "Огнена топка."
    assert data["material"] == spell.get("material")
    status, data = _detail("lang=en")
    assert data["textLang"] == "en" and data["desc"] == spell["desc"]
    status, data = _detail()
    assert data["textLang"] == "en" and data["desc"] == spell["desc"]


def test_spell_detail_falls_back_when_stale(overlay_dir):
    write(overlay_dir, {"fireball": {"hash": "bad", "desc": ["x"], "higherLevel": [], "material": None, "castingCondition": None}})
    status, data = _detail("lang=bg")
    assert status == 200 and data["textLang"] == "en" and data["desc"] == service._catalog.spells["fireball"]["desc"]


def test_spell_detail_rejects_a_bad_lang():
    assert _detail("lang=xx")[0] == 400
    assert _detail("lang=BG")[0] == 400


def test_the_list_endpoint_is_unchanged(overlay_dir):
    status, _c, _h, body = service.handle("GET", "/api/spells", "class=wizard&lang=bg")
    assert status == 200 and "textLang" not in json.loads(body)["spells"][0]


# --- the validator ---------------------------------------------------------------------------------------------------

def reasons(**over):
    return tool.validate(EN, good(**over))


def test_a_good_record_passes():
    assert reasons() == []


@pytest.mark.parametrize("over,needle", [
    ({"hash": "0" * 40}, "hash"),
    ({"desc": ["Само един параграф 8d6, 20."]}, "desc: 1 paragraphs"),
    ({"higherLevel": []}, "higherLevel: 0 paragraphs"),
    ({"desc": ["Щета 20 8d6 фута.", ""]}, "empty paragraph"),
    ({"desc": ["Щета 8d6 20 фута.", "Запалва."], "higherLevel": ["Щетата 1d6 над 3 е повече"], "material": "Guano"}, "no Cyrillic"),
    ({"desc": ["Щета 8d8 20 фута.", "Запалва."]}, "dice expressions differ"),
    ({"desc": ["Щета 20 фута.", "Запалва."]}, "dice expressions differ"),
    ({"desc": ["Щета 8d6 в радиус от фута.", "Запалва."]}, "numbers missing"),
    ({"desc": ["Щета 8d6 20 фута.", "It ignites objects."]}, "no Cyrillic"),
    ({"material": "A tiny ball of bat guano."}, "no Cyrillic"),
    ({"castingCondition": "Условие"}, "castingCondition: the English spell has none"),
])
def test_validator_rejects(over, needle):
    assert any(needle in r for r in reasons(**over)), reasons(**over)


def test_a_paragraph_left_in_english_is_rejected_when_it_has_cyrillic_elsewhere():
    en = {**EN, "desc": ["Щета 8d6 на всяка цел", "ok"]}  # source text mixing scripts: same text copied back is "left in English"
    rec = {**good(), "hash": store.source_hash(en), "desc": list(en["desc"])}
    assert any("left in English" in r for r in tool.validate(en, rec))


def test_extra_numbers_in_bulgarian_are_allowed():
    assert reasons(desc=["Щета 8d6 в радиус 20 фута (6 м), 30 фута.", "Запалва 3 предмета."]) == []


def test_apply_merges_valid_records_and_reports_rejects(overlay_dir, monkeypatch, tmp_path):
    spells = {"x": RECORD, "y": {**RECORD, "index": "y"}}
    merged, results = tool.apply_records(spells, {}, [good(), good(id="y", desc=["bad"]), good(id="nope")])
    assert sorted(merged) == ["x"] and merged["x"]["desc"] == good()["desc"]
    assert dict(results)["x"] == [] and dict(results)["y"] and dict(results)["nope"] == ["id: unknown spell"]


def test_cli_export_apply_status_round_trip(overlay_dir, tmp_path, capsys):
    out = tmp_path / "w.json"
    assert tool.main(["export", "--ids", "fireball", "--out", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))[0]
    assert rec["id"] == "fireball" and rec["hash"] == store.source_hash(store.spell_fields(service._catalog.spells["fireball"]))
    rec["desc"] = [p.replace("fire", "огън") for p in rec["desc"]]  # still English: must be rejected
    out.write_text(json.dumps([rec], ensure_ascii=False), encoding="utf-8")
    assert tool.main(["apply", str(out)]) == 1
    assert "REJECT fireball" in capsys.readouterr().out
    assert not (overlay_dir / "bg" / "spells.json").exists()
    assert tool.main(["status"]) == 0
    assert "total" in capsys.readouterr().out


def test_export_only_missing_skips_translated(overlay_dir):
    spells = {"x": RECORD}
    assert [r["id"] for r in tool.export_records(spells, {}, only_missing=True)] == ["x"]
    assert tool.export_records(spells, {"x": {"hash": store.source_hash(EN)}}, only_missing=True) == []
    assert [r["id"] for r in tool.export_records(spells, {"x": {"hash": "old"}}, only_missing=True)] == ["x"]


def test_status_counts():
    spells = {"x": {**RECORD, "source": "A"}, "y": {**RECORD, "source": "A"}, "z": {**RECORD, "source": "B"}}
    counts = tool.status_counts(spells, {"x": {"hash": store.source_hash(EN)}, "y": {"hash": "old"}})
    assert counts["A"]["translated"] == 1 and counts["A"]["stale"] == 1 and counts["B"]["missing"] == 1


# --- the offline pack ------------------------------------------------------------------------------------------------

def test_the_pack_ships_the_overlays_but_not_the_tool_or_the_readme():
    spec = importlib.util.spec_from_file_location("build_offline_overlay_test", ROOT / "scripts" / "build_offline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    pack = module.app_files()
    assert "server/data/i18n/bg/spells.json" in pack
    assert "server/i18n/content/store.py" in pack and "server/i18n/content/__init__.py" in pack
    assert "server/i18n/content/spells.py" not in pack and "server/i18n/content/tool.py" not in pack
    assert not any(f.endswith("README.md") and "data/i18n" in f for f in pack)


def test_the_store_finds_the_overlay_where_the_pack_puts_it():
    assert store.I18N_DIR == ROOT / "server" / "data" / "i18n"


# --- species / items / item-rules ------------------------------------------------------------------------------------

SPECIES = {"index": "sp", "name": "Sp", "source": "SRD", "fluff": ["Elves live 750 years.", "They love art."],
           "traitDetails": [{"name": "Darkvision", "desc": ["You see 60 feet in the dark."]},
                            {"name": "Trance", "desc": ["Rest 4 hours.", "Dream a bit."]}]}
SP_EN = store.fields_for("species", SPECIES)
SP_BG = {"id": "sp", "hash": store.source_hash("species", SP_EN), "fluff": ["Елфите живеят 750 години.", "Обичат изкуството."],
         "traits": [{"desc": ["Виждаш на 60 фута в тъмното."]}, {"desc": ["Почивка 4 часа.", "Сънуваш малко."]}]}
ITEM = {"index": "it", "name": "It", "source": "SRD", "desc": ["Deals 2d6 acid damage."], "special": ["Needs 2 hands."]}
IT_EN = store.fields_for("items", ITEM)
IT_BG = {"id": "it", "hash": store.source_hash("items", IT_EN), "desc": ["Нанася 2d6 щета от киселина."], "special": ["Иска 2 ръце."]}


def test_spell_hash_is_unchanged_by_the_generalization():
    import hashlib

    assert store.source_hash("spells", EN) == store.source_hash(EN)
    # Frozen form of the pre-generalization hash: sorted-key JSON of the four spell fields.
    canon = json.dumps({"castingCondition": None, "desc": EN["desc"], "higherLevel": EN["higherLevel"], "material": EN["material"]},
                       ensure_ascii=False, sort_keys=True)
    assert store.source_hash(EN) == hashlib.sha1(canon.encode()).hexdigest()
    assert store.source_hash({"desc": None, "higherLevel": None, "material": None, "castingCondition": None}) == \
        store.source_hash({"desc": [], "higherLevel": [], "material": None, "castingCondition": None})


def test_the_committed_spell_overlay_is_all_fresh():
    from catalog.loader import load

    overlay = json.loads((ROOT / "server" / "data" / "i18n" / "bg" / "spells.json").read_text(encoding="utf-8"))
    spells = load().spells
    stale = [k for k, v in overlay.items() if k in spells and v["hash"] != store.source_hash(store.spell_fields(spells[k]))]
    assert stale == []


def test_kind_hashes_differ_and_follow_their_fields():
    assert store.source_hash("species", SP_EN) != store.source_hash("species", {**SP_EN, "fluff": ["x"]})
    assert store.source_hash("species", SP_EN) != store.source_hash("species", {**SP_EN, "traits": SP_EN["traits"][:1]})
    assert store.source_hash("items", IT_EN) != store.source_hash("items", {**IT_EN, "special": []})
    assert store.source_hash("items", {"desc": None, "special": None}) == store.source_hash("items", {"desc": [], "special": []})
    assert store.source_hash("item-rules", {"desc": ["a"]}) == store.source_hash("item-rules", {"desc": ["a"], "other": 1})


def test_species_validator():
    v = lambda **over: generic_tool.validate(SP_EN, {**SP_BG, **over}, "species")
    assert v() == []
    assert any("hash" in r for r in v(hash="0" * 40))
    assert any("fluff: 1 paragraphs" in r for r in v(fluff=["Елфи 750."]))
    assert any("traits: 1 traits" in r for r in v(traits=SP_BG["traits"][:1]))
    assert any("traits[1].desc: 1 paragraphs" in r for r in v(traits=[SP_BG["traits"][0], {"desc": ["Само един 4."]}]))
    assert any("numbers missing" in r for r in v(fluff=["Елфите живеят дълго.", "Обичат изкуството."]))
    assert any("no Cyrillic" in r for r in v(traits=[{"desc": ["You see 60 feet in the dark."]}, SP_BG["traits"][1]]))
    assert any("traits:" in r for r in v(traits="x"))


def test_items_validator():
    v = lambda **over: generic_tool.validate(IT_EN, {**IT_BG, **over}, "items")
    assert v() == []
    assert any("dice expressions differ" in r for r in v(desc=["Нанася 2d8 щета."]))
    assert any("special: 0 paragraphs" in r for r in v(special=[]))
    assert any("numbers missing" in r for r in v(special=["Иска две ръце."]))
    assert any("empty paragraph" in r for r in v(desc=[" "]))
    assert generic_tool.validate({"desc": ["Reach 5 feet."]}, {"hash": store.source_hash("item-rules", {"desc": ["Reach 5 feet."]}),
                                                            "desc": ["Обхват 5 фута."]}, "item-rules") == []


def test_apply_export_status_for_species_and_items(overlay_dir):
    recs = {"sp": SPECIES}
    exported = generic_tool.export_records(recs, {}, kind="species")
    assert exported[0]["hash"] == SP_BG["hash"] and exported[0]["traits"][0] == {"name": "Darkvision", "desc": SP_EN["traits"][0]}
    merged, results = generic_tool.apply_records(recs, {}, [SP_BG, {**SP_BG, "id": "nope"}], "species")
    assert merged == {"sp": {"hash": SP_BG["hash"], "fluff": SP_BG["fluff"], "traits": SP_BG["traits"]}}
    assert dict(results)["nope"] == ["id: unknown species"]
    assert generic_tool.status_counts(recs, merged, "species")["SRD"]["translated"] == 1
    assert generic_tool.status_counts(recs, {"sp": {"hash": "old"}}, "species")["SRD"]["stale"] == 1
    merged, results = generic_tool.apply_records({"it": ITEM}, {}, [IT_BG], "items")
    assert merged["it"] == {"hash": IT_BG["hash"], "desc": IT_BG["desc"], "special": IT_BG["special"]}
    assert generic_tool.export_records({"it": ITEM}, merged, only_missing=True, kind="items") == []


def test_overlay_species_and_items(overlay_dir):
    (overlay_dir / "bg" / "species.json").write_text(json.dumps({"sp": {k: v for k, v in SP_BG.items() if k != "id"}}), encoding="utf-8")
    (overlay_dir / "bg" / "items.json").write_text(json.dumps({"it": {k: v for k, v in IT_BG.items() if k != "id"}}), encoding="utf-8")
    store.load_overlay.cache_clear()
    out = store.overlay_species("sp", SPECIES, "bg")
    assert out["textLang"] == "bg" and out["fluff"] == SP_BG["fluff"]
    assert [t["desc"] for t in out["traitDetails"]] == [t["desc"] for t in SP_BG["traits"]]
    assert [t["name"] for t in out["traitDetails"]] == ["Darkvision", "Trance"]  # names stay English
    assert store.overlay_species("sp", SPECIES, "en")["textLang"] == "en"
    assert store.overlay_species("sp", {**SPECIES, "fluff": ["changed"]}, "bg")["fluff"] == ["changed"]
    assert store.overlay_species("other", SPECIES, "bg")["textLang"] == "en"
    out = store.overlay_items(ITEM, {"name": "It", "desc": ITEM["desc"], "special": ITEM["special"]}, "bg")
    assert out["textLang"] == "bg" and out["desc"] == IT_BG["desc"] and out["special"] == IT_BG["special"] and out["name"] == "It"
    assert store.overlay_items({**ITEM, "desc": ["new"]}, {"desc": ["new"]}, "bg")["textLang"] == "en"
    assert store.overlay_rule("property:reach:PHB", ["x"], "bg") is None


def test_the_cli_works_for_species_items_and_item_rules(overlay_dir, tmp_path, capsys):
    out = tmp_path / "w.json"
    assert generic_tool.main(["--kind", "species", "export", "--ids", "elf", "--out", str(out)]) == 0
    rec = json.loads(out.read_text(encoding="utf-8"))[0]
    assert rec["id"] == "elf" and rec["traits"][0]["name"]
    assert generic_tool.main(["--kind", "species", "apply", "--check", str(out)]) == 1  # still English
    assert "REJECT elf" in capsys.readouterr().out
    assert generic_tool.main(["--kind", "items", "status"]) == 0
    assert generic_tool.main(["--kind", "item-rules", "status"]) == 0
    assert not (overlay_dir / "bg" / "species.json").exists()


# --- the item route ----------------------------------------------------------------------------------------------------

def _item(item_id, query=None):
    status, _ctype, _headers, body = service.handle("GET", f"/api/items/{item_id}", query)
    return status, json.loads(body)


needs_official = pytest.mark.skipif(not service._catalog.item_properties, reason="needs the official data (SRD-only job)")


@needs_official
def test_item_detail_shape_for_weapon_armor_and_pack():
    status, sword = _item("longsword")
    assert status == 200 and sword["category"] == "weapon" and sword["damage"] == {"dice": "1d8", "type": "slashing"}
    assert sword["twoHandedDamage"] == {"dice": "1d10", "type": "slashing"} and sword["armor"] is None
    assert [p["id"] for p in sword["properties"]] == ["versatile"] and sword["textLang"] == "en"
    assert sword["mastery"]["name"] == "Sap"
    _, mail = _item("chain-mail")
    assert mail["armor"] == {"base": 16, "dexBonus": False, "maxBonus": None, "strMinimum": 13, "stealthDisadvantage": True}
    _, pack = _item("explorers-pack")
    assert {"id": "torch", "name": "Torch", "qty": 10} in pack["contents"]
    _, lance = _item("lance")
    assert lance["special"] and [p["id"] for p in lance["properties"]] == ["reach", "special"]
    assert lance["properties"][1]["desc"] == []


@needs_official
def test_item_detail_ruleset_picks_the_property_texts_and_hides_the_mastery_under_2014():
    _, mixed = _item("longsword")
    _, new = _item("longsword", "ruleset=2024")
    _, old = _item("longsword", "ruleset=2014")
    assert old["mastery"] is None and mixed["mastery"] and new["mastery"]
    assert mixed["properties"][0]["desc"] == old["properties"][0]["desc"] != new["properties"][0]["desc"]
    assert new["properties"][0]["desc"][0].startswith("A Versatile weapon")


def test_item_detail_errors():
    assert _item("no-such-item") == (404, {"error": "not found"})
    assert _item("longsword", "lang=xx")[0] == 400


@needs_official
def test_item_detail_overlay_and_text_lang(overlay_dir):
    lance = service._catalog.items["lance"]
    write_kind = lambda kind, data: ((overlay_dir / "bg" / f"{kind}.json").write_text(json.dumps(data), encoding="utf-8"), store.load_overlay.cache_clear())
    english = service._catalog.item_properties.get(("reach", "PHB"), [])
    mastery_en = service._catalog.weapon_masteries["Topple"]
    write_kind("items", {"lance": {"hash": store.source_hash("items", store.item_fields(lance)), "desc": [], "special": ["Специално."]}})
    status, data = _item("lance", "lang=bg")
    assert data["special"] == ["Специално."]
    assert data["mastery"]["desc"] == mastery_en and data["textLang"] == "en"  # the mastery text is still English
    rules = {"mastery:Topple": {"hash": store.source_hash("item-rules", {"desc": mastery_en}), "desc": ["Събаря."]}}
    if english:
        rules["property:reach:PHB"] = {"hash": store.source_hash("item-rules", {"desc": english}), "desc": ["Обхват."]}
    write_kind("item-rules", rules)
    _, data = _item("lance", "lang=bg")
    assert data["mastery"]["desc"] == ["Събаря."] and data["name"] == "Lance"
    assert data["properties"][1]["desc"] == []
    if english:
        assert data["properties"][0]["desc"] == ["Обхват."] and data["textLang"] == "bg"
    assert _item("lance")[1]["textLang"] == "en"  # lang=en ignores the overlay
    assert _item("lance", "lang=bg&ruleset=2014")[1]["mastery"] is None
    # an item without any prose and without properties: nothing English is left
    assert _item("backpack", "lang=bg")[1]["textLang"] == "bg"


@needs_official
def test_item_rule_records_and_cli(overlay_dir, tmp_path):
    recs = generic_tool.load_records("item-rules")
    assert "mastery:Sap" in recs
    assert "property:versatile:PHB" in recs and "property:versatile:XPHB" in recs
    assert not any(k.startswith(("property:special", "property:monk")) for k in recs)
    out = tmp_path / "w.json"
    assert generic_tool.main(["--kind", "item-rules", "export", "--ids", "mastery:Sap", "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))[0]["desc"] == service._catalog.weapon_masteries["Sap"]


def test_item_detail_without_official_data_still_answers():
    status, data = _item("longsword")
    assert status == 200 and data["properties"][0]["id"] == "versatile" and data["id"] == "longsword"


def _species(query=None, sid="elf"):
    status, _ctype, _headers, body = service.handle("GET", f"/api/catalog/species/{sid}", query)
    return status, json.loads(body)


def _write_species(overlay_dir, data):
    (overlay_dir / "bg" / "species.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_species_route_serves_the_overlay_in_bg(overlay_dir):
    _status, en = _species()
    assert en["textLang"] == "en"
    entry = {"hash": store.source_hash("species", store.species_fields(en)),
             "fluff": ["БГ"] * len(en["fluff"]),
             "traits": [{"desc": ["бг"] * len(t["desc"])} for t in en["traitDetails"]]}
    _write_species(overlay_dir, {"elf": entry})
    status, bg = _species("lang=bg")
    assert status == 200 and bg["textLang"] == "bg"
    assert bg["fluff"] == entry["fluff"]
    assert [t["name"] for t in bg["traitDetails"]] == [t["name"] for t in en["traitDetails"]]
    assert all(t["desc"][0] == "бг" for t in bg["traitDetails"])
    assert _species("lang=en")[1] == en  # English ignores the overlay


def test_species_route_stale_hash_falls_back(overlay_dir):
    _write_species(overlay_dir, {"elf": {"hash": "bad", "fluff": ["x"], "traits": []}})
    status, data = _species("lang=bg")
    assert status == 200 and data["textLang"] == "en" and data["fluff"] != ["x"]


def test_species_route_rejects_a_bad_lang():
    assert _species("lang=xx")[0] == 400
    assert _species("lang=xx", "nope")[0] == 400
