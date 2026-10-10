"""C6a / C6b-1 / C6b-2 / C6c-1 / C6c-2: 2024 class choice cards that are built from XPHB feature ids (helper for resolve()).

Pure functions over the catalog; resolve() only wires them. Everything here is ruleset "2024"
only: with any other ruleset, or an SRD-only catalog (no XPHB feature records), every function
returns "nothing", so the SRD cards stay.
"""
from __future__ import annotations

from catalog.reference_data import (
    CLASS_LANGUAGES_2024, CLASS_OPTION_CHOICES_2024, EXPERTISE_2024, LANGUAGES_2024_RARE, LANGUAGES_2024_STANDARD, PRIMAL_KNOWLEDGE_2024,
    SKILL_NAMES, SRD_CARDS_REPLACED_2024,
)


def _join(desc) -> str:
    return "\n\n".join(desc) if isinstance(desc, list) else (desc or "")


def expertise_entries(catalog, cls_id: str, ruleset: str) -> list[tuple[str, dict]]:
    """[(feature id, EXPERTISE_2024 entry)] of this class whose XPHB feature exists, by level."""
    if ruleset != "2024":
        return []
    found = [(fid, e) for fid, e in EXPERTISE_2024.items() if e["class"] == cls_id and fid in catalog.features]
    return sorted(found, key=lambda pair: pair[1]["level"])


def expertise_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """One Expertise card per XPHB entry up to the class level.

    cid `class:<cls>:<lvl>:expertise-choice:<xphb feature id>`: the `expertise-choice` marker
    is what the expertise gate, the proficiency scans and `sheet.expertiseSkills` key off, and
    the feature id lets sheet_features attach the pick to its C5 row. `lacksExpertise` is an
    internal key (stripped from the output) read by the Expertise gate."""
    cls_id = rc.get("cls_id")
    if not rc.get("cls") or not cls_id:
        return []
    out = []
    for fid, entry in expertise_entries(catalog, cls_id, ruleset):
        if entry["level"] > rc["level"]:
            continue
        feature = catalog.features[fid]
        skills = entry["skills"] or list(SKILL_NAMES)
        tpl = {
            "id": f"class:{cls_id}:{entry['level']}:expertise-choice:{fid}",
            "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": entry["level"]},
            "label": feature["name"],
            "description": _join(feature.get("desc")),
            "count": entry["count"],
            "options": [{"id": s, "label": SKILL_NAMES[s]} for s in skills],
        }
        if entry["lacks_expertise"]:
            tpl["lacksExpertise"] = True
        out.append(tpl)
    return out


def replaced_srd_features(catalog, cls_id: str, ruleset: str) -> set[str]:
    """SRD feature ids whose card is replaced by a 2024 card (see SRD_CARDS_REPLACED_2024)."""
    if ruleset != "2024" or cls_id not in SRD_CARDS_REPLACED_2024:
        return set()
    if cls_id == "sorcerer":  # C6c-1: only when the XPHB Metamagic card can exist
        ok = METAMAGIC_FEATURE in catalog.features and optional_feature_progression(catalog, "sorcerer", "MM")
        return set(SRD_CARDS_REPLACED_2024[cls_id]) if ok else set()
    if cls_id == "warlock":  # C7a: only when the XPHB invocation card can exist
        return set(SRD_CARDS_REPLACED_2024[cls_id]) if _invocation_ready(catalog) else set()
    if cls_id == "ranger":
        return set(SRD_CARDS_REPLACED_2024[cls_id]) if cls_id in (catalog.class_2024_records or {}) else set()
    return set(SRD_CARDS_REPLACED_2024[cls_id]) if expertise_entries(catalog, cls_id, ruleset) else set()


# ---- C6b-2: class languages ---------------------------------------------------------------

def _language_entries(catalog, cls_id: str, ruleset: str) -> list[tuple[str, dict]]:
    if ruleset != "2024":
        return []
    found = [(fid, e) for fid, e in CLASS_LANGUAGES_2024.items() if e["class"] == cls_id and fid in catalog.features]
    return sorted(found, key=lambda pair: pair[1]["level"])


