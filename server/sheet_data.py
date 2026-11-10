"""The data of the fillable sheet: a Resolution (+ catalog, language) -> ordered field values (SHEET-S4).

Pure: no drawing, no PDF, no pypdf, no I/O. ``build_sheet_data(resolution, catalog, lang)`` returns a ``SheetData``:

* ``values``: one ``FieldValue`` per field of ``sheet_layout.FIELDS``, in layout order (text, or True / False for a
  checkbox); a box the player fills in by hand is the empty string.
* ``flow``: the blocks of the features flow (pages 2-3, three columns each) followed by the leftovers of the small
  boxes of pages 1 and 4 that did not fit ("... (continued)"); the renderer splits them over the columns.
* ``overflow``: leftover blocks of the big text boxes of page 4 (backstory, notes) for the notes continuation pages.
* ``equipment_overflow``: equipment rows beyond the 56 of pages 2-3.
* ``spell_groups``: per spellcasting class (and the innate spells) the header values and the ordered rows (level
  headers and one row per spell) of the spell pages.
* ``coverage``: for every feature / feat of the character whether a description was found.

Descriptions are looked up in the catalog by name, level and edition and printed only when the match is certain
("no description rather than a wrong one"). Game terms from the data (class, spell, item names) stay English; every
word of ours comes from ``export_labels`` (family ``LABELS[lang]["sheet"]`` and the older labels).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import sheet_layout as L
from catalog.reference_data import LANGUAGE_NAMES, SKILL_ABILITY, SKILL_NAMES, proficiency_label
from export_fields import _DAMAGE_SECTIONS, _title, fmt_mod, fmt_spell_slots, resource_line, species_label
from export_labels import DEFAULT_LANG, check_lang, label, sheet_label, weight, word

STANDARD_ACTIONS = ("Attack", "Dash", "Disengage", "Dodge", "Help", "Hide", "Influence", "Magic", "Ready", "Search",
                    "Study", "Utilize")
MARK_PROFICIENT, MARK_EXPERT, MARK_SAVE = "P", "E", "●"
SMALL_FONT = 6.0  # Letter points: the smallest size a text box shrinks to before text continues elsewhere
CHAR_WIDTH_EM = 0.58  # average character width of DejaVu Sans in em (a conservative estimate for the overflow split)
LEADING = 1.2
EQUIPMENT_FIELD_ROWS = L.EQUIPMENT_ROWS
WEAPON_ROWS = 6


@dataclass(frozen=True)
class FieldValue:
    name: str
    value: str | bool


@dataclass(frozen=True)
class FlowBlock:
    kind: str  # "heading" | "title" | "text"
    text: str


@dataclass(frozen=True)
class SpellRow:
    kind: str  # "header" | "spell"
    cells: dict  # header: {"Name": text}; spell: column key -> text (see sheet_layout.SPELL_COLUMNS)
    level: int = 0


@dataclass(frozen=True)
class SpellGroup:
    key: str  # class id, or "innate"
    title: str
    ability: str
    save_dc: str
    attack: str
    slots: str
    rows: tuple[SpellRow, ...]


@dataclass(frozen=True)
class Coverage:
    kind: str
    name: str
    level: int | None
    described: bool


@dataclass(frozen=True)
class SheetData:
    lang: str
    values: tuple[FieldValue, ...]
    flow: tuple[FlowBlock, ...]
    overflow: dict
    equipment_overflow: tuple[tuple[str, str, str], ...]
    spell_groups: tuple[SpellGroup, ...]
    coverage: tuple[Coverage, ...]

    def as_dict(self) -> dict[str, str | bool]:
        return {v.name: v.value for v in self.values}


# ---------------------------------------------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------------------------------------------
_TAG = re.compile(r"\{@(\w+)(?: ([^{}]*))?\}")


def strip_tags(text: str) -> str:
    """5etools inline tags -> plain text: ``{@spell fire bolt|phb}`` -> ``fire bolt``, ``{@dc 13}`` -> ``DC 13``."""
    def one(m: re.Match) -> str:
        tag, body = m.group(1), m.group(2) or ""
        parts = body.split("|")
        shown = parts[2] if len(parts) > 2 and parts[2] else parts[0]
        if tag == "dc":
            return f"DC {parts[0]}"
        if tag == "hit":
            return fmt_mod(int(parts[0])) if re.fullmatch(r"-?\d+", parts[0]) else parts[0]
        if tag == "h":
            return "Hit: "
        if tag == "atk":
            return {"mw": "Melee Weapon Attack:", "rw": "Ranged Weapon Attack:", "ms": "Melee Spell Attack:",
                    "rs": "Ranged Spell Attack:"}.get(parts[0], "Attack:")
        if tag == "recharge":
            return f"(Recharge {parts[0] or 6})"
        return shown

    prev = None
    while prev != text:  # tags may nest
        prev, text = text, _TAG.sub(one, text)
    return text


def flatten_entries(entries, depth: int = 0) -> list[str]:
    """5etools ``entries`` (strings and nested objects) -> plain paragraphs."""
    out: list[str] = []
    if isinstance(entries, str):
        return [strip_tags(entries)]
    if not isinstance(entries, list):
        return out
    for e in entries:
        if isinstance(e, str):
            out.append(strip_tags(e))
        elif isinstance(e, dict):
            kind = e.get("type")
            if kind in ("entries", "section", "inset", "insetReadaloud", "quote", "item", "itemSub", "variant"):
                inner = flatten_entries(e.get("entries") if "entries" in e else e.get("entry", []), depth + 1)
                name = e.get("name")
                if name and inner:
                    inner[0] = f"{strip_tags(name)}. {inner[0]}"
                out.extend(inner)
            elif kind == "list":
                for item in e.get("items", []):
                    out.extend("- " + t for t in flatten_entries([item] if not isinstance(item, list) else item, depth + 1))
            elif kind == "table":
                if e.get("caption"):
                    out.append(strip_tags(e["caption"]))
                heads = [strip_tags(str(h)) for h in e.get("colLabels", [])]
                if heads:
                    out.append(" | ".join(heads))
                for row in e.get("rows", []):
                    out.append(" | ".join(strip_tags(c) if isinstance(c, str) else " ".join(flatten_entries([c])) for c in row))
    return out


def lines_estimate(text: str, width: float, size: float) -> int:
    """Rough number of wrapped lines of ``text`` in a box ``width`` Letter points wide at ``size``."""
    per_line = max(1, int((width - 4.0) / (size * CHAR_WIDTH_EM)))
    return sum(max(1, math.ceil(len(line) / per_line)) for line in text.split("\n"))


def capacity_lines(rect: L.Rect, size: float) -> int:
    return max(1, int((rect[3] - rect[1] - 4.0) / (size * LEADING)))


def fill_box(blocks: list[str], rect: L.Rect, size: float = SMALL_FONT) -> tuple[list[str], list[str]]:
    """(blocks that fit the box at the smallest size, the rest). A single block taller than the box is cut by words."""
    width = rect[2] - rect[0]
    room = capacity_lines(rect, size)
    taken: list[str] = []
    for i, block in enumerate(blocks):
        need = lines_estimate(block, width, size) + (1 if taken else 0)
        if need <= room:
            taken.append(block)
            room -= need
            continue
        if not taken and room > 1:  # the first block alone is too big: keep its first lines
            words, cut = block.split(" "), []
            while words and lines_estimate(" ".join(cut + [words[0]]), width, size) <= room:
                cut.append(words.pop(0))
            if cut and words:
                return [" ".join(cut)], [" ".join(words)] + blocks[i + 1:]
        return taken, blocks[i:]
    return taken, []


# ---------------------------------------------------------------------------------------------------------------
# catalog lookups (descriptions)
# ---------------------------------------------------------------------------------------------------------------
def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name or "").strip().casefold()


def _is_2024(record_id: str) -> bool:
    return "xphb" in (record_id or "")


class _Descriptions:
    def __init__(self, catalog, sheet: dict, ruleset: str):
        self.catalog, self.sheet, self.ruleset = catalog, sheet, ruleset
        self.by_class: dict[tuple[str, str], list[dict]] = {}
        classes = {c["id"] for c in sheet.get("classes") or []}
        for rec in getattr(catalog, "features", {}).values():
            cls = (rec.get("class") or {}).get("index")
            if cls in classes:
                self.by_class.setdefault((cls, _norm(rec.get("name", ""))), []).append(rec)
        self.subclasses = {c["id"]: (c.get("subclass") or {}).get("id") or (c.get("subclass") or {}).get("name")
                           for c in sheet.get("classes") or []}
        self.traits: dict[str, list[dict]] = {}
        for rec in getattr(catalog, "traits", {}).values():
            self.traits.setdefault(_norm(rec.get("name", "")), []).append(rec)

    @staticmethod
    def _pick(records: list[dict], ruleset: str) -> list[str] | None:
        """The one description the records agree on, preferring the character's edition (never the other one under
        a strict ruleset); None when there is none or the candidates differ."""
        def texts(group):
            return {tuple(strip_tags(p) for p in r.get("desc") or []) for r in group if r.get("desc")}
        new = [r for r in records if _is_2024(r.get("index", ""))]
        old = [r for r in records if not _is_2024(r.get("index", ""))]
        if ruleset in ("2024", "2014"):
            found = texts(new if ruleset == "2024" else old)
            return list(next(iter(found))) if len(found) == 1 else None
        # the edition is unknown ("mixed" or not given): only when both editions say the same, or only one exists
        found = texts(new) | texts(old)
        return list(next(iter(found))) if len(found) == 1 else None

    def feature(self, entry: dict) -> list[str] | None:
        kind, source = entry["source"]["kind"], entry["source"]
        name = _norm(entry["name"])
        if kind == "class":
            records = [r for r in self.by_class.get((source["id"], name), [])
                       if r.get("level") == entry.get("level")
                       and (not (r.get("subclass") or {}).get("index") or (r["subclass"]["index"] == self.subclasses.get(source["id"])))]
            return self._pick(records, self.ruleset)
        if kind == "species":
            species = self.sheet.get("species") or {}
            ids = {species.get("id"), (species.get("subspecies") or {}).get("id")} - {None}
            records = [r for r in self.traits.get(name, [])
                       if ids & {x.get("index") for x in (r.get("races") or []) + (r.get("subraces") or [])}]
            return self._pick(records, self.ruleset) if records else None
        if kind == "background":
            bg = getattr(self.catalog, "backgrounds", {}).get(source["id"]) or {}
            feature = bg.get("feature") or {}
            if _norm(feature.get("name", "")) == name and feature.get("desc"):
                return [strip_tags(p) for p in feature["desc"]]
        return None

    def feat(self, entry: dict) -> list[str] | None:
        rec = getattr(self.catalog, "feats", {}).get(entry.get("id"))
        if rec and _norm(rec.get("name", "")) == _norm(entry.get("name", "")):
            paragraphs = flatten_entries(rec.get("entries") or rec.get("desc") or [])
            return paragraphs or None
        return None


# ---------------------------------------------------------------------------------------------------------------
# spells
# ---------------------------------------------------------------------------------------------------------------
def compact_time(text: str) -> str:
    t = (text or "").strip().lower()
    for prefix, code in (("1 bonus action", "1BA"), ("1 action", "1A"), ("1 reaction", "1R")):
        if t.startswith(prefix):
            return code if t == prefix or t.startswith(prefix + ",") else (code if "or" not in t else text)
    m = re.fullmatch(r"(\d+) (minute|hour|day)s?", t)
    if m:
        return f"{m.group(1)}{ {'minute': 'm', 'hour': 'h', 'day': 'd'}[m.group(2)] }"
    return text or "--"


def compact_range(text: str) -> str:
    t = (text or "--").replace("-foot", "-ft.").replace(" feet", " ft.").replace(" foot", " ft.").replace(" miles", " mi.").replace(" mile", " mi.")
    return t


def compact_duration(text: str, concentration: bool) -> str:
    t = re.sub(r"^concentration, ", "", (text or "--"), flags=re.I)
    t = re.sub(r"^up to ", "", t, flags=re.I)
    t = (t.replace("Instantaneous", "Inst.").replace(" minutes", " min").replace(" minute", " min").replace(" hours", " hr")
          .replace(" hour", " hr").replace(" rounds", " rnd").replace(" round", " rnd").replace("Until dispelled", "Until disp."))
    return ("C " + t) if concentration else t


def _spell_record(catalog, spell_id: str):
    sid = catalog.resolve_spell_id(spell_id) if hasattr(catalog, "resolve_spell_id") else spell_id
    return catalog.spells.get(sid or spell_id)


def _cantrip_dice(spell: dict, level: int) -> str:
    table = (spell.get("damage") or {}).get("damage_at_character_level") or {}
    best = ""
    for k in sorted(table, key=int):
        if int(k) <= level:
            best = table[k]
    return best


def _save_or_attack(spell: dict, attack_bonus: str) -> str:
    dc = (spell.get("dc") or {}).get("dc_type") or {}
    if dc.get("index"):
        return str(dc["index"]).upper()
    if spell.get("spell_attack") or spell.get("attack_type"):
        return attack_bonus or "ATK"
    return "--"


def _spell_cells(spell: dict | None, name: str, attack_bonus: str) -> dict:
    if not spell:
        return {"Name": name, "Save": "--", "Time": "--", "Range": "--", "Comp": "--", "Duration": "--", "Ref": ""}
    return {
        "Name": name, "Save": _save_or_attack(spell, attack_bonus), "Time": compact_time(spell.get("casting_time", "")),
        "Range": compact_range(spell.get("range", "")), "Comp": ",".join(spell.get("components") or []) or "--",
        "Duration": compact_duration(spell.get("duration", ""), bool(spell.get("concentration"))),
        "Ref": str(spell.get("source", "SRD")),
    }


def _spell_groups(resolution: dict, catalog, lang: str) -> tuple[SpellGroup, ...]:
    sheet, derived = resolution["sheet"], resolution["derived"]
    names = {c["id"]: c["name"] for c in sheet.get("classes") or []}
    groups: list[SpellGroup] = []
    slots = ", ".join(x for x in (fmt_spell_slots(derived.get("spellSlots") or {}, lang),
                                  fmt_spell_slots(derived.get("warlockSpellSlots") or {}, lang)) if x)
    for entry in sheet.get("spells") or []:
        cls_id = entry["classId"]
        ability = _casting_ability(catalog, cls_id)
        attack = fmt_mod(entry["spellAttackBonus"]) if entry.get("spellAttackBonus") is not None else ""
        rows: dict[str, dict] = {}  # spell id -> merged row
        order: list[str] = []

        def add(item: dict, prep: str, note: str = "", source: str = "") -> None:
            sid = item["id"]
            if sid not in rows:
                spell = _spell_record(catalog, sid)
                cells = _spell_cells(spell, item["name"], attack)
                cells.update({"Prep": "", "Source": source or names.get(cls_id, cls_id), "Notes": [], "_level": item["level"]})
                if spell and spell.get("ritual"):
                    cells["Notes"].append("R")
                rows[sid] = cells
                order.append(sid)
            row = rows[sid]
            if prep == "P" or (prep == "O" and row["Prep"] != "P"):
                row["Prep"] = prep
            if note and note not in row["Notes"]:
                row["Notes"].append(note)

        for s in entry.get("cantrips") or []:
            add(s, "")
        for s in entry.get("spellbook") or []:
            add(s, "", sheet_label(lang, "noteSpellbook"))
        for s in entry.get("known") or []:
            add(s, "O")
        for s in entry.get("alwaysPrepared") or []:
            add(s, "P", sheet_label(lang, "noteAlways"))
        for key in ("mysticArcanum", "spellMastery", "signatureSpells", "pactOfTheTome"):
            for s in entry.get(key) or []:
                add(s, "P", label(lang, key))
        grouped: dict[int, list[str]] = {}
        for sid in order:
            grouped.setdefault(rows[sid]["_level"], []).append(sid)
        out: list[SpellRow] = []
        for lvl in sorted(grouped):
            head = sheet_label(lang, "headSpellCantrips") if lvl == 0 else sheet_label(lang, "headSpellLevel", lvl=lvl)
            out.append(SpellRow("header", {"Name": head}, lvl))
            for sid in sorted(grouped[lvl], key=lambda i: rows[i]["Name"].casefold()):
                r = rows[sid]
                cells = {k: v for k, v in r.items() if k not in ("Notes", "_level")}
                cells["Notes"] = ", ".join(r["Notes"])
                out.append(SpellRow("spell", cells, lvl))
        groups.append(SpellGroup(cls_id, names.get(cls_id, cls_id), ability.upper(),
                                 str(entry["spellSaveDC"]) if entry.get("spellSaveDC") is not None else "", attack, slots, tuple(out)))
    innate = sheet.get("innateSpells") or []
    if innate:
        out = [SpellRow("header", {"Name": sheet_label(lang, "headInnate")}, 0)]
        seen: set[str] = set()
        for e in sorted(innate, key=lambda x: (x.get("level") or 0, x["name"].casefold())):
            key = e.get("id") or e["name"]
            if key in seen:
                continue
            seen.add(key)
            spell = _spell_record(catalog, e.get("id") or e["name"])
            cells = _spell_cells(spell, e["name"], "")
            notes = [x for x in (str(e.get("uses") or ""), e.get("note") or "") if x]
            cells.update({"Prep": "P", "Source": sheet_label(lang, "noteInnate"), "Notes": ", ".join(notes)})
            out.append(SpellRow("spell", cells, (spell or {}).get("level", 0)))
        groups.append(SpellGroup("innate", sheet_label(lang, "headInnate").strip("= "), "", "", "", "", tuple(out)))
    return tuple(groups)


def _casting_ability(catalog, class_id: str) -> str:
    rec = (getattr(catalog, "classes_2024", {}) or {}).get(class_id) or {}
    sc = rec.get("spellcasting") or (getattr(catalog, "classes", {}).get(class_id) or {}).get("spellcasting") or {}
    return (sc.get("spellcasting_ability") or {}).get("index", "") or ""


# ---------------------------------------------------------------------------------------------------------------
# the field map
# ---------------------------------------------------------------------------------------------------------------
def _equipment_rows(resolution: dict, catalog) -> list[tuple[str, str, str]]:
    eq = resolution["sheet"].get("equipment") or {}
    rows: list[tuple[str, str, str]] = []

    def weight_of(item_id: str, qty: int) -> str:
        w = (catalog.items.get(item_id) or {}).get("weight")
        if not isinstance(w, (int, float)) or isinstance(w, bool) or w == 0:
            return "--"
        total = w * qty
        return f"{int(total) if float(total).is_integer() else total} lb"

    for key in ("granted", "chosen", "added"):
        for e in eq.get(key) or []:
            if e.get("contents"):  # a pack is listed by what is in it
                for c in e["contents"]:
                    rows.append((c["name"], str(c.get("qty", 1)), weight_of(c["itemId"], c.get("qty", 1))))
                continue
            rows.append((e["name"], str(e.get("qty", 1)), weight_of(e["itemId"], e.get("qty", 1))))
    for item in eq.get("narrativeItems") or []:
        rows.append((str(item), "", "--"))
    return rows


def _weapon_rows(resolution: dict, catalog, lang: str) -> list[tuple[str, str, str, str]]:
    rows = []
    for a in resolution["derived"].get("attacks") or []:
        damage = ""
        if a.get("damage"):
            damage = f"{a['damage']} {word(lang, 'damage', a['damageType'])}" if a.get("damageType") else a["damage"]
        notes = []
        if a.get("versatileDamage"):
            notes.append(label(lang, "attackVersatile", dice=a["versatileDamage"]))
        if a.get("duelingDamage"):
            notes.append(label(lang, "attackDueling", dice=a["duelingDamage"]))
        if a.get("offhandDamage"):
            notes.append(label(lang, "attackOffhand", dice=a["offhandDamage"]))
        if a.get("range"):
            notes.append(label(lang, "attackRange", range=a["range"]))
        notes.extend(a.get("notes") or [])
        if a.get("mastery"):
            notes.append(label(lang, "attackMastery", mastery=a["mastery"]))
        rows.append((a["name"], fmt_mod(a["attackBonus"]), damage, ", ".join(notes)))
    sheet = resolution["sheet"]
    level = sheet.get("level") or 1
    for entry in sheet.get("spells") or []:  # attack / save cantrips follow the weapons
        attack = fmt_mod(entry["spellAttackBonus"]) if entry.get("spellAttackBonus") is not None else ""
        dc = entry.get("spellSaveDC")
        for s in entry.get("cantrips") or []:
            spell = _spell_record(catalog, s["id"])
            if not spell or not (spell.get("damage") or spell.get("damage_inflict") or spell.get("dc") or spell.get("spell_attack")):
                continue
            how = _save_or_attack(spell, attack)
            hit = how if how in ("--",) or how.startswith(("+", "-")) else f"{how} {dc}" if dc is not None else how
            dice = _cantrip_dice(spell, level)
            types = [word(lang, "damage", t) for t in (spell.get("damage_inflict") or [(spell.get("damage") or {}).get("damage_type", {}).get("index")]) if t]
            damage = f"{dice} {', '.join(types)}".strip()
            rows.append((s["name"], hit, damage, compact_range(spell.get("range", ""))))
    return rows


def _skill_rows(resolution: dict) -> dict[str, tuple[str, str, str]]:
    sheet, derived = resolution["sheet"], resolution["derived"]
    prof = set(sheet["proficiencies"].get("skills") or [])
    expert = set(sheet.get("expertiseSkills") or [])
    out = {}
    for skill in L.SKILLS:
        sid = "skill-" + re.sub(r"(?<!^)([A-Z])", r"-\1", skill).lower()
        mark = MARK_EXPERT if sid in expert else MARK_PROFICIENT if sid in prof else ""
        value = derived["skills"].get(sid)
        out[skill] = (mark, fmt_mod(value) if value is not None else "", SKILL_ABILITY.get(sid, ""))
    return out


def _defenses(sheet: dict, lang: str) -> list[str]:
    blocks = []
    damage = sheet.get("damageModifiers") or {}
    for key, label_key in _DAMAGE_SECTIONS:
        if damage.get(key):
            blocks.append(f"{label(lang, label_key)}: " + ", ".join(_title(d) for d in damage[key]))
    if sheet.get("conditionImmunities"):
        blocks.append(f"{label(lang, 'conditionImmunities')}: " + ", ".join(_title(c) for c in sheet["conditionImmunities"]))
    return blocks


def _paragraphs(text: str | None) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]


def build_sheet_data(resolution: dict, catalog, lang: str = DEFAULT_LANG, ruleset: str | None = None) -> SheetData:
    """``ruleset`` ("2014" / "2024" / "mixed") is the draft's; the resolution does not carry it. With "2014" or "2024"
    the feature text of that edition is used; otherwise a description is printed only when it is unambiguous."""
    check_lang(lang)
    sheet, derived = resolution["sheet"], resolution["derived"]
    ruleset = ruleset or "mixed"
    feet = lambda n: label(lang, "feet", n=n)  # noqa: E731
    v: dict[str, str | bool] = {}
    blocks: dict[str, list[str]] = {}  # multi field -> blocks (paragraph groups)

    # identity
    v["CharacterName"] = sheet.get("name") or ""
    classes = sheet.get("classes") or []
    v["ClassLevel"] = " / ".join(
        f"{c['name']} {c['level']}" + (f" ({c['subclass']['name']})" if c.get("subclass") else "") for c in classes)
    v["Species"] = species_label(sheet.get("species")) if sheet.get("species") else ""
    v["Background"] = (sheet.get("background") or {}).get("name", "")

    # abilities, saves, skills
    mods, saves = derived.get("abilityModifiers") or {}, derived.get("savingThrows") or {}
    save_prof = set((sheet.get("proficiencies") or {}).get("savingThrows") or [])
    for a in L.ABILITIES:
        ab = a.upper()
        v[f"Ability{a}"] = str((sheet.get("abilities") or {}).get(ab, ""))
        v[f"Ability{a}Mod"] = fmt_mod(mods[ab]) if ab in mods else ""
        v[f"Save{a}Mark"] = MARK_SAVE if ab in save_prof else ""
        v[f"Save{a}"] = fmt_mod(saves[ab]) if ab in saves else ""
    for skill, (mark, value, ability) in _skill_rows(resolution).items():
        v[f"Skill{skill}Mark"], v[f"Skill{skill}"], v[f"Skill{skill}Ability"] = mark, value, ability
    v["PassivePerception"] = str(derived.get("passivePerception", ""))
    v["PassiveInsight"] = str(derived.get("passiveInsight", ""))
    v["PassiveInvestigation"] = str(derived.get("passiveInvestigation", ""))
    blocks["Senses"] = [f"{word(lang, 'senses', k)} {feet(n)}" for k, n in (sheet.get("senses") or {}).items()]

    # combat block
    v["Initiative"] = fmt_mod(derived["initiative"]) if derived.get("initiative") is not None else ""
    v["ArmorClass"] = str(derived.get("armorClass", ""))
    blocks["Defenses"] = _defenses(sheet, lang)
    v["Inspiration"] = False
    v["ProficiencyBonus"] = fmt_mod(derived["proficiencyBonus"]) if derived.get("proficiencyBonus") is not None else ""
    for i, entry in enumerate((sheet.get("spells") or [])[:2], start=1):
        if entry.get("spellSaveDC") is not None:
            v[f"SpellDc{i}"] = str(entry["spellSaveDC"])
            v[f"SpellDc{i}Ability"] = _casting_ability(catalog, entry["classId"]).upper()
    speeds = derived.get("speeds") or ({"walk": derived["speed"]} if derived.get("speed") is not None else {})
    blocks["Speed"] = [f"{feet(n)} ({word(lang, 'modes', m)})" for m, n in speeds.items()]
    v["MaxHp"] = str(derived.get("hitPointMax", ""))
    v["HitDiceTotal"] = str(derived.get("hitDice") or "")
    for i in (1, 2, 3):
        v[f"DeathSuccess{i}"] = v[f"DeathFailure{i}"] = False

    prof = sheet.get("proficiencies") or {}
    prof_blocks = []
    for key, head in (("armor", "headArmor"), ("weapons", "headWeapons"), ("tools", "headTools")):
        if prof.get(key):
            prof_blocks.append(sheet_label(lang, head) + "\n" + ", ".join(proficiency_label(e) for e in prof[key]))
    if prof.get("languages"):
        prof_blocks.append(sheet_label(lang, "headLanguages") + "\n" + ", ".join(LANGUAGE_NAMES.get(x, x) for x in prof["languages"]))
    blocks["Proficiencies"] = prof_blocks

    # actions (two columns): standard actions, attacks per action, resources
    action_blocks = [sheet_label(lang, "headActions") + "\n" + sheet_label(lang, "standardActions", list=", ".join(STANDARD_ACTIONS))]
    if (derived.get("attacksPerAction") or 1) > 1:
        action_blocks.append(label(lang, "attacksPerAction", n=derived["attacksPerAction"]))
    resources = [("classResources", "secClassResources"), ("featResources", "secFeatResources"), ("speciesResources", "secSpeciesResources")]
    res_lines = [resource_line(r, lang) for key, _t in resources for r in derived.get(key) or []]
    if res_lines:
        action_blocks.append(sheet_label(lang, "headResources") + "\n" + "\n".join(res_lines))

    # weapons
    weapons = _weapon_rows(resolution, catalog, lang)
    for i in range(1, WEAPON_ROWS + 1):
        row = weapons[i - 1] if i <= len(weapons) else ("", "", "", "")
        v[f"Weapon{i}Name"], v[f"Weapon{i}Attack"], v[f"Weapon{i}Damage"], v[f"Weapon{i}Notes"] = row
    extra_weapons = weapons[WEAPON_ROWS:]
    if extra_weapons:
        action_blocks.append(sheet_label(lang, "headAttacks") + "\n" + "\n".join(
            " ".join(x for x in (n, h, d, no) if x) for n, h, d, no in extra_weapons))

    # equipment, coins, carrying
    rows = _equipment_rows(resolution, catalog)
    for i in range(EQUIPMENT_FIELD_ROWS):
        name, qty, wt = rows[i] if i < len(rows) else ("", "", "")
        v[f"Eq{i}Name"], v[f"Eq{i}Qty"], v[f"Eq{i}Weight"] = name, qty, wt
    for n in ("Cp", "Sp", "Ep", "Pp"):
        v[f"Coins{n}"] = "0"
    v["CoinsGp"] = str(sheet.get("startingGold") or 0)
    carry = derived.get("carryingCapacity") or {}
    if carry:
        v["WeightCarried"] = weight(carry["carried"], lang)
        v["WeightCapacity"] = weight(carry["capacity"], lang)
        v["PushDragLift"] = weight(carry["pushDragLift"], lang) if carry.get("pushDragLift") else ""

    # page 4
    details = sheet.get("details") or {}
    for key, field_name in (("age", "BodyAge"), ("height", "BodyHeight"), ("weight", "BodyWeight"), ("alignment", "BodyAlignment"),
                            ("faith", "BodyFaith"), ("skin", "BodySkin"), ("eyes", "BodyEyes"), ("hair", "BodyHair")):
        v[field_name] = str(details.get(key) or "")
    v["BodySize"] = str((sheet.get("species") or {}).get("size") or "")
    allies = []
    for key, head in (("allies", "headAllies"), ("organizations", "headOrganizations"), ("enemies", "headEnemies")):
        if details.get(key):
            allies.append(sheet_label(lang, head) + "\n" + details[key].strip())
    blocks["Allies"] = allies
    for key, field_name in (("personalityTraits", "Personality"), ("ideals", "Ideals"), ("bonds", "Bonds"), ("flaws", "Flaws"),
                            ("backstory", "Backstory"), ("notes", "Notes1")):
        blocks[field_name] = _paragraphs(details.get(key))

    # features flow
    desc = _Descriptions(catalog, sheet, ruleset)
    flow: list[FlowBlock] = []
    coverage: list[Coverage] = []
    current = None
    for f in sheet.get("features") or []:
        if f["source"]["kind"] == "feat":
            continue  # feats have their own section
        if f["source"]["label"] != current:
            current = f["source"]["label"]
            flow.append(FlowBlock("heading", f"=== {current.upper()} ==="))
        title = "* " + f["name"]
        if f.get("level"):
            title += f" • {label(lang, 'featureLevel', level=f['level'])}"
        if f.get("choice"):
            title += ": " + ", ".join(f["choice"])
        flow.append(FlowBlock("title", title))
        text = desc.feature(f)
        coverage.append(Coverage(f["source"]["kind"], f["name"], f.get("level"), bool(text)))
        for p in text or []:
            flow.append(FlowBlock("text", p))
    feats = sheet.get("feats") or []
    if feats:
        flow.append(FlowBlock("heading", sheet_label(lang, "headFeats")))
    for f in feats:
        title = "* " + f["name"]
        if f.get("level"):
            title += f" • {label(lang, 'featureLevel', level=f['level'])}"
        if f.get("choice"):
            title += ": " + ", ".join(f["choice"])
        flow.append(FlowBlock("title", title))
        text = desc.feat(f)
        coverage.append(Coverage("feat", f["name"], f.get("level"), bool(text)))
        for p in text or []:
            flow.append(FlowBlock("text", p))
        if f.get("notes"):
            flow.append(FlowBlock("text", "; ".join(f["notes"])))

    # distribute the actions over its two columns, then fit every box; leftovers continue in the flow / notes pages
    overflow: dict[str, tuple[str, ...]] = {}
    continued: list[FlowBlock] = []
    rect = {f.name: f.widgets[0].rect for f in L.FIELDS if f.kind == "multi"}
    size = {f.name: f.size for f in L.FIELDS if f.kind == "multi"}
    left = list(action_blocks)
    for name in ("Actions1", "Actions2"):
        taken, left = fill_box(left, rect[name])
        v[name] = "\n\n".join(taken)
    if left:
        blocks["_actions_rest"] = left
    for name, bl in blocks.items():
        if name == "_actions_rest":
            title = sheet_label(lang, "actions")
            rest = bl
            taken = []
        else:
            taken, rest = fill_box(bl, rect[name])
            v[name] = "\n\n".join(taken)
            title = sheet_label(lang, _FRAME_TITLE.get(name, "notes"))
        if rest:
            if name in ("Backstory", "Notes1", "Notes2"):
                overflow[name] = tuple(rest)
            else:
                continued.append(FlowBlock("heading", sheet_label(lang, "headContinued", title=title)))
                continued.extend(FlowBlock("text", b) for b in rest)
    all_values = []
    for fdef in L.FIELDS:
        default: str | bool = False if fdef.kind == "check" else ""
        all_values.append(FieldValue(fdef.name, v.get(fdef.name, default)))
    return SheetData(lang, tuple(all_values), tuple(flow + continued), overflow,
                     tuple(rows[EQUIPMENT_FIELD_ROWS:]), _spell_groups(resolution, catalog, lang), tuple(coverage))


_FRAME_TITLE = {"Senses": "senses", "Defenses": "defenses", "Speed": "speed", "Proficiencies": "proficiencies",
                "Allies": "allies", "Personality": "personality", "Ideals": "ideals", "Bonds": "bonds", "Flaws": "flaws",
                "Backstory": "backstory", "Notes1": "notes"}
