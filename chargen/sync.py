#!/usr/bin/env python3
"""
sync.py — fetch 5e SRD reference data from 5e-bits/5e-database

Downloads the ten JSON datasets chargen's rules engine is built on (spells,
levels, classes, subclasses, features, races, subraces, traits, equipment,
backgrounds) from the open 5e-bits/5e-database repo (MIT + OGL licensed) and
saves them to chargen/data/srd/. The result is committed to the repo — see
the module docstring in chargen/sources.py — so the character builder works
fully offline; this script is only needed to refresh the data, not to run it.

Deliberately mirrors the conventions of skills/dnd/scripts/data_pull.py
(TARGETS list, _fetch() helper, meta.json sidecar, --force/--status flags)
since that script established the pattern for this repo. One difference:
_fetch() here writes to a sibling ".tmp" file and only os.replace()s it into
place after the response has been read AND validated as parseable JSON. A
plain "open(dest, 'wb').write(data)" — which is what data_pull.py does — can
leave a truncated or corrupt file at dest if the process dies mid-write or
the response turns out to be an HTML error page. Writing through a temp file
and renaming means dest is only ever fully-good-or-untouched, which matters
here because dest is a file we commit to source control.

Usage:
    python3 -m chargen.sync                       # skip files that already exist
    python3 -m chargen.sync --force                # re-download everything
    python3 -m chargen.sync --status                # show what's installed
    python3 -m chargen.sync --official               # fetch the official (non-SRD) catalog
    python3 -m chargen.sync --official --force        # re-download the official catalog
    python3 -m chargen.sync --official --status       # show official-install status too

--official (Task 10) fetches the wider, multi-sourcebook official catalog
(races.json, backgrounds.json — the 5etools-src omnibus, MIT-licensed) into
chargen.sources.official_dir(), which is OUTSIDE this repo (gitignored, never
committed — see the plan's Decision log). It is a separate destination, a
separate meta.json sidecar, and a separate opt-in: the SRD sync above always
runs and is committed to the repo; --official is a one-time, per-machine
widening of the catalog that chargen/catalog.py's _merge_official() layers on
top of the SRD baseline when present, and is never a hard dependency.

Spells (Slice 11a.1): --official also fetches spells/index.json,
spells/sources.json and every book file the index lists into
official_dir()/spells/ (OFFICIAL_SUBDIR_TARGETS). The server's
catalog/official/spells.py converts them; chargen itself does not read them.
Slice 11b.1 adds class/ (index + every class file) and optionalfeatures.json.
Still NOT fetched: items (11c).
"""

import json
import os
import pathlib
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from chargen.sources import official_dir, srd_dir

BASE_URL = "https://raw.githubusercontent.com/5e-bits/5e-database/main/src/2014/en"

OFFICIAL_BASE_URL = "https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data"
OFFICIAL_TARGETS = [
    {"key": "races", "filename": "races.json",
     "desc": "Races and subraces — the full official arsenal"},
    {"key": "backgrounds", "filename": "backgrounds.json",
     "desc": "Backgrounds — the full official arsenal"},
    {"key": "feats", "filename": "feats.json",
     "desc": "Feats — the full official arsenal (Phase 4c grounding)"},
    {"key": "optionalfeatures", "filename": "optionalfeatures.json",
     "desc": "Optional features - maneuvers, arcane shots, runes, elemental disciplines (Slice 11b)"},
    {"key": "items-base", "filename": "items-base.json",
     "desc": "Base items - mundane weapons and armor (Slice 11c)"},
]

# Slice 11a.1: subdirectories of the 5etools data tree. Each lists its own
# index.json ({"PHB": "spells-phb.json", ...}) whose every file is fetched into
# official_dir()/<subdir>/ too, alongside the fixed `files` below.
OFFICIAL_SUBDIR_TARGETS = [
    {"subdir": "spells", "files": ["index.json", "sources.json"],
     "desc": "Spells - every book listed in spells/index.json plus the class-list map"},
    {"subdir": "class", "files": ["index.json"],
     "desc": "Classes and subclasses - every file in class/index.json"},
]
_SAFE_SUBDIR_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")

