"""I1: the "message zoo" and the frozen English message snapshot.

Why: from I2 on the engine emits tagged messages (`Msg`, server/i18n/messages.py) instead of bare English strings.
The golden (c_series_mixed_2014_baseline) pins the English text only where a golden draft happens to produce it (almost
no problems / warnings / pruned entries, ~3,300 disabledReason leaves). This module builds a much larger, deliberately
messy set of drafts (the "zoo") and snapshots every engine-written message-bearing leaf of their resolutions in
`golden/messages_en_snapshot.json.gz`. The snapshot was taken from the engine at HEAD BEFORE any message conversion; every
later slice must keep it identical (tests/test_i18n_snapshot.py).

The zoo
-------
- ``g/<golden case>``: every golden draft as stored (251 cases: the filled drafts, 4 family x ruleset x sources).
- ``clear/<case>``: the same with every selection cleared (class / species / background / equipment choices {}), so
  every card is pending and the disabled / export-gate paths run.
- ``half/<case>``: every class level halved (min 1), selections kept: stale picks are pruned, subclass unlock levels bite.
- ``r2024/<case>``: ruleset switched to 2024 with the selections kept (2014 background/species notes, pruned picks).
- ``ks2024/<id>`` and ``ks2024-as-2014/<id>``: the 2024 kitchen sinks (not in the golden), as built and switched to 2014.
- ``t/<name>``: hand-written triggers, one or more per problem / warning id family (TRIGGERS below).

Snapshot leaves per case (all engine-written English): ``problems`` / ``warnings`` as [id, message], ``pruned`` as
[choiceId, reason], ``disabled`` {"<cardId> | <optionId>": disabledReason}, ``cards`` {cardId: [label, description]},
``exportGate`` (app._pending_export_problems) as [id, message].

Policy: the snapshot only GROWS, through ``--append`` (new case names only; every stored case is re-resolved and must
be unchanged first). There is deliberately NO regenerate. ``--freeze`` writes the file once when it does not exist.

    cd server && ../.venv/bin/python tests/i18n_zoo.py --freeze      # first time only
    cd server && ../.venv/bin/python tests/i18n_zoo.py --append      # new cases only
    cd server && ../.venv/bin/python tests/i18n_zoo.py --coverage    # problem / warning id family coverage report

The whole thing needs the 5etools data (like the golden); tests skip without it.
"""
from __future__ import annotations

