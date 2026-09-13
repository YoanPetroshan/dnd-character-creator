import json

import pytest

from engine import local_context


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "source").mkdir()
    (camp / "state.md").write_text(
        "# Campaign: demo\n\n"
        "## Current Situation\n"
        "- **Location:** the Patio (M2)\n"
        "- **Party:** Torvin Bracewell — Fighter 1 | HP 12/12 | AC 18\n\n"
        "## Pinned Facts\n"
        "- The party's home village is cursed.\n\n"
        "## Live State Flags\n"
        "- Door to M9 is ajar.\n\n"
        "## Campaign Arc\n"
        "```yaml\n"
        "type: structured\n"
        "current_chapter: \"1.2\"\n"
        "current_chapter_detail:\n"
        "  id: \"1.2\"\n"
        "  title: \"Fistandia's Mansion\"\n"
        "  location: \"the mansion (M1-M19)\"\n"
        "  source_ref: \"source/2-mansion.md\"\n"
        "  key_beats:\n"
        "    - \"Find the seven books\"\n"
        "next_chapter: \"2.1\"\n"
        "```\n",
        encoding="utf-8",
    )
    (camp / "source" / "2-mansion.md").write_text(
        "## Fistandia's Mansion\n\n"
        "#### M1. Foyer\n"
        "A grand foyer with two hallways.\n\n"
        "#### M2. Patio\n"
        "A semicircular flagstone patio wreathed in indigo mist.\n\n"
        "#### M3. Library\n"
        "Shelves of waterlogged books.\n",
        encoding="utf-8",
    )
    (camp / "characters" / "torvin-bracewell.md").write_text(
        "# Torvin Bracewell\n**Player:** test\n\n"
        "## Combat Stats\n"
        "- **HP:** 12 / 12 | **Temp HP:** 0\n"
        "- **AC:** 18\n",
        encoding="utf-8",
    )
    return camp


def test_arc_pointer_parses_structured_block(root):
    arc = local_context.arc_pointer("demo")
    assert arc["current_chapter"] == "1.2"
    assert arc["current_chapter_detail"]["source_ref"] == "source/2-mansion.md"


