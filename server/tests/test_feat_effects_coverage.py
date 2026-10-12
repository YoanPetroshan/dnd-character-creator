"""FE0: feat scan table, coverage ratchet and data guards (docs/superpowers/plans/2026-10-11-feat-effects.md).

Data and tests only. Nothing in the engine reads ``catalog.feat_effects_data`` yet.

Ratchet: every catalog feat index is in exactly one of ``FEAT_EFFECTS`` (classified) and
``FEAT_PENDING`` (not yet classified); every ``FEAT_EFFECTS`` key is a catalog feat and uses only
the known vocabulary; ``FEAT_PENDING`` may only shrink (``PENDING_CEILING`` was lowered by each FE
slice) and has been empty since FE10. ``FEAT_KINDS`` is the per-index scan table of plan
section 3 and must cover the catalog exactly.

Data guards (they pin assumptions later slices rely on, read from the raw 5etools feats.json):
- B1 / V2: the Epic Boon feat bodies in the catalog do not repeat the cap (only the data does):
  ``ability[].max == 30`` on all 32 Epic Boon feats and on no other feat.
- V3: no Origin, Fighting Style, FS:P or FS:R feat has an ``ability`` record.
- B5: Keenness of the Stone Giant is the only holder of ``bonusSenses`` (darkvision 60).
- B3: Echoing Soul's data says one skill (``{"any": 1}``) while its text says two skills; the
  text wins in FE6, so the guard pins both the data count and the text sentence.
- V18: the F0 golden holds no feat at all (FE12 raises the pinned count additively).
"""
from __future__ import annotations

import gzip
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from catalog import feat_effects_data as fed  # noqa: E402
from catalog import official_source as official  # noqa: E402
from catalog.loader import load  # noqa: E402
from catalog.official.feats import _feat_from_5etools  # noqa: E402

pytestmark = pytest.mark.skipif(not official.has_official(), reason="5etools official data missing")

# Lowered by each FE slice that classifies feats; FE10 set it to 0 (nothing may be added back).
PENDING_CEILING = 0
# Raised only by FE12 (additive golden cases that hold feats): feats-mixed-fighter14, feats-2014-rogue16 and
# feats-mixed-wizard8, each under `sources` [] (the golden's `--append` mode added them; no existing case changed).
GOLDEN_FEAT_CASES = 3
GOLDEN = pathlib.Path(__file__).parent / "golden" / "c_series_mixed_2014_baseline.json.gz"


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def raw_feats():
    """(index, raw 5etools record) for every feat, in file order."""
    with open(official.official_dir() / "feats.json", encoding="utf-8") as f:
        data = json.load(f)
    out = []
    for raw in data.get("feat", []):
        converted = _feat_from_5etools(raw)
        if converted is not None:
            out.append((converted["index"], raw))
    return out


def _text(feat: dict) -> str:
    """Every string in the feat's ``entries`` (nested entries, lists and list items)."""
    def walk(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v)
    return " ".join(walk(feat.get("entries", [])))


# ---------------------------------------------------------------- ratchet


def test_every_feat_is_classified_or_pending_exactly_once(catalog):
    indexes = set(catalog.feats)
    assert len(indexes) == 305
    effects, pending = set(fed.FEAT_EFFECTS), set(fed.FEAT_PENDING)
    assert not effects & pending
    assert effects | pending == indexes


def test_every_effect_key_is_a_catalog_feat_and_uses_known_vocabulary(catalog):
    assert set(fed.FEAT_EFFECTS) <= set(catalog.feats)
    for index, entry in fed.FEAT_EFFECTS.items():
        assert entry, index
        assert set(entry) <= fed.FEAT_EFFECT_KEYS, (index, set(entry) - fed.FEAT_EFFECT_KEYS)


def test_pending_only_shrinks_and_is_empty_after_fe10():
    """FE10: every catalog feat is classified, so the pending set is empty and stays empty."""
    assert PENDING_CEILING == 0 and fed.FE10_DONE
    assert len(fed.FEAT_PENDING) <= PENDING_CEILING
    assert fed.FEAT_PENDING == frozenset()


def test_every_catalog_feat_has_an_effect_entry(catalog):
    assert set(catalog.feats) == set(fed.FEAT_EFFECTS)


def test_fighting_style_feats_done_through_class_feature_effects_are_data_only(catalog):
    from catalog.reference_data import CLASS_FEATURE_EFFECTS
    done = {i for i, k in fed.FEAT_KINDS.items() if k == {"fighting-style"}}
    assert len(done) == 7
    # (FE3 added data_only entries for the proficiency / spell feats; the 7 FS ones are still exactly these.)
    assert done == {i for i, e in fed.FEAT_EFFECTS.items()
                    if e == {"data_only": True} and fed.FEAT_KINDS[i] == {"fighting-style"}}
    for index in done:
        assert catalog.feats[index]["category"].startswith("FS"), index
    # Six of the seven are keyed in CLASS_FEATURE_EFFECTS; Blind Fighting's blindsight comes
    # from the catalog's own ``senses`` field.
    assert {i for i in done if i in CLASS_FEATURE_EFFECTS} == done - {"blind-fighting-xphb"}
    assert catalog.feats["blind-fighting-xphb"]["senses"] == {"blindsight": 10}


# ---------------------------------------------------------------- scan table


def test_scan_table_covers_the_catalog_exactly(catalog):
    assert set(fed.FEAT_KINDS) == set(catalog.feats)
    assert all(kinds and kinds <= fed.SCAN_KINDS for kinds in fed.FEAT_KINDS.values())


