"""Slice 7: the three exporters cover every sheet/derived key."""
import io

import yaml
import pytest
from pypdf import PdfReader

import export_fields
from catalog.loader import load
from catalog.reference_data import LANGUAGE_NAMES, SKILL_NAMES
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf


@pytest.fixture(scope="module")
def catalog():
    return load()


def _rich_resolution(catalog):
    d = {
        "name": "Тест", "sources": ["srd", "phb", "xphb"],
        "classes": [{"classId": "rogue", "level": 6, "choices": {
            "class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-athletics"],
            "class:rogue:1:expertise-choice:rogue-expertise-1": ["skill-stealth", "skill-acrobatics"],
            "class:rogue:4:asi": ["feat:athlete-xphb"],
        }}],
        "background": {"id": "acolyte-xphb", "choices": {}},
        "species": {"id": "dwarf", "subspeciesId": "hill-dwarf", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 16, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }
    return resolve(d, catalog)


def _cleric(catalog):
    return resolve({
        "name": "C", "sources": ["srd"], "classes": [{"classId": "cleric", "level": 5, "subclassId": "life", "choices": {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 14, "CHA": 10}},
        "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {},
    }, catalog)


def test_every_sheet_and_derived_key_is_exported_or_excluded(catalog):
    for res in (_rich_resolution(catalog), _cleric(catalog)):
        doc = yaml.safe_load(to_yaml(res))
        for section in ("sheet", "derived"):
            for key in res[section]:
                assert key in doc or (section, key) in export_fields.EXCLUDED, f"{section}.{key} is not exported"
        for reason in export_fields.EXCLUDED.values():
            assert reason


def test_yaml_values_match_resolution(catalog):
    res = _rich_resolution(catalog)
    doc = yaml.safe_load(to_yaml(res))
    for key in ("expertiseSkills", "grantedFeats", "damageModifiers", "conditionImmunities", "senses", "startingGold",
                "innateSpells", "features", "feats", "featOptions"):
        assert doc[key] == res["sheet"][key], key
    for key in ("initiative", "passivePerception", "passiveInsight", "passiveInvestigation", "speeds"):
        assert doc[key] == res["derived"][key], key
    assert doc["expertiseSkills"] == ["skill-stealth", "skill-acrobatics"]
    assert doc["senses"].get("darkvision") == 60


def test_markdown_lists_new_sections(catalog):
    md = to_markdown(_rich_resolution(catalog))
    assert "## Черти и способности" in md
    assert "Sneak Attack (ниво 1)" in md and "Darkvision" in md
    assert "## Таланти" in md and "Athlete" in md
    assert "## Експертиза" in md
    assert "Stealth: " in md and "(експертиза)" in md
    assert "## Сетива" in md and "тъмно зрение 60 фута" in md
    assert "## Съпротиви и имунитети" in md and "Poison" in md


def test_markdown_always_prepared_spells(catalog):
    md = to_markdown(_cleric(catalog))
    assert "## Винаги подготвени заклинания" in md and "Bless (ниво 1)" in md


def test_markdown_expertise_marker_only_on_expert_skills(catalog):
    md = to_markdown(_rich_resolution(catalog))
    assert md.count("(експертиза)") == 2


def test_pdf_renders_with_new_sections(catalog):
    for res in (_rich_resolution(catalog), _cleric(catalog)):
        data = to_pdf(res)
        assert data.startswith(b"%PDF") and len(data) > 2000


def test_markdown_and_pdf_share_the_same_blocks(catalog):
    res = _rich_resolution(catalog)
    blocks = export_fields.extra_blocks(res)
    md = to_markdown(res)
    for kind, text in blocks:
        assert text in md, text


# ---- Slice 9: attacks and carrying capacity in every export ----------------


def _rogue_1(catalog):
    return resolve({
        "name": "R", "sources": ["srd"], "classes": [{"classId": "rogue", "level": 1, "choices": {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 16, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}},
        "equipment": {"choices": {}, "added": [{"itemId": "longsword", "qty": 1, "equipped": True}], "skipped": False}, "details": {},
    }, catalog)


def test_yaml_carries_attacks_and_capacity(catalog):
    res = _rogue_1(catalog)
    doc = yaml.safe_load(to_yaml(res))
    assert doc["attacks"] == res["derived"]["attacks"]
    assert doc["carryingCapacity"] == res["derived"]["carryingCapacity"]
    assert doc["stealthDisadvantage"] is False
    dagger = next(a for a in doc["attacks"] if a["itemId"] == "dagger")
    assert dagger["attackBonus"] == 5 and dagger["damage"] == "1d4+3"


def test_markdown_and_pdf_list_attacks_and_capacity(catalog):
    res = _rogue_1(catalog)
    carried, capacity = res["derived"]["carryingCapacity"]["carried"], res["derived"]["carryingCapacity"]["capacity"]
    assert capacity == 165  # STR 10 + 1 (human) = 11, x 15
    md = to_markdown(res)
    assert "## Атаки" in md
    assert "- Dagger: +5, 1d4+3 piercing" in md
    # STR 11 (+0), rogue is proficient with longswords: +2, bare dice
    assert "- Longsword: +2, 1d8 slashing (versatile 1d10)" in md
    assert "## Носимост" in md and f"{carried}/{capacity} lb" in md
    assert "## Броня" not in md  # leather armor: no stealth disadvantage
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "Атаки" in text and "Dagger: +5, 1d4+3 piercing" in text and f"{carried}/{capacity} lb" in text


def test_over_capacity_and_stealth_armor_are_flagged(catalog):
    res = _rogue_1(catalog)
    res["derived"]["carryingCapacity"] = {"capacity": 100, "pushDragLift": 200, "carried": 130, "overCapacity": True}
    res["derived"]["stealthDisadvantage"] = True
    md = to_markdown(res)
    assert "130/100 lb (претоварен)" in md
    assert "## Броня" in md and "Недостатък при Скритост" in md


def test_markdown_and_pdf_show_dueling_damage(catalog):
    res = _rogue_1(catalog)
    for a in res["derived"]["attacks"]:
        if a["itemId"] == "longsword":
            a["duelingDamage"] = "1d8+2"
    md = to_markdown(res)
    assert "- Longsword: +2, 1d8 slashing (versatile 1d10), с Дуел 1d8+2" in md
    text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages)
    assert "с Дуел 1d8+2" in text


# ---- S6: kitchen-sink field-level sweep across YAML, Markdown and PDF -------

import re

from kitchen_sink import KITCHEN_SINK, build, skip_reason

# What each draft must actually put on the sheet, so a passing sweep is not vacuous.
_EXPECT = {
    "barbarian20-2014": {"resources": ["Rage"], "apa": 2},
    "barbarian20-2024": {"resources": ["Rage"], "apa": 2, "masteries": True, "mastery_suffix": True},
    "monk14": {"resources": ["Martial Arts", "Ki"], "apa": 2},
    "paladin6": {"resources": ["Lay on Hands", "Channel Divinity"], "apa": 2},
    "cleric6": {"resources": ["Channel Divinity"]},
    "warlock17": {"resources": ["Agonizing Blast"], "feature_choice": "Armor of Shadows", "arcanum": 4, "devils_sight": True, "innate": True},
    "fighter10-2024": {"resources": ["Second Wind", "Action Surge", "Indomitable"], "apa": 2, "masteries": True,
                       "mastery_suffix": True, "dueling": True, "feature_choice": "Dueling"},
    "warlock7-2024": {"resources": ["Agonizing Blast", "Pact of the Blade"], "tome": True, "lessons": True, "pact_weapon": True,
                      "devils_sight": True, "feature_choice": "Pact of the Tome"},
    "wizard5-2014": {"resources": ["Arcane Recovery"], "spellbook": True},
    "wizard20-2014": {"resources": ["Arcane Recovery", "Signature Spells"], "spellbook": True, "spell_mastery": 2,
                      "signature": 2},  # RP15
    "wizard5-2024": {"resources": ["Arcane Recovery"], "spellbook": True},
    "bard10-2014": {},  # RP16: SRD Magical Secrets picks (Fireball, Sacred Flame) in the known list
    "bard6-lore-2014": {},  # RPX1: SRD Lore Bard 6, Bonus Proficiencies and Additional Magical Secrets picks
    "psi-warrior11": {"resources": ["Psionic Energy Dice"], "apa": 3},
    "totem-bear6": {"resources": ["Rage"], "feature_choice": "Bear"},
    "cleric1-thaumaturge-2024": {"feature_choice": "Thaumaturge"},
    # F3b: the C6b..C9b / R9 stages
    "rogue6-2024": {"resources": ["Sneak Attack"], "masteries": True, "expertise": 4, "feature_choice": "Dwarvish",
                    "languages": ["common", "thieves-cant"]},
    "sorcerer17-2024": {"resources": ["Sorcery Points", "Innate Sorcery", "Sorcerous Restoration"],
                        "feature_choice": "Careful Spell (1 SP)", "languages": ["common"]},
    "cleric7-2024": {"resources": ["Channel Divinity", "Divine Strike"], "feature_choice": "Divine Strike"},
    "wizard20-2024": {"resources": ["Arcane Recovery"], "spellbook": True, "spell_mastery": 2, "signature": 2,
                      "expertise": 1, "feature_choice": "Arcana"},
    "ranger9-2024": {"masteries": True, "expertise": 3, "feature_choice": "Elvish", "languages": ["common", "elvish"]},
    "barbarian3-2024": {"resources": ["Rage"], "feature_choice": "Perception", "masteries": True},
    "fighter4-2024": {"resources": ["Second Wind", "Action Surge"], "masteries": True, "feature_choice": "Archery",
                      "equip_qty": ("Javelin", 8),
                      # RP8: the 2024 kitchen sink now carries its Dungeoneer's Pack contents (deliberate _EXPECT change)
                      "pack": "dungeoneers-pack",
                      # RP9: the Soldier (XPHB) background package A is now real items: the 20-pack Arrow and the Dice Set that
                      # is the background's own tool proficiency pick (deliberate _EXPECT change)
                      "bg_items": ["Arrow", "Dice Set", "Quiver"]},
}
_EXPECT.update({
    "magic-initiate-2024": {"innate": True, "feats": ["magic-initiate-xphb"]},
    # FE12: feat effects reach every export (notes, resources, attack-row notes, feat picks)
    "feats-mixed-fighter14": {"feats": ["alert-phb", "tough-phb", "great-weapon-master-phb", "lucky-phb", "observant-phb"],
                              "feat_resources": ["Luck Points"], "attack_note": "Great Weapon Master: before you attack",
                              "feat_note": "Alert", "initiative": 7},
    "feats-2014-rogue16": {"resources": ["Sneak Attack"], "feats": ["keen-mind-phb", "weapon-master-phb", "resilient-phb"],
                           "elemental_adept": 2, "feat_note": "Keen Mind", "attack_note": "Sneak Attack"},
    "feats-mixed-wizard8": {"resources": ["Arcane Recovery"], "feats": ["martial-adept-phb", "eldritch-adept-tce"],
                            "feat_resources": ["Superiority Die (Martial Adept)"], "innate": True, "feat_note": "Eldritch Adept"},
    "feats-2024-fighter19": {"resources": ["Second Wind"], "feats": [
        "alert-xphb", "tough-xphb", "great-weapon-master-xphb", "lucky-xphb", "observant-xphb", "keen-mind-xphb",
        "weapon-master-xphb", "boon-of-fortitude-xphb"], "feat_resources": ["Luck Points"], "masteries": True,
        "attack_note": "Great Weapon Master: +", "feat_note": "Alert", "initiative": 9},
})
assert set(_EXPECT) == set(KITCHEN_SINK)

_SINK_RES: dict = {}


def _sink(sid, catalog):
    reason = skip_reason(KITCHEN_SINK[sid])
    if reason:
        pytest.skip(reason)
    if sid not in _SINK_RES:
        draft = build(sid, catalog, resolve)
        res = resolve(draft, catalog)
        assert res["problems"] == [] and all(c["status"] == "resolved" for c in res["choices"] if c["source"]["kind"] != "equipment")
        _SINK_RES[sid] = res
    return _SINK_RES[sid]


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def _pdf_text(res) -> str:
    return _flat("\n".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages))


