"""W9: export completeness audit.

For every KITCHEN_SINK draft (all rulesets) plus a few long-content drafts, every leaf of
``resolution["sheet"]`` and ``resolution["derived"]`` must reach BOTH the Markdown and the PDF text, or be listed in
``EXPORT_OMITTED`` with a reason. (YAML is a full dump of the same keys; test_export_fields.py covers that.)

How a leaf is checked (text is whitespace-collapsed and case-folded, so PDF line wraps do not matter):

* string: must occur in the text; ``FORMATTED`` maps id-like leaves to the Bulgarian label the exporters print.
* number: the number (``+3``, ``x8`` and ``-1`` forms accepted) must occur as a token; inside a list item that has a
  ``name`` the token must occur within 40 characters before to 400 after that name (``IMPLIED_NUMBER``: quantity 1). A handful of scalars are checked against their
  exact labelled line (``STRICT_SCALARS``). A bare number match is weak by nature, so the labelled checks and the
  per-feature tests in test_export_fields.py carry the precision.
* ``False`` and ``None`` print nothing by design and are skipped. ``True`` must print (``FLAG_TEXT``) or be listed.

``EXPORT_OMITTED``: path pattern -> "category: reason". ``*`` is one path segment, ``**`` any depth, list items are
``[]`` and numeric dict keys are ``#``. An entry that matches no leaf in any audited draft fails as stale.
"""
from __future__ import annotations

import io
import re
from collections import Counter

import pytest
from pypdf import PdfReader

import export_fields
import pdf_export
from export_labels import LABELS, label, word
from catalog.loader import load
from catalog.reference_data import LANGUAGE_NAMES, SKILL_NAMES, proficiency_label
from engine.resolve import resolve
from kitchen_sink import KITCHEN_SINK, _sub, base_draft, build, fill, skip_reason
from markdown_export import to_markdown
from pdf_export import to_pdf

_ID = "id: machine id; the human name next to it is printed"
_IDLIST = "id: machine id list; the human names are printed from the matching feats/spells/items entries"
_SRC = "id: source reference (kind/id) of a feature or resource; its label/name is printed"
_FLAG = "flag: boolean that only drives engine/UI behaviour; the visible effect is already in the printed numbers"

EXPORT_OMITTED: dict[str, str] = {
    # ---- machine ids (the YAML carries them; the sheet prints the names)
    "sheet.background.id": _ID, "sheet.species.id": _ID, "sheet.species.variant.id": _ID,
    "sheet.classes.[].subclass.id": _ID,
    "sheet.feats.[].id": _ID, "sheet.feats.[].origin": "id: where the feat came from (internal enum); the feat name is printed",
    "sheet.grantedFeats.[]": _IDLIST,
    "sheet.features.[].source.id": _SRC, "sheet.features.[].source.kind": _SRC,
    "sheet.equipment.granted.[].itemId": _ID, "sheet.equipment.chosen.[].itemId": _ID,
    "sheet.equipment.added.[].itemId": _ID,
    "sheet.equipment.chosen.[].contents.[].itemId": _ID, 
    "sheet.equipment.slots.armor.[].itemId": _ID, "sheet.equipment.slots.hands.[].itemId": _ID,
    "sheet.equipment.slots.shield.[].itemId": _ID,
    "sheet.equipment.slots.current.armor": "id: the worn armor id; the 'Носено' line prints its name",
    "sheet.equipment.slots.current.shield": "implied: the shield in use follows the '(екипиран)' tag and the 'Носено' line, which print when set",
    "sheet.weaponMasteries.[].itemId": _ID,
    "sheet.innateSpells.[].spellId": _ID, "sheet.innateSpells.[].featId": _ID,
    "sheet.spells.[].cantrips.[].id": _ID, "sheet.spells.[].known.[].id": _ID, "sheet.spells.[].spellbook.[].id": _ID,
    "sheet.spells.[].mysticArcanum.[].id": _ID, "sheet.spells.[].pactOfTheTome.[].id": _ID,
    "sheet.spells.[].spellMastery.[].id": _ID, "sheet.spells.[].signatureSpells.[].id": _ID,
    "sheet.spells.[].alwaysPrepared.[].id": _ID,
    "derived.attacks.[].itemId": _ID,
    "derived.classResources.[].id": _ID, "derived.classResources.[].source.id": _SRC,
    "derived.classResources.[].source.kind": _SRC,
    "derived.featResources.[].id": _ID, "derived.featResources.[].featId": _ID, "derived.featResources.[].source.id": _SRC,
    "derived.featResources.[].source.kind": _SRC,
    "derived.speciesResources.[].id": _ID, "derived.speciesResources.[].speciesId": _ID,
    "derived.speciesResources.[].traitId": _ID, "derived.speciesResources.[].source.id": _SRC,
    "derived.speciesResources.[].source.kind": _SRC,
    "derived.classResources.[].details.spell": "id: spell id inside a resource's details; the resource name carries the spell",
    # ---- flags / presentation data of equipment slots and attacks
    "sheet.equipment.slots.hands.[].kind": "slot: kind of a hand-slot candidate (weapon/shield), UI picker data",
    "sheet.equipment.slots.hands.[].twoHanded": _FLAG,
    "derived.attacks.[].proficient": _FLAG,
    # ---- spell level of a cantrip is 0 by definition; the 'Трикове' heading says so
    "sheet.spells.[].cantrips.[].level": "implied: cantrips are listed under the 'Трикове' heading, level 0 by definition",
}

