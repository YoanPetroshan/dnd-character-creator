"""RP18 (F4): XPHB subclass innate spells, ruleset "2024" only; mixed / 2014 are unchanged.

Governing texts (catalog.features, XPHB records; `reference_data.SUBCLASS_INNATE_2024` carries the verbatim quotes,
pinned by `test_quotes_match_catalog`; the converter's `innate_spells` key on the subclass record is the data side):
  Animal Speaker (Wild Heart 3)       "You can cast the Beast Sense and Speak with Animals spells but only as Rituals.
                                      Wisdom is your spellcasting ability for them."
  Nature Speaker (Wild Heart 10)      "You can cast the Commune with Nature spell but only as a Ritual."
  Mantle of Majesty (Glamour 6)       "you cast Command without expending a spell slot" ... "Once you use this feature, you
                                      can't use it again until you finish a Long Rest."
  Telekinetic Master (Psi Warrior 18) "you can cast it without a spell slot or components, and your spellcasting ability
                                      for it is Intelligence." ... "until you finish a Long Rest"
  Darkness (Shadow 3)                 "You can expend 1 Focus Point to cast the Darkness spell without spell components."
  Steps of the Fey (Archfey 3)        "You can cast Misty Step without expending a spell slot a number of times equal to
                                      your Charisma modifier (minimum of once), and you regain all expended uses when you
                                      finish a Long Rest."
  Eldritch Hex (Great Old One 10)     "You always have the Hex spell prepared."  (prepared, NOT a free cast)
  The Third Eye (Diviner 10)          "See Invisibility. You can cast See Invisibility without expending a spell slot."

Rule matrix (sheet.innateSpells entry = spellId, name, level = the class level of the feature, uses, ability, source =
the subclass name, note):
  Wild Heart 3   Beast Sense + Speak with Animals   "ritual only"          WIS    from Barbarian 3
  Wild Heart 10  Commune with Nature                "ritual only"          WIS    from Barbarian 10
  Glamour 6      Command                            "1/long rest"          CHA    from Bard 6
  Psi Warrior 18 Telekinesis                        "1/long rest"          INT    from Fighter 18
  Shadow 3       Darkness                           "1 Focus Point"        WIS    from Monk 3
  Archfey 3      Misty Step                         "<max(1, CHA mod)>/long rest"  CHA    from Warlock 3
  Diviner 10     See Invisibility                   "1/short or long rest" INT    from Wizard 10
  Great Old One 10  Hex                             not innate: always prepared (sheet.spells[warlock].alwaysPrepared)
  gates          2024 only; none below the feature's class level, without the subclass, with an SRD-only catalog or a
                 catalog without the converter key; no new resource rows (the RP11 rows stay the trackers)"""
from perf_helpers import assert_fast, measure
import copy
import time

import pytest

from catalog import reference_data
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

# feature id -> (class, subclass id, subclass name, [(spell id, character level)], uses, ability)
CASES = {
    "wild-heart-xphb-3-animal-speaker": ("barbarian", "wild-heart-xphb", "Path of the Wild Heart", 3,
                                         ["beast-sense-xphb", "speak-with-animals-xphb"], "ritual only", "WIS"),
    "wild-heart-xphb-10-nature-speaker": ("barbarian", "wild-heart-xphb", "Path of the Wild Heart", 10,
                                          ["commune-with-nature-xphb"], "ritual only", "WIS"),
    "glamour-xphb-6-mantle-of-majesty": ("bard", "glamour-xphb", "College of Glamour", 6,
                                         ["command-xphb"], "1/long rest", "CHA"),
    "psi-warrior-xphb-18-telekinetic-master": ("fighter", "psi-warrior-xphb", "Psi Warrior", 18,
                                               ["telekinesis-xphb"], "1/long rest", "INT"),
    "shadow-xphb-3-darkness": ("monk", "shadow-xphb", "Warrior of Shadow", 3,
                               ["darkness-xphb"], "1 Focus Point", "WIS"),
    "archfey-xphb-3-steps-of-the-fey": ("warlock", "archfey-xphb", "Archfey Patron", 3,
                                        ["misty-step-xphb"], "1/long rest", "CHA"),
    "diviner-xphb-10-the-third-eye": ("wizard", "diviner-xphb", "Diviner", 10,
                                      ["see-invisibility-xphb"], "1/short or long rest", "INT"),
}
HEX_FID = "great-old-one-xphb-10-eldritch-hex"
# G5: the FRHoF rows of the same table (tests/test_g5_frhof_innate.py owns their rule matrix)
G5_FIDS = {"banneret-frhof-3-knightly-envoy", "moon-frhof-6-blessing-of-moonlight"}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(cls_id, level, sub, ruleset="2024", cha=14, wis=12, int_=12):
    entry = {"classId": cls_id, "level": level, "choices": {}}
    if sub:
        entry["subclassId"] = sub
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 12, "INT": int_, "WIS": wis, "CHA": cha}},
        "species": {"id": "human-xphb"},
        "background": {"id": "sage-xphb", "choices": {}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [entry],
    }


