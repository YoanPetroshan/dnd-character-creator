"""I5: card labels, card descriptions and `unavailableReason` texts the engine WRITES are tagged messages
(`msg("label-...")`, `msg("desc-...")`, `msg("unavailable-...")`) with English and Bulgarian templates.

Same checks as I2-I4: catalog completeness both ways, en/bg placeholder parity, call-site parameters equal the template
fields, an AST guard against plain-text card texts, tag loss and Bulgarian coverage over the message zoo, `?lang=bg` end
to end through the Flask client. Plus the engine's own label comparison (`_label_is`, by catalog key, never by text).

What stays English on purpose (checked by the zoo test, not merely listed): a label or description that comes from the
DATA (a class feature / trait name such as "Divine Order", a 5etools description, a starting-equipment envelope's text)
and rules terms that are not translated in any slice (decision E4 and the I2-I4 convention: Expertise, Fighting Style,
Maneuvers, Metamagic, Eldritch Invocation, class and spell-school names).
"""
from __future__ import annotations

import ast
import pathlib
import re

import pytest

import i18n_zoo as zoo
from app import app
from engine import class_choices_2024
from engine import resolve as resolve_mod
from i18n import catalog as catalog_pkg
from i18n import messages as m
from i18n.messages import Msg, localize, msg, render, template_fields

LABEL_KEYS = set(catalog_pkg.labels.MESSAGES)
PREFIXES = ("label-", "desc-", "noun-", "unavailable-")
# rules terms used as the tail of a "<feat>: <tail>" label; they stay English in Bulgarian (the label is still a Msg)
TERM_TAILS = {"Expertise", "Fighting Style", "Maneuvers", "Metamagic", "Eldritch Invocation"}


