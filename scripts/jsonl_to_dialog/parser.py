"""JSONL transcript -> list[Event] parser for jsonl_to_dialog.

Source of truth: scripts/jsonl_to_dialog/SPEC.md (frozen Event contract +
closed Kinds set + robustness rules). This module owns parsing only; it has
no dependency on the renderer half.

Resolved SPEC ambiguities (pinned here so the renderer half can rely on them):
  - Title em-dash: SPEC's title-conventions table uses em-dash (U+2014). We
    emit em-dashes verbatim; the renderer can re-format if it prefers.
  - Timestamp source for assistant/user fan-out: when the message-level dict
    has no `timestamp`, we look at the outer envelope's `timestamp`. If neither
    has one, all fan-out events share `timestamp=None`.
  - tool_result body: the LSP/SDK sometimes emits `content` as a list of
    blocks ([{"type":"text","text":"..."}]). We flatten to a single string
    by concatenating any block whose `type` is "text" (others stringified).
  - "task_id short": the parser stores the FULL `task_id` in `meta["task_id"]`
    and uses the first 8 chars in the title (the renderer may override).
  - Hook `output` / `stdout` collisions: real fixtures duplicate `output`
    and `stdout`. We prefer `output` when populating the body, falling back
    to `stdout` then `stderr`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional


# ---------------------------------------------------------------------------
# Frozen Event contract (matches SPEC verbatim; do NOT change without
# coordinating with the renderer half).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Event:
    seq: int
    timestamp: Optional[str]
    role: str
    kind: str
    title: str
    body: str
    meta: dict[str, Any]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(path: "str | os.PathLike[str]") -> list[Event]:
    """Parse a UTF-8 JSONL transcript file into a list of Events."""
    with open(path, "r", encoding="utf-8") as fh:
        return parse_lines(fh)


def parse_lines(lines: Iterable[str]) -> list[Event]:
    """Parse an iterable of raw JSONL lines into a list of Events.

    `seq` is assigned in emission order (1-based, monotonic across the whole
    stream, including assistant fan-out blocks).
    """
    counter = _SeqCounter()
    out: list[Event] = []
    for raw in lines:
        out.extend(_parse_one(raw, counter))
    return out


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

class _SeqCounter:
    """Tiny mutable counter so fan-out helpers can grab the next seq."""

    def __init__(self) -> None:
        self._n = 0

    def next(self) -> int:
        self._n += 1
        return self._n


_MAX_RAW_BODY = 200  # SPEC: malformed-line raw body capped at 200 chars


def _parse_one(raw: str, counter: _SeqCounter) -> list[Event]:
    """Convert a single line into 0+ Events.

    Empty / whitespace-only lines yield no events. Malformed JSON yields a
    single `unknown` event with `meta.parse_error`.
    """
    line = raw.rstrip("\n").rstrip("\r")
    if not line.strip():
        return []

    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:
        return [Event(
            seq=counter.next(),
            timestamp=None,
            role="unknown",
            kind="unknown",
            title="unknown",
            body=line[:_MAX_RAW_BODY],
            meta={"parse_error": str(exc)},
        )]

    if not isinstance(obj, dict):
        # Top-level JSON value that isn't an object -> treat as unknown.
        return [Event(
            seq=counter.next(),
            timestamp=None,
            role="unknown",
            kind="unknown",
            title="unknown",
            body=line[:_MAX_RAW_BODY],
            meta={"parse_error": "top-level value is not an object"},
        )]

    kind_dispatch = {
        "system": _parse_system,
        "assistant": _parse_assistant,
        "user": _parse_user,
        "rate_limit_event": _parse_rate_limit,
        "result": _parse_result,
    }
    raw_type = obj.get("type")
    type_key = raw_type if isinstance(raw_type, str) else ""
    handler = kind_dispatch.get(type_key, _parse_unknown)
    return handler(obj, counter)


# -- timestamp / meta helpers -------------------------------------------------

def _extract_timestamp(obj: dict[str, Any]) -> Optional[str]:
    """Pull timestamp from the outer envelope (or message dict if absent)."""
    ts = obj.get("timestamp")
    if isinstance(ts, str):
        return ts
    msg = obj.get("message")
    if isinstance(msg, dict):
        inner = msg.get("timestamp")
        if isinstance(inner, str):
            return inner
    return None


def _pick(obj: dict[str, Any], *keys: str) -> dict[str, Any]:
    """Return a new dict with only the listed keys that are present + non-None."""
    out: dict[str, Any] = {}
    for k in keys:
        v = obj.get(k)
        if v is not None:
            out[k] = v
    return out


# -- system -------------------------------------------------------------------

_SYSTEM_KINDS = {
    "init",
    "hook_started",
    "hook_progress",
    "hook_response",
    "task_started",
    "task_progress",
    "task_notification",
}


def _parse_system(obj: dict[str, Any], counter: _SeqCounter) -> list[Event]:
    subtype = obj.get("subtype", "")
    kind = subtype if subtype in _SYSTEM_KINDS else "other"
    ts = _extract_timestamp(obj)

    if kind == "init":
        return [_build_system_init(obj, counter, ts)]
    if kind in {"hook_started", "hook_progress", "hook_response"}:
        return [_build_system_hook(obj, counter, ts, kind)]
    if kind in {"task_started", "task_progress", "task_notification"}:
        return [_build_system_task(obj, counter, ts, kind)]

    # "other"
    meta = _pick(obj, "subtype", "session_id", "uuid")
    return [Event(
        seq=counter.next(),
        timestamp=ts,
        role="system",
        kind="other",
        title=f"system ({subtype or 'unknown'})",
        body="",
        meta=meta,
    )]


def _build_system_init(obj: dict[str, Any], counter: _SeqCounter,
                       ts: Optional[str]) -> Event:
    meta = _pick(obj, "session_id", "model", "cwd", "permissionMode",
                  "claude_code_version", "output_style", "uuid",
                  "apiKeySource")
    return Event(
        seq=counter.next(),
        timestamp=ts,
        role="system",
        kind="init",
        title="init",
        body="",
        meta=meta,
    )


def _build_system_hook(obj: dict[str, Any], counter: _SeqCounter,
                       ts: Optional[str], kind: str) -> Event:
    hook_name = obj.get("hook_name", "")
    title = f"{kind} — {hook_name}" if hook_name else kind
    if kind == "hook_response":
        exit_code = obj.get("exit_code")
        if exit_code is not None:
            title = f"{title} (exit {exit_code})"

    body = ""
    for key in ("output", "stdout", "stderr"):
        candidate = obj.get(key)
        if isinstance(candidate, str) and candidate:
            body = candidate
            break

    meta = _pick(obj, "hook_id", "hook_name", "hook_event", "exit_code",
                  "outcome", "stdout", "stderr", "session_id", "uuid")
    return Event(
        seq=counter.next(),
        timestamp=ts,
        role="system",
        kind=kind,
        title=title,
        body=body,
        meta=meta,
    )


def _build_system_task(obj: dict[str, Any], counter: _SeqCounter,
                       ts: Optional[str], kind: str) -> Event:
    task_id = obj.get("task_id", "")
    short = task_id[:8] if isinstance(task_id, str) else ""
    title = f"{kind} — {short}" if short else kind
    body = ""
    for key in ("description", "message", "step", "stdout"):
        candidate = obj.get(key)
        if isinstance(candidate, str) and candidate:
            body = candidate
            break
    meta = _pick(obj, "task_id", "description", "step", "message",
                  "session_id", "uuid")
    return Event(
        seq=counter.next(),
        timestamp=ts,
        role="system",
        kind=kind,
        title=title,
        body=body,
        meta=meta,
    )


# -- assistant ---------------------------------------------------------------

def _parse_assistant(obj: dict[str, Any], counter: _SeqCounter) -> list[Event]:
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return _parse_unknown(obj, counter)
    ts = _extract_timestamp(obj)
    message_id = msg.get("id", "")
    common_meta_base: dict[str, Any] = {}
    if message_id:
        common_meta_base["message_id"] = message_id
    if isinstance(msg.get("model"), str):
        common_meta_base["model"] = msg["model"]
    sess = obj.get("session_id")
    if isinstance(sess, str):
        common_meta_base["session_id"] = sess

    content = msg.get("content")
    if not isinstance(content, list):
        # No fan-out possible -> emit a single unknown placeholder.
        return [Event(
            seq=counter.next(),
            timestamp=ts,
            role="assistant",
            kind="text",
            title="text",
            body="" if not isinstance(content, str) else content,
            meta=common_meta_base,
        )]

    events: list[Event] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        events.append(_assistant_block_to_event(block, counter, ts, common_meta_base))
    return events


def _assistant_block_to_event(block: dict[str, Any], counter: _SeqCounter,
                              ts: Optional[str], base_meta: dict[str, Any]) -> Event:
    btype = block.get("type")
    meta = dict(base_meta)
    if btype == "thinking":
        raw_thinking = block.get("thinking", "")
        if isinstance(raw_thinking, str):
            body = raw_thinking
        else:
            body = json.dumps(block, ensure_ascii=False)
            meta["coerced_from_non_string"] = True
        return Event(
            seq=counter.next(),
            timestamp=ts,
            role="assistant",
            kind="thinking",
            title="thinking",
            body=body,
            meta=meta,
        )
    if btype == "text":
        raw_text = block.get("text", "")
        if isinstance(raw_text, str):
            body = raw_text
        else:
            body = json.dumps(block, ensure_ascii=False)
            meta["coerced_from_non_string"] = True
        return Event(
            seq=counter.next(),
            timestamp=ts,
            role="assistant",
            kind="text",
            title="text",
            body=body,
            meta=meta,
        )
    if btype == "tool_use":
        tool_name = block.get("name", "")
        tool_input = block.get("input", {})
        if not isinstance(tool_input, dict):
            tool_input = {"_raw": tool_input}
        meta["tool_name"] = tool_name
        meta["tool_use_id"] = block.get("id", "")
        meta["tool_input"] = tool_input
        title = f"tool_use — {tool_name}" if tool_name else "tool_use"
        return Event(
            seq=counter.next(),
            timestamp=ts,
            role="assistant",
            kind="tool_use",
            title=title,
            body="",  # renderer formats the JSON
            meta=meta,
        )
    # Unknown assistant block type -> generic text-ish event with raw payload
    meta["block_type"] = btype
    return Event(
        seq=counter.next(),
        timestamp=ts,
        role="assistant",
        kind="text",
        title="text",
        body=json.dumps(block, ensure_ascii=False),
        meta=meta,
    )


# -- user ---------------------------------------------------------------------

def _parse_user(obj: dict[str, Any], counter: _SeqCounter) -> list[Event]:
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return _parse_unknown(obj, counter)
    ts = _extract_timestamp(obj)
    base_meta: dict[str, Any] = {}
    sess = obj.get("session_id")
    if isinstance(sess, str):
        base_meta["session_id"] = sess

    content = msg.get("content")
    if isinstance(content, str):
        return [Event(
            seq=counter.next(),
            timestamp=ts,
            role="user",
            kind="text",
            title="text",
            body=content,
            meta=base_meta,
        )]

    if not isinstance(content, list):
        # Top-level non-string, non-list content: render the whole message dict
        # as JSON and tag the coercion (don't lose the data via repr).
        coerced_meta = dict(base_meta)
        coerced_meta["coerced_from_non_string"] = True
        return [Event(
            seq=counter.next(),
            timestamp=ts,
            role="user",
            kind="text",
            title="text",
            body=json.dumps(msg, ensure_ascii=False),
            meta=coerced_meta,
        )]

    events: list[Event] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        events.append(_user_block_to_event(block, counter, ts, base_meta))
    return events


def _user_block_to_event(block: dict[str, Any], counter: _SeqCounter,
                         ts: Optional[str], base_meta: dict[str, Any]) -> Event:
    btype = block.get("type")
    meta = dict(base_meta)
    if btype == "tool_result":
        raw_tool_use_id = block.get("tool_use_id")
        tool_use_id = raw_tool_use_id if isinstance(raw_tool_use_id, str) and raw_tool_use_id else ""
        meta["tool_use_id"] = tool_use_id
        is_error = bool(block.get("is_error", False))
        meta["is_error"] = is_error
        body = _flatten_tool_result_content(block.get("content"))
        status = "error" if is_error else "ok"
        title_id = tool_use_id if tool_use_id else "?"
        title = f"tool_result — {title_id} ({status})"
        return Event(
            seq=counter.next(),
            timestamp=ts,
            role="user",
            kind="tool_result",
            title=title,
            body=body,
            meta=meta,
        )
    if btype == "text":
        raw_text = block.get("text", "")
        if isinstance(raw_text, str):
            body = raw_text
        else:
            body = json.dumps(block, ensure_ascii=False)
            meta["coerced_from_non_string"] = True
        return Event(
            seq=counter.next(),
            timestamp=ts,
            role="user",
            kind="text",
            title="text",
            body=body,
            meta=meta,
        )
    # Unknown user block type
    meta["block_type"] = btype
    return Event(
        seq=counter.next(),
        timestamp=ts,
        role="user",
        kind="text",
        title="text",
        body=json.dumps(block, ensure_ascii=False),
        meta=meta,
    )


def _flatten_tool_result_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            else:
                parts.append(json.dumps(block, ensure_ascii=False))
        return "\n".join(parts)
    if content is None:
        return ""
    return json.dumps(content, ensure_ascii=False)


# -- rate_limit / result / unknown -------------------------------------------

def _parse_rate_limit(obj: dict[str, Any], counter: _SeqCounter) -> list[Event]:
    ts = _extract_timestamp(obj)
    info = obj.get("rate_limit_info")
    meta: dict[str, Any] = {}
    if isinstance(info, dict):
        for k in ("status", "rateLimitType", "resetsAt", "overageStatus",
                  "isUsingOverage", "overageDisabledReason"):
            if k in info and info[k] is not None:
                meta[k] = info[k]
    sess = obj.get("session_id")
    if isinstance(sess, str):
        meta["session_id"] = sess
    status = meta.get("status", "unknown")
    return [Event(
        seq=counter.next(),
        timestamp=ts,
        role="rate_limit",
        kind="event",
        title=f"rate_limit (status={status})",
        body="",
        meta=meta,
    )]


def _parse_result(obj: dict[str, Any], counter: _SeqCounter) -> list[Event]:
    ts = _extract_timestamp(obj)
    raw_subtype = obj.get("subtype")
    subtype = raw_subtype if isinstance(raw_subtype, str) else ""
    if subtype in {"success", "error"}:
        kind = subtype
        title = f"result ({kind})"
    else:
        kind = "other"
        title = f"result ({subtype or 'unknown'})"
    meta = _pick(obj, "subtype", "session_id", "duration_ms", "num_turns",
                  "error", "uuid")
    body = ""
    if isinstance(obj.get("error"), str):
        body = obj["error"]
    return [Event(
        seq=counter.next(),
        timestamp=ts,
        role="result",
        kind=kind,
        title=title,
        body=body,
        meta=meta,
    )]


def _parse_unknown(obj: dict[str, Any], counter: _SeqCounter) -> list[Event]:
    return [_parse_unknown_inline(obj, counter, _extract_timestamp(obj))]


def _parse_unknown_inline(obj: dict[str, Any], counter: _SeqCounter,
                          ts: Optional[str]) -> Event:
    meta = _pick(obj, "type", "session_id", "uuid")
    raw = json.dumps(obj, ensure_ascii=False)
    return Event(
        seq=counter.next(),
        timestamp=ts,
        role="unknown",
        kind="unknown",
        title="unknown",
        body=raw[:_MAX_RAW_BODY],
        meta=meta,
    )


__all__ = ["Event", "parse_file", "parse_lines"]
