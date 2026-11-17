"""Translator tooling for the Bulgarian content overlays (developer-only, not in the offline pack). Run from server/:

    python -m i18n.content.tool --kind species export --ids elf,dwarf --out work.json
    python -m i18n.content.tool --kind items export --source SRD --limit 20 --only-missing --out work.json
    python -m i18n.content.tool --kind spells apply work.json   # validates every record, merges the valid ones, exit 1 on a reject
    python -m i18n.content.tool --kind species status           # translated / stale / missing per source

Kinds: spells, species, items, item-rules (property and mastery texts; keys `property:<index>:<PHB|XPHB>`, `mastery:<Name>`).
`python -m i18n.content.spells ...` is the same tool with --kind spells.

Work file: a JSON list of {id, name, source, hash, <the kind's fields>}; `export` writes the English texts, the translator
fills in the Bulgarian ones and keeps `id` and `hash` untouched. Fields per kind: spells desc / higherLevel / material /
castingCondition; species fluff[] and traits[{name, desc[]}] (trait names stay English, the count and order must match);
items desc[] / special[]; item-rules desc[]."""
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
SCALARS = {"spells": ("material", "castingCondition")}  # optional string fields (null = keep the English)
LISTS = {"spells": ("desc", "higherLevel"), "species": ("fluff",), "items": ("desc", "special"), "item-rules": ("desc",)}


def _is_strings(value) -> bool:
    return isinstance(value, list) and all(isinstance(p, str) for p in value)


def _check_paragraphs(pairs: list[tuple[str, str]], problems: list[str]) -> None:
    for en, text in pairs:
        if not text.strip():
            problems.append("empty paragraph")
        elif text == en and (" | " in text or not re.search(r"[A-Za-z\u0400-\u04ff]", text)):
            continue  # a table row of names / numbers or a separator row (|---|---|) may be copied as it is
        elif not CYRILLIC.search(text):
            problems.append(f"no Cyrillic in a paragraph: {text[:40]!r}")
        elif text == en and len(en.split()) > 3:
            problems.append(f"paragraph left in English: {en[:40]!r}")


def validate(english: dict, record: dict, kind: str = "spells") -> list[str]:
    """Reasons `record` (Bulgarian values) is not acceptable for the record whose current English fields are `english`
    (see store.fields_for); empty when it is fine."""
    problems: list[str] = []
    if record.get("hash") != store.source_hash(kind, english):
        problems.append("hash: the English text has changed since the export (export again)")
    groups: list[tuple[list[str], list[str]]] = []  # (English paragraphs, Bulgarian paragraphs), in reading order
    bg: dict = {}
    for key in LISTS[kind]:
        value = record.get(key)
        if not _is_strings(value):
            problems.append(f"{key}: must be a list of strings")
            continue
        bg[key] = value
        if len(value) != len(english[key]):
            problems.append(f"{key}: {len(value)} paragraphs, the English has {len(english[key])}")
        groups.append((english[key], value))
    if kind == "species":
        traits = record.get("traits")
        if not isinstance(traits, list) or not all(isinstance(t, dict) and _is_strings(t.get("desc")) for t in traits):
            problems.append("traits: must be a list of {desc: list of strings}")
        elif len(traits) != len(english["traits"]):
            problems.append(f"traits: {len(traits)} traits, the English has {len(english['traits'])}")
        else:
            for i, (en_desc, t) in enumerate(zip(english["traits"], traits)):
                if len(t["desc"]) != len(en_desc):
                    problems.append(f"traits[{i}].desc: {len(t['desc'])} paragraphs, the English has {len(en_desc)}")
                groups.append((en_desc, t["desc"]))
    scalars = []  # (English, Bulgarian) of the optional strings that are set
    for key in SCALARS.get(kind, ()):
        value = record.get(key)
        if value is not None and not isinstance(value, str):
            problems.append(f"{key}: must be a string or null")
            value = None
        if value is not None and english[key] is None:
            problems.append(f"{key}: the English {'spell' if kind == 'spells' else 'record'} has none")
        bg[key] = value
        scalars.append((key, english[key], value))
    if problems:
        return problems

    # Pair every Bulgarian text with its English source; a null material / castingCondition stays English (effective text).
    pairs = [p for en_list, bg_list in groups for p in zip(en_list, bg_list)]
    pairs += [(en, v) for _k, en, v in scalars if v is not None]
    _check_paragraphs(pairs, problems)
    en_all = " ".join([p for en_list, _ in groups for p in en_list] + [en for _k, en, _v in scalars if isinstance(en, str)])
    bg_all = " ".join([p for _, bg_list in groups for p in bg_list]
                      + [v if v is not None else en for _k, en, v in scalars if isinstance(en, str)])
    en_dice, bg_dice = collections.Counter(DICE.findall(en_all)), collections.Counter(DICE.findall(bg_all))
    # Every English die must survive; Bulgarian may repeat a die the English names ("още един d8" for "these d8s").
    if (en_dice - bg_dice) or any(d not in en_dice for d in bg_dice - en_dice):
        problems.append(f"dice expressions differ: English {sorted(DICE.findall(en_all))}, Bulgarian {sorted(DICE.findall(bg_all))}")
    missing = collections.Counter(_numbers(en_all)) - collections.Counter(_numbers(bg_all))
    if missing:
        problems.append(f"numbers missing from the Bulgarian text: {sorted(missing.elements())}")
    return problems