import ast
import copy
import glob
import gzip
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
SERVER = HERE.parent
for _p in (str(SERVER), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from catalog import official_source as official  # noqa: E402
from catalog.loader import load  # noqa: E402
from engine.resolve import resolve  # noqa: E402
import kitchen_sink as ks  # noqa: E402

GOLDEN = HERE / "golden" / "c_series_mixed_2014_baseline.json.gz"
SNAPSHOT = HERE / "golden" / "messages_en_snapshot.json.gz"

NEEDS_DATA = [m for m, ok in (("classes", official.has_official_classes), ("official", official.has_official),
                              ("spells", official.has_official_spells)) if not ok()]


# --- the hand-written triggers ---------------------------------------------------------------------------------

_ABIL = {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}


def base(**over) -> dict:
    """A clean SRD draft (Human / Acolyte, Fighter 8 Champion, nothing chosen): resolves with no problem or warning."""
    d = {"name": "Zoo", "ruleset": "mixed", "sources": [],
         "abilities": {"method": "manual", "base": dict(_ABIL)},
         "species": {"id": "human", "choices": {}}, "background": {"id": "acolyte", "choices": {}},
         "equipment": {"choices": {}, "added": [], "skipped": False},
         "classes": [{"classId": "fighter", "level": 8, "subclassId": "champion", "choices": {}}]}
    d.update(over)
    return d


def _with(**path_values):
    """A trigger from dotted-path assignments: `_with(**{"abilities.base.STR": "x"})`. Lists index with [i]."""
    def build() -> dict:
        d = base()
        for path, value in path_values.items():
            node = d
            parts = path.replace("[", ".").replace("]", "").split(".")
            for part in parts[:-1]:
                node = node[int(part)] if isinstance(node, list) else node[part]
            last = parts[-1]
            if isinstance(node, list):
                node[int(last)] = value
            else:
                node[last] = value
        return d
    return build


def _add(name: str, make, catalog: str | None = None) -> None:
    TRIGGERS[name] = make
    if catalog:
        TRIGGER_CATALOG[name] = catalog


def _equip(*entries, **extra) -> dict:
    d = base()
    d["equipment"]["added"] = [dict(e) for e in entries]
    d["equipment"].update(extra)
    return d


TRIGGERS: dict = {}
TRIGGER_CATALOG: dict[str, str] = {}  # trigger name -> catalog variant (see CATALOG_VARIANTS); default: the real catalog
PREREQ = {"usePrerequisites": {"feats": True, "multiclass": True}}


def _empty_2024_tables(catalog):
    """The catalog without the 2024 class / subclass resource tables (as test_class_resources does)."""
    cat = copy.copy(catalog)
    cat.class_2024_tables = {}
    cat.subclass_2024_tables = {}
    return cat


def _dropped_envelopes(catalog):
    """The Wizard and the Acolyte each gain a starting-equipment envelope the engine cannot show (it is dropped)."""
    bad = {"choose": 1, "type": "equipment", "from": {"option_set_type": "equipment", "equipment": []}}
    cat = copy.copy(catalog)
    cat.classes = dict(catalog.classes)
    wizard = dict(catalog.classes["wizard"])
    wizard["starting_equipment_options"] = [bad] + list(wizard["starting_equipment_options"])
    cat.classes["wizard"] = wizard
    cat.backgrounds = dict(catalog.backgrounds)
    acolyte = dict(catalog.backgrounds["acolyte"])
    acolyte["starting_equipment_options"] = [bad]
    cat.backgrounds["acolyte"] = acolyte
    return cat


CATALOG_VARIANTS = {"empty-2024-tables": _empty_2024_tables, "dropped-envelopes": _dropped_envelopes}

# normalize.py
_add("malformed-draft", lambda: "not a draft")
_add("malformed-draft-list", lambda: [1, 2])
_add("malformed-name", _with(name=5))
_add("malformed-sources", _with(sources="phb"))
_add("malformed-preferences", _with(preferences=5))
_add("malformed-use-prerequisites", _with(preferences={"usePrerequisites": 5}))
_add("malformed-abilities", _with(abilities=5))
_add("malformed-abilities-base", _with(**{"abilities.base": 5}))
_add("ability-invalid-str-text", _with(**{"abilities.base.STR": "lots"}))
_add("ability-invalid-dex-float", _with(**{"abilities.base.DEX": 12.5}))
_add("ability-out-of-range-low", _with(**{"abilities.base.CON": 0}))
_add("ability-out-of-range-high", _with(**{"abilities.base.INT": 99}))
_add("ability-above-20", _with(**{"abilities.base.WIS": 22}))
_add("ability-out-of-range-final", _with(**{"abilities.base.CHA": 30, "species.id": "human"}))
_add("ability-out-of-range-final-suffix", _with(**{"abilities.base.CHA": 99, "species.id": "human"}))
_add("malformed-class-id", _with(**{"classes[0]": {"classId": 7, "level": 1, "choices": {}}}))
_add("malformed-subclass-id", _with(**{"classes[0]": {"classId": "fighter", "subclassId": 7, "level": 3, "choices": {}}}))
_add("level-unsupported-text", _with(**{"classes[0]": {"classId": "fighter", "level": "many", "choices": {}}}))
_add("level-unsupported-zero", _with(**{"classes[0]": {"classId": "fighter", "level": 0, "choices": {}}}))
_add("level-unsupported-21", _with(**{"classes[0]": {"classId": "fighter", "level": 21, "choices": {}}}))
_add("malformed-choices", _with(**{"classes[0]": {"classId": "fighter", "level": 3, "choices": 4}}))
_add("malformed-choice-selection", _with(**{"classes[0]": {"classId": "fighter", "level": 3, "choices": {"class:fighter:1:prof-choice-0": "skill-athletics"}}}))
_add("malformed-choice-selection-entries", _with(**{"classes[0]": {"classId": "fighter", "level": 3, "choices": {"class:fighter:1:prof-choice-0": ["skill-athletics", 5, None]}}}))
_add("malformed-background-id", _with(**{"background.id": 5}))
_add("malformed-species-id", _with(**{"species.id": 5}))
_add("malformed-subspecies-id", _with(**{"species.subspeciesId": 5}))
_add("malformed-equipment", _with(equipment=4))
_add("malformed-equipment-choices-type", _with(**{"equipment.choices": 4}))
_add("malformed-equipment-added", _with(**{"equipment.added": 4}))
_add("equipment-qty-invalid-text", lambda: _equip({"itemId": "dagger", "qty": "two"}))
_add("equipment-qty-invalid-zero", lambda: _equip({"itemId": "dagger", "qty": 0}))
_add("malformed-equipment-worn", _with(**{"equipment.worn": 4}))
_add("malformed-equipment-wielded", _with(**{"equipment.wielded": 4}))
_add("malformed-equipment-worn-field", _with(**{"equipment.worn": {"armor": 4, "shield": "yes"}}))
_add("malformed-equipment-wielded-field", _with(**{"equipment.wielded": {"main": 4, "off": 5}}))

# resolve.py: ability methods
_add("point-buy-out-of-range", _with(**{"abilities.method": "pointbuy"}))  # base 16s are above 15
_add("point-buy-over-budget", _with(**{"abilities.method": "pointbuy", "abilities.base": {k: 15 for k in _ABIL}}))
_add("standard-array-mismatch", _with(**{"abilities.method": "standard"}))
_add("roll-out-of-range", _with(**{"abilities.method": "roll", "abilities.base": {"STR": 2, "DEX": 19, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}}))

# resolve.py: classes / subclass / background / species shape
_add("malformed-classes", _with(classes=5))
_add("malformed-class-entry", _with(classes=["fighter"]))
_add("duplicate-class", lambda: dict(base(), classes=[
    {"classId": "fighter", "level": 2, "choices": {}}, {"classId": "fighter", "level": 3, "choices": {}}]))
_add("unknown-class", _with(**{"classes[0]": {"classId": "artificer-x", "level": 3, "choices": {}}}))
_add("unknown-subclass", _with(**{"classes[0].subclassId": "no-such-subclass"}))
_add("subclass-mismatch", _with(**{"classes[0].subclassId": "berserker"}))
_add("subclass-not-unlocked", _with(**{"classes[0].level": 2}))
_add("total-level-exceeded", lambda: dict(base(), classes=[
    {"classId": "fighter", "level": 15, "choices": {}}, {"classId": "wizard", "level": 15, "choices": {}}]))
_add("malformed-background", _with(background=5))
_add("unknown-background", _with(**{"background.id": "no-such-background"}))
_add("malformed-species", _with(species=5))
_add("unknown-species", _with(**{"species.id": "no-such-species"}))
_add("unknown-subspecies", _with(**{"species.id": "elf", "species.subspeciesId": "no-such-lineage"}))
_add("subspecies-mismatch", _with(**{"species.id": "elf", "species.subspeciesId": "hill-dwarf"}))
_add("ruleset-invalid", _with(ruleset="2030"))
_add("ruleset-2014-bg-2024", _with(ruleset="2014", **{"background.id": "soldier-xphb"}))
_add("ruleset-2024-srd-origin", _with(ruleset="2024"))
_add("asi-double-dip", _with(**{"species.id": "dwarf-phb", "background.id": "soldier-xphb"}))
_add("source-hidden-background", _with(sources=["srd"], **{"background.id": "soldier-xphb"}))
_add("source-hidden-species", _with(sources=["srd"], **{"species.id": "human-xphb"}))
_add("source-hidden-subspecies", _with(sources=["srd"], **{"species.id": "dwarf-phb", "species.subspeciesId": "dwarf-phb-duergar-mtf"}))

# resolve.py: choices
_add("over-selected", _with(**{"classes[0]": {"classId": "fighter", "level": 3, "subclassId": "champion", "choices": {
    "class:fighter:1:prof-choice-0": ["skill-acrobatics", "skill-athletics", "skill-history", "skill-insight"]}}}))
_add("stale-choice-id", _with(**{"classes[0].choices": {"class:fighter:99:nothing": ["x"]}}))
_add("stale-choice-many", _with(**{"classes[0].choices": {f"class:fighter:99:nothing-{i}": ["x"] for i in range(40)}}))
_add("hp-roll-invalid", _with(preferences={"hitPointType": "manual"},
                              **{"classes[0].hpRolls": {"2": 99, "3": "x", "4": 0}}))
_add("equipment-envelope-dropped", _with(**{"classes[0]": {"classId": "wizard", "level": 1, "choices": {}}}),
     catalog="dropped-envelopes")

# equipment.py / worn.py
def _wizard_armor(*items, **abilities) -> dict:
    d = _equip(*items)
    d["classes"] = [{"classId": "wizard", "level": 3, "choices": {}}]
    d["abilities"] = {"method": "manual", "base": dict(_ABIL, **abilities)}
    return d


_add("armor-not-proficient", lambda: _wizard_armor({"itemId": "plate-armor", "qty": 1, "equipped": True}))
_add("armor-not-proficient-shield", lambda: _wizard_armor({"itemId": "shield", "qty": 1, "equipped": True}))
_add("armor-strength", lambda: dict(_equip({"itemId": "plate-armor", "qty": 1, "equipped": True}),
                                    abilities={"method": "manual", "base": dict(_ABIL, STR=8)}))
for _rid in ("aarakocra-mpmm", "aven-psa", "fairy-mpmm"):
    _add(f"fly-armor-{_rid}", lambda _rid=_rid: dict(_equip({"itemId": "chain-mail", "qty": 1, "equipped": True}),
                                                     species={"id": _rid, "choices": {}}))
_add("armor-multiple-body", lambda: _equip({"itemId": "chain-mail", "qty": 1, "equipped": True},
                                           {"itemId": "leather-armor", "qty": 1, "equipped": True}))
_add("worn-unknown-item", lambda: _equip(**{"worn": {"armor": "no-such-armor"}}))
_add("worn-not-in-inventory", lambda: _equip(**{"worn": {"armor": "chain-mail"}}))
_add("worn-armor-not-body-armor", lambda: _equip({"itemId": "shield", "qty": 1}, **{"worn": {"armor": "shield"}}))
_add("worn-shield-missing", lambda: _equip(**{"worn": {"shield": True}}))
_add("wielded-unknown-item", lambda: _equip(**{"wielded": {"main": "no-such-weapon"}}))
_add("wielded-not-in-inventory", lambda: _equip(**{"wielded": {"main": "longsword"}}))
_add("wielded-not-holdable", lambda: _equip({"itemId": "chain-mail", "qty": 1}, **{"wielded": {"main": "chain-mail"}}))
_add("wielded-main-shield", lambda: _equip({"itemId": "shield", "qty": 1}, **{"wielded": {"main": "shield"}}))
_add("wielded-same-item-twice", lambda: _equip({"itemId": "longsword", "qty": 1},
                                               **{"wielded": {"main": "longsword", "off": "longsword"}}))
_add("wielded-two-handed-conflict", lambda: _equip({"itemId": "greatsword", "qty": 1}, {"itemId": "dagger", "qty": 1},
                                                   **{"wielded": {"main": "greatsword", "off": "dagger"}}))
_add("wielded-shield-not-worn", lambda: _equip({"itemId": "shield", "qty": 1}, {"itemId": "longsword", "qty": 1},
                                               **{"wielded": {"main": "longsword", "off": "shield"},
                                                  "worn": {"shield": False}}))
_add("wielded-two-handed-shield", lambda: _equip({"itemId": "shield", "qty": 1}, {"itemId": "greatsword", "qty": 1},
                                                 **{"wielded": {"main": "greatsword"}, "worn": {"shield": True}}))


# --- feats ---------------------------------------------------------------------------------------------------------

def _asi(**picks) -> dict:
    d = base()
    d["classes"][0]["choices"] = {f"class:fighter:{k}:asi": v for k, v in picks.items()}
    return d


_add("feat-prerequisite-unmet-asi", lambda: dict(_asi(**{"4": ["feat:grappler-xphb"]}), preferences=PREREQ,
                                                 abilities={"method": "manual", "base": dict(_ABIL, STR=8, DEX=8)}))
_add("feat-prerequisite-unmet-species", lambda: dict(_asi(**{"4": ["feat:dragon-fear-xge"]}), preferences=PREREQ))
_add("feat-duplicate-species-card", lambda: dict(base(ruleset="2024"), preferences=PREREQ,
                                                 species={"id": "human-xphb", "choices": {"species:human-xphb:feat-0": ["feat:savage-attacker-xphb"]}},
                                                 background={"id": "soldier-xphb", "choices": {}}))
_add("fighting-style-duplicate", lambda: dict(base(), classes=[{"classId": "fighter", "level": 10, "subclassId": "champion", "choices": {
    "class:fighter:4:asi": ["feat:dueling-xphb"],
    "class:fighter:10:feature:additional-fighting-style": ["fighter-fighting-style-dueling"]}}]))
_add("feat-duplicate-asi", lambda: _asi(**{"4": ["feat:lucky-xphb"], "6": ["feat:lucky-xphb"]}))
_add("feat-hidden-by-filters-asi", lambda: dict(_asi(**{"4": ["feat:lucky-xphb"]}), sources=["srd"]))
_add("asi-over-cap", lambda: dict(_asi(**{"4": ["ability-str", "ability-str"]}),
                                  abilities={"method": "manual", "base": dict(_ABIL, STR=20)}))
_add("asi-bad-pick", lambda: _asi(**{"4": ["not-a-valid-asi-pick"]}))
_add("origin-feat-hidden", lambda: dict(base(ruleset="2024"), sources=["srd"],
                                        species={"id": "human-xphb", "choices": {}},
                                        background={"id": "soldier-xphb", "choices": {}}))
_add("multiclass-prerequisite-unmet", lambda: dict(base(), preferences=PREREQ, abilities={"method": "manual", "base": dict(_ABIL, INT=8)},
                                                   classes=[{"classId": "fighter", "level": 3, "choices": {}},
                                                            {"classId": "wizard", "level": 2, "choices": {}}]))
_add("multiclass-cleric-two", lambda: dict(base(), preferences=PREREQ, abilities={"method": "manual", "base": dict(_ABIL, WIS=8, STR=8)},
                                           classes=[{"classId": "fighter", "level": 3, "choices": {}},
                                                    {"classId": "paladin", "level": 2, "choices": {}},
                                                    {"classId": "cleric", "level": 2, "choices": {}}]))


# --- every kitchen-sink class under a hostile edit ---------------------------------------------------------------

def _wizard_draft(level=5, ruleset="mixed", **choices) -> dict:
    d = base(ruleset=ruleset)
    d["classes"] = [{"classId": "wizard", "level": level, "choices": dict(choices)}]
    return d


_add("wizard-spells-not-offered", lambda: _wizard_draft(**{
    "class:wizard:spells-cantrips": ["fire-bolt", "fire-bolt", "no-such-spell"],
    "class:wizard:spellbook": ["magic-missile", "no-such-spell", "wish"]}))
_add("wizard-spells-too-many", lambda: _wizard_draft(**{
    "class:wizard:spells-cantrips": ["fire-bolt", "light", "mage-hand", "prestidigitation", "ray-of-frost"]}))
_add("wizard-2024-spells", lambda: _wizard_draft(ruleset="2024", **{
    "class:wizard:spells-cantrips": ["fire-bolt-xphb", "light-xphb", "mage-hand-xphb", "shocking-grasp-xphb"],
    "class:wizard:spellbook": ["magic-missile-xphb", "shield-xphb"]}))


def _fighter_2024(**choices) -> dict:
    d = base(ruleset="2024")
    d["species"] = {"id": "human-xphb", "choices": {}}
    d["background"] = {"id": "soldier-xphb", "choices": {}}
    d["classes"] = [{"classId": "fighter", "level": 6, "choices": dict(choices)}]
    return d


_add("fighter-2024-bad-style", lambda: _fighter_2024(**{"class:fighter:1:fighting-style": ["feat:no-such-xphb"]}))
_add("fighter-2024-style-duplicate", lambda: dict(_fighter_2024(**{
    "class:fighter:1:fighting-style": ["feat:dueling-xphb"], "class:fighter:4:asi": ["feat:dueling-xphb"]})))
_add("fighter-2024-mastery-bad", lambda: _fighter_2024(**{"class:fighter:weapon-mastery": ["no-such", "longsword", "longsword", "dagger", "club", "mace", "pike"]}))
_add("bard-multiclass-skill-duplicate", lambda: dict(base(), classes=[
    {"classId": "rogue", "level": 3, "choices": {"class:rogue:1:prof-choice-0": ["skill-acrobatics", "skill-athletics", "skill-stealth", "skill-insight"]}},
    {"classId": "bard", "level": 2, "choices": {"class:bard:multiclass-prof-choice-0": ["skill-acrobatics"]}}]))
_add("warlock-invocation-stale", lambda: dict(base(), classes=[{"classId": "warlock", "level": 5, "choices": {
    "class:warlock:2:invocations:eldritch-invocations": ["eldritch-invocation-agonizing-blast", "eldritch-invocation-no-such"],
    "class:warlock:spells-cantrips": ["minor-illusion", "mage-hand"]}}]))
_add("warlock-2024-invocation-stale", lambda: dict(base(ruleset="2024"), classes=[{"classId": "warlock", "level": 7, "choices": {
    "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations": ["opt-agonizing-blast-xphb", "opt-pact-of-the-blade-xphb"],
    "class:warlock:invocation:opt-agonizing-blast-xphb:cantrip": ["eldritch-blast-xphb"],
    "class:warlock:invocation:opt-pact-of-the-blade-xphb:weapon": ["longsword"],
    "class:warlock:spells-cantrips": ["minor-illusion-xphb", "mage-hand-xphb"]}}]))
_add("cleric-2024-mismatch", lambda: dict(base(ruleset="2024"), classes=[{"classId": "cleric", "level": 5, "choices": {
    "class:cleric:1:divine-order": ["xphb-cleric-protector", "xphb-cleric-thaumaturge"]}}]))
_add("ranger-2024-expertise", lambda: dict(base(ruleset="2024"), classes=[{"classId": "ranger", "level": 9, "choices": {
    "class:ranger:2:expertise-choice:ranger-expertise-1": ["skill-stealth", "skill-stealth"]}}]))
_add("bard-2024-magical-secrets", lambda: dict(base(ruleset="2024"), classes=[{"classId": "bard", "level": 10, "choices": {
    "class:bard:spells-known": ["vicious-mockery-xphb", "vicious-mockery-xphb"]}}]))
_add("background-languages-duplicate", lambda: dict(base(), background={"id": "acolyte", "choices": {
    "background:acolyte:languages": ["common", "common"]}}, species={"id": "human", "choices": {
        "species:human:languages": ["common"]}}))
_add("sorcerer-metamagic-too-many", lambda: dict(base(), classes=[{"classId": "sorcerer", "level": 3, "choices": {
    "class:sorcerer:3:metamagic": ["careful-spell", "distant-spell", "empowered-spell", "extended-spell", "heightened-spell"]}}]))
_add("barbarian-2024-weapon-mastery", lambda: dict(base(ruleset="2024"), classes=[{"classId": "barbarian", "level": 3, "choices": {
    "class:barbarian:weapon-mastery": ["greataxe", "greataxe", "no-such"]}}]))
_add("subclass-spell-school-limit", lambda: dict(base(), classes=[{"classId": "fighter", "level": 8, "subclassId": "eldritch-knight-phb", "choices": {
    "class:fighter:spells-known": ["charm-person", "sleep", "identify", "detect-magic", "disguise-self", "hold-person",
                                   "invisibility", "mirror-image"]}}]))
_add("class-2024-tables-missing", lambda: dict(base(ruleset="2024"), classes=[
    {"classId": "barbarian", "level": 5, "choices": {}}, {"classId": "rogue", "level": 3, "choices": {}}]),
     catalog="empty-2024-tables")
_add("subclass-2024-tables-missing", lambda: dict(base(ruleset="2024"), classes=[
    {"classId": "fighter", "level": 9, "subclassId": "psi-warrior-xphb", "choices": {}}]), catalog="empty-2024-tables")


# --- the zoo -------------------------------------------------------------------------------------------------------

def _clear(d: dict) -> dict:
    d = copy.deepcopy(d)
    for entry in d.get("classes") or []:
        entry["choices"] = {}
    for key in ("species", "background"):
        if isinstance(d.get(key), dict):
            d[key]["choices"] = {}
    if isinstance(d.get("equipment"), dict):
        d["equipment"]["choices"] = {}
    return d


def _half(d: dict) -> dict:
    d = copy.deepcopy(d)
    for entry in d.get("classes") or []:
        entry["level"] = max(1, int(entry["level"]) // 2)
    return d


def _ruleset(d: dict, ruleset: str) -> dict:
    d = copy.deepcopy(d)
    d["ruleset"] = ruleset
    return d


def golden_drafts() -> dict[str, dict]:
    data = json.load(gzip.open(GOLDEN, "rt"))
    return {name: entry["draft"] for name, entry in data.items()}


def zoo(catalog) -> dict[str, dict]:
    """case name -> draft (JSON-ready). Deterministic."""
    cases: dict[str, dict] = {}
    for name, draft in golden_drafts().items():
        cases[f"g/{name}"] = draft
        cases[f"clear/{name}"] = _clear(draft)
        cases[f"half/{name}"] = _half(draft)
        cases[f"r2024/{name}"] = _ruleset(draft, "2024")
    for sid, spec in ks.KITCHEN_SINK.items():
        if spec["ruleset"] != "2024" or ks.skip_reason(spec):
            continue
        built = ks.build(sid, catalog, resolve)
        cases[f"ks2024/{sid}"] = built
        cases[f"ks2024-as-2014/{sid}"] = _ruleset(built, "2014")
    for name, make in TRIGGERS.items():
        cases[f"t/{name}"] = make()
    return cases


# --- snapshot leaves -------------------------------------------------------------------------------------------------

def _export_gate(resolution: dict) -> list:
    import app  # noqa: PLC0415  (heavy: loads the Flask app and the catalog, so only here)
    return [[p["id"], str(p["message"])] for p in app._pending_export_problems(resolution)]


def leaves(resolution: dict) -> dict:
    """The engine-written English leaves of one resolution, as plain strings (a `Msg` is stored as its text)."""
    disabled, cards = {}, {}
    for card in resolution.get("choices") or []:
        cards[card["id"]] = [str(card.get("label", "")), str(card.get("description", ""))]
        for opt in card.get("options") or []:
            if opt.get("disabledReason") is not None:
                disabled[f"{card['id']} | {opt['id']}"] = str(opt["disabledReason"])
    return {
        "problems": [[p["id"], str(p["message"])] for p in resolution.get("problems") or []],
        "warnings": [[p["id"], str(p["message"])] for p in resolution.get("warnings") or []],
        "pruned": [[p["choiceId"], str(p["reason"])] for p in resolution.get("pruned") or []],
        "disabled": disabled,
        "cards": cards,
        "exportGate": _export_gate(resolution),
    }


LOCALIZED_CARD_KEYS = ("label", "description", "unavailableReason")


def without_localized(resolution: dict) -> dict:
    """The resolution with every engine-localized card text dropped (card label / description / unavailableReason and
    each option's disabledReason; I4, I5), to compare the rest of two languages' resolutions."""
    out = dict(resolution)
    out["choices"] = [{**{k: v for k, v in c.items() if k not in LOCALIZED_CARD_KEYS},
                       "options": [{k: v for k, v in o.items() if k != "disabledReason"} for o in c.get("options") or []]}
                      for c in resolution.get("choices") or []]
    return out


def catalog_for(name: str, catalog):
    """The catalog a zoo case resolves against: the real one, or a degraded variant for a few triggers."""
    variant = TRIGGER_CATALOG.get(name[len("t/"):]) if name.startswith("t/") else None
    return CATALOG_VARIANTS[variant](catalog) if variant else catalog


def case_leaves(draft, catalog) -> dict:
    return json.loads(json.dumps(leaves(resolve(copy.deepcopy(draft), catalog))))


def build_snapshot(catalog, names: list[str] | None = None) -> dict:
    cases = zoo(catalog)
    return {name: case_leaves(cases[name], catalog_for(name, catalog)) for name in (names or sorted(cases))}


def load_snapshot() -> dict:
    return json.load(gzip.open(SNAPSHOT, "rt")) if SNAPSHOT.exists() else {}


def _write(data: dict) -> None:
    with gzip.open(SNAPSHOT, "wt", compresslevel=9) as f:
        json.dump(data, f, sort_keys=True, separators=(",", ":"))


def freeze() -> None:
    if SNAPSHOT.exists():
        raise SystemExit(f"{SNAPSHOT.name} exists: the snapshot is never regenerated; use --append for new cases")
    if NEEDS_DATA:
        raise SystemExit(f"5etools data missing: {', '.join(NEEDS_DATA)}")
    data = build_snapshot(load())
    _write(data)
    print(f"froze {len(data)} cases, {SNAPSHOT.stat().st_size} bytes")


def append() -> None:
    """Add cases whose names are not stored yet. Every stored case is re-resolved first and must be unchanged."""
    catalog = load()
    old = load_snapshot()
    cases = zoo(catalog)
    for name, stored in old.items():
        assert case_leaves(cases[name], catalog_for(name, catalog)) == stored, f"stored zoo case changed: {name}"
    new = [n for n in sorted(cases) if n not in old]
    for name in new:
        old[name] = case_leaves(cases[name], catalog_for(name, catalog))
    _write(old)
    print(f"kept {len(old) - len(new)} stored cases unchanged, added {len(new)}: {new}")


# --- coverage of the problem / warning id families --------------------------------------------------------------------

def _template_rx(template: str) -> str:
    """A regex for the text a catalog template produces: literals escaped, every field (plural fields too) `.*?`."""
    import string
    out = []
    for literal, field, _spec, _conv in string.Formatter().parse(template):
        out.append(re.escape(literal))
        if field is not None:
            out.append(".*?")
    return "".join(out)


def _is_msg_call(node) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "msg"
            and bool(node.args) and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str))


