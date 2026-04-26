# Stage 1E — Python Strategies + LSP Adapters — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1e-python-strategies (submodule); feature/stage-1e-python-strategies (parent)
Author: AI Hive(R)
Built on: stage-1d-multi-server-merge-complete

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0 | Bootstrap branches + ledger + dep pins                             | `86854789` | DONE      | — |
| T1 | language_strategy.py Protocol + Rust/Python mixins                 | `7cb079e1` | DONE      | Protocol uses sentinel defaults so attrs appear in inspect.getmembers (deviation from plan). |
| T2 | rust_strategy.py skeleton (assist-family + ext allow-list)         | `bd88008c` | DONE      | — |
| T3 | pylsp_server.py adapter (spawn/init/facade conformance)            | `ea2aa92d` | DONE      | Adapter overrides `get_language_enum_instance` returning `Language.PYTHON` rather than mutating the legacy `get_ls_class` registry (slot owned by PyrightServer). |
| T4 | pylsp_server.py real workspace/applyEdit drain (1D T11 deferred)   | `0bbe72cb` | DONE      | Branch B — base `execute_command` already returns `(response, drained)`; only the regression test landed. pylsp 1.14.0 lacks `codeAction/resolve`; pylsp-rope ships command-typed actions directly so the resolve call is bypassed. |
| T5 | basedpyright_server.py adapter (pull-mode diagnostic, P4)          | `f1316152` | DONE      | Same T3 deviations re-applied: override `get_language_enum_instance`, implement `_start_server`, use `open_file()` ctx mgr in boot test. Boot+pull GREEN — basedpyright returned items[] with source="basedpyright". |
| T6 | ruff_server.py adapter                                             | `08e37bfe` | DONE      | Same T3/T5 deviations re-applied. Boot+codeAction GREEN — ruff offered source.organizeImports. Test fixed to pass absolute path to `request_code_actions` (it calls `Path(file).as_uri()`). Cross-check (all 3 Python adapters import together) GREEN. |
| T7 | python_strategy.py — MultiServerCoordinator wiring (no mypy)       | `626387aa` | DONE      | 6/6 green. _SERVER_LANGUAGE_TAG mapping forces pool dedup keys to be distinct per LSP role. Q1-cascade regression-guard test passes (no didSave-injection method names leak). |
| T8 | python_strategy.py — 14-step interpreter + Rope library bridge     | `eb3b7bf3` | DONE      | rope 1.14.0 API drift: `MoveModule.get_changes(dest)` takes only dest folder (no `new_name` kwarg) — bridge dispatches Rename for same-dir, MoveModule for cross-dir; `rope.base.change` has no `RenameResource` (collapsed into `MoveResource` with `new_resource` field). 17 T8 tests + 6 T7 regression all green. |
| T9 | __init__.py registry + smoke + ledger close + ff-merge + tag       | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

- 2026-04-25 — Adapter LoC budget per file revised 50→100-150 LoC. Rationale: precedent `vendor/serena/src/solidlsp/language_servers/jedi_server.py` confirms `InitializeParams` alone consumes ~60-80 LoC per adapter. Total Stage 1E LoC still under 1,425 budget.
- 2026-04-25 — Rope library bridge ships 2 of 5 ops at MVP (`move_module`, `change_signature`). The remaining 3 (IntroduceFactory, EncapsulateField, Restructure) routed to Stage 1F. Per drafter §J.3.
- 2026-04-25 — Interpreter discovery chain ships at 14 steps (NOT 16). PEP 723 + direnv steps deferred to v0.2.0. Matches scope-report §7 as written.
- 2026-04-25 — T0 step 1 adapted: parent transitions directly from `develop` to a new `feature/stage-1e-python-strategies` execution branch (the planning branch `feature/plan-stage-1e` was already merged). Submodule branch `feature/stage-1e-python-strategies` opened fresh off `origin/main`.
- 2026-04-25 — T8 rope-1.14.0 API drift captured: `MoveModule.get_changes(dest, resources=, task_handle=)` does NOT accept `new_name` (plan draft was wrong). Bridge now dispatches `rope.refactor.rename.Rename` for same-directory renames and `MoveModule` for cross-directory moves. Also: `rope.base.change.RenameResource` does not exist at 1.14.0 — `MoveResource` carries both `resource` and `new_resource` regardless, and the WorkspaceEdit converter maps it to LSP `rename` kind unconditionally.

## Stage 1D entry baseline

- Submodule `main` head at Stage 1E start: `3ae27952d9f25eedf128f1cc52e69c752e236237`
- Parent branch head at Stage 1E start: `ddb1a5d`
- Parent execution branch: `feature/stage-1e-python-strategies` (opened via git-flow at T0)
- Stage 1D tag: `stage-1d-multi-server-merge-complete`
- Stage 1D suite green: 303/303 (per memory note `project_stage_1d_complete`)

## Spike outcome quick-reference (carryover for context)

- P3 → ALL-PASS — Rope 1.14.0 + Python 3.10–3.13+ supported. Rope library bridge in T8.
- P4 → A — basedpyright 1.39.3 PULL-mode only; auto-responder for blocking server→client requests handled by base `_install_default_request_handlers`. Adapter delivers pull-mode in T5.
- P5a → C (re-confirmed 2026-04-25) — pylsp-mypy DROPPED. PythonStrategy never spawns it (T7).
- Q1 cascade — synthetic per-step `didSave` injection no longer needed (was a pylsp-mypy mitigation).
- Q3 — `basedpyright==1.39.3` exact pin (T0 step 6).
