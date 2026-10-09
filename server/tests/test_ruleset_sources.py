"""Slice 10.1: draft.sources filters subspecies by their OWN book."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(species, sub, sources):
    return {
        "name": "T", "sources": sources,
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": species, "subspeciesId": sub, "choices": {}},
        "abilities": {"method": "standard", "base": {a: 10 for a in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
    }


def _ids(r):
    return [p["id"] for p in r["problems"]]


def test_subrace_carries_source(catalog):
    assert catalog.subraces["dwarf-phb-hill-phb"]["source"] == "PHB"
    assert catalog.subraces["dwarf-phb-duergar-mtf"]["source"] == "MTF"


def test_other_book_subspecies_warns_but_still_applies(catalog):
    # Round-2 F3: a source-hidden subspecies resolves with a warning.
    r = resolve(_draft("dwarf-phb", "dwarf-phb-duergar-mtf", ["phb"]), catalog)
    assert "unknown-subspecies" not in _ids(r)
    assert "source-hidden-subspecies" in [w["id"] for w in r["warnings"]]
    assert r["sheet"]["abilities"]["STR"] == 11


def test_subspecies_allowed_when_book_enabled(catalog):
    r = resolve(_draft("dwarf-phb", "dwarf-phb-duergar-mtf", ["phb", "mtf"]), catalog)
    assert "unknown-subspecies" not in _ids(r)
    assert r["sheet"]["abilities"]["STR"] == 11


def test_srd_subrace_always_allowed(catalog):
    r = resolve(_draft("dwarf", "hill-dwarf", ["phb"]), catalog)
    assert "unknown-subspecies" not in _ids(r)


# --- 10.2 ruleset tagging ---

def test_race_and_subrace_tags(catalog):
    assert catalog.races["dwarf-xphb"]["ruleset"] == "2024"
    assert catalog.races["dwarf-phb"]["ruleset"] == "2014"
    assert catalog.races["dwarf"]["ruleset"] == "2014"  # SRD
    assert catalog.subraces["hill-dwarf"]["ruleset"] == "2014"
    assert catalog.subraces["dwarf-phb-hill-phb"]["ruleset"] == "2014"
    for sub in catalog.subraces.values():
        parent = catalog.races[sub["race"]["index"]]
        assert sub["ruleset"] == parent["ruleset"]


def test_exactly_sixty_2024_backgrounds(catalog):
    bgs = [b for b in catalog.backgrounds.values() if b["ruleset"] == "2024"]
    assert len(bgs) == 60
    assert all(b["ability_bonus_options"] for b in bgs)
    assert catalog.backgrounds["acolyte"]["ruleset"] == "2014"
    assert all(b["ruleset"] in ("2014", "2024") for b in catalog.backgrounds.values())


def test_feat_tags(catalog):
    assert catalog.feats["alert-xphb"]["ruleset"] == "2024"
    assert catalog.feats["alert-phb"]["ruleset"] == "2014"
    assert all(f["ruleset"] == "2024" for f in catalog.feats.values() if f["source"] in {"XPHB", "FRHoF", "EFA", "ABH", "LFL"})
    assert all(f["ruleset"] == "2014" for f in catalog.feats.values() if f["source"] in {"PHB", "XGE", "TCE", "RHW"})


def test_2024_race_count(catalog):
    from collections import Counter
    c = Counter(r["ruleset"] for r in catalog.races.values())
    assert c["2024"] == 18  # XPHB 10 + EFA 5 + RHW 3


# --- 10.4 /api/catalog filtering ---

@pytest.fixture(scope="module")
def client():
    import app as app_module
    return app_module.app.test_client()


def _cat(client, query=""):
    resp = client.get("/api/catalog" + query)
    assert resp.status_code == 200
    return resp.get_json()


def test_catalog_unfiltered_is_complete(client):
    data = _cat(client)
    assert len(data["species"]) == 153
    assert len(data["backgrounds"]) == 136
    assert {"id": "PHB", "name": "Player's Handbook (2014)"}.items() <= next(s for s in data["sources"] if s["id"] == "PHB").items()
    assert all(s["count"] > 0 for s in data["sources"])
    assert all(s["id"] != "SRD" for s in data["sources"])


def test_catalog_ruleset_2014_hides_2024_species(client):
    data = _cat(client, "?ruleset=2014")
    ids = [s["id"] for s in data["species"]]
    assert "dwarf-phb" in ids and "dwarf" in ids
    assert not [i for i in ids if i.endswith("-xphb")]
    assert all(s["ruleset"] == "2014" for s in data["species"])
    assert all(b["ruleset"] == "2014" for b in data["backgrounds"])


def test_catalog_ruleset_2024_shows_only_2024_official_backgrounds(client):
    data = _cat(client, "?ruleset=2024")
    bgs = data["backgrounds"]
    assert len(bgs) == 60 and all(b["ruleset"] == "2024" for b in bgs)
    assert "acolyte" not in [b["id"] for b in bgs]
    assert "dwarf-phb" in [s["id"] for s in data["species"]]  # 2014 species stay available


def test_catalog_sources_filter(client):
    data = _cat(client, "?sources=phb")
    dwarf = next(s for s in data["species"] if s["id"] == "dwarf-phb")
    sub_ids = [s["id"] for s in dwarf["subspecies"]]
    assert "dwarf-phb-hill-phb" in sub_ids and "dwarf-phb-duergar-mtf" not in sub_ids
    assert "dwarf" in [s["id"] for s in data["species"]]  # SRD always present
    assert "aasimar-vgm" not in [s["id"] for s in data["species"]]
    assert next(s for s in data["sources"] if s["id"] == "VGM")  # picker still lists filtered-out books
    assert len(_cat(client, "?sources=phb,mtf")["species"]) > len(data["species"]) - 1


def test_catalog_selected_hidden_species_still_resolvable(client, catalog):
    # visibility only: resolve() ignores ruleset for validity
    draft = _draft("dwarf-xphb", None, [])
    draft["ruleset"] = "2014"
    assert "unknown-species" not in _ids(resolve(draft, catalog))


# --- Round-2 audit F10: 2024 + restricted sources must not leave 0 backgrounds ---

@pytest.mark.parametrize("sources", ["srd", "phb,xge,tce"])
def test_catalog_2024_with_restricted_sources_falls_back_to_srd_background(client, sources):
    data = _cat(client, f"?ruleset=2024&sources={sources}")
    assert [b["id"] for b in data["backgrounds"]] == ["acolyte"]
    assert data["backgroundsFallback"] is True


def test_catalog_2024_unrestricted_has_no_background_fallback(client):
    data = _cat(client, "?ruleset=2024")
    assert len(data["backgrounds"]) == 60 and data["backgroundsFallback"] is False
