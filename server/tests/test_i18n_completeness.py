"""C1: one cross-layer completeness test for both languages.

Layers and what this file checks across them (the per-layer tests live next to each layer: test_i18n_messages /
_problems / _pruned / _disabled / _labels, test_export_labels, test_glossary, frontend copyGuards.test.ts):

1. Server message catalogs (problems, warnings, pruned, disabled, labels): every key has `en` AND `bg`, nothing else,
   the same placeholders, Cyrillic only in `bg`, no key in two modules.
2. Export labels (`export_labels.LABELS`): `bg` and `en` hold the same keys and placeholders.
3. Glossary: every term has en + bg; `frontend/src/copy/glossary.gen.ts` holds exactly what `glossary.json` holds.
4. Frontend copy: the key lists (and leaf kinds) of `bg.ts` and `en.ts`, parsed from SOURCE (i18n/ts_copy.py), are equal.
5. Consistency of the same rules term across layers (glossary vs export labels vs frontend copy). Findings are
   PINNED (`KNOWN_INCONSISTENCIES`, each with a reason): a new one fails here; a fixed one must leave the table. The
   table is mirrored in docs/I18N-REVIEW.md / ARCHITECTURE-CURRENT-STATE.md "i18n".
6. End to end: for mixed 2014/2024 drafts `/api/resolve?lang=bg` (and the export gate) leaves no plain-English
   problem / warning / pruned reason / disabledReason / card label / description / unavailableReason, except the
   allowlisted data-sourced text.
"""
from __future__ import annotations

import copy
import json
import pathlib
import re

import pytest

import export_labels
import i18n_zoo as zoo
from app import app
from i18n import glossary
from i18n.catalog import MESSAGES, disabled, labels, problems, pruned, warnings
from i18n.messages import validate_catalog
from i18n.ts_copy import COPY_DIR, flatten, load_glossary_ts, parse_catalog

CYRILLIC = re.compile("[Ѐ-ӿ]")
FRONTEND_SRC = COPY_DIR.parent
MODULES = {"problems": problems, "warnings": warnings, "pruned": pruned, "disabled": disabled, "labels": labels}

pytestmark_data = pytest.mark.skipif(bool(zoo.NEEDS_DATA), reason=f"5etools data missing: {', '.join(zoo.NEEDS_DATA)}")


def _leaves(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, path + (k,))
    else:
        yield ".".join(path), node


# ---- 1. server message catalogs --------------------------------------------------------------------------------------

@pytest.mark.parametrize("name", MODULES)
def test_catalog_module_has_english_and_bulgarian_for_every_key(name):
    entries = MODULES[name].MESSAGES
    assert entries, name
    for key, entry in entries.items():
        assert set(entry) == {"en", "bg"}, (name, key, sorted(entry))
        assert isinstance(entry["en"], str) and entry["en"].strip(), (name, key, "en")
        assert isinstance(entry["bg"], str) and entry["bg"].strip(), (name, key, "bg")
        assert not CYRILLIC.search(entry["en"]), (name, key)
    assert validate_catalog(entries, require_bg=True) == []


def test_catalog_keys_are_unique_across_modules_and_counted():
    total = sum(len(m.MESSAGES) for m in MODULES.values())
    assert len(MESSAGES) == total  # build() raises on a duplicate; the merged size proves nothing was lost
    assert validate_catalog(require_bg=True) == []
    counts = {n: len(m.MESSAGES) for n, m in MODULES.items()}
    # floors: a catalog never shrinks silently (problems 88 = 52 + 36, pruned 37, disabled 49, labels 107 at I5)
    assert counts["problems"] >= 52 and counts["warnings"] >= 36 and counts["pruned"] >= 37
    assert counts["disabled"] >= 49 and counts["labels"] >= 107


def test_a_bulgarian_template_without_cyrillic_is_only_a_pure_placeholder_or_quoted_data():
    plain = {k: e["bg"] for k, e in MESSAGES.items() if not CYRILLIC.search(e["bg"])}
    # a Bulgarian template with no Cyrillic would print English: only templates that are just a parameter qualify
    assert all(re.fullmatch(r"(\{[^{}]*\}|[\s,.:;'()\[\]|-])*", t) for t in plain.values()), plain


# ---- 2. export labels ------------------------------------------------------------------------------------------------

