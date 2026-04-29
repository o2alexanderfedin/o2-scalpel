"""Tests for renderer.py — built against the locked Event contract in SPEC.md.

These tests construct Event instances directly and never invoke the parser, so
they can run in isolation while the parser agent is still working.
"""

from __future__ import annotations

import json
import re
from typing import Any

from scripts.jsonl_to_dialog.renderer import Event, RenderOptions, render


# --- helpers ----------------------------------------------------------------


def _ev(
    *,
    seq: int = 1,
    timestamp: str | None = "2026-04-28T08:00:00Z",
    role: str = "assistant",
    kind: str = "text",
    title: str = "text",
    body: str = "",
    meta: dict[str, Any] | None = None,
) -> Event:
    return Event(
        seq=seq,
        timestamp=timestamp,
        role=role,
        kind=kind,
        title=title,
        body=body,
        meta=dict(meta or {}),
    )


# --- 0. Document-header smoke + multi-event spread --------------------------


def test_document_header_starts_with_dialog_dash() -> None:
    events = [
        _ev(seq=1, role="system", kind="init", title="init",
            body="", meta={"session_id": "abc-123", "model": "claude-opus-4-7"}),
        _ev(seq=2, role="assistant", kind="thinking", title="thinking",
            body="reasoning..."),
        _ev(seq=3, role="assistant", kind="text", title="text",
            body="Hello, world."),
        _ev(seq=4, role="assistant", kind="tool_use", title="tool_use — Bash",
            body="", meta={"tool_name": "Bash", "tool_input": {"command": "ls"}}),
        _ev(seq=5, role="user", kind="tool_result",
            title="tool_result — toolu_xyz (ok)", body="output"),
        _ev(seq=6, role="result", kind="success", title="result (success)",
            body="", meta={"duration_ms": 1234}),
    ]
    out = render(events, RenderOptions(source_label="sample.jsonl"))
    assert out.startswith("# Dialog — sample.jsonl\n"), out[:80]


# --- 1. Header line exactness (SPEC test obligation 1) ----------------------


def test_header_line_exact_format() -> None:
    ev = _ev(
        seq=42,
        timestamp="2026-04-28T08:00:00Z",
        role="assistant",
        kind="text",
        title="text",
        body="hi",
    )
    out = render([ev])
    assert "### #42 · 2026-04-28T08:00:00Z · assistant · text" in out


def test_header_line_with_missing_timestamp_uses_em_dash() -> None:
    # SPEC test obligation 4
    ev = _ev(seq=7, timestamp=None, role="user", kind="text",
             title="text", body="no ts")
    out = render([ev])
    assert "### #7 · — · user · text" in out


def test_header_strips_newlines_from_title() -> None:
    # Quality bar: titles MUST NOT inject markdown via newlines.
    ev = _ev(seq=1, role="assistant", kind="text", title="line1\nline2",
             body="x")
    out = render([ev])
    # Title should appear with newline replaced by space.
    assert "### #1 · 2026-04-28T08:00:00Z · assistant · line1 line2" in out
    # And there should be no stray "line2" header on its own line.
    assert "\nline2\n" not in out.split("### ")[1].splitlines()[0]


# --- Section separators -----------------------------------------------------


def test_section_separator_is_triple_dash_surrounded_by_blank_lines() -> None:
    events = [
        _ev(seq=1, role="assistant", kind="text", title="text", body="A"),
        _ev(seq=2, role="assistant", kind="text", title="text", body="B"),
    ]
    out = render(events)
    # SPEC requires: blank line, body, blank line, ---, blank line.
    assert "\n\n---\n\n" in out


# --- 2. tool_use body: fenced ```json with pretty-printed JSON --------------


def test_tool_use_body_is_fenced_json_pretty() -> None:
    ev = _ev(
        seq=1,
        role="assistant",
        kind="tool_use",
        title="tool_use — Bash",
        body="",
        meta={
            "tool_name": "Bash",
            "tool_input": {"command": "ls", "description": "x"},
        },
    )
    out = render([ev])
    # Must contain a ```json fence
    assert "```json" in out, out
    # Extract the JSON between ```json and the closing ```
    match = re.search(r"```json\n(.*?)\n```", out, flags=re.DOTALL)
    assert match is not None, "expected ```json ... ``` block"
    parsed = json.loads(match.group(1))
    assert parsed == {"command": "ls", "description": "x"}
    # Pretty-printed: 2-space indent → expect a line that starts with two spaces.
    assert "\n  " in match.group(1), "expected 2-space indent"


# --- 3. tool_result truncation over 4000 chars ------------------------------


