# Phase 4c-ii — Close the Feat Choice-Effects Gap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A background-granted feat's choice-shaped `ability_bonus_options`/`proficiency_choices`/`language_options` — already converted into the catalog by Phase 4c-i but never turned into a selectable `Choice` (the exact disclosed gap that phase's final review found and left for this slice) — now produce a real `Choice` in `resolution.choices`, and a player's selection actually applies to the sheet.

**Architecture:** A new `_feat_choice_templates(feats: list[dict]) -> list[dict]` in `server/engine/resolve.py`, mirroring the EXISTING `_background_choice_templates`/`_species_choice_templates` pattern exactly (same `build_choice_template` call, same `":proficiency-choice"` cid-substring convention). Three merge sites (already grounded against the current real code — see Global Constraints) get a new `"feat"` kind alongside the existing `"species"`/`"background"` ones. No new choice-building mechanism, no new merge architecture — purely additive participation in machinery that already exists.

**Tech Stack:** Same as every prior phase — Python/Flask backend, no new dependencies.

## Global Constraints

- **Safe no-op for a feat with no choice-shaped content, or no feat at all.** A draft with `resolved_feats == []`, or every resolved feat's `ability_bonus_options`/`proficiency_choices`/`language_options` all `None`/empty, must produce IDENTICAL `resolution.choices`/sheet output to today's. Checked at the end of every task.
- **The exact 3 merge sites needing a new `"feat"` kind, confirmed at plan-writing time by direct grep of the current `server/engine/resolve.py`:**
  1. `proficient_skills` merge: `if c["source"]["kind"] in ("class", "species", "background"):` → add `"feat"`.
  2. `_categorize_proficiency` merge: two `elif` branches (`"species"`/`"background"`, each gated on `"proficiency-choice" in c["id"]`) → add a third for `"feat"`.
  3. Language merge: `if c["source"]["kind"] in ("background", "species") and c["id"].endswith(":languages"):` → add `"feat"`.
  Re-locate these exact lines fresh before editing — line numbers will have shifted since plan-writing.
- **The `":proficiency-choice"` cid substring is load-bearing, not decorative** — it's what merge site #2 uses to distinguish a genuine proficiency choice from any other feat-sourced choice (mirroring the EXISTING established reason this convention exists for species/background).
- **Real data grounded at plan-writing time**: Artisan/XPHB grants Crafter/XPHB, which has `toolProficiencies: [{"choose": {"from": [8 named tools], "count": 3}}]` — a real, reachable `proficiency_choices` case with solid end-to-end coverage. NO real background→feat combination currently produces a genuine `ability_bonus_options` or `language_options` CHOICE (Cult of the Dragon Initiate's and Clan Crafter's own two-entry language shapes both resolve as FIXED-only "conditional substitute" grants per Phase 4c-i's own established rule, not a choice; Harper Agent's language grant is also fixed-only, and the language itself — "thieves' cant" — isn't even a recognized slug). Test those two paths via a synthetic feat (mirroring Phase 4c-i's own established, clearly-disclosed synthetic-feat testing convention), not real data — do not claim real coverage you don't have.
- **Every claim verified against the REAL fetched data** (`~/.claude/dnd/.data/official/feats.json`, `~/.claude/dnd/.data/official/backgrounds.json`) before trusting it — this project's unbroken discipline.

---

### Task 1: `_feat_choice_templates` — proficiency choices (real end-to-end coverage)

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `build_choice_template` from `catalog/choices.py` (unchanged), `resolved_feats` (already computed by the existing `_resolve_granted_feats` bridge, Phase 4c-i — no new resolution step).
- Produces: `_feat_choice_templates(feats: list[dict]) -> list[dict]`, handling `proficiency_choices` first (the real, testable case) — `ability_bonus_options`/`language_options` come in Task 2.

- [ ] **Step 1: Confirm the exact real Crafter/XPHB shape and re-locate the 3 merge sites**

```bash
cd server
.venv/bin/python -c "
from catalog.loader import load
catalog = load()
crafter = catalog.feats.get('crafter-xphb')
print('proficiency_choices:', crafter.get('proficiency_choices') if crafter else 'NOT FOUND')
"
grep -n '"class", "species", "background"' engine/resolve.py
grep -n 'kind.*==.*"species".*and.*"proficiency-choice"\|kind.*==.*"background".*and.*"proficiency-choice"' engine/resolve.py
grep -n 'kind.*in.*("background", "species").*endswith(":languages")' engine/resolve.py
```

