"""I3: the `reason` of every `pruned` entry is a tagged message (`msg("pruned-...", **params)`) with English and Bulgarian
templates.

Same checks as I2 (test_i18n_problems.py): catalog completeness both ways, en/bg placeholder parity, call-site parameters
equal the template fields, an AST guard against plain-text reasons, tag loss and Bulgarian coverage over the message zoo,
and `?lang=bg` end to end through the Flask client. The English text is pinned by the frozen snapshot
(test_i18n_snapshot.py) and the existing English assertions.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

import i18n_zoo as zoo
from app import app
from i18n import catalog as catalog_pkg
from i18n import messages as m
from i18n.messages import Msg, localize, msg, render, template_fields

PRUNED_KEYS = set(catalog_pkg.pruned.MESSAGES)


def sample_params(template: str) -> dict:
    return {f: ([2] if f in m.list_fields(template) else 2) for f in template_fields(template)}


# --- catalog completeness and parity -----------------------------------------------------------------------------

def test_every_pruned_key_used_in_code_is_in_the_catalog_with_en_and_bg():
    used = [(f, l, k) for f, l, k, _kw, _s in zoo.msg_calls() if k.startswith("pruned-")]
    assert len(used) >= 37
    bad = [f"{f}:{l} {k}" for f, l, k in used if k not in PRUNED_KEYS or not m.MESSAGES[k].get("bg")]
    assert not bad, bad


def test_every_pruned_catalog_key_is_used_in_code():
    used = {k for _f, _l, k, _kw, _s in zoo.msg_calls()}
    assert not sorted(PRUNED_KEYS - used), f"catalog keys no code uses: {sorted(PRUNED_KEYS - used)}"


def test_pruned_catalog_keys_are_named_pruned():
    assert all(k.startswith("pruned-") for k in PRUNED_KEYS) and len(PRUNED_KEYS) >= 35


def test_pruned_templates_have_bulgarian_with_the_same_placeholders():
    assert m.validate_catalog({k: m.MESSAGES[k] for k in PRUNED_KEYS}, require_bg=True) == []


def test_bulgarian_pruned_templates_are_bulgarian_and_english_ones_are_not():
    assert not [k for k in PRUNED_KEYS if not re.search("[А-Яа-я]", m.MESSAGES[k]["bg"])]
    assert not [k for k in PRUNED_KEYS if re.search("[А-Яа-я]", m.MESSAGES[k]["en"])]


def test_call_site_parameters_match_the_template_fields():
    wrong = []
    for file, line, key, kws, splat in zoo.msg_calls():
        if key not in PRUNED_KEYS:
            continue
        fields = template_fields(m.MESSAGES[key]["en"])
        if (kws - fields) or (not splat and fields != kws):
            wrong.append(f"{file}:{line} {key}: passes {sorted(kws)}, template uses {sorted(fields)}")
    assert not wrong, wrong


@pytest.mark.parametrize("key", sorted(PRUNED_KEYS))
def test_every_pruned_template_renders_in_both_languages(key):
    template = m.MESSAGES[key]["en"]
    for n in (1, 2, 5):
        params = {f: ([n, n + 1] if f in m.list_fields(template) else n) for f in template_fields(template)}
        made = msg(key, **params)
        assert isinstance(made, Msg) and made.key == key
        bg = render(made, "bg")
        assert isinstance(bg, str) and bg and re.search("[А-Яа-я]", bg)
        assert "{" not in bg and "}" not in bg


def test_list_params_join_with_the_separator_and_render_nested_messages():
    made = msg("pruned-proficient", label="Skills", names=["Arcana", "History"])
    assert made == "'Skills': Arcana, History is already proficient; the selection was ignored."
    assert render(made, "bg") == "'Skills': вече се владее Arcana, History; изборът беше пренебрегнат."
    one = msg("pruned-ability-closed", label="X", items=[msg("pruned-ability-closed-item", ab="STR", why="already at maximum (20)")])
    assert one == "'X': STR is already at maximum (20) and was ignored."
    assert render(one, "bg") == "'X': STR е already at maximum (20); изборът беше пренебрегнат."
    assert render(msg("pruned-more", extra=1), "bg") == "...и още 1 остарял избор е пренебрегнат."
    assert render(msg("pruned-more", extra=3), "bg") == "...и още 3 остарели избора са пренебрегнати."


# --- AST guard: no plain-text pruned reason ------------------------------------------------------------------------------

PLAIN = (ast.Constant, ast.JoinedStr, ast.BinOp)


def _is_plain(v) -> bool:
    return isinstance(v, (ast.JoinedStr, ast.BinOp)) or (isinstance(v, ast.Constant) and isinstance(v.value, str))


def plain_reason_sites(tree, dict_keys=("reason",), names=("reason",)) -> list[int]:
    """Lines where a `"reason"` dict value is built as plain text (a str literal, an f-string, a concatenation), and, in
    a function that builds such dicts, where the variable `reason` is assigned plain text or augmented (`reason += ...`
    would drop the tag). The `reason` variables of the disabledReason helpers are checked by test_i18n_disabled.py."""
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value in dict_keys and _is_plain(v):
                    bad.append(v.lineno)
    for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        builds = any(isinstance(d, ast.Dict) and any(isinstance(k, ast.Constant) and k.value in dict_keys for k in d.keys)
                     for d in ast.walk(fn))
        if not builds:
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets) and _is_plain(node.value):
                bad.append(node.lineno)
            elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
                bad.append(node.lineno)
    return sorted(set(bad))


def test_no_plain_text_pruned_reason_in_the_engine():
    found = {pathlib.Path(p).name: plain_reason_sites(t) for p, t in zoo.server_trees()}
    found = {k: v for k, v in found.items() if v}
    assert not found, f'use msg("pruned-...", ...) for pruned "reason" values; plain text at {found}'


def test_the_ast_guard_catches_what_it_should():
    bad = ast.parse('def f():\n    x = {"choiceId": c, "reason": f"hi {n}"}\n    y = {"reason": "hi"}\n    z = {"reason": "a" + b}\n'
                    '    reason = "plain"\n    reason += msg("k")\n    reason = f"x"\n    ok = {"reason": msg("k")}\n'
                    '    ok2 = {"reason": r}\n    reason = None\n    reason = msg("k")\n'
                    'def g():\n    reason = "not a pruned builder"\n')
    assert plain_reason_sites(bad) == [2, 3, 4, 5, 6, 7]


# --- tag loss and Bulgarian coverage over the zoo ------------------------------------------------------------------------

pytestmark_data = pytest.mark.skipif(bool(zoo.NEEDS_DATA), reason=f"5etools data missing: {', '.join(zoo.NEEDS_DATA)}")
CHUNKS = 8


@pytest.fixture(scope="module")
def catalog():
    return zoo.load()


@pytest.fixture(scope="module")
def cases(catalog):
    return zoo.zoo(catalog)


def _resolve_chunk(chunk, cases, catalog):
    import copy
    for name in sorted(cases)[chunk::CHUNKS]:
        yield name, zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))


@pytestmark_data
@pytest.mark.parametrize("chunk", range(CHUNKS))
def test_every_pruned_reason_in_the_zoo_is_a_tagged_message_and_localizes_to_bulgarian(chunk, cases, catalog):
    plain, stayed = [], []
    for name, res in _resolve_chunk(chunk, cases, catalog):
        bg = localize({"pruned": res["pruned"]}, "bg")["pruned"]
        for before, after in zip(res["pruned"], bg):
            reason = before["reason"]
            if not isinstance(reason, Msg):
                plain.append(f"{name}: {before['choiceId']}: {reason!r}")
            elif type(after["reason"]) is not str or after["reason"] == str(reason) or not re.search("[А-Яа-я]", after["reason"]):
                stayed.append(f"{name}: {reason.key}: {reason}")
    assert not plain, f"tag loss (a plain str where a Msg is expected): {plain[:5]}"
    assert not stayed, f"English left after localize(bg): {stayed[:5]}"


@pytestmark_data
def test_the_zoo_reaches_most_pruned_shapes(cases, catalog):
    import copy
    keys = set()
    for name in sorted(cases):
        res = zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))
        keys |= {p["reason"].key for p in res["pruned"] if isinstance(p["reason"], Msg)}
    assert len(keys) >= 12, sorted(keys)
    # the rest are exercised by the engine tests (every key but one is built somewhere in the suite) and by the render test


# --- ?lang=bg end to end ---------------------------------------------------------------------------------------------------

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _stale_draft() -> dict:
    d = zoo.base(ruleset="2024")
    d["classes"][0].update(level=2, subclassId="champion", choices={"class:fighter:bogus": ["x"]})
    d["equipment"]["worn"] = {"armor": "chain-mail"}
    return d


@pytestmark_data
def test_resolve_lang_bg_returns_bulgarian_pruned_reasons(client):
    draft = _stale_draft()
    en = client.post("/api/resolve", json=draft).get_json()
    bg = client.post("/api/resolve?lang=bg", json=draft).get_json()
    assert client.post("/api/resolve?lang=en", json=draft).get_json() == en
    en_by_id = {p["choiceId"]: p["reason"] for p in en["pruned"]}
    bg_by_id = {p["choiceId"]: p["reason"] for p in bg["pruned"]}
    assert set(en_by_id) == set(bg_by_id) == {"class:fighter:subclass", "class:fighter:bogus", "equipment:worn:armor"}
    assert en_by_id["class:fighter:subclass"] == "'Champion' unlocks at fighter level 3 and was ignored."
    assert bg_by_id["class:fighter:subclass"] == "'Champion' се отключва на ниво 3 на fighter и беше пренебрегнат."
    assert en_by_id["class:fighter:bogus"] == "'class:fighter:bogus' no longer applies to the current character and was ignored."
    assert bg_by_id["class:fighter:bogus"] == "'class:fighter:bogus' вече не се прилага към текущия герой и беше пренебрегнат."
    assert en_by_id["equipment:worn:armor"] == "Chain Mail is no longer in the inventory and was removed from the worn armor slot."
    assert bg_by_id["equipment:worn:armor"] == "Chain Mail вече не е в инвентара и беше премахнат от мястото (носен: броня)."
    assert {k: v for k, v in bg.items() if k not in ("problems", "warnings", "pruned")} == {
        k: v for k, v in en.items() if k not in ("problems", "warnings", "pruned")}
