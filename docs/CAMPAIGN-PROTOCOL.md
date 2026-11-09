# Verification campaign protocol (for tester agents)

You are a "character tester". You test the engine's output for a batch of characters against the books. You do NOT fix
the engine. Plan: `docs/superpowers/plans/2026-11-04-skeleton-and-verification-campaign.md` (Part B).

## 1. Setup and what to run

Work in a scratch directory (`<scratchpad>/campaign/<batch-id>/`). All commands run from `server/tests` with the repo venv:

    cd server/tests
    PY=../../.venv/bin/python
    $PY -m tools.chartest run --tier T3 --batch 0 --size 10 --out <scratch>/findings.jsonl

* `--tier` is T1, T2, T3, T4 or WEIRD; `--batch N --size 10` selects specs N*10 .. N*10+9 of the deterministic list
  (`--seed` changes the list; leave it at 0 unless told). A spec can also be given as a spec id (regex), a JSON object or
  a `.jsonl` file.
* One line per character: `OK|FAIL <spec-id> checks=<n> fail=[RULES] known=[KG tags] <ms>`. `fail` lists only
  unexplained failures; failures that match a documented known gap are tagged `known=[KG-...]` and are not written to
  the findings file (use `--keep-known` to keep them, `gaps` to list the tags, `--no-known-gaps` to disable the tagging).
* `--no-exports` skips the Markdown/YAML/PDF/W9 checks (faster); keep exports ON for the real campaign.
* Needs the 5etools data (`server/data/official`); without it the CLI exits with code 2.

## 2. Read the report

For each FAIL line: `$PY -m tools.chartest explain <spec-id> <RULE>` prints the character's classes, ruleset, proficiency
bonus and abilities, then `expected`, `actual` and `cite` (the raw data file, field or book page the expected value comes
from). Then `$PY -m tools.chartest show <spec-id>` for the whole sheet. Also run `show` for 2 PASSING characters of the
batch and read them for anything strange (a missing feature, an odd number, a duplicated line, a wrong label).

Rule ids: oracle checks PB, ABIL-MOD, ABIL-RANGE, HP, HIT-DICE, SAVE-PROF, SAVES, SKILLS, PASSIVES, INITIATIVE, SLOTS, PACT,
SPELL-DC, CANTRIPS, SPELLS-KNOWN, SPELLBOOK, AC, SPEED, ATTACKS-PER-ACTION, FEATURES-LEVEL, FEATURES-PRESENT, RESOURCES,
MC-PREREQ, MC-PROF, DUPLICATES, FEAT-PREREQ (source: `server/tests/tools/chartest/checks.py`, one small function each);
detectors W-NUMBERS, W-EMPTY, W-DUP-IDS, W-PENDING, W-UNAVAILABLE, W-PROBLEMS, W-WARN, W-PRUNED, W-LEAK, W-IDEMPOTENT,
W-PERF, W-EXPORT, W-EXPORT-NAME, W-W9, W-EXC (resolve raised), W-FILL (the filler could not settle a legal draft; a
blocked character) (`weird.py`).

## 3. Verify every suspicious finding against the books/data

Never trust the oracle blindly: it can be wrong. For each failed check decide ONE of

* `engine` bug: the cited source says X and the engine shows Y;
* `oracle` bug: the oracle misreads the source or ignores a legitimate bonus (a feat, subclass feature or species trait);
* `known-gap`: documented in `docs/superpowers/specs/ARCHITECTURE-CURRENT-STATE.md` ("Known gaps after RP22", the
  "Deferred" lists) - search there first;
* `unclear`: the books are ambiguous or you cannot decide.

Evidence you may read (read-only): `server/data/official/**` (5etools JSON: `class/class-<name>.json` class tables with
`classTableGroups`, `races.json`, `feats.json`, `items-base.json`, `backgrounds.json`), `chargen/data/srd/*.json` (SRD
2014), the 2024 PHB markdown if present (`Resurses/`, chapters 1, 2, 4, 5, 6, 7) and the PHB page cited in `cite`.
Use `grep`/`python -c "import json..."`; do not import the engine into your own scripts except through the CLI.

## 4. File findings

The `run` command already appends engine findings to the findings file (JSON lines
`{fid, spec, spec_id, rule, severity, expected, actual, source, known_gap, occurrences}`; `fid` = hash of
rule + ruleset + classes + subclasses, so the same bug found on 20 characters is ONE record with `occurrences`).
For a finding you found by reading a sheet (no check failed) or to add your classification:

    $PY -m tools.chartest finding add --rule SKILLS --spec <spec-id> --expected "..." --actual "..." \
        --source "PHB p.xx / file:field" --severity S2 --note "engine: ..." --out <scratch>/findings.jsonl

Severity: **S1** wrong number on the sheet or exports, an exception, an export failure, a blocked legal character.
**S2** wrong or missing feature / choice / prerequisite / count, a duplicate. **S3** label, text, timing.
Put your classification (engine | oracle | known-gap | unclear) in `--note`. Oracle bugs are NOT engine findings: list
them in your report so the harness gets fixed.

Final report to the coordinator, at most 25 lines: batch id, characters run / failed, unique findings by severity with
spec id + rule + one-line expected/actual + classification, oracle bugs, two lines on the passing characters you read.

## 5. What NOT to touch

* No engine or app code (`server/engine`, `server/catalog`, `server/*.py`, `frontend`), no data (`server/data`,
  `chargen/data`), no `server/tests/golden/**`, no `*baseline*.json`, no `Resurses/`, no `docs/` except your scratch.
* Do not edit the harness (`server/tests/tools/chartest`) - report oracle bugs instead.
* No `--regenerate` of any golden, no git commit/push, no dev servers.
* Write only inside your scratch directory.
* Do not re-report a finding tagged `known=[...]`; do not downgrade a severity to make a report shorter.
