"""Shared draft/lookup helpers for the C7c tests (invocation dependents under ruleset 2024)."""
import copy
import time

import pytest

from catalog.official_source import has_official, has_official_classes
from engine.resolve import resolve

needs_data = pytest.mark.skipif(not (has_official() and has_official_classes()),
                                reason="5etools official data not available")


INV = "class:warlock:1:invocations:xphb-warlock-1-eldritch-invocations"
CANT = "class:warlock:spells-cantrips"
KNOWN = "class:warlock:spells-known"
X = "opt-{}-xphb"
BLADE, CHAIN, TOME = X.format("pact-of-the-blade"), X.format("pact-of-the-chain"), X.format("pact-of-the-tome")
AGON, SPEAR, REPEL = X.format("agonizing-blast"), X.format("eldritch-spear"), X.format("repelling-blast")
THIRST, LESSONS = X.format("thirsting-blade"), X.format("lessons-of-the-first-ones")
EB, TTD, MI, FB = "eldritch-blast-xphb", "toll-the-dead-xphb", "minor-illusion-xphb", "fire-bolt-xphb"


def tcid(inst, kind):
    return f"class:warlock:invocation:{inst}:{kind}"


TOME_C, TOME_R = tcid(TOME, "cantrips"), tcid(TOME, "rituals")
BLADE_W = tcid(BLADE, "weapon")


def _draft(level, picks=None, cantrips=None, extra=None, bg="soldier-xphb", cha=16, strength=10, dex=14, added=None,
           wielded=None, ruleset="2024", classes_before=()):
    ch = dict(extra or {})
    if picks is not None:
        ch[INV] = picks
    if cantrips is not None:
        ch[CANT] = cantrips
    equipment = {"choices": {}, "added": added or [], "skipped": False}
    if wielded is not None:
        equipment["wielded"] = wielded
    return {
        "ruleset": ruleset, "sources": [],
        "abilities": {"method": "manual", "base": {"STR": strength, "DEX": dex, "CON": 14, "INT": 10, "WIS": 10, "CHA": cha}},
        "species": {"id": "human-xphb"}, "background": {"id": bg}, "equipment": equipment,
        "classes": [*classes_before, {"classId": "warlock", "level": level, "choices": ch}],
    }


def _res(catalog, level, picks=None, cantrips=None, **kw):
    return resolve(_draft(level, picks, cantrips, **kw), catalog)


def _card(res, cid):
    return next((c for c in res["choices"] if c["id"] == cid), None)


def _opt(card, oid):
    return next(o for o in card["options"] if o["id"] == oid)


def _resource(res, name):
    return next((x for x in res["derived"]["classResources"] if x["name"] == name), None)


def _pruned(res, cid):
    return " | ".join(p["reason"] for p in res["pruned"] if p["choiceId"] == cid)


def _problem_ids(res):
    return [p["id"] for p in res["problems"]]


def _dependent_ids(res):
    return [c["id"] for c in res["choices"] if c["id"].startswith("class:warlock:invocation:")]


def _srd_only(catalog):
    bare = copy.copy(catalog)
    bare.features = {k: v for k, v in catalog.features.items() if not k.startswith(("xphb-", "opt-")) or k.startswith("opt-") and not k.endswith("-xphb")}
    bare.class_2024_records = {}
    bare.class_2024_level_features = {}
    bare.classes_2024 = {}
    return bare




LONGSWORD = [{"itemId": "longsword", "qty": 1, "equipped": True}]


def _l(k=1):
    """Lessons of the First Ones instance id (1 = the base id, k > 1 = `<id>~k`)."""
    return LESSONS if k == 1 else f"{LESSONS}~{k}"


def time_resolve(draft, catalog, n=20):
    """Mean resolve() time in ms over n runs (after one warm-up)."""
    resolve(draft, catalog)
    start = time.perf_counter()
    for _ in range(n):
        resolve(draft, catalog)
    return (time.perf_counter() - start) / n * 1000
