"""Repo-wide import-boundary check.

The whole point of this guard is that nothing in the repo can drag in
the old first-generation play engine (`engine/`, `skills/`, or any of its modules
like `library`, `paths`, `lookup`, `char_state_schema`, `char_state_sync`,
`char_state_derive`) or a server/model dependency `chargen` itself must
never see. An earlier version of this test only denied five module names
and only scanned `chargen/` — it would not have caught an `import library`
anywhere else in the tree, or a stray `engine`/`skills` directory landing
back in the repo (exactly what happened once already; see the plan's Task 1
incident). This version is an allowlist walk over every `.py` file in the
repo instead: anything not stdlib, not `chargen`, and not one of the
declared third-party dependencies is a violation, full stop.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The declared third-party dependencies this repo actually uses, across
# both the root requirements.txt (which only includes server/requirements.txt;
# the v1 root code was removed in D-5) and server/requirements.txt (v2's Flask
# backend). Everything else must be stdlib or `chargen`.
ALLOWED_THIRD_PARTY = {"flask", "flask_cors", "werkzeug", "yaml", "pypdf", "fpdf", "pytest"}

STDLIB_MODULES = set(sys.stdlib_module_names)

_EXCLUDED_DIR_PARTS = {".venv", "venv", "__pycache__", ".git"}

# First-party repo-root modules (none since the v1 root files were removed in
# D-5, but any new root *.py would be allowed to import its siblings) — the
# invariant this test defends is that NONE of them (or chargen) reach out to
# the source repo's play engine.
LOCAL_MODULES = {p.stem for p in ROOT.glob("*.py")} | {"chargen", "tests"}

# The v2 builder's own first-party packages, all living under server/
# (server/app.py, server/catalog/, server/engine/, server/export.py) — v2's
# counterparts to chargen. Deliberately NOT folded into the blanket
# LOCAL_MODULES set above and NOT allowed from arbitrary paths: "engine" is
# literally one of the exact module names this test exists to catch (see
# the module docstring), so this exemption only applies to imports from
# inside server/ itself — an `import engine` anywhere else in the repo is
# still exactly the violation this test is designed to flag.
# "service" is server/service.py, the framework-free API (O0); "app" is server/app.py (the root app.py was removed in D-5, so it is no longer a LOCAL_MODULES stem).
SERVER_LOCAL_MODULES = {"app", "catalog", "engine", "export", "export_fields", "markdown_export", "pdf_export", "test_export", "kitchen_sink", "c7c_helpers", "perf_helpers", "test_feat_tail", "test_types_drift", "test_resolve_fuzz", "test_export_completeness", "i18n", "i18n_zoo", "export_labels", "test_export_baseline", "test_data_precedence", "test_export_labels", "test_pdf_export", "test_i18n_completeness", "service", "test_service", "service_requests", "test_service_baseline", "tools", "chartest", "test_chartest_harness", "test_export_completeness", "sheet_layout", "sheet_form", "sheet_data", "sheet_pdf"}

# O1: the two offline-pack files that drive the server packages from outside server/ (the fixture emitter runs natively
# with server/ and server/tests on sys.path; the harness runs inside Pyodide with the app mounted at /app/server).
OFFLINE_SERVER_USERS = {pathlib.Path("scripts") / "offline_fixtures.py", pathlib.Path("scripts") / "dev_sample_sheets.py", pathlib.Path("frontend") / "src" / "offline" / "harness.py"}

def _iter_repo_py_files():
    for py in sorted(ROOT.rglob("*.py")):
        rel = py.relative_to(ROOT)
        if _EXCLUDED_DIR_PARTS & set(rel.parts):
            continue
        yield py, rel


def test_engine_and_skills_directories_do_not_exist():
    """The Task 1 incident was an unauthorized copy of the source repo's
    engine/ and skills/ directories landing in this repo. This is the
    specific check that would have caught it immediately."""
    assert not (ROOT / "engine").exists()
    assert not (ROOT / "skills").exists()


def test_every_top_level_import_is_stdlib_chargen_or_a_declared_dependency():
    offenders = []
    for py, rel in _iter_repo_py_files():
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                candidates = [(alias.name, node.lineno) for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue  # relative import — always internal to its own package
                if not node.module:
                    continue
                candidates = [(node.module, node.lineno)]
            else:
                continue

            for mod, lineno in candidates:
                top = mod.split(".")[0]
                if (top in LOCAL_MODULES or top in ALLOWED_THIRD_PARTY
                        or top in STDLIB_MODULES):
                    continue
                if (rel.parts[0] == "server" or rel in OFFLINE_SERVER_USERS) and top in SERVER_LOCAL_MODULES:
                    continue
                offenders.append(f"{rel}:{lineno}: import {mod}")

    assert offenders == [], offenders
