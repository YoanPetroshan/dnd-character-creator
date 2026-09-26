import yaml

from app import app
from catalog.official_source import has_official


import pytest


@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _fighter_acolyte_human_draft():
    return {
        "name": "Torvin Bracewell",
        "sources": ["srd"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},
        "details": {},
    }


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_resolve_empty_draft_is_valid_not_an_error(client):
    resp = client.post("/api/resolve", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["problems"] == []
    assert body["choices"] == []


def test_resolve_real_draft_returns_computed_values(client):
    resp = client.post("/api/resolve", json=_fighter_acolyte_human_draft())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["problems"] == []
    assert body["sheet"]["classes"][0]["id"] == "fighter"
    assert body["derived"]["hitPointMax"] == 12
    assert body["derived"]["armorClass"] == 12
    skill_choice = next(c for c in body["choices"] if c["label"] == "Skill Proficiencies")
    insight = next(o for o in skill_choice["options"] if o["id"] == "skill-insight")
    assert insight["disabled"] is True


def test_catalog_endpoint_lists_all_classes_backgrounds_species(client):
    resp = client.get("/api/catalog")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["classes"]) == 12
    # Bundled SRD species/background counts are exactly 9/1 — byte-identical
    # when official sourcebook data hasn't been fetched on this machine. When
    # it has (as on this dev machine), catalog/loader.py merges in the wider
    # official race/background lists, so these become lower bounds instead
    # (see test_loader.py's own test_load_returns_expected_counts for the
    # same split).
    if has_official():
        assert len(body["species"]) >= 9
        assert len(body["backgrounds"]) >= 100  # 1 SRD + ~135 official (Phase 4b Task 1)
    else:
        assert len(body["species"]) == 9
        assert len(body["backgrounds"]) == 1
    fighter = next(c for c in body["classes"] if c["id"] == "fighter")
    assert fighter["hitDie"] == 10
    dwarf = next(s for s in body["species"] if s["id"] == "dwarf")
    assert dwarf["subspecies"] == [{"id": "hill-dwarf", "name": "Hill Dwarf"}]
    # Bundled SRD species/backgrounds have no 'source' field of their own
    # (implicitly SRD) — the catalog endpoint still exposes the key, just
    # empty, so the frontend can group consistently either way.
    assert dwarf["source"] == ""
    acolyte = next(b for b in body["backgrounds"] if b["id"] == "acolyte")
    assert acolyte["source"] == ""
    if has_official():
        # aasimar-vgm (official_source.py's own id convention): 'source'
        # carries the real book abbreviation for frontend grouping.
        aasimar = next((s for s in body["species"] if s["id"] == "aasimar-vgm"), None)
        assert aasimar is not None
        assert aasimar["source"] == "VGM"


def test_catalog_class_detail_endpoint(client):
    resp = client.get("/api/catalog/class/fighter")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Fighter"


def test_catalog_class_detail_endpoint_404s_for_unknown_id(client):
    resp = client.get("/api/catalog/class/not-a-class")
    assert resp.status_code == 404


def test_catalog_class_includes_level_feature_counts(client):
    resp = client.get("/api/catalog/class/fighter")
    body = resp.get_json()
    assert "levelFeatureCounts" in body
    assert body["levelFeatureCounts"]["1"] == 2  # fighter-fighting-style, second-wind
    assert body["levelFeatureCounts"]["3"] == 1  # martial-archetype
    assert len(body["levelFeatureCounts"]) == 20


def test_catalog_class_includes_subclass_unlock_level(client):
    resp = client.get("/api/catalog/class/cleric")
    assert resp.get_json()["subclassUnlockLevel"] == 1
    resp = client.get("/api/catalog/class/fighter")
    assert resp.get_json()["subclassUnlockLevel"] == 3


def test_catalog_background_detail_endpoint(client):
    resp = client.get("/api/catalog/background/acolyte")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Acolyte"


def test_catalog_species_detail_endpoint_includes_subspecies(client):
    resp = client.get("/api/catalog/species/dwarf")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Dwarf"
    assert [s["index"] for s in body["subspecies"]] == ["hill-dwarf"]


