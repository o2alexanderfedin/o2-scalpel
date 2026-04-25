# Stage 1B — Applier + Checkpoints + Transactions — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1b-applier-checkpoints-transactions (parent + submodule)
Author: AI Hive(R)

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0 | Bootstrap feature branches + ledger | parent `8d45aaf` | ✅ | — |
| T1 | TextDocumentEdit matrix (basic + multi-edit + version-checked) | submodule `c14c9315` | OK | — |
| T2 | CreateFile operation (overwrite / ignoreIfExists) | submodule `c5e44ccd` | ✅ | — |
| T3 | DeleteFile operation (recursive / ignoreIfNotExists) | submodule `70590841` | ✅ | — |
| T4 | RenameFile option handling (overwrite / ignoreIfExists) | submodule `f63a59fb` | ✅ | — |
| T5 | SnippetTextEdit defensive `$N`/`${N` stripper | submodule `5a58e5ea` | ✅ | — |
| T6 | Order preservation (descending offset) | submodule `b664c766` | ✅ | Test-only; T1 sort already covered contract |
| T7 | changeAnnotations advisory surfacer | submodule `7b2c9080` | ✅ | — |
| T8 | Atomic snapshot + restore on partial failure | submodule `9f7f1044` | ✅ | — |
| T9 | Workspace-boundary path filter integration | submodule `f04de716` | ✅ | — |
| T10 | Inverse `WorkspaceEdit` computation | submodule `d31eb546` | ✅ | — |
| T11 | `CheckpointStore` LRU(50) | submodule `08dcd344` | ✅ | — |
| T12 | `TransactionStore` LRU(20) | submodule `13803b33` | ✅ | — |
| T13 | Multi-shape integration test + rollback round-trip | submodule `2c5f830e` | ⚠️ DONE_WITH_CONCERNS | Latent bug surfaced — see entry below |
| T14 | Submodule ff-merge to main + parent pointer bump + tag | _pending_ | _pending_ | — |

## Decisions log

- **2026-04-25**: Stage 1B sub-plan written (3428 lines, 15 tasks). Plan over budget on length (target 1500-2000) due to no-placeholder rule — every TDD step carries full code. Acceptable trade.
- **2026-04-25**: `_FileSnapshot` modeled as `dict[str, str]` with sentinel strings (`"__NONEXISTENT__"`, `"__DIRECTORY__"`) instead of dataclass — KISS, the snapshot is a single map updated in-place across per-op appliers.
- **2026-04-25**: T1 version-check uses `getattr(ls, "get_open_file_version", lambda _p: None)(relative_path)` for graceful absence — implementer may need to verify the method exists on `SolidLanguageServer` and adjust.
- **2026-04-25**: `_check_workspace_boundary` parses `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` per-call via `os.environ.get` so test `monkeypatch.setenv` works. Negligible perf hit (one env read per op).
- **2026-04-25**: `TransactionStore._evict_lru` cascades to `CheckpointStore.evict`. `CheckpointStore` never calls back into `TransactionStore` — directed dependency, safe. Lock dropped before cascade.
- **2026-04-25**: T13 surfaced a latent production bug in `inverse_workspace_edit`/`_full_file_overwrite` (T10). The inverse of a `DeleteFile` emits `CreateFile(overwrite=True)` followed by a `TextDocumentEdit` whose end-position is computed from the **snapshot's** content geometry (e.g. `(1,0)` for `"deleted soon\n"`). When the inverse is applied, the freshly-created file is empty, so the synthesized end-position is past EOF and `TextUtils.get_index_from_line_col` raises `InvalidTextLocationError`. The end-of-file clamp comment in `_full_file_overwrite` is aspirational — neither the production `SolidLanguageServer.apply_text_edits_to_file` nor the test fake actually clamps. Fix needed: either (a) clamp end-position at apply time inside the buffer driver, or (b) emit the inverse for `DeleteFile` as a single `CreateFile`+content (write the snapshot during create, not via a separate full-file `TextDocumentEdit`). Test 1 (`test_complex_multi_shape_edit_then_checkpoint_restore`) is committed in failing state to document the bug; Test 2 (`test_three_sequential_edits_transaction_rollback`) passes — the simple TextDocumentEdit-only inverse round-trip composes correctly because both file states share identical geometry.

## Spike outcome carryover

- Stage 1A T11 → `is_in_workspace(target, roots, extra_paths=())` adopted verbatim from P-WB.
- Stage 1A T2 → `pop_pending_apply_edits` drains the WorkspaceEdit reverse-request capture (Phase 0 P1).
- §11.1 priority table for multi-server merge → Stage 1D, NOT Stage 1B.
