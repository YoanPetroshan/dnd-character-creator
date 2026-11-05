"""G1: 2014 Hunter (SRD) and Totem Warrior (PHB) pick effects as note-only subclass resources, the 2014 twin of RP13.

Governing texts (catalog.features; `reference_data.SUBCLASS_PICK_RESOURCES_2014` carries a verbatim quote per option,
pinned by `test_every_quote_is_in_its_record`):
  Hunter 3 Hunter's Prey        Colossus Slayer "You can deal this extra damage only once per turn." (turn);
                                Giant Killer "you can use your reaction to attack that creature" (reaction);
                                Horde Breaker "Once on each of your turns when you make a weapon attack" (turn)
  Hunter 7 Defensive Tactics    Escape the Horde, Multiattack Defense (+4 AC), Steel Will: passive, notes only
  Hunter 11 Multiattack         Volley, Whirlwind Attack: "You can use your action ...", notes only
  Hunter 15 Superior Hunter's Defense  Evasion (passive); Stand Against the Tide and Uncanny Dodge ("you can use your
                                reaction ...")
  Totem Warrior 3 Totem Spirit / 6 Aspect of the Beast / 14 Totemic Attunement: bear, eagle, elk, tiger, wolf (each
                                option has its own "Name. text" line); Elk Totemic Attunement: "Strength saving throw
                                (DC 8 + your Strength bonus + your proficiency bonus) ... bludgeoning damage equal to
                                1d12 + your Strength modifier"; every other option states no number.

Rule matrix:
  entries   one note-only subclass resource "<Feature>: <Option>" (id `<cls>:<slug>`, source kind subclass) per picked
            option, only under mixed / 2014 with the SRD Hunter or the PHB Totem Warrior selected and the class at the
            feature record's level; no pick, a pick that is no longer offered, 2024 or another subclass give nothing
  limits    uses 1 + recharge "turn" (X2 vocabulary) for Colossus Slayer and Horde Breaker; uses 1 + recharge "other"
            with "Reaction:" first in the note for Giant Killer, Stand Against the Tide and Uncanny Dodge; every other
            entry has no uses and no recharge
  DC        only the Elk Totemic Attunement: `dc` and the note's "DC n" = 8 + proficiency bonus + Strength modifier
  2024      untouched: the 2024 Hunter entries keep their ids, texts and (empty) limits, and a 2014 pick never reads
            the 2024 attack-row note
  mixed     identical to 2014"""
import copy
import re

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve
from export_fields import resource_line
from perf_helpers import assert_fast, measure

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

TABLE = "SUBCLASS_PICK_RESOURCES_2014"
HUNTER, TOTEM = "hunter", "totem-warrior-phb"

# (class, subclass, card feature id, feature label, class level of the card, [(option id, option name)])
CARDS = [
    ("ranger", HUNTER, "hunters-prey", "Hunter's Prey", 3,
     [("hunters-prey-colossus-slayer", "Colossus Slayer"), ("hunters-prey-giant-killer", "Giant Killer"),
      ("hunters-prey-horde-breaker", "Horde Breaker")]),
    ("ranger", HUNTER, "defensive-tactics", "Defensive Tactics", 7,
     [("defensive-tactics-escape-the-horde", "Escape the Horde"),
      ("defensive-tactics-multiattack-defense", "Multiattack Defense"), ("defensive-tactics-steel-will", "Steel Will")]),
    ("ranger", HUNTER, "multiattack", "Multiattack", 11,
     [("multiattack-volley", "Volley"), ("multiattack-whirlwind-attack", "Whirlwind Attack")]),
    ("ranger", HUNTER, "superior-hunters-defense", "Superior Hunter's Defense", 15,
     [("superior-hunters-defense-evasion", "Evasion"),
      ("superior-hunters-defense-stand-against-the-tide", "Stand Against the Tide"),
      ("superior-hunters-defense-uncanny-dodge", "Uncanny Dodge")]),
] + [
    ("barbarian", TOTEM, f"totem-warrior-phb-{lvl}-{slug}", label, lvl,
     [(f"totem-warrior-phb-{lvl}-{slug}--{a}", a.title()) for a in ("bear", "eagle", "elk", "tiger", "wolf")])
    for lvl, slug, label in ((3, "totem-spirit", "Totem Spirit"), (6, "aspect-of-the-beast", "Aspect of the Beast"),
                             (14, "totemic-attunement", "Totemic Attunement"))
]
ALL = [(c, s, f, lbl, lvl, oid, oname) for c, s, f, lbl, lvl, opts in CARDS for oid, oname in opts]

