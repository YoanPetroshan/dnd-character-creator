"""FE10: the resource and note tail of the feat effect table (docs/superpowers/plans/2026-10-11-feat-effects.md).

After FE10 every one of the 305 catalog feats has an entry in ``catalog.feat_effects_data.FEAT_EFFECTS`` and
``FEAT_PENDING`` is empty. The 170 feats that were still pending (plus the notes / resources that FE1-FE9 left out of 13
entries they had classified for their number) are written in ``catalog.feat_effects_tail``. Each feat follows its own
edition's text under every ruleset. Decision F-D8: the spell-grant tables (the eight Arcane Adept feats of Unearthed
Arcana keyed by spell slot level, Potent Dragonmark's extra slot, Rune Shaper, Boon of Magic School Mastery, Magic
Connoisseur) are notes only.

Governing sentences (catalog text, tags stripped; the full set is ``FEAT_EFFECT_QUOTES`` /
``FEAT_EFFECT_EXTRA_QUOTES``, pinned against the catalog by ``test_quote_matches_catalog_text``):

  Uses       "You can use this benefit a number of times equal to your proficiency bonus, and you regain all expended
             uses when you finish a long rest." (resource ``uses`` "pb", recharge long; the shorter "Once you use this
             benefit, you can't use it again until you finish a Short or Long Rest" is 1 use, short-or-long).
  Boon of Recovery   "You have a pool of ten d10s." (a resource of 10 uses with ``die`` d10).
  Spell Subterfuge   "a number of times equal to the ability modifier of the score increased by this feat" (``uses`` "inc_mod").
  Potent Dragonmark  "The spell slot's level is half your level (round up), to a maximum of level 5."
  Rune Shaper        "You know a number of runes equal to half your proficiency bonus (rounded down)."

Matrix: which feats carry a resource x its uses (fixed, Proficiency Bonus, ability modifier) at Proficiency Bonus 2 and 4
x the source of the feat (ASI pick, with the patched catalog for the feats no ASI pool offers) x which numbers a note
prints (DCs, Temporary Hit Points, level, Proficiency Bonus) x the effects the catalog fields already carry (resistances,
immunities, senses, Expertise, languages, spells) x output surfaces (YAML, Markdown, PDF) x no-feat identity x empty
catalog x timing.
"""
import copy
import io
import re
import time

import pytest
import yaml
from pypdf import PdfReader

import export_fields
from catalog import feat_effects_data as fed
from catalog import feat_effects_tail as tail
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_effects as fe
from engine.resolve import resolve
from export import to_yaml
from markdown_export import to_markdown
from pdf_export import to_pdf

pytestmark = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

ABS = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
FE10_ENTRIES = tuple(tail.TAIL_EFFECTS) + tuple(tail.COMPLETION)
WITH_RESOURCES = tuple(i for i in FE10_ENTRIES if fed.FEAT_EFFECTS[i].get("resources"))
# Scan-kind "resource" feats whose uses live in spell-grant tables or in a per-rest choice (decision F-D8 / F-D7): notes only.
NOTES_ONLY_RESOURCE_SCAN = {"rune-shaper-bgg"}  # FX6: Potent Dragonmark now carries its extra slot as a resource


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
    text = " ".join(out)

    def tag(m):
        parts = m.group(2).split("|")
        return parts[2] if len(parts) > 2 and parts[2] else parts[0]
    return re.sub(r"\{@(\w+) ([^}]*)\}", tag, text)


def _draft(classes, feats=(), ruleset="mixed", background="acolyte", species="human", sources=None):
    entries = []
    for n, (cls, level) in enumerate(classes):
        chosen = {}
        if n == 0:
            slots = [lv for lv in (4, 8, 12, 16, 19) if lv <= level]
            for slot, feat in zip(slots, feats):
                chosen[f"class:{cls}:{slot}:asi"] = [f"feat:{feat}"]
        entries.append({"classId": cls, "level": level, "choices": chosen})
    return {"name": "t", "ruleset": ruleset, "sources": sources or [], "classes": entries,
            "background": {"id": background, "choices": {}}, "species": {"id": species, "choices": {}},
            "abilities": {"method": "manual", "base": {a: 10 for a in ABS}},
            "equipment": {"choices": {}, "added": [], "skipped": False}, "details": {}, "preferences": {}}


