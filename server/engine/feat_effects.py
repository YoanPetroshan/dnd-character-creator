"""Feat effects (FE series, docs/superpowers/plans/2026-10-11-feat-effects.md).

Pure: no catalog import. Callers pass the resolved feat instances (``resolve.resolved_feats``)
and the effect table (``catalog.feat_effects_data.FEAT_EFFECTS``). A feat follows its own
edition's text under every ruleset (entries are keyed by feat index), so nothing here looks at
the ruleset.

FE1 covers the numeric derived stats: initiative, hit point maximum, walking speed and the
Athlete climb speed. Numeric effects are deduplicated by the feat's edition-independent name
key, so a stray duplicate (the S2 rules already forbid one) can never double Alert or Tough.

FE4 adds Armor Class (formulas, conditional bonuses, the medium armor cap), passive score bonuses, the
Stealth rule and additive senses.

FE5 adds the attack rows: weapon-math flags (off-hand attacks, Finesse), the Unarmed Strike a feat improves
(F-D6) and the predicate notes with the character's numbers (F-D2: optional riders are never folded into ``damage``).

FE3 adds the output surfaces: ``notes`` (text for effects that are not folded into a number, with
the character's numbers filled in) and ``resources`` (``derived.featResources``).
"""
from __future__ import annotations

import ast
import re

CHOOSE_ABILITY = "(choose the ability)"


def _name_key(feat: dict) -> str:
    """Same identity as resolve._feat_name_key: the lowercased name without a trailing (...)."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", feat.get("name") or "").strip().lower()


def _origin(feat: dict) -> str:
    return ("asi" if feat.get("_asi_cid") else "invocation" if feat.get("_inv_cid")
            else "fighting-style" if feat.get("_fs_cid") else "species" if feat.get("_species_origin")
            else "background")


def increased_ability(feat: dict, choices, prefix: str) -> str | None:
    """The ability this feat instance increased, as ``"STR"``..: its single fixed increase, else
    the selected ``<prefix>:ability-bonus`` pick, else None (not chosen yet, or the feat has none)."""
    fixed = {b["ability_score"]["index"].upper() for b in feat.get("ability_bonuses") or []}
    if len(fixed) == 1:
        return next(iter(fixed))
    card = next((c for c in choices or [] if c.get("id") == f"{prefix}:ability-bonus"), None)
    selected = (card or {}).get("selected") or []
    return selected[0].upper() if selected else None


def instances(resolved_feats, table: dict, choices=None) -> list[dict]:
    """One entry per held feat instance that has an effect entry:
    ``{feat, index, prefix, origin, effect, increased}``. Kept-but-hidden picks (A2) are included
    because they are in ``resolved_feats``; ``data_only`` entries carry nothing for the engine.
    ``increased`` is the instance's increased ability (see ``increased_ability``)."""
    out = []
    for feat in resolved_feats:
        effect = table.get(feat["index"])
        if not effect:
            continue
        prefix = feat.get("_asi_origin") or feat.get("_species_origin") or f"feat:{feat['index']}"
        out.append({"feat": feat, "index": feat["index"], "prefix": prefix,
                    "origin": _origin(feat), "effect": effect,
                    "increased": increased_ability(feat, choices, prefix)})
    return out


def _numeric(insts: list[dict], key: str) -> list:
    """Effect values for ``key``, one per feat name (first instance wins)."""
    seen, values = set(), []
    for inst in insts:
        if key not in inst["effect"]:
            continue
        name = _name_key(inst["feat"])
        if name in seen:
            continue
        seen.add(name)
        values.append(inst["effect"][key])
    return values


def initiative_parts(insts: list[dict]) -> tuple[int, bool]:
    """(flat bonus, adds the Proficiency Bonus). Alert (PHB) is a flat +5 on top of everything;
    Alert (XPHB) lets you add the Proficiency Bonus, which replaces the Jack of All Trades /
    Remarkable Athlete half bonus (a roll that adds the full bonus gains nothing from half)."""
    values = _numeric(insts, "initiative")
    return sum(v for v in values if isinstance(v, int)), any(v == "pb" for v in values)


def hp_bonus(insts: list[dict], total_level: int) -> int:
    """Tough: twice the character level when gained plus 2 per later level = 2 x current level."""
    return (sum(_numeric(insts, "hp_per_level")) * total_level) + sum(_numeric(insts, "hp_flat"))


def walk_bonus(insts: list[dict]) -> int:
    return sum(_numeric(insts, "walk_bonus"))


def climb_equals_walk(insts: list[dict]) -> bool:
    return any(_numeric(insts, "climb_equals_walk"))


# ---------------------------------------------------------------- FE4: AC, passive scores, Stealth, senses


