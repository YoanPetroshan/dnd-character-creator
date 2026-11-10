"""The fillable character sheet as a PDF (plan 2026-11-10; SHEET-S5 onward): ``to_sheet(resolution, lang, catalog, created)``.

fpdf2 draws the A4 pages (frames, titles, labels, an invisible charset line); ``sheet_form.apply_form`` adds the AcroForm
with every value as a real, editable field. Geometry is ``sheet_layout`` (Letter points through one A4 transform), the
values are ``sheet_data.build_sheet_data``. Nothing here is a D&D Beyond / WotC asset: plain own frames, headings and footer.

Page plan: 1 (combat), 2-3 (features flow, coins, equipment), continuation pages as the content needs, 4 (story), notes
continuation, then the spell pages.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import TextMode

import sheet_layout as L
from export_labels import DEFAULT_LANG, check_lang, label, sheet_label
from sheet_data import SheetData, build_sheet_data
from sheet_form import CHARSET, LEADING, PAD, apply_form, charset_for, wrap_text

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
GREY = (90, 90, 90)
LIGHT = (235, 235, 235)
S = L.SCALE
SKILL_LABELS = ("Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception", "History", "Insight", "Intimidation",
                "Investigation", "Medicine", "Nature", "Perception", "Performance", "Persuasion", "Religion", "Sleight of Hand",
                "Stealth", "Survival")


class _Doc(FPDF):
    def __init__(self):
        super().__init__(format="A4", unit="pt")
        self.set_auto_page_break(False)
        self.add_font("DejaVu", "", str(FONT_DIR / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FONT_DIR / "DejaVuSans-Bold.ttf"))

    # ---- measuring and placing text (all coordinates are Letter points, y up, like sheet_layout) ----
    def width(self, text: str, size: float, bold: bool = False) -> float:
        self.set_font("DejaVu", "B" if bold else "", size * S)
        return self.get_string_width(text) / S

    def fit_size(self, text: str, width: float, size: float, minimum: float = 4.0, bold: bool = False) -> float:
        while size > minimum and self.width(text, size, bold) > width:
            size -= 0.25
        return size

    def put(self, text: str, x: float, y: float, size: float, align: str = "left", width: float = 0, bold: bool = False,
            minimum: float = 4.0, color=(0, 0, 0)) -> None:
        """Draw ``text`` with its baseline at Letter (x, y); ``align`` centre/right inside ``width`` from x; shrinks to fit width."""
        if not text:
            return
        if width:
            size = self.fit_size(text, width, size, minimum, bold)
        w = self.width(text, size, bold)
        if align == "center" and width:
            x += (width - w) / 2
        elif align == "right" and width:
            x += width - w
        self.set_text_color(*color)
        ax, ay = L.a4_point(x, y)
        self.text(ax, L.A4_H - ay, text)

    def box(self, rect, width: float = 0.5, fill=None, radius: float = 0, color=GREY) -> None:
        x0, y0, x1, y1 = L.a4_rect(rect)
        self.set_draw_color(*color)
        self.set_line_width(width * S)
        if fill:
            self.set_fill_color(*fill)
        style = "DF" if fill else "D"
        if radius:
            self.rect(x0, L.A4_H - y1, x1 - x0, y1 - y0, style=style, round_corners=True, corner_radius=radius * S)
        else:
            self.rect(x0, L.A4_H - y1, x1 - x0, y1 - y0, style=style)


def _members_bbox(fr: L.Frame):
    rects = [w.rect for n in fr.members for w in L.FIELDS_BY_NAME[n].widgets if w.page == fr.page]
    if not rects:
        return None
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def draw_frame(doc: _Doc, fr: L.Frame, lang: str, title: str | None = None) -> None:
    """A rounded frame with its title in the biggest free band (below, above, right or left of the fields)."""
    doc.box(fr.rect, 0.9, radius=4)
    text = sheet_label(lang, fr.title) if title is None and fr.title else (title or "")
    bbox = _members_bbox(fr)
    if not text or not bbox:
        return
    text = text.upper()
    x0, y0, x1, y1 = fr.rect
    below, above = bbox[1] - y0, y1 - bbox[3]
    right, left = x1 - bbox[2], bbox[0] - x0
    size = 5.5
    if fr.name == "weapons":  # the column heads use the top band
        above = 0
    if below >= 8 or above >= 8:
        y = y0 + (below - 5.5) / 2 + 1.2 if below >= above else y1 - above + (above - 5.5) / 2 + 1.2
        doc.put(text, x0 + 3, y, size, "center", x1 - x0 - 6, bold=True, color=GREY)
    elif right >= 36:
        doc.put(text, bbox[2] + 4, (bbox[1] + bbox[3]) / 2 - 2, size, "left", right - 8, bold=True, color=GREY)
    elif left >= 30:
        doc.put(text, x0 + 3, (bbox[1] + bbox[3]) / 2 - 2, size, "left", left - 6, bold=True, color=GREY)


def draw_field_boxes(doc: _Doc, names, page: int) -> None:
    for n in names:
        f = L.FIELDS_BY_NAME[n]
        for w in f.widgets:
            if w.page == page:
                doc.box(w.rect, 0.4, fill=LIGHT if f.kind != "check" else None, color=(150, 150, 150), radius=0 if f.kind == "multi" else 1.5)


class Sheet:
    def __init__(self, resolution: dict, lang: str, catalog, created: datetime, ruleset: str | None):
        self.lang = check_lang(lang)
        self.resolution, self.catalog, self.created = resolution, catalog, created
        self.data: SheetData = build_sheet_data(resolution, catalog, lang, ruleset)
        self.values = self.data.as_dict()
        self.name = (resolution["sheet"].get("name") or "").strip() or label(lang, "unnamed")
        self.doc = _Doc()
        self.fields: list[L.Field] = []
        self.index: dict[str, int] = {}
        self.flow_extra: list[str] = []
        self.pages: list[str] = []  # kind per page, in order

    # ---- registering fields ----
    def add_fields(self, names, page_map: dict[int, int]) -> None:
        """Fields of the fixed layout whose widgets on the mapped layout pages are placed on the real pages."""
        for n in names:
            f = L.FIELDS_BY_NAME[n]
            widgets = tuple(L.Widget(page_map[w.page], w.rect) for w in f.widgets if w.page in page_map)
            if not widgets:
                continue
            at = self.index.get(n)
            if at is None:
                self.index[n] = len(self.fields)
                self.fields.append(L.Field(f.name, f.kind, widgets, f.align, f.size))
            else:
                old = self.fields[at]
                self.fields[at] = L.Field(old.name, old.kind, old.widgets + widgets, old.align, old.size)

    def new_page(self, kind: str) -> int:
        self.doc.add_page()
        self.pages.append(kind)
        return len(self.pages)

    # ---- page 1 ----
    def page1(self) -> None:
        d, lang = self.doc, self.lang
        page = self.new_page("combat")
        names = [f.name for f in L.FIELDS if any(w.page == 1 for w in f.widgets)]
        for fr in L.FRAMES:
            if fr.page == 1:
                draw_frame(d, fr, lang)
        draw_field_boxes(d, names, 1)
        # identity labels under the boxes
        for key, n in (("idName", "CharacterName"), ("idClass", "ClassLevel"), ("idPlayer", "PlayerName"), ("idSpecies", "Species"),
                       ("idBackground", "Background"), ("idXp", "ExperiencePoints")):
            x0, y0, x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key).upper(), x0, y0 - 7.5, 5, "left", x1 - x0, color=GREY)
        # saves: short names; skills: names and ability tags are fields, the names are drawn
        for i, a in enumerate(L.ABILITIES):
            y = L.FIELDS_BY_NAME[f"Save{a}"].widgets[0].rect[1]
            d.put(a.upper(), 131, y + 2, 7, "left", 22, color=(0, 0, 0))
        for i, s in enumerate(L.SKILLS):
            y = L.FIELDS_BY_NAME[f"Skill{s}"].widgets[0].rect[1]
            d.put(SKILL_LABELS[i], 128, y + 2, 7, "left", 48)
        # passives
        for n, key in (("PassivePerception", "passivePerception"), ("PassiveInsight", "passiveInsight"),
                       ("PassiveInvestigation", "passiveInvestigation")):
            x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(label(lang, key), x1 + 5, y0 + 5.5, 6, "left", 200 - x1 - 8, minimum=4.5)
        # hit points / dice / death saves labels
        for n, key in (("MaxHp", "hpMax"), ("CurrentHp", "hpCurrent"), ("TempHp", "hpTemp")):
            x0, y0, x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key), x0 - 2, y0 - 8, 5.5, "center", x1 - x0 + 4, color=GREY)
        for n, key, dy in (("HitDiceTotal", "hdTotal", 3), ("HitDiceSpent", "hdSpent", -7)):
            x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key), x0 - 2, (y1 if dy > 0 else y0) + dy, 5.5, "center", x1 - x0 + 4, color=GREY)
        for n, key in (("DeathSuccess1", "dsSuccess"), ("DeathFailure1", "dsFailure")):
            x0, y0, _x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key), 500, y0 + 3, 5.5, "left", x0 - 503, color=GREY)
        # weapon column heads
        top = L.FIELDS_BY_NAME["Weapon1Name"].widgets[0].rect[3] + 3
        for n, key in (("Weapon1Name", "colName"), ("Weapon1Attack", "colAttack"), ("Weapon1Damage", "colDamage"), ("Weapon1Notes", "colNotes")):
            x0, _y0, x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key).upper(), x0, top, 5, "left", x1 - x0, color=GREY)
        self.add_fields(names, {1: page})


    # ---- packing text into columns (the features flow, notes) ----
    def pack(self, blocks, columns, size: float, more=None):
        """Fill columns (list of (width, height) in Letter points) with FlowBlocks. Lines are wrapped with the font's
        metrics; a paragraph may continue in the next column; a heading or title is never the last line of a column.
        Returns (texts per column, leftover blocks). With ``more`` (a (width, height) column) it keeps adding columns."""
        d = self.doc
        lines: list[tuple[int, str, str]] = []  # (paragraph id, text, kind)
        pid = 0
        for b in blocks:
            if lines and b.kind in ("heading", "title"):
                lines.append((-1, "", "blank"))
            pid += 1
            width = columns[0][0] if columns else more[0]
            inner = (width - 2 * PAD / S) * 0.985
            for ln in wrap_text(lambda t: d.width(t, size), b.text, inner):
                lines.append((pid, ln, b.kind))
        texts: list[str] = []
        i, col = 0, 0
        while i < len(lines):
            if col < len(columns):
                w, h = columns[col]
            elif more:
                w, h = more
            else:
                break
            cap = max(1, int((h - 2 * PAD / S) / (size * LEADING)))
            taken: list[tuple[int, str, str]] = []
            while i < len(lines) and len(taken) < cap:
                if not taken and lines[i][2] == "blank":
                    i += 1
                    continue
                if lines[i][2] in ("heading", "title") and len(taken) >= cap - 1 and taken:
                    break  # keep a heading with its text
                taken.append(lines[i])
                i += 1
            while taken and taken[-1][2] == "blank":
                taken.pop()
            paragraphs: list[str] = []
            last = None
            for par, text, kind in taken:
                if par != -1 and par == last:
                    paragraphs[-1] += " " + text
                else:
                    paragraphs.append(text)
                last = par
            texts.append("\n".join(paragraphs))
            col += 1
        return texts, lines[i:]

    def header_line(self, text: str) -> None:
        self.doc.put(text, 36, 742, 11, "left", 520, bold=True)

    def draw_features_frame(self, rect, title_key="features", page_title: str | None = None) -> None:
        fr = L.Frame("x", 0, rect, title_key, ())
        self.doc.box(rect, 0.9, radius=4)

    # ---- pages 2 and 3 ----
    def pages23(self) -> None:
        d, lang = self.doc, self.lang
        first = self.new_page("features")
        second = self.new_page("features")
        pm = {2: first, 3: second}
        cols = [L.FIELDS_BY_NAME[f"Features{i}"] for i in range(1, 7)]
        dims = [(f.widgets[0].rect[2] - f.widgets[0].rect[0], f.widgets[0].rect[3] - f.widgets[0].rect[1]) for f in cols]
        flow = list(self.data.flow)
        texts, rest = self.pack(flow, dims, 7.0, more=(dims[0][0], 616.0))
        self.flow_columns = texts  # first six on pages 2-3, the rest on continuation pages
        for i, f in enumerate(cols):
            self.values[f.name] = texts[i] if i < len(texts) else ""
        self.flow_extra = texts[6:]
        for page, real in ((2, first), (3, second)):
            d.page = real
            for fr in L.FRAMES:
                if fr.page == page:
                    draw_frame(d, fr, lang)
            self.draw_page23_labels(page)
            names = [f.name for f in L.FIELDS if any(w.page == page for w in f.widgets)]
            draw_field_boxes(d, names, page)
            self.add_fields(names, {page: real})

    def draw_page23_labels(self, page: int) -> None:
        d, lang = self.doc, self.lang
        for key, n in (("idName", "CharacterName"), ("idClass", "ClassLevel"), ("idPlayer", "PlayerName"), ("idSpecies", "Species"),
                       ("idBackground", "Background"), ("idXp", "ExperiencePoints")):
            for w in L.FIELDS_BY_NAME[n].widgets:
                if w.page == page:
                    d.put(sheet_label(lang, key).upper(), w.rect[0], w.rect[1] - 7.5, 5, "left", w.rect[2] - w.rect[0], color=GREY)
        if page == 2:
            for n, key in (("CoinsCp", "CP"), ("CoinsSp", "SP"), ("CoinsEp", "EP"), ("CoinsGp", "GP"), ("CoinsPp", "PP")):
                x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                d.put(key, x1 + 2, y0 + 6, 7, "left", 10, bold=True, color=GREY)
            for n, key in (("WeightCarried", "carryWeight"), ("WeightCapacity", "carryCapacity"), ("PushDragLift", "carryPush")):
                x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                d.put(sheet_label(lang, key), x0, y1 + 2, 5.5, "left", x1 - x0 + 4, color=GREY, minimum=3.5)
            heads = (("Eq0Name", "Eq0Qty", "Eq0Weight"), ("Eq15Name", "Eq15Qty", "Eq15Weight"), ("Attuned1Name", "Attuned1Qty", "Attuned1Weight"))
        else:
            heads = (("Eq26Name", "Eq26Qty", "Eq26Weight"), ("Eq41Name", "Eq41Qty", "Eq41Weight"))
        for trio in heads:
            for n, key in zip(trio, ("colName", "colQty", "colWeight")):
                x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                d.put(sheet_label(lang, key).upper(), x0, y1 + 3, 5, "left", x1 - x0, color=GREY)

    # ---- continuation pages ----
    def flow_pages(self) -> None:
        d, lang = self.doc, self.lang
        cols = L.FIELDS_BY_NAME
        xs = [(f.widgets[0].rect[0], f.widgets[0].rect[2]) for f in (cols["Features1"], cols["Features2"], cols["Features3"])]
        extra = self.flow_extra
        for k, start in enumerate(range(0, len(extra), 3), start=1):
            page = self.new_page("features-continued")
            self.header_line(f"{self.name}  \u00b7  {sheet_label(lang, 'headContinued', title=sheet_label(lang, 'features'))}")
            names = []
            for c, (x0, x1) in enumerate(xs):
                rect = (x0, 40.0, x1, 656.0)
                name = f"Flow{k}_{c + 1}"
                self.doc.box((x0 - 2, 38.0, x1 + 2, 658.0), 0.9, radius=4)
                self.doc.box(rect, 0.4, fill=LIGHT, color=(150, 150, 150))
                text = extra[start + c] if start + c < len(extra) else ""
                self.values[name] = text
                self.fields.append(L.Field(name, "multi", (L.Widget(page, rect),), "left", 7.0))

    def equipment_pages(self) -> None:
        d, lang = self.doc, self.lang
        rows = list(self.data.equipment_overflow)
        per_col = 40
        for k, start in enumerate(range(0, len(rows), 2 * per_col), start=1):
            page = self.new_page("equipment-continued")
            self.header_line(f"{self.name}  \u00b7  {sheet_label(lang, 'headContinued', title=sheet_label(lang, 'equipment'))}")
            chunk = rows[start:start + 2 * per_col]
            for c, (nx, qx, wx) in enumerate((((36.5, 231.5), (235.8, 265.9), (270.0, 299.8)), ((312.5, 507.6), (511.5, 541.2), (545.7, 575.5)))):
                d.box((nx[0] - 3, 36.0, wx[1] + 3, 660.0), 0.9, radius=4)
                for key, (x0, x1) in zip(("colName", "colQty", "colWeight"), (nx, qx, wx)):
                    d.put(sheet_label(lang, key).upper(), x0, 644.0, 5, "left", x1 - x0, color=GREY)
                for i in range(per_col):
                    y0 = 628.0 - 14.89 * i
                    idx = c * per_col + i
                    name, qty, wt = chunk[idx] if idx < len(chunk) else ("", "", "")
                    for key, (x0, x1), val, al in (("Name", nx, name, "left"), ("Qty", qx, qty, "center"), ("Weight", wx, wt, "center")):
                        fname = f"EqX{k}_{idx:02d}{key}"
                        rect = (x0, y0, x1, y0 + 14.1)
                        d.box(rect, 0.4, fill=LIGHT, color=(150, 150, 150), radius=1.5)
                        self.values[fname] = val
                        self.fields.append(L.Field(fname, "text", (L.Widget(page, rect),), al, 8.0))

    def build(self) -> bytes:
        self.page1()
        self.pages23()
        self.flow_pages()
        self.equipment_pages()
        self.finish_pages()
        base = bytes(self.doc.output())
        texts = [v for v in self.values.values() if isinstance(v, str)] + [self.name]
        return apply_form(base, self.fields, self.values, self.created) if False else self.apply(base, texts)

    def finish_pages(self) -> None:
        d, total = self.doc, len(self.pages)
        for i in range(total):
            d.page = i + 1
            if i == 0:
                d.set_font("DejaVu", "", 4)
                with d.local_context(text_mode=TextMode.INVISIBLE):
                    d.set_xy(4, 3)
                    d.cell(0, 4, charset_for([v for v in self.values.values() if isinstance(v, str)] + [self.name, self.footer(1, total)]))
            text = self.footer(i + 1, total)
            d.set_text_color(*GREY)
            d.set_font("DejaVu", "", 6.5)
            d.set_xy(0, L.A4_H - 24)
            d.cell(L.A4_W, 8, text, align="C")

    def footer(self, n: int, m: int) -> str:
        return sheet_label(self.lang, "footer", name=self.name, n=n, m=m)

    def apply(self, base: bytes, texts) -> bytes:
        return apply_form(base, self.fields, self.values, self.created)


def to_sheet(resolution: dict, lang: str = DEFAULT_LANG, catalog=None, created: datetime | None = None, ruleset: str | None = None) -> bytes:
    """The fillable character sheet in ``lang`` ("bg" or "en"). ``created`` makes the bytes reproducible."""
    if catalog is None:
        from catalog.loader import load
        catalog = load()
    return Sheet(resolution, lang, catalog, created or datetime(2000, 1, 1), ruleset).build()