def test_tool_result_truncates_over_4000_chars() -> None:
    big = "x" * 5000
    ev = _ev(
        seq=1,
        role="user",
        kind="tool_result",
        title="tool_result — toolu_x (ok)",
        body=big,
    )
    out = render([ev])
    assert "... [truncated 1000 chars]" in out
    # The fenced block content must be exactly 4000 chars + truncation marker.
    match = re.search(r"```\n(.*?)\n```", out, flags=re.DOTALL)
    assert match is not None
    block = match.group(1)
    # Block layout: <4000 'x'>\n... [truncated 1000 chars]
    expected = ("x" * 4000) + "\n... [truncated 1000 chars]"
    assert block == expected, repr(block[:50] + "..." + block[-50:])


def test_tool_result_under_threshold_not_truncated() -> None:
    body = "small output"
    ev = _ev(
        seq=1,
        role="user",
        kind="tool_result",
        title="tool_result — toolu_x (ok)",
        body=body,
    )
    out = render([ev])
    assert "[truncated" not in out
    assert "small output" in out


# --- 5. Output ends with single trailing newline ----------------------------


def test_output_ends_with_single_trailing_newline() -> None:
    out = render([_ev(body="hi")])
    assert out.endswith("\n")
    assert not out.endswith("\n\n"), "trailing newlines must collapse to one"


# --- 6. Determinism ---------------------------------------------------------


def test_render_is_deterministic_byte_for_byte() -> None:
    events = [
        _ev(seq=1, role="system", kind="init", title="init",
            meta={"session_id": "s", "model": "m", "cwd": "/tmp"}),
        _ev(seq=2, role="assistant", kind="thinking", title="thinking",
            body="reasoning"),
        _ev(seq=3, role="assistant", kind="tool_use", title="tool_use — Bash",
            meta={"tool_name": "Bash",
                  "tool_input": {"command": "ls", "extra": [1, 2, 3]}}),
        _ev(seq=4, role="user", kind="tool_result",
            title="tool_result — toolu_z (ok)", body="ok"),
    ]
    a = render(events)
    b = render(events)
    assert a == b


# --- 7. <details> wrapping for thinking can be disabled ---------------------


def test_thinking_default_wrapped_in_details() -> None:
    ev = _ev(seq=1, role="assistant", kind="thinking", title="thinking",
             body="secret reasoning text")
    out = render([ev])
    assert "<details><summary>thinking</summary>" in out
    assert "</details>" in out
    assert "secret reasoning text" in out


def test_thinking_unwrapped_when_disabled() -> None:
    ev = _ev(seq=1, role="assistant", kind="thinking", title="thinking",
             body="raw reasoning")
    out = render([ev], RenderOptions(wrap_thinking=False))
    assert "<details>" not in out
    assert "raw reasoning" in out


# --- Body conventions for non-tool / non-thinking kinds ---------------------


def test_assistant_text_body_rendered_verbatim() -> None:
    ev = _ev(role="assistant", kind="text", title="text",
             body="### actual heading\n\n- bullet")
    out = render([ev])
    # Body content present unchanged.
    assert "### actual heading" in out
    assert "- bullet" in out


def test_init_body_is_meta_bullet_list() -> None:
    ev = _ev(
        seq=1,
        role="system",
        kind="init",
        title="init",
        body="",
        meta={"session_id": "abcd-1234", "model": "claude-opus-4-7",
              "cwd": "/tmp"},
    )
    out = render([ev])
    assert "- session_id: abcd-1234" in out
    assert "- model: claude-opus-4-7" in out
    assert "- cwd: /tmp" in out


def test_unknown_kind_does_not_crash_with_arbitrary_meta() -> None:
    ev = _ev(
        seq=1,
        role="unknown",
        kind="unknown",
        title="unknown",
        body="raw",
        meta={"weird_key": object()},
    )
    out = render([ev])
    assert "### #1" in out
    assert "raw" in out


# --- Empty input edge case --------------------------------------------------


def test_empty_event_list_still_renders_header() -> None:
    out = render([], RenderOptions(source_label="empty.jsonl"))
    assert out.startswith("# Dialog — empty.jsonl\n")
    assert out.endswith("\n")


# --- RenderOptions sanity ---------------------------------------------------


def test_render_options_truncate_chars_is_configurable() -> None:
    body = "y" * 100
    ev = _ev(role="user", kind="tool_result",
             title="tool_result — toolu_a (ok)", body=body)
    out = render([ev], RenderOptions(truncate_chars=50))
    assert "... [truncated 50 chars]" in out
