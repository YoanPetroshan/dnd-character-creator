import json
from pathlib import Path

from engine import lang

FIXTURE = Path(__file__).parent / "fixtures" / "protocol_sample.md"


def test_parses_term_pairs():
    data = lang.parse_protocol(FIXTURE.read_text())
    pairs = {t["en"]: t["bg"] for t in data["terms"]}
    assert pairs["Ability Check"] == "Проверка на умение (Ability Check)"
    assert pairs["Blinded"] == "Сляп (Blinded)"


def test_skips_table_separator_rows():
    data = lang.parse_protocol(FIXTURE.read_text())
    assert all(not t["en"].startswith("-") for t in data["terms"])
    assert all(t["en"] != "Английски" for t in data["terms"])


def test_identity_terms_land_in_keep_english():
    data = lang.parse_protocol(FIXTURE.read_text())
    assert "Advantage" in data["keep_english"]


def test_never_translate_captures_proper_nouns():
    data = lang.parse_protocol(FIXTURE.read_text())
    assert "Waterdeep" in data["never_translate"]
    assert "Gundren Rockseeker" in data["never_translate"]


def test_build_glossary_writes_json(tmp_path):
    out = tmp_path / "bg_glossary.json"
    data = lang.build_glossary(FIXTURE, out)
    assert out.exists()
    assert json.loads(out.read_text())["terms"] == data["terms"]


def test_protocol_path_defaults_into_the_content_root(monkeypatch, tmp_path):
    monkeypatch.delenv("DND_PROTOCOL_PATH", raising=False)
    monkeypatch.setenv("DND_CONTENT_ROOT", str(tmp_path))
    assert lang.protocol_path() == tmp_path / lang.PROTOCOL_FILENAME


def test_protocol_path_honours_the_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_PROTOCOL_PATH", str(tmp_path / "custom.md"))
    assert lang.protocol_path() == tmp_path / "custom.md"


def test_build_glossary_falls_back_to_a_prebuilt_glossary(monkeypatch, tmp_path, capsys):
    """engine.main.serve() calls build_glossary unconditionally for Bulgarian,
    and preflight only checks the OUTPUT json — so an unreachable source used
    to kill the engine on boot with an unhandled FileNotFoundError.
    """
    monkeypatch.setenv("DND_CONTENT_ROOT", str(tmp_path / "nowhere"))
    monkeypatch.delenv("DND_PROTOCOL_PATH", raising=False)
    out = tmp_path / "bg_glossary.json"
    prebuilt = {"terms": [{"en": "Stealth", "bg": "Скриване"}],
                "keep_english": ["HP"], "never_translate": ["Waterdeep"]}
    out.write_text(json.dumps(prebuilt, ensure_ascii=False), encoding="utf-8")

    data = lang.build_glossary(out_path=out)
    assert data == prebuilt
    assert "using prebuilt glossary" in capsys.readouterr().err
    # A fallback must never overwrite the good glossary it just read.
    assert json.loads(out.read_text()) == prebuilt


def test_build_glossary_falls_back_to_the_packaged_glossary(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_PROTOCOL_PATH", str(tmp_path / "missing.md"))
    data = lang.build_glossary(out_path=tmp_path / "not_written.json")
    assert data["terms"], "the repo's committed glossary should have carried this"
    assert not (tmp_path / "not_written.json").exists()


def test_build_glossary_survives_with_no_glossary_at_all(monkeypatch, tmp_path):
    monkeypatch.setenv("DND_PROTOCOL_PATH", str(tmp_path / "missing.md"))
    monkeypatch.setattr(lang, "PACKAGED_GLOSSARY_PATH", tmp_path / "also_missing.json")
    data = lang.build_glossary(out_path=tmp_path / "nope.json")
    assert data["terms"] == []
    assert "HP" in data["keep_english"]


def test_prompt_block_contains_rules_and_terms():
    data = lang.parse_protocol(FIXTURE.read_text())
    block = lang.glossary_prompt_block(data)
    assert "Ability Check" in block
    assert "Advantage" in block
    assert "Waterdeep" in block


def test_prompt_block_respects_max_terms():
    data = {"terms": [{"en": f"T{i}", "bg": f"Б{i}"} for i in range(500)],
            "keep_english": [], "never_translate": []}
    block = lang.glossary_prompt_block(data, max_terms=10)
    assert "T9" in block
    assert "T10" not in block


def test_row_with_escaped_pipe_in_cell_still_parses():
    md = "| Attack \\| Defense | Атака \\| Защита |\n"
    data = lang.parse_protocol(md)
    assert len(data["terms"]) == 1
    term = data["terms"][0]
    assert term["en"] == "Attack | Defense"
    assert term["bg"] == "Атака | Защита"


def test_row_with_bold_markup_strips_asterisks():
    md = "| **Ability Check** | **Проверка на умение** |\n"
    data = lang.parse_protocol(md)
    assert len(data["terms"]) == 1
    term = data["terms"][0]
    assert term["en"] == "Ability Check"
    assert term["bg"] == "Проверка на умение"
    assert "*" not in term["en"]
    assert "*" not in term["bg"]


def test_never_translate_bullet_with_plain_hyphen_separator():
    md = (
        "## ИМЕНА, РАСИ И ЛОКАЦИИ — НЕ СЕ ПРЕВЕЖДАТ\n\n"
        "- **Имена на локации** - Neverwinter, Baldur's Gate\n"
    )
    data = lang.parse_protocol(md)
    assert "Neverwinter" in data["never_translate"]
    assert "Baldur's Gate" in data["never_translate"]


def test_never_translate_bullet_hyphen_separator_ignores_mid_word_hyphen():
    # The label itself contains a mid-word hyphen ("NPC-та"); the plain-hyphen
    # separator fix must not mistake that for the label/items boundary.
    md = (
        "## ИМЕНА, РАСИ И ЛОКАЦИИ — НЕ СЕ ПРЕВЕЖДАТ\n\n"
        "- **Имена на герои и NPC-та** - Gundren Rockseeker, Sildar Hallwinter\n"
    )
    data = lang.parse_protocol(md)
    assert "Gundren Rockseeker" in data["never_translate"]
    assert "Sildar Hallwinter" in data["never_translate"]
    assert "NPC-та" not in data["never_translate"]
    assert "та" not in data["never_translate"]


def test_never_translate_bullet_with_semicolon_separator():
    md = (
        "## ИМЕНА, РАСИ И ЛОКАЦИИ — НЕ СЕ ПРЕВЕЖДАТ\n\n"
        "- **Имена на герои** — Gundren Rockseeker; Sildar Hallwinter\n"
    )
    data = lang.parse_protocol(md)
    assert "Gundren Rockseeker" in data["never_translate"]
    assert "Sildar Hallwinter" in data["never_translate"]
