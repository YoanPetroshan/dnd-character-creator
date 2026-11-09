"""Always-on detectors (``detect``) and the odd-but-legal draft generator (``generate`` / ``apply``).

Detectors return the same ``{check, ok, expected, actual, cite}`` records as checks.py, rule ids start with ``W-``."""
from __future__ import annotations

import copy
import json
import random
import time

from .spec import CharSpec

UNICODE_NAMES = ["Ӂ̷̢ǻ̸ Ünïcödé 龍 ‮ rtl", "Зорница-Ивановa 🐉", "O'Brien \"quotes\" <b>x</b> & ;\n---\n# h", "", "名" * 120]


def _w(rule, ok, expected, actual, cite="weird.py"):
    return {"check": rule, "ok": bool(ok), "expected": expected, "actual": actual, "cite": cite}


def _walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")
    else:
        yield path, obj


def detect(spec: CharSpec, draft: dict, res: dict, resolve=None, catalog=None, exports: bool = True) -> list[dict]:
    out: list[dict] = []
    sheet, der = res["sheet"], res["derived"]
    legal = not spec.weird and "prereq-negative" not in spec.tags
    # numbers
    bad = []
    for p, v in _walk(der):
        if "carryingCapacity" in p:
            continue  # weights are legitimately large (pushDragLift 15 x STR)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and (v != v or v < -10 or v > 400):
            bad.append((p, v))
    degraded = any(p.get("id") == "unknown-species" for p in res.get("problems", []))  # no species record: no speed to report
    for key, lo, hi in (("hitPointMax", 1, 1500), ("armorClass", 1, 40), ("speed", 0, 400), ("proficiencyBonus", 2, 6)):
        v = der.get(key, lo)
        if v is None:
            if not (degraded and key == "speed"):
                bad.append((key, None))  # a missing number is a finding, not a crash of the detector
        elif not lo <= v <= hi:
            bad.append((key, v))
    out.append(_w("W-NUMBERS", not bad, "no absurd / negative derived numbers", bad[:5] or "ok"))
    # empty sections
    empty = [k for k in ("features", "classes") if not sheet.get(k)] + (["savingThrows"] if not sheet["proficiencies"]["savingThrows"] else []) \
        + (["hitDice"] if not der.get("hitDice") else [])
    out.append(_w("W-EMPTY", not empty, "features, classes, saving throws, hit dice are never empty", empty or "ok"))
    # duplicate card ids / options
    ids = [c["id"] for c in res["choices"]]
    dup = {i for i in ids if ids.count(i) > 1}
    dup_opts = [c["id"] for c in res["choices"] if len({o["id"] for o in c["options"]}) != len(c["options"])]
    out.append(_w("W-DUP-IDS", not dup and not dup_opts, "unique card ids and option ids", {"cards": sorted(dup)[:3], "options": dup_opts[:3]} or "ok"))
    if legal:
        pend = [c["id"] for c in res["choices"] if c["status"] == "pending"]
        out.append(_w("W-PENDING", not pend, "no pending card after the filler", pend[:5] or "ok"))
        unav = [c["id"] for c in res["choices"] if c["status"] == "unavailable"]
        out.append(_w("W-UNAVAILABLE", not unav, "unavailable cards, listed for judgment", unav[:5] or "ok"))
        probs = [p["id"] for p in res["problems"] if not p["id"].startswith("multiclass-prerequisite-unmet")]  # MC-PREREQ judges those
        out.append(_w("W-PROBLEMS", not probs, "no problems on a filled legal draft", probs[:5] or "ok"))
        informational = ("ruleset-2024-", "asi-double-dip-prevented", "armor-not-proficient-", "armor-strength-", "fly-armor-")
        warns = [w["id"] for w in res["warnings"] if not w["id"].startswith(informational)]
        if spec.sources or (spec.tags and spec.tags[0] == "T3"):
            warns = []  # narrow sources / edge cases warn on purpose
        out.append(_w("W-WARN", not warns, "no warnings on a filled legal draft", warns[:5] or "ok"))
        flagged = _unexplained_pruned(draft, res, resolve, catalog)
        out.append(_w("W-PRUNED", not flagged, "nothing pruned on a fresh draft (stale filler picks and cap notes excepted)",
                      [f"{p.get('choiceId')}: {p.get('reason')}" if isinstance(p, dict) else p for p in flagged][:5] or "ok"))
    # ruleset leakage
    if spec.ruleset == "2014":
        leak = [f["id"] for f in sheet.get("feats", []) if f["id"].endswith("-xphb")]
        out.append(_w("W-LEAK", not leak, "no 2024 feat on a 2014 sheet", leak or "ok"))
    # idempotence / draft not mutated
    if resolve is not None:
        before = json.dumps(draft, sort_keys=True, default=str)
        r1 = json.dumps(resolve(draft, catalog), sort_keys=True, default=str)
        r2 = json.dumps(resolve(draft, catalog), sort_keys=True, default=str)
        out.append(_w("W-IDEMPOTENT", r1 == r2 and before == json.dumps(draft, sort_keys=True, default=str),
                      "resolve twice gives the same result and leaves the draft alone", "differs" if r1 != r2 else "draft mutated" if before != json.dumps(draft, sort_keys=True, default=str) else "ok"))
        best = 1e9
        for _ in range(3):
            t = time.perf_counter()
            resolve(draft, catalog)
            best = min(best, (time.perf_counter() - t) * 1000)
        out.append(_w("W-PERF", best <= 50, "resolve best of 3 <= 50 ms", f"{best:.1f} ms"))
    if exports:
        out += _export_checks(res)
    return out


