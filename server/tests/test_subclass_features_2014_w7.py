"""W7 (finding F4, subclass half): the 2014 SRD subclass use-limit tail. SRD subclass features (Berserker, Lore, Life,
Land, Champion, Open Hand, Devotion, Hunter, Thief, Draconic, Fiend, Evocation) whose text gives a use count, a rest rule
or a number the sheet can compute become subclass resources (`reference_data.SUBCLASS_TAIL_2014`, source kind
"subclass", right after the class's own entries and the R6 subclass entries) or a sentence on the resource the feature
spends (`reference_data.SUBCLASS_NOTES_2014`). Rulesets "mixed" and "2014" only, only the 12 SRD subclass ids (the book
subclasses are slice W8); "2024" stays byte-identical. Every entry quotes the catalog text it was built from. Written
before the wiring.

Rule matrix (texts read from the catalog on 2026-10-24; `test_quotes_match_catalog` pins every quote):

 Berserker (Barbarian)  Frenzy (3): bonus-action attack while raging, "one level of exhaustion" when the rage ends.
                        Intimidating Presence (10): DC "8 + your proficiency bonus + your Charisma modifier".
 Lore (Bard)            Cutting Words (3) and Peerless Skill (14) "expend one of your uses of Bardic Inspiration" ->
                        notes on Bardic Inspiration.
 Life (Cleric)          Disciple of Life (1) "2 + the spell's level" (+ Blessed Healer 6); Divine Strike (8) "extra 1d8
                        radiant damage ... 14th level ... 2d8"; Preserve Life (2) "five times your cleric level" -> note
                        on Channel Divinity.
 Land (Druid)           Natural Recovery (2): "half your druid level (rounded up)", once per long rest; Nature's
                        Sanctuary (14): Wisdom save against "your druid spell save DC".
 Champion (Fighter)     Survivor (18): "5 + your Constitution modifier" hit points.
 Open Hand (Monk)       Wholeness of Body (6): "three times your monk level", once per long rest; Tranquility (11): sanctuary
                        DC "8 + your Wisdom modifier + your proficiency bonus"; Quivering Palm (17): 3 ki, "number of days
                        equal to your monk level", 10d10 necrotic -> note on Ki.
 Devotion (Paladin)     Sacred Weapon / Turn the Unholy (3): notes on Channel Divinity (Charisma modifier, minimum +1);
                        Holy Nimbus (20): 30-foot radius, 10 radiant damage (the catalog text has no rest rule).
 Draconic (Sorcerer)    Elemental Affinity (6): Charisma modifier; Draconic Presence (18): 5 sorcery points -> note on
                        Sorcery Points.
 Fiend (Warlock)        Dark One's Blessing (1): "Charisma modifier + your warlock level (minimum of 1)"; Dark One's Own Luck
                        (6): d10, short or long rest; Hurl Through Hell (14): 10d10 psychic damage, long rest.
 Evocation (Wizard)     Empowered Evocation (10): Intelligence modifier; Overchannel (14): first use free, then 2d12 necrotic
                        per spell level (+1d12 per further use) until a long rest.

Scanned and skipped: see ARCHITECTURE-CURRENT-STATE.md (W7 section).
"""
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.class_resources import _slug
from engine.resolve import resolve
from export_fields import resource_line

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

RULESETS_2014 = ["mixed", "2014"]
SRD_SUBCLASSES = {"berserker", "lore", "life", "land", "champion", "open-hand", "devotion", "hunter", "thief", "draconic",
                  "fiend", "evocation"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, cls, level, sub, ruleset="2014", abilities=None, extra=None):
    base = {"STR": 12, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 10}
    base.update(abilities or {})
    entries = [{"classId": cls, "level": level, "subclassId": sub, "choices": {}}] + (extra or [])
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": base},
         "species": {"id": "human"}, "background": {"id": "acolyte"}, "classes": entries}
    return resolve(d, catalog)


def _ids(res):
    return [r["id"] for r in res["derived"]["classResources"]]


def _entry(res, rid):
    return next((r for r in res["derived"]["classResources"] if r["id"] == rid), None)


def _note(res, rid):
    return ((_entry(res, rid) or {}).get("details") or {}).get("note")


def _mod(res, ability):
    return res["derived"]["abilityModifiers"][ability]


def _pb(res):
    return res["derived"]["proficiencyBonus"]


