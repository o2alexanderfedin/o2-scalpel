# Facade-stub audit & fix spec — 2026-04-29

**Author:** AI Hive®
**Repo:** `o2-scalpel`
**Worktree:** `/Volumes/Unitek-B/Projects/o2-scalpel.wt-facade-stubs` (branch `feature/v1.5-facade-stub-fixes`)
**Trigger:** user-reported `scalpel_split_file` Rust path is a stub (`del groups`, hardcoded `(0,0)→(0,0)` LSP range, `actions[0]` taken without policy, mock-only test).

## TL;DR

Four parallel adversarial audits (parameter graveyards / mock-only tests / degenerate LSP calls / TODO-FIXME markers) confirm the user's report is **not an isolated case**:

- **17 facades** discard ≥1 declared semantic parameter at function entry via `del`.
- **5 facades** + 1 helper send hardcoded `(0,0)→(0,0)` ranges to the LSP.
- **2 shared dispatchers** (`_dispatch_single_kind_facade`, `_python_dispatch_single_kind`) blindly take `actions[0]` from the LSP response with no policy — these dispatchers are called by ~17 facades, amplifying every disambiguation problem.
- **63 mock-only spike tests** (~30% of facade tests) assert dispatch shape but never re-read files post-apply, so none would catch a parameter-discard regression.
- **21 of 25 ergonomic facades** have ZERO real-disk-mutation test coverage.
- **The `_apply_workspace_edit_to_disk` applier silently drops `CreateFile`/`RenameFile`/`DeleteFile` resource ops** (`scalpel_facades.py:130-135` — `# Resource op — skip per v1.1 deferral`).

## Severity rubric

