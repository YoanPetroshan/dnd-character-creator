"""F0: golden guard that `mixed` and `2014` resolve() output never changes during the 2024 stages.

The 2024 chassis series (C6b ... C9b) may only change behaviour under ``ruleset == "2024"``.
This file pins ~230 fully filled drafts, each resolved under ``mixed`` and ``2014`` (never 2024):

- the 12 SRD classes at levels 1, 3, 11 and 20 (first SRD subclass from level 3), every pending
  choice auto-filled with the kitchen-sink "first option" filler, under ``sources`` ``[]`` and
  ``["srd"]``;
- five multiclass drafts (Wizard 1 / Fighter 1, Rogue 3 / Bard 2, Warlock 5 / Sorcerer 3,
  Cleric 1 / Druid 1, Barbarian 3 / Monk 2);
- every non-2024 kitchen-sink entry (own ruleset), under both ``sources`` values.

The golden file stores the FILLED DRAFT next to its resolve() result, so a later change to the
filler or to the set of pending cards cannot move the input. The test compares the freshly
resolved result with the stored one after a JSON round trip (exact equality).

Deliberate change: a later slice may add an explicitly listed additive key to ``STRIP`` (a
mapping of dotted paths, see ``strip``). Any other difference fails. To regenerate the golden
on purpose (only after the user agreed that mixed/2014 output may change), run from ``server/``:

    ../.venv/bin/python tests/test_c_series_golden.py --regenerate

FE12 appended the feat-holding kitchen-sink cases with ``--append`` (existing cases asserted unchanged and rewritten
byte for byte; only the new names are added). Use ``--append`` for any later addition.

REBASELINE MODE (RP6 / P0). A slice that deliberately changes mixed / 2014 output (the E11 slices and the
RPX extras) must not use ``--regenerate``. It adds an entry to ``REBASELINES`` (append-only, empty today):

    REBASELINES["RP7"] = {"cases": ["mixed/*/monk*", "2014/*/monk*"],      # fnmatch over case names
                          "paths": [r"^result[.]choices[[]class:monk:1:prof-choice-1[]]"],  # regexes over paths
                          "why": "SRD Monk tool or instrument choice"}

The ``paths`` allowlist is written from the slice's rule matrix, never copied from the dry-run output. Then, from
``server/``:

    ../.venv/bin/python tests/test_c_series_golden.py --rebaseline RP7 --dry-run   # prints the diff, writes nothing
    ../.venv/bin/python tests/test_c_series_golden.py --rebaseline RP7             # writes the gz, prints the summary

Cases NOT matching ``cases`` must re-resolve to their stored result (written back unchanged). For matching cases
``ks.fill`` fills only the cards that are now ``pending`` (existing picks stay), the draft is re-resolved, and
``{draft, result}`` old vs new is diffed on normalized paths: lists of dicts that all carry a unique ``id`` become dicts
keyed by id (path ``result.choices[<id>].options[<id>]``), so an inserted card does not shift every index. Every changed
path must match a ``paths`` regex or the run fails; a matching case with no diff prints a warning (pattern too wide).
Cases are never deleted (new ones come only through ``--append``). Paste the printed summary into the slice's
ARCHITECTURE section and name the rebaseline in the commit message. ``STRIP`` is applied to both sides of the compare.

The file was first written from the engine at commit 81fce17 (before any C-series work). The
whole module skips when the local 5etools data (classes, official, spells) is absent.
"""
from __future__ import annotations

import copy
import fnmatch
import gzip
import json
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from catalog import official_source as official  # noqa: E402
from catalog.loader import load  # noqa: E402
from engine.resolve import resolve  # noqa: E402
import kitchen_sink as ks  # noqa: E402

GOLDEN = pathlib.Path(__file__).parent / "golden" / "c_series_mixed_2014_baseline.json.gz"

CLASSES = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger",
           "rogue", "sorcerer", "warlock", "wizard"]
