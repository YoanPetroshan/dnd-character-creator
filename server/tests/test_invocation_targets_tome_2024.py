"""C7c-1: Eldritch Invocation target cantrips (Agonizing Blast / Eldritch Spear / Repelling Blast) and Pact of the Tome
under ruleset 2024 (XPHB). Decision E4: repeat instances `<id>~2`/`~3`, each with its own target pick, targets differ.

XPHB text (read from the imported catalog, 2026-10-11):
  Agonizing Blast   "Choose one of your known Warlock cantrips that deals damage. You can add your Charisma modifier to
                    that spell's damage rolls. Repeatable ... Each time you do so, choose a different eligible cantrip."
  Eldritch Spear    "Choose one of your known Warlock cantrips that deals damage and has a range of 10+ feet. When you
                    cast that spell, its range increases by a number of feet equal to 30 times your Warlock level."
  Repelling Blast   "Choose one of your known Warlock cantrips that requires an attack roll. When you hit a Large or
                    smaller creature with that cantrip, you can push the creature up to 10 feet straight away."
  Pact of the Tome  "When the book appears, choose three cantrips, and choose two level 1 spells that have the Ritual
                    tag. The spells can be from any class's spell list, and they must be spells you don't already have
                    prepared. While the book is on your person, you have the chosen spells prepared, and they function
                    as Warlock spells for you."

Rule matrix (text -> engine):
  target pick   one card per SELECTED instance, cid class:warlock:invocation:<instance id>:cantrip (count 1); options =
                the known Warlock cantrips (+ Tome cantrips); a cantrip that does not qualify is disabled with its
                reason; a cantrip another instance of the same invocation holds is disabled ("already chosen for ...");
                effects: Agonizing resource details.spell, Spear note (range), Repelling note (cantrip).
  Tome          cards ...:opt-pact-of-the-tome-xphb:cantrips (3, any class) and :rituals (2 level-1 rituals); spells the
                Warlock already has are disabled; sheet.spells[warlock].pactOfTheTome (+ export line); Tome cantrips
                count towards the invocation cantrip prerequisites while the Tome is selected (fixed point).
Matrix: invocation x instance x stored pick validity x level-down x ruleset (2024 / mixed / 2014) x SRD-only catalog x
exports."""
import io

import pytest

from catalog.loader import load
from c7c_helpers import (  # noqa: F401
    AGON, BLADE, BLADE_W, CANT, CHAIN, EB, FB, INV, KNOWN, LESSONS, LONGSWORD, MI, REPEL, SPEAR, THIRST, TOME, TOME_C, TOME_R,
    TTD, X, _card, _dependent_ids, _draft, _l, _opt, _problem_ids, _pruned, _res, _resource, _srd_only, needs_data, tcid,
    _l, resolve_laps,
)
from engine import class_choices_2024
from engine.resolve import resolve


@pytest.fixture(scope="module")
def catalog():
    return load()


# ---- target cantrips (Agonizing Blast / Eldritch Spear / Repelling Blast) -------------------------------------------


@needs_data
def test_cards_exist_only_for_selected_instances(catalog):
    r = _res(catalog, 5, [AGON], [EB, TTD, MI])
    assert _dependent_ids(r) == [tcid(AGON, "cantrip")]
    card = _card(r, tcid(AGON, "cantrip"))
    assert card["count"] == 1 and card["status"] == "pending" and card["source"]["kind"] == "class"
    assert {o["id"] for o in card["options"]} == {EB, TTD, MI}
    r2 = _res(catalog, 5, [AGON, f"{AGON}~2"], [EB, TTD, MI])
    assert _dependent_ids(r2) == [tcid(AGON, "cantrip"), tcid(f"{AGON}~2", "cantrip")]
    assert _dependent_ids(_res(catalog, 5, [CHAIN], [EB])) == []
    assert not any(":invocation:" in i for i in _problem_ids(r2))  # R8 plumbing ignores the singular marker


@needs_data
def test_two_agonizing_instances_have_two_resources_with_distinct_targets(catalog):
    picks = {tcid(AGON, "cantrip"): [EB], tcid(f"{AGON}~2", "cantrip"): [TTD]}
    r = _res(catalog, 5, [AGON, f"{AGON}~2"], [EB, TTD, MI], extra=picks)
    first, second = _resource(r, "Agonizing Blast"), _resource(r, "Agonizing Blast (2)")
    assert first["bonus"] == 3 and second["bonus"] == 3  # CHA 16
    assert first["details"]["spell"] == EB and second["details"]["spell"] == TTD
    assert "Eldritch Blast" in first["details"]["note"] and "Toll the Dead" in second["details"]["note"]
    assert _card(r, tcid(AGON, "cantrip"))["status"] == "resolved"
    assert _card(r, tcid(f"{AGON}~2", "cantrip"))["selected"] == [TTD]