def _literal_strings() -> set[str]:
    """Every string constant in the server code the I-series scans (a key kept in a table counts as used)."""
    out: set[str] = set()
    for _path, tree in zoo.server_trees(with_catalog=True):
        out |= {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    return out


# --- catalog completeness and parity -----------------------------------------------------------------------------

def test_every_label_key_used_in_code_is_in_the_catalog_with_en_and_bg():
    used = [(f, l, k) for f, l, k, _kw, _s in zoo.msg_calls(with_catalog=True) if k.startswith(PREFIXES)]
    assert len(used) >= 90, len(used)
    bad = [f"{f}:{l} {k}" for f, l, k in used if k not in LABEL_KEYS or not m.MESSAGES[k].get("bg")]
    assert not bad, bad


def test_every_label_catalog_key_is_used_in_code():
    used = {k for _f, _l, k, _kw, _s in zoo.msg_calls(with_catalog=True)} | (_literal_strings() & LABEL_KEYS)
    assert not sorted(LABEL_KEYS - used), f"catalog keys no code uses: {sorted(LABEL_KEYS - used)}"


def test_label_catalog_key_names():
    assert all(k.startswith(PREFIXES) for k in LABEL_KEYS) and len(LABEL_KEYS) >= 95


def test_label_templates_have_bulgarian_with_the_same_placeholders():
    assert m.validate_catalog({k: m.MESSAGES[k] for k in LABEL_KEYS}, require_bg=True) == []


def test_bulgarian_label_templates_are_bulgarian_and_english_ones_are_not():
    assert not [k for k in LABEL_KEYS if not re.search("[А-Яа-я]", m.MESSAGES[k]["bg"]) and k != "label-prefixed"]
    assert not [k for k in LABEL_KEYS if re.search("[А-Яа-я]", m.MESSAGES[k]["en"])]


def test_call_site_parameters_match_the_template_fields():
    wrong = []
    for file, line, key, kws, splat in zoo.msg_calls(with_catalog=True):
        if key not in LABEL_KEYS:
            continue
        fields = template_fields(m.MESSAGES[key]["en"])
        if (kws - fields) or (not splat and fields != kws):
            wrong.append(f"{file}:{line} {key}: passes {sorted(kws)}, template uses {sorted(fields)}")
    assert not wrong, wrong


@pytest.mark.parametrize("key", sorted(LABEL_KEYS))
def test_every_label_template_renders_in_both_languages(key):
    template = m.MESSAGES[key]["en"]
    for n in (1, 2, 5):
        params = {f: ([n, n + 1] if f in m.list_fields(template) else n) for f in template_fields(template)}
        made = msg(key, **params)
        assert isinstance(made, Msg) and made.key == key
        bg = render(made, "bg")
        assert isinstance(bg, str) and bg and "{" not in bg and "}" not in bg
        if key != "label-prefixed":
            assert re.search("[А-Яа-я]", bg)


def test_english_templates_are_the_former_texts():
    """A few of the byte-for-byte strings (the frozen snapshot pins the rest)."""
    assert msg("label-skill-proficiencies") == "Skill Proficiencies"
    assert msg("desc-asi") == "Increase one ability score by 2, or two ability scores by 1 each — or take a feat instead."
    assert msg("desc-feat-proficiencies", n=1) == "Choose 1 proficiency of your choice."
    assert msg("desc-feat-proficiencies", n=3) == "Choose 3 proficiencies of your choice."
    assert msg("desc-asi-improvement-options", n=1) == "Choose 1 ability score improvement option."
    assert msg("desc-feat-saves", n=1) == "Choose 1 ability to gain saving throw proficiency in."
    assert msg("desc-wizard-pick-none", level=1, condition=msg("desc-cond-action")) == \
        "No spell in your spellbook is eligible (level 1 that have a casting time of an action)."


def test_nested_card_texts_localize():
    label = msg("label-prefixed", head="Skill Expert", tail=msg("label-ability-score-increase"))
    assert label == "Skill Expert: Ability Score Increase"
    assert render(label, "bg") == "Skill Expert: Увеличаване на характеристика"
    noun = msg("noun-from-list", noun=msg("noun-cantrip", n=2), classes=["Cleric"])
    desc = msg("desc-choose-noun", count=2, noun=noun)
    assert desc == "Choose 2 cantrips from the Cleric list."
    assert render(desc, "bg") == "Изберете 2 трика от списъка на Cleric."
    spells = msg("noun-school", schools=["Evocation", "Illusion"], noun=msg("noun-spell-levels", n=1, levels=[1]))
    assert msg("desc-choose-noun", count=1, noun=spells) == "Choose 1 Evocation or Illusion level 1 spell."
    assert render(msg("desc-choose-noun", count=1, noun=spells), "bg") == \
        "Изберете 1 заклинание от ниво 1 от школа Evocation или Illusion."
    # a pruned reason nests the card label it quotes
    pruned = msg("pruned-proficient", label=msg("label-skill-proficiencies"), names=["Arcana"])
    assert render(pruned, "bg").startswith("'Владеене на умения':")


# --- AST guard: no plain-text card text ---------------------------------------------------------------------------------

CARD_KEYS = {"label", "description"}
ANY_DICT_KEYS = {"unavailableReason"}
CARD_BUILDERS = {"build_choice_template", "build_equipment_choice"}


def _plain(v) -> bool:
    """A str literal (not the empty one), f-string or concatenation, also on either side of `x or "..."` / `a if c else "..."`."""
    if isinstance(v, (ast.JoinedStr, ast.BinOp)):
        return True
    if isinstance(v, ast.Constant):
        return isinstance(v.value, str) and v.value != ""
    if isinstance(v, ast.BoolOp):
        return any(_plain(x) for x in v.values)
    if isinstance(v, ast.IfExp):
        return _plain(v.body) or _plain(v.orelse)
    return False


OPTION_NAMES = {"opt", "option", "o"}  # `opt["label"] = ...` writes an OPTION label (spell name + game term), not a card label


def plain_card_text_sites(tree, *, cards: bool = True) -> list[int]:
    """Lines where a card's label / description / unavailableReason is plain text: a dict literal that is a card (it has
    an "options" key) or any dict with "unavailableReason" given such a value; `tpl["label"] = ...` /
    `["description"] = ...` / `+=` on a subscript; a plain label or `description=` argument of the card builders; a plain
    label / description argument of the local `card(...)` helper of `_feat_extra_templates`. `cards=False` (the data
    tables: a feature name is a plain "label" there) only checks `unavailableReason`."""
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
            for k, v in zip(node.keys, node.values):
                if not isinstance(k, ast.Constant):
                    continue
                if (cards and k.value in CARD_KEYS and "options" in keys and _plain(v)) or (k.value in ANY_DICT_KEYS and _plain(v)):
                    bad.append(v.lineno)
        elif isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if (isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)
                        and t.slice.value in CARD_KEYS | ANY_DICT_KEYS
                        and not (isinstance(t.value, ast.Name) and t.value.id in OPTION_NAMES)):
                    if isinstance(node, ast.AugAssign) or _plain(node.value):
                        bad.append(node.lineno)
        elif isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
            if name in CARD_BUILDERS and len(node.args) >= 4 and _plain(node.args[3]):
                bad.append(node.args[3].lineno)
            if name == "card" and isinstance(node.func, ast.Name) and len(node.args) >= 3 \
                    and (_plain(node.args[1]) or _plain(node.args[2])):
                bad.append(node.lineno)
            for kw in node.keywords:
                if (name in CARD_BUILDERS and kw.arg == "description" and _plain(kw.value)) \
                        or (kw.arg in ANY_DICT_KEYS and _plain(kw.value)):
                    bad.append(kw.value.lineno)
    return sorted(set(bad))


