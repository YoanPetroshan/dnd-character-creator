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


# ================================================================ A3b: dependents of a feat-held invocation
# Rule (XPHB texts, quoted in ``test_xphb_option_text_matches_catalog``): Agonizing Blast / Eldritch Spear "Choose one of
# your known Warlock cantrips that deals damage"; Repelling Blast "... that requires an attack roll"; Pact of the Tome
# "choose three cantrips, and choose two level 1 spells that have the Ritual tag"; Pact of the Blade "a Simple or Martial
# Melee weapon of your choice with which you bond". The C7c builders run with the Eldritch Adept card as the holder:
# cids ``<feat card cid>:<invocation>:<kind>``, source = the feat's own source.


def ea(cls="warlock", level=4):
    return cid_of(cls, level, EA, "invocation")


def dep(inst, kind, cls="warlock", level=4):
    return f"{ea(cls, level)}:{inst}:{kind}"


def wl(level, pick, own=None, cantrips=("eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"), more=None, ability="cha", **kw):
    ch = {INV: own if own is not None else [MIND, ARMOR, DEVIL], CANT: list(cantrips), **(more or {})}
    picks = {"invocation": [pick], "invocation-ability": [ability]}
    return run(catalog_(), "warlock", level, EA, picks, class_choices=ch, **kw)


_CATALOG = []


def catalog_():
    if not _CATALOG:
        _CATALOG.append(load())
    return _CATALOG[0]


def test_target_card_for_a_feat_held_agonizing_blast(catalog):
    r = wl(5, AGON)
    card = _card(r, dep(AGON, "cantrip"))
    assert card["count"] == 1 and card["status"] == "pending" and card["source"] == _card(r, ea())["source"]
    assert card["label"] == "Agonizing Blast: Cantrip"
    assert {o["id"] for o in card["options"]} == {"eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"}
    assert not _opt(card, "eldritch-blast-xphb").get("disabled")
    assert _opt(card, "minor-illusion-xphb")["disabledReason"] == "does not deal damage"
    done = wl(5, AGON, more={dep(AGON, "cantrip"): ["eldritch-blast-xphb"]})
    assert _card(done, dep(AGON, "cantrip"))["status"] == "resolved"
    res = next(x for x in done["derived"]["classResources"] if x["name"] == "Agonizing Blast")
    assert res["details"]["spell"] == "eldritch-blast-xphb" and "Eldritch Blast" in res["details"]["note"]
    assert res["bonus"] == 3  # the Warlock's CHA 16 + Human 1 -> +3


def test_target_cards_for_spear_and_repelling_blast(catalog):
    spear = wl(5, SPEAR, more={dep(SPEAR, "cantrip"): ["eldritch-blast-xphb"]})
    card = _card(spear, dep(SPEAR, "cantrip"))
    assert card["selected"] == ["eldritch-blast-xphb"]
    note = next(x for x in spear["derived"]["classResources"] if x["name"] == "Eldritch Spear")["details"]["note"]
    assert note == "Eldritch Blast: range 120 ft + 150 ft (30 x Warlock level 5) = 270 ft."
    assert _opt(card, "mage-hand-xphb")["disabledReason"] == "does not deal damage"
    rep = wl(5, REPEL, more={dep(REPEL, "cantrip"): ["eldritch-blast-xphb"]})
    assert _card(rep, dep(REPEL, "cantrip"))["selected"] == ["eldritch-blast-xphb"]
    assert _opt(_card(rep, dep(REPEL, "cantrip")), "mage-hand-xphb")["disabledReason"] == "does not require an attack roll"
    note = next(x for x in rep["derived"]["classResources"] if x["name"] == "Repelling Blast")["details"]["note"]
    assert "Eldritch Blast" in note and "push it up to 10 feet" in note


def test_a_stored_target_pick_that_is_no_longer_valid_is_pruned_not_over_selected(catalog):
    r = wl(5, AGON, more={dep(AGON, "cantrip"): ["minor-illusion-xphb"]})
    assert _card(r, dep(AGON, "cantrip"))["selected"] == []
    assert "no longer available" in _pruned(r, dep(AGON, "cantrip"))
    assert not [p for p in r["problems"] if "over-selected" in p["id"]]


