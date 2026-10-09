"""Tests for chargen/sync.py — the SRD data sync script.

No test touches the network: urllib.request.urlopen is monkeypatched with a
stub that either returns canned bytes or raises, so these run fast and
deterministically regardless of connectivity.
"""

import io
import json
import os
import pathlib
import urllib.error

import pytest

from chargen import sync


@pytest.fixture()
def srd_dir(tmp_path, monkeypatch):
    """Point chargen.sources.srd_dir() (and thus sync.py) at a scratch dir."""
    d = tmp_path / "srd"
    d.mkdir()
    monkeypatch.setattr(sync, "srd_dir", lambda: d)
    return d


class _FakeResponse:
    """Minimal stand-in for the object urlopen() returns as a context manager."""

    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _stub_urlopen_ok(payload: bytes):
    def _urlopen(req, timeout=30):
        return _FakeResponse(payload)
    return _urlopen


def _stub_urlopen_fail_network():
    def _urlopen(req, timeout=30):
        raise urllib.error.URLError("simulated network failure")
    return _urlopen


def _stub_urlopen_bad_json(payload: bytes = b"not json at all"):
    def _urlopen(req, timeout=30):
        return _FakeResponse(payload)
    return _urlopen


def test_fetch_writes_file_on_stubbed_success(srd_dir, monkeypatch):
    payload = json.dumps([{"index": "fireball"}]).encode("utf-8")
    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_ok(payload))

    dest = srd_dir / "5e-SRD-Spells.json"
    ok, msg = sync._fetch("https://example.invalid/5e-SRD-Spells.json", str(dest))

    assert ok is True
    assert dest.exists()
    assert dest.read_bytes() == payload


def test_status_reports_present_and_missing(srd_dir, monkeypatch, capsys):
    # Pre-create one of the ten targets so status sees a mix.
    present = sync.TARGETS[0]
    (srd_dir / present["filename"]).write_text("[]")
    meta = {present["key"]: {"filename": present["filename"],
                              "pulled_at": "2026-08-24 00:00 UTC",
                              "url": "https://example.invalid/x"}}
    (srd_dir / "meta.json").write_text(json.dumps(meta))

    sync.cmd_status()
    out = capsys.readouterr().out

    assert "✓" in out
    assert present["key"] in out
    # Every other target should be reported missing.
    missing_keys = [t["key"] for t in sync.TARGETS[1:]]
    assert all(k in out for k in missing_keys)
    assert out.count("✗") == len(missing_keys)


def test_failed_fetch_leaves_existing_file_untouched(srd_dir, monkeypatch):
    dest = srd_dir / "5e-SRD-Backgrounds.json"
    original_content = b'{"already": "good", "do": "not touch me"}'
    dest.write_bytes(original_content)

    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_fail_network())

    ok, msg = sync._fetch("https://example.invalid/5e-SRD-Backgrounds.json", str(dest))

    assert ok is False
    assert dest.read_bytes() == original_content


def test_failed_fetch_with_invalid_json_leaves_existing_file_untouched(srd_dir, monkeypatch):
    dest = srd_dir / "5e-SRD-Traits.json"
    original_content = b'{"already": "good"}'
    dest.write_bytes(original_content)

    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_bad_json())

    ok, msg = sync._fetch("https://example.invalid/5e-SRD-Traits.json", str(dest))

    assert ok is False
    assert dest.read_bytes() == original_content


def test_failed_fetch_does_not_leave_a_lingering_tmp_file(srd_dir, monkeypatch):
    dest = srd_dir / "5e-SRD-Features.json"
    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_fail_network())

    ok, msg = sync._fetch("https://example.invalid/5e-SRD-Features.json", str(dest))

    assert ok is False
    assert not dest.exists()
    leftovers = list(srd_dir.glob("*.tmp")) + list(srd_dir.glob("*.tmp.*"))
    # No stray temp files anywhere in the destination directory.
    assert list(srd_dir.iterdir()) == []


def test_pull_skips_existing_files_unless_forced(srd_dir, monkeypatch, capsys):
    existing = sync.TARGETS[0]
    dest = srd_dir / existing["filename"]
    dest.write_bytes(b'{"pre": "existing"}')

    calls = []

    def _urlopen(req, timeout=30):
        calls.append(req.full_url if hasattr(req, "full_url") else str(req))
        return _FakeResponse(b"[]")

    monkeypatch.setattr(sync.urllib.request, "urlopen", _urlopen)

    sync.cmd_pull(force=False)

    # The pre-existing file must not have been re-fetched (content unchanged).
    assert dest.read_bytes() == b'{"pre": "existing"}'


