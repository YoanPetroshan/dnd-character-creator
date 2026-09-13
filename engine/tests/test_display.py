import http.client
import urllib.error

import pytest

import engine.display as display
from engine.state import runtime_dir


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    return tmp_path


def test_dice_request_builds_expected_argv(monkeypatch):
    captured = {}

    def fake_run(argv, timeout):
        captured["argv"] = argv
        return (0, "17", "")

    monkeypatch.setattr(display, "_run", fake_run)
    out = display.dice_request(
        character="Falin", spec="1d20", modifier=3, label="Initiative", dc=15
    )
    argv = captured["argv"]
    assert "--dice-request" in argv
    assert argv[argv.index("--character") + 1] == "Falin"
    assert argv[argv.index("--spec") + 1] == "1d20"
    assert argv[argv.index("--modifier") + 1] == "3"
    assert argv[argv.index("--label") + 1] == "Initiative"
    assert argv[argv.index("--dc") + 1] == "15"
    assert "--wait" in argv
    assert out == "17"


def test_dice_request_without_wait_omits_flag(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        display, "_run", lambda argv, timeout: (captured.setdefault("argv", argv), (0, "", ""))[1]
    )
    display.dice_request(character="Falin", wait=False)
    assert "--wait" not in captured["argv"]


def test_push_expands_a_list_value_into_multiple_argv_tokens(monkeypatch):
    captured = {}

    def fake_run(argv, timeout):
        captured["argv"] = argv
        return (0, "", "")

    monkeypatch.setattr(display, "_run", fake_run)
    display.push(player="Torvin", hp=[7, 12])
    argv = captured["argv"]
    i = argv.index("--hp")
    assert argv[i + 1 : i + 3] == ["7", "12"]
    assert argv[argv.index("--player") + 1] == "Torvin"


def test_push_passes_a_scalar_value_as_one_argv_token(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        display, "_run", lambda argv, timeout: (captured.setdefault("argv", argv), (0, "", ""))[1]
    )
    display.push(player="Torvin", second_wind="false")
    argv = captured["argv"]
    assert argv[argv.index("--second-wind") + 1] == "false"


def test_send_narration_passes_text(monkeypatch):
    # send.py has no positional TEXT arg and no --system flag (verified against
    # the real, unmodified CLI's --help / argparse setup) — plain narration is
    # delivered over stdin, not via argv. See engine/display.py::_send_stdin.
    captured = {}

    def fake_run_stdin(argv, timeout, text):
        captured["argv"] = argv
        captured["text"] = text
        return (0, "", "")

    monkeypatch.setattr(display, "_run_stdin", fake_run_stdin)
    assert display.send_narration("Мракът се сгъстява.") is True
    assert captured["text"] == "Мракът се сгъстява."
    assert "Мракът се сгъстява." not in captured["argv"]


def test_send_narration_reports_failure(monkeypatch):
    monkeypatch.setattr(display, "_run_stdin", lambda argv, timeout, text: (1, "", "boom"))
    assert display.send_narration("x") is False


def test_send_system_uses_tutor_flag(monkeypatch):
    # send_system() must render as a visually distinct block (collapsible
    # parchment via --tutor), not blend into plain in-character narration —
    # confirmed via the real send.py --help and its handling of --tutor.
    captured = {}

    def fake_run_stdin(argv, timeout, text):
        captured["argv"] = argv
        captured["text"] = text
        return (0, "", "")

    monkeypatch.setattr(display, "_run_stdin", fake_run_stdin)
    assert display.send_system("DM is online.") is True
    assert "--tutor" in captured["argv"]
    assert captured["text"] == "DM is online."


def test_read_token_returns_file_contents(root):
    (runtime_dir() / ".token").write_text("secret-token\n")
    assert display._read_token() == "secret-token"


def test_read_token_missing_file_returns_empty(root):
    assert display._read_token() == ""


def test_read_token_non_utf8_returns_empty(root):
    # .read_text() raises UnicodeDecodeError (a ValueError subclass, not an
    # OSError) on invalid UTF-8 — must be swallowed, not propagate.
    (runtime_dir() / ".token").write_bytes(b"\xff\xfe\x00bad")
    assert display._read_token() == ""


def test_notify_thinking_posts_to_queue_consumed_with_token(root, monkeypatch):
    (runtime_dir() / ".token").write_text("secret-token")
    captured = {}

    def fake_urlopen(req, timeout=None, context=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return None

    monkeypatch.setattr(display.urllib.request, "urlopen", fake_urlopen)
    assert display.notify_thinking(5001) is True
    assert captured["url"] == "http://localhost:5001/queue/consumed"
    assert captured["headers"].get("X-dnd-token") == "secret-token"
    assert captured["timeout"] is not None and captured["timeout"] <= 3


def test_notify_thinking_missing_token_still_posts(root, monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None, context=None):
        captured["headers"] = dict(req.header_items())
        return None

    monkeypatch.setattr(display.urllib.request, "urlopen", fake_urlopen)
    assert display.notify_thinking(5001) is True
    assert "X-dnd-token" not in captured["headers"]


def test_notify_thinking_transport_error_returns_false(root, monkeypatch):
    def fake_urlopen(req, timeout=None, context=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(display.urllib.request, "urlopen", fake_urlopen)
    assert display.notify_thinking(5001) is False


def test_notify_thinking_oserror_returns_false(root, monkeypatch):
    def fake_urlopen(req, timeout=None, context=None):
        raise OSError("boom")

    monkeypatch.setattr(display.urllib.request, "urlopen", fake_urlopen)
    assert display.notify_thinking(5001) is False


def test_notify_thinking_http_exception_returns_false(root, monkeypatch):
    # http.client.HTTPException (e.g. a malformed response from getresponse())
    # is NOT wrapped as OSError/URLError by urllib — the catch must be broad
    # enough to still swallow it, since this call must never break a turn.
    def fake_urlopen(req, timeout=None, context=None):
        raise http.client.HTTPException("bad status line")

    monkeypatch.setattr(display.urllib.request, "urlopen", fake_urlopen)
    assert display.notify_thinking(5001) is False