def test_dependents_go_when_the_feat_pick_changes_or_the_feat_goes(catalog):
    stored = {dep(AGON, "cantrip"): ["eldritch-blast-xphb"]}
    swapped = wl(5, ARMOR, more=stored)
    assert _card(swapped, dep(AGON, "cantrip")) is None
    assert dep(AGON, "cantrip") in {p["choiceId"] for p in swapped["pruned"]}
    # the feat is no longer picked at the ASI: the whole cascade is stale
    ch = {INV: [MIND, ARMOR, DEVIL], CANT: ["eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"],
          ea(): [AGON], **stored}
    gone = resolve(_draft([("warlock", 5, ch, None)]), load())
    assert _card(gone, ea()) is None and _card(gone, dep(AGON, "cantrip")) is None
    assert dep(AGON, "cantrip") in {p["choiceId"] for p in gone["pruned"]}


def test_a_feat_pick_dropped_by_the_gate_takes_its_target_card_with_it(catalog):
    # no damaging cantrip at all: the pick is unmet, so there is no target card either
    r = wl(5, AGON, cantrips=("minor-illusion-xphb", "mage-hand-xphb", "prestidigitation-xphb"))
    assert _card(r, ea())["selected"] == [] and _card(r, dep(AGON, "cantrip")) is None


def test_the_warlock_and_the_feat_do_not_share_a_target_card(catalog):
    r = wl(5, SPEAR, own=[AGON, MIND, ARMOR],
           more={dep(SPEAR, "cantrip"): ["eldritch-blast-xphb"],
                 "class:warlock:invocation:" + AGON + ":cantrip": ["eldritch-blast-xphb"]})
    own = _card(r, "class:warlock:invocation:" + AGON + ":cantrip")
    feat = _card(r, dep(SPEAR, "cantrip"))
    assert own["selected"] == ["eldritch-blast-xphb"] and feat["selected"] == ["eldritch-blast-xphb"]
    assert own["source"]["kind"] == "class" and feat["source"]["kind"] == "feat"


def test_duplicate_of_the_warlock_agonizing_blast_is_still_blocked(catalog):
    r = wl(5, AGON, own=[AGON, MIND, ARMOR], more={"class:warlock:invocation:" + AGON + ":cantrip": ["eldritch-blast-xphb"]})
    card = _card(r, ea())
    assert _opt(card, AGON)["disabledReason"] == "already taken (Agonizing Blast, Warlock)" and card["selected"] == []
    assert _card(r, dep(AGON, "cantrip")) is None


# ---- Pact of the Tome through the feat (any class)


def test_pact_of_the_tome_cards_for_a_wizard(catalog):
    r = run(catalog, "wizard", 4, EA, {"invocation": [TOME], "invocation-ability": ["int"]})
    cantrips, rituals = _card(r, dep(TOME, "cantrips", "wizard")), _card(r, dep(TOME, "rituals", "wizard"))
    assert (cantrips["count"], rituals["count"]) == (3, 2) and cantrips["status"] == rituals["status"] == "pending"
    assert cantrips["source"]["kind"] == "feat"
    assert all(catalog.spells[o["id"]]["level"] == 0 for o in cantrips["options"])
    assert all(catalog.spells[o["id"]]["level"] == 1 and catalog.spells[o["id"]].get("ritual") for o in rituals["options"])
    assert {"fire-bolt-xphb", "light-xphb"} <= {o["id"] for o in cantrips["options"]}  # any class's list
    picks = {dep(TOME, "cantrips", "wizard"): ["fire-bolt-xphb", "light-xphb", "guidance-xphb"],
             dep(TOME, "rituals", "wizard"): ["detect-magic-xphb", "identify-xphb"]}
    done = run(catalog, "wizard", 4, EA, {"invocation": [TOME], "invocation-ability": ["int"]}, class_choices=picks)
    spells = {s["spellId"]: s for s in done["sheet"]["innateSpells"] if s["source"] == "Eldritch Adept"}
    assert {"fire-bolt-xphb", "light-xphb", "guidance-xphb", "detect-magic-xphb", "identify-xphb"} <= set(spells)
    assert spells["detect-magic-xphb"]["ability"] == "INT" and spells["detect-magic-xphb"]["uses"] == "always prepared"
    assert "Pact of the Tome" in spells["fire-bolt-xphb"]["note"]


