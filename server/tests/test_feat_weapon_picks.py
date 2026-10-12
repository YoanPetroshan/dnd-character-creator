"""FE8: weapon picks of Weapon Master (docs/superpowers/plans/2026-10-11-feat-effects.md). Each feat follows its own
edition's text under every ruleset (effects are keyed by feat index). Governing sentences (catalog text, tags stripped):

  Weapon Master (PHB)  "You gain proficiency with four weapons of your choice. Each one must be a simple or a martial
                       weapon."  -> card ``:weapon-choice``, 4 of every Simple / Martial catalog weapon; the picks join
                       the proficient weapons (attack rows, ``sheet.proficiencies.weapons``) BEFORE the Weapon Mastery
                       gate of the classes (C2), so a class mastery card sees them.
  Weapon Master (XPHB) "use the mastery property of one kind of Simple or Martial weapon of your choice, provided you
                       have proficiency with it. Whenever you finish a Long Rest, you can change the kind of weapon to
                       another eligible kind."  -> card ``:weapon-mastery``, 1 pick among weapons with a mastery
                       property; non-proficient weapons are disabled "not proficient"; a weapon already mastered by a
                       class card is disabled "already mastered"; the pick joins ``sheet.weaponMasteries`` and the
                       attack row. The card stays editable (F-D7).

Matrix: edition x ruleset (2014, mixed, 2024) x proficiency (Wizard / Rogue / Fighter) x pick count x stale pick x
duplicate with a class mastery card x edit x five feat sites x no-feat identity x empty catalog x pending blocks export
x timing."""
import copy
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
PHB, XPHB = "weapon-master-phb", "weapon-master-xphb"


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


def _draft(classes, ruleset="mixed", background="acolyte", species="human", species_choices=None, bg_choices=None,
           weapons=(), sources=None):
    scores = {a: 10 for a in ABS}
    return {"name": "t", "ruleset": ruleset, "sources": sources or [],
            "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
            "background": {"id": background, "choices": bg_choices or {}},
            "species": {"id": species, "choices": species_choices or {}},
            "abilities": {"method": "manual", "base": scores},
            "equipment": {"choices": {}, "added": [{"itemId": w, "qty": 1, "equipped": True} for w in weapons],
                          "skipped": False}, "details": {}, "preferences": {}}


