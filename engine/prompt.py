"""System prompt and per-turn prompt assembly."""
from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

from engine.config import Config
from engine.lang import glossary_prompt_block
from engine.state import campaign_dir, character_name, party_names, state_header

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skills" / "dnd"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

# ${CLAUDE_SKILL_DIR} is only substituted to a real path by Claude Code's
# native Skill-loading mechanism. read_skill_docs() reads the files directly
# with Path.read_text(), bypassing that entirely -- every example command in
# the upstream docs would otherwise reach the agent with a literal,
# non-existent `${CLAUDE_SKILL_DIR}` path in it. Substitute it ourselves.
_SKILL_DIR_PLACEHOLDER = "${CLAUDE_SKILL_DIR}"

# ATX heading, level 1 or 2 only (`#`/`##`). Level 3+ headings are left
# embedded in whichever level-1/2 section contains them -- nothing here
# needs to exclude at that finer granularity, and not splitting on them
# avoids having to stitch nested sections back together.
_HEADING_RE = re.compile(r"^(#{1,2})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^```")
# A line that is bold text and nothing else, e.g. "**Some Label:**" -- a
# pseudo-heading some sections use instead of a real "#"/"##" heading.
_BOLD_LINE_RE = re.compile(r"^\*\*(.+?)\*\*:?\s*$")
# A line that *starts* a new bold-led paragraph at column 0 -- no leading
# whitespace, no list marker (`-`, `  - `, etc.) before the "**". This is
# what distinguishes a standalone bold pseudo-heading/paragraph (e.g.
# "**Initiative** is always DM-rolled...") from bold text used *inside* a
# list item (e.g. "- **`roll_mode: players`**..." or the nested
# "  - **Prescribe the roll...**"), which must NOT be treated as a
# terminator since it's part of the very subsection being removed.
_BOLD_PARA_START_RE = re.compile(r"^\*\*")

# Top-level ("##") sections excluded from the prompt injection per skill
# doc file: matched by a case-insensitive prefix of the heading text (not
# line numbers, so small rewordings of the rest of the heading don't break
# this). Each is either one-time setup, pure reference material never
# needed mid-turn, or fully superseded by this project's own engine -- see
# the investigation notes in the commit that introduced this trimming.
_EXCLUDED_H2_PREFIXES: dict[str, tuple[str, ...]] = {
    "SKILL.md": (
        "guided entry",       # campaign-selection menu; engine.main resolves this before the agent starts
        "directory layout",   # pure file-location reference, not needed to narrate a scene
        "model routing",      # stale model names; the model is fixed externally by the SDK's model= param
    ),
    "SKILL-scripts.md": (
        "data commands",              # lookup.py superseded by engine.rules.lookup; sync/build are one-time
        "display companion setup",    # one-time setup; engine.main.preflight() already has the display running
        "continuity autosave",        # opt-in Stop-hook registration; this engine drives autosave itself (engine/turn_loop.py), not via a Claude Code hook
        "lazy corpus",                # administrative/maintenance (corpus_check.py), not turn-by-turn
    ),
}

# Bold pseudo-subheadings (not real "#"/"##" headings, so the H2 exclusion
# above can't reach them) that document content fully superseded by a block
# this module generates itself. Keyed by skill doc file name.
_EXCLUDED_BOLD_SUBSECTIONS: dict[str, tuple[str, ...]] = {
    # "Dice convention" documents the old `send.py --dice-request --wait`
    # protocol for PC rolls. pc_roll_tool_block() below supersedes it with
    # engine.dice, and says so explicitly -- keeping both means the agent
    # sees two competing instructions for the same decision every turn.
    "SKILL.md": ("dice convention",),
}


