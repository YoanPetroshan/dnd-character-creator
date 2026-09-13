"""Tests for engine/tts_trigger.py.

Two things need proving:

1. `_browser_normalize()` really does reproduce the browser's
   `_ttsExtractText()` pipeline (templates/index.html) for both the DM and
   NPC block shapes — a cache-key mismatch here silently doubles synthesis
   load instead of raising, so these are worth pinning down explicitly.
2. `prewarm_tts()` never raises, under every failure mode the real HTTP call
   can produce (refused connection, timeout, HTTP error, malformed local
   response, a non-UTF-8 token file) — it is called via
   `asyncio.create_task(asyncio.to_thread(...))` and never awaited by
   `turn_loop.run_once()`, so an exception here would surface as, at best,
   an "exception was never retrieved" warning, and at worst break the turn.
"""
from __future__ import annotations

import http.client
import socket
import urllib.error

import pytest

from engine import tts_trigger


# ─── _strip_inline_md / _browser_normalize ─────────────────────────────────

def test_strip_inline_md_bold():
    assert tts_trigger._strip_inline_md("това е **важно** нещо") == "това е важно нещо"


def test_strip_inline_md_italic():
    assert tts_trigger._strip_inline_md("*шепнешком*") == "шепнешком"


def test_strip_inline_md_unterminated_delimiter_kept_literal():
    """_mdParseInline (templates/index.html) pushes an unterminated `*`/`**`
    as a literal character instead of consuming it — narration legitimately
    contains lone asterisks (e.g. footnote-style markers), and treating them
    as an opened-but-never-closed span would silently eat the rest of the
    line."""
    assert tts_trigger._strip_inline_md("3 * 4 = 12") == "3 * 4 = 12"
    assert tts_trigger._strip_inline_md("почти **готово") == "почти **готово"


def test_strip_inline_md_no_backtick_or_underscore_handling():
    """The real _mdParseInline has no backtick or underscore branch — only
    `**` and `*`. An earlier draft of this work assumed otherwise, which
    would have corrupted the cache key for narration containing `_` or `` ` ``."""
    assert tts_trigger._strip_inline_md("`code`") == "`code`"
    assert tts_trigger._strip_inline_md("some_var_name") == "some_var_name"


def test_browser_normalize_dm_lines_join_without_separator():
    """textContent of <p>a</p><p>b</p> is 'ab', not 'a b' -- sibling <p>
    elements introduce no separator. This is the single highest-value
    assertion in this file: get it wrong and the cache misses on almost
    every real multi-line turn.

    Trailing '\\n' so the (dropped) last line is the empty string, isolating
    this test from the last-line-drop behavior covered separately below."""
    text = "Първи ред.\nВтори ред.\n"
    assert tts_trigger._browser_normalize(text) == "Първи ред.Втори ред."


def test_browser_normalize_dm_blank_lines_contribute_nothing():
    text = "Първи ред.\n\nВтори ред.\n"
    assert tts_trigger._browser_normalize(text) == "Първи ред.Втори ред."


def test_browser_normalize_dm_untrimmed_lines_collapse_via_final_pass():
    """Lines are NOT individually trimmed on the DM path -- only the final
    /\\s+/ collapse + .trim() cleans things up. A line's own trailing spaces
    must not survive as literal double-spaces in the middle of the result."""
    text = "Ред с интервали   \nВтори ред\n"
    assert tts_trigger._browser_normalize(text) == "Ред с интервали Втори ред"


def test_browser_normalize_dm_strips_markdown_delimiters():
    text = "**Тъмнина** обгръща залата.\n"
    assert tts_trigger._browser_normalize(text) == "Тъмнина обгръща залата."


def test_browser_normalize_dm_drops_last_line_when_no_trailing_newline():
    """flushNewBlock() removes `currentCursor` -- the block's LAST <p> --
    before _ttsExtractText() ever reads textContent, on the browser's live
    typewriter path. So a narration that does NOT end in '\\n' loses its
    final line entirely from what the browser actually sends to /tts; this
    was verified by replaying real campaign narration entries. A trailing
    '\\n' (see other tests in this file) produces an empty last "line",
    which is what actually gets dropped, so real content survives."""
    text = "Първи ред.\nВторият ред отпада."
    assert tts_trigger._browser_normalize(text) == "Първи ред."


def test_browser_normalize_dm_single_line_no_trailing_newline_is_fully_dropped():
    """A single-line narration with no trailing '\\n' has exactly one <p>,
    which IS `currentCursor` -- so it is entirely removed by flushNewBlock()
    and the browser sends nothing at all for it. Reproduced faithfully here,
    matching the browser's actual (if surprising) behavior."""
    assert tts_trigger._browser_normalize("Какво правите?") == ""


def test_browser_normalize_npc_lines_trimmed_and_blanks_skipped():
    text = "  Спри натам!  \n\n  Няма да мине.  "
    got = tts_trigger._browser_normalize(text, npc_name="Стражът")
    assert got == "СтражътСпри натам!Няма да мине."


