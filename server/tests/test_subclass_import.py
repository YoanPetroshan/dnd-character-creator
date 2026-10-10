"""Slice 11b: sourcebook subclasses (5etools class/*.json -> SRD subclass shape).

Every number asserted against real data was computed by script (with the
project's own `catalog.official.common.slug`) over
/Users/yoanpetrov/Documents/5etools-src/data/class on 2026-10-09; tests that
need the files skip when they are absent (no `DND_5ETOOLS_DATA`, nothing
synced into official_dir()/class)."""
import json

import pytest

from catalog.official import paths, subclasses as sub_mod
from catalog.official_source import has_official_classes

needs_classes = pytest.mark.skipif(not has_official_classes(), reason="5etools class files not available")

RAW_SUBCLASSES = 315
RAW_SUBCLASS_FEATURES = 1397
RAW_OPTIONAL_FEATURES = 213


# ---------------------------------------------------------------- 11b.1 data

def _write_class_dir(root, files=None):
    d = root / "class"
    d.mkdir(parents=True)
    files = files if files is not None else {
        "fighter": {"subclass": [{"name": "Battle Master", "shortName": "Battle Master", "source": "PHB"}],
                    "subclassFeature": [{"name": "Combat Superiority"}]},
        "wizard": {"subclass": [{"name": "Evocation"}, {"name": "Abjuration"}], "subclassFeature": []},
    }
    (d / "index.json").write_text(json.dumps({k: f"class-{k}.json" for k in files}))
    for k, body in files.items():
        (d / f"class-{k}.json").write_text(json.dumps(body))
    return d


def test_class_dir_honours_the_env_override(tmp_path, monkeypatch):
    d = _write_class_dir(tmp_path / "data")
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "data"))
    assert paths.class_dir() == d
    assert paths.has_official_classes()


def test_class_dir_falls_back_to_the_official_dir_then_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DND_5ETOOLS_DATA", raising=False)
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.class_dir() is None
    assert not paths.has_official_classes()
    d = _write_class_dir(tmp_path / "official")
    assert paths.class_dir() == d


def test_optionalfeatures_file_override_first_then_official_dir_then_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DND_5ETOOLS_DATA", raising=False)
    monkeypatch.setattr(paths, "official_dir", lambda: tmp_path / "official")
    assert paths.optionalfeatures_file() is None
    (tmp_path / "official").mkdir()
    (tmp_path / "official" / "optionalfeatures.json").write_text('{"optionalfeature": []}')
    assert paths.optionalfeatures_file() == tmp_path / "official" / "optionalfeatures.json"
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "optionalfeatures.json").write_text('{"optionalfeature": []}')
    monkeypatch.setenv("DND_5ETOOLS_DATA", str(tmp_path / "data"))
    assert paths.optionalfeatures_file() == tmp_path / "data" / "optionalfeatures.json"


def test_raw_loader_reads_every_file_in_the_index(tmp_path):
    d = _write_class_dir(tmp_path)
    subs, feats = sub_mod.load_raw_class_data(d)
    assert [s["name"] for s in subs] == ["Battle Master", "Evocation", "Abjuration"]
    assert [f["name"] for f in feats] == ["Combat Superiority"]


def test_raw_loader_returns_empty_when_missing_and_skips_a_broken_file(tmp_path):
    assert sub_mod.load_raw_class_data(None) == ([], [])
    assert sub_mod.load_raw_class_data(tmp_path / "nope") == ([], [])
    d = _write_class_dir(tmp_path / "x")
    (d / "class-wizard.json").write_text("{not json")
    subs, _ = sub_mod.load_raw_class_data(d)
    assert [s["name"] for s in subs] == ["Battle Master"]


def test_raw_optional_feature_loader(tmp_path):
    assert sub_mod.load_raw_optional_features(None) == []
    assert sub_mod.load_raw_optional_features(tmp_path / "nope.json") == []
    p = tmp_path / "of.json"
    p.write_text(json.dumps({"optionalfeature": [{"name": "Riposte"}, "junk"]}))
    assert [o["name"] for o in sub_mod.load_raw_optional_features(p)] == ["Riposte"]
    p.write_text("{bad")
    assert sub_mod.load_raw_optional_features(p) == []


@needs_classes
def test_real_raw_counts():
    subs, feats = sub_mod.load_raw_class_data(paths.class_dir())
    assert len(subs) == RAW_SUBCLASSES
    assert len(feats) == RAW_SUBCLASS_FEATURES


@needs_classes
def test_real_raw_optional_features_count():
    path = paths.optionalfeatures_file()
    assert path is not None
    assert len(sub_mod.load_raw_optional_features(path)) == RAW_OPTIONAL_FEATURES


# ------------------------------------------------- 11b.2 converter and merge

from catalog.loader import Catalog, load  # noqa: E402
from catalog.official_source import slug  # noqa: E402
from engine.resolve import resolve  # noqa: E402

SRD_SUBCLASS_IDS = {"berserker", "lore", "life", "land", "champion", "open-hand", "devotion", "hunter",
                    "thief", "draconic", "fiend", "evocation"}
# Script-verified (project slug, 2026-10-09).
IMPORTED_SUBCLASSES = 164
CATALOG_SUBCLASSES = 176
TWIN_PAIRS = 48
IMPORTED_FEATURES = 1089
IMPORTED_LEVEL_ROWS = 671
TOTAL_LEVEL_ROWS = 961
SRD_LEVEL_ROWS = 290


