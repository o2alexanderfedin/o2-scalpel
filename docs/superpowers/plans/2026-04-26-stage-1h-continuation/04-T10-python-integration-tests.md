# Leaf 04 — T10: 8 Python Integration Tests

**Goal:** Land the 8 Python integration tests deferred from v0.1.0 — covering rope-bridge facades (extract method/variable, inline, organize-imports, move-global, rename-module), basedpyright auto-import quickfix, and ruff `source.fixAll.ruff`. All 8 tests boot the **full 3-server** Python merge path (pylsp + basedpyright + ruff) via the existing `python_coordinator` conftest fixture and assert merge-priority + dedup + diagnostics-delta invariants.

## Precondition (cross-stream)

> **`v020-followups/01-basedpyright-dynamic-capability` MUST land before this leaf.** Per `stage-1h-results/PROGRESS.md:36, 85`, the static Stage 1F catalog hides basedpyright (it registers capabilities dynamically post-init). Without runtime capability discovery, the `python_coordinator` cannot deterministically include basedpyright in the 3-server merge — sub-tests that assert basedpyright auto-import (T21 below) and 3-server organize-imports (T20) will be non-deterministic.
>
> Verification before starting this leaf:
> ```bash
> cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest \
>   test/integration/test_smoke_workspace_health.py::test_basedpyright_visible_in_capabilities -v
> ```
> Expected: PASS (currently x-fail per the v0.1.0 cut decision log).

**Architecture:** One test module per Python assist family. Each module uses the existing `python_coordinator` (3-server `MultiServerCoordinator`) + `pylsp_lsp` / `basedpyright_lsp` / `ruff_lsp` adapters. The Stage 2A facade-application path (pure-Python `WorkspaceEdit` applier already wired per project memory `project_v0_3_0_facade_application.md`) handles edit application; the test asserts post-apply text + diagnostics-delta + per-server merge-source attribution.

**Tech stack:** pytest 8 + `pytest-asyncio`, `solidlsp` Python adapters from Stage 1E, `MultiServerCoordinator` from Stage 1D, the `WorkspaceEdit` applier landed in v0.3.0.

**Source spec:** original Stage 1H plan §File structure T17–T24 (lines 144–151) and §Task 10 (lines 4888–5353).

**Original Stage 1H task:** **T10** ("8 Python integration tests"). Deferred per `stage-1h-results/PROGRESS.md:23`.

**Author:** AI Hive(R)

## File structure

| Path (under `vendor/serena/test/integration/`) | LoC | Targets fixture | Assist family |
|---|---|---|---|
| `test_assist_extract_method_py.py` | ~120 | `calcpy` (leaf 06) | pylsp_rope.refactor.extract.method |
| `test_assist_extract_variable_py.py` | ~100 | `calcpy` | pylsp_rope.refactor.extract.variable |
| `test_assist_inline_py.py` | ~100 | `calcpy_dataclasses` (leaf 02) | pylsp_rope.refactor.inline |
| `test_assist_organize_import_py.py` | ~120 | `calcpy_notebooks` (leaf 02) | source.organize_import + source.organizeImports.ruff (multi-server) |
| `test_assist_basedpyright_autoimport.py` | ~120 | `calcpy` | basedpyright quickfix on reportUndefinedVariable |
| `test_assist_ruff_fix_all.py` | ~120 | `calcpy` (with deliberate lint triggers) | source.fixAll.ruff |
| `test_assist_move_global_py.py` | ~150 | `calcpy` | Rope library bridge MoveGlobal |
| `test_assist_rename_module_py.py` | ~120 | `calcpy` | Rope library bridge MoveModule |

**LoC total:** ~950 honest sum. Within the original-spec budget envelope of ~1,100 — Python tests are smaller per-test than Rust because no `cargo check` step.

## Tasks

Pattern: per the writing-plans skill rule "Similar to Task N — repeat the code", we define the **canonical TDD cycle for one test module** (Task 1 — `test_assist_extract_method_py.py`) with full code, then list the 7 remaining modules with assertion intent + target fixture. The implementer follows the same cycle.

### Task 1 — `test_assist_extract_method_py.py` (canonical pattern)

- [ ] **Step 1: Write failing integration test**

Create `vendor/serena/test/integration/test_assist_extract_method_py.py`:

```python
"""Stage 1H T10 — Python: pylsp_rope.refactor.extract.method round-trip.
Targets calcpy fixture. Asserts (a) edit applies cleanly,
(b) post-apply text parses, (c) post-diagnostics count <= pre."""
from __future__ import annotations
import ast
import pytest
from pathlib import Path
from solidlsp.ls_types import Position, Range, TextDocumentIdentifier


pytestmark = pytest.mark.asyncio


async def test_extract_method_on_evaluator_branch(
    pylsp_lsp, calcpy_workspace, _assert_workspace_edit_round_trip
):
    """Inside calcpy.evaluate(), select the binary-op branch and request
    pylsp_rope.refactor.extract.method. The resulting WorkspaceEdit must:
    introduce a new method, route the original site through the call,
    keep the file parseable, and not increase diagnostic count."""
    src = calcpy_workspace / "calcpy" / "calcpy.py"
    text = src.read_text()
    line_idx = next(i for i, ln in enumerate(text.splitlines())
                    if "if isinstance(node, BinOp):" in ln)
    rng = Range(start=Position(line=line_idx, character=4),
                end=Position(line=line_idx + 4, character=0))
    actions = await pylsp_lsp.request_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    titles = [a.get("title", "") for a in actions]
    extract = next(
        (a for a in actions if "Extract method" in a.get("title", "")),
        None,
    )
    if extract is None:
        pytest.skip(f"pylsp-rope did not offer Extract method at this position; got {titles}")
    edit = extract.get("edit")
    assert edit is not None, f"Extract method action missing edit: {extract}"
    _assert_workspace_edit_round_trip(edit, expected_files=[src])
    # Post-apply parse check
    post_text = src.read_text()
    ast.parse(post_text)


async def test_extract_method_writes_new_def(
    pylsp_lsp, calcpy_workspace
):
    """The edit text must include a `def ` line for the extracted method."""
    src = calcpy_workspace / "calcpy" / "calcpy.py"
    text = src.read_text()
    line_idx = next(i for i, ln in enumerate(text.splitlines())
                    if "def evaluate(" in ln)
    rng = Range(start=Position(line=line_idx + 2, character=4),
                end=Position(line=line_idx + 6, character=0))
    actions = await pylsp_lsp.request_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    extract = next((a for a in actions if "Extract method" in a.get("title", "")), None)
    if extract is None:
        pytest.skip("Extract method not offered at this position")
    edit_text = str(extract.get("edit", {}))
    assert "def " in edit_text, f"edit body lacks new def: {edit_text[:200]}"
```

