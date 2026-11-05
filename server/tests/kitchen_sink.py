from __future__ import annotations

"""Shared by the S6 export sweep (test_export_fields.py, test_app.py): fully chosen
real-catalog drafts that put every R/C-slice field on the sheet at once."""
import copy

_BASE = {"STR": 16, "DEX": 14, "CON": 14, "INT": 14, "WIS": 14, "CHA": 16}
_WL_INV = "class:warlock:2:invocations:eldritch-invocations"
_WL_INV_2024 = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
_P = "eldritch-invocation-"


def _sub(index, level, ruleset="mixed", sub=None, overrides=None, equip=(), marks=(), origin=None, feats=False, once=False):
    spec = {"classes": [(index, level, sub)], "ruleset": ruleset, "overrides": overrides or {},
            "equip": list(equip), "marks": marks}
    if feats:  # FE12: a feat-holding draft (the golden adds it once, under `sources` [])
        spec["feats"] = True
    if once:  # G1: a draft whose picks a "srd" source filter would hide (SCAG Elk / Tiger): added once, under `sources` []
        spec["once"] = True
    if origin:  # F3b: (species id, background id) instead of the SRD Human / Acolyte
        spec["origin"] = origin
    return spec


_XPHB_ORIGIN = ("human-xphb", "soldier-xphb")