@pytest.fixture(scope="module")
def catalog():
    return load()


def _sub(name="Alpha", short=None, source="XGE", cls="Warlock", features=None, **extra):
    raw = {"name": name, "shortName": short or name, "source": source, "className": cls, "classSource": "PHB",
           "edition": "classic", "subclassFeatures": features if features is not None else []}
    raw.update(extra)
    return raw


def _feat(name, level, short="Alpha", source="XGE", cls="Warlock", entries=None, **extra):
    raw = {"name": name, "source": source, "className": cls, "classSource": "PHB",
           "subclassShortName": short, "subclassSource": source, "level": level, "entries": entries or [f"{name} text."]}
    raw.update(extra)
    return raw


def _convert(subs, feats, srd=frozenset()):
    return sub_mod.convert_subclasses(subs, feats, set(srd), lambda s: None)


def test_converter_record_shape_ids_and_rulesets():
    subs = [_sub("The Alpha", "Alpha", features=["Gift|Warlock||Alpha|XGE|1"]),
            _sub("Wild Heart", "Wild Heart", source="XPHB", cls="Barbarian", classSource="XPHB", edition="one"),
            _sub("Fort (Banneret)", "Purple Dragon Knight (Banneret)", source="SCAG", cls="Fighter")]
    subs[1]["classSource"] = "XPHB"
    out_subs, out_feats, rows = _convert(subs, [_feat("Gift", 1)])
    rec = out_subs["alpha-xge"]
    assert rec["name"] == "The Alpha" and rec["short_name"] == "Alpha" and rec["source"] == "XGE"
    assert rec["class"] == {"index": "warlock", "name": "Warlock"} and rec["ruleset"] == "2014"
    assert out_subs["wild-heart-xphb"]["ruleset"] == "2024"
    assert "purple-dragon-knight-scag" in out_subs
    feat = out_feats["alpha-xge-1-gift"]
    assert feat["class"] == {"index": "warlock", "name": "Warlock"}
    assert feat["subclass"] == {"index": "alpha-xge", "name": "The Alpha"} and feat["level"] == 1
    assert rows[0]["index"] == "alpha-xge-1" and rows[0]["features"] == [{"index": "alpha-xge-1-gift", "name": "Gift"}]


def test_converter_filters():
    subs = [
        _sub("Copy", _copy={"name": "X"}),
        _sub("Srd one", "Srd one", srd=True),
        _sub("Mystic path", cls="Mystic"),
        _sub("Other book", classSource="UA2020"),
        _sub("Keep"),
    ]
    out, _, _ = _convert(subs, [])
    assert list(out) == ["keep-xge"]


def test_converter_expands_child_refs_in_document_order_and_inlines_options():
    top = _feat("Intro", 1, entries=[
        "Intro text.",
        {"type": "refSubclassFeature", "subclassFeature": "Child A|Warlock||Alpha|XGE|1"},
        {"type": "refSubclassFeature", "subclassFeature": "Child B|Warlock||Alpha|XGE|1"},
    ])
    child_a = _feat("Child A", 1, entries=["A text."])
    child_b = _feat("Child B", 1, entries=[
        "B text.",
        {"type": "options", "count": 1, "entries": [
            {"type": "refSubclassFeature", "subclassFeature": "Opt X|Warlock||Alpha|XGE|1"},
            {"type": "refOptionalfeature", "optionalfeature": "Riposte|XGE"},
        ]},
    ])
    opt_x = _feat("Opt X", 1, entries=["X text."])
    _, feats, rows = _convert([_sub("Alpha", features=["Intro|Warlock||Alpha|XGE|1"])], [top, child_a, child_b, opt_x])
    assert [f["index"] for f in feats.values()] == ["alpha-xge-1-intro", "alpha-xge-1-child-a", "alpha-xge-1-child-b"]
    assert [f["index"] for f in rows[0]["features"]] == list(feats)
    assert feats["alpha-xge-1-child-b"]["desc"] == ["B text.", "Opt X. X text.", "Riposte"]
    assert feats["alpha-xge-1-intro"]["desc"] == ["Intro text."]


def test_converter_blank_sources_mean_phb_and_missing_feature_is_skipped():
    subs = [_sub("Beta", "Beta", source="PHB", features=["Real|Warlock||Beta||3", "Ghost|Warlock||Beta||3"])]
    feats = [_feat("Real", 3, short="Beta", source="PHB")]
    _, out_feats, rows = _convert(subs, feats)
    assert list(out_feats) == ["beta-phb-3-real"] and len(rows) == 1


def test_converter_twins_are_symmetric_and_use_the_srd_id_for_srd_records():
    subs = [
        _sub("Fiend", "Fiend", source="PHB", srd=True, reprintedAs=["Fiend|Warlock|XPHB|XPHB"]),
        _sub("Fiend", "Fiend", source="XPHB", classSource="XPHB", edition="one"),
        _sub("Totem", "Totem Warrior", source="PHB", cls="Barbarian", reprintedAs=["Wild Heart|Barbarian|XPHB|XPHB"]),
        _sub("Wild Heart", "Wild Heart", source="XPHB", cls="Barbarian", classSource="XPHB", edition="one"),
    ]
    subs[1]["className"] = "Warlock"
    twins = sub_mod.subclass_twins_from(subs, {"fiend"} | {"totem-warrior-phb", "wild-heart-xphb", "fiend-xphb"})
    assert twins == {"fiend": "fiend-xphb", "fiend-xphb": "fiend",
                     "totem-warrior-phb": "wild-heart-xphb", "wild-heart-xphb": "totem-warrior-phb"}


