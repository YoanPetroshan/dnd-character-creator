"""Converts the wider, multi-sourcebook 5etools-src race/subrace/background
data (fetched by `python3 -m chargen.sync --official` into
chargen.sources.official_dir(), never committed to this repo — see that
module and chargen/sync.py for the fetch/licensing details this module
inherits without re-litigating) into the SAME dict shape
catalog/loader.py already produces for the bundled 2014 SRD data. This is
a from-scratch v2-native normalizer — it does NOT reuse chargen.catalog's
own normalizer (chargen.normalise.race_from_5etools etc.), because that
targets chargen's own frozen dataclasses, a different, incompatible
object model from the raw dicts catalog/choices.py and engine/resolve.py
read throughout. Only chargen.sources' pure path/existence helpers are
shared.

Every record's id is source-qualified (e.g. "aasimar-vgm") using the raw
5etools "source" field lowercased, so a reprint across multiple books
(Aasimar in VGM, then MPMM, then XPHB) produces multiple distinct
records, and nothing here can ever collide with a bundled SRD id (SRD ids
have no source suffix at all).

Subrace ids are additionally scoped by their parent race's own id (e.g.
"aasimar-vgm-fallen-vgm"), not just their own (name, source) — empirically
confirmed against the real fetched data that (name, source) alone is NOT
globally unique for subraces: "Ixalan"/PSX names a subrace of both
Goblin/PSZ and Vampire/PSZ, and "Variant; Mark of Finding"/ERLW names a
subrace of both Half-Orc/PHB and Human/PHB. Scoping by parent race id
resolves both collisions.

_copy/_mod-based records (5etools' own "defined as another record plus a
diff" shorthand) are skipped — real, but a bounded, disclosed cut, same
scope decision v1's own chargen/normalise.py already made for the same
reason (see that module's docstring). Subrace records with no "name"
field are also skipped: empirically these are "SRD-complete" placeholder
markers (e.g. for Human/Half-Elf/Half-Orc/Tiefling/Dragonborn in the PHB)
that carry no selectable content of their own, not real subraces.

chargen lives at the repo root, a SIBLING of server/ — not a subpackage
of it. Every real way this server runs (`cd server && python app.py` in
production, `cd server && pytest` for tests) has `server/` as the
working directory, which does not put the repo root on sys.path. The
insert below is what makes `from chargen.sources import ...` resolve —
this module is the ONLY place in the whole codebase that imports
chargen.sources directly; official_dir/has_official are re-exported
from here (see the import line right below) so every caller (loader.py,
every test) imports them FROM catalog.official_source instead, and
never needs to know chargen lives one level up at all.

Innate spellcasting (Task 6, 2026-09-24): `additionalSpells[].innate`
converts to each race/subrace's new `innate_spells` field — see
_innate_spells_from_5etools' docstring for the full shape/scope
grounding. Resolvability measurement (2026-09-24, re-measured after a
code review caught two bugs in the first pass: a "rest"-wrapper entry
was being silently dropped instead of counted, and the original count
included races/subraces filtered out by the "_copy" check below and so
never actually reached this code): running the REAL shipped pipeline —
load_official_races() followed by resolving each returned innate-spell
reference against catalog.spells, exactly what
engine.resolve._species_innate_spells does — over the real fetched
races.json produces 102 total innate-spell references (races AND
subraces, since subraces carry the field independently too), of which
93/102 (91.2%) resolve cleanly against the bundled 2014 SRD spell
catalog once 5etools' own nested "{level: {"daily"|"rest": {"1":
[...]}}}" shape and "name|source"/"name#N" decorations are correctly
stripped before slugging — most sourcebook races' innate spells
genuinely are 2014-era SRD spells. The remaining 9/102 (8.8%) reference
spells this project has no data for at all (Hex, Tenser's Floating Disk,
Ice Knife, Wall of Water, Crown of Madness, Ray of Sickness x2, Armor of
Agathys, Searing Smite) — a real, disclosed gap (this project has not
imported spell DATA beyond the bundled SRD list, an explicitly
out-of-scope decision predating this task), handled by
engine.resolve._species_innate_spells degrading gracefully: spellId is
null but the spell's name is still shown, never silently dropped.

Slice 11.0 (2026-10-09): the converters now live in the package
catalog/official/ (paths.py - the only importer of chargen.sources, so the
sys.path note above applies THERE now; common.py, equipment.py,
proficiencies.py, languages.py, innate_spells.py, races.py, backgrounds.py,
feats.py), split by concern with no behaviour change. This module is only
the re-export shim: every public AND private name callers and tests import
from `catalog.official_source` is re-exported unchanged.
"""
from __future__ import annotations

