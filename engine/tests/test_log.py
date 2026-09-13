import pytest

from engine import log


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setenv("DND_CAMPAIGN_ROOT", str(tmp_path))
    return tmp_path


def test_log_event_writes_jsonl(root):
    log.log_event("turn_start", turn=1, campaign="demo")
    log.log_event("turn_end", turn=1, ok=True)
    events = log.read_events()
    assert [e["event"] for e in events] == ["turn_start", "turn_end"]
    assert events[0]["turn"] == 1
    assert "ts" in events[0]


def test_read_events_respects_limit(root):
    for i in range(10):
        log.log_event("tick", i=i)
    assert len(log.read_events(limit=3)) == 3
    assert log.read_events(limit=3)[-1]["i"] == 9


def test_corrupt_line_is_skipped(root):
    log.log_event("ok", n=1)
    log.log_path().open("a").write("not json\n")
    assert [e["event"] for e in log.read_events()] == ["ok"]