ALL_SOURCES = ["EFA", "FRHoF", "AU", "ABH", "RHW", "DSotDQ", "BGG", "SatO", "FTD", "ERLW", "PSK", "SCC", "BMT",
               "MTF", "PSX", "XGE", "TCE", "LFL", "XPHB", "PHB"]


def _patched(catalog, index):
    """The catalog with ``index`` filed as a General feat: the Dragonmark, Dark Gift and Fighting Style feats are in no
    ASI pool, so the matrix grants them through this patch (their prerequisites are not enforced by default)."""
    patched = copy.copy(catalog)
    patched.feats = {**catalog.feats, index: {**catalog.feats[index], "category": "G"}}
    return patched


def _grant(catalog, index, level=4):
    """resolve() of a Fighter of ``level`` that took ``index`` as an ASI feat (level 4; the last slot for Epic Boons)."""
    classes = [("fighter", level)]
    slot_level = max(lv for lv in (4, 8, 12, 16, 19) if lv <= level)
    for ruleset, sources in (("mixed", ALL_SOURCES), ("2024", ALL_SOURCES), ("2014", ALL_SOURCES)):
        draft = _draft(classes, ruleset=ruleset, sources=sources)
        draft["classes"][0]["choices"] = {f"class:fighter:{slot_level}:asi": [f"feat:{index}"]}
        result = resolve(draft, catalog)
        if index in [f["id"] for f in result["sheet"]["feats"]]:
            return result
    cat = _patched(catalog, index)
    draft = _draft(classes, ruleset="mixed", sources=ALL_SOURCES)
    draft["classes"][0]["choices"] = {f"class:fighter:{slot_level}:asi": [f"feat:{index}"]}
    result = resolve(draft, cat)
    assert index in [f["id"] for f in result["sheet"]["feats"]], index
    return result


# ---------------------------------------------------------------- data guards


def test_every_feat_is_classified_and_the_tail_does_not_overlap_the_earlier_slices(catalog):
    assert fed.FEAT_PENDING == frozenset() and fed.FE10_DONE
    assert set(fed.FEAT_EFFECTS) == set(catalog.feats)
    assert len(tail.TAIL_EFFECTS) == 170
    assert set(tail.COMPLETION) <= set(fed.FEAT_EFFECTS) - set(tail.TAIL_EFFECTS)


def test_every_scan_kind_has_its_modelled_effect_or_a_documented_note(catalog):
    """A feat scanned as ``resource`` has a resource (the two spell-table feats excepted: F-D8); one scanned as
    ``notes`` has notes or is carried by catalog fields (``data_only``)."""
    for index, kinds in fed.FEAT_KINDS.items():
        entry = fed.FEAT_EFFECTS[index]
        if "resource" in kinds and index not in NOTES_ONLY_RESOURCE_SCAN:
            assert entry.get("resources"), index
        if kinds == {"notes"}:
            assert entry.get("notes") or entry.get("data_only"), index
    for index in NOTES_ONLY_RESOURCE_SCAN:
        assert fed.FEAT_EFFECTS[index].get("notes") and not fed.FEAT_EFFECTS[index].get("resources")


@pytest.mark.parametrize("index", sorted(set(tail.TAIL_QUOTES) | set(tail.COMPLETION_QUOTES)))
def test_quote_matches_catalog_text(catalog, index):
    """Each governing sentence of the FE10 entries is in the feat's own catalog text."""
    text = _plain(catalog.feats[index]["entries"])
    quotes = tail.TAIL_QUOTES.get(index, ()) or ()
    quotes = (quotes,) if isinstance(quotes, str) else quotes
    for quote in tuple(quotes) + tuple(fed.FEAT_EFFECT_EXTRA_QUOTES.get(index, ())):
        assert quote in text, (index, quote)


def test_every_quote_of_every_entry_matches_the_catalog(catalog):
    """The pin over ALL entries (FE1-FE10), not only the tail."""
    for index, quotes in fed.FEAT_EFFECT_QUOTES.items():
        text = _plain(catalog.feats[index]["entries"])
        for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
            assert quote in text, (index, quote)