def test_a_catalog_built_by_hand_still_finds_level_rows():
    cat = Catalog(levels=[
        {"index": "w-1", "level": 1, "class": {"index": "wizard"}},
        {"index": "e-3", "level": 3, "class": {"index": "wizard"}, "subclass": {"index": "evo"}},
    ])
    assert cat.class_level_row("wizard", 1)["index"] == "w-1"
    assert cat.class_level_row("wizard", 3) is None
    assert cat.subclass_level_row("evo", 3)["index"] == "e-3"
    cat.levels.append({"index": "w-2", "level": 2, "class": {"index": "wizard"}})  # grows after first use
    assert cat.class_level_row("wizard", 2)["index"] == "w-2"


@needs_classes
def test_real_import_totals(catalog):
    assert len(catalog.subclasses) == CATALOG_SUBCLASSES
    imported = [s for s in catalog.subclasses.values() if s.get("source") != "SRD"]
    assert len(imported) == IMPORTED_SUBCLASSES
    assert SRD_SUBCLASS_IDS <= set(catalog.subclasses)
    assert len(catalog.levels) == TOTAL_LEVEL_ROWS
    imported_features = [f for f in catalog.features.values() if f.get("subclass", {}).get("index") not in (None, *SRD_SUBCLASS_IDS)]
    assert len(imported_features) == IMPORTED_FEATURES
    assert sum(1 for r in catalog.levels if r.get("subclass", {}).get("index") not in SRD_SUBCLASS_IDS
               and "subclass" in r) == IMPORTED_LEVEL_ROWS


@needs_classes
def test_real_subclass_records(catalog):
    hb = catalog.subclasses["hexblade-xge"]
    assert hb["class"]["index"] == "warlock" and hb["ruleset"] == "2014" and hb["source"] == "XGE"
    assert hb["name"] == "The Hexblade"
    assert catalog.subclasses["berserker-xphb"]["ruleset"] == "2024"
    assert all(s["ruleset"] == "2014" and s["source"] == "SRD" for i, s in catalog.subclasses.items() if i in SRD_SUBCLASS_IDS)
    assert not any("artificer" in i or "mystic" in i for i in catalog.subclasses)
    assert {s["class"]["index"] for s in catalog.subclasses.values()} == {
        "barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"}


@needs_classes
def test_real_twins(catalog):
    t = catalog.subclass_twins
    assert len(t) == 2 * TWIN_PAIRS
    assert t["berserker-xphb"] == "berserker" and t["berserker"] == "berserker-xphb"
    assert t["totem-warrior-phb"] == "wild-heart-xphb" and t["wild-heart-xphb"] == "totem-warrior-phb"
    assert all(t[t[a]] == a for a in t)


@needs_classes
def test_real_hexblade_level_one_features_in_document_order(catalog):
    row = catalog.subclass_level_row("hexblade-xge", 1)
    assert [f["index"] for f in row["features"]] == [
        "hexblade-xge-1-the-hexblade", "hexblade-xge-1-hexblades-curse", "hexblade-xge-1-hex-warrior"]
    assert catalog.subclass_level_row("hexblade-xge", 6)["features"][0]["name"] == "Accursed Specter"


@needs_classes
def test_real_totem_spirit_text_and_no_dangling_references(catalog):
    assert "Bear" in " ".join(catalog.features["totem-warrior-phb-3-totem-spirit"]["desc"])
    for row in catalog.levels:
        for ref in row.get("features", []):
            assert ref["index"] in catalog.features, ref
    ids = [f["index"] for f in catalog.features.values()]
    assert len(ids) == len(set(ids))


@needs_classes
def test_srd_rows_are_untouched(catalog):
    assert catalog.subclasses["fiend"]["name"] == "Fiend"
    assert catalog.subclass_level_row("fiend", 1)["features"][0]["index"] == "dark-ones-blessing"
    assert sum(1 for r in catalog.levels if r.get("url", "").startswith("/api/2014")) == SRD_LEVEL_ROWS


def _draft(cls, level, sub, choices=None):
    return {
        "name": "T", "sources": [], "classes": [{"classId": cls, "level": level, "subclassId": sub, "choices": choices or {}}],
        "background": {"id": "acolyte", "choices": {}}, "species": {"id": "human", "choices": {}},
        "abilities": {"method": "manual", "base": {"STR": 10, "DEX": 14, "CON": 14, "INT": 10, "WIS": 12, "CHA": 16}},
    }


@needs_classes
def test_warlock_with_hexblade_resolves_clean_and_lists_its_features(catalog):
    res = resolve(_draft("warlock", 1, "hexblade-xge"), catalog)
    assert not [p for p in res["problems"] if p["id"] in ("unknown-subclass", "subclass-mismatch")]
    feats = {f["name"]: f for f in res["sheet"]["features"]}
    assert "Hexblade's Curse" in feats and "Hex Warrior" in feats
    assert feats["Hex Warrior"]["source"]["kind"] == "subclass"
    assert not resolve(_draft("warlock", 3, "hexblade-xge"), catalog)["problems"]


