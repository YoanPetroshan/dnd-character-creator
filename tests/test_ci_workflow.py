"""The CI workflow (.github/workflows/ci.yml) must run the same commands the README documents.

GitHub Actions cannot run here, so this parses the YAML and pins its shape: triggers, the four test jobs and their
commands (the README "Test" section is the source of truth for the commands), no secrets, pinned actions. It also pins
the GitHub Pages deploy (.github/workflows/pages.yml): triggers, permissions, the build steps and the pinned actions.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
PAGES = ROOT / ".github" / "workflows" / "pages.yml"
README = (ROOT / "README.md").read_text(encoding="utf-8")

# job id -> the one shell command it runs after setup (the README form, with `pytest` for `.venv/bin/python -m pytest`)
EXPECTED_COMMANDS = {
    "server-bundle": "cd server && pytest -q -n auto",
    "server-srd-only": "cd server && env DND_OFFICIAL_DATA=none pytest -q -n auto",
    "root": "pytest -q",
    "frontend": "cd frontend && npm ci && npm run build && npm test",
}


# The offline job runs several commands (pack build and pin check, Node equivalence test, the Pages-style PWA build and
# the check that the precache manifest lists every file); it is the one job that is not a single README command.
OFFLINE_JOB = "offline"
OFFLINE_RUNS = [
    "python scripts/build_offline.py",
    "python scripts/build_offline.py --check",
    "cd frontend && npm ci",
    "cd frontend && npm run test:offline",
    "cd frontend && VITE_BASE=/dnd-character-creator/ VITE_SERVERLESS=1 npm run build:offline",
    "cd frontend && REQUIRE_PRECACHE=1 npx vitest run src/offline/precache.dist.test.mjs",
]
PINNED = r"actions/[a-z-]+@[0-9a-f]{40} # v\d+\.\d+\.\d+"


def _load(path=WORKFLOW):
    # PyYAML (YAML 1.1) reads the bare key `on` as the boolean True
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if True in data and "on" not in data:
        data["on"] = data.pop(True)
    return data


def _run_steps(job):
    return [s["run"].strip() for s in job["steps"] if "run" in s]


def _readme_normalised():
    # the README spells the interpreter as the local venv (`../.venv/bin/python -m pytest`); CI has it on PATH
    return re.sub(r"(?:\.\./)?\.venv/bin/python -m pytest", "pytest", README)


def test_workflow_parses_and_has_exactly_the_expected_jobs():
    assert set(_load()["jobs"]) == set(EXPECTED_COMMANDS) | {OFFLINE_JOB}


def test_triggers_are_push_to_main_and_pull_request():
    on = _load()["on"]
    assert set(on) == {"push", "pull_request"}
    assert on["push"] == {"branches": ["main"]}
    assert not on["pull_request"]  # no filters: every pull request


def test_offline_job_builds_the_pack_runs_the_node_test_and_checks_the_precache_manifest():
    job = _load()["jobs"][OFFLINE_JOB]
    assert job["runs-on"] == "ubuntu-latest"
    assert _run_steps(job) == OFFLINE_RUNS
    # the pack is built before it is checked or used, and the precache check needs the built dist
    assert OFFLINE_RUNS.index("python scripts/build_offline.py") < OFFLINE_RUNS.index("cd frontend && npm run test:offline")
    assert "REQUIRE_PRECACHE=1" in OFFLINE_RUNS[-1]
    node = [s for s in job["steps"] if s.get("uses", "").startswith("actions/setup-node@")]
    assert node and node[0]["with"]["cache"] == "npm"


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
        # setup-python caches pip only where requirements are installed (the offline job installs none: the pack
        # builder is stdlib-only)
        setup = [s for s in uses if "setup-" in s["uses"] and not (name == OFFLINE_JOB and "setup-python" in s["uses"])]
        assert setup and all(s.get("with", {}).get("cache") in ("pip", "npm") for s in setup), name
    assert _load()["permissions"] == {"contents": "read"}


# ---- the GitHub Pages deploy ------------------------------------------------------------------------------

def test_pages_workflow_triggers_are_push_to_main_and_manual_dispatch():
    on = _load(PAGES)["on"]
    assert set(on) == {"push", "workflow_dispatch"}
    assert on["push"] == {"branches": ["main"]}


def test_pages_workflow_permissions_are_least_privilege():
    data = _load(PAGES)
    assert data["permissions"] == {"contents": "read"}
    assert set(data["jobs"]) == {"build", "deploy"}
    assert "permissions" not in data["jobs"]["build"]  # inherits contents: read only
    assert data["jobs"]["deploy"]["permissions"] == {"pages": "write", "id-token": "write"}
    assert data["jobs"]["deploy"]["needs"] == "build"
    assert data["jobs"]["deploy"]["environment"]["name"] == "github-pages"
    assert data["concurrency"] == {"group": "pages", "cancel-in-progress": False}


def test_pages_workflow_uses_no_secrets_and_only_the_page_url_expression():
    text = PAGES.read_text(encoding="utf-8")
    assert "secrets" not in text.lower()
    assert "token" not in text.lower().replace("id-token", "")
    assert re.findall(r"\$\{\{[^}]*\}\}", text) == ["${{ steps.deployment.outputs.page_url }}"]


def test_pages_workflow_pins_every_action_by_commit_sha_with_a_version_comment():
    text = PAGES.read_text(encoding="utf-8")
    uses = [ln.strip() for ln in text.splitlines() if ln.strip().lstrip("- ").startswith("uses:")]
    assert len(uses) == 6
    for ln in uses:
        assert re.fullmatch(r"-?\s*uses: " + PINNED, ln), ln
    wanted = {"checkout", "setup-python", "setup-node", "configure-pages", "upload-pages-artifact", "deploy-pages"}
    assert {re.search(r"actions/([a-z-]+)@", ln).group(1) for ln in uses} == wanted
    # the actions ci.yml already uses carry the very same pins
    ci = WORKFLOW.read_text(encoding="utf-8")
    for ln in uses:
        name = re.search(r"actions/([a-z-]+)@", ln).group(1)
        if name in ("checkout", "setup-python", "setup-node"):
            assert ln.lstrip("- ").strip() in ci, ln


def test_pages_build_steps_build_the_pack_then_the_subpath_site_check_it_and_upload_dist():
    steps = _load(PAGES)["jobs"]["build"]["steps"]
    runs = [s["run"] for s in steps if "run" in s]
    assert runs == [
        "python scripts/build_offline.py",
        "cd frontend && npm ci",
        "cd frontend && npm run build:offline",
        "cd frontend && REQUIRE_PRECACHE=1 npx vitest run src/offline/precache.dist.test.mjs",
    ]
    build = next(s for s in steps if s.get("run") == "cd frontend && npm run build:offline")
    assert build["env"] == {"VITE_BASE": "/dnd-character-creator/", "VITE_SERVERLESS": "1"}
    upload = next(s for s in steps if s.get("uses", "").startswith("actions/upload-pages-artifact@"))
    assert upload["with"] == {"path": "frontend/dist"}
    order = [s.get("run") or s["uses"].split("@")[0] for s in steps]
    assert order.index("python scripts/build_offline.py") < order.index("cd frontend && npm run build:offline") < order.index("actions/upload-pages-artifact")


def test_the_pack_and_the_build_output_are_gitignored_but_the_pwa_sources_are_not():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "frontend/public/pyodide/" in ignored
    assert "frontend/dist/" in ignored
    for needed in ("frontend/public/manifest.webmanifest", "frontend/public/icons/icon-192.png", "frontend/pwa/sw.template.js"):
        assert (ROOT / needed).is_file(), needed
        assert not any(line.strip() and line.strip().rstrip("/") in needed for line in ignored if not line.startswith("#")), needed