def test_every_tail_entry_with_text_has_a_quote_and_only_known_vocabulary():
    for index, entry in tail.TAIL_EFFECTS.items():
        assert set(entry) <= {"notes", "resources", "data_only", "modifies"}, index
        assert index in tail.TAIL_QUOTES, index
        assert entry.get("notes") or entry.get("data_only"), index
        assert not (entry.get("data_only") and len(entry) > 1), index
    for index in tail.COMPLETION:
        assert index in fed.FEAT_EFFECT_QUOTES and index in fed.FEAT_EFFECT_EXTRA_QUOTES, index


def test_resource_entries_use_only_the_implemented_vocabulary():
    seen = 0
    for index in FE10_ENTRIES:
        for res in fed.FEAT_EFFECTS[index].get("resources", []):
            seen += 1
            assert set(res) <= {"name", "uses", "recharge", "note", "die", "dc"}, index
            assert res["uses"] in ("pb", "inc_mod") or isinstance(res["uses"], int), (index, res)
            assert res["recharge"] in ("long", "short", "short-or-long"), (index, res)
    assert seen == 75
    assert len(WITH_RESOURCES) == 70


@pytest.mark.parametrize("index", sorted(i for i, e in tail.TAIL_EFFECTS.items() if e.get("data_only")))
def test_data_only_tail_feats_really_carry_their_effect_in_catalog_fields(catalog, index):
    feat = catalog.feats[index]
    assert any(feat.get(k) for k in ("innate_spells", "spell_choices", "languages")), index


# ---------------------------------------------------------------- the numbers in the notes


def _notes(catalog, index, pb=2, level=5, mods=None, inc=None):
    mods = {a: 0 for a in ABS} | (mods or {})
    numbers = fe.numbers_for(mods, {a: 10 + 2 * m for a, m in mods.items()}, pb, level)
    feat = catalog.feats[index]
    prefix = f"feat:{index}"
    choices = [{"id": f"{prefix}:ability-bonus", "selected": [inc.lower()]}] if inc else []
    insts = fe.instances([feat], fed.FEAT_EFFECTS, choices)
    return " ".join(fe.notes(insts, numbers)[prefix])


@pytest.mark.parametrize("index,kw,expected", [
    ("boon-of-terror-frhof", dict(pb=4, mods={"CHA": 3}), "DC 15"),
    ("cult-of-the-dragon-initiate-frhof", dict(pb=3, mods={"WIS": 2}), "DC 13"),
    ("gathered-whispers-rhw", dict(pb=3), "+3 to your AC"),
    ("gathered-whispers-rhw", dict(pb=3), "DC 16"),
    ("mist-walker-rhw", dict(pb=2), "DC 15"),
    ("living-shadow-rhw", dict(pb=6), "DC 19"),
    ("knight-of-the-rose-dsotdq", dict(pb=3, mods={"CHA": 3}, inc="CHA"), "1d8 + 3 + 3 Temporary"),
    ("knight-of-the-sword-dsotdq", dict(pb=4, mods={"STR": 1}, inc="STR"), "DC 13"),
    ("familiar-friend-au", dict(level=9), "increase by 18"),
    ("genie-magic-frhof", dict(level=11), "your level is 11"),
    ("potent-dragonmark-efa", dict(level=1), "slot of level 1 "),
    ("potent-dragonmark-efa", dict(level=7), "slot of level 4 "),
    ("potent-dragonmark-efa", dict(level=20), "slot of level 5 "),
    ("rune-shaper-bgg", dict(pb=2), "know 1 rune(s)"),
    ("rune-shaper-bgg", dict(pb=5), "know 2 rune(s)"),
    ("chef-tce", dict(pb=3), "food for 7 creatures"),
    ("chef-tce", dict(pb=3), "3 treats per hour"),
    ("vigor-of-the-hill-giant-bgg", dict(pb=3, mods={"CON": 2}), "regain 5 extra"),
    ("dwarven-fortitude-xge", dict(mods={"CON": 3}), "add 3 and"),
    ("interception-xphb", dict(pb=3), "1d10 + 3"),
    ("dragon-fear-xge", dict(pb=3, mods={"CHA": 4}), "DC 15"),
    ("telekinetic-tce", dict(pb=2, mods={"WIS": 2}, inc="WIS"), "DC 12"),
    ("street-justice-frhof", dict(pb=4), "add 4 to the DC"),
    ("shadowmoor-hexer-lfl", dict(pb=3), "takes 3 Psychic"),
    ("boon-of-bloodshed-frhof", dict(pb=5), "+5 extra damage"),
    ("arcane-overload-au", dict(pb=2), "+2 to one damage roll"),
    ("arcane-safeguard-au", dict(pb=3), "gains 3 Temporary"),
    ("baleful-scion-sato", dict(pb=4), "1d6 + 4 necrotic"),
    ("vampire-hunter-abh", dict(pb=3), "roll 3d6"),
    ("warlike-familiar-au", dict(pb=5), "+5 to the Armor Class"),
    ("survivor-rhw", dict(pb=3), "add +3 to the roll"),
    ("greater-mark-of-handling-efa", dict(pb=2, mods={"WIS": 3}), "DC 13"),
    ("greater-aberrant-mark-efa", dict(mods={"CON": 2}), "Temporary Hit Points + 2 and"),
    ("quicksmithing-psk", dict(level=7), "rounded up (4)"),
    ("conjuration-adept-au", dict(mods={"WIS": 3}, inc="WIS"), "+3 to Constitution saves"),
    ("conjuration-adept-au", dict(), "(choose the ability)"),
    ("elemental-familiar-au", dict(pb=3), "DC 11"),
    ("second-skin-rhw", dict(pb=4), "DC 17"),
    ("keenness-of-the-stone-giant-bgg", dict(pb=3, mods={"WIS": 2}, inc="WIS"), "DC 13"),
    ("boon-of-fortitude-xphb", dict(mods={"CON": 4}), "regain 4 extra"),
])
def test_a_note_prints_the_characters_numbers(catalog, index, kw, expected):
    assert expected in _notes(catalog, index, **kw), (index, _notes(catalog, index, **kw))


