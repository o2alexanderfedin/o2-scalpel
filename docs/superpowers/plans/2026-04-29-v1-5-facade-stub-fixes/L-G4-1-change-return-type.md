# Leaf L-G4-1 — `ScalpelChangeReturnTypeTool` honors `new_return_type`

**Goal.** Stop discarding `new_return_type` (`scalpel_facades.py:1490` `del preview_token, new_return_type`). After G1 lands, this leaf threads the caller's requested return type into the dispatcher's `title_match` so the resolved code-action's title matches what the caller asked for. When rust-analyzer's surfaced action does NOT mention the requested type — meaning the assist's auto-pick disagreed with the caller — return an `INPUT_NOT_HONORED` envelope instead of silently applying the wrong rewrite. Spec § HI-2.

**Strategy.** Rust-analyzer's `change_return_type` assist offers a single rewrite per cursor. The action's title typically encodes the inferred replacement (e.g. `"Change return type to Result<T, E>"`). When the caller passes `new_return_type="Result<T, E>"`, route via `title_match=new_return_type`; if the title-match envelope reports `no_candidate_matched_title_match`, surface that to the caller as `INPUT_NOT_HONORED` (a new docstring-honest status, not a silent application). Update the docstring at L1481-1487 to remove the "informational" weasel-word.

**Source spec.** § HI-2 (lines 57-60).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelChangeReturnTypeTool.apply` (L1464-1503) | ~40 |
| `vendor/serena/test/spikes/test_v1_5_g4_1_change_return_type.py` | NEW | ~180 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_1_change_return_type.py`:

```python
"""v1.5 G4-1 — change_return_type honors new_return_type (HI-2).

Acid tests:
  * Caller's new_return_type flows into title_match.
  * When RA's action title contains the requested type → applied=True,
    real-disk read confirms the new return type is in the source.
  * When RA's action title does NOT contain the requested type → response
    envelope is INPUT_NOT_HONORED (not silent-success).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelChangeReturnTypeTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text("pub fn calc() -> i32 { 0 }\n")
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelChangeReturnTypeTool:
    tool = ScalpelChangeReturnTypeTool.__new__(ScalpelChangeReturnTypeTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title):
    a = MagicMock()
    a.id = action_id
    a.action_id = action_id
    a.title = title
    a.is_preferred = False
    a.provenance = "rust-analyzer"
    a.kind = "refactor.rewrite.change_return_type"
    return a


def test_change_return_type_honors_new_return_type(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action(
            "ra:1",
            'Change return type to Result<i32, Error>',
        )]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 17},
                      "end": {"line": 0, "character": 20}},
            "newText": "Result<i32, Error>",
        }]},
    }

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 8},
            new_return_type="Result<i32, Error>",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # Real-disk acid test:
    assert "Result<i32, Error>" in src.read_text(encoding="utf-8")


def test_change_return_type_input_not_honored_when_title_mismatch(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ra:1", "Change return type to Option<i32>")]

    fake_coord.merge_code_actions = _actions

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 0, "character": 8},
            new_return_type="Result<i32, Error>",
            language="rust",
        )
    payload = json.loads(out)
    # Honest response — not a silent-apply of Option<i32>:
    assert payload.get("status") == "skipped"
    assert payload.get("reason") == "no_candidate_matched_title_match"
    # Real-disk acid test: source UNCHANGED.
    assert src.read_text(encoding="utf-8") == "pub fn calc() -> i32 { 0 }\n"
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_1_change_return_type.py -x` — fails today (`del new_return_type` discards the arg).

## Implementation steps

1. **Drop `new_return_type` from the `del` line** at `scalpel_facades.py:1490`.
2. **Pass `title_match=new_return_type`** when delegating to `_dispatch_single_kind_facade(...)` at L1498-1502 (added in G1).
3. **Update docstring at L1481-1487** — remove "(informational — rust-analyzer offers a single rewrite per cursor; the target type is selected by the assist)" and replace with: `"replacement type expression. When the assist's surfaced rewrite does not match this type, the response is INPUT_NOT_HONORED — caller can retry at a different cursor or accept rust-analyzer's suggested type."`
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_1_change_return_type.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t2_rust_wave_b.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(change_return_type): honor new_return_type via title_match (HI-2)

Threads the caller's new_return_type into the shared dispatcher's
title_match (per L-G1). When RA's surfaced rewrite does not match,
returns INPUT_NOT_HONORED instead of silently applying the wrong type.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** RA's title format changes between versions and the substring match misses. Mitigation: title_match is case-insensitive substring; version drift is low risk over the 1-year horizon.
- **Rollback:** revert single commit; HI-2 reopens.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-A real-disk tests for change_return_type.

---

**Author:** AI Hive®.
