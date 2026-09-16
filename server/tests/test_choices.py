import json
from pathlib import Path

from catalog.choices import build_choice_options, build_choice_template

_DATA_DIR = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"


def _load(name):
    with open(_DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def test_options_array_resolves_to_explicit_options():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["proficiency_choices"][0]
    options = build_choice_options(envelope["from"])
    assert options is not None
    ids = {o["id"] for o in options}
    assert ids == {
        "skill-acrobatics", "skill-animal-handling", "skill-athletics",
        "skill-history", "skill-insight", "skill-intimidation",
        "skill-perception", "skill-survival",
    }
    labels = {o["label"] for o in options}
    assert "Skill: Athletics" in labels


def test_resource_list_languages_resolves_from_reference_data():
    backgrounds = _load("5e-SRD-Backgrounds.json")
    acolyte = backgrounds[0]
    envelope = acolyte["language_options"]
    assert envelope["from"]["option_set_type"] == "resource_list"
    options = build_choice_options(envelope["from"])
    assert options is not None
    assert len(options) == 16
    ids = {o["id"] for o in options}
    assert "celestial" in ids
    assert "draconic" in ids


def test_equipment_category_is_unresolved_in_phase_1():
    backgrounds = _load("5e-SRD-Backgrounds.json")
    acolyte = backgrounds[0]
    envelope = acolyte["starting_equipment_options"][0]
    assert envelope["from"]["option_set_type"] == "equipment_category"
    assert build_choice_options(envelope["from"]) is None


def test_build_choice_template_fighting_style_shape():
    features = _load("5e-SRD-Features.json")
    fighting_style = next(f for f in features if f["index"] == "fighter-fighting-style")
    # The subfeature_options envelope itself carries no 'desc' key (verified
    # directly against the JSON — only proficiency_choices envelopes do);
    # the description text lives on the parent feature. build_choice_template
    # never guesses at this — the caller (engine/resolve.py, Task 5) always
    # passes it explicitly, which is exactly what this test exercises.
    envelope = fighting_style["feature_specific"]["subfeature_options"]
    assert "desc" not in envelope
    source = {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1}
    tpl = build_choice_template(
        envelope, "class:fighter:1:feature:fighter-fighting-style", source, "Fighting Style",
        description=" ".join(fighting_style["desc"]),
    )
    assert tpl is not None
    assert tpl["id"] == "class:fighter:1:feature:fighter-fighting-style"
    assert tpl["source"] == source
    assert tpl["label"] == "Fighting Style"
    assert tpl["count"] == 1
    assert "specialty" in tpl["description"]
    option_ids = {o["id"] for o in tpl["options"]}
    assert "fighter-fighting-style-archery" in option_ids
    assert "fighter-fighting-style-defense" in option_ids


def test_build_choice_template_returns_none_when_unresolvable():
    backgrounds = _load("5e-SRD-Backgrounds.json")
    acolyte = backgrounds[0]
    envelope = acolyte["starting_equipment_options"][0]
    source = {"kind": "background", "id": "acolyte", "label": "Acolyte"}
    assert build_choice_template(envelope, "background:acolyte:equipment", source, "Equipment") is None


def test_build_choice_template_joins_list_desc_into_a_string():
    features = _load("5e-SRD-Features.json")
    fighting_style = next(f for f in features if f["index"] == "fighter-fighting-style")
    assert isinstance(fighting_style["desc"], list)
    envelope = fighting_style["feature_specific"]["subfeature_options"]
    source = {"kind": "class", "id": "fighter", "label": "Fighter", "level": 1}
    tpl = build_choice_template(envelope, "x", source, "Fighting Style", description=" ".join(fighting_style["desc"]))
    assert isinstance(tpl["description"], str)


def test_multiple_bundle_of_counted_references_resolves_to_one_option():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][0]  # "(a) chain mail or (b) leather armor, longbow, and 20 arrows"
    options = build_choice_options(envelope["from"])
    assert options is not None
    assert len(options) == 2
    ids = {o["id"] for o in options}
    assert "chain-mail" in ids
    assert "leather-armor+longbow+arrow" in ids
    bundle = next(o for o in options if o["id"] == "leather-armor+longbow+arrow")
    assert "Leather Armor" in bundle["label"]
    assert "Longbow" in bundle["label"]
    assert "20x Arrow" in bundle["label"]


def test_multiple_bundle_with_a_nested_choice_is_dropped_not_faked():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][1]  # "(a) a martial weapon and a shield or (b) two martial weapons"
    # Both options in this envelope nest an option_type "choice" somewhere —
    # neither is resolvable in this phase, so the whole envelope resolves to
    # no options at all, which build_choice_options reports as None (its
    # established "nothing resolvable" signal, same as an all-empty
    # options_array).
    assert build_choice_options(envelope["from"]) is None


def test_simple_multiple_bundle_alongside_a_plain_counted_reference():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][2]  # "(a) a light crossbow and 20 bolts or (b) two handaxes"
    options = build_choice_options(envelope["from"])
    assert options is not None
    ids = {o["id"] for o in options}
    assert "crossbow-light+crossbow-bolt" in ids
    assert "handaxe" in ids


def test_two_plain_counted_reference_options_both_resolve():
    classes = _load("5e-SRD-Classes.json")
    fighter = next(c for c in classes if c["index"] == "fighter")
    envelope = fighter["starting_equipment_options"][3]  # "(a) a dungeoneer's pack or (b) an explorer's pack"
    options = build_choice_options(envelope["from"])
    assert options is not None
    ids = {o["id"] for o in options}
    assert ids == {"dungeoneers-pack", "explorers-pack"}
