"""The export gates and prerequisite checks of resolve(): distinct picks, duplicate skills, positioned proficiencies, saves, expertise, invocations, masteries, multiclass prerequisites.

Split from engine/resolve.py (S17); the text below is moved unchanged. `engine.resolve` re-exports every name.
"""
from __future__ import annotations

import re
from catalog import reference_data
from catalog.loader import Catalog
from i18n.messages import msg
from catalog.reference_data import ABILITIES, SUBCLASS_PROFICIENCIES
from . import attacks as attacks_mod
from . import class_choices_2024
from . import subclass_spells_2024
from . import features as features_mod
from .resolve_feats import _feat_build_position, _feat_name_key, _feat_proficiency_ids

def _gate_distinct_choices(choices: list[dict], class_order: list[str] = ()) -> list[dict]:
    """FE7: cards flagged `distinctGroup` (Elemental Adept: "you must choose a different damage type" each time)
    may not repeat an option across the instances of the same feat group (both editions share the group). Walk order
    is origin feats first, then ASI feat cards by (class order, ASI level); the later pick is the duplicate: its option
    is disabled "already chosen for <feat> (n)" (n = which instance holds it) and a stored duplicate is dropped with a
    `pruned` entry. Mutates `choices` in place; returns the pruned entries."""
    indexes = [i for i, c in enumerate(choices) if c.get("distinctGroup")]
    if not indexes:
        return []

    def walk_key(i: int):
        m = _ASI_FEAT_CID_RE.match(choices[i]["id"])
        if not m:
            return (0, 0, 0, i)
        cls_id = m.group(1)
        return (1, class_order.index(cls_id) if cls_id in class_order else len(class_order), int(m.group(2)), i)

    pruned_by_index: dict[int, dict] = {}
    dependents: list[str] = []
    held: dict[str, dict[str, int]] = {}  # group -> {option id: instance number}
    count: dict[str, int] = {}
    for i in sorted(indexes, key=walk_key):
        c = choices[i]
        group = c["distinctGroup"]
        count[group] = count.get(group, 0) + 1
        taken = held.setdefault(group, {})
        name = c["source"]["label"]
        options = [o if o.get("disabled") or o["id"] not in taken
                   else {**o, "disabled": True, "disabledReason": msg("disabled-already-chosen-for-n", name=name, n=taken[o["id"]])}
                   for o in c["options"]]
        kept = [s for s in c.get("selected", []) if s not in taken]
        dropped = [s for s in c.get("selected", []) if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            pruned_by_index[i] = {"choiceId": c["id"], "reason": msg(
                "pruned-distinct-duplicate", label=c["label"], names=[labels.get(d, d) for d in dropped], name=name,
                n=taken[dropped[0]])}
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
        for s in kept:
            taken[s] = count[group]
        for fixed in c.get("distinctFixed", []):  # WF: a list the background fixes is held by this instance
            taken.setdefault(fixed, count[group])
        if dropped and c["id"].endswith(":spell-variant"):  # WF: the spell picks of the dropped list go with it
            dependents.append(c["id"][:-len("spell-variant")] + "spell-choice-")
    if dependents:
        choices[:] = [c for c in choices if not any(c["id"].startswith(d) for d in dependents)]
    return [pruned_by_index[i] for i in sorted(pruned_by_index)]

def _is_expertise_choice(choice: dict) -> bool:
    """Feat expertise picks (`...:expertise-choice-N`) and class-feature ones
    (Rogue/Bard, `class:...:expertise-choice:{feature}`)."""
    return choice["source"]["kind"] in ("feat", "class") and "expertise-choice" in choice["id"]

def _expertise_selected_values(choices: list[dict]) -> list[str]:
    out: list[str] = []
    for c in choices:
        if _is_expertise_choice(c):
            for sel in c.get("selected", []):
                if sel not in out:
                    out.append(sel)
    return out

_ASI_FEAT_CID_RE = re.compile(r"^class:([^:]+):(\d+):asi:feat:")

def _prof_or_expertise_priors(choices: list[dict], resolved_feats: list[dict], fixed_origin_skills: set[str],
                              class_order: list[str]) -> dict[str, set[str]]:
    """FE6 (F-D4): for every card flagged `profOrExpertise` (Keen Mind / Observant XPHB: "If you lack proficiency
    in the chosen skill, you gain proficiency in it, and if you already have proficiency in it, you gain
    Expertise in it"), the skills the character is already proficient in AT THE CARD'S POSITION: origin sources
    (background, species, origin feats) first, then cards and ASI feats at or before its (class order, class
    level), an ASI feat after the class feature of its level, and the flagged cards before it. A later grant of
    the same skill never converts the pick. Returns {card id: skill ids}."""
    flagged = [c for c in choices if c.get("profOrExpertise")]
    if not flagged:
        return {}
    last = (len(class_order) + 1, 0)

    def pos(c: dict):
        return class_choices_2024.card_position(c, class_order) or last

    order = {c["id"]: n for n, c in enumerate(sorted(flagged, key=lambda c: (pos(c), c["id"])))}
    priors: dict[str, set[str]] = {}
    for card in flagged:
        here, rank = pos(card), order[card["id"]]
        prior = set(fixed_origin_skills)
        for c in choices:
            if c is card or c["source"]["kind"] not in ("class", "species", "background", "feat") or "expertise-choice" in c["id"]:
                continue
            if c.get("profOrExpertise"):
                before = order[c["id"]] < rank
            else:
                before = pos(c) <= here
            if before:
                prior.update(s for s in c["selected"] if _is_skill_id(s))
        for f in resolved_feats:  # fixed skill grants of ASI feats sit at their ASI level
            if f.get("_asi_cid") and (_feat_build_position(f, class_order) or last) <= here:
                prior.update(p for p in _feat_proficiency_ids([f]) if p.startswith("skill-"))
        priors[card["id"]] = prior
    return priors

def _is_skill_id(pick: str) -> bool:
    """VF1.2: a real skill id (one of the 18 `reference_data.SKILL_ABILITY` keys). A prefix test is not enough: the XGE
    spell Skill Empowerment has the id `skill-empowerment` and is a legal pick of Bard / Sorcerer / Wizard spell cards."""
    return pick in reference_data.SKILL_ABILITY

def _proficiency_grants(choices: list[dict], catalog: Catalog, resolved_classes: list[dict], resolved_feats: list[dict],
                        bg: dict | None, race: dict | None, subrace: dict | None, xphb_effects, class_order: list[str],
                        ) -> list[tuple[tuple[int, int], str]]:
    """RP12: the FIXED skill / tool proficiency grants of the build as (position, proficiency id): origin sources
    (background, species traits, origin feats) at (-1, 0); a class's fixed proficiencies at (class position, 1); a
    subclass's fixed grants (`SUBCLASS_PROFICIENCIES`) at (class position, 3) (every 2024 subclass starts at 3);
    ASI and Lessons feats at their build position; the RP2 XPHB effects (Mercy) at their feature record's level."""
    origin = (-1, 0)
    grants: list[tuple[tuple[int, int], str]] = []
    if bg:
        grants += [(origin, p["index"]) for p in bg.get("starting_proficiencies", [])]
    if race:
        for ref in list(race.get("traits", [])) + (list(subrace.get("racial_traits", [])) if subrace else []):
            trait = catalog.traits.get(ref["index"])
            if trait:
                grants += [(origin, p["index"]) for p in trait.get("proficiencies", [])]
    for f in resolved_feats:
        pos = _feat_build_position(f, class_order) or origin
        grants += [(pos, p) for p in _feat_proficiency_ids([f])]
    for rc in resolved_classes:
        if not rc["cls"] or rc["cls_id"] not in class_order:
            continue
        at = class_order.index(rc["cls_id"])
        fixed = rc["cls"].get("proficiencies", []) if at == 0 else rc["cls"].get("multi_classing", {}).get("proficiencies", [])
        grants += [((at, 1), p["index"]) for p in fixed]
        grants += [((at, 3), p) for p in SUBCLASS_PROFICIENCIES.get(rc["subclass_id"], [])]
    for cls_id, _lvl, effect in xphb_effects:
        if cls_id in class_order:
            level = (catalog.features.get(effect.get("feature_id")) or {}).get("level") or 1
            grants += [((class_order.index(cls_id), level), p)
                       for p in list(effect.get("skills") or []) + list(effect.get("proficiencies") or [])]
    return grants

def _gate_duplicate_skill_picks(choices: list[dict], class_order: list[str]) -> list[dict]:
    """RPF (PHB: you can't gain the same proficiency twice, pick another): generic skill duplicates between the
    ordinary class / species / multiclass proficiency pick cards, all rulesets. The cards are walked in (class order,
    class level) order, origin (species) first and a multiclass card at (its class, 1); a card keeps the skills held
    by the cards before it out of its options ("already proficient") and drops a stored duplicate with a
    non-blocking `pruned` entry. Skill ids only; expertise, Keen Mind style (`profOrExpertise`) and the positioned
    subclass picks have their own gates. Mutates `choices`; returns the pruned entries."""
    last = (len(class_order) + 1, 0)

    def eligible(c: dict) -> bool:
        return (c["source"]["kind"] in ("class", "species") and "expertise-choice" not in c["id"]
                and ("prof-choice-" in c["id"] or "proficiency-choice" in c["id"])
                and not c.get("profOrExpertise") and not class_choices_2024.is_positioned_proficiency_card(c)
                and any(o["id"].startswith("skill-") for o in c["options"]))

    cards = sorted((c for c in choices if eligible(c)),
                   key=lambda c: (class_choices_2024.proficiency_position(c, class_order) or last, c["id"]))
    pruned: list[dict] = []
    held: set[str] = set()
    for card in cards:
        i = next(n for n, c in enumerate(choices) if c["id"] == card["id"])
        c = choices[i]
        dup = [s for s in c["selected"] if s in held]
        options = [o if o.get("disabled") or o["id"] not in held
                   else {**o, "disabled": True, "disabledReason": msg("disabled-already-proficient")} for o in c["options"]]
        kept = [s for s in c["selected"] if s not in held]
        if dup:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            pruned.append({"choiceId": c["id"], "reason": msg(
                "pruned-proficient", label=c["label"], names=[labels.get(d, d) for d in dup])})
        choices[i] = {**c, "options": options, "selected": kept, "status": "resolved" if len(kept) == c["count"] else "pending"}
        held.update(s for s in kept if _is_skill_id(s))
    return pruned

def _gate_positioned_proficiencies(choices: list[dict], catalog: Catalog, resolved_classes: list[dict],
                                   resolved_feats: list[dict], bg: dict | None, race: dict | None,
                                   subrace: dict | None, xphb_effects, class_order: list[str]) -> list[dict]:
    """C6b-2 + F3a-4, generalised by RP12 into "positioned proficiency picks": Primal Knowledge and the subclass skill
    / tool picks (Lore, Student of War, Otherworldly Glamour). They are walked in (class order, class level) order.
    Each pick sees everything gained at or before its position (fixed grants, other cards, ASI feats, earlier
    positioned picks): such options are disabled "already proficient" and a stored duplicate is dropped with a
    `pruned` entry. The picks that come later then see its choice the same way
    (`class_choices_2024.gate_after_positioned_pick`). A grant that comes later never converts a pick. Mutates
    `choices`; returns the pruned entries."""
    cards = [c for c in choices if class_choices_2024.is_positioned_proficiency_card(c)]
    if not cards:
        return []
    last = (len(class_order) + 1, 0)
    grants = _proficiency_grants(choices, catalog, resolved_classes, resolved_feats, bg, race, subrace, xphb_effects, class_order)
    pruned: list[dict] = []
    held: set[str] = set()  # the (kept) picks of the positioned cards walked so far
    for card in sorted(cards, key=lambda c: (class_choices_2024.proficiency_position(c, class_order) or last, c["id"])):
        pos = class_choices_2024.proficiency_position(card, class_order) or last
        prior = {pid for at, pid in grants if at <= pos} | held
        for c in choices:
            if (c["source"]["kind"] not in ("class", "species", "background", "feat") or "expertise-choice" in c["id"]
                    or class_choices_2024.is_positioned_proficiency_card(c)):
                continue
            at = class_choices_2024.proficiency_position(c, class_order)
            if at is None or at > pos:
                continue
            is_prof_card = "prof-choice-" in c["id"] or "proficiency-choice" in c["id"]
            prior.update(s for s in c["selected"] if _is_skill_id(s) or is_prof_card)
        if class_choices_2024.is_primal_knowledge_card(card):
            pruned += class_choices_2024.gate_primal_knowledge(choices, prior)
            name = "Primal Knowledge"
        else:
            pruned += class_choices_2024.gate_positioned_card(choices, card["id"], prior)
            name = catalog.features[class_choices_2024.pick_spec_for_card(card)["feature"]]["name"]
        picked = set(next(c for c in choices if c["id"] == card["id"])["selected"])
        held |= picked
        if picked:
            pruned += class_choices_2024.gate_after_positioned_pick(choices, class_order, pos, picked, name)
    return pruned

def _save_grant_positions(catalog: Catalog, resolved_feats: list[dict], choices: list[dict], class_feature_list,
                          xphb_effects, ruleset: str, class_order: list[str], class_saves: list[str],
                          ) -> list[tuple[tuple[int, int], str]]:
    """RP12: every saving throw proficiency of the build as (position, ability): the first class's saves at (0, 1),
    origin / ASI feats and Resilient-style `save-choice` cards at their position, class features (Diamond Soul,
    Slippery Mind ...) at their feature record's level."""
    origin = (-1, 0)
    out = [((0, 1), ab) for ab in class_saves]
    for f in resolved_feats:
        out += [(_feat_build_position(f, class_order) or origin, ab) for ab in f.get("saving_throw_proficiencies", [])]
    for c in choices:
        if c["source"]["kind"] == "feat" and ":save-choice-" in c["id"]:
            pos = class_choices_2024.proficiency_position(c, class_order) or origin
            out += [(pos, a.upper()) for a in c["selected"]]
    for cls_id, lvl, idx in class_feature_list:
        if cls_id not in class_order:
            continue
        granted = features_mod.save_proficiencies(features_mod.active_effects([(cls_id, lvl, idx)]), [idx], ruleset)
        level = (catalog.features.get(idx) or {}).get("level") or lvl
        out += [((class_order.index(cls_id), level), ab) for ab in granted]
    for cls_id, _lvl, effect in xphb_effects:
        if cls_id in class_order and effect.get("save_proficiency"):
            level = (catalog.features.get(effect.get("feature_id")) or {}).get("level") or 1
            grant = effect["save_proficiency"]
            out += [((class_order.index(cls_id), level), ab) for ab in (ABILITIES if grant == "all" else grant)]
    return out

def _gate_save_picks(choices: list[dict], catalog: Catalog, resolved_classes: list[dict], resolved_feats: list[dict],
                     class_feature_list, xphb_effects, ruleset: str, class_saves: list[str],
                     proficient_save_abilities: list[str]) -> list[dict]:
    """RP12 Gloom Stalker 7 Iron Mind: "You gain proficiency in Wisdom saving throws. If you already have this
    proficiency, you instead gain proficiency in Intelligence or Charisma saving throws (your choice)." "Already" =
    gained at or before the card's position (class order, class level). Without it the card is removed and Wisdom is
    added outright (a stored pick is reported); with it the card stays, the saves already held are disabled and the
    pick is added to `proficient_save_abilities` (mutated). Returns the pruned entries."""
    cards = [c for c in choices if class_choices_2024.is_save_pick_card(c)]
    if not cards:
        return []
    class_order = [rc["cls_id"] for rc in resolved_classes if rc["cls"]]
    grants = _save_grant_positions(catalog, resolved_feats, choices, class_feature_list, xphb_effects, ruleset,
                                   class_order, class_saves)
    pruned: list[dict] = []
    for card in cards:
        spec = class_choices_2024.pick_spec_for_card(card)
        pos = class_choices_2024.proficiency_position(card, class_order)
        prior = {ab for at, ab in grants if at <= pos}
        if spec["fixed"] not in prior:
            choices[:] = [c for c in choices if c["id"] != card["id"]]
            if card["selected"]:
                pruned.append({"choiceId": card["id"], "reason": msg("pruned-iron-mind", label=card["label"])})
            if spec["fixed"] not in proficient_save_abilities:
                proficient_save_abilities.append(spec["fixed"])
            continue
        pruned += class_choices_2024.gate_positioned_card(choices, card["id"], {ab.lower() for ab in prior})
        for sel in next(c for c in choices if c["id"] == card["id"])["selected"]:
            if sel.upper() not in proficient_save_abilities:
                proficient_save_abilities.append(sel.upper())
    return pruned

def _gate_expertise_choices(
    choices: list[dict], proficient_skills: set[str], fixed_expertise=(), class_order: list[str] = (),
    ruleset: str = "mixed", poe_priors: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Restrict every feat- or class-sourced Expertise Choice to skills (and,
    for the Rogue, tools) the character is proficient in. Mutates `choices` in place (entries replaced by index);
    returns non-blocking pruned entries for selections that were dropped.

    C6b-1: a card flagged `lacksExpertise` (2024 Deft Explorer, Ranger 9: "with which you lack
    Expertise") also disables, and drops stored picks of, skills that already have Expertise from
    an earlier source. The walk order is fixed Expertise from feats (`fixed_expertise`), origin
    feat cards, then class cards and ASI feat cards by (position in `class_order`, class level;
    F3a-3: an ASI feat card sits at its ASI level, after the class feature of the same level); the
    later pick is the duplicate. Decision E1 (revised 2026-10-11): under ruleset 2024 every
    Expertise card behaves as flagged (Bard, Rogue, Scholar, feat cards too); outside 2024 only
    flagged cards do (none in practice), an unflagged duplicate is simply wasted."""
    pruned_by_index: dict[int, dict] = {}  # reported in `choices` order, whatever the walk order
    poe_priors = poe_priors or {}
    indexes = [i for i, c in enumerate(choices) if _is_expertise_choice(c) or c["id"] in poe_priors]

    def walk_key(i: int):
        c = choices[i]
        if c["source"]["kind"] == "feat":
            m = _ASI_FEAT_CID_RE.match(c["id"])
            if not m:
                return (0, 0, 0, 0, i)  # origin feats come first
            cls_id = m.group(1)
            return (1, class_order.index(cls_id) if cls_id in class_order else len(class_order), int(m.group(2)), 1, i)
        cls_id = c["source"].get("id")
        return (1, class_order.index(cls_id) if cls_id in class_order else len(class_order), c["source"].get("level") or 0, 0, i)

    have: set[str] = set(fixed_expertise)
    for i in sorted(indexes, key=walk_key):
        c = choices[i]
        if c["id"] in poe_priors:
            # FE6: a proficiency-or-Expertise card. Any skill may be picked (an unproficient one just becomes a
            # proficiency); a pick already proficient at the card's position is Expertise, and under 2024 (E1
            # revised) may not repeat an Expertise skill.
            prior = poe_priors[c["id"]]
            options = [o if o.get("disabled") or not (ruleset == "2024" and o["id"] in prior and o["id"] in have)
                       else {**o, "disabled": True, "disabledReason": msg("disabled-has-expertise")} for o in c["options"]]
            kept = [s for s in c.get("selected", []) if not (ruleset == "2024" and s in prior and s in have)]
            dropped = [s for s in c.get("selected", []) if s not in kept]
            if dropped:
                labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
                names = [labels.get(d, d) for d in dropped]
                pruned_by_index[i] = {"choiceId": c["id"],
                                      "reason": msg("pruned-expertise-already", label=c["label"], names=names)}
            choices[i] = {**c, "options": options, "selected": kept,
                          "status": "resolved" if len(kept) == c["count"] else "pending"}
            have.update(s for s in kept if s in prior)
            continue
        # User decision 2026-10-11: under 2024 EVERY Expertise card forbids a skill that already has Expertise
        # (stricter than RAW on purpose: a pick is never wasted). mixed / 2014 keep the flag-only behavior.
        lacks = ruleset == "2024" or bool(c.get("lacksExpertise"))
        options = []
        for o in c["options"]:
            if o.get("disabled"):
                options.append(o)
            elif o["id"] not in proficient_skills:
                options.append({**o, "disabled": True, "disabledReason": msg("disabled-not-proficient")})
            elif lacks and o["id"] in have:
                options.append({**o, "disabled": True, "disabledReason": msg("disabled-has-expertise")})
            else:
                options.append(o)
        enabled = {o["id"] for o in options if not o.get("disabled")}
        selected = c.get("selected", [])
        kept = [s for s in selected if s in enabled or (s in proficient_skills and not lacks)]
        dropped = [s for s in selected if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = [labels.get(d, d) for d in dropped]
            lost_profs = [d for d in dropped if d not in proficient_skills]
            if lost_profs:
                reason = msg("pruned-expertise-not-proficient", label=c["label"], names=names)
            else:
                reason = msg("pruned-expertise-already-chosen", label=c["label"], names=names)
            pruned_by_index[i] = {"choiceId": c["id"], "reason": reason}
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
        have.update(kept)
    return [pruned_by_index[i] for i in sorted(pruned_by_index)]

def _invocation_unmet(inv: dict, warlock_level: int, pacts: set[str], cantrips: set[str]) -> str | None:
    """Why an Eldritch Invocation's prerequisites are not met, or None."""
    for req in inv.get("prerequisites") or []:
        kind = req.get("type")
        if kind == "level" and warlock_level < req.get("level", 0):
            return msg("disabled-requires-warlock-level", level=req["level"])
        if kind == "feature" and req.get("feature", "").rsplit("/", 1)[-1] not in pacts:
            return msg("disabled-requires", name=req["feature"].rsplit("/", 1)[-1].replace("-", " ").title().replace(" Of ", " of ").replace(" The ", " the "))
        if kind == "spell" and req.get("spell", "").rsplit("/", 1)[-1] not in cantrips:
            return msg("disabled-requires-cantrip", spell=req["spell"].rsplit("/", 1)[-1].replace("-", " "))
    return None

def _gate_invocation_choices(choices: list[dict], resolved_classes: list[dict], catalog: Catalog) -> list[dict]:
    """Disable Eldritch Invocation options whose prerequisites (warlock
    level, Pact Boon, Eldritch Blast) are unmet and drop stale selections of
    them. Mutates `choices` in place; returns non-blocking pruned entries."""
    pruned: list[dict] = []
    for i, c in enumerate(choices):
        if c["source"]["kind"] != "class" or ":invocations:" not in c["id"]:
            continue
        cls_id = c["source"]["id"]
        level = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == cls_id), 0)
        if class_choices_2024.is_invocation_card_2024(c):  # C7a: prerequisites incl. Pacts inside the card
            cantrips = [sel for o in choices if o["id"] == f"class:{cls_id}:spells-cantrips" for sel in o["selected"]]
            choices[i], more = class_choices_2024.gate_invocations(
                catalog, c, level, cantrips, class_choices_2024.tome_picks(choices)["cantrips"],  # C7c: Tome cantrips count
                class_choices_2024.feat_tome_picks(choices)["cantrips"])  # RP20: so do those of a Tome held through Eldritch Adept
            pruned += more
            continue
        pacts = {sel for o in choices if o["source"].get("id") == cls_id and ":feature:" in o["id"] for sel in o["selected"]}
        cantrips = {sel for o in choices if o["id"] == f"class:{cls_id}:spells-cantrips" for sel in o["selected"]}
        options, unmet_ids = [], {}
        for o in c["options"]:
            reason = _invocation_unmet(catalog.features.get(o["id"]) or {}, level, pacts, cantrips)
            if reason:
                unmet_ids[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": reason}
            options.append(o)
        selected = [s for s in c["selected"] if s not in unmet_ids]
        dropped = [unmet_ids[s] for s in c["selected"] if s in unmet_ids]
        if dropped:
            pruned.append({
                "choiceId": c["id"],
                "reason": msg("pruned-invocation-prereq", label=c["label"], names=dropped),
            })
        choices[i] = {**c, "options": options, "selected": selected,
                      "status": "resolved" if len(selected) == c["count"] else "pending"}
    return pruned

def _gate_feat_invocation_prereqs(choices: list[dict], resolved_classes: list[dict], catalog: Catalog) -> list[dict]:
    """FE9 Eldritch Adept: "If the invocation has a prerequisite of any kind, you can choose that invocation only if
    you're a warlock who meets the prerequisite." The `:invocation` feat card's options are disabled with the
    warlock prerequisite reason (a non-Warlock has level 0, no Pact and no cantrips, so every invocation with a
    prerequisite is closed) and a stored pick of one is dropped with a `pruned` entry. Pacts of a 2024 Warlock
    (invocations) count as the matching 2014 Pact. Mutates `choices`; returns the pruned entries."""
    cards = [i for i, c in enumerate(choices) if c["source"]["kind"] == "feat" and c["id"].endswith(":invocation")]
    if not cards:
        return []
    level = next((rc["level"] for rc in resolved_classes if rc["cls_id"] == "warlock" and rc["cls"]), 0)
    pacts = {sel for o in choices if o["source"].get("id") == "warlock" and ":feature:" in o["id"] for sel in o["selected"]}
    for o in choices:
        if class_choices_2024.is_invocation_card_2024(o):
            pacts |= {m.group(0)[len("opt-"):-len("-xphb")] for sel in o["selected"]
                      if (m := re.match(r"^opt-pact-of-the-(?:blade|chain|tome)-xphb", sel))}
    cantrips = {sel for o in choices if o["id"] == "class:warlock:spells-cantrips" for sel in o["selected"]}
    # RP20: the XPHB records carry `prerequisite_2024` (Warlock level, optional feature, damaging / attack cantrip);
    # the Warlock's own picks (Pacts included) and cantrips (+ Pact of the Tome cantrips) are what the feat's pick is
    # checked against, a non-Warlock has level 0 and none of them
    held_2024 = [sel for o in choices if class_choices_2024.is_invocation_card_2024(o) for sel in o["selected"]]
    cantrips_2024 = sorted(cantrips) + class_choices_2024.tome_picks(choices)["cantrips"]
    pruned = []
    for i in cards:
        c = choices[i]
        unmet, options = {}, []
        for o in c["options"]:
            if o.get("disabled"):
                reason = None
            elif o["id"].startswith("opt-") and o["id"].endswith("-xphb"):
                reason = class_choices_2024.invocation_unmet(catalog, o["id"], level, set(held_2024), cantrips_2024)
            else:
                reason = _invocation_unmet(catalog.features.get(o["id"]) or {}, level, pacts, cantrips)
            if reason:
                unmet[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": reason}
            options.append(o)
        kept = [s for s in c["selected"] if s not in unmet]
        if len(kept) != len(c["selected"]):
            pruned.append({"choiceId": c["id"], "reason": msg(
                "pruned-eldritch-adept-prereq", label=c["label"], names=[unmet[s] for s in c["selected"] if s in unmet])})
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
    return pruned

_PICK_PREFIX = re.compile(r"^(?:Fighting Style|Metamagic|Eldritch Invocation):\s*")

_FEAT_PICK_GROUPS = {":fighting-style": "style", ":maneuvers": "maneuver", ":metamagic": "metamagic", ":invocation": "invocation"}

_SRD_METAMAGIC_CID = re.compile(r"^class:sorcerer:\d+:feature:metamagic-\d+$")

_BATTLE_MASTER_CID = re.compile(r"^class:fighter:\d+:feature:battle-master-(?:phb|xphb)-3-battle-master$")

def _gate_duplicate_picks(choices: list[dict], catalog: Catalog, class_order: list[str],
                          srd_style_cids: set[str], fs_cids: set[str]) -> list[dict]:
    """FE9: one option cannot be held twice across the cards that offer the same family of options (Fighting Initiate's
    "the one you choose must be different", and the same logic for maneuvers, Metamagic and invocations, which a feat
    can learn on top of the class's own list). Families: fighting styles (SRD class cards, 2024 Fighting Style feat
    cards, Fighting Initiate), maneuvers (Battle Master, Martial Adept), Metamagic (Sorcerer SRD / 2024, Metamagic
    Adept), invocations (Warlock, Eldritch Adept). Cards are walked in build order (origin feats first, then by
    (class index, level), a class card before the ASI of its level) and the later holder is the duplicate: its option
    is disabled "already taken (<name>, <holder>)" and a stored duplicate is dropped with a `pruned` entry. Options are
    compared by name, so the 2014 and 2024 editions of one option are the same. Fighting Style feat cards (the feat is
    already resolved) and the 2024 invocation card only hold options. Mutates `choices`; returns the pruned entries."""
    def info(c):
        src, cid = c["source"], c["id"]
        if src["kind"] == "feat":
            for suffix, group in _FEAT_PICK_GROUPS.items():
                if cid.endswith(suffix):
                    return group, True, src["label"]
            return None
        if src["kind"] != "class":
            return None
        if cid in srd_style_cids:
            return "style", True, "SRD"
        if cid in fs_cids:
            return "style", False, None
        if _BATTLE_MASTER_CID.match(cid):
            return "maneuver", True, "Battle Master"
        if _SRD_METAMAGIC_CID.match(cid) or cid == class_choices_2024.metamagic_cid():
            return "metamagic", True, "Sorcerer"
        if ":invocations:" in cid and src.get("id") == "warlock":
            return "invocation", not class_choices_2024.is_invocation_card_2024(c), "Warlock"
        return None

    def position(i):
        c = choices[i]
        m = _ASI_FEAT_CID_RE.match(c["id"])
        slot = lambda cls: class_order.index(cls) if cls in class_order else len(class_order)  # noqa: E731
        if c["source"]["kind"] == "feat":
            return (1, slot(m.group(1)), int(m.group(2)), 1, i) if m else (0, 0, 0, 0, i)
        return (1, slot(c["source"].get("id")), c["source"].get("level") or 0, 0, i)

    def key_and_name(group, option_id, label):
        if group == "style":
            if option_id.startswith("feat:"):
                feat = catalog.feats.get(option_id[len("feat:"):])
                return (_feat_name_key(feat), feat["name"], feat.get("source")) if feat else (option_id, option_id, None)
            name = _PICK_PREFIX.sub("", (catalog.features.get(option_id) or {}).get("name") or label).strip()
            return name.lower(), name, None
        name = re.sub(r"\s*\([^)]*\)\s*$", "", _PICK_PREFIX.sub("", label)).strip()
        return name.lower(), name, None

    members = [(i, *found) for i, c in enumerate(choices) if (found := info(c))]
    feat_groups = {g for i, g, _m, _h in members if choices[i]["source"]["kind"] == "feat"}
    members = [m for m in members if m[1] in feat_groups]  # no feat pick, no change: class lists stay as they were
    if not members:
        return []
    held: dict[str, dict[str, str]] = {}  # options held by any card, read by the feat cards
    held_by_feat: dict[str, dict[str, str]] = {}  # options held by a feat card, read by the class cards
    pruned = []
    for i, group, modifiable, holder in sorted(members, key=lambda m: position(m[0])):
        c = choices[i]
        is_feat = c["source"]["kind"] == "feat"
        taken = (held if is_feat else held_by_feat).setdefault(group, {})
        labels = {o["id"]: o["label"] for o in c["options"]}
        picks = [(s, *key_and_name(group, s, labels.get(s, s))) for s in c["selected"]]  # (id, key, name, feat source)
        if modifiable:
            options = [{**o, "disabled": True, "disabledReason": msg("disabled-already-taken-from", where=taken[key])}
                       if (key := key_and_name(group, o["id"], o["label"])[0]) in taken and not o.get("disabled") else o
                       for o in c["options"]]
            dropped = [p for p in picks if p[1] in taken]
            picks = [p for p in picks if p[1] not in taken]
            if dropped:
                pruned.append({"choiceId": c["id"], "reason": msg(
                    "pruned-already-taken", label=c["label"], names=[p[2] for p in dropped], where=taken[dropped[0][1]])})
            if dropped or any(a is not b for a, b in zip(options, c["options"])):
                ids = [p[0] for p in picks]
                choices[i] = {**c, "options": options, "selected": ids,
                              "status": "resolved" if len(ids) == c["count"] else "pending"}
        for _id, key, name, feat_source in picks:
            label = f"{name}, {holder or feat_source or 'feat'}"
            held.setdefault(group, {}).setdefault(key, label)
            if is_feat:
                held_by_feat.setdefault(group, {}).setdefault(key, label)
    return pruned

def _multiclass_prerequisite_problems(resolved_classes: list[dict], final_scores: dict[str, int], use_prerequisites: bool) -> list[dict]:
    """Checks every resolved class's multi_classing.prerequisites (a plain
    list, ALL must be met) or multi_classing.prerequisite_options (an
    options-array, "choose N of these" — Fighter is the only SRD class
    with this shape, STR-or-DEX) against the character's final ability
    scores. Applies to EVERY class, not just secondary ones — the SRD
    prerequisite is a two-way gate (both the class you already have and
    the class you're adding need their own prerequisite met), which
    matches this loop iterating over all of resolved_classes, not just
    index > 0. Never hides the class — only appends a problem.

    A character with fewer than two actually-resolved classes isn't
    multiclassing at all, so the check never applies to them regardless of
    the preference's value — otherwise a single-class character (e.g. a
    lone Wizard with low INT) would get a spurious
    multiclass-prerequisite-unmet problem for a class they aren't even
    multiclassing into."""
    if not use_prerequisites:
        return []
    if len([rc for rc in resolved_classes if rc["cls"]]) < 2:
        return []
    problems = []
    for rc in resolved_classes:
        cls, cls_id = rc["cls"], rc["cls_id"]
        if not (cls and cls_id):
            continue
        mc = cls.get("multi_classing", {})
        prereqs = mc.get("prerequisites")
        prereq_options = mc.get("prerequisite_options")
        if prereqs:
            met = all(final_scores.get(p["ability_score"]["index"].upper(), 0) >= p["minimum_score"] for p in prereqs)
        elif prereq_options:
            options = prereq_options.get("from", {}).get("options", [])
            choose = prereq_options.get("choose", 1)
            met_count = sum(
                1 for opt in options
                if final_scores.get(opt["ability_score"]["index"].upper(), 0) >= opt["minimum_score"]
            )
            met = met_count >= choose
        else:
            met = True  # no prerequisite data at all — nothing to fail
        if not met:
            problems.append({
                "id": f"multiclass-prerequisite-unmet-{cls_id}",
                "message": msg("multiclass-prerequisite-unmet", cls=cls["name"]),
            })
    return problems

def _is_mastery_choice(tpl: dict) -> bool:
    """C2 class Weapon Mastery cards and (FE8) Weapon Master (XPHB)'s feat card share the `:weapon-mastery` suffix."""
    return tpl["source"]["kind"] in ("class", "feat") and tpl["id"].endswith(":weapon-mastery")

def _is_count_variable_choice(tpl: dict) -> bool:
    """True for the spell choices whose allowed count follows the class
    level table / casting modifier (see _spell_choice_templates), so a
    stored over-count is staleness rather than a malformed Draft. Broader than
    the frontend `isSpellChoiceId` in frontend/src/pages/ClassPage.tsx (which
    only sorts spell cards into the Spells tab): this also covers level-scaled
    feat spell picks, Weapon Mastery and Eldritch Invocations, which the
    frontend does not treat as spell cards."""
    if tpl.get("count_by_level"):
        return True  # level-scaled feat spell picks (Ritual Caster) and Elemental Attunement: over-count is staleness
    if _is_mastery_choice(tpl):
        return True  # C2: Weapon Mastery count follows the class table (FE8: and the feat card's proficiency gate)
    if tpl["source"]["kind"] == "class" and ":invocations:" in tpl["id"]:
        return True  # Eldritch Invocations known follow the warlock level table
    if class_choices_2024.is_dependent_choice(tpl):
        return True  # C7c: invocation dependents (targets, Tome, pact weapon, Lessons feat) follow the spell cards / inventory; RP20: also the Eldritch Adept's
    if class_choices_2024.is_additional_secrets_card(tpl):
        return True  # RPX1: the offered spell levels follow the Bard table (and the sources filter)
    if subclass_spells_2024.is_pick_card(tpl):
        return True  # RP17: Savants (count and spell levels follow the Wizard table), Improved Illusions, Magical Discoveries
    # C6d: Spell Mastery / Signature Spells picks follow the spellbook and the class level
    return tpl["source"]["kind"] == "class" and tpl["id"].endswith(
        (":spells-cantrips", ":spells-known", ":spellbook", ":spell-mastery-1", ":spell-mastery-2", ":signature-spells"))

def _mastery_filter_reason(cls_id: str, item: dict) -> str | None:
    """Why the class's Weapon Mastery filter excludes a weapon, or None.
    Barbarian: Simple or Martial Melee. Fighter, Paladin, Ranger and Rogue: Simple or Martial (every
    weapon); F3a-8: the XPHB Rogue text is "two kinds of weapons of your choice with which you have
    proficiency", so only the proficiency gate limits the Rogue."""
    if cls_id == "barbarian" and item.get("weapon_range") != "Melee":
        return msg("disabled-melee-only")
    return None

def _gate_mastery_choices(choices: list[dict], catalog: Catalog, proficient_weapons: set[str]) -> list[dict]:
    """Disable Weapon Mastery options the character is not proficient with, drop stale
    selections of them, and only then cut the rest to the card's count (F1: the generic
    pass leaves mastery picks un-truncated, so a non-proficient pick never costs a valid
    one its place). Mutates `choices`; returns non-blocking pruned, each naming its reason."""
    pruned: list[dict] = []
    mastered: set[str] = set()  # FE8: weapons already mastered by a class card; the feat card (walked last) may not repeat them
    for i, c in sorted(((i, c) for i, c in enumerate(choices) if _is_mastery_choice(c)),
                       key=lambda ic: ic[1]["source"]["kind"] == "feat"):
        is_feat = c["source"]["kind"] == "feat"
        options, lacking, repeated = [], {}, {}
        for o in c["options"]:
            item = catalog.items.get(o["id"])
            if item and not o.get("disabled") and not attacks_mod.weapon_is_proficient(item, proficient_weapons):
                lacking[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": msg("disabled-not-proficient")}
            elif is_feat and not o.get("disabled") and o["id"] in mastered:
                repeated[o["id"]] = o["label"]
                o = {**o, "disabled": True, "disabledReason": msg("disabled-already-mastered")}
            options.append(o)
        dup = [repeated[s] for s in c["selected"] if s in repeated and s not in lacking]
        if dup:
            pruned.append({"choiceId": c["id"], "reason": msg("pruned-mastered-through-class", label=c["label"], names=dup)})
        proficient = [s for s in c["selected"] if s not in lacking and s not in repeated]
        selected = proficient[: c["count"]]
        dropped = [lacking[s] for s in c["selected"] if s in lacking]
        if dropped:
            pruned.append({
                "choiceId": c["id"],
                "reason": msg("pruned-weapon-not-proficient", label=c["label"], names=dropped),
            })
        overflow = proficient[c["count"]:]
        if overflow:
            names = [(catalog.items.get(d) or {}).get("name", d) for d in overflow]
            pruned.append({
                "choiceId": c["id"],
                "reason": msg("pruned-count-overflow", id=c["id"], count=c["count"], n=len(overflow), names=names),
            })
        choices[i] = {**c, "options": options, "selected": selected,
                      "status": "resolved" if len(selected) == c["count"] else "pending"}
        if not is_feat:
            mastered.update(selected)
    return pruned

def _weapon_masteries(choices: list[dict], catalog: Catalog) -> list[dict]:
    """sheet.weaponMasteries: every selected mastery weapon, first-seen order, deduped."""
    out: list[dict] = []
    for c in choices:
        if not _is_mastery_choice(c):  # class cards, then (FE8) Weapon Master (XPHB)'s feat card
            continue
        for sel in c["selected"]:
            item = catalog.items.get(sel)
            if item and item.get("mastery") and all(m["itemId"] != sel for m in out):
                out.append({"itemId": sel, "name": item["name"], "mastery": item["mastery"]})
    return out