def test_pull_force_refetches_all(srd_dir, monkeypatch):
    existing = sync.TARGETS[0]
    dest = srd_dir / existing["filename"]
    dest.write_bytes(b'{"pre": "existing"}')

    def _urlopen(req, timeout=30):
        return _FakeResponse(b"[]")

    monkeypatch.setattr(sync.urllib.request, "urlopen", _urlopen)

    sync.cmd_pull(force=True)

    assert dest.read_bytes() == b"[]"
    meta_path = srd_dir / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert existing["key"] in meta


def test_pull_records_meta_for_all_ten_targets(srd_dir, monkeypatch):
    def _urlopen(req, timeout=30):
        return _FakeResponse(b"[]")

    monkeypatch.setattr(sync.urllib.request, "urlopen", _urlopen)

    sync.cmd_pull(force=False)

    assert len(sync.TARGETS) == 10
    meta = json.loads((srd_dir / "meta.json").read_text())
    for t in sync.TARGETS:
        assert t["key"] in meta
        assert (srd_dir / t["filename"]).exists()


def test_pull_preserves_meta_entries_for_files_that_succeeded_before_a_later_failure(
    srd_dir, monkeypatch
):
    """If target N fails mid-run, meta.json must still retain the entries
    written for targets 1..N-1 that succeeded earlier in the same run."""
    fail_filename = sync.TARGETS[2]["filename"]

    def _urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if fail_filename in url:
            raise urllib.error.URLError("simulated failure on third target")
        return _FakeResponse(b"[]")

    monkeypatch.setattr(sync.urllib.request, "urlopen", _urlopen)

    sync.cmd_pull(force=False)

    meta = json.loads((srd_dir / "meta.json").read_text())
    # The two targets before the failing one succeeded and must be recorded.
    assert sync.TARGETS[0]["key"] in meta
    assert sync.TARGETS[1]["key"] in meta
    # The failing target must not have a bogus meta entry.
    assert sync.TARGETS[2]["key"] not in meta


# ---------------------------------------------------------------------------
# --official: the wider, multi-sourcebook catalog (Task 10)
# ---------------------------------------------------------------------------


@pytest.fixture()
def official_dir_fixture(tmp_path, monkeypatch):
    """Point chargen.sources.official_dir() (and thus sync.py) at a scratch
    dir OUTSIDE the repo tree — the safe, default-shaped case."""
    d = tmp_path / "official"
    monkeypatch.setattr(sync, "official_dir", lambda: d)
    return d


def test_official_pull_writes_both_targets(official_dir_fixture, monkeypatch):
    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_ok(b'{"race": []}'))

    ok = sync.cmd_official_pull(force=False)

    assert ok is True
    assert (official_dir_fixture / "races.json").exists()
    assert (official_dir_fixture / "backgrounds.json").exists()


def test_official_pull_uses_its_own_meta_sidecar_not_the_srd_ones(
    official_dir_fixture, srd_dir, monkeypatch
):
    """The official meta.json must live inside official_dir(), separate from
    (and never overwriting) the SRD meta.json in srd_dir()."""
    srd_meta = {"spells": {"filename": "5e-SRD-Spells.json",
                            "pulled_at": "2026-08-24 00:00 UTC", "url": "x"}}
    (srd_dir / "meta.json").write_text(json.dumps(srd_meta))

    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_ok(b'{"race": []}'))
    sync.cmd_official_pull(force=False)

    official_meta_path = official_dir_fixture / "meta.json"
    assert official_meta_path.exists()
    official_meta = json.loads(official_meta_path.read_text())
    assert "races" in official_meta
    assert "backgrounds" in official_meta
    # untouched SRD meta.json
    srd_meta_after = json.loads((srd_dir / "meta.json").read_text())
    assert srd_meta_after == srd_meta


def test_official_pull_skips_existing_unless_forced(official_dir_fixture, monkeypatch):
    official_dir_fixture.mkdir(parents=True, exist_ok=True)
    dest = official_dir_fixture / "races.json"
    dest.write_bytes(b'{"pre": "existing"}')

    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_ok(b'{"race": []}'))
    sync.cmd_official_pull(force=False)

    assert dest.read_bytes() == b'{"pre": "existing"}'


def test_official_pull_force_refetches(official_dir_fixture, monkeypatch):
    official_dir_fixture.mkdir(parents=True, exist_ok=True)
    dest = official_dir_fixture / "races.json"
    dest.write_bytes(b'{"pre": "existing"}')

    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_ok(b'{"race": []}'))
    sync.cmd_official_pull(force=True)

    assert dest.read_bytes() == b'{"race": []}'


