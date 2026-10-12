"""FE3: feat notes and `derived.featResources` (docs/superpowers/plans/2026-10-11-feat-effects.md).

Each feat follows its own edition's text under every ruleset. Governing sentences (catalog text, tags stripped;
the full set is `catalog.feat_effects_data.FEAT_EFFECT_QUOTES`, pinned against the catalog by
`test_quote_matches_catalog_text`):

  Lucky (PHB)       "You have 3 luck points."  ...  "You regain your expended luck points when you finish a long rest."
  Lucky (XPHB)      "You have a number of Luck Points equal to your Proficiency Bonus"  (regained on a Long Rest)
  Inspiring Leader  (XPHB) "Temporary Hit Points equal to your character level plus the modifier of the ability you
                    increased with this feat"; (PHB) "temporary hit points equal to your level + your Charisma modifier".
  Durable (PHB)     "the minimum number of hit points you regain from the roll equals twice your Constitution
                    modifier (minimum of 2)".
  Heavy Armor Master (XPHB) "is reduced by an amount equal to your Proficiency Bonus"; (PHB) "reduced by 3".
  Shield Master (XPHB) "(8 plus your Strength modifier and Proficiency Bonus)".
  Mage Slayer (XPHB) Guarded Mind: "you can't use it again until you finish a Short or Long Rest".
  Second Chance / Fade Away / Orcish Fury (XGE): one use until a short or long rest (Second Chance: also until you
                    roll initiative).

Matrix: which note / resource a feat has (data) x number (Proficiency Bonus, level, ability modifier, pending
ability) x source of the feat (background, ASI, hidden by ruleset) x edition x output surface (sheet.feats[].notes,
derived.featResources, YAML, Markdown, PDF) x no-feat identity x empty catalog x timing.
"""
import copy
import io
import re
import time

import pytest
import yaml
from pypdf import PdfReader

import export_fields
from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_effects as fe
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FE3_DATA_ONLY = ("heavily-armored-phb", "heavily-armored-xphb", "lightly-armored-phb", "lightly-armored-xphb",
                 "moderately-armored-phb", "moderately-armored-xphb", "martial-weapon-training-xphb",
                 "resilient-phb", "resilient-xphb", "skilled-phb", "skilled-xphb", "magic-initiate-phb",
                 "magic-initiate-xphb", "fey-touched-xphb", "shadow-touched-xphb")
FE3_WITH_TEXT = tuple(i for i, e in fed.FEAT_EFFECTS.items() if e.get("notes") or e.get("resources"))
FE4_ENTRIES = ("dragon-hide-xge", "medium-armor-master-phb", "medium-armor-master-xphb", "dual-wielder-phb",
               "revenant-blade-erlw", "observant-phb", "keenness-of-the-stone-giant-bgg")  # later slice (tests/test_feat_defense.py)
FE7_ENTRIES = ("dragonscarred-frhof", "boon-of-energy-resistance-xphb", "portal-jumper-au", "spell-resistant-au",
               "scion-of-the-outer-planes-sato", "elemental-adept-phb", "elemental-adept-xphb",
               "strike-of-the-giants-bgg")  # later slice (tests/test_feat_resist_choices.py)
FE8_ENTRIES = ("weapon-master-phb", "weapon-master-xphb")  # later slice (tests/test_feat_weapon_picks.py)
FE9_ENTRIES = ("fighting-initiate-tce", "eldritch-adept-tce", "martial-adept-phb", "metamagic-adept-tce")  # tests/test_feat_option_picks.py
FE3_WITH_TEXT = tuple(i for i in FE3_WITH_TEXT if i in fed.FEAT_EFFECT_QUOTES and i not in
                      ("alert-phb",) + FE4_ENTRIES + FE7_ENTRIES + FE8_ENTRIES + FE9_ENTRIES)


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, feats=(), ruleset="mixed", background="acolyte", species="human", base=None,
         picks=None):
    """classes: (classId, level). feats: ASI picks put on the first class's ASI slots (4, 8, ...).
    picks: extra {choice id: [selected]} for the first class."""
    entries = []
    for n, (cls, level) in enumerate(classes):
        chosen = {}
        if n == 0:
            slots = [lv for lv in (4, 8, 12, 16, 19) if lv <= level]
            for slot, feat in zip(slots, feats):
                chosen[f"class:{cls}:{slot}:asi"] = [f"feat:{feat}"]
            chosen.update(picks or {})
        entries.append({"classId": cls, "level": level, "choices": chosen})
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": entries,
         "background": {"id": background, "choices": {}}, "species": {"id": species, "choices": {}},
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {}, "preferences": {}}
    return resolve(d, catalog)


