"""The ONLY module of the official-data converters that imports
`chargen.sources` (see the sys.path note below); every other module of this
package, and every caller, gets `official_dir` / `has_official` /
`_repo_root` from here (or via the `catalog.official_source` shim)."""
from __future__ import annotations

from pathlib import Path
import sys

_repo_root = Path(__file__).resolve().parents[3]  # server/catalog/official/paths.py -> official -> catalog -> server -> repo root
if str(_repo_root) not in sys.path:
    # Appended, not prepended: the root also holds the v1 app.py/storage.py,
    # which must never shadow the server's own modules (only `chargen` is needed).
    sys.path.append(str(_repo_root))

from chargen.sources import official_dir, has_official  # noqa: E402,F401  (must follow the sys.path fix above)
