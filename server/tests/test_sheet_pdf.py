"""SHEET-S5..S8: the fillable sheet PDF (server/sheet_pdf.py)."""
import io
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sheet_data as D  # noqa: E402
import sheet_form as SF  # noqa: E402
import sheet_layout as L  # noqa: E402
import sheet_pdf  # noqa: E402
from catalog.loader import load  # noqa: E402
from engine.resolve import resolve  # noqa: E402
from kitchen_sink import KITCHEN_SINK, build, skip_reason  # noqa: E402

CREATED = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
CYRILLIC = re.compile("[Ѐ-ӿ]")
_cache: dict = {}


@pytest.fixture(scope="module")
def catalog():
    return load()


def resolution(sid, catalog):
    reason = skip_reason(KITCHEN_SINK[sid])
    if reason:
        pytest.skip(reason)
    if sid not in _cache:
        _cache[sid] = resolve(build(sid, catalog, resolve), catalog)
    return _cache[sid]


def make(sid, lang, catalog, created=CREATED):
    return sheet_pdf.to_sheet(resolution(sid, catalog), lang, catalog, created, KITCHEN_SINK[sid]["ruleset"])


def reader(data):
    return PdfReader(io.BytesIO(data))


def metrics_of(r):
    return SF.FontMetrics(next(iter(r.trailer["/Root"]["/AcroForm"]["/DR"]["/Font"].values())).get_object())


def page_text(r, i):
    return r.pages[i].extract_text()


@pytest.mark.parametrize("lang", ("bg", "en"))
def test_page_one_is_a_fillable_a4_page_with_the_values(lang, catalog):
    data = make("paladin6", lang, catalog)
    r = reader(data)
    assert [tuple(round(float(x), 2) for x in p.mediabox) for p in r.pages][0] == (0.0, 0.0, 595.28, 841.89)
    fields = r.get_fields()
    expected = D.build_sheet_data(resolution("paladin6", catalog), catalog, lang, "2014").as_dict()
    page1 = {f.name for f in L.FIELDS if any(w.page == 1 for w in f.widgets)}
    assert page1 <= set(fields)
    for n in page1:
        want = expected[n]
        got = fields[n].get("/V")
        assert (got == ("/Yes" if want else "/Off")) if isinstance(want, bool) else (got or "") == want, n
    assert r.trailer["/Root"]["/AcroForm"]["/NeedAppearances"] == False  # noqa: E712


@pytest.mark.parametrize("lang", ("bg", "en"))
def test_nothing_of_the_reference_artwork_or_footer_is_printed(lang, catalog):
    r = reader(make("paladin6", lang, catalog))
    text = " ".join(page_text(r, i) for i in range(len(r.pages)))
    for banned in ("D&D Beyond", "Wizards", "BEYOND", "Hasbro", "Permission is granted"):
        assert banned.lower() not in text.lower()
    assert ("стр. 1/" if lang == "bg" else "p. 1/") in text
    assert ("Лист на героя (Character Sheet)" if lang == "bg" else "Character Sheet") in text


@pytest.mark.parametrize("lang", ("bg", "en"))
def test_every_value_fits_its_box_at_the_smallest_size(lang, catalog):
    r = reader(make("paladin6", lang, catalog))
    m = metrics_of(r)
    for page in r.pages:
        for a in page.get("/Annots", []):
            a = a.get_object()
            owner = a.get("/Parent", a).get_object() if "/Parent" in a else a
            if owner.get("/FT") != "/Tx" or not owner.get("/V"):
                continue
            x0, y0, x1, y1 = (float(v) for v in a["/Rect"])
            multi = bool(int(owner.get("/Ff", 0)) & 4096)
            nominal = _nominal(owner["/T"])
            _lines, _s, fits = SF.fit_text(m, str(owner["/V"]), x1 - x0, y1 - y0, nominal, multi)
            assert fits, (owner["/T"], owner["/V"])


def test_output_is_deterministic_and_has_no_question_mark_glyphs(catalog):
    a, b = make("paladin6", "bg", catalog), make("paladin6", "bg", catalog)
    assert a == b
    r = reader(a)
    q = metrics_of(r).to_cid["?"]
    for page in r.pages:
        for annot in page.get("/Annots", []):
            ap = annot.get_object()["/AP"]["/N"].get_object()
            if hasattr(ap, "get_data"):
                for h in re.findall(rb"<([0-9A-F]+)> Tj", ap.get_data()):
                    assert q not in [int(h[i:i + 4], 16) for i in range(0, len(h), 4)]


