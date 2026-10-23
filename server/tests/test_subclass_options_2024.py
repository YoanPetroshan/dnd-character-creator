"""RP13 (F2, E13): 2024 subclass option cards and their effects. Ruleset "2024" only; mixed / 2014 are unchanged.

Governing texts (catalog.features, XPHB records; `reference_data.SUBCLASS_OPTIONS_2024` carries a verbatim quote per
card and per option, pinned by `test_quotes_match_catalog`):
  Hunter 3 Hunter's Prey        "You gain one of the following feature options of your choice. Whenever you finish a
                                Short or Long Rest, you can replace the chosen option with the other one."
                                Colossus Slayer: "extra 1d8 damage to the target if it's missing any of its Hit
                                Points ... only once per turn"; Horde Breaker: a second attack.
  Hunter 7 Defensive Tactics    same wording; Escape the Horde / Multiattack Defense.
  Wild Heart 6 Aspect of the Wilds  Owl: Darkvision 60 (+60 when already held); Panther: Climb Speed equal to your
                                Speed; Salmon: Swim Speed equal to your Speed. "Whenever you finish a Long Rest, you
                                can change your choice."
  Draconic 6 Elemental Affinity "Choose one of those types: Acid, Cold, Fire, Lightning, or Poison. You have
                                Resistance to that damage type, and ... you can add your Charisma modifier to one
                                damage roll of that spell."
  Beast Master 3 Primal Companion "Choose its stat block: Beast of the Land, Beast of the Sea, or Beast of the Sky."
                                (label only: the stat blocks are not in the data)
  Fey Wanderer 3 Fey Wanderer Spells "Choose it from the Feywild Gifts table or determine it randomly." (6 flavour)
  Not cards (the pick lasts a turn, a rest or one use): Elemental Epitome, Fiendish Resilience, Starry Form,
  The Third Eye; their text stays the note.

Rule matrix:
  cards     one required card (count 1) per feature, cid `class:<cls>:<lvl>:feature:<feature id>`, options
            `<feature id>--<key>`; none below the record's level, without the subclass, under mixed / 2014 (a hidden
            stored XPHB subclass) or with an SRD-only catalog; the pick attaches to the feature row in sheet.features
  Owl       Darkvision 60, or +60 on the final range of a species Darkvision (dwarf 120 -> 180)
  Panther   climb = final walk speed; Salmon swim = final walk speed (after Fast Movement etc.)
  Affinity  resistance in sheet.damageModifiers + a note-only subclass resource with the Charisma modifier
  Colossus  a note-only resource and the note on every weapon attack row (never the unarmed strike)
  switching the stored option moves the effect; the other options give nothing"""
import copy
import time

import pytest

from catalog import official_source, reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import subclass_options_2024
from engine.resolve import resolve
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

PREY = "class:ranger:3:feature:hunter-xphb-3-hunters-prey"
TACTICS = "class:ranger:7:feature:hunter-xphb-7-defensive-tactics"
ASPECT = "class:barbarian:6:feature:wild-heart-xphb-6-aspect-of-the-wilds"
AFFINITY = "class:sorcerer:6:feature:draconic-xphb-6-elemental-affinity"
COMPANION = "class:ranger:3:feature:beast-master-xphb-3-primal-companion"
GIFTS = "class:ranger:3:feature:fey-wanderer-xphb-3-fey-wanderer-spells"
FEATURE = {PREY: "hunter-xphb-3-hunters-prey", TACTICS: "hunter-xphb-7-defensive-tactics",
           ASPECT: "wild-heart-xphb-6-aspect-of-the-wilds", AFFINITY: "draconic-xphb-6-elemental-affinity",
           COMPANION: "beast-master-xphb-3-primal-companion", GIFTS: "fey-wanderer-xphb-3-fey-wanderer-spells"}
SUB = {PREY: "hunter-xphb", TACTICS: "hunter-xphb", ASPECT: "wild-heart-xphb", AFFINITY: "draconic-xphb",
       COMPANION: "beast-master-xphb", GIFTS: "fey-wanderer-xphb"}
CLS = {PREY: "ranger", TACTICS: "ranger", ASPECT: "barbarian", AFFINITY: "sorcerer", COMPANION: "ranger",
       GIFTS: "ranger"}