def test_browser_normalize_npc_does_not_strip_markdown():
    """renderNPCBlock() (templates/index.html) assigns p.textContent = trimmed
    directly -- it never runs _mdParseInline for NPC lines, unlike the DM
    path. Stripping ** here would diverge from the browser's real
    textContent for any NPC line with a literal asterisk."""
    got = tts_trigger._browser_normalize("Внимавай **сега**!", npc_name="Стражът")
    assert got == "СтражътВнимавай **сега**!"


def test_browser_normalize_strips_ctrl_and_csi_and_tab():
    text = "Ред1\x1b[31mцветен\x1b[0m\tтекст\r\nРед2\n"
    got = tts_trigger._browser_normalize(text)
    assert "\x1b" not in got
    assert "\r" not in got
    # \t becomes two spaces (mid-line, collapsed to one by the final \s+
    # pass); the \n line break itself still joins with NO separator, same as
    # the plain multi-line case above.
    assert got == "Ред1цветен текстРед2"


def test_browser_normalize_truncates_to_2000_chars():
    text = "а" * 3000 + "\n"
    got = tts_trigger._browser_normalize(text)
    assert len(got) == tts_trigger.MAX_TEXT_CHARS


def test_browser_normalize_empty_text_is_empty_string():
    assert tts_trigger._browser_normalize("") == ""
    assert tts_trigger._browser_normalize(None) == ""  # type: ignore[arg-type]


# ─── prewarm_tts: success path ──────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, status=200, body=b"ok", cache=None):
        self.status = status
        self._body = body
        # Mirrors http.client.HTTPResponse.headers (an email.message.Message),
        # which prewarm_tts reads via .get("X-Audio-Cache") for observability.
        self.headers = {"X-Audio-Cache": cache} if cache else {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def isolated_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    monkeypatch.delenv("DND_RUNTIME_DIR", raising=False)
    return tmp_path


def test_prewarm_tts_success_returns_true_and_posts_normalized_text(isolated_runtime, monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = req.data
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return _FakeResponse(status=200)

    monkeypatch.setattr(tts_trigger.urllib.request, "urlopen", fake_urlopen)

    # Trailing '\n' -- see test_browser_normalize_dm_lines_join_without_separator
    # for why: it isolates this from the last-line-drop behavior so both real
    # lines survive normalization.
    ok = tts_trigger.prewarm_tts("Първи ред.\nВтори ред.\n", display_port=5001)

    assert ok is True
    assert captured["url"] == "http://localhost:5001/tts"
    assert captured["method"] == "POST"
    import json
    body = json.loads(captured["body"])
    # No separator between lines -- see test_browser_normalize_dm_lines_join_without_separator.
    assert body["text"] == "Първи ред.Втори ред."
    assert body["prewarm"] is True


def test_prewarm_tts_logs_cache_hit_miss_from_response_header(isolated_runtime, monkeypatch):
    """The display sets X-Audio-Cache: hit|miss on every /tts response.
    Without reading and logging it, a prewarm hit-rate regression (e.g. the
    voice-key mismatch or the normalization drift both fixed alongside this)
    is invisible in production -- there is nothing to grep in engine.log to
    tell a hit from a miss."""
    logged = []
    monkeypatch.setattr(tts_trigger, "log_event", lambda event, **fields: logged.append((event, fields)))
    monkeypatch.setattr(
        tts_trigger.urllib.request, "urlopen",
        lambda req, timeout=None: _FakeResponse(status=200, cache="hit"),
    )
    ok = tts_trigger.prewarm_tts("Здравей.\n", display_port=5001)

    assert ok is True
    assert ("tts_prewarm", {"cache": "hit", "chars": len("Здравей.")}) in logged


def test_prewarm_tts_includes_token_header_when_token_file_exists(isolated_runtime, monkeypatch):
    (isolated_runtime / ".runtime").mkdir(parents=True, exist_ok=True)
    (isolated_runtime / ".runtime" / ".token").write_text("secret-token-value")

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.header_items())
        return _FakeResponse(status=200)

    monkeypatch.setattr(tts_trigger.urllib.request, "urlopen", fake_urlopen)
    # Trailing '\n' so normalization doesn't drop this (single-line-only)
    # text entirely -- see test_browser_normalize_dm_single_line_no_trailing_newline_is_fully_dropped.
    ok = tts_trigger.prewarm_tts("Здравей.\n", display_port=5001)

    assert ok is True
    # urllib title-cases header names it's given via add_header/Request(headers=...)
    assert captured["headers"].get("X-dnd-token") == "secret-token-value"


def test_prewarm_tts_no_token_file_omits_header_but_still_succeeds(isolated_runtime, monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.header_items())
        return _FakeResponse(status=200)

    monkeypatch.setattr(tts_trigger.urllib.request, "urlopen", fake_urlopen)
    ok = tts_trigger.prewarm_tts("Здравей.\n", display_port=5001)

    assert ok is True
    assert "X-dnd-token" not in captured["headers"]


def test_prewarm_tts_passes_voice_when_given(isolated_runtime, monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["body"] = req.data
        return _FakeResponse(status=200)

    monkeypatch.setattr(tts_trigger.urllib.request, "urlopen", fake_urlopen)
    tts_trigger.prewarm_tts("Здравей.\n", display_port=5001, voice="Enceladus")

    import json
    body = json.loads(captured["body"])
    assert body["voice"] == "Enceladus"


def test_prewarm_tts_empty_normalized_text_short_circuits_without_a_request(isolated_runtime, monkeypatch):
    called = []
    monkeypatch.setattr(
        tts_trigger.urllib.request, "urlopen",
        lambda req, timeout=None: called.append(1) or _FakeResponse(),
    )
    ok = tts_trigger.prewarm_tts("   \n\n  ", display_port=5001)
    assert ok is False
    assert called == []


# ─── prewarm_tts: every failure mode is swallowed, never raised ───────────

def _raiser(exc):
    def _fake_urlopen(req, timeout=None):
        raise exc
    return _fake_urlopen


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.URLError("connection refused"),
        socket.timeout("timed out"),
        urllib.error.HTTPError("http://x", 500, "boom", {}, None),
        http.client.BadStatusLine("garbage"),
        ConnectionResetError("reset"),
        ValueError("something else entirely"),
    ],
    ids=["refused", "timeout", "http-error", "malformed-response", "reset", "unexpected"],
)
def test_prewarm_tts_swallows_every_failure_mode_and_returns_false(isolated_runtime, monkeypatch, exc):
    monkeypatch.setattr(tts_trigger.urllib.request, "urlopen", _raiser(exc))
    # Must not raise.
    ok = tts_trigger.prewarm_tts("Здравей, свят.\n", display_port=5001)
    assert ok is False