def test_tome_cards_only_for_the_selected_feat_pick(catalog):
    none = run(catalog, "wizard", 4, EA, {"invocation": [CHAIN]})
    assert not [c["id"] for c in none["choices"] if "pact-of-the-tome" in c["id"]]


def test_feat_tome_cantrips_count_for_the_warlocks_prerequisite(catalog):
    own = [MIND, AGON, ARMOR]
    cants = ("minor-illusion-xphb", "mage-hand-xphb", "prestidigitation-xphb")
    without = wl(5, ARMOR, own=own, cantrips=cants)
    assert _card(without, INV)["selected"] == [MIND, ARMOR]  # Agonizing Blast needs a damaging cantrip
    tome = {dep(TOME, "cantrips"): ["fire-bolt-xphb", "light-xphb", "guidance-xphb"]}
    with_tome = wl(5, TOME, own=own, cantrips=cants, more=tome)
    assert _card(with_tome, INV)["selected"] == own and _card(with_tome, ea())["selected"] == [TOME]


def test_duplicate_of_the_warlock_tome_is_blocked(catalog):
    r = wl(5, TOME, own=[TOME, MIND, ARMOR])
    assert _card(r, ea())["selected"] == [] and _card(r, dep(TOME, "cantrips")) is None
    assert _card(r, "class:warlock:invocation:" + TOME + ":cantrips") is not None


# ---- Pact of the Blade through the feat


def test_pact_of_the_blade_weapon_card_and_attack_row(catalog):
    r = run(catalog, "wizard", 4, EA, {"invocation": [BLADE], "invocation-ability": ["cha"]})
    card = _card(r, dep(BLADE, "weapon", "wizard"))
    assert card["count"] == 1 and card["source"]["kind"] == "feat"
    assert {"longsword", "dagger", "greatsword"} <= {o["id"] for o in card["options"]}
    assert all(catalog.items[o["id"]]["weapon_range"] == "Melee" for o in card["options"])
    done = run(catalog, "wizard", 4, EA, {"invocation": [BLADE], "invocation-ability": ["cha"]},
               class_choices={dep(BLADE, "weapon", "wizard"): ["longsword"]})
    (row,) = [a for a in done["derived"]["attacks"] if a["itemId"] == "longsword"]
    assert row["ability"] == "CHA" and any("Pact weapon" in n for n in row["notes"])
    plain = run(catalog, "wizard", 4, EA, {"invocation": [BLADE]}, class_choices={dep(BLADE, "weapon", "wizard"): ["longsword"]},
                ruleset="mixed")
    assert not [a for a in plain["derived"]["attacks"] if a["itemId"] == "longsword"]


def test_thirsting_blade_through_the_feat_adds_its_row_note(catalog):
    r = wl(5, THIRST, own=[BLADE, MIND, ARMOR], more={"class:warlock:invocation:" + BLADE + ":weapon": ["longsword"]})
    assert _card(r, ea())["selected"] == [THIRST]
    (row,) = [a for a in r["derived"]["attacks"] if a["itemId"] == "longsword"]
    assert any("Thirsting" in n or "Extra Attack" in n for n in row["notes"])


# ---- sites, rulesets, identity, degrade, timing


