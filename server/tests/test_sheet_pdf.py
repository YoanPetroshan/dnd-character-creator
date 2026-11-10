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
