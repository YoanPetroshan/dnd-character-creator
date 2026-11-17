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
    assert "server/i18n/content/spells.py" not in pack
    assert not any(f.endswith("README.md") and "data/i18n" in f for f in pack)


def test_the_store_finds_the_overlay_where_the_pack_puts_it():
    assert store.I18N_DIR == ROOT / "server" / "data" / "i18n"
