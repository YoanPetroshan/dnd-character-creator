import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


import os  # noqa: E402

import pytest  # noqa: E402

# The data-source variables of a developer's shell must not change what a test sees. `DND_OFFICIAL_DATA=none` is kept: CI
# (the SRD-only job) and `env DND_OFFICIAL_DATA=none pytest` ask for it on purpose for the whole run. A test that needs a
# variable sets it with monkeypatch (the fixture below runs first).
_KEEP = {("DND_OFFICIAL_DATA", "none")}


@pytest.fixture(autouse=True)
def _clean_dnd_environment(monkeypatch):
    for name, value in list(os.environ.items()):
        if name.startswith("DND_") and (name, value.strip().lower()) not in _KEEP:
            monkeypatch.delenv(name)
