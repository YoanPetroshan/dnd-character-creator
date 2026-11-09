"""``python -m tools.chartest`` (run from server/tests). See docs/CAMPAIGN-PROTOCOL.md."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import checks, matrix, runner, weird
from .spec import CharSpec, load_catalog, have_data

DEFAULT_OUT = os.environ.get("CHARTEST_FINDINGS", "campaign/findings.jsonl")


def _specs(args, catalog) -> list[CharSpec]:
    if getattr(args, "spec", None):
        return [s for tok in args.spec for s in runner.find_spec(tok, catalog)]
    if args.tier == "WEIRD":
        return weird.generate(args.seed, args.size * (args.batch + 1))[args.batch * args.size:]
    return matrix.batch(args.tier, args.batch, args.size, args.seed, catalog)


def cmd_gen(args, catalog):
    for s in _specs(args, catalog):
        print(s.to_json())


def cmd_run(args, catalog):
    gaps = [] if args.no_known_gaps else runner.load_known_gaps(args.known_gaps)
    findings, total_fail = [], 0
    for spec in _specs(args, catalog):
        rec = runner.run_spec(spec, catalog, exports=not args.no_exports, gaps=gaps)
        new = [r for r in rec["results"] if not r["known_gap"]]
        total_fail += len(new)
        tag = "OK  " if not new else "FAIL"
        names = ",".join(sorted({r["check"] for r in new})) or "-"
        kg = sorted({r["known_gap"] for r in rec["results"] if r["known_gap"]})
        print(f"{tag} {spec.id:<46} checks={rec['n_checks']:<3} fail=[{names}]" + (f" known={kg}" if kg else "") + f" {rec['ms']}ms")
        for r in rec["results"]:
            findings.append(runner.finding(r, spec))
    if not args.no_write and findings:
        s = runner.write_findings(args.out, [f for f in findings if not f["known_gap"] or args.keep_known])
        print(f"findings -> {args.out}: {s}")
    print(f"unexplained failures: {total_fail}")


def cmd_show(args, catalog):
    from engine.resolve import resolve
    for spec in _specs(args, catalog):
        rec = runner.run_spec(spec, catalog, exports=False)
        res = rec["res"]
        if not res:
            print(spec.id, "-> exception:", rec["results"][0]["actual"])
            continue
        s, d = res["sheet"], res["derived"]
        L = [f"== {spec.id}  ({spec.ruleset}, level {s['level']})",
             "classes: " + ", ".join(f"{c['name']} {c['level']}" + (f" ({c['subclass']['name']})" if c.get("subclass") else "") for c in s["classes"]),
             f"species: {s['species'].get('name')}  background: {s['background'].get('name')}",
             "abilities: " + " ".join(f"{a}={s['abilities'][a]}({d['abilityModifiers'][a]:+d})" for a in checks.ABILITIES),
             f"PB +{d['proficiencyBonus']}  HP {d['hitPointMax']}  HD {d['hitDice']}  AC {d['armorClass']}  speed {d['speed']}  init {d['initiative']:+d}  attacks/action {d['attacksPerAction']}",
             "saves: " + " ".join(f"{a}{v:+d}" for a, v in d["savingThrows"].items()),
             "save profs: " + ",".join(s["proficiencies"]["savingThrows"]),
             "skills (proficient): " + ", ".join(f"{k[6:]} {d['skills'][k]:+d}" for k in s["proficiencies"]["skills"]),
             f"slots: {d['spellSlots']}  pact: {d['warlockSpellSlots']}",
             "spells: " + "; ".join(f"{e['classId']} DC {e.get('spellSaveDC')} atk {e.get('spellAttackBonus')} cantrips {len(e['cantrips'])} known {len(e['known'])}" for e in s["spells"]),
             "feats: " + ", ".join(f["name"] for f in s["feats"]),
             "resources: " + ", ".join(f"{r['name']} {r['uses']}" for r in d["classResources"][:14]),
             "features: " + ", ".join(f"{f['name']}@{f.get('level')}" for f in s["features"][:30]),
             f"problems: {[p['id'] for p in res['problems']]}  warnings: {[w['id'] for w in res['warnings']][:6]}  pruned: {len(res['pruned'])}"]
        print("\n".join(L[:60]))


def cmd_explain(args, catalog):
    specs = runner.find_spec(args.char, catalog)
    for spec in specs:
        rec = runner.run_spec(spec, catalog, exports=False)
        res = rec["res"]
        if res:
            x = checks.Ctx(rec["draft"], res)
            print(f"{spec.id}: classes {x.classes} ruleset {x.ruleset} PB {x.pb} abilities {x.ab} mods {x.mods}")
        hits = [r for r in checks.run_checks(rec["draft"], res) if r["check"] == args.check] if res else []
        hits += [r for r in rec["results"] if r["check"] == args.check and r not in hits]
        for r in hits:
            print(json.dumps({k: r.get(k) for k in ("check", "ok", "expected", "actual", "cite", "known_gap")}, ensure_ascii=False, indent=1, default=str))
        if not hits:
            print(f"no result for {args.check} (not applicable to this character); rules: {', '.join(sorted(set(checks.rule_ids())))}")


def cmd_finding_add(args, catalog):
    spec = runner.find_spec(args.spec, catalog)[0] if args.spec else CharSpec(id="manual")
    r = {"check": args.rule, "expected": args.expected, "actual": args.actual, "cite": args.source, "known_gap": args.known_gap}
    f = runner.finding(r, spec)
    if args.severity:
        f["severity"] = args.severity
    f["note"] = args.note
    print(runner.write_findings(args.out, [f]))


def cmd_gaps(args, catalog):
    for g in runner.load_known_gaps(args.known_gaps):
        print(f"{g['tag']:<28} rule={g['rule']:<20} {g['note']}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.chartest", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, spec_pos=True):
        if spec_pos:
            p.add_argument("spec", nargs="*", help="spec JSON, .json/.jsonl path, or spec id (regex)")
        p.add_argument("--tier", choices=[*matrix.TIERS, "WEIRD"], default="T1")
        p.add_argument("--batch", type=int, default=0)
        p.add_argument("--size", type=int, default=10)
        p.add_argument("--seed", type=int, default=0)

    g = sub.add_parser("gen"); common(g); g.set_defaults(fn=cmd_gen)
    r = sub.add_parser("run"); common(r)
    r.add_argument("--out", default=DEFAULT_OUT); r.add_argument("--known-gaps", nargs="?", default=None, const=None,
                   help="known-gaps JSON file (default: the packaged known_gaps.json)")
    r.add_argument("--no-known-gaps", action="store_true"); r.add_argument("--keep-known", action="store_true", help="also write known-gap findings")
    r.add_argument("--no-exports", action="store_true"); r.add_argument("--no-write", action="store_true")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("show"); common(s); s.set_defaults(fn=cmd_show)
    e = sub.add_parser("explain"); e.add_argument("char"); e.add_argument("check"); e.set_defaults(fn=cmd_explain)
    f = sub.add_parser("finding"); fs = f.add_subparsers(dest="sub", required=True)
    fa = fs.add_parser("add")
    for a in ("rule", "expected", "actual", "source"):
        fa.add_argument(f"--{a}", required=True)
    fa.add_argument("--spec"); fa.add_argument("--severity", choices=["S1", "S2", "S3"]); fa.add_argument("--note", default="")
    fa.add_argument("--known-gap", default=None); fa.add_argument("--out", default=DEFAULT_OUT); fa.set_defaults(fn=cmd_finding_add)
    k = sub.add_parser("gaps"); k.add_argument("--known-gaps", default=None); k.set_defaults(fn=cmd_gaps)
    args = ap.parse_args(argv)
    if not have_data() and args.cmd != "gaps":
        print("5etools data missing (DND_OFFICIAL_DATA=none?): the harness needs server/data/official", file=sys.stderr)
        return 2
    args.fn(args, load_catalog() if args.cmd != "gaps" else None)
    return 0
