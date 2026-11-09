"""VC0 character-test harness. Run from server/tests: ``../../.venv/bin/python -m tools.chartest --help``.

The package puts server/ and server/tests on sys.path so the engine and kitchen_sink import from anywhere.
Only ``checks.py`` is the oracle; it never imports engine code (the engine is reached through ``spec.resolve_spec``)."""
import pathlib
import sys

_TESTS = pathlib.Path(__file__).resolve().parents[2]
for _p in (_TESTS.parent, _TESTS):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
