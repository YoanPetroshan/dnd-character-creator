"""The single field list and Bulgarian text blocks shared by the YAML,
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
    ("attacks", []), ("attacksPerAction", 1), ("classResources", []), ("carryingCapacity", None), ("stealthDisadvantage", False),
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


_MODE_NAMES = {"walk": "ходене", "fly": "летене", "swim": "плуване", "climb": "катерене", "burrow": "ровене"}
_SENSE_NAMES = {
    "darkvision": "тъмно зрение", "blindsight": "сляпо зрение",
    "tremorsense": "усещане за вибрации", "truesight": "истинско зрение", "devilsSight": "дяволско зрение",
}
_DAMAGE_SECTIONS = (("resistances", "Устойчивост"), ("immunities", "Имунитет"), ("vulnerabilities", "Уязвимост"))


def _title(slug: str) -> str:
    return slug.replace("-", " ").capitalize()


def expertise_label(entry: str) -> str:
    return SKILL_NAMES.get(entry) or proficiency_label(entry)


_RECHARGE_WORDS = {"long": "дълга почивка", "short": "кратка почивка", "short-or-long": "кратка или дълга почивка"}


_DAMAGE_NAMES_BG = {
    "acid": "киселинни", "bludgeoning": "дробящи", "cold": "студени", "fire": "огнени", "force": "силови",
    "lightning": "мълниеносни", "necrotic": "некротични", "piercing": "пробождащи", "poison": "отровни",
    "psychic": "психични", "radiant": "лъчисти", "slashing": "режещи", "thunder": "гръмотевични",
}


def resource_detail_parts(details: dict | None) -> list[str]:
    """Short Bulgarian fragments for a class resource's `details` (only what is meaningful)."""
    d = details or {}
    parts: list[str] = []
    res = d.get("resistances")
    if res:
        if len(res) == len(_DAMAGE_NAMES_BG) - 1 and "psychic" not in res:
            parts.append("съпротива: всички видове щета освен психична")
        else:
            parts.append("съпротива: " + ", ".join(_DAMAGE_NAMES_BG.get(t, t) for t in res))
    if d.get("shortRestRegains"):
        n = d["shortRestRegains"]
        parts.append(f"{n} използване се възстановява при кратка почивка" if n == 1
                     else f"{n} използвания се възстановяват при кратка почивка")
    if d.get("spellSlotRegainsUse"):
        parts.append("използване се възстановява срещу слот за заклинание")
    if d.get("bonusActionRegainsOne"):
        parts.append("бонус действие: връща 1 зар")
    if d.get("onShortRest"):
        parts.append("при кратка почивка")
    if d.get("maxSlotLevel") is not None:
        parts.append(f"слотове до ниво {d['maxSlotLevel']}")
    costs = d.get("slotCosts")
    if costs:
        parts.append(", ".join(f"слот ниво {lvl} за {costs[lvl]} т." for lvl in sorted(costs, key=int)))
    if d.get("knownForms") is not None:
        parts.append(f"известни форми: {d['knownForms']}")
    if d.get("fly") is True:
        parts.append("летене")
    if d.get("swim") is True:
        parts.append("плуване")
    return parts


def resource_line(r: dict) -> str:
    """One class resource as a bullet: `Rage: 3 (дълга почивка), щета +2`."""
    parts = []
    if r.get("unlimited"):
        parts.append("без ограничение")
    elif r.get("uses") is not None:
        parts.append(str(r["uses"]))
    for key, label in (("die", ""), ("dice", ""), ("pool", "пул "), ("bonus", "бонус "), ("dc", "ТС ")):
        if r.get(key) is not None:
            value = f"{r[key]:+d}" if key == "bonus" else r[key]
            parts.append(f"{label}{value}")
    core = ", ".join(parts)
    word = _RECHARGE_WORDS.get(r.get("recharge"))
    if word:
        core = f"{core} ({word})" if core else f"({word})"
    note = (r.get("details") or {}).get("note")
    if note:
        core = f"{core}, {note}" if core else note
    damage = (r.get("details") or {}).get("damageBonus")
    if damage is not None:
        core += f", щета +{damage}"
    heal = (r.get("details") or {}).get("heal")
    if heal:
        core += f", лекуване {heal}"
    for fragment in resource_detail_parts(r.get("details")):
        core = f"{core}, {fragment}" if core else fragment
    max_cr = (r.get("details") or {}).get("maxCr")
    if max_cr:
        core = f"{core}, макс. CR {max_cr}" if core else f"макс. CR {max_cr}"
    return f"{r['name']}: {core}" if core else r["name"]


