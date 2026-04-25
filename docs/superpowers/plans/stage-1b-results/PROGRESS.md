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
| T5 | SnippetTextEdit defensive `$N`/`${N` stripper | _pending_ | _pending_ | — |
| T6 | Order preservation (descending offset) | _pending_ | _pending_ | — |
| T7 | changeAnnotations advisory surfacer | _pending_ | _pending_ | — |
| T8 | Atomic snapshot + restore on partial failure | _pending_ | _pending_ | — |
| T9 | Workspace-boundary path filter integration | _pending_ | _pending_ | — |
| T10 | Inverse `WorkspaceEdit` computation | _pending_ | _pending_ | — |
| T11 | `CheckpointStore` LRU(50) | _pending_ | _pending_ | — |
| T12 | `TransactionStore` LRU(20) | _pending_ | _pending_ | — |
| T13 | Multi-shape integration test + rollback round-trip | _pending_ | _pending_ | — |
| T14 | Submodule ff-merge to main + parent pointer bump + tag | _pending_ | _pending_ | — |

## Decisions log

- **2026-04-25**: Stage 1B sub-plan written (3428 lines, 15 tasks). Plan over budget on length (target 1500-2000) due to no-placeholder rule — every TDD step carries full code. Acceptable trade.
- **2026-04-25**: `_FileSnapshot` modeled as `dict[str, str]` with sentinel strings (`"__NONEXISTENT__"`, `"__DIRECTORY__"`) instead of dataclass — KISS, the snapshot is a single map updated in-place across per-op appliers.
- **2026-04-25**: T1 version-check uses `getattr(ls, "get_open_file_version", lambda _p: None)(relative_path)` for graceful absence — implementer may need to verify the method exists on `SolidLanguageServer` and adjust.
- **2026-04-25**: `_check_workspace_boundary` parses `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` per-call via `os.environ.get` so test `monkeypatch.setenv` works. Negligible perf hit (one env read per op).
- **2026-04-25**: `TransactionStore._evict_lru` cascades to `CheckpointStore.evict`. `CheckpointStore` never calls back into `TransactionStore` — directed dependency, safe. Lock dropped before cascade.

## Spike outcome carryover

- Stage 1A T11 → `is_in_workspace(target, roots, extra_paths=())` adopted verbatim from P-WB.
- Stage 1A T2 → `pop_pending_apply_edits` drains the WorkspaceEdit reverse-request capture (Phase 0 P1).
- §11.1 priority table for multi-server merge → Stage 1D, NOT Stage 1B.
