"""X2: per-turn / per-combat / per-rage / other non-rest recharges as a resource kind.

The recharge vocabulary of every resource (class, subclass, feat, species) is ``long | short | short-or-long`` plus the
four X2 words ``turn | combat | rage | other`` (``reference_data.RESOURCE_RECHARGES``). ``other`` carries its exact
condition in ``details.note``. A feature whose catalog text limits its main effect to "once per turn" / "once per
combat" / "once per rage" is a resource with ``uses`` 1 and that recharge.

Rule matrix (catalog text, tags stripped; ``QUOTE`` below pins every sentence, ``test_quotes_match_catalog``):

 SPECIES (non-2024, ``SPECIES_RESOURCES_2014``)
  Hobgoblin (DMG) Martial Advantage   "Once per turn, you can deal an extra 2d6 damage ..."                  -> 1, turn
  Bugbear (ERLW, VGM) Surprise Attack "You can use this trait only once per combat."                          -> 1, combat
  Tabaxi (MPMM, VGM) Feline Agility   "... you can't use it again until you move 0 feet on one of your turns." -> 1, other
 CLASS / SUBCLASS (existing note-only rows, ``uses`` None / ``recharge`` None before X2)
  Foe Slayer, 2024 Stunning Strike, every domain Divine Strike (Life + 11 book domains), Order's Wrath, Ferocious
  Charger, Deft Strike, TCE Hand of Harm, TCE Dreadful Strikes, Gathered Swarm, Empowered Healing, Genie's Wrath,
  Grim Harvest                                                                                   -> 1, turn
  Fanatical Focus "You can use this ability only once per rage."                                  -> 1, rage
  NEW rows: Rapid Strike, Unerring Accuracy, Stalker's Flurry, Spell Bombardment, 2024 Dreadful Strikes, Radiant Soul,
  Superior Hunter's Prey                                                                         -> 1, turn
  2024 Travel Along the Tree "once per Rage, you can increase the range of that teleport to 150 feet" -> 1, rage
 ENGINE (class builders with dice)
  Sneak Attack (2014 and 2024), 2024 Divine Strike, 2024 Primal Strike                            -> 1, turn
"""
from __future__ import annotations

from perf_helpers import assert_fast
import pathlib
import re
import time

import pytest

import export_fields
from catalog import reference_data as ref
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

VOCAB = ("long", "short", "short-or-long", "turn", "combat", "rage", "other")
WORDS = {"turn": "на ход", "combat": "на битка", "rage": "на ярост", "other": "виж бележката"}
ROOT = pathlib.Path(__file__).resolve().parents[2]
ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _plain(node):
    text = " ".join(node) if isinstance(node, list) else str(node)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\s+", " ", re.sub(r"\{@(\w+) ([^}]*)\}", tag, text))


# ---------------------------------------------------------------- vocabulary (one list, four consumers)

def test_vocabulary_constant():
    assert tuple(ref.RESOURCE_RECHARGES) == VOCAB


def test_export_words_cover_the_vocabulary_with_bulgarian_words():
    assert set(export_fields._RECHARGE_WORDS) == set(VOCAB)
    for key, word in WORDS.items():
        assert export_fields._RECHARGE_WORDS[key] == word


def test_frontend_describe_resource_words_equal_the_export_words():
    # SK5: the words moved from ClassResourcesList.tsx into the copy module (resourceText.ts reads them from there)
    src = (ROOT / "frontend/src/copy/bg.ts").read_text(encoding="utf-8")
    block = re.search(r"recharge: \{(.*?)\} as Record<string, string>", src, re.S).group(1)
    words = {m.group(1) or m.group(2): m.group(3) for m in re.finditer(r'(?:"([\w-]+)"|(\w+)):\s*"([^"]+)"', block)}
    assert words == export_fields._RECHARGE_WORDS


def test_types_ts_union_equals_the_vocabulary():
    src = (ROOT / "frontend/src/types.ts").read_text(encoding="utf-8")
    union = re.search(r"export interface ResourceCore \{.*?recharge: ([^;]+);", src, re.S).group(1)
    members = re.findall(r'"([\w-]+)"', union)
    assert tuple(members) == VOCAB and union.strip().endswith("| null")


