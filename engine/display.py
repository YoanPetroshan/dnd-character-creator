"""Bridge to the existing Flask display companion via its CLI helpers.

The display UI itself is never modified — this module only invokes
`send.py` and `push_stats.py` as subprocesses, plus one additional,
legitimate way of talking to the display's existing HTTP API directly:
`notify_thinking()` POSTs to its already-authenticated `/queue/consumed`
endpoint to trigger the "DM is thinking" indicator.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

from engine.log import log_event
from engine.state import runtime_dir

REPO_ROOT = Path(__file__).resolve().parent.parent


def skill_display_dir() -> Path:
    return REPO_ROOT / "skills" / "dnd" / "display"


def _run(argv: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as exc:
        return 1, "", str(exc)


def _run_stdin(argv: list[str], timeout: int, text: str) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv, input=text, capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except OSError as exc:
        return 1, "", str(exc)


def _send(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    argv = [sys.executable, str(skill_display_dir() / "send.py")] + args
    return _run(argv, timeout)


def _send_stdin(args: list[str], text: str, timeout: int = 30) -> tuple[int, str, str]:
    # send.py has no positional TEXT argument — text is always delivered over
    # stdin, per its own --help / docstring ("DM narration (default)").
    # Verified against the real, unmodified send.py. There is also no
    # dedicated "--system" flag: send_system() instead passes ["--tutor"],
    # which the display renders as a visually distinct collapsible parchment
    # block — the closest real styling to an out-of-band operator/system
    # notice, as opposed to plain in-character narration.
    argv = [sys.executable, str(skill_display_dir() / "send.py")] + args
    return _run_stdin(argv, timeout, text)


def send_narration(text: str) -> bool:
    code, _, err = _send_stdin([], text)
    if code != 0:
        log_event("display_send_failed", kind="narration", error=err)
    return code == 0


def send_system(text: str) -> bool:
    code, _, err = _send_stdin(["--tutor"], text)
    if code != 0:
        log_event("display_send_failed", kind="system", error=err)
    return code == 0


def push(**flags) -> bool:
    """Push a stat update. Most flags are single values; push_stats.py's
    --hp takes two (CURRENT MAX) — pass a list/tuple for those and each
    element becomes its own argv token."""
    argv = [sys.executable, str(skill_display_dir() / "push_stats.py")]
    for key, value in flags.items():
        argv.append("--" + key.replace("_", "-"))
        if isinstance(value, (list, tuple)):
            argv.extend(str(v) for v in value)
        else:
            argv.append(str(value))
    code, _, err = _run(argv, timeout=30)
    if code != 0:
        log_event("display_push_failed", error=err)
    return code == 0


def dice_request(
    character: str,
    spec: str = "1d20",
    modifier: int = 0,
    label: str = "",
    dc: int | None = None,
    advantage: str = "normal",
    wait: bool = True,
    timeout: int = 120,
) -> str | None:
    args = [
        "--dice-request",
        "--character", character,
        "--spec", spec,
        "--modifier", str(modifier),
        "--advantage", advantage,
    ]
    if label:
        args += ["--label", label]
    if dc is not None:
        args += ["--dc", str(dc)]
    if wait:
        args += ["--wait", "--wait-timeout", str(timeout)]
    code, out, err = _send(args, timeout=timeout + 15)
    log_event("dice_request", character=character, spec=spec, label=label, ok=code == 0)
    if code != 0:
        return None
    return out or None


def _read_token() -> str:
    """Read the display's auth token, mirroring
    skills/dnd/display/send.py::_read_token() exactly — same runtime-dir
    resolution (both ultimately key off DND_CAMPAIGN_ROOT / ~/.claude/dnd),
    reimplemented natively so this module doesn't import from skills/dnd/.
    """
    try:
        return (runtime_dir() / ".token").read_text().strip()
    except Exception:
        # OSError (missing/unreadable file) is the expected case, but this
        # must never be able to raise into a turn — e.g. a token file that
        # somehow isn't valid UTF-8 raises UnicodeDecodeError (a ValueError
        # subclass, not an OSError) from .read_text().
        return ""


def notify_thinking(port: int) -> bool:
    """Trigger the display's existing "DM is thinking" indicator.

    POSTs an empty JSON body to the display's already-authenticated
    `/queue/consumed` endpoint, which already broadcasts `dm_processing:
    true` — the frontend has a fully-built, currently-orphaned bouncing-dots
    indicator wired to exactly this signal. Fire-and-forget UX polish: must
    never be able to stall or break a turn, so failures are logged and
    swallowed rather than raised, and there are no retries (unlike the
    retried narration sends).
    """
    token = _read_token()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-DND-Token"] = token
    req = urllib.request.Request(
        f"http://localhost:{port}/queue/consumed",
        data=b"{}",
        headers=headers,
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception as exc:
        # Deliberately broad: OSError/urllib.error.* cover a refused or
        # timed-out connection, but a malformed response from the local
        # Flask dev server can also raise http.client.HTTPException, which
        # urllib does not wrap as a URLError. This call must never be able
        # to stall or break a turn, so any failure here is logged and
        # swallowed rather than raised.
        log_event("display_notify_thinking_failed", error=str(exc))
        return False


def is_running(port: int = 5001) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0
