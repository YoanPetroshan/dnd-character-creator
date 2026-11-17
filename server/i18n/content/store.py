"""The content overlay store: Bulgarian texts for catalog records, in `server/data/i18n/<lang>/<kind>.json`.

An entry carries the sha1 of the English fields it was translated from. When the English text later changes the hash no
longer matches and the entry is ignored (the English text is served), so a stale translation never reaches a user."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "i18n"  # server/data/i18n (bundled into the offline pack)

SPELL_FIELDS = ("desc", "higherLevel", "material", "castingCondition")
# The translatable fields (under their API names) of every overlay kind: they, and only they, go into the source hash.
KIND_FIELDS = {
    "spells": SPELL_FIELDS,
    "species": ("fluff", "traits"),  # fluff: paragraphs; traits: one list of desc paragraphs per trait, in served order
    "items": ("desc", "special"),
    "item-rules": ("desc",),  # item properties (`property:<index>:<PHB|XPHB>`) and weapon masteries (`mastery:<Name>`)
}
KINDS = tuple(KIND_FIELDS)


def spell_fields(record: dict) -> dict:
    """The translatable fields of a catalog spell record, under their API names."""
    return {
        "desc": list(record.get("desc") or []),
        "higherLevel": list(record.get("higher_level") or []),
        "material": record.get("material"),
        "castingCondition": record.get("casting_condition"),
    }


def species_fields(record: dict) -> dict:
    """The translatable fields of a species record as the species route serves it (`fluff` and `traitDetails`)."""
    return {"fluff": list(record.get("fluff") or []),
            "traits": [list(t.get("desc") or []) for t in record.get("traitDetails") or []]}


def item_fields(record: dict) -> dict:
    return {"desc": list(record.get("desc") or []), "special": list(record.get("special") or [])}


def rule_fields(record: dict) -> dict:
    return {"desc": list(record.get("desc") or [])}


_FIELD_FUNCS = {"spells": spell_fields, "species": species_fields, "items": item_fields, "item-rules": rule_fields}


def fields_for(kind: str, record: dict) -> dict:
    """The translatable fields of a catalog `record` of the given overlay kind."""
    return _FIELD_FUNCS[kind](record)


def source_hash(*args) -> str:
    """sha1 hex of the English values of a kind's fields (sorted-key JSON, non-ASCII kept). `source_hash(fields)` is the
    spell hash (kept byte-identical); `source_hash(kind, fields)` any kind."""
    kind, record_fields = ("spells", args[0]) if len(args) == 1 else args
    canon = {name: record_fields.get(name) for name in KIND_FIELDS[kind]}
    for name in ("desc", "higherLevel", "fluff", "traits", "special"):
        if name in canon and canon[name] is None:
            canon[name] = []
    return hashlib.sha1(json.dumps(canon, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


@lru_cache(maxsize=None)
def load_overlay(kind: str, lang: str) -> dict:
    """`server/data/i18n/<lang>/<kind>.json` as a dict; a missing or unreadable file is an empty overlay."""
    try:
        data = json.loads((I18N_DIR / lang / f"{kind}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def overlay_spell(spell_record: dict, payload: dict, lang: str) -> dict:
    """`payload` (a spell-detail response body) with the Bulgarian texts when `lang` is "bg" and the overlay has a fresh
    entry for the spell; always with `textLang` ("bg" or "en"). Null material / castingCondition stay English."""
    out = dict(payload)
    out["textLang"] = "en"
    if lang != "bg":
        return out
    entry = load_overlay("spells", lang).get(spell_record.get("index"))
    if not isinstance(entry, dict) or entry.get("hash") != source_hash(spell_fields(spell_record)):
        return out
    out["desc"] = list(entry.get("desc") or [])
    out["higherLevel"] = list(entry.get("higherLevel") or [])
    if entry.get("material") is not None:
        out["material"] = entry["material"]
    if entry.get("castingCondition") is not None:
        out["castingCondition"] = entry["castingCondition"]
    out["textLang"] = "bg"
    return out


def _fresh_entry(kind: str, key: str, fields: dict, lang: str):
    """The overlay entry of `key` when `lang` is "bg" and its hash matches the English `fields`; else None."""
    if lang != "bg":
        return None
    entry = load_overlay(kind, lang).get(key)
    if not isinstance(entry, dict) or entry.get("hash") != source_hash(kind, fields):
        return None
    return entry


def overlay_species(species_id: str, payload: dict, lang: str) -> dict:
    """`payload` (a species-detail response body with `fluff` and `traitDetails`) with the Bulgarian fluff and trait
    descriptions when the overlay has a fresh entry for the species (the trait count must match); trait names and
    everything else stay English. Always with `textLang`."""
    out = dict(payload)
    out["textLang"] = "en"
    entry = _fresh_entry("species", species_id, species_fields(payload), lang)
    if entry is None:
        return out
    traits, details = entry.get("traits"), payload.get("traitDetails") or []
    if not isinstance(traits, list) or len(traits) != len(details):
        return out
    out["fluff"] = list(entry.get("fluff") or [])
    out["traitDetails"] = [{**d, "desc": list((t or {}).get("desc") or [])} for d, t in zip(details, traits)]
    out["textLang"] = "bg"
    return out


def overlay_items(item_record: dict, payload: dict, lang: str) -> dict:
    """`payload` (an item-detail response body with `desc` and `special`) with the Bulgarian texts when the overlay has a
    fresh entry for the item; always with `textLang`. Item names stay English."""
    out = dict(payload)
    out["textLang"] = "en"
    entry = _fresh_entry("items", item_record.get("index"), item_fields(item_record), lang)
    if entry is None:
        return out
    out["desc"] = list(entry.get("desc") or [])
    out["special"] = list(entry.get("special") or [])
    out["textLang"] = "bg"
    return out


def overlay_rule(key: str, english_desc: list, lang: str) -> list | None:
    """The Bulgarian paragraphs of an item-rule entry (`property:<index>:<PHB|XPHB>` / `mastery:<Name>`) when fresh,
    else None (serve `english_desc`)."""
    entry = _fresh_entry("item-rules", key, {"desc": english_desc}, lang)
    return None if entry is None else list(entry.get("desc") or [])
