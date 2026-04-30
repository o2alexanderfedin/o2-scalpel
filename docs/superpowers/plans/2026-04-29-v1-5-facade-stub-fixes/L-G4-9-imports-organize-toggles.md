# Leaf L-G4-9 — `ScalpelImportsOrganizeTool` honors `add_missing` / `remove_unused` / `reorder`

**Goal.** Stop discarding three of four user toggles (`scalpel_facades.py:958` `del add_missing, remove_unused, reorder, preview_token`). Today the facade dispatches a single `source.organizeImports` request that conflates all three behaviors; the caller cannot ask "remove unused only" or "sort only". This leaf maps each flag to a sub-kind, dispatches per enabled flag, and merges edits. Spec § HI-10.

**Strategy.** LSP `source.organizeImports` is the unified umbrella; servers expose finer-grained kinds:

| Flag | Sub-kind |
|---|---|
| `add_missing=True` | `quickfix.import` (rope's auto-import family) |
| `remove_unused=True` | `source.organizeImports.removeUnused` (ruff/pylsp) |
| `reorder=True` | `source.organizeImports.sortImports` (isort-style) |

When all three are True (the v1.4 default): dispatch all three sub-kinds and merge — equivalent to today's single `source.organizeImports` behavior. When the caller deselects one (e.g. `remove_unused=False`), the corresponding sub-kind is NOT dispatched.

**Source spec.** § HI-10 (lines 96-99).

**Author.** AI Hive®.

## Files to modify

| Path | Action | Approx LoC |
|---|---|---|
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit `ScalpelImportsOrganizeTool.apply` (L929-1051) — per-flag dispatch + merge | ~90 |
| `vendor/serena/test/spikes/test_v1_5_g4_9_imports_organize_toggles.py` | NEW | ~280 |

## TDD — failing test first

Create `vendor/serena/test/spikes/test_v1_5_g4_9_imports_organize_toggles.py`:

```python
"""v1.5 G4-9 — imports_organize honors add_missing / remove_unused / reorder (HI-10)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from serena.tools.scalpel_facades import ScalpelImportsOrganizeTool
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
        "import sys\n"
        "import os\n"
        "import json  # unused\n"
        "print(sys.version, os.path.exists)\n"
    )
    return tmp_path


def _make_tool(project_root: Path) -> ScalpelImportsOrganizeTool:
    tool = ScalpelImportsOrganizeTool.__new__(ScalpelImportsOrganizeTool)
    tool.get_project_root = lambda: str(project_root)  # type: ignore[method-assign]
    return tool


def _action(action_id, kind, provenance="ruff"):
    a = MagicMock()
    a.id = action_id; a.action_id = action_id; a.title = f"Apply {kind}"
    a.kind = kind; a.is_preferred = False; a.provenance = provenance
    return a


def test_remove_unused_only_dispatches_remove_unused_kind(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[dict] = []

    async def _actions(**kw):
        captured.append(kw)
        only = kw.get("only") or []
        if "removeUnused" in (only[0] if only else ""):
            return [_action("ruff:1", only[0])]
        return []

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {"changes": {src.as_uri(): [{
        "range": {"start": {"line": 2, "character": 0},
                  "end": {"line": 3, "character": 0}},
        "newText": "",
    }]}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            files=[str(src)],
            add_missing=False,
            remove_unused=True,
            reorder=False,
            language="python",
        )
    payload = json.loads(out)
    assert payload["applied"] is True
    only_values = [c.get("only") for c in captured]
    # Exactly one dispatch with the remove-unused kind:
    assert any("removeUnused" in str(o) for o in only_values), only_values
    # No dispatch for sortImports or quickfix.import:
    assert not any("sortImports" in str(o) for o in only_values), only_values
    assert not any("quickfix.import" in str(o) for o in only_values), only_values

    # Real-disk acid test: unused json import gone, others preserved:
    body = src.read_text(encoding="utf-8")
    assert "import json" not in body
    assert "import sys" in body
    assert "import os" in body


def test_all_three_flags_dispatch_all_three_kinds(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[str] = []

    async def _actions(**kw):
        only = (kw.get("only") or [""])[0]
        captured.append(only)
        return [_action("a:1", only)]

    fake_coord.merge_code_actions = _actions
    fake_coord.get_action_edit = lambda aid: {"changes": {}}

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        tool.apply(
            files=[str(src)],
            add_missing=True,
            remove_unused=True,
            reorder=True,
            language="python",
        )
    # All three sub-kinds dispatched:
    assert any("removeUnused" in c for c in captured), captured
    assert any("sortImports" in c for c in captured), captured
    assert any("quickfix.import" in c for c in captured), captured


def test_no_flags_is_no_op(python_workspace):
    tool = _make_tool(python_workspace)
    src = python_workspace / "main.py"
    fake_coord = MagicMock()
    fake_coord.supports_kind.return_value = True

    captured: list[str] = []

    async def _actions(**kw):
        captured.append((kw.get("only") or [""])[0])
        return []

    fake_coord.merge_code_actions = _actions

    with patch(
        "serena.tools.scalpel_facades.coordinator_for_facade",
        return_value=fake_coord,
    ):
        out = tool.apply(
            files=[str(src)],
            add_missing=False,
            remove_unused=False,
            reorder=False,
            language="python",
        )
    payload = json.loads(out)
    assert payload["no_op"] is True
    assert captured == []
```

Run: `uv run pytest vendor/serena/test/spikes/test_v1_5_g4_9_imports_organize_toggles.py -x`.

## Implementation steps

1. **Drop `add_missing, remove_unused, reorder` from `del`** at `scalpel_facades.py:958`.
2. **Build sub-kind list per call:**
   ```python
   sub_kinds: list[str] = []
   if remove_unused:
       sub_kinds.append("source.organizeImports.removeUnused")
   if reorder:
       sub_kinds.append("source.organizeImports.sortImports")
   if add_missing:
       sub_kinds.append("quickfix.import")
   if not sub_kinds:
       return RefactorResult(applied=False, no_op=True, ...).model_dump_json(indent=2)
   ```
3. **Replace the single-kind loop (L988-997)** with a per-file × per-kind loop:
   ```python
   all_actions: list[Any] = []
   captured_edits: list[dict[str, Any]] = []
   for f in files:
       for kind in sub_kinds:
           if not coord.supports_kind(lang, kind):
               continue  # skip silently when server doesn't expose this sub-kind
           start, end = compute_file_range(f)
           actions = _run_async(coord.merge_code_actions(
               file=f, start=start, end=end, only=[kind],
           ))
           for a in actions:
               all_actions.append(a)
               edit = _resolve_winner_edit(coord, a)
               if isinstance(edit, dict) and edit:
                   captured_edits.append(edit)
   ```
4. **Use `compute_file_range`** (closes part of HI-13 for imports_organize; G5 leaf becomes a no-op for this site after this lands).
5. **Submodule pyright clean.**

## Verification

```bash
uv run pytest vendor/serena/test/spikes/test_v1_5_g4_9_imports_organize_toggles.py -x
uv run pytest vendor/serena/test/spikes/test_stage_2a_t6_imports_organize.py -x  # regression
uv run pyright vendor/serena/src/serena/tools/scalpel_facades.py
```

**Atomic commit:**

```
fix(imports_organize): honor add_missing / remove_unused / reorder (HI-10)

Maps each flag to a sub-kind dispatch (removeUnused / sortImports /
quickfix.import); merges resulting edits. False flags omit the dispatch
entirely. Caller can now ask "remove unused only" or "sort only".

Closes the (0,0)→(0,0) range bug in this site by routing through
compute_file_range (per HI-13).

Authored-by: AI Hive®
```

## Risk + rollback

- **Risk:** some pylsp+ruff combinations may not advertise all three sub-kinds. Mitigation: per-kind capability gate (`coord.supports_kind`) silently skips unsupported sub-kinds; the no-op path with all three off is the test counterpoint.
- **Rollback:** revert single commit.

## Dependencies

- **Hard:** L-G1.
- **Blocks:** L-G5 (this leaf closes the imports_organize (0,0) site).
- **Blocks:** L-G7-B real-disk tests for imports_organize.

---

**Author:** AI Hive®.
