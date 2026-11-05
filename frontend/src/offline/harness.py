"""Runs inside Pyodide (Node) for equivalence.test.mjs: the same comparisons the native tests make, against the
stored baselines. Inputs are files the test writes into the Pyodide file system; each function returns a JSON string
{"checked": n, "mismatches": [...], "seconds": s}. Imports nothing of the repo before `setup()` (the app is mounted at
/app first)."""
import copy
import gzip
import hashlib
import json
import re
import sys
import time
import urllib.parse

STRIP = ("derived.featResources", "derived.speciesResources")  # = STRIP of server/tests/test_c_series_golden.py
# Flask answers GET /api with the SPA catch-all, not the API's 404; the service is not the SPA (as in test_service.py).
NOT_API = {"api-root"}


def setup():
    for p in ("/app/server", "/app"):
        if p not in sys.path:
            sys.path.insert(0, p)


def _strip(node, parts):
    head, rest = parts[0], parts[1:]
    if not isinstance(node, dict) or head not in node:
        return
    if rest:
        _strip(node[head], rest)
    else:
        del node[head]


def _strip_all(res):
    res = copy.deepcopy(res)
    for path in STRIP:
        _strip(res, path.split("."))
    return res


def _canon(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _out(checked, mismatches, t0, **extra):
    return json.dumps({"checked": checked, "mismatches": mismatches, "seconds": time.perf_counter() - t0, **extra})


def golden(path="/golden.json.gz"):
    from catalog.loader import load
    from engine.resolve import resolve
    t0 = time.perf_counter()
    cases = json.load(gzip.open(path, "rt", encoding="utf-8"))
    catalog = load()
    bad = []
    for name, case in cases.items():
        got = _strip_all(json.loads(json.dumps(resolve(copy.deepcopy(case["draft"]), catalog))))
        if _canon(got) != _canon(_strip_all(case["result"])):
            bad.append(name)
    return _out(len(cases), bad, t0)


def _normalise_pdf(data):
    data = re.sub(rb"/CreationDate\s*\(D:[^)]*\)", b"/CreationDate (D:X)", bytes(data))
    return re.sub(rb"/ID\s*\[\s*<[0-9a-fA-F]*>\s*<[0-9a-fA-F]*>\s*\]", b"/ID [<X> <X>]", data)


def _sha(data):
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def exports(fixture="/fixtures.json", baseline="/export_baseline.json"):
    from catalog.loader import load
    from engine.resolve import resolve
    from export import to_yaml
    from markdown_export import to_markdown
    from pdf_export import to_pdf
    t0 = time.perf_counter()
    cases = json.load(open(fixture, encoding="utf-8"))["exports"]
    expected = json.load(open(baseline, encoding="utf-8"))
    catalog = load()
    bad = []
    for sid, case in cases.items():
        res = resolve(case["draft"], catalog) if "draft" in case else case["resolution"]
        got = {"markdown": _sha(to_markdown(res)), "pdf": _sha(_normalise_pdf(to_pdf(res))), "yaml": _sha(to_yaml(res))}
        for fmt in got:
            if got[fmt] != expected[sid][fmt]:
                bad.append(f"{sid}:{fmt}")
    return _out(len(cases), bad, t0, ids=sorted(cases) == sorted(expected))


def requests(fixture="/fixtures.json", baseline="/service_baseline.json"):
    import service
    import base64
    t0 = time.perf_counter()
    reqs = json.load(open(fixture, encoding="utf-8"))["requests"]
    expected = json.load(open(baseline, encoding="utf-8"))
    bad, n = [], 0
    for r in reqs:
        if r["name"] in NOT_API:
            continue
        n += 1
        body = base64.b64decode(r["body"]) if r["body"] is not None else None
        ctype = r["ctype"]
        sent = body if (body is not None and ctype is not None and "json" in ctype) else None
        parts = urllib.parse.urlsplit(r["url"])
        status, content_type, headers, data = service.handle(r["method"], urllib.parse.unquote(parts.path), parts.query, sent)
        if content_type == "application/pdf":
            data = _normalise_pdf(data)
        want = expected[r["name"]]
        got_headers = {"Content-Type": content_type}
        if "Content-Disposition" in headers:
            got_headers["Content-Disposition"] = headers["Content-Disposition"]
        got = {"status": status, "headers": got_headers, "bodySha256": _sha(bytes(data)), "bodyLength": len(data)}
        if got != want:
            bad.append(r["name"])
    return _out(n, bad, t0, baselineSize=len(expected))