@needs_classes
def test_subclass_of_another_class_is_still_a_mismatch(catalog):
    res = resolve(_draft("fighter", 3, "hexblade-xge"), catalog)
    assert any(p["id"] == "subclass-mismatch" for p in res["problems"])


_SRD_SUB_FOR_CLASS = {
    "warlock": "fiend", "barbarian": "berserker", "bard": "lore", "cleric": "life", "druid": "land",
    "fighter": "champion", "monk": "open-hand", "paladin": "devotion", "ranger": "hunter",
    "rogue": "thief", "sorcerer": "draconic", "wizard": "evocation",
}


def _srd_only(catalog):
    """The same catalog with every imported subclass, feature and level row removed."""
    import dataclasses
    keep = lambda sid: sid in SRD_SUBCLASS_IDS  # noqa: E731
    return dataclasses.replace(
        catalog,
        subclasses={i: s for i, s in catalog.subclasses.items() if keep(i)},
        features={i: f for i, f in catalog.features.items() if not f.get("subclass") or keep(f["subclass"]["index"])},
        levels=[r for r in catalog.levels if "subclass" not in r or keep(r["subclass"]["index"])],
        subclass_twins={}, _row_index=None,
    )


@needs_classes
def test_existing_srd_drafts_resolve_byte_for_byte_the_same_as_without_the_import(catalog):
    srd = _srd_only(catalog)
    assert len(srd.levels) == SRD_LEVEL_ROWS and len(srd.subclasses) == 12
    for cls, sub in _SRD_SUB_FOR_CLASS.items():
        for lvl in (1, 3, 9, 20):
            draft = _draft(cls, lvl, sub)
            a = json.dumps(resolve(draft, catalog), sort_keys=True, default=str)
            b = json.dumps(resolve(draft, srd), sort_keys=True, default=str)
            assert a == b, (cls, lvl)


@needs_classes
def test_resolve_stays_as_fast_as_with_the_srd_only_catalog(catalog):
    import time
    srd = _srd_only(catalog)

    def best(cat, sub):
        draft = _draft("fighter", 20, sub)
        resolve(draft, cat)
        t = []
        for _ in range(4):
            start = time.perf_counter()
            for _ in range(50):
                resolve(draft, cat)
            t.append(time.perf_counter() - start)
        return min(t)

    # Measured 2026-10-09: 0.157 s for 50 resolves before the import (linear row scans), the dict index must not be slower.
    assert best(catalog, "battle-master-phb") <= best(srd, "champion") * 1.10 + 0.05


# ------------------------------------------------------ 11b.4 subclass spells

# Script-verified over the raw files: 109 additionalSpells records among the
# in-scope subclasses (6 SRD or multi-block ones skipped), string refs
# prepared 527 + expanded 114 + known 95 = 736, all of which resolve; the 98
# single-block imported subclasses (81 of them with string lists) emit 661 entries (no spell is
# listed twice in one subclass).
STRING_REFS = {"prepared": 527, "expanded": 114, "known": 95}
SPELL_ENTRIES = 661
SUBCLASSES_WITH_SPELLS = 81  # of the 98 single-block ones; the rest hold only innate or object-valued lists
MULTI_BLOCK = {"giant-bgg", "land-xphb", "arcane-archer-xge", "divine-soul-xge", "genie-tce"}


def _raw_spell_sub(extra, short="Alpha", source="XGE", edition="classic", cls="Warlock"):
    return {"name": short, "shortName": short, "source": source, "className": cls, "classSource": "PHB",
            "edition": edition, "subclassFeatures": [], "additionalSpells": extra}


def test_converter_spell_entries_modes_levels_and_cleaning():
    known = {"shield": "shield", "toll the dead": "toll-the-dead"}
    raw = _raw_spell_sub([{
        "expanded": {"s1": ["shield|phb", "toll the dead|xge"], "s3": ["blink"]},
        "prepared": {"3": ["guidance#c", {"choose": "level=1"}]},
        "known": {"1": ["unknown spell"], "5": {"_": ["shield"]}},
        "innate": {"1": ["shield"]},
    }])
    subs, _, _ = sub_mod.convert_subclasses([raw], [], set(), lambda s: s if s in ("shield", "toll-the-dead", "blink", "guidance") else None)
    entries = subs["alpha-xge"]["spells"]
    assert [(e["spell"]["index"], e["mode"], e["prerequisites"][0]["index"]) for e in entries] == [
        ("guidance", "always", "warlock-3"),     # prepared first, class level key
        ("shield", "expanded", "warlock-1"),     # sN -> warlock level 2N-1
        ("toll-the-dead", "expanded", "warlock-1"),
        ("blink", "expanded", "warlock-5"),
    ]
    assert all(e["prerequisites"][0]["type"] == "level" for e in entries)
    assert sub_mod.unresolved_spell_refs([raw], lambda s: s if s in ("shield", "toll-the-dead", "blink", "guidance") else None) == ["unknown spell"]


