# Stage 2A — Ergonomic Facades + Transaction Commit + Real LSP Spawn — PROGRESS

| Task | Branch SHA (submodule) | Outcome | Follow-ups |
|---|---|---|---|
| T0 | 50895d3dc0b0ae4d41f87a97e567cdcf1be26196 | DONE | bootstrap |
| T1 | 72d9b881e0ca34a14dbacf7c120c32869629c4b0 | DONE | _AsyncAdapter wraps sync facades for async coord |
| T2 | 8bdb453019af407ee9d81a3f5ff8cc9cf228d71f | DONE | facade_support helpers |
| T3 | 69cc6f82a04ec7040856cb41f2bba3cc39a1474b | DONE | scalpel_split_file |
| T4 | 5b0a13c5f41a17534384424011fc3e9d08a9e354 | DONE | scalpel_extract |
| T5 | 63fa5e79055b2b6c32946a98c5ce91f9771f6411 | DONE | scalpel_inline |
| T6 | 1c45917797eb696fc8ab7cc98c3efd120e35db5c | DONE | scalpel_rename + text-search fallback |
| T7 | cb09c51a4408c160e38bf08eb0baa478cef5a926 | DONE | scalpel_imports_organize |
| T8 | b0c79041f306d001379bd8dcf5f56958ca86f85f | DONE | scalpel_transaction_commit + TransactionStore.steps/expires_at |
| T9 | ad2930334aa602b7491a2f856c8d7b9ffe740f05 | DONE | Q4 boundary integration matrix |
| T10 | f9c7134509212104d84c8a9086ebcbd56312ce4a | DONE | registry + Stage 1G T9 EXPECTED_NAMES extension |
| T11 | f9c7134509212104d84c8a9086ebcbd56312ce4a | DONE | submodule ff-merge to main + tag + parent merge to develop + tag |

## Entry baseline

- Submodule branch: `feature/stage-2a-ergonomic-facades` from `origin/main` @ `ee0a123b888c3e0659ed06775aebf11f70f3fec0`
- Parent branch: `feature/stage-2a-ergonomic-facades` from `origin/develop` @ `779149956c78d5ad1b299d596ac14b1093ddc038`
- Stage 1J exit tag: `stage-1j-plugin-skill-generator-complete`
- Test baseline (Stage 1J): submodule pytest = 499 passed, 3 skipped (full `test/`).

## Exit baseline

- Submodule `main` tip @ `f9c7134509212104d84c8a9086ebcbd56312ce4a` (tagged `stage-2a-ergonomic-facades-complete`).
- Parent `develop` tip after merge — to be tagged `stage-2a-ergonomic-facades-complete` after this commit.
- Test count (Stage 2A): added 87 new tests (T1=10, T2=10, T3=6, T4=6, T5=5, T6=5, T7=5, T8=4, T9=12, T10=24).
- Full submodule `test/spikes/` regression: 586 passed, 3 skipped (was 499 before Stage 2A; +87 new tests, zero regressions).
- Integration tests (`test/integration/`) sample: 4 passed.
- LoC delta (production): scalpel_runtime.py +149/-10, facade_support.py +179, scalpel_facades.py +918, transactions.py +33/-2, scalpel_primitives.py +6/-1, tools/__init__.py +1. Total ~1,275 LoC production.

## Sync/async wrapping resolution

Implemented as `_AsyncAdapter` class in `scalpel_runtime.py`. Each spawned `SolidLanguageServer` is wrapped — the four facade methods (`request_code_actions`, `resolve_code_action`, `execute_command`, `request_rename_symbol_edit`) become coroutines via `asyncio.to_thread`. Other attributes pass through unchanged. Stage 1D `_FakeServer` doubles remain async-native and bypass the adapter.

## Follow-ups for Stage 2B

1. **Coordinator `find_symbol_position` not yet implemented.** Stage 2A's `ScalpelRenameTool` falls back to a thin text-search via `_text_search_position` — Stage 2B should add a real `find_symbol_position` implementation on `MultiServerCoordinator` (likely backed by `textDocument/documentSymbol` aggregated across servers) and remove the fallback once landed.

2. **`MultiServerCoordinator.merge_rename` signature mismatch.** The plan assumed `merge_rename(file=..., position=..., new_name=...)` returning `{primary_server, workspace_edit}`; the real signature is `merge_rename(relative_file_path, line, column, new_name, language)` returning `(workspace_edit_or_none, warnings)`. The facade currently passes the plan-shape kwargs and reads `merged.get("workspace_edit", ...)` — works against test doubles but real wiring needs an adapter shim before the first end-to-end run. Tracked as Stage 2B item.

3. **`merge_organize_imports` not yet present on coordinator.** Stage 2A `ScalpelImportsOrganizeTool` calls `coord.merge_code_actions(only=["source.organizeImports"])` per the plan — the merge happens generically. Stage 2B may add a typed wrapper if benchmarks show benefit.

4. **`E10-py __all__` preservation rope path** — only the module-rename short-circuit is wired in `_rename_python_module`; the symbol-rename path falls through to `coord.merge_rename` and does not consult `__all__`. Stage 2B E2E scenario E10 will surface this.

5. **`CapabilityCatalog.hash()` method** — Stage 1G T7 still uses `hasattr` guard; the optional follow-up to add `hash() -> str` (SHA-256 of canonical JSON) was not pursued in Stage 2A scope.

6. **Pyright clean-up audit** — Stage 2A code passes runtime tests; explicit Pyright info-level (★) audit deferred to Stage 2B sweep so the per-task watchdog cadence stays intact.
