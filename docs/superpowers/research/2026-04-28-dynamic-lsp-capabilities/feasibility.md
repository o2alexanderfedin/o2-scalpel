# Feasibility — Dynamic LSP Discovery for Scalpel Facades

**Researcher**: Agent C (feasibility)
**Date**: 2026-04-28

## TL;DR (3 bullets)

- Dynamic method-support lookup (dimension A) is already half-done: `ServerCapabilities` post-`initialize` + `DynamicCapabilityRegistry` (runtime `client/registerCapability` events) give us most of what we need at LOW cost. The infrastructure shipped in the basedpyright dynamic-capability followup.
- Dynamic param-schema reconstruction (dimension B) is not-feasible as a runtime concern: the LSP spec provides no introspection RPC, and the only realistic path (parse `metaModel.json` at build time) adds complexity for near-zero gain on the actual facade surface — every facade already hardcodes its params or delegates to strategy-specific helpers.
- The 33 facades break into two populations: 26 "thin code-action wrappers" that would benefit trivially from a capability gate, and 7 "non-LSP-routed" facades (AST rewrite, rope direct, markdown pure-text) that bypass LSP capability checks entirely. The right answer is **option A** — dynamic capability detection only, wired at the coordinator boundary.

---

## 1. Surface inventory

All counts are from reading `scalpel_facades.py` and `scalpel_primitives.py` directly.

### Ergonomic facades (scalpel_facades.py — 33 Tool subclasses)

| Facade | LSP method(s) | Hardcoded per-lang? | Known gap? |
|---|---|---|---|
| `scalpel_split_file` | `textDocument/codeAction` (refactor.extract.module) / Rope `move_module` | yes — python→rope, rust→code-action | none at current surface |
| `scalpel_extract` | `textDocument/codeAction` (refactor.extract.*) | yes — python→pylsp-rope, rust→RA | pylsp-rope only for Python |
| `scalpel_inline` | `textDocument/codeAction` (refactor.inline.*) | yes — inferred per extension | RA-only for several targets |
| `scalpel_rename` | `textDocument/rename` + `textDocument/prepareRename` | yes — python via coord.merge_rename (pylsp-rope primary) | marksman also wired |
| `scalpel_imports_organize` | `textDocument/codeAction` (source.organizeImports) | yes — multi-server (ruff/rope/basedpyright) | rust: RA organises via code action; no python gap |
| `scalpel_convert_module_layout` | `textDocument/codeAction` (refactor.rewrite.move_module_to_file / move_inline_module_to_file) | yes — rust-analyzer only | python: not applicable |
| `scalpel_change_visibility` | `textDocument/codeAction` (refactor.rewrite.change_visibility) | yes — rust-analyzer only | python: not applicable |
| `scalpel_tidy_structure` | `textDocument/codeAction` (3 reorder/sort kinds) | yes — rust-analyzer only | python: not applicable |
| `scalpel_change_type_shape` | `textDocument/codeAction` (refactor.rewrite.convert_*) | yes — rust-analyzer only | python: not applicable |
| `scalpel_change_return_type` | `textDocument/codeAction` (refactor.rewrite.change_return_type) | yes — rust-analyzer only | python: not applicable |
| `scalpel_complete_match_arms` | `textDocument/codeAction` (quickfix.add_missing_match_arms) | yes — rust-analyzer only | python: not applicable |
| `scalpel_extract_lifetime` | `textDocument/codeAction` (refactor.extract.extract_lifetime) | yes — rust-analyzer only | python: not applicable |
| `scalpel_expand_glob_imports` | `textDocument/codeAction` (refactor.rewrite.expand_glob_imports) | yes — rust-analyzer only | python: not applicable |
| `scalpel_generate_trait_impl_scaffold` | `textDocument/codeAction` (refactor.rewrite.generate_trait_impl) | yes — rust-analyzer only | python: not applicable |
| `scalpel_generate_member` | `textDocument/codeAction` (refactor.rewrite.generate_{getter,setter,method,default_from_new}) | yes — rust-analyzer only | python: not applicable |
| `scalpel_expand_macro` | `rust-analyzer/expandMacro` (custom) | yes — rust-analyzer only | python: not applicable |
| `scalpel_verify_after_refactor` | `experimental/runnables` + `rust-analyzer/runFlycheck` | yes — rust-analyzer only | python: not applicable |
| `scalpel_convert_to_method_object` | `textDocument/codeAction` (refactor.rewrite.method_to_method_object) | yes — pylsp-rope only | rust: not applicable |
| `scalpel_local_to_field` | `textDocument/codeAction` (refactor.rewrite.local_to_field) | yes — pylsp-rope only | rust: not applicable |
| `scalpel_use_function` | `textDocument/codeAction` (refactor.rewrite.use_function) | yes — pylsp-rope only | rust: not applicable |
| `scalpel_introduce_parameter` | `textDocument/codeAction` (refactor.rewrite.introduce_parameter) | yes — pylsp-rope only | rust: not applicable |
| `scalpel_generate_from_undefined` | `textDocument/codeAction` (quickfix.generate) | yes — pylsp-rope only | rust: not applicable |
| `scalpel_auto_import_specialized` | `textDocument/codeAction` (quickfix.import) | yes — pylsp-rope / basedpyright | rust: not applicable |
| `scalpel_fix_lints` | `textDocument/codeAction` (source.fixAll.ruff) | yes — ruff only | rust: not applicable |
| `scalpel_ignore_diagnostic` | `textDocument/codeAction` (quickfix.pyright_ignore / quickfix.ruff_noqa) | yes — basedpyright or ruff | rust: not applicable |
| `scalpel_convert_to_async` | AST rewrite (no LSP call) | yes — python only | no LSP dependency |
| `scalpel_annotate_return_type` | `textDocument/inlayHint` (basedpyright) | yes — basedpyright only | rust: not applicable; method itself under-advertised by some pyright versions |
| `scalpel_convert_from_relative_imports` | Rope `relatives_to_absolutes` (no LSP call) | yes — python only | no LSP dependency |
| `scalpel_rename_heading` | `textDocument/rename` + `textDocument/prepareRename` | yes — marksman only | no gap; marksman implements both |
| `scalpel_split_doc` | none (markdown_doc_ops pure-text) | yes — markdown only | no LSP dependency |
| `scalpel_extract_section` | none (markdown_doc_ops pure-text) | yes — markdown only | no LSP dependency |
| `scalpel_organize_links` | none (markdown_doc_ops pure-text) | yes — markdown only | no LSP dependency |
| `scalpel_transaction_commit` | orchestration only — replays prior step tool calls | no direct LSP call | n/a |

