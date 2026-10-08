# Plan: enforcing feat prerequisites beyond level and ability

(Written by an Opus planner, 2026-10-08. All changes in `server/engine/resolve.py` unless noted. Baseline: run `cd server && ../.venv/bin/python -m pytest -q` after each slice; commit per slice.)

## 1. Data facts (verified against real data)
- 94 ASI-eligible feats (category G minus "Ability Score Improvement") all have a prerequisite; 50 already enforced (level/ability only). The other 44:
  - `{"level":4,"feat":[...]}` 25 feats (Dragonscarred, the 4 AU Familiar feats, Enclave Magic, 13 Greater Mark/Aberrant Mark EFA, Harper Teamwork, Lordly Resolve, Magic Connoisseur, Order's Resilience, Zhentarim Tactics)
  - `{"level":4,"spellcasting2020":true}` 12 (8 AU "<School> Adept", Elemental Adept/XPHB, Spell Sniper/XPHB, Spell Subterfuge/AU, War Caster/XPHB)
  - `{"level":4,"proficiency":[{"armor":X}]}` 5 (Heavily Armored, Heavy Armor Master, Medium Armor Master, Moderately Armored, Shield Master — XPHB)
  - Purple Dragon Commandant/FRHoF: OR of feat / `{"proficiency":[{"weaponGroup":"martial"}]}`; Spellfire Adept/FRHoF: OR of feat / `{"feature":["Spellcasting","Pact Magic"]}`; Potent Dragonmark/EFA: `{"level":4,"featCategory":["D"]}`.
- Every `feat` ref `"name|source"` maps to catalog index `f"{slug(name)}-{source.lower()}"`. Required feats are category O/D, so only background grants can satisfy them. familiar-friend-au is granted by no background → the 4 AU Familiar feats will always be disabled (correct).
- App proficiency ids: `light-armor`, `medium-armor`, `heavy-armor`, `all-armor` (Fighter/Paladin primary), `shields`, `martial-weapons`. Real chain: Lightly → Moderately → Heavily Armored → Heavy Armor Master (Wizard 16 can take all at 4/8/12/16).
- Spellcasting test: `spells_mod.single_class_spell_slots(catalog, cls_id, level)` non-empty for Wizard 1, Warlock 1, Paladin 2; `{}` for Paladin 1, Ranger 1, Fighter 4. Don't test for key presence (zero rows exist).

## 2. Stays disclosed-only (one line each in the ARCHITECTURE doc)
campaign; background (always satisfied by the granting background); exclusiveFeatCategory (only Dragonmark feats, category D, never ASI-eligible); race; other/otherSummary; spellcasting (2014)/spellcastingFeature (Rune Shaper only); dict-shaped `level` (IoHS, Squire); repeatableHidden (display flag; `repeatable` already honoured); feat_options (Rewarded/Ruined BMT).
`_feat_prerequisite_problems` (background second pass) KEEPS the old `{"level","ability"}` key set — never widen it (would give false problems for ASI-gated picks).

## 3. Core design
A. Held-state:
```python
from dataclasses import dataclass, field
@dataclass
class _HeldFeatState:
    feat_indices: set[str] = field(default_factory=set)
    feat_categories: set[str] = field(default_factory=set)
    proficiency_ids: set[str] = field(default_factory=set)
    has_spellcasting_feature: bool = False
    def copy(self): return _HeldFeatState(set(self.feat_indices), set(self.feat_categories), set(self.proficiency_ids), self.has_spellcasting_feature)
    def add_feat(self, feat):
        self.feat_indices.add(feat["index"])
        if feat.get("category"): self.feat_categories.add(feat["category"])
        self.proficiency_ids.update(_feat_proficiency_ids([feat]))
```
(check `_feat_proficiency_ids` return type, use as is.)
B. Keep `_STRUCTURED_FEAT_PREREQUISITE_KEYS = {"level","ability"}`. Add `_ASI_GATE_PREREQUISITE_KEYS` (starts equal; each slice adds keys). `_feat_structured_prerequisite(feat, supported_keys=_STRUCTURED_FEAT_PREREQUISITE_KEYS)`; replace the `set(alt.keys()) <= ...` test with `_alt_is_verifiable(alt, supported_keys)`: key-subset AND per-key value validation (`level` must be int; `feature` non-empty subset of {"Spellcasting","Pact Magic"}; `proficiency` entries single-key dicts in `_PROFICIENCY_PREREQ_SATISFIERS`). OR-of-alternatives all-or-nothing rule stays: any unverifiable alternative → None (not enforced).
C. `_feat_prerequisite_alt_met(alt, total_level, scores, held=None)`: existing level/ability unchanged; new keys checked only when present.
D. `_feat_prerequisite_unmet_reason(feat, total_level, scores, use_prerequisites, held, catalog=None) -> str|None`: None if prerequisites off, not structured under `_ASI_GATE_PREREQUISITE_KEYS`, or any alternative met. Else `"prerequisite not met"`; when exactly one alternative, append `": requires " + "; ".join(parts)` for failing parts: feat → `the {catalog.feats[idx]['name']} feat`; spellcasting2020/feature → `the Spellcasting or Pact Magic feature`; proficiency armor X → `{X} armor proficiency` (shield → `shield proficiency`), weaponGroup → `martial weapon proficiency`; featCategory D → `a Dragonmark feat`; level → `character level {n}`; ability → `{AB} {min}` joined with ` or `. `_feat_option_prerequisite_met(..., held=None)` becomes `return _feat_prerequisite_unmet_reason(...) is None` (keep name).
E. `_apply_asi_progression` gets kwargs `held=None`, `held_by_level=None` (out-param; keep the existing 3-tuple return). After `scores_by_level[lvl] = dict(running)`: `if held_by_level is not None: held_by_level[lvl] = held.copy() if held else _HeldFeatState()`. Pass `held` to `_feat_option_prerequisite_met` in the feat branch. After a pick passes the gate call `held.add_feat(asi_feats_by_cid[cid])` (so a feat never satisfies itself, later picks never satisfy earlier ones, blocked picks never chain).
F. resolve() wiring: before the per-class loop (after `use_feat_prereqs`, ~line 2065) `held = _HeldFeatState(); for f in background_feats: held.add_feat(f)`. Pass ONE shared `held` to every `_apply_asi_progression` call (accumulates across classes in resolved_classes order = "first pick wins" order). Per class `rc_held_by_level = {}` passed in. Pass `held_by_level=rc_held_by_level` to `_asi_choice_templates` (new kwarg, default None); inside, `reason = _feat_prerequisite_unmet_reason(feat, total_level, current_scores, use_prerequisites, (held_by_level or {}).get(lvl) or _HeldFeatState(), catalog)`; if reason: disabled + disabledReason=reason. A prerequisite failure wins over "already taken". Templates MUST read the per-level snapshot, never the live object. Hand-edited picks need nothing new: a pick whose option would be disabled is blocked in the walk (existing `feat-prerequisite-unmet-{index}` problem). Optionally append `f" ({reason})"` to that problem's message (grep tests for "isn't met at" first; tests assert ids not messages).
Disclosed timing simplification: pre-walk inputs (class proficiencies, spellcasting, race) use the FINAL character, same as `level` uses total_level; permissive, never a false disable.

## 4. Slices (run suite + commit after each; assert specific problem ids/option flags, not `problems == []`; use `@pytest.mark.skipif(not has_official(), ...)`, `_fighter_acolyte_human_draft(...)` with `preferences=_feat_prereqs_on()`; include every needed book in `sources`, e.g. ["srd","xphb","efa"]; override `background={"id":"house-cannith-heir-efa","choices":{}}`; new tests go in server/tests/test_resolve.py after the ASI-or-feat sections)

### Slice 0 — plumbing, no behaviour change
Add A–F with `_ASI_GATE_PREREQUISITE_KEYS = {"level","ability"}`. Tests: (1) `_HeldFeatState().copy()` independent; `add_feat(catalog.feats["lightly-armored-xphb"])` → proficiency_ids ⊇ {"light-armor","shields"}, feat_categories == {"G"}. (2) `_feat_prerequisite_unmet_reason(catalog.feats["actor-xphb"], 4, {"CHA":9}, True, _HeldFeatState(), catalog)` contains "prerequisite not met" and "CHA 13". (3) existing suite stays at exactly 589+(whatever the current count is) green.

### Slice 1 — `feat` key (25 feats)
Add "feat" to `_ASI_GATE_PREREQUISITE_KEYS`. In alt check: `any(_feat_ref_index(r) in held.feat_indices for r in alt["feat"])` with
`def _feat_ref_index(ref): name,_,source = ref.partition("|"); return f"{slug(name)}-{source.lower()}"`.
Purple Dragon Commandant and Spellfire Adept stay unenforced until slices 3/2.
Tests: (1) Fighter 4, background house-cannith-heir-efa, sources srd+efa: option `feat:greater-mark-of-making-efa` at `class:fighter:4:asi` not disabled. (2) background acolyte-xphb, sources srd+xphb+efa: disabled, reason == "prerequisite not met: requires the Mark of Making feat" (verify exact feat display name from catalog). (3) hand-edited pick with that acolyte draft → problem `feat-prerequisite-unmet-greater-mark-of-making-efa`, feat absent from sheet["grantedFeats"], ASI choice selected == [] and pending. (4) Magic Connoisseur (sources srd+xphb+au): acolyte-xphb and sage-xphb enabled; house-cannith-heir-efa disabled. (5) `feat:elemental-familiar-au` always disabled, reason contains "Familiar Friend". (6) prerequisites toggled off → all enabled. (7) chaining via `monkeypatch.setitem(catalog.feats, "test-chain-xphb", {**catalog.feats["actor-xphb"], "index":"test-chain-xphb","name":"Test Chain","prerequisite":[{"level":4,"feat":["actor|xphb"]}]})`: Fighter 8, CHA 14, Actor at 4 + test-chain at 6 → both applied; swapped → test-chain at 4 blocked, Actor at 6 applied. (8) `test_asi_choice_templates_includes_eligible_general_feats` still counts 21+94.

### Slice 2 — `spellcasting2020` and `feature` (13 feats)
Add both keys (with feature value-validation). Pre-walk: `held.has_spellcasting_feature = any(rc["cls"] and spells_mod.single_class_spell_slots(catalog, rc["cls_id"], rc["level"]) for rc in resolved_classes)`. Alt check: if `alt.get("spellcasting2020")` or `"feature" in alt` require it.
Tests (`feat:war-caster-xphb`, srd+xphb): Fighter 4 disabled, reason contains "Spellcasting or Pact Magic"; Wizard 4 enabled; Warlock 4 enabled; Fighter 4 + Paladin 1 disabled; Fighter 4 + Paladin 2 enabled; hand-edited Fighter 4 pick → problem `feat-prerequisite-unmet-war-caster-xphb`; Spellfire Adept (srd+xphb+frhof): acolyte-xphb Fighter disabled; Wizard 4 enabled (skip the spellfire-background case unless a granting background is found quickly).

### Slice 3 — `proficiency` (5 feats + Purple Dragon Commandant)
```python
_PROFICIENCY_PREREQ_SATISFIERS = {
  ("armor","light"): {"light-armor","all-armor"}, ("armor","medium"): {"medium-armor","all-armor"},
  ("armor","heavy"): {"heavy-armor","all-armor"}, ("armor","shield"): {"shields"},
  ("weaponGroup","martial"): {"martial-weapons"}}
```
Alt's proficiency list is AND (real data has one entry); entry met if `held.proficiency_ids & satisfiers`. Pre-walk, add FIXED grants only: classes (`rc["cls"]["proficiencies"]` if rc["index"]==0 else `rc["cls"].get("multi_classing",{}).get("proficiencies",[])`), race/subrace traits (`catalog.traits[ref]["proficiencies"]`, same expression as resolve.py ~line 2534; `race`/`subrace` resolved before the loop), background `starting_proficiencies`, background feats (already via add_feat). Disclosed gap: proficiency CHOICE selections unavailable pre-walk; scan species/background/feat `proficiency_choices` for armor/shield/martial options and document the result.
Tests (srd+xphb): (1) real chain Wizard 16: lightly-armored@4, moderately-armored@8, heavily-armored@12, heavy-armor-master@16 → no `feat-prerequisite-unmet-*` problems, armor ⊇ {"light-armor","shields","medium-armor","heavy-armor"}, all four in grantedFeats. (2) ordering Wizard 8: moderately@4, lightly@8 → moderately blocked (problem id, "medium-armor" absent), lightly applied; level-4 reason == "prerequisite not met: requires light armor proficiency". (3) heavily-armored@4 + heavy-armor-master@8 → both blocked, "heavy-armor" absent. (4) synthetic feat (monkeypatch) with prerequisite heavy armor and proficiencies copied from heavily-armored-xphb, Wizard 4 → blocked. (5) Fighter 4: heavy-armor-master-xphb enabled (all-armor). (6) race-sourced: Wizard 4 Mountain Dwarf (ground real subrace id first) → medium-armor-master-xphb enabled. (7) Shield Master: Wizard 4 disabled; Cleric 4 enabled. (8) Purple Dragon Commandant (srd+xphb+frhof): Wizard 4 + acolyte-xphb disabled with reason "prerequisite not met"; Wizard 4 + purple-dragon-squire-frhof enabled; Fighter 4 + acolyte-xphb enabled; Wizard 8 with martial-weapon-training-xphb@4 and Commandant@8 enabled.

### Slice 4 — `featCategory` (Potent Dragonmark)
Add key; check `any(c in held.feat_categories for c in alt["featCategory"])`. Tests (srd+efa+xphb, `feat:potent-dragonmark-efa`): Fighter 4 + house-lyrandar-heir-efa enabled; + aberrant-heir-efa enabled; + acolyte-xphb disabled, reason contains "Dragonmark"; no self-satisfaction.

### Slice 5 — docs
ARCHITECTURE-CURRENT-STATE.md: enforced keys and where (ASI walk gate + option reasons only); held-state rules (background feats, then earlier applied ASI picks in walk order; never the feat itself/later/blocked); timing simplification; disclosed-only list (section 2); 4 AU Familiar feats permanently disabled. Update the comment above `_STRUCTURED_FEAT_PREREQUISITE_KEYS` and `_feat_structured_prerequisite` docstring (incl. stale "85/305").

## 5. Risks
Walk and templates must both go through `_feat_prerequisite_unmet_reason` with the same snapshot. Source filtering: a background filtered out by draft.sources isn't held → dependants disabled (tests must list every book). Duplicate-skipped picks never reach the walk.
