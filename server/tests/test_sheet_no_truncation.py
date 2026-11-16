"""S05 (audit EXP-01, EXP-02): the fillable sheet never stores a cut text and the Bulgarian weights carry kilograms.

Owner decision (2026-11-16): the full text goes into the field value (/V); where a box is too small the viewer shows it
clipped. Nothing is replaced by an ellipsis and nothing is lost from the file."""
from __future__ import annotations

import io
import re

import pytest
from pypdf import PdfReader

from catalog.loader import load
from test_sheet_baseline import render

IDS = ("wizard20-2024", "warlock7-2024", "sorcerer17-2024")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _fields(sid, lang, catalog):
    reader = PdfReader(io.BytesIO(render(sid, lang, catalog)))
    return {k: str(v.get("/V") or "") for k, v in (reader.get_fields() or {}).items()}


@pytest.mark.parametrize("lang", ["en", "bg"])
@pytest.mark.parametrize("sid", IDS)
def test_no_spell_field_value_ends_with_an_ellipsis(catalog, sid, lang):
    fields = _fields(sid, lang, catalog)
    assert [k for k, v in fields.items() if k.startswith("Spell") and ("…" in v)] == []


@pytest.mark.parametrize("lang", ["en", "bg"])
@pytest.mark.parametrize("sid", IDS)
def test_the_long_spell_range_is_stored_in_full(catalog, sid, lang):
    fields = _fields(sid, lang, catalog)
    ranges = [v for k, v in fields.items() if re.fullmatch(r"Spell\d+_\d+_Range", k)]
    assert any(v.startswith("Self (") and len(v) > 16 for v in ranges), ranges


@pytest.mark.parametrize("sid", IDS)
def test_every_spell_name_is_present_in_the_english_sheet(catalog, sid):
    fields = _fields(sid, "en", catalog)
    names = [v for k, v in fields.items() if re.fullmatch(r"Spell\d+_\d+_Name", k) and v]
    assert len(names) >= 8 and all(not n.endswith("…") for n in names)


@pytest.mark.parametrize("sid", IDS)
def test_the_bulgarian_weights_are_in_kilograms_and_the_english_ones_in_pounds(catalog, sid):
    bg = {k: v for k, v in _fields(sid, "bg", catalog).items() if re.fullmatch(r"Eq\d+Weight", k) and v not in ("", "--")}
    en = {k: v for k, v in _fields(sid, "en", catalog).items() if re.fullmatch(r"Eq\d+Weight", k) and v not in ("", "--")}
    # the narrow cell only holds the kilograms ("0,9 kg"); the pounds stay in the English sheet and in the Markdown / PDF
    assert bg and all(v.endswith(" kg") for v in bg.values()), bg
    assert en and all(v.endswith(" lb") for v in en.values()), en