from .official.paths import (  # noqa: F401
    _repo_root,
    has_official,
    class_dir,
    has_official_classes,
    has_official_spells,
    items_base_file,
    official_dir,
    optionalfeatures_file,
    spells_dir,
)
from .official.common import (  # noqa: F401
    _ABILITY_KEYS,
    _ability_bonus_options_from_5etools,
    _ability_bonus_options_from_5etools_weighted_pair,
    _ability_bonuses_from_5etools,
    _condition_immunities_from_5etools,
    _damage_modifiers_from_5etools,
    _darkvision_from_5etools,
    _senses_from_5etools,
    _sentence_case,
    _speed_from_5etools,
    _tool_display_name,
    _weighted_asi_envelope,
    slug,
)
from .official.equipment import (  # noqa: F401
    _EQUIPMENT_TYPE_LABELS,
    _SRD_EQUIPMENT,
    _SRD_EQUIPMENT_BY_WORDS,
    _SRD_EQUIPMENT_WORDS,
    _counted_reference_for_item_name,
    _equipment_bundle_member_from_5etools,
    _equipment_name_words,
    _find_srd_equipment_item,
    _fixed_starting_equipment_from_5etools,
    _starting_equipment_options_from_5etools,
)
from .official.proficiencies import (  # noqa: F401
    _TOOL_CHOICE_CATEGORY_PLACEHOLDERS,
    _TOOL_WILDCARD_KEY_CATEGORY,
    _WEAPON_ID_OVERRIDES,
    _attach_choice_proficiencies,
    _attach_fixed_proficiencies,
    _background_tool_choice_envelopes_from_5etools,
    _background_tool_choice_option_from_5etools,
    _category_display_name,
    _pluralize,
    _proficiencies_from_5etools,
    _proficiency_choices_from_5etools,
    _skill_choice_envelope_from_5etools,
    _tool_choice_envelope_from_5etools,
)
from .official.languages import (  # noqa: F401
    _LANGUAGES_BY_INDEX,
    _language_choice_option_from_5etools,
    _language_grants_from_5etools,
    _language_ref_from_key,
)
from .official.innate_spells import (  # noqa: F401
    _SPELL_SCHOOL_CODES,
    _clean_innate_spell_name,
    _innate_spell_ability,
    _innate_spell_uses_and_names,
    _innate_spells_from_5etools,
)
from .official.races import (  # noqa: F401
    _NAMELESS_SKIP_KEYS,
    _merge_nameless_subraces,
    _mod_replaces_entry,
    _race_from_5etools,
    _race_variants_from_5etools,
    _resist_options_from_5etools,
    _species_feat_grants_from_5etools,
    _subrace_from_5etools,
    _trait_refs_from_entries,
    _variant_from_source,
    _variant_slug,
    load_official_races,
)
from .official.backgrounds import (  # noqa: F401
    _background_from_5etools,
    _feats_from_5etools,
    load_official_backgrounds,
)
from .official.feats import (  # noqa: F401
    SAVE_ABILITY_NAMES,
    _FEAT_SPELLS_SKIP,
    _INHERIT_ABILITY_RE,
    _SAME_AS_FEAT_ABILITY_RE,
    _expertise_choices_from_5etools,
    _expertise_skills_from_5etools,
    _feat_ability_bonus_options_from_5etools,
    _feat_from_5etools,
    _feat_spell_ability_override,
    _feat_spell_uses_and_items,
    _feat_spells_from_5etools,
    _feat_variant_hints_from_5etools,
    _parse_spell_filter,
    _saving_throw_choices_from_5etools,
    _saving_throw_proficiencies_from_5etools,
    load_official_feats,
)
from .official.spells import (  # noqa: F401
    SRD_SPELL_ALIASES,
    build_spell_aliases,
    link_spell_versions,
    load_official_spells,
    load_raw_spells,
    load_spell_class_lookup,
)
from .official.items import convert_items, load_raw_base_items  # noqa: F401
from .official.subclasses import (  # noqa: F401
    convert_subclasses,
    subclass_twins_from,
    unresolved_spell_refs,
    load_class_2024_progressions,
    load_raw_class_data,
    load_raw_optional_features,
)