def cli(module: str) -> str:
    """A `python -m <module>` invocation the agent can actually run.

    The agent's cwd is the campaign root (`~/.claude/dnd`, see
    engine/agent.py), not this repo, so a bare `python3 -m engine.…` dies with
    ModuleNotFoundError. Every tool command handed to the agent therefore
    carries the repo root and the venv interpreter explicitly.
    """
    python = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)
    return f"cd {shlex.quote(str(REPO_ROOT))} && {shlex.quote(str(python))} -m {module}"


def _split_top_sections(text: str) -> list[tuple[int, str, str]]:
    """Split markdown into (level, title, block_text) chunks at level-1/2
    ATX headings, skipping anything that looks like a heading inside a
    fenced code block (a bash comment like `# note` must never be mistaken
    for a document heading -- both files are full of them).

    block_text runs from the heading line itself up to (but not including)
    the next level-1/2 heading, or EOF -- so it carries any nested level-3+
    subsections along with it intact. Content before the first heading is
    returned as a level-0, title-"" chunk.
    """
    lines = text.splitlines(keepends=True)
    boundaries: list[tuple[int, int, str]] = []
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            boundaries.append((i, len(m.group(1)), m.group(2)))
    if not boundaries:
        return [(0, "", text)]
    chunks: list[tuple[int, str, str]] = []
    if boundaries[0][0] > 0:
        chunks.append((0, "", "".join(lines[: boundaries[0][0]])))
    for idx, (line_idx, level, title) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        chunks.append((level, title, "".join(lines[line_idx:end])))
    return chunks


def _drop_bold_subsection(text: str, label_prefix: str) -> str:
    """Remove a bold pseudo-heading paragraph (a line that is exactly
    `**Label...**`) and everything through the next terminator -- whichever
    comes first of: a real heading, a horizontal rule (`---`), a bold-only
    line, or a line that *starts* a new bold paragraph at column 0 (no list
    marker before the `**`, e.g. "**Initiative** is always DM-rolled...").

    That last case matters: without it, unindented sibling paragraphs that
    immediately follow the removed subsection -- but aren't part of it --
    get swallowed too, because they don't hit any of the other terminators
    until much further down the document. Bold text *inside* a list item
    (indented, or after a leading `-`) is not a terminator, since that's
    part of the very subsection being removed here.

    Used for content that's a sub-part of a larger section we otherwise
    keep in full, so a whole-section exclusion would cut too much.
    """
    lines = text.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        m = _BOLD_LINE_RE.match(line.strip("\n"))
        if m and m.group(1).strip().casefold().startswith(label_prefix):
            start = i
            break
    if start is None:
        return text
    end = len(lines)
    for j in range(start + 1, len(lines)):
        raw = lines[j].rstrip("\n")
        stripped = raw.strip()
        if (
            stripped.startswith("#")
            or stripped == "---"
            or _BOLD_LINE_RE.match(stripped)
            or _BOLD_PARA_START_RE.match(raw)
        ):
            end = j
            break
    return "".join(lines[:start] + lines[end:])


def _trim_skill_doc(name: str, text: str) -> str:
    """Drop sections that are one-time setup, pure reference, or fully
    superseded by this project's own engine -- see _EXCLUDED_H2_PREFIXES /
    _EXCLUDED_BOLD_SUBSECTIONS for the specific list and why each is cut.
    Everything else (narration standards, dice protocol, display sync,
    per-turn combat sequence, script syntax actually used mid-turn, ...)
    passes through unchanged.
    """
    exclude_h2 = _EXCLUDED_H2_PREFIXES.get(name, ())
    kept = []
    for level, title, block in _split_top_sections(text):
        if level == 2 and any(title.strip().casefold().startswith(p) for p in exclude_h2):
            continue
        kept.append(block)
    text = "".join(kept)
    for label_prefix in _EXCLUDED_BOLD_SUBSECTIONS.get(name, ()):
        text = _drop_bold_subsection(text, label_prefix)
    return text