def _innate(catalog, cls_id, level, sub, **kw):
    return resolve(_draft(cls_id, level, sub, **kw), catalog)["sheet"]["innateSpells"]


def _subclass_rows(rows, name):
    return [r for r in rows if r.get("source") == name]


# ---- data -----------------------------------------------------------------------------------

@needs_data
def test_quotes_match_catalog(catalog):
    table = reference_data.SUBCLASS_INNATE_2024
    assert set(table) == set(CASES) | {HEX_FID} | G5_FIDS
    for fid, spec in table.items():
        rec = catalog.features[fid]
        text = "\n".join(rec["desc"])
        assert rec["source"] == ("FRHoF" if fid in G5_FIDS else "XPHB")
        assert (rec["subclass"] or {}).get("index") == spec["subclass"], fid
        assert (rec["class"] or {}).get("index") == spec["class"], fid
        assert spec["quotes"], fid
        for q in spec["quotes"]:
            assert q in text, (fid, q)
        # every spell of the entry is named in a quote (by its catalog name)
        for slug_ in spec["spells"]:
            name = catalog.spells[slug_ + "-xphb"]["name"]
            assert any(name in q for q in spec["quotes"]), (fid, name)


@needs_data
def test_frequency_and_ability_are_pinned_to_the_text(catalog):
    """Each frequency word of the table is in a quote; the abilities that the text does not state are the class's own."""
    table = reference_data.SUBCLASS_INNATE_2024
    words = {
        "wild-heart-xphb-3-animal-speaker": "only as Rituals",
        "wild-heart-xphb-10-nature-speaker": "only as a Ritual",
        "glamour-xphb-6-mantle-of-majesty": "until you finish a Long Rest",
        "psi-warrior-xphb-18-telekinetic-master": "until you finish a Long Rest",
        "shadow-xphb-3-darkness": "expend 1 Focus Point",
        "archfey-xphb-3-steps-of-the-fey": "number of times equal to your Charisma modifier (minimum of once)",
        "diviner-xphb-10-the-third-eye": "Short or Long Rest",
    }
    for fid, word in words.items():
        assert any(word in q for q in table[fid]["quotes"]), fid
    stated = {"wild-heart-xphb-3-animal-speaker": "Wisdom is your spellcasting ability",
              "wild-heart-xphb-10-nature-speaker": "Wisdom is your spellcasting ability",
              "psi-warrior-xphb-18-telekinetic-master": "your spellcasting ability for it is Intelligence"}
    for fid, ability in ((f, c[6]) for f, c in CASES.items()):
        spec = table[fid]
        assert spec["ability"] == ability, fid
        if fid in stated:
            assert spec["ability_from"] == "text" and any(stated[fid] in q for q in spec["quotes"]), fid
        elif spec["ability_from"] == "class":
            assert catalog.classes[spec["class"]]["spellcasting"]["spellcasting_ability"]["index"].upper() == ability, fid
        else:
            assert spec["ability_from"] == "data"