def item_rule_records(catalog) -> dict[str, dict]:
    """`property:<index>:<PHB|XPHB>` and `mastery:<Name>` -> {name, source, desc}: the rules texts the item route serves."""
    out = {f"property:{index}:{book}": {"name": index.replace("-", " ").title(), "source": book, "desc": list(desc)}
           for (index, book), desc in catalog.item_properties.items()}
    out.update({f"mastery:{name}": {"name": name, "source": "XPHB", "desc": list(desc)}
                for name, desc in catalog.weapon_masteries.items()})
    return out


def load_records(kind: str) -> dict[str, dict]:
    """The catalog records of a kind by overlay key. Species records carry `fluff` and `traitDetails` exactly as
    GET /api/catalog/species/<id> serves them; items are the catalog item records."""
    from catalog.loader import load

    catalog = load()
    if kind == "spells":
        return catalog.spells
    if kind == "items":
        return catalog.items
    if kind == "species":
        from catalog.official.race_fluff import species_fluff, trait_details

        out = {}
        for rid, race in catalog.races.items():
            subs = catalog.subraces_of(rid)
            out[rid] = {**race, "fluff": species_fluff(race.get("name", ""), race.get("source", ""), [s.get("name", "") for s in subs]),
                        "traitDetails": trait_details(race, catalog.traits)}
        return out
    if kind == "item-rules":
        return item_rule_records(catalog)
    raise KeyError(kind)


def _load_spells() -> dict[str, dict]:
    return load_records("spells")


def _label(kind: str) -> str:
    return {"spells": "spell", "species": "species", "items": "item", "item-rules": "item rule"}[kind]


def _export_fields(kind: str, fields: dict, record: dict) -> dict:
    if kind == "species":  # the trait names ride along for the translator; apply ignores them
        names = [t.get("name", "") for t in record.get("traitDetails") or []]
        return {"fluff": fields["fluff"], "traits": [{"name": n, "desc": d} for n, d in zip(names, fields["traits"])]}
    return fields


def export_records(records: dict[str, dict], overlay: dict, *, ids=None, source=None, limit=None, only_missing=False,
                   kind: str = "spells") -> list[dict]:
    chosen = sorted(records) if ids is None else list(ids)
    out = []
    for rid in chosen:
        rec = records.get(rid)
        if rec is None:
            raise KeyError(f"unknown {_label(kind)} id {rid!r}")
        if source and rec.get("source", "SRD") != source:
            continue
        fields = store.fields_for(kind, rec)
        h = store.source_hash(kind, fields)
        if only_missing and (overlay.get(rid) or {}).get("hash") == h:
            continue
        out.append({"id": rid, "name": rec["name"], "source": rec.get("source", "SRD"), "hash": h, **_export_fields(kind, fields, rec)})
        if limit is not None and len(out) >= limit:
            break
    return out