TARGETS = [
    {"key": "spells", "filename": "5e-SRD-Spells.json",
     "desc": "Spells — level, school, range, duration, components, description"},
    {"key": "levels", "filename": "5e-SRD-Levels.json",
     "desc": "Per-level class progression — proficiency bonus, features, slots"},
    {"key": "classes", "filename": "5e-SRD-Classes.json",
     "desc": "Classes — hit die, proficiencies, starting equipment"},
    {"key": "subclasses", "filename": "5e-SRD-Subclasses.json",
     "desc": "Subclasses — archetypes chosen within a class"},
    {"key": "features", "filename": "5e-SRD-Features.json",
     "desc": "Class and subclass features by level"},
    {"key": "races", "filename": "5e-SRD-Races.json",
     "desc": "Races — ability bonuses, traits, speed, size"},
    {"key": "subraces", "filename": "5e-SRD-Subraces.json",
     "desc": "Subraces — variants within a race"},
    {"key": "traits", "filename": "5e-SRD-Traits.json",
     "desc": "Racial and subracial traits, described in full"},
    {"key": "equipment", "filename": "5e-SRD-Equipment.json",
     "desc": "Equipment — weapons, armour, adventuring gear, costs"},
    {"key": "backgrounds", "filename": "5e-SRD-Backgrounds.json",
     "desc": "Backgrounds — skill proficiencies, equipment, feature, traits"},
]


def _meta_file(dir_path=None) -> str:
    """dir_path defaults to srd_dir() — the SRD meta.json. Official-catalog
    callers pass official_dir() explicitly, so the two sidecars never touch
    or overwrite each other."""
    d = dir_path if dir_path is not None else srd_dir()
    return os.path.join(str(d), "meta.json")


