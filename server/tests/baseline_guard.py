"""S14 (audit TEST-02): the writers of the stored baselines (`WRITE_EXPORT_BASELINE`, `WRITE_SHEET_BASELINE`,
`WRITE_SERVICE_BASELINE`) refuse to run in CI (the `CI` variable is set by GitHub Actions and most other CI systems), and
every write prints what it changes, so a baseline can no longer be overwritten silently by a pipeline or an absent-minded
`export WRITE_...=1`. The proof that "only this changed" is still the job of the person who rewrites (see
docs / the execution plan); this only makes the write loud and impossible in CI."""
from __future__ import annotations

import json
import os
import pathlib


class BaselineWriteRefused(RuntimeError):
    pass


def refuse_in_ci(label: str) -> None:
    if os.environ.get("CI"):
        raise BaselineWriteRefused(f"{label}: refusing to rewrite a stored baseline when CI is set; rewrite it on a developer machine and commit it")


def change_summary(old: dict | None, new: dict) -> str:
    """One line: how many entries are new, removed and changed, with the first few names."""
    old = old or {}
    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
    def names(items):
        return ", ".join(items[:5]) + (f", ... ({len(items)})" if len(items) > 5 else "")
    return f"+{len(added)} new [{names(added)}], -{len(removed)} removed [{names(removed)}], ~{len(changed)} changed [{names(changed)}]"


def write_baseline(path: pathlib.Path, new: dict, old: dict | None, label: str) -> None:
    """Write `new` as the baseline file, after the CI refusal and with a printed summary against `old`."""
    refuse_in_ci(label)
    print(f"[{label}] rewriting {path.name}: {change_summary(old, new)}")
    path.write_text(json.dumps(new, indent=1, sort_keys=True) + "\n", encoding="utf-8")
