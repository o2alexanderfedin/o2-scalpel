# Leaf 05 — T11: 7 Cross-Language Multi-Server Tests

**Goal:** Land the 7 cross-language multi-server invariant tests deferred from v0.1.0 — one per merge invariant from the original plan §11.7. Each test exercises the `MultiServerCoordinator.merge_code_actions(...)` path against a real LSP boot and asserts the named invariant (priority, dedup, syntactic validity, workspace boundary, STALE_VERSION rejection, `disabled.reason` surfacing, namespace-package handling, circular-import handling).

## Precondition (cross-stream)

> **`v020-followups/03-multi-server-async-wrapping` MUST land before this leaf.** Per `stage-1h-results/PROGRESS.md:87`, today's `MultiServerCoordinator.merge_code_actions` is sync at the broadcast inner-loop site; without `asyncio.to_thread` wrapping in `broadcast._one`, every test in this leaf will surface `TypeError: object list can't be used in 'await' expression` rather than the merge-invariant failures the tests are meant to assert.
>
> Verification before starting this leaf:
> ```bash
> cd vendor/serena && grep -n "asyncio.to_thread" src/serena/refactoring/multi_server_coordinator.py
> ```
> Expected: at least one match in the `broadcast._one` body. If no match, the precondition has not landed; this leaf is blocked.

**Architecture:** Tests use `python_coordinator` (the 3-server merge from Stage 1D), `ra_lsp` (single-server Rust), and a synthetic stale-version setup for the apply-cleanly path. Each invariant gets one module so failures localize cleanly to the merge concern they probe.

**Tech stack:** pytest 8 + `pytest-asyncio`, the `MultiServerCoordinator` from Stage 1D, the `WorkspaceEdit` applier from v0.3.0, the `WorkspaceHealth` check from Stage 1F.

**Source spec:** original Stage 1H plan §File structure T25–T31 (lines 152–158) and §Task 11 (lines 5354–5919).

**Original Stage 1H task:** **T11** ("7 cross-language tests — multi-server merge invariants from §11.7"). Deferred per `stage-1h-results/PROGRESS.md:24`.

**Author:** AI Hive(R)

## File structure

| Path (under `vendor/serena/test/integration/`) | LoC | Targets fixtures | §11.7 invariant |
|---|---|---|---|
| `test_multi_server_organize_imports.py` | ~150 | `calcpy` (leaf 06) | inv 1 + 3: priority + dedup |
| `test_multi_server_workspace_boundary.py` | ~150 | `calcrs` (leaf 01) + `calcpy` | inv 4: out-of-workspace rejection |
| `test_multi_server_apply_cleanly.py` | ~120 | `calcpy` | inv 1: STALE_VERSION rejection |
| `test_multi_server_syntactic_validity.py` | ~150 | `calcrs` + `calcpy` | inv 2: post-apply parse |
| `test_multi_server_disabled_reason.py` | ~100 | `calcpy` | inv 3: `disabled.reason` surfacing |
| `test_multi_server_namespace_pkg.py` | ~120 | `calcpy_namespace` | PEP 420 edge case |
| `test_multi_server_circular_import.py` | ~120 | `calcpy_circular` (leaf 02) | circular-import detect+warn |

**LoC total:** ~910 honest sum. The original-plan §14.1 row totals come to ~910 for the 7 multi-server tests; the master orchestration §3 brief 4 cited a conservative ~600 deduplication estimate. This leaf surfaces the larger honest figure rather than over-promise on dedup at planning time.

## Tasks

Pattern: per the writing-plans skill rule "Similar to Task N — repeat the code", we define the **canonical TDD cycle for one test module** (Task 1 — `test_multi_server_organize_imports.py`) with full code, then list the 6 remaining modules with assertion intent + invariant + target fixtures. The implementer follows the same cycle.

### Task 1 — `test_multi_server_organize_imports.py` (canonical pattern)

- [ ] **Step 1: Write failing integration test**

Create `vendor/serena/test/integration/test_multi_server_organize_imports.py`:

```python
"""Stage 1H T11 — Multi-server invariant 1 (priority) + invariant 3 (dedup)
from original plan §11.7. pylsp + basedpyright + ruff all emit
organize-imports candidates; only ruff's source.organizeImports.ruff wins."""
from __future__ import annotations
import pytest
from pathlib import Path
from solidlsp.ls_types import Position, Range, TextDocumentIdentifier


pytestmark = pytest.mark.asyncio


async def test_organize_imports_dedups_to_one_winner(
    python_coordinator, calcpy_workspace
):
    """All three Python servers offer organize-imports; the merge result
    must surface exactly one applicable candidate per the priority order
    ruff > basedpyright > pylsp-rope (§11.7 invariant 1)."""
    src = calcpy_workspace / "calcpy" / "calcpy.py"
    text = src.read_text()
    n_lines = len(text.splitlines())
    rng = Range(start=Position(line=0, character=0),
                end=Position(line=n_lines - 1, character=0))
    merged = await python_coordinator.merge_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    organize = [a for a in merged.actions
                if "organize" in a.get("title", "").lower()
                and "import" in a.get("title", "").lower()
                and not a.get("disabled")]
    assert len(organize) == 1, \
        f"expected exactly 1 applicable organize-imports; got {len(organize)}: {[a.get('title') for a in organize]}"
    winner = organize[0]
    assert winner.get("source", "") == "ruff", \
        f"expected ruff to win priority; got source={winner.get('source')}"


