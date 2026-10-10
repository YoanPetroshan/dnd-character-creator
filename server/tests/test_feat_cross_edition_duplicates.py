"""S2 (decision D4): a feat taken under one edition makes the same-name feat of
the other edition "already taken" under every ruleset (it only matters under
`mixed`, the only ruleset whose pool holds both editions), unless the feat
being picked is `repeatable`.

RAW rule: you can't take the same feat more than once unless it says so. The
5etools data flags the 2024 versions of Elemental Adept, Magic Initiate and
Skilled `repeatable`; their 2014 versions are NOT flagged. Matrix:
  - taken XPHB Alert (background), pick PHB Alert  -> blocked, cross-edition reason
  - taken PHB Alert (ASI), pick XPHB Alert later   -> blocked (first pick wins)
  - taken XPHB Magic Initiate, pick PHB Magic Initiate -> blocked (picked is not repeatable)
  - taken PHB Magic Initiate, pick XPHB Magic Initiate -> allowed (picked is repeatable)
  - 2014 / 2024 rulesets: each pool has one edition, A1 counts unchanged.
"""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

ABILS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset="mixed", background="guard-xphb", picks=None, level=8, extra=None):
    choices = {cid: [p] for cid, p in (picks or {}).items()}
    d = {
        "ruleset": ruleset, "sources": [],
        "classes": [{"classId": "fighter", "level": level, "choices": choices}],
        "species": {"id": "human"}, "background": {"id": background},
        "abilities": {"method": "manual", "base": {a: 10 for a in ABILS}},
    }
    return d


def _opt(r, cid, oid):
    tpl = next(c for c in r["choices"] if c["id"] == cid)
    return next(o for o in tpl["options"] if o["id"] == oid)


def _feat_indices(r):
    return [str(f.get("index") or f.get("id") or f) for f in r["sheet"]["feats"]]


def test_background_grants_xphb_alert(catalog):
    # VERIFIED by script: Criminal, Guard, Ice Fisher (FRHoF) and Inquisitive
    # (EFA) XPHB-style backgrounds grant Alert (ref alert-xphb).
    for bid in ("criminal-xphb", "guard-xphb"):
        assert catalog.backgrounds[bid]["feat_refs"] == ["alert-xphb"]


def test_phb_alert_disabled_after_xphb_background_alert(catalog):
    r = resolve(_draft(), catalog)
    o = _opt(r, "class:fighter:4:asi", "feat:alert-phb")
    assert o["disabled"] is True
    assert o["disabledReason"] == "already taken (Alert, XPHB)"
    # the same-index case keeps the plain reason
    assert _opt(r, "class:fighter:4:asi", "feat:alert-xphb")["disabledReason"] == "already taken"


def test_stored_phb_alert_is_a_duplicate_problem_and_not_applied(catalog):
    r = resolve(_draft(picks={"class:fighter:4:asi": "feat:alert-phb"}), catalog)
    assert "feat-duplicate-alert-phb-class:fighter:4:asi" in [p["id"] for p in r["problems"]]
    assert sum("alert" in s for s in _feat_indices(r)) == 1


def test_asi_pick_blocks_other_edition_at_later_level(catalog):
    r = resolve(_draft(background="acolyte", picks={"class:fighter:4:asi": "feat:alert-phb"}), catalog)
    assert _opt(r, "class:fighter:8:asi", "feat:alert-xphb")["disabledReason"] == "already taken (Alert, PHB)"
    r2 = resolve(_draft(background="acolyte", picks={
        "class:fighter:4:asi": "feat:alert-phb", "class:fighter:8:asi": "feat:alert-xphb"}), catalog)
    assert "feat-duplicate-alert-xphb-class:fighter:8:asi" in [p["id"] for p in r2["problems"]]


def test_species_feat_pick_blocks_other_edition_at_asi(catalog):
    # Variant-human style species feat grants and the XPHB Human origin feat
    # share the same taken map as the ASI levels.
    d = _draft(background="acolyte")
    d["species"] = {"id": "human-xphb", "choices": {"species:human-xphb:feat-0": ["feat:alert-xphb"]}}
    r = resolve(d, catalog)
    assert any(c["id"] == "species:human-xphb:feat-0" for c in r["choices"])
    assert _opt(r, "class:fighter:4:asi", "feat:alert-phb")["disabledReason"] == "already taken (Alert, XPHB)"


def test_repeatable_magic_initiate_matrix(catalog):
    assert catalog.feats["magic-initiate-xphb"]["repeatable"] is True
    assert not catalog.feats["magic-initiate-phb"].get("repeatable")
    # XPHB first, picking the (non-repeatable) PHB one is blocked
    r = resolve(_draft(background="acolyte", picks={"class:fighter:4:asi": "feat:magic-initiate-xphb"}), catalog)
    assert _opt(r, "class:fighter:8:asi", "feat:magic-initiate-phb")["disabled"] is True
    # PHB first, picking the repeatable XPHB one is allowed
    r = resolve(_draft(background="acolyte", picks={"class:fighter:4:asi": "feat:magic-initiate-phb"}), catalog)
    assert not _opt(r, "class:fighter:8:asi", "feat:magic-initiate-xphb").get("disabled")
    # XPHB again after XPHB: repeatable, still allowed
    r = resolve(_draft(background="acolyte", picks={"class:fighter:4:asi": "feat:magic-initiate-xphb"}), catalog)
    assert not _opt(r, "class:fighter:8:asi", "feat:magic-initiate-xphb").get("disabled")


@pytest.mark.parametrize("ruleset", ["2014", "2024"])
def test_single_edition_rulesets_unchanged(catalog, ruleset):
    r = resolve(_draft(ruleset, background="acolyte", level=4), catalog)
    tpl = next(c for c in r["choices"] if c["id"] == "class:fighter:4:asi")
    assert not [o for o in tpl["options"] if o.get("disabledReason", "").startswith("already taken")]
    # A1 counts for a Fighter: 123 feats + 21 ASI combos (2014); 140 + 21 (2024, 129 before C3
    # added the 11 plain Fighting Style feats; FS:P / FS:R excluded in F1) are asserted in test_asi_feat_eligibility.py.
    assert len(tpl["options"]) == {"2014": 123, "2024": 140}[ruleset] + 21
