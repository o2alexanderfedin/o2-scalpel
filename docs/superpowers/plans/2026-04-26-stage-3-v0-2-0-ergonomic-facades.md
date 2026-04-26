# Stage 3 (v0.2.0) — Ergonomic facades + long-tail E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the 12 Stage 3 Rust ergonomic facades + 8 Stage 3 Python facades + 8 long-tail E2E scenarios + server-extension whitelist tests + README/install docs that round out the v0.2.0 release immediately after the v0.2.0 critical-path (`v0.2.0-critical-path-complete`).

**Architecture:** Each facade extends `serena.tools.scalpel_facades` with a new `Tool` subclass that follows the Stage 2A 5-facade pattern: `apply()` accepts `file=` (or `files=`), an optional `language=`, an `allow_out_of_workspace=` boolean, and `dry_run=`/`preview_token=` for the dry-run/commit grammar. Each facade dispatches to either the existing `MultiServerCoordinator` primitives (Rust) or the `_RopeBridge` (Python). New E2E scenarios extend the Stage 2B harness; they reuse `_McpDriver` + the per-test calcrs/calcpy clones and add facade-specific calls.

**Tech Stack:** pytest, pydantic v2, asyncio, rope, pylsp-rope, basedpyright, ruff, rust-analyzer.

**Source of truth:** `docs/design/mvp/2026-04-24-mvp-scope-report.md` §14.3 (Stage 3 LoC roll-up + file list) + §4.2 (Rust assist-family allocation) + §4.4 (Python LSP capabilities).

---

## Pre-flight

- [ ] **Verify entry baseline**

```bash
cd /Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena
git checkout main && git pull --ff-only
git log --oneline -1   # expect tag v0.2.0-critical-path-complete
PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/spikes/ -q --tb=line
```

Expected: spike-suite 614/3-skip, tag `v0.2.0-critical-path-complete` reachable.

- [ ] **Bootstrap branches**

Submodule: `git checkout -b feature/stage-3-ergonomic-facades`
Parent: `git checkout -b feature/stage-3-ergonomic-facades develop`

---

## Tasks

### Task 0: PROGRESS ledger

**Files:**
- Create: `docs/superpowers/plans/stage-3-results/PROGRESS.md` (parent)

- [ ] **Step 1: Seed PROGRESS.md** with task table mirroring this plan (T0-T10 rows + `Outcome` + `Follow-ups` columns).

### Task 1: Rust facades wave A (4 facades)

**Files:**
- Modify: `vendor/serena/src/serena/tools/scalpel_facades.py` (+~550 LoC)
- Test: `vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py`

