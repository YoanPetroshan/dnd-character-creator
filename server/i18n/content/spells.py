"""Thin shim: `python -m i18n.content.spells export|apply|status ...` is `python -m i18n.content.tool --kind spells ...`
(developer-only, not in the offline pack). See tool.py."""
from __future__ import annotations

import sys

from i18n.content import tool
from i18n.content.tool import (  # noqa: F401  (re-exported for the existing callers and tests)
    apply_records, export_records, overlay_path, status_counts, validate, write_overlay,
)


def main(argv=None) -> int:
    return tool.main(argv, default_kind="spells", prog="python -m i18n.content.spells")


if __name__ == "__main__":
    sys.exit(main())
