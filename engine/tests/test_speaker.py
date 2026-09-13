import json
import threading

import pytest

from engine import speaker


@pytest.fixture(autouse=True)
def quiet_log(tmp_path, monkeypatch):
    """Keep log_event off the real runtime dir."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))


def test_speak_ignores_blank_text():
    assert speaker.speak("") is False
    assert speaker.speak("   \n ") is False


def test_speak_posts_narration_to_the_connector(monkeypatch):
    sent = {}
    done = threading.Event()

    def fake_post(text, base_url):
        sent["text"] = text
        sent["url"] = base_url
        done.set()
        return True

    monkeypatch.setattr(speaker, "_post_speak", fake_post)
    assert speaker.speak("Групата влиза в залата.", "http://127.0.0.1:9999")
    assert done.wait(timeout=5)
    assert sent["text"] == "Групата влиза в залата."
    assert sent["url"] == "http://127.0.0.1:9999"


def test_speak_preserves_order(monkeypatch):
    """Narration read aloud out of order would be worse than no audio."""
    seen = []
    done = threading.Event()

    def fake_post(text, base_url):
        seen.append(text)
        if len(seen) == 3:
            done.set()
        return True

    monkeypatch.setattr(speaker, "_post_speak", fake_post)
    for line in ("първо", "второ", "трето"):
        speaker.speak(line)
    assert done.wait(timeout=5)
    assert seen == ["първо", "второ", "трето"]


def test_worker_survives_a_failing_post(monkeypatch):
    calls = []
    done = threading.Event()

    def flaky(text, base_url):
        calls.append(text)
        if len(calls) == 1:
            raise OSError("connector went away")
        done.set()
        return True

    monkeypatch.setattr(speaker, "_post_speak", flaky)
    speaker.speak("едно")
    speaker.speak("две")
    assert done.wait(timeout=5), "worker died on the first failure"
    assert calls == ["едно", "две"]


def test_post_speak_sends_the_expected_body(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr(speaker.urllib.request, "urlopen", fake_urlopen)
    assert speaker._post_speak("здравей", "http://127.0.0.1:5001/") is True
    assert captured["url"] == "http://127.0.0.1:5001/speak"
    assert captured["body"] == {"text": "здравей"}


def test_post_speak_returns_false_when_the_display_is_down(monkeypatch):
    monkeypatch.setattr(
        speaker.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("connection refused")),
    )
    # A display that isn't running is a normal way to play, not an error.
    assert speaker._post_speak("здравей", speaker.resolve_url(None)) is False


def test_is_available_reports_false_without_a_display(monkeypatch):
    monkeypatch.setattr(
        speaker.urllib.request, "urlopen",
        lambda *a, **k: (_ for _ in ()).throw(OSError("refused")),
    )
    assert speaker.is_available("http://127.0.0.1:1") is False


def test_is_available_reports_true_when_health_answers(monkeypatch):
    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"ok"

    monkeypatch.setattr(speaker.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    assert speaker.is_available("http://127.0.0.1:5001") is True


# --- speech now lives in the display, not a second process ----------------


def test_resolve_url_defaults_to_the_display_port():
    """An empty local_speaker_url must follow the display, so changing the
    display port can never leave speech pointed at a dead address."""
    assert speaker.resolve_url("") == "http://127.0.0.1:5001"
    assert speaker.resolve_url(None) == "http://127.0.0.1:5001"
    assert speaker.resolve_url("", display_port=8080) == "http://127.0.0.1:8080"


def test_resolve_url_honours_an_explicit_override():
    assert speaker.resolve_url("http://elsewhere:9000", display_port=5001) == \
        "http://elsewhere:9000"


def test_post_speak_authenticates_against_the_display(tmp_path, monkeypatch):
    """The display rejects unauthenticated writes in LAN mode; the old
    standalone connector had no auth at all, so this header is new and
    load-bearing -- without it every line of narration 403s."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    rt = tmp_path / ".runtime"
    rt.mkdir(parents=True, exist_ok=True)
    (rt / ".token").write_text("sekrit\n")

    captured = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake_urlopen(req, timeout=None):
        captured["token"] = req.headers.get("X-dnd-token")
        return FakeResp()

    monkeypatch.setattr(speaker.urllib.request, "urlopen", fake_urlopen)
    assert speaker._post_speak("здравей", "http://127.0.0.1:5001") is True
    assert captured["token"] == "sekrit"


def test_post_speak_still_works_without_a_token(tmp_path, monkeypatch):
    """Localhost mode has no .token file; speech must not require one."""
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    captured = {}

    class FakeResp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b"{}"

    def fake_urlopen(req, timeout=None):
        captured["token"] = req.headers.get("X-dnd-token")
        return FakeResp()

    monkeypatch.setattr(speaker.urllib.request, "urlopen", fake_urlopen)
    assert speaker._post_speak("здравей", "http://127.0.0.1:5001") is True
    assert captured["token"] is None
