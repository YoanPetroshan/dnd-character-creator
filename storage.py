"""Character persistence — YAML sheet + Markdown + PDF, one directory per
character, at the same path convention dnd-app-bg-local's play app already
uses (skills/dnd/scripts/paths.py::characters_dir()) — so a character this
app saves is already visible to that app's library.py with zero migration,
without this module importing anything from that repo.

Imports nothing outside the standard library + PyYAML.
"""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import yaml

_UNSAFE = re.compile(r"[/\\:*?\"<>|\x00-\x1f]")


def root_dir() -> Path:
    raw = os.environ.get("DND_CAMPAIGN_ROOT", "")
    if raw.strip():
        return Path(raw.strip()).expanduser().resolve()
    return Path("~/.claude/dnd").expanduser()


def characters_dir() -> Path:
    d = root_dir() / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_dir_name(name: str) -> str:
    """A character name reduced to something safe to use as a folder.

    Preserves spaces, case, and non-ASCII letters — the folder is meant to
    be readable in a file browser — and only strips what a filesystem
    cannot take. A name that reduces to nothing is rejected.
    """
    cleaned = _UNSAFE.sub("", unicodedata.normalize("NFC", str(name))).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise ValueError(f"character name {name!r} has no usable characters")
    return cleaned[:80]


def char_dir(name: str) -> Path:
    d = characters_dir() / safe_dir_name(name)
    d.mkdir(parents=True, exist_ok=True)
    return d


def character_exists(name: str) -> bool:
    """True if a character named `name` already has a saved sheet.

    Non-creating: unlike char_dir(), this never mkdir's anything, so a
    plain existence check can't leave empty folders behind in the shared
    library (see storage.characters_dir()'s docstring / Minor 2).
    """
    return (characters_dir() / safe_dir_name(name) / "current.yaml").exists()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def save_yaml(name: str, sheet: dict) -> Path:
    path = char_dir(name) / "current.yaml"
    text = yaml.safe_dump(sheet, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)
    _atomic_write_text(path, text)
    return path


def save_markdown(name: str, text: str) -> Path:
    path = char_dir(name) / "character.md"
    _atomic_write_text(path, text)
    return path


def save_pdf(name: str, data: bytes) -> Path:
    path = char_dir(name) / "character.pdf"
    _atomic_write_bytes(path, data)
    return path


def list_characters() -> list[dict]:
    out = []
    root = characters_dir()
    if not root.exists():
        return out
    for entry in sorted(root.iterdir()):
        current = entry / "current.yaml"
        if not current.is_file():
            continue
        try:
            sheet = yaml.safe_load(current.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        classes = sheet.get("classes") or []
        level = sum(int(c.get("level", 0) or 0) for c in classes if isinstance(c, dict))
        out.append({
            "name": sheet.get("name", entry.name),
            "race": sheet.get("race", ""),
            "classes": classes,
            "level": level,
        })
    return out