def test_arc_pointer_returns_none_without_a_campaign_arc_section(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "bare"
    camp.mkdir(parents=True)
    (camp / "state.md").write_text("## Current Situation\n- nothing\n")
    assert local_context.arc_pointer("bare") is None


def test_chapter_excerpt_extracts_only_the_current_room(root):
    excerpt = local_context.chapter_excerpt("demo")
    assert "semicircular flagstone patio" in excerpt
    assert "grand foyer" not in excerpt
    assert "waterlogged books" not in excerpt


def test_chapter_excerpt_falls_back_to_key_beats_without_a_room_match(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    camp.mkdir(parents=True)
    (camp / "state.md").write_text(
        "## Current Situation\n- **Location:** somewhere vague\n\n"
        "## Campaign Arc\n```yaml\n"
        "current_chapter_detail:\n"
        "  title: \"Opening\"\n"
        "  key_beats:\n    - \"Meet the sage\"\n"
        "```\n"
    )
    excerpt = local_context.chapter_excerpt("demo")
    assert "Opening" in excerpt
    assert "Meet the sage" in excerpt


def test_party_line_extracts_the_party_bullet(root):
    assert "Torvin Bracewell" in local_context.party_line("demo")


def test_state_section_extracts_named_heading_only(root):
    pinned = local_context.state_section("demo", "Pinned Facts")
    assert "cursed" in pinned
    assert "Torvin" not in pinned


def test_recent_narration_tail_reads_text_log(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    runtime = tmp_path / ".runtime"
    runtime.mkdir(parents=True)
    log = [{"text": f"Line {i}"} for i in range(10)]
    (runtime / "text_log.json").write_text(json.dumps(log), encoding="utf-8")
    tail = local_context.recent_narration_tail("demo", n=3)
    assert "Line 9" in tail
    assert "Line 0" not in tail


def test_recent_narration_tail_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    assert local_context.recent_narration_tail("demo") == ""


def test_character_sheet_path_matches_by_real_name_case_insensitively(root):
    path = local_context.character_sheet_path("demo", "torvin bracewell")
    assert path is not None
    assert path.name == "torvin-bracewell.md"


def test_character_sheet_path_returns_none_for_unknown_name(root):
    assert local_context.character_sheet_path("demo", "Nobody") is None


def test_read_hp_returns_current_and_max(root):
    assert local_context.read_hp("demo", "Torvin Bracewell") == (12, 12)


def test_apply_hp_delta_damages_and_persists(root):
    result = local_context.apply_hp_delta("demo", "Torvin Bracewell", -5)
    assert result == (7, 12)
    assert local_context.read_hp("demo", "Torvin Bracewell") == (7, 12)


def test_apply_hp_delta_heals_clamped_to_max(root):
    local_context.apply_hp_delta("demo", "Torvin Bracewell", -10)
    result = local_context.apply_hp_delta("demo", "Torvin Bracewell", 999)
    assert result == (12, 12)


def test_apply_hp_delta_clamps_at_zero(root):
    result = local_context.apply_hp_delta("demo", "Torvin Bracewell", -999)
    assert result == (0, 12)


def test_apply_hp_delta_unknown_character_returns_none(root):
    assert local_context.apply_hp_delta("demo", "Nobody", -5) is None


# --- quests -----------------------------------------------------------------
# The sidebar's quest entries had nothing to open because only name+status
# ever reached the display; the descriptions were sitting in state.md the
# whole time. These pin the parse that finally carries them across.


def _quest_campaign(tmp_path, monkeypatch, body: str):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    camp.mkdir(parents=True, exist_ok=True)
    (camp / "state.md").write_text(
        "# Campaign: demo\n\n## Active Quests\n" + body + "\n\n## World State\n- x\n",
        encoding="utf-8",
    )
    return "demo"


def test_quests_carry_name_status_and_description(tmp_path, monkeypatch):
    camp = _quest_campaign(tmp_path, monkeypatch,
        "- **Escape Fistandia's Mansion:** collect the seven lettered books "
        "and speak \"liberty\" near the M1 portal — status: pending\n"
    )
    assert local_context.quests(camp) == [{
        "name": "Escape Fistandia's Mansion",
        "status": "active",
        "detail": 'collect the seven lettered books and speak "liberty" near the M1 portal',
    }]


def test_quests_map_state_md_wording_onto_tracker_statuses(tmp_path, monkeypatch):
    """state.md writes "pending"/"done"; the tracker only styles a fixed set,
    rendering anything else in a washed-out "unknown"."""
    camp = _quest_campaign(tmp_path, monkeypatch,
        "- **A:** one — status: pending\n"
        "- **B:** two — status: done\n"
        "- **C:** three — status: failed\n"
        "- **D:** four — status: threat\n"
    )
    assert [q["status"] for q in local_context.quests(camp)] == \
        ["active", "resolved", "failed", "threat"]


def test_quests_default_to_active_without_a_trailing_status(tmp_path, monkeypatch):
    camp = _quest_campaign(tmp_path, monkeypatch, "- **Find Matreous:** ask at Candlekeep\n")
    q = local_context.quests(camp)
    assert q == [{"name": "Find Matreous", "status": "active",
                  "detail": "ask at Candlekeep"}]


def test_quests_skip_prose_and_survive_a_missing_section(tmp_path, monkeypatch):
    """The section is hand-maintained prose, so a stray line must be ignored
    rather than raising and taking startup down with it."""
    camp = _quest_campaign(tmp_path, monkeypatch,
        "*(none yet)*\n"
        "- not a quest, no bold name\n"
        "- **Real One:** a description — status: active\n"
    )
    assert [q["name"] for q in local_context.quests(camp)] == ["Real One"]

    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path / "empty"))
    (tmp_path / "empty" / "campaigns" / "demo").mkdir(parents=True)
    (tmp_path / "empty" / "campaigns" / "demo" / "state.md").write_text("# Campaign: demo\n")
    assert local_context.quests("demo") == []


def test_quests_tolerate_a_name_with_no_description(tmp_path, monkeypatch):
    """No detail means the sidebar entry stays non-interactive, which is
    correct -- an expandable row that opens onto nothing is worse than a
    plain one."""
    camp = _quest_campaign(tmp_path, monkeypatch, "- **Bare Quest:** — status: active\n")
    assert local_context.quests(camp) == [
        {"name": "Bare Quest", "status": "active", "detail": ""}
    ]
