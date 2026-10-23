"""RP9 (C, E12): 2024 background starting equipment with real items and quantities, ruleset 2024 only.

Governing text: the `Equipment:` line of every ruleset-2024 background record (read from the 5etools
backgrounds file; the stripped line is read at test time, not copied here). It always has the shape
"Choose A or B: (A) <items>, <N> GP; or (B) 50 GP". Rules this slice implements:

  * quantities are kept ("2 Pouches", "5 Torches", "Parchment (10 sheets)", "Oil (5 flasks)", "2 Daggers");
  * "Robe" is the catalog `robes`; "20 Arrows" / "20 Bolts" are ONE `arrow` / `crossbow-bolt` (both catalog items
    are already 20-packs, F3a-6); "Iron Spikes" is the catalog `spike-iron` (weight 5 lb = the 10-pack);
  * "Holy Symbol" is a nested pick over the holy symbols (Amulet / Emblem / Reliquary), but "Holy Symbol
    (reliquary)" is the Reliquary; "Arcane Focus (Crystal or Wand)" is a nested pick narrowed to those two;
  * "Gaming Set / Artisan's Tools / Musical Instrument (same as above)" is the item of the background's own tool
    proficiency pick (sentinel `background-tool`, narrative label while unpicked); with no matching proficiency pick
    on the background (Carouser's data has none, Wayfarer says "(any)") it is a nested pick of that category;
  * "Map" has no catalog item (the catalog "Case, map or scroll" is a different item): a narrative item;
  * gold comes from the text when the data disagrees (Mulhorandi Tomb Raider: the data lost "26 GP" into a
    display name).

Cases: converter (60 backgrounds, text-driven: gold, quantities, no placeholder, B = 50 GP) | per-background items
(Acolyte, Soldier, Guard, Wayfarer, Artisan, Entertainer, Noble, Spellfire, Vampire Survivor, Mulhorandi,
Archaeologist, Carouser, Lords' Alliance, Shadowmasters) | resolve (inventory, nested cards, carried weight, gold,
narrative) | mixed and 2014 unchanged | ruleset switch | SRD-only and patched catalogs | strict converter."""
import json
import re

import pytest

from catalog import official_source
from catalog.loader import load
from catalog.official import background_equipment
from catalog.official_source import has_official, official_dir
from catalog import reference_data
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

SENTINEL = reference_data.BACKGROUND_TOOL_SENTINEL


@pytest.fixture(scope="module")
def catalog():
    return load()


def _bg_ids(catalog):
    return sorted(i for i, b in catalog.backgrounds.items() if b.get("ruleset") == "2024")


def _raw():
    with open(official_dir() / "backgrounds.json", encoding="utf-8") as f:
        return json.load(f)["background"]


def _line(catalog, bg_id):
    """The stripped `Equipment:` entry of the raw record behind a catalog background."""
    bg = catalog.backgrounds[bg_id]
    for raw in _raw():
        if raw["name"] == bg["name"] and raw.get("source") == bg["source"]:
            for item in raw["entries"][0]["items"]:
                if item["name"].startswith("Equipment"):
                    return re.sub(r"\{@\w+ ([^}]*)\}", lambda m: (m.group(1).split("|") + ["", ""])[2] or m.group(1).split("|")[0],
                                  item["entry"])
    raise AssertionError(bg_id)


def _options(catalog, bg_id):
    envelopes = catalog.backgrounds[bg_id]["starting_equipment_options_2024"]
    assert len(envelopes) == 1
    return envelopes[0], {o["items"][0]["of"]["index"] == "gp-50" and "B" or "A": o for o in envelopes[0]["from"]["options"]}


def _members(option):
    return [m for m in option["items"]]


def _ref(member):
    return member["of"]["index"] if member["option_type"] == "counted_reference" else "nested"


def _a_members(catalog, bg_id):
    _, opts = _options(catalog, bg_id)
    return _members(opts["A"])