async def test_organize_imports_other_servers_surfaced_disabled(
    python_coordinator, calcpy_workspace
):
    """The losers must still surface in the result list (§11.7 invariant 3)
    but with disabled.reason set so the agent can audit."""
    src = calcpy_workspace / "calcpy" / "calcpy.py"
    rng = Range(start=Position(line=0, character=0),
                end=Position(line=10, character=0))
    merged = await python_coordinator.merge_code_actions(
        TextDocumentIdentifier(uri=src.as_uri()), rng, context={"diagnostics": []}
    )
    losers = [a for a in merged.actions
              if "organize" in a.get("title", "").lower()
              and a.get("disabled")]
    sources = {a.get("source") for a in losers}
    assert sources <= {"pylsp", "basedpyright"}, \
        f"unexpected losing sources: {sources}"
    for a in losers:
        assert a["disabled"].get("reason"), f"loser missing disabled.reason: {a}"
```

Run: `cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/integration/test_multi_server_organize_imports.py -v`
Expected: **FAIL** — assertion error if the precondition has landed (`merge_code_actions` is now awaitable but the test surfaces a real merge-priority discrepancy); `TypeError: object list can't be used in 'await' expression` if the precondition has NOT landed (this is what the front-matter precondition block guards against).

- [ ] **Step 2: Re-confirm precondition still holds**

Re-run the front-matter verification command:

```bash
cd vendor/serena && grep -n "asyncio.to_thread" src/serena/refactoring/multi_server_coordinator.py
```

Expected: still at least one match. If absent, the precondition has regressed; this leaf is blocked.

- [ ] **Step 3: Re-run test — green**

Run: `cd vendor/serena && PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/integration/test_multi_server_organize_imports.py -v`
Expected: `2 passed`.

- [ ] **Step 4: Commit**

```bash
cd vendor/serena
git add test/integration/test_multi_server_organize_imports.py
git commit -m "test(stage-1h): add T11 multi-server organize-imports invariant tests (T25)

Co-Authored-By: AI Hive(R) <noreply@o2.services>"
```

### Tasks 2–7 — remaining 6 cross-language test modules (apply Task 1 pattern)

For each row below, repeat Task 1's 4-step cycle. Use `python_coordinator` for the Python merge tests, `ra_lsp` for Rust-only invariants, and a synthetic stale-version setup for the apply-cleanly path.

| # | Module slug | Sub-tests | §11.7 invariant | Assertion intent |
|---|---|---|---|---|
| 2 | `test_multi_server_workspace_boundary.py` | 3 | inv 4 + §11.8 | (a) basedpyright tries to write `target/debug/cache/x.py` (under `calcrs/target/`) — applier rejects with `OUT_OF_WORKSPACE`; (b) pylsp tries to write into `.venv/site-packages/foo/bar.py` — applier rejects; (c) the rejection is atomic — no partial application of the candidate edit |
| 3 | `test_multi_server_apply_cleanly.py` | 2 | inv 1 STALE_VERSION | (a) bump file `version` field on `TextDocumentIdentifier` mid-flight; merged edit is dropped with `STALE_VERSION` reason; (b) post-rejection, no edit applied to disk |
| 4 | `test_multi_server_syntactic_validity.py` | 3 | inv 2 post-apply parse | (a) for calcpy: a candidate with deliberate `SyntaxError`-introducing edit is filtered out, alternate candidate wins; (b) for calcrs: candidate that produces non-`cargo check`-clean Rust is filtered out; (c) when ALL candidates fail parse, merge result is empty (no auto-apply) |
| 5 | `test_multi_server_disabled_reason.py` | 2 | inv 3 disabled surfacing | (a) merge result surfaces all candidates including disabled ones; (b) `disabled.reason` is non-empty string for every disabled candidate (auditability gate) |
| 6 | `test_multi_server_namespace_pkg.py` | 2 | PEP 420 edge | (a) split-file flow on `calcpy_namespace/ns_root/calcpy_ns/core.py` does NOT introduce `__init__.py` (PEP 420 namespace package); (b) `python -c "import calcpy_ns.core"` works post-flow |
| 7 | `test_multi_server_circular_import.py` | 2 | circular-import detect | (a) extract-function flow on `calcpy_circular/a.py` detects the lazy-import-inside-body pattern and emits a warning candidate (`disabled.reason` = "circular_import_protection"); (b) auto-apply does not promote the lazy import to top-level — `from calcpy_circular import b` does NOT appear at module top after the flow |

### Self-review

- [ ] **Spec coverage:** original plan T25–T31 each map to a row above (7 modules total).
- [ ] **Placeholder scan:** Task 1 has full executable code; Tasks 2–7 specify exact assertion intent + invariant + target fixture per sub-test. No "TBD" / "appropriate" / "similar to" left.
- [ ] **Type consistency:** all modules import `solidlsp.ls_types.{Position, Range, TextDocumentIdentifier}` and use the conftest fixture names (`python_coordinator`, `ra_lsp`, `calcpy_workspace`, `calcrs_workspace`, `calcpy_namespace_workspace`, `calcpy_circular_workspace`).
- [ ] **Cross-stream deps called out:** the front-matter "Precondition (cross-stream)" block lists `v020-followups/03-multi-server-async-wrapping` with a one-line verification command — same pattern as leaf 04. Tasks 1 step 2 re-confirms the precondition still holds at execution time.
- [ ] **Helper reuse:** the `_assert_workspace_edit_round_trip` helper (defined in leaf 03 Task 1 step 2) handles edit application — DRY across 03/04/05.
