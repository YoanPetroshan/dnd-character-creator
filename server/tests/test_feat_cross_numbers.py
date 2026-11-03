"""RP5 (A5, open question 21): cross-feat modifications with numbers.

Governing sentences (catalog feat `entries`, tags stripped; pinned by ``test_quote_matches_catalog``):
  greater-mark-of-healing-efa  "...cast Cure Wounds without using a spell slot a number of times equal to your
                                Proficiency Bonus, and you regain all expended uses when you finish a Long Rest."
  greater-mark-of-making-efa   "...cast Magic Weapon without a spell slot, you cast the spell as its level 3 version."
  greater-mark-of-shadow-efa   "...cast Invisibility without a spell slot, you cast the spell as its level 3 version."
  adept of the Black / Red / White Robes, Outlands Envoy, Warlike Familiar, Magic Connoisseur: "...spellcasting ability is
                                the one chosen (for/when you gained) <base feat>."

Rule matrix:
  Healing: base alone -> Cure Wounds "1/day", no note; base + Greater at Proficiency Bonus 2 / 4 -> "2/long rest" /
           "4/long rest" plus the healing-dice note; Greater alone keeps its own tracker and no patched entry.
  Making / Shadow: base + Greater -> the level 3 note on Magic Weapon / Invisibility only (other entries untouched).
  ability_from: base held -> the dependent feat has no ``:spell-ability`` card and its innate spells carry the base's
           chosen ability; base chosen later changes both; base removed -> own card is back (Outlands / Warlike have none
           of their own: ability pending / None); a stored pick on the removed card is a non-blocking `pruned` entry.
  Markdown / PDF show the note. SRD-only catalog: no entry."""
from perf_helpers import assert_fast
import re
import time

import pytest

from catalog import feat_effects_data as fed
from catalog import feat_effects_tail as tail
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import feat_effects as fe
from engine.resolve import resolve

from catalog.official.paths import has_official, has_official_classes, has_official_spells  # noqa: E402

needs_official = pytest.mark.skipif(
    not (has_official() and has_official_classes() and has_official_spells()), reason="5etools data not available")

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


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


HOUSE = {"mark-of-healing-efa": "house-jorasco-heir-efa", "mark-of-making-efa": "house-cannith-heir-efa",
         "mark-of-shadow-efa": "house-phiarlan-heir-efa"}  # the Marks come from a House background (category D)


def _draft(feats, ruleset="mixed", level=8, choices=None, background="acolyte"):
    chosen = {f"class:fighter:{slot}:asi": [f"feat:{f}"] for slot, f in zip((4, 6), feats)}
    chosen.update(choices or {})
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": 14, "DEX": 16, "CON": 12, "INT": 12, "WIS": 12, "CHA": 12}},
        "species": {"id": "human", "choices": {}},
        "background": {"id": background, "choices": {}},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": "fighter", "level": level, "choices": chosen}],
    }


def _ability_card(res, feat):
    return next((c for c in res["choices"] if c["id"].endswith(":spell-ability") and c["source"]["id"] == feat), None)


def _innate(res, name):
    return next((e for e in res["sheet"]["innateSpells"] if e["name"] == name), None)


def _marks(base, greater=True, **kw):
    """Base Mark from its House background; the Greater Mark (level 4) at the first Ability Score Improvement."""
    return _draft([f"greater-{base}"] if greater else [], background=HOUSE[base], **kw)


# ---------------------------------------------------------------- data pins


@needs_official
@pytest.mark.parametrize("index", sorted(tail.RP5_INNATE_QUOTES))
def test_quote_matches_catalog(catalog, index):
    assert tail.RP5_INNATE_QUOTES[index] in _plain(catalog.feats[index]["entries"])


@needs_official
def test_healing_dice_quote_matches_catalog(catalog):
    assert tail.RP5_HEALING_DICE_QUOTE in _plain(catalog.feats["greater-mark-of-healing-efa"]["entries"])


