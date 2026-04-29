# Stub Facade Audit — Unified Verdict

**Status**: APPROVED v1
**Date**: 2026-04-29
**Synthesis**: skeptic-review.md + defender-review.md, with line-level cross-check
**Synthesizer**: 3-agent pair audit (skeptic + defender + synthesizer)
**Source files**:
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_facades.py` (3,425 lines, 33 facade classes)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_primitives.py` (1,247 lines, 10 primitive classes)

---

## Executive summary

- **43 tools audited**: 33 facades in `scalpel_facades.py` + 10 primitives in `scalpel_primitives.py`. (Skeptic counted 33+10; defender double-counted at 35+11. The reconciled count is 33+10 — `_FACADE_DISPATCH` table has 35 entries because of facade aliases; the facade *classes* number 33.)
- **Verdict distribution**:
  - **STUB**: 4 (apply_capability, dry_run_compose, split_file-python-branch, rollback-pair)
  - **HYBRID**: 18 (real LSP dispatch but with documented-parameter ablation that misleads the LLM contract)
  - **INTENTIONAL**: 21 (real implementation, real tests, real on-disk apply; only the universal A5 doc-Examples gap)
- **Universal gap**: zero `Examples:` blocks across 43 tools. Not a stub but a docstring polish item.
- **Highest-priority Stage-2 candidates** (top 5):
  1. `scalpel_apply_capability` — fix `_dispatch_via_coordinator` to resolve+apply WorkspaceEdit instead of recording `{"changes": {}}` with `applied=True`. **P1**.
  2. `scalpel_split_file` (Python branch) — wire `_apply_workspace_edit_to_disk(merged)` after `record_checkpoint_for_workspace_edit`; honor `groups[*]` symbol lists (currently iterates only keys). **P1**.
  3. `scalpel_rollback` / `scalpel_transaction_rollback` — replace `_no_op_applier` with a real on-disk inverse-applier OR add a giant docstring WARNING that rollback is bookkeeping-only. **P1 (correctness lie) or P3 (doc only)**.
  4. `scalpel_dry_run_compose` — finish `_dry_run_one_step` so per-step `StepPreview.changes` reports the prospective edit (currently returns `()` always). **P2**.
  5. `scalpel_change_visibility` / `_change_return_type` / `_extract_lifetime` / `_generate_trait_impl_scaffold` / `_introduce_parameter` / `_generate_from_undefined` / `_auto_import_specialized` / `_ignore_diagnostic` — the "informational parameter" cluster. Either rip the parameters from the signature OR open the docstring with `Note: this parameter is informational; the LSP picks the action.` Stage 2 should pick one of those two paths and ship consistently. **P2**.

---

## Methodology

For each facade I read the `apply()` body in source. When reviewers disagreed I treated source as tiebreaker:

| Test | Adjudication rule |
|---|---|
| Does the body call `_apply_workspace_edit_to_disk` (or `_apply_markdown_workspace_edit`) on a non-empty edit? | If yes → real on-disk change → not a Tier-1 stub on A3. If no → A3 fails. |
| Does the body `del` documented parameters at the top of `apply()`? | If yes → A4 partial — note the contract gap. The defender's "informational signal" defense is accepted only if the docstring explicitly tags the parameter as informational; otherwise HYBRID. |
| Does the body call `coord.supports_kind` or `coord.supports_method` before LSP I/O? | If yes → A1 defended → not a stub on dispatch. |
| Does a test exercise the real body (not a mock-and-patch of the body)? | If yes → A2 defended. The two cases where the test patches out the body (`apply_capability`, `dry_run_compose`) are flagged. |
| Is the deferral comment (`# Stage 2A wires`, `# Phase 2.5`) present AND does the body silently return success? | If both → STUB regardless of staging plan, because the contract is `applied=True`. If the body returns `CAPABILITY_NOT_AVAILABLE`/INVALID_ARGUMENT instead, the deferral is honest. |

When the defender invokes spec § 5.2.1 / § 4.5 / `project_dynamic_lsp_capability_complete` to defend a facade that returns `CAPABILITY_NOT_AVAILABLE`, the defender wins — that envelope IS the contract. When the defender invokes the same to defend a facade that returns `applied=True` while having modified zero bytes on disk, the skeptic wins — the contract says `applied=True` means edits landed.

---

## Verdict table

