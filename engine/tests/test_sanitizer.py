import importlib.util
import os
import sys
import tempfile
from pathlib import Path

import pytest

DISPLAY_APP = Path(__file__).resolve().parents[2] / "skills" / "dnd" / "display" / "dnd-display-app.py"
WRAPPER = Path(__file__).resolve().parents[2] / "skills" / "dnd" / "display" / "wrapper.py"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    # skills/dnd/display/runtime_paths.py resolves and caches its runtime
    # dir (RT) ONCE, at first import, for the lifetime of the process --
    # whichever DND_CAMPAIGN_ROOT is in effect at THIS import wins
    # permanently, regardless of what any later test sets it to. This
    # fixture is module-scoped, so it runs BEFORE conftest.py's
    # function-scoped autouse isolate_campaign_root fixture applies to the
    # first test in this module -- it cannot rely on that fixture's
    # ordering and must set its own isolated DND_CAMPAIGN_ROOT here, before
    # the dynamic import, with save/restore since this fixture has no
    # `monkeypatch` (module-scoped fixtures can't use the function-scoped
    # monkeypatch fixture). DND_RUNTIME_DIR takes priority over
    # DND_CAMPAIGN_ROOT wherever either is read, so it must be cleared too --
    # otherwise a stray/leaked DND_RUNTIME_DIR would silently bypass the
    # DND_CAMPAIGN_ROOT isolation set below.
    #
    # This fixture used to stop at the env vars, but that's only half the
    # fix: runtime_paths (and paths) cache their resolved dir in a MODULE
    # attribute at first import, once per process. pytest runs every test
    # file in one process, so if anything imported either module earlier
    # (e.g. tests/test_chunk_dedup.py, which already had this exact fix),
    # that first import wins permanently regardless of what DND_CAMPAIGN_ROOT
    # this fixture sets afterward -- the dynamic import below would silently
    # reuse a stale, possibly-already-deleted tmp dir instead of this one.
    # Purging both names before the import forces a fresh resolution against
    # the env vars just set, matching test_chunk_dedup.py's _load_module().
    sys.modules.pop("runtime_paths", None)
    sys.modules.pop("paths", None)
    tmp_root = tmp_path_factory.mktemp("test_sanitizer_app_root")
    (tmp_root / ".runtime").mkdir(parents=True, exist_ok=True)
    prev_root = os.environ.get("DND_CAMPAIGN_ROOT")
    prev_runtime_dir = os.environ.get("DND_RUNTIME_DIR")
    os.environ["DND_CAMPAIGN_ROOT"] = str(tmp_root)
    os.environ.pop("DND_RUNTIME_DIR", None)
    try:
        spec = importlib.util.spec_from_file_location("dnd_display_app", DISPLAY_APP)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # missing optional deps in this env
            pytest.skip(f"cannot import display app: {exc}")
        return module
    finally:
        if prev_root is None:
            os.environ.pop("DND_CAMPAIGN_ROOT", None)
        else:
            os.environ["DND_CAMPAIGN_ROOT"] = prev_root
        if prev_runtime_dir is not None:
            os.environ["DND_RUNTIME_DIR"] = prev_runtime_dir


