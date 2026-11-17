"""The spell helpers of resolve(): spell visibility under the sources and the ruleset, spell option lists, Magical Secrets, spellbook and Mystic Arcanum templates, the source filter.

Split from engine/resolve.py (S17); the text below is moved unchanged. `engine.resolve` re-exports every name.
"""
from __future__ import annotations

from catalog import reference_data
from catalog.choices import build_choice_template
from catalog.loader import Catalog
from i18n.messages import msg
from catalog.reference_data import ruleset_allows
from . import class_choices_2024
from . import subclass_innate_2024
from . import subclass_spells_2024
from . import feat_spell_tables
from . import spells as spells_mod
from .resolve_feats import _source_allowed, _spell_filter_options, _spell_visible

def _subclass_visible(catalog: Catalog, sub: dict, sources=None, ruleset: str = "mixed") -> bool:
    """Whether a subclass may be offered under the draft's sources and ruleset
    (same twin rule as `_spell_visible`, over `catalog.subclass_twins`): a
    2014/2024 pair shows its 2014 record under "mixed" (and unknown values),
    its 2024 record under "2024", unless the other version's book is excluded
    by `sources`; "2014" hides 2024 records. A subclass without a twin is
    shown under every ruleset except 2014-hides-2024. Purely an offer filter -
    resolve() accepts any catalog subclass of the class."""
    if not _source_allowed(sub, sources) or not ruleset_allows(sub, "subclass", ruleset):
        return False
    twin = catalog.subclasses.get(catalog.subclass_twins.get(sub["index"]))
    if twin is None or ruleset == "2014" or not _source_allowed(twin, sources):
        return True
    is_2024 = (sub.get("ruleset") or "2014") == "2024"
    return is_2024 if ruleset == "2024" else not is_2024

MAX_SOURCES = 100  # Q5: more distinct books than this are ignored (the catalog has fewer than 50)

def _normalised_sources(raw) -> tuple[frozenset | None, bool]:
    """`draft.sources` as a frozenset of at most MAX_SOURCES distinct lowercase strings (other entries are dropped), plus
    whether the list had more than that. None when there is nothing to filter by. The slice is taken before any work on the
    list, so 100 000 entries cost no more than 100."""
    if not isinstance(raw, list) or not raw:
        return None, False
    kept: set[str] = set()
    for entry in raw:
        if isinstance(entry, str):
            kept.add(entry.lower())
            if len(kept) > MAX_SOURCES:
                return frozenset(sorted(kept)[:MAX_SOURCES]), True
    return (frozenset(kept) if kept else None), False

def _subclass_spell_ids(catalog: Catalog, cls_id: str, subclass_id: str | None, class_level: int,
                        feature_ids: set[str], mode: str, variant: str | None = None, ruleset: str = "mixed") -> list[str]:
    """Spells from the subclass's `spells` list whose prerequisites (class
    level, and for Circle of the Land the chosen terrain feature) are met,
    for entries behaving as `mode` ("always" prepared / "expanded" list). An
    entry's own `mode` (imported subclasses, one of which can carry both)
    wins over `SUBCLASS_SPELL_MODE` (SRD records), default "always". RP17: `variant` (Circle of the Land's picked
    land) adds the entries of the record's `spells_by_variant[variant]`."""
    from catalog import reference_data
    if not subclass_id:
        return []
    subclass_mode = reference_data.SUBCLASS_SPELL_MODE.get(subclass_id, "always")
    out: list[str] = []
    sub_record = catalog.subclasses.get(subclass_id) or {}
    for entry in (sub_record.get("spells") or []) + ((sub_record.get("spells_by_variant") or {}).get(variant) or [] if variant else []):
        if (entry.get("mode") or subclass_mode) != mode:
            continue
        spell_id = (entry.get("spell") or {}).get("index")
        if spell_id not in catalog.spells or spell_id in out:
            continue
        ok = True
        for req in entry.get("prerequisites") or []:
            if req.get("type") == "level":
                prefix, _, num = req["index"].rpartition("-")
                if prefix != cls_id or not num.isdigit() or class_level < int(num):
                    ok = False
            elif req.get("type") == "feature" and req["index"] not in feature_ids:
                ok = False
        if ok:
            out.append(spell_id)
    if mode == "always" and ruleset == "2024":  # RP18: the "prepared" innate entries (Great Old One Eldritch Hex)
        out += [sid for sid in subclass_innate_2024.prepared_spell_ids(catalog, sub_record, cls_id, class_level) if sid not in out]
    return out