LEVEL = {PREY: 3, TACTICS: 7, ASPECT: 6, AFFINITY: 6, COMPANION: 3, GIFTS: 3}


def opt(cid, key):
    return f"{FEATURE[cid]}--{key}"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", species="human-xphb", cha=10, added=(), background="sage-xphb"):
    """classes: (classId, level, subclassId | None, {cid: [picks]})."""
    entries = []
    for cls_id, level, sub, choices in classes:
        e = {"classId": cls_id, "level": level, "choices": choices}
        if sub:
            e["subclassId"] = sub
        entries.append(e)
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": 12, "CHA": cha}},
        "species": {"id": species}, "background": {"id": background},
        "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added],
                      "skipped": False},
        "classes": entries,
    }


def _res(catalog, classes, **kw):
    return resolve(_draft(classes, **kw), catalog)


def _one(catalog, cid, key=None, level=None, ruleset="2024", sub=True, **kw):
    picks = {cid: [opt(cid, key)]} if key else {}
    return _res(catalog, [(CLS[cid], level or LEVEL[cid], SUB[cid] if sub else None, picks)], ruleset=ruleset, **kw)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _resource(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if "-xphb-" not in k}
    return bare


# ---- data -----------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    table = reference_data.SUBCLASS_OPTIONS_2024
    assert set(table) == set(FEATURE.values())
    for fid, spec in table.items():
        rec = catalog.features[fid]
        text = rec["name"] + "\n" + "\n".join(rec["desc"])
        assert (rec["subclass"] or {}).get("index") == spec["subclass"], fid
        assert (rec["class"] or {}).get("index") == spec["class"], fid
        assert rec["source"] == "XPHB"
        for q in spec["quotes"]:
            assert q in text, (fid, q)
        for key, o in spec["options"].items():
            if "quote" in o:
                assert o["quote"] in text, (fid, key)
            else:
                assert o["name"] in " ".join(spec["quotes"]), (fid, key)
            if o.get("line"):
                assert o["quote"].startswith(o["name"] + ". ")
                assert any(line.startswith(o["name"] + ". ") for line in rec["desc"])


@needs_data
def test_option_counts_and_names(catalog):
    table = reference_data.SUBCLASS_OPTIONS_2024
    names = {fid: [o["name"] for o in spec["options"].values()] for fid, spec in table.items()}
    assert names["hunter-xphb-3-hunters-prey"] == ["Colossus Slayer", "Horde Breaker"]
    assert names["hunter-xphb-7-defensive-tactics"] == ["Escape the Horde", "Multiattack Defense"]
    assert names["wild-heart-xphb-6-aspect-of-the-wilds"] == ["Owl", "Panther", "Salmon"]
    assert names["draconic-xphb-6-elemental-affinity"] == ["Acid", "Cold", "Fire", "Lightning", "Poison"]
    assert names["beast-master-xphb-3-primal-companion"] == ["Beast of the Land", "Beast of the Sea", "Beast of the Sky"]
    assert len(names["fey-wanderer-xphb-3-fey-wanderer-spells"]) == 6
    rows = [r for r in catalog.features["fey-wanderer-xphb-3-fey-wanderer-spells"]["desc"] if r[:2] in {f"{n} " for n in range(1, 7)}]
    assert len(rows) == 6


@needs_data
def test_no_card_for_per_rest_or_per_use_picks(catalog):
    """Elemental Epitome, Fiendish Resilience, Starry Form and The Third Eye stay text (a note), never a card."""
    for fid in ("elements-xphb-17-elemental-epitome", "fiend-xphb-10-fiendish-resilience", "stars-xphb-3-starry-form"):
        assert fid not in reference_data.SUBCLASS_OPTIONS_2024
        assert fid in reference_data.CLASS_FEATURE_NOTES_ONLY_2024
        assert reference_data.CLASS_FEATURE_NOTES_ONLY_2024[fid] in " ".join(catalog.features[fid]["desc"])
    assert "wild-heart-xphb-6-aspect-of-the-wilds" not in reference_data.CLASS_FEATURE_NOTES_ONLY_2024  # now a card
    for cls, lvl, sub in (("monk", 17, "elements-xphb"), ("warlock", 10, "fiend-xphb"), ("druid", 20, "stars-xphb"),
                          ("wizard", 20, "diviner-xphb")):
        res = _res(catalog, [(cls, lvl, sub, {})])
        assert not [c for c in res["choices"] if any(w in c["id"] for w in ("epitome", "fiendish", "starry", "third-eye"))]


