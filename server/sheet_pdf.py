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
from sheet_data import FlowBlock, SheetData, build_sheet_data
from export_fields import fmt_spell_slots
from sheet_form import CHARSET, LEADING, PAD, apply_form, charset_for, wrap_text

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
GREY = (90, 90, 90)
LIGHT = (235, 235, 235)
INK_ = (0, 0, 0)
FIELD_ = (255, 255, 255)
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
        self.overflows: list[tuple[str, float, float]] = []  # (text, width needed at the smallest size, width allowed): a defect

    def clean(self, text: str) -> str:
        """Characters DejaVu has no glyph for (emoji, CJK ...) become "?": visible and explicit, never a missing-glyph error."""
        cmap = self.fonts["dejavu"].cmap
        if all(ord(c) in cmap or c in "\n" for c in text):
            return text
        return "".join(c if ord(c) in cmap or c == "\n" else "?" for c in text)

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
        text = self.clean(text)
        if width:
            size = self.fit_size(text, width, size, minimum, bold)
            if self.width(text, size, bold) > width + 0.5:
                self.overflows.append((text, round(self.width(text, size, bold), 1), width))
        w = self.width(text, size, bold)
        if align == "center" and width:
            x += (width - w) / 2
        elif align == "right" and width:
            x += width - w
        self.set_text_color(*color)
        ax, ay = L.a4_point(x, y)
        self.text(ax, L.A4_H - ay, text)

    def poly(self, points, fill=None, width: float = 0.8, color=INK_) -> None:
        """A closed polygon of Letter points."""
        self.set_draw_color(*color)
        self.set_line_width(width * S)
        if fill:
            self.set_fill_color(*fill)
        self.polygon([(L.a4_point(x, y)[0], L.A4_H - L.a4_point(x, y)[1]) for x, y in points], style="DF" if fill else "D")

    def oval(self, rect, fill=None, width: float = 0.7) -> None:
        x0, y0, x1, y1 = L.a4_rect(rect)
        self.set_draw_color(*INK_)
        self.set_line_width(width * S)
        if fill:
            self.set_fill_color(*fill)
        self.ellipse(x0, L.A4_H - y1, x1 - x0, y1 - y0, style="DF" if fill else "D")

    def hexagon(self, rect) -> None:
        x0, y0, x1, y1 = rect
        m, k = (y0 + y1) / 2, min(9.0, (x1 - x0) / 4)
        self.poly([(x0, m), (x0 + k, y1), (x1 - k, y1), (x1, m), (x1 - k, y0), (x0 + k, y0)], fill=FIELD_, width=0.9)

    def shield(self, rect) -> None:
        """A heater shield behind the armor class value."""
        x0, y0, x1, y1 = rect
        cx, left, right, top = (x0 + x1) / 2, x0 - 6, x1 + 6, y1 + 6
        side, tip = y0 + 8, y0 - 4
        pts = [(left, top), (cx, top - 2), (right, top), (right, side)]
        for i in range(1, 9):  # right curve down to the tip
            t = i / 8
            pts.append(((1 - t) ** 2 * right + 2 * t * (1 - t) * (right - 4) + t * t * cx, (1 - t) ** 2 * side + 2 * t * (1 - t) * (tip + 7) + t * t * tip))
        for i in range(1, 8):
            t = i / 8
            pts.append(((1 - t) ** 2 * cx + 2 * t * (1 - t) * (left + 4) + t * t * left, (1 - t) ** 2 * tip + 2 * t * (1 - t) * (tip + 7) + t * t * side))
        self.poly(pts, fill=FIELD_, width=1.2)

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


