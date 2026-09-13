#!/usr/bin/env python3
"""campaign_builder.py — create a campaign, and load an adventure into it.

Until now the only way to turn a written adventure into a playable campaign
was `/dm:dnd import`, a procedure Claude executes: it reads the source,
decides the structure, and authors the campaign files with its own judgment.
That works well and stays the better option when it is available — but it
means a person with a markdown module and no Claude session had no path at
all, and the local engine cannot drive that loop itself.

This is the deterministic path. It does strictly less than Claude does: it
does not interpret the adventure, invent a world, or populate NPCs. It
splits the source on its own headings, writes the campaign skeleton from the
templates, and wires the arc pointer to the first chapter — which is exactly
enough for the engine to start narrating from real source text. Everything
it fills in is marked so a human (or Claude, later) can see what is a
placeholder and what came from the adventure.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import paths  # noqa: E402

# A campaign folder name: safe on every filesystem, readable in a URL.
_SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}[a-z0-9]$")
def _heading_re(level: int) -> "re.Pattern":
    """Headings at exactly `level` — `(?!#)` stops `##` matching a `###`."""
    return re.compile(r"^" + ("#" * level) + r"\s+(?!#)(.+?)\s*$", re.M)


# Chapters are looked for from the top down, stopping at the first level
# that actually divides the document. Published adventures are wildly
# inconsistent about where they start: some open at `#`, plenty at `##`,
# and one real module in this repo has no `#` at all, a single `##` title,
# then `###` sections holding `####` rooms. `_MAX_HEADING_LEVEL` stops the
# search at `###` on purpose — `####` is usually the individual room, and
# splitting there would write a file per room and break the engine's
# room-code extraction, which expects rooms to sit *inside* a chapter.
_MAX_HEADING_LEVEL = 3


def slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", str(text), flags=re.UNICODE).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:64] or "campaign"


def valid_name(name: str) -> bool:
    return bool(_SLUG_OK.match(name or ""))


def templates_dir() -> Path:
    return Path(_HERE).parent / "templates"


def _read_template(name: str) -> str:
    p = templates_dir() / name
    return p.read_text(encoding="utf-8") if p.exists() else ""


def split_chapters(markdown: str, max_chapters: int = 40) -> list:
    """Split an adventure into chapters on its own headings.

    Prefers `#` headings and falls back to `##` when the document uses a
    single `#` title with `##` sections — which is how most single-adventure
    markdown is actually written. Text before the first heading is kept as a
    leading chapter rather than dropped, since that is usually the
    introduction.
    """
    text = (markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []

    # Walk down heading levels until one genuinely divides the document.
    # A level with a single heading is the document's title, not a chapter
    # boundary; splitting there would leave the whole book as one file.
    matches: list = []
    for level in range(1, _MAX_HEADING_LEVEL + 1):
        found = list(_heading_re(level).finditer(text))
        if len(found) >= 2:
            matches = found
            break

    if not matches:
        return [{"title": "Adventure", "text": text.strip()}]

    chapters = []
    lead = text[: matches[0].start()].strip()
    if len(lead) > 200:
        chapters.append({"title": "Introduction", "text": lead})

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].strip()
        if body:
            chapters.append({"title": m.group(1).strip(), "text": body})

    # A very long document with dozens of tiny headings would produce a file
    # per heading; fold the tail into the last chapter instead.
    if len(chapters) > max_chapters:
        head, tail = chapters[: max_chapters - 1], chapters[max_chapters - 1:]
        head.append({"title": tail[0]["title"],
                     "text": "\n\n".join(c["text"] for c in tail)})
        chapters = head
    return chapters


def create_campaign(name: str, *, title: str = "", ruleset: str = "2024",
                    exist_ok: bool = False, description: str = "") -> Path:
    """Write an empty but valid campaign skeleton."""
    if not valid_name(name):
        raise ValueError(
            f"{name!r} is not a usable campaign folder name — use lowercase "
            "letters, digits and hyphens (e.g. 'lost-mine-of-phandelver')")
    camp = paths.campaigns_dir() / name
    if camp.exists() and not exist_ok:
        raise FileExistsError(f"campaign {name!r} already exists at {camp}")

    (camp / "characters").mkdir(parents=True, exist_ok=True)
    (camp / "source").mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    display_title = title or name.replace("-", " ").title()

    state = _read_template("state.md") or "# Campaign: <name>\n"
    state = (state
             .replace("# Campaign: <name>", f"# Campaign: {name}")
             .replace("**Created:** <date>", f"**Created:** {today}")
             .replace("**Ruleset:** 2014", f"**Ruleset:** {ruleset}"))
    if "## Campaign Arc" not in state:
        state += "\n## Campaign Arc\n*(no arc yet)*\n"
    _write(camp / "state.md", state)

    for fname in ("world.md", "arc.md", "npcs.md", "session-log.md"):
        body = _read_template(fname)
        if body:
            _write(camp / fname, body.replace("<name>", display_title))

    _write(camp / "source-index.md",
           f"# Source Index — {name}\n\n"
           "*Which file holds which chapter. Read one chapter at a time.*\n\n"
           "| Chapter ID | File | Title |\n|---|---|---|\n")

    if description.strip():
        set_description(name, description)
    return camp


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _arc_yaml(chapters: list, title: str) -> str:
    first = chapters[0] if chapters else {"title": "Chapter 1"}
    beats = "\n".join(
        f'    - "{c["title"][:110].replace(chr(34), chr(39))}"' for c in chapters[:8])
    return (
        "## Campaign Arc\n"
        "```yaml\n"
        "# --- STRUCTURED ARC POINTER (imported from markdown) ---\n"
        "type: structured\n"
        f'source: "{title[:110].replace(chr(34), chr(39))}"\n'
        "structure: linear\n"
        "current_act: 1\n"
        'current_chapter: "1.1"\n'
        "current_chapter_detail:\n"
        '  id: "1.1"\n'
        f'  title: "{first["title"][:110].replace(chr(34), chr(39))}"\n'
        '  location: ""   # fill in where the party actually starts\n'
        f'  source_ref: "source/{_chapter_filename(1, first["title"])}"\n'
        "  key_beats:\n"
        f"{beats or '    - \"Play through the adventure\"'}\n"
        'next_chapter: "1.2"\n'
        "steering_notes: >\n"
        "  Imported from markdown without interpretation. The chapter list is\n"
        "  the source's own headings; refine locations and beats by hand or\n"
        "  with /dm:dnd arc.\n"
        "```\n"
    )


def _chapter_filename(index: int, title: str) -> str:
    return f"{index}-{slugify(title) or 'chapter'}.md"


def import_markdown(campaign: str, markdown: str, *, source_title: str = "",
                    set_arc: bool = True) -> dict:
    """Split `markdown` into `source/` chapters and index them.

    Returns what it did, so a caller can show it rather than guess.
    """
    camp = paths.find_campaign(campaign)
    if not camp.exists():
        raise FileNotFoundError(f"no campaign {campaign!r}")

    chapters = split_chapters(markdown)
    if not chapters:
        raise ValueError("the adventure file has no readable text")

    src = camp / "source"
    src.mkdir(parents=True, exist_ok=True)

    written = []
    for i, ch in enumerate(chapters, start=1):
        fname = _chapter_filename(i, ch["title"])
        _write(src / fname, ch["text"] + "\n")
        written.append({"id": f"1.{i}", "file": f"source/{fname}",
                        "title": ch["title"], "chars": len(ch["text"])})

    title = source_title or (chapters[0]["title"] if chapters else campaign)
    rows = "\n".join(f"| {w['id']} | `{w['file']}` | {w['title']} |" for w in written)
    _write(camp / "source-index.md",
           f"# Source Index — {campaign}\n\n"
           f"**Source:** {title}\n\n"
           "*Which file holds which chapter. The engine reads one chapter at a\n"
           "time — never pre-load ahead.*\n\n"
           "| Chapter ID | File | Title |\n|---|---|---|\n" + rows + "\n")

    if set_arc:
        state_path = camp / "state.md"
        state = state_path.read_text(encoding="utf-8") if state_path.exists() else ""
        arc = _arc_yaml(chapters, title)
        # Replace an existing "## Campaign Arc" section in place, so an
        # import into a campaign that already has one doesn't leave two.
        pattern = re.compile(r"^##\s+Campaign Arc\s*$.*?(?=^##\s+(?!#)|\Z)",
                             re.M | re.S)
        state = pattern.sub(arc, state) if pattern.search(state) else (state + "\n" + arc)
        _write(state_path, state)

    return {"campaign": campaign, "chapters": written, "title": title,
            "source_dir": str(src)}


def list_campaigns() -> list:
    """Every campaign, with just enough to choose between them."""
    root = paths.campaigns_dir()
    if not root.exists():
        return []
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        state = d / "state.md"
        text = state.read_text(encoding="utf-8", errors="replace") if state.exists() else ""
        # [ \t]* (not \s*) around the capture — \s* would cross the
        # newline when the field is empty and slurp the next line's text.
        m_loc = re.search(r"^-\s*\*\*Location:\*\*[ \t]*(.*?)[ \t]*$", text, re.M)
        m_desc = re.search(r"^-\s*\*\*Description:\*\*[ \t]*(.*?)[ \t]*$", text, re.M)
        m_sessions = re.search(r"\*\*Session count:\*\*\s*(\d+)", text)
        m_last = re.search(r"\*\*Last session:\*\*\s*(.+?)\s{2,}", text)
        m_rules = re.search(r"\*\*Ruleset:\*\*\s*(\S+)", text)
        chars = sorted((d / "characters").glob("*.yaml")) if (d / "characters").exists() else []
        if not chars and (d / "characters").exists():
            chars = sorted((d / "characters").glob("*.md"))
        out.append({
            "name": d.name,
            "location": (m_loc.group(1)[:160] if m_loc else ""),
            "description": (m_desc.group(1)[:400] if m_desc else ""),
            "sessions": int(m_sessions.group(1)) if m_sessions else 0,
            "last_session": (m_last.group(1).strip() if m_last else ""),
            "ruleset": m_rules.group(1) if m_rules else "",
            "party": [p.stem for p in chars],
            "has_source": (d / "source").exists() and any((d / "source").glob("*.md")),
            "playable": bool(chars),
        })
    return out


def active_campaign() -> str:
    f = paths.runtime_dir() / ".campaign"
    try:
        return f.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def set_active_campaign(name: str) -> str:
    """Point the engine at a campaign. Refuses one that isn't there — a
    dangling name means the next launch fails preflight for no visible
    reason."""
    if not (paths.campaigns_dir() / name).exists():
        raise FileNotFoundError(f"no campaign {name!r}")
    _write(paths.runtime_dir() / ".campaign", name + "\n")
    return name


def set_description(name: str, text: str) -> str:
    """Write (or insert) the campaign's short description line in
    state.md. Handles campaigns created before this field existed in the
    template — inserts the line right after **Location:** if it's
    missing, rather than requiring it to already be there.

    Both branches pass a FUNCTION as re.sub()'s replacement, never a
    string: a replacement string is itself parsed for backreferences, so
    the user's own text would be interpreted rather than inserted. A
    backslash in the description ("C:\\docs", a trailing "\\") raised
    re.PatternError instead of saving, and a "\\1" in the description
    silently expanded to the captured Location line and got written to
    disk in its place. A function's return value is inserted literally."""
    camp = paths.campaigns_dir() / name
    if not camp.exists():
        raise FileNotFoundError(f"no campaign {name!r}")
    state_path = camp / "state.md"
    original = state_path.read_text(encoding="utf-8")
    clean = text.strip().replace("\n", " ")[:400]
    if re.search(r"^-\s*\*\*Description:\*\*", original, re.M):
        updated = re.sub(
            r"^-\s*\*\*Description:\*\*.*$",
            lambda _m: f"- **Description:** {clean}",
            original, count=1, flags=re.M)
    else:
        updated = re.sub(
            r"^-\s*\*\*Location:\*\*.*$",
            lambda m: m.group(0) + f"\n- **Description:** {clean}",
            original, count=1, flags=re.M)
    _write(state_path, updated)
    return clean


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        prog="campaign_builder",
        description="Create a campaign and load a markdown adventure into it.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="create an empty campaign")
    n.add_argument("name")
    n.add_argument("--title", default="")
    n.add_argument("--ruleset", default="2024", choices=["2014", "2024"])

    i = sub.add_parser("import", help="load a markdown adventure into a campaign")
    i.add_argument("campaign")
    i.add_argument("file", help="path to the .md adventure")
    i.add_argument("--title", default="")
    i.add_argument("--create", action="store_true",
                   help="create the campaign first if it doesn't exist")

    sub.add_parser("list", help="list campaigns")

    a = sub.add_parser("use", help="set the active campaign")
    a.add_argument("name")

    args = ap.parse_args()

    if args.cmd == "new":
        camp = create_campaign(args.name, title=args.title, ruleset=args.ruleset)
        print(f"created {camp}")
        return 0

    if args.cmd == "import":
        if args.create:
            try:
                create_campaign(args.campaign, title=args.title)
            except FileExistsError:
                pass
        text = Path(args.file).read_text(encoding="utf-8", errors="replace")
        res = import_markdown(args.campaign, text,
                              source_title=args.title or Path(args.file).stem)
        print(f"{res['campaign']}: {len(res['chapters'])} chapters → {res['source_dir']}")
        for c in res["chapters"]:
            print(f"  {c['id']:5} {c['file']:44} {c['chars']:>7} chars  {c['title'][:40]}")
        return 0

    if args.cmd == "list":
        for c in list_campaigns():
            mark = "*" if c["name"] == active_campaign() else " "
            print(f"{mark} {c['name']:38} sessions={c['sessions']:<3} "
                  f"party={len(c['party'])} source={'yes' if c['has_source'] else 'no'}")
        return 0

    if args.cmd == "use":
        print("active campaign:", set_active_campaign(args.name))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