def _draft(bg="soldier-xphb", ruleset="2024", eq=None, prof=None, cls="fighter", species="human-xphb"):
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
        "species": {"id": species}, "background": {"id": bg, "choices": dict(prof or {})},
        "equipment": {"choices": dict(eq or {}), "added": [], "skipped": False},
        "classes": [{"classId": cls, "level": 1, "choices": {}}],
    }


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _ecid(bg):
    return f"background:{bg}:equipment-choice-0"


def _pcid(bg):
    return f"background:{bg}:proficiency-choice-0"


def _option_id(res, bg, letter):
    card = _card(res, _ecid(bg))
    options = card["options"]
    return next(o["id"] for o in options if (o["id"].split("+")[-1] == "gp-50") == (letter == "B"))


def _pick_a(bg, catalog, prof=None, nested=None, ruleset="2024", species="human-xphb"):
    """Resolve with package A selected (and optional proficiency / nested picks); returns the result."""
    base = resolve(_draft(bg, ruleset, prof=prof, species=species), catalog)
    a = _option_id(base, bg, "A")
    eq = {_ecid(bg): [a]}
    for slot, value in (nested or {}).items():
        eq[f"{_ecid(bg)}:{slot}"] = [value]
    return resolve(_draft(bg, ruleset, eq=eq, prof=prof, species=species), catalog)


def _chosen(res):
    return {e["itemId"]: e["qty"] for e in res["sheet"]["equipment"]["chosen"]}


def _weight(catalog, chosen):
    return sum((catalog.items[i].get("weight") or 0) * q for i, q in chosen.items())


# ---- converter: text-driven over every ruleset-2024 background ---------------------------------------------------

def _text_a(line):
    seg = re.split(r"\(A\)", line, maxsplit=1)[1].split("; or (B)")[0].strip()
    gold = re.search(r",?\s*(?:and\s+)?(\d+) GP\s*$", seg)
    items = seg[:gold.start()] if gold else seg
    return [t.strip() for t in re.split(r",\s*", items) if t.strip()], int(gold.group(1)) if gold else None


def _text_qty(token):
    if re.match(r"20 (Arrows|Bolts)$", token):
        return 1  # one 20-pack catalog item
    lead = re.match(r"(\d+) ", token)
    paren = re.search(r"\((\d+) (?:flasks?|sheets?|days)", token) or re.search(r"\((\d+) (?:flasks?|sheets?)\)", token)
    if lead:
        return int(lead.group(1))
    return int(paren.group(1)) if paren else 1


@needs_data
def test_sixty_backgrounds_have_the_2024_envelope_and_the_old_key_is_untouched(catalog):
    ids = _bg_ids(catalog)
    assert len(ids) == 60
    for bg_id in ids:
        bg = catalog.backgrounds[bg_id]
        assert bg["starting_equipment_options_2024"], bg_id
        assert bg["starting_equipment_options"] and "keep_counts" not in bg["starting_equipment_options"][0]
    # the SRD Acolyte and the 2014 backgrounds have no 2024 key
    assert "starting_equipment_options_2024" not in catalog.backgrounds["acolyte"]


@needs_data
@pytest.mark.parametrize("letters", [("A", "B")])
def test_every_envelope_is_ab_keep_counts_and_b_is_fifty_gold(catalog, letters):
    for bg_id in _bg_ids(catalog):
        envelope, opts = _options(catalog, bg_id)
        assert envelope["keep_counts"] is True and envelope["type"] == "equipment" and envelope["choose"] == 1, bg_id
        assert set(opts) == set(letters), bg_id
        assert [_ref(m) for m in opts["B"]["items"]] == ["gp-50"], bg_id
        assert "Choose A or B" in envelope["desc"], bg_id


