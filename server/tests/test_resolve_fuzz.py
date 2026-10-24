"""W3: seeded fuzz / property harness for resolve() and the export endpoints.

Default: N=60 drafts per run (about +3 s). A bigger run is just the env var:
    FUZZ_N=2000 FUZZ_SEED0=0 .venv/bin/python -m pytest server/tests/test_resolve_fuzz.py -q
(about 25 ms per draft per property; 3000 drafts take ~80 s). Seeds are consecutive from FUZZ_SEED0.
Deterministic: draft = gen_draft(seed, catalog) is a pure function of the seed (random.Random(seed), no global state),
so every failure message starts with `seed=<n>` and reproduces with gen_draft(n, load()).
Properties: (a) resolve never raises, (b) resolve twice is byte-identical, (c) kitchen_sink.fill settles in 10 rounds
(failure prints seed, draft and the cards still pending / flipping), (d) after random mutations resolve never raises
and stale picks are reported in `pruned`, (e) yaml / markdown / pdf exports return 200 on up to 10 settled drafts,
(f) the slowest resolve is under 50 ms."""
import copy
import json
import os
import pathlib
import random
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kitchen_sink as ks  # noqa: E402
from app import app  # noqa: E402
from catalog.loader import load  # noqa: E402
from catalog.reference_data import ruleset_allows  # noqa: E402
from engine.resolve import resolve  # noqa: E402

FUZZ_N = int(os.environ.get("FUZZ_N", "60"))
FUZZ_SEED0 = int(os.environ.get("FUZZ_SEED0", "0"))
SEEDS = list(range(FUZZ_SEED0, FUZZ_SEED0 + FUZZ_N))
SOURCE_POOL = ["PHB", "XPHB", "XGE", "TCE", "SCAG", "MPMM", "VGM", "FTD", "GGR", "AI"]


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _pick_subclass(rng, catalog, class_id, ruleset):
    subs = sorted(i for i, s in catalog.subclasses.items()
                  if s.get("class", {}).get("index") == class_id and ruleset_allows(s, "subclass", ruleset))
    return rng.choice(subs) if subs and rng.random() < 0.75 else None


def _pick_origin(rng, catalog, ruleset):
    species = sorted(i for i, r in catalog.races.items() if ruleset_allows(r, "species", ruleset))
    backgrounds = sorted(i for i, b in catalog.backgrounds.items() if ruleset_allows(b, "background", ruleset))
    sid = rng.choice(species)
    subs = sorted(s["index"] for s in catalog.subraces_of(sid) if ruleset_allows(s, "species", ruleset))
    return sid, (rng.choice(subs) if subs and rng.random() < 0.7 else None), rng.choice(backgrounds)


def gen_draft(seed, catalog):
    """A random, unfilled draft. Pure function of the seed."""
    rng = random.Random(seed)
    ruleset = rng.choice(["2014", "2024", "mixed"])
    n = rng.choice([1, 1, 2, 2, 3])
    class_ids = rng.sample(sorted(catalog.classes), n)
    levels = [1] * n
    for _ in range(rng.randint(0, 20 - n)):
        levels[rng.randrange(n)] += 1
    sources = [] if rng.random() < 0.5 else rng.sample(SOURCE_POOL, rng.randint(1, len(SOURCE_POOL)))
    sid, subid, bid = _pick_origin(rng, catalog, ruleset)
    classes = []
    for cid, lvl in zip(class_ids, levels):
        c = {"classId": cid, "level": lvl, "choices": {}}
        sub = _pick_subclass(rng, catalog, cid, ruleset)
        if sub:
            c["subclassId"] = sub  # a level below the unlock level is allowed on purpose
        classes.append(c)
    species = {"id": sid, "choices": {}}
    if subid:
        species["subspeciesId"] = subid
    return {"name": f"Fuzz {seed}", "ruleset": ruleset, "sources": sources,
            "abilities": {"method": "manual", "base": {k: rng.randint(3, 18) for k in ("STR", "DEX", "CON", "INT", "WIS", "CHA")}},
            "species": species, "background": {"id": bid, "choices": {}},
            "equipment": {"choices": {}, "added": [], "skipped": False}, "classes": classes}


def canon(res):
    return json.dumps(res, sort_keys=True, default=str)


class Settle(Exception):
    pass


def settle(draft, catalog, timings=None):
    """kitchen_sink.fill with a tracing resolve. Returns the filled draft; on failure raises Settle with a report of
    the cards that stay pending (flip) between rounds."""
    rounds = []

    def traced(d, cat):
        t = time.perf_counter()
        res = resolve(d, cat)
        if timings is not None:
            timings.append(time.perf_counter() - t)
        rounds.append({c["id"]: list(c["selected"]) for c in res["choices"] if c["status"] == "pending"})
        return res

    try:
        return ks.fill(draft, catalog, {}, traced)
    except AssertionError:
        last = rounds[-4:]
        ids = sorted(set().union(*[set(r) for r in last]))
        flips = [i for i in ids if sum(i in r for r in last) < len(last) or len({tuple(r.get(i, ())) for r in last}) > 1]
        raise Settle(f"fill did not settle in 10 rounds; pending in the last rounds: {ids}; flipping: {flips}")