def test_the_invisible_charset_line_covers_the_values_and_fonts_are_embedded(catalog):
    out = None
    if shutil.which("pdffonts"):  # poppler is optional: absent on the CI runner
        out = subprocess.run(["pdffonts", "-"], input=make("paladin6", "bg", catalog), capture_output=True)
    if out is not None and out.returncode == 0:
        lines = out.stdout.decode().splitlines()[2:]
        assert lines and all(" yes yes yes " in ln for ln in lines), lines
    r = reader(make("paladin6", "bg", catalog))
    m = metrics_of(r)
    assert all(ch in m.to_cid for ch in SF.CHARSET + "Кухненска мивка")


def test_a_name_with_characters_outside_the_charset_still_renders(catalog):
    res = {**resolution("paladin6", catalog)}
    res["sheet"] = {**res["sheet"], "name": "Zoë Ünlü ½"}
    r = reader(sheet_pdf.to_sheet(res, "en", catalog, CREATED, "2014"))
    assert r.get_fields()["CharacterName"]["/V"] == "Zoë Ünlü ½"


def test_page_one_speed(catalog):
    res = resolution("paladin6", catalog)
    sheet_pdf.to_sheet(res, "bg", catalog, CREATED, "2014")
    best = min(_time(lambda: sheet_pdf.to_sheet(res, "bg", catalog, CREATED, "2014")) for _ in range(3))
    assert best < 1.0, best


def _time(fn):
    t = time.perf_counter()
    fn()
    return time.perf_counter() - t


# ---------------------------------------------------------------- S6: pages 2-3, flow, equipment, continuation pages
def _flow_words(blocks):
    return " ".join(b.text for b in blocks).split()


def _column_words(r):
    names = sorted(n for n in r.get_fields() if re.fullmatch(r"Features[1-6]|Flow\d+_[123]", n))
    # page order: Features1-6 first, then Flow k columns in order
    names = [n for n in names if n.startswith("Features")] + sorted((n for n in names if n.startswith("Flow")), key=lambda n: tuple(map(int, re.findall(r"\d+", n))))
    words = []
    for n in names:
        words += str(r.get_fields()[n].get("/V") or "").split()
    return names, words


def _fits_everywhere(r):
    m = metrics_of(r)
    for page in r.pages:
        for a in page.get("/Annots", []):
            a = a.get_object()
            owner = a.get("/Parent", a).get_object() if "/Parent" in a else a
            if owner.get("/FT") != "/Tx" or not owner.get("/V"):
                continue
            x0, y0, x1, y1 = (float(v) for v in a["/Rect"])
            nominal = _nominal(owner["/T"])
            _l, _s, fits = SF.fit_text(m, str(owner["/V"]), x1 - x0, y1 - y0, nominal, bool(int(owner.get("/Ff", 0)) & 4096))
            assert fits, (owner["/T"], str(owner["/V"])[:60])


def _nominal(name):
    if name.startswith("Spell"):
        return (8.0 if name.endswith("_Class") else 9.0 if name.endswith(("_Ability", "_SaveDc", "_Attack")) else 6.5) * L.SCALE
    f = L.FIELDS_BY_NAME.get(name)
    if f:
        return f.size * L.SCALE
    return (7.0 if name.startswith(("Flow", "Notes")) else 8.0) * L.SCALE


@pytest.mark.parametrize("sid,lang", (("paladin6", "bg"), ("wizard20-2014", "en"), ("barbarian20-2014", "en"), ("fighter10-2024", "bg")))
def test_the_features_flow_is_lossless_and_fits(sid, lang, catalog):
    res = resolution(sid, catalog)
    data = D.build_sheet_data(res, catalog, lang, KITCHEN_SINK[sid]["ruleset"])
    r = reader(make(sid, lang, catalog))
    _names, words = _column_words(r)
    expected = _flow_words(data.flow)  # the features, the feats and the leftovers of the small boxes
    assert words == expected, "the columns hold exactly the words of the flow, in order"
    _fits_everywhere(r)


def _fat(catalog, extra_features=0, items=0, paragraphs=0):
    res = __import__("copy").deepcopy(resolution("wizard20-2014", catalog))
    sheet = res["sheet"]
    for i in range(extra_features):
        sheet["features"].append({"source": {"kind": "class", "id": "wizard", "label": "Wizard"}, "name": f"Invented Feature {i}", "level": 3})
    sheet["equipment"]["added"] = [{"itemId": "dagger", "name": f"Gear {i}", "qty": 2} for i in range(items)]
    if paragraphs:
        sheet["details"] = {"backstory": "\n\n".join(f"Story {i}. " + "word " * 120 for i in range(paragraphs)), "notes": "n"}
    return res