# Everything below depends on the export language: the words come from export_labels (XL), never from literals.
LANGS = ("bg", "en")


def _recharge(lang):
    return lambda v: [LABELS[lang]["recharge"][v]]


def formatted(lang: str) -> dict:
    """A value the exporters print through a lookup/translation instead of verbatim: pattern -> value -> printed alternatives."""
    dmg = LABELS[lang]["damage"]
    return {
        "sheet.expertiseSkills.[]": lambda v: [export_fields.expertise_label(v)],
        "sheet.proficiencies.skills.[]": lambda v: [SKILL_NAMES.get(v, v)],
        "sheet.proficiencies.languages.[]": lambda v: [LANGUAGE_NAMES.get(v, v)],
        "sheet.proficiencies.armor.[]": lambda v: [proficiency_label(v)],
        "sheet.proficiencies.weapons.[]": lambda v: [proficiency_label(v)],
        "sheet.proficiencies.tools.[]": lambda v: [proficiency_label(v)],
        "derived.classResources.[].recharge": _recharge(lang),
        "derived.featResources.[].recharge": _recharge(lang),
        "derived.speciesResources.[].recharge": _recharge(lang),
        "derived.classResources.[].details.resistances.[]": lambda v: [dmg.get(v, v), label(lang, "resAll")],
    }


def flag_text(lang: str) -> dict:
    """A True flag that the exporters print as a fixed phrase."""
    return {
        "derived.stealthDisadvantage": label(lang, "stealthDisadvantage"),
        "derived.carryingCapacity.overCapacity": label(lang, "overCapacity").strip(" ()"),
        "sheet.equipment.*.[].equipped": label(lang, "equipped"),
        "derived.classResources.[].unlimited": label(lang, "unlimited"),
        "derived.classResources.[].details.fly": word(lang, "modes", "fly"),
        "derived.classResources.[].details.swim": word(lang, "modes", "swim"),
        "derived.classResources.[].details.onShortRest": label(lang, "onShortRest"),
        "derived.classResources.[].details.bonusActionRegainsOne": label(lang, "bonusActionRegainsOne"),
    }


def strict_scalars(lang: str) -> dict:
    """Scalars checked against the exact label the exporters print: path -> printed template."""
    return {
        "derived.armorClass": label(lang, "armorClass") + ": {}",
        "derived.hitPointMax": label(lang, "hitPoints") + ": {}",
        "derived.speed": label(lang, "speed") + ": " + label(lang, "feet", n="{}"),
        "derived.passivePerception": label(lang, "passivePerception") + ": {}",
        "derived.passiveInsight": label(lang, "passiveInsight") + ": {}",
        "derived.passiveInvestigation": label(lang, "passiveInvestigation") + ": {}",
        "derived.carryingCapacity.carried": label(lang, "secCarrying") + " {}/",
        "derived.carryingCapacity.capacity": "/{} lb",
        "sheet.level": label(lang, "level", level="{}"),
        "sheet.startingGold": label(lang, "startingGold", n="{}"),
    }


