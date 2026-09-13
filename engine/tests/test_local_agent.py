import asyncio

import pytest

from engine import local_agent
from engine.config import Config


def make_agent(campaign="demo"):
    return local_agent.LocalDMAgent(Config(), system_prompt="SP", campaign=campaign)


@pytest.fixture
def campaign_root(tmp_path, monkeypatch):
    """A campaign with one character sheet, for HP-writing marker tests."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "characters" / "torvin-bracewell.md").write_text(
        "# Torvin Bracewell\n\n## Combat Stats\n- **HP:** 12 / 12\n",
        encoding="utf-8",
    )
    return camp


@pytest.fixture(autouse=True)
def no_real_display_calls(monkeypatch):
    """Every test in this file runs with DND_CAMPAIGN_ROOT unset or pointed
    at a throwaway tmp_path — display.push() must never shell out for real."""
    monkeypatch.setattr(local_agent.display, "push", lambda **kw: True)


# --- _split_at_marker -------------------------------------------------

def test_split_at_marker_no_marker_returns_whole_text_and_none():
    text, marker = local_agent._split_at_marker("Просто наратив, без хвърляне.")
    assert text == "Просто наратив, без хвърляне."
    assert marker is None


def test_split_at_marker_splits_prefix_from_marker():
    text, marker = local_agent._split_at_marker(
        "Sylwen се промъква напред.\n[ROLL|Sylwen|1d20|+2|Stealth|15|normal]"
    )
    assert text == "Sylwen се промъква напред.\n"
    assert marker == ("ROLL", "Sylwen|1d20|+2|Stealth|15|normal")


# --- _resolve_marker: ROLL / ATTACK / DMROLL -----------------------------

def test_resolve_roll_marker_reports_success_against_dc(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 17)
    visible, outcome = local_agent._resolve_marker(
        "ROLL", "Sylwen|1d20|+2|Stealth|15|normal", "demo"
    )
    assert visible
    assert "Sylwen" in outcome
    assert "= 17" in outcome
    assert "УСПЕХ" in outcome


def test_resolve_roll_marker_reports_failure_against_dc(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 9)
    _, outcome = local_agent._resolve_marker(
        "ROLL", "Sylwen|1d20|+2|Stealth|15|normal", "demo"
    )
    assert "ПРОВАЛ" in outcome


def test_resolve_roll_marker_no_dc_reports_total_only(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 12)
    _, outcome = local_agent._resolve_marker("ROLL", "Torvin|1d20|+3|Attack|-|normal", "demo")
    assert "= 12" in outcome
    assert "УСПЕХ" not in outcome and "ПРОВАЛ" not in outcome


def test_resolve_roll_marker_timeout_asks_to_speak_up(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: None)
    _, outcome = local_agent._resolve_marker("ROLL", "Torvin|1d20|+3|Attack|-|normal", "demo")
    assert "няма отговор" in outcome


def test_resolve_attack_marker_without_target_uses_dice_enemy_attack(monkeypatch):
    monkeypatch.setattr(
        local_agent.dice, "enemy_attack",
        lambda *a, **k: {"line": "Goblin: d20(14) + 4 = 18 vs AC 15 — УДАР", "damage": 0},
    )
    visible, outcome = local_agent._resolve_marker("ATTACK", "Goblin|+4|15|1|6|2", "demo")
    assert visible
    assert outcome == "Goblin: d20(14) + 4 = 18 vs AC 15 — УДАР"


def test_resolve_attack_marker_with_target_applies_damage_and_pushes_stats(
    monkeypatch, campaign_root
):
    monkeypatch.setattr(
        local_agent.dice, "enemy_attack",
        lambda *a, **k: {"line": "Goblin hits Torvin", "damage": 5},
    )
    pushed = {}
    monkeypatch.setattr(
        local_agent.display, "push",
        lambda **kw: pushed.update(kw) or True,
    )
    visible, outcome = local_agent._resolve_marker(
        "ATTACK", "Goblin|+4|15|1|6|2|Torvin Bracewell", "demo"
    )
    assert visible
    assert "Torvin Bracewell: HP 7/12" in outcome
    assert pushed == {"player": "Torvin Bracewell", "hp": [7, 12]}
    assert local_agent.local_context.read_hp("demo", "Torvin Bracewell") == (7, 12)


def test_resolve_attack_marker_with_unknown_target_skips_hp_write(monkeypatch, campaign_root):
    monkeypatch.setattr(
        local_agent.dice, "enemy_attack",
        lambda *a, **k: {"line": "Goblin hits Nobody", "damage": 5},
    )
    visible, outcome = local_agent._resolve_marker(
        "ATTACK", "Goblin|+4|15|1|6|2|Nobody", "demo"
    )
    assert visible
    assert outcome == "Goblin hits Nobody"


def test_resolve_dmroll_marker_reports_dc_outcome(monkeypatch):
    result = local_agent.dice.RollResult(d20=16, total=19, detail="d20(16) + 3 = 19")
    monkeypatch.setattr(local_agent.dice, "roll_d20", lambda **k: result)
    _, outcome = local_agent._resolve_marker("DMROLL", "1d20|+3|Perception|12", "demo")
    assert "УСПЕХ" in outcome
    assert "Perception" in outcome


def test_resolve_marker_malformed_field_count_returns_none():
    assert local_agent._resolve_marker("ROLL", "just|two", "demo") is None


def test_resolve_marker_malformed_non_integer_returns_none():
    assert local_agent._resolve_marker("ATTACK", "Goblin|+4|not-a-number|1|6|2", "demo") is None


# --- _resolve_marker: DAMAGE / HEAL ---------------------------------------

def test_resolve_damage_marker_applies_and_pushes(monkeypatch, campaign_root):
    pushed = {}
    monkeypatch.setattr(local_agent.display, "push", lambda **kw: pushed.update(kw) or True)
    visible, outcome = local_agent._resolve_marker(
        "DAMAGE", "Torvin Bracewell|4|fall", "demo"
    )
    assert visible
    assert "-4 HP" in outcome
    assert "8/12" in outcome
    assert pushed == {"player": "Torvin Bracewell", "hp": [8, 12]}


def test_resolve_heal_marker_applies_and_clamps_to_max(monkeypatch, campaign_root):
    local_agent.local_context.apply_hp_delta("demo", "Torvin Bracewell", -10)
    visible, outcome = local_agent._resolve_marker(
        "HEAL", "Torvin Bracewell|999|cure wounds", "demo"
    )
    assert visible
    assert "12/12" in outcome


def test_resolve_damage_marker_unknown_character_returns_none(campaign_root):
    assert local_agent._resolve_marker("DAMAGE", "Nobody|5|trap", "demo") is None


# --- _resolve_marker: LOOKUP ----------------------------------------------

def test_resolve_lookup_marker_is_invisible(monkeypatch):
    monkeypatch.setattr(local_agent, "_lookup_text", lambda kind, name: "STATBLOCK TEXT")
    visible, outcome = local_agent._resolve_marker("LOOKUP", "monster|Goblin", "demo")
    assert not visible
    assert outcome == "STATBLOCK TEXT"


def test_resolve_lookup_marker_missing_name_is_malformed():
    assert local_agent._resolve_marker("LOOKUP", "monster|", "demo") is None


def test_lookup_text_falls_back_to_unknown_kind(monkeypatch):
    monkeypatch.setattr(local_agent.lookup, "find", lambda name, kind=None: None)
    monkeypatch.setattr(local_agent.lookup, "srd_fallback", lambda name, cat=None: None)
    text = local_agent._lookup_text("not-a-real-kind", "Something")
    assert "Something" in text


# --- LocalDMAgent._chat_checked ------------------------------------------

def test_chat_checked_returns_bulgarian_reply_without_retrying():
    agent = make_agent()
    calls = []

    def fake(messages, on_text=None):
        calls.append(messages)
        return "Стаята е тиха."

    agent._chat = fake
    result = agent._chat_checked([{"role": "user", "content": "х"}])
    assert result == "Стаята е тиха."
    assert len(calls) == 1


def test_chat_checked_retries_once_on_english_drift():
    agent = make_agent()
    replies = iter(["The room is quiet and dusty tonight.", "Стаята е тиха."])
    calls = []

    def fake(messages, on_text=None):
        calls.append(messages)
        return next(replies)

    agent._chat = fake
    result = agent._chat_checked([{"role": "user", "content": "х"}])
    assert result == "Стаята е тиха."
    assert len(calls) == 2


def test_chat_checked_skips_language_check_for_english_campaigns():
    agent = local_agent.LocalDMAgent(Config(language="en"), system_prompt="SP", campaign="demo")
    calls = []

    def fake(messages, on_text=None):
        calls.append(messages)
        return "The room is quiet."

    agent._chat = fake
    result = agent._chat_checked([{"role": "user", "content": "x"}])
    assert result == "The room is quiet."
    assert len(calls) == 1


# --- LocalDMAgent.run_turn ------------------------------------------------

def test_run_turn_plain_narration_passes_through():
    agent = make_agent()
    agent._chat = lambda messages, on_text=None: "Стаята е тиха и прашна."
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert result.text == "Стаята е тиха и прашна."


def test_run_turn_resolves_a_roll_then_continues(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 17)
    agent = make_agent()
    replies = iter([
        "Sylwen се промъква напред.\n[ROLL|Sylwen|1d20|+2|Stealth|15|normal]",
        "Тя изчезва безшумно в сенките.",
    ])
    agent._chat = lambda messages, on_text=None: next(replies)
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert "Sylwen се промъква напред." in result.text
    assert "УСПЕХ" in result.text
    assert "Тя изчезва безшумно в сенките." in result.text


def test_run_turn_resolves_a_lookup_without_showing_it_in_narration(monkeypatch):
    monkeypatch.setattr(local_agent, "_lookup_text", lambda kind, name: "AC 17 | HP 21")
    agent = make_agent()
    replies = iter([
        "Иззад ъгъла изскача гоблин.\n[LOOKUP|monster|Goblin]",
        "Гоблинът размахва ятагана си свирепо.",
    ])
    agent._chat = lambda messages, on_text=None: next(replies)
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert "Иззад ъгъла изскача гоблин." in result.text
    assert "Гоблинът размахва ятагана си свирепо." in result.text
    assert "AC 17" not in result.text  # reference text never shown to the player


def test_run_turn_malformed_marker_does_not_crash():
    agent = make_agent()
    agent._chat = lambda messages, on_text=None: "Текст. [ROLL|badonly]"
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert "Текст." in result.text


def test_run_turn_network_failure_is_not_ok():
    agent = make_agent()

    def boom(messages, on_text=None):
        raise OSError("connection refused")

    agent._chat = boom
    result = asyncio.run(agent.run_turn("промпт"))
    assert not result.ok
    assert "local_backend_error" in result.error


def test_run_turn_caps_roll_iterations(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 10)
    agent = make_agent()
    calls = {"n": 0}

    def always_marker(messages, on_text=None):
        calls["n"] += 1
        return "Реплика. [ROLL|Torvin|1d20|+1|Check|10|normal]"

    agent._chat = always_marker
    result = asyncio.run(agent.run_turn("промпт"))
    assert calls["n"] == local_agent.MAX_ROLL_ITERATIONS
    assert result.ok


# --- streaming: safe emit boundaries --------------------------------------

def test_safe_emit_limit_stops_before_an_unclosed_marker():
    buf = "Sylwen пристъпва напред. [ROLL|Sylwen|1d2"
    limit = local_agent._safe_emit_limit(buf, 0)
    assert buf[:limit] == "Sylwen пристъпва напред. "


def test_safe_emit_limit_allows_text_past_a_closed_bracket():
    buf = "Той взе [нещо] от масата."
    assert local_agent._safe_emit_limit(buf, 0) == len(buf)


def test_emit_point_first_emission_fires_on_one_sentence():
    buf = "Първо изречение. Второто още се пише"
    point = local_agent._emit_point(buf, 0, first_emission=True)
    assert buf[:point] == "Първо изречение. "


def test_emit_point_first_emission_waits_for_a_full_sentence():
    buf = "Още няма край на изречението"
    assert local_agent._emit_point(buf, 0, first_emission=True) == 0


def test_emit_point_later_emissions_wait_for_a_paragraph_break():
    buf = "Изречение едно. Изречение две. "
    assert local_agent._emit_point(buf, 0, first_emission=False) == 0
    buf2 = "Абзац едно.\n\nАбзац две"
    point = local_agent._emit_point(buf2, 0, first_emission=False)
    assert buf2[:point] == "Абзац едно.\n\n"


def test_emit_point_never_emits_a_partial_marker():
    buf = "Разказ. [ROLL|Sylwen"
    point = local_agent._emit_point(buf, 0, first_emission=True)
    assert "[ROLL" not in buf[:point]


# --- streaming: _chat over a fake Ollama stream ----------------------------

def _stream_bytes(*chunks, done_last=True):
    """Encode chunks as Ollama's newline-delimited streaming JSON."""
    import json as _json
    lines = []
    for i, c in enumerate(chunks):
        last = done_last and i == len(chunks) - 1
        lines.append(_json.dumps({"message": {"content": c}, "done": last}).encode())
    return lines


