"""F3a-10: drift guard between resolve() output and the hand-written frontend types.

`frontend/src/types.ts` is maintained by hand. Every key of the resolved containers below that appears in real
output must be a field of the matching interface; a new server key without a type fails here instead of silently
reaching the UI untyped. The interfaces are read with a small regex parser (top-level `name?: ...;` lines of an
`export interface`, plus `extends`). Keys that are intentionally untyped go into `UNTYPED_ALLOWLIST` with a reason.

Real output comes from the S6 kitchen-sink drafts (all rulesets, incl. warlock7-2024) plus fully chosen 2024 and
mixed drafts of every class at level 5 / 11 / 20 and a 2024 multiclass."""
import pathlib
import re

import pytest

from catalog.loader import load
from engine.resolve import resolve
from kitchen_sink import KITCHEN_SINK, base_draft, build, fill, skip_reason

TYPES_TS = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src" / "types.ts"

# (path into the resolution, interface name). "[]" = every element of a list; "sheet.spells[]" etc.
CONTAINERS = [
    ("sheet", "Sheet"),
    ("derived", "Derived"),
    ("choices[]", "Choice"),
    ("choices[].source", "ChoiceSource"),
    ("choices[].options[]", "ChoiceOption"),
    ("derived.attacks[]", "Attack"),
    ("derived.classResources[]", "ClassResource"),
    ("derived.featResources[]", "FeatResource"),
    ("sheet.features[]", "SheetFeature"),
    ("sheet.feats[]", "SheetFeat"),
    ("sheet.spells[]", "SheetClassSpells"),
    ("sheet.innateSpells[]", "SheetInnateSpell"),
    # RP22: nested containers the RP series extended (pack contents, subclass spell rows, mastery rows)
    ("sheet.equipment", "SheetEquipment"),
    ("sheet.equipment.granted[]", "SheetEquipmentEntry"),
    ("sheet.equipment.chosen[]", "SheetEquipmentEntry"),
    ("sheet.equipment.added[]", "SheetAddedEquipmentEntry"),
    ("sheet.weaponMasteries[]", "WeaponMastery"),
    ("derived.carryingCapacity", "CarryingCapacity"),
    ("sheet.spells[].alwaysPrepared[]", "SheetSpellSummary"),
    ("sheet.spells[].spellbook[]", "SheetSpellSummary"),
]

# interface name -> {key: why it is intentionally not typed}. Keep this list short and justified.
UNTYPED_ALLOWLIST: dict[str, dict[str, str]] = {}

_FIELD = re.compile(r"^  (\w+)\??:")
_INTERFACE = re.compile(r"^export interface (\w+)(?: extends ([\w, ]+))? \{$")


def parse_interfaces(text: str) -> dict[str, set[str]]:
    """{interface name: set of top-level field names (own + extended)}."""
    own: dict[str, set[str]] = {}
    parents: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = _INTERFACE.match(line)
        if m:
            current = m.group(1)
            own[current] = set()
            parents[current] = [p.strip() for p in (m.group(2) or "").split(",") if p.strip()]
        elif line.startswith("}"):
            current = None
        elif current:
            f = _FIELD.match(line)
            if f:
                own[current].add(f.group(1))

    def fields(name: str, seen=()) -> set[str]:
        out = set(own.get(name, ()))
        for p in parents.get(name, ()):
            if p not in seen:
                out |= fields(p, seen + (name,))
        return out

    return {name: fields(name) for name in own}


def _collect(node, path: str):
    """Yield every dict found at `path` ('a.b[].c'): '[]' fans out over a list."""
    head, _, rest = path.partition(".")
    is_list = head.endswith("[]")
    key = head[:-2] if is_list else head
    value = node.get(key) if isinstance(node, dict) else None
    if value is None:
        return
    items = value if is_list else [value]
    for item in items:
        if not isinstance(item, dict):
            continue
        if rest:
            yield from _collect(item, rest)
        else:
            yield item


