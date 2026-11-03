"""Vendored 5etools data bundle: build, verify, and drift-check `server/data/official`.

The bundle is a byte-exact copy of the raw 5etools files the converters read
(see `required_files`) plus a deterministic `MANIFEST.json`. Stdlib only.

    python -m catalog.official.bundle --from <dir> [--check]     (run from server/)

Without `--check` it rebuilds the bundle from <dir>; with `--check` it prints
what differs (added/removed/changed) and exits 1 on drift, writing nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

BUNDLE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "official"

MANIFEST_NAME = "MANIFEST.json"
MANIFEST_FORMAT = 1

# Same rule as chargen/sync.py `_SAFE_SUBDIR_FILE` (copied, not imported).
_SAFE_SUBDIR_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")

TOP_LEVEL_FILES = (
    "races.json",
    "backgrounds.json",
    "feats.json",
    "items-base.json",
    "optionalfeatures.json",
)
# subdir -> files always present besides what its index.json lists
SUBDIRS = {
    "spells": ("index.json", "sources.json"),
    "class": ("index.json",),
}


def _index_files(subdir: Path) -> list[str]:
    try:
        index = json.loads((subdir / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(index, dict):
        return []
    names: list[str] = []
    for value in index.values():
        if isinstance(value, str) and _SAFE_SUBDIR_FILE.match(value) and value not in names:
            names.append(value)
    return names


def required_files(src) -> list[str]:
    """Relative POSIX paths of every file the converters read, sorted.

    Subdirectory data files are taken from `<subdir>/index.json`, accepting only
    plain `*.json` names so a hostile index cannot point outside the tree."""
    src = Path(src)
    rels = list(TOP_LEVEL_FILES)
    for subdir, fixed in SUBDIRS.items():
        rels.extend(f"{subdir}/{n}" for n in fixed)
        rels.extend(f"{subdir}/{n}" for n in _index_files(src / subdir))
    return sorted(set(rels))


def _load_meta(src: Path) -> dict:
    try:
        meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def _meta_entry(meta: dict, rel: str) -> dict:
    entry = meta.get(rel)
    if not isinstance(entry, dict):
        # top-level files are keyed by short name ("races", "items-base")
        stem = rel[:-5] if rel.endswith(".json") and "/" not in rel else None
        entry = meta.get(stem) if stem else None
    return entry if isinstance(entry, dict) else {}


def _records(data) -> dict:
    if not isinstance(data, dict):
        return {}
    return {k: len(v) for k, v in data.items() if isinstance(v, list)}


def _bundle_sha(files: dict) -> str:
    lines = "".join(f"{rel} {files[rel]['sha256']}\n" for rel in sorted(files))
    return hashlib.sha256(lines.encode("utf-8")).hexdigest()


def _read_valid(src: Path, rel: str) -> bytes:
    path = src / rel
    if not path.is_file():
        raise FileNotFoundError(f"missing required file: {path}")
    raw = path.read_bytes()
    try:
        json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ValueError(f"invalid JSON in {path}: {exc}") from exc
    return raw


def build(src, dest) -> dict:
    """Copy the required files from `src` into `dest` (replacing it) and write
    MANIFEST.json. Raises, leaving `dest` untouched, on a missing/invalid file."""
    src, dest = Path(src), Path(dest)
    rels = required_files(src)
    meta = _load_meta(src)
    files: dict = {}
    for rel in rels:
        raw = _read_valid(src, rel)
        entry = _meta_entry(meta, rel)
        files[rel] = {
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "records": _records(json.loads(raw.decode("utf-8"))),
            "url": entry.get("url"),
            "pulled_at": entry.get("pulled_at"),
        }
    manifest = {"format": MANIFEST_FORMAT, "files": files, "bundle_sha256": _bundle_sha(files)}

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{dest.name}-build-", dir=dest.parent))
    backup = None
    try:
        os.chmod(tmp, 0o755)
        for rel in rels:
            target = tmp / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, target)
            os.chmod(target, 0o644)
        (tmp / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if dest.exists():
            backup = dest.with_name(f".{dest.name}-old-{os.getpid()}")
            os.replace(dest, backup)
        os.replace(tmp, dest)
    except BaseException:
        if backup is not None and not dest.exists():
            os.replace(backup, dest)
            backup = None
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if backup is not None:
        shutil.rmtree(backup, ignore_errors=True)
    return manifest


def check(src, dest=BUNDLE_DIR):
    """Compare `src` with the bundle at `dest`: (added, removed, changed) lists."""
    src, dest = Path(src), Path(dest)
    wanted = set(required_files(src))
    have = set()
    if dest.is_dir():
        have = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
        have.discard(MANIFEST_NAME)
    added = sorted(wanted - have)
    removed = sorted(have - wanted)
    changed = sorted(
        rel for rel in wanted & have
        if (src / rel).is_file() and (src / rel).read_bytes() != (dest / rel).read_bytes()
    )
    # a required file absent from src cannot be built: report it as removed-from-source
    missing = sorted(rel for rel in wanted if not (src / rel).is_file())
    if missing:
        removed = sorted(set(removed) | set(missing))
        added = [r for r in added if r not in missing]
    return added, removed, changed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m catalog.official.bundle", description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="src", required=True, help="directory holding the raw 5etools data")
    ap.add_argument("--dest", default=str(BUNDLE_DIR), help="bundle directory (default: server/data/official)")
    ap.add_argument("--check", action="store_true", help="report drift (exit 1) without writing")
    args = ap.parse_args(argv)
    src = Path(args.src).expanduser()
    if args.check:
        added, removed, changed = check(src, args.dest)
        for tag, items in (("added", added), ("removed", removed), ("changed", changed)):
            for rel in items:
                print(f"{tag}: {rel}")
        if added or removed or changed:
            return 1
        print("bundle matches source")
        return 0
    try:
        manifest = build(src, args.dest)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    total = sum(e["bytes"] for e in manifest["files"].values())
    print(f"built {len(manifest['files'])} files, {total} bytes, bundle_sha256 {manifest['bundle_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