def test_export_labels_have_the_same_keys_and_placeholders_in_both_languages():
    from i18n.messages import template_fields
    assert tuple(export_labels.LABELS) == ("bg", "en")
    bg, en = dict(_leaves(export_labels.LABELS["bg"])), dict(_leaves(export_labels.LABELS["en"]))
    assert set(bg) == set(en) and len(bg) > 150
    assert [k for k in bg if template_fields(bg[k]) != template_fields(en[k])] == []
    assert [k for k, v in en.items() if CYRILLIC.search(v)] == []


# ---- 3. glossary ------------------------------------------------------------------------------------------------------

def test_every_glossary_term_has_english_and_bulgarian():
    data = glossary.load()
    assert glossary.validate(data) == []
    assert len(data) >= 40
    for tid, term in data.items():
        assert term["en"].strip() and term["bg"].strip(), tid
        assert not CYRILLIC.search(term["en"]), tid
        if tid in glossary.BG_IS_ENGLISH:
            assert term["bg"] == term["en"], tid  # owner decision 2026-11-05: the English term is the Bulgarian one
        else:
            assert CYRILLIC.search(term["bg"]), tid


def test_the_frontend_glossary_holds_exactly_what_glossary_json_holds():
    data = glossary.load()
    ts = load_glossary_ts()
    assert set(ts) == set(data)
    assert {tid: {"en": t["en"], "bg": t["bg"]} for tid, t in data.items()} == ts


# ---- 4. frontend copy key lists ---------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def front():
    bg = flatten(parse_catalog(COPY_DIR / "bg.ts", "bg"))
    en = flatten(parse_catalog(COPY_DIR / "en.ts", "en"))
    return bg, en


def test_the_parser_sees_the_catalogs(front):
    bg, en = front
    # 481 leaves at C1 (360 plain texts + 121 templates in bg); the floor catches a parser that silently stops early
    assert len(bg) >= 470 and len(en) >= 470
    assert {"nav.steps.home", "sheet.armorClass.title", "msg.raw", "library.unnamed"} <= set(bg)


def test_bg_and_en_copy_have_the_same_keys_and_leaf_kinds(front):
    bg, en = front
    assert sorted(set(bg) - set(en)) == [] and sorted(set(en) - set(bg)) == []
    # a text stays a text and a template stays a template (en may compute a text from the glossary: "expr")
    mismatch = {p: (bg[p].kind, en[p].kind) for p in bg if bg[p].kind != en[p].kind and not (bg[p].kind == "str" and en[p].kind == "expr")}
    assert mismatch == {}, mismatch


def test_en_copy_has_no_cyrillic_and_every_glossary_reference_exists(front):
    _bg, en = front
    data = glossary.load()
    assert [p for p, leaf in en.items() if CYRILLIC.search(leaf.text)] == []
    refs = set(re.findall(r"\bg\.(\w+)\.(en|bg)\b", (COPY_DIR / "en.ts").read_text(encoding="utf-8")))
    assert refs and {t for t, _ in refs} <= set(data), sorted({t for t, _ in refs} - set(data))
    assert {lang for _t, lang in refs} == {"en"}  # the English catalog reads only the English wording
    assert "glossary" not in (COPY_DIR / "bg.ts").read_text(encoding="utf-8")  # bg.ts keeps its own (pinned) wording


def test_the_frontend_term_table_matches_the_glossary(front):
    """The path -> term table of copyGuards.test.ts, re-checked here from source for both languages."""
    bg, en = front
    data = glossary.load()
    src = (FRONTEND_SRC / "copyGuards.test.ts").read_text(encoding="utf-8")
    table = re.findall(r'\["([\w.]+)", "(\w+)"\]', src)
    assert len(table) >= 30
    for path, term in table:
        assert bg[path].kind == "str" and bg[path].text == data[term]["bg"], (path, term)
        assert _value(en[path], data) == data[term]["en"], (path, term)


def _value(leaf, data, lang="en") -> str:
    """Text of a leaf; `g.term.lang` and `${g.term.lang}` references are resolved with the glossary."""
    if leaf.kind == "fn":
        return leaf.text
    text = re.sub(r"\$\{g\.(\w+)\.(en|bg)\}", lambda m: data[m.group(1)][m.group(2)], leaf.text)
    whole = re.fullmatch(r"g\.(\w+)\.(en|bg)", text)
    if whole:
        return data[whole.group(1)][whole.group(2)]
    if leaf.kind == "expr" and text.startswith("`") and text.endswith("`"):
        return text[1:-1]
    return text


# ---- 5. one rules term, the same wording in every layer ---------------------------------------------------------------