def test_converter_2024_subclass_prefers_the_xphb_spell_id():
    raw = _raw_spell_sub([{"prepared": {"3": ["fireball", "shield"]}}], source="XPHB", edition="one")
    ids = {"fireball-xphb", "fireball", "shield"}
    subs, _, _ = sub_mod.convert_subclasses([raw], [], set(), lambda s: s if s in ids else None)
    assert [e["spell"]["index"] for e in subs["alpha-xphb"]["spells"]] == ["fireball-xphb", "shield"]
    raw14 = _raw_spell_sub([{"prepared": {"3": ["fireball"]}}])
    subs, _, _ = sub_mod.convert_subclasses([raw14], [], set(), lambda s: s if s in ids else None)
    assert [e["spell"]["index"] for e in subs["alpha-xge"]["spells"]] == ["fireball"]


def test_converter_skips_subclasses_with_several_named_blocks():
    raw = _raw_spell_sub([{"name": "Fire", "prepared": {"3": ["shield"]}}, {"name": "Ice", "prepared": {"3": ["blink"]}}])
    subs, _, _ = sub_mod.convert_subclasses([raw], [], set(), lambda s: s)
    assert subs["alpha-xge"]["spells"] == []


@needs_classes
def test_real_spell_refs_all_resolve_and_counts_match(catalog):
    raw_subs, _ = sub_mod.load_raw_class_data(paths.class_dir())
    in_scope = [s for s in raw_subs if sub_mod._in_scope(s) and not s.get("srd")]
    counts = {"prepared": 0, "expanded": 0, "known": 0}
    for s in in_scope:
        for block in s.get("additionalSpells") or []:
            for mode in counts:
                for lv in (block.get(mode) or {}).values():
                    counts[mode] += sum(isinstance(x, str) for x in lv) if isinstance(lv, list) else 0
    assert counts == STRING_REFS
    assert sub_mod.unresolved_spell_refs(in_scope, catalog.resolve_spell_id) == []
    withspells = {i: s for i, s in catalog.subclasses.items() if s["source"] != "SRD" and s["spells"]}
    assert len(withspells) == SUBCLASSES_WITH_SPELLS
    assert sum(len(s["spells"]) for s in withspells.values()) == SPELL_ENTRIES
    assert not MULTI_BLOCK & set(withspells)
    assert all(e["spell"]["index"] in catalog.spells for s in withspells.values() for e in s["spells"])


def _pairs(catalog, sub_id):
    return [(e["spell"]["index"], e["mode"], e["prerequisites"][0]["index"]) for e in catalog.subclasses[sub_id]["spells"]]


@needs_classes
def test_real_hexblade_expanded_list(catalog):
    assert _pairs(catalog, "hexblade-xge") == [
        ("shield", "expanded", "warlock-1"), ("wrathful-smite", "expanded", "warlock-1"),
        ("blur", "expanded", "warlock-3"), ("branding-smite", "expanded", "warlock-3"),
        ("blink", "expanded", "warlock-5"), ("elemental-weapon", "expanded", "warlock-5"),
        ("phantasmal-killer", "expanded", "warlock-7"), ("staggering-smite", "expanded", "warlock-7"),
        ("banishing-smite", "expanded", "warlock-9"), ("cone-of-cold", "expanded", "warlock-9"),
    ]


def _spell_choice(res, cid):
    return next(c for c in res["choices"] if c["id"] == cid)


@needs_classes
def test_warlock_hexblade_offers_expanded_spells_that_fiend_does_not(catalog):
    hex_opts = {o["id"] for o in _spell_choice(resolve(_draft("warlock", 1, "hexblade-xge"), catalog), "class:warlock:spells-known")["options"]}
    fiend_opts = {o["id"] for o in _spell_choice(resolve(_draft("warlock", 1, "fiend"), catalog), "class:warlock:spells-known")["options"]}
    assert {"shield", "wrathful-smite"} <= hex_opts
    assert not {"shield", "wrathful-smite"} <= fiend_opts


@needs_classes
def test_cleric_light_domain_always_prepared_grows_with_level(catalog):
    def always(level):
        sheet = resolve(_draft("cleric", level, "light-phb"), catalog)["sheet"]
        return {sp["id"] for entry in sheet["spells"] for sp in entry.get("alwaysPrepared", [])}
    one = always(1)
    assert {"burning-hands", "faerie-fire"} <= one and "flaming-sphere" not in one
    three = always(3)
    assert {"burning-hands", "faerie-fire", "flaming-sphere", "scorching-ray"} <= three


@needs_classes
def test_a_2024_subclass_resolves_spells_to_xphb_ids_when_they_exist(catalog):
    ids = [i for i, _, _ in _pairs(catalog, "light-xphb")]
    assert ids
    for spell_id in ids:
        base = spell_id[:-5] if spell_id.endswith("-xphb") else spell_id
        if base + "-xphb" in catalog.spells:
            assert spell_id.endswith("-xphb"), spell_id


# --------------------------------------------------- 11b.5 fixed proficiencies

from catalog import reference_data  # noqa: E402

