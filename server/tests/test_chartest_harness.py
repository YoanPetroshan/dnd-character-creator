"""VC0: tests of the character-test harness (tools/chartest). The harness is a tool, not a test module; these tests prove
the oracle passes on known-good drafts, fails when a value is corrupted, the matrix is deterministic, `run` is fast and
the findings file dedupes. Skips cleanly without the 5etools data."""
from __future__ import annotations

import ast
import copy
import json
import pathlib
import time

import pytest

from tools.chartest import cli, checks, matrix, runner, spec as S, weird
from tools.chartest.spec import CharSpec

pytestmark = pytest.mark.skipif(not S.have_data(), reason="5etools data missing (classes / official)")

PHB_EXAMPLE = {"1": 4, "2": 3, "3": 2}  # PHB 2014 p.165: Ranger 4 / Sorcerer 3 = 4/3/2

GOOD = {
    "fighter20": CharSpec(id="g-fighter20", ruleset="2014", classes=[["fighter", 20, "champion"]]),
    "wizard20-2024": CharSpec(id="g-wizard20-2024", ruleset="2024", classes=[["wizard", 20, "evoker-xphb"]]),
    "warlock7-2024": CharSpec(id="g-warlock7-2024", ruleset="2024", classes=[["warlock", 7, "fiend-xphb"]]),
    "bard10-2014": CharSpec(id="g-bard10-2014", ruleset="2014", classes=[["bard", 10, "lore"]]),
    "paladin6-warlock2": CharSpec(id="g-pal6-war2", ruleset="2014", prereqs=True, classes=[["paladin", 6, "devotion"], ["warlock", 2, None]],
                                  abilities={"method": "manual", "base": {"STR": 15, "DEX": 12, "CON": 14, "INT": 10, "WIS": 10, "CHA": 16}, "priority": []}),
    "ranger4-sorcerer3": CharSpec(id="g-ran4-sor3", ruleset="2014", prereqs=True, classes=[["ranger", 4, None], ["sorcerer", 3, None]],
                                  abilities={"method": "manual", "base": {"STR": 10, "DEX": 15, "CON": 14, "INT": 10, "WIS": 14, "CHA": 15}, "priority": []}),
}


@pytest.fixture(scope="module")
def catalog():
    return S.load_catalog()


@pytest.fixture(scope="module")
def samples(catalog):
    from engine.resolve import resolve
    out = {k: S.resolve_spec(v, catalog, resolve) for k, v in GOOD.items()}
    import kitchen_sink as ks
    d = ks.build("feats-2024-fighter19", catalog, resolve)
    d.setdefault("preferences", {})["usePrerequisites"] = {"feats": True}
    out["fighter19-feats"] = (d, resolve(d, catalog))
    return out


@pytest.mark.parametrize("name", list(GOOD))
def test_known_good_drafts_pass_every_check(samples, name):
    draft, res = samples[name]
    results = checks.run_checks(draft, res)
    assert [r for r in results if not r["ok"]] == []
    assert len(results) >= 15


def test_every_rule_is_exercised_by_a_known_good_draft(samples):
    seen = {r["check"] for d, res in samples.values() for r in checks.run_checks(d, res)}
    assert set(checks.rule_ids()) - seen == set()


def test_phb_multiclass_example_slots(samples):
    _d, res = samples["ranger4-sorcerer3"]
    assert {k: v for k, v in res["derived"]["spellSlots"].items() if v} == PHB_EXAMPLE
    assert res["derived"]["warlockSpellSlots"] == {} and samples["paladin6-warlock2"][1]["derived"]["warlockSpellSlots"] == {"1": 2}


def _bump(path, delta):
    def mut(d, r):
        node = r
        for p in path[:-1]:
            node = node[p]
        node[path[-1]] += delta
    return mut


def _card_count(suffix):
    def mut(d, r):
        next(c for c in r["choices"] if c["id"].endswith(suffix))["count"] += 1
    return mut


def _set(path, value):
    def mut(d, r):
        node = r
        for p in path[:-1]:
            node = node[p]
        node[path[-1]] = value
    return mut


def _first_save_prof_removed(d, r):
    r["sheet"]["proficiencies"]["savingThrows"].pop(0)


def _drop_class_features(d, r):
    r["sheet"]["features"] = [f for f in r["sheet"]["features"] if (f.get("source") or {}).get("kind") != "class"]


