"""S0 viewer spike for the fillable character sheet (dev script, no app code).

Writes a 2-page A4 PDF form to the path given on the command line (default:
./sheet_spike.pdf; keep it OUT of the repository). Geometry is kept in
Letter points and scaled by s = 595.28 / 612, centred vertically, exactly as
the plan prescribes for the real sheet.

Contents: a Cyrillic single-line field, a Cyrillic multiline field, one field
with two widgets on two pages (shared value), a checkbox with its own /Yes and
/Off appearance streams. The form font is the regular DejaVu subset that fpdf2
embedded for the page, which also contains an invisible charset line (so the
subset has every glyph a player may type); NeedAppearances is false.

    .venv/bin/python scripts/dev_sheet_spike.py /path/outside/repo/spike.pdf
"""
from __future__ import annotations

import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import TextMode

FONT_DIR = Path(__file__).resolve().parent.parent / "server" / "assets" / "fonts"
S = 595.28 / 612.0
OFF_Y = (841.89 - 792.0 * S) / 2.0
CHARSET = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "".join(chr(c) for c in range(0x0400, 0x0460))
    + "–—’“”•…№●○"
)


def rect(x0: float, y0: float, x1: float, y1: float) -> list[float]:
    """Letter rect (PDF origin bottom-left) -> A4 rect."""
    return [x0 * S, y0 * S + OFF_Y, x1 * S, y1 * S + OFF_Y]


# name, page, letter rect (x0, y0, x1, y1), kind, value
FIELDS = [
    ("SpikeLine", 0, (60, 700, 300, 720), "line", "Иван Петров – Паладин 6"),
    ("SpikeMulti", 0, (60, 560, 300, 680), "multi", "Първи ред на описание.\nВторият ред е по-дълъг и трябва да се пренесе на нов ред вътре в полето, за да проверим пренасянето."),
    ("SharedName", 0, (320, 700, 560, 720), "line", "Общо име"),
    ("SharedName", 1, (320, 700, 560, 720), "line", "Общо име"),
    ("SpikeCheck", 0, (60, 520, 80, 540), "check", True),
    ("SpikeCheckOff", 0, (100, 520, 120, 540), "check", False),
]


def draw(created: datetime) -> bytes:
    pdf = FPDF(format="A4", unit="pt")
    pdf.set_auto_page_break(False)
    pdf.set_creation_date(created)
    pdf.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
    for page in range(2):
        pdf.add_page()
        pdf.set_font("DejaVu", "", 12 * S)
        pdf.set_xy(60 * S, 40 * S + OFF_Y)
        pdf.cell(0, 14, f"Spike page {page + 1}")
        # frames for every widget on this page
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.6 * S)
        for name, p, r, kind, _v in FIELDS:
            if p == page:
                x0, y0, x1, y1 = r
                pdf.rect(x0 * S, 792 * S + OFF_Y - y1 * S, (x1 - x0) * S, (y1 - y0) * S)
    # invisible charset line on page 1 (keeps the glyphs in the embedded subset)
    pdf.page = 1
    pdf.set_font("DejaVu", "", 6)
    pdf.set_xy(10, 5)
    with pdf.local_context(text_mode=TextMode.INVISIBLE):
        pdf.cell(0, 6, CHARSET)
    return bytes(pdf.output())


def font_maps(font) -> tuple[dict[str, int], dict[int, float]]:
    """unicode char -> CID (inverse of the font's /ToUnicode) and CID -> width (1/1000 em, from /W)."""
    import re

    cmap = font["/ToUnicode"].get_object().get_data().decode("latin-1")
    to_cid: dict[str, int] = {}
    for cid, uni in re.findall(r"<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]{4})>", cmap):
        to_cid.setdefault(chr(int(uni, 16)), int(cid, 16))
    desc = font["/DescendantFonts"][0].get_object()
    widths: dict[int, float] = {}
    w = [x.get_object() for x in desc["/W"]]
    k = 0
    while k < len(w):
        if isinstance(w[k + 1], list) or hasattr(w[k + 1], "__iter__") and not isinstance(w[k + 1], (int, float)):
            for n, width in enumerate(w[k + 1]):
                widths[int(w[k]) + n] = float(width)
            k += 2
        else:
            for cid in range(int(w[k]), int(w[k + 1]) + 1):
                widths[cid] = float(w[k + 2])
            k += 3
    widths.setdefault(0, float(desc.get("/DW", 1000)))
    return to_cid, widths


def wrap(measure, text: str, width: float) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = word if not cur else cur + " " + word
            if measure(trial) <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


FONT_SIZE = 10
PAD = 2.0


