# Leaf L-G8 — LOW tier + docstring drift fixes

**Goal.** Acknowledge documented limitations honestly and fix two pure-doc drifts. Spec § LO-1, LO-2, LO-3.

**Sub-tasks:**

| Sub | Spec | Subject | File:line | Fix |
|---|---|---|---|---|
| LO-1 | `scalpel_rename` `also_in_strings` (L708) | `scalpel_facades.py:681-802` | LSP `textDocument/rename` cannot rewrite string literals — protocol limitation. When `also_in_strings=True`, return a `warnings` field on the RefactorResult: `"also_in_strings is unsupported by textDocument/rename; use scalpel_replace_regex for string-literal renames"`. Update docstring to match. |
| LO-2 | `rust_strategy.py` Stage-1E doc drift | `vendor/serena/src/serena/refactoring/rust_strategy.py:5-7` | Replace "Stage-1E skeleton awaiting Stage 1G fill-out" with the v1.4 reality: the strategy is fully wired across all 25 Rust facades. Pure docstring update. |
| LO-3 | `checkpoints.py` deep-tree restore deferral | `vendor/serena/src/serena/refactoring/checkpoints.py:87` | Update the docstring to flag this as a v1.6 enhancement; do NOT implement (out of scope per spec). The current behavior (only empty placeholder dirs recreated by `scalpel_undo_last`) is preserved. |

**Source spec.** § LO-1 (lines 145-147), § LO-2 (lines 149-150), § LO-3 (lines 152-154).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelRenameTool.apply` (L681-802) — wire `also_in_strings` to a warnings field | ~20 |
| `vendor/serena/src/serena/refactoring/rust_strategy.py` | edit module docstring (L1-30) | ~15 |
| `vendor/serena/src/serena/refactoring/checkpoints.py` | edit docstring near L87 | ~10 |
| `vendor/serena/test/spikes/test_v1_5_g8_lo_1_rename_strings_warn.py` | NEW | ~80 |

## TDD — failing test first (LO-1 only — LO-2 / LO-3 are docstring-only)

Create `vendor/serena/test/spikes/test_v1_5_g8_lo_1_rename_strings_warn.py`:

```python
"""v1.5 G8 — LO-1: scalpel_rename also_in_strings honest warning.

textDocument/rename cannot rewrite string literals. When the caller
passes also_in_strings=True, the response should carry a warning that
points to scalpel_replace_regex as the right tool — instead of silently
ignoring the flag.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelRenameTool
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
        'pub fn helper() {}\n'
        'fn caller() { let s = "helper called"; helper(); }\n'
    )
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelRenameTool:
    tool = ScalpelRenameTool.__new__(ScalpelRenameTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def test_rename_also_in_strings_emits_warning(rust_workspace):
    tool = _make_tool(rust_workspace)
    src = rust_workspace / "lib.rs"
    fake_coord = MagicMock()
    fake_coord.supports_method.return_value = True

    async def _find(**kw):
        return {"line": 0, "character": 7}
    fake_coord.find_symbol_position = _find

    async def _rename(**kw):
        return ({"changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 7},
                      "end": {"line": 0, "character": 13}},
            "newText": "renamed",
        }]}}, [])
    fake_coord.merge_rename = _rename

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            name_path="helper",
            new_name="renamed",
            also_in_strings=True,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    warnings = payload.get("warnings") or ()
    # Warning is present:
    assert any(
        "also_in_strings" in w and "scalpel_replace_regex" in w
        for w in warnings
    ), warnings
    # String literal was NOT rewritten (correct LSP semantics):
    body = src.read_text(encoding="utf-8")
    assert '"helper called"' in body
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g8_lo_1_rename_strings_warn.py -x`.

## Implementation steps

1. **LO-1:** drop `also_in_strings` from `del` at `scalpel_facades.py:708`. After resolving the WorkspaceEdit but before returning, when `also_in_strings is True` append a warning string to `warnings` tuple in the returned `RefactorResult`. Update docstring at L695-706 to describe the limitation.
2. **LO-2:** update `rust_strategy.py:5-7` docstring — drop the Stage-1E language; describe the strategy's current v1.4 capabilities.
3. **LO-3:** update `checkpoints.py:87` comment — flag deep-tree restoration as v1.6 enhancement; preserve current behavior.
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g8_lo_1_rename_strings_warn.py -x

# Existing rename tests must still pass:
uv run pytest vendor/serena/test/spikes/test_stage_2a_t5_rename.py -x

uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py \
                vendor/serena/src/serena/refactoring/rust_strategy.py \
                vendor/serena/src/serena/refactoring/checkpoints.py
```

**Atomic commit:**

```
docs(facade-low): honest also_in_strings warning + docstring drift cleanup (LO-1..LO-3)

LO-1: scalpel_rename emits a warnings entry pointing to
       scalpel_replace_regex when also_in_strings=True (LSP limitation).
LO-2: rust_strategy.py module docstring updated to v1.4 reality.
LO-3: checkpoints.py acknowledges deep-tree restore deferral to v1.6.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** none meaningful. LO-1 adds a warning, no behavior change. LO-2 / LO-3 are docstring-only.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** none. Independent of all other leaves.
- **Blocks:** none.

---

**Author:** AI Hive®.
