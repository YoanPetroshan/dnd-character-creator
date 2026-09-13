"""Query the indexed 2024 rules corpus. One entry in, one compact entry out.

Run:
    python3 -m engine.rules.lookup monster "Goblin Boss"
    python3 -m engine.rules.lookup item "Bag of Holding"
    python3 -m engine.rules.lookup rule "grappling"
    python3 -m engine.rules.lookup loot --cr 3 --kind individual
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

from engine.config import json_dir
from engine.rules.index import load_index

MAX_CHARS = 6000

# difflib.SequenceMatcher ratio() threshold above which a fuzzy match is
# trusted without a second opinion. Chosen so a near-exact match like
# "Opportunity Attack" -> "Opportunity Attacks" (ratio 0.973, a mere
# pluralization) clears it, while a coincidental-but-wrong match like
# "Grappling" -> "Mapping" (ratio 0.75) does not.
_HIGH_CONFIDENCE = 0.9

# 5etools source text embeds cross-reference markup like {@damage 8d6},
# {@variantrule Sphere|XPHB}, {@hazard burning|XPHB}. Strip the wrapper and
# keep the first pipe-separated segment (the display text). Some tags —
# {@h}, {@actTrigger}, {@actResponse}, {@actSaveFail}, {@actSaveSuccess},
# {@actSaveSuccessOrFail}, {@recharge}, {@hom} — carry no body at all
# (confirmed via the real corpus: {@h} alone appears 650+ times across the
# bestiary); those get a readable label instead of vanishing into nothing.
_TAG = re.compile(r"\{@(\w+)(?:\s+([^}]*))?\}")

_EMPTY_TAG_LABELS = {
    "h": "Hit: ",
    "actTrigger": "Trigger: ",
    "actResponse": "Response: ",
    "actSaveFail": "Failure: ",
    "actSaveSuccess": "Success: ",
    "actSaveSuccessOrFail": "Success or Failure: ",
    "recharge": "(Recharge) ",
}


def strip_tags(text: str) -> str:
    def _replace(m: "re.Match[str]") -> str:
        tag, body = m.group(1), m.group(2)
        if body is not None:
            return body.split("|")[0]
        return _EMPTY_TAG_LABELS.get(tag, "")

    result = _TAG.sub(_replace, text)
    # A label like "Trigger: " butting up against the source text's own
    # leading space (e.g. "{@actTrigger} A creature...") leaves "Trigger:  A".
    return re.sub(r"[ \t]{2,}", " ", result)


def find(name: str, kind: str | None = None, index: dict | None = None) -> dict | None:
    data = index if index is not None else load_index()
    entries = data.get("entries", [])
    if kind:
        entries = [e for e in entries if e.get("kind") == kind]
    if not entries:
        return None

    for entry in entries:                      # exact
        if entry["name"] == name:
            return entry
    low = name.lower()
    for entry in entries:                      # case-insensitive
        if entry["name"].lower() == low:
            return entry

    names = [e["name"] for e in entries]

    # A high-confidence difflib match (near-exact modulo pluralization/typo,
    # e.g. "Opportunity Attack" -> "Opportunity Attacks" at ratio 0.973) is
    # trusted outright and never second-guessed by the substring check below.
    close = difflib.get_close_matches(name, names, n=1, cutoff=_HIGH_CONFIDENCE)
    if close:
        return next(e for e in entries if e["name"] == close[0])

    # No high-confidence difflib match. Rather than fall back to a loose
    # difflib cutoff — which lets a short, coincidentally letter-heavy,
    # UNRELATED name outscore a real topical match (confirmed on the real
    # corpus: querying "Grappling", which has no exact rule heading, scores
    # the unrelated heading "Mapping" at ratio 0.75 — higher than the
    # genuinely relevant "Grappling Hook (2 GP)") — look for the query text
    # verbatim inside a candidate name. This is a much stronger signal than
    # an ambiguous ratio and correctly rescues the "Grappling" case.
    #
    # Only the query-inside-candidate direction is used, never the reverse
    # (candidate-inside-query). The reverse direction is what previously
    # broke "Sneak Attack": the short, generic, unrelated heading "Attack"
    # (a Bastion-rules heading in the DMG) is a substring of the query
    # "Sneak Attack", but that's not meaningful evidence of relevance — no
    # "Sneak Attack" heading exists in the corpus, and the honest answer is
    # "not found", not a wrong short match.
    substr_hits = [e for e in entries if low in e["name"].lower()]
    if substr_hits:
        return min(substr_hits, key=lambda e: len(e["name"]))

    return None


def fetch_record(entry: dict, directory: Path | None = None) -> dict | None:
    if entry.get("kind") == "rule":
        return _fetch_markdown(entry)
    directory = Path(directory) if directory is not None else json_dir()
    path = directory / entry["file"]
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    records = data.get(entry["key"], [])
    pos = entry.get("pos", -1)
    if not isinstance(records, list) or not (0 <= pos < len(records)):
        return None
    return records[pos]


def _fetch_markdown(entry: dict) -> dict | None:
    path = Path(entry["file"])
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = max(0, entry.get("line", 1) - 1)
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("#"):
            break
        body.append(line)
        if sum(len(x) for x in body) > MAX_CHARS:
            break
    return {"name": entry["name"], "source": entry.get("source", ""),
            "entries": ["\n".join(body).strip()]}


def _flatten(value, out: list[str], depth: int = 0) -> None:
    if depth > 6 or sum(len(x) for x in out) > MAX_CHARS:
        return
    if isinstance(value, str):
        out.append(strip_tags(value))
    elif isinstance(value, list):
        for item in value:
            _flatten(item, out, depth + 1)
    elif isinstance(value, dict):
        if value.get("name"):
            # Action/item/reward names can themselves carry markup, e.g.
            # "Fire Breath {@recharge 5}" on nearly every dragon — confirmed
            # on the real corpus (24% of bestiary-xmm.json monsters). Route
            # through strip_tags just like the string branch above does.
            out.append(f"**{strip_tags(value['name'])}.**")
        for key in ("entries", "items", "rows", "entry"):
            if key in value:
                _flatten(value[key], out, depth + 1)


def format_monster(rec: dict) -> str:
    ac = rec.get("ac")
    if isinstance(ac, list) and ac:
        ac_val = ac[0].get("ac") if isinstance(ac[0], dict) else ac[0]
    else:
        ac_val = ac
    hp = rec.get("hp", {})
    hp_val = hp.get("average") if isinstance(hp, dict) else hp
    cr = rec.get("cr", "?")
    cr_val = cr.get("cr", "?") if isinstance(cr, dict) else cr
    abilities = " ".join(
        f"{k.upper()} {rec.get(k)}" for k in ("str", "dex", "con", "int", "wis", "cha")
        if rec.get(k) is not None
    )

    lines = [
        f"# {rec.get('name', '?')}  [{rec.get('source', '?')}]",
        f"AC {ac_val} | HP {hp_val} | CR {cr_val}",
    ]
    if abilities:
        lines.append(abilities)
    for section in ("trait", "action", "bonus", "reaction", "legendary"):
        items = rec.get(section)
        if not items:
            continue
        lines.append(f"\n## {section}")
        body: list[str] = []
        _flatten(items, body)
        lines.append("\n".join(body))
    return "\n".join(lines)[:MAX_CHARS]


def format_generic(rec: dict) -> str:
    head = f"# {rec.get('name', '?')}"
    if rec.get("source"):
        head += f"  [{rec['source']}]"
    meta = [f"{k}: {rec[k]}" for k in ("type", "rarity", "rating", "trapHazType")
            if rec.get(k)]
    body: list[str] = []
    _flatten(rec.get("entries", []), body)
    parts = [head]
    if meta:
        parts.append(" | ".join(meta))
    parts.append("\n".join(body))
    return "\n".join(parts)[:MAX_CHARS]


def format_record(entry: dict, rec: dict) -> str:
    if entry.get("kind") == "monster":
        return format_monster(rec)
    return format_generic(rec)


def srd_fallback(name: str, category: str | None = None) -> str | None:
    """Query the skill's bundled SRD dataset as a last resort.

    The user's `spells-xphb.json` covers the 2024 PHB spell list, so this
    only fires for a spell that file doesn't have (third-party, homebrew).
    The bundled set is 2014-flavoured — the caller must say so when printing.
    """
    scripts = Path(__file__).resolve().parents[2] / "skills" / "dnd" / "scripts"
    if not (scripts / "lookup.py").exists():
        return None
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import lookup as srd_lookup  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        return srd_lookup.lookup(name, category=category)
    except Exception:  # noqa: BLE001 — a fallback must never crash the tool
        return None


def _cr_value(cr) -> float:
    if isinstance(cr, (int, float)):
        return float(cr)
    text = str(cr).strip()
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            return float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def loot_table(cr: float, kind: str = "individual", directory: Path | None = None) -> dict | None:
    directory = Path(directory) if directory is not None else json_dir()
    path = directory / "loot.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for table in data.get(kind, []):
        lo, hi = table.get("crMin"), table.get("crMax")
        if lo is None or hi is None:
            continue
        if _cr_value(lo) <= cr <= _cr_value(hi):
            return table
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="engine.rules.lookup")
    ap.add_argument("kind", choices=["monster", "item", "spell", "rule", "trap",
                                     "hazard", "reward", "chapter", "loot", "any"])
    ap.add_argument("name", nargs="?", default="")
    ap.add_argument("--cr", type=float, default=None)
    ap.add_argument("--kind", dest="loot_kind", default="individual")
    ap.add_argument("--json", action="store_true", help="dump the raw record")
    args = ap.parse_args(argv)

    if args.kind == "loot":
        if args.cr is None:
            print("loot requires --cr", file=sys.stderr)
            return 2
        table = loot_table(args.cr, args.loot_kind)
        if table is None:
            print(f"No {args.loot_kind} loot table for CR {args.cr}")
            return 1
        print(json.dumps(table, ensure_ascii=False, indent=2)[:MAX_CHARS])
        return 0

    if not args.name:
        print("name is required", file=sys.stderr)
        return 2

    search_kind = None if args.kind == "any" else args.kind
    entry = find(args.name, kind=search_kind)

    if entry is None and args.kind in ("spell", "any"):
        text = srd_fallback(args.name, "spell" if args.kind == "spell" else None)
        if text:
            print(text)
            print("\n[Справка: вграден SRD — 2014 текст; провери срещу PHB 2024]")
            return 0

    if entry is None:
        print(f"Няма запис за „{args.name}“ ({args.kind}). "
              f"Провери правописа или импровизирай по DMG 2024.")
        return 1

    rec = fetch_record(entry)
    if rec is None:
        print(f"Индексът сочи към липсващ запис: {entry}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2)[:MAX_CHARS])
    else:
        print(format_record(entry, rec))
        print(f"\n[Справка: {entry.get('source') or entry.get('file')}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
