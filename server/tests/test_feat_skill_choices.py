"""FE6: feat skill and Expertise rules (Keen Mind / Observant XPHB, the "lacks Expertise" feats, Echoing Soul,
Harper Agent). Each feat follows its own edition's text under every ruleset (keyed by feat index).

Governing sentences (read from catalog.feats[...]["entries"], pinned by test_quote_matches_catalog_text):
  Keen Mind XPHB   "If you lack proficiency in the chosen skill, you gain proficiency in it, and if you already
                    have proficiency in it, you gain Expertise in it."   (F-D4: "already" is position-aware)
  Observant XPHB   the same sentence for Insight / Investigation / Perception.
  Skill Expert TCE / Prodigy XGE
                   "The skill you choose must be one that isn't already benefiting from a feature, such as
                    Expertise, that doubles your proficiency bonus."
  Skill Expert XPHB  "Choose one skill in which you have proficiency but lack Expertise."
  Boon of Skill XPHB "Choose one skill in which you lack Expertise."
  Echoing Soul     "You have proficiency in two skills of your choice."  (5etools data says one: B3)
  Harper Agent     "You know Thieves' Cant."                              (5etools language key dropped: B4)

Rule matrix (rule x ruleset x position):
  * proficiency-or-Expertise: skill already proficient at the feat's position -> Expertise (and still listed once
    as a proficiency); not proficient -> proficiency only. "At the feat's position": origin sources first, then
    class cards by (class order, class level), an ASI feat after the class feature of its level; a LATER grant
    of the same skill never converts it (the later card is the duplicate).
  * under 2024 (decision E1 revised) a converted pick is also gated by "already has Expertise" (option disabled,
    stored pick dropped with a `pruned` entry); mixed / 2014 do not gate it (the feat text has no such clause).
  * "lacks Expertise" feats (Skill Expert TCE / XPHB, Prodigy, Boon of Skill): the gate applies under EVERY ruleset.
    Control: the SRD Rogue / Bard Expertise cards stay unflagged under mixed / 2014.
  * Echoing Soul: two skill proficiency picks. Harper Agent: Thieves' Cant is known (fixed language) and the C6b-2
    language gate sees it.
"""
import copy
import re

import pytest

from catalog import feat_effects_data as fed
from catalog.loader import load
from catalog.official_source import has_official, has_official_classes
from engine import resolve as resolve_mod
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")

SIX = {"STR": 10, "DEX": 14, "CON": 12, "INT": 16, "WIS": 14, "CHA": 10}
FE6_PROF_OR_EXPERTISE = ("keen-mind-xphb", "observant-xphb")
FE6_LACKS = ("skill-expert-tce", "prodigy-xge", "skill-expert-xphb", "boon-of-skill-xphb")
FE6_DATA = ("echoing-soul-rhw", "harper-agent-frhof")


@pytest.fixture(scope="module")
def catalog():
    return load()


def _draft(classes, ruleset="2024", background="sage-xphb", species="human", sources=None, species_choices=None):
    return {
        "ruleset": ruleset, "sources": sources or [],
        "abilities": {"method": "manual", "base": dict(SIX)},
        "species": {"id": species, **({"choices": species_choices} if species_choices else {})},
        "background": {"id": background},
        "equipment": {"choices": {}, "added": [], "skipped": False},
        "classes": [{"classId": c, "level": lv, "choices": ch} for c, lv, ch in classes],
    }


def _asi(cls, lvl, feat, **picks):
    base = f"class:{cls}:{lvl}:asi"
    out = {base: [f"feat:{feat}"]}
    for k, v in picks.items():
        out[f"{base}:feat:{feat}:{k.replace('_', '-')}"] = v if isinstance(v, list) else [v]
    return out


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _text(feat):
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
    walk(feat["entries"])
    text = " ".join(out)
    return re.sub(r"\{@(\w+) ([^}]*)\}",
                  lambda m: (m.group(2).split("|")[2] if len(m.group(2).split("|")) > 2 and m.group(2).split("|")[2]
                             else m.group(2).split("|")[0]), text)


def _pruned_for(res, cid):
    return [p for p in res["pruned"] if p["choiceId"] == cid]


# ---------------------------------------------------------------- data


@pytest.mark.parametrize("index", FE6_PROF_OR_EXPERTISE + FE6_LACKS + FE6_DATA)
@needs_data
def test_quote_matches_catalog_text(catalog, index):
    quotes = fed.FEAT_EFFECT_QUOTES[index]
    for quote in (quotes if isinstance(quotes, tuple) else (quotes,)):
        assert quote in _text(catalog.feats[index]), (index, quote)


