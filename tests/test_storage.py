import os
import yaml
import pytest

import storage


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    yield tmp_path


def test_root_dir_respects_env(isolated_root):
    assert storage.root_dir() == isolated_root


def test_root_dir_default(monkeypatch):
    monkeypatch.delenv("DND_CAMPAIGN_ROOT", raising=False)
    assert storage.root_dir() == (__import__("pathlib").Path("~/.claude/dnd").expanduser())


def test_safe_dir_name_strips_unsafe_chars():
    assert storage.safe_dir_name("Sy/lwen Night?brook") == "Sylwen Nightbrook"


def test_safe_dir_name_rejects_empty():
    with pytest.raises(ValueError):
        storage.safe_dir_name("///")


def test_save_yaml_round_trips(isolated_root):
    sheet = {"name": "Torvin Bracewell", "race": "Human",
             "classes": [{"cls": "Fighter", "subclass": "", "level": 1}]}
    path = storage.save_yaml("Torvin Bracewell", sheet)
    assert path.exists()
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert loaded == sheet
    assert path.parent == storage.char_dir("Torvin Bracewell")
    assert path.name == "current.yaml"


def test_save_markdown_and_pdf(isolated_root):
    md_path = storage.save_markdown("Torvin Bracewell", "# Torvin Bracewell\n")
    pdf_path = storage.save_pdf("Torvin Bracewell", b"%PDF-fake-bytes")
    assert md_path.read_text(encoding="utf-8") == "# Torvin Bracewell\n"
    assert pdf_path.read_bytes() == b"%PDF-fake-bytes"
    assert md_path.name == "character.md"
    assert pdf_path.name == "character.pdf"


def test_list_characters(isolated_root):
    storage.save_yaml("Sylwen Nightbrook", {
        "name": "Sylwen Nightbrook", "race": "Wood Elf",
        "classes": [{"cls": "Cleric", "subclass": "Life", "level": 1}]})
    storage.save_yaml("Torvin Bracewell", {
        "name": "Torvin Bracewell", "race": "Human",
        "classes": [{"cls": "Fighter", "subclass": "", "level": 1}]})
    out = storage.list_characters()
    names = sorted(c["name"] for c in out)
    assert names == ["Sylwen Nightbrook", "Torvin Bracewell"]
    sylwen = next(c for c in out if c["name"] == "Sylwen Nightbrook")
    assert sylwen["race"] == "Wood Elf"
    assert sylwen["classes"] == [{"cls": "Cleric", "subclass": "Life", "level": 1}]
