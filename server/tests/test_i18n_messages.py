"""I1: tagged messages (Msg), the plural filter, localize(), the empty catalog, and `?lang=` on the API."""
from __future__ import annotations

import copy
import json
import pickle

import pytest

from app import app
from i18n import catalog as catalog_pkg
from i18n import messages as m
from i18n.messages import Msg, localize, msg, parse_lang, render


@pytest.fixture()
def cat(monkeypatch):
    """A tiny catalog patched into the (otherwise empty) real one."""
    entries = {
        "t-level": {"en": "Level {level!r} for '{cls}' is out of range.", "bg": "Ниво {level!r} за '{cls}' е извън обхвата."},
        "t-count": {"en": "{n} spell{n||s} left.", "bg": "{n|Остава|Остават} {n} {n|заклинание|заклинания}."},
        "t-plural": {"en": "{n} {n|file|files}", "bg": "{n} {n|файл|файла}"},
        "t-nested": {"en": "{inner} is taken.", "bg": "{inner} е заето."},
        "t-name": {"en": "Dueling", "bg": "Дуел"},
        "t-en-only": {"en": "Only English {x}.", },
    }
    for key, entry in entries.items():
        monkeypatch.setitem(m.MESSAGES, key, entry)
    return entries


# --- Msg ---------------------------------------------------------------------------------------------------------

def test_msg_is_the_english_text_with_key_and_params(cat):
    x = msg("t-level", level="x", cls="fighter")
    assert isinstance(x, str) and isinstance(x, Msg)
    assert x == "Level 'x' for 'fighter' is out of range."
    assert x.key == "t-level" and x.params == {"level": "x", "cls": "fighter"}


def test_msg_keeps_string_behaviour(cat):
    x = msg("t-level", level=3, cls="wizard")
    assert x.startswith("Level 3") and "wizard" in x and x.endswith("range.")
    assert x == "Level 3 for 'wizard' is out of range." and hash(x) == hash("Level 3 for 'wizard' is out of range.")
    assert {"a": x} == {"a": "Level 3 for 'wizard' is out of range."}
    assert repr(x) == repr("Level 3 for 'wizard' is out of range.")
    assert type(str(x)) is str and type(f"{x}") is str


def test_msg_serializes_to_json_as_a_plain_string(cat):
    x = msg("t-level", level="x", cls="fighter")
    assert json.dumps({"message": x}) == json.dumps({"message": "Level 'x' for 'fighter' is out of range."})
    assert json.loads(json.dumps([x])) == [str(x)]
    assert json.dumps(x, ensure_ascii=False) == json.dumps(str(x), ensure_ascii=False)


def test_string_operations_drop_the_tag(cat):
    x = msg("t-name")
    for result in (x + "!", f"<{x}>", x.strip(), "".join([x]), "%s" % x, x[:3]):
        assert type(result) is str


def test_deepcopy_copy_and_pickle_keep_key_and_params(cat):
    x = msg("t-level", level=["a", {"b": 1}], cls="c")
    for y in (copy.deepcopy(x), copy.copy(x), pickle.loads(pickle.dumps(x)), pickle.loads(pickle.dumps(x, protocol=2))):
        assert isinstance(y, Msg) and y == x and y.key == "t-level" and y.params == x.params
    deep = copy.deepcopy(x)
    deep.params["level"][1]["b"] = 99
    assert x.params["level"][1]["b"] == 1  # params are deep-copied, not shared


def test_deepcopy_of_a_structure_holding_messages(cat):
    res = {"problems": [{"id": "a", "message": msg("t-name")}], "w": [[msg("t-name")]]}
    dup = copy.deepcopy(res)
    assert isinstance(dup["problems"][0]["message"], Msg) and isinstance(dup["w"][0][0], Msg)
    assert dup == res and dup["problems"][0]["message"] is not res["problems"][0]["message"]


def test_nesting_a_message_inside_a_message(cat):
    inner = msg("t-name")
    outer = msg("t-nested", inner=inner)
    assert outer == "Dueling is taken." and outer.params["inner"] is inner
    assert render(outer, "bg") == "Дуел е заето."
    assert render(outer, "en") == "Dueling is taken."
    assert copy.deepcopy(outer).params["inner"].key == "t-name"


def test_nested_messages_in_list_params(cat):
    outer = msg("t-nested", inner=[msg("t-name")])
    assert render(outer, "bg") == "['Дуел'] е заето."


def test_unknown_key_raises(cat):
    with pytest.raises(KeyError):
        msg("no-such-key")


def test_a_bare_msg_is_equal_to_its_text_and_not_to_other_text():
    a = Msg("Hello", "k", {})
    assert a == "Hello" and a != "Hallo" and Msg("Hello", "other") == a


# --- the plural filter -------------------------------------------------------------------------------------------

