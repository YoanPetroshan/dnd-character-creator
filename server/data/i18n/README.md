# Translated long texts (overlays)

`<lang>/<kind>.json` holds translations of long catalog texts that the English data does not carry. Kinds: `bg/spells.json`, `bg/species.json`, `bg/items.json`, `bg/item-rules.json`, `bg/feats.json`, `bg/choice-texts.json` (the last four are filled batch by batch).

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

Other kinds (same `export` / `apply` / `status`, `--kind species|items|item-rules|feats|choice-texts`; `python -m i18n.content.spells ...` stays as a shim for spells):

    species     { "<race id>": { "hash", "fluff": [...], "traits": [ { "desc": [...] }, ... ] } }
                hash = sha1 of the served English fluff and every trait's desc list; the trait count and order must match
                (trait names stay English); `export` lists the trait names for the translator only
    items       { "<item id>": { "hash", "desc": [...], "special": [...] } }
    item-rules  { "property:<index>:<PHB|XPHB>" | "mastery:<Name>": { "hash", "desc": [...] } }   (loader arrives with the item route)

The same validation applies to every kind (paragraph counts per list, dice, numbers, Cyrillic, nothing left in English).
`store.overlay_species` / `overlay_items` / `overlay_rule` apply a fresh entry to a response body and set `textLang`.

    feats       { "<feat index>": { "hash", "desc": [...] } }
                hash = sha1 of the English `desc` paragraphs (the feat text flattened as GET /api/feats/<id> serves it);
                same validation as the other kinds (paragraph count, dice, numbers, Cyrillic)
    choice-texts  { "<sha1 of the English text>": { "ref": "<option or card id it was found on>", "en": "<English>", "bg": "<Bulgarian>" } }
                The descriptions the choice cards and their options carry (`choices[].description`, `choices[].options[].description`)
                are plain English data strings. `store.localize_content(resolution, lang)` (after `localize`, in /api/resolve
                and the exports) replaces every one whose sha1 is a key with `bg`; the key IS the hash, so a changed English
                text stops matching and English is served (ten `opt-*-xphb` ids carry two different texts, hence text keys, not ids).
                `export` harvests the distinct texts by resolving the drafts of `server/tests/i18n_zoo.py` plus a sweep of the
                catalog `opt-*` features, and writes records `{id: <sha1>, name: <option or card id>, source, hash: <sha1>,
                desc: [<the whole English text>]}`; the translator returns `desc` as usual, `apply` stores it joined by spaces
                (no paragraph-count check; dice, every English number, Cyrillic and non-empty are still checked).
                `status` lists a key that no harvested text matches any more as stale (`(unused)`). Needs the official data
                to see all texts. The en payload never changes.
