"""SK10 (Y2): option dicts carry `source` (book code, "SRD" when the record has none); labels never change."""
import re

import pytest

from catalog.loader import load
from catalog.official_source import has_official
from engine.option_source import annotate_choices
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="official data not fetched on this machine")

SUFFIX = re.compile(r"\s\(([A-Z][A-Z0-9]{1,7})\)$")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(ruleset, classes, sources=(), **extra):
    return {"ruleset": ruleset, "sources": list(sources),
            "classes": [{"classId": c, "level": lvl, "choices": {}} for c, lvl in classes],
            "species": {"id": "human"}, "background": {"id": "acolyte"}, **extra}


def _card(result, cid):
    return next(c for c in result["choices"] if c["id"] == cid)


def test_every_option_of_the_mixed_fighter_4_asi_card_has_a_source(catalog):
    opts = _card(resolve(_draft("mixed", [("fighter", 4)]), catalog), "class:fighter:4:asi")["options"]
    assert len(opts) > 150
    assert all(isinstance(o.get("source"), str) and o["source"] for o in opts)


def test_the_unlabelled_feat_options_get_their_real_code(catalog):
    opts = _card(resolve(_draft("mixed", [("fighter", 4)]), catalog), "class:fighter:4:asi")["options"]
    unlabelled = [o for o in opts if o["id"].startswith("feat:") and not SUFFIX.search(o["label"])]
    assert len(unlabelled) >= 100  # the "Без етикет" bucket of the picker
    for o in unlabelled:
        assert o["source"] == (catalog.feats[o["id"][5:]].get("source") or "SRD")
    assert {o["source"] for o in unlabelled} >= {"PHB", "XPHB"}


def test_labelled_options_source_equals_the_label_code(catalog):
    opts = _card(resolve(_draft("mixed", [("fighter", 4)]), catalog), "class:fighter:4:asi")["options"]
    labelled = [o for o in opts if SUFFIX.search(o["label"])]
    assert labelled
    for o in labelled:
        assert SUFFIX.search(o["label"]).group(1) == o["source"]


def test_asi_steps_are_srd(catalog):
    opts = _card(resolve(_draft("2024", [("fighter", 4)]), catalog), "class:fighter:4:asi")["options"]
    steps = [o for o in opts if not o["id"].startswith("feat:")]
    assert len(steps) == 21 and {o["source"] for o in steps} == {"SRD"}


def test_srd_only_sources_give_srd_on_srd_feats(catalog):
    r = resolve(_draft("mixed", [("fighter", 4)], sources=["srd"]), catalog)
    for o in _card(r, "class:fighter:4:asi")["options"]:
        assert o["source"] == "SRD" or catalog.feats[o["id"][5:]].get("source")


def test_spell_card_options_have_the_spell_source(catalog):
    r = resolve(_draft("mixed", [("wizard", 3)]), catalog)
    card = _card(r, "class:wizard:spells-cantrips")
    assert card["options"]
    for o in card["options"]:
        assert o["source"] == (catalog.spells[o["id"]].get("source") or "SRD")
    assert any(o["source"] == "SRD" for o in card["options"])


def test_warlock_invocation_and_sorcerer_metamagic_options(catalog):
    r = resolve(_draft("mixed", [("warlock", 5)]), catalog)
    inv = _card(r, "class:warlock:2:invocations:eldritch-invocations")["options"]
    assert inv and all(o["source"] == (catalog.features[o["id"]].get("source") or "SRD") for o in inv)
    assert any(o["source"] == "SRD" for o in inv)
    r = resolve(_draft("mixed", [("sorcerer", 3)]), catalog)
    meta = [c for c in r["choices"] if c["id"].startswith("class:sorcerer:3:feature:metamagic")]
    assert meta and all("source" in o for c in meta for o in c["options"])


def test_subclass_text_option_cards_use_the_option_or_feature_source(catalog):
    d = _draft("mixed", [("barbarian", 3)])
    d["classes"][0]["subclassId"] = "totem-warrior-phb"
    card = _card(resolve(d, catalog), "class:barbarian:3:feature:totem-warrior-phb-3-totem-spirit")
    by_id = {o["id"].split("--")[1]: o["source"] for o in card["options"]}
    assert by_id["bear"] == "PHB" and by_id["elk"] == "SCAG"


def test_2024_subclass_option_cards(catalog):
    d = _draft("2024", [("ranger", 3)])
    d["classes"][0]["subclassId"] = "hunter-xphb"
    r = resolve(d, catalog)
    cards = [c for c in r["choices"] if "--" in (c["options"][0]["id"] if c["options"] else "")]
    assert cards
    for c in cards:
        assert all(o["source"] == "XPHB" for o in c["options"])


def test_non_book_options_get_no_source(catalog):
    r = resolve(_draft("mixed", [("fighter", 1)]), catalog)
    skills = _card(r, "class:fighter:1:prof-choice-0")["options"]
    assert skills and all("source" not in o for o in skills)
    equip = [c for c in r["choices"] if c["source"]["kind"] == "equipment"]
    assert equip and all("source" not in o for c in equip for o in c["options"])


def test_labels_are_not_changed_by_the_pass(catalog):
    r = resolve(_draft("mixed", [("fighter", 4)]), catalog)
    for c in r["choices"]:
        for o in c["options"]:
            stripped = {k: v for k, v in o.items() if k != "source"}
            assert annotate_choices(catalog, [{**c, "options": [stripped]}])[0]["options"][0]["label"] == o["label"]


def test_the_pass_does_not_mutate_its_input(catalog):
    choice = {"id": "class:fighter:4:asi", "source": {"kind": "class"}, "options": [{"id": "feat:alert-phb", "label": "Alert"}]}
    out = annotate_choices(catalog, [choice])
    assert "source" not in choice["options"][0] and out[0]["options"][0]["source"] == "PHB"


def test_no_book_option_is_left_without_a_source_in_a_wide_sample(catalog):
    """Every option id that is a feat / spell / feature record on a non-equipment, non-skill card has a source."""
    drafts = [_draft("mixed", [(c, 11)]) for c in ("wizard", "warlock", "sorcerer", "bard", "cleric", "ranger", "rogue", "fighter")]
    drafts += [_draft("2024", [(c, 5)]) for c in ("wizard", "warlock", "bard", "paladin", "druid")]
    for d in drafts:
        for c in resolve(d, catalog)["choices"]:
            if c["source"]["kind"] == "equipment":
                continue
            for o in c["options"]:
                oid = o["id"]
                book = (oid.startswith("feat:") or oid in catalog.features or "--" in oid
                        or (oid in catalog.spells and not oid.startswith("skill-")))
                assert ("source" in o) == book or c["id"].endswith(":asi"), (c["id"], oid)
