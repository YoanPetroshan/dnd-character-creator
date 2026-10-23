"""RP7 (E11c): SRD Monk "one type of artisan's tools or one musical instrument" is a real card under mixed / 2014.

Governing text (catalog `classes["monk"]["proficiency_choices"][1]["desc"]`, the SRD Monk Proficiencies line,
pinned verbatim below): "Choose one type of artisan's tools or one musical instrument".

Why it never showed: that envelope holds two nested `option_type: "choice"` options (artisan's tools / musical
instrument), which `build_choice_options` skipped, so the card did not resolve. It is the only nested choice in any
class / background / race / feat proficiency envelope (test below), so flattening them (proficiency envelopes only)
changes nothing else.

Rule matrix (ruleset mixed and 2014; 2024 is the C9a card and stays as it was):
  Monk is the INITIAL class     -> card `class:monk:1:prof-choice-1`, count 1, 27 options in the order
                                   17 Artisan's Tools then 10 Musical Instruments, `group` = the tool category
  the pick                      -> `sheet.proficiencies.tools`, status resolved
  Monk is a SECONDARY class     -> no card (the SRD Monk multiclass row grants no tool)
  card order                    -> `prof-choice-0` (2 of 6 skills) then `prof-choice-1`
  same cid as the 2024 card     -> a pick survives a ruleset switch (2024 options are the same 27 ids)
  SRD data lists Disguise Kit and Forgery Kit under the nested artisan's tools list; the catalog tool table
  (`reference_data.TOOLS`) does not class them as artisan's tools, so they are not offered (27, not 29).
  Equipment nested choices (`build_equipment_choice`) are untouched; a non-proficiency envelope keeps skipping a
  nested choice option."""
import json
from pathlib import Path

import pytest

from catalog import reference_data
from catalog.choices import build_choice_options, build_choice_template
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

DATA = Path(__file__).resolve().parents[2] / "chargen" / "data" / "srd"
CID = "class:monk:1:prof-choice-1"
ARTISANS = [t["index"] for t in reference_data.TOOLS if t["category"] == "Artisan's Tools"]
INSTRUMENTS = [t["index"] for t in reference_data.TOOLS if t["category"] == "Musical Instrument"]


@pytest.fixture(scope="module")
def catalog():
    return load()


def _res(catalog, classes, ruleset="mixed", choices=None, sources=None):
    return resolve({
        "ruleset": ruleset, "sources": sources if sources is not None else [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 10, "CHA": 10}},
        "species": {"id": "human"}, "background": {"id": "acolyte"},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": (choices or {}).get(c, {})} for c, lv in classes],
    }, catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


# ------------------------------------------------------------- data pins

def test_srd_monk_sentence_is_pinned_and_the_nested_shape_is_what_we_flatten(catalog):
    env = catalog.classes["monk"]["proficiency_choices"][1]
    assert env["desc"] == "Choose one type of artisan’s tools or one musical instrument"
    assert env["choose"] == 1
    nested = [o for o in env["from"]["options"] if o["option_type"] == "choice"]
    assert [n["choice"]["desc"] for n in nested] == ["artisan's tools", "musical instrument"]


def test_only_the_monk_has_a_nested_choice_in_a_proficiency_envelope():
    """The VERIFY of the slice: classes (own + multiclass), backgrounds, races, subraces, traits."""
    holders = []
    for fname, keys in (("5e-SRD-Classes.json", ("proficiency_choices", "multi_classing")),
                        ("5e-SRD-Backgrounds.json", ("starting_proficiency_choices",)),
                        ("5e-SRD-Races.json", ("starting_proficiency_options",)),
                        ("5e-SRD-Subraces.json", ("starting_proficiency_options",)),
                        ("5e-SRD-Traits.json", ("proficiency_choices",))):
        for rec in json.loads((DATA / fname).read_text(encoding="utf-8")):
            def envs(value):
                if isinstance(value, dict):
                    if "from" in value:
                        yield value
                    for v in value.values():
                        yield from envs(v)
                elif isinstance(value, list):
                    for v in value:
                        yield from envs(v)
            for key in keys:
                for env in envs(rec.get(key)):
                    if any(o.get("option_type") == "choice" for o in env["from"].get("options", [])):
                        holders.append((fname, rec["index"]))
    assert holders == [("5e-SRD-Classes.json", "monk")]


# ------------------------------------------------------------- build_choice_template

def _monk_envelope():
    monk = next(c for c in json.loads((DATA / "5e-SRD-Classes.json").read_text(encoding="utf-8")) if c["index"] == "monk")
    return monk["proficiency_choices"][1]


SRC = {"kind": "class", "id": "monk", "label": "Monk", "level": 1}


def test_template_flattens_to_27_options_with_groups():
    tpl = build_choice_template(_monk_envelope(), CID, SRC, "Tool Proficiencies")
    assert tpl is not None and tpl["count"] == 1
    assert [o["id"] for o in tpl["options"]] == ARTISANS + INSTRUMENTS and len(tpl["options"]) == 27
    assert {o["group"] for o in tpl["options"][:17]} == {"Artisan's Tools"}
    assert {o["group"] for o in tpl["options"][17:]} == {"Musical Instrument"}
    assert {"id": "flute", "label": "Flute", "group": "Musical Instrument"} in tpl["options"]
    assert not {"disguise-kit", "forgery-kit"} & {o["id"] for o in tpl["options"]}


