"""XL: the Markdown / PDF exports in Bulgarian and English.

* export_labels.LABELS: same keys, same placeholders, every template formats; EN is Cyrillic-free; rules terms equal the
  glossary; no Cyrillic literal is left in the exporters' code.
* An export of an ASCII-only draft in English contains no Cyrillic, in Markdown or in the PDF text.
* Bulgarian (and `lang` omitted) is byte-identical to the baseline (test_export_baseline.py) - re-checked here through
  the HTTP route as well.
* DejaVu draws both scripts; `/api/export/<fmt>?lang=` for every format and language, a bad `lang` is a 400.
* The PDF cell-width spy for both languages lives in test_export_completeness.py.
"""
from __future__ import annotations

import ast
import io
import json
import pathlib
import re
import urllib.parse

import pytest
from pypdf import PdfReader

import export_fields
import export_labels
from app import app
from catalog.loader import load
from engine.resolve import resolve
from export import to_yaml
from export_labels import GLOSSARY_LINKS, GLOSSARY_NESTED, LABELS, LANGS, label
from i18n import glossary
from i18n.messages import format_template, list_fields, template_fields
from kitchen_sink import KITCHEN_SINK, base_draft, build, fill, skip_reason
from markdown_export import to_markdown
from pdf_export import to_pdf
from test_export_baseline import BASELINE, HAND, normalise_pdf, sha
from test_export_completeness import ALL_SPECS

SERVER = pathlib.Path(__file__).resolve().parent.parent
CYRILLIC = re.compile("[Ѐ-ӿ]")


def _leaves(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, path + (k,))
    else:
        yield path, node


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---- the label tables ---------------------------------------------------------------------------------------------

def test_both_languages_have_the_same_keys():
    assert tuple(LABELS) == ("bg", "en") == export_labels.LANGS
    bg, en = dict(_leaves(LABELS["bg"])), dict(_leaves(LABELS["en"]))
    assert set(bg) == set(en)
    assert len(bg) > 150


@pytest.mark.parametrize("lang", LANGS)
def test_every_template_is_a_string_that_formats(lang):
    for path, template in _leaves(LABELS[lang]):
        assert isinstance(template, str) and template, path
        params = {name: ([2] if name in list_fields(template) else 2) for name in template_fields(template)}
        format_template(template, params)


def test_placeholders_are_the_same_in_both_languages():
    bg, en = dict(_leaves(LABELS["bg"])), dict(_leaves(LABELS["en"]))
    for path in bg:
        assert template_fields(bg[path]) == template_fields(en[path]), path


def test_english_has_no_cyrillic_and_bulgarian_has_it_where_it_translates():
    assert not [p for p, t in _leaves(LABELS["en"]) if CYRILLIC.search(t)]
    # a BG label without Cyrillic is deliberately the English word the export always printed (see export_labels.py)
    english_in_bg = {p[-1] for p, t in _leaves(LABELS["bg"]) if not CYRILLIC.search(t)}
    assert english_in_bg == {"spellSlots", "pactSlots", "attackVersatile", "attackOffhand", "attackRange"}, english_in_bg


def test_the_english_wording_of_the_spell_slot_labels_is_the_glossary_term():
    g = glossary.load()
    assert LABELS["en"]["spellSlots"] == g["spellSlots"]["en"]


@pytest.mark.parametrize("lang", LANGS)
def test_rules_terms_equal_the_glossary(lang):
    g = glossary.load()
    for key, term in GLOSSARY_LINKS.items():
        assert LABELS[lang][key] == g[term][lang], (lang, key, term)
    for (group, key), term in GLOSSARY_NESTED.items():
        # a word inside a sentence is lower case in the labels, the glossary keeps the case of the source
        assert LABELS[lang][group][key].casefold() == g[term][lang].casefold(), (lang, group, key, term)
    assert g["feet"][lang] in LABELS[lang]["feet"]
    assert g["gold"][lang] in LABELS[lang]["startingGold"]


def test_label_rejects_an_unknown_language():
    with pytest.raises(ValueError):
        label("fr", "unnamed")
    with pytest.raises(ValueError):
        to_markdown({"sheet": {}, "derived": {}}, "fr")
    with pytest.raises(ValueError):
        to_pdf({"sheet": {}, "derived": {}}, "fr")


def test_plural_forms_of_the_short_rest_regain():
    assert label("bg", "shortRestRegains", n=1) == "1 използване се възстановява при кратка почивка (Short Rest)"
    assert label("bg", "shortRestRegains", n=3) == "3 използвания се възстановяват при кратка почивка (Short Rest)"
    assert label("en", "shortRestRegains", n=1) == "1 use regained on a short rest"
    assert label("en", "shortRestRegains", n=2) == "2 uses regained on a short rest"


