# Fix inspect.getsource(cls.apply) Flakes Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use `- [ ]` checkboxes.

**Goal:** Eliminate the 6 `inspect.getsource(cls.apply)` flakes in Stage 2A/3 spike fixtures via one root-cause fix that captures and exposes a stable source string for every facade Tool's `apply` method.

**Architecture:** Attach an explicit `__wrapped_source__` attribute to each Stage 2A/3 facade Tool's `apply` method at module-import time. The 6 test sites switch from raw `inspect.getsource(cls.apply)` (linecache-dependent, documented flake source per `docs/gap-analysis/D-debt.md` §2) to `get_apply_source(cls)` which prefers the captured attribute and falls back to `inspect.getsource`. One-shot capture at import — no runtime wrapping. Author: AI Hive(R).

**Tech Stack:** Python 3.11; `inspect`; pytest 8.4.1 + pytest-xdist 3.8.0 (already pinned in `vendor/serena/pyproject.toml`). No new runtime deps. Determinism is verified with a portable shell loop — neither `pytest-repeat` nor `pytest-randomly` is installed and adding them is YAGNI.

**Decision: Remediation (b) — explicit `__wrapped_source__` attachment.** The 26 `Scalpel*Tool.apply` methods (verified by `grep -n "^class Scalpel" vendor/serena/src/serena/tools/scalpel_facades.py`) are **not** wrapped — `workspace_boundary_guard()` is called inline. Remediation (a) (`functools.WRAPPER_ASSIGNMENTS`-aware extraction) has no wrapper to chase. The flake is a `linecache` / filesystem race in `inspect.getsource`. Capturing once at import eliminates the race; (b) is explicit, survives future re-decoration, trivial to audit.

**Master Brief 2 callout (divergence owned).** MASTER §3 Brief 2 promises a fix at "the safety-call wrapper site (`scalpel_facades.py:1002`)". Verified by reading lines 995–1003: `:1002` is **inside the docstring** of the shared `_apply_single_action` dispatcher (the literal "the safety call stays visible in `inspect.getsource(cls.apply)`"), not a wrapper. There is no decorator there to fix. Root-cause therefore moves to module-bottom attribute attachment, honouring the brief's *intent* (one fix, not per-test masks) while correcting its *site*.

**Sizing: Small, ~155 LoC, ~22 ≤5-LoC steps across 6 tasks.**

---

## File Structure

| Path | Role |
|---|---|
| `vendor/serena/src/serena/tools/facade_support.py` | Add `attach_apply_source(cls)` + `get_apply_source(cls)`. |
| `vendor/serena/src/serena/tools/scalpel_facades.py` | Loop-attach `__wrapped_source__` for every `Scalpel*Tool` class at module bottom. |
| `vendor/serena/test/unit/test_facade_support_apply_source.py` | New unit test for the helpers. |
| `vendor/serena/test/spikes/test_apply_source_determinism.py` | New regression test — 100 calls per facade, identical output. |
| `vendor/serena/test/spikes/test_stage_3_t{1,2,3,4,5}_*.py` & `test_stage_2a_t9_registry_smoke.py` | Switch the 6 `inspect.getsource(cls.apply)` sites to `get_apply_source(cls)`. |

---

## Task 1: Pin determinism contract (regression test)

**Files:** Create `vendor/serena/test/spikes/test_apply_source_determinism.py`. `_FACADE_NAMES` (Step 1 below) is the **verified union of all 25 classes** the 6 spike sites inspect (4+4+4+4+4 = 20 in t1–t5, plus 5 in `SCALPEL_2A_TOOLS` minus `ScalpelTransactionCommitTool`). Source: `grep -nE "Scalpel[A-Za-z]+Tool" vendor/serena/test/spikes/test_stage_*` cross-referenced against `grep -n "^class Scalpel" vendor/serena/src/serena/tools/scalpel_facades.py` (2026-04-26).

- [ ] **Step 1: Write the failing regression test**