# Fixed grants read from the imported feature text (checked by script on
# 2026-10-09): every imported feature that says "you gain proficiency with ...".
EXPECTED_GRANTS = {
    "valor-phb": {"medium-armor", "shields", "martial-weapons"},
    "valor-xphb": {"medium-armor", "shields", "martial-weapons"},
    "swords-xge": {"medium-armor", "scimitars"},
    "death-dmg": {"martial-weapons"},
    "nature-phb": {"heavy-armor"},
    "tempest-phb": {"martial-weapons", "heavy-armor"},
    "war-phb": {"martial-weapons", "heavy-armor"},
    "solidarity-psa": {"heavy-armor"},
    "strength-psa": {"heavy-armor"},
    "zeal-psa": {"martial-weapons", "heavy-armor"},
    "order-tce": {"heavy-armor"},
    "twilight-tce": {"martial-weapons", "heavy-armor"},
    "forge-xge": {"heavy-armor", "smiths-tools"},
    "rune-knight-tce": {"smiths-tools"},
    "assassin-phb": {"disguise-kit", "poisoners-kit"},
    "assassin-xphb": {"disguise-kit", "poisoners-kit"},
    "hexblade-xge": {"medium-armor", "shields", "martial-weapons"},
    "bladesinging-tce": {"light-armor"},
    "life": {"heavy-armor"},
}


def test_subclass_proficiency_table_matches_the_verified_grants():
    assert {k: set(v) for k, v in reference_data.SUBCLASS_PROFICIENCIES.items()} == EXPECTED_GRANTS


@needs_classes
def test_every_granting_subclass_exists_in_the_catalog(catalog):
    assert set(EXPECTED_GRANTS) <= set(catalog.subclasses)


def _attack(res, item_id):
    return next(a for a in res["derived"]["attacks"] if a["itemId"] == item_id)


def _with_gear(draft, *items):
    draft["equipment"] = {"choices": {}, "skipped": False,
                          "added": [{"itemId": i, "qty": 1, "equipped": True} for i in items]}
    return draft


@needs_classes
def test_hexblade_warlock_is_proficient_with_a_longsword(catalog):
    hexblade = resolve(_with_gear(_draft("warlock", 1, "hexblade-xge"), "longsword"), catalog)
    assert _attack(hexblade, "longsword")["proficient"] is True
    fiend = resolve(_with_gear(_draft("warlock", 1, "fiend"), "longsword"), catalog)
    assert _attack(fiend, "longsword")["proficient"] is False
    assert {"medium-armor", "shields", "martial-weapons"} <= set(hexblade["sheet"]["proficiencies"]["armor"]) | set(hexblade["sheet"]["proficiencies"]["weapons"])


@needs_classes
def test_tempest_cleric_wears_chain_mail_without_a_warning(catalog):
    def warnings(sub):
        res = resolve(_with_gear(_draft("cleric", 1, sub), "chain-mail"), catalog)
        return [w["id"] for w in res["warnings"]]
    assert "armor-not-proficient-chain-mail" in warnings("light-phb")
    assert "armor-not-proficient-chain-mail" not in warnings("tempest-phb")


@needs_classes
def test_swords_bard_is_proficient_with_the_scimitar_and_forge_cleric_with_smiths_tools(catalog):
    res = resolve(_with_gear(_draft("bard", 3, "swords-xge"), "scimitar"), catalog)
    assert _attack(res, "scimitar")["proficient"] is True
    forge = resolve(_draft("cleric", 1, "forge-xge"), catalog)
    assert "smiths-tools" in forge["sheet"]["proficiencies"]["tools"]


# ------------------------------------- 11b.6 optionalfeatureProgression picks

# Script-verified over optionalfeatures.json + the class files: the 5
# featureTypes used by non-SRD subclasses (MV:B, FS:B, AS, RN, ED) cover 76
# records; 11 carry a level prerequisite (Rune Knight 2 at 7, Four Elements 9
# at 6/11/17).
OPTION_RECORDS = 76
OPTIONS_BY_TYPE = {"MV:B": 43, "FS:B": 2, "AS": 8, "RN": 6, "ED": 17}
BM_PHB_FEATURE = "battle-master-phb-3-battle-master"


def _opt_raw(name, source="PHB", types=("MV:B",), prereq_level=None):
    raw = {"name": name, "source": source, "featureType": list(types), "entries": [f"{name} text."]}
    if prereq_level:
        raw["prerequisite"] = [{"level": {"level": prereq_level, "class": {"name": "Monk"}}}]
    return raw


def test_converter_option_records_pools_and_attachment():
    subs = [
        _sub("Master", "Master", source="PHB", cls="Fighter", features=["Core|Fighter||Master||3"],
             optionalfeatureProgression=[{"name": "Maneuvers", "featureType": ["MV:B"], "progression": {"3": 3, "7": 5}}]),
        _sub("Master", "Master", source="XPHB", cls="Fighter", edition="one", features=["Core|Fighter|XPHB|Master|XPHB|3"],
             optionalfeatureProgression=[{"name": "Maneuvers", "featureType": ["MV:B"], "progression": {"3": 3}}]),
    ]
    subs[1]["classSource"] = "XPHB"
    feats = [_feat("Core", 3, short="Master", source="PHB", cls="Fighter"),
             {**_feat("Core", 3, short="Master", source="XPHB", cls="Fighter"), "classSource": "XPHB"}]
    opts = [_opt_raw("Riposte"), _opt_raw("Ambush", "TCE"), _opt_raw("Riposte", "XPHB"), _opt_raw("Other", "PHB", ("ED",), 6)]
    _, out_feats, _ = sub_mod.convert_subclasses(subs, feats, set(), lambda s: None, opts)
    assert out_feats["opt-riposte-phb"] == {
        "index": "opt-riposte-phb", "name": "Riposte", "desc": ["Riposte text."], "source": "PHB", "ruleset": "2014",
        "prerequisite_level": None}
    assert out_feats["opt-other-phb"]["prerequisite_level"] == 6
    old = out_feats["master-phb-3-core"]["feature_specific"]["optional_progression"]
    assert old == {"progression": {"3": 3, "7": 5}, "options": ["opt-riposte-phb", "opt-ambush-tce"]}
    new = out_feats["master-xphb-3-core"]["feature_specific"]["optional_progression"]
    assert new["options"] == ["opt-riposte-xphb"]


