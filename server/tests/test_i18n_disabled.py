"""I4: an option's `disabledReason` is a tagged message (`msg("disabled-...", **params)`) with English and Bulgarian templates.

Same checks as I2/I3: catalog completeness both ways, en/bg placeholder parity, call-site parameters equal the template
fields, an AST guard against plain-text reasons, tag loss and Bulgarian coverage over the message zoo, `?lang=bg` end to
end through the Flask client. Plus the engine's own comparison on a reason: `startswith("already taken")` decides between a
`feat-duplicate-*` and a `feat-prerequisite-unmet-*` problem for a stored species/background feat pick.
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

import i18n_zoo as zoo
from app import app
from engine import resolve as resolve_mod
from i18n import catalog as catalog_pkg
from i18n import messages as m
from i18n.messages import Msg, localize, msg, render, template_fields

DISABLED_KEYS = set(catalog_pkg.disabled.MESSAGES)
# pieces of a reason (nested messages) and the prerequisite wording; everything else is a whole reason
NESTED_KEYS = {k for k in DISABLED_KEYS if k.startswith("prereq-")}


# --- catalog completeness and parity -----------------------------------------------------------------------------

def test_every_disabled_key_used_in_code_is_in_the_catalog_with_en_and_bg():
    used = [(f, l, k) for f, l, k, _kw, _s in zoo.msg_calls() if k.startswith(("disabled-", "prereq-"))]
    assert len(used) >= 49
    bad = [f"{f}:{l} {k}" for f, l, k in used if k not in DISABLED_KEYS or not m.MESSAGES[k].get("bg")]
    assert not bad, bad


def test_every_disabled_catalog_key_is_used_in_code():
    used = {k for _f, _l, k, _kw, _s in zoo.msg_calls()}
    assert not sorted(DISABLED_KEYS - used), f"catalog keys no code uses: {sorted(DISABLED_KEYS - used)}"


def test_disabled_catalog_key_names():
    assert all(k.startswith(("disabled-", "prereq-")) for k in DISABLED_KEYS) and len(DISABLED_KEYS) >= 45


def test_disabled_templates_have_bulgarian_with_the_same_placeholders():
    assert m.validate_catalog({k: m.MESSAGES[k] for k in DISABLED_KEYS}, require_bg=True) == []


def test_bulgarian_disabled_templates_are_bulgarian_and_english_ones_are_not():
    assert not [k for k in DISABLED_KEYS if not re.search("[А-Яа-я]", m.MESSAGES[k]["bg"])]
    assert not [k for k in DISABLED_KEYS if re.search("[А-Яа-я]", m.MESSAGES[k]["en"])]


def test_call_site_parameters_match_the_template_fields():
    wrong = []
    for file, line, key, kws, splat in zoo.msg_calls():
        if key not in DISABLED_KEYS:
            continue
        fields = template_fields(m.MESSAGES[key]["en"])
        if (kws - fields) or (not splat and fields != kws):
            wrong.append(f"{file}:{line} {key}: passes {sorted(kws)}, template uses {sorted(fields)}")
    assert not wrong, wrong


@pytest.mark.parametrize("key", sorted(DISABLED_KEYS))
def test_every_disabled_template_renders_in_both_languages(key):
    template = m.MESSAGES[key]["en"]
    for n in (1, 2, 5):
        params = {f: ([n, n + 1] if f in m.list_fields(template) else n) for f in template_fields(template)}
        made = msg(key, **params)
        assert isinstance(made, Msg) and made.key == key
        bg = render(made, "bg")
        assert isinstance(bg, str) and bg and re.search("[А-Яа-я]", bg)
        assert "{" not in bg and "}" not in bg


def test_the_prerequisite_reason_nests_its_parts_and_localizes_them():
    parts = [msg("prereq-level", level=8), msg("prereq-any-of", items=["STR 13", "DEX 13"]),
             msg("prereq-armor-proficiency", category=msg("armor-category-medium")), msg("prereq-feat", name="Alert")]
    reason = msg("disabled-prereq-unmet-requires", parts=parts)
    assert reason == ("prerequisite not met: requires character level 8; STR 13 or DEX 13; medium armor proficiency; "
                      "the Alert feat")
    assert render(reason, "bg") == ("изискването не е изпълнено: изисква се ниво на героя 8; STR 13 или DEX 13; "
                                    "владеене на средна броня; талантът (feat) Alert")
    assert render(msg("disabled-school-limit", free=1, schools=["evocation", "illusion"]), "bg") == \
        "само 1 заклинание може да е извън evocation или illusion на това ниво"
    assert render(msg("disabled-school-limit", free=2, schools=["evocation", "illusion"]), "bg") == \
        "само 2 заклинания могат да са извън evocation или illusion на това ниво"


def test_a_pruned_reason_nests_the_disabled_reason_it_quotes():
    made = msg("pruned-asi-option-closed", label="Ability Score Improvement", option="Strength",
               why=msg("disabled-ability-cap-20"))
    assert made == ("'Ability Score Improvement': Strength is not available (would exceed the ability score cap of 20) "
                    "and was ignored.")
    assert render(made, "bg") == ("'Ability Score Improvement': Strength не е наличен (би надвишило горната граница от 20 "
                                  "за характеристика); изборът беше пренебрегнат.")
    closed = msg("pruned-ability-closed", label="X", items=[msg("pruned-ability-closed-item", ab="STR", why=msg("disabled-feat-ability-max", cap=20))])
    assert closed == "'X': STR is already at maximum (20) and was ignored."
    assert render(closed, "bg") == "'X': STR е вече на максимума (20); изборът беше пренебрегнат."


# --- AST guard: no plain-text disabledReason ------------------------------------------------------------------------------

REASON_FUNCS = {"_taken_reason", "_target_reason", "_mastery_filter_reason", "_feat_prerequisite_unmet_reason",
                "_invocation_unmet", "_invocation_unmet_2024", "invocation_unmet"}


def _plain(v) -> bool:
    return isinstance(v, (ast.JoinedStr, ast.BinOp)) or (isinstance(v, ast.Constant) and isinstance(v.value, str))


def plain_disabled_sites(tree) -> list[int]:
    """Lines where a disabledReason is built as plain text: the dict key / keyword / subscript target `disabledReason`
    given a str literal, f-string or concatenation; a variable `reason` (or a `*_REASON` constant) assigned such text or
    augmented (`reason += ...` drops the tag) in a function that sets a disabledReason; a plain `return` of a reason helper;
    a plain `.append` into the prerequisite part list."""
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "disabledReason" and _plain(v):
                    bad.append(v.lineno)
        elif isinstance(node, ast.keyword) and node.arg == "disabledReason" and _plain(node.value):
            bad.append(node.value.lineno)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == "disabledReason"
                        and _plain(node.value)):
                    bad.append(node.lineno)
                if isinstance(t, ast.Name) and t.id.endswith("_REASON") and _plain(node.value):
                    bad.append(node.lineno)
    for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
        sets_reason = any((isinstance(n, ast.Constant) and n.value == "disabledReason")
                          or (isinstance(n, ast.keyword) and n.arg == "disabledReason") for n in ast.walk(fn))
        for node in ast.walk(fn):
            if sets_reason and isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "reason" for t in node.targets) \
                    and _plain(node.value):
                bad.append(node.lineno)
            elif sets_reason and isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name) and node.target.id == "reason":
                bad.append(node.lineno)
            elif fn.name in REASON_FUNCS and isinstance(node, ast.Return) and node.value is not None and _plain(node.value):
                bad.append(node.lineno)
            elif fn.name in REASON_FUNCS and isinstance(node, ast.Return) and isinstance(node.value, ast.IfExp) \
                    and (_plain(node.value.body) or _plain(node.value.orelse)):
                bad.append(node.lineno)
            elif fn.name == "_feat_prerequisite_failing_parts" and isinstance(node, ast.Call) \
                    and isinstance(node.func, ast.Attribute) and node.func.attr == "append" and node.args and _plain(node.args[0]):
                bad.append(node.lineno)
    return sorted(set(bad))


def test_no_plain_text_disabled_reason_in_the_engine():
    found = {pathlib.Path(p).name: plain_disabled_sites(t) for p, t in zoo.server_trees()}
    found = {k: v for k, v in found.items() if v}
    assert not found, f'use msg("disabled-...", ...) for disabledReason values; plain text at {found}'


def test_the_ast_guard_catches_what_it_should():
    bad = ast.parse('''
def f(o, c):
    a = {"disabledReason": "x"}
    b = {"disabledReason": f"x {c}"}
    o["disabledReason"] = "plain"
    o.update(disabled=True, disabledReason="plain")
    reason = "plain"
    reason += msg("k")
    ok = {"disabledReason": msg("k")}
    o["disabledReason"] = reason
    reason = msg("k")
_LESSONS_REASON = "plain"
def _taken_reason(feat, taken):
    if x:
        return "already taken"
    return f"already taken ({x})"
def _target_reason():
    return None if a else "plain"
def _feat_prerequisite_failing_parts():
    parts.append("plain")
    parts.append(msg("k"))
def g():
    reason = "unrelated: this function sets no disabledReason"
''')
    assert plain_disabled_sites(bad) == [3, 4, 5, 6, 7, 8, 12, 15, 16, 18, 20]


# --- tag loss and Bulgarian coverage over the zoo ------------------------------------------------------------------------

pytestmark_data = pytest.mark.skipif(bool(zoo.NEEDS_DATA), reason=f"5etools data missing: {', '.join(zoo.NEEDS_DATA)}")
CHUNKS = 8


@pytest.fixture(scope="module")
def catalog():
    return zoo.load()


@pytest.fixture(scope="module")
def cases(catalog):
    return zoo.zoo(catalog)


def _reasons(res):
    for card in res.get("choices") or []:
        for opt in card.get("options") or []:
            if opt.get("disabledReason") is not None:
                yield f"{card['id']} | {opt['id']}", opt["disabledReason"]


@pytestmark_data
@pytest.mark.parametrize("chunk", range(CHUNKS))
def test_every_disabled_reason_in_the_zoo_is_a_tagged_message_and_localizes_to_bulgarian(chunk, cases, catalog):
    import copy
    plain, stayed = [], []
    for name in sorted(cases)[chunk::CHUNKS]:
        res = zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))
        bg = localize({"choices": res["choices"]}, "bg")["choices"]
        bg_reasons = {}
        for card in bg:
            for opt in card.get("options") or []:
                if opt.get("disabledReason") is not None:
                    bg_reasons[f"{card['id']} | {opt['id']}"] = opt["disabledReason"]
        for where, reason in _reasons(res):
            if not isinstance(reason, Msg):
                plain.append(f"{name}: {where}: {reason!r}")
                continue
            text = bg_reasons[where]
            if type(text) is not str or text == str(reason) or not re.search("[А-Яа-я]", text):
                stayed.append(f"{name}: {where}: {reason.key}: {reason}")
    assert not plain, f"tag loss (a plain str where a Msg is expected): {plain[:5]}"
    assert not stayed, f"English left after localize(bg): {stayed[:5]}"


@pytestmark_data
def test_the_zoo_reaches_most_disabled_shapes(cases, catalog):
    import copy
    keys = set()
    for name in sorted(cases):
        res = zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))
        keys |= {r.key for _w, r in _reasons(res) if isinstance(r, Msg)}
    assert len(keys) >= 28, sorted(keys)
    # the rest are exercised by the engine tests (all but the two feat-category / martial prerequisite parts) and by the
    # per-template render test above


# --- the engine's own comparison: startswith("already taken") ---------------------------------------------------------------

def test_taken_reason_keeps_the_text_the_engine_compares_against():
    feat = {"index": "alert-xphb", "name": "Alert", "source": "XPHB"}
    plain = resolve_mod._taken_reason(feat, {"alert-xphb": "Alert, XPHB"})
    cross = resolve_mod._taken_reason({"index": "alert-phb", "name": "Alert", "source": "PHB"},
                                      {"name:" + resolve_mod._feat_name_key(feat): "Alert, XPHB"})
    assert isinstance(plain, Msg) and plain.key == "disabled-already-taken" and plain == "already taken"
    assert isinstance(cross, Msg) and cross.key == "disabled-already-taken-from" and cross == "already taken (Alert, XPHB)"
    for reason in (plain, cross):
        assert reason.startswith("already taken") and str(reason).startswith("already taken")
        assert not render(reason, "bg").startswith("already taken")  # only the engine's English text is compared
    assert resolve_mod._taken_reason({**feat, "repeatable": True}, {"alert-xphb": "x"}) is None
    assert resolve_mod._taken_reason(feat, None) is None


@pytestmark_data
def test_a_duplicate_species_feat_pick_is_still_a_duplicate_problem_not_a_prerequisite_problem(catalog):
    res = zoo.resolve(zoo.TRIGGERS["feat-duplicate-species-card"](), catalog)
    (p,) = [p for p in res["problems"] if p["id"].startswith("feat-")]
    assert p["id"] == "feat-duplicate-savage-attacker-xphb-species:human-xphb:feat-0"
    assert isinstance(p["message"], Msg) and p["message"].key == "feat-duplicate-at-source"
    card = next(c for c in res["choices"] if c["id"] == "species:human-xphb:feat-0")
    opt = next(o for o in card["options"] if o["id"] == "feat:savage-attacker-xphb")
    assert isinstance(opt["disabledReason"], Msg) and opt["disabledReason"].startswith("already taken")


@pytestmark_data
def test_a_prerequisite_reason_is_not_mistaken_for_a_taken_one(catalog):
    d = zoo.TRIGGERS["feat-prerequisite-unmet-asi"]()
    res = zoo.resolve(d, catalog)
    card = next(c for c in res["choices"] if c["id"] == "class:fighter:4:asi")
    opt = next(o for o in card["options"] if o["id"] == "feat:abjuration-adept-au")
    assert opt["disabledReason"].key == "disabled-prereq-unmet-requires" and not opt["disabledReason"].startswith("already taken")


@pytestmark_data
def test_the_duplicate_problem_does_not_depend_on_the_requested_language():
    app.config["TESTING"] = True
    with app.test_client() as c:
        d = zoo.TRIGGERS["feat-duplicate-species-card"]()
        ids = {lang: [p["id"] for p in c.post(f"/api/resolve?lang={lang}", json=d).get_json()["problems"]] for lang in ("en", "bg")}
    assert ids["en"] == ids["bg"] == ["feat-duplicate-savage-attacker-xphb-species:human-xphb:feat-0"]


# --- ?lang=bg end to end ---------------------------------------------------------------------------------------------------

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _options(resolution: dict) -> dict:
    return {f"{c['id']} | {o['id']}": o["disabledReason"] for c in resolution["choices"] for o in c.get("options") or []
            if o.get("disabledReason") is not None}


@pytestmark_data
def test_resolve_lang_bg_returns_bulgarian_disabled_reasons(client):
    draft = zoo.base(ruleset="2024")
    draft["background"] = {"id": "guard-xphb", "choices": {}}
    en = client.post("/api/resolve", json=draft).get_json()
    bg = client.post("/api/resolve?lang=bg", json=draft).get_json()
    assert client.post("/api/resolve?lang=en", json=draft).get_json() == en
    en_r, bg_r = _options(en), _options(bg)
    assert set(en_r) == set(bg_r) and len(en_r) >= 3
    assert all(re.search("[А-Яа-я]", t) for t in bg_r.values())
    taken = [w for w, t in en_r.items() if t.startswith("already taken")]
    assert taken, "the Guard background grants Alert, so Alert is taken at the ASI cards"
    assert {en_r[w] for w in taken} == {"already taken"} and {bg_r[w] for w in taken} == {"вече взето"}
    # nothing else of the resolution depends on the language
    def rest(res):
        res = {**res, "choices": [{**c, "options": [{k: v for k, v in o.items() if k != "disabledReason"}
                                                    for o in c.get("options") or []]} for c in res["choices"]]}
        return {k: v for k, v in res.items() if k not in ("problems", "warnings", "pruned")}
    assert rest(bg) == rest(en)


@pytestmark_data
def test_resolve_lang_bg_prerequisite_reason_with_nested_parts(client):
    d = zoo.TRIGGERS["feat-prerequisite-unmet-asi"]()
    en = _options(client.post("/api/resolve", json=d).get_json())
    bg = _options(client.post("/api/resolve?lang=bg", json=d).get_json())
    key = "class:fighter:4:asi | feat:abjuration-adept-au"
    assert en[key] == "prerequisite not met: requires the Spellcasting or Pact Magic feature"
    assert bg[key] == "изискването не е изпълнено: изисква се чертата Spellcasting или Pact Magic"
    key = "class:fighter:4:asi | feat:crossbow-expert-xphb"
    assert en[key] == "prerequisite not met: requires DEX 13"
    assert bg[key] == "изискването не е изпълнено: изисква се DEX 13"
