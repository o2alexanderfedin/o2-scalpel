# o2.scalpel — MVP Scope Report (v2: Full LSP Coverage)

> **Status (2026-04-27):** Headline numbers in this report are stale. As of `stage-v0.2.0-followups-complete`, the registry shows **8 primitives + 25 facades = 33 always-on tools** (was 13 + 11 at draft). For current state see `docs/gap-analysis/WHAT-REMAINS.md`. The historical record below is preserved unchanged.

Status: report-only. Authoritative MVP scope synthesized from the four full-coverage specialist brainstorms plus the main design and the open-questions resolution. **Supersedes** the narrow v1 synthesis at [`archive-v1-narrow/2026-04-24-mvp-scope-report.md`](archive-v1-narrow/2026-04-24-mvp-scope-report.md) on every disagreement.

Date: 2026-04-24. Author: AI Hive(R).

Cross-reference:
- Main design: [`../2026-04-24-serena-rust-refactoring-extensions-design.md`](../2026-04-24-serena-rust-refactoring-extensions-design.md).
- Open-questions resolution: [`../2026-04-24-o2-scalpel-open-questions-resolution.md`](../2026-04-24-o2-scalpel-open-questions-resolution.md).
- Full-coverage specialist reports: [`specialist-rust.md`](specialist-rust.md), [`specialist-python.md`](specialist-python.md), [`specialist-agent-ux.md`](specialist-agent-ux.md), [`specialist-scope.md`](specialist-scope.md).
- Archived narrow synthesis: [`archive-v1-narrow/2026-04-24-mvp-scope-report.md`](archive-v1-narrow/2026-04-24-mvp-scope-report.md).

---

## 1. TL;DR

o2.scalpel MVP under the **full-coverage directive** ships a language-agnostic MCP write surface for **Rust + Python simultaneously** in which every assist family of the chosen LSPs is reachable from any Claude Code session. The canonical surface is **13 always-on MCP tools** plus **~11 deferred-loading specialty facades** advertised via Anthropic's `defer_loading: true` mechanism (24 tools total at MVP; only the 13 burn cold context). Tools follow the `scalpel_<area>_<verb>` naming convention. The 13th always-on tool is `scalpel_transaction_commit`, promoted from a dispatcher payload to a sibling of `scalpel_dry_run_compose` / `scalpel_transaction_rollback` per [Q2 resolution](open-questions/q2-12-vs-13-tools.md). Every published rust-analyzer assist (158, in 12 families) is reachable — ~93 via facades, ~50 via the long-tail dispatcher (`scalpel_apply_capability`), 1 (`term_search`) via the primitive escape hatch. All ~52 LSP protocol methods rust-analyzer advertises are wired. 8 of 36 rust-analyzer custom extensions are first-class facades; 27 are reachable via typed pass-through; 1 (`experimental/onEnter`) is explicit-blocked. Every Rope refactor (9 via pylsp-rope commands, 10 via library bridge), every basedpyright code action, and every ruff `source.*` action is reachable. Python LSPs are pinned exact (`basedpyright==1.39.3` plus the rest of the Python stack — see [Q3 resolution](open-questions/q3-basedpyright-pinning.md)). Confirmation flow for unsafe operations (out-of-workspace edits, etc.) reuses **Claude Code's standard tool-permission prompt** rather than an in-band scalpel UI: scalpel exposes unsafe behaviors as explicit boolean facade arguments (`allow_out_of_workspace`, etc.) so the harness's "Allow / Allow always / Deny" UI fires automatically — see §11.9.

MVP cut line is **Stage 1 + Stage 2** (full primitive reach + capability catalog + rollback + 5 ergonomic facades for split / extract / inline / rename / fix-imports). Stage 3 (the remaining 7 ergonomic facades + 6 long-tail E2E scenarios) becomes `v0.2.0` and ships immediately after MVP. Resource floor commits **24 GB recommended** dev laptop with `O2_SCALPEL_DISABLE_LANGS` opt-out for 16 GB hosts. Distribution at MVP is `uvx --from <local-path>`; marketplace publication remains v1.1 work for stronger reasons under full coverage than under the narrow round. Total LoC (logic + fixtures + tests): ~17,600 at MVP cut, ~27,100 fully-loaded (3.1× the narrow MVP). 9 E2E scenarios block MVP; the other 6 ship in v0.2.0.

---

## 2. MVP Definition (single falsifiable sentence)

> **Scalpel MVP is done when (a) `scalpel_capabilities_list` returns a JSON catalog whose entries are byte-equal to the checked-in baseline and cover every rust-analyzer assist family + every Rope refactor + every basedpyright/ruff code action; (b) one passing integration test exists per assist family (~31 sub-tests across 32 modules) and one passing unit test exists per WorkspaceEdit shape × option permutation (~80 tests against the applier); (c) the 5 ergonomic facades (`scalpel_split_file`, `scalpel_extract`, `scalpel_inline`, `scalpel_rename`, `scalpel_imports_organize`) plus the 7 catalog/safety/diagnostics/transaction tools (incl. `scalpel_transaction_commit`) plus `scalpel_apply_capability` are reachable from a Claude Code session via `uvx --from <local-path>`; (d) the 9 MVP E2E scenarios pass on `calcrs` + `calcpy` + their companion fixtures with zero flakes in a single CI run on a 24 GB dev laptop.**

Falsifiable on six axes:

1. **Coverage.** The capability catalog round-trips; every catalog row has a passing integration test.
2. **Reachability.** Long-tail dispatcher `scalpel_apply_capability` reaches every assist not facaded.
3. **Ergonomics.** 5 ergonomic facades green on their dedicated E2E scenarios.
4. **Safety.** Single-checkpoint and transaction rollback both green; diagnostics-delta gating fires; no partially-applied refactor survives a failure.
5. **Distribution.** `uvx --from <local-path>` install on a clean 24 GB laptop with no PyPI / marketplace dependency.
6. **Resource floor.** All four scalpel LSP processes (rust-analyzer, pylsp, basedpyright, ruff) co-resident; aggregated scalpel RSS under 8 GB on the fixture set.

If any axis fails, MVP is not done. If all six pass, MVP is done regardless of unfinished v0.2.0 / v1.1 items.

---

## 3. Directive change record

The first round (archived at [`archive-v1-narrow/`](archive-v1-narrow/)) cut depth aggressively: 4 MCP tools (`split_file`, `fix_imports`, `rollback`, `apply_code_action`); ~5,640 LoC; 2 LSP processes scalpel-side; 7 E2E scenarios; 16 GB RAM floor; pylsp + pyright (read-only secondary). The narrow round's logic was: depth, not breadth — Rust + Python paper-validated against a single ergonomic facade so the abstraction wasn't designed around Rust's shape, with the long tail explicitly v1.1.

The user reversed that compression on **2026-04-24**: *"For the LSPs we choose, we must fully support the LSP's features."* Languages remain Rust + Python (top priority). What changed:

| Axis | Narrow v1 | Full-coverage v2 (this report) |
|---|---|---|
| Tool surface (LLM-visible) | 4 always-on | 13 always-on + ~11 deferred = 24 |
| LSP capabilities reachable | ~10 (just enough for 3 facades) | 158 RA assists + 18 Python ops + 36 RA extensions = ~210 |
| LSP processes (scalpel-side) | 2 (rust-analyzer + pyright) | 4 (rust-analyzer + pylsp + basedpyright + ruff) |
| Ergonomic facades at MVP | 3 | 5 (Stage 2) + 11 deferred specialty + 7 (Stage 3 = v0.2.0) |
| E2E scenarios at MVP | 7 | 9 |
| Integration tests | ~10 | ~31 (one per assist family) |
| Unit tests | ~30 | ~120 (incl. ~80 WorkspaceEdit shape × option) |
| RAM floor | 16 GB | 24 GB recommended; 16 GB with `O2_SCALPEL_DISABLE_LANGS` |
| Logic + fixtures + tests | ~5,640 LoC | ~17,600 LoC at MVP cut (3.1×) |
| Fully loaded | ~8,665 LoC | ~27,100 LoC |
| Distribution at MVP | `uvx --from <path>` | unchanged |

What the inversion **buys**: a tool surface that genuinely matches the LSP it wraps. No "this rust-analyzer feature isn't reachable through scalpel" apologies. No silent capability gaps. The directive's promise — "every assist reachable, every WorkspaceEdit shape applied, every advertised method wired" — is honored modulo one explicit-blocked editor-only method (`experimental/onEnter`, §6.9).

What the inversion **costs**: 3.1× LoC; 2× LSP process count; the multi-LSP coordination protocol (§11) that the narrow round did not need; ~3× test surface; 50% higher RAM floor on the recommended-tier; a more disciplined cut between always-on and deferred tool surface (§5) than the narrow round needed. The distribution and resource-degradation paths are not changed; the marketplace decision (v1.1) is reaffirmed for stronger reasons (§14).

The narrow synthesis is preserved as the rollback target: if telemetry post-MVP shows the 13-tool surface degrades LLM accuracy below the narrow round's measured baseline, we can revert to the 4-tool surface without re-architecting the underlying solidlsp / strategy / facade plumbing — those layers are common to both rounds.

**2026-04-24 (later) — second-round resolutions and confirmation-flow directive.** Four §19 open questions resolved (Q1–Q4; see [`open-questions/`](open-questions/)). After the Q4 specialist completed, the user issued an additional directive: *"confirmations should work the same way as all claude cli confirmations, if possible."* This means scalpel must NOT invent its own in-band confirmation tool or UI; instead, unsafe operations are exposed as explicit boolean facade arguments (e.g., `allow_out_of_workspace`) so Claude Code's standard tool-permission prompt fires when the LLM tries to use them. See §11.9 for the canonical statement of the confirmation-flow contract.

---

## 4. In-Scope vs. Out-of-Scope matrix

Every design element, every LSP capability family, every WorkspaceEdit shape, every protocol method assigned to one of: **MVP-facade** (named ergonomic tool), **MVP-deferred** (named tool, `defer_loading: true`), **MVP-primitive** (reachable via `scalpel_apply_capability`), **v0.2.0** (Stage 3, ergonomic facade after MVP), **v1.1** (post-v0.2.0), **v2+** (genuinely optional), **explicit-block** (refused with documented rationale).

### 4.1 LSP primitive layer (`solidlsp`)

| Item | Stage | Driver |
|---|---|---|
| `request_code_actions(file, range, only?, trigger_kind, diagnostics?)` | MVP-primitive | Every facade routes through it |
| `resolve_code_action(action)` | MVP-primitive | Two-phase resolve, mandatory on rust-analyzer |
| `execute_command(method, params)` typed pass-through | MVP-primitive | pylsp-rope, ruff `source.fixAll`, basedpyright auto-import all use it |
| `workspace/applyEdit` reverse-request handler (full, not stub) | **MVP** | `experimental/ssr` and macro-expansion paths fire it (specialist-rust §S3) |
| `workspace/configuration` reverse handler | MVP | rust-analyzer queries us mid-session |
| `client/registerCapability` + `unregisterCapability` reverse handlers | MVP | rust-analyzer dynamically registers `workspace/didChangeWatchedFiles` |
| `window/showMessageRequest` reverse handler (auto-accept first non-destructive) | MVP-stub | RA "Reload workspace?" prompts |
| `window/workDoneProgress/create` reverse handler | MVP | Required because we advertise `progressSupport=true` |
| `workspace/semanticTokens/refresh` reverse handler | MVP | Cache-invalidation notification |
| `workspace/diagnostic/refresh` reverse handler | MVP | Required by diagnostics-delta gate |
| `$/progress` per-token tracker (`rustAnalyzer/Indexing`, `Building`, `Fetching`, `Cargo`, `Roots Scanned`; `pylsp:`, `basedpyright:`, `ruff:` prefixes) | MVP | Cold-start gate; flake risk otherwise |
| `wait_for_indexing(timeout_s)` | MVP | Every facade calls before first codeAction |
| WorkspaceEdit applier — `TextDocumentEdit` (basic, multi-edit, version-checked) | MVP | Every assist emits this |
| WorkspaceEdit applier — `CreateFile` (overwrite / ignoreIfExists permutations) | MVP | `move_module_to_file`, `extract_module` |
| WorkspaceEdit applier — `RenameFile` (overwrite / ignoreIfExists permutations) | MVP | `move_from_mod_rs`, Rope `MoveModule` |
| WorkspaceEdit applier — `DeleteFile` (recursive / ignoreIfNotExists permutations) | **MVP** | Rope `MoveGlobal` emits it (Python full-coverage requirement) |
| WorkspaceEdit applier — `changeAnnotations` map (needsConfirmation, description, label) | **MVP** | Surfaced in dry-run; advisory only. Safety enforced by §11 workspace-boundary path filter (Q4 resolution); rename-shadowing emits non-blocking `SemanticShiftWarning` |
| WorkspaceEdit applier — `SnippetTextEdit` `$N` marker stripping (defensive) | MVP | Even with `snippetTextEdit:false` advertised |
| WorkspaceEdit applier — order preservation, descending-offset, version mismatch reject | MVP | Correctness |
| WorkspaceEdit applier — atomic in-memory snapshot + restore on partial failure | MVP | Rollback contract |
| WorkspaceEdit applier — old-style `changes` map fallback | MVP | pylsp-rope sometimes emits it |
| WorkspaceEdit applier — multi-server transactional fan-in | MVP | Python multi-LSP path |
| WorkspaceEdit applier — Rope `ChangeSet` → WorkspaceEdit shim | MVP | Library-bridge ops |
| Checkpoint store — in-memory LRU (50 entries) | MVP | Single-checkpoint rollback |
| Transaction store — LRU (20 entries; evicting transaction evicts its checkpoints) | MVP | `scalpel_dry_run_compose` rollback |
| Inverse `WorkspaceEdit` computation (extended for DeleteFile) | MVP | Rollback mechanism |
| Persistent disk checkpoints under `.serena/checkpoints/` | v1.1 | LRU-only at MVP |
| `is_alive()` pre-checkout probe | MVP | Multi-LSP transparent respawn |
| Idle-shutdown after `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS` (default 600) | MVP | Per Q12 |
| `(language, project_root, server_id)` registry | MVP | Multi-LSP requires `server_id` axis |

### 4.2 rust-analyzer 158 assists × 12 families

| # | Family | Count | MVP-facade / MVP-deferred / MVP-primitive / v0.2.0 |
|---|---|---|---|
| A | Module / file boundary (`extract_module`, `move_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs`) | 4 | 2 facaded (`scalpel_split_file`, `scalpel_apply_capability` for `move_inline_module_to_file`); 2 v0.2.0 (`scalpel_rust_promote_inline_module` deferred, `convert_module_layout` Stage 3) |
| B | Extractors (`extract_function`, `extract_variable`, `extract_type_alias`, `extract_struct_from_enum_variant`, `promote_local_to_const`, etc.) | 8 | All reached via `scalpel_extract(target=...)`; `extract_struct_from_enum_variant` is `scalpel_rust_extract_struct_from_variant` (deferred) |
| C | Inliners (`inline_local_variable`, `inline_call`, `inline_into_callers`, `inline_type_alias`, `inline_macro`, `inline_const_as_literal`) | 5 | All reached via `scalpel_inline(target=..., scope=...)` |
| D | Imports (`auto_import`, `qualify_path`, `replace_qualified_name_with_use`, `remove_unused_imports`, `merge_imports`, `unmerge_imports`, `normalize_import`, `split_import`, `expand_glob_import`, `expand_glob_reexport`) | 10 | 8 reached via `scalpel_imports_organize`; 2 v0.2.0 (`expand_glob_imports` Stage 3 facade) |
| E | Visibility (`change_visibility`, `fix_visibility`) | 2 | `change_visibility` v0.2.0 facade; `fix_visibility` MVP-primitive (auto-fired by split pipeline) |
| F | Ordering (`reorder_impl_items`, `sort_items`, `reorder_fields`) | 3 | All MVP-primitive; v0.2.0 `tidy_structure` facade |
| G | Generators (`generate_*` family) | 32 | ~20 MVP-primitive; `scalpel_rust_impl_trait` deferred; v0.2.0 `generate_trait_impl_scaffold`, `generate_member` facades |
| H | Convert / rewrite (`convert_*`, `apply_*`, `replace_*`, `flip_*`, `wrap_*`, `unwrap_*`, etc.) | 40 | ~36 MVP-primitive; `scalpel_rust_match_to_iflet` deferred; v0.2.0 `change_type_shape`, `change_return_type` facades |
| I | Pattern / destructuring (`add_missing_match_arms`, `add_missing_impl_members`, `destructure_struct_binding`, etc.) | 5 | 2 MVP-primitive; v0.2.0 `complete_match_arms` facade |
| J | Lifetimes & references (`add_explicit_lifetime_to_self`, `extract_explicit_lifetime`, etc.) | 4 | 3 MVP-primitive; `scalpel_rust_lifetime_elide` deferred (covers `extract_explicit_lifetime`) |
| K | `term_search` synthesis | 1 | MVP-primitive only (no symbolic input — facade contract cannot be honored) |
| L | Quickfixes bound to diagnostics (`add_missing_semicolon`, `add_explicit_type`, `add_turbo_fish`, etc.) | ~30 | MVP-primitive via diagnostics-delta sweep + `scalpel_apply_capability` |

**Coverage check**: of 158, ~93 facaded (via 5 always-on + 6 v0.2.0 facades + 6 rust-only deferred), ~50 primitive-only (reachable via dispatcher), ~15 quickfix overlap. **No assist is silently unreachable**. `term_search` is documented as primitive-only.

### 4.3 rust-analyzer 36 custom extensions

| # | Extension | Verdict |
|---|---|---|
| 1 | `experimental/parentModule` | **MVP-facade** (`scalpel_workspace_health` + internal `plan_file_split`); also MVP-primitive |
| 2 | `experimental/joinLines` | MVP-primitive |
| 3 | `experimental/onEnter` | **explicit-block** — editor-keystroke semantics, snippet escape (§6.9) |
| 4 | `experimental/matchingBrace` | MVP-primitive |
| 5 | `experimental/ssr` | **MVP-deferred** facade (`scalpel_rust_ssr` deferred); reachable via dispatcher |
| 6 | `experimental/runnables` | MVP-primitive (composed by `verify_after_refactor` v0.2.0) |
| 7 | `experimental/externalDocs` | MVP-primitive |
| 8 | `experimental/openCargoToml` | MVP-primitive |
| 9 | `experimental/moveItem` | MVP-primitive |
| 10 | `experimental/serverStatus` (notification) | **MVP-facade** internal — surfaces via `scalpel_workspace_health` |
| 11–17 | `experimental/discoverTest` family (7 methods) | **v1.1** (Test Explorer surface; LLM uses `relatedTests`+`runFlycheck` instead) |
| 18 | `rust-analyzer/analyzerStatus` | MVP-primitive |
| 19 | `rust-analyzer/reloadWorkspace` | MVP-primitive |
| 20 | `rust-analyzer/rebuildProcMacros` | MVP-primitive |
| 21 | `rust-analyzer/runFlycheck` | **MVP-facade** internal — `scalpel_workspace_health` surfaces; v0.2.0 dedicated facade `run_flycheck` |
| 22 | `rust-analyzer/cancelFlycheck` | MVP-primitive |
| 23 | `rust-analyzer/clearFlycheck` | MVP-primitive |
| 24 | `rust-analyzer/viewSyntaxTree` | MVP-primitive (debug; reachable, unsurfaced) |
| 25 | `rust-analyzer/viewHir` | MVP-primitive |
| 26 | `rust-analyzer/viewMir` | MVP-primitive |
| 27 | `rust-analyzer/viewFileText` | MVP-primitive |
| 28 | `rust-analyzer/viewItemTree` | MVP-primitive (used internally by `plan_file_split`) |
| 29 | `rust-analyzer/viewCrateGraph` | MVP-primitive (SVG; reachable, unsurfaced) |
| 30 | `rust-analyzer/expandMacro` | MVP-primitive (v0.2.0 facade `expand_macro`) |
| 31 | `rust-analyzer/relatedTests` | MVP-primitive |
| 32 | `rust-analyzer/fetchDependencyList` | MVP-primitive |
| 33 | `rust-analyzer/viewRecursiveMemoryLayout` | MVP-primitive |
| 34 | `rust-analyzer/getFailedObligations` | MVP-primitive |
| 35 | `rust-analyzer/interpretFunction` | MVP-primitive |
| 36 | `rust-analyzer/childModules` | MVP-primitive |

**8 first-class** (parentModule via `scalpel_workspace_health` + internal facades, serverStatus, ssr deferred, runFlycheck via diagnostics, expandMacro v0.2.0, runnables/relatedTests via verify v0.2.0, reloadWorkspace+rebuildProcMacros via diagnostics, viewItemTree internal). **27 typed pass-through** via `scalpel_apply_capability` + `scalpel_execute_command` (deferred). **1 explicit-block**: `experimental/onEnter`.

### 4.4 Python LSP capabilities

