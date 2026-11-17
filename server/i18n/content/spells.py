"""Translator tooling for the Bulgarian spell-text overlay (developer-only, not in the offline pack). Run from server/:

    python -m i18n.content.spells export --ids fireball,shield --out work.json
    python -m i18n.content.spells export --source XPHB --limit 20 --only-missing --out work.json
    python -m i18n.content.spells apply work.json        # validates every record, merges the valid ones, exit 1 on a reject
    python -m i18n.content.spells status                 # translated / stale / missing per source

Work file: a JSON list of {id, name, source, hash, desc, higherLevel, material, castingCondition}; `export` writes the
English texts, the translator fills in the Bulgarian ones and keeps `id` and `hash` untouched."""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

from i18n.content import store

DICE = re.compile(r"\b\d*d\d+\b")
INTEGER = re.compile(r"(?<!\w)\d+(?!\w)")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
# Thousands groups: "1,000" (English) and "1 000" / "1\u2009000" / "1\u00a0000" (Bulgarian) both count as 1000.
_GROUPED = re.compile(r"(?<=\d)[,\u2009\u00a0 ](?=\d{3}(?!\d))")


def _numbers(text: str) -> list[str]:
    return INTEGER.findall(_GROUPED.sub("", text))
LATIN = re.compile(r"[A-Za-z]")
LANG = "bg"


def _paragraphs(fields: dict) -> list[str]:
    """Every English / Bulgarian text of a record, as one list (material and castingCondition when present)."""
    texts = list(fields.get("desc") or []) + list(fields.get("higherLevel") or [])
    texts += [fields[k] for k in ("material", "castingCondition") if isinstance(fields.get(k), str)]
    return texts


def validate(english: dict, record: dict) -> list[str]:
    """Reasons `record` (Bulgarian values) is not acceptable for the spell whose current English fields are `english`;
    empty when it is fine."""
    problems: list[str] = []
    if record.get("hash") != store.source_hash(english):
        problems.append("hash: the English text has changed since the export (export again)")
    bg: dict = {}
    for key in ("desc", "higherLevel"):
        value = record.get(key)
        if not isinstance(value, list) or not all(isinstance(p, str) for p in value):
            problems.append(f"{key}: must be a list of strings")
            bg[key] = None
            continue
        bg[key] = value
        if len(value) != len(english[key]):
            problems.append(f"{key}: {len(value)} paragraphs, the English has {len(english[key])}")
    for key in ("material", "castingCondition"):
        value = record.get(key)
        if value is not None and not isinstance(value, str):
            problems.append(f"{key}: must be a string or null")
            value = None
        if value is not None and english[key] is None:
            problems.append(f"{key}: the English spell has none")
        bg[key] = value
    if problems:
        return problems

    # Pair every Bulgarian text with its English source; a null material / castingCondition stays English (effective text).
    pairs = list(zip(english["desc"], bg["desc"])) + list(zip(english["higherLevel"], bg["higherLevel"]))
    pairs += [(english[k], bg[k]) for k in ("material", "castingCondition") if bg[k] is not None]
    for en, text in pairs:
        if not text.strip():
            problems.append("empty paragraph")
        elif text == en and (" | " in text or not re.search(r"[A-Za-z\u0400-\u04ff]", text)):
            continue  # a table row of names / numbers or a separator row (|---|---|) may be copied as it is
        elif not CYRILLIC.search(text):
            problems.append(f"no Cyrillic in a paragraph: {text[:40]!r}")
        elif text == en and len(en.split()) > 3:
            problems.append(f"paragraph left in English: {en[:40]!r}")
    effective = {**bg, **{k: english[k] for k in ("material", "castingCondition") if bg[k] is None}}
    en_all, bg_all = " ".join(_paragraphs(english)), " ".join(_paragraphs(effective))
    en_dice, bg_dice = collections.Counter(DICE.findall(en_all)), collections.Counter(DICE.findall(bg_all))
    # Every English die must survive; Bulgarian may repeat a die the English names ("още един d8" for "these d8s").
    if (en_dice - bg_dice) or any(d not in en_dice for d in bg_dice - en_dice):
        problems.append(f"dice expressions differ: English {sorted(DICE.findall(en_all))}, Bulgarian {sorted(DICE.findall(bg_all))}")
    missing = collections.Counter(_numbers(en_all)) - collections.Counter(_numbers(bg_all))
    if missing:
        problems.append(f"numbers missing from the Bulgarian text: {sorted(missing.elements())}")
    return problems


def _load_spells() -> dict[str, dict]:
    from catalog.loader import load

    return load().spells