def _card(r, cid):
    return next((c for c in r["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _row(r, item):
    return next(a for a in r["derived"]["attacks"] if a["itemId"] == item)


def _masteries(r):
    return [m["itemId"] for m in r["sheet"]["weaponMasteries"]]


def run(catalog, cls, level, feat, picks=None, ruleset="mixed", weapons=(), class_choices=None):
    cid = f"class:{cls}:{level}:asi:feat:{feat}"
    ch = {f"class:{cls}:{level}:asi": [f"feat:{feat}"], **(class_choices or {})}
    for suffix, sel in (picks or {}).items():
        ch[f"{cid}:{suffix}"] = sel
    return resolve(_draft([(cls, level, ch)], ruleset=ruleset, weapons=weapons), catalog)


def cid_of(cls, level, feat, suffix):
    return f"class:{cls}:{level}:asi:feat:{feat}:{suffix}"


# ---------------------------------------------------------------- data


@pytest.mark.parametrize("index", [PHB, XPHB])
def test_quote_matches_catalog_text(catalog, index):
    assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    text = _plain(catalog.feats[index]["entries"])
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in text, (index, quote)


def test_entries_match_the_texts():
    assert fed.FEAT_EFFECTS[PHB]["weapon_proficiency_choice"] == {"count": 4, "categories": ["simple", "martial"]}
    assert fed.FEAT_EFFECTS[XPHB]["mastery_choice"] == {"count": 1, "categories": ["simple", "martial"]}


# ---------------------------------------------------------------- Weapon Master (PHB): four proficiencies


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_phb_card_offers_every_weapon_and_four_picks(catalog, ruleset):
    r = run(catalog, "wizard", 4, PHB, ruleset=ruleset)
    card = _card(r, cid_of("wizard", 4, PHB, "weapon-choice"))
    assert card["source"]["kind"] == "feat" and card["count"] == 4 and card["status"] == "pending"
    weapons = {i["index"] for i in catalog.items.values()
               if i.get("equipment_category", {}).get("index") == "weapon"
               and i.get("weapon_category") in ("Simple", "Martial")}
    assert {o["id"] for o in card["options"]} == weapons and len(weapons) >= 40
    assert not any(o.get("disabled") for o in card["options"])


def test_phb_picks_make_the_rows_proficient(catalog):
    cid = "weapon-choice"
    base = run(catalog, "wizard", 4, PHB, weapons=["longsword", "greataxe", "dagger"])
    assert not _row(base, "longsword")["proficient"] and not _row(base, "greataxe")["proficient"]
    assert _row(base, "dagger")["proficient"]  # the Wizard's own proficiency, unchanged
    r = run(catalog, "wizard", 4, PHB, {cid: ["longsword", "greataxe", "rapier", "halberd"]},
            weapons=["longsword", "greataxe", "dagger"])
    assert _row(r, "longsword")["proficient"] and _row(r, "greataxe")["proficient"]
    assert _row(r, "longsword")["attackBonus"] == _row(base, "longsword")["attackBonus"] + 2
    weapons = r["sheet"]["proficiencies"]["weapons"]
    assert {"longswords", "greataxes", "rapiers", "halberds"} <= set(weapons)
    assert not {"longswords", "greataxes"} & set(r["sheet"]["proficiencies"]["tools"])
    assert _card(r, cid_of("wizard", 4, PHB, "weapon-choice"))["status"] == "resolved"


def test_phb_light_crossbow_uses_its_irregular_proficiency_id(catalog):
    r = run(catalog, "fighter", 4, PHB, {"weapon-choice": ["crossbow-heavy", "crossbow-hand", "net", "lance"]})
    assert {"crossbows-heavy", "hand-crossbows"} <= set(r["sheet"]["proficiencies"]["weapons"])


def test_phb_fewer_than_four_is_pending_and_blocks_export(catalog):
    from app import _pending_export_problems
    cid = cid_of("wizard", 4, PHB, "weapon-choice")
    r = run(catalog, "wizard", 4, PHB, {"weapon-choice": ["longsword", "greataxe"]})
    assert _card(r, cid)["status"] == "pending"
    assert any(cid in str(p) for p in _pending_export_problems(r))
    done = run(catalog, "wizard", 4, PHB, {"weapon-choice": ["longsword", "greataxe", "rapier", "halberd"]})
    assert not any(cid in str(p) for p in _pending_export_problems(done))


def test_phb_stale_pick_is_pruned_and_gives_nothing(catalog):
    cid = cid_of("wizard", 4, PHB, "weapon-choice")
    r = run(catalog, "wizard", 4, PHB, {"weapon-choice": ["not-a-weapon", "longsword"]}, weapons=["longsword"])
    assert _card(r, cid)["selected"] == ["longsword"]
    assert any(p["choiceId"] == cid for p in r["pruned"])


def test_phb_dropping_the_feat_drops_the_proficiency_and_prunes(catalog):
    cid = cid_of("wizard", 4, PHB, "weapon-choice")
    r = resolve(_draft([("wizard", 4, {cid: ["longsword"]})], weapons=["longsword"]), catalog)
    assert not _row(r, "longsword")["proficient"] and any(p["choiceId"] == cid for p in r["pruned"])


def test_phb_picks_are_seen_by_the_class_weapon_mastery_gate(catalog):
    """Rogue (2024) is not proficient with a Longsword (martial, no Finesse / Light); Weapon Master (PHB) is."""
    mastery = "class:rogue:weapon-mastery"
    without = run(catalog, "rogue", 4, PHB, ruleset="2024")
    assert _opt(_card(without, mastery), "longsword")["disabledReason"] == "not proficient"
    r = run(catalog, "rogue", 4, PHB, {"weapon-choice": ["longsword", "greataxe", "halberd", "lance"]}, ruleset="2024",
            class_choices={mastery: ["longsword"]}, weapons=["longsword"])
    assert not _opt(_card(r, mastery), "longsword").get("disabled")
    assert _masteries(r) == ["longsword"] and _row(r, "longsword")["mastery"] == "Sap"


# ---------------------------------------------------------------- Weapon Master (XPHB): one mastery


@pytest.mark.parametrize("ruleset", ["2014", "mixed", "2024"])
def test_xphb_card_exists_under_every_ruleset(catalog, ruleset):
    r = run(catalog, "wizard", 4, XPHB, ruleset=ruleset)
    card = _card(r, cid_of("wizard", 4, XPHB, "weapon-mastery"))
    assert card["source"]["kind"] == "feat" and card["count"] == 1 and card["status"] == "pending"
    assert _opt(card, "dagger")["label"] == "Dagger (Nick)"
    ids = {o["id"] for o in card["options"]}
    assert "longsword" in ids and "net" not in ids  # only weapons with a mastery property


def test_xphb_wizard_non_proficient_weapon_is_disabled(catalog):
    card = _card(run(catalog, "wizard", 4, XPHB, ruleset="2024"), cid_of("wizard", 4, XPHB, "weapon-mastery"))
    longsword = _opt(card, "longsword")
    assert longsword["disabled"] and longsword["disabledReason"] == "not proficient"
    assert not _opt(card, "dagger").get("disabled") and not _opt(card, "quarterstaff").get("disabled")


def test_xphb_dagger_pick_gives_nick_on_the_row(catalog):
    r = run(catalog, "wizard", 4, XPHB, {"weapon-mastery": ["dagger"]}, weapons=["dagger", "quarterstaff"])
    assert _masteries(r) == ["dagger"]
    assert r["sheet"]["weaponMasteries"][0] == {"itemId": "dagger", "name": "Dagger", "mastery": "Nick"}
    assert _row(r, "dagger")["mastery"] == "Nick" and _row(r, "quarterstaff")["mastery"] is None
    assert _card(r, cid_of("wizard", 4, XPHB, "weapon-mastery"))["status"] == "resolved"


def test_xphb_non_proficient_stored_pick_is_dropped(catalog):
    cid = cid_of("wizard", 4, XPHB, "weapon-mastery")
    r = run(catalog, "wizard", 4, XPHB, {"weapon-mastery": ["longsword"]}, ruleset="2024", weapons=["longsword"])
    assert _card(r, cid)["selected"] == [] and _masteries(r) == [] and _card(r, cid)["status"] == "pending"
    assert any(p["choiceId"] == cid and "longsword" in p["reason"].lower() for p in r["pruned"])
    assert _row(r, "longsword")["mastery"] is None


def test_xphb_edit_changes_the_mastery_f_d7(catalog):
    a = run(catalog, "wizard", 4, XPHB, {"weapon-mastery": ["dagger"]}, weapons=["dagger", "quarterstaff"])
    b = run(catalog, "wizard", 4, XPHB, {"weapon-mastery": ["quarterstaff"]}, weapons=["dagger", "quarterstaff"])
    assert _masteries(a) == ["dagger"] and _masteries(b) == ["quarterstaff"]
    assert _row(b, "quarterstaff")["mastery"] == "Topple"


def test_xphb_rogue_proficiency_follows_the_class(catalog):
    card = _card(run(catalog, "rogue", 4, XPHB, ruleset="2024"), cid_of("rogue", 4, XPHB, "weapon-mastery"))
    assert not _opt(card, "rapier").get("disabled") and _opt(card, "longsword")["disabled"]


def test_xphb_class_mastery_duplicate_is_disabled_already_mastered(catalog):
    mastery = "class:fighter:weapon-mastery"
    cid = cid_of("fighter", 4, XPHB, "weapon-mastery")
    r = run(catalog, "fighter", 4, XPHB, {"weapon-mastery": ["dagger"]}, ruleset="2024",
            class_choices={mastery: ["dagger", "longsword", "rapier", "greataxe"]})
    opt = _opt(_card(r, cid), "dagger")
    assert opt["disabled"] and opt["disabledReason"] == "already mastered"
    assert _card(r, cid)["selected"] == [] and any(p["choiceId"] == cid for p in r["pruned"])
    assert _card(r, mastery)["selected"] == ["dagger", "longsword", "rapier", "greataxe"]
    ok = run(catalog, "fighter", 4, XPHB, {"weapon-mastery": ["scimitar"]}, ruleset="2024",
             class_choices={mastery: ["dagger", "longsword", "rapier", "greataxe"]})
    assert _card(ok, cid)["selected"] == ["scimitar"] and "scimitar" in _masteries(ok)
    assert len(_masteries(ok)) == 5


# ---------------------------------------------------------------- sites, identity, degrade, timing


def test_cards_are_stripped_of_internal_flags(catalog):
    r = run(catalog, "wizard", 4, XPHB)
    card = _card(r, cid_of("wizard", 4, XPHB, "weapon-mastery"))
    assert "distinctGroup" not in card and "lacksExpertise" not in card


@pytest.mark.parametrize("site", ["background", "species", "fighting-style", "lessons", "asi"])
def test_every_feat_site_emits_and_applies_the_cards(catalog, monkeypatch, site):
    """The cards come from `_feat_choice_templates`, which all five sites call; the shipped Weapon Master feats are
    only reachable through ASI, so the effect table of a feat each other site does grant is patched."""
    spec = {"weapon_proficiency_choice": {"count": 1, "categories": ["simple", "martial"]}}
    if site == "background":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        draft = _draft([("wizard", 1, {})], ruleset="2024", background="criminal-xphb", weapons=["greataxe"])
        cid = "feat:alert-xphb:weapon-choice"
    elif site == "species":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        draft = _draft([("wizard", 1, {})], ruleset="2024", species="human-xphb", weapons=["greataxe"],
                       species_choices={"species:human-xphb:feat-0": ["feat:alert-xphb"]})
        cid = "species:human-xphb:feat-0:feat:alert-xphb:weapon-choice"
    elif site == "fighting-style":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "defense-xphb", {**fed.FEAT_EFFECTS["defense-xphb"], **spec})
        draft = _draft([("fighter", 1, {"class:fighter:1:fighting-style": ["feat:defense-xphb"]})], ruleset="2024",
                       weapons=["greataxe"])
        cid = next((c["id"] for c in resolve(draft, catalog)["choices"] if c["id"].endswith(":weapon-choice")), "")
        assert cid.startswith("class:fighter:1:fighting-style:") and "defense-xphb" in cid
    elif site == "lessons":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        inv = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
        lessons = "opt-lessons-of-the-first-ones-xphb"
        card = f"class:warlock:invocation:{lessons}:feat"
        draft = _draft([("warlock", 2, {inv: [lessons], card: ["feat:alert-xphb"]})], ruleset="2024",
                       weapons=["greataxe"])
        cid = next((c["id"] for c in resolve(draft, catalog)["choices"] if c["id"].endswith(":weapon-choice")), "")
        assert cid.startswith(card + ":") and "alert-xphb" in cid
    else:
        draft = _draft([("wizard", 4, {"class:wizard:4:asi": [f"feat:{PHB}"]})], ruleset="2024", weapons=["greataxe"])
        cid = cid_of("wizard", 4, PHB, "weapon-choice")
    r = resolve(draft, catalog)
    cards = [c for c in r["choices"] if c["id"].endswith(":weapon-choice")]
    assert len(cards) == 1 and cards[0]["source"]["kind"] == "feat", site
    assert cards[0]["id"] == cid, (site, cards[0]["id"])
    assert cards[0]["status"] == "pending" and _opt(cards[0], "greataxe")
    if site != "fighting-style":  # a Fighter is already proficient with every weapon
        assert not _row(r, "greataxe")["proficient"]
    if site == "background":
        draft["background"]["choices"] = {cid: ["greataxe"]}
    elif site == "species":
        draft["species"]["choices"][cid] = ["greataxe"]
    else:
        draft["classes"][0]["choices"][cid] = ["greataxe"]
    r2 = resolve(draft, catalog)
    assert _card(r2, cid)["selected"] == ["greataxe"] and _card(r2, cid)["status"] == ("pending" if site == "asi" else "resolved"), site  # asi: the real PHB card wants 4
    assert "greataxes" in r2["sheet"]["proficiencies"]["weapons"], site
    assert _row(r2, "greataxe")["proficient"], site


def test_mastery_card_at_a_non_asi_site(catalog, monkeypatch):
    monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], "mastery_choice": {"count": 1, "categories": ["simple", "martial"]}})
    draft = _draft([("wizard", 1, {})], ruleset="2024", background="criminal-xphb", weapons=["dagger"])
    r = resolve(draft, catalog)
    card = _card(r, "feat:alert-xphb:weapon-mastery")
    assert card and not _opt(card, "dagger").get("disabled") and _opt(card, "longsword")["disabled"]
    draft["background"]["choices"] = {"feat:alert-xphb:weapon-mastery": ["dagger"]}
    assert _masteries(resolve(draft, catalog)) == ["dagger"]


