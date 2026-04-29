# jsonl_to_dialog — SPEC (locked contract for parser ↔ renderer)

Transforms a Claude Code SDK transcript (`*.log`/`*.jsonl`, one JSON object per line)
into a Markdown file rendered as a chronological dialog.

## Module split (so parser & renderer can be developed in parallel)

```
scripts/jsonl_to_dialog/
    parser.py          # JSONL line(s) -> list[Event]
    renderer.py        # list[Event] -> markdown str
    cli.py             # glue: file in -> file out  (added in integration step)
    tests/test_parser.py
    tests/test_renderer.py
    tests/fixtures/sample.jsonl
```

`parser.py` and `renderer.py` MUST NOT import each other.
The Event dataclass below is the only shared contract — defined in `parser.py` and
re-exported by `renderer.py` via `from .parser import Event` (or duplicated as a
TypedDict in renderer if circular imports are ever a concern).

## The Event contract (FROZEN — do not change without coordination)

```python
from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class Event:
    seq: int                   # 1-based ordinal in the transcript
    timestamp: Optional[str]   # ISO-8601 string from input, or None if absent
    role: str                  # "system" | "user" | "assistant" | "rate_limit" | "result" | "unknown"
    kind: str                  # finer-grained type — see "Kinds" table below
    title: str                 # short header label, plain text, no markdown chars
    body: str                  # markdown-ready body; multi-line allowed; safe to drop into a doc
    meta: dict[str, Any]       # extra structured fields (session_id, hook_name, model, tool_name, tool_use_id...)
```

`meta` is informational only — renderer MAY surface a few common keys (see below)
but is allowed to ignore unknown ones. Renderer MUST NOT crash on unexpected `meta`.

## Kinds (closed set the parser emits)

| role         | kind              | source line shape                                        |
|--------------|-------------------|----------------------------------------------------------|
| system       | init              | `{"type":"system","subtype":"init", ...}`                |
| system       | hook_started      | `{"type":"system","subtype":"hook_started", ...}`        |
| system       | hook_progress     | `{"type":"system","subtype":"hook_progress", ...}`       |
| system       | hook_response     | `{"type":"system","subtype":"hook_response", ...}`       |
| system       | task_started      | `{"type":"system","subtype":"task_started", ...}`        |
| system       | task_progress     | `{"type":"system","subtype":"task_progress", ...}`       |
| system       | task_notification | `{"type":"system","subtype":"task_notification", ...}`   |
| system       | other             | any other system subtype                                 |
| assistant    | thinking          | one content block of `{"type":"thinking", ...}`          |
| assistant    | text              | one content block of `{"type":"text", ...}`              |
| assistant    | tool_use          | one content block of `{"type":"tool_use", ...}`          |
| user         | text              | a string `content`, OR a content block of `{"type":"text", ...}` |
| user         | tool_result       | one content block of `{"type":"tool_result", ...}`       |
| rate_limit   | event             | `{"type":"rate_limit_event", ...}`                       |
| result       | success / error   | `{"type":"result","subtype":"success", ...}`             |
| unknown      | unknown           | any line whose `type` doesn't match the above            |

### Fan-out rule for assistant/user content blocks

A single assistant message with N content blocks → N Events (one per block),
preserving block order. `seq` is assigned across all events in the file, not
per-message. All N events share the same `timestamp` (from the message) and a
common `meta.message_id`.

A user message whose `content` is a plain string becomes ONE Event
(`role="user"`, `kind="text"`).

### Title conventions (for renderer headers)

| kind             | title example                                |
|------------------|----------------------------------------------|
| init             | `init`                                       |
| hook_started     | `hook_started — SessionStart:startup`        |
| hook_progress    | `hook_progress — SessionStart:startup`       |
| hook_response    | `hook_response — SessionStart:startup (exit 0)` |
| task_started     | `task_started — <task_id short>`             |
| task_progress    | `task_progress — <task_id short>`            |
| task_notification| `task_notification — <task_id short>`        |
| thinking         | `thinking`                                   |
| text             | `text`                                       |
| tool_use         | `tool_use — Bash`                            |
| tool_result      | `tool_result — toolu_xxx (ok)` or `(error)`  |
| event            | `rate_limit (status=allowed)`                |
| success / error  | `result (success)` / `result (error)`        |
| unknown          | `unknown`                                    |

Body conventions:
- For `tool_use`: render the input args as a fenced ```json block (pretty-printed).
- For `tool_result`: render the textual content as a fenced ``` block (auto-truncate at 4000 chars with a `... [truncated N chars]` marker).
- For assistant `text` and user `text`: render the text verbatim (it's already markdown-friendly).
- For `thinking`: render text verbatim, but the renderer MAY wrap in a `<details><summary>thinking</summary>…</details>` block (default: ON).
- For hook/init/task/result/rate_limit kinds: render a small key/value list (markdown bullet list) of the most useful fields from `meta`.

## Renderer output shape

```
# Dialog — <basename of input>

_<line count> events · <session_id(s)> · generated <UTC ISO>_

---

### #1 · 2026-04-28T07:55:14Z · system · init
- session_id: e5237de2-…
- model: claude-opus-4-7
- cwd: /Volumes/Unitek-B/Projects/o2-scalpel

---

### #2 · 2026-04-28T07:55:14Z · assistant · text
Some markdown text…

---
```

- Header line: `### #{seq} · {timestamp or "—"} · {role} · {title}` (one space around `·`).
- Followed by a blank line, then body, then a blank line, then `---`, then blank line.
- If timestamp is `None`, render `—` (em dash).

## Robustness rules

- A malformed JSON line MUST NOT abort the run. Parser yields a single `unknown`
  Event with `meta.parse_error` set and the raw line truncated to 200 chars in body.
- An empty/whitespace-only line is silently skipped (no Event emitted).
- Renderer MUST be deterministic: same input → byte-identical output.
- Encoding: parser/renderer operate on `str`; CLI reads/writes UTF-8.

## Test obligations

`test_parser.py` MUST cover:
1. Each kind in the Kinds table (one assertion per row).
2. Fan-out: assistant message with `[thinking, text, tool_use]` produces 3 events with consecutive `seq`.
3. User message with string `content` → one `user/text` event.
4. Malformed JSON → one `unknown` event with `meta.parse_error`.
5. Empty line → no event emitted.
6. `seq` is 1-based and monotonically increasing across the whole stream.
7. Timestamp passthrough (when present in source) and `None` (when absent).

`test_renderer.py` MUST cover:
1. Header format exactly matches `### #{seq} · {ts} · {role} · {title}`.
2. `tool_use` body is a fenced `json` block with pretty-printed input.
3. `tool_result` body truncates over 4000 chars and adds `... [truncated N chars]`.
4. Missing timestamp renders as `—`.
5. Output ends with a single trailing newline.
6. Determinism: rendering the same `[Event]` twice yields the same string.
7. `<details>` wrapping for thinking can be disabled via a flag.

Both test files run under `pytest` with no project-wide conftest needed.
