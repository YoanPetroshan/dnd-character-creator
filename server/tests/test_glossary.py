"""I0: the BG/EN glossary (server/i18n/glossary.json) and its generated outputs."""
import copy
import pathlib
import subprocess
import sys

import pytest

from i18n import glossary as g

DATA = g.load()
STARTERS = (
    "armorClass hitPoints hitPointDice proficiencyBonus savingThrows skills initiative speed passivePerception "
    "passiveInsight passiveInvestigation abilityScores spellSaveDc spellAttackBonus spellSlots cantrips "
    "preparedSpells spellbook species background originFeat feats classFeatures languages equipment "
    "weaponMastery size senses darkvision resistance immunity vulnerability shortRest longRest "
    "carryingCapacity feet gold"
).split()
SERVER = pathlib.Path(__file__).resolve().parent.parent


def test_file_is_structurally_valid():
    assert g.validate(DATA) == []


def test_starter_terms_present():
    assert [t for t in STARTERS if t not in DATA] == []


def test_every_term_has_en_bg_cite():
    for tid, t in DATA.items():
        assert t["en"] and t["bg"], tid
        assert t["cite"]["src"] in g.SOURCES and t["cite"]["locator"], tid


def test_validator_rejects_bad_entries():
    def errs(mutate):
        d = copy.deepcopy(DATA)
        mutate(d)
        return g.validate(d)

    assert errs(lambda d: d["skills"].pop("bg"))
    assert errs(lambda d: d["skills"].update(bg=""))
    assert errs(lambda d: d["skills"].update(bg="Skills"))  # no Cyrillic
    assert errs(lambda d: d["skills"].update(en="Умения"))
    assert errs(lambda d: d["skills"].pop("cite"))
    assert errs(lambda d: d["skills"]["cite"].update(src="wiki"))
    assert errs(lambda d: d["skills"]["cite"].update(locator=" "))
    assert errs(lambda d: d["darkvision"]["cite"].update(locator="5e-SRD-Traits.json"))  # missing ::
    assert errs(lambda d: d.update({"Bad_Id": d["skills"]}))
    assert errs(lambda d: d["skills"].update(en=d["speed"]["en"]))  # duplicate en
    assert g.validate({}) and g.validate([])


def test_cyrillic_bg_is_not_a_cite_of_book_text():
    # terms and locators only: nothing passage-sized is stored
    for tid, t in DATA.items():
        assert len(t["en"]) <= 40 and len(t["bg"]) <= 40 and len(t["cite"]["locator"]) <= 60, tid


# --- citations ------------------------------------------------------------------------------

def _json_cites():
    return [(tid, t["cite"]) for tid, t in DATA.items() if t["cite"]["src"] in ("srd", "5etools")]


def test_there_are_srd_and_5etools_cites():
    assert {c["src"] for _, c in _json_cites()} == {"srd", "5etools"}


@pytest.mark.parametrize("tid,cite", _json_cites(), ids=lambda v: v if isinstance(v, str) else "")
def test_srd_and_5etools_cites_hold(tid, cite):
    base = g.SRD_DIR if cite["src"] == "srd" else g.OFFICIAL_DIR
    fname = cite["locator"].partition("::")[0]
    if not (base / fname).is_file():
        pytest.skip(f"{fname} not present in this checkout")
    assert g.check_cite(tid, cite) is None


def test_json_cite_failures_are_reported():
    assert "does not exist" in g.check_cite("x", {"src": "srd", "locator": "nope.json::Darkvision"})
    assert "not found" in g.check_cite("x", {"src": "srd", "locator": "5e-SRD-Traits.json::No Such Trait"})
    assert g.check_cite("x", {"src": "srd", "locator": "5e-SRD-Traits.json::Darkvision"}) is None


@pytest.mark.skipif(not g.PHB_PATH.is_file(), reason="2024 PHB markdown is outside the repo (not in CI)")
def test_phb_cites_hold():
    text = g.PHB_PATH.read_text(encoding="utf-8")
    bad = [tid for tid, t in DATA.items()
           if t["cite"]["src"] == "phb2024" and not g.phb_locator_found(text, t["cite"]["locator"])]
    assert bad == []