def test_no_plain_text_card_label_description_or_unavailable_reason_in_the_engine():
    data_tables = {"reference_data.py", "feat_effects_data.py"}
    found = {pathlib.Path(p).name: plain_card_text_sites(t, cards=pathlib.Path(p).name not in data_tables)
             for p, t in zoo.server_trees(with_catalog=True)}
    found = {k: v for k, v in found.items() if v}
    assert not found, f'use msg("label-..."/"desc-..."/"unavailable-...") for card texts; plain text at {found}'


def test_the_ast_guard_catches_what_it_should():
    bad = ast.parse('''
a = {"id": 1, "label": "Plain", "options": []}
b = {"id": 1, "label": f"{x}: y", "description": "d", "options": []}
c = {"id": 1, "label": msg("label-size"), "description": msg("desc-size"), "options": []}
d = {"kind": "class", "label": "a source label is not a card"}
e = {"id": 1, "label": cls["name"], "description": _join(x) or "", "options": []}
f = {"description": _join(x) or "Fallback", "options": []}
g = {"label": "A" if x else "B", "options": []}
tpl["description"] = tpl["description"] + "more"
tpl["description"] += "more"
tpl["label"] = msg("label-size")
opt["label"] = f"{opt['label']} (term)"
h = {"unavailableReason": "plain"}
i = {"unavailableReason": msg("unavailable-no-option")}
build_choice_template(env, cid, source, "Plain label", description=msg("desc-size"))
build_choice_template(env, cid, source, msg("label-size"), description="plain")
build_choice_template(env, cid, source, label, description=description)
def _feat_extra_templates():
    def card(suffix, label, description, count, options): pass
    card("s", "Plain", msg("desc-size"), 1, [])
    card("s", msg("label-size"), msg("desc-size"), 1, [])
''')
    assert plain_card_text_sites(bad) == [2, 3, 7, 8, 9, 10, 13, 15, 16, 20]
    assert plain_card_text_sites(ast.parse('a = {"label": "Divine Order", "options": {}}'), cards=False) == []


def comparisons_with_label_text(tree) -> list[int]:
    """Lines comparing a card / option `label` (subscript or `.get`) with a string literal: the engine must compare a
    card label by its Msg key (`_label_is`), not by its text."""
    def is_label(n) -> bool:
        return (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and n.slice.value == "label") or (
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "get" and n.args
            and isinstance(n.args[0], ast.Constant) and n.args[0].value == "label")

    def is_text(n) -> bool:
        return isinstance(n, ast.Constant) and isinstance(n.value, str) or isinstance(n, ast.JoinedStr)

    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and all(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.ops):
            operands = [node.left, *node.comparators]
            if any(is_label(o) for o in operands) and any(is_text(o) for o in operands):
                bad.append(node.lineno)
    return sorted(bad)


