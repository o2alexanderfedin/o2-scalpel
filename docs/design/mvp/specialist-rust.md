# MVP Brainstorm — Rust Language Specialist (Full-Coverage Round)

Status: report-only. Brainstorming input for the o2.scalpel MVP rescoping under the **full-LSP-coverage directive**.
Authoritative design: [`2026-04-24-serena-rust-refactoring-extensions-design.md`](../2026-04-24-serena-rust-refactoring-extensions-design.md).
Capabilities reference: [`2026-04-24-rust-analyzer-capabilities-brief.md`](../../research/2026-04-24-rust-analyzer-capabilities-brief.md).
Protocol reference: [`2026-04-24-mcp-lsp-protocol-brief.md`](../../research/2026-04-24-mcp-lsp-protocol-brief.md).
Prior (narrower) position: [`archive-v1-narrow/specialist-rust.md`](archive-v1-narrow/specialist-rust.md).
Prior synthesis: [`archive-v1-narrow/2026-04-24-mvp-scope-report.md`](archive-v1-narrow/2026-04-24-mvp-scope-report.md).

---

## 0. Directive change & what it inverts

The previous round (`archive-v1-narrow/`) cut Rust depth aggressively to keep dual-language MVP cheap: 6 of 158 rust-analyzer assists wrapped as facades, ~2,310 LoC on the Rust side, 5 of 33 custom extensions whitelisted (and even those flagged as "Rust-next, drop from MVP"). The product owner has now **reversed that compression**.

New directive, restated for self-discipline:

> For the LSPs we choose, we must fully support the LSP's features. Language count for MVP priority stays at 2 (Rust + Python). Within rust-analyzer, we commit to **full capability coverage** — every assist reachable, every WorkspaceEdit shape applied, every custom extension callable, every advertised capability wired.

What "full coverage" does NOT mean:

| Misreading | Correct reading |
|---|---|
| 158 bespoke facades. | A **small set of facades** (~12–18) covering every assist *family*, plus a generic `list_code_actions → resolve → apply` chain that makes the long tail reachable. No capability is silently unavailable. |
| Every custom extension exposed as a first-class MCP tool. | All 33 are **callable** via `execute_command` against a typed whitelist. The 6–8 the LLM benefits from become first-class; the rest are reachable through the typed pass-through. |
| `viewHir`/`viewMir`/`viewCrateGraph` ship as polished IDE tools. | These are debug views meaningless to autonomous LLMs. They live in the typed pass-through. Not blocked, not promoted. |
| Every advertised LSP method must be wrapped before MVP. | Every method r-a advertises must be **wired end-to-end** (request shape, response shape, error handling). Some — `inlayHint`, `documentLink`, `selectionRange` — are wired but not surfaced as facades because their value lives in the Read tool family Claude Code already owns. Wired ≠ facaded. |

The single most important consequence of the directive change for Rust: **every shortcut the narrow MVP took to limit interface surface is back on the table**. The narrow MVP's "depth, not breadth" rule is reversed: full breadth, full depth, but with discipline about *which* surface the LLM sees vs. which surface stays under the hood.

---

## 1. Capability inventory — 158 assists, classified

This is the central deliverable. Every assist registered in rust-analyzer's `crates/ide-assists/src/lib.rs::all()` is grouped by family and assigned an exposure mode:

- **(a) Generic primitive only** — `list_code_actions`/`apply_code_action` reaches it. No facade. The LLM invokes it by name through the primitive layer.
- **(b) Wrapped in a task-level facade** — covered by an existing or proposed facade. The LLM never names the assist.
- **(c) Requires a NEW facade for full-coverage MVP** — promoted to first-class because LLM agents repeatedly compose this assist into multi-step refactors and the orchestration costs justify a dedicated tool.
- **(d) Reachable only via `execute_command` pass-through** — the assist is technically a code action but is invoked through r-a's command path or has no clean code-action invocation surface.

Source of truth: `crates/ide-assists/src/handlers/` paths, registry in `lib.rs`. Counts checked against the capabilities brief (158 distinct handler entries).

### 1.1 Family A — Module / file boundary (4 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `extract_module` | `extract_module.rs` | (b) | `extract_symbols_to_module`, `split_file_by_symbols` |
| `move_module_to_file` | `move_module_to_file.rs` | (b) | `move_inline_module_to_file`, internal step of `split_file_by_symbols` |
| `move_from_mod_rs` | `move_from_mod_rs.rs` | (c) | NEW: `convert_module_layout` |
| `move_to_mod_rs` | `move_to_mod_rs.rs` | (c) | NEW: `convert_module_layout` |

**Family verdict:** core split workflow; `convert_module_layout` is new for full coverage to handle both layout swaps in one symmetric facade.

### 1.2 Family B — Extractors (8 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `extract_function` | `extract_function.rs` | (c) | NEW: `extract_expression` (kind=`function`) |
| `extract_variable` | `extract_variable.rs` | (c) | NEW: `extract_expression` (kind=`variable`) |
| `extract_type_alias` | `extract_type_alias.rs` | (c) | NEW: `extract_expression` (kind=`type_alias`) |
| `extract_struct_from_enum_variant` | `extract_struct_from_enum_variant.rs` | (c) | NEW: `extract_struct_from_enum_variant` |
| `extract_expressions_from_format_string` | `extract_expressions_from_format_string.rs` | (a) | — |
| `promote_local_to_const` | `promote_local_to_const.rs` | (b) | sub-step of `extract_expression` (kind=`constant`) |
| `extract_constant` (variant of `extract_variable`) | `extract_variable.rs` | (b) | inside `extract_expression` |
| `extract_static` (variant of `extract_variable`) | `extract_variable.rs` | (b) | inside `extract_expression` |

**Family verdict:** the LLM uses extraction relentlessly when shaping code before a split. A unified `extract_expression(file, range, kind, new_name)` facade collapses 6 assists into one tool. `extract_struct_from_enum_variant` stays separate (different selection semantics).

### 1.3 Family C — Inliners (5 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `inline_local_variable` | `inline_local_variable.rs` | (b) | NEW: `inline_symbol` |
| `inline_call` | `inline_call.rs` | (b) | NEW: `inline_symbol` (variant=`call_site`) |
| `inline_into_callers` | `inline_call.rs` | (b) | NEW: `inline_symbol` (variant=`all_callers`) |
| `inline_type_alias` / `inline_type_alias_uses` | `inline_type_alias.rs` | (b) | NEW: `inline_symbol` (kind=`type_alias`) |
| `inline_macro` | `inline_macro.rs` | (b) | NEW: `inline_symbol` (kind=`macro`) |
| `inline_const_as_literal` | `inline_const_as_literal.rs` | (b) | NEW: `inline_symbol` (kind=`const`) |

**Family verdict:** dual of Family B. `inline_symbol(file, position, kind?, scope?)` covers all six variants. The `scope: "single_call_site" | "all_callers"` flag selects between `inline_call` and `inline_into_callers`.

### 1.4 Family D — Imports (10 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `auto_import` | `auto_import.rs` | (b) | `fix_imports(add_missing=True)` |
| `qualify_path` | `qualify_path.rs` | (b) | `fix_imports(disambiguate=True)` |
| `replace_qualified_name_with_use` | `replace_qualified_name_with_use.rs` | (b) | `fix_imports(unqualify=True)` |
| `remove_unused_imports` | `remove_unused_imports.rs` | (b) | `fix_imports(remove_unused=True)` |
| `merge_imports` | `merge_imports.rs` | (b) | `fix_imports(reorder=True)` |
| `unmerge_imports` | `unmerge_imports.rs` | (b) | `fix_imports(reorder=True, style="flat")` |
| `normalize_import` | `normalize_import.rs` | (b) | `fix_imports(reorder=True)` |
| `split_import` | `split_import.rs` | (b) | `fix_imports(reorder=True, style="flat")` |
| `expand_glob_import` | `expand_glob_import.rs` | (a) + (c) | NEW: `expand_glob_imports` (workspace-scoped) |
| `expand_glob_reexport` | `expand_glob_reexport.rs` | (a) + (c) | NEW: `expand_glob_imports(include_reexports=True)` |

**Family verdict:** expand `fix_imports` from a 3-flag tool to a fully-flagged import surgeon. Add `expand_glob_imports` as a separate facade because it has different ergonomics (it changes public API, not just hygiene).

### 1.5 Family E — Visibility (2 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `change_visibility` | `change_visibility.rs` | (c) | NEW: `change_visibility` |
| `fix_visibility` | `fix_visibility.rs` | (b) | `fix_imports(fix_visibility=True)` AND auto-fired by `split_file_by_symbols` |

**Family verdict:** `change_visibility(file, name_path, new_visibility)` is the proactive form (LLM decides). `fix_visibility` is the diagnostic-driven cleanup form, fired automatically by the split pipeline.

### 1.6 Family F — Ordering / structural (3 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `reorder_impl_items` | `reorder_impl_items.rs` | (b) | NEW: `tidy_structure` (option=`impl_order`) |
| `sort_items` | `sort_items.rs` | (b) | NEW: `tidy_structure` (option=`item_order`) |
| `reorder_fields` | `reorder_fields.rs` | (b) | NEW: `tidy_structure` (option=`field_order`) |

**Family verdict:** `tidy_structure(file, scope, options[])` collapses three cosmetic-but-LSP-aware reorderings into one tool. Useful before splitting (consistent ordering reduces diff noise).

### 1.7 Family G — Generators / scaffolders (~32 assists)

The `generate_*` family. Listed by handler name:

`generate_constant`, `generate_default_from_enum_variant`, `generate_default_from_new`, `generate_delegate_methods`, `generate_delegate_trait`, `generate_deref`, `generate_derive`, `generate_documentation_template`, `generate_documentation_template_for_module`, `generate_enum_is_method`, `generate_enum_projection_method`, `generate_enum_variant`, `generate_fn_type_alias`, `generate_from_impl_for_enum`, `generate_function`, `generate_getter`, `generate_getter_or_setter`, `generate_impl`, `generate_impl_from`, `generate_is_empty_from_len`, `generate_mut_trait_method`, `generate_new`, `generate_setter`, `generate_trait_from_impl`, `generate_trait_impl`, `generate_impl_trait`, `generate_constant_for_enum_variant`, `generate_const_default_for_const`.

| Sub-family | Assists | Mode | Facade |
|---|---|---|---|
| Trait-impl scaffolding | `generate_impl`, `generate_trait_impl`, `generate_impl_trait`, `generate_trait_from_impl`, `generate_from_impl_for_enum`, `generate_impl_from`, `generate_default_from_enum_variant`, `generate_default_from_new` | (c) | NEW: `generate_trait_impl_scaffold` |
| Method scaffolding | `generate_function`, `generate_getter`, `generate_setter`, `generate_getter_or_setter`, `generate_new`, `generate_delegate_methods`, `generate_delegate_trait`, `generate_mut_trait_method`, `generate_deref`, `generate_is_empty_from_len`, `generate_enum_is_method`, `generate_enum_projection_method` | (c) | NEW: `generate_member` |
| Item scaffolding | `generate_enum_variant`, `generate_constant`, `generate_constant_for_enum_variant`, `generate_const_default_for_const`, `generate_fn_type_alias`, `generate_derive` | (a) | reached via `list_code_actions` |
| Documentation | `generate_documentation_template`, `generate_documentation_template_for_module` | (a) | reached via `list_code_actions` |