def test_flags_are_set_on_exactly_the_documented_feats():
    assert {i for i, e in fed.FEAT_EFFECTS.items() if e.get("prof_or_expertise")} == set(FE6_PROF_OR_EXPERTISE)
    assert {i for i, e in fed.FEAT_EFFECTS.items() if e.get("lacks_expertise")} == set(FE6_LACKS)
    for index in FE6_DATA:
        assert fed.FEAT_EFFECTS[index] == {"data_only": True}
    for index in FE6_PROF_OR_EXPERTISE + FE6_LACKS + FE6_DATA:
        assert index not in fed.FEAT_PENDING


@needs_data
def test_echoing_soul_has_two_skill_picks_and_one_expertise_pick(catalog):
    """B3. "You have proficiency in two skills of your choice." """
    feat = catalog.feats["echoing-soul-rhw"]
    assert [env["choose"] for env in feat["proficiency_choices"]] == [2]
    assert [env["choose"] for env in feat["expertise_choices"]] == [1]
    assert feat["language_options"]["choose"] == 1  # "You know one additional language" is untouched


@needs_data
def test_echoing_soul_card_asks_for_two_skills(catalog):
    feat = catalog.feats["echoing-soul-rhw"]
    cards = resolve_mod._feat_choice_templates([feat])
    skill = next(c for c in cards if c["id"] == "feat:echoing-soul-rhw:proficiency-choice-0")
    assert skill["count"] == 2


@needs_data
def test_harper_agent_knows_thieves_cant_in_the_catalog(catalog):
    """B4. "You know Thieves' Cant." (5etools key: ``{"thieves' cant": true}``)."""
    assert [lang["index"] for lang in catalog.feats["harper-agent-frhof"]["languages"]] == ["thieves-cant"]
    assert catalog.feats["harper-agent-frhof"]["language_options"] is None


# ---------------------------------------------------------------- Harper Agent in resolve()


@needs_data
def test_harper_agent_background_lists_thieves_cant(catalog):
    res = resolve(_draft([("fighter", 1, {})], background="harper-frhof", sources=["FRHoF"]), catalog)
    assert "thieves-cant" in res["sheet"]["proficiencies"]["languages"]
    assert res["sheet"]["proficiencies"]["languages"].count("thieves-cant") == 1


@needs_data
def test_language_gate_sees_harper_agents_thieves_cant(catalog):
    """C6b-2 gate: Deft Explorer's language card offers Thieves' Cant, but the Harper Agent already knows it."""
    cid = "class:ranger:2:languages:xphb-ranger-2-deft-explorer"
    plain = resolve(_draft([("ranger", 2, {})], sources=["FRHoF"]), catalog)
    assert "disabled" not in _opt(_card(plain, cid), "thieves-cant") or not _opt(_card(plain, cid), "thieves-cant").get("disabled")
    harper = resolve(_draft([("ranger", 2, {})], background="harper-frhof", sources=["FRHoF"]), catalog)
    opt = _opt(_card(harper, cid), "thieves-cant")
    assert opt.get("disabled") and opt["disabledReason"] == "already known"
    stored = resolve(_draft([("ranger", 2, {cid: ["thieves-cant", "elvish"]})], background="harper-frhof",
                            sources=["FRHoF"]), catalog)
    assert _card(stored, cid)["selected"] == ["elvish"]
    assert _pruned_for(stored, cid)


# ---------------------------------------------------------------- Keen Mind / Observant: proficiency or Expertise

KM = "keen-mind-xphb"
KM_CARD = "class:wizard:4:asi:feat:keen-mind-xphb:proficiency-choice-0"


@needs_data
def test_keen_mind_on_a_proficient_skill_is_expertise(catalog):
    """Sage (XPHB) grants Arcana and History: History is already proficient -> Expertise."""
    res = resolve(_draft([("wizard", 4, _asi("wizard", 4, KM, proficiency_choice_0="skill-history"))]), catalog)
    assert res["sheet"]["expertiseSkills"] == ["skill-history"]
    assert res["sheet"]["proficiencies"]["skills"].count("skill-history") == 1
    plain = resolve(_draft([("wizard", 4, {})]), catalog)
    # History at Expertise: +PB on top of the proficiency (PB 2 at level 4)
    assert res["derived"]["skills"]["skill-history"] - plain["derived"]["skills"]["skill-history"] == 2


