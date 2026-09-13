import json

import pytest

from engine import dice, log


def test_roll_d20_in_range_and_adds_modifier(monkeypatch):
    monkeypatch.setattr(dice, "_d", lambda sides: 13)
    r = dice.roll_d20(modifier=4)
    assert r.d20 == 13
    assert r.total == 17
    assert not r.crit and not r.fumble


def test_roll_d20_flags_crit_and_fumble(monkeypatch):
    monkeypatch.setattr(dice, "_d", lambda sides: 20)
    assert dice.roll_d20().crit is True
    monkeypatch.setattr(dice, "_d", lambda sides: 1)
    assert dice.roll_d20().fumble is True


def test_advantage_takes_higher(monkeypatch):
    seq = iter([5, 18])
    monkeypatch.setattr(dice, "_d", lambda sides: next(seq))
    assert dice.roll_d20(advantage="advantage").d20 == 18


def test_disadvantage_takes_lower(monkeypatch):
    seq = iter([5, 18])
    monkeypatch.setattr(dice, "_d", lambda sides: next(seq))
    assert dice.roll_d20(advantage="disadvantage").d20 == 5


def test_resolve_attack_equal_to_ac_hits():
    assert dice.resolve_attack(total=15, target_ac=15) == "УДАР"


def test_resolve_attack_nat20_always_hits():
    assert dice.resolve_attack(total=3, target_ac=25, nat20=True) == "КРИТИЧЕН УДАР"


def test_resolve_attack_nat1_always_misses():
    assert dice.resolve_attack(total=40, target_ac=5, nat1=True) == "КРИТИЧЕН ПРОПУСК"


def test_crit_doubles_dice_not_modifier(monkeypatch):
    monkeypatch.setattr(dice, "_d", lambda sides: 20 if sides == 20 else 3)
    out = dice.enemy_attack("Goblin", atk_mod=4, target_ac=16,
                            num_dice=1, die=6, dmg_mod=2)
    assert out["status"] == "КРИТИЧЕН УДАР"
    assert len(out["damage_dice"]) == 2
    assert out["damage"] == 3 + 3 + 2


def test_miss_deals_no_damage(monkeypatch):
    monkeypatch.setattr(dice, "_d", lambda sides: 2)
    out = dice.enemy_attack("Goblin", atk_mod=0, target_ac=18,
                            num_dice=1, die=6, dmg_mod=2)
    assert out["status"] == "ПРОПУСК"
    assert out["damage"] == 0


@pytest.mark.parametrize("damage,expected", [(0, 10), (10, 10), (22, 11), (100, 30)])
def test_concentration_dc(damage, expected):
    assert dice.concentration_dc(damage) == expected


def test_roll_dice_count_and_bounds():
    rolls = dice.roll_dice(5, 6)
    assert len(rolls) == 5
    assert all(1 <= r <= 6 for r in rolls)


# --- request_pc_roll ------------------------------------------------------
#
# The realistic contract, verified against the real code:
#   * `send.py --dice-request --wait` prints ONLY the hex request id on stdout
#     (skills/dnd/display/send.py: `print(request_id, flush=True)`); every
#     status line the wait loop emits goes to stderr.
#   * the player's actual total is appended to the display's text log by
#     /player-input/dice as
#       f"{character} rolls {spec}{mod_str}: {breakdown} = {total}{suffix}"
#     (skills/dnd/display/dnd-display-app.py).
# So these tests stub dice_request with a request id and put a real-format
# entry in text_log.json — never a bare number as a return value.

