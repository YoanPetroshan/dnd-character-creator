"""ASI-level feat eligibility by ruleset and slot level (F1): 2014 offers the
category-less books plus General (AU) feats, 2024 offers General + Origin,
Epic Boons only at slot level 19 and never under 2014.

C3 (U3): the 11 plain Fighting Style feats (FS, incl. Arcane Warrior AU) are also
offered under 2024 and mixed when the character has a Fighting Style feature (a Fighter
here), never under 2014. F1: Blessed Warrior (FS:P) and Druidic Warrior (FS:R) are NOT
admitted (their prerequisite is the level-2 Paladin / Ranger feature itself); they come
only from those classes' fighting-style cards. Pool sizes for a Fighter, before C3 ->
after C3 -> after F1: 2024 slot 4 129 -> 142 -> 140, slot 19 161 -> 174 -> 172; mixed
237 -> 250 -> 248 and 269 -> 282 -> 280; sources srd+xphb 2024/mixed 52 -> 64 -> 62
(slot 19: 64 -> 76 -> 74); 2014 unchanged (123); a Wizard (no Fighting Style feature)
unchanged (129 / 237).

G1: under 2024 Arcane Warrior (AU) is offered only when AU is an explicit source, so the
unfiltered 2024 Fighter pools lose one: slot 4 140 -> 139, slot 19 172 -> 171 (mixed and
the srd+xphb counts are unchanged)."""
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
    assert len(ids) == 21 + 139  # G1: Arcane Warrior (AU) needs AU enabled under 2024
    assert {"feat:alert-xphb", "feat:great-weapon-master-xphb", "feat:archery-xphb"} <= ids
    assert not {"feat:blessed-warrior-xphb", "feat:druidic-warrior-xphb"} & ids  # F1
    for no in ("feat:great-weapon-master-phb", "feat:boon-of-combat-prowess-xphb",
               "feat:ability-score-improvement-xphb"):
        assert no not in ids


def test_fighter_4_mixed_pool(catalog):
    assert len(_options(resolve(_draft("mixed", 4), catalog))) == 21 + 248


def test_unknown_ruleset_behaves_like_mixed(catalog):
    from engine.resolve import _is_asi_eligible_feat
    gwm = catalog.feats["great-weapon-master-phb"]
    assert _is_asi_eligible_feat(gwm, "weird", 4)
    assert not _is_asi_eligible_feat(catalog.feats["ability-score-improvement-xphb"], "mixed", 4)


def test_fighter_19_epic_boon_only_at_slot_19(catalog):
    r = resolve(_draft("2024", 19), catalog)
    at19 = _options(r, 19)
    assert len(at19) == 21 + 171
    boon = next(o for o in at19 if o["id"] == "feat:boon-of-combat-prowess-xphb")
    assert not boon.get("disabled")
    assert "feat:boon-of-combat-prowess-xphb" not in _ids(_options(r, 16))
    assert len(_options(r, 16)) == 21 + 139


def test_fighter_19_2014_no_epic_boon(catalog):
    r = resolve(_draft("2014", 19), catalog)
    assert len(_options(r, 19)) == 21 + 123
    assert not any("boon" in i for i in _ids(_options(r, 19)))


def test_fighter_19_mixed_pool(catalog):
    assert len(_options(resolve(_draft("mixed", 19), catalog), 19)) == 21 + 280


def test_sources_filter_counts(catalog):
    def n(ruleset, sources, level=4):
        return len([o for o in _options(resolve(_draft(ruleset, level, sources=sources), catalog), level)
                    if o["id"].startswith("feat:")])
    assert (n("2014", ["srd"]), n("2024", ["srd"]), n("mixed", ["srd"])) == (0, 0, 0)
    assert (n("2014", ["srd", "xphb"]), n("2024", ["srd", "xphb"]), n("mixed", ["srd", "xphb"])) == (0, 62, 62)
    assert n("2024", ["srd", "xphb"], 19) == 74
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


def test_wizard_pools_do_not_change_with_c3(catalog):
    """A character with no Fighting Style feature keeps the pre-C3 pools."""
    def n(ruleset, cls="wizard"):
        r = resolve({"ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": 4}],
                     "species": {"id": "human"}, "background": {"id": "acolyte"}}, catalog)
        return len(next(c for c in r["choices"] if c["id"] == f"class:{cls}:4:asi")["options"]) - 21
    assert (n("2014"), n("2024"), n("mixed")) == (123, 129, 237)
    assert (n("2014", "paladin"), n("2024", "paladin"), n("mixed", "paladin")) == (123, 139, 248)