# ---- the cards -------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cid,labels", [
    (PREY, ["Colossus Slayer", "Horde Breaker"]),
    (TACTICS, ["Escape the Horde", "Multiattack Defense"]),
    (ASPECT, ["Owl", "Panther", "Salmon"]),
    (AFFINITY, ["Acid", "Cold", "Fire", "Lightning", "Poison"]),
    (COMPANION, ["Beast of the Land", "Beast of the Sea", "Beast of the Sky"]),
])
def test_card_options(catalog, cid, labels):
    card = _card(_one(catalog, cid), cid)
    assert card["count"] == 1 and card["status"] == "pending"
    assert [o["label"] for o in card["options"]] == labels
    assert card["source"] == {"kind": "class", "id": CLS[cid], "label": card["source"]["label"], "level": LEVEL[cid]}
    assert card["label"] == reference_data.SUBCLASS_OPTIONS_2024[FEATURE[cid]]["label"]
    assert card["description"]
    assert [o["id"] for o in card["options"]][0].startswith(FEATURE[cid] + "--")


@needs_data
def test_line_options_carry_their_description(catalog):
    card = _card(_one(catalog, ASPECT), ASPECT)
    owl = next(o for o in card["options"] if o["label"] == "Owl")
    assert owl["description"] == "You have Darkvision with a range of 60 feet. If you already have Darkvision, its range increases by 60 feet."
    prey = _card(_one(catalog, PREY), PREY)
    assert prey["options"][1]["description"].startswith("Once on each of your turns when you make an attack with a weapon")


@needs_data
def test_feywild_gifts_card(catalog):
    card = _card(_one(catalog, GIFTS), GIFTS)
    assert [o["id"] for o in card["options"]] == [f"{FEATURE[GIFTS]}--gift-{n}" for n in range(1, 7)]
    assert card["options"][4]["label"] == "Horns or antlers sprout from your head."
    res = _one(catalog, GIFTS, "gift-5")
    assert _card(res, GIFTS)["status"] == "resolved"
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Fey Wanderer Spells")
    assert row["choice"] == ["Horns or antlers sprout from your head."]


@needs_data
def test_feywild_gifts_is_optional_and_does_not_block_export_while_unpicked(catalog):
    """RPF: the gift is a cosmetic table pick ("Choose it ... or determine it randomly"): it stays selectable but
    an unpicked card is flagged `optional` and the export gate skips it; every other card is unchanged."""
    from app import _pending_export_problems
    res = _one(catalog, GIFTS)
    card = _card(res, GIFTS)
    assert card["status"] == "pending" and card["optional"] is True and card["selected"] == []
    assert not any(GIFTS in p["id"] for p in _pending_export_problems(res))
    picked = _card(_one(catalog, GIFTS, "gift-2"), GIFTS)
    assert picked["selected"] == [f"{FEATURE[GIFTS]}--gift-2"] and picked["status"] == "resolved"
    for cid in (PREY, TACTICS, ASPECT, AFFINITY, COMPANION):  # the others stay required and blocking
        other = _one(catalog, cid)
        assert "optional" not in _card(other, cid)
        assert any(cid in p["id"] for p in _pending_export_problems(other)), cid


@needs_data
@pytest.mark.parametrize("cid", list(FEATURE))
def test_card_absent_below_level_without_subclass_and_under_mixed(catalog, cid):
    assert _card(_one(catalog, cid, level=LEVEL[cid] - 1), cid) is None
    assert _card(_one(catalog, cid, sub=False), cid) is None
    assert _card(_one(catalog, cid), cid) is not None
    # a hidden stored XPHB subclass under mixed / 2014: no card, a stored pick is a stale cid
    key = next(iter(reference_data.SUBCLASS_OPTIONS_2024[FEATURE[cid]]["options"]))
    for ruleset in ("mixed", "2014"):
        res = _one(catalog, cid, key, ruleset=ruleset)
        assert _card(res, cid) is None
        assert any(p["choiceId"] == cid for p in res["pruned"])