### Always-on primitives (scalpel_primitives.py — 11 Tool subclasses)

| Primitive | LSP method(s) | Hardcoded per-lang? | Known gap? |
|---|---|---|---|
| `scalpel_capabilities_list` | none (static catalog query) | no | n/a |
| `scalpel_capability_describe` | none (static catalog query) | no | n/a |
| `scalpel_apply_capability` | `textDocument/codeAction` (long-tail dispatcher) | yes — via catalog `source_server` | n/a |
| `scalpel_dry_run_compose` | none (plumbing) | no | n/a |
| `scalpel_confirm_annotations` | indirect — calls `_apply_workspace_edit_to_disk` | no | n/a |
| `scalpel_rollback` | none (checkpoint restore) | no | n/a |
| `scalpel_transaction_rollback` | none (checkpoint restore) | no | n/a |
| `scalpel_workspace_health` | `DynamicCapabilityRegistry` + pool stats | no | dynamic registry already in prod |
| `scalpel_execute_command` | `workspace/executeCommand` | yes — per-language whitelist | non-whitelisted commands silently absent |
| `scalpel_reload_plugins` | none (plugin registry reload) | no | n/a |
| `scalpel_install_lsp_servers` | none (installer subprocess) | no | n/a |

---

## 2. Feasibility analysis

### A. Dynamic method-support lookup

**Rating: easy for static-capabilities, medium for dynamic-registration gaps**

The foundation is already in place:

1. **`ServerCapabilities` post-`initialize`**: The LSP `initialize` response carries a `ServerCapabilities` object that enumerates `renameProvider`, `codeActionProvider`, `inlayHintProvider`, etc. This is readable at the coordinator/adapter level without any probe — we already parse it implicitly when deciding whether to call methods. Making the check explicit (cache the parsed capabilities dict per server-instance) is a one-time addition to each adapter's `__init__` or `on_initialize`.

2. **`DynamicCapabilityRegistry`**: Already exists at `solidlsp/dynamic_capabilities.py` and is populated from `client/registerCapability` events. `scalpel_workspace_health` already surfaces `dynamic_capabilities` from it. basedpyright and pylsp are already wired (memory file confirms). The gap is that facades themselves do not consult this registry before dispatching — they assume the method works and surface a "no actions" result on failure.

