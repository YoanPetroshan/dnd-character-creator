"""FE7: resistance, damage-type and variant picks of feats
(docs/superpowers/plans/2026-10-11-feat-effects.md). Each feat follows its own edition's text under every ruleset
(effects are keyed by feat index). Governing sentences (catalog text, tags stripped):

  Dragonscarred (FRHoF)    "choose Acid, Cold, Fire, Lightning, or Poison. You have Resistance to the chosen damage
                           type."                                        -> card ``:resistance-choice``, 1 of 5.
  Boon of Energy Resistance "You gain Resistance to two of the following damage types of your choice: Acid, Cold,
                           Fire, Lightning, Necrotic, Poison, Psychic, Radiant, or Thunder. Whenever you finish a
                           Long Rest, you can change your choices."      -> 2 of 9, an editable build-time card (F-D7);
                           Energy Redirection DC 8 + CON modifier + Proficiency Bonus in a note.
  Portal Jumper (AU)       "You have Resistance to one of the following damage types: Necrotic, Psychic, or Radiant
                           (choose when you select this feat)."         -> 1 of 3, plus the Portal Step resource.
  Spell Resistant (AU)     "You have Resistance to one of the following damage types (choose when you gain this
                           feat): Necrotic, Psychic, Radiant, or Thunder." -> 1 of 4, plus the Magic Resistant resource.
  Scion of the Outer Planes "Your choice gives you resistance to a damage type and the ability to cast a cantrip, as
                           specified in the table."                      -> no extra card: the resistance follows the
                           ``:spell-variant`` pick (Chaotic poison, Evil necrotic, Good radiant, Lawful force,
                           Outlands psychic; the table of the feat itself).
  Elemental Adept          PHB "Each time you do so, you must choose a different damage type."; XPHB "you must choose
                           a different damage type each time for Energy Mastery." -> ``:damage-type``; a repeat
                           cannot take a type already chosen for another instance (both editions share the group).
  Strike of the Giants (BGG) "choose one of the benefits listed below." (Cloud, Fire, Frost, Hill, Stone, Storm
                           Strike)                                       -> ``:giant-type``; the picked strike's
                           text is a note, and the resource note names it.

Matrix: feat x pick (damage type reaches ``damageModifiers.resistances``) x origin (background, species, Fighting
Style, Lessons, ASI; the three origins no shipped FE7 feat reaches are covered by patching the effect table) x
stale / duplicate pick x edit (F-D7: changing the pick changes the sheet) x pending card blocks export x no-feat
identity x empty catalog x timing."""
import copy
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_effects as fe
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FE7 = ("dragonscarred-frhof", "boon-of-energy-resistance-xphb", "portal-jumper-au", "spell-resistant-au",
       "scion-of-the-outer-planes-sato", "elemental-adept-phb", "elemental-adept-xphb", "strike-of-the-giants-bgg")