@needs_data
def test_every_a_package_matches_the_text_gold_quantities_and_has_no_placeholder(catalog):
    for bg_id in _bg_ids(catalog):
        tokens, gold = _text_a(_line(catalog, bg_id))
        members = _a_members(catalog, bg_id)
        gold_members = [m for m in members if _ref(m).startswith("gp-")]
        item_members = [m for m in members if not _ref(m).startswith("gp-")]
        assert [m["of"]["index"] for m in gold_members] == ([f"gp-{gold}"] if gold else []), (bg_id, gold)
        assert len(item_members) == len(tokens), (bg_id, tokens, [_ref(m) for m in item_members])
        assert [m.get("count", 1) for m in item_members] == [_text_qty(t) for t in tokens], (bg_id, tokens)
        for m in item_members:
            ref = _ref(m)
            assert not ref.startswith(("unlisted-", "category-")), (bg_id, ref)
            assert not ref.startswith("flavor-") or ref == "flavor-map", (bg_id, ref)
            assert ref in ("nested", SENTINEL, "flavor-map") or ref in catalog.items, (bg_id, ref)


@needs_data
def test_scribe_data_lost_its_quantities_the_text_wins_and_the_display_names_agree_elsewhere(catalog):
    assert dict(_summary(catalog, "scribe-xphb"))["oil-flask"] == 3
    assert dict(_summary(catalog, "scribe-xphb"))["parchment-one-sheet"] == 12
    # without the text line the data-only fallback (quantity / display name) gives the same counts for all but Scribe
    for bg_id in _bg_ids(catalog):
        bg = catalog.backgrounds[bg_id]
        raw = next(r for r in _raw() if r["name"] == bg["name"] and r.get("source") == bg["source"])
        bare = background_equipment.starting_equipment_options_2024_from_5etools(
            {**raw, "entries": []}, bg["starting_proficiency_choices"])
        have = [(m["of"]["index"], m.get("count", 1)) for m in bare[0]["from"]["options"][0]["items"]
                if m["option_type"] == "counted_reference" and not m["of"]["index"].startswith("gp-")]
        want = [(m["of"]["index"], m.get("count", 1)) for m in _a_members(catalog, bg_id)
                if m["option_type"] == "counted_reference" and not m["of"]["index"].startswith("gp-")]
        if bg_id != "scribe-xphb":
            assert have == want, bg_id


@needs_data
def test_gold_table_every_background_text_wins(catalog):
    expected = {"mulhorandi-tomb-raider-frhof": 26, "soldier-xphb": 14, "acolyte-xphb": 8, "artisan-xphb": 32,
                "house-deneith-heir-efa": 1, "haunted-one-rhw": 14, "mist-wanderer-rhw": 30}
    for bg_id, gold in expected.items():
        assert f"gp-{gold}" in [_ref(m) for m in _a_members(catalog, bg_id)], bg_id


@needs_data
def test_the_mulhorandi_data_defect_is_documented_and_fixed(catalog):
    # the data glued "26 GP" into a display name and carries no gold value: the text wins
    members = _a_members(catalog, "mulhorandi-tomb-raider-frhof")
    assert [m for m in members if _ref(m) == "waterskin"][0]["of"]["name"] == catalog.items["waterskin"]["name"]
    assert "gp-26" in [_ref(m) for m in members]
    old = catalog.backgrounds["mulhorandi-tomb-raider-frhof"]["starting_equipment_options"][0]["from"]["options"][0]["items"]
    assert not any(m["of"]["index"].startswith("gp-") for m in old)  # the old key (untouched) lost it


# ---- converter: the item rules -----------------------------------------------------------------------------------

def _summary(catalog, bg_id):
    return [(_ref(m), m.get("count", 1)) for m in _a_members(catalog, bg_id) if not _ref(m).startswith("gp-")]


@needs_data
def test_acolyte_a_quantities_robe_and_holy_symbol_pick(catalog):
    s = _summary(catalog, "acolyte-xphb")
    assert s == [("book", 1), ("calligraphers-supplies", 1), ("nested", 1), ("parchment-one-sheet", 10), ("robes", 1)]
    nested = [m for m in _a_members(catalog, "acolyte-xphb") if m["option_type"] == "choice"][0]["choice"]
    assert nested["from"]["equipment_category"]["index"] == "holy-symbols"


