# The ASI-or-Feat Mechanic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** At every ASI-granting class level, the player may pick either an ability-score increase (today's 7 combos, unchanged) or one eligible feat from the real 95-entry ("General" category minus the literal "Ability Score Improvement" catalog entry) pool — a single merged Choice per level. Picking a feat applies its full granted-effect set (Phase 4c-i machinery) and, if it has choice-shaped content, cascades those as real, selectable sub-choices (Phase 4c-ii machinery, reused via a new `origin` parameter for cid-scoping).

**Architecture:** No new choice-building mechanism. `_asi_choice_templates`'s option list grows to include feat options (namespaced `feat:{index}`, disabled when a prerequisite isn't met). A new pre-pass, `_resolve_asi_selected_feats(resolved_classes, catalog)`, runs alongside the existing `_resolve_granted_feats` call and resolves any feat a class's current `choices` dict already names at one of its ASI levels — feeding the SAME `resolved_feats` list every other feat-effects function already consumes generically, plus a per-level ability-bonus-delta map threaded into `_apply_asi_progression`. `_feat_choice_templates`/`_feat_ability_bonus_choice_templates` gain an optional `origin` parameter so a feat's cascaded sub-choice cids can be scoped `class:{cls_id}:{lvl}:asi:feat:{index}:...` instead of the background-only default `feat:{index}:...`, avoiding a collision if the same feat is ever reachable from two origins.

**Tech Stack:** Same as every prior phase — Python/Flask backend, TypeScript/React frontend, no new dependencies.

## Global Constraints

