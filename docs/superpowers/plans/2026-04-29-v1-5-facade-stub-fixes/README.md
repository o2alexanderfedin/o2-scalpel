# v1.5 Facade-stub fixes — TREE plan

**Author:** AI Hive®
**Date:** 2026-04-29
**Worktree:** `/Volumes/Unitek-B/Projects/o2-scalpel.wt-facade-stubs` (branch `feature/v1.5-facade-stub-fixes`)
**Spec:** [`docs/superpowers/specs/2026-04-29-facade-stub-audit.md`](../../specs/2026-04-29-facade-stub-audit.md)
**Parent milestone:** v1.4 (Stream 6 polyglot — `v1.4-stream6-polyglot-complete`)
**Target tag:** `v1.5-facade-stub-fixes-complete`

## Goal

Lift 17 stub facades + 1 applier-level CRITICAL gap + 1 shared-dispatcher root cause from "decorative argument acceptance" to "argument-honoring real-disk mutation" — proven by REAL `Path.read_text()` post-apply assertions on every fix. The test-discipline retrofit (G7) is the second pillar: every fix gets a real-disk regression test, and the 21 zero-coverage facades each gain ≥1 such test.

The user-reported `scalpel_split_file` Rust path is the headline (CR-1). The blast-radius root cause is the shared `_dispatch_single_kind_facade` / `_python_dispatch_single_kind` pair which propagates "take `actions[0]` without policy" to 17 facade callers (HI-1). Fix order is shared-blast-radius first, safety violations next, user-reported third.

## Why now

- The user's adversarial spike on `scalpel_split_file` surfaced a stub that the existing mock-only tests could not catch.
- Four parallel audits confirmed the pattern is systemic, not isolated: 17 facades discard ≥1 declared semantic argument at function entry via `del`, 5 sites send hardcoded `(0,0)→(0,0)` LSP ranges, and 21 of 25 ergonomic facades have zero real-disk test coverage.
- Strategic end-goal memory: "Claude CLI uses LSPs at full extent for search/navigate/edit on code AND markdown." Decorative facades that silently faked work undermine that promise.

## Scope

### In scope (this milestone)