def declared_families() -> dict[str, str]:
    """`file:line` -> "<id regex>  ||  <message regex>" for every problem / warning emission site in the engine and the
    app (I2: the message is a `msg("<key>", ...)` call, so its regex comes from the key's English catalog template;
    f-string holes in the id become `.*?`). A site is a dict literal with an "id" and a "message" whose value is a
    `msg(...)` call, or a tuple `("<id>", msg(...), ...)` (the export gate's three "choose a ... first" rows)."""
    from i18n.catalog import MESSAGES

    def rx_of(node) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return re.escape(node.value)
        if isinstance(node, ast.JoinedStr):
            return "".join(re.escape(v.value) if isinstance(v, ast.Constant) else ".*?" for v in node.values)
        return "<expr>"

    out: dict[str, str] = {}
    for path in sorted(glob.glob(str(SERVER / "engine" / "*.py"))) + [str(SERVER / "app.py")]:
        tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
        name = pathlib.Path(path).name
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                keys = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
                if "id" in keys and _is_msg_call(keys.get("message")):
                    out[f"{name}:{node.lineno}"] = f"{rx_of(keys['id'])}  ||  {_template_rx(MESSAGES[keys['message'].args[0].value]['en'])}"
            elif isinstance(node, ast.Tuple) and len(node.elts) >= 2 and _is_msg_call(node.elts[1]) \
                    and isinstance(node.elts[0], ast.Constant) and isinstance(node.elts[0].value, str):
                out[f"{name}:{node.lineno}"] = f"{rx_of(node.elts[0])}  ||  {_template_rx(MESSAGES[node.elts[1].args[0].value]['en'])}"
    return out



