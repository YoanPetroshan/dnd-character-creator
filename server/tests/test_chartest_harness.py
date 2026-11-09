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
    "CARRY": ("fighter20", _bump(["derived", "carryingCapacity", "capacity"], 15)),
    "LANGUAGES": ("fighter20", lambda d, r: r["sheet"]["proficiencies"]["languages"].remove("common")),
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


# ---------------------------------------------------------------- VC T3 campaign: oracle / harness fixes
def _run(token, catalog, exports=False):
    spec = runner.find_spec(token, catalog)[0]
    return runner.run_spec(spec, catalog, exports=exports, gaps=[])


def _failed(rec):
    return {r["check"] for r in rec["results"]}


@pytest.mark.parametrize("feat,bonus", [
    ("Mark of Passage", 5), ("Transmuted Anatomy", 5), ("Squat Nimbleness", 5), ("Speedy", 10), ("Mobile", 10),
    ("Charger", 0), ("Alert", 0), ("Boon of Speed", 0),
])
def test_feat_speed_bonus_reads_the_feat_text(feat, bonus):
    assert checks.feat_speed_bonus(feat, "2024" if feat in ("Speedy", "Charger", "Alert", "Boon of Speed") else "2014") == bonus


def test_speed_check_counts_a_speed_feat_and_still_catches_a_wrong_speed(catalog):
    rec = _run("t3-041-arcane-trickster-levels-13-2024", catalog)  # Elf (Zendikar) 30 + Transmuted Anatomy 5
    assert "SPEED" not in _failed(rec) and rec["res"]["derived"]["speed"] == 35
    d, res = rec["draft"], copy.deepcopy(rec["res"])
    res["derived"]["speed"] = 30
    assert "SPEED" in {r["check"] for r in checks.run_checks(d, res) if not r["ok"]}


def test_heavy_armor_specs_really_wear_plate_armor(catalog):
    assert any(i["itemId"] == "plate-armor" for s in matrix.generate("T3", 0, 64) for i in s.equip)
    assert not any(i["itemId"] == "plate" for s in matrix.generate("T3", 0, 64) for i in s.equip)
    rec = _run("t3-046-heavy-armor-under-str-2024", catalog)  # STR 8 in plate (STR 15): AC 18, Deep Gnome 20 + 5 - 10
    assert rec["res"]["derived"]["armorClass"] == 18 and rec["res"]["derived"]["speed"] == 15
    assert _failed(rec) == set()


def test_ac_check_counts_armor_of_shadows(catalog):
    assert "AC" not in _failed(_run("t2-007-sor10-war10-2014", catalog))  # Warlock 10, Armor of Shadows: 13 + DEX
    assert "AC" not in _failed(_run("t2-008-sor19-war1-2024", catalog))


def test_thaumaturge_cantrip_goes_to_the_cleric_only(catalog):
    assert "CANTRIPS" not in _failed(_run("t2-046-cle3-dru2-2024", catalog))  # Thaumaturge Cleric 3 + plain Druid 2


def test_mc_prof_explains_protector_and_psa_domain_heavy_armor(catalog):
    for token in ("t2-076-bar19-cle1-2024", "t2-074-cle2-pal3-2014", "t2-108-cle19-bar1-2014"):
        assert "MC-PROF" not in _failed(_run(token, catalog)), token


def test_skills_check_rejects_a_non_skill_id_but_allows_tool_expertise(samples):
    d, res = samples["fighter20"]
    bad = copy.deepcopy(res)
    bad["sheet"]["proficiencies"]["skills"].append("skill-empowerment")
    assert "SKILLS" in {r["check"] for r in checks.run_checks(d, bad) if not r["ok"]}
    ok = copy.deepcopy(res)
    ok["sheet"]["expertiseSkills"] = [*ok["sheet"].get("expertiseSkills", []), "thieves-tools"]
    assert "SKILLS" not in {r["check"] for r in checks.run_checks(d, ok) if not r["ok"]}


def test_pruned_detector_ignores_stale_filler_picks_and_cap_notes_but_reports_a_persistent_prune(catalog):
    from engine.resolve import resolve
    assert "W-PRUNED" not in _failed(_run("t1-065-fig2-2024", catalog))   # Kobold skill pick vs Draconic Sorcery variant
    assert "W-PRUNED" not in _failed(_run("t3-044-feat-asi-caps-2024", catalog))  # "STR is already at maximum (20)"
    spec = runner.find_spec("t1-065-fig2-2024", catalog)[0]
    draft, res = S.resolve_spec(spec, catalog, resolve)
    assert res["pruned"] and "choiceId" in res["pruned"][0]
    persistent = lambda d, c: {"pruned": res["pruned"]}  # noqa: E731  (the prune survives removing the pick: an engine defect)
    out = [r for r in weird.detect(spec, draft, res, persistent, catalog, exports=False) if r["check"] == "W-PRUNED"][0]
    assert not out["ok"] and "no longer applies" in json.dumps(out["actual"]) and "None" not in json.dumps(out["actual"])