| # | Facade | Skeptic tier | Defender tier | Final verdict | Priority | Gap to close |
|---|---|---|---|---|---|---|
| 1 | `scalpel_split_file` (Python branch) | T1 | T1 (defended) | **STUB** | P1 | `_apply_workspace_edit_to_disk(merged)` missing; `groups[*]` symbol lists silently dropped (only keys iterated); 5 of 9 docstring parameters `del`'d |
| 2 | `scalpel_split_file` (Rust branch) | T3 | T1 | **HYBRID** | P2 | Real LSP path + `_apply_workspace_edit_to_disk`, but `del groups` makes the user's symbol-grouping intent ineffectual — RA assist drives output |
| 3 | `scalpel_extract` | T1 | T1 | **HYBRID** | P2 | Real path including `find_symbol_range` for `name_path`, double-gate, on-disk apply — but `del new_name, visibility, similar, global_scope, preview_token` silently drops 4 user-facing knobs |
| 4 | `scalpel_inline` | T1 | T1 | **HYBRID** | P2 | `del name_path, remove_definition, preview_token` — `name_path` discarded (callers must pass `position`); `remove_definition=True` advertised but not honored |
| 5 | `scalpel_rename` | T2 | T1 | **HYBRID** | P3 | Three orthogonal paths (module-rename, `__all__` augmentation, LSP rename) all real; only `also_in_strings` toggle ablated. Minor. |
| 6 | `scalpel_imports_organize` | T1 | T1 | **HYBRID** | P2 | Real multi-file dispatch + per-file `_apply_workspace_edit_to_disk` + engine filter — but `add_missing`, `remove_unused`, `reorder` toggles deleted (3 of 4 advertised behaviors are theatre) |
| 7 | `scalpel_convert_module_layout` | T2 | T2 | **INTENTIONAL** | — | Real dispatcher delegate; only A5 missing |
| 8 | `scalpel_change_visibility` | T1 | T2 | **HYBRID** | P2 | `del target_visibility` discards THE knob (4-tier visibility selection); body always dispatches one kind regardless of pub/pub_crate/pub_super/private request |
| 9 | `scalpel_tidy_structure` | T1 | T2 | **HYBRID** | P2 | `del scope` — multi-kind loop is real and per-kind-gated, but `scope='type'` and `scope='impl'` silently behave like `scope='file'` |
| 10 | `scalpel_change_type_shape` | T2 | T2 | **INTENTIONAL** | — | Real 7-entry kind table + dispatcher delegate; A5 only |
| 11 | `scalpel_change_return_type` | T1 | T2 | **HYBRID** | P2 | `del new_return_type` — defender concedes the parameter is informational; docstring should be re-tagged or parameter should be ripped |
| 12 | `scalpel_complete_match_arms` | T2 | T2 | **INTENTIONAL** | — | Dispatcher delegate; A5 only |
| 13 | `scalpel_extract_lifetime` | T1 | T2 | **HYBRID** | P2 | `del lifetime_name` — same informational-parameter pattern as `_change_return_type` |
| 14 | `scalpel_expand_glob_imports` | T2 | T2 | **INTENTIONAL** | — | Dispatcher delegate; A5 only |
| 15 | `scalpel_generate_trait_impl_scaffold` | T1 | T2 | **HYBRID** | P2 | `del trait_name` — required positional parameter discarded |
| 16 | `scalpel_generate_member` | T2 | T2 | **INTENTIONAL** | — | Custom 4-entry kind table; A5 only |
| 17 | `scalpel_expand_macro` | T1 | T2 | **HYBRID** | P3 | Custom rust-only path via `coord.expand_macro`, real introspection — but `del dry_run` violates the docstring promise to honor `dry_run` |
| 18 | `scalpel_verify_after_refactor` | T1 | T2 | **HYBRID** | P3 | Composite `fetch_runnables` + `run_flycheck` — but `del dry_run` same as `expand_macro` |
| 19 | `scalpel_convert_to_method_object` | T3 | T2 | **INTENTIONAL** | — | `_python_dispatch_single_kind` with unique kind constant; A5 only |
| 20 | `scalpel_local_to_field` | T3 | T2 | **INTENTIONAL** | — | Same as above; supports_kind gate makes it a CAPABILITY_NOT_AVAILABLE machine when pylsp-rope doesn't advertise — that's the contract |
| 21 | `scalpel_use_function` | T3 | T2 | **INTENTIONAL** | — | Same as above |
| 22 | `scalpel_introduce_parameter` | T1 | T2 | **HYBRID** | P2 | `del parameter_name, language` — parameter_name is the knob |
| 23 | `scalpel_generate_from_undefined` | T1 | T2 | **HYBRID** | P2 | `del target_kind, language` — `target_kind: Literal["function", "class", "variable"]` is the routing knob and is dropped |
| 24 | `scalpel_auto_import_specialized` | T1 | T2 | **HYBRID** | P2 | `del symbol_name, language` — docstring concedes "v1.1 will expose a candidate-set parameter" — still unimplemented at v1.5 |
| 25 | `scalpel_fix_lints` | T1 | T2 | **HYBRID** | P3 | Bespoke body with real `_resolve_winner_edit` + `_apply_workspace_edit_to_disk` (closes E13-py dedup); only `del rules, language` and the docstring already tags `rules` informational. Minor. |
| 26 | `scalpel_ignore_diagnostic` | T1 | T2 | **HYBRID** | P2 | `del rule, language` — `rule` is THE knob ("which lint rule to suppress"); always whatever pyright/ruff surfaces wins |
| 27 | `scalpel_convert_to_async` | T2 | T2 | **INTENTIONAL** | — | Real `python_async_conversion.convert_function_to_async` helper, real on-disk apply, dedicated test |
| 28 | `scalpel_annotate_return_type` | T2 | T2 | **INTENTIONAL** | — | Real `python_return_type_infer.annotate_return_type`; dedicated test |
| 29 | `scalpel_convert_from_relative_imports` | T2 | T2 | **INTENTIONAL** | — | Real `python_imports_relative.convert_from_relative_imports`; dedicated test |
| 30 | `scalpel_rename_heading` | T2 | T2 | **INTENTIONAL** | — | Custom regex pre-resolution + marksman LSP rename; A5 only |
| 31 | `scalpel_split_doc` | T2 | T2 | **INTENTIONAL** | — | Real `markdown_doc_ops.split_doc_along_headings` + CreateFile resource ops via `_apply_markdown_workspace_edit` |
| 32 | `scalpel_extract_section` | T2 | T2 | **INTENTIONAL** | — | Real `markdown_doc_ops.extract_section`; same applier |
| 33 | `scalpel_organize_links` | T2 | T2 | **INTENTIONAL** | — | Real `markdown_doc_ops.organize_markdown_links`; same applier |
| 34 | `scalpel_generate_constructor` | T1 | T2 | **HYBRID** | P3 | Real `_java_generate_dispatch` with `find_symbol_range` resolution; explicit Phase-2.5 deferral comment — `del include_fields` is openly tagged. Honest deferral. Tag-only fix: ensure docstring opener says "all fields included by default". |
| 35 | `scalpel_override_methods` | T1 | T2 | **HYBRID** | P3 | Same as `_generate_constructor` — `del method_names` openly tagged Phase 2.5 |
| 36 | `scalpel_transaction_commit` | T2 | T1 | **INTENTIONAL** | — | Walks `_FACADE_DISPATCH` (35 entries), per-step replay, fail-fast; inherits child stubness but the dispatcher itself is real |
| | **PRIMITIVES** | | | | | |
| 37 | `scalpel_capabilities_list` | OK | T1 | **INTENTIONAL** | — | Catalog reader with `preferred_facade` field per v1.5 P1 |
| 38 | `scalpel_capability_describe` | OK | T1 | **INTENTIONAL** | — | Fuzzy-match error recovery via top-5 candidates |
| 39 | `scalpel_apply_capability` (FALLBACK) | **T1 highest confidence** | T1 (defended) | **STUB** | **P1** | `_dispatch_via_coordinator` records `applied={"changes": {}}` and returns `applied=True` without resolving the action's WorkspaceEdit or applying to disk. The `del params, preview_token  # Stage 2A wires these end-to-end` comment is an explicit deferral that contradicts the `applied=True` return. See cross-check § below. |
| 40 | `scalpel_dry_run_compose` | T1 | T1 (defender concedes the helper) | **STUB** | P2 | `_dry_run_one_step` returns empty `StepPreview` with `changes=()`. Tests that exercise fail-fast inject failures by patching the helper externally, proving the body cannot produce a failure organically. Defender concedes this is the genuine stub-helper. |
| 41 | `scalpel_confirm_annotations` | T2 | T1 | **INTENTIONAL** | — | 62-line `_filter_workspace_edit_by_labels` walker; real on-disk apply |
| 42 | `scalpel_rollback` | T1 (rollback-as-bookkeeping) | T1 | **STUB** | P1 (or P3 if doc-only) | `ckpt_store.restore(checkpoint_id, _no_op_applier)` — `_no_op_applier` returns 0 unconditionally, never inverts on-disk state. Either wire a real reverse-applier OR add a docstring WARNING that rollback is checkpoint-bookkeeping-only |
| 43 | `scalpel_transaction_rollback` | T1 | T1 | **STUB** | P1 (or P3 if doc-only) | Same `_no_op_applier` problem applied per-step in reverse |
| 44 | `scalpel_workspace_health` | T2 | T1 | **HYBRID** | P3 | Real pool-stats + dynamic-registry walker — but `_build_language_health` only iterates `(Language.PYTHON, Language.RUST)` (per skeptic line 832); 11-language v1.4 fleet means TypeScript/Go/C++/Java/Lean/SMT2/Prolog/ProbLog/Markdown projects get empty `languages: {}` |
| 45 | `scalpel_execute_command` | T2 | T1 | **INTENTIONAL** | — | Live allowlist via `coord.execute_command_allowlist`; static `_FALLBACK` rename per DLp5 makes the static set advisory-only |
| 46 | `scalpel_reload_plugins` | T2 | T1 | **INTENTIONAL** | — | Thin wrapper over `runtime.plugin_registry().reload()`; tested |
| 47 | `scalpel_install_lsp_servers` | T2 | T1 | **INTENTIONAL** | — | 15-entry `_installer_registry`; `dry_run=True` default; per-language detect-installed; private API call (`installer._install_command()`) is a smell but functional |

