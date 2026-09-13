"""Test-wide isolation from the user's real campaign runtime.

Mirrors engine/tests/conftest.py's core mechanism. Several files in this
directory dynamically import skills/dnd/display/dnd-display-app.py (or
send.py) via importlib.util, and those modules write to the runtime dir
(`rt("text_log.json")`, `rt("stats.json")`, ...) as a side effect of ordinary
calls. Tests that never set DND_CAMPAIGN_ROOT before that import would
otherwise write straight into the live ~/.claude/dnd/.runtime/.

Every test in this directory now gets a throwaway campaign root by default.
Tests that manage their own root (setting the env var directly inside a
setUpClass, e.g. tests/test_chunk_dedup.py) simply set the variable again
afterwards and win, since this is a plain environment variable applied in
order.

There is no `live`-marker exemption here (unlike engine/tests/conftest.py) --
the live-marked test that talks to the user's real running display lives
under engine/tests/, not here.

DND_RUNTIME_DIR takes priority over DND_CAMPAIGN_ROOT in both
skills/dnd/scripts/paths.py:runtime_dir() and the fallback resolver in
skills/dnd/display/runtime_paths.py -- it's a real, documented, supported
override (see CHANGELOG.md), also used deliberately by
tests/test_autosave_checkpoint.py. If it's ever set in the ambient
environment (a developer's shell, or a leaked/failed teardown elsewhere),
setting DND_CAMPAIGN_ROOT alone does NOT achieve isolation -- it's silently
ignored. This fixture clears it every test.

IMPORTANT for anyone adding a new test here: if you dynamically import
anything from skills/dnd/display/ (via importlib.util) from a module- or
class-scoped fixture, or from unittest's setUpClass, you MUST set
DND_CAMPAIGN_ROOT (and clear DND_RUNTIME_DIR) YOURSELF, immediately before
that import. This autouse fixture is function-scoped and runs AFTER
module/class-scoped fixtures and setUpClass, so it does NOT protect them --
see engine/tests/test_sanitizer.py, tests/test_milestone_counter.py, and
tests/test_phone_presence.py for the pattern to copy.
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
