"""S13 (audit DATA-01, Q1 = B): 5etools `_copy` / `_mod` records are resolved instead of dropped.

16 species, 1 subspecies and 26 backgrounds of the bundled data are reprints written as "copy that record, then modify
it". They used to be skipped (the audit counted them as missing content). `catalog.official.common.resolve_copies` builds
the full record (the parent, the child's own keys over it, then the `_mod` operations replaceArr / appendArr / insertArr
/ replaceTxt); a record it cannot resolve (parent missing, an operation it does not know) stays a `_copy` and is skipped
as before."""
from __future__ import annotations

import copy
import json

import pytest

from catalog.official import paths
from catalog.official.common import resolve_copies

pytestmark_data = pytest.mark.skipif(paths.data_source() != "bundled", reason="uses the bundled 5etools data")


def rec(name, source, **kw):
    return {"name": name, "source": source, **kw}


PARENT = rec("Elf", "XPHB", page=10, srd=True, basicRules=True, hasFluff=True, size=["M"],
             entries=[{"name": "Darkvision", "type": "entries", "entries": ["60 ft."]},
                      {"name": "Keen Senses", "type": "entries", "entries": ["Perception."]},
                      "closing text about elves"])


def child(mod=None, preserve=None, **own):
    c = {"name": "Elf", "source": "XPHB"}
    if mod is not None:
        c["_mod"] = mod
    if preserve is not None:
        c["_preserve"] = preserve
    return rec("Elf", "LFL", _copy=c, **own)


def resolved(c, parent=PARENT):
    return resolve_copies([copy.deepcopy(parent), c])[1]


def test_a_copy_without_mod_is_the_parent_with_the_childs_own_keys_and_without_reprint_metadata():
    out = resolved(child(page=77, size=["S"]))
    assert "_copy" not in out
    assert (out["name"], out["source"]) == ("Elf", "LFL")
    assert out["size"] == ["S"]  # the child's own key wins
    assert out["entries"] == PARENT["entries"]
    assert out["page"] == 77  # the child's own
    assert "srd" not in out and "basicRules" not in out and "hasFluff" not in out  # parent-only metadata is dropped


def test_preserve_keeps_the_named_parent_keys():
    out = resolved(child(preserve={"srd": True, "page": True}))
    assert out["srd"] is True and out["page"] == 10 and "basicRules" not in out


def test_replaceArr_by_name_and_by_index():
    new = {"name": "Darkvision", "type": "entries", "entries": ["120 ft."]}
    by_name = resolved(child({"entries": {"mode": "replaceArr", "replace": "Darkvision", "items": new}}))
    assert by_name["entries"][0] == new and by_name["entries"][1:] == PARENT["entries"][1:]
    by_index = resolved(child({"entries": {"mode": "replaceArr", "replace": {"index": 2}, "items": ["a", "b"]}}))
    assert by_index["entries"][2:] == ["a", "b"]


def test_appendArr_insertArr_and_a_list_of_operations_run_in_order():
    out = resolved(child({"entries": [
        {"mode": "appendArr", "items": "tail"},
        {"mode": "insertArr", "index": 1, "items": [{"name": "Inserted", "type": "entries", "entries": ["x"]}]},
    ]}))
    names = [e["name"] if isinstance(e, dict) else e for e in out["entries"]]
    assert names == ["Darkvision", "Inserted", "Keen Senses", "closing text about elves", "tail"]


def test_replaceTxt_rewrites_every_string_below_the_array():
    out = resolved(child({"entries": {"mode": "replaceTxt", "replace": "60 ft", "with": "90 ft", "flags": "i"}}))
    assert out["entries"][0]["entries"] == ["90 ft."]