def test_dependents_at_the_background_site(catalog, monkeypatch):
    monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], "option_picks": {"kind": "invocation", "count": 1}})
    d = _draft([("wizard", 1, {}, None)])
    d["background"]["id"] = "criminal-xphb"
    card = "feat:alert-xphb:invocation"
    d["classes"][0]["choices"] = {card: [TOME], f"{card}:{TOME}:cantrips": ["fire-bolt-xphb", "light-xphb", "guidance-xphb"]}
    r = resolve(d, catalog)
    assert _card(r, card)["selected"] == [TOME]
    assert _card(r, f"{card}:{TOME}:cantrips")["selected"] == ["fire-bolt-xphb", "light-xphb", "guidance-xphb"]
    assert _card(r, f"{card}:{TOME}:rituals")["status"] == "pending"


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_dependents_outside_2024(catalog, ruleset):
    r = run(catalog, "wizard", 4, EA, {"invocation": [TOME]}, ruleset=ruleset)
    assert not [c["id"] for c in r["choices"] if c["id"].startswith(ea("wizard") + ":")]


def test_srd_only_catalog_has_no_dependents(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not (k.startswith("opt-") and k.endswith("-xphb"))}
    r = run(bare, "wizard", 4, EA, {"invocation": [TOME]})
    assert not [c["id"] for c in r["choices"] if c["id"].startswith(ea("wizard") + ":")]


def test_dependents_with_a_pending_target_block_export(catalog):
    from app import _pending_export_problems
    r = wl(5, AGON)
    assert any(dep(AGON, "cantrip") in str(p) for p in _pending_export_problems(r))


def test_a_target_card_with_no_enabled_option_does_not_block_export(catalog):
    # Eldritch Spear needs a damaging cantrip with range 10+; with only Toll-the-Dead-like short ranges the pick is dropped
    r = wl(5, SPEAR, cantrips=("minor-illusion-xphb", "mage-hand-xphb", "eldritch-blast-xphb"))
    assert _card(r, dep(SPEAR, "cantrip"))["status"] == "pending"
    cards = [c for c in r["choices"] if c["id"].startswith(ea() + ":")]
    assert cards and all(c["status"] in ("pending", "resolved", "unavailable") for c in cards)


def test_warlock_20_with_all_four_feats_stays_fast(catalog):
    ch = {INV: [AGON, SPEAR, REPEL, BLADE, THIRST, MIND, ARMOR, DEVIL, X.format("fiendish-vigor"), X.format("mask-of-many-faces")],
          CANT: ["eldritch-blast-xphb", "fire-bolt-xphb", "minor-illusion-xphb", "mage-hand-xphb"],
          "class:warlock:4:asi": [f"feat:{EA}"], "class:warlock:8:asi": [f"feat:{MA}"],
          "class:warlock:12:asi": [f"feat:{MMA}"], "class:warlock:16:asi": [f"feat:{FI}"]}
    ch[ea()] = [CHAIN]
    for ruleset in ("mixed", "2024"):
        d = _draft([("warlock", 20, ch, None)], ruleset=ruleset)
        resolve(d, catalog)
        start = time.perf_counter()
        for _ in range(10):
            resolve(d, catalog)
        assert (time.perf_counter() - start) / 10 * 1000 < 50


def test_a_tome_card_without_any_ritual_spell_is_unavailable_not_blocking(catalog):
    bare = copy.copy(catalog)
    bare.spells = {k: v for k, v in catalog.spells.items() if not v.get("ritual")}
    r = run(bare, "wizard", 4, EA, {"invocation": [TOME]})
    rituals = _card(r, dep(TOME, "rituals", "wizard"))
    assert rituals["status"] == "unavailable" and rituals["options"] == []


def test_the_feat_may_come_from_another_class_than_the_warlock(catalog):
    fighter = {"class:fighter:4:asi": [f"feat:{EA}"], cid_of("fighter", 4, EA, "invocation"): [AGON],
               cid_of("fighter", 4, EA, "invocation-ability"): ["cha"]}
    warlock = {INV: [MIND, ARMOR, DEVIL], CANT: ["eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"]}
    d = _draft([("fighter", 4, fighter, None), ("warlock", 5, warlock, None)])
    r = resolve(d, catalog)
    card = _card(r, f"{cid_of('fighter', 4, EA, 'invocation')}:{AGON}:cantrip")
    assert card and not _opt(card, "eldritch-blast-xphb").get("disabled") and _opt(card, "minor-illusion-xphb").get("disabled")
    assert _card(r, cid_of("fighter", 4, EA, "invocation"))["selected"] == [AGON]
    nowl = resolve(_draft([("fighter", 4, fighter, None)]), catalog)
    assert _card(nowl, cid_of("fighter", 4, EA, "invocation"))["selected"] == []  # no Warlock level, no Agonizing Blast