def test_no_engine_code_compares_a_label_with_literal_text():
    found = {pathlib.Path(p).name: comparisons_with_label_text(t) for p, t in zoo.server_trees(with_catalog=True)}
    found = {k: v for k, v in found.items() if v}
    assert not found, f"compare a card label with _label_is(label, '<key>'), not with its text: {found}"
    bad = ast.parse('x = tpl["label"] == "Skill Proficiencies"\ny = o.get("label") != f"a"\nz = tpl["label"] == other["label"]\n'
                    'w = tpl["id"] == "x"')
    assert comparisons_with_label_text(bad) == [1, 2]


# --- the engine's own label comparison ----------------------------------------------------------------------------------

def test_label_is_compares_by_key_not_by_text():
    skill = msg("label-skill-proficiencies")
    assert resolve_mod._label_is(skill, "label-skill-proficiencies")
    assert not resolve_mod._label_is(skill, "label-tool-proficiencies")
    # a plain str with the very same text is NOT the tagged label (tag loss would break the relabel, so tests catch it)
    assert not resolve_mod._label_is("Skill Proficiencies", "label-skill-proficiencies")
    assert resolve_mod._provisional_choice_label({"type": "proficiencies"}).key == "label-skill-proficiencies"
    assert resolve_mod._provisional_choice_label({}).key == "label-choice"
    assert resolve_mod._provisional_choice_label({"type": "languages"}) == "Languages"


def test_a_non_skill_proficiency_envelope_is_relabelled_tool_proficiencies_by_key():
    env = {"choose": 1, "type": "proficiencies", "from": {"option_set_type": "options_array", "options": [
        {"option_type": "reference", "item": {"index": "lute", "name": "Lute"}}]}}
    cls = {"name": "Bard", "multi_classing": {"proficiency_choices": [env]}}
    (tpl,) = resolve_mod._multiclass_proficiency_choice_templates(cls, "bard")
    assert isinstance(tpl["label"], Msg) and tpl["label"].key == "label-tool-proficiencies" and tpl["label"] == "Tool Proficiencies"
    assert render(tpl["label"], "bg") == "Владеене на инструменти"
    skills = {**env, "from": {"option_set_type": "options_array", "options": [
        {"option_type": "reference", "item": {"index": "skill-arcana", "name": "Arcana"}}]}}
    (tpl,) = resolve_mod._multiclass_proficiency_choice_templates({"name": "Bard", "multi_classing": {"proficiency_choices": [skills]}}, "bard")
    assert tpl["label"].key == "label-skill-proficiencies"
    (tpl,) = resolve_mod._class_choice_templates({"name": "Bard", "proficiency_choices": [env]}, "bard")
    assert tpl["label"].key == "label-tool-proficiencies"


# --- tag loss and Bulgarian coverage over the zoo ------------------------------------------------------------------------

pytestmark_data = pytest.mark.skipif(bool(zoo.NEEDS_DATA), reason=f"5etools data missing: {', '.join(zoo.NEEDS_DATA)}")
CHUNKS = 8


@pytest.fixture(scope="module")
def catalog():
    return zoo.load()


@pytest.fixture(scope="module")
def cases(catalog):
    return zoo.zoo(catalog)


def _strings(node, out: set[str], depth: int = 0) -> None:
    if depth > 12:
        return
    if isinstance(node, str):
        out.add(node)
    elif isinstance(node, dict):
        for v in node.values():
            _strings(v, out, depth + 1)
    elif isinstance(node, (list, tuple, set, frozenset)):
        items = list(node)
        if items and all(isinstance(x, str) for x in items):
            out.update({" ".join(items), "\n".join(items), "\n\n".join(items)})
        for v in items:
            _strings(v, out, depth + 1)


@pytest.fixture(scope="module")
def data_texts(catalog) -> set[str]:
    """Every string the data supplies (the loaded catalog and the reference tables): a plain label or description must be one."""
    from catalog import feat_effects_data, reference_data
    out: set[str] = set()
    for value in vars(catalog).values():
        _strings(value, out)
    for module in (reference_data, feat_effects_data):
        for name, value in vars(module).items():
            if not name.startswith("__"):
                _strings(value, out)
    return out


def _bg(res):
    return {c["id"]: c for c in localize({"choices": res["choices"]}, "bg")["choices"]}