(Rows 1+2 are `_split_python` + `_split_rust` branches of one Tool — counted as separate scoring rows because they have substantially different verdicts. Net unique Tool classes: 43.)

---

## STUB facades — Stage 2 planning candidates

### `scalpel_apply_capability` (`scalpel_primitives.py:273` + helper `:201`)

- **Verdict**: **STUB**
- **Why**: Cross-check at `_dispatch_via_coordinator` (lines 261-270) confirms the skeptic. The function:
  1. Calls `coord.merge_code_actions(...)` (line 228) — real LSP dispatch.
  2. Returns early on `not actions` (line 235) with `applied=False` — honest.
  3. Returns early on `dry_run` (line 253) with `applied=False` — honest.
  4. **Otherwise** (line 261-270): records `runtime.checkpoint_store().record(applied={"changes": {}}, snapshot={})` and returns `RefactorResult(applied=True, ..., checkpoint_id=ckpt_id)` — without ever calling `_resolve_winner_edit` or `_apply_workspace_edit_to_disk`. **The `applied=True` is a lie when measured against the rest of the codebase's contract** (compare `_split_rust` at facades.py:351-353 which DOES resolve+apply, or `_dispatch_single_kind_facade` which is correct downstream).
  5. The explicit `del params, preview_token  # Stage 2A wires these end-to-end` (line 216) is a textbook deferred-implementation marker. Defender's defense ("FALLBACK opener is the contract") protects the *routing semantics* but doesn't excuse the false `applied=True`.