def _feat(res, index):
    return next(f for f in res["sheet"]["feats"] if f["id"] == index)


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
    text = " ".join(out)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, text)


# ---------------------------------------------------------------- data guards


@pytest.mark.parametrize("index", FE3_WITH_TEXT)
def test_quote_matches_catalog_text(catalog, index):
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    text = _plain(catalog.feats[index]["entries"])
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in text, (index, quote)


def test_every_entry_with_notes_or_resources_has_a_quote():
    for index, entry in fed.FEAT_EFFECTS.items():
        if entry.get("notes") or entry.get("resources"):
            assert index in fed.FEAT_EFFECT_QUOTES, index


def test_the_fe3_entries_are_classified_and_the_ratchet_counts_them():
    assert len(FE3_WITH_TEXT) == 44
    for index in FE3_WITH_TEXT + FE3_DATA_ONLY:
        assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    for index in FE3_DATA_ONLY:
        assert fed.FEAT_EFFECTS[index] == {"data_only": True}


def test_resource_entries_use_only_the_implemented_vocabulary():
    seen = 0
    for index, entry in fed.FEAT_EFFECTS.items():
        for res in entry.get("resources", []):
            seen += 1
            assert set(res) <= {"name", "uses", "recharge", "note", "die", "dc"}, index
            assert res["uses"] == "pb" or isinstance(res["uses"], int), index
            assert res["recharge"] in ("long", "short", "short-or-long"), index
    assert seen == 12  # 7 from FE3, 3 from FE7, Martial Adept / Metamagic Adept from FE9


def test_lucky_follows_its_own_edition():
    assert fed.FEAT_EFFECTS["lucky-phb"]["resources"][0]["uses"] == 3
    assert fed.FEAT_EFFECTS["lucky-xphb"]["resources"][0]["uses"] == "pb"


NUMBERS = fe.numbers_for({a: 1 for a in ABS}, {a: 12 for a in ABS}, 2, 5)


def test_every_note_template_renders_with_and_without_a_chosen_ability(catalog):
    for index, entry in fed.FEAT_EFFECTS.items():
        for text in entry.get("notes", []):
            for inc in ("WIS", None):
                inst = {"increased": inc}
                out = fe.render(text, fe._env(inst, NUMBERS))
                assert "{" not in out and out, (index, text)


def test_a_note_that_needs_the_increased_ability_belongs_to_a_feat_that_increases_one(catalog):
    for index, entry in fed.FEAT_EFFECTS.items():
        if any("inc_mod" in t for t in entry.get("notes", [])):
            feat = catalog.feats[index]
            assert feat.get("ability_bonuses") or feat.get("ability_bonus_options"), index


@pytest.mark.parametrize("index", FE3_DATA_ONLY)
def test_data_only_feats_really_carry_their_effect_in_catalog_fields(catalog, index):
    feat = catalog.feats[index]
    carried = ("proficiencies", "proficiency_choices", "saving_throw_choices", "innate_spells", "spell_choices")
    assert any(feat.get(k) for k in carried), index


# ---------------------------------------------------------------- the pure engine


def test_render_arithmetic_sum_and_pending():
    env = fe._env({"increased": "WIS"}, fe.numbers_for({"WIS": 3, "CON": -1}, {"INT": 14}, 3, 8))
    assert fe.render("{level}/{pb}/{wis_mod}", env) == "8/3/3"
    assert fe.render("{sum:level,inc_mod}", env) == "8 + 3 = 11"
    assert fe.render("{8+wis_mod+pb}", env) == "14"
    assert fe.render("{max(2,2*con_mod)}", env) == "2"
    assert fe.render("{int_score+pb}", env) == "17"
    pending = fe._env({"increased": None}, fe.numbers_for({"WIS": 3}, {}, 3, 8))
    assert fe.render("{sum:level,inc_mod}", pending) == fe.CHOOSE_ABILITY
    assert fe.render("DC {8+inc_mod+pb}", pending) == f"DC {fe.CHOOSE_ABILITY}"


