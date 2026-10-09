"""S4: build-time option choices carried in feature text (decision D10).

RAW: Totem Warrior (PHB p.50) picks a totem animal at 3 (Totem Spirit), 6
(Aspect of the Beast) and 14 (Totemic Attunement); each pick is independent
(the same animal or a different one). Storm Herald (XGE p.9) picks one aura
environment at 3 (Storm Aura); Storm Soul / Raging Storm follow it and are
NOT separate choices. Per-rest choices (Third Eye, Master Transmuter) and
grant-all blocks (Psionic Power) are not build-time and get no card.

Cases distinguished: converter emits `text_options` only for allowlisted ids
and keeps the text in desc; real-data option ids/counts; a pick shows in
sheet.features; Third Eye has no card; level-down prunes the Aspect pick;
unselected subclass shows no card.

Raw facts verified by script: the Totem Spirit block lists Bear, Eagle, Elk,
Tiger, Wolf (Elk/Tiger are SCAG children inside the same block, not a
separate entry), count 1; the Storm Aura block has no `count` (default 1) and
Desert/Sea/Tundra.
"""
import pytest

from catalog.official import subclasses as sub_mod
from catalog.official_source import has_official_classes
from catalog.loader import load
from catalog.reference_data import FEATURE_TEXT_CHOICES
from engine.resolve import resolve

needs_official = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

TS = "totem-warrior-phb-3-totem-spirit"
AB = "totem-warrior-phb-6-aspect-of-the-beast"
TA = "totem-warrior-phb-14-totemic-attunement"
SA = "storm-herald-xge-3-storm-aura"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(level, picks=None, cls="barbarian", sub="totem-warrior-phb"):
    return {
        "name": "T", "sources": [],
        "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": picks or {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 10}},
    }


def _cid(lvl, fid, cls="barbarian"):
    return f"class:{cls}:{lvl}:feature:{fid}"


