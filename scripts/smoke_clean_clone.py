#!/usr/bin/env python3
"""B5 clean-clone smoke test: prove the COMMITTED tree alone runs the whole app.

What it does (stdlib only):
  1. refuses to run when `git status --porcelain` shows TRACKED changes (untracked files only warn);
  2. `git clone --quiet --no-local <repo> <tmp>/clone` (a fresh clone of HEAD, so ignored or uncommitted files
     cannot leak in);
  3. builds a minimal child environment: PATH, HOME=<tmp>/home (empty), PYTHONNOUSERSITE=1, no DND_* variables;
  4. runs the EXISTING main-checkout `.venv/bin/python` with cwd=<clone>/server. Installing packages is out of
     scope (dependencies are not data). A real fresh-venv check needs `pip download -r server/requirements.txt -d
     wheels` once while online, then `python -m venv v && v/bin/pip install --no-index --find-links wheels -r ...`;
  5. the child blocks the network, then asserts the app and the data come from the clone, the data source is
     `bundled`, the pinned catalog counts, resolves a fixed non-SRD draft (no problems) and exports
     yaml/markdown/pdf (the PDF proves the bundled fonts load);
  6. `--frontend`: symlinks the main checkout's frontend/node_modules into the clone (offline), builds the
     frontend there and GETs `/`;
  7. `--full-suite`: runs `pytest -q -n 4` in the clone's server dir with the same environment (0 failures, no
     5etools/official-data skips);
  8. removes the temp dir unless `--keep`. Exit code 0 on success, 1 on any failure.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The catalog sizes of the vendored bundle (see server/tests/test_data_bundle.py and DATA-SOURCES.md).
PINNED_COUNTS = {
    "classes": 12, "levels": 961, "features": 1783, "subclasses": 176, "races": 153, "subraces": 96,
    "traits": 1086, "backgrounds": 136, "items": 244, "spells": 936, "feats": 305, "spell_twins": 758,
    "classes_2024": 12,
}

# A filled, non-SRD draft: Wizard 5 (School of the Scribes, TCE), Hobgoblin (VGM), XGE spells (Absorb Elements,
# Catapult) in the spellbook, and the PHB feat Alert on the level-4 ASI. Every pending choice is already stored.
SMOKE_DRAFT = {
    "name": "Smoke", "ruleset": "mixed", "sources": [],
    "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 16, "WIS": 12, "CHA": 10}},
    "species": {"id": "hobgoblin-vgm", "choices": {}},
    "background": {"id": "acolyte", "choices": {"background:acolyte:languages": ["common", "dwarvish"]}},
    "equipment": {"choices": {"class:wizard:1:equipment-choice-0": ["quarterstaff"],
                              "class:wizard:1:equipment-choice-1": ["component-pouch"],
                              "class:wizard:1:equipment-choice-2": ["scholars-pack"],
                              "background:acolyte:equipment-choice-0": ["amulet"]},
                  "added": [], "skipped": False},
    "classes": [{"classId": "wizard", "level": 5, "subclassId": "scribes-tce", "choices": {
        "class:wizard:4:asi": ["feat:alert-phb"],
        "class:wizard:spells-cantrips": ["acid-splash", "blade-ward", "booming-blade", "chill-touch"],
        "class:wizard:1:prof-choice-0": ["skill-arcana", "skill-history"],
        "class:wizard:spellbook": ["absorb-elements", "catapult", "alarm", "burning-hands", "cause-fear",
                                   "charm-person", "chromatic-orb", "color-spray", "comprehend-languages",
                                   "detect-magic", "disguise-self", "distort-value", "earth-tremor",
                                   "expeditious-retreat"],
        "class:wizard:spells-known": ["absorb-elements", "catapult", "alarm", "burning-hands", "cause-fear",
                                      "charm-person", "chromatic-orb", "color-spray"]}}],
}
# Ids that must show up in the resolved sheet (they are all outside the SRD).
NON_SRD_IDS = ["scribes-tce", "hobgoblin-vgm", "absorb-elements", "catapult", "alert-phb"]

# Runs inside the child (and, standalone, in the unit tests). Patches the socket module so that only loopback
# targets are reachable.
NETWORK_BLOCKER_SRC = '''
import ipaddress as _ip
import socket as _socket

_LOOPBACK_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost"}


def _is_loopback(host):
    if host is None or host == "":
        return True  # wildcard bind / default lookup, no remote endpoint
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if not isinstance(host, str):
        return False
    host = host.strip("[]").split("%")[0]
    if host.lower() in _LOOPBACK_NAMES:
        return True
    try:
        return _ip.ip_address(host).is_loopback
    except ValueError:
        return False


def _blocked(host):
    return OSError("network blocked by the clean-clone smoke test: " + repr(host))


def _target_host(address):
    if isinstance(address, (tuple, list)) and address:
        return address[0]
    return address  # AF_UNIX path (str) is never a remote endpoint


def block_network():
    real_connect = _socket.socket.connect
    real_connect_ex = _socket.socket.connect_ex
    real_getaddrinfo = _socket.getaddrinfo
    real_create = _socket.create_connection

    def connect(self, address):
        if self.family in (_socket.AF_INET, _socket.AF_INET6) and not _is_loopback(_target_host(address)):
            raise _blocked(address)
        return real_connect(self, address)

    def connect_ex(self, address):
        if self.family in (_socket.AF_INET, _socket.AF_INET6) and not _is_loopback(_target_host(address)):
            raise _blocked(address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host):
            raise _blocked(host)
        return real_getaddrinfo(host, *args, **kwargs)

    def create_connection(address, *args, **kwargs):
        if not _is_loopback(_target_host(address)):
            raise _blocked(address)
        return real_create(address, *args, **kwargs)

    _socket.socket.connect = connect
    _socket.socket.connect_ex = connect_ex
    _socket.getaddrinfo = getaddrinfo
    _socket.create_connection = create_connection
'''

# The child program. `{...}` placeholders are filled with json.dumps values via str.replace (no format braces).
CHILD_SRC = r'''
import json, os, sys
from pathlib import Path

CLONE = Path(__CLONE__).resolve()
PINNED = json.loads(__PINNED__)
DRAFT = json.loads(__DRAFT__)
NON_SRD = json.loads(__NON_SRD__)
FRONTEND = __FRONTEND__

__BLOCKER__
block_network()

failures = []
def check(ok, msg):
    if not ok:
        failures.append(msg)

def inside(p):
    p = Path(p).resolve()
    return p == CLONE or CLONE in p.parents

stray = sorted(k for k in os.environ if k.startswith("DND_"))
check(not stray, "DND_* variables leaked into the child: %s" % stray)

import app as app_module
check(inside(app_module.__file__), "app module is outside the clone: %s" % app_module.__file__)
from catalog.official import paths
check(inside(paths.official_dir()), "official_dir() is outside the clone: %s" % paths.official_dir())
check(paths.data_source() == "bundled", "data_source() is %r, expected 'bundled'" % paths.data_source())
check(paths.has_official(), "the bundled official directory is empty or missing: %s" % paths.official_dir())

cat = app_module._catalog
counts = {k: (len(getattr(cat, k)) if hasattr(cat, k) else None) for k in PINNED}
bad = {k: "%s (expected %s)" % (counts[k], v) for k, v in PINNED.items() if counts[k] != v}
check(not bad, "catalog counts differ from the pinned bundle: %s" % bad)

if failures:
    print("SMOKE FAIL (data):"); [print("  - " + f) for f in failures]
    sys.exit(1)

client = app_module.app.test_client()
r = client.post("/api/resolve", json=DRAFT)
check(r.status_code == 200, "POST /api/resolve -> %s" % r.status_code)
res = r.get_json() or {}
check(res.get("problems") == [], "resolve problems: %s" % res.get("problems"))
blob = json.dumps(res)
for ident in NON_SRD:
    check(ident in blob, "non-SRD id %r is missing from the resolved sheet" % ident)

sizes = {}
for fmt, magic in (("yaml", None), ("markdown", None), ("pdf", b"%PDF")):
    e = client.post("/api/export/" + fmt, json=DRAFT)
    sizes[fmt] = len(e.data)
    check(e.status_code == 200, "POST /api/export/%s -> %s %s" % (fmt, e.status_code, e.data[:200]))
    if e.status_code == 200 and magic:
        check(e.data.startswith(magic), "the %s export does not start with %r" % (fmt, magic))
check(sizes.get("pdf", 0) > 10 * 1024, "the PDF is only %s bytes (fonts not loaded?)" % sizes.get("pdf"))

if FRONTEND:
    dist = CLONE / "frontend" / "dist"
    app_module.app.config["FRONTEND_DIST"] = dist
    g = client.get("/")
    check(g.status_code == 200, "GET / -> %s" % g.status_code)
    check(g.data == (dist / "index.html").read_bytes(), "GET / did not return the built index.html")
    check(b"<div id=\"root\"" in g.data or b"<script" in g.data, "GET / does not look like the SPA index.html")

if failures:
    print("SMOKE FAIL:"); [print("  - " + f) for f in failures]
    sys.exit(1)
print("SMOKE OK " + json.dumps({"counts": counts, "export_bytes": sizes, "frontend": bool(FRONTEND)}))
'''


class SmokeError(Exception):
    pass


def build_env(home: Path) -> dict[str, str]:
    """The minimal child environment: PATH, an empty HOME, no user site, and never a DND_* variable."""
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(home), "PYTHONNOUSERSITE": "1",
           "PYTHONDONTWRITEBYTECODE": "1"}
    assert not any(k.startswith("DND_") for k in env)
    return env


def tracked_changes(repo: Path) -> tuple[list[str], list[str]]:
    out = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=True).stdout
    lines = [ln for ln in out.splitlines() if ln.strip()]
    untracked = [ln for ln in lines if ln.startswith("??")]
    return [ln for ln in lines if not ln.startswith("??")], untracked


def make_clone(repo: Path, tmp: Path) -> Path:
    clone = tmp / "clone"
    (tmp / "home").mkdir(exist_ok=True)
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(repo), str(clone)], check=True,
                   capture_output=True, text=True)
    return clone


def child_source(clone: Path, frontend: bool) -> str:
    return (CHILD_SRC.replace("__CLONE__", json.dumps(str(clone))).replace("__PINNED__", repr(json.dumps(PINNED_COUNTS)))
            .replace("__DRAFT__", repr(json.dumps(SMOKE_DRAFT))).replace("__NON_SRD__", repr(json.dumps(NON_SRD_IDS)))
            .replace("__FRONTEND__", "True" if frontend else "False").replace("__BLOCKER__", NETWORK_BLOCKER_SRC))


def run_app_checks(clone: Path, env: dict[str, str], python: Path, frontend: bool = False,
                   timeout: int = 600) -> tuple[int, str]:
    """Run the network-blocked data/resolve/export checks in a child. Returns (returncode, combined output)."""
    p = subprocess.run([str(python), "-c", child_source(clone, frontend)], cwd=clone / "server", env=env,
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def build_frontend(clone: Path, env: dict[str, str], main_repo: Path) -> None:
    nm = main_repo / "frontend" / "node_modules"
    if not nm.is_dir():
        raise SmokeError(f"{nm} is missing: run `npm ci` in the main checkout once (offline builds reuse it)")
    link = clone / "frontend" / "node_modules"
    if not link.exists():
        link.symlink_to(nm)
    p = subprocess.run(["npm", "run", "build"], cwd=clone / "frontend", env=env, capture_output=True, text=True,
                       timeout=900)
    if p.returncode != 0:
        raise SmokeError("npm run build failed:\n" + (p.stdout + p.stderr)[-3000:])
    if not (clone / "frontend" / "dist" / "index.html").is_file():
        raise SmokeError("npm run build produced no frontend/dist/index.html")


def run_full_suite(clone: Path, env: dict[str, str], python: Path) -> str:
    p = subprocess.run([str(python), "-m", "pytest", "-q", "-n", "4", "-rs", "-p", "no:cacheprovider"],
                       cwd=clone / "server", env=env, capture_output=True, text=True, timeout=3600)
    out = p.stdout + p.stderr
    tail = out[-3000:]
    if p.returncode != 0:
        raise SmokeError("the full suite failed in the clone:\n" + tail)
    data_skips = [ln for ln in out.splitlines() if ln.startswith("SKIPPED") and re.search(r"5etools|official", ln, re.I)]
    if data_skips:
        raise SmokeError("the full suite skipped tests for missing official data:\n" + "\n".join(data_skips[:20]))
    summary = [ln for ln in out.splitlines() if re.search(r"\d+ passed", ln)]
    return summary[-1] if summary else tail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--frontend", action="store_true", help="also build the frontend in the clone and GET /")
    ap.add_argument("--full-suite", action="store_true", help="also run the whole server pytest suite in the clone")
    ap.add_argument("--keep", action="store_true", help="keep the temp directory")
    args = ap.parse_args(argv)

    t0 = time.time()
    tracked, untracked = tracked_changes(REPO)
    if tracked:
        print("refusing to run: tracked changes would not be in the clone (commit or stash them first):")
        print("\n".join("  " + ln for ln in tracked))
        return 1
    if untracked:
        print(f"warning: {len(untracked)} untracked path(s) are not in the clone (that is the point of this test)")

    python = REPO / ".venv" / "bin" / "python"
    if not python.exists():
        print(f"error: {python} not found (create the venv with scripts/setup.sh first)")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="dnd-clean-clone-"))
    code = 0
    try:
        step = time.time()
        clone = make_clone(REPO, tmp)
        print(f"[1/4] cloned HEAD into {clone} ({time.time() - step:.1f}s)")
        env = build_env(tmp / "home")

        step = time.time()
        if args.frontend:
            build_frontend(clone, env, REPO)
            print(f"[2/4] frontend built in the clone ({time.time() - step:.1f}s)")
        else:
            print("[2/4] frontend build skipped (use --frontend)")

        step = time.time()
        rc, out = run_app_checks(clone, env, python, frontend=args.frontend)
        print(f"[3/4] app checks, network blocked: exit {rc} ({time.time() - step:.1f}s)")
        print(out)
        if rc != 0:
            raise SmokeError("the app checks failed in the clean clone")

        if args.full_suite:
            step = time.time()
            summary = run_full_suite(clone, env, python)
            print(f"[4/4] full suite in the clone: {summary} ({time.time() - step:.1f}s)")
        else:
            print("[4/4] full suite skipped (use --full-suite)")
        print(f"CLEAN-CLONE SMOKE PASSED in {time.time() - t0:.1f}s")
    except SmokeError as exc:
        print(f"CLEAN-CLONE SMOKE FAILED: {exc}")
        code = 1
    except subprocess.CalledProcessError as exc:
        print(f"CLEAN-CLONE SMOKE FAILED: {exc}\n{exc.stderr or ''}")
        code = 1
    finally:
        if args.keep:
            print(f"kept {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