- **Full design spec**: `docs/superpowers/specs/2026-09-28-builder-v2-asi-or-feat-design.md` — read it before starting if anything below is unclear; this plan implements it exactly.
- **Safe no-op regression guard**: every existing ASI-related test (`_apply_asi_progression`, `_asi_choice_templates`, and the full multiclass/leveling test suite) must pass UNCHANGED. A draft with no ASI-level feat selections (every level unfilled or filled with a plain ASI combo, exactly as today) must be byte-identical to pre-this-plan output. This is the single most important guard — `_apply_asi_progression` is load-bearing code the whole leveling system depends on.
- **`origin=None` preserves Phase 4c-ii's exact existing behavior** in `_feat_choice_templates`/`_feat_ability_bonus_choice_templates` — background-granted feats' cids, tests, and behavior must not change at all.
- **The real 95-entry General feat pool**, minus the literal `Ability Score Improvement` (XPHB) catalog entry (excluded because it duplicates the app's own hardcoded 7-combo ASI path) — 94 real feat options per ASI level.
- **Real feats grounded this session** (re-verify exact shapes fresh at implementation time against `catalog.feats`, this is a live catalog, not a frozen fixture): Actor/XPHB, Crossbow Expert/XPHB, Great Weapon Master/XPHB, Durable/XPHB (no choice-shaped content at all); Skill Expert/XPHB (`skillProficiencies: [{"any": 1}]` — a genuine proficiency choice — AND `ability: [{"choose": {"from": [...]}}]` — a genuine ability-bonus choice, on the SAME feat); Chef/XPHB (`toolProficiencies: [{"cook's utensils": true}]` — FIXED, not a choice — alongside a genuine choice-shaped ability bonus); Grappler/XPHB (STR 13 prerequisite, offers a choice-shaped +1 among STR/DEX/CON — the concrete case for the self-bonus-prerequisite fix).
- **`resolved_classes`** (built early in `resolve()`, well before the "Final ability scores" section, around where `primary = resolved_classes[0]` is set) is a list of dicts, each with `cls_id`, `cls`, `level`, `subclass_id`, `subclass`, `class_choices` (that class's own `choices` dict from the draft) — this is the exact object `_resolve_asi_selected_feats` operates on, not raw `draft.classes`.
- **`resolved_feats = _resolve_granted_feats(granted_feats, catalog, granted_feat_refs)`** is the current call, around line 1500 in `server/engine/resolve.py` (re-locate the exact line before editing — it will have shifted). Every downstream feat-effects consumer (`_feat_ability_bonuses`, `_feat_proficiency_ids`, `_feat_languages`, `_feat_expertise_skills`, `_feat_saving_throw_proficiencies`, `_feat_senses`, `_species_damage_modifiers`/`_species_condition_immunities`'s `feats` parameter, `_feat_prerequisite_problems`, `sheet.grantedFeats` assembly) already reads `resolved_feats` generically — appending ASI-selected feats to this SAME list is the only wiring those consumers need; do not special-case ASI-selected feats in any of them.

---

### Task 1: `origin` parameter on `_feat_choice_templates`/`_feat_ability_bonus_choice_templates`

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Produces: `_feat_choice_templates(feats: list[dict], origin: str | None = None) -> list[dict]` and `_feat_ability_bonus_choice_templates(feats: list[dict], origin: str | None = None) -> list[tuple[dict, dict]]` — when `origin` is given, every cid this call builds uses `origin` as the prefix instead of `f"feat:{feat['index']}"`. Only ever call with a non-`None` origin when `feats` has exactly ONE entry (document this constraint in each function's docstring — origin-scoping a multi-feat list would collide all of them onto the same prefix, which is never the actual call shape either background or ASI call sites use).

- [ ] **Step 1: Read both functions fresh in the current file**

`grep -n "_feat_choice_templates\|_feat_ability_bonus_choice_templates" server/engine/resolve.py` — confirm current line numbers and exact cid-building lines (`f"feat:{feat['index']}:languages"`, `f"feat:{feat['index']}:proficiency-choice-{i}"`, `f"feat:{feat['index']}:ability-bonus"`) before editing.

- [ ] **Step 2: Write failing tests**

```python
def test_feat_choice_templates_origin_param_scopes_the_cid(catalog):
    # Skill Expert/XPHB has real proficiency_choices content (ground the
    # exact real shape via catalog.feats before trusting this literal).
    skill_expert = catalog.feats.get("skill-expert-xphb")
    assert skill_expert is not None, "ground the real catalog id before trusting this test"
    default_templates = _feat_choice_templates([skill_expert])
    scoped_templates = _feat_choice_templates([skill_expert], origin="class:fighter:4:asi:feat:skill-expert-xphb")
    assert all(t["id"].startswith("feat:skill-expert-xphb:") for t in default_templates)
    assert all(t["id"].startswith("class:fighter:4:asi:feat:skill-expert-xphb:") for t in scoped_templates)
    # Same label/description/options — only the cid prefix differs.
    assert [t["label"] for t in default_templates] == [t["label"] for t in scoped_templates]


def test_feat_ability_bonus_choice_templates_origin_param_scopes_the_cid(catalog):
    skill_expert = catalog.feats.get("skill-expert-xphb")
    default_pairs = _feat_ability_bonus_choice_templates([skill_expert])
    scoped_pairs = _feat_ability_bonus_choice_templates([skill_expert], origin="class:fighter:4:asi:feat:skill-expert-xphb")
    assert default_pairs[0][0]["id"] == "feat:skill-expert-xphb:ability-bonus"
    assert scoped_pairs[0][0]["id"] == "class:fighter:4:asi:feat:skill-expert-xphb:ability-bonus"
    assert scoped_pairs[0][1] is skill_expert  # the paired feat itself is unaffected by origin
```

(Ground the exact real `catalog.feats` key for Skill Expert/XPHB — likely `"skill-expert-xphb"` matching this project's established `slug-source` convention, confirm via `catalog.feats.keys()` before trusting the literal.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && ../.venv/bin/pytest tests/test_resolve.py -v -k "origin_param"`
Expected: FAIL — `origin` isn't a parameter yet (TypeError).

- [ ] **Step 4: Implement**

Add `origin: str | None = None` to both signatures. Inside each, replace every `f"feat:{feat['index']}:..."` cid construction with:
```python
cid_prefix = origin if origin is not None else f"feat:{feat['index']}"
cid = f"{cid_prefix}:languages"  # (or :proficiency-choice-{i}, or :ability-bonus, per the existing line)
```
Update each function's docstring to note the new parameter and the single-feat constraint when it's given. Do NOT change `source` (still `{"kind": "feat", "id": feat["index"], "label": feat["name"]}` — the `source.id` stays the bare feat index regardless of cid scoping, since `source` identifies WHICH feat, not where the choice came from).

- [ ] **Step 5: Run to verify tests pass, then full suite green**

Run: `cd server && ../.venv/bin/pytest tests/test_resolve.py -v -k "origin_param"`
Then: `cd server && ../.venv/bin/pytest tests/ -v` — full suite green (555 baseline + 2 new), zero regressions. Every existing Phase 4c-ii test calls these functions with no `origin` arg — confirm none of them break.

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: add origin param to feat choice-template builders for cid scoping

_feat_choice_templates/_feat_ability_bonus_choice_templates default to
Phase 4c-ii's existing feat:{index}:... cid shape (origin=None,
unchanged behavior for background-granted feats). A caller can now
pass an explicit origin prefix instead, so a feat granted from a
different mechanism (the upcoming ASI-or-feat slice) can scope its
own cascaded choices without colliding with a background-granted
instance of the same feat.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Feat options in `_asi_choice_templates`

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `catalog.feats` (filtered to `category == "G"`, minus the literal Ability Score Improvement entry), `_feat_structured_prerequisite`/`_feat_prerequisite_alt_met` (Phase 4c-i, reused unchanged for the disabled-option check).
- Produces: `_asi_choice_templates(cls_id, cls_name, asi_levels, scores_by_level, catalog, total_level, use_prerequisites)` — extends the EXISTING function's signature (3 new params: `catalog`, `total_level`, `use_prerequisites`) so each level's `options` list includes the 7 existing ASI combos PLUS one option per eligible General feat.

- [ ] **Step 1: Ground the real General feat pool and the ASI-exclusion id**

```bash
cd server && ../.venv/bin/python -c "
from catalog.loader import load
catalog = load()
general = {k: v for k, v in catalog.feats.items() if v.get('category') == 'G'}
print('General feat count:', len(general))
asi_feat = next((k for k, v in general.items() if v['name'] == 'Ability Score Improvement'), None)
print('ASI-feat catalog id to exclude:', asi_feat)
"
```
(If `catalog.feats` doesn't carry a `category` field yet, check `official_source.py`'s `_feats_from_5etools` — it may need a small addition to pass the raw `category` field through; ground this before assuming the field exists, since Phase 4c-i's own grounding notes didn't name `category` among the fields it explicitly converts.)

- [ ] **Step 2: Write failing tests**

```python
def test_asi_choice_templates_includes_eligible_general_feats(catalog):
    templates = _asi_choice_templates("fighter", "Fighter", [4], {4: {"STR": 15, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}}, catalog, total_level=4, use_prerequisites=False)
    assert len(templates) == 1
    option_ids = {o["id"] for o in templates[0]["options"]}
    assert "feat:actor-xphb" in option_ids  # ground the real catalog id before trusting this literal
    # The literal "Ability Score Improvement" catalog feat must never appear as its own option.
    assert not any("ability-score-improvement" in oid for oid in option_ids)
    # 7 existing ASI combos + 94 General feats (95 minus the ASI-feat exclusion).
    assert len(option_ids) == 7 + 94


def test_asi_choice_templates_disables_a_feat_option_with_unmet_prerequisite(catalog):
    # Grappler/XPHB requires STR >= 13 (ground the real prerequisite shape first).
    templates = _asi_choice_templates("fighter", "Fighter", [4], {4: {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}}, catalog, total_level=4, use_prerequisites=True)
    grappler_option = next(o for o in templates[0]["options"] if o["id"] == "feat:grappler-xphb")
    assert grappler_option.get("disabled") is True
    assert "prerequisite" in grappler_option.get("disabledReason", "").lower()


def test_asi_choice_templates_feat_options_not_disabled_when_prerequisites_off(catalog):
    templates = _asi_choice_templates("fighter", "Fighter", [4], {4: {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}}, catalog, total_level=4, use_prerequisites=False)
    grappler_option = next(o for o in templates[0]["options"] if o["id"] == "feat:grappler-xphb")
    assert not grappler_option.get("disabled")
```

(Ground every literal catalog id — `feat:actor-xphb`, `feat:grappler-xphb` — against Step 1's real output before trusting these placeholders; the id format is `feat:{catalog key}`, confirm this matches `_asi_choice_templates`'s actual new option-id construction once you write it.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && ../.venv/bin/pytest tests/test_resolve.py -v -k "asi_choice_templates_includes or asi_choice_templates_disables or feat_options_not_disabled"`
Expected: FAIL — `_asi_choice_templates` doesn't accept these new params yet, and/or the option list doesn't include feats yet.

- [ ] **Step 4: Implement**

Extend `_asi_choice_templates`'s signature and body. Read the EXISTING function first (it currently builds `options` from `asi_mod.asi_combinations()` only) and extend the SAME `options` list construction, not a parallel one:

```python
def _asi_choice_templates(
    cls_id: str, cls_name: str, asi_levels: list[int], scores_by_level: dict[int, dict[str, int]],
    catalog: Catalog, total_level: int, use_prerequisites: bool,
) -> list[dict]:
    general_feats = [
        f for f in catalog.feats.values()
        if f.get("category") == "G" and f["name"] != "Ability Score Improvement"
    ]
    general_feats.sort(key=lambda f: f["name"])
    templates = []
    for lvl in asi_levels:
        current_scores = scores_by_level.get(lvl, {})
        options = []
        for option_id, deltas in asi_mod.asi_combinations():
            option = {"id": option_id, "label": _asi_option_label(deltas)}
            if asi_mod.asi_exceeds_cap(deltas, current_scores):
                option["disabled"] = True
                option["disabledReason"] = "would exceed the ability score cap of 20"
            options.append(option)
        for feat in general_feats:
            option = {"id": f"feat:{feat['index']}", "label": feat["name"]}
            prereq = _feat_structured_prerequisite(feat)
            if use_prerequisites and prereq is not None:
                if not any(_feat_prerequisite_alt_met(alt, total_level, current_scores) for alt in prereq):
                    option["disabled"] = True
                    option["disabledReason"] = "prerequisite not met"
            options.append(option)
        cid = f"class:{cls_id}:{lvl}:asi"
        source = {"kind": "class", "id": cls_id, "label": cls_name, "level": lvl}
        templates.append({
            "id": cid, "source": source, "label": "Ability Score Improvement",
            "description": "Increase one ability score by 2, or two ability scores by 1 each — or take a feat instead.",
            "count": 1,
            "options": options,
        })
    return templates
```

Update the ONE call site (`choice_templates += _asi_choice_templates(rc_cls_id, rc_cls["name"], rc_asi_levels, rc_asi_scores_by_level)`, inside the per-class loop) to pass the 3 new arguments — `catalog` (already in scope, `resolve()`'s own parameter), `total_level` (already computed earlier in `resolve()`), `use_prerequisites` (reuse the SAME `preferences.usePrerequisites.feats` toggle `_feat_prerequisite_problems` already reads — read that exact line fresh and mirror it, don't reintroduce a new preferences key).

If `catalog.feats` doesn't yet carry a `category` field (check Step 1's output), add it in `server/catalog/official_source.py`'s `_feats_from_5etools` — a single new key, `"category": raw.get("category")`, alongside whatever fields that function already copies through; this is a small, additive, backward-compatible catalog field, not a shape change to anything existing.

- [ ] **Step 5: Run to verify tests pass, then full suite green**

Run the 3 new tests, then `cd server && ../.venv/bin/pytest tests/ -v` — full suite green, zero regressions. Pay particular attention to any EXISTING test that calls `_asi_choice_templates` with the OLD 4-argument signature — update those call sites too (search `_asi_choice_templates(` across `test_resolve.py`).

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/catalog/official_source.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: offer eligible General feats as ASI-level choice options

_asi_choice_templates' per-level options list now includes one option
per real "General"-category feat (94, excluding the literal "Ability
Score Improvement" catalog entry which duplicates the app's own
hardcoded 7-combo ASI path), disabled with a reason when its
prerequisite isn't met and usePrerequisites.feats is on — reusing
_feat_structured_prerequisite/_feat_prerequisite_alt_met unchanged.
Selecting a feat option doesn't yet apply its effects — that's the
next task in this plan.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Resolve and apply an ASI-selected feat

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Consumes: `resolved_classes` (already built early in `resolve()`), `catalog.feats`, `_feat_ability_bonus_deltas` (Phase 4c-ii, unchanged), `_feat_choice_templates`/`_feat_ability_bonus_choice_templates` with the `origin` param (Task 1).
- Produces: `_resolve_asi_selected_feats(resolved_classes: list[dict], catalog: Catalog) -> tuple[list[dict], dict[str, list[tuple[str, int]]]]` — returns `(asi_selected_feats, feat_deltas_by_cid)`. `asi_selected_feats` is a flat list of resolved feat dicts, each tagged with `feat["_asi_origin"] = f"class:{cls_id}:{lvl}:asi:feat:{feat['index']}"` (used by Task 1's `origin` param at this feat's own choice-template call sites). `feat_deltas_by_cid` maps each `class:{cls_id}:{lvl}:asi` cid to that level's total ability-bonus delta list (fixed `ability_bonuses` + any already-selected `ability_bonus_options` choice), for `_apply_asi_progression` to apply.
- Also modifies `_apply_asi_progression`'s signature to accept and apply this delta map.

- [ ] **Step 1: Re-read `_apply_asi_progression` and the `resolved_feats`/"Final ability scores" call sites fresh**

`grep -n "_apply_asi_progression\|resolved_feats = _resolve_granted_feats\|feat_bonuses = _feat_ability_bonuses" server/engine/resolve.py` — confirm current line numbers before editing; both will have shifted since this plan was written.

- [ ] **Step 2: Write failing tests**

```python
def test_asi_selected_feat_with_no_choice_content_applies_fixed_effects(catalog):
    # Actor/XPHB: +1 CHA fixed, no choice-shaped content (ground the real shape first).
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["level"] = 4
    draft["classes"][0]["choices"]["class:fighter:4:asi"] = ["feat:actor-xphb"]
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    assert resolution["derived"]["abilityScores"]["CHA"] == 8 + 1 + 4  # ground the real base/modifier math against this draft's actual base scores
    assert any(f["name"] == "Actor" for f in resolution["sheet"].get("grantedFeats", []))
    feat_sourced_choices = [c for c in resolution["choices"] if c["source"]["kind"] == "feat"]
    assert feat_sourced_choices == []  # Actor has no choice-shaped content, nothing should cascade


def test_asi_selected_feat_with_proficiency_and_ability_choice_cascades_and_applies(catalog):
    # Skill Expert/XPHB: skillProficiencies any-1 AND a genuine ability_bonus_options choice.
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["level"] = 4
    draft["classes"][0]["choices"]["class:fighter:4:asi"] = ["feat:skill-expert-xphb"]
    resolution = resolve(draft, catalog)
    cascaded_cids = {c["id"] for c in resolution["choices"] if c["source"]["kind"] == "feat"}
    prof_cid = next(cid for cid in cascaded_cids if "proficiency-choice" in cid and "skill-expert-xphb" in cid)
    ability_cid = next(cid for cid in cascaded_cids if "ability-bonus" in cid and "skill-expert-xphb" in cid)
    assert prof_cid.startswith("class:fighter:4:asi:feat:skill-expert-xphb:")
    assert ability_cid.startswith("class:fighter:4:asi:feat:skill-expert-xphb:")
    # Select both cascaded sub-choices and confirm they apply.
    draft["classes"][0]["choices"][prof_cid] = ["<a real skill option id — ground against the resolved template>"]
    draft["classes"][0]["choices"][ability_cid] = ["str"]  # ground the real option id
    resolution2 = resolve(draft, catalog)
    assert resolution2["problems"] == []
    assert resolution2["derived"]["abilityScores"]["STR"] > resolution["derived"]["abilityScores"]["STR"]


def test_the_ability_score_improvement_catalog_feat_is_never_offered(catalog):
    templates = _asi_choice_templates("fighter", "Fighter", [4], {4: {}}, catalog, total_level=4, use_prerequisites=False)
    option_ids = {o["id"] for o in templates[0]["options"]}
    asi_feat = next(f for f in catalog.feats.values() if f["name"] == "Ability Score Improvement")
    assert f"feat:{asi_feat['index']}" not in option_ids


def test_two_classes_selecting_the_same_feat_at_different_asi_levels_do_not_collide(catalog):
    draft = _fighter_ranger_multiclass_draft()  # or build inline — ground the real fixture name/shape in this test file first
    draft["classes"][0]["choices"]["class:fighter:4:asi"] = ["feat:skill-expert-xphb"]
    draft["classes"][1]["choices"]["class:ranger:4:asi"] = ["feat:skill-expert-xphb"]
    resolution = resolve(draft, catalog)
    assert resolution["problems"] == []
    cascaded_cids = {c["id"] for c in resolution["choices"] if c["source"]["kind"] == "feat"}
    fighter_cids = {cid for cid in cascaded_cids if cid.startswith("class:fighter:4:asi:")}
    ranger_cids = {cid for cid in cascaded_cids if cid.startswith("class:ranger:4:asi:")}
    assert fighter_cids and ranger_cids and fighter_cids.isdisjoint(ranger_cids)


def test_asi_progression_with_no_feat_selection_is_a_byte_identical_no_op(catalog):
    # The critical regression guard — run one of the EXISTING pre-this-plan
    # ASI tests (find a real one in this file, e.g. a plain ASI-combo
    # selection test) and confirm its assertions still hold unmodified.
    ...
```

(This task's tests need real ground-truth values for base ability scores, real option ids for Skill Expert's cascaded choices, and a real multiclass draft fixture already used elsewhere in this test file — locate and reuse an existing fixture/helper rather than inventing a new draft shape; ground every placeholder against what you actually observe before trusting it.)

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && ../.venv/bin/pytest tests/test_resolve.py -v -k "asi_selected_feat or ability_score_improvement_catalog_feat or same_feat_at_different_asi_levels"`
Expected: FAIL — selecting a feat option currently does nothing (falls through `_apply_asi_progression`'s existing `if raw_selected[0] in combos` check, since a `feat:...` id is never in `combos`).

- [ ] **Step 4: Implement**

Add `_resolve_asi_selected_feats`:
```python
def _resolve_asi_selected_feats(
    resolved_classes: list[dict], catalog: Catalog,
) -> tuple[list[dict], dict[str, list[tuple[str, int]]]]:
    """Mirrors _resolve_granted_feats' role for background grants, but for
    a class's own ASI-level feat pick. Reads each already-resolved class's
    `class_choices` for a `class:{cls_id}:{lvl}:asi` selection naming a
    `feat:{index}` option (built by Task 2's extended
    _asi_choice_templates) rather than a plain ASI-combo id. Runs BEFORE
    the "Final ability scores" section (same call-site neighborhood as
    _resolve_granted_feats) so an ASI-selected feat's ability bonus is
    ready before _apply_asi_progression needs it, and so the resolved
    feat can join `resolved_feats` before every other feat-effects
    function (proficiencies, languages, senses, etc.) runs."""
    asi_selected_feats: list[dict] = []
    feat_deltas_by_cid: dict[str, list[tuple[str, int]]] = {}
    for rc in resolved_classes:
        cls_id, cls, level, class_choices = rc["cls_id"], rc["cls"], rc["level"], rc["class_choices"]
        if not (cls_id and cls):
            continue
        for lvl in _asi_granting_levels(catalog, cls_id, level):
            cid = f"class:{cls_id}:{lvl}:asi"
            raw_selected = class_choices.get(cid) or []
            if not (isinstance(raw_selected, list) and len(raw_selected) == 1):
                continue
            selected_id = raw_selected[0]
            if not (isinstance(selected_id, str) and selected_id.startswith("feat:")):
                continue
            feat_index = selected_id[len("feat:"):]
            feat = catalog.feats.get(feat_index)
            if not feat:
                continue
            origin = f"{cid}:feat:{feat_index}"
            feat = dict(feat)
            feat["_asi_origin"] = origin
            asi_selected_feats.append(feat)
            deltas = list(feat.get("ability_bonuses_as_tuples") or [
                (e["ability_score"]["index"].upper(), e["bonus"]) for e in feat.get("ability_bonuses", [])
            ])
            ability_envelope = feat.get("ability_bonus_options")
            if ability_envelope:
                chosen = class_choices.get(f"{origin}:ability-bonus") or []
                deltas_by_option = _feat_ability_bonus_deltas(ability_envelope)
                for opt_id in chosen:
                    deltas.extend(deltas_by_option.get(opt_id, []))
            if deltas:
                feat_deltas_by_cid[cid] = deltas
    return asi_selected_feats, feat_deltas_by_cid
```
(The `ability_bonuses_as_tuples` fallback line is defensive — ground the REAL shape of `feat["ability_bonuses"]` against the current catalog before trusting either branch; simplify to just the list-comprehension form if `ability_bonuses_as_tuples` doesn't exist as a real field, which is likely — don't leave dead defensive code in the final implementation.)

Extend `_apply_asi_progression` to accept and apply the delta map:
```python
def _apply_asi_progression(
    base_scores: dict[str, int], asi_levels: list[int], class_choices: dict, cls_id: str | None,
    feat_deltas_by_cid: dict[str, list[tuple[str, int]]] | None = None,
) -> tuple[dict[int, dict[str, int]], dict[str, int]]:
    combos = dict(asi_mod.asi_combinations())
    feat_deltas_by_cid = feat_deltas_by_cid or {}
    scores_by_level: dict[int, dict[str, int]] = {}
    running = dict(base_scores)
    for lvl in asi_levels:
        scores_by_level[lvl] = dict(running)
        cid = f"class:{cls_id}:{lvl}:asi"
        raw_selected = class_choices.get(cid) or []
        if isinstance(raw_selected, list) and len(raw_selected) == 1 and raw_selected[0] in combos:
            deltas = combos[raw_selected[0]]
            if not asi_mod.asi_exceeds_cap(deltas, running):
                running = asi_mod.apply_asi(deltas, running)
        elif cid in feat_deltas_by_cid:
            running = asi_mod.apply_asi(feat_deltas_by_cid[cid], running)
    return scores_by_level, running
```
(Confirm `asi_mod.apply_asi` doesn't itself enforce the combo cap in a way that would reject an already-computed feat delta — read it fresh; a feat's own ability bonus is RAW-uncapped by the ASI mechanism's own combo-shape rules, only the 1-30 range check later in `resolve()` should ever flag it.)

Wire both into `resolve()`:
1. Right after `resolved_feats = _resolve_granted_feats(...)`: `asi_selected_feats, feat_deltas_by_cid = _resolve_asi_selected_feats(resolved_classes, catalog)` then `resolved_feats = resolved_feats + asi_selected_feats`.
2. In the per-class loop's `_apply_asi_progression` call, add `feat_deltas_by_cid` as the 5th argument.
3. In the per-class loop, alongside the existing `choice_templates += _asi_choice_templates(...)` line, also add the cascaded sub-choices for any feat selected at one of THIS class's own ASI levels: build a small per-class filter (`[f for f in asi_selected_feats if f.get("_asi_origin", "").startswith(f"class:{rc_cls_id}:")]`) and call `_feat_choice_templates(that_subset_one_at_a_time, origin=feat["_asi_origin"])` / `_feat_ability_bonus_choice_templates(...)` per feat (Task 1's single-feat-per-call constraint), appending their output to `choice_templates`. Also apply the selected sub-choices' OTHER effects (proficiency/language) the SAME way the existing merge-site machinery already does for background-granted feats' cascaded choices — re-read how Phase 4c-ii's merge sites pick these up generically (by `source.kind == "feat"` and cid substring) to confirm NO additional wiring is needed here beyond appending to `choice_templates` and `all_selections` (the general `all_selections.update(rc["class_choices"])` line already covers this class's own choices dict, which is where these selections live).

- [ ] **Step 5: Run to verify tests pass, then full suite green**

Run the new tests, then `cd server && ../.venv/bin/pytest tests/ -v` — full suite green, zero regressions, especially every pre-existing ASI/multiclass test.

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
feat: resolve and apply an ASI-level feat selection

_resolve_asi_selected_feats mirrors _resolve_granted_feats for a
class's own ASI-level pick, feeding the same resolved_feats list every
other feat-effects function already consumes generically, plus a
per-cid ability-bonus delta map threaded into _apply_asi_progression
so an ASI-selected feat's bonus (fixed + any already-chosen
ability_bonus_options delta) is applied at the right point in the
per-class leveling walk. Cascaded sub-choices reuse Task 1's origin
param, scoped class:{cls_id}:{lvl}:asi:feat:{index}:... so the same
feat chosen at two different classes/levels never collides.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Prerequisite self-bonus fix for choice-shaped ability bonuses

**Files:**
- Modify: `server/engine/resolve.py`
- Test: `server/tests/test_resolve.py`

**Interfaces:**
- Modifies: `_feat_prerequisite_problems` — currently subtracts each feat's own FIXED `ability_bonuses` before checking its own prerequisite; extend it to also subtract that feat's own CHOSEN `ability_bonus_options` delta, when one was selected.

- [ ] **Step 1: Re-read `_feat_prerequisite_problems` fresh**

`grep -n "_feat_prerequisite_problems" server/engine/resolve.py` — read the whole function fresh; it currently takes `(feats, total_level, final_scores, use_prerequisites)`. Confirm the exact current subtraction loop before extending it.

- [ ] **Step 2: Write failing tests**

```python
def test_grapplers_own_chosen_ability_bonus_cannot_satisfy_its_own_prerequisite(catalog):
    # Grappler/XPHB: STR >= 13 prerequisite, offers a choice-shaped +1 among STR/DEX/CON.
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["level"] = 4
    draft["classes"][0]["choices"]["class:fighter:4:asi"] = ["feat:grappler-xphb"]
    draft["classes"][0]["choices"]["class:fighter:4:asi:feat:grappler-xphb:ability-bonus"] = ["str"]
    draft["preferences"] = {"usePrerequisites": {"feats": True}}
    draft["abilities"]["base"]["STR"] = 12  # below 13 before Grappler's own bonus
    resolution = resolve(draft, catalog)
    assert any(p["id"].startswith("feat-prerequisite-unmet-") for p in resolution["problems"])


def test_grappler_with_a_genuinely_met_prerequisite_is_not_flagged(catalog):
    draft = _fighter_acolyte_human_draft()
    draft["classes"][0]["level"] = 4
    draft["classes"][0]["choices"]["class:fighter:4:asi"] = ["feat:grappler-xphb"]
    draft["classes"][0]["choices"]["class:fighter:4:asi:feat:grappler-xphb:ability-bonus"] = ["dex"]
    draft["preferences"] = {"usePrerequisites": {"feats": True}}
    draft["abilities"]["base"]["STR"] = 13  # meets the prerequisite on its own, regardless of which ability Grappler's own bonus targets
    resolution = resolve(draft, catalog)
    assert not any(p["id"].startswith("feat-prerequisite-unmet-") for p in resolution["problems"])
```

- [ ] **Step 3: Run to verify they fail**

Run: `cd server && ../.venv/bin/pytest tests/test_resolve.py -v -k "grapplers_own_chosen or grappler_with_a_genuinely_met"`
Expected: the first test FAILS (no problem is currently flagged, since Grappler's own chosen +1 STR isn't subtracted).

- [ ] **Step 4: Implement**

`_feat_prerequisite_problems` needs each feat's own chosen ability-bonus delta available per-feat. Thread it in as a new parameter, `chosen_ability_deltas_by_feat_index: dict[str, list[tuple[str, int]]] | None = None` (built by the SAME early pass that already computes `feat_bonuses` — Task 3's `_resolve_asi_selected_feats` already computes this per-cid for ASI-selected feats; for a background-granted feat with its own `ability_bonus_options`, the EXISTING early pass at the `_feat_ability_bonus_choice_templates`/`feat_ability_choice_pairs` call site already computes `selected_feat_abilities`/`feat_ability_deltas` per feat too — read that loop fresh and build a `{feat["index"]: deltas}` dict there, covering BOTH origins in one small dict built once, right where `feat_bonuses` itself is already accumulated).

Inside `_feat_prerequisite_problems`'s existing per-feat subtraction loop, after the existing `for entry in feat.get("ability_bonuses", [])` block, add:
```python
for ab_key, delta in (chosen_ability_deltas_by_feat_index or {}).get(feat["index"], []):
    scores_without_own_bonus[ab_key] = scores_without_own_bonus.get(ab_key, 0) - delta
```
Update the docstring to note this now also covers choice-shaped bonuses, referencing the 10 real General feats named in the design spec's grounding (Athlete, Charger, Dual Wielder, Grappler, Inspiring Leader, Observant, Polearm Master, Ritual Caster, Sentinel, Speedy) as the concrete real cases this closes.

- [ ] **Step 5: Run to verify tests pass, then full suite green**

Run the 2 new tests, then `cd server && ../.venv/bin/pytest tests/ -v` — full suite green, zero regressions (especially Phase 4c-i's own existing prerequisite tests, which must stay passing unmodified since `chosen_ability_deltas_by_feat_index` defaults to covering "no chosen deltas" for any feat that doesn't have one).

- [ ] **Step 6: Commit**

```bash
git add server/engine/resolve.py server/tests/test_resolve.py
git commit -m "$(cat <<'EOF'
fix: a feat's own CHOSEN ability bonus can no longer satisfy its own prerequisite

_feat_prerequisite_problems already subtracted a feat's own FIXED
ability_bonuses before checking its own prerequisite (Phase 4c-i
Finding 2). Extends the same discipline to a feat's own CHOSEN
ability_bonus_options delta, newly reachable now that feats are
freely selectable via an ASI level (10 real General feats combine an
ability prerequisite with a choice-shaped ability bonus: Athlete,
Charger, Dual Wielder, Grappler, Inspiring Leader, Observant, Polearm
Master, Ritual Caster, Sentinel, Speedy).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Frontend — render cascaded ASI-feat choices on ClassPage

**Files:**
- Modify: `frontend/src/pages/ClassPage.tsx`
- Verify (likely no change needed, confirm fresh): `frontend/src/types.ts`, `frontend/src/components/StepNav.tsx`, `frontend/src/DraftContext.tsx`

**Interfaces:**
- Modifies: `ClassPage.tsx`'s choice-filtering predicate, currently `c.source.kind === "class" && c.id.startsWith(\`class:${classId}:\`)` — widen to also accept `"feat"`, mirroring EXACTLY the fix Phase 4c-ii's final review made to `BackgroundPage.tsx` for the identical reason (a new choice kind produced by the backend, invisible in the frontend, while the export gate blocks on it regardless of kind).

- [ ] **Step 1: Read the current `ClassPage.tsx` choice-filtering code fresh**

`grep -n "source.kind\|SET_CHOICE_SELECTION\|kind ===" frontend/src/pages/ClassPage.tsx` — confirm the exact current line/variable names (they may have shifted since this plan was written) before editing.

- [ ] **Step 2: Confirm `types.ts` already has `"feat"` in `ChoiceSourceKind`**

`grep -n "ChoiceSourceKind" frontend/src/types.ts` — Phase 4c-ii already added `"feat"` to this union; confirm it's still there (no change expected, this step is a verification, not an edit).

- [ ] **Step 3: Widen the ClassPage filter**

Change the choice-filtering predicate from `c.source.kind === "class" && c.id.startsWith(...)` to `(c.source.kind === "class" || c.source.kind === "feat") && c.id.startsWith(...)`. Confirm the `handleChange`/selection-dispatch code already sends `source: "class"` for every choice rendered on this page (mirroring `BackgroundPage.tsx`'s own hardcoded `source: "background"`, per Phase 4c-ii's fix) — read the actual current dispatch code before assuming this, don't guess.

- [ ] **Step 4: Check whether a per-class "pending choices" badge/count needs the same widening**

Search `StepNav.tsx` for how it counts a class step's pending choices (mirroring the Background step's own `kinds.includes(...)` fix from Phase 4c-ii) — if the Class step's `Step.kind` is similarly a fixed list/array, add `"feat"` to it the same way; if it counts differently (e.g. purely by cid prefix, not by kind), confirm feat-sourced cascaded choices are still counted correctly without a change, and note which is the case in your report.

- [ ] **Step 5: Verify — backend tests, frontend build, and a manual end-to-end check**

Run `cd server && ../.venv/bin/pytest tests/ -v` (this task shouldn't touch backend code, but confirm nothing else in the worktree broke). Run `cd frontend && npm run build` (or the actual current build script name — check `package.json`) — must be clean, zero type errors. If practical, do a quick manual sanity check: start the dev servers, select a General feat with cascaded choices (e.g. Skill Expert) at a Fighter's level-4 ASI slot, and confirm its sub-choices render on the Class page and the export gate clears once they're filled in — note in your report whether you were able to do this manually or only verified via code tracing.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ClassPage.tsx
# add frontend/src/components/StepNav.tsx too if Step 4 required a change
git commit -m "$(cat <<'EOF'
fix: render an ASI-selected feat's cascaded choices on ClassPage

Mirrors Phase 4c-ii's identical BackgroundPage fix: a feat's own
choice-shaped content (source.kind "feat") now renders alongside the
class's own choices, instead of being invisible while the export gate
still blocks on it.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Notes

- **Spec coverage**: every section of the design spec (feat-options merge into the existing ASI Choice, the pre-pass + `_apply_asi_progression` extension, cid origin-scoping via Task 1's new parameter, the prerequisite self-bonus fix, the one required frontend change) has a task.
- **Placeholder scan**: every real feat name/id used in tests is named in the Global Constraints as something to re-verify fresh against the live catalog before trusting the literal — this project's established discipline, not a plan gap; Task 3's `ability_bonuses_as_tuples` defensive line is explicitly flagged as needing grounding-and-likely-simplification, not left as unexplained dead code.
- **Type consistency**: `_asi_choice_templates`'s new signature (Task 2) and `_apply_asi_progression`'s new signature (Task 3) are each introduced once and their ONE call site updated in the same task — no task downstream re-defines either signature differently.
- **Scope check**: bounded to the mechanic itself plus its minimum required frontend surface (Task 5). Explicitly excludes `repeatable`/`exclusiveFeatCategory`/non-structured-prerequisite enforcement/`additionalSpells` — unchanged, pre-existing, already-disclosed non-goals inherited from Phase 4c-i, not re-litigated here.