@needs_data
def test_arrows_bolts_and_iron_spikes_are_single_catalog_packs(catalog):
    assert ("arrow", 1) in _summary(catalog, "soldier-xphb") and ("arrow", 1) in _summary(catalog, "guide-xphb")
    assert ("crossbow-bolt", 1) in _summary(catalog, "guard-xphb")
    assert ("spike-iron", 1) in _summary(catalog, "shadowmasters-exile-frhof")
    assert catalog.items["arrow"]["quantity"] == 20 and catalog.items["crossbow-bolt"]["quantity"] == 20
    assert catalog.items["spike-iron"]["weight"] == 5


@needs_data
def test_bundle_quantities_pouches_torches_oil_daggers(catalog):
    assert dict(_summary(catalog, "criminal-xphb"))["dagger"] == 2 and dict(_summary(catalog, "criminal-xphb"))["pouch"] == 2
    assert dict(_summary(catalog, "dragon-cultist-frhof"))["oil-flask"] == 5
    assert dict(_summary(catalog, "mulhorandi-tomb-raider-frhof"))["torch"] == 5
    assert dict(_summary(catalog, "lords-alliance-vassal-frhof"))["parchment-one-sheet"] == 9
    assert dict(_summary(catalog, "lords-alliance-vassal-frhof"))["javelin"] == 2
    assert dict(_summary(catalog, "chondathan-freebooter-frhof"))["rations-1-day"] == 3


@needs_data
@pytest.mark.parametrize("bg_id", ["soldier-xphb", "guard-xphb", "noble-xphb", "artisan-xphb", "entertainer-xphb",
                                   "house-deneith-heir-efa", "house-tharashk-heir-efa", "house-thuranni-heir-efa",
                                   "house-agent-efa", "house-cannith-heir-efa", "haunted-one-rhw", "mist-wanderer-rhw",
                                   "spellfire-initiate-frhof", "spirit-medium-rhw"])
def test_same_as_above_members_are_the_sentinel(catalog, bg_id):
    assert SENTINEL in [r for r, _ in _summary(catalog, bg_id)]
    # the background really has the matching tool proficiency pick the sentinel reads
    assert catalog.backgrounds[bg_id]["starting_proficiency_choices"][0]["from"]["option_set_type"] == "any_tool"


@needs_data
@pytest.mark.parametrize("bg_id,category", [("wayfarer-xphb", "gaming-sets"), ("carouser-abh", "gaming-sets")])
def test_no_matching_proficiency_pick_gives_a_nested_category_pick(catalog, bg_id, category):
    assert SENTINEL not in [r for r, _ in _summary(catalog, bg_id)]
    nested = [m for m in _a_members(catalog, bg_id) if m["option_type"] == "choice"]
    assert len(nested) == 1 and nested[0]["choice"]["from"]["equipment_category"]["index"] == category


@needs_data
def test_holy_symbol_reliquary_is_direct_and_arcane_focus_is_narrowed(catalog):
    assert ("reliquary", 1) in _summary(catalog, "vampire-survivor-abh")
    assert not [m for m in _a_members(catalog, "vampire-survivor-abh") if m["option_type"] == "choice"]
    spellfire = [m for m in _a_members(catalog, "spellfire-initiate-frhof") if m["option_type"] == "choice"]
    assert len(spellfire) == 1 and spellfire[0]["choice"]["from"]["equipment_category"]["index"] == "arcane-foci"
    assert spellfire[0]["choice"]["from"]["only"] == ["crystal", "wand"]
    knight = [m for m in _a_members(catalog, "knight-of-the-gauntlet-frhof") if m["option_type"] == "choice"]
    assert knight[0]["choice"]["from"]["equipment_category"]["index"] == "holy-symbols"


@needs_data
def test_map_has_no_catalog_item_and_is_narrative_the_case_stays_an_item(catalog):
    for bg_id in ("archaeologist-efa", "house-orien-heir-efa"):
        s = _summary(catalog, bg_id)
        assert ("flavor-map", 1) in s and ("case-map-or-scroll", 1) in s
    # mixed keeps its old key (the catalog "Case, map or scroll" twice); not our business
    old = [m["of"]["index"] for m in catalog.backgrounds["archaeologist-efa"]["starting_equipment_options"][0]["from"]["options"][0]["items"]]
    assert old.count("case-map-or-scroll") == 2  # the old key matched "map" to the case too; it stays as it was


