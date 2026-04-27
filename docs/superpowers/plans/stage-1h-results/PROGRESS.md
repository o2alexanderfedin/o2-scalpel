# Stage 1H — Full Fixtures + Per-Assist-Family Integration Tests — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1h-fixtures-integration-tests (both parent + submodule)
Author: AI Hive(R)
Built on: stage-1g-primitive-tools-complete
Predecessor green: 303 + Stage 1E + 1F + 1G suite (per stage-1g-results/PROGRESS.md)
**Status: REDUCED-SCOPE v0.1.0 COMPLETE — full plan deferred to v0.2.0 "Stage 1H continuation"**

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0          | Bootstrap branches + ledger + fixture-tree skeleton dirs                | 9623c61c | OK | — |
| T1-min      | calcrs Cargo workspace shell + calcrs-core companion (NOT 5+18)         | 3c628177 | OK — `cargo check` clean (under `CARGO_BUILD_RUSTC=rustc` workaround) | 17 RA companion crates → v0.2.0 |
| T2          | 13 additional RA companion crates                                       | _deferred_ | DEFERRED → v0.2.0 | route under "Stage 1H continuation" |
| T3-min      | calcpy package shell + calcpy/core.py (NOT monolith + 4 sub-fixtures)   | bf471377 | OK — `import calcpy; calcpy.evaluate(calcpy.parse('42'))` round-trips | 3 calcpy sub-fixtures → v0.2.0 |
| T4          | calcpy sub-fixture 2 (calcpy_circular)                                  | _deferred_ | DEFERRED → v0.2.0 | — |
| T5          | calcpy sub-fixture 3 (calcpy_dataclasses)                               | _deferred_ | DEFERRED → v0.2.0 | — |
| T6          | calcpy sub-fixture 4 (calcpy_notebooks)                                 | _deferred_ | DEFERRED → v0.2.0 | — |
| T7          | integration test harness (test/integration/conftest.py)                 | 5279700d | OK — boots ra+pylsp+basedpyright+ruff session-scoped | — |
| T-smoke     | 3 smoke integration tests (rust codeaction / python codeaction / health) | 5279700d | OK — 4/4 sub-tests green | replaces T8/T10 minimum |
| T8          | 8 Rust assist-family integration tests (extract/inline/move/rewrite)    | _deferred_ | DEFERRED → v0.2.0 | — |
| T9          | 8 more Rust integration tests (generators/convert/pattern/visibility/…) | _deferred_ | DEFERRED → v0.2.0 | — |
| T10         | 8 Python integration tests (rope-bridge facades + pylsp + basedpyright) | _deferred_ | DEFERRED → v0.2.0 | — |
| T11         | 7 cross-language tests (multi-server merge invariants from §11.7)       | _deferred_ | DEFERRED → v0.2.0 | — |
| T-close     | Ledger close + ff-merge to main + tag                                   | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

- 2026-04-25 — Plan deviation noted: capability catalog module is `src/serena/refactoring/capabilities.py` (not `capability_catalog.py` as the plan references). Surface check at T0 step 5 adapted accordingly.
- 2026-04-25 — Stage 1H execution PAUSED after T0 bootstrap. Honest scope assessment by orchestrator: 9,460 LoC of fixtures + 31 integration tests requiring real-LSP boots cannot fit the imposed 8-hour budget without producing half-broken submodule state. T0 committed as a safe bootstrap checkpoint; T1..T12 deferred pending budget revision or scope reduction (e.g., minimum-viable subset: T1+T3+T7 + 3 representative integration tests proving the harness boots all four LSPs).
- 2026-04-25 — Orchestrator scope-reduced Stage 1H to v0.1.0 minimum: T1-min (calcrs workspace + 1 companion), T3-min (calcpy + core.py), T7 at full quality, T-smoke (3 tests). Routes 28 tests + 17 RA companions + 3 calcpy sub-fixtures to v0.2.0 "Stage 1H continuation" milestone. Justification: covers Stage 2A (5 facade integration tests) + Stage 2B (9 MVP E2E scenarios) actual cut criteria; full plan was honest 16–24 h scope.
- 2026-04-25 — `Cargo.lock` gitignored at fixture root (matches existing `test/spikes/seed_fixtures/calcrs_seed/` pattern). Lockfile is recomputed by each cargo invocation.
- 2026-04-25 — `CARGO_BUILD_RUSTC=rustc` workaround applied in conftest module-load to defeat the developer machine's global `~/.cargo/config.toml` `rust-fv-driver` wrapper (broken dyld lookup). Same workaround already in `test/spikes/test_spike_s3_apply_edit_reverse.py:24`.
- 2026-04-25 — `WorkspaceHealth` smoke asserts pylsp-rope + ruff + rust-analyzer (3 catalog-visible servers), NOT 4 LSPs as the brief named. basedpyright registers capabilities dynamically post-init; the static Stage 1F catalog enumerates only servers with at-strategy-build advertised capabilities. The basedpyright LSP boot itself IS exercised by the `basedpyright_lsp` session fixture in `conftest.py` — the harness wires all 4.
- 2026-04-25 — Whole-file probe in Rust smoke uses computed file-end coordinates instead of `{line:10000, char:0}`; rust-analyzer rejects out-of-range positions while ruff clamps. The `whole_file_range` fixture remains for ruff/python paths.