@needs_data
def test_converter_keeps_the_innate_blocks_as_data(catalog):
    """The additive `innate_spells` key exists on exactly the seven XPHB subclasses whose 5etools block has `innate`
    (plus, since G5, the FRHoF Banneret and College of the Moon; Scion of the Three has only a `choose` item)."""
    with_key = {k for k, v in catalog.subclasses.items() if "innate_spells" in v}
    assert with_key == {c[1] for c in CASES.values()} | {"great-old-one-xphb", "banneret-frhof", "moon-frhof"}
    wh = catalog.subclasses["wild-heart-xphb"]["innate_spells"]
    assert [(e["level"], e["spell"], e["kind"]) for e in wh] == [
        (3, "beast-sense-xphb", "ritual"), (3, "speak-with-animals-xphb", "ritual"), (10, "commune-with-nature-xphb", "ritual")]
    shadow = catalog.subclasses["shadow-xphb"]["innate_spells"]
    assert shadow == [{"level": 3, "spell": "darkness-xphb", "kind": "resource", "uses": "1", "ability": "WIS",
                       "resource": "Focus Point"}]
    arch = catalog.subclasses["archfey-xphb"]["innate_spells"]
    assert arch == [{"level": None, "spell": "misty-step-xphb", "kind": "daily", "uses": "cha", "ability": None,
                     "resource": None}]
    psi = catalog.subclasses["psi-warrior-xphb"]["innate_spells"]
    assert [(e["level"], e["spell"], e["kind"], e["uses"]) for e in psi] == [(18, "telekinesis-xphb", "daily", "1")]
    plain = {k: [(e["level"], e["spell"], e["kind"]) for e in catalog.subclasses[k]["innate_spells"]]
             for k in ("glamour-xphb", "great-old-one-xphb", "diviner-xphb")}
    assert plain == {"glamour-xphb": [(6, "command-xphb", "plain")], "great-old-one-xphb": [(10, "hex-xphb", "plain")],
                     "diviner-xphb": [(10, "see-invisibility-xphb", "plain")]}
    # no 2014 / SRD subclass gets the key
    assert not [k for k, v in catalog.subclasses.items()
                if "innate_spells" in v and not k.endswith(("-xphb", "-frhof"))]


@needs_data
def test_table_agrees_with_converter_data(catalog):
    """The table says what the text means; the converter data decides which spell at which class level exists."""
    for fid, spec in reference_data.SUBCLASS_INNATE_2024.items():
        rec = catalog.features[fid]
        data = {(e["spell"], e["level"] or rec["level"]) for e in catalog.subclasses[spec["subclass"]]["innate_spells"]}
        for slug_ in spec["spells"]:
            assert (slug_ + "-xphb", rec["level"]) in data, (fid, slug_)


# ---- rule matrix ----------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("fid", sorted(CASES))
def test_entry_appears_exactly_from_its_level(catalog, fid):
    cls_id, sub, sub_name, level, spells, uses, ability = CASES[fid]
    below = _subclass_rows(_innate(catalog, cls_id, level - 1, sub), sub_name) if level - 1 >= 3 else []
    assert not [r for r in below if r["spellId"] in spells]
    rows = _subclass_rows(_innate(catalog, cls_id, level, sub), sub_name)
    mine = [r for r in rows if r["spellId"] in spells]
    assert sorted(r["spellId"] for r in mine) == sorted(spells)
    for r in mine:
        assert r["level"] == level and r["ability"] == ability and r["source"] == sub_name
        assert r["variant"] is None and r["name"] == catalog.spells[r["spellId"]]["name"]
        if fid != "archfey-xphb-3-steps-of-the-fey":
            assert r["uses"] == uses, fid
    # higher levels keep it
    higher = [r["spellId"] for r in _subclass_rows(_innate(catalog, cls_id, 20, sub), sub_name) if r["spellId"] in spells]
    assert sorted(higher) == sorted(spells)


