"""C3: under ruleset 2024 the Fighter / Paladin / Ranger "Fighting Style" feature is a
Fighting Style FEAT choice (XPHB: "you gain a Fighting Style feat of your choice"),
and Fighting Style feats join the Ability Score Improvement pools of characters that
have a Fighting Style feature (resolves U3).

Rules (XPHB class features read from the 5etools files on 2026-10-10):
- Fighter level 1 "Fighting Style": a Fighting Style feat (category FS) of your choice.
- Paladin level 2 / Ranger level 2: same; Blessed Warrior (FS:P) is the Paladin's own
  extra option, Druidic Warrior (FS:R) the Ranger's.
- Champion (XPHB) level 7 "Additional Fighting Style": another Fighting Style feat.
- Every FS feat has the prerequisite "Fighting Style feature"; a feat cannot be taken twice.

Verified by script: 13 FS-category feats = 10 XPHB FS + Arcane Warrior (AU, ruleset
2014) + Blessed Warrior (FS:P) + Druidic Warrior (FS:R). `ruleset_allows` keeps 2014
feats visible under 2024 (the existing A1 2024 pool already holds the AU "G" feats), so
with no source filter the Fighter card has 11 options (10 XPHB + Arcane Warrior AU),
Paladin and Ranger 12; with sources that exclude AU, 10 / 11.

Matrix: ruleset (2024 / mixed / 2014) x class (fighter / paladin / ranger / wizard) x
level (feature gained / not yet) x source of the pick (feature card / ASI card / stored
SRD pick) x state (taken, hidden, pruned) x effect (AC, attacks, senses, cantrips)."""
import pytest

from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="2024", added=(), choices=None, sources=None, subclass=None, prereq=False):
    draft = {
        "ruleset": ruleset, "sources": sources or [], "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": list(added), "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": (choices or {}).get(c, {}),
                     **({"subclassId": (subclass or {}).get(c)} if (subclass or {}).get(c) else {})}
                    for c, lv in classes],
    }
    if prereq:
        draft["preferences"] = {"usePrerequisites": {"feats": True}}
    return resolve(draft, catalog)


def _card(res, cls, lvl):
    return next((c for c in res["choices"] if c["id"] == f"class:{cls}:{lvl}:fighting-style"), None)


def _old_card(res, cls, lvl, feature):
    return next((c for c in res["choices"] if c["id"] == f"class:{cls}:{lvl}:feature:{feature}"), None)


def _opt(card, feat_id):
    return next((o for o in card["options"] if o["id"] == f"feat:{feat_id}"), None)


def _asi(res, cls, lvl):
    return next(c for c in res["choices"] if c["id"] == f"class:{cls}:{lvl}:asi")


# ---- the feature card --------------------------------------------------------

@needs_data
def test_fighter_1_2024_card_is_a_feat_choice(catalog):
    res = _res(catalog, [("fighter", 1)])
    card = _card(res, "fighter", 1)
    assert card["count"] == 1 and card["status"] == "pending"
    assert card["source"]["kind"] == "class" and card["source"]["level"] == 1
    ids = [o["id"] for o in card["options"]]
    assert len(ids) == 10  # G1: XPHB lists exactly ten; Arcane Warrior (AU) needs AU enabled
    assert all(i.startswith("feat:") for i in ids)
    assert len(_card(_res(catalog, [("fighter", 1)], sources=["srd", "xphb"]), "fighter", 1)["options"]) == 10
    for want in ("archery", "blind-fighting", "defense", "dueling", "great-weapon-fighting", "interception",
                 "protection", "thrown-weapon-fighting", "two-weapon-fighting", "unarmed-fighting"):
        assert f"feat:{want}-xphb" in ids
    for no in ("feat:blessed-warrior-xphb", "feat:druidic-warrior-xphb"):
        assert no not in ids
    assert "feat:arcane-warrior-au" not in ids
    assert not any(o.get("disabled") for o in card["options"])
    assert _old_card(res, "fighter", 1, "fighter-fighting-style") is None


@needs_data
def test_fighter_1_2014_and_mixed_keep_the_srd_card(catalog):
    for ruleset in ("2014", "mixed"):
        res = _res(catalog, [("fighter", 1)], ruleset)
        assert _card(res, "fighter", 1) is None
        old = _old_card(res, "fighter", 1, "fighter-fighting-style")
        assert old and len(old["options"]) == 6