def read_skill_docs() -> str:
    parts = []
    for name in ("SKILL.md", "SKILL-scripts.md"):
        path = SKILL_DIR / name
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            text = text.replace(_SKILL_DIR_PLACEHOLDER, str(SKILL_DIR))
            text = _trim_skill_doc(name, text)
            parts.append(text)
    return "\n\n".join(parts)


def dice_protocol_block() -> str:
    return """## ПРОТОКОЛ ЗА ЗАРОВЕ (задължителен)

1. **Играчите хвърлят за своите герои.** НИКОГА не хвърляй вместо PC — нито
   атака, нито check, нито saving throw, нито death save. Поискай хвърлянето
   с командата от раздела „ЗАЯВКА ЗА ХВЪРЛЯНЕ НА ИГРАЧ“ по-долу и изчакай.
   Ако няма отговор, попитай на глас — не замествай с автоматичен резултат.
2. **Всяко твое хвърляне минава през скрипт с реален RNG.** Никога не
   „избирай" число, не измисляй и не ползвай средни стойности.
3. Числото, което играчът съобщава, ВИНАГИ е тоталът (зар + модификатор).
   Не добавяй модификатора втори път.
4. Natural 20 / natural 1 важат САМО за attack rolls. Ability checks и
   saving throws нямат автоматичен успех или провал.
5. Критичен удар удвоява БРОЯ на заровете за щети, не модификатора.
6. Тотал точно равен на AC — УДАР.
7. Concentration save DC = min(30, max(10, щети // 2)).
8. Формат: `КРИТИЧЕН УДАР` / `КРИТИЧЕН ПРОПУСК` / `УДАР` / `ПРОПУСК`.
9. Скритите проверки се хвърлят, но на играча се показват само наративните
   последствия.
"""


def pc_roll_tool_block() -> str:
    """The one authoritative way to ask a player for their own roll.

    The upstream skill docs (pulled in verbatim by read_skill_docs) describe
    calling `display/send.py --dice-request ... --wait` directly and claim it
    prints the player's result. It does not: send.py prints only the request
    id on stdout, and the resolved value lands in the display's text log.
    This block names the engine's own wrapper as the command to run, and says
    so explicitly, so the two instructions cannot be confused.

    _drop_bold_subsection() also strips the old "Dice convention" subsection
    out of SKILL.md, which used to carry the strongest anti-auto-roll
    warning in the whole doc ("Never fall back to dice.py ... for a PC ...
    silently auto-rolling a PC is the #1 thing players notice and
    dislike"). SKILL-scripts.md's still-present Dice Script section
    documents `dice.py ... --player <pc-name>` as normal usage -- correct
    for NPC/DM-side rolls, but nothing left in the prompt said that's wrong
    for a PC's own check/save/attack once that warning was gone. This block
    carries the warning forward explicitly instead, so the gap doesn't
    reopen.
    """
    dice_cli = cli("engine.dice")
    return f"""## ЗАЯВКА ЗА ХВЪРЛЯНЕ НА ИГРАЧ — ЕДИНСТВЕНАТА КОМАНДА

Когато на герой (PC) му трябва хвърляне, извикай през Bash:

```bash
{dice_cli} pc --character "Sylwen Nightbrook" --spec 1d20 --modifier 5 --label "Stealth check" --dc 15
{dice_cli} pc --character "Torvin Bracewell" --spec 1d20 --modifier 3 --label "Attack: боздуган" --advantage advantage
```

- `--character` е ТОЧНОТО име на героя, както е в списъка „Група“.
- Командата блокира, докато играчът хвърли на телефона си.
- На stdout се отпечатва САМО едно число — това е ТОТАЛЪТ (зар +
  модификатор). Ползвай го както е; не добавяй модификатора втори път.
- При липса на отговор отпечатва ред, започващ с `TIMEOUT:` — тогава попитай
  играча на глас. НЕ хвърляй вместо него.
- `--spec` приема само формат `NdM` (напр. `1d20`, `2d6`).

**ВАЖНО — това заменя старата инструкция от документацията на skill-а.**
Не извиквай `display/send.py --dice-request ... --wait` директно: тя
отпечатва само идентификатора на заявката, не резултата на играча.
Не ползвай и `scripts/dice.py ... --player <PC>` за хвърляне на герой —
това е автоматично хвърляне вместо играча и е точно нещото, което играчите
забелязват и не харесват най-много. `dice.py --player` е само за
проверка на маршрутизацията, никога заместител на реалното хвърляне.
За хвърляне на PC ползвай единствено `{dice_cli} pc ...`.
Твоите собствени (NPC/чудовища) хвърляния не минават оттук — за тях
`scripts/dice.py` (без `--player`) си остава правилният инструмент.
"""