- **Gap**:
  - Line 261: replace `applied={"changes": {}}` with the resolved edit from `_resolve_winner_edit(coord, actions[0])`.
  - Line 261-263: call `_apply_workspace_edit_to_disk(edit)` BEFORE recording the checkpoint, mirroring the pattern in `_split_rust` / `_extract`.
  - Line 216: thread `params` through `coord.merge_code_actions` (or document it as informational and drop the `del`).
  - Add a test that asserts the dispatcher writes a real edit to disk for at least one capability_id (currently `test_apply_capability_dispatches_when_in_workspace` patches `_dispatch_via_coordinator` out and never exercises the body).
- **Effort**: M (90% of the wiring already exists in `_split_rust`; copy the same 5 lines)
- **Priority**: **P1** — this is the long-tail dispatcher claimed to cover ~82% of the catalog (per pragmatic-surveyor.md)
- **Stage 2 hint**: Single PR, mirror `_split_rust:351-368`. Add e2e test against any rust-analyzer assist NOT covered by a named facade (e.g. `assist.move_format_string_arg` or `assist.add_missing_match_arms`).

### `scalpel_dry_run_compose._dry_run_one_step` (`scalpel_primitives.py:340`)

- **Verdict**: **STUB** (helper inside otherwise-real Tool)
- **Why**: Both reviewers agree. `_dry_run_one_step` returns `StepPreview(changes=(), diagnostics_delta=_empty_diagnostics_delta(), failure=None)` regardless of the step's `tool` or `args`. The docstring at line 346-352 ("Virtually apply one step against the in-memory shadow workspace... shadow-workspace mutation lives in Stage 2A") is the explicit deferral. The grammar around it (transaction_id, expires_at, fail-fast walking, manual-mode `_apply_manual_mode`, `_derive_annotation_groups`) IS real — only the per-step preview is fake.
- **Gap**:
  - Wire `_dry_run_one_step` to invoke the dispatched facade in dry_run mode and capture its `RefactorResult.preview_token` + the would-be edit. The dispatch table `_FACADE_DISPATCH` is the obvious lookup.
  - Update the failing test that currently patches `_dry_run_one_step` to inject failures; the new body should produce failures organically when the routed facade returns `failure!=None`.