def _future_feature(d, r):
    r["sheet"]["features"].append({"source": {"kind": "class", "id": r["sheet"]["classes"][0]["id"], "label": "x"}, "name": "Future", "level": 99})


def _resource_up(d, r):
    for res in r["derived"]["classResources"]:
        if res["name"].lower().startswith(("rage", "ki", "focus", "sorcery", "channel")) and res["uses"]:
            res["uses"] += 1
            return
    raise AssertionError("no numeric resource")


def _dup_language(d, r):
    langs = r["sheet"]["proficiencies"]["languages"]
    langs.append(langs[0])


def _grappler(d, r):
    r["sheet"]["abilities"]["CHA"] = 3
    r["sheet"]["feats"].append({"id": "actor-xphb", "name": "Actor", "origin": "asi", "level": 4})


def _slots_wrong(d, r):
    slots = r["derived"]["spellSlots"]
    k = next(iter(slots))
    slots[k] += 1


# rule -> (sample, mutation). Each mutation must make exactly that rule fail on the otherwise good draft.
NEGATIVE = {
    "PB": ("fighter20", _bump(["derived", "proficiencyBonus"], 1)),
    "ABIL-MOD": ("fighter20", _bump(["derived", "abilityModifiers", "STR"], 1)),
    "ABIL-RANGE": ("fighter20", _set(["sheet", "abilities", "STR"], 27)),
    "HP": ("fighter20", _bump(["derived", "hitPointMax"], 7)),
    "HIT-DICE": ("fighter20", _set(["derived", "hitDice"], "19d10")),
    "SAVE-PROF": ("fighter20", _first_save_prof_removed),
    "SAVES": ("fighter20", _bump(["derived", "savingThrows", "STR"], 1)),
    "SKILLS": ("fighter20", _bump(["derived", "skills", "skill-acrobatics"], 1)),
    "PASSIVES": ("fighter20", _bump(["derived", "passiveInsight"], 1)),
    "INITIATIVE": ("fighter20", _bump(["derived", "initiative"], 2)),
    "SLOTS": ("wizard20-2024", _slots_wrong),
    "PACT": ("warlock7-2024", _set(["derived", "warlockSpellSlots"], {"5": 9})),
    "SPELL-DC": ("wizard20-2024", _bump(["sheet", "spells", 0, "spellSaveDC"], 1)),
    "CANTRIPS": ("wizard20-2024", _card_count("spells-cantrips")),
    "SPELLS-KNOWN": ("bard10-2014", _card_count("spells-known")),
    "SPELLBOOK": ("wizard20-2024", _card_count("spellbook")),
    "AC": ("fighter20", _bump(["derived", "armorClass"], 5)),
    "SPEED": ("fighter20", _bump(["derived", "speed"], 15)),
    "ATTACKS-PER-ACTION": ("fighter20", _set(["derived", "attacksPerAction"], 2)),
    "FEATURES-LEVEL": ("fighter20", _future_feature),
    "FEATURES-PRESENT": ("fighter20", _drop_class_features),
    "RESOURCES": ("paladin6-warlock2", None),  # replaced below by a Sorcerer / Monk sample
    "MC-PREREQ": ("paladin6-warlock2", lambda d, r: r["problems"].append({"id": "multiclass-prerequisite-unmet-paladin", "message": "x"})),
    "MC-PROF": ("ranger4-sorcerer3", lambda d, r: r["sheet"]["proficiencies"]["armor"].append("heavy-armor")),
    "DUPLICATES": ("fighter20", _dup_language),
    "FEAT-PREREQ": ("fighter19-feats", _grappler),
}


@pytest.mark.parametrize("rule", [r for r in NEGATIVE if r != "RESOURCES"])
def test_each_check_fails_when_the_actual_value_is_altered(samples, rule):
    sample, mut = NEGATIVE[rule]
    draft, res = samples[sample]
    assert [r for r in checks.run_checks(draft, res, {rule}) if not r["ok"]] == [], "the unaltered draft must pass"
    bad = copy.deepcopy(res)
    mut(draft, bad)
    hits = [r for r in checks.run_checks(draft, bad, {rule}) if not r["ok"]]
    assert hits, f"{rule} did not catch the corruption"
    assert hits[0]["cite"] and "expected" in hits[0] and "actual" in hits[0]