def test_a_very_long_flow_continues_on_extra_pages_and_loses_nothing(catalog):
    class FatCat:  # every invented feature gets a long description through a fake catalog record
        def __init__(self, base):
            self.__dict__.update(base.__dict__)
            self.features = dict(base.features)
            for i in range(160):
                self.features[f"invented-{i}"] = {"index": f"invented-{i}", "class": {"index": "wizard"}, "name": f"Invented Feature {i}", "level": 3,
                                                   "desc": [f"Paragraph one of {i}. " + "lorem ipsum dolor sit amet " * 30, "Second paragraph. " + "consectetur " * 40]}
        def resolve_spell_id(self, x):
            return x if x in self.spells else None
    cat = FatCat(catalog)
    res = _fat(catalog, extra_features=160)
    data = D.build_sheet_data(res, cat, "en", "2014")
    r = reader(sheet_pdf.to_sheet(res, "en", cat, CREATED, "2014"))
    names, words = _column_words(r)
    assert any(n.startswith("Flow") for n in names), "continuation pages exist"
    flow_words = _flow_words([b for b in data.flow])
    got = " ".join(words)
    # all feature text survives, in order, across page 2, 3 and the continuation pages
    assert got.startswith(" ".join(flow_words[:200])) and " ".join(flow_words) in got
    assert len(r.pages) >= 5
    _fits_everywhere(r)
    assert len(set(r.get_fields())) == len(r.get_fields())


def test_equipment_beyond_the_rows_gets_continuation_pages(catalog):
    res = _fat(catalog, items=150)
    data = D.build_sheet_data(res, catalog, "en", "2014")
    r = reader(sheet_pdf.to_sheet(res, "en", catalog, CREATED, "2014"))
    f = r.get_fields()
    cont = sorted(n for n in f if n.startswith("EqX"))
    assert cont and len(data.equipment_overflow) > 0
    names = [f[n]["/V"] for n in cont if n.endswith("Name") and f[n].get("/V")]
    assert names == [row[0] for row in data.equipment_overflow]
    _fits_everywhere(r)


@pytest.mark.parametrize("lang", ("bg", "en"))
def test_pages_two_and_three_carry_the_shared_identity_and_their_fields(lang, catalog):
    r = reader(make("paladin6", lang, catalog))
    assert len(r.pages) >= 3
    root = r.trailer["/Root"]["/AcroForm"]["/Fields"]
    parents = {a.get_object()["/T"]: a.get_object() for a in root}
    for n in ("ClassLevel", "PlayerName", "Species", "Background", "ExperiencePoints"):
        assert len(parents[n]["/Kids"]) == 3, n
    f = r.get_fields()
    expected = D.build_sheet_data(resolution("paladin6", catalog), catalog, lang, "2014").as_dict()
    for i in range(56):
        assert (f[f"Eq{i}Name"].get("/V") or "") == expected[f"Eq{i}Name"]
    assert (f["CoinsGp"].get("/V") or "") == expected["CoinsGp"]
    assert "Features1" in f and "Features6" in f
    assert len({n for n in f}) == len(f)


# ---------------------------------------------------------------- S7: page 4 and the notes continuation
@pytest.mark.parametrize("lang", ("bg", "en"))
def test_page_four_fields_and_the_shared_character_name(lang, catalog):
    res = __import__("copy").deepcopy(resolution("paladin6", catalog))
    res["sheet"]["details"] = {"alignment": "Lawful Good", "age": "27", "height": "6 ft", "eyes": "grey", "faith": "Pelor",
                               "personalityTraits": "Brave.\n\nLoud.", "ideals": "Honor", "bonds": "My order", "flaws": "Proud",
                               "backstory": "Born in a small village.", "allies": "The Guild", "enemies": "Bandits", "notes": "Remember the key"}
    r = reader(sheet_pdf.to_sheet(res, lang, catalog, CREATED, "2014"))
    f = r.get_fields()
    assert f["BodyAlignment"]["/V"] == "Lawful Good" and f["BodyAge"]["/V"] == "27" and f["BodyFaith"]["/V"] == "Pelor"
    assert f["Personality"]["/V"] == "Brave.\n\nLoud." and f["Ideals"]["/V"] == "Honor" and f["Backstory"]["/V"] == "Born in a small village."
    assert "The Guild" in f["Allies"]["/V"] and "Bandits" in f["Allies"]["/V"] and f["Notes1"]["/V"] == "Remember the key"
    assert f["BodySize"]["/V"] == "Medium"
    assert not any("ortrait" in n for n in f), "the portrait is a bare frame, not a field"
    parents = {a.get_object()["/T"]: a.get_object() for a in r.trailer["/Root"]["/AcroForm"]["/Fields"]}
    assert len(parents["CharacterName"]["/Kids"]) == 4
    last = r.pages[3]
    assert {(a.get_object().get("/T") or a.get_object()["/Parent"]["/T"]) for a in last["/Annots"]} >= {"CharacterName", "Backstory", "Notes2"}
    _fits_everywhere(r)


