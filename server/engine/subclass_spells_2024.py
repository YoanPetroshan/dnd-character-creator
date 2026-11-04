"""RP17 (F3, E13): XPHB subclass spell picks, ruleset "2024" only.

  Savants (Abjurer / Diviner / Evoker / Illusionist 3)  free spellbook spells of the school, joining the effective book
  Improved Illusions (Illusionist 3)                    one other Wizard cantrip when Minor Illusion is already known
  Magical Discoveries (Lore Bard 6)                     two always-prepared spells of the Cleric / Druid / Wizard lists
  Circle of the Land spells                             the picked land's spell table (catalog `spells_by_variant`)

The data is `reference_data.SUBCLASS_SPELL_PICKS_2024` (verbatim quotes pinned by tests) plus the catalog subclass
record's `spell_choices` (filters and the class level of each pick) and `spells_by_variant` (converter keys of
`catalog/official/subclasses.py`). A card needs the XPHB feature record, the selected subclass and the class level at
that record's level, so an SRD-only catalog, a 2014 twin, mixed / 2014 or a missing subclass give nothing (a stored pick
there is a stale cid and lands in `pruned`). Pure: resolve() wires the templates, `class_choices_2024` the
unavailable / count-variable hooks. The spell lookups are passed in (`options_fn`), the module never imports resolve."""
from __future__ import annotations

import re

from catalog import reference_data
from i18n.messages import msg

_CARD_RE = re.compile(r"^class:([^:]+):(\d+):feature:(.+)$")


def spec_for_card(c: dict) -> tuple[str, dict] | None:
    """(feature id, SUBCLASS_SPELL_PICKS_2024 entry) a class card was built from, or None."""
    if (c.get("source") or {}).get("kind") != "class":
        return None
    m = _CARD_RE.match(c.get("id", ""))
    if not m:
        return None
    spec = reference_data.SUBCLASS_SPELL_PICKS_2024.get(m.group(3))
    return (m.group(3), spec) if spec and spec["class"] == m.group(1) else None


def is_pick_card(c: dict) -> bool:
    return spec_for_card(c) is not None


def card_id(cls_id: str, level: int, feature_id: str) -> str:
    return f"class:{cls_id}:{level}:feature:{feature_id}"


def _join(desc) -> str:
    return "\n".join(str(d) for d in desc or [])


def _applicable(catalog, rc: dict, ruleset: str, kind: str) -> list[tuple[str, dict, dict]]:
    """[(feature id, spec, feature record)] of the `kind` entries of the class's selected XPHB subclass whose level is reached."""
    cls_id, sub_id = rc.get("cls_id"), rc.get("subclass_id")
    if ruleset != "2024" or not rc.get("cls") or not cls_id or not sub_id:
        return []
    out = []
    for fid, spec in reference_data.SUBCLASS_SPELL_PICKS_2024.items():
        if spec["kind"] != kind or spec["class"] != cls_id or spec["subclass"] != sub_id:
            continue
        record = catalog.features.get(fid)
        if record and rc["level"] >= (record.get("level") or 1):
            out.append((fid, spec, record))
    return out


def _reached(catalog, sub_id: str, mode: str, class_level: int) -> list[dict]:
    """The subclass record's `spell_choices` entries of `mode` gained at or below `class_level`."""
    sub = catalog.subclasses.get(sub_id) or {}
    return [e for e in sub.get("spell_choices") or [] if e["mode"] == mode and e["level"] <= class_level]


def effective(options: list[dict], stored, count: int) -> list[str]:
    """What the generic choice pass resolves a stored selection to: deduplicated, strings only, offered and not
    disabled, first `count`."""
    valid = {o["id"] for o in options if not o.get("disabled")}
    picked = list(dict.fromkeys(x for x in stored if isinstance(x, str))) if isinstance(stored, list) else []
    return [x for x in picked if x in valid][:count]