@needs_data
def test_paladin_2_offers_blessed_warrior_not_before_level_2(catalog):
    assert _card(_res(catalog, [("paladin", 1)]), "paladin", 2) is None
    res = _res(catalog, [("paladin", 2)])
    card = _card(res, "paladin", 2)
    assert len(card["options"]) == 11  # G1: no Arcane Warrior (AU) without AU enabled
    assert _opt(card, "blessed-warrior-xphb") and not _opt(card, "druidic-warrior-xphb")
    assert _old_card(res, "paladin", 2, "paladin-fighting-style") is None


@needs_data
def test_ranger_2_offers_druidic_warrior(catalog):
    card = _card(_res(catalog, [("ranger", 2)]), "ranger", 2)
    assert len(card["options"]) == 11
    assert _opt(card, "druidic-warrior-xphb") and not _opt(card, "blessed-warrior-xphb")


@needs_data
def test_other_classes_have_no_fighting_style_card(catalog):
    for cls in ("wizard", "barbarian", "bard"):
        res = _res(catalog, [(cls, 3)])
        assert not any(c["id"].endswith(":fighting-style") for c in res["choices"])


@needs_data
def test_pick_becomes_a_feat_with_origin_and_level(catalog):
    res = _res(catalog, [("fighter", 1)], choices={"fighter": {"class:fighter:1:fighting-style": ["feat:defense-xphb"]}})
    assert _card(res, "fighter", 1)["status"] == "resolved"
    feat = next(f for f in res["sheet"]["feats"] if f["id"] == "defense-xphb")
    assert feat["origin"] == "fighting-style" and feat["level"] == 1 and feat["name"] == "Defense"
    assert "defense-xphb" in res["sheet"]["grantedFeats"]
    assert res["problems"] == []


# ---- effects -----------------------------------------------------------------

CHAIN = [{"itemId": "chain-mail", "qty": 1, "equipped": True}]


@needs_data
def test_defense_in_chain_mail_is_ac_17(catalog):
    base = _res(catalog, [("fighter", 1)], added=CHAIN)
    assert base["derived"]["armorClass"] == 16
    res = _res(catalog, [("fighter", 1)], added=CHAIN,
               choices={"fighter": {"class:fighter:1:fighting-style": ["feat:defense-xphb"]}})
    assert res["derived"]["armorClass"] == 17
    unarmored = _res(catalog, [("fighter", 1)],
                     choices={"fighter": {"class:fighter:1:fighting-style": ["feat:defense-xphb"]}})
    assert unarmored["derived"]["armorClass"] == 12  # no armor: no bonus


@needs_data
def test_defense_picked_at_an_asi_also_applies(catalog):
    res = _res(catalog, [("fighter", 4)], added=CHAIN,
               choices={"fighter": {"class:fighter:4:asi": ["feat:defense-xphb"]}})
    assert res["derived"]["armorClass"] == 17


def _attack(res, item_id):
    return next(a for a in res["derived"]["attacks"] if a["itemId"] == item_id)


def _gear(*ids):
    return [{"itemId": i, "qty": 1, "equipped": True} for i in ids]


@needs_data
def test_archery_adds_two_to_ranged_attacks(catalog):
    plain = _attack(_res(catalog, [("fighter", 1)], added=_gear("longbow")), "longbow")
    res = _res(catalog, [("fighter", 1)], added=_gear("longbow"),
               choices={"fighter": {"class:fighter:1:fighting-style": ["feat:archery-xphb"]}})
    assert _attack(res, "longbow")["attackBonus"] == plain["attackBonus"] + 2


@needs_data
def test_dueling_gives_dueling_damage_not_greatsword(catalog):
    res = _res(catalog, [("fighter", 1)], added=_gear("longsword", "greatsword"),
               choices={"fighter": {"class:fighter:1:fighting-style": ["feat:dueling-xphb"]}})
    sword = _attack(res, "longsword")
    assert sword["duelingDamage"] and sword["duelingDamage"] != sword["damage"]
    assert _attack(res, "greatsword")["duelingDamage"] is None


@needs_data
def test_two_weapon_fighting_adds_modifier_to_offhand(catalog):
    plain = _attack(_res(catalog, [("fighter", 1)], added=_gear("shortsword")), "shortsword")
    res = _res(catalog, [("fighter", 1)], added=_gear("shortsword"),
               choices={"fighter": {"class:fighter:1:fighting-style": ["feat:two-weapon-fighting-xphb"]}})
    assert plain["offhandDamage"] == "1d6" and _attack(res, "shortsword")["offhandDamage"] == "1d6+2"