def _all_recharges():
    tables = (ref.SPECIES_RESOURCES, ref.SPECIES_RESOURCES_2014)
    for table in tables:
        for tid, spec in table.items():
            yield tid, spec.get("recharge")
    for name in ("RESOURCE_TAIL_2014", "RESOURCE_TAIL_2024", "SUBCLASS_TAIL_2014", "SUBCLASS_TAIL_2014_BOOKS",
                 "SUBCLASS_TAIL_2024"):
        for spec in getattr(ref, name):
            recharge = spec["recharge"]
            if isinstance(recharge, tuple):  # staged: (default, ((feature id, value), ...))
                yield spec["feature"], recharge[0]
                for _fid, value in recharge[1]:
                    yield spec["feature"], value
            else:
                yield spec["feature"], recharge
            for _fid, value in spec.get("recharge_stages") or ():
                yield spec["feature"], value


def test_every_table_recharge_is_in_the_vocabulary():
    bad = [(k, v) for k, v in _all_recharges() if v is not None and v not in VOCAB]
    assert not bad, bad


# ---------------------------------------------------------------- species

SPECIES = {  # trait id -> (race id, name, recharge, pinned sentence)
    "hobgoblin-dmg-trait-0": ("hobgoblin-dmg", "Martial Advantage", "turn",
                              "Once per turn, you can deal an extra 2d6 damage to a creature you hit with a weapon attack"),
    "bugbear-erlw-trait-7": ("bugbear-erlw", "Surprise Attack", "combat", "You can use this trait only once per combat."),
    "bugbear-vgm-trait-6": ("bugbear-vgm", "Surprise Attack", "combat", "You can use this trait only once per combat."),
    "tabaxi-mpmm-trait-5": ("tabaxi-mpmm", "Feline Agility", "other",
                            "you can't use it again until you move 0 feet on one of your turns."),
    "tabaxi-vgm-trait-3": ("tabaxi-vgm", "Feline Agility", "other",
                           "you can't use it again until you move 0 feet on one of your turns."),
}


@pytest.mark.parametrize("tid", list(SPECIES))
def test_species_entries_are_pinned_and_shaped(catalog, tid):
    race, name, recharge, sentence = SPECIES[tid]
    spec = ref.SPECIES_RESOURCES_2014[tid]
    assert (spec["race"], spec["name"], spec["uses"], spec["recharge"]) == (race, name, 1, recharge)
    text = _plain(catalog.traits[tid]["desc"])
    assert sentence in text and catalog.traits[tid]["name"] == name
    assert sentence in spec["quotes"] or any(sentence in q for q in spec["quotes"])
    for quote in spec["quotes"]:
        assert quote in text, (tid, quote)
    assert tid in [t["index"] for t in catalog.races[race]["traits"]]
    assert catalog.races[race]["ruleset"] == "2014"


def _species(catalog, species, level=5, ruleset="2014", cls="fighter"):
    d = {"name": "t", "ruleset": ruleset, "sources": [], "classes": [{"classId": cls, "level": level, "choices": {}}],
         "background": {"id": "acolyte", "choices": {}}, "species": {"id": species, "choices": {}},
         "abilities": {"method": "manual", "base": {a: 12 for a in ABS}},
         "equipment": {"choices": {}, "added": [], "skipped": True}, "details": {}, "preferences": {}}
    return resolve(d, catalog)


@pytest.mark.parametrize("tid", list(SPECIES))
@pytest.mark.parametrize("ruleset", ["2014", "mixed"])
def test_species_resolve_to_one_use_with_the_new_recharge(catalog, tid, ruleset):
    race, name, recharge, _s = SPECIES[tid]
    res = _species(catalog, race, ruleset=ruleset)["derived"]["speciesResources"]
    entry = next(r for r in res if r["traitId"] == tid)
    assert (entry["uses"], entry["recharge"], entry["name"]) == (1, recharge, name)
    assert entry["id"] == f"species:{race}:{name.lower().replace(' ', '-')}"
    assert entry["details"]["note"]
    assert WORDS[recharge] in export_fields.resource_line(entry)


def test_other_recharge_names_its_condition_in_the_note(catalog):
    for race in ("tabaxi-mpmm", "tabaxi-vgm"):
        entry = _species(catalog, race)["derived"]["speciesResources"][0]
        assert entry["recharge"] == "other"
        assert "move 0 feet on one of your turns" in entry["details"]["note"]
        assert "double your speed" in entry["details"]["note"]


def test_species_without_these_traits_get_no_such_entry(catalog):
    for race in ("human", "goblin-mpmm", "kobold-vgm"):
        res = _species(catalog, race)["derived"]["speciesResources"]
        assert not [r for r in res if r["recharge"] in ("turn", "combat", "rage", "other")
                    and r["traitId"] in SPECIES], race