```python
"""Reproduce the inspect.getsource(cls.apply) flake (D-debt.md §2).

inspect.getsource consults linecache, which is unstable across xdist
workers and pyc-only loads. This test calls the introspection path 100
times per facade class and asserts identical, non-empty output.
"""
from __future__ import annotations

import inspect

import pytest

import serena.tools as tools_module

# Verified union of classes the 6 spike sites inspect (t1/t2/t3/t4/t5: 4 each;
# 2A registry smoke: SCALPEL_2A_TOOLS minus TransactionCommit = 5).
_FACADE_NAMES = (
    "ScalpelConvertModuleLayoutTool", "ScalpelChangeVisibilityTool",
    "ScalpelTidyStructureTool", "ScalpelChangeTypeShapeTool",
    "ScalpelChangeReturnTypeTool", "ScalpelCompleteMatchArmsTool",
    "ScalpelExtractLifetimeTool", "ScalpelExpandGlobImportsTool",
    "ScalpelGenerateTraitImplScaffoldTool", "ScalpelGenerateMemberTool",
    "ScalpelExpandMacroTool", "ScalpelVerifyAfterRefactorTool",
    "ScalpelConvertToMethodObjectTool", "ScalpelLocalToFieldTool",
    "ScalpelUseFunctionTool", "ScalpelIntroduceParameterTool",
    "ScalpelGenerateFromUndefinedTool", "ScalpelAutoImportSpecializedTool",
    "ScalpelFixLintsTool", "ScalpelIgnoreDiagnosticTool",
    "ScalpelSplitFileTool", "ScalpelExtractTool", "ScalpelInlineTool",
    "ScalpelRenameTool", "ScalpelImportsOrganizeTool",
)


@pytest.mark.parametrize("cls_name", _FACADE_NAMES)
def test_apply_source_is_stable_across_repeated_calls(cls_name: str) -> None:
    cls = getattr(tools_module, cls_name)
    samples = [inspect.getsource(cls.apply) for _ in range(100)]
    first = samples[0]
    assert first, f"{cls_name}.apply source must be non-empty"
    assert all(s == first for s in samples), (
        f"{cls_name}.apply source non-deterministic across 100 calls"
    )
    assert "workspace_boundary_guard(" in first
```

- [ ] **Step 2: Pin contract** — `cd vendor/serena && for i in $(seq 1 10); do uv run pytest test/spikes/test_apply_source_determinism.py -v -p no:cacheprovider; done` — Expected: 10/10 PASS once Task 3 lands. Pre-Task-3, intermittent fail is acceptable but at least one of the 10 runs MUST pass to prove the test is well-formed.

- [ ] **Step 3: Commit** — `git add vendor/serena/test/spikes/test_apply_source_determinism.py && git commit -m "test(stage-3): pin apply-source determinism contract" -m "Co-authored-by: AI Hive(R) <noreply@aihive.local>"`

---

## Task 2: Add `attach_apply_source` + `get_apply_source` helpers

**Files:** Modify `vendor/serena/src/serena/tools/facade_support.py`; create `vendor/serena/test/unit/test_facade_support_apply_source.py`.

- [ ] **Step 1: Write the failing unit test** (at the new file path)

```python
"""Unit coverage for attach_apply_source / get_apply_source helpers."""
from __future__ import annotations

import inspect

from serena.tools.facade_support import (
    attach_apply_source,
    get_apply_source,
)


class _SampleTool:
    def apply(self, x: int) -> int:
        # workspace_boundary_guard(  # marker
        return x + 1


def test_attach_apply_source_captures_inspect_getsource_once() -> None:
    attach_apply_source(_SampleTool)
    captured = getattr(_SampleTool.apply, "__wrapped_source__", None)
    assert isinstance(captured, str) and captured
    assert captured == inspect.getsource(_SampleTool.apply)


def test_get_apply_source_prefers_captured_attribute() -> None:
    attach_apply_source(_SampleTool)
    _SampleTool.apply.__wrapped_source__ = "SENTINEL_CAPTURED_VALUE"
    assert get_apply_source(_SampleTool) == "SENTINEL_CAPTURED_VALUE"


def test_get_apply_source_falls_back_to_inspect_getsource() -> None:
    class _UnattachedTool:
        def apply(self) -> None:
            return None

    assert "def apply" in get_apply_source(_UnattachedTool)
```

- [ ] **Step 2: Run to verify FAIL** — `cd vendor/serena && uv run pytest test/unit/test_facade_support_apply_source.py -v` — expected: `ImportError: cannot import name 'attach_apply_source'`.

- [ ] **Step 3: Implement helpers in facade_support.py**

Insert immediately **before** the `__all__` block (currently lines 171–179) in `vendor/serena/src/serena/tools/facade_support.py`:

