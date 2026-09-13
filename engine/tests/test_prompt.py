import pytest

from engine import prompt
from engine.config import Config


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "state.md").write_text(
        "## Live State Flags\n- Scene: crypt, torchlight\n"
    )
    (camp / "characters" / "falin.md").write_text("# Falin\n")
    return tmp_path


GLOSSARY = {
    "terms": [{"en": "Stealth", "bg": "Скриване (Stealth)"}],
    "keep_english": ["Advantage", "HP"],
    "never_translate": ["Waterdeep"],
}


def test_read_skill_docs_is_substantial():
    docs = prompt.read_skill_docs()
    assert len(docs) > 10_000
    # "Dice convention" is the old send.py --dice-request subsection,
    # deliberately excluded -- see test_read_skill_docs_trims_bloat below.
    assert "Dice convention" not in docs


def test_read_skill_docs_substitutes_the_real_skill_dir():
    """${CLAUDE_SKILL_DIR} is only expanded by Claude Code's native
    Skill-loading mechanism. read_skill_docs() reads the files directly with
    Path.read_text(), bypassing that -- so it must substitute the real path
    itself, or every example command in the docs reaches the agent with a
    literal, non-existent placeholder in it."""
    docs = prompt.read_skill_docs()
    assert "${CLAUDE_SKILL_DIR}" not in docs
    assert str(prompt.SKILL_DIR) in docs


def test_read_skill_docs_drops_dice_request_subsection_but_keeps_neighbors():
    """The 'Dice convention' subsection documents the old send.py
    --dice-request protocol for PC rolls, fully superseded by
    pc_roll_tool_block()'s engine.dice path. It must be gone, but the rest
    of 'Active DM Mode' -- display sync, per-turn combat sequence, the
    player-input-queue mechanism -- must survive untouched."""
    docs = prompt.read_skill_docs()
    assert "Active DM Mode" in docs
    assert "--dice-request" not in docs
    assert "Dice convention" not in docs
    assert "roll_mode: players" not in docs
    assert "roll_mode: auto" not in docs
    # neighboring content in the same section must still be present
    assert "check_input.py" in docs
    assert "Per-turn combat sequence" in docs
    assert "_display_running" in docs


def test_read_skill_docs_keeps_the_bullets_immediately_after_dice_convention():
    """Regression pin: _drop_bold_subsection's original terminator (bold-only
    line / heading / "---") ran past the end of the "Dice convention"
    material and swallowed the three unindented bold paragraphs that
    immediately follow it in the real file -- Initiative, the per-player
    roll-mode override, and "NPC/monster rolls are always yours". None of
    those document --dice-request and none of them should have been cut.

    Initiative matters most: dice_protocol_block() states an unqualified
    "never roll a PC's check" rule, and a PC's initiative roll is a DEX
    check -- without this explicit carve-out surviving, the agent has no
    documented exception for initiative at all.
    """
    docs = prompt.read_skill_docs()
    assert "**Initiative** is always DM-rolled" in docs
    assert "combat.py init" in docs
    assert "Per-player override" in docs
    assert "[[<Char> roll mode: auto|players]]" in docs
    assert "NPC/monster rolls are always yours" in docs


def test_read_skill_docs_trims_bloat_sections():
    """One-time setup, pure reference, and content fully superseded by this
    project's own engine must not be resent every turn."""
    docs = prompt.read_skill_docs()
    for gone in (
        "Guided entry",
        "Directory Layout",
        "Model Routing",
        "claude-sonnet-4-6",  # stale model name from the Model Routing table
        "Data Commands",
        "Display Companion Setup",
        "Continuity Autosave",
        "Lazy Corpus",
    ):
        assert gone not in docs, f"expected {gone!r} to be trimmed from skill docs"