def test_export_yaml_endpoint_returns_valid_yaml(client):
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["choices"] = {
        "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"],
        "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
    }
    # Fighter now offers 3 resolvable equipment choices (Task 3) — all must
    # be selected for the draft to have no pending choices left to export.
    draft["equipment"]["choices"] = {
        "class:fighter:1:equipment-choice-0": ["chain-mail"],
        "class:fighter:1:equipment-choice-2": ["handaxe"],
        "class:fighter:1:equipment-choice-3": ["explorers-pack"],
    }
    draft["background"]["choices"] = {"background:acolyte:languages": ["dwarvish", "elvish"]}
    draft["species"]["choices"] = {"species:human:languages": ["giant"]}
    resp = client.post("/api/export/yaml", json=draft)
    assert resp.status_code == 200
    assert resp.mimetype == "application/x-yaml"
    doc = yaml.safe_load(resp.data.decode("utf-8"))
    assert doc["name"] == "Torvin Bracewell"
    assert doc["hitPointMax"] == 12


def test_export_yaml_rejects_a_draft_with_problems(client):
    # "multiclass-unsupported" no longer exists as of Phase 3b-i (resolve()
    # now supports multiple classes for real) — an unknown class id is used
    # here instead to exercise the same "rejects a draft with problems" path.
    resp = client.post("/api/export/yaml", json={
        "classes": [{"classId": "not-a-class", "level": 1, "choices": {}}],
    })
    assert resp.status_code == 400
    assert any(p["id"] == "unknown-class" for p in resp.get_json()["problems"])


def test_export_yaml_rejects_when_a_choice_is_still_pending(client):
    resp = client.post("/api/export/yaml", json=_fighter_acolyte_human_draft())
    # Fighting Style is never pre-selected in this fixture, so it stays pending
    assert resp.status_code == 400
    assert any("unresolved-choice" in p["id"] for p in resp.get_json()["problems"])


def test_export_markdown_endpoint_returns_markdown(client):
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["choices"] = {
        "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"],
        "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
    }
    draft["equipment"]["choices"] = {
        "class:fighter:1:equipment-choice-0": ["chain-mail"],
        "class:fighter:1:equipment-choice-2": ["handaxe"],
        "class:fighter:1:equipment-choice-3": ["explorers-pack"],
    }
    draft["background"]["choices"] = {"background:acolyte:languages": ["dwarvish", "elvish"]}
    draft["species"]["choices"] = {"species:human:languages": ["giant"]}
    resp = client.post("/api/export/markdown", json=draft)
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    assert "Torvin Bracewell" in resp.data.decode("utf-8")


def test_export_markdown_rejects_when_a_choice_is_still_pending(client):
    resp = client.post("/api/export/markdown", json=_fighter_acolyte_human_draft())
    # Same pending Fighting Style choice as the YAML gate test above — both
    # routes must share the same gate, not two independently-drifting copies.
    assert resp.status_code == 400
    assert any("unresolved-choice" in p["id"] for p in resp.get_json()["problems"])


def test_export_pdf_endpoint_returns_a_pdf(client):
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["choices"] = {
        "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics"],
        "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
    }
    draft["equipment"]["choices"] = {
        "class:fighter:1:equipment-choice-0": ["chain-mail"],
        "class:fighter:1:equipment-choice-2": ["handaxe"],
        "class:fighter:1:equipment-choice-3": ["explorers-pack"],
    }
    draft["background"]["choices"] = {"background:acolyte:languages": ["dwarvish", "elvish"]}
    draft["species"]["choices"] = {"species:human:languages": ["giant"]}
    resp = client.post("/api/export/pdf", json=draft)
    assert resp.status_code == 200
    assert resp.content_type.startswith("application/pdf")
    assert resp.data[:4] == b"%PDF"


def test_export_pdf_rejects_when_a_choice_is_still_pending(client):
    resp = client.post("/api/export/pdf", json=_fighter_acolyte_human_draft())
    # Same pending Fighting Style choice as the YAML/Markdown gate tests above.
    assert resp.status_code == 400
    body = resp.get_json()
    assert "problems" in body


def test_export_unknown_format_returns_404(client):
    resp = client.post("/api/export/xml", json={})
    assert resp.status_code == 404


def test_items_endpoint_lists_every_bundled_item(client):
    resp = client.get("/api/items")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 237
    chain_mail = next(i for i in body["items"] if i["id"] == "chain-mail")
    assert chain_mail["name"] == "Chain Mail"
    assert chain_mail["category"] == "armor"


def test_items_endpoint_filters_by_category(client):
    resp = client.get("/api/items?category=armor")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["items"]) == 13
    assert all(i["category"] == "armor" for i in body["items"])