# Independent expectation of the limits (from the quoted texts, not from the table).
TURN = {"hunters-prey-colossus-slayer", "hunters-prey-horde-breaker"}
REACTION = {"hunters-prey-giant-killer", "superior-hunters-defense-stand-against-the-tide",
            "superior-hunters-defense-uncanny-dodge"}
# A fragment each note must carry (checked against the quoted text by `test_notes_state_what_the_text_states`).
FRAGMENT = {
    "hunters-prey-colossus-slayer": "1d8", "hunters-prey-giant-killer": "Large or larger",
    "hunters-prey-horde-breaker": "different creature",
    "defensive-tactics-escape-the-horde": "disadvantage", "defensive-tactics-multiattack-defense": "+4 bonus to AC",
    "defensive-tactics-steel-will": "frightened", "multiattack-volley": "10 feet of a point",
    "multiattack-whirlwind-attack": "within 5 feet of you", "superior-hunters-defense-evasion": "no damage",
    "superior-hunters-defense-stand-against-the-tide": "repeat the same attack",
    "superior-hunters-defense-uncanny-dodge": "halve",
}

PB = {1: 2, 5: 3, 9: 4, 13: 5, 17: 6}


def pb(level):
    return PB[max(k for k in PB if k <= level)]


def rid(label, name):
    return "-".join(re.sub(r"[^a-z0-9]+", " ", f"{label}: {name}".lower()).split())


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls, level, sub, picks=None, ruleset="2014", strength=16, sources=()):
    return {"ruleset": ruleset, "sources": list(sources),
            "abilities": {"method": "manual", "base": {"STR": strength, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12,
                                                       "CHA": 8}},
            "species": {"id": "human"}, "background": {"id": "acolyte"},
            "equipment": {"choices": {}, "added": [{"itemId": "longsword", "qty": 1, "equipped": True}],
                          "skipped": False},
            "classes": [{"classId": cls, "level": level, **({"subclassId": sub} if sub else {}),
                         "choices": dict(picks or {})}]}


def _cid(cls, lvl, fid):
    return f"class:{cls}:{lvl}:feature:{fid}"


def _build(catalog, cards, level, ruleset="2014", strength=16, sources=()):
    """cards: [(cls, sub, fid, lvl, option id)] of one class."""
    cls, sub = cards[0][0], cards[0][1]
    picks = {_cid(c, lvl_, fid): [oid] for c, _s, fid, lvl_, oid in cards}
    return resolve(_draft(cls, level, sub, picks, ruleset, strength, sources), catalog)


def _resources(res):
    return {r["id"]: r for r in res["derived"]["classResources"]}


LABELS = tuple(f"{lbl}: " for _c, _s, _f, lbl, _l, _o in CARDS)


def _pick_resources(res):
    return [r for r in res["derived"]["classResources"] if r["source"]["kind"] == "subclass"
            and r["name"].startswith(LABELS)]


def _text(catalog, fid):
    rec = catalog.features[fid]
    return rec["name"] + "\n" + "\n".join(rec["desc"])


# ---- data ----------------------------------------------------------------------------------------------------------