# ================================================================ A3c: Lessons of the First Ones through the feat
# Rule: XPHB "You have received knowledge from an elder entity of the multiverse, allowing you to gain one Origin feat of
# your choice." (prerequisite: Warlock level 2). The Eldritch Adept pick is one invocation instance, so one Origin feat.
# The pick resolves in the F1 walk right after the Eldritch Adept ASI feat (same `seen` map as every other feat), its
# cid is ``<feat card cid>:opt-lessons-of-the-first-ones-xphb:feat`` and the feat's own choices cascade under
# ``<that cid>:<feat index>``; the feat is tagged origin "invocation" like the Warlock's own Lessons.


def lcid(cls="warlock", level=4):
    return dep(LESSONS, "feat", cls, level)


def wl_lessons(level=5, origin=None, more=None, own=None, **kw):
    ch = {INV: own if own is not None else [MIND, ARMOR, DEVIL], CANT: ["eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"],
          **({lcid(): [origin]} if origin else {}), **(more or {})}
    return run(load(), "warlock", level, EA, {"invocation": [LESSONS], "invocation-ability": ["cha"]}, class_choices=ch, **kw)


def test_the_lessons_card_offers_origin_feats_for_a_warlock(catalog):
    r = wl_lessons()
    card = _card(r, lcid())
    assert card["count"] == 1 and card["source"] == _card(r, ea())["source"] and card["label"] == "Lessons of the First Ones"
    ids = {o["id"] for o in card["options"]}
    assert {"feat:alert-xphb", "feat:magic-initiate-xphb", "feat:skilled-xphb", "feat:tough-xphb"} <= ids
    assert all(catalog.feats[i[len("feat:"):]]["category"] == "O" for i in ids)
    assert "feat:grappler-xphb" not in ids and card["status"] == "pending"


def test_the_origin_feat_lands_on_the_sheet_and_applies(catalog):
    base = wl_lessons()
    r = wl_lessons(origin="feat:alert-xphb")
    feat = next(f for f in r["sheet"]["feats"] if f["id"] == "alert-xphb")
    assert feat["origin"] == "invocation" and "alert-xphb" in r["sheet"]["grantedFeats"]
    assert _card(r, lcid())["status"] == "resolved" and _card(r, lcid())["selected"] == ["feat:alert-xphb"]
    assert r["derived"]["initiative"] == base["derived"]["initiative"] + 3  # Alert (XPHB): Initiative Proficiency, PB 3 at level 5
    assert next(f for f in r["sheet"]["feats"] if f["id"] == EA)["origin"] == "asi"


def test_the_origin_feat_cascades_its_own_choices(catalog):
    r = wl_lessons(origin="feat:skilled-xphb")
    cascade = [c for c in r["choices"] if c["id"].startswith(lcid() + ":")]
    assert len(cascade) == 1 and cascade[0]["count"] == 3 and cascade[0]["source"]["kind"] == "feat"
    picks = {cascade[0]["id"]: ["skill-stealth", "skill-arcana", "skill-history"]}
    r2 = wl_lessons(origin="feat:skilled-xphb", more=picks)
    assert {"skill-stealth", "skill-arcana", "skill-history"} <= set(r2["sheet"]["proficiencies"]["skills"])
    assert next(f for f in r2["sheet"]["feats"] if f["id"] == "skilled-xphb")["choice"]