PANEL = (208, 208, 208)  # the large grey regions behind groups of frames
FRAME_FILL = (234, 234, 234)
FIELD = (255, 255, 255)
INK = (0, 0, 0)
TITLE = (25, 25, 25)
LABEL = (55, 55, 55)  # small captions: dark enough to stay readable in greyscale
FIELD_LINE = (70, 70, 70)
TITLE_SIZE = 5.6
TITLE_MIN = 5.0
LINE_H = 6.6
# which frames sit on one grey panel, per layout page (the panel is their union plus a margin)
PANEL_GROUPS = {
    1: [["ability_str", "ability_dex", "ability_con", "ability_int", "ability_wis", "ability_cha"], ["saves", "skills"],
        ["initiative", "armor_class", "defenses", "inspiration", "proficiency_bonus", "spell_dc", "speed"],
        ["hit_points", "hit_dice", "death_saves"], ["proficiencies"], ["actions"], ["senses"], ["weapons"]],
    2: [["features_1", "features_2", "features_3"], ["coins", "carrying"], ["equipment_left", "equipment_right", "attuned"]],
    3: [["features_4", "features_5", "features_6"], ["equipment_left", "equipment_right"]],
    4: [["body"], ["allies"], ["personality", "ideals", "bonds", "flaws"], ["appearance"], ["backstory"], ["notes1", "notes2"]],
}
CIRCLES = ("Save", "Skill", "CustomSkill", "Inspiration", "DeathSuccess", "DeathFailure")


def _members_bbox(fr: L.Frame):
    rects = [w.rect for n in fr.members for w in L.FIELDS_BY_NAME[n].widgets if w.page == fr.page]
    if not rects:
        return None
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def title_lines(doc: _Doc, text: str, width: float, max_lines: int = 3) -> tuple[list[str], float]:
    """The title in capitals as one line, or wrapped (the bracket term starts its own line), at TITLE_SIZE, else at TITLE_MIN.
    Words are never cut; a line that is still too wide is recorded by ``put`` as an overflow."""
    text = text.upper()
    lines: list[str] = [text]
    for size in (TITLE_SIZE, TITLE_MIN):
        measure = lambda t, size=size: doc.width(t, size, True)  # noqa: E731
        if measure(text) <= width:
            return [text], size
        if " (" in text:
            head, tail = text.split(" (", 1)
            lines = wrap_text(measure, head, width) + wrap_text(measure, "(" + tail, width)
        else:
            lines = wrap_text(measure, text, width)
        if len(lines) <= max_lines and all(measure(x) <= width + 0.01 for x in lines):
            return lines, size
    return lines, TITLE_MIN


def pill_radius(rect) -> float:
    return min(rect[3] - rect[1], rect[2] - rect[0]) / 2.0


def draw_frame(doc: _Doc, fr: L.Frame, lang: str, title: str | None = None, misses: list | None = None) -> None:
    """A black-outlined rounded frame (light grey) with its bold capital title in the biggest free band."""
    if fr.name == "identity":
        draw_header(doc, fr)
        return
    pill = fr.name in ("inspiration", "proficiency_bonus", "spell_dc")
    doc.box(fr.rect, 1.0, fill=FRAME_FILL, radius=pill_radius(fr.rect) if pill else 5, color=INK)
    text = sheet_label(lang, fr.title) if title is None and fr.title else (title or "")
    bbox = _members_bbox(fr)
    if not text or not bbox:
        return
    x0, y0, x1, y1 = fr.rect
    below, above = bbox[1] - y0, y1 - bbox[3]
    right, left = x1 - bbox[2], bbox[0] - x0
    if fr.name == "weapons":  # the column heads use the top band
        above = 0
    inner = x1 - x0 - 8
    lines, size = title_lines(doc, text, inner)
    need = LINE_H * len(lines)
    if below >= need + 1 or above >= need + 1:
        at_bottom = below >= need + 1 and (below >= above or above < need + 1)
        top = (y0 + (below + need) / 2 - 1.2) if at_bottom else (y1 - above + (above + need) / 2 - 1.2)
        for i, ln in enumerate(lines):
            doc.put(ln, x0 + 4, top - LINE_H * (i + 1) + 1.6, size, "center", inner, bold=True, color=TITLE, minimum=size)
        return
    for room, x_start in ((right, bbox[2] + 4), (left, x0 + 4)):
        if room >= 34:
            lines, size = title_lines(doc, text, room - 8)
            mid = (bbox[1] + bbox[3]) / 2 + LINE_H * len(lines) / 2
            for i, ln in enumerate(lines):
                doc.put(ln, x_start, mid - LINE_H * (i + 1) + 1.6, size, "left", room - 8, bold=True, color=TITLE, minimum=size)
            return
    if misses is not None:
        misses.append(fr.name)