| Tier | Definition |
|---|---|
| **CRITICAL** | Required argument silently discarded AND the fake behavior produces wrong-but-plausible output (caller can't detect failure from the response envelope). |
| **HIGH** | Documented argument discarded OR degenerate LSP call OR shared dispatcher with no policy — caller's intent is decorative. |
| **MEDIUM** | Argument discarded but documented "informational" in docstring, OR LSP call has compensating logic that masks most caller intent. |
| **LOW** | Acknowledged limitation; docstring is honest about the gap. |

## Findings — by stub (deduplicated across audit angles)

### CRITICAL

#### CR-1: `_split_rust` — entire grouping payload is fiction
- **File:** `vendor/serena/src/serena/tools/scalpel_facades.py:319-368`
- **Discarded:** `groups` (the whole point), plus `parent_layout`, `keep_in_original`, `reexport_policy`, `explicit_reexports`, `allow_partial`, `preview_token` (6 of 8 semantic args).
- **Degenerate LSP call:** `start={"line":0,"character":0}, end={"line":0,"character":0}, only=["refactor.extract.module"]`; only `actions[0]` applied.
- **Tests:** mock-only at `test/spikes/test_stage_2a_t2_split_file.py:115` — passes a `groups={"helpers":["add"]}` dict that is never asserted to flow into the LSP request.
- **User-visible behavior:** rust-analyzer is asked for one default extract action at the file head; the user's split plan is decorative.
- **Fix:** for each `target_module` key in `groups`, resolve each symbol's range via `coord.find_symbol_range`, dispatch one `refactor.extract.module` per symbol with the symbol's actual range, merge the resulting WorkspaceEdits. Mirror the `_split_python` per-group iteration pattern.

#### CR-2: `_apply_workspace_edit_to_disk` silently drops resource ops
- **File:** `vendor/serena/src/serena/tools/scalpel_facades.py:130-135`
- **Code:** `if "kind" in dc: continue  # Resource op — skip per v1.1 deferral.`
- **User-visible behavior:** every facade that emits `CreateFile`/`RenameFile`/`DeleteFile` (e.g., module rename, file split, scaffold-related-class) silently succeeds with `applied=True` while the file ops were dropped. Markdown's split/extract route through a parallel applier (`_apply_markdown_workspace_edit` at L3177) and so DO get resource-ops; everything else is broken.
- **Fix:** implement `CreateFile` (touch + `mkdir -p`), `RenameFile` (move with conflict detection), `DeleteFile` (with `ignoreIfNotExists` semantics) per LSP spec. Add resource-op assertions to the applier's checkpoint.

### HIGH

The shared root cause for 17 of these is the shared dispatcher pattern described under HI-13 below. Stubs that go through that dispatcher are listed first; bespoke stubs after.

#### HI-1: `_dispatch_single_kind_facade` / `_python_dispatch_single_kind` — `actions[0]` without policy (ROOT CAUSE — 17 facades affected)
- **File:** `scalpel_facades.py:1102-1175` (Rust dispatcher) and `1870-1924` (Python dispatcher).
- **Code:** `workspace_edit = _resolve_winner_edit(coord, actions[0])`
- **Why it's a stub:** when the LSP returns N candidate code actions, the FIRST is silently chosen. No `isPreferred=True` filter, no title match against the caller's payload, no "fail loud if multiple actions remain" guard.
- **Affected facades** (every facade routed through this dispatcher inherits the bug): `change_return_type`, `complete_match_arms`, `extract_lifetime`, `expand_glob_imports`, `generate_trait_impl_scaffold`, `generate_member`, `change_visibility`, `convert_module_layout`, `tidy_structure`, `change_type_shape`, `convert_to_method_object`, `local_to_field`, `use_function`, `introduce_parameter`, `generate_from_undefined`, `auto_import_specialized`, `ignore_diagnostic`.
- **Fix:** add candidate disambiguation policy: (1) prefer `isPreferred=True`; (2) match by `action.title` against caller's intent payload (e.g., `target_visibility="pub_crate"` should match `Change visibility to pub(crate)`); (3) fail with `MULTIPLE_CANDIDATES` envelope if step 2 is ambiguous.

#### HI-2: `ScalpelChangeReturnTypeTool` — discards `new_return_type` (the headline arg)
- **File:** `scalpel_facades.py:1464-1503` — `del preview_token, new_return_type` at L1490.
- **Why it's a stub:** docstring promises "rewrite return type to X"; rust-analyzer's `change_return_type` only suggests one type per cursor; user-supplied `new_return_type="Result<T,E>"` has zero effect.
- **Fix:** if rust-analyzer's assist arguments expose a parameter slot (some assists do), pass `new_return_type` as the override. If not, return `INPUT_NOT_HONORED` envelope when caller-supplied differs from LSP-suggested, and document this clearly. Do NOT silently fake.

#### HI-3: `ScalpelExtractLifetimeTool` — discards `lifetime_name`
- **File:** `scalpel_facades.py:1550-1589` — `del preview_token, lifetime_name` at L1576.
- **Fix:** see HI-2 (same shape — caller-named lifetime can't override rust-analyzer's auto-pick at v0.10; surface honestly).

#### HI-4: `ScalpelGenerateTraitImplScaffoldTool` — discards `trait_name` (REQUIRED positional argument)
- **File:** `scalpel_facades.py:1641-1679` — `del preview_token, trait_name` at L1666.
- **Why it's a stub:** `trait_name: str` is a REQUIRED arg per the type signature; the facade promises "scaffold `impl Display for Foo`"; the implementation drops the trait name and accepts whatever rust-analyzer offers.
- **Fix:** rust-analyzer's `generate_trait_impl` assist takes the trait via an interactive picker UI. We need to either (a) wire `trait_name` into the assist's `arguments` payload (read RA's protocol for this), or (b) filter the returned actions by title match (`Implement <trait_name>`).

#### HI-5: `ScalpelChangeVisibilityTool` — discards `target_visibility`
- **File:** `scalpel_facades.py:1253-1290` — `del preview_token, target_visibility` at L1277.
- **Why it's a stub:** `target_visibility ∈ {pub, pub_crate, pub_super, private}` is dropped; only `_VISIBILITY_KIND="refactor.rewrite.change_visibility"` is dispatched. rust-analyzer's `change_visibility` cycles through tiers — caller can't pick a tier.
- **Fix:** filter the returned candidates by title prefix (`Change visibility to pub(crate)`) — this is rust-analyzer's stable title format. Surface `MULTIPLE_CANDIDATES` if no match.

#### HI-6: `ScalpelGenerateFromUndefinedTool` — discards `target_kind`
- **File:** `scalpel_facades.py:2097-2133` — `del preview_token, target_kind, language` at L2121.
- **Why it's a stub:** `target_kind ∈ {function, class, variable}` is dropped; one fixed `_GENERATE_FROM_UNDEFINED_KIND="quickfix.generate"` is dispatched; rope generates whatever its first candidate is (typically a function regardless of caller's choice).
- **Fix:** dispatch separate kinds per `target_kind` value (rope offers `quickfix.generate.function`, `.class`, `.variable` per its API), or filter by title.

#### HI-7: `ScalpelExtractTool` — discards 4 of 9 semantic args
- **File:** `scalpel_facades.py:403-543` — `del new_name, visibility, similar, global_scope, preview_token` at L440.
- **Why it's a stub:** `new_name="my_helper"` becomes whatever LSP auto-names; `visibility="pub(crate)"` (Rust) is fiction; `similar=True` (Rope) is fiction; `global_scope=True` (Python) is fiction. The CORE target+kind do flow through, so this is HIGH not CRITICAL.
- **Fix:** rope supports `similar` and `global_scope` as part of the `extract_*` parameters — wire them; for Rust `visibility`, post-process the WorkspaceEdit to inject the `pub(crate)` qualifier; for `new_name`, post-process or filter by title.

#### HI-8: `ScalpelInlineTool` — discards `name_path` + `remove_definition`; degenerate (0,0) on `all_callers` scope
- **File:** `scalpel_facades.py:560-665` — `del name_path, remove_definition, preview_token` at L591; fallback `pos = position or {"line":0,"character":0}` at L627.
- **Why it's a stub:** the `scope='all_callers'` path silently uses (0,0) when `position` is omitted; the `name_path` alternate-entry mode is fiction; `remove_definition: bool` is dropped (LSP assist always removes).
- **Fix:** when `name_path` is given, resolve the symbol via `coord.find_symbol_range` to get the real `position`; iterate references via `coord.request_references` for the `all_callers` scope; honor `remove_definition` by post-filtering the WorkspaceEdit.

#### HI-9: `ScalpelFixLintsTool` — discards `rules`; hardcoded (0,0); `actions[0]`
- **File:** `scalpel_facades.py:2185-2264` — `del preview_token, rules, language` at L2212; `start={"line":0,"character":0}, end={...}, only=[_FIX_LINTS_KIND]` at L2228-2232.
- **Why it's a stub:** `rules: list[str]` allow-list is dropped; ruff's full `source.fixAll.ruff` runs regardless. Range is whole-file degenerate.
- **Fix:** pass `rules` via the LSP `data`/`arguments` payload (`source.fixAll.ruff` accepts `--select` equivalent through `data.rules`), OR run ruff multiple times with per-rule `only=[...]` filters and merge edits.

#### HI-10: `ScalpelImportsOrganizeTool` — discards `add_missing`/`remove_unused`/`reorder`
- **File:** `scalpel_facades.py:929-1051` — `del add_missing, remove_unused, reorder, preview_token` at L958.
- **Why it's a stub:** three of four user toggles dropped; one fixed `source.organizeImports` request conflates them. Caller can't ask "remove unused only".
- **Fix:** dispatch separate kinds per flag (`source.organizeImports.removeUnused`, `…sortImports`, `quickfix.import` for missing) and merge resulting edits.

#### HI-11: `ScalpelIgnoreDiagnosticTool` — discards `rule`
- **File:** `scalpel_facades.py:2273-2316` — `del preview_token, rule, language` at L2299.
- **Why it's a stub:** the rule the caller wants to silence is dropped; whatever quickfix LSP returns first is applied.
- **Fix:** pass `rule` as the diagnostic to attach the `noqa: <rule>` comment to. ruff/pylsp expose this via `data.code` in the diagnostic payload.

#### HI-12: `ScalpelExpandMacroTool` + `ScalpelVerifyAfterRefactorTool` — discard `dry_run` (SAFETY VIOLATION)
- **File:** `scalpel_facades.py:1760, 1824` — both `del preview_token, dry_run`.
- **Why it's a stub:** `dry_run=True` still triggers live LSP work and side effects (flycheck runs). This is a safety-contract violation, not just a feature gap.
- **Fix:** honor `dry_run`: if true, return a preview envelope without invoking flycheck/macro-expansion side effects.

#### HI-13: hardcoded `(0,0)→(0,0)` LSP ranges (5 sites)
- **Files (all in scalpel_facades.py):** L330-335 (`_split_rust`), L991-995 (imports organize), L2228-2232 (fix_lints), L3011-3019 (java generate fallback), L627-628 (inline fallback).
- **Fix:** for each site, derive a real range from caller input (file-wide, symbol range, or selection). The "java generate fallback" case is the trickiest — fix by resolving `class_name_path` to a class range first.

### MEDIUM

#### ME-1: `ScalpelTidyStructureTool` — discards `scope`
- **File:** `scalpel_facades.py:1300-1363` — `del preview_token, scope` at L1325; loops all `_TIDY_STRUCTURE_KINDS` regardless.
- **Fix:** filter the iterated kinds by `scope ∈ {file, type, impl}`.

#### ME-2: `ScalpelAutoImportSpecializedTool` — discards `symbol_name` (documented)
- **File:** `scalpel_facades.py:2139-2179` — `del preview_token, symbol_name, language` at L2167.
- **Fix:** filter rope's candidates by `symbol_name` substring match.

#### ME-3: `ScalpelIntroduceParameterTool` — discards `parameter_name`
- **File:** `scalpel_facades.py:2050-2093` — `del preview_token, parameter_name, language` at L2074.
- **Fix:** post-process the WorkspaceEdit to substitute the auto-generated name with `parameter_name`.

#### ME-4: `ScalpelGenerateConstructorTool` + `ScalpelOverrideMethodsTool` — discard selection lists (documented "Phase 2.5 deferral")
- **Files:** `scalpel_facades.py:3098, 3153` — `del include_fields` / `del method_names`.
- **Fix:** wire the selection lists via jdtls's interactive-picker arguments.

#### ME-5: `ScalpelConvertModuleLayoutTool` — `actions[0]` despite `target_layout` flowing
- **File:** `scalpel_facades.py:1201-1247`.
- **Fix:** disambiguate by title (HI-1 root-cause fix).

#### ME-6: `_java_generate_dispatch` — (0,0) fallback may select wrong class
- **File:** `scalpel_facades.py:3011-3019`.
- **Fix:** resolve `class_name_path` to a class range first; fall back only if resolution fails (and surface `SYMBOL_NOT_FOUND`).

#### ME-7: `ScalpelExtractTool` — `actions[0]` (covered by HI-1) + the discarded knobs in HI-7

### LOW

#### LO-1: `ScalpelRenameTool` — discards `also_in_strings`
- **File:** `scalpel_facades.py:681-802` — `del also_in_strings, preview_token` at L708.
- **Note:** `textDocument/rename` cannot rewrite string literals — this is an LSP protocol limitation, not a fixable gap. Surface this honestly via response envelope, don't fake.

#### LO-2: `rust_strategy.py` doc-drift
- **File:** `vendor/serena/src/serena/refactoring/rust_strategy.py:5-7` — module docstring still describes the file as a Stage-1E skeleton awaiting Stage 1G fill-out, despite v1.1 having shipped.
- **Fix:** update the docstring (purely documentation).

#### LO-3: `checkpoints.py` deep-tree restore deferral
- **File:** `vendor/serena/src/serena/refactoring/checkpoints.py:87` — directory tree restoration out of scope; only empty placeholder dirs are recreated by `scalpel_undo_last`.
- **Fix:** implement recursive directory snapshot in checkpoints.

## Test discipline gaps

**Quantitative findings (from test audit):**

| Test category | MOCKED | HALF-REAL | REAL | Total |
|---|---|---|---|---|
| Stage 2A facade unit tests | 25 | 0 | 0 | 25 |
| Stage 3 facade unit tests | 38 | 0 | 0 | 38 |
| Integration `test_assist_*.py` | 0 | 51 | 10 | 61 |
| Integration multi-server / smoke | 1 | 24 | 0 | 25 |
| E2E `test_e2e_*.py` | 0 | 36 | 25 | 61 |
| **Totals** | **63** | **111** | **35** | **210** |

**Acid test:** does the test contain `Path.read_text()` AFTER the facade call, AND assert specific content was written? Only **35 of 210 facade-touching tests pass** (17%).

**Facades with ZERO real-disk-mutation test coverage (21 of 25 ergonomic facades):** `scalpel_inline`, `scalpel_imports_organize`, `scalpel_transaction_commit`, `scalpel_convert_module_layout`, `scalpel_change_type_shape`, `scalpel_change_return_type`, `scalpel_complete_match_arms`, `scalpel_extract_lifetime`, `scalpel_expand_glob_imports`, `scalpel_generate_trait_impl_scaffold`, `scalpel_generate_member`, `scalpel_expand_macro`, `scalpel_verify_after_refactor`, `scalpel_convert_to_method_object`, `scalpel_local_to_field`, `scalpel_use_function`, `scalpel_introduce_parameter`, `scalpel_generate_from_undefined`, `scalpel_auto_import_specialized`, `scalpel_fix_lints`, `scalpel_ignore_diagnostic`.

**Implication:** every parameter-discard finding above (CR-* and HI-* and ME-*) would still pass its current test suite. The mock-only tests assert dispatch shape only; they cannot catch the discards.

## Fix priority groups (for execution planning)

The finds are best fixed in order of **shared-blast-radius first** (the dispatcher fix unblocks 17 facades) and **safety violations next**.

| Group | Findings | Reason |
|---|---|---|
| **G1 — Root-cause dispatcher fix** | HI-1 (the two shared dispatchers) | One fix unblocks 17 callers; precondition for HI-2/3/4/5/6 to be testable. |
| **G2 — Safety violations** | HI-12 (`dry_run` discards in 2 tools) | Safety contract is non-negotiable. |
| **G3 — User-reported & resource ops** | CR-1, CR-2 | User explicitly flagged CR-1; CR-2 is a related applier-level deferral. |
| **G4 — Parameter graveyards (HIGH)** | HI-2, HI-3, HI-4, HI-5, HI-6, HI-7, HI-8, HI-9, HI-10, HI-11 | After G1 lands, most of these become "wire the discarded arg into the disambiguation policy". |
| **G5 — Hardcoded ranges (HI-13)** | the 3 remaining (0,0) sites not covered by G3/G4 | Pure pattern fix. |
| **G6 — MEDIUM** | ME-1 through ME-7 | Documented stubs; fix as bandwidth permits. |
| **G7 — Test discipline retrofit** | Add real-disk assertions to the 63 mock-only tests | Prevents regression; the 21 zero-coverage facades each need ≥1 REAL test. |
| **G8 — LOW & docs** | LO-1, LO-2, LO-3 | Acknowledge limitations; minor doc polish. |

## How to verify each fix

For every fix:

1. **Failing test first** that reads the file post-apply and asserts content (acid-test discipline).
2. **Implementation** against real LSP (or carefully-faked LSP that records the LSP request payload so the test can assert the discarded arg now flows through).
3. **Submodule pyright 0/0/0** + targeted regression sweep on the affected test files.
4. **Atomic commit per fix** with `Authored-by: AI Hive®`.

## Out of scope for this milestone

- The 1010 LoC of `scalpel_facades.py` itself is a known-too-monolithic file; refactoring its structure is deferred. Fix the bugs in-place.
- Deep-tree directory checkpoint restore (LO-3) — separate v1.6 feature.
- Markdown applier consolidation with the main applier (CR-2) — could be done in this milestone or deferred; flagged as a v1.5 stretch goal.

## Sources (line-cited audit reports)

The four parallel audit agents produced ~37 file:line citations between them, all reproduced inline above. Findings are deduplicated across audit angles (parameter graveyard, mock-only test, degenerate LSP call, TODO/FIXME marker) — many stubs were independently surfaced by ≥3 angles, increasing confidence.