def ac_formulas(insts: list[dict]) -> list[dict]:
    """Alternative unarmored AC formulas from feats (Dragon Hide). They join the class-feature formulas and
    compete with them; the best candidate wins, never summed (PHB 2024 multiclassing: one way to
    calculate AC at a time)."""
    return _numeric(insts, "ac_formula")


def medium_armor_dex_cap(insts: list[dict], dex_score: int) -> int | None:
    """Medium Armor Master: the DEX bonus cap of medium armor (3 rather than 2) when the Dexterity
    SCORE is high enough; None when no feat applies."""
    caps = [c["cap"] for c in _numeric(insts, "medium_armor_dex_cap") if dex_score >= c["min_dex_score"]]
    return max(caps, default=None)


def medium_armor_stealth_ok(insts: list[dict]) -> bool:
    """Medium Armor Master (PHB): medium armor imposes no Stealth disadvantage."""
    return any(_numeric(insts, "medium_armor_stealth_ok"))


def _melee_one_handed_weapon(item: dict | None) -> bool:
    return bool(item and (item.get("equipment_category") or {}).get("index") == "weapon"
                and item.get("weapon_range") == "Melee"
                and not any(p.get("index") == "two-handed" for p in item.get("properties", [])))


def _wielded_ok(condition, hands: dict | None, items: list[dict]) -> bool:
    """Does ``equipment.wielded`` prove the condition? Without it (``hands`` is None) nothing is proven (F-D3)."""
    if not hands:
        return False
    by_id = {i["index"]: i for i in items}
    main, off = by_id.get(hands.get("main")), by_id.get(hands.get("off"))
    if condition == "two-melee":
        # "a separate melee weapon in each hand": two one-handed melee weapons (two copies of one weapon count).
        return _melee_one_handed_weapon(main) and _melee_one_handed_weapon(off)
    if isinstance(condition, dict):
        held = [i for i in (hands.get("main"), hands.get("off")) if i]
        # "holding a <item> with two hands": it is the only thing held, so both hands are on it.
        return held == [condition["item"]] and condition.get("two_hands", False)
    return False


def ac_bonus(insts: list[dict], hands: dict | None, items: list[dict]) -> int:
    """Flat AC bonuses whose condition the wielded hands prove (Dual Wielder PHB, Revenant Blade)."""
    return sum(c["bonus"] for c in _numeric(insts, "ac_bonus_if") if _wielded_ok(c["wielded"], hands, items))


def passive_bonus(insts: list[dict]) -> dict[str, int]:
    """{skill id: bonus} to passive scores only (Observant PHB); never to ``derived.skills``."""
    out: dict[str, int] = {}
    for bonus in _numeric(insts, "passive_bonus"):
        for skill, value in bonus.items():
            out[skill] = out.get(skill, 0) + value
    return out


def add_senses(senses: dict[str, int], insts: list[dict]) -> dict[str, int]:
    """Additive senses (Keenness of the Stone Giant): the range is added to an existing range of that
    sense, else it is the range itself. Call after every other source so the rule reads the final range."""
    out = dict(senses)
    for extra in _numeric(insts, "senses_additive"):
        for sense, value in extra.items():
            out[sense] = out.get(sense, 0) + value
    return out


# ---------------------------------------------------------------- FE3: notes and resources

_ABILITIES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
_PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


def numbers_for(modifiers: dict, scores: dict, prof_bonus: int, total_level: int) -> dict:
    """Names a note template may use: ``pb``, ``level``, ``<abl>_mod`` and ``<abl>_score`` (lowercase)."""
    env = {"pb": prof_bonus, "level": total_level}
    for ability in _ABILITIES:
        if ability in modifiers:
            env[f"{ability.lower()}_mod"] = modifiers[ability]
        if ability in scores:
            env[f"{ability.lower()}_score"] = scores[ability]
    return env


def _eval(node, env: dict):
    """Safe integer arithmetic: + - * //, max/min, numbers and names of ``env``. None = a name that is
    not known yet (``inc_mod`` of a feat whose ability is still to be chosen). Anything else raises."""
    if isinstance(node, ast.Expression):
        return _eval(node.body, env)
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise KeyError(node.id)
        return env[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)):
        left, right = _eval(node.left, env), _eval(node.right, env)
        if left is None or right is None:
            return None
        return {ast.Add: left + right, ast.Sub: left - right, ast.Mult: left * right,
                ast.FloorDiv: left // right if right else 0}[type(node.op)]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("max", "min")
            and not node.keywords):
        values = [_eval(a, env) for a in node.args]
        return None if any(v is None for v in values) else (max if node.func.id == "max" else min)(values)
    raise ValueError(f"unsupported note expression: {ast.dump(node)}")


