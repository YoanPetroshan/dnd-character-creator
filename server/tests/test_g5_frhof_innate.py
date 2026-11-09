"""G5: (a) the FRHoF Banneret / College of the Moon / Scion of the Three `additionalSpells` blocks in the RP18 subclass
innate table; (b) Magic Connoisseur's spell list follows the chosen Magic Initiate list; (c) Rune Shaper (the Rune Spells
table is a literal list) and Boon of Magic School Mastery (no literal list: stays as it was).

Governing data (vendored 5etools, quoted verbatim; FRHoF is ruleset "2024" like the XPHB books, source FRHoF):
  Banneret (Fighter 3)  additionalSpells [{innate: {"3": {ritual: ["comprehend languages|xphb"]}}, ability: "cha"}];
                        Knightly Envoy: "Comprehension. You can cast the Comprehend Languages spell but only as a Ritual.
                        Charisma is your spellcasting ability for it."
  Moon (Bard 3 / 6)     [{innate: {"3": [{choose: "level=0|class=druid", count: 1}]},
                          prepared: {"6": {daily: {"1e": ["moonbeam|xphb"]}}}}];
                        Blessing of Moonlight: "You always have the Moonbeam spell prepared."
                        Primal Lore: "You learn Druidic and one cantrip from the Druid spell list." = a pick by a rule
  Scion (Rogue 3)       [{innate: {"3": [{choose: {from: [minor illusion, blade ward, chill touch], count: 1}}]}, ability:
                        "int"}]; Dread Allegiance: "When you finish a Long Rest, you can change your choice." = a one-rest
                        choice tied to a resistance (Q17)
Rule matrix:
  Banneret 3+      innate row Comprehend Languages "ritual only", CHA, source Banneret, level 3; none at Fighter 2
  Moon 6+          Moonbeam in sheet.spells[bard].alwaysPrepared (reason: the subclass), no innate row; none at Bard 5
  Moon / Scion     the cantrip picks are NOT modelled (a rule / a one-rest choice): no row, no card, no invented list
  gates            ruleset "2024" only (mixed / 2014 byte-identical), selected subclass, class level, FRHoF feature record,
                   the converter key; an SRD-only catalog or a catalog without the key gives nothing
  reachability     Banneret is offered under "2024" only (it has a 2014 twin); Moon and Scion are also offered under
                   "mixed" but the table is read for "2024" only (decision D2 of RP18)
(b) Magic Connoisseur: "Choose a level 1 and a level 2 spell from the same list you selected for the Magic Initiate feat's
cantrips." -> no `:spell-variant` card of its own while Magic Initiate is held; its two spell cards list the base feat's
class; none until the base picks a list; without the base feat it keeps its own card.
(c) Rune Shaper: "You know a number of runes equal to half your proficiency bonus (rounded down), chosen from the Rune Spells
table." -> one fixed grant (Comprehend Languages, 1/day) and one pick of N (1 up to level 8, 2 at 9-16, 3 from 17) from the
13 table spells, 1/day each, ability Intelligence / Wisdom / Charisma chosen with the feat. Boon of Magic School Mastery
has filters ("a level 1 spell from the chosen school that appears on your class's spell list"), no list: unchanged."""
import copy
import json

import pytest

from catalog import feat_effects_data, reference_data
from catalog.loader import load
from catalog.official import paths
from catalog.official_source import has_official, has_official_classes
from engine.resolve import _subclass_visible, resolve
from markdown_export import to_markdown
from perf_helpers import assert_fast, measure

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

BANNERET = "banneret-frhof-3-knightly-envoy"
MOON = "moon-frhof-6-blessing-of-moonlight"
RUNES = ["fog-cloud", "inflict-wounds", "chromatic-orb", "disguise-self", "burning-hands", "speak-with-animals",
         "armor-of-agathys", "goodberry", "longstrider", "command", "entangle", "sanctuary", "thunderwave"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls_id, level, sub=None, ruleset="2024", bg="sage-xphb", bg_choices=None, class_choices=None, cha=14):
    entry = {"classId": cls_id, "level": level, "choices": dict(class_choices or {})}
    if sub:
        entry["subclassId"] = sub
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 12, "INT": 12, "WIS": 12, "CHA": cha}},
        "species": {"id": "human-xphb"},
        "background": {"id": bg, "choices": dict(bg_choices or {})},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [entry],
    }