LEVELS = (1, 3, 11, 20)
RULESETS = ("mixed", "2014")
SOURCES = ([], ["srd"])
MULTICLASS = {
    "wizard1-fighter1": [("wizard", 1), ("fighter", 1)],
    "rogue3-bard2": [("rogue", 3), ("bard", 2)],
    "warlock5-sorcerer3": [("warlock", 5), ("sorcerer", 3)],
    "cleric1-druid1": [("cleric", 1), ("druid", 1)],
    "barbarian3-monk2": [("barbarian", 3), ("monk", 2)],
}

# Additive keys a later slice may legitimately add under mixed/2014: dotted paths, "[]" = every
# list element. Empty on purpose; adding to it needs the user's agreement and a note here.
# "derived.featResources": FE3 additive key (feat resources, e.g. Lucky), always [] for the feat-less golden
# drafts; user-approved feat-effects series (decision F-D1). Both sides are stripped, nothing else changes.
STRIP: tuple[str, ...] = ("derived.featResources",)

# RP6 / P0: append-only record of deliberate mixed / 2014 changes, see the module docstring. slice id ->
# {"cases": [fnmatch over case names], "paths": [regexes over normalized paths], "why": one line}. Empty on purpose.
REBASELINES: dict[str, dict] = {
    # RP7 / E11c: the SRD Monk "one type of artisan's tools or one musical instrument" is now a card (the nested
    # choice is flattened), so the primary-Monk cases gain the card, the filler's first-option pick, and that tool in
    # the proficiencies. The multiclass Barbarian 3 / Monk 2 (Monk is secondary) must not move.
    "RP7": {
        "cases": ["*/src-*/monk[0-9]*", "ks/src-*/monk14"],
        "paths": [
            r"^result\.choices\[class:monk:1:prof-choice-1\]$",            # the new card, reported once at its root
            r"^draft\.classes\[0\]\.choices\.class:monk:1:prof-choice-1$",   # the filler's pick, in the draft (Monk first)
            r"^result\.sheet\.proficiencies\.tools$",                      # the picked tool
        ],
        "why": "SRD Monk tool or instrument choice (E11c)",
    },
    # RPF: PHB "you can't gain the same proficiency twice": the later of two ordinary skill pick cards loses a
    # duplicate. Only the golden's multiclass Rogue 3 / Bard 2 holds one (the Bard multiclass skill card, entered
    # second, was filled with Acrobatics like the Rogue's card). The filler re-picks the first enabled skill
    # (Animal Handling), so: the Bard multiclass card (options disabled "already proficient", the new pick, the draft
    # pick), the skill list, the new skill's modifier and its option in the Rogue's expertise card (a skill that
    # is now proficient becomes eligible for Expertise) move, nothing else.
    "RPF": {
        "cases": ["*/src-*/multi-rogue3-bard2"],
        "paths": [
            r"^draft\.classes\[1\]\.choices\.class:bard:multiclass-prof-choice-0\[0\]$",   # the filler's new pick
            r"^result\.choices\[class:bard:multiclass-prof-choice-0\]",                       # options disabled, selected
            r"^result\.choices\[class:rogue:1:expertise-choice:rogue-expertise-1\]\.options\[skill-animal-handling\]\.(disabled|disabledReason)$",
            r"^result\.sheet\.proficiencies\.skills$",                                         # the replacement skill
            r"^result\.derived\.skills\.skill-animal-handling$",                                # its modifier
        ],
        "why": "duplicate skill pick between ordinary class cards (RPF)",
    },
    # RP15 / E11b: the SRD Wizard Spell Mastery (18) and Signature Spell (20) are cards under mixed and 2014 (same cids
    # as 2024). Only the Wizard 20 cases hold them. Rule matrix: the three new cards; the filler's picks in the
    # draft; sheet.spells[wizard].spellMastery / signatureSpells / alwaysPrepared (signature picks are always
    # prepared; Spell Mastery is not); the resource wizard:signature-spells; the Spell Mastery / Signature Spell
    # sheet.features rows' picked names; the prepared card's disabled flags (always-prepared signature picks).
    "RP15": {
        "cases": ["*/src-*/wizard20"],
        "paths": [
            r"^result\.choices\[class:wizard:18:spell-mastery-[12]\]$",           # the new cards, reported once at the root
            r"^result\.choices\[class:wizard:20:signature-spells\]$",
            r"^draft\.classes\[0\]\.choices\.class:wizard:(18:spell-mastery-[12]|20:signature-spells)$",  # filler picks
            r"^result\.sheet\.spells\[\d+\]\.(spellMastery|signatureSpells|alwaysPrepared)$",
            r"^result\.derived\.classResources\[wizard:signature-spells\]$",
            r"^result\.sheet\.features\[\d+\]\.choice$",                          # the two rows' picked spell names
            r"^result\.choices\[class:wizard:spells-known\]\.options\[[^\]]+\]\.(disabled|disabledReason)$",
        ],
        "why": "SRD Wizard Spell Mastery / Signature Spell cards (E11b)",
    },
    # RP16 / E11a: SRD Bard Magical Secrets (10 / 14 / 18). The Bard known-spells card also offers every other class's
    # spells up to the highest slot level plus their cantrips, labelled "(Magical Secrets)", and its description names
    # the cap. Only the Bard 11 and 20 cases hold the feature (Bard 1 / 3 are below 10; the multiclass Bard is 2).
    # Rule matrix: the added options (reported once at their roots), a changed option's label / group / disabled flag,
    # the description. The stored picks (the old list's first spells), the count, the selection and every other card
    # stay as they are.
    "RP16": {
        "cases": ["*/src-*/bard11", "*/src-*/bard20"],
        "paths": [
            r"^result\.choices\[class:bard:spells-known\]\.options\[[^\]]+\]$",       # an added option, at its root
            r"^result\.choices\[class:bard:spells-known\]\.options\[[^\]]+\]\.(label|group|disabled|disabledReason)$",
            r"^result\.choices\[class:bard:spells-known\]\.description$",
        ],
        "why": "SRD Bard Magical Secrets (E11a)",
    },
}

