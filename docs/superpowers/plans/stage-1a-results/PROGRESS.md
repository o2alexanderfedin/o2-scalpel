# Stage 1A — LSP Primitives — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1a-lsp-primitives (parent + submodule)
Author: AI Hive(R)

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0 | Bootstrap feature branches + ledger | _in_progress_ | _pending_ | — |
| T1 | Multi-callback notification dispatch | _pending_ | _pending_ | — |
| T2 | workspace/applyEdit capturing reverse-request handler | _pending_ | _pending_ | — |
| T3 | workspace/configuration + client/registerCapability auto-responders | _pending_ | _pending_ | — |
| T4 | window/showMessageRequest + window/workDoneProgress/create stubs | _pending_ | _pending_ | — |
| T5 | workspace/{semanticTokens,diagnostic}/refresh auto-responders | _pending_ | _pending_ | — |
| T6 | request_code_actions facade | _pending_ | _pending_ | — |
| T7 | resolve_code_action facade | _pending_ | _pending_ | — |
| T8 | execute_command facade | _pending_ | _pending_ | — |
| T9 | wait_for_indexing + indexing token classes | _pending_ | _pending_ | — |
| T10 | override_initialize_params hook | _pending_ | _pending_ | — |
| T11 | is_in_workspace path filter | _pending_ | _pending_ | — |
| T12 | applyEdit capture register on SolidLanguageServer | _pending_ | _pending_ | — |
| T13 | rust_analyzer.py — use override hook + additive `$/progress` | _pending_ | _pending_ | — |
| T14 | Re-bind S1/S2/S3/S6 spikes against new facades | _pending_ | _pending_ | — |
| T15 | Submodule ff-merge to main + parent pointer bump + tag | _pending_ | _pending_ | — |

## Decisions log

- **2026-04-25**: Submodule not gitflow-initialized; use direct `git checkout -b feature/stage-1a-lsp-primitives` per Phase 0 convention. Same ff-merge-to-main pattern at T15.
- **2026-04-25**: Adopt sibling-branch naming `feature/stage-1a-lsp-primitives` in both parent and submodule for traceability.
- **2026-04-25**: Pre-existing `Cargo.lock` untracked file in `vendor/serena/test/spikes/seed_fixtures/calcrs_seed/` carried over from Phase 0; leave alone, it's a Cargo-build artifact.

## Spike outcome quick-reference

- S1 → A (with shim caveat) — additive subscriptions required.
- S2 → A — capability-override hook (~+15 LoC).
- S3 → B (re-verified) — minimal `{applied: true}` ACK + capture, ~+40 LoC.
- S6 → A — `edit:` only on auto_import resolve.
- P1 → A — pylsp-rope reads in-memory; capture WorkspaceEdit via reverse-request.
- P-WB → 5/5 — adopt `is_in_workspace()` verbatim.