```python
def attach_apply_source(cls: type) -> None:
    """Capture ``inspect.getsource(cls.apply)`` once and stash it as
    ``__wrapped_source__`` so downstream introspection is independent of
    ``linecache``. Idempotent. No-op when ``cls`` has no ``apply`` or when
    ``inspect.getsource`` raises (frozen / built-in / pyc-only)."""
    import inspect as _inspect
    fn = cls.__dict__.get("apply") or getattr(cls, "apply", None)
    if fn is None:
        return
    try:
        src = _inspect.getsource(fn)
    except (OSError, TypeError):
        return
    try:
        fn.__wrapped_source__ = src  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        return


def get_apply_source(cls: type) -> str:
    """Deterministic source for ``cls.apply``. Prefers the
    ``__wrapped_source__`` attribute attached by :func:`attach_apply_source`;
    falls back to ``inspect.getsource``. Returns ``""`` on failure."""
    import inspect as _inspect
    fn = getattr(cls, "apply", None)
    if fn is None:
        return ""
    captured = getattr(fn, "__wrapped_source__", None)
    if isinstance(captured, str) and captured:
        return captured
    try:
        return _inspect.getsource(fn)
    except (OSError, TypeError):
        return ""
```

Then extend the `__all__` list (currently lines 171–179) by adding `"attach_apply_source"` and `"get_apply_source"` (alphabetical position: both go before `"build_failure_result"`, immediately after `"apply_workspace_edit_via_editor"`).

- [ ] **Step 4: Run to verify PASS** — `cd vendor/serena && uv run pytest test/unit/test_facade_support_apply_source.py -v` — expected: 3 passed.

- [ ] **Step 5: Commit** — `git add vendor/serena/src/serena/tools/facade_support.py vendor/serena/test/unit/test_facade_support_apply_source.py && git commit -m "feat(facade-support): attach_apply_source + get_apply_source" -m "Capture inspect.getsource(cls.apply) once at import time so introspection is independent of linecache (root cause of D-debt.md §2 flakes)." -m "Co-authored-by: AI Hive(R) <noreply@aihive.local>"`

---

## Task 3: Wire `attach_apply_source` into every Scalpel facade

**Files:** Modify `vendor/serena/src/serena/tools/scalpel_facades.py`.

**Strategy (TRIZ separation by criterion, DRY):** derive the registration set by *introspection* — every class in the module whose name matches `Scalpel*Tool`. Verified to resolve to exactly 26 classes (25 inspected by spikes + `ScalpelTransactionCommitTool`).

- [ ] **Step 1: Append the has-attribute test to Task 1's regression file**

```python
def test_every_inspected_facade_has_wrapped_source_attribute() -> None:
    """Every facade Tool inspected by the 6 spike sites must opt in."""
    for name in _FACADE_NAMES:
        cls = getattr(tools_module, name)
        captured = getattr(cls.apply, "__wrapped_source__", None)
        assert isinstance(captured, str) and captured, (
            f"{name}.apply must carry __wrapped_source__"
        )
        assert "workspace_boundary_guard(" in captured
```

- [ ] **Step 2: Run to verify FAIL** — `cd vendor/serena && uv run pytest test/spikes/test_apply_source_determinism.py::test_every_inspected_facade_has_wrapped_source_attribute -v` — expected: `AssertionError: ScalpelConvertModuleLayoutTool.apply must carry __wrapped_source__`.

- [ ] **Step 3: Apply the registration diff to scalpel_facades.py**

```diff
--- a/vendor/serena/src/serena/tools/scalpel_facades.py
+++ b/vendor/serena/src/serena/tools/scalpel_facades.py
@@ -16,6 +16,7 @@
 from .facade_support import (
+    attach_apply_source,
     workspace_boundary_guard,
 )
@@ -2270,3 +2271,18 @@
 # ---------------------------------------------------------------------------
 # End of facade definitions.
 # ---------------------------------------------------------------------------
+
+# Apply-source capture — fixes D-debt.md §2 flakes. Loop attaches
+# __wrapped_source__ to every Scalpel*Tool.apply so introspection is
+# independent of linecache. Name-based discovery (DRY): new facades
+# auto-register. Callers read via facade_support.get_apply_source(cls).
+for _name, _obj in list(globals().items()):
+    if isinstance(_obj, type) and _name.startswith("Scalpel") and _name.endswith("Tool"):
+        attach_apply_source(_obj)
+del _name, _obj
```

