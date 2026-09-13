"""Test-wide isolation from the user's real campaign runtime.

Several modules write to `state.runtime_dir()` as a side effect of ordinary
calls — `log_event` on every guard hit, dice request, agent start and turn
boundary; `heartbeat`; the display fallback. Tests that never set
DND_CAMPAIGN_ROOT therefore wrote straight into the live
`~/.claude/dnd/.runtime/`, mixing hundreds of test artifacts into the real
engine.log that the runbook tells the user to read when something goes wrong.

Every test now gets a throwaway campaign root by default. Tests that manage
their own root (`monkeypatch.setenv("DND_CAMPAIGN_ROOT", ...)` inside a
fixture) simply set the variable again afterwards and win — the two do not
conflict, since this is a plain environment variable and monkeypatch applies
them in order.

The one deliberate exception is the `live` marker: engine/tests/test_live_turn.py
runs a real turn against the user's real, running display and real campaign,
reading `state.text_log_count()` and `state.runtime_dir()` directly. Pointing
it at a temp directory would make it silently test nothing.

DND_RUNTIME_DIR takes priority over DND_CAMPAIGN_ROOT in both
skills/dnd/scripts/paths.py:runtime_dir() and the fallback resolver in
skills/dnd/display/runtime_paths.py -- it's a real, documented, supported
override (see CHANGELOG.md), also used deliberately by
tests/test_autosave_checkpoint.py in the repo-root suite. If it's ever set in
the ambient environment (a developer's shell, or a leaked/failed teardown
elsewhere), setting DND_CAMPAIGN_ROOT alone does NOT achieve isolation --
it's silently ignored. This fixture clears it every test (except for `live`).

IMPORTANT for anyone adding a new test here: if you dynamically import
anything from skills/dnd/display/ (via importlib.util) from a module- or
class-scoped fixture, or from unittest's setUpClass, you MUST set
DND_CAMPAIGN_ROOT (and clear DND_RUNTIME_DIR) YOURSELF, immediately before
that import. This autouse fixture is function-scoped and runs AFTER
module/class-scoped fixtures and setUpClass, so it does NOT protect them --
see test_sanitizer.py's `app`/`wrapper` fixtures for the pattern to copy.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_campaign_root(request, tmp_path_factory, monkeypatch):
    if "live" in request.keywords:
        return None
    root = tmp_path_factory.mktemp("dnd-root")
    (root / ".runtime").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(root))
    # DND_RUNTIME_DIR takes priority over DND_CAMPAIGN_ROOT wherever both are
    # read -- clear it so a stray/leaked value can't silently defeat the
    # isolation above.
    monkeypatch.delenv("DND_RUNTIME_DIR", raising=False)
    return root