def _strip_choices(obj, ids: set):
    """Remove the given choice ids from every ``choices`` mapping of a draft (in place)."""
    if isinstance(obj, dict):
        ch = obj.get("choices")
        if isinstance(ch, dict):
            for i in ids:
                ch.pop(i, None)
        for v in obj.values():
            _strip_choices(v, ids)
    elif isinstance(obj, list):
        for v in obj:
            _strip_choices(v, ids)


def _unexplained_pruned(draft: dict, res: dict, resolve, catalog) -> list:
    """``pruned`` entries on a filled draft that are not benign.  Two shapes are benign and not reported:
    an ability increase the engine ignored at the 20 cap ("... is already at maximum ... ignored", the manual 19 / 20 base
    specs), and a stale pick the filler stored while its card existed and a later pick made the card vanish (Kobold skill vs
    the Draconic Sorcery variant): removing those picks leaves a draft that resolves without any pruned entry."""
    pruned = [p for p in res.get("pruned") or [] if not (isinstance(p, dict) and "already at maximum" in str(p.get("reason", "")))]
    if not pruned or resolve is None:
        return pruned
    ids = {p.get("choiceId") for p in pruned if isinstance(p, dict) and p.get("choiceId")}
    if len(ids) != len(pruned):
        return pruned
    d2 = copy.deepcopy(draft)
    _strip_choices(d2, ids)
    again = [p for p in resolve(d2, catalog).get("pruned") or [] if not (isinstance(p, dict) and "already at maximum" in str(p.get("reason", "")))]
    return again


def _w9_unexplained(fails: list[str], res: dict) -> list[str]:
    """Drop the W9 leaves that are not export defects (each verified against the exporter, see the VC T3 campaign notes):
    * ``sheet.startingGold = 0``: export_fields prints the gold line only when the amount is non-zero;
    * ``details.spellSlotRegainsUse = True``: printed as the label "spellSlotRegainsUse" (export_fields.resource_detail_parts),
      the audit's FLAG_TEXT table just has no entry for it;
    * a character name with glyphs outside the bundled DejaVu font (emoji, CJK) in the PDF: fpdf2 drops those glyphs, the
      remaining characters are printed (pinned by the harness test)."""
    from export_labels import label
    import markdown_export
    name = (res.get("sheet") or {}).get("name") or ""
    exotic = any(ord(c) > 0xFFFF or 0x2E80 <= ord(c) <= 0x9FFF or ord(c) in (0x202E, 0x202D) for c in name)
    out = []
    for f in fails:
        if f.startswith("sheet.startingGold = 0 "):
            continue
        if "details.spellSlotRegainsUse = True" in f and label("bg", "spellSlotRegainsUse") in markdown_export.to_markdown(res):
            continue
        if exotic and f.startswith("sheet.name = ") and f.endswith("missing from the PDF"):
            continue
        out.append(f)
    return out