def _expected_strings(res) -> list[tuple[str, str]]:
    """(label, text) pairs that must appear in both Markdown and the PDF."""
    sheet, derived = res["sheet"], res["derived"]
    out = [("classResource", r["name"]) for r in derived["classResources"]]
    for r in derived["classResources"]:
        out += [("resourceDetail", frag) for frag in export_fields.resource_detail_parts(r.get("details"))]
    out += [("featResource", r["name"]) for r in derived.get("featResources", [])]  # FE3
    out += [("featNote", note) for f in sheet["feats"] for note in f.get("notes", [])]  # FE3
    out += [("weaponMastery", m["name"]) for m in sheet["weaponMasteries"]]
    for cs in sheet["spells"]:
        out += [("mysticArcanum", m["name"]) for m in cs.get("mysticArcanum") or []]
        out += [("pactOfTheTome", s["name"]) for s in cs.get("pactOfTheTome") or []]  # C7c
        if cs.get("spellbook"):
            out.append(("spellbook heading", "Книга със заклинания"))
            out += [("spellbook", s["name"]) for s in cs["spellbook"]]
    out += [("innateSpell", e["name"]) for e in sheet["innateSpells"]]
    if derived["attacksPerAction"] > 1:
        out.append(("attacksPerAction", f"Атаки на действие: {derived['attacksPerAction']}"))
    for a in derived["attacks"]:
        out += [("attackNote", n) for n in a.get("notes", [])]  # FE5 / FE12: feat riders on the attack rows
        if a.get("offhandDamage"):
            out.append(("offhandDamage", f"off hand {a['offhandDamage']}"))
        if a.get("duelingDamage"):
            out.append(("duelingDamage", f"с Дуел {a['duelingDamage']}"))
        if a.get("mastery"):
            out.append(("mastery suffix", f"майсторство {a['mastery']}"))
    out += [("language", LANGUAGE_NAMES.get(lang, lang)) for lang in sheet["proficiencies"]["languages"]]  # F3b: C6b-2 / C8
    for cs in sheet["spells"]:  # C6d: Wizard 18 / 20 picks
        for key, heading in export_fields.SPELL_PICK_LINES:
            out += [(key, s["name"]) for s in cs.get(key) or []]
            if cs.get(key):
                out.append((key + " heading", heading))
    for key in ("granted", "chosen", "added"):  # C9b: package quantities
        for e in sheet["equipment"][key]:
            out.append(("equipment", e["name"] + (f" x{e['qty']}" if e.get("qty", 1) != 1 else "")))
    if sheet.get("expertiseSkills"):
        out.append(("expertise heading", "Експертиза"))
    if "devilsSight" in sheet["senses"]:
        out.append(("senses.devilsSight", f"дяволско зрение {sheet['senses']['devilsSight']} фута"))
    for f in sheet["features"]:
        if f.get("choice"):
            out.append(("feature choice", f"{f['name']}" + (f" (ниво {f['level']})" if f.get("level") else "")
                        + ": " + ", ".join(f["choice"])))
    return out


