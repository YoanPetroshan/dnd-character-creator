"""Bulgarian Translation Protocol → machine-readable glossary + prompt block."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from engine.config import content_root_path

PROTOCOL_FILENAME = "Bulgarian_Translation_Protocol.md"
# The glossary this repo ships with. Used as the source of truth whenever the
# protocol markdown itself is unreachable, so a moved or missing source file
# degrades to "use the committed glossary" instead of killing the engine on
# boot with an unhandled FileNotFoundError.
PACKAGED_GLOSSARY_PATH = Path(__file__).resolve().parent / "lang" / "bg_glossary.json"


def protocol_path() -> Path:
    """Where the Bulgarian Translation Protocol markdown lives.

    Override with DND_PROTOCOL_PATH; otherwise it sits in the rules corpus
    alongside the books (itself overridable via DND_CONTENT_ROOT), the same
    env-var pattern as campaign_root()/content_root_path(). It used to be a
    hardcoded absolute path into a directory outside this repo entirely.
    """
    override = os.environ.get("DND_PROTOCOL_PATH")
    if override:
        return Path(override)
    return content_root_path() / PROTOCOL_FILENAME

# Terms the protocol explicitly keeps in English because they have no settled
# Bulgarian equivalent in the D&D community.
KEEP_ENGLISH = [
    "Advantage", "Disadvantage", "Bonus Action", "Spell Slot", "Concentration",
    "Hit Points", "HP", "Hit Dice", "AC", "XP", "DC", "DM", "NPC",
    "Attack Bonus", "Health", "Armor Class",
]

_ROW = re.compile(r"^\|\s*(?P<en>[^|]+?)\s*\|\s*(?P<bg>[^|]+?)\s*\|\s*$")
_SEP = re.compile(r"^[\s\-:]+$")
# Separator between a bullet's bold label and its item list. Must be a dash
# variant (em dash —, en dash –, or plain hyphen -) with whitespace on both
# sides, so it never matches a mid-word hyphen like "NPC-та" (no surrounding
# spaces there).
_BULLET_TAIL = re.compile(r"(?:^|\s)[—–-]\s+(?P<items>.+?)(?:\s*и т\.н\.)?\s*$")
_ITEM_SEP = re.compile(r"[,;]")
# Placeholder for an escaped pipe (`\|`) inside a table cell, so it survives
# the `|`-delimited row split instead of being mistaken for a column border.
_ESCAPED_PIPE = "\\|"
_PIPE_PLACEHOLDER = "\x00PIPE\x00"


def _strip_md(s: str) -> str:
    """Strip surrounding markdown emphasis markers (**, *, _) and whitespace."""
    return s.strip().strip("*_").strip()


def parse_protocol(md: str) -> dict:
    terms: list[dict[str, str]] = []
    keep_english: list[str] = list(KEEP_ENGLISH)
    never: list[str] = []
    in_never_section = False

    for raw in md.splitlines():
        line = raw.rstrip()

        if line.startswith("## "):
            in_never_section = "НЕ СЕ ПРЕВЕЖДАТ" in line
            continue

        if in_never_section and line.lstrip().startswith("- "):
            # Strip the leading "- " bullet marker itself before searching for
            # the label/items separator, so a leading-whitespace bullet dash
            # (e.g. indented "  - ...") can never be mistaken for the em-dash
            # separator later in the line.
            content = line.lstrip()[2:]
            m = _BULLET_TAIL.search(content)
            if m:
                for item in _ITEM_SEP.split(m.group("items")):
                    item = _strip_md(item)
                    if item and item.lower() not in {"и т.н.", "и т.н"}:
                        never.append(item)
            continue

        m = _ROW.match(line.replace(_ESCAPED_PIPE, _PIPE_PLACEHOLDER))
        if not m:
            continue
        raw_en, raw_bg = m.group("en").strip(), m.group("bg").strip()
        if _SEP.match(raw_en) or _SEP.match(raw_bg):
            continue
        en = _strip_md(raw_en).replace(_PIPE_PLACEHOLDER, "|")
        bg = _strip_md(raw_bg).replace(_PIPE_PLACEHOLDER, "|")
        if en.lower() in {"английски", "english"}:
            continue
        terms.append({"en": en, "bg": bg})
        if en == bg and en not in keep_english:
            keep_english.append(en)

    # de-duplicate, preserve order
    seen: set[str] = set()
    unique_terms = []
    for t in terms:
        if t["en"] in seen:
            continue
        seen.add(t["en"])
        unique_terms.append(t)

    return {
        "terms": unique_terms,
        "keep_english": keep_english,
        "never_translate": list(dict.fromkeys(never)),
    }


def _load_json(path: Path | None) -> dict | None:
    if path is None or not Path(path).exists():
        return None
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) and data.get("terms") is not None else None


def build_glossary(md_path: Path | None = None, out_path: Path | None = None) -> dict:
    """Parse the protocol markdown, falling back to an already-built glossary.

    engine.main.serve() calls this unconditionally for Bulgarian, so a missing
    source file used to raise FileNotFoundError straight through startup —
    and preflight could not catch it, since preflight only checks that the
    OUTPUT json exists. A prebuilt glossary is a perfectly good substitute, so
    prefer it over dying. The output file is only rewritten when the markdown
    actually parsed, so a fallback can never overwrite a good glossary.
    """
    path = Path(md_path) if md_path is not None else protocol_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        for fallback in (out_path, PACKAGED_GLOSSARY_PATH):
            data = _load_json(fallback)
            if data is not None:
                print(f"lang: {exc}; using prebuilt glossary {fallback}", file=sys.stderr)
                return data
        print(f"lang: {exc}; no prebuilt glossary available — "
              "Bulgarian terminology will be minimal", file=sys.stderr)
        return {"terms": [], "keep_english": list(KEEP_ENGLISH), "never_translate": []}

    data = parse_protocol(text)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def glossary_prompt_block(glossary: dict, max_terms: int = 220) -> str:
    lines = [
        "## ЕЗИК НА ИГРАТА — БЪЛГАРСКИ",
        "",
        "Разказвай, води NPC репликите и давай подсказки НА БЪЛГАРСКИ.",
        "При първо споменаване на игрови термин в сцена ползвай формата",
        "`Български (English)`; след това само българската форма.",
        "",
        "### Термини, които ВИНАГИ остават на английски",
        ", ".join(glossary.get("keep_english", [])),
        "",
        "### НИКОГА не превеждай",
        "Имена на герои и NPC-та, раси и подраси, локации, божества, заклинания",
        "и магически предмети. Вплитай ги в българския текст без превод.",
        "Пример: „Двамата Dwarf-а прекосиха моста към Waterdeep.“",
        "Примери от протокола: " + ", ".join(glossary.get("never_translate", [])[:40]),
        "",
        "### Речник",
    ]
    for term in glossary.get("terms", [])[:max_terms]:
        lines.append(f"- {term['en']} → {term['bg']}")
    return "\n".join(lines)
