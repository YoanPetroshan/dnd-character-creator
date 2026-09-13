import json

import pytest

from engine import encounters
from engine.rules import monster_stats
from engine.rules.cr import cr_key

# Small fixture mirroring the real msbcr.json shape (DMG 2024, "Monster
# Statistics by Challenge Rating") — not the full 0–30 table, just enough
# rows to cover fractional CR, CR 0, and a high CR.
ROWS = [
    {"_cr": "0", "pb": 2, "ac": 13, "hpMin": 1, "hpMax": 6,
     "attackBonus": 3, "dprMin": 0, "dprMax": 1, "saveDc": 13},
    {"_cr": "1/8", "pb": 2, "ac": 13, "hpMin": 7, "hpMax": 35,
     "attackBonus": 3, "dprMin": 2, "dprMax": 3, "saveDc": 13},
    {"_cr": "1/4", "pb": 2, "ac": 13, "hpMin": 36, "hpMax": 49,
     "attackBonus": 3, "dprMin": 4, "dprMax": 5, "saveDc": 13},
    {"_cr": "1/2", "pb": 2, "ac": 13, "hpMin": 50, "hpMax": 70,
     "attackBonus": 3, "dprMin": 6, "dprMax": 8, "saveDc": 13},
    {"_cr": "9", "pb": 4, "ac": 16, "hpMin": 191, "hpMax": 205,
     "attackBonus": 7, "dprMin": 57, "dprMax": 62, "saveDc": 16},
    {"_cr": "20", "pb": 6, "ac": 19, "hpMin": 505, "hpMax": 525,
     "attackBonus": 12, "dprMin": 173, "dprMax": 189, "saveDc": 19},
    {"_cr": "30", "pb": 9, "ac": 19, "hpMin": 805, "hpMax": 850,
     "attackBonus": 14, "dprMin": 303, "dprMax": 320, "saveDc": 23},
]


@pytest.fixture
def data_dir(tmp_path):
    (tmp_path / "msbcr.json").write_text(json.dumps({"cr": ROWS}), encoding="utf-8")
    return tmp_path


def test_load_table_reads_the_real_shape(data_dir):
    rows = monster_stats.load_table(data_dir)
    assert len(rows) == len(ROWS)
    assert rows[0]["_cr"] == "0"


def test_load_table_missing_file_returns_empty(tmp_path):
    assert monster_stats.load_table(tmp_path) == []


def test_find_row_exact_cr(data_dir):
    row = monster_stats.find_row("9", data_dir)
    assert row is not None
    assert row["ac"] == 16
    assert row["saveDc"] == 16


@pytest.mark.parametrize("cr,ac,dpr_min", [
    ("1/8", 13, 2),
    ("1/4", 13, 4),
    ("1/2", 13, 6),
])
def test_find_row_fractional_cr(data_dir, cr, ac, dpr_min):
    row = monster_stats.find_row(cr, data_dir)
    assert row is not None
    assert row["ac"] == ac
    assert row["dprMin"] == dpr_min


def test_find_row_cr_zero(data_dir):
    row = monster_stats.find_row("0", data_dir)
    assert row is not None
    assert row["hpMax"] == 6


def test_find_row_high_cr(data_dir):
    row = monster_stats.find_row("20", data_dir)
    assert row is not None
    assert row["attackBonus"] == 12
    row30 = monster_stats.find_row("30", data_dir)
    assert row30 is not None
    assert row30["pb"] == 9


@pytest.mark.parametrize("cr", ["31", "garbage", "", "-1"])
def test_find_row_unknown_cr_returns_none(data_dir, cr):
    assert monster_stats.find_row(cr, data_dir) is None


def test_find_row_handles_cr_as_dict(data_dir):
    # 5etools represents lair/variant CR as {"cr": "...", "xpLair": ...}.
    # find_row must unwrap it the same way engine.encounters.monster_xp does.
    row = monster_stats.find_row({"cr": "9", "xpLair": 15000}, data_dir)
    assert row is not None
    assert row["_cr"] == "9"


def test_format_row_includes_key_stats(data_dir):
    row = monster_stats.find_row("9", data_dir)
    out = monster_stats.format_row(row)
    assert "CR 9" in out
    assert "AC: 16" in out
    assert "191" in out and "205" in out
    assert "Save DC: 16" in out


# --- Shared CR normalization -------------------------------------------
#
# The whole point of factoring cr_key out into engine.rules.cr is that
# engine.encounters (CR_XP lookups) and engine.rules.monster_stats (msbcr.json
# lookups) never drift into two different, possibly-inconsistent parsers for
# CR-as-dict / CR-as-fraction values — a bug class this project has hit
# before. Confirm both modules are actually using the identical function,
# not just similarly-behaving copies.
def test_encounters_and_monster_stats_share_the_same_cr_normalizer():
    assert encounters.cr_key is cr_key
    assert monster_stats.cr_key is cr_key


def test_cr_key_agrees_on_dict_shaped_cr_across_both_modules():
    dict_cr = {"cr": "14", "xpLair": 13000}
    assert cr_key(dict_cr) == "14"
    # encounters.monster_xp and monster_stats.find_row both funnel through
    # this same normalizer, so a lair CR dict resolves identically in both.
    assert encounters.cr_key(dict_cr) == monster_stats.cr_key(dict_cr) == "14"


# --- CLI -----------------------------------------------------------------

def test_main_prints_stats_for_known_cr(data_dir, monkeypatch, capsys):
    monkeypatch.setattr(monster_stats, "json_dir", lambda: data_dir)
    rc = monster_stats.main(["--cr", "9"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CR 9" in out
    assert "AC: 16" in out
    assert "Справка" in out


def test_main_reports_unknown_cr_with_nonzero_exit(data_dir, monkeypatch, capsys):
    monkeypatch.setattr(monster_stats, "json_dir", lambda: data_dir)
    rc = monster_stats.main(["--cr", "31"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "31" in out
    assert "Няма запис" in out


def test_main_requires_cr_flag():
    with pytest.raises(SystemExit):
        monster_stats.main([])
