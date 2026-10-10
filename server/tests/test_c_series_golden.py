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

The file was first written from the engine at commit 81fce17 (before any C-series work). The
whole module skips when the local 5etools data (classes, official, spells) is absent.
"""
from __future__ import annotations

import copy
import gzip
import json
import pathlib
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
STRIP: tuple[str, ...] = ()

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
        for src in SOURCES:
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


@pytest.mark.parametrize("name", sorted(_GOLDEN))
def test_mixed_and_2014_resolve_is_unchanged(catalog, name):
    entry = _GOLDEN[name]
    now = strip(json.loads(json.dumps(resolve(copy.deepcopy(entry["draft"]), catalog))))
    assert now == strip(entry["result"])


if __name__ == "__main__":
    if "--regenerate" not in sys.argv:
        sys.exit("pass --regenerate to rewrite the golden file")
    regenerate()
