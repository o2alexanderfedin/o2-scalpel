# Leaf 05 — E1-py Flake Root-Cause and Fix

> **STATUS: SHIPPED 2026-04-26** — see `stage-v0.2.0-followups-complete` tag (parent + submodule). Cross-reference: `docs/gap-analysis/WHAT-REMAINS.md` §4 line 108 + `docs/superpowers/plans/stage-1h-results/PROGRESS.md` §88 (E1-py bullet).
>
> **Implementation deviations from this plan** (recorded post-shipment):
> - Flake did NOT reproduce on the impl host (30/30 + 100/100 applies). Per spec's "if flake doesn't reproduce" branch, Task 3's facade fix was SKIPPED. The strip-the-skip change tightens the contract regardless. Empirical ledger committed at `vendor/serena/test/e2e/_e1_py_diagnostic_ledger.json`.
> - Note: P5a SHIP/B decision (per `docs/superpowers/plans/2026-04-26-decision-p5a-mypy.md`, ratified 2026-04-27) is now load-bearing for L05's underlying multi-LSP merge path.

**Goal.** Root-cause and fix the E1-py flake (Stage 2B observed gap) so `test_e1_py_4way_split_byte_identical` returns a deterministic PASS instead of `pytest.skip(... applied=False ...)`. Closes WHAT-REMAINS.md §4 line 106 and the E1-py bullet in `docs/gap-analysis/D-debt.md` §7 (commit `2ee21f8` for context).

**Architecture.** The current test (`vendor/serena/test/e2e/test_e2e_e1_py_split_file_python.py`) runs the 4-way split, then **conditionally** asserts byte-identity only when `payload.get("applied") is True`; otherwise it skips with the `failure` reason. The "skip on applied=False" path masks an underlying nondeterminism in the split-file facade dispatcher. Our task: (1) reproduce 10× under `pytest -p no:randomly --count=10`; (2) capture the failure reason payload across runs; (3) trace to the root-cause site (likely a stale `pylsp` source-map or basedpyright pull-mode timing window); (4) fix at the root; (5) flip the `pytest.skip` into an assertion failure so future regressions are loud.

**Tech Stack.** Python 3.13, pytest, `pytest-repeat`, the existing `mcp_driver_python` fixture. Reference WHAT-REMAINS.md §2 (inspect.getsource flakes are a separate stream) and `decision-p5a-mypy` (must ratify SHIP-vs-DROP first because the split path runs the multi-LSP merge which depends on whether mypy participates).

**Source spec.** `stage-1h-results/PROGRESS.md:88` (E1-py flake bullet inside the §Concerns/follow-ups block — the upstream evidence anchor); `vendor/serena/test/e2e/test_e2e_e1_py_split_file_python.py:88-91` (the skip site); WHAT-REMAINS.md §4 line 106.

**Author.** AI Hive(R).

## File Structure

| Path | Action | Approx LoC |
|------|--------|------------|
| `vendor/serena/test/e2e/test_e2e_e1_py_split_file_python.py` | edit — strip skip path; demand applied=true | ~10 (delta) |
| `vendor/serena/test/e2e/_e1_py_diagnostic.py` | new — instrumentation harness for the 10× repro | ~140 |
| `vendor/serena/src/serena/tools/scalpel_facades.py` | edit — root-cause fix at split-file dispatch | ~15 (delta) |
| `vendor/serena/test/e2e/test_e2e_e1_py_determinism.py` | new — repeat-N determinism test | ~80 |

## Tasks

### Task 1 — Failing determinism test (10× repro)

Create `vendor/serena/test/e2e/test_e2e_e1_py_determinism.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.parametrize("run_index", range(10))
def test_e1_py_split_applies_every_run(
    mcp_driver_python,
    calcpy_e2e_root: Path,
    run_index: int,
) -> None:
    src = calcpy_e2e_root / "calcpy" / "calcpy.py"
    payload = json.loads(mcp_driver_python.split_file(
        file=str(src),
        groups={
            "ast": ["Num", "Add", "Sub", "Mul", "Div", "Expr"],
            "errors": ["CalcError", "ParseError", "DivisionByZero"],
            "parser": ["parse"],
            "evaluator": ["evaluate"],
        },
        parent_layout="file",
        reexport_policy="preserve_public_api",
        dry_run=False,
        language="python",
    ))
    assert payload.get("applied") is True, (
        f"run {run_index}: applied=False; failure={payload.get('failure')!r}; "
        f"full payload={payload!r}"
    )
```

Run `uv run pytest vendor/serena/test/e2e/test_e2e_e1_py_determinism.py -x -p no:randomly` — expect at least one failure across the 10 runs. Capture `failure` payload values to console. Stage the test only.

### Task 2 — Build instrumentation harness

Create `vendor/serena/test/e2e/_e1_py_diagnostic.py`:

