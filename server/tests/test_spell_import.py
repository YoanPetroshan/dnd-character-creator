"""Slice 11a: sourcebook spells (5etools spells/*.json -> SRD spell shape).

Every number asserted against real data was computed by script from
/Users/yoanpetrov/Documents/5etools-src/data/spells (2026-10-09); tests that
need the files skip when they are absent (no `DND_5ETOOLS_DATA`, nothing
synced into official_dir()/spells)."""
import json

import pytest

from catalog.official import paths, spells as spells_mod
from catalog.official_source import has_official_spells

needs_spells = pytest.mark.skipif(not has_official_spells(), reason="5etools spell files not available")

# Verified totals (script over index.json, 17 book files).
RAW_TOTAL = 936
RAW_BY_SOURCE = {
    "XPHB": 391, "PHB": 361, "XGE": 95, "TCE": 21, "FRHoF": 19, "EGW": 15, "AI": 7, "FTD": 7,
    "SCC": 5, "BMT": 3, "LLK": 3, "AAG": 2, "IDRotF": 2, "SatO": 2, "AitFR-AVT": 1, "EFA": 1, "GGR": 1,
}


# ---------------------------------------------------------------- 11a.1 data

def _write_spell_dir(root, files=None):
    d = root / "spells"
    d.mkdir(parents=True)
    files = files if files is not None else {"PHB": {"spell": [{"name": "Hex", "source": "PHB"}]}}
    (d / "index.json").write_text(json.dumps({src: f"spells-{src.lower()}.json" for src in files}))
    for src, body in files.items():
        (d / f"spells-{src.lower()}.json").write_text(json.dumps(body))
    (d / "sources.json").write_text(json.dumps({"PHB": {"Hex": {"class": [{"name": "Warlock", "source": "PHB"}]}}}))
    return d


def test_spells_dir_honours_the_env_override(tmp_path, monkeypatch):
    d = _write_spell_dir(tmp_path / "data")
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "data"))
    assert paths.spells_dir() == d
    assert paths.has_official_spells()


def test_spells_dir_falls_back_to_the_official_dir_then_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DND_5ETOOLS_DATA", raising=False)
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.spells_dir() is None
    assert not paths.has_official_spells()
    d = _write_spell_dir(tmp_path / "official")
    assert paths.spells_dir() == d


def test_env_override_pointing_nowhere_falls_through(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "nope"))
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.spells_dir() is None


def test_raw_loader_returns_empty_when_the_directory_is_missing(tmp_path):
    assert spells_mod.load_raw_spells(None) == []
    assert spells_mod.load_raw_spells(tmp_path / "missing") == []
    assert spells_mod.load_spell_class_lookup(tmp_path / "missing") == {}


def test_raw_loader_reads_every_file_in_index_order_and_skips_broken_ones(tmp_path):
    d = _write_spell_dir(tmp_path, {
        "PHB": {"spell": [{"name": "Hex", "source": "PHB"}, {"name": "Fireball", "source": "PHB"}]},
        "XGE": {"spell": [{"name": "Toll the Dead", "source": "XGE"}]},
    })
    (d / "spells-xge.json").write_text("{not json")
    assert [s["name"] for s in spells_mod.load_raw_spells(d)] == ["Hex", "Fireball"]
    assert spells_mod.load_spell_class_lookup(d)["PHB"]["Hex"]["class"][0]["name"] == "Warlock"


@needs_spells
def test_real_spell_files_total_and_per_source_counts():
    raw = spells_mod.load_raw_spells(paths.spells_dir())
    assert len(raw) == RAW_TOTAL
    counts = {}
    for s in raw:
        counts[s["source"]] = counts.get(s["source"], 0) + 1
    assert counts == RAW_BY_SOURCE
    assert not any("_copy" in s for s in raw)
