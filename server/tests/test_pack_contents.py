"""S12 (DATA-05 / MAINT-02): what the offline pack ships. The developer-only i18n tools stay out, and no module of the pack
is dead weight: every module that ships is imported by another module that ships (or is a named entry point)."""
from __future__ import annotations

import ast
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _build_offline():
    spec = importlib.util.spec_from_file_location("build_offline_under_test", ROOT / "scripts" / "build_offline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PACK = _build_offline().app_files()
PY = [f for f in PACK if f.endswith(".py") and f.startswith("server/")]

# Modules reached from outside the pack's own imports: the worker calls `service`, and the data loaders name modules by
# string (`DATA_OVERRIDES["where"]` = "catalog.reference_data:NAME").
ENTRY_POINTS = {"service"}


def _module_name(rel: str) -> str:
    parts = pathlib.PurePosixPath(rel[len("server/"):]).with_suffix("").parts
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _imported_names(rel: str) -> set[str]:
    tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    package = _module_name(rel).rsplit(".", 1)[0] if "." in _module_name(rel) and not rel.endswith("__init__.py") else _module_name(rel)
    if "." not in _module_name(rel) and not rel.endswith("__init__.py"):
        package = ""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package.split(".") if package else []
                anchor = anchor[: len(anchor) - (node.level - 1)] if node.level > 1 else anchor
                base = ".".join(filter(None, [*anchor, base]))
            found.add(base)
            found.update(f"{base}.{alias.name}" if base else alias.name for alias in node.names)
    return found


def test_the_developer_only_i18n_tools_are_not_in_the_pack():
    for tool in ("review_table", "ts_copy", "review_sheet", "terms_table", "glossary", "bracket_terms"):
        assert f"server/i18n/{tool}.py" not in PACK, tool


def test_the_data_bundle_builder_is_not_in_the_pack():
    assert "server/catalog/official/bundle.py" not in PACK


def test_every_module_of_the_pack_has_a_runtime_user_in_the_pack():
    modules = {_module_name(f): f for f in PY if not f.endswith("__init__.py")}
    imported: dict[str, set[str]] = {f: _imported_names(f) for f in PY}
    dead = []
    for name, rel in sorted(modules.items()):
        if name in ENTRY_POINTS:
            continue
        users = [other for other, names in imported.items() if other != rel and name in names]
        if not users:
            dead.append(name)
    assert not dead, f"modules in the offline pack that nothing in the pack imports: {dead}"
