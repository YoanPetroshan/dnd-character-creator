"""5etools class files -> SRD-shaped subclass records (Slice 11b).

`class/index.json` maps a class id to a file; each file is
{"class": [...], "subclass": [...], "subclassFeature": [...]}. Only the
`subclass` and `subclassFeature` arrays are read here.
"""
from __future__ import annotations

import json
from pathlib import Path


def _read_json(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_raw_class_data(class_dir) -> tuple[list[dict], list[dict]]:
    """(raw subclasses, raw subclass features) of every file named in
    `class_dir/index.json`, in index order. ([], []) when the directory or
    index is missing; a file that is missing or not valid JSON is skipped."""
    if not class_dir:
        return [], []
    class_dir = Path(class_dir)
    index = _read_json(class_dir / "index.json")
    if not isinstance(index, dict):
        return [], []
    subclasses: list[dict] = []
    features: list[dict] = []
    for filename in index.values():
        if not isinstance(filename, str):
            continue
        data = _read_json(class_dir / filename)
        if isinstance(data, dict):
            subclasses.extend(s for s in data.get("subclass", []) if isinstance(s, dict))
            features.extend(f for f in data.get("subclassFeature", []) if isinstance(f, dict))
    return subclasses, features


def load_raw_optional_features(path) -> list[dict]:
    """Every record of `optionalfeatures.json`; [] when missing or broken."""
    if not path:
        return []
    data = _read_json(Path(path))
    if not isinstance(data, dict):
        return []
    return [o for o in data.get("optionalfeature", []) if isinstance(o, dict)]
