# Translated long texts (overlays)

`<lang>/<kind>.json` holds translations of long catalog texts that the English data does not carry. Kinds: `bg/spells.json`, `bg/species.json`, `bg/items.json`, `bg/item-rules.json` (the last three are filled batch by batch).

    { "<spell index>": { "hash": "<sha1>", "desc": [...], "higherLevel": [...], "material": str|null, "castingCondition": str|null } }

`hash` is the sha1 of the English `desc`, `higherLevel`, `material`, `castingCondition` the entry was translated from
(`i18n.content.store.source_hash`). `GET /api/spells/<id>?lang=bg` serves an entry only while its hash matches the current
English text; a missing or stale entry falls back to English (`textLang: "en"`). A null `material` / `castingCondition`
keeps the English value. The offline build bundles `*.json` from this folder (not this file).

Workflow (run from `server/`):

    python -m i18n.content.tool --kind spells export --source XPHB --limit 20 --only-missing --out work.json   # or --ids fireball,shield
    # translate desc / higherLevel / material / castingCondition in work.json; keep id and hash
    python -m i18n.content.tool --kind spells apply work.json     # validates each record, merges the valid ones, exit 1 on any REJECT
    python -m i18n.content.tool --kind spells status              # translated / stale / missing per source

Validation: hash current, same paragraph counts, same dice expressions (`8d6`), every English number present in the
Bulgarian text (extra ones are fine: "20 фута (6 м)"), no empty or untranslated paragraph, Cyrillic in every paragraph.

Other kinds (same `export` / `apply` / `status`, `--kind species|items|item-rules`; `python -m i18n.content.spells ...` stays as a shim for spells):

    species     { "<race id>": { "hash", "fluff": [...], "traits": [ { "desc": [...] }, ... ] } }
                hash = sha1 of the served English fluff and every trait's desc list; the trait count and order must match
                (trait names stay English); `export` lists the trait names for the translator only
    items       { "<item id>": { "hash", "desc": [...], "special": [...] } }
    item-rules  { "property:<index>:<PHB|XPHB>" | "mastery:<Name>": { "hash", "desc": [...] } }   (loader arrives with the item route)

The same validation applies to every kind (paragraph counts per list, dice, numbers, Cyrillic, nothing left in English).
`store.overlay_species` / `overlay_items` / `overlay_rule` apply a fresh entry to a response body and set `textLang`.
