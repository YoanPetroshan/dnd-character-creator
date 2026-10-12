"""Repo-wide import-boundary check.

The whole point of this app is that nothing outside `chargen/` can drag in
the source repo's play engine (`engine/`, `skills/`, or any of its modules
like `library`, `paths`, `lookup`, `char_state_schema`, `char_state_sync`,
`char_state_derive`) or a server/model dependency `chargen` itself must
never see. An earlier version of this test only denied five module names
and only scanned `chargen/` — it would not have caught an `import library`
anywhere else in the tree, or a stray `engine`/`skills` directory landing
back in the repo (exactly what happened once already; see the plan's Task 1
incident). This version is an allowlist walk over every `.py` file in the
repo instead: anything not stdlib, not `chargen`, and not one of the
declared third-party dependencies is a violation, full stop.

Two narrow, explicit exemptions exist, both already known-and-intentional
(see the final review, I6/Minor 7):

- `chargen/cli.py` has one lazy `import library` inside `_save_to_library()`,
  behind a `--save` CLI flag no test exercises. It cannot be fixed without
  touching `chargen/`, which must stay byte-identical to the source repo.
- `tests/test_chargen_build.py`'s `RoundTripTest` (class-level
  `@unittest.skip`) and one skipped test method in `tests/test_chargen_cli.py`
  contain `import paths` / `import library` / `import char_state_derive` /
  `import char_state_schema` calls that are ported, dead-by-design code —
  they never run. Only the decorated (skipped) class/function bodies are
  exempted, not the rest of either file.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The declared third-party dependencies this repo actually uses, across
# both the root requirements.txt (this app's v1 code) and server/
# requirements.txt (v2's Flask backend) — there is no single combined
# manifest, so this set is the closest thing to one. Everything else must
# be stdlib or `chargen`.
ALLOWED_THIRD_PARTY = {"flask", "flask_cors", "werkzeug", "yaml", "pypdf", "fpdf", "pytest"}

STDLIB_MODULES = set(sys.stdlib_module_names)

_EXCLUDED_DIR_PARTS = {".venv", "venv", "__pycache__", ".git"}

# This app's own first-party, repo-root modules (app.py, storage.py, ...) —
# these import each other freely; the invariant this test defends is that
# NONE of them (or chargen) reach out to the source repo's play engine, not
# that they can't import their own siblings.
LOCAL_MODULES = {p.stem for p in ROOT.glob("*.py")} | {"chargen", "tests"}

# The v2 builder's own first-party packages, all living under server/
# (server/app.py, server/catalog/, server/engine/, server/export.py) — v2's
# counterparts to chargen. Deliberately NOT folded into the blanket
# LOCAL_MODULES set above and NOT allowed from arbitrary paths: "engine" is
# literally one of the exact module names this test exists to catch (see
# the module docstring), so this exemption only applies to imports from
# inside server/ itself — an `import engine` anywhere else in the repo is
# still exactly the violation this test is designed to flag.
SERVER_LOCAL_MODULES = {"catalog", "engine", "export", "export_fields", "markdown_export", "pdf_export", "test_export", "kitchen_sink", "c7c_helpers", "test_feat_tail", "test_types_drift"}

# The one lazy import chargen/cli.py is allowed to keep — see module
# docstring above and final-review.md's I6/Minor 7.
_CLI_LAZY_IMPORT_EXEMPTION = (pathlib.Path("chargen") / "cli.py", "library")


def _iter_repo_py_files():
    for py in sorted(ROOT.rglob("*.py")):
        rel = py.relative_to(ROOT)
        if _EXCLUDED_DIR_PARTS & set(rel.parts):
            continue
        yield py, rel


def _decorator_is_skip(dec: ast.expr) -> bool:
    target = dec.func if isinstance(dec, ast.Call) else dec
    try:
        text = ast.unparse(target)
    except Exception:
        return False
    return text == "skip" or text.endswith(".skip")


def _skipped_line_ranges(tree: ast.AST) -> list[tuple[int, int]]:
    """Line ranges of every class/function carrying an @unittest.skip(...)
    (or bare @skip) decorator — imports inside these never actually run."""
    ranges = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(_decorator_is_skip(d) for d in node.decorator_list):
                ranges.append((node.lineno, getattr(node, "end_lineno", node.lineno)))
    return ranges


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
        skipped_ranges = _skipped_line_ranges(tree) if rel.parts[0] == "tests" else []

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
                if rel.parts[0] == "server" and top in SERVER_LOCAL_MODULES:
                    continue
                if (rel, top) == _CLI_LAZY_IMPORT_EXEMPTION:
                    continue
                if any(start <= lineno <= end for start, end in skipped_ranges):
                    continue
                offenders.append(f"{rel}:{lineno}: import {mod}")

    assert offenders == [], offenders