@pytest.mark.parametrize("n,en,bg", [(1, "1 file", "1 файл"), (0, "0 files", "0 файла"), (2, "2 files", "2 файла"),
                                      (21, "21 files", "21 файла"), (-1, "-1 files", "-1 файла")])
def test_plural_filter(cat, n, en, bg):
    x = msg("t-plural", n=n)
    assert x == en and render(x, "bg") == bg


def test_several_plural_fields_in_one_template(cat):
    one, many = msg("t-count", n=1), msg("t-count", n=3)
    assert one == "1 spell left." and many == "3 spells left."
    assert render(one, "bg") == "Остава 1 заклинание." and render(many, "bg") == "Остават 3 заклинания."


def test_plural_filter_functions():
    assert m.format_template("{n|one|many}", {"n": 1}) == "one"
    assert m.format_template("{n|one|many}", {"n": 5}) == "many"
    assert m.format_template("{n} {n|day|days}, {who!r}", {"n": 1, "who": "x"}) == "1 day, 'x'"
    assert m.format_template("{{literal}} {n|a|b}", {"n": 1}) == "{literal} a"
    with pytest.raises(ValueError):
        m.format_template("{n|only}", {"n": 1})
    with pytest.raises(ValueError):
        m.format_template("{n|a|b|c}", {"n": 1})
    with pytest.raises(KeyError):
        m.format_template("{n|a|b}", {})


def test_template_fields():
    assert m.template_fields("{a} {b!r} {n|x|y} {{no}}") == {"a", "b", "n"}


# --- render / localize ----------------------------------------------------------------------------------------------

def test_render_falls_back_to_english_without_a_template(cat):
    x = msg("t-en-only", x=1)
    assert render(x, "bg") == "Only English 1." and type(render(x, "bg")) is str
    orphan = Msg("Orphan text", "key-not-in-catalog", {})
    assert render(orphan, "bg") == "Orphan text"


def test_render_leaves_other_values_alone():
    assert render("plain", "bg") == "plain" and render(5, "bg") == 5 and render(None, "en") is None


def test_render_and_localize_reject_an_unknown_language():
    with pytest.raises(ValueError):
        render(Msg("x", "k"), "de")
    with pytest.raises(ValueError):
        localize({}, "de")


def _resolution(cat):
    return {
        "problems": [{"id": "a", "message": msg("t-level", level=7, cls="x")}],
        "warnings": [{"id": "b", "message": "plain text from an unconverted site"}],
        "choices": [{"id": "c", "options": [{"id": "o", "disabledReason": msg("t-name")}, {"id": "p"}]}],
        "pruned": [],
        "sheet": {"name": "Бил", "n": 3, "t": (1, 2), "tm": (msg("t-name"),)},
    }


def test_localize_en_returns_the_input_untouched(cat):
    res = _resolution(cat)
    out = localize(res, "en")
    assert out is res
    assert isinstance(out["problems"][0]["message"], Msg)  # still tagged


def test_localize_bg_renders_every_message_and_leaves_the_rest(cat):
    res = _resolution(cat)
    snapshot = copy.deepcopy(res)
    out = localize(res, "bg")
    assert out["problems"][0]["message"] == "Ниво 7 за 'x' е извън обхвата."
    assert out["choices"][0]["options"][0]["disabledReason"] == "Дуел"
    assert out["warnings"][0]["message"] == "plain text from an unconverted site"
    assert out["sheet"]["tm"] == ("Дуел",) and out["sheet"]["t"] == (1, 2) and out["sheet"]["name"] == "Бил"
    assert not any(isinstance(v, Msg) for v in _strings(out))
    assert res == snapshot and isinstance(res["problems"][0]["message"], Msg)  # the input is not modified


def _strings(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, (list, tuple)):
        for v in node:
            yield from _strings(v)
    else:
        yield node


def test_localize_shares_subtrees_without_messages(cat):
    res = _resolution(cat)
    out = localize(res, "bg")
    assert out["pruned"] is res["pruned"] and out["choices"][0]["options"][1] is res["choices"][0]["options"][1]
    assert out is not res and out["problems"] is not res["problems"]


def test_localize_without_any_message_returns_the_same_object():
    res = {"a": [1, {"b": "text"}], "c": ()}
    assert localize(res, "bg") is res


def test_localize_result_is_json_serializable(cat):
    json.dumps(localize(_resolution(cat), "bg"), ensure_ascii=False)


# --- lang parsing --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [(None, "en"), ("en", "en"), ("bg", "bg")])
def test_parse_lang_accepts(raw, expected):
    assert parse_lang(raw) == expected


@pytest.mark.parametrize("raw", ["", "EN", "Bg", "de", "bg,en", " bg", "en-US"])
def test_parse_lang_rejects(raw):
    with pytest.raises(ValueError):
        parse_lang(raw)


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


EMPTY = {"name": "Бил", "ruleset": "mixed"}