@needs_data
def test_keen_mind_on_a_new_skill_is_plain_proficiency(catalog):
    res = resolve(_draft([("wizard", 4, _asi("wizard", 4, KM, proficiency_choice_0="skill-nature"))]), catalog)
    assert res["sheet"]["expertiseSkills"] == []
    assert "skill-nature" in res["sheet"]["proficiencies"]["skills"]


@needs_data
def test_keen_mind_converts_under_every_ruleset(catalog):
    """The feat's own text, not the draft's ruleset (decision: effects follow the feat's edition)."""
    for ruleset in ("mixed", "2014", "2024"):
        res = resolve(_draft([("wizard", 4, _asi("wizard", 4, KM, proficiency_choice_0="skill-history"))],
                             ruleset=ruleset, background="sage-xphb"), catalog)
        assert res["sheet"]["expertiseSkills"] == ["skill-history"], ruleset


@needs_data
def test_a_class_grant_before_the_feat_converts_it(catalog):
    """Fighter 4 picks Perception as a class skill (level 1), Observant XPHB at ASI 4 takes Perception again."""
    picks = {"class:fighter:1:prof-choice-0": ["skill-perception", "skill-athletics"],
             **_asi("fighter", 4, "observant-xphb", proficiency_choice_0="skill-perception", ability_bonus="wis")}
    res = resolve(_draft([("fighter", 4, picks)], background="soldier-xphb"), catalog)
    assert "skill-perception" in res["sheet"]["expertiseSkills"], [c["id"] for c in res["choices"] if "fighter" in c["id"]][:6]


@needs_data
def test_observant_with_a_species_perception_is_expertise(catalog):
    """SRD Elf (Keen Senses) is proficient in Perception from the species: Observant -> Expertise."""
    picks = _asi("fighter", 4, "observant-xphb", proficiency_choice_0="skill-perception", ability_bonus="wis")
    res = resolve(_draft([("fighter", 4, picks)], ruleset="mixed", species="elf", background="acolyte"), catalog)
    assert res["sheet"]["expertiseSkills"] == ["skill-perception"]
    assert res["sheet"]["proficiencies"]["skills"].count("skill-perception") == 1


@needs_data
def test_primal_knowledge_before_the_feat_converts_it_and_after_it_does_not(catalog):
    """Position-aware (F-D4, like F3a and Primal Knowledge). Barbarian 3 Primal Knowledge (Nature) comes
    before a Fighter 4 ASI feat in class order [barbarian, fighter] and after it in [fighter, barbarian]."""
    pk = "class:barbarian:3:feature:xphb-barbarian-3-primal-knowledge"
    barb = ("barbarian", 3, {pk: ["skill-nature"]})
    fight = ("fighter", 4, _asi("fighter", 4, KM, proficiency_choice_0="skill-nature"))
    km_card = "class:fighter:4:asi:feat:keen-mind-xphb:proficiency-choice-0"
    first = resolve(_draft([barb, fight]), catalog)
    assert first["sheet"]["expertiseSkills"] == ["skill-nature"]
    assert _card(first, km_card)["selected"] == ["skill-nature"]
    assert _card(first, pk)["selected"] == ["skill-nature"]
    later = resolve(_draft([fight, barb]), catalog)
    assert later["sheet"]["expertiseSkills"] == []  # the later grant never converts the earlier pick
    assert _card(later, km_card)["selected"] == ["skill-nature"]
    assert _card(later, pk)["selected"] == []  # the later Primal Knowledge card is the duplicate (F3a-4)
    assert _opt(_card(later, pk), "skill-nature")["disabledReason"] == "already proficient"


@needs_data
def test_a_second_card_sees_the_first_card(catalog):
    """Observant (ASI 4) takes Investigation; Keen Mind (ASI 6) takes it again -> Expertise at the later card."""
    picks = {**_asi("fighter", 4, "observant-xphb", proficiency_choice_0="skill-investigation", ability_bonus="int"),
             **_asi("fighter", 6, KM, proficiency_choice_0="skill-investigation")}
    res = resolve(_draft([("fighter", 6, picks)], background="soldier-xphb"), catalog)
    assert res["sheet"]["expertiseSkills"] == ["skill-investigation"]
    assert res["sheet"]["proficiencies"]["skills"].count("skill-investigation") == 1
    earlier = {k: v for k, v in picks.items() if "keen-mind" not in k and ":6:" not in k}
    assert resolve(_draft([("fighter", 4, earlier)], background="soldier-xphb"), catalog)["sheet"]["expertiseSkills"] == []


