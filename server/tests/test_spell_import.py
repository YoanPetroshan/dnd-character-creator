"""Slice 11a: sourcebook spells (5etools spells/*.json -> SRD spell shape).

Every number asserted against real data was computed by script from
/Users/yoanpetrov/Documents/5etools-src/data/spells (2026-10-09); tests that
need the files skip when they are absent (no `DND_5ETOOLS_DATA`, nothing
synced into official_dir()/spells)."""
import json

import pytest

from catalog.official import paths, spells as spells_mod
from catalog.official_source import has_official_spells

needs_spells = pytest.mark.skipif(not has_official_spells(), reason="5etools spell files not available")

# Verified totals (script over index.json, 17 book files).
RAW_TOTAL = 936
RAW_BY_SOURCE = {
    "XPHB": 391, "PHB": 361, "XGE": 95, "TCE": 21, "FRHoF": 19, "EGW": 15, "AI": 7, "FTD": 7,
    "SCC": 5, "BMT": 3, "LLK": 3, "AAG": 2, "IDRotF": 2, "SatO": 2, "AitFR-AVT": 1, "EFA": 1, "GGR": 1,
}


# ---------------------------------------------------------------- 11a.1 data

def _write_spell_dir(root, files=None):
    d = root / "spells"
    d.mkdir(parents=True)
    files = files if files is not None else {"PHB": {"spell": [{"name": "Hex", "source": "PHB"}]}}
    (d / "index.json").write_text(json.dumps({src: f"spells-{src.lower()}.json" for src in files}))
    for src, body in files.items():
        (d / f"spells-{src.lower()}.json").write_text(json.dumps(body))
    (d / "sources.json").write_text(json.dumps({"PHB": {"Hex": {"class": [{"name": "Warlock", "source": "PHB"}]}}}))
    return d


def test_spells_dir_honours_the_env_override(tmp_path, monkeypatch):
    d = _write_spell_dir(tmp_path / "data")
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "data"))
    assert paths.spells_dir() == d
    assert paths.has_official_spells()


def test_spells_dir_falls_back_to_the_official_dir_then_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DND_5ETOOLS_DATA", raising=False)
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.spells_dir() is None
    assert not paths.has_official_spells()
    d = _write_spell_dir(tmp_path / "official")
    assert paths.spells_dir() == d


def test_env_override_pointing_nowhere_falls_through(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "nope"))
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.spells_dir() is None


def test_raw_loader_returns_empty_when_the_directory_is_missing(tmp_path):
    assert spells_mod.load_raw_spells(None) == []
    assert spells_mod.load_raw_spells(tmp_path / "missing") == []
    assert spells_mod.load_spell_class_lookup(tmp_path / "missing") == {}


def test_raw_loader_reads_every_file_in_index_order_and_skips_broken_ones(tmp_path):
    d = _write_spell_dir(tmp_path, {
        "PHB": {"spell": [{"name": "Hex", "source": "PHB"}, {"name": "Fireball", "source": "PHB"}]},
        "XGE": {"spell": [{"name": "Toll the Dead", "source": "XGE"}]},
    })
    (d / "spells-xge.json").write_text("{not json")
    assert [s["name"] for s in spells_mod.load_raw_spells(d)] == ["Hex", "Fireball"]
    assert spells_mod.load_spell_class_lookup(d)["PHB"]["Hex"]["class"][0]["name"] == "Warlock"


@needs_spells
def test_real_spell_files_total_and_per_source_counts():
    raw = spells_mod.load_raw_spells(paths.spells_dir())
    assert len(raw) == RAW_TOTAL
    counts = {}
    for s in raw:
        counts[s["source"]] = counts.get(s["source"], 0) + 1
    assert counts == RAW_BY_SOURCE
    assert not any("_copy" in s for s in raw)


# ------------------------------------------------------- 11a.2 converter / ids

from catalog.loader import load  # noqa: E402
from catalog.official_source import slug  # noqa: E402
from engine.resolve import _spell_filter_options, _spell_options_up_to, _spell_visible, resolve  # noqa: E402