def test_official_status_reports_present_and_missing(official_dir_fixture, monkeypatch, capsys):
    official_dir_fixture.mkdir(parents=True, exist_ok=True)
    (official_dir_fixture / "races.json").write_text('{"race": []}')
    meta = {"races": {"filename": "races.json",
                       "pulled_at": "2026-08-24 00:00 UTC", "url": "x"}}
    (official_dir_fixture / "meta.json").write_text(json.dumps(meta))

    sync.cmd_official_status()
    out = capsys.readouterr().out

    assert "✓" in out
    assert "races" in out
    assert "✗" in out
    assert "backgrounds" in out


def test_official_pull_refuses_to_write_inside_the_repo_tree(monkeypatch):
    """DND_CAMPAIGN_ROOT pointed at the repo itself must be refused — no
    files written, no network call made — even though this is exactly the
    shape official_dir() would otherwise happily return."""
    repo_root = pathlib.Path(sync.__file__).resolve().parent.parent
    monkeypatch.setattr(sync, "official_dir", lambda: repo_root / ".data" / "official")

    calls = []

    def _urlopen(req, timeout=30):
        calls.append(req)
        return _FakeResponse(b'{"race": []}')

    monkeypatch.setattr(sync.urllib.request, "urlopen", _urlopen)

    ok = sync.cmd_official_pull(force=False)

    assert ok is False
    assert calls == []
    assert not (repo_root / ".data").exists()


def test_official_dir_is_safe_rejects_repo_root_itself(monkeypatch):
    repo_root = pathlib.Path(sync.__file__).resolve().parent.parent
    monkeypatch.setattr(sync, "official_dir", lambda: repo_root)
    safe, msg = sync._official_dir_is_safe()
    assert safe is False
    assert "repo" in msg.lower()


def test_official_dir_is_safe_accepts_a_path_outside_the_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(sync, "official_dir", lambda: tmp_path / "official")
    safe, msg = sync._official_dir_is_safe()
    assert safe is True
    assert msg == ""


def test_status_with_official_flag_reports_both_sections(
    srd_dir, official_dir_fixture, capsys
):
    sync.cmd_status(official=True)
    out = capsys.readouterr().out
    assert "Data directory:" in out
    assert "Official data directory:" in out


# ---------------------------------------------------------------------------
# --official: the spells/ subdirectory (Slice 11a.1)
# ---------------------------------------------------------------------------


def _routing_urlopen(files: dict[str, bytes], requested: list):
    """Serves `files` by the URL's trailing path (e.g. "spells/index.json");
    anything else is a 404-shaped network error."""
    def _urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else req
        requested.append(url)
        for suffix, payload in files.items():
            if url.endswith("/" + suffix):
                return _FakeResponse(payload)
        raise urllib.error.HTTPError(url, 404, "not found", {}, None)
    return _urlopen


def _spell_fixture_files():
    index = {"PHB": "spells-phb.json", "XGE": "spells-xge.json"}
    return {
        "races.json": b'{"race": []}',
        "backgrounds.json": b'{"background": []}',
        "feats.json": b'{"feat": []}',
        "spells/index.json": json.dumps(index).encode(),
        "spells/sources.json": b'{"PHB": {}}',
        "spells/spells-phb.json": b'{"spell": []}',
        "spells/spells-xge.json": b'{"spell": []}',
        "optionalfeatures.json": b'{"optionalfeature": []}',
        "class/index.json": json.dumps({"fighter": "class-fighter.json", "wizard": "class-wizard.json"}).encode(),
        "class/class-fighter.json": b'{"class": [], "subclass": [], "subclassFeature": []}',
        "class/class-wizard.json": b'{"class": [], "subclass": [], "subclassFeature": []}',
    }


def test_official_pull_fetches_the_spells_index_sources_and_every_listed_file(official_dir_fixture, monkeypatch):
    requested = []
    monkeypatch.setattr(sync.urllib.request, "urlopen", _routing_urlopen(_spell_fixture_files(), requested))

    assert sync.cmd_official_pull(force=False) is True

    spells = official_dir_fixture / "spells"
    assert sorted(p.name for p in spells.iterdir()) == ["index.json", "sources.json", "spells-phb.json", "spells-xge.json"]
    meta = json.loads((official_dir_fixture / "meta.json").read_text())
    assert "spells/spells-phb.json" in meta and "spells/index.json" in meta


