# Pre-MVP Spikes — Aggregate Summary

Date: 2026-04-24
Spikes run: 13 (S1, S2, S3, S4, S5, S6, P1, P2, P3, P3a, P4, P5a, P6, P-WB)
Branch: feature/phase-0-pre-mvp-spikes
Author: AI Hive(R)

---

## 1. Per-spike outcomes

| ID | Title | Outcome | Decision impact |
|---|---|---|---|
| S1 | `$/progress` forwarding | A (with shim caveat) | Stage 1A adds +30 LoC notification-tap shim per plan §13 fallback (additive subscriptions, no clobbering); `wait_for_indexing()` watches `rustAnalyzer/{Fetching, Building CrateGraph, Loading proc-macros, cachePriming, Roots Scanned, Building compile-time-deps}` + `rust-analyzer/flycheck/N`. |
| S2 | `snippetTextEdit:false` honored | A | Defensive `$N` strip in applier (~10 LoC) suffices; +15 LoC capability-override hook needed in Stage 1A (rust-analyzer subclass hard-codes `experimental.snippetTextEdit: True`). |
| S3 | `applyEdit` reverse-request | B (with re-verify caveat) | Stage 1A ships minimal `{applied: true, failureReason: null}` stub (~+20 LoC), reclaiming ~50 LoC vs. full handler; re-verified on S4/S5/S6. P1 finding upgrades stub: it must CAPTURE the `WorkspaceEdit`, not merely ACK. |
| S4 | `experimental/ssr` upper bound | feature-unavailable (LSP -32601) on rust-analyzer 1.95.0 stock | `max_edits: int = 500` default pre-fixed by §13. Gate `scalpel_rust_ssr` behind a runtime capability probe so it errors gracefully on stock builds. |
| S5 | `expandMacro` on proc macros | feature-unavailable (LSP -32601) on rust-analyzer 1.95.0 stock | Facade unavailable until rust-analyzer is built with `expandMacro` support; share the runtime capability-probe machinery with S4. |
| S6 | auto_import resolve shape | A | Applier branches on `edit:` only (+0 LoC vs. optimistic two-shape branch); confirms S3 minimal-stub decision generalizes. In-memory `didChange` pollution path works for rust-analyzer code-action surfacing — no `didSave` round-trip needed. |
| P1 | pylsp-rope unsaved buffer | A | Stage 1E `PythonStrategy` passes the buffer via `didChange` only; no extra `didSave` round-trip per code-action call. |
| P2 | organize-imports merge winner | DIVERGENT (ruff wins per §11.1) | Ruff wins by §11.1 priority table; pylsp-rope's organize-imports dropped at merge time when both are available. Merge rule must normalize hierarchical sub-kinds (`source.organizeImports.ruff` ↔ `source.organizeImports`). |
| P3 | Rope vs PEP 695/701/654 | ALL-PASS (rope 1.14.0 + Python 3.13.3) | All-pass → declare Python 3.10–3.13+ supported. No version-pin fallback path needed. |
| P3a | basedpyright==1.39.3 baseline | BASELINE ESTABLISHED | 0 errors outside `_pep_syntax.py` on `seed_python` with the Q3 pin (`basedpyright==1.39.3` exact); re-run at Stage 1H against full calcpy with the same path-partitioning rule. |
| P4 | basedpyright relatedInformation | A | `RefactorResult.diagnostics_delta.severity_breakdown` exposes per-diagnostic `related_locations: list[Location]` (~+15 LoC); consumers must tolerate empty arrays since `reportArgumentType` on a same-file callee carries title only. **Pull-mode** finding: Stage 1E `BasedpyrightServer` adapter MUST call `textDocument/diagnostic` explicitly (1.39.3 emits ZERO `publishDiagnostics`). |
| P5a | pylsp-mypy stale-rate | C — drop pylsp-mypy at MVP | Drop pylsp-mypy from MVP active server set; basedpyright remains sole type-error source per MVP §11.1. specialist-python.md §3.5 must update the pylsp config block to `"pylsp_mypy": {"enabled": False}`. Stale_rate 8.33% (1/12, cold-daemon step 1); p95 8.031s. |
| P6 | three-server rename convergence | DIVERGENT (pylsp wins per §11.1) | Stage 1D `multi_server.py` rename-merger picks pylsp; logs `provenance.disagreement` warning carrying the symdiff summary (only_in_pylsp / only_in_basedpyright counts + samples). pylsp ships whole-file replacement edits across 2 files; basedpyright ships surgical token-range edits in 1 file (misses `__main__.py` cross-file refs in pull-mode). |
| P-WB | workspace-boundary rule | 5/5 PASS | Adopt `is_in_workspace(target, roots)` verbatim in Stage 1A `WorkspaceEditApplier` per Q4 §7.1; treat `OutsideWorkspace` annotation as advisory and the path filter as enforcement. `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` plumbing validated. |

