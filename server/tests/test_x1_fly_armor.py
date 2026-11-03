"""X1: a flying speed that the species text bans in armor is unusable while the counted body armor is of a banned category.

Rule matrix (catalog text, tags stripped; one row per record, quoted verbatim in ``FLY_ARMOR_BAN``):

  aarakocra-eepc-trait-3   "To use this speed, you can't be wearing medium or heavy armor."
  aarakocra-mpmm-trait-0   "You can't use this flying speed if you're wearing medium or heavy armor."
  aven-psa-trait-3 / -psd  "You can't use your flying speed while you wear medium or heavy armor."
  fairy-mpmm / fairy-wbtw  "You can't use this flying speed if you're wearing medium or heavy armor."
  owlin-scc-trait-2        "You can't use this flying speed if you're wearing medium or heavy armor."
  siren-psx-trait-3        "You can't use your flying speed while you wear medium or heavy armor."
  winged tiefling (SCAG)   "You have a flying speed of 30 feet while you aren't wearing heavy armor."  (HEAVY only)

Medium or Heavy BODY armor (the suit AC counts, WH) removes the fly mode and raises a non-blocking warning; Light armor,
a shield alone, an explicit ``worn.armor: null`` and armor in the pack leave it. Species without such text are unaffected.
"""
from __future__ import annotations

from perf_helpers import assert_fast
import re
import time

import pytest

from catalog import reference_data as ref
from catalog.loader import load
from catalog.official_source import has_official
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not has_official(), reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")

# trait id -> (species id, subspecies id or None, categories banned, sentence that must be in the catalog text)
RECORDS = {
    "aarakocra-eepc-trait-3": ("aarakocra-eepc", None, ("Medium", "Heavy"),
                               "To use this speed, you can't be wearing medium or heavy armor."),
    "aarakocra-mpmm-trait-0": ("aarakocra-mpmm", None, ("Medium", "Heavy"),
                               "You can't use this flying speed if you're wearing medium or heavy armor."),
    "aven-psa-trait-3": ("aven-psa", None, ("Medium", "Heavy"),
                         "You can't use your flying speed while you wear medium or heavy armor."),
    "aven-psd-trait-3": ("aven-psd", None, ("Medium", "Heavy"),
                         "You can't use your flying speed while you wear medium or heavy armor."),
    "fairy-mpmm-trait-2": ("fairy-mpmm", None, ("Medium", "Heavy"),
                           "You can't use this flying speed if you're wearing medium or heavy armor."),
    "fairy-wbtw-trait-1": ("fairy-wbtw", None, ("Medium", "Heavy"),
                           "You can't use this flying speed if you're wearing medium or heavy armor."),
    "owlin-scc-trait-2": ("owlin-scc", None, ("Medium", "Heavy"),
                          "You can't use this flying speed if you're wearing medium or heavy armor."),
    "siren-psx-trait-3": ("siren-psx", None, ("Medium", "Heavy"),
                          "You can't use your flying speed while you wear medium or heavy armor."),
    "tiefling-phb-variant;-winged-scag-trait-1": ("tiefling-phb", "tiefling-phb-variant;-winged-scag", ("Heavy",),
                                                  "You have a flying speed of 30 feet while you aren't wearing heavy armor."),
}
LIGHT, MEDIUM_ARMORS, HEAVY_ARMORS = "leather-armor", ("chain-shirt", "half-plate-armor", "breastplate"), ("chain-mail", "plate-armor")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _plain(node):
    text = " ".join(node) if isinstance(node, list) else str(node)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\s+", " ", re.sub(r"\{@(\w+) ([^}]*)\}", tag, text))


def _res(catalog, species="aarakocra-mpmm", sub=None, ruleset="mixed", added=(), worn=None, cls="fighter", level=5, base=None):
    scores = {a: 10 for a in ABS}
    scores["STR"] = 18  # no heavy-armor speed penalty in these cases
    scores.update(base or {})
    sp = {"id": species, "choices": {}}
    if sub:
        sp["subspeciesId"] = sub
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": {}}],
         "background": {"id": "acolyte", "choices": {}}, "species": sp,
         "abilities": {"method": "manual", "base": scores},
         "equipment": {"choices": {}, "added": [{"itemId": i, "qty": 1, "equipped": True} for i in added], "skipped": True},
         "details": {}, "preferences": {}}
    if worn is not None:
        d["equipment"]["worn"] = worn
    return resolve(d, catalog)