def _spell_options(catalog: Catalog, cls_id: str, spell_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if s["level"] == spell_level and any(c["index"] == cls_id for c in s.get("classes", []))
        and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    matches.sort(key=lambda s: s["name"])
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]

def _spell_options_up_to(catalog: Catalog, cls_id: str, max_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    matches = [
        s for s in catalog.spells.values()
        if 1 <= s["level"] <= max_level and any(c["index"] == cls_id for c in s.get("classes", []))
        and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]

def _magical_secrets_options(catalog: Catalog, cls_id: str, max_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    """RP16 (SRD Bard Magical Secrets): every spell of level 0 .. `max_level` that sits on some class list but not
    on `cls_id`'s own (the own list is offered anyway; its cantrips live on the Cantrips card). A spell on no class
    list is not "from any class"."""
    matches = [
        s for s in catalog.spells.values()
        if s["level"] <= max_level and s.get("classes") and not any(c["index"] == cls_id for c in s["classes"])
        and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]

def _additional_secrets_options(catalog: Catalog, max_level: int, sources=None, ruleset: str = "mixed", keep=()) -> list[dict]:
    """RPX1 (SRD Lore Bard 6 Additional Magical Secrets): every spell of level 0 .. `max_level` that sits on some class
    list ("two spells of your choice from any class", the Bard's own included). A spell on no class list is not
    "from a class"."""
    matches = [
        s for s in catalog.spells.values()
        if s["level"] <= max_level and s.get("classes") and (s["index"] in keep or _spell_visible(catalog, s, sources, ruleset))
    ]
    matches.sort(key=lambda s: (s["level"], s["name"]))
    return [{"option_type": "reference", "item": {"index": s["index"], "name": s["name"]}} for s in matches]

def _additional_secrets_templates(catalog: Catalog, rc: dict, spellcasting: dict, sources, ruleset: str, stored) -> list[dict]:
    """RPX1: the Lore Bard's Additional Magical Secrets card (mixed / 2014): count 2, spells of any class of a level the
    BARD table can cast (`spellcasting` is the Bard's own level row) and cantrips. The picks are not counted against
    Spells Known and not part of the RP16 cap; `class_choices_2024.gate_additional_secrets` keeps them apart from the
    Bard's other spell cards. A stored pick hidden by `sources` stays offered."""
    if not class_choices_2024.additional_secrets_applies(catalog, rc, ruleset):
        return []
    spec = reference_data.ADDITIONAL_SECRETS_2014
    feature = catalog.features[spec["feature"]]
    kept = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
    cid = class_choices_2024.additional_secrets_cid(catalog)
    envelope = {"choose": spec["count"], "from": {
        "option_set_type": "options_array",
        "options": _additional_secrets_options(catalog, _highest_spell_slot_level(spellcasting), sources, ruleset, kept)}}
    source = {"kind": "class", "id": rc["cls_id"], "label": rc["cls"]["name"], "level": feature.get("level") or 6}
    description = msg("desc-additional-secrets", text=" ".join(feature.get("desc") or []))
    tpl = build_choice_template(envelope, cid, source, spec["label"], description=description)
    if tpl is None:
        return []
    _tag_spell_level_groups(catalog, tpl)
    return [tpl]

def _apply_secrets_cap(catalog: Catalog, tpl: dict, cls_id: str, cap: int, stored, on_list: set[str] = frozenset()) -> None:
    """RP16: at most `cap` of the known spells may be off the class's own list (2 per Magical Secrets feature
    reached). Walks the stored picks in order like the generic pass (valid, deduplicated, first `count`); an
    off-list pick over the cap is disabled, so the generic pass drops it as a non-blocking `pruned` entry and it
    does not take a count slot. At the cap the other off-list options are disabled. `on_list` (RP19): the Spells of
    the Mark spells, which are on the class's list for this character. Mutates `tpl`."""
    def off_list(option_id: str) -> bool:
        return option_id not in on_list and not any(c["index"] == cls_id for c in (catalog.spells.get(option_id) or {}).get("classes", []))

    reason = msg("disabled-magical-secrets-used", cap=cap)
    valid = {o["id"] for o in tpl["options"] if not o.get("disabled")}
    stored_ids = [x for x in dict.fromkeys(stored if isinstance(stored, list) else []) if isinstance(x, str) and x in valid]
    accepted, used, excess = [], 0, []
    for x in stored_ids:
        if len(accepted) >= tpl["count"]:
            break
        if off_list(x):
            if used >= cap:
                excess.append(x)
                continue
            used += 1
        accepted.append(x)
    for opt in tpl["options"]:
        if off_list(opt["id"]) and not opt.get("disabled") and (opt["id"] in excess or (used >= cap and opt["id"] not in accepted)):
            opt["disabled"] = True
            opt["disabledReason"] = reason

def _highest_spell_slot_level(spellcasting: dict) -> int:
    highest = 0
    for n in range(1, 10):
        if spellcasting.get(f"spell_slots_level_{n}", 0) > 0:
            highest = n
    return highest

def _tag_spell_level_groups(catalog: Catalog, tpl: dict) -> None:
    """Set `group` = "spell-level-N" on each spell option (catalog spell
    level) so the picker can render level headings."""
    for opt in tpl["options"]:
        spell = catalog.spells.get(opt["id"])
        if spell is not None:
            opt["group"] = f"spell-level-{spell['level']}"

def _apply_school_limit(
    catalog: Catalog, tpl: dict, limit: dict, class_level: int, cls_id: str, stored, problems_out: list | None,
) -> None:
    """2014 third-caster school limit on the known-spells card (see
    _spell_choice_templates). Mutates `tpl`."""
    schools = set(limit["schools"])
    free = len([lvl for lvl in limit["free_at"] if lvl <= class_level])

    def inside(option_id: str) -> bool:
        return ((catalog.spells.get(option_id) or {}).get("school") or {}).get("index") in schools

    for opt in tpl["options"]:
        opt["group"] = "school" if inside(opt["id"]) else "any-school"
    tpl["options"].sort(key=lambda o: o["group"] != "school")  # stable: keeps (level, name) inside each group
    valid = {o["id"] for o in tpl["options"] if not o.get("disabled")}
    picked = [x for x in dict.fromkeys(stored if isinstance(stored, list) else []) if isinstance(x, str) and x in valid]
    picked = picked[: tpl["count"]]
    outside = [x for x in picked if not inside(x)]
    if len(outside) >= free:
        for opt in tpl["options"]:
            if opt["group"] == "any-school" and not opt.get("disabled") and opt["id"] not in picked:
                opt["disabled"] = True
                opt["disabledReason"] = msg("disabled-school-limit", free=free, schools=list(limit["schools"]))
    if len(outside) > free and problems_out is not None:
        problems_out.append({
            "id": f"subclass-spell-school-limit-{cls_id}",
            "message": msg("subclass-spell-school-limit", n=len(outside), school_a=limit["schools"][0], school_b=limit["schools"][-1], free=free),
        })

def _effective_caster(catalog: Catalog, rc: dict, ruleset: str = "mixed") -> tuple[str, dict, str] | None:
    """(spellcasting ability, spellcasting dict, spell-list class id) of a
    resolved class entry, or None. A class with its own spellcasting uses its
    level row; otherwise a subclass with a third-caster `spellcasting` block
    (Eldritch Knight, Arcane Trickster) at class level >= 3 yields ability INT
    and a SYNTHETIC dict (`cantrips_known`, `spells_known`, `spell_slots_level_N`,
    `spells_kind`) shaped like a class level row's `spellcasting`. The
    synthetic dict is only handed to _spell_choice_templates; it never lands
    in `rc["level_row"]`. Under ruleset "2024" a class with an XPHB progression
    (`catalog.class_2024_progressions`) gets a COPY of its spellcasting dict
    with the cantrip count, the fixed prepared-spell count (`spells_known`,
    `spells_kind: "prepared"`) from those tables and, for a Paladin/Ranger,
    the round-up slots (caster level ceil(level / 2), slots from level 1)."""
    cls, cls_id, level = rc["cls"], rc["cls_id"], rc["level"]
    ability = spells_mod.spellcasting_ability(cls) if cls else None
    if ability:
        row = rc.get("level_row")
        if not row:
            return None
        sc = row.get("spellcasting") or {}
        prog = catalog.class_2024_progressions.get(cls_id) if ruleset == "2024" else None
        if prog and 1 <= level <= 20:
            sc = dict(sc)
            if prog["cantrips"]:
                sc["cantrips_known"] = prog["cantrips"][level - 1]
            sc["spells_known"] = prog["prepared"][level - 1]
            sc["spells_kind"] = "prepared"
            for n, count in spells_mod.single_class_spell_slots(catalog, cls_id, level, None, ruleset).items():
                sc[f"spell_slots_level_{n}"] = count
        return ability, sc, cls_id
    block = (rc.get("subclass") or {}).get("spellcasting")
    if not (isinstance(block, dict) and block.get("progression") == "1/3") or level < 3:
        return None
    try:
        sc = {"cantrips_known": block["cantrips"][level - 1], "spells_known": block["spells"][level - 1],
              "spells_kind": block.get("kind", "known")}
        for n, count in enumerate(block["slots"][level - 1], start=1):
            sc[f"spell_slots_level_{n}"] = count
    except (KeyError, IndexError, TypeError):
        return None
    return str(block.get("ability", "INT")).upper(), sc, str(block.get("list_class") or "wizard")

def _wizard_spellbook_template(
    catalog: Catalog, cls: dict, cls_id: str, spellcasting: dict, class_level: int, sources, ruleset: str,
    source: dict, keep: set[str], stored, mark_ids: list[str] = (),
) -> dict:
    """C4: the Wizard's spellbook choice (cid `class:wizard:spellbook`, both
    rulesets). XPHB / PHB: six level 1 spells at Wizard level 1, +2 for every
    later Wizard level, each of a level the character has spell slots for. Count
    follows the class level, so it is count-variable (`_is_count_variable_choice`,
    level-down reports `pruned`, never a blocking problem)."""
    count = 6 + 2 * (class_level - 1)
    max_spell_level = _highest_spell_slot_level(spellcasting)
    options = _spell_options_up_to(catalog, cls_id, max_spell_level, sources, ruleset, keep)
    added = _add_mark_options(catalog, options, mark_ids, max_spell_level, sources, ruleset, keep)  # RP19 Spells of the Mark
    envelope = {"choose": count, "from": {"option_set_type": "options_array", "options": options}}
    noun = (msg("noun-spell-levels", n=count, levels=[1]) if max_spell_level == 1
            else msg("noun-spell-upto", n=count, max=max_spell_level))
    description = msg("desc-spellbook", count=count, noun=noun)
    tpl = build_choice_template(envelope, f"class:{cls_id}:spellbook", source, msg("label-spellbook"), description=description)
    _tag_spell_level_groups(catalog, tpl)
    _label_mark_options(tpl, added)
    return tpl

def _add_mark_options(catalog: Catalog, options: list[dict], mark_ids: list[str], max_level: int, sources, ruleset: str,
                      keep=()) -> set[str]:
    """RP19: appends the Spells of the Mark spells (level 1 .. `max_level`, visible under the draft's sources and
    ruleset or already picked) that the class list does not offer yet to `options`, sorted like the rest. Returns the
    ids added (the ones to label)."""
    present = {o["item"]["index"] for o in options}
    added: set[str] = set()
    for sid in mark_ids:
        spell = catalog.spells.get(sid)
        if not spell or sid in present or not 1 <= spell["level"] <= max_level:
            continue
        if sid not in keep and not _spell_visible(catalog, spell, sources, ruleset):
            continue
        options.append({"option_type": "reference", "item": {"index": sid, "name": spell["name"]}})
        present.add(sid)
        added.add(sid)
    if added:
        options.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
    return added

def _label_mark_options(tpl: dict, added: set[str]) -> None:
    for opt in tpl["options"]:
        if opt["id"] in added:
            opt["label"] = f"{opt['label']} ({feat_spell_tables.MARK_LABEL})"

def _spell_choice_templates(
    catalog: Catalog, cls: dict, cls_id: str, level_row: dict | None, ability_modifier: int, class_level: int,
    expanded_spell_ids: list[str] = (), always_prepared: dict[str, str] | None = None,
    sources=None, ruleset: str = "mixed", class_choices: dict | None = None, list_class_id: str | None = None,
    school_limit: dict | None = None, problems_out: list | None = None, secrets_cap: int = 0,
    subclass_id: str | None = None, mark_ids: list[str] = (),
) -> list[dict]:
    """`sources`/`ruleset` (the draft's) decide which catalog spells are
    offered; spells already selected in `class_choices` stay offered either
    way, so changing the ruleset never silently drops a pick. `list_class_id`
    (default: `cls_id`) is the class whose spell list is offered (a third
    caster uses the wizard list). `school_limit` (2014 Eldritch Knight /
    Arcane Trickster, `reference_data.SUBCLASS_SPELL_SCHOOL_LIMITS`) splits the
    known-spells card into `school` / `any-school` groups, locks the outside
    options once the stored picks use up the free slots, and appends a
    `subclass-spell-school-limit-<cls>` problem to `problems_out` when the
    stored picks exceed them. `secrets_cap` (RP16, SRD Bard Magical Secrets under mixed / 2014, from
    `class_choices_2024.magical_secrets_cap_2014`) adds the other classes' spells and cantrips to the known-spells
    card and limits how many of the picks may come from outside the class's own list. `subclass_id` (RP17, ruleset
    2024): the Wizard's selected subclass; a Savant card (free spellbook spells) is built after the spellbook card and
    its valid picks join the effective book (prepared card, Spell Mastery, Signature Spells). `mark_ids` (RP19): catalog
    ids of the held Mark feats' table spells (both editions of a spell); the ones up to this class's highest slot level
    join the spell list the cards offer, labelled "(Spells of the Mark)"."""
    if not level_row:
        return []
    spellcasting = level_row.get("spellcasting") or {}
    list_id = list_class_id or cls_id
    list_name = (catalog.classes.get(list_id) or cls)["name"]
    # An always-prepared spell and its 2014/2024 twin are the same spell.
    always_ids = dict(always_prepared or {})
    for sid, why in list(always_ids.items()):
        twin = catalog.spell_twins.get(sid)
        if twin:
            always_ids.setdefault(twin, why)
    templates = []
    # No `level` in source — these choices span every level a spellcaster
    # has reached (count grows as they level up), so they're not anchored
    # to one specific level the way a feature/ASI choice is.
    source = {"kind": "class", "id": cls_id, "label": cls["name"]}

    def _kept(cid: str) -> set[str]:
        picked = (class_choices or {}).get(cid)
        return {x for x in picked if isinstance(x, str)} if isinstance(picked, list) else set()

    cantrips_known = spellcasting.get("cantrips_known", 0)
    if cantrips_known > 0:
        envelope = {"choose": cantrips_known, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, list_id, 0, sources, ruleset, _kept(f"class:{cls_id}:spells-cantrips")),
        }}
        cid = f"class:{cls_id}:spells-cantrips"
        description = msg("desc-cantrips-from-list", n=cantrips_known, list=list_name)
        tpl = build_choice_template(envelope, cid, source, msg("label-cantrips-known"), description=description)
        if tpl:
            _tag_spell_level_groups(catalog, tpl)
            for opt in tpl["options"]:
                if opt["id"] in always_ids:
                    opt["disabled"] = True
                    opt["disabledReason"] = msg("disabled-always-prepared", source=always_ids[opt["id"]])
            templates.append(tpl)

    known_count = spells_mod.known_spell_count(level_row, ability_modifier, class_level=class_level, cls_id=cls_id)
    # C4: only the Wizard class has a spellbook (Eldritch Knight / Arcane
    # Trickster are fighter/rogue classes with list_class_id "wizard" and are
    # not affected). The prepared card then draws from the stored book.
    wizard_book: list[str] | None = None
    if cls_id == "wizard" and list_id == "wizard" and class_level >= 1 and _highest_spell_slot_level(spellcasting) > 0:
        book_tpl = _wizard_spellbook_template(
            catalog, cls, cls_id, spellcasting, class_level, sources, ruleset, source, _kept(f"class:{cls_id}:spellbook"),
            (class_choices or {}).get(f"class:{cls_id}:spellbook"), mark_ids,
        )
        templates.append(book_tpl)
        valid_book = {o["id"] for o in book_tpl["options"]}
        stored_book = (class_choices or {}).get(f"class:{cls_id}:spellbook")
        stored_book = list(dict.fromkeys(x for x in stored_book if isinstance(x, str))) if isinstance(stored_book, list) else []
        # Same rule as the generic pass: first `count` valid picks.
        wizard_book = [x for x in stored_book if x in valid_book][: book_tpl["count"]]
        if ruleset == "2024" and subclass_id:  # RP17: Abjuration / Divination / Evocation / Illusion Savant
            savant_tpl = subclass_spells_2024.savant_template(
                catalog, {"cls": cls, "cls_id": cls_id, "level": class_level, "subclass_id": subclass_id}, ruleset,
                _highest_spell_slot_level(spellcasting), wizard_book,
                lambda flt, keep: _spell_filter_options(catalog, flt, sources, ruleset, keep), class_choices)
            if savant_tpl is not None:
                templates.append(savant_tpl)
                savant_picks = subclass_spells_2024.effective_savant_picks(savant_tpl, (class_choices or {}).get(savant_tpl["id"]))
                for opt in book_tpl["options"]:  # the spellbook card may not repeat a free Savant spell
                    if opt["id"] in savant_picks and not opt.get("disabled"):
                        opt["disabled"] = True
                        opt["disabledReason"] = msg("disabled-chosen-as", label=savant_tpl["label"])
                wizard_book = wizard_book + [x for x in savant_picks if x not in wizard_book]
    # C6d (2024): Wizard 18 Spell Mastery / Wizard 20 Signature Spells; their picks are always prepared
    pick_templates: list[dict] = []
    if wizard_book is not None:
        pick_templates, pick_always = class_choices_2024.wizard_spell_pick_templates(
            catalog, class_level, wizard_book, source, ruleset, class_choices)
        for sid, why in pick_always.items():
            for key in (sid, catalog.spell_twins.get(sid)):
                if key:
                    always_ids.setdefault(key, why)
    if known_count > 0:
        max_spell_level = _highest_spell_slot_level(spellcasting)
        if wizard_book is not None:
            option_list = [{"option_type": "reference", "item": {"index": sid, "name": catalog.spells[sid]["name"]}} for sid in wizard_book]
            option_list.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
        else:
            option_list = _spell_options_up_to(catalog, list_id, max_spell_level, sources, ruleset, _kept(f"class:{cls_id}:spells-known"))
        present = {o["item"]["index"] for o in option_list}
        mark_added = (_add_mark_options(catalog, option_list, mark_ids, max_spell_level, sources, ruleset,
                                        _kept(f"class:{cls_id}:spells-known"))
                      if wizard_book is None else set())  # RP19 Spells of the Mark
        present |= mark_added
        for sid in (expanded_spell_ids if wizard_book is None else ()):  # e.g. Fiend Expanded Spell List
            spell = catalog.spells[sid]
            if sid not in present and 1 <= spell["level"] <= max_spell_level:
                option_list.append({"option_type": "reference", "item": {"index": sid, "name": spell["name"]}})
        if secrets_cap and wizard_book is None and list_id == cls_id:  # RP16: SRD Magical Secrets (levels 10 / 14 / 18)
            option_list += [o for o in _magical_secrets_options(
                catalog, cls_id, max_spell_level, sources, ruleset, _kept(f"class:{cls_id}:spells-known"))
                if o["item"]["index"] not in present]
        option_list.sort(key=lambda o: (catalog.spells[o["item"]["index"]]["level"], o["item"]["name"]))
        envelope = {"choose": known_count, "from": {
            "option_set_type": "options_array",
            "options": option_list,
        }}
        cid = f"class:{cls_id}:spells-known"
        is_known_caster = spellcasting.get("spells_known") is not None and spellcasting.get("spells_kind", "known") == "known"
        label = msg("label-spells-known") if is_known_caster else msg("label-prepared-spells")
        noun = (msg("noun-spell", n=known_count) if max_spell_level == 1
                else msg("noun-spell-upto", n=known_count, max=max_spell_level))
        if wizard_book is None:
            description = (msg("desc-spells-know", n=known_count, noun=noun, list=list_name) if is_known_caster
                           else msg("desc-spells-prepare", n=known_count, noun=noun, list=list_name))
        elif wizard_book:
            description = (msg("desc-spells-know-book", n=known_count, noun=noun) if is_known_caster
                           else msg("desc-spells-prepare-book", n=known_count, noun=noun))
        else:
            description = msg("desc-spellbook-first")
        if secrets_cap and wizard_book is None and list_id == cls_id:
            description = msg("desc-spells-secrets", text=description, cap=secrets_cap)
        tpl = build_choice_template(envelope, cid, source, label, description=description)
        if tpl is not None and mark_added:
            _label_mark_options(tpl, mark_added)
        if tpl is None and wizard_book is not None and not wizard_book:
            # build_choice_template returns None for an empty option list; an
            # empty spellbook must still show the (option-less) prepared card.
            tpl = {"id": cid, "source": source, "label": label, "description": description, "count": known_count, "options": []}
        if tpl:
            _tag_spell_level_groups(catalog, tpl)
            for opt in tpl["options"]:
                if opt["id"] in always_ids:
                    opt["disabled"] = True
                    opt["disabledReason"] = msg("disabled-always-prepared", source=always_ids[opt["id"]])
            if school_limit:
                _apply_school_limit(catalog, tpl, school_limit, class_level, cls_id,
                                    (class_choices or {}).get(cid), problems_out)
            if secrets_cap and wizard_book is None and list_id == cls_id:
                _apply_secrets_cap(catalog, tpl, cls_id, secrets_cap, (class_choices or {}).get(cid), mark_added)
            templates.append(tpl)

    return templates + pick_templates

