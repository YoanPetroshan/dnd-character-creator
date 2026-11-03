"""DATA-SOURCES.md stays in step with the repo: quoted paths exist and the manifest is covered."""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "DATA-SOURCES.md"
BUNDLE = REPO / "server" / "data" / "official"
PATH_EXT = (".json", ".md", ".py", ".ttf", ".sh")


def _doc():
    return DOC.read_text(encoding="utf-8")


def _backticked():
    return re.findall(r"`([^`\n]+)`", _doc())


def _quoted_paths():
    out = []
    for tok in _backticked():
        if " " in tok or tok.startswith(("--", "python", "~", "<")):
            continue
        if "/" in tok or tok.endswith(PATH_EXT):
            if tok.startswith("5e-SRD-") or tok in ("index.json", "sources.json"):
                continue
            out.append(tok)
    return out


def test_doc_exists_and_quotes_paths():
    assert DOC.is_file()
    assert len(_quoted_paths()) >= 8


def test_every_quoted_relative_path_exists():
    missing = []
    for tok in _quoted_paths():
        if "<" in tok:
            continue
        if not (REPO / tok).exists():
            missing.append(tok)
    assert not missing, missing


def test_srd_files_named_in_doc_exist():
    for name in re.findall(r"`(5e-SRD-[A-Za-z]+\.json)`", _doc()):
        assert (REPO / "chargen" / "data" / "srd" / name).is_file(), name


def test_every_manifest_file_is_covered():
    files = json.loads((BUNDLE / "MANIFEST.json").read_text())["files"]
    doc = _doc()
    group_prefixes = [
        t for t in _backticked() if t.startswith("server/data/official/") and (t.endswith("/") or t.endswith(".json"))
    ]
    for rel, meta in files.items():
        full = "server/data/official/" + rel
        if meta["url"] is not None:
            assert f"`{full}`" in doc, full
            assert meta["url"] in doc, (rel, "url")
            assert meta["pulled_at"] in doc, (rel, "pulled_at")
        else:
            assert meta["pulled_at"] is None
            assert any(full == g or (g.endswith("/") and full.startswith(g)) for g in group_prefixes), full


def test_documented_counts_match_manifest():
    files = json.loads((BUNDLE / "MANIFEST.json").read_text())["files"]
    assert len(files) == 40
    assert sum(1 for m in files.values() if m["url"] is not None) == 4
    assert sum(1 for m in files.values() if m["url"] is None) == 36
    assert sum(m["bytes"] for m in files.values()) == 5868057
    assert "5,868,057" in _doc()


def test_provenance_commit_and_source_codes():
    doc = _doc()
    assert "d2a2616867c2e435b37e465d64cc01e2fc075ace" in doc and "v2.25.4" in doc
    codes = set()
    for f in ("races", "backgrounds", "feats", "items-base", "optionalfeatures"):
        for lst in json.loads((BUNDLE / f"{f}.json").read_text()).values():
            if isinstance(lst, list):
                codes |= {r["source"] for r in lst if isinstance(r, dict) and "source" in r}
    for path in (BUNDLE / "spells").glob("spells-*.json"):
        codes |= {r["source"] for r in json.loads(path.read_text()).get("spell", [])}
    for path in (BUNDLE / "class").glob("class-*.json"):
        for lst in json.loads(path.read_text()).values():
            if isinstance(lst, list):
                codes |= {r["source"] for r in lst if isinstance(r, dict) and "source" in r}
    listed = set(re.findall(r"[A-Za-z][A-Za-z\-]*", doc.split("The `source` codes found")[1].split("The 17 spell books")[0]))
    assert codes <= listed, sorted(codes - listed)
