"""Data source paths for chargen.

Separates bundled SRD rules (checked into the repo, under chargen/data/srd) from
optional official supplemental data (user-provided or synced, under
~/.claude/dnd/.data/official or a configured DND_CAMPAIGN_ROOT).
"""

import os
import pathlib


def srd_dir() -> pathlib.Path:
    """Return the bundled SRD rules directory, creating it if needed.

    The SRD data is checked into the repo and should always be available.
    Create eagerly to signal the intent — chargen.sync writes data here.
    """
    root = pathlib.Path(__file__).resolve().parent.parent
    srd = root / "chargen" / "data" / "srd"
    srd.mkdir(parents=True, exist_ok=True)
    return srd


def official_dir() -> pathlib.Path:
    """Return the optional official supplemental data directory.

    Respects DND_CAMPAIGN_ROOT to allow users to co-locate their campaign data
    with official supplemental rules they've synced. Do not create eagerly —
    this directory only exists once `python3 -m chargen.sync --official` has
    populated it; its absence means this machine has not run that fetch, and
    the builder runs on the committed SRD data alone. has_official() checks
    for presence.
    """
    raw = os.environ.get("DND_CAMPAIGN_ROOT", "")
    if raw.strip():
        return pathlib.Path(raw.strip()).expanduser().resolve() / ".data" / "official"
    return pathlib.Path("~/.claude/dnd/.data/official").expanduser()


def has_official() -> bool:
    """Return True if official supplemental data exists and is non-empty."""
    d = official_dir()
    if not d.exists():
        return False
    try:
        return any(d.iterdir())
    except OSError:
        return False