def _speeds(r):
    return r["derived"]["speeds"]


def _ids(r):
    return [w["id"] for w in r["warnings"]]


def _fly_warnings(r):
    return [w for w in r["warnings"] if w["id"].startswith("fly-armor-")]


# ---------------------------------------------------------------- data pins

@pytest.mark.parametrize("trait_id", list(RECORDS))
def test_each_record_quote_matches_the_catalog_text(catalog, trait_id):
    species, sub, categories, sentence = RECORDS[trait_id]
    assert sentence in _plain(catalog.traits[trait_id]["desc"]), trait_id
    entry = ref.FLY_ARMOR_BAN[trait_id]
    assert entry["quote"] == sentence
    assert tuple(entry["categories"]) == categories
    assert entry["race"] == species
    assert entry.get("subrace") == sub
    assert trait_id in [t["index"] for t in (catalog.subraces[sub] if sub else catalog.races[species]).get(
        "racial_traits" if sub else "traits")]


def test_the_table_is_exactly_the_catalog_traits_that_ban_flying_in_armor(catalog):
    pattern = re.compile(r"(?:can't|cannot) use (?:this|your) fl\w+ speed|fl\w+ speed of \d+ feet while you aren't wearing "
                         r"heavy armor|to use this speed, you can't be wearing", re.I)
    found = {tid for tid, t in catalog.traits.items() if pattern.search(_plain(t.get("desc", [])))}
    assert found == set(RECORDS) == set(ref.FLY_ARMOR_BAN), found ^ set(RECORDS)


def test_every_species_with_a_fly_mode_is_in_the_table_or_listed_without_the_text(catalog):
    fliers = {rid for rid, r in catalog.races.items() if (r.get("movement") or {}).get("fly")}
    fliers |= {sid for sid, s in catalog.subraces.items() if (s.get("movement") or {}).get("fly")}
    banned = {e.get("subrace") or e["race"] for e in ref.FLY_ARMOR_BAN.values()}
    # aarakocra-dmg: fly 50 with no Flight trait in the catalog (its three traits say nothing about armor): not banned.
    assert fliers - banned == {"aarakocra-dmg"}, fliers - banned
    assert not any("armor" in _plain(catalog.traits[t["index"]]["desc"]).lower() for t in catalog.races["aarakocra-dmg"]["traits"])


# ---------------------------------------------------------------- behavior, every record

@pytest.mark.parametrize("trait_id", list(RECORDS))
def test_light_armor_and_no_armor_keep_the_fly_speed(catalog, trait_id):
    species, sub, _c, _s = RECORDS[trait_id]
    for added in ((), (LIGHT,)):
        r = _res(catalog, species, sub, added=added)
        assert _speeds(r).get("fly"), (trait_id, added, _speeds(r))
        assert not _fly_warnings(r)


@pytest.mark.parametrize("trait_id", list(RECORDS))
def test_banned_categories_remove_the_fly_speed_and_warn(catalog, trait_id):
    species, sub, categories, _s = RECORDS[trait_id]
    armors = {"Medium": MEDIUM_ARMORS, "Heavy": HEAVY_ARMORS}
    for category, items in armors.items():
        for item in items:
            r = _res(catalog, species, sub, added=[item])
            if category in categories:
                assert "fly" not in _speeds(r), (trait_id, item)
                assert len(_fly_warnings(r)) == 1, (trait_id, item)
            else:
                assert _speeds(r).get("fly"), (trait_id, item)
                assert not _fly_warnings(r)