def test_long_backstory_continues_on_notes_pages_without_loss(catalog):
    res = __import__("copy").deepcopy(resolution("paladin6", catalog))
    paragraphs = [f"Chapter {i}. " + "the story goes on and on " * 40 for i in range(60)]
    res["sheet"]["details"] = {"backstory": "\n\n".join(paragraphs), "notes": "\n\n".join("note " * 100 for _ in range(30))}
    r = reader(sheet_pdf.to_sheet(res, "en", catalog, CREATED, "2014"))
    f = r.get_fields()
    cont = sorted((n for n in f if n.startswith("NotesC")), key=lambda n: tuple(map(int, re.findall(r"\d+", n))))
    assert cont, "continuation pages exist"
    words = (f["Backstory"]["/V"] + "\n\n").split()
    for n in cont:
        words += str(f[n].get("/V") or "").split()
    got = " ".join(words)
    assert got.count("Chapter ") == 60
    assert "Chapter 0." in got and "Chapter 59." in got and got.index("Chapter 5.") < got.index("Chapter 59.")
    assert (got + " " + f["Notes1"]["/V"] + " ").count("note ") == 3000
    assert len(r.pages) >= 6
    _fits_everywhere(r)


def test_every_page_has_its_footer_with_its_number(catalog):
    res = _fat(catalog, extra_features=0, items=150, paragraphs=40)
    r = reader(sheet_pdf.to_sheet(res, "bg", catalog, CREATED, "2014"))
    total = len(r.pages)
    assert total >= 7
    for i, page in enumerate(r.pages, start=1):
        assert f"стр. {i}/{total}" in page.extract_text(), i


def test_the_bytes_depend_on_created_only_not_on_the_clock(catalog):
    first = make("paladin6", "en", catalog)
    time.sleep(1.1)  # a different second: fpdf2 would have stamped the current time (a flaky determinism failure under load)
    assert make("paladin6", "en", catalog) == first


# ---------------------------------------------------------------- S8: spell pages
def _spell_names(r, n):
    f = r.get_fields()
    return [(f[f"Spell{n}_{s:02d}_Name"].get("/V") or "") for s in range(L.SPELL_SLOTS)]


def _spell_pages(r):
    return sorted({int(m.group(1)) for k in r.get_fields() for m in [re.match(r"Spell(\d+)_Class$", k)] if m})


def _many_spells(catalog, count):
    out = []
    for sid, sp in sorted(catalog.spells.items()):
        if 1 <= sp["level"] <= 9 and sp.get("source") in ("SRD", "PHB") and len(out) < count and "xphb" not in sid:
            out.append({"id": sid, "name": sp["name"], "level": sp["level"]})
    return out


def test_120_spells_paginate_without_a_trailing_header_or_a_lost_spell(catalog):
    res = __import__("copy").deepcopy(resolution("wizard5-2014", catalog))
    spells = _many_spells(catalog, 120)
    assert len(spells) == 120
    res["sheet"]["spells"][0]["known"] = spells
    res["sheet"]["spells"][0]["spellbook"] = []
    r = reader(sheet_pdf.to_sheet(res, "en", catalog, CREATED, "2014"))
    pages = _spell_pages(r)
    assert len(pages) >= 3
    seen = []
    for n in pages:
        names = _spell_names(r, n)
        used = [x for x in names if x]
        assert used and not used[-1].startswith("==="), "a level header is never the last row of a page"
        assert names[:len(used)] == used, "rows are consecutive from the top"
        seen += [x for x in used if not x.startswith("===")]
    cantrips = {s["name"] for s in res["sheet"]["spells"][0]["cantrips"]}
    assert sorted(seen) == sorted([s["name"] for s in spells] + sorted(cantrips))
    assert all(n in r.get_fields() for n in (f"Spell{p}_Class" for p in pages))
    _fits_everywhere(r)
    assert len(r.get_fields()) == len(set(r.get_fields()))


