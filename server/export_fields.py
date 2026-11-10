"""The single field list and the text blocks (Bulgarian or English, words from export_labels) shared by the YAML,
Markdown and PDF exporters, so a field added to resolve()'s `sheet`/`derived`
shows up in all three (tests/test_export_fields.py fails when a key is in
neither list below).

* ``SHEET_FIELDS`` / ``DERIVED_FIELDS``: (key, default) in YAML order. The YAML
  document is these keys flattened to the top level; the default stands in
  when a hand-built resolution lacks the key.
* ``EXCLUDED``: ("sheet"|"derived", key) -> why the key is deliberately not
  exported. Empty today.
* ``extra_blocks``: the sections Markdown and PDF print for the fields their
  older, fixed layout does not cover. A block is (kind, text) with kind in
  "h2" / "h3" / "body" / "bullet"; each renderer only maps kinds to its own
  formatting.
"""
from __future__ import annotations

from catalog.reference_data import SKILL_NAMES, proficiency_label
from export_labels import DEFAULT_LANG, LABELS, label, weight, weight_pair, word

SHEET_FIELDS: list[tuple[str, object]] = [
    ("name", ""), ("level", 0), ("classes", []), ("background", None), ("species", None),
    ("details", None), ("abilities", {}),
]
# derived keys sit between the sheet's identity block and its tail lists in the
# YAML (historic order); the tail of the sheet follows.
DERIVED_FIELDS: list[tuple[str, object]] = [
    ("abilityModifiers", {}), ("proficiencyBonus", None), ("hitPointMax", None), ("hitDice", None),
    ("armorClass", None), ("speed", None), ("speeds", {}), ("savingThrows", {}), ("skills", {}),
    ("initiative", None), ("passivePerception", None), ("passiveInsight", None), ("passiveInvestigation", None),
    ("spellSlots", {}), ("warlockSpellSlots", {}), ("slotGrantingClasses", []),
    ("attacks", []), ("attacksPerAction", 1), ("classResources", []), ("featResources", []), ("speciesResources", []), ("carryingCapacity", None), ("stealthDisadvantage", False),
]
SHEET_TAIL_FIELDS: list[tuple[str, object]] = [
    ("proficiencies", {}), ("expertiseSkills", []), ("senses", {}), ("damageModifiers", {}),
    ("conditionImmunities", []), ("startingGold", 0), ("equipment", {}), ("spells", []),
    ("innateSpells", []), ("features", []), ("feats", []), ("grantedFeats", []), ("featOptions", []),
    ("weaponMasteries", []),
]
EXCLUDED: dict[tuple[str, str], str] = {}


def yaml_document(resolution: dict) -> dict:
    sheet, derived = resolution["sheet"], resolution["derived"]
    doc: dict = {}
    for key, default in SHEET_FIELDS:
        doc[key] = sheet.get(key, default)
    for key, default in DERIVED_FIELDS:
        doc[key] = derived.get(key, default)
    for key, default in SHEET_TAIL_FIELDS:
        doc[key] = sheet.get(key, default)
    return doc


# Detail sections of the character sheet: (section key, field keys); the words are export_labels' detailSections / detailFields.
DETAIL_SECTIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("identity", ("alignment", "faith", "lifestyle")),
    ("physical", ("age", "height", "weight", "eyes", "skin", "hair")),
    ("personality", ("personalityTraits", "ideals", "bonds", "flaws")),
    ("notes", ("backstory", "organizations", "allies", "enemies", "notes")),
)
_DAMAGE_SECTIONS = (("resistances", "dmgResistances"), ("immunities", "dmgImmunities"), ("vulnerabilities", "dmgVulnerabilities"))


def _title(slug: str) -> str:
    return slug.replace("-", " ").capitalize()


def expertise_label(entry: str) -> str:
    return SKILL_NAMES.get(entry) or proficiency_label(entry)


# X2: `turn` / `combat` / `rage` are non-rest limits ("once per turn" ...), `other` points at the condition in the note.
_RECHARGE_WORDS = LABELS["bg"]["recharge"]  # the Bulgarian words (tests compare them with the frontend copy)

