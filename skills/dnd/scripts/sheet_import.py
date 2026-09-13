#!/usr/bin/env python3
"""sheet_import.py — read a filled-in character sheet into library YAML.

Three input shapes, in descending order of how much they can be trusted:

* **YAML** — a sheet this program wrote. Loaded as-is.
* **Markdown** — the downloadable template with its blanks filled in. Parsed
  by heading and label; anything unreadable is reported rather than guessed.
* **PDF** — only the *form fields* of a fillable sheet. A scanned or flattened
  PDF carries no field data at all, and OCR of a hand-written sheet would
  invent numbers a character then gets played with, so it is refused with a
  clear reason instead of attempted.

Every path returns `(sheet, warnings)`. Warnings are the honest part: a sheet
that parsed with gaps still imports, and the caller shows what was missing so
it can be fixed by hand rather than silently played with wrong values.
"""
from __future__ import annotations

import io
import re
from typing import Any

import yaml

ABILITIES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_FIELD = re.compile(r"\*\*(?P<key>[^:*]+):\*\*\s*(?P<val>[^|\n]*)")
_INT = re.compile(r"-?\d+")


def _first_int(text: str, default: int | None = None) -> int | None:
    m = _INT.search(text or "")
    return int(m.group()) if m else default


def _placeholder(value: str) -> bool:
    """True for a template blank that was never filled in.

    The template ships with `<Name>`, `XX (+X)` and bare `/` markers; taking
    those literally would create a character called "<Name>" with 0 HP.
    """
    v = (value or "").strip()
    return (not v or v in {"-", "—", "/"} or v.startswith("<")
            or bool(re.fullmatch(r"[Xx/+()\s—-]*", v)))


def _clean(value: str) -> str:
    v = (value or "").strip().strip("*").strip()
    return "" if _placeholder(v) else v


def blank_sheet(name: str = "") -> dict:
    """The minimum a sheet needs to load and be played."""
    return {
        "name": name, "race": "", "background": "", "alignment": "", "player": "",
        "classes": [], "ability_scores": {a: 10 for a in ABILITIES},
        "combat": {"hp_current": 1, "hp_max": 1, "hp_temp": 0, "speed": 30,
                   "death_saves": {"successes": 0, "failures": 0}, "hit_dice": []},
        "proficiencies": {"saving_throws": [], "skills": [], "armor": [],
                          "weapons": [], "tools": [], "languages": []},
        "conditions": {"inspiration": False, "exhaustion": 0, "active": [],
                       "attunement": [], "weapon_mastery": []},
        "personality": {"traits": "", "ideals": "", "bonds": "", "flaws": ""},
        "features_traits": [], "backstory": "",
        "currency": {"cp": 0, "sp": 0, "ep": 0, "gp": 0, "pp": 0},
        "equipment": [], "misc_items": [], "spellcasting": [], "spells": [],
        "spell_slots": {}, "pact_magic_slots": None,
    }


# ── markdown ────────────────────────────────────────────────────────────

def from_markdown(text: str) -> tuple[dict, list]:
    warnings: list = []
    sheet = blank_sheet()

    m = _H1.search(text or "")
    name = _clean(m.group(1)) if m else ""
    if not name:
        raise ValueError("no character name — the first line must be '# Name'")
    sheet["name"] = name

    fields: dict = {}
    for fm in _FIELD.finditer(text or ""):
        key = fm.group("key").strip().lower()
        fields.setdefault(key, _clean(fm.group("val")))

    sheet["race"] = fields.get("race", "")
    sheet["background"] = fields.get("background", "")
    sheet["alignment"] = fields.get("alignment", "")
    sheet["player"] = fields.get("player", "")

    cls = fields.get("class", "")
    level = _first_int(fields.get("level", ""), None)
    if cls:
        sheet["classes"] = [{"cls": cls, "subclass": "", "level": level or 1}]
        if level is None:
            warnings.append("no level found — assumed 1")
    else:
        warnings.append("no class found")

    # Ability scores: the template's table row is "| 15 (+2) | 14 (+2) | …".
    scores, found = {}, False
    tbl = re.search(
        r"\|\s*STR\s*\|\s*DEX\s*\|\s*CON\s*\|\s*INT\s*\|\s*WIS\s*\|\s*CHA\s*\|"
        r"\s*\n\|[-\s|]+\|\s*\n\|(?P<row>[^\n]+)\|",
        text or "", re.I)
    if tbl:
        cells = [c.strip() for c in tbl.group("row").split("|") if c.strip()]
        if len(cells) >= 6:
            for ability, cell in zip(ABILITIES, cells[:6]):
                val = _first_int(cell)
                if val is not None:
                    scores[ability] = val
                    found = True
    if found:
        sheet["ability_scores"] = {a: scores.get(a, 10) for a in ABILITIES}
        missing = [a for a in ABILITIES if a not in scores]
        if missing:
            warnings.append(f"ability scores defaulted to 10: {', '.join(missing)}")
    else:
        warnings.append("no ability scores found — all left at 10")

    hp_raw = fields.get("hp", "")
    hp_nums = _INT.findall(hp_raw)
    if len(hp_nums) >= 2:
        sheet["combat"]["hp_current"] = int(hp_nums[0])
        sheet["combat"]["hp_max"] = int(hp_nums[1])
    elif len(hp_nums) == 1:
        sheet["combat"]["hp_current"] = sheet["combat"]["hp_max"] = int(hp_nums[0])
        warnings.append("only one HP number found — used for both current and max")
    else:
        warnings.append("no HP found — set to 1/1, fix before playing")

    speed = _first_int(fields.get("speed", ""))
    if speed:
        sheet["combat"]["speed"] = speed
    return sheet, warnings