def test_chat_streams_and_emits_narration_in_order(monkeypatch):
    agent = make_agent()

    class FakeResp:
        def __init__(self, lines): self._lines = lines
        def __enter__(self): return self._lines
        def __exit__(self, *a): return False

    monkeypatch.setattr(
        agent, "_post",
        lambda payload: FakeResp(_stream_bytes(
            "Първо изречение. ", "Още текст.\n\n", "Втори абзац.",
        )),
    )
    seen = []
    reply = agent._chat([{"role": "user", "content": "х"}], seen.append)
    assert reply == "Първо изречение. Още текст.\n\nВтори абзац."
    assert seen[0] == "Първо изречение. "
    assert "".join(seen) == reply


def test_chat_stream_stops_at_a_complete_marker(monkeypatch):
    agent = make_agent()
    consumed = []

    class FakeResp:
        def __init__(self, lines): self._lines = lines
        def __enter__(self):
            def gen():
                for ln in self._lines:
                    consumed.append(ln)
                    yield ln
            return gen()
        def __exit__(self, *a): return False

    monkeypatch.setattr(
        agent, "_post",
        lambda payload: FakeResp(_stream_bytes(
            "Разказ. ", "[ROLL|Sylwen|1d20|+2|Stealth|15|normal]",
            "ТОВА НЕ ТРЯБВА ДА СЕ ЧЕТЕ", done_last=False,
        )),
    )
    seen = []
    reply = agent._chat([{"role": "user", "content": "х"}], seen.append)
    assert "ТОВА НЕ ТРЯБВА ДА СЕ ЧЕТЕ" not in reply
    assert len(consumed) == 2  # stopped reading at the marker
    assert "[ROLL" not in "".join(seen)  # marker never shown to the player


