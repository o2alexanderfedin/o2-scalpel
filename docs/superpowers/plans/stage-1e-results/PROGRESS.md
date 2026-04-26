# Stage 1E — Python Strategies + LSP Adapters — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1e-python-strategies (submodule); feature/stage-1e-python-strategies (parent)
Author: AI Hive(R)
Built on: stage-1d-multi-server-merge-complete

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0 | Bootstrap branches + ledger + dep pins                             | _pending_ | _pending_ | — |
| T1 | language_strategy.py Protocol + Rust/Python mixins                 | _pending_ | _pending_ | — |
| T2 | rust_strategy.py skeleton (assist-family + ext allow-list)         | _pending_ | _pending_ | — |
| T3 | pylsp_server.py adapter (spawn/init/facade conformance)            | _pending_ | _pending_ | — |
| T4 | pylsp_server.py real workspace/applyEdit drain (1D T11 deferred)   | _pending_ | _pending_ | — |
| T5 | basedpyright_server.py adapter (pull-mode diagnostic, P4)          | _pending_ | _pending_ | — |
| T6 | ruff_server.py adapter                                             | _pending_ | _pending_ | — |
| T7 | python_strategy.py — MultiServerCoordinator wiring (no mypy)       | _pending_ | _pending_ | — |
| T8 | python_strategy.py — 14-step interpreter + Rope library bridge     | _pending_ | _pending_ | — |
| T9 | __init__.py registry + smoke + ledger close + ff-merge + tag       | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

- 2026-04-25 — Adapter LoC budget per file revised 50→100-150 LoC. Rationale: precedent `vendor/serena/src/solidlsp/language_servers/jedi_server.py` confirms `InitializeParams` alone consumes ~60-80 LoC per adapter. Total Stage 1E LoC still under 1,425 budget.
- 2026-04-25 — Rope library bridge ships 2 of 5 ops at MVP (`move_module`, `change_signature`). The remaining 3 (IntroduceFactory, EncapsulateField, Restructure) routed to Stage 1F. Per drafter §J.3.
- 2026-04-25 — Interpreter discovery chain ships at 14 steps (NOT 16). PEP 723 + direnv steps deferred to v0.2.0. Matches scope-report §7 as written.
- 2026-04-25 — T0 step 1 adapted: parent transitions directly from `develop` to a new `feature/stage-1e-python-strategies` execution branch (the planning branch `feature/plan-stage-1e` was already merged). Submodule branch `feature/stage-1e-python-strategies` opened fresh off `origin/main`.

## Stage 1D entry baseline

- Submodule `main` head at Stage 1E start: `3ae27952d9f25eedf128f1cc52e69c752e236237`
- Parent branch head at Stage 1E start: (filled in at T0 commit)
- Stage 1D tag: `stage-1d-multi-server-merge-complete`
- Stage 1D suite green: 303/303 (per memory note `project_stage_1d_complete`)

## Spike outcome quick-reference (carryover for context)

- P3 → ALL-PASS — Rope 1.14.0 + Python 3.10–3.13+ supported. Rope library bridge in T8.
- P4 → A — basedpyright 1.39.3 PULL-mode only; auto-responder for blocking server→client requests handled by base `_install_default_request_handlers`. Adapter delivers pull-mode in T5.
- P5a → C (re-confirmed 2026-04-25) — pylsp-mypy DROPPED. PythonStrategy never spawns it (T7).
- Q1 cascade — synthetic per-step `didSave` injection no longer needed (was a pylsp-mypy mitigation).
- Q3 — `basedpyright==1.39.3` exact pin (T0 step 6).