# ---- resolve: ruleset 2024 ---------------------------------------------------------------------------------------

@needs_data
def test_acolyte_a_inventory_quantities_gold_and_weight(catalog):
    res = _pick_a("acolyte-xphb", catalog)
    nested = _card(res, _ecid("acolyte-xphb") + ":0")
    assert nested is not None and nested["status"] == "pending"
    assert [o["id"] for o in nested["options"]] == ["amulet", "emblem", "reliquary"]
    res = _pick_a("acolyte-xphb", catalog, nested={0: "emblem"})
    chosen = _chosen(res)
    assert chosen == {"calligraphers-supplies": 1, "book": 1, "emblem": 1, "parchment-one-sheet": 10, "robes": 1}
    assert res["sheet"]["startingGold"] == 8
    assert res["sheet"]["equipment"]["narrativeItems"] == []
    assert res["derived"]["carryingCapacity"]["carried"] == _weight(catalog, chosen)


@needs_data
def test_soldier_a_gaming_set_is_the_proficiency_pick_and_arrows_are_one_pack(catalog):
    unpicked = _pick_a("soldier-xphb", catalog)
    assert "dice-set" not in _chosen(unpicked)
    assert any("Gaming Set" in n for n in unpicked["sheet"]["equipment"]["narrativeItems"])
    res = _pick_a("soldier-xphb", catalog, prof={_pcid("soldier-xphb"): ["playing-card-set"]})
    chosen = _chosen(res)
    assert chosen == {"spear": 1, "shortbow": 1, "arrow": 1, "playing-card-set": 1, "healers-kit": 1, "quiver": 1,
                      "clothes-travelers": 1}
    assert not any("Gaming Set" in n for n in res["sheet"]["equipment"]["narrativeItems"])
    assert res["sheet"]["startingGold"] == 14
    assert res["derived"]["carryingCapacity"]["carried"] == _weight(catalog, chosen)


@needs_data
def test_guard_bolts_artisan_and_entertainer_tools(catalog):
    guard = _pick_a("guard-xphb", catalog, prof={_pcid("guard-xphb"): ["dice-set"]})
    assert _chosen(guard)["crossbow-bolt"] == 1 and _chosen(guard)["dice-set"] == 1 and _chosen(guard)["crossbow-light"] == 1
    artisan = _pick_a("artisan-xphb", catalog, prof={_pcid("artisan-xphb"): ["smiths-tools"]})
    assert _chosen(artisan) == {"smiths-tools": 1, "pouch": 2, "clothes-travelers": 1}
    assert artisan["sheet"]["startingGold"] == 32
    ent = _pick_a("entertainer-xphb", catalog, prof={_pcid("entertainer-xphb"): ["lute"]})
    assert _chosen(ent)["lute"] == 1 and _chosen(ent)["clothes-costume"] == 2


@needs_data
def test_changing_the_proficiency_pick_changes_the_item(catalog):
    a = _chosen(_pick_a("soldier-xphb", catalog, prof={_pcid("soldier-xphb"): ["dice-set"]}))
    b = _chosen(_pick_a("soldier-xphb", catalog, prof={_pcid("soldier-xphb"): ["playing-card-set"]}))
    assert "dice-set" in a and "playing-card-set" not in a and "playing-card-set" in b and "dice-set" not in b


@needs_data
def test_wayfarer_gaming_set_is_a_nested_card_with_the_catalog_sets(catalog):
    res = _pick_a("wayfarer-xphb", catalog)
    nested = _card(res, _ecid("wayfarer-xphb") + ":0")
    assert nested is not None and [o["id"] for o in nested["options"]] == ["dice-set", "playing-card-set"]
    res = _pick_a("wayfarer-xphb", catalog, nested={0: "dice-set"})
    assert _chosen(res)["dagger"] == 2 and _chosen(res)["pouch"] == 2 and _chosen(res)["dice-set"] == 1
    assert res["sheet"]["startingGold"] == 16


