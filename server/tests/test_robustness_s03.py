"""S03 (audit API-01, API-02, API-03, LOG-01, API-05): the service and the engine survive hostile but legal input.

- a 5000-digit integer string (`level`, an ability score, `qty`) is a reported problem, not a 500 (`int()` refuses > 4300 digits);
- `sources` is read once into a bounded lowercase set: 100 000 entries cost no more than 100 and say so in a warning;
- a JSON `true` in `hpRolls` is not a roll of 1;
- an unreadable body, a non-JSON Content-Type-less blob or a number over 4300 digits is a 400, not an empty draft (Q4 = B);
- the download name has no control / bidi characters, no trailing dots or spaces and no reserved Windows device name.
"""
from __future__ import annotations

import json
import re
import urllib.parse

import pytest

import service
from catalog.loader import load
from engine.normalize import coerce_int
from engine.resolve import resolve
from perf_helpers import assert_fast, measure
from service_requests import exportable_draft

needs_data = pytest.mark.skipif(not service._catalog.races, reason="catalog not loaded")
BIG = "9" * 5000


def _post(path, body, query=None):
    raw = body if isinstance(body, (bytes, str)) else json.dumps(body)
    return service.handle("POST", path, query, raw.encode("utf-8") if isinstance(raw, str) else raw)


def _name(headers) -> str:
    m = re.fullmatch(r"attachment; filename\*=UTF-8''(.+)", headers["Content-Disposition"])
    assert m and m.group(1).isascii()
    return urllib.parse.unquote(m.group(1))


# ---- API-01: long digit strings ------------------------------------------------------------------------------

def test_coerce_int_rejects_more_than_12_digits_instead_of_raising():
    assert coerce_int("123456789012") == 123456789012
    assert coerce_int("1234567890123") is None
    assert coerce_int(BIG) is None


@needs_data
@pytest.mark.parametrize("where", ["level", "STR", "qty"])
def test_a_5000_digit_string_is_a_problem_not_a_500(where):
    draft = exportable_draft()
    if where == "level":
        draft["classes"][0]["level"] = BIG
    elif where == "STR":
        draft["abilities"]["base"]["STR"] = BIG
    else:
        draft["equipment"]["added"] = [{"itemId": "dagger", "qty": BIG}]
    status, _ct, _h, body = _post("/api/resolve", draft)
    assert status == 200, body[:200]
    assert json.loads(body)["problems"], where


# ---- API-02: sources -----------------------------------------------------------------------------------------

@needs_data
def test_100000_sources_cost_no_more_than_100_and_warn():
    catalog = load()
    base = exportable_draft()
    big = dict(base, sources=[f"book{i}" for i in range(100_000)])
    resolve(big, catalog)  # warm
    assert_fast(measure(lambda: resolve(big, catalog), runs=5), "100 000 sources", limit_ms=100)
    ids = [w["id"] for w in resolve(big, catalog)["warnings"]]
    assert "sources-too-many" in ids
    assert "sources-too-many" not in [w["id"] for w in resolve(base, catalog)["warnings"]]


@needs_data
def test_sources_are_matched_case_insensitively_and_junk_entries_are_ignored():
    catalog = load()
    a = resolve(dict(exportable_draft(), sources=["SRD", 5, None, ["x"]]), catalog)
    b = resolve(dict(exportable_draft(), sources=["srd"]), catalog)
    assert a["sheet"] == b["sheet"]


# ---- API-03: hpRolls ----------------------------------------------------------------------------------------

@needs_data
def test_a_boolean_hp_roll_is_the_average_plus_a_warning():
    catalog = load()

    def hp(rolls):
        d = exportable_draft()
        d["preferences"] = {"hitPointType": "manual"}
        d["classes"][0]["level"] = 2
        d["classes"][0]["hpRolls"] = rolls
        r = resolve(d, catalog)
        return r["derived"]["hitPointMax"], [w["id"] for w in r["warnings"] if w["id"].startswith("hp-roll-invalid")]

    average, _ = hp({})
    assert hp({"2": True}) == (average, ["hp-roll-invalid-fighter-2"])
    assert hp({"2": False})[0] == average


# ---- API-02 (Q4 = B): an unreadable body is a 400 -------------------------------------------------------------

@pytest.mark.parametrize("path", ["/api/resolve", "/api/export/yaml"])
@pytest.mark.parametrize("body", [b"{not json", b"\xff\xfe\x00", b'{"level": ' + b"9" * 4400 + b"}"], ids=["not-json", "bad-bytes", "4400-digit-number"])
def test_an_unreadable_body_is_a_400(path, body):
    status, _ct, _h, out = _post(path, body)
    assert status == 400, out[:200]
    assert "error" in json.loads(out)


@pytest.mark.parametrize("path", ["/api/resolve", "/api/export/yaml"])
def test_an_empty_or_null_body_is_still_an_empty_draft(path):
    for body in (b"", b"null"):
        status, *_ = _post(path, body)
        assert status != 400 or path != "/api/resolve"


# ---- API-05: the download name ----------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("name", ["a\x00b", "a\x1bb", "a‮b", "a⁦b⁩", "a\x7fb"])
def test_control_and_bidi_characters_never_reach_the_header(name):
    status, _ct, headers, body = _post("/api/export/yaml", exportable_draft(name=name))
    assert status == 200, body[:200]
    cd = headers["Content-Disposition"]
    assert not re.search(r"%00|%1B|%7F|%E2%80%AE|%E2%81%A6|%E2%81%A9", cd, re.I), cd
    assert _name(headers) == "ab.yaml"


@needs_data
@pytest.mark.parametrize("name,expected", [
    ("...", "character.yaml"),
    ("  ", "character.yaml"),
    ("Torvin. . ", "Torvin.yaml"),
    ("CON", "_CON.yaml"),
    ("com1", "_com1.yaml"),
    ("LPT9", "_LPT9.yaml"),
    ("Console", "Console.yaml"),
])
def test_dots_spaces_and_reserved_windows_names(name, expected):
    status, _ct, headers, body = _post("/api/export/yaml", exportable_draft(name=name))
    assert status == 200, body[:200]
    assert _name(headers) == expected
