"""SHEET-S5..S8: the fillable sheet PDF (server/sheet_pdf.py)."""
import io
import re
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
            nominal = L.FIELDS_BY_NAME[owner["/T"]].size * L.SCALE
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
    out = subprocess.run(["pdffonts", "-"], input=make("paladin6", "bg", catalog), capture_output=True)
    if out.returncode == 0:
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