def test_read_skill_docs_keeps_load_bearing_content():
    """Standards, table dials, XP awards, tutor mode, and scripts actually
    invoked mid-turn must survive the trim."""
    docs = prompt.read_skill_docs()
    for kept in (
        "What Makes a Great DM",
        "Table Dials",
        "XP Awards",
        "Tutor Mode",
        "push_stats.py",
        "combat.py",
        "tracker.py",
        "calendar.py",
        "campaign_search.py",
        "session_recap.py",
        "oracle.py",
        "xp.py",
        "ability-scores.py",
        "character.py",
        "dice.py",
    ):
        assert kept in docs, f"expected {kept!r} to survive the trim"


def test_system_prompt_contains_language_and_dice_rules():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "БЪЛГАРСКИ" in sp
    assert "Waterdeep" in sp
    assert "Скриване (Stealth)" in sp
    assert "КРИТИЧЕН УДАР" in sp
    assert "никога" in sp.lower()


def test_system_prompt_forbids_echoing_the_player_action():
    """The display server now writes the player's action to the feed itself,
    verbatim, the moment it is handed off. The skill docs still tell the agent
    to open every turn with `send.py --player <name>` and a "cleaned version"
    of the text — this block must supersede that, or the player sees their own
    line twice, reworded, an LLM turn late."""
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    block = prompt.player_echo_block()
    assert block in sp
    assert "НЕ извиквай `display/send.py --player" in block
    assert "заменя старата инструкция" in block
    # The instruction it overrides is genuinely still in the pulled-in docs —
    # if that ever stops being true, this override can be retired.
    assert "send.py --player" in prompt.read_skill_docs()


def test_system_prompt_states_engine_owns_the_loop():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "autorun_wait" in sp
    assert "send.py" in sp


def test_system_prompt_carries_the_two_modes():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "МОДУЛЕН" in sp
    assert "ИМПРОВИЗИРАН" in sp
    assert "random encounter" in sp.lower()


def test_system_prompt_carries_ooc_block_rules():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "OOC" in sp
    assert "Тежко ранен" in sp
    assert "Невредим" in sp


def test_system_prompt_carries_source_priority_and_citation():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "PHB 2024" in sp
    assert "Monster Manual 2025" in sp
    assert "[Справка:" in sp


def test_system_prompt_teaches_the_rules_lookup_cli():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "engine.rules.lookup" in sp
    assert "monster" in sp


def test_system_prompt_teaches_the_pc_roll_cli():
    """The engine's own dice wrapper has to be reachable by the agent, and it
    has to be unambiguous: the upstream skill docs (included verbatim) also
    describe `send.py --dice-request --wait` and wrongly claim it prints the
    player's result, so the prompt must name one command and say which one
    wins."""
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    # The fully-qualified form only: the agent's cwd is the campaign root, so
    # a bare `python3 -m engine.dice` dies with ModuleNotFoundError. It must
    # not survive anywhere in the prompt — not in the examples, and not in the
    # "use only this" directive sentence either.
    assert f"{prompt.cli('engine.dice')} pc" in sp
    assert "python3 -m engine." not in sp
    assert "--character" in sp
    # The skill docs' competing instruction must be explicitly superseded.
    block = prompt.pc_roll_tool_block()
    assert "send.py --dice-request" in block
    assert "TIMEOUT" in block


def test_pc_roll_block_is_reachable_from_the_dice_protocol():
    protocol = prompt.dice_protocol_block()
    assert "ЗАЯВКА ЗА ХВЪРЛЯНЕ НА ИГРАЧ" in protocol
    assert "ЗАЯВКА ЗА ХВЪРЛЯНЕ НА ИГРАЧ" in prompt.pc_roll_tool_block()


def test_pc_roll_block_also_warns_against_dice_py_player_for_pcs():
    """The old 'Dice convention' subsection cut from SKILL.md carried the
    strongest anti-auto-roll warning in the doc (never fall back to dice.py
    for a PC). SKILL-scripts.md's Dice Script section is still inlined
    verbatim and documents `dice.py ... --player <pc-name>` as normal usage
    -- correct for NPC/DM-side rolls, but nothing else in the prompt says
    that's wrong for a PC's own roll. pc_roll_tool_block() must carry that
    warning forward explicitly so the gap doesn't reopen."""
    block = prompt.pc_roll_tool_block()
    assert "dice.py" in block
    assert "--player" in block


