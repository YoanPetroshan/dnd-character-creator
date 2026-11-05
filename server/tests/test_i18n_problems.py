"""I2: problems and warnings are tagged messages (`msg("<key>", **params>)`) with English and Bulgarian templates.

Checks: catalog completeness (code <-> catalog), en/bg placeholder parity, call-site parameters match the template, an AST
guard against new plain-text `"message"` dicts, tag-loss and Bulgarian coverage over the message zoo, the engine's own
comparisons on messages, and `?lang=bg` end to end through the Flask client. The English text itself is pinned by the
frozen snapshot (test_i18n_snapshot.py) and the existing English assertions.
"""
from __future__ import annotations

import ast
import glob
import pathlib
import re

import pytest

import i18n_zoo as zoo
from app import app
from i18n import catalog as catalog_pkg
from i18n import messages as m
from i18n.messages import Msg, localize, msg, render, template_fields

SERVER = pathlib.Path(__file__).resolve().parent.parent
ENGINE_FILES = sorted(glob.glob(str(SERVER / "engine" / "*.py"))) + [str(SERVER / "app.py")]
SERVER_FILES = ENGINE_FILES + [str(SERVER / n) for n in ("export.py", "export_fields.py", "markdown_export.py", "pdf_export.py")]
CODE_KEYS_MODULES = (catalog_pkg.problems, catalog_pkg.warnings)
I2_KEYS = {k for mod in CODE_KEYS_MODULES for k in mod.MESSAGES}


def _trees():
    for path in SERVER_FILES:
        yield path, ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))


def _msg_calls():
    """(file, line, key, keyword names, has ** splat) for every `msg("<key>", ...)` call in the server code."""
    out = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "msg"
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                kws = {k.arg for k in node.keywords if k.arg}
                out.append((pathlib.Path(path).name, node.lineno, node.args[0].value, kws, any(k.arg is None for k in node.keywords)))
    return out


# --- catalog completeness and parity -----------------------------------------------------------------------------

def test_every_msg_key_used_in_code_is_in_the_catalog_with_en_and_bg():
    missing = []
    for file, line, key, _kws, _splat in _msg_calls():
        entry = m.MESSAGES.get(key)
        if not entry or not entry.get("en") or not entry.get("bg"):
            missing.append(f"{file}:{line} {key}")
    assert not missing, missing


def test_every_problem_and_warning_catalog_key_is_used_in_code():
    used = {key for _f, _l, key, _k, _s in _msg_calls()}
    assert not sorted(I2_KEYS - used), f"catalog keys no code uses: {sorted(I2_KEYS - used)}"


def test_no_msg_call_uses_a_non_literal_key():
    """Completeness is an AST scan, so every key must be a string literal."""
    bad = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "msg"
                    and not (node.args and isinstance(node.args[0], ast.Constant))):
                bad.append(f"{pathlib.Path(path).name}:{node.lineno}")
    assert not bad, bad


def test_problem_and_warning_templates_have_bulgarian_with_the_same_placeholders():
    only = {k: v for k, v in m.MESSAGES.items() if k in I2_KEYS}
    assert len(only) >= 70
    assert m.validate_catalog(only, require_bg=True) == []


def test_bulgarian_templates_are_bulgarian_text():
    plain = [k for k in sorted(I2_KEYS) if not re.search("[А-Яа-я]", m.MESSAGES[k]["bg"])]
    assert not plain, f"Bulgarian templates without any Cyrillic: {plain}"


def test_english_templates_have_no_cyrillic():
    assert not [k for k in I2_KEYS if re.search("[А-Яа-я]", m.MESSAGES[k]["en"])]


def test_call_site_parameters_match_the_template_fields():
    """`msg("key", a=1, b=2)` must pass exactly the fields the English template uses (a ** splat may supply the rest)."""
    wrong = []
    for file, line, key, kws, splat in _msg_calls():
        fields = template_fields(m.MESSAGES[key]["en"])
        if (kws - fields) or (not splat and fields != kws):
            wrong.append(f"{file}:{line} {key}: passes {sorted(kws)}, template uses {sorted(fields)}")
    assert not wrong, wrong


@pytest.mark.parametrize("key", sorted(I2_KEYS))
def test_every_template_renders_in_both_languages_with_sample_params(key):
    fields = template_fields(m.MESSAGES[key]["en"])
    for n in (1, 2, 5):
        params = {f: n for f in fields}
        made = msg(key, **params)
        assert isinstance(made, Msg) and made.key == key
        bg = render(made, "bg")
        assert isinstance(bg, str) and bg


# --- AST guard: no plain-text "message" ----------------------------------------------------------------------------