def _export_checks(res: dict) -> list[dict]:
    out = []
    try:
        import export
        import markdown_export
        import pdf_export
        y = export.to_yaml(res)
        m = markdown_export.to_markdown(res)
        p = pdf_export.to_pdf(res)
        problems = []
        if not y or not m:
            problems.append("empty yaml/markdown")
        if len(p) < 10_000:
            problems.append(f"pdf {len(p)} bytes")
        out.append(_w("W-EXPORT", not problems, "yaml, markdown and PDF (>= 10 KB) build", problems or "ok"))
        sheet = res["sheet"]
        missing = [t for t in (sheet["name"],) if t and t not in m]
        out.append(_w("W-EXPORT-NAME", not missing, "the character name reaches the Markdown", missing or "ok"))
        try:
            import test_export_completeness as w9
            fails, _used = w9.audit(res, "bg")
            fails = _w9_unexplained(fails, res)
            out.append(_w("W-W9", not fails, "every sheet / derived leaf reaches Markdown and PDF (W9 matcher)", fails or "ok", "tests/test_export_completeness.py audit"))
        except ImportError:
            pass
    except Exception as e:
        out.append(_w("W-EXPORT", False, "exports build", f"{type(e).__name__}: {e}"))
    return out


# ------------------------------------------------------------------ generator of odd drafts
OPS = ["switch_ruleset", "narrow_sources", "level_edge", "ability_limits", "empty_picks", "max_picks", "unicode_name", "swap_species", "drop_class"]


def apply(spec: CharSpec, draft: dict) -> dict:
    """Mutate a freshly filled draft according to ``spec.weird`` (a dict op -> argument)."""
    w = spec.weird
    rng = random.Random(spec.id)
    if "switch_ruleset" in w:
        draft["ruleset"] = w["switch_ruleset"]
    if "narrow_sources" in w:
        draft["sources"] = list(w["narrow_sources"])
    if "level_edge" in w:
        for c, lvl in zip(draft["classes"], w["level_edge"]):
            c["level"] = lvl
    if "ability_limits" in w:
        draft["abilities"]["base"] = {a: w["ability_limits"][i % len(w["ability_limits"])] for i, a in enumerate(("STR", "DEX", "CON", "INT", "WIS", "CHA"))}
    if w.get("empty_picks"):
        for c in draft["classes"]:
            c["choices"] = {}
        draft["species"]["choices"] = {}
        draft["background"]["choices"] = {}
        draft["equipment"]["choices"] = {}
    if w.get("max_picks"):
        for c in draft["classes"]:
            for k, v in list(c["choices"].items()):
                if isinstance(v, list):
                    c["choices"][k] = v * 3
    if "unicode_name" in w:
        draft["name"] = UNICODE_NAMES[w["unicode_name"] % len(UNICODE_NAMES)]
    if "swap_species" in w:
        draft["species"] = {"id": w["swap_species"], "choices": draft["species"]["choices"]}
    if w.get("drop_class") and len(draft["classes"]) > 1:
        draft["classes"].pop(rng.randrange(len(draft["classes"])))
    return draft


def generate(seed: int = 0, n: int = 24) -> list[CharSpec]:
    """Deterministic odd-but-legal specs: each carries a ``weird`` mutation applied after the filler."""
    rng = random.Random(seed)
    classes = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"]
    out = []
    for i in range(n):
        op = OPS[i % len(OPS)]
        cs = [[rng.choice(classes), rng.choice([1, 3, 20]), None]]
        if i % 3 == 0:
            cs.append([rng.choice(classes), rng.choice([1, 2, 10]), None])
        w: dict = {}
        if op == "switch_ruleset":
            w["switch_ruleset"] = rng.choice(["2014", "2024", "mixed"])
        elif op == "narrow_sources":
            w["narrow_sources"] = rng.choice([["srd"], ["phb"], ["xphb"], ["does-not-exist"]])
        elif op == "level_edge":
            w["level_edge"] = [rng.choice([1, 20, 21, 0, -3]) for _ in cs]
        elif op == "ability_limits":
            w["ability_limits"] = rng.choice([[1], [30], [0, 31], [3, 18, 20, 8, 99, -4]])
        elif op in ("empty_picks", "max_picks"):
            w[op] = True
        elif op == "unicode_name":
            w["unicode_name"] = i
        elif op == "swap_species":
            w["swap_species"] = rng.choice(["human", "human-xphb", "no-such-species", "tiefling-phb"])
        elif op == "drop_class":
            w["drop_class"] = True
        out.append(CharSpec(id=f"weird-{i:03d}-{op}", ruleset=rng.choice(["2014", "2024", "mixed"]), classes=cs,
                            abilities={"method": "manual", "base": {"STR": 10, "DEX": 12, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}, "priority": []},
                            filler={"mode": "seeded", "seed": i}, weird=w, tags=["weird", op]))
    return out