@needs_data
def test_great_weapon_fighting_2024_note_is_not_the_2014_reroll(catalog):
    res = _res(catalog, [("fighter", 1)], added=_gear("greatsword"),
               choices={"fighter": {"class:fighter:1:fighting-style": ["feat:great-weapon-fighting-xphb"]}})
    notes = _attack(res, "greatsword")["notes"]
    assert any("treat 1s and 2s as 3" in n for n in notes) and not any("reroll" in n for n in notes)


@needs_data
def test_thrown_weapon_fighting_notes_plus_two_on_thrown_weapons(catalog):
    res = _res(catalog, [("fighter", 1)], added=_gear("handaxe", "longsword"),
               choices={"fighter": {"class:fighter:1:fighting-style": ["feat:thrown-weapon-fighting-xphb"]}})
    assert any("Thrown Weapon Fighting" in n and "+2" in n for n in _attack(res, "handaxe")["notes"])
    assert not any("Thrown Weapon Fighting" in n for n in _attack(res, "longsword")["notes"])


@needs_data
def test_blind_fighting_grants_blindsight(catalog):
    res = _res(catalog, [("fighter", 1)], choices={"fighter": {"class:fighter:1:fighting-style": ["feat:blind-fighting-xphb"]}})
    assert res["sheet"]["senses"].get("blindsight") == 10


@needs_data
def test_blessed_warrior_cascades_its_cantrip_choice(catalog):
    res = _res(catalog, [("paladin", 2)], choices={"paladin": {"class:paladin:2:fighting-style": ["feat:blessed-warrior-xphb"]}})
    cascaded = [c for c in res["choices"] if c["id"].startswith("class:paladin:2:fighting-style:feat:blessed-warrior-xphb:")]
    assert cascaded and cascaded[0]["count"] == 2


# ---- prune / duplicate / filters --------------------------------------------

@needs_data
def test_stored_srd_pick_is_pruned_under_2024(catalog):
    old = "class:fighter:1:feature:fighter-fighting-style"
    res = _res(catalog, [("fighter", 1)], added=_gear("longbow"),
               choices={"fighter": {old: ["fighter-fighting-style-archery"]}})
    assert any(p["choiceId"] == old for p in res["pruned"])
    assert _card(res, "fighter", 1)["selected"] == []
    plain = _attack(_res(catalog, [("fighter", 1)], added=_gear("longbow")), "longbow")
    assert _attack(res, "longbow")["attackBonus"] == plain["attackBonus"]


@needs_data
def test_stored_feat_pick_is_pruned_under_2014_and_mixed(catalog):
    cid = "class:fighter:1:fighting-style"
    for ruleset in ("2014", "mixed"):
        res = _res(catalog, [("fighter", 1)], ruleset, choices={"fighter": {cid: ["feat:defense-xphb"]}})
        assert any(p["choiceId"] == cid for p in res["pruned"])
        assert not any(f["id"] == "defense-xphb" for f in res["sheet"]["feats"])


@needs_data
def test_unknown_or_non_fs_stored_pick_is_dropped(catalog):
    cid = "class:fighter:1:fighting-style"
    res = _res(catalog, [("fighter", 1)], choices={"fighter": {cid: ["feat:alert-xphb", "feat:blessed-warrior-xphb"]}})
    assert _card(res, "fighter", 1)["selected"] == []
    assert not any(f["id"] in ("alert-xphb", "blessed-warrior-xphb") for f in res["sheet"]["feats"])


@needs_data
def test_champion_additional_fighting_style_cannot_repeat(catalog):
    res = _res(catalog, [("fighter", 7)], subclass={"fighter": "champion-xphb"}, choices={"fighter": {
        "class:fighter:1:fighting-style": ["feat:defense-xphb"],
        "class:fighter:7:fighting-style": ["feat:defense-xphb"]}})
    second = _card(res, "fighter", 7)
    assert second and _opt(second, "defense-xphb")["disabled"]
    assert "already taken" in _opt(second, "defense-xphb")["disabledReason"]
    assert second["selected"] == [] or not any(f["id"] == "defense-xphb" and f["level"] == 7 for f in res["sheet"]["feats"])
    assert any(p["id"].startswith("feat-duplicate-defense-xphb") for p in res["problems"])
    assert sum(1 for f in res["sheet"]["feats"] if f["id"] == "defense-xphb") == 1
    ok = _res(catalog, [("fighter", 7)], subclass={"fighter": "champion-xphb"}, choices={"fighter": {
        "class:fighter:1:fighting-style": ["feat:defense-xphb"],
        "class:fighter:7:fighting-style": ["feat:archery-xphb"]}})
    assert {f["id"] for f in ok["sheet"]["feats"]} >= {"defense-xphb", "archery-xphb"}
    assert ok["problems"] == []


