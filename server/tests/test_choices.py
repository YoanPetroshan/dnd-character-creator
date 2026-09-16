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
