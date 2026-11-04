"""SK10 (Y2): the book code of a choice option, as a `source` key on the option dict.

Labels are never changed (a feat label carries "(SOURCE)" only when its name occurs twice); the picker
used to parse the code from the label and could not filter the 177 options of a mixed ASI card that carry
none. `annotate_choices` is a pure post-pass over the finished choice list: it copies each option dict
that it can trace to a catalog record and adds `"source": <code>` ("SRD" when the record has none).

Which options get a `source`, by option id (equipment cards are skipped: their ids are item ids that can
collide with spell ids such as "shield"):
  - `feat:<index>`                    -> the feat record (ASI, background/species feat grants, feat pools);
  - an ASI step option (str-plus-2 ...) on a `class:*:asi` card -> "SRD" (the basic rule, not a book feature);
  - `<feature id>--<key>`             -> the text option's own `source`, else the feature record (subclass option
                                         cards: Totem Spirit, Hunter's Prey, ...);
  - an id in `catalog.features`       -> that record (invocations, metamagic, maneuvers and other optional
                                         features, Circle of the Land);
  - an id in `catalog.spells`         -> that spell (every spell card), except `skill-*` ids.
Options that are none of these (skills, languages, abilities, damage types, ...) get no `source`.
"""
from __future__ import annotations

SRD = "SRD"


def _code(record: dict | None) -> str:
    return (record or {}).get("source") or SRD


def option_source(catalog, choice: dict, option: dict) -> str | None:
    """The source code for one option, or None when the option is not a book record."""
    if (choice.get("source") or {}).get("kind") == "equipment":
        return None
    oid = option.get("id")
    if not isinstance(oid, str):
        return None
    if oid.startswith("feat:"):
        feat = catalog.feats.get(oid[5:])
        return _code(feat) if feat else None
    if choice.get("id", "").endswith(":asi"):
        return SRD  # an ASI step (str-plus-2, ...): feat options returned above
    if "--" in oid:
        fid = oid.split("--", 1)[0]
        feature = catalog.features.get(fid)
        if feature:
            text = ((feature.get("feature_specific") or {}).get("text_options") or {}).get("options") or []
            own = next((t for t in text if t.get("id") == oid), None)
            return (own or {}).get("source") or _code(feature)
        return None
    feature = catalog.features.get(oid)
    if feature:
        return _code(feature)
    if not oid.startswith("skill-"):
        spell = catalog.spells.get(oid)
        if spell:
            return _code(spell)
    return None


def annotate_choices(catalog, choices: list[dict]) -> list[dict]:
    """The choice list with `source` added to the traceable options. Choices and options that gain nothing
    are returned as they are; the rest are copied (input dicts are never mutated)."""
    out = []
    for choice in choices:
        options = choice.get("options")
        if not options:
            out.append(choice)
            continue
        new_options = []
        changed = False
        for option in options:
            src = option_source(catalog, choice, option)
            if src is not None and option.get("source") != src:
                new_options.append({**option, "source": src})
                changed = True
            else:
                new_options.append(option)
        out.append({**choice, "options": new_options} if changed else choice)
    return out