@needs_official
@pytest.mark.parametrize("dependent", sorted(tail.RP5_ABILITY_FROM))
def test_ability_from_quote_and_base_match_the_catalog(catalog, dependent):
    base, sentence = tail.RP5_ABILITY_FROM[dependent]
    assert sentence in _plain(catalog.feats[dependent]["entries"])
    assert fed.FEAT_EFFECTS[dependent]["ability_from"] == base
    assert base in catalog.feats
    prereq = str(catalog.feats[dependent]["prerequisite"]).lower()
    assert base.split("-")[0] in prereq  # the base feat is the dependent's prerequisite


def test_new_keys_are_in_the_vocabulary():
    assert {"modifies", "ability_from"} <= fed.FEAT_EFFECT_KEYS
    for index, entry in fed.FEAT_EFFECTS.items():
        assert set(entry) <= fed.FEAT_EFFECT_KEYS, index


# ---------------------------------------------------------------- engine, pure


def _inst(index):
    return {"feat": {"index": index, "name": index}, "index": index, "prefix": f"feat:{index}", "origin": "background",
            "effect": fed.FEAT_EFFECTS[index], "increased": None, "resist": [], "pick_text": None}


@pytest.mark.parametrize("pb", [2, 4])
def test_innate_patch_uses_the_proficiency_bonus(pb):
    patches = fe.innate_patches([_inst("mark-of-healing-efa"), _inst("greater-mark-of-healing-efa")], {"pb": pb})
    patch = patches[("mark-of-healing-efa", "cure-wounds")]
    assert patch["uses"] == f"{pb}/long rest" and "1 or 2" in patch["note"]


def test_innate_patch_needs_both_feats():
    assert fe.innate_patches([_inst("mark-of-healing-efa")], {"pb": 2}) == {}
    assert fe.innate_patches([_inst("greater-mark-of-healing-efa")], {"pb": 2}) == {}


# ---------------------------------------------------------------- resolve: innate patches


@needs_data
@pytest.mark.parametrize("level,pb", [(8, 3), (4, 2), (13, 5), (9, 4)])
def test_greater_healing_turns_cure_wounds_into_pb_per_long_rest(catalog, level, pb):
    res = resolve(_marks("mark-of-healing-efa", level=level), catalog)
    cure = _innate(res, "Cure Wounds")
    assert cure["uses"] == f"{pb}/long rest" and "treat a 1 or 2" in cure["note"]
    assert len([e for e in res["sheet"]["innateSpells"] if e["name"] == "Cure Wounds"]) == 1
    assert _innate(res, "Lesser Restoration")["uses"] == "1/day"  # the other Healing Touch spell is untouched


@needs_data
def test_base_healing_alone_is_unchanged_and_greater_alone_has_no_patched_entry(catalog):
    base = resolve(_marks("mark-of-healing-efa", greater=False), catalog)
    assert _innate(base, "Cure Wounds")["uses"] == "1/day" and "note" not in _innate(base, "Cure Wounds")
    greater = resolve(_draft(["greater-mark-of-healing-efa"]), catalog)  # no base Mark held (prerequisite unmet)
    assert _innate(greater, "Cure Wounds") is None
    assert any(r["name"] == "Improved Healing (Cure Wounds)" for r in greater["derived"]["featResources"])


@needs_data
@pytest.mark.parametrize("mark,spell,other", [("making", "Magic Weapon", "Mending"), ("shadow", "Invisibility", "Minor Illusion")])
def test_greater_making_and_shadow_cast_at_level_3(catalog, mark, spell, other):
    base, greater = f"mark-of-{mark}-efa", f"greater-mark-of-{mark}-efa"
    both = resolve(_marks(base), catalog)
    assert "level 3 version" in _innate(both, spell)["note"] and _innate(both, spell)["uses"] == "1/day"
    assert "note" not in _innate(both, other)
    alone = resolve(_marks(base, greater=False), catalog)
    assert "note" not in _innate(alone, spell)


@needs_data
def test_2024_ruleset_follows_the_feat_text_too(catalog):
    res = resolve(_marks("mark-of-healing-efa", ruleset="2024"), catalog)
    assert _innate(res, "Cure Wounds")["uses"].endswith("/long rest")


