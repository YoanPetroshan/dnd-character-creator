# D&D Character Creator

A standalone character-creation app for D&D 5e (SRD content), split out of
the `dnd-app-bg` play app's builder. Produces three exports per character:

- `current.yaml` — the canonical sheet (same shape/location convention the
  play app's character library already uses, at
  `~/.claude/dnd/characters/<Name>/current.yaml` — override the root with
  `DND_CAMPAIGN_ROOT`)
- `character.md` — a human-readable Markdown sheet
- `character.pdf` — the official Wizards of the Coast fillable sheet, filled in

## Setup

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt

## Run

    .venv/bin/python3 app.py

Then open http://127.0.0.1:5300/

## Test

    .venv/bin/pytest tests/ -v

## Architecture

See `docs/superpowers/specs/2026-09-13-character-creator-app-design.md` for
the full design rationale. In short: `chargen/` (ported verbatim from
`dnd-app-bg-local`) is the rules/content engine and has zero dependencies
outside the standard library; everything else in this repo (`storage.py`,
`sheet_derive.py`, `markdown_render.py`, `pdf_fill.py`, `app.py`) is new,
and none of it imports from `dnd-app-bg-local`'s play engine.

Not yet done: linking this app's output back into the play app as a
campaign-recruitable character. The storage path is chosen so that step
needs no data migration when it happens.