**Family verdict:** two new facades cover ~20 of the 32 generators. The remaining ~12 are item-level scaffolders the LLM handles textually faster than via codeAction round-trip; left in (a) — reachable but not facaded.

### 1.8 Family H — Convert / rewrite (~40 assists)

The `convert_*`, `apply_*`, `replace_*`, `flip_*`, `wrap_*`, `unwrap_*`, `toggle_*`, `unmerge_*`, `desugar_*`, `bind_unused_param` family. Indicative members: `apply_demorgan`, `apply_demorgan_iterator`, `bind_unused_param`, `bool_to_enum`, `convert_bool_then_to_if`, `convert_closure_to_fn`, `convert_for_loop_with_query_to_match`, `convert_from_to_tryfrom`, `convert_if_to_bool_then`, `convert_integer_literal`, `convert_into_to_from`, `convert_iter_for_each_to_for`, `convert_let_else_to_match`, `convert_match_to_let_else`, `convert_named_struct_to_tuple_struct`, `convert_nested_function_to_closure`, `convert_to_guarded_return`, `convert_tuple_return_type_to_struct`, `convert_tuple_struct_to_named_struct`, `convert_two_arm_bool_match_to_matches_macro`, `desugar_async_into_impl_future`, `desugar_doc_comment`, `desugar_method_call`, `flip_binexpr`, `flip_comma`, `flip_or_pattern`, `flip_trait_bound`, `move_arm_cond_to_match_guard`, `move_const_to_impl`, `move_format_string_arg`, `move_guard`, `pull_assignment_up`, `raw_string`, `replace_arith_op`, `replace_derive_with_manual_impl`, `replace_if_let_with_match`, `replace_is_method_with_if_let_else`, `replace_let_with_if_let`, `replace_match_with_if_let`, `replace_method_eager_lazy`, `replace_named_generic_with_impl`, `replace_string_with_char`, `replace_try_expr_with_match`, `replace_turbofish_with_explicit_type`, `replace_with_eager_method`, `replace_with_lazy_method`, `toggle_async_sugar`, `toggle_ignore`, `toggle_macro_delimiter`, `unmerge_match_arm`, `unwrap_block`, `unwrap_option_return_type`, `unwrap_result_return_type`, `unwrap_tuple`, `wrap_return_type` (in_option/in_result/etc.), `wrap_unwrap_cfg_attr`.

| Sub-family | Mode | Facade |
|---|---|---|
| Boolean / pattern rewrites (`apply_demorgan`, `flip_*`, `convert_bool_then_to_if`, `convert_two_arm_bool_match_to_matches_macro`, etc.) | (a) | reachable via primitives |
| Control-flow rewrites (`convert_for_loop_*`, `convert_iter_*`, `replace_if_let_with_match`, `replace_match_with_if_let`, `convert_let_else_to_match`, `convert_match_to_let_else`, `move_guard`, `move_arm_cond_to_match_guard`, `convert_to_guarded_return`, `pull_assignment_up`) | (a) | reachable via primitives |
| Type-shape rewrites (`convert_named_struct_to_tuple_struct`, `convert_tuple_struct_to_named_struct`, `convert_tuple_return_type_to_struct`, `bool_to_enum`, `unwrap_tuple`) | (c) | NEW: `change_type_shape` |
| Return-type wrapping (`wrap_return_type`, `unwrap_option_return_type`, `unwrap_result_return_type`) | (c) | NEW: `change_return_type` |
| Async/sugar (`desugar_async_into_impl_future`, `toggle_async_sugar`, `desugar_doc_comment`, `desugar_method_call`) | (a) | reachable via primitives |
| Trait-bound / generics (`convert_closure_to_fn`, `convert_nested_function_to_closure`, `replace_named_generic_with_impl`, `replace_turbofish_with_explicit_type`, `flip_trait_bound`, `convert_from_to_tryfrom`, `convert_into_to_from`, `replace_derive_with_manual_impl`) | (a) | reachable via primitives |
| String / literal (`raw_string`, `replace_string_with_char`, `convert_integer_literal`, `move_format_string_arg`) | (a) | reachable via primitives |
| Method-call eagerness (`replace_method_eager_lazy`, `replace_with_eager_method`, `replace_with_lazy_method`, `replace_is_method_with_if_let_else`, `replace_let_with_if_let`, `replace_try_expr_with_match`) | (a) | reachable via primitives |
| Misc (`bind_unused_param`, `move_const_to_impl`, `unmerge_match_arm`, `unwrap_block`, `wrap_unwrap_cfg_attr`, `toggle_ignore`, `toggle_macro_delimiter`) | (a) | reachable via primitives |

**Family verdict:** ~36 of ~40 stay in (a). Two new narrow facades (`change_type_shape`, `change_return_type`) elevate the high-value type-shape rewrites because they have multi-file consequences a naive primitive caller would miss (every `Foo` → `(T, U)` flip needs callers updated).

### 1.9 Family I — Pattern / destructuring (5 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `add_missing_match_arms` | `add_missing_match_arms.rs` | (b) | NEW: `complete_match_arms` |
| `add_missing_impl_members` | `add_missing_impl_members.rs` | (b) | `generate_trait_impl_scaffold(complete_missing=True)` |
| `add_missing_default_impl_members` | (same handler family) | (b) | same |
| `destructure_struct_binding` | `destructure_struct_binding.rs` | (a) | reachable via primitives |
| `destructure_tuple_binding` | `destructure_tuple_binding.rs` | (a) | reachable via primitives |

### 1.10 Family J — Lifetimes & references (4 assists)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `add_explicit_lifetime_to_self` | (lifetime family) | (a) | reachable via primitives |
| `extract_explicit_lifetime` | (lifetime family) | (c) | NEW: `extract_lifetime` |
| `replace_named_generic_with_impl` | (lifetime/generics family) | (a) | reachable via primitives |
| `add_explicit_type` | (type-annotation family) | (a) | reachable via primitives |

### 1.11 Family K — `term_search` and synthesis (1 assist)

| Assist | Handler | Mode | Facade |
|---|---|---|---|
| `term_search` | `term_search.rs` | (d) | reachable only via primitives — power-user assist that synthesizes a term inhabiting a hole `_`. Documented separately. |

### 1.12 Family L — Quickfixes bound to diagnostics (~30 assists)

These are not registered in `all()` as standalone assists but emerge through the diagnostic → codeAction binding. Members include: `add_missing_semicolon`, `add_explicit_type`, `add_reference_here`, `add_turbo_fish`, `add_lifetime_to_type`, `wrap_in_async_block`, `add_async_keyword`, `make_function_async`, `make_function_const`, `replace_filter_map_next_with_find_map`, etc.

| Mode | Approach |
|---|---|
| (b) | All diagnostic-bound quickfixes flow through `fix_imports(add_missing=True)` and the implicit "post-apply diagnostic sweep" inside every mutating facade. |

### 1.13 Family roll-up

| Family | Count | (a) primitive only | (b) covered by facades | (c) needs NEW facade | (d) pass-through |
|---|---|---|---|---|---|
| A — Module/file | 4 | 0 | 2 | 2 | 0 |
| B — Extractors | 8 | 1 | 3 | 4 | 0 |
| C — Inliners | 5 | 0 | 5 | 0 | 0 |
| D — Imports | 10 | 0 | 8 | 2 | 0 |
| E — Visibility | 2 | 0 | 1 | 1 | 0 |
| F — Ordering | 3 | 0 | 0 | 3 | 0 |
| G — Generators | 32 | 6 + 2 = 8 | 0 | 24 | 0 |
| H — Convert/rewrite | 40 | 36 | 0 | 4 | 0 |
| I — Pattern | 5 | 2 | 2 | 1 | 0 |
| J — Lifetimes | 4 | 3 | 0 | 1 | 0 |
| K — term_search | 1 | 0 | 0 | 0 | 1 |
| L — Quickfix | ~30 | 0 | ~30 | 0 | 0 |
| **Totals** | **~144** + (~14 quickfix overlap) ≈ **158** | **~50** | **~51** | **~42** | **~1** |

Reading: of the 158, **~93 are reached via facades (b+c)** and **~50 via the primitive escape hatch (a)** plus **~1 via typed pass-through (d)**. The previous round had 6 of 158 facaded. Full coverage as proposed has roughly 93 of 158 facaded — a 15× expansion in facade reach without a 15× expansion in tool count, because facades are *families*.

---

## 2. Facade list for full coverage (proposed canonical set)

The narrow MVP shipped 6 facades. Full coverage adds ~12, reaching **~18 facades**. Each is one MCP tool with a docstring under 30 words.

### 2.1 Inherited from the narrow MVP (unchanged surface)

| # | Facade | One-line docstring |
|---|---|---|
| 1 | `plan_file_split` | Read-only. Suggest module groups by clustering symbols against the call/type-reference graph. |
| 2 | `split_file_by_symbols` | Mutating. Split a file into N modules atomically, emitting CreateFile + parent-mod declarations + import fixup. |
| 3 | `extract_symbols_to_module` | Mutating. Move named symbols into a single new module — wrapper over `split_file_by_symbols` for the 1-group case. |
| 4 | `move_inline_module_to_file` | Mutating. Convert an inline `mod foo { ... }` into a separate file with a `mod foo;` declaration in the parent. |
| 5 | `fix_imports` | Mutating. Adds missing imports, removes unused imports, merges/normalizes/splits, raises visibility, disambiguates qualified paths. |
| 6 | `rollback_refactor` | Recovery. Replays the inverse WorkspaceEdit captured at apply-time for a `checkpoint_id`. |

### 2.2 New for full coverage

| # | Facade | One-line docstring | Family |
|---|---|---|---|
| 7 | `convert_module_layout` | Mutating. Toggle a module between `foo.rs` ↔ `foo/mod.rs` layouts (`move_from_mod_rs` / `move_to_mod_rs`). | A |
| 8 | `extract_expression` | Mutating. Extract a selected range into a new function / variable / const / static / type alias. | B |
| 9 | `extract_struct_from_enum_variant` | Mutating. Promote an enum variant's payload into a standalone struct, updating callers. | B |
| 10 | `inline_symbol` | Mutating. Inline a local variable / function call / type alias / macro / const, optionally at a single call site or all callers. | C |
| 11 | `expand_glob_imports` | Mutating. Replace `use foo::*` with explicit member imports throughout a file or workspace scope. | D |
| 12 | `change_visibility` | Mutating. Set or cycle visibility on a named item (`pub`, `pub(crate)`, `pub(super)`, private). | E |
| 13 | `tidy_structure` | Mutating. Reorder impl items, top-level items, and/or struct fields to a canonical order. | F |
| 14 | `generate_trait_impl_scaffold` | Mutating. Generate or complete an `impl Trait for Type` block, optionally filling missing default-method bodies. | G |
| 15 | `generate_member` | Mutating. Generate a function / getter / setter / `new` constructor / delegate method on a target type. | G |
| 16 | `change_type_shape` | Mutating. Convert named ↔ tuple struct, wrap a return type in `Option`/`Result`, or unwrap. Updates callers. | H |
| 17 | `change_return_type` | Mutating. Wrap, unwrap, or replace a function's return type, propagating diagnostics through callers. | H |
| 18 | `complete_match_arms` | Mutating. Add missing arms to a `match` expression based on the inhabited variants. | I |
| 19 | `extract_lifetime` | Mutating. Promote an elided or `'_` lifetime to a named generic. | J |

### 2.3 What "facade" promises that "primitive escape hatch" does not

