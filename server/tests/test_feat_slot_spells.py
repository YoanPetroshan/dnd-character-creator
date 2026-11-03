"""RP19 (A2, open question 14, + Spells of the Mark): spell tables keyed by spell slot level.

Governing sentences (catalog feat `entries`, tags stripped; `feat_effects_tail.RP19_QUOTES`, pinned by
``test_quote_matches_catalog``):
  Arcane Adept (8 feats, Unearthed Arcana)  "When you have spell slots of a level specified in the <School> Adept Spells
        table, you thereafter always have the spells listed for that level and lower prepared."
  Spells of the Mark (12 feats, EFA)        "If you have the Spellcasting or Pact Magic class feature, the spells on the
        Mark of <X> Spells table are added to that feature's spell list."
The tables themselves are parsed from the catalog text (`test_table_matches_catalog_text`): the converter keys
`slot_spells` (Adept, from `prepared` sN) and `expanded_spells` (Marks, from `expanded` sN) must equal the printed rows.

Rule matrix (FE edition policy: the effect applies under every ruleset in which the character holds the feat):
  Arcane Adept   highest slot level H = max(shared pool, Pact Magic slot level); every spell of the rows 1..H becomes a
                 sheet.innateSpells entry (uses "always prepared", featId, source = the feat name, no class, level None,
                 note names the row); no slots (non-caster, Fighter) -> nothing; two Adept feats -> both tables.
                 Paladin 5 (H 2) Shield + Lesser Restoration; Wizard 9 (H 5) all five; Warlock 5 (pact 3) three;
                 Wizard 3 / Warlock 5 -> 3 (the pact level is higher); Cleric 9 / Warlock 2 -> 5 (the pool is higher).
  Marks          for each caster class (Spellcasting or Pact Magic) the table spells up to ITS highest castable level are
                 added to that class's spell cards (known / prepared list, Wizard spellbook), labelled "(Spells of the
                 Mark)" when they are not on the class list; a non-caster gets nothing; a Mark spell already on the list is
                 not duplicated; hidden by the ruleset / sources -> not offered; a stored pick that becomes invalid is a
                 non-blocking `pruned` entry (the existing spell-card pass).
  gates          no effect without the feat; a catalog without the converter keys / an empty catalog gives nothing."""
from perf_helpers import assert_fast
import copy
import re
import time

import pytest

from catalog import feat_effects_tail as tail
from catalog.official.common import slug
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_spell_tables
from engine.resolve import resolve
from markdown_export import to_markdown

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

SCHOOLS = ("abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy", "transmutation")
ADEPTS = tuple(f"{s}-adept-au" for s in SCHOOLS)
HOUSE = {"mark-of-making-efa": "house-cannith-heir-efa", "mark-of-sentinel-efa": "house-deneith-heir-efa",
         "mark-of-hospitality-efa": "house-ghallanda-heir-efa", "mark-of-healing-efa": "house-jorasco-heir-efa",
         "mark-of-warding-efa": "house-kundarak-heir-efa", "mark-of-storm-efa": "house-lyrandar-heir-efa",
         "mark-of-detection-efa": "house-medani-heir-efa", "mark-of-passage-efa": "house-orien-heir-efa",
         "mark-of-shadow-efa": "house-phiarlan-heir-efa", "mark-of-scribing-efa": "house-sivis-heir-efa",
         "mark-of-finding-efa": "house-tharashk-heir-efa", "mark-of-handling-efa": "house-vadalis-heir-efa"}
MARKS = tuple(HOUSE)
MARK_LABEL = "(Spells of the Mark)"


@pytest.fixture(scope="module")
def catalog():
    return load()


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


def _table_rows(entries):
    """{row number: [spell slug]} from the first 'table' node of a feat's entries (the printed rows)."""
    found = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "table":
                found.append(n)
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(entries)
    rows = {}
    for row in found[0]["rows"]:
        names = [m.split("|")[0] for m in re.findall(r"\{@spell ([^}]*)\}", row[1])]
        rows[int(row[0])] = [slug(n) for n in names]
    return rows


