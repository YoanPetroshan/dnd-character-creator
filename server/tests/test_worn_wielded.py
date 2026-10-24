"""G2: worn / wielded equipment model (decision D3 option c).

RAW checked against the catalog text:
- Mage Armor (Armor of Shadows): "The target's base AC becomes 13 + its Dexterity modifier." It
  ends if the target dons armor. A character that wears no armor gets 13 + DEX; a shield is fine.
- Unarmored Defense (Barbarian): applies "while you are not wearing any armor"; carrying armor
  in the pack does not matter.
- Dueling (PHB and SRD): "When you are wielding a melee weapon in one hand and no other weapons,
  you gain a +2 bonus to damage rolls with that weapon." XPHB: "holding a Melee weapon in one hand
  and no other weapons". A shield (not a weapon) is allowed; a versatile weapon held in one
  hand counts as one-handed.
Cases: worn absent (today's best-armor behavior), worn.armor null / id, shield flag, wielded
absent (S5 duelingDamage) vs present (+2 in `damage` only when the rule holds), stale ids,
two-handed with an off-hand item.
"""
from __future__ import annotations

import copy
import gzip
import json
import pathlib
import time

import pytest

from catalog.loader import load
from engine.resolve import resolve

GOLDEN = pathlib.Path(__file__).parent / "golden" / "g2_resolve_baseline.json.gz"


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, base=None, equipment=None, ruleset=None, background="acolyte"):
    d = {
        "name": "t", "sources": ["srd"], "classes": classes,
        "background": {"id": background, "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10, **(base or {})}},
        "equipment": equipment or {"choices": {}, "added": [], "skipped": False}, "details": {},
    }
    if ruleset:
        d["ruleset"] = ruleset
    return d


def _cls(cid, level=1, choices=None):
    return {"classId": cid, "level": level, "choices": choices or {}}


def _added(item_id, qty=1, equipped=True):
    return {"itemId": item_id, "qty": qty, "equipped": equipped}


def _eq(added=(), **extra):
    return {"choices": {}, "added": list(added), "skipped": False, **extra}


def golden_cases() -> dict:
    """Drafts compared against the pre-G2 resolve() output (tests/golden)."""
    from kitchen_sink import KITCHEN_SINK, base_draft
    inv = "class:warlock:2:invocations:eldritch-invocations"
    cases = {
        "srd-fighter20": _draft([_cls("fighter", 20)], {"STR": 16, "DEX": 14}, _eq([_added("longsword"), _added("shield")])),
        "srd-warlock2-default-kit": _draft([_cls("warlock", 2, {inv: ["eldritch-invocation-armor-of-shadows"]})], {"DEX": 14, "CHA": 16}),
        "srd-barbarian5-chain-in-pack": _draft([_cls("barbarian", 5)], {"STR": 16, "CON": 14}, _eq([_added("chain-mail", equipped=False), _added("greataxe")])),
        "srd-rogue3": _draft([_cls("rogue", 3)], {"DEX": 16}, _eq([_added("shortsword"), _added("longbow")])),
        "srd-monk5-2024": _draft([_cls("monk", 5)], {"DEX": 16, "WIS": 14}, ruleset="2024"),
    }
    for sid in ("barbarian20-2014", "monk14", "paladin6", "cleric6"):
        cases["ks-" + sid] = base_draft(KITCHEN_SINK[sid])
    return cases


G2_KEYS = ("slots", "worn", "wielded")


def strip_g2(res: dict) -> dict:
    """Remove the additive G2 keys so the rest can be compared with the baseline."""
    res = copy.deepcopy(res)
    for k in G2_KEYS:
        res["sheet"]["equipment"].pop(k, None)
    for a in res["derived"].get("attacks", []):
        a.pop("wielded", None)
    res["derived"].pop("featResources", None)  # FE3 additive key (feat-less baseline drafts: always [])
    res["derived"].pop("speciesResources", None)  # W5a additive key (empty for the baseline drafts)
    return res


# ---- old drafts: identical output ------------------------------------------------------------

# Names ending "-2024" are excluded from the strict comparison: 2024 output evolves through the
# C-series stages. Mixed/2014 stability is guarded by test_c_series_golden.py (F0). The entries
# stay in the golden file.
_CASE_NAMES = [n for n in (json.load(gzip.open(GOLDEN, "rt")) if GOLDEN.exists() else []) if not n.endswith("-2024")]


@pytest.mark.parametrize("name", _CASE_NAMES)
def test_drafts_without_worn_or_wielded_resolve_exactly_as_before_g2(catalog, name):
    """The golden file was written from the pre-G2 engine. Only the additive G2 keys may differ."""
    if name.startswith("ks-"):
        from kitchen_sink import KITCHEN_SINK, skip_reason
        reason = skip_reason(KITCHEN_SINK[name[3:]])
        if reason:
            pytest.skip(reason)
    baseline = json.load(gzip.open(GOLDEN, "rt"))[name]
    now = strip_g2(json.loads(json.dumps(resolve(golden_cases()[name], catalog))))
    if name == "ks-monk14":
        # RP7 (E11c): the SRD Monk tool/instrument card is new under mixed / 2014. This pre-G2 baseline draft holds
        # no pick, so the card is the ONLY difference; it must be pending with its 27 options, then it is removed.
        card = next(c for c in now["choices"] if c["id"] == "class:monk:1:prof-choice-1")
        assert card["status"] == "pending" and len(card["options"]) == 27
        now["choices"] = [c for c in now["choices"] if c is not card]
    # RPX2: SRD packs now weigh their contents' sum (the pre-G2 baseline counted 0). RPX3: the counts of the equipment
    # text are real quantities (two handaxes, five javelins; ammunition stays one pack; the Ranger's fixed 20 arrows
    # is one pack). `carried` may differ from the baseline by exactly those, and the quantity fields / "Nx " labels they
    # touch are neutralised on both sides; everything else must be identical.
    import re
    from engine.derived import pack_weights_from_contents
    pack_lb = pack_weights_from_contents(catalog.items)

    def slots(res):
        return [e for k in ("granted", "chosen", "added") for e in res["sheet"]["equipment"][k]]

    base_entries = {k: {e["itemId"]: e for e in baseline["sheet"]["equipment"][k]} for k in ("granted", "chosen")}
    delta = sum(pack_lb.get(e["itemId"], 0) * e.get("qty", 1) for e in slots(now))
    for k in ("granted", "chosen"):
        for e in now["sheet"]["equipment"][k]:
            old = base_entries[k].get(e["itemId"])
            assert old is not None, e
            delta += (catalog.items[e["itemId"]].get("weight") or 0) * (e.get("qty", 1) - old.get("qty", 1))
    assert now["derived"]["carryingCapacity"]["carried"] == pytest.approx(baseline["derived"]["carryingCapacity"]["carried"] + delta)
    for res in (now, baseline):
        res["derived"]["carryingCapacity"]["carried"] = res["derived"]["carryingCapacity"]["overCapacity"] = None
        for k in ("granted", "chosen"):
            for e in res["sheet"]["equipment"][k]:
                e["qty"] = None
        for card in res["choices"]:
            for o in card.get("options", []):
                if "quantities" in o:
                    o.pop("quantities")
                o["label"] = re.sub(r"^\d+x ", "", o["label"]) if card["id"].endswith(tuple(f"equipment-choice-{i}" for i in range(9))) else o["label"]
    _neutralise_class_feature_tails(now, baseline)
    assert now == baseline


def _neutralise_class_feature_tails(*results):
    """W6 / W7 / W8: the SRD class-feature, subclass-feature and book subclass tails add resources (RESOURCE_TAIL_2014, SUBCLASS_TAIL_2014)
    and notes on existing ones (RESOURCE_NOTES_2014, SUBCLASS_NOTES_2014) that the pre-G2 baseline lacks; both are
    removed on both sides."""
    from catalog import reference_data
    from engine.class_resources import _slug
    new_ids = {f"{s['class']}:{_slug(s['name'])}" for s in reference_data.RESOURCE_TAIL_2014 + reference_data.SUBCLASS_TAIL_2014
               + reference_data.SUBCLASS_TAIL_2014_BOOKS}
    targets = {s["target"] for s in reference_data.RESOURCE_NOTES_2014 + reference_data.SUBCLASS_NOTES_2014
               + reference_data.SUBCLASS_NOTES_2014_BOOKS}
    for res in results:
        kept = []
        for r in res["derived"]["classResources"]:
            if r["id"] in new_ids:
                continue
            if r["id"] in targets and r.get("details"):
                r["details"].pop("note", None)
                if not r["details"]:
                    del r["details"]
            kept.append(r)
        res["derived"]["classResources"] = kept


def test_auto_mode_has_no_worn_or_wielded_state_and_no_wielded_flags(catalog):
    r = resolve(_draft([_cls("fighter", 1)], {}, _eq([_added("longsword")])), catalog)
    eq = r["sheet"]["equipment"]
    assert "worn" not in eq and "wielded" not in eq
    assert all("wielded" not in a for a in r["derived"]["attacks"])
    assert {o["itemId"] for o in eq["slots"]["hands"]} >= {"longsword"}


# ---- armor class -----------------------------------------------------------------------------

_INV = "class:warlock:2:invocations:eldritch-invocations"
_AOS = "eldritch-invocation-armor-of-shadows"


def _warlock(worn=None, **eq):
    equipment = _eq(**eq)
    if worn is not None:
        equipment["worn"] = worn
    return _draft([_cls("warlock", 2, {_INV: [_AOS]})], {"DEX": 14}, equipment)


def test_warlock_default_kit_without_worn_keeps_the_leather_armor_ac(catalog):
    r = resolve(_warlock(), catalog)
    assert r["derived"]["armorClass"] == 13  # leather 11 + DEX 2; the kit's armor counts as worn


def test_warlock_default_kit_worn_armor_null_gets_armor_of_shadows(catalog):
    r = resolve(_warlock({"armor": None}), catalog)
    assert r["derived"]["armorClass"] == 15  # 13 + DEX 2
    assert r["sheet"]["equipment"]["worn"] == {"armor": None, "shield": False, "manual": True}
    assert not [w for w in r["warnings"] if w["id"].startswith(("worn-", "armor-"))]


def test_warlock_choosing_the_leather_armor_explicitly_is_the_same_as_auto(catalog):
    r = resolve(_warlock({"armor": "leather-armor"}), catalog)
    assert r["derived"]["armorClass"] == 13
    assert r["sheet"]["equipment"]["worn"]["armor"] == "leather-armor"


def test_armor_of_shadows_allows_a_shield(catalog):
    r = resolve(_warlock({"armor": None, "shield": True}, added=[_added("shield", equipped=False)]), catalog)
    assert r["derived"]["armorClass"] == 17


def test_barbarian_unarmored_defense_with_chain_mail_in_the_pack(catalog):
    base = {"DEX": 14, "CON": 14}  # human +1: DEX 15 (+2), CON 15 (+2)
    draft = _draft([_cls("barbarian", 1)], base, _eq([_added("chain-mail")]))
    assert resolve(draft, catalog)["derived"]["armorClass"] == 16  # today: chain mail is worn
    draft["equipment"]["worn"] = {"armor": None}
    r = resolve(draft, catalog)
    assert r["derived"]["armorClass"] == 14  # 10 + DEX 2 + CON 2
    assert not [w for w in r["warnings"] if w["id"].startswith("armor-")]  # not worn: no proficiency warning
    assert r["derived"]["stealthDisadvantage"] is False


def test_worn_armor_replaces_the_best_of_several_equipped(catalog):
    draft = _draft([_cls("fighter", 1)], {"DEX": 14}, _eq([_added("chain-mail"), _added("leather-armor")]))
    assert "armor-multiple-body" in [w["id"] for w in resolve(draft, catalog)["warnings"]]
    draft["equipment"]["worn"] = {"armor": "leather-armor"}
    r = resolve(draft, catalog)
    assert r["derived"]["armorClass"] == 13
    assert "armor-multiple-body" not in [w["id"] for w in r["warnings"]]


def test_worn_armor_can_be_an_unequipped_added_item(catalog):
    draft = _draft([_cls("fighter", 1)], {"DEX": 14}, _eq([_added("chain-mail", equipped=False)]))
    assert resolve(draft, catalog)["derived"]["armorClass"] == 12
    draft["equipment"]["worn"] = {"armor": "chain-mail"}
    assert resolve(draft, catalog)["derived"]["armorClass"] == 16


def test_shield_flag_false_drops_an_equipped_shield_and_none_means_auto(catalog):
    draft = _draft([_cls("fighter", 1)], {"DEX": 14}, _eq([_added("shield")]))
    assert resolve(draft, catalog)["derived"]["armorClass"] == 14
    draft["equipment"]["worn"] = {"shield": False}
    assert resolve(draft, catalog)["derived"]["armorClass"] == 12
    draft["equipment"]["worn"] = {"shield": None}
    assert resolve(draft, catalog)["derived"]["armorClass"] == 14
    draft["equipment"]["worn"] = {"shield": True}
    assert resolve(draft, catalog)["derived"]["armorClass"] == 14


def test_shield_flag_true_wears_an_unequipped_shield(catalog):
    draft = _draft([_cls("fighter", 1)], {"DEX": 14}, _eq([_added("shield", equipped=False)], worn={"shield": True}))
    assert resolve(draft, catalog)["derived"]["armorClass"] == 14


def test_worn_state_feeds_speed_stealth_and_fast_movement(catalog):
    barb = _draft([_cls("barbarian", 5)], {"STR": 14}, _eq([_added("plate-armor")]))
    assert resolve(barb, catalog)["derived"]["stealthDisadvantage"] is True
    base_speed = resolve(barb, catalog)["derived"]["speed"]
    barb["equipment"]["worn"] = {"armor": None}
    r = resolve(barb, catalog)
    assert r["derived"]["stealthDisadvantage"] is False
    assert r["derived"]["speed"] == base_speed + 10  # Fast Movement is back (was blocked by heavy armor)
    monk = _draft([_cls("monk", 2)], {"DEX": 14}, _eq([_added("leather-armor")]))
    slow = resolve(monk, catalog)["derived"]["speed"]
    monk["equipment"]["worn"] = {"armor": None}
    assert resolve(monk, catalog)["derived"]["speed"] > slow  # Unarmored Movement


# ---- Dueling and the hands ---------------------------------------------------------------------

_FS = "class:fighter:1:feature:fighter-fighting-style"


def _duelist(wielded=None, added=(), worn=None):
    equipment = _eq(added)
    if wielded is not None:
        equipment["wielded"] = wielded
    if worn is not None:
        equipment["worn"] = worn
    return _draft([_cls("fighter", 1, {_FS: ["fighter-fighting-style-dueling"]})], {"STR": 16}, equipment)  # STR 17 (+3)


def _row(r, item):
    return next(a for a in r["derived"]["attacks"] if a["itemId"] == item)


_KIT = [_added("longsword"), _added("shortsword"), _added("shield"), _added("greatsword"), _added("longbow")]


def test_no_wielded_keeps_the_s5_dueling_damage_field(catalog):
    a = _row(resolve(_duelist(added=_KIT), catalog), "longsword")
    assert (a["damage"], a["duelingDamage"]) == ("1d8+3", "1d8+5")
    assert "Dueling: only with no other weapon" in a["notes"]
    assert "wielded" not in a


def test_dueling_longsword_main_and_shield_off_applies_plus_two(catalog):
    r = resolve(_duelist({"main": "longsword", "off": "shield"}, _KIT), catalog)
    a = _row(r, "longsword")
    assert (a["damage"], a["duelingDamage"], a["wielded"]) == ("1d8+5", None, True)
    assert a["versatileDamage"] == "1d10+3"  # the two-handed grip never gets Dueling
    assert "Dueling: only with no other weapon" not in a["notes"]
    assert _row(r, "shortsword")["wielded"] is False
    assert _row(r, "shortsword")["damage"] == "1d6+3" and _row(r, "shortsword")["duelingDamage"] is None


def test_dueling_longsword_main_and_empty_off_hand_applies(catalog):
    a = _row(resolve(_duelist({"main": "longsword", "off": None}, _KIT), catalog), "longsword")
    assert a["damage"] == "1d8+5"


def test_dueling_longsword_main_and_shortsword_off_has_no_bonus(catalog):
    r = resolve(_duelist({"main": "longsword", "off": "shortsword"}, _KIT), catalog)
    assert _row(r, "longsword")["damage"] == "1d8+3" and _row(r, "longsword")["duelingDamage"] is None
    assert _row(r, "shortsword")["damage"] == "1d6+3"  # off hand: not the main weapon, no Dueling either
    assert _row(r, "shortsword")["wielded"] is True


def test_dueling_never_applies_to_two_handed_ranged_or_unwielded_main(catalog):
    r = resolve(_duelist({"main": "greatsword", "off": None}, _KIT), catalog)
    assert _row(r, "greatsword")["damage"] == "2d6+3" and _row(r, "greatsword")["duelingDamage"] is None
    r = resolve(_duelist({"main": "longbow", "off": None}, _KIT), catalog)
    assert _row(r, "longbow")["damage"].startswith("1d8")
    assert _row(r, "longbow")["duelingDamage"] is None
    r = resolve(_duelist({"main": None, "off": None}, _KIT), catalog)  # bare hands: nobody gets +2
    assert _row(r, "longsword")["damage"] == "1d8+3" and _row(r, "longsword")["wielded"] is False


def test_dueling_wielded_set_without_the_style_changes_nothing_in_damage(catalog):
    draft = _draft([_cls("fighter", 1)], {"STR": 16}, _eq(_KIT, wielded={"main": "longsword", "off": "shield"}))
    a = _row(resolve(draft, catalog), "longsword")
    assert (a["damage"], a["duelingDamage"], a["wielded"]) == ("1d8+3", None, True)


def test_wielded_weapon_is_an_attack_even_when_not_flagged_equipped(catalog):
    draft = _draft([_cls("fighter", 1)], {"STR": 16}, _eq([_added("longsword", equipped=False)], wielded={"main": "longsword"}))
    assert _row(resolve(draft, catalog), "longsword")["wielded"] is True


def test_granted_and_chosen_items_can_be_wielded(catalog):
    draft = _draft([_cls("rogue", 1)], {"DEX": 16}, _eq(wielded={"main": "dagger"}))
    r = resolve(draft, catalog)
    assert _row(r, "dagger")["wielded"] is True


# ---- validation ----------------------------------------------------------------------------------

def _ids(r):
    return [w["id"] for w in r["warnings"]]


def test_two_handed_main_with_an_off_hand_item_warns(catalog):
    r = resolve(_duelist({"main": "greatsword", "off": "shield"}, _KIT), catalog)
    assert "wielded-two-handed-conflict" in _ids(r)
    r = resolve(_duelist({"main": "greatsword", "off": None}, _KIT), catalog)
    assert "wielded-two-handed-conflict" not in _ids(r)
    r = resolve(_duelist({"main": "greatsword", "off": None}, _KIT, worn={"shield": True}), catalog)
    assert "wielded-two-handed-shield" in _ids(r)


def test_unknown_and_missing_items_are_non_blocking_warnings_and_ignored(catalog):
    r = resolve(_duelist({"main": "no-such-sword", "off": "longbow"}, [_added("shortsword")]), catalog)
    ids = _ids(r)
    assert "wielded-main-unknown-item" in ids and "wielded-off-not-in-inventory" in ids
    assert r["problems"] == [] or all(not p["id"].startswith("wielded") for p in r["problems"])
    assert r["sheet"]["equipment"]["wielded"] == {"main": None, "off": None, "manual": True}
    assert any(p["choiceId"] == "equipment:wielded:off" for p in r["pruned"])
    assert all(a["itemId"] != "longbow" for a in r["derived"]["attacks"])


def test_stale_worn_armor_is_pruned_and_falls_back_to_auto(catalog):
    draft = _draft([_cls("fighter", 1)], {"DEX": 14}, _eq([_added("leather-armor")], worn={"armor": "plate-armor"}))
    r = resolve(draft, catalog)
    assert "worn-armor-not-in-inventory" in _ids(r)
    assert any(p["choiceId"] == "equipment:worn:armor" for p in r["pruned"])
    assert r["derived"]["armorClass"] == 13  # the stale id was dropped: auto leather armor
    assert r["sheet"]["equipment"]["worn"]["armor"] == "leather-armor"


def test_removing_the_item_from_the_inventory_prunes_it(catalog):
    draft = _duelist({"main": "longsword", "off": "shield"}, _KIT)
    assert resolve(draft, catalog)["pruned"] == []
    draft["equipment"]["added"] = [e for e in draft["equipment"]["added"] if e["itemId"] != "longsword"]
    r = resolve(draft, catalog)
    assert any(p["choiceId"] == "equipment:wielded:main" for p in r["pruned"])
    assert r["sheet"]["equipment"]["wielded"]["main"] is None


def test_body_armor_in_a_hand_or_a_shield_in_the_armor_slot_warns(catalog):
    kit = [_added("chain-mail"), _added("shield"), _added("longsword")]
    r = resolve(_duelist({"main": "chain-mail", "off": None}, kit), catalog)
    assert "wielded-main-not-holdable" in _ids(r)
    assert _row(r, "longsword")["damage"] == "1d8+3"
    r = resolve(_duelist({"main": "shield", "off": None}, kit), catalog)
    assert "wielded-main-shield" in _ids(r)
    r = resolve(_duelist(None, kit, worn={"armor": "shield"}), catalog)
    assert "worn-armor-not-body-armor" in _ids(r)
    r = resolve(_duelist(None, kit, worn={"armor": "longsword"}), catalog)
    assert "worn-armor-not-body-armor" in _ids(r)


def test_shield_true_without_a_shield_and_unknown_armor_id_warn(catalog):
    r = resolve(_duelist(None, [_added("longsword")], worn={"shield": True, "armor": "no-such-armor"}), catalog)
    assert "worn-shield-missing" in _ids(r) and "worn-armor-unknown-item" in _ids(r)


def test_same_weapon_in_both_hands_needs_two_copies(catalog):
    r = resolve(_duelist({"main": "shortsword", "off": "shortsword"}, [_added("shortsword")]), catalog)
    assert "wielded-same-item-twice" in _ids(r)
    r = resolve(_duelist({"main": "shortsword", "off": "shortsword"}, [_added("shortsword", qty=2)]), catalog)
    assert "wielded-same-item-twice" not in _ids(r)


def test_shield_in_off_hand_counts_as_a_worn_shield_in_auto_mode_and_conflicts_with_false(catalog):
    draft = _duelist({"main": "longsword", "off": "shield"}, [_added("longsword"), _added("shield", equipped=False)])
    assert resolve(draft, catalog)["derived"]["armorClass"] == 10 + 0 + 2  # human DEX 10 +0; shield +2
    draft["equipment"]["worn"] = {"shield": False}
    r = resolve(draft, catalog)
    assert "wielded-shield-not-worn" in _ids(r) and r["derived"]["armorClass"] == 10


def test_malformed_worn_and_wielded_are_dropped_with_problems(catalog):
    draft = _duelist(None, [_added("longsword")])
    draft["equipment"]["worn"] = "plate"
    draft["equipment"]["wielded"] = {"main": 5, "off": ["x"]}
    r = resolve(draft, catalog)
    ids = [p["id"] for p in r["problems"]]
    assert "malformed-equipment-worn" in ids and "malformed-equipment-wielded" in ids
    assert "worn" not in r["sheet"]["equipment"]


# ---- slots, exports, speed ------------------------------------------------------------------------

def test_slot_options_list_the_resolved_inventory(catalog):
    draft = _draft([_cls("fighter", 1)], {}, _eq([_added("chain-mail", equipped=False), _added("shield"), _added("longsword"), _added("rope-hempen-50-feet")]))
    s = resolve(draft, catalog)["sheet"]["equipment"]["slots"]
    assert [o["itemId"] for o in s["armor"]] == ["chain-mail"]
    assert [o["itemId"] for o in s["shield"]] == ["shield"]
    hands = {o["itemId"]: o for o in s["hands"]}
    assert "longsword" in hands and "shield" in hands and "chain-mail" not in hands
    assert hands["longsword"]["twoHanded"] is False


def test_markdown_and_pdf_print_the_same_worn_wielded_line(catalog):
    import io
    from markdown_export import to_markdown
    from pdf_export import to_pdf
    from pypdf import PdfReader
    r = resolve(_duelist({"main": "longsword", "off": "shield"}, _KIT, worn={"armor": None, "shield": True}), catalog)
    md = to_markdown(r)
    line = next(ln for ln in md.splitlines() if ln.startswith("Носено:"))
    assert "без броня" in line and "щит" in line and "Longsword" in line and "Shield" in line
    pdf_text = "".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(r))).pages)
    assert " ".join(line.split()) in " ".join(pdf_text.split())
    plain = resolve(_duelist(None, _KIT), catalog)
    assert "Носено:" not in to_markdown(plain)


def test_yaml_carries_worn_and_wielded_through_sheet_equipment(catalog):
    import yaml
    from export import to_yaml
    r = resolve(_duelist({"main": "longsword", "off": "shield"}, _KIT), catalog)
    doc = yaml.safe_load(to_yaml(r))
    assert doc["equipment"]["wielded"]["main"] == "longsword"


def test_resolve_stays_fast_for_a_level_20_fighter_with_worn_and_wielded(catalog):
    draft = _duelist({"main": "longsword", "off": "shield"}, _KIT, worn={"armor": None, "shield": True})
    draft["classes"][0]["level"] = 20
    resolve(draft, catalog)
    t0 = time.perf_counter()
    for _ in range(20):
        resolve(draft, catalog)
    assert (time.perf_counter() - t0) / 20 < 0.05