FORMATTED, FLAG_TEXT, STRICT_SCALARS = formatted("bg"), flag_text("bg"), strict_scalars("bg")  # the keys are language independent
# Numbers the exporters leave out because they are the default: pattern -> the value that is implied.
IMPLIED_NUMBER = {"**.qty": 1}  # quantity 1 prints no 'x1' tag


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _pattern(pat: str) -> re.Pattern:
    out = re.escape(pat).replace(r"\*\*", ".+").replace(r"\*", "[^.]+")
    return re.compile(out + "$")


def _leaves(obj, path):
    if isinstance(obj, dict):
        for k, v in obj.items():
            seg = "#" if str(k).isdigit() else str(k)
            yield from _leaves(v, path + [seg])
    elif isinstance(obj, list):
        for v in obj:
            yield from _leaves(v, path + ["[]"])
    else:
        yield ".".join(path), obj


def _leaves_with_parent(obj, path, parent=None):
    if isinstance(obj, dict):
        for k, v in obj.items():
            seg = "#" if str(k).isdigit() else str(k)
            yield from _leaves_with_parent(v, path + [seg], obj)
    elif isinstance(obj, list):
        for v in obj:
            yield from _leaves_with_parent(v, path + ["[]"], parent)
    else:
        yield ".".join(path), obj, parent


def _lookup(table: dict, path: str):
    for pat, val in table.items():
        if _pattern(pat).match(path):
            return val
    return None


def _number_token(value) -> re.Pattern:
    text = re.escape(str(abs(value)) if isinstance(value, int) else str(value))
    sign = r"-" if value < 0 else r"[+x×]?"
    return re.compile(r"(?<![\w.])" + sign + text + r"(?![\w])")


def _has_number(text: str, value, name: str | None) -> bool:
    token = _number_token(value)
    if name:
        key = _norm(name)
        start = 0
        while (i := text.find(key, start)) != -1:
            if token.search(text[max(0, i - 40):i + 400 + len(key)]):  # "Ниво 14 Monk" puts the level before the name
                return True
            start = i + 1
        return False
    return bool(token.search(text))


def _pdf_text(res, lang="bg") -> str:
    return _norm("\n".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res, lang))).pages))


def audit(res: dict, lang: str = "bg") -> tuple[list[str], set[str]]:
    """(failures, every leaf path seen) for one resolution, exported in `lang`."""
    md, pdf = _norm(to_markdown(res, lang).replace("**", "")), _pdf_text(res, lang)
    FORMATTED, FLAG_TEXT, STRICT_SCALARS = formatted(lang), flag_text(lang), strict_scalars(lang)
    failures, seen = [], set()
    for section in ("sheet", "derived"):
        for path, value, parent in _leaves_with_parent(res[section], [section]):
            seen.add(path)
            if _lookup(EXPORT_OMITTED, path) is not None:
                continue
            if value is None or value is False:
                continue
            for label, text in (("Markdown", md), ("PDF", pdf)):
                if value is True:
                    phrase = _lookup(FLAG_TEXT, path)
                    ok = phrase is not None and _norm(phrase) in text
                elif isinstance(value, str):
                    alts = _lookup(FORMATTED, path)
                    ok = any(_norm(a) in text for a in (alts(value) if alts else [value]))
                else:
                    if _lookup(IMPLIED_NUMBER, path) == value:
                        continue
                    strict = STRICT_SCALARS.get(path)
                    name = parent.get("name") if isinstance(parent, dict) else None
                    ok = (_norm(strict.format(value)) in text if strict
                          else _has_number(text, value, name if isinstance(name, str) else None))
                if not ok:
                    failures.append(f"{path} = {value!r} missing from the {label}")
    return failures, seen


