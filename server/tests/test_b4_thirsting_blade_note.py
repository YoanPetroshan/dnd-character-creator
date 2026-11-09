"""B4 (owner decision 2026-11-09, plan B4 + decision B10): Thirsting Blade's extra attack stays OUT of `attacksPerAction`; it is a
note on the pact weapon's attack row (a per-attack rider is a note, never an attack-row option).

VERIFIED against the vendored optionalfeatures.json first:
  Thirsting Blade | PHB (2014, srd)  "You can attack with your pact weapon twice, instead of once, whenever you take the Attack action on your turn."
  Thirsting Blade | XPHB (2024)      "You gain the Extra Attack feature for your pact weapon only. With that feature, you can attack twice with the
                                      weapon instead of once when you take the Attack action on your turn."
  Devouring Blade | XPHB             "The Extra Attack of your Thirsting Blade invocation confers two extra attacks rather than one."
Where the row exists: only the 2024 chassis has a pact weapon pick (C7c / E5: the card `...:opt-pact-of-the-blade-xphb:weapon`),
so only 2024 has a pact weapon attack row, and the row note (`PACT_WEAPON_ROW_NOTES_2024`, added by C7c) is already there; B4 pins
its text against the records and the count. The 2014 invocation has no weapon pick in this app (`test_no_pact_weapon_outside_ruleset_2024`):
there is no row to annotate, its note stays on the invocation resource (`INVOCATION_EFFECTS` `thirsting-blade`). The clause
"(not on top of Extra Attack)" is the PHB 2024 Multiclassing rule (not in the vendored records), kept from C7c as is."""
from __future__ import annotations

import json

import pytest

from catalog.official.paths import official_dir
from catalog.loader import load
from catalog import reference_data
from c7c_helpers import BLADE, BLADE_W, EB, LONGSWORD, MI, THIRST, X, _res, _resource, needs_data
from engine.resolve import resolve

pytestmark = needs_data

DEVOUR = X.format("devouring-blade")


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def raw():
    data = json.load(open(official_dir() / "optionalfeatures.json"))["optionalfeature"]
    return {(r["name"], r["source"]): r for r in data}


def test_quote_pin_the_records(raw):
    assert raw[("Thirsting Blade", "PHB")]["entries"] == [
        "You can attack with your pact weapon twice, instead of once, whenever you take the {@action Attack} action on your turn."]
    assert raw[("Thirsting Blade", "XPHB")]["entries"] == [
        "You gain the Extra Attack feature for your pact weapon only. With that feature, you can attack twice with the weapon instead of once "
        "when you take the {@action Attack|XPHB} action on your turn."]
    assert raw[("Devouring Blade", "XPHB")]["entries"] == [
        "The Extra Attack of your {@optfeature Thirsting Blade|XPHB} invocation confers two extra attacks rather than one."]


def test_row_note_texts_follow_the_records():
    notes = reference_data.PACT_WEAPON_ROW_NOTES_2024
    assert notes[THIRST] == "Thirsting Blade: attack twice with the Attack action (not on top of Extra Attack)"
    assert notes[DEVOUR] == "Devouring Blade: Thirsting Blade confers two extra attacks rather than one"
    # the 2014 and 2024 invocation resource notes say the same thing as their records
    assert reference_data.INVOCATION_EFFECTS["eldritch-invocation-thirsting-blade"]["note"] == (
        "Attack with your pact weapon twice, instead of once, when you take the Attack action.")
    assert "attack twice instead of once with the Attack action" in reference_data.INVOCATION_EFFECTS_2024[THIRST]["note"]


def _row(r, item="longsword"):
    return next(a for a in r["derived"]["attacks"] if a["itemId"] == item)


def _blade(catalog, level, picks, **kw):
    return _res(catalog, level, picks, [EB, MI], added=LONGSWORD, extra={BLADE_W: ["longsword"]}, **kw)


def test_2024_row_carries_the_note_and_the_count_stays_out(catalog):
    with_t = _blade(catalog, 5, [BLADE, THIRST])
    without = _blade(catalog, 5, [BLADE])
    assert "Thirsting Blade: attack twice with the Attack action (not on top of Extra Attack)" in _row(with_t)["notes"]
    assert not any("Thirsting" in n for n in _row(without)["notes"])
    for key in ("attackBonus", "damage", "ability", "proficient"):  # information only: the numbers do not move
        assert _row(with_t)[key] == _row(without)[key], key
    assert with_t["derived"]["attacksPerAction"] == without["derived"]["attacksPerAction"] == 1
    other = [a for a in with_t["derived"]["attacks"] if a["itemId"] != "longsword"]
    assert all(not any("Thirsting" in n for n in a["notes"]) for a in other)  # only the pact weapon's row


def test_2024_devouring_blade_adds_its_note_and_still_no_count(catalog):
    r = _blade(catalog, 12, [BLADE, THIRST, DEVOUR])
    notes = _row(r)["notes"]
    assert "Devouring Blade: Thirsting Blade confers two extra attacks rather than one" in notes
    assert notes.index("Thirsting Blade: attack twice with the Attack action (not on top of Extra Attack)") < notes.index(
        "Devouring Blade: Thirsting Blade confers two extra attacks rather than one")
    assert r["derived"]["attacksPerAction"] == 1


def test_a_real_extra_attack_class_keeps_its_own_count(catalog):
    fighter5 = {"classId": "fighter", "level": 5, "subclassId": "champion", "choices": {}}
    r = _blade(catalog, 5, [BLADE, THIRST], classes_before=(fighter5,))
    assert r["derived"]["attacksPerAction"] == 2  # the Fighter's Extra Attack; Thirsting Blade adds nothing on top
    assert "Thirsting Blade: attack twice with the Attack action (not on top of Extra Attack)" in _row(r)["notes"]


@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_2014_has_no_pact_weapon_row_and_the_count_is_unchanged(catalog, ruleset):
    """The 2014 / mixed Warlock has no pact weapon pick, so no row to annotate; attacksPerAction is 1 with or without the invocation."""
    def draft(picks):
        return {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 10, "CHA": 16}},
                "species": {"id": "human"}, "background": {"id": "acolyte"}, "equipment": {"choices": {}, "added": LONGSWORD, "skipped": False},
                "classes": [{"classId": "warlock", "level": 5, "choices": {"class:warlock:3:feature:pact-boon": ["pact-of-the-blade"],
                                                                          "class:warlock:2:invocations:eldritch-invocations": picks}}]}
    on = resolve(draft(["eldritch-invocation-thirsting-blade"]), catalog)
    off = resolve(draft([]), catalog)
    assert on["derived"]["attacksPerAction"] == off["derived"]["attacksPerAction"] == 1
    assert not any("Thirsting" in n for a in on["derived"]["attacks"] for n in a["notes"])
    res = next(r for r in on["derived"]["classResources"] if r["name"] == "Thirsting Blade")
    assert res["details"]["note"] == "Attack with your pact weapon twice, instead of once, when you take the Attack action."
    assert not any(r["name"] == "Thirsting Blade" for r in off["derived"]["classResources"])
