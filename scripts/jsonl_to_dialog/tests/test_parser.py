"""Tests for the jsonl_to_dialog parser.

Covers SPEC.md "Test obligations -> test_parser.py" (items 1-7) plus the
extra obligations the parser-half contract calls out:
    - parse_file(path) returns a list[Event]
    - real-excerpt fixture parses without exception (>=7 events)
    - fan-out for msg_test_001 -> [thinking, text, tool_use]
    - tool_use / tool_result meta plumbing
    - hook + init meta plumbing
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.jsonl_to_dialog.parser import Event, parse_file, parse_lines


FIXTURES = Path(__file__).parent / "fixtures"
REAL_EXCERPT = FIXTURES / "real_excerpt.jsonl"
EDGE_CASES = FIXTURES / "edge_cases.jsonl"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _msg_events(events: list[Event], message_id: str) -> list[Event]:
    return [e for e in events if e.meta.get("message_id") == message_id]


# ---------------------------------------------------------------------------
# Public API shape
# ---------------------------------------------------------------------------

def test_parse_file_returns_list_of_events() -> None:
    events = parse_file(REAL_EXCERPT)
    assert isinstance(events, list)
    assert all(isinstance(e, Event) for e in events)


def test_event_dataclass_has_all_seven_fields() -> None:
    e = Event(
        seq=1,
        timestamp=None,
        role="system",
        kind="other",
        title="x",
        body="y",
        meta={},
    )
    # frozen
    with pytest.raises(Exception):
        e.seq = 2  # type: ignore[misc]
    assert e.seq == 1
    assert e.timestamp is None
    assert e.role == "system"
    assert e.kind == "other"
    assert e.title == "x"
    assert e.body == "y"
    assert e.meta == {}


def test_real_excerpt_parses_without_exception_and_emits_at_least_seven() -> None:
    events = parse_file(REAL_EXCERPT)
    assert len(events) >= 7


# ---------------------------------------------------------------------------
# SPEC obligation #1 - one assertion per Kinds-table row
# ---------------------------------------------------------------------------

def _events_for_line(line: str) -> list[Event]:
    return parse_lines([line])


def test_kind_system_init() -> None:
    line = json.dumps({
        "type": "system", "subtype": "init",
        "session_id": "s1", "model": "m", "cwd": "/tmp",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "init"
    assert ev.meta["session_id"] == "s1"
    assert ev.meta["model"] == "m"
    assert ev.meta["cwd"] == "/tmp"


def test_kind_system_hook_started() -> None:
    line = json.dumps({
        "type": "system", "subtype": "hook_started",
        "hook_name": "SessionStart:startup", "hook_event": "SessionStart",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "hook_started"
    assert ev.meta["hook_name"] == "SessionStart:startup"
    assert ev.meta["hook_event"] == "SessionStart"


def test_kind_system_hook_progress() -> None:
    line = json.dumps({
        "type": "system", "subtype": "hook_progress",
        "hook_name": "SessionStart:startup", "hook_event": "SessionStart",
        "stdout": "hello",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "hook_progress"
    assert ev.meta["hook_name"] == "SessionStart:startup"


def test_kind_system_hook_response() -> None:
    line = json.dumps({
        "type": "system", "subtype": "hook_response",
        "hook_name": "SessionStart:startup", "hook_event": "SessionStart",
        "exit_code": 0, "outcome": "success",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "hook_response"
    assert ev.meta["exit_code"] == 0
    assert ev.meta["hook_name"] == "SessionStart:startup"


def test_kind_system_task_started() -> None:
    line = json.dumps({
        "type": "system", "subtype": "task_started",
        "task_id": "t-1234", "description": "go",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "task_started"
    assert ev.meta.get("task_id") == "t-1234"


def test_kind_system_task_progress() -> None:
    line = json.dumps({
        "type": "system", "subtype": "task_progress",
        "task_id": "t-1234", "step": "fetching",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "task_progress"


def test_kind_system_task_notification() -> None:
    line = json.dumps({
        "type": "system", "subtype": "task_notification",
        "task_id": "t-1234", "message": "tick",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "task_notification"


def test_kind_system_other() -> None:
    line = json.dumps({"type": "system", "subtype": "weird_subtype", "x": 1})
    [ev] = _events_for_line(line)
    assert ev.role == "system" and ev.kind == "other"
    # subtype should be preserved in meta so the renderer can show it
    assert ev.meta.get("subtype") == "weird_subtype"


def test_kind_assistant_thinking_text_tool_use_via_fanout() -> None:
    line = json.dumps({
        "type": "assistant",
        "message": {
            "model": "m", "id": "msg_kinds", "type": "message", "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "hmm"},
                {"type": "text", "text": "hi"},
                {"type": "tool_use", "id": "tu1", "name": "Bash",
                 "input": {"command": "ls"}},
            ],
        },
        "session_id": "s",
        "uuid": "u",
    })
    events = _events_for_line(line)
    kinds = [e.kind for e in events]
    assert kinds == ["thinking", "text", "tool_use"]
    assert all(e.role == "assistant" for e in events)


def test_kind_user_text_string_content() -> None:
    line = json.dumps({
        "type": "user",
        "message": {"role": "user", "content": "What's up?"},
        "session_id": "s", "uuid": "u",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "user" and ev.kind == "text"
    assert ev.body == "What's up?"


def test_kind_user_text_blocks() -> None:
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": "follow up"}],
        },
        "session_id": "s", "uuid": "u",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "user" and ev.kind == "text"
    assert ev.body == "follow up"


def test_assistant_text_with_non_string_text_is_coerced_to_json() -> None:
    line = json.dumps({
        "type": "assistant",
        "message": {
            "model": "m", "id": "msg_x", "type": "message", "role": "assistant",
            "content": [{"type": "text", "text": {"oops": "dict"}}],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.role == "assistant" and ev.kind == "text"
    # Body must be valid JSON containing "oops" — NOT a Python repr.
    parsed = json.loads(ev.body)
    assert parsed == {"type": "text", "text": {"oops": "dict"}}
    assert "{'oops':" not in ev.body
    assert ev.meta["coerced_from_non_string"] is True
    assert ev.title == "text"


def test_assistant_thinking_with_non_string_is_coerced_to_json() -> None:
    line = json.dumps({
        "type": "assistant",
        "message": {
            "model": "m", "id": "msg_x", "type": "message", "role": "assistant",
            "content": [{"type": "thinking", "thinking": {"hidden": "obj"}}],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.role == "assistant" and ev.kind == "thinking"
    parsed = json.loads(ev.body)
    assert parsed == {"type": "thinking", "thinking": {"hidden": "obj"}}
    assert ev.meta["coerced_from_non_string"] is True
    assert ev.title == "thinking"


def test_user_text_block_with_non_string_text_is_coerced_to_json() -> None:
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": {"weird": 1}}],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.role == "user" and ev.kind == "text"
    parsed = json.loads(ev.body)
    assert parsed == {"type": "text", "text": {"weird": 1}}
    assert ev.meta["coerced_from_non_string"] is True
    assert ev.title == "text"


def test_user_message_string_content_with_non_string_top_level_is_coerced() -> None:
    # Top-level non-string user content (e.g. a number/bool/null/dict that isn't a list).
    line = json.dumps({
        "type": "user",
        "message": {"role": "user", "content": 42},
    })
    [ev] = _events_for_line(line)
    # Whatever role/kind is emitted, must NOT silently drop or repr the dict.
    # Per spec extension: non-string string-content is JSON-encoded with the flag.
    # The whole message dict should be JSON-encoded.
    parsed = json.loads(ev.body)
    assert parsed == {"role": "user", "content": 42}
    assert ev.meta.get("coerced_from_non_string") is True


def test_kind_user_tool_result() -> None:
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{
                "tool_use_id": "toolu_xyz",
                "type": "tool_result",
                "content": "ok\nline2",
                "is_error": False,
            }],
        },
        "session_id": "s", "uuid": "u",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "user" and ev.kind == "tool_result"
    assert ev.meta["tool_use_id"] == "toolu_xyz"
    assert ev.meta["is_error"] is False
    assert "ok" in ev.body


def test_tool_result_title_ok_includes_tool_use_id() -> None:
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{
                "tool_use_id": "toolu_abc",
                "type": "tool_result",
                "content": "fine",
                "is_error": False,
            }],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.title == "tool_result — toolu_abc (ok)"


def test_tool_result_title_error_includes_tool_use_id() -> None:
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{
                "tool_use_id": "toolu_abc",
                "type": "tool_result",
                "content": "fail",
                "is_error": True,
            }],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.title == "tool_result — toolu_abc (error)"


def test_tool_result_title_missing_tool_use_id_uses_question_mark() -> None:
    line = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "content": "no id",
                "is_error": False,
            }],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.title == "tool_result — ? (ok)"


def test_kind_rate_limit_event() -> None:
    line = json.dumps({
        "type": "rate_limit_event",
        "rate_limit_info": {"status": "allowed", "rateLimitType": "five_hour"},
        "uuid": "u", "session_id": "s",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "rate_limit" and ev.kind == "event"
    assert ev.meta.get("status") == "allowed"


def test_kind_result_success() -> None:
    line = json.dumps({
        "type": "result", "subtype": "success",
        "session_id": "s", "duration_ms": 100, "num_turns": 1,
    })
    [ev] = _events_for_line(line)
    assert ev.role == "result" and ev.kind == "success"


def test_kind_result_error() -> None:
    line = json.dumps({
        "type": "result", "subtype": "error",
        "session_id": "s", "error": "boom",
    })
    [ev] = _events_for_line(line)
    assert ev.role == "result" and ev.kind == "error"


def test_kind_result_other_for_unknown_subtype() -> None:
    line = json.dumps({"type": "result", "subtype": "weird"})
    [ev] = _events_for_line(line)
    assert ev.role == "result"
    assert ev.kind == "other"
    assert ev.title == "result (weird)"


def test_kind_result_other_for_missing_subtype() -> None:
    line = json.dumps({"type": "result"})
    [ev] = _events_for_line(line)
    assert ev.role == "result"
    assert ev.kind == "other"
    assert ev.title == "result (unknown)"


def test_kind_unknown_for_unrecognised_type() -> None:
    line = json.dumps({"type": "weird_unseen_type", "foo": "bar"})
    [ev] = _events_for_line(line)
    assert ev.role == "unknown" and ev.kind == "unknown"


# ---------------------------------------------------------------------------
# SPEC obligation #2 - fan-out yields N events with consecutive seq
# ---------------------------------------------------------------------------

def test_fanout_consecutive_seq_for_assistant_message() -> None:
    events = parse_file(EDGE_CASES)
    fan = _msg_events(events, "msg_test_001")
    assert [e.kind for e in fan] == ["thinking", "text", "tool_use"]
    seqs = [e.seq for e in fan]
    assert seqs == list(range(seqs[0], seqs[0] + 3))
    # all share the same message_id
    assert all(e.meta.get("message_id") == "msg_test_001" for e in fan)


def test_fanout_meta_plumbing_tool_use_and_tool_result() -> None:
    events = parse_file(EDGE_CASES)
    fan = _msg_events(events, "msg_test_001")
    [tu] = [e for e in fan if e.kind == "tool_use"]
    assert tu.meta["tool_name"] == "Bash"
    assert tu.meta["tool_input"] == {"command": "ls -la", "description": "List files"}
    assert tu.meta["tool_use_id"] == "toolu_test_1"

    tr = next(e for e in events
              if e.role == "user" and e.kind == "tool_result"
              and e.meta.get("tool_use_id") == "toolu_test_1")
    assert tr.meta["tool_use_id"] == "toolu_test_1"


# ---------------------------------------------------------------------------
# SPEC obligation #3 - user string content -> single user/text event
# ---------------------------------------------------------------------------

def test_user_string_content_single_event() -> None:
    events = parse_file(EDGE_CASES)
    txt = [e for e in events if e.role == "user" and e.kind == "text"]
    assert len(txt) == 1
    assert txt[0].body == "What's up?"


# ---------------------------------------------------------------------------
# SPEC obligation #4 - malformed JSON -> unknown event with parse_error
# ---------------------------------------------------------------------------

def test_malformed_json_yields_unknown_event_with_parse_error() -> None:
    [ev] = parse_lines(["this is not json {"])
    assert ev.role == "unknown" and ev.kind == "unknown"
    assert "parse_error" in ev.meta
    assert ev.body  # raw line preserved
    assert len(ev.body) <= 200


def test_malformed_json_truncated_at_200_chars() -> None:
    raw = "x" * 500 + " not json"
    [ev] = parse_lines([raw])
    assert ev.role == "unknown"
    assert "parse_error" in ev.meta
    assert len(ev.body) <= 200


# ---------------------------------------------------------------------------
# SPEC obligation #5 - empty / whitespace-only lines silently skipped
# ---------------------------------------------------------------------------

def test_empty_and_whitespace_lines_skipped() -> None:
    out = parse_lines(["", "   ", "\t\n"])
    assert out == []


def test_blank_lines_in_edge_cases_are_skipped() -> None:
    events = parse_file(EDGE_CASES)
    # Fixture lines (1-indexed):
    #   1 assistant (fans out to 3) + 1 user/text + 1 user/tool_result
    #   blank (skip), whitespace (skip)
    #   malformed JSON (1 unknown) + result (1) + rate_limit (1) + unknown-type (1)
    # = 3 + 1 + 1 + 0 + 0 + 1 + 1 + 1 + 1 = 9 events.
    assert len(events) == 9


# ---------------------------------------------------------------------------
# SPEC obligation #6 - seq is 1-based and monotonically increasing
# ---------------------------------------------------------------------------

def test_seq_is_one_based_and_monotonic() -> None:
    events = parse_file(EDGE_CASES)
    assert events[0].seq == 1
    for prev, curr in zip(events, events[1:]):
        assert curr.seq == prev.seq + 1


def test_seq_continues_across_fanout() -> None:
    events = parse_file(EDGE_CASES)
    fan = _msg_events(events, "msg_test_001")
    # The fan-out is at the start of the file; seqs should be 1,2,3.
    assert [e.seq for e in fan] == [1, 2, 3]


# ---------------------------------------------------------------------------
# SPEC obligation #7 - timestamp passthrough and None when absent
# ---------------------------------------------------------------------------

def test_timestamp_passthrough_when_present() -> None:
    events = parse_file(EDGE_CASES)
    user_text = [e for e in events if e.role == "user" and e.kind == "text"][0]
    assert user_text.timestamp == "2026-04-28T08:00:00.000Z"


def test_timestamp_none_when_absent() -> None:
    line = json.dumps({"type": "system", "subtype": "init",
                       "session_id": "s", "model": "m", "cwd": "/x"})
    [ev] = _events_for_line(line)
    assert ev.timestamp is None


def test_assistant_fanout_shares_one_timestamp() -> None:
    line = json.dumps({
        "type": "assistant",
        "timestamp": "2026-04-28T09:00:00.000Z",
        "message": {
            "model": "m", "id": "msg_x", "type": "message", "role": "assistant",
            "content": [
                {"type": "text", "text": "a"},
                {"type": "text", "text": "b"},
            ],
        },
        "session_id": "s", "uuid": "u",
    })
    events = _events_for_line(line)
    assert len(events) == 2
    assert {e.timestamp for e in events} == {"2026-04-28T09:00:00.000Z"}


# ---------------------------------------------------------------------------
# Hook + init meta plumbing (parser-half contract bullet)
# ---------------------------------------------------------------------------

def test_hook_events_surface_hook_name_and_event() -> None:
    events = parse_file(REAL_EXCERPT)
    hooks = [e for e in events if e.kind in {"hook_started", "hook_progress", "hook_response"}]
    assert hooks, "expected at least one hook event in real_excerpt"
    for h in hooks:
        assert h.meta["hook_name"] == "SessionStart:startup"
        assert h.meta["hook_event"] == "SessionStart"


def test_init_event_surfaces_model_cwd_session_id() -> None:
    events = parse_file(REAL_EXCERPT)
    [init] = [e for e in events if e.kind == "init"]
    assert init.meta["model"] == "claude-opus-4-7[1m]"
    assert init.meta["cwd"] == "/Volumes/Unitek-B/Projects/o2-scalpel"
    assert init.meta["session_id"] == "e5237de2-83eb-48a3-a080-21943c9d9ae6"


# ---------------------------------------------------------------------------
# Title sanity checks (renderer relies on these)
# ---------------------------------------------------------------------------

def test_titles_for_simple_kinds() -> None:
    init = _events_for_line(json.dumps({
        "type": "system", "subtype": "init",
        "session_id": "s", "model": "m", "cwd": "/x",
    }))[0]
    assert init.title == "init"

    txt = _events_for_line(json.dumps({
        "type": "user",
        "message": {"role": "user", "content": "hi"},
    }))[0]
    assert txt.title == "text"


def test_title_for_tool_use_includes_tool_name() -> None:
    line = json.dumps({
        "type": "assistant",
        "message": {
            "model": "m", "id": "msg", "type": "message", "role": "assistant",
            "content": [{"type": "tool_use", "id": "tu", "name": "Bash",
                          "input": {"command": "ls"}}],
        },
    })
    [ev] = _events_for_line(line)
    assert ev.title == "tool_use - Bash" or ev.title == "tool_use — Bash"