def _entry(kind: str, rec: dict) -> dict:
    if kind == "spells":
        return {"hash": rec["hash"], "desc": rec["desc"], "higherLevel": rec["higherLevel"],
                "material": rec.get("material"), "castingCondition": rec.get("castingCondition")}
    if kind == "species":
        return {"hash": rec["hash"], "fluff": rec["fluff"], "traits": [{"desc": t["desc"]} for t in rec["traits"]]}
    if kind == "items":
        return {"hash": rec["hash"], "desc": rec["desc"], "special": rec["special"]}
    return {"hash": rec["hash"], "desc": rec["desc"]}


def apply_records(records: dict[str, dict], overlay: dict, work: list, kind: str = "spells") -> tuple[dict, list[tuple[str, list[str]]]]:
    """(the overlay with the valid records merged in, [(id, reasons)] per record; empty reasons = accepted)."""
    merged = dict(overlay)
    results: list[tuple[str, list[str]]] = []
    for rec in work:
        rid = rec.get("id") if isinstance(rec, dict) else None
        if not isinstance(rid, str) or rid not in records:
            results.append((str(rid), [f"id: unknown {_label(kind)}"]))
            continue
        reasons = validate(store.fields_for(kind, records[rid]), rec, kind)
        results.append((rid, reasons))
        if not reasons:
            merged[rid] = _entry(kind, rec)
    return merged, results


def status_counts(records: dict[str, dict], overlay: dict, kind: str = "spells") -> dict[str, collections.Counter]:
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for rid, rec in records.items():
        entry = overlay.get(rid)
        if not isinstance(entry, dict):
            state = "missing"
        elif entry.get("hash") == store.source_hash(kind, store.fields_for(kind, rec)):
            state = "translated"
        else:
            state = "stale"
        counts[rec.get("source", "SRD")][state] += 1
    return counts


def overlay_path(kind: str = "spells") -> Path:
    return store.I18N_DIR / LANG / f"{kind}.json"


def write_overlay(overlay: dict, kind: str = "spells") -> None:
    path = overlay_path(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(overlay, ensure_ascii=False, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    store.load_overlay.cache_clear()


def main(argv=None, *, default_kind: str | None = None, prog: str = "python -m i18n.content.tool") -> int:
    ap = argparse.ArgumentParser(prog=prog, description=__doc__.split("\n")[0])
    ap.add_argument("--kind", choices=store.KINDS, default=default_kind, required=default_kind is None,
                    help="which overlay: spells, species, items, item-rules")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="write the English texts of some records to a work file")
    which = ex.add_mutually_exclusive_group(required=True)
    which.add_argument("--ids", help="comma-separated ids")
    which.add_argument("--source", help="book code, e.g. XPHB")
    which.add_argument("--all", action="store_true", help="every record")
    ex.add_argument("--limit", type=int)
    ex.add_argument("--only-missing", action="store_true", help="skip records whose translation is present and fresh")
    ex.add_argument("--out", required=True)
    ap_apply = sub.add_parser("apply", help="validate a translated work file and merge the valid records")
    ap_apply.add_argument("file")
    ap_apply.add_argument("--check", action="store_true", help="validate only, write nothing")
    sub.add_parser("status", help="translated / stale / missing per source")
    args = ap.parse_args(argv)
    kind = args.kind

    try:
        records = load_records(kind)
    except NotImplementedError as err:
        print(err.args[0], file=sys.stderr)
        return 2
    overlay = store.load_overlay(kind, LANG)
    if args.cmd == "export":
        ids = [i for i in args.ids.split(",") if i] if args.ids else None
        try:
            out = export_records(records, overlay, ids=ids, source=args.source, limit=args.limit, only_missing=args.only_missing, kind=kind)
        except KeyError as err:
            print(err.args[0], file=sys.stderr)
            return 1
        Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"exported {len(out)} {_label(kind)}(s) to {args.out}")
        return 0
    if args.cmd == "apply":
        work = json.loads(Path(args.file).read_text(encoding="utf-8"))
        if not isinstance(work, list):
            print("the work file must be a JSON list", file=sys.stderr)
            return 1
        merged, results = apply_records(records, overlay, work, kind)
        for rid, reasons in results:
            print(f"OK     {rid}" if not reasons else f"REJECT {rid}: " + "; ".join(reasons))
        if merged != overlay and not args.check:
            write_overlay(merged, kind)
        return 1 if any(reasons for _, reasons in results) else 0
    counts = status_counts(records, overlay, kind)
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