@needs_data
def test_card_is_not_offered_for_another_subclass(catalog):
    res = _res(catalog, [("ranger", 7, "gloom-stalker-xphb", {})])
    assert _card(res, PREY) is None and _card(res, TACTICS) is None
    res = _res(catalog, [("ranger", 7, "hunter", {})])  # the SRD Hunter keeps its own cards
    assert _card(res, PREY) is None and _card(res, TACTICS) is None


@needs_data
def test_pick_shows_on_the_feature_row(catalog):
    res = _one(catalog, PREY, "horde-breaker")
    assert _card(res, PREY)["status"] == "resolved"
    row = next(f for f in res["sheet"]["features"] if f["name"] == "Hunter's Prey")
    assert row["choice"] == ["Horde Breaker"]
    assert not res["problems"]


@needs_data
def test_stale_or_invalid_pick_is_reported_not_blocking(catalog):
    res = _res(catalog, [("ranger", 3, "hunter-xphb", {PREY: [f"{FEATURE[PREY]}--nonsense"]})])
    assert _card(res, PREY)["status"] == "pending"
    assert any(p["choiceId"] == PREY for p in res["pruned"])
    res = _res(catalog, [("ranger", 2, "hunter-xphb", {PREY: [opt(PREY, "horde-breaker")]})])
    assert _card(res, PREY) is None
    assert any(p["choiceId"] == PREY for p in res["pruned"])


@needs_data
def test_multiclass_both_cards(catalog):
    res = _res(catalog, [("ranger", 3, "hunter-xphb", {PREY: [opt(PREY, "colossus-slayer")]}),
                         ("barbarian", 6, "wild-heart-xphb", {ASPECT: [opt(ASPECT, "owl")]})])
    assert _card(res, PREY)["status"] == "resolved" and _card(res, ASPECT)["status"] == "resolved"
    assert res["sheet"]["senses"]["darkvision"] == 60


# ---- Aspect of the Wilds ----------------------------------------------------------------------

@needs_data
def test_owl_darkvision_with_and_without_species_darkvision(catalog):
    assert "darkvision" not in _one(catalog, ASPECT)["sheet"]["senses"]
    assert _one(catalog, ASPECT, "owl")["sheet"]["senses"]["darkvision"] == 60
    base = _one(catalog, ASPECT, species="dwarf-xphb")["sheet"]["senses"]["darkvision"]
    assert base == 120
    assert _one(catalog, ASPECT, "owl", species="dwarf-xphb")["sheet"]["senses"]["darkvision"] == base + 60


@needs_data
def test_panther_and_salmon_equal_the_final_walk_speed(catalog):
    walk = _one(catalog, ASPECT)["derived"]["speeds"]["walk"]
    panther = _one(catalog, ASPECT, "panther")["derived"]["speeds"]
    assert walk == 40  # 30 + Fast Movement (Barbarian 5): the climb speed follows the FINAL walk speed
    assert panther["climb"] == panther["walk"] == walk
    assert "swim" not in panther
    salmon = _one(catalog, ASPECT, "salmon")["derived"]["speeds"]
    assert salmon["swim"] == salmon["walk"] and "climb" not in salmon
    assert not {"climb", "swim"} & set(_one(catalog, ASPECT, "owl")["derived"]["speeds"])
    assert not {"climb", "swim"} & set(_one(catalog, ASPECT)["derived"]["speeds"])


@needs_data
def test_switching_the_option_moves_the_effect(catalog):
    owl = _one(catalog, ASPECT, "owl")
    panther = _one(catalog, ASPECT, "panther")
    assert "darkvision" in owl["sheet"]["senses"] and "climb" not in owl["derived"]["speeds"]
    assert "darkvision" not in panther["sheet"]["senses"] and "climb" in panther["derived"]["speeds"]


# ---- Elemental Affinity -----------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("t", ["acid", "cold", "fire", "lightning", "poison"])
def test_affinity_resistance_and_note(catalog, t):
    res = _one(catalog, AFFINITY, t, cha=18)
    assert res["sheet"]["damageModifiers"]["resistances"] == [t] or t in res["sheet"]["damageModifiers"]["resistances"]
    note = _resource(res, "sorcerer:elemental-affinity-" + t)
    assert note["source"]["kind"] == "subclass"
    assert f"Add your Charisma modifier (+{(18 - 10) // 2}) to one damage roll of a {t} damage spell" == note["details"]["note"]
    others = set(reference_data.DAMAGE_TYPES) - {t}
    assert not (set(res["sheet"]["damageModifiers"]["resistances"]) & {"acid", "cold", "fire", "lightning", "poison"} - {t})
    assert others  # sanity


