# Leaf L-G4-8 — `ScalpelFixLintsTool` honors `rules`

**Goal.** Stop discarding `rules` (`scalpel_facades.py:2212` `del preview_token, rules, language`). Today the facade dispatches `source.fixAll.ruff` once and ruff applies its full auto-fix set regardless of the caller's allow-list. This leaf wires `rules` to a per-rule dispatch that runs `source.fixAll.ruff` once per rule with `arguments=[{"select": [rule]}]` and merges the resulting edits — the same merge pattern already used by `_split_python` and `imports_organize`. Spec § HI-9.

**Strategy.** Two paths considered:

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Per-rule dispatch + merge** | Honest filter; ruff truly only auto-fixes the listed rules | N LSP calls per facade invocation | **Chosen** — N is bounded (caller-supplied list, typically 1-5) |
| **Single dispatch + post-filter** | One LSP call | Requires understanding ruff's emitted diagnostics-to-fix mapping; brittle to ruff version | Rejected |

When `rules is None or rules == []`, behavior is unchanged: one `source.fixAll.ruff` dispatch covers the full auto-fix set (matches today's silent behavior, but now documented as the explicit "all rules" path).

**Source spec.** § HI-9 (lines 91-94).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelFixLintsTool.apply` (L2185-2264) — per-rule dispatch + merge | ~80 |
| `vendor/serena/test/spikes/test_v1_5_g4_8_fix_lints_rules.py` | NEW | ~250 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_8_fix_lints_rules.py`:

```python
"""v1.5 G4-8 — fix_lints honors rules allow-list (HI-9)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelFixLintsTool
from serena.tools.scalpel_runtime import ScalpelRuntime


@pytest.fixture(autouse=True)
def reset_runtime():
    ScalpelRuntime.reset_for_testing()
    yield
    ScalpelRuntime.reset_for_testing()


@pytest.fixture
def python_workspace(tmp_path: Path) -> Path:
    src = tmp_path / "main.py"
    src.write_text(
        "import os\n"
        "import os  # I001 dup\n"
        "x = 1  # E501 line-length placeholder\n"
    )
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelFixLintsTool:
    tool = ScalpelFixLintsTool.__new__(ScalpelFixLintsTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, title):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = title
    a.kind = "source.fixAll.ruff"; a.is_preferred = False; a.provenance = "ruff"
    return a


def test_fix_lints_with_rules_dispatches_per_rule(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _actions(**kw):
        captured.append(kw)
        return [_action(f"ruff:{kw.get('arguments') or '_'}",
                        f"Fix {kw.get('arguments')}")]

    fake_coord.merge_code_actions = _actions

    def _resolve(aid):
        if "I001" in aid:
            # Removes the duplicate import:
            return {"changes": {src.as_uri(): [{
                "range": {"start": {"line": 1, "character": 0},
                          "end": {"line": 2, "character": 0}},
                "newText": "",
            }]}}
        return None  # F401 / others not requested

    fake_coord.get_action_edit = _resolve

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            rules=["I001"],
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True

    # Per-rule dispatch: exactly ONE call, with I001 in arguments:
    assert len(captured) == 1
    args0 = captured[0].get("arguments") or [{}]
    select = args0[0].get("select") if args0 else None
    assert select == ["I001"], captured

    # Real-disk acid test: I001 dup line removed:
    body = src.read_text(encoding="utf-8")
    assert body.count("import os") == 1


def test_fix_lints_no_rules_means_all(python_workspace):
    """rules=None preserves today's behavior — one dispatch with no select filter."""
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _actions(**kw):
        captured.append(kw)
        return [_action("ruff:1", "Fix all")]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {"changes": {src.as_uri(): [{
        "range": {"start": {"line": 1, "character": 0},
                  "end": {"line": 2, "character": 0}},
        "newText": "",
    }]}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            file=str(src),
            rules=None,
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    assert len(captured) == 1
    args0 = captured[0].get("arguments")
    # No select filter → arguments either absent or no `select` key:
    assert not args0 or not (args0[0] or {}).get("select")
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_8_fix_lints_rules.py -x`.

## Implementation steps

1. **Drop `rules` from `del`** at `scalpel_facades.py:2212`.
2. **Replace the single dispatch (L2227-2233)** with a loop:
   ```python
   if rules:
       all_actions: list[Any] = []
       captured_edits: list[dict[str, Any]] = []
       for rule in rules:
           actions_per_rule = _run_async(coord.merge_code_actions(
               file=file,
               start={"line": 0, "character": 0},
               end=compute_file_range(file)[1],   # G5 site lift; falls back to (0,0) if file empty
               only=[_FIX_LINTS_KIND],
               arguments=[{"select": [rule]}],
           ))
           for action in actions_per_rule:
               all_actions.append(action)
               edit = _resolve_winner_edit(coord, action)
               if isinstance(edit, dict) and edit:
                   captured_edits.append(edit)
       merged = _merge_workspace_edits(captured_edits)
   else:
       # Existing single-dispatch path with full auto-fix set.
       actions = _run_async(coord.merge_code_actions(...))
       ...
   ```
3. **Use `compute_file_range`** for the end position (closes part of HI-13 for fix_lints; G5 leaf only needs to handle the unhandled remainder). Add `from solidlsp.util.file_range import compute_file_range` at the top of the file or local-import inside the function.
4. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_8_fix_lints_rules.py -x
uv run pytest vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(fix_lints): honor rules via per-rule dispatch + merge (HI-9)

Replaces single source.fixAll.ruff dispatch with N dispatches (one per
caller-supplied rule), merging edits via _merge_workspace_edits.
rules=None preserves the full auto-fix-all behavior.

Replaces the (0,0)→(0,0) end position with compute_file_range — closes
half of HI-13 for this site (G5 covers the remainder).

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** ruff doesn't honor `select` in the codeAction arguments payload. Mitigation: verify against ruff-lsp v0.0.x docs in execution; if not honored, fall back to per-rule dispatch via separate `kind` registrations (`source.fixAll.ruff.<rule>`) if exposed, else surface as `INPUT_NOT_HONORED`.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1 (uses default-path `actions[0]` selection).
- **Blocks:** L-G5 (this leaf closes the fix_lints (0,0) site; G5 only handles the imports_organize site after this lands).
- **Blocks:** L-G7-B real-disk tests for fix_lints.

---

**Author:** AI Hive®.