@needs_data
def test_the_second_instance_cannot_pick_the_first_instances_cantrip(catalog):
    picks = {tcid(AGON, "cantrip"): [EB], tcid(f"{AGON}~2", "cantrip"): [EB]}
    r = _res(catalog, 5, [AGON, f"{AGON}~2"], [EB, TTD, MI], extra=picks)
    second = _card(r, tcid(f"{AGON}~2", "cantrip"))
    assert _opt(second, EB)["disabled"] and "already chosen for Agonizing Blast" in _opt(second, EB)["disabledReason"]
    assert second["selected"] == [] and second["status"] == "pending"
    assert _card(r, tcid(AGON, "cantrip"))["selected"] == [EB]
    assert "spell" not in _resource(r, "Agonizing Blast (2)")["details"]  # no target yet: the generic note stays
    # and the first instance sees the second one's pick as taken
    picks2 = {tcid(AGON, "cantrip"): [], tcid(f"{AGON}~2", "cantrip"): [TTD]}
    r2 = _res(catalog, 5, [AGON, f"{AGON}~2"], [EB, TTD, MI], extra=picks2)
    assert _opt(_card(r2, tcid(AGON, "cantrip")), TTD)["disabled"]


@needs_data
def test_a_cantrip_that_does_not_qualify_is_disabled_with_its_reason(catalog):
    r = _res(catalog, 5, [AGON, REPEL], [EB, TTD, MI])
    agon = _card(r, tcid(AGON, "cantrip"))
    assert "deal" in _opt(agon, MI)["disabledReason"] and not _opt(agon, TTD).get("disabled")
    repel = _card(r, tcid(REPEL, "cantrip"))
    assert not _opt(repel, EB).get("disabled")  # Eldritch Blast: ranged spell attack
    assert "attack roll" in _opt(repel, TTD)["disabledReason"]  # Toll the Dead is a saving throw
    assert "attack roll" in _opt(repel, MI)["disabledReason"]


@needs_data
def test_eldritch_spear_needs_range_10_feet_and_notes_the_extended_range(catalog):
    cantrips = [EB, "chill-touch-xphb", "thunderclap-xphb"]
    r = _res(catalog, 5, [SPEAR], cantrips, extra={tcid(SPEAR, "cantrip"): [EB]})
    card = _card(r, tcid(SPEAR, "cantrip"))
    assert not _opt(card, EB).get("disabled")
    assert "range" in _opt(card, "chill-touch-xphb")["disabledReason"]  # Touch
    assert "range" in _opt(card, "thunderclap-xphb")["disabledReason"]  # Self (5-foot emanation)
    note = _resource(r, "Eldritch Spear")["details"]["note"]
    assert "Eldritch Blast" in note and "150" in note and "270" in note  # 30 x 5 = +150 ft on 120 ft
    r2 = _res(catalog, 5, [SPEAR], cantrips, extra={tcid(SPEAR, "cantrip"): ["chill-touch-xphb"]})
    assert _card(r2, tcid(SPEAR, "cantrip"))["selected"] == []
    assert "150" in _resource(r2, "Eldritch Spear")["details"]["note"]  # generic note without a target


@needs_data
def test_repelling_blast_note_names_the_cantrip(catalog):
    r = _res(catalog, 5, [REPEL], [EB, TTD], extra={tcid(REPEL, "cantrip"): [EB]})
    note = _resource(r, "Repelling Blast")["details"]["note"]
    assert "Eldritch Blast" in note and "10 feet" in note


@needs_data
def test_removing_the_invocation_prunes_its_target_pick(catalog):
    picks = {tcid(AGON, "cantrip"): [EB], tcid(f"{AGON}~2", "cantrip"): [TTD]}
    r = _res(catalog, 5, [AGON], [EB, TTD], extra=picks)
    assert _dependent_ids(r) == [tcid(AGON, "cantrip")]
    assert "no longer applies" in _pruned(r, tcid(f"{AGON}~2", "cantrip"))
    assert _resource(r, "Agonizing Blast (2)") is None


@needs_data
def test_a_target_that_is_no_longer_a_known_cantrip_is_pruned_not_blocking(catalog):
    picks = {tcid(AGON, "cantrip"): [EB], tcid(f"{AGON}~2", "cantrip"): [TTD]}
    r = _res(catalog, 5, [AGON, f"{AGON}~2"], [EB, MI, "chill-touch-xphb"], extra=picks)
    card = _card(r, tcid(f"{AGON}~2", "cantrip"))
    assert card["selected"] == [] and _pruned(r, card["id"])
    assert not [p for p in r["problems"] if "over-selected" in p["id"]]