PLANES = {"chaotic-outer-plane": "poison", "evil-outer-plane": "necrotic", "good-outer-plane": "radiant",
          "lawful-outer-plane": "force", "the-outlands": "psychic"}


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
           base=None, sources=None):
    scores = {a: 10 for a in ABS}
    scores.update(base or {})
    return {"name": "t", "ruleset": ruleset, "sources": sources or [],
            "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
            "background": {"id": background, "choices": bg_choices or {}},
            "species": {"id": species, "choices": species_choices or {}},
            "abilities": {"method": "manual", "base": scores},
            "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {}, "preferences": {}}


def _asi(cls, slots_feats, **picks):
    """ASI choices: {level: feat index}; picks are full cids."""
    out = {f"class:{cls}:{lvl}:asi": [f"feat:{feat}"] for lvl, feat in slots_feats.items()}
    out.update(picks)
    return out


def _card(r, cid):
    return next((c for c in r["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _resists(r):
    return r["sheet"]["damageModifiers"]["resistances"]


def _notes(r, feat):
    return next(f.get("notes", []) for f in r["sheet"]["feats"] if f["id"] == feat)


def _pending_cards(r):
    from app import _pending_export_problems
    return [p for p in _pending_export_problems(r)]


def fighter(catalog, slots_feats, picks=None, level=None, **kw):
    level = level or max(slots_feats)
    ch = _asi("fighter", slots_feats, **(picks or {}))
    return resolve(_draft([("fighter", level, ch)], **kw), catalog)


# ---------------------------------------------------------------- data


@pytest.mark.parametrize("index", FE7)
def test_quote_matches_catalog_text(catalog, index):
    assert index in fed.FEAT_EFFECTS and index not in fed.FEAT_PENDING
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    text = _plain(catalog.feats[index]["entries"])
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in text, (index, quote)


def test_scion_table_in_the_data_is_the_feats_own_table(catalog):
    rows = next(e for e in catalog.feats["scion-of-the-outer-planes-sato"]["entries"]
                if isinstance(e, dict) and e.get("type") == "table")["rows"]
    slug = lambda name: re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")  # noqa: E731
    assert {slug(r[0]): r[1].lower() for r in rows} == fed.FEAT_EFFECTS["scion-of-the-outer-planes-sato"]["resist_by_variant"]
    assert set(fed.FEAT_EFFECTS["scion-of-the-outer-planes-sato"]["resist_by_variant"]) == \
        {slug(v) for v in catalog.feats["scion-of-the-outer-planes-sato"]["spell_variants"]}


def test_resistance_option_lists_match_the_feat_texts(catalog):
    e = fed.FEAT_EFFECTS
    assert e["dragonscarred-frhof"]["resist_choice"] == {"count": 1, "options": ["acid", "cold", "fire", "lightning", "poison"]}
    assert e["boon-of-energy-resistance-xphb"]["resist_choice"]["count"] == 2
    assert e["boon-of-energy-resistance-xphb"]["resist_choice"]["options"] == [
        "acid", "cold", "fire", "lightning", "necrotic", "poison", "psychic", "radiant", "thunder"]
    assert e["portal-jumper-au"]["resist_choice"]["options"] == ["necrotic", "psychic", "radiant"]
    assert e["spell-resistant-au"]["resist_choice"]["options"] == ["necrotic", "psychic", "radiant", "thunder"]
    for index in ("elemental-adept-phb", "elemental-adept-xphb"):
        assert e[index]["damage_type_choice"] == {"options": ["acid", "cold", "fire", "lightning", "thunder"],
                                                  "distinct_across_repeats": True}
    giants = [o["id"] for o in e["strike-of-the-giants-bgg"]["variant_choice"]["options"]]
    assert giants == ["cloud", "fire", "frost", "hill", "stone", "storm"]


def test_every_fe7_note_template_renders(catalog):
    numbers = fe.numbers_for({a: 2 for a in ABS}, {a: 14 for a in ABS}, 3, 8)
    for index in FE7:
        entry = fed.FEAT_EFFECTS[index]
        for text in entry.get("notes", []) + [o["note"] for o in (entry.get("variant_choice") or {}).get("options", [])] + \
                [r["note"] for r in entry.get("resources", []) if r.get("note")]:
            for pick in ("Fire", None):
                out = fe.render(text, fe._env({"increased": None, "pick_text": pick}, numbers))
                assert out and "{" not in out, (index, text)


# ---------------------------------------------------------------- resistance cards


def test_dragonscarred_offers_five_types_and_the_pick_reaches_the_sheet(catalog):
    base = fighter(catalog, {4: "dragonscarred-frhof"})
    card = _card(base, "class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice")
    assert card["source"]["kind"] == "feat" and card["count"] == 1 and card["status"] == "pending"
    assert [o["id"] for o in card["options"]] == ["acid", "cold", "fire", "lightning", "poison"]
    assert _resists(base) == []
    r = fighter(catalog, {4: "dragonscarred-frhof"},
                {"class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice": ["fire"]})
    assert _resists(r) == ["fire"]
    assert _card(r, card["id"])["status"] == "resolved"
    assert next(f for f in r["sheet"]["feats"] if f["id"] == "dragonscarred-frhof")["choice"]
    assert any("Fire" in n for n in _notes(r, "dragonscarred-frhof"))


def test_the_card_is_stripped_of_its_internal_flags_and_has_no_template_leak(catalog):
    r = fighter(catalog, {4: "elemental-adept-xphb"})
    card = _card(r, "class:fighter:4:asi:feat:elemental-adept-xphb:damage-type")
    assert "distinctGroup" not in card


def test_boon_of_energy_resistance_is_two_of_nine_and_editable(catalog):
    cid = "class:fighter:19:asi:feat:boon-of-energy-resistance-xphb:resistance-choice"
    r = fighter(catalog, {19: "boon-of-energy-resistance-xphb"}, {cid: ["fire", "cold"]}, ruleset="2024", level=19)
    card = _card(r, cid)
    assert card["count"] == 2 and len(card["options"]) == 9 and card["status"] == "resolved"
    assert set(_resists(r)) == {"fire", "cold"}
    # F-D7: "Whenever you finish a Long Rest, you can change your choices" -> the card stays editable
    r2 = fighter(catalog, {19: "boon-of-energy-resistance-xphb"}, {cid: ["radiant", "thunder"]}, ruleset="2024", level=19)
    assert set(_resists(r2)) == {"radiant", "thunder"}
    one = fighter(catalog, {19: "boon-of-energy-resistance-xphb"}, {cid: ["fire"]}, ruleset="2024", level=19)
    assert _card(one, cid)["status"] == "pending" and _resists(one) == ["fire"]


def test_boon_of_energy_resistance_redirection_dc_uses_constitution_and_proficiency(catalog):
    cid = "class:fighter:19:asi:feat:boon-of-energy-resistance-xphb:resistance-choice"
    r = fighter(catalog, {19: "boon-of-energy-resistance-xphb"}, {cid: ["fire", "cold"]}, ruleset="2024", level=19,
                base={"CON": 14})
    con_mod = r["derived"]["modifiers"]["CON"] if "modifiers" in r["derived"] else 2
    text = " ".join(_notes(r, "boon-of-energy-resistance-xphb"))
    assert f"DC {8 + con_mod + 6}" in text and f"2d12 + {con_mod}" in text
    assert "Fire, Cold" in text or "Cold, Fire" in text


def test_portal_jumper_resistance_and_resource(catalog):
    cid = "species:human-xphb:feat-0"
    r = resolve(_draft([("fighter", 1, {})], species="human-xphb",
                       species_choices={cid: ["feat:portal-jumper-au"]}), catalog)
    card = _card(r, f"{cid}:feat:portal-jumper-au:resistance-choice")
    assert card is not None and [o["id"] for o in card["options"]] == ["necrotic", "psychic", "radiant"]
    r2 = resolve(_draft([("fighter", 1, {})], species="human-xphb",
                        species_choices={cid: ["feat:portal-jumper-au"], card["id"]: ["psychic"]}), catalog)
    assert _resists(r2) == ["psychic"]
    res = next(x for x in r2["derived"]["featResources"] if x["name"] == "Portal Step")
    assert res["uses"] == 2 and res["recharge"] == "long"


def test_spell_resistant_one_of_four_and_resource(catalog):
    cid = "class:fighter:4:asi:feat:spell-resistant-au:resistance-choice"
    r = fighter(catalog, {4: "spell-resistant-au"}, {cid: ["thunder"]})
    assert [o["id"] for o in _card(r, cid)["options"]] == ["necrotic", "psychic", "radiant", "thunder"]
    assert _resists(r) == ["thunder"]
    res = next(x for x in r["derived"]["featResources"] if x["name"] == "Magic Resistant")
    assert res["uses"] == 2 and res["recharge"] == "long"


def test_a_resistance_pick_adds_to_species_resistance_without_duplicates(catalog):
    cid = "class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice"
    r = fighter(catalog, {4: "dragonscarred-frhof"}, {cid: ["poison"]}, species="dwarf")  # Dwarven Resilience: poison
    assert _resists(r).count("poison") == 1


def test_a_stale_pick_outside_the_options_is_pruned(catalog):
    cid = "class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice"
    r = fighter(catalog, {4: "dragonscarred-frhof"}, {cid: ["necrotic"]})
    assert _resists(r) == []
    assert any(p["choiceId"] == cid for p in r["pruned"])


def test_dropping_the_feat_drops_the_resistance_and_prunes_the_card(catalog):
    cid = "class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice"
    r = fighter(catalog, {}, {cid: ["fire"]}, level=4)
    assert _resists(r) == [] and any(p["choiceId"] == cid for p in r["pruned"])


# ---------------------------------------------------------------- Scion of the Outer Planes


@pytest.mark.parametrize("variant,damage", sorted(PLANES.items()))
def test_scion_resistance_follows_the_plane_pick_with_no_extra_card(catalog, variant, damage):
    base = "class:fighter:4:asi:feat:scion-of-the-outer-planes-sato"
    r = fighter(catalog, {4: "scion-of-the-outer-planes-sato"}, {f"{base}:spell-variant": [variant]})
    assert not [c for c in r["choices"] if c["id"].endswith(":resistance-choice")]
    assert _resists(r) == [damage]
    assert damage.capitalize() in " ".join(_notes(r, "scion-of-the-outer-planes-sato"))


def test_scion_without_a_plane_has_no_resistance_yet(catalog):
    r = fighter(catalog, {4: "scion-of-the-outer-planes-sato"})
    assert _resists(r) == []
    assert _card(r, "class:fighter:4:asi:feat:scion-of-the-outer-planes-sato:spell-variant")["status"] == "pending"


def test_scion_plane_change_changes_the_resistance(catalog):
    cid = "class:fighter:4:asi:feat:scion-of-the-outer-planes-sato:spell-variant"
    assert _resists(fighter(catalog, {4: "scion-of-the-outer-planes-sato"}, {cid: ["good-outer-plane"]})) == ["radiant"]
    assert _resists(fighter(catalog, {4: "scion-of-the-outer-planes-sato"}, {cid: ["lawful-outer-plane"]})) == ["force"]


# ---------------------------------------------------------------- Elemental Adept


def test_elemental_adept_types_and_note(catalog):
    cid = "class:fighter:4:asi:feat:elemental-adept-xphb:damage-type"
    r = fighter(catalog, {4: "elemental-adept-xphb"}, {cid: ["fire"]})
    assert [o["id"] for o in _card(r, cid)["options"]] == ["acid", "cold", "fire", "lightning", "thunder"]
    note = " ".join(_notes(r, "elemental-adept-xphb"))
    assert "Fire" in note and "treat any 1" in note
    assert _resists(r) == []  # it ignores the TARGET's resistance; it grants none


def test_elemental_adept_second_instance_cannot_repeat_a_type(catalog):
    first = "class:fighter:4:asi:feat:elemental-adept-xphb:damage-type"
    second = "class:fighter:8:asi:feat:elemental-adept-xphb:damage-type"
    r = fighter(catalog, {4: "elemental-adept-xphb", 8: "elemental-adept-xphb"}, {first: ["fire"], second: ["fire"]})
    opt = _opt(_card(r, second), "fire")
    assert opt["disabled"] and opt["disabledReason"] == "already chosen for Elemental Adept (1)"
    assert _card(r, second)["selected"] == [] and _card(r, second)["status"] == "pending"
    assert _card(r, first)["selected"] == ["fire"]
    assert any(p["choiceId"] == second for p in r["pruned"])
    ok = fighter(catalog, {4: "elemental-adept-xphb", 8: "elemental-adept-xphb"}, {first: ["fire"], second: ["cold"]})
    assert _card(ok, second)["selected"] == ["cold"] and _card(ok, second)["status"] == "resolved"
    assert not any(p["choiceId"] == second for p in ok["pruned"])


def test_elemental_adept_editions_share_the_distinct_rule(catalog):
    first = "class:fighter:4:asi:feat:elemental-adept-phb:damage-type"
    second = "class:fighter:8:asi:feat:elemental-adept-xphb:damage-type"
    r = fighter(catalog, {4: "elemental-adept-phb", 8: "elemental-adept-xphb"}, {first: ["thunder"], second: ["thunder"]})
    assert _opt(_card(r, second), "thunder")["disabled"]
    assert _card(r, second)["selected"] == []
    assert "Elemental Adept" in _opt(_card(r, second), "thunder")["disabledReason"]


def test_a_different_feat_with_the_same_types_is_not_blocked(catalog):
    first = "class:fighter:4:asi:feat:elemental-adept-xphb:damage-type"
    r = fighter(catalog, {4: "elemental-adept-xphb", 8: "dragonscarred-frhof"}, {
        first: ["fire"], "class:fighter:8:asi:feat:dragonscarred-frhof:resistance-choice": ["fire"]})
    assert _resists(r) == ["fire"]


def test_the_earlier_instance_wins_whatever_the_stored_order(catalog):
    first = "class:fighter:4:asi:feat:elemental-adept-xphb:damage-type"
    second = "class:fighter:8:asi:feat:elemental-adept-xphb:damage-type"
    r = fighter(catalog, {4: "elemental-adept-xphb", 8: "elemental-adept-xphb"}, {second: ["acid"], first: ["acid"]})
    assert _card(r, first)["selected"] == ["acid"] and _card(r, second)["selected"] == []


# ---------------------------------------------------------------- Strike of the Giants


def test_strike_of_the_giants_type_card_notes_and_resource(catalog):
    cid = "class:fighter:4:asi:feat:strike-of-the-giants-bgg:giant-type"
    base = fighter(catalog, {4: "strike-of-the-giants-bgg"})
    card = _card(base, cid)
    assert [o["label"] for o in card["options"]] == [
        "Cloud Strike", "Fire Strike", "Frost Strike", "Hill Strike", "Stone Strike", "Storm Strike"]
    assert card["status"] == "pending"
    assert not any("thunder" in n for n in _notes(base, "strike-of-the-giants-bgg"))
    r = fighter(catalog, {4: "strike-of-the-giants-bgg"}, {cid: ["storm"]}, base={"STR": 16, "CON": 14})
    notes = " ".join(_notes(r, "strike-of-the-giants-bgg"))
    assert "Storm Strike" in notes and "1d6 lightning" in notes
    assert "DC 13" in notes  # 8 + PB 2 + STR 3 (Strength or Constitution, the better one)
    res = next(x for x in r["derived"]["featResources"] if x["name"] == "Strike of the Giants")
    assert res["uses"] == 2 and res["recharge"] == "long" and "Storm Strike" in res["details"]["note"]
    r2 = fighter(catalog, {4: "strike-of-the-giants-bgg"}, {cid: ["fire"]})
    assert "1d10 fire" in " ".join(_notes(r2, "strike-of-the-giants-bgg"))


# ---------------------------------------------------------------- blocking and origins


def test_a_pending_card_blocks_export_like_any_other(catalog):
    r = fighter(catalog, {4: "dragonscarred-frhof"})
    cid = "class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice"
    assert any(cid in str(p) for p in _pending_cards(r))
    done = fighter(catalog, {4: "dragonscarred-frhof"}, {cid: ["acid"]})
    assert not any(cid in str(p) for p in _pending_cards(done))


def test_species_origin_cards_cascade_and_resolve(catalog):
    cid = "species:human-xphb:feat-0"
    r = resolve(_draft([("fighter", 1, {})], species="human-xphb",
                       species_choices={cid: ["feat:portal-jumper-au"]}), catalog)
    cards = [c["id"] for c in r["choices"] if c["id"].endswith(":resistance-choice")]
    assert cards == [f"{cid}:feat:portal-jumper-au:resistance-choice"]
    r2 = resolve(_draft([("fighter", 1, {})], species="human-xphb",
                        species_choices={cid: ["feat:portal-jumper-au"], cards[0]: ["radiant"]}), catalog)
    assert _resists(r2) == ["radiant"]


@pytest.mark.parametrize("site", ["background", "species", "fighting-style", "lessons", "asi"])
def test_every_feat_site_emits_and_applies_the_cards(catalog, monkeypatch, site):
    """The cards come from `_feat_choice_templates`, which all five sites call; the shipped FE7 feats are not
    reachable from every site (no background grants one, no Fighting Style / Origin-via-Lessons feat has one), so
    the effect table of a feat each site does grant is patched."""
    spec = {"resist_choice": {"count": 1, "options": ["acid", "cold"]}}
    if site == "background":  # Criminal XPHB grants Alert (XPHB)
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        draft = _draft([("fighter", 1, {})], ruleset="2024", background="criminal-xphb")
        cid = "feat:alert-xphb:resistance-choice"
    elif site == "species":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        draft = _draft([("fighter", 1, {})], ruleset="2024", species="human-xphb",
                       species_choices={"species:human-xphb:feat-0": ["feat:alert-xphb"]})
        cid = "species:human-xphb:feat-0:feat:alert-xphb:resistance-choice"
    elif site == "fighting-style":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "defense-xphb", {**fed.FEAT_EFFECTS["defense-xphb"], **spec})
        draft = _draft([("fighter", 1, {"class:fighter:1:fighting-style": ["feat:defense-xphb"]})], ruleset="2024")
        cid = next((c["id"] for c in resolve(draft, catalog)["choices"] if c["id"].endswith(":resistance-choice")), "")
        assert cid.startswith("class:fighter:1:fighting-style:") and "defense-xphb" in cid
    elif site == "lessons":
        monkeypatch.setitem(fed.FEAT_EFFECTS, "alert-xphb", {**fed.FEAT_EFFECTS["alert-xphb"], **spec})
        inv = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
        lessons = "opt-lessons-of-the-first-ones-xphb"
        card = f"class:warlock:invocation:{lessons}:feat"
        draft = _draft([("warlock", 2, {inv: [lessons], card: ["feat:alert-xphb"]})], ruleset="2024")
        cid = next((c["id"] for c in resolve(draft, catalog)["choices"] if c["id"].endswith(":resistance-choice")), "")
        assert cid.startswith(card + ":") and "alert-xphb" in cid
    else:
        monkeypatch.setitem(fed.FEAT_EFFECTS, "grappler-xphb", {**fed.FEAT_EFFECTS["grappler-xphb"], **spec})
        draft = _draft([("fighter", 4, _asi("fighter", {4: "grappler-xphb"}))], ruleset="2024")
        cid = "class:fighter:4:asi:feat:grappler-xphb:resistance-choice"
    r = resolve(draft, catalog)
    cards = [c for c in r["choices"] if c["id"].endswith(":resistance-choice")]
    assert len(cards) == 1 and cards[0]["source"]["kind"] == "feat", site
    assert cards[0]["id"] == cid, (site, cards[0]["id"])
    assert [o["id"] for o in cards[0]["options"]] == ["acid", "cold"] and cards[0]["status"] == "pending"
    # apply a pick: re-resolve with the pick stored in the owner's selections
    if site == "background":
        draft["background"]["choices"] = {cid: ["cold"]}
    elif site == "species":
        draft["species"]["choices"][cid] = ["cold"]
    else:
        draft["classes"][0]["choices"][cid] = ["cold"]
    r2 = resolve(draft, catalog)
    assert "cold" in _resists(r2), site


# ---------------------------------------------------------------- identity, degrade, timing


def test_no_fe7_feat_means_no_fe7_cards_and_no_resistance(catalog):
    r = resolve(_draft([("fighter", 4, {})]), catalog)
    for suffix in (":resistance-choice", ":damage-type", ":giant-type"):
        assert not [c for c in r["choices"] if c["id"].endswith(suffix)]
    assert _resists(r) == []


def test_empty_feat_catalog_degrades(catalog):
    bare = copy.copy(catalog)
    bare.feats = {}
    r = resolve(_draft([("fighter", 4, _asi("fighter", {4: "dragonscarred-frhof"}))]), bare)
    assert _resists(r) == [] and not [c for c in r["choices"] if c["id"].endswith(":resistance-choice")]
    assert fe.resistances([]) == []


def test_pure_resistances_dedupe_and_keep_order():
    insts = [{"resist": ["fire", "cold"]}, {"resist": ["cold", "acid"]}]
    assert fe.resistances(insts) == ["fire", "cold", "acid"]


def _mean_ms(catalog, draft):
    resolve(draft, catalog)
    start = time.perf_counter()
    for _ in range(10):
        resolve(draft, catalog)
    return (time.perf_counter() - start) / 10 * 1000


def test_resolve_stays_fast_with_fe7_feats(catalog):
    cid = {"class:fighter:4:asi:feat:dragonscarred-frhof:resistance-choice": ["fire"],
           "class:fighter:8:asi:feat:elemental-adept-xphb:damage-type": ["cold"],
           "class:fighter:12:asi:feat:strike-of-the-giants-bgg:giant-type": ["storm"]}
    ch = _asi("fighter", {4: "dragonscarred-frhof", 8: "elemental-adept-xphb", 12: "strike-of-the-giants-bgg"}, **cid)
    assert _mean_ms(catalog, _draft([("fighter", 20, ch)])) < 50
    assert _mean_ms(catalog, _draft([("fighter", 20, ch)], ruleset="2024")) < 50
