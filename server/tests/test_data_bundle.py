"""B1: the vendored 5etools data bundle (server/data/official) and its builder."""

import hashlib
import json
import os
import pathlib
import subprocess
import sys

import pytest

from catalog.official import bundle

SERVER = pathlib.Path(__file__).resolve().parent.parent
BUNDLE = SERVER / "data" / "official"


def _w(path: pathlib.Path, data) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = data if isinstance(data, bytes) else json.dumps(data, indent="\t").encode()
    path.write_bytes(raw)
    return raw


def make_src(root: pathlib.Path, *, hostile: bool = False) -> pathlib.Path:
    src = root / "src"
    _w(src / "races.json", {"race": [{"name": "A"}, {"name": "B"}], "_meta": {"x": 1}})
    _w(src / "backgrounds.json", {"background": [{"name": "C"}]})
    _w(src / "feats.json", {"feat": []})
    _w(src / "items-base.json", {"baseitem": [{"name": "D"}]})
    _w(src / "optionalfeatures.json", {"optionalfeature": [{"name": "E"}]})
    idx = {"PHB": "spells-phb.json", "XGE": "spells-xge.json"}
    if hostile:
        idx.update({"bad1": "../evil.json", "bad2": "sub/x.json", "bad3": ".hidden.json",
                    "bad4": "notjson.txt", "bad5": 7})
    _w(src / "spells" / "index.json", idx)
    _w(src / "spells" / "sources.json", {"PHB": {"Fireball": {}}})
    _w(src / "spells" / "spells-phb.json", {"spell": [{"name": "s1"}, {"name": "s2"}]})
    _w(src / "spells" / "spells-xge.json", {"spell": [{"name": "s3"}]})
    _w(src / "class" / "index.json", {"wizard": "class-wizard.json"})
    _w(src / "class" / "class-wizard.json", {"class": [{"name": "W"}], "subclass": [1, 2, 3]})
    _w(src / "meta.json", {
        "races": {"filename": "races.json", "pulled_at": "2026-08-24 23:55 UTC",
                  "url": "https://example.test/races.json"},
        "spells/sources.json": {"pulled_at": "2026-09-01 00:00 UTC", "url": "https://example.test/s"},
    })
    return src


EXPECTED = {
    "races.json", "backgrounds.json", "feats.json", "items-base.json", "optionalfeatures.json",
    "spells/index.json", "spells/sources.json", "spells/spells-phb.json", "spells/spells-xge.json",
    "class/index.json", "class/class-wizard.json",
}


def test_required_files_exact_set(tmp_path):
    assert set(bundle.required_files(make_src(tmp_path))) == EXPECTED


def test_required_files_ignores_hostile_index(tmp_path):
    src = make_src(tmp_path, hostile=True)
    assert set(bundle.required_files(src)) == EXPECTED


def test_build_exact_bytes_and_modes(tmp_path):
    src = make_src(tmp_path)
    dest = tmp_path / "dest"
    bundle.build(src, dest)
    for rel in EXPECTED:
        assert (dest / rel).read_bytes() == (src / rel).read_bytes()
        assert not (dest / rel).stat().st_mode & 0o111
    assert not (dest / "meta.json").exists()
    assert (dest / "MANIFEST.json").is_file()
    m = json.loads((dest / "MANIFEST.json").read_text())
    assert m["format"] == 1
    assert set(m["files"]) == EXPECTED
    assert m["files"]["races.json"]["records"] == {"race": 2}
    assert m["files"]["class/class-wizard.json"]["records"] == {"class": 1, "subclass": 3}
    assert m["files"]["races.json"]["url"] == "https://example.test/races.json"
    assert m["files"]["races.json"]["pulled_at"] == "2026-08-24 23:55 UTC"
    assert m["files"]["spells/sources.json"]["pulled_at"] == "2026-09-01 00:00 UTC"
    assert m["files"]["feats.json"]["url"] is None and m["files"]["feats.json"]["pulled_at"] is None


def test_manifest_deterministic(tmp_path):
    src = make_src(tmp_path)
    bundle.build(src, tmp_path / "d1")
    bundle.build(src, tmp_path / "d2")
    assert (tmp_path / "d1/MANIFEST.json").read_bytes() == (tmp_path / "d2/MANIFEST.json").read_bytes()
    m = json.loads((tmp_path / "d1/MANIFEST.json").read_text())
    lines = "".join(f"{r} {m['files'][r]['sha256']}\n" for r in sorted(m["files"]))
    assert m["bundle_sha256"] == hashlib.sha256(lines.encode()).hexdigest()