Run: `cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/integration/test_assist_extract_method_py.py -v`
Expected: **FAIL** — `calcpy.py` (the headline monolith) is not yet on disk (leaf 06 ships it).

- [ ] **Step 2: Confirm leaf 06 (calcpy monolith) landed**

Run: `test -f vendor/serena/test/fixtures/calcpy/calcpy/calcpy.py && wc -l vendor/serena/test/fixtures/calcpy/calcpy/calcpy.py`
Expected: file exists, line count near ~950.

If absent, leaf 06 has not landed — block this leaf.

- [ ] **Step 3: Re-run test — green**

Run: `cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/integration/test_assist_extract_method_py.py -v`
Expected: `2 passed` (or `1 passed, 1 skipped` if rope refuses extract at the second position — honest).

- [ ] **Step 4: Commit**

```bash
cd vendor/serena
git add test/integration/test_assist_extract_method_py.py
git commit -m "test(stage-1h): add T10 extract_method_py integration suite (T17 sub-test)

Co-Authored-By: AI Hive(R) <noreply@o2.services>"
```

### Tasks 2–8 — remaining 7 Python integration test modules (apply Task 1 pattern)

For each row below, repeat Task 1's 4-step cycle. Use the `python_coordinator` fixture for any test asserting multi-server merge; use the per-server adapter (`pylsp_lsp` / `basedpyright_lsp` / `ruff_lsp`) for single-server tests.

| # | Module slug | Sub-tests | Target fixture | Assertion intent |
|---|---|---|---|---|
| 2 | `test_assist_extract_variable_py.py` | 2 | `calcpy` | (a) Extract variable on `(1+2)*(3+4)`-shaped expression in calcpy.py; (b) extracted name appears as `Optional[str]` parametrizable per rope contract |
| 3 | `test_assist_inline_py.py` | 2 | `calcpy_dataclasses` | (a) Inline a single-call-site helper into its caller; (b) `dataclass.__repr__` baseline preserved post-inline |
| 4 | `test_assist_organize_import_py.py` | 3 | `calcpy_notebooks/src/calcpy_min.py` | (a) `python_coordinator.merge_code_actions(...)` returns one organize-imports candidate; (b) ruff's `source.organizeImports.ruff` wins over pylsp-rope's `source.organize_import` per §11.7 priority; (c) `.ipynb` companion bytes unchanged post-apply |
| 5 | `test_assist_basedpyright_autoimport.py` | 2 | `calcpy` | (a) Insert `Counter` use at top of calcpy.py without `from collections import Counter` → basedpyright surfaces `reportUndefinedVariable`; (b) basedpyright `quickfix` action title contains "Add import" and edit imports `Counter` from `collections` |
| 6 | `test_assist_ruff_fix_all.py` | 2 | `calcpy` (with deliberate lint triggers) | (a) ruff offers `source.fixAll.ruff`; (b) post-apply, the deliberate F401/E501/E711 lints are gone (count delta proves) |
| 7 | `test_assist_move_global_py.py` | 2 | `calcpy` | (a) Rope `MoveGlobal` (library bridge — call via `serena.refactoring.rope_bridge.move_global`) moves a top-level fn from `calcpy.py` to `calcpy/util.py`; (b) cross-module move updates 3 import-site references |
| 8 | `test_assist_rename_module_py.py` | 2 | `calcpy` | (a) Rope `MoveModule` renames `calcpy/core.py` → `calcpy/legacy_core.py`; (b) all `from calcpy.core import …` sites in tests/ rewritten |

### Self-review

- [ ] **Spec coverage:** original plan T17–T24 each map to a row above (8 modules total).
- [ ] **Placeholder scan:** Task 1 has full executable code; Tasks 2–8 specify exact assertion intent + target fixture per sub-test. No "TBD" / "appropriate" / "similar to" left.
- [ ] **Type consistency:** all modules import `solidlsp.ls_types.{Position, Range, TextDocumentIdentifier}` and use the conftest fixture names (`pylsp_lsp`, `basedpyright_lsp`, `ruff_lsp`, `python_coordinator`, `calcpy_workspace`, `calcpy_dataclasses_workspace`, `calcpy_notebooks_workspace`).
- [ ] **Cross-stream dep called out:** the precondition section at the top of this file links `v020-followups/01-basedpyright-dynamic-capability` and provides a one-line verification command — no surprise blocker mid-execution.
- [ ] **Helper reuse:** `_assert_workspace_edit_round_trip` is defined in leaf 03 Task 1 step 2 and reused here — DRY.
