"""The form step of the fillable sheet: turns the drawn (fpdf2) pages into an AcroForm (plan 2026-11-10, SHEET-S3).

``apply_form(base_pdf, fields, values, created)`` takes the bytes of a PDF whose first regular DejaVu subset also
contains the invisible charset line (``CHARSET``, drawn with ``TextMode.INVISIBLE``), adds one widget per
``sheet_layout.Widget`` (shared fields: a parent with several kids), the checkbox appearances and a REAL appearance
stream for every text field, and writes ``/AcroForm`` with ``/DR`` (that same font), ``/DA`` and
``/NeedAppearances false``.

Why the appearance streams are written here and not by pypdf's ``update_page_form_field_values`` (found in S0): pypdf
encodes text with the glyph ids of the embedded subset, while the page font (an fpdf2 Type0 / Identity-H font) maps a
CODE to a glyph through fpdf2's own CID numbering; the two differ and Cyrillic came out as other letters. The font's
``/ToUnicode`` is the one reliable table, so a character is encoded as the inverse of it and measured with the font's
``/W``; a character that is not in the subset raises ``MissingGlyph`` (never a silent ``?``).

pypdf is imported lazily (it is not part of the default Pyodide distribution; the offline build loads the pinned
wheel with the PDF stack), so importing this module costs nothing.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from sheet_layout import SCALE, Field, a4_rect, a4_size

# The characters a player may type into a field: ASCII, the Cyrillic block of Bulgarian and Russian (U+0400-045F)
# and the usual punctuation (the plan's list plus the opening quotes U+2018 and U+201E, which Bulgarian typography uses). The renderer draws this line invisibly on page 1 so the embedded subset holds them.
CHARSET = (
    "".join(chr(c) for c in range(0x20, 0x7F))
    + "".join(chr(c) for c in range(0x0400, 0x0460))
    + "\u2013\u2014\u2018\u2019\u201c\u201d\u201e\u2022\u2026\u2116\u25cf\u25cb"
)

FONT_RESOURCE = "/DejaVu"
LEADING = 1.2
PAD = 1.5  # A4 points, inside a field box
MIN_SIZE_SINGLE = 0.6  # a single-line value may shrink to this fraction of the field's size
MIN_SIZE_MULTI = 6.0 * SCALE  # a multiline value shrinks down to 6 pt (Letter) before it is cut off


class MissingGlyph(ValueError):
    """A character of a field value is not in the embedded font subset."""

    def __init__(self, chars: str):
        super().__init__(f"characters missing from the font subset: {sorted(set(chars))!r}")
        self.chars = "".join(sorted(set(chars)))


def charset_for(texts: Sequence[str] = ()) -> str:
    """CHARSET plus every other character of ``texts`` (so a typed or generated é, ü ... also reaches the subset)."""
    extra = sorted({ch for t in texts for ch in t if ch not in CHARSET and ch >= " " and ch != "\x7f"})
    return CHARSET + "".join(extra)


class FontMetrics:
    """Unicode -> CID (inverse of /ToUnicode) and CID -> width (1/1000 em, from /W) of a Type0 font."""

    def __init__(self, font: Any):
        cmap = font["/ToUnicode"].get_object().get_data().decode("latin-1")
        self.to_cid: dict[str, int] = {}
        for cid, uni in re.findall(r"<([0-9A-Fa-f]{4})>\s*<([0-9A-Fa-f]{4})>", cmap):
            self.to_cid.setdefault(chr(int(uni, 16)), int(cid, 16))
        desc = font["/DescendantFonts"][0].get_object()
        self.widths: dict[int, float] = {}
        w = [x.get_object() for x in desc["/W"]]
        i = 0
        while i < len(w):
            nxt = w[i + 1]
            if isinstance(nxt, (int, float)):
                for cid in range(int(w[i]), int(nxt) + 1):
                    self.widths[cid] = float(w[i + 2])
                i += 3
            else:
                for n, width in enumerate(nxt):
                    self.widths[int(w[i]) + n] = float(width.get_object() if hasattr(width, "get_object") else width)
                i += 2
        self.default = float(desc.get("/DW", 1000))

    def width(self, text: str, size: float) -> float:
        return sum(self.widths.get(self.to_cid[ch], self.default) if ch in self.to_cid else self.default for ch in text) * size / 1000.0

    def encode(self, text: str) -> str:
        missing = [ch for ch in text if ch not in self.to_cid]
        if missing:
            raise MissingGlyph("".join(missing))
        return "".join(f"{self.to_cid[ch]:04X}" for ch in text)

    def decode(self, hex_codes: str) -> str:
        back = {cid: ch for ch, cid in self.to_cid.items()}
        return "".join(back[int(hex_codes[i:i + 4], 16)] for i in range(0, len(hex_codes), 4))


def wrap_text(measure, text: str, width: float) -> list[str]:
    """Greedy word wrap of ``text`` (paragraphs split on newlines); a word wider than the line is cut by characters."""
    lines: list[str] = []
    for para in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        cur = ""
        for word in para.split(" "):
            trial = word if not cur else cur + " " + word
            if measure(trial) <= width:
                cur = trial
                continue
            if cur:
                lines.append(cur)
                cur = ""
            while measure(word) > width and len(word) > 1:
                cut = len(word) - 1
                while cut > 1 and measure(word[:cut]) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            cur = word
        lines.append(cur)
    return lines


def fit_text(metrics: FontMetrics, text: str, width: float, height: float, size: float, multiline: bool) -> tuple[list[str], float, bool]:
    """(lines, font size, fits) for ``text`` in a box of ``width`` x ``height`` A4 points. Single line: the size shrinks to
    ``MIN_SIZE_SINGLE`` of ``size``; multiline: it shrinks (0.25 pt steps) to ``MIN_SIZE_MULTI``. ``fits`` is False when
    the text still does not fit at the smallest size (the appearance is then clipped; /V keeps all of it)."""
    inner_w = width - 2 * PAD
    if not multiline:
        line = text.replace("\r", " ").replace("\n", " ")
        s = size
        floor = size * MIN_SIZE_SINGLE
        while metrics.width(line, s) > inner_w and s > floor:
            s = max(floor, s - 0.25)
        return [line], s, metrics.width(line, s) <= inner_w
    s = size
    while True:
        lines = wrap_text(lambda t: metrics.width(t, s), text, inner_w)
        fits = len(lines) * s * LEADING + 2 * PAD <= height
        if fits or s <= MIN_SIZE_MULTI:
            return lines, s, fits
        s = max(MIN_SIZE_MULTI, s - 0.25)


def find_form_font(writer: Any) -> Any:
    """The regular DejaVu Type0 font of the drawn pages (an indirect reference)."""
    for page in writer.pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for ref in fonts.values():
            font = ref.get_object()
            base = str(font.get("/BaseFont", ""))
            if font.get("/Subtype") == "/Type0" and "DejaVu" in base and "Bold" not in base:
                return ref
    raise ValueError("no regular DejaVu Type0 font on the drawn pages")


def _pdf_date(created: datetime) -> str:
    created = created.astimezone(timezone.utc) if created.tzinfo else created
    return created.strftime("D:%Y%m%d%H%M%SZ")


def apply_form(base: bytes, fields: Sequence[Field], values: Mapping[str, str | bool], created: datetime) -> bytes:
    """The PDF ``base`` plus one AcroForm with ``fields`` filled from ``values`` (missing: empty / unchecked).

    Page numbers of the widgets are 1-based pages of ``base``. The output is a pure function of its inputs: with a
    fixed ``created`` the bytes are identical from run to run."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import (ArrayObject, BooleanObject, DictionaryObject, FloatObject, NameObject, NumberObject,
                               StreamObject, TextStringObject)

    writer = PdfWriter(clone_from=PdfReader(BytesIO(base)))
    font_ref = find_form_font(writer)
    metrics = FontMetrics(font_ref.get_object())
    missing = [ch for ch in CHARSET if ch not in metrics.to_cid]
    if missing:
        raise MissingGlyph("".join(missing))
    writer.add_metadata({"/CreationDate": _pdf_date(created), "/ModDate": _pdf_date(created)})

    n = NameObject
    resources = writer._add_object(DictionaryObject({n("/Font"): DictionaryObject({n(FONT_RESOURCE): font_ref})}))
    default_da = f"{FONT_RESOURCE} 8 Tf 0 g"
    acro = DictionaryObject({
        n("/Fields"): ArrayObject(),
        n("/DR"): DictionaryObject({n("/Font"): DictionaryObject({n(FONT_RESOURCE): font_ref})}),
        n("/DA"): TextStringObject(default_da),
        n("/NeedAppearances"): BooleanObject(False),
    })
    writer._root_object[n("/AcroForm")] = writer._add_object(acro)
    page_annots: dict[int, Any] = {}

    def bbox(w: float, h: float):
        return ArrayObject([FloatObject(0), FloatObject(0), FloatObject(round(w, 3)), FloatObject(round(h, 3))])

    def form_xobject(body: str, w: float, h: float, with_font: bool):
        st = StreamObject()
        st._data = body.encode("latin-1")
        st.update({n("/Type"): n("/XObject"), n("/Subtype"): n("/Form"), n("/BBox"): bbox(w, h)})
        if with_font:
            st[n("/Resources")] = resources
        return writer._add_object(st)

    def annots_of(page_no: int):
        if page_no not in page_annots:
            page = writer.pages[page_no - 1]
            arr = ArrayObject()
            page[n("/Annots")] = arr
            page_annots[page_no] = arr
        return page_annots[page_no]

    for field in fields:
        value = values.get(field.name, False if field.kind == "check" else "")
        multi = field.kind == "multi"
        field_entries: dict[Any, Any]
        if field.kind == "check":
            field_entries = {n("/FT"): n("/Btn"), n("/T"): TextStringObject(field.name)}
        else:
            text = "" if value is None or value is False else str(value)
            field_entries = {n("/FT"): n("/Tx"), n("/T"): TextStringObject(field.name), n("/V"): TextStringObject(text),
                             n("/Ff"): NumberObject(4096 if multi else 0)}
            if field.align == "center":
                field_entries[n("/Q")] = NumberObject(1)
        parent = None
        if len(field.widgets) > 1:
            parent = DictionaryObject({**field_entries, n("/Kids"): ArrayObject()})
            parent_ref = writer._add_object(parent)
            acro["/Fields"].append(parent_ref)
        for widget in field.widgets:
            x0, y0, x1, y1 = a4_rect(widget.rect)
            w, h = x1 - x0, y1 - y0
            annot = DictionaryObject({
                n("/Type"): n("/Annot"), n("/Subtype"): n("/Widget"),
                n("/Rect"): ArrayObject([FloatObject(round(v, 3)) for v in (x0, y0, x1, y1)]),
                n("/F"): NumberObject(4), n("/P"): writer.pages[widget.page - 1].indirect_reference,
                n("/MK"): DictionaryObject(),
            })
            if field.kind == "check":
                on = form_xobject(f"q 0 g {a4_size(1.0):.2f} w {PAD:.2f} {PAD:.2f} m {w - PAD:.2f} {h - PAD:.2f} l S "
                                  f"{PAD:.2f} {h - PAD:.2f} m {w - PAD:.2f} {PAD:.2f} l S Q", w, h, False)
                off = form_xobject("", w, h, False)
                state = n("/Yes" if value else "/Off")
                annot.update({n("/AP"): DictionaryObject({n("/N"): DictionaryObject({n("/Yes"): on, n("/Off"): off})}),
                              n("/AS"): state})
                if parent is None:
                    annot.update(field_entries)
                    annot[n("/V")] = state
                else:
                    parent[n("/V")] = state
            else:
                lines, size, _fits = fit_text(metrics, text, w, h, a4_size(field.size), multi)
                da = f"{FONT_RESOURCE} {size:.2f} Tf 0 g"
                ops = ["/Tx BMC", "q", f"{PAD / 2:.2f} {PAD / 2:.2f} {w - PAD:.2f} {h - PAD:.2f} re W n", "BT", da]
                if lines != [""]:
                    base_y = h - PAD - size * 0.93 if multi else (h - size * 0.73) / 2.0
                    for line in lines:
                        tw = metrics.width(line, size)
                        x = (w - tw) / 2.0 if field.align == "center" and not multi else PAD + 0.5
                        ops.append(f"1 0 0 1 {x:.2f} {base_y:.2f} Tm <{metrics.encode(line)}> Tj")
                        base_y -= size * LEADING
                ops += ["ET", "Q", "EMC"]
                annot[n("/AP")] = DictionaryObject({n("/N"): form_xobject("\n".join(ops), w, h, True)})
                annot[n("/DA")] = TextStringObject(da)
                if parent is None:
                    annot.update(field_entries)
            ref = writer._add_object(annot)
            if parent is None:
                acro["/Fields"].append(ref)
            else:
                annot[n("/Parent")] = parent_ref
                parent["/Kids"].append(ref)
            annots_of(widget.page).append(ref)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