def test_phb_cite_check_is_skipped_when_file_absent(tmp_path):
    cite = {"src": "phb2024", "locator": "Whatever"}
    assert g.check_cite("x", cite, tmp_path / "missing.md") is None
    assert g.check_cite("x", cite, None) is None


def test_phb_locator_forms(tmp_path):
    text = ("### Ability Scores\n\n***Hit Point Dice.*** x\n\n**Spell save DC** = 8\n\n"
            '<span data-rd-data-embed-name="true">Darkvision</span>\n\n| Gold Piece (GP) | 1 |\n')
    for loc in ("Ability Scores", "ability scores", "Hit Point Dice", "Spell save DC", "Darkvision",
                "text:Gold Piece (GP)"):
        assert g.phb_locator_found(text, loc), loc
    for loc in ("Ability", "Dice", "text:Silver", "Scores"):
        assert not g.phb_locator_found(text, loc), loc
    p = tmp_path / "phb.md"
    p.write_text(text, encoding="utf-8")
    assert g.check_cite("x", {"src": "phb2024", "locator": "Hit Point Dice"}, p) is None
    assert "not found" in g.check_cite("x", {"src": "phb2024", "locator": "Nope"}, p)


# --- consistency with the Bulgarian the app prints today -------------------------------------

def test_bg_matches_existing_app_wording():
    import export_fields as ef

    from export_labels import LABELS

    bg = LABELS["bg"]
    for sense in ("darkvision", "blindsight", "tremorsense", "truesight"):
        assert DATA[sense]["bg"] == bg["senses"][sense]
    assert DATA["shortRest"]["bg"] == ef._RECHARGE_WORDS["short"]
    assert DATA["longRest"]["bg"] == ef._RECHARGE_WORDS["long"]
    # the damage section labels are "<term> към щета" (XL moved the words to export_labels.py)
    assert bg["dmgResistances"] == DATA["resistance"]["bg"] + " към щета"
    assert bg["dmgImmunities"] == DATA["immunity"]["bg"] + " към щета"
    assert bg["dmgVulnerabilities"] == DATA["vulnerability"]["bg"] + " към щета"


def test_bg_appears_in_exports_or_frontend_copy():
    corpus = "".join((SERVER / f).read_text(encoding="utf-8")
                     for f in ("markdown_export.py", "pdf_export.py", "export_fields.py", "export_labels.py"))
    corpus += (SERVER.parent / "frontend" / "src" / "copy" / "bg.ts").read_text(encoding="utf-8")
    # originFeat: the app has no Bulgarian label for it today (the page text says "Origin feat"); the
    # rendering is new, introduced with the I-series.
    new_wording = {"originFeat"}
    missing = [tid for tid, t in DATA.items() if tid not in new_wording and t["bg"].lower() not in corpus.lower()]
    assert missing == [], "bg wording not used anywhere in the app: " + ", ".join(missing)


# --- generated files ---------------------------------------------------------------------------

def test_generated_files_are_up_to_date():
    for path, text in g.outputs(DATA).items():
        assert path.read_text(encoding="utf-8") == text, f"{path} is stale: run `python -m i18n.glossary` in server/"


def test_check_mode_reports_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "GLOSSARY_MD", tmp_path / "GLOSSARY.md")
    monkeypatch.setattr(g, "GLOSSARY_TS", tmp_path / "glossary.gen.ts")
    assert g.main(["--check"]) == 1  # missing files
    assert g.main([]) == 0  # writes
    assert g.main(["--check"]) == 0
    (tmp_path / "glossary.gen.ts").write_text("// edited\n", encoding="utf-8")
    assert g.main(["--check"]) == 1


def test_cli_check_passes():
    r = subprocess.run([sys.executable, "-m", "i18n.glossary", "--check"], cwd=SERVER, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_generated_ts_is_well_formed():
    ts = g.render_ts(DATA)
    assert ts.count(" en: ") == len(DATA) and "export type GlossaryId" in ts
    md = g.render_markdown(DATA)
    assert md.count("\n| `") == len(DATA)