@needs_data
def test_spellfire_arcane_focus_card_only_offers_crystal_and_wand(catalog):
    res = _pick_a("spellfire-initiate-frhof", catalog, prof={_pcid("spellfire-initiate-frhof"): ["dice-set"]})
    nested = _card(res, _ecid("spellfire-initiate-frhof") + ":0")
    assert [o["id"] for o in nested["options"]] == ["crystal", "wand"]
    res = _pick_a("spellfire-initiate-frhof", catalog, prof={_pcid("spellfire-initiate-frhof"): ["dice-set"]}, nested={0: "wand"})
    assert _chosen(res) == {"dice-set": 1, "wand": 1, "pouch": 2, "clothes-travelers": 1}


@needs_data
def test_vampire_survivor_reliquary_and_archaeologist_map_narrative(catalog):
    chosen = _chosen(_pick_a("vampire-survivor-abh", catalog))
    assert chosen["reliquary"] == 1 and chosen["oil-flask"] == 3 and chosen["holy-water-flask"] == 1
    arch = _pick_a("archaeologist-efa", catalog)
    assert "Map" in arch["sheet"]["equipment"]["narrativeItems"] and _chosen(arch)["case-map-or-scroll"] == 1


@needs_data
def test_mulhorandi_gold_and_shadowmasters_spikes(catalog):
    res = _pick_a("mulhorandi-tomb-raider-frhof", catalog)
    assert res["sheet"]["startingGold"] == 26 and _chosen(res)["torch"] == 5 and _chosen(res)["pouch"] == 2
    shadow = _pick_a("shadowmasters-exile-frhof", catalog)
    assert _chosen(shadow)["spike-iron"] == 1 and _chosen(shadow)["dagger"] == 2 and shadow["sheet"]["startingGold"] == 3


@needs_data
def test_carouser_gaming_set_is_a_nested_pick_because_the_data_has_no_proficiency_card(catalog):
    res = _pick_a("carouser-abh", catalog, nested={0: "dice-set"})
    assert _chosen(res)["dice-set"] == 1 and _chosen(res)["bottle-glass"] == 1


@needs_data
def test_package_b_is_still_fifty_gold_and_nothing_else(catalog):
    base = resolve(_draft("acolyte-xphb"), catalog)
    res = resolve(_draft("acolyte-xphb", eq={_ecid("acolyte-xphb"): [_option_id(base, "acolyte-xphb", "B")]}), catalog)
    assert _chosen(res) == {} and res["sheet"]["startingGold"] == 50


@needs_data
def test_an_unpicked_package_gives_nothing_and_a_pending_card(catalog):
    res = resolve(_draft("soldier-xphb"), catalog)
    card = _card(res, _ecid("soldier-xphb"))
    assert card["status"] == "pending" and _chosen(res) == {}
    acolyte = _card(resolve(_draft("acolyte-xphb"), catalog), _ecid("acolyte-xphb"))
    assert any(o.get("quantities", {}).get("parchment-one-sheet") == 10 for o in acolyte["options"])


# ---- mixed / 2014 unchanged, ruleset switch ----------------------------------------------------------------------

@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_keep_the_old_envelope_with_qty_one(catalog, ruleset):
    res = _pick_a("acolyte-xphb", catalog, ruleset=ruleset)
    card = _card(res, _ecid("acolyte-xphb"))
    a = next(o for o in card["options"] if not o["id"].endswith("gp-50"))
    assert "unlisted-holy-symbol" in a["id"] and "unlisted-robe" in a["id"] and "quantities" not in a
    assert _card(res, _ecid("acolyte-xphb") + ":0") is None
    assert _chosen(res) == {"calligraphers-supplies": 1, "book": 1, "parchment-one-sheet": 1}
    assert set(res["sheet"]["equipment"]["narrativeItems"]) == {"Holy Symbol", "Robe"}
    assert res["sheet"]["startingGold"] == 8