@needs_data
def test_every_quote_is_in_its_record(catalog):
    table = getattr(reference_data, TABLE)
    assert set(table) == {fid for _c, _s, fid, _l, _lvl, _o in CARDS}
    for fid, spec in table.items():
        rec = catalog.features[fid]
        assert (rec["class"] or {}).get("index") == spec["class"], fid
        assert (rec["subclass"] or {}).get("index") == spec["subclass"], fid
        assert spec["label"] == next(lbl for _c, _s, f, lbl, _l, _o in CARDS if f == fid)
        for oid, option in spec["options"].items():
            record = option.get("record", fid)
            assert option["quote"] in _text(catalog, record), (fid, oid)
            assert len(option["quote"]) > 20, oid
            if "record" not in option:  # a Totem line: "Name. text"
                assert option["quote"].startswith(option["name"] + ". "), oid


@needs_data
def test_options_are_exactly_the_cards_options_nothing_skipped(catalog):
    """Every option of the imported pick card has an entry (a skipped option would be a silent gap)."""
    table = getattr(reference_data, TABLE)
    for cls, sub, fid, lbl, lvl, opts in CARDS:
        assert [o for o in table[fid]["options"]] == [o for o, _n in opts], fid
        assert [o["name"] for o in table[fid]["options"].values()] == [n for _o, n in opts], fid
        card = next(c for c in _build(catalog, [(cls, sub, fid, lvl, opts[0][0])], max(lvl, 3))["choices"]
                    if c["id"] == _cid(cls, lvl, fid))
        assert [o["id"] for o in card["options"]] == [o for o, _n in opts], fid


@needs_data
def test_limits_in_the_table_follow_the_x2_vocabulary(catalog):
    table = getattr(reference_data, TABLE)
    for fid, spec in table.items():
        for oid, option in spec["options"].items():
            recharge = option.get("recharge")
            if oid in TURN:
                assert (option.get("uses"), recharge) == (1, "turn"), oid
                assert recharge in reference_data.RESOURCE_RECHARGES
            elif oid in REACTION:
                assert (option.get("uses"), recharge) == (1, "other"), oid
                assert option["note"].startswith("Reaction"), oid
            else:
                assert "uses" not in option and "recharge" not in option, oid
            assert ("dc" in option) == (oid == "totem-warrior-phb-14-totemic-attunement--elk"), oid


@needs_data
@pytest.mark.parametrize("oid", sorted(TURN | REACTION))
def test_limits_are_stated_by_the_quoted_text(catalog, oid):
    """Only a text that states the limit gets one: the quote itself carries the phrase."""
    spec = next(s for s in getattr(reference_data, TABLE).values() if oid in s["options"])
    quote = spec["options"][oid]["quote"]
    assert ("only once per turn" in quote or "Once on each of your turns" in quote) if oid in TURN \
        else "you can use your reaction" in quote


# ---- resolve: every pick, at the card's own level --------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cls,sub,fid,lbl,lvl,oid,oname", ALL, ids=[a[5] for a in ALL])
def test_each_pick_gives_one_note_only_subclass_resource(catalog, cls, sub, fid, lbl, lvl, oid, oname):
    res = _build(catalog, [(cls, sub, fid, lvl, oid)], lvl)
    mine = _pick_resources(res)
    assert [r["name"] for r in mine] == [f"{lbl}: {oname}"]
    r = mine[0]
    assert r["id"] == f"{cls}:{rid(lbl, oname)}" and r["classId"] == cls
    assert r["source"]["kind"] == "subclass" and r["source"]["id"] == sub
    assert r["details"]["note"].strip() and "{" not in r["details"]["note"]
    if oid in TURN:
        assert (r["uses"], r["recharge"]) == (1, "turn")
    elif oid in REACTION:
        assert (r["uses"], r["recharge"]) == (1, "other") and r["details"]["note"].startswith("Reaction")
    else:
        assert r["uses"] is None and r["recharge"] is None
    if oid in FRAGMENT:
        assert FRAGMENT[oid] in r["details"]["note"], oid
    assert ("dc" in r) == (oid == "totem-warrior-phb-14-totemic-attunement--elk")
    assert not any(k in r for k in ("die", "dice", "pool", "bonus", "unlimited"))