def test_system_prompt_carries_prohibitions():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert "ЗАБРАНИ" in sp


def test_english_config_skips_bulgarian_block():
    sp = prompt.build_system_prompt(Config(language="en"), GLOSSARY)
    assert "ЕЗИК НА ИГРАТА" not in sp


def test_turn_prompt_embeds_state_and_actions(root):
    tp = prompt.build_turn_prompt("demo", "[Falin]: претърсвам саркофага")
    assert "crypt, torchlight" in tp
    assert "претърсвам саркофага" in tp
    assert "Falin" in tp


# --- campaign_paths_block / turn-prompt file-location grounding ----------
#
# Regression coverage for the production incident that motivated this block:
# the agent's Bash cwd is one level ABOVE the active campaign (campaign_root,
# shared by every campaign) and the turn prompt never stated the resolved
# path or the character-filename convention, so a request for a specific
# character's sheet had no anchor. The agent resorted to
# `find / -iname "*sylwen*"` -- a whole-filesystem scan that alone took 68s
# of a 256s turn. These tests pin that the real, resolved path and the real
# character filenames now reach the prompt, and that filesystem search is
# explicitly forbidden.

@pytest.fixture
def two_char_root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    camp = tmp_path / "campaigns" / "demo"
    (camp / "characters").mkdir(parents=True)
    (camp / "state.md").write_text("## Live State Flags\n- Scene: crypt\n")
    (camp / "characters" / "sylwen-nightbrook.md").write_text("# Sylwen Nightbrook\n")
    (camp / "characters" / "torvin-bracewell.md").write_text("# Torvin Bracewell\n")
    return tmp_path


def test_campaign_paths_block_states_the_real_resolved_directory(two_char_root):
    block = prompt.campaign_paths_block("demo")
    expected_dir = two_char_root / "campaigns" / "demo"
    assert str(expected_dir) in block


def test_campaign_paths_block_lists_real_character_filenames_mapped_to_real_names(two_char_root):
    """The filename is a slug (lowercase, hyphen-separated) of the name on the
    sheet, not the name itself -- verified against engine.state.character_name
    and the real files on disk. Listing the actual files present, mapped to
    their real names, is what removes the need to search or guess."""
    block = prompt.campaign_paths_block("demo")
    assert "characters/sylwen-nightbrook.md" in block
    assert "Sylwen Nightbrook" in block
    assert "characters/torvin-bracewell.md" in block
    assert "Torvin Bracewell" in block


def test_campaign_paths_block_names_the_other_campaign_files(two_char_root):
    block = prompt.campaign_paths_block("demo")
    for fname in (
        "state.md", "world.md", "npcs.md", "npcs-full.md", "arc.md",
        "world-nodes.md", "session-log.md", "source-index.md",
    ):
        assert fname in block
    assert "source/" in block


def test_campaign_paths_block_forbids_filesystem_search(two_char_root):
    block = prompt.campaign_paths_block("demo")
    assert "find" in block
    assert "НЕ търси" in block or "НИКОГА" in block


def test_turn_prompt_includes_the_campaign_paths_block(two_char_root):
    tp = prompt.build_turn_prompt("demo", "[Sylwen]: тествам")
    expected_dir = two_char_root / "campaigns" / "demo"
    assert str(expected_dir) in tp
    assert "characters/sylwen-nightbrook.md" in tp
    assert "find" in tp


def test_campaign_paths_block_handles_missing_characters_dir(tmp_path, monkeypatch):
    """A campaign with no characters/ directory yet (e.g. mid-creation) must
    not raise -- the block should still describe the convention generically."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    (tmp_path / "campaigns" / "demo").mkdir(parents=True)
    block = prompt.campaign_paths_block("demo")
    assert "characters/" in block


# --- _trim_skill_doc / _split_top_sections / _drop_bold_subsection -------
#
# These exercise the markdown parsing directly against synthetic content
# that mirrors the real heading structure of skills/dnd/SKILL.md and
# SKILL-scripts.md (top-level "##" sections, nested "###" standards, a bold
# pseudo-heading subsection, and fenced code blocks containing lines that
# start with "#" -- bash comments that must never be mistaken for document
# headings). This keeps the parsing logic covered even if the real skill
# docs are edited later, since this project doesn't own skills/dnd/.

SKILL_MD_FIXTURE = """\
# D&D 5e Dungeon Master