# Warlock level at which each Mystic Arcanum spell level is gained (identical
# in the 2014 and 2024 books); the SRD `mystic_arcanum_level_N` column is the
# gate, this table only names the level used in the cid.
_ARCANUM_LEVELS = {6: 11, 7: 13, 8: 15, 9: 17}

def _mystic_arcanum_templates(catalog: Catalog, rc: dict, sources=None, ruleset: str = "mixed", class_choices: dict | None = None) -> list[dict]:
    """Warlock Mystic Arcanum (D11): one ordinary single-pick choice per
    arcanum spell level whose `class_specific.mystic_arcanum_level_N` is >= 1
    at the current Warlock level, always from the Warlock list (also in a
    multiclass). A spell already stored stays offered, as for other spell
    options."""
    if rc.get("cls_id") != "warlock" or not rc.get("cls"):
        return []
    specific = ((rc.get("level_row") or {}).get("class_specific")) or {}
    templates = []
    for spell_level, gained_at in _ARCANUM_LEVELS.items():
        if (specific.get(f"mystic_arcanum_level_{spell_level}") or 0) < 1:
            continue
        cid = f"class:warlock:{gained_at}:mystic-arcanum-{spell_level}"
        stored = (class_choices or {}).get(cid)
        keep = {x for x in stored if isinstance(x, str)} if isinstance(stored, list) else set()
        envelope = {"choose": 1, "from": {
            "option_set_type": "options_array",
            "options": _spell_options(catalog, "warlock", spell_level, sources, ruleset, keep),
        }}
        source = {"kind": "class", "id": "warlock", "label": rc["cls"]["name"], "level": gained_at}
        tpl = build_choice_template(
            envelope, cid, source, msg("label-feature-level", name="Mystic Arcanum", level=spell_level),
            description=msg("desc-mystic-arcanum", level=spell_level),
        )
        if tpl:
            _tag_spell_level_groups(catalog, tpl)
            templates.append(tpl)
    return templates