#### 4.4.1 pylsp-rope command surface (9 commands + 10 library-only ops)

| # | Op | Source | Stage |
|---|---|---|---|
| 1 | `pylsp_rope.refactor.extract.method` | pylsp-rope | MVP-facade (`scalpel_extract(target="function")`) |
| 2 | `pylsp_rope.refactor.extract.variable` | pylsp-rope | MVP-facade (`scalpel_extract(target="variable")`) |
| 3 | `pylsp_rope.refactor.inline` | pylsp-rope | MVP-facade (`scalpel_inline`) |
| 4 | `pylsp_rope.refactor.local_to_field` | pylsp-rope | MVP-primitive (v0.2.0 facade `local_to_field`) |
| 5 | `pylsp_rope.refactor.method_to_method_object` | pylsp-rope | MVP-primitive (v0.2.0 facade `convert_to_method_object`) |
| 6 | `pylsp_rope.refactor.use_function` | pylsp-rope | MVP-primitive (v0.2.0 `use_function`) |
| 7 | `pylsp_rope.refactor.introduce_parameter` | pylsp-rope | MVP-primitive (v0.2.0 `introduce_parameter`) |
| 8 | `pylsp_rope.quickfix.generate` | pylsp-rope | MVP-primitive (v0.2.0 `generate_from_undefined`) |
| 9 | `pylsp_rope.source.organize_import` | pylsp-rope | MVP-facade (`scalpel_imports_organize(engine="rope")`) |
| 10 | `rope.refactor.move.MoveGlobal` | library bridge | MVP-facade (composed in `scalpel_split_file`) |
| 11 | `rope.refactor.move.MoveModule` | library bridge | MVP-facade (`scalpel_rename` on module URI) |
| 12 | `rope.refactor.move.MoveMethod` | library bridge | v1.1 (`move_method`) |
| 13 | `rope.refactor.change_signature.ChangeSignature` | library bridge | v1.1 |
| 14 | `rope.refactor.encapsulate_field.EncapsulateField` | library bridge | v1.1 |
| 15 | `rope.refactor.introduce_factory.IntroduceFactory` | library bridge | v1.1 |
| 16 | `rope.refactor.restructure.Restructure` | library bridge | v1.1 (pass-through; powerful and unsafe) |
| 17 | `rope.refactor.importutils.relative_to_absolute` / `froms_to_imports` / `expand_stars` / `handle_long_imports` | library bridge | v1.1 (`convert_imports`, `expand_star_imports`) |

#### 4.4.2 basedpyright code-action surface

| # | Action kind | Stage |
|---|---|---|
| 1 | `source.organizeImports` | MVP-facade (consumed by `scalpel_imports_organize`; ruff wins by default) |
| 2 | `quickfix` (auto-import on `reportUndefinedVariable`) | MVP-facade (`scalpel_imports_organize(...)` and merge rule §11) |
| 3 | `quickfix` (`# pyright: ignore[<rule>]` insertion) | MVP-primitive (v0.2.0 `ignore_diagnostic(tool="pyright")`) |
| 4 | `quickfix` (annotate type from inferred) | MVP-primitive (`scalpel_py_type_annotate` deferred) |
| 5 | basedpyright commands (`organizeImports`, `restartServer`, `writeBaseline`, `addOptionalForParam`, `createTypeStub`) | MVP-primitive via dispatcher |

#### 4.4.3 ruff server code-action surface

| # | Action kind | Stage |
|---|---|---|
| 1 | `source.fixAll.ruff` | MVP-facade (v0.2.0 `fix_lints`); MVP via `scalpel_apply_capability` |
| 2 | per-rule `quickfix.ruff.<RULE>` | MVP-primitive |
| 3 | `source.organizeImports.ruff` | MVP-facade (consumed by `scalpel_imports_organize`) |

### 4.5 LSP protocol method roster (~52 wired)

