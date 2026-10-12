"""FE12 consolidation: the frontend type guard covers every key a feat can put on the output.

``test_types_drift`` checks the kitchen-sink and class drafts. This module resolves a character that holds EACH of
the 305 catalog feats (through an ASI pick; the patched-catalog route of ``test_feat_tail`` for the feats no ASI pool
offers), with a weapon set on the sheet so the attack rows carry the feat riders (Unarmed Strike, off-hand damage,
row notes), and runs the same drift check on every container: ``sheet.feats[]`` (``notes``, ``choice``),
``derived.featResources[]`` (``die``, ``dc``, ``uses`` ...), ``derived.attacks[]``, ``sheet.innateSpells[]``,
``choices[]`` and the choice options of the feat cards.  A new feat key without a field in ``frontend/src/types.ts``
fails here instead of silently reaching the UI untyped."""
import copy

import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from test_feat_tail import ALL_SOURCES, _draft, _patched
from test_types_drift import TYPES_TS, _drift, parse_interfaces

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

_GEAR = [{"itemId": i, "qty": 1, "equipped": True}
         for i in ("greataxe", "longbow", "crossbow-hand", "rapier", "double-bladed-scimitar", "leather-armor")]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _grant_with_gear(catalog, index):
    slot = 19
    for ruleset in ("mixed", "2024", "2014"):
        for cat in (catalog, _patched(catalog, index)):
            draft = _draft([("fighter", slot)], ruleset=ruleset, sources=ALL_SOURCES)
            draft["classes"][0]["choices"] = {f"class:fighter:{slot}:asi": [f"feat:{index}"]}
            draft["equipment"]["added"] = copy.deepcopy(_GEAR)
            res = resolve(draft, cat)
            if index in [f["id"] for f in res["sheet"]["feats"]]:
                return res
    return None


def test_every_feat_key_on_the_output_is_typed_in_types_ts(catalog):
    interfaces = parse_interfaces(TYPES_TS.read_text(encoding="utf-8"))
    drift, granted, seen_keys = {}, 0, set()
    for index in sorted(catalog.feats):
        res = _grant_with_gear(catalog, index)
        if res is None:
            continue
        granted += 1
        for feat in res["sheet"]["feats"]:
            seen_keys |= set(feat)
        for res_ in res["derived"]["featResources"]:
            seen_keys |= set(res_)
        for item in _drift(res, interfaces):
            drift.setdefault(item, index)
    assert granted >= 300, granted             # the sweep is not vacuous: (almost) every feat was really granted
    assert {"notes"} <= seen_keys and {"die", "dc", "uses", "featId"} <= seen_keys
    assert not drift, "feat output keys without a field in frontend/src/types.ts:\n" + "\n".join(
        f"  {iface}.{key}  (first seen with {where})" for (iface, key), where in sorted(drift.items()))