def test_build_removes_stale_files(tmp_path):
    src = make_src(tmp_path)
    dest = tmp_path / "dest"
    _w(dest / "old.json", {})
    _w(dest / "spells" / "spells-gone.json", {})
    bundle.build(src, dest)
    assert not (dest / "old.json").exists()
    assert not (dest / "spells" / "spells-gone.json").exists()
    on_disk = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
    assert on_disk == EXPECTED | {"MANIFEST.json"}
    assert not [p for p in tmp_path.iterdir() if p.name not in {"src", "dest"}]


def test_missing_file_raises_and_leaves_dest(tmp_path):
    src = make_src(tmp_path)
    dest = tmp_path / "dest"
    bundle.build(src, dest)
    before = {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
    (src / "spells" / "spells-xge.json").unlink()
    with pytest.raises(Exception):
        bundle.build(src, dest)
    after = {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
    assert before == after
    assert not [p for p in tmp_path.iterdir() if p.name not in {"src", "dest"}]


def test_invalid_json_raises(tmp_path):
    src = make_src(tmp_path)
    (src / "races.json").write_bytes(b"{not json")
    dest = tmp_path / "dest"
    with pytest.raises(Exception):
        bundle.build(src, dest)
    assert not dest.exists()


def _cli(*args):
    return subprocess.run([sys.executable, "-m", "catalog.official.bundle", *args],
                          cwd=SERVER, capture_output=True, text=True)


def test_check_exit_codes(tmp_path):
    src = make_src(tmp_path)
    dest = tmp_path / "dest"
    bundle.build(src, dest)
    assert bundle.check(src, dest) == ([], [], [])
    ok = _cli("--from", str(src), "--check", "--dest", str(dest))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    # drift: change one, remove one, add one in src
    _w(src / "feats.json", {"feat": [{"name": "new"}]})
    (src / "spells" / "spells-xge.json").unlink()
    idx = json.loads((src / "spells" / "index.json").read_text())
    del idx["XGE"]
    idx["AAG"] = "spells-aag.json"
    _w(src / "spells" / "index.json", idx)
    _w(src / "spells" / "spells-aag.json", {"spell": []})
    snapshot = {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}
    bad = _cli("--from", str(src), "--check", "--dest", str(dest))
    assert bad.returncode == 1
    out = bad.stdout
    assert "spells/spells-aag.json" in out and "spells/spells-xge.json" in out and "feats.json" in out
    assert snapshot == {p.relative_to(dest).as_posix(): p.read_bytes() for p in dest.rglob("*") if p.is_file()}


# ---- the real vendored bundle ------------------------------------------------

def _manifest():
    return json.loads((BUNDLE / "MANIFEST.json").read_text(encoding="utf-8"))


def test_real_bundle_integrity():
    m = _manifest()
    on_disk = {p.relative_to(BUNDLE).as_posix() for p in BUNDLE.rglob("*") if p.is_file()}
    assert on_disk == set(m["files"]) | {"MANIFEST.json"}
    for rel, e in m["files"].items():
        raw = (BUNDLE / rel).read_bytes()
        assert len(raw) == e["bytes"], rel
        assert hashlib.sha256(raw).hexdigest() == e["sha256"], rel
    lines = "".join(f"{r} {m['files'][r]['sha256']}\n" for r in sorted(m["files"]))
    assert m["bundle_sha256"] == hashlib.sha256(lines.encode()).hexdigest()
    assert set(bundle.required_files(BUNDLE)) == set(m["files"])
    assert len(m["files"]) == 40


def test_real_bundle_completeness():
    m = _manifest()["files"]
    assert m["races.json"]["records"]["race"] == 160
    assert m["races.json"]["records"]["subrace"] == 98
    assert m["backgrounds.json"]["records"]["background"] == 161
    assert m["feats.json"]["records"]["feat"] == 305
    assert m["optionalfeatures.json"]["records"]["optionalfeature"] == 213
    assert m["items-base.json"]["records"]["baseitem"] == 230
    books = [r for r in m if r.startswith("spells/spells-")]
    assert len(books) == 17
    assert sum(m[r]["records"]["spell"] for r in books) == 936
    assert len([r for r in m if r.startswith("class/class-")]) == 15