def _raw_subclass(cls_file, name):
    d = json.load(open(paths.class_dir() / f"class-{cls_file}.json", encoding="utf-8"))
    return next(s for s in d["subclass"] if s["name"] == name and s["source"] == "FRHoF")


# ---- (a) data -------------------------------------------------------------------------------------------------------

@needs_data
def test_the_vendored_blocks_are_what_the_table_assumes():
    ban = _raw_subclass("fighter", "Banneret")
    assert ban["edition"] == "one" and ban["classSource"] == "XPHB"
    assert ban["additionalSpells"] == [{"innate": {"3": {"ritual": ["comprehend languages|xphb"]}}, "ability": "cha"}]
    moon = _raw_subclass("bard", "College of the Moon")
    assert moon["edition"] == "one"
    assert moon["additionalSpells"] == [{"innate": {"3": [{"choose": "level=0|class=druid", "count": 1}]},
                                         "prepared": {"6": {"daily": {"1e": ["moonbeam|xphb"]}}}}]
    scion = _raw_subclass("rogue", "Scion of the Three")
    assert scion["edition"] == "one"
    assert scion["additionalSpells"] == [{"innate": {"3": [{"choose": {
        "from": ["minor illusion|xphb#c", "blade ward|xphb#c", "chill touch|xphb#c"], "count": 1}}]}, "ability": "int"}]


@needs_data
def test_quotes_and_pins(catalog):
    for fid in (BANNERET, MOON):
        spec = reference_data.SUBCLASS_INNATE_2024[fid]
        rec = catalog.features[fid]
        text = "\n".join(rec["desc"])
        assert rec["source"] == "FRHoF" and catalog.subclasses[spec["subclass"]]["source"] == "FRHoF"
        assert catalog.subclasses[spec["subclass"]]["ruleset"] == "2024"
        assert (rec["class"] or {}).get("index") == spec["class"] and (rec["subclass"] or {}).get("index") == spec["subclass"]
        for q in spec["quotes"]:
            assert q in text, fid
    ban = reference_data.SUBCLASS_INNATE_2024[BANNERET]
    assert ban["spells"] == ("comprehend-languages",) and ban["uses"] == "ritual only" and "only as a Ritual" in ban["quotes"][0]
    assert ban["ability"] == "CHA" and "Charisma is your spellcasting ability" in ban["quotes"][0]
    moon = reference_data.SUBCLASS_INNATE_2024[MOON]
    assert moon["mode"] == "prepared" and moon["spells"] == ("moonbeam",)


@needs_data
def test_converter_keys(catalog):
    assert catalog.subclasses["banneret-frhof"]["innate_spells"] == [
        {"level": 3, "spell": "comprehend-languages-xphb", "kind": "ritual", "uses": None, "ability": "CHA", "resource": None}]
    assert catalog.subclasses["moon-frhof"]["innate_spells"] == [
        {"level": 6, "spell": "moonbeam-xphb", "kind": "daily", "uses": "1e", "ability": None, "resource": None}]
    # the Scion block holds only a `choose` item: nothing to record, nothing invented
    assert "innate_spells" not in catalog.subclasses["scion-of-the-three-frhof"]
    # the other FRHoF subclasses (prepared lists, Bladesinger without a block) get no key
    for sub in ("knowledge-frhof", "noble-genies-frhof", "winter-walker-frhof", "spellfire-frhof", "bladesinger-frhof"):
        assert "innate_spells" not in catalog.subclasses[sub], sub


@needs_data
def test_reachability(catalog):
    vis = {s: {rs: _subclass_visible(catalog, catalog.subclasses[s], [], rs) for rs in ("mixed", "2014", "2024")}
           for s in ("banneret-frhof", "moon-frhof", "scion-of-the-three-frhof")}
    assert vis["banneret-frhof"] == {"mixed": False, "2014": False, "2024": True}
    for s in ("moon-frhof", "scion-of-the-three-frhof"):
        assert vis[s] == {"mixed": True, "2014": False, "2024": True}


# ---- (a) engine -----------------------------------------------------------------------------------------------------