def test_spell_rows_carry_the_columns(catalog):
    r = reader(make("paladin6", "en", catalog))
    f = r.get_fields()
    n = _spell_pages(r)[0]
    assert f[f"Spell{n}_Class"]["/V"] == "Paladin" and f[f"Spell{n}_SaveDc"]["/V"] == "14" and f[f"Spell{n}_Ability"]["/V"] == "CHA"
    assert f[f"Spell{n}_Attack"]["/V"] == "+6"
    rows = {f[f"Spell{n}_{s:02d}_Name"].get("/V"): s for s in range(L.SPELL_SLOTS) if f[f"Spell{n}_{s:02d}_Name"].get("/V")}
    s = rows["Bless"]
    cell = lambda k: f[f"Spell{n}_{s:02d}_{k}"].get("/V")  # noqa: E731
    assert (cell("Prep"), cell("Time"), cell("Range"), cell("Comp"), cell("Duration"), cell("Ref"), cell("Source")) == ("O", "1A", "30 ft.", "V,S,M", "C 1 min", "SRD", "Paladin")
    assert rows["=== Level 1 ==="] + 1 == rows["Bless"] or rows["=== Level 1 ==="] < rows["Bless"]


def test_multiclass_casters_get_a_page_per_class(catalog):
    r = reader(make("cleric6-paladin3-2014", "en", catalog))
    f = r.get_fields()
    pages = _spell_pages(r)
    assert [f[f"Spell{n}_Class"]["/V"] for n in pages][:2] == ["Cleric", "Paladin"]
    assert f[f"Spell{pages[0]}_Ability"]["/V"] == "WIS" and f[f"Spell{pages[1]}_Ability"]["/V"] == "CHA"
    text = r.pages[-1].extract_text()
    assert "Spell Slots" in text


def test_pact_magic_slots_are_printed_for_a_warlock(catalog):
    r = reader(make("warlock7-2024", "en", catalog))
    assert "Pact Magic Slots" in "".join(p.extract_text() for p in r.pages)


def test_innate_spells_have_their_own_page(catalog):
    res = __import__("copy").deepcopy(resolution("fighter10-2024", catalog))
    res["sheet"]["innateSpells"] = [{"name": "Misty Step", "uses": "1/long rest", "level": 3}, {"name": "Thaumaturgy", "uses": "at will"}]
    r = reader(sheet_pdf.to_sheet(res, "en", catalog, CREATED, "2024"))
    n = _spell_pages(r)[-1]
    names = _spell_names(r, n)
    assert names[0] == "=== Innate Spells ===" and "Misty Step" in names and "Thaumaturgy" in names
    f = r.get_fields()
    s = names.index("Misty Step")
    assert f[f"Spell{n}_{s:02d}_Prep"]["/V"] == "P" and f[f"Spell{n}_{s:02d}_Source"]["/V"] == "innate"
    assert "1/long rest" in f[f"Spell{n}_{s:02d}_Notes"]["/V"]


def test_a_non_caster_has_no_spell_pages(catalog):
    r = reader(make("fighter10-2024", "en", catalog))
    assert _spell_pages(r) == [] and not [n for n in r.get_fields() if re.match(r"Spell\d+_", n)]
    assert len(r.pages) >= 4


def test_level_20_caster_sheet_speed(catalog):
    res = resolution("wizard20-2014", catalog)
    sheet_pdf.to_sheet(res, "bg", catalog, CREATED, "2014")
    best = min(_time(lambda: sheet_pdf.to_sheet(res, "bg", catalog, CREATED, "2014")) for _ in range(3))
    assert best < 1.5, best


def test_characters_the_font_lacks_become_a_question_mark_not_an_error(catalog):
    res = {**resolution("paladin6", catalog)}
    res["sheet"] = {**res["sheet"], "name": "Жé \U0001F409 龍"}
    r = reader(sheet_pdf.to_sheet(res, "en", catalog, CREATED, "2014"))
    assert r.get_fields()["CharacterName"]["/V"] == "Жé ? ?"
    assert "Жé ? ?" in r.pages[0].extract_text()


# ---------------------------------------------------------------- S11: the look
@pytest.mark.parametrize("lang", ("bg", "en"))
def test_every_frame_title_finds_room_and_stays_readable(lang, catalog):
    res = resolution("wizard20-2014", catalog)
    sheet = sheet_pdf.Sheet(res, lang, catalog, CREATED, "2014")
    sheet.build()
    assert sheet.title_misses == []
    assert sheet_pdf.TITLE_MIN >= 5.0 and sheet_pdf.TITLE_SIZE >= 5.5


