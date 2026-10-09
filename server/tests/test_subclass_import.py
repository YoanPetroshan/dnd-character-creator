"""Slice 11b: sourcebook subclasses (5etools class/*.json -> SRD subclass shape).

Every number asserted against real data was computed by script (with the
project's own `catalog.official.common.slug`) over
/Users/yoanpetrov/Documents/5etools-src/data/class on 2026-10-09; tests that
need the files skip when they are absent (no `DND_5ETOOLS_DATA`, nothing
synced into official_dir()/class)."""
import json

import pytest

from catalog.official import paths, subclasses as sub_mod
from catalog.official_source import has_official_classes

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

RAW_SUBCLASSES = 315
RAW_SUBCLASS_FEATURES = 1397
RAW_OPTIONAL_FEATURES = 213


# ---------------------------------------------------------------- 11b.1 data

def _write_class_dir(root, files=None):
    d = root / "class"
    d.mkdir(parents=True)
    files = files if files is not None else {
        "fighter": {"subclass": [{"name": "Battle Master", "shortName": "Battle Master", "source": "PHB"}],
                    "subclassFeature": [{"name": "Combat Superiority"}]},
        "wizard": {"subclass": [{"name": "Evocation"}, {"name": "Abjuration"}], "subclassFeature": []},
    }
    (d / "index.json").write_text(json.dumps({k: f"class-{k}.json" for k in files}))
    for k, body in files.items():
        (d / f"class-{k}.json").write_text(json.dumps(body))
    return d


def test_class_dir_honours_the_env_override(tmp_path, monkeypatch):
    d = _write_class_dir(tmp_path / "data")
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "data"))
    assert paths.class_dir() == d
    assert paths.has_official_classes()


def test_class_dir_falls_back_to_the_official_dir_then_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DND_5ETOOLS_DATA", raising=False)
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.class_dir() is None
    assert not paths.has_official_classes()
    d = _write_class_dir(tmp_path / "official")
    assert paths.class_dir() == d


def test_optionalfeatures_file_override_first_then_official_dir_then_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DND_5ETOOLS_DATA", raising=False)
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.optionalfeatures_file() is None
    (tmp_path / "official").mkdir()
    (tmp_path / "official" / "optionalfeatures.json").write_text('{"optionalfeature": []}')
    assert paths.optionalfeatures_file() == tmp_path / "official" / "optionalfeatures.json"
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "optionalfeatures.json").write_text('{"optionalfeature": []}')
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "data"))
    assert paths.optionalfeatures_file() == tmp_path / "data" / "optionalfeatures.json"


def test_raw_loader_reads_every_file_in_the_index(tmp_path):
    d = _write_class_dir(tmp_path)
    subs, feats = sub_mod.load_raw_class_data(d)
    assert [s["name"] for s in subs] == ["Battle Master", "Evocation", "Abjuration"]
    assert [f["name"] for f in feats] == ["Combat Superiority"]


def test_raw_loader_returns_empty_when_missing_and_skips_a_broken_file(tmp_path):
    assert sub_mod.load_raw_class_data(None) == ([], [])
    assert sub_mod.load_raw_class_data(tmp_path / "nope") == ([], [])
    d = _write_class_dir(tmp_path / "x")
    (d / "class-wizard.json").write_text("{not json")
    subs, _ = sub_mod.load_raw_class_data(d)
    assert [s["name"] for s in subs] == ["Battle Master"]


def test_raw_optional_feature_loader(tmp_path):
    assert sub_mod.load_raw_optional_features(None) == []
    assert sub_mod.load_raw_optional_features(tmp_path / "nope.json") == []
    p = tmp_path / "of.json"
    p.write_text(json.dumps({"optionalfeature": [{"name": "Riposte"}, "junk"]}))
    assert [o["name"] for o in sub_mod.load_raw_optional_features(p)] == ["Riposte"]
    p.write_text("{bad")
    assert sub_mod.load_raw_optional_features(p) == []


@needs_classes
def test_real_raw_counts():
    subs, feats = sub_mod.load_raw_class_data(paths.class_dir())
    assert len(subs) == RAW_SUBCLASSES
    assert len(feats) == RAW_SUBCLASS_FEATURES


@needs_classes
def test_real_raw_optional_features_count():
    path = paths.optionalfeatures_file()
    assert path is not None
    assert len(sub_mod.load_raw_optional_features(path)) == RAW_OPTIONAL_FEATURES
