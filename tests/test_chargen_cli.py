"""Tests for chargen.cli — `python -m chargen <subcommand> ...`.

Task 7's whole point is proving the engine (catalog.py + build.py) is usable
with no server and no browser. Most tests here call `chargen.cli.main()`
directly with an argv list (the standard argparse-testing pattern — fast,
no subprocess). One test at the bottom spawns the real
`python -m chargen races` subprocess to prove the actual invocation works
end-to-end.

The real committed SRD data has exactly one background: acolyte (5e-SRD-
Backgrounds.json ships only that one record) — every build draft here uses
it, not the plan brief's "outlander" example, which does not exist on disk.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from chargen import cli

SCRIPTS = str(Path(__file__).resolve().parent.parent / "skills" / "dnd" / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)


def run(argv: list[str]) -> tuple[int, str, str]:
    """Call cli.main() directly and capture stdout/stderr, like a subprocess
    would, without paying subprocess cost.

    A malformed argument (e.g. the wrong --scores count) makes argparse
    itself print a usage error and call sys.exit(2) rather than returning
    normally -- caught here the same way a real subprocess's exit code
    would surface it.
    """
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


LEGAL_BUILD_ARGS = [
    "build",
    "--name", "Kaelen",
    "--race", "half-orc",
    "--class", "barbarian",
    "--level", "3",
    "--background", "acolyte",
    "--scores", "16,13,15,8,12,10",
]


class ListingCommandsTest(unittest.TestCase):
    def test_races_lists_all_nine_real_races(self):
        code, out, err = run(["races"])
        self.assertEqual(code, 0)
        for race_id in ("dwarf", "elf", "halfling", "human", "dragonborn",
                        "gnome", "half-elf", "half-orc", "tiefling"):
            self.assertIn(race_id, out)

    def test_official_flag_notes_no_official_data_yet(self):
        code, out, err = run(["races", "--official"])
        self.assertEqual(code, 0)
        self.assertIn("no official data", out.lower())
        # still shows the SRD races even with --official requested
        self.assertIn("human", out)

    def test_backgrounds_lists_acolyte(self):
        code, out, err = run(["backgrounds"])
        self.assertEqual(code, 0)
        self.assertIn("acolyte", out)
        self.assertIn("Insight", out)
        self.assertIn("Religion", out)

    def test_classes_lists_barbarian_with_hit_die(self):
        code, out, err = run(["classes"])
        self.assertEqual(code, 0)
        self.assertIn("barbarian", out)
        self.assertIn("12", out)  # d12 hit die

    def test_spells_class_and_level_filter_includes_fireball(self):
        code, out, err = run(["spells", "--class", "Wizard", "--level", "3"])
        self.assertEqual(code, 0)
        self.assertIn("Fireball", out)

    def test_spells_with_no_filters_lists_all_spells(self):
        code, out, err = run(["spells"])
        self.assertEqual(code, 0)
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(len(lines), 319)

    def test_spells_search_filter(self):
        code, out, err = run(["spells", "--search", "fire"])
        self.assertEqual(code, 0)
        self.assertIn("Fireball", out)
        self.assertNotIn("Magic Missile", out)

    def test_weapons_category_martial_includes_longsword(self):
        code, out, err = run(["weapons", "--category", "martial"])
        self.assertEqual(code, 0)
        self.assertIn("Longsword", out)

    def test_weapons_category_simple_excludes_longsword(self):
        code, out, err = run(["weapons", "--category", "simple"])
        self.assertEqual(code, 0)
        self.assertNotIn("Longsword", out)

    def test_armor_lists_twelve_entries_not_thirteen(self):
        code, out, err = run(["armor"])
        self.assertEqual(code, 0)
        lines = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(len(lines), 12)
        self.assertNotIn("Shield", out)


class BuildCommandTest(unittest.TestCase):
    def test_legal_build_prints_json_sheet_with_no_problems(self):
        code, out, err = run(LEGAL_BUILD_ARGS)
        self.assertEqual(code, 0, err)
        sheet = json.loads(out)
        self.assertEqual(sheet["name"], "Kaelen")
        self.assertEqual(sheet["classes"][0]["cls"], "Barbarian")
        self.assertEqual(sheet["classes"][0]["level"], 3)

    def test_skills_omitted_auto_picks_a_legal_set(self):
        code, out, err = run(LEGAL_BUILD_ARGS)
        self.assertEqual(code, 0, err)
        sheet = json.loads(out)
        # no skill-related problems means build() succeeded at all --
        # the auto-picked skills must have been valid Barbarian options
        # that don't collide with Acolyte's granted Insight/Religion.
        skills = sheet["proficiencies"]["skills"]
        self.assertIn("Insight", skills)
        self.assertIn("Religion", skills)
        self.assertEqual(len(skills), 4)  # 2 background + 2 auto-picked

    def test_explicit_skills_are_used_verbatim(self):
        code, out, err = run(LEGAL_BUILD_ARGS + ["--skills", "Perception,Survival"])
        self.assertEqual(code, 0, err)
        sheet = json.loads(out)
        skills = sheet["proficiencies"]["skills"]
        self.assertIn("Perception", skills)
        self.assertIn("Survival", skills)

    def test_illegal_draft_exits_nonzero_prints_problems_no_save_call(self):
        with TemporaryDirectory() as tmp:
            old = os.environ.get("DND_CAMPAIGN_ROOT")
            os.environ["DND_CAMPAIGN_ROOT"] = tmp
            try:
                code, out, err = run([
                    "build",
                    "--name", "Ghost",
                    "--race", "nonexistent-race",
                    "--class", "barbarian",
                    "--level", "3",
                    "--background", "acolyte",
                    "--scores", "16,13,15,8,12,10",
                    "--save",
                ])
                self.assertNotEqual(code, 0)
                self.assertIn("nonexistent-race", err)
                self.assertEqual(out, "")
                # no file was written anywhere under the temp campaign root
                characters_dir = Path(tmp) / "characters"
                self.assertFalse(characters_dir.exists() and any(characters_dir.iterdir()))
            finally:
                if old is None:
                    os.environ.pop("DND_CAMPAIGN_ROOT", None)
                else:
                    os.environ["DND_CAMPAIGN_ROOT"] = old

    def test_save_actually_calls_library_save_and_is_loadable(self):
        with TemporaryDirectory() as tmp:
            old = os.environ.get("DND_CAMPAIGN_ROOT")
            os.environ["DND_CAMPAIGN_ROOT"] = tmp
            os.environ.pop("DND_RUNTIME_DIR", None)
            try:
                import importlib
                import paths
                importlib.reload(paths)
                import library
                importlib.reload(library)

                code, out, err = run(LEGAL_BUILD_ARGS + ["--save"])
                self.assertEqual(code, 0, err)
                self.assertIn("Saved", out)
                self.assertIn("Kaelen", out)

                loaded = library.load("Kaelen")
                self.assertEqual(loaded["name"], "Kaelen")
                self.assertEqual(loaded["classes"][0]["cls"], "Barbarian")
            finally:
                if old is None:
                    os.environ.pop("DND_CAMPAIGN_ROOT", None)
                else:
                    os.environ["DND_CAMPAIGN_ROOT"] = old

    def test_bad_scores_count_is_a_cli_level_error(self):
        code, out, err = run([
            "build", "--name", "X", "--race", "human", "--class", "barbarian",
            "--level", "1", "--background", "acolyte", "--scores", "10,10,10",
        ])
        self.assertNotEqual(code, 0)


    def test_bad_hp_method_is_a_cli_level_error(self):
        """argparse rejects it by name before build() is ever called — the
        value picks a rules branch, so a typo must never reach the engine
        and silently take the default."""
        code, out, err = run(LEGAL_BUILD_ARGS + ["--hp-method", "max_then_avarage"])
        self.assertNotEqual(code, 0)
        self.assertIn("max_then_avarage", err)

    def test_both_real_hp_methods_are_accepted_by_the_cli(self):
        for method in ("max_then_average", "max_then_max"):
            with self.subTest(method=method):
                code, out, err = run(LEGAL_BUILD_ARGS + ["--hp-method", method])
                self.assertEqual(code, 0, err)

    def test_build_command_accepts_weapons_and_gear_flags(self):
        """--weapons/--gear (Task 5) parse into chosen_weapons/chosen_gear
        Draft entries (Task 4) and fold into the printed sheet's equipment,
        alongside whatever the class/background starting kit already grants."""
        code, out, err = run(LEGAL_BUILD_ARGS + [
            "--weapons", "longsword,dagger:2",
            "--gear", "rope-hempen-50-feet",
        ])
        self.assertEqual(code, 0, err)
        sheet = json.loads(out)
        names = {item["name"]: item["quantity"] for item in sheet["equipment"]}
        self.assertIn("Longsword", names)
        self.assertIn("Dagger", names)
        self.assertEqual(names["Dagger"], 2)
        self.assertIn("Rope, hempen (50 feet)", names)

    def test_a_non_numeric_weapon_quantity_is_a_cli_level_error_not_a_traceback(self):
        """`--weapons longsword:abc` used to raise a bare ValueError out of
        _parse_id_qty_list() in the middle of cmd_build. It is an argparse
        `type=` now, so it fails the same way --scores and --hp-method
        already do: a usage error naming the bad value, exit code 2."""
        code, out, err = run(LEGAL_BUILD_ARGS + ["--weapons", "longsword:abc"])
        self.assertNotEqual(code, 0)
        self.assertIn("abc", err)
        self.assertNotIn("Traceback", err)

    def test_a_non_numeric_gear_quantity_is_a_cli_level_error(self):
        code, out, err = run(LEGAL_BUILD_ARGS + ["--gear", "pouch:many"])
        self.assertNotEqual(code, 0)
        self.assertIn("many", err)

    def test_a_negative_weapon_quantity_is_reported_as_a_build_problem(self):
        """Parseable but illegal — caught by validate_equipment(), printed
        to stderr as a problem with exit code 1, not built into a sheet
        carrying a negative equipment row."""
        code, out, err = run(LEGAL_BUILD_ARGS + ["--weapons", "longsword:-5"])
        self.assertEqual(code, 1)
        self.assertIn("invalid quantity", err)

    def test_build_command_has_no_ruleset_flag(self):
        """draft["ruleset"] is fully gone from the schema (Task 1/2) —
        the CLI must no longer accept a --ruleset flag at all."""
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(LEGAL_BUILD_ARGS + ["--ruleset", "2014"])

    def test_build_command_prints_warnings_to_stdout(self):
        """A 2014-style race (dwarf) plus a 2024-style background
        (acolyte-xphb) is a legal draft that build() flags with a
        mixed-edition warning — cmd_build must print it to stdout,
        without failing the build.

        aasimar-xphb/acolyte-xphb (the plan brief's own original example)
        does NOT work here: both are genuinely ruleset "2024" in the real
        catalog, so they agree and produce no warning. dwarf (real SRD
        2014) + acolyte-xphb (real 2024) genuinely disagree instead.

        tests/conftest.py's autouse isolate_campaign_root fixture points
        DND_CAMPAIGN_ROOT at a fresh empty tmp dir for every test in this
        directory, so there is no real official (2024) data for
        Catalog.load() to find here regardless of what this machine has
        actually synced — "acolyte-xphb" would 404 as an unknown catalog
        id otherwise. This monkeypatches in a small hand-written official
        background fixture instead, the exact pattern
        tests/test_chargen_catalog.py's own official_fixture_dir fixture
        uses, reproducing the real acolyte-xphb record's own ability_choice
        shape (verified against the live catalog: options
        ['INT', 'WIS', 'CHA'], weights [2, 1]).
        """
        official_backgrounds = {
            "background": [
                {"name": "Acolyte", "source": "XPHB", "edition": "one",
                 "skillProficiencies": [{"insight": True, "religion": True}],
                 "ability": [{"choose": {"weighted": {
                     "from": ["int", "wis", "cha"], "weights": [2, 1]}}}],
                 "entries": []},
            ],
        }
        import chargen.catalog as catalog_mod

        args = cli.build_parser().parse_args([
            "build", "--name", "Test", "--race", "dwarf",
            "--background", "acolyte-xphb", "--class", "cleric",
            "--level", "3", "--scores", "13,12,14,10,15,8",
            "--skills", "Medicine,Persuasion",
            "--ability-choice-index", "0",
            "--ability-choice-assignment", "WIS:2,INT:1",
            "--hp-method", "max_then_average",
        ])

        with TemporaryDirectory() as official_dir:
            official_path = Path(official_dir)
            (official_path / "backgrounds.json").write_text(
                json.dumps(official_backgrounds))
            with unittest.mock.patch.object(
                    catalog_mod, "official_dir", lambda: official_path), \
                 unittest.mock.patch.object(
                    catalog_mod, "has_official", lambda: True):
                catalog_mod.Catalog._clear_cache()
                try:
                    out = io.StringIO()
                    with redirect_stdout(out):
                        code = cli.cmd_build(args)
                finally:
                    catalog_mod.Catalog._clear_cache()

        self.assertEqual(code, 0, out.getvalue())
        printed = out.getvalue()
        self.assertIn("2024", printed)

    def test_help_text_carries_no_internal_plan_vocabulary(self):
        """"Task 10" is this project's own planning vocabulary; a user
        reading --help has no idea what it refers to."""
        for argv in (["--help"], ["build", "--help"], ["races", "--help"]):
            with self.subTest(argv=argv):
                code, out, err = run(argv)
                self.assertNotIn("Task ", out)


class SubprocessSmokeTest(unittest.TestCase):
    """Proves the real `python -m chargen races` invocation genuinely works,
    not just our internal main() function."""

    def test_python_dash_m_chargen_races(self):
        repo_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "chargen", "races"],
            capture_output=True, text=True, cwd=str(repo_root),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("human", result.stdout)
        self.assertIn("half-orc", result.stdout)


if __name__ == "__main__":
    unittest.main()
