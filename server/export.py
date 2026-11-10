"""Turns a Resolution (see engine/resolve.py) into a portable YAML
character sheet — a flat document with the fields a player would actually
want to keep, not the internal choices/problems bookkeeping. The field list
lives in export_fields.py (shared with the Markdown and PDF exporters).

Spell save DC / attack bonus live inside each sheet["spells"][i] entry (a
multiclass character's casters each use their own ability), so there is no
top-level scalar for them.
"""
from __future__ import annotations

import yaml

from export_fields import yaml_document
from i18n.messages import Msg


def _represent_msg(dumper, data):
    """VF7.7a: a tagged engine message (`Msg`, a str subclass; the attack-row notes now are) is written as its English text."""
    return dumper.represent_str(str(data))


yaml.SafeDumper.add_representer(Msg, _represent_msg)


def to_yaml(resolution: dict) -> str:
    # allow_unicode=True: character names in this app are routinely
    # Cyrillic (the app's own examples are Bulgarian) — without this,
    # PyYAML escapes them as \uXXXX, which is technically valid YAML but
    # unreadable to a human opening the file.
    return yaml.safe_dump(yaml_document(resolution), sort_keys=False, allow_unicode=True)