@pytest.mark.parametrize("query", ["", "?lang=en", "?lang=bg"])
def test_resolve_accepts_lang_and_returns_the_same_english_today(client, query):
    plain = client.post("/api/resolve", json=EMPTY).get_json()
    r = client.post("/api/resolve" + query, json=EMPTY)
    assert r.status_code == 200 and r.get_json() == plain


@pytest.mark.parametrize("query", ["?lang=de", "?lang=", "?lang=EN", "?lang=xx"])
def test_resolve_rejects_other_languages(client, query):
    r = client.post("/api/resolve" + query, json=EMPTY)
    assert r.status_code == 400 and r.get_json() == {"error": "'lang' must be 'bg' or 'en'"}


@pytest.mark.parametrize("fmt", ["yaml", "markdown", "pdf"])
def test_export_rejects_other_languages_and_accepts_the_two(client, fmt):
    bad = client.post(f"/api/export/{fmt}?lang=fr", json=EMPTY)
    assert bad.status_code == 400 and bad.get_json() == {"error": "'lang' must be 'bg' or 'en'"}
    for lang in ("", "?lang=en", "?lang=bg"):
        r = client.post(f"/api/export/{fmt}{lang}", json=EMPTY)
        assert r.status_code == 400 and list(r.get_json()) == ["problems"]  # the gate answers, not the lang check


def test_unknown_export_format_is_still_404_with_a_bad_lang(client):
    assert client.post("/api/export/docx?lang=fr", json={}).status_code == 404


def test_export_problems_body_is_localized(client, monkeypatch, cat):
    monkeypatch.setattr("app.resolve", lambda draft, catalog: {
        "problems": [{"id": "x", "message": msg("t-name")}], "choices": [], "sheet": {"classes": [1], "species": 1, "background": 1}})
    en = client.post("/api/export/yaml?lang=en", json=EMPTY).get_json()
    bg = client.post("/api/export/yaml?lang=bg", json=EMPTY).get_json()
    assert en == {"problems": [{"id": "x", "message": "Dueling"}]}
    assert bg == {"problems": [{"id": "x", "message": "Дуел"}]}


def test_resolve_response_is_localized(client, monkeypatch, cat):
    monkeypatch.setattr("app.resolve", lambda draft, catalog: {"problems": [{"id": "x", "message": msg("t-name")}]})
    assert client.post("/api/resolve", json=EMPTY).get_json() == {"problems": [{"id": "x", "message": "Dueling"}]}
    assert client.post("/api/resolve?lang=bg", json=EMPTY).get_json() == {"problems": [{"id": "x", "message": "Дуел"}]}


def test_error_bodies_stay_english_whatever_the_language(client):
    r = client.post("/api/resolve?lang=bg", json=[1])
    assert r.status_code == 400 and r.get_json() == {"error": "draft must be a JSON object"}


# --- the catalog package ----------------------------------------------------------------------------------------------

def test_catalog_is_wired_to_the_modules():
    """I2 filled problems and warnings, I3 pruned, I4 disabled; labels stay empty until I5."""
    assert catalog_pkg.MESSAGES is m.MESSAGES
    assert (catalog_pkg.problems.MESSAGES and catalog_pkg.warnings.MESSAGES and catalog_pkg.pruned.MESSAGES
            and catalog_pkg.disabled.MESSAGES)
    assert catalog_pkg.labels.MESSAGES == {}
    assert m.MESSAGES == {**catalog_pkg.problems.MESSAGES, **catalog_pkg.warnings.MESSAGES, **catalog_pkg.pruned.MESSAGES,
                          **catalog_pkg.disabled.MESSAGES}


def test_catalog_modules_merge_and_reject_duplicates(monkeypatch):
    real = catalog_pkg.build()
    monkeypatch.setitem(catalog_pkg.problems.MESSAGES, "dup", {"en": "a"})
    monkeypatch.setitem(catalog_pkg.pruned.MESSAGES, "other", {"en": "o"})
    assert catalog_pkg.build() == {**real, "dup": {"en": "a"}, "other": {"en": "o"}}
    monkeypatch.setitem(catalog_pkg.warnings.MESSAGES, "dup", {"en": "b"})
    with pytest.raises(ValueError, match="duplicate message keys"):
        catalog_pkg.build()


def test_validate_catalog():
    ok = {"a": {"en": "x {n|a|b}", "bg": "ю {n|а|б}"}}
    assert m.validate_catalog(ok, require_bg=True) == []
    assert m.validate_catalog({"a": {"en": "x"}}) == []
    assert "no Bulgarian" in m.validate_catalog({"a": {"en": "x"}}, require_bg=True)[0]
    assert "no English" in m.validate_catalog({"a": {"bg": "x"}})[0]
    assert "placeholder mismatch" in m.validate_catalog({"a": {"en": "{x}", "bg": "{y}"}})[0]
    assert "does not format" in m.validate_catalog({"a": {"en": "{n|one}"}})[0]
