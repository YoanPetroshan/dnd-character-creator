# Plan: feat spellcasting-ability fixes (inherit rule + spell-ability Choice)

(Opus planner, 2026-10-08. Paths under `server/`. Run `../.venv/bin/python -m pytest -q` after each slice; commit after each slice.)

## Data audit (reachable feats: category G or background-granted, with additionalSpells)
- No `ability` key but text says "spellcasting ability ... is the ability increased by this feat" (should be inherit): Cloying Mists, Light Bringer, Treacherous Allure, Vampire Touched (ABH), Ritual Caster XPHB.
- Data has `{choose:[int,wis,cha]}` but text says "is the ability increased by this feat" (should be inherit): Cold Caster FRHoF, Enclave Magic FRHoF.
- Already `inherit` and correct: Fey-Touched, Shadow-Touched, Telekinetic, Telepathic (XPHB).
- `inherit` but wrong: Magic Connoisseur AU — text: ability is "the same as the spellcasting ability chosen for your Magic Initiate feat's spells"; prerequisite `feat: ['magic initiate|xphb']`. Warlike Familiar AU is wrong the same way but unreachable (leave).
- Genuinely none/class-based (keep None): the 8 AU Adept feats; Rune Shaper is in `_FEAT_SPELLS_SKIP`.
- True choose abilities (picked when the feat is taken): Magic Initiate XPHB, the 12 EFA Marks, Child of the Sun, Emerald Enclave Fledgling, Initiate of High Sorcery, Scion of the Outer Planes, Shadowmoor Hexer, Spellfire Spark, Strixhaven Initiate. Magic Initiate PHB uses fixed abilities per variant; Aberrant Dragonmark fixed CON.

## Slice 1 — catalog rule driven by feat text (`catalog/official_source.py`)
Next to `_FEAT_SPELLS_SKIP`:
```python
_INHERIT_ABILITY_RE = re.compile(r"spellcasting ability[^.]*?\bis the ability increased by this feat", re.I)
_SAME_AS_FEAT_ABILITY_RE = re.compile(r"spellcasting ability[^.]*?chosen for your [^.]*?feat", re.I)
```
Helper `_feat_spell_ability_override(raw) -> str | dict | None`: `text = json.dumps(raw.get("entries") or [])`; (1) if `_SAME_AS_FEAT_ABILITY_RE` matches and `raw.get("prerequisite")` has exactly one `feat` ref across all entries → `{"sameAsFeat": f"{slug(name)}-{source}"}` (ref parsed `name, _, src = ref.partition("|")`; Magic Connoisseur → "magic-initiate-xphb"); (2) if `_INHERIT_ABILITY_RE` matches and `raw.get("ability")` is present → "inherit"; else None. In `_feat_spells_from_5etools` compute the override once; per entry: sameAsFeat always wins; "inherit" applies only when the entry's ability is missing/None/a `{"choose"}` dict (fixed strings never overridden); otherwise current logic. Update the `_innate_spell_ability` docstring line about "not wired into Choice machinery".
Tests (test_official_source.py, skipif not has_official, `_feats_by_id()`): every innate_spells and spell_choices entry of light-bringer-abh, cloying-mists-abh, treacherous-allure-abh, vampire-touched-abh, ritual-caster-xphb, cold-caster-frhof, enclave-magic-frhof has ability "inherit"; magic-connoisseur-au spell_choices all `{"sameAsFeat": "magic-initiate-xphb"}`; mark-of-storm-efa still `{"choose":["INT","WIS","CHA"]}` (existing test ~line 2053 still passes); magic-initiate-phb abilities unchanged (Wizard variant "INT"); warlike-familiar-au still "inherit".
test_resolve.py: `_asi_feat_spell_draft("light-bringer-abh", {_LB+"spell-variant":["light"], _LB+"ability-bonus":["cha"]})` → Light entry ability == "CHA"; without the ability-bonus pick → `{"choose":["INT","WIS","CHA"]}`.

