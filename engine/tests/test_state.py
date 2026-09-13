import json

import pytest

from engine import state


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    (tmp_path / ".runtime").mkdir(parents=True)
    camp = tmp_path / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "state.md").write_text(
        "# State\n"
        "**Ruleset:** 2014\n\n"
        "## Session Flags\n"
        "roll_mode: players\n"
        "autorun: true\n"
        "autorun_interval: 60\n\n"
        "## Live State Flags\n"
        "- Faction: Harpers neutral\n"
        "- Scene: library, night\n"
    )
    (camp / "characters" / "falin.md").write_text("# Falin\n")
    (camp / "characters" / "sparrow.md").write_text("# Sparrow\n")
    (tmp_path / ".runtime" / ".campaign").write_text("demo\n")
    return tmp_path


def test_active_campaign(root):
    assert state.active_campaign() == "demo"


def test_take_input_queue_reads_and_clears(root):
    q = root / ".runtime" / ".input_queue"
    q.write_text("[Falin]: отварям вратата")
    assert state.take_input_queue() == "[Falin]: отварям вратата"
    assert not q.exists()
    assert state.take_input_queue() == ""


def test_text_log_count(root):
    assert state.text_log_count() == 0
    (root / ".runtime" / "text_log.json").write_text(json.dumps([{"t": "a"}, {"t": "b"}]))
    assert state.text_log_count() == 2


def test_session_flags_parsed(root):
    flags = state.session_flags("demo")
    assert flags["roll_mode"] == "players"
    assert flags["autorun_interval"] == "60"


def test_set_session_flag_updates_existing(root):
    state.set_session_flag("demo", "roll_mode", "auto")
    assert state.session_flags("demo")["roll_mode"] == "auto"


def test_set_session_flag_adds_new(root):
    state.set_session_flag("demo", "language", "bg")
    assert state.session_flags("demo")["language"] == "bg"


def test_party_names(root):
    assert sorted(state.party_names("demo")) == ["Falin", "Sparrow"]


def test_party_names_uses_the_real_two_word_name_from_the_sheet(root):
    """Regression: names came from the filename slug, so the real, live
    character `characters/sylwen-nightbrook.md` (heading `# Sylwen
    Nightbrook`) was reported as "Sylwen-Nightbrook". That slug never appears
    in narration, so the PC-autoroll guard could not match it and the DM's own
    turn prompt introduced the party under a wrong name.
    """
    camp = root / "campaigns" / "demo"
    (camp / "characters" / "sylwen-nightbrook.md").write_text(
        "# Sylwen Nightbrook\n**Player:** somebody\n\n## Abilities\n"
    )
    names = state.party_names("demo")
    assert "Sylwen Nightbrook" in names
    assert "Sylwen-Nightbrook" not in names


def test_party_names_falls_back_to_spaced_slug_without_a_heading(root):
    camp = root / "campaigns" / "demo"
    (camp / "characters" / "torvin-bracewell.md").write_text(
        "## Abilities\nno top-level heading here\n"
    )
    names = state.party_names("demo")
    assert "Torvin Bracewell" in names


def test_party_names_ignores_section_headings(root):
    camp = root / "campaigns" / "demo"
    (camp / "characters" / "vex-skulk.md").write_text(
        "## Notes\nsome preamble\n\n# Vex Skulk\n"
    )
    assert "Vex Skulk" in state.party_names("demo")


def test_state_header_includes_live_flags(root):
    header = state.state_header("demo")
    assert "Harpers neutral" in header
    assert "library, night" in header


def test_set_session_flag_substring_vs_header_detection(root):
    """Regression test for Bug 1: substring check vs case-insensitive header detection.

    Previously, set_session_flag used a case-sensitive substring check to detect
    if the Session Flags section exists, but the loop used case-insensitive exact-line
    matching. If "## Session Flags" appeared as a substring in a line (e.g.,
    "- Note: see ## Session Flags above") but not as a real header, the function would
    skip creating the header and silently lose the written flag.
    """
    camp = root / "campaigns" / "demo"
    # Create a state.md with "## Session Flags" appearing as a substring, not a header
    (camp / "state.md").write_text(
        "# State\n"
        "- Note: see ## Session Flags above for info\n"
    )
    # Should create the header and write the flag successfully
    state.set_session_flag("demo", "new_flag", "value1")
    flags = state.session_flags("demo")
    assert flags["new_flag"] == "value1"

    # Also test with mixed-case header to ensure case-insensitivity
    (camp / "state.md").write_text(
        "# State\n"
        "## session flags\n"
    )
    state.set_session_flag("demo", "another_flag", "value2")
    flags = state.session_flags("demo")
    assert flags["another_flag"] == "value2"


def test_set_session_flag_with_digit_in_key(root):
    """Regression test for Bug 2: keys with digits should round-trip correctly.

    Previously, _FLAG_RE only matched keys with lowercase letters and underscores.
    Keys with digits were silently dropped on read, breaking the round-trip contract
    that set_session_flag → session_flags should preserve the value.
    """
    state.set_session_flag("demo", "interval2", "5")
    flags = state.session_flags("demo")
    assert flags["interval2"] == "5"

    # Also test that updating a key with digits works
    state.set_session_flag("demo", "interval2", "10")
    flags = state.session_flags("demo")
    assert flags["interval2"] == "10"
