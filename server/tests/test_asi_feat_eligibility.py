"""ASI-level feat eligibility by ruleset and slot level (F1): 2014 offers the
category-less books plus General (AU) feats, 2024 offers General + Origin,
Epic Boons only at slot level 19 and never under 2014."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset, level, choices=None, sources=None):
    return {
        "ruleset": ruleset, "sources": sources or [],
        "classes": [{"classId": "fighter", "level": level, "choices": choices or {}}],
        "species": {"id": "human"}, "background": {"id": "acolyte"},
    }


def _options(r, level=4):
    tpl = next(c for c in r["choices"] if c["id"] == f"class:fighter:{level}:asi")
    return tpl["options"]


def _ids(options):
    return {o["id"] for o in options}


def test_fighter_4_2014_pool(catalog):
    opts = _options(resolve(_draft("2014", 4), catalog))
    ids = _ids(opts)
    assert len(opts) == 21 + 123
    for want in ("feat:great-weapon-master-phb", "feat:lucky-phb", "feat:war-caster-phb", "feat:abjuration-adept-au"):
        assert want in ids
    assert not any(i.endswith("-xphb") for i in ids if i.startswith("feat:"))
    assert "feat:alert-xphb" not in ids


def test_fighter_4_2024_pool(catalog):
    ids = _ids(_options(resolve(_draft("2024", 4), catalog)))
    assert len(ids) == 21 + 129
    assert {"feat:alert-xphb", "feat:great-weapon-master-xphb"} <= ids
    for no in ("feat:great-weapon-master-phb", "feat:boon-of-combat-prowess-xphb", "feat:archery-xphb",
               "feat:ability-score-improvement-xphb"):
        assert no not in ids


def test_fighter_4_mixed_pool(catalog):
    assert len(_options(resolve(_draft("mixed", 4), catalog))) == 21 + 237


def test_unknown_ruleset_behaves_like_mixed(catalog):
    from engine.resolve import _is_asi_eligible_feat
    gwm = catalog.feats["great-weapon-master-phb"]
    assert _is_asi_eligible_feat(gwm, "weird", 4)
    assert not _is_asi_eligible_feat(catalog.feats["ability-score-improvement-xphb"], "mixed", 4)


def test_fighter_19_epic_boon_only_at_slot_19(catalog):
    r = resolve(_draft("2024", 19), catalog)
    at19 = _options(r, 19)
    assert len(at19) == 21 + 161
    boon = next(o for o in at19 if o["id"] == "feat:boon-of-combat-prowess-xphb")
    assert not boon.get("disabled")
    assert "feat:boon-of-combat-prowess-xphb" not in _ids(_options(r, 16))
    assert len(_options(r, 16)) == 21 + 129


def test_fighter_19_2014_no_epic_boon(catalog):
    r = resolve(_draft("2014", 19), catalog)
    assert len(_options(r, 19)) == 21 + 123
    assert not any("boon" in i for i in _ids(_options(r, 19)))


def test_fighter_19_mixed_pool(catalog):
    assert len(_options(resolve(_draft("mixed", 19), catalog), 19)) == 21 + 269


def test_sources_filter_counts(catalog):
    def n(ruleset, sources, level=4):
        return len([o for o in _options(resolve(_draft(ruleset, level, sources=sources), catalog), level)
                    if o["id"].startswith("feat:")])
    assert (n("2014", ["srd"]), n("2024", ["srd"]), n("mixed", ["srd"])) == (0, 0, 0)
    assert (n("2014", ["srd", "xphb"]), n("2024", ["srd", "xphb"]), n("mixed", ["srd", "xphb"])) == (0, 52, 52)
    assert n("2024", ["srd", "xphb"], 19) == 64
    assert (n("2014", ["phb"]), n("2024", ["phb"]), n("mixed", ["phb"])) == (42, 0, 42)
    assert (n("2014", ["phb", "xge", "tce"]), n("mixed", ["phb", "xge", "tce"])) == (72, 72)


def test_2024_pick_alert_is_applied(catalog):
    r = resolve(_draft("2024", 4, {"class:fighter:4:asi": ["feat:alert-xphb"]}), catalog)
    assert any(f["id"] == "alert-xphb" or f.get("index") == "alert-xphb" for f in r["sheet"]["feats"])


def test_2014_pick_great_weapon_master_is_applied(catalog):
    r = resolve(_draft("2014", 4, {"class:fighter:4:asi": ["feat:great-weapon-master-phb"]}), catalog)
    assert any("great-weapon-master-phb" in str(f) for f in r["sheet"]["feats"])
    assert r["problems"] == []


def test_epic_boon_at_slot_4_not_applied(catalog):
    r = resolve(_draft("2024", 4, {"class:fighter:4:asi": ["feat:boon-of-combat-prowess-xphb"]}), catalog)
    assert not any("boon-of-combat-prowess" in str(f) for f in r["sheet"]["feats"])