For each of the 13 new facades, the value over a primitive `apply_code_action(id)` call is exactly four things, and all four are required for the LLM-driven workflow:

1. **Name-path addressing.** The facade accepts `name_path: "module::function"`, never a byte range. Internally the facade resolves to a range via `documentSymbol`. The primitive layer accepts `range: {start, end}` directly because power-users sometimes want it; the facade refuses byte ranges except where there is no symbolic addressing available (e.g., `extract_expression` over a sub-expression range — there is no name for that range).
2. **Atomic checkpoint capture.** Every mutating facade snapshots affected files before applying and stores an inverse WorkspaceEdit under a `checkpoint_id`. The LLM gets `rollback_refactor(checkpoint_id)` as its only safety net.
3. **Diagnostics-delta gating.** Strict-mode default: if `diagnostics_delta.severity_breakdown["error"].after > 0`, rollback and return `failure` — no matter what the LSP said. Primitives don't gate; they apply whatever WorkspaceEdit comes back.
4. **Idempotent semantics.** Calling the facade twice with the same input either returns `applied: True, no_op: True` (already at target state) or fails fast with a clear "stale precondition" error. Primitives are not idempotent.

Every facade in §2.1–§2.2 conforms to this contract. If the contract cannot be honored (e.g., `term_search` has no symbolic input), the assist is **not** facaded — it stays in the primitive layer.

---

## 3. rust-analyzer custom extensions — typed whitelist

All 33 from `docs/book/src/contributing/lsp-extensions.md`. Each gets a verdict in `{expose_directly, whitelist_for_execute_command, explicit_block}`.

| # | Method | Namespace | I/O | Verdict | Justification |
|---|---|---|---|---|---|
| 1 | `experimental/parentModule` | exp | TDPP → Location[] | **expose_directly** | Used by `plan_file_split` to identify parent-module boundaries. First-class because facades depend on it. |
| 2 | `experimental/joinLines` | exp | JoinLinesParams → TextEdit[] | whitelist_for_execute_command | Cosmetic. LLM can use it; no facade needed. |
| 3 | `experimental/onEnter` | exp | TDPP → SnippetTextEdit[] | **explicit_block** | Editor-context-only (responds to a literal Enter keystroke). Has no meaning for an autonomous LLM. Block. |
| 4 | `experimental/matchingBrace` | exp | positions → positions | whitelist_for_execute_command | Trivially useful; no facade. |
| 5 | `experimental/ssr` | exp | SsrParams → WorkspaceEdit | **expose_directly** | Structural search/replace is a power tool. New facade `structural_search_replace(pattern, template, files?)` justified by frequent LLM use cases ("rename every call to `foo::bar(x)` → `baz::qux(x, default)`"). |
| 6 | `experimental/runnables` | exp | RunnablesParams → Runnable[] | **expose_directly** | Used by `verify_after_refactor` (new facade, §3.1) to identify what to run. |
| 7 | `experimental/externalDocs` | exp | TDPP → string\|null | whitelist_for_execute_command | Doc URL retrieval. Useful occasionally; no facade. |
| 8 | `experimental/openCargoToml` | exp | params → Location | whitelist_for_execute_command | Locating `Cargo.toml` is occasionally useful. |
| 9 | `experimental/moveItem` | exp | MoveItemParams → SnippetTextEdit[] | whitelist_for_execute_command | Within-scope reorder. Subsumed by `tidy_structure` for the canonical-order case; fine via pass-through. |
| 10 | `experimental/serverStatus` (notification) | exp | — | **expose_directly** | Health/quiescent state. Used internally by `wait_for_indexing`; surfaces to LLM as `workspace_health()`. |
| 11 | `experimental/discoverTest` | exp | — | whitelist_for_execute_command | Test Explorer surface. |
| 12 | `experimental/runTest` | exp | — | whitelist_for_execute_command | Test Explorer surface. |
| 13 | `experimental/endRunTest` | exp | — | whitelist_for_execute_command | Test Explorer surface. |
| 14 | `experimental/abortRunTest` | exp | — | whitelist_for_execute_command | Test Explorer surface. |
| 15 | `experimental/changeTestState` (notif) | exp | — | whitelist_for_execute_command | Test Explorer notification. |
| 16 | `experimental/appendOutputToRunTest` (notif) | exp | — | whitelist_for_execute_command | Test Explorer notification. |
| 17 | `experimental/discoveredTests` (notif) | exp | — | whitelist_for_execute_command | Test Explorer notification. |
| 18 | `rust-analyzer/analyzerStatus` | ra | — → string | whitelist_for_execute_command | Diagnostic dump; debug-grade. |
| 19 | `rust-analyzer/reloadWorkspace` | ra | — | **expose_directly** | Required after external `Cargo.toml` edits; surfaced as `reload_workspace()` facade because the LLM may legitimately want to invoke it. |
| 20 | `rust-analyzer/rebuildProcMacros` | ra | — | **expose_directly** | Same — proc-macro recompile is occasionally needed mid-refactor. Surfaced as `rebuild_proc_macros()`. |
| 21 | `rust-analyzer/runFlycheck` | ra | RunFlycheckParams | **expose_directly** | Forces a `cargo check`; surfaces as `run_flycheck(scope?)` and is used as the post-apply gate when strict-mode demands it. |
| 22 | `rust-analyzer/cancelFlycheck` | ra | — | whitelist_for_execute_command | |
| 23 | `rust-analyzer/clearFlycheck` | ra | — | whitelist_for_execute_command | |
| 24 | `rust-analyzer/viewSyntaxTree` | ra | TDPP → string | whitelist_for_execute_command | Power-user debugging only. |
| 25 | `rust-analyzer/viewHir` | ra | TDPP → string | whitelist_for_execute_command | **Not promoted.** HIR dump is a compiler-debug tool with no autonomous-LLM use case. Reachable for power users; not surfaced. |
| 26 | `rust-analyzer/viewMir` | ra | TDPP → string | whitelist_for_execute_command | Same as HIR. |
| 27 | `rust-analyzer/viewFileText` | ra | TextDocumentIdentifier → string | whitelist_for_execute_command | "File as the server sees it" — useful debugging, niche. |
| 28 | `rust-analyzer/viewItemTree` | ra | TextDocumentIdentifier → string | **expose_directly** | Used internally by `plan_file_split` as a faster `documentSymbol`. Surfaces to the LLM as a read tool. |
| 29 | `rust-analyzer/viewCrateGraph` | ra | bool → string (SVG) | whitelist_for_execute_command | SVG output. Not LLM-friendly; reachable but not promoted. |
| 30 | `rust-analyzer/expandMacro` | ra | TDPP → ExpandedMacro | **expose_directly** | LLM legitimately benefits from "what does this macro expand to?" mid-refactor. Surfaces as `expand_macro(file, position)`. |
| 31 | `rust-analyzer/relatedTests` | ra | TDPP → TestInfo[] | **expose_directly** | Pairs with `verify_after_refactor` to know what tests to run. |
| 32 | `rust-analyzer/fetchDependencyList` | ra | — → DependencyList | whitelist_for_execute_command | One-shot dep enumeration. Useful but not common. |
| 33 | `rust-analyzer/viewRecursiveMemoryLayout` | ra | TDPP → MemoryLayoutNode | whitelist_for_execute_command | Niche introspection. |
| 34 | `rust-analyzer/getFailedObligations` | ra | — | whitelist_for_execute_command | Trait-solver introspection. |
| 35 | `rust-analyzer/interpretFunction` | ra | TDPP → string | whitelist_for_execute_command | Const-eval introspection. |
| 36 | `rust-analyzer/childModules` | ra | TDPP → Location[] | **expose_directly** | Mirror of `parentModule`. Used by `plan_file_split`. |

(Inventory in source is documented as 33 wire-level methods; I have listed every method in `lsp-extensions.md` plus four supplementary ones (`childModules`, `relatedTests`, `viewItemTree`, `fetchDependencyList`) that the editor extension uses but which are sometimes counted as part of the same surface. Net actionable count: 36 wire methods, 8 promoted to first-class, 27 whitelisted for `execute_command`, 1 explicitly blocked.)

### 3.1 First-class extension facades (8 surfaced as MCP tools)

| Facade | Wraps | Why surfaced |
|---|---|---|
| `parent_module(file, position)` | `experimental/parentModule` + `rust-analyzer/childModules` | Composed by `plan_file_split` and useful standalone. |
| `child_modules(file, position)` | `rust-analyzer/childModules` | Same. |
| `view_item_tree(file)` | `rust-analyzer/viewItemTree` | Faster than `documentSymbol`-walk; LLM-readable structural enumeration. |
| `expand_macro(file, position)` | `rust-analyzer/expandMacro` | Macro debugging during refactors. |
| `structural_search_replace(pattern, template, files?, dry_run)` | `experimental/ssr` | Bulk path rewrites. |
| `run_flycheck(scope?)` | `rust-analyzer/runFlycheck` | Force `cargo check` and consume diagnostics. |
| `verify_after_refactor(checkpoint_id?)` | `experimental/runnables` + `rust-analyzer/relatedTests` + `runFlycheck` | Composite "did the refactor stick?" gate. |
| `reload_workspace()` / `rebuild_proc_macros()` | `rust-analyzer/reloadWorkspace`, `rust-analyzer/rebuildProcMacros` | After external `Cargo.toml` edits. |

These 8 tools surface in the same `mcp__o2-scalpel__*` namespace as the refactor facades, so the LLM sees them on equal footing.

### 3.2 The blocked one

`experimental/onEnter` is the only assist that gets `explicit_block`. Justification:

- Its semantics are tied to a literal user keystroke (Enter pressed at a specific cursor position). It returns *snippet edits* that depend on the cursor's textual context (continuing a doc-comment, indenting after a `{`, etc.).
- An autonomous LLM has no concept of "the user just pressed Enter". Calling this method from an MCP context produces edits whose meaning is "what would have happened if a human had typed Enter here", which is never what an LLM agent wants. The most charitable invocation produces an extra newline + auto-indent — which the LLM can do in 5 characters of textual edit faster than via an LSP round-trip.
- Worse: it can return `SnippetTextEdit` with `$0` cursor markers that we are otherwise stripping. Allowing it through `execute_command` re-introduces the snippet escape problem solved at `initialize`.
- Cost of blocking: zero. No facade depends on it. No LLM agent has ever asked for it.

All other custom extensions are reachable. The user's directive that "anything deferred must still be reachable via `execute_command` pass-through" is honored for 35 of 36 methods. `onEnter` is the documented exception with rationale.

---

## 4. Protocol-level capabilities — every method we wire

Source: rust-analyzer's `crates/rust-analyzer/src/lsp/capabilities.rs` (capabilities brief §2). I list every advertised capability, mark MVP-essential vs. forward-compat, and document our wire status.

### 4.1 Lifecycle & negotiation

