# Leaf L-G2 — `dry_run` safety honor on `expand_macro` + `verify_after_refactor`

**Goal.** Stop two facades from violating the `dry_run` safety contract. Today both `ScalpelExpandMacroTool.apply` (`scalpel_facades.py:1738-1799`) and `ScalpelVerifyAfterRefactorTool.apply` (`scalpel_facades.py:1802-1862`) execute `del preview_token, dry_run` at function entry (L1760, L1824) — the user-supplied `dry_run=True` is dropped and the LSP work runs anyway, including flycheck side effects on disk. Spec § HI-12 calls this a **safety violation**, not a feature gap. This leaf short-circuits both facades when `dry_run=True` BEFORE invoking the LSP.

**Architecture.** Both facades return early with a `RefactorResult(applied=False, no_op=False, preview_token=...)` when `dry_run=True`, before any LSP call. For `expand_macro`, the preview includes the macro identifier resolved from the position (cheap — single AST walk via the existing rust-analyzer document-symbol path) so the caller still gets useful continuation context. For `verify_after_refactor`, the preview is bare since flycheck cannot be partially evaluated.

**Tech stack.** Python 3.13. No new dependencies.

**Source spec.** `docs/superpowers/specs/2026-04-29-facade-stub-audit.md` § HI-12 (lines 106-109).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelExpandMacroTool.apply` (L1738-1799) and `ScalpelVerifyAfterRefactorTool.apply` (L1802-1862) | ~50 |
| `vendor/serena/test/spikes/test_v1_5_g2_dry_run_safety.py` | NEW — failing tests that the LSP is NOT called when dry_run=True | ~150 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g2_dry_run_safety.py`:

```python
"""v1.5 G2 — dry_run safety honor on expand_macro + verify_after_refactor.

Acid test: when dry_run=True, the coord's expand_macro / fetch_runnables /
run_flycheck methods MUST NOT be called. The current code calls them and
ignores the dry_run flag entirely (HI-12 safety violation).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import (
    ScalpelExpandMacroTool,
    ScalpelVerifyAfterRefactorTool,
)
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def rust_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "lib.rs"
    src.write_text("fn main() { println!(\"hi\"); }\n")
    return tmp_path


def _make_expand(project_root: Path) -> ScalpelExpandMacroTool:
    tool = ScalpelExpandMacroTool.__new__(ScalpelExpandMacroTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _make_verify(project_root: Path) -> ScalpelVerifyAfterRefactorTool:
    tool = ScalpelVerifyAfterRefactorTool.__new__(ScalpelVerifyAfterRefactorTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def test_expand_macro_dry_run_does_not_call_lsp(rust_workspace):
    tool = _make_expand(rust_workspace)
    fake_coord = MagicMock()
    fake_coord.expand_macro = MagicMock()  # If called → assertion below fails.

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(rust_workspace / "lib.rs"),
            position={"line": 0, "character": 12},
            dry_run=True,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is False
    assert payload["no_op"] is False  # preview, not no-op
    assert payload["preview_token"] is not None
    fake_coord.expand_macro.assert_not_called()


def test_expand_macro_no_dry_run_calls_lsp(rust_workspace):
    """Counter-test: ensure we didn't accidentally short-circuit
    the non-dry_run path."""
    tool = _make_expand(rust_workspace)
    fake_coord = MagicMock()

    async def _fake_expand(**kw):
        return {"name": "println", "expansion": "// expansion"}

    fake_coord.expand_macro = _fake_expand

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(rust_workspace / "lib.rs"),
            position={"line": 0, "character": 12},
            dry_run=False,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True


def test_verify_after_refactor_dry_run_does_not_call_lsp(rust_workspace):
    tool = _make_verify(rust_workspace)
    fake_coord = MagicMock()
    fake_coord.fetch_runnables = MagicMock()
    fake_coord.run_flycheck = MagicMock()

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(rust_workspace / "lib.rs"),
            dry_run=True,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is False
    assert payload["preview_token"] is not None
    fake_coord.fetch_runnables.assert_not_called()
    fake_coord.run_flycheck.assert_not_called()


def test_verify_after_refactor_no_dry_run_calls_lsp(rust_workspace):
    tool = _make_verify(rust_workspace)
    fake_coord = MagicMock()

    async def _fake_runnables(**kw):
        return []

    async def _fake_flycheck(**kw):
        return {"diagnostics": []}

    fake_coord.fetch_runnables = _fake_runnables
    fake_coord.run_flycheck = _fake_flycheck

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(rust_workspace / "lib.rs"),
            dry_run=False,
            language="rust",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
```

Run `uv run pytest vendor/serena/test/spikes/test_v1_5_g2_dry_run_safety.py -x` — failing because today both facades drop `dry_run`. Stage tests only.

## Implementation steps

1. **In `ScalpelExpandMacroTool.apply` (`scalpel_facades.py:1738-1799`):**
   - Remove `del preview_token, dry_run` at L1760; replace with `del preview_token` (keep `dry_run` live).
   - After workspace_boundary_guard but before `coord = coordinator_for_facade(...)` at L1776, insert:
     ```python
     if dry_run:
         return RefactorResult(
             applied=False, no_op=False,
             diagnostics_delta=_empty_diagnostics_delta(),
             preview_token=f"pv_expand_macro_{int(time.time())}",
             duration_ms=0,
         ).model_dump_json(indent=2)
     ```

2. **In `ScalpelVerifyAfterRefactorTool.apply` (`scalpel_facades.py:1802-1862`):**
   - Remove `del preview_token, dry_run` at L1824; replace with `del preview_token`.
   - After workspace_boundary_guard but before `coord = coordinator_for_facade(...)` at L1840, insert the same dry_run short-circuit (with `pv_verify_{int(time.time())}`).

3. **Submodule pyright clean** — verify type-narrowing still holds with the early return.

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g2_dry_run_safety.py -x

# Existing facade tests unaffected:
uv run pytest vendor/serena/test/spikes/test_stage_3_t3_rust_wave_c.py -x

uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit message draft:**

```
fix(facade-safety): honor dry_run on expand_macro + verify_after_refactor (HI-12)

Both facades previously executed `del preview_token, dry_run` at entry,
silently dropping the safety contract. dry_run=True now short-circuits
BEFORE any LSP call (no flycheck side effects, no macro expansion work).

Closes spec § HI-12.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** none meaningful. The dry_run path returns a preview-token RefactorResult shape that callers already handle via the same pattern as every other facade.
- **Rollback:** revert the single commit. The bug is contained.

## Dependencies

- **Hard:** none. Independent of L-G1 (these facades are bespoke, do not route through the shared dispatcher).
- **Blocks:** L-G7-C (test-discipline retrofit references these facades' dry_run paths in its rewrite of `test_stage_3_t3_rust_wave_c.py`).

---

**Author:** AI Hive®.