def fixed_class_languages(catalog, resolved_classes, ruleset: str) -> list[str]:
    """Language ids always known through 2024 class features (Thieves' Cant, Druidic) at the
    classes' current levels. [] outside 2024 or without the XPHB feature records."""
    out: list[str] = []
    for rc in resolved_classes:
        if not rc.get("cls") or not rc.get("cls_id"):
            continue
        for _fid, e in _language_entries(catalog, rc["cls_id"], ruleset):
            if e["level"] <= rc["level"]:
                out += e["fixed"]
    return out


def language_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """One card per class language feature with a pick (Thieves' Cant 1, Deft Explorer 2), up to
    the class level. cid `class:<cls>:<lvl>:languages:<xphb feature id>`; options are the PHB 2024
    Standard + Rare tables (decision E2). "Already known" is applied late by gate_languages."""
    cls_id = rc.get("cls_id")
    if not rc.get("cls") or not cls_id:
        return []
    pool = [{"id": l["index"], "label": l["name"]} for l in LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE]
    out = []
    for fid, e in _language_entries(catalog, cls_id, ruleset):
        if e["choose"] <= 0 or e["level"] > rc["level"]:
            continue
        feature = catalog.features[fid]
        out.append({
            "id": f"class:{cls_id}:{e['level']}:languages:{fid}",
            "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": e["level"]},
            "label": feature["name"],
            "description": _join(feature.get("desc")),
            "count": e["choose"],
            "options": [dict(o) for o in pool],
        })
    return out


def is_class_language_card(c: dict) -> bool:
    return c["source"]["kind"] == "class" and ":languages:" in c["id"]