def test_the_2024_species_table_is_unchanged_by_x2():
    assert not set(SPECIES) & set(ref.SPECIES_RESOURCES)
    assert all(spec["recharge"] in ("long", "short", "short-or-long", None) for spec in ref.SPECIES_RESOURCES.values())


# ---------------------------------------------------------------- class / subclass / feature upgrades

PHRASE = re.compile(r"once (?:per|on each|during each|each) (?:of (?:your|the cleric's) )?(?:turn|turns|combat|rage|round)"
                    r"|only once per (?:turn|rage|round)|once on each of your turns|once per rage", re.I)

# (table, subclass or None, feature id, name, recharge, pinned sentence); the row keeps its older note, X2 sets
# uses 1 + recharge and appends the sentence to the row's quotes.
UPGRADES = (
    ("RESOURCE_TAIL_2014", None, "foe-slayer", "Foe Slayer", "turn",
     "Once on each of your turns, you can add your Wisdom modifier to the attack roll or the damage roll"),
    ("RESOURCE_TAIL_2024", None, "xphb-monk-5-stunning-strike", "Stunning Strike", "turn",
     "Once per turn when you hit a creature with a Monk weapon or an Unarmed Strike"),
    ("SUBCLASS_TAIL_2014", "life", "divine-strike", "Divine Strike (Life Domain)", "turn",
     "Once on each of your turns when you hit a creature with a weapon attack"),
) + tuple(
    ("SUBCLASS_TAIL_2014_BOOKS", sub, f"{sub}-8-divine-strike", f"Divine Strike ({dom} Domain)", "turn",
     "Once on each of your turns when you hit a creature with a weapon attack")
    for sub, dom in (("forge-xge", "Forge"), ("nature-phb", "Nature"), ("order-tce", "Order"), ("solidarity-psa", "Solidarity"),
                     ("strength-psa", "Strength"), ("tempest-phb", "Tempest"), ("trickery-phb", "Trickery"),
                     ("twilight-tce", "Twilight"), ("war-phb", "War"), ("zeal-psa", "Zeal"))
) + (
    ("SUBCLASS_TAIL_2014_BOOKS", "death-dmg", "death-dmg-8-divine-strike", "Divine Strike (Death Domain)", "turn",
     "Once on each of the cleric's turns when he or she hits a creature with a weapon attack"),
    ("SUBCLASS_TAIL_2014_BOOKS", "order-tce", "order-tce-17-orders-wrath", "Order's Wrath", "turn",
     "You can curse a creature in this way only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "cavalier-xge", "cavalier-xge-15-ferocious-charger", "Ferocious Charger", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "kensei-xge", "kensei-xge-6-one-with-the-blade", "Deft Strike", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "mercy-tce", "mercy-tce-3-hand-of-harm", "Hand of Harm", "turn",
     "You can use this feature only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "fey-wanderer-tce", "fey-wanderer-tce-3-dreadful-strikes", "Dreadful Strikes", "turn",
     "which can take this extra damage only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "swarmkeeper-tce", "swarmkeeper-tce-3-gathered-swarm", "Gathered Swarm", "turn",
     "Once on each of your turns, you can cause the swarm to assist you"),
    ("SUBCLASS_TAIL_2014_BOOKS", "divine-soul-xge", "divine-soul-xge-6-empowered-healing", "Empowered Healing", "turn",
     "You can use this feature only once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "genie-tce", "genie-tce-1-genies-vessel", "Genie's Wrath", "turn",
     "Once during each of your turns when you hit with an attack roll"),
    ("SUBCLASS_TAIL_2014_BOOKS", "necromancy-phb", "necromancy-phb-2-grim-harvest", "Grim Harvest", "turn",
     "Once per turn when you kill one or more creatures with a spell of 1st level or higher"),
    ("SUBCLASS_TAIL_2014_BOOKS", "zealot-xge", "zealot-xge-6-fanatical-focus", "Fanatical Focus", "rage",
     "You can use this ability only once per rage"),
    # new rows
    ("SUBCLASS_TAIL_2014_BOOKS", "samurai-xge", "samurai-xge-15-rapid-strike", "Rapid Strike", "turn",
     "You can do so no more than once per turn"),
    ("SUBCLASS_TAIL_2014_BOOKS", "kensei-xge", "kensei-xge-17-unerring-accuracy", "Unerring Accuracy", "turn",
     "You can use this feature only once on each of your turns"),
    ("SUBCLASS_TAIL_2014_BOOKS", "gloom-stalker-xge", "gloom-stalker-xge-11-stalkers-flurry", "Stalker's Flurry", "turn",
     "Once on each of your turns when you miss with a weapon attack"),
    ("SUBCLASS_TAIL_2014_BOOKS", "wild-phb", "wild-phb-18-spell-bombardment", "Spell Bombardment", "turn",
     "You can use the feature only once per turn"),
    ("SUBCLASS_TAIL_2024", "fey-wanderer-xphb", "fey-wanderer-xphb-3-dreadful-strikes", "Dreadful Strikes", "turn",
     "which can take this extra damage only once per turn"),
    ("SUBCLASS_TAIL_2024", "celestial-xphb", "celestial-xphb-6-radiant-soul", "Radiant Soul", "turn",
     "Once per turn, when a spell you cast deals Radiant or Fire damage"),
    ("SUBCLASS_TAIL_2024", "hunter-xphb", "hunter-xphb-11-superior-hunters-prey", "Superior Hunter's Prey", "turn",
     "Once per turn when you deal damage to a creature marked by your Hunter's Mark"),
    ("SUBCLASS_TAIL_2024", "world-tree-xphb", "world-tree-xphb-14-travel-along-the-tree", "Travel Along the Tree", "rage",
     "once per Rage, you can increase the range of that teleport to 150 feet"),
)