def test_a_magic_initiate_pick_cascades_the_spell_cards(catalog):
    r = wl_lessons(origin="feat:magic-initiate-xphb")
    variant = next(c for c in r["choices"] if c["id"].endswith(":spell-variant") and c["id"].startswith(lcid()))
    prefix = variant["id"][: -len(":spell-variant")]
    assert prefix == f"{lcid()}:magic-initiate-xphb"
    picks = {variant["id"]: ["cleric-spells"], prefix + ":spell-ability": ["cha"]}
    r2 = wl_lessons(origin="feat:magic-initiate-xphb", more=picks)
    for card in [c for c in r2["choices"] if c["id"].startswith(prefix + ":spell-choice-")]:
        picks[card["id"]] = [o["id"] for o in card["options"] if not o.get("disabled")][: card["count"]]
    r3 = wl_lessons(origin="feat:magic-initiate-xphb", more=picks)
    assert len([e for e in r3["sheet"]["innateSpells"] if e.get("featId") == "magic-initiate-xphb"]) == 3
    # the invocation goes: the whole cascade goes with it, as stale picks
    r4 = run(catalog, "warlock", 5, EA, {"invocation": [ARMOR], "invocation-ability": ["cha"]},
             class_choices={INV: [MIND, DEVIL, X.format("fiendish-vigor")], CANT: ["eldritch-blast-xphb"], lcid(): ["feat:magic-initiate-xphb"], **picks})
    assert not [e for e in r4["sheet"]["innateSpells"] if e.get("featId") == "magic-initiate-xphb"]
    assert _pruned(r4, variant["id"])


def test_changing_the_pick_away_from_lessons_removes_the_feat(catalog):
    stored = {lcid(): ["feat:alert-xphb"]}
    r = wl_lessons(more=stored)
    assert [f for f in r["sheet"]["feats"] if f["id"] == "alert-xphb"]
    gone = run(catalog, "warlock", 5, EA, {"invocation": [ARMOR], "invocation-ability": ["cha"]},
               class_choices={INV: [MIND, DEVIL, X.format("fiendish-vigor")], CANT: ["eldritch-blast-xphb"], **stored})
    assert _card(gone, lcid()) is None and "no longer applies" in _pruned(gone, lcid())
    assert "alert-xphb" not in [f["id"] for f in gone["sheet"]["feats"]]


def test_lessons_through_the_feat_needs_a_warlock_level_2(catalog):
    wizard = run(catalog, "wizard", 4, EA, {"invocation": [LESSONS]}, class_choices={dep(LESSONS, "feat", "wizard"): ["feat:alert-xphb"]})
    assert ea_card(wizard)["selected"] == [] and _card(wizard, dep(LESSONS, "feat", "wizard")) is None
    assert "alert-xphb" not in [f["id"] for f in wizard["sheet"]["feats"]]
    fighter = {"class:fighter:4:asi": [f"feat:{EA}"], cid_of("fighter", 4, EA, "invocation"): [LESSONS],
               f"{cid_of('fighter', 4, EA, 'invocation')}:{LESSONS}:feat": ["feat:alert-xphb"]}
    low = resolve(_draft([("fighter", 4, fighter, None), ("warlock", 1, {}, None)]), catalog)
    assert "alert-xphb" not in [f["id"] for f in low["sheet"]["feats"]]
    ok = resolve(_draft([("fighter", 4, fighter, None), ("warlock", 2, {}, None)]), catalog)
    feat = next(f for f in ok["sheet"]["feats"] if f["id"] == "alert-xphb")
    assert feat["origin"] == "invocation"  # the Fighter's ASI feat, a Warlock 2 multiclass


def test_a_feat_from_the_background_is_already_taken(catalog):
    d = _draft([("warlock", 5, {INV: [MIND, ARMOR, DEVIL], CANT: ["eldritch-blast-xphb"], "class:warlock:4:asi": [f"feat:{EA}"],
                                ea(): [LESSONS], lcid(): ["feat:alert-xphb"]}, None)])
    d["background"]["id"] = "criminal-xphb"  # grants Alert
    r = resolve(d, catalog)
    card = _card(r, lcid())
    assert "already taken" in _opt(card, "feat:alert-xphb")["disabledReason"] and card["selected"] == []
    assert [f["id"] for f in r["sheet"]["feats"]].count("alert-xphb") == 1
    assert any(p["id"].startswith("feat-duplicate-alert-xphb") for p in r["problems"])