def test_no_weapon_master_means_no_cards_and_no_masteries(catalog):
    r = resolve(_draft([("wizard", 4, {})]), catalog)
    assert not [c for c in r["choices"] if c["id"].endswith((":weapon-choice", ":weapon-mastery"))]
    assert r["sheet"]["weaponMasteries"] == []


def test_empty_feat_catalog_degrades(catalog):
    bare = copy.copy(catalog)
    bare.feats = {}
    r = resolve(_draft([("wizard", 4, {"class:wizard:4:asi": [f"feat:{PHB}"]})]), bare)
    assert not [c for c in r["choices"] if c["id"].endswith(":weapon-choice")]


def _mean_ms(catalog, draft):
    resolve(draft, catalog)
    start = time.perf_counter()
    for _ in range(10):
        resolve(draft, catalog)
    return (time.perf_counter() - start) / 10 * 1000


def test_resolve_stays_fast_with_weapon_master(catalog):
    ch = {"class:fighter:4:asi": [f"feat:{PHB}"], cid_of("fighter", 4, PHB, "weapon-choice"): ["longsword", "dagger", "rapier", "halberd"]}
    assert _mean_ms(catalog, _draft([("fighter", 20, ch)])) < 50
    ch = {"class:fighter:4:asi": [f"feat:{XPHB}"], cid_of("fighter", 4, XPHB, "weapon-mastery"): ["dagger"]}
    assert _mean_ms(catalog, _draft([("fighter", 20, ch)], ruleset="2024")) < 50
