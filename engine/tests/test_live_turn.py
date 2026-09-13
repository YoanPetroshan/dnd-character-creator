"""Live end-to-end turn. Requires the display server running and a loaded campaign.

WARNING: this test mutates the user's REAL, LIVE campaign. It does not just
"require a loaded campaign" — it appends a permanent turn (a real Claude
Agent SDK call and its narration) to whatever campaign is currently active
via `state.active_campaign()` / `cfg.campaign`. There is no dry-run mode.

WARNING: the wait for the queued action to be picked up has no timeout on
this end (it is bounded only by whatever timeout, if any, lives inside
`serve`/`run_loop` themselves). A stuck turn can hang this test indefinitely.

WARNING: do not run this while a separate live `engine.main` process is also
running against the same campaign — both processes would race to consume the
same `.input_queue` file, and the outcome is undefined.

Run:  .venv/bin/python -m pytest engine/tests/test_live_turn.py -m live -v -s
"""
import asyncio
import json

import pytest

from engine import display, guards, state
from engine.config import Config, load_config
from engine.main import STARTUP_BANNER, resolve_campaign, serve
from engine.turn_loop import TURN_FAILED_MESSAGE

pytestmark = pytest.mark.live

# Known non-narration strings that `send_system` can push to the display
# outside of genuine turn narration. Both are themselves fluent Bulgarian,
# so on their own they would satisfy `cyrillic_ratio(last) > 0.3` -- that
# check alone cannot distinguish "the turn produced real narration" from
# "the turn produced nothing and only boilerplate reached the display".
# Note STARTUP_BANNER unconditionally appears as a *new* text-log entry on
# every serve() call, pass or fail (it fires before run_loop even starts),
# so it is expected among newly-appended entries on a genuine pass -- the
# structural signal is specifically whether the LAST entry (the one the
# language check actually inspects) is boilerplate rather than narration.
_NON_NARRATION_BOILERPLATE = {STARTUP_BANNER, TURN_FAILED_MESSAGE}


def test_one_real_turn_reaches_the_display():
    cfg = load_config()
    cfg.language = "bg"
    campaign = resolve_campaign(cfg, None)

    assert display.is_running(cfg.display_port), "start the display first"

    before = state.text_log_count()

    queue = state.runtime_dir() / ".input_queue"
    queue.write_text("[Everybody]: Оглеждам се наоколо и описвам какво виждам.")

    turns = asyncio.run(serve(cfg, campaign, max_turns=1))
    assert turns == 1

    after = state.text_log_count()
    assert after > before, "narration never reached the display"

    entries = json.loads((state.runtime_dir() / "text_log.json").read_text())

    last_entry = entries[-1]
    last_text = last_entry.get("text") if isinstance(last_entry, dict) else last_entry
    assert last_text not in _NON_NARRATION_BOILERPLATE, (
        "last text-log entry is boilerplate (startup banner or turn-failure "
        f"message), not genuine narration: {last_text!r}"
    )

    last = json.dumps(last_entry, ensure_ascii=False)
    assert guards.cyrillic_ratio(last) > 0.3, f"narration was not Bulgarian: {last[:200]}"