def export_records(spells: dict[str, dict], overlay: dict, *, ids=None, source=None, limit=None, only_missing=False) -> list[dict]:
    chosen = sorted(spells) if ids is None else list(ids)
    out = []
    for sid in chosen:
        spell = spells.get(sid)
        if spell is None:
            raise KeyError(f"unknown spell id {sid!r}")
        if source and spell.get("source", "SRD") != source:
            continue
        fields = store.spell_fields(spell)
        h = store.source_hash(fields)
        if only_missing and (overlay.get(sid) or {}).get("hash") == h:
            continue
        out.append({"id": sid, "name": spell["name"], "source": spell.get("source", "SRD"), "hash": h, **fields})
        if limit is not None and len(out) >= limit:
            break
    return out


def apply_records(spells: dict[str, dict], overlay: dict, records: list) -> tuple[dict, list[tuple[str, list[str]]]]:
    """(the overlay with the valid records merged in, [(id, reasons)] per record; empty reasons = accepted)."""
    merged = dict(overlay)
    results: list[tuple[str, list[str]]] = []
    for rec in records:
        sid = rec.get("id") if isinstance(rec, dict) else None
        if not isinstance(sid, str) or sid not in spells:
            results.append((str(sid), ["id: unknown spell"]))
            continue
        reasons = validate(store.spell_fields(spells[sid]), rec)
        results.append((sid, reasons))
        if not reasons:
            merged[sid] = {"hash": rec["hash"], "desc": rec["desc"], "higherLevel": rec["higherLevel"],
                           "material": rec.get("material"), "castingCondition": rec.get("castingCondition")}
    return merged, results


def status_counts(spells: dict[str, dict], overlay: dict) -> dict[str, collections.Counter]:
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for sid, spell in spells.items():
        entry = overlay.get(sid)
        if not isinstance(entry, dict):
            state = "missing"
        elif entry.get("hash") == store.source_hash(store.spell_fields(spell)):
            state = "translated"
        else:
            state = "stale"
        counts[spell.get("source", "SRD")][state] += 1
    return counts


def overlay_path() -> Path:
    return store.I18N_DIR / LANG / "spells.json"


def write_overlay(overlay: dict) -> None:
    path = overlay_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overlay, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    store.load_overlay.cache_clear()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m i18n.content.spells", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="write the English texts of some spells to a work file")
    which = ex.add_mutually_exclusive_group(required=True)
    which.add_argument("--ids", help="comma-separated spell ids")
    which.add_argument("--source", help="book code, e.g. XPHB")
    ex.add_argument("--limit", type=int)
    ex.add_argument("--only-missing", action="store_true", help="skip spells whose translation is present and fresh")
    ex.add_argument("--out", required=True)
    ap_apply = sub.add_parser("apply", help="validate a translated work file and merge the valid records")
    ap_apply.add_argument("file")
    ap_apply.add_argument("--check", action="store_true", help="validate only, write nothing")
    sub.add_parser("status", help="translated / stale / missing per source")
    args = ap.parse_args(argv)

    spells = _load_spells()
    overlay = store.load_overlay("spells", LANG)
    if args.cmd == "export":
        ids = [i for i in args.ids.split(",") if i] if args.ids else None
        try:
            records = export_records(spells, overlay, ids=ids, source=args.source, limit=args.limit, only_missing=args.only_missing)
        except KeyError as err:
            print(err.args[0], file=sys.stderr)
            return 1
        Path(args.out).write_text(json.dumps(records, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"exported {len(records)} spell(s) to {args.out}")
        return 0
    if args.cmd == "apply":
        records = json.loads(Path(args.file).read_text(encoding="utf-8"))
        if not isinstance(records, list):
            print("the work file must be a JSON list", file=sys.stderr)
            return 1
        merged, results = apply_records(spells, overlay, records)
        for sid, reasons in results:
            print(f"OK     {sid}" if not reasons else f"REJECT {sid}: " + "; ".join(reasons))
        if merged != overlay and not args.check:
            write_overlay(merged)
        return 1 if any(reasons for _, reasons in results) else 0
    counts = status_counts(spells, overlay)
    print(f"{'source':<10}{'translated':>11}{'stale':>7}{'missing':>9}")
    total: collections.Counter = collections.Counter()
    for src in sorted(counts):
        c = counts[src]
        total += c
        print(f"{src:<10}{c['translated']:>11}{c['stale']:>7}{c['missing']:>9}")
    print(f"{'total':<10}{total['translated']:>11}{total['stale']:>7}{total['missing']:>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