def test_items_endpoint_filters_by_search_query(client):
    resp = client.get("/api/items?q=longbow")
    assert resp.status_code == 200
    body = resp.get_json()
    names = [i["name"].lower() for i in body["items"]]
    assert any("longbow" in n for n in names)
    assert all("longbow" in n for n in names)


def test_spells_endpoint_lists_all_spells_by_default(client):
    resp = client.get("/api/spells")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["spells"]) == 319
    fireball = next(s for s in body["spells"] if s["id"] == "fireball")
    assert fireball["name"] == "Fireball"


def test_spells_endpoint_filters_by_class(client):
    resp = client.get("/api/spells?class=wizard")
    assert resp.status_code == 200
    body = resp.get_json()
    spell_ids = [s["id"] for s in body["spells"]]
    # Fireball is a wizard spell
    assert "fireball" in spell_ids
    # Cure Wounds is cleric/druid/paladin/ranger/bard but not wizard
    assert "cure-wounds" not in spell_ids


def test_spells_endpoint_filters_by_class_and_level(client):
    resp = client.get("/api/spells?class=wizard&level=0")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["spells"]) > 0
    # All returned spells must be level 0
    assert all(s["level"] == 0 for s in body["spells"])


def test_spells_endpoint_filters_by_search_query(client):
    resp = client.get("/api/spells?q=fire")
    assert resp.status_code == 200
    body = resp.get_json()
    spell_names = [s["name"].lower() for s in body["spells"]]
    # Fire Bolt and Fireball should be present
    assert any("fire bolt" in n for n in spell_names)
    assert any("fireball" in n for n in spell_names)
    # Non-matching spell like "cure wounds" should not be present
    assert not any("cure wounds" in n for n in spell_names)


def test_spells_endpoint_rejects_invalid_level_parameter(client):
    resp = client.get("/api/spells?level=notanumber")
    assert resp.status_code == 400
    body = resp.get_json()
    assert "error" in body
    assert "integer" in body["error"].lower()


def test_spells_endpoint_returns_full_spell_details(client):
    resp = client.get("/api/spells?q=fireball")
    assert resp.status_code == 200
    body = resp.get_json()
    fireball = next(s for s in body["spells"] if s["id"] == "fireball")
    # Check all expected keys are present
    expected_keys = {"id", "name", "level", "school", "castingTime", "range",
                     "components", "duration", "concentration", "ritual", "material", "desc"}
    assert set(fireball.keys()) == expected_keys
    # Check concrete values for Fireball
    assert fireball["name"] == "Fireball"
    assert fireball["level"] == 3
    assert fireball["school"] == "Evocation"
    assert isinstance(fireball["components"], list)
    assert "V" in fireball["components"]
    assert fireball["concentration"] is False
    assert fireball["ritual"] is False


def test_spells_endpoint_includes_material_field(client):
    resp = client.get("/api/spells?q=fireball")
    assert resp.status_code == 200
    body = resp.get_json()
    fireball = next(s for s in body["spells"] if s["id"] == "fireball")
    assert fireball["material"] == "A tiny ball of bat guano and sulfur."


def test_spells_endpoint_tolerates_empty_level_parameter(client):
    resp = client.get("/api/spells?level=")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["spells"]) == 319


def test_export_yaml_does_not_block_on_pending_equipment_choices(client):
    resp = client.post("/api/export/yaml", json={
        "name": "Torvin Bracewell",
        "classes": [{"classId": "fighter", "level": 1, "choices": {
            "class:fighter:1:prof-choice-0": ["skill-athletics", "skill-history"],
            "class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-archery"],
        }}],
        "background": {"id": "acolyte", "choices": {"background:acolyte:languages": ["draconic", "deep-speech"]}},
        "species": {"id": "human", "choices": {"species:human:languages": ["dwarvish"]}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"added": [], "skipped": False},  # no "choices" key — exactly what the shipped frontend sends
    })
    assert resp.status_code == 200
    assert resp.mimetype == "application/x-yaml"


def test_equipment_choice_appears_in_resolve_response(client):
    resp = client.post("/api/resolve", json={
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}],
        "background": {"choices": {}}, "species": {"choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
    })
    assert resp.status_code == 200
    body = resp.get_json()
    equipment_choices = [c for c in body["choices"] if c["source"]["kind"] == "equipment"]
    assert len(equipment_choices) == 3