@needs_data
def test_notes_state_what_the_text_states(catalog):
    """Words of the quoted text that decide an entry reach its note (numbers and conditions are not invented)."""
    table = getattr(reference_data, TABLE)
    needles = {
        "totem-warrior-phb-3-totem-spirit--bear": ("resistance to all damage except psychic", "raging"),
        "totem-warrior-phb-3-totem-spirit--eagle": ("disadvantage on opportunity attack", "Dash", "heavy armor"),
        "totem-warrior-phb-3-totem-spirit--elk": ("15 feet", "heavy armor"),
        "totem-warrior-phb-3-totem-spirit--tiger": ("10 feet", "3 feet"),
        "totem-warrior-phb-3-totem-spirit--wolf": ("advantage on melee attack rolls", "5 feet"),
        "totem-warrior-phb-6-aspect-of-the-beast--bear": ("doubled", "Strength checks"),
        "totem-warrior-phb-6-aspect-of-the-beast--eagle": ("1 mile", "100 feet", "dim light"),
        "totem-warrior-phb-6-aspect-of-the-beast--elk": ("doubled", "ten companions", "60 feet"),
        "totem-warrior-phb-6-aspect-of-the-beast--tiger": ("two skills", "Athletics", "Survival"),
        "totem-warrior-phb-6-aspect-of-the-beast--wolf": ("track", "stealthily"),
        "totem-warrior-phb-14-totemic-attunement--bear": ("disadvantage on attack rolls", "5 feet"),
        "totem-warrior-phb-14-totemic-attunement--eagle": ("flying speed", "current walking speed", "fall"),
        "totem-warrior-phb-14-totemic-attunement--tiger": ("20 feet", "additional melee weapon attack"),
        "totem-warrior-phb-14-totemic-attunement--wolf": ("knock", "prone"),
    }
    for fid, spec in table.items():
        for oid, (needle_set) in ((o, needles[o]) for o in spec["options"] if o in needles):
            note = spec["options"][oid]["note"].lower()
            for needle in needle_set:
                assert needle.lower() in note, (oid, needle)
                assert needle.lower() in spec["options"][oid]["quote"].lower() or needle.lower() in _text(
                    catalog, spec["options"][oid].get("record", fid)).lower(), (oid, needle)


@needs_data
@pytest.mark.parametrize("strength,level", [(16, 14), (8, 14), (20, 14), (12, 18)])
def test_elk_totemic_attunement_dc_is_8_plus_pb_plus_strength(catalog, strength, level):
    """The text gives the DC ("8 + your Strength bonus + your proficiency bonus"); the Strength modifier is final."""
    oid = "totem-warrior-phb-14-totemic-attunement--elk"
    res = _build(catalog, [("barbarian", TOTEM, "totem-warrior-phb-14-totemic-attunement", 14, oid)], level,
                 strength=strength)
    r = _resources(res)["barbarian:totemic-attunement-elk"]
    mod = res["derived"]["abilityModifiers"]["STR"]
    assert res["derived"]["proficiencyBonus"] == pb(level)
    assert r["dc"] == 8 + pb(level) + mod
    assert f"DC {r['dc']}" in r["details"]["note"]
    assert f"1d12{mod:+d}" in r["details"]["note"]


@needs_data
def test_only_the_elk_attunement_has_a_dc(catalog):
    for oid in ("bear", "eagle", "tiger", "wolf"):
        res = _build(catalog, [("barbarian", TOTEM, "totem-warrior-phb-14-totemic-attunement", 14,
                                f"totem-warrior-phb-14-totemic-attunement--{oid}")], 14)
        assert "dc" not in _resources(res)[f"barbarian:totemic-attunement-{oid}"]
        assert "DC" not in _resources(res)[f"barbarian:totemic-attunement-{oid}"]["details"]["note"]


# ---- combinations, switching, absence -------------------------------------------------------------------------------