The loop matches all 26 `Scalpel*Tool` classes (verified by `grep -n "^class Scalpel" vendor/serena/src/serena/tools/scalpel_facades.py`). Verify post-edit with: `cd vendor/serena && uv run python -c "import serena.tools.scalpel_facades as m; print(len([n for n in dir(m) if n.startswith('Scalpel') and n.endswith('Tool')]))"` — expected: `26`.

- [ ] **Step 4: Run to verify PASS** — `cd vendor/serena && uv run pytest test/spikes/test_apply_source_determinism.py -v` — expected: 26 passed (25 stable-source params + 1 has-attribute).

- [ ] **Step 5: Commit** — `git add vendor/serena/src/serena/tools/scalpel_facades.py vendor/serena/test/spikes/test_apply_source_determinism.py && git commit -m "fix(scalpel-facades): attach __wrapped_source__ to every Scalpel*Tool" -m "Closes the 6 inspect.getsource flakes (D-debt.md §2) at the root via DRY name-based discovery." -m "Co-authored-by: AI Hive(R) <noreply@aihive.local>"`

---

## Task 4: Migrate the 6 spike sites to `get_apply_source`

**Files:** the 6 test files listed under "File Structure".

- [ ] **Step 1: Apply the same edit to each of the 6 files**

For each file, find the line `src = inspect.getsource(cls.apply)` (at `:374`, `:201`, `:247`, `:181`, `:261`, `:63` respectively) and replace with:

```python
src = get_apply_source(cls)
```

Add (alongside the existing `import inspect`):

```python
from serena.tools.facade_support import get_apply_source
```

Leave `import inspect` in place — other tests in each file may use it.

- [ ] **Step 2: Run all 6 spike files once** — `cd vendor/serena && uv run pytest test/spikes/test_stage_3_t1_rust_wave_a.py test/spikes/test_stage_3_t2_rust_wave_b.py test/spikes/test_stage_3_t3_rust_wave_c.py test/spikes/test_stage_3_t4_python_wave_a.py test/spikes/test_stage_3_t5_python_wave_b.py test/spikes/test_stage_2a_t9_registry_smoke.py -v` — expected: all green.

- [ ] **Step 3: Commit** — `cd vendor/serena && git add test/spikes/test_stage_3_t{1..5}_*.py test/spikes/test_stage_2a_t9_registry_smoke.py && git commit -m "test(spikes): switch 6 sites to deterministic get_apply_source" -m "Co-authored-by: AI Hive(R) <noreply@aihive.local>"`

---

## Task 5: Verify determinism — 10 consecutive runs per file

**Files:** verification-only.

**Per-class call multiplier (≥10-rerun audit transparency).** Each t1–t5 spike file runs **4 parametrized invocations** per pytest run; 2A registry smoke iterates over **5** classes per test. Across the 10-run loop each `inspect.getsource(cls.apply)` site is exercised ≥40 times (≥50 for 2A). The new regression test runs each of 25 classes 100× per pytest run × 10 reruns = ≥1000 introspection calls per class. ≥10-rerun budget vastly exceeded.

- [ ] **Step 1: Repeated-run loop for the 6 spike files**

```bash
cd vendor/serena
for f in \
  test/spikes/test_stage_3_t1_rust_wave_a.py \
  test/spikes/test_stage_3_t2_rust_wave_b.py \
  test/spikes/test_stage_3_t3_rust_wave_c.py \
  test/spikes/test_stage_3_t4_python_wave_a.py \
  test/spikes/test_stage_3_t5_python_wave_b.py \
  test/spikes/test_stage_2a_t9_registry_smoke.py
do
  echo "=== $f ==="
  for i in $(seq 1 10); do
    uv run pytest "$f" -v -p no:cacheprovider --tb=line \
      || { echo "FAIL on run $i for $f"; exit 1; }
  done
done
echo "All 60 runs (10 x 6 files) green."
```

Expected: terminal output ends with `All 60 runs (10 x 6 files) green.`

- [ ] **Step 2: Repeated-run loop for the regression test**

```bash
cd vendor/serena
for i in $(seq 1 10); do
  uv run pytest test/spikes/test_apply_source_determinism.py -v -p no:cacheprovider \
    || { echo "FAIL on run $i"; exit 1; }
done
echo "10 runs of test_apply_source_determinism.py all green."
```

