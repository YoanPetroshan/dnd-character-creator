"""SHEET-S2: the geometry data of the fillable sheet (server/sheet_layout.py)."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sheet_layout as L  # noqa: E402

PAGES = {1, 2, 3, 4, L.SPELL_PAGE}
EPS = 0.05


def _all_fields():
    return list(L.FIELDS) + list(L.spell_fields(1)) + list(L.spell_fields(2))


def _inside(inner, outer, eps=EPS):
    return inner[0] >= outer[0] - eps and inner[1] >= outer[1] - eps and inner[2] <= outer[2] + eps and inner[3] <= outer[3] + eps


def _overlap(a, b):
    return a[0] < b[2] - EPS and b[0] < a[2] - EPS and a[1] < b[3] - EPS and b[1] < a[3] - EPS


def test_every_rectangle_is_a_proper_rectangle_on_the_letter_page():
    for f in _all_fields():
        assert f.widgets
        for w in f.widgets:
            x0, y0, x1, y1 = w.rect
            assert w.page in PAGES, f.name
            assert 0 <= x0 < x1 <= L.LETTER_W and 0 <= y0 < y1 <= L.LETTER_H, (f.name, w.rect)


def test_field_names_are_unique_ascii_and_free_of_dots():
    names = [f.name for f in _all_fields()]
    assert len(names) == len(set(names))
    for n in names:
        assert re.fullmatch(r"[A-Za-z0-9_]+", n), n
        assert "." not in n and n.isascii()
    assert {f.kind for f in _all_fields()} == {"text", "multi", "check"}


def test_a_field_has_at_most_one_widget_per_page():
    for f in _all_fields():
        pages = [w.page for w in f.widgets]
        assert len(pages) == len(set(pages)), f.name


def test_identity_fields_are_shared_across_pages():
    by = L.FIELDS_BY_NAME
    for n in ("ClassLevel", "PlayerName", "Species", "Background", "ExperiencePoints"):
        assert [w.page for w in by[n].widgets] == [1, 2, 3]
    assert [w.page for w in by["CharacterName"].widgets] == [1, 2, 3, 4]


def test_the_reference_counts_are_kept():
    assert len(L.SKILLS) == 18 and len(L.ABILITIES) == 6
    assert L.EQUIPMENT_ROWS == 56  # Eq0 .. Eq55
    assert len(L.ROW_GROUPS["weapons"]) == 6
    sp = L.spell_fields(1)
    assert len(sp) == 4 + L.SPELL_SLOTS * len(L.SPELL_COLUMNS) == 504


@pytest.mark.parametrize("group", sorted(L.ROW_GROUPS))
def test_rows_of_a_group_do_not_overlap(group):
    rows = []
    for names in L.ROW_GROUPS[group]:
        rects = [w.rect for n in names for w in L.FIELDS_BY_NAME[n].widgets]
        rows.append((min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects)))
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            assert not _overlap(a, b), (group, a, b)


def test_spell_slots_do_not_overlap_and_fit_the_page():
    prev = None
    for slot in range(L.SPELL_SLOTS):
        y0, y1 = L.spell_slot_y(slot)
        assert y1 - y0 == pytest.approx(L.SPELL_SLOT_HEIGHT)
        if prev is not None:
            assert y1 <= prev - 0.5  # a gap between lines
        prev = y0
    assert prev >= 50.0
    cols = [(x0, x1) for _k, x0, x1, _a in L.SPELL_COLUMNS]
    for (a0, a1), (b0, b1) in zip(cols, cols[1:]):
        assert a1 < b0


def test_no_two_fields_overlap_on_a_page():
    for page in PAGES:
        rects = [(f.name, w.rect) for f in list(L.FIELDS) + list(L.spell_fields(1)) for w in f.widgets if w.page == page]
        for i, (na, a) in enumerate(rects):
            for nb, b in rects[i + 1:]:
                assert not _overlap(a, b), (page, na, nb)


def test_frames_contain_their_widgets():
    names = set()
    for fr in L.FRAMES:
        assert fr.page in PAGES and (fr.name, fr.page) not in names
        names.add((fr.name, fr.page))
        assert 0 <= fr.rect[0] < fr.rect[2] <= L.LETTER_W and 0 <= fr.rect[1] < fr.rect[3] <= L.LETTER_H
        for member in fr.members:
            widgets = [w for w in L.FIELDS_BY_NAME[member].widgets if w.page == fr.page]
            assert widgets, (fr.name, member)
            for w in widgets:
                assert _inside(w.rect, fr.rect), (fr.name, member, w.rect, fr.rect)


def test_every_widget_sits_in_a_frame_of_its_page():
    for f in _all_fields():
        for w in f.widgets:
            assert any(fr.page == w.page and _inside(w.rect, fr.rect) for fr in L.FRAMES), (f.name, w.page)


def test_every_fixed_field_is_a_member_of_a_frame():
    members = {(m, fr.page) for fr in L.FRAMES for m in fr.members}
    for f in L.FIELDS:
        for w in f.widgets:
            assert (f.name, w.page) in members, (f.name, w.page)


def test_frames_of_a_page_do_not_overlap():
    for page in PAGES:
        frames = [fr for fr in L.FRAMES if fr.page == page]
        for i, a in enumerate(frames):
            for b in frames[i + 1:]:
                assert not _overlap(a.rect, b.rect), (page, a.name, b.name)
    assert not _overlap(L.PORTRAIT_RECT, next(fr.rect for fr in L.FRAMES if fr.name == "allies"))


def test_the_a4_transform_is_uniform_and_centred():
    assert L.SCALE == pytest.approx(595.28 / 612)
    x0, y0, x1, y1 = L.a4_rect((0, 0, L.LETTER_W, L.LETTER_H))
    assert (x0, x1) == pytest.approx((0.0, L.A4_W))
    assert y0 == pytest.approx(L.A4_H - y1)  # equal margins top and bottom
    assert y1 - y0 == pytest.approx(L.LETTER_H * L.SCALE)
    rect = (47.5, 710.3, 220.6, 731.2)
    a = L.a4_rect(rect)
    assert (a[2] - a[0]) / (rect[2] - rect[0]) == pytest.approx(L.SCALE)
    assert (a[3] - a[1]) / (rect[3] - rect[1]) == pytest.approx(L.SCALE)
    assert L.a4_size(10) == pytest.approx(10 * L.SCALE)
    assert L.a4_point(100, 100) == pytest.approx((100 * L.SCALE, 100 * L.SCALE + L.OFFSET_Y))
    for f in _all_fields():
        for w in f.widgets:
            r = L.a4_rect(w.rect)
            assert 0 <= r[0] < r[2] <= L.A4_W and 0 <= r[1] < r[3] <= L.A4_H


def test_the_module_imports_only_the_standard_library():
    import ast
    tree = ast.parse((Path(L.__file__)).read_text(encoding="utf-8"))
    mods = {(n.module if isinstance(n, ast.ImportFrom) else a.name).split(".")[0]
            for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in (n.names if isinstance(n, ast.Import) else [n])}
    assert mods <= {"__future__", "dataclasses"}
