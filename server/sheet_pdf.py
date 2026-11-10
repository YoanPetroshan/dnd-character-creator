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
from sheet_form import CHARSET, apply_form, charset_for

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
        self.pages: list[str] = []  # kind per page, in order

    # ---- registering fields ----
    def add_fields(self, names, page_map: dict[int, int]) -> None:
        """Fields of the fixed layout whose widgets on the mapped layout pages are placed on the real pages."""
        for n in names:
            f = L.FIELDS_BY_NAME[n]
            widgets = tuple(L.Widget(page_map[w.page], w.rect) for w in f.widgets if w.page in page_map)
            if widgets:
                self.fields.append(L.Field(f.name, f.kind, widgets, f.align, f.size))

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

    def build(self) -> bytes:
        self.page1()
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