def _stale_violations(draft, res):
    """Stored picks that are neither in a live card's options nor reported in pruned (property d)."""
    pruned = {p["choiceId"] for p in res["pruned"]}
    cards = {c["id"]: c for c in res["choices"]}
    bad = []
    for store in [c["choices"] for c in draft["classes"]] + [draft["species"]["choices"], draft["background"]["choices"],
                                                              draft["equipment"].get("choices", {})]:
        for cid in store:
            if cid not in cards and cid not in pruned:
                bad.append(f"{cid}: stored, no card, not pruned")
    for cid, card in cards.items():
        if cid in pruned:
            continue
        ids = {o["id"] for o in card["options"]}
        off = [s for s in card["selected"] if ids and s not in ids]
        if off:
            bad.append(f"{cid}: selected {off} not in options and not pruned")
    return bad


def mutate(draft, rng, catalog):
    d = copy.deepcopy(draft)
    kind = rng.choice(["level-down", "reorder", "ruleset", "species", "background"])
    if kind == "level-down":
        c = rng.choice(d["classes"])
        c["level"] = max(1, c["level"] - rng.randint(1, 10))
    elif kind == "reorder":
        rng.shuffle(d["classes"])
    elif kind == "ruleset":
        d["ruleset"] = rng.choice([r for r in ("2014", "2024", "mixed") if r != d["ruleset"]])
    elif kind == "species":
        sid, subid, _ = _pick_origin(rng, catalog, d["ruleset"])
        d["species"]["id"] = sid
        d["species"].pop("subspeciesId", None)
        if subid:
            d["species"]["subspeciesId"] = subid
    else:
        d["background"]["id"] = _pick_origin(rng, catalog, d["ruleset"])[2]
    return kind, d


@pytest.fixture(scope="module")
def settled(catalog):
    """seed -> (filled draft | None, error text, timings) for every seed; shared by the properties below."""
    out = {}
    for seed in SEEDS:
        draft = gen_draft(seed, catalog)
        timings = []
        try:
            out[seed] = (settle(draft, catalog, timings), None, timings)
        except Settle as e:
            out[seed] = (None, f"seed={seed} ruleset={draft['ruleset']} draft={json.dumps(draft, sort_keys=True)} :: {e}", timings)
    return out


def test_generator_is_deterministic(catalog):
    assert json.dumps(gen_draft(7, catalog), sort_keys=True) == json.dumps(gen_draft(7, catalog), sort_keys=True)
    assert sum(c["level"] for c in gen_draft(7, catalog)["classes"]) <= 20


def test_fill_settles_within_ten_rounds(settled):
    failures = [err for _, err, _ in settled.values() if err]
    assert not failures, "\n".join(failures)


def test_resolve_never_raises_and_is_idempotent(settled, catalog):
    for seed, (draft, err, _) in settled.items():
        if draft is None:
            continue
        a, b = canon(resolve(copy.deepcopy(draft), catalog)), canon(resolve(copy.deepcopy(draft), catalog))
        assert a == b, f"seed={seed}: resolve is not byte-identical on a second run"


def test_unfilled_drafts_never_raise(catalog):
    for seed in SEEDS:
        resolve(gen_draft(seed, catalog), catalog)


def test_mutations_never_raise_and_stale_picks_are_reported(settled, catalog):
    for seed, (draft, err, _) in settled.items():
        if draft is None:
            continue
        rng = random.Random(seed * 7919 + 1)
        cur = draft
        for _ in range(3):
            kind, cur = mutate(cur, rng, catalog)
            res = resolve(cur, catalog)
            bad = _stale_violations(cur, res)
            assert not bad, f"seed={seed} mutation={kind}: {bad}"


def test_exports_return_200_on_settled_drafts(settled, client):
    ok = 0
    for seed, (draft, err, _) in settled.items():
        if draft is None or ok >= 10:
            continue
        res = resolve(copy.deepcopy(draft), load_catalog())
        if res["problems"] or any(c["status"] == "pending" for c in res["choices"]):
            continue
        for fmt in ("yaml", "markdown", "pdf"):
            r = client.post(f"/api/export/{fmt}", json=draft)
            assert r.status_code == 200, f"seed={seed} {fmt}: {r.status_code} {r.data[:200]!r}"
        ok += 1
    assert ok >= min(10, len(SEEDS) // 6) or FUZZ_N < 30, f"only {ok} problem-free settled drafts to export"


def test_slowest_resolve_under_50_ms(settled):
    worst = max((max(t) if t else 0.0, seed) for seed, (_, _, t) in settled.items())
    assert worst[0] < 0.05, f"seed={worst[1]} resolve took {worst[0] * 1000:.1f} ms"


_CAT = []


def load_catalog():
    if not _CAT:
        _CAT.append(load())
    return _CAT[0]