@needs_classes
def test_real_option_records(catalog):
    # the C6c-1 XPHB Invocation / Metamagic records (no prerequisite_level key) are a separate family
    opts = {i: f for i, f in catalog.features.items() if i.startswith("opt-") and "prerequisite_level" in f}
    assert len(opts) == OPTION_RECORDS
    assert sum(1 for f in opts.values() if f["prerequisite_level"]) == 11
    attached = {i: f["feature_specific"]["optional_progression"] for i, f in catalog.features.items()
                if f.get("feature_specific", {}).get("optional_progression")}
    assert set(attached) == {
        "battle-master-phb-3-battle-master", "battle-master-xphb-3-battle-master", "arcane-archer-xge-3-arcane-archer",
        "rune-knight-tce-3-rune-knight", "four-elements-phb-3-way-of-the-four-elements", "swords-xge-3-college-of-swords"}
    assert len(attached) == 6
    sizes = sorted(len(a["options"]) for a in attached.values())
    assert sizes == sorted([23, 20, 8, 6, 17, 2])
    assert all(o in opts for a in attached.values() for o in a["options"])
    assert attached[BM_PHB_FEATURE]["progression"] == {"3": 3, "7": 5, "10": 7, "15": 9}


def _bm(level, sub="battle-master-phb", picks=()):
    cid = f"class:fighter:3:feature:{sub}-3-battle-master"
    return _draft("fighter", level, sub, {cid: list(picks)} if picks else {}), cid


@needs_classes
def test_battle_master_counts_and_option_pools(catalog):
    draft, cid = _bm(3)
    ch = _spell_choice(resolve(draft, catalog), cid)
    assert ch["count"] == 3 and len(ch["options"]) == 23 and not any(o.get("disabled") for o in ch["options"])
    assert ch["label"] == "Battle Master" and ch["status"] == "pending"
    assert _spell_choice(resolve(_bm(7)[0], catalog), cid)["count"] == 5
    assert _spell_choice(resolve(_bm(20)[0], catalog), cid)["count"] == 9
    draft, cid24 = _bm(3, "battle-master-xphb")
    assert len(_spell_choice(resolve(draft, catalog), cid24)["options"]) == 20


@needs_classes
def test_battle_master_picks_reach_the_sheet_and_level_down_prunes(catalog):
    maneuvers = [o["id"] for o in _spell_choice(resolve(_bm(3)[0], catalog), _bm(3)[1])["options"]]
    draft, cid = _bm(7, picks=maneuvers[:5])
    res = resolve(draft, catalog)
    ch = _spell_choice(res, cid)
    assert ch["status"] == "resolved" and len(ch["selected"]) == 5
    feature = next(f for f in res["sheet"]["features"] if f["name"] == "Battle Master")
    assert len(feature["choice"]) == 5
    assert next(f for f in res["sheet"]["features"] if f["name"] == "Combat Superiority")["source"]["kind"] == "subclass"
    draft, cid = _bm(3, picks=maneuvers[:5])
    res = resolve(draft, catalog)
    assert len(_spell_choice(res, cid)["selected"]) == 3
    assert any(p["choiceId"] == cid for p in res["pruned"])
    assert not [p for p in res["problems"] if cid in p["message"] or p["id"].startswith("over-selected")]


@needs_classes
def test_rune_knight_and_four_elements_disable_options_above_the_class_level(catalog):
    cid = "class:fighter:3:feature:rune-knight-tce-3-rune-knight"
    runes = _spell_choice(resolve(_draft("fighter", 3, "rune-knight-tce"), catalog), cid)
    assert len(runes["options"]) == 6 and sum(1 for o in runes["options"] if o.get("disabled")) == 2
    assert all(o["disabledReason"] for o in runes["options"] if o.get("disabled"))
    assert runes["count"] == 2
    seven = _spell_choice(resolve(_draft("fighter", 7, "rune-knight-tce"), catalog), cid)
    assert not any(o.get("disabled") for o in seven["options"]) and seven["count"] == 3
    cid = "class:monk:3:feature:four-elements-phb-3-way-of-the-four-elements"
    disc = _spell_choice(resolve(_draft("monk", 3, "four-elements-phb"), catalog), cid)
    # S3: Elemental Attunement is granted, so 16 options and 1 pick at level 3
    assert len(disc["options"]) == 16 and sum(1 for o in disc["options"] if o.get("disabled")) == 9 and disc["count"] == 1