@pytestmark_data
@pytest.mark.parametrize("chunk", range(CHUNKS))
def test_every_engine_written_card_text_in_the_zoo_is_tagged_and_localizes_to_bulgarian(chunk, cases, catalog, data_texts):
    import copy
    plain, stayed, unknown = [], [], []
    for name in sorted(cases)[chunk::CHUNKS]:
        res = zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))
        bg = _bg(res)
        for card in res["choices"]:
            for field in ("label", "description", "unavailableReason"):
                value = card.get(field)
                if not value:
                    continue
                out = bg[card["id"]][field]
                if isinstance(value, Msg):
                    if type(out) is not str:
                        stayed.append(f"{name}: {card['id']}: {field}: still tagged after localize")
                    elif out == str(value) or not re.search("[А-Яа-я]", out):
                        # only "<feat>: <rules term>" keeps its English text (the term is not translated)
                        tail = value.params.get("tail")
                        if not (value.key == "label-prefixed" and tail in TERM_TAILS):
                            stayed.append(f"{name}: {card['id']}: {field}: {value.key}: {value}")
                elif field == "unavailableReason":
                    plain.append(f"{name}: {card['id']}: unavailableReason {value!r}")
                elif value not in data_texts:
                    plain.append(f"{name}: {card['id']}: {field} {value[:80]!r}")
    assert not plain, f"engine-written text left as plain English (tag loss or an unconverted site): {plain[:6]}"
    assert not stayed, f"English left after localize(bg): {stayed[:6]}"
    assert not unknown


@pytestmark_data
def test_the_zoo_reaches_most_label_keys(cases, catalog):
    import copy
    keys: set[str] = set()

    def collect(v):
        if isinstance(v, Msg):
            keys.add(v.key)
            for p in v.params.values():
                collect(p)
        elif isinstance(v, (list, tuple)):
            for x in v:
                collect(x)

    for name in sorted(cases):
        res = zoo.resolve(copy.deepcopy(cases[name]), zoo.catalog_for(name, catalog))
        for card in res["choices"]:
            for field in ("label", "description", "unavailableReason"):
                collect(card.get(field))
    reached = keys & LABEL_KEYS
    assert len(reached) >= 75, (len(reached), sorted(LABEL_KEYS - reached))
    # the rest are built by the engine suite and covered by the per-template render test


@pytestmark_data
def test_unavailable_reasons_are_tagged_messages(catalog):
    res = zoo.resolve(zoo._wizard_draft(level=18, ruleset="2024", **{"class:wizard:spellbook": ["alarm-xphb"]}), catalog)
    card = next(c for c in res["choices"] if c["id"] == "class:wizard:18:spell-mastery-1")
    assert card["status"] == "unavailable"
    assert isinstance(card["unavailableReason"], Msg) and card["unavailableReason"].key == "unavailable-no-option"
    assert card["unavailableReason"] == "Nothing can be chosen here with the current character: no option is offered yet."
    # the other two shapes
    shapes = class_choices_2024.mark_unavailable(
        [{"id": "class:wizard:18:spell-mastery-1", "source": {"kind": "class", "id": "wizard"}, "status": "pending", "count": 1,
          "options": [{"id": "a", "disabled": True}]},
         {"id": "species:human-xphb:feat-0", "source": {"kind": "species", "id": "human-xphb"}, "status": "pending",
          "count": 1, "options": []}], "2024")
    assert [c["unavailableReason"].key for c in shapes] == ["unavailable-all-closed", "unavailable-no-feat-offered"]
    assert render(shapes[1]["unavailableReason"], "bg") == "Избраните източници не предлагат талант, затова тук нищо не може да се избере."


# --- ?lang=bg end to end ----------------------------------------------------------------------------------------------------

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _cards(resolution: dict) -> dict:
    return {c["id"]: c for c in resolution["choices"]}