def draw_header(doc: _Doc, fr: L.Frame) -> None:
    """The name ribbon (swallow-tailed banner behind the character name) and, on pages 1-3, the grey block of the other identity boxes."""
    name = L.FIELDS_BY_NAME["CharacterName"].widgets[0] if fr.page == 1 else next(w for w in L.FIELDS_BY_NAME["CharacterName"].widgets if w.page == fr.page)
    x0, y0, x1, y1 = name.rect
    ribbon = [(x0 - 20, y1 + 8), (x1 + 14, y1 + 8), (x1 + 5, (y0 + y1) / 2), (x1 + 14, y0 - 8), (x0 - 20, y0 - 8), (x0 - 11, (y0 + y1) / 2)]
    doc.poly(ribbon, fill=(190, 190, 190), width=1.0)
    if fr.page != 4:
        doc.box((x1 + 24, fr.rect[1], fr.rect[2], fr.rect[3]), 1.0, fill=FRAME_FILL, radius=6, color=INK)


def draw_panels(doc: _Doc, page: int) -> None:
    for group in PANEL_GROUPS.get(page, []):
        rects = [fr.rect for fr in L.FRAMES if fr.page == page and fr.name in group]
        if rects:
            doc.box((min(r[0] for r in rects) - 4, min(r[1] for r in rects) - 4, max(r[2] for r in rects) + 4, max(r[3] for r in rects) + 4),
                    0.0, fill=PANEL, radius=7, color=PANEL)


def draw_field_boxes(doc: _Doc, names, page: int) -> None:
    """White boxes with dark text on the grey frames; round marks, an oval modifier, a shield behind the AC, hexagonal coins."""
    for n in names:
        f = L.FIELDS_BY_NAME[n]
        for w in f.widgets:
            if w.page != page:
                continue
            x0, y0, x1, y1 = w.rect
            if n == "ArmorClass":
                doc.shield(w.rect)
            elif n.endswith("Mod") and n.startswith("Ability"):
                doc.oval((x0 - 3, y0 - 1.5, x1 + 3, y1 + 1.5), FIELD)
            elif n.startswith("Coins"):
                doc.hexagon((x0 - 2, y0 - 2, x1 + 2, y1 + 2))
            elif (n.startswith(CIRCLES) and (n.endswith("Mark") or n.startswith(("Inspiration", "Death")))):
                doc.oval(w.rect, FIELD)
            else:
                doc.box(w.rect, 0.6, fill=FIELD, color=FIELD_LINE, radius=0 if f.kind == "multi" else 2)