def _problem_ids(res):
    return [p["id"] for p in res["problems"] if p["id"].startswith("feat-duplicate-")]


@needs_data
def test_duplicate_blames_the_later_pick_across_asi_and_fighting_style(catalog):
    """F1 (1): picks are ordered by class level whatever their kind, so the LATER pick is the
    duplicate. Champion 8: ASI at 4, 6, 8; fighting-style cards at 1 and 7."""
    sub = {"fighter": "champion-xphb"}
    # ASI at 4 comes before the level-7 card: the card is the duplicate.
    res = _res(catalog, [("fighter", 8)], subclass=sub, choices={"fighter": {
        "class:fighter:4:asi": ["feat:archery-xphb"], "class:fighter:7:fighting-style": ["feat:archery-xphb"]}})
    assert _problem_ids(res) == ["feat-duplicate-archery-xphb-class:fighter:7:fighting-style"]
    feats = [f for f in res["sheet"]["feats"] if f["id"] == "archery-xphb"]
    assert len(feats) == 1 and feats[0]["origin"] == "asi" and feats[0]["level"] == 4
    card7 = _card(res, "fighter", 7)
    assert _opt(card7, "archery-xphb")["disabled"] and _opt(card7, "archery-xphb")["disabledReason"] == "already taken"
    asi4 = next(o for o in _asi(res, "fighter", 4)["options"] if o["id"] == "feat:archery-xphb")
    assert not asi4.get("disabled")
    # The card at 7 comes before the ASI at 8: the ASI pick is the duplicate.
    res = _res(catalog, [("fighter", 8)], subclass=sub, choices={"fighter": {
        "class:fighter:7:fighting-style": ["feat:archery-xphb"], "class:fighter:8:asi": ["feat:archery-xphb"]}})
    assert _problem_ids(res) == ["feat-duplicate-archery-xphb-class:fighter:8:asi"]
    asi8 = next(o for o in _asi(res, "fighter", 8)["options"] if o["id"] == "feat:archery-xphb")
    assert asi8["disabled"] and asi8["disabledReason"] == "already taken"
    # An ASI at 4 does not block a LOWER card (level 1).
    res = _res(catalog, [("fighter", 8)], subclass=sub, choices={"fighter": {
        "class:fighter:1:fighting-style": ["feat:archery-xphb"], "class:fighter:4:asi": ["feat:archery-xphb"]}})
    assert _problem_ids(res) == ["feat-duplicate-archery-xphb-class:fighter:4:asi"]


@needs_data
def test_no_second_card_without_champion(catalog):
    res = _res(catalog, [("fighter", 7)])
    assert _card(res, "fighter", 7) is None and _card(res, "fighter", 1)


@needs_data
def test_multiclass_fighter_paladin_cards_and_duplicate_state(catalog):
    res = _res(catalog, [("fighter", 1), ("paladin", 2)], choices={
        "fighter": {"class:fighter:1:fighting-style": ["feat:dueling-xphb"]}})
    pal = _card(res, "paladin", 2)
    assert _opt(pal, "dueling-xphb")["disabled"] and "already taken" in _opt(pal, "dueling-xphb")["disabledReason"]
    assert not _opt(pal, "defense-xphb").get("disabled")


@needs_data
def test_pick_hidden_by_sources_stays_selected_with_warning(catalog):
    cid = "class:fighter:1:fighting-style"
    res = _res(catalog, [("fighter", 1)], sources=["srd", "xphb"], choices={"fighter": {cid: ["feat:defense-xphb"]}})
    assert any(f["id"] == "defense-xphb" for f in res["sheet"]["feats"])
    # Arcane Warrior (AU) is outside sources srd+xphb: it stays selected, flagged and warned.
    au = _res(catalog, [("fighter", 1)], sources=["srd", "xphb"], choices={"fighter": {cid: ["feat:arcane-warrior-au"]}})
    assert any(f["id"] == "arcane-warrior-au" for f in au["sheet"]["feats"])
    assert _opt(_card(au, "fighter", 1), "arcane-warrior-au")["hiddenByFilters"]
    assert any(w["id"] == f"feat-hidden-by-filters-{cid}" for w in au["warnings"])