# Verified by script (raw files + bundled SRD list, 2026-10-09).
SRD_TOTAL = 319
NEW_BY_SOURCE = {  # records added on top of the SRD list (42 of the 361 PHB spells are genuinely new)
    "XPHB": 391, "XGE": 95, "PHB": 42, "TCE": 21, "FRHoF": 19, "EGW": 15, "AI": 7, "FTD": 7,
    "SCC": 5, "BMT": 3, "LLK": 3, "AAG": 2, "IDRotF": 2, "SatO": 2, "AitFR-AVT": 1, "EFA": 1, "GGR": 1,
}
CATALOG_TOTAL = 936
VISIBLE = {"mixed": 557, "2014": 525, "2024": 557}  # unfiltered, per draft ruleset
TWIN_PAIRS = 379  # spells printed in both a 2014 book (or the SRD) and a 2024 one
NO_CLASS_DATA = 16  # EGW 15 + GGR Encode Thoughts: absent from sources.json
ALIASES_TOTAL = 49  # 17 SRD renames + 32 bare slugs of 2024-only spells
SRD_ONLY_UNRESOLVED_INNATE = {  # distinct innate spell ids no SRD spell matches (13)
    "armor-of-agathys", "battle-familiar", "beast-sense", "crown-of-madness", "friends", "hex", "ice-knife",
    "ottos-irresistible-dance", "ray-of-sickness", "searing-smite", "tensers-floating-disk", "thunderclap",
    "wall-of-water",
}


@pytest.fixture(scope="module")
def catalog():
    return load()


def _raw(name, source="PHB", **extra):
    base = {
        "name": name, "source": source, "level": 1, "school": "V",
        "time": [{"number": 1, "unit": "action"}],
        "range": {"type": "point", "distance": {"type": "feet", "amount": 60}},
        "components": {"v": True, "s": True}, "duration": [{"type": "instant"}], "entries": ["Boom."],
    }
    base.update(extra)
    return base


# Table-driven: the shapes of time / range / duration / components.
@pytest.mark.parametrize("raw_bits, expected", [
    ({"time": [{"number": 1, "unit": "bonus"}]}, {"casting_time": "1 bonus action"}),
    ({"time": [{"number": 1, "unit": "reaction", "condition": "which you take when hit"}]},
     {"casting_time": "1 reaction", "casting_condition": "which you take when hit"}),
    ({"time": [{"number": 10, "unit": "minute"}]}, {"casting_time": "10 minutes"}),
    ({"time": [{"number": 1, "unit": "hour"}]}, {"casting_time": "1 hour"}),
    ({"range": {"type": "point", "distance": {"type": "self"}}}, {"range": "Self"}),
    ({"range": {"type": "point", "distance": {"type": "touch"}}}, {"range": "Touch"}),
    ({"range": {"type": "point", "distance": {"type": "miles", "amount": 500}}}, {"range": "500 miles"}),
    ({"range": {"type": "point", "distance": {"type": "miles", "amount": 1}}}, {"range": "1 mile"}),
    ({"range": {"type": "cone", "distance": {"type": "feet", "amount": 15}}}, {"range": "Self (15-foot cone)"}),
    ({"range": {"type": "special"}}, {"range": "Special"}),
    ({"duration": [{"type": "timed", "duration": {"type": "hour", "amount": 1}, "concentration": True}]},
     {"duration": "Up to 1 hour", "concentration": True}),
    ({"duration": [{"type": "timed", "duration": {"type": "minute", "amount": 10}}]},
     {"duration": "10 minutes", "concentration": False}),
    ({"duration": [{"type": "permanent", "ends": ["dispel"]}]}, {"duration": "Until dispelled"}),
    ({"duration": [{"type": "special"}]}, {"duration": "Special"}),
    ({"meta": {"ritual": True}}, {"ritual": True}),
    ({"components": {"v": True, "s": True, "m": {"text": "a pearl worth 100 gp", "cost": 10000}}},
     {"components": ["V", "S", "M"], "material": "A pearl worth 100 gp."}),
    ({"components": {"v": True}}, {"components": ["V"]}),
    ({"school": "N", "level": 0}, {"school": {"index": "necromancy", "name": "Necromancy"}, "level": 0}),
])
def test_converter_shapes(raw_bits, expected):
    rec = spells_mod._spell_from_5etools(_raw("Test Spell", **raw_bits), {})
    for key, value in expected.items():
        assert rec[key] == value, key