def test_the_warlocks_own_lessons_wins_over_the_feats(catalog):
    own = {INV: [LESSONS, MIND, ARMOR], "class:warlock:invocation:" + LESSONS + ":feat": ["feat:tough-xphb"]}
    r = wl_lessons(own=own[INV], more={k: v for k, v in own.items() if k != INV} | {lcid(): ["feat:alert-xphb"]})
    assert _opt(_card(r, ea()), LESSONS)["disabledReason"] == "already taken (Lessons of the First Ones, Warlock)"
    assert _card(r, lcid()) is None
    ids = [f["id"] for f in r["sheet"]["feats"]]
    assert "tough-xphb" in ids and "alert-xphb" not in ids


def test_an_asi_pick_of_the_same_origin_feat_later_is_the_duplicate(catalog):
    more = {lcid(): ["feat:alert-xphb"], "class:warlock:8:asi": ["feat:alert-xphb"]}
    r = wl_lessons(level=8, more=more)
    assert [f["origin"] for f in r["sheet"]["feats"] if f["id"] == "alert-xphb"] == ["invocation"]
    assert any(p["id"].startswith("feat-duplicate-alert-xphb") for p in r["problems"])


def test_a_non_origin_feat_stored_at_the_lessons_card_is_ignored(catalog):
    r = wl_lessons(origin="feat:grappler-xphb")
    assert _card(r, lcid())["selected"] == [] and "grappler-xphb" not in [f["id"] for f in r["sheet"]["feats"]]


def test_lessons_through_the_feat_outside_2024_has_no_card(catalog):
    r = run(catalog, "wizard", 4, EA, {"invocation": [LESSONS]}, ruleset="mixed")
    assert not [c for c in r["choices"] if c["id"].endswith(":feat")]


def test_srd_only_catalog_has_no_lessons_card(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not (k.startswith("opt-") and k.endswith("-xphb"))}
    r = run(bare, "warlock", 5, EA, {"invocation": [LESSONS]})
    assert not [c for c in r["choices"] if c["id"].endswith(":feat")]


def test_the_lessons_pick_is_pending_until_made_and_blocks_export(catalog):
    from app import _pending_export_problems
    assert any(lcid() in str(p) for p in _pending_export_problems(wl_lessons()))
    assert not any(lcid() in str(p) for p in _pending_export_problems(wl_lessons(origin="feat:alert-xphb")))


def test_a_blocked_eldritch_adept_takes_its_lessons_feat_with_it(catalog):
    # prerequisites on and Eldritch Adept made to need Strength 20: the ASI feat is not applied and neither is anything under it
    patched = copy.copy(catalog)
    patched.feats = {**catalog.feats, EA: {**catalog.feats[EA], "prerequisite": [{"ability": [{"str": 20}]}]}}
    fighter = {"class:fighter:4:asi": [f"feat:{EA}"], cid_of("fighter", 4, EA, "invocation"): [LESSONS],
               f"{cid_of('fighter', 4, EA, 'invocation')}:{LESSONS}:feat": ["feat:alert-xphb"]}
    d = _draft([("fighter", 4, fighter, None), ("warlock", 2, {}, None)])
    d["preferences"] = {"usePrerequisites": {"feats": True}}
    r = resolve(d, patched)
    assert EA not in [f["id"] for f in r["sheet"]["feats"]] and "alert-xphb" not in [f["id"] for f in r["sheet"]["feats"]]
    assert "alert-xphb" not in r["sheet"]["grantedFeats"]
    d["preferences"] = {}
    free = resolve(d, patched)
    assert EA in [f["id"] for f in free["sheet"]["feats"]] and "alert-xphb" in [f["id"] for f in free["sheet"]["feats"]]