@pytest.fixture(scope="module")
def wrapper(tmp_path_factory):
    # wrapper.py also does `from runtime_paths import rt` -- same
    # first-import-wins caching hazard as the `app` fixture above. This
    # fixture is module-scoped too, so it can run before conftest.py's
    # autouse isolate_campaign_root fixture applies (e.g. if only
    # wrapper-based tests in this module are selected to run). Set an
    # isolated DND_CAMPAIGN_ROOT before the dynamic import, with save/restore.
    # DND_RUNTIME_DIR takes priority over DND_CAMPAIGN_ROOT wherever either
    # is read, so it must be cleared too -- otherwise a stray/leaked
    # DND_RUNTIME_DIR would silently bypass the isolation set below.
    #
    # Same first-import-wins caching hazard as the `app` fixture above --
    # runtime_paths (and paths) cache their resolved dir at first import, so
    # a stale binding from an earlier test file must be purged before this
    # import too, or it silently reuses that earlier (possibly already
    # torn-down) tmp dir instead of this fixture's own.
    sys.modules.pop("runtime_paths", None)
    sys.modules.pop("paths", None)
    tmp_root = tmp_path_factory.mktemp("test_sanitizer_wrapper_root")
    (tmp_root / ".runtime").mkdir(parents=True, exist_ok=True)
    prev_root = os.environ.get("DND_CAMPAIGN_ROOT")
    prev_runtime_dir = os.environ.get("DND_RUNTIME_DIR")
    os.environ["DND_CAMPAIGN_ROOT"] = str(tmp_root)
    os.environ.pop("DND_RUNTIME_DIR", None)
    try:
        spec = importlib.util.spec_from_file_location("wrapper", WRAPPER)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            pytest.skip(f"cannot import wrapper: {exc}")
    finally:
        if prev_root is None:
            os.environ.pop("DND_CAMPAIGN_ROOT", None)
        else:
            os.environ["DND_CAMPAIGN_ROOT"] = prev_root
        if prev_runtime_dir is not None:
            os.environ["DND_RUNTIME_DIR"] = prev_runtime_dir

    # wrapper._sanitize() requires CAMP_FILE to exist. Create it in a temp dir.
    tmp_dir = tmp_path_factory.mktemp("wrapper_test")
    camp_file = tmp_dir / ".campaign"
    camp_file.touch()

    # Patch the module's CAMP_FILE to point to our temp file
    original_camp_file = module.CAMP_FILE
    module.CAMP_FILE = str(camp_file)

    yield module

    # Cleanup: restore original path
    module.CAMP_FILE = original_camp_file


# ─── Tests for dnd-display-app.py ────────────────────────────────────────────

def test_app_bulgarian_survives(app):
    text = "Промъквам се покрай стражата към Waterdeep"
    assert app._sanitize_input(text) == text


def test_app_prose_punctuation_survives(app):
    text = "Атакувам! (с advantage) [bonus] {extra} — готов ли си?"
    out = app._sanitize_input(text)
    # Check all prose punctuation characters survive
    for ch in ("!", "(", ")", "[", "]", "{", "}"):
        assert ch in out, f"Character {ch} was stripped from: {out}"


def test_app_dangerous_shell_chars_still_stripped(app):
    out = app._sanitize_input("rm -rf / ; echo $HOME `id` && ls | wc")
    for ch in ("$", "`", ";", "|", "&", ">", "<", "\\"):
        assert ch not in out


# ─── Tests for wrapper.py ────────────────────────────────────────────────────

def test_wrapper_bulgarian_survives(wrapper):
    """wrapper._sanitize() takes [CharName]: action payloads."""
    # Use "Everybody" to bypass known character check
    payload = "[Everybody]: Промъквам се покрай стражата към Waterdeep\n"
    result = wrapper._sanitize(payload)
    assert result is not None
    assert "Промъквам" in result


def test_wrapper_prose_punctuation_survives(wrapper):
    """wrapper._sanitize() preserves prose punctuation in action text."""
    payload = "[Everybody]: Атакувам! (с advantage) [bonus] {extra} — готов ли си?\n"
    result = wrapper._sanitize(payload)
    assert result is not None
    # Check all prose punctuation characters survive
    for ch in ("!", "(", ")", "[", "]", "{", "}"):
        assert ch in result, f"Character {ch} was stripped from: {result}"


def test_wrapper_dangerous_shell_chars_still_stripped(wrapper):
    """wrapper._sanitize() strips genuinely dangerous shell metacharacters."""
    payload = "[Everybody]: rm -rf / ; echo $HOME `id` && ls | wc\n"
    result = wrapper._sanitize(payload)
    assert result is not None
    for ch in ("$", "`", ";", "|", "&", ">", "<", "\\"):
        assert ch not in result, f"Dangerous character {ch} was not stripped from: {result}"