def build(created: datetime) -> bytes:
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, BooleanObject, DictionaryObject, FloatObject,
                               NameObject, NumberObject, StreamObject, TextStringObject)

    base = draw(created)
    reader = PdfReader(BytesIO(base))
    writer = PdfWriter(clone_from=reader)
    font_ref = next(iter(writer.pages[0]["/Resources"]["/Font"].values()))
    to_cid, widths = font_maps(font_ref.get_object())
    missing = [ch for ch in CHARSET if ch not in to_cid]
    assert not missing, f"charset line did not reach the font subset: {missing!r}"

    def measure(text: str) -> float:
        return sum(widths.get(to_cid.get(ch, 0), 600.0) for ch in text) * FONT_SIZE / 1000.0

    def encode(text: str) -> str:
        # every char must be in the subset: a miss is an error, never a silent "?"
        return "".join(f"{to_cid[ch]:04X}" for ch in text)

    da = f"/DejaVu {FONT_SIZE} Tf 0 g"
    acro = DictionaryObject({
        NameObject("/Fields"): ArrayObject(),
        NameObject("/DR"): DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/DejaVu"): font_ref})}),
        NameObject("/DA"): TextStringObject(da),
        NameObject("/NeedAppearances"): BooleanObject(False),
    })
    writer._root_object[NameObject("/AcroForm")] = writer._add_object(acro)

    def bbox(w: float, h: float):
        return ArrayObject([FloatObject(0), FloatObject(0), FloatObject(round(w, 3)), FloatObject(round(h, 3))])

    def form(body: str, w: float, h: float, resources: bool):
        st = StreamObject()
        st._data = body.encode("latin-1")
        st.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Form"),
                   NameObject("/BBox"): bbox(w, h)})
        if resources:
            st[NameObject("/Resources")] = DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/DejaVu"): font_ref})})
        return writer._add_object(st)

    parents: dict[str, DictionaryObject] = {}
    counts = {n: sum(1 for f in FIELDS if f[0] == n) for n, *_ in FIELDS}
    for name, page_no, r, kind, value in FIELDS:
        page = writer.pages[page_no]
        rr = rect(*r)
        w, h = rr[2] - rr[0], rr[3] - rr[1]
        widget = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/Rect"): ArrayObject([FloatObject(round(v, 3)) for v in rr]),
            NameObject("/F"): NumberObject(4), NameObject("/P"): page.indirect_reference,
        })
        top = widget  # the object that carries the field entries
        if kind == "check":
            on = form(f"q 0 g 1 w 2 2 m {w - 2:.2f} {h - 2:.2f} l S 2 {h - 2:.2f} m {w - 2:.2f} 2 l S Q", w, h, False)
            off = form("", w, h, False)
            state = NameObject("/Yes" if value else "/Off")
            widget.update({
                NameObject("/FT"): NameObject("/Btn"), NameObject("/T"): TextStringObject(name),
                NameObject("/V"): state, NameObject("/AS"): state,
                NameObject("/AP"): DictionaryObject({NameObject("/N"): DictionaryObject({
                    NameObject("/Yes"): on, NameObject("/Off"): off})}),
            })
        else:
            multi = kind == "multi"
            lines = wrap(measure, value, w - 2 * PAD) if multi else [value]
            ops = ["/Tx BMC", "q", f"{PAD} {PAD} {w - 2 * PAD:.3f} {h - 2 * PAD:.3f} re W n", "BT", da]
            y = h - PAD - FONT_SIZE if multi else (h - FONT_SIZE) / 2 + 2.0
            for ln in lines:
                ops.append(f"1 0 0 1 {PAD + 0.5:.2f} {y:.2f} Tm <{encode(ln)}> Tj")
                y -= FONT_SIZE * 1.2
            ops += ["ET", "Q", "EMC"]
            widget[NameObject("/AP")] = DictionaryObject({NameObject("/N"): form("\n".join(ops), w, h, True)})
            widget[NameObject("/DA")] = TextStringObject(da)
            fields = {NameObject("/FT"): NameObject("/Tx"), NameObject("/T"): TextStringObject(name),
                      NameObject("/V"): TextStringObject(value),  # the unwrapped text
                      NameObject("/Ff"): NumberObject(4096 if multi else 0)}
            if counts[name] == 1:
                widget.update(fields)
            elif name in parents:
                widget[NameObject("/Parent")] = parents[name].indirect_reference
                top = None
            else:
                parent = DictionaryObject({**fields, NameObject("/DA"): TextStringObject(da), NameObject("/Kids"): ArrayObject()})
                parent.indirect_reference = writer._add_object(parent)
                parents[name] = parent
                widget[NameObject("/Parent")] = parent.indirect_reference
                top = None
                acro["/Fields"].append(parent.indirect_reference)
        ref = writer._add_object(widget)
        if top is widget:
            acro["/Fields"].append(ref)
        if name in parents:
            parents[name]["/Kids"].append(ref)
        if "/Annots" in page:
            page["/Annots"].append(ref)
        else:
            page[NameObject("/Annots")] = ArrayObject([ref])
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def main(argv: list[str]) -> int:
    target = Path(argv[1] if len(argv) > 1 else "sheet_spike.pdf")
    created = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        data = build(created)
    target.write_bytes(data)
    print(f"wrote {target} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
