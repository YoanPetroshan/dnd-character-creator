"""B2: which directory the server reads the official data from.

Order: DND_5ETOOLS_DATA (per file) > DND_OFFICIAL_DATA=none > DND_OFFICIAL_DATA=<path>
> DND_CAMPAIGN_ROOT (explicit, non-empty .data/official) > the vendored bundle.
Skip markers elsewhere evaluate at collection; these tests set the env themselves."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from catalog.loader import load
from catalog.official import paths

REAL_SYNCED = Path("~/.claude/dnd/.data/official").expanduser()  # captured before HOME is faked
FIXTURE_RACES = {"race": [{"name": "Fixtureling", "source": "PHB"}]}
FULL = dict(classes=12, levels=961, features=1783, subclasses=176, races=153, subraces=96,
            traits=1086, backgrounds=136, items=244, spells=936, feats=305, spell_twins=758, classes_2024=12)
SRD = dict(spells=319, races=9, feats=0, subclasses=12, levels=290, features=407)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ("DND_5ETOOLS_DATA", "DND_OFFICIAL_DATA", "DND_CAMPAIGN_ROOT"):
        monkeypatch.delenv(name, raising=False)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


def _counts(cat) -> dict:
    return {k: len(getattr(cat, k)) for k in (*FULL, *SRD)}


def _catalog_digest(cat) -> str:
    return hashlib.sha256(json.dumps({k: getattr(cat, k) for k in FULL}, sort_keys=True, default=str).encode()).hexdigest()


def _fixture_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "races.json").write_text(json.dumps(FIXTURE_RACES))
    return root


def test_default_is_the_bundle_with_full_counts():
    assert paths.official_dir() == paths.BUNDLED_DIR
    assert paths.BUNDLED_DIR.name == "official" and paths.BUNDLED_DIR.parent.name == "data"
    assert paths.data_source() == "bundled"
    assert paths.has_official() and paths.has_official_classes() and paths.has_official_spells()
    cat = load()
    got = _counts(cat)
    for key, want in FULL.items():
        assert got[key] == want, (key, got[key], want)


def test_none_is_srd_only():
    import os
    os.environ["DND_OFFICIAL_DATA"] = "none"
    try:
        assert paths.data_source() == "srd-only"
        assert not paths.official_dir().exists()
        assert not paths.has_official()
        assert not paths.has_official_classes()
        assert not paths.has_official_spells()
        got = _counts(load())
    finally:
        del os.environ["DND_OFFICIAL_DATA"]
    for key, want in SRD.items():
        assert got[key] == want, (key, got[key], want)


def test_explicit_official_data_path(monkeypatch, tmp_path):
    d = _fixture_dir(tmp_path / "mine")
    monkeypatch.setenv("DND_OFFICIAL_DATA", str(d))
    assert paths.official_dir() == d
    assert paths.data_source() == "explicit"
    assert paths.has_official()


def test_campaign_root_with_data(monkeypatch, tmp_path):
    root = tmp_path / "camp"
    _fixture_dir(root / ".data" / "official")
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(root))
    assert paths.official_dir() == (root / ".data" / "official").resolve()
    assert paths.data_source() == "campaign"


def test_empty_or_missing_campaign_root_falls_to_the_bundle(monkeypatch, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    for value in (str(empty), "/nonexistent"):
        monkeypatch.setenv("DND_CAMPAIGN_ROOT", value)
        assert paths.official_dir() == paths.BUNDLED_DIR
        assert paths.data_source() == "bundled"
    # an existing but empty .data/official also falls through
    (empty / ".data" / "official").mkdir(parents=True)
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(empty))
    assert paths.data_source() == "bundled"
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", "   ")
    assert paths.data_source() == "bundled"


def test_official_data_beats_campaign_root(monkeypatch, tmp_path):
    root = tmp_path / "camp"
    _fixture_dir(root / ".data" / "official")
    d = _fixture_dir(tmp_path / "mine")
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(root))
    monkeypatch.setenv("DND_OFFICIAL_DATA", str(d))
    assert paths.official_dir() == d


def test_5etools_override_still_wins_per_file(monkeypatch, tmp_path):
    src = tmp_path / "5etools" / "data"
    (src / "spells").mkdir(parents=True)
    (src / "spells" / "index.json").write_text("{}")
    (src / "optionalfeatures.json").write_text("{}")
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(src))
    monkeypatch.setenv("DND_OFFICIAL_DATA", "none")
    assert paths.spells_dir() == src / "spells"
    assert paths.optionalfeatures_file() == src / "optionalfeatures.json"
    assert paths.items_base_file() is None  # not in the override, and none -> absent


def test_implicit_home_copy_is_ignored(clean_env):
    decoy = clean_env / ".claude" / "dnd" / ".data" / "official"
    _fixture_dir(decoy)
    assert paths.official_dir() == paths.BUNDLED_DIR
    assert paths.data_source() == "bundled"


def test_bundle_equals_the_synced_copy_when_present(monkeypatch):
    synced = REAL_SYNCED
    if not (synced / "races.json").is_file():
        pytest.skip("no synced copy on this machine")
    bundled_digest = _catalog_digest(load())
    monkeypatch.setenv("DND_OFFICIAL_DATA", str(synced))
    assert paths.data_source() == "explicit"
    assert _catalog_digest(load()) == bundled_digest