def _rows(catalog, cls_id, level, sub, **kw):
    return resolve(_draft(cls_id, level, sub, **kw), catalog)["sheet"]["innateSpells"]


@needs_data
@pytest.mark.parametrize("level", [3, 7, 20])
def test_banneret_comprehend_languages(catalog, level):
    rows = [r for r in _rows(catalog, "fighter", level, "banneret-frhof") if r.get("source") == "Banneret"]
    assert len(rows) == 1
    r = rows[0]
    assert (r["spellId"], r["name"], r["uses"], r["ability"], r["level"]) == (
        "comprehend-languages-xphb", "Comprehend Languages", "ritual only", "CHA", 3)
    assert "usesMax" not in r and "recharge" not in r  # a ritual-only line has no count (G6 parser)


@needs_data
def test_banneret_not_below_level_3_or_without_the_subclass(catalog):
    assert not [r for r in _rows(catalog, "fighter", 2, "banneret-frhof") if r.get("source") == "Banneret"]
    assert not [r for r in _rows(catalog, "fighter", 3, "champion-xphb") if r.get("source") == "Banneret"]
    assert not [r for r in _rows(catalog, "fighter", 3, None) if r["spellId"] == "comprehend-languages-xphb"]


@needs_data
def test_moon_moonbeam_is_always_prepared_not_innate(catalog):
    def bard(lvl):
        res = resolve(_draft("bard", lvl, "moon-frhof"), catalog)
        return res, next(e for e in res["sheet"]["spells"] if e["classId"] == "bard")
    res5, e5 = bard(5)
    res6, e6 = bard(6)
    assert "moonbeam-xphb" not in [s["id"] for s in e5["alwaysPrepared"]]
    assert "moonbeam-xphb" in [s["id"] for s in e6["alwaysPrepared"]]
    always = {s["id"]: s for s in e6["alwaysPrepared"]}
    assert "Moon" in always["moonbeam-xphb"].get("reason", "") or "Moon" in str(always["moonbeam-xphb"])
    assert not [r for r in res6["sheet"]["innateSpells"] if r["spellId"] == "moonbeam-xphb"]
    # the Bard's own prepared card cannot take it twice
    card = next(c for c in res6["choices"] if c["id"] == "class:bard:spells-known")
    opt = next((o for o in card["options"] if o["id"] == "moonbeam-xphb"), None)
    assert opt is None or opt.get("disabled")


@needs_data
def test_cantrip_picks_are_not_modelled(catalog):
    """Moon's Primal Lore (a Druid cantrip by a rule) and Scion's Dread Allegiance (a one-rest choice): no row, no card."""
    moon = resolve(_draft("bard", 6, "moon-frhof"), catalog)
    scion = resolve(_draft("rogue", 9, "scion-of-the-three-frhof"), catalog)
    assert not [r for r in moon["sheet"]["innateSpells"] if r.get("source") == "College of the Moon"]
    assert not [r for r in scion["sheet"]["innateSpells"] if r.get("source")]
    for res in (moon, scion):
        assert not [c for c in res["choices"] if "primal-lore" in c["id"] or "dread-allegiance" in c["id"]]
        assert res["problems"] == [] or all("lore" not in str(p).lower() for p in res["problems"])
    assert reference_data.SUBCLASS_INNATE_2024.keys().isdisjoint(
        {"moon-frhof-3-primal-lore", "scion-of-the-three-frhof-3-dread-allegiance"})


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_other_rulesets_get_nothing(catalog, ruleset):
    assert not [r for r in _rows(catalog, "fighter", 10, "banneret-frhof", ruleset=ruleset) if r.get("source") == "Banneret"]
    res = resolve(_draft("bard", 10, "moon-frhof", ruleset=ruleset), catalog)
    for e in res["sheet"]["spells"]:
        assert "moonbeam-xphb" not in [s["id"] for s in e.get("alwaysPrepared", [])]


