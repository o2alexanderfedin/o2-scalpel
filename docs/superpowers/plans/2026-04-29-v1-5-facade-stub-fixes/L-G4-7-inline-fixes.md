# Leaf L-G4-7 — `ScalpelInlineTool` honors `name_path` + `remove_definition`; (0,0) fallback removed

**Goal.** Three fixes in one leaf because they share the same `ScalpelInlineTool.apply` entry-point (`scalpel_facades.py:560-665`):

1. **`name_path` resolution** (currently `del name_path` at L591). When caller passes `name_path` instead of `position`, resolve via `coord.find_symbol_range`.
2. **`remove_definition` honored** (currently `del remove_definition` at L591). LSP's inline assist always removes the definition; when caller asks `remove_definition=False`, post-filter the WorkspaceEdit to drop the deletion hunk.
3. **(0,0) fallback removed** at L627 (`pos = position or {"line":0,"character":0}`). When `scope='all_callers'` and no `position`, use `coord.request_references(file=..., name_path=...)` (resolved from name_path or symbol identification) and dispatch one inline per call site.

Spec § HI-8 + § HI-13 (third site).

**Source spec.** § HI-8 (lines 86-89), § HI-13 (line 112 — `inline` site).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelInlineTool.apply` (L560-665) — three fixes | ~110 |
| `vendor/serena/test/spikes/test_v1_5_g4_7_inline_fixes.py` | NEW | ~280 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_7_inline_fixes.py`:

```python
"""v1.5 G4-7 — scalpel_inline honors name_path + remove_definition; no (0,0) fallback (HI-8 + HI-13)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelInlineTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text(
        "fn helper(a: i32) -> i32 { a + 1 }\n"
        "fn caller() { let x = helper(10); }\n"
    )
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelInlineTool:
    tool = ScalpelInlineTool.__new__(ScalpelInlineTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title, kind):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title; a.kind = kind
    a.is_preferred = False; a.provenance = "rust-analyzer"
    return a


def test_inline_resolves_name_path_to_position(rust_workspace):
    """name_path is no longer dropped; coord.find_symbol_range supplies the position."""
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _find(**kw):
        return {"start": {"line": 1, "character": 22},
                "end": {"line": 1, "character": 32}}

    fake_coord.find_symbol_range = _find

    async def _actions(**kw):
        captured.append(kw)
        return [_action("ra:1", "Inline call", "refactor.inline.call")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {"changes": {src.as_uri(): [{
        "range": {"start": {"line": 1, "character": 22},
                  "end": {"line": 1, "character": 32}},
        "newText": "10 + 1",
    }]}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            name_path="caller::helper",   # NOT position=
            target="call",
            scope="single_call_site",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # Real-disk acid test: helper call inlined to "10 + 1":
    body = src.read_text(encoding="utf-8")
    assert "helper(10)" not in body
    assert "10 + 1" in body
    # Dispatch used resolved range, NOT (0,0):
    for c in captured:
        assert c["start"] != {"line": 0, "character": 0}


def test_inline_remove_definition_false_keeps_definition(rust_workspace):
    """When the LSP emits both 'replace call' and 'delete definition' hunks,
    remove_definition=False post-filters out the deletion."""
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    async def _find(**kw):
        return {"start": {"line": 1, "character": 22},
                "end": {"line": 1, "character": 32}}

    fake_coord.find_symbol_range = _find

    async def _actions(**kw):
        return [_action("ra:1", "Inline call", "refactor.inline.call")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {"changes": {src.as_uri(): [
        # Hunk 1: replace call site
        {"range": {"start": {"line": 1, "character": 22},
                   "end": {"line": 1, "character": 32}},
         "newText": "10 + 1"},
        # Hunk 2: delete definition (the bit we want to KEEP)
        {"range": {"start": {"line": 0, "character": 0},
                   "end": {"line": 1, "character": 0}},
         "newText": ""},
    ]}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 1, "character": 22},
            target="call",
            scope="single_call_site",
            remove_definition=False,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    body = src.read_text(encoding="utf-8")
    # Definition preserved:
    assert "fn helper(a: i32)" in body
    # Call site still inlined:
    assert "10 + 1" in body


def test_inline_all_callers_uses_references_not_zero_zero(rust_workspace):
    """scope='all_callers' triggers references-driven dispatch, NOT (0,0)."""
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _references(**kw):
        return [
            {"uri": src.as_uri(),
             "range": {"start": {"line": 1, "character": 22},
                       "end": {"line": 1, "character": 32}}},
        ]

    fake_coord.request_references = _references

    async def _actions(**kw):
        captured.append(kw)
        return [_action("ra:1", "Inline call", "refactor.inline.call")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {"changes": {src.as_uri(): [{
        "range": {"start": {"line": 1, "character": 22},
                  "end": {"line": 1, "character": 32}},
        "newText": "10 + 1",
    }]}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            name_path="helper",
            target="call",
            scope="all_callers",
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # Dispatch happened against references' position, NOT (0,0):
    for c in captured:
        assert c["start"] != {"line": 0, "character": 0}
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_7_inline_fixes.py -x`.

## Implementation steps

1. **Drop `name_path, remove_definition` from `del`** at `scalpel_facades.py:591`.
2. **Resolve `name_path` to position** when `position is None`:
   ```python
   if position is None and name_path is not None:
       resolved = _run_async(coord.find_symbol_range(
           file=file, name_path=name_path,
           project_root=str(project_root),
       ))
       if resolved is None:
           return build_failure_result(
               code=ErrorCode.SYMBOL_NOT_FOUND,
               stage="scalpel_inline",
               reason=f"Symbol {name_path!r} not found in {file!r}.",
           ).model_dump_json(indent=2)
       position = resolved["start"]
   ```
3. **Remove the `(0,0)` fallback at L627.** Replace `pos = position or {"line":0,"character":0}` with: when `position is None and scope == "all_callers"` (and name_path was given), call `coord.request_references(...)` to get all call-site positions; iterate dispatching one inline per site; merge resulting WorkspaceEdits. When `scope == "single_call_site"` AND position is still None after step 2, return INVALID_ARGUMENT (existing branch at L607-613 handles this — keep).
4. **Honor `remove_definition`**: after resolving the WorkspaceEdit but before applying, when `remove_definition == False` post-filter every TextDocumentEdit's `edits` list — drop hunks whose `newText == ""` and whose range covers more than 2 lines (heuristic: a deletion of the definition body). Document this heuristic inline; refine if a real LSP returns differently-shaped hunks.
5. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_7_inline_fixes.py -x
uv run pytest vendor/serena/test/spikes/test_stage_2a_t4_inline.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(inline): honor name_path + remove_definition; no (0,0) fallback (HI-8 + HI-13)

Resolves name_path via coord.find_symbol_range; iterates references for
scope='all_callers'; post-filters WorkspaceEdit to honor
remove_definition=False. Removes the (0,0) hardcoded fallback that
silently dispatched against the file head.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** the heuristic for "deletion of definition" hunk could mis-classify a genuine multi-line replace. Mitigation: tests cover both shapes; refine heuristic if false-positives surface in G7-A real-LSP runs.
- **Risk:** `request_references` not exposed on `MultiServerCoordinator`. Verify before implementation; if missing, this leaf adds it (small additive change). Existing `merge_rename` path goes through references at the per-server layer — the helper exists there.
- **Rollback:** revert single commit; HI-8 reopens.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G5 (the `inline` (0,0) site is closed here, removing it from G5's residual set).
- **Blocks:** L-G7-B real-disk tests for inline.

---

**Author:** AI Hive®.