@needs_data
def test_a_feat_proficiency_grant_later_in_the_build_does_not_convert(catalog):
    """Keen Mind at ASI 4 picks Arcana (not proficient). A Skill Expert (XPHB) at ASI 6 then grants Arcana as a
    proficiency: that later grant is the duplicate, Keen Mind stays plain proficiency."""
    picks = {**_asi("fighter", 4, KM, proficiency_choice_0="skill-arcana"),
             **_asi("fighter", 6, "skill-expert-xphb", proficiency_choice_0="skill-arcana", ability_bonus="str")}
    res = resolve(_draft([("fighter", 6, picks)], background="soldier-xphb"), catalog)
    assert res["sheet"]["expertiseSkills"] == []


@needs_data
def test_under_2024_a_converted_pick_is_gated_by_existing_expertise(catalog):
    """Rogue 1 Expertise in History (decision E1 revised): under 2024 Keen Mind cannot double it."""
    rogue1 = "class:rogue:1:expertise-choice:xphb-rogue-1-expertise"
    picks = {rogue1: ["skill-history", "skill-stealth"],
             "class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"],
             **_asi("rogue", 4, KM, proficiency_choice_0="skill-history")}
    res = resolve(_draft([("rogue", 4, picks)]), catalog)
    card = _card(res, "class:rogue:4:asi:feat:keen-mind-xphb:proficiency-choice-0")
    assert _opt(card, "skill-history")["disabledReason"] == "already has Expertise"
    assert card["selected"] == []
    assert _pruned_for(res, card["id"])
    assert res["sheet"]["expertiseSkills"].count("skill-history") == 1
    # the options that are not expert stay open
    assert not _opt(card, "skill-arcana").get("disabled")


@needs_data
def test_outside_2024_a_converted_pick_is_not_gated(catalog):
    """Mixed: the feat's text has no "lack Expertise" clause, so a duplicate is accepted (and listed once)."""
    picks = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"],
             "class:rogue:1:expertise-choice:rogue-expertise-1": ["skill-stealth", "skill-acrobatics"],
             "class:rogue:1:expertise-choice-0": [],
             **_asi("rogue", 4, "observant-xphb", proficiency_choice_0="skill-perception", ability_bonus="wis")}
    res = resolve(_draft([("rogue", 4, picks)], ruleset="mixed", background="acolyte"), catalog)
    assert "skill-perception" in res["sheet"]["proficiencies"]["skills"]
    # Perception is already proficient (class card): converted to Expertise
    assert "skill-perception" in res["sheet"]["expertiseSkills"]


@needs_data
def test_converted_expertise_blocks_a_later_skill_expert_pick_under_2024(catalog):
    """The conversion takes part in the Expertise walk: Keen Mind (ASI 4) History -> Expertise, then
    Skill Expert XPHB (ASI 6) may not pick History."""
    picks = {**_asi("wizard", 4, KM, proficiency_choice_0="skill-history"),
             **_asi("wizard", 8, "skill-expert-xphb", proficiency_choice_0="skill-arcana", ability_bonus="int",
                    expertise_choice_0="skill-history")}
    res = resolve(_draft([("wizard", 8, picks)]), catalog)
    card = _card(res, "class:wizard:8:asi:feat:skill-expert-xphb:expertise-choice-0")
    assert _opt(card, "skill-history")["disabledReason"] == "already has Expertise"
    assert card["selected"] == []


@needs_data
def test_internal_template_flags_are_stripped(catalog):
    res = resolve(_draft([("wizard", 4, _asi("wizard", 4, KM, proficiency_choice_0="skill-history"))]), catalog)
    for c in res["choices"]:
        assert "profOrExpertise" not in c and "lacksExpertise" not in c


@needs_data
def test_keen_mind_phb_is_untouched(catalog):
    """PHB Keen Mind has no skill clause (it is a note feat)."""
    res = resolve(_draft([("wizard", 4, _asi("wizard", 4, "keen-mind-phb"))], ruleset="mixed", background="acolyte"), catalog)
    assert res["sheet"]["expertiseSkills"] == []


# ---------------------------------------------------------------- "lacks Expertise" feats under every ruleset


def _rogue_with(feat, ruleset, expertise_pick, **feat_picks):
    picks = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"],
             "class:rogue:1:expertise-choice:rogue-expertise-1": ["skill-stealth", "skill-acrobatics"],
             "class:rogue:1:expertise-choice:xphb-rogue-1-expertise": ["skill-stealth", "skill-acrobatics"],
             **_asi("rogue", 4, feat, expertise_choice_0=expertise_pick, **feat_picks)}
    return resolve(_draft([("rogue", 4, picks)], ruleset=ruleset, background="acolyte"), load())


