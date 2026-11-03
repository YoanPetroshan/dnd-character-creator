"""Test-wide isolation from the user's real character library.

The default storage root is the real `~/.claude/dnd` -- the same directory the
`dnd-app-bg-local` play app uses for its live character library, and where
`chargen.sync --official` puts the 5etools data. (The v1 root `storage.py` that
originally wrote there was removed in D-5; chargen's CLI still resolves paths
from `DND_CAMPAIGN_ROOT`.) A test that forgot to override that root could write
into that real, shared directory -- exactly the accidental write this fixture
prevents in every test in this directory.

Every test in this directory gets a throwaway campaign root by default:
this fixture points `DND_CAMPAIGN_ROOT` at a fresh `tmp_path_factory` directory
before each test runs. Tests that manage their own root explicitly (setting the env var
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