def test_chat_without_callback_uses_the_blocking_path(monkeypatch):
    agent = make_agent()
    seen_payloads = []

    class FakeResp:
        def __enter__(self):
            import io, json as _json
            return io.BytesIO(_json.dumps({"message": {"content": "Текст."}}).encode())
        def __exit__(self, *a): return False

    def fake_post(payload):
        seen_payloads.append(payload)
        return FakeResp()

    monkeypatch.setattr(agent, "_post", fake_post)
    assert agent._chat([{"role": "user", "content": "х"}]) == "Текст."
    assert seen_payloads[0]["stream"] is False


# --- streaming: language gate ---------------------------------------------

def test_language_gate_blocks_english_from_reaching_the_player():
    agent = make_agent()
    replies = iter(["The room is quiet and dusty tonight.", "Стаята е тиха."])

    def fake(messages, on_text=None):
        text = next(replies)
        if on_text:
            on_text(text)
        return text

    agent._chat = fake
    seen = []
    result = agent._chat_checked([{"role": "user", "content": "х"}], seen.append)
    assert result == "Стаята е тиха."
    assert seen == ["Стаята е тиха."]  # the English attempt never reached the display


def test_language_gate_keeps_a_reply_that_drifts_after_the_first_chunk():
    agent = make_agent()

    def fake(messages, on_text=None):
        if on_text:
            on_text("Стаята е тиха. ")
        return "Стаята е тиха. " + "The rest drifted into English entirely here."

    agent._chat = fake
    seen = []
    result = agent._chat_checked([{"role": "user", "content": "х"}], seen.append)
    # Already on screen -- retrying would show the scene's opening twice.
    assert "Стаята е тиха." in result
    assert seen == ["Стаята е тиха. "]