_NEEDS_DATA = [m for m, ok in (("classes", official.has_official_classes), ("official", official.has_official),
                               ("spells", official.has_official_spells)) if not ok()]


def strip(res: dict) -> dict:
    res = copy.deepcopy(res)
    for path in STRIP:
        _strip(res, path.split("."))
    return res


def _strip(node, parts):
    head, rest = parts[0], parts[1:]
    if head == "[]":
        for x in node:
            _strip(x, rest) if rest else None
        return
    if not isinstance(node, dict) or head not in node:
        return
    if rest:
        _strip(node[head], rest)
    else:
        del node[head]


def _subclass(catalog, cls):
    for sid, s in catalog.subclasses.items():
        if s["class"]["index"] == cls and s.get("source") == "SRD":
            return sid
    return None


def _draft(catalog, classes, ruleset, sources):
    out = []
    for cid, lvl in classes:
        c = {"classId": cid, "level": lvl, "choices": {}}
        sub = _subclass(catalog, cid) if lvl >= 3 else None
        if sub:
            c["subclassId"] = sub
        out.append(c)
    return {"name": "golden", "ruleset": ruleset, "sources": list(sources),
            "abilities": {"method": "manual", "base": dict(ks._BASE)},
            "species": {"id": "human", "choices": {}}, "background": {"id": "acolyte", "choices": {}},
            "equipment": {"choices": {}, "added": [], "skipped": False}, "classes": out}


def _label(sources):
    return "src-" + ("all" if not sources else "srd")


