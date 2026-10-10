"""S3: Way of the Four Elements grants Elemental Attunement automatically.

RAW (PHB p.81): "You learn the Elemental Attunement discipline" at Monk 3 and
then pick further disciplines (2 known at 3, 3 at 6, 4 at 11, 5 at 17 in the
class table; Elemental Attunement is one of the 2 at level 3).

Cases distinguished: converter carries `required`; level 3 offers 1 pick and
not the attunement option; level 6 offers 2 picks; the sheet lists attunement
first; an old draft that stored attunement silently drops it (no pruned entry,
no over-selected problem); other optional progressions (Battle Master) have no
`required` and are unchanged.

Raw facts verified by script over class-monk.json: only Way of the Four
Elements PHB has `required` ({"3": ["Elemental Attunement|PHB"]}); the option
id is `opt-elemental-attunement-phb` (slug rule of convert_optional_features).
"""
import pytest

from catalog.official import subclasses as sub_mod
from catalog.official_source import has_official_classes
from catalog.loader import load
from engine.resolve import resolve

needs_official = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

ATT = "opt-elemental-attunement-phb"
FEATURE = "four-elements-phb-3-way-of-the-four-elements"
CID = f"class:monk:3:feature:{FEATURE}"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(level, picks=None, cls="monk", sub="four-elements-phb"):
    return {
        "name": "T", "sources": [],
        "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": {CID: picks} if picks else {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 16}},
    }


def _choice(res):
    return next(c for c in res["choices"] if c["id"] == CID)


def test_converter_maps_required_names_to_option_ids():
    sub = {"name": "Elements", "shortName": "Elements", "source": "PHB", "className": "Monk", "classSource": "PHB",
           "edition": "classic", "subclassFeatures": ["Core|Monk||Elements||3"],
           "optionalfeatureProgression": [{"name": "Disciplines", "featureType": ["ED"],
                                           "progression": {"3": 2, "6": 3},
                                           "required": {"3": ["Elemental Attunement|PHB"]}}]}
    feat = {"name": "Core", "source": "PHB", "className": "Monk", "classSource": "PHB", "subclassShortName": "Elements",
            "subclassSource": "PHB", "level": 3, "entries": ["Core text."]}
    opts = [{"name": "Elemental Attunement", "source": "PHB", "featureType": ["ED"], "entries": ["x"]},
            {"name": "Fangs", "source": "PHB", "featureType": ["ED"], "entries": ["y"]}]
    _, feats, _ = sub_mod.convert_subclasses([sub], [feat], set(), lambda s: None, opts)
    spec = feats["elements-phb-3-core"]["feature_specific"]["optional_progression"]
    assert spec["required"] == {"3": ["opt-elemental-attunement-phb"]}


def test_converter_without_required_has_no_required_key():
    sub = {"name": "M", "shortName": "M", "source": "PHB", "className": "Fighter", "classSource": "PHB",
           "edition": "classic", "subclassFeatures": ["Core|Fighter||M||3"],
           "optionalfeatureProgression": [{"name": "Man", "featureType": ["MV:B"], "progression": {"3": 3}}]}
    feat = {"name": "Core", "source": "PHB", "className": "Fighter", "classSource": "PHB", "subclassShortName": "M",
            "subclassSource": "PHB", "level": 3, "entries": ["t"]}
    opts = [{"name": "Riposte", "source": "PHB", "featureType": ["MV:B"], "entries": ["z"]}]
    _, feats, _ = sub_mod.convert_subclasses([sub], [feat], set(), lambda s: None, opts)
    assert "required" not in feats["m-phb-3-core"]["feature_specific"]["optional_progression"]


@needs_official
def test_real_data_required_only_on_four_elements(catalog):
    with_req = {i: f["feature_specific"]["optional_progression"]["required"] for i, f in catalog.features.items()
                if (f.get("feature_specific") or {}).get("optional_progression", {}).get("required")}
    assert with_req == {FEATURE: {"3": [ATT]}}
    assert ATT in catalog.features


@needs_official
def test_level_3_offers_one_pick_without_attunement(catalog):
    ch = _choice(resolve(_draft(3), catalog))
    assert ch["count"] == 1
    assert ATT not in [o["id"] for o in ch["options"]]
    assert len(ch["options"]) == 16
    assert ch["granted"] == [{"id": ATT, "label": "Elemental Attunement"}]
    assert "Elemental Attunement is granted automatically." in ch["description"]


@needs_official
def test_level_6_offers_two_picks(catalog):
    assert _choice(resolve(_draft(6), catalog))["count"] == 2


@needs_official
def test_sheet_feature_lists_attunement_first(catalog):
    opts = [o["id"] for o in _choice(resolve(_draft(3), catalog))["options"] if not o.get("disabled")]
    res = resolve(_draft(3, [opts[0]]), catalog)
    feature = next(f for f in res["sheet"]["features"] if f["name"] == "Way of the Four Elements")
    assert feature["choice"][0] == "Elemental Attunement"
    assert len(feature["choice"]) == 2
    assert _choice(res)["status"] == "resolved"


@needs_official
def test_sheet_feature_lists_attunement_even_without_picks(catalog):
    res = resolve(_draft(3), catalog)
    feature = next(f for f in res["sheet"]["features"] if f["name"] == "Way of the Four Elements")
    assert feature["choice"] == ["Elemental Attunement"]


@needs_official
def test_old_draft_with_attunement_is_filtered_silently(catalog):
    opts = [o["id"] for o in _choice(resolve(_draft(3), catalog))["options"] if not o.get("disabled")]
    res = resolve(_draft(3, [ATT, opts[0]]), catalog)
    assert _choice(res)["selected"] == [opts[0]]
    assert _choice(res)["status"] == "resolved"
    assert not [p for p in res["pruned"] if p["choiceId"] == CID]
    assert not [p for p in res["problems"] if "over-selected" in p["id"]]


@needs_official
def test_battle_master_unchanged(catalog):
    cid = "class:fighter:3:feature:battle-master-phb-3-battle-master"
    d = _draft(3, cls="fighter", sub="battle-master-phb")
    ch = next(c for c in resolve(d, catalog)["choices"] if c["id"] == cid)
    assert ch["count"] == 3 and len(ch["options"]) == 23 and "granted" not in ch


@needs_official
def test_internal_count_by_level_key_is_not_in_the_api_choices(catalog):
    """F2-C: the internal template key never reaches resolve()'s choices."""
    res = resolve(_draft(3), catalog)
    assert "count_by_level" not in _choice(res)
    assert all("count_by_level" not in c for c in res["choices"])