def gate_languages(choices: list[dict], fixed_languages, class_order: list[str] = ()) -> list[dict]:
    """Disable ("already known") and drop stored picks of languages the character already knows:
    fixed languages plus the picks of every non-class language card (background / species / feat
    cards keep priority), then class language cards by (class order, class level). Mutates
    `choices` by index; returns non-blocking `pruned` entries in `choices` order."""
    idxs = [i for i, c in enumerate(choices) if is_class_language_card(c)]
    if not idxs:
        return []
    known: set[str] = set(fixed_languages)
    for c in choices:
        if c["source"]["kind"] in ("background", "species", "feat") and c["id"].endswith(":languages"):
            known.update(c["selected"])

    def key(i):
        src = choices[i]["source"]
        cid = src.get("id")
        return (class_order.index(cid) if cid in class_order else len(class_order), src.get("level") or 0, i)

    pruned_by_index: dict[int, dict] = {}
    for i in sorted(idxs, key=key):
        c = choices[i]
        options = [
            o if o.get("disabled") or o["id"] not in known
            else {**o, "disabled": True, "disabledReason": "already known"}
            for o in c["options"]
        ]
        enabled = {o["id"] for o in options if not o.get("disabled")}
        kept = [s for s in c["selected"] if s in enabled]
        dropped = [s for s in c["selected"] if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = ", ".join(labels.get(d, d) for d in dropped)
            pruned_by_index[i] = {
                "choiceId": c["id"],
                "reason": f"'{c['label']}': {names} is already known; the language selection was ignored.",
            }
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
        known.update(kept)
    return [pruned_by_index[i] for i in sorted(pruned_by_index)]


# ---- C6b-2: Barbarian Primal Knowledge -------------------------------------------------------

def primal_knowledge_cid() -> str:
    return f"class:{PRIMAL_KNOWLEDGE_2024['class']}:{PRIMAL_KNOWLEDGE_2024['level']}:feature:{PRIMAL_KNOWLEDGE_2024['feature']}"


def is_primal_knowledge_card(c: dict) -> bool:
    return c["id"] == primal_knowledge_cid() and c["source"]["kind"] == "class"


def primal_knowledge_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """Barbarian level 3+ (ruleset 2024): one skill from the Barbarian level 1 skill list, taken
    from the 2024 chassis record. No card without the XPHB feature or the chassis overlay."""
    if ruleset != "2024" or rc.get("cls_id") != PRIMAL_KNOWLEDGE_2024["class"] or not rc.get("cls"):
        return []
    feature = catalog.features.get(PRIMAL_KNOWLEDGE_2024["feature"])
    barbarian = (getattr(catalog, "classes_2024", None) or {}).get("barbarian")
    if not feature or not barbarian or rc["level"] < PRIMAL_KNOWLEDGE_2024["level"]:
        return []
    skills: list[str] = []
    for choice in barbarian.get("proficiency_choices") or []:
        for opt in (choice.get("from") or {}).get("options", []):
            idx = (opt.get("item") or {}).get("index", "")
            if idx in SKILL_NAMES and idx not in skills:
                skills.append(idx)
        if skills:
            break
    if not skills:
        return []
    return [{
        "id": primal_knowledge_cid(),
        "source": {"kind": "class", "id": "barbarian", "label": rc["cls"]["name"], "level": PRIMAL_KNOWLEDGE_2024["level"]},
        "label": feature["name"],
        "description": _join(feature.get("desc")),
        "count": 1,
        "options": [{"id": s, "label": SKILL_NAMES[s]} for s in skills],
    }]


def gate_primal_knowledge(choices: list[dict], proficient_skills: set[str]) -> list[dict]:
    """`proficient_skills` = every proficiency from sources other than this card. Options already
    proficient are disabled "already proficient" ("another skill"); stored picks of them are
    dropped with a `pruned` entry. Returns the pruned entries."""
    pruned: list[dict] = []
    for i, c in enumerate(choices):
        if not is_primal_knowledge_card(c):
            continue
        options = [
            o if o.get("disabled") or o["id"] not in proficient_skills
            else {**o, "disabled": True, "disabledReason": "already proficient"}
            for o in c["options"]
        ]
        enabled = {o["id"] for o in options if not o.get("disabled")}
        kept = [s for s in c["selected"] if s in enabled]
        dropped = [s for s in c["selected"] if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = ", ".join(labels.get(d, d) for d in dropped)
            pruned.append({"choiceId": c["id"],
                           "reason": f"'{c['label']}': {names} is already a proficient skill; the selection was ignored."})
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}
    return pruned


# ---- C6c-1: Sorcerer Metamagic (XPHB optional features) ---------------------------------------

METAMAGIC_FEATURE = "xphb-sorcerer-2-metamagic"


def optional_feature_progression(catalog, cls_id: str, feature_type: str) -> dict[int, int]:
    """{class level: total picks} from the XPHB class record's optionalfeatureProgression for one
    featureType ("MM"); {} when the record or the progression is missing."""
    record = (getattr(catalog, "class_2024_records", None) or {}).get(cls_id) or {}
    for prog in record.get("optional_feature_progression") or []:
        if feature_type in (prog.get("featureType") or []) and isinstance(prog.get("progression"), dict):
            return {int(k): v for k, v in prog["progression"].items() if str(k).isdigit() and isinstance(v, int)}
    return {}


def metamagic_cid() -> str:
    return f"class:sorcerer:2:feature:{METAMAGIC_FEATURE}"


def metamagic_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """Sorcerer under 2024: one Metamagic card, count = progression value at the highest reached
    level ({2: 2, 10: 4, 17: 6}), options = the XPHB MM records labelled with their Sorcery Point
    cost. `count_by_level` makes a level-down a non-blocking `pruned` entry."""
    if ruleset != "2024" or rc.get("cls_id") != "sorcerer" or not rc.get("cls"):
        return []
    feature = catalog.features.get(METAMAGIC_FEATURE)
    progression = optional_feature_progression(catalog, "sorcerer", "MM")
    reached = [lvl for lvl in progression if lvl <= rc["level"]]
    options = sorted((f for f in catalog.features.values()
                      if f.get("source") == "XPHB" and "MM" in (f.get("feature_types") or [])),
                     key=lambda f: f["name"])
    if not feature or not reached or not options:
        return []
    return [{
        "id": metamagic_cid(),
        "source": {"kind": "class", "id": "sorcerer", "label": rc["cls"]["name"], "level": 2},
        "label": feature["name"],
        "description": _join(feature.get("desc")),
        "count": progression[max(reached)],
        "count_by_level": True,
        "options": [{"id": o["index"], "label": f"{o['name']} ({o.get('cost', 1)} SP)",
                     **({"description": _join(o["desc"])} if o.get("desc") else {})} for o in options],
    }]


def metamagic_details(catalog, choices) -> list[dict]:
    """[{name, cost}] of the selected 2024 Metamagic options, in pick order ([] without a card)."""
    if not isinstance(choices, list):
        return []
    card = next((c for c in choices if c.get("id") == metamagic_cid()), None)
    out = []
    for oid in (card or {}).get("selected") or []:
        opt = catalog.features.get(oid)
        if opt:
            out.append({"name": opt["name"], "cost": opt.get("cost", 1)})
    return out


# ---- C6a / C6c-2: class option cards (Divine / Primal Order, Blessed Strikes, Elemental Fury) ------

def class_option_specs(cls_id: str | None) -> list[tuple[str, dict]]:
    """[(slug, CLASS_OPTION_CHOICES_2024 entry)] of a class, by level."""
    found = [(slug, spec) for (cls, slug), spec in CLASS_OPTION_CHOICES_2024.items() if cls == cls_id]
    return sorted(found, key=lambda pair: pair[1]["level"])


def class_option_options(catalog, cls_id: str, slug: str, ruleset: str) -> list[dict]:
    """The options of one class option card, each `{id, label, description?}` from the imported XPHB
    feature records; [] when the ruleset is not 2024, the entry is unknown or the catalog lacks the
    XPHB records (SRD-only data)."""
    spec = CLASS_OPTION_CHOICES_2024.get((cls_id, slug))
    if ruleset != "2024" or not spec or spec["feature"] not in catalog.features:
        return []
    options = []
    for opt_id in spec["options"]:
        opt = catalog.features.get(opt_id)
        if not opt:
            return []
        option = {"id": opt_id, "label": opt["name"]}
        desc = _join(opt.get("desc"))
        if desc:
            option["description"] = desc
        options.append(option)
    return options


def class_option_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """One required pick (count 1) per option entry of the class whose level is reached, under ruleset
    "2024" only: C6a `class:<cls>:1:divine-order` / `...:primal-order` and C6c-2
    `class:<cls>:7:feature:<xphb feature id>` (the feature id lets sheet_features attach the pick to its
    C5 row). Every class entry of a multiclass character grants its own. No card under 2014 / mixed, so
    a stored pick there (or below the card's level) falls into the stale-cid `pruned` pass."""
    cls_id = rc.get("cls_id")
    if not rc.get("cls") or not cls_id:
        return []
    out = []
    for slug, spec in class_option_specs(cls_id):
        options = class_option_options(catalog, cls_id, slug, ruleset)
        if not options or rc["level"] < spec["level"]:
            continue
        out.append({
            "id": spec["cid"],
            "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": spec["level"]},
            "label": spec["label"],
            "description": _join(catalog.features[spec["feature"]].get("desc")),
            "count": 1,
            "options": options,
        })
    return out