def _spell_options(catalog, refs: list[dict]) -> list[dict]:
    """Reference options -> card options, grouped by the spell's level (`spell-level-N`)."""
    out = []
    for r in refs:
        sid = r["item"]["index"]
        spell = catalog.spells.get(sid)
        opt = {"id": sid, "label": r["item"]["name"]}
        if spell is not None:
            opt["group"] = f"spell-level-{spell['level']}"
        out.append(opt)
    return out


def _source(rc: dict, level: int) -> dict:
    return {"kind": "class", "id": rc["cls_id"], "label": rc["cls"]["name"], "level": level}


def _twins(catalog, sid: str) -> set[str]:
    return {sid, catalog.spell_twins.get(sid) or sid}


# ---- Savants -------------------------------------------------------------------------------------------------------

def savant_template(catalog, rc: dict, ruleset: str, max_slot: int, book_ids: list[str], options_fn, selections) -> dict | None:
    """The Savant card (count = filter entries reached, 2 at level 3 then one at every level that opens a new slot
    level). Options: Wizard spells of the school, levels 1 .. min(slot level, the levels of the reached filters); a spell
    already in the effective spellbook is disabled. `options_fn(filter, keep)` returns reference options."""
    for fid, spec, record in _applicable(catalog, rc, ruleset, "savant"):
        entries = [e for e in _reached(catalog, rc["subclass_id"], "known", rc["level"])
                   if (e["filter"].get("school") or []) == [spec["school"]]]
        if not entries:
            continue
        levels = sorted({lv for e in entries for lv in e["filter"].get("level", []) if 1 <= lv <= max_slot})
        stored = (selections or {}).get(card_id(rc["cls_id"], record.get("level") or 1, fid))
        keep = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
        refs = options_fn({"level": levels, "class": ["wizard"], "school": [spec["school"]]}, keep) if levels else []
        options = _spell_options(catalog, refs)
        in_book = set(book_ids) | {t for sid in book_ids for t in _twins(catalog, sid)}
        for o in options:
            if o["id"] in in_book:
                o["disabled"] = True
                o["disabledReason"] = "already in your spellbook"
        count = len(entries)
        level = record.get("level") or 1
        return {
            "id": card_id(rc["cls_id"], level, fid), "source": _source(rc, level), "label": record["name"],
            "description": (_join(record.get("desc"))
                            + f" Free spellbook spells so far: {count}. They do not count against the spellbook card."),
            "count": count, "options": options,
        }
    return None


def effective_savant_picks(tpl: dict | None, stored) -> list[str]:
    return effective(tpl["options"], stored, tpl["count"]) if tpl else []


# ---- Improved Illusions --------------------------------------------------------------------------------------------

def cantrip_template(catalog, rc: dict, ruleset: str, options_fn, selections) -> dict | None:
    """Improved Illusions: one OTHER Wizard cantrip (not Minor Illusion, which is known anyway). Always built for the
    Illusionist; `gate_improved_illusions` removes the card when Minor Illusion is not already known elsewhere."""
    for fid, spec, record in _applicable(catalog, rc, ruleset, "cantrip"):
        stored = (selections or {}).get(card_id(rc["cls_id"], record.get("level") or 1, fid))
        keep = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
        skip = _twins(catalog, spec["known"] + "-xphb") | _twins(catalog, spec["known"])
        refs = [r for r in options_fn({"level": [0], "class": ["wizard"]}, keep) if r["item"]["index"] not in skip]
        level = record.get("level") or 1
        return {
            "id": card_id(rc["cls_id"], level, fid), "source": _source(rc, level), "label": record["name"],
            "description": _join(record.get("desc")), "count": 1, "options": _spell_options(catalog, refs),
        }
    return None


def minor_illusion_ids(catalog) -> set[str]:
    spec = reference_data.SUBCLASS_SPELL_PICKS_2024["illusionist-xphb-3-improved-illusions"]
    return _twins(catalog, spec["known"] + "-xphb") | _twins(catalog, spec["known"])


def improved_illusions_applies(catalog, rc: dict, ruleset: str) -> bool:
    return bool(_applicable(catalog, rc, ruleset, "cantrip"))