def test_converter_flattens_entries_and_strips_tags():
    raw = _raw(
        "Tag Spell",
        entries=[
            "Each creature makes a {@dc 15} {@skill Dexterity} save, taking {@damage 8d6} fire damage; see {@spell fireball|phb}.",
            {"type": "entries", "name": "Sub", "entries": ["Inner {@condition prone|XPHB|knocked down}."]},
            {"type": "list", "items": ["one", {"type": "item", "name": "Two", "entry": "second"}]},
            {"type": "table", "caption": "Roll", "colLabels": ["d4", "Result"], "rows": [[{"type": "cell", "roll": {"exact": 1}}, "Hit"]]},
        ],
        entriesHigherLevel=[{"type": "entries", "name": "At Higher Levels", "entries": ["{@scaledamage 8d6|3-9|1d6} more."]}],
    )
    rec = spells_mod._spell_from_5etools(raw, {})
    assert rec["desc"] == [
        "Each creature makes a DC 15 Dexterity save, taking 8d6 fire damage; see fireball.",
        "Sub. Inner knocked down.", "one", "Two. second", "Roll", "d4 | Result", "1 | Hit",
    ]
    assert rec["higher_level"] == ["8d6 more."]
    assert "{@" not in " ".join(rec["desc"] + rec["higher_level"])


def test_converter_ignores_unusable_records():
    assert spells_mod._spell_from_5etools({"name": "x"}, {}) is None
    assert spells_mod._spell_from_5etools(_raw("Copy", _copy={"name": "y"}), {}) is None


def test_converter_classes_union_class_and_class_variant_deduped():
    lookup = {"XGE": {"Toll": {"classVariant": [{"name": "Cleric", "source": "PHB"}, {"name": "Cleric", "source": "XPHB"}, {"name": "Warlock", "source": "PHB"}]}},
              "PHB": {"Both": {"class": [{"name": "Wizard", "source": "PHB"}], "classVariant": [{"name": "Wizard", "source": "PHB"}, {"name": "Artificer", "source": "TCE"}]}}}
    assert [c["index"] for c in spells_mod._spell_from_5etools(_raw("Toll", "XGE"), lookup)["classes"]] == ["cleric", "warlock"]
    assert [c["index"] for c in spells_mod._spell_from_5etools(_raw("Both"), lookup)["classes"]] == ["wizard", "artificer"]
    assert spells_mod._spell_from_5etools(_raw("Nowhere", "EGW"), lookup)["classes"] == []


# The ID rule, on synthetic input (no data needed).
def test_id_rule_srd_alias_collision_and_2024():
    srd = frozenset({"fireball", "floating-disk"})
    idx = lambda name, source, taken=(): spells_mod._spell_index(_raw(name, source), srd, taken)  # noqa: E731
    assert idx("Fireball", "PHB") == "fireball"                    # SRD spell keeps its id
    assert idx("Tenser's Floating Disk", "PHB") == "floating-disk"  # rename -> SRD id
    assert idx("Hex", "PHB") == "hex"                              # new spell: bare slug
    assert idx("Blade of Disaster", "TCE") == "blade-of-disaster"
    assert idx("Blade of Disaster", "SCC", {"blade-of-disaster"}) == "blade-of-disaster-scc"   # collision
    assert idx("Fireball", "XPHB") == "fireball-xphb"              # 2024 books always get the suffix
    assert idx("Blade of Disaster", "FRHoF") == "blade-of-disaster-frhof"
    assert idx("Divine Smite", "XPHB") == "divine-smite-xphb"