# Every place where a glossary term's English wording is in a surface's English text but its Bulgarian wording is NOT in
# the matching Bulgarian text. Key: "<surface>:<term>:<path>". A fix removes the line; a new finding fails the test.
_LEGACY = ("Bulgarian UI page / label that has always shown the English word (the SK6-BI LEGACY allowlist; translating it "
           "is a deliberate later change)")
# T1 (owner decision 2026-11-05): the feats / resistance / background / species / rest findings of C1 are all fixed (one
# wording per term, with its English term in brackets); only the Equipment page words are still English in the BG UI, because
# 'Equipment' / 'Екипировка' is not one of the 29 rows of docs/TERMS-PROPOSAL.md.
KNOWN_INCONSISTENCIES: dict[str, str] = {
    "front:originFeat:choice.groups.origin": "false positive: the group heading is the plural 'Таланти от произхода (Origin "
                                             "Feats)' of the singular glossary term 'Талант от произхода'; wording is consistent",
    **{f"front:{term}:{path}": _LEGACY for term, path in [
        ("equipment", "nav.steps.equipment"), ("equipment", "equipmentPage.title"),
    ]},
}


def _core(bg: str) -> str:
    """The Bulgarian wording of a glossary term without its English term in brackets (T1: "Талант (Feat)" -> "Талант")."""
    return re.sub(r"\s*\([^()]*\)$", "", bg)


def _scan_front(front, data) -> set[str]:
    bg, en = front
    found = set()
    for path in bg:
        if bg[path].kind == "fn" or en[path].kind == "fn":
            continue
        e, b = _value(en[path], data).casefold(), _value(bg[path], data, "bg").casefold()
        for tid, term in data.items():
            if re.search(r"\b" + re.escape(term["en"].casefold()) + r"(s|es)?\b", e) and _core(term["bg"]).casefold() not in b:
                found.add(f"front:{tid}:{path}")
    return found


def _scan_export(data) -> set[str]:
    bg, en = dict(_leaves(export_labels.LABELS["bg"])), dict(_leaves(export_labels.LABELS["en"]))
    found = set()
    for path in bg:
        for tid, term in data.items():
            if re.search(r"\b" + re.escape(term["en"].casefold()) + r"(s|es)?\b", en[path].casefold()) \
                    and _core(term["bg"]).casefold() not in bg[path].casefold():
                found.add(f"export:{tid}:{path}")
    return found


def test_a_rules_term_is_worded_the_same_in_the_glossary_the_exports_and_the_frontend(front):
    data = glossary.load()
    found = _scan_export(data) | _scan_front(front, data)
    new = sorted(found - set(KNOWN_INCONSISTENCIES))
    stale = sorted(set(KNOWN_INCONSISTENCIES) - found)
    assert not new, f"new wording inconsistency (fix it, or pin it with a reason in KNOWN_INCONSISTENCIES): {new}"
    assert not stale, f"fixed or vanished, remove from KNOWN_INCONSISTENCIES: {stale}"


def test_the_english_side_has_no_inconsistency(front):
    """EN export labels and EN frontend copy: a rules term printed as a glossary term is spelled exactly like it
    (heading position); the lower-case mid-sentence forms ('on a short rest') are allowed."""
    _bg, en = front
    data = glossary.load()
    bad = []
    surfaces = {f"front:{p}": _value(leaf, data) for p, leaf in en.items() if leaf.kind != "fn"}
    # the words of the `recharge` / `senses` families sit inside sentences and are lower case on purpose (GLOSSARY_NESTED)
    surfaces.update({f"export:{p}": t for p, t in _leaves(export_labels.LABELS["en"])
                     if not p.startswith(("recharge.", "senses."))})
    for where, text in surfaces.items():
        for tid, term in data.items():
            w = term["en"]
            if w[:1].isupper() and text.casefold() == w.casefold() and text != w:
                bad.append((where, tid, text))
    assert bad == []


def test_export_english_words_in_the_bulgarian_labels_are_the_known_set():
    english_in_bg = {p for p, t in _leaves(export_labels.LABELS["bg"]) if not CYRILLIC.search(t)}
    assert {p.split(".")[-1] for p in english_in_bg} == {"spellSlots", "pactSlots", "attackVersatile", "attackOffhand", "attackRange"}


# ---- 6. end to end ----------------------------------------------------------------------------------------------------