def player_echo_block() -> str:
    """The display now echoes the player's action itself — the agent must not.

    The upstream skill docs (pulled in verbatim by read_skill_docs) instruct
    the agent to open every turn with `send.py --player <CharacterName>` and
    a "cleaned version" of the action ("typos corrected, intent intact"), and
    SKILL.md's per-turn combat sequence lists it as step (a). That is now
    wrong on all three counts: the display server writes the player's action
    to the permanent feed itself, the instant it is handed off, so the agent's
    copy arrives a full LLM turn late, reworded, and costs a tool call. The
    user asked explicitly for their submitted text to appear EXACTLY as
    typed, with no model reformulation spent on it.

    Styled and placed like pc_roll_tool_block(), which already supersedes an
    outdated skill-doc instruction the same way. If the model disobeys anyway,
    the display's (kind, speaker) dedup window silently absorbs the duplicate.
    """
    return """## ДЕЙСТВИЕТО НА ИГРАЧА СЕ ПОКАЗВА АВТОМАТИЧНО — НЕ ГО ПРАЩАЙ

Дисплеят вече записва действието на всеки играч в общия поток В МОМЕНТА, в
който то бъде подадено към теб — дословно, точно както играчът го е написал.

**ВАЖНО — това заменя старата инструкция от документацията на skill-а.**
НЕ извиквай `display/send.py --player ...`. Не преразказвай, не „изчиствай"
и не поправяй текста на играча — той вече е на екрана, непокътнат. Стъпка
(а) от последователността за бой („send.py --player") отпада напълно.

Започвай хода си направо от разрешаването на действието: хвърляния,
наратив, `push_stats.py`. Всичко останало в реда на блоковете остава същото
(`--dice` → наратив → `--npc` → `--tutor`).
"""