@needs_data
def test_ranger_11_with_three_picks_lists_them_after_the_class_entries_in_card_order(catalog):
    cards = [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-horde-breaker"),
             ("ranger", HUNTER, "defensive-tactics", 7, "defensive-tactics-multiattack-defense"),
             ("ranger", HUNTER, "multiattack", 11, "multiattack-volley")]
    res = _build(catalog, cards, 11)
    assert [r["name"] for r in _pick_resources(res)] == [
        "Hunter's Prey: Horde Breaker", "Defensive Tactics: Multiattack Defense", "Multiattack: Volley"]


@needs_data
def test_ranger_15_all_four_cards_and_ranger_3_only_the_first(catalog):
    cards = [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-giant-killer"),
             ("ranger", HUNTER, "defensive-tactics", 7, "defensive-tactics-steel-will"),
             ("ranger", HUNTER, "multiattack", 11, "multiattack-whirlwind-attack"),
             ("ranger", HUNTER, "superior-hunters-defense", 15, "superior-hunters-defense-uncanny-dodge")]
    assert len(_pick_resources(_build(catalog, cards, 15))) == 4
    low = _build(catalog, cards, 3)  # the higher cards are not offered at level 3: their picks are pruned
    assert [r["name"] for r in _pick_resources(low)] == ["Hunter's Prey: Giant Killer"]
    assert any(p for p in low["pruned"])


@needs_data
def test_barbarian_14_three_totem_cards_with_different_animals(catalog):
    cards = [("barbarian", TOTEM, "totem-warrior-phb-3-totem-spirit", 3, "totem-warrior-phb-3-totem-spirit--wolf"),
             ("barbarian", TOTEM, "totem-warrior-phb-6-aspect-of-the-beast", 6,
              "totem-warrior-phb-6-aspect-of-the-beast--tiger"),
             ("barbarian", TOTEM, "totem-warrior-phb-14-totemic-attunement", 14,
              "totem-warrior-phb-14-totemic-attunement--elk")]
    res = _build(catalog, cards, 14)
    assert [r["name"] for r in _pick_resources(res)] == [
        "Totem Spirit: Wolf", "Aspect of the Beast: Tiger", "Totemic Attunement: Elk"]
    assert "barbarian:rage" in _resources(res)
    mid = _build(catalog, cards, 6)
    assert [r["name"] for r in _pick_resources(mid)] == ["Totem Spirit: Wolf", "Aspect of the Beast: Tiger"]
    assert [r["name"] for r in _pick_resources(_build(catalog, cards, 3))] == ["Totem Spirit: Wolf"]