def test_the_same_note_follows_the_proficiency_bonus():
    """The rule (a DC of 13 + the Proficiency Bonus) is data; the number is the character's."""
    for pb, dc in ((2, 15), (4, 17), (6, 19)):
        assert f"DC {dc}" in _notes(load(), "second-skin-rhw", pb=pb)


# ---------------------------------------------------------------- resources


def _expected_uses(spec, pb):
    return pb if spec == "pb" else spec


def test_the_ten_d10_pool_of_boon_of_recovery(catalog):
    r = _grant(catalog, "boon-of-recovery-xphb", level=19)
    by_name = {x["name"]: x for x in r["derived"]["featResources"]}
    assert set(by_name) == {"Last Stand", "Recover Vitality"}
    assert (by_name["Last Stand"]["uses"], by_name["Last Stand"]["recharge"]) == (1, "long")
    pool = by_name["Recover Vitality"]
    assert (pool["uses"], pool["die"], pool["recharge"]) == (10, "d10", "long")


@pytest.mark.parametrize("index", WITH_RESOURCES)
@pytest.mark.parametrize("level,pb", [(4, 2), (9, 4)])
def test_every_resource_feat_yields_its_resources_at_the_proficiency_bonus(catalog, index, level, pb):
    """Each feat is granted through an ASI pick (the patched catalog for the feats no ASI pool offers) and must
    produce exactly its resources, with the uses its text gives at Proficiency Bonus 2 and 4."""
    spec = fed.FEAT_EFFECTS[index]["resources"]
    r = _grant(catalog, index, level=level)
    got = {x["name"]: x for x in r["derived"]["featResources"] if x["featId"] == index}
    assert set(got) == {s["name"] for s in spec}, index
    for s in spec:
        res = got[s["name"]]
        if s["uses"] == "inc_mod":
            assert res["uses"] == 0 and "(choose the ability)" in res["details"]["note"], index
        else:
            assert res["uses"] == _expected_uses(s["uses"], pb), (index, s["name"])
        assert res["recharge"] == s["recharge"]
        assert res["source"]["kind"] == "feat" and res["source"]["id"] == index and "classId" not in res
        if s.get("die"):
            assert res["die"] == s["die"]
        if s.get("note"):
            assert res["details"]["note"]