Intro paragraph.

## Guided entry — what does the player want this session?

Menu-driven campaign selection, only relevant before the agent starts.

## What Makes a Great DM — Applied Standards

### 1. Improvise, Don't Script
Body text for standard one.

### 2. Listen and Calibrate
Body text for standard two.

## Directory Layout

```
${CLAUDE_SKILL_DIR}/
  scripts/
```

## Model Routing

| Tier | Model |
|------|-------|
| Sonnet | claude-sonnet-4-6 |

## Active DM Mode

Stay in DM mode narration text.

**Narration principles:**
- bullet one
- bullet two

**Dice convention — who rolls (read `roll_mode` and obey it):**

Roll handling is chosen at game start and stored as `roll_mode`.

- **`roll_mode: players` (default) — players roll their own PCs.** Call for the roll and wait.
  - **Prescribe the roll through the display when it's running**: call
    `python3 ${CLAUDE_SKILL_DIR}/display/send.py --dice-request --character "<PC>" --spec 1dN --wait`.
    The roll routes to that PC's phone.
- **`roll_mode: auto` — you roll everything openly.** Resolve PC d20s yourself via `dice.py`.

**Initiative** is always DM-rolled via `combat.py init` for all combatants regardless of `roll_mode`.

**Per-player override:** a player can flip their own PC via the phone Settings toggle. `check_input.py` prepends a `[[<Char> roll mode: auto|players]]` directive.

**NPC/monster rolls are always yours** — resolve via `dice.py`, show math inline:
  `Goblin attacks: d20+4 = 17 vs AC 16 — hit! 1d6+2 = 5 piercing damage`

---

**Display sync (when `_display_running = true`):**

```bash
# Hidden roll (silent in terminal, visible on display):
python3 ${CLAUDE_SKILL_DIR}/scripts/dice.py d20+5 --silent
```

## XP Awards

Award XP text.
"""

SKILL_SCRIPTS_MD_FIXTURE = """\
# D&D Skill — Scripts Reference

## Dice Script — `scripts/dice.py`

```bash
# Always pass --label so the phone HUD shows what the roll is for:
python3 ${CLAUDE_SKILL_DIR}/scripts/dice.py d20+5 --label "Perception check"
```