def test_numbers_detector_survives_a_missing_speed(samples, catalog):
    draft, res = samples["fighter20"]
    spec = GOOD["fighter20"]
    none_speed = copy.deepcopy(res)
    none_speed["derived"]["speed"] = None
    out = {r["check"]: r for r in weird.detect(spec, draft, none_speed, None, None, exports=False)}
    assert not out["W-NUMBERS"]["ok"]  # reported, not a TypeError
    none_speed["problems"].append({"id": "unknown-species", "message": "x"})
    out = {r["check"]: r for r in weird.detect(spec, draft, none_speed, None, None, exports=False)}
    assert out["W-NUMBERS"]["ok"]  # an unknown species has no speed to report


def test_the_unknown_species_weird_spec_no_longer_crashes_the_detector(catalog):
    spec = [s for s in weird.generate(0, 50) if "swap_species" in s.weird][0]
    rec = runner.run_spec(spec, catalog, exports=False)
    assert "W-EXC" not in _failed(rec)


def test_w9_filter_drops_only_the_verified_non_defects():
    res = {"sheet": {"name": "Hero \U0001f409"}}
    fails = ["sheet.startingGold = 0 missing from the Markdown", "sheet.startingGold = 5 missing from the PDF",
             "sheet.name = 'Hero \U0001f409' missing from the PDF", "sheet.name = 'Hero \U0001f409' missing from the Markdown",
             "derived.classResources.[].details.damageTypes = 'Cold' missing from the Markdown"]
    assert weird._w9_unexplained(fails, res) == fails[1:2] + fails[3:]


def test_rewarded_ruined_feat_options_leaf_is_a_tagged_known_gap():
    gaps = runner.load_known_gaps()
    r = {"check": "W-W9", "expected": "x", "actual": ["sheet.featOptions.[] = 'lucky' missing from the Markdown"]}
    assert runner.known_gap(r, CharSpec(id="k"), gaps) == "KG-bmt-feat-options"
    r["actual"] = ["sheet.proficiencies.skills.[] = 'skill-empowerment' missing from the Markdown"]
    assert runner.known_gap(r, CharSpec(id="k"), gaps) is None


# ---------------------------------------------------------------- VC T2/T4 campaign: AC oracle (species natural armor, College of Dance)
def _spec_json(base_token, catalog, **changes):
    d = json.loads(runner.find_spec(base_token, catalog)[0].to_json())
    d.update(changes)
    return json.dumps(d)


@pytest.mark.parametrize("name,source,formulas,flat", [
    ("Lizardfolk", "MPMM", {"natural-or-armor": (13, "DEX")}, 0),
    ("Lizardfolk", "DMG", {}, 3),
    ("Locathah", "LR", {"natural-or-armor": (12, "DEX")}, 0),
    ("Loxodon", "GGR", {"natural-or-armor": (12, "CON")}, 0),
    ("Autognome", "AAG", {"natural": (13, "DEX")}, 0),
    ("Thri-kreen", "AAG", {"natural": (13, "DEX")}, 0),
    ("Tortle", "MPMM", {"natural": (17, None)}, 0),    # Shell Defense (+4 in the shell) is not a standing bonus
    ("Warforged", "ERLW", {}, 1),
    ("Warforged", "EFA", {}, 1),                      # `+1 bonus to your {@variantrule Armor Class|XPHB}`: the tag is stripped
    ("Troglodyte", "DMG", {}, 1),
    ("Human", "PHB", {}, 0),
])
def test_species_armor_reads_the_trait_text(name, source, formulas, flat):
    race = next(r for r in checks.raw_races()["race"] if r["name"] == name and r["source"] == source)
    assert checks.species_armor(race) == (formulas, flat)


