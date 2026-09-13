import pytest

from engine import health


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    return tmp_path


def test_heartbeat_writes_state(root, monkeypatch):
    monkeypatch.setattr(health.display, "push", lambda **kw: True)
    health.heartbeat("thinking")
    hb = health.read_heartbeat()
    assert hb["state"] == "thinking"
    assert hb["ts"] > 0


def test_heartbeat_toggles_autorun_waiting(root, monkeypatch):
    pushed = []
    monkeypatch.setattr(health.display, "push", lambda **kw: pushed.append(kw) or True)
    health.heartbeat("waiting")
    health.heartbeat("thinking")
    assert pushed[0]["autorun_waiting"] == "true"
    assert pushed[1]["autorun_waiting"] == "false"


def test_read_heartbeat_missing_returns_empty(root):
    assert health.read_heartbeat() == {}


def test_pause_for_usage_limit_notifies_display(root, monkeypatch):
    sent = []
    slept = []
    monkeypatch.setattr(health.display, "push", lambda **kw: True)
    monkeypatch.setattr(health.display, "send_system", lambda t: sent.append(t) or True)
    monkeypatch.setattr(health.time, "sleep", lambda s: slept.append(s))
    health.pause_for_usage_limit(5, "Лимитът е достигнат.")
    assert sent and "Лимитът" in sent[0]
    assert slept == [5]
    assert health.read_heartbeat()["state"] == "paused"


def test_pause_is_sliced_not_one_monolithic_sleep(root, monkeypatch):
    """The pause runs in a worker thread, where a signal cannot reach it, so a
    single 300s sleep meant Ctrl-C was ignored for up to five minutes."""
    slept = []
    monkeypatch.setattr(health.display, "push", lambda **kw: True)
    monkeypatch.setattr(health.display, "send_system", lambda t: True)
    monkeypatch.setattr(health.time, "sleep", lambda s: slept.append(s))

    assert health.pause_for_usage_limit(300, "x") is True
    assert max(slept) <= health.PAUSE_SLICE_S
    assert sum(slept) == 300


def test_pause_cuts_itself_short_when_asked_to_stop(root, monkeypatch):
    slept = []
    monkeypatch.setattr(health.display, "push", lambda **kw: True)
    monkeypatch.setattr(health.display, "send_system", lambda t: True)
    monkeypatch.setattr(health.time, "sleep", lambda s: slept.append(s))

    stopping = {"n": 0}

    def should_stop():
        stopping["n"] += 1
        return stopping["n"] > 2  # stop requested during the third slice

    assert health.pause_for_usage_limit(300, "x", should_stop) is False
    assert sum(slept) == 2 * health.PAUSE_SLICE_S, (
        "the pause must end within one slice of the stop request, "
        "not run out the full 300s"
    )