def case_drafts(catalog) -> dict[str, dict]:
    """name -> filled draft (unfilled here; `fill` runs in regenerate)."""
    cases = {}
    for rs in RULESETS:
        for src in SOURCES:
            for cid in CLASSES:
                for lvl in LEVELS:
                    cases[f"{rs}/{_label(src)}/{cid}{lvl}"] = (_draft(catalog, [(cid, lvl)], rs, src), {})
            for name, cl in MULTICLASS.items():
                cases[f"{rs}/{_label(src)}/multi-{name}"] = (_draft(catalog, cl, rs, src), {})
    for sid, spec in ks.KITCHEN_SINK.items():
        if spec["ruleset"] == "2024":
            continue
        # FE12: feat-holding drafts are added once, under `sources` [] (a "srd" filter would hide the feat picks)
        for src in (([],) if spec.get("feats") else SOURCES):
            d = ks.base_draft(spec)
            d["sources"] = list(src)
            cases[f"ks/{_label(src)}/{sid}"] = (d, spec["overrides"])
    return cases


def regenerate() -> None:
    catalog = load()
    out = {}
    for name, (draft, overrides) in case_drafts(catalog).items():
        spec = ks.KITCHEN_SINK.get(name.rsplit("/", 1)[-1]) if name.startswith("ks/") else None
        if spec and ks.skip_reason(spec):
            continue
        filled = ks.fill(draft, catalog, overrides, resolve)
        out[name] = {"draft": filled, "result": json.loads(json.dumps(resolve(filled, catalog)))}
    GOLDEN.parent.mkdir(exist_ok=True)
    with gzip.open(GOLDEN, "wt", compresslevel=9) as f:
        json.dump(out, f, sort_keys=True, separators=(",", ":"))
    print(f"wrote {len(out)} cases, {GOLDEN.stat().st_size} bytes")


def append_new_cases() -> None:
    """FE12: add only the cases the golden does not hold yet (the feat-holding kitchen-sink drafts).

    Every existing entry is asserted unchanged first: its stored filled draft and (stripped) result must equal a fresh
    resolve, and it is written back byte for byte. Nothing else in the file may move."""
    catalog = load()
    old = json.load(gzip.open(GOLDEN, "rt"))
    before = {name: json.dumps(entry, sort_keys=True, separators=(",", ":")) for name, entry in old.items()}
    for name, entry in old.items():
        now = strip(json.loads(json.dumps(resolve(copy.deepcopy(entry["draft"]), catalog))))
        assert now == strip(entry["result"]), f"existing golden case changed: {name}"
    added = []
    for name, (draft, overrides) in case_drafts(catalog).items():
        if name in old:
            continue
        spec = ks.KITCHEN_SINK.get(name.rsplit("/", 1)[-1]) if name.startswith("ks/") else None
        if spec and ks.skip_reason(spec):
            continue
        filled = ks.fill(draft, catalog, overrides, resolve)
        old[name] = {"draft": filled, "result": json.loads(json.dumps(resolve(filled, catalog)))}
        added.append(name)
    for name, text in before.items():
        assert json.dumps(old[name], sort_keys=True, separators=(",", ":")) == text, name
    with gzip.open(GOLDEN, "wt", compresslevel=9) as f:
        json.dump(old, f, sort_keys=True, separators=(",", ":"))
    print(f"kept {len(before)} existing cases unchanged, added {len(added)}: {added}")


class RebaselineError(AssertionError):
    """A rebaseline broke its allowlist (or an unmatched case moved)."""


def _keyed(node):
    """Normalize: lists of dicts that each carry a unique string `id` become dicts keyed by it."""
    if isinstance(node, dict):
        return {k: _keyed(v) for k, v in node.items()}
    if isinstance(node, list):
        if node and all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in node):
            ids = [x["id"] for x in node]
            if len(set(ids)) == len(ids):
                return {_KeyedId(x["id"]): _keyed(x) for x in node}
        return [_keyed(x) for x in node]
    return node


class _KeyedId(str):
    """A dict key that came from an `id` (rendered `[id]` in paths, not `.id`)."""


def _join(path: str, key) -> str:
    return f"{path}[{key}]" if isinstance(key, _KeyedId) else f"{path}.{key}" if path else str(key)


