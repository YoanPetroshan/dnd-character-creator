"""S16 (audit MAINT-06): the Python dependencies are split and pinned.

`server/requirements.txt` is what the app needs to RUN (what a host installs); `server/requirements-dev.txt` adds the test
tools (pytest, xdist, execnet); `server/constraints.txt` pins every transitive package. The PDF libraries the offline pack
ships as wheels (scripts/offline_manifest.json) must have the same versions natively, or the native and the browser engine
can disagree."""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
TEST_TOOLS = {"pytest", "pytest-xdist", "execnet"}


def _pins(path: pathlib.Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.fullmatch(r"([A-Za-z0-9._-]+)==([A-Za-z0-9.+!_-]+)", line)
        assert m, f"{path.name}: not an exact pin: {line!r}"
        out[m.group(1).lower().replace("_", "-")] = m.group(2)
    return out


def test_runtime_requirements_have_no_test_tools_and_are_exact_pins():
    runtime = _pins(SERVER / "requirements.txt")
    assert runtime and not TEST_TOOLS & set(runtime)
    assert {"flask", "flask-cors", "pyyaml", "fpdf2", "pypdf", "waitress"} <= set(runtime)


def test_dev_requirements_include_the_runtime_file_and_the_test_tools():
    text = (SERVER / "requirements-dev.txt").read_text(encoding="utf-8")
    assert re.search(r"^-r requirements\.txt$", text, re.M)
    assert TEST_TOOLS == set(_pins(SERVER / "requirements-dev.txt"))


def test_the_root_requirements_install_the_dev_set():
    assert re.search(r"^-r server/requirements-dev\.txt$", (ROOT / "requirements.txt").read_text(encoding="utf-8"), re.M)


def test_constraints_pin_every_package_once_and_agree_with_the_requirements():
    constraints = _pins(SERVER / "constraints.txt")
    wanted = {**_pins(SERVER / "requirements.txt"), **_pins(SERVER / "requirements-dev.txt")}
    for name, version in wanted.items():
        assert constraints.get(name) == version, (name, constraints.get(name), version)
    # the transitive packages of the app and of pytest are pinned too
    for name in ("werkzeug", "jinja2", "markupsafe", "click", "blinker", "itsdangerous", "pillow", "fonttools", "defusedxml",
                 "pluggy", "iniconfig", "packaging", "pygments"):
        assert name in constraints, name


def test_the_pdf_libraries_have_the_versions_of_the_offline_pack():
    manifest = json.loads((ROOT / "scripts" / "offline_manifest.json").read_text(encoding="utf-8"))
    names = [f.get("name") or f.get("url", "").rsplit("/", 1)[-1] for f in manifest["files"]]
    pack = {}
    for n in names:
        m = re.match(r"(pillow|fonttools|defusedxml|fpdf2|pypdf)-([0-9][^-]*)-", n)
        if m:
            pack[m.group(1)] = m.group(2)
    assert set(pack) == {"pillow", "fonttools", "defusedxml", "fpdf2", "pypdf"}, pack
    constraints = _pins(SERVER / "constraints.txt")
    assert {k: constraints[k] for k in pack} == pack