def test_aliases_and_twins_on_synthetic_catalog():
    spells = {
        "fireball": {"index": "fireball", "name": "Fireball", "ruleset": "2014"},
        "fireball-xphb": {"index": "fireball-xphb", "name": "Fireball", "ruleset": "2024"},
        "arcane-hand": {"index": "arcane-hand", "name": "Arcane Hand", "ruleset": "2014"},
        "bigbys-hand-xphb": {"index": "bigbys-hand-xphb", "name": "Bigby's Hand", "ruleset": "2024"},
        "divine-smite-xphb": {"index": "divine-smite-xphb", "name": "Divine Smite", "ruleset": "2024"},
    }
    assert spells_mod.link_spell_versions(spells) == {
        "fireball": "fireball-xphb", "fireball-xphb": "fireball",
        "arcane-hand": "bigbys-hand-xphb", "bigbys-hand-xphb": "arcane-hand",
    }
    aliases = spells_mod.build_spell_aliases(spells)
    assert aliases["divine-smite"] == "divine-smite-xphb" and "fireball" not in aliases
    assert aliases["tensers-floating-disk"] == "floating-disk"


@needs_spells
def test_srd_aliases_match_the_srd_name_strings_5etools_prints(catalog):
    raw = spells_mod.load_raw_spells(paths.spells_dir())
    derived = {slug(s["name"]): slug(s["srd"]) for s in raw if s["source"] == "PHB" and isinstance(s.get("srd"), str)}
    assert derived == spells_mod.SRD_SPELL_ALIASES and len(derived) == 17
    srd_ids = {k for k, v in catalog.spells.items() if v["source"] == "SRD"}
    assert set(derived.values()) <= srd_ids


@needs_spells
def test_catalog_totals_and_sources(catalog):
    assert len(catalog.spells) == CATALOG_TOTAL
    counts = {}
    for s in catalog.spells.values():
        counts[s["source"]] = counts.get(s["source"], 0) + 1
    assert counts.pop("SRD") == SRD_TOTAL
    assert counts == NEW_BY_SOURCE
    assert sum(1 for s in catalog.spells.values() if s["ruleset"] == "2024") == 411  # XPHB 391 + FRHoF 19 + EFA 1
    assert len(catalog.spell_aliases) == ALIASES_TOTAL
    assert len(catalog.spell_twins) == 2 * TWIN_PAIRS
    assert sum(1 for s in catalog.spells.values() if not s["classes"]) == NO_CLASS_DATA


@needs_spells
def test_srd_records_keep_their_ids_and_gain_source_and_ruleset(catalog):
    fireball = catalog.spells["fireball"]
    assert (fireball["source"], fireball["ruleset"], fireball["level"]) == ("SRD", "2014", 3)
    assert "fireball-xphb" in catalog.spells and catalog.spells["fireball-xphb"]["ruleset"] == "2024"
    assert catalog.spell_twins["fireball"] == "fireball-xphb"
    assert "magic-missile" in catalog.spells and catalog.spells["magic-missile"]["source"] == "SRD"
    # PHB reprints of SRD spells add nothing but missing classes
    assert {c["index"] for c in fireball["classes"]} >= {"sorcerer", "wizard"}


@needs_spells
def test_hex_is_imported_with_class_school_and_shape(catalog):
    hex_ = catalog.spells["hex"]
    assert [c["index"] for c in hex_["classes"]] == ["warlock"]
    assert hex_["level"] == 1 and hex_["school"] == {"index": "enchantment", "name": "Enchantment"}
    assert (hex_["casting_time"], hex_["range"], hex_["duration"]) == ("1 bonus action", "90 feet", "Up to 1 hour")
    assert hex_["concentration"] is True and hex_["ritual"] is False
    assert hex_["components"] == ["V", "S", "M"] and hex_["material"] == "The petrified eye of a newt."
    assert hex_["source"] == "PHB" and hex_["ruleset"] == "2014"
    assert hex_["higher_level"] and "{@" not in " ".join(hex_["desc"] + hex_["higher_level"])