def class_option_effect(catalog, rc: dict, slug: str, ruleset: str) -> dict:
    """Effect record of the option stored in the draft for this class entry's card, or {}. Mirrors the
    generic choice pass: the first valid stored option counts, so e.g. the cantrip count agrees with the
    resolved selection."""
    cls_id = rc.get("cls_id")
    spec = CLASS_OPTION_CHOICES_2024.get((cls_id, slug))
    options = class_option_options(catalog, cls_id, slug, ruleset)
    if not options or not spec or rc["level"] < spec["level"]:
        return {}
    stored = rc["class_choices"].get(spec["cid"])
    if not isinstance(stored, list):
        return {}
    valid = {o["id"] for o in options}
    pick = next((s for s in stored if isinstance(s, str) and s in valid), None)
    return spec["options"][pick] if pick else {}


def class_option_extra_cantrips(catalog, rc: dict, ruleset: str) -> int:
    """Extra cantrips known from the stored class option picks of this class entry (Thaumaturge / Magician)."""
    return sum(class_option_effect(catalog, rc, slug, ruleset).get("extra_cantrips", 0)
               for slug, _spec in class_option_specs(rc.get("cls_id")))


def selected_class_options(choices, cls_id: str | None = None) -> list[tuple[str, str, dict]]:
    """[(slug, option id, effect record)] of the resolved (selected) class option cards, in choice order;
    only the cards of `cls_id` when given."""
    if not isinstance(choices, list):
        return []
    out = []
    for c in choices:
        src = c.get("source") or {}
        if src.get("kind") != "class" or not c.get("selected") or (cls_id and src.get("id") != cls_id):
            continue
        for slug, spec in class_option_specs(src.get("id")):
            if c["id"] == spec["cid"]:
                effect = spec["options"].get(c["selected"][0])
                if effect is not None:
                    out.append((slug, c["selected"][0], effect))
    return out