- **Effort**: L (touches the compose grammar; needs a shadow-workspace stub)
- **Priority**: P2 (the commit path `scalpel_transaction_commit` does dispatch real facades, so the user CAN compose+commit; only the *preview* is empty)
- **Stage 2 hint**: Spec § P5a SHIP-B explicitly ratified shipping without shadow simulation. Talk to the user before committing engineering effort here — this may stay an INTENTIONAL deferral.

### `scalpel_split_file._split_python` (`scalpel_facades.py:275`)

- **Verdict**: **STUB**
- **Why**: Two distinct gaps confirmed by cross-check:
  1. **Symbol lists silently dropped** (line 288): `for group_name in groups.keys()` iterates only keys; the `list[str]` symbol lists are never read. The signature documents `groups: dict[str, list[str]]` as `target_module → [symbol_name, ...]` (line 279) but the body treats it as `dict[str, _Ignored]`.
  2. **No on-disk apply** (line 305): `record_checkpoint_for_workspace_edit(merged, snapshot={})` only stores the edit in the checkpoint store; `facade_support.py:143-151` confirms the helper does NOT apply. Compare with `_split_rust` at line 353 which calls `_apply_workspace_edit_to_disk(edit)`. So the Python branch returns `applied=True, checkpoint_id=cid` while leaving disk untouched.
  3. **5 of 9 parameters dropped** at the top of `apply()`: `parent_layout, keep_in_original, reexport_policy, explicit_reexports, allow_partial`.
- **Gap**: 
  - Line 296 (after `_merge_workspace_edits`): add `_apply_workspace_edit_to_disk(merged)` before `record_checkpoint_for_workspace_edit`.
  - Lines 287-290: rewrite to honor the symbol lists — for each `(group_name, symbols)` pair, call `bridge.move_symbols_to_module(rel, target_rel, symbols)` (or whatever the rope bridge supports), not `bridge.move_module(rel, target_rel)`.
  - Decide policy on the 5 dropped parameters (rip from signature OR thread to rope bridge).
- **Effort**: M (the on-disk apply is a one-liner; the symbol-grouping rewrite needs rope bridge work)
- **Priority**: **P1** — Python users invoking `split_file` get `applied=True` with disk untouched
- **Stage 2 hint**: Mirror the Rust branch's pattern (lines 350-356). Reuse `_apply_workspace_edit_to_disk` from `facade_support`.

### `scalpel_rollback` + `scalpel_transaction_rollback` (`scalpel_primitives.py:670`, `:699`)

- **Verdict**: **STUB** (or **HYBRID** if you accept "rollback = checkpoint bookkeeping only" as the contract)
- **Why**: The skeptic's claim is correct: `_no_op_applier` (line 652-657) returns `0` unconditionally; `ckpt_store.restore(checkpoint_id, _no_op_applier)` walks the store but applies *no inverse edit* to disk. The defender's "idempotency contract" defense is real (the second call IS a no-op) but doesn't address the symmetric stub: if `apply` writes to disk, then `rollback` must read the pre-edit `snapshot` and write it back to disk. Today it doesn't.
- **Gap**: Two paths:
  - **A (real fix, P1)**: Implement a real applier that takes the pre-edit `snapshot` from the checkpoint and writes it back to the file. The checkpoint store's `record()` is called with `snapshot={}` everywhere (e.g. `_dispatch_via_coordinator:262`, `_split_python:305`, `_split_rust:356`) — first close that gap so snapshots are populated, then thread them into the inverse applier.
  - **B (doc-only fix, P3)**: Add a giant `WARNING:` block to both class docstrings stating "rollback marks the checkpoint reverted in the store; it does NOT undo edits to disk. The caller is responsible for re-running the inverse refactor or using their editor's undo stack."