def test_official_pull_spell_files_skip_existing_unless_forced(official_dir_fixture, monkeypatch):
    requested = []
    monkeypatch.setattr(sync.urllib.request, "urlopen", _routing_urlopen(_spell_fixture_files(), requested))
    sync.cmd_official_pull(force=False)
    (official_dir_fixture / "spells" / "spells-phb.json").write_bytes(b'{"spell": ["local"]}')

    requested.clear()
    sync.cmd_official_pull(force=False)
    assert (official_dir_fixture / "spells" / "spells-phb.json").read_bytes() == b'{"spell": ["local"]}'
    assert not any(u.endswith("spells-phb.json") for u in requested)

    sync.cmd_official_pull(force=True)
    assert (official_dir_fixture / "spells" / "spells-phb.json").read_bytes() == b'{"spell": []}'


def test_official_pull_ignores_unsafe_names_in_the_spells_index(official_dir_fixture, monkeypatch):
    files = _spell_fixture_files()
    files["spells/index.json"] = json.dumps(
        {"PHB": "spells-phb.json", "BAD": "../../evil.json", "WORSE": "/etc/passwd", "ODD": ["x"]}
    ).encode()
    requested = []
    monkeypatch.setattr(sync.urllib.request, "urlopen", _routing_urlopen(files, requested))

    assert sync.cmd_official_pull(force=False) is True
    assert not any("evil" in u or "passwd" in u for u in requested)
    assert not (official_dir_fixture.parent / "evil.json").exists()
    assert (official_dir_fixture / "spells" / "spells-phb.json").exists()


def test_official_pull_with_a_generic_stub_still_succeeds_without_spell_files(official_dir_fixture, monkeypatch):
    # A stub that answers every URL with the same non-index JSON: no files to fetch, no failure.
    monkeypatch.setattr(sync.urllib.request, "urlopen", _stub_urlopen_ok(b'{"race": []}'))
    assert sync.cmd_official_pull(force=False) is True


def test_official_status_lists_the_spell_files(official_dir_fixture, capsys):
    (official_dir_fixture / "spells").mkdir(parents=True)
    (official_dir_fixture / "spells" / "index.json").write_text('{"PHB": "spells-phb.json"}')
    sync.cmd_official_status()
    out = capsys.readouterr().out
    assert "spells/index.json" in out
    assert "spells/sources.json" in out  # missing one is reported too


# ---------------------------------------------------------------------------
# --official: the class/ subdirectory and optionalfeatures.json (Slice 11b.1)
# ---------------------------------------------------------------------------


def test_official_pull_fetches_the_class_index_and_every_listed_class_file(official_dir_fixture, monkeypatch):
    requested = []
    monkeypatch.setattr(sync.urllib.request, "urlopen", _routing_urlopen(_spell_fixture_files(), requested))

    assert sync.cmd_official_pull(force=False) is True

    classes = official_dir_fixture / "class"
    assert sorted(p.name for p in classes.iterdir()) == ["class-fighter.json", "class-wizard.json", "index.json"]
    meta = json.loads((official_dir_fixture / "meta.json").read_text())
    assert "class/class-fighter.json" in meta and "class/index.json" in meta


def test_official_pull_fetches_optionalfeatures(official_dir_fixture, monkeypatch):
    requested = []
    monkeypatch.setattr(sync.urllib.request, "urlopen", _routing_urlopen(_spell_fixture_files(), requested))
    assert sync.cmd_official_pull(force=False) is True
    assert (official_dir_fixture / "optionalfeatures.json").read_bytes() == b'{"optionalfeature": []}'
    assert any(t["filename"] == "optionalfeatures.json" for t in sync.OFFICIAL_TARGETS)


def test_official_pull_ignores_unsafe_names_in_the_class_index(official_dir_fixture, monkeypatch):
    files = _spell_fixture_files()
    files["class/index.json"] = json.dumps(
        {"fighter": "class-fighter.json", "BAD": "../../evil.json", "WORSE": "/etc/passwd"}
    ).encode()
    requested = []
    monkeypatch.setattr(sync.urllib.request, "urlopen", _routing_urlopen(files, requested))
    assert sync.cmd_official_pull(force=False) is True
    assert not any("evil" in u or "passwd" in u for u in requested)
    assert (official_dir_fixture / "class" / "class-fighter.json").exists()


def test_official_status_lists_the_class_files(official_dir_fixture, capsys):
    (official_dir_fixture / "class").mkdir(parents=True)
    (official_dir_fixture / "class" / "index.json").write_text('{"fighter": "class-fighter.json"}')
    sync.cmd_official_status()
    out = capsys.readouterr().out
    assert "class/index.json" in out
    assert "class/class-fighter.json" in out
    assert "optionalfeatures" in out