def _plain_message_sites(tree) -> list[int]:
    """Lines of a dict literal `"message": <str / f-string / concatenation>` or an augmented assignment to a message."""
    plain = (ast.Constant, ast.JoinedStr, ast.BinOp)
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "message" and isinstance(v, plain):
                    bad.append(v.lineno)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Subscript):
            sl = node.target.slice
            if isinstance(sl, ast.Constant) and sl.value == "message":
                bad.append(node.lineno)
    return bad


def test_no_plain_text_message_dict_in_the_engine_or_the_app():
    found = {pathlib.Path(p).name: _plain_message_sites(t) for p, t in _trees()}
    found = {k: v for k, v in found.items() if v}
    assert not found, f'use msg("<key>", ...) for "message" values; plain text at {found}'


def test_the_ast_guard_catches_what_it_should():
    bad = ast.parse('x = {"id": "a", "message": f"hi {n}"}\ny = {"message": "hi"}\nz = {"message": "a" + b}\n'
                    'p["message"] += "x"\nok = {"message": msg("k")}\nok2 = {"message": text}')
    assert sorted(_plain_message_sites(bad)) == [1, 2, 3, 4]


# --- the engine's own comparisons keep working -----------------------------------------------------------------------

def test_the_out_of_range_final_rebuild_keeps_tag_text_and_the_old_check():
    d = zoo.base()
    d["abilities"]["base"]["STR"] = 40
    r = zoo.resolve(d, zoo.load())
    (p,) = [p for p in r["problems"] if p["id"] == "ability-out-of-range-STR"]
    assert isinstance(p["message"], Msg)
    # the clamped base plus the Fighter's bonuses still leaves STR at 31: the engine rebuilds the message, tagged
    assert p["message"].key == "ability-out-of-range-clamped-final"
    assert p["message"] == ("STR score 40 is out of the 1-30 range; using 30 instead. "
                            "With the species, background and feat bonuses the final STR score is 31, still outside 1-30.")
    assert "final" in p["message"]
    d["abilities"]["base"]["STR"] = 30
    d["abilities"]["base"]["DEX"] = 0
    (q,) = [x for x in zoo.resolve(d, zoo.load())["problems"] if x["id"] == "ability-out-of-range-DEX"]
    assert q["message"].key == "ability-out-of-range-clamped" and "final" not in q["message"]
    final = msg("ability-out-of-range-clamped-final", ab="STR", n=40, clamped=30, final=31)
    assert final == ("STR score 40 is out of the 1-30 range; using 30 instead. "
                     "With the species, background and feat bonuses the final STR score is 31, still outside 1-30.")
    assert "final" in final and "final" not in msg("ability-out-of-range-clamped", ab="STR", n=40, clamped=30)
    assert "31" in render(final, "bg") and re.search("[А-Яа-я]", render(final, "bg"))


def test_normalize_messages_are_tagged_and_equal_their_english():
    from engine.normalize import normalize_draft
    _clean, problems = normalize_draft({"name": 5, "sources": "x", "abilities": {"base": {"STR": "x", "DEX": 99}}})
    assert [p["id"] for p in problems] == ["malformed-name", "malformed-sources", "ability-invalid-STR", "ability-out-of-range-DEX"]
    assert all(isinstance(p["message"], Msg) for p in problems)
    assert problems[2]["message"] == "STR score 'x' isn't a valid whole number; using 10 instead."
    assert problems[2]["message"].params == {"ab": "STR", "value": "x"}


# --- tag loss and Bulgarian coverage over the zoo ------------------------------------------------------------------------

pytestmark_data = pytest.mark.skipif(bool(zoo.NEEDS_DATA), reason=f"5etools data missing: {', '.join(zoo.NEEDS_DATA)}")
CHUNKS = 8


@pytest.fixture(scope="module")
def catalog():
    return zoo.load()


@pytest.fixture(scope="module")
def cases(catalog):
    return zoo.zoo(catalog)


def _messages(resolution):
    """(where, id, message) for every problem / warning message of a resolution and its export gate."""
    import app as app_module
    for key in ("problems", "warnings"):
        for p in resolution.get(key) or []:
            yield key, p["id"], p["message"]
    for p in app_module._pending_export_problems(resolution):
        yield "exportGate", p["id"], p["message"]


def _resolve_chunk(chunk, cases, catalog):
    import copy
    for name in sorted(cases)[chunk::CHUNKS]:
        yield name, zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))


@pytestmark_data
@pytest.mark.parametrize("chunk", range(CHUNKS))
def test_every_problem_and_warning_in_the_zoo_is_a_tagged_message(chunk, cases, catalog):
    plain = []
    for name, res in _resolve_chunk(chunk, cases, catalog):
        plain += [f"{name}: {where} {pid}: {text!r}" for where, pid, text in _messages(res) if not isinstance(text, Msg)]
    assert not plain, f"tag loss (a plain str where a Msg is expected): {plain[:5]}"