- **G1** (1 leaf): shared dispatcher disambiguation — fixes HI-1 root cause for 17 callers.
- **G2** (1 leaf): `dry_run` safety violations — fixes HI-12 (`expand_macro` + `verify_after_refactor`).
- **G3a** (1 leaf): `_split_rust` per-group iteration — closes CR-1 (the user's report).
- **G3b** (1 leaf): `_apply_workspace_edit_to_disk` resource-op support — closes CR-2.
- **G4-{1..10}** (10 leaves): the 10 HIGH parameter graveyards (HI-2 through HI-11). Each leaf is one facade; each leaf rewires one previously-discarded argument into the disambiguation policy from G1 (or, where no policy hook exists, returns an explicit `INPUT_NOT_HONORED` envelope and updates the docstring to match).
- **G5** (1 leaf): hardcoded `(0,0)` cleanup — fixes the 3 remaining sites after G3a closes the `_split_rust` site (HI-13: `imports_organize`, `fix_lints`, `inline` fallback). The Java fallback site (`_java_generate_dispatch`) is folded into ME-6 / G6.
- **G6** (1 leaf): MEDIUM tier (ME-1, ME-2, ME-3, ME-4, ME-5, ME-6, ME-7). Sub-checkboxes per finding — they share a similar structural pattern (filter-after-dispatch) so one leaf with 7 sub-tasks is correct sizing.
- **G7-A**, **G7-B**, **G7-C** (3 leaves): test-discipline retrofit. 21 zero-coverage facades + 7 mock-test rewrites = 28 facades to cover. Split into three waves of ≤10 facades each so each leaf stays tractable as a single PR-sized commit.
- **G8** (1 leaf): LOW + docs (LO-1 honest envelope on `also_in_strings`, LO-2 `rust_strategy.py` docstring drift, LO-3 deferral note in `checkpoints.py`).

### Out of scope

- Refactoring `scalpel_facades.py` structure. The file is 3425 LoC and known-too-monolithic, but the spec explicitly says "fix in place." Restructuring is a separate v1.6 milestone.
- Markdown applier consolidation with the main applier. Spec § Out of scope says "could be done in this milestone or deferred; flagged as a v1.5 stretch goal." We defer — `_apply_markdown_workspace_edit` already supports CreateFile, and G3b lifts the main applier to parity. Consolidation can happen post-merge under a follow-up.
- Deep-tree directory checkpoint restore (LO-3). Spec says v1.6 feature; we update the docstring acknowledging the limitation but do not implement.
- Per-field / per-method selection in `ScalpelGenerateConstructorTool` and `ScalpelOverrideMethodsTool` (ME-4). The spec acknowledges these as "Phase 2.5 deferral"; we surface honestly via response envelope but do not wire jdtls's interactive picker.
- Solver integration / Z3 / CVC5 — unrelated to this milestone.

## Severity-to-leaf mapping

| Spec finding | Tier | Leaf |
|---|---|---|
| CR-1 `_split_rust` per-group | CRITICAL | L-G3a |
| CR-2 applier resource ops | CRITICAL | L-G3b |
| HI-1 shared dispatcher | HIGH (root cause) | **L-G1** |
| HI-2 `change_return_type` | HIGH | L-G4-1 |
| HI-3 `extract_lifetime` | HIGH | L-G4-2 |
| HI-4 `generate_trait_impl_scaffold` | HIGH | L-G4-3 |
| HI-5 `change_visibility` | HIGH | L-G4-4 |
| HI-6 `generate_from_undefined` | HIGH | L-G4-5 |
| HI-7 `extract` (4 args) | HIGH | L-G4-6 |
| HI-8 `inline` (2 args + (0,0)) | HIGH | L-G4-7 |
| HI-9 `fix_lints` (rules) | HIGH | L-G4-8 |
| HI-10 `imports_organize` (3 toggles) | HIGH | L-G4-9 |
| HI-11 `ignore_diagnostic` (rule) | HIGH | L-G4-10 |
| HI-12 `dry_run` safety | HIGH (safety) | L-G2 |
| HI-13 hardcoded ranges | HIGH | L-G5 (3 sites; 1 site closes via G3a; 1 in G6) |
| ME-1 .. ME-7 | MEDIUM | L-G6 (sub-checkboxes) |
| 21 zero-coverage facades | TEST DISCIPLINE | L-G7-A / L-G7-B / L-G7-C |
| LO-1 .. LO-3 | LOW | L-G8 |

## Leaf table

| # | Leaf | Subject | LoC est. | Risk | Depends-on | Status |
|---|---|---|---|---|---|---|
| 01 | [L-G1](./L-G1-shared-dispatcher-disambiguation.md) | Shared dispatcher candidate-disambiguation policy (`isPreferred` → title-match → `MULTIPLE_CANDIDATES`) | ~150 | low — pure policy + 17 downstream consumers untouched in shape | none | PLANNED |
| 02 | [L-G2](./L-G2-dry-run-safety-honor.md) | `expand_macro` + `verify_after_refactor` honor `dry_run` | ~80 | low — short-circuit before LSP dispatch | none | PLANNED |
| 03 | [L-G3a](./L-G3a-split-rust-per-group.md) | `_split_rust` per-group iteration mirroring `_split_python` (CLOSES USER REPORT) | ~140 | medium — multiple LSP calls per facade invocation | L-G1 | PLANNED |
| 04 | [L-G3b](./L-G3b-applier-resource-ops.md) | `_apply_workspace_edit_to_disk` learns CreateFile / RenameFile / DeleteFile | ~180 | medium — file-system mutations + conflict detection | none | PLANNED |
| 05 | [L-G4-1](./L-G4-1-change-return-type.md) | `change_return_type` honors `new_return_type` (post-process or `INPUT_NOT_HONORED`) | ~100 | low — title-filter via G1 | L-G1 | PLANNED |
| 06 | [L-G4-2](./L-G4-2-extract-lifetime.md) | `extract_lifetime` honors `lifetime_name` (post-process or `INPUT_NOT_HONORED`) | ~100 | low — title-filter via G1 | L-G1 | PLANNED |
| 07 | [L-G4-3](./L-G4-3-generate-trait-impl-scaffold.md) | `generate_trait_impl_scaffold` honors `trait_name` (REQUIRED arg) | ~110 | low — title-filter `Implement <trait_name>` | L-G1 | PLANNED |
| 08 | [L-G4-4](./L-G4-4-change-visibility.md) | `change_visibility` honors `target_visibility` via title prefix `Change visibility to pub(crate)` | ~110 | low — RA stable title format | L-G1 | PLANNED |
| 09 | [L-G4-5](./L-G4-5-generate-from-undefined.md) | `generate_from_undefined` honors `target_kind` via per-kind dispatch | ~120 | low — kind-table extension | L-G1 | PLANNED |
| 10 | [L-G4-6](./L-G4-6-extract-knobs.md) | `scalpel_extract` honors `new_name` / `visibility` / `similar` / `global_scope` | ~180 | medium — 4 args, mixed strategy (rope wiring + Rust post-processing) | L-G1 | PLANNED |
| 11 | [L-G4-7](./L-G4-7-inline-fixes.md) | `scalpel_inline` honors `name_path` + `remove_definition`; (0,0) fallback removed | ~140 | medium — both an HI-8 fix and an HI-13 site | L-G1 | PLANNED |
| 12 | [L-G4-8](./L-G4-8-fix-lints-rules.md) | `scalpel_fix_lints` honors `rules` (per-rule dispatch + merge) | ~150 | medium — multiple dispatches per call | L-G1 | PLANNED |
| 13 | [L-G4-9](./L-G4-9-imports-organize-toggles.md) | `imports_organize` honors `add_missing` / `remove_unused` / `reorder` (per-flag kind) | ~160 | medium — 3 sub-kinds + merge | L-G1 | PLANNED |
| 14 | [L-G4-10](./L-G4-10-ignore-diagnostic-rule.md) | `ignore_diagnostic` honors `rule` via diagnostic data attachment | ~130 | low | L-G1 | PLANNED |
| 15 | [L-G5](./L-G5-hardcoded-ranges-cleanup.md) | The 2 remaining `(0,0)` sites: `imports_organize` (file range), `fix_lints` (file range). `inline` covered by G4-7; `_split_rust` covered by G3a; `_java_generate_dispatch` by G6. | ~80 | low — `compute_file_range` already exists (`solidlsp.util.file_range`) | L-G4-8, L-G4-9 | PLANNED |
| 16 | [L-G6](./L-G6-medium-tier.md) | ME-1..ME-7 (7 sub-checkboxes — `tidy_structure` scope, `auto_import` symbol filter, `introduce_parameter` rename, generate_constructor / override_methods (deferred), `convert_module_layout` title-disambig, `_java_generate_dispatch` real range, `extract` actions[0] [duplicate of G1 → drop]) | ~250 | low/medium per item | L-G1 | PLANNED |
| 17 | [L-G7-A](./L-G7-A-real-disk-tests-wave-a.md) | Real-disk test wave A — 10 Rust facades (`change_visibility`, `change_return_type`, `convert_module_layout`, `tidy_structure`, `change_type_shape`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `generate_trait_impl_scaffold`, `generate_member`) | ~600 test | medium — requires fixture targets in calcrs companion crates | L-G1 .. L-G6 | PLANNED |
| 18 | [L-G7-B](./L-G7-B-real-disk-tests-wave-b.md) | Real-disk test wave B — 10 Python facades (`inline`, `imports_organize`, `convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `auto_import_specialized`, `fix_lints`, `ignore_diagnostic`) | ~600 test | medium — pylsp + ruff fixtures | L-G1 .. L-G6 | PLANNED |
| 19 | [L-G7-C](./L-G7-C-real-disk-tests-wave-c.md) | Real-disk test wave C — `transaction_commit`, `expand_macro`, `verify_after_refactor`, plus rewrites of the 7 mock-only spike tests in `test_stage_2a_t*` / `test_stage_3_t*` to `Path.read_text()` discipline | ~500 test | low — patterns established by waves A/B | L-G7-A, L-G7-B | PLANNED |
| 20 | [L-G8](./L-G8-low-and-docs.md) | LO-1 honest `also_in_strings` envelope; LO-2 `rust_strategy.py` docstring drift; LO-3 `checkpoints.py` deep-tree deferral note | ~50 | trivial | none | PLANNED |

**Total leaves: 20.** Test-discipline retrofit (G7-A/B/C) is the largest by LoC; fix leaves average ~120 LoC each.

## Execution order

The fix order obeys two rules:
1. **G1 (root cause) before G4-* and G6-ME5** — the disambiguation policy is the substrate every parameter-graveyard fix builds on.
2. **G3b (applier resource ops) parallelizable to fix leaves** — independent of G1, can land before, alongside, or after.
3. **G7-A/B/C (test retrofit) gated on the fix leaves** — fix the bugs, then write the tests that prove the fixes (and would have caught them).

```text
Wave 1  (independent, parallel-safe):
        L-G1 (shared dispatcher)        ← unblocks 17 facades
        L-G2 (dry_run safety)           ← independent
        L-G3b (applier resource ops)    ← independent
        L-G8 (LOW + docs)               ← independent

Wave 2  (gated on G1):
        L-G3a (split_rust per-group)    ← USER-VISIBLE FIX
        L-G4-1..L-G4-10 (10 leaves)     ← can fan out in parallel; no shared files
        L-G6 (MEDIUM tier)              ← shares dispatcher with G4 leaves

Wave 3  (gated on Wave 2):
        L-G5 (cleanup remaining (0,0))  ← only after G4-7/8/9 land

Wave 4  (gated on Waves 1-3):
        L-G7-A (Rust real-disk tests)
        L-G7-B (Python real-disk tests)
        L-G7-C (transaction + spike rewrites)
```

**Parallelism note:** within Wave 2, the 10 G4 leaves modify disjoint sections of `scalpel_facades.py` (each leaf owns one Tool subclass) and disjoint test files. They can be implemented in parallel by separate executor agents IF coordinated by the orchestrator; sequentially by one agent is also fine. **G1's commit MUST land alone** to give blame clarity for the 17-facade blast radius — do not bundle G1 with any other leaf.

## Intra-tree dependency diagram

```mermaid
flowchart TD
    G1[L-G1 shared dispatcher policy]
    G2[L-G2 dry_run safety]
    G3a[L-G3a split_rust per-group]
    G3b[L-G3b applier resource ops]
    G8[L-G8 LOW + docs]

    G41[L-G4-1 change_return_type]
    G42[L-G4-2 extract_lifetime]
    G43[L-G4-3 generate_trait_impl_scaffold]
    G44[L-G4-4 change_visibility]
    G45[L-G4-5 generate_from_undefined]
    G46[L-G4-6 extract knobs]
    G47[L-G4-7 inline fixes]
    G48[L-G4-8 fix_lints rules]
    G49[L-G4-9 imports_organize toggles]
    G410[L-G4-10 ignore_diagnostic rule]

    G5[L-G5 (0,0) cleanup]
    G6[L-G6 MEDIUM tier]

    G7A[L-G7-A Rust real-disk tests]
    G7B[L-G7-B Python real-disk tests]
    G7C[L-G7-C transaction + spike rewrites]

    G1 --> G3a
    G1 --> G41
    G1 --> G42
    G1 --> G43
    G1 --> G44
    G1 --> G45
    G1 --> G46
    G1 --> G47
    G1 --> G48
    G1 --> G49
    G1 --> G410
    G1 --> G6

    G47 --> G5
    G48 --> G5
    G49 --> G5

    G1 --> G7A
    G2 --> G7C
    G3a --> G7C
    G3b --> G7A
    G3b --> G7B
    G41 --> G7A
    G42 --> G7A
    G43 --> G7A
    G44 --> G7A
    G45 --> G7B
    G46 --> G7A
    G46 --> G7B
    G47 --> G7B
    G48 --> G7B
    G49 --> G7B
    G410 --> G7B
    G5 --> G7A
    G5 --> G7B
    G6 --> G7A
    G6 --> G7B
```

## Verification gate (definition of done for the milestone)

1. **Submodule pyright:** 0 errors / 0 warnings / 0 hints.
2. **Submodule full test suite:** ≥614 PASS / ≤3 SKIP, no new FAILs. Expected delta from G7-A/B/C: ~+50 new real-disk tests.
3. **Parameter-flow proof:** every G4 leaf's failing test asserts via `Path.read_text()` post-apply that the previously-discarded argument flowed through to the on-disk result. Mock-only `del foo` regressions are no longer possible because no leaf removes the post-apply read assertion.
4. **User-report close-out:** `scalpel_split_file` with `groups={"helpers": ["add"], "ops": ["sub"]}` produces TWO `refactor.extract.module` LSP requests (one per group) bracketed by the actual symbol ranges of `add` and `sub` (not `(0,0)→(0,0)`); resulting on-disk module files contain the moved symbols. This is asserted by L-G3a's test suite, NOT just by code review.
5. **Atomic commits:** one commit per leaf, `Authored-by: AI Hive®` footer. **L-G1 lands alone** for blame clarity.
6. **G1 blast-radius regression check:** after L-G1 lands and before L-G4-* lands, the existing test suite must still pass — the disambiguation policy must default to RA's status-quo behavior when no caller payload is supplied (i.e., `actions[0]` is still chosen when no title-match or `isPreferred` flag separates candidates). This protects the 17 callers that haven't yet had their payload-flow leaves applied.
7. **CR-2 close-out:** L-G3b's tests prove `CreateFile` writes an empty file at the target URI, `RenameFile` moves the file with conflict detection (`ignoreIfExists`), `DeleteFile` removes the file (with `ignoreIfNotExists` semantics).
8. **Tag:** `v1.5-facade-stub-fixes-complete` on parent + submodule bump.

## Risk + rollback (milestone-level)

- **Risk: L-G1 disambiguation policy regresses an existing facade.** Mitigation: G1's policy defaults to `actions[0]` when no caller-payload disambiguator exists; existing tests continue to pass. Rollback: revert L-G1 commit; the 17 G4 leaves cannot land without it.
- **Risk: L-G3b resource-op support breaks an existing edit application.** Mitigation: feature-gated by the `kind` field — existing edits with no `kind` field continue through the legacy path. The 5 markdown facades already use `_apply_markdown_workspace_edit` (a separate function); changes to the main applier do not affect them.
- **Risk: G7-A/B/C real-disk tests are flaky against real LSPs.** Mitigation: each test is gated by `_require_binary("rust-analyzer" / "pylsp" / "ruff")` and skip-cleanly when the host is partial. Existing v0.1.0 conftest discipline is reused unchanged.
- **Risk: A G4 leaf cannot wire its argument honestly because the underlying LSP does not expose the seam.** Mitigation: the leaf's plan explicitly enumerates this as a fallback path — return `INPUT_NOT_HONORED` envelope and update the docstring to match. The existing CAPABILITY_NOT_AVAILABLE precedent + envelope shape is reused; no schema change.

## Cross-references

- Spec: [`../../specs/2026-04-29-facade-stub-audit.md`](../../specs/2026-04-29-facade-stub-audit.md)
- Source: `vendor/serena/src/serena/tools/scalpel_facades.py` (3425 LoC, fix in place)
- Schemas: `vendor/serena/src/serena/tools/scalpel_schemas.py` (`ErrorCode` enum at line 22)
- Coordinator: `vendor/serena/src/serena/refactoring/multi_server.py` (`MergedCodeAction` at line 69, `find_symbol_range` at line 1528, `get_action_edit` at line 1592)
- Conftest: `vendor/serena/test/integration/conftest.py` (`assert_workspace_edit_round_trip` helper at line 309)
- Project memory anchors: `project_v0_3_0_facade_application.md`, `project_v0_2_0_review_fixes_batch.md` (mock-strip-the-skip pattern)
- Existing real-disk applier tests (precedent for L-G7-*): `vendor/serena/test/spikes/test_v0_3_0_workspace_edit_applier.py`

---

**Author:** AI Hive®
