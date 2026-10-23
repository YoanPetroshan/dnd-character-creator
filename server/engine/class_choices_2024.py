"""C6a / C6b-1 / C6b-2 / C6c-1 / C6c-2 / C7a-c: 2024 class choice cards that are built from XPHB feature ids (helper for resolve()).

Pure functions over the catalog; resolve() only wires them. Everything here is ruleset "2024"
only: with any other ruleset, or an SRD-only catalog (no XPHB feature records), every function
returns "nothing", so the SRD cards stay.
"""
from __future__ import annotations

import re

from engine import subclass_options_2024
from catalog.reference_data import (
    FEAT_LANGUAGE_REPLACEMENT,
    CLASS_LANGUAGES_2024, CLASS_OPTION_CHOICES_2024, EXPERTISE_2024, INVOCATION_EFFECTS, INVOCATION_EFFECTS_2024, LANGUAGES_2024_RARE, LANGUAGES_2024_STANDARD, PRIMAL_KNOWLEDGE_2024,
    SKILL_NAMES, SRD_CARDS_REPLACED_2024, SUBCLASS_PICKS_2024, TOOLS,
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


def fixed_class_language_entries(catalog, resolved_classes, ruleset: str) -> list[tuple[tuple[int, int], str]]:
    """F3a-5: `fixed_class_languages` with the position (class position, class level of the feature) of each."""
    order = [rc["cls_id"] for rc in resolved_classes if rc.get("cls") and rc.get("cls_id")]
    out: list[tuple[tuple[int, int], str]] = []
    for rc in resolved_classes:
        if not rc.get("cls") or not rc.get("cls_id"):
            continue
        for _fid, e in _language_entries(catalog, rc["cls_id"], ruleset):
            if e["level"] <= rc["level"]:
                out += [((order.index(rc["cls_id"]), e["level"]), lang) for lang in e["fixed"]]
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


# ---- C8: 2024 origin languages --------------------------------------------------------------
# PHB 2024 ch. 2 "Choose Languages": "Your character knows at least three languages: Common plus
# two languages you roll or choose from the Standard Languages table." (decision E10)

ORIGIN_LANGUAGES_CID = "origin:languages"
ORIGIN_LANGUAGES_PICKS = 2


def fixed_origin_languages(ruleset: str) -> list[str]:
    """Languages every 2024 character knows (Common). [] outside 2024."""
    return ["common"] if ruleset == "2024" else []


def is_origin_language_card(c: dict) -> bool:
    return c["id"] == ORIGIN_LANGUAGES_CID and c["source"]["kind"] == "background"


def origin_language_templates(bg: dict | None, bg_id: str | None, ruleset: str) -> list[dict]:
    """The single 2-pick card of Standard languages (Common excluded: it is fixed). Source kind
    `background` so BackgroundPage renders it and the export gate counts it; the picks are stored
    under background.choices. No card without a chosen background (nowhere to store the picks)."""
    if ruleset != "2024" or not bg or not bg_id:
        return []
    return [{
        "id": ORIGIN_LANGUAGES_CID,
        "source": {"kind": "background", "id": bg_id, "label": bg.get("name", "")},
        "label": "Languages",
        "description": ("Your character knows Common plus two languages you choose from the Standard "
                        "Languages table (Player's Handbook 2024, chapter 2)."),
        "count": ORIGIN_LANGUAGES_PICKS,
        "options": [{"id": l["index"], "label": l["name"]} for l in LANGUAGES_2024_STANDARD if l["index"] != "common"],
    }]


# ---- RP3 (A1): replacement language of a feat whose fixed language may already be known ----------------------------

def is_feat_replacement_language_card(c: dict) -> bool:
    """The `<feat cid prefix>:languages` card of a FEAT_LANGUAGE_REPLACEMENT feat (Cult of the Dragon Initiate)."""
    return (c["source"]["kind"] == "feat" and c["source"].get("id") in FEAT_LANGUAGE_REPLACEMENT
            and c["id"].endswith(":languages"))


def feat_replacement_language_template(feat: dict, cid_prefix: str, feat_level: int | None = None) -> dict | None:
    """The conditional card: "If you already know <language> when you select this feat, you instead learn one
    language of your choice". Built for every holder; gate_languages removes it when the language is not known at
    the feat's position. Options: the PHB 2024 Standard + Rare tables (decision E2)."""
    rule = FEAT_LANGUAGE_REPLACEMENT.get(feat.get("index"))
    if not rule:
        return None
    source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
    if feat_level is not None:
        source["level"] = feat_level
    return {
        "id": f"{cid_prefix}:languages",
        "source": source,
        "label": f"{feat['name']}: {rule['label']}",
        "description": (f"You already know {rule['language'].capitalize()}, so you learn one language of your "
                        "choice instead."),
        "count": 1,
        "options": [{"id": l["index"], "label": l["name"]} for l in LANGUAGES_2024_STANDARD + LANGUAGES_2024_RARE],
    }


_CLASS_CID_PREFIX_RE = re.compile(r"^class:([^:]+):")


def _feat_card_position(c: dict, class_order) -> tuple[int, int]:
    """Position of a feat card: ASI feats sit at `class:<cls>:<lvl>:...`, Lessons of the First Ones feats at
    `class:<cls>:invocation:...` (level in `source.level`); origin feats at (-1, 0)."""
    m = _CLASS_CID_PREFIX_RE.match(c["id"])
    if not m:
        return (-1, 0)
    pos = card_position(c, class_order)
    if pos is not None and pos != (-1, 0):
        return pos
    order = list(class_order)
    return (order.index(m.group(1)) if m.group(1) in order else len(order), c["source"].get("level") or 0)


def gate_languages(choices: list[dict], fixed_languages, class_order: list[str] = (), positioned_fixed=()) -> list[dict]:
    """Disable ("already known") and drop stored picks of languages the character already knows.
    Priority: `fixed_languages` (species / background / origin feats / Common), picks of every other
    origin language card (background / species / origin feat cards), the C8 origin card, then class
    language cards by (class order, class level).
    F3a-5: `positioned_fixed` = [((class position, class level), language)] are fixed grants (class
    features, Lessons / ASI feats) and ASI feat language picks counted only for cards at or after
    their position, so an earlier pick wins and the later duplicate is blamed.
    RP3: a FEAT_LANGUAGE_REPLACEMENT feat card (Cult of the Dragon Initiate) exists only while the feat's fixed
    language is already known at the feat's position, not counting the feat's own grant (origin feats: fixed
    species / background languages and origin card picks of species / background; Lessons / ASI feats: also
    everything earlier in the build). Otherwise the card is removed and a stored pick is reported.
    Mutates `choices`; returns non-blocking `pruned` entries in `choices` order."""
    repl = [i for i, c in enumerate(choices) if is_feat_replacement_language_card(c)]
    idxs = [i for i, c in enumerate(choices) if is_class_language_card(c) or is_origin_language_card(c)]
    if not idxs and not repl:
        return []
    known: set[str] = set(fixed_languages)
    pick_known: set[str] = set()  # picks of species / background / origin feat cards (not the replacement card)
    positioned = list(positioned_fixed)
    for c in choices:
        if (c["source"]["kind"] in ("background", "species", "feat") and c["id"].endswith(":languages")
                and not is_origin_language_card(c) and not is_feat_replacement_language_card(c)):
            pos = card_position(c, class_order) if c["source"]["kind"] == "feat" else (-1, 0)
            if pos is None or pos == (-1, 0):
                known.update(c["selected"])
                pick_known.update(c["selected"])
            else:
                positioned += [(pos, lang) for lang in c["selected"]]

    pruned_by_index: dict[int, dict] = {}
    removed: set[int] = set()

    def own_language(c):
        return FEAT_LANGUAGE_REPLACEMENT[c["source"]["id"]]["language"]

    def known_without_own(c, here):
        """Languages known at `here`, with the feat's own fixed grant taken out once."""
        fixed = list(fixed_languages)
        pos_fixed = list(positioned)
        lang = own_language(c)
        if here == (-1, 0):
            if lang in fixed:
                fixed.remove(lang)
        elif (here, lang) in pos_fixed:
            pos_fixed.remove((here, lang))
        # origin picks of species / background / other feat cards count; the origin card and earlier cards are
        # added by the caller for positioned feats
        return set(fixed) | pick_known | {l for p, l in pos_fixed if p <= here}

    def settle_replacement(i, extra_known):
        c = choices[i]
        here = _feat_card_position(c, class_order)
        lang = own_language(c)
        known_before = known_without_own(c, here) | extra_known
        if lang not in known_before:
            if c["selected"]:
                labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
                names = ", ".join(labels.get(d, d) for d in c["selected"])
                pruned_by_index[i] = {
                    "choiceId": c["id"],
                    "reason": (f"'{c['label']}': {names} no longer applies because you do not already know "
                               f"{lang.capitalize()}; the language selection was ignored."),
                }
            removed.add(i)
            return
        known_here = known | known_before | {l for p, l in positioned if p <= here}
        options = [o if o.get("disabled") or o["id"] not in known_here
                   else {**o, "disabled": True, "disabledReason": "already known"} for o in c["options"]]
        enabled = {o["id"] for o in options if not o.get("disabled")}
        kept = [s for s in c["selected"] if s in enabled][: c["count"]]
        dropped = [s for s in c["selected"] if s not in kept]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            pruned_by_index[i] = {
                "choiceId": c["id"],
                "reason": f"'{c['label']}': {', '.join(labels.get(d, d) for d in dropped)} is already known; "
                          "the language selection was ignored.",
            }
        choices[i] = {**c, "options": options, "selected": kept,
                      "status": "resolved" if len(kept) == c["count"] else "pending"}

    # origin-position replacement cards first: their picks have the priority of every other origin feat card
    for i in repl:
        if _feat_card_position(choices[i], class_order) == (-1, 0):
            settle_replacement(i, set())
            if i not in removed:
                known.update(choices[i]["selected"])
    later_repl = [i for i in repl if i not in removed and _feat_card_position(choices[i], class_order) != (-1, 0)]

    def pos_of(i):
        c = choices[i]
        if is_origin_language_card(c):
            return (-1, 0)
        if is_feat_replacement_language_card(c):
            return _feat_card_position(c, class_order)
        src = c["source"]
        cid = src.get("id")
        return (class_order.index(cid) if cid in class_order else len(class_order), src.get("level") or 0)

    for i in sorted(idxs + later_repl, key=lambda i: (*pos_of(i), i)):
        if i in later_repl:
            settle_replacement(i, set(known))
            if i not in removed:
                known.update(choices[i]["selected"])
            continue
        c = choices[i]
        here = pos_of(i)
        known_here = known | {lang for pos, lang in positioned if pos <= here}
        options = [
            o if o.get("disabled") or o["id"] not in known_here
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
    out = [pruned_by_index[i] for i in sorted(pruned_by_index)]
    if removed:
        choices[:] = [c for i, c in enumerate(choices) if i not in removed]
    return out


# ---- C6b-2: Barbarian Primal Knowledge -------------------------------------------------------

def primal_knowledge_cid() -> str:
    return f"class:{PRIMAL_KNOWLEDGE_2024['class']}:{PRIMAL_KNOWLEDGE_2024['level']}:feature:{PRIMAL_KNOWLEDGE_2024['feature']}"


def is_primal_knowledge_card(c: dict) -> bool:
    return c["id"] == primal_knowledge_cid() and c["source"]["kind"] == "class"


def _level_1_skills(cls_record: dict | None) -> list[str]:
    """The skills of a class record's first skill proficiency choice (the 2024 chassis record lists its level 1
    skills there)."""
    skills: list[str] = []
    for choice in (cls_record or {}).get("proficiency_choices") or []:
        for opt in (choice.get("from") or {}).get("options", []):
            idx = (opt.get("item") or {}).get("index", "")
            if idx in SKILL_NAMES and idx not in skills:
                skills.append(idx)
        if skills:
            break
    return skills


def primal_knowledge_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """Barbarian level 3+ (ruleset 2024): one skill from the Barbarian level 1 skill list, taken
    from the 2024 chassis record. No card without the XPHB feature or the chassis overlay."""
    if ruleset != "2024" or rc.get("cls_id") != PRIMAL_KNOWLEDGE_2024["class"] or not rc.get("cls"):
        return []
    feature = catalog.features.get(PRIMAL_KNOWLEDGE_2024["feature"])
    barbarian = (getattr(catalog, "classes_2024", None) or {}).get("barbarian")
    if not feature or not barbarian or rc["level"] < PRIMAL_KNOWLEDGE_2024["level"]:
        return []
    skills = _level_1_skills(barbarian)
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


_CLASS_CID_LEVEL_RE = re.compile(r"^class:([^:]+):(\d+):")


def card_position(c: dict, class_order) -> tuple[int, int] | None:
    """Where a card's grant sits in the build: (class position, class level); (-1, 0) for origin cards (species,
    background, background feats); None for class cards without a level in their cid (spell cards ...). ASI feat
    cards (`class:<cls>:<lvl>:asi:feat:...`) sit at their ASI level."""
    kind = c["source"]["kind"]
    m = _CLASS_CID_LEVEL_RE.match(c["id"])
    if kind in ("species", "background") or (kind == "feat" and not m):
        return (-1, 0)
    if not m:
        return None
    order = list(class_order)
    return (order.index(m.group(1)) if m.group(1) in order else len(order), int(m.group(2)))


_MULTICLASS_PROF_CID_RE = re.compile(r"^class:([^:]+):multiclass-prof-choice-\d+$")


def proficiency_position(c: dict, class_order) -> tuple[int, int] | None:
    """`card_position`, plus RP12: a multiclass proficiency card (`class:<cls>:multiclass-prof-choice-N`, no level in
    its cid) is gained when the class is entered, so it sits at (class position, 1)."""
    m = _MULTICLASS_PROF_CID_RE.match(c["id"]) if c["source"]["kind"] == "class" else None
    if m:
        order = list(class_order)
        return (order.index(m.group(1)) if m.group(1) in order else len(order), 1)
    return card_position(c, class_order)


def gate_after_positioned_pick(choices: list[dict], class_order, pos: tuple[int, int], granted: set[str],
                               source_name: str) -> list[dict]:
    """F3a-4, generalised by RP12: proficiency picks (skills and tools) that come AFTER a positioned pick (Primal
    Knowledge, a subclass pick) see its proficiencies as already held: the option is disabled and a stored pick of
    it is dropped (the later pick is the duplicate). Positioned cards themselves are walked in order by the caller.
    Returns the pruned entries."""
    pruned: list[dict] = []
    for i, c in enumerate(choices):
        if c["source"]["kind"] not in ("class", "feat") or is_positioned_proficiency_card(c):
            continue
        if c.get("profOrExpertise"):  # FE6: Keen Mind / Observant turn an already proficient skill into Expertise
            continue
        if not ("proficiency-choice" in c["id"] or "prof-choice-" in c["id"]) or "expertise-choice" in c["id"]:
            continue
        here = proficiency_position(c, class_order)
        hit = [o["id"] for o in c["options"] if o["id"] in granted]
        if here is None or here <= pos or not hit:
            continue
        options = [o if o["id"] not in granted or o.get("disabled") else {**o, "disabled": True, "disabledReason": "already proficient"}
                   for o in c["options"]]
        kept = [s for s in c["selected"] if s not in granted]
        if len(kept) != len(c["selected"]):
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = ", ".join(labels.get(s, s) for s in c["selected"] if s in granted)
            pruned.append({"choiceId": c["id"], "reason": f"'{c['label']}': {names} is already proficient ({source_name}); the selection was ignored."})
        choices[i] = {**c, "options": options, "selected": kept, "status": "resolved" if len(kept) == c["count"] else "pending"}
    return pruned


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


# ---- RP12: subclass proficiency picks (Lore, Student of War, Otherworldly Glamour, Iron Mind) -------------------------

_PICK_CID_RE = re.compile(r"^class:([^:]+):\d+:(feature|tool-choice):(.+)$")
_SAVE_NAMES = {"STR": "Strength", "DEX": "Dexterity", "CON": "Constitution", "INT": "Intelligence", "WIS": "Wisdom", "CHA": "Charisma"}


def pick_spec_for_card(c: dict) -> dict | None:
    """The `SUBCLASS_PICKS_2024` entry a class card was built from (matched on class, cid kind and feature id), or None."""
    if c["source"]["kind"] != "class":
        return None
    m = _PICK_CID_RE.match(c["id"])
    if not m:
        return None
    return next((spec for spec in SUBCLASS_PICKS_2024
                 if spec["class"] == m.group(1) and spec["cid"] == m.group(2) and spec["feature"] == m.group(3)), None)


def is_positioned_proficiency_card(c: dict) -> bool:
    """The skill / tool picks whose position in the build matters: Primal Knowledge (C6b-2) and the RP12 subclass
    skill and tool picks. They are walked in (class order, class level) order and see everything gained before them;
    later cards see them. (The Iron Mind save pick is gated separately, against saving throws.)"""
    if is_primal_knowledge_card(c):
        return True
    spec = pick_spec_for_card(c)
    return spec is not None and spec["kind"] in ("skills", "tool")


def is_save_pick_card(c: dict) -> bool:
    spec = pick_spec_for_card(c)
    return spec is not None and spec["kind"] == "save"


def _pick_options(catalog, spec: dict) -> list[dict]:
    kind = spec["kind"]
    if kind == "tool":
        return [{"id": t["index"], "label": t["name"]} for t in TOOLS if t["category"] == "Artisan's Tools"]
    if kind == "save":
        return [{"id": a.lower(), "label": _SAVE_NAMES[a]} for a in spec["alternatives"]]
    pool = spec["pool"]
    if pool == "any":
        skills = list(SKILL_NAMES)
    elif isinstance(pool, tuple):
        skills = list(pool)
    else:  # "class-level-1:<class id>"
        skills = _level_1_skills((getattr(catalog, "classes_2024", None) or {}).get(pool.split(":", 1)[1]))
    return [{"id": sk, "label": SKILL_NAMES[sk]} for sk in skills]


def subclass_pick_templates(catalog, rc: dict, ruleset: str) -> list[dict]:
    """RP12: the proficiency pick cards of the class's selected XPHB subclass (`SUBCLASS_PICKS_2024`), ruleset 2024
    only. A card needs its XPHB feature record and the class level at that record's level, so an SRD-only catalog,
    a missing subclass or a 2014 twin gives nothing. The Iron Mind card is always built here; resolve() removes it
    when the Wisdom save is not yet proficient at its position (the feature then grants Wisdom outright)."""
    sub_id, cls_id = rc.get("subclass_id"), rc.get("cls_id")
    if ruleset != "2024" or not sub_id or not rc.get("cls"):
        return []
    out = []
    for spec in SUBCLASS_PICKS_2024:
        if spec["subclass"] != sub_id or spec["class"] != cls_id:
            continue
        feature = catalog.features.get(spec["feature"])
        if not feature or rc["level"] < (feature.get("level") or 1):
            continue
        options = _pick_options(catalog, spec)
        if not options:
            continue
        level = feature.get("level") or 1
        out.append({
            "id": f"class:{cls_id}:{level}:{spec['cid']}:{spec['feature']}",
            "source": {"kind": "class", "id": cls_id, "label": rc["cls"]["name"], "level": level},
            "label": spec["label"],
            "description": _join(feature.get("desc")),
            "count": spec["count"],
            "options": options,
        })
    return out


def gate_positioned_card(choices: list[dict], card_id: str, prior: set[str]) -> list[dict]:
    """RP12: the generic form of `gate_primal_knowledge` for a positioned pick (skills, tools or saves): options in
    `prior` (everything gained at or before the card's position) are disabled "already proficient" and stored picks
    of them are dropped with a `pruned` entry. Returns the pruned entries."""
    pruned: list[dict] = []
    for i, c in enumerate(choices):
        if c["id"] != card_id:
            continue
        options = [o if o.get("disabled") or o["id"] not in prior
                   else {**o, "disabled": True, "disabledReason": "already proficient"} for o in c["options"]]
        kept = [s for s in c["selected"] if s not in prior]
        dropped = [s for s in c["selected"] if s in prior]
        if dropped:
            labels = {o["id"]: o.get("label", o["id"]) for o in c["options"]}
            names = ", ".join(labels.get(d, d) for d in dropped)
            pruned.append({"choiceId": c["id"], "reason": f"'{c['label']}': {names} is already proficient; the selection was ignored."})
        choices[i] = {**c, "options": options, "selected": kept, "status": "resolved" if len(kept) == c["count"] else "pending"}
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
TOME_ID, BLADE_ID = "opt-pact-of-the-tome-xphb", "opt-pact-of-the-blade-xphb"
AGONIZING_ID, SPEAR_ID, REPELLING_ID = "opt-agonizing-blast-xphb", "opt-eldritch-spear-xphb", "opt-repelling-blast-xphb"
LESSONS_ID = "opt-lessons-of-the-first-ones-xphb"


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
    base = invocation_base_id(option_id)
    if base in _TARGET_KIND:
        # F3a-2a: instance k needs k different eligible cantrips (the same check the target cards use, incl.
        # Eldritch Spear's range), or its target card could never be completed.
        eligible = {c for c in cantrips if c in catalog.spells and not _target_reason(catalog, base, catalog.spells[c])}
        if len(eligible) < k:
            return "needs another eligible cantrip" if k > 1 else "needs an eligible cantrip"
    return None


def gate_invocations(catalog, choice: dict, level: int, cantrips: list[str],
                    tome_cantrips: list[str] = ()) -> tuple[dict, list[dict]]:
    """Disable options whose prerequisites are unmet and drop selected ones that no longer qualify, to a
    fixed point (removing Pact of the Blade also removes Thirsting Blade, then Devouring Blade).
    C7c: `tome_cantrips` (the Pact of the Tome picks) count as Warlock cantrips while the Tome is selected
    ("they function as Warlock spells for you"), so dropping the Tome can drop Agonizing Blast in turn.
    Returns (new choice, non-blocking pruned entries)."""
    selected = list(choice["selected"])
    dropped: list[str] = []
    names = {o["id"]: o["label"] for o in choice["options"]}

    def known(keep: set[str]) -> list[str]:
        return list(cantrips) + (list(tome_cantrips) if TOME_ID in keep else [])

    overflow: list[str] = []
    for _ in range(12):
        keep = set(selected)
        bad = [s for s in selected if _invocation_unmet_2024(catalog, s, level, keep, known(keep))]
        if not bad:
            if len(selected) <= choice["count"]:
                break
            # F3a-9: the count cut comes AFTER the prerequisite check, so valid picks behind invalid ones survive;
            # cutting can remove an enabler, hence another round
            overflow += selected[choice["count"]:]
            selected = selected[:choice["count"]]
            continue
        selected = [s for s in selected if s not in bad]
        dropped += bad
    keep = set(selected)
    options = []
    for o in choice["options"]:
        reason = _invocation_unmet_2024(catalog, o["id"], level, keep, known(keep))
        options.append({**o, "disabled": True, "disabledReason": reason} if reason else o)
    pruned = []
    if dropped:
        pruned.append({"choiceId": choice["id"], "reason":
                       f"'{choice['label']}': {', '.join(names.get(d, d) for d in dropped)} no longer meets its prerequisites and was ignored."})
    if overflow:
        pruned.append({"choiceId": choice["id"], "reason":
                       f"'{choice['id']}' now allows {choice['count']} selection(s); {len(overflow)} stored selection(s) "
                       f"no longer fit and were ignored: {', '.join(names.get(d, d) for d in overflow)}."})
    return {**choice, "options": options, "selected": selected,
            "status": "resolved" if len(selected) == choice["count"] else "pending"}, pruned


# E6: the data says "ritual" for Pact of the Chain; the text says it is cast without a spell slot, so at will.
_INNATE_USES_2024 = {"at-will": "at-will", "1/long rest": "1/long rest", "ritual": "at-will"}


def invocation_effect(catalog, option_id: str) -> dict | None:
    """C7b: the effect dict of one selected invocation (instance suffix already stripped).
    SRD ids read `INVOCATION_EFFECTS`; XPHB ids merge what the imported record carries (the innate spell with its
    frequency and the spell's catalog level, senses) with `INVOCATION_EFFECTS_2024` (table wins on a clash).
    An innate spell missing from the catalog is left out (nothing unverifiable). None = no effect."""
    eff = INVOCATION_EFFECTS.get(option_id)
    if eff:
        return eff
    if not (option_id.startswith("opt-") and option_id.endswith("-xphb")):
        return None
    out: dict = {}
    rec = (catalog.features.get(option_id) if catalog is not None else None) or {}
    for entry in ((rec.get("spells") or {}).get("innate") or [])[:1]:
        spell = catalog.spells.get(entry["spell"])
        uses = _INNATE_USES_2024.get(entry.get("uses"))
        if spell and uses:
            out["innate_spell"] = {"spell": entry["spell"], "uses": uses, "level": spell["level"]}
    if rec.get("senses"):
        out["senses"] = dict(rec["senses"])
    out.update(INVOCATION_EFFECTS_2024.get(option_id) or {})
    return out or None


# ---- C7c: invocation dependents (target cantrips, Pact of the Tome, Pact of the Blade) ---------------------------
# Cards that exist only for SELECTED invocation instances. Their cids contain `:invocation:` (singular), never
# `:invocations:`, so the R8 count-variable / `selected_invocation_ids` plumbing ignores them:
#   class:warlock:invocation:<instance id>:cantrip   target of Agonizing Blast / Eldritch Spear / Repelling Blast
#   class:warlock:invocation:opt-pact-of-the-tome-xphb:cantrips | :rituals
#   class:warlock:invocation:opt-pact-of-the-blade-xphb:weapon
#   class:warlock:invocation:<Lessons instance>:feat (+ the feat's own cascade under `...:feat:<index>`; built in resolve)
# They are built from the RAW stored invocation selection (like the feat cascades) and pruned after the
# invocation gate when their instance is no longer selected (`prune_invocation_dependents`).

DEPENDENT_PREFIX = "class:warlock:invocation:"
_DEPENDENT_RE = re.compile(r"^class:warlock:invocation:([^:]+):")
_RANGE_RE = re.compile(r"^(\d+) feet$")
# target invocations: what the cantrip must do (XPHB text)
_TARGET_KIND = {AGONIZING_ID: "damage", SPEAR_ID: "damage", REPELLING_ID: "attack"}
SPEAR_MIN_RANGE_FEET = 10


def dependent_cid(instance_id: str, kind: str) -> str:
    return f"{DEPENDENT_PREFIX}{instance_id}:{kind}"


def is_dependent_choice(c: dict) -> bool:
    return c["source"]["kind"] in ("class", "feat") and c["id"].startswith(DEPENDENT_PREFIX)


def spell_range_feet(spell: dict) -> int | None:
    """The spell's range in feet when it is a plain "N feet" range; None for Self, Touch and the rest."""
    m = _RANGE_RE.match((spell.get("range") or "").strip())
    return int(m.group(1)) if m else None


def raw_invocation_instances(catalog, rc: dict, ruleset: str) -> list[str]:
    """The instance ids (`<id>` / `<id>~k`) the stored invocation selection resolves to BEFORE the cantrip-based
    gate: the card's valid picks (first `count`), minus those failing the structural prerequisites that do not
    need the spell cards (Warlock level, repeat instance k needs k-1). The late gate then decides the rest."""
    tpls = invocation_templates(catalog, rc, ruleset)
    if not tpls:
        return []
    tpl = tpls[0]
    picks = effective_picks(tpl["options"], (rc.get("class_choices") or {}).get(INVOCATION_CID), len(tpl["options"]))
    kept: list[str] = []
    for _ in range(len(picks) + 1):
        again = [s for s in picks if s not in kept and _structure_ok(catalog, s, rc["level"], set(kept))]
        if not again:
            break
        kept += again
    return [s for s in picks if s in kept][:tpl["count"]]  # F3a-9: structure first, then the count cut


def _structure_ok(catalog, option_id: str, level: int, kept: set[str]) -> bool:
    rec = catalog.features.get(invocation_base_id(option_id)) or {}
    if ((rec.get("prerequisite_2024") or {}).get("level") or 0) > level:
        return False
    k = invocation_instance(option_id)
    return k == 1 or invocation_base_id(option_id) + ("" if k == 2 else f"~{k - 1}") in kept


def instance_label(catalog, instance_id: str) -> str:
    k = invocation_instance(instance_id)
    name = (catalog.features.get(invocation_base_id(instance_id)) or {}).get("name", instance_id)
    return name if k == 1 else f"{name} ({k})"


def _spell_option(catalog, sid: str) -> dict:
    return {"id": sid, "label": (catalog.spells.get(sid) or {}).get("name", sid)}


def _target_source(rc: dict) -> dict:
    return {"kind": "class", "id": "warlock", "label": rc["cls"]["name"], "level": 2}


def _target_reason(catalog, base_id: str, spell: dict) -> str | None:
    from engine.spells import spell_attack_roll, spell_deals_damage
    if _TARGET_KIND[base_id] == "attack":
        return None if spell_attack_roll(spell) else "does not require an attack roll"
    if not spell_deals_damage(spell):
        return "does not deal damage"
    if base_id == SPEAR_ID and (spell_range_feet(spell) or 0) < SPEAR_MIN_RANGE_FEET:
        return "range is under 10 feet"
    return None


def target_templates(catalog, rc: dict, instances: list[str], candidates: list[str]) -> list[dict]:
    """One single-pick card per selected Agonizing Blast / Eldritch Spear / Repelling Blast instance. `candidates`
    are the known Warlock cantrips (plus the Tome's). Instances of one invocation hold different cantrips: the
    lower instance wins a duplicated stored pick, and every card disables the other instances' picks."""
    class_choices = rc.get("class_choices") or {}
    ordered = sorted((i for i in instances if invocation_base_id(i) in _TARGET_KIND),
                     key=lambda i: ((catalog.features.get(invocation_base_id(i)) or {}).get("name", ""), invocation_instance(i)))
    cands = sorted(dict.fromkeys(c for c in candidates if c in catalog.spells), key=lambda c: catalog.spells[c]["name"])
    chosen: dict[str, str] = {}  # instance id -> its effective pick
    for inst in ordered:
        base = invocation_base_id(inst)
        stored = class_choices.get(dependent_cid(inst, "cantrip"))
        taken = {chosen[o] for o in chosen if invocation_base_id(o) == base}
        for sid in (list(dict.fromkeys(x for x in stored if isinstance(x, str))) if isinstance(stored, list) else []):
            if sid in cands and sid not in taken and not _target_reason(catalog, base, catalog.spells[sid]):
                chosen[inst] = sid
                break
    out = []
    for inst in ordered:
        base = invocation_base_id(inst)
        options = []
        for sid in cands:
            opt = _spell_option(catalog, sid)
            reason = _target_reason(catalog, base, catalog.spells[sid])
            holder = next((o for o in chosen if o != inst and invocation_base_id(o) == base and chosen[o] == sid), None)
            if reason is None and holder:
                reason = f"already chosen for {instance_label(catalog, holder)}"
            if reason:
                opt.update(disabled=True, disabledReason=reason)
            options.append(opt)
        name = instance_label(catalog, inst)
        out.append({
            "id": dependent_cid(inst, "cantrip"), "source": _target_source(rc), "label": f"{name}: Cantrip",
            "description": ((catalog.features.get(base) or {}).get("desc") or [""])[0], "count": 1, "options": options,
        })
    return out


def instance_target(choices: list[dict], instance_id: str) -> str | None:
    """The resolved target cantrip id of one Agonizing / Spear / Repelling instance, or None."""
    cid = dependent_cid(instance_id, "cantrip")
    card = next((c for c in choices if c.get("id") == cid), None)
    return card["selected"][0] if card and card.get("selected") else None


TOME_CANTRIPS = {"filter": {"level": [0]}, "count": 3}
TOME_RITUALS = {"filter": {"level": [1], "ritual": True}, "count": 2}


def tome_templates(catalog, rc: dict, instances: list[str], spell_options, owned: set[str]) -> list[dict]:
    """Pact of the Tome: three cantrips and two level 1 Ritual spells from any class's list, none of which the
    Warlock already has prepared. `spell_options(filter)` is resolve's `_spell_filter_options` (ruleset / sources
    aware). The cards exist while the Tome is among the selected instances."""
    if TOME_ID not in instances:
        return []
    out = []
    for kind, spec, label, noun in (("cantrips", TOME_CANTRIPS, "Cantrips", "cantrips"),
                                    ("rituals", TOME_RITUALS, "Rituals", "level 1 spells with the Ritual tag")):
        options = []
        for o in spell_options(spec["filter"]):
            sid = o["item"]["index"]
            opt = {"id": sid, "label": o["item"]["name"]}
            if sid in owned:
                opt.update(disabled=True, disabledReason="already prepared")
            options.append(opt)
        out.append({
            "id": dependent_cid(TOME_ID, kind), "source": {**_target_source(rc), "level": 1}, "label": f"Pact of the Tome: {label}",
            "description": f"Choose {spec['count']} {noun} from any class's spell list that you don't already have prepared. "
                           "While the Book of Shadows is on your person you have them prepared and they function as Warlock spells.",
            "count": spec["count"], "options": options,
        })
    return out


def tome_picks(choices: list[dict]) -> dict[str, list[str]]:
    """{"cantrips": [...], "rituals": [...]} of the resolved Pact of the Tome cards ([] when absent)."""
    out = {}
    for kind in ("cantrips", "rituals"):
        card = next((c for c in choices if c.get("id") == dependent_cid(TOME_ID, kind)), None)
        out[kind] = list(card["selected"]) if card else []
    return out


def blade_template(catalog, rc: dict, instances: list[str]) -> list[dict]:
    """Pact of the Blade (E5): the pact weapon pick, every Simple / Martial Melee weapon of the catalog (F3a-2c:
    the text lets you conjure "a Simple or Martial Melee weapon of your choice"; it need not be owned)."""
    if BLADE_ID not in instances:
        return []
    weapons = sorted((i for i in catalog.items.values()
                      if (i.get("equipment_category") or {}).get("index") == "weapon" and i.get("weapon_range") == "Melee"
                      and i.get("weapon_category") in ("Simple", "Martial")), key=lambda i: i["name"])
    if not weapons:
        return []
    return [{
        "id": dependent_cid(BLADE_ID, "weapon"), "source": {**_target_source(rc), "level": 1}, "label": "Pact of the Blade: Pact Weapon",
        "description": "Choose the Simple or Martial Melee weapon you conjure and bond with. You are proficient with it "
                       "and can use your Charisma modifier for its attack and damage rolls.",
        "count": 1, "options": [{"id": i["index"], "label": i["name"]} for i in weapons],
    }]


def invocation_dependent_templates(catalog, rc: dict, ruleset: str, templates: list[dict], spell_options,
                                   owned: set[str]) -> list[dict]:
    """Target, Tome and Blade cards of the Warlock (everything except Lessons, which needs the feat walk).
    `templates` are the templates built so far (the Warlock cantrip card is read from there)."""
    if ruleset != "2024" or rc.get("cls_id") != "warlock" or not rc.get("cls") or not _invocation_ready(catalog):
        return []
    instances = raw_invocation_instances(catalog, rc, ruleset)
    if not instances:
        return []
    class_choices = rc.get("class_choices") or {}
    cantrip_card = next((t for t in templates if t["id"] == "class:warlock:spells-cantrips"), None)
    known = effective_picks(cantrip_card["options"], class_choices.get(cantrip_card["id"]), cantrip_card["count"]) if cantrip_card else []
    prepared_card = next((t for t in templates if t["id"] == "class:warlock:spells-known"), None)
    prepared = effective_picks(prepared_card["options"], class_choices.get(prepared_card["id"]), prepared_card["count"]) if prepared_card else []
    tome = tome_templates(catalog, rc, instances, spell_options, owned | set(known) | set(prepared))
    tome_cantrips: list[str] = []
    for tpl in tome:
        if tpl["id"].endswith(":cantrips"):
            tome_cantrips = effective_picks(tpl["options"], class_choices.get(tpl["id"]), tpl["count"])
    return target_templates(catalog, rc, instances, known + tome_cantrips) + tome + blade_template(catalog, rc, instances)


def prune_invocation_dependents(choices: list[dict], selected_instances) -> list[dict]:
    """After the invocation gate: drop the dependent cards whose instance is no longer selected. Mutates `choices`;
    returns non-blocking pruned entries for the cards that held a pick."""
    keep = set(selected_instances)
    pruned = []
    for c in list(choices):
        m = _DEPENDENT_RE.match(c["id"])
        if m and m.group(1) not in keep:
            choices.remove(c)
            if c.get("selected"):
                pruned.append({"choiceId": c["id"], "reason": f"'{c['label']}' no longer applies: its invocation is no longer selected, so the pick was ignored."})
    return pruned


def selected_pact_weapon(choices: list[dict]) -> str | None:
    card = next((c for c in choices if c.get("id") == dependent_cid(BLADE_ID, "weapon")), None)
    return card["selected"][0] if card and card.get("selected") else None


def pact_weapon_row_notes(selected_ids) -> list[str]:
    """Notes for the pact weapon's attack row from the selected XPHB invocations (instance suffix stripped), in table order."""
    from catalog.reference_data import PACT_WEAPON_ROW_NOTES_2024
    bases = {invocation_base_id(s) for s in selected_ids}
    return [note for fid, note in PACT_WEAPON_ROW_NOTES_2024.items() if fid in bases]


def lessons_instances(catalog, rc: dict, ruleset: str) -> list[str]:
    """Selected Lessons of the First Ones instance ids (`<id>`, `<id>~2`, ...) in instance order: the stored
    selection minus what fails the structural prerequisites (Warlock level 2, instance k needs k-1). Lessons has no
    spell prerequisite, so the late gate never drops what this returns (the feat walk needs it EARLY)."""
    if ruleset != "2024" or rc.get("cls_id") != "warlock" or not rc.get("cls") or not _invocation_ready(catalog):
        return []
    return sorted((i for i in raw_invocation_instances(catalog, rc, ruleset) if invocation_base_id(i) == LESSONS_ID),
                  key=invocation_instance)


# ---- F3a-2b: new 2024 cards that can never be completed ----------------------------------------------------------
# A card the 2024 chassis introduced (expertise, class languages, XPHB feature picks, Spell Mastery / Signature
# Spells, the Warlock's invocation dependents) can end up with every option disabled for the current character (no
# eligible spell, nothing left to learn). Such a card must not block export: its status becomes "unavailable" and
# `unavailableReason` explains why. SRD / 2014 cards keep their behaviour (they are never touched).
_NEW_2024_CARD_RE = re.compile(
    r"^class:[a-z-]+:\d+:(?:expertise-choice|languages):|^class:[a-z-]+:\d+:feature:xphb-"
    r"|^class:wizard:\d+:(?:spell-mastery-\d|signature-spells)$")


def _is_subclass_option_card(c: dict) -> bool:
    return subclass_options_2024.spec_for_card(c) is not None


def is_new_2024_class_card(c: dict) -> bool:
    return c["source"]["kind"] == "class" and bool(
        _NEW_2024_CARD_RE.match(c["id"]) or c["id"].startswith(DEPENDENT_PREFIX)
        or pick_spec_for_card(c) is not None  # RP12: subclass proficiency picks
        or _is_subclass_option_card(c))  # RP13: subclass option cards


def mark_unavailable(choices: list[dict], ruleset: str) -> list[dict]:
    """Under 2024, pending new-chassis cards with no enabled option become `unavailable` (non-blocking)."""
    if ruleset != "2024":
        return choices
    out = []
    for c in choices:
        if (c["status"] == "pending" and c["count"] > 0 and is_new_2024_class_card(c)
                and not any(not o.get("disabled") for o in c["options"])):
            reason = ("Nothing can be chosen here with the current character: " +
                      ("no option is offered yet." if not c["options"] else "every option is unavailable."))
            c = {**c, "status": "unavailable", "unavailableReason": reason}
        out.append(c)
    return out