@needs_data
def test_agonizing_is_dropped_when_the_last_damaging_cantrip_goes(catalog):
    r = _res(catalog, 5, [AGON], [MI, "mage-hand-xphb"], extra={tcid(AGON, "cantrip"): [EB]})
    assert AGON not in _card(r, INV)["selected"]
    assert _dependent_ids(r) == []  # the dependent card goes with its invocation
    assert _resource(r, "Agonizing Blast") is None


@needs_data
def test_level_down_drops_instances_and_their_cards(catalog):
    picks = {tcid(AGON, "cantrip"): [EB], tcid(f"{AGON}~2", "cantrip"): [TTD], tcid(f"{AGON}~3", "cantrip"): [FB]}
    r = _res(catalog, 1, [AGON, f"{AGON}~2", f"{AGON}~3"], [EB, TTD], extra=picks)
    assert _dependent_ids(r) == []  # count 1 at Warlock 1, and Agonizing needs level 2


# ---- Pact of the Tome ------------------------------------------------------------------------------------------------


@needs_data
def test_tome_cards_offer_any_class_cantrips_and_two_level_1_rituals(catalog):
    r = _res(catalog, 3, [TOME], [EB, MI, "mage-hand-xphb"])
    c, rit = _card(r, TOME_C), _card(r, TOME_R)
    assert c["count"] == 3 and rit["count"] == 2
    assert FB in {o["id"] for o in c["options"]}  # a Sorcerer / Wizard cantrip
    assert all(catalog.spells[o["id"]]["level"] == 0 for o in c["options"])
    assert all(catalog.spells[o["id"]]["level"] == 1 and catalog.spells[o["id"]]["ritual"] for o in rit["options"])
    assert "find-familiar-xphb" in {o["id"] for o in rit["options"]}  # not on the Warlock list
    assert _dependent_ids(_res(catalog, 3, [CHAIN])) == []


@needs_data
def test_tome_options_exclude_spells_the_warlock_already_has(catalog):
    r = _res(catalog, 3, [TOME], [EB, MI, "mage-hand-xphb"], extra={KNOWN: ["comprehend-languages-xphb", "hex-xphb"]})
    assert "already prepared" in _opt(_card(r, TOME_C), EB)["disabledReason"]
    assert "already prepared" in _opt(_card(r, TOME_R), "comprehend-languages-xphb")["disabledReason"]
    assert not _opt(_card(r, TOME_C), FB).get("disabled")
    r2 = _res(catalog, 3, [TOME], [EB, MI, "mage-hand-xphb"], extra={TOME_C: [EB, FB]})
    assert _card(r2, TOME_C)["selected"] == [FB]  # the clash does not stay selected


@needs_data
def test_tome_picks_reach_the_sheet_without_changing_the_known_counts(catalog):
    picks = {TOME_C: [FB, "sacred-flame-xphb", "light-xphb"], TOME_R: ["find-familiar-xphb", "detect-magic-xphb"]}
    r = _res(catalog, 3, [TOME], [EB, MI], extra=picks)
    assert _card(r, TOME_C)["status"] == "resolved" and _card(r, TOME_R)["status"] == "resolved"
    entry = next(e for e in r["sheet"]["spells"] if e["classId"] == "warlock")
    assert [s["id"] for s in entry["pactOfTheTome"]] == [FB, "sacred-flame-xphb", "light-xphb", "find-familiar-xphb", "detect-magic-xphb"]
    assert [s["level"] for s in entry["pactOfTheTome"]] == [0, 0, 0, 1, 1]
    assert all(set(s) == {"id", "name", "level"} for s in entry["pactOfTheTome"])
    assert [s["id"] for s in entry["cantrips"]] == [EB, MI]  # Tome cantrips are not "known" cantrips
    assert _card(r, CANT)["count"] == 2
    entry2 = next(e for e in _res(catalog, 3, [CHAIN], [EB, MI])["sheet"]["spells"] if e["classId"] == "warlock")
    assert "pactOfTheTome" not in entry2


@needs_data
def test_tome_cantrips_satisfy_the_invocation_cantrip_prerequisite(catalog):
    base = [MI, "mage-hand-xphb"]  # no damaging Warlock cantrip of its own
    r = _res(catalog, 5, [AGON], base)
    assert AGON not in _card(r, INV)["selected"] and "damage" in _opt(_card(r, INV), AGON)["disabledReason"]
    r2 = _res(catalog, 5, [TOME, AGON], base, extra={TOME_C: [FB, "light-xphb", "guidance-xphb"]})
    assert _card(r2, INV)["selected"] == [TOME, AGON]  # Fire Bolt counts: it "functions as a Warlock spell"
    target = _card(r2, tcid(AGON, "cantrip"))
    assert FB in {o["id"] for o in target["options"]} and not _opt(target, FB).get("disabled")
    assert _opt(target, "light-xphb")["disabled"]
    # taking the Tome away takes the prerequisite (and the invocation, and its target card) with it
    r3 = _res(catalog, 5, [AGON], base, extra={TOME_C: [FB, "light-xphb", "guidance-xphb"]})
    assert AGON not in _card(r3, INV)["selected"] and _dependent_ids(r3) == []