def test_kitchen_sink_rage_details_are_printed(catalog):
    """F2-A: the Rage resistances and (2024) short-rest regain reach Markdown and PDF."""
    for sid, want in (("barbarian20-2024", "1 използване се възстановява при кратка почивка"),
                      ("barbarian20-2014", "съпротива: дробящи, пробождащи, режещи"),
                      ("totem-bear6", "съпротива: всички видове щета освен психична")):
        res = _sink(sid, catalog)
        assert want in _flat(to_markdown(res)), (sid, want)
        assert want in _pdf_text(res), (sid, want)
    res = _sink("barbarian20-2024", catalog)
    assert "съпротива: дробящи, пробождащи, режещи" in _flat(to_markdown(res))


@pytest.mark.parametrize("sid", list(KITCHEN_SINK))
def test_kitchen_sink_yaml_carries_every_key(catalog, sid):
    res = _sink(sid, catalog)
    doc = yaml.safe_load(to_yaml(res))
    for section in ("sheet", "derived"):
        for key in res[section]:
            assert key in doc or (section, key) in export_fields.EXCLUDED, f"{section}.{key}"
    for key in ("classResources", "attacksPerAction", "weaponMasteries", "innateSpells", "senses", "spells", "features"):
        assert key in doc
    assert doc["classResources"] == res["derived"]["classResources"]
    assert doc["weaponMasteries"] == res["sheet"]["weaponMasteries"]
    assert doc["attacksPerAction"] == res["derived"]["attacksPerAction"]