@needs_spells
def test_find_familiar_ritual_and_fireball_shapes(catalog):
    ff = catalog.spells["find-familiar"]
    assert (ff["ritual"], ff["casting_time"], ff["concentration"]) == (True, "1 hour", False)
    shield = catalog.spells["shield-xphb"]
    assert shield["casting_time"] == "1 reaction" and shield["casting_condition"]
    assert catalog.spells["burning-hands"]["range"] in ("Self (15-foot cone)", "Self")  # SRD record untouched


@needs_spells
def test_new_phb_spells_and_other_books(catalog):
    phb_new = {k for k, v in catalog.spells.items() if v["source"] == "PHB"}
    assert len(phb_new) == 42 and {"hex", "armor-of-agathys", "compelled-duel", "dissonant-whispers"} <= phb_new
    assert catalog.spells["toll-the-dead"]["source"] == "XGE"
    assert [c["index"] for c in catalog.spells["toll-the-dead"]["classes"]] == ["cleric", "warlock", "wizard"]
    assert "divine-smite-xphb" in catalog.spells and "divine-smite" not in catalog.spells
    assert catalog.resolve_spell_id("divine-smite") == "divine-smite-xphb"


@needs_spells
def test_renamed_spells_resolve_through_the_alias_and_are_not_imported_twice(catalog):
    assert "tensers-floating-disk" not in catalog.spells and "ottos-irresistible-dance" not in catalog.spells
    assert catalog.resolve_spell_id("tensers-floating-disk") == "floating-disk"
    assert catalog.resolve_spell_id("ottos-irresistible-dance") == "irresistible-dance"
    assert catalog.resolve_spell_id("not-a-spell") is None


def _innate_spell_ids(catalog):
    ids = set()
    for coll in (catalog.races, catalog.subraces, catalog.feats):
        for rec in coll.values():
            for e in rec.get("innate_spells") or []:
                ids.add(e["spell_id"])
            for v in rec.get("variants") or []:
                ids.update(e["spell_id"] for e in v.get("innate_spells") or [])
    return ids


@needs_spells
def test_unresolved_innate_spell_refs_go_from_13_to_1(catalog):
    ids = _innate_spell_ids(catalog)
    srd_ids = {k for k, v in catalog.spells.items() if v["source"] == "SRD"}
    assert {i for i in ids if i not in srd_ids} == SRD_ONLY_UNRESOLVED_INNATE and len(SRD_ONLY_UNRESOLVED_INNATE) == 13
    assert {i for i in ids if catalog.resolve_spell_id(i) is None} == {"battle-familiar"}  # an Unearthed Arcana spell


@needs_spells
def test_innate_grants_resolve_to_catalog_ids(catalog):
    draft = {
        "name": "T", "sources": ["vgm"],
        "classes": [{"classId": "fighter", "level": 1, "choices": {}}], "background": {"id": "acolyte", "choices": {}},
        "species": {"id": "triton-vgm", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 16, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8}},
    }
    grants = {g["name"]: g for g in resolve(draft, catalog)["sheet"]["innateSpells"]}
    assert grants["Wall of Water"]["spellId"] == "wall-of-water" and grants["Wall of Water"]["level"] == 5


@needs_spells
def test_visible_spell_totals_per_ruleset(catalog):
    for ruleset, total in VISIBLE.items():
        assert sum(1 for s in catalog.spells.values() if _spell_visible(catalog, s, [], ruleset)) == total, ruleset