# C6d / C7c: Wizard 18 / 20 and Pact of the Tome spell picks printed under the class's spells: the key on the
# sheet.spells entry, which is also the export_labels key of the line's label.
SPELL_PICK_KEYS = ("spellMastery", "signatureSpells", "pactOfTheTome")  # C7c: Warlock Pact of the Tome


def resource_detail_parts(details: dict | None, lang: str = DEFAULT_LANG) -> list[str]:
    """Short fragments for a class resource's `details` (only what is meaningful), in `lang`."""
    d = details or {}
    parts: list[str] = []
    res = d.get("resistances")
    if res:
        if len(res) == len(LABELS[lang]["damage"]) - 1 and "psychic" not in res:
            parts.append(label(lang, "resAll"))
        else:
            parts.append(label(lang, "resSome", types=", ".join(word(lang, "damage", t) for t in res)))
    if d.get("shortRestRegains"):
        parts.append(label(lang, "shortRestRegains", n=d["shortRestRegains"]))
    if d.get("spellSlotRegainsUse"):
        parts.append(label(lang, "spellSlotRegainsUse"))
    if d.get("bonusActionRegainsOne"):
        parts.append(label(lang, "bonusActionRegainsOne"))
    if d.get("onShortRest"):
        parts.append(label(lang, "onShortRest"))
    if d.get("maxSlotLevel") is not None:
        parts.append(label(lang, "maxSlotLevel", n=d["maxSlotLevel"]))
    costs = d.get("slotCosts")
    if costs:
        parts.append(", ".join(label(lang, "slotCost", lvl=lvl, n=costs[lvl]) for lvl in sorted(costs, key=int)))
    if d.get("knownForms") is not None:
        parts.append(label(lang, "knownForms", n=d["knownForms"]))
    if d.get("fly") is True:
        parts.append(word(lang, "modes", "fly"))
    if d.get("swim") is True:
        parts.append(word(lang, "modes", "swim"))
    meta = d.get("metamagic")
    if meta:
        parts.append(label(lang, "metamagic", items=", ".join(f"{m['name']} ({m['cost']})" for m in meta)))
    options = d.get("perRageOptions")
    if options:
        parts.append(label(lang, "perRageOptions", items="; ".join(f"{o['name']}: {o['effect']}" for o in options)))
    if isinstance(d.get("damageTypes"), str) and d["damageTypes"]:  # VF1.7: Divine Strike / Primal Strike ("Cold, Fire, Lightning, or Thunder")
        parts.append(label(lang, "damageTypesLine", types=d["damageTypes"]))
    return parts


def resource_line(r: dict, lang: str = DEFAULT_LANG) -> str:
    """One class resource as a bullet: `Rage: 3, дълга почивка (Long Rest), щета +2` (EN: `Rage: 3 (long rest), damage +2`;
    the Bulgarian recharge word carries its own English term in brackets, so it is not wrapped in parentheses)."""
    parts = []
    if r.get("unlimited"):
        parts.append(label(lang, "unlimited"))
    elif r.get("uses") is not None:
        parts.append(str(r["uses"]))
    for key, prefix in (("die", ""), ("dice", ""), ("pool", LABELS[lang]["pool"]), ("bonus", LABELS[lang]["bonus"]),
                        ("dc", LABELS[lang]["dc"])):
        if r.get(key) is not None:
            value = f"{r[key]:+d}" if key == "bonus" else r[key]
            parts.append(f"{prefix}{value}")
    core = ", ".join(parts)
    recharge = word(lang, "recharge", r.get("recharge"), "") if r.get("recharge") else ""
    if recharge:
        if "(" in recharge:  # the Bulgarian word carries its English term in brackets: no second pair of parentheses
            core = f"{core}, {recharge}" if core else recharge
        else:
            core = f"{core} ({recharge})" if core else f"({recharge})"
    note = (r.get("details") or {}).get("note")
    if note:
        core = f"{core}, {note}" if core else note
    damage = (r.get("details") or {}).get("damageBonus")
    if damage is not None:
        core += ", " + label(lang, "damageBonus", n=damage)
    heal = (r.get("details") or {}).get("heal")
    if heal:
        core += ", " + label(lang, "healing", v=heal)
    for fragment in resource_detail_parts(r.get("details"), lang):
        core = f"{core}, {fragment}" if core else fragment
    max_cr = (r.get("details") or {}).get("maxCr")
    if max_cr:
        core = f"{core}, {label(lang, 'maxCr', v=max_cr)}" if core else label(lang, "maxCr", v=max_cr)
    return f"{r['name']}: {core}" if core else r["name"]