def test_resources_check_fails_when_a_table_number_is_altered(catalog):
    from engine.resolve import resolve
    spec = CharSpec(id="g-monk5-2014", ruleset="2014", classes=[["monk", 5, "open-hand"]])
    draft, res = S.resolve_spec(spec, catalog, resolve)
    assert [r for r in checks.run_checks(draft, res, {"RESOURCES"}) if not r["ok"]] == []
    assert checks.run_checks(draft, res, {"RESOURCES"}), "Monk Ki must be compared"
    bad = copy.deepcopy(res)
    _resource_up(draft, bad)
    assert [r for r in checks.run_checks(draft, bad, {"RESOURCES"}) if not r["ok"]]


def test_checks_module_imports_nothing_from_the_engine():
    tree = ast.parse((pathlib.Path(checks.__file__)).read_text(encoding="utf-8"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add((n.module or "").split(".")[0] if n.level == 0 else "<relative>")
    assert mods <= {"functools", "json", "math", "os", "pathlib", "re", "__future__"}, mods


def test_spec_to_draft_is_deterministic(catalog):
    from engine.resolve import resolve
    s = matrix.generate("T2", 0, catalog=catalog)[7]
    a = S.build_draft(CharSpec.from_json(s.to_json()), catalog, resolve)
    b = S.build_draft(CharSpec.from_json(s.to_json()), catalog, resolve)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_filler_modes_differ_but_each_settles(catalog):
    from engine.resolve import resolve
    drafts = []
    for mode in ("first", "last", "seeded", "alldiff"):
        sp = CharSpec(id="f-" + mode, ruleset="2014", classes=[["wizard", 5, None]], filler={"mode": mode, "seed": 3})
        d = S.build_draft(sp, catalog, resolve)
        assert not [c for c in resolve(d, catalog)["choices"] if c["status"] == "pending"]
        drafts.append(json.dumps(d["classes"], sort_keys=True))
    assert len(set(drafts)) >= 3


def test_matrix_sizes_and_determinism(catalog):
    sizes = {t: len(matrix.generate(t, 0, catalog=catalog)) for t in matrix.TIERS}
    assert sizes["T1"] == 180 and sizes["T2"] == 150 and sizes["T4"] == 9 and 50 <= sizes["T3"] <= 75
    for t in matrix.TIERS:
        a = [s.to_json() for s in matrix.generate(t, 5, catalog=catalog)]
        b = [s.to_json() for s in matrix.generate(t, 5, catalog=catalog)]
        assert a == b
    assert [s.to_json() for s in matrix.generate("T1", 0, catalog=catalog)] != [s.to_json() for s in matrix.generate("T1", 1, catalog=catalog)]
    ids = [s.id for t in matrix.TIERS for s in matrix.generate(t, 0, catalog=catalog)]
    assert len(ids) == len(set(ids))


def test_matrix_shape_rules(catalog):
    t1 = matrix.generate("T1", 0, catalog=catalog)
    assert {s.ruleset for s in t1} == {"2014", "2024", "mixed"}
    assert {c[1] for s in t1 for c in s.classes} >= {1, 3, 5, 11, 20}
    assert {c[0] for s in t1 for c in s.classes} == set(matrix.CLASSES)
    for t in matrix.TIERS:
        for s in matrix.generate(t, 0, catalog=catalog):
            assert len(s.classes) <= (3 if t == "T4" else 2), s.id
            assert s.total_level <= 20
            if len(s.classes) > 1 and "prereq-negative" not in s.tags:
                base = S.ability_scores(s.abilities)
                for c in s.classes:
                    need = [a for a in matrix.PRIMARY[c[0]]]
                    if c[0] == "fighter":
                        assert max(base["STR"], base["DEX"]) >= 13, s.id
                    else:
                        assert all(base[a] >= 13 for a in need), (s.id, c[0])
    assert len([s for s in matrix.generate("T2", 0, catalog=catalog) if len(s.classes) == 2]) == 150


def test_matrix_covers_every_class_subclass_species_background(catalog):
    assert matrix.coverage(catalog) == {"class": [], "species": [], "background": [], "subclass": []}


def test_run_five_specs_under_ten_seconds(catalog):
    specs = matrix.batch("T3", 0, 5, catalog=catalog)
    t = time.perf_counter()
    for s in specs:
        rec = runner.run_spec(s, catalog, exports=True)
        assert rec["n_checks"] > 20
    assert time.perf_counter() - t < 10


def test_findings_dedupe_by_fid(tmp_path, catalog):
    spec = matrix.generate("T3", 0, catalog=catalog)[0]
    other = matrix.generate("T3", 0, catalog=catalog)[1]
    r = {"check": "HP", "expected": 1, "actual": 2, "cite": "x", "known_gap": None}
    out = tmp_path / "f.jsonl"
    assert runner.write_findings(out, [runner.finding(r, spec)]) == {"new": 1, "merged": 0, "total": 1}
    assert runner.write_findings(out, [runner.finding(r, spec)])["total"] == 1  # same spec again: no inflation
    spec2 = copy.deepcopy(spec)
    spec2.id = "another"
    s = runner.write_findings(out, [runner.finding(r, spec2)])
    assert s["total"] == 1
    rec = json.loads(out.read_text().splitlines()[0])
    assert rec["occurrences"] == 2 and set(rec) >= {"fid", "spec", "rule", "severity", "expected", "actual", "source", "known_gap"}
    r2 = dict(r, check="PB")
    assert runner.write_findings(out, [runner.finding(r2, spec)])["total"] == 2
    assert runner.severity("HP") == "S1" and runner.severity("FEATURES-PRESENT") == "S2" and runner.severity("W-PERF") == "S3"
    del other


def test_known_gap_tags(catalog):
    gaps = runner.load_known_gaps()
    wl = CharSpec(id="k", classes=[["warlock", 5, None]])
    assert runner.known_gap({"check": "ATTACKS-PER-ACTION", "expected": 1, "actual": 2}, wl, gaps) == "KG-thirsting-blade-count"
    assert runner.known_gap({"check": "ATTACKS-PER-ACTION", "expected": 1, "actual": 2}, CharSpec(id="k2"), gaps) is None
    assert runner.known_gap({"check": "HP", "expected": 1, "actual": 2}, wl, gaps) is None


def test_cli_run_writes_findings_and_marks_known_gaps(tmp_path, capsys, catalog):
    out = tmp_path / "campaign" / "findings.jsonl"
    cli.main(["run", "--tier", "T4", "--size", "3", "--no-exports", "--out", str(out)])
    text = capsys.readouterr().out
    assert "unexplained failures:" in text and text.count("t4-00") == 3
    cli.main(["gen", "--tier", "T3", "--size", "2"])
    lines = capsys.readouterr().out.strip().splitlines()
    assert [CharSpec.from_json(l).id for l in lines] == [s.id for s in matrix.batch("T3", 0, 2, catalog=catalog)]
    cli.main(["explain", "t4-000", "HP"])
    assert "expected" in capsys.readouterr().out
    cli.main(["show", "t4-000"])
    assert "abilities:" in capsys.readouterr().out


def test_weird_generator_is_deterministic_and_never_crashes_the_runner(catalog):
    a = [s.to_json() for s in weird.generate(1, 18)]
    assert a == [s.to_json() for s in weird.generate(1, 18)]
    for s in weird.generate(1, 18):
        rec = runner.run_spec(s, catalog, exports=False)
        assert rec["id"] == s.id and isinstance(rec["results"], list)


def test_detectors_flag_a_broken_resolution(samples, catalog):
    from engine.resolve import resolve
    draft, res = samples["fighter20"]
    spec = GOOD["fighter20"]
    assert [r for r in weird.detect(spec, draft, res, resolve, catalog, exports=True) if not r["ok"]] == []
    bad = copy.deepcopy(res)
    bad["derived"]["hitPointMax"] = -4
    bad["problems"].append({"id": "x", "message": "x"})
    bad["choices"].append({**bad["choices"][0], "status": "pending"})
    failed = {r["check"] for r in weird.detect(spec, draft, bad, None, None, exports=False) if not r["ok"]}
    assert {"W-NUMBERS", "W-PROBLEMS", "W-PENDING", "W-DUP-IDS"} <= failed


def test_the_harness_does_not_touch_the_golden_baselines():
    golden = pathlib.Path(__file__).parent / "golden"
    src = "".join(p.read_text(encoding="utf-8") for p in pathlib.Path(checks.__file__).parent.glob("*.py"))
    assert "golden" not in src.replace("never touches golden", "")
    assert golden.exists()