@needs_classes
def test_arcane_archer_counts(catalog):
    cid = "class:fighter:3:feature:arcane-archer-xge-3-arcane-archer"
    assert _spell_choice(resolve(_draft("fighter", 3, "arcane-archer-xge"), catalog), cid)["count"] == 2
    assert len(_spell_choice(resolve(_draft("fighter", 18, "arcane-archer-xge"), catalog), cid)["options"]) == 8
    assert _spell_choice(resolve(_draft("fighter", 18, "arcane-archer-xge"), catalog), cid)["count"] == 6


@needs_classes
def test_swords_bard_dueling_adds_two_to_longsword_damage(catalog):
    cid = "class:bard:3:feature:swords-xge-3-college-of-swords"
    base = resolve(_with_gear(_draft("bard", 3, "swords-xge"), "longsword"), catalog)
    ch = _spell_choice(base, cid)
    assert [o["id"] for o in ch["options"]] == ["opt-dueling-phb", "opt-two-weapon-fighting-phb"] and ch["count"] == 1
    plain = _attack(base, "longsword")
    assert plain["duelingDamage"] is None
    dueling = resolve(_with_gear(_draft("bard", 3, "swords-xge", {cid: ["opt-dueling-phb"]}), "longsword"), catalog)
    bonus = lambda d: int(d.split("+")[1]) if "+" in d else 0  # noqa: E731
    atk = _attack(dueling, "longsword")
    # S5: base damage is unchanged; the +2 is in duelingDamage.
    assert atk["damage"] == plain["damage"]
    assert bonus(atk["duelingDamage"]) == bonus(plain["damage"]) + 2


# ----------------------------------------- B1: third-caster `spellcasting` blocks
# Numbers verified by script over class-fighter.json / class-rogue.json (2026-10-09).

_EK_SLOTS = [[0, 0, 0, 0], [0, 0, 0, 0], [2, 0, 0, 0], [3, 0, 0, 0], [3, 0, 0, 0], [3, 0, 0, 0],
             [4, 2, 0, 0], [4, 2, 0, 0], [4, 2, 0, 0], [4, 3, 0, 0], [4, 3, 0, 0], [4, 3, 0, 0],
             [4, 3, 2, 0], [4, 3, 2, 0], [4, 3, 2, 0], [4, 3, 3, 0], [4, 3, 3, 0], [4, 3, 3, 0],
             [4, 3, 3, 1], [4, 3, 3, 1]]
_THIRD_SPELLS = [0, 0, 3, 4, 4, 4, 5, 6, 6, 7, 8, 8, 9, 10, 10, 11, 11, 11, 12, 13]
_THIRD_CANTRIPS = [0, 0] + [2] * 7 + [3] * 11


@needs_classes
def test_exactly_four_subclasses_carry_a_spellcasting_block(catalog):
    carriers = sorted(i for i, s in catalog.subclasses.items() if "spellcasting" in s)
    assert carriers == ["arcane-trickster-phb", "arcane-trickster-xphb",
                        "eldritch-knight-phb", "eldritch-knight-xphb"]


@needs_classes
def test_third_caster_blocks_match_the_class_tables(catalog):
    for sid in ("eldritch-knight-phb", "eldritch-knight-xphb", "arcane-trickster-phb", "arcane-trickster-xphb"):
        sc = catalog.subclasses[sid]["spellcasting"]
        assert sc["ability"] == "INT" and sc["progression"] == "1/3" and sc["list_class"] == "wizard"
        assert sc["cantrips"] == _THIRD_CANTRIPS
        assert sc["spells"] == _THIRD_SPELLS
        assert sc["slots"] == _EK_SLOTS
    assert catalog.subclasses["eldritch-knight-phb"]["spellcasting"]["slots"][6] == [4, 2, 0, 0]
    assert catalog.subclasses["eldritch-knight-phb"]["spellcasting"]["kind"] == "known"
    assert catalog.subclasses["arcane-trickster-phb"]["spellcasting"]["kind"] == "known"
    assert catalog.subclasses["eldritch-knight-xphb"]["spellcasting"]["kind"] == "prepared"
    assert catalog.subclasses["arcane-trickster-xphb"]["spellcasting"]["kind"] == "prepared"
    assert catalog.subclasses["arcane-trickster-xphb"]["spellcasting"]["cantrips"][9] == 3


def test_converter_list_class_falls_back_to_wizard_and_ignores_other_progressions():
    raw = _sub("Third", source="PHB", cls="Fighter", casterProgression="1/3", spellsKnownProgression=[0, 0, 3],
               cantripProgression=[0, 0, 2],
               subclassTableGroups=[{"rowsSpellProgression": [[0], [0], [2]]}])
    subs, _, _ = _convert([raw], [])
    sc = subs["third-phb"]["spellcasting"]
    assert sc["list_class"] == "wizard" and sc["kind"] == "known" and sc["slots"] == [[0], [0], [2]]
    half = _sub("Half", source="PHB", cls="Fighter", casterProgression="1/2")
    assert "spellcasting" not in _convert([half], [])[0]["half-phb"]


def test_school_limits_table():
    from catalog.reference_data import SUBCLASS_SPELL_SCHOOL_LIMITS as lim
    assert lim["eldritch-knight-phb"] == {"schools": ["abjuration", "evocation"], "free_at": [3, 8, 14, 20]}
    assert lim["arcane-trickster-phb"] == {"schools": ["enchantment", "illusion"], "free_at": [3, 8, 14, 20]}
    assert set(lim) == {"eldritch-knight-phb", "arcane-trickster-phb"}