def test_render_rejects_unknown_names_and_arbitrary_code():
    env = fe._env({"increased": None}, NUMBERS)
    with pytest.raises(KeyError):
        fe.render("{nothing}", env)
    with pytest.raises(ValueError):
        fe.render("{__import__('os')}", env)


def test_increased_ability_fixed_chosen_and_missing():
    fixed = {"ability_bonuses": [{"ability_score": {"index": "cha"}, "bonus": 1}]}
    assert fe.increased_ability(fixed, [], "p") == "CHA"
    cards = [{"id": "p:ability-bonus", "selected": ["wis"]}]
    assert fe.increased_ability({"ability_bonuses": []}, cards, "p") == "WIS"
    assert fe.increased_ability({"ability_bonuses": []}, [{"id": "p:ability-bonus", "selected": []}], "p") is None
    assert fe.increased_ability({}, None, "p") is None


def test_resources_shape_and_instance_scoped_ids():
    feat = {"index": "lucky-xphb", "name": "Lucky"}
    got = fe.resources(fe.instances([feat], fed.FEAT_EFFECTS), NUMBERS)
    assert got == [{"id": "feat:lucky-xphb:luck-points", "featId": "lucky-xphb",
                    "source": {"kind": "feat", "id": "lucky-xphb", "label": "Lucky"},
                    "name": "Luck Points", "uses": 2, "recharge": "long"}]
    second = fe.resources(fe.instances([{**feat, "_asi_cid": "c", "_asi_origin": "class:fighter:4:asi:feat:x"}],
                                       fed.FEAT_EFFECTS), NUMBERS)
    assert second[0]["id"] == "class:fighter:4:asi:feat:x:luck-points"


# ---------------------------------------------------------------- resolve: resources


def test_lucky_xphb_from_merchant_follows_the_proficiency_bonus(catalog):
    r = _res(catalog, [("rogue", 5)], ruleset="2024", background="merchant-xphb")
    [lucky] = r["derived"]["featResources"]
    assert (lucky["name"], lucky["uses"], lucky["recharge"], lucky["featId"]) == ("Luck Points", 3, "long", "lucky-xphb")
    assert lucky["source"] == {"kind": "feat", "id": "lucky-xphb", "label": "Lucky"} and "classId" not in lucky
    low = _res(catalog, [("rogue", 1)], ruleset="2024", background="merchant-xphb")
    assert low["derived"]["featResources"][0]["uses"] == 2


def test_lucky_xphb_from_the_wayfarer_background(catalog):
    r = _res(catalog, [("fighter", 1)], ruleset="2024", background="wayfarer-xphb")
    assert [x["featId"] for x in r["derived"]["featResources"]] == ["lucky-xphb"]


def test_lucky_phb_is_three_points_whatever_the_level(catalog):
    r = _res(catalog, [("fighter", 4)], ["lucky-phb"])
    assert [(x["uses"], x["recharge"]) for x in r["derived"]["featResources"]] == [(3, "long")]
    r = _res(catalog, [("fighter", 12)], ["lucky-phb"])
    assert r["derived"]["featResources"][0]["uses"] == 3


def test_lucky_xphb_kept_under_ruleset_2014_is_still_a_resource(catalog):
    r = _res(catalog, [("fighter", 4)], ["lucky-xphb"], ruleset="2014")
    assert r["derived"]["featResources"][0]["uses"] == 2


def test_mage_slayer_xphb_guarded_mind(catalog):
    r = _res(catalog, [("fighter", 4)], ["mage-slayer-xphb"], ruleset="2024")
    [res] = r["derived"]["featResources"]
    assert (res["name"], res["uses"], res["recharge"]) == ("Guarded Mind", 1, "short-or-long")