@needs_spells
def test_ruleset_prefers_one_version_of_a_twin_pair(catalog):
    mixed = lambda sid, **kw: _spell_visible(catalog, catalog.spells[sid], kw.get("sources"), kw.get("ruleset", "mixed"))  # noqa: E731
    assert mixed("fireball") and not mixed("fireball-xphb")                       # mixed: the 2014 record
    assert not mixed("fireball", ruleset="2024") and mixed("fireball-xphb", ruleset="2024")
    assert mixed("fireball", ruleset="2014") and not mixed("fireball-xphb", ruleset="2014")
    assert mixed("divine-smite-xphb") and not mixed("divine-smite-xphb", ruleset="2014")   # 2024-only
    assert mixed("absorb-elements", ruleset="2024")                                        # 2014-only stays usable
    # the other version's book excluded by sources: the visible one is not hidden
    assert not mixed("fireball-xphb", sources=["xphb"])                                   # the SRD twin is always allowed
    assert not mixed("hex-xphb", sources=["xphb", "phb"]) and mixed("hex-xphb", sources=["xphb"])
    assert not mixed("hex", sources=["xge"])                                               # PHB book not enabled


@needs_spells
def test_warlock_spell_options_gain_hex_and_armor_of_agathys(catalog):
    ids = {o["item"]["index"] for o in _spell_options_up_to(catalog, "warlock", 1)}
    assert {"hex", "armor-of-agathys", "hellish-rebuke"} <= ids
    srd_only = {k for k, v in catalog.spells.items() if v["source"] == "SRD"}
    assert not {"hex", "armor-of-agathys"} & srd_only


@needs_spells
def test_wizard_options_have_no_2024_duplicate_of_a_visible_2014_spell(catalog):
    ids = {o["item"]["index"] for o in _spell_options_up_to(catalog, "wizard", 1)}
    dupes = [i for i in ids if i.endswith("-xphb") and i[:-5] in catalog.spells]
    assert dupes == [] and "magic-missile" in ids and "magic-missile-xphb" not in ids
    ids24 = {o["item"]["index"] for o in _spell_options_up_to(catalog, "wizard", 1, ruleset="2024")}
    assert "magic-missile-xphb" in ids24 and "magic-missile" not in ids24


@needs_spells
def test_feat_cantrip_filter_for_wizard_grows_and_stays_cantrips(catalog):
    opts = _spell_filter_options(catalog, {"level": [0], "class": ["wizard"]})
    ids = [o["item"]["index"] for o in opts]
    assert all(catalog.spells[i]["level"] == 0 for i in ids)
    assert len(ids) == 31 and {"toll-the-dead", "mind-sliver", "booming-blade"} <= set(ids)  # 14 SRD + 17 (script-verified)


def _warlock_draft(choices, **extra):
    d = {
        "name": "T", "sources": [], "classes": [{"classId": "warlock", "level": 1, "choices": choices}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 16}},
    }
    d.update(extra)
    return d


def _choice(res, cid):
    return next(c for c in res["choices"] if c["id"] == cid)


@needs_spells
def test_warlock_level_one_choice_offers_hex_and_keeps_picks(catalog):
    res = resolve(_warlock_draft({"class:warlock:spells-known": ["hex", "armor-of-agathys"]}), catalog)
    ch = _choice(res, "class:warlock:spells-known")
    assert {"hex", "armor-of-agathys"} <= {o["id"] for o in ch["options"]}
    assert ch["selected"] == ["hex", "armor-of-agathys"] and ch["status"] == "resolved"


@needs_spells
def test_existing_srd_spell_pick_resolves_unchanged_under_every_ruleset(catalog):
    for ruleset in ("mixed", "2014", "2024"):
        d = {
            "name": "T", "ruleset": ruleset, "sources": [], "background": {"id": "acolyte", "choices": {}},
            "classes": [{"classId": "wizard", "level": 1, "choices": {"class:wizard:spells-known": ["magic-missile"]}}],
            "species": {"id": "human", "choices": {}},
            "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 16, "WIS": 12, "CHA": 8}},
        }
        res = resolve(d, catalog)
        assert _choice(res, "class:wizard:spells-known")["selected"] == ["magic-missile"], ruleset
        assert res["pruned"] == [], ruleset