# --- AST helpers shared by the I3-I5 catalog tests -----------------------------------------------------------------------

SERVER_FILES = sorted(glob.glob(str(SERVER / "engine" / "*.py"))) + [str(SERVER / n) for n in (
    "app.py", "export.py", "export_fields.py", "markdown_export.py", "pdf_export.py")]
# I5: the catalog modules that write card texts (a label of a data table, the equipment card builder); the earlier guards
# scan SERVER_FILES only (data tables carry plain "reason" keys of their own)
CATALOG_FILES = [str(SERVER / n) for n in ("catalog/choices.py", "catalog/reference_data.py", "catalog/feat_effects_data.py")]


def server_trees(*, with_catalog: bool = False):
    for path in SERVER_FILES + (CATALOG_FILES if with_catalog else []):
        yield path, ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))


def msg_calls(*, with_catalog: bool = False) -> list[tuple]:
    """(file, line, key, keyword names, has ** splat) for every `msg("<key>", ...)` call in the server code."""
    out = []
    for path, tree in server_trees(with_catalog=with_catalog):
        for node in ast.walk(tree):
            if _is_msg_call(node):
                out.append((pathlib.Path(path).name, node.lineno, node.args[0].value,
                            {k.arg for k in node.keywords if k.arg}, any(k.arg is None for k in node.keywords)))
    return out