def _draft(classes, feats=(), ruleset="mixed", background="acolyte", base=None, sources=()):
    """`classes`: [(class id, level, subclass id or None)]; `feats` are taken at the first class's Ability Score
    Improvement levels (4, 8, ...)."""
    first = classes[0][0]
    chosen = {f"class:{first}:{slot}:asi": [f"feat:{f}"] for slot, f in zip((4, 8, 12, 16), feats)}
    entries = []
    for i, (cid, level, sub) in enumerate(classes):
        entry = {"classId": cid, "level": level, "choices": chosen if i == 0 else {}}
        if sub:
            entry["subclassId"] = sub
        entries.append(entry)
    return {
        "ruleset": ruleset, "sources": list(sources),
        "abilities": {"method": "manual", "base": base or {"STR": 12, "DEX": 14, "CON": 12, "INT": 14, "WIS": 14, "CHA": 14}},
        "species": {"id": "human", "choices": {}},
        "background": {"id": background, "choices": {}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": entries,
    }


def _adept_rows(res, feat=None):
    return [e for e in res["sheet"]["innateSpells"] if e.get("featId") and (feat is None or e["featId"] == feat)
            and e["uses"] == "always prepared"]


def _names(rows):
    return {e["name"].lower() for e in rows}


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _option_labels(res, cid):
    return {o["id"]: o["label"] for o in _card(res, cid)["options"]}


# ---------------------------------------------------------------- data pins


@needs_data
@pytest.mark.parametrize("index", ADEPTS + MARKS)
def test_quote_matches_catalog(catalog, index):
    key = "adept" if index in ADEPTS else "mark"
    assert tail.RP19_QUOTES[key] in _plain(catalog.feats[index]["entries"])


@needs_data
@pytest.mark.parametrize("index", ADEPTS)
def test_adept_table_matches_catalog_text(catalog, index):
    feat = catalog.feats[index]
    assert feat["slot_spells"] == _table_rows(feat["entries"])
    assert set(feat["slot_spells"]) == {1, 2, 3, 4, 5}
    assert feat["expanded_spells"] == {}


@needs_data
@pytest.mark.parametrize("index", MARKS)
def test_mark_table_matches_catalog_text(catalog, index):
    feat = catalog.feats[index]
    assert feat["expanded_spells"] == _table_rows(feat["entries"])
    assert set(feat["expanded_spells"]) == {1, 2, 3, 4, 5}
    assert feat["slot_spells"] == {}


@needs_data
def test_only_these_twenty_feats_carry_a_table(catalog):
    assert {i for i, f in catalog.feats.items() if f["slot_spells"] or f["expanded_spells"]} == set(ADEPTS) | set(MARKS)


@needs_data
@pytest.mark.parametrize("index", ADEPTS + MARKS)
def test_every_table_spell_is_in_the_catalog(catalog, index):
    feat = catalog.feats[index]
    for ids in (feat["slot_spells"] or feat["expanded_spells"]).values():
        for sid in ids:
            assert catalog.resolve_spell_id(sid) in catalog.spells, sid


@needs_data
def test_mark_table_row_is_the_spell_level(catalog):
    for index in MARKS:
        for n, ids in catalog.feats[index]["expanded_spells"].items():
            assert {catalog.spells[catalog.resolve_spell_id(s)]["level"] for s in ids} == {n}, index


@needs_data
def test_feat_notes_no_longer_print_the_adept_table(catalog):
    from catalog import feat_effects_data as fed
    for index in ADEPTS:
        notes = " ".join(fed.FEAT_EFFECTS[index]["notes"])
        assert "innate spells" in notes and "Mass Cure Wounds" not in notes and "Banishment" not in notes, index


# ---------------------------------------------------------------- pure functions


def test_highest_slot_level_is_the_max_of_pool_and_pact():
    f = feat_spell_tables.highest_slot_level
    assert f({}, {}) == 0
    assert f({"1": 4, "2": 3}, {}) == 2
    assert f({}, {"2": 2}) == 2
    assert f({"1": 4, "2": 3}, {"3": 2}) == 3
    assert f({"1": 4, "2": 3, "3": 3, "4": 3, "5": 2}, {"1": 1}) == 5


def test_adept_entries_pure(catalog=None):
    feat = {"index": "x-adept-au", "name": "X Adept", "slot_spells": {1: ["shield"], 2: ["lesser-restoration"], 3: ["fireball"]}}
    rows = feat_spell_tables.adept_entries([feat], 2)
    assert [r["spell_id"] for r in rows] == ["shield", "lesser-restoration"]
    assert rows[0]["uses"] == "always prepared" and rows[0]["featId"] == "x-adept-au" and rows[0]["source_label"] == "X Adept"
    assert rows[0]["level"] is None and rows[0]["ability"] is None and "slot level 1" in rows[0]["note"]
    assert feat_spell_tables.adept_entries([feat], 0) == []
    assert feat_spell_tables.adept_entries([{"index": "plain", "name": "Plain"}], 5) == []  # catalog without the key


def test_mark_ids_pure():
    feat = {"index": "m", "name": "M", "expanded_spells": {1: ["a", "b"], 2: ["c"], 4: ["d"]}}
    assert feat_spell_tables.mark_spell_slugs([feat], 2) == ["a", "b", "c"]
    assert feat_spell_tables.mark_spell_slugs([feat], 0) == []
    assert feat_spell_tables.mark_spell_slugs([{"index": "plain"}], 5) == []


# ---------------------------------------------------------------- Arcane Adept, engine


ABJ = {1: "Shield", 2: "Lesser Restoration", 3: "Protection from Energy", 4: "Banishment", 5: "Mass Cure Wounds"}


def _expect(upto):
    return {name.lower() for n, name in ABJ.items() if n <= upto}


@needs_data
def test_abjuration_adept_paladin_5(catalog):
    res = resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), catalog)
    rows = _adept_rows(res, "abjuration-adept-au")
    assert _names(rows) == _expect(2) == {"shield", "lesser restoration"}
    for e in rows:
        assert e["uses"] == "always prepared" and e["featId"] == "abjuration-adept-au"
        assert e["source"] == "Abjuration Adept" and e["level"] is None and e["ability"] is None
        assert e["spellId"] in catalog.spells and "slot level" in e["note"]
    assert not {"protection from energy", "banishment"} & _names(res["sheet"]["innateSpells"])