@needs_data
def test_ruleset_switch_keeps_the_b_pick_and_a_package_without_placeholders(catalog):
    for bg_id in ("acolyte-xphb", "criminal-xphb"):
        base = resolve(_draft(bg_id), catalog)
        b = _option_id(base, bg_id, "B")
        res = resolve(_draft(bg_id, "mixed", eq={_ecid(bg_id): [b]}), catalog)
        assert _card(res, _ecid(bg_id))["selected"] == [b] and res["sheet"]["startingGold"] == 50
    base = resolve(_draft("criminal-xphb"), catalog)
    a = _option_id(base, "criminal-xphb", "A")
    res = resolve(_draft("criminal-xphb", "mixed", eq={_ecid("criminal-xphb"): [a]}), catalog)
    assert _card(res, _ecid("criminal-xphb"))["selected"] == [a]  # same option id in both rulesets


@needs_data
def test_exactly_these_backgrounds_get_another_package_a_id_than_before(catalog):
    from catalog.choices import build_equipment_choice

    def ids(envelope):
        return [o["id"] for o in build_equipment_choice(envelope, "x", {}, "l", catalog.items)[0]["options"]]

    changed = {i for i in _bg_ids(catalog) if ids(catalog.backgrounds[i]["starting_equipment_options"][0])
               != ids(catalog.backgrounds[i]["starting_equipment_options_2024"][0])}
    placeholders = {i for i in _bg_ids(catalog) if any(
        m["of"]["index"].startswith(("unlisted-", "category-"))
        for o in catalog.backgrounds[i]["starting_equipment_options"][0]["from"]["options"] for m in o["items"])}
    assert len(placeholders) == 26 and len(changed) == 29
    assert changed - placeholders == {"archaeologist-efa", "house-orien-heir-efa", "mulhorandi-tomb-raider-frhof"}
    assert placeholders <= changed


@needs_data
def test_ruleset_switch_with_a_placeholder_package_is_a_nonblocking_stale_pick(catalog):
    # Acolyte A has other ids under 2024 (robes, a nested holy symbol), so the stored A is not an option under mixed
    base = resolve(_draft("acolyte-xphb"), catalog)
    a = _option_id(base, "acolyte-xphb", "A")
    res = resolve(_draft("acolyte-xphb", "mixed", eq={_ecid("acolyte-xphb"): [a]}), catalog)
    card = _card(res, _ecid("acolyte-xphb"))
    assert card["selected"] == [] and card["status"] == "pending"
    assert not [p for p in res.get("problems", []) if p.get("blocking")]


# ---- catalog degradation / strictness -----------------------------------------------------------------------------

def test_srd_only_catalog_has_no_2024_key_and_resolves(monkeypatch, tmp_path):
    monkeypatch.setattr(official_source, "official_dir", lambda: tmp_path)
    cat = load()
    assert "starting_equipment_options_2024" not in cat.backgrounds["acolyte"]
    res = resolve(_draft("acolyte", species="human"), cat)
    assert _card(res, _ecid("acolyte")) is not None


@needs_data
def test_patched_catalog_without_gaming_sets_drops_only_the_option_that_needs_them(catalog):
    patched = load()
    for k in ("dice-set", "playing-card-set"):
        patched.items.pop(k)
    res = resolve(_draft("wayfarer-xphb"), patched)
    card = _card(res, _ecid("wayfarer-xphb"))
    assert card is not None and [o["id"] for o in card["options"]] == ["gp-50"]
    res = resolve(_draft("criminal-xphb"), patched)
    assert len(_card(res, _ecid("criminal-xphb"))["options"]) == 2


def test_unmapped_member_raises():
    raw = {"name": "X", "source": "XPHB", "edition": "one", "startingEquipment": [{"A": ["frobnicator|xphb", {"value": 100}], "B": [{"value": 5000}]}], "entries": []}
    with pytest.raises(ValueError):
        background_equipment.starting_equipment_options_2024_from_5etools(raw, [])