## Data Commands — `scripts/sync_srd.py`, `scripts/build_srd.py`, and `scripts/lookup.py`

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/lookup.py spell "fireball"
```

## Display Companion Setup (one-time)

```bash
cd ${CLAUDE_SKILL_DIR}/display
pip3 install -r requirements.txt
```

## Continuity Autosave — `scripts/autosave_checkpoint.py`, `scripts/install_autosave_hook.py`

```bash
# Opt-in: register the Stop hook (writes ~/.claude/settings.json, idempotent)
python3 ${CLAUDE_SKILL_DIR}/scripts/install_autosave_hook.py
```

## Lazy Corpus — `scripts/corpus_check.py`

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/corpus_check.py --campaign <name>
```
"""


def test_trim_skill_doc_drops_excluded_h2_sections_but_keeps_neighbors():
    trimmed = prompt._trim_skill_doc("SKILL.md", SKILL_MD_FIXTURE)
    assert "Guided entry" not in trimmed
    assert "Directory Layout" not in trimmed
    assert "Model Routing" not in trimmed
    assert "claude-sonnet-4-6" not in trimmed
    # untouched neighbors, including the nested ### standards
    assert "# D&D 5e Dungeon Master" in trimmed
    assert "1. Improvise, Don't Script" in trimmed
    assert "2. Listen and Calibrate" in trimmed
    assert "Active DM Mode" in trimmed
    assert "XP Awards" in trimmed


def test_trim_skill_doc_drops_only_the_dice_convention_subsection():
    trimmed = prompt._trim_skill_doc("SKILL.md", SKILL_MD_FIXTURE)
    assert "Dice convention" not in trimmed
    assert "--dice-request" not in trimmed
    assert "roll_mode: players" not in trimmed
    assert "roll_mode: auto" not in trimmed
    # content immediately before and after the bold subsection survives
    assert "**Narration principles:**" in trimmed
    assert "**Display sync (when `_display_running = true`):**" in trimmed
    assert "Hidden roll (silent in terminal" in trimmed


def test_trim_skill_doc_does_not_swallow_bullets_after_dice_convention():
    """Regression pin (fixture level): the three unindented bold paragraphs
    that immediately follow the 'Dice convention' material in the real file
    -- Initiative, the per-player roll-mode override, and 'NPC/monster
    rolls are always yours' -- must survive. They don't document
    --dice-request and were never meant to be part of the cut; an earlier
    version of _drop_bold_subsection's terminator logic swallowed them
    because it only stopped at a bold-*only* line, a heading, or '---'."""
    trimmed = prompt._trim_skill_doc("SKILL.md", SKILL_MD_FIXTURE)
    assert "**Initiative** is always DM-rolled via `combat.py init`" in trimmed
    assert "**Per-player override:**" in trimmed
    assert "[[<Char> roll mode: auto|players]]" in trimmed
    assert "**NPC/monster rolls are always yours**" in trimmed
    assert "Goblin attacks: d20+4 = 17 vs AC 16" in trimmed


def test_trim_skill_doc_ignores_hash_comments_inside_fenced_code():
    """A bash comment like '# Hidden roll ...' inside a ```code fence```
    must never be mistaken for a level-1 heading and used as a section
    boundary -- both real skill docs are full of these."""
    trimmed = prompt._trim_skill_doc("SKILL.md", SKILL_MD_FIXTURE)
    # the comment line and the command after it must both still be present,
    # proving the fence content wasn't chopped mid-block
    assert "# Hidden roll (silent in terminal, visible on display):" in trimmed
    assert 'dice.py d20+5 --silent' in trimmed


def test_trim_skill_doc_scripts_excludes_setup_and_superseded_sections():
    trimmed = prompt._trim_skill_doc("SKILL-scripts.md", SKILL_SCRIPTS_MD_FIXTURE)
    for gone in (
        "Data Commands",
        "Display Companion Setup",
        "Continuity Autosave",
        "Lazy Corpus",
        "install_autosave_hook.py",
        "corpus_check.py",
    ):
        assert gone not in trimmed, f"expected {gone!r} to be trimmed"
    # dice.py is still invoked mid-turn (NPC/DM-side rolls) -- must survive
    assert "Dice Script" in trimmed
    assert "scripts/dice.py" in trimmed


def test_trim_skill_doc_is_a_no_op_for_files_with_no_excluded_sections():
    text = "# Title\n\n## Some Section\n\nBody.\n"
    assert prompt._trim_skill_doc("SKILL.md", text) == text


def test_split_top_sections_does_not_duplicate_nested_h3_content():
    chunks = prompt._split_top_sections(SKILL_MD_FIXTURE)
    joined = "".join(block for _, _, block in chunks)
    # reassembling every chunk must reproduce the source exactly once
    assert joined == SKILL_MD_FIXTURE
    assert joined.count("1. Improvise, Don't Script") == 1


def test_read_skill_docs_substitution_leaves_no_placeholder_anywhere():
    """End-to-end guard on the real files: zero literal occurrences of the
    ${CLAUDE_SKILL_DIR} placeholder in what actually reaches the model."""
    docs = prompt.read_skill_docs()
    assert docs.count("${CLAUDE_SKILL_DIR}") == 0


def test_build_system_prompt_has_no_placeholder_occurrences():
    sp = prompt.build_system_prompt(Config(), GLOSSARY)
    assert sp.count("${CLAUDE_SKILL_DIR}") == 0