def _choice(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def test_allowlist_ids():
    assert FEATURE_TEXT_CHOICES == {TS: 1, AB: 1, TA: 1, SA: 1}


def _convert(feature_id_name, level=3):
    sub = {"name": "Tot", "shortName": "Tot", "source": "PHB", "className": "Barbarian", "classSource": "PHB",
           "edition": "classic", "subclassFeatures": [f"{feature_id_name}|Barbarian||Tot||{level}"]}
    top = {"name": feature_id_name, "source": "PHB", "className": "Barbarian", "classSource": "PHB",
           "subclassShortName": "Tot", "subclassSource": "PHB", "level": level,
           "entries": ["Intro.", {"type": "options", "count": 1, "entries": [
               {"type": "refSubclassFeature", "subclassFeature": f"Bear|Barbarian||Tot||{level}"},
               {"type": "refSubclassFeature", "subclassFeature": f"Wolf Pack|Barbarian||Tot||{level}"}]}]}
    kids = [{"name": n, "source": "PHB", "className": "Barbarian", "classSource": "PHB",
             "subclassShortName": "Tot", "subclassSource": "PHB", "level": level,
             "entries": [f"{n} text."]} for n in ("Bear", "Wolf Pack")]
    _, feats, _ = sub_mod.convert_subclasses([sub], [top] + kids, set(), lambda s: None)
    return feats


def test_converter_emits_text_options_only_for_allowlisted(monkeypatch):
    monkeypatch.setitem(FEATURE_TEXT_CHOICES, "tot-phb-3-demo", 1)
    feats = _convert("Demo")
    spec = feats["tot-phb-3-demo"]["feature_specific"]["text_options"]
    assert spec["count"] == 1
    assert [o["id"] for o in spec["options"]] == ["tot-phb-3-demo--bear", "tot-phb-3-demo--wolf-pack"]
    assert spec["options"][0]["name"] == "Bear" and "Bear text." in " ".join(spec["options"][0]["desc"])
    assert "Bear text." in " ".join(feats["tot-phb-3-demo"]["desc"])  # still inlined


def test_converter_not_allowlisted_has_no_text_options():
    feats = _convert("Other")
    assert "feature_specific" not in feats["tot-phb-3-other"]


@needs_official
def test_real_data_options(catalog):
    ts = catalog.features[TS]["feature_specific"]["text_options"]
    assert ts["count"] == 1
    assert [o["id"] for o in ts["options"]] == [f"{TS}--{n}" for n in ("bear", "eagle", "elk", "tiger", "wolf")]
    assert [o["name"] for o in ts["options"]] == ["Bear", "Eagle", "Elk", "Tiger", "Wolf"]
    assert "resistance to all damage except psychic" in " ".join(ts["options"][0]["desc"])
    for fid in (AB, TA):
        assert [o["name"] for o in catalog.features[fid]["feature_specific"]["text_options"]["options"]] == \
            ["Bear", "Eagle", "Elk", "Tiger", "Wolf"]
    sa = catalog.features[SA]["feature_specific"]["text_options"]
    assert sa["count"] == 1 and [o["name"] for o in sa["options"]] == ["Desert", "Sea", "Tundra"]
    assert sa["options"][2]["id"] == f"{SA}--tundra"


@needs_official
def test_only_allowlisted_features_carry_text_options(catalog):
    carriers = {i for i, f in catalog.features.items() if (f.get("feature_specific") or {}).get("text_options")}
    assert carriers == set(FEATURE_TEXT_CHOICES)


@needs_official
def test_totem_spirit_card_and_sheet(catalog):
    res = resolve(_draft(3), catalog)
    ch = _choice(res, _cid(3, TS))
    assert ch["count"] == 1 and ch["status"] == "pending"
    assert [o["label"] for o in ch["options"]] == ["Bear", "Eagle", "Elk", "Tiger", "Wolf"]
    assert ch["options"][0]["description"].startswith("While raging")
    assert _choice(res, _cid(6, AB)) is None  # not reached yet
    res = resolve(_draft(3, {_cid(3, TS): [f"{TS}--bear"]}), catalog)
    assert _choice(res, _cid(3, TS))["status"] == "resolved"
    feature = next(f for f in res["sheet"]["features"] if f["name"] == "Totem Spirit")
    assert feature["choice"] == ["Bear"]


@needs_official
def test_aspect_and_attunement_cards(catalog):
    assert _choice(resolve(_draft(6), catalog), _cid(6, AB))["count"] == 1
    res = resolve(_draft(14), catalog)
    assert _choice(res, _cid(14, TA)) and _choice(res, _cid(6, AB)) and _choice(res, _cid(3, TS))


@needs_official
def test_same_animal_may_be_picked_at_each_level(catalog):
    picks = {_cid(3, TS): [f"{TS}--bear"], _cid(6, AB): [f"{AB}--bear"]}
    res = resolve(_draft(6, picks), catalog)
    assert _choice(res, _cid(6, AB))["selected"] == [f"{AB}--bear"]
    assert _choice(res, _cid(6, AB))["status"] == "resolved"


@needs_official
def test_storm_herald_card(catalog):
    res = resolve(_draft(3, sub="storm-herald-xge"), catalog)
    ch = _choice(res, _cid(3, SA))
    assert [o["label"] for o in ch["options"]] == ["Desert", "Sea", "Tundra"]
    assert not any("storm-soul" in c["id"] or "raging-storm" in c["id"] for c in resolve(_draft(14, sub="storm-herald-xge"), catalog)["choices"])


@needs_official
def test_no_card_without_the_subclass(catalog):
    res = resolve(_draft(6, sub="berserker"), catalog)
    assert not any(TS in c["id"] or AB in c["id"] for c in res["choices"])
    res = resolve(_draft(6, sub=None), catalog)
    assert not any(TS in c["id"] for c in res["choices"])


@needs_official
def test_third_eye_has_no_card(catalog):
    res = resolve(_draft(10, cls="wizard", sub="divination"), catalog)
    assert not any("third-eye" in c["id"] for c in res["choices"])


@needs_official
def test_level_down_prunes_aspect_pick(catalog):
    picks = {_cid(3, TS): [f"{TS}--wolf"], _cid(6, AB): [f"{AB}--eagle"]}
    res = resolve(_draft(6, picks), catalog)
    assert _choice(res, _cid(6, AB))["selected"] == [f"{AB}--eagle"]
    res = resolve(_draft(5, picks), catalog)
    assert _choice(res, _cid(6, AB)) is None
    assert _choice(res, _cid(3, TS))["selected"] == [f"{TS}--wolf"]
    assert any(_cid(6, AB) in str(p) for p in res.get("pruned", []))