# ---- drafts: every kitchen sink plus long-content ones (not golden cases, so not in KITCHEN_SINK)
_WL_INV_2024 = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
LONG_DRAFTS = {
    "bard20-2014": _sub("bard", 20, "2014", marks=("classes",)),
    "wizard20-spellbook-2014": _sub("wizard", 20, "2014", marks=("classes",)),
    "paladin20-watchers-mixed": _sub("paladin", 20, "mixed", sub="watchers-tce", marks=("classes",)),
    "warlock20-2024": _sub("warlock", 20, "2024", marks=("classes", "official", "spells"), overrides={}),
    "fighter19-feat-resources": _sub("fighter", 19, "mixed", marks=("classes", "official"), feats=True, overrides={
        "class:fighter:4:asi": ["feat:lucky-phb"], "class:fighter:6:asi": ["feat:martial-adept-phb"],
        "class:fighter:8:asi": ["feat:metamagic-adept-tce"], "class:fighter:12:asi": ["feat:second-chance-xge"],
        "class:fighter:14:asi": ["feat:fade-away-xge"], "class:fighter:16:asi": ["feat:orcish-fury-xge"],
        "class:fighter:19:asi": ["feat:mage-slayer-xphb"]}),
}
ALL_SPECS = {**KITCHEN_SINK, **LONG_DRAFTS}
_RES: dict[str, dict] = {}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _resolution(sid, catalog):
    spec = ALL_SPECS[sid]
    reason = skip_reason(spec)
    if reason:
        pytest.skip(reason)
    if sid not in _RES:
        draft = build(sid, catalog, resolve) if sid in KITCHEN_SINK else fill(base_draft(spec), catalog, spec["overrides"], resolve)
        _RES[sid] = resolve(draft, catalog)
    return _RES[sid]


_AUDITS: dict[tuple[str, str], tuple[list[str], set[str]]] = {}


def _audit(sid, catalog, lang="bg"):
    if (sid, lang) not in _AUDITS:
        _AUDITS[sid, lang] = audit(_resolution(sid, catalog), lang)
    return _AUDITS[sid, lang]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("sid", list(ALL_SPECS))
def test_every_sheet_and_derived_leaf_reaches_markdown_and_pdf(catalog, sid, lang):
    failures, _ = _audit(sid, catalog, lang)
    assert not failures, f"{sid} [{lang}]:\n" + "\n".join(sorted(set(failures))[:40])


def test_export_omitted_has_no_stale_entries(catalog):
    seen: set[str] = set()
    for sid, spec in ALL_SPECS.items():
        if skip_reason(spec):
            pytest.skip("5etools data missing: the stale check needs every draft")
        seen |= _audit(sid, catalog)[1]
    stale = [pat for pat in EXPORT_OMITTED if not any(_pattern(pat).match(p) for p in seen)]
    for pat in list(FLAG_TEXT) + list(FORMATTED) + list(STRICT_SCALARS):
        if not any(_pattern(pat).match(p) for p in seen):
            stale.append(pat)
    assert not stale, f"stale allowlist entries: {stale}"
    assert all(isinstance(r, str) and ": " in r for r in EXPORT_OMITTED.values())


@pytest.mark.parametrize("lang", LANGS)
def test_the_audit_catches_a_missing_leaf(catalog, lang):
    """The audit must fail on a value that no exporter prints."""
    res = _resolution("monk14", catalog)
    broken = {"sheet": res["sheet"], "derived": {**res["derived"], "carryingCapacity": {**res["derived"]["carryingCapacity"], "invented": "Zzyzx-Marker"}}}
    failures, _ = audit({**res, **broken}, lang)
    assert any("Zzyzx-Marker" in f for f in failures)


def test_export_omitted_summary(catalog):
    """Documents the allowlist size by category (printed with -s; asserts the categories stay known)."""
    cats = Counter(r.split(":")[0] for r in EXPORT_OMITTED.values())
    assert set(cats) <= {"id", "flag", "slot", "implied"}, cats