def test_warning_text_names_the_species_and_the_categories(catalog):
    msg = lambda r: _fly_warnings(r)[0]["message"]  # noqa: E731
    assert msg(_res(catalog, "aarakocra-mpmm", added=["chain-mail"])) == "Aarakocra flying speed unusable in medium/heavy armor."
    assert msg(_res(catalog, "fairy-mpmm", added=["half-plate-armor"])) == "Fairy flying speed unusable in medium/heavy armor."
    assert msg(_res(catalog, "owlin-scc", added=["plate-armor"])) == "Owlin flying speed unusable in medium/heavy armor."
    assert msg(_res(catalog, "tiefling-phb", "tiefling-phb-variant;-winged-scag", added=["plate-armor"])) \
        == "Winged Tiefling flying speed unusable in heavy armor."
    assert _fly_warnings(_res(catalog, "aarakocra-mpmm", added=["chain-mail"]))[0]["id"] == "fly-armor-aarakocra-mpmm"


# ---------------------------------------------------------------- shields, worn model, pack

def test_a_shield_alone_does_not_count(catalog):
    r = _res(catalog, added=["shield"])
    assert _speeds(r).get("fly") and not _fly_warnings(r)


def test_shield_with_medium_armor_still_removes_fly_once(catalog):
    r = _res(catalog, added=["half-plate-armor", "shield"])
    assert "fly" not in _speeds(r) and len(_fly_warnings(r)) == 1


def test_shield_with_light_armor_keeps_fly(catalog):
    r = _res(catalog, added=[LIGHT, "shield"])
    assert _speeds(r).get("fly") and not _fly_warnings(r)


def test_explicit_worn_armor_null_keeps_fly_even_with_armor_in_the_pack(catalog):
    r = _res(catalog, added=["plate-armor"], worn={"armor": None})
    assert _speeds(r).get("fly") and not _fly_warnings(r)


def test_explicit_worn_armor_pick_is_the_counted_suit(catalog):
    r = _res(catalog, added=["leather-armor", "chain-mail"], worn={"armor": "chain-mail"})
    assert "fly" not in _speeds(r)
    r = _res(catalog, added=["chain-mail", "leather-armor"], worn={"armor": "leather-armor"})
    assert _speeds(r).get("fly") and not _fly_warnings(r)


def test_two_suits_without_a_pick_follow_the_counted_first_suit(catalog):
    assert _speeds(_res(catalog, added=["leather-armor", "plate-armor"])).get("fly")  # leather counts
    assert "fly" not in _speeds(_res(catalog, added=["plate-armor", "leather-armor"]))


def test_unequipped_armor_in_the_pack_does_not_count(catalog):
    d = _res(catalog, added=[])
    r = resolve({**{"name": "t", "ruleset": "mixed", "sources": [], "classes": [{"classId": "fighter", "level": 5, "choices": {}}],
                    "background": {"id": "acolyte", "choices": {}}, "species": {"id": "fairy-mpmm", "choices": {}},
                    "abilities": {"method": "manual", "base": {a: 12 for a in ABS}},
                    "equipment": {"choices": {}, "added": [{"itemId": "plate-armor", "qty": 1, "equipped": False}], "skipped": True},
                    "details": {}, "preferences": {}}}, catalog)
    assert _speeds(d).get("fly") and _speeds(r).get("fly")


# ---------------------------------------------------------------- species without the ban, other modes, interplay

def test_species_without_the_ban_are_unaffected(catalog):
    for species in ("human", "dwarf", "tabaxi-mpmm", "aarakocra-dmg"):
        r = _res(catalog, species, added=["plate-armor"])
        assert not _fly_warnings(r), species
    # aarakocra-dmg: fly 50 and no armor sentence in its catalog traits: stays
    assert _speeds(_res(catalog, "aarakocra-dmg", added=["plate-armor"])).get("fly") == 50
    # other movement modes with an equal-to-walk fly source are not touched either (Aasimar has no fly mode here)
    assert "fly" not in _speeds(_res(catalog, "human", added=["plate-armor"]))


def test_other_modes_survive_a_banned_fly(catalog):
    r = _res(catalog, "tabaxi-mpmm", added=["plate-armor"])
    assert _speeds(r).get("climb") == _speeds(r)["walk"]  # Tabaxi climb (equal to walk) is not an X1 record
    r = _res(catalog, "aarakocra-eepc", added=["chain-mail"])
    assert _speeds(r)["walk"] == 25 and "fly" not in _speeds(r)