# ── pdf ─────────────────────────────────────────────────────────────────

# Field names vary between sheet editions; these are the ones the common
# fillable PHB sheets use. Matched case-insensitively against whatever the
# PDF actually carries.
_PDF_MAP = {
    "charactername": "name", "playername": "player", "race ": "race",
    "background": "background", "alignment": "alignment",
    "classlevel": "_classlevel", "speed": "_speed",
    "hpcurrent": "_hp_current", "hpmax": "_hp_max",
    "str": "STR", "dex": "DEX", "con": "CON",
    "int": "INT", "wis": "WIS", "cha": "CHA",
}


def from_pdf(data: bytes) -> tuple[dict, list]:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "reading PDF sheets needs pypdf — install it with "
                "`pip install pypdf`, or upload the .md template instead"
            ) from exc

    reader = PdfReader(io.BytesIO(data))
    raw: dict = {}
    try:
        raw = reader.get_fields() or {}
    except Exception:  # noqa: BLE001 — a malformed AcroForm is just "no fields"
        raw = {}
    if not raw:
        raise ValueError(
            "this PDF has no fillable form fields — it is probably scanned or "
            "flattened. Reading numbers off an image would mean guessing them, "
            "so fill in the .md template instead."
        )

    values: dict = {}
    for key, spec in raw.items():
        val = ""
        if isinstance(spec, dict):
            val = spec.get("/V", "") or ""
        values[str(key).strip().lower()] = str(val).strip()

    sheet, warnings = blank_sheet(), []
    picked: dict = {}
    for pdf_key, target in _PDF_MAP.items():
        for actual, val in values.items():
            if actual == pdf_key.strip() or actual.replace(" ", "") == pdf_key.strip():
                if val:
                    picked[target] = val
                break

    sheet["name"] = picked.get("name", "").strip()
    if not sheet["name"]:
        raise ValueError("the PDF has form fields but no character name in them")
    for key in ("player", "race", "background", "alignment"):
        sheet[key] = picked.get(key, "")

    cl = picked.get("_classlevel", "")
    if cl:
        lvl = _first_int(cl, 1)
        cls = re.sub(r"\d+", "", cl).strip(" -–—")
        sheet["classes"] = [{"cls": cls or "Unknown", "subclass": "", "level": lvl or 1}]
    else:
        warnings.append("no class/level field found")

    scores = {}
    for ability in ABILITIES:
        v = _first_int(picked.get(ability, ""))
        if v is not None:
            scores[ability] = v
    sheet["ability_scores"] = {a: scores.get(a, 10) for a in ABILITIES}
    if len(scores) < 6:
        warnings.append(
            f"ability scores defaulted to 10: "
            f"{', '.join(a for a in ABILITIES if a not in scores)}")

    hp_max = _first_int(picked.get("_hp_max", ""))
    hp_cur = _first_int(picked.get("_hp_current", ""), hp_max)
    if hp_max:
        sheet["combat"]["hp_max"] = hp_max
        sheet["combat"]["hp_current"] = hp_cur or hp_max
    else:
        warnings.append("no HP found — set to 1/1, fix before playing")
    speed = _first_int(picked.get("_speed", ""))
    if speed:
        sheet["combat"]["speed"] = speed
    return sheet, warnings


# ── yaml ────────────────────────────────────────────────────────────────

def from_yaml(text: str) -> tuple[dict, list]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("that YAML file is not a character sheet")
    if not (data.get("name") or "").strip():
        raise ValueError("the sheet has no name")
    merged = blank_sheet()
    merged.update(data)
    warnings = []
    if not merged.get("classes"):
        warnings.append("no classes listed")
    return merged, warnings


def parse(filename: str, data: bytes) -> tuple[dict, list]:
    """Dispatch on extension. Raises with a readable reason on anything else."""
    lower = (filename or "").lower()
    if lower.endswith((".yaml", ".yml")):
        return from_yaml(data.decode("utf-8", errors="replace"))
    if lower.endswith((".md", ".markdown", ".txt")):
        return from_markdown(data.decode("utf-8", errors="replace"))
    if lower.endswith(".pdf"):
        return from_pdf(data)
    raise ValueError(f"don't know how to read {filename!r} — use .md, .yaml or .pdf")