@pytest.mark.parametrize("feat,species,name,note", [
    ("second-chance-xge", "halfling", "Second Chance", "also regained when you roll initiative"),
    ("fade-away-xge", "gnome", "Fade Away", None),
    ("orcish-fury-xge", "half-orc", "Orcish Fury", None),
])
def test_xge_racial_feat_resources(catalog, feat, species, name, note):
    r = _res(catalog, [("fighter", 4)], [feat], species=species)
    [res] = r["derived"]["featResources"]
    assert (res["name"], res["uses"], res["recharge"]) == (name, 1, "short-or-long")
    assert (res.get("details") or {}).get("note") == note


def test_ritual_caster_xphb_quick_ritual(catalog):
    r = _res(catalog, [("fighter", 4)], ["ritual-caster-xphb"], ruleset="2024", base={"INT": 13})
    assert [(x["name"], x["uses"], x["recharge"]) for x in r["derived"]["featResources"]] == [("Quick Ritual", 1, "long")]


def test_two_feats_give_two_resources(catalog):
    r = _res(catalog, [("fighter", 8)], ["lucky-phb", "mage-slayer-xphb"])
    assert sorted(x["featId"] for x in r["derived"]["featResources"]) == ["lucky-phb", "mage-slayer-xphb"]


def test_a_featless_character_has_no_feat_resources_or_notes(catalog):
    r = _res(catalog, [("fighter", 4)])
    assert r["derived"]["featResources"] == []
    assert all("notes" not in f for f in r["sheet"]["feats"])


# ---------------------------------------------------------------- resolve: notes


def _wis_pick(level_slot=4):
    return {f"class:fighter:{level_slot}:asi:feat:inspiring-leader-xphb:ability-bonus": ["wis"]}


def test_inspiring_leader_xphb_adds_the_level_and_the_increased_modifier(catalog):
    # WIS base 15 + 1 (the feat) = 16 -> +3; Fighter 8 (2024: the species gives no ability bonus).
    r = _res(catalog, [("fighter", 8)], ["inspiring-leader-xphb"], ruleset="2024", base={"WIS": 15}, picks=_wis_pick())
    assert r["sheet"]["abilities"]["WIS"] == 16
    assert any("8 + 3 = 11 Temporary Hit Points" in n for n in _feat(r, "inspiring-leader-xphb")["notes"])


def test_inspiring_leader_xphb_uses_the_chosen_ability_not_wisdom(catalog):
    picks = {"class:fighter:4:asi:feat:inspiring-leader-xphb:ability-bonus": ["cha"]}
    r = _res(catalog, [("fighter", 8)], ["inspiring-leader-xphb"], ruleset="2024",
             base={"WIS": 15, "CHA": 9}, picks=picks)  # CHA 9 + 1 (the feat) = 10 -> +0
    assert any("8 + 0 = 8 Temporary Hit Points" in n for n in _feat(r, "inspiring-leader-xphb")["notes"])


def test_inspiring_leader_xphb_with_the_ability_still_to_choose(catalog):
    r = _res(catalog, [("fighter", 8)], ["inspiring-leader-xphb"], ruleset="2024", base={"WIS": 14})
    [note] = _feat(r, "inspiring-leader-xphb")["notes"]
    assert fe.CHOOSE_ABILITY in note and "Temporary Hit Points" in note


def test_inspiring_leader_phb_uses_charisma(catalog):
    r = _res(catalog, [("fighter", 8)], ["inspiring-leader-phb"], base={"CHA": 15})  # 15 + 1 Human = 16 -> +3
    assert any("8 + 3 = 11 Temporary Hit Points" in n for n in _feat(r, "inspiring-leader-phb")["notes"])


def test_durable_phb_minimum_is_twice_the_constitution_modifier_at_least_two(catalog):
    high = _res(catalog, [("fighter", 4)], ["durable-phb"], base={"CON": 16})  # 16 + 1 + 1 (feat) = 18 -> +4
    assert "at least 8 hit points" in _feat(high, "durable-phb")["notes"][0]
    low = _res(catalog, [("fighter", 4)], ["durable-phb"], base={"CON": 8})  # 8 + 1 + 1 = 10 -> +0
    assert "at least 2 hit points" in _feat(low, "durable-phb")["notes"][0]


