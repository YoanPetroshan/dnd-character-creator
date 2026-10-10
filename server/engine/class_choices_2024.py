"""C6b-1: 2024 class choice cards that are built from XPHB feature ids (helper for resolve()).

Pure functions over the catalog; resolve() only wires them. Everything here is ruleset "2024"
only: with any other ruleset, or an SRD-only catalog (no XPHB feature records), every function
returns "nothing", so the SRD cards stay.
"""
from __future__ import annotations

from catalog.reference_data import EXPERTISE_2024, SKILL_NAMES, SRD_CARDS_REPLACED_2024


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
    if cls_id == "ranger":
        return set(SRD_CARDS_REPLACED_2024[cls_id]) if cls_id in (catalog.class_2024_records or {}) else set()
    return set(SRD_CARDS_REPLACED_2024[cls_id]) if expertise_entries(catalog, cls_id, ruleset) else set()