- **Effort**: L for path A; S for path B
- **Priority**: **P1** if path A; P3 if path B
- **Stage 2 hint**: Decide between A and B at planning time. A user expectation survey would help — most LLM-generated workflows assume `scalpel_rollback(ckpt_id)` puts the file back.

### Informational-parameter cluster (Stage 2 batch — 9 facades)

These all exhibit the same pattern: `del <documented_param>` at the top of `apply()`. The defender argues they're "routing signals to the LLM"; the skeptic argues they're contract violations. The truthful diagnosis: rust-analyzer's assist API genuinely doesn't accept these parameters (one-shot, single-rewrite-per-cursor), so the LSP semantically can't honor them. The honest fixes are:

| Facade | Dropped param | Honest fix |
|---|---|---|
| `scalpel_change_visibility` | `target_visibility` | Rewrite signature to remove the param OR open docstring with `Note: target_visibility is informational; rust-analyzer's assist picks the visibility tier per cursor.` |
| `scalpel_change_return_type` | `new_return_type` | Same. Docstring already concedes informational — promote to opener. |
| `scalpel_extract_lifetime` | `lifetime_name` | Same |
| `scalpel_generate_trait_impl_scaffold` | `trait_name` | This one is harder — `trait_name` is a *required* positional. Either thread it to a `coord.execute_command` precheck, or remove it from the signature. |
| `scalpel_introduce_parameter` | `parameter_name` | Same as `change_return_type` |
| `scalpel_generate_from_undefined` | `target_kind` | `target_kind: Literal["function", "class", "variable"]` is the routing intent — defender's "routing signal" claim is most defensible here, but the body doesn't even pass it to `coord.merge_code_actions` `only=` filter. Should at minimum filter actions by `target_kind`. |
| `scalpel_auto_import_specialized` | `symbol_name` | Docstring concedes "v1.1 candidate-set" — at v1.5 this is a 4-version overrun |
| `scalpel_ignore_diagnostic` | `rule` | `rule` is THE knob — without it the facade ignores whichever lint pyright/ruff surfaces first. Should at minimum filter actions by `data.rule` after `merge_code_actions` |
| `scalpel_extract` | 4 params (`new_name, visibility, similar, global_scope`) | Same as `change_visibility`; docstring already names `target` as the only effective routing knob |
| `scalpel_inline` | `name_path, remove_definition` | `name_path` should be honored (resolve via `find_symbol_range` like `_extract` does at line 487-490); `remove_definition` is informational |
| `scalpel_imports_organize` | 3 toggles (`add_missing, remove_unused, reorder`) | Same as `change_visibility`; docstring should opener-tag them informational |
| `scalpel_split_file` (Rust branch) | `groups` | Hard — without `groups` the body is "ask RA for any extract.module action and apply it"; the docstring promises explicit grouping. Either thread groups via `coord.execute_command` to RA's `extractModule` LSP command, or rip the parameter and document the "RA picks" reality. |

- **Effort batch**: M (10-15 facades, mostly docstring tags + signature audits)
- **Priority**: **P2** (no on-disk corruption; only contract clarity)
- **Stage 2 hint**: Pick a policy first (rip vs informational-tag), then execute as a single PR. The defender's argument that these are "router-LLM signals" is reasonable IFF the docstring opener says so.

---

## INTENTIONAL facades — defender wins