def observed_pairs(snapshot: dict) -> set[tuple[str, str]]:
    pairs = set()
    for leaf in snapshot.values():
        for key in ("problems", "warnings", "exportGate"):
            pairs.update((i, m) for i, m in leaf[key])
    return pairs


def coverage(snapshot: dict) -> tuple[dict[str, str], dict[str, str]]:
    """(covered, uncovered): `file:line` -> pattern, split by whether any observed (id, message) pair matches both
    halves of it. A non-literal id or message (`<expr>`) matches anything on that half."""
    seen = observed_pairs(snapshot)
    covered, uncovered = {}, {}
    for site, rx in declared_families().items():
        id_rx, msg_rx = rx.split("  ||  ")
        hit = any((id_rx == "<expr>" or re.fullmatch(id_rx, i, re.S)) and (msg_rx == "<expr>" or re.fullmatch(msg_rx, m, re.S))
                  for i, m in seen)
        (covered if hit else uncovered)[site] = rx
    return covered, uncovered


def main(argv: list[str]) -> None:
    if argv == ["--freeze"]:
        freeze()
    elif argv == ["--append"]:
        append()
    elif argv == ["--coverage"]:
        snap = load_snapshot() or build_snapshot(load())
        covered, uncovered = coverage(snap)
        print(f"{len(snap)} cases; id sites covered {len(covered)} of {len(covered) + len(uncovered)}")
        for site, rx in sorted(uncovered.items()):
            print(f"  NOT COVERED {site}  {rx}")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
