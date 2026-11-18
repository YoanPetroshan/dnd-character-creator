"""Overlay kind `choice-texts`: Bulgarian texts for option / card descriptions, keyed by the sha1 of the English text
(store.localize_content, applied after `localize` in /api/resolve and the exports), and the translators' tool for it.
Every test uses a tmp overlay dir, never the real server/data/i18n files."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

import service
from i18n.content import store, tool

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import i18n_zoo  # noqa: E402


@pytest.fixture
def overlay_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "I18N_DIR", tmp_path)
    store.load_overlay.cache_clear()
    (tmp_path / "bg").mkdir()
    yield tmp_path
    store.load_overlay.cache_clear()


def write(overlay_dir, data):
    (overlay_dir / "bg" / "choice-texts.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    store.load_overlay.cache_clear()


def post(lang):
    query = {} if lang is None else {"lang": lang}
    status, _ct, _h, body = service.handle("POST", "/api/resolve", query, json.dumps(i18n_zoo.base()))
    assert status == 200
    return body


def described(body: bytes):
    """(card ids with a data description, option ids with one) of a resolve body."""
    out = json.loads(body)
    return out["choices"]


def first_text(body: bytes):
    for choice in json.loads(body)["choices"]:
        for option in choice.get("options") or []:
            if isinstance(option.get("description"), str) and option["description"]:
                return choice["id"], option["id"], option["description"]
    pytest.fail("the base draft has no option with a description")


def test_english_payload_is_byte_identical_with_or_without_an_overlay(overlay_dir):
    without = post(None)
    _cid, _oid, text = first_text(without)
    write(overlay_dir, {store.text_hash(text): {"ref": "x", "en": text, "bg": "Превод."}})
    assert post(None) == without
    assert post("en") == without


def test_bg_replaces_a_known_text_and_keeps_unknown_ones(overlay_dir):
    english = post("bg")
    cid, oid, text = first_text(english)
    write(overlay_dir, {store.text_hash(text): {"ref": oid, "en": text, "bg": "Превод на текста."}})
    out = post("bg")
    assert out != english
    before = {c["id"]: c for c in json.loads(english)["choices"]}
    after = {c["id"]: c for c in json.loads(out)["choices"]}
    changed = 0
    for cid_, card in after.items():
        assert {k: v for k, v in card.items() if k != "options"} == {k: v for k, v in before[cid_].items() if k != "options"}
        for a, b in zip(card.get("options") or [], before[cid_].get("options") or []):
            if a != b:
                changed += 1
                assert b["description"] == text and a["description"] == "Превод на текста."
                assert {k: v for k, v in a.items() if k != "description"} == {k: v for k, v in b.items() if k != "description"}
    assert changed >= 1


def test_an_unknown_or_stale_hash_falls_back_to_english(overlay_dir):
    english = post("bg")
    _cid, _oid, text = first_text(english)
    write(overlay_dir, {"0" * 40: {"ref": "x", "en": "gone", "bg": "Изчезнал."}, store.text_hash(text + "!"): {"ref": "x", "en": text + "!", "bg": "Остарял."}})
    assert post("bg") == english
    write(overlay_dir, {store.text_hash(text): {"ref": "x", "en": text, "bg": "  "}})  # an empty translation is ignored
    assert post("bg") == english


def test_localize_content_unit(overlay_dir):
    res = {"sheet": {}, "choices": [{"id": "c", "description": "Card text.", "options": [{"id": "o", "description": "Opt text."}, {"id": "p"}]},
                                      {"id": "d", "description": None, "options": []}]}
    assert store.localize_content(res, "en") is res
    assert store.localize_content(res, "bg") is res  # no overlay: the input itself
    write(overlay_dir, {store.text_hash("Card text."): {"ref": "c", "en": "Card text.", "bg": "Карта."},
                        store.text_hash("Opt text."): {"ref": "o", "en": "Opt text.", "bg": "Опция."}})
    out = store.localize_content(res, "bg")
    assert out["choices"][0]["description"] == "Карта." and out["choices"][0]["options"][0]["description"] == "Опция."
    assert out["choices"][0]["options"][1] == {"id": "p"} and out["choices"][1] is res["choices"][1]
    assert res["choices"][0]["description"] == "Card text."  # the input is not modified


# --- the tool --------------------------------------------------------------------------------------------------------

TEXT = "You gain a +2 bonus to damage rolls (1d6 extra)."
RECORDS = {store.text_hash(TEXT): {"name": "opt-x", "source": "SRD", "text": TEXT}}


def test_harvest_collects_distinct_data_strings():
    catalog = service._catalog
    found = tool.harvest_choice_texts(catalog, drafts={"a": i18n_zoo.base(), "b": i18n_zoo.base()})
    assert found and all(k == store.text_hash(v["text"]) for k, v in found.items())
    assert len({v["text"] for v in found.values()}) == len(found)
    assert all(isinstance(v["text"], str) and v["name"] for v in found.values())
    if any(str(i).startswith("opt-") and i in catalog.features and catalog.features[i].get("desc") for i in catalog.features):
        assert any(v["name"].startswith("opt-") for v in found.values())  # the catalog opt-* sweep (official data only)


def test_export_shape_and_apply_status(overlay_dir):
    h = store.text_hash(TEXT)
    out = tool.export_records(RECORDS, {}, kind="choice-texts")
    assert out == [{"id": h, "name": "opt-x", "source": "SRD", "hash": h, "desc": [TEXT]}]
    bg = {"id": h, "hash": h, "desc": ["Получаваш +2 бонус към щетите (1d6 допълнително)."]}
    merged, results = tool.apply_records(RECORDS, {}, [bg], "choice-texts")
    assert results == [(h, [])]
    assert merged == {h: {"ref": "opt-x", "en": TEXT, "bg": bg["desc"][0]}}
    assert tool.export_records(RECORDS, merged, only_missing=True, kind="choice-texts") == []
    counts = tool.status_counts(RECORDS, merged, "choice-texts")
    assert counts["SRD"]["translated"] == 1
    assert tool.status_counts(RECORDS, {"0" * 40: {"bg": "x"}}, "choice-texts")["(unused)"]["stale"] == 1


def test_validator_rules():
    english = store.fields_for("choice-texts", RECORDS[store.text_hash(TEXT)])
    h = store.text_hash(TEXT)
    v = lambda desc, **over: tool.validate(english, {"id": h, "hash": h, "desc": desc, **over}, "choice-texts")
    assert v(["Получаваш +2 бонус към щетите (1d6 допълнително)."]) == []
    assert v(["Получаваш +2 бонус.", "Към щетите (1d6)."]) == []  # no paragraph-count check
    assert v([]) and v([""])
    assert v(["Получаваш +2 бонус към щетите (1d8 допълнително)."])  # dice
    assert v(["Получаваш бонус към щетите (1d6 допълнително)."])  # number 2 missing
    assert v(["You gain a +2 bonus to damage rolls (1d6 extra)."])  # no Cyrillic
    assert v(["Получаваш +2 бонус към щетите (1d6)."], hash="0" * 40)  # stale hash