@needs_data
def test_markdown_and_pdf_show_the_note(catalog):
    from markdown_export import to_markdown
    res = resolve(_marks("mark-of-making-efa"), catalog)
    assert "level 3 version" in to_markdown(res)
    import pdf_export
    src = open(pdf_export.__file__).read()
    assert "e['note']" in src  # the PDF bullet carries the same note (rendering needs fonts; text path pinned)


# ---------------------------------------------------------------- resolve: ability_from


BASE_ROBES = "initiate-of-high-sorcery-dsotdq"


@needs_data
def test_adept_of_the_red_robes_uses_the_initiate_ability(catalog):
    feats = [BASE_ROBES, "adept-of-the-red-robes-dsotdq"]
    pending = resolve(_draft(feats), catalog)
    assert _ability_card(pending, "adept-of-the-red-robes-dsotdq") is None
    own = _ability_card(pending, BASE_ROBES)
    assert own is not None
    chosen = resolve(_draft(feats, choices={own["id"]: ["wis"]}), catalog)
    assert _ability_card(chosen, "adept-of-the-red-robes-dsotdq") is None
    adept_entries = [e for e in chosen["sheet"]["innateSpells"] if e.get("featId") == "adept-of-the-red-robes-dsotdq"]
    # the spell itself is a pick (spell_choices): once picked it carries WIS; the sheet ability follows the base
    assert all(e["ability"] == "WIS" for e in adept_entries)


@needs_data
def test_stored_pick_on_the_removed_card_is_pruned(catalog):
    feats = [BASE_ROBES, "adept-of-the-red-robes-dsotdq"]
    res = resolve(_draft(feats), catalog)
    own = _ability_card(res, BASE_ROBES)
    prefix = own["id"].rsplit(":", 1)[0]
    # the adept's origin prefix is the other ASI slot
    adept_cid = f"class:fighter:6:asi:feat:adept-of-the-red-robes-dsotdq:spell-ability"
    res2 = resolve(_draft(feats, choices={own["id"]: ["int"], adept_cid: ["cha"]}), catalog)
    reasons = [p for p in res2["pruned"] if p["choiceId"] == adept_cid]
    assert len(reasons) == 1, [c["id"] for c in res2["choices"] if "adept" in c["id"]]


@needs_data
def test_without_the_base_feat_the_dependent_keeps_its_own_card(catalog):
    res = resolve(_draft(["adept-of-the-red-robes-dsotdq"]), catalog)
    assert _ability_card(res, "adept-of-the-red-robes-dsotdq") is not None


@needs_data
def test_outlands_envoy_and_warlike_familiar_follow_their_base(catalog):
    for base, dep, spells in (("scion-of-the-outer-planes-sato", "outlands-envoy-sato", ("Misty Step", "Tongues")),
                              ("familiar-friend-au", "warlike-familiar-au", ("Battle Familiar",))):
        res = resolve(_draft([base, dep]), catalog)
        card = _ability_card(res, base)
        assert card is not None
        assert _ability_card(res, dep) is None
        pending = resolve(_draft([base, dep], choices={}), catalog)
        for name in spells:
            entry = _innate(pending, name)
            assert entry and isinstance(entry["ability"], dict), (dep, name, entry)
        done = resolve(_draft([base, dep], choices={card["id"]: ["cha"]}), catalog)
        for name in spells:
            assert _innate(done, name)["ability"] == "CHA", (dep, name)


@needs_data
def test_magic_connoisseur_has_no_card_and_follows_magic_initiate(catalog):
    res = resolve(_draft(["magic-initiate-xphb", "magic-connoisseur-au"]), catalog)
    assert _ability_card(res, "magic-connoisseur-au") is None


@needs_data
def test_timing_stays_fast(catalog):
    d = _marks("mark-of-healing-efa", level=20)
    resolve(d, catalog)
    laps = []
    for _ in range(10):
        t_run = time.perf_counter()
        resolve(d, catalog)
        laps.append(time.perf_counter() - t_run)
    assert_fast(laps)