## Slice 2 — `{prefix}:spell-ability` Choice (`engine/resolve.py`)
1. In `_feat_spell_choice_templates`, after the source is computed and before the variant block (and before its `continue`), collect dict abilities: `abil = next((e["ability"] for e in feat.get("innate_spells",[]) + feat.get("spell_choices",[]) if isinstance(e.get("ability"), dict) and e["ability"].get("choose")), None)`. If found, append a template built directly (like the variant picker): `{"id": f"{prefix}:spell-ability", "source": source, "label": f"{feat['name']}: Spellcasting Ability", "description": "Choose this feat's spellcasting ability.", "count": 1, "options": [{"id": a.lower(), "label": SAVE_ABILITY_NAMES[a.lower()]} for a in abil["choose"]]}` (import SAVE_ABILITY_NAMES from catalog.official_source). Emitted whether or not a variant is picked. Feats whose ability is "inherit" never get it. Works at both call sites (ASI: `class:fighter:4:asi:feat:X:spell-ability`; background: `feat:X:spell-ability`).
2. `_feat_spell_ability(feat, ability, choices, feats=())`: "inherit" unchanged; dict with "choose": look up `f"{prefix}:spell-ability"`; if selected return `selected[0].upper()` else the dict unchanged; dict with "sameAsFeat": find `other = next(f for f in feats if f["index"] == ref)`; missing → None; else take the first ability in other's innate_spells/spell_choices and recurse (depth guard: never recurse a second sameAsFeat); else unchanged. `_feat_innate_spells` passes `feats` through.
3. Pruning/validation: nothing new (stale cids go to `pruned`; invalid ids dropped by valid_ids filter).
4. Commit message must mention: pending `spell-ability` choices now block export for backgrounds granting these feats; fix any existing tests that assumed those backgrounds had no pending choices.
Tests (test_resolve.py): Acolyte/XPHB `_fighter_acolyte_human_draft(sources=["srd","xphb"], background={"id":"acolyte-xphb","choices":{}})`: choice `feat:magic-initiate-xphb:spell-ability` exists, options ["int","wis","cha"], pending, source.kind "feat"; with `{"feat:magic-initiate-xphb:spell-variant":["cleric-spells"], "feat:magic-initiate-xphb:spell-ability":["wis"], <cantrip spell-choice cid>:["guidance","sacred-flame"]}` every innateSpells entry with featId magic-initiate-xphb has ability "WIS"; without the pick `{"choose":["INT","WIS","CHA"]}`. Invalid pick ["str"] → selected [] and pending. House Cannith Heir (EFA, sources ["srd","efa"]): `feat:mark-of-making-efa:spell-ability` pending; pick ["int"] → Mending and Magic Weapon ability "INT". astral-drifter-aag (Magic Initiate PHB) has NO spell-ability choice. ASI feat telepathic-xphb has no spell-ability choice. Rewrite `test_magic_connoisseur_selected_spells_become_daily_innate_spells_with_inherited_ability`: with `_MC+"ability-bonus":["wis"]` and no Magic Initiate pick → `{"choose":["INT","WIS","CHA"]}`; after `background.choices["feat:magic-initiate-xphb:spell-ability"]=["cha"]` (acolyte-xphb) → Shield and Invisibility ability "CHA" despite ability-bonus WIS. Synthetic ASI feat via `_synthetic_feat` (spell_choices=[], innate_spells=[{name:"Light", spell_id:"light", level:None, uses:"at-will", ability:{"choose":["INT","WIS"]}, variant:None}], ability_bonus_options) yields both `<origin>:ability-bonus` and `<origin>:spell-ability`; spell ability follows only spell-ability (follow the existing synthetic ASI test pattern). Stale selection of `feat:magic-initiate-xphb:spell-ability` under house-cannith-heir-efa appears in `pruned`.

## Slice 3 — description grammar (`_spell_filter_description`)
```python
core = "cantrip" if level == [0] else (f"level {' or '.join(map(str, level))} " if level else "") + "spell"
if count != 1: core += "s"
# then school prefix, " from the X list", " with the Ritual tag"
return f"Choose {count} {noun}."
```
Unit tests: `_spell_filter_description(2, {"level":[0],"class":["cleric"]}) == "Choose 2 cantrips from the Cleric list."`; `(1, {"level":[1],"school":["enchantment","divination"]}) == "Choose 1 Enchantment or Divination level 1 spell."`; `(2, {"level":[1],"ritual":True}) == "Choose 2 level 1 spells with the Ritual tag."` (adapt to the real signature; keep existing description tests passing).

## Slice 4 — docs
In ARCHITECTURE-CURRENT-STATE.md "Feats' additionalSpells" section: the regex rule and `sameAsFeat` marker, the `{prefix}:spell-ability` Choice, Warlike Familiar left as is (unreachable), Magic Connoisseur's spell LIST not yet following Magic Initiate's variant (disclosed gap), sameAsFeat resolves to None if Magic Initiate absent (prerequisites off).

## Frontend: no code change (BackgroundPage/ClassPage/StepNav already render/count feat choices). Check `cd frontend && npm run build`, and in the browser on Acolyte/XPHB the "Magic Initiate: Spellcasting Ability" card has three options.
