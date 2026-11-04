"""Tagged engine messages (I1 of the bilingual plan).

The engine writes English text. From I2 on, every message it emits is a `Msg`: a `str` that carries the catalog `key`
and the `params` it was rendered from. Because it IS the English text, nothing about English changes: `==`, `startswith`,
`in`, JSON serialization (`json.dumps` writes a `str` subclass as a plain string), hashing and `!r` all behave as for the
text, and the engine may keep comparing its own messages. A caller that wants another language runs `localize` on the
finished resolution: it walks it and swaps each `Msg` for the rendering of its key in that language.

    m = msg("level-unsupported", level="x", cls="fighter")     # Msg, text = the English template filled in
    render(m, "bg")                                             # the Bulgarian rendering (English if the key has none)
    localize(resolution, "bg")                                  # a copy of the resolution with every Msg rendered

Catalog: `i18n.catalog.MESSAGES[key] = {"en": template, "bg": template}`; templates use `str.format` fields and two
extras: the plural filter `{n|one|many}` and the list join `{names:, }` (see `format_template`).

Tag loss: string operations on a `Msg` (`+`, `%`, f-strings, `.strip()`, `"".join`) return a plain `str`, and the tag is
gone. The localizer then leaves that text as it is, in English. Conversions must therefore build the whole message with
`msg(...)` (params, not concatenation); the I2 tests check BG coverage over the zoo.

`lang` is always an explicit argument (the Pyodide worker has no HTTP): "en" returns its input untouched.
"""
from __future__ import annotations

import string
from typing import Any

from i18n.catalog import MESSAGES

LANGS = ("en", "bg")
DEFAULT_LANG = "en"


class Msg(str):
    """The English text of a catalog message plus the key and params it was made from."""

    key: str
    params: dict

    def __new__(cls, text: str, key: str, params: dict | None = None) -> "Msg":
        self = super().__new__(cls, text)
        self.key = key
        self.params = dict(params or {})
        return self

    def __reduce__(self):
        # deepcopy / copy / pickle: str subclasses with attributes need an explicit rebuild (also deep-copies the params)
        return (_rebuild, (str(self), self.key, self.params))


def _rebuild(text: str, key: str, params: dict) -> Msg:
    return Msg(text, key, params)


class _Formatter(string.Formatter):
    """`str.format` plus the plural filter: a field `{n|one|many}` yields `one` when the parameter n equals 1, else
    `many`. The two forms may not contain `{ } : ! [ ] |`.
    A list or tuple parameter with a format spec is joined: `{names:, }` with ", ", `{names: or }` with " or " (the
    text after the colon is the separator; without a spec a list formats as its repr) (I3: the engine hands over the names it used to join itself, so each can still be a nested message)."""

    def format_field(self, value, format_spec):
        if isinstance(value, (list, tuple)) and format_spec:
            return format_spec.join(str(v) for v in value)
        return super().format_field(value, format_spec)

    def get_field(self, field_name: str, args, kwargs):
        if "|" in field_name:
            name, *forms = field_name.split("|")
            if len(forms) != 2:
                raise ValueError(f"plural field {{{field_name}}} needs exactly two forms: {{n|one|many}}")
            return (forms[0] if kwargs[name] == 1 else forms[1]), name
        return super().get_field(field_name, args, kwargs)


_FORMATTER = _Formatter()


def format_template(template: str, params: dict) -> str:
    """Fill a catalog template: `str.format` fields (`{name}`, `{n!r}`) and plural fields `{n|one|many}`."""
    return _FORMATTER.vformat(template, (), params)


def list_fields(template: str) -> set[str]:
    """The parameters a template formats with a join separator (`{names:, }`): they take a list."""
    return {field.split("|")[0] for _t, field, spec, _c in string.Formatter().parse(template) if field and spec}


