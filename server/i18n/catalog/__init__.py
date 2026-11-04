"""The message catalog: `MESSAGES[key] = {"en": template, "bg": template}`.

Merged from one module per kind of engine message. Wired in I1, empty on purpose: I2 (problems and warnings), I3 (pruned),
I4 (disabled reasons) and I5 (labels and descriptions) fill the modules as the emission sites are converted.
A key is unique across the modules; a duplicate raises at import.
"""
from __future__ import annotations

from i18n.catalog import disabled, labels, problems, pruned, warnings

_MODULES = (problems, warnings, pruned, disabled, labels)


def build() -> dict[str, dict[str, str]]:
    """The merged catalog; raises ValueError when two modules define the same key."""
    merged: dict[str, dict[str, str]] = {}
    for module in _MODULES:
        clash = merged.keys() & module.MESSAGES.keys()
        if clash:
            raise ValueError(f"duplicate message keys in {module.__name__}: {sorted(clash)}")
        merged.update(module.MESSAGES)
    return merged


MESSAGES = build()