@pytest.mark.parametrize("sid", list(KITCHEN_SINK))
def test_kitchen_sink_fields_are_non_empty_as_expected(catalog, sid):
    """Guards the sweep against passing vacuously: the draft really carries the field."""
    res = _sink(sid, catalog)
    sheet, derived, want = res["sheet"], res["derived"], _EXPECT[sid]
    assert {r["name"] for r in derived["classResources"]} >= set(want.get("resources", []))
    if "apa" in want:
        assert derived["attacksPerAction"] == want["apa"]
    if want.get("masteries"):
        assert sheet["weaponMasteries"]
    if want.get("mastery_suffix"):
        assert any(a.get("mastery") for a in derived["attacks"])
    if want.get("dueling"):
        assert any(a.get("duelingDamage") for a in derived["attacks"])
    if "arcanum" in want:
        assert sum(len(s.get("mysticArcanum") or []) for s in sheet["spells"]) == want["arcanum"]
    if want.get("spellbook"):
        assert any(s.get("spellbook") for s in sheet["spells"])
    if "expertise" in want:  # C6b-1
        assert len(sheet["expertiseSkills"]) == want["expertise"]
    for lang in want.get("languages", []):  # C6b-2 / C8
        assert lang in sheet["proficiencies"]["languages"]
        assert lang in LANGUAGE_NAMES, lang
    if "spell_mastery" in want:  # C6d
        assert sum(len(s.get("spellMastery") or []) for s in sheet["spells"]) == want["spell_mastery"]
    if "signature" in want:
        assert sum(len(s.get("signatureSpells") or []) for s in sheet["spells"]) == want["signature"]
    if "equip_qty" in want:  # C9b
        name, qty = want["equip_qty"]
        assert any(e["name"] == name and e["qty"] == qty for k in ("granted", "chosen", "added") for e in sheet["equipment"][k])
    if "bg_items" in want:  # RP9: background package A as inventory items, not narrative placeholders
        names = {e["name"] for k in ("granted", "chosen", "added") for e in sheet["equipment"][k]}
        assert set(want["bg_items"]) <= names
        assert not any("Gaming Set" in n or "Arrows (20)" in n for n in sheet["equipment"]["narrativeItems"])
    if "pack" in want:  # RP8: ruleset 2024 pack entry with contents, exported to Markdown and the PDF
        entry = next(e for k in ("granted", "chosen", "added") for e in sheet["equipment"][k] if e["itemId"] == want["pack"])
        assert entry["contents"]
        assert export_fields.pack_contents_suffix(entry).strip() in _flat(to_markdown(res))
    if want.get("tome"):  # C7c
        assert sum(len(s.get("pactOfTheTome") or []) for s in sheet["spells"]) == 5
    if want.get("lessons"):
        assert any(f["origin"] == "invocation" for f in sheet["feats"])
    if want.get("pact_weapon"):
        assert any("Pact weapon" in " ".join(a["notes"]) and a["proficient"] for a in derived["attacks"])  # STR 16 = CHA 16: ability stays STR
    if want.get("devils_sight"):
        assert sheet["senses"].get("devilsSight") == 120
    if want.get("innate"):
        assert sheet["innateSpells"]
    if "feature_choice" in want:
        assert any(want["feature_choice"] in (f.get("choice") or []) for f in sheet["features"])
    # FE12 feat-holding drafts
    ids = [f["id"] for f in sheet["feats"]]
    for feat in want.get("feats", []):
        assert feat in ids, feat
    assert {r["name"] for r in derived["featResources"]} >= set(want.get("feat_resources", []))
    if "elemental_adept" in want:
        picks = [f["choice"][0] for f in sheet["feats"] if f["id"] == "elemental-adept-phb"]
        assert len(picks) == want["elemental_adept"] and len(set(picks)) == len(picks)
    if "initiative" in want:
        assert derived["initiative"] == want["initiative"]
    if "feat_note" in want:
        assert any(f.get("notes") and want["feat_note"] in f["name"] for f in sheet["feats"])
    if "attack_note" in want:
        assert any(want["attack_note"] in n for a in derived["attacks"] for n in a["notes"])


