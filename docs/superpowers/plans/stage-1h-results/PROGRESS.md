# Stage 1H — Full Fixtures + Per-Assist-Family Integration Tests — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1h-fixtures-integration-tests (both parent + submodule)
Author: AI Hive(R)
Built on: stage-1g-primitive-tools-complete
Predecessor green: 303 + Stage 1E + 1F + 1G suite (per stage-1g-results/PROGRESS.md)

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0  | Bootstrap branches + ledger + fixture-tree skeleton dirs                | 9623c61c | OK — branches open, skeleton dirs + sentinels committed | — |
| T1  | calcrs Cargo workspace shell + 5 baseline crates                        | _pending_ | _pending_ | — |
| T2  | 13 additional RA companion crates                                       | _pending_ | _pending_ | — |
| T3  | calcpy package shell + sub-fixture 1 (calcpy_namespace, split_file)     | _pending_ | _pending_ | — |
| T4  | calcpy sub-fixture 2 (calcpy_circular, extract_function)                | _pending_ | _pending_ | — |
| T5  | calcpy sub-fixture 3 (calcpy_dataclasses, inline)                       | _pending_ | _pending_ | — |
| T6  | calcpy sub-fixture 4 (calcpy_notebooks, organize_imports)               | _pending_ | _pending_ | — |
| T7  | integration test harness (test/integration/conftest.py)                 | _pending_ | _pending_ | — |
| T8  | 8 Rust assist-family integration tests (extract/inline/move/rewrite)    | _pending_ | _pending_ | — |
| T9  | 8 more Rust integration tests (generators/convert/pattern/visibility/…) | _pending_ | _pending_ | — |
| T10 | 8 Python integration tests (rope-bridge facades + pylsp + basedpyright) | _pending_ | _pending_ | — |
| T11 | 7 cross-language tests (multi-server merge invariants from §11.7)       | _pending_ | _pending_ | — |
| T12 | registry update + ledger close + ff-merge + tag                         | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

- 2026-04-25 — Plan deviation noted: capability catalog module is `src/serena/refactoring/capabilities.py` (not `capability_catalog.py` as the plan references). Surface check at T0 step 5 adapted accordingly.
- 2026-04-25 — Stage 1H execution PAUSED after T0 bootstrap. Honest scope assessment by orchestrator: 9,460 LoC of fixtures + 31 integration tests requiring real-LSP boots cannot fit the imposed 8-hour budget without producing half-broken submodule state. T0 committed as a safe bootstrap checkpoint; T1..T12 deferred pending budget revision or scope reduction (e.g., minimum-viable subset: T1+T3+T7 + 3 representative integration tests proving the harness boots all four LSPs).

## Stage 1H entry baseline

- Submodule `main` head at Stage 1H start: `71ceedb3` (Stage 1J complete)
- Parent branch: feature/stage-1h-fixtures-integration-tests off develop @ `653a631`
- Stage 1G tag: `stage-1g-primitive-tools-complete`
- Predecessor suite green: per stage-1g-results/PROGRESS.md

## Fixture LoC running tally (updated per task)

| Task | Cumulative fixture LoC | Cumulative test LoC | Total Stage 1H LoC |
|---|---|---|---|
| T0  | 0    | 1   (pkg `__init__.py`) | 1     |

## Spike outcome quick-reference (carryover for context)

- P3 → ALL-PASS — Rope 1.14.0 + Python 3.10–3.13+ supported. Library bridge integration tested in T23 / T24.
- P4 → A — basedpyright 1.39.3 PULL-mode only; T21 exercises pull-mode auto-import.
- P5a → C — pylsp-mypy DROPPED. T20 / T25 verify the 3-server merge does not include mypy.
- Q1 cascade — synthetic per-step `didSave` injection no longer needed (was a pylsp-mypy mitigation).
- Q3 — `basedpyright==1.39.3` exact pin verified by T21 startup assertion.
- S5 → see S5 note — `expandMacro` proc-macro pathway tested via `ra_proc_macros` + T15.