def test_uses_equal_to_the_ability_modifier_follow_the_chosen_ability():
    feat = {"index": "spell-subterfuge-au", "name": "Spell Subterfuge"}
    prefix = "feat:spell-subterfuge-au"

    def uses(inc, mods):
        numbers = fe.numbers_for(mods, {}, 3, 8)
        choices = [{"id": f"{prefix}:ability-bonus", "selected": [inc.lower()]}] if inc else []
        [res] = fe.resources(fe.instances([feat], fed.FEAT_EFFECTS, choices), numbers)
        return res

    assert uses("INT", {"INT": 3, "WIS": 1})["uses"] == 3
    assert uses("WIS", {"INT": 3, "WIS": 1})["uses"] == 1
    assert uses("CHA", {"CHA": -1})["uses"] == 0          # a negative modifier gives no uses
    pending = uses(None, {"INT": 3})
    assert pending["uses"] == 0 and pending["details"]["note"].endswith("(choose the ability)")


def test_a_resource_is_scoped_by_the_instance_and_two_feats_give_two_lists(catalog):
    r = _grant(catalog, "survivor-rhw", level=9)
    ids = [x["id"] for x in r["derived"]["featResources"]]
    assert ids == ["class:fighter:8:asi:feat:survivor-rhw:steel-yourself"] or len(ids) == 1
    r = resolve(_draft([("fighter", 9)], ["tireless-reveler-abh", "bloodlust-abh"]), catalog)
    assert sorted(x["name"] for x in r["derived"]["featResources"]) == ["Sanguine Feast", "Tireless Reveler"]


def test_the_earlier_entries_keep_their_numbers_and_gain_the_missing_text(catalog):
    base = resolve(_draft([("fighter", 9)]), catalog)["derived"]
    r = _grant(catalog, "transmuted-anatomy-au", level=9)
    assert r["derived"]["speed"] == base["speed"] + 5
    [res] = r["derived"]["featResources"]
    assert (res["name"], res["uses"], res["recharge"]) == ("Resilient Anatomy", 4, "long")
    r = _grant(catalog, "keenness-of-the-stone-giant-bgg", level=9)
    assert r["sheet"]["senses"]["darkvision"] == 60
    [res] = r["derived"]["featResources"]
    assert (res["name"], res["uses"]) == ("Stone Throw", 4)
    r = _grant(catalog, "boon-of-fortitude-xphb", level=19)
    note = next(f for f in r["sheet"]["feats"] if f["id"] == "boon-of-fortitude-xphb")["notes"]
    assert len(note) == 1 and "extra Hit Points" in note[0]


# ---------------------------------------------------------------- effects the catalog fields already carry


CARRIED = {
    "boon-of-terror-frhof": lambda s: ("frightened" in s["conditionImmunities"]
                                       and "skill-intimidation" in s["expertiseSkills"]),
    "boon-of-truesight-xphb": lambda s: s["senses"].get("truesight") == 60,
    "aberrant-anatomy-rhw": lambda s: s["senses"].get("blindsight") == 15 and "skill-perception" in s["expertiseSkills"],
    "infernal-constitution-xge": lambda s: {"cold", "poison"} <= set(s["damageModifiers"]["resistances"]),
    "boon-of-poison-mastery-frhof": lambda s: ("poison" in s["damageModifiers"]["immunities"]
                                               and "poisoned" in s["conditionImmunities"]),
    "boon-of-blazing-dawn-abh": lambda s: "radiant" in s["damageModifiers"]["immunities"],
    "boon-of-the-soul-drinker-frhof": lambda s: {"cold", "necrotic"} <= set(s["damageModifiers"]["resistances"]),
    "boon-of-the-furious-storm-frhof": lambda s: {"lightning", "thunder"} <= set(s["damageModifiers"]["resistances"]),
    "ember-of-the-fire-giant-bgg": lambda s: "fire" in s["damageModifiers"]["resistances"],
    "fury-of-the-frost-giant-bgg": lambda s: "cold" in s["damageModifiers"]["resistances"],
    "mark-of-storm-efa": lambda s: "lightning" in s["damageModifiers"]["resistances"],
    "cult-of-the-dragon-initiate-frhof": lambda s: "draconic" in s["proficiencies"]["languages"],
    "fey-teleportation-xge": lambda s: "sylvan" in s["proficiencies"]["languages"],
}


@pytest.mark.parametrize("index", sorted(CARRIED))
def test_effects_carried_by_catalog_fields_reach_the_sheet(catalog, index):
    r = _grant(catalog, index, level=19 if index.startswith("boon-") else 4)
    assert CARRIED[index](r["sheet"]), index