TERM_TAILS = {"Expertise", "Fighting Style", "Maneuvers", "Metamagic", "Eldritch Invocation"}
# engine-written texts that keep English in Bulgarian on purpose (docs: ARCHITECTURE "i18n" > known English leftovers)
ALLOWED_ENGLISH = [
    re.compile(r"^[^:]+: (" + "|".join(sorted(TERM_TAILS)) + r")$"),  # "<feat or feature>: <rules term not translated>"
]


def _strings(node, out: set, depth: int = 0) -> None:
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
def catalog():
    return zoo.load()


@pytest.fixture(scope="module")
def data_texts(catalog) -> set[str]:
    """Every string the data supplies: a card label or description that is one of these is data, not engine text."""
    from catalog import feat_effects_data, reference_data
    out: set[str] = set()
    for value in vars(catalog).values():
        _strings(value, out)
    for module in (reference_data, feat_effects_data):
        for name, value in vars(module).items():
            if not name.startswith("__"):
                _strings(value, out)
    return out


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _mixed_drafts(catalog) -> dict[str, dict]:
    """Mixed 2014/2024 drafts: the ruleset 'mixed' with 2014 and 2024 pieces together, plus messy variants that fill
    every message-bearing field (problems, warnings, pruned reasons, disabled options, pending cards)."""
    import kitchen_sink as ks
    from engine.resolve import resolve
    cases: dict[str, dict] = {}
    base = zoo.base()
    cases["mixed/fighter8-2014"] = base
    cases["mixed/fighter6-with-2024-species-and-background"] = dict(
        zoo.base(), species={"id": "human-xphb", "choices": {}}, background={"id": "soldier-xphb", "choices": {}},
        classes=[{"classId": "fighter", "level": 6, "choices": {}}])
    cases["mixed/wizard5"] = zoo._wizard_draft(level=5, ruleset="mixed")
    cases["mixed/wizard18-2014-class-2024-spells"] = zoo._wizard_draft(
        level=18, ruleset="mixed", **{"class:wizard:spellbook": ["alarm-xphb", "shield-xphb"]})
    cases["mixed/multiclass-2014-rogue-2024-bard"] = dict(base, classes=[
        {"classId": "rogue", "level": 3, "choices": {"class:rogue:1:prof-choice-0": ["skill-acrobatics", "skill-athletics", "skill-stealth", "skill-insight"]}},
        {"classId": "bard", "level": 2, "choices": {"class:bard:multiclass-prof-choice-0": ["skill-acrobatics"]}}])
    for sid in ("feats-mixed-wizard8", "bard10-2014", "warlock7-2024", "fighter4-2024"):
        spec = ks.KITCHEN_SINK.get(sid)
        if spec is None or ks.skip_reason(spec):
            continue
        cases[f"mixed/ks-{sid}"] = ks.build(sid, catalog, resolve)
        cases[f"mixed/ks-{sid}-cleared"] = zoo._clear(ks.build(sid, catalog, resolve))
        cases[f"mixed/ks-{sid}-half"] = zoo._half(ks.build(sid, catalog, resolve))
        cases[f"mixed/ks-{sid}-as-mixed"] = zoo._ruleset(ks.build(sid, catalog, resolve), "mixed")
    for name in ("malformed-name", "ability-invalid-str-text", "ability-out-of-range-final", "unknown-class", "unknown-subclass",
                 "subclass-not-unlocked", "total-level-exceeded", "unknown-background", "duplicate-class",
                 "point-buy-over-budget", "bard-multiclass-skill-duplicate", "warlock-invocation-stale",
                 "warlock-2024-invocation-stale", "cleric-2024-mismatch", "sorcerer-metamagic-too-many",
                 "background-languages-duplicate", "subclass-spell-school-limit", "fighter-2024-mastery-bad",
                 "barbarian-2024-weapon-mastery", "bard-2024-magical-secrets", "feat-duplicate-species-card"):
        if name in zoo.TRIGGERS:
            d = zoo.TRIGGERS[name]()
            if isinstance(d, dict):
                cases[f"mixed/t-{name}"] = dict(d, ruleset="mixed") if d.get("ruleset") != "mixed" else d
    for gname, gdraft in list(zoo.golden_drafts().items())[:3]:
        cases[f"mixed/golden-{gname}"] = gdraft
        cases[f"mixed/golden-{gname}-cleared"] = zoo._clear(gdraft)
        cases[f"mixed/golden-{gname}-to-2024"] = zoo._ruleset(gdraft, "2024")
        cases[f"mixed/golden-{gname}-half"] = zoo._half(gdraft)
    return cases