@needs_data
def test_sources_without_fs_feats_fall_back_to_the_srd_card(catalog):
    res = _res(catalog, [("fighter", 1)], sources=["srd"])
    assert _card(res, "fighter", 1) is None
    assert _old_card(res, "fighter", 1, "fighter-fighting-style")


# ---- ASI pools ----------------------------------------------------------------

@needs_data
def test_fighter_4_2024_asi_offers_fs_feats(catalog):
    res = _res(catalog, [("fighter", 4)])
    opts = _asi(res, "fighter", 4)["options"]
    archery = next(o for o in opts if o["id"] == "feat:archery-xphb")
    assert not archery.get("disabled")
    ids = {o["id"] for o in opts}
    # F1: Blessed / Druidic Warrior need the level-2 Paladin / Ranger feature: not in ASI pools.
    assert not {"feat:blessed-warrior-xphb", "feat:druidic-warrior-xphb"} & ids
    assert "feat:arcane-warrior-au" not in ids  # G1: AU Fighting Style feat needs AU enabled under 2024
    taken = _res(catalog, [("fighter", 4)], choices={"fighter": {"class:fighter:1:fighting-style": ["feat:archery-xphb"]}})
    state = next(o for o in _asi(taken, "fighter", 4)["options"] if o["id"] == "feat:archery-xphb")
    assert state["disabled"] and state["disabledReason"] == "already taken"


@needs_data
def test_blessed_and_druidic_warrior_only_from_their_class_cards(catalog):
    """F1: FS:P / FS:R need the level-2 Paladin / Ranger Fighting Style feature, so they are
    not ASI options for anyone (Fighter, Paladin or Ranger), only on the class cards."""
    for cls, feat in (("paladin", "blessed-warrior-xphb"), ("ranger", "druidic-warrior-xphb")):
        res = _res(catalog, [(cls, 4)], choices={cls: {f"class:{cls}:4:asi": [f"feat:{feat}"]}})
        assert _opt(_asi(res, cls, 4), feat) is None
        assert _opt(_card(res, cls, 2), feat) and not _opt(_card(res, cls, 2), feat).get("disabled")
        assert not any(f["id"] == feat for f in res["sheet"]["feats"])
        assert any(p["choiceId"] == f"class:{cls}:4:asi" for p in res["pruned"])
        via_card = _res(catalog, [(cls, 4)], choices={cls: {f"class:{cls}:2:fighting-style": [f"feat:{feat}"]}})
        assert any(f["id"] == feat for f in via_card["sheet"]["feats"])


@needs_data
def test_wizard_4_asi_has_no_fs_feats(catalog):
    for ruleset in ("2024", "mixed"):
        ids = {o["id"] for o in _asi(_res(catalog, [("wizard", 4)], ruleset), "wizard", 4)["options"]}
        assert not any(i.startswith("feat:") and i.split(":")[1] in {
            "archery-xphb", "defense-xphb", "blessed-warrior-xphb", "arcane-warrior-au"} for i in ids)


@needs_data
def test_fighter_1_wizard_4_multiclass_wizard_asi_offers_fs(catalog):
    res = _res(catalog, [("wizard", 4), ("fighter", 1)])
    ids = {o["id"] for o in _asi(res, "wizard", 4)["options"]}
    assert "feat:archery-xphb" in ids  # the character holds a Fighting Style feature


@needs_data
def test_fighter_4_2014_pool_has_no_fs_feats(catalog):
    ids = {o["id"] for o in _asi(_res(catalog, [("fighter", 4)], "2014"), "fighter", 4)["options"]}
    assert not any("archery" in i or "blessed-warrior" in i or "arcane-warrior" in i for i in ids)


@needs_data
def test_fighter_4_mixed_pool_has_fs_feats(catalog):
    ids = {o["id"] for o in _asi(_res(catalog, [("fighter", 4)], "mixed"), "fighter", 4)["options"]}
    assert {"feat:archery-xphb", "feat:arcane-warrior-au"} <= ids