@needs_data
@pytest.mark.parametrize("cls,level,upto", [
    ("wizard", 5, 3), ("wizard", 7, 4), ("wizard", 9, 5), ("wizard", 20, 5), ("cleric", 9, 5), ("paladin", 9, 3), ("paladin", 17, 5),
    ("bard", 4, 2), ("sorcerer", 5, 3), ("druid", 7, 4), ("ranger", 5, 2)])
def test_adept_tracks_the_highest_slot_level(catalog, cls, level, upto):
    res = resolve(_draft([(cls, level, None)], ["abjuration-adept-au"]), catalog)
    assert _names(_adept_rows(res)) == _expect(upto)
    assert min(5, max(int(k) for k in res["derived"]["spellSlots"])) == upto


@needs_data
@pytest.mark.parametrize("level,pact", [(4, 2), (5, 3), (9, 5), (11, 5)])
def test_adept_uses_the_pact_magic_slot_level(catalog, level, pact):
    res = resolve(_draft([("warlock", level, None)], ["abjuration-adept-au"]), catalog)
    assert res["derived"]["spellSlots"] == {}
    assert max(int(k) for k in res["derived"]["warlockSpellSlots"]) == pact
    assert _names(_adept_rows(res)) == _expect(pact)


@needs_data
def test_adept_multiclass_takes_the_higher_of_pool_and_pact(catalog):
    wizard_warlock = resolve(_draft([("warlock", 5, None), ("wizard", 3, None)], ["abjuration-adept-au"]), catalog)
    assert max(int(k) for k in wizard_warlock["derived"]["spellSlots"]) == 2
    assert max(int(k) for k in wizard_warlock["derived"]["warlockSpellSlots"]) == 3
    assert _names(_adept_rows(wizard_warlock)) == _expect(3)
    cleric_warlock = resolve(_draft([("cleric", 9, None), ("warlock", 2, None)], ["abjuration-adept-au"]), catalog)
    assert max(int(k) for k in cleric_warlock["derived"]["warlockSpellSlots"]) == 1
    assert _names(_adept_rows(cleric_warlock)) == _expect(5)