def test_non_proficiency_envelope_still_skips_a_nested_choice_option():
    """Flattening is for `type: proficiencies` only; an envelope of another type keeps the old skip."""
    env = dict(_monk_envelope(), type="equipment")
    assert build_choice_template(env, CID, SRC, "x") is None
    assert build_choice_options(_monk_envelope()["from"]) is None  # the bare option builder keeps its contract


def test_nested_choice_with_no_known_tool_is_dropped():
    env = {"choose": 1, "type": "proficiencies", "from": {"option_set_type": "options_array", "options": [
        {"option_type": "choice", "choice": {"desc": "x", "choose": 1, "type": "proficiencies", "from": {
            "option_set_type": "options_array",
            "options": [{"option_type": "reference", "item": {"index": "nonsense", "name": "Nonsense", "url": ""}}]}}}]}}
    assert build_choice_template(env, CID, SRC, "x") is None


def test_flat_options_do_not_get_a_group():
    skills = next(c for c in json.loads((DATA / "5e-SRD-Classes.json").read_text(encoding="utf-8"))
                  if c["index"] == "monk")["proficiency_choices"][0]
    assert all("group" not in o for o in build_choice_template(skills, "x", SRC, "x")["options"])


# ------------------------------------------------------------- resolve()

@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
@pytest.mark.parametrize("sources", [[], ["srd"]])
def test_monk_1_has_the_tool_card(catalog, ruleset, sources):
    res = _res(catalog, [("monk", 1)], ruleset, sources=sources)
    card = _card(res, CID)
    assert card and card["status"] == "pending" and card["count"] == 1 and card["label"] == "Tool Proficiencies"
    assert [o["id"] for o in card["options"]] == ARTISANS + INSTRUMENTS
    assert card["source"] == {"kind": "class", "id": "monk", "label": "Monk", "level": 1}


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
def test_the_pick_reaches_sheet_tools(catalog, ruleset):
    base = _res(catalog, [("monk", 1)], ruleset)
    assert not set(ARTISANS + INSTRUMENTS) & set(base["sheet"]["proficiencies"]["tools"])
    for pick in ("smiths-tools", "flute"):
        res = _res(catalog, [("monk", 1)], ruleset, choices={"monk": {CID: [pick]}})
        assert _card(res, CID)["status"] == "resolved" and _card(res, CID)["selected"] == [pick]
        assert pick in res["sheet"]["proficiencies"]["tools"]
        assert not [t for t in ARTISANS + INSTRUMENTS if t != pick and t in res["sheet"]["proficiencies"]["tools"]]


def test_the_card_also_shows_at_higher_monk_levels(catalog):
    for lvl in (3, 11, 20):
        assert _card(_res(catalog, [("monk", lvl)]), CID) is not None


def test_secondary_monk_has_no_card(catalog):
    for classes in ([("barbarian", 3), ("monk", 2)], [("fighter", 1), ("monk", 1)]):
        res = _res(catalog, classes)
        assert _card(res, CID) is None and _card(res, "class:monk:multiclass-prof-choice-0") is None
    # a stored pick on a secondary Monk is not an applied proficiency
    res = _res(catalog, [("fighter", 1), ("monk", 1)], choices={"monk": {CID: ["flute"]}})
    assert "flute" not in res["sheet"]["proficiencies"]["tools"]


def test_card_order_skills_then_tools(catalog):
    ids = [c["id"] for c in _res(catalog, [("monk", 1)])["choices"] if c["id"].startswith("class:monk:1:prof-choice-")]
    assert ids == ["class:monk:1:prof-choice-0", CID]


def test_unaffected_classes_keep_their_proficiency_cards(catalog):
    """Bard (skills + instruments) and Rogue have no nested choice: same cards, flat options without a group."""
    for cls, want in (("bard", ["class:bard:1:prof-choice-0", "class:bard:1:prof-choice-1"]),
                      ("rogue", ["class:rogue:1:prof-choice-0"])):
        res = _res(catalog, [(cls, 1)])
        cards = [c for c in res["choices"] if "prof-choice" in c["id"]]
        assert [c["id"] for c in cards] == want
        assert all("group" not in o for c in cards for o in c["options"])


def test_a_stale_pick_is_dropped_not_applied(catalog):
    res = _res(catalog, [("monk", 1)], choices={"monk": {CID: ["not-a-tool"]}})
    assert _card(res, CID)["status"] == "pending" and "not-a-tool" not in res["sheet"]["proficiencies"]["tools"]


needs_2024 = pytest.mark.skipif(not (has_official() and has_official_classes()), reason="5etools data not available")


@needs_2024
def test_2024_card_is_the_same_cid_and_ids_and_a_pick_survives_a_ruleset_switch(catalog):
    new = _card(_res(catalog, [("monk", 1)], "2024"), CID)
    old = _card(_res(catalog, [("monk", 1)], "mixed"), CID)
    assert [o["id"] for o in new["options"]] == [o["id"] for o in old["options"]]
    assert all("group" not in o for o in new["options"])  # the 2024 card is unchanged
    for rs in ("2024", "mixed", "2014"):
        res = _res(catalog, [("monk", 1)], rs, choices={"monk": {CID: ["lute"]}})
        assert _card(res, CID)["status"] == "resolved" and "lute" in res["sheet"]["proficiencies"]["tools"]


def test_degrades_with_an_srd_only_catalog(catalog):
    """The card comes from SRD data alone (sources ["srd"] above); nothing here needs an official source."""
    res = _res(catalog, [("monk", 1)], sources=["srd"])
    assert len(_card(res, CID)["options"]) == 27