@pytest.mark.parametrize("sid", list(KITCHEN_SINK))
def test_kitchen_sink_fields_reach_markdown_and_pdf(catalog, sid):
    res = _sink(sid, catalog)
    md, pdf = _flat(to_markdown(res)), _pdf_text(res)
    expected = _expected_strings(res)
    assert expected, "nothing to check"
    for label, text in expected:
        assert text in md, f"{label} {text!r} missing from Markdown"
        assert text in pdf, f"{label} {text!r} missing from the PDF"


@pytest.mark.parametrize("sid", list(KITCHEN_SINK))
def test_kitchen_sink_bulgarian_text_has_no_substituted_glyphs(catalog, sid, caplog):
    res = _sink(sid, catalog)
    with caplog.at_level("WARNING"):
        pdf = _pdf_text(res)  # fpdf2 logs "missing the following glyphs" for an undrawable character
    assert "glyph" not in caplog.text.lower(), caplog.text
    md = to_markdown(res)
    if "?" not in md:
        assert "?" not in pdf
    for _, heading in (b for b in export_fields.extra_blocks(res) if b[0] == "h2"):
        assert heading in pdf, heading
    for heading in ("Заклинания", "Книга със заклинания", "Мистичен арканум", "Вродени заклинания"):
        if heading in md:
            assert heading in pdf, heading


