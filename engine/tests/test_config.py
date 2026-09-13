import json

import pytest

from engine.config import Config, load_config, save_config


def test_defaults_are_bulgarian_sonnet_2024():
    cfg = Config()
    assert cfg.language == "bg"
    assert cfg.ruleset == "2024"
    assert cfg.turn_model == "claude-sonnet-5"
    assert cfg.heavy_model == "claude-opus-5"
    assert cfg.turn_timeout_s == 180
    assert cfg.autosave_every == 5


def test_content_paths_point_at_the_users_corpus():
    from engine.config import json_dir, rules_index_path
    assert json_dir().name == "JSON"
    assert "DND content" in str(json_dir())
    assert rules_index_path().name == "index.json"


def test_load_missing_file_returns_defaults(tmp_path):
    cfg = load_config(tmp_path / "nope.json")
    assert cfg.language == "bg"


def test_roundtrip(tmp_path):
    path = tmp_path / "engine_config.json"
    save_config(Config(language="en", turn_timeout_s=99), path)
    assert json.loads(path.read_text())["turn_timeout_s"] == 99
    assert load_config(path).turn_timeout_s == 99


def test_unknown_keys_in_file_are_ignored(tmp_path):
    path = tmp_path / "engine_config.json"
    path.write_text(json.dumps({"language": "bg", "obsolete_key": 1}))
    cfg = load_config(path)
    assert cfg.language == "bg"


def test_unsupported_ruleset_is_rejected():
    """cfg.ruleset feeds the prompt header while engine.main pins the same
    value into state.md; allowing anything but 2024 would let the two
    disagree, with nothing in the system preventing it."""
    with pytest.raises(ValueError):
        Config(ruleset="2014")


def test_unsupported_ruleset_in_file_falls_back_without_losing_other_settings(tmp_path, capsys):
    path = tmp_path / "engine_config.json"
    path.write_text(json.dumps({"ruleset": "2014", "turn_timeout_s": 99, "language": "en"}))
    cfg = load_config(path)
    assert cfg.ruleset == "2024"
    assert cfg.turn_timeout_s == 99, "one bad value must not discard the rest"
    assert cfg.language == "en"
    assert "unsupported ruleset" in capsys.readouterr().err