def test_the_sheet_uses_white_fields_on_grey_panels():
    assert sheet_pdf.FIELD == (255, 255, 255)
    assert sheet_pdf.PANEL[0] < sheet_pdf.FRAME_FILL[0] < sheet_pdf.FIELD[0]
    # text and captions are dark enough for greyscale printing (contrast against the frame fill >= 4.5:1)
    def lum(c):
        v = [x / 255 for x in c]
        v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    ratio = lambda a, b: (max(lum(a), lum(b)) + 0.05) / (min(lum(a), lum(b)) + 0.05)  # noqa: E731
    for ink in (sheet_pdf.INK, sheet_pdf.TITLE, sheet_pdf.LABEL):
        assert ratio(ink, sheet_pdf.FRAME_FILL) >= 4.5 and ratio(ink, sheet_pdf.FIELD) >= 4.5
    assert ratio(sheet_pdf.INK, sheet_pdf.PANEL) >= 4.5


def test_every_page_registers_its_fonts(catalog):
    """A page that draws text with a font its /Resources lack shows nothing in poppler ("No font in show"); fpdf2 registers a
    font on a page only when the style changes there. Checked with pypdf: every `/Fn size Tf` of a page content stream names a
    font of that page's resources."""
    r = reader(make("wizard20-2014", "bg", catalog))
    for number, page in enumerate(r.pages, start=1):
        fonts = set(page["/Resources"]["/Font"])
        used = set(re.findall(rb"(/F\d+) [\d.]+ Tf", page.get_contents().get_data()))
        assert used and {u.decode() for u in used} <= fonts, (number, used, fonts)
        assert len(fonts) == 2


@pytest.mark.parametrize("lang", ("bg", "en"))
@pytest.mark.parametrize("sid", ("paladin6", "wizard20-2014", "cleric6-paladin3-2014", "warlock7-2024"))
def test_no_drawn_text_is_wider_than_the_room_it_was_given(sid, lang, catalog):
    """Every caption, title and heading is measured with the real font against the width its box / frame allows (at the smallest
    readable size); one that still overflows is recorded by `_Doc.put` and is a defect (a title crossing its frame border)."""
    sheet = sheet_pdf.Sheet(resolution(sid, catalog), lang, catalog, CREATED, KITCHEN_SINK[sid]["ruleset"])
    sheet.build()
    assert sheet.doc.overflows == [], sheet.doc.overflows
    assert sheet.title_misses == []


def test_the_longest_carrying_values_fit_at_six_points_or_more(catalog):
    """`NNNN lb (NNNN,N kg)` in a carrying box (a Strength 30 character: 1800 lb push / drag / lift) at 6 pt (Letter) or more."""
    r = reader(make("paladin6", "bg", catalog))
    m = metrics_of(r)
    for name in ("WeightCarried", "WeightCapacity", "PushDragLift"):
        x0, y0, x1, y1 = L.a4_rect(L.FIELDS_BY_NAME[name].widgets[0].rect)
        for text in ("1234 lb (559,9 kg)", "1800 lb (816,5 kg)", "99 lb (44,9 kg)"):
            _lines, size, fits = SF.fit_text(m, text, x1 - x0, y1 - y0, L.FIELDS_BY_NAME[name].size * L.SCALE, False)
            assert fits and size >= 6.0 * L.SCALE, (name, text, size)


def test_the_spell_save_dc_boxes_hold_three_letter_abilities(catalog):
    m = metrics_of(reader(make("paladin6", "en", catalog)))
    for name in ("SpellDc1Ability", "SpellDc2Ability"):
        x0, y0, x1, y1 = L.a4_rect(L.FIELDS_BY_NAME[name].widgets[0].rect)
        for text in ("CHA", "WIS", "INT", "CON", "STR", "DEX"):
            _l, size, fits = SF.fit_text(m, text, x1 - x0, y1 - y0, L.FIELDS_BY_NAME[name].size * L.SCALE, False)
            assert fits and size >= L.FIELDS_BY_NAME[name].size * L.SCALE - 0.01, (name, text, size)  # not even shrunk