---

## 2. Tier-1 (BLOCKING) verdict

The 5 blocking spikes — S1, S3, P1, P2, P5a — were the gating set per plan §13.

- **S1: A (with shim caveat)** — `$/progress` reaches the dispatcher with rich rust-analyzer indexing tokens (178 events, 7 distinct token classes including `rustAnalyzer/Fetching`, `Building CrateGraph`, `Loading proc-macros`, `cachePriming`, `Roots Scanned`, `Building compile-time-deps`, and `rust-analyzer/flycheck/N`). Public-API tap is clobbered by `rust_analyzer.py:720` `do_nothing` registration + single-callback dispatcher → +30 LoC notification-tap shim required (Stage 1A budget).
- **S3: B** — minimal `applyEdit` `{applied: true, failureReason: null}` stub sufficient (re-verified on S4/S5/S6). P1's discovery (pylsp-rope ships `WorkspaceEdit`s via `applyEdit` reverse-request) means the stub must CAPTURE the payload, not merely ACK — raising the +20 LoC stub to ~+40 LoC.
- **P1: A** — pylsp-rope reads from the in-memory pylsp document buffer (`workspace.get_maybe_document(uri).source`); after `didChange` (no `didSave`), inline produces `_TEST_CALL = 1 + 2` newText that exists ONLY in the in-memory buffer. No extra `didSave` round-trip in Stage 1E `PythonStrategy`.
- **P2: DIVERGENT** — both LSPs return `source.organizeImports`, but with materially different behaviors (pylsp-rope removes unused imports under `source.organizeImports`; ruff sorts only — removal lives under `source.fixAll.ruff`). Decision fixed: **ruff wins** per §11.1.
- **P5a: C** — stale_rate 8.33% (cold-daemon step 1) AND p95 8.031s; both Q1 falsifier criteria fail. Decision fixed: **drop pylsp-mypy** from MVP active set; basedpyright sole type-error source per §11.1.

**All 5 blocking spikes have produced actionable evidence; none escalated to BLOCKED state.** Stage 1 entry is approved on the blocking-spike axis.

---

## 3. Tier-2 (non-blocking) outcomes