def gate_improved_illusions(choices: list[dict], catalog, innate_ids) -> list[dict]:
    """Late pass (the Iron Mind pattern). Minor Illusion is "already known" when it is selected on any other card (the
    Wizard's Cantrips Known card, another class's, a species / feat cantrip card) or granted by species / feat innate
    spells. Not known: the card is removed (a valid stored pick gets a non-blocking `pruned` entry). Known: the card
    stays and a cantrip already known elsewhere is disabled "already known" (a stored duplicate is dropped with a
    `pruned` entry). Mutates `choices`; returns the pruned entries."""
    idx = next((i for i, c in enumerate(choices) if (found := spec_for_card(c)) and found[1]["kind"] == "cantrip"), None)
    if idx is None:
        return []
    card = choices[idx]
    held = {s for i, c in enumerate(choices) if i != idx for s in c["selected"]
            if (catalog.spells.get(s) or {}).get("level") == 0} | {x for x in innate_ids if x}
    pruned: list[dict] = []
    if not (held & minor_illusion_ids(catalog)):
        del choices[idx]
        if card["selected"]:
            pruned.append({"choiceId": card["id"], "reason": msg("pruned-minor-illusion-required", label=card["label"])})
        return pruned
    options = [o if o.get("disabled") or o["id"] not in held else {**o, "disabled": True, "disabledReason": "already known"}
               for o in card["options"]]
    kept = [s for s in card["selected"] if s not in held]
    dropped = [s for s in card["selected"] if s in held]
    if dropped:
        names = [(catalog.spells.get(d) or {}).get("name", d) for d in dropped]
        pruned.append({"choiceId": card["id"], "reason": msg("pruned-known-ignored", label=card["label"], names=names)})
    choices[idx] = {**card, "options": options, "selected": kept,
                    "status": "resolved" if len(kept) == card["count"] else "pending"}
    return pruned


# ---- Magical Discoveries -------------------------------------------------------------------------------------------

def discoveries_template(catalog, rc: dict, ruleset: str, max_slot: int, taken: dict[str, str], options_fn,
                         selections) -> tuple[dict | None, dict[str, str]]:
    """(card, {spell id: reason} of the valid picks). Count = prepared filter entries reached (2 at Bard 6), options =
    Cleric / Druid / Wizard spells, cantrips and levels up to the highest BARD slot level (`max_slot`); a spell the class
    already has always prepared (`taken`) is disabled. The picks are always prepared (reason "Magical Discoveries"), so
    resolve() hands them to the Bard's Cantrips / Prepared cards as disabled options."""
    for fid, spec, record in _applicable(catalog, rc, ruleset, "discoveries"):
        entries = _reached(catalog, rc["subclass_id"], "prepared", rc["level"])
        if not entries:
            continue
        stored = (selections or {}).get(card_id(rc["cls_id"], record.get("level") or 1, fid))
        keep = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
        refs = options_fn({"level": list(range(0, max_slot + 1)), "class": list(spec["lists"])}, keep)
        options = _spell_options(catalog, refs)
        for o in options:
            if o["id"] in taken:
                o["disabled"] = True
                o["disabledReason"] = f"always prepared ({taken[o['id']]})"
        level = record.get("level") or 1
        tpl = {"id": card_id(rc["cls_id"], level, fid), "source": _source(rc, level), "label": record["name"],
               "description": _join(record.get("desc")), "count": len(entries), "options": options}
        picks = effective(options, stored, tpl["count"])
        grants = {}
        for sid in picks:
            for key in _twins(catalog, sid):
                grants.setdefault(key, spec["grant"])
        return tpl, grants
    return None, {}


def picked_spells(choices: list[dict], kind: str) -> list[str]:
    """Spell ids selected on the resolved cards of `kind`."""
    out: list[str] = []
    for c in choices:
        found = spec_for_card(c)
        if found and found[1]["kind"] == kind:
            out += [s for s in c["selected"] if s not in out]
    return out
