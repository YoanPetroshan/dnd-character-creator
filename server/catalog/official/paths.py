"""Where the official-data converters read their files (B2: the vendored
bundle at server/data/official is the default). The ONLY module of this
package that imports `chargen.sources` (see the sys.path note below), and only
for the explicit DND_CAMPAIGN_ROOT branch; every other module and caller gets
`official_dir` / `has_official` / `data_source` / `_repo_root` from here (or
via the `catalog.official_source` shim)."""
from __future__ import annotations

from pathlib import Path
import os
import sys

_repo_root = Path(__file__).resolve().parents[3]  # server/catalog/official/paths.py -> official -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    # Appended, not prepended: a root module must never shadow the server's own
    # modules (the v1 root app.py/storage.py are gone since D-5; only `chargen` is needed).
    sys.path.append(str(_repo_root))

from chargen import sources as _chargen_sources  # noqa: E402  (must follow the sys.path fix above)

BUNDLED_DIR = _repo_root / "server" / "data" / "official"
"""The vendored raw 5etools files (B1). The default data source."""


def _nonempty_dir(d: Path) -> bool:
    try:
        return d.is_dir() and any(d.iterdir())
    except OSError:
        return False


def _resolve() -> tuple[Path, str]:
    """(directory, source label). Evaluated at CALL time, never cached.

    Order: `DND_OFFICIAL_DATA=none` (SRD-only, a guaranteed-absent path) >
    `DND_OFFICIAL_DATA=<path>` ("explicit") > `DND_CAMPAIGN_ROOT` explicitly set
    and its `.data/official` non-empty ("campaign") > the bundle ("bundled").
    The implicit `~/.claude/dnd/.data/official` is never consulted. (The
    per-file `DND_5ETOOLS_DATA` override lives in the *_dir()/_file() helpers
    below and sits above all of this.)"""
    explicit = os.environ.get("DND_OFFICIAL_DATA", "").strip()
    if explicit:
        if explicit.lower() == "none":
            return BUNDLED_DIR / "__disabled__", "srd-only"
        return Path(explicit).expanduser(), "explicit"
    if os.environ.get("DND_CAMPAIGN_ROOT", "").strip():
        campaign = Path(_chargen_sources.official_dir())
        if _nonempty_dir(campaign):
            return campaign, "campaign"
    return BUNDLED_DIR, "bundled"


def official_dir() -> Path:
    """Directory the official-data converters read (see `_resolve`)."""
    return _resolve()[0]


def data_source() -> str:
    """'srd-only' | 'explicit' | 'campaign' | 'bundled' (diagnostic)."""
    return _resolve()[1]


def has_official() -> bool:
    """True when `official_dir()` exists and is non-empty."""
    return _nonempty_dir(official_dir())


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
