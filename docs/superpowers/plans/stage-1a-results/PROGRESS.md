# Stage 1A — LSP Primitives — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1a-lsp-primitives (parent + submodule)
Author: AI Hive(R)

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0 | Bootstrap feature branches + ledger | parent `5572def`, sub on branch | ✅ | — |
| T1 | Multi-callback notification dispatch | sub `2cabdd49` | ✅ | NIT: multi-listener CancelledError early-returns rest of dispatch — acceptable cooperative-cancel semantics, document if it surfaces |
| T2 | workspace/applyEdit capturing reverse-request handler | sub `a40cb08d` | ✅ | NIT: ApplyWorkspaceEditResponse `failureReason: None` (drop on next-touch — currently accepted by RA per S3) |
| T3 | workspace/configuration + client/registerCapability auto-responders | sub `ae7f7946` | ✅ | NITs: register-cap doesn't honor watchers (OK at MVP); hoist `_ConcreteSLS` to conftest when T4/T5 land third copy |
| T4 | window/showMessageRequest + window/workDoneProgress/create stubs | sub `172294ae` | ✅ | T3-NIT folded in: `_ConcreteSLS` + `slim_sls` hoisted to conftest; T2 now uses thin `apply_edit_sls` wrapper |
| T5 | workspace/{semanticTokens,diagnostic}/refresh auto-responders | sub `b8b7bc4a` | ✅ | — |
| T6 | request_code_actions facade | sub `1f713d4c` | ✅ | NIT: no abs-path validation on `file` (Path.as_uri() raises ValueError on relative); docstring contracts it |
| T7 | resolve_code_action facade | sub `b0052b86` | ✅ | — |
| T8 | execute_command facade | sub `02a69685` | ✅ | — |
| T9 | wait_for_indexing + indexing token classes | sub `f833a5e1` | ✅ | NIT: subclasses can extend `_INDEXING_TOKEN_PREFIXES` (will matter for Python adapters in Stage 1E) |
| T10 | override_initialize_params hook | sub `cff32adb` + fix `5e7f03c4` | ✅ | Implementer chose runtime monkey-patch of `self.server.send.initialize` in `__init__` (single chokepoint, transparent to all 30+ subclasses). Type-cast follow-up satisfies InitializeParams TypedDict |
| T11 | is_in_workspace path filter | sub `1d0a0d13` | ✅ | — |
| T12 | applyEdit capture register on SolidLanguageServer | sub `04cd4a0c` | ✅ | analyzerStatus supported on local RA 1.95.0; success branch fires |
| T13 | rust_analyzer.py — use override hook + additive `$/progress` | sub `e31c2413` | ✅ | hard-coded `True` at L458 left in place; override flips on the wire (KISS) |
| T14 | Re-bind S1/S2/S3/S6 spikes against new facades | sub `8a458114` + fix `73f54b23` | ✅ | S1 floor relaxed to `>= 5` cold-start events (was 178 single-observation); cold-start probe still uses second SLS instance + public additive listener |
| T15 | Submodule ff-merge to main + parent pointer bump + tag | _in_progress_ | _pending_ | — |

## Decisions log

- **2026-04-25**: Submodule not gitflow-initialized; use direct `git checkout -b feature/stage-1a-lsp-primitives` per Phase 0 convention. Same ff-merge-to-main pattern at T15.
- **2026-04-25**: Adopt sibling-branch naming `feature/stage-1a-lsp-primitives` in both parent and submodule for traceability.
- **2026-04-25**: Pre-existing `Cargo.lock` untracked file in `vendor/serena/test/spikes/seed_fixtures/calcrs_seed/` carried over from Phase 0; leave alone, it's a Cargo-build artifact.
- **2026-04-25 (T1)**: Plan referenced class `LanguageServerHandler`; the actual class in `solidlsp/ls_process.py` is `LanguageServerProcess`. Plan amended in commit `ce2496d` (parent). Code uses correct name.
- **2026-04-25 (T1)**: Code-quality reviewer flagged 3 dispatch-semantic regressions in T1's `_notification_handler` rewrite; restored in `2cabdd49` (sub): asyncio.CancelledError swallow, `_is_shutting_down` log gate, `Unhandled method` warning. Added 4 regression-pinning tests; spike suite stays 21/21 green with venv on PATH.
- **2026-04-25 (test env)**: Submodule spike tests require venv on PATH (`pylsp`/`basedpyright` binaries); use `PATH="$(pwd)/.venv/bin:$PATH" .venv/bin/pytest test/spikes/`. Without this, P1/P2/P3/P3a/P4/P5a/P6 fail with `FileNotFoundError`.

## Spike outcome quick-reference

- S1 → A (with shim caveat) — additive subscriptions required.
- S2 → A — capability-override hook (~+15 LoC).
- S3 → B (re-verified) — minimal `{applied: true}` ACK + capture, ~+40 LoC.
- S6 → A — `edit:` only on auto_import resolve.
- P1 → A — pylsp-rope reads in-memory; capture WorkspaceEdit via reverse-request.
- P-WB → 5/5 — adopt `is_in_workspace()` verbatim.
