"""Slice 8a: feats granted by a species (Human/XPHB's Versatile origin feat,
Variant Human and Custom Lineage's free feat) are a pick among the eligible
feats, not a silent no-op.

Verified against the fetched races.json: 144 races without `_copy` and 97
subraces; exactly three records carry `feats` - Custom Lineage/TCE
(`[{"any": 1}]`), Human/XPHB (`anyFromCategory` O) and Variant Human
(`human-phb-variant-phb`, `[{"any": 1}]`). Catalog feat categories: '' 108,
G 95, O 35 (10 of them from allowed-in-SOURCES books), EB 32, D 13, FS 11,
DG 9, FS:P/FS:R 1 each."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

SOURCES = ["srd", "phb", "mpmm", "tce", "scag", "erlw", "mtf", "xphb", "ftd", "egw", "vgm", "psk"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, background="acolyte", fighter_level=1, fighter_choices=None, prereqs=False, sources=None):
    return {
        "name": "T", "sources": SOURCES if sources is None else sources,
        "classes": [{"classId": "fighter", "level": fighter_level, "choices": fighter_choices or {}}],
        "background": {"id": background, "choices": {}},
        "species": species,
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
        "preferences": {"usePrerequisites": {"feats": prereqs}},
    }


def _run(catalog, species, **kw):
    return resolve(_draft(species, **kw), catalog)


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


FEAT_CID = "species:human-xphb:feat-0"


# --- catalog ---------------------------------------------------------------

def test_catalog_carries_feat_grants(catalog):
    assert catalog.races["human-xphb"]["feat_grants"] == [{"count": 1, "category": "O"}]
    assert catalog.races["custom-lineage-tce"]["feat_grants"] == [{"count": 1, "category": None}]
    assert catalog.subraces["human-phb-variant-phb"]["feat_grants"] == [{"count": 1, "category": None}]


def test_only_three_records_carry_feat_grants(catalog):
    holders = [r["index"] for r in catalog.races.values() if r.get("feat_grants")]
    holders += [s["index"] for s in catalog.subraces.values() if s.get("feat_grants")]
    assert sorted(holders) == ["custom-lineage-tce", "human-phb-variant-phb", "human-xphb"]


def test_srd_races_have_no_feat_grants(catalog):
    assert not catalog.races["human"].get("feat_grants")
    assert not catalog.races["dwarf"].get("feat_grants")


# --- the pick ---------------------------------------------------------------

def test_unpicked_human_xphb_has_a_pending_origin_feat_choice(catalog):
    res = _run(catalog, {"id": "human-xphb", "choices": {}})
    ch = _choice(res, FEAT_CID)
    assert ch and ch["status"] == "pending" and ch["count"] == 1
    assert ch["source"]["kind"] == "species" and ch["source"]["id"] == "human-xphb"
    ids = {o["id"] for o in ch["options"]}
    assert "feat:alert-xphb" in ids and "feat:skilled-xphb" in ids
    assert "feat:actor-xphb" not in ids  # General, not Origin
    expected = {k for k, f in catalog.feats.items() if f["category"] == "O" and f["source"].lower() in SOURCES}
    assert ids == {f"feat:{k}" for k in expected}
    assert len(ids) == 10


def test_selecting_a_feat_grants_it(catalog):
    res = _run(catalog, {"id": "human-xphb", "choices": {FEAT_CID: ["feat:alert-xphb"]}})
    assert _choice(res, FEAT_CID)["status"] == "resolved"
    assert "alert-xphb" in res["sheet"]["grantedFeats"]
    assert [f for f in res["sheet"]["feats"] if f["id"] == "alert-xphb"][0]["origin"] == "species"
    assert any(f["name"] == "Alert" and f["source"]["kind"] == "feat" for f in res["sheet"]["features"])
    assert res["problems"] == []


def test_feat_options_follow_the_sources_filter(catalog):
    res = _run(catalog, {"id": "human-xphb", "choices": {}}, sources=["xphb"])
    ids = {o["id"] for o in _choice(res, FEAT_CID)["options"]}
    assert ids == {f"feat:{k}" for k, f in catalog.feats.items() if f["category"] == "O" and f["source"] == "XPHB"}


def test_picked_feat_cascades_its_own_choices(catalog):
    sel = {FEAT_CID: ["feat:crafter-xphb"]}
    res = _run(catalog, {"id": "human-xphb", "choices": sel})
    sub = next(c for c in res["choices"] if c["id"].startswith(FEAT_CID + ":feat:crafter-xphb:") and "proficiency-choice" in c["id"])
    assert sub["source"]["kind"] == "feat" and sub["status"] == "pending" and sub["count"] == 3
    tools = [o["id"] for o in sub["options"]][:3]
    sel[sub["id"]] = tools
    res = _run(catalog, {"id": "human-xphb", "choices": sel})
    assert set(tools) <= set(res["sheet"]["proficiencies"]["tools"])


def test_magic_initiate_offers_its_spell_list_choice(catalog):
    res = _run(catalog, {"id": "human-xphb", "choices": {FEAT_CID: ["feat:magic-initiate-xphb"]}})
    assert _choice(res, FEAT_CID + ":feat:magic-initiate-xphb:spell-variant") is not None


# --- duplicates -------------------------------------------------------------

def test_background_feat_makes_the_same_species_pick_unavailable(catalog):
    res = _run(catalog, {"id": "human-xphb", "choices": {}}, background="criminal-xphb")
    assert "alert-xphb" in res["sheet"]["grantedFeats"] or "alert" in res["sheet"]["grantedFeats"]
    opt = next(o for o in _choice(res, FEAT_CID)["options"] if o["id"] == "feat:alert-xphb")
    assert opt["disabled"] and opt["disabledReason"] == "already taken"
    # a hand-edited draft naming it anyway: not applied, reported
    res = _run(catalog, {"id": "human-xphb", "choices": {FEAT_CID: ["feat:alert-xphb"]}}, background="criminal-xphb")
    held = [g for g in res["sheet"]["grantedFeats"] if g in ("alert", "alert-xphb")]
    assert len(held) == 1
    assert any(p["id"].startswith("feat-duplicate-alert-xphb-") for p in res["problems"])
    assert _choice(res, FEAT_CID)["status"] == "pending"


def test_species_feat_blocks_the_same_feat_at_an_asi_level(catalog):
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb",
               "choices": {"species:human-phb:subspecies:human-phb-variant-phb:feat-0": ["feat:actor-xphb"]}}
    res = _run(catalog, species, fighter_level=4)
    opts = {o["id"]: o for o in _choice(res, "species:human-phb:subspecies:human-phb-variant-phb:feat-0")["options"]}
    assert "feat:actor-xphb" in opts  # category G is offered under "any"
    asi = {o["id"]: o for o in _choice(res, "class:fighter:4:asi")["options"]}
    assert asi["feat:actor-xphb"]["disabled"] and asi["feat:actor-xphb"]["disabledReason"] == "already taken"
    assert "actor-xphb" in res["sheet"]["grantedFeats"]
    assert res["sheet"]["abilities"]["CHA"] == 11  # the feat's fixed +1


def test_species_pick_wins_over_a_later_asi_pick_of_the_same_feat(catalog):
    sid = "species:human-phb:subspecies:human-phb-variant-phb:feat-0"
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb", "choices": {sid: ["feat:actor-xphb"]}}
    res = _run(catalog, species, fighter_level=4, fighter_choices={"class:fighter:4:asi": ["feat:actor-xphb"]})
    assert res["sheet"]["grantedFeats"].count("actor-xphb") == 1
    assert any(p["id"].startswith("feat-duplicate-actor-xphb-") for p in res["problems"])


def test_any_pool_excludes_expanded_categories(catalog):
    res = _run(catalog, {"id": "custom-lineage-tce", "choices": {}})
    ch = _choice(res, "species:custom-lineage-tce:feat-0")
    ids = {o["id"] for o in ch["options"]}
    cats = {catalog.feats[i[len("feat:"):]]["category"] for i in ids}
    assert cats <= {"", "G", "O"}
    assert "feat:ability-score-improvement-xphb" not in ids
    allowed = {k for k, f in catalog.feats.items()
               if f["category"] in ("", "G", "O") and f["name"] != "Ability Score Improvement"
               and f["source"].lower() in SOURCES}
    assert ids == {f"feat:{k}" for k in allowed}
    # Grouped (display order per ruleset), then name/source inside a group.
    keys = [(o["group"], catalog.feats[o["id"][5:]]["name"], catalog.feats[o["id"][5:]]["source"]) for o in ch["options"]]
    assert [o["group"] for o in ch["options"]][0] == "general"
    for g in {k[0] for k in keys}:
        in_group = [k[1:] for k in keys if k[0] == g]
        assert in_group == sorted(in_group)


def test_prerequisites_disable_species_feat_options(catalog):
    res = _run(catalog, {"id": "custom-lineage-tce", "choices": {}}, prereqs=True)
    opts = {o["id"]: o for o in _choice(res, "species:custom-lineage-tce:feat-0")["options"]}
    assert opts["feat:actor-xphb"]["disabled"]  # CHA 13 required, base 10
    assert "prerequisite" in opts["feat:actor-xphb"]["disabledReason"]
    assert not opts["feat:alert-xphb"].get("disabled")


# --- stale picks ------------------------------------------------------------

def test_changing_the_feat_prunes_the_old_feats_subchoice(catalog):
    sel = {FEAT_CID: ["feat:crafter-xphb"]}
    res = _run(catalog, {"id": "human-xphb", "choices": dict(sel)})
    sub_id = next(c["id"] for c in res["choices"] if "proficiency-choice" in c["id"] and c["id"].startswith(FEAT_CID))
    sel[sub_id] = ["carpenters-tools", "masons-tools", "potters-tools"]
    sel[FEAT_CID] = ["feat:alert-xphb"]
    res = _run(catalog, {"id": "human-xphb", "choices": sel})
    assert sub_id in [p["choiceId"] for p in res["pruned"]]
    assert "carpenters-tools" not in res["sheet"]["proficiencies"]["tools"]


# --- unaffected -------------------------------------------------------------

def test_srd_only_sources_offer_no_species_feat(catalog):
    res = _run(catalog, {"id": "human", "choices": {}}, sources=["srd"])
    assert not [c for c in res["choices"] if ":feat-" in c["id"]]


def test_races_without_feat_grants_are_unchanged(catalog):
    res = _run(catalog, {"id": "elf-xphb", "choices": {}})
    assert not [c for c in res["choices"] if ":feat-" in c["id"]]
