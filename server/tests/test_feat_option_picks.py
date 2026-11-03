"""FE9: option-pick feats (docs/superpowers/plans/2026-10-11-feat-effects.md). Each feat follows its own edition's
text under every ruleset (effects are keyed by feat index). Governing sentences (catalog text, tags stripped; the full
set is `catalog.feat_effects_data.FEAT_EFFECT_QUOTES`, pinned against the catalog by `test_quote_matches_catalog_text`):

  Fighting Initiate (TCE)  "If you already have a style, the one you choose must be different." / "Whenever you reach a
                           level that grants the Ability Score Improvement feature, you can replace this feat's fighting
                           style with another one from the fighter class that you don't have."  -> card
                           ``:fighting-style`` (6 SRD fighter styles, editable); the pick is a class feature, so its
                           effect applies (Defense +1 AC in armor, Archery, Dueling ...); a style already held is
                           disabled "already taken (<name>, <holder>)".
  Eldritch Adept (TCE)     "Your spellcasting ability for the invocation is Intelligence, Wisdom, or Charisma (choose when
                           you select this feat)." / "If the invocation has a prerequisite of any kind, you can choose
                           that invocation only if you're a warlock who meets the prerequisite." -> cards
                           ``:invocation`` and ``:invocation-ability``; the effects reach the invocation effects (Armor
                           of Shadows AC and Mage Armor, Devil's Sight, Beguiling Influence).
  Martial Adept (PHB)      "You gain one superiority die, which is a d6 (this die is added to any superiority dice you
                           have from another source)." and "the saving throw DC equals 8 + your proficiency bonus +
                           your Strength or Dexterity modifier (your choice)." -> card ``:maneuvers`` (2 of the Battle
                           Master list) and a separate feat resource with the d6 and the DC.
  Metamagic Adept (TCE)    "You gain 2 sorcery points to spend on Metamagic (these points are added to any sorcery points
                           you have from another source but can be used only on Metamagic)." -> card ``:metamagic`` (2 of
                           the 8 SRD options) and a separate 2-point feat resource.

Matrix: feat x ruleset (2014, mixed, 2024) x class (Wizard, Fighter, Warlock, Sorcerer, Battle Master) x pool x
prerequisite (Warlock level / Pact / cantrip) x duplicate with the class's own list (both directions) x edit x stale
pick x five feat sites x Variant Human origin x no-feat identity x empty catalog x pending blocks export x timing."""
from perf_helpers import assert_fast, measure
import copy
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_effects as fe
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FI, EA, MA, MMA = "fighting-initiate-tce", "eldritch-adept-tce", "martial-adept-phb", "metamagic-adept-tce"
FE9 = [FI, EA, MA, MMA]
VH = "species:human-phb:subspecies:human-phb-variant-phb:feat-0"


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
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, " ".join(out))


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="mixed", species=None, weapons=(), subclass=None):
    scores = {a: 10 for a in ABS}
    d = {"name": "t", "ruleset": ruleset, "sources": [],
         "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
         "background": {"id": "acolyte", "choices": {}},
         "species": species or {"id": "human", "choices": {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": w, "qty": 1, "equipped": True} for w in weapons],
                       "skipped": False}, "details": {}, "preferences": {}}
    if subclass:
        d["classes"][0]["subclassId"] = subclass
    return d


def cid_of(cls, level, feat, suffix):
    return f"class:{cls}:{level}:asi:feat:{feat}:{suffix}"


def _card(r, cid):
    return next((c for c in r["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def run(catalog, cls, level, feat, picks=None, ruleset="mixed", weapons=(), class_choices=None, subclass=None, asi=None):
    ch = {f"class:{cls}:{asi or level}:asi": [f"feat:{feat}"], **(class_choices or {})}
    for suffix, sel in (picks or {}).items():
        ch[cid_of(cls, asi or level, feat, suffix)] = sel
    return resolve(_draft([(cls, level, ch)], ruleset=ruleset, weapons=weapons, subclass=subclass), catalog)


def _res(r, name):
    return next((x for x in r["derived"]["featResources"] if x["name"] == name), None)


# ---------------------------------------------------------------- data


@pytest.mark.parametrize("index", FE9)
def test_quote_matches_catalog_text(catalog, index):
    assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    text = _plain(catalog.feats[index]["entries"])
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in text, (index, quote)


def test_entries_match_the_texts():
    e = fed.FEAT_EFFECTS
    assert e[FI]["option_picks"] == {"kind": "fighting-style", "count": 1}
    assert e[EA]["option_picks"] == {"kind": "invocation", "count": 1}
    assert e[MA]["option_picks"] == {"kind": "maneuver", "count": 2}
    assert e[MMA]["option_picks"] == {"kind": "metamagic", "count": 2}
    ma = e[MA]["resources"][0]
    assert (ma["uses"], ma["die"], ma["recharge"]) == (1, "d6", "short-or-long")
    assert (e[MMA]["resources"][0]["uses"], e[MMA]["resources"][0]["recharge"]) == (2, "long")


def test_every_fe9_note_template_renders(catalog):
    numbers = fe.numbers_for({a: 2 for a in ABS}, {a: 14 for a in ABS}, 3, 8)
    for index in FE9:
        entry = fed.FEAT_EFFECTS[index]
        for text in entry.get("notes", []) + [r["note"] for r in entry.get("resources", []) if r.get("note")]:
            for pick in ("Parry, Riposte", None):
                out = fe.render(text, fe._env({"increased": None, "pick_text": pick}, numbers))
                assert out and "{" not in out, (index, text)


def test_pools(catalog):
    f = catalog.features
    styles = {o["id"] for o in _card(run(catalog, "wizard", 4, FI), cid_of("wizard", 4, FI, "fighting-style"))["options"]}
    assert styles == {i for i in f if i.startswith("fighter-fighting-style-")} and len(styles) == 6
    bm = f["battle-master-phb-3-battle-master"]["feature_specific"]["optional_progression"]["options"]
    man = _card(run(catalog, "wizard", 4, MA), cid_of("wizard", 4, MA, "maneuvers"))
    assert [o["id"] for o in man["options"]] == [o for o in bm if o in f] and len(bm) == 23
    mm = _card(run(catalog, "wizard", 4, MMA), cid_of("wizard", 4, MMA, "metamagic"))
    assert [o["label"] for o in mm["options"]] == [
        "Careful Spell", "Distant Spell", "Empowered Spell", "Extended Spell", "Heightened Spell",
        "Quickened Spell", "Subtle Spell", "Twinned Spell"]
    inv = _card(run(catalog, "wizard", 4, EA), cid_of("wizard", 4, EA, "invocation"))
    refs = f["eldritch-invocations"]["feature_specific"]["invocations"]
    assert [o["id"] for o in inv["options"]] == [r["index"] for r in refs]


# ---------------------------------------------------------------- Fighting Initiate


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_fi_card_has_six_styles_under_every_ruleset(catalog, ruleset):
    card = _card(run(catalog, "wizard", 4, FI, ruleset=ruleset), cid_of("wizard", 4, FI, "fighting-style"))
    assert card["source"]["kind"] == "feat" and card["count"] == 1 and card["status"] == "pending"
    assert {o["label"] for o in card["options"]} == {
        "Archery", "Defense", "Dueling", "Great Weapon Fighting", "Protection", "Two-Weapon Fighting"}


def test_fi_defense_adds_one_ac_in_armor(catalog):
    base = run(catalog, "wizard", 4, FI, weapons=["chain-mail"])
    r = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-defense"]}, weapons=["chain-mail"])
    assert r["derived"]["armorClass"] == base["derived"]["armorClass"] + 1
    unarmored = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-defense"]})
    assert unarmored["derived"]["armorClass"] == run(catalog, "wizard", 4, FI)["derived"]["armorClass"]


def test_fi_archery_adds_two_to_ranged_attacks(catalog):
    base = run(catalog, "wizard", 4, FI, weapons=["longbow"])
    r = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-archery"]}, weapons=["longbow"])
    row = lambda x: next(a for a in x["derived"]["attacks"] if a["itemId"] == "longbow")  # noqa: E731
    assert row(r)["attackBonus"] == row(base)["attackBonus"] + 2


def test_fi_dueling_adds_two_damage_with_one_handed_melee(catalog):
    row = lambda x: next(a for a in x["derived"]["attacks"] if a["itemId"] == "longsword")  # noqa: E731
    base = run(catalog, "wizard", 4, FI, weapons=["longsword"])
    r = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-dueling"]}, weapons=["longsword"])
    assert row(base).get("duelingDamage") is None
    assert row(r)["duelingDamage"].endswith("+2") and row(r)["damage"] == row(base)["damage"]


def test_fi_pick_shows_on_the_sheet_and_is_editable(catalog):
    a = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-defense"]}, weapons=["chain-mail"])
    b = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-archery"]}, weapons=["chain-mail"])
    feat = next(f for f in a["sheet"]["feats"] if f["id"] == FI)
    assert feat["choice"] == ["Defense"] and any("Defense" in n for n in feat["notes"])
    assert a["derived"]["armorClass"] == b["derived"]["armorClass"] + 1  # F-D7: swapping the style swaps the effect
    assert _card(a, cid_of("wizard", 4, FI, "fighting-style"))["status"] == "resolved"


def test_fi_duplicate_of_the_class_srd_style_is_disabled_and_pruned(catalog):
    """"If you already have a style, the one you choose must be different." The Fighter's own card comes first."""
    srd = {"class:fighter:1:feature:fighter-fighting-style": ["fighter-fighting-style-dueling"]}
    cid = cid_of("fighter", 4, FI, "fighting-style")
    r = run(catalog, "fighter", 4, FI, {"fighting-style": ["fighter-fighting-style-dueling"]}, class_choices=srd)
    card = _card(r, cid)
    opt = _opt(card, "fighter-fighting-style-dueling")
    assert opt["disabled"] and opt["disabledReason"] == "already taken (Dueling, SRD)"
    assert card["selected"] == [] and card["status"] == "pending"
    assert any(p["choiceId"] == cid and "Dueling" in p["reason"] for p in r["pruned"])
    ok = run(catalog, "fighter", 4, FI, {"fighting-style": ["fighter-fighting-style-archery"]}, class_choices=srd)
    assert _card(ok, cid)["selected"] == ["fighter-fighting-style-archery"] and not ok["pruned"]


def test_fi_earlier_origin_style_closes_the_later_class_card(catalog):
    """A Variant Human takes Fighting Initiate first; the Fighter's own style must then differ."""
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb",
               "choices": {VH: [f"feat:{FI}"], f"{VH}:feat:{FI}:fighting-style".replace("feat-0:feat", "feat-0:feat"): []}}
    fi_cid = next(c["id"] for c in resolve(_draft([("fighter", 1, {})], species=species), catalog)["choices"]
                  if c["id"].endswith(":fighting-style") and c["source"]["kind"] == "feat")
    species["choices"][fi_cid] = ["fighter-fighting-style-dueling"]
    srd = "class:fighter:1:feature:fighter-fighting-style"
    r = resolve(_draft([("fighter", 1, {srd: ["fighter-fighting-style-dueling"]})], species=species), catalog)
    card = _card(r, srd)
    assert _opt(card, "fighter-fighting-style-dueling")["disabledReason"] == "already taken (Dueling, Fighting Initiate)"
    assert card["selected"] == [] and any(p["choiceId"] == srd for p in r["pruned"])
    assert _card(r, fi_cid)["selected"] == ["fighter-fighting-style-dueling"]


def test_fi_duplicate_of_a_2024_fighting_style_feat(catalog):
    fs = {"class:fighter:1:fighting-style": ["feat:dueling-xphb"]}
    r = run(catalog, "fighter", 4, FI, {"fighting-style": ["fighter-fighting-style-dueling"]}, ruleset="2024", class_choices=fs)
    card = _card(r, cid_of("fighter", 4, FI, "fighting-style"))
    assert _opt(card, "fighter-fighting-style-dueling")["disabledReason"] == "already taken (Dueling, XPHB)"
    assert card["selected"] == []


def test_fi_pending_blocks_export(catalog):
    from app import _pending_export_problems
    cid = cid_of("wizard", 4, FI, "fighting-style")
    assert any(cid in str(p) for p in _pending_export_problems(run(catalog, "wizard", 4, FI)))
    done = run(catalog, "wizard", 4, FI, {"fighting-style": ["fighter-fighting-style-defense"]})
    assert not any(cid in str(p) for p in _pending_export_problems(done))


def test_fi_stale_pick_and_removed_feat_are_pruned(catalog):
    cid = cid_of("wizard", 4, FI, "fighting-style")
    r = run(catalog, "wizard", 4, FI, {"fighting-style": ["not-a-style"]})
    assert _card(r, cid)["selected"] == [] and any(p["choiceId"] == cid for p in r["pruned"])
    gone = resolve(_draft([("wizard", 4, {cid: ["fighter-fighting-style-defense"]})], weapons=["chain-mail"]), catalog)
    assert _card(gone, cid) is None and any(p["choiceId"] == cid for p in gone["pruned"])


# ---------------------------------------------------------------- Eldritch Adept


def test_ea_non_warlock_only_gets_invocations_without_prerequisite(catalog):
    card = _card(run(catalog, "wizard", 4, EA), cid_of("wizard", 4, EA, "invocation"))
    assert card["count"] == 1 and len(card["options"]) == 32
    for oid in ("eldritch-invocation-armor-of-shadows", "eldritch-invocation-devils-sight",
                "eldritch-invocation-beguiling-influence"):
        assert not _opt(card, oid).get("disabled")
    assert _opt(card, "eldritch-invocation-mire-the-mind")["disabledReason"] == "requires warlock level 5"
    assert "eldritch blast" in _opt(card, "eldritch-invocation-agonizing-blast")["disabledReason"]
    assert _opt(card, "eldritch-invocation-voice-of-the-chain-master")["disabled"]


def test_ea_warlock_meeting_the_prerequisite_may_take_it(catalog):
    inv = "class:warlock:2:invocations:eldritch-invocations"
    cid = cid_of("warlock", 5, EA, "invocation")
    base = {"class:warlock:3:feature:pact-boon": ["pact-of-the-blade"], "class:warlock:spells-cantrips": ["eldritch-blast"] * 0 + [
        "eldritch-blast", "mage-hand", "prestidigitation"]}
    r = run(catalog, "warlock", 5, EA, {"invocation": ["eldritch-invocation-thirsting-blade"]}, class_choices=base, asi=4)
    card = _card(r, cid_of("warlock", 4, EA, "invocation"))
    assert not _opt(card, "eldritch-invocation-mire-the-mind").get("disabled")
    assert not _opt(card, "eldritch-invocation-agonizing-blast").get("disabled")
    assert card["selected"] == ["eldritch-invocation-thirsting-blade"]
    no_pact = run(catalog, "warlock", 5, EA, {"invocation": ["eldritch-invocation-thirsting-blade"]},
                  class_choices={"class:warlock:3:feature:pact-boon": ["pact-of-the-tome"]}, asi=4)
    nc = _card(no_pact, cid_of("warlock", 4, EA, "invocation"))
    assert _opt(nc, "eldritch-invocation-thirsting-blade")["disabled"] and nc["selected"] == []
    low = run(catalog, "warlock", 3, EA, asi=4)  # ASI at 4 is not reached: no card
    assert _card(low, cid_of("warlock", 4, EA, "invocation")) is None
    assert inv and cid


def test_ea_stored_invocation_with_unmet_prerequisite_is_dropped(catalog):
    cid = cid_of("wizard", 4, EA, "invocation")
    r = run(catalog, "wizard", 4, EA, {"invocation": ["eldritch-invocation-mire-the-mind"]})
    assert _card(r, cid)["selected"] == [] and any(p["choiceId"] == cid for p in r["pruned"])


def test_ea_armor_of_shadows_gives_the_ac_formula_and_mage_armor(catalog):
    base = run(catalog, "wizard", 4, EA)
    pick = {"invocation": ["eldritch-invocation-armor-of-shadows"], "invocation-ability": ["int"]}
    r = run(catalog, "wizard", 4, EA, pick)
    assert base["derived"]["armorClass"] == 10 and r["derived"]["armorClass"] == 13  # 13 + DEX modifier
    (spell,) = [s for s in r["sheet"]["innateSpells"] if s["spellId"] == "mage-armor"]
    assert spell["ability"] == "INT" and spell["uses"] == "at-will" and spell["source"] == "Eldritch Adept"
    assert _card(r, cid_of("wizard", 4, EA, "invocation"))["status"] == "resolved"


def test_ea_ability_card_drives_the_spell_ability(catalog):
    for abl in ("int", "wis", "cha"):
        r = run(catalog, "wizard", 4, EA, {"invocation": ["eldritch-invocation-armor-of-shadows"], "invocation-ability": [abl]})
        assert next(s for s in r["sheet"]["innateSpells"] if s["spellId"] == "mage-armor")["ability"] == abl.upper()
    card = _card(run(catalog, "wizard", 4, EA), cid_of("wizard", 4, EA, "invocation-ability"))
    assert [o["id"] for o in card["options"]] == ["int", "wis", "cha"] and card["status"] == "pending"


def test_ea_devils_sight_and_beguiling_influence(catalog):
    r = run(catalog, "wizard", 4, EA, {"invocation": ["eldritch-invocation-devils-sight"]})
    assert r["sheet"]["senses"].get("devilsSight") == 120
    b = run(catalog, "wizard", 4, EA, {"invocation": ["eldritch-invocation-beguiling-influence"]})
    skills = b["sheet"]["proficiencies"]["skills"]
    assert "skill-deception" in skills and "skill-persuasion" in skills
    assert "skill-deception" not in run(catalog, "wizard", 4, EA)["sheet"]["proficiencies"]["skills"]


def test_ea_duplicate_of_the_warlock_invocation_is_disabled(catalog):
    inv = "class:warlock:2:invocations:eldritch-invocations"
    r = run(catalog, "warlock", 4, EA, {"invocation": ["eldritch-invocation-devils-sight"]},
            class_choices={inv: ["eldritch-invocation-devils-sight", "eldritch-invocation-armor-of-shadows"]})
    card = _card(r, cid_of("warlock", 4, EA, "invocation"))
    assert _opt(card, "eldritch-invocation-devils-sight")["disabledReason"] == "already taken (Devil's Sight, Warlock)"
    assert card["selected"] == [] and any(p["choiceId"] == card["id"] for p in r["pruned"])


def test_ea_pending_blocks_export_and_removal_prunes(catalog):
    from app import _pending_export_problems
    cid = cid_of("wizard", 4, EA, "invocation")
    assert any(cid in str(p) for p in _pending_export_problems(run(catalog, "wizard", 4, EA)))
    gone = resolve(_draft([("wizard", 4, {cid: ["eldritch-invocation-devils-sight"]})]), catalog)
    assert _card(gone, cid) is None and any(p["choiceId"] == cid for p in gone["pruned"])
    assert "devilsSight" not in gone["sheet"]["senses"]


# ---------------------------------------------------------------- Martial Adept


def test_ma_card_two_maneuvers_and_the_resource(catalog):
    card = _card(run(catalog, "wizard", 4, MA), cid_of("wizard", 4, MA, "maneuvers"))
    assert card["count"] == 2 and card["status"] == "pending" and any(o["label"] == "Parry" for o in card["options"])
    r = run(catalog, "wizard", 4, MA, {"maneuvers": ["opt-parry-phb", "opt-riposte-phb"]})
    res = _res(r, "Superiority Die (Martial Adept)")
    assert (res["uses"], res["die"], res["recharge"], res["dc"]) == (1, "d6", "short-or-long", 10)  # 8 + 2 + 0
    assert "Parry" in res["details"]["note"] and "Riposte" in res["details"]["note"]
    assert res["source"] == {"kind": "feat", "id": MA, "label": "Martial Adept"} and res["featId"] == MA
    assert res["id"].endswith(":superiority-die-martial-adept")
    feat = next(f for f in r["sheet"]["feats"] if f["id"] == MA)
    assert feat["choice"] == ["Parry", "Riposte"]


def test_ma_dc_uses_the_better_of_strength_and_dexterity_and_the_proficiency_bonus(catalog):
    d = _draft([("fighter", 20, {"class:fighter:4:asi": [f"feat:{MA}"]})])
    d["abilities"]["base"].update({"STR": 8, "DEX": 18})
    res = _res(resolve(d, catalog), "Superiority Die (Martial Adept)")
    assert res["dc"] == 8 + 6 + 4  # PB 6 at level 20, DEX 19 (+1 human) -> +4
    d["abilities"]["base"].update({"STR": 20, "DEX": 8})
    assert _res(resolve(d, catalog), "Superiority Die (Martial Adept)")["dc"] == 8 + 6 + 5


def test_ma_is_separate_from_the_battle_master_dice(catalog):
    r = run(catalog, "fighter", 4, MA, {"maneuvers": ["opt-parry-phb", "opt-riposte-phb"]}, subclass="battle-master-phb")
    bm = next(x for x in r["derived"]["classResources"] if x["name"] == "Superiority Dice")
    assert (bm["uses"], bm["die"]) == (4, "d8")
    ma = _res(r, "Superiority Die (Martial Adept)")
    assert (ma["uses"], ma["die"]) == (1, "d6") and ma["id"] != bm["id"]


def test_ma_duplicate_of_a_battle_master_maneuver(catalog):
    bm = "class:fighter:3:feature:battle-master-phb-3-battle-master"
    r = run(catalog, "fighter", 4, MA, {"maneuvers": ["opt-parry-phb", "opt-riposte-phb"]}, subclass="battle-master-phb",
            class_choices={bm: ["opt-parry-phb", "opt-feinting-attack-phb", "opt-rally-phb"]})
    card = _card(r, cid_of("fighter", 4, MA, "maneuvers"))
    assert _opt(card, "opt-parry-phb")["disabledReason"] == "already taken (Parry, Battle Master)"
    assert card["selected"] == ["opt-riposte-phb"] and card["status"] == "pending"
    assert any(p["choiceId"] == card["id"] and "Parry" in p["reason"] for p in r["pruned"])


def test_ma_without_picks_still_has_the_die_and_says_so(catalog):
    res = _res(run(catalog, "wizard", 4, MA), "Superiority Die (Martial Adept)")
    assert "(not chosen yet)" in res["details"]["note"]


# ---------------------------------------------------------------- Metamagic Adept


def test_mma_card_two_options_and_a_separate_point_pool(catalog):
    r = run(catalog, "sorcerer", 4, MMA, {"metamagic": ["metamagic-careful-spell", "metamagic-twinned-spell"]})
    card = _card(r, cid_of("sorcerer", 4, MMA, "metamagic"))
    assert card["count"] == 2 and card["status"] == "resolved"
    res = _res(r, "Sorcery Points (Metamagic Adept)")
    assert (res["uses"], res["recharge"]) == (2, "long") and "Careful Spell" in res["details"]["note"]
    own = next(x for x in r["derived"]["classResources"] if x["name"] == "Sorcery Points")
    assert own["uses"] == 4 and own["id"] != res["id"]  # the sorcerer's own pool is untouched


def test_mma_for_a_wizard_and_every_ruleset(catalog):
    for ruleset in ("2014", "mixed", "2024"):
        r = run(catalog, "wizard", 4, MMA, ruleset=ruleset)
        assert _res(r, "Sorcery Points (Metamagic Adept)")["uses"] == 2
        assert _card(r, cid_of("wizard", 4, MMA, "metamagic"))["count"] == 2


def test_mma_duplicate_of_the_sorcerer_srd_metamagic(catalog):
    own = {"class:sorcerer:3:feature:metamagic-1": ["metamagic-careful-spell", "metamagic-quickened-spell"]}
    r = run(catalog, "sorcerer", 4, MMA, {"metamagic": ["metamagic-careful-spell", "metamagic-twinned-spell"]}, class_choices=own)
    card = _card(r, cid_of("sorcerer", 4, MMA, "metamagic"))
    assert _opt(card, "metamagic-careful-spell")["disabledReason"] == "already taken (Careful Spell, Sorcerer)"
    assert card["selected"] == ["metamagic-twinned-spell"]


def test_mma_duplicate_of_the_2024_sorcerer_metamagic_by_name(catalog):
    own = {"class:sorcerer:2:feature:xphb-sorcerer-2-metamagic": ["opt-careful-spell-xphb", "opt-quickened-spell-xphb"]}
    r = run(catalog, "sorcerer", 4, MMA, {"metamagic": ["opt-careful-spell-xphb"]}, ruleset="2024", class_choices=own)  # RP20: XPHB pool
    card = _card(r, cid_of("sorcerer", 4, MMA, "metamagic"))
    assert _opt(card, "opt-careful-spell-xphb")["disabled"] and card["selected"] == []
    assert _card(r, "class:sorcerer:2:feature:xphb-sorcerer-2-metamagic")["selected"] == [
        "opt-careful-spell-xphb", "opt-quickened-spell-xphb"]


def test_mma_removal_prunes_and_drops_the_resource(catalog):
    cid = cid_of("sorcerer", 4, MMA, "metamagic")
    r = resolve(_draft([("sorcerer", 4, {cid: ["metamagic-careful-spell"]})]), catalog)
    assert _card(r, cid) is None and any(p["choiceId"] == cid for p in r["pruned"])
    assert r["derived"]["featResources"] == []


# ---------------------------------------------------------------- sites, identity, degrade, timing


@pytest.mark.parametrize("feat", FE9)
def test_variant_human_origin_site(catalog, feat):
    species = {"id": "human-phb", "subspeciesId": "human-phb-variant-phb", "choices": {VH: [f"feat:{feat}"]}}
    r = resolve(_draft([("sorcerer", 1, {})], species=species), catalog)
    suffix = fed.FEAT_EFFECTS[feat]["option_picks"]["kind"]
    names = {"fighting-style": "fighting-style", "maneuver": "maneuvers", "metamagic": "metamagic", "invocation": "invocation"}
    cards = [c for c in r["choices"] if c["id"].endswith(":" + names[suffix]) and c["source"]["kind"] == "feat"]
    assert len(cards) == 1 and cards[0]["id"].startswith(VH + ":feat:" + feat)


@pytest.mark.parametrize("site", ["background", "species", "fighting-style", "lessons"])
def test_every_other_feat_site_emits_the_card(catalog, monkeypatch, site):
    """The cards come from `_feat_choice_templates`, which all five sites call; the real feats are reachable through
    ASI and Variant Human only, so the effect table of a feat each other site does grant is patched."""
    spec = {"option_picks": {"kind": "maneuver", "count": 1}}
    if site == "background":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        draft, prefix = _draft([("wizard", 1, {})], ruleset="2024"), "feat:alert-xphb"
        draft["background"]["id"] = "criminal-xphb"
    elif site == "species":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        slot = "species:human-xphb:feat-0"
        draft = _draft([("wizard", 1, {})], ruleset="2024", species={"id": "human-xphb", "choices": {slot: ["feat:alert-xphb"]}})
        prefix = slot + ":feat:alert-xphb"
    elif site == "fighting-style":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "defense-xphb", {**fed.FEAT_EFFECTS["defense-xphb"], **spec})
        draft = _draft([("fighter", 1, {"class:fighter:1:fighting-style": ["feat:defense-xphb"]})], ruleset="2024")
        prefix = "class:fighter:1:fighting-style:feat:defense-xphb"
    else:
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        inv = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
        lessons = "opt-lessons-of-the-first-ones-xphb"
        card = f"class:warlock:invocation:{lessons}:feat"
        draft = _draft([("warlock", 2, {inv: [lessons], card: ["feat:alert-xphb"]})], ruleset="2024")
        prefix = card + ":alert-xphb"
    cards = [c for c in resolve(draft, catalog)["choices"] if c["id"].endswith(":maneuvers")]
    assert [c["id"] for c in cards] == [prefix + ":maneuvers"], site
    assert cards[0]["count"] == 1 and len(cards[0]["options"]) == 20  # RP20: the XPHB Battle Master list under ruleset 2024


def test_cards_carry_no_internal_flags(catalog):
    for feat, suffix in ((FI, "fighting-style"), (MA, "maneuvers"), (MMA, "metamagic"), (EA, "invocation")):
        card = _card(run(catalog, "wizard", 4, feat), cid_of("wizard", 4, feat, suffix))
        assert not {"distinctGroup", "lacksExpertise", "profOrExpertise"} & set(card)


def test_no_fe9_feat_means_no_cards_and_no_resources(catalog):
    r = resolve(_draft([("wizard", 4, {})]), catalog)
    assert not [c for c in r["choices"] if c["id"].endswith((":fighting-style", ":maneuvers", ":metamagic", ":invocation"))
                and c["source"]["kind"] == "feat"]
    assert r["derived"]["featResources"] == [] and r["pruned"] == []


def test_a_class_with_its_own_lists_is_unchanged_without_the_feats(catalog):
    own = {"class:sorcerer:3:feature:metamagic-1": ["metamagic-careful-spell", "metamagic-twinned-spell"]}
    r = resolve(_draft([("sorcerer", 4, own)]), catalog)
    assert _card(r, "class:sorcerer:3:feature:metamagic-1")["selected"] == [
        "metamagic-careful-spell", "metamagic-twinned-spell"] and r["pruned"] == []


def test_exports_print_the_feat_resources(catalog):
    import export_fields
    r = run(catalog, "wizard", 4, MA, {"maneuvers": ["opt-parry-phb", "opt-riposte-phb"]})
    line = export_fields.resource_line(_res(r, "Superiority Die (Martial Adept)"))
    assert "Superiority Die (Martial Adept): 1" in line and "d6" in line and "ТС 10" in line and "Parry" in line


def test_empty_feat_catalog_degrades(catalog):
    bare = copy.copy(catalog)
    bare.feats = {}
    r = resolve(_draft([("wizard", 4, {"class:wizard:4:asi": [f"feat:{MA}"]})]), bare)
    assert not [c for c in r["choices"] if c["id"].endswith(":maneuvers")] and r["derived"]["featResources"] == []


def _laps(catalog, draft):
    return measure(lambda: resolve(draft, catalog))


def test_resolve_stays_fast_with_the_heaviest_fe9_feats(catalog):
    asi = {"class:wizard:4:asi": [f"feat:{EA}"], "class:wizard:8:asi": [f"feat:{MA}"], "class:wizard:12:asi": [f"feat:{MMA}"],
           "class:wizard:16:asi": [f"feat:{FI}"],
           cid_of("wizard", 4, EA, "invocation"): ["eldritch-invocation-armor-of-shadows"],
           cid_of("wizard", 8, MA, "maneuvers"): ["opt-parry-phb", "opt-riposte-phb"],
           cid_of("wizard", 12, MMA, "metamagic"): ["metamagic-careful-spell", "metamagic-twinned-spell"],
           cid_of("wizard", 16, FI, "fighting-style"): ["fighter-fighting-style-defense"]}
    for ruleset in ("mixed", "2024"):
        assert_fast(_laps(catalog, _draft([("wizard", 20, asi)], ruleset=ruleset)))
    assert_fast(_laps(catalog, _draft([("fighter", 20, {})])))
    assert_fast(_laps(catalog, _draft([("wizard", 20, {})])))
