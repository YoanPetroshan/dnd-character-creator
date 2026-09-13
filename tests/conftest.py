"""Test-wide isolation from the user's real character library.

`storage.py` (this repo's own module, not chargen's) defaults its storage
root to the real `~/.claude/dnd` -- the same directory the `dnd-app-bg-local`
play app uses for its live character library (see storage.py's module
docstring and README.md). A test that forgot to override that root before
calling `storage.save_yaml()`/`save_markdown()`/`save_pdf()`, or before
posting to `app.py`'s `/api/chargen/build`, would otherwise write straight
into that real, shared directory -- exactly the kind of accidental
production write this fixture exists to prevent in every test in this repo.

Every test in this directory now gets a throwaway campaign root by default:
this fixture points `DND_CAMPAIGN_ROOT` (the env var `storage.root_dir()`
reads) at a fresh `tmp_path_factory` directory before each test runs, so
`storage.characters_dir()` / `char_dir()` resolve under that temp directory
instead. Tests that manage their own root explicitly (setting the env var
themselves, e.g. via `monkeypatch.setenv` in a fixture) simply set the
variable again afterwards and win, since this is a plain environment
variable applied in order.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_campaign_root(tmp_path_factory, monkeypatch):
    root = tmp_path_factory.mktemp("dnd-root")
    (root / ".runtime").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(root))
    # DND_RUNTIME_DIR takes priority over DND_CAMPAIGN_ROOT wherever both are
    # read -- clear it so a stray/leaked value can't silently defeat the
    # isolation above.
    monkeypatch.delenv("DND_RUNTIME_DIR", raising=False)
    return root