def test_heavy_armor_master_follows_its_own_edition(catalog):
    old = _res(catalog, [("fighter", 4)], ["heavy-armor-master-phb"])
    assert "reduced by 3" in _feat(old, "heavy-armor-master-phb")["notes"][0]
    new = _res(catalog, [("fighter", 8)], ["heavy-armor-master-xphb"], ruleset="2024")  # PB 3
    assert "reduced by 3" in _feat(new, "heavy-armor-master-xphb")["notes"][0]
    high = _res(catalog, [("fighter", 12)], ["heavy-armor-master-xphb"], ruleset="2024")  # PB 4
    assert "reduced by 4" in _feat(high, "heavy-armor-master-xphb")["notes"][0]


def test_shield_master_xphb_dc_uses_strength_and_proficiency(catalog):
    # STR 15 + 1 Human (+1 feat when picked) -> the feat has no fixed bonus here, so STR 16 -> +3; PB 2 at level 4.
    r = _res(catalog, [("fighter", 4)], ["shield-master-xphb"], ruleset="2024", base={"STR": 15})
    mod = r["derived"]["abilityModifiers"]["STR"]
    assert f"DC {8 + mod + 2}" in _feat(r, "shield-master-xphb")["notes"][0]


def test_chef_and_musician_scale_with_the_proficiency_bonus(catalog):
    r = _res(catalog, [("fighter", 4)], ["chef-xphb"], ruleset="2024")  # PB 2
    chef = " ".join(_feat(r, "chef-xphb")["notes"])
    assert "food for 6 creatures" in chef and "2 treats" in chef and "gives 2 Temporary Hit Points" in chef
    r = _res(catalog, [("fighter", 8)], ["chef-xphb"], ruleset="2024")  # PB 3
    assert "food for 7 creatures" in " ".join(_feat(r, "chef-xphb")["notes"])
    r = _res(catalog, [("fighter", 8)], ["musician-xphb"], ruleset="2024")
    assert "up to 3 allies" in _feat(r, "musician-xphb")["notes"][0]


def test_defensive_duelist_editions(catalog):
    old = _res(catalog, [("fighter", 4)], ["defensive-duelist-phb"], base={"DEX": 13})
    assert "+2 AC" in _feat(old, "defensive-duelist-phb")["notes"][0]
    new = _res(catalog, [("fighter", 8)], ["defensive-duelist-xphb"], ruleset="2024", base={"DEX": 13})
    assert "+3 AC" in _feat(new, "defensive-duelist-xphb")["notes"][0]


def test_actor_xphb_mimicry_dc(catalog):
    r = _res(catalog, [("fighter", 4)], ["actor-xphb"], ruleset="2024", base={"CHA": 13})
    mod = r["derived"]["abilityModifiers"]["CHA"]
    assert f"DC {8 + mod + 2}" in " ".join(_feat(r, "actor-xphb")["notes"])


def test_telekinetic_shove_dc_follows_the_increased_ability(catalog):
    picks = {"class:fighter:4:asi:feat:telekinetic-xphb:ability-bonus": ["int"]}
    r = _res(catalog, [("fighter", 4)], ["telekinetic-xphb"], ruleset="2024", base={"INT": 14}, picks=picks)
    mod = r["derived"]["abilityModifiers"]["INT"]
    assert f"DC {8 + mod + 2}" in _feat(r, "telekinetic-xphb")["notes"][0]


def test_feat_from_a_background_carries_its_notes(catalog):
    r = _res(catalog, [("fighter", 5)], ruleset="2024", background="entertainer-xphb")  # grants Musician
    assert "up to 3 allies" in _feat(r, "musician-xphb")["notes"][0]
    r = _res(catalog, [("fighter", 5)], ruleset="2024", background="artisan-xphb")  # grants Crafter
    assert "20 percent" in _feat(r, "crafter-xphb")["notes"][0]