def test_no_cyrillic_literal_is_left_in_the_exporters():
    """Every Bulgarian word of the exports lives in export_labels.py; comments and docstrings may mention them."""
    for name in ("markdown_export.py", "pdf_export.py", "export_fields.py"):
        tree = ast.parse((SERVER / name).read_text(encoding="utf-8"))
        docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body
                      and isinstance(n.body[0], ast.Expr) and isinstance(n.body[0].value, ast.Constant)}
        bad = [(name, n.lineno, n.value) for n in ast.walk(tree)
               if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
               and CYRILLIC.search(n.value)]
        assert not bad, bad


def test_default_language_is_bulgarian():
    assert export_labels.DEFAULT_LANG == "bg"
    assert export_fields._RECHARGE_WORDS is LABELS["bg"]["recharge"]


# ---- drafts -------------------------------------------------------------------------------------------------------

def _resolution(sid, catalog):
    if sid in HAND:
        return HAND[sid]()
    spec = ALL_SPECS[sid]
    reason = skip_reason(spec)
    if reason:
        pytest.skip(reason)
    draft = build(sid, catalog, resolve) if sid in KITCHEN_SINK else fill(base_draft(spec), catalog, spec["overrides"], resolve)
    draft["name"] = "Hero"  # an ASCII-only draft
    return resolve(draft, catalog)


def _pdf_text(data: bytes) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)


@pytest.mark.parametrize("sid", list(ALL_SPECS) + ["hand-sample", "hand-nameless", "hand-details"])
def test_english_export_of_an_ascii_draft_has_no_cyrillic(catalog, sid):
    res = _resolution(sid, catalog)
    if sid.startswith("hand-"):  # hand-built resolutions carry a Bulgarian name; the data itself is English
        res["sheet"]["name"] = "" if sid == "hand-nameless" else "Hero"
    md = to_markdown(res, "en")
    assert not CYRILLIC.search(md), CYRILLIC.findall(md)[:20]
    assert not CYRILLIC.search(_pdf_text(to_pdf(res, "en")))
    assert CYRILLIC.search(to_markdown(res, "bg"))  # and the Bulgarian export of the same draft really has some


def test_english_nameless_sheet_and_titles(catalog):
    res = HAND["hand-nameless"]()
    assert to_markdown(res, "en").startswith("# Unnamed Character\n")
    assert to_markdown(res, "bg").startswith("# Безименен герой\n")
    assert "Unnamed Character" in _pdf_text(to_pdf(res, "en"))
    assert "Безименен герой" in _pdf_text(to_pdf(res, "bg"))


def test_english_markdown_uses_the_glossary_terms(catalog):
    res = _resolution("monk14", catalog)
    md = to_markdown(res, "en")
    for term in ("## Combat Statistics", "- **Armor Class:**", "- **Hit Points:**", "- **Speed:**", "feet",
                 "- **Proficiency Bonus:**", "## Ability Scores", "## Saving Throws", "## Skills", "## Languages",
                 "## Proficiencies", "## Equipment", "**Level 14 Monk", "**Background:**", "**Species:**"):
        assert term in md, term


def test_bulgarian_spell_slots_keep_their_english_label_and_english_says_spell_slots(catalog):
    res = next(_resolution(s, catalog) for s in KITCHEN_SINK if s.startswith("wizard") or s.startswith("cleric"))
    bg, en = to_markdown(res, "bg"), to_markdown(res, "en")
    assert "**Spell Slots:** ниво 1:" in bg
    assert "**Spell Slots:** level 1:" in en
    assert "Spell Save DC" in en and "DC на спасяването от заклинание (Spell Save DC)" in bg


# ---- byte identity of Bulgarian -------------------------------------------------------------------------------------

@pytest.mark.parametrize("sid", ["hand-sample", "hand-nameless", "hand-details"] + list(KITCHEN_SINK)[:6])
def test_explicit_bg_equals_the_default_and_the_baseline(catalog, sid):
    res = _resolution(sid, catalog)
    stored = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert to_markdown(res, "bg") == to_markdown(res)
    assert normalise_pdf(to_pdf(res, "bg")) == normalise_pdf(to_pdf(res))
    if sid in HAND:
        assert sha(to_markdown(res, "bg")) == stored[sid]["markdown"]
        assert sha(normalise_pdf(to_pdf(res, "bg"))) == stored[sid]["pdf"]


# ---- fonts --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("lang", LANGS)
def test_dejavu_renders_both_scripts(lang, caplog):
    res = HAND["hand-sample"]()
    res["sheet"]["name"] = "Hero Герой – ’×"
    with caplog.at_level("WARNING"):
        data = to_pdf(res, lang)
    assert "glyph" not in caplog.text.lower(), caplog.text
    text = _pdf_text(data)
    assert "Hero Герой – ’×" in text
    assert (re.search("[А-Яа-я]{4}", text.replace("Герой", "")) is not None) == (lang == "bg")  # the labels follow the language, the name stays