| Group | Count | Status |
|---|---|---|
| Lifecycle / negotiation (`initialize`, `shutdown`, `$/setTrace`, `$/cancelRequest`, `$/progress`, `client/registerCapability`, `client/unregisterCapability`, `window/showMessage`, `window/logMessage`, `window/showMessageRequest` (stubbed), `window/workDoneProgress/create`, `window/workDoneProgress/cancel`) | 12 | full / 1 stubbed |
| Document sync (`didOpen`, `didChange`, `didClose`, `didSave`, `workspace/didChangeWatchedFiles`) | 5 | full |
| Read-only language features (`definition`, `declaration`, `typeDefinition`, `implementation`, `references`, `hover`, `documentSymbol`, `workspace/symbol`, `foldingRange`, `selectionRange`, `documentHighlight`, `inlayHint`, `semanticTokens/{full,range,full/delta}`, `workspace/semanticTokens/refresh`) | ~16 | full |
| Editing (`codeAction`, `codeAction/resolve`, `rename`, `prepareRename`, `formatting`, `rangeFormatting`, `completion`, `completionItem/resolve`, `signatureHelp`, `callHierarchy/{prepareCallHierarchy,incomingCalls,outgoingCalls}`) | ~12 | full |
| Workspace ops (`applyEdit`, `willRenameFiles`, `didRenameFiles`, `executeCommand`, `configuration`, `didChangeConfiguration`, `diagnostic/refresh`) | 7 | full |
| Diagnostics (`publishDiagnostics`) | 1 | full |
| **Total wired** | ~52 | |
| `willSave`, `willSaveWaitUntil`, `onTypeFormatting`, `willCreateFiles`, `willDeleteFiles`, `didCreateFiles`, `didDeleteFiles`, pull `diagnostic` | ~8 | not wired (rust-analyzer doesn't advertise; future strategies may) |

### 4.6 WorkspaceEdit shape × option matrix

| Variant | Tested? | Test count |
|---|---|---|
| `TextDocumentEdit` basic | yes | 4 (basic, multi-edit, version-valid/stale/null) |
| `TextDocumentEdit` with `SnippetTextEdit` `$N` markers | yes | 4 (with `snippetTextEdit:false`, with strip path, inside-string-literal safe, escape-strip basic) |
| `CreateFile` × `overwrite` × `ignoreIfExists` | yes | 4 |
| `RenameFile` × `overwrite` × `ignoreIfExists` × target-exists matrix | yes | 6 |
| `DeleteFile` × `recursive` × `ignoreIfNotExists` | yes | 4 |
| `changeAnnotations` × `needsConfirmation` × `description` × `label` | yes | 4 |
| Old-style `changes` map fallback (Python) | yes | 2 |
| Ordering: `documentChanges` array order, descending-offset within edit, CreateFile-before-TextEdit, no-double-write | yes | 4 |
| Atomicity: rollback-on-partial-failure, version-mismatch-rejects-entire-edit, multi-server fan-in atomicity | yes | 6 |
| **Total applier matrix** | | **~80 unit tests** |

### 4.7 Out-of-scope canonical list (merged from all four specialists)

| # | Cut | v0.2.0 / v1.1 / v2+ / explicit-block |
|---|---|---|
| 1 | TypeScript / Go / clangd / Java strategies | v2+ (paper-only at MVP per OQ #7) |
| 2 | `experimental/onEnter` | explicit-block (§6.9) |
| 3 | rust-analyzer Test Explorer family (7 methods) | v1.1 |
| 4 | `viewHir`, `viewMir`, `viewCrateGraph`, `viewSyntaxTree`, `viewFileText`, `viewRecursiveMemoryLayout`, `getFailedObligations`, `interpretFunction` first-class facades | reachable but unsurfaced (MVP-primitive) |
| 5 | Stage 3 ergonomic facades — `convert_module_layout`, `change_visibility` (Rust), `tidy_structure`, `change_type_shape`, `change_return_type`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `extract_struct_from_enum_variant` (split out), `generate_trait_impl_scaffold`, `generate_member`, `expand_macro` | v0.2.0 |
| 6 | Python facades — `move_method`, `change_signature`, `introduce_factory`, `encapsulate_field`, `annotate_return_type`, `convert_to_async`, `convert_imports`, `expand_star_imports`, `restructure` | v1.1 |
| 7 | `verify_after_refactor` composite (runnables + relatedTests + flycheck) | v0.2.0 |
| 8 | Persistent disk checkpoints `.serena/checkpoints/` durability | v1.1 |
| 9 | Filesystem watcher on plugin cache | explicit-reject (Q10) |
| 10 | `o2-scalpel-newplugin` template generator | v2+ (Q14) |
| 11 | Reference LSP-config plugins (`rust-analyzer-reference`, `clangd-reference`) | v2+ |
| 12 | Marketplace publication at `o2alexanderfedin/claude-code-plugins` | v1.1 (§14) |
| 13 | Boostvolt fork under neutral name | v2+ |
| 14 | Vendor-exclusion CI guard for Piebald content | v1.1 |
| 15 | `verify-scalpel.sh` SessionStart hook | v1.1 |
| 16 | `scalpel_reload_plugins` MCP tool | v1.1 |
| 17 | Multi-interpreter monorepo subtrees (Python) | v1.1 |
| 18 | Notebook (`.ipynb`) refactor (warn-only at MVP) | v2+ |
| 19 | Cython / `.pyx` refactor | v2+ |
| 20 | LSP 3.18 features (typeHierarchy, etc.) | v2+ |
| 21 | Pull diagnostics (`textDocument/diagnostic`) | v2+ (rust-analyzer doesn't advertise) |
| 22 | Edition 2024 / PEP 695 / PEP 701 fixture variants | v1.1 (gated by spike S5 / spike 10.3 outcomes) |
| 23 | Multi-crate / multi-package E2E (E5) | v0.2.0 (nightly) |
| 24 | Crate-wide `fix_imports(files=["**"])` glob | v0.2.0 (E6 nightly) |
| 25 | rust-analyzer cold-start E2E on 200+ crate workspace (E7) | v0.2.0 |
| 26 | Crash-recovery E2E (E8) | v0.2.0 |
| 27 | Idle-shutdown tuning UI | v1.1 |
| 28 | Streaming test output for `verify_after_refactor` | v1.1 |
| 29 | Sub-expression range modes for `extract_expression` | v1.1 |
| 30 | `plan_file_split` strategies `by_visibility`, `by_type_affinity` | v1.1 (only `by_cluster` ships at MVP) |
| 31 | `parent_module_style="mod_rs"` first-class flag | v0.2.0 (Stage 3 `convert_module_layout` covers post-split) |
| 32 | `reexport_policy="explicit_list"` advanced flag | v1.1 |
| 33 | Telemetry / observability beyond `lsp_ops: list[LspOpStat]` | v1.1 (telemetry framework exists; aggregation pipeline post-MVP) |

---

## 5. Canonical MVP Tool Surface

### 5.1 The 13 always-on tools

All names follow `scalpel_<area>_<verb>`. All docstrings ≤ 30 words. All accept an optional `language: Literal["rust", "python"] | None = None` parameter; `None` = infer from file extension. Returns the cross-language `RefactorResult` schema (§10) unless noted. The 13th tool (`scalpel_transaction_commit`) was promoted from a dispatcher payload per [Q2 resolution](open-questions/q2-12-vs-13-tools.md): routing a *core grammar verb* through `scalpel_apply_capability` violated the dispatcher's "long-tail" contract and forced the LLM to reproduce a magic-string `capability_id` byte-exact (the dominant hallucination failure mode per MCP-Zero's measured 23-point accuracy gap). Several facades expose explicit unsafe-operation boolean arguments (e.g., `allow_out_of_workspace`) — these are the trigger for Claude Code's standard tool-permission prompt; see §11.9.

```python
# ----- 5 ergonomic intent facades --------------------------------------

def scalpel_split_file(
    file: str,
    groups: dict[str, list[str]],
    parent_layout: Literal["package", "file"] = "package",
    keep_in_original: list[str] = [],
    reexport_policy: Literal["preserve_public_api", "none", "explicit_list"] = "preserve_public_api",
    explicit_reexports: list[str] = [],
    allow_partial: bool = False,
    dry_run: bool = False,
    preview_token: str | None = None,
    language: Literal["rust", "python"] | None = None,
) -> RefactorResult:
    """Split a source file into N modules by moving named symbols.
    Returns diff + diagnostics_delta + preview_token. Atomic."""

def scalpel_extract(
    file: str,
    range: Range | None = None,
    name_path: str | None = None,
    target: Literal["variable", "function", "constant", "static", "type_alias", "module"] = "function",
    new_name: str = "extracted",
    visibility: Literal["private", "pub_crate", "pub"] = "private",
    similar: bool = False,
    global_scope: bool = False,
    dry_run: bool = False,
    preview_token: str | None = None,
    language: Literal["rust", "python"] | None = None,
) -> RefactorResult:
    """Extract a symbol or selection into a new variable, function, module,
    or type. Pick `target` to choose. Atomic."""

def scalpel_inline(
    file: str,
    name_path: str | None = None,
    position: Position | None = None,
    target: Literal["call", "variable", "type_alias", "macro", "const"] = "call",
    scope: Literal["single_call_site", "all_callers"] = "single_call_site",
    remove_definition: bool = True,
    dry_run: bool = False,
    preview_token: str | None = None,
    language: Literal["rust", "python"] | None = None,
) -> RefactorResult:
    """Inline a function, variable, or type alias at its definition or
    all call-sites. Pick `target`. Atomic."""

def scalpel_rename(
    file: str,
    name_path: str,
    new_name: str,
    also_in_strings: bool = False,
    dry_run: bool = False,
    preview_token: str | None = None,
    language: Literal["rust", "python"] | None = None,
) -> RefactorResult:
    """Rename a symbol everywhere it is referenced. Cross-file.
    Returns checkpoint_id. Hallucination-resistant on name-paths."""

def scalpel_imports_organize(
    files: list[str],
    add_missing: bool = True,
    remove_unused: bool = True,
    reorder: bool = True,
    engine: Literal["auto", "rope", "ruff", "basedpyright"] = "auto",
    dry_run: bool = False,
    preview_token: str | None = None,
    language: Literal["rust", "python"] | None = None,
) -> RefactorResult:
    """Add missing, remove unused, reorder imports across files.
    Idempotent; safe to re-call."""

# ----- 1 long-tail dispatcher ------------------------------------------

def scalpel_apply_capability(
    capability_id: str,
    file: str,
    range_or_name_path: Range | str,
    params: dict = {},
    dry_run: bool = False,
    preview_token: str | None = None,
    allow_out_of_workspace: bool = False,
) -> RefactorResult:
    """Apply any registered capability by capability_id from
    capabilities_list. The long-tail dispatcher. Atomic. Set
    allow_out_of_workspace=True only with user permission."""

# ----- 2 catalog tools -------------------------------------------------

def scalpel_capabilities_list(
    language: Literal["rust", "python"] | None = None,
    filter_kind: str | None = None,
    applies_to_symbol_kind: str | None = None,
) -> list[CapabilityDescriptor]:
    """List capabilities for a language with optional filter. Returns
    capability_id + title + applies_to_kinds + preferred_facade."""

def scalpel_capability_describe(
    capability_id: str,
) -> CapabilityFullDescriptor:
    """Return full schema, examples, and pre-conditions for one
    capability_id. Call before invoking unknown capabilities."""

# ----- 1 dry-run composer ----------------------------------------------

def scalpel_dry_run_compose(
    steps: list[ComposeStep],
    fail_fast: bool = True,
) -> ComposeResult:
    """Preview a chain of refactor steps without committing any.
    Returns transaction_id; call scalpel_transaction_commit to apply."""

# ----- 3 transaction-grammar tools (commit + 2 rollback) ----------------

def scalpel_transaction_commit(
    transaction_id: str,
) -> TransactionResult:
    """Commit a previewed transaction from dry_run_compose. Applies all
    steps atomically, captures one checkpoint per step. Idempotent."""

def scalpel_rollback(
    checkpoint_id: str,
) -> RefactorResult:
    """Undo a refactor by checkpoint_id. Idempotent: second call is no-op."""

def scalpel_transaction_rollback(
    transaction_id: str,
) -> TransactionResult:
    """Undo all checkpoints in a transaction (from dry_run_compose) in
    reverse order. Idempotent."""

# ----- 1 diagnostics tool ----------------------------------------------

def scalpel_workspace_health(
    project_root: str | None = None,
) -> WorkspaceHealth:
    """Probe LSP servers: indexing state, registered capabilities, version.
    Call before refactor sessions."""
```

### 5.2 The ~11 deferred-loading specialty tools (`defer_loading: true`)

Registered with `defer_loading: true`; advertised by `scalpel_capabilities_list` with `preferred_facade` set to the deferred tool name. The LLM finds them via Anthropic Tool Search. Cold context cost is **0 tokens** until search retrieves them.

| Name | Language | Docstring (≤30 words) | Priority |
|---|---|---|---|
| `scalpel_rust_lifetime_elide` | rust | Apply rust-analyzer's lifetime elision/explicit assists to a function signature. Atomic. | P1 |
| `scalpel_rust_impl_trait` | rust | Generate a missing impl Trait for a type via rust-analyzer's add-missing-impl-members assist. | P1 |
| `scalpel_rust_promote_inline_module` | rust | Promote `mod foo {…}` to `foo.rs`. Rust-only equivalent of split. | P1 |
| `scalpel_rust_extract_struct_from_variant` | rust | Pull data of an enum variant out into a named struct. | P2 |
| `scalpel_rust_match_to_iflet` | rust | Convert match ↔ if let chains. rust-analyzer rewrite kind. | P2 |
| `scalpel_rust_qualify_path` | rust | Qualify or unqualify a path. Useful before/after import organization. | P2 |
| `scalpel_rust_ssr` | rust | Structural search/replace via `experimental/ssr`. Bulk path rewrites. Atomic. | P1 |
| `scalpel_py_async_ify` | python | Convert a sync function and its propagated callsites to async. Pyright/ruff-driven. | P1 |
| `scalpel_py_type_annotate` | python | Add or refine type hints on a function/class via basedpyright inference. Idempotent. | P1 |
| `scalpel_py_dataclass_from_dict` | python | Convert a dict-shaped class or factory into a `@dataclass`. | P2 |
| `scalpel_py_promote_method_to_function` | python | Promote a method to a module-level function. | P2 |
| `scalpel_execute_command` | both | Server-specific JSON-RPC pass-through, whitelisted per LanguageStrategy. Power-user escape hatch. | P2 |

**Total surface: 13 always-on + ~11 deferred = ~24 tools.** Hot context cost is bounded by the always-on 13 (~14.2K tokens including Tool Search Tool itself; well under the 25K MCP-chatter pain point). The 13th tool's ~1K-token cold cost is justified per [Q2 resolution](open-questions/q2-12-vs-13-tools.md) — the transaction-grammar symmetry (`scalpel_dry_run_compose` / `scalpel_transaction_commit` / `scalpel_transaction_rollback`) and the elimination of the dispatcher-payload hallucination risk dominate.

### 5.3 Cluster prefix discipline (anti-collision)

| Cluster prefix | Tools | Notes |
|---|---|---|
| `scalpel_split_*` / `scalpel_extract` / `scalpel_inline` / `scalpel_rename` | high-frequency intent verbs | LLM reaches for verb first |
| `scalpel_imports_*` | `scalpel_imports_organize` | object-first cluster |
| `scalpel_capabilities_*` / `scalpel_capability_*` | `_list`, `_describe` | catalog cluster |
| `scalpel_dry_run_*` | `scalpel_dry_run_compose` | composer cluster |
| `scalpel_transaction_*` | `scalpel_transaction_commit`, `scalpel_transaction_rollback` | transaction-grammar cluster (commit + rollback siblings of dry_run_compose) |
| `scalpel_*rollback` | `scalpel_rollback`, `scalpel_transaction_rollback` | safety cluster (suffix) |
| `scalpel_workspace_*` | `scalpel_workspace_health` | diagnostics cluster |
| `scalpel_apply_*` | `scalpel_apply_capability` | unique dispatcher |
| `scalpel_rust_*`, `scalpel_py_*` | language-specialty deferred set | language prefix tells LLM to skip if file isn't this language |

Banned at always-on tier: `move`, `refactor`, `transform`, `update`, `fix`, `change`, `do`, `run` (over-broad invitation verbs). Anti-collision with Claude Code built-in `LSP` umbrella: never use `definition`, `references`, `hover`, `documentSymbol`, `completion`, `format` as scalpel tool names.

### 5.4 What the docstring can and cannot do

The 30-word docstring is *router signage*, not documentation. Three sentences: imperative verb + discriminator + contract bit (atomicity / idempotency / returns checkpoint_id). Depth lives in `scalpel_capability_describe` (the 1-shot lookup the LLM does when invoking unknown capabilities) and in the marketplace `SKILL.md`.

### 5.5 Compose / commit auxiliary schemas

```python
class ComposeStep(BaseModel):
    tool: str                  # e.g. "scalpel_split_file"
    args: dict                 # the tool's args, minus dry_run/preview_token

class StepPreview(BaseModel):
    step_index: int
    tool: str
    changes: list[FileChange]
    diagnostics_delta: DiagnosticsDelta
    failure: FailureInfo | None = None

class ComposeResult(BaseModel):
    transaction_id: str
    per_step: list[StepPreview]
    aggregated_changes: list[FileChange]    # post-all-steps shadow state
    aggregated_diagnostics_delta: DiagnosticsDelta
    expires_at: float                       # 5-min TTL
    warnings: list[str]
```

Compose semantics:

- **Virtual application.** Each step applies to an in-memory shadow workspace; on-disk files are not touched until commit.
- **Per-step diagnostics.** Each `StepPreview.diagnostics_delta` is computed against the shadow state of the *previous* step. The LLM sees how errors evolve across the chain.
- **Fail-fast (default).** First failing step ends compose with `TRANSACTION_ABORTED`. `fail_fast=False` continues and reports every step's outcome (read-only; commit is still all-or-nothing).
- **Commit.** `scalpel_transaction_commit(transaction_id=...)` applies all steps in order, captures one checkpoint per step bundled under one `transaction_id`. `scalpel_transaction_rollback(transaction_id)` undoes the chain in reverse step order. The legacy `scalpel_apply_capability(capability_id="scalpel.transaction.commit", ...)` path remains as a deprecated alias for one minor version (back-compat for any code paths still calling it); telemetry monitors for residual usage and the alias is removed in v0.2.0.
- **Invalidation.** Any external file change in the affected set invalidates the transaction → `PREVIEW_EXPIRED`.
- **No nested composes at MVP.** `steps[]` items must be regular tool calls, not other compose calls. v1.1 may relax.

### 5.6 Worked example — cross-language compose

A repo with `crates/foo/src/lib.rs` (Rust) and `services/api.py` (Python). User asks: *"factor `api.py`'s endpoint handlers into `services/api/handlers/`, and rename `lib.rs::Engine` to `Core` everywhere."*

```
turn 1: scalpel_workspace_health()
        → {languages: {rust: {indexing_state: ready}, python: {indexing_state: ready}}}

turn 2: scalpel_dry_run_compose(steps=[
          {tool: "scalpel_split_file",
           args: {file: "services/api.py",
                  groups: {"handlers": ["users","orders","admin"]}}},
          {tool: "scalpel_imports_organize",
           args: {files: ["services/api/**"]}},
          {tool: "scalpel_rename",
           args: {file: "crates/foo/src/lib.rs",
                  name_path: "Engine", new_name: "Core"}},
          {tool: "scalpel_imports_organize",
           args: {files: ["crates/foo/src/**"]}}
        ])
        → {transaction_id: "txn_x",
           per_step: [...],
           aggregated_diagnostics_delta: {after: {error: 0, warning: 0, ...}}}

turn 3: scalpel_transaction_commit(transaction_id="txn_x")
        → {applied: true, transaction_id: "txn_x", checkpoint_ids: [...]}

turn 4: external verify (cargo check + pytest)
        → fails (test imports old Engine)

turn 5: scalpel_transaction_rollback(transaction_id="txn_x")
        → {applied: true, restored_files: [...], rolled_back: true}
```

5 turns total (3 scalpel + 2 external) for a cross-language 4-step refactor. Without compose, the same workflow is 8 scalpel turns + verify + 4 manual rollbacks if anything goes wrong = ~14 turns. **Compose is a 3× turn-count savings on multi-step refactors.**

---

## 6. Resolved Conflicts

The 12 conflicts the orchestrator was asked to resolve, in writing.

### 6.1 Tool surface count

Rust-specialist proposed 19 facades; Python-specialist proposed 12+8; Agent-UX proposed 12 always-on + ~11 deferred; Engineering-scope proposed 5 ergonomic facades + primitives at MVP cut.

**Resolved**: **13 always-on + ~11 deferred (Anthropic `defer_loading: true`) = 24 tools at MVP**, with 5 of the 13 always-on being ergonomic intent facades (split, extract, inline, rename, imports_organize). The remaining 8 always-on are catalog/safety/diagnostics/dispatcher/transaction-grammar tools (`scalpel_apply_capability`, `scalpel_capabilities_list`, `scalpel_capability_describe`, `scalpel_dry_run_compose`, `scalpel_transaction_commit`, `scalpel_transaction_rollback`, `scalpel_rollback`, `scalpel_workspace_health`). **"Ergonomic facade" = "intent facade"** in this synthesis — the two terms refer to the same thing. Deferred tools enumerate via `scalpel_capabilities_list` (each row's `preferred_facade` field points to the deferred tool name). They are visible to Anthropic Tool Search but not loaded into cold context. Telemetry post-MVP promotes hot deferred tools to always-on and demotes cold always-on tools to deferred.

The 19-facade proposal collapses to 13 always-on by recognizing that 7 of the Rust-specialist's facades are properly **language-specialty** and belong in deferred-loading (lifetime, impl_trait, ssr, promote_inline_module, extract_struct_from_variant, match_to_iflet, qualify_path). The remaining 12 of 19 collapse further into the 5 ergonomic intent facades because they're parameterized over `target`/`scope`/`engine` (as Agent-UX's option B inside option E pattern dictates). The Python-specialist's 12 facades collapse the same way — `extract_method`, `extract_variable`, `extract_function` are one facade with `target`. `convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `move_method`, `change_signature`, `introduce_factory`, `encapsulate_field`, `annotate_return_type`, `convert_to_async`, `convert_imports` become v0.2.0 / v1.1 deferred specialty or are absorbed into the dispatcher. The +1 (12 → 13) over the original synthesis is the [Q2-resolved](open-questions/q2-12-vs-13-tools.md) promotion of `scalpel_transaction_commit` to a sibling tool.

### 6.2 Stage cut for MVP

Engineering-scope drew the line at Stage 1 + Stage 2 = MVP cut (full primitive reach + capability catalog + rollback + 5 ergonomic facades). Rust-specialist described 19 facades for full coverage.

**Resolved**: **MVP cut = Stage 1 + Stage 2**. The 5 ergonomic always-on intent facades ship at MVP. The 7 specialty deferred Rust-only facades ship at MVP **as deferred-loading entries** (cold-context cost zero). The 6 v0.2.0 ergonomic facades (`convert_module_layout`, `change_visibility`, `tidy_structure`, `change_type_shape`, `change_return_type`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `generate_trait_impl_scaffold`, `generate_member`, `expand_macro`) ship as Stage 3 = `v0.2.0` immediately after MVP. None of the 19 Rust-specialist facades is "v1.1" — they all ship at MVP or v0.2.0. v1.1 is reserved for Python-specific facades and the deferred items in §4.7.

This honors Rust's full-coverage promise (every assist reachable, every WorkspaceEdit shape applied) while keeping the always-on context cost in the *Recommended (mitigated)* band of the published evidence (≤15 always-on tools).

### 6.3 Multi-LSP coordination on Python

Python-specialist committed 3 concurrent LSPs at MVP (pylsp + basedpyright + ruff). Engineering-scope flagged P1 risk (RAM, startup, dedup).

**Resolved**: 3 concurrent Python LSPs at MVP, **plus** pylsp's in-process plugins (pylsp-rope, pylsp-mypy, pylsp-ruff). That is 4 LSP processes scalpel-side total when Python is active (rust-analyzer + pylsp + basedpyright + ruff), 3 of which talk Python. Coordinated via the priority-merge rule (§11). Resource floor commits to 24 GB recommended; `O2_SCALPEL_DISABLE_SERVERS=ruff` and `O2_SCALPEL_DISABLE_LANGS=python` documented opt-outs (§16). The merge rule is *deterministic* — the same input always produces the same merged output, eliminating the multi-LSP non-determinism risk.

### 6.4 Capability catalog as a tool

Agent-UX proposed `scalpel_capabilities_list(language)` as one of the 12 always-on tools. Rust + Python specialists reference catalog drift testing.

**Resolved**: **`scalpel_capabilities_list`** is the canonical name (not `list_capabilities` from Engineering-scope). Signature in §5.1. Cached per-language at MCP server startup. Re-emitted on `scalpel_reload_plugins` (v1.1). The catalog drift test is an MVP gate: CI diffs `scalpel_capabilities_list("rust")` and `scalpel_capabilities_list("python")` JSON output against `test/baselines/capability_catalog_{lang}.json`; any diff = MVP not done. New rust-analyzer release that adds an assist = update the baseline + add an integration test for the new family. Pin `rust-analyzer` to `v0.3.18xx` and the Python LSP stack to exact versions per [Q3 resolution](open-questions/q3-basedpyright-pinning.md): `basedpyright==1.39.3`, `python-lsp-server==1.13.1`, `pylsp-rope==0.1.17`, `pylsp-mypy==0.7.0`, `python-lsp-ruff==2.2.2`, `ruff==0.14.4`, `rope==1.13.0`. Floating (`~=1.X`) was rejected because basedpyright explicitly does not commit to SemVer (v1.32.0 release notes state the project allows "interesting breaking changes" at minor bumps; issue #1218 documents new diagnostics shipping in patches), and 8 of 8 minor releases over 12 months would have changed scalpel's catalog or diagnostic surface — 2 of 8 in ways the catalog drift gate alone does not detect (title-text and diagnostic-count drift). Two new fixtures plug the catalog gate's blind spots; see §15.

### 6.5 Resource floor

Narrow MVP committed 16 GB; full-coverage scope-specialist recommended 24 GB.

**Resolved**: **24 GB recommended** at MVP. 16 GB supported via documented opt-outs:
- `O2_SCALPEL_DISABLE_LANGS=rust` — fall back to CC's read-only RA + `Edit` tool for Rust writes.
- `O2_SCALPEL_DISABLE_LANGS=python` — fall back to CC's read-only pyright + `Edit` for Python writes.
- `O2_SCALPEL_DISABLE_SERVERS=ruff` — Python keeps pylsp + basedpyright; loses ~770 ruff-only lint rules; falls back to autopep8 (~30 rules).
- `O2_SCALPEL_DISABLE_SERVERS=basedpyright` — Python keeps pylsp + ruff; loses Pylance-port auto-import richness; falls back to rope_autoimport.
- `O2_SCALPEL_LAZY_SPAWN=1` (default on) — defers spawn cost until first language-specific facade call.
- `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS=600` (default 10 min) — reclaims idle LSP RAM.

Per-LSP memory cost on the `calcrs+calcpy` fixtures: rust-analyzer ~500 MB, pylsp+plugins ~250 MB, basedpyright ~300 MB, ruff ~80 MB, scalpel MCP server ~300 MB. Aggregate scalpel-side RSS active: ~1.4 GB on fixtures, ~5–6 GB on real workspaces. MVP gate: scalpel-attributable RSS under 8 GB on fixtures.

### 6.6 Pre-MVP spikes

Rust-specialist listed 6 (S1–S6); Python-specialist listed 6 (2 blocking). Reconciled into **12 spikes** in §13 (Q1 added P5a — replaces P5; Q3 added P3a; Q4 added P-WB).

### 6.7 Test gates

Rust-specialist=11 of 16 E2E at MVP; Engineering-scope=9 E2E at MVP. **Resolved: 9 E2E at MVP** (per Engineering-scope's cut line argument — Stages 1+2 = MVP); the additional 2 Rust E2E (E11=`extract_expression` round-trip, E12=`inline_symbol(all_callers)` with diagnostics-delta) are subsumed by E11 in our renumbering. The full 9-scenario list is canonical in §15. The other 6 Rust E2E (E13–E16, plus E4-py / E5-py / E8-py / E11-py from Python) ship as v0.2.0 nightly gates.

### 6.8 `LanguageStrategy` Protocol shape

Rust grew it from 12 to 26 methods. Python added a `PythonStrategyExtensions` mixin with 9 more methods. The base Protocol must stay narrow per the design rule.

**Resolved**: Base Protocol stays at **12 narrow methods** (the original §5 design); a `RustStrategyExtensions` mixin holds the 14 rust-side methods that the full-coverage facades require; a `PythonStrategyExtensions` mixin holds the 9 Python-only methods. Renames adopted from the narrow round (`module_layout_style` → `parent_layout`, structured `DiagnosticsDelta` with `severity_breakdown`, `extract_module_strategy`, `parent_module_register_lines` + `parent_module_import_lines` split). Full Protocol + mixin roster in §7.

### 6.9 `apply_code_action` long-tail dispatcher

Three specialists referenced `apply_code_action` as a primitive. Agent-UX proposed `scalpel_apply_capability` as one of the always-on 12.

**Resolved**: **They are the same tool, with the Agent-UX naming**. The MVP-canonical name is **`scalpel_apply_capability`**. Signature in §5.1. The first parameter is a stable o2.scalpel-issued `capability_id` (e.g., `rust.refactor.extract.module`), **not** a raw LSP `kind` string — this is the hallucination-resistance discipline. The `capability_id` comes from `scalpel_capabilities_list`. The internal implementation translates `capability_id` → LSP `kind` + server selection. Engineering-scope's `apply_code_action` primitive is the implementation, not the user-facing surface; it lives in the solidlsp layer for use by the strategies and is never directly LLM-visible.

The dispatcher carries an explicit `allow_out_of_workspace: bool = False` argument so that any rare power-user invocation that intentionally targets vendored or out-of-workspace paths surfaces through Claude Code's tool-permission prompt (see §11.9). Note: per [Q2 resolution](open-questions/q2-12-vs-13-tools.md), transaction commit was **promoted out of the dispatcher** to its own always-on tool `scalpel_transaction_commit` because routing a core grammar verb through a magic-string `capability_id` was the dominant hallucination failure mode. The `capability_id="scalpel.transaction.commit"` alias is preserved for one minor version as a deprecated path; telemetry monitors residual usage.

### 6.10 Distribution

Engineering-scope confirmed `uvx --from <local-path>` at MVP, marketplace at v1.1 (argument is *stronger* under full coverage).

**Resolved**: Adopt verbatim. `uvx --from <local-path> serena-mcp-server --mode scalpel` at MVP. Marketplace publication at `o2alexanderfedin/claude-code-plugins` at v1.1, for stronger reasons under full coverage:

1. The capability catalog is a versioned contract; drift between RA / Python LSP versions changes `scalpel_capabilities_list` output. Public marketplace consumers cannot tolerate that without v1.0 stability.
2. The 13-tool surface itself is unstable until telemetry confirms which deferred tools to promote.
3. Stage 3 = v0.2.0 ships immediately after MVP; making MVP install path unstable for one release.

### 6.11 Tool-naming convention

Agent-UX proposed `scalpel_<area>_<verb>`. Rust + Python specialists used unprefixed names in their facade lists.

**Resolved**: **`scalpel_<area>_<verb>` adopted canonically and applied throughout this synthesis.** All 13 always-on tools, all ~11 deferred tools, all v0.2.0 facades use this convention. Rust + Python specialists' unprefixed names (`split_file_by_symbols`, `extract_method`, etc.) are renamed accordingly. The MCP namespace prefix `mcp__o2-scalpel__` is added at registration time per Claude Code's MCP convention; the LLM sees `mcp__o2-scalpel__scalpel_split_file` (slightly redundant but harmless; the second `scalpel_` is the meaningful router prefix).

### 6.12 Cuts list

Engineering-scope provided 27-item cut list; Rust gave its own cuts; Python kept 8 facades for v1.1.

**Resolved**: Merged into the canonical 33-item out-of-scope list in §4.7. Every cut has a single owning stage (v0.2.0 / v1.1 / v2+ / explicit-block) and a one-sentence rationale.

---

## 7. Language Strategy Interface (revised)

Base `LanguageStrategy` Protocol stays narrow per the original design rule. Per-language extensions live in mixins. Diff against original design §5 below.

### 7.1 Base Protocol (12 methods)

```python
class LanguageStrategy(Protocol):
    """Per-language plugin. Surface is intentionally narrow.
    If it grows past 15 methods, the abstraction is wrong and
    facades are leaking — re-audit before adding the 16th."""

    language: Language
    file_extensions: frozenset[str]

    # --- Code-action identification ------------------------------------
    def extract_module_kind(self) -> str: ...
        # Rust: "refactor.extract.module"; Python: composes via Rope MoveGlobal
    def move_to_file_kind(self) -> str | None: ...
        # None if pure composition path (Rust has it; Python doesn't)
    def rename_kind(self) -> str: ...

    # --- Module / file layout ------------------------------------------
    def parent_module_register_lines(self, name: str, layout: ParentLayout) -> list[str]: ...
        # Rust+package: ["mod foo;"]  |  Rust+file: ["mod foo;"]
        # Python: ["from . import foo"]
    def parent_module_import_lines(self, name: str, symbols: Iterable[str]) -> list[str]: ...
        # Rust: pub use lines  |  Python: from-import lines
    def module_filename_for(self, name: str, layout: ParentLayout) -> Path: ...
        # Rust+package: foo/mod.rs  |  Rust+file: foo.rs  |  Python: foo.py
    def reexport_syntax(self, symbol: str) -> str: ...

    # --- Planning heuristics -------------------------------------------
    def is_top_level_item(self, symbol: DocumentSymbol) -> bool: ...
    def symbol_size_heuristic(self, symbol: DocumentSymbol) -> int: ...

    # --- Server extensions ---------------------------------------------
    def execute_command_whitelist(self) -> frozenset[str]: ...
    def lsp_init_overrides(self) -> Mapping[str, Any]: ...
```

**ParentLayout** is the renamed `parent_module_style` (see §6.8 — `package` ↔ `dir` and `file` ↔ `mod_rs`). `DocumentSymbol` from LSP.

### 7.2 `RustStrategyExtensions` mixin (14 methods)

```python
class RustStrategyExtensions(Protocol):
    """Rust-specific seam. Implemented by RustStrategy. Used by full-coverage
    facades that the cross-language base does not need (lifetimes, macros,
    SSR, rust-analyzer custom extensions)."""

    # --- Code-action kind tables ---------------------------------------
    def extractor_kinds(self) -> Mapping[ExtractorKind, str]: ...
    def inliner_kinds(self) -> Mapping[InlinerKind, str]: ...
    def generator_kinds(self) -> Mapping[GeneratorKind, str | None]: ...
    def visibility_change_kind(self) -> str | None: ...
    def reorder_kinds(self) -> Mapping[ReorderScope, str]: ...
    def kind_match_priority(self) -> Sequence[str]: ...

    # --- Capability gates ----------------------------------------------
    def supports_lifetimes(self) -> bool: ...     # True
    def supports_macros(self) -> bool: ...        # True
    def supports_structural_search(self) -> bool: ...   # True (SSR)
    def supports_proc_macros(self) -> bool: ...   # True

    # --- Dry-run / safety ----------------------------------------------
    def dry_run_supported_for(self, facade_name: str) -> bool: ...
    def is_safe_to_move(self, symbol: DocumentSymbol) -> tuple[bool, str]: ...

    # --- Post-apply hooks ----------------------------------------------
    def post_apply_health_check_commands(self) -> list[ExecuteCommand]: ...
        # Rust: [ExecuteCommand("rust-analyzer/runFlycheck")]

    # --- Specialty seams (kept empty at MVP; reserved) ----------------
    def language_specific_facades(self) -> list[ToolDescriptor]: ...   # [] at MVP
    def explicit_command_blocks(self) -> frozenset[str]: ...           # {"experimental/onEnter"}

    def clustering_signal_quality(self) -> Literal["high", "medium", "low"]: ...   # "high"
    def default_visibility_for_extracted_module(self) -> str: ...                  # "pub(crate)"
```

### 7.3 `PythonStrategyExtensions` mixin (9 methods)

```python
class PythonStrategyExtensions(Protocol):
    """Python-only methods. Used by PythonStrategy.
    Cross-language facades isinstance-check the strategy."""

    # --- Layout discovery ---------------------------------------------
    def is_namespace_package(self, project_root: Path) -> bool: ...
    def detect_init_side_effects(self, init_path: Path) -> list[SideEffect]: ...

    # --- Public-API surface management --------------------------------
    def parse_dunder_all(self, file_path: Path) -> list[str] | None: ...
    def update_dunder_all(self, file_path: Path,
                          additions: list[str], removals: list[str]) -> WorkspaceEdit: ...

    # --- Type-system glue --------------------------------------------
    def has_type_checking_block(self, file_path: Path) -> bool: ...
    def rewrite_type_checking_imports(self, file_path: Path,
                                      name_map: dict[str, str]) -> WorkspaceEdit: ...
    def has_future_annotations(self, file_path: Path) -> bool: ...

    # --- Stub-file twin handling --------------------------------------
    def stub_file_for(self, source_path: Path) -> Path | None: ...
    def split_stub_alongside(self, stub_path: Path,
                             symbol_groups: dict[str, list[str]]) -> WorkspaceEdit: ...

    # --- Decorator-aware top-level resolution -------------------------
    def resolve_decorated_top_level(self, file_path: Path,
                                    source_symbols: list[DocumentSymbol]
                                    ) -> list[ResolvedTopLevel]: ...

    # --- Import normalization + circular-import detection -------------
    def normalize_relative_imports(self, file_path: Path,
                                   mode: Literal["absolute", "relative"]) -> WorkspaceEdit: ...
    def find_import_cycles(self, project_root: Path) -> list[list[str]]: ...

    # --- Async detection ----------------------------------------------
    def is_async_definition(self, symbol: DocumentSymbol) -> bool: ...
```

### 7.4 Diff vs. original design §5

| Original method | Status | Replacement |
|---|---|---|
| `extract_module_kind` | kept on base | — |
| `move_to_file_kind` | kept on base | — |
| `rename_kind` | kept on base | — |
| `module_declaration_syntax(name, style)` | **split** | `parent_module_register_lines` + `parent_module_import_lines` |
| `module_filename_for(name, style)` | kept; `style: ParentLayout` enum | renamed parameter type |
| `reexport_syntax` | kept on base | — |
| `is_top_level_item` | kept on base | — |
| `symbol_size_heuristic` | kept on base | — |
| `execute_command_whitelist` | kept on base | — |
| `post_apply_health_check_commands` | **moved to mixin** | `RustStrategyExtensions.post_apply_health_check_commands` |

### 7.5 Supporting enums + types

```python
class ParentLayout(StrEnum):
    PACKAGE = "package"   # dir-based: foo/mod.rs (Rust), foo/__init__.py (Python)
    FILE    = "file"      # single-file: foo.rs (Rust), foo.py (Python)

class ExtractorKind(StrEnum):
    FUNCTION   = "function"
    VARIABLE   = "variable"
    CONSTANT   = "constant"
    STATIC     = "static"
    TYPE_ALIAS = "type_alias"
    MODULE     = "module"

class InlinerKind(StrEnum):
    CALL       = "call"
    VARIABLE   = "variable"
    TYPE_ALIAS = "type_alias"
    MACRO      = "macro"
    CONST      = "const"

class InlineScope(StrEnum):
    SINGLE_CALL_SITE = "single_call_site"
    ALL_CALLERS      = "all_callers"

class GeneratorKind(StrEnum):
    TRAIT_IMPL = "trait_impl"
    METHOD     = "method"
    GETTER     = "getter"
    SETTER     = "setter"
    NEW        = "new"
    DELEGATE   = "delegate"

class ReorderScope(StrEnum):
    FILE   = "file"
    IMPL   = "impl"
    STRUCT = "struct"

class Visibility(StrEnum):
    PRIVATE   = "private"
    PUB_SUPER = "pub_super"
    PUB_CRATE = "pub_crate"
    PUB       = "pub"

class ExecuteCommand(BaseModel):
    method: str
    arguments: list[Any] = []
```

### 7.6 Strategy method count audit

| Mixin | Method count | Soft cap | Notes |
|---|---|---|---|
| `LanguageStrategy` (base) | 12 | 15 | Unchanged from original design; rename of `module_declaration_syntax` to two methods balanced by removing `post_apply_health_check_commands` |
| `RustStrategyExtensions` | 14 | — | All gated by single-purpose accessors; cannot consolidate without losing fail-fast clarity |
| `PythonStrategyExtensions` | 13 | — | Stub-file twin handling reserved as sub-mixin if TS `.d.ts` warrants reuse |
| **Total Rust facade view** | **26 methods** | — | (12 base + 14 RustExt) |
| **Total Python facade view** | **25 methods** | — | (12 base + 13 PythonExt) |

The Rust-specialist's 26-method count for the full `LanguageStrategy` is preserved exactly — but partitioned across base + mixin so the base Protocol stays at 12. Future minimal strategies (TypeScript paper design, Go, clangd) implement only the 12-method base.

**`parent_module_style: dir|mod_rs`** vocabulary is **renamed `parent_layout: package|file`** per the narrow round's leak-fix recommendation. `package` = directory-with-init/mod.rs layout; `file` = single-file module layout.

The original 12-method design is preserved on the base; full-coverage growth is contained in mixins. Facades `isinstance`-check the strategy when they need extension methods. The base Protocol's narrow shape means a future minimal strategy (TypeScript paper-design) implements only 12 methods.

---

## 8. Rust full-coverage MVP

Distilled from `specialist-rust.md`. The Rust side is the larger of the two strategies under full coverage (~7,335 LoC + 19 fixtures vs. Python's ~3,470 + ~5,310 LoC including fixtures). Key commitments:

### 8.1 Facade roster (all reachable at MVP)

| Tier | Facades | Count | When |
|---|---|---|---|
| Always-on (5 ergonomic) | `scalpel_split_file`, `scalpel_extract`, `scalpel_inline`, `scalpel_rename`, `scalpel_imports_organize` | 5 | MVP Stage 2 |
| Always-on (catalog/safety/diag/transaction-grammar) | `scalpel_apply_capability`, `scalpel_capabilities_list`, `scalpel_capability_describe`, `scalpel_dry_run_compose`, `scalpel_transaction_commit`, `scalpel_rollback`, `scalpel_transaction_rollback`, `scalpel_workspace_health` | 8 | MVP Stage 1+2 |
| Deferred Rust-specialty | `scalpel_rust_lifetime_elide`, `scalpel_rust_impl_trait`, `scalpel_rust_promote_inline_module`, `scalpel_rust_extract_struct_from_variant`, `scalpel_rust_match_to_iflet`, `scalpel_rust_qualify_path`, `scalpel_rust_ssr` | 7 | MVP (defer_loading) |
| v0.2.0 (Stage 3 ergonomic) | `convert_module_layout`, `change_visibility`, `tidy_structure`, `change_type_shape`, `change_return_type`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `generate_trait_impl_scaffold`, `generate_member`, `expand_macro`, `verify_after_refactor` | 12 | v0.2.0 |

### 8.2 Assist-family coverage

| Family | Reach | Test fixture |
|---|---|---|
| A — Module/file boundary (4 assists) | `scalpel_split_file` + `scalpel_rust_promote_inline_module` (deferred) + `convert_module_layout` (v0.2.0) | `inline_modules.rs`, `mod_rs_swap.rs`, `ra_module_layouts.rs` |
| B — Extractors (8 assists) | `scalpel_extract(target=...)` + `scalpel_rust_extract_struct_from_variant` (deferred) | `ra_extractors.rs` |
| C — Inliners (5 assists) | `scalpel_inline(target=..., scope=...)` | `ra_inliners.rs` |
| D — Imports (10 assists) | `scalpel_imports_organize` + v0.2.0 `expand_glob_imports` | `ra_imports.rs`, `ra_glob_imports.rs` |
| E — Visibility (2 assists) | `scalpel_imports_organize` (auto-fired) + v0.2.0 `change_visibility` | `cross_visibility.rs`, `ra_visibility.rs` |
| F — Ordering (3 assists) | dispatcher + v0.2.0 `tidy_structure` | `ra_ordering.rs` |
| G — Generators (32 assists) | dispatcher + `scalpel_rust_impl_trait` (deferred) + v0.2.0 `generate_trait_impl_scaffold`, `generate_member` | `ra_generators_traits.rs`, `ra_generators_methods.rs` |
| H — Convert/rewrite (40 assists) | dispatcher + `scalpel_rust_match_to_iflet` (deferred) + v0.2.0 `change_type_shape`, `change_return_type` | `ra_convert_typeshape.rs`, `ra_convert_returntype.rs` |
| I — Pattern (5 assists) | dispatcher + v0.2.0 `complete_match_arms` | `ra_pattern_destructuring.rs` |
| J — Lifetimes (4 assists) | `scalpel_rust_lifetime_elide` (deferred) + v0.2.0 `extract_lifetime` | `ra_lifetimes.rs` |
| K — `term_search` (1 assist) | dispatcher only (no symbolic input) | `ra_term_search.rs` |
| L — Quickfixes (~30 assists) | dispatcher (diagnostics-delta sweep) | `ra_quickfixes.rs` |

### 8.3 Custom-extension coverage

8 first-class (parentModule, childModules, viewItemTree internal, expandMacro v0.2.0, ssr deferred, runFlycheck via diagnostics, runnables/relatedTests v0.2.0, reloadWorkspace+rebuildProcMacros via diagnostics). 27 typed pass-through. 1 explicit-block (`experimental/onEnter`).

### 8.4 Protocol method coverage

All ~52 advertised LSP methods wired (§4.5). `workspace/applyEdit` is full-fidelity (not stub) — required by SSR and macro-expansion paths per spike S3.

### 8.5 Fixtures (`calcrs` + 18 companions)

| Fixture | LoC | Families exercised |
|---|---|---|
| `calcrs/src/lib.rs` (expanded) | ~950 | A, D, E, L |
| `ra_extractors.rs` | ~250 | B |
| `ra_inliners.rs` | ~200 | C |
| `ra_visibility.rs` | ~150 | E |
| `ra_imports.rs` | ~300 | D |
| `ra_glob_imports.rs` | ~120 | D (glob) |
| `ra_ordering.rs` | ~180 | F |
| `ra_generators_traits.rs` | ~250 | G |
| `ra_generators_methods.rs` | ~200 | G |
| `ra_convert_typeshape.rs` | ~150 | H |
| `ra_convert_returntype.rs` | ~120 | H |
| `ra_pattern_destructuring.rs` | ~150 | I |
| `ra_lifetimes.rs` | ~180 | J |
| `ra_proc_macros.rs` | ~200 | proc-macro pathway (serde) |
| `ra_ssr.rs` | ~180 | SSR |
| `ra_macros.rs` | ~150 | `expandMacro` |
| `ra_module_layouts.rs` | ~200 | A (mod.rs swap) |
| `ra_quickfixes.rs` | ~250 | L |
| `ra_workspace_edit_shapes.rs` | ~120 | every WorkspaceEdit variant |
| `ra_term_search.rs` | ~80 | K |

**Total Rust fixtures: ~3,400 LoC across 19 fixtures.**

### 8.6 6 pre-MVP Rust spikes

Numbered S1–S6 per `specialist-rust.md` §6. All 6 are MVP-blocking (results documented before design freeze):

- **S1**: `multilspy` `$/progress` forwarding (gates `wait_for_indexing` design)
- **S2**: `SnippetTextEdit` round-trip with `snippetTextEdit:false` (gates strip path scope)
- **S3**: `applyEdit` reverse-request fires on `CodeAction.command` paths (gates handler scope; required for SSR)
- **S4**: `experimental/ssr` upper bound on `WorkspaceEdit` size (gates SSR safety)
- **S5**: `rust-analyzer/expandMacro` works on proc macros (gates expand_macro facade scope)
- **S6**: `auto_import` apply branch — `command` vs `edit` resolve shape (gates `scalpel_imports_organize` correctness)

Pessimistic-path combined cost: +250 LoC of remediation. Spike outcomes unify with the §13 master spike list.

### 8.7 Rust LoC

| Layer | LoC |
|---|---|
| `solidlsp` primitive methods | ~120 |
| `rust_analyzer.py` init | ~15 |
| WorkspaceEditApplier (variants × options × ordering × atomicity) | ~500 |
| Reverse-request handlers | ~150 |
| `$/progress` listener + `wait_for_indexing` | ~80 |
| Checkpoint/rollback machinery | ~150 |
| Primitive tools | ~350 |
| 5 always-on ergonomic facades (Rust portion) | ~700 |
| 7 deferred Rust-specialty facades | ~700 |
| 12 v0.2.0 ergonomic facades | ~1,650 |
| Typed `execute_command` whitelist + dispatch | ~180 |
| `LanguageStrategy` base + `RustStrategyExtensions` | ~250 |
| `RustStrategy` plugin (full whitelist, kinds, post-apply) | ~300 |
| Unit tests | ~900 |
| Integration tests + 19 fixtures | ~1,200 + 3,400 fixtures |
| E2E harness + scenarios | ~700 |
| **Rust-side total** | **~7,335 LoC + 3,400 fixture LoC** |

### 8.8 Rust-specific facade Pydantic stubs (selected)

```python
class StructuralSearchReplaceInput(BaseModel):
    pattern: str        # rust-analyzer SSR pattern syntax
    template: str       # SSR replacement template
    files: list[str] | None = None
    max_edits: int = 500
    dry_run: bool = False

class ExpandMacroInput(BaseModel):
    file: str
    position: Position

class ChangeTypeShapeInput(BaseModel):
    file: str
    type_name_path: str
    change: Literal["named_to_tuple", "tuple_to_named",
                    "bool_to_enum", "tuple_return_to_struct"]
    dry_run: bool = False

class ChangeReturnTypeInput(BaseModel):
    file: str
    fn_name_path: str
    change: Literal["wrap_option", "wrap_result",
                    "unwrap_option", "unwrap_result"]
    dry_run: bool = False

class CompleteMatchArmsInput(BaseModel):
    file: str
    position: Position
    dry_run: bool = False

class ExtractLifetimeInput(BaseModel):
    file: str
    fn_or_type_name_path: str
    new_lifetime: str = "'a"
    dry_run: bool = False

class GenerateTraitImplScaffoldInput(BaseModel):
    file: str
    type_name_path: str
    trait_path: str
    complete_missing: bool = True
    dry_run: bool = False

class GenerateMemberInput(BaseModel):
    file: str
    target_type_name_path: str
    member_kind: GeneratorKind
    member_name: str
    field_or_target: str | None = None
    dry_run: bool = False

class TidyStructureInput(BaseModel):
    file: str
    scope: ReorderScope = ReorderScope.FILE
    options: list[Literal["impl_order", "item_order", "field_order"]]
    dry_run: bool = False

class VerifyAfterRefactorResult(BaseModel):
    flycheck_ok: bool
    flycheck_diagnostics: DiagnosticsDelta
    tests_run: int
    tests_passed: int
    tests_failed: int
    failed_tests: list[str]
    runnables_executed: list[str]
    duration_ms: int
```

---

## 9. Python full-coverage MVP

Distilled from `specialist-python.md`. The Python side is structurally different from Rust: composition + library bridge instead of single-assist-call, three concurrent LSPs, multi-server merge rule.

### 9.1 3-LSP architecture

| Server | Role | MVP capabilities | RAM (calcpy) |
|---|---|---|---|
| pylsp + pylsp-rope + pylsp-mypy (`live_mode: false`, `dmypy: true`) + pylsp-ruff plugin disabled | Refactor primary | base nav, 9 rope commands, mypy diagnostics (via dmypy daemon) | ~250 MB |
| basedpyright | Pylance-port auto-import, typecheck secondary, organize-imports secondary | Pylance-port auto-import, `# pyright: ignore` insertion, basedpyright commands | ~300 MB |
| ruff server | Lint autofix tertiary | `source.fixAll.ruff`, `source.organizeImports.ruff`, ~800 lint rules (300 autofixable) | ~80 MB |
| **Total scalpel-side Python RAM** | | | **~630 MB** |

`pylsp_ruff` plugin is disabled inside pylsp because we run standalone `ruff server` instead. `pyflakes`, `pycodestyle`, `mccabe`, `autopep8`, `yapf`, `pylint`, `flake8` plugins are all disabled in pylsp because ruff covers their domain — running them via pylsp would duplicate diagnostics that the merge rule then has to dedup.

**pylsp-mypy canonical config** (resolved via [Q1](open-questions/q1-pylsp-mypy-live-mode.md)): `live_mode: false` + `dmypy: true`. `pylsp-mypy` and `live_mode: true` are mutually exclusive at the plugin level (`pylsp_mypy/plugin.py:264` — the plugin forces `live_mode=False` when `dmypy=true`), and naïvely shipping `live_mode: false` returns cached `last_diagnostics` on every internal `didChange` (plugin.py:285), making the *true* stale-rate within a transaction **100%, not the 5% the original §19 entry assumed**. Therefore: scalpel injects a synthetic `textDocument/didSave` after each successful internal `apply()` step within a transaction — buffer is written to disk, all three Python LSPs receive `didSave`, and the dmypy daemon re-checks the on-disk state in <500 ms warm. Cross-LSP consistency is tightened (all three servers see the same on-disk state per step), atomicity at the user-visible transaction boundary is preserved via the existing `python-edit-log.jsonl` rollback machinery (§11.5), and basedpyright remains authoritative for `severity_breakdown` per §11.1 — pylsp-mypy is a corroborator, not a gate. Spike **P5a** (§13) is the falsifier: stale-rate <5% AND p95 didSave→diagnostic latency <1 s on `calcpy` → ship; failure → drop pylsp-mypy from the active server set and rely on basedpyright alone. Integration cost ~135 LoC across `python_strategy.py`, `multi_server.py`, and tests; Stage 2 LoC accounting in §14 absorbs this.

### 9.2 Full Rope inventory mapping

| Path | Count | At MVP |
|---|---|---|
| pylsp-rope command (LSP path) | 9 | All reachable; 3 facaded (extract.method, extract.variable, inline → `scalpel_extract`/`scalpel_inline`); 1 in `scalpel_imports_organize`; 5 reachable via dispatcher |
| Rope library bridge (strategy-internal) | 10 | `MoveGlobal` and `MoveModule` composed inside `scalpel_split_file`/`scalpel_rename`; 8 v1.1 (`MoveMethod`, `ChangeSignature`, `IntroduceFactory`, `EncapsulateField`, `Restructure`, `ImportTools.{handle_long_imports,relative_to_absolute,froms_to_imports,expand_stars}`) |

**Bridge-shape rule**: every library-bridge call returns the same `WorkspaceEdit` shape that pylsp-rope would have returned via the LSP path. The applier is unaware of which path produced the edit.

### 9.3 Python facade roster

| Tier | Facades | Count |
|---|---|---|
| Always-on (5 ergonomic, shared with Rust) | `scalpel_split_file`, `scalpel_extract`, `scalpel_inline`, `scalpel_rename`, `scalpel_imports_organize` | 5 |
| Always-on (7 catalog/safety/diag, shared) | (per §5.1) | 7 |
| Deferred Python-specialty | `scalpel_py_async_ify`, `scalpel_py_type_annotate`, `scalpel_py_dataclass_from_dict`, `scalpel_py_promote_method_to_function` | 4 |
| v0.2.0 (Stage 3 Python ergonomic) | `convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `auto_import` (specialized), `fix_lints`, `ignore_diagnostic` | 8 |
| v1.1 (deferred) | `move_method`, `move_symbol`, `change_signature`, `introduce_factory`, `encapsulate_field`, `annotate_return_type`, `convert_to_async`, `convert_imports`, `expand_star_imports`, `restructure` | 10 |

### 9.4 14-step interpreter discovery chain

Strict order, fail loud at end. Every Python LSP gets the same resolved interpreter.

| # | Source |
|---|---|
| 1 | `$O2_SCALPEL_PYTHON_EXECUTABLE` env var |
| 2 | `[tool.o2-scalpel] python_executable` in `pyproject.toml` |
| 3 | `$VIRTUAL_ENV/bin/python` |
| 4 | `<project-root>/.venv/bin/python` |
| 5 | `<project-root>/venv/bin/python` |
| 6 | `<project-root>/__pypackages__/<py-version>/bin/python` (PEP 582 / PDM) |
| 7 | `poetry env info -p` if `poetry.lock` present |
| 8 | `pdm info --packages` if `pdm.lock` present |
| 9 | `uv run --no-project which python` if `uv.lock` present |
| 10 | `pipenv --venv` if `Pipfile.lock` present |
| 11 | `$CONDA_PREFIX/bin/python` (conda / micromamba) |
| 12 | `pyenv which python` if `.python-version` present |
| 13 | `asdf which python` if `.tool-versions` present |
| 14 | First `python3` on `$PATH` whose `sys.prefix` differs from system Python |

(The list grew from the narrow round's 10 to 14; PEP 582, pipenv, asdf, and the path-walk heuristic are the additions. Step 15 = `sys.executable`; step 16 = fail loud with structured `interpreter_unresolved` failure including all attempted paths.)

Cache invalidation: stat the resolved `python` binary on each LSP request that depends on it; if mtime/inode changed, re-run the chain.

### 9.5 Fixture: `calcpy` + 4 sub-fixtures

| Fixture | LoC | Pitfalls covered |
|---|---|---|
| `calcpy/calcpy.py` (monolith) | ~950 | star imports, `__init__.py` side effects, runtime-injected attrs, `__all__`, `if __name__ == "__main__"`, doctest, decorators, async, future-annotations |
| `calcpy/calcpy.pyi` stub | ~120 | stub drift |
| `calcpy/__init__.py` re-exports | ~15 | |
| `tests/test_calcpy.py` + `test_public_api.py` + `test_doctests.py` | ~310 | regression baseline |
| `pyproject.toml` | ~25 | |
| `calcpy_namespace/` (PEP 420 namespace package) | ~180 | namespace package detection |
| `calcpy_circular/` (engineered circular import) | ~90 | circular-import detection |
| `calcpy_dataclasses/` (5 `@dataclass` declarations) | ~220 | decorator-aware top-level resolution |
| `calcpy_notebooks/` (`.ipynb` companion) | ~100 | notebook detection (warn-only) |
| Expected-state snapshots | ~250 | |

**Total Python fixtures: ~2,260 LoC.**

24 pitfalls covered (star-imports, namespace packages, stub drift, circular imports, runtime-injected attrs, `__all__`, pytest discovery, notebooks, `TYPE_CHECKING` blocks, future-annotations, PEP 695 generics, PEP 701 f-string nesting, dataclass restructuring, async/await, decorator stack, name-mangling, conditional top-level, future-import placement, doctest, `if __name__ == "__main__"`, lazy imports, monkey-patched stdlib, plus 2 explicit non-coverage items: implicit relative imports, Cython).

### 9.6 6 pre-MVP Python spikes (2 blocking)

| ID | Question | Blocking? |
|---|---|---|
| P1 | pylsp-rope unsaved-buffer behavior — does it honor `didChange` without `didSave`? | **blocking** |
| P2 | Conflicting `source.organizeImports` between pylsp-rope and ruff — diff and lock the merge winner | **blocking** |
| P3 | Rope's `MoveGlobal` against PEP 695 / PEP 701 / PEP 654 syntax | non-blocking (gates 3.13+ support) |
| P4 | basedpyright `relatedInformation` on diagnostics richness | non-blocking |
| P5a | pylsp-mypy stale-diagnostic rate on `calcpy` under `live_mode: false` + `dmypy: true` + scalpel-injected per-step `didSave` (replaces the old P5 ruff-cycle question, which folds into spike implementation) | **blocking** ([Q1 falsifier](open-questions/q1-pylsp-mypy-live-mode.md): pass = stale-rate <5% AND p95 didSave→diagnostic latency <1 s; fail = drop pylsp-mypy at MVP) |
| P6 | Three-server `textDocument/rename` response convergence | non-blocking |

### 9.7 Python LoC

| Component | LoC |
|---|---|
| `PythonStrategy` core (incl. extensions §7.3) | ~420 |
| Python-specific facades (12 MVP + 10 v1.1 placeholders) | ~640 |
| Multi-server multiplexer (§11 merge rule) | ~430 |
| Interpreter discovery (§9.4) | ~210 |
| Rope library bridge (10 ops) | ~280 |
| WorkspaceEdit applier upgrades (Python-side) | ~120 |
| Tests (unit + integration + E2E) | ~1,050 |
| Fixture content (`calcpy` + 4 sub-fixtures) | ~1,840 |
| **Python-side total** | **~3,470 production + ~1,840 fixtures** |

### 9.8 Python-specific facade Pydantic stubs (selected)

```python
class FixLintsInput(BaseModel):
    files: list[str]
    rules: list[str] | None = None       # e.g. ["F401", "UP*"] or None for all
    apply_unsafe: bool = False
    iteration_cap: int = 5
    dry_run: bool = False

class IgnoreDiagnosticInput(BaseModel):
    file: str
    range: Range
    tool: Literal["ruff", "pyright", "mypy"]
    rule_code: str | None = None
    scope: Literal["line", "file", "block"] = "line"
    dry_run: bool = False

class AutoImportInput(BaseModel):
    file: str
    range: Range
    target_name: str | None = None       # disambiguator
    prefer: Literal["basedpyright", "rope"] = "basedpyright"
    dry_run: bool = False

class GenerateFromUndefinedInput(BaseModel):
    file: str
    range: Range
    target: Literal["variable", "function", "class", "module", "package"]
    location_hint: str | None = None
    dry_run: bool = False

class ConvertToMethodObjectInput(BaseModel):
    file: str
    name_path: str          # method name-path
    new_class_name: str
    dry_run: bool = False

class LocalToFieldInput(BaseModel):
    file: str
    name_path: str          # local variable name-path inside a method
    field_name: str | None = None
    dry_run: bool = False

class IntroduceParameterInput(BaseModel):
    file: str
    name_path: str          # function name-path
    expression_range: Range  # what to lift to a parameter
    parameter_name: str
    dry_run: bool = False

class UseFunctionInput(BaseModel):
    file: str
    name_path: str          # the function to use
    scope: Literal["file", "project"] = "file"
    dry_run: bool = False
```

### 9.9 Python interpreter discovery — failure mode

```python
class InterpreterUnresolvedFailure(BaseModel):
    kind: Literal["interpreter_unresolved"]
    attempted: list[ResolutionStep]
    hint: str

class ResolutionStep(BaseModel):
    step: int
    source: str        # human description
    result: Literal["not_set", "no_match", "subprocess_failed", "path_not_executable"]
    error: str | None
```

If step 16 hits, scalpel returns this structured failure. The LLM can read `hint` and act without scraping. The full `attempted` chain is preserved for triage telemetry.

---

## 10. Cross-language `RefactorResult` schema

Finalized; supersedes the v1 design's §3 `RefactorResult` and absorbs the multi-LSP additions Python requires.

```python
class ChangeProvenance(BaseModel):
    """Carried on every FileChange. The `source` field replaces what was
    historically a bare Literal string; the boolean fields record which
    safety/normalization passes the change has cleared."""
    source: Literal["pylsp-rope", "pylsp-base", "basedpyright", "ruff",
                    "pylsp-mypy", "rust-analyzer", "rope-library", "scalpel-internal"]
        # Which LSP server emitted this change (Python multi-LSP path)
        # or "rust-analyzer" for Rust, "scalpel-internal" for orchestrator-applied.
    workspace_boundary_check: bool = True
        # True iff the change's target path passed the §11 workspace-boundary
        # path filter (Q4 resolution). Always True for applied changes; the
        # field is included for trace-forensics and is the canonical signal
        # that the §11.9 confirmation flow either passed or was bypassed via
        # `allow_out_of_workspace=True`.

class FileChange(BaseModel):
    path: str
    kind: Literal["create", "modify", "delete"]
    hunks: list[Hunk]
    provenance: ChangeProvenance

class DiagnosticSeverityBreakdown(BaseModel):
    error: int
    warning: int
    information: int
    hint: int

class DiagnosticsDelta(BaseModel):
    before: DiagnosticSeverityBreakdown
    after: DiagnosticSeverityBreakdown
    new_findings: list[Diagnostic]   # finer-grained than v1's `new_errors`
    severity_breakdown: DiagnosticSeverityBreakdown   # `after - before` per severity

class LanguageFinding(BaseModel):
    """Language-specific finding the standard severity breakdown can't carry.
    Python uses for circular-import SCCs, namespace-package warnings, etc.
    Rust uses for proc-macro expansion failures, edition mismatches."""
    code: str
    message: str
    locations: list[Location]
    related: list[str] = []

class ResolvedSymbol(BaseModel):
    requested: str
    resolved: str
    kind: str        # symbol kind for disambiguation

class FailureInfo(BaseModel):
    stage: str
    symbol: str | None
    reason: str
    code: ErrorCode  # one of the 10 error codes from §15.4
    recoverable: bool
    candidates: list[str] = []   # for SYMBOL_NOT_FOUND, CAPABILITY_NOT_AVAILABLE
    failed_step_index: int | None = None   # for TRANSACTION_ABORTED

class LspOpStat(BaseModel):
    method: str
    server: str             # which LSP (Python multi-LSP path)
    count: int
    total_ms: int

class RefactorResult(BaseModel):
    applied: bool
    no_op: bool = False
    changes: list[FileChange]
    diagnostics_delta: DiagnosticsDelta
    language_findings: list[LanguageFinding] = []
    checkpoint_id: str | None
    transaction_id: str | None = None
    preview_token: str | None = None
    resolved_symbols: list[ResolvedSymbol]
    warnings: list[str]
    failure: FailureInfo | None = None
    lsp_ops: list[LspOpStat]
    duration_ms: int
    language_options: dict = {}   # opaque, per-language extra (e.g., RustOptions, PythonOptions)

class TransactionResult(BaseModel):
    transaction_id: str
    per_step: list[RefactorResult]
    aggregated_diagnostics_delta: DiagnosticsDelta
    aggregated_language_findings: list[LanguageFinding] = []
    duration_ms: int
    rules_fired: list[str]    # cross-step
    rolled_back: bool = False
    remaining_checkpoint_ids: list[str] = []  # populated on partial rollback failure

class WorkspaceHealth(BaseModel):
    project_root: str
    languages: dict[str, LanguageHealth]   # keyed by language name

class LanguageHealth(BaseModel):
    language: str
    indexing_state: Literal["indexing", "ready", "failed", "not_started"]
    indexing_progress: str | None  # token-prefixed message
    servers: list[ServerHealth]
    capabilities_count: int
    estimated_wait_ms: int | None
    capability_catalog_hash: str   # for drift detection

class ServerHealth(BaseModel):
    server_id: str        # "rust-analyzer", "pylsp", "basedpyright", "ruff"
    version: str
    pid: int | None
    rss_mb: int | None
    capabilities_advertised: list[str]    # codeActionKinds, etc.
```

**Key changes vs. v1 `RefactorResult`**:

1. `DiagnosticsDelta` upgraded from integer counts to **`severity_breakdown`** (error/warning/info/hint). Diagnostic-delta gate uses `severity_breakdown["error"].after > 0`.
2. `language_findings: list[LanguageFinding]` carries Python-specific concerns (import cycles, namespace-package warnings) and Rust-specific concerns (proc-macro expansion failures) without leaking into the cross-language schema's primary fields.
3. `provenance` field per `FileChange` records which LSP server emitted the change (Python multi-LSP path).
4. `preview_token` separated from `checkpoint_id`. Preview tokens have a 5-min TTL and don't survive file changes; checkpoints persist for the LRU lifetime.
5. `transaction_id` carried for chained operations (`scalpel_dry_run_compose` commits).
6. `language_options: dict` is the opaque bag where per-language facade-specific knobs live (e.g., `{"rust": {"reexport_policy": "preserve_public_api"}}`, `{"python": {"engine": "ruff"}}`).
7. `failure.code: ErrorCode` is now an enum (the 10 codes of §15.4).
8. `lsp_ops[].server` records which LSP method was issued against (multi-server fan-out observability).

---

## 11. Multi-LSP coordination protocol

Only Python uses it at MVP, but the design must support it. Specified once and implementation-shared with future Rust+other-LSP scenarios (e.g., Rust + clippy server).

### 11.1 Two-stage merge rule

When a tool issues `textDocument/codeAction` for a `(file, range, kind-prefix)` tuple to all reachable LSPs in parallel, results merge through:

**Stage 1 — server priority per kind-prefix:**

| Kind prefix | Priority order (highest → lowest) | Rationale |
|---|---|---|
| `source.organizeImports` | ruff > pylsp-rope > basedpyright | Ruff is fastest and matches isort, the de-facto standard |
| `source.fixAll` | ruff (unique) | Only ruff emits |
| `quickfix` (auto-import context) | basedpyright > pylsp-rope (rope_autoimport) | Pylance heuristics best-in-class |
| `quickfix` (lint fix context) | ruff > pylsp-rope > basedpyright | Ruff owns lint |
| `quickfix` (type error context) | basedpyright > pylsp-mypy | basedpyright richer; mypy still runs for cross-validation |
| `quickfix` (other) | pylsp-rope > basedpyright > ruff | Catch-all; pylsp-rope's `quickfix.generate` is unique |
| `refactor.extract` | pylsp-rope (unique) | Only pylsp-rope emits |
| `refactor.inline` | pylsp-rope (unique) | Only pylsp-rope emits |
| `refactor.rewrite` | pylsp-rope > basedpyright | Both can emit; Rope more thorough |
| `refactor` (catch-all) | pylsp-rope > basedpyright | Pylsp-rope owns refactor surface |
| `source` (catch-all) | ruff > pylsp-rope > basedpyright | Ruff owns source-level transforms |

Context disambiguators inside `quickfix` are inferred from the triggering diagnostic code (table in `specialist-python.md` §5.3).

**Stage 2 — dedup-by-equivalence:**

For actions surviving Stage 1, dedup if **any** of:

1. **Normalized title equality**. Lowercase, strip leading "Add: " / "Quick fix: ", collapse whitespace. `"Import 'numpy'"` and `"Add import: numpy"` normalize to `"import numpy"`.
2. **`WorkspaceEdit` structural equality**: same set of `(uri, range, newText)` triples after applying the resolve step. Computed lazily — only on titles that don't match.

Tiebreak: prefer the higher-priority server's action.

### 11.2 Server-disagreement handling

| Case | Resolution |
|---|---|
| Two servers' `WorkspaceEdit`s overlap on byte ranges (one is a subset of the other) | Pick higher-priority; warn only if lower-priority would have produced changes the higher-priority does not |
| Two servers return same kind on different ranges (one wider, one narrower) | Treat as different actions; do not dedup. LLM picks via title |
| Server returns `disabled.reason` set | Preserve in merged list; LLM sees why disabled. Do not silently drop |
| Server times out (>2 s for `codeAction`) | Continue with responding servers; emit `warnings: ["server X timed out on codeAction"]` |
| Server returns action with `kind: null` or unrecognized | Bucket as `quickfix.other`; lowest priority |
| All servers return byte-identical edit | Pick highest-priority provenance; suppress rest |

### 11.3 `textDocument/rename` priority (single-response, not list)

Rename is a single-`WorkspaceEdit` method, not a list. **Send rename only to the primary server per language**:

| Language | Primary | Notes |
|---|---|---|
| Python | pylsp-rope | basedpyright also emits rename but pylsp-rope's Rope-backed rename is more thorough (`docstrings=True`, in-string occurrences) |
| Rust | rust-analyzer | (only one server) |

### 11.4 Provenance reporting

Every `CodeActionDescriptor` carries `provenance: Literal["pylsp-rope", "pylsp-base", "basedpyright", "ruff", "pylsp-mypy"]`. Every `FileChange` in `RefactorResult` carries `provenance` per §10. With `O2_SCALPEL_DEBUG_MERGE=1`, descriptors include `suppressed_alternatives: list[SuppressedAlternative]` showing what the merge dropped and why.

### 11.5 Edit-attribution log

For every applied edit, scalpel appends to `.serena/python-edit-log.jsonl`:

```jsonc
{"ts": "...", "checkpoint_id": "ckpt_py_3c9", "tool": "scalpel_split_file",
 "server": "pylsp-rope", "kind": "TextDocumentEdit",
 "uri": "file:///.../calcpy/parser.py", "edit_count": 12, "version": 47}
```

Used by `scalpel_rollback` for inverse-edit replay and by E2E integration tests for trace forensics. Idempotent — replaying the log replays the exact session.

### 11.6 Multi-server schemas

```python
class MergedCodeAction(BaseModel):
    id: str
    title: str
    kind: str
    disabled_reason: str | None
    is_preferred: bool
    provenance: Literal["pylsp-rope", "pylsp-base", "basedpyright",
                        "ruff", "pylsp-mypy", "rust-analyzer"]
    suppressed_alternatives: list[SuppressedAlternative] = []

class SuppressedAlternative(BaseModel):
    title: str
    provenance: str
    reason: Literal["lower_priority", "duplicate_title", "duplicate_edit"]

class ServerTimeoutWarning(BaseModel):
    server: str
    method: str            # e.g. "textDocument/codeAction"
    timeout_ms: int        # default 2000
    after_ms: int

class MultiServerBroadcastResult(BaseModel):
    """Internal: result of fanning a request to N servers in parallel."""
    responses: dict[str, Any]   # server_id -> response
    timeouts: list[ServerTimeoutWarning]
    errors: dict[str, str]      # server_id -> error message
```

The `multi_server` module (§14.1 [10]) is the only place that knows about server identities. Below it, `WorkspaceEditApplier` sees a single merged `WorkspaceEdit` per call (with `provenance` annotations). Above it, facades see merged `MergedCodeAction` lists with `suppressed_alternatives` populated only when `O2_SCALPEL_DEBUG_MERGE=1`.

### 11.7 Semantic-equivalence requirements per merge action

Before a merge picks a winner, both candidate edits must satisfy:

1. **Apply cleanly** to the current document version (no `STALE_VERSION`).
2. **Preserve syntactic validity** — both Rust and Python strategies run a post-apply parse on the affected file (Rust: rust-analyzer's `viewSyntaxTree`; Python: `ast.parse`). Failure → drop the candidate; warn.
3. **Pass the `disabled.reason` filter** — actions with `disabled` set are preserved in the merged list (LLM sees them) but are not auto-applied.
4. **Pass the workspace-boundary path filter (§11.8)** — every `documentChanges` entry must target a path under LSP-reported `workspaceFolders` (or `O2_SCALPEL_WORKSPACE_EXTRA_PATHS`). Failure → reject the entire `WorkspaceEdit` atomically with `OUT_OF_WORKSPACE_EDIT_BLOCKED`. `changeAnnotations.needsConfirmation: true` is **advisory only** — the path filter is the load-bearing safety check.

These are the four invariants the multi-server merge must not violate. Each has a unit test in `test_multi_server.py`.

### 11.8 Workspace-boundary path filter (uniform across all LSPs)

Per [Q4 resolution](open-questions/q4-changeannotations-auto-accept.md), the WorkspaceEdit applier enforces a workspace-boundary rule **independently of any annotation** and **uniformly across all LSPs** (rust-analyzer + the three Python LSPs). The rule:

```python
def is_in_workspace(path: Path,
                    workspace_folders: list[Path],
                    extra: list[Path]) -> bool:
    target = path.resolve(strict=False)
    candidates = [f.resolve(strict=False) for f in (workspace_folders + extra)]
    return any(target.is_relative_to(c) for c in candidates)
```

For every `documentChanges` entry (every `TextDocumentEdit`, `CreateFile.uri`, `RenameFile.oldUri`/`newUri`, `DeleteFile.uri`), if `is_in_workspace(...)` is `False`, the entire `WorkspaceEdit` is rejected atomically with `error_code = "OUT_OF_WORKSPACE_EDIT_BLOCKED"` and the rejected paths in `failure.details.rejected_paths`. **No partial application.**

`workspace_folders` comes from `initialize.params.workspaceFolders` (or the fallback `rootUri`). `extra` comes from `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` (colon-separated list, optional) for vendored-dep workflows.

Python-side has a stricter interpretation: even when a path is *under* a workspace folder, it is rejected if it contains any of `.venv/`, `venv/`, `site-packages/`, `__pypackages__/`, `node_modules/` (the `implicit_exclude` set). Symmetric `extra` allowlist applies.

**Annotation handling** (advisory only):
- `OutsideWorkspace` annotation (rust-analyzer's primary `needs_confirmation: true` emitter) → surfaced in dry-run preview and audit log; the path filter does the actual rejection. Note: the path filter and the annotation are **independent** — a path can fail the boundary check without an annotation (e.g., `target/` artefacts), and a path can pass the boundary check while bearing an `OutsideWorkspace` annotation (e.g., a vendored dep added via `O2_SCALPEL_WORKSPACE_EXTRA_PATHS`).
- Non-`OutsideWorkspace` annotations with `needs_confirmation: true` (rust-analyzer's rename-shadowing case) → edit applies (path is in-workspace), but `RefactorResult.warnings += [SemanticShiftWarning(label, description, affected_paths)]` and the LLM sees the warning in the result. Recoverable via `scalpel_rollback`.

**Override.** Every facade and the dispatcher carry an explicit `allow_out_of_workspace: bool = False` argument. When the LLM passes `True`, the path filter is skipped — and Claude Code's tool-permission prompt fires automatically because the unsafe argument is plainly visible in the tool call (§11.9). No MVP facade defaults this to `True`.

### 11.9 Confirmation flow — Claude Code permission prompt integration

> **2026-04-24 user directive**: *"confirmations should work the same way as all claude cli confirmations, if possible."*

scalpel does NOT invent its own confirmation UI. Instead, scalpel exposes every unsafe behavior as an explicit boolean argument on its facades and the dispatcher. When the LLM populates such an argument with `True`, Claude Code's standard tool-permission prompt fires automatically — the same "Allow / Allow always / Deny" dialog the user already sees for `Bash`, file writes, and other unsafe MCP tool calls. This means:

1. **No in-band MCP confirmation tool.** scalpel never registers a `scalpel_confirm_*` tool. The previous `v1.1` plan to add `scalpel_confirm_annotations` is canceled.
2. **No custom approval workflow.** scalpel does not prompt the user via stdout, log files, or any other channel.
3. **Default-safe.** Every unsafe argument defaults to `False`. If the LLM never sets the argument to `True`, no permission prompt is needed and the safe path is taken.
4. **Explicit unsafe arg = the permission trigger.** When the LLM does set the argument to `True`, the *literal value* in the tool call is what Claude Code's permission UI inspects; the harness has full visibility into which scalpel facades are being asked to perform unsafe operations and against which paths.
5. **Documentation discipline.** Each scalpel facade signature explicitly types its unsafe arguments so the harness's permission UI can render an informative prompt.

**Inventory of scalpel facades carrying unsafe-operation arguments:**

| Facade | Unsafe argument | Default | What `True` does |
|---|---|---|---|
| `scalpel_apply_capability` | `allow_out_of_workspace: bool` | `False` | Skips §11.8 workspace-boundary path filter; permits edits to paths under `~/.cargo/registry/`, sysroot, etc. |
| `scalpel_split_file` | `allow_partial: bool` (existing) | `False` | Permits the file-split to commit even if some symbols cannot be relocated |
| `scalpel_rename` | `also_in_strings: bool` (existing) | `False` | Permits the rename to walk through string literals and docstrings (Rope's `docstrings=True` mode) |
| Catalog-defined deferred facades | `allow_out_of_workspace: bool` (when applicable) | `False` | Same as dispatcher |

**No other MVP facade currently carries unsafe arguments.** The list will grow only as new unsafe operations are introduced; in every case, the unsafe behavior must be exposed as an explicit boolean argument with a `False` default — no implicit "the LLM is autonomous so go ahead" path is permitted.

**Audit trail.** Every applied edit is logged to `.serena/python-edit-log.jsonl` (Python-side, §11.6) and the equivalent Rust-side log; the log records whether `allow_out_of_workspace` was `True` for that call, so post-hoc forensics can reconstruct exactly which permissions the harness granted.

**Cross-reference.** Claude Code's permission docs ([`https://code.claude.com/docs/en/permissions`](https://code.claude.com/docs/en/permissions), §"Permission system" / §"Manage permissions") describe the harness's tiered Allow / Ask / Deny model with "Yes, don't ask again" — file modifications prompt until session end, Bash commands prompt with project-scoped persistence, MCP tools follow the `mcp__<server>__<tool>` rule syntax. scalpel relies on that UI rather than reproducing it; unsafe scalpel facade calls surface as `mcp__o2-scalpel__<tool>` permission prompts on first use.

**What this replaces in the prior synthesis.** §11.7 row 4 previously read "Honor `changeAnnotations.needsConfirmation` — annotated edits surface in dry-run; auto-apply only under explicit `allow_out_of_workspace=true` (rare; default false)". The substantive policy is unchanged; what §11.9 makes explicit is *who runs the prompt*: not scalpel, but the Claude Code harness, via the explicit argument as the trigger.

---

## 12. Capability catalog and dynamic registration

### 12.1 The `scalpel_capabilities_list` tool

Computed at MCP server startup; cached per language; ~3K tokens uncompressed per language. Re-emitted on `scalpel_reload_plugins` (v1.1). Used like shell tab-completion.

`scalpel_capabilities_list("rust")` returns ~80 entries (158 assists filtered by relevance to refactoring intent + 36 custom extensions). `scalpel_capabilities_list("python")` returns ~50 entries (9 pylsp-rope commands + 10 library-bridge ops + 4 basedpyright actions + 3 ruff kinds + composite intent ids).

Each row is a `CapabilityDescriptor`:

```python
class CapabilityDescriptor(BaseModel):
    capability_id: str             # "rust.refactor.extract.module"
    title: str                     # "Extract symbols into module"
    applies_to_kinds: list[str]    # ["function","struct","enum","impl","trait"]
    lsp_kind: str                  # "refactor.extract.module"
    lsp_source: str                # "rust-analyzer" / "pylsp-rope" / etc.
    preferred_facade: str | None   # "scalpel_split_file" or null
```

`preferred_facade` lets the LLM short-circuit: if a capability has a high-level facade, the LLM should prefer it (better defaults, better errors, hallucination-resistant inputs).

### 12.2 Deferred-loading mechanism

The 11 deferred specialty tools are registered with `defer_loading: true` per Anthropic Tool Search docs. They appear in Tool Search results when relevant but do not load into cold context.

Discovery flow at MCP server startup:

```python
def list_tools(...):
    base = ALWAYS_ON_TOOLS.copy()
    for lang, strategy in registry.activated_strategies():
        for tool in strategy.deferred_tools():
            base.append({**tool, "defer_loading": True})
    return base
```

A deferred tool appears in `scalpel_capabilities_list` with `preferred_facade=<deferred-tool-name>`. The LLM that calls `capabilities_list` first sees the deferred tool exists; Tool Search retrieves its full schema when the LLM invokes it.

### 12.3 Catalog drift test (MVP gate)

CI step in `test/baselines/`:

```
pytest test/baselines/test_capability_catalog_drift.py
```

Diffs live `scalpel_capabilities_list("rust")` against `test/baselines/capability_catalog_rust.json`, and `scalpel_capabilities_list("python")` against `test/baselines/capability_catalog_python.json`. Empty diff = pass. Any addition / removal / rename = fail (re-baseline + add integration test, or revert).

Pinning ensures the catalog is stable: `rust-analyzer ^v0.3.18xx`, and the entire Python LSP stack exact-pinned per [Q3 resolution](open-questions/q3-basedpyright-pinning.md): `basedpyright==1.39.3`, `python-lsp-server==1.13.1`, `pylsp-rope==0.1.17`, `pylsp-mypy==0.7.0`, `python-lsp-ruff==2.2.2`, `ruff==0.14.4`, `rope==1.13.0`. Re-baseline on the §8 bump procedure described in the Q3 resolution doc (monthly stale-check nag + four basedpyright integration tests + catalog-drift gate + new title-stability + diagnostic-count fixtures).

### 12.4 How the LLM discovers and uses long-tail capabilities

Recommended SKILL.md prompt: "Always start unfamiliar tasks by calling `scalpel_capabilities_list(language=...)`. The result tells you which capability_ids exist and which have ergonomic facades."

The LLM workflow:

```
turn 1: scalpel_capabilities_list(language="rust", filter_kind="refactor.extract")
        → [{capability_id: "rust.refactor.extract.module", preferred_facade: "scalpel_split_file"},
           {capability_id: "rust.refactor.extract.function", preferred_facade: "scalpel_extract"},
           ...]

turn 2: scalpel_capability_describe(capability_id="rust.refactor.extract.struct_from_variant")
        → {description: "...", params_schema: {...}, example_invocation: {...}}

turn 3: scalpel_apply_capability(
          capability_id="rust.refactor.extract.struct_from_variant",
          file="calcrs/src/lib.rs",
          range_or_name_path={...},
          dry_run=True)
        → RefactorResult{applied: false, preview_token: "preview_5e2", ...}
```

If the LLM forgets `capabilities_list` exists, `scalpel_apply_capability` with an unknown `capability_id` returns `CAPABILITY_NOT_AVAILABLE` with `candidates[]` populated by Levenshtein distance — the recovery path teaches the LLM about the catalog.

---

### 12.5 Error-code taxonomy (11 codes)

The narrow round had 6 codes; full coverage adds 4 (initial round) and 1 more from [Q4 resolution](open-questions/q4-changeannotations-auto-accept.md). Each has a one-line repair pattern; the LLM uses these as retry-decision signals.

| # | Code | When | Repair pattern (one line) | Retryable | Same-turn budget |
|---|---|---|---|---|---|
| 1 | `STALE_VERSION` | File version drifted between operations | Re-issue the call; idempotent facades treat moved symbols as no-ops | yes | ×2 |
| 2 | `NOT_APPLICABLE` | LSP has no action of requested kind here, or `disabled.reason` set | Read `reason`; widen range or change cursor; retry once | yes | ×1 |
| 3 | `INDEXING` | LSP cold-starting / re-indexing | Wait `estimated_wait_ms`; or call `scalpel_workspace_health` | yes (after wait) | ×1 |
| 4 | `APPLY_FAILED` | WorkspaceEdit apply errored, rolled back | Inspect `failed_stage`; adjust `reexport_policy` to explicit and retry | conditional | ×1 |
| 5 | `PREVIEW_EXPIRED` | `preview_token` past TTL or invalidated by file change | Re-issue the `dry_run=true` call | yes | ×2 |
| 6 | `SYMBOL_NOT_FOUND` | Name-path resolved 0 or >1 (shape unified per v1) | Pick from `candidates[]`; retry with exact path | yes | ×2 |
| 7 | `CAPABILITY_NOT_AVAILABLE` *(new)* | `capability_id` not registered for the file's language | Call `scalpel_capabilities_list(language=...)`; pick a registered id | yes | ×1 |
| 8 | `SERVER_REQUIRED` *(new)* | Capability needs an LSP whose server is not reachable | Run `scalpel_workspace_health`; install/start the LSP plugin | conditional | 0 (escalate) |
| 9 | `MULTIPLEX_AMBIGUOUS` *(new)* | Cross-language operation matched assists in 2+ LSPs | Pick `language` explicitly; or scope `files` to one language | yes | ×1 |
| 10 | `TRANSACTION_ABORTED` *(new)* | A step in `dry_run_compose` failed; later steps did not run | Inspect `failed_step_index`; fix that step's params; recompose | yes | ×1 |
| 11 | `OUT_OF_WORKSPACE_EDIT_BLOCKED` *(new — Q4)* | Some `documentChanges` entry's target path falls outside LSP-reported `workspaceFolders` (and the optional `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` allowlist) | Inspect `rejected_paths`; narrow scope to in-workspace files, or re-invoke via `scalpel_apply_capability(..., allow_out_of_workspace=True)` to trigger Claude Code's permission prompt (§11.9) | yes (with explicit unsafe-arg) | ×1 |

Cumulative same-turn retry budget: ≤3 retries across all errors before the LLM should escalate to the user. Documented in the always-on tools' SKILL.md.

Error response shape:

```json
{
  "error": "CAPABILITY_NOT_AVAILABLE",
  "message": "capability_id 'rust.refactor.lifetime.elide' not registered for python",
  "hint": "Call scalpel_capabilities_list(language='python') to discover available capabilities.",
  "retryable": true,
  "candidates": ["python.refactor.extract.function","python.refactor.inline.variable"]
}
```

`candidates[]` is populated by Levenshtein distance for `CAPABILITY_NOT_AVAILABLE` and by scope walk for `SYMBOL_NOT_FOUND`.

### 12.6 Telemetry trace event schema

Per call, scalpel logs to `.serena/telemetry/calls.jsonl` (redact-by-default; user-disable-able via `O2_SCALPEL_TELEMETRY=0`):

```python
class TraceEvent(BaseModel):
    ts: float
    session_id: str
    tool_name: str
    language: str | None
    capability_id: str | None
    args_summary: dict           # structural counts; no file contents, no symbol names
    disposition: Literal["ok", "err", "no_op"]
    error_code: str | None
    duration_ms: int
    checkpoint_id: str | None
    transaction_id: str | None
    preview_token_used: bool
    indexing_ready: bool
    rules_fired: list[str]
    lsp_ops_total_ms: int
    tool_search_expanded: list[str]
```

Privacy posture: no file contents, no symbol names (hashed if needed), local-only by default. JSONL format chosen so a simple `jq` + `duckdb` pipeline post-MVP produces tool-popularity histograms (promote/demote candidates), capability-popularity histograms (promote to facade), per-tool error rates, perf regression detection, and `defer_loading` validation (`tool_search_expanded` per turn).

---

## 13. Pre-MVP spikes (canonical merged list)

12 spikes total (Rust 6 + Python 6, deduplicated; 5 are blocking). Each spike has: question, falsifiable answer shape, fallback if pessimistic. Order by blocking-status then by dependency. Q1, Q3, Q4 resolutions added P5a, P3a (basedpyright bump procedure smoke test), and P-WB (workspace-boundary fixture suite).

| ID | Title | Blocking? | Question | Falsifiable answer shape | Fallback |
|---|---|---|---|---|---|
| **S1** | `multilspy` `$/progress` forwarding (Rust + Python) | **blocking** | Does `solidlsp` see `$/progress` notifications with token prefixes (`rustAnalyzer/Indexing`, `pylsp:`, `basedpyright:`, `ruff:`)? | (A) all arrive (best); (B) only begin/end (works coarse); (C) nothing (need shim) | (C): +30 LoC notification-tap shim in `solidlsp/lsp_protocol_handler/server.py` |
| **S3** | `applyEdit` reverse-request fires on `CodeAction.command` paths | **blocking** | Does rust-analyzer (or pylsp-rope) issue `workspace/applyEdit` reverse-request when an action is `command:` rather than `edit:`? | (A) reverse-request fires (full handler required); (B) edit embedded in `executeCommand` response (handler can stay minimal) | (A) is the assumption; +80 LoC real handler |
| **P1** | pylsp-rope unsaved-buffer behavior | **blocking** | Does pylsp-rope honor `didChange` without `didSave`? Or does it read disk? | (A) honors didChange (preferred); (B) reads disk → must `didSave({includeText: true})` before every code-action call | (B): +1 round-trip per call; eliminates staleness class |
| **P2** | Conflicting `source.organizeImports` between pylsp-rope and ruff | **blocking** | Do both produce the same output on `calcpy.py`? | Compare, document differences | Lock merge winner: ruff. Strategy-level config `engine: {"ruff", "rope"}` lets users pin |
| **P5a** | pylsp-mypy stale-diagnostic rate under `live_mode: false` + `dmypy: true` + scalpel-injected per-step `didSave` (replaces P5; per [Q1 resolution](open-questions/q1-pylsp-mypy-live-mode.md)) | **blocking** | Across 12 internal `apply()` steps on `calcpy`, does pylsp-mypy diagnostics-delta match a ground-truth `dmypy run` oracle within 5%, AND does p95 didSave→diagnostic latency stay under 1 s? | (A) pass both thresholds (ship MVP with pylsp-mypy in active set); (B) latency 1–3 s p95 (ship with documented warning); (C) staleness >5% OR latency >3 s p95 OR cache-corruption observed | (C): drop pylsp-mypy from MVP active server set; basedpyright sole type-error source per §11.1. Document in CHANGELOG. |
| **S2** | `SnippetTextEdit` round-trip with `snippetTextEdit:false` | non-blocking | Do all assists honor `false`? | (A) all honor (defensive strip path only); (B) some ignore (mandatory strip path) | (B): +50 LoC regex with edge-case handling |
| **S4** | `experimental/ssr` upper bound on `WorkspaceEdit` size | non-blocking | What's the max edit count + memory for a broad SSR pattern? | Bounds documented | Add `max_edits: int = 500` parameter to `scalpel_rust_ssr` |
| **S5** | `rust-analyzer/expandMacro` works on proc macros | non-blocking | Does it expand `#[derive(...)]` proc-macros, or only `macro_rules!`? | (A) both; (B) declarative only | (B): facade errors on proc-macro positions with `not_supported_for_proc_macros` |
| **S6** | `auto_import` apply branch — `command` vs `edit` resolve shape | non-blocking | Does resolve always populate `edit`, or sometimes only `command`? | (A) always `edit`; (B) sometimes `command` only | (B): +40 LoC two-shape branch in applier |
| **P3** | Rope vs PEP 695 / PEP 701 / PEP 654 syntax | non-blocking | Does Rope's parser handle 3.12+ syntax? | Per-PEP outcome | Document supported Python = 3.10–3.12; pin Rope; 3.13+ best-effort |
| **P3a** | basedpyright bump procedure validation (per [Q3 resolution](open-questions/q3-basedpyright-pinning.md)) | non-blocking (one-shot pre-MVP) | Run §15 fixtures (catalog drift + title-stability + diagnostic-count + 4 basedpyright integration tests + E1-py/E3-py/E9-py/E10-py) on the pinned `basedpyright==1.39.3` and capture green-bar baseline | Green-bar baseline established | If baseline fails on the pinned version, treat as a blocker — investigate before MVP commit |
| **P-WB** | Workspace-boundary rule on real fixtures (per [Q4 resolution](open-questions/q4-changeannotations-auto-accept.md)) | non-blocking (one-shot pre-MVP) | Do the three fixtures in `tests/test_workspace_boundary.py` (registry-edit reject, rename-shadowing soft-warn, `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` opt-in) green-bar against `calcrs`? | All three green | Tighten `is_in_workspace` canonicalization; revisit on Windows where `Path.resolve()` semantics differ |

P4 (basedpyright `relatedInformation` richness) and P6 (three-server rename convergence) from the Python list are non-blocking and observation-only; folded into the same execution as P1/P2/P3/P5a.

**Pessimistic-path combined cost**: ~+250 LoC of remediation across spikes. Already absorbed in §8.7 / §9.7 LoC tables; the Q1/Q3/Q4 incremental costs (~135 + ~250 + ~70 ≈ ~455 LoC) are accounted for in §14.

---

## 14. Staged delivery plan

Stage 1 (Small) + Stage 2 (Medium) = MVP cut. Stage 3 (Large) = v0.2.0. No time estimates per CLAUDE.md.

### 14.1 Stage 1 (Small — primitive reach + capability catalog + rollback)

Goal: every assist family **reachable** via `scalpel_apply_capability`. Stage 1 alone satisfies "full reach" but lacks ergonomic facades.

Files (new or modified) and LoC:

| # | File | Type | LoC | Stage |
|---|---|---|---|---|
| 1 | `vendor/serena/src/solidlsp/ls.py` (codeAction, resolve, executeCommand, applyEdit, $/progress, multi-server hooks) | Modify | +470 | 1 |
| 2 | `vendor/serena/src/solidlsp/lsp_protocol_handler/server.py` | Modify | +60 | 1 |
| 3 | `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py` | Modify | +20 | 1 |
| 4 | `vendor/serena/src/solidlsp/language_servers/python_lsp.py` (multi-server: pylsp, basedpyright, ruff) | New | +250 | 1 |
| 5 | `vendor/serena/src/serena/code_editor.py` (applier upgrade — full WorkspaceEdit matrix) | Modify | +500 | 1 |
| 6 | `vendor/serena/src/serena/refactoring/checkpoints.py` | New | +150 | 1 |
| 7 | `vendor/serena/src/serena/refactoring/transactions.py` | New | +180 | 1 |
| 8 | `vendor/serena/src/serena/refactoring/lsp_pool.py` | New | +180 | 1 |
| 9 | `vendor/serena/src/serena/refactoring/discovery.py` | New | +110 | 1 |
| 10 | `vendor/serena/src/serena/refactoring/multi_server.py` (priority + dedup merge rule) | New | +430 | 1 |
| 11 | `vendor/serena/src/serena/refactoring/language_strategy.py` (Protocol + mixins) | New | +250 | 1 |
| 12 | `vendor/serena/src/serena/refactoring/rust_strategy.py` (skeleton + family declarations + extension whitelist) | New | +300 | 1 |
| 13 | `vendor/serena/src/serena/refactoring/python_strategy.py` (skeleton + multi-server orchestration + interpreter discovery + Rope library bridge) | New | +420 + 280 = +700 | 1 |
| 14 | `vendor/serena/src/serena/refactoring/__init__.py` (registry) | New | +25 | 1 |
| 15 | `vendor/serena/src/serena/refactoring/capability_catalog.py` | New | +200 | 1 |
| 16 | `vendor/serena/src/serena/tools/primitive_tools.py` (`scalpel_capabilities_list`, `scalpel_capability_describe`, `scalpel_apply_capability`, `scalpel_dry_run_compose`, `scalpel_rollback`, `scalpel_transaction_rollback`, `scalpel_workspace_health`, `scalpel_execute_command`) | New | +600 | 1 |
| 17 | All MVP fixtures (calcrs + 18 RA companions; calcpy + 4 sub-fixtures) | New (trees) | ~5,240 fixtures | 1 |
| 18 | Unit tests (applier ~80 tests, multi-server, catalog, strategies, transactions) | New | ~1,750 | 1 |
| 19 | Integration tests per assist family (15 RA families + 16 Python ops = 31 modules, ~70 sub-tests) | New | ~2,800 | 1 |
| 20 | `o2-scalpel/.claude-plugin/plugin.json` + `.mcp.json` | New | +35 | 1 |

**Stage 1 totals**: ~5,140 logic + 5,240 fixtures + 4,550 tests = **~14,930 LoC**.

**Stage 1 exit gate**:
- `scalpel_capabilities_list` returns the full catalog and matches the baseline.
- Every assist family has a green integration test reaching the assist via `scalpel_apply_capability`.
- `scalpel_rollback` and `scalpel_transaction_rollback` round-trip on `kitchen_sink_*` workspaces.
- All 4 LSP processes spawn on first call without exceeding the §16 RAM budget.
- 6 primitive/safety/diag tools reachable from Claude Code session.

### 14.2 Stage 2 (Medium — top-decile ergonomic facades)

Goal: the 5 most-used families have named ergonomic facades. The LLM rarely needs `scalpel_apply_capability` for common workflows.

| # | File | Type | LoC |
|---|---|---|---|
| 21 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `scalpel_split_file` (Rust + Python composition via Rope MoveGlobal) | New | +700 |
| 22 | …—`scalpel_imports_organize` (multi-server consolidator on Python) | New | +280 |
| 23 | …—`scalpel_extract` (multiplexer over RA + Rope; target enum) | New | +280 |
| 24 | …—`scalpel_inline` (multiplexer over RA + Rope; target + scope enum) | New | +280 |
| 25 | …—`scalpel_rename` (Serena's rename_symbol re-skin; cross-file; module-rename via Rope MoveModule) | New | +120 |
| 25a | `vendor/serena/src/serena/tools/primitive_tools.py` — `scalpel_transaction_commit` (13th always-on tool, [Q2 resolution](open-questions/q2-12-vs-13-tools.md); reuses transaction store) | New | +60 |
| 25b | Q1 per-step synthetic `didSave` injection ([Q1 resolution](open-questions/q1-pylsp-mypy-live-mode.md)) — `python_strategy.py` (~40), `multi_server.py` `broadcast_did_save` (~15), tests (~80) | New/Modify | +135 |
| 25c | Q4 workspace-boundary path filter ([Q4 resolution](open-questions/q4-changeannotations-auto-accept.md)) — applier filter, `RefactorResult` schema additions, `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` parsing | New/Modify | +70 |
| 26 | E2E harness (`test/e2e/conftest.py`, multi-server fixture wiring, four-LSP startup) | New | +250 |
| 27 | E2E scenarios E1, E1-py, E2, E3, E9, E9-py, E10, E11 (extract round-trip), E12 (inline) | New | +900 |
| 27a | Q3 catalog-gate-blind-spot fixtures ([Q3 resolution](open-questions/q3-basedpyright-pinning.md)) — `test_action_title_stability.py` (~80), `test_diagnostic_count_calcpy.py` (~120), `make check-deps-stale` target + CI nag (~50) | New | +250 |
| 27b | Q4 workspace-boundary integration tests — `tests/test_workspace_boundary.py` (registry-edit reject, rename-shadowing soft-warn, `EXTRA_PATHS` opt-in) | New | +120 |

**Stage 2 totals (revised)**: ~2,025 logic (+265 vs. pre-resolutions) + 0 fixtures + 1,520 tests (+370 vs. pre-resolutions) = **~3,545 LoC** (+735 vs. pre-resolutions). The increase is driven by Q1 (+135), Q3 (+250), Q4 (+190), and Q2 (+60).

**Stage 2 exit gate** (= **MVP cut**):
- 9 MVP E2E scenarios green (E1, E1-py, E2, E3, E9, E9-py, E10, E11, E12).
- 5 ergonomic facades pass per-facade integration tests.
- Stage 1 gate still green.
- `pytest -m e2e` completes within wall-clock budget on CI runner.
- `O2_SCALPEL_DISABLE_LANGS={rust,python}` opt-out paths exercised in degradation tests.

### 14.3 Stage 3 (Large — v0.2.0; remaining ergonomic facades + long-tail E2E)

Goal: every remaining ergonomic facade in §4 implemented; every E2E in §15 green; capability catalog stable.

| # | File | Type | LoC |
|---|---|---|---|
| 28 | `refactoring_tools.py` — Stage 3 Rust facades (`convert_module_layout`, `change_visibility`, `tidy_structure`, `change_type_shape`, `change_return_type`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `generate_trait_impl_scaffold`, `generate_member`, `expand_macro`, `verify_after_refactor`) | New | +1,650 |
| 29 | `refactoring_tools.py` — Stage 3 Python facades (`convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `auto_import` specialized, `fix_lints`, `ignore_diagnostic`) | New | +640 |
| 30 | E2E scenarios E13–E16 + E4-py / E5-py / E8-py / E11-py | New | +900 |
| 31 | Server-extension whitelist tests | New | +200 |
| 32 | README + install docs | Modify | +150 |

**Stage 3 totals**: ~3,540 logic + 0 fixtures + 1,100 tests = **~4,640 LoC**.

**Stage 3 exit gate** (= **v0.2.0**): every facade in §4 reachable as a named tool; all 15 E2E scenarios green.

### 14.4 LoC roll-up

| Stage | Logic | Tests | Fixtures | Total |
|---|---|---|---|---|
| Stage 1 | ~5,140 | ~4,550 | ~5,240 | ~14,930 |
| Stage 2 (incl. Q1/Q2/Q3/Q4 deltas) | ~2,025 | ~1,520 | 0 | ~3,545 |
| **MVP cut (1+2)** | **~7,165** | **~6,070** | **~5,240** | **~18,475** |
| Stage 3 | ~3,540 | ~1,100 | 0 | ~4,640 |
| **v0.2.0 (1+2+3)** | **~10,705** | **~7,170** | **~5,240** | **~23,115** |
| Fully loaded (incl. CI scaffolding, lint config, type stubs, doc strings, LSP-init smoke tests at ~54% loading factor) | | | | **~28,200 (MVP); ~35,500 (v0.2.0)** |

The MVP figure is **~3.3× the narrow MVP's ~5,640 LoC** (the Q1/Q3/Q4 resolutions added ~735 LoC over the original synthesis). The fully-loaded MVP figure is at the upper end of the directive's stated 12,000–20,000 band when test scaffolding is included.

### 14.5 Dependency graph + parallelization

CPU cores = 8 on this machine; CLAUDE.md says max parallel = cores.

```
Stage 1: [1, 2, 3]  (parallel) → [4]
                    [5] ← [1]
                    [6] ← [5]
                    [7] ← [5]
                    [8] ← [1]
                    [9]
                    [10] ← [1, 4]
                    [11]
                    [12] ← [11]
                    [13] ← [11, 10]
                    [14] ← [12, 13]
                    [15] ← [12, 13]
                    [16] ← [5, 6, 7, 15]
                    [17] (fixtures, parallel with all above)
                    [18, 19] ← [12, 13, 15]
                    [20] ← [16]

Stage 2: [21, 22, 23, 24, 25] ← Stage 1   (parallel after Stage 1 exits)
         [26] ← [21..25]
         [27] ← [26]

Stage 3: [28, 29] ← Stage 2   (parallel)
         [30] ← [28, 29]
         [31, 32] ← [28, 29]
```

TDD ordering: write spike outcomes (§13) → write applier matrix tests (§4.6) → write applier (§5 of design) → write `LanguageStrategy` Protocol (§7) → write strategy stubs → write multi-server merge rule (§11) tests → write merge rule → write capability catalog → write primitive tools → write integration tests per family → write fixtures → write Stage 2 facades → write E2E scenarios → green-bar.

---

## 15. MVP Test Gates

### 15.1 9-scenario E2E list (canonical)

Reconciled across Rust-specialist's 11 and Engineering-scope's 9. The MVP-blocking 9:

| # | Scenario | Languages | Description |
|---|---|---|---|
| E1 | Happy-path 4-way split | Rust | Split `calcrs/src/lib.rs` into `ast`/`errors`/`parser`/`eval`. `cargo test` byte-identical |
| E1-py | Happy-path 4-way split | Python | Split `calcpy/calcpy.py` into `ast`/`errors`/`parser`/`evaluator`. `pytest -q` byte-identical |
| E2 | Dry-run → inspect → adjust → commit | both | `dry_run=true` returns same `WorkspaceEdit` `dry_run=false` applies; diagnostics_delta matches |
| E3 | Rollback after intentional break | both | `scalpel_rollback(checkpoint_id)` restores byte-identical pre-refactor tree |
| E9 | Semantic equivalence | both | Pre/post-refactor `cargo test` / `pytest --doctest-modules` byte-identical on `calcrs` and `calcpy` |
| E9-py | (Python lane of E9) | python | included in E9 |
| E10 | `scalpel_rename` regression | both | Existing `rename_symbol` E2E passes byte-for-byte |
| E10-py | `__all__` preservation | python | `from calcpy import *` yields same name set post-refactor |
| E11 | `scalpel_extract` round-trip | both | Extract function + variable + type-alias on Rust; extract method + variable on Python; verify diagnostics-delta |
| E12 | `scalpel_inline` round-trip with `scope=all_callers` | both | Inline function across multiple call-sites; verify diagnostics-delta + checkpoint replay |
| E13-py | Multi-server merge — organize-imports | python | All three servers active; verify only one organize-imports action surfaces (priority + dedup applied) |

**Total MVP E2E gates: 9** (E1, E1-py, E2, E3, E9 (covers E9-py via dual-lane), E10 (covers E10-py), E11, E12, E13-py).

### 15.2 Per-assist-family integration test rule

One integration test module per assist family. Each module contains 2–4 sub-tests sharing a fixture.

| Family | Test module | Approx LoC | Fixture |
|---|---|---|---|
| RA: module/file boundary | `test_module_file_boundary.py` | ~200 | `inline_modules.rs`, `mod_rs_swap.rs` |
| RA: extractors | `test_extractors_rust.py` | ~120 | `ra_extractors.rs` |
| RA: inliners | `test_inliners_rust.py` | ~120 | `ra_inliners.rs` |
| RA: visibility & import hygiene | `test_visibility_imports.py` | ~150 | `cross_visibility.rs`, `ra_imports.rs` |
| RA: ordering | `test_ordering_rust.py` | ~80 | `ra_ordering.rs` |
| RA: generators | `test_generators_rust.py` | ~120 | `ra_generators_*.rs` |
| RA: replace | `test_replace_rust.py` | ~80 | (kitchen_sink) |
| RA: convert | `test_convert_rust.py` | ~80 | `ra_convert_*.rs` |
| RA: micro-rewrites | `test_micro_rewrites_rust.py` | ~80 | (kitchen_sink) |
| RA: pattern | `test_pattern_rust.py` | ~80 | `ra_pattern_destructuring.rs` |
| RA: lifetimes | `test_lifetimes_rust.py` | ~80 | `ra_lifetimes.rs` |
| RA: term-search | `test_term_search_rust.py` | ~60 | `ra_term_search.rs` |
| RA: diagnostic-driven quickfixes | `test_quickfix_rust.py` | ~150 | `flycheck_diagnostics_rs/` |
| RA: rename | `test_rename_rust.py` | ~80 | (kitchen_sink) |
| RA: macro expand | `test_expand_macro.py` | ~80 | `ra_macros.rs` |
| RA: SSR | `test_ssr_rust.py` | ~100 | `ra_ssr.rs` |
| Py: rope.extract.method | `test_extract_method_py.py` | ~80 | `kitchen_sink_py` |
| Py: rope.extract.variable | `test_extract_variable_py.py` | ~60 | `kitchen_sink_py` |
| Py: rope.inline | `test_inline_py.py` | ~80 | `kitchen_sink_py` |
| Py: rope.local_to_field | `test_local_to_field_py.py` | ~60 | `kitchen_sink_py` |
| Py: rope.method_to_method_object | `test_m2mo_py.py` | ~60 | `kitchen_sink_py` |
| Py: rope.use_function | `test_use_function_py.py` | ~60 | `kitchen_sink_py` |
| Py: rope.introduce_parameter | `test_introduce_parameter_py.py` | ~60 | `kitchen_sink_py` |
| Py: rope.quickfix.generate | `test_quickfix_generate_py.py` | ~60 | `kitchen_sink_py` |
| Py: rope.organize_import | `test_organize_import_py.py` | ~80 | `kitchen_sink_py` |
| Py: rope library Move | `test_move_global_py.py` | ~120 | `kitchen_sink_py` |
| Py: rope library MoveModule | `test_rename_module_py.py` | ~100 | `kitchen_sink_py` |
| Py: basedpyright organizeImports | `test_basedpyright_imports.py` | ~80 | `kitchen_sink_py` |
| Py: basedpyright auto-import | `test_basedpyright_autoimport.py` | ~100 | `kitchen_sink_py` |
| Py: basedpyright pyright-ignore | `test_basedpyright_ignore.py` | ~80 | (mypy_diag) |
| Py: basedpyright type-annotate | `test_basedpyright_annotate.py` | ~80 | (mypy_diag) |
| Py: ruff source.fixAll | `test_ruff_fix_all.py` | ~100 | (ruff_diag) |
| Py: ruff per-rule quickfix | `test_ruff_per_rule.py` | ~80 | (ruff_diag) |

**Total: 32 modules × ~2.2 sub-tests = ~70 sub-tests; ~2,800 LoC.**

### 15.3 Unit test rule (~80 WorkspaceEdit shape × options matrix)

Exhaustive matrix from §4.6: 80 unit tests on `WorkspaceEditApplier` alone. Plus ~40 unit tests on multi-server merge / catalog / strategies / transactions = ~120 unit sub-tests, ~1,750 LoC.

### 15.4 Capability-catalog drift test

`test/baselines/test_capability_catalog_drift.py` diffs `scalpel_capabilities_list("rust")` and `("python")` JSON output against the checked-in baseline. Empty diff = pass. **MVP gate.**

### 15.4a basedpyright catalog-gate blind-spot fixtures (Q3)

Per [Q3 resolution](open-questions/q3-basedpyright-pinning.md), the catalog-drift gate catches additions/removals/renames but misses *title-text drift* and *diagnostic-count drift*. Two new fixtures plug these blind spots and are MVP gates on every basedpyright bump:

- `test/integration/python/test_action_title_stability.py` — snapshot-tests literal title strings basedpyright emits for the four MVP action kinds (`source.organizeImports`, `quickfix.basedpyright.autoimport`, `quickfix.basedpyright.pyrightignore`, `source.organizeImports.basedpyright`). ~80 LoC; ~2 s runtime.
- `test/integration/python/test_diagnostic_count_calcpy.py` — asserts basedpyright emits ≤ N diagnostics on `calcpy` baseline (catches v1.32.0 / v1.39.0-style diagnostic-count drift). ~120 LoC; ~5 s runtime.

Plus a non-blocking `make check-deps-stale` CI nag job for 60-day stale pins (~50 LoC).

### 15.4b Workspace-boundary integration tests (Q4)

Per [Q4 resolution](open-questions/q4-changeannotations-auto-accept.md), three integration tests in `tests/test_workspace_boundary.py` lock the workspace-boundary path filter behavior. **MVP gate.**

| Test | What it asserts |
|---|---|
| `test_ssr_rejects_registry_edit` | A synthesized `WorkspaceEdit` whose `documentChanges` includes a path under `~/.cargo/registry/` is atomically rejected with `OUT_OF_WORKSPACE_EDIT_BLOCKED`; the in-workspace file is NOT modified; rejected path appears in `failure.details.rejected_paths`; the `OutsideWorkspace` annotation alone does not gate (path filter does). |
| `test_rename_shadowing_warns_but_applies` | A non-`OutsideWorkspace` `needsConfirmation: true` annotation (rename-shadowing case) does NOT block the apply; `RefactorResult.warnings` contains a `SemanticShiftWarning` with the label. |
| `test_extra_paths_opt_in` | Setting `O2_SCALPEL_WORKSPACE_EXTRA_PATHS=<vendored-dir>` allows edits in the vendored path; warning still emitted but apply succeeds. |

Cost: ~120 LoC. Independent of rust-analyzer's exact label text — keyed on annotation id `"OutsideWorkspace"` and `needs_confirmation: true`, so the tests survive RA version bumps.

### 15.5 Test count summary

| Tier | Count | LoC |
|---|---|---|
| Unit (sub-tests) | ~120 | ~1,750 |
| Integration (sub-tests) | ~70 | ~2,800 |
| E2E | 9 | ~900 |
| Catalog drift | 2 (rust, python) | ~50 |
| basedpyright catalog-gate blind-spot fixtures (Q3) | 2 | ~250 |
| Workspace-boundary integration tests (Q4) | 3 | ~120 |
| **Total tests** | **~206** | **~5,870** |

Green-bar definition: all ~206 tests pass in a single CI run. Retries allowed only once per test; two retries = flaky = MVP not done.

---

## 16. Resource floor and degradation

### 16.1 24 GB recommended (canonical)

Per-LSP RSS on the `calcrs+calcpy` fixtures:

| Process | Purpose | Memory (fixtures) | Memory (real workspace) |
|---|---|---|---|
| Claude Code's built-in rust-analyzer | Read-only nav | ~500 MB | ~4–8 GB |
| **Scalpel's rust-analyzer** | Refactor mutations (separate `cargo.targetDir`) | ~500 MB | ~4–8 GB |
| Claude Code's built-in pyright (or basedpyright) | Read-only nav | ~300 MB | ~600 MB |
| **Scalpel's pylsp** + plugins | Refactor primary | ~250 MB | ~500 MB |
| **Scalpel's basedpyright** | Diagnostics + auto-import secondary | ~300 MB | ~600 MB |
| **Scalpel's ruff server** | Lint autofix tertiary | ~80 MB | ~150 MB |
| Scalpel MCP server (Python) | Orchestration | ~300 MB | ~300 MB |
| OS + Claude Code + editor | — | ~3 GB | ~3 GB |

**Active aggregate on `calcrs+calcpy`: ~5.4 GB.** **Active on real workspace (large Rust + medium Python): ~17–22 GB.**

### 16.2 16 GB degradation path

Documented opt-outs (set in env or `~/.config/o2.scalpel/config.toml`):

| Flag | Effect | Loss |
|---|---|---|
| `O2_SCALPEL_DISABLE_LANGS=rust` | Skip rust-analyzer in scalpel; CC's read-only RA still works; `Edit` tool for writes | All Rust facades return `failure: language_disabled_by_user` |
| `O2_SCALPEL_DISABLE_LANGS=python` | Skip Python LSP stack; CC's read-only pyright still works; `Edit` for writes | All Python facades return same |
| `O2_SCALPEL_DISABLE_SERVERS=ruff` | Python keeps pylsp + basedpyright | Loses ~770 ruff-only lint rules; `fix_lints` falls back to autopep8 (~30 rules); `source.fixAll.ruff` returns `kind unsupported` |
| `O2_SCALPEL_DISABLE_SERVERS=basedpyright` | Python keeps pylsp + ruff | Loses Pylance-port auto-import richness; falls back to rope_autoimport |
| `O2_SCALPEL_LAZY_SPAWN=1` (default on) | Defer LSP spawn until first language-specific facade call | None (default) |
| `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS=600` | Reclaim idle LSP RAM after 10 min | None (default) |
| `O2_SCALPEL_ISOLATE_CACHES=1` | basedpyright + ruff caches under `${CLAUDE_PLUGIN_DATA}/` | +100 MB disk |
| `scalpel.lsp.<lang>.disable=true` in TOML | Same as `O2_SCALPEL_DISABLE_LANGS=<lang>` | Same |

### 16.3 MVP gate per resource floor

- On a 24 GB dev laptop with all four scalpel LSPs eager-spawned on `calcrs+calcpy`, total scalpel-attributable RSS under 8 GB.
- On a 16 GB CI runner with **no opt-outs**, full E2E suite completes within wall-clock budget (≤ 12 min, accounting for RA cold start).
- On a 16 GB dev laptop with `O2_SCALPEL_DISABLE_LANGS=rust`, scalpel's Python path works against `calcpy` and the relevant Python E2E scenarios pass.

### 16.4 Startup wall-clock budget

| Phase | Budget | Notes |
|---|---|---|
| MCP server boot | <500ms | Python interpreter startup + tool registration |
| Plugin-cache discovery | <200ms | `~/.claude/plugins/cache/**/.lsp.json` walk |
| Lazy-spawn rust-analyzer (first use, fixture) | ~10s | `cargo metadata` + initial index |
| Lazy-spawn rust-analyzer (real workspace, 200+ crates) | up to 8 min | RA cold-start floor; documented |
| Lazy-spawn pylsp+plugins (first use, fixture) | ~5s | Plugin loading dominates |
| Lazy-spawn basedpyright (first use, fixture) | <1s | |
| Lazy-spawn ruff server (first use, fixture) | <100ms | |
| First `scalpel_extract` call (after spawn) | <1s | |
| First `scalpel_apply_capability` call (after spawn) | <1s | |
| E2E run wall-clock (9 scenarios on calcrs+calcpy) | 4–8 min on CI | Dominated by RA cold start + multi-LSP coordination |

### 16.5 Cache isolation policy

| Server | Cache location (default) | Mitigation under `O2_SCALPEL_ISOLATE_CACHES=1` |
|---|---|---|
| rust-analyzer | `<project>/target/` shared with cargo | `cargo.targetDir = ${CLAUDE_PLUGIN_DATA}/ra-target` per Q12 |
| pylsp + rope_autoimport | None on disk by default; `memory: true` | Already isolated |
| basedpyright | `~/.cache/basedpyright/` typed-stub cache | Override via `XDG_CACHE_HOME` for the scalpel session |
| ruff | `.ruff_cache/` in project root | Override via `RUFF_CACHE_DIR` to `${CLAUDE_PLUGIN_DATA}/ruff-cache/<project-hash>` |

Disk overhead under isolation: ~100 MB for basedpyright stubs + ~5 MB for ruff cache + ~2 GB for RA target dir (real workspace). Default behavior shares user caches; `O2_SCALPEL_ISOLATE_CACHES=1` is the opt-in for users who want session isolation.

---

## 17. Risks (top 10, re-ranked after Q1–Q4 resolutions)

| Rank | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| **P0** | rust-analyzer cold-start UX regression on real workspace (≥3 min on 200+ crates) | High | High | Lazy spawn + `wait_for_indexing()` + `$/progress` per-token tracking; document the floor; spike S1 verifies |
| **P0** | Tool-surface bloat past 13 always-on degrades LLM selection accuracy by 10–30% | High | High | 13 always-on cap; 11 specialty tools `defer_loading: true`; cluster prefix discipline; 30-word docstrings. The +1 (12 → 13) is +0.1% per Speakeasy curve — sub-noise. |
| **P0** | Capability catalog drifts between RA / Python LSP releases | High | Medium-Low (was Medium) | All LSP versions exact-pinned per [Q3 resolution](open-questions/q3-basedpyright-pinning.md); CI catalog-baseline drift test (§15.4) is MVP gate; new title-stability + diagnostic-count fixtures (§15.4a) plug the catalog-gate blind spots |
| **P0** | Multi-LSP coordination introduces consistency bugs (one server stale, another not) | High | Medium-Low (was Medium) | `multi_server` module owns broadcast; integration test forces cross-server consistency on every Python fixture; deterministic merge rule. [Q1](open-questions/q1-pylsp-mypy-live-mode.md) per-step `didSave` *tightens* cross-server consistency (all three Python LSPs see the same on-disk state per step) |
| **P1** | pylsp-mypy stale-diagnostic rate within transactions (`live_mode: false` cache fallback returns last_diagnostics on every internal `didChange`, true rate = 100% without intervention) | High | Medium | Per [Q1 resolution](open-questions/q1-pylsp-mypy-live-mode.md): synthetic `didSave` after each internal `apply()` step + `dmypy: true` warm rechecks; spike P5a is the falsifier — failure path drops pylsp-mypy at MVP |
| **P1** | pylsp-rope unsaved-buffer experimental support produces stale `WorkspaceEdit` | High | Medium | Spike P1 (blocking); fallback `didSave({includeText: true})` before each rope call |
| **P1** | `rust-analyzer/runFlycheck` flakes when `cargo.targetDir` separation isn't respected | High | Medium | `lsp_init_overrides` enforces separate `targetDir`; integration test asserts |
| **P1** | `workspace/applyEdit` reverse-request handler underbuilt → SSR silently fails | Medium | Medium | Spike S3 (blocking); production-grade handler not stub |
| **P2** | basedpyright corroboration disagrees with pylsp-mypy on diagnostic counts → false rollbacks | Medium | Medium | Pick basedpyright as authoritative for `severity_breakdown`; corroborate but don't gate. With Q1 synthetic `didSave`, both servers see same on-disk state, narrowing the disagreement window. |
| **P2** | Ruff fixes conflict with pylsp-rope refactor edits on same offsets | Medium | Medium | Apply rope edits first, ruff `source.fixAll` second; integration test verifies |
| **P2** | `scalpel_apply_capability` discoverability — LLM forgets `capabilities_list` exists | Medium | Medium | SKILL.md prompt; `CAPABILITY_NOT_AVAILABLE` carries `candidates[]` (Levenshtein) and `hint: call capabilities_list`; telemetry post-MVP measures call ratio |
| **P3** *(was P1)* | Out-of-workspace edit regression from auto-accept of `changeAnnotations.needsConfirmation: true` | Low (was Medium) | Low (was Medium) | Per [Q4 resolution](open-questions/q4-changeannotations-auto-accept.md), workspace-boundary path filter is the load-bearing safety check (independent of any annotation); rename-shadowing emits `SemanticShiftWarning` only. The annotation became advisory; the path filter caught the regression vector. Confirmation flow surfaces via Claude Code's permission prompt (§11.9), not scalpel-side UI. |

The directive change *adds* three P0/P1 risks (multi-LSP, catalog drift, tool bloat) and *intensifies* one (pylsp-rope stale buffers) vs. the narrow round. The Q1–Q4 resolutions: lower catalog-drift and multi-LSP-consistency likelihood (exact pin + Q3 fixtures + Q1 synthetic-didSave), drop the auto-accept regression risk to P3 (Q4 path filter mitigates), and add the pylsp-mypy staleness risk to P1 (the original §19 Q1 was about staleness; P5a tests it directly).

---

### 17.1 Risk-mitigation LoC accounting

| Mitigation | LoC | Already counted? |
|---|---|---|
| `multi_server` module | ~430 | Yes (§14.1 [10]) |
| Capability-catalog baseline + drift CI | ~150 (catalog) + ~50 (CI script) | Yes for catalog; CI script in fixture count |
| Tool-prefix grouping | minimal (~20 LoC) | Yes (across primitive/refactoring tools) |
| `targetDir` integration test | ~50 | Yes (in integration tests) |
| `didSave` before rope calls (P1 mitigation) | ~30 | In `python_strategy.py` |
| Spike S1 fallback (`$/progress` shim) | ~30 | In `solidlsp/lsp_protocol_handler/server.py` |
| Spike S3 fallback (real `applyEdit` handler) | ~80 | In §14.1 [2] |
| Spike S4 fallback (`max_edits` guard for SSR) | ~30 | In `scalpel_rust_ssr` deferred facade |
| Defer-loading registration scaffolding | ~40 | In strategy `deferred_tools()` method |

**No additional LoC budget needed for risk mitigation; it is structural in the §14 estimate.**

### 17.2 Risk vs. narrow round (re-rank deltas)

| Risk class | Narrow rank | Full-coverage rank (after Q1–Q4) | Reason |
|---|---|---|---|
| Cold start | P0 | P0 | Unchanged |
| Tool-surface bloat | not listed | **P0** | 4→24 tools (13 always-on + 11 deferred); the directive's headline UX cost |
| Multi-LSP coordination | not listed | **P0** (likelihood ↓ Medium → Medium-Low after Q1) | Q1 per-step `didSave` tightens cross-server consistency |
| Capability catalog drift | not listed | **P0** (likelihood ↓ Medium → Medium-Low after Q3) | Q3 exact-pin policy + new title-stability + diagnostic-count fixtures plug catalog-gate blind spots |
| pylsp-mypy stale diagnostics within transactions | not listed | **P1** (NEW from Q1) | True rate without intervention is 100%; Q1 synthetic-didSave mitigates; P5a falsifies |
| pylsp-rope stale buffers | P2 | P1 | Higher exercise rate under full coverage |
| `runFlycheck` `targetDir` | P1 | P1 | Same |
| Out-of-workspace auto-accept regression | not listed | **P3** (was P1 pre-Q4) | Q4 workspace-boundary path filter mitigates; annotation became advisory |
| Marketplace publication pressure | not listed | P3 | New consideration |
| Persistent checkpoint absence | P2 | P3 | Same; v1.1 |

Net effect of Q1–Q4: one new P1 risk (pylsp-mypy staleness) added; two P0 risks lower their likelihood (catalog drift, multi-LSP coordination); one risk drops from P1 to P3 (auto-accept regression). The directive is honest about this.

---

## 18. Comparative table

| Axis | Narrow MVP (v1) | Full-coverage MVP (this report) | Full design (theoretical maximum) |
|---|---|---|---|
| MCP tools (LLM-visible) | 4 always-on | 13 always-on + 11 deferred = 24 | 50+ (per-handler facades) |
| Languages | Rust + Python | Rust + Python | Rust + Python + TS + Go + Java + C/C++ |
| LSP processes (scalpel-side) | 2 | 4 | 6+ |
| LSP capabilities reachable | ~10 | ~210 (158 RA + 36 RA-extensions + 18 Python) | same as full-coverage MVP |
| Ergonomic facades at MVP | 3 | 5 (Stage 2) + 11 deferred + 12 v0.2.0 | 30+ |
| E2E scenarios at MVP | 7 | 9 | 15+ |
| Integration tests | ~10 | ~70 sub-tests / 32 modules | ~158 (per-handler) |
| Unit tests | ~30 | ~120 | same |
| Logic LoC | ~3,415 | ~6,800 (MVP), ~10,340 (v0.2.0) | ~17,000 (per-handler facades) |
| Fixture LoC | ~2,175 | ~5,240 | ~10,000 |
| Test LoC | ~1,180 | ~5,500 | ~12,000 |
| Total LoC | ~5,640 | ~17,540 (MVP), ~22,380 (v0.2.0) | ~39,000 |
| Fully-loaded LoC | ~8,665 | ~27,100 (MVP) | ~60,000 |
| RAM floor (idle, eager) | ~5 GB | ~5.4 GB | ~10 GB |
| RAM floor (active, real workspace) | ~16 GB | ~17–22 GB | ~30 GB |
| RAM recommended | 16 GB | **24 GB** | 32–64 GB |
| Distribution at MVP | uvx local | uvx local | marketplace |
| Effort sizing | S→M→L | L→L→L (3 stages, all heavy) | XL+ |

The directive's full-coverage MVP is **3.1× the narrow MVP** on logic + tests + fixtures (consistent across Rust + Python + Engineering-scope estimates), but only **1.1–1.4× the resource floor**. The cost lives in **strategies, facades, fixtures, and tests** — not in the agnostic core, which absorbs ~90% of its narrow-round code unchanged.

### 18.1 What survives unchanged from the narrow round

Despite the 3.1× expansion, the following narrow-round artifacts ship into full-coverage MVP **unchanged**:

| Artifact | Narrow round | Full-coverage MVP |
|---|---|---|
| Sibling-LSP discovery (`~/.claude/plugins/cache/**/.lsp.json` walk) | MVP | MVP — unchanged |
| `multilspy` adoption | MVP | MVP — unchanged |
| `platformdirs` path resolution chain | MVP | MVP — unchanged |
| `pydantic` v2 schema validation on `.lsp.json` | MVP | MVP — unchanged |
| Lazy-spawn pattern (SQLAlchemy `pool_pre_ping` analogue) | MVP | MVP — `is_alive()` probe added at full coverage |
| Idle-shutdown after `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS` | v1.1 (narrow) | **MVP** (promoted because 4 LSPs amplify idle cost) |
| Cache-path resolution layered chain (env → TOML → platformdirs → fallback → fail loud) | MVP | MVP — unchanged |
| `o2-scalpel/.claude-plugin/plugin.json` + `.mcp.json` deployment | MVP | MVP — unchanged |
| `vendor/serena/` git submodule | MVP | MVP — unchanged |
| `RustStrategy` separate `cargo.targetDir` override | MVP | MVP — unchanged |
| `O2_SCALPEL_DISABLE_LANGS=<csv>` opt-out | MVP | MVP — semantics extended to `O2_SCALPEL_DISABLE_SERVERS` |
| Marketplace at `o2alexanderfedin/claude-code-plugins` | v1.1 | v1.1 — unchanged |
| `o2-scalpel-newplugin` template generator | v2+ | v2+ — unchanged |
| Boostvolt fork legality posture | MVP-compatible | MVP-compatible — unchanged |
| Piebald no-redistribution stance | enforced | enforced — unchanged |
| SQLAlchemy `pool_pre_ping` mental model | MVP | MVP — unchanged |
| `vendor/claude-code-lsps-piebald/` excluded from release tarballs | release-blocker | release-blocker — unchanged |

The discovery, deployment, vendor-license, and marketplace decisions from the narrow round are unaffected by the directive change. The full-coverage cost is concentrated entirely in the per-language strategy + facade + test surface, exactly as the comparative table predicts.

### 18.2 Failure modes the narrow round avoided that full coverage must address

| Failure mode | Narrow round | Full coverage |
|---|---|---|
| Multi-LSP non-determinism (different organize-imports results from different servers) | n/a (single Python LSP) | §11 deterministic merge rule with priority + dedup |
| Capability catalog drift between LSP releases | n/a (no catalog) | §15.4 baseline drift CI gate |
| Tool-surface saturation past LLM tool-selection ceiling | n/a (4 tools) | 13 always-on cap + `defer_loading` for the rest (Q2 lifted from 12 → 13 to retire dispatcher-payload hallucination on transaction commit) |
| Cross-server stale-buffer race after applying an edit | n/a | `multi_server.py` invalidates buffer-state on all servers via `didChange` |
| `scalpel_apply_capability` discoverability collapse | n/a | SKILL.md prompt + `CAPABILITY_NOT_AVAILABLE` candidates + telemetry post-MVP |
| Auto-accept of `changeAnnotations.needsConfirmation` re-introduces silent regressions | rejected at narrow MVP | per [Q4 resolution](open-questions/q4-changeannotations-auto-accept.md): annotation becomes advisory; safety enforced by §11.8 workspace-boundary path filter; rename-shadowing emits non-blocking `SemanticShiftWarning`. Confirmation prompts via Claude Code's standard tool-permission UI (§11.9), NOT a scalpel-side `scalpel_confirm_*` tool. |
| `experimental/onEnter` snippet escape via `executeCommand` pass-through | n/a | explicit-block (§4.3, §6.9 / spec §3.2) |

---

## 19. Open Questions

The four v2-round open questions (Q1–Q4 below) were resolved on 2026-04-24 by specialist subagents; full reasoning in `open-questions/`. Items 5–7 remain as proposed-resolution-paths from the original synthesis (no new specialist subagent has been engaged).

1. **RESOLVED — see [§9 (pylsp-mypy section)](#9-python-full-coverage-mvp) and `open-questions/q1-pylsp-mypy-live-mode.md`.** Decision: keep `pylsp-mypy` in the MVP active server set with `live_mode: false`, `dmypy: true`, and a scalpel-injected `textDocument/didSave` after each successful internal `apply()` step within a transaction. Falsifier: spike **P5a** (§13). Source-verified: pylsp-mypy's cache fallback (`pylsp_mypy/plugin.py:285`) returns stale `last_diagnostics` on every internal `didChange` — the *true* stale rate without intervention is 100%, not 5%. Integration cost ~135 LoC (already in §14 Stage 2 accounting).

2. **RESOLVED — see [§5.1 / §5.5 / §5.6](#5-canonical-mvp-tool-surface) and `open-questions/q2-12-vs-13-tools.md`.** Decision: promote `scalpel_transaction_commit` to a 13th always-on tool. Routing a *core grammar verb* through `scalpel_apply_capability` violates the dispatcher's "long-tail" contract and forces the LLM to reproduce a magic-string `capability_id` byte-exact (MCP-Zero measures a 23-percentage-point accuracy gap on dispatcher payload vs. named tool). Cold-context cost ~1K tokens; ~0.1% selection-accuracy on Speakeasy curve; sub-noise. The `scalpel.transaction.commit` capability_id alias is preserved for one minor version, then removed in v0.2.0.

3. **RESOLVED — see [§6.4](#64-capability-catalog-as-a-tool) / [§14](#14-staged-delivery-plan) / [§15.4a](#154a-basedpyright-catalog-gate-blind-spot-fixtures-q3) and `open-questions/q3-basedpyright-pinning.md`.** Decision: pin exact at `basedpyright==1.39.3` (and the rest of the Python LSP stack). basedpyright explicitly does not commit to SemVer (v1.32.0 release notes admit "interesting breaking changes" at minor bumps); 8/8 minor releases over 12 months would have changed scalpel's surface; 2/8 introduce drift the catalog gate alone misses. Two new fixtures (~250 LoC) plug the title-stability and diagnostic-count blind spots; serena's upstream `pyright==1.1.403` exact pin is the strongest precedent (same `uvx`-from-git distribution).

4. **RESOLVED — see [§11.8](#118-workspace-boundary-path-filter-uniform-across-all-lsps) / [§11.9](#119-confirmation-flow--claude-code-permission-prompt-integration) and `open-questions/q4-changeannotations-auto-accept.md`.** Decision: workspace-boundary path filter is the load-bearing safety check (independent of any annotation); `changeAnnotations.needsConfirmation: true` becomes advisory; rename-shadowing emits non-blocking `SemanticShiftWarning`; rejection produces `OUT_OF_WORKSPACE_EDIT_BLOCKED`. **User override applied (2026-04-24, post-specialist):** confirmations for unsafe operations reuse Claude Code's standard tool-permission prompt — scalpel exposes unsafe behaviors (e.g., `allow_out_of_workspace`) as explicit boolean facade arguments; the harness's "Allow / Allow always / Deny" UI fires automatically on those arguments. **No `scalpel_confirm_*` MCP tool is added** (the prior plan to add `scalpel_confirm_annotations` in v1.1 is canceled).

---

The following items were carried forward from the original synthesis as proposed-resolution-paths and have not been further escalated:

5. **Strategy-level `[tool.o2-scalpel.python]` config block in `pyproject.toml`.** Python-specialist §17.10 leans yes. **Proposed resolution path**: defer the schema; ship MVP with env-var-only configuration; add the TOML schema in v1.1 alongside `scalpel_reload_plugins`.

6. **Rope's `Project` instance lifecycle.** Python-specialist §17.1 — per-instance with 30-min idle timeout (proposed) vs. per-call (clean). **Proposed resolution path**: per-instance at MVP (faster); spike at Stage 1 to verify memory bounds on 10k-LoC Python project; flip to per-call only if memory exceeds 200 MB per `Project`.

7. **Tool Search ranking for `scalpel_rust_*` deferred tools.** Agent-UX §15.3 notes Anthropic's BM25 ranker may not surface `scalpel_rust_lifetime_elide` highly for "elide lifetime" queries. **Proposed resolution path**: post-MVP tuning — add `keywords` field to deferred tool registrations; measure expansion rate via telemetry's `tool_search_expanded` field.

**All v2-round open questions (Q1–Q4) resolved as of 2026-04-24.** Items 5–7 are tracked but not blocking MVP.

---

## 20. References

Primary sources:

- [Main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — authoritative architecture (Serena + rust-analyzer extensions).
- [Open-questions resolution](../2026-04-24-o2-scalpel-open-questions-resolution.md) — Q10 (cache + lazy spawn), Q11 (marketplace), Q12 (two-process tax), Q13 (fork legality), Q14 (on-demand plugin generator).
- [Rust full-coverage specialist](specialist-rust.md) — 19 facades, 158 assists × 12 families, 36 RA extensions, ~52 protocol methods, `calcrs` + 18 fixtures, 6 spikes.
- [Python full-coverage specialist](specialist-python.md) — 3-LSP architecture, full Rope inventory, 12 MVP facades + 8 v1.1, 14-step interpreter discovery, `calcpy` + 4 sub-fixtures, 6 spikes.
- [Agent UX full-coverage specialist](specialist-agent-ux.md) — 12 always-on + 11 deferred, hybrid (E) + dynamic registration (D), `scalpel_<area>_<verb>`, 30-word docstrings, 10 error codes, `scalpel_dry_run_compose` + transactional rollback.
- [Engineering scope full-coverage specialist](specialist-scope.md) — Stage 1 + Stage 2 = MVP cut, Stage 3 = v0.2.0, ~17,600 LoC, 24 GB floor, marketplace at v1.1.

Open-question resolutions (v2-round, 2026-04-24):

- [Q1 — pylsp-mypy `live_mode` policy](open-questions/q1-pylsp-mypy-live-mode.md) — `live_mode: false` + `dmypy: true` + scalpel synthetic per-step `didSave`; spike P5a is the falsifier.
- [Q2 — 12 vs. 13 always-on tools](open-questions/q2-12-vs-13-tools.md) — promote `scalpel_transaction_commit` to a 13th always-on tool; retire dispatcher-payload hallucination.
- [Q3 — basedpyright pinning policy](open-questions/q3-basedpyright-pinning.md) — `basedpyright==1.39.3` exact pin; new title-stability + diagnostic-count fixtures plug the catalog-gate blind spots.
- [Q4 — `changeAnnotations` auto-accept policy](open-questions/q4-changeannotations-auto-accept.md) — workspace-boundary path filter is load-bearing; annotation advisory; user-override (2026-04-24): confirmations reuse Claude Code's tool-permission prompt — no scalpel-side confirmation UI.

Archived narrow synthesis (superseded by this report):

- [archive-v1-narrow/2026-04-24-mvp-scope-report.md](archive-v1-narrow/2026-04-24-mvp-scope-report.md) — 4-tool collapse, ~5,640 LoC, 16 GB floor.
- [archive-v1-narrow/specialist-rust.md](archive-v1-narrow/specialist-rust.md), [archive-v1-narrow/specialist-python.md](archive-v1-narrow/specialist-python.md), [archive-v1-narrow/specialist-agent-ux.md](archive-v1-narrow/specialist-agent-ux.md), [archive-v1-narrow/specialist-scope.md](archive-v1-narrow/specialist-scope.md).

External references (already in the main design and resolution docs; preserved here for self-containment):

- LSP 3.17 specification: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
- rust-analyzer assist registry: `crates/ide-assists/src/lib.rs::all()`
- rust-analyzer LSP extensions: `docs/book/src/contributing/lsp-extensions.md`
- pylsp-rope: https://github.com/python-rope/pylsp-rope
- Rope: https://rope.readthedocs.io/en/latest/library.html
- basedpyright: https://docs.basedpyright.com/latest/
- Ruff: https://docs.astral.sh/ruff/editors/features/
- multilspy: https://github.com/microsoft/multilspy
- Anthropic Tool Search: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- Anthropic `defer_loading`: https://unified.to/blog/scaling_mcp_tools_with_anthropic_defer_loading
- Claude Code permissions (canonical): https://code.claude.com/docs/en/permissions
- Claude Code MCP integration: https://code.claude.com/docs/en/mcp
- platformdirs: https://github.com/platformdirs/platformdirs

---

*End of full-coverage MVP synthesis. Supersedes [archive-v1-narrow/2026-04-24-mvp-scope-report.md](archive-v1-narrow/2026-04-24-mvp-scope-report.md). Authors: AI Hive(R), 2026-04-24.*
