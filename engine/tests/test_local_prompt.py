import pytest

from engine import local_prompt
from engine.config import Config

GLOSSARY = {
    "terms": [{"en": "Stealth", "bg": "Скриване (Stealth)"}],
    "keep_english": ["Advantage", "HP"],
    "never_translate": ["Waterdeep"],
}


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    camp.mkdir(parents=True)
    (camp / "state.md").write_text(
        "## Current Situation\n"
        "- **Location:** the Patio (M2)\n"
        "- **Party:** Torvin Bracewell — Fighter 1 | HP 12/12 | AC 18\n\n"
        "## Live State Flags\n"
        "- Door to M9 is ajar.\n"
    )
    return camp


def test_system_prompt_includes_roll_marker_spec_and_glossary():
    sp = local_prompt.build_local_system_prompt(Config(language="bg"), GLOSSARY)
    assert "[ROLL|" in sp
    assert "[ATTACK|" in sp
    assert "Скриване (Stealth)" in sp


def test_system_prompt_skips_glossary_block_for_english():
    sp = local_prompt.build_local_system_prompt(Config(language="en"), GLOSSARY)
    assert "Скриване" not in sp


def test_system_prompt_is_small_enough_for_a_tiny_context_budget():
    sp = local_prompt.build_local_system_prompt(Config(language="bg"), GLOSSARY)
    # Rough proxy (chars/4 ~= tokens) -- this must stay well under the 8k
    # num_ctx budget local_agent uses by default, leaving room for the
    # per-turn context and the model's own reply.
    assert len(sp) / 4 < 3000


def test_turn_prompt_includes_situation_party_and_actions(root):
    tp = local_prompt.build_local_turn_prompt("demo", "Sylwen влиза в стаята.")
    assert "Patio" in tp
    assert "Torvin Bracewell" in tp
    assert "Sylwen влиза в стаята." in tp


def test_turn_prompt_omits_empty_sections(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "bare"
    camp.mkdir(parents=True)
    (camp / "state.md").write_text("## Current Situation\n- nothing\n")
    tp = local_prompt.build_local_turn_prompt("bare", "действие")
    assert "Запомнени факти" not in tp
    assert "Текст на текущата сцена" not in tp