def diff_paths(old, new, path: str = "") -> list[str]:
    """Dotted paths where `old` and `new` differ (an added / removed subtree is reported once, at its root)."""
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for k in sorted(set(old) | set(new), key=str):
            sub = _join(path, k)
            if k not in old or k not in new:
                out.append(sub)
            else:
                out += diff_paths(old[k], new[k], sub)
        return out
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        out = []
        for i, (a, b) in enumerate(zip(old, new)):
            out += diff_paths(a, b, f"{path}[{i}]")
        return out
    return [] if old == new else [path]


def _norm(entry: dict) -> dict:
    return _keyed({"draft": entry["draft"], "result": strip(entry["result"])})


def _write_golden(data: dict) -> None:
    with gzip.open(GOLDEN, "wt", compresslevel=9) as f:
        json.dump(data, f, sort_keys=True, separators=(",", ":"))


def rebaseline(slice_id: str, *, dry_run: bool = False, catalog=None, rebaselines: dict | None = None,
               resolver=None, filler=None, overrides_for=None, out=print) -> dict:
    """RP6 / P0: re-resolve the golden under a slice's allowlist (see the module docstring).

    Returns {"changed": {case: [paths]}, "violations": {case: [paths]}, "warnings": [case], "counts": {regex: n}}.
    Outside `dry_run` a violation raises `RebaselineError` before anything is written."""
    table = REBASELINES if rebaselines is None else rebaselines
    if slice_id not in table:
        raise KeyError(f"unknown rebaseline slice {slice_id!r}: add it to REBASELINES first")
    spec = table[slice_id]
    patterns, allowed = spec["cases"], [re.compile(p) for p in spec["paths"]]
    resolver = resolver or resolve
    filler = filler or ks.fill
    if catalog is None:
        catalog = load()
    if overrides_for is None:
        drafts = case_drafts(catalog)
        overrides_for = lambda name: drafts[name][1] if name in drafts else {}  # noqa: E731
    old = _load_golden()
    new, changed, violations, warnings = {}, {}, {}, []
    counts = {p.pattern: 0 for p in allowed}
    for name, entry in old.items():
        matched = any(fnmatch.fnmatchcase(name, pat) for pat in patterns)
        if not matched:
            now = strip(json.loads(json.dumps(resolver(copy.deepcopy(entry["draft"]), catalog))))
            if now != strip(entry["result"]):
                bad = diff_paths(_norm(entry), _keyed({"draft": entry["draft"], "result": now}))
                violations[name] = bad or ["<unmatched case changed>"]
            new[name] = entry  # unmatched cases are written back untouched
            continue
        draft = filler(copy.deepcopy(entry["draft"]), catalog, overrides_for(name), resolver)
        fresh = {"draft": draft, "result": json.loads(json.dumps(resolver(copy.deepcopy(draft), catalog)))}
        paths = diff_paths(_norm(entry), _norm(fresh))
        new[name] = fresh if paths else entry
        if not paths:
            warnings.append(name)
            continue
        changed[name] = paths
        for pth in paths:
            hit = [p for p in allowed if p.search(pth)]
            if not hit:
                violations.setdefault(name, []).append(pth)
            for p in hit[:1]:
                counts[p.pattern] += 1
    assert set(new) == set(old), "a rebaseline never deletes or adds cases (use --append)"
    out(f"rebaseline {slice_id} ({spec.get('why', '')}){' [dry run]' if dry_run else ''}")
    out(f"  matching cases changed: {len(changed)} of {len(old)}")
    for p, n in counts.items():
        out(f"  {n:5d} changed path(s) match {p}")
    for name in warnings:
        out(f"  WARNING: {name} matches `cases` but did not change (pattern too wide?)")
    for name, paths in changed.items():
        if dry_run:
            out(f"  {name}")
            for pth in paths:
                out(f"      {'DISALLOWED ' if pth in violations.get(name, []) else ''}{pth}")
    for name, paths in violations.items():
        out(f"  VIOLATION {name}: {len(paths)} path(s) outside the allowlist, e.g. {paths[:3]}")
    report = {"changed": changed, "violations": violations, "warnings": warnings, "counts": counts}
    if dry_run:
        return report
    if violations:
        raise RebaselineError(f"rebaseline {slice_id}: paths outside the allowlist or unmatched case changed: "
                              f"{ {n: p[:3] for n, p in violations.items()} }")
    if changed:
        _write_golden(new)
        out(f"wrote {len(new)} cases, {GOLDEN.stat().st_size} bytes")
    else:
        out("nothing changed, golden file not rewritten")
    return report