def extra_blocks(resolution: dict) -> list[tuple[str, str]]:
    """Sections for the fields the fixed Markdown/PDF layout lacks."""
    sheet, derived = resolution["sheet"], resolution["derived"]
    blocks: list[tuple[str, str]] = []

    speeds = derived.get("speeds") or {}
    if len(speeds) > 1 or (speeds and "walk" not in speeds):
        blocks.append(("h2", "Движение"))
        blocks.append(("body", ", ".join(f"{_MODE_NAMES.get(m, m)} {v} фута" for m, v in speeds.items())))

    senses = sheet.get("senses") or {}
    if senses:
        blocks.append(("h2", "Сетива"))
        blocks.append(("body", ", ".join(f"{_SENSE_NAMES.get(k, k)} {v} фута" for k, v in senses.items())))

    expertise = sheet.get("expertiseSkills") or []
    if expertise:
        blocks.append(("h2", "Експертиза"))
        blocks.append(("body", ", ".join(expertise_label(e) for e in expertise)))

    damage = sheet.get("damageModifiers") or {}
    conditions = sheet.get("conditionImmunities") or []
    if any(damage.get(k) for k, _ in _DAMAGE_SECTIONS) or conditions:
        blocks.append(("h2", "Съпротиви и имунитети"))
        for key, label in _DAMAGE_SECTIONS:
            if damage.get(key):
                blocks.append(("bullet", f"{label} към щета: " + ", ".join(_title(d) for d in damage[key])))
        if conditions:
            blocks.append(("bullet", "Имунитет към състояния: " + ", ".join(_title(c) for c in conditions)))

    attacks = derived.get("attacks") or []
    per_action = derived.get("attacksPerAction") or 1
    if attacks or per_action > 1:
        blocks.append(("h2", "Атаки"))
        blocks.append(("bullet", f"Атаки на действие: {per_action}"))
        for a in attacks:
            line = f"{a['name']}: {a['attackBonus']:+d}"
            if a.get("damage"):
                line += f", {a['damage']} {a['damageType']}"
                if a.get("versatileDamage"):
                    line += f" (versatile {a['versatileDamage']})"
            if a.get("duelingDamage"):
                line += f", с Дуел {a['duelingDamage']}"
            if a.get("offhandDamage"):
                line += f", off hand {a['offhandDamage']}"
            if a.get("range"):
                line += f", range {a['range']}"
            if a.get("notes"):
                line += "; " + ", ".join(a["notes"])
            if a.get("mastery"):
                line += f", майсторство {a['mastery']}"
            blocks.append(("bullet", line))

    masteries = sheet.get("weaponMasteries") or []
    if masteries:
        blocks.append(("h2", "Майсторство с оръжия"))
        for m in masteries:
            blocks.append(("bullet", f"{m['name']}: {m['mastery']}"))

    resources = derived.get("classResources") or []
    if resources:
        blocks.append(("h2", "Ресурси на класа"))
        for r in resources:
            blocks.append(("bullet", resource_line(r)))

    carrying = derived.get("carryingCapacity")
    if carrying:
        blocks.append(("h2", "Носимост"))
        over = " (претоварен)" if carrying.get("overCapacity") else ""
        blocks.append(("body", f"{carrying['carried']}/{carrying['capacity']} lb{over}"))
    if derived.get("stealthDisadvantage"):
        blocks.append(("h2", "Броня"))
        blocks.append(("body", "Недостатък при Скритост (носена броня)."))

    gold = sheet.get("startingGold") or 0
    narrative = (sheet.get("equipment") or {}).get("narrativeItems") or []
    if gold or narrative:
        blocks.append(("h2", "Начално злато и други предмети"))
        if gold:
            blocks.append(("bullet", f"Начално злато: {gold} зл."))
        for item in narrative:
            blocks.append(("bullet", str(item)))

    always = [(e["classId"], e["alwaysPrepared"]) for e in sheet.get("spells") or [] if e.get("alwaysPrepared")]
    if always:
        names = {c["id"]: c["name"] for c in sheet.get("classes") or []}
        blocks.append(("h2", "Винаги подготвени заклинания"))
        for class_id, spells in always:
            blocks.append(("h3", names.get(class_id, class_id)))
            for s in spells:
                blocks.append(("bullet", f"{s['name']} (ниво {s['level']})"))

    # Feats have their own section below.
    features = [f for f in sheet.get("features") or [] if f["source"]["kind"] != "feat"]
    if features:
        blocks.append(("h2", "Черти и способности"))
        current = None
        for f in features:
            label = f["source"]["label"]
            if label != current:
                current = label
                blocks.append(("h3", label))
            line = f["name"]
            if f.get("level"):
                line += f" (ниво {f['level']})"
            if f.get("choice"):
                line += ": " + ", ".join(f["choice"])
            blocks.append(("bullet", line))

    feats = sheet.get("feats") or []
    if feats:
        blocks.append(("h2", "Таланти"))
        for f in feats:
            line = f["name"]
            if f.get("level"):
                line += f" (ниво {f['level']})"
            if f.get("choice"):
                line += ": " + ", ".join(f["choice"])
            blocks.append(("bullet", line))
    return blocks