@needs_data
def test_asi_pick_of_fs_feat_is_applied_and_wizard_pick_is_dropped(catalog):
    res = _res(catalog, [("fighter", 4)], choices={"fighter": {"class:fighter:4:asi": ["feat:archery-xphb"]}})
    assert any(f["id"] == "archery-xphb" and f["origin"] == "asi" for f in res["sheet"]["feats"])
    bad = _res(catalog, [("wizard", 4)], choices={"wizard": {"class:wizard:4:asi": ["feat:archery-xphb"]}})
    assert not any(f["id"] == "archery-xphb" for f in bad["sheet"]["feats"])
    assert any(p["choiceId"] == "class:wizard:4:asi" for p in bad["pruned"])


@needs_data
def test_fs_feature_prerequisite_is_enforced_for_the_gate(catalog):
    from engine.resolve import _HeldFeatState, _feat_prerequisite_unmet_reason
    feat = catalog.feats["archery-xphb"]
    assert _feat_prerequisite_unmet_reason(feat, 4, {}, True, _HeldFeatState(), catalog)
    assert _feat_prerequisite_unmet_reason(feat, 4, {}, True, _HeldFeatState(fighting_style=True), catalog) is None


# ---- robustness ---------------------------------------------------------------

def test_srd_only_catalog_does_not_crash_and_keeps_the_srd_card():
    cat = load()
    cat.feats = {}
    res = _res(cat, [("fighter", 4), ("paladin", 2)])
    assert not any(c["id"].endswith(":fighting-style") for c in res["choices"])
    assert _old_card(res, "fighter", 1, "fighter-fighting-style")
    assert res["sheet"]["feats"] == []


@needs_data
def test_resolve_speed_fighter_20(catalog):
    import time
    _res(catalog, [("fighter", 20)], choices={"fighter": {"class:fighter:1:fighting-style": ["feat:defense-xphb"]}})
    start = time.perf_counter()
    for _ in range(20):
        _res(catalog, [("fighter", 20)], choices={"fighter": {"class:fighter:1:fighting-style": ["feat:defense-xphb"]}})
    assert (time.perf_counter() - start) / 20 < 0.05


@needs_data
def test_arcane_warrior_and_druidic_warrior_cascade_without_crashing(catalog):
    res = _res(catalog, [("fighter", 1)], choices={"fighter": {"class:fighter:1:fighting-style": ["feat:arcane-warrior-au"]}})
    assert any(f["id"] == "arcane-warrior-au" for f in res["sheet"]["feats"])
    assert any(c["id"].startswith("class:fighter:1:fighting-style:feat:arcane-warrior-au:") for c in res["choices"])
    res = _res(catalog, [("ranger", 2)], choices={"ranger": {"class:ranger:2:fighting-style": ["feat:druidic-warrior-xphb"]}})
    assert any(c["id"].startswith("class:ranger:2:fighting-style:feat:druidic-warrior-xphb:") for c in res["choices"])


# ---- G1-5: unofficial (AU) Fighting Style feats under 2024 ---------------------

@needs_data
def test_arcane_warrior_au_needs_au_enabled_under_2024(catalog):
    """XPHB chapter 5 lists exactly ten Fighting Style feats (plus Blessed / Druidic
    Warrior from the class text). Arcane Warrior is Unearthed Arcana: under 2024 it is
    offered (card and ASI pool) only when AU is an explicitly selected source."""
    res = _res(catalog, [("fighter", 4)])  # no source filter = no explicit AU
    ids = [o["id"] for o in _card(res, "fighter", 1)["options"]]
    assert len(ids) == 10 and "feat:arcane-warrior-au" not in ids
    assert "feat:arcane-warrior-au" not in {o["id"] for o in _asi(res, "fighter", 4)["options"]}
    res = _res(catalog, [("fighter", 4)], sources=["srd", "xphb", "au"])
    assert "feat:arcane-warrior-au" in [o["id"] for o in _card(res, "fighter", 1)["options"]]
    assert "feat:arcane-warrior-au" in {o["id"] for o in _asi(res, "fighter", 4)["options"]}
    # mixed keeps every edition and source when unfiltered
    assert "feat:arcane-warrior-au" in {o["id"] for o in _asi(_res(catalog, [("fighter", 4)], "mixed"), "fighter", 4)["options"]}


@needs_data
def test_stored_arcane_warrior_pick_stays_when_au_is_off(catalog):
    cid = "class:fighter:1:fighting-style"
    res = _res(catalog, [("fighter", 1)], choices={"fighter": {cid: ["feat:arcane-warrior-au"]}})
    opt = _opt(_card(res, "fighter", 1), "arcane-warrior-au")
    assert opt["hiddenByFilters"] is True
    assert _card(res, "fighter", 1)["selected"] == ["feat:arcane-warrior-au"]