@needs_data
def test_switching_the_pick_moves_the_entry(catalog):
    a = _build(catalog, [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-colossus-slayer")], 3)
    b = _build(catalog, [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-giant-killer")], 3)
    assert [r["name"] for r in _pick_resources(a)] == ["Hunter's Prey: Colossus Slayer"]
    assert [r["name"] for r in _pick_resources(b)] == ["Hunter's Prey: Giant Killer"]


@needs_data
def test_no_pick_gives_no_entry(catalog):
    res = resolve(_draft("ranger", 15, HUNTER), catalog)
    assert _pick_resources(res) == [] and not any(c["selected"] for c in res["choices"] if ":feature:" in c["id"])
    assert _pick_resources(resolve(_draft("barbarian", 14, TOTEM), catalog)) == []


@needs_data
def test_below_the_card_level_and_without_the_subclass_nothing(catalog):
    assert _pick_resources(resolve(_draft("ranger", 2, HUNTER), catalog)) == []
    # a Hunter pick stored on a Ranger of another subclass (Beast Master) is a stale cid: no entry
    stale = _draft("ranger", 3, "beast-master", {_cid("ranger", 3, "hunters-prey"): ["hunters-prey-colossus-slayer"]})
    assert _pick_resources(resolve(stale, catalog)) == []
    stale = _draft("barbarian", 3, "berserker", {_cid("barbarian", 3, "totem-warrior-phb-3-totem-spirit"):
                                                  ["totem-warrior-phb-3-totem-spirit--bear"]})
    assert _pick_resources(resolve(stale, catalog)) == []


@needs_data
def test_srd_only_sources_keep_the_hunter(catalog):
    hunter = _build(catalog, [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-colossus-slayer")], 3,
                    sources=["srd"])
    assert [r["name"] for r in _pick_resources(hunter)] == ["Hunter's Prey: Colossus Slayer"]


# ---- rulesets ---------------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cls,sub,fid,lbl,lvl,oid,oname", [a for a in ALL if a[5].endswith(("slayer", "elk", "dodge"))],
                         ids=lambda v: v if isinstance(v, str) and "-" in v else "")
def test_mixed_equals_2014(catalog, cls, sub, fid, lbl, lvl, oid, oname):
    cards = [(cls, sub, fid, lvl, oid)]
    assert _resources(_build(catalog, cards, 20, "mixed")) == _resources(_build(catalog, cards, 20, "2014"))


@needs_data
def test_2024_hides_the_2014_subclasses_and_reads_nothing(catalog):
    res = _build(catalog, [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-colossus-slayer")], 3, "2024")
    assert _pick_resources(res) == []
    res = _build(catalog, [("barbarian", TOTEM, "totem-warrior-phb-3-totem-spirit", 3,
                            "totem-warrior-phb-3-totem-spirit--bear")], 3, "2024")
    assert _pick_resources(res) == []


@needs_data
def test_2024_hunter_entries_are_unchanged_and_keep_the_attack_row_note(catalog):
    pick = {"class:ranger:3:feature:hunter-xphb-3-hunters-prey": ["hunter-xphb-3-hunters-prey--colossus-slayer"]}
    res = resolve(_draft("ranger", 3, "hunter-xphb", pick, "2024", sources=()), catalog)
    r = _resources(res)["ranger:hunter-s-prey-colossus-slayer"]
    assert r["source"]["id"] == "hunter-xphb" and r["uses"] is None and r["recharge"] is None
    assert r["details"]["note"].startswith("Once per turn, a weapon hit deals an extra 1d8")
    notes = [n for a in res["derived"]["attacks"] for n in a["notes"]]
    assert "Colossus Slayer: +1d8 once per turn if the target is missing any Hit Points" in notes


@needs_data
def test_a_2014_pick_never_gets_the_2024_attack_row_text(catalog):
    res = _build(catalog, [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-colossus-slayer")], 3)
    assert res["derived"]["attacks"], "the draft holds a longsword"
    for attack in res["derived"]["attacks"]:
        assert not any("Colossus Slayer" in n for n in attack["notes"]), attack


# ---- export and speed ---------------------------------------------------------------------------------------------------

@needs_data
def test_export_lines(catalog):
    res = _build(catalog, [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-colossus-slayer")], 3)
    line = resource_line(_resources(res)["ranger:hunter-s-prey-colossus-slayer"])
    assert line.startswith("Hunter's Prey: Colossus Slayer: 1 (на ход), ") and "1d8" in line
    res = _build(catalog, [("barbarian", TOTEM, "totem-warrior-phb-14-totemic-attunement", 14,
                            "totem-warrior-phb-14-totemic-attunement--elk")], 14)
    assert "DC" in resource_line(_resources(res)["barbarian:totemic-attunement-elk"], "en")


@needs_data
def test_resolve_stays_fast_with_picks(catalog):
    cards = [("ranger", HUNTER, "hunters-prey", 3, "hunters-prey-colossus-slayer"),
             ("ranger", HUNTER, "defensive-tactics", 7, "defensive-tactics-steel-will"),
             ("ranger", HUNTER, "multiattack", 11, "multiattack-volley"),
             ("ranger", HUNTER, "superior-hunters-defense", 15, "superior-hunters-defense-evasion")]
    draft = _draft("ranger", 15, HUNTER, {_cid(c, lvl, fid): [oid] for c, _s, fid, lvl, oid in cards})
    resolve(copy.deepcopy(draft), catalog)
    assert_fast(measure(lambda: resolve(copy.deepcopy(draft), catalog)), "ranger 15 hunter with four picks")