@needs_data
def test_wild_heart_levels(catalog):
    names = lambda lvl: [r["name"] for r in _subclass_rows(_innate(catalog, "barbarian", lvl, "wild-heart-xphb"), "Path of the Wild Heart")]  # noqa: E731
    assert names(3) == ["Beast Sense", "Speak with Animals"] and names(9) == names(3)
    assert names(10) == ["Beast Sense", "Speak with Animals", "Commune with Nature"]


@needs_data
def test_notes_carry_the_use_rules(catalog):
    glam = _subclass_rows(_innate(catalog, "bard", 6, "glamour-xphb"), "College of Glamour")[0]
    assert "Bonus Action" in glam["note"] and "level 3+ spell slot" in glam["note"]
    psi = _subclass_rows(_innate(catalog, "fighter", 18, "psi-warrior-xphb"), "Psi Warrior")[0]
    assert "Psionic Energy Die" in psi["note"] and "components" in psi["note"]
    shadow = _subclass_rows(_innate(catalog, "monk", 3, "shadow-xphb"), "Warrior of Shadow")[0]
    assert shadow["uses"] == "1 Focus Point" and "components" in shadow["note"]
    eye = _subclass_rows(_innate(catalog, "wizard", 10, "diviner-xphb"), "Diviner")[0]
    assert "Third Eye" in eye["note"]


@pytest.mark.parametrize("cha,expected", [(8, 1), (10, 1), (12, 1), (14, 2), (18, 4), (20, 5)])
@needs_data
def test_archfey_misty_step_uses_follow_charisma_minimum_one(catalog, cha, expected):
    row = _subclass_rows(_innate(catalog, "warlock", 3, "archfey-xphb", cha=cha), "Archfey Patron")[0]
    assert row["spellId"] == "misty-step-xphb" and row["uses"] == f"{expected}/long rest" and row["ability"] == "CHA"
    assert row["level"] == 3


@needs_data
def test_great_old_one_hex_is_always_prepared_not_innate(catalog):
    def warlock(lvl):
        res = resolve(_draft("warlock", lvl, "great-old-one-xphb"), catalog)
        entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")
        return res, entry
    res9, e9 = warlock(9)
    res10, e10 = warlock(10)
    assert "hex-xphb" not in [s["id"] for s in e9["alwaysPrepared"]]
    always = {s["id"]: s for s in e10["alwaysPrepared"]}
    assert "hex-xphb" in always
    assert not [r for r in res10["sheet"]["innateSpells"] if r["spellId"] == "hex-xphb"]
    # the Warlock's own prepared card cannot take it twice
    card = next(c for c in res10["choices"] if c["id"] == "class:warlock:spells-known")
    hex_opt = next((o for o in card["options"] if o["id"] == "hex-xphb"), None)
    assert hex_opt is None or hex_opt.get("disabled")


@needs_data
def test_no_new_resource_rows(catalog):
    """RP11 owns the trackers; RP18 only adds innate entries (the resource rows equal those of a catalog without the data)."""
    nokey = copy.copy(catalog)
    nokey.subclasses = {k: {kk: vv for kk, vv in v.items() if kk != "innate_spells"} for k, v in catalog.subclasses.items()}
    for fid, (cls_id, sub, _name, level, *_rest) in CASES.items():
        with_data = resolve(_draft(cls_id, level, sub), catalog)
        without = resolve(_draft(cls_id, level, sub), nokey)
        assert with_data["sheet"]["innateSpells"] != without["sheet"]["innateSpells"], fid
        assert with_data["derived"]["classResources"] == without["derived"]["classResources"], fid


# ---- gates ----------------------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_other_rulesets_get_nothing(catalog, ruleset):
    for fid, (cls_id, sub, sub_name, level, *_rest) in CASES.items():
        rows = _innate(catalog, cls_id, max(level, 10), sub, ruleset=ruleset)
        assert _subclass_rows(rows, sub_name) == [], (fid, ruleset)
    res = resolve(_draft("warlock", 10, "great-old-one-xphb", ruleset=ruleset), catalog)
    for e in res["sheet"]["spells"]:
        assert "hex-xphb" not in [s["id"] for s in e.get("alwaysPrepared", [])]