def dm_behaviour_block() -> str:
    return """## РОЛ

Ти си строг, професионален Dungeon Master за D&D 5e, издание **2024**.
Водиш по правилата на официалните източници. Не обясняваш символиката на
събитията — играчите тълкуват сами. Следвай тона на активното приключение.
Описания на сцени: 3 до 5 изречения. NPC-тата имат характер, глас и мотивация.
При 2+ играчи адресирай различни герои; ако един доминира, NPC-то се обръща
към по-мълчаливия.

## ДВА РЕЖИМА — знай в кой си

### Режим А: МОДУЛЕН (по подразбиране)
Героите са в локация, NPC или сцена, описана в приключението.
- ПЪРВО провери текста на модула, ПОСЛЕ разказвай. Не разказвай по памет.
- Не добавяй капани, врагове, съкровища или изходи, които не са в текста.
- НЕ хвърляй random encounter или trap проверки. Модулът вече е решил.
- Репликите, мотивациите и тайните на NPC-тата идват от модула.
- Ако информацията липсва: „Не виждам тази част от модула."

### Режим Б: ИМПРОВИЗИРАН
Героите са извън картираното съдържание.
- Импровизирай с „Да, и…" или „Не, но…".
- Ползвай справочните таблици за капани и плячка.
- Random проверки са разрешени.
- Вплитай елемент, който насочва обратно към сюжета — но никога не казвай
  „трябва да се върнете".

Импровизираното съдържание остава част от света. Запиши го в state.md.

## ENCOUNTER SCALING

Скалираме срещите, не героите. Никакви безплатни бонуси към AC, HP или атака.
Изчисли бюджета и XP на срещата през инструмента (виж по-долу), не наум.
При усилване, по ред на предпочитание: по-висок CR вместо повече врагове →
лидер/подкрепление → терен → +HP (максимум +50%, последна опция; никога AC
или attack бонуси). Максимум 4–5 врага наведнъж при 2 герои.

## OOC БЛОК — задължителен

В бой: в края на всеки рунд. В изследване: при смяна на локация, след почивка
и след всяко получаване на щети.

━━━━━━━━━━━━━━━━━━━━━━━━━━
OOC — СЪСТОЯНИЕ | Рунд [N]

ПАРТИТО
[Име]: HP ##/## | AC ## | [Conditions или „—"]
  Ресурси: [Hit Dice X/Y | Spell Slots 1ви: X/Y | ...]

ВРАГОВЕ
[Име]: [Невредим / Ранен / Тежко ранен / Повален]

Concentration: [Кой на какво, или „—"]
━━━━━━━━━━━━━━━━━━━━━━━━━━

- HP на враговете НИКОГА като число. Само: Невредим (100–75%),
  Ранен (74–35%), Тежко ранен (34–1%), Повален.
- AC, attack бонуси и stat blocks на враговете НЕ се показват.
- HP на героите се показва точно — играчът има право на своите числа.
- Точните числа на враговете водиш вътрешно и не ги губиш между рундовете.

## ИЗТОЧНИЦИ — приоритет

1. Активното приключение — сцени, NPC, предмети
2. Player's Handbook 2024 (PHB 2024) — правила за герои
3. Dungeon Master's Guide 2024 — водене, баланс, награди
4. Monster Manual 2025 — stat blocks
5. Вграденият SRD — бърза справка

Маркирай източника: `[Справка: DMG 2024, Chapter 4]`.

## ФОРМАТ НА ОТГОВОР

[Справка: източник]

[Описание — 3 до 5 изречения, в тона на модула]

NPC: „Реплика" [бележка за характера]

[Заявка за хвърляне към играч ИЛИ резултат от твое хвърляне]

[OOC блок, когато е приложимо]

## ЗАБРАНИ

- Не подсказвай, не улеснявай, не разкривай скрита информация
- Не хвърляй вместо играч — НИКОГА
- Не хвърляй свой зар без реален RNG — НИКОГА
- Не показвай stat blocks, AC или точни HP на враговете
- Не импровизирай съдържание, което е в модула (Режим А)
- Не блокирай играчите, когато излязат от сюжета (Режим Б)
- Способностите и ограниченията от character sheet-овете се спазват стриктно
- Не давай безплатни бонуси като компенсация за трудност
"""


def rules_tool_block() -> str:
    lookup = cli("engine.rules.lookup")
    enc = cli("engine.encounters")
    mstats = cli("engine.rules.monster_stats")
    return f"""## СПРАВКА В ПРАВИЛАТА — ползвай инструмента, не паметта

Книгите не са в контекста ти. Когато ти трябва stat block, предмет,
заклинание, капан, таблица за плячка или правило — извикай справката през
Bash и цитирай източника:

```bash
{lookup} monster "Goblin Boss"
{lookup} item "Bag of Holding"
{lookup} spell "Fireball"
{lookup} rule "grappling"
{lookup} trap --tier 1
{lookup} loot --cr 3 --kind individual
```

Бюджет и баланс на срещите:

```bash
{enc} budget --level 4 --players 2
{enc} encounter --level 4 --players 2 --monsters "Goblin Boss,Goblin Warrior,Goblin Warrior"
```

Когато импровизираш или коригираш чудовище (homebrew или адаптация) и ти
трябват реалистични целеви числа за неговия CR — AC, HP диапазон, attack
бонус, DPR диапазон, save DC — вместо да ги измисляш:

```bash
{mstats} --cr 9
{mstats} --cr 1/8
```

Никога не измисляй stat block, DC или таблица по памет. Ако справката не
върне нищо, кажи го изрично и импровизирай по стандартите на DMG 2024.
"""