def _english_left(where: str, value, data_texts: set[str], *, kind: str) -> str | None:
    """None when `value` (a Bulgarian-language leaf) is fine, else a description of the English left in it."""
    if not isinstance(value, str) or not value.strip():
        return None
    if CYRILLIC.search(value):
        return None
    if any(rx.match(value) for rx in ALLOWED_ENGLISH):
        return None
    if kind in ("label", "description") and value in data_texts:
        return None  # the data supplies this text (class feature name, 5etools description, equipment envelope ...)
    return f"{where}: {value[:90]!r}"


@pytestmark_data
def test_resolve_lang_bg_leaves_no_plain_english_for_mixed_drafts(client, catalog, data_texts):
    cases = _mixed_drafts(catalog)
    assert len(cases) >= 40, len(cases)
    seen = {"problems": 0, "warnings": 0, "pruned": 0, "disabled": 0, "cards": 0}
    left: list[str] = []
    for name, draft in sorted(cases.items()):
        res_bg = client.post("/api/resolve?lang=bg", json=copy.deepcopy(draft))
        res_en = client.post("/api/resolve?lang=en", json=copy.deepcopy(draft))
        assert res_bg.status_code == res_en.status_code == 200, name
        bg, en = res_bg.get_json(), res_en.get_json()
        assert client.post("/api/resolve", json=copy.deepcopy(draft)).get_json() == en, name  # no ?lang= is English
        lb, le = zoo.leaves(bg), zoo.leaves(en)
        for kind in ("problems", "warnings", "pruned"):
            seen[kind] += len(lb[kind])
            assert [x[0] for x in lb[kind]] == [x[0] for x in le[kind]], (name, kind)  # ids never change
            for (_id, text) in lb[kind]:
                msg = _english_left(f"{name}: {kind} {_id}", text, data_texts, kind=kind)
                if msg:
                    left.append(msg)
        seen["disabled"] += len(lb["disabled"])
        for where, text in lb["disabled"].items():
            msg = _english_left(f"{name}: disabledReason {where}", text, data_texts, kind="disabled")
            if msg:
                left.append(msg)
        for card in bg["choices"]:
            seen["cards"] += 1
            for field in ("label", "description", "unavailableReason"):
                msg = _english_left(f"{name}: {card['id']} {field}", card.get(field), data_texts, kind=field)
                if msg:
                    left.append(msg)
        # only the localized texts differ between the languages
        assert zoo.without_localized(bg) == zoo.without_localized(en) or _only_texts_differ(bg, en), name
    assert all(n > 0 for n in seen.values()), seen
    assert not left, f"plain English left in lang=bg ({len(left)}): {left[:8]}"


def _only_texts_differ(bg: dict, en: dict) -> bool:
    """problems / warnings / pruned messages differ in text only (their ids and shapes are equal)."""
    strip = lambda r: {k: v for k, v in zoo.without_localized(r).items() if k not in ("problems", "warnings", "pruned")}
    return strip(bg) == strip(en)


@pytestmark_data
def test_export_gate_lang_bg_is_bulgarian_for_mixed_drafts(client):
    seen = 0
    for name, draft in {"mixed-2024-empty": zoo.base(ruleset="2024"), "mixed-wizard": zoo._wizard_draft(level=5, ruleset="mixed"),
                        "mixed-fighter-2024": zoo._fighter_2024()}.items():
        en = client.post("/api/export/yaml?lang=en", json=copy.deepcopy(draft))
        bg = client.post("/api/export/yaml?lang=bg", json=copy.deepcopy(draft))
        assert en.status_code == bg.status_code, name
        if bg.status_code != 400:
            continue
        e, b = en.get_json()["problems"], bg.get_json()["problems"]
        assert [p["id"] for p in e] == [p["id"] for p in b], name
        for p in b:
            seen += 1
            assert CYRILLIC.search(p["message"]), (name, p)
    assert seen >= 3


@pytestmark_data
def test_the_english_left_check_has_teeth(data_texts):
    assert _english_left("x", "Choose 2 skills.", data_texts, kind="description")
    assert _english_left("x", "Изберете 2 умения.", data_texts, kind="description") is None
    assert _english_left("x", "Skill Expert: Expertise", data_texts, kind="label") is None
    assert _english_left("x", "Skill Expert: Anything", data_texts, kind="label")
    assert json.dumps(sorted(TERM_TAILS))