def test_form_fields_have_no_fill_so_a_blue_tint_is_the_viewers_highlight(catalog):
    r = reader(make("paladin6", "bg", catalog))
    for page in r.pages:
        for a in page.get("/Annots", []):
            a = a.get_object()
            assert "/BG" not in a.get("/MK", {}) and "/IC" not in a.get("/MK", {}), a.get("/T")


# ---------------------------------------------------------------- generic geometry audit of everything drawn
def _boxes_hit(a, b, eps=0.25):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def _inside(a, b, eps=0.4):
    return a[0] >= b[0] - eps and a[1] >= b[1] - eps and a[2] <= b[2] + eps and a[3] <= b[3] + eps


AUDIT = (("paladin6", "bg"), ("paladin6", "en"), ("wizard20-2014", "bg"), ("wizard20-2014", "en"),
         ("cleric6-paladin3-2014", "bg"), ("cleric6-paladin3-2014", "en"), ("warlock7-2024", "bg"), ("warlock7-2024", "en"),
         ("barbarian20-2014", "bg"), ("barbarian20-2014", "en"))


@pytest.mark.parametrize("sid,lang", AUDIT)
def test_drawn_texts_never_overlap_each_other_a_frame_border_or_a_field(sid, lang, catalog):
    sheet = sheet_pdf.Sheet(resolution(sid, catalog), lang, catalog, CREATED, KITCHEN_SINK[sid]["ruleset"])
    sheet.build()
    doc = sheet.doc
    assert not doc.overflows and not sheet.title_misses
    texts = doc.texts
    assert len(texts) > 40
    problems = []
    for i, (page, text, box) in enumerate(texts):
        for page2, text2, box2 in texts[i + 1:]:
            if page2 == page and _boxes_hit(box, box2, eps=-0.5):  # clear space between two texts (line pitch of a wrapped caption is the minimum)
                problems.append(f"p{page}: text '{text}' touches or overlaps text '{text2}'")
        for fpage, frect in doc.frames:
            if fpage == page and _boxes_hit(box, frect) and not _inside(box, frect):
                problems.append(f"p{page}: text '{text}' crosses the border of the frame {frect}")
        for f in sheet.fields:
            for w in f.widgets:
                if w.page == page and _boxes_hit(box, w.rect):
                    problems.append(f"p{page}: text '{text}' is drawn over the field {f.name}")
    assert not problems, "\n".join(problems[:25])


@pytest.mark.parametrize("sid,lang", (("paladin6", "bg"), ("wizard20-2014", "en"), ("barbarian20-2014", "bg")))
def test_field_widgets_never_overlap_each_other_on_any_page(sid, lang, catalog):
    sheet = sheet_pdf.Sheet(resolution(sid, catalog), lang, catalog, CREATED, KITCHEN_SINK[sid]["ruleset"])
    sheet.build()
    by_page: dict[int, list] = {}
    for f in sheet.fields:
        for w in f.widgets:
            by_page.setdefault(w.page, []).append((f.name, w.rect))
    for page, items in by_page.items():
        for i, (na, a) in enumerate(items):
            for nb, b in items[i + 1:]:
                assert not _boxes_hit(a, b), (page, na, nb)


def test_the_audit_helpers_see_an_overlap():
    doc = sheet_pdf._Doc()
    doc.add_page()
    doc.put("ABCDEFGH", 100, 100, 6, "left", 60, bold=True)
    doc.put("Успехи", 102, 100, 6, "left", 40)
    assert _boxes_hit(doc.texts[0][2], doc.texts[1][2])
    doc.box((90, 90, 130, 130), 1.0, color=(0, 0, 0))
    assert doc.frames and not _inside(doc.texts[0][2], doc.frames[0][1])


# ---------------------------------------------------------------- S12: long identity values stay readable and inside their boxes
LONG = {
    "species": [{"id": "x", "name": "Half-Elf", "subspecies": {"name": "Variant; Moon Elf or Sun Elf Descent"}, "variant": None, "size": "Medium"},
                {"id": "x", "name": "Half-Orc", "subspecies": {"name": "Variant; Mark of Finding"}, "variant": None, "size": "Medium"},
                {"id": "x", "name": "Elf (Kaladesh)", "subspecies": {"name": "Bishatar and Tirahar"}, "variant": None, "size": "Medium"},
                {"id": "x", "name": "Dragonborn (Chromatic)", "subspecies": None, "variant": None, "size": "Medium"}],
    "background": ["Variant City Watch (Investigator)", "Celebrity Adventurer's Scion", "Emerald Enclave Caretaker", "Mulhorandi Tomb Raider"],
    "classes": [[{"id": "barbarian", "name": "Barbarian", "level": 7, "subclass": {"name": "Path of the Ancestral Guardian"}},
                 {"id": "fighter", "name": "Fighter", "level": 5, "subclass": {"name": "Purple Dragon Knight (Banneret)"}},
                 {"id": "sorcerer", "name": "Sorcerer", "level": 3, "subclass": {"name": "Way of the Ascendant Dragon"}}],
                [{"id": "wizard", "name": "Wizard", "level": 12, "subclass": {"name": "School of Evocation"}},
                 {"id": "cleric", "name": "Cleric", "level": 8, "subclass": {"name": "Twilight Domain"}}]],
}