def _row(table, sub, feature, name):
    rows = [s for s in getattr(ref, table) if s["feature"] == feature and s["name"] == name
            and (sub is None or s.get("subclass") == sub)]
    assert len(rows) == 1, (table, feature, name, len(rows))
    return rows[0]


@pytest.mark.parametrize("table,sub,feature,name,recharge,sentence", UPGRADES)
def test_quotes_match_catalog(catalog, table, sub, feature, name, recharge, sentence):
    text = _plain(catalog.features[feature]["desc"])
    assert sentence in text, (feature, sentence)
    row = _row(table, sub, feature, name)
    assert any(sentence in q[1] for q in row["quotes"]), f"{feature}: the row's quotes do not pin the sentence"
    for fid, quote in row["quotes"]:
        assert quote in _plain(catalog.features[fid]["desc"]), (feature, quote)


@pytest.mark.parametrize("table,sub,feature,name,recharge,sentence", UPGRADES)
def test_row_state(table, sub, feature, name, recharge, sentence):
    row = _row(table, sub, feature, name)
    assert row["uses"] == 1 and row["recharge"] == recharge
    assert row["recharge"] in VOCAB


def _char(catalog, cls, level, sub, ruleset):
    d = {"ruleset": ruleset, "sources": [], "abilities": {"method": "manual", "base": {
        "STR": 14, "DEX": 14, "CON": 14, "INT": 12, "WIS": 12, "CHA": 12}},
         "species": {"id": "human"}, "background": {"id": "acolyte"},
         "classes": [{"classId": cls, "level": level, **({"subclassId": sub} if sub else {}), "choices": {}}]}
    return resolve(d, catalog)


@pytest.mark.parametrize("table,sub,feature,name,recharge,sentence", UPGRADES)
def test_resolved_resource(catalog, table, sub, feature, name, recharge, sentence):
    row = _row(table, sub, feature, name)
    level = catalog.features[feature]["level"]
    rulesets = ["2024"] if table.endswith("2024") else ["2014", "mixed"]
    for ruleset in rulesets:
        res = _char(catalog, row["class"], max(level, 3), sub, ruleset)
        entries = [r for r in res["derived"]["classResources"] if r["name"] == name]
        assert len(entries) == 1, (ruleset, name, [r["name"] for r in res["derived"]["classResources"]])
        entry = entries[0]
        assert (entry["uses"], entry["recharge"]) == (1, recharge), (ruleset, name)
        assert WORDS[recharge] in export_fields.resource_line(entry)


def test_below_the_feature_level_there_is_no_entry(catalog):
    res = _char(catalog, "monk", 3, "kensei-xge", "2014")
    assert "Unerring Accuracy" not in [r["name"] for r in res["derived"]["classResources"]]
    res = _char(catalog, "barbarian", 5, "zealot-xge", "2014")
    assert "Fanatical Focus" not in [r["name"] for r in res["derived"]["classResources"]]