def _load_golden() -> dict:
    return json.load(gzip.open(GOLDEN, "rt")) if GOLDEN.exists() else {}


_GOLDEN = _load_golden() if not _NEEDS_DATA else {}
pytestmark = pytest.mark.skipif(bool(_NEEDS_DATA), reason=f"5etools data missing: {', '.join(_NEEDS_DATA)}")


@pytest.fixture(scope="module")
def catalog():
    return load()


def test_golden_file_present_and_covers_every_case():
    assert _GOLDEN, "golden file missing: regenerate (see module docstring)"
    names = set(case_drafts(load()))
    kitchen = {n for n in names if n.startswith("ks/") and ks.skip_reason(ks.KITCHEN_SINK[n.rsplit("/", 1)[-1]])}
    assert set(_GOLDEN) == names - kitchen
    assert all(json.loads(json.dumps(v["draft"]))["ruleset"] in RULESETS for v in _GOLDEN.values())


# --- RP6 / P0: rebaseline mode, tested on a synthetic two-case golden (the real file is never touched) ---

def _synthetic(tmp_path, monkeypatch):
    """Two cases in tmp_path; `GOLDEN` is overridden at module level. Fake resolver: result = hp + choice cards."""
    path = tmp_path / "synthetic.json.gz"
    monkeypatch.setitem(globals(), "GOLDEN", path)
    fighter, wizard = ({"hp": 10, "cards": ["a", "b"]}, {"hp": 6, "cards": ["a"]})
    entries = {}
    for name, d in (("mixed/x/fighter", fighter), ("mixed/x/wizard", wizard)):
        entries[name] = {"draft": d, "result": _fake(d, {})}
    _write_golden(entries)
    return path


def _fake(draft, flags):
    cards = [{"id": c, "status": "done", "options": [{"id": "o1"}, {"id": "o2"}]} for c in draft["cards"]]
    if flags.get("insert"):
        cards.insert(0, {"id": "new", "status": "pending", "options": []})
    bump = flags.get("hp", 0) if not flags.get("fighter_only") or "b" in draft["cards"] else 0
    return {"hp": draft["hp"] + bump, "choices": cards, "derived": {"featResources": [1]}}


def _run(slice_id, flags, table, **kw):
    log = []
    rep = rebaseline(slice_id, catalog=object(), rebaselines=table, overrides_for=lambda n: {},
                     resolver=lambda d, c: _fake(d, flags), filler=lambda d, *a: d, out=log.append, **kw)
    return rep, "\n".join(log)


def _table(cases, paths):
    return {"T": {"cases": cases, "paths": paths, "why": "synthetic"}}