def _text(catalog, fid):
    rec = catalog.features[fid]
    return " ".join([rec.get("name") or ""] + [x for x in rec["desc"] if isinstance(x, str)])


# (subclass, class, resource id, first level, uses, recharge)   uses: int, "cha" (max(1, CHA modifier)) or None
RESOURCES = [
    ("berserker", "barbarian", "barbarian:frenzy", 3, None, None),
    ("berserker", "barbarian", "barbarian:intimidating-presence", 10, None, None),
    ("life", "cleric", "cleric:disciple-of-life", 1, None, None),
    ("life", "cleric", "cleric:divine-strike-life-domain", 8, 1, "turn"),  # X2
    ("land", "druid", "druid:natural-recovery", 2, None, "long"),
    ("land", "druid", "druid:nature-s-sanctuary", 14, None, None),
    ("champion", "fighter", "fighter:survivor", 18, None, None),
    ("open-hand", "monk", "monk:wholeness-of-body", 6, 1, "long"),
    ("open-hand", "monk", "monk:tranquility", 11, None, None),
    ("devotion", "paladin", "paladin:holy-nimbus", 20, None, None),
    ("draconic", "sorcerer", "sorcerer:elemental-affinity", 6, None, None),
    ("fiend", "warlock", "warlock:dark-one-s-blessing", 1, None, None),
    ("fiend", "warlock", "warlock:dark-one-s-own-luck", 6, 1, "short-or-long"),
    ("fiend", "warlock", "warlock:hurl-through-hell", 14, 1, "long"),
    ("evocation", "wizard", "wizard:empowered-evocation", 10, None, None),
    ("evocation", "wizard", "wizard:overchannel", 14, 1, "long"),
]

# (subclass, class, existing resource id, first level, text the note must hold)
NOTES = [
    ("lore", "bard", "bard:bardic-inspiration", 3, "Cutting Words"),
    ("lore", "bard", "bard:bardic-inspiration", 14, "Peerless Skill"),
    ("life", "cleric", "cleric:channel-divinity", 2, "Preserve Life"),
    ("devotion", "paladin", "paladin:channel-divinity", 3, "Sacred Weapon"),
    ("devotion", "paladin", "paladin:channel-divinity", 3, "Turn the Unholy"),
    ("open-hand", "monk", "monk:ki", 17, "Quivering Palm"),
    ("draconic", "sorcerer", "sorcerer:sorcery-points", 18, "Draconic Presence"),
]