def test_other_subclass_and_other_ruleset_do_not_see_the_rows(catalog):
    res = _char(catalog, "monk", 17, "open-hand", "2014")
    assert "Unerring Accuracy" not in [r["name"] for r in res["derived"]["classResources"]]
    res = _char(catalog, "monk", 17, "kensei-xge", "2024")  # kensei has no XPHB record: no 2014 table row under 2024
    assert "Unerring Accuracy" not in [r["name"] for r in res["derived"]["classResources"]]


def test_the_reference_data_upgrade_list_is_the_existing_rows_of_this_matrix():
    mine = set(ref.X2_RECHARGE_UPGRADES)
    assert len(mine) == len(ref.X2_RECHARGE_UPGRADES) == 24
    assert mine <= set(UPGRADES)
    new = set(UPGRADES) - mine
    assert {u[3] for u in new} == {"Rapid Strike", "Unerring Accuracy", "Stalker's Flurry", "Spell Bombardment",
                                   "Dreadful Strikes", "Radiant Soul", "Superior Hunter's Prey", "Travel Along the Tree"}


def test_every_domain_divine_strike_row_is_a_turn_resource():
    rows = [s for t in ("SUBCLASS_TAIL_2014", "SUBCLASS_TAIL_2014_BOOKS") for s in getattr(ref, t)
            if s["name"].startswith("Divine Strike (")]
    assert len(rows) == 12
    assert all(s["uses"] == 1 and s["recharge"] == "turn" for s in rows)


# ---------------------------------------------------------------- engine builders with dice

def test_sneak_attack_is_one_use_per_turn_under_every_ruleset(catalog):
    for ruleset in ("2014", "mixed", "2024"):
        entry = next(r for r in _char(catalog, "rogue", 5, None, ruleset)["derived"]["classResources"]
                     if r["name"] == "Sneak Attack")
        assert (entry["uses"], entry["recharge"], entry["dice"]) == (1, "turn", "3d6")


def test_2024_divine_and_primal_strike_are_one_use_per_turn(catalog):
    picks = {"cleric": ("class:cleric:7:feature:xphb-cleric-7-blessed-strikes", "xphb-cleric-7-divine-strike", "Divine Strike"),
             "druid": ("class:druid:7:feature:xphb-druid-7-elemental-fury", "xphb-druid-7-primal-strike", "Primal Strike")}
    for cls, (card, option, name) in picks.items():
        d = {"ruleset": "2024", "sources": [], "abilities": {"method": "manual", "base": {
            "STR": 14, "DEX": 14, "CON": 12, "INT": 10, "WIS": 12, "CHA": 10}},
             "species": {"id": "human"}, "background": {"id": "acolyte"},
             "classes": [{"classId": cls, "level": 7, "choices": {card: [option]}}]}
        entry = next(r for r in resolve(d, catalog)["derived"]["classResources"] if r["name"] == name)
        assert (entry["uses"], entry["recharge"], entry["dice"]) == (1, "turn", "1d8")
        assert entry["details"]["note"].startswith("once per turn")


# ---------------------------------------------------------------- the scan: nothing with a per-turn text is unclassified

