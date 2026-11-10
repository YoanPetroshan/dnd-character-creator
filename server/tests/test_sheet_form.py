"""SHEET-S3: the pypdf form step (server/sheet_form.py)."""
import io
import logging
import re
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fpdf import FPDF
from fpdf.enums import TextMode
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sheet_form as SF  # noqa: E402
import sheet_layout as L  # noqa: E402
from perf_helpers import assert_fast, measure  # noqa: E402

FONTS = Path(L.__file__).resolve().parent / "assets" / "fonts"
CREATED = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)


def base_pdf(pages=5, extra_charset="", bold=True):
    pdf = FPDF(format="A4", unit="pt")
    pdf.set_auto_page_break(False)
    pdf.set_creation_date(CREATED)
    pdf.add_font("DejaVu", "", str(FONTS / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
    for i in range(pages):
        pdf.add_page()
        if bold:
            pdf.set_font("DejaVu", "B", 10)
            pdf.cell(50, 10, "Title")
    pdf.page = 1
    pdf.set_font("DejaVu", "", 6)
    pdf.set_xy(5, 5)
    with pdf.local_context(text_mode=TextMode.INVISIBLE):
        pdf.cell(0, 6, SF.charset_for([extra_charset]) if extra_charset else SF.CHARSET)
    return bytes(pdf.output())


def fields(*names):
    return [L.FIELDS_BY_NAME[n] for n in names]


SAMPLE = ("CharacterName", "ClassLevel", "AbilityStr", "Actions1", "Inspiration", "DeathSuccess1", "Initiative")
VALUES = {
    "CharacterName": "Иван Петров",
    "ClassLevel": "Паладин 6 – „Клетва“",
    "AbilityStr": "16",
    "Actions1": "Първи ред.\nВторият ред е достатъчно дълъг, за да се пренесе на нов ред вътре в полето за действия, и още малко.",
    "Inspiration": True,
    "DeathSuccess1": False,
    "Initiative": "+3",
}


def built(values=VALUES, names=SAMPLE, created=CREATED):
    return SF.apply_form(base_pdf(), fields(*names), values, created)


def _ap_texts(reader):
    """name -> list of decoded lines of every text appearance stream (the inverse of the encoding)."""
    font = next(iter(reader.trailer["/Root"]["/AcroForm"]["/DR"]["/Font"].values())).get_object()
    metrics = SF.FontMetrics(font)
    out = {}
    for page in reader.pages:
        for a in page.get("/Annots", []):
            a = a.get_object()
            name = a.get("/T") or a["/Parent"].get_object()["/T"]
            ap = a["/AP"]["/N"].get_object()
            if not hasattr(ap, "get_data"):
                continue
            data = ap.get_data().decode("latin-1")
            out.setdefault(name, []).append([metrics.decode(h) for h in re.findall(r"<([0-9A-F]+)> Tj", data)])
    return out, metrics


def test_read_back_values_flags_and_widgets():
    r = PdfReader(io.BytesIO(built()))
    f = r.get_fields()
    assert set(f) == set(SAMPLE)
    assert f["CharacterName"]["/V"] == "Иван Петров" and f["ClassLevel"]["/V"] == "Паладин 6 – „Клетва“"
    assert f["Initiative"]["/V"] == "+3" and f["AbilityStr"]["/V"] == "16"
    assert f["Actions1"]["/Ff"] == 4096 and f["ClassLevel"]["/Ff"] == 0
    pages = {i: [(a.get_object().get("/T") or a.get_object()["/Parent"]["/T"]) for a in p["/Annots"]] for i, p in enumerate(r.pages) if "/Annots" in p}
    assert sorted(pages[0]) == sorted(SAMPLE)
    assert pages[1] == ["CharacterName", "ClassLevel"] and pages[3] == ["CharacterName"] and pages[2] == ["CharacterName", "ClassLevel"] and 4 not in pages
    # the shared identity field is ONE field with a widget per page (1-4)
    cn = [a.get_object() for a in r.trailer["/Root"]["/AcroForm"]["/Fields"] if a.get_object()["/T"] == "CharacterName"]
    assert len(cn) == 1 and len(cn[0]["/Kids"]) == 4
    centered = next(a.get_object() for a in r.trailer["/Root"]["/AcroForm"]["/Fields"] if a.get_object()["/T"] == "AbilityStr")
    assert centered["/Q"] == 1
    assert [float(x) for x in centered["/Rect"]] == pytest.approx(L.a4_rect(L.FIELDS_BY_NAME["AbilityStr"].widgets[0].rect), abs=0.001)


def test_checkboxes_have_state_and_both_appearance_streams():
    r = PdfReader(io.BytesIO(built()))
    f = r.get_fields()
    assert f["Inspiration"]["/V"] == "/Yes" and f["DeathSuccess1"]["/V"] == "/Off"
    for page in r.pages:
        for a in page.get("/Annots", []):
            a = a.get_object()
            if a.get("/T") in ("Inspiration", "DeathSuccess1"):
                assert set(a["/AP"]["/N"]) == {"/Yes", "/Off"}
                assert a["/AS"] == a["/V"]
                assert a["/AP"]["/N"]["/Yes"].get_object().get_data().strip().endswith(b"Q")
                assert a["/AP"]["/N"]["/Off"].get_object().get_data() == b""


def test_cyrillic_is_encoded_through_the_font_not_replaced_and_nothing_warns(caplog):
    caplog.set_level(logging.WARNING)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        data = built()
    assert [rec for rec in caplog.records if rec.name.startswith("pypdf")] == []
    r = PdfReader(io.BytesIO(data))
    texts, metrics = _ap_texts(r)
    assert texts["CharacterName"] == [["Иван Петров"]] * 4
    assert texts["ClassLevel"] == [["Паладин 6 – „Клетва“"]] * 3
    q = metrics.to_cid["?"]
    for name, widgets in texts.items():
        for lines in widgets:
            for line in lines:
                assert "?" not in line and q is not None  # no glyph code of "?" in a value without a question mark
    raw = b"".join(a.get_object()["/AP"]["/N"].get_object().get_data() for p in r.pages for a in p.get("/Annots", [])
                   if hasattr(a.get_object()["/AP"]["/N"].get_object(), "get_data"))
    for hexstr in re.findall(rb"<([0-9A-F]+)> Tj", raw):
        codes = [int(hexstr[i:i + 4], 16) for i in range(0, len(hexstr), 4)]
        assert q not in codes


def test_acroform_dr_font_is_the_type0_dejavu_subset_and_appearances_are_final():
    r = PdfReader(io.BytesIO(built()))
    af = r.trailer["/Root"]["/AcroForm"]
    assert af["/NeedAppearances"] is False or af["/NeedAppearances"] == False  # noqa: E712
    font = af["/DR"]["/Font"]["/DejaVu"].get_object()
    assert font["/Subtype"] == "/Type0" and font["/Encoding"] == "/Identity-H"
    assert "DejaVuSans" in font["/BaseFont"] and "Bold" not in font["/BaseFont"]
    assert af["/DA"].startswith("/DejaVu")
    assert b"NeedAppearances true" not in built()


def test_multiline_is_pre_wrapped_in_the_appearance_but_v_keeps_the_original():
    r = PdfReader(io.BytesIO(built()))
    assert r.get_fields()["Actions1"]["/V"] == VALUES["Actions1"]
    texts, metrics = _ap_texts(r)
    lines = texts["Actions1"][0]
    assert len(lines) >= 3 and lines[0] == "Първи ред."
    assert " ".join(lines[1:]) == VALUES["Actions1"].split("\n")[1]
    w = L.a4_rect(L.FIELDS_BY_NAME["Actions1"].widgets[0].rect)
    width = w[2] - w[0]
    font_size = float(re.search(rb"/DejaVu ([0-9.]+) Tf", r.get_fields()["Actions1"] and
                                next(a.get_object() for a in r.pages[0]["/Annots"] if a.get_object().get("/T") == "Actions1")["/AP"]["/N"].get_object().get_data()).group(1))
    for line in lines:
        assert metrics.width(line, font_size) <= width - 2 * SF.PAD + 0.01


def test_wrap_and_fit_helpers():
    measure_fn = lambda t: 5.0 * len(t)  # noqa: E731
    assert SF.wrap_text(measure_fn, "aa bb cc", 25) == ["aa bb", "cc"]
    assert SF.wrap_text(measure_fn, "a\n\nb", 100) == ["a", "", "b"]
    assert SF.wrap_text(measure_fn, "abcdefghij", 20) == ["abcd", "efgh", "ij"]


def test_a_character_outside_the_subset_is_an_error_never_a_question_mark():
    with pytest.raises(SF.MissingGlyph) as e:
        SF.apply_form(base_pdf(), fields("CharacterName"), {"CharacterName": "Zoë"}, CREATED)
    assert "ë" in e.value.chars
    # the renderer widens the invisible charset line with the characters it is about to write
    data = SF.apply_form(base_pdf(extra_charset="Zoë"), fields("CharacterName"), {"CharacterName": "Zoë"}, CREATED)
    assert _ap_texts(PdfReader(io.BytesIO(data)))[0]["CharacterName"][0] == ["Zoë"]
    assert SF.charset_for(["Zoë"]).endswith("ë") and SF.charset_for([]) == SF.CHARSET


def test_a_base_without_the_charset_line_is_refused():
    pdf = FPDF(format="A4", unit="pt")
    pdf.add_font("DejaVu", "", str(FONTS / "DejaVuSans.ttf"))
    pdf.add_page()
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(50, 10, "Title")
    with pytest.raises(SF.MissingGlyph):
        SF.apply_form(bytes(pdf.output()), fields("CharacterName"), {}, CREATED)


def test_single_line_text_shrinks_but_never_changes_the_value():
    long = "Много дълго име на герой, което не се побира в рамката"
    r = PdfReader(io.BytesIO(SF.apply_form(base_pdf(), fields("CharacterName"), {"CharacterName": long}, CREATED)))
    assert r.get_fields()["CharacterName"]["/V"] == long
    annot = r.pages[0]["/Annots"][0].get_object()
    size = float(re.search(rb"/DejaVu ([0-9.]+) Tf", annot["/AP"]["/N"].get_object().get_data()).group(1))
    assert size < L.a4_size(12.0)


def test_output_is_byte_identical_for_a_fixed_created_and_differs_with_another():
    a, b = built(), built()
    assert a == b
    assert built(created=datetime(2026, 11, 11, tzinfo=timezone.utc)) != a
    assert PdfReader(io.BytesIO(a)).metadata.creation_date == CREATED  # pypdf writes the date escaped (D\\072...)


def test_round_trip_read_back_then_apply_again_is_identical():
    first = built()
    read = PdfReader(io.BytesIO(first)).get_fields()
    values = {name: (f["/V"] == "/Yes" if f["/FT"] == "/Btn" else f["/V"]) for name, f in read.items()}
    assert values == {**VALUES}
    assert built(values) == first


def test_400_fields_take_under_400_ms():
    allf = (list(L.FIELDS) + list(L.spell_fields(1)))[:400]
    base = base_pdf()
    values = {f.name: ("Тест 12" if f.kind == "text" else "Ред\nвтори ред" if f.kind == "multi" else True) for f in allf}
    SF.apply_form(base, allf, values, CREATED)
    laps = measure(lambda: SF.apply_form(base, allf, values, CREATED), runs=5, warmup=1)
    assert_fast(laps, "apply_form 400 fields", limit_ms=400.0)


def test_pypdf_is_imported_lazily():
    import ast
    tree = ast.parse(Path(SF.__file__).read_text(encoding="utf-8"))
    top = {(n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
           for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [n])}
    assert "pypdf" not in top and "fpdf" not in top
