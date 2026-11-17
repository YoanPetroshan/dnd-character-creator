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


def spell_fields(record: dict) -> dict:
    """The translatable fields of a catalog spell record, under their API names."""
    return {
        "desc": list(record.get("desc") or []),
        "higherLevel": list(record.get("higher_level") or []),
        "material": record.get("material"),
        "castingCondition": record.get("casting_condition"),
    }


def source_hash(record_fields: dict) -> str:
    """sha1 hex of the English values of `SPELL_FIELDS` (sorted-key JSON, non-ASCII kept)."""
    canon = {name: record_fields.get(name) for name in SPELL_FIELDS}
    if canon["desc"] is None:
        canon["desc"] = []
    if canon["higherLevel"] is None:
        canon["higherLevel"] = []
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