@needs_data
def test_without_the_subclass_or_with_another_one(catalog):
    assert not [r for r in _innate(catalog, "warlock", 10, None) if r["spellId"] == "misty-step-xphb"]
    assert not [r for r in _innate(catalog, "warlock", 10, "fiend-xphb") if r.get("source") == "Archfey Patron"]
    both = _innate(catalog, "warlock", 10, "archfey-xphb")
    assert [r["spellId"] for r in both if r.get("source") == "Archfey Patron"] == ["misty-step-xphb"]


@needs_data
def test_srd_only_and_missing_converter_keys_degrade(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if "-xphb-" not in k}
    for fid, (cls_id, sub, sub_name, level, *_rest) in CASES.items():
        res = resolve(_draft(cls_id, level, sub), bare)
        assert _subclass_rows(res["sheet"]["innateSpells"], sub_name) == [], fid
    nokey = copy.copy(catalog)
    nokey.subclasses = {k: {kk: vv for kk, vv in v.items() if kk != "innate_spells"} for k, v in catalog.subclasses.items()}
    for fid, (cls_id, sub, sub_name, level, *_rest) in CASES.items():
        res = resolve(_draft(cls_id, level, sub), nokey)
        assert _subclass_rows(res["sheet"]["innateSpells"], sub_name) == [], fid
    res = resolve(_draft("warlock", 10, "great-old-one-xphb"), nokey)
    entry = next(e for e in res["sheet"]["spells"] if e["classId"] == "warlock")
    assert "hex-xphb" not in [s["id"] for s in entry["alwaysPrepared"]]


@needs_data
def test_multiclass_keeps_each_class_level(catalog):
    d = _draft("barbarian", 3, "wild-heart-xphb")
    d["classes"].append({"classId": "warlock", "level": 3, "subclassId": "archfey-xphb", "choices": {}})
    rows = resolve(d, catalog)["sheet"]["innateSpells"]
    assert {r["source"] for r in rows if r.get("source")} == {"Path of the Wild Heart", "Archfey Patron"}
    d["classes"][0]["level"] = 2  # Wild Heart not reached
    rows = resolve(d, catalog)["sheet"]["innateSpells"]
    assert {r["source"] for r in rows if r.get("source")} == {"Archfey Patron"}


# ---- surfaces -------------------------------------------------------------------------------

@needs_data
def test_exports_print_the_entries(catalog):
    from markdown_export import to_markdown
    res = resolve(_draft("warlock", 3, "archfey-xphb", cha=16), catalog)
    md = to_markdown(res)
    assert "Misty Step (3/long rest" in md
    res = resolve(_draft("barbarian", 3, "wild-heart-xphb"), catalog)
    md = to_markdown(res)
    assert "Beast Sense (ritual only" in md and "Speak with Animals (ritual only" in md


@needs_data
def test_resolve_stays_fast(catalog):
    drafts = {
        "Fighter 20 mixed": _draft("fighter", 20, None, ruleset="mixed"),
        "Fighter 20 2024": _draft("fighter", 20, None),
        "Wizard 20 mixed": _draft("wizard", 20, None, ruleset="mixed"),
        "Wizard 20 2024": _draft("wizard", 20, None),
        "Bard 20 mixed": _draft("bard", 20, None, ruleset="mixed"),
        "Bard 20 2024": _draft("bard", 20, None),
        "Wild Heart 10": _draft("barbarian", 10, "wild-heart-xphb"),
        "Glamour 20": _draft("bard", 20, "glamour-xphb"),
        "Psi Warrior 18": _draft("fighter", 18, "psi-warrior-xphb"),
        "Shadow 3": _draft("monk", 3, "shadow-xphb"),
        "Archfey 10": _draft("warlock", 10, "archfey-xphb"),
        "Great Old One 10": _draft("warlock", 10, "great-old-one-xphb"),
        "Diviner 10": _draft("wizard", 10, "diviner-xphb"),
    }
    for name, d in drafts.items():
        resolve(d, catalog)
        assert_fast(measure(lambda: resolve(d, catalog)), name)