def selected_class_option_effects(choices) -> list[dict]:
    """Effect records of the resolved class option cards, in choice order."""
    return [effect for _slug, _opt, effect in selected_class_options(choices)]


def strike_effect(choices, cls_id: str, key: str) -> dict | None:
    """The `divine_strike` / `primal_strike` / `potent_spellcasting` effect of a class's resolved
    Blessed Strikes / Elemental Fury card, or None."""
    for _slug, _opt, effect in selected_class_options(choices, cls_id):
        if key in effect:
            return effect[key]
    return None


def dice_at_level(dice_by_level: dict[int, str], level: int) -> str | None:
    """The dice string of the highest reached level key, None below the first."""
    reached = [lvl for lvl in dice_by_level if lvl <= level]
    return dice_by_level[max(reached)] if reached else None


# ---- C6d: class spell grants (always prepared, Magical Secrets, Spell Mastery, Signature Spells) ----

MAGICAL_SECRETS_LABEL = "Magical Secrets"


def class_spell_grants(catalog, cls_id: str | None, ruleset: str) -> dict:
    """The XPHB `additionalSpells` grants of one class ({} outside 2024 or without the data)."""
    if ruleset != "2024" or not cls_id:
        return {}
    return (getattr(catalog, "class_2024_spell_grants", None) or {}).get(cls_id) or {}


def always_prepared_class_spells(catalog, cls_id: str | None, class_level: int, class_name: str, ruleset: str) -> dict[str, str]:
    """{spell id: reason} of the spells this class always has prepared at `class_level` (Ranger 1
    Hunter's Mark, Paladin 2 Divine Smite, ...). The reason is the class name. Only spells in the
    catalog are returned."""
    out: dict[str, str] = {}
    for level, ids in sorted(class_spell_grants(catalog, cls_id, ruleset).get("always", {}).items()):
        if level <= class_level:
            out.update({sid: class_name for sid in ids if sid in catalog.spells})
    return out


def magical_secrets_filters(catalog, cls_id: str | None, class_level: int, max_slot_level: int, ruleset: str) -> list[dict]:
    """Parsed spell filters of the class's `expanded` grants that apply now: the key is a class level
    ("10") or "s<N>" (needs a spell slot of level N). Bard 10: Cleric, Druid and Wizard spells of
    level 1-5, then 6-9 as the slots arrive."""
    out = []
    for key, flt in class_spell_grants(catalog, cls_id, ruleset).get("expanded", {}).items():
        if key.isdigit():
            ok = class_level >= int(key)
        elif key[:1] == "s" and key[1:].isdigit():
            ok = max_slot_level >= int(key[1:])
        else:
            ok = False
        if ok:
            out.append(flt)
    return out


def label_magical_secrets(catalog, templates: list[dict], cls_id: str | None, class_level: int, ruleset: str) -> None:
    """Marks the options of the class's prepared-spells card that are not on its own spell list
    ("Fireball (Magical Secrets)"). Mutates the templates; no-op without an expanded grant."""
    if not magical_secrets_filters(catalog, cls_id, class_level, 9, ruleset):
        return
    for tpl in templates:
        if tpl["id"] != f"class:{cls_id}:spells-known":
            continue
        for opt in tpl["options"]:
            spell = catalog.spells.get(opt["id"])
            if spell and not any(c["index"] == cls_id for c in spell.get("classes", [])):
                opt["label"] = f"{opt['label']} ({MAGICAL_SECRETS_LABEL})"


def spell_pick_cid(slug: str, spec: dict) -> str:
    return f"class:wizard:{spec['class_level']}:{slug}"


