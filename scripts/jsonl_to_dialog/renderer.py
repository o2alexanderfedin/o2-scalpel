"""Renderer half of the jsonl_to_dialog tool.

Consumes a sequence of `Event` records (frozen dataclass — see SPEC.md) and
emits a deterministic Markdown document.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from .parser import Event


# --- Public options ---------------------------------------------------------


@dataclass(frozen=True)
class RenderOptions:
    """Renderer knobs.

    Attributes:
        wrap_thinking: When True (default) wrap assistant `thinking` bodies in
            a `<details><summary>thinking</summary>…</details>` block.
        truncate_chars: Max characters of a `tool_result` body before
            truncation. Surplus is replaced with `... [truncated N chars]`.
        source_label: Text after `# Dialog — ` in the document header. Pass
            the input file's basename here.
        generated_at: Optional override for the "_<count> events · … generated
            <UTC ISO>_" subtitle line. When None, the current UTC time is used.
            Tests pin this to keep output deterministic when needed.
    """

    wrap_thinking: bool = True
    truncate_chars: int = 4000
    source_label: str = "transcript"
    generated_at: str | None = None


# --- Constants --------------------------------------------------------------

_SECTION_SEPARATOR = "\n\n---\n\n"
_EM_DASH = "—"


# --- Module-level entry point ----------------------------------------------


def render(
    events: Sequence[Event],
    options: RenderOptions | None = None,
) -> str:
    """Render `events` to a Markdown string.

    Output is deterministic for a given (events, options) pair and ends with
    exactly one trailing newline.
    """

    opts = options if options is not None else RenderOptions()
    parts: list[str] = []
    parts.append(_render_document_header(events, opts))
    for ev in events:
        parts.append(_render_event(ev, opts))
    body = _SECTION_SEPARATOR.join(parts)
    # Ensure exactly one trailing newline.
    if not body.endswith("\n"):
        body += "\n"
    while body.endswith("\n\n"):
        body = body[:-1]
    return body


# --- Document header --------------------------------------------------------


def _render_document_header(events: Sequence[Event], opts: RenderOptions) -> str:
    session_ids = _collect_session_ids(events)
    sessions_str = ", ".join(session_ids) if session_ids else "no-session"
    generated = opts.generated_at or _utc_now_iso()
    subtitle = f"_{len(events)} events · {sessions_str} · generated {generated}_"
    return f"# Dialog — {opts.source_label}\n\n{subtitle}"


def _collect_session_ids(events: Sequence[Event]) -> list[str]:
    """Return de-duplicated session_ids in first-seen order (deterministic)."""
    seen: dict[str, None] = {}
    for ev in events:
        sid = ev.meta.get("session_id") if isinstance(ev.meta, Mapping) else None
        if isinstance(sid, str) and sid and sid not in seen:
            seen[sid] = None
    return list(seen.keys())


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Per-event rendering ----------------------------------------------------


def _render_event(ev: Event, opts: RenderOptions) -> str:
    header = _header_line(ev)
    body = _body_for(ev, opts)
    if body:
        return f"{header}\n\n{body}"
    return header


def _header_line(ev: Event) -> str:
    ts = ev.timestamp if ev.timestamp else _EM_DASH
    title = _sanitize_title(ev.title)
    return f"### #{ev.seq} · {ts} · {ev.role} · {title}"


def _sanitize_title(title: str) -> str:
    """Strip newlines from titles to prevent markdown injection in headers."""
    return title.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


# --- Dispatch table: (role, kind) -> body formatter -------------------------

_BodyFormatter = Callable[[Event, RenderOptions], str]


def _body_text_verbatim(ev: Event, _opts: RenderOptions) -> str:
    del _opts  # uniform formatter signature; opts unused here.
    return ev.body


def _body_thinking(ev: Event, opts: RenderOptions) -> str:
    text = ev.body
    if opts.wrap_thinking:
        return f"<details><summary>thinking</summary>\n\n{text}\n\n</details>"
    return text


def _body_tool_use(ev: Event, _opts: RenderOptions) -> str:
    del _opts  # uniform formatter signature; opts unused here.
    payload = ev.meta.get("tool_input", {})
    pretty = json.dumps(payload, indent=2, ensure_ascii=False)
    return _block("json", pretty)


def _body_tool_result(ev: Event, opts: RenderOptions) -> str:
    text = ev.body
    limit = opts.truncate_chars
    if len(text) > limit:
        truncated = len(text) - limit
        text = f"{text[:limit]}\n... [truncated {truncated} chars]"
    return _block("", text)


def _body_meta_bullets(ev: Event, _opts: RenderOptions) -> str:
    """Render a small key/value bullet list of selected meta fields.

    Used for kinds where there's no natural prose body (init, hooks, tasks,
    rate_limit, result). Keys are rendered in their dict iteration order
    (stable on CPython 3.7+) — the parser controls that order.
    """
    del _opts  # uniform formatter signature; opts unused here.
    if not isinstance(ev.meta, Mapping) or not ev.meta:
        return ev.body or ""
    lines: list[str] = []
    for key, value in ev.meta.items():
        try:
            rendered = _format_meta_value(value)
        except Exception:
            rendered = "<unrenderable>"
        lines.append(f"- {key}: {rendered}")
    return "\n".join(lines)


def _format_meta_value(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return str(value)
    if isinstance(value, (list, tuple, dict)):
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            return repr(value)
    return repr(value)


# Per (role, kind) dispatch — keep it KISS and explicit.
_FORMATTERS: dict[tuple[str, str], _BodyFormatter] = {
    ("assistant", "text"): _body_text_verbatim,
    ("assistant", "thinking"): _body_thinking,
    ("assistant", "tool_use"): _body_tool_use,
    ("user", "text"): _body_text_verbatim,
    ("user", "tool_result"): _body_tool_result,
    ("system", "init"): _body_meta_bullets,
    ("system", "hook_started"): _body_meta_bullets,
    ("system", "hook_progress"): _body_meta_bullets,
    ("system", "hook_response"): _body_meta_bullets,
    ("system", "task_started"): _body_meta_bullets,
    ("system", "task_progress"): _body_meta_bullets,
    ("system", "task_notification"): _body_meta_bullets,
    ("system", "other"): _body_meta_bullets,
    ("rate_limit", "event"): _body_meta_bullets,
    ("result", "success"): _body_meta_bullets,
    ("result", "error"): _body_meta_bullets,
}


def _body_for(ev: Event, opts: RenderOptions) -> str:
    formatter = _FORMATTERS.get((ev.role, ev.kind))
    if formatter is None:
        # Fallback for unknown / unmapped (role, kind): show body verbatim,
        # then any meta as bullets if body is empty.
        if ev.body:
            return ev.body
        return _body_meta_bullets(ev, opts)
    return formatter(ev, opts)


# --- Helpers ----------------------------------------------------------------


def _block(language: str, text: str) -> str:
    """Fence `text` in a Markdown code block. `language` may be empty."""
    fence_open = f"```{language}" if language else "```"
    return f"{fence_open}\n{text}\n```"


__all__ = ["render", "RenderOptions", "Event"]