Wave A facades:
- `scalpel_convert_module_layout` — converts `mod foo;` ↔ `mod foo { ... }` (cross-references §4.7 #5).
- `scalpel_change_visibility` — pub/pub(crate)/pub(super) toggles via rust-analyzer's `change_visibility` assist.
- `scalpel_tidy_structure` — composite of `reorder_impl_items`, `sort_items`, `reorder_fields` (§4.2 row F).
- `scalpel_change_type_shape` — `convert_*_to_*` family (§4.2 row H).

- [ ] **Step 1: Test scaffolds** for the 4 facades using the Stage 2A pattern (`_make_tool` + `MagicMock` coord + `merge_code_actions` fake returning the relevant action kind). One test per facade asserting `applied=True` + `checkpoint_id` exists.

- [ ] **Step 2: Run failing tests** — expect ImportError on the 4 facade Tool classes.

- [ ] **Step 3: Implement** the 4 Tool subclasses following the Stage 2A pattern. Each routes through `coordinator_for_facade` + `merge_code_actions` with a fixed `only=[<rust-analyzer kind>]` filter.

- [ ] **Step 4: Verify** all 4 tests green; no regressions in the spike-suite.

- [ ] **Step 5: Commit** `feat(stage-3-T1): rust wave A — convert_module_layout, change_visibility, tidy_structure, change_type_shape`.

### Task 2: Rust facades wave B (4 facades)

Wave B facades:
- `scalpel_change_return_type` — function return-type rewriter (§4.2 row H tail).
- `scalpel_complete_match_arms` — `add_missing_match_arms` exhaustiveness assist (§4.2 row I).
- `scalpel_extract_lifetime` — lifetime-introduction assist.
- `scalpel_expand_glob_imports` — `expand_glob_imports` (paired with the MVP `imports_organize` flow per §4.2 row D).

Same TDD shape as Task 1. Commit: `feat(stage-3-T2): rust wave B — change_return_type, complete_match_arms, extract_lifetime, expand_glob_imports`.

### Task 3: Rust facades wave C (4 facades)

Wave C facades:
- `scalpel_generate_trait_impl_scaffold` — generate stub `impl T for U {}` (§4.2 row G).
- `scalpel_generate_member` — generate getter/setter/method stubs (§4.2 row G tail).
- `scalpel_expand_macro` — first-class facade over rust-analyzer's `expandMacro` (§4.7 #5; primitive at MVP).
- `scalpel_verify_after_refactor` — composite of `runnables` + `relatedTests` + `runFlycheck` per scope-report §4.7 #7. Returns a structured verification report (`{tests_run, passed, failed, flycheck_diagnostics}`); calls Cargo via the runnables JSON spec.

Commit: `feat(stage-3-T3): rust wave C — generate_*, expand_macro, verify_after_refactor`.

### Task 4: Python facades wave A (4 facades)

**Files:**
- Modify: `vendor/serena/src/serena/tools/scalpel_facades.py` (+~320 LoC)
- Test: `vendor/serena/test/spikes/test_stage_3_t4_python_wave_a.py`

Wave A facades:
- `scalpel_convert_to_method_object` — pylsp-rope `method_to_method_object` (§4.4.1 row 5; primitive at MVP).
- `scalpel_local_to_field` — pylsp-rope `local_to_field` (§4.4.1 row 4).
- `scalpel_use_function` — pylsp-rope `use_function` (§4.4.1 row 6).
- `scalpel_introduce_parameter` — pylsp-rope `introduce_parameter` (§4.4.1 row 7).

Each routes through `merge_code_actions` with the appropriate pylsp-rope command. Tests follow Stage 2A pattern.

Commit: `feat(stage-3-T4): python wave A — convert_to_method_object, local_to_field, use_function, introduce_parameter`.

### Task 5: Python facades wave B (4 facades)

Wave B facades:
- `scalpel_generate_from_undefined` — pylsp-rope `quickfix.generate` (§4.4.1 row 8).
- `scalpel_auto_import_specialized` — `auto_import` two-step flow (paired with the MVP `imports_organize` glob path); resolves the AmbiguousImport candidate set via the `addImport` resolve.
- `scalpel_fix_lints` — ruff `source.fixAll.ruff` first-class facade (§4.4.3 row 1; primitive at MVP). **Includes the E13-py organize_imports dedup gap** discovered during v0.2.0 critical-path: the test in `test_e2e_e10_rename_multi_file.py::test_e13_py_organize_imports_single_action` expects duplicate `import sys` removal that ruff `source.organizeImports` does NOT perform; this facade must select `source.fixAll.ruff` (or chain it after `organizeImports`) so duplicates collapse.
- `scalpel_ignore_diagnostic` — basedpyright `quickfix` (`# pyright: ignore[<rule>]` insertion, §4.4.2 row 3) + ruff `noqa` insertion. `tool="pyright"|"ruff"` parameter.

Commit: `feat(stage-3-T5): python wave B — generate_from_undefined, auto_import, fix_lints, ignore_diagnostic`.

### Task 6: Stage 3 Rust E2E (E13–E16)

**Files:**
- Create: `vendor/serena/test/e2e/test_e2e_e13_rust_*.py` (one per scenario)
- Modify: `vendor/serena/test/e2e/conftest.py` — extend `_McpDriver` with the 12 Stage 3 Rust facade methods.

E13–E16 from scope-report §15.1 (Stage 3 nightly):
- E13: `verify_after_refactor` round-trip (cargo test + flycheck after a split).
- E14: `change_visibility` cross-module ripple (verify no breakage in private callers).
- E15: `expand_macro` round-trip (`println!` expanded equivalence).
- E16: `complete_match_arms` exhaustiveness on a sealed enum.

Tests follow Stage 2B harness pattern (per-test calcrs clone, MCP driver, dry-run + commit). Each test marked `@pytest.mark.e2e`.

Commit: `test(stage-3-T6): rust E2E E13-E16`.

### Task 7: Stage 3 Python E2E (E4-py / E5-py / E8-py / E11-py)

**Files:**
- Create: `vendor/serena/test/e2e/test_e2e_*_py_*.py`

Scenarios (scope-report §15.1):
- E4-py: cross-package extract.
- E5-py: multi-package E2E (`pytest -q` byte-identical post-refactor).
- E8-py: crash-recovery on a partial pylsp-rope failure.
- E11-py: `__all__` preservation under the v0.2.0-E rename path (extends the Stage 2B test).

Commit: `test(stage-3-T7): python E2E E4/E5/E8/E11-py`.

### Task 8: Server-extension whitelist tests

**Files:**
- Create: `vendor/serena/test/spikes/test_stage_3_t8_server_extension_whitelist.py` (~200 LoC)

Asserts every rust-analyzer custom extension method (§4.3 — 36 methods) is either:
- First-class facaded (the 8 enumerated facades),
- Surfaced via `scalpel_apply_capability` (the 27 typed pass-through),
- Or explicit-blocked (the 1: `experimental/onEnter`).

The whitelist is a frozen set; the test fails if a new rust-analyzer release adds an unfamiliar method.

Commit: `test(stage-3-T8): server-extension whitelist`.

### Task 9: README + install docs

**Files:**
- Modify: `README.md` (project root), `vendor/serena/README.md`
- Create: `docs/install.md`

Document:
- Marketplace install path (boostvolt / `o2alexanderfedin/claude-code-plugins`) is **v1.1**, not v0.2.0.
- v0.2.0 install: `uvx --from <local-path>`.
- All 21 ergonomic facades (5 MVP + 12 Stage 3 Rust + 8 Stage 3 Python + 1 transaction_commit).
- Capability catalog drift gate (`pytest --update-catalog-baseline`).

Commit: `docs(stage-3-T9): README + install docs for v0.2.0`.

### Task 10: ff-merge + tag

- [ ] **Step 1: Submodule** `git checkout main && git merge --ff-only feature/stage-3-ergonomic-facades && git tag -a v0.2.0 -m "v0.2.0: Stage 3 ergonomic facades + long-tail E2E"`.
- [ ] **Step 2: Parent** bump submodule pointer; merge feature → develop → main; tag `v0.2.0` on parent main.
- [ ] **Step 3: Verify** spike-suite 614+ green; e2e suite 26 passed (was 18) + 2 skipped (host cargo).

---

## Out of scope for Stage 3 (deferred)

- v0.2.0 carry-over backlog items #11-15 from MVP cut (multi-crate E2E, crate-wide glob, cold-start, crash recovery, parent_module_style flag) — those are v0.2.0 *nightly* gates, not Stage 3 facades.
- Stage 1H continuation (28 tests + 17 RA crates + 3 calcpy fixtures) — runs as a parallel workstream (separate plan).

## Self-review

- Coverage: each scope-report §14.3 file (28-32) has a dedicated task above.
- Facade count: 12 Rust + 8 Python = 20 (matches §14.3 promise of "every remaining ergonomic facade in §4").
- E2E: 4 Rust (E13-E16) + 4 Python (E4/E5/E8/E11-py) = 8 scenarios (matches §14.3 row 30).
- LoC budget: ~1,650 logic + ~640 logic + ~900 tests + ~200 tests + ~150 docs = ~3,540 logic + ~1,100 tests = ~4,640 (matches §14.3 roll-up).

## Execution handoff

Plan complete. Two execution options when next session resumes:

**1. Subagent-Driven (recommended)** — dispatch `gsd-executor` (or superpowers:subagent-driven-development) with this plan; per-task implementer + reviewer, ~10 turns to complete Stage 3.

**2. Inline Execution** — execute T1-T10 in-session with checkpoints at each task boundary.

For both, follow the v0.2.0-critical-path pattern: PROGRESS ledger updated per task, atomic commits, ff-merge + tag at T10.