def template_fields(template: str) -> set[str]:
    """The parameter names a template uses (a plural field counts as its parameter name)."""
    names: set[str] = set()
    for _text, field, _spec, _conv in string.Formatter().parse(template):
        if field:
            names.add(field.split("|")[0].split(".")[0].split("[")[0])
    return names


def msg(key: str, /, **params: Any) -> Msg:
    """A `Msg` for `key`: its text is the English template filled in with `params` (nested `Msg` params render as
    their English text). An unknown key is a programming error and raises KeyError."""
    return Msg(format_template(MESSAGES[key]["en"], params), key, params)


def _render_param(value: Any, lang: str) -> Any:
    if isinstance(value, Msg):
        return render(value, lang)
    if isinstance(value, (list, tuple)):
        return type(value)(_render_param(v, lang) for v in value)
    return value


def check_lang(lang: str) -> str:
    if lang not in LANGS:
        raise ValueError(f"unsupported language {lang!r}; use one of {LANGS}")
    return lang


def render(m: Any, lang: str) -> Any:
    """`m` in `lang`. A value that is not a `Msg` is returned as it is. English is the stored text; another language
    uses its catalog template, or falls back to the English text when the key has no template in it."""
    check_lang(lang)
    if not isinstance(m, Msg):
        return m
    if lang == "en":
        return str(m)
    template = (MESSAGES.get(m.key) or {}).get(lang)
    if template is None:
        return str(m)
    return format_template(template, {k: _render_param(v, lang) for k, v in m.params.items()})


def _walk(node: Any, lang: str) -> Any:
    """Copy-on-change deep walk: a container with no `Msg` below it is returned as the same object."""
    if isinstance(node, Msg):
        return render(node, lang)
    if isinstance(node, dict):
        out = None
        for k, v in node.items():
            new = _walk(v, lang)
            if new is not v and out is None:
                out = dict(node)
            if out is not None:
                out[k] = new
        return node if out is None else out
    if isinstance(node, (list, tuple)):
        items = [_walk(v, lang) for v in node]
        if all(a is b for a, b in zip(items, node)):
            return node
        return items if isinstance(node, list) else tuple(items)
    return node


def localize(resolution: Any, lang: str) -> Any:
    """`resolution` with every `Msg` replaced by its rendering in `lang`. "en" returns the input itself, untouched;
    for another language the input is not modified either (containers holding a `Msg` are copied, the rest is shared)."""
    check_lang(lang)
    if lang == "en":
        return resolution
    return _walk(resolution, lang)


def parse_lang(raw: str | None) -> str:
    """The `lang` query parameter: missing (None) is "en", "bg" and "en" are themselves, anything else (including an
    empty or differently cased value) raises ValueError, which the API answers with a 400."""
    if raw is None:
        return DEFAULT_LANG
    if raw in LANGS:
        return raw
    raise ValueError(f"'lang' must be 'bg' or 'en', not {raw!r}")


def validate_catalog(messages: dict | None = None, *, require_bg: bool = False) -> list[str]:
    """Problems in a catalog: an entry needs an English template; with `require_bg` a Bulgarian one too; the two must
    use the same parameter names; every template must format (plural fields well formed). Empty list = fine."""
    problems: list[str] = []
    for key, entry in sorted((MESSAGES if messages is None else messages).items()):
        if not isinstance(entry, dict) or not isinstance(entry.get("en"), str):
            problems.append(f"{key}: no English template")
            continue
        fields = {lang: template_fields(entry[lang]) for lang in LANGS if isinstance(entry.get(lang), str)}
        if require_bg and "bg" not in fields:
            problems.append(f"{key}: no Bulgarian template")
        if len({frozenset(f) for f in fields.values()}) > 1:
            problems.append(f"{key}: placeholder mismatch {fields}")
        for lang in fields:
            try:
                joined = list_fields(entry[lang])
                format_template(entry[lang], {name: ([2] if name in joined else 2) for name in fields[lang]})
            except (ValueError, KeyError, IndexError) as exc:
                problems.append(f"{key}: {lang} template does not format ({exc})")
    return problems