def _load_meta(dir_path=None) -> dict:
    try:
        with open(_meta_file(dir_path)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_meta(meta: dict, dir_path=None) -> None:
    with open(_meta_file(dir_path), "w") as f:
        json.dump(meta, f, indent=2)


def _fetch(url: str, dest: str) -> tuple[bool, str]:
    """Download url -> dest. Returns (success, message).

    Writes to dest + ".tmp" first and only os.replace()s it into place once
    the bytes are confirmed to be valid JSON. If anything fails along the
    way — network error, non-2xx response, invalid JSON — dest is left
    exactly as it was before the call (untouched if it already existed,
    absent if it didn't), and the temp file is cleaned up rather than left
    lying around.
    """
    tmp = dest + ".tmp"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "dnd-chargen-sync/1.0"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        # Validate it's parseable JSON before it ever touches disk at dest.
        json.loads(data)
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
        kb = len(data) // 1024
        return True, f"{kb} KB"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except urllib.error.URLError as e:
        return False, f"Network error: {e.reason}"
    except json.JSONDecodeError:
        return False, "Invalid JSON in response"
    except Exception as e:
        return False, str(e)
    finally:
        # Never leave a partial .tmp file behind, whether we failed before
        # or after creating it.
        if os.path.exists(tmp):
            os.remove(tmp)


def cmd_status(official: bool = False) -> None:
    d = str(srd_dir())
    meta = _load_meta()
    print(f"Data directory: {d}\n")
    any_missing = False
    for t in TARGETS:
        path = os.path.join(d, t["filename"])
        if os.path.exists(path):
            size_kb = os.path.getsize(path) // 1024
            pulled = meta.get(t["key"], {}).get("pulled_at", "unknown date")
            print(f"  ✓  {t['key']:12s}  {size_kb:>5} KB   pulled {pulled}")
        else:
            print(f"  ✗  {t['key']:12s}  (not downloaded)")
            any_missing = True
    if any_missing:
        print("\nRun `python3 -m chargen.sync` to download missing files.")
    else:
        print("\nAll files present. Run `python3 -m chargen.sync --force` to refresh.")

    if official:
        print()
        cmd_official_status()


# ---------------------------------------------------------------------------
# --official: the wider, multi-sourcebook catalog (Task 10)
# ---------------------------------------------------------------------------


def _official_dir_is_safe() -> tuple[bool, str]:
    """Refuse to write official data inside this repo's tree.

    official_dir() normally resolves outside the repo (~/.claude/dnd/.data/
    official, or wherever DND_CAMPAIGN_ROOT points), but DND_CAMPAIGN_ROOT is
    user-configurable — if it's ever set to somewhere inside this checkout,
    the fetch would land files that could get committed. This check runs
    before any write, every time, regardless of what DND_CAMPAIGN_ROOT is
    set to.
    """
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    dest = official_dir()
    try:
        dest_resolved = dest.resolve()
    except OSError:
        dest_resolved = dest
    if dest_resolved == repo_root or repo_root in dest_resolved.parents:
        return False, (
            f"Refusing to write official data inside the repo tree: "
            f"{dest_resolved} is inside {repo_root}. Set DND_CAMPAIGN_ROOT to "
            f"a location outside the repo (or leave it unset to use the "
            f"default ~/.claude/dnd/.data/official)."
        )
    return True, ""


def _subdir_index_files(subdir_dir: pathlib.Path) -> list[str]:
    """The data files listed by <subdir>/index.json: only plain `*.json` file
    names are accepted (no path separators or leading dots), anything else in
    the index is ignored, so a hostile index cannot make us write elsewhere."""
    try:
        with open(subdir_dir / "index.json", encoding="utf-8") as f:
            index = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(index, dict):
        return []
    names = []
    for value in index.values():
        if isinstance(value, str) and _SAFE_SUBDIR_FILE.match(value) and value not in names:
            names.append(value)
    return names


def _subdir_expected_files(target: dict, root: pathlib.Path) -> list[str]:
    names = list(target["files"])
    for name in _subdir_index_files(root / target["subdir"]):
        if name not in names:
            names.append(name)
    return names


def cmd_official_status() -> None:
    d = str(official_dir())
    meta = _load_meta(official_dir())
    print(f"Official data directory: {d}\n")
    any_missing = False
    for t in OFFICIAL_TARGETS:
        path = os.path.join(d, t["filename"])
        if os.path.exists(path):
            size_kb = os.path.getsize(path) // 1024
            pulled = meta.get(t["key"], {}).get("pulled_at", "unknown date")
            print(f"  ✓  {t['key']:12s}  {size_kb:>5} KB   pulled {pulled}")
        else:
            print(f"  ✗  {t['key']:12s}  (not downloaded)")
            any_missing = True
    for st in OFFICIAL_SUBDIR_TARGETS:
        for rel in _subdir_expected_files(st, pathlib.Path(d)):
            path = os.path.join(d, st["subdir"], rel)
            key = f"{st['subdir']}/{rel}"
            if os.path.exists(path):
                size_kb = os.path.getsize(path) // 1024
                pulled = meta.get(key, {}).get("pulled_at", "unknown date")
                print(f"  ✓  {key:24s}  {size_kb:>5} KB   pulled {pulled}")
            else:
                print(f"  ✗  {key:24s}  (not downloaded)")
                any_missing = True
    if any_missing:
        print("\nRun `python3 -m chargen.sync --official` to download missing files.")
    else:
        print("\nAll official files present. Run `python3 -m chargen.sync --official "
              "--force` to refresh.")


def _pull_one(rel: str, url: str, dest_dir: pathlib.Path, meta: dict, meta_dir: pathlib.Path, force: bool) -> str:
    """Fetches one file into dest_dir; returns "pulled" | "skipped" | "failed"."""
    dest = dest_dir / pathlib.PurePosixPath(rel).name
    key = f"{dest_dir.name}/{dest.name}"
    if dest.exists() and not force:
        print(f"  skip  {key} (already exists - use --force to refresh)")
        return "skipped"
    print(f"  pull  {key} … ", end="", flush=True)
    t0 = time.time()
    ok, fetch_msg = _fetch(url, str(dest))
    if not ok:
        print(f"FAILED — {fetch_msg}")
        return "failed"
    print(f"done ({fetch_msg}, {time.time() - t0:.1f}s)")
    meta[key] = {
        "filename": f"{dest_dir.name}/{dest.name}",
        "pulled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "url": url,
    }
    _save_meta(meta, meta_dir)
    return "pulled"


def _pull_subdir(target: dict, root: pathlib.Path, meta: dict, force: bool) -> tuple[int, int, int]:
    """Fetches a subdirectory's fixed files, then every file its index.json
    lists (the index is read after it has been fetched)."""
    sub = root / target["subdir"]
    sub.mkdir(parents=True, exist_ok=True)
    counts = {"pulled": 0, "skipped": 0, "failed": 0}
    done = set()
    for name in target["files"]:
        done.add(name)
        counts[_pull_one(name, f"{OFFICIAL_BASE_URL}/{target['subdir']}/{name}", sub, meta, root, force)] += 1
    for name in _subdir_index_files(sub):
        if name in done:
            continue
        counts[_pull_one(name, f"{OFFICIAL_BASE_URL}/{target['subdir']}/{name}", sub, meta, root, force)] += 1
    return counts["pulled"], counts["skipped"], counts["failed"]


def cmd_official_pull(force: bool) -> bool:
    """Returns True on success (including an all-skipped no-op run), False
    if the safety guard refused or any target failed to download."""
    safe, msg = _official_dir_is_safe()
    if not safe:
        print(f"ERROR: {msg}")
        return False

    d = official_dir()
    d.mkdir(parents=True, exist_ok=True)
    meta = _load_meta(d)

    pulled = 0
    skipped = 0
    failed = 0

    for t in OFFICIAL_TARGETS:
        dest = os.path.join(str(d), t["filename"])
        url = f"{OFFICIAL_BASE_URL}/{t['filename']}"

        if os.path.exists(dest) and not force:
            print(f"  skip  {t['key']} (already exists — use --force to refresh)")
            skipped += 1
            continue

        print(f"  pull  {t['key']} … ", end="", flush=True)
        t0 = time.time()
        ok, fetch_msg = _fetch(url, dest)
        elapsed = time.time() - t0

        if ok:
            print(f"done ({fetch_msg}, {elapsed:.1f}s)")
            meta[t["key"]] = {
                "filename": t["filename"],
                "pulled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "url": url,
            }
            _save_meta(meta, d)
            pulled += 1
        else:
            print(f"FAILED — {fetch_msg}")
            failed += 1

    for target in OFFICIAL_SUBDIR_TARGETS:
        p_, s_, f_ = _pull_subdir(target, d, meta, force)
        pulled, skipped, failed = pulled + p_, skipped + s_, failed + f_

    print()
    print(f"Done. Pulled: {pulled}  Skipped: {skipped}  Failed: {failed}")
    if failed:
        print("Check network connection and try again. Partial pulls are safe to re-run.")
    else:
        print(f"Official data stored in: {d}")
    return failed == 0


def cmd_pull(force: bool) -> None:
    d = str(srd_dir())
    meta = _load_meta()

    pulled = 0
    skipped = 0
    failed = 0

    for t in TARGETS:
        dest = os.path.join(d, t["filename"])
        url = f"{BASE_URL}/{t['filename']}"

        if os.path.exists(dest) and not force:
            print(f"  skip  {t['key']} (already exists — use --force to refresh)")
            skipped += 1
            continue

        print(f"  pull  {t['key']} … ", end="", flush=True)
        t0 = time.time()
        ok, msg = _fetch(url, dest)
        elapsed = time.time() - t0

        if ok:
            print(f"done ({msg}, {elapsed:.1f}s)")
            meta[t["key"]] = {
                "filename": t["filename"],
                "pulled_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "url": url,
            }
            # Save incrementally so a later failure in this same run never
            # loses the record of files that already succeeded.
            _save_meta(meta)
            pulled += 1
        else:
            print(f"FAILED — {msg}")
            failed += 1

    print()
    print(f"Done. Pulled: {pulled}  Skipped: {skipped}  Failed: {failed}")
    if failed:
        print("Check network connection and try again. Partial pulls are safe to re-run.")
    else:
        print(f"Data stored in: {d}")


def main() -> None:
    args = sys.argv[1:]
    official = "--official" in args
    status = "--status" in args
    force = "--force" in args

    if status:
        cmd_status(official=official)
    elif official:
        if not cmd_official_pull(force=force):
            sys.exit(1)
    else:
        cmd_pull(force=force)


if __name__ == "__main__":
    main()
