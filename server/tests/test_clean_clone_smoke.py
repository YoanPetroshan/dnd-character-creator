"""B5: the clean-clone smoke script (scripts/smoke_clean_clone.py).

Fast unit tests always run; the full smoke runs only with RUN_CLONE_SMOKE=1."""
import importlib.util
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "smoke_clean_clone.py"
PY = ROOT / ".venv" / "bin" / "python"


def _load():
    spec = importlib.util.spec_from_file_location("smoke_clean_clone", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["smoke_clean_clone"] = mod
    spec.loader.exec_module(mod)
    return mod


smoke = _load()


def test_env_has_no_dnd_variables_and_redirects_home(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_OFFICIAL_DATA", "/somewhere")
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", "/campaign")
    env = smoke.build_env(tmp_path / "home")
    assert not [k for k in env if k.startswith("DND_")]
    assert env["HOME"] == str(tmp_path / "home")
    assert env["PYTHONNOUSERSITE"] == "1"
    assert set(env) <= {"PATH", "HOME", "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"}


def _blocked_probe(code: str) -> str:
    """Run `code` in a subprocess after the blocker (never patch the pytest process itself)."""
    src = smoke.NETWORK_BLOCKER_SRC + "\nblock_network()\n" + code
    p = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, timeout=60)
    return p.stdout + p.stderr


def test_network_blocker_rejects_remote_and_allows_loopback():
    out = _blocked_probe("""
import socket
for call in (lambda: socket.create_connection(("93.184.216.34", 80), timeout=1),
             lambda: socket.getaddrinfo("example.com", 80),
             lambda: socket.socket().connect(("93.184.216.34", 80))):
    try:
        call()
        print("NOT BLOCKED")
    except OSError as e:
        print("blocked" if "network blocked" in str(e) else "other: " + str(e))
# loopback passes the guard: a closed local port is a plain refusal, not a block
for call in (lambda: socket.create_connection(("127.0.0.1", 1), timeout=1),
             lambda: socket.socket().connect(("127.0.0.1", 1))):
    try:
        call()
    except OSError as e:
        print("loopback-error-not-blocker" if "network blocked" not in str(e) else "WRONGLY BLOCKED")
print(socket.getaddrinfo("localhost", 80)[0][0] is not None)
""")
    lines = out.split()
    assert out.count("blocked") >= 3 and "NOT" not in out and "WRONGLY" not in out, out
    assert out.count("loopback-error-not-blocker") == 2, out
    assert lines[-1] == "True", out


def test_refuses_tracked_changes(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    run = lambda *a: subprocess.run(a, cwd=repo, check=True, capture_output=True)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    (repo / "a.txt").write_text("1")
    run("git", "add", "a.txt")
    run("git", "commit", "-qm", "x")
    (repo / "new.txt").write_text("u")
    assert smoke.tracked_changes(repo)[0] == [] and len(smoke.tracked_changes(repo)[1]) == 1
    (repo / "a.txt").write_text("2")
    assert len(smoke.tracked_changes(repo)[0]) == 1


@pytest.mark.skipif(not PY.exists(), reason="needs the repo .venv")
def test_missing_race_file_fails_with_a_clear_message(tmp_path):
    """Negative test: a clone without races.json must trip the pinned-count assertion."""
    clone = smoke.make_clone(ROOT, tmp_path)
    (clone / "server" / "data" / "official" / "races.json").unlink()
    rc, out = smoke.run_app_checks(clone, smoke.build_env(tmp_path / "home"), PY)
    assert rc != 0, out
    assert "catalog counts differ from the pinned bundle" in out or "Error" in out, out
    assert "races" in out, out


@pytest.mark.skipif(os.environ.get("RUN_CLONE_SMOKE") != "1", reason="set RUN_CLONE_SMOKE=1 to run the clean-clone smoke")
def test_full_clean_clone_smoke():
    tracked, _ = smoke.tracked_changes(ROOT)
    if tracked:
        pytest.skip("tracked changes: the smoke tests HEAD only")
    assert smoke.main([]) == 0
