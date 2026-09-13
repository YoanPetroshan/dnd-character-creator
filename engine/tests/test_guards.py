import json

import pytest

import engine.guards as guards
from engine import state


def test_cyrillic_ratio_detects_bulgarian():
    assert guards.cyrillic_ratio("Мракът се сгъстява около Waterdeep.") > 0.5
    assert guards.cyrillic_ratio("The darkness gathers.") == 0.0


def test_check_language_accepts_bulgarian_with_english_proper_nouns():
    text = "Двамата Dwarf-а прекосиха моста към Waterdeep, където ги чакаше Gundren."
    assert guards.check_language(text, expect="bg") is True


def test_check_language_rejects_english_narration():
    assert guards.check_language("The two dwarves crossed the bridge.", expect="bg") is False


def test_check_language_ignores_short_text():
    assert guards.check_language("OK", expect="bg") is True


def test_find_pc_autorolls_flags_unrequested_roll():
    text = "Falin: d20(14) + 3 = 17 vs DC 15 — УСПЕХ"
    assert guards.find_pc_autorolls(text, ["Falin", "Sparrow"], requested=set()) == ["Falin"]


def test_find_pc_autorolls_allows_requested_roll():
    text = "Falin: d20(14) + 3 = 17 vs DC 15 — УСПЕХ"
    assert guards.find_pc_autorolls(text, ["Falin"], requested={"Falin"}) == []


def test_find_pc_autorolls_ignores_enemy_rolls():
    text = "Goblin Warrior: d20(9) + 4 = 13 vs AC 16 — ПРОПУСК"
    assert guards.find_pc_autorolls(text, ["Falin"], requested=set()) == []


def test_find_pc_autorolls_ignores_enemy_attack_naming_pc_as_target():
    text = "Goblin Warrior attacks Falin: d20(9) + 4 = 13 vs AC 16"
    assert guards.find_pc_autorolls(text, ["Falin"], requested=set()) == []


def test_find_pc_autorolls_ignores_pc_name_mentioned_before_other_actor_rolls():
    text = "Falin гледаше как боецът замахва. Vex Skulk: d20(11) + 5 = 16 vs AC 14"
    assert guards.find_pc_autorolls(text, ["Falin"], requested=set()) == []


def test_find_pc_autorolls_flags_genuine_actor_at_announcement_start():
    text = "Falin: d20(14) + 3 = 17 vs DC 15 — УСПЕХ"
    assert guards.find_pc_autorolls(text, ["Falin"], requested=set()) == ["Falin"]


def test_find_pc_autorolls_matches_requested_name_case_insensitively():
    text = "Sylwen Nightbrook: d20(14) + 5 = 19 vs DC 15 — УСПЕХ"
    names = ["Sylwen Nightbrook"]
    assert guards.find_pc_autorolls(text, names, requested={"sylwen nightbrook"}) == []


def test_find_pc_autorolls_flags_a_real_two_word_name():
    """Every earlier test used single-token names, which is how the
    slug-mangling bug in party_names survived: "Sylwen-Nightbrook" never
    matches the narration, so nothing was ever flagged for a real character."""
    text = "Sylwen Nightbrook: d20(14) + 5 = 19 vs DC 15 — УСПЕХ"
    assert guards.find_pc_autorolls(
        text, ["Sylwen Nightbrook"], requested=set()) == ["Sylwen Nightbrook"]
    assert guards.find_pc_autorolls(
        text, ["Sylwen-Nightbrook"], requested=set()) == []


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    (tmp_path / ".runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path / ".runtime"


def write_log(runtime, entries):
    (runtime / "text_log.json").write_text(json.dumps(entries, ensure_ascii=False))


def test_ensure_display_pushed_noop_when_log_grew(runtime, monkeypatch):
    called = []
    monkeypatch.setattr(guards.display, "send_narration", lambda t: called.append(t) or True)
    write_log(runtime, [{"text": f"ред {i}"} for i in range(3)])
    before = state.text_log_fingerprint()
    write_log(runtime, [{"text": f"ред {i}"} for i in range(5)])
    after = state.text_log_fingerprint()
    assert guards.ensure_display_pushed(before, after, "текст") is False
    assert called == []


def test_ensure_display_pushed_sends_fallback(runtime, monkeypatch):
    called = []
    monkeypatch.setattr(guards.display, "send_narration", lambda t: called.append(t) or True)
    write_log(runtime, [{"text": f"ред {i}"} for i in range(3)])
    before = state.text_log_fingerprint()
    after = state.text_log_fingerprint()
    assert guards.ensure_display_pushed(before, after, "текст") is True
    assert called == ["текст"]


def test_ensure_display_pushed_skips_empty_text(runtime, monkeypatch):
    called = []
    monkeypatch.setattr(guards.display, "send_narration", lambda t: called.append(t) or True)
    write_log(runtime, [{"text": "ред"}])
    marker = state.text_log_fingerprint()
    assert guards.ensure_display_pushed(marker, marker, "   ") is False
    assert called == []


# --- saturated display log (deque(maxlen=60)) -----------------------------

SATURATION = 60


def saturated(runtime, last_text="последен ред"):
    entries = [{"text": f"ред {i}"} for i in range(SATURATION - 1)]
    entries.append({"text": last_text})
    write_log(runtime, entries)
    return entries


def test_ensure_display_pushed_detects_a_push_into_a_saturated_log(runtime, monkeypatch):
    """The display keeps deque(maxlen=60). After one evening of play the count
    stops growing, so the old `after > before` check reported "the agent never
    pushed" on EVERY later turn and double-pushed the raw model response —
    references and OOC block included — on top of correct narration.
    """
    called = []
    monkeypatch.setattr(guards.display, "send_narration", lambda t: called.append(t) or True)

    entries = saturated(runtime)
    before = state.text_log_fingerprint()
    assert before[0] == SATURATION

    # The agent pushes: the oldest entry rolls off, the newest is the narration.
    rolled = entries[1:] + [{"text": "Мракът се сгъстява над криптата."}]
    write_log(runtime, rolled)
    after = state.text_log_fingerprint()
    assert after[0] == SATURATION, "count is saturated — it cannot grow"

    assert guards.ensure_display_pushed(before, after, "raw model text") is False
    assert called == [], "narration was pushed; the fallback must stay silent"


def test_ensure_display_pushed_still_fires_when_saturated_and_nothing_pushed(runtime, monkeypatch):
    called = []
    monkeypatch.setattr(guards.display, "send_narration", lambda t: called.append(t) or True)

    saturated(runtime)
    before = state.text_log_fingerprint()
    after = state.text_log_fingerprint()

    assert guards.ensure_display_pushed(before, after, "Мракът се сгъстява.") is True
    assert called == ["Мракът се сгъстява."]