@needs_data
def test_adept_without_spell_slots_gives_nothing(catalog):
    res = resolve(_draft([("fighter", 8, None)], ["abjuration-adept-au"]), catalog)
    assert res["derived"]["spellSlots"] == {} and res["derived"]["warlockSpellSlots"] == {}
    assert _adept_rows(res) == []
    assert any(f["id"] == "abjuration-adept-au" for f in res["sheet"]["feats"])  # the feat itself is still on the sheet


@needs_data
def test_adept_slot_level_gates_the_rows_exactly(catalog):
    """A Paladin 5 has no 3rd-level slot yet; at Paladin 9 the 3rd row joins."""
    five = resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), catalog)
    nine = resolve(_draft([("paladin", 9, None)], ["abjuration-adept-au"]), catalog)
    assert "protection from energy" not in _names(_adept_rows(five))
    assert "protection from energy" in _names(_adept_rows(nine))


@needs_data
@pytest.mark.parametrize("school", SCHOOLS)
def test_every_adept_feat_resolves_its_own_table(catalog, school):
    index = f"{school}-adept-au"
    res = resolve(_draft([("wizard", 9, None)], [index]), catalog)
    rows = _adept_rows(res, index)
    want = [catalog.spells[catalog.resolve_spell_id(s)]["name"] for ids in catalog.feats[index]["slot_spells"].values() for s in ids]
    assert [e["name"] for e in rows] == want and len(rows) == 5
    assert all(e["source"] == catalog.feats[index]["name"] for e in rows)


@needs_data
def test_two_adept_feats_list_both_tables(catalog):
    res = resolve(_draft([("wizard", 9, None)], ["abjuration-adept-au", "evocation-adept-au"]), catalog)
    assert {e["featId"] for e in _adept_rows(res)} == {"abjuration-adept-au", "evocation-adept-au"}
    assert len(_adept_rows(res)) == 10 and "fireball" in _names(_adept_rows(res)) and "shield" in _names(_adept_rows(res))


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014", "2024"])
def test_adept_applies_under_every_ruleset(catalog, ruleset):
    res = resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"], ruleset=ruleset), catalog)
    assert _names(_adept_rows(res)) == _expect(2)


@needs_data
def test_adept_rows_reach_the_markdown_export(catalog):
    res = resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), catalog)
    md = to_markdown(res)
    assert "Shield (always prepared)" in md and "Lesser Restoration (always prepared)" in md


@needs_data
def test_adept_respects_the_ability_less_shape_for_the_types(catalog):
    res = resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), catalog)
    for e in _adept_rows(res):
        assert set(e) <= {"spellId", "name", "level", "uses", "ability", "variant", "featId", "source", "note"}


# ---------------------------------------------------------------- gates


@needs_data
def test_no_feat_no_rows_and_no_label(catalog):
    for cls, lvl in (("paladin", 5), ("wizard", 9), ("cleric", 5)):
        res = resolve(_draft([(cls, lvl, None)]), catalog)
        assert _adept_rows(res) == []
        for c in res["choices"]:
            assert not any(MARK_LABEL in o["label"] for o in c["options"])


@needs_data
def test_catalog_without_the_converter_keys_gives_nothing(catalog):
    patched = copy.copy(catalog)
    patched.feats = {i: {k: v for k, v in f.items() if k not in ("slot_spells", "expanded_spells")} for i, f in catalog.feats.items()}
    res = resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), patched)
    assert _adept_rows(res) == []
    res = resolve(_draft([("cleric", 5, None)], background="house-jorasco-heir-efa"), patched)
    assert not any(MARK_LABEL in o["label"] for c in res["choices"] for o in c["options"])