@needs_data
def test_affinity_switch_and_species_merge(catalog):
    fire = _one(catalog, AFFINITY, "fire")["sheet"]["damageModifiers"]["resistances"]
    cold = _one(catalog, AFFINITY, "cold")["sheet"]["damageModifiers"]["resistances"]
    assert "fire" in fire and "cold" not in fire and "cold" in cold and "fire" not in cold
    none = _one(catalog, AFFINITY)
    assert not {"fire", "cold"} & set(none["sheet"]["damageModifiers"]["resistances"])
    assert [r for r in none["derived"]["classResources"] if "affinity" in r["id"]] == []
    dwarf = _one(catalog, AFFINITY, "poison", species="dwarf-xphb")["sheet"]["damageModifiers"]["resistances"]
    assert dwarf.count("poison") == 1  # the Dwarf's own poison resistance does not duplicate


@needs_data
def test_affinity_note_with_negative_modifier(catalog):
    res = _one(catalog, AFFINITY, "acid", cha=8)
    assert "(-1)" in _resource(res, "sorcerer:elemental-affinity-acid")["details"]["note"]


@needs_data
def test_affinity_export_line(catalog):
    line = resource_line(_resource(_one(catalog, AFFINITY, "fire", cha=16), "sorcerer:elemental-affinity-fire"))
    assert "+3" in line and "fire" in line


# ---- Hunter's Prey, Defensive Tactics, Companion -------------------------------------------------

@needs_data
def test_colossus_slayer_note_on_weapon_rows_only(catalog):
    res = _one(catalog, PREY, "colossus-slayer", added=["longbow", "shortsword"])
    rows = res["derived"]["attacks"]
    assert rows
    note = reference_data.SUBCLASS_OPTIONS_2024[FEATURE[PREY]]["options"]["colossus-slayer"]["attack_note"]
    weapon_rows = [r for r in rows if r["itemId"] in ("longbow", "shortsword")]
    assert len(weapon_rows) == 2
    for row in weapon_rows:
        assert note in row["notes"]
    for row in rows:
        if row["itemId"] not in ("longbow", "shortsword"):
            assert note not in row["notes"]  # the unarmed strike is not a weapon row
    assert _resource(res, "ranger:hunter-s-prey-colossus-slayer")["details"]["note"].startswith("Once per turn")


@needs_data
def test_horde_breaker_and_other_option_give_no_row_note(catalog):
    note = reference_data.SUBCLASS_OPTIONS_2024[FEATURE[PREY]]["options"]["colossus-slayer"]["attack_note"]
    res = _one(catalog, PREY, "horde-breaker", added=["longbow"])
    assert all(note not in r["notes"] for r in res["derived"]["attacks"])
    assert _resource(res, "ranger:hunter-s-prey-colossus-slayer") is None
    assert _resource(res, "ranger:hunter-s-prey-horde-breaker") is not None
    unpicked = _one(catalog, PREY, added=["longbow"])
    assert all(note not in r["notes"] for r in unpicked["derived"]["attacks"])


@needs_data
def test_switching_hunters_prey_moves_the_note(catalog):
    a = _one(catalog, PREY, "colossus-slayer", added=["longbow"])
    b = _one(catalog, PREY, "horde-breaker", added=["longbow"])
    assert _resource(a, "ranger:hunter-s-prey-colossus-slayer") and not _resource(a, "ranger:hunter-s-prey-horde-breaker")
    assert _resource(b, "ranger:hunter-s-prey-horde-breaker") and not _resource(b, "ranger:hunter-s-prey-colossus-slayer")


@needs_data
@pytest.mark.parametrize("key,name", [("escape-the-horde", "Escape the Horde"), ("multiattack-defense", "Multiattack Defense")])
def test_defensive_tactics_notes(catalog, key, name):
    res = _res(catalog, [("ranger", 7, "hunter-xphb", {PREY: [opt(PREY, "horde-breaker")], TACTICS: [opt(TACTICS, key)]})])
    r = _resource(res, "ranger:defensive-tactics-" + key)
    assert r and r["name"] == f"Defensive Tactics: {name}"
    other = "multiattack-defense" if key == "escape-the-horde" else "escape-the-horde"
    assert _resource(res, "ranger:defensive-tactics-" + other) is None


