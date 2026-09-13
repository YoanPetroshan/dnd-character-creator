"""Engine settings, persisted as JSON next to the campaign runtime files."""
from __future__ import annotations

import dataclasses
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONTENT_ROOT = str(Path.home() / "Documents" / "DND content")
# This engine is 2024-only by design: the rules module, the encounter budgets
# and the prompt header all encode that edition. Keeping the set here makes
# cfg.ruleset the single source of truth — engine.main pins the same value
# into state.md, so the prompt and the state file cannot disagree.
SUPPORTED_RULESETS = ("2024",)
# "claude" is the original Claude Agent SDK backend (engine.agent.DMAgent);
# "local" is this fork's offline backend (engine.local_agent.LocalDMAgent),
# talking to a local Ollama server instead of the Claude API.
SUPPORTED_BACKENDS = ("claude", "local")
DEFAULT_LOCAL_HOST = "http://127.0.0.1:11434"
# qwen3.5:4b over todorov/bggpt:Gemma-3-4B-IT-Q4_K_M: compared head-to-head
# (same 3 scenarios, same harness, 2026-08-22 — see README-LOCAL.md) it fired
# the marker protocol correctly far more consistently (5/6 across two runs vs
# BgGPT's 1/3) and responded noticeably faster, at the cost of rougher (but
# still readable) Bulgarian than the Bulgarian-tuned BgGPT. Set
# local_model="todorov/bggpt:Gemma-3-4B-IT-Q4_K_M" to trade back for polish.
DEFAULT_LOCAL_MODEL = "qwen3.5:4b"


@dataclass
class Config:
    language: str = "bg"
    ruleset: str = "2024"
    backend: str = "local"
    turn_model: str = "claude-sonnet-5"
    heavy_model: str = "claude-opus-5"
    local_host: str = DEFAULT_LOCAL_HOST
    local_model: str = DEFAULT_LOCAL_MODEL
    local_num_ctx: int = 8192
    # Stream narration to the display as the model writes it, instead of
    # pushing the whole turn once it finishes. Set False to fall back to the
    # original end-of-turn push (see engine/local_agent.py's on_narration).
    local_stream: bool = True
    # Speak narration aloud in Bulgarian as the model writes it. Handled by
    # the display companion itself (POST /speak), which synthesises through
    # the same tts.py the per-block speaker button uses and plays it in the
    # display's own browser tab -- no separate process, port or tab.
    # Empty (the default) means "the display", resolved from display_port;
    # this stays configurable only so an unusual setup can point speech
    # somewhere else.
    local_speak: bool = True
    local_speaker_url: str = ""
    turn_timeout_s: int = 180
    turn_retries: int = 1
    autosave_every: int = 5
    display_port: int = 5001
    lan: bool = True
    # Pre-warm the display's TTS cache with the narration text as soon as a
    # turn succeeds, so the player's speaker-button click plays instantly
    # instead of waiting on a cold synthesis. Pure latency optimisation —
    # turning it off costs only that latency, never correctness.
    tts_prewarm: bool = True
    campaign: str | None = None
    content_root: str = DEFAULT_CONTENT_ROOT

    def __post_init__(self) -> None:
        if self.ruleset not in SUPPORTED_RULESETS:
            raise ValueError(
                f"unsupported ruleset {self.ruleset!r}; "
                f"this engine supports only {', '.join(SUPPORTED_RULESETS)}"
            )
        if self.backend not in SUPPORTED_BACKENDS:
            raise ValueError(
                f"unsupported backend {self.backend!r}; "
                f"this fork supports only {', '.join(SUPPORTED_BACKENDS)}"
            )


def campaign_root() -> Path:
    return Path(os.environ.get("DND_CAMPAIGN_ROOT", str(Path.home() / ".claude" / "dnd")))


def content_root_path() -> Path:
    return Path(os.environ.get("DND_CONTENT_ROOT", DEFAULT_CONTENT_ROOT))


def json_dir() -> Path:
    return content_root_path() / "JSON"


def rules_index_path() -> Path:
    return campaign_root() / ".rules" / "index.json"


def default_config_path() -> Path:
    return campaign_root() / ".runtime" / "engine_config.json"


def load_config(path: Path | None = None) -> Config:
    path = path or default_config_path()
    if not path.exists():
        return Config()
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return Config()
    known = {f.name for f in dataclasses.fields(Config)}
    values = {k: v for k, v in raw.items() if k in known}
    ruleset = values.get("ruleset")
    if ruleset is not None and ruleset not in SUPPORTED_RULESETS:
        # Don't discard every other saved setting over one bad value, and
        # don't let it reach state.md either — warn and use the default.
        print(f"config: unsupported ruleset {ruleset!r} in {path}; "
              f"using {Config.ruleset!r}", file=sys.stderr)
        values.pop("ruleset")
    return Config(**values)


def save_config(cfg: Config, path: Path | None = None) -> None:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataclasses.asdict(cfg), indent=2, ensure_ascii=False))