@needs_data
def test_missing_record_or_key_degrades(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if "-frhof-" not in k}
    assert not [r for r in resolve(_draft("fighter", 5, "banneret-frhof"), bare)["sheet"]["innateSpells"]
                if r.get("source") == "Banneret"]
    nokey = copy.copy(catalog)
    nokey.subclasses = {k: {kk: vv for kk, vv in v.items() if kk != "innate_spells"} for k, v in catalog.subclasses.items()}
    assert not [r for r in resolve(_draft("fighter", 5, "banneret-frhof"), nokey)["sheet"]["innateSpells"]
                if r.get("source") == "Banneret"]
    res = resolve(_draft("bard", 6, "moon-frhof"), nokey)
    assert "moonbeam-xphb" not in [s["id"] for e in res["sheet"]["spells"] for s in e["alwaysPrepared"]]


@needs_data
def test_multiclass_and_markdown(catalog):
    d = _draft("fighter", 3, "banneret-frhof")
    d["classes"].append({"classId": "bard", "level": 6, "subclassId": "moon-frhof", "choices": {}})
    res = resolve(d, catalog)
    assert [r["spellId"] for r in res["sheet"]["innateSpells"] if r.get("source") == "Banneret"] == ["comprehend-languages-xphb"]
    assert "Comprehend Languages (ritual only" in to_markdown(res)
    d["classes"][0]["level"] = 2
    assert not [r for r in resolve(d, catalog)["sheet"]["innateSpells"] if r.get("source") == "Banneret"]


# ---- (b) Magic Connoisseur follows Magic Initiate -------------------------------------------------------------------

MI_WIZ = {"feat:magic-initiate-xphb:spell-variant": ["wizard-spells"], "feat:magic-initiate-xphb:spell-ability": ["int"]}
MC_PICK = {"class:wizard:4:asi": ["feat:magic-connoisseur-au"],
           "class:wizard:4:asi:feat:magic-connoisseur-au:ability-bonus": ["int"]}


def _mc(catalog, bg_choices, **kw):
    return resolve(_draft("wizard", 4, None, bg_choices=bg_choices, class_choices=MC_PICK, **kw), catalog)


def _cards(res, marker):
    return {c["id"]: c for c in res["choices"] if marker in c["id"]}


@needs_data
def test_the_vendored_text_says_same_list(catalog):
    text = "\n".join(str(x) for x in catalog.feats["magic-connoisseur-au"]["entries"])
    assert "from the same list you selected for the Magic Initiate feat's cantrips" in text
    assert feat_effects_data.FEAT_EFFECTS["magic-connoisseur-au"]["ability_from"] == "magic-initiate-xphb"
    assert (catalog.feats["magic-connoisseur-au"]["spell_variants"] == catalog.feats["magic-initiate-xphb"]["spell_variants"]
            == ["Cleric Spells", "Druid Spells", "Wizard Spells"])


@needs_data
def test_no_own_variant_card_and_no_spell_cards_until_the_base_picks(catalog):
    # F1: Sage's Magic Initiate has its list fixed by the background (a single-option card): that counts as picked even
    # though it was never clicked. The base feat taken at the ASI (free list) is the one that waits for its pick.
    res = _mc(catalog, {})
    mc = _cards(res, "magic-connoisseur-au")
    assert not [i for i in mc if i.endswith(":spell-variant")] and len([i for i in mc if ":spell-choice-" in i]) == 2
    assert "feat:magic-initiate-xphb:spell-variant" in _cards(res, "magic-initiate")
    asi = {"class:wizard:4:asi": ["feat:magic-initiate-xphb"], "class:wizard:8:asi": ["feat:magic-connoisseur-au"],
           "class:wizard:8:asi:feat:magic-connoisseur-au:ability-bonus": ["int"]}
    res = resolve(_draft("wizard", 8, None, bg="soldier-xphb", class_choices=asi), catalog)
    mc = _cards(res, "magic-connoisseur-au")
    assert not [i for i in mc if i.endswith(":spell-variant") or ":spell-choice-" in i]