def test_scan_kind_counts_match_the_plan():
    """Plan section 3: B 19, C 22, D 32, E 82; the rest are notes (154, see the deviation note
    in ARCHITECTURE: the plan says 161, which still counts the 7 done Fighting Style feats)."""
    count = {k: sum(1 for kinds in fed.FEAT_KINDS.values() if k in kinds) for k in fed.SCAN_KINDS}
    assert count == {"numeric": 19, "choice": 22, "attack": 32, "resource": 82,
                     "notes": 154, "fighting-style": 7}
    # "notes" is exclusive: a notes-only feat has no other kind.
    assert all(kinds == {"notes"} for kinds in fed.FEAT_KINDS.values() if "notes" in kinds)
    assert len(fed.FEAT_KINDS) == 305


@pytest.mark.parametrize("index,kinds", [
    ("alert-phb", {"numeric"}), ("alert-xphb", {"numeric"}), ("tough-xphb", {"numeric"}),
    ("dragon-hide-xge", {"numeric", "attack"}), ("dual-wielder-phb", {"numeric", "attack"}),
    ("keenness-of-the-stone-giant-bgg", {"numeric", "resource"}),
    ("keen-mind-xphb", {"choice"}), ("skill-expert-xphb", {"choice"}),
    ("martial-adept-phb", {"choice", "resource"}), ("metamagic-adept-tce", {"choice", "resource"}),
    ("lucky-phb", {"resource"}), ("lucky-xphb", {"resource"}),
    ("tavern-brawler-xphb", {"attack"}), ("polearm-master-phb", {"attack"}),
    ("inspiring-leader-xphb", {"notes"}), ("archery-xphb", {"fighting-style"}),
])
def test_scan_table_spot_checks(index, kinds):
    assert fed.FEAT_KINDS[index] == kinds


# ---------------------------------------------------------------- data guards


def test_epic_boon_cap_30_is_carried_by_exactly_the_32_boons(catalog, raw_feats):
    """V2 / B1. The cap lives only in the data (``max``: 30), not in the catalog body text."""
    boons = {i for i, f in catalog.feats.items() if f["category"] == "EB"}
    assert len(boons) == 32
    with_max = {i for i, raw in raw_feats if any("max" in a for a in raw.get("ability", []))}
    assert with_max == boons
    for index, raw in raw_feats:
        if index in boons:
            assert all(a.get("max") == 30 for a in raw["ability"]), index


def test_no_origin_or_fighting_style_feat_has_an_ability_record(catalog, raw_feats):
    """V3: the Lessons and fighting-style paths skip ASI, so these categories must stay ASI-free."""
    cats = {"O", "FS", "FS:P", "FS:R"}
    held = {i for i, f in catalog.feats.items() if f["category"] in cats}
    assert len(held) == 35 + 11 + 1 + 1
    for index, raw in raw_feats:
        if index in held:
            assert not raw.get("ability"), index
            assert not catalog.feats[index]["ability_bonuses"], index
            assert catalog.feats[index]["ability_bonus_options"] is None, index


def test_keenness_of_the_stone_giant_is_the_only_bonus_senses_holder(catalog, raw_feats):
    """B5. Catalog text (Cavernous Sight): darkvision with a range of 60 feet, and an existing
    darkvision "increases by 60 feet"."""
    holders = [(i, raw["bonusSenses"]) for i, raw in raw_feats if "bonusSenses" in raw]
    assert holders == [("keenness-of-the-stone-giant-bgg", [{"darkvision": 60}])]
    text = _text(catalog.feats["keenness-of-the-stone-giant-bgg"])
    assert "darkvision} with a range of 60 feet" in text
    assert "its range increases by 60 feet" in text
    # Not converted yet (FE4 adds the catalog field ``bonus_senses``).
    assert "darkvision" not in catalog.feats["keenness-of-the-stone-giant-bgg"]["senses"]


def test_echoing_soul_data_count_is_one_while_the_text_says_two(catalog, raw_feats):
    """B3 / V1. Text (catalog entries): "You have proficiency in two skills of your choice." """
    raw = dict(raw_feats)["echoing-soul-rhw"]
    assert raw["skillProficiencies"] == [{"any": 1}]
    assert "proficiency in two skills of your choice" in _text(catalog.feats["echoing-soul-rhw"])
    # FE6 overrides the count to the text's two skills (reference_data.FEAT_SKILL_PICK_COUNT_OVERRIDES).
    assert catalog.feats["echoing-soul-rhw"]["proficiency_choices"][0]["choose"] == 2


def test_harper_agent_thieves_cant_comes_from_the_override_table(catalog, raw_feats):
    """B4. The data says ``languageProficiencies: [{"thieves' cant": true}]``; the converter drops the unknown
    key and FE6's override table adds "You know Thieves' Cant." """
    raw = dict(raw_feats)["harper-agent-frhof"]
    assert raw["languageProficiencies"] == [{"thieves' cant": True}]
    assert [lang["index"] for lang in catalog.feats["harper-agent-frhof"]["languages"]] == ["thieves-cant"]
    assert catalog.feats["harper-agent-frhof"]["language_options"] is None


def test_mixed_and_2014_golden_holds_no_feat():
    """V18. F0 golden: SRD Human + Acolyte with every ASI filled by an ability combo."""
    if not GOLDEN.exists():
        pytest.skip("golden file missing")
    golden = json.load(gzip.open(GOLDEN, "rt"))
    holding = sorted(
        name for name, case in golden.items()
        if case["result"]["sheet"].get("feats") or case["result"]["sheet"].get("grantedFeats")
        or '"feat:' in json.dumps(case["draft"]))
    assert len(holding) == GOLDEN_FEAT_CASES, holding[:5]