class Sheet:
    def __init__(self, resolution: dict, lang: str, catalog, created: datetime, ruleset: str | None):
        self.lang = check_lang(lang)
        self.resolution, self.catalog, self.created = resolution, catalog, created
        self.data: SheetData = build_sheet_data(resolution, catalog, lang, ruleset)
        self.values = self.data.as_dict()
        self.name = (resolution["sheet"].get("name") or "").strip() or label(lang, "unnamed")
        self.doc = _Doc()
        self.doc.set_creation_date(created)  # fpdf2 would stamp the current time
        self.fields: list[L.Field] = []
        self.index: dict[str, int] = {}
        self.flow_extra: list[str] = []
        self.pages: list[str] = []  # kind per page, in order
        self.title_misses: list[str] = []  # frames whose title found no room (a test keeps this empty)

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

    def use_page(self, number: int) -> None:
        """Make ``number`` the drawing page and register both fonts on it (fpdf2 only does that when the style CHANGES)."""
        self.doc.page = number
        self.doc.set_font("DejaVu", "B", 6)
        self.doc.set_font("DejaVu", "", 6)

    def new_page(self, kind: str) -> int:
        self.doc.add_page()
        self.pages.append(kind)
        self.use_page(len(self.pages))
        return len(self.pages)

    # ---- page 1 ----
    def page1(self) -> None:
        d, lang = self.doc, self.lang
        page = self.new_page("combat")
        names = [f.name for f in L.FIELDS if any(w.page == 1 for w in f.widgets)]
        draw_panels(d, 1)
        for fr in L.FRAMES:
            if fr.page == 1:
                draw_frame(d, fr, lang, misses=self.title_misses)
        draw_field_boxes(d, names, 1)
        # identity labels under the boxes
        for key, n in (("idName", "CharacterName"), ("idClass", "ClassLevel"), ("idPlayer", "PlayerName"), ("idSpecies", "Species"),
                       ("idBackground", "Background"), ("idXp", "ExperiencePoints")):
            x0, y0, x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key).upper(), x0, y0 - (17.0 if n == "CharacterName" else 7.5), 5.6, "left", x1 - x0, color=LABEL)
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
            d.put(sheet_label(lang, key), x0 - 2, y0 - 8, 5.6, "center", x1 - x0 + 4, color=LABEL)
        for n, key, dy in (("HitDiceTotal", "hdTotal", 3), ("HitDiceSpent", "hdSpent", -5.5)):
            x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key), x0 - 2, (y1 if dy > 0 else y0) + dy, 5.6, "center", x1 - x0 + 4, color=LABEL)
        for n, key in (("DeathSuccess1", "dsSuccess"), ("DeathFailure1", "dsFailure")):
            x0, y0, _x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key), 500, y0 + 3, 5.6, "left", x0 - 503, color=LABEL)
        # weapon column heads
        top = L.FIELDS_BY_NAME["Weapon1Name"].widgets[0].rect[3] + 3
        for n, key in (("Weapon1Name", "colName"), ("Weapon1Attack", "colAttack"), ("Weapon1Damage", "colDamage"), ("Weapon1Notes", "colNotes")):
            x0, _y0, x1, _ = L.FIELDS_BY_NAME[n].widgets[0].rect
            d.put(sheet_label(lang, key).upper(), x0, top, 5.6, "left", x1 - x0, color=LABEL)
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
            for ln in wrap_text(lambda t: d.width(t, size), d.clean(b.text), inner):
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
            self.use_page(real)
            draw_panels(d, page)
            for fr in L.FRAMES:
                if fr.page == page:
                    draw_frame(d, fr, lang, misses=self.title_misses)
            self.draw_page23_labels(page)
            d.put(sheet_label(lang, "features").upper(), 36.0, 303.0, TITLE_SIZE, "center", 538.0, bold=True, color=TITLE, minimum=TITLE_MIN)
            names = [f.name for f in L.FIELDS if any(w.page == page for w in f.widgets)]
            draw_field_boxes(d, names, page)
            self.add_fields(names, {page: real})

    def draw_page23_labels(self, page: int) -> None:
        d, lang = self.doc, self.lang
        for key, n in (("idName", "CharacterName"), ("idClass", "ClassLevel"), ("idPlayer", "PlayerName"), ("idSpecies", "Species"),
                       ("idBackground", "Background"), ("idXp", "ExperiencePoints")):
            for w in L.FIELDS_BY_NAME[n].widgets:
                if w.page == page:
                    d.put(sheet_label(lang, key).upper(), w.rect[0], w.rect[1] - (17.0 if n == "CharacterName" else 7.5), 5.6, "left", w.rect[2] - w.rect[0], color=LABEL)
        if page == 2:
            for n, key in (("CoinsCp", "CP"), ("CoinsSp", "SP"), ("CoinsEp", "EP"), ("CoinsGp", "GP"), ("CoinsPp", "PP")):
                x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                d.put(key, x1 + 4.5, (y0 + y1) / 2 - 2.0, 6.0, "left", 10, bold=True, color=TITLE)
            for n, key in (("WeightCarried", "carryWeight"), ("WeightCapacity", "carryCapacity"), ("PushDragLift", "carryPush")):
                x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                caption = wrap_text(lambda t: d.width(t, 5.6), sheet_label(lang, key), x1 - x0 + 2)
                for i, ln in enumerate(reversed(caption[:2])):
                    d.put(ln, x0, y1 + 2.2 + 6.0 * i, 5.6, "left", x1 - x0 + 2, color=LABEL, minimum=5.0)
            heads = (("Eq0Name", "Eq0Qty", "Eq0Weight"), ("Eq15Name", "Eq15Qty", "Eq15Weight"), ("Attuned1Name", "Attuned1Qty", "Attuned1Weight"))
        else:
            heads = (("Eq26Name", "Eq26Qty", "Eq26Weight"), ("Eq41Name", "Eq41Qty", "Eq41Weight"))
        for trio in heads:
            for n, key in zip(trio, ("colName", "colQty", "colWeight")):
                x0, y0, x1, y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                d.put(sheet_label(lang, key).upper(), x0, y1 + 3, 5.6, "left", x1 - x0, color=LABEL)

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
                self.doc.box((x0 - 3, 36.0, x1 + 3, 660.0), 1.0, fill=FRAME_FILL, radius=6, color=INK)
                self.doc.box(rect, 0.4, fill=FIELD, color=FIELD_LINE)
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
                d.box((nx[0] - 5, 34.0, wx[1] + 5, 662.0), 1.0, fill=FRAME_FILL, radius=6, color=INK)
                for key, (x0, x1) in zip(("colName", "colQty", "colWeight"), (nx, qx, wx)):
                    d.put(sheet_label(lang, key).upper(), x0, 644.0, 5.6, "left", x1 - x0, color=LABEL)
                for i in range(per_col):
                    y0 = 628.0 - 14.89 * i
                    idx = c * per_col + i
                    name, qty, wt = chunk[idx] if idx < len(chunk) else ("", "", "")
                    for key, (x0, x1), val, al in (("Name", nx, name, "left"), ("Qty", qx, qty, "center"), ("Weight", wx, wt, "center")):
                        fname = f"EqX{k}_{idx:02d}{key}"
                        rect = (x0, y0, x1, y0 + 14.1)
                        d.box(rect, 0.4, fill=FIELD, color=FIELD_LINE, radius=2)
                        self.values[fname] = val
                        self.fields.append(L.Field(fname, "text", (L.Widget(page, rect),), al, 8.0))

    # ---- page 4: appearance and story ----
    def page4(self) -> None:
        d, lang = self.doc, self.lang
        page = self.new_page("story")
        draw_panels(d, 4)
        for fr in L.FRAMES:
            if fr.page == 4:
                draw_frame(d, fr, lang, misses=self.title_misses)
        names = [f.name for f in L.FIELDS if any(w.page == 4 for w in f.widgets)]
        draw_field_boxes(d, names, 4)
        w = L.FIELDS_BY_NAME["CharacterName"].widgets[-1]
        d.put(sheet_label(lang, "idName").upper(), w.rect[0], w.rect[1] - 17.0, 5.6, "left", w.rect[2] - w.rect[0], color=LABEL)
        for n in names:
            if n.startswith("Body"):
                x0, y0, x1, _y1 = L.FIELDS_BY_NAME[n].widgets[0].rect
                d.put(sheet_label(lang, "body" + n[4:]).upper(), x0, y0 - 6.5, 5.6, "left", x1 - x0, color=LABEL, minimum=5.0)
        d.box(L.PORTRAIT_RECT, 1.0, fill=FIELD, radius=5, color=INK)
        d.put(sheet_label(lang, "portrait").upper(), L.PORTRAIT_RECT[0], L.PORTRAIT_RECT[1] + 5, 5.6, "center",
              L.PORTRAIT_RECT[2] - L.PORTRAIT_RECT[0], bold=True, color=GREY)
        self.add_fields(names, {4: page})

    def notes_pages(self) -> None:
        """Backstory / notes text that did not fit the page-4 boxes continues in two tall columns per page."""
        d, lang = self.doc, self.lang
        blocks: list = []
        for name, key in (("Backstory", "backstory"), ("Notes1", "notes"), ("Notes2", "notes")):
            rest = self.data.overflow.get(name)
            if rest:
                blocks.append(FlowBlock("heading", sheet_label(lang, "headContinued", title=sheet_label(lang, key))))
                blocks.extend(FlowBlock("text", t) for t in rest)
        if not blocks:
            return
        xs = ((36.5, 295.0), (302.0, 575.5))
        dims = [(x1 - x0, 616.0) for x0, x1 in xs]
        texts, _rest = self.pack(blocks, dims, 7.0, more=dims[0])
        for k, start in enumerate(range(0, len(texts), 2), start=1):
            page = self.new_page("notes-continued")
            self.header_line(f"{self.name}  \u00b7  {sheet_label(lang, 'headContinued', title=sheet_label(lang, 'notes'))}")
            for c, (x0, x1) in enumerate(xs):
                rect = (x0, 40.0, x1, 656.0)
                name = f"NotesC{k}_{c + 1}"
                d.box((x0 - 3, 36.0, x1 + 3, 660.0), 1.0, fill=FRAME_FILL, radius=6, color=INK)
                d.box(rect, 0.4, fill=FIELD, color=FIELD_LINE)
                self.values[name] = texts[start + c] if start + c < len(texts) else ""
                self.fields.append(L.Field(name, "multi", (L.Widget(page, rect),), "left", 7.0))

    # ---- spell pages ----
    def spell_pages(self) -> None:
        """One group (class / innate) after the other, 50 slots per page; a level header is never the last slot of a page."""
        d, lang = self.doc, self.lang
        derived = self.resolution["derived"]
        slot_parts = []
        if derived.get("spellSlots"):
            slot_parts.append(f"{label(lang, 'spellSlots')}: {fmt_spell_slots(derived['spellSlots'], lang)}")
        if derived.get("warlockSpellSlots"):
            slot_parts.append(f"{label(lang, 'pactSlots')}: {fmt_spell_slots(derived['warlockSpellSlots'], lang)}")
        number = 0
        for group in self.data.spell_groups:
            rows = list(group.rows)
            at = 0
            first = True
            while at < len(rows) or first:
                take = rows[at:at + L.SPELL_SLOTS]
                if len(take) == L.SPELL_SLOTS and take[-1].kind == "header":
                    take = take[:-1]
                at += len(take)
                first = False
                number += 1
                self.one_spell_page(number, group, take, slot_parts if group.key != "innate" else [], continued=at > len(take))

    def one_spell_page(self, n: int, group, rows, slot_parts, continued: bool) -> None:
        d, lang = self.doc, self.lang
        page = self.new_page("spells")
        fields = L.spell_fields(n, page)
        values: dict[str, str] = {f.name: "" for f in fields}
        values[f"Spell{n}_Class"] = group.title
        values[f"Spell{n}_Ability"] = group.ability
        values[f"Spell{n}_SaveDc"] = group.save_dc
        values[f"Spell{n}_Attack"] = group.attack
        for slot, row in enumerate(rows):
            if row.kind == "header":
                values[f"Spell{n}_{slot:02d}_Name"] = row.cells["Name"]
                continue
            cells = {key: str(row.cells.get(key, "")) for key, *_ in L.SPELL_COLUMNS}
            moved = []
            for key, x0, x1, _al in L.SPELL_COLUMNS:
                if key == "Notes":
                    continue
                short = self.shorten(cells[key], x1 - x0)
                if short != cells[key]:
                    moved.append(cells[key])  # the full text continues in the Notes box
                    cells[key] = short
            if moved:
                cells["Notes"] = ", ".join([x for x in (cells["Notes"], *moved) if x])
            cells["Notes"] = self.shorten(cells["Notes"], 578.8 - 422.6)
            for key, text in cells.items():
                values[f"Spell{n}_{slot:02d}_{key}"] = text
        d.box((43.0, 689.5, 560.0, 742.0), 1.0, fill=FRAME_FILL, radius=6, color=INK)
        d.box((25.0, 49.0, 582.0, 652.0), 1.0, fill=PANEL, radius=7, color=INK)
        for slot, row in enumerate(rows):  # a darker band behind each level header
            if row.kind == "header":
                y0, y1 = L.spell_slot_y(slot)
                d.box((28.0, y0 - 0.5, 580.0, y1 + 0.5), 0.2, fill=(205, 205, 205), color=(205, 205, 205))
        d.set_fill_color(*LIGHT)
        for f in fields:
            for w in f.widgets:
                d.box(w.rect, 0.3, fill=FIELD, color=(125, 125, 125))
        for slot, row in enumerate(rows):
            if row.kind == "header":
                y0, y1 = L.spell_slot_y(slot)
                d.box((41.9, y0, 148.1, y1), 0.3, fill=(205, 205, 205), color=(205, 205, 205))
        for key, text in (("Ability", "spAbility"), ("SaveDc", "spDc"), ("Attack", "spAttack"), ("Class", "spClass")):
            rect = next(f for f in fields if f.name == f"Spell{n}_{key}").widgets[0].rect
            room = {"Ability": 96.0, "SaveDc": 70.0, "Attack": 112.0, "Class": rect[2] - rect[0]}[key]
            lines, size = title_lines(d, sheet_label(lang, text), room)
            cx = (rect[0] + rect[2]) / 2
            for i, ln in enumerate(lines):
                x = rect[0] if key == "Class" else cx - room / 2
                d.put(ln, x, rect[1] - 6.6 - LINE_H * i, size, "left" if key == "Class" else "center", room, bold=True, color=TITLE, minimum=size)
        top = L.SPELL_SLOT_TOP + 3
        for key, x0, x1, _al in L.SPELL_COLUMNS:
            d.put(sheet_label(lang, "sp" + key).upper() if key != "Prep" else sheet_label(lang, "spPrep").upper(), x0, top, 5.6, "left", x1 - x0, bold=True, color=LABEL, minimum=5.0)
        if slot_parts:
            d.put("   ".join(slot_parts), 47.5, 677.0, 7, "left", 510, color=(0, 0, 0))
        if continued:
            d.put(sheet_label(lang, "headContinued", title=group.title), 47.5, 664.0, 7, "left", 510, bold=True, color=LABEL)
        for i, line in enumerate(wrap_text(lambda t: d.width(t, 5.0), sheet_label(lang, "legend"), 552.0)[:3]):
            d.put(line, 28.0, 41.5 - 6.0 * i, 5.0, "left", 552.0, color=LABEL, minimum=5.0)
        self.fields.extend(fields)
        self.values.update(values)

    def shorten(self, text: str, width: float, size: float = 6.5) -> str:
        """``text`` cut with an ellipsis until it fits one line of a ``width`` box at 0.6 of ``size`` (what apply_form shrinks to)."""
        small = size * 0.6
        inner = (width - 2 * PAD / S) * 0.985
        if not text or self.doc.width(text, small) <= inner:
            return text
        while text and self.doc.width(text + "\u2026", small) > inner:
            text = text[:-1]
        return text.rstrip() + "\u2026"

    def build(self) -> bytes:
        self.page1()
        self.pages23()
        self.flow_pages()
        self.equipment_pages()
        self.page4()
        self.notes_pages()
        self.spell_pages()
        self.finish_pages()
        base = bytes(self.doc.output())
        texts = [v for v in self.values.values() if isinstance(v, str)] + [self.name]
        return apply_form(base, self.fields, self.values, self.created) if False else self.apply(base, texts)

    def finish_pages(self) -> None:
        d, total = self.doc, len(self.pages)
        self.name = d.clean(self.name)
        self.values = {k: (d.clean(v) if isinstance(v, str) else v) for k, v in self.values.items()}
        for i in range(total):
            d.page = i + 1
            if i == 0:
                d.set_font("DejaVu", "", 4)
                with d.local_context(text_mode=TextMode.INVISIBLE):
                    d.set_xy(4, 3)
                    d.cell(0, 4, charset_for([v for v in self.values.values() if isinstance(v, str)] + [self.name, self.footer(1, total)]))
            text = self.footer(i + 1, total)
            d.set_text_color(*GREY)
            d.set_font("DejaVu", "B", 6.5)  # a change of style makes fpdf2 register the font on THIS page
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