@pytest.mark.parametrize("lang", ("bg", "en"))
def test_the_longest_identity_values_fit_their_boxes_at_a_readable_size(lang, catalog):
    base = resolution("paladin6", catalog)
    cases = [("Species", lambda sh, x: sh.update(species=x), LONG["species"]),
             ("Background", lambda sh, x: sh.update(background={"id": "b", "name": x}), LONG["background"]),
             ("ClassLevel", lambda sh, x: sh.update(classes=x), LONG["classes"])]
    for field, setter, values in cases:
        for value in values:
            res = {**base, "sheet": {**base["sheet"]}}
            setter(res["sheet"], value)
            r = reader(sheet_pdf.to_sheet(res, lang, catalog, CREATED, "2014"))
            m = metrics_of(r)
            f = L.FIELDS_BY_NAME[field]
            for w in f.widgets:
                x0, y0, x1, y1 = L.a4_rect(w.rect)
                text = r.get_fields()[field]["/V"]
                _lines, size, fits = SF.fit_text(m, text, x1 - x0, y1 - y0, f.size * L.SCALE, False)
                assert fits and size >= 5.4 * L.SCALE, (field, text, round(size / L.SCALE, 2))


def test_a_long_value_does_not_change_the_width_pdfkit_needs(catalog):
    """Preview (PDFKit) lays a form field's text out in the box minus about 3 pt and wraps / hides the rest: the fit pad is that."""
    assert SF.PAD >= 3.5  # a 3-character value like +11 in an 18.5 pt box lost its last digit at 3.2
    r = reader(make("paladin6", "en", catalog))
    f = r.get_fields()
    m = metrics_of(r)
    for name in ("Species", "ClassLevel", "SkillAcrobatics", "WeightCarried", "Initiative"):
        w = L.FIELDS_BY_NAME[name].widgets[0]
        x0, y0, x1, y1 = L.a4_rect(w.rect)
        text = str(f[name].get("/V") or "")
        _l, size, fits = SF.fit_text(m, text, x1 - x0, y1 - y0, L.FIELDS_BY_NAME[name].size * L.SCALE, False)
        assert fits and m.width(text, size) <= x1 - x0 - 2 * 3.5 + 0.01, name


def test_saves_are_dot_checkboxes_and_skill_marks_are_letters_that_fit_their_circle(catalog):
    r = reader(make("wizard5-2024", "en", catalog))
    f = r.get_fields()
    sheet = resolution("wizard5-2024", catalog)["sheet"]
    assert sheet["expertiseSkills"], "the draft has expertise"
    for page in r.pages:
        for a in page.get("/Annots", []):
            a = a.get_object()
            name = a.get("/T") or ""
            if name.startswith("Save") and name.endswith("Mark"):
                assert set(a["/AP"]["/N"]) == {"/Yes", "/Off"}
                on = a["/AP"]["/N"]["/Yes"].get_object().get_data()
                assert b" c f" in on and b" l S" not in on, name  # a filled dot, not the cross
    for skill in sheet["expertiseSkills"]:
        field = "Skill" + "".join(w.capitalize() for w in skill.replace("skill-", "").split("-"))
        assert f[field + "Mark"]["/V"] == "E" and f[field + "Mark"]["/FT"] == "/Tx", field
    assert not [n for n in f if n.endswith("Expert")]
    m = metrics_of(r)
    for name in [f"Skill{s}Mark" for s in L.SKILLS]:
        x0, y0, x1, y1 = L.a4_rect(L.FIELDS_BY_NAME[name].widgets[0].rect)
        for ch in ("P", "E"):
            _l, size, fits = SF.fit_text(m, ch, x1 - x0, y1 - y0, L.FIELDS_BY_NAME[name].size * L.SCALE, False)
            assert fits and size >= L.FIELDS_BY_NAME[name].size * L.SCALE - 0.01, (name, ch)  # not even shrunk