# id -> spec. `marks` name the skip markers the draft needs (see needs()).
KITCHEN_SINK: dict[str, dict] = {
    "barbarian20-2014": _sub("barbarian", 20, "2014", marks=("classes",)),
    "barbarian20-2024": _sub("barbarian", 20, "2024", marks=("classes", "official"),
                             equip=[{"itemId": "greataxe", "qty": 1, "equipped": True}]),
    "monk14": _sub("monk", 14, marks=("classes",)),
    "paladin6": _sub("paladin", 6, marks=("classes",)),
    "cleric6": _sub("cleric", 6, marks=("classes",)),
    "warlock17": _sub("warlock", 17, marks=("classes", "spells"), overrides={
        "class:warlock:spells-cantrips": ["eldritch-blast"],
        _WL_INV: [_P + n for n in ("agonizing-blast", "armor-of-shadows", "devils-sight",
                                   "misty-visions", "mask-of-many-faces")]}),
    "fighter10-2024": _sub("fighter", 10, "2024", marks=("classes", "official"), overrides={
        "class:fighter:1:fighting-style": ["feat:dueling-xphb"],
        "class:fighter:weapon-mastery": ["longsword"]},
        equip=[{"itemId": "longsword", "qty": 1, "equipped": True}]),
    "warlock7-2024": _sub("warlock", 7, "2024", marks=("classes", "official", "spells"), overrides={
        "class:warlock:spells-cantrips": ["eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"],
        _WL_INV_2024: ["opt-pact-of-the-tome-xphb", "opt-pact-of-the-blade-xphb", "opt-thirsting-blade-xphb",
                       "opt-agonizing-blast-xphb", "opt-lessons-of-the-first-ones-xphb", "opt-devils-sight-xphb"],
        "class:warlock:invocation:opt-agonizing-blast-xphb:cantrip": ["eldritch-blast-xphb"],
        "class:warlock:invocation:opt-pact-of-the-blade-xphb:weapon": ["longsword"]},
        equip=[{"itemId": "longsword", "qty": 1, "equipped": True}]),
    "wizard5-2014": _sub("wizard", 5, "2014", marks=("classes",)),
    "wizard5-2024": _sub("wizard", 5, "2024", marks=("classes", "official")),
    # RP15 (E11b): the SRD Spell Mastery (a reaction is allowed) and Signature Spell picks, with a stored prepared list
    "wizard20-2014": _sub("wizard", 20, "2014", marks=("classes",), overrides={
        "class:wizard:spellbook": ["shield", "magic-missile", "detect-magic", "web", "haste", "fireball", "counterspell", "fly"],
        "class:wizard:spells-known": ["magic-missile", "web", "haste"],
        "class:wizard:18:spell-mastery-1": ["shield"], "class:wizard:18:spell-mastery-2": ["web"],
        "class:wizard:20:signature-spells": ["fireball", "counterspell"]}),
    # RP16 (E11a): SRD Bard 10 with Magical Secrets: Fireball (Wizard) and Sacred Flame (a Cleric cantrip that takes a
    # known slot), 12 ordinary Bard spells (the card needs 14)
    "bard10-2014": _sub("bard", 10, "2014", marks=("classes",), overrides={
        "class:bard:spells-known": ["cure-wounds", "healing-word", "heroism", "dissonant-whispers", "hold-person",
                                    "invisibility", "suggestion", "hypnotic-pattern", "dimension-door", "polymorph",
                                    "greater-invisibility", "hold-monster", "fireball", "sacred-flame"]}),
    # RPX1 (Extra 1): SRD Lore Bard 6, Bonus Proficiencies (3 skills) and Additional Magical Secrets (Fireball and the
    # Cleric cantrip Sacred Flame, outside the 9 known spells)
    "bard6-lore-2014": _sub("bard", 6, "2014", sub="lore", marks=("classes",), overrides={
        "class:bard:3:feature:bonus-proficiencies": ["skill-arcana", "skill-history", "skill-nature"],
        "class:bard:6:feature:additional-magical-secrets": ["fireball", "sacred-flame"]}),
    # RP22: Wizard 18 under 2014 (Spell Mastery only; Signature Spell is level 20) and the SRD Lore Bard 6 under mixed
    # (RPX1 under another ruleset: Bonus Proficiencies and Additional Magical Secrets). New non-2024 golden cases (--append).
    "wizard18-2014": _sub("wizard", 18, "2014", marks=("classes",), overrides={
        "class:wizard:spellbook": ["shield", "magic-missile", "detect-magic", "web", "haste", "fireball", "counterspell", "fly"],
        "class:wizard:spells-known": ["magic-missile", "web", "haste"],
        "class:wizard:18:spell-mastery-1": ["detect-magic"], "class:wizard:18:spell-mastery-2": ["web"]}),
    "bard6-lore-mixed": _sub("bard", 6, "mixed", sub="lore", marks=("classes",), overrides={
        "class:bard:3:feature:bonus-proficiencies": ["skill-arcana", "skill-history", "skill-nature"],
        "class:bard:6:feature:additional-magical-secrets": ["fireball", "sacred-flame"]}),
    # W8a: a 2014 book subclass with modelled use-limit features (Whispers Bard 14: Words of Terror, Mantle of Whispers,
    # Shadow Lore, Psychic Blades on Bardic Inspiration); non-2024, so part of the golden via --append
    "whispers-bard14-2014": _sub("bard", 14, "2014", sub="whispers-xge", marks=("classes",)),
    # W8b: a 2014 book subclass with modelled use-limit features (Circle of the Stars Druid 10 under mixed: Star Map, Cosmic
    # Omen, the Starry Form sentence on Wild Shape); non-2024, so part of the golden via --append
    "stars-druid10-mixed": _sub("druid", 10, "mixed", sub="stars-tce", marks=("classes",)),
    # W8c: Oath of the Watchers Paladin 20 under 2014 (Aura of the Sentinel, Vigilant Rebuke, Mortal Bulwark, the Abjure the
    # Extraplanar and Watcher's Will sentences on Channel Divinity); non-2024, so part of the golden via --append
    "watchers-paladin20-2014": _sub("paladin", 20, "2014", sub="watchers-tce", marks=("classes",)),
    # W8d: a Celestial Warlock 14 under mixed (Healing Light pool of d6s, Radiant Soul, Celestial Resilience, Searing
    # Vengeance); non-2024, so part of the golden via --append
    "celestial-warlock14-mixed": _sub("warlock", 14, "mixed", sub="celestial-xge", marks=("classes",)),
    "psi-warrior11": _sub("fighter", 11, "mixed", sub="psi-warrior-tce", marks=("classes",)),
    "totem-bear6": _sub("barbarian", 6, "mixed", sub="totem-warrior-phb", marks=("classes",), overrides={
        "class:barbarian:3:feature:totem-warrior-phb-3-totem-spirit": ["totem-warrior-phb-3-totem-spirit--bear"],
        "class:barbarian:6:feature:totem-warrior-phb-6-aspect-of-the-beast": [
            "totem-warrior-phb-6-aspect-of-the-beast--bear"]}),
    # G1: 2014 Totem Warrior 14 with the Elk Totemic Attunement (the only option whose text gives a DC) and the Hunter
    # Ranger 15 with a pick on each of the four cards; non-2014-only golden cases via --append
    "totem-elk14": _sub("barbarian", 14, "mixed", sub="totem-warrior-phb", marks=("classes",), once=True, overrides={
        "class:barbarian:3:feature:totem-warrior-phb-3-totem-spirit": ["totem-warrior-phb-3-totem-spirit--elk"],
        "class:barbarian:6:feature:totem-warrior-phb-6-aspect-of-the-beast": [
            "totem-warrior-phb-6-aspect-of-the-beast--tiger"],
        "class:barbarian:14:feature:totem-warrior-phb-14-totemic-attunement": [
            "totem-warrior-phb-14-totemic-attunement--elk"]}),
    "hunter15-2014": _sub("ranger", 15, "2014", sub="hunter", marks=("classes",), overrides={
        "class:ranger:3:feature:hunters-prey": ["hunters-prey-horde-breaker"],
        "class:ranger:7:feature:defensive-tactics": ["defensive-tactics-multiattack-defense"],
        "class:ranger:11:feature:multiattack": ["multiattack-whirlwind-attack"],
        "class:ranger:15:feature:superior-hunters-defense": ["superior-hunters-defense-uncanny-dodge"]}),
    # G2: Sorcerer 17 under 2014 with a pick on each Metamagic card, including the two TCE options (Seeking, Transmuted)
    # and Twinned (cost "spell level"); non-2024, so part of the golden via --append
    "sorcerer17-metamagic-2014": _sub("sorcerer", 17, "2014", marks=("classes",), once=True, overrides={
        "class:sorcerer:3:feature:metamagic-1": ["metamagic-twinned-spell", "opt-seeking-spell-tce"],
        "class:sorcerer:10:feature:metamagic-2": ["metamagic-heightened-spell"],
        "class:sorcerer:17:feature:metamagic-3": ["opt-transmuted-spell-tce"]}),
    # G4: Way of the Four Elements Monk 17 with four disciplines (ki costs on the Ki entry), Rune Knight Fighter 15 with five
    # runes (one resource each, 2 uses from Master of Runes, Rune Magic DC on Fire / Stone), the Genie Warlock 14
    # (Limited Wish, recharge other) and the War Magic Wizard 6 (Power Surge); non-2024, so part of the golden via --append
    "four-elements17-2014": _sub("monk", 17, "2014", sub="four-elements-phb", marks=("classes",), once=True, overrides={
        "class:monk:3:feature:four-elements-phb-3-way-of-the-four-elements": [
            "opt-fist-of-four-thunders-phb", "opt-unbroken-air-phb", "opt-fangs-of-the-fire-snake-phb",
            "opt-breath-of-winter-phb"]}),
    "rune-knight15-2014": _sub("fighter", 15, "2014", sub="rune-knight-tce", marks=("classes",), once=True, overrides={
        "class:fighter:3:feature:rune-knight-tce-3-rune-knight": [
            "opt-fire-rune-tce", "opt-stone-rune-tce", "opt-frost-rune-tce", "opt-hill-rune-tce", "opt-storm-rune-tce"]}),
    "genie-warlock14-2014": _sub("warlock", 14, "2014", sub="genie-tce", marks=("classes",), once=True),
    "war-wizard6-2014": _sub("wizard", 6, "2014", sub="war-xge", marks=("classes",), once=True),
    # G3: Cleric 6 (Life) + Paladin 3 (Devotion) under 2014: one merged Channel Divinity (PHB 164) whose note keeps both
    # classes' options; non-2024, so part of the golden via --append
    "cleric6-paladin3-2014": {**_sub("cleric", 6, "2014", marks=("classes",)),
                              "classes": [("cleric", 6, "life"), ("paladin", 3, "devotion")]},
    "cleric1-thaumaturge-2024": _sub("cleric", 1, "2024", marks=("classes", "official"), overrides={
        "class:cleric:1:divine-order": ["xphb-cleric-1-thaumaturge"]}),
    # F3b: the C6b..C9b / R9 stages, 2024 origin (Human, Soldier) so the origin language card is present
    "rogue6-2024": _sub("rogue", 6, "2024", marks=("classes", "official"), origin=_XPHB_ORIGIN, overrides={
        "class:rogue:1:expertise-choice:xphb-rogue-1-expertise": ["skill-stealth", "skill-sleight-of-hand"],
        "class:rogue:6:expertise-choice:xphb-rogue-6-expertise": ["skill-perception", "skill-acrobatics"],
        "class:rogue:1:prof-choice-0": ["skill-stealth", "skill-sleight-of-hand", "skill-perception", "skill-acrobatics"]}),
    "sorcerer17-2024": _sub("sorcerer", 17, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN),
    "cleric7-2024": _sub("cleric", 7, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:cleric:7:feature:xphb-cleric-7-blessed-strikes": ["opt-divine-strike-xphb"]}),
    "wizard20-2024": _sub("wizard", 20, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:wizard:spellbook": ["fireball-xphb", "counterspell-xphb", "fly-xphb", "haste-xphb", "scorching-ray-xphb"],
        "class:wizard:spells-known": ["burning-hands-xphb", "scorching-ray-xphb", "fireball-xphb"],
        "class:wizard:20:signature-spells": ["fireball-xphb", "counterspell-xphb"]}),
    "ranger9-2024": _sub("ranger", 9, "2024", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN),
    "barbarian3-2024": _sub("barbarian", 3, "2024", marks=("classes", "official"), origin=_XPHB_ORIGIN),
    "fighter4-2024": _sub("fighter", 4, "2024", marks=("classes", "official"), origin=_XPHB_ORIGIN),
    # RPF: a Magic Initiate origin feat whose dependent spell cards (stored by cid prefix, see _store) are filled
    "magic-initiate-2024": _sub("fighter", 1, "2024", marks=("classes", "official", "spells"), origin=("human-xphb", "acolyte-xphb")),
    # RP22: the RP10..RP20 subclass stages under 2024 (Human / Soldier origin)
    "evoker5-2024": _sub("wizard", 5, "2024", sub="evoker-xphb", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:wizard:3:feature:evoker-xphb-3-evocation-savant": ["magic-missile-xphb", "thunderwave-xphb", "scorching-ray-xphb"]}),
    "land-druid10-2024": _sub("druid", 10, "2024", sub="land-xphb", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:druid:3:feature:land-xphb-3-circle-of-the-land-spells": ["land-xphb-3-circle-of-the-land-spells--polar"]}),
    "cleric7-light-2024": _sub("cleric", 7, "2024", sub="light-xphb", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN),
    "warlock7-goo-2024": _sub("warlock", 7, "2024", sub="great-old-one-xphb", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN, overrides={
        "class:warlock:spells-cantrips": ["eldritch-blast-xphb", "minor-illusion-xphb", "mage-hand-xphb"],
        _WL_INV_2024: ["opt-pact-of-the-tome-xphb", "opt-agonizing-blast-xphb", "opt-devils-sight-xphb"],
        "class:warlock:invocation:opt-agonizing-blast-xphb:cantrip": ["eldritch-blast-xphb"]}),
    "battle-master3-2024": _sub("fighter", 3, "2024", sub="battle-master-xphb", marks=("classes", "official"), origin=_XPHB_ORIGIN,
                                overrides={"class:fighter:3:feature:battle-master-xphb-3-battle-master": [
                                    "opt-ambush-xphb", "opt-bait-and-switch-xphb", "opt-commanders-strike-xphb"]}),
    "fey-wanderer3-2024": _sub("ranger", 3, "2024", sub="fey-wanderer-xphb", marks=("classes", "official", "spells"), origin=_XPHB_ORIGIN),
    # W5b: the SRD Dragonborn (2014): Breath Weapon with the picked Draconic Ancestry (non-2024, so part of the golden via --append)
    "dragonborn6-2014": _sub("fighter", 6, "2014", marks=("classes",), origin=("dragonborn", "acolyte")),
    # W5a: species trait resources (2024 only, so not part of the golden): Breath Weapon + Draconic Flight, Adrenaline Rush
    # + Relentless Endurance, Giant Ancestry + Large Form
    "dragonborn11-2024": _sub("fighter", 11, "2024", marks=("classes", "official"), origin=("dragonborn-xphb", "soldier-xphb")),
    "orc5-2024": _sub("barbarian", 5, "2024", marks=("classes", "official"), origin=("orc-xphb", "soldier-xphb")),
    "goliath5-2024": _sub("fighter", 5, "2024", marks=("classes", "official"), origin=("goliath-xphb", "soldier-xphb")),
    # FE12: feat-holding drafts (ASI feat picks as overrides; every feat card is filled with its first option)
    "feats-mixed-fighter14": _sub("fighter", 14, "mixed", marks=("classes", "official"), feats=True, overrides={
        "class:fighter:4:asi": ["feat:alert-phb"], "class:fighter:6:asi": ["feat:tough-phb"],
        "class:fighter:8:asi": ["feat:great-weapon-master-phb"], "class:fighter:12:asi": ["feat:lucky-phb"],
        "class:fighter:14:asi": ["feat:observant-phb"]},
        equip=[{"itemId": "greataxe", "qty": 1, "equipped": True}, {"itemId": "longbow", "qty": 1, "equipped": True}]),
    "feats-2014-rogue16": _sub("rogue", 16, "2014", marks=("classes", "official"), feats=True, overrides={
        "class:rogue:4:asi": ["feat:keen-mind-phb"], "class:rogue:8:asi": ["feat:weapon-master-phb"],
        "class:rogue:10:asi": ["feat:resilient-phb"], "class:rogue:12:asi": ["feat:elemental-adept-phb"],
        "class:rogue:16:asi": ["feat:elemental-adept-phb"]},
        equip=[{"itemId": "rapier", "qty": 1, "equipped": True}]),
    "feats-mixed-wizard8": _sub("wizard", 8, "mixed", marks=("classes", "official", "spells"), feats=True, overrides={
        "class:wizard:4:asi": ["feat:martial-adept-phb"], "class:wizard:8:asi": ["feat:eldritch-adept-tce"]}),
    "feats-2024-fighter19": _sub("fighter", 19, "2024", marks=("classes", "official"), feats=True,
                                 origin=("human-xphb", "criminal-xphb"), overrides={
        "class:fighter:4:asi": ["feat:tough-xphb"], "class:fighter:6:asi": ["feat:great-weapon-master-xphb"],
        "class:fighter:8:asi": ["feat:lucky-xphb"], "class:fighter:12:asi": ["feat:observant-xphb"],
        "class:fighter:14:asi": ["feat:keen-mind-xphb"], "class:fighter:16:asi": ["feat:weapon-master-xphb"],
        "class:fighter:19:asi": ["feat:boon-of-fortitude-xphb"]},
        equip=[{"itemId": "greataxe", "qty": 1, "equipped": True}]),
}


def base_draft(spec: dict) -> dict:
    classes = []
    for index, level, sub in spec["classes"]:
        c = {"classId": index, "level": level, "choices": {}}
        if sub:
            c["subclassId"] = sub
        classes.append(c)
    return {"name": "Кухненска мивка", "ruleset": spec["ruleset"], "sources": [],
            "abilities": {"method": "manual", "base": dict(_BASE)},
            "species": {"id": spec.get("origin", ("human", "acolyte"))[0], "choices": {}},
            "background": {"id": spec.get("origin", ("human", "acolyte"))[1], "choices": {}},
            "equipment": {"choices": {}, "added": copy.deepcopy(spec["equip"]), "skipped": False},
            "classes": classes}


def _store(draft: dict, source: dict, cid: str = "") -> dict:
    """Mirror of the frontend routing (ClassPage / SpeciesPage / BackgroundPage filters + DraftContext
    storedSelection): a feat card is stored by its cid prefix, `class:<id>:` in that class's choices,
    `species:` in the species choices, every other one in the background choices."""
    kind = source["kind"]
    if kind == "feat":
        if cid.startswith("class:"):
            kind, source = "class", {"id": cid.split(":")[1]}
        elif cid.startswith("species:"):
            kind = "species"
        else:
            kind = "background"
    if kind == "class":
        return next(c for c in draft["classes"] if c["classId"] == source["id"])["choices"]
    if kind == "background":
        return draft["background"]["choices"]
    if kind == "species":
        return draft["species"]["choices"]
    return draft["equipment"]["choices"]


def fill(draft: dict, catalog, overrides: dict, resolve) -> dict:
    """Pick every pending choice: the override ids first, then the first enabled options."""
    for _ in range(10):
        res = resolve(draft, catalog)
        todo = [c for c in res["choices"] if c["status"] == "pending"]  # F3a: "unavailable" cards cannot be filled
        if not todo:
            return draft
        # spell cards first, then re-resolve: invocation prerequisites (Agonizing Blast needs
        # eldritch blast) read the stored spell picks
        spell_cards = [c for c in todo if ":spells-" in c["id"] and c["options"]]
        # F3b: then proficiency cards, so an Expertise card (options gated to proficient skills) sees them
        prof_cards = [c for c in todo if ("prof-choice" in c["id"] or "proficiency-choice" in c["id"]) and c["options"]]
        for c in spell_cards or prof_cards or todo:
            ids = [o["id"] for o in c["options"] if not o.get("disabled")]
            picked = [i for i in overrides.get(c["id"], []) if i in ids]
            picked += [i for i in ids if i not in picked]
            _store(draft, c["source"], c["id"])[c["id"]] = picked[:c["count"]]
    raise AssertionError("choices did not settle")


def skip_reason(spec: dict) -> str | None:
    """Why the draft cannot run here (missing 5etools data), else None."""
    from catalog import official_source as o
    checks = {"classes": o.has_official_classes, "official": o.has_official, "spells": o.has_official_spells}
    missing = [m for m in spec["marks"] if not checks[m]()]
    return f"5etools data missing: {', '.join(missing)}" if missing else None


def build(sid: str, catalog, resolve) -> dict:
    spec = KITCHEN_SINK[sid]
    return fill(base_draft(spec), catalog, spec["overrides"], resolve)