def render(template: str, env: dict) -> str:
    """Format a note template. ``{expr}`` is replaced by the value, ``{sum:a,b}`` by ``a + b = total``.
    A placeholder that needs the increased ability before it is chosen renders ``CHOOSE_ABILITY``;
    an unknown name raises (it is a data bug, caught by the data guard tests)."""
    def sub(match):
        body = match.group(1)
        if body.startswith("sum:"):
            values = [_eval(ast.parse(part.strip(), mode="eval"), env) for part in body[4:].split(",")]
            if any(v is None for v in values):
                return CHOOSE_ABILITY
            return " + ".join(str(v) for v in values) + f" = {sum(values)}"
        value = _eval(ast.parse(body.strip(), mode="eval"), env)
        return CHOOSE_ABILITY if value is None else str(value)
    return _PLACEHOLDER.sub(sub, template)


def _env(inst: dict, numbers: dict) -> dict:
    env = dict(numbers)
    if inst["increased"]:
        env["inc_mod"] = numbers.get(f"{inst['increased'].lower()}_mod")
    else:
        env["inc_mod"] = None
    return env


def notes(insts: list[dict], numbers: dict) -> dict[str, list[str]]:
    """{instance prefix: formatted notes} for the instances that have any."""
    out = {}
    for inst in insts:
        texts = inst["effect"].get("notes")
        if texts:
            env = _env(inst, numbers)
            out[inst["prefix"]] = [render(t, env) for t in texts]
    return out


def _slug(text: str) -> str:
    return "-".join("".join(ch if ch.isalnum() else " " for ch in text.lower()).split())


def resources(insts: list[dict], numbers: dict) -> list[dict]:
    """``derived.featResources``: the class-resource shape with ``featId`` instead of ``classId`` and
    ``source.kind == "feat"``. Uses are an int or ``"pb"`` (the Proficiency Bonus). One entry per
    feat instance (the id is scoped by the instance prefix, so a repeatable feat never collides)."""
    out = []
    for inst in insts:
        for res in inst["effect"].get("resources") or []:
            uses = numbers["pb"] if res["uses"] == "pb" else res["uses"]
            entry = {"id": f"{inst['prefix']}:{_slug(res['name'])}", "featId": inst["index"],
                     "source": {"kind": "feat", "id": inst["index"], "label": inst["feat"]["name"]},
                     "name": res["name"], "uses": uses, "recharge": res.get("recharge")}
            if res.get("note"):
                entry["details"] = {"note": res["note"]}
            out.append(entry)
    return out


# ---------------------------------------------------------------- FE5: attack rows

_DIE = re.compile(r"(\d+)d(\d+)")
_DMG_PLACEHOLDER = re.compile(r"\{dmg:(\d+d\d+)\}")


def attack_flags(insts: list[dict]) -> dict:
    """Flags merged into ``features.attack_styles(...)`` for ``attacks.weapon_attack``: the off-hand attack of
    Dual Wielder (PHB: non-Light one-handed melee; XPHB: any melee weapon without Two-Handed), Crossbow Expert
    (XPHB: the modifier on the Light crossbow's extra attack) and Revenant Blade's Finesse items."""
    offhand = _numeric(insts, "offhand")
    return {
        "offhand_non_light": any(o.get("non_light_one_handed_melee") for o in offhand),
        "offhand_dw2024": any(o.get("dw2024") for o in offhand),
        "offhand_light_crossbow_mod": any(o.get("light_crossbow_mod") for o in offhand),
        "finesse_items": frozenset(i for items in _numeric(insts, "finesse_items") for i in items),
    }


def _sides(die: str | None) -> int:
    match = re.search(r"d(\d+)", die or "")
    return int(match.group(1)) if match else 0


def _full_die(die: str | None) -> str:
    return die if die and die[0].isdigit() else f"1{die}"


def _holds_weapon_or_shield(hands: dict | None, items: list[dict]) -> bool:
    """True unless ``equipment.wielded`` proves both hands hold nothing that is a weapon or a Shield. Without
    ``wielded`` (``hands`` is None) nothing is proven, so the answer is True (F-D3 style)."""
    if hands is None:
        return True
    by_id = {i["index"]: i for i in items}
    for held in (hands.get("main"), hands.get("off")):
        if held is None:
            continue
        item = by_id.get(held)
        if item is None or (item.get("equipment_category") or {}).get("index") == "weapon" \
                or item.get("armor_category") == "Shield":
            return True
    return False