def pack_contents_suffix(entry: dict, lang: str = DEFAULT_LANG) -> str:
    """RP8: " (съдържа: Backpack, Oil x2, ...)" for a 2024 equipment-pack entry, else "".
    Markdown and PDF both print exactly this text after the entry."""
    contents = entry.get("contents") or []
    if not contents:
        return ""
    parts = [c["name"] + (f" x{c['qty']}" if c.get("qty", 1) != 1 else "") for c in contents]
    return " (" + label(lang, "packContents", items=", ".join(parts)) + ")"


def worn_wielded_line(sheet: dict, lang: str = DEFAULT_LANG) -> str | None:
    """G2: one plain line for the Equipment block, only when the draft sets worn/wielded.
    Markdown and PDF both print exactly this text."""
    eq = sheet.get("equipment") or {}
    worn, wielded = eq.get("worn"), eq.get("wielded")
    if not worn and not wielded:
        return None
    slots = eq.get("slots") or {}
    names = {o["itemId"]: o["name"] for k in ("armor", "shield", "hands") for o in slots.get(k, [])}
    parts = []
    if worn:
        armor = names.get(worn.get("armor"), worn.get("armor")) if worn.get("armor") else label(lang, "wornNoArmor")
        parts.append(label(lang, "wornArmor", name=armor) + (label(lang, "wornShield") if worn.get("shield") else ""))
    if wielded:
        def hand(i):
            return names.get(i, i) if i else label(lang, "handEmpty")
        parts.append(label(lang, "wielded", main=hand(wielded.get("main")), off=hand(wielded.get("off"))))
    return label(lang, "worn", parts="; ".join(parts))