| Facade | One-line reason |
|---|---|
| `scalpel_convert_module_layout` | Real dispatcher delegate with kind table; A5 only |
| `scalpel_change_type_shape` | Real 7-entry kind table |
| `scalpel_complete_match_arms` | Dispatcher delegate |
| `scalpel_expand_glob_imports` | Dispatcher delegate |
| `scalpel_generate_member` | Custom 4-entry kind table |
| `scalpel_convert_to_method_object` | `_python_dispatch_single_kind` with unique kind |
| `scalpel_local_to_field` | Same — CAPABILITY_NOT_AVAILABLE when pylsp-rope absent IS the contract |
| `scalpel_use_function` | Same |
| `scalpel_convert_to_async` | Real `python_async_conversion` helper + dedicated test |
| `scalpel_annotate_return_type` | Real `python_return_type_infer` helper + dedicated test |
| `scalpel_convert_from_relative_imports` | Real `python_imports_relative` helper + dedicated test |
| `scalpel_rename_heading` | Custom regex pre-resolution + marksman LSP rename |
| `scalpel_split_doc` | Real `markdown_doc_ops` helper + CreateFile resource ops |
| `scalpel_extract_section` | Same |
| `scalpel_organize_links` | Same |
| `scalpel_transaction_commit` | Walks `_FACADE_DISPATCH` (35 entries); inherits child stubness but dispatcher is real |
| `scalpel_capabilities_list` | Catalog reader with `preferred_facade` field |
| `scalpel_capability_describe` | Fuzzy-match error recovery |
| `scalpel_confirm_annotations` | 62-line label-filter walker; real on-disk apply |
| `scalpel_execute_command` | Live allowlist via `coord.execute_command_allowlist` |
| `scalpel_reload_plugins` | Real `runtime.plugin_registry().reload()` + tested |
| `scalpel_install_lsp_servers` | 15-entry registry; `dry_run=True` safety; per-language detect+probe |

22 INTENTIONAL.

---

## Universal findings

### A5 — Examples blocks (43/43 facades fail)

Zero `Examples:` blocks in either file. `grep -c "Examples\?:" scalpel_facades.py scalpel_primitives.py` returns `0` and `0`. The `PREFERRED:`/`FALLBACK:` opener convention from spec § 5.2.1 IS shipped (33/33 named facades + 1/1 FALLBACK), but no facade carries a `>>> tool.apply(...)` or fenced-code example.

**Diagnosis**: this is a doc convention gap, not a stub signal. The spec doesn't require Examples; the LLM router has the asymmetric `PREFERRED:`/`FALLBACK:` token plus the `:param` typed signatures plus the dynamic-capability gating. Adding Examples would help LLMs ground argument shapes (especially for `range`/`position` LSP dicts and the `groups: dict[str, list[str]]` shape) but is not a Stage-2 priority.

**Recommendation**: Stage 4 polish task — generate one `Examples:` block per facade from the existing test fixtures.

### A4 — Documented-parameter ablation (17 facades, varying severity)

The skeptic's strongest universal critique. Tally:

- **17 facades** `del` at least one documented parameter in `apply()`.
- **Of those 17**:
  - **3** are honestly tagged in their docstring as informational (`scalpel_fix_lints.rules`, `scalpel_change_return_type.new_return_type`, `scalpel_auto_import_specialized.symbol_name`). Honest deferral; tag is buried though.
  - **2** have explicit Phase-2.5 comment markers (`scalpel_generate_constructor.include_fields`, `scalpel_override_methods.method_names`). Honest deferral.
  - **12** silently drop the parameter without any docstring acknowledgement. **These are the Stage-2 cluster.**

Stage 2 should pick a uniform policy (rip from signature OR opener-tag informational) and ship across the cluster.

---

## Cross-check evidence

The four most contentious verdicts, with source-code evidence inline.

### Cross-check 1: `_dispatch_via_coordinator` (the FALLBACK dispatcher)

Source — `scalpel_primitives.py:201-270`:

```python
def _dispatch_via_coordinator(
    capability, file, range_or_name_path, params, *, dry_run, preview_token, project_root,
) -> RefactorResult:
    """Drive the Stage 1D coordinator + Stage 1B applier.

    Stage 1G ships the dispatcher *plumbing*; the Stage 2A ergonomic
    facades exercise the full code-action -> resolve -> apply pipeline.
    """
    del params, preview_token  # Stage 2A wires these end-to-end
    # ...
    actions = coord.merge_code_actions(
        file=file,
        start=rng["start"], end=rng["end"],
        only=[capability.kind],
    )
    # ... no_actions / dry_run early returns are honest ...
    ckpt_id = runtime.checkpoint_store().record(
        applied={"changes": {}},                          # <-- EMPTY EDIT recorded
        snapshot={},
    )
    return RefactorResult(
        applied=True,                                     # <-- claims success
        diagnostics_delta=_empty_diagnostics_delta(),
        checkpoint_id=ckpt_id,
        duration_ms=elapsed_ms,
    )
```

**Adjudication**: skeptic wins. The defender's defense ("FALLBACK opener is the contract; spec § 6 preserves the dispatcher") protects the *existence* of the long-tail dispatcher but does not excuse `applied=True` paired with `applied={"changes": {}}`. Compare with `_split_rust` at `scalpel_facades.py:351-356` which DOES `_resolve_winner_edit` and `_apply_workspace_edit_to_disk` before recording — the canonical pattern exists in the codebase and is missing here.