def test_fixed_fly_values_keep_their_number_when_allowed(catalog):
    assert _speeds(_res(catalog, "aarakocra-eepc"))["fly"] == 50
    assert _speeds(_res(catalog, "aven-psa"))["fly"] == 30
    assert _speeds(_res(catalog, "tiefling-phb", "tiefling-phb-variant;-winged-scag", added=["half-plate-armor"]))["fly"] == 30


def test_equal_to_walk_fly_follows_the_final_walk_when_allowed(catalog):
    # WF/W1 interplay: Fairy fly = final walk. Barbarian 5 Fast Movement +10 (no heavy armor), light armor: fly 40.
    r = _res(catalog, "fairy-mpmm", cls="barbarian", level=5, added=[LIGHT])
    assert _speeds(r)["walk"] == 40 and _speeds(r)["fly"] == 40


def test_banned_fly_is_removed_after_the_heavy_armor_speed_penalty(catalog):
    # plate with STR 10: walk 20 (W1) and fly gone (X1); both effects apply
    r = _res(catalog, "owlin-scc", added=["plate-armor"], base={"STR": 10})
    assert _speeds(r)["walk"] == 20 and "fly" not in _speeds(r)
    assert "armor-strength-plate-armor" in _ids(r) and len(_fly_warnings(r)) == 1


def test_heavy_armor_exempt_races_are_not_relevant_but_walk_is_untouched(catalog):
    r = _res(catalog, "fairy-mpmm", added=["half-plate-armor"])
    assert _speeds(r)["walk"] == 30  # medium armor has no Strength minimum: walk unchanged


def test_unarmored_movement_is_not_affected_by_the_ban(catalog):
    # Monk 5 unarmored: walk 40 (Fairy 30 + 10), fly equals walk (40)
    r = _res(catalog, "fairy-mpmm", cls="monk", level=5)
    assert _speeds(r)["walk"] == 40 and _speeds(r)["fly"] == 40


# ---------------------------------------------------------------- rulesets

@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_mixed_and_2014_apply_the_ban(catalog, ruleset):
    r = _res(catalog, "aarakocra-mpmm", ruleset=ruleset, added=["chain-mail"])
    assert "fly" not in _speeds(r) and len(_fly_warnings(r)) == 1
    assert _speeds(_res(catalog, "aarakocra-mpmm", ruleset=ruleset, added=[LIGHT])).get("fly")


def test_no_2024_species_has_a_fly_ban_record(catalog):
    for tid in ref.FLY_ARMOR_BAN:
        owner = ref.FLY_ARMOR_BAN[tid]
        rec = catalog.subraces[owner["subrace"]] if owner.get("subrace") else catalog.races[owner["race"]]
        assert rec.get("ruleset") == "2014", tid
    for rid, r in catalog.races.items():
        if r.get("ruleset") == "2024":
            assert not (r.get("movement") or {}).get("fly"), rid  # 2024 species with a fly mode would need their own check


def test_the_2024_ruleset_does_not_invent_a_ban(catalog):
    r = _res(catalog, "human", ruleset="2024", added=["plate-armor"])
    assert not _fly_warnings(r)


# ---------------------------------------------------------------- degradation and timing

def test_empty_ban_table_degrades(catalog, monkeypatch):
    monkeypatch.setattr(ref, "FLY_ARMOR_BAN", {})
    r = _res(catalog, "aarakocra-mpmm", added=["plate-armor"])
    assert _speeds(r).get("fly") and not _fly_warnings(r)


def test_ban_table_entry_without_the_catalog_trait_degrades(catalog, monkeypatch):
    monkeypatch.setattr(ref, "FLY_ARMOR_BAN", {"aarakocra-mpmm-trait-0": {**ref.FLY_ARMOR_BAN["aarakocra-mpmm-trait-0"],
                                                                         "race": "someone-else"}})
    assert _speeds(_res(catalog, "aarakocra-mpmm", added=["plate-armor"])).get("fly")


def test_resolve_timing_is_unchanged(catalog):
    _res(catalog, "aarakocra-mpmm", added=["plate-armor"])
    laps = []
    for _ in range(10):
        t_run = time.perf_counter()
        _res(catalog, "aarakocra-mpmm", added=["plate-armor"])
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