@needs_data
def test_empty_tables_give_nothing(catalog):
    patched = copy.copy(catalog)
    patched.feats = {i: {**f, "slot_spells": {}, "expanded_spells": {}} for i, f in catalog.feats.items()}
    assert _adept_rows(resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), patched)) == []


@needs_data
def test_a_table_spell_missing_from_the_catalog_keeps_its_name(catalog):
    patched = copy.copy(catalog)
    patched.feats = {**catalog.feats, "abjuration-adept-au": {**catalog.feats["abjuration-adept-au"],
                                                             "slot_spells": {1: ["not-a-real-spell"]}}}
    rows = _adept_rows(resolve(_draft([("paladin", 5, None)], ["abjuration-adept-au"]), patched))
    assert [(e["name"], e["spellId"]) for e in rows] == [("Not A Real Spell", None)]


# ---------------------------------------------------------------- Spells of the Mark, engine


def _mark_draft(mark, classes, ruleset="mixed", **kw):
    return _draft(classes, background=HOUSE[mark], ruleset=ruleset, **kw)


def _mark_ids(catalog, mark, upto):
    return {catalog.resolve_spell_id(s) for n, ids in catalog.feats[mark]["expanded_spells"].items() if n <= upto for s in ids}


@needs_data
def test_mark_of_healing_cleric_5_gets_the_mark_spells_up_to_level_3(catalog):
    res = resolve(_mark_draft("mark-of-healing-efa", [("cleric", 5, None)]), catalog)
    labels = _option_labels(res, "class:cleric:spells-known")
    names = {n for n in ("False Life", "Healing Word", "Arcane Vigor", "Prayer of Healing", "Aura of Vitality",
                         "Mass Healing Word")}
    shown = {re.sub(r" \(Spells of the Mark\)$", "", v) for v in labels.values()}
    assert names <= shown
    assert "Aura of Purity" not in shown and "Greater Restoration" not in shown  # levels 4 and 5: no slot yet
    off_list = {sid for sid in labels if not any(c["index"] == "cleric" for c in catalog.spells[sid].get("classes", []))}
    assert off_list and all(labels[sid].endswith(MARK_LABEL) for sid in off_list)
    assert all(MARK_LABEL not in labels[sid] for sid in labels if sid not in off_list)
    assert all(labels[sid].startswith("False Life") for sid in labels if catalog.spells[sid]["name"] == "False Life")


@needs_data
@pytest.mark.parametrize("level,upto", [(1, 1), (3, 2), (5, 3), (7, 4), (9, 5)])
def test_mark_spells_follow_the_class_slot_level(catalog, level, upto):
    res = resolve(_mark_draft("mark-of-healing-efa", [("cleric", level, None)]), catalog)
    offered = {o["id"] for o in _card(res, "class:cleric:spells-known")["options"]}
    for n, ids in catalog.feats["mark-of-healing-efa"]["expanded_spells"].items():
        for s in ids:
            got = any(catalog.resolve_spell_id(s) == o or catalog.spell_twins.get(o) == catalog.resolve_spell_id(s) for o in offered)
            assert got == (n <= upto), (level, s)


@needs_data
def test_without_the_mark_the_off_list_spells_are_not_offered(catalog):
    res = resolve(_draft([("cleric", 5, None)]), catalog)
    shown = {o["label"] for o in _card(res, "class:cleric:spells-known")["options"]}
    assert "False Life" not in shown and "Arcane Vigor" not in shown