@needs_data
@pytest.mark.parametrize("variant, klass", [("wizard-spells", "wizard"), ("cleric-spells", "cleric"), ("druid-spells", "druid")])
def test_the_spell_cards_follow_the_base_list(catalog, variant, klass):
    bg = {"feat:magic-initiate-xphb:spell-variant": [variant], "feat:magic-initiate-xphb:spell-ability": ["int"]}
    res = _mc(catalog, bg)
    mc = _cards(res, "magic-connoisseur-au:spell-choice-")
    assert len(mc) == 2 and not [i for i in _cards(res, "magic-connoisseur-au") if i.endswith(":spell-variant")]
    by_level = {}
    for card in mc.values():
        ids = [o["id"] if "id" in o else o["item"]["index"] for o in card["options"]]
        levels = {catalog.spells[i]["level"] for i in ids}
        classes = {c["index"] for i in ids for c in catalog.spells[i].get("classes", [])}
        by_level[next(iter(levels))] = (len(levels), classes)
    assert sorted(by_level) == [1, 2] and all(n == 1 for n, _ in by_level.values())
    assert all(klass in classes for _n, classes in by_level.values())
    # every offered spell is on that class's list (a spell of the other lists is not offered)
    for card in mc.values():
        for o in card["options"]:
            assert klass in {c["index"] for c in catalog.spells[o["id"]].get("classes", [])}


@needs_data
def test_picks_reach_the_sheet_with_the_base_ability(catalog):
    bg = dict(MI_WIZ)
    first = _cards(_mc(catalog, bg), "magic-connoisseur-au:spell-choice-")
    ids = sorted(first)
    picks = {ids[0]: [first[ids[0]]["options"][0]["id"]], ids[1]: [first[ids[1]]["options"][0]["id"]]}
    d = _draft("wizard", 4, None, bg_choices=bg, class_choices={**MC_PICK, **picks})
    res = resolve(d, catalog)
    rows = [r for r in res["sheet"]["innateSpells"] if r.get("featId") == "magic-connoisseur-au"]
    assert sorted(r["spellId"] for r in rows) == sorted(v[0] for v in picks.values())
    assert all(r["ability"] == "INT" and r["uses"] == "1/day" for r in rows)


@needs_data
def test_a_stored_own_variant_pick_is_a_non_blocking_stale_entry(catalog):
    cc = {**MC_PICK, "class:wizard:4:asi:feat:magic-connoisseur-au:spell-variant": ["cleric-spells"]}
    res = resolve(_draft("wizard", 4, None, bg_choices=MI_WIZ, class_choices=cc), catalog)
    assert any(p["choiceId"].endswith("magic-connoisseur-au:spell-variant") for p in res["pruned"])
    mc = _cards(res, "magic-connoisseur-au:spell-choice-")
    assert mc and all("wizard" in {c["index"] for c in catalog.spells[o["id"]].get("classes", [])}
                      for card in mc.values() for o in card["options"])


@needs_data
def test_without_the_base_feat_the_feat_keeps_its_own_card(catalog):
    res = resolve(_draft("wizard", 4, None, bg="soldier-xphb", class_choices=MC_PICK), catalog)
    ids = _cards(res, "magic-connoisseur-au")
    assert any(i.endswith(":spell-variant") for i in ids)


@needs_data
def test_other_feats_with_ability_from_are_unchanged(catalog):
    """Only feats that have `spell_variants` of their own follow a variant; the Robes / Envoy / Familiar feats do not."""
    d = feat_effects_data.FEAT_EFFECTS
    followers = [k for k, e in d.items() if e.get("ability_from") and catalog.feats[k].get("spell_variants")]
    assert followers == ["magic-connoisseur-au"]


# ---- (c) Rune Shaper and Boon of Magic School Mastery ---------------------------------------------------------------

@needs_data
def test_rune_shaper_record_is_pinned_to_the_table_and_the_text(catalog):
    f = catalog.feats["rune-shaper-bgg"]
    text = json.dumps(f["entries"])
    assert "half your proficiency bonus (rounded down)" in text
    assert "Intelligence, Wisdom, or Charisma (choose when you select this feat)" in text
    table = next(i for e in f["entries"][1]["items"] for i in e["entries"] if isinstance(i, dict) and i.get("type") == "table")
    assert table["colLabels"] == ["Rune", "Spell"] and len(table["rows"]) == 13
    assert [r[1].split("}")[0].split(" ", 1)[1].lower().replace(" ", "-") for r in table["rows"]] == RUNES
    assert f["innate_spells"] == [{"name": "Comprehend Languages", "spell_id": "comprehend-languages", "level": None,
                                   "uses": "1/day", "ability": {"choose": ["INT", "WIS", "CHA"]}, "variant": None}]
    (choice,) = f["spell_choices"]
    assert choice["from"] == RUNES and choice["filter"] is None and choice["uses"] == "1/day"
    assert choice["count_by_level"] == {"1": 1, "9": 1, "17": 1} and f["spell_variants"] == []


