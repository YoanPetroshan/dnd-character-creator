# Translated long texts (overlays)

`<lang>/<kind>.json` holds translations of long catalog texts that the English data does not carry. Today: `bg/spells.json`.

    { "<spell index>": { "hash": "<sha1>", "desc": [...], "higherLevel": [...], "material": str|null, "castingCondition": str|null } }

`hash` is the sha1 of the English `desc`, `higherLevel`, `material`, `castingCondition` the entry was translated from
(`i18n.content.store.source_hash`). `GET /api/spells/<id>?lang=bg` serves an entry only while its hash matches the current
English text; a missing or stale entry falls back to English (`textLang: "en"`). A null `material` / `castingCondition`
keeps the English value. The offline build bundles `*.json` from this folder (not this file).

Workflow (run from `server/`):

    python -m i18n.content.spells export --source XPHB --limit 20 --only-missing --out work.json   # or --ids fireball,shield
    # translate desc / higherLevel / material / castingCondition in work.json; keep id and hash
    python -m i18n.content.spells apply work.json     # validates each record, merges the valid ones, exit 1 on any REJECT
    python -m i18n.content.spells status              # translated / stale / missing per source

Validation: hash current, same paragraph counts, same dice expressions (`8d6`), every English number present in the
Bulgarian text (extra ones are fine: "20 фута (6 м)"), no empty or untranslated paragraph, Cyrillic in every paragraph.