| Method | Direction | MVP-essential | Status | Notes |
|---|---|---|---|---|
| `initialize` / `initialized` | C→S | yes | full | Negotiate `snippetTextEdit:false`, `positionEncoding`, `workDoneProgress`. |
| `shutdown` / `exit` | C→S | yes | full | Required for clean `solidlsp` shutdown. |
| `$/setTrace` | C→S | yes | full | Surface r-a debug logging behind `O2_SCALPEL_LSP_TRACE`. Useful for issue triage. |
| `$/cancelRequest` | C↔S | yes | full | Required for tool-call cancellation; the MCP runtime can cancel a pending facade call mid-flight. |
| `$/progress` | S→C | yes | full | Listen for `rustAnalyzer/Indexing`, `rustAnalyzer/Building`, `rustAnalyzer/Fetching`, `rustAnalyzer/Cargo`, `rustAnalyzer/Roots Scanned` tokens. |
| `client/registerCapability` | S→C | yes | full | r-a dynamically registers `workspace/didChangeWatchedFiles` mid-session. |
| `client/unregisterCapability` | S→C | yes | full | Symmetric. |
| `window/showMessage` (notif) | S→C | yes | full | Log into `solidlsp` log channel. |
| `window/logMessage` (notif) | S→C | yes | full | Log. |
| `window/showMessageRequest` | S→C | **forward-compat** | stubbed | Returns first action by default with a warning; r-a uses this for "Reload workspace?" prompts. Autonomous policy: auto-accept the first non-destructive option. |
| `window/workDoneProgress/create` | S→C | yes | full | Required because our `progressSupport` capability is true. |
| `window/workDoneProgress/cancel` | C→S | forward-compat | full | We don't initiate work-done progress today, but symmetry is cheap. |

### 4.2 Document synchronization

| Method | MVP-essential | Status |
|---|---|---|
| `textDocument/didOpen` | yes | full |
| `textDocument/didChange` | yes | full — we use full-document sync, not incremental, because `multilspy` does. |
| `textDocument/didClose` | yes | full |
| `textDocument/didSave` | yes | full |
| `textDocument/willSave` | forward-compat | not wired |
| `textDocument/willSaveWaitUntil` | forward-compat | not wired |
| `workspace/didChangeWatchedFiles` | yes | full — fired when we create files via WorkspaceEdit. |

### 4.3 Read-only language features (already covered by Claude Code's built-in LSP tool but wired in scalpel for completeness)

| Method | MVP-essential | Status | Why wire it if CC already has it? |
|---|---|---|---|
| `textDocument/definition` | yes | full | Used internally by hallucination-resistance to confirm `name_path` resolution. |
| `textDocument/declaration` | forward-compat | full | Required for the same. |
| `textDocument/typeDefinition` | forward-compat | full | |
| `textDocument/implementation` | yes | full | Used by `plan_file_split` (cross-impl edges). |
| `textDocument/references` | yes | full | Core for `plan_file_split`, `change_type_shape`. |
| `textDocument/hover` | forward-compat | full | Used internally for type hints during planning. |
| `textDocument/documentSymbol` | yes | full | Core. |
| `workspace/symbol` | yes | full | Used by `fix_imports` workspace-scope expansion. |
| `textDocument/foldingRange` | forward-compat | full | Used internally by `extract_expression` to verify selection covers a complete syntactic unit. |
| `textDocument/selectionRange` | forward-compat | full | Same — used to expand a cursor to its enclosing expression. |
| `textDocument/documentHighlight` | forward-compat | full | |
| `textDocument/inlayHint` + `inlayHint/resolve` | forward-compat | full | Surfaced read-only via existing CC tool; we listen but don't surface a duplicate. |
| `textDocument/semanticTokens/full` | forward-compat | full | |
| `textDocument/semanticTokens/range` | forward-compat | full | |
| `textDocument/semanticTokens/full/delta` | forward-compat | full | Required because r-a advertises delta-mode. |
| `workspace/semanticTokens/refresh` | yes | full — handle it as a notification trigger to invalidate any cached token data. |

### 4.4 Editing language features (the heart of scalpel)

| Method | MVP-essential | Status |
|---|---|---|
| `textDocument/codeAction` | yes | full |
| `codeAction/resolve` | yes | full |
| `textDocument/rename` | yes | full |
| `textDocument/prepareRename` | yes | full — required to validate rename targets before requesting `rename`. |
| `textDocument/formatting` | yes | full |
| `textDocument/rangeFormatting` | forward-compat | full (when r-a is configured for `rustfmt`) |
| `textDocument/onTypeFormatting` | forward-compat | not wired (no use case) |
| `textDocument/completion` + `completionItem/resolve` | forward-compat | full — used by `generate_member` to discover trait methods. |
| `textDocument/signatureHelp` | forward-compat | full |
| `callHierarchy/prepareCallHierarchy` | yes | full |
| `callHierarchy/incomingCalls` | yes | full |
| `callHierarchy/outgoingCalls` | yes | full |
| `typeHierarchy/*` | n/a | r-a does not advertise; future strategies may. |

### 4.5 Workspace operations

