#!/usr/bin/env python3
"""library.py — the cross-campaign character library.

Characters used to live in two places with neither being a real home: the
canonical YAML sat inside whichever campaign the character was rolled in
(`campaigns/<c>/characters/<slug>.yaml`), and a flat markdown copy was
mirrored to `~/.claude/dnd/characters/<slug>.md` as a roster listing. That
made "show me every character I have ever made" a directory scrape, and it
kept no history at all — levelling a character overwrote the only record of
what they used to be.

This module owns a proper library instead:

    ~/.claude/dnd/characters/
      Sylwen Nightbrook/
        current.yaml            ← the character as they are now
        meta.json               ← origin, campaigns played, timestamps
        levels/
          level-01.yaml         ← a frozen snapshot, written on level-up
          level-02.yaml

The per-level snapshots are the point of the folder: they are immutable
records, never rewritten, so a character can be inspected — or recruited
into a new campaign — at the level they were at any point in their history.

The directory name is the character's real name, not a slug, because this
is a shelf a person browses. Slugs are still used for file *contents*
interop with the existing char_state tooling.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import paths  # noqa: E402

MAX_LEVEL = 20
# Anything that would escape the library directory or confuse the filesystem.
_UNSAFE = re.compile(r"[/\\:*?\"<>|\x00-\x1f]")


def library_dir() -> Path:
    d = paths.characters_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_dir_name(name: str) -> str:
    """A character name reduced to something safe to use as a folder.

    Deliberately preserves spaces, case and non-ASCII letters — the folder
    is meant to be readable in Finder — and only strips what a filesystem
    genuinely cannot take. A name that reduces to nothing is rejected rather
    than silently becoming an empty or hidden directory.
    """
    cleaned = _UNSAFE.sub("", unicodedata.normalize("NFC", str(name))).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise ValueError(f"character name {name!r} has no usable characters")
    return cleaned[:80]


def slug(name: str) -> str:
    """The lowercase-hyphen form the char_state tooling uses for filenames."""
    s = unicodedata.normalize("NFKD", str(name))
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_]+", "-", s) or "character"


def char_dir(name: str) -> Path:
    return library_dir() / safe_dir_name(name)


def level_path(name: str, level: int) -> Path:
    return char_dir(name) / "levels" / f"level-{int(level):02d}.yaml"


def current_path(name: str) -> Path:
    return char_dir(name) / "current.yaml"


def meta_path(name: str) -> Path:
    return char_dir(name) / "meta.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write(path: Path, text: str) -> None:
    """Write via a sibling temp file + rename, so a crash mid-write can never
    leave a half-written character behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False,
                          default_flow_style=False)


def total_level(data: dict) -> int:
    """A character's level, summed across classes for multiclass sheets."""
    classes = data.get("classes") or []
    total = sum(int(c.get("level", 0) or 0) for c in classes if isinstance(c, dict))
    return total or int(data.get("level", 1) or 1)


# ── meta ────────────────────────────────────────────────────────────────

