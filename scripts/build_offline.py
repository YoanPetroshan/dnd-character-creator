#!/usr/bin/env python3
"""Build the offline pack: the engine as a zip plus the pinned Pyodide runtime, in frontend/public/pyodide/.

    .venv/bin/python scripts/build_offline.py            # build app.zip + fonts.zip, fetch what is missing, verify all
    .venv/bin/python scripts/build_offline.py --check    # verify only (no build, no network): exit 1 on any mismatch

Output (all under frontend/public/pyodide/, gitignored):
  app.zip     server engine + catalog + service + export code, i18n catalogs, the bundled official data, and
              chargen/{__init__,sources}.py + chargen/data/srd. Unzipped at "/app" it gives /app/server and /app/chargen.
  fonts.zip   server/assets/fonts (the PDF export's DejaVu fonts); unzipped at "/app" too, so it is a separate file
              the app can fetch lazily with the PDF stack.
  pack.json   name, size and sha256 of every file of the pack (the precache list of a later slice).
  + the Pyodide core files and the wheels pinned in scripts/offline_manifest.json.

Network use: only the downloads listed in scripts/offline_manifest.json (jsdelivr's mirror of Pyodide 314.0.7 and
files.pythonhosted.org for fpdf2, defusedxml and pypdf), and only for files that are missing or fail their hash. Every
download is checked against the pinned size and sha256 BEFORE it is moved into place; a mismatch stops the script
(exit 2), nothing is skipped. app.zip is deterministic (sorted names, fixed timestamps and modes, fixed compression).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import pathlib
import sys
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "scripts" / "offline_manifest.json"
OUT = ROOT / "frontend" / "public" / "pyodide"

DATE_TIME = (1980, 1, 1, 0, 0, 0)

# server/*.py modules that ship (app.py is the Flask adapter and stays out), and the packages that ship whole.
SERVER_MODULES_EXCLUDE = {"app.py"}
SERVER_PACKAGES = ("catalog", "engine", "i18n")
# Developer-only files inside those packages (parse the TypeScript copy / render the review table).
EXCLUDE_FILES = {"server/i18n/review_table.py", "server/i18n/ts_copy.py"}
SERVER_DATA = "server/data/official"
CHARGEN_FILES = ("chargen/__init__.py", "chargen/sources.py")
CHARGEN_DATA = "chargen/data/srd"
FONTS = "server/assets/fonts"


class VerificationError(Exception):
    """A pinned file does not match its size or sha256."""


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _walk(rel_dir: str) -> list[str]:
    base = ROOT / rel_dir
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__" and not d.startswith("."))
        for name in filenames:
            if name.endswith((".pyc", ".pyo")) or name.startswith(".") or name.endswith(".tmp"):
                continue
            out.append(str((pathlib.Path(dirpath) / name).relative_to(ROOT)).replace(os.sep, "/"))
    return out


def app_files() -> list[str]:
    files = [f"server/{p.name}" for p in (ROOT / "server").glob("*.py") if p.name not in SERVER_MODULES_EXCLUDE]
    for pkg in SERVER_PACKAGES:
        files += _walk(f"server/{pkg}")
    files += _walk(SERVER_DATA)
    files += list(CHARGEN_FILES)
    files += _walk(CHARGEN_DATA)
    return sorted(f for f in files if f not in EXCLUDE_FILES)


def font_files() -> list[str]:
    return sorted(_walk(FONTS))


def write_zip(target: pathlib.Path, rel_files: list[str]) -> None:
    """Deterministic zip: sorted entries, fixed timestamp and mode, deflate level 9, no extra fields."""
    tmp = target.with_suffix(target.suffix + ".tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(rel_files):
            info = zipfile.ZipInfo(rel, DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            z.writestr(info, (ROOT / rel).read_bytes(), compresslevel=9)
    tmp.replace(target)


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verify(path: pathlib.Path, entry: dict) -> None:
    if not path.exists():
        raise VerificationError(f"{entry['name']}: missing")
    if path.stat().st_size != entry["size"]:
        raise VerificationError(f"{entry['name']}: size {path.stat().st_size}, pinned {entry['size']}")
    got = sha256_file(path)
    if got != entry["sha256"]:
        raise VerificationError(f"{entry['name']}: sha256 {got}, pinned {entry['sha256']}")


def fetch(entry: dict, target: pathlib.Path) -> None:
    print(f"  download {entry['url']}")
    tmp = target.with_suffix(target.suffix + ".part")
    req = urllib.request.Request(entry["url"], headers={"User-Agent": "dnd-builder-offline-build"})
    with urllib.request.urlopen(req, timeout=120) as resp, tmp.open("wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)
    try:
        verify(tmp, entry)
    except VerificationError:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(target)


def ensure_pinned(manifest: dict, allow_download: bool) -> None:
    for entry in manifest["files"]:
        target = OUT / entry["name"]
        try:
            verify(target, entry)
            continue
        except VerificationError as err:
            if not allow_download:
                raise
            print(f"  {err}; fetching")
        fetch(entry, target)


def kb(n: int) -> str:
    return f"{n / 1024:,.0f} KB" if n < 1 << 20 else f"{n / (1 << 20):.2f} MB"


def gz_size(path: pathlib.Path) -> int:
    return len(gzip.compress(path.read_bytes(), 9, mtime=0))


def write_pack_json(names: list[str]) -> None:
    pack = {n: {"size": (OUT / n).stat().st_size, "sha256": sha256_file(OUT / n)} for n in sorted(names)}
    (OUT / "pack.json").write_text(json.dumps(pack, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def report(names: list[str]) -> None:
    print(f"\n{'file':62} {'size':>10} {'gzip':>10}")
    total = total_gz = 0
    for n in names:
        p = OUT / n
        s, g = p.stat().st_size, gz_size(p)
        total, total_gz = total + s, total_gz + g
        print(f"{n:62} {kb(s):>10} {kb(g):>10}")
    print(f"{'total':62} {kb(total):>10} {kb(total_gz):>10}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="verify the pack in frontend/public/pyodide, build nothing")
    args = ap.parse_args(argv)
    manifest = load_manifest()
    names = [e["name"] for e in manifest["files"]] + ["app.zip", "fonts.zip"]
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        if args.check:
            ensure_pinned(manifest, allow_download=False)
            print("pinned files verified")
            return 0
        print("pinned files:")
        ensure_pinned(manifest, allow_download=True)
    except (VerificationError, OSError) as err:
        print(f"STOP: {err}", file=sys.stderr)
        return 2
    print("app.zip / fonts.zip:")
    write_zip(OUT / "app.zip", app_files())
    write_zip(OUT / "fonts.zip", font_files())
    write_pack_json(names)
    report(names)
    print(f"\napp.zip sha256 {sha256_file(OUT / 'app.zip')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
