"""S15 (audit MAINT-04): the paths the living documents cite exist, and the repository carries no personal paths.

Living documents: README.md, DATA-SOURCES.md, docs/API.md and the current-state files of docs/architecture/ (not the frozen
CHANGELOG-slices.md, which may name files that were later renamed or removed, not docs/superpowers/ which is history, and not
docs/DESIGN-HANDOFF.md which the design work owns). A cited path is a `server/...` or `frontend/...` token in backticks."""
from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIVING = ["README.md", "DATA-SOURCES.md", "docs/API.md",
          *(f"docs/architecture/{n}.md" for n in ("overview", "engine", "data", "i18n", "offline-pwa", "testing", "known-gaps"))]
TOKEN = re.compile(r"`((?:server|frontend)/[A-Za-z0-9_./()\[\]@+-]+)`")


def _cited(doc: str):
    text = (ROOT / doc).read_text(encoding="utf-8")
    for m in TOKEN.finditer(text):
        yield m.group(1).rstrip(".,:;")


def _exists(path: str) -> bool:
    if "*" in path or "<" in path:  # a glob or a placeholder
        return True
    if path.startswith(("frontend/dist", "frontend/node_modules")):  # build output, not in the repository
        return True
    return (ROOT / path.rstrip("/")).exists()


def test_every_path_a_living_document_cites_exists():
    missing = sorted({f"{doc}: {p}" for doc in LIVING for p in _cited(doc) if not _exists(p)})
    assert missing == [], "\n".join(missing)


def test_the_living_documents_exist_and_cite_something():
    for doc in LIVING:
        assert (ROOT / doc).is_file(), doc
    assert sum(1 for doc in LIVING for _ in _cited(doc)) > 50


# ---- no personal paths in the repository (the plans are history; the design handoff belongs to the design work) ----------------
_HOME = re.compile("/" + "Users" + "/[A-Za-z0-9._-]")  # a home directory of a person; spelled in parts so that this file does not contain it
EXCLUDED = ("docs/superpowers/plans/", "docs/DESIGN-HANDOFF.md")


def test_no_tracked_file_names_a_personal_home_directory():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    offenders = []
    for rel in files:
        if rel.startswith(EXCLUDED[0]) or rel == EXCLUDED[1] or not (ROOT / rel).is_file():
            continue
        try:
            text = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if _HOME.search(line):
                offenders.append(f"{rel}:{n}")
    assert offenders == [], offenders[:20]