def effective_picks(options, stored, count: int) -> list[str]:
    """What the generic choice pass resolves a stored selection to: deduplicated, strings only,
    valid (offered, not disabled) options, first `count`."""
    valid = {o["id"] for o in options if not o.get("disabled")}
    picked = list(dict.fromkeys(x for x in stored if isinstance(x, str))) if isinstance(stored, list) else []
    return [x for x in picked if x in valid][:count]


def wizard_spell_pick_templates(catalog, class_level: int, book_ids: list[str], source: dict, ruleset: str,
                                class_choices: dict | None) -> tuple[list[dict], dict[str, str]]:
    """Spell Mastery (Wizard 18) and Signature Spells (Wizard 20), ruleset 2024 only.

    Returns ([card templates], {spell id: reason}). `book_ids` is the effective spellbook (what the
    spellbook card resolves to). Options are the book spells of the pick's spell level, with the
    casting time condition when the rule has one. The reason map holds the picks the generic pass
    will resolve (valid stored picks), so the prepared card can disable them. An empty book (or no
    spell that fits) gives an option-less pending card. No card without the XPHB feature record."""
    from catalog.reference_data import WIZARD_SPELL_PICKS_2024

    if ruleset != "2024":
        return [], {}
    templates, always = [], {}
    for slug, spec in WIZARD_SPELL_PICKS_2024.items():
        if class_level < spec["class_level"] or spec["feature"] not in catalog.features:
            continue
        spells = sorted(
            (catalog.spells[sid] for sid in book_ids if sid in catalog.spells
             and catalog.spells[sid]["level"] == spec["spell_level"]
             and (spec["casting_time"] is None or catalog.spells[sid].get("casting_time") == spec["casting_time"])),
            key=lambda s: s["name"])
        cid = spell_pick_cid(slug, spec)
        condition = f" that have a casting time of {spec['casting_time'].replace('1 ', 'an ')}" if spec["casting_time"] else ""
        description = (f"Choose {spec['count']} level {spec['spell_level']} spell{'s' if spec['count'] != 1 else ''} in your "
                       f"spellbook{condition}. You always have them prepared.")
        if not spells:
            description = ("Choose spells for your spellbook first." if not book_ids
                           else f"No spell in your spellbook is eligible (level {spec['spell_level']}{condition}).")
        tpl = {"id": cid, "source": {**source, "level": spec["class_level"]}, "label": spec["label"],
               "description": description, "count": spec["count"],
               "options": [{"id": s["index"], "label": s["name"]} for s in spells]}
        templates.append(tpl)
        for sid in effective_picks(tpl["options"], (class_choices or {}).get(cid), spec["count"]):
            always[sid] = spec["grant"]
    return templates, always


# ---- C7a: Warlock Eldritch Invocations (XPHB optional features) -------------------------------

INVOCATION_FEATURE = "xphb-warlock-1-eldritch-invocations"
INVOCATION_CID = f"class:warlock:1:invocations:{INVOCATION_FEATURE}"


def invocation_base_id(option_id: str) -> str:
    """`opt-agonizing-blast-xphb~2` -> `opt-agonizing-blast-xphb` (E4: repeat instances are `<id>~k`)."""
    return option_id.split("~", 1)[0]


def invocation_instance(option_id: str) -> int:
    tail = option_id.partition("~")[2]
    return int(tail) if tail.isdigit() else 1


def invocation_records(catalog) -> list[dict]:
    """The XPHB Eldritch Invocation records (featureType EI), sorted by name."""
    return sorted((f for f in catalog.features.values()
                   if f.get("source") == "XPHB" and "EI" in (f.get("feature_types") or [])), key=lambda f: f["name"])


def invocation_counts(catalog) -> list[int]:
    """Invocations known per Warlock level (index level-1): the class table, else the record progression."""
    table = ((getattr(catalog, "class_2024_tables", None) or {}).get("warlock") or {}).get("invocations")
    if isinstance(table, list) and table:
        return table
    record = (getattr(catalog, "class_2024_records", None) or {}).get("warlock") or {}
    for prog in record.get("optional_feature_progression") or []:
        if "EI" in (prog.get("featureType") or []) and isinstance(prog.get("progression"), list):
            return prog["progression"]
    return []