# --- run_turn: incremental push -------------------------------------------

def test_run_turn_pushes_narration_and_roll_outcomes_as_they_happen(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 17)
    pushed = []
    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo", on_narration=pushed.append,
    )
    replies = iter([
        "Sylwen се промъква.\n[ROLL|Sylwen|1d20|+2|Stealth|15|normal]",
        "Тя изчезва в сенките.",
    ])

    def fake(messages, on_text=None):
        text = next(replies)
        if on_text:
            prefix, _ = local_agent._split_at_marker(text)
            on_text(prefix)
        return text

    agent._chat = fake
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert any("Sylwen се промъква" in p for p in pushed)
    assert any("🎲" in p and "УСПЕХ" in p for p in pushed)
    assert all(p.endswith("\n") for p in pushed)  # keeps the display's TTS text intact


def test_run_turn_push_failure_does_not_break_the_turn(monkeypatch):
    def boom(chunk):
        raise OSError("display is down")

    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo", on_narration=boom,
    )
    agent._chat = lambda messages, on_text=None: (on_text("Текст.") if on_text else None) or "Текст."
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert "Текст." in result.text


def test_run_turn_without_callback_pushes_nothing_midturn():
    agent = make_agent()
    agent._chat = lambda messages, on_text=None: "Само текст, без маркер."
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok
    assert result.text == "Само текст, без маркер."