@needs_data
def test_primal_companion_is_a_label_only(catalog):
    plain = _one(catalog, COMPANION)
    for key in ("beast-of-the-land", "beast-of-the-sea", "beast-of-the-sky"):
        res = _one(catalog, COMPANION, key)
        assert _card(res, COMPANION)["status"] == "resolved"
        assert res["sheet"]["senses"] == plain["sheet"]["senses"]
        assert res["derived"]["speeds"] == plain["derived"]["speeds"]
        assert res["derived"]["classResources"] == plain["derived"]["classResources"]
        assert res["sheet"]["damageModifiers"] == plain["sheet"]["damageModifiers"]
        row = next(f for f in res["sheet"]["features"] if f["name"] == "Primal Companion")
        assert row["choice"] == [reference_data.SUBCLASS_OPTIONS_2024[FEATURE[COMPANION]]["options"][key]["name"]]


# ---- mixed / 2014 / SRD-only --------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cid", list(FEATURE))
def test_mixed_and_2014_have_no_effect_from_a_stored_pick(catalog, cid):
    key = next(iter(reference_data.SUBCLASS_OPTIONS_2024[FEATURE[cid]]["options"]))
    for ruleset in ("mixed", "2014"):
        with_pick = _one(catalog, cid, key, ruleset=ruleset, added=["longbow"])
        without = _one(catalog, cid, None, ruleset=ruleset, added=["longbow"])
        assert with_pick["sheet"]["senses"] == without["sheet"]["senses"]
        assert with_pick["derived"]["speeds"] == without["derived"]["speeds"]
        assert with_pick["derived"]["attacks"] == without["derived"]["attacks"]
        assert with_pick["derived"]["classResources"] == without["derived"]["classResources"]
        assert with_pick["sheet"]["damageModifiers"] == without["sheet"]["damageModifiers"]


@needs_data
def test_mixed_stored_owl_and_fire_do_nothing(catalog):
    assert "darkvision" not in _one(catalog, ASPECT, "owl", ruleset="mixed")["sheet"]["senses"]
    assert "fire" not in _one(catalog, AFFINITY, "fire", ruleset="mixed")["sheet"]["damageModifiers"]["resistances"]


@needs_data
def test_patched_srd_only_catalog_has_no_cards_and_no_crash(catalog):
    bare = _srd_only(catalog)
    for cid in FEATURE:
        key = next(iter(reference_data.SUBCLASS_OPTIONS_2024[FEATURE[cid]]["options"]))
        res = _one(bare, cid, key, added=["longbow"])
        assert _card(res, cid) is None
    assert subclass_options_2024.templates(bare, {"cls": {"name": "Ranger"}, "cls_id": "ranger", "subclass_id": "hunter-xphb",
                                                   "level": 20, "class_choices": {}}, "2024") == []


# ---- helper contract --------------------------------------------------------------------------

@needs_data
def test_spec_for_card_maps_cards_back(catalog):
    res = _one(catalog, PREY)
    card = _card(res, PREY)
    assert subclass_options_2024.spec_for_card(card)[0] == FEATURE[PREY]
    other = next(c for c in res["choices"] if c["id"] != PREY)
    assert subclass_options_2024.spec_for_card(other) is None


# ---- timing -------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("classes", [
    [("fighter", 20, "champion-xphb", {})],
    [("wizard", 20, "diviner-xphb", {})],
    [("bard", 20, "lore-xphb", {})],
    [("ranger", 7, "hunter-xphb", {PREY: [f"{FEATURE[PREY]}--colossus-slayer"], TACTICS: [f"{FEATURE[TACTICS]}--escape-the-horde"]})],
    [("barbarian", 6, "wild-heart-xphb", {ASPECT: [f"{FEATURE[ASPECT]}--owl"]})],
    [("sorcerer", 6, "draconic-xphb", {AFFINITY: [f"{FEATURE[AFFINITY]}--fire"]})],
])
def test_resolve_speed(catalog, classes):
    draft = _draft(classes)
    resolve(draft, catalog)
    start = time.perf_counter()
    for _ in range(10):
        resolve(draft, catalog)
    assert (time.perf_counter() - start) / 10 < 0.05
