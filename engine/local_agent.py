"""Ollama-backed DM agent. The local-model counterpart to engine.agent.

engine.agent.DMAgent hands Claude a persistent session and lets it run its
own Bash/Read/Write tool loop turn after turn. This agent instead makes one
stateless HTTP call per turn to a local Ollama server — no session to
resume, no filesystem access for the model itself. Continuity across turns
comes entirely from the context engine.local_prompt rebuilds each time
(state.md, the recent narration tail, the chapter excerpt), not from
conversation memory: see turn_loop.py's own module docstring, "this is what
the model can no longer forget."

Within a single turn, a short bounded back-and-forth is still needed: the
model can ask for a roll via an inline marker (see local_prompt.py), and a
real dice/display round-trip has to happen before the model can keep
narrating from the result. That loop is entirely local to run_turn().
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from engine import dice, display, guards, local_context
from engine.agent import TurnResult
from engine.config import DEFAULT_LOCAL_HOST, DEFAULT_LOCAL_MODEL, Config
from engine.log import log_event
from engine.rules import lookup

MAX_ROLL_ITERATIONS = 4
_MARKER_RE = re.compile(r"\[(ROLL|ATTACK|DMROLL|DAMAGE|HEAL|LOOKUP)\|([^\]\n]*)\]")
_LOOKUP_KINDS = {"monster", "item", "spell", "rule", "trap", "hazard", "reward", "loot", "any"}
_LOOKUP_MAX_CHARS = 900

# A sentence ends at .!?… followed by whitespace. Used to decide when enough
# text has streamed in to be worth showing the player -- see _emit_point().
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s")
# Paragraph break: the natural block boundary in this model's own output.
_PARAGRAPH_BREAK = "\n\n"
# How much of a chunk's opening has to match an already-shown one for it to
# count as a repeat. Long enough that two genuinely different sentences
# won't collide, short enough to catch a restatement that drifts after its
# opening clause -- which is the shape the repetition actually takes.
_REPEAT_PREFIX_CHARS = 45
_WS_RE = re.compile(r"\s+")


def _trim_to_last_sentence(buf: str, already_emitted: int) -> str:
    """Cut a length-truncated reply back to its last finished sentence.

    Hitting `num_predict` stops generation wherever it lands, which for
    Bulgarian narration means mid-word. Dropping the severed tail is better
    than showing it -- but never below what the player has already been
    shown, since that text cannot be taken back off the display.
    """
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(buf)]
    cut = max((e for e in ends if e >= already_emitted), default=None)
    if cut is not None:
        return buf[:cut].rstrip()
    # No sentence finished after the last flush: drop the severed remainder
    # rather than flushing it. Unless nothing was flushed at all, in which
    # case a partial line still beats an empty turn.
    return buf[:already_emitted].rstrip() if already_emitted else buf


def _repeat_key(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip().casefold())[:_REPEAT_PREFIX_CHARS]


def _parse_signed_int(raw: str, default: int = 0) -> int:
    raw = (raw or "").strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _parse_dc(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw or raw == "-":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _split_at_marker(text: str) -> tuple[str, tuple[str, str] | None]:
    """(text before the first marker, (kind, body)) — or (whole text, None)."""
    m = _MARKER_RE.search(text)
    if not m:
        return text, None
    return text[: m.start()], (m.group(1), m.group(2))


class _LanguageDrift(Exception):
    """Raised inside the stream gate when the first chunk isn't Bulgarian, so
    the round can be retried before anything reaches the player."""


def _safe_emit_limit(buf: str, start: int) -> int:
    """How far into `buf` it is safe to show the player, from `start`.

    Never past an opening `[` that has no `]` yet: that is a marker still
    being generated, and half a `[ROLL|Sylwen|1d2` must never reach the
    display. Everything before it is ordinary narration and is fine to show.
    """
    idx = buf.find("[", start)
    while idx != -1:
        if buf.find("]", idx) == -1:
            return idx
        idx = buf.find("[", idx + 1)
    return len(buf)


def _emit_point(buf: str, start: int, first_emission: bool) -> int:
    """Index up to which `buf[start:]` should be flushed to the player now,
    or `start` for "not yet".

    Two rules, both measured rather than guessed (see
    docs/superpowers/plans/2026-08-22-local-latency-optimisation.md):

    * The FIRST flush of a round goes out as soon as one sentence is
      complete. Time-to-first-word is the metric that matters -- the player
      was previously staring at a bouncing-dots indicator for the whole
      turn -- and one sentence is the smallest unit that reads as finished.
    * After that, flush on paragraph breaks only. Every flush becomes its
      own block on the display (with its own divider and TTS bar), so
      flushing per sentence thereafter would shred one narrative beat into
      a column of fragments. The model already writes in paragraphs; this
      follows its own structure.
    """
    limit = _safe_emit_limit(buf, start)
    window = buf[start:limit]
    if not window.strip():
        return start

    if first_emission:
        m = _SENTENCE_END_RE.search(window)
        if m:
            return start + m.end()
        return start

    idx = window.rfind(_PARAGRAPH_BREAK)
    if idx != -1:
        return start + idx + len(_PARAGRAPH_BREAK)
    return start


def _lookup_text(kind: str, name: str, max_chars: int = _LOOKUP_MAX_CHARS) -> str:
    """The same reference text engine.rules.lookup's CLI would print — called
    directly (no subprocess) since the model has no Bash access here."""
    kind = (kind or "").strip().lower()
    if kind not in _LOOKUP_KINDS:
        kind = "any"
    entry = lookup.find(name, kind=None if kind == "any" else kind)
    if entry is None and kind in ("spell", "any"):
        text = lookup.srd_fallback(name, "spell" if kind == "spell" else None)
        if text:
            return text[:max_chars]
    if entry is None:
        return f"Няма запис за „{name}“ ({kind}). Импровизирай по стандартите на DMG 2024."
    rec = lookup.fetch_record(entry)
    if rec is None:
        return f"Индексът сочи към липсващ запис за „{name}“."
    return lookup.format_record(entry, rec)[:max_chars]


def _apply_pc_damage(campaign: str, character: str, damage: int) -> str | None:
    """Persist damage to a PC's sheet and push the new HP to the display.

    Returns a short " → HP x/y" suffix on success, or None if the character
    couldn't be found (caller decides how to degrade — see ATTACK/DAMAGE).
    """
    applied = local_context.apply_hp_delta(campaign, character, -abs(damage))
    if applied is None:
        return None
    new_current, max_hp = applied
    display.push(player=character, hp=[new_current, max_hp])
    return f" → {character}: HP {new_current}/{max_hp}"


def _resolve_marker(kind: str, body: str, campaign: str) -> tuple[bool, str] | None:
    """Run the requested roll/lookup/HP-change for real.

    Returns (visible, outcome_text), or None for a marker that doesn't
    parse — callers treat that the same as "no marker": a 4B model's output
    isn't trustworthy enough to let a malformed request crash or stall a
    turn. `visible` distinguishes dice outcomes (shown to the player, 🎲
    prefixed) from LOOKUP reference text (informs the model's next reply
    only — a raw stat block is DM reference material, not something a
    player should see dumped into the narration).
    """
    fields = body.split("|")
    try:
        if kind == "ROLL" and len(fields) >= 6:
            character, spec, mod, label, dc_raw, adv = (f.strip() for f in fields[:6])
            dc = _parse_dc(dc_raw)
            modifier = _parse_signed_int(mod)
            adv = adv if adv in ("advantage", "disadvantage") else "normal"
            total = dice.request_pc_roll(character, spec, modifier, label, dc, adv)
            if total is None:
                return True, f"{character}: няма отговор навреме — попитай на глас."
            outcome = f"{character}: {spec}{mod} = {total}"
            if dc is not None:
                outcome += f" vs DC {dc} — " + ("УСПЕХ" if total >= dc else "ПРОВАЛ")
            return True, outcome

        if kind == "ATTACK" and len(fields) >= 6:
            attacker, atk_mod, target_ac, num_dice, die, dmg_mod = (
                f.strip() for f in fields[:6]
            )
            target_pc = fields[6].strip() if len(fields) >= 7 else "-"
            result = dice.enemy_attack(
                attacker, _parse_signed_int(atk_mod), int(target_ac),
                int(num_dice), int(die), _parse_signed_int(dmg_mod),
            )
            line = result["line"]
            if target_pc and target_pc != "-" and result["damage"] > 0:
                suffix = _apply_pc_damage(campaign, target_pc, result["damage"])
                if suffix:
                    line += suffix
            return True, line

        if kind == "DMROLL" and len(fields) >= 4:
            spec, mod, label, dc_raw = (f.strip() for f in fields[:4])
            modifier = _parse_signed_int(mod)
            adv = "normal"
            if len(fields) >= 5 and fields[4].strip() in ("advantage", "disadvantage"):
                adv = fields[4].strip()
            r = dice.roll_d20(modifier=modifier, advantage=adv)
            dc = _parse_dc(dc_raw)
            outcome = f"{label}: {r.detail}"
            if dc is not None:
                outcome += f" vs DC {dc} — " + ("УСПЕХ" if r.total >= dc else "ПРОВАЛ")
            return True, outcome

        if kind == "DAMAGE" and len(fields) >= 2:
            character, amount_raw = fields[0].strip(), fields[1].strip()
            label = fields[2].strip() if len(fields) >= 3 else ""
            amount = abs(int(amount_raw))
            applied = local_context.apply_hp_delta(campaign, character, -amount)
            if applied is None:
                return None
            new_current, max_hp = applied
            display.push(player=character, hp=[new_current, max_hp])
            tail = f" ({label})" if label else ""
            return True, f"{character}: -{amount} HP{tail} → {new_current}/{max_hp}"

        if kind == "HEAL" and len(fields) >= 2:
            character, amount_raw = fields[0].strip(), fields[1].strip()
            label = fields[2].strip() if len(fields) >= 3 else ""
            amount = abs(int(amount_raw))
            applied = local_context.apply_hp_delta(campaign, character, amount)
            if applied is None:
                return None
            new_current, max_hp = applied
            display.push(player=character, hp=[new_current, max_hp])
            tail = f" ({label})" if label else ""
            return True, f"{character}: +{amount} HP{tail} → {new_current}/{max_hp}"

        if kind == "LOOKUP" and len(fields) >= 2:
            lookup_kind, name = fields[0].strip(), fields[1].strip()
            if name:
                return False, _lookup_text(lookup_kind, name)
    except (ValueError, KeyError, TypeError) as exc:
        log_event("local_marker_malformed", kind=kind, body=body[:200], error=str(exc))
        return None
    log_event("local_marker_malformed", kind=kind, body=body[:200], error="field count")
    return None


@dataclass
class LocalDMAgent:
    """One Ollama chat model, called fresh (no session) each turn."""

    cfg: Config
    system_prompt: str
    campaign: str
    host: str = DEFAULT_LOCAL_HOST
    model: str = DEFAULT_LOCAL_MODEL
    num_ctx: int = 8192
    temperature: float = 0.7
    request_timeout_s: int = 120
    # How long Ollama keeps the model in memory after a request.
    #
    # Deliberately finite. `-1` (forever) is faster in principle, but it
    # pins ~3.1GB of an 8GB machine and only releases if stop() actually
    # runs -- which it does not after a crash, a `kill -9`, or a closed
    # terminal window. Observed on this machine: free memory down to 0.1GB
    # with the model held after the engine was gone.
    #
    # 30 minutes covers any realistic gap between turns at a table (the
    # 5-minute default did not -- that eviction cost a measured 11.1s
    # reload) while self-healing if the engine dies without cleaning up.
    keep_alive: str = "30m"
    # Upper bound on tokens per round -- a runaway guard, NOT a budget.
    #
    # This was 220, chosen from English-ish token counts measured during the
    # latency work, and it cut real Bulgarian narration off mid-word at the
    # table ("...какво крият тези петна и листове. Тър"). Cyrillic is far
    # less token-efficient under this tokenizer -- roughly 2 chars/token
    # against 4 for English -- so a normal 3-5 sentence Bulgarian scene
    # description lands near 300 tokens, comfortably over the old cap.
    # 512 leaves real headroom while still bounding a model that will not
    # stop. `_chat` additionally trims to the last complete sentence if the
    # cap is ever reached, so the player never sees a severed word.
    num_predict: int = 512
    # Called with narration text as it streams, so the display can show the
    # scene mid-turn instead of after it. None = no incremental push (the
    # original behaviour; turn_loop's own fallback then pushes at the end).
    on_narration: object = None
    # Called once, after the turn, with the list of blocks that were pushed.
    # Exists because streaming changes what the display's TTS cache keys ARE:
    # the player now clicks a speaker button per block, so pre-warming the
    # whole turn's text (what turn_loop does for the Claude path) would warm
    # a key nothing ever asks for. See engine/tts_trigger.py's normaliser.
    on_turn_end: object = None
    _ready: bool = field(default=False, init=False, repr=False)

    async def start(self) -> None:
        try:
            req = urllib.request.Request(f"{self.host}/api/version", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
            self._ready = True
        except (urllib.error.URLError, OSError) as exc:
            log_event("local_agent_unreachable", host=self.host, error=str(exc))
            self._ready = False
            return
        self._warm_up()

    def _warm_up(self) -> None:
        """Load the model and prime its prefix cache before the first turn.

        Two costs the player would otherwise pay on their opening action,
        both measured: ~11s to load an evicted model, and ~2.9s of prompt
        eval for the system prompt (vs ~1.3s once its prefix is cached).
        Spending them at engine startup instead is free -- the display is
        still being opened and nobody has typed anything yet.

        Best-effort and time-boxed: a slow or unreachable backend must delay
        the first turn, never prevent the engine from starting.
        """
        started = time.time()
        try:
            payload = self._payload(
                [{"role": "system", "content": self.system_prompt},
                 {"role": "user", "content": "Готов ли си?"}],
                stream=False,
            )
            payload["options"] = dict(payload["options"], num_predict=1)
            with self._post(payload) as resp:
                resp.read()
            log_event("local_agent_warm", seconds=round(time.time() - started, 1))
        except Exception as exc:  # noqa: BLE001 -- startup must not fail on this
            log_event("local_agent_warmup_failed", error=str(exc))

    async def stop(self) -> None:
        """Release the model immediately rather than waiting out keep_alive.

        Best-effort: a failure here costs idle RAM until Ollama's own
        timeout reclaims it, which must never be allowed to break shutdown.
        """
        self._ready = False
        try:
            payload = {"model": self.model, "messages": [], "keep_alive": 0}
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.host}/api/chat", data=data,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception as exc:  # noqa: BLE001 -- shutdown must not raise
            log_event("local_agent_release_failed", error=str(exc))

    def _payload(self, messages: list[dict], stream: bool) -> dict:
        options = {"num_ctx": self.num_ctx, "temperature": self.temperature}
        if self.num_predict:
            options["num_predict"] = self.num_predict
        return {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            # Hybrid-reasoning models (e.g. Qwen3.5) default to an extended
            # "thinking" pass that isn't bounded by anything relevant to a
            # one-sentence reply -- observed directly generating 2000+ tokens
            # of chain-of-thought for "say one short sentence" and never
            # stopping inside a 150s window. This app only ever wants the
            # final narration text, never the reasoning trace, so thinking
            # is always off. Models without a thinking mode (BgGPT/Gemma)
            # just ignore the field.
            "think": False,
            # Keep the model resident between turns. Ollama's default is 5
            # minutes, and a real table regularly spends longer than that
            # between turns (reading, arguing, rolling) -- measured, that
            # eviction costs 11.1s of reload on the very next turn. Released
            # again in stop(), so the 3.1GB isn't pinned after the game ends.
            "keep_alive": self.keep_alive,
            "options": options,
        }

    def _post(self, payload: dict):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat", data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        return urllib.request.urlopen(req, timeout=self.request_timeout_s)

    def _chat(self, messages: list[dict], on_text=None) -> str:
        """One completion. Returns the full reply text.

        When `on_text` is given, the reply is streamed and `on_text(chunk)`
        is called with narration as it becomes readable, so the player sees
        the scene while the model is still writing it (and, in the roll
        loop, while the phone is still waiting for their die). Without it,
        this is an ordinary blocking completion.

        Streaming also lets the round stop the moment a complete marker
        appears, rather than reading out a reply whose tail would be
        discarded anyway.
        """
        if on_text is None:
            with self._post(self._payload(messages, stream=False)) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return (body.get("message") or {}).get("content", "")

        buf = ""
        emitted = 0
        truncated = False
        with self._post(self._payload(messages, stream=True)) as resp:
            for line in resp:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                buf += (event.get("message") or {}).get("content", "")

                point = _emit_point(buf, emitted, first_emission=emitted == 0)
                if point > emitted:
                    chunk = buf[emitted:point]
                    emitted = point
                    if chunk.strip():
                        on_text(chunk)

                if event.get("done"):
                    # "length" means num_predict cut generation off wherever
                    # it happened to be -- mid-word, in practice.
                    truncated = event.get("done_reason") == "length"
                    break
                if _MARKER_RE.search(buf):
                    break

        if truncated:
            log_event("local_agent_output_truncated",
                      num_predict=self.num_predict, chars=len(buf))
            buf = _trim_to_last_sentence(buf, emitted)

        # Flush whatever narration is left, minus any marker (which is the
        # engine's instruction, never the player's text).
        prefix, _ = _split_at_marker(buf)
        if len(prefix) > emitted and prefix[emitted:].strip():
            on_text(prefix[emitted:])
        return buf

    def _chat_checked(self, messages: list[dict], on_text=None) -> str:
        """_chat(), with one corrective retry if the reply drifted off-language.

        A 4B model asked for Bulgarian narration sometimes answers in
        English anyway — observed directly against this backend, not a
        theoretical worry. engine.guards already has the language check
        turn_loop uses to just log-and-flag for Claude; a local model drifts
        often enough that a flag alone isn't good enough, so this retries
        once with an explicit nudge before giving up and returning whatever
        it got (turn_loop's own guard still flags a persistent failure).

        Checks only the narration prefix, before any roll marker: the
        marker syntax itself is (deliberately) English protocol keywords
        plus whatever the character's own name is, so language-checking the
        raw reply as a whole makes a marker-ending reply falsely look
        English-drifted.

        Streaming makes the ordering load-bearing: text already pushed to
        the display cannot be taken back, so the FIRST chunk is gated on the
        language check and nothing reaches the player until it passes. A
        reply that starts Bulgarian and drifts later is kept and logged
        rather than retried — retrying it would leave the opening of a scene
        on screen twice.
        """
        emitted = {"any": False}

        def gated(chunk: str) -> None:
            if not emitted["any"]:
                if self.cfg.language == "bg" and not guards.check_language(chunk, expect="bg"):
                    raise _LanguageDrift()
                emitted["any"] = True
            on_text(chunk)

        try:
            reply = self._chat(messages, gated if on_text is not None else None)
        except _LanguageDrift:
            reply = ""
        else:
            prefix, _ = _split_at_marker(reply)
            if self.cfg.language != "bg" or guards.check_language(prefix, expect="bg"):
                return reply
            if emitted["any"]:
                log_event("local_agent_language_drift_kept",
                          ratio=round(guards.cyrillic_ratio(prefix), 3))
                return reply
            log_event("local_agent_language_retry",
                      ratio=round(guards.cyrillic_ratio(prefix), 3))

        nudge = messages + [{
            "role": "user",
            "content": "ВАЖНО: предният отговор не беше на български. "
                       "Напиши го наново — ИЗЦЯЛО на български език.",
        }]
        retry = self._chat(nudge, on_text)
        if not guards.check_language(retry, expect="bg"):
            log_event("local_agent_language_retry_failed",
                      ratio=round(guards.cyrillic_ratio(retry), 3))
        return retry

    async def run_turn(self, turn_prompt: str) -> TurnResult:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": turn_prompt},
        ]
        parts: list[str] = []
        # Every chunk the player has already been shown, so the turn's final
        # text can be assembled without the display having to be re-pushed
        # (turn_loop's fallback sees the log already changed and stands down).
        push = self.on_narration
        shown: list[str] = []
        seen_keys: set[str] = set()

        def show(chunk: str) -> None:
            # Drop a beat the player has already been given this turn.
            # Observed in a real streamed turn: the model restated the same
            # sentence across three consecutive rounds, which on the display
            # is clutter but through the Bulgarian audio connector means
            # hearing the same line read out three times. The prompt-side
            # fix (see `grounding` below) reduces this; the guard makes it
            # invisible when it happens anyway.
            key = _repeat_key(chunk)
            if key and key in seen_keys:
                log_event("local_agent_repeat_suppressed", chars=len(chunk))
                return
            if key:
                seen_keys.add(key)
            # Trailing newline is load-bearing, not cosmetic: the display's
            # typewriter drops the block's last <p> in flushNewBlock() before
            # the TTS bar reads its text, so a chunk that doesn't end on a
            # newline loses its final line from the spoken audio.
            block = chunk if chunk.endswith("\n") else chunk + "\n"
            shown.append(block)
            try:
                push(block)
            except Exception as exc:  # noqa: BLE001 -- display must not break a turn
                log_event("local_agent_push_failed", error=str(exc))

        for _ in range(MAX_ROLL_ITERATIONS):
            try:
                reply = self._chat_checked(messages, show if push else None)
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
                log_event("local_agent_request_failed", error=str(exc))
                return TurnResult(ok=False, error=f"local_backend_error: {exc}")

            prefix, marker = _split_at_marker(reply)
            parts.append(prefix.strip())
            if marker is None:
                break

            resolved = _resolve_marker(*marker, self.campaign)
            if resolved is None:
                # Malformed marker: drop it rather than showing raw bracket
                # syntax to the player — the clean prefix (already appended
                # above) is what's kept, the turn just ends a little short.
                log_event("local_marker_dropped", kind=marker[0], body=marker[1][:200])
                break

            visible, outcome = resolved
            messages.append({"role": "assistant", "content": reply})
            # A repeated across-the-turn reminder, not just a one-time system
            # prompt line: observed directly that a small model drifts further
            # from the original scene/state with each additional round-trip in
            # a turn (inventing unrelated plot beats a few rounds in) unless
            # re-grounded every time, not just once at the start.
            # Both halves are load-bearing, and the second was added after
            # watching a real turn read the same sentence aloud three times:
            # telling a small model only to "stay in the same scene" invites
            # it to restate that scene instead of advancing it.
            grounding = (
                "Остани в СЪЩАТА сцена от контекста по-горе — не въвеждай "
                "нови места, герои или обрати, които не са поискани. "
                "НЕ преразказвай и НЕ повтаряй нищо, което вече си написал "
                "в този ход — продължи напред от мястото, докъдето стигна."
            )
            if visible:
                # A dice outcome: part of the story, shown to the player.
                parts.append(f"\n🎲 {outcome}\n")
                if push:
                    show(f"🎲 {outcome}")
                messages.append({
                    "role": "user",
                    "content": f"Резултат от хвърлянето: {outcome}\n"
                                "Продължи наратива директно от този резултат. "
                                "Не повтаряй числото буквално, разкажи какво се случва. "
                                + grounding,
                })
            else:
                # A rules lookup: DM-only reference, never shown verbatim.
                messages.append({
                    "role": "user",
                    "content": f"Справка от правилата: {outcome}\n"
                                "Продължи наратива, ползвайки тази информация точно, "
                                "но НЕ показвай суровия текст на играча — само разказ. "
                                + grounding,
                })
        else:
            log_event("local_agent_roll_loop_exhausted", turns=MAX_ROLL_ITERATIONS)

        if self.on_turn_end is not None and shown:
            # Hand over exactly the blocks the player can now click a speaker
            # button on. Deliberately AFTER the turn, never during it: local
            # TTS runs slower than real-time on this machine and would be
            # competing with the model for the same GPU mid-turn.
            try:
                self.on_turn_end(list(shown))
            except Exception as exc:  # noqa: BLE001 -- never break a finished turn
                log_event("local_agent_turn_end_hook_failed", error=str(exc))

        text = "\n".join(p for p in parts if p).strip()
        return TurnResult(ok=bool(text), text=text)
