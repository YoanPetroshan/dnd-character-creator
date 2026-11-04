"""The CI workflow (.github/workflows/ci.yml) must run the same commands the README documents.

GitHub Actions cannot run here, so this parses the YAML and pins its shape: triggers, the four test jobs and their
commands (the README "Test" section is the source of truth for the commands), no secrets, pinned actions.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
README = (ROOT / "README.md").read_text(encoding="utf-8")

# job id -> the one shell command it runs after setup (the README form, with `pytest` for `.venv/bin/python -m pytest`)
EXPECTED_COMMANDS = {
    "server-bundle": "cd server && pytest -q -n auto",
    "server-srd-only": "cd server && env DND_OFFICIAL_DATA=none pytest -q -n auto",
    "root": "pytest -q",
    "frontend": "cd frontend && npm ci && npm run build && npm test",
}


def _load():
    # PyYAML (YAML 1.1) reads the bare key `on` as the boolean True
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def _run_steps(job):
    return [s["run"].strip() for s in job["steps"] if "run" in s]


def _readme_normalised():
    # the README spells the interpreter as the local venv (`../.venv/bin/python -m pytest`); CI has it on PATH
    return re.sub(r"(?:\.\./)?\.venv/bin/python -m pytest", "pytest", README)


def test_workflow_parses_and_has_exactly_the_expected_jobs():
    assert set(_load()["jobs"]) == set(EXPECTED_COMMANDS)


def test_triggers_are_push_to_main_and_pull_request():
    on = _load()["on"]
    assert set(on) == {"push", "pull_request"}
    assert on["push"] == {"branches": ["main"]}
    assert not on["pull_request"]  # no filters: every pull request


def test_each_job_runs_the_expected_command_last():
    jobs = _load()["jobs"]
    for name, cmd in EXPECTED_COMMANDS.items():
        runs = _run_steps(jobs[name])
        assert runs and runs[-1] == cmd, (name, runs)
        assert jobs[name]["runs-on"] == "ubuntu-latest"


def test_python_jobs_install_the_server_requirements_first():
    jobs = _load()["jobs"]
    for name in ("server-bundle", "server-srd-only", "root"):
        assert _run_steps(jobs[name])[0] == "pip install -r server/requirements.txt"


def test_commands_match_the_readme_test_commands():
    readme = _readme_normalised()
    for name, cmd in EXPECTED_COMMANDS.items():
        # the README shows `pytest -q` and says to add `-n auto` for the parallel run
        # CI additionally installs first (`npm ci`, from the lockfile the README mentions)
        assert cmd.replace(" -n auto", "").replace("npm ci && ", "") in readme, (name, cmd)
    assert "cd server && pytest -q -n auto" in readme
    assert "env DND_OFFICIAL_DATA=none pytest -q" in readme


def test_no_job_uses_secrets():
    data = _load()
    assert "secrets" not in yaml.safe_dump(data).lower()
    assert "${{" not in yaml.safe_dump(data)
    for job in data["jobs"].values():
        assert not any("env" in s and "secret" in str(s["env"]).lower() for s in job["steps"])


def test_actions_are_pinned_to_a_full_commit_sha_and_caches_are_on():
    jobs = _load()["jobs"]
    for name, job in jobs.items():
        uses = [s for s in job["steps"] if "uses" in s]
        assert uses, name
        for s in uses:
            assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", s["uses"]), s["uses"]
        setup = [s for s in uses if "setup-" in s["uses"]]
        assert setup and all(s.get("with", {}).get("cache") in ("pip", "npm") for s in setup), name
    assert _load()["permissions"] == {"contents": "read"}