3. **Under-advertising servers**: rust-analyzer consistently advertises all its code-action kinds up-front; the probe pattern (call and handle empty response) is what facades already do implicitly. A capability gate would short-circuit this to a fast structured error rather than a slow "no actions" path.

**Caching policy**: Per-server-instance is correct. The capability set is frozen at `initialize` except for `client/registerCapability` events, which the `DynamicCapabilityRegistry` already handles incrementally. No per-session re-query is needed.

**Critical finding**: The `scalpel_execute_command` whitelist is a *hardcoded* substitute for the LSP `workspace/executeCommand`-level capability check. The real `ServerCapabilities.executeCommandProvider.commands` list from each server's `initialize` response is richer and self-updating — replacing the whitelist with that list would be the canonical fix. This is the single highest-value target for dynamic method-support.

### B. Dynamic param-schema reconstruction

**Rating: not-feasible as a runtime concern; medium effort for build-time generation**

The LSP spec (3.17) provides no `textDocument/schemaQuery` or similar introspection RPC. The options are:

1. **`metaModel.json` at build time**: The official LSP meta-model JSON (available at `microsoft/language-server-protocol`) describes every standard method's param types. Python code generators (e.g. `pygls` 1.x + `lsprotocol`) can produce typed param dataclasses from it. This is what TypeScript's `vscode-languageclient` does internally. The path for o2-scalpel would be: pull `metaModel.json` → generate per-method param classes → import them in adapters/facades. Effort: medium (one-time). Benefit: mostly theoretical — the 26 LSP-backed facades already hardcode exactly the param subset they use, and the subset is narrow (`file`, `range`/`position`). A full param-schema generator would produce classes wider than anything the facades need.

2. **Server-extended methods**: `rust-analyzer/expandMacro`, `experimental/runnables`, `rust-analyzer/runFlycheck` — none of these appear in `metaModel.json`. The fallback for custom methods is the server's own documentation (or source). There is no runtime path for schema discovery here; the current approach (hardcode the custom RPC name + params in the adapter) is correct and unavoidable.

3. **The `workspaceSymbol` scenario** from the problem statement: The harness `find_symbol_position` calls `request_workspace_symbol` as a fallback, passing only a query string — there is no param-shape mismatch to fix dynamically. The schema for `workspace/symbol` is stable and fully covered by the existing coordinator call site. No benefit from dynamic schema reconstruction here.

**Conclusion**: Build-time `metaModel.json` generation is a refactor-for-consistency exercise, not a capability-gap fix. The actual param shapes are well-known, narrow, and stable for the methods the facades use.

### C. Per-facade migration cost

**Population A — thin code-action wrappers (26 facades)**: All call `coord.merge_code_actions(..., only=[kind])` then check `if not actions`. Adding a pre-dispatch capability gate would mean: before calling `merge_code_actions`, ask the coordinator `supports_kind(server_id, kind)` and return a structured `CAPABILITY_NOT_AVAILABLE` immediately if false. Each facade change is 3–5 lines. The shared `_dispatch_single_kind_facade` and `_python_dispatch_single_kind` helpers cover 22 of the 26 — adding the gate there propagates to all callers. Net: small effort, concentrated in 2 dispatcher functions.

**Population B — non-LSP-routed facades (7 facades)**: `scalpel_convert_to_async`, `scalpel_convert_from_relative_imports`, `scalpel_split_doc`, `scalpel_extract_section`, `scalpel_organize_links` (pure-text/AST), and `scalpel_annotate_return_type` (basedpyright inlay hints, gated by `_get_inlay_hint_provider` which already does graceful None-return). These facades bypass `merge_code_actions` entirely. Dynamic capability detection has zero benefit for them — they fail gracefully through their own error paths.

**Population C — orchestration + side-effect primitives (7 primitives)**: `scalpel_apply_capability`, `scalpel_dry_run_compose`, `scalpel_transaction_commit`, `scalpel_execute_command`, `scalpel_workspace_health`, `scalpel_rollback`, `scalpel_transaction_rollback`. Only `scalpel_execute_command` benefits clearly (replace hardcoded whitelist with `executeCommandProvider.commands` from `ServerCapabilities`). `scalpel_workspace_health` already queries `DynamicCapabilityRegistry`.

### D. Static + dynamic catalog coexistence

The static catalog (`capabilities.py`, built at test time from adapter introspection) serves two purposes that dynamic detection cannot replace:

1. **Drift CI gate**: The golden baseline (`--update-catalog-baseline`) catches when a strategy's `code_action_allow_list` diverges from what adapters actually advertise. A dynamic registry can only observe what a running server sends; it cannot assert what a server *should* send.

