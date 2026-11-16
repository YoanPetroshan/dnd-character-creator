"""S04 (audit PERF-01): a long word with no spaces took 24 s to export as a sheet.

`wrap_text` cut an over-wide word by measuring one prefix after another (each measure is O(length)), and `fit_text` / `pack`
call it again for every font size they try. The cut is now a galloping + binary search for the longest prefix that fits.
The old implementation stays here as the reference: the new one must return the very same lines for any input."""
from __future__ import annotations

import json
import random
import time

import pytest

import service
from service_requests import exportable_draft
from sheet_form import wrap_text

needs_data = pytest.mark.skipif(not service._catalog.races, reason="catalog not loaded")


def wrap_text_reference(measure, text: str, width: float) -> list[str]:
    """The implementation before S04, verbatim."""
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


def _measure(rng: random.Random):
    widths = {ch: rng.choice([0, 1, 2, 3, 5, 8, 13]) for ch in "abcdefghijklmnopqrstuvwxyz WMi.-"}
    return lambda t: float(sum(widths.get(ch, 4) for ch in t))


def test_the_new_wrap_gives_the_reference_lines_for_random_text_and_widths():
    rng = random.Random(20261116)
    alphabet = "abcdefghijklmnopqrstuvwxyz WMi.-\n"
    for _ in range(3000):
        measure = _measure(rng)
        text = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 120)))
        if rng.random() < 0.3:
            text = text.replace(" ", "")  # long unbroken words are the case that changed
        width = rng.choice([0.0, 1.0, 2.0, 7.0, 20.0, 55.5, 90.0, 400.0])
        assert wrap_text(measure, text, width) == wrap_text_reference(measure, text, width), (text, width)


@pytest.mark.parametrize("text,width", [("", 10.0), ("x", 0.5), ("W" * 50, 1.0), ("a" * 1000, 37.0), ("a b " * 50, 12.0)])
def test_edge_cases_equal_the_reference(text, width):
    measure = lambda t: float(len(t) * 2)  # noqa: E731
    assert wrap_text(measure, text, width) == wrap_text_reference(measure, text, width)


@needs_data
@pytest.mark.parametrize("backstory", ["W" * 5000, "Lorem ipsum " * 500], ids=["5000-W", "lorem-500"])
def test_a_5000_character_backstory_exports_a_sheet_in_under_two_seconds(backstory):
    draft = exportable_draft()
    draft["details"] = {"backstory": backstory}
    body = json.dumps(draft).encode()
    service.handle("POST", "/api/export/sheet", None, json.dumps(exportable_draft()).encode())  # warm the fonts
    t = time.perf_counter()
    status, _ct, _h, out = service.handle("POST", "/api/export/sheet", None, body)
    seconds = time.perf_counter() - t
    assert status == 200 and out[:4] == b"%PDF"
    assert seconds < 2.0, f"{seconds:.1f} s"


# ---- Q5 = A: free text of a section is capped at 20 000 characters, with a visible note ---------------------------------

@needs_data
@pytest.mark.parametrize("lang,note", [("en", "cut to 20000 characters"), ("bg", "съкратен до 20000 знака")])
@pytest.mark.parametrize("key", ["backstory", "notes", "allies", "personalityTraits"])
def test_free_text_over_20000_characters_is_cut_with_a_visible_note(key, lang, note):
    import sheet_data
    from catalog.loader import load
    from engine.resolve import resolve

    catalog = load()

    def texts(text):
        draft = exportable_draft()
        draft["details"] = {key: text}
        data = sheet_data.build_sheet_data(resolve(draft, catalog), catalog, lang, "mixed")
        values = data.as_dict()
        field = {"backstory": "Backstory", "notes": "Notes1", "allies": "Allies", "personalityTraits": "Personality"}[key]
        return "\n".join([str(values.get(field, "")), *(b.text for b in data.flow), *(t for rest in data.overflow.values() for t in rest)])

    long = ("word " * 6000).strip()  # 29 999 characters
    out = texts(long)
    assert note in out
    assert out.count("word") <= 20000 // 5 + 1  # nothing beyond the cap is kept
    ok = ("word " * 3999).strip()  # 19 995 characters: untouched
    assert note not in texts(ok)
