"""SK5: the in-app sheet (/sheet) covers every resolution leaf the W9 export audit looks at.

`frontend/src/logic/sheetCoverage.json` maps each sheet section key to the resolution paths (``sheet.*`` /
``derived.*``) the section shows; the vitest test `sheetSections.test.ts` checks, on the dumped fixtures, that those
leaves really reach the section data and the rendered page text. This test closes the other side: every leaf of every
audited resolution (the W9 drafts, plus one draft with worn / wielded / details set) that is not already an id in
``EXPORT_OMITTED`` is either assigned to a section there or listed in ``SHEET_OMITTED`` below with a reason.

``SHEET_OMITTED``: path pattern -> "category: reason" (pattern syntax of test_export_completeness.py). Categories:
id (a machine id whose name is shown), dup (the same information is shown through another leaf), ui (picker data of
the Equipment page, not sheet content), flag (a boolean that only drives the UI). An entry that matches no leaf fails
as stale.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import Counter

import pytest

import test_export_completeness as W9
from catalog.loader import load
from engine.resolve import resolve
from kitchen_sink import build, skip_reason

FRONTEND = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "logic"
COVERAGE = json.loads((FRONTEND / "sheetCoverage.json").read_text(encoding="utf-8"))["sections"]

_NOTE = "dup: the Breath Weapon note text already says the damage type, the save and the area"
SHEET_OMITTED: dict[str, str] = {
    "derived.classResources.[].classId": "id: the class the resource belongs to; the resource name is shown under 'Ресурси на класа'",
    "derived.classResources.[].source.label": "dup: the resource name already names the feature; the sheet does not repeat its class / subclass",
    "derived.featResources.[].source.label": "dup: the resource name already names the feat",
    "derived.speciesResources.[].source.label": "dup: the resource name already names the species trait",
    "derived.speciesResources.[].details.damageType": _NOTE,
    "derived.speciesResources.[].details.save": _NOTE,
    "derived.speciesResources.[].details.shape": _NOTE,
    "derived.classResources.[].details.metamagicCosts.*": "dup: G2, the same picks and costs are shown through details.metamagic (names with costs)",
    "derived.classResources.[].details.recharges": "dup: G4, the recharge condition is written out in the note (recharge 'other')",
    "derived.classResources.[].details.disciplineKiCosts.*": "dup: G4, the same picks and costs are in the Ki note (Elemental disciplines: ...)",
    "derived.classResources.[].details.classes.[]": "dup: G3, the classes behind a merged Channel Divinity; its note is labelled with the class names",
    "sheet.equipment.slots.armor.[].name": "ui: candidates of the worn-armor picker; the sheet shows only the armor that is worn",
    "sheet.equipment.slots.shield.[].name": "ui: candidates of the shield picker; the sheet shows only whether a shield is used",
    "sheet.equipment.slots.hands.[].name": "ui: candidates of the hand picker; the sheet shows only what is wielded",
    "sheet.equipment.worn.manual": "flag: whether the draft set the worn armor by hand",
    "sheet.equipment.wielded.manual": "flag: whether the draft set the wielded weapons by hand",
}

# Coverage patterns that no audited draft produces; the section code handles them and sheetSections.test.ts
# exercises the sections with synthetic resolutions where it can.
UNSEEN_OK = {
    "sheet.equipment.narrativeItems.[]": "no audited draft has narrative items; the section code prints the list",
}


def _extra_resolution(catalog):
    """fighter4-2024 with worn / wielded / details set: leaves the kitchen sinks do not have."""
    draft = build("fighter4-2024", catalog, resolve)
    draft["equipment"]["worn"] = {"armor": "chain-mail", "shield": False}
    draft["equipment"]["wielded"] = {"main": "greatsword", "off": None}
    draft["details"] = {"alignment": "Neutral", "faith": "None", "lifestyle": "Modest", "age": "30", "height": "180",
                        "weight": "80", "eyes": "Grey", "skin": "Pale", "hair": "Black", "personalityTraits": "Calm",
                        "ideals": "Order", "bonds": "Kin", "flaws": "Proud", "backstory": "Long", "organizations": "None",
                        "allies": "Few", "enemies": "Some", "notes": "More"}
    return resolve(draft, catalog)


@pytest.fixture(scope="module")
def catalog():
    return load()


def _all_paths(catalog) -> set[str]:
    """Every leaf path of every audited resolution that the W9 audit checks (not an id in EXPORT_OMITTED)."""
    paths: set[str] = set()
    resolutions = []
    for sid, spec in W9.ALL_SPECS.items():
        if skip_reason(spec):
            pytest.skip("5etools data missing: the coverage check needs every audited draft")
        resolutions.append(W9._resolution(sid, catalog))
    resolutions.append(_extra_resolution(catalog))
    for res in resolutions:
        for section in ("sheet", "derived"):
            for path, _value in W9._leaves(res[section], [section]):
                if W9._lookup(W9.EXPORT_OMITTED, path) is None:
                    paths.add(path)
    return paths


def _covered(path: str) -> str | None:
    for key, pats in COVERAGE.items():
        if any(W9._pattern(p).match(path) for p in pats):
            return key
    return None


def test_every_checked_leaf_is_rendered_or_listed_in_sheet_omitted(catalog):
    uncovered = sorted(p for p in _all_paths(catalog) if _covered(p) is None and W9._lookup(SHEET_OMITTED, p) is None)
    assert not uncovered, "leaves neither on the /sheet page (sheetCoverage.json) nor in SHEET_OMITTED:\n" + "\n".join(uncovered)


def test_the_check_catches_an_unassigned_leaf():
    assert _covered("derived.inventedKey") is None and W9._lookup(SHEET_OMITTED, "derived.inventedKey") is None
    assert _covered("derived.armorClass") == "armorClass"


def test_nothing_is_both_rendered_and_omitted(catalog):
    both = sorted(p for p in _all_paths(catalog) if _covered(p) is not None and W9._lookup(SHEET_OMITTED, p) is not None)
    assert not both, both


def test_no_stale_entries(catalog):
    paths = _all_paths(catalog)
    stale_omitted = [pat for pat in SHEET_OMITTED if not any(W9._pattern(pat).match(p) for p in paths)]
    assert not stale_omitted, f"stale SHEET_OMITTED entries: {stale_omitted}"
    stale_cov = [(key, pat) for key, pats in COVERAGE.items() for pat in pats
                 if pat not in UNSEEN_OK and not any(W9._pattern(pat).match(p) for p in paths)]
    assert not stale_cov, f"coverage patterns matching no audited leaf: {stale_cov}"


def test_sheet_omitted_entries_have_a_known_category_and_a_reason():
    cats = Counter(r.split(":")[0] for r in SHEET_OMITTED.values())
    assert set(cats) <= {"id", "dup", "ui", "flag"}, cats
    assert all(": " in r and len(r.split(": ", 1)[1]) > 10 for r in SHEET_OMITTED.values())
    assert len(SHEET_OMITTED) <= 16, "keep the omitted table small"  # G4: 14 -> 16 (two dups); G6 listed its two in EXPORT_OMITTED instead


def test_coverage_sections_are_the_typescript_section_keys():
    ts = (FRONTEND / "sheetSections.ts").read_text(encoding="utf-8")
    block = re.search(r"SHEET_SECTION_KEYS = \[(.*?)\] as const", ts, re.S).group(1)
    keys = re.findall(r'"(\w+)"', block)
    assert sorted(keys) == sorted(COVERAGE), set(keys) ^ set(COVERAGE)
    assert all(COVERAGE[k] for k in COVERAGE)