def test_prewarm_tts_logs_on_failure(isolated_runtime, monkeypatch):
    logged = []
    monkeypatch.setattr(tts_trigger, "log_event", lambda event, **fields: logged.append((event, fields)))
    monkeypatch.setattr(
        tts_trigger.urllib.request, "urlopen", _raiser(urllib.error.URLError("refused")),
    )
    tts_trigger.prewarm_tts("Здравей, свят.\n", display_port=5001)
    assert logged
    assert logged[0][0] == "tts_prewarm_failed"


def test_prewarm_tts_non_2xx_status_returns_false_without_raising(isolated_runtime, monkeypatch):
    monkeypatch.setattr(
        tts_trigger.urllib.request, "urlopen",
        lambda req, timeout=None: _FakeResponse(status=500),
    )
    ok = tts_trigger.prewarm_tts("Здравей, свят.\n", display_port=5001)
    assert ok is False


# ─── _read_token: the documented UnicodeDecodeError case ──────────────────

def test_read_token_non_utf8_file_returns_empty_string_not_raise(isolated_runtime):
    (isolated_runtime / ".runtime").mkdir(parents=True, exist_ok=True)
    (isolated_runtime / ".runtime" / ".token").write_bytes(b"\xff\xfe not valid utf-8 \xff")
    # Must not raise UnicodeDecodeError.
    assert tts_trigger._read_token() == ""


def test_prewarm_tts_survives_non_utf8_token_file(isolated_runtime, monkeypatch):
    (isolated_runtime / ".runtime").mkdir(parents=True, exist_ok=True)
    (isolated_runtime / ".runtime" / ".token").write_bytes(b"\xff\xfe bad \xff")

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["headers"] = dict(req.header_items())
        return _FakeResponse(status=200)

    monkeypatch.setattr(tts_trigger.urllib.request, "urlopen", fake_urlopen)
    ok = tts_trigger.prewarm_tts("Здравей.\n", display_port=5001)

    assert ok is True
    assert "X-dnd-token" not in captured["headers"]


# --- serial pre-warm queue (streaming backend) ----------------------------

def test_queue_prewarm_processes_blocks_in_order(monkeypatch):
    import threading
    from engine import tts_trigger

    seen = []
    done = threading.Event()

    def fake_prewarm(text, port, voice=None):
        seen.append(text)
        if len(seen) == 3:
            done.set()
        return True

    monkeypatch.setattr(tts_trigger, "prewarm_tts", fake_prewarm)
    accepted = tts_trigger.queue_prewarm(["едно\n", "две\n", "три\n"], 5001)
    assert accepted == 3
    assert done.wait(timeout=5), "worker did not drain the queue"
    assert seen == ["едно\n", "две\n", "три\n"]


def test_queue_prewarm_skips_blank_blocks(monkeypatch):
    from engine import tts_trigger

    monkeypatch.setattr(tts_trigger, "prewarm_tts", lambda *a, **k: True)
    assert tts_trigger.queue_prewarm(["", "   \n", "\n"], 5001) == 0


def test_queue_prewarm_survives_a_failing_synthesis(monkeypatch):
    import threading
    from engine import tts_trigger

    calls = []
    done = threading.Event()

    def flaky(text, port, voice=None):
        calls.append(text)
        if len(calls) == 1:
            raise OSError("tts backend down")
        done.set()
        return True

    monkeypatch.setattr(tts_trigger, "prewarm_tts", flaky)
    tts_trigger.queue_prewarm(["първо\n", "второ\n"], 5001)
    assert done.wait(timeout=5), "worker died on the first failure"
    assert calls == ["първо\n", "второ\n"]
