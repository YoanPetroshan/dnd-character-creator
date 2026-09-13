"""Regression test for the DND_RUNTIME_DIR isolation bypass (code-review
finding, fix round 2).

skills/dnd/scripts/paths.py:runtime_dir() and the fallback resolver in
skills/dnd/display/runtime_paths.py both check DND_RUNTIME_DIR FIRST, before
ever consulting DND_CAMPAIGN_ROOT -- it's a real, documented, supported
override (see CHANGELOG.md; tests/test_autosave_checkpoint.py already uses
it deliberately, scoped to its own setUp/tearDown). Before this fix, if
DND_RUNTIME_DIR was ever set in the ambient environment (a developer's
shell, or a leaked/failed teardown elsewhere), setting DND_CAMPAIGN_ROOT in
any of the isolation fixtures added for the original data-corruption bug
was silently ignored -- the exact original corruption path stayed fully
reachable even with every DND_CAMPAIGN_ROOT fix in place and looking
correct. Confirmed concretely in review: running
`DND_RUNTIME_DIR=<scratch> pytest engine/tests/test_sanitizer.py` made the
`app` fixture resolve LOG_FILE under the scratch dir instead of its own
tmp root.

The fix clears DND_RUNTIME_DIR (in addition to setting DND_CAMPAIGN_ROOT) at
every one of the six isolation sites: both conftest.py autouse fixtures, and
the four in-file blocks in engine/tests/test_sanitizer.py (`app` and
`wrapper` fixtures), tests/test_milestone_counter.py (`setUpClass`), and
tests/test_phone_presence.py (`_load_app_module()`).

This test proves the fix the same way the reviewer's own demonstration did:
point DND_RUNTIME_DIR at a real-looking (but definitely disposable) scratch
directory, with DND_CAMPAIGN_ROOT deliberately left UNSET (simulating the
worst case -- a bare env leak with no other isolation in effect), and
re-run the exact combined trigger invocation that caused the original
incident, now extended to also cover tests/test_phone_presence.py (the
sixth fixed site). Because skills/dnd/display/runtime_paths.py caches its
resolved path once per process, this has to run in a genuinely separate
subprocess to get an honest read -- a same-process check would just see
whatever this session's conftest.py already cached.

Safety note: DND_RUNTIME_DIR unconditionally wins over DND_CAMPAIGN_ROOT in
both resolvers (see the two files named above), so even in a total
regression of this fix, any leaked write lands in the scratch directory
created below -- never in the real ~/.claude/dnd/.runtime -- making this
test safe to run on its own merits, independent of whether the fix holds.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_RUNTIME_DIR = Path("~/.claude/dnd/.runtime").expanduser()


def test_ambient_dnd_runtime_dir_does_not_leak_into_isolated_tests():
    scratch = Path(tempfile.mkdtemp(prefix="dnd-runtime-dir-bypass-scratch-"))
    assert scratch.is_dir()
    assert list(scratch.iterdir()) == []  # sanity: starts empty

    # Snapshot the real runtime files' mtimes before touching anything, so a
    # regression here is caught immediately rather than trusting the
    # subprocess's own isolation.
    real_log = REAL_RUNTIME_DIR / "text_log.json"
    real_stats = REAL_RUNTIME_DIR / "stats.json"
    before_log_mtime = real_log.stat().st_mtime if real_log.exists() else None
    before_stats_mtime = real_stats.stat().st_mtime if real_stats.exists() else None

    env = dict(os.environ)
    env["DND_RUNTIME_DIR"] = str(scratch)
    # Deliberately unset DND_CAMPAIGN_ROOT -- the worst case, a bare
    # DND_RUNTIME_DIR leak with nothing else set, exactly as the reviewer
    # demonstrated.
    env.pop("DND_CAMPAIGN_ROOT", None)

    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "engine/tests/",
            # This file lives under engine/tests/ and its own subprocess
            # target list would otherwise include itself -- collecting (and
            # re-running) test_runtime_dir_regression.py from inside its own
            # subprocess, which spawns another identical subprocess, which
            # collects and re-runs itself again, and so on. --ignore breaks
            # that self-referential explosion.
            "--ignore=engine/tests/test_runtime_dir_regression.py",
            "tests/test_chunk_dedup.py",
            "tests/test_display_robustness.py",
            "tests/test_milestone_counter.py",
            "tests/test_phone_presence.py",
            "-q",
        ],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 0, (
        "combined suite failed under a leaked DND_RUNTIME_DIR:\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )

    # The real proof: if the bypass were still present, POST-driven writes
    # from test_milestone_counter.py (/stats) and test_chunk_dedup.py
    # (/chunk) would land under the scratch dir, since DND_RUNTIME_DIR wins
    # over DND_CAMPAIGN_ROOT in both resolvers. A fixed test suite leaves it
    # untouched -- every fixture/setUpClass pops DND_RUNTIME_DIR before its
    # own dynamic import.
    leaked = list(scratch.iterdir())
    assert leaked == [], (
        f"DND_RUNTIME_DIR bypass regression: the scratch dir received writes "
        f"{leaked!r} -- one of the six isolation sites stopped clearing "
        "DND_RUNTIME_DIR before its dynamic import."
    )

    # And, as always, the real files must show zero drift.
    after_log_mtime = real_log.stat().st_mtime if real_log.exists() else None
    after_stats_mtime = real_stats.stat().st_mtime if real_stats.exists() else None
    assert after_log_mtime == before_log_mtime, (
        "real text_log.json mtime changed during the DND_RUNTIME_DIR "
        "regression test -- STOP, this must not happen"
    )
    assert after_stats_mtime == before_stats_mtime, (
        "real stats.json mtime changed during the DND_RUNTIME_DIR "
        "regression test -- STOP, this must not happen"
    )
