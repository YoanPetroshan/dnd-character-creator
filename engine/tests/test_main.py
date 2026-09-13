import json
import subprocess

import pytest

from engine import main as engine_main
from engine.config import Config
from engine.log import read_events


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    (tmp_path / ".runtime").mkdir(parents=True)
    (tmp_path / "campaigns" / "demo").mkdir(parents=True)
    return tmp_path


def test_parser_defaults():
    args = engine_main.build_parser().parse_args([])
    assert args.campaign is None
    # None, not "bg": see test_saved_language_preference_survives_a_plain_run.
    assert args.lang is None
    assert args.max_turns is None


def test_parser_accepts_overrides():
    args = engine_main.build_parser().parse_args(
        ["--campaign", "demo", "--lang", "en", "--model", "claude-opus-5", "--max-turns", "2"]
    )
    assert args.campaign == "demo"
    assert args.lang == "en"
    assert args.model == "claude-opus-5"
    assert args.max_turns == 2


def test_resolve_campaign_prefers_explicit(root):
    assert engine_main.resolve_campaign(Config(campaign="fromcfg"), "explicit") == "explicit"


def test_resolve_campaign_falls_back_to_config(root):
    assert engine_main.resolve_campaign(Config(campaign="fromcfg"), None) == "fromcfg"


def test_resolve_campaign_uses_active_marker(root):
    (root / ".runtime" / ".campaign").write_text("demo\n")
    assert engine_main.resolve_campaign(Config(), None) == "demo"


def test_resolve_campaign_raises_when_unknown(root):
    with pytest.raises(SystemExit):
        engine_main.resolve_campaign(Config(), None)


def test_preflight_flags_missing_character_sheets(root, monkeypatch):
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    problems = engine_main.preflight(Config(), "demo")
    assert any("character sheet" in p.lower() for p in problems)


def test_preflight_flags_empty_rules_index(root, monkeypatch):
    (root / "campaigns" / "demo" / "characters").mkdir(parents=True)
    (root / "campaigns" / "demo" / "characters" / "falin.md").write_text("# Falin\n")
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [], "count": 0})
    problems = engine_main.preflight(Config(), "demo")
    assert any("rules index" in p.lower() for p in problems)


def test_preflight_clean_when_everything_present(root, monkeypatch):
    (root / "campaigns" / "demo" / "characters").mkdir(parents=True)
    (root / "campaigns" / "demo" / "characters" / "falin.md").write_text("# Falin\n")
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [1], "count": 1})
    # Stub the backend probe: otherwise this asserts on whether ollama
    # happens to be running on the machine, not on preflight's own logic.
    monkeypatch.setattr(engine_main, "ollama_reachable", lambda host: True)
    assert engine_main.preflight(Config(), "demo") == []


def test_preflight_flags_an_unreachable_local_backend(root, monkeypatch):
    (root / "campaigns" / "demo" / "characters").mkdir(parents=True)
    (root / "campaigns" / "demo" / "characters" / "falin.md").write_text("# Falin\n")
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [1], "count": 1})
    monkeypatch.setattr(engine_main, "ollama_reachable", lambda host: False)
    problems = engine_main.preflight(Config(), "demo")
    assert len(problems) == 1
    assert "Ollama isn't reachable" in problems[0]


def test_preflight_skips_the_backend_probe_for_the_claude_backend(root, monkeypatch):
    (root / "campaigns" / "demo" / "characters").mkdir(parents=True)
    (root / "campaigns" / "demo" / "characters" / "falin.md").write_text("# Falin\n")
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [1], "count": 1})

    def boom(host):
        raise AssertionError("the Claude backend must not probe ollama")

    monkeypatch.setattr(engine_main, "ollama_reachable", boom)
    assert engine_main.preflight(Config(backend="claude"), "demo") == []


def test_preflight_flags_missing_campaign_folder(root, monkeypatch):
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [1], "count": 1})
    # "nosuchcampaign" has no folder under campaigns/ — the "demo" folder
    # created by the root fixture is irrelevant here.
    problems = engine_main.preflight(Config(), "nosuchcampaign")
    assert any("campaign folder" in p.lower() for p in problems)