def test_ac_check_expects_the_species_natural_armor_and_the_flat_bonus(catalog):
    from engine.resolve import resolve
    # Wizard 1 with no armor: expected = formula(DEX modifier read from the resolved sheet)
    cases = {"lizardfolk-mpmm": lambda dex, con: 13 + dex, "tortle-mpmm": lambda dex, con: 17,
             "warforged-erlw": lambda dex, con: 11 + dex, "human": lambda dex, con: 10 + dex}
    for species, formula in cases.items():
        tok = _spec_json("t2-044-fig1-pal19-2014", catalog, id="ac-" + species, species=species, subspecies=None,
                         classes=[["wizard", 1, None]],
                         abilities={"method": "manual", "base": {"STR": 14, "DEX": 15, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}, "priority": []})
        spec = runner.find_spec(tok, catalog)[0]
        d, res = S.resolve_spec(spec, catalog, resolve)
        right, wrong = copy.deepcopy(res), copy.deepcopy(res)
        ab = res["sheet"]["abilities"]
        ac = formula((ab["DEX"] - 10) // 2, (ab["CON"] - 10) // 2)
        right["derived"]["armorClass"], wrong["derived"]["armorClass"] = ac, ac - 1
        assert "AC" not in {r["check"] for r in checks.run_checks(d, right) if not r["ok"]}, species
        assert "AC" in {r["check"] for r in checks.run_checks(d, wrong) if not r["ok"]}, species


def test_ac_check_expects_college_of_dance_unarmored_defense_and_tags_the_known_gap_outside_2024(catalog):
    rec = _run(_spec_json("t2-054-bar4-pal3-mixed", catalog, id="dance-2024", ruleset="2024"), catalog)
    assert rec["res"]["derived"]["armorClass"] == 12  # DEX 11 (+0), CHA 14 (+2): 10 + 0 + 2, no armor in the 2024 bard kit
    assert "AC" not in _failed(rec)
    wrong = copy.deepcopy(rec["res"])
    wrong["derived"]["armorClass"] = 10
    assert "AC" in {r["check"] for r in checks.run_checks(rec["draft"], wrong) if not r["ok"]}
    gaps = runner.load_known_gaps()
    result = {"check": "AC", "expected": "12", "actual": 10}
    for sub, rs, tag in [("dance-xphb", "mixed", "KG-xphb-effects-2024-only"), ("draconic-xphb", "2014", "KG-xphb-effects-2024-only"),
                         ("dance-xphb", "2024", None), ("draconic-xphb", "2024", None)]:
        cls = [("bard", 4, sub)] if "dance" in sub else [("sorcerer", 3, sub)]
        spec = CharSpec(id="x", ruleset=rs, classes=cls)
        assert runner.known_gap(result, spec, gaps) == tag, (sub, rs)


# ---------------------------------------------------------------- VC T2 b9-14 / T1 b0-6: initiative (Hare-Trigger), carrying capacity (Powerful Build), species languages
def _species_sample(catalog, species, ruleset="2014", wiz_base=None, **changes):
    from engine.resolve import resolve
    base = wiz_base or {"STR": 16, "DEX": 15, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    tok = _spec_json("t2-044-fig1-pal19-2014", catalog, id="vc-" + species, species=species, subspecies=None, ruleset=ruleset,
                     classes=[["wizard", 1, None]], abilities={"method": "manual", "base": base, "priority": []}, **changes)
    spec = runner.find_spec(tok, catalog)[0]
    return S.resolve_spec(spec, catalog, resolve)


def _rules_failing(draft, res):
    return {r["check"] for r in checks.run_checks(draft, res) if not r["ok"]}


def test_initiative_check_requires_the_harengon_hare_trigger_bonus(catalog):
    d, res = _species_sample(catalog, "harengon-mpmm")
    dex, pb = res["derived"]["abilityModifiers"]["DEX"], res["derived"]["proficiencyBonus"]
    right, wrong = copy.deepcopy(res), copy.deepcopy(res)
    right["derived"]["initiative"], wrong["derived"]["initiative"] = dex + pb, dex
    assert "INITIATIVE" not in _rules_failing(d, right)
    assert "INITIATIVE" in _rules_failing(d, wrong)
    d2, res2 = _species_sample(catalog, "human")
    assert res2["derived"]["initiative"] == res2["derived"]["abilityModifiers"]["DEX"]
    assert "INITIATIVE" not in _rules_failing(d2, res2)


@pytest.mark.parametrize("species,factor", [("orc-mpmm", 2), ("firbolg-vgm", 2), ("human", 1)])
def test_carry_check_doubles_the_capacity_for_powerful_build(catalog, species, factor):
    d, res = _species_sample(catalog, species)
    cap = res["sheet"]["abilities"]["STR"] * 15 * factor
    right, wrong = copy.deepcopy(res), copy.deepcopy(res)
    right["derived"]["carryingCapacity"].update(capacity=cap, pushDragLift=cap * 2)
    wrong["derived"]["carryingCapacity"].update(capacity=cap // factor if factor > 1 else cap + 15, pushDragLift=cap * 2)
    assert "CARRY" not in _rules_failing(d, right), species
    assert "CARRY" in _rules_failing(d, wrong), species


def test_languages_check_wants_the_fixed_species_languages_outside_2024(catalog):
    d, res = _species_sample(catalog, "tiefling-phb")
    right, wrong = copy.deepcopy(res), copy.deepcopy(res)
    right["sheet"]["proficiencies"]["languages"] = ["common", "infernal"]
    wrong["sheet"]["proficiencies"]["languages"] = ["common"]
    assert "LANGUAGES" not in _rules_failing(d, right)
    hit = [r for r in checks.run_checks(d, wrong) if r["check"] == "LANGUAGES" and not r["ok"]]
    assert hit and hit[0]["actual"]["missing"] == ["infernal"]
    d24, res24 = _species_sample(catalog, "tiefling-phb", ruleset="2024")
    res24["sheet"]["proficiencies"]["languages"] = ["common"]
    assert "LANGUAGES" not in _rules_failing(d24, res24)


# ---------------------------------------------------------------- VC T1 b7-17: oracle fixes after VF2 (Goliath carrying weight, Warforged EFA +1, Tortle armor)
def test_carry_check_reads_the_mpmm_goliath_carrying_weight_wording(catalog):
    race = next(r for r in checks.raw_races()["race"] if r["name"] == "Goliath" and r["source"] == "MPMM")
    assert checks._ONE_SIZE_LARGER_RE.search(json.dumps(race["entries"]))
    d, res = _species_sample(catalog, "goliath-mpmm")
    cap = res["sheet"]["abilities"]["STR"] * 15 * 2
    right, wrong = copy.deepcopy(res), copy.deepcopy(res)
    right["derived"]["carryingCapacity"].update(capacity=cap, pushDragLift=cap * 2)
    wrong["derived"]["carryingCapacity"].update(capacity=cap // 2, pushDragLift=cap)
    assert "CARRY" not in _rules_failing(d, right)
    assert "CARRY" in _rules_failing(d, wrong)


def test_ac_check_expects_the_warforged_efa_tagged_bonus_and_the_tortle_ignoring_armor(catalog):
    from engine.resolve import resolve
    assert checks.species_ignores_armor(next(r for r in checks.raw_races()["race"] if r["name"] == "Tortle" and r["source"] == "MPMM"))
    assert checks.species_ignores_armor(next(r for r in checks.raw_races()["race"] if r["name"] == "Tortle" and r["source"] == "TTP"))
    assert not checks.species_ignores_armor(next(r for r in checks.raw_races()["race"] if r["name"] == "Warforged" and r["source"] == "ERLW"))
    for species, ruleset in [("tortle-mpmm", "2014"), ("warforged-efa", "2024")]:
        tok = _spec_json("t2-044-fig1-pal19-2014", catalog, id="ac-" + species, species=species, subspecies=None, ruleset=ruleset,
                         classes=[["fighter", 1, None]],
                         abilities={"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}, "priority": []},
                         equip=[{"itemId": "chain-mail", "qty": 1, "equipped": True}])
        spec = runner.find_spec(tok, catalog)[0]
        d, res = S.resolve_spec(spec, catalog, resolve)
        # the engine's own number for the two real characters must satisfy the oracle (it did not before the fix)
        assert "AC" not in _rules_failing(d, res), (species, res["derived"]["armorClass"])
        wrong = copy.deepcopy(res)
        wrong["derived"]["armorClass"] += 1
        assert "AC" in _rules_failing(d, wrong), species


def test_ac_check_uses_the_xphb_draconic_sorcery_formula_for_the_real_subclass_id(catalog):
    # the XPHB subclass is `draconic-xphb` (name "Draconic Sorcery"), the PHB one `draconic`: 10 + DEX + CHA vs 13 + DEX
    for ruleset, sub, formula in [("2024", "draconic-xphb", lambda dex, cha: 10 + dex + cha), ("2014", "draconic", lambda dex, cha: 13 + dex)]:
        rec = _run(_spec_json("t1-145-sor3-mixed", catalog, id="drac-" + ruleset, ruleset=ruleset, classes=[["sorcerer", 3, sub]]), catalog)
        mods = rec["res"]["derived"]["abilityModifiers"]
        exp = formula(mods["DEX"], mods["CHA"])
        right, wrong = copy.deepcopy(rec["res"]), copy.deepcopy(rec["res"])
        right["derived"]["armorClass"], wrong["derived"]["armorClass"] = exp, exp - 1
        assert "AC" not in _rules_failing(rec["draft"], right), (ruleset, sub)
        assert "AC" in _rules_failing(rec["draft"], wrong), (ruleset, sub)
    # mixed: the engine applies no XPHB effects (11 instead of 13), tagged KG-xphb-effects-2024-only
    rec = _run(_spec_json("t1-145-sor3-mixed", catalog, id="drac-mixed"), catalog)
    hit = [r for r in rec["results"] if r["check"] == "AC"]
    assert hit and runner.known_gap(hit[0], rec["spec"], runner.load_known_gaps()) == "KG-xphb-effects-2024-only"