def engine_contract_block() -> str:
    return """## ДОГОВОР С ДВИГАТЕЛЯ

Ти си DM-ът. Ти НЕ управляваш цикъла на игра.

- НЕ извиквай `autorun_wait.py`. Двигателят чака хода вместо теб.
- НЕ решаваш кога да се записва. Двигателят вика autosave.
- ЗАДЪЛЖИТЕЛНО прати наратива към дисплея с `send.py` в рамките на хода,
  и обнови статистиките с `push_stats.py` при всяка промяна на HP, слотове,
  състояния или инвентар.
- Един ход = един отговор. Приключи хода си, когато сцената е разказана и
  дисплеят е обновен.
"""


def build_system_prompt(cfg: Config, glossary: dict) -> str:
    blocks = [
        f"# DUNGEON MASTER — D&D 5e {cfg.ruleset}",
        read_skill_docs(),
        dm_behaviour_block(),
        dice_protocol_block(),
        pc_roll_tool_block(),
        player_echo_block(),
        rules_tool_block(),
        engine_contract_block(),
    ]
    if cfg.language == "bg":
        blocks.insert(2, glossary_prompt_block(glossary))
    return "\n\n---\n\n".join(b for b in blocks if b.strip())


def campaign_paths_block(campaign: str) -> str:
    """The resolved, absolute location of every file in the active campaign.

    The agent's Bash cwd is `campaign_root()` (see engine/agent.py) -- one
    level ABOVE the active campaign, and shared with every other campaign on
    this machine. Without this block, nothing in the turn prompt states the
    real path, so a request for a specific file (e.g. a character sheet) has
    no anchor -- observed in production as a `find / -iname ...` scan of the
    entire filesystem that alone took 68s of a 256s turn. This block gives
    the agent the real path plus the concrete filename convention so a
    filesystem search is never necessary.

    Character filenames are a slug of the real name on the sheet (lowercase,
    hyphen-separated -- see engine.state.character_name), not the name
    itself -- listing the actual files present, mapped to their real names,
    removes any need to guess or search for that mapping.
    """
    cdir = campaign_dir(campaign)
    char_dir = cdir / "characters"
    char_lines = [
        f"  characters/{path.name} — {character_name(path)}"
        for path in sorted(char_dir.glob("*.md"))
    ] if char_dir.exists() else []
    chars = "\n".join(char_lines) if char_lines else "  characters/<slug-на-име>.md"
    return f"""## ПЪТИЩА НА АКТИВНАТА КАМПАНИЯ — знаеш ги, НЕ търси файлове

Директорията на тази кампания е точно тук: `{cdir}`

  state.md, world.md, npcs.md, npcs-full.md, arc.md, world-nodes.md,
  session-log.md, source-index.md — направо в директорията по-горе
{chars}
  source/<id-на-глава>.md — изходен текст на главите от внесеното приключение

Пътищата по-горе са точни и актуални — файлите на героите вече са изредени
с реалните им имена. НИКОГА не пускай `find` по цялата файлова система или
извън тази директория, за да търсиш файл. Ако ти трябва конкретен файл,
отвори го директно на познатия път."""


def build_turn_prompt(campaign: str, actions: str) -> str:
    header = state_header(campaign)
    party = ", ".join(party_names(campaign)) or "—"
    paths = campaign_paths_block(campaign)
    return f"""{header}

{paths}

## Група
{party}

## Ходове на играчите за този рунд
{actions}

Разреши хода. Прати наратива към дисплея и обнови статистиките."""