REQUEST_ID = "9f3c1a7be2d04a11"


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    (tmp_path / ".runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path / ".runtime"


def write_log(runtime, entries):
    (runtime / "text_log.json").write_text(json.dumps(entries, ensure_ascii=False))


def test_request_pc_roll_reads_the_total_from_the_text_log(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Мракът се сгъстява над криптата."},
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19 — Stealth check",
         "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll(
        "Sylwen Nightbrook", "1d20", 5, "Stealth check") == 19


def test_request_pc_roll_never_parses_the_request_id(runtime, monkeypatch):
    """The old implementation ran a bare `\\d+` search over dice_request's
    return value — the hex request id — and handed the DM a garbage digit as
    the player's total. Here the id starts with "9", so the regression would
    return 9 instead of the real 19."""
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    total = dice.request_pc_roll("Sylwen Nightbrook", "1d20", 5, "")
    assert total == 19
    assert total != 9


def test_request_pc_roll_takes_the_newest_matching_entry(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [3] = 8", "dice": True},
        {"text": "Torvin Bracewell rolls 1d20+3: [20] = 23", "dice": True},
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Sylwen Nightbrook", "1d20", 5, "") == 19
    assert dice.request_pc_roll("Torvin Bracewell", "1d20", 3, "") == 23


def test_request_pc_roll_handles_advantage_breakdown_and_label_suffix(runtime, monkeypatch):
    # Real advantage format, with a trailing label suffix after the total.
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [7, 18] → keep 18 (advantage) "
                 "+5 = 23 — Perception check", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll(
        "Sylwen Nightbrook", "1d20", 5, "Perception check",
        advantage="advantage") == 23


def test_request_pc_roll_handles_negative_total(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Torvin Bracewell rolls 1d20-3: [1] -3 = -2", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Torvin Bracewell", "1d20", -3, "") == -2


def test_request_pc_roll_ignores_non_dice_entries_quoting_a_roll(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19", "dice": True},
        {"text": "Sylwen Nightbrook rolls 1d20+5: [1] = 6 (narration echo)"},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Sylwen Nightbrook", "1d20", 5, "") == 19


def test_request_pc_roll_returns_none_when_no_entry_landed(runtime, monkeypatch):
    write_log(runtime, [{"text": "Torvin Bracewell rolls 1d20+3: [9] = 12",
                         "dice": True}])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Sylwen Nightbrook", "1d20", 5, "") is None


def test_request_pc_roll_returns_none_on_timeout(runtime, monkeypatch):
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: None)
    assert dice.request_pc_roll("Sylwen Nightbrook", "1d20", 3, "Initiative") is None


def test_request_pc_roll_logs_a_pc_roll_event_the_guard_can_read(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    dice.request_pc_roll("Sylwen Nightbrook", "1d20", 5, "Stealth")
    events = [e for e in log.read_events(limit=50) if e["event"] == "pc_roll"]
    assert events and events[-1]["character"] == "Sylwen Nightbrook"
    assert events[-1]["total"] == 19


@pytest.mark.parametrize("raw,normalized", [
    ("d20", "1d20"), ("1D20", "1d20"), ("2d6", "2d6"), (" 1d20 ", "1d20"),
])
def test_normalize_spec(raw, normalized):
    assert dice.normalize_spec(raw) == normalized


def test_request_pc_roll_normalizes_spec_before_matching(runtime, monkeypatch):
    """The display only accepts NdM and logs exactly what it received, so a
    caller passing "d20" must still find the "1d20" entry."""
    sent = {}
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request",
                        lambda **kw: sent.update(kw) or REQUEST_ID)
    assert dice.request_pc_roll("Sylwen Nightbrook", "d20", 5, "") == 19
    assert sent["spec"] == "1d20"


# --- CLI ------------------------------------------------------------------


def test_cli_prints_only_the_total(runtime, monkeypatch, capsys):
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19 — Stealth check",
         "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    code = dice.main(["pc", "--character", "Sylwen Nightbrook", "--spec", "1d20",
                      "--modifier", "5", "--label", "Stealth check", "--dc", "15"])
    assert code == 0
    assert capsys.readouterr().out.strip() == "19"


def test_cli_forwards_every_flag_to_the_display(runtime, monkeypatch):
    sent = {}
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+5: [14] = 19", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request",
                        lambda **kw: sent.update(kw) or REQUEST_ID)
    dice.main(["pc", "--character", "Sylwen Nightbrook", "--spec", "1d20",
               "--modifier", "5", "--label", "Stealth", "--dc", "15",
               "--advantage", "advantage"])
    assert sent["character"] == "Sylwen Nightbrook"
    assert sent["modifier"] == 5
    assert sent["label"] == "Stealth"
    assert sent["dc"] == 15
    assert sent["advantage"] == "advantage"
    assert sent["wait"] is True


def test_cli_reports_timeout_without_inventing_a_number(runtime, monkeypatch, capsys):
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: None)
    code = dice.main(["pc", "--character", "Sylwen Nightbrook"])
    out = capsys.readouterr().out
    assert code == 1
    assert out.startswith("TIMEOUT")
    assert not any(ch.isdigit() for ch in out.split(":")[0])


# --- manually entered rolls -------------------------------------------------
# For a table with real dice on it: the player types what the dice show and
# the display adds the modifier. The feed text picks up a "manual" marker, so
# these pin that the DM still reads the total out of it exactly as before —
# resolved_pc_roll matches on the text PREFIX, and the marker sits after it.


def test_request_pc_roll_reads_a_manually_entered_roll(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+3: [17 manual] +3 = 20 — Arcana check",
         "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll(
        "Sylwen Nightbrook", "1d20", 3, "Arcana check") == 20


def test_manual_roll_keeps_the_natural_die_distinguishable(runtime, monkeypatch):
    """The whole reason the manual field excludes the modifier: a 17 with a
    +3 totals 20 but is NOT a natural 20, and the DM has to be able to tell
    those apart. The raw value stays in the bracketed position either way."""
    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+3: [17 manual] +3 = 20", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Sylwen Nightbrook", "1d20", 3, "") == 20

    write_log(runtime, [
        {"text": "Sylwen Nightbrook rolls 1d20+3: [20 manual] +3 = 23", "dice": True},
    ])
    # Same total is unreachable from a natural 20 here; the totals differ, and
    # the bracketed raw is what says which one actually happened.
    assert dice.request_pc_roll("Sylwen Nightbrook", "1d20", 3, "") == 23


def test_request_pc_roll_reads_a_manual_multi_die_sum(runtime, monkeypatch):
    """2d8 is entered as the sum the dice show (5 and 7 → 12), not face by
    face — the individual faces change no outcome."""
    write_log(runtime, [
        {"text": "Torvin Bracewell rolls 2d8+2: [12 manual] +2 = 14 — Damage",
         "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Torvin Bracewell", "2d8", 2, "Damage") == 14


def test_request_pc_roll_reads_a_manual_roll_with_a_negative_modifier(runtime, monkeypatch):
    write_log(runtime, [
        {"text": "Torvin Bracewell rolls 1d20-2: [10 manual] -2 = 8", "dice": True},
    ])
    monkeypatch.setattr(dice.display, "dice_request", lambda **kw: REQUEST_ID)
    assert dice.request_pc_roll("Torvin Bracewell", "1d20", -2, "") == 8