def _drift(resolution: dict, interfaces: dict[str, set[str]]) -> set[tuple[str, str]]:
    missing = set()
    for path, name in CONTAINERS:
        assert name in interfaces, f"types.ts has no interface {name}"
        allowed = interfaces[name] | set(UNTYPED_ALLOWLIST.get(name, {}))
        for obj in _collect({"": None, **resolution}, path):
            missing |= {(name, k) for k in obj if k not in allowed}
    return missing


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def interfaces():
    return parse_interfaces(TYPES_TS.read_text(encoding="utf-8"))


def test_parser_reads_the_known_interfaces(interfaces):
    assert {"Sheet", "Derived", "Choice", "Attack", "SheetAddedEquipmentEntry"} <= set(interfaces)
    assert "alignment" in interfaces["CharacterDetails"] and "equipped" in interfaces["SheetAddedEquipmentEntry"]
    assert "itemId" in interfaces["SheetAddedEquipmentEntry"]  # extended from SheetEquipmentEntry


def test_a_new_server_key_without_a_type_is_reported(interfaces):
    fake = {"derived": {"hitPointMax": 5, "brandNewKey": 1}, "choices": [{"id": "x", "options": [{"id": "a", "label": "A", "zzz": 1}]}]}
    assert _drift(fake, interfaces) == {("Derived", "brandNewKey"), ("ChoiceOption", "zzz")}


def _kitchen_sink_resolutions(catalog):
    for sid, spec in KITCHEN_SINK.items():
        if skip_reason(spec):
            continue
        yield sid, resolve(build(sid, catalog, resolve), catalog)


def _class_drafts(catalog):
    from catalog import official_source
    classes = ["barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer",
               "warlock", "wizard"]
    rulesets = ["mixed"] + (["2024"] if official_source.has_official() and official_source.has_official_classes() else [])
    for ruleset in rulesets:
        for cls in classes:
            for level in (5, 11, 20):
                spec = {"classes": [(cls, level, None)], "ruleset": ruleset, "equip": []}
                draft = base_draft(spec)
                if ruleset == "2024":
                    draft["species"] = {"id": "human-xphb", "choices": {}}
                    draft["background"] = {"id": "soldier-xphb", "choices": {}}
                yield f"{ruleset}/{cls}{level}", draft
    if "2024" in rulesets:
        spec = {"classes": [("rogue", 4, None), ("druid", 3, None), ("barbarian", 3, None)], "ruleset": "2024", "equip": []}
        draft = base_draft(spec)
        draft["species"] = {"id": "human-xphb", "choices": {}}
        draft["background"] = {"id": "soldier-xphb", "choices": {}}
        yield "2024/multiclass", draft


def test_every_resolved_key_is_typed_in_types_ts(catalog, interfaces):
    drift: dict[tuple[str, str], str] = {}
    for sid, res in _kitchen_sink_resolutions(catalog):
        for item in _drift(res, interfaces):
            drift.setdefault(item, f"kitchen sink {sid}")
    for sid, draft in _class_drafts(catalog):
        res = resolve(fill(draft, catalog, {}, resolve), catalog)
        for item in _drift(res, interfaces):
            drift.setdefault(item, sid)
    assert not drift, "keys in resolve() output without a field in frontend/src/types.ts:\n" + "\n".join(
        f"  {iface}.{key}  (first seen: {where})" for (iface, key), where in sorted(drift.items()))


def test_attack_ability_type_allows_the_pact_weapon_charisma_row():
    text = TYPES_TS.read_text(encoding="utf-8")
    attack = text[text.index("export interface Attack "):]
    attack = attack[:attack.index("\n}")]
    assert re.search(r'ability: "STR" \| "DEX" \| "CHA";', attack)


def test_innate_spell_level_and_choice_optional_are_typed_as_the_server_emits_them():
    # RPF 9: an innate spell without a catalog record has `level: None`; RPF 7: `optional` on Choice.
    text = TYPES_TS.read_text(encoding="utf-8")
    spell = text[text.index("export interface SheetInnateSpell "):]
    spell = spell[:spell.index("\n}")]
    assert re.search(r"level: number \| null;", spell)
    choice = text[text.index("export interface Choice "):]
    choice = choice[:choice.index("\n}")]
    assert re.search(r"optional\?: boolean;", choice)