# --- keep_alive / num_predict ---------------------------------------------

def test_payload_keeps_the_model_resident_and_caps_generation():
    agent = make_agent()
    payload = agent._payload([{"role": "user", "content": "х"}], stream=False)
    # Finite, not -1: "forever" pins ~3.1GB of an 8GB machine and only ever
    # releases if stop() runs, which a crash or kill -9 skips.
    assert payload["keep_alive"] == "30m"
    assert payload["options"]["num_predict"] == agent.num_predict
    assert payload["think"] is False


def test_stop_releases_the_model(monkeypatch):
    agent = make_agent()
    sent = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b""

    def fake_urlopen(req, timeout=None):
        sent["body"] = __import__("json").loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr(local_agent.urllib.request, "urlopen", fake_urlopen)
    asyncio.run(agent.stop())
    assert sent["body"]["keep_alive"] == 0


def test_stop_survives_an_unreachable_server(monkeypatch):
    agent = make_agent()
    monkeypatch.setattr(
        local_agent.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("refused")),
    )
    asyncio.run(agent.stop())  # must not raise


# --- on_turn_end: TTS pre-warm handoff -------------------------------------

def test_run_turn_hands_pushed_blocks_to_the_turn_end_hook():
    handed = []
    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo",
        on_narration=lambda c: None, on_turn_end=handed.append,
    )
    agent._chat = lambda messages, on_text=None: (
        on_text("Разказ.") if on_text else None) or "Разказ."
    asyncio.run(agent.run_turn("промпт"))
    assert handed and handed[0] == ["Разказ.\n"]


def test_run_turn_skips_the_hook_when_nothing_was_pushed():
    handed = []
    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo", on_turn_end=handed.append,
    )
    agent._chat = lambda messages, on_text=None: "Разказ."
    asyncio.run(agent.run_turn("промпт"))
    assert handed == []


def test_run_turn_survives_a_failing_turn_end_hook():
    def boom(blocks):
        raise OSError("tts queue exploded")

    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo",
        on_narration=lambda c: None, on_turn_end=boom,
    )
    agent._chat = lambda messages, on_text=None: (
        on_text("Разказ.") if on_text else None) or "Разказ."
    result = asyncio.run(agent.run_turn("промпт"))
    assert result.ok


# --- warm-up ---------------------------------------------------------------

def test_start_warms_the_model_with_the_real_system_prompt(monkeypatch):
    agent = make_agent()
    posted = []

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    monkeypatch.setattr(
        local_agent.urllib.request, "urlopen",
        lambda *a, **k: FakeResp(),
    )
    monkeypatch.setattr(agent, "_post", lambda payload: posted.append(payload) or FakeResp())
    asyncio.run(agent.start())
    assert posted, "start() did not warm the model"
    warm = posted[0]
    assert warm["messages"][0]["content"] == "SP"   # the real system prompt
    assert warm["options"]["num_predict"] == 1      # load + prime only, no narration


def test_start_survives_a_failing_warm_up(monkeypatch):
    agent = make_agent()

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    monkeypatch.setattr(local_agent.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    monkeypatch.setattr(
        agent, "_post",
        lambda payload: (_ for _ in ()).throw(OSError("model busy")),
    )
    asyncio.run(agent.start())  # must not raise
    assert agent._ready


def test_start_skips_warm_up_when_the_backend_is_unreachable(monkeypatch):
    agent = make_agent()
    posted = []
    monkeypatch.setattr(
        local_agent.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("refused")),
    )
    monkeypatch.setattr(agent, "_post", lambda payload: posted.append(payload))
    asyncio.run(agent.start())
    assert not agent._ready
    assert posted == []


# --- repetition guard ------------------------------------------------------

def test_repeat_key_normalises_whitespace_and_case():
    a = local_agent._repeat_key("  Силватър усеща лека промяна във въздуха някъде  ")
    b = local_agent._repeat_key("силватър усеща лека промяна във въздуха някъде зад дивана")
    assert a == b