@needs_data
def test_tome_cantrip_target_can_feed_agonizing_blast_end_to_end(catalog):
    r = _res(catalog, 5, [TOME, AGON], [MI, "mage-hand-xphb"],
             extra={TOME_C: [FB, "light-xphb", "guidance-xphb"], tcid(AGON, "cantrip"): [FB]})
    assert _resource(r, "Agonizing Blast")["details"]["spell"] == FB


# ---- ruleset isolation, degrade, exports ------------------------------------------------------------------------------


STORED = {
    tcid(AGON, "cantrip"): [EB], TOME_C: [FB, "light-xphb", "guidance-xphb"], TOME_R: ["find-familiar-xphb", "detect-magic-xphb"],
}


@needs_data
@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_no_target_or_tome_cards_outside_ruleset_2024(catalog, ruleset):
    r = _res(catalog, 5, [AGON, TOME], [EB, MI], extra=STORED, ruleset=ruleset, bg="acolyte")
    assert _dependent_ids(r) == []
    entry = next(e for e in r["sheet"]["spells"] if e["classId"] == "warlock")
    assert "pactOfTheTome" not in entry


@needs_data
def test_srd_only_catalog_degrades(catalog):
    r = _res(_srd_only(catalog), 5, [AGON, TOME], [EB, MI], extra=STORED)
    assert _dependent_ids(r) == []


@needs_data
def test_exports_print_the_tome_line(catalog):
    from markdown_export import to_markdown
    from pdf_export import to_pdf
    from pypdf import PdfReader
    picks = {TOME_C: [FB, "light-xphb", "guidance-xphb"], TOME_R: ["find-familiar-xphb", "detect-magic-xphb"]}
    r = _res(catalog, 3, [TOME], [EB, MI], extra=picks)
    md = to_markdown(r)
    assert "**Книга на сенките:** Fire Bolt (ниво 0)" in md and "Find Familiar (ниво 1)" in md
    pdf = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(r))).pages)
    assert "Книга на сенките: Fire Bolt (ниво 0)" in pdf
    assert "Книга на сенките" not in to_markdown(_res(catalog, 3, [CHAIN], [EB, MI]))


@needs_data
def test_helpers_range_and_instance_cards(catalog):
    assert class_choices_2024.spell_range_feet(catalog.spells[EB]) == 120
    assert class_choices_2024.spell_range_feet(catalog.spells["chill-touch-xphb"]) is None
    assert class_choices_2024.spell_range_feet(catalog.spells["thunderclap-xphb"]) is None
    assert class_choices_2024.dependent_cid(f"{AGON}~2", "cantrip") == tcid(f"{AGON}~2", "cantrip")


@needs_data
def test_malformed_stored_dependent_values_do_not_crash(catalog):
    extra = {tcid(AGON, "cantrip"): "eldritch-blast-xphb", TOME_C: {"a": 1}, TOME_R: [None, 5, "detect-magic-xphb"],
             BLADE_W: 7, tcid(_l(), "feat"): [["feat:alert-xphb"]]}
    r = _res(catalog, 5, [AGON, TOME, BLADE, _l()], [EB, MI], extra=extra)
    assert _card(r, tcid(AGON, "cantrip"))["selected"] == []
    assert _card(r, TOME_R)["selected"] == ["detect-magic-xphb"]
    assert not [p for p in r["problems"] if "over-selected" in p["id"]]


def test_prune_dependents_and_instance_target_helpers():
    card = lambda cid, sel: {"id": cid, "label": cid, "selected": sel, "source": {"kind": "class"}}  # noqa: E731
    choices = [card(INV, [AGON]), card(tcid(AGON, "cantrip"), [EB]), card(tcid(f"{AGON}~2", "cantrip"), [TTD]),
               card(tcid(f"{AGON}~3", "cantrip"), []), card("class:warlock:spells-cantrips", [EB])]
    assert class_choices_2024.instance_target(choices, AGON) == EB
    assert class_choices_2024.instance_target(choices, f"{AGON}~3") is None
    assert class_choices_2024.instance_target(choices, REPEL) is None
    pruned = class_choices_2024.prune_invocation_dependents(choices, [AGON])
    assert [c["id"] for c in choices] == [INV, tcid(AGON, "cantrip"), "class:warlock:spells-cantrips"]
    assert [p["choiceId"] for p in pruned] == [tcid(f"{AGON}~2", "cantrip")]  # the empty ~3 card goes silently