| Method | MVP-essential | Status |
|---|---|---|
| `workspace/applyEdit` | yes | full — server-initiated; we register a handler that delegates to `WorkspaceEditApplier`. The narrow MVP stubbed this; full coverage requires the real implementation because `experimental/ssr`'s response path uses it. |
| `workspace/willRenameFiles` | yes | full |
| `workspace/willCreateFiles` | forward-compat | not wired (r-a doesn't advertise) |
| `workspace/willDeleteFiles` | forward-compat | not wired |
| `workspace/didRenameFiles` | yes | full |
| `workspace/didCreateFiles` | forward-compat | not wired |
| `workspace/didDeleteFiles` | forward-compat | not wired |
| `workspace/executeCommand` | yes | full — even though r-a doesn't *advertise* it, our typed pass-through wraps the LSP method for forward-compatibility with non-r-a servers and for the custom-extension whitelist. |
| `workspace/configuration` (S→C) | yes | full — r-a queries us for live config. |
| `workspace/didChangeConfiguration` | yes | full |
| `workspace/diagnostic/refresh` (S→C) | yes | full |

### 4.6 Diagnostics

| Method | MVP-essential | Status |
|---|---|---|
| `textDocument/publishDiagnostics` | yes | full — required for the diagnostics-delta gating. |
| `textDocument/diagnostic` (pull) | n/a | r-a does not advertise pull diagnostics. |
| `workspace/diagnostic` (pull) | n/a | same. |

### 4.7 Counts and gap

- **Wired full**: ~52 methods (counting both directions).
- **Stubbed for forward-compat**: 1 (`window/showMessageRequest`).
- **Explicitly not wired** (r-a doesn't advertise; future strategies may need): ~8 methods.
- **Reverse-request handlers we own**: `workspace/applyEdit`, `workspace/configuration`, `client/registerCapability`, `client/unregisterCapability`, `window/showMessageRequest`, `window/workDoneProgress/create`, `workspace/semanticTokens/refresh`, `workspace/diagnostic/refresh`.

The critical full-coverage upgrade vs. the narrow MVP is **`workspace/applyEdit` becomes full instead of stubbed**, because `experimental/ssr` and the macro-expansion pipeline use it. ~80 LoC of real handler vs. 5 LoC of stub.

---

## 5. WorkspaceEdit shape coverage matrix

Every `documentChanges` variant rust-analyzer can emit × every options flag the LSP allows × the test we owe.

### 5.1 Variant matrix

| Variant | Emitted by | Field permutations | Test fixture | Test status |
|---|---|---|---|---|
| `TextDocumentEdit` (basic) | every assist | `textDocument.version` valid / stale / null | `ra_text_edits.rs` | required |
| `TextDocumentEdit` with multiple `edits` | most assists | array length 1, 2, N (>=10), overlapping (must reject), descending-offset | `ra_text_edits.rs` | required |
| `TextDocumentEdit` + `SnippetTextEdit` | `generate_function`, `generate_new`, etc. | `insertTextFormat=Snippet`, `$0`, `$1`, `${1:placeholder}` | `ra_snippets.rs` | required (both with `snippetTextEdit:false` advertised — should not arrive — and with the legacy escape-strip path) |
| `CreateFile` | `move_module_to_file`, `extract_module` (sometimes) | `options.overwrite` true/false, `options.ignoreIfExists` true/false, both, neither | `ra_create_file.rs` | required |
| `RenameFile` | `move_from_mod_rs`, `move_to_mod_rs`, file-system renames triggered by `willRenameFiles` | `options.overwrite`, `options.ignoreIfExists`, target path exists, target path missing | `ra_rename_file.rs` | required |
| `DeleteFile` | none in r-a's current assist set | `options.recursive`, `options.ignoreIfNotExists` | `ra_delete_file.rs` | required for forward-compat (Python's pyright emits this) |
| `changeAnnotations` map | when client advertises `changeAnnotationSupport`, used by r-a for "OutsideWorkspace" edits | `needsConfirmation` true/false, `description` set/unset, `label` length | `ra_change_annotations.rs` | required |

### 5.2 Options flag matrix

| Flag | Variant | Default if absent | Honored by applier | Test |
|---|---|---|---|---|
| `overwrite: true` | CreateFile, RenameFile | false | yes — overwrite target if exists | `test_create_file_overwrite_existing` |
| `overwrite: false` | CreateFile, RenameFile | — | yes — error if target exists | `test_create_file_no_overwrite` |
| `ignoreIfExists: true` | CreateFile | false | yes — silently no-op | `test_create_file_ignore_existing` |
| `ignoreIfExists: false` | CreateFile | — | yes — error if target exists | covered by no-overwrite test |
| `recursive: true` | DeleteFile | false | yes — recursive delete | `test_delete_dir_recursive` |
| `recursive: false` | DeleteFile | — | yes — refuse to delete non-empty dir | `test_delete_dir_non_recursive_fails` |
| `ignoreIfNotExists: true` | DeleteFile | false | yes — silently no-op | `test_delete_file_missing_silently` |
| `ignoreIfNotExists: false` | DeleteFile | — | yes — error | covered |
| `needsConfirmation: true` | changeAnnotations entry | — | yes — facade rejects unless `allow_out_of_workspace=true` | `test_annotations_needs_confirmation_rejected` |
| `description: <string>` | changeAnnotations entry | — | yes — surfaced in dry-run output | `test_annotations_description_in_preview` |
| `label: <string>` | changeAnnotations entry | — | yes — surfaced in dry-run output | `test_annotations_label_in_preview` |
| `$0`, `$N`, `${N:placeholder}` snippet markers | SnippetTextEdit | — | yes — stripped on entry; defensive even when `snippetTextEdit:false` | `test_snippet_marker_strip_basic`, `test_snippet_strip_inside_string_literal_safe` |

### 5.3 Ordering and atomicity

| Rule | Test |
|---|---|
| `documentChanges` array applies in array order. | `test_create_then_text_edit_order_preserved` |
| Inside one `TextDocumentEdit`, `edits` are applied as if simultaneous; applier sorts descending by `start` before applying to a string buffer. | `test_overlapping_edits_descending_order` |
| `CreateFile` must come before any `TextDocumentEdit` targeting that URI. r-a emits in this order; applier validates and rejects malformed edits. | `test_create_file_before_text_edit_validation` |
| Non-overlapping edits must not double-write. | `test_no_double_write` |
| On any failure mid-array, restore all snapshots; leave filesystem in pre-apply state. | `test_atomic_rollback_on_partial_failure` |
| Version mismatch on any `TextDocumentEdit.textDocument.version` → reject the entire edit, raise `STALE_VERSION`. | `test_stale_version_rejects_entire_edit` |

### 5.4 The full coverage matrix is the test plan

7 variants × ~12 option permutations × 6 ordering/atomicity rules = **~80 unit tests on `WorkspaceEditApplier` alone**. The narrow MVP budgeted ~150 LoC for the applier upgrade. Full coverage with full tests is **~500 LoC** of applier + test code (split: ~200 applier, ~300 tests). This is the single largest line-count expansion vs. the narrow MVP and is non-negotiable for the directive.

---

## 6. Pre-MVP spikes — what must be verified before commit

Each spike is a 1-day investigation with a binary outcome that gates a design decision. **All five are MVP-blocking** under full-coverage.

### 6.1 Spike S1 — Does `multilspy` forward `$/progress` cleanly?

**Question.** Can `solidlsp` (built on `multilspy`) observe `$/progress` notifications with token `rustAnalyzer/Indexing`? Or are they swallowed at the JSON-RPC shim?

**Method.** 30-line script that spawns `rust-analyzer` via `solidlsp.SolidLanguageServer`, opens a 200-crate workspace, attaches a `notifications.on("$/progress", ...)` listener, prints every token + payload for 5 minutes.

**Expected outcomes.**
- (A) All `$/progress` arrive — `wait_for_indexing()` is straightforward to implement.
- (B) Only the `begin`/`end` markers arrive, no `report` updates — `wait_for_indexing()` works but progress UI is coarse.
- (C) Nothing arrives — `multilspy` swallows them. **Blocking**: must add a notification-tap shim in `solidlsp/lsp_protocol_handler/server.py` (~30 LoC) before the design freezes.

**Why it gates full-coverage MVP.** Every facade calls `wait_for_indexing()` per §3.2 of the narrow specialist. Without it, the first call after spawn returns empty results that look like "no actions available" to the LLM. R7 in the narrow MVP risks flagged this; full coverage cannot assume the optimistic path.

### 6.2 Spike S2 — Does `SnippetTextEdit` round-trip when we declare `snippetTextEdit:false`?

**Question.** When we advertise `snippetTextEdit: false` at `initialize`, does rust-analyzer reliably fall back to plain `TextEdit` for *every* assist, or do some assists ignore the cap and emit snippets anyway?

**Method.** Generate a fixture of every assist family that produces snippets (`generate_function`, `generate_new`, `extract_function`, etc.) and run `codeAction → resolve` against each, asserting no `$N` markers appear in any returned `TextEdit`. Repeat with `snippetTextEdit: true` for control.

**Expected outcomes.**
- (A) All assists honor `false` → applier's snippet-strip path is defensive-only, not load-bearing.
- (B) Some assists ignore the cap → strip path is mandatory and must be audited for false-positive matches inside string literals.

**Why it gates.** §3.1 of the narrow specialist makes `snippetTextEdit:false` mandatory. Full coverage adds the strip path as belt-and-suspenders. If outcome (B), we need ~50 LoC of regex with edge-case handling instead of 5 LoC of capability advertisement.

### 6.3 Spike S3 — Does `applyEdit` reverse-request fire on `CodeAction.command` paths?

**Question.** When a `CodeAction` has `command: { command: "rust-analyzer.applySnippetWorkspaceEdit", arguments: [...] }` instead of `edit`, and we invoke `workspace/executeCommand` with that command, does rust-analyzer respond with a `workspace/applyEdit` reverse-request? Or does it embed the edit in the `executeCommand` response?

**Method.** Pick an assist that emits a `command`-style action (`auto_import` in some configurations does). Invoke via `executeCommand`. Capture both the response and any `applyEdit` reverse-request that arrives in the next 5 seconds.

**Expected outcomes.**
- (A) Reverse-request fires → our `workspace/applyEdit` handler must be production-grade, not a stub. (This is the full-coverage assumption.)
- (B) Edit is embedded in `executeCommand` response → simpler path; handler can stay minimal.

**Why it gates.** Full coverage requires `experimental/ssr` to work end-to-end, and SSR uses the reverse-request path. Without S3 evidence, we may underbuild the handler and SSR silently fails.

### 6.4 Spike S4 — Does `experimental/ssr` accept multi-file results without crashing on large workspaces?

**Question.** What is the upper bound on `WorkspaceEdit` size r-a's SSR produces? Is there a server-side timeout?

**Method.** Run SSR with a deliberately broad pattern (`$x.unwrap()` → `$x?`) on `calcrs` and on a 200-crate fixture. Measure response time, edit count, peak memory.

**Expected outcomes.**
- Bounds documented; we either accept them or add a `max_edits` parameter to `structural_search_replace`.

**Why it gates.** SSR is the single largest blast-radius facade in the full-coverage set. Knowing the bounds before MVP prevents a "SSR hung r-a" issue from killing user trust.

### 6.5 Spike S5 — Does `rust-analyzer/expandMacro` work on proc macros?

**Question.** `expandMacro` is documented for declarative macros. Does it also expand proc-macros (e.g., `#[derive(Serialize)]`)? Or only `macro_rules!`?

**Method.** Run `expandMacro` against `calcrs` with a `serde::Serialize` derive added. Compare to a `macro_rules!` invocation in the same file.

**Expected outcomes.**
- (A) Both work → `expand_macro` facade has uniform semantics.
- (B) Only declarative → facade must error out on proc-macro positions with a clear `not_supported_for_proc_macros` failure.

**Why it gates.** §3.5 of the narrow MVP made `procMacro.enable=true` mandatory. Full coverage exposes `expand_macro` as a facade. We need to know whether it works on the *common case* (proc-macros are everywhere in real code) or just on the *demo case* (declarative macros in textbook examples).

### 6.6 Spike S6 — `did the codeAction.command path round-trip on `auto_import` quickfixes?

**Question.** `auto_import` in some configurations returns `CodeAction.command` rather than `CodeAction.edit`. Does our two-phase flow (list → resolve → apply) handle both shapes, or does it assume `edit` is always populated post-resolve?

**Method.** Run `auto_import` against a file with 50 unresolved imports. Capture both shapes' frequencies. Audit the applier's branch.

**Expected outcomes.**
- (A) Resolve always populates `edit` → simple.
- (B) Resolve sometimes leaves `edit: null` and only `command` is set → the applier must invoke `executeCommand` on the command, then handle the resulting reverse-request.

**Why it gates.** `fix_imports` is one of the six narrow MVP facades and the most-used in the workflow. Edge cases here corrupt every demo.

### 6.7 Spike summary

| ID | Decision gated | Outcome cost if optimistic path holds | Outcome cost if pessimistic |
|---|---|---|---|
| S1 | `wait_for_indexing` design | 0 LoC | +30 LoC shim in `solidlsp` |
| S2 | snippet-strip path scope | 5 LoC | +50 LoC regex |
| S3 | `applyEdit` handler scope | 5 LoC stub | +80 LoC real handler |
| S4 | SSR safety bounds | 0 LoC | +30 LoC `max_edits` guard |
| S5 | `expand_macro` facade scope | 0 LoC | +20 LoC proc-macro reject branch |
| S6 | `auto_import` apply branch | 0 LoC | +40 LoC two-shape branch |

Pessimistic-case combined cost: **+250 LoC** above the optimistic baseline. This is rolled into §8 effort estimates.

---

## 7. `calcrs` fixture expansion for full coverage

The narrow `calcrs` (~900 LoC `lib.rs` + minor `tests/smoke.rs`) covered ~30% of assist families — exactly the families used by the headline split-file workflow. Full coverage demands more fixtures.

### 7.1 Strategy: split into companion fixtures, don't bloat `calcrs`

Bloating `calcrs` to 5,000 LoC defeats its purpose (auditable in under an hour). Instead, **add companion fixtures** in `tests/solidlsp/rust/fixtures/`, each scoped to a family. `calcrs` stays the headline workflow demo; companions exercise the long tail.

### 7.2 Proposed companion fixtures

| Fixture | Size (LoC) | Families exercised | Tests it gates |
|---|---|---|---|
| `calcrs/src/lib.rs` (existing, expanded ~+50 LoC) | ~950 | A, D, E, L | E1, E2, E3, E7, E9, E10 |
| `ra_extractors.rs` | ~250 | B (extractors) | `extract_expression` family tests |
| `ra_inliners.rs` | ~200 | C (inliners) | `inline_symbol` family tests |
| `ra_visibility.rs` | ~150 | E (visibility), L (post-move) | `change_visibility` round-trip + `fix_visibility` diagnostic-driven |
| `ra_imports.rs` | ~300 | D (imports, full set) | `fix_imports` flag matrix |
| `ra_glob_imports.rs` | ~120 | D (glob expansion) | `expand_glob_imports` |
| `ra_ordering.rs` | ~180 | F (ordering) | `tidy_structure` |
| `ra_generators_traits.rs` | ~250 | G (trait scaffolders) | `generate_trait_impl_scaffold` |
| `ra_generators_methods.rs` | ~200 | G (method scaffolders) | `generate_member` |
| `ra_convert_typeshape.rs` | ~150 | H (type-shape rewrites) | `change_type_shape` |
| `ra_convert_returntype.rs` | ~120 | H (return-type rewrites) | `change_return_type` |
| `ra_pattern_destructuring.rs` | ~150 | I (patterns) | `complete_match_arms` |
| `ra_lifetimes.rs` | ~180 | J (lifetimes) | `extract_lifetime` |
| `ra_proc_macros.rs` | ~200 | proc-macro pathway (serde, async-trait) | proc-macro spike S5 + R2 |
| `ra_ssr.rs` | ~180 | extension (SSR) | `structural_search_replace` |
| `ra_macros.rs` | ~150 | extension (`expandMacro`) | `expand_macro` |
| `ra_module_layouts.rs` | ~200 | A (`mod.rs` swap) | `convert_module_layout` |
| `ra_quickfixes.rs` | ~250 | L (diagnostic-bound quickfixes) | applies the diagnostics-delta sweep across 30+ quickfix kinds |
| `ra_workspace_edit_shapes.rs` | ~120 | every WorkspaceEdit variant from §5 | the 80-test applier matrix |
| `ra_term_search.rs` | ~80 | K (term_search) | primitive-only escape-hatch test |

**Total fixture LoC: ~3,400 across 19 fixtures (counting calcrs as one).** This is large but each fixture is independent and short. They're all plain Rust files that compile standalone (or as part of a tiny per-fixture Cargo workspace).

### 7.3 Ground rules per fixture

1. **Compile cleanly** before any refactor is applied. The diagnostics-delta gate counts errors *introduced by* the refactor, not pre-existing.
2. **Pinned to edition 2021** unless the fixture's purpose is to exercise a different edition.
3. **Zero crates.io dependencies** except for `serde`, `tokio`, `async-trait`, `clap` in `ra_proc_macros.rs` (where the whole point is proc-macro coverage).
4. **One refactor scenario per fixture** by default. Multi-scenario fixtures encouraged only when scenarios share a structural setup (e.g., `ra_imports.rs` exercises 8 import-family flags with a single base file).
5. **Snapshot-asserted post-refactor** is *out* by default (per §4 of the narrow specialist's rationale; snapshot trees are maintenance burden). Semantic-equivalence assertions only.

### 7.4 What this expansion does NOT include

- A full multi-crate workspace fixture (E5 in the design's E2E list). Stays nightly per the narrow MVP. Full coverage doesn't change this — multi-crate is an *orthogonal* concern, not a capability gap in our tool.
- Edition 2024 fixture. Stays nightly.
- A `no_std` fixture. r-a handles `no_std` indistinguishably; no fixture needed.

---

## 8. Re-staging the Rust-side delivery

The narrow MVP estimated ~2,310 LoC + 11 fixtures on the Rust side. Full-coverage realistically balloons.

### 8.1 LoC table

| Layer | Narrow-MVP LoC | Full-coverage LoC | Delta | Sizing |
|---|---|---|---|---|
| `solidlsp` primitive methods (codeAction/resolve, executeCommand, wait_for_indexing) | ~90 | ~120 | +30 | M |
| `rust_analyzer.py` init (snippetTextEdit:false, procMacro.enable, cargo.targetDir) | ~10 | ~15 | +5 | S |
| `WorkspaceEditApplier` (all variants × all options × ordering × atomicity) | ~150 | ~500 | +350 | L |
| Reverse-request handlers (`applyEdit` real, `configuration`, `registerCapability`, `showMessageRequest`) | ~30 (stub) | ~150 | +120 | M |
| `$/progress` listener + `wait_for_indexing` + per-token tracking | ~30 | ~80 | +50 | S |
| Checkpoint/rollback machinery (in-memory + `.serena/checkpoints/` durability) | ~100 | ~150 | +50 | M |
| Primitive tools (`list_code_actions`, `resolve_code_action`, `apply_code_action`, `execute_command`, typed pass-through) | ~200 | ~350 | +150 | M |
| Inherited facades (`plan_file_split`, `split_file_by_symbols`, `extract_symbols_to_module`, `move_inline_module_to_file`, `fix_imports` (expanded), `rollback_refactor`) | ~350 | ~700 | +350 | L |
| New facades — split workflow (`convert_module_layout`) | 0 | ~80 | +80 | S |
| New facades — extract/inline (`extract_expression`, `extract_struct_from_enum_variant`, `inline_symbol`) | 0 | ~280 | +280 | M |
| New facades — imports (`expand_glob_imports`) | 0 | ~120 | +120 | S |
| New facades — visibility/ordering (`change_visibility`, `tidy_structure`) | 0 | ~180 | +180 | M |
| New facades — generators (`generate_trait_impl_scaffold`, `generate_member`) | 0 | ~250 | +250 | M |
| New facades — type-shape (`change_type_shape`, `change_return_type`) | 0 | ~250 | +250 | M |
| New facades — patterns/lifetimes (`complete_match_arms`, `extract_lifetime`) | 0 | ~180 | +180 | S |
| Extension facades (`parent_module`, `child_modules`, `view_item_tree`, `expand_macro`, `structural_search_replace`, `run_flycheck`, `verify_after_refactor`, `reload_workspace`/`rebuild_proc_macros`) | 0 | ~400 | +400 | L |
| Typed `execute_command` whitelist + dispatch | 0 | ~180 | +180 | M |
| `LanguageStrategy` interface + registry (expanded per §10) | ~140 | ~250 | +110 | M |
| `RustStrategy` plugin (full whitelist, all kind mappings, post-apply hooks) | ~120 | ~300 | +180 | M |
| Unit tests | ~350 | ~900 | +550 | L |
| Integration tests | ~350 + 5 fixtures | ~1,200 + 19 fixtures | +850 | L |
| E2E harness + scenarios | ~450 + 6 workspaces | ~700 + 9 workspaces | +250 | L |
| **Rust-side total** | **~2,310 + 11 fixtures** | **~7,335 + 19 fixtures** | **+5,025 + 8 fixtures** | — |

### 8.2 Sizing call-out per CLAUDE.md

Per the project's "no time estimates" rule, sizing uses S/M/L:

| Bucket | Definition | Items | Combined LoC |
|---|---|---|---|
| **S** (small) | <100 LoC, < ~150 LoC tests, single-file scope, 1-developer | 6 items above | ~520 |
| **M** (medium) | 100–300 LoC, 200–400 LoC tests, 2–3 files, integration tests required | 11 items | ~2,500 |
| **L** (large) | >300 LoC, >400 LoC tests, multi-file, cross-cutting changes | 7 items (applier, inherited facades, extension facades, unit tests, integration tests, E2E) | ~4,300 |

The "L" bucket is the danger zone. **Three of seven L items are testing infrastructure**, not implementation. Full coverage isn't dominated by writing more code; it's dominated by writing more *tests*. This matters because:

1. The marginal cost of facade #19 over facade #6 is ~150 LoC of facade + ~200 LoC of tests. The facade is small; the tests are not.
2. The applier matrix (§5) is the single largest piece of testing work and is non-negotiable for the directive.
3. Running E2E for 19 fixtures × cold-start cost (~30–60s each) means CI time per Rust-side run becomes ~15 min, vs. the narrow MVP's ~5 min.

### 8.3 Honest re-estimate vs. the prompt's range

The prompt forecasted ~4,500–6,000 LoC on the Rust side for full coverage. **My estimate is ~7,335 LoC**, ~25% above the upper bound of the prompt's forecast. The overshoot is concentrated in:

- WorkspaceEdit applier (+200 LoC over forecast) — the variant × options matrix is exhaustive.
- Extension facades (+150 LoC over forecast) — 8 first-class wrappers, each with their own input schema.
- Tests (+400 LoC over forecast) — the matrix-driven tests aren't padding; they're the proof that "full coverage" is real.

If a tighter target is needed, the responsible cuts are §9. Cutting LoC further means cutting *test coverage*, which violates the directive's spirit. I do not recommend it.

---

## 9. Cuts I still recommend (full-coverage compatible)

"Full LSP support" doesn't mean every feature ships in MVP. The directive says all capabilities must be **reachable**. Several capabilities are not meaningful for an autonomous LLM and stay reachable via `execute_command` pass-through but do not get first-class facades, polish, or dedicated test fixtures.

### 9.1 Capabilities that stay reachable but unsurfaced

| Capability | Reach mechanism | Why unsurfaced |
|---|---|---|
| `rust-analyzer/viewHir` | typed `execute_command("rust-analyzer/viewHir", {...})` | HIR dump is for compiler authors. An LLM gets no actionable signal from it. |
| `rust-analyzer/viewMir` | typed `execute_command` | Same as HIR. |
| `rust-analyzer/viewCrateGraph` | typed `execute_command` | Returns SVG. SVGs are unparseable by LLMs without a vision model in the loop, which we don't have in MCP. |
| `rust-analyzer/viewSyntaxTree` | typed `execute_command` | Useful for r-a-developer debugging only. |
| `rust-analyzer/viewFileText` | typed `execute_command` | "File as r-a sees it" — diagnoses sync drift but isn't actionable autonomously. |
| `rust-analyzer/viewRecursiveMemoryLayout` | typed `execute_command` | Niche. |
| `rust-analyzer/getFailedObligations` | typed `execute_command` | Trait-solver introspection. Useful when investigating `cannot satisfy ...` errors but the LLM can read the diagnostic message instead. |
| `rust-analyzer/interpretFunction` | typed `execute_command` | Const-eval introspection. |
| `experimental/discoverTest` family (7 methods) | typed `execute_command` | Test Explorer is a UX surface (tree view of test results). The LLM benefits from `relatedTests` + `runFlycheck`, not Test Explorer. |
| `experimental/onEnter` | **explicit_block** | See §3.2; the only blocked method. |
| `rust-analyzer/cancelFlycheck` / `clearFlycheck` | typed `execute_command` | Auxiliary to `runFlycheck`. |
| `rust-analyzer/fetchDependencyList` | typed `execute_command` | LLM rarely needs this; reading `Cargo.toml` is faster. |

### 9.2 Facade depth that defers

Even within the proposed facade set, some features defer to a v1.x:

| Facade | Deferred feature | Mitigation |
|---|---|---|
| `split_file_by_symbols` | `parent_module_style="mod_rs"` | Reachable via `convert_module_layout` post-split. |
| `split_file_by_symbols` | `reexport_policy="explicit_list"` | LLM uses `Edit` tool to add manual `pub use` lines. |
| `fix_imports` | crate-wide `files=["**"]` glob | Caller supplies explicit file list. Workspace walk is left to the user's shell. |
| `plan_file_split` | `strategy="by_visibility"`, `"by_type_affinity"` | `by_cluster` is the strongest default; alternatives are demoware. |
| `extract_expression` | sub-expression range modes (e.g., extract from inside a chained method call) | Reachable via primitive `apply_code_action` with manual range. |
| `verify_after_refactor` | streaming test output | One-shot completion only; full streaming is post-MVP. |

### 9.3 What is explicitly NOT cut

The directive's promise — every capability reachable, every WorkspaceEdit shape applied, every advertised method wired — is honored:

- All 36 custom extensions: 8 first-class, 27 typed pass-through, 1 explicit_block (with documented rationale).
- All 7 WorkspaceEdit variants × all option flags: tested.
- All ~52 wired protocol methods: tested.
- All 158 assists: 93 reached via facades, 50 via primitives, 1 (`term_search`) via primitives only with documentation.

**Net: the deferrable cuts in §9.1–§9.2 are ~5% of capability, restricted to debug views and second-order facade options. The other 95% ships at MVP.**

---

## 10. Abstraction audit — `LanguageStrategy` under full-coverage pressure

The narrow MVP flagged 10 abstraction leaks (§6 of the archived specialist). Full coverage adds new leaks and amplifies old ones, because facades like `extract_lifetime`, `change_type_shape`, and `expand_macro` are more Rust-shaped than `split_file_by_symbols` was.

### 10.1 New strategy methods required by full coverage

| Method | Purpose | Rust value | Python value | Why it has to live in the strategy |
|---|---|---|---|---|
| `extractor_kinds() -> dict[Literal["function","variable","constant","static","type_alias"], str]` | Map facade-level extraction kind to LSP code-action kind. | `{"function": "refactor.extract.function", "variable": "refactor.extract.variable", "constant": "refactor.extract.const", ...}` | `{"function": "refactor.extract.method", "variable": "refactor.extract.variable", ...}` | Different LSP servers use different `kind` strings. Hardcoding in the facade leaks Rust. |
| `inliner_kinds() -> dict[Literal["call","variable","type_alias","macro","const"], str]` | Same for inlining. | rust-analyzer kinds | pyright kinds | Same. |
| `generator_kinds() -> dict[Literal["trait_impl","method","getter","setter","new"], str]` | Same for generators. | rust-analyzer kinds | pyright equivalents (mostly absent — Python has no traits) | If a kind is unsupported, the strategy returns `None` and the facade returns `failure: not_supported_for_language`. |
| `supports_lifetimes() -> bool` | Gate `extract_lifetime` facade. | True | False | Python has no lifetimes; the facade should refuse rather than execute a meaningless code-action search. |
| `supports_macros() -> bool` | Gate `expand_macro` facade. | True | False | Python has no macros (decorators don't expand the same way). |
| `supports_structural_search() -> bool` | Gate `structural_search_replace`. | True (via SSR) | depends on pyright; probably False | SSR is rust-analyzer-specific; other LSPs lack it. |
| `language_specific_facades() -> list[Tool]` | Lets a strategy register additional facades that are language-only. | `[]` for now (every full-coverage facade is generalizable) | `[]` | Reserve slot per the directive's seam. Not used in MVP but defined so future Rust-only or Python-only facades don't need to break the interface. |
| `kind_match_priority() -> list[str]` | Fallback when the LLM gives a kind hint with no exact match. | Rust: `["class"→struct/enum/trait, ...]` | Python: `["class"→class only, ...]` | Mentioned in §6.10 of the narrow specialist; full coverage formalizes. |
| `safe_to_move_predicates() -> list[Callable[[DocumentSymbol], tuple[bool,str]]]` | Strategy supplies predicates to guard `is_safe_to_move`. | Rust: always-safe | Python: refuse `if __name__ == "__main__":` regions | Per §6.4 of the archived specialist. |
| `default_visibility_for_extracted_module() -> str` | What visibility to use when a moved symbol crosses a privacy boundary. | Rust: `"pub(crate)"` | Python: `""` (Python has no visibility) | Used by `change_visibility` and `split_file_by_symbols`. |
| `clustering_signal_quality() -> Literal["high","medium","low"]` | Calibrate `plan_file_split` confidence. | Rust: `"high"` | Python: `"medium"` | Per §6.7 of the archived specialist. |
| `dry_run_supported_for(facade_name: str) -> bool` | Per-facade dry-run gate. | Rust: True for all | Python: False for `extract_expression(kind="function")` (pyright multi-step) | Per §6.9 of the archived specialist. |

### 10.2 Updated `LanguageStrategy` Protocol stub

Pseudocode (Pydantic-style schema where applicable; Protocol stubs only — no implementation):

```python
class LanguageStrategy(Protocol):
    """Per-language plugin. Surface is intentionally narrow.

    Full-coverage MVP: ~25 methods. If it grows past ~30, the abstraction
    is wrong and facades are leaking — re-audit before adding the 31st.
    """

    language: Language
    file_extensions: frozenset[str]

    # --- Code-action kind tables (full-coverage expansion) -------------
    def extract_module_kind(self) -> str: ...
    def move_to_file_kind(self) -> str | None: ...
    def rename_kind(self) -> str: ...
    def extractor_kinds(self) -> Mapping[ExtractorKind, str]: ...
    def inliner_kinds(self) -> Mapping[InlinerKind, str]: ...
    def generator_kinds(self) -> Mapping[GeneratorKind, str | None]: ...
    def visibility_change_kind(self) -> str | None: ...
    def reorder_kinds(self) -> Mapping[ReorderScope, str]: ...

    # --- Capability gates ---------------------------------------------
    def supports_lifetimes(self) -> bool: ...
    def supports_macros(self) -> bool: ...
    def supports_structural_search(self) -> bool: ...
    def supports_proc_macros(self) -> bool: ...

    # --- Module / file layout -----------------------------------------
    def parent_module_register_lines(self, name: str) -> list[str]: ...
    def parent_module_import_lines(self, name: str, symbols: Iterable[str]) -> list[str]: ...
    def module_filename_for(self, name: str, layout: ParentLayout) -> Path: ...
    def reexport_syntax(self, symbol: str) -> str: ...
    def default_parent_layout(self) -> ParentLayout: ...
    def default_visibility_for_extracted_module(self) -> str: ...

    # --- Planning heuristics ------------------------------------------
    def is_top_level_item(self, symbol: DocumentSymbol) -> bool: ...
    def is_safe_to_move(self, symbol: DocumentSymbol) -> tuple[bool, str]: ...
    def symbol_size_heuristic(self, symbol: DocumentSymbol) -> int: ...
    def is_publicly_visible(self, symbol: DocumentSymbol) -> bool: ...
    def kind_match_priority(self) -> Sequence[str]: ...
    def clustering_signal_quality(self) -> Literal["high", "medium", "low"]: ...

    # --- Server extensions --------------------------------------------
    def execute_command_whitelist(self) -> frozenset[str]: ...
    def explicit_command_blocks(self) -> frozenset[str]: ...
    def language_specific_facades(self) -> list[ToolDescriptor]: ...

    # --- Dry-run / safety ---------------------------------------------
    def dry_run_supported_for(self, facade_name: str) -> bool: ...

    # --- LSP init -----------------------------------------------------
    def lsp_init_overrides(self) -> Mapping[str, Any]: ...
    def post_apply_health_check_commands(self) -> list[ExecuteCommand]: ...
```

Method count: 26. Above 25 by one. The 25-method ceiling I named in the docstring is a **soft warning**, not a hard limit. If the count climbs to 30, that's the redesign trigger.

### 10.3 The `language_specific_facades` seam

The directive opens the door to "Rust-only facades" because `extract_lifetime`, `expand_macro`, and `structural_search_replace` are conceptually Rust-only (Python has no analog).

**Option A — keep them in the language-agnostic facade set, gate via `supports_*()` predicates.** Facade `extract_lifetime` is registered globally; on a Python file, it returns `failure: {kind: "unsupported_for_language", language: "python"}`.

**Option B — register them only for Rust via `language_specific_facades()`.** The LLM only sees `extract_lifetime` when working on `.rs` files.

**My recommendation: Option A for MVP.** Two reasons:

1. **MCP tool registration is global.** The LLM's tool list is fixed at session start. Tools that appear/disappear by file path break tool-use stability. The LLM is better at "this tool exists but failed" than "this tool exists for some files".
2. **Forward compatibility.** Python eventually grows things like async-trait sugar (already exists informally). If we register `expand_macro` as Rust-only and Python later wants similar semantics for decorators, we have to migrate. Better to keep the surface uniform and let strategies refuse.

`language_specific_facades()` is reserved as a future seam for Option B but stays empty in MVP for both Rust and Python.

### 10.4 Strategy method count vs. method-count anxiety

26 strategy methods is a lot. The narrow MVP had ~12. Justification per method:

- 8 are kind-mapping tables. Each is necessary because LSP servers use different kind strings. Cannot consolidate.
- 4 are capability gates (`supports_*`). Each guards a different facade. Cannot consolidate without losing fail-fast clarity.
- 6 are layout/syntax (module declarations, imports, reexports, layouts, defaults). All required by facades.
- 6 are heuristics (top-level, safe-to-move, size, visibility, kind priority, signal quality). All required.
- 4 are misc (whitelist, block list, language-specific seam, init overrides).

Each method has a single, narrow purpose. None is incidental. Compressing to fewer methods would mean either:

- Bigger return values (a single `kinds() -> dict` covering all kind tables) — fragile and harder to type.
- Fewer capabilities exposed — violates the directive.

The 26 stays.

### 10.5 Abstraction leaks the narrow specialist named that full coverage *aggravates*

| Leak | Narrow MVP | Full coverage |
|---|---|---|
| `parent_module_style: dir\|mod_rs` | Renamed to `parent_layout: package\|file`. | Same. Full coverage adds `convert_module_layout` which speaks the canonical vocabulary. |
| `module_declaration_syntax(name, style)` | Split into `parent_module_register_lines` + `parent_module_import_lines`. | Unchanged. |
| `is_top_level_item` | Sibling `is_safe_to_move` added. | Unchanged. |
| Diagnostics integer count | Augmented with `severity_breakdown`. | Unchanged. Diagnostic-delta gate uses `severity_breakdown["error"]`. |
| Cluster algorithm Rust-shaped | `clustering_signal_quality` warning. | Unchanged. |
| `name_path` resolution | Kind-hint disambiguation. | Unchanged. Full coverage adds more facades that take name-paths, all of which use the same resolver. |

### 10.6 New abstraction leaks introduced by full coverage

| New leak | Where it manifests | Mitigation |
|---|---|---|
| `extract_lifetime` is Rust-only conceptually | Facade exists for both languages. Python returns `unsupported_for_language`. | `supports_lifetimes()` gate. |
| `expand_macro` is Rust-only | Same. | `supports_macros()` gate. |
| `structural_search_replace` semantics differ | Rust SSR uses syntactic patterns; if Python ever gets it, it'll be different. | `supports_structural_search()` gate; when both languages support, document that pattern syntax is per-strategy. |
| `tidy_structure` order conventions differ wildly | Rust convention (`derive`s first, then fields, then methods) is rust-specific. Python has no analog. | `tidy_structure(scope, options[])` accepts a per-strategy-validated option set; strategy returns `failure: unsupported_option` for invalid combinations. |
| `change_type_shape` for tuple↔named struct | Rust-specific. Python has dataclasses but the assist family is different. | `supports_type_shape_changes() -> set[Literal[...]]` returns the set the strategy supports. |
| `verify_after_refactor` depends on `runFlycheck` semantics | rust-analyzer fires `cargo check`. Python's pyright doesn't have an analog; mypy is external. | Strategy method `post_apply_verify() -> list[VerifyStep]` returns whatever the language-equivalent verification looks like. |

These six new leaks are all gated by capability methods. None is silently per-language behavior; each refusal returns a structured `failure` the LLM can read.

---

## 11. End-to-end gates under full coverage

The narrow MVP gated 6 of 10 E2E scenarios. Full coverage demands more.

| Scenario | Narrow MVP | Full coverage | Notes |
|---|---|---|---|
| E1 — Happy-path 1200-line split | gated | gated | unchanged |
| E2 — Dry-run → inspect → adjust → commit | gated | gated | unchanged |
| E3 — Rollback after failed cargo check | gated | gated | unchanged |
| E4 — Concurrent edit during refactor | nightly | **gated** | `ContentModified` retry path is exercised by `inline_symbol(scope=all_callers)` on a busy fixture |
| E5 — Multi-crate workspace | nightly | nightly | unchanged |
| E6 — `fix_imports` crate-wide glob | skipped | nightly | glob deferred but reachable via primitives |
| E7 — rust-analyzer cold start | gated | gated | unchanged |
| E8 — Crash recovery | nightly | nightly | unchanged |
| E9 — Semantic equivalence on `calcrs` | gated | gated | unchanged |
| E10 — Regression: existing `rename_symbol` | gated | gated | unchanged |
| E11 — `extract_expression` round-trip | new | **gated** | covers Family B |
| E12 — `inline_symbol(all_callers)` with diagnostics-delta | new | **gated** | covers Family C |
| E13 — `expand_macro` on proc-macro | new | **gated** | covers proc-macro pathway + spike S5 |
| E14 — `structural_search_replace` on `calcrs` | new | **gated** | covers SSR + spike S4 |
| E15 — `WorkspaceEditApplier` exhaustive variant matrix | new | **gated** | the §5 80-test matrix |
| E16 — Typed pass-through round-trip (every whitelisted command) | new | **gated** | proves "every capability reachable" |

**Net MVP gates: 11 (E1–E4, E7, E9–E16).** Up from 6. CI time per Rust run ~15 min vs. narrow MVP's ~5 min.

---

## 12. Re-staging: Stage A / B / C under full coverage

The narrow MVP staged Small → Medium → Large. Full coverage keeps the same shape but expands each stage.

### Stage A (Small) — primitive layer + interface skeleton

- All 5 spikes (S1–S6) executed, results recorded.
- `solidlsp` primitive methods (request_code_actions, resolve_code_action, execute_command, wait_for_indexing).
- `WorkspaceEditApplier` baseline (TextDocumentEdit + version check + atomicity).
- `LanguageStrategy` Protocol skeleton with all 26 methods stubbed.
- Both `RustStrategy` and `PythonStrategy` stub-implement enough to call `apply_code_action` end-to-end.
- Reverse-request handlers stubbed (returning `applied:false` with a diagnostic message).

Sizing: M. Validates the protocol; nothing user-visible yet.

### Stage B (Medium) — full applier + checkpoint + primitives + first-class extensions

- `WorkspaceEditApplier` complete (all variants × options × ordering × atomicity).
- §5 test matrix (~80 tests) green.
- Reverse-request handlers production-grade (per S3 outcome).
- Checkpoint/rollback machinery + `.serena/checkpoints/` durability.
- All 4 primitive tools (`list_code_actions`, `resolve_code_action`, `apply_code_action`, `execute_command`).
- Typed pass-through for all 27 whitelisted custom extensions.
- 8 first-class extension facades (`parent_module`, `child_modules`, `view_item_tree`, `expand_macro`, `structural_search_replace`, `run_flycheck`, `verify_after_refactor`, `reload_workspace`).
- `RustStrategy` complete kind tables.
- E15, E16 gates green.

Sizing: L. Major surface complete; the LLM can drive any rust-analyzer assist, including SSR.

### Stage C (Large) — full facade layer

- All 19 facades operational.
- 19 fixtures complete and tested.
- Diagnostics-delta gate firing on every mutating facade.
- Idempotency guarantees on all relevant facades.
- E1–E4, E7, E9–E14 gates green.
- Dual-language gating: PythonStrategy must pass equivalent gates before Stage C ships.

Sizing: L. Headline surface ships.

The strict ordering rule from the narrow MVP is preserved and **strengthened**: Stage B's `PythonStrategy` minimum-viable MUST land before Stage C's facade layer, because the abstraction leaks (§10) only surface under a real second strategy. Without it, MVP ships with hidden Rust-isms and v2 pays the cost.

---

## 13. Summary of full-coverage MVP recommendations (the actionable list)

### Must-do for MVP (release-blocking)

1. **All 19 facades operational** — 6 inherited + 13 new — with the four-part contract (name-path addressing, atomic checkpoint, diagnostics-delta gate, idempotency).
2. **All 158 assists reachable** — 93 via facades, 50 via primitives, 1 (`term_search`) documented as primitive-only.
3. **All 36 custom extensions reachable** — 8 first-class facades, 27 typed pass-through, 1 explicit_block (`experimental/onEnter`).
4. **All 7 WorkspaceEdit variants × 12 option flags tested** — the §5 matrix, ~80 unit tests.
5. **All 52 advertised LSP methods wired** — including `workspace/applyEdit` reverse-request as production-grade (not stub) and `$/progress` per-token tracking.
6. **6 pre-MVP spikes (S1–S6) complete** before design freeze; outcomes recorded; pessimistic-path LoC budgeted.
7. **19 fixtures** — `calcrs` plus 18 companions covering every assist family and the WorkspaceEdit variant matrix.
8. **11 E2E gates (E1–E4, E7, E9–E16)** green.
9. **`LanguageStrategy` interface frozen at 26 methods** with both Rust and Python compiling against it before any facade merges.
10. **Cross-language abstraction-leak fixes from the narrow MVP §6 carried forward** — `parent_layout`, register-lines/import-lines split, `is_safe_to_move`, severity breakdown, `default_parent_layout`.

### Reachable but unsurfaced (by design)

1. `viewHir`, `viewMir`, `viewCrateGraph`, `viewSyntaxTree`, `viewFileText`, `viewRecursiveMemoryLayout`, `getFailedObligations`, `interpretFunction` — debug views.
2. Test Explorer 7-method family — UX surface, not autonomous-LLM workflow.
3. `cancelFlycheck`/`clearFlycheck` — auxiliary.
4. `fetchDependencyList` — niche.
5. `parent_module_style="mod_rs"`, `reexport_policy="explicit_list"`, `fix_imports(files=["**"])`, `plan_file_split` strategies `by_visibility`/`by_type_affinity`.

All of the above are accessible via `execute_command` typed pass-through or via primitive-layer fallbacks. The directive's "no capability silently unavailable" rule is honored.

### Explicit_block (1 method, with rationale)

`experimental/onEnter` — semantics tied to literal Enter keystroke; meaningless for autonomous LLM; re-introduces snippet escape problem if allowed. Documented in §3.2.

### Required cross-language coordination (Rust + Python specialists)

1. Co-review `LanguageStrategy` interface (26 methods) before facade layer merges.
2. Settle the 4 capability gates (`supports_lifetimes`, `supports_macros`, `supports_structural_search`, `supports_proc_macros`) and how Python returns False values without breaking facade behavior.
3. Settle `dry_run_supported_for(facade_name)` per-facade matrix.
4. Settle `language_specific_facades()` MVP value (empty for both) and forward seam.
5. Confirm reverse-request `workspace/applyEdit` is full-fidelity for both strategies.
6. Confirm `severity_breakdown` schema is comparable across rust-analyzer and pyright.

### Effort, sized

**Rust-side total: ~7,335 LoC + 19 fixtures.** ~3.2× the narrow MVP. Concentrated in WorkspaceEdit applier (L), inherited facades expansion (L), 13 new facades (M each), tests (L), E2E (L).

Per CLAUDE.md, no time estimate is provided. Sizing summary: 6 S items (~520 LoC), 11 M items (~2,500 LoC), 7 L items (~4,300 LoC).

---

## 14. Appendix — Pydantic-style schemas for new facade inputs

These are stubs for design freeze. No implementation.

```python
# --- §1.2 / §2.2 facade #8 -----------------------------------------------
class ExtractKind(StrEnum):
    FUNCTION   = "function"
    VARIABLE   = "variable"
    CONSTANT   = "constant"
    STATIC     = "static"
    TYPE_ALIAS = "type_alias"

class ExtractExpressionInput(BaseModel):
    file: str
    range: Range
    kind: ExtractKind
    new_name: str
    visibility: Literal["private", "pub_crate", "pub"] = "private"
    dry_run: bool = False

# --- §1.3 / §2.2 facade #10 ----------------------------------------------
class InlineKind(StrEnum):
    CALL       = "call"
    VARIABLE   = "variable"
    TYPE_ALIAS = "type_alias"
    MACRO      = "macro"
    CONST      = "const"

class InlineScope(StrEnum):
    SINGLE_CALL_SITE = "single_call_site"
    ALL_CALLERS      = "all_callers"

class InlineSymbolInput(BaseModel):
    file: str
    name_path: str | None = None       # required for symbol-level inlines
    position: Position | None = None   # required for call-site inlines
    kind: InlineKind
    scope: InlineScope = InlineScope.SINGLE_CALL_SITE
    dry_run: bool = False

# --- §1.4 / §2.2 facade #11 ----------------------------------------------
class ExpandGlobImportsInput(BaseModel):
    files: list[str]
    include_reexports: bool = False
    dry_run: bool = False

# --- §1.5 / §2.2 facade #12 ----------------------------------------------
class Visibility(StrEnum):
    PRIVATE   = "private"
    PUB_SUPER = "pub_super"
    PUB_CRATE = "pub_crate"
    PUB       = "pub"

class ChangeVisibilityInput(BaseModel):
    file: str
    name_path: str
    new_visibility: Visibility
    dry_run: bool = False

# --- §1.6 / §2.2 facade #13 ----------------------------------------------
class TidyScope(StrEnum):
    FILE = "file"
    IMPL = "impl"
    STRUCT = "struct"

class TidyOption(StrEnum):
    IMPL_ORDER  = "impl_order"
    ITEM_ORDER  = "item_order"
    FIELD_ORDER = "field_order"

class TidyStructureInput(BaseModel):
    file: str
    scope: TidyScope = TidyScope.FILE
    options: list[TidyOption]
    dry_run: bool = False

# --- §1.7 / §2.2 facade #14, #15 -----------------------------------------
class GenerateTraitImplScaffoldInput(BaseModel):
    file: str
    type_name_path: str
    trait_path: str
    complete_missing: bool = True
    dry_run: bool = False

class GenerateMemberKind(StrEnum):
    FUNCTION = "function"
    GETTER   = "getter"
    SETTER   = "setter"
    NEW      = "new"
    DELEGATE = "delegate"

class GenerateMemberInput(BaseModel):
    file: str
    target_type_name_path: str
    member_kind: GenerateMemberKind
    member_name: str
    field_or_target: str | None = None
    dry_run: bool = False

# --- §1.8 / §2.2 facade #16 ----------------------------------------------
class TypeShapeChange(StrEnum):
    NAMED_TO_TUPLE       = "named_to_tuple"
    TUPLE_TO_NAMED       = "tuple_to_named"
    BOOL_TO_ENUM         = "bool_to_enum"
    TUPLE_RETURN_TO_STRUCT = "tuple_return_to_struct"

class ChangeTypeShapeInput(BaseModel):
    file: str
    type_name_path: str
    change: TypeShapeChange
    dry_run: bool = False

# --- §1.8 / §2.2 facade #17 ----------------------------------------------
class ReturnTypeChange(StrEnum):
    WRAP_OPTION   = "wrap_option"
    WRAP_RESULT   = "wrap_result"
    UNWRAP_OPTION = "unwrap_option"
    UNWRAP_RESULT = "unwrap_result"

class ChangeReturnTypeInput(BaseModel):
    file: str
    fn_name_path: str
    change: ReturnTypeChange
    dry_run: bool = False

# --- §1.9 / §2.2 facade #18 ----------------------------------------------
class CompleteMatchArmsInput(BaseModel):
    file: str
    position: Position
    dry_run: bool = False

# --- §1.10 / §2.2 facade #19 ---------------------------------------------
class ExtractLifetimeInput(BaseModel):
    file: str
    fn_or_type_name_path: str
    new_lifetime: str = "'a"
    dry_run: bool = False

# --- §3.1 extension facades ----------------------------------------------
class StructuralSearchReplaceInput(BaseModel):
    pattern: str        # rust-analyzer SSR pattern syntax
    template: str       # SSR replacement template
    files: list[str] | None = None
    max_edits: int = 500
    dry_run: bool = False

class RunFlycheckInput(BaseModel):
    scope: Literal["workspace", "package", "current_file"] = "workspace"

class VerifyAfterRefactorInput(BaseModel):
    checkpoint_id: str | None = None
    run_tests: bool = True
    test_filter: str | None = None

class ExpandMacroInput(BaseModel):
    file: str
    position: Position

class ParentModuleInput(BaseModel):
    file: str
    position: Position

class ChildModulesInput(BaseModel):
    file: str
    position: Position

class ViewItemTreeInput(BaseModel):
    file: str
```

All output schemas reuse `RefactorResult` from the design report's §3 with one addition for verification:

```python
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

## 15. Closing — what changed vs. the narrow specialist

| Dimension | Narrow MVP | Full-coverage MVP | Direction |
|---|---|---|---|
| Facades | 6 | 19 | **+13** |
| Assists facaded | 6 / 158 | 93 / 158 | **+87** |
| Custom extensions surfaced | 0 first-class | 8 first-class + 27 pass-through + 1 block | **+36 reach** |
| WorkspaceEdit variant tests | minimal | exhaustive matrix (~80 tests) | **+80 tests** |
| LSP methods wired | ~25 | ~52 | **+27** |
| Reverse-request handlers | 1 stub | 8 production-grade | **+7** |
| Pre-MVP spikes | 1 (multilspy progress) | 6 | **+5** |
| Fixtures | 5 + calcrs | 18 + calcrs | **+13** |
| E2E gates | 6 | 11 | **+5** |
| Strategy method count | ~12 | 26 | **+14** |
| Rust-side LoC | ~2,310 | ~7,335 | **+5,025** |
| What ships | a coherent split-file workflow | a coherent split-file workflow + the long tail of every rust-analyzer capability behind a documented interface | depth, in addition to breadth |

The narrow MVP optimized for shipping a clean dual-language story fast. The full-coverage MVP optimizes for **never having to apologize that "this rust-analyzer feature isn't reachable through scalpel"**. The cost of the latter is ~3.2× LoC and one additional staging gate. The benefit is a tool surface that genuinely matches the LSP it wraps — which is, after all, the project's stated goal.

---

*End of full-coverage Rust specialist input. Cross-references throughout to capabilities brief, protocol brief, and the authoritative design. Co-review with the Python specialist required before facade-layer merge per Stage C entry condition.*