@needs_data
def test_a_mark_spell_can_be_picked_and_reaches_the_sheet(catalog):
    base = _mark_draft("mark-of-healing-efa", [("cleric", 5, None)])
    res = resolve(base, catalog)
    pick = next(o["id"] for o in _card(res, "class:cleric:spells-known")["options"] if o["label"].startswith("False Life"))
    base["classes"][0]["choices"]["class:cleric:spells-known"] = [pick]
    res = resolve(base, catalog)
    assert pick in _card(res, "class:cleric:spells-known")["selected"]
    assert any(s["id"] == pick for s in res["sheet"]["spells"][0]["known"])
    assert not res["pruned"]


@needs_data
def test_a_pick_disappears_non_blocking_when_the_mark_goes(catalog):
    base = _mark_draft("mark-of-healing-efa", [("cleric", 5, None)])
    pick = next(o["id"] for o in _card(resolve(base, catalog), "class:cleric:spells-known")["options"] if o["label"].startswith("False Life"))
    base["classes"][0]["choices"]["class:cleric:spells-known"] = [pick]
    base["background"]["id"] = "acolyte"
    res = resolve(base, catalog)
    assert pick not in _card(res, "class:cleric:spells-known")["selected"]
    assert any(p.get("choiceId") == "class:cleric:spells-known" for p in res["pruned"])
    assert not any(p.get("blocking") for p in res.get("problems", []) if "spells-known" in str(p))


@needs_data
def test_mark_on_a_non_caster_gives_nothing(catalog):
    res = resolve(_mark_draft("mark-of-healing-efa", [("fighter", 5, None)]), catalog)
    assert not any(MARK_LABEL in o["label"] for c in res["choices"] for o in c["options"])
    assert not any(c["id"].endswith("spells-known") for c in res["choices"])


@needs_data
def test_mark_spells_join_the_wizard_spellbook_and_the_prepared_card_draws_from_it(catalog):
    base = _mark_draft("mark-of-healing-efa", [("wizard", 5, None)])
    res = resolve(base, catalog)
    book = _option_labels(res, "class:wizard:spellbook")
    healing = next(sid for sid, label in book.items() if label.startswith("Healing Word"))
    assert book[healing].endswith(MARK_LABEL)
    assert not any(label.startswith("Greater Restoration") for label in book.values())  # level 5 spell, slot level 3
    base["classes"][0]["choices"]["class:wizard:spellbook"] = [healing]
    prepared = _card(resolve(base, catalog), "class:wizard:spells-known")
    assert healing in {o["id"] for o in prepared["options"]}


@needs_data
def test_mark_on_a_warlock_uses_the_pact_slot_level(catalog):
    res = resolve(_mark_draft("mark-of-healing-efa", [("warlock", 5, None)]), catalog)
    labels = _option_labels(res, "class:warlock:spells-known")
    shown = {re.sub(r" \(Spells of the Mark\)$", "", v) for v in labels.values()}
    assert {"False Life", "Healing Word", "Aura of Vitality"} <= shown   # pact slot level 3
    assert "Aura of Life" not in shown


@needs_data
def test_mark_on_a_third_caster_subclass(catalog):
    res = resolve(_mark_draft("mark-of-healing-efa", [("fighter", 7, "eldritch-knight-phb")]), catalog)
    card = _card(res, "class:fighter:spells-known")
    assert card is not None
    shown = {o["label"] for o in card["options"]}
    assert any(x.startswith("False Life") for x in shown) and not any(x.startswith("Aura of Vitality") for x in shown)


@needs_data
def test_each_class_of_a_multiclass_uses_its_own_slot_level(catalog):
    res = resolve(_mark_draft("mark-of-healing-efa", [("cleric", 5, None), ("wizard", 1, None)]), catalog)
    cleric = {o["label"] for o in _card(res, "class:cleric:spells-known")["options"]}
    wizard = {o["label"] for o in _card(res, "class:wizard:spellbook")["options"]}
    assert any(x.startswith("Aura of Vitality") for x in cleric)           # Cleric 5: level 3 slots
    assert not any(x.startswith("Aura of Vitality") for x in wizard)       # Wizard 1: level 1 only
    assert any(x.startswith("False Life") for x in wizard)