## Stage 1H entry baseline

- Submodule `main` head at Stage 1H start: `71ceedb3` (Stage 1J complete)
- Parent branch: feature/stage-1h-fixtures-integration-tests off develop @ `653a631`
- Stage 1G tag: `stage-1g-primitive-tools-complete`
- Predecessor suite green: per stage-1g-results/PROGRESS.md

## Stage 1H exit state (v0.1.0)

- Submodule final SHA: `5279700d`
- Submodule tag: `stage-1h-fixtures-integration-tests-complete` (applied at T-close)
- Parent merge into develop: at T-close
- Parent tag: `stage-1h-v0.1.0-complete` (applied at T-close)
- Test count: **503 passed, 1 skipped** across `test/spikes/` + `test/integration/` (Stage 1H added 4 new tests; full suite was 499 + 1 skipped pre-Stage-1H).
- Pyright on `test/integration/`: **0 errors**, 41 warnings (pre-existing project bar — see Stage 1A–1G ledgers for the same warning shape).

## Fixture LoC running tally (final, v0.1.0)

| Task | Cumulative fixture LoC | Cumulative test LoC | Total Stage 1H LoC |
|---|---|---|---|
| T0      | 0                  | 1   (pkg `__init__.py`)        | 1                                 |
| T1-min  | +201 (Rust + manifests)  | +1                              | 202                               |
| T3-min  | +155 (Python + manifest)  | +1                              | 358                               |
| T7      | +155                       | +210 (conftest)                 | 568 (conftest counted as test surface) |
| T-smoke | +155                       | +210 + ~240 (3 smoke modules)   | ~810                              |

LoC delta vs full-plan target (~9,460):
- Production: 0 LoC (Stage 1H is pure test/fixture surface — same as full plan).
- Fixtures: ~360 LoC delivered vs ~5,240 LoC planned (~7%).
- Tests + harness: ~450 LoC delivered vs ~4,180 LoC planned (~11%).
- Total: ~810 LoC delivered vs ~9,460 LoC planned (~9%).

The remaining ~91% routes to v0.2.0 "Stage 1H continuation".

## Items routed to v0.2.0 "Stage 1H continuation"

- 17 RA companion crates: `ra_extractors`, `ra_inliners`, `ra_visibility`, `ra_imports`, `ra_glob_imports`, `ra_ordering`, `ra_generators_traits`, `ra_generators_methods`, `ra_convert_typeshape`, `ra_convert_returntype`, `ra_pattern_destructuring`, `ra_lifetimes`, `ra_proc_macros`, `ra_ssr`, `ra_macros`, `ra_module_layouts`, `ra_quickfixes`, `ra_workspace_edit_shapes`, `ra_term_search` (~3,200 LoC).
- 3 calcpy sub-fixtures: `calcpy_namespace` (PEP 420), `calcpy_circular` (lazy-import trap), `calcpy_dataclasses` (5 dataclass restructure), `calcpy_notebooks` (.ipynb companion) (~590 LoC).
- 28 deferred per-assist-family integration test modules:
  - **Rust (15)**: T1 module/file boundary, T2 extractors_rust, T3 inliners_rust, T4 visibility_imports, T5 glob_imports, T6 ordering_rust, T7 generators_traits, T8 generators_methods, T9 convert_typeshape, T10 convert_returntype, T11 pattern_rust, T12 lifetimes_rust, T13 term_search_rust, T14 quickfix_rust, T15 macros_rust, T16 ssr_rust.
  - **Python (8)**: T17 extract_method_py, T18 extract_variable_py, T19 inline_py, T20 organize_import_py, T21 basedpyright_autoimport, T22 ruff_fix_all, T23 move_global_py, T24 rename_module_py.
  - **Cross-language (7)**: T25 multi_server_organize_imports, T26 multi_server_workspace_boundary, T27 multi_server_apply_cleanly, T28 multi_server_syntactic_validity, T29 multi_server_disabled_reason, T30 multi_server_namespace_pkg, T31 multi_server_circular_import.