```python
"""Instrumentation harness for the E1-py flake.

Runs the split 30 times back-to-back, recording for each run:
  - returncode of the dispatch
  - `applied` flag
  - `failure` reason string (if any)
  - timestamps for: facade entry, multi-LSP merge complete, applier complete

Drops a JSON ledger at /tmp/e1py-flake-<timestamp>.json for offline analysis.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def run_one(driver: Any, src: Path) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = json.loads(driver.split_file(
        file=str(src),
        groups={
            "ast": ["Num", "Add", "Sub", "Mul", "Div", "Expr"],
            "errors": ["CalcError", "ParseError", "DivisionByZero"],
            "parser": ["parse"],
            "evaluator": ["evaluate"],
        },
        parent_layout="file",
        reexport_policy="preserve_public_api",
        dry_run=False,
        language="python",
    ))
    return {
        "elapsed_s": time.perf_counter() - t0,
        "applied": payload.get("applied"),
        "failure": payload.get("failure"),
        "checkpoint_id": payload.get("checkpoint_id"),
    }


def collect(driver: Any, src: Path, n: int = 30) -> list[dict[str, Any]]:
    return [run_one(driver, src) for _ in range(n)]
```

Run the harness against the local fixture. Inspect `failure` strings. Likely root-causes (TRIZ — segmentation: split apply-vs-discover):

1. **basedpyright pull-mode race** — pull arrives after merge, downgrading actions to a stale subset (P4 spike).
2. **Stale source-map in pylsp-rope** after a prior test mutated `calcpy.py` and the file watcher hasn't fired.
3. **Checkpoint LRU eviction** — `applied=False` because the previous checkpoint's edit set was evicted before `apply_workspace_edit`.

Document the actual observed cause in the commit message. Stage only.

### Task 3 — Root-cause fix

Locate the dispatch in `scalpel_facades.py` (search for `def split_file` then trace to the multi-server merge call). Apply the minimal fix corresponding to the observed cause. Examples (pick one based on Task 2 evidence):

**If basedpyright pull-mode race:**
```python
# Before merging, force a synchronous pull on the source file so all servers
# observe identical state. References q3-basedpyright-pinning.md §3.
await coordinator.synchronize_pull_diagnostics(file=src, timeout_s=2.0)
```

**If stale source-map:**
```python
# Force file-watcher flush; pylsp-rope keys its source-map off mtime+inode.
self._poke_filewatcher(src)
```

**If checkpoint eviction:**
```python
# Ensure split-file holds its checkpoint open across the apply boundary.
with self._checkpoints.pin(checkpoint_id):
    apply_workspace_edit(edit)
```

**Escape hatch.** If the harness ledger from Task 2 does not match any of the three hypotheses above (e.g. `failure` strings reference a fourth subsystem such as `WorkspaceEdit` document-version mismatch, `TextDocumentSync` queue stall, or a pylsp-rope thread-pool exhaustion message), STOP and spawn a research subtask before patching. Per project CLAUDE.md "Problem Resolution" rule, blind patches against an un-modelled failure mode produce regression risk. The research subtask must (a) post the full ledger to `/tmp/e1py-flake-<ts>.json`, (b) cross-reference against `docs/superpowers/plans/spike-results/P5a.md` and `stage-1h-results/PROGRESS.md:88`, (c) propose a fourth hypothesis with a falsifiable test, and (d) return that hypothesis to this task before any code edit.

Re-run determinism test 10× with `-p no:randomly`. Must be 10/10 green. Commit `fix(stage-v0.2.0-followup-05a): root-cause E1-py flake at <observed-site>` with the harness ledger linked.

### Task 4 — Strip the skip path

Edit `vendor/serena/test/e2e/test_e2e_e1_py_split_file_python.py` lines 87-91:

```python
    assert payload.get("applied") is True, (
        f"E1-py split must apply deterministically; got payload={payload!r}"
    )
    assert payload.get("checkpoint_id"), f"applied=true but no checkpoint_id: {payload}"
    init_text = init.read_text(encoding="utf-8")
    for name in ("CalcError", "DivisionByZero", "Expr", "evaluate", "parse"):
        assert name in init_text, f"__all__ lost {name!r} after split"
    post_rc, post_stdout = _run_pytest_q(calcpy_e2e_root, python_bin)
    assert post_rc == 0, f"post-split pytest failed: rc={post_rc}\n{post_stdout}"
    assert post_stdout == pre_stdout, (
        f"pytest -q stdout drifted across split:\n--- pre ---\n{pre_stdout}\n--- post ---\n{post_stdout}"
    )
```

(Drop the `else: pytest.skip(...)` branch entirely.) Run `uv run pytest vendor/serena/test/e2e/test_e2e_e1_py_split_file_python.py -x` — green. Commit `test(stage-v0.2.0-followup-05b): E1-py is now an unconditional assertion`.

### Task 5 — Self-review and tag

Run the full `pytest -m e2e -p no:randomly --count=5` covering E1-py + E9-py + E10-py — all 15 green. `git tag stage-v0.2.0-followup-05-e1-py-flake-rootcause-complete`.

## Self-Review Checklist

- [ ] 10/10 deterministic passes under `pytest -p no:randomly --count=10`.
- [ ] `pytest.skip` removed; future flakes will fail loudly.
- [ ] Root-cause documented in commit message (not "added retry").
- [ ] D-debt.md §7 entry crossed off (single-source update only).
- [ ] If a fourth hypothesis was needed, the research subtask's findings are linked from the commit message and from D-debt.md §7.
- [ ] Author = AI Hive(R), no emoji, no time estimates.