@needs_data
def test_a_mark_spell_on_the_class_list_is_not_duplicated_or_labelled(catalog):
    res = resolve(_mark_draft("mark-of-healing-efa", [("cleric", 5, None)]), catalog)
    card = _card(res, "class:cleric:spells-known")
    ids = [o["id"] for o in card["options"]]
    assert len(ids) == len(set(ids))
    healing = [o for o in card["options"] if o["label"].startswith("Healing Word")]
    assert len(healing) == 1 and MARK_LABEL not in healing[0]["label"]


@needs_data
@pytest.mark.parametrize("mark", MARKS)
def test_every_mark_adds_its_level_one_spells_to_a_wizard_book(catalog, mark):
    res = resolve(_mark_draft(mark, [("wizard", 1, None)]), catalog)
    book = {re.sub(r" \(Spells of the Mark\)$", "", v) for v in _option_labels(res, "class:wizard:spellbook").values()}
    for s in catalog.feats[mark]["expanded_spells"][1]:
        assert catalog.spells[catalog.resolve_spell_id(s)]["name"] in book, (mark, s)


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2024"])
def test_marks_apply_under_mixed_and_2024(catalog, ruleset):
    res = resolve(_mark_draft("mark-of-healing-efa", [("cleric", 5, None)], ruleset=ruleset), catalog)
    shown = {o["label"] for o in _card(res, "class:cleric:spells-known")["options"]}
    assert any(x.startswith("False Life") for x in shown)


@needs_data
def test_marks_respect_the_visibility_filter(catalog):
    """Under ruleset 2014 the 2024-book spells are hidden, so Arcane Vigor (a 2024-only spell) is not offered; the
    2014 spells of the table still are."""
    res = resolve(_mark_draft("mark-of-healing-efa", [("cleric", 5, None)], ruleset="2014"), catalog)
    shown = {o["label"] for o in _card(res, "class:cleric:spells-known")["options"]}
    assert not any(x.startswith("Arcane Vigor") for x in shown)
    assert any(x.startswith("False Life") for x in shown)


@needs_data
def test_rp16_magical_secrets_cap_does_not_count_mark_spells(catalog):
    """A Mark spell is on the Bard's list for this character, so it is not a Magical Secrets (off-list) pick: with the
    two Magical Secrets picks used, the Mark options stay open while the other off-list options are closed."""
    base = _mark_draft("mark-of-healing-efa", [("bard", 10, None)])
    card = _card(resolve(base, catalog), "class:bard:spells-known")
    mark_only = [o for o in card["options"] if o["label"].endswith(MARK_LABEL)]
    assert mark_only and all("Magical Secrets" not in o["label"] for o in mark_only)
    secrets = [o["id"] for o in card["options"] if o["label"].endswith("(Magical Secrets)")]
    assert len(secrets) > 2
    base["classes"][0]["choices"]["class:bard:spells-known"] = secrets[:2]
    card = _card(resolve(base, catalog), "class:bard:spells-known")
    by_id = {o["id"]: o for o in card["options"]}
    assert all(not o.get("disabled") for o in card["options"] if o["label"].endswith(MARK_LABEL))
    assert by_id[secrets[2]].get("disabled")  # the cap is real: a third Magical Secret is closed


# ---------------------------------------------------------------- timing


@needs_data
def test_timing_stays_under_50_ms(catalog):
    cases = [
        _draft([("fighter", 20, None)], ["abjuration-adept-au"]),
        _draft([("wizard", 20, None)], ["abjuration-adept-au", "evocation-adept-au"]),
        _draft([("bard", 20, None)], ["illusion-adept-au"]),
        _mark_draft("mark-of-healing-efa", [("wizard", 20, None)], ruleset="2024"),
        _mark_draft("mark-of-storm-efa", [("bard", 20, None)]),
    ]
    for d in cases:
        resolve(d, catalog)
        laps = []
        for _ in range(10):
            t_run = time.perf_counter()
            resolve(d, catalog)
            laps.append(time.perf_counter() - t_run)
        assert_fast(laps)