# ---- data pins ---------------------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    """Every W7 entry quotes the SRD record text it was built from (verbatim substring of name + desc), names an SRD
    feature of an SRD subclass, and the level tables that live only in the text are pinned."""
    specs = list(reference_data.SUBCLASS_TAIL_2014) + list(reference_data.SUBCLASS_NOTES_2014)
    assert len(reference_data.SUBCLASS_TAIL_2014) == len(RESOURCES)
    assert len(reference_data.SUBCLASS_NOTES_2014) == len(NOTES)
    for spec in specs:
        assert spec["quotes"], spec["feature"]
        assert spec["subclass"] in SRD_SUBCLASSES
        rec = catalog.features[spec["feature"]]
        assert rec["url"].startswith("/api/2014/features/"), spec["feature"]
        assert rec["class"]["index"] == spec["class"]
        sub = rec.get("subclass")
        assert (sub or {}).get("index") == spec["subclass"], spec["feature"]
        for fid, quote in spec["quotes"]:
            assert quote in _text(catalog, fid), (spec["feature"], fid, quote)
            assert catalog.features[fid]["url"].startswith("/api/2014/features/"), fid
        for extra_id, _t in spec.get("extras") or ():
            assert catalog.features[extra_id]["url"].startswith("/api/2014/features/"), extra_id
    # the level table that lives only in the text
    divine = _text(catalog, "divine-strike")
    assert "an extra 1d8 radiant damage" in divine and "When you reach 14th level, the extra damage increases to 2d8" in divine
    assert reference_data.DIVINE_STRIKE_DICE_2014 == ((8, "1d8"), (14, "2d8"))
    assert catalog.features["divine-strike"]["level"] == 8


@needs_data
def test_record_levels_are_the_documented_ones(catalog):
    for sub, cls, rid, first, _u, _r in RESOURCES:
        spec = next(s for s in reference_data.SUBCLASS_TAIL_2014 if s["subclass"] == sub and s["class"] == cls
                    and f"{cls}:{_slug(s['name'])}" == rid)
        assert catalog.features[spec["feature"]]["level"] == first, rid
    for sub, cls, rid, first, text in NOTES:
        spec = next(s for s in reference_data.SUBCLASS_NOTES_2014 if s["subclass"] == sub and s["name"] == text)
        assert catalog.features[spec["feature"]]["level"] == first, text
    assert catalog.features["blessed-healer"]["level"] == 6


# ---- resources: appear at the record's level for the selected SRD subclass --------------------------------

def _expected_uses(res, uses):
    return max(1, _mod(res, "CHA")) if uses == "cha" else uses


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_appears_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, uses, recharge):
    res = _res(catalog, cls, max(first, 3), sub, ruleset)
    r = _entry(res, rid)
    assert r and r["classId"] == cls and r["source"]["kind"] == "subclass" and r["source"]["id"] == sub
    assert r["uses"] == uses and r["recharge"] == recharge and "unlimited" not in r
    assert r["details"]["note"]
    if first > 3:
        assert _entry(_res(catalog, cls, first - 1, sub, ruleset), rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,uses,recharge", RESOURCES)
def test_resource_needs_its_subclass(catalog, ruleset, sub, cls, rid, first, uses, recharge):
    other = _res(catalog, cls, 20, None, ruleset)
    assert _entry(other, rid) is None


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
@pytest.mark.parametrize("sub,cls,rid,first,text", NOTES)
def test_note_is_attached_at_the_feature_level(catalog, ruleset, sub, cls, rid, first, text):
    res = _res(catalog, cls, max(first, 3), sub, ruleset)
    assert text in (_note(res, rid) or ""), (rid, _note(res, rid))
    if first > 3:
        before = _res(catalog, cls, first - 1, sub, ruleset)
        assert text not in (_note(before, rid) or "")
    assert text not in (_note(_res(catalog, cls, 20, None, ruleset), rid) or "")  # no subclass: no note


# ---- numbers ---------------------------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("cha", [6, 10, 18])
def test_intimidating_presence_dc_uses_charisma(catalog, cha):
    res = _res(catalog, "barbarian", 10, "berserker", abilities={"CHA": cha})
    n = _note(res, "barbarian:intimidating-presence")
    assert f"DC {8 + _pb(res) + _mod(res, 'CHA')}" in n and "24 hours" in n
    assert "exhaustion" in _note(res, "barbarian:frenzy") and "bonus action" in _note(res, "barbarian:frenzy")


@needs_data
def test_cutting_words_and_peerless_skill_spend_a_use(catalog):
    n = _note(_res(catalog, "bard", 14, "lore"), "bard:bardic-inspiration")
    assert "expend a use" in n.split("Cutting Words")[1].split(";")[0]
    assert n.index("Cutting Words") < n.index("Peerless Skill")
    assert "Peerless Skill" not in _note(_res(catalog, "bard", 13, "lore"), "bard:bardic-inspiration")


@needs_data
def test_disciple_of_life_and_blessed_healer(catalog):
    n1 = _note(_res(catalog, "cleric", 3, "life"), "cleric:disciple-of-life")
    assert "2 + the spell's level" in n1 and "Blessed Healer" not in n1
    n6 = _note(_res(catalog, "cleric", 6, "life"), "cleric:disciple-of-life")
    assert "Blessed Healer" in n6 and n6.count("2 + the spell's level") == 2


@needs_data
@pytest.mark.parametrize("level,dice", [(8, "1d8"), (13, "1d8"), (14, "2d8"), (20, "2d8")])
def test_divine_strike_dice_follow_the_text(catalog, level, dice):
    r = _entry(_res(catalog, "cleric", level, "life"), "cleric:divine-strike-life-domain")
    assert r["dice"] == dice and f"extra {dice} radiant" in r["details"]["note"]
    assert "Divine Strike" in resource_line(r) and dice in resource_line(r)


@needs_data
def test_divine_strike_does_not_feed_the_2024_attack_notes(catalog):
    """The 2024 Divine Strike resource (id cleric:divine-strike) drives annotate_attacks; the 2014 one has another id."""
    res = _res(catalog, "cleric", 8, "life")
    assert _entry(res, "cleric:divine-strike") is None
    assert all("Divine Strike" not in note for a in res["derived"]["attacks"] for note in a["notes"])


@needs_data
@pytest.mark.parametrize("level", [8, 10, 18, 20])
def test_preserve_life_pool_is_five_times_the_level(catalog, level):
    n = _note(_res(catalog, "cleric", level, "life"), "cleric:channel-divinity")
    assert f"{5 * level} hit points" in n and "half" in n


@needs_data
@pytest.mark.parametrize("level", [2, 3, 4, 7, 20])
def test_natural_recovery_pool_is_half_the_level_rounded_up(catalog, level):
    r = _entry(_res(catalog, "druid", level, "land" if level >= 2 else None), "druid:natural-recovery")
    assert r["pool"] == (level + 1) // 2 and r["recharge"] == "long" and r["uses"] is None
    assert "6th level or higher" in r["details"]["note"] and "short rest" in r["details"]["note"]
    assert "пул" in resource_line(r)


@needs_data
@pytest.mark.parametrize("wis", [8, 18])
def test_natures_sanctuary_dc(catalog, wis):
    res = _res(catalog, "druid", 14, "land", abilities={"WIS": wis})
    n = _note(res, "druid:nature-s-sanctuary")
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n and "24 hours" in n


@needs_data
@pytest.mark.parametrize("con", [6, 14, 20])
def test_survivor_is_five_plus_constitution(catalog, con):
    res = _res(catalog, "fighter", 18, "champion", abilities={"CON": con})
    assert f"{5 + _mod(res, 'CON')} hit points" in _note(res, "fighter:survivor")


@needs_data
@pytest.mark.parametrize("level", [6, 11, 20])
def test_wholeness_of_body_heals_three_times_the_level(catalog, level):
    n = _note(_res(catalog, "monk", level, "open-hand"), "monk:wholeness-of-body")
    assert f"{3 * level} hit points" in n


@needs_data
@pytest.mark.parametrize("wis", [8, 18])
def test_tranquility_dc(catalog, wis):
    res = _res(catalog, "monk", 11, "open-hand", abilities={"WIS": wis})
    n = _note(res, "monk:tranquility")
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n and "sanctuary" in n


@needs_data
def test_quivering_palm_note_on_ki(catalog):
    res = _res(catalog, "monk", 17, "open-hand")
    n = _note(res, "monk:ki")
    assert "Quivering Palm" in n and "3 ki points" in n and "17 days" in n and "10d10 necrotic" in n
    assert f"DC {8 + _pb(res) + _mod(res, 'WIS')}" in n
    assert n.startswith("Flurry of Blows")  # the W6 Ki notes come first


@needs_data
@pytest.mark.parametrize("cha", [6, 18])
def test_sacred_weapon_bonus_is_charisma_minimum_one(catalog, cha):
    res = _res(catalog, "paladin", 3, "devotion", abilities={"CHA": cha})
    n = _note(res, "paladin:channel-divinity")
    assert f"+{max(1, _mod(res, 'CHA'))}" in n.split("Sacred Weapon")[1] and "Turn the Unholy" in n
    assert n.startswith("Channel Divinity effects")  # the W6 Paladin note first


@needs_data
def test_holy_nimbus_has_no_invented_rest_rule(catalog):
    r = _entry(_res(catalog, "paladin", 20, "devotion"), "paladin:holy-nimbus")
    assert r["uses"] is None and r["recharge"] is None
    assert "10 radiant damage" in r["details"]["note"] and "30-foot radius" in r["details"]["note"]


@needs_data
@pytest.mark.parametrize("cha", [6, 18])
def test_elemental_affinity_adds_the_charisma_modifier(catalog, cha):
    res = _res(catalog, "sorcerer", 6, "draconic", abilities={"CHA": cha})
    assert f"{_mod(res, 'CHA'):+d}" in _note(res, "sorcerer:elemental-affinity")
    assert "1 sorcery point" in _note(res, "sorcerer:elemental-affinity")


@needs_data
def test_draconic_presence_costs_five_sorcery_points(catalog):
    n = _note(_res(catalog, "sorcerer", 18, "draconic"), "sorcerer:sorcery-points")
    assert "5 sorcery points" in n and "60 feet" in n


@needs_data
@pytest.mark.parametrize("level,cha", [(1, 6), (3, 18), (14, 10), (20, 18)])
def test_dark_ones_blessing_temporary_hit_points(catalog, level, cha):
    res = _res(catalog, "warlock", level, "fiend", abilities={"CHA": cha})
    assert f"{max(1, _mod(res, 'CHA') + level)} temporary hit points" in _note(res, "warlock:dark-one-s-blessing")


@needs_data
def test_dark_ones_own_luck_and_hurl_through_hell(catalog):
    r = _entry(_res(catalog, "warlock", 6, "fiend"), "warlock:dark-one-s-own-luck")
    assert r["die"] == "d10" and "ability check or saving throw" in r["details"]["note"]
    n = _note(_res(catalog, "warlock", 14, "fiend"), "warlock:hurl-through-hell")
    assert "10d10 psychic" in n and "fiend" in n


@needs_data
@pytest.mark.parametrize("int_", [8, 20])
def test_empowered_evocation_adds_intelligence(catalog, int_):
    res = _res(catalog, "wizard", 10, "evocation", abilities={"INT": int_})
    assert f"{_mod(res, 'INT'):+d}" in _note(res, "wizard:empowered-evocation")


@needs_data
def test_overchannel_note(catalog):
    n = _note(_res(catalog, "wizard", 14, "evocation"), "wizard:overchannel")
    assert "maximum damage" in n and "2d12 necrotic" in n and "1d12" in n and "first use" in n


# ---- gates -----------------------------------------------------------------------------------------------------

@needs_data
def test_2024_output_is_independent_of_the_2014_tables(catalog, monkeypatch):
    """Under ruleset 2024 the 2014 subclass tables are never read, even for a held SRD subclass."""
    def snapshot():
        return {(sub, cls): copy.deepcopy(_res(catalog, cls, 20, sub, "2024")["derived"]["classResources"])
                for sub, cls in {(r[0], r[1]) for r in RESOURCES} | {(n[0], n[1]) for n in NOTES}}
    before = snapshot()
    monkeypatch.setattr(reference_data, "SUBCLASS_TAIL_2014", ())
    monkeypatch.setattr(reference_data, "SUBCLASS_NOTES_2014", ())
    assert snapshot() == before
    assert _entry(_res(catalog, "warlock", 20, "fiend", "2014"), "warlock:hurl-through-hell") is None  # 2014 reads them


@needs_data
def test_2024_twin_subclasses_and_book_subclasses_get_nothing(catalog):
    """XPHB twins (life-xphb) and book subclasses (totem-warrior-phb) are not SRD ids: no W7 entry (slice W8)."""
    new = {r[2] for r in RESOURCES}
    for cls, sub in (("cleric", "life-xphb"), ("barbarian", "totem-warrior-phb"), ("monk", "four-elements-phb"),
                     ("paladin", "ancients-phb"), ("warlock", "great-old-one-phb")):
        res = _res(catalog, cls, 20, sub, "mixed")
        assert not set(_ids(res)) & new, (sub, set(_ids(res)) & new)
        for n in NOTES:
            if n[1] == cls:
                assert n[4] not in (_note(res, n[2]) or ""), (sub, n[4])


@needs_data
def test_hunter_and_thief_have_no_w7_entries(catalog):
    """Hunter's Prey / Defensive Tactics / Multiattack / Superior Hunter's Defense are picks without a use limit, and the
    Thief's features carry no use count or class number: nothing is added (see the ARCHITECTURE scan)."""
    for cls, sub in (("ranger", "hunter"), ("rogue", "thief")):
        res = _res(catalog, cls, 20, sub)
        assert all(r["source"]["kind"] != "subclass" for r in res["derived"]["classResources"])


@needs_data
def test_multiclass_keeps_each_subclass_with_its_class(catalog):
    res = _res(catalog, "warlock", 6, "fiend", extra=[{"classId": "cleric", "level": 3, "subclassId": "life", "choices": {}}])
    ids = _ids(res)
    assert "warlock:dark-one-s-own-luck" in ids and "cleric:disciple-of-life" in ids
    assert ids.index("warlock:dark-one-s-blessing") < ids.index("cleric:disciple-of-life")


@needs_data
@pytest.mark.parametrize("ruleset", RULESETS_2014)
def test_resolve_stays_fast(catalog, ruleset):
    for cls, sub in (("fighter", "champion"), ("wizard", "evocation"), ("bard", "lore"), ("cleric", "life"),
                     ("warlock", "fiend")):
        _res(catalog, cls, 20, sub, ruleset)  # warm
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, cls, 20, sub, ruleset)
        assert (time.perf_counter() - t) / 10 < 0.05, (ruleset, cls)