- Headline calcpy monolith (~950 LoC `calcpy.py` + `calcpy.pyi` stub + 4 baseline test modules + `expected/baseline.txt`).

## Concerns / follow-ups

- **basedpyright dynamic-capability gap**: _CLOSED 2026-04-26 (tag `stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete`)._ `DynamicCapabilityRegistry` records `client/registerCapability` events; `LanguageHealth.dynamic_capabilities` (tuple) surfaces them in `workspace_health`. See `docs/gap-analysis/WHAT-REMAINS.md` §4.
- **rust-analyzer position validation**: _CLOSED 2026-04-26 (tag `stage-v0.2.0-followups-complete`, Leaf 02)._ `compute_file_range(path)` LSP helper at `vendor/serena/src/solidlsp/util/file_range.py`; `RustAnalyzer.request_code_actions` `@override` raises `ValueError` preflight; `whole_file_range` conftest fixture migrated to dual-mode. 12 tests; 0/0/0 pyright. See `docs/gap-analysis/WHAT-REMAINS.md` §4.
- **Multi-server async wrapping**: _CLOSED 2026-04-26 (tag `stage-v0.2.0-followups-complete`, Leaf 03)._ `serena.refactoring._async_check.assert_servers_async_callable` rejects raw sync servers at `MultiServerCoordinator.__init__` with explicit `TypeError` pointing at `_AsyncAdapter`. `AWAITED_SERVER_METHODS` is single source of truth feeding both the coordinator gate and `_AsyncAdapter._ASYNC_METHODS`. Real-adapter parallelism evidence test boots all 3 Python servers. 18 tests; 0/0/0 pyright. See `docs/gap-analysis/WHAT-REMAINS.md` §4.
- **`CARGO_BUILD_RUSTC=rustc` workaround**: _CLOSED 2026-04-26 (tag `stage-v0.2.0-followups-complete`, Leaf 04)._ Inline `os.environ.setdefault` removed from 7 sites; relocated to opt-in pytest plugin `vendor/serena/test/conftest_dev_host.py` gated on `O2_SCALPEL_LOCAL_HOST=1`. CI runs clean. Single-source-of-truth doc at `docs/dev/host-rustc-shim.md`. See `docs/gap-analysis/WHAT-REMAINS.md` §4.

## Spike outcome quick-reference (carryover for context)

- P3 → ALL-PASS — Rope 1.14.0 + Python 3.10–3.13+ supported. Library bridge integration tested in T23 / T24 (deferred to v0.2.0).
- P4 → A — basedpyright 1.39.3 PULL-mode only; T21 (deferred) exercises pull-mode auto-import.
- P5a → B (re-run 2026-04-26, SHIP) — pylsp-mypy ships as a plugin inside pylsp-rope (`live_mode: false` + `dmypy: true`); see `solidlsp.decisions.p5a_mypy`. T20 / T25 (deferred) still verify the SERVER_SET (`{pylsp-rope, basedpyright, ruff}`) — pylsp-mypy is NOT a server, so SERVER_SET assertions remain valid.
- Q1 cascade — synthetic per-step `didSave` injection no longer needed (was a pylsp-mypy mitigation).
- Q3 — `basedpyright==1.39.3` exact pin verified by adapter boot in T7 conftest fixture.
- S5 → see S5 note — `expandMacro` proc-macro pathway will be tested via `ra_proc_macros` + T15 (deferred to v0.2.0).