# ---- PDF layout with long content
class _CellSpy:
    """Records every fpdf cell that would run past the right margin (a cell never wraps, multi_cell does)."""

    def __init__(self, monkeypatch):
        self.overflow: list[str] = []
        original = pdf_export.FPDF.cell
        spy = self

        def cell(pdf, w=None, h=None, text="", *args, **kwargs):
            width = pdf.get_string_width(text)
            room = (pdf.w - pdf.r_margin - pdf.x) if not w else w
            if width > room + 0.01:
                spy.overflow.append(f"{text[:60]!r} {width:.0f} > {room:.0f}")
            return original(pdf, w, h, text, *args, **kwargs)

        monkeypatch.setattr(pdf_export.FPDF, "cell", cell)


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("sid", list(LONG_DRAFTS))
def test_long_drafts_span_pages_without_cut_or_dropped_lines(catalog, sid, lang, monkeypatch, caplog):
    res = _resolution(sid, catalog)
    spy = _CellSpy(monkeypatch)
    with caplog.at_level("WARNING"):
        data = to_pdf(res, lang)
    pages = PdfReader(io.BytesIO(data)).pages
    assert len(pages) >= 2, "a long draft should span several pages"
    assert "glyph" not in caplog.text.lower(), caplog.text
    assert not spy.overflow, spy.overflow
    text = _norm("\n".join(p.extract_text() for p in pages))
    names = [export_fields.resource_line(r, lang) for key in ("classResources", "featResources", "speciesResources")
             for r in res["derived"][key]]
    for cs in res["sheet"]["spells"]:
        for key in ("cantrips", "known", "spellbook", "mysticArcanum", "spellMastery", "signatureSpells", "pactOfTheTome"):
            names += [s["name"] for s in cs.get(key) or []]
    names += [f["name"] for f in res["sheet"]["features"]] + [f["name"] for f in res["sheet"]["feats"]]
    assert names
    missing = [n for n in names if _norm(n) not in text]
    assert not missing, missing[:10]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("sid", list(KITCHEN_SINK))
def test_no_cell_runs_past_the_page_edge(catalog, sid, lang, monkeypatch):
    spy = _CellSpy(monkeypatch)
    to_pdf(_resolution(sid, catalog), lang)
    assert not spy.overflow, spy.overflow


@pytest.mark.parametrize("lang", LANGS)
def test_long_user_text_in_headings_does_not_run_off_the_page(catalog, lang, monkeypatch):
    res = _resolution("monk14", catalog)
    res = {**res, "sheet": {**res["sheet"], "name": "Дългото име на един герой, който просто не иска да свърши никога " * 2}}
    spy = _CellSpy(monkeypatch)
    to_pdf(res, lang)
    assert not spy.overflow, spy.overflow


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("sid", list(LONG_DRAFTS) + ["monk14"])
def test_special_characters_render_in_long_drafts(catalog, sid, lang, caplog):
    res = _resolution(sid, catalog)
    res = {**res, "sheet": {**res["sheet"], "name": "Дракон × Герой’s – Ъгъл"}}
    with caplog.at_level("WARNING"):
        text = _pdf_text(res, lang)
    assert "glyph" not in caplog.text.lower(), caplog.text
    assert "дракон × герой’s – ъгъл" in text


def test_long_drafts_really_are_long(catalog):
    """Guards the fixtures: the drafts must keep the volume the layout checks are about."""
    wl = _resolution("warlock20-2024", catalog)
    inv = next(f for f in wl["sheet"]["features"] if f["name"] == "Eldritch Invocations")
    assert len(inv["choice"]) == 10
    assert len(_resolution("fighter19-feat-resources", catalog)["derived"]["featResources"]) >= 5
    assert len(_resolution("bard20-2014", catalog)["sheet"]["spells"][0]["known"]) >= 20
    assert len(_resolution("wizard20-spellbook-2014", catalog)["sheet"]["spells"][0]["spellbook"]) >= 40
    assert sum(1 for r in _resolution("paladin20-watchers-mixed", catalog)["derived"]["classResources"]
               if (r.get("details") or {}).get("note")) >= 1