2. **LLM routing aid**: `scalpel_capabilities_list` / `scalpel_capability_describe` expose the catalog to the LLM before any server is started. A fully dynamic approach would require a running server to enumerate capabilities — breaking the cold-start routing pattern.

The correct architecture is **static catalog as aspiration + dynamic runtime as availability gate**:
- Static catalog: "these are the capabilities this server *should* support"
- Dynamic registry: "at this moment, this running server instance *has* registered these methods"
- Facade dispatch: check dynamic availability, emit `CAPABILITY_NOT_AVAILABLE` (not `SYMBOL_NOT_FOUND`) when the runtime gate fails

This coexistence is already partially implemented — `scalpel_workspace_health` surfaces `dynamic_capabilities` alongside `capabilities_advertised` from the static catalog. The gap is that individual facades do not yet consult the dynamic gate before dispatching.

---

## 3. Recommendation

**Option chosen**: Dynamic capability detection only (option A)

**Rationale**:

The real unsolved problem in the current system is not schema discovery — it's that when a server doesn't support a method at runtime, the facade returns a slow "no actions found" or a misleading `SYMBOL_NOT_FOUND` error instead of a fast, structured `CAPABILITY_NOT_AVAILABLE`. Dynamic detection fixes this signal clarity at low cost.

The work is:

1. **Extend `MultiServerCoordinator`** to expose `supports_kind(kind: str) -> bool` backed by the post-`initialize` `ServerCapabilities` parse + `DynamicCapabilityRegistry`.
2. **Add a 3-line capability gate** to `_dispatch_single_kind_facade` and `_python_dispatch_single_kind` (covers 22 of 26 LSP-backed facades automatically).
3. **Replace the `_EXECUTE_COMMAND_WHITELIST`** in `scalpel_execute_command` with a per-server `executeCommandProvider.commands` lookup from `ServerCapabilities`.
4. **No changes** to the static catalog, the drift CI gate, or the non-LSP-routed facades.

This is a **small** effort affecting ~3 locations in the codebase with high signal-quality payoff.

Dynamic param-schema reconstruction (option B) adds medium effort for near-zero benefit: every facade already hardcodes the exact narrow param subset it needs, and custom server methods have no meta-model entry anyway. Building `metaModel.json` parsing would be gold-plating.

Static-only iteration (option C) is the status quo — it does not close the "misleading error on unsupported method" signal-quality gap, which is the actual pain point.

**Risks**:

- A server that under-advertises a method it actually supports (e.g., an older pylsp-rope version that works but doesn't declare the code-action kind in `ServerCapabilities`) would be incorrectly gated out. Mitigation: gate should be opt-in per facade with a `force=True` escape hatch, and the fallback should be the current "call and accept empty" behaviour.
- `executeCommandProvider.commands` may not be populated by all server versions. Mitigation: fall back to the existing hardcoded whitelist when the field is absent.

---

## Open questions for the synthesis pair

1. Should the `supports_kind` gate be added to `MultiServerCoordinator.merge_code_actions` itself (transparent to all facades) or inserted explicitly in each dispatcher helper? Transparent insertion risks masking bugs where the server genuinely has the kind but `ServerCapabilities` is stale.
2. For `scalpel_execute_command`: the `executeCommandProvider.commands` list grows at runtime (servers can register new commands via `client/registerCapability`). Should `DynamicCapabilityRegistry` be extended to track command IDs separately from method names?
3. Should the static catalog record a `requires_dynamic_check: bool` flag per record, signalling to the LLM that availability is session-dependent (e.g., for methods that basedpyright only registers after indexing)?
4. The `scalpel_annotate_return_type` facade already gracefully handles `textDocument/inlayHint` unavailability via `_get_inlay_hint_provider() → None`. Is this the pattern the dynamic gate should generalise, or should it emit a structured `CAPABILITY_NOT_AVAILABLE` to the LLM instead of a silent skip?

---

## Files referenced

- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_facades.py` (33 ergonomic facades)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_primitives.py` (11 always-on primitives)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/capabilities.py` (static catalog + build logic)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/solidlsp/dynamic_capabilities.py` (runtime registry)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/language_strategy.py` (strategy protocol + code_action_allow_list)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/python_strategy.py` (PythonStrategy + SERVER_SET)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/rust_strategy.py` (RustStrategy + execute-command whitelist)
- `/Users/alexanderfedin/.claude/projects/-Volumes-Unitek-B-Projects-o2-scalpel/memory/reference_lsp_capability_gaps.md` (known per-LSP gaps)