def test_a_chain_of_copies_resolves_through_the_middle_record():
    middle = rec("Elf", "LFL", _copy={"name": "Elf", "source": "XPHB", "_mod": {"entries": {"mode": "appendArr", "items": "middle"}}})
    last = rec("Elf", "ZZZ", _copy={"name": "Elf", "source": "LFL", "_mod": {"entries": {"mode": "appendArr", "items": "last"}}})
    out = resolve_copies([last, middle, copy.deepcopy(PARENT)])[0]  # the order in the file does not matter
    assert out["entries"][-2:] == ["middle", "last"]


def test_a_record_with_a_missing_parent_or_an_unknown_operation_stays_a_copy():
    orphan = rec("Ghost", "LFL", _copy={"name": "Nobody", "source": "XPHB"})
    odd = child({"entries": {"mode": "somethingNew", "items": "x"}})
    out = resolve_copies([copy.deepcopy(PARENT), orphan, odd])
    assert "_copy" in out[1] and "_copy" in out[2]


def test_the_input_is_not_modified_and_records_without_copy_are_returned_as_they_are():
    plain = copy.deepcopy(PARENT)
    before = json.dumps([plain, child({"entries": {"mode": "appendArr", "items": "t"}})], sort_keys=True)
    items = json.loads(before)
    resolve_copies(items)
    assert json.dumps(items, sort_keys=True) == before
    assert resolve_copies([plain])[0] == PARENT


def test_a_copy_of_a_nameless_race_target_uses_name_source_and_race_name_for_subraces():
    parent = rec("Variant", "PHB", raceName="Human", raceSource="PHB", entries=["p"])
    c = rec("Amonkhet", "PSA", raceName="Human", raceSource="PHB",
            _copy={"name": "Variant", "source": "PHB", "raceName": "Human", "raceSource": "PHB",
                   "_mod": {"entries": {"mode": "appendArr", "items": "q"}}})
    other = rec("Variant", "PHB", raceName="Elf", raceSource="PHB", entries=["wrong"])
    out = resolve_copies([other, parent, c], match_race=True)[2]
    assert out["entries"] == ["p", "q"]


# ---- the bundled data -------------------------------------------------------------------------------------------------

@pytestmark_data
def test_every_copy_record_of_the_bundled_data_is_in_the_catalog():
    from catalog.loader import load
    from catalog.official.common import slug

    cat = load()
    data = paths.official_dir()
    missing = []
    for fname, key, coll in (("races.json", "race", cat.races), ("backgrounds.json", "background", cat.backgrounds)):
        for r in json.loads((data / fname).read_text(encoding="utf-8")).get(key, []):
            if "_copy" in r and f"{slug(r['name'])}-{r['source'].lower()}" not in coll:
                missing.append((key, r["name"], r["source"]))
    subs = json.loads((data / "races.json").read_text(encoding="utf-8")).get("subrace", [])
    for r in subs:
        if "_copy" not in r:
            continue
        # a copy takes its raceName / raceSource from the parent it copies
        rn, rs = r.get("raceName") or r["_copy"]["raceName"], r.get("raceSource") or r["_copy"]["raceSource"]
        if f"{slug(rn)}-{rs.lower()}-{slug(r['name'])}-{r['source'].lower()}" not in cat.subraces:
            missing.append(("subrace", r["name"], r["source"]))
    assert missing == []


@pytestmark_data
def test_a_resolved_background_and_a_resolved_species_carry_their_parents_content():
    from catalog.loader import load

    cat = load()
    acolyte = cat.backgrounds["acolyte-phb"] if "acolyte-phb" in cat.backgrounds else cat.backgrounds["acolyte"]
    gate = cat.backgrounds["baldurs-gate-acolyte-bgdia"]
    assert gate["starting_proficiencies"] == acolyte["starting_proficiencies"]  # same skills / tools as the Acolyte it copies
    assert gate["name"] == "Baldur's Gate Acolyte" and gate["source"] == "BGDIA"
    elf_lfl = cat.races["elf-lfl"]
    assert elf_lfl["source"] == "LFL" and elf_lfl["speed"] and elf_lfl["traits"]
