"""RP20 (A3, open question 15): 2024 pools for the option-pick feats (docs/superpowers/plans/2026-10-22-remaining-program.md).

Rule (PHB 2024, "the versions of things in this book replace versions from older books"; decision of the plan): under
ruleset 2024 the TCE / PHB option-pick feats draw from the 2024 class lists. mixed and 2014 keep the FE9 pools
(byte-identical; the F0 golden stays green and is never regenerated).

Governing sentences (catalog text, tags stripped; pinned by ``test_quote_matches_catalog_text``):

  Eldritch Adept (TCE)    "you learn one Eldritch Invocation option of your choice from the warlock class." / "If the
                          invocation has a prerequisite of any kind, you can choose that invocation only if you're a
                          warlock who meets the prerequisite."  -> the 28 XPHB invocations; a prerequisite
                          (``prerequisite_2024``: Warlock level, optional feature, damaging / attack cantrip) is met only
                          by a Warlock; a non-Warlock has level 0, so only the prerequisite-free ones are open.
  Metamagic Adept (TCE)   "You learn two Metamagic options of your choice from the sorcerer class."  -> the 10 XPHB
                          Metamagic options (Seeking Spell and Transmuted Spell are among them).
  Martial Adept (PHB)     "You learn two maneuvers of your choice from among those available to the Battle Master
                          archetype in the fighter class."  -> the 20 maneuvers of the XPHB Battle Master.
  Fighting Initiate (TCE) keeps the six SRD fighter styles under every ruleset (no 2024 "style option" record exists;
                          the same-named FS effects already apply; the 2024 Fighting Style FEATS are a user decision,
                          see ARCHITECTURE-CURRENT-STATE open question 15).
  Dependents (A3b)        a feat-held Agonizing Blast / Eldritch Spear / Repelling Blast has its target-cantrip card,
                          Pact of the Tome its cantrip / ritual cards, Pact of the Blade its weapon card (the C7c
                          builders with the feat card as holder); Lessons of the First Ones through the feat (A3c).

Matrix: feat x ruleset (2014, mixed, 2024) x class (Wizard, Sorcerer, Fighter, Warlock) x pool x prerequisite (level /
Pact / cantrip) x duplicate with the class card (both pools) x stale SRD pick x effects (AC formula, senses, innate
spell) x no-feat identity x SRD-only catalog x timing."""
import copy
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import class_choices_2024 as cc
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

EA, MA, MMA, FI = "eldritch-adept-tce", "martial-adept-phb", "metamagic-adept-tce", "fighting-initiate-tce"
X = "opt-{}-xphb"
AGON, SPEAR, REPEL = X.format("agonizing-blast"), X.format("eldritch-spear"), X.format("repelling-blast")
BLADE, CHAIN, TOME = X.format("pact-of-the-blade"), X.format("pact-of-the-chain"), X.format("pact-of-the-tome")
THIRST, LESSONS = X.format("thirsting-blade"), X.format("lessons-of-the-first-ones")
ARMOR, DEVIL, MIND = X.format("armor-of-shadows"), X.format("devils-sight"), X.format("eldritch-mind")
INV = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
CANT = "class:warlock:spells-cantrips"
BM2024 = "class:fighter:3:feature:battle-master-xphb-3-battle-master"
SORC_MM = "class:sorcerer:2:feature:xphb-sorcerer-2-metamagic"
ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


def _plain(node):
    out = []

    def walk(n):
        if isinstance(n, str):
            out.append(n)
        elif isinstance(n, dict):
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(node)

    def tag(m):
        parts = m.group(2).split("|")
        if m.group(1) == "filter":
            return parts[0]
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, " ".join(out))


@pytest.fixture(scope="module")
def catalog():
    return load()


def cid_of(cls, level, feat, suffix):
    return f"class:{cls}:{level}:asi:feat:{feat}:{suffix}"


def _draft(classes, ruleset="2024", weapons=()):
    scores = {a: 10 for a in ABS}
    scores["CHA"] = 16
    return {"name": "t", "ruleset": ruleset, "sources": [],
            "classes": [{"classId": c, "level": lv, "choices": ch, **({"subclassId": sub} if sub else {})}
                        for c, lv, ch, sub in classes],
            "background": {"id": "soldier-xphb" if ruleset == "2024" else "acolyte", "choices": {}},
            "species": {"id": "human-xphb" if ruleset == "2024" else "human", "choices": {}},
            "abilities": {"method": "manual", "base": scores},
            "equipment": {"choices": {}, "added": [{"itemId": w, "qty": 1, "equipped": True} for w in weapons],
                          "skipped": False}, "details": {}, "preferences": {}}