def test_run_turn_suppresses_a_repeated_beat(monkeypatch):
    """A restated sentence is clutter on screen and a line read aloud twice
    through the Bulgarian audio connector -- observed in a real turn."""
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 15)
    pushed = []
    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo", on_narration=pushed.append,
    )
    line = "Силватър усеща лека промяна във въздуха, някъде зад дивана нещо помръдва."
    replies = iter([
        f"{line}\n[ROLL|Sylwen|1d20|+2|Perception|15|normal]",
        line,  # the model restates the same beat
    ])

    def fake(messages, on_text=None):
        text = next(replies)
        if on_text:
            prefix, _ = local_agent._split_at_marker(text)
            on_text(prefix)
        return text

    agent._chat = fake
    asyncio.run(agent.run_turn("промпт"))
    narration = [p for p in pushed if "🎲" not in p]
    assert len(narration) == 1, f"repeat was not suppressed: {narration}"


def test_run_turn_keeps_genuinely_different_beats(monkeypatch):
    monkeypatch.setattr(local_agent.dice, "request_pc_roll", lambda *a, **k: 15)
    pushed = []
    agent = local_agent.LocalDMAgent(
        Config(), system_prompt="SP", campaign="demo", on_narration=pushed.append,
    )
    replies = iter([
        "Sylwen пристъпва към вратата и се вслушва в тишината зад нея.\n"
        "[ROLL|Sylwen|1d20|+2|Perception|15|normal]",
        "Torvin вдига щита си и заема позиция до колоната отсреща.",
    ])

    def fake(messages, on_text=None):
        text = next(replies)
        if on_text:
            prefix, _ = local_agent._split_at_marker(text)
            on_text(prefix)
        return text

    agent._chat = fake
    asyncio.run(agent.run_turn("промпт"))
    narration = [p for p in pushed if "🎲" not in p]
    assert len(narration) == 2


# --- truncation (num_predict hit) ------------------------------------------

def test_trim_to_last_sentence_drops_a_severed_tail():
    """Bulgarian narration cut mid-word by num_predict, as seen at the table."""
    buf = "Стаята е тиха. Мъглата се стеле бавно. Тър"
    out = local_agent._trim_to_last_sentence(buf, already_emitted=0)
    assert out == "Стаята е тиха. Мъглата се стеле бавно."


def test_trim_to_last_sentence_never_cuts_below_what_was_shown():
    """Text already pushed to the display cannot be taken back."""
    buf = "Стаята е тиха. Мъглата се стеле. Той тръгва напре"
    shown = len("Стаята е тиха. Мъглата се стеле. ")
    out = local_agent._trim_to_last_sentence(buf, already_emitted=shown)
    assert out.startswith("Стаята е тиха. Мъглата се стеле.")
    assert "напре" not in out


def test_trim_to_last_sentence_keeps_a_partial_when_nothing_finished():
    buf = "Само едно недовършено изречен"
    assert local_agent._trim_to_last_sentence(buf, already_emitted=0) == buf


def test_chat_trims_a_length_truncated_stream(monkeypatch):
    agent = make_agent()

    class FakeResp:
        def __init__(self, lines): self._lines = lines
        def __enter__(self): return iter(self._lines)
        def __exit__(self, *a): return False

    import json as _json
    lines = [
        _json.dumps({"message": {"content": "Стаята е тиха. "}, "done": False}).encode(),
        _json.dumps({"message": {"content": "Мъглата се стеле. Тър"},
                     "done": True, "done_reason": "length"}).encode(),
    ]
    monkeypatch.setattr(agent, "_post", lambda payload: FakeResp(lines))
    seen = []
    reply = agent._chat([{"role": "user", "content": "х"}], seen.append)
    assert not reply.endswith("Тър")
    assert "Мъглата се стеле." in reply


def test_chat_leaves_a_naturally_finished_stream_alone(monkeypatch):
    agent = make_agent()

    class FakeResp:
        def __init__(self, lines): self._lines = lines
        def __enter__(self): return iter(self._lines)
        def __exit__(self, *a): return False

    import json as _json
    lines = [
        _json.dumps({"message": {"content": "Стаята е тиха и прашна."},
                     "done": True, "done_reason": "stop"}).encode(),
    ]
    monkeypatch.setattr(agent, "_post", lambda payload: FakeResp(lines))
    reply = agent._chat([{"role": "user", "content": "х"}], lambda c: None)
    assert reply == "Стаята е тиха и прашна."