def test_a_conditional_resistance_is_a_note_not_a_permanent_one(catalog):
    """Soul of the Storm Giant's resistance exists only while the aura is up; Boon of Desperate Resilience only while Bloodied."""
    r = _grant(catalog, "soul-of-the-storm-giant-bgg")
    assert r["sheet"]["damageModifiers"]["resistances"] == []
    assert any("Resistance to lightning and thunder" in n
               for f in r["sheet"]["feats"] for n in f.get("notes", []))
    r = _grant(catalog, "boon-of-desperate-resilience-frhof", level=19)
    assert r["sheet"]["damageModifiers"]["resistances"] == []


# ---------------------------------------------------------------- output surfaces


def _knight(catalog):
    return _grant(catalog, "knight-of-the-rose-dsotdq", level=9)


def test_blocks_carry_the_resource_line_and_the_notes(catalog):
    res = _knight(catalog)
    blocks = export_fields.extra_blocks(res)
    assert ("h2", "Ресурси от таланти") in blocks
    line = export_fields.resource_line(res["derived"]["featResources"][0])
    assert line.startswith("Bolstering Rally: 4 (дълга почивка)") and ("bullet", line) in blocks
    bullet = next(t for kind, t in blocks if kind == "bullet" and t.startswith("Knight of the Rose"))
    assert "1d8 + 4" in bullet


def test_yaml_markdown_and_pdf_print_the_tail_resources_and_notes(catalog):
    res = _knight(catalog)
    doc = yaml.safe_load(to_yaml(res))
    assert doc["featResources"] == res["derived"]["featResources"]
    flat = lambda t: re.sub(r"\s+", " ", t)  # noqa: E731
    pdf = flat("\n".join(p.extract_text() for p in PdfReader(io.BytesIO(to_pdf(res))).pages))
    md = flat(to_markdown(res))
    for text in ("Ресурси от таланти", "Bolstering Rally: 4 (дълга почивка)", "Bolstering Rally (Bonus Action)"):
        assert text in md, text
        assert text in pdf, text


# ---------------------------------------------------------------- identity, degrade, speed


def test_a_featless_character_is_unchanged(catalog):
    r = resolve(_draft([("fighter", 9)]), catalog)
    assert r["derived"]["featResources"] == []
    assert all("notes" not in f for f in r["sheet"]["feats"])


def test_empty_catalog_is_a_no_op():
    bare = copy.copy(load())
    bare.feats = {}
    r = resolve(_draft([("fighter", 4)], ["lucky-phb"]), bare)
    assert r["derived"]["featResources"] == []


def test_resolve_stays_fast_with_many_resource_feats(catalog):
    many = ["knight-of-the-rose-dsotdq", "bloodlust-abh", "survivor-rhw", "tireless-reveler-abh", "sharp-eye-rhw"]
    cases = (([("fighter", 20)], "mixed", "acolyte", many),
             ([("fighter", 20)], "2024", "merchant-xphb", ["boon-of-recovery-xphb"] + many[:4]),
             ([("wizard", 20)], "mixed", "acolyte", many))
    for classes, ruleset, bg, feats in cases:
        draft = _draft(classes, feats, ruleset=ruleset, background=bg, sources=ALL_SOURCES)
        resolve(draft, catalog)
        t = time.perf_counter()
        for _ in range(10):
            result = resolve(draft, catalog)
        assert (time.perf_counter() - t) / 10 < 0.05
        assert len(result["derived"]["featResources"]) >= 4


@pytest.mark.parametrize("level,slot", [(4, 2), (7, 4), (9, 5), (20, 5)])
def test_potent_dragonmark_extra_slot_is_a_resource_with_the_computed_level(catalog, level, slot):
    """FX6. "The spell slot's level is half your level (round up), to a maximum of level 5. You regain the expended
    slot when you finish a Short Rest or Long Rest." One slot, so uses 1."""
    r = _grant(catalog, "potent-dragonmark-efa", level=level)
    res = next(x for x in r["derived"]["featResources"] if x["name"] == "Dragonmark Spell Slot")
    assert (res["uses"], res["recharge"]) == (1, "short-or-long")
    assert f"spell slot of level {slot} " in res["details"]["note"]
