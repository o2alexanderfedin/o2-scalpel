# Stage 1D — Multi-Server Merge — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1d-multi-server-merge (parent + submodule)
Author: AI Hive(R)
Built on: stage-1b-applier-checkpoints-transactions-complete

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0  | Bootstrap progress ledger + `_FakeServer` fixture                      | `d897516e` | OK | — |
| T1  | §11.6 multi-server schemas (pydantic v2 BaseModels)                    | _pending_ | _pending_ | — |
| T2  | `broadcast()` parallel fan-out (asyncio.gather + wait_for)             | _pending_ | _pending_ | — |
| T3  | `_normalize_kind()` — P2 sub-kind collapse                             | _pending_ | _pending_ | — |
| T4  | `_apply_priority()` — §11.1 priority table                             | _pending_ | _pending_ | — |
| T5  | `_dedup()` — title + WorkspaceEdit structural equality                 | _pending_ | _pending_ | — |
| T6  | resolve-then-classify (deferred + direct)                              | _pending_ | _pending_ | — |
| T7  | §11.7 four invariants (apply / ast.parse / disabled / boundary)        | _pending_ | _pending_ | — |
| T8  | `merge_rename()` + P6 whole-file ↔ surgical reconciliation             | _pending_ | _pending_ | — |
| T9  | provenance + edit-attribution log (§11.4 + §11.5) + replay             | _pending_ | _pending_ | — |
| T10 | §11.2 six server-disagreement cases                                    | _pending_ | _pending_ | — |
| T11 | E2E: 3-fake-server P2 + P6 + auto-import replay                        | _pending_ | _pending_ | — |
| T12 | Submodule ff-merge to main + parent pointer bump + tag                 | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

## Stage 1B entry baseline

- Submodule `main` head at Stage 1D start: `ba7e62b1` (per Stage 1B PROGRESS final verdict)
- Parent `develop` head at Stage 1D start: <fill in via `git rev-parse develop` at T0 close>
- Stage 1B tag: `stage-1b-applier-checkpoints-transactions-complete`
- Stage 1B spike-suite green: 130/130 (per Stage 1B PROGRESS final verdict)

## Spike outcome quick-reference (carryover for context)

- P2 → DIVERGENT — ruff wins `source.organizeImports`; pylsp-rope dropped at merge time. Sub-kind hierarchical normalization required (`source.organizeImports.ruff` → `source.organizeImports`). Implemented in T3 + T4.
- P5a → C (DROP pylsp-mypy) — merger never receives pylsp-mypy candidate; "type error" priority row collapses to basedpyright-only. Documented in §11.1 cross-reference; enforced by T4 priority table.
- P6 → DIVERGENT — pylsp wins `textDocument/rename`; whole-file vs surgical edit reconciliation required. Implemented in T8 via `difflib` line-mapping.
- §11.1 priority table → Stage 1D (this plan).
- §11.6 schemas → Stage 1D T1.
- §11.7 invariants → Stage 1D T7 (consumes Stage 1A `is_in_workspace` for invariant 4).
- §11.5 edit-attribution log → Stage 1D T9.
