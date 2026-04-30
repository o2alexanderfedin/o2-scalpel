# Leaf L-G4-6 — `ScalpelExtractTool` honors `new_name` / `visibility` / `similar` / `global_scope`

**Goal.** Stop discarding 4 of 9 semantic args at `scalpel_facades.py:440` (`del new_name, visibility, similar, global_scope, preview_token`). After G1, this leaf wires each argument to its honest seam. Spec § HI-7.

**Per-arg strategy.**

| Arg | Language | Honest seam |
|---|---|---|
| `new_name` | rust + python | Post-process the WorkspaceEdit: substitute the LSP's auto-name (`new_function`, `new_var`, `extracted`) with the caller's `new_name` in every emitted hunk. Symmetric on the rename in the call site. |
| `visibility` | rust | Post-process the WorkspaceEdit: prepend the caller's visibility prefix (`pub(crate)`, `pub`, `private` → bare) to the emitted item. |
| `similar` | python (rope) | Pass `arguments=[{..., "similar": True}]` to the LSP `executeCommand` → rope honors via `rope.refactor.extract_method.similar`. |
| `global_scope` | python (rope) | Pass `arguments=[{..., "global_scope": True}]` similarly → `rope.refactor.extract_variable.global_`. |

The pattern is "post-process for sed-replaceable names; pass through for rope-arg-aware flags." Each arg gets its own honest path; none silently faked.

**Source spec.** § HI-7 (lines 81-84).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelExtractTool.apply` (L403-543) — wire each of 4 discarded args | ~120 |
| `vendor/serena/src/serena/refactoring/python_strategy.py` | extend bridge to forward `similar` / `global_scope` to rope's `arguments` payload | ~40 |
| `vendor/serena/test/spikes/test_v1_5_g4_6_extract_knobs.py` | NEW | ~300 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_6_extract_knobs.py`:

```python
"""v1.5 G4-6 — scalpel_extract honors new_name / visibility / similar / global_scope (HI-7)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelExtractTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text("fn caller() { let x = 1 + 2 + 3; }\n")
    return tmp_path


@pytest.fixture
def python_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "calc.py"
    src.write_text("def caller():\n    x = 1 + 2 + 3\n")
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelExtractTool:
    tool = ScalpelExtractTool.__new__(ScalpelExtractTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title, *, kind, provenance="rust-analyzer"):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title; a.kind = kind
    a.is_preferred = False; a.provenance = provenance
    return a


def test_rust_extract_post_processes_new_name(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ra:1", "Extract function",
                        kind="refactor.extract.function")]

    fake_coord.merge_code_actions = _actions

    async def _find(**kw):
        return {"start": {"line": 0, "character": 23},
                "end": {"line": 0, "character": 31}}

    fake_coord.find_symbol_range = _find
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 1, "character": 0}},
            "newText": (
                "fn caller() { let x = new_function(); }\n"
                "fn new_function() -> i32 { 1 + 2 + 3 }\n"
            ),
        }]},
    }

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            range={"start": {"line": 0, "character": 23},
                   "end": {"line": 0, "character": 31}},
            target="function",
            new_name="sum_three",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    body = src.read_text(encoding="utf-8")
    assert "sum_three" in body
    assert "new_function" not in body


def test_rust_extract_post_processes_visibility(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _actions(**kw):
        return [_action("ra:1", "Extract function",
                        kind="refactor.extract.function")]

    fake_coord.merge_code_actions = _actions

    async def _find(**kw):
        return {"start": {"line": 0, "character": 23},
                "end": {"line": 0, "character": 31}}

    fake_coord.find_symbol_range = _find
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 1, "character": 0}},
            "newText": (
                "fn caller() { let x = new_function(); }\n"
                "fn new_function() -> i32 { 1 + 2 + 3 }\n"
            ),
        }]},
    }

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            range={"start": {"line": 0, "character": 23},
                   "end": {"line": 0, "character": 31}},
            target="function",
            new_name="sum",
            visibility="pub_crate",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    body = src.read_text(encoding="utf-8")
    assert "pub(crate) fn sum" in body


def test_python_extract_passes_similar_to_rope_bridge(python_workspace):
    """Asserts the rope bridge receives `similar=True` in its arguments dict."""
    tool = _make_tool(python_workspace)
    src = python_workspace / "calc.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _actions(**kw):
        captured.append(kw)
        return [_action("rope:1", "Extract method",
                        kind="refactor.extract.function",
                        provenance="pylsp-rope")]

    fake_coord.merge_code_actions = _actions

    async def _find(**kw):
        return {"start": {"line": 1, "character": 8},
                "end": {"line": 1, "character": 17}}

    fake_coord.find_symbol_range = _find
    fake_coord.get_action_edit = lambda aid: {"changes": {src.as_uri(): [{
        "range": {"start": {"line": 0, "character": 0},
                  "end": {"line": 0, "character": 0}},
        "newText": "",
    }]}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            range={"start": {"line": 1, "character": 8},
                   "end": {"line": 1, "character": 17}},
            target="function",
            new_name="sum_three",
            similar=True,
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # The dispatch's arguments-payload carries similar=True:
    assert any(
        (kw.get("arguments") or [{}])[0].get("similar") is True
        for kw in captured
    ), captured
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_6_extract_knobs.py -x`.

## Implementation steps

1. **Drop the 4 args from `del`** at `scalpel_facades.py:440` (`new_name`, `visibility`, `similar`, `global_scope`). Keep `preview_token`.
2. **Add `_post_process_extract_edit` helper** that takes `(workspace_edit, *, new_name=None, visibility=None) -> dict`:
   - For `new_name`: walk every `TextDocumentEdit.edits[*].newText`, regex-replace LSP's auto-names (`new_function`, `new_var`, `extracted`, `placeholder`) with the caller's `new_name`. Use `\b<old>\b` for word-boundary safety.
   - For `visibility`: when `lang == "rust"`, prepend `pub`/`pub(crate)`/`pub(super)` to lines that start with `fn`/`const`/`type` in the new hunk(s). `private` is a no-op (default).
3. **Pass `similar` / `global_scope` to `merge_code_actions`** via the existing `arguments` parameter slot:
   ```python
   actions = _run_async(coord.merge_code_actions(
       file=file, start=rng["start"], end=rng["end"], only=[kind],
       arguments=[{"similar": similar, "global_scope": global_scope}],
   ))
   ```
   `merge_code_actions` already forwards the `arguments` kwarg to the per-server `request_code_actions` call when present (verify against `multi_server.py`; if not exposed, extend the signature in this leaf — small additive change).
4. **In the post-apply path** (around L526-528), call `_post_process_extract_edit` before `_apply_workspace_edit_to_disk`.
5. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_6_extract_knobs.py -x
uv run pytest vendor/serena/test/spikes/test_stage_2a_t3_extract.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py \
                vendor/serena/src/serena/refactoring/python_strategy.py
```

**Atomic commit:**

```
fix(extract): honor new_name / visibility / similar / global_scope (HI-7)

Drops the 4-arg `del`. new_name + visibility post-process the LSP's
emitted WorkspaceEdit; similar + global_scope pass through rope's
executeCommand arguments payload.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** post-processing `new_name` via regex risks replacing matches inside string literals / comments. Mitigation: word-boundary regex + only operate on hunks the LSP emitted (not pre-existing code surrounding them). Test covers this.
- **Risk:** `merge_code_actions(arguments=...)` not yet wired across all servers. Mitigation: this leaf may need a small additive extension to the coordinator method; if so, document inline in commit.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-A and L-G7-B real-disk tests for extract.

---

**Author:** AI Hive®.