- **S2** — capability negotiation works: with `experimental.snippetTextEdit: false` advertised (via instance monkey-patch of `_get_initialize_params`), 0 of 43 resolved code actions emit `$N`/`${N` snippet markers across a 10-range sweep over `lib.rs`. Defensive `$N` regex in applier suffices.
- **S4** — `experimental/ssr` returns LSP `-32601` on stock rust-analyzer 1.95.0; capability probe required before exposing the facade. Default `max_edits = 500` pre-fixed by §13. Fix-loop landed structured `_classify_failure(exc) -> (failure_class, lsp_code)` parsing JSON-RPC `-326XX` codes + dynamic `_capture_rust_analyzer_version()` runtime capture.
- **S5** — `rust-analyzer/expandMacro` returns LSP `-32601` on the same build for both `macro_rules!` and proc-macro positions; declarative-vs-proc-macro question is unanswerable on stock rust-analyzer. Same probe strategy as S4.
- **S6** — auto_import quickfix is `edit:`-typed after `codeAction/resolve` (edit_only=1, command_only=0); applier single-branch path holds. Confirms in-memory `didChange` pollution works for rust-analyzer.
- **P3** — pylsp + rope 1.14.0 parses PEP 695 (type aliases), PEP 701 (nested f-strings), and PEP 654 (except groups) cleanly on Python 3.13.3; no version-pin needed.
- **P3a** — `basedpyright==1.39.3` exact pin baselined: 0 errors / 1 warning on `seed_python` excluding the intentional `_pep_syntax.py` fixture (P3's PEP-654 semantic violation). No CLI `--exclude` flag in 1.39.3; spike partitions diagnostics by file path.
- **P4** — 2/13 basedpyright-sourced diagnostics carry non-empty `relatedInformation` (`reportIncompatibleMethodOverride` → base-class method; `reportCallIssue` overload mismatch → closest-matching overload). PULL-mode-only diagnostics finding is the live wrapper-gap.
- **P6** — pylsp + basedpyright DIVERGE on `textDocument/rename`: pylsp emits whole-file replacement edits across `__init__.py` + `__main__.py` (cross-file complete); basedpyright emits surgical token-range edits in `__init__.py` only (including the `__all__` string `"add"` → `"plus"`) and misses `__main__.py` in pull-mode. Symmetric difference 4/4. Per §11.1: pylsp wins; merger logs `provenance.disagreement`.
- **P-WB** — pure-Python path-prefix probe with `Path.resolve()` semantics passes 5/5 cases (in-workspace, registry, random-tmp, `extra_paths` included, `extra_paths` NOT included). Adopt verbatim. Windows path-semantics revisit deferred.

---

## 4. Stage 1 LoC budget reconciliation

Per plan §13, "+250 LoC of remediation across spikes" was budgeted in §8.7 / §9.7. Actual deltas:

| Spike | Δ LoC | Stage | Note |
|---|---|---|---|
| S1 | +30 | 1A | notification-tap shim (plan §13 fallback) |
| S2 | +15 | 1A | capability-override hook on `SolidLanguageServer` (defensive `$N` strip itself ~10 LoC was already in budget) |
| S3 | +20 | 1A | `applyEdit` reverse-request handler upgraded from minimal-ACK to capture-WorkspaceEdit per P1 finding |
| S4 | +15 | 1B | `scalpel_rust_ssr` runtime capability probe |
| S5 | +0 | 1B | shares the S4 capability-probe machinery |
| S6 | +0 | 1A | edit-only path; reclaim ~40 LoC budgeted for two-shape branch |
| P1 | +0 | 1E | `didChange` honored in-memory; no extra `didSave` |
| P2 | +20 | 1D | merge-rule sub-kind normalization in `multi_server.py` |
| P3 | +0 | — | Python 3.10–3.13 supported; no version-pin fallback |
| P3a | +0 | 1H | baseline established under Q3 pin |
| P4 (rel-info) | +15 | 1E | `related_locations: list[Location]` on `severity_breakdown` |
| P4 (pull-mode) | +30 | 1E | `BasedpyrightServer` calls `textDocument/diagnostic` after every didOpen/didChange/didSave |
| P4 (req auto-resp) | +25 | 1E | basedpyright server→client request handler (`workspace/configuration`, `client/registerCapability`, `window/workDoneProgress/create`) |
| P5a | **-135** | 1E | budgeted Q1 plumbing (`python_strategy.py` + `multi_server.py` synthetic-didSave) NO LONGER NEEDED — pylsp-mypy dropped |
| P6 | +30–40 | 1D | merger normalization for whole-file vs surgical edit reconciliation |
| P-WB | +0 | 1A | path-filter shape adopted verbatim |

**Total estimated remediation:** ~+145 to +200 LoC (depending on chosen P4 / P6 implementation depth, accounting for the −135 LoC reclaimed by dropping pylsp-mypy).

**Within the +250 LoC plan budget.**

---

## 5. Critical wrapper-gap findings (consolidated)

These are the gaps in the `vendor/serena` fork's `SolidLanguageServer` API surface discovered during Phase 0. Each has a Stage assignment so nothing falls through.

- **No `request_code_actions` / `resolve_code_action` / `execute_command` facade on `SolidLanguageServer`** (S3, S4, S5, S6) → **Stage 1A**: add facade methods (~+20 LoC; `LanguageServerRequest` already implements them, so this is a thin wrapper layer).
- **`$/progress` notification dispatcher is single-callback-per-method with `do_nothing` clobber** at `rust_analyzer.py:720` (S1) → **Stage 1A**: notification-tap shim, ~+30 LoC.
- **No capability-override hook on `SolidLanguageServer` / `RustAnalyzer`** — fork hard-codes `experimental.snippetTextEdit: True` at `rust_analyzer.py:458` (S2) → **Stage 1A**: add `LanguageStrategy.override_initialize_params(params) -> params` per-language hook, ~+15 LoC.
- **`Language.PYTHON` resolves to PyrightServer (`ls_config.py:346`), NOT pylsp** (P1, P2, P3, P4, P5a, P6) → **Stage 1E**: add `PylspServer(SolidLanguageServer)` adapter (~+50 LoC, template `jedi_server.py`); add `BasedpyrightServer(SolidLanguageServer)` adapter (~+50 LoC); add `RuffServer(SolidLanguageServer)` adapter (~+50 LoC).
- **No `notify_did_change_configuration` facade** (P5a) → **Stage 1E**: add to `PylspServer` adapter (recorded for completeness; pylsp-mypy is dropped, but pylsp-rope/pylsp-ruff config may need this in v1.1).
- **basedpyright 1.39.3 is PULL-mode only** (P4) → **Stage 1E**: `BasedpyrightServer` adapter calls `textDocument/diagnostic` after each didOpen/didChange/didSave; standard `publishDiagnostics`-listening pattern returns 0 diagnostics.
- **basedpyright BLOCKS on server→client requests** (P4) → **Stage 1E**: auto-responder for `workspace/configuration` (→ `[{} for _ in items]`), `client/registerCapability` (→ `null`), `window/workDoneProgress/create` (→ `null`).
- **Submodule pre-commit hook + git-flow pattern** (T6+) → operational; recorded in PROGRESS.md decisions log. Canonical pattern: feature branch in submodule → ff-merge to main → bump parent submodule pointer.

---

## 6. Cross-cutting decisions

- **pylsp-mypy: DROPPED from MVP** per Q1 §6.3 fallback / §11.1. Active Python LSP set at MVP: pylsp (with pylsp-rope) + basedpyright + ruff.
- **pylsp-rope organize-imports: DROPPED at merge time** per §11.1; ruff wins. v1.1 `engine: {ruff, rope}` config knob deferred.
- **rust-analyzer custom commands (`experimental/ssr`, `rust-analyzer/expandMacro`): UNAVAILABLE on stock 1.95.0**; gate `scalpel_rust_ssr` and `scalpel_rust_expand_macro` facades behind a shared runtime capability probe in Stage 1B (`_method_supported(command: str) -> bool`).
- **Workspace boundary rule**: 5/5 cases pass; adopt `is_in_workspace()` verbatim in Stage 1A applier per Q4 §7.1.
- **Stage 1A `applyEdit` handler: CAPTURE the WorkspaceEdit, not merely ACK** (S3 minimal-stub upgraded by P1 finding) — pylsp-rope ships its inline/refactor results via `workspace/applyEdit` reverse-request, not via `executeCommand` return.
- **Code-action flow MUST resolve before classifying**: rust-analyzer is deferred-resolution (top-level response carries `{title, kind, data, group?}` only; `command`/`edit` populate after `codeAction/resolve`); pylsp-rope is direct command-typed (no resolve needed). Stage 1A code-action facade supports both styles.

---

## 7. Stage 1 entry decision

- All 5 blocking spikes (S1, S3, P1, P2, P5a) produced actionable evidence: **YES**.
- LoC budget within +250 LoC: **YES** (estimated +145 to +200 LoC).
- All wrapper-gap findings have a Stage assignment: **YES** (Stage 1A, 1B, 1D, 1E, 1H — see §5).
- **Verdict: PROCEED to Stage 1A.**

---

## 8. References

- Original plan: [`docs/superpowers/plans/2026-04-24-phase-0-pre-mvp-spikes.md`](../2026-04-24-phase-0-pre-mvp-spikes.md)
- MVP scope report (§13 falsifier matrix; §11.1 priority tables): [`docs/design/mvp/2026-04-24-mvp-scope-report.md`](../../design/mvp/2026-04-24-mvp-scope-report.md)
- Q1 / Q3 / Q4 resolutions feeding P5a / P3a / P-WB: [`docs/design/mvp/open-questions/`](../../design/mvp/open-questions/)
- Per-spike outcome docs: this directory (`S1.md`, `S2.md`, `S3.md`, `S4.md`, `S5.md`, `S6.md`, `P1.md`, `P2.md`, `P3.md`, `P3a.md`, `P4.md`, `P5a.md`, `P6.md`, `P-WB.md`)
- Durable cross-context ledger: [`PROGRESS.md`](./PROGRESS.md)
