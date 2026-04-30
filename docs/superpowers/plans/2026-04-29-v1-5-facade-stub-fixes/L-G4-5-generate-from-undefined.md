# Leaf L-G4-5 — `ScalpelGenerateFromUndefinedTool` honors `target_kind`

**Goal.** Stop discarding `target_kind` (`scalpel_facades.py:2121` `del preview_token, target_kind, language`). Today the facade dispatches a single `quickfix.generate` and rope picks whatever first candidate is (typically a function regardless of caller's choice). After G1, this leaf maps `target_kind ∈ {function, class, variable}` to a per-kind dispatch using rope's exposed sub-kinds. Spec § HI-6.

**Strategy.** Two paths considered:

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Per-kind dispatch** — extend `_GENERATE_FROM_UNDEFINED_KIND` to a table mapping `target_kind` → `quickfix.generate.<kind>` | Honest LSP-level filtering | Depends on rope offering sub-kinds; existing rope API uses `quickfix.generate` flat | Try first |
| **Title-match via G1** — keep flat `quickfix.generate`, threaded `title_match=target_kind` (e.g. "function") | Reuses G1 substrate | rope titles vary; substring `"function"` may collide with `"functional"` etc. | Fallback |

The test below asserts ONE dispatch with the correctly filtered `only=[...]` argument. If the title-match fallback turns out to be needed in execution (rope flat-kind only), the leaf adapts: same test, same external behavior, internal swap of strategy.

**Source spec.** § HI-6 (lines 76-79).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelGenerateFromUndefinedTool.apply` (L2097-2133); extend kind mapping | ~50 |
| `vendor/serena/test/spikes/test_v1_5_g4_5_generate_from_undefined.py` | NEW | ~200 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_5_generate_from_undefined.py`:

```python
"""v1.5 G4-5 — generate_from_undefined honors target_kind (HI-6)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelGenerateFromUndefinedTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def python_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "calc.py"
    src.write_text("def main():\n    x = compute()\n")
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelGenerateFromUndefinedTool:
    tool = ScalpelGenerateFromUndefinedTool.__new__(ScalpelGenerateFromUndefinedTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title, kind):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title
    a.kind = kind; a.is_preferred = False; a.provenance = "pylsp-rope"
    return a


def test_generate_from_undefined_target_class_dispatches_class_kind(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "calc.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _actions(**kw):
        captured.append(kw)
        return [_action("rope:1", "Generate class compute",
                        "quickfix.generate.class")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 2, "character": 0},
                      "end": {"line": 2, "character": 0}},
            "newText": "class compute:\n    pass\n",
        }]},
    }

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 1, "character": 8},
            target_kind="class",
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    # Dispatch carries class-specific kind:
    assert any(
        "class" in str(c.get("only") or "")
        for c in captured
    ), captured
    assert "class compute" in src.read_text(encoding="utf-8")


def test_generate_from_undefined_target_variable_dispatches_variable_kind(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "calc.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _actions(**kw):
        captured.append(kw)
        return [_action("rope:1", "Generate variable compute",
                        "quickfix.generate.variable")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {
        "changes": {src.as_uri(): [{
            "range": {"start": {"line": 0, "character": 0},
                      "end": {"line": 0, "character": 0}},
            "newText": "compute = None\n",
        }]},
    }

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            position={"line": 1, "character": 8},
            target_kind="variable",
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    assert any(
        "variable" in str(c.get("only") or "")
        for c in captured
    ), captured
    assert "compute = None" in src.read_text(encoding="utf-8")
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_5_generate_from_undefined.py -x`.

## Implementation steps

1. **Drop `target_kind` from `del`** at `scalpel_facades.py:2121`.
2. **Replace the single-kind dispatch** with a per-target-kind table:
   ```python
   _GENERATE_FROM_UNDEFINED_KIND_BY_TARGET: dict[str, str] = {
       "function": "quickfix.generate.function",
       "class":    "quickfix.generate.class",
       "variable": "quickfix.generate.variable",
   }
   ```
3. **Inside `apply`**, look up `kind = _GENERATE_FROM_UNDEFINED_KIND_BY_TARGET.get(target_kind)` and pass it to `_python_dispatch_single_kind(...)`. Fall back to `quickfix.generate` + `title_match=target_kind` if `coord.supports_kind` returns False for the granular kind (forward-compat for older rope).
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_5_generate_from_undefined.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py -x
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(generate_from_undefined): honor target_kind via per-kind dispatch (HI-6)

Maps {function, class, variable} → quickfix.generate.<kind> with a
title_match fallback for older rope versions that emit only the flat
quickfix.generate.

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** rope versions vary on whether `quickfix.generate.<kind>` is exposed. Mitigation: capability-gate via `coord.supports_kind`; fallback to flat kind + title_match.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G7-B real-disk tests for generate_from_undefined.

---

**Author:** AI Hive®.