def run(catalog, cls, level, feat, picks=None, ruleset="2024", class_choices=None, subclass=None, asi=4, weapons=()):
    ch = {f"class:{cls}:{asi}:asi": [f"feat:{feat}"], **(class_choices or {})}
    for suffix, sel in (picks or {}).items():
        ch[cid_of(cls, asi, feat, suffix)] = sel
    return resolve(_draft([(cls, level, ch, subclass)], ruleset=ruleset, weapons=weapons), catalog)


def _card(r, cid):
    return next((c for c in r["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _ids(card):
    return [o["id"] for o in card["options"]]


def _res(r, name):
    return next((x for x in r["derived"]["featResources"] if x["name"] == name), None)


def _pruned(r, cid):
    return " | ".join(p["reason"] for p in r["pruned"] if p["choiceId"] == cid)


def ea_card(r, cls="wizard", level=4):
    return _card(r, cid_of(cls, level, EA, "invocation"))


# ---------------------------------------------------------------- data (quote matches catalog text)


@pytest.mark.parametrize("feat,quote", [
    (EA, "you learn one Eldritch Invocation option of your choice from the warlock class"),
    (EA, "you can choose that invocation only if you're a warlock who meets the prerequisite"),
    (MMA, "You learn two Metamagic options of your choice from the sorcerer class"),
    (MA, "You learn two maneuvers of your choice from among those available to the Battle Master archetype in the fighter class"),
    (FI, "you learn one Fighting Style option of your choice from the fighter class"),
])
def test_quote_matches_catalog_text(catalog, feat, quote):
    assert quote in _plain(catalog.feats[feat]["entries"]).replace("learn one Eldritch Invocation", "learn one Eldritch Invocation")


@pytest.mark.parametrize("feature,quote", [
    (AGON, "Choose one of your known Warlock cantrips that deals damage."),
    (SPEAR, "Choose one of your known Warlock cantrips that deals damage and has a range of 10+ feet."),
    (REPEL, "Choose one of your known Warlock cantrips that requires an attack roll."),
    (LESSONS, "gain one Origin feat of your choice"),
    (TOME, "choose three cantrips, and choose two level 1 spells that have the Ritual tag"),
    (BLADE, "a Simple or Martial Melee weapon of your choice with which you bond"),
    (X.format("seeking-spell"), "If you make an attack roll for a spell and miss, you can spend 1 Sorcery Point to reroll the d20"),
    (X.format("transmuted-spell"), "When you cast a spell that deals a type of damage"),
    (X.format("parry"), "When another creature damages you with a melee attack roll"),
    (X.format("riposte"), "When a creature misses you with a melee attack roll"),
])
def test_xphb_option_text_matches_catalog(catalog, feature, quote):
    assert quote in _plain(catalog.features[feature]["desc"])


def test_xphb_prerequisites_are_the_pinned_ones(catalog):
    pre = {k: catalog.features[k]["prerequisite_2024"] for k in (AGON, SPEAR, REPEL, LESSONS, THIRST, ARMOR, TOME)}
    assert (pre[AGON]["level"], pre[AGON]["cantrip"]) == (2, "damage")
    assert (pre[SPEAR]["level"], pre[SPEAR]["cantrip"]) == (2, "damage")
    assert (pre[REPEL]["level"], pre[REPEL]["cantrip"]) == (2, "attack")
    assert pre[LESSONS]["level"] == 2 and pre[THIRST]["optional_features"] == [BLADE]
    assert pre[ARMOR]["level"] is None and pre[TOME]["level"] is None


# ---------------------------------------------------------------- pools


def test_pools_under_2024(catalog):
    f = catalog.features
    inv = ea_card(run(catalog, "wizard", 4, EA))
    assert _ids(inv) == sorted((k for k in f if k.startswith("opt-") and k.endswith("-xphb") and "EI" in (f[k].get("feature_types") or [])),
                               key=lambda k: f[k]["name"]) and len(inv["options"]) == 28
    assert inv["count"] == 1
    mm = _card(run(catalog, "wizard", 4, MMA), cid_of("wizard", 4, MMA, "metamagic"))
    assert [o["id"] for o in mm["options"]] == sorted(
        (k for k in f if k.endswith("-xphb") and "MM" in (f[k].get("feature_types") or [])), key=lambda k: f[k]["name"])
    assert len(mm["options"]) == 10 and "Seeking Spell (1 SP)" in [o["label"] for o in mm["options"]]
    assert "Transmuted Spell (1 SP)" in [o["label"] for o in mm["options"]] and "Heightened Spell (2 SP)" in [o["label"] for o in mm["options"]]
    bm = f["battle-master-xphb-3-battle-master"]["feature_specific"]["optional_progression"]["options"]
    ma = _card(run(catalog, "wizard", 4, MA), cid_of("wizard", 4, MA, "maneuvers"))
    assert _ids(ma) == bm and len(bm) == 20 and ma["count"] == 2


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_pools_under_mixed_and_2014_are_the_fe9_ones(catalog, ruleset):
    f = catalog.features
    inv = ea_card(run(catalog, "wizard", 4, EA, ruleset=ruleset))
    assert _ids(inv) == [r["index"] for r in f["eldritch-invocations"]["feature_specific"]["invocations"]] and len(inv["options"]) == 32
    mm = _card(run(catalog, "wizard", 4, MMA, ruleset=ruleset), cid_of("wizard", 4, MMA, "metamagic"))
    assert len(mm["options"]) == 8 and all(o["id"].startswith("metamagic-") for o in mm["options"])
    ma = _card(run(catalog, "wizard", 4, MA, ruleset=ruleset), cid_of("wizard", 4, MA, "maneuvers"))
    assert len(ma["options"]) == 23 and all(o["id"].endswith("-phb") or o["id"].endswith("-tce") for o in ma["options"])


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_fighting_initiate_keeps_the_six_srd_styles(catalog, ruleset):
    card = _card(run(catalog, "wizard", 4, FI, ruleset=ruleset), cid_of("wizard", 4, FI, "fighting-style"))
    assert {o["label"] for o in card["options"]} == {
        "Archery", "Defense", "Dueling", "Great Weapon Fighting", "Protection", "Two-Weapon Fighting"}
    assert all(o["id"].startswith("fighter-fighting-style-") for o in card["options"])


# ---------------------------------------------------------------- Eldritch Adept prerequisites (2024 branch)


def test_ea_non_warlock_gets_only_the_prerequisite_free_invocations(catalog):
    card = ea_card(run(catalog, "wizard", 4, EA))
    open_ids = {o["id"] for o in card["options"] if not o.get("disabled")}
    assert open_ids == {ARMOR, MIND, BLADE, CHAIN, TOME}
    assert _opt(card, AGON)["disabledReason"] == "requires warlock level 2"
    assert _opt(card, SPEAR)["disabledReason"] == "requires warlock level 2"
    assert _opt(card, REPEL)["disabledReason"] == "requires warlock level 2"
    assert _opt(card, LESSONS)["disabledReason"] == "requires warlock level 2"
    assert _opt(card, X.format("witch-sight"))["disabledReason"] == "requires warlock level 15"
    assert _opt(card, THIRST)["disabled"]  # level 5 comes first


def test_ea_warlock_meets_level_cantrip_and_pact_prerequisites(catalog):
    own = {INV: [BLADE, MIND], CANT: ["eldritch-blast-xphb", "minor-illusion-xphb"]}
    card = ea_card(run(catalog, "warlock", 5, EA, {"invocation": [THIRST]}, class_choices=own), "warlock")
    assert not _opt(card, AGON).get("disabled") and not _opt(card, SPEAR).get("disabled")
    assert not _opt(card, REPEL).get("disabled") and not _opt(card, LESSONS).get("disabled")
    assert not _opt(card, THIRST).get("disabled") and card["selected"] == [THIRST] and card["status"] == "resolved"
    chain = ea_card(run(catalog, "warlock", 5, EA, {"invocation": [THIRST]}, class_choices={INV: [CHAIN], CANT: ["eldritch-blast-xphb"]}),
                    "warlock")
    assert _opt(chain, THIRST)["disabledReason"] == "requires Pact of the Blade" and chain["selected"] == []


def test_ea_cantrip_prerequisites_follow_the_warlock_cantrips(catalog):
    own = {INV: [MIND], CANT: ["minor-illusion-xphb", "mage-hand-xphb"]}
    card = ea_card(run(catalog, "warlock", 4, EA, class_choices=own), "warlock")
    assert _opt(card, AGON)["disabledReason"] == "requires a Warlock cantrip that deals damage"
    assert _opt(card, REPEL)["disabledReason"] == "requires a Warlock cantrip that requires an attack roll"
    assert not _opt(card, ARMOR).get("disabled")


def test_ea_stored_pick_with_an_unmet_prerequisite_is_dropped(catalog):
    cid = cid_of("wizard", 4, EA, "invocation")
    r = run(catalog, "wizard", 4, EA, {"invocation": [AGON]})
    assert ea_card(r)["selected"] == [] and ea_card(r)["status"] == "pending" and "Agonizing Blast" in _pruned(r, cid)
    kept = run(catalog, "wizard", 4, EA, {"invocation": [CHAIN]})
    assert ea_card(kept)["selected"] == [CHAIN] and ea_card(kept)["status"] == "resolved"


def test_ea_stored_srd_id_under_2024_is_pruned(catalog):
    cid = cid_of("wizard", 4, EA, "invocation")
    r = run(catalog, "wizard", 4, EA, {"invocation": ["eldritch-invocation-devils-sight"]})
    assert ea_card(r)["selected"] == [] and cid in {p["choiceId"] for p in r["pruned"]}
    again = run(catalog, "wizard", 4, EA, {"invocation": ["eldritch-invocation-devils-sight"]}, ruleset="mixed")
    assert ea_card(again)["selected"] == ["eldritch-invocation-devils-sight"]  # the same draft under mixed keeps it


def test_ea_duplicate_of_the_warlock_invocation_is_disabled_and_pruned(catalog):
    r = run(catalog, "warlock", 4, EA, {"invocation": [DEVIL]}, class_choices={INV: [DEVIL, ARMOR]}, )
    card = ea_card(r, "warlock")
    assert _opt(card, DEVIL)["disabledReason"] == "already taken (Devil's Sight, Warlock)"
    assert _opt(card, ARMOR)["disabledReason"] == "already taken (Armor of Shadows, Warlock)"
    assert card["selected"] == [] and "Devil's Sight" in _pruned(r, card["id"])
    assert _card(r, INV)["selected"] == [DEVIL, ARMOR]  # the class card is untouched (C7a)


def test_ea_duplicate_is_by_name_across_editions(catalog):
    r = run(catalog, "warlock", 4, EA, {"invocation": [CHAIN]}, class_choices={INV: [CHAIN]})
    assert ea_card(r, "warlock")["selected"] == []
    free = run(catalog, "warlock", 4, EA, {"invocation": [CHAIN]}, class_choices={INV: [ARMOR]})
    assert ea_card(free, "warlock")["selected"] == [CHAIN]


# ---------------------------------------------------------------- Eldritch Adept effects with XPHB ids


def test_ea_armor_of_shadows_gives_the_ac_formula_and_mage_armor(catalog):
    base = run(catalog, "wizard", 4, EA)
    r = run(catalog, "wizard", 4, EA, {"invocation": [ARMOR], "invocation-ability": ["int"]})
    assert r["derived"]["armorClass"] == base["derived"]["armorClass"] + 3  # 13 + DEX instead of 10 + DEX
    (spell,) = [s for s in r["sheet"]["innateSpells"] if s["spellId"] and s["spellId"].startswith("mage-armor")]
    assert spell["ability"] == "INT" and spell["uses"] == "at-will" and spell["source"] == "Eldritch Adept"


def test_ea_pact_of_the_chain_gives_find_familiar(catalog):
    r = run(catalog, "wizard", 4, EA, {"invocation": [CHAIN], "invocation-ability": ["wis"]})
    (spell,) = [s for s in r["sheet"]["innateSpells"] if (s["spellId"] or "").startswith("find-familiar")]
    assert spell["ability"] == "WIS" and spell["uses"] == "at-will" and spell["source"] == "Eldritch Adept"


def test_ea_devils_sight_needs_a_warlock_level_2(catalog):
    wizard = ea_card(run(catalog, "wizard", 4, EA, {"invocation": [DEVIL]}))
    assert wizard["selected"] == []
    r = run(catalog, "warlock", 4, EA, {"invocation": [DEVIL]}, class_choices={INV: [MIND, ARMOR]}, )
    assert r["sheet"]["senses"].get("devilsSight") == 120 and ea_card(r, "warlock")["selected"] == [DEVIL]


# ---------------------------------------------------------------- Metamagic Adept (XPHB list)


def test_mma_takes_seeking_spell_and_names_it(catalog):
    r = run(catalog, "wizard", 4, MMA, {"metamagic": [X.format("seeking-spell"), X.format("transmuted-spell")]})
    card = _card(r, cid_of("wizard", 4, MMA, "metamagic"))
    assert card["selected"] == [X.format("seeking-spell"), X.format("transmuted-spell")] and card["status"] == "resolved"
    res = _res(r, "Sorcery Points (Metamagic Adept)")
    assert res["uses"] == 2 and "Seeking Spell" in res["details"]["note"] and "Transmuted Spell" in res["details"]["note"]


def test_mma_duplicate_of_the_2024_sorcerer_metamagic(catalog):
    own = {SORC_MM: [X.format("careful-spell"), X.format("quickened-spell")]}
    r = run(catalog, "sorcerer", 4, MMA, {"metamagic": [X.format("careful-spell"), X.format("seeking-spell")]}, class_choices=own)
    card = _card(r, cid_of("sorcerer", 4, MMA, "metamagic"))
    assert _opt(card, X.format("careful-spell"))["disabledReason"] == "already taken (Careful Spell, Sorcerer)"
    assert card["selected"] == [X.format("seeking-spell")] and _card(r, SORC_MM)["selected"] == own[SORC_MM]
    assert "Careful Spell" in _pruned(r, card["id"])


def test_mma_stored_srd_ids_under_2024_are_pruned(catalog):
    cid = cid_of("wizard", 4, MMA, "metamagic")
    r = run(catalog, "wizard", 4, MMA, {"metamagic": ["metamagic-careful-spell", X.format("seeking-spell")]})
    assert _card(r, cid)["selected"] == [X.format("seeking-spell")] and cid in {p["choiceId"] for p in r["pruned"]}


# ---------------------------------------------------------------- Martial Adept (XPHB maneuvers)


def test_ma_takes_xphb_maneuvers_and_names_them(catalog):
    r = run(catalog, "wizard", 4, MA, {"maneuvers": [X.format("riposte"), X.format("parry")]})
    card = _card(r, cid_of("wizard", 4, MA, "maneuvers"))
    assert card["selected"] == [X.format("riposte"), X.format("parry")] and card["status"] == "resolved"
    res = _res(r, "Superiority Die (Martial Adept)")
    assert (res["uses"], res["die"]) == (1, "d6") and "Riposte" in res["details"]["note"] and "Parry" in res["details"]["note"]
    assert next(f for f in r["sheet"]["feats"] if f["id"] == MA)["choice"] == ["Riposte", "Parry"]


def test_ma_duplicate_of_a_2024_battle_master_maneuver(catalog):
    r = run(catalog, "fighter", 4, MA, {"maneuvers": [X.format("parry"), X.format("riposte")]}, subclass="battle-master-xphb",
            class_choices={BM2024: [X.format("parry"), X.format("rally"), X.format("trip-attack")]})
    card = _card(r, cid_of("fighter", 4, MA, "maneuvers"))
    assert _opt(card, X.format("parry"))["disabledReason"] == "already taken (Parry, Battle Master)"
    assert card["selected"] == [X.format("riposte")] and card["status"] == "pending"


def test_ma_stored_srd_maneuvers_under_2024_are_pruned(catalog):
    cid = cid_of("wizard", 4, MA, "maneuvers")
    r = run(catalog, "wizard", 4, MA, {"maneuvers": ["opt-parry-phb", X.format("riposte")]})
    assert _card(r, cid)["selected"] == [X.format("riposte")] and cid in {p["choiceId"] for p in r["pruned"]}


# ---------------------------------------------------------------- identity, degrade, timing


def test_a_character_without_the_feats_is_unchanged(catalog):
    base = _draft([("wizard", 4, {}, None)])
    r = resolve(base, catalog)
    assert not [c for c in r["choices"] if c["source"]["kind"] == "feat" and c["id"].endswith(
        (":invocation", ":metamagic", ":maneuvers"))]
    assert r["derived"]["featResources"] == []


def test_srd_only_catalog_falls_back_to_the_srd_pools(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not (k.startswith("opt-") and k.endswith("-xphb"))}
    r = run(bare, "wizard", 4, EA)
    assert len(ea_card(r)["options"]) == 32
    assert len(_card(run(bare, "wizard", 4, MMA), cid_of("wizard", 4, MMA, "metamagic"))["options"]) == 8
    assert len(_card(run(bare, "wizard", 4, MA), cid_of("wizard", 4, MA, "maneuvers"))["options"]) == 23


@pytest.mark.parametrize("ruleset", ["mixed", "2024"])
def test_resolve_stays_fast_with_all_four_feats(catalog, ruleset):
    ch = {"class:wizard:4:asi": [f"feat:{EA}"], "class:wizard:8:asi": [f"feat:{MA}"],
          "class:wizard:12:asi": [f"feat:{MMA}"], "class:wizard:16:asi": [f"feat:{FI}"]}
    d = _draft([("wizard", 20, ch, None)], ruleset=ruleset)
    resolve(d, catalog)
    start = time.perf_counter()
    for _ in range(10):
        resolve(d, catalog)
    assert (time.perf_counter() - start) / 10 * 1000 < 50