def extra_blocks(resolution: dict, lang: str = DEFAULT_LANG) -> list[tuple[str, str]]:
    """Sections for the fields the fixed Markdown/PDF layout lacks."""
    sheet, derived = resolution["sheet"], resolution["derived"]
    blocks: list[tuple[str, str]] = []
    feet = lambda n: label(lang, "feet", n=n)  # noqa: E731

    speeds = derived.get("speeds") or {}
    if len(speeds) > 1 or (speeds and "walk" not in speeds):
        blocks.append(("h2", label(lang, "secMovement")))
        blocks.append(("body", ", ".join(f"{word(lang, 'modes', m)} {feet(v)}" for m, v in speeds.items())))

    size = (sheet.get("species") or {}).get("size")
    if size:
        blocks.append(("h2", label(lang, "secSize")))
        blocks.append(("body", str(size)))

    senses = sheet.get("senses") or {}
    if senses:
        blocks.append(("h2", label(lang, "secSenses")))
        blocks.append(("body", ", ".join(f"{word(lang, 'senses', k)} {feet(v)}" for k, v in senses.items())))

    expertise = sheet.get("expertiseSkills") or []
    if expertise:
        blocks.append(("h2", label(lang, "secExpertise")))
        blocks.append(("body", ", ".join(expertise_label(e) for e in expertise)))

    damage = sheet.get("damageModifiers") or {}
    conditions = sheet.get("conditionImmunities") or []
    if any(damage.get(k) for k, _ in _DAMAGE_SECTIONS) or conditions:
        blocks.append(("h2", label(lang, "secResistances")))
        for key, label_key in _DAMAGE_SECTIONS:
            if damage.get(key):
                blocks.append(("bullet", f"{label(lang, label_key)}: " + ", ".join(_title(d) for d in damage[key])))
        if conditions:
            blocks.append(("bullet", f"{label(lang, 'conditionImmunities')}: " + ", ".join(_title(c) for c in conditions)))

    attacks = derived.get("attacks") or []
    per_action = derived.get("attacksPerAction") or 1
    if attacks or per_action > 1:
        blocks.append(("h2", label(lang, "secAttacks")))
        blocks.append(("bullet", label(lang, "attacksPerAction", n=per_action)))
        for a in attacks:
            line = f"{a['name']}: {a['attackBonus']:+d}"
            if a.get("damage"):
                line += f", {a['damage']} {a['damageType']}"
                if a.get("versatileDamage"):
                    line += f" ({label(lang, 'attackVersatile', dice=a['versatileDamage'])})"
            if a.get("duelingDamage"):
                line += ", " + label(lang, "attackDueling", dice=a["duelingDamage"])
            if a.get("offhandDamage"):
                line += ", " + label(lang, "attackOffhand", dice=a["offhandDamage"])
            if a.get("range"):
                line += ", " + label(lang, "attackRange", range=a["range"])
            if a.get("notes"):
                line += "; " + ", ".join(a["notes"])
            if a.get("mastery"):
                line += ", " + label(lang, "attackMastery", mastery=a["mastery"])
            blocks.append(("bullet", line))

    masteries = sheet.get("weaponMasteries") or []
    if masteries:
        blocks.append(("h2", label(lang, "secMasteries")))
        for m in masteries:
            blocks.append(("bullet", f"{m['name']}: {m['mastery']}"))

    resources = derived.get("classResources") or []
    if resources:
        blocks.append(("h2", label(lang, "secClassResources")))
        for r in resources:
            blocks.append(("bullet", resource_line(r, lang)))

    feat_resources = derived.get("featResources") or []  # FE3: same line as a class resource
    if feat_resources:
        blocks.append(("h2", label(lang, "secFeatResources")))
        for r in feat_resources:
            blocks.append(("bullet", resource_line(r, lang)))

    species_resources = derived.get("speciesResources") or []  # W5a: same line as a class resource
    if species_resources:
        blocks.append(("h2", label(lang, "secSpeciesResources")))
        for r in species_resources:
            blocks.append(("bullet", resource_line(r, lang)))

    carrying = derived.get("carryingCapacity")
    if carrying:
        blocks.append(("h2", label(lang, "secCarrying")))
        over = label(lang, "overCapacity") if carrying.get("overCapacity") else ""
        lift = label(lang, "pushDragLift", n=weight(carrying["pushDragLift"], lang)) if carrying.get("pushDragLift") else ""
        blocks.append(("body", f"{weight_pair(carrying['carried'], carrying['capacity'], lang)}{over}{lift}"))
    if derived.get("stealthDisadvantage"):
        blocks.append(("h2", label(lang, "secArmor")))
        blocks.append(("body", label(lang, "stealthDisadvantage")))

    gold = sheet.get("startingGold") or 0
    narrative = (sheet.get("equipment") or {}).get("narrativeItems") or []
    if gold or narrative:
        blocks.append(("h2", label(lang, "secStartingGold")))
        if gold:
            blocks.append(("bullet", label(lang, "startingGold", n=gold)))
        for item in narrative:
            blocks.append(("bullet", str(item)))

    always = [(e["classId"], e["alwaysPrepared"]) for e in sheet.get("spells") or [] if e.get("alwaysPrepared")]
    if always:
        names = {c["id"]: c["name"] for c in sheet.get("classes") or []}
        blocks.append(("h2", label(lang, "alwaysPrepared")))
        for class_id, spells in always:
            blocks.append(("h3", names.get(class_id, class_id)))
            for s in spells:
                blocks.append(("bullet", f"{s['name']} ({label(lang, 'spellLevel', lvl=s['level'])})"))

    # Feats have their own section below.
    features = [f for f in sheet.get("features") or [] if f["source"]["kind"] != "feat"]
    if features:
        blocks.append(("h2", label(lang, "secFeatures")))
        current = None
        for f in features:
            source_label = f["source"]["label"]
            if source_label != current:
                current = source_label
                blocks.append(("h3", source_label))
            line = f["name"]
            if f.get("level"):
                line += f" ({label(lang, 'featureLevel', level=f['level'])})"
            if f.get("choice"):
                line += ": " + ", ".join(f["choice"])
            blocks.append(("bullet", line))

    feats = sheet.get("feats") or []
    if feats:
        blocks.append(("h2", label(lang, "secFeats")))
        for f in feats:
            line = f["name"]
            if f.get("level"):
                line += f" ({label(lang, 'featureLevel', level=f['level'])})"
            if f.get("choice"):
                line += ": " + ", ".join(f["choice"])
            if f.get("notes"):  # FE3
                line += " — " + "; ".join(f["notes"])
            blocks.append(("bullet", line))
    return blocks