@pytestmark_data
@pytest.mark.parametrize("chunk", range(CHUNKS))
def test_every_problem_and_warning_in_the_zoo_localizes_to_bulgarian(chunk, cases, catalog):
    stayed, bad = [], []
    for name, res in _resolve_chunk(chunk, cases, catalog):
        bg = localize({"problems": res["problems"], "warnings": res["warnings"]}, "bg")
        for key in ("problems", "warnings"):
            for before, after in zip(res[key], bg[key]):
                en, text = str(before["message"]), after["message"]
                if not isinstance(before["message"], Msg):
                    continue  # reported by the tag-loss test
                if type(text) is not str or text == en:
                    stayed.append(f"{name}: {before['id']}: {en}")
                if not re.search("[А-Яа-я]", text):
                    bad.append(f"{name}: {before['id']}: {text}")
        for p in _messages_gate(res):
            if render(p["message"], "bg") == str(p["message"]):
                stayed.append(f"{name}: gate {p['id']}")
    assert not stayed and not bad, f"English left after localize(bg): {stayed[:5]} {bad[:5]}"


def _messages_gate(res):
    import app as app_module
    return app_module._pending_export_problems(res)


# --- ?lang=bg end to end -----------------------------------------------------------------------------------------------

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _messy_draft() -> dict:
    d = zoo.base(ruleset="2024")
    d["abilities"]["base"].update({"STR": 99, "DEX": "x"})
    d["equipment"]["added"] = [{"itemId": "shield", "qty": 1}]
    d["equipment"]["wielded"] = {"main": "shield"}
    d["classes"].append({"classId": "nope", "level": 3})
    return d


def _without_reasons(resolution: dict) -> dict:
    """The resolution without its engine-localized card texts (disabledReason since I4, label / description / unavailableReason since I5)."""
    return zoo.without_localized(resolution)


def test_resolve_lang_bg_returns_bulgarian_problems_and_warnings(client):
    draft = _messy_draft()
    en = client.post("/api/resolve", json=draft).get_json()
    bg = client.post("/api/resolve?lang=bg", json=draft).get_json()
    assert client.post("/api/resolve?lang=en", json=draft).get_json() == en
    by_id = {p["id"]: p["message"] for p in bg["problems"] + bg["warnings"]}
    en_by_id = {p["id"]: p["message"] for p in en["problems"] + en["warnings"]}
    assert set(by_id) == set(en_by_id)
    assert en_by_id["unknown-class"] == "Unknown class 'nope'."
    assert by_id["unknown-class"] == "Непознат клас 'nope'."
    assert en_by_id["ability-invalid-DEX"] == "DEX score 'x' isn't a valid whole number; using 10 instead."
    assert by_id["ability-invalid-DEX"] == "Стойността 'x' на DEX не е валидно цяло число; вместо нея се използва 10."
    assert by_id["wielded-main-shield"] != en_by_id["wielded-main-shield"] and "щит" in by_id["wielded-main-shield"]
    assert all(re.search("[А-Яа-я]", t) for t in by_id.values()), by_id
    # everything that is not an engine message is identical in both languages
    # (the cards' texts are localized since I4 / I5, so the cards are compared without them)
    assert {k: v for k, v in _without_reasons(bg).items() if k not in ("problems", "warnings")} == {
        k: v for k, v in _without_reasons(en).items() if k not in ("problems", "warnings")}


def test_export_gate_body_is_bulgarian_with_lang_bg(client):
    body = {"name": "x", "ruleset": "mixed"}
    en = client.post("/api/export/yaml", json=body)
    bg = client.post("/api/export/yaml?lang=bg", json=body)
    assert en.status_code == bg.status_code == 400
    assert [p["message"] for p in en.get_json()["problems"]] == [
        "Choose a class first.", "Choose a species first.", "Choose a background first."]
    assert [p["message"] for p in bg.get_json()["problems"]] == [
        "Първо изберете клас.", "Първо изберете раса.", "Първо изберете произход."]
    assert [p["id"] for p in bg.get_json()["problems"]] == [p["id"] for p in en.get_json()["problems"]]


def test_unresolved_choice_gate_message_is_localized(client):
    d = zoo.base()
    res = client.post("/api/export/yaml?lang=bg", json=d)
    if res.status_code == 400:
        texts = [p["message"] for p in res.get_json()["problems"] if p["id"].startswith("unresolved-choice-")]
        assert texts and all("още не е избрано докрай" in t for t in texts)