def test_rebaseline_expected_path_passes_and_writes(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    before = json.load(gzip.open(path, "rt"))
    rep, log = _run("T", {"hp": 1, "fighter_only": True}, _table(["*/fighter"], [r"^result[.]hp$"]))
    after = json.load(gzip.open(path, "rt"))
    assert rep["changed"] == {"mixed/x/fighter": ["result.hp"]} and not rep["violations"]
    assert after["mixed/x/fighter"]["result"]["hp"] == 11 and after["mixed/x/wizard"] == before["mixed/x/wizard"]
    assert "1 changed path(s) match ^result[.]hp$" in log


def test_rebaseline_unexpected_path_fails_and_leaves_file(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    raw = path.read_bytes()
    with pytest.raises(RebaselineError):
        _run("T", {"hp": 1, "insert": True, "fighter_only": True}, _table(["*/fighter"], [r"^result[.]hp$"]))
    assert path.read_bytes() == raw


def test_rebaseline_unmatched_case_changing_fails(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    raw = path.read_bytes()
    with pytest.raises(RebaselineError, match="wizard"):
        _run("T", {"hp": 1}, _table(["*/fighter"], [r"^result[.]hp$"]))  # wizard also moves but is not listed
    assert path.read_bytes() == raw


def test_rebaseline_dry_run_writes_nothing_and_prints_diff(tmp_path, monkeypatch):
    path = _synthetic(tmp_path, monkeypatch)
    raw = path.read_bytes()
    rep, log = _run("T", {"hp": 1, "fighter_only": True}, _table(["*/fighter"], [r"^nothing$"]), dry_run=True)  # no raise on violations
    assert path.read_bytes() == raw
    assert "DISALLOWED result.hp" in log and "[dry run]" in log and "mixed/x/fighter" in rep["violations"]


def test_rebaseline_warns_when_a_matching_case_does_not_change(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    rep, log = _run("T", {}, _table(["mixed/*"], [r"^result"]))
    assert sorted(rep["warnings"]) == ["mixed/x/fighter", "mixed/x/wizard"] and "WARNING" in log
    assert "not rewritten" in log


def test_rebaseline_inserted_card_lands_at_a_keyed_path(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    rep, _ = _run("T", {"insert": True}, _table(["mixed/*"], [r"^result[.]choices\[new\]$"]), dry_run=True)
    # one path per case, not a shifted index for every following card
    assert rep["changed"] == {"mixed/x/fighter": ["result.choices[new]"], "mixed/x/wizard": ["result.choices[new]"]}
    assert not rep["violations"]


def test_rebaseline_unknown_slice_raises(tmp_path, monkeypatch):
    _synthetic(tmp_path, monkeypatch)
    with pytest.raises(KeyError):
        _run("nope", {}, _table(["*"], []))


def test_rebaselines_constant_is_append_only_and_strip_unchanged():
    """Append-only record: a later slice adds a key, never edits or removes one (extend this tuple then)."""
    assert tuple(REBASELINES) == ("RP7", "RPF", "RP15", "RP16") and STRIP == ("derived.featResources",)
    rp7 = REBASELINES["RP7"]
    assert rp7["cases"] == ["*/src-*/monk[0-9]*", "ks/src-*/monk14"] and len(rp7["paths"]) == 3


def test_rp7_cases_are_the_primary_monk_cases_only():
    """The multiclass Barbarian 3 / Monk 2 (Monk secondary) is not matched, so it must stay byte-identical."""
    names = sorted(_GOLDEN)
    hit = [n for n in names if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RP7"]["cases"])]
    assert len(hit) == 18 and not [n for n in hit if "multi-" in n]
    for n in hit:  # every matched case carries the new card with the filler's pick (the rebaselined content)
        assert any(c["id"] == "class:monk:1:prof-choice-1" and c["status"] == "resolved" for c in _GOLDEN[n]["result"]["choices"])
    for n in names:
        if "multi-barbarian3-monk2" in n:
            assert not any(c["id"] == "class:monk:1:prof-choice-1" for c in _GOLDEN[n]["result"]["choices"])


def test_rpf_cases_are_the_multiclass_rogue_bard_only_and_hold_no_duplicate_skill_pick():
    hit = [n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RPF"]["cases"])]
    assert len(hit) == 4 and all("multi-rogue3-bard2" in n for n in hit)
    for n in hit:
        res = _GOLDEN[n]["result"]
        picks = [s for c in res["choices"] if c["id"].endswith(("prof-choice-0", "prof-choice-1")) and c["source"]["kind"] == "class"
                 for s in c["selected"] if s.startswith("skill-")]
        assert len(picks) == len(set(picks)), n


def test_rp15_cases_are_the_wizard_20_cases_and_hold_the_srd_pick_cards():
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RP15"]["cases"]))
    assert len(hit) == 4 and all(n.endswith("/wizard20") for n in hit)
    for n in hit:  # the golden books hold level 1 / 2 spells only: Mastery is filled, Signature has nothing to offer
        by_id = {c["id"]: c for c in _GOLDEN[n]["result"]["choices"]}
        assert by_id["class:wizard:18:spell-mastery-1"]["status"] == "resolved", n
        assert by_id["class:wizard:20:signature-spells"]["status"] == "unavailable", n
    for n in ("ks/src-all/wizard20-2014", "ks/src-srd/wizard20-2014"):  # appended kitchen sink with real picks
        res = _GOLDEN[n]["result"]
        entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "wizard")
        assert [s["id"] for s in entry["signatureSpells"]] == ["fireball", "counterspell"]
        assert [s["id"] for s in entry["spellMastery"]] == ["shield", "web"]
        assert [s["id"] for s in entry["alwaysPrepared"]] == ["fireball", "counterspell"]
        assert any(r["id"] == "wizard:signature-spells" and r["uses"] == 2 for r in res["derived"]["classResources"])


def test_rp16_cases_are_the_bard_11_and_20_cases_and_hold_the_magical_secrets_options():
    hit = sorted(n for n in _GOLDEN if any(fnmatch.fnmatchcase(n, p) for p in REBASELINES["RP16"]["cases"]))
    assert len(hit) == 8 and all(n.endswith(("/bard11", "/bard20")) for n in hit)
    for n in hit:  # the stored picks are the old list's first spells: none from another class, all kept
        card = next(c for c in _GOLDEN[n]["result"]["choices"] if c["id"] == "class:bard:spells-known")
        labelled = [o for o in card["options"] if o["label"].endswith("(Magical Secrets)")]
        assert labelled and any(o["id"] == "fire-bolt" for o in labelled) and "Magical Secrets" in card["description"], n
        assert not set(card["selected"]) & {o["id"] for o in labelled}, n
        assert len(card["selected"]) == card["count"], n
    for n in ("ks/src-all/bard10-2014", "ks/src-srd/bard10-2014"):  # appended kitchen sink with real picks
        res = _GOLDEN[n]["result"]
        known = next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")["known"]
        assert {"fireball", "sacred-flame"} <= {s["id"] for s in known}, n
        assert not [p for p in res["pruned"] if p["choiceId"] == "class:bard:spells-known"], n


def test_keyed_normalization_and_diff_paths():
    a = _keyed({"choices": [{"id": "x", "v": 1}, {"id": "y", "v": 2}], "plain": [1, 2]})
    b = _keyed({"choices": [{"id": "n", "v": 0}, {"id": "x", "v": 1}, {"id": "y", "v": 3}], "plain": [1, 2]})
    assert diff_paths(a, b) == ["choices[n]", "choices[y].v"]
    dup = _keyed({"c": [{"id": "x"}, {"id": "x"}]})  # non-unique ids stay a list
    assert isinstance(dup["c"], list)


@pytest.mark.parametrize("name", sorted(_GOLDEN))
def test_mixed_and_2014_resolve_is_unchanged(catalog, name):
    entry = _GOLDEN[name]
    now = strip(json.loads(json.dumps(resolve(copy.deepcopy(entry["draft"]), catalog))))
    assert now == strip(entry["result"])


if __name__ == "__main__":
    if "--rebaseline" in sys.argv:
        i = sys.argv.index("--rebaseline")
        if i + 1 >= len(sys.argv):
            sys.exit("--rebaseline needs a slice id (a key of REBASELINES)")
        try:
            rebaseline(sys.argv[i + 1], dry_run="--dry-run" in sys.argv)
        except (KeyError, RebaselineError) as e:
            sys.exit(str(e))
    elif "--append" in sys.argv:
        append_new_cases()
    elif "--regenerate" in sys.argv:
        regenerate()
    else:
        sys.exit("pass --append (add new cases only), --rebaseline <SLICE> [--dry-run] or --regenerate (rewrite everything) to change the golden file")
