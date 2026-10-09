"""The ONLY module of the official-data converters that imports
`chargen.sources` (see the sys.path note below); every other module of this
package, and every caller, gets `official_dir` / `has_official` /
`_repo_root` from here (or via the `catalog.official_source` shim)."""
from __future__ import annotations

from pathlib import Path
import os
import sys

_repo_root = Path(__file__).resolve().parents[3]  # server/catalog/official/paths.py -> official -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    # Appended, not prepended: the root also holds the v1 app.py/storage.py,
    # which must never shadow the server's own modules (only `chargen` is needed).
    sys.path.append(str(_repo_root))

from chargen.sources import official_dir, has_official  # noqa: E402,F401  (must follow the sys.path fix above)


def spells_dir() -> Path | None:
    """Where the 5etools spell files live, or None when they are absent.

    `DND_5ETOOLS_DATA` (a 5etools-src `data` directory, e.g.
    ~/Documents/5etools-src/data) wins when set and has `spells/index.json`;
    otherwise `official_dir()/spells` as filled by
    `python3 -m chargen.sync --official`. Read at call time, so tests and
    shells can switch it without reloading anything."""
    override = os.environ.get("DND_5ETOOLS_DATA", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override).expanduser() / "spells")
    candidates.append(Path(official_dir()) / "spells")
    for candidate in candidates:
        if (candidate / "index.json").is_file():
            return candidate
    return None


def has_official_spells() -> bool:
    return spells_dir() is not None


def class_dir() -> Path | None:
    """Where the 5etools class files live (class/index.json), or None.
    Same lookup as `spells_dir()`: `DND_5ETOOLS_DATA` first, then
    `official_dir()/class`."""
    override = os.environ.get("DND_5ETOOLS_DATA", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override).expanduser() / "class")
    candidates.append(Path(official_dir()) / "class")
    for candidate in candidates:
        if (candidate / "index.json").is_file():
            return candidate
    return None


def has_official_classes() -> bool:
    return class_dir() is not None


def optionalfeatures_file() -> Path | None:
    """`optionalfeatures.json` (maneuvers, arcane shots, runes...): the
    `DND_5ETOOLS_DATA` override first, then `official_dir()`, else None."""
    override = os.environ.get("DND_5ETOOLS_DATA", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override).expanduser() / "optionalfeatures.json")
    candidates.append(Path(official_dir()) / "optionalfeatures.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def items_base_file() -> Path | None:
    """`items-base.json` (mundane weapons and armor): the `DND_5ETOOLS_DATA`
    override first, then `official_dir()`, else None."""
    override = os.environ.get("DND_5ETOOLS_DATA", "").strip()
    candidates = []
    if override:
        candidates.append(Path(override).expanduser() / "items-base.json")
    candidates.append(Path(official_dir()) / "items-base.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None