@pytest.mark.parametrize("level, pb, count", [(1, 2, 1), (4, 2, 1), (5, 3, 1), (8, 3, 1), (9, 4, 2), (12, 4, 2),
                                              (13, 5, 2), (16, 5, 2), (17, 6, 3), (20, 6, 3)])
@needs_data
def test_rune_count_is_half_the_proficiency_bonus(catalog, level, pb, count):
    assert count == pb // 2
    res = resolve(_draft("wizard", level, None, ruleset="mixed", bg="rune-carver-bgg"), catalog)
    card = next(c for c in res["choices"] if c["id"] == "feat:rune-shaper-bgg:spell-choice-0")
    assert card["count"] == count and len(card["options"]) == 13
    assert [o["id"] for o in card["options"]] == RUNES  # the Rune Spells table order


@needs_data
def test_rune_shaper_sheet_rows(catalog):
    bg = {"feat:rune-shaper-bgg:spell-ability": ["wis"], "feat:rune-shaper-bgg:spell-choice-0": ["fog-cloud", "goodberry"]}
    res = resolve(_draft("wizard", 9, None, ruleset="mixed", bg="rune-carver-bgg", bg_choices=bg), catalog)
    rows = [r for r in res["sheet"]["innateSpells"] if r.get("featId") == "rune-shaper-bgg"]
    assert [r["spellId"] for r in rows] == ["comprehend-languages", "fog-cloud", "goodberry"]
    assert all(r["uses"] == "1/day" and r["ability"] == "WIS" and r["usesMax"] == 1 and r["recharge"] == "long" for r in rows)
    assert res["problems"] == [] and res["pruned"] == []
    # a pick the level no longer allows is a non-blocking pruned entry (G-style count shrink)
    low = resolve(_draft("wizard", 1, None, ruleset="mixed", bg="rune-carver-bgg", bg_choices=bg), catalog)
    card = next(c for c in low["choices"] if c["id"] == "feat:rune-shaper-bgg:spell-choice-0")
    assert card["selected"] == ["fog-cloud"] and card["status"] == "resolved"


@needs_data
def test_rune_shaper_unpicked_is_pending_and_the_old_note_stays(catalog):
    res = resolve(_draft("wizard", 5, None, ruleset="mixed", bg="rune-carver-bgg"), catalog)
    pend = {c["id"] for c in res["choices"] if c["status"] == "pending" and "rune-shaper" in c["id"]}
    assert pend == {"feat:rune-shaper-bgg:spell-ability", "feat:rune-shaper-bgg:spell-choice-0"}
    assert "Rune Magic" in json.dumps(feat_effects_data.FEAT_EFFECTS["rune-shaper-bgg"]["notes"])


@needs_data
def test_boon_of_magic_school_mastery_is_not_a_literal_list(catalog):
    """Every pick of the Boon is a school filter (the "on your class's spell list" restriction is a rule): no `from` list
    anywhere, so G5 leaves the record and its note exactly as they were."""
    f = catalog.feats["boon-of-magic-school-mastery-au"]
    assert f["innate_spells"] == [] and len(f["spell_choices"]) == 16
    assert all(c["filter"] and not c["from"] and c["filter"].get("school") and "class" not in c["filter"]
               for c in f["spell_choices"])
    assert "on your class's spell list" in json.dumps(f["entries"])
    assert feat_effects_data.FEAT_EFFECTS["boon-of-magic-school-mastery-au"]["notes"][0].startswith("Choose a school of magic")


@needs_data
def test_resolve_stays_fast(catalog):
    drafts = {
        "Banneret 20": _draft("fighter", 20, "banneret-frhof"),
        "Moon 20": _draft("bard", 20, "moon-frhof"),
        "Rune Shaper 17": _draft("wizard", 17, None, ruleset="mixed", bg="rune-carver-bgg"),
        "Connoisseur": _draft("wizard", 8, None, bg_choices=MI_WIZ, class_choices=MC_PICK),
    }
    for name, d in drafts.items():
        resolve(d, catalog)
        assert_fast(measure(lambda: resolve(d, catalog)), name)