@pytest.mark.parametrize("ruleset", ["mixed", "2014"])
@needs_data
def test_skill_expert_tce_and_prodigy_refuse_an_expert_skill_outside_2024(catalog, ruleset):
    """"The skill you choose must be one that isn't already benefiting from a feature, such as Expertise,
    that doubles your proficiency bonus." """
    for feat, extra in (("skill-expert-tce", {}), ("prodigy-xge", {})):
        res = _rogue_with(feat, ruleset, "skill-stealth", **extra)
        card = _card(res, f"class:rogue:4:asi:feat:{feat}:expertise-choice-0")
        if card is None:  # the feat was not offered (prerequisites): nothing to check
            pytest.skip(f"{feat} not selectable here")
        assert _opt(card, "skill-stealth")["disabledReason"] == "already has Expertise", feat
        assert card["selected"] == [], feat
        assert _pruned_for(res, card["id"]), feat
        assert not _opt(card, "skill-perception").get("disabled"), feat


@needs_data
def test_skill_expert_tce_mixed_accepts_a_skill_without_expertise(catalog):
    res = _rogue_with("skill-expert-tce", "mixed", "skill-perception")
    card = _card(res, "class:rogue:4:asi:feat:skill-expert-tce:expertise-choice-0")
    assert card["selected"] == ["skill-perception"]
    assert set(res["sheet"]["expertiseSkills"]) == {"skill-stealth", "skill-acrobatics", "skill-perception"}


@needs_data
def test_the_srd_rogue_card_itself_stays_unflagged_outside_2024(catalog):
    """Control (E1 revised): a plain duplicate on the SRD Rogue 6 card is still accepted under mixed."""
    picks = {"class:rogue:1:prof-choice-0": ["skill-stealth", "skill-acrobatics", "skill-perception", "skill-insight"],
             "class:rogue:1:expertise-choice:rogue-expertise-1": ["skill-stealth", "skill-acrobatics"],
             "class:rogue:6:expertise-choice:rogue-expertise-2": ["skill-stealth", "skill-perception"]}
    res = resolve(_draft([("rogue", 6, picks)], ruleset="mixed", background="acolyte"), catalog)
    assert _card(res, "class:rogue:6:expertise-choice:rogue-expertise-2")["selected"] == ["skill-stealth", "skill-perception"]


@needs_data
def test_skill_expert_xphb_and_boon_of_skill_under_every_ruleset(catalog):
    """"Choose one skill in which you have proficiency but lack Expertise." / "...in which you lack Expertise." """
    for ruleset in ("mixed", "2014", "2024"):
        res = _rogue_with("skill-expert-xphb", ruleset, "skill-stealth", proficiency_choice_0="skill-arcana",
                          ability_bonus="dex")
        card = _card(res, "class:rogue:4:asi:feat:skill-expert-xphb:expertise-choice-0")
        assert _opt(card, "skill-stealth")["disabledReason"] == "already has Expertise", ruleset
    # Boon of Skill (level 19) as a card template: flagged under every ruleset
    feat = catalog.feats["boon-of-skill-xphb"]
    tpl = resolve_mod._feat_choice_templates([feat])
    assert [c.get("lacksExpertise") for c in tpl if "expertise-choice" in c["id"]] == [True]


@needs_data
def test_the_four_lacks_feats_flag_their_expertise_cards_and_nobody_else(catalog):
    flagged = set()
    for index, feat in catalog.feats.items():
        for c in resolve_mod._feat_choice_templates([feat]):
            if c.get("lacksExpertise"):
                flagged.add(index)
    assert flagged == set(FE6_LACKS)
    flagged_prof = set()
    for index, feat in catalog.feats.items():
        for c in resolve_mod._feat_choice_templates([feat]):
            if c.get("profOrExpertise"):
                flagged_prof.add(index)
    assert flagged_prof == set(FE6_PROF_OR_EXPERTISE)


# ---------------------------------------------------------------- degrade / timing


@needs_data
def test_empty_feat_catalog_degrades(catalog):
    bare = copy.copy(catalog)
    bare.feats = {}
    res = resolve(_draft([("wizard", 4, _asi("wizard", 4, KM, proficiency_choice_0="skill-history"))]), bare)
    assert res["sheet"]["expertiseSkills"] == []


@needs_data
def test_no_feat_draft_is_unchanged_by_the_flags(catalog):
    res = resolve(_draft([("wizard", 4, {})]), catalog)
    assert res["sheet"]["expertiseSkills"] == []