# Features whose text matches PHRASE and that X2 does NOT turn into a "once per turn" resource, with the reason.
LEFT = {
    "sneak-attack": "engine builder, handled (Sneak Attack resource)",
    "xphb-rogue-1-sneak-attack": "engine builder, handled (Sneak Attack resource)",
    "xphb-cleric-7-divine-strike": "engine builder, handled (2024 Divine Strike resource, only with the pick)",
    "xphb-druid-7-primal-strike": "engine builder, handled (2024 Primal Strike resource, only with the pick)",
    "xphb-druid-5-wild-resurgence": "already a resource (1 use, long rest); the per-turn clause is one of two ways to regain Wild Shape",
    "hunters-prey-colossus-slayer": "one option of a Hunter's Prey pick card (pick-dependent; a G1 resource with uses 1 / turn only when picked)",
    "hunters-prey-horde-breaker": "one option of a Hunter's Prey pick card (pick-dependent; a G1 resource with uses 1 / turn only when picked)",
    "hunter-xphb-3-hunters-prey": "pick-dependent (Colossus Slayer / Horde Breaker), notes only",
    "opt-eldritch-smite-xphb": "pact-weapon attack-row note that spends a spell slot (not a standalone resource)",
    "opt-lifedrinker-xphb": "pact-weapon attack-row note (not a standalone resource)",
    "beast-tce-3-form-of-the-beast": "multi-part feature (bite, claws, tail); the per-turn clause is not the main effect",
    "beast-tce-6-bestial-soul": "sub-clause of a pick (swimming / climbing / jumping); the special check is a note",
    "whispers-xge-3-psychic-blades": "a note on Bardic Inspiration (spends a Bardic Inspiration use), the pool is the resource",
    "moon-frhof-3-moons-inspiration": "FRHoF (ruleset 2024, not XPHB): Lunar Vitality clause only, not read",
    "peace-tce-1-emboldening-bond": "already a resource (PB uses, long rest); 'once per turn' is a per-creature clause",
    "spores-tce-10-spreading-spores": "per-creature damage limit inside a bonus-action effect, no own count",
    "moon-xphb-14-lunar-form": "one of several Lunar Form benefits, not the whole feature",
    "arcane-archer-xge-3-arcane-shot": "already a resource (2 uses, short or long rest); the per-turn clause is part of it",
    "psi-warrior-tce-3-psionic-power": "already a resource (psionic energy dice); per-turn clause is part of it",
    "psi-warrior-xphb-3-psionic-strike": "already a resource (psionic energy dice); per-turn clause is part of it",
    "rune-knight-tce-3-giants-might": "already a resource (PB uses, long rest); extra damage per turn is a sub-clause",
    "battle-master-xphb-15-relentless": "a note on Superiority Dice (it spends no resource of its own)",
    "mercy-tce-11-flurry-of-healing-and-harm": "already a resource (WIS uses); the per-turn clause restates Hand of Harm",
    "mercy-xphb-3-hand-of-harm": "a note on Focus Points (SUBCLASS_NOTES_2024), it spends a Focus Point",
    "mercy-xphb-11-flurry-of-healing-and-harm": "already a resource (WIS uses); the per-turn clause restates Hand of Harm",
    "astral-self-tce-11-body-of-the-astral-self": "multi-part feature; Empowered Arms is one of two benefits",
    "elements-xphb-17-elemental-epitome": "multi-part feature; per-turn limits are per-creature / per-benefit clauses",
    "glory-tce-20-living-legend": "already a resource (1 use, long rest); per-turn is the Unerring Strike clause",
    "glory-xphb-20-living-legend": "already a resource (1 use, long rest); per-turn is the Unerring Strike clause",
    "gloom-stalker-xphb-3-dread-ambusher": "already a resource (WIS uses, long rest); per-turn is a clause",
    "winter-walker-frhof-3-frigid-explorer": "FRHoF (ruleset 2024, not XPHB), not read",
    "wild-phb-1-wild-magic-surge": "DM / table-triggered chance of a surge once per turn, not a use the player spends",
    "wild-magic-xphb-3-wild-magic-surge": "table-triggered chance of a surge once per turn, not a use the player spends",
    "spellfire-frhof-3-spellfire-burst": "FRHoF (ruleset 2024, not XPHB), not read",
    "spellfire-frhof-18-crown-of-spellfire": "FRHoF (ruleset 2024, not XPHB), not read",
    "undead-vrgr-1-form-of-dread": "already a resource (PB uses, long rest); per-turn is the immunity clause",
    "undead-vrgr-6-grave-touched": "per-turn clause of an always-on benefit (extra damage die), no own count",
    "undead-vrgr-14-spirit-projection": "per-turn clause inside a transformed state (note only)",
    "fiend-xphb-14-hurl-through-hell": "already a resource (1 use, long rest)",
    "divination-phb-2-portent": "already a resource (Portent dice); per-turn replacement is a clause",
    "diviner-xphb-3-portent": "already a resource (Portent dice); per-turn replacement is a clause",
    "war-xge-6-power-surge": "already a resource (INT-modifier pool, recharge other, G4); the per-turn clause is the spend rule",
}
HANDLED = {u[2] for u in UPGRADES}


def test_scan_every_per_turn_feature_is_handled_or_listed_with_a_reason(catalog):
    found = set()
    for fid, feature in catalog.features.items():
        if PHRASE.search(_plain(feature.get("desc", []))):
            found.add(fid)
    unclassified = found - HANDLED - set(LEFT)
    assert not unclassified, sorted(unclassified)
    stale = set(LEFT) - found
    assert not stale, sorted(stale)
    assert not (set(LEFT) & HANDLED)


# ---------------------------------------------------------------- degradation and timing

def test_timing(catalog):
    _char(catalog, "rogue", 20, None, "2014")
    laps = []
    for _ in range(10):
        t_run = time.perf_counter()
        _char(catalog, "rogue", 20, None, "2014")
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
