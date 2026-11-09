"""Spec -> draft -> resolution -> oracle + detectors; findings file with fid dedupe and known-gap tags."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import time

from . import checks, matrix, weird
from .spec import CharSpec, resolve_spec

SEVERITY = {  # everything not listed is S2
    "S1": {"PB", "ABIL-MOD", "ABIL-RANGE", "HP", "HIT-DICE", "SAVES", "SKILLS", "PASSIVES", "INITIATIVE", "SLOTS", "PACT", "SPELL-DC",
           "AC", "SPEED", "ATTACKS-PER-ACTION", "W-EXC", "W-FILL", "W-EXPORT", "W-NUMBERS", "W-IDEMPOTENT"},
    "S3": {"W-PERF", "W-WARN", "W-UNAVAILABLE", "W-EMPTY", "W-EXPORT-NAME"},
}
KNOWN_GAPS_FILE = pathlib.Path(__file__).with_name("known_gaps.json")


def severity(rule: str) -> str:
    for s, rules in SEVERITY.items():
        if rule in rules:
            return s
    return "S2"


def load_known_gaps(path=None) -> list[dict]:
    p = pathlib.Path(path) if path else KNOWN_GAPS_FILE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def known_gap(result: dict, spec: CharSpec, gaps: list[dict]) -> str | None:
    text = json.dumps([result["expected"], result["actual"]], ensure_ascii=False, default=str).lower()
    for g in gaps:
        if g["rule"] not in ("*", result["check"]):
            continue
        m = g.get("match", {})
        if "class" in m and m["class"] not in [c[0] for c in spec.classes]:
            continue
        if "ruleset" in m and spec.ruleset not in ([m["ruleset"]] if isinstance(m["ruleset"], str) else m["ruleset"]):
            continue
        if "subclass" in m and not any(c[2] and m["subclass"] in c[2] for c in spec.classes):
            continue
        if "feature" in m and m["feature"] not in text:
            continue
        if "feat" in m and m["feat"] not in text:
            continue
        return g["tag"]
    return None


def _discriminator(result: dict) -> str:
    """W-* detectors: the same defect shows on any class, so the key is the defect (first leaf path / first id, digits stripped)."""
    act = result.get("actual")
    first = act[0] if isinstance(act, list) and act else (next(iter(act.values())) if isinstance(act, dict) and act else act)
    if isinstance(first, (list, tuple)) and first:
        first = first[0]
    text = re.sub(r"\d+", "#", str(first))
    return text.split(" = ")[0][:80] if result["check"] == "W-W9" else re.sub(r"(class|background|species):[^ ']*", r"\1:*", text)[:80]


def fid(result: dict, spec: CharSpec) -> str:
    if result["check"].startswith("W-"):
        key = "|".join([result["check"], spec.ruleset, _discriminator(result)])
    else:
        key = "|".join([result["check"], spec.ruleset, ",".join(sorted(c[0] for c in spec.classes)),
                        ",".join(sorted(str(c[2]) for c in spec.classes if c[2]))])
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def run_spec(spec: CharSpec, catalog, exports: bool = True, gaps: list[dict] | None = None, only: set | None = None) -> dict:
    from engine.resolve import resolve
    t = time.perf_counter()
    rec = {"id": spec.id, "spec": spec, "results": [], "n_checks": 0, "error": None, "draft": None, "res": None}
    try:
        draft, res = resolve_spec(spec, catalog, resolve)
        rec["draft"], rec["res"] = draft, res
        results = [] if spec.weird else checks.run_checks(draft, res, only)
        results += weird.detect(spec, draft, res, resolve, catalog, exports)
    except Exception as e:  # engine exception on a spec = S1 finding
        results = [{"check": "W-FILL" if type(e).__name__ == "FillStuck" else "W-EXC", "ok": False, "expected": "resolve() returns", "actual": f"{type(e).__name__}: {e}"[:300], "cite": "engine"}]
    rec["n_checks"] = len(results)
    rec["results"] = [r for r in results if not r["ok"]]
    for r in rec["results"]:
        r["known_gap"] = known_gap(r, spec, gaps if gaps is not None else load_known_gaps())
    rec["ms"] = round((time.perf_counter() - t) * 1000)
    return rec


def finding(result: dict, spec: CharSpec) -> dict:
    return {"fid": fid(result, spec), "spec": spec.to_json(), "spec_id": spec.id, "rule": result["check"],
            "severity": severity(result["check"]), "expected": result["expected"], "actual": result["actual"],
            "source": result.get("cite"), "known_gap": result.get("known_gap"), "occurrences": 1}


def write_findings(path, findings: list[dict]) -> dict:
    """Append findings to a JSONL file, merging on fid (occurrences += 1, up to 5 example spec ids)."""
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                f = json.loads(line)
                existing[f["fid"]] = f
    new = merged = 0
    for f in findings:
        old = existing.get(f["fid"])
        if old:
            if old["spec_id"] != f["spec_id"] and f["spec_id"] not in old.setdefault("also", []):
                old["occurrences"] += 1
                if len(old["also"]) < 5:
                    old["also"].append(f["spec_id"])
            merged += 1
        else:
            existing[f["fid"]] = f
            new += 1
    p.write_text("".join(json.dumps(f, ensure_ascii=False, default=str) + "\n" for f in existing.values()), encoding="utf-8")
    return {"new": new, "merged": merged, "total": len(existing)}


def find_spec(token: str, catalog) -> list[CharSpec]:
    """A JSON object, a path to a .json/.jsonl file, or a spec id from any tier / the weird generator."""
    t = token.strip()
    if t.startswith("{"):
        return [CharSpec.from_json(t)]
    p = pathlib.Path(t)
    if p.exists():
        return [CharSpec.from_json(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    pool = [s for tier in matrix.TIERS for s in matrix.generate(tier, 0, catalog=catalog)] + weird.generate()
    hit = [s for s in pool if s.id == t] or [s for s in pool if re.search(t, s.id)]
    if not hit:
        raise SystemExit(f"no spec {token!r}")
    return hit