def load_meta(name: str) -> dict:
    try:
        return json.loads(meta_path(name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_meta(name: str, updates: dict | None = None) -> dict:
    """Merge `updates` into the character's meta.json.

    Takes a dict rather than **kwargs: the meta legitimately carries a
    "name" key, which would collide with the positional parameter.
    """
    meta = load_meta(name)
    meta.update(updates or {})
    meta.setdefault("created", _now())
    meta["updated"] = _now()
    _atomic_write(meta_path(name), json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


# ── read / write ────────────────────────────────────────────────────────

def load(name: str, level: int | None = None) -> dict:
    """The character's current sheet, or a frozen snapshot at `level`."""
    path = current_path(name) if level is None else level_path(name, level)
    if not path.exists():
        what = "current sheet" if level is None else f"level {level}"
        raise FileNotFoundError(f"{name}: no {what} in the library")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save(name: str, data: dict, *, archive: bool = True,
         origin_campaign: str | None = None) -> dict:
    """Write the current sheet, and snapshot it at its level.

    `archive` writes `levels/level-NN.yaml` for the sheet's current level if
    that snapshot does not already exist. Existing snapshots are never
    overwritten: the archive is a history, and a level the character has
    already passed through is a fact, not a draft. Re-archiving a level
    on purpose means deleting that file first.
    """
    name = str(data.get("name") or name).strip()
    if not name:
        raise ValueError("a character needs a name")
    _atomic_write(current_path(name), _dump_yaml(data))

    lvl = total_level(data)
    archived = False
    if archive and 1 <= lvl <= MAX_LEVEL:
        lp = level_path(name, lvl)
        if not lp.exists():
            _atomic_write(lp, _dump_yaml(data))
            archived = True

    meta = load_meta(name)
    updates: dict = {"name": name, "level": lvl}
    if origin_campaign and not meta.get("origin_campaign"):
        updates["origin_campaign"] = origin_campaign
    if origin_campaign:
        seen = list(meta.get("campaigns") or [])
        if origin_campaign not in seen:
            seen.append(origin_campaign)
        updates["campaigns"] = seen
    save_meta(name, updates)
    return {"name": name, "level": lvl, "archived_level": lvl if archived else None}


def archived_levels(name: str) -> list:
    d = char_dir(name) / "levels"
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("level-*.yaml")):
        m = re.match(r"level-(\d+)\.yaml$", f.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def exists(name: str) -> bool:
    try:
        return current_path(name).exists()
    except ValueError:
        return False


def summary(name: str) -> dict:
    """One row for the library listing — cheap enough to call for every
    character on the shelf."""
    try:
        data = load(name)
    except (FileNotFoundError, yaml.YAMLError):
        data = {}
    meta = load_meta(name)
    classes = data.get("classes") or []
    cls_str = " / ".join(
        f"{c.get('cls','?')} {c.get('level','?')}" for c in classes if isinstance(c, dict)
    )
    combat = data.get("combat") or {}
    return {
        "name": data.get("name") or name,
        "dir": safe_dir_name(name),
        "race": data.get("race", ""),
        "background": data.get("background", ""),
        "classes": cls_str,
        "level": total_level(data) if data else meta.get("level", 0),
        "hp_current": combat.get("hp_current"),
        "hp_max": combat.get("hp_max"),
        "origin_campaign": meta.get("origin_campaign", ""),
        "campaigns": meta.get("campaigns", []),
        "levels": archived_levels(name),
        "updated": meta.get("updated", ""),
        "playable": bool(data),
    }


def list_characters() -> list:
    """Every character on the shelf, newest-updated first."""
    out = []
    for d in library_dir().iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        if not (d / "current.yaml").exists():
            continue
        out.append(summary(d.name))
    out.sort(key=lambda s: (s.get("updated") or "", s["name"]), reverse=True)
    return out


def delete(name: str) -> bool:
    """Remove a character and their whole history. Irreversible."""
    d = char_dir(name)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


# ── campaign interop ────────────────────────────────────────────────────

def import_from_campaign(campaign: str, slug_or_name: str) -> dict:
    """Copy a character out of a campaign and onto the shelf.

    Reads the campaign's canonical YAML when there is one. A pre-migration
    campaign that only has the markdown sheet is not silently half-imported —
    it raises, so the caller can say what is actually wrong.
    """
    camp_dir = paths.find_campaign(campaign)
    chars = camp_dir / "characters"
    candidates = [chars / f"{slug_or_name}.yaml", chars / f"{slug(slug_or_name)}.yaml"]
    src = next((p for p in candidates if p.exists()), None)
    if src is None:
        md = next((p for p in (chars / f"{slug(slug_or_name)}.md",
                               chars / f"{slug_or_name}.md") if p.exists()), None)
        if md is not None:
            raise FileNotFoundError(
                f"{slug_or_name} in {campaign} is a pre-migration markdown-only "
                f"sheet ({md.name}); convert it with migrate_character_to_yaml.py first"
            )
        raise FileNotFoundError(f"no character {slug_or_name!r} in campaign {campaign!r}")

    data = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    if not data.get("name"):
        raise ValueError(f"{src} has no name field")
    return save(data["name"], data, origin_campaign=campaign)


def _render_markdown(data: dict) -> str:
    """The human-readable sheet, via the existing renderer when it loads.

    Falls back to a minimal sheet rather than failing the recruit: the two
    things the engine actually parses out of this file are the `# Name`
    heading (party_names) and the `**HP:** x / y` line (read_hp), and both
    are here either way.
    """
    try:
        import char_state_schema as _schema
        import char_state_sync as _sync
        tmp = char_dir(data.get("name", "")) / ".render.yaml"
        _atomic_write(tmp, _dump_yaml(data))
        try:
            character = _schema.load_character.__wrapped__(data) \
                if hasattr(_schema.load_character, "__wrapped__") else None
        finally:
            tmp.unlink(missing_ok=True)
        if character is not None:
            return _sync.render_markdown(character)
    except Exception:  # noqa: BLE001 — the fallback below is always valid
        pass

    combat = data.get("combat") or {}
    classes = " / ".join(
        f"{c.get('cls','')} {c.get('level','')}".strip()
        for c in (data.get("classes") or []) if isinstance(c, dict))
    return (
        f"# {data.get('name','')}\n"
        f"**Player:** {data.get('player','')}  **Campaign:** —\n\n"
        "## Identity\n"
        f"- **Race:** {data.get('race','')} | **Class:** {classes} | "
        f"**Background:** {data.get('background','')}\n"
        f"- **Alignment:** {data.get('alignment','')}\n\n"
        "## Combat Stats\n"
        f"- **HP:** {combat.get('hp_current', 1)} / {combat.get('hp_max', 1)}"
        f" | **Speed:** {combat.get('speed', 30)}\n\n"
        "*Generated when this character was recruited from the library. "
        "The .yaml beside it is the canonical sheet.*\n"
    )


def copy_to_campaign(name: str, campaign: str, level: int | None = None) -> Path:
    """Place a library character into a campaign so they can be played.

    `level` recruits the archived snapshot from that level instead of the
    character's current state — the reason the per-level archive exists.

    Writes BOTH the canonical `.yaml` and a rendered `.md`. The markdown is
    not decoration: engine.state.party_names() finds the party by globbing
    `characters/*.md`, so a yaml-only recruit is invisible to the game and
    the campaign fails preflight with "no character sheet" despite the
    character sitting right there.
    """
    data = load(name, level=level)
    camp_dir = paths.find_campaign(campaign)
    dest_dir = camp_dir / "characters"
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = slug(data.get("name") or name)
    dest = dest_dir / f"{stem}.yaml"
    _atomic_write(dest, _dump_yaml(data))
    _atomic_write(dest_dir / f"{stem}.md", _render_markdown(data))
    meta = load_meta(name)
    seen = list(meta.get("campaigns") or [])
    if campaign not in seen:
        seen.append(campaign)
    save_meta(name, {"campaigns": seen})
    return dest