# ---- the HTTP route -----------------------------------------------------------------------------------------------

def _draft(name="Torvin Bracewell"):
    draft = {
        "name": name, "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }
    draft["classes"][0]["choices"] = {
        "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"],
        "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
    }
    draft["equipment"]["choices"] = {
        "class:fighter:1:equipment-choice-0": ["chain-mail"],
        "class:fighter:1:equipment-choice-2": ["handaxe"],
        "class:fighter:1:equipment-choice-3": ["explorers-pack"],
    }
    draft["background"]["choices"] = {"background:acolyte:languages": ["dwarvish", "elvish"]}
    draft["species"]["choices"] = {"species:human:languages": ["giant"]}
    return draft


def _body(fmt, resp):
    return _pdf_text(resp.data) if fmt == "pdf" else resp.data.decode("utf-8")


@pytest.mark.parametrize("fmt", ["yaml", "markdown", "pdf"])
@pytest.mark.parametrize("lang", ["bg", "en"])
def test_export_route_for_every_format_and_language(client, fmt, lang):
    resp = client.post(f"/api/export/{fmt}?lang={lang}", json=_draft())
    assert resp.status_code == 200
    assert resp.mimetype == {"yaml": "application/x-yaml", "markdown": "text/markdown", "pdf": "application/pdf"}[fmt]
    assert resp.headers["Content-Disposition"] == "attachment; filename*=UTF-8''Torvin%20Bracewell." + {
        "yaml": "yaml", "markdown": "md", "pdf": "pdf"}[fmt]
    text = _body(fmt, resp)
    if fmt == "yaml":
        assert not CYRILLIC.search(text) and "armorClass" in text  # no localized labels, the same in both languages
    else:
        # T1: the Bulgarian label carries the English term in brackets, so "Armor Class" is looked for outside them
        assert ("Armor Class" in text.replace("(Armor Class, AC)", "")) == (lang == "en")
        assert ("Клас броня (Armor Class, AC)" in text) == (lang == "bg")
        assert (CYRILLIC.search(text) is not None) == (lang == "bg")


@pytest.mark.parametrize("fmt", ["yaml", "markdown", "pdf"])
def test_missing_lang_is_bulgarian_and_identical_to_lang_bg(client, fmt):
    omitted = client.post(f"/api/export/{fmt}", json=_draft())
    bg = client.post(f"/api/export/{fmt}?lang=bg", json=_draft())
    norm = normalise_pdf if fmt == "pdf" else (lambda b: b)
    assert norm(omitted.data) == norm(bg.data)
    if fmt == "markdown":
        assert "Клас броня (Armor Class, AC)" in omitted.data.decode("utf-8")


def test_yaml_is_the_same_in_both_languages(client):
    yaml_bg = client.post("/api/export/yaml?lang=bg", json=_draft()).data
    assert client.post("/api/export/yaml?lang=en", json=_draft()).data == yaml_bg == client.post("/api/export/yaml", json=_draft()).data


@pytest.mark.parametrize("fmt", ["yaml", "markdown", "pdf"])
@pytest.mark.parametrize("bad", ["fr", "", "BG", "bg,en", "english"])
def test_bad_lang_is_a_400(client, fmt, bad):
    resp = client.post(f"/api/export/{fmt}?lang={urllib.parse.quote(bad)}", json=_draft())
    assert resp.status_code == 400
    assert resp.get_json() == {"error": "'lang' must be 'bg' or 'en'"}


@pytest.mark.parametrize("lang,fallback", [("bg", "герой"), ("en", "character"), (None, "character")])
def test_filename_fallback_per_language(client, lang, fallback):
    """No `lang` keeps the file name the route always had; the sheet inside is Bulgarian then."""
    resp = client.post("/api/export/markdown" + (f"?lang={lang}" if lang else ""), json=_draft(name=""))
    assert resp.status_code == 200
    assert resp.headers["Content-Disposition"] == f"attachment; filename*=UTF-8''{urllib.parse.quote(fallback)}.md"
    text = resp.data.decode("utf-8")
    assert text.startswith("# " + ("Unnamed Character" if lang == "en" else "Безименен герой"))


def test_gate_problems_are_still_localized_by_lang(client):
    body = {"name": "x", "ruleset": "mixed"}
    assert client.post("/api/export/pdf?lang=en", json=body).get_json()["problems"][0]["message"] == "Choose a class first."
    assert client.post("/api/export/pdf?lang=bg", json=body).get_json()["problems"][0]["message"] == "Първо изберете клас."


def test_frontend_filename_fallbacks_equal_the_servers():
    root = SERVER.parent / "frontend" / "src" / "copy"
    for lang in LANGS:
        src = (root / f"{lang}.ts").read_text(encoding="utf-8")
        assert re.search(r'fileFallback: "([^"]+)"', src).group(1) == LABELS[lang]["filenameFallback"], lang