def unarmed_spec(insts: list[dict], hands: dict | None, items: list[dict], martial_arts_die: str | None,
                 monk: bool = False) -> dict | None:
    """F-D6: the Unarmed Strike row exists when a held feat improves it (Tavern Brawler, Unarmed Fighting, Dragon
    Hide). Returns ``{die, type, notes}`` for ``attacks.unarmed_strike`` or None. The best die wins; on a tie the
    Monk's Martial Arts (``die`` None) comes first, then the feats in the order held; the others are listed in
    the notes. Unarmed Fighting's d6 becomes a d8 when ``wielded`` proves no weapon or Shield is held."""
    entries = _numeric(insts, "unarmed")
    if not entries:
        return None
    cands = []
    if monk:
        cands.append((_sides(martial_arts_die), 0, {"name": "Martial Arts", "die": None, "type": "bludgeoning",
                                                      "notes": ["Martial Arts"]}))
    holds = _holds_weapon_or_shield(hands, items)
    for rank, entry in enumerate(entries, 1):
        die, notes = entry["die"], list(entry["notes"])
        free = entry.get("die_free_hands")
        if free and not holds:
            die = free
            notes.insert(0, f"{entry['name']}: {free} because no weapon or Shield is held")
        elif free:
            notes.insert(0, f"{entry['name']}: the {die} becomes a {free} when no weapon or Shield is held")
        cands.append((_sides(die), rank, {"name": entry["name"], "die": die, "type": entry["type"], "notes": notes}))
    cands.sort(key=lambda c: (-c[0], c[1]))
    best, others = cands[0][2], [c[2] for c in cands[1:]]
    notes = list(best["notes"])
    for other in others:
        notes.append(f"Alternative: {other['name']} {_full_die(other['die'] or martial_arts_die)} {other['type']}")
    return {"die": best["die"], "type": best["type"], "notes": notes}


def _facts(row: dict, item: dict | None) -> dict:
    props = {p["index"] for p in (item or {}).get("properties", [])}
    return {"melee": (item.get("weapon_range") == "Melee") if item else True,
            "ranged": (item.get("weapon_range") == "Ranged") if item else False,
            "weapon": item is not None, "props": props}


def _matches(when: dict, row: dict, facts: dict) -> bool:
    props = facts["props"]
    for key, want in when.items():
        if key in ("melee", "ranged", "weapon"):
            if facts[key] != want:
                return False
        elif key == "properties":
            if not set(want.get("all", ())) <= props or (want.get("any") and not set(want["any"]) & props):
                return False
        elif key == "lacks":
            if set(want) & props:
                return False
        elif key == "damage_types":
            if row.get("damageType") not in want:
                return False
        elif key == "items":
            if row["itemId"] not in want:
                return False
        elif key == "ability_in":
            if row["ability"] not in want:
                return False
        elif key == "proficient":
            if bool(row["proficient"]) != want:
                return False
        elif key == "damaging":
            if (row.get("damage") is not None) != want:
                return False
        else:
            raise ValueError(f"unknown attack predicate: {key}")
    return True


def _signed(dice: str, mod: int) -> str:
    return dice if mod == 0 else f"{dice}{mod:+d}"


def row_note(text: str, env: dict, row: dict) -> str:
    """Fill a note template for an attack row: ``{dmg:XdY}``, ``{die}`` and ``{dtype}`` first, then FE3's ``render``
    (``{pb}``, ``{mod}``, ``{inc_mod}``, ``{inc_score}``, arithmetic)."""
    mod = env.get(f"{row['ability'].lower()}_mod") if row.get("ability") else 0
    first = _DIE.search(row.get("damage") or "")
    text = _DMG_PLACEHOLDER.sub(lambda m: _signed(m.group(1), mod or 0), text)
    text = text.replace("{die}", f"1d{first.group(2)}" if first else "").replace("{dtype}", row.get("damageType") or "")
    return render(text, {**env, "mod": mod or 0})


def annotate_attacks(attacks: list[dict], items: list[dict], insts: list[dict], numbers: dict) -> list[dict]:
    """Append the feats' attack-row notes (F-D2) with the character's numbers. Notes are information: ``damage`` is
    unchanged. Rows without a catalog item (the Unarmed Strike) match as melee, non-weapon rows. A feat's notes are
    taken once per feat name (the edition-independent key)."""
    owners, seen = [], set()
    for inst in insts:
        if "attack_notes" in inst["effect"] and _name_key(inst["feat"]) not in seen:
            seen.add(_name_key(inst["feat"]))
            owners.append(inst)
    if not owners:
        return attacks
    catalog_items = {i["index"]: i for i in items}
    out = []
    for row in attacks:
        facts = _facts(row, catalog_items.get(row["itemId"]))
        notes = list(row["notes"])
        for inst in owners:
            env = _env(inst, numbers)
            env["inc_score"] = numbers.get(f"{inst['increased'].lower()}_score") if inst["increased"] else None
            for entry in inst["effect"]["attack_notes"]:
                when = entry["when"]
                if any(_matches(w, row, facts) for w in (when if isinstance(when, list) else [when])):
                    text = row_note(entry["text"], env, row)
                    if text not in notes:
                        notes.append(text)
        out.append({**row, "notes": notes})
    return out
