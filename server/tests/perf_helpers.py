"""Load-robust wall-clock checks for the "resolve() stays under 50 ms" tests.

A single (or mean) wall-clock measurement flakes when the machine is busy (load average > 100 was seen), because any
scheduler hiccup lands inside the timed region. The bound still protects the same thing, so it is not raised: every
check is warm (the caller resolves once before timing) and takes the BEST of N individually timed runs. A run that
is never fast means resolve() itself is slow, not that the machine was busy. On failure the best and the median are
both reported so a load artefact can be told from a real regression.
"""
import statistics
import time

LIMIT_MS = 50.0


class Laps(list):
    """Per-run wall-clock times in seconds."""


def measure(fn, runs=10, warmup=1):
    """Call fn() `warmup` times untimed, then `runs` times timed one by one. Returns Laps (seconds)."""
    for _ in range(warmup):
        fn()
    laps = Laps()
    for _ in range(runs):
        t = time.perf_counter()
        fn()
        laps.append(time.perf_counter() - t)
    return laps


def assert_fast(laps, what=None, limit_ms=LIMIT_MS):
    """The best run must be under limit_ms; the failure message reports best and median over all runs."""
    best = min(laps) * 1000
    median = statistics.median(laps) * 1000
    assert best < limit_ms, (
        f"{what + ': ' if what else ''}best of {len(laps)} runs {best:.1f} ms, median {median:.1f} ms "
        f"(limit {limit_ms:g} ms for the best run)")