def test_pdf_renders_the_times_sign_and_other_symbols(catalog, caplog):
    """Item and feature names can carry '×' / curly quotes; DejaVu has them, '?' would mean a fallback."""
    res = _rogue_1(catalog)
    res["sheet"]["name"] = "Дракон × Герой’s"
    res["sheet"]["equipment"]["narrativeItems"] = ["20× стрела", "Ключ – ковчег"]
    with caplog.at_level("WARNING"):
        text = _pdf_text(res)
    assert "glyph" not in caplog.text.lower(), caplog.text
    assert "×" in text and "20× стрела" in text and "’" in text and "–" in text and "?" not in text


def test_kitchen_sink_markdown_and_pdf_share_the_same_blocks(catalog):
    for sid in KITCHEN_SINK:
        res = _sink(sid, catalog)
        md = to_markdown(res)
        for kind, text in export_fields.extra_blocks(res):
            assert text in md, text


def test_kitchen_sink_2024_stage_lines_reach_every_export(catalog):
    """F3b: spot checks on the C6b..C9b / R9 lines, printed in the book's words in all three formats."""
    for sid, needles in (
        ("rogue6-2024", ["Thieves' Cant", "Common", "Експертиза", "Stealth: ", "(експертиза)", "майсторство"]),
        ("sorcerer17-2024", ["Sorcery Points", "Innate Sorcery", "Sorcerous Restoration", "Careful Spell (1 SP)"]),
        ("cleric7-2024", ["Divine Strike", "Blessed Strikes"]),
        ("wizard20-2024", ["Майсторство със заклинания", "Burning Hands (ниво 1)", "Scorching Ray (ниво 2)", "Запазени заклинания", "Fireball (ниво 3)", "Scholar"]),
        ("wizard20-2014", ["Майсторство със заклинания", "Shield (ниво 1)", "Web (ниво 2)", "Запазени заклинания",
                           "Fireball (ниво 3)", "Counterspell (ниво 3)"]),  # RP15: the SRD picks under 2014
        ("bard10-2014", ["Fireball (ниво 3)", "Sacred Flame (ниво 0)"]),  # RP16: Magical Secrets picks in the known list
        ("bard6-lore-2014", ["Fireball (ниво 3)", "Sacred Flame (ниво 0)", "Additional Magical Secrets"]),  # RPX1: not-counted picks
        ("ranger9-2024", ["Elvish", "Dwarvish", "Deft Explorer"]),
        ("barbarian3-2024", ["Primal Knowledge"]),
        ("fighter4-2024", ["Javelin x8", "Fighting Style"]),
        ("warlock7-2024", ["Pact weapon", "Lessons of the First Ones", "Книга на сенките"]),
    ):
        res = _sink(sid, catalog)
        md, pdf = _flat(to_markdown(res)), _pdf_text(res)
        for needle in needles:
            assert needle in md, (sid, needle, "Markdown")
            assert needle in pdf, (sid, needle, "PDF")
        doc = yaml.safe_load(to_yaml(res))
        assert doc["proficiencies"]["languages"] == res["sheet"]["proficiencies"]["languages"], sid
        assert doc["equipment"] == res["sheet"]["equipment"], sid


def test_magic_initiate_kitchen_sink_has_innate_spells(catalog):
    """RPF: the kitchen-sink filler stores feat cards by cid prefix like the frontend, so the dependent
    Magic Initiate spell cards are filled and the spells reach the sheet."""
    res = _sink("magic-initiate-2024", catalog)
    assert [c["id"] for c in res["choices"] if c["status"] == "pending"] == []
    assert len(res["sheet"]["innateSpells"]) >= 3  # two cantrips + one level-1 spell