Expected: ten consecutive `passed` lines + the trailing echo.

---

## Task 6: Roll up + close the gap-analysis entry

**Files:** parent submodule pointer + `docs/gap-analysis/WHAT-REMAINS.md`.

- [ ] **Step 1: Confirm clean tree** — `cd /Volumes/Unitek-B/Projects/o2-scalpel && git -C vendor/serena status` — expected: `nothing to commit, working tree clean`.

- [ ] **Step 2: Bump submodule pointer** — `cd /Volumes/Unitek-B/Projects/o2-scalpel && git add vendor/serena && git commit -m "chore(submodule): bump serena to inspect.getsource fix" -m "Closes the 6 flakes documented in docs/gap-analysis/D-debt.md §2." -m "Co-authored-by: AI Hive(R) <noreply@aihive.local>"`

- [ ] **Step 3: Mark WHAT-REMAINS.md §2 closed** — append to `docs/gap-analysis/WHAT-REMAINS.md` §2 sub-section "The 6 inspect.getsource flakes":

```markdown
**Status (2026-04-26): CLOSED** via `attach_apply_source` capture in `scalpel_facades.py` + helper in `facade_support.py`; 60 consecutive verification runs green (see `2026-04-26-fix-inspect-getsource-flakes.md` Task 5).
```

Then commit: `cd /Volumes/Unitek-B/Projects/o2-scalpel && git add docs/gap-analysis/WHAT-REMAINS.md && git commit -m "docs(gap-analysis): mark inspect.getsource flakes CLOSED" -m "Co-authored-by: AI Hive(R) <noreply@aihive.local>"`

---

## Verification matrix

All 7 files use the same loop-shape: `cd vendor/serena && for i in $(seq 1 10); do uv run pytest <FILE> -v -p no:cacheprovider; done`. Substitute `<FILE>` with each row below; expected outcome: 10/10 PASS per row, **70 consecutive runs green** total. Each spike row introspects 4–5 classes per run; per-class call counts are documented in Task 5 multiplier note.

| # | Test site | Classes/run | Pre-fix symptom |
|---|---|---|---|
| 1 | `test/spikes/test_stage_3_t1_rust_wave_a.py:374` | 4 | OSError / empty src |
| 2 | `test/spikes/test_stage_3_t2_rust_wave_b.py:201` | 4 | same |
| 3 | `test/spikes/test_stage_3_t3_rust_wave_c.py:247` | 4 | same |
| 4 | `test/spikes/test_stage_3_t4_python_wave_a.py:181` | 4 | same |
| 5 | `test/spikes/test_stage_3_t5_python_wave_b.py:261` | 4 | same |
| 6 | `test/spikes/test_stage_2a_t9_registry_smoke.py:63` | 5 | same |
| 7 | `test/spikes/test_apply_source_determinism.py` (new) | 25 × 100 | n/a — pins regression |

## Self-review

1. **Spec coverage:** (a) reproduce one flake = Task 1; (b) remediation (b) implemented in Tasks 2+3; (c) ≥10-rerun determinism per file = Task 5; (d) all 6 sites = Task 4 + matrix; (e) exact pytest invocations + complete diff = both present.
2. **Critic v1 blockers resolved.** R1 (wrong class names): Task 3 uses introspective `globals()` registration auto-discovering all 26 verified `Scalpel*Tool` classes — no hand-tuple, no drift. R2 (4-of-25 parametrize): `_FACADE_NAMES` is now the verified 25-class union.
3. **Critic v1 required edits 3–5 resolved.** (3) `__all__` line range corrected to 171–179. (4) Master Brief `:1002` divergence now documented in header callout (lines 995–1003 are docstring). (5) Per-class call multiplier note added in Task 5 (≥40 file-level + ≥250 regression-level invocations per class).
4. **Critic v1 suggested edits S1–S4 applied.** S1: introspective loop. S2: explicit no-op docstring on `attach_apply_source`. S3: Task 1 Step 2 expectation tightened. S4: sizing line in header.
5. **Placeholder scan & type consistency:** no "TBD"/"appropriate"/"similar to"/"edge cases"; `attach_apply_source(cls: type) -> None` and `get_apply_source(cls: type) -> str` referenced consistently; `__wrapped_source__` is `str | None`-by-getattr in every consumer.

*Author: AI Hive(R).*