@pytestmark_data
def test_resolve_lang_bg_returns_bulgarian_card_texts(client):
    draft = zoo._fighter_2024()
    draft["classes"][0]["level"] = 4
    en = client.post("/api/resolve", json=draft).get_json()
    bg = client.post("/api/resolve?lang=bg", json=draft).get_json()
    assert client.post("/api/resolve?lang=en", json=draft).get_json() == en
    e, b = _cards(en), _cards(bg)
    assert set(e) == set(b)
    asi = "class:fighter:4:asi"
    assert e[asi]["label"] == "Ability Score Improvement" and b[asi]["label"] == "Увеличение на характеристики"
    assert e[asi]["description"].startswith("Increase one ability score by 2") and b[asi]["description"].startswith("Увеличете една")
    # fixed engine cards: the 2024 origin languages, Weapon Mastery, Starting Equipment
    langs = next(cid for cid in e if cid.endswith("languages") and e[cid]["label"] == "Languages")
    assert b[langs]["label"] == "Езици" and b[langs]["description"].startswith("Героят ви знае Common")
    mastery = next(cid for cid in e if cid.endswith("weapon-mastery"))
    assert b[mastery]["label"] == "Майсторство с оръжия" and "вида оръжия" in b[mastery]["description"]
    equip = next(cid for cid in e if "equipment-choice" in cid and e[cid]["label"] == "Starting Equipment")
    assert b[equip]["label"] == "Начална екипировка"
    # the description of a starting-equipment card is the data's own text and stays English
    assert b[equip]["description"] == e[equip]["description"]
    # every card keeps its id, count, selected, status, source and options (only the texts differ)
    assert zoo.without_localized(bg) == zoo.without_localized(en)


@pytestmark_data
def test_resolve_lang_bg_spell_cards_and_nested_card_labels(client):
    draft = zoo._wizard_draft(level=18, ruleset="2024", **{"class:wizard:spellbook": ["alarm-xphb"]})
    en = _cards(client.post("/api/resolve", json=draft).get_json())
    bg = _cards(client.post("/api/resolve?lang=bg", json=draft).get_json())
    assert en["class:wizard:spellbook"]["label"] == "Spellbook" and bg["class:wizard:spellbook"]["label"] == "Книга със заклинания"
    assert en["class:wizard:spells-cantrips"]["label"] == "Cantrips Known"
    assert bg["class:wizard:spells-cantrips"]["label"] == "Известни трикове"
    assert en["class:wizard:spells-cantrips"]["description"] == "Choose 5 cantrips from the Wizard spell list."
    assert bg["class:wizard:spells-cantrips"]["description"] == "Изберете 5 трика от списъка със заклинания на Wizard."
    mastery = "class:wizard:18:spell-mastery-1"
    assert en[mastery]["status"] == bg[mastery]["status"] == "unavailable"
    assert en[mastery]["label"] == "Spell Mastery (level 1)" and bg[mastery]["label"] == "Spell Mastery (ниво 1)"
    assert bg[mastery]["unavailableReason"].startswith("С текущия герой")
    assert en[mastery]["description"].startswith("No spell in your spellbook is eligible")
    assert bg[mastery]["description"].startswith("Няма подходящо заклинание")


@pytestmark_data
def test_a_pruned_reason_and_a_problem_quote_the_card_label_in_the_requested_language(client):
    d = zoo.TRIGGERS["feat-duplicate-species-card"]()
    en = client.post("/api/resolve", json=d).get_json()
    bg = client.post("/api/resolve?lang=bg", json=d).get_json()
    (pe,) = [p for p in en["problems"] if p["id"].startswith("feat-duplicate")]
    (pb,) = [p for p in bg["problems"] if p["id"].startswith("feat-duplicate")]
    assert pe["id"] == pb["id"] and pe["message"] != pb["message"] and re.search("[А-Яа-я]", pb["message"])
    # the export gate quotes the unresolved card's label
    gate_en = client.post("/api/export/yaml", json=zoo.base(ruleset="2024"))
    gate_bg = client.post("/api/export/yaml?lang=bg", json=zoo.base(ruleset="2024"))
    assert gate_en.status_code == gate_bg.status_code == 400
    en_msgs = [p["message"] for p in gate_en.get_json()["problems"]]
    bg_msgs = [p["message"] for p in gate_bg.get_json()["problems"]]
    assert len(en_msgs) == len(bg_msgs) and en_msgs != bg_msgs