def _invocation_ready(catalog) -> bool:
    return INVOCATION_FEATURE in catalog.features and bool(invocation_counts(catalog)) and bool(invocation_records(catalog))


def invocation_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """Warlock under 2024: one Eldritch Invocation card (Pacts are invocations). Count = the table value at
    the Warlock level; options = the 28 XPHB records plus `<id>~k` repeat instances (E4), each shown after its
    base. Prerequisites are enforced late by `gate_invocations` (disabled + reasons)."""
    if ruleset != "2024" or rc.get("cls_id") != "warlock" or not rc.get("cls") or not _invocation_ready(catalog):
        return []
    counts = invocation_counts(catalog)
    count = counts[min(rc["level"], len(counts)) - 1]
    options = []
    for rec in invocation_records(catalog):
        base = {"id": rec["index"], "label": rec["name"]}
        if rec.get("desc"):
            base["description"] = _join(rec["desc"])
        options.append(base)
        if rec.get("repeatable"):
            for k in range(2, count + 1):
                options.append({**base, "id": f"{rec['index']}~{k}", "label": f"{rec['name']} ({k})"})
    return [{
        "id": INVOCATION_CID,
        "source": {"kind": "class", "id": "warlock", "label": rc["cls"]["name"], "level": 1},
        "label": catalog.features[INVOCATION_FEATURE]["name"],
        "description": _join(catalog.features[INVOCATION_FEATURE].get("desc")),
        "count": count,
        "options": options,
    }]


def is_invocation_card_2024(c: dict) -> bool:
    return c["source"]["kind"] == "class" and c["id"] == INVOCATION_CID


def _invocation_unmet_2024(catalog, option_id: str, level: int, selected: set[str], cantrips: list[str]) -> str | None:
    from engine.spells import spell_attack_roll, spell_deals_damage
    rec = catalog.features.get(invocation_base_id(option_id)) or {}
    pre = rec.get("prerequisite_2024") or {}
    if (pre.get("level") or 0) > level:
        return f"requires warlock level {pre['level']}"
    bases = {invocation_base_id(s) for s in selected}
    for need in pre.get("optional_features") or []:
        if need not in bases:
            return "requires " + (catalog.features.get(need) or {}).get("name", need)
    kind = pre.get("cantrip")
    if kind:
        test = spell_attack_roll if kind == "attack" else spell_deals_damage
        if not any(test(catalog.spells.get(c) or {}) for c in cantrips):
            return ("requires a Warlock cantrip that requires an attack roll" if kind == "attack"
                    else "requires a Warlock cantrip that deals damage")
    k = invocation_instance(option_id)
    if k > 1:
        prev = invocation_base_id(option_id) + ("" if k == 2 else f"~{k - 1}")
        if prev not in selected:
            return f"take {rec.get('name', 'it')}{'' if k == 2 else f' ({k - 1})'} first"
    return None


def gate_invocations(catalog, choice: dict, level: int, cantrips: list[str]) -> tuple[dict, list[dict]]:
    """Disable options whose prerequisites are unmet and drop selected ones that no longer qualify, to a
    fixed point (removing Pact of the Blade also removes Thirsting Blade, then Devouring Blade).
    Returns (new choice, non-blocking pruned entries)."""
    selected = list(choice["selected"])
    dropped: list[str] = []
    names = {o["id"]: o["label"] for o in choice["options"]}
    for _ in range(12):
        keep = set(selected)
        bad = [s for s in selected if _invocation_unmet_2024(catalog, s, level, keep, cantrips)]
        if not bad:
            break
        selected = [s for s in selected if s not in bad]
        dropped += bad
    keep = set(selected)
    options = []
    for o in choice["options"]:
        reason = _invocation_unmet_2024(catalog, o["id"], level, keep, cantrips)
        options.append({**o, "disabled": True, "disabledReason": reason} if reason else o)
    pruned = []
    if dropped:
        pruned.append({"choiceId": choice["id"], "reason":
                       f"'{choice['label']}': {', '.join(names.get(d, d) for d in dropped)} no longer meets its prerequisites and was ignored."})
    return {**choice, "options": options, "selected": selected,
            "status": "resolved" if len(selected) == choice["count"] else "pending"}, pruned