Confirm all three still match this plan's Global Constraints section exactly before proceeding — if `official_source.py`'s `_feat_proficiency_choices_from_5etools`-equivalent (or however Phase 4c-i's Task 3 named it) produces a differently-shaped envelope than expected, re-ground against the real current code, don't assume.

- [ ] **Step 2: Write failing tests against real data**

```python
def test_crafter_xphb_tool_choice_is_offered_as_a_real_choice(catalog):
    draft = _fighter_acolyte_human_draft(background={"id": "artisan-xphb", "choices": {}})
    resolution = resolve(draft, catalog)
    cids = {c["id"] for c in resolution["choices"]}
    tool_cid = next((cid for cid in cids if "crafter-xphb" in cid and "proficiency-choice" in cid), None)
    assert tool_cid is not None, f"expected a feat-sourced tool choice, got: {cids}"
    choice = next(c for c in resolution["choices"] if c["id"] == tool_cid)
    assert choice["count"] == 3
    assert len(choice["options"]) == 8  # ground the exact real option count/labels before trusting this


def test_selecting_the_crafter_tool_choice_reaches_the_sheet(catalog):
    draft = _fighter_acolyte_human_draft(background={"id": "artisan-xphb", "choices": {}})
    resolution = resolve(draft, catalog)
    tool_cid = next(cid for cid in {c["id"] for c in resolution["choices"]} if "crafter-xphb" in cid and "proficiency-choice" in cid)
    draft["background"]["choices"][tool_cid] = ["<3 real tool ids — ground against Step 1's real option list before trusting placeholders>"]
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    # ground the exact real sheet field path/tool ids before trusting this assertion
    assert set(draft["background"]["choices"][tool_cid]) <= set(resolution2["sheet"]["proficiencies"]["tools"])


def test_a_feat_with_no_choice_shaped_content_is_a_safe_no_op(catalog):
    # A background granting a feat with ONLY fixed content (e.g. Sailor/XPHB
    # -> Tavern Brawler/XPHB, already real from Phase 4c-i's own final-review
    # fix) must produce zero feat-sourced choices.
    draft = _fighter_acolyte_human_draft(background={"id": "sailor-xphb", "choices": {}})
    resolution = resolve(draft, catalog)
    assert not any(c["source"]["kind"] == "feat" for c in resolution["choices"])
```

(Ground every literal — the real 8 tool names/ids, the real sheet field path for tools — against Step 1's real output before trusting these placeholders.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "crafter or feat_with_no_choice"`
Expected: FAIL — no feat-sourced choice exists yet.

- [ ] **Step 4: Implement**

Add `_feat_choice_templates` to `server/engine/resolve.py`, mirroring `_background_choice_templates`'s exact structure for the proficiency-choice block:

```python
def _feat_choice_templates(feats: list[dict]) -> list[dict]:
    templates = []
    for feat in feats:
        for i, prof_envelope in enumerate(feat.get("proficiency_choices", []) or []):
            cid = f"feat:{feat['index']}:proficiency-choice-{i}"
            source = {"kind": "feat", "id": feat["index"], "label": feat["name"]}
            label = _background_proficiency_choice_label(prof_envelope)  # reuse — confirm this helper is generic enough, or find/adapt the real current labeling helper
            choose = prof_envelope.get("choose", 1)
            description = f"Choose {choose} proficienc{'ies' if choose != 1 else 'y'} of your choice."
            tpl = build_choice_template(prof_envelope, cid, source, label, description=description)
            if tpl:
                templates.append(tpl)
    return templates
```

(`_background_proficiency_choice_label` may need to be genuinely reusable across background/feat call sites, or the current code may already name it generically — confirm its real current signature before assuming this call works unmodified.)

Wire the call site into `resolve()` alongside `_background_choice_templates(bg, bg_id)`'s own existing line — `choice_templates += _feat_choice_templates(resolved_feats)`.

Extend the 3 merge sites per Global Constraints (add `"feat"` to each).

- [ ] **Step 5: Run to verify tests pass, then full suite green**

Run: `cd server && .venv/bin/python -m pytest tests/test_resolve.py -v -k "crafter or feat_with_no_choice"`
Then: `cd server && .venv/bin/python -m pytest -v` — full suite green (550 baseline + your new tests), no regressions.

- [ ] **Step 6: Commit**

```bash
cd /Users/yoanpetrov/dnd-character-creator
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: background-granted feat proficiency choices are now real Choices

_feat_choice_templates mirrors _background_choice_templates'/
_species_choice_templates' exact pattern — reuses build_choice_
template unmodified, and 3 existing merge sites (proficient_skills,
_categorize_proficiency, the language merge) gain a new "feat" kind
alongside the existing "species"/"background" ones. Closes the real,
disclosed proficiency_choices half of Phase 4c-i's Finding 3 gap:
Artisan/XPHB's grant of Crafter/XPHB now genuinely offers "choose 3
of 8 artisan's tools" instead of nothing. ability_bonus_options/
language_options are a separate follow-up task in this same plan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `_feat_choice_templates` — ability-bonus and language choices (synthetic coverage, disclosed)

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: the EXISTING `_background_ability_bonus_deltas` pattern (built Phase 4b for the 2024 background ASI's bundle shape) as the direct structural precedent for a new `_feat_ability_bonus_deltas`.
- Produces: `_feat_choice_templates` extended to also build `ability_bonus_options`/`language_options` Choice templates; the SAME merge sites (already extended in Task 1) apply the selections.

- [ ] **Step 1: Read `_background_ability_bonus_deltas` fresh, confirm its real current signature/logic**

This function maps a selected ability-bonus-choice option's id back to the actual `[(ability, delta), ...]` deltas to apply — built for the 2024 background ASI's specific "+2/+1 split or +1/+1/+1" bundle shape. Confirm whether it's ALREADY generic enough to call directly for a feat's `ability_bonus_options` (which could be either that same weighted-bundle shape OR the simpler race-style "+1 to one of N" shape — `build_choice_options`/`build_choice_template` already handle both envelope shapes uniformly at the TEMPLATE-building level; only the deltas-back-out-of-a-selection step is the question here), or needs a small, disclosed feat-specific variant.

- [ ] **Step 2: Write failing tests using a SYNTHETIC feat (disclosed, matching Phase 4c-i's own established convention)**

No real background→feat combination reaches these two paths (confirmed at plan-writing time — re-verify, don't assume). Use whatever synthetic-feat-injection helper Phase 4c-i's own test file already established (`_synthetic_feat`/`_grant_synthetic_feat` or similarly named — find the real current helper) to construct:

```python
def test_a_synthetic_feats_ability_bonus_choice_is_offered_and_applies():
    # DISCLOSED: no real background->feat grant reaches this path today
    # (confirmed 2026-09-28 against real data) — mirrors the SAME synthetic-
    # feat testing convention Phase 4c-i's own test file already
    # established for its own no-real-coverage cases.
    ...


def test_a_synthetic_feats_language_choice_is_offered_and_applies():
    # Same disclosure as above.
    ...
```

- [ ] **Step 3: Run to verify they fail, implement, verify pass, full suite green**

- [ ] **Step 4: Empirical end-to-end check across real data**

```bash
.venv/bin/python -c "
from catalog.loader import load
from engine.resolve import resolve
catalog = load()
for bg_id in ('artisan-xphb',):
    draft = {
        'classes': [{'classId': 'fighter', 'level': 1, 'choices': {}}],
        'background': {'id': bg_id, 'choices': {}},
        'species': {'id': 'human', 'choices': {}},
        'abilities': {'method': 'manual', 'base': {'STR': 16, 'DEX': 14, 'CON': 14, 'INT': 10, 'WIS': 12, 'CHA': 8}},
        'equipment': {'choices': {}, 'added': [], 'skipped': True}, 'details': {},
    }
    r = resolve(draft, catalog)
    feat_choices = [c for c in r['choices'] if c['source']['kind'] == 'feat']
    print(bg_id, '-> feat choices offered:', [c['id'] for c in feat_choices])
    print('problems:', r['problems'])
"
```

- [ ] **Step 5: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: background-granted feat ability-bonus/language choices

Extends _feat_choice_templates (Task 1) to also build
ability_bonus_options/language_options Choice templates, reusing the
same 3 merge sites already extended. No real background->feat grant
currently exercises either path (confirmed against real data) —
tested via the same synthetic-feat convention Phase 4c-i's own test
file already established, clearly disclosed as such.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage:** both halves of the design spec's scope (proficiency_choices with real coverage, ability_bonus_options/language_options with disclosed synthetic coverage) have a task each.
- **Placeholder scan:** Task 1's exact tool-id/sheet-field literals are explicitly flagged as needing re-grounding at implementation time, not guessed — matching this project's established discipline for anything not yet directly verified against real code.
- **Type consistency:** `_feat_choice_templates` is introduced once (Task 1) and extended (Task 2), not redefined; the `"feat"` kind and `":proficiency-choice"` cid convention are used identically across both tasks.
- **Scope check:** deliberately bounded to background-granted feats only — explicitly NOT the ASI-or-feat mechanic, which is the user-approved SECOND slice, a separate plan.
