"""C6b-1 / C6b-2: 2024 class choice cards that are built from XPHB feature ids (helper for resolve()).

Pure functions over the catalog; resolve() only wires them. Everything here is ruleset "2024"
only: with any other ruleset, or an SRD-only catalog (no XPHB feature records), every function
returns "nothing", so the SRD cards stay.
"""
from __future__ import annotations

from catalog.reference_data import (
    CLASS_LANGUAGES_2024, EXPERTISE_2024, LANGUAGES_2024_RARE, LANGUAGES_2024_STANDARD, PRIMAL_KNOWLEDGE_2024,
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