def test_notes_of_a_feat_kept_but_hidden_by_the_ruleset_remain(catalog):
    r = _res(catalog, [("fighter", 4)], ["war-caster-xphb"], ruleset="2014")
    assert "Reactive Spell" in " ".join(_feat(r, "war-caster-xphb")["notes"])


def test_skulker_xphb_blindsight_is_a_sheet_sense_and_not_double_counted(catalog):
    r = _res(catalog, [("fighter", 4)], ["skulker-xphb"], ruleset="2024", base={"DEX": 13})
    assert r["sheet"]["senses"]["blindsight"] == 10


def test_data_only_feats_add_no_notes_and_still_work(catalog):
    r = _res(catalog, [("fighter", 4)], ["heavily-armored-xphb"], ruleset="2024")
    assert "heavy-armor" in r["sheet"]["proficiencies"]["armor"] and "notes" not in _feat(r, "heavily-armored-xphb")
    r = _res(catalog, [("fighter", 4)], ["resilient-xphb"], ruleset="2024",
             picks={"class:fighter:4:asi:feat:resilient-xphb:save-choice-0": ["wis"]})
    assert "WIS" in r["sheet"]["proficiencies"]["savingThrows"]


# ---------------------------------------------------------------- exports


def _lucky_res(catalog):
    return _res(catalog, [("fighter", 8)], ["inspiring-leader-phb", "lucky-phb"], base={"CHA": 15})


def test_blocks_carry_the_resource_line_and_the_notes(catalog):
    res = _lucky_res(catalog)
    blocks = export_fields.extra_blocks(res)
    assert ("h2", "Ресурси от таланти") in blocks
    line = export_fields.resource_line(res["derived"]["featResources"][0])
    assert line == "Luck Points: 3 (дълга почивка)" and ("bullet", line) in blocks
    bullet = next(t for kind, t in blocks if kind == "bullet" and t.startswith("Inspiring Leader"))
    assert " — " in bullet and "8 + 3 = 11 Temporary Hit Points" in bullet


def test_yaml_markdown_and_pdf_print_resources_and_notes(catalog):
    res = _lucky_res(catalog)
    doc = yaml.safe_load(to_yaml(res))
    assert doc["featResources"] == res["derived"]["featResources"]
    assert doc["feats"] == res["sheet"]["feats"] and doc["feats"][0]["notes"]
    flat = lambda t: re.sub(r"\s+", " ", t)  # noqa: E731
    pdf = flat("\n".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages))
    md = flat(to_markdown(res))
    for text in ("Ресурси от таланти", "Luck Points: 3 (дълга почивка)", "8 + 3 = 11 Temporary Hit Points"):
        assert text in md, text
        assert text in pdf, text


def test_a_featless_export_has_no_feat_resource_section(catalog):
    res = _res(catalog, [("fighter", 4)])
    assert ("h2", "Ресурси от таланти") not in export_fields.extra_blocks(res)
    assert yaml.safe_load(to_yaml(res))["featResources"] == []


# ---------------------------------------------------------------- degrade and speed


def test_empty_catalog_is_a_no_op():
    bare = copy.copy(load())
    bare.feats = {}
    r = _res(bare, [("fighter", 4)], ["lucky-phb"])
    assert r["derived"]["featResources"] == []
    assert all("notes" not in f for f in r["sheet"]["feats"])


def test_resolve_stays_fast_with_note_and_resource_feats(catalog):
    cases = (([("fighter", 20)], "mixed", "acolyte", ["lucky-phb", "inspiring-leader-phb", "war-caster-phb", "durable-phb"]),
             ([("fighter", 20)], "2024", "merchant-xphb", ["chef-xphb", "mage-slayer-xphb", "shield-master-xphb"]),
             ([("wizard", 20)], "mixed", "acolyte", ["lucky-phb", "actor-phb", "keen-mind-phb"]))
    for classes, ruleset, bg, feats in cases:
        _res(catalog, classes, feats, ruleset=ruleset, background=bg)
        t = time.perf_counter()
        for _ in range(10):
            _res(catalog, classes, feats, ruleset=ruleset, background=bg)
        assert (time.perf_counter() - t) / 10 < 0.05