### Cross-check 2: `_split_python` vs `_split_rust`

`_split_python` (scalpel_facades.py:275):

```python
def _split_python(self, *, file, groups, project_root, dry_run):
    bridge = _build_python_rope_bridge(project_root)
    edits: list[dict[str, Any]] = []
    try:
        rel = str(Path(file).relative_to(project_root))
        for group_name in groups.keys():           # <-- only KEYS iterated
            target_rel = f"{group_name}.py"
            edits.append(bridge.move_module(rel, target_rel))   # <-- moves, doesn't split
    finally:
        ...
    merged = _merge_workspace_edits(edits)
    # ...
    cid = record_checkpoint_for_workspace_edit(merged, snapshot={})
    return RefactorResult(applied=True, ...)        # <-- NO _apply_workspace_edit_to_disk
```

`_split_rust` (scalpel_facades.py:319):

```python
def _split_rust(self, *, file, groups, project_root, dry_run):
    del groups
    # ...
    actions = _run_async(coord.merge_code_actions(...))
    # ...
    edit = _resolve_winner_edit(coord, actions[0])
    if isinstance(edit, dict) and edit:
        _apply_workspace_edit_to_disk(edit)         # <-- DOES apply
    else:
        edit = {"changes": {}}
    cid = record_checkpoint_for_workspace_edit(workspace_edit=edit, snapshot={})
```

**Adjudication**: skeptic wins on Python branch (no `_apply_workspace_edit_to_disk`); HYBRID on Rust branch (real apply but `del groups`).

### Cross-check 3: `scalpel_extract.name_path` (defender's claimed find_symbol_range path)

Source — `scalpel_facades.py:482-498`:

```python
# When the caller passes only ``name_path``, resolve it to a range via
# the coordinator's document-symbols walk. ...
if range is None and name_path is not None:
    range = _run_async(coord.find_symbol_range(
        file=file, name_path=name_path,
        project_root=str(project_root),
    ))
    if range is None:
        return build_failure_result(
            code=ErrorCode.SYMBOL_NOT_FOUND, ...
        ).model_dump_json(indent=2)
```

**Adjudication**: defender wins on `name_path` resolution. The skeptic's verdict that `_extract` is T1 is overstated — `name_path` IS resolved. But `del new_name, visibility, similar, global_scope, preview_token` (line 440) IS still real, so HYBRID is the honest verdict.

### Cross-check 4: `_no_op_applier` (rollback)

Source — `scalpel_primitives.py:652-657`:

```python
def _no_op_applier(_: dict[str, Any]) -> int:
    """Stage 1G synthetic applier — exists so checkpoint_store.restore
    can be invoked without spinning up a real LSP. Returns 0 so restore()
    surfaces as ``no_op=True`` in RefactorResult.
    """
    return 0
```

Used at lines 690 (`ScalpelRollbackTool`) and 727 (`ScalpelTransactionRollbackTool`).

**Adjudication**: skeptic wins. The applier never inverts on-disk state. Defender's "idempotency contract" defense is true but tangential — the user-visible contract for `rollback(ckpt_id)` is "put the file back to pre-edit state", and this implementation cannot. Either fix the applier (P1) or warn aggressively in the docstring (P3 doc-only).

---

## Score

- **Skeptic was right on**: `apply_capability` (FALLBACK lies), `_dry_run_one_step` (defender concedes), `_split_python` (no on-disk apply), rollback pair (`_no_op_applier`), 12 silently-dropped parameters in HYBRID facades.
- **Defender was right on**: `_extract.name_path` resolution, the dispatcher-delegation pattern (SOLID/DRY justification), the `CAPABILITY_NOT_AVAILABLE` envelope as legitimate contract, the markdown facades, the 3 v1.1 Python facades, all 22 INTENTIONAL verdicts.
- **Universal**: A5 (Examples) is real but soft; A4 (parameter ablation) is real and Stage-2 actionable.

The skeptic's framing was sharper for the 4 STUB cases; the defender's framing was correct for 22 INTENTIONAL cases; both were partially right on the 18 HYBRID cases.

**Top priority**: fix `_dispatch_via_coordinator:261-270` to mirror `_split_rust:351-356`. One PR, ~8 lines, closes the highest-confidence stub in the audit.