def test_preflight_flags_display_not_running(root, monkeypatch):
    (root / "campaigns" / "demo" / "characters").mkdir(parents=True)
    (root / "campaigns" / "demo" / "characters" / "falin.md").write_text("# Falin\n")
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: False)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "g.json")
    (root / "g.json").write_text("{}")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [1], "count": 1})
    problems = engine_main.preflight(Config(), "demo")
    assert any("display" in p.lower() for p in problems)


def test_saved_language_preference_survives_a_plain_run(root, monkeypatch, capsys):
    """`cfg.language = args.lang` was unconditional and argparse defaulted to
    "bg", so every run silently overrode a saved `language: "en"`."""
    (root / ".runtime" / "engine_config.json").write_text(
        json.dumps({"language": "en", "campaign": "demo"})
    )
    seen = {}

    def fake_preflight(cfg, campaign):
        seen["language"] = cfg.language
        return []

    monkeypatch.setattr(engine_main, "preflight", fake_preflight)
    engine_main.main(["--check"])
    assert seen["language"] == "en"


def test_explicit_lang_flag_still_wins(root, monkeypatch):
    (root / ".runtime" / "engine_config.json").write_text(
        json.dumps({"language": "en", "campaign": "demo"})
    )
    seen = {}

    def fake_preflight(cfg, campaign):
        seen["language"] = cfg.language
        return []

    monkeypatch.setattr(engine_main, "preflight", fake_preflight)
    engine_main.main(["--check", "--lang", "bg"])
    assert seen["language"] == "bg"


# --- ensure_ruleset -------------------------------------------------------


@pytest.fixture
def campaign_state(root):
    camp = root / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True, exist_ok=True)
    (camp / "state.md").write_text("# State\n\n## Session Flags\nroll_mode: players\n")
    return camp


def test_ensure_ruleset_pins_the_configured_ruleset(campaign_state, monkeypatch):
    monkeypatch.setattr(engine_main.subprocess, "run",
                        lambda *a, **kw: subprocess.CompletedProcess(a, 0, "", ""))
    engine_main.ensure_ruleset(Config(), "demo")
    assert engine_main.state.session_flags("demo")["ruleset"] == "2024"


def test_ensure_ruleset_survives_a_hung_migration(campaign_state, monkeypatch):
    """run_autosave wraps its subprocess call; this one did not, so a hung or
    unlaunchable migration killed the engine on boot with a traceback."""
    def boom(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="migrate_ruleset.py", timeout=60)

    monkeypatch.setattr(engine_main.subprocess, "run", boom)
    engine_main.ensure_ruleset(Config(), "demo")  # must not raise
    assert engine_main.state.session_flags("demo")["ruleset"] == "2024"
    events = [e["event"] for e in read_events(limit=50)]
    assert "ruleset_migration_failed" in events


def test_ensure_ruleset_survives_a_missing_interpreter(campaign_state, monkeypatch):
    monkeypatch.setattr(engine_main.subprocess, "run",
                        lambda *a, **kw: (_ for _ in ()).throw(OSError("no such file")))
    engine_main.ensure_ruleset(Config(), "demo")
    assert "ruleset_migration_failed" in [e["event"] for e in read_events(limit=50)]


def test_ensure_ruleset_logs_a_nonzero_exit_code(campaign_state, monkeypatch):
    """The discarded exit code: a migration that failed looked identical to
    one that succeeded."""
    monkeypatch.setattr(
        engine_main.subprocess, "run",
        lambda *a, **kw: subprocess.CompletedProcess(a, 3, "", "boom: bad campaign"),
    )
    engine_main.ensure_ruleset(Config(), "demo")
    failures = [e for e in read_events(limit=50)
                if e["event"] == "ruleset_migration_failed"]
    assert failures and failures[-1]["returncode"] == 3
    assert "boom" in failures[-1]["stderr"]


def test_preflight_flags_missing_glossary(root, monkeypatch):
    (root / "campaigns" / "demo" / "characters").mkdir(parents=True)
    (root / "campaigns" / "demo" / "characters" / "falin.md").write_text("# Falin\n")
    monkeypatch.setattr(engine_main.display, "is_running", lambda port=5001: True)
    monkeypatch.setattr(engine_main, "GLOSSARY_PATH", root / "no_such_glossary.json")
    monkeypatch.setattr(engine_main, "load_index", lambda: {"entries": [1], "count": 1})
    cfg = Config()
    assert cfg.language == "bg"
    problems = engine_main.preflight(cfg, "demo")
    assert any("glossary" in p.lower() for p in problems)
