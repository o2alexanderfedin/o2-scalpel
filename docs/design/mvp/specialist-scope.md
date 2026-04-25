# MVP Scope — Engineering Delivery Specialist View (Full-Coverage Directive)

Status: report-only. Brainstorm input for the **second** MVP scope round, under a reversed product directive: full feature coverage of the chosen LSPs for Rust + Python instead of the four-tool narrow surface that the prior round landed on.

Scope-discipline lens. Sizing via small/medium/large plus LoC counts; no time estimates per project `CLAUDE.md`. Authoritative-design tone; table-dominant.

Cross-references:
- [Main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — authoritative architecture.
- [Open-questions resolution](../2026-04-24-o2-scalpel-open-questions-resolution.md) — Q10/Q11/Q12/Q13/Q14 decisions still apply.
- [Prior narrow scope](archive-v1-narrow/specialist-scope.md) and [prior synthesis report](archive-v1-narrow/2026-04-24-mvp-scope-report.md) — superseded by this report on the **what-ships** axis; their primitive-layer and applier analyses still hold.
- Research briefs: [rust-analyzer capabilities](../../research/2026-04-24-rust-analyzer-capabilities-brief.md), [cache-discovery](../../research/2026-04-24-cache-discovery-brief.md), [two-process](../../research/2026-04-24-two-process-brief.md), [marketplace](../../research/2026-04-24-marketplace-brief.md), [license-rename](../../research/2026-04-24-license-rename-brief.md).

---

## §0 — Directive change and what it changes

| Axis | Prior MVP (v1-narrow) | New MVP directive (this report) |
|---|---|---|
| Tool surface | 3 facades + 0 primitives = 4 tools (rollback counted) | Every assist family + every primitive reachable; ~25–30 tools |
| Languages | Rust + Python (same) | Rust + Python (unchanged) |
| LSP servers | rust-analyzer + pyright (one each) | rust-analyzer + pylsp(+rope+mypy+ruff) + basedpyright; up to four LSP processes |
| LSP capability coverage | Just enough to drive 3 facades | **Full** coverage of every chosen LSP's published capability surface |
| Falsifiability gate | 7 E2E scenarios | ~15 E2E + ~60 integration tests, one per assist family |
| LoC ceiling | ~5,010 logic + fixtures, ~8,665 fully loaded | ~14,000–18,000 logic + fixtures (§3) |
| Resource floor | 16 GB dev laptop | 24 GB recommended; 16 GB still supported via opt-out flags |
| Distribution at MVP | local `uvx --from <path>` only | same; marketplace stays at v1.1 — argued in §10 |

**The directive does not double the LoC; it triples the test-and-fixture surface and roughly doubles the production surface.** The agnostic core stays the same. The cost lives in: (a) more `WorkspaceEdit` shapes verified by the applier, (b) one fixture per assist family instead of one fixture per facade, (c) a multi-server multiplexer for Python where the prior MVP had a single pyright instance, (d) a capability-catalog tool that exposes everything the LLM can actually reach.

This report is honest about that cost. It does **not** soften the directive into "full-ish" coverage. It also does not pretend that "full" is binary — §5 stages it.

---

## §1 — Falsifiable MVP statement (full-coverage)

> **Scalpel MVP is done when (a) every assist family in rust-analyzer's 158-handler inventory is reachable from a Claude Code session via either a named facade tool or the `apply_code_action` primitive — verified by one passing integration test per family — and (b) every Rope-backed refactor exposed by `pylsp-rope` plus every `source.*` action exposed by `basedpyright` and `ruff` is reachable likewise; and the seven user-journey E2E scenarios pass on `calcrs` + `calcpy` + a multi-family `kitchen_sink_rs/py` fixture; the Stage-1 capability-catalog tool reports the full inventory and that report is byte-equal to a checked-in baseline.**

Falsifiable on five axes:

1. **Coverage.** A test in `test/integration/assist_families/` exists and passes for **each** rust-analyzer assist family (15 families, §2.1) and **each** Python refactor command (9 pylsp-rope + 4 basedpyright + 2 ruff = 15, §2.2).
2. **Reachability.** The `list_capabilities` MCP tool (§4) returns a complete catalog whose `family_id` set matches the integration-test set. If a family is in the catalog but no test, MVP is not done. If a test is green but the family isn't catalogued, MVP is not done.
3. **User journeys.** The seven E2E scenarios from the prior MVP plus eight new ones (§6) pass on `calcrs`, `calcpy`, and the `kitchen_sink_*` fixtures.
4. **Distribution.** `uvx --from <local-path> serena-mcp-server --mode scalpel` installs cleanly on a 24 GB dev laptop with no PyPI dependency and no marketplace dependency.
5. **Resource floor.** With all four LSP processes spawned, RSS stays under 8 GB on the `calcrs+calcpy` fixtures; pertinent E2E run completes within the §9 wall-clock budget.

If any axis fails, MVP is not done. Axis 1 is the load-bearing one — it is what makes "full coverage" measurable.

---

## §2 — Feature triage matrix (full-coverage)

Legend:
- **MVP** = blocks the §1 statement.
- **MVP-primitive** = reachable via the primitive escape hatch (`apply_code_action` / direct `executeCommand`); test exists; no dedicated facade.
- **MVP-facade** = wrapped by a named, schema-validated MCP tool with its own integration tests.
- **v1.1** = follows MVP immediately.
- **v2+** = genuinely optional.

### 2.1 rust-analyzer assist families (158 handlers grouped into 15 families)

The 158 assists are grouped by what an LLM caller would request, not by file path. Each family has a representative handler; the family is "covered" when at least one handler from the family round-trips through scalpel with the `WorkspaceEdit` correctly applied.

| # | Family (15) | Representative handlers | Stage | Reachability path |
|---|---|---|---|---|
| 1 | **Module/file boundary** | `extract_module`, `move_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs` | MVP-facade | `split_file_by_symbols`, `move_inline_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs` |
| 2 | **Extractors** | `extract_function`, `extract_variable`, `extract_type_alias`, `extract_struct_from_enum_variant`, `extract_expressions_from_format_string`, `promote_local_to_const` | MVP-facade | `extract` facade (multiplexes the six handlers; LLM passes `kind`) |
| 3 | **Inliners** | `inline_local_variable`, `inline_call`, `inline_into_callers`, `inline_type_alias`, `inline_type_alias_uses`, `inline_macro`, `inline_const_as_literal` | MVP-facade | `inline` facade |
| 4 | **Visibility & import hygiene** | `change_visibility`, `fix_visibility`, `auto_import`, `qualify_path`, `replace_qualified_name_with_use`, `remove_unused_imports`, `merge_imports`, `unmerge_imports`, `normalize_import`, `split_import`, `expand_glob_import`, `expand_glob_reexport` | MVP-facade | `fix_imports` (already specced) covers organize-import family; `change_visibility` exposed as its own facade |
| 5 | **Ordering helpers** | `reorder_impl_items`, `sort_items`, `reorder_fields` | MVP-primitive | `apply_code_action(kind="refactor.rewrite", filter="reorder|sort")` |
| 6 | **Generators (impls)** | `generate_impl`, `generate_trait_impl`, `generate_impl_trait`, `generate_default_from_new`, `generate_derive`, `generate_documentation_template`, `generate_function`, `generate_getter`, `generate_setter`, `generate_new`, `generate_constant` (~30 handlers) | MVP-primitive | `apply_code_action(kind="quickfix"|"refactor.rewrite")` |
| 7 | **Replace family** | `replace_arith_op`, `replace_let_with_match`, `replace_match_with_if_let`, `replace_named_generic_with_impl`, `replace_qualified_name_with_use`, `replace_string_with_char`, `replace_turbofish_with_type_alias` (~20 handlers) | MVP-primitive | Same. |
| 8 | **Convert family** | `convert_bool_then_to_if`, `convert_for_loop_with_iter_to_for_each`, `convert_into_to_from`, `convert_iter_for_each_to_for`, `convert_match_to_let_else`, `convert_named_struct_to_tuple_struct`, `convert_to_guarded_return`, `convert_tuple_struct_to_named_struct`, `convert_two_arm_bool_match_to_matches_macro` (~25 handlers) | MVP-primitive | Same. |
| 9 | **Apply/flip/wrap micro-rewrites** | `apply_demorgan`, `flip_binexpr`, `flip_comma`, `flip_or_pattern`, `wrap_return_type`, `wrap_unwrap_cargo_dep`, `unwrap_block`, `unwrap_tuple` (~15 handlers) | MVP-primitive | Same. |
| 10 | **Pattern-related** | `add_explicit_type`, `add_label_to_loop`, `add_lifetime_to_type`, `add_missing_match_arms`, `add_return_type`, `bind_unused_param`, `destructure_struct_binding`, `destructure_tuple_binding` (~15 handlers) | MVP-primitive | Same. |
| 11 | **String/format** | `extract_expressions_from_format_string`, `move_format_string_arg`, `inline_macro` (when applied to `format!`) | MVP-primitive | Same. |
| 12 | **Async sugar** | `toggle_async_sugar`, `toggle_macro_delimiter` | MVP-primitive | Same. |
| 13 | **Term search / construct** | `term_search`, `into_to_qualified_from`, `qualify_method_call_as_path` | MVP-primitive | Same. |
| 14 | **Diagnostic-driven quickfixes** | every assist with `kind = quickfix` (~30 handlers — includes clippy lifts via flycheck) | MVP-facade | `apply_quickfix_at` facade — driven by published-diagnostics offsets |
| 15 | **Rename** (special — not technically `codeAction` but adjacent) | `textDocument/prepareRename` + `textDocument/rename` | MVP-facade | `rename_symbol` (reuses Serena's existing facade; regression-tested) |

Total handlers covered: 158 of 158. **Reach** = MVP-facade for 5 families + MVP-primitive for 10 families. The 5 facades chosen for MVP are families that an LLM is **likely** to request as named operations (extract, inline, split, fix-imports, rename, change-visibility, quickfix-at-position); the rest are reachable through `apply_code_action` and listed in `list_capabilities`.

### 2.2 rust-analyzer custom LSP extensions (33 methods)

| # | Extension | Stage | Justification |
|---|---|---|---|
| 1 | `experimental/parentModule` | MVP-primitive | Used by `move_to_mod_rs` facade internally. |
| 2 | `experimental/joinLines` | MVP-primitive | Exposed verbatim. |
| 3 | `experimental/onEnter` | v2+ | Editor-only; LLM doesn't press Enter. |
| 4 | `experimental/matchingBrace` | v2+ | Editor-only. |
| 5 | `experimental/ssr` | MVP-facade | `structural_search_replace` — high LLM value; 1 facade. |
| 6 | `experimental/runnables` | MVP-primitive | Forms the input to `runFlycheck` equivalents. |
| 7 | `experimental/externalDocs` | MVP-primitive | Read-only; cheap to expose. |
| 8 | `experimental/openCargoToml` | MVP-primitive | Read-only. |
| 9 | `experimental/moveItem` | MVP-primitive | `direction: up/down`; rarely useful for LLM but cheap. |
| 10 | `experimental/serverStatus` (notification) | MVP | Wired into the cold-start gate (§7). |
| 11–17 | `experimental/discoverTest`, `runTest`, `endRunTest`, `abortRunTest`, `changeTestState`, `appendOutputToRunTest`, `discoveredTests` | v1.1 | Test Explorer surface; defer. |
| 18 | `rust-analyzer/analyzerStatus` | MVP-primitive | Diagnostic dump; useful for debugging hung server. |
| 19 | `rust-analyzer/reloadWorkspace` | MVP-primitive | Required when `Cargo.toml` changes. |
| 20 | `rust-analyzer/rebuildProcMacros` | MVP-primitive | Required after macro crate edits. |
| 21 | `rust-analyzer/runFlycheck` | MVP-facade | `run_check` facade — forces a diagnostic pass post-refactor. |
| 22 | `rust-analyzer/cancelFlycheck` | MVP-primitive | |
| 23 | `rust-analyzer/clearFlycheck` | MVP-primitive | |
| 24 | `rust-analyzer/viewSyntaxTree` | v2+ | IDE debug only. |
| 25 | `rust-analyzer/viewHir` | v2+ | IDE debug only — explicit cut per directive. |
| 26 | `rust-analyzer/viewMir` | v2+ | Same. |
| 27 | `rust-analyzer/viewFileText` | MVP-primitive | Useful as ground truth when buffers diverge. |
| 28 | `rust-analyzer/viewItemTree` | MVP-primitive | Cheaper than walking documentSymbol; used by `plan_file_split`. |
| 29 | `rust-analyzer/viewCrateGraph` | v2+ | SVG; not LLM-friendly. |
| 30 | `rust-analyzer/expandMacro` | MVP-primitive | High-value debugging primitive. |
| 31 | `rust-analyzer/relatedTests` | MVP-primitive | Drives `run_check` filter. |
| 32 | `rust-analyzer/fetchDependencyList` | MVP-primitive | Needed by Python's `auto_import` analogue path. |
| 33 | `rust-analyzer/viewRecursiveMemoryLayout` | v2+ | Niche. |
| 34 | `rust-analyzer/getFailedObligations` | v2+ | Trait-solver internals. |
| 35 | `rust-analyzer/interpretFunction` | v2+ | const-eval introspection. |
| 36 | `rust-analyzer/childModules` | MVP-primitive | Cheap counterpart to `parentModule`. |

Of 36 listed extensions, **19 are MVP** (3 facades + 16 primitives), **7 are v1.1** (Test Explorer), **10 are v2+** (IDE-debug only). The cuts are explicit and justified per the directive.

### 2.3 Python LSP capability coverage (pylsp + pylsp-rope + pylsp-mypy + pylsp-ruff + basedpyright + ruff)

Python is multi-server. The MVP Python strategy talks to **all four** servers in parallel and routes by capability:

| Server | Role | MVP capabilities |
|---|---|---|
| `pylsp` | Refactor primary | base completions, definitions, references, hovers, formatting; hosts the rope/mypy/ruff plugins |
| `pylsp-rope` | Refactor commands | 9 rope commands (full list below) |
| `pylsp-mypy` | Type diagnostics | `publishDiagnostics` for mypy errors; quickfixes |
| `pylsp-ruff` | Lint diagnostics + fixes | `publishDiagnostics`; `source.fixAll`; per-rule code actions |
| `basedpyright` | Read-only secondary | go-to-def, references, hover, auto-import, organize-imports, type diagnostics — **redundant with pylsp for read but more accurate; used as a corroborator on diagnostics-delta** |
| `ruff` (standalone, optional) | Format-only fast path | `textDocument/formatting` if a separate `ruff server` is preferred to `pylsp-ruff` |

#### 2.3.1 pylsp-rope command surface (full)

| # | Rope command | Family (analogue to RA) | Stage |
|---|---|---|---|
| 1 | `pylsp_rope.refactor.extract.method` | Extractors | MVP-facade (`extract`) |
| 2 | `pylsp_rope.refactor.extract.variable` | Extractors | MVP-facade (`extract`) |
| 3 | `pylsp_rope.refactor.inline` | Inliners | MVP-facade (`inline`) |
| 4 | `pylsp_rope.refactor.local_to_field` | Module/class boundary | MVP-primitive |
| 5 | `pylsp_rope.refactor.method_to_method_object` | Refactor (rewrite) | MVP-primitive |
| 6 | `pylsp_rope.refactor.use_function` | Replace | MVP-primitive |
| 7 | `pylsp_rope.refactor.introduce_parameter` | Refactor | MVP-primitive |
| 8 | `pylsp_rope.quickfix.generate` | Generators | MVP-primitive |
| 9 | `pylsp_rope.source.organize_import` | Visibility/import hygiene | MVP-facade (`fix_imports`) |
| 10 | (library-only) `rope.refactor.move.MoveGlobal` | Module/file boundary | MVP-facade — **driven via Rope-as-library inside `PythonStrategy`** because pylsp-rope does not expose it |
| 11 | (library-only) `rope.refactor.move.create_move` | Same | Same |
| 12 | (library-only) `rope.refactor.rename.Rename` (per-module) | Rename | MVP-facade (`rename_symbol`) — pylsp-rope routes through this internally |

**MVP commitment**: every pylsp-rope command (1–9) and the two library-only Move classes (10–11). The directive's "full support" clause covers Rope-as-library because it is the only path to `extract_module` shape behavior on Python.

#### 2.3.2 basedpyright code-action surface

basedpyright's `codeAction` surface is narrow and Pylance-derived (refactor.extract is *not* shipped):

| # | Action kind | Stage |
|---|---|---|
| 1 | `source.organizeImports` | MVP-facade (`fix_imports` consumes both pylsp-rope's and basedpyright's; chooses higher-confidence) |
| 2 | `quickfix` (auto-import for unresolved name) | MVP-facade (same) |
| 3 | `quickfix` (add `# pyright: ignore[…]` line directive) | MVP-primitive |
| 4 | `quickfix` (annotate type from inferred) | MVP-primitive |

Total: 4 actions, all MVP-reachable.

#### 2.3.3 ruff code-action surface

| # | Action kind | Stage |
|---|---|---|
| 1 | `source.fixAll.ruff` | MVP-facade (`apply_lint_fixes`) |
| 2 | per-rule `quickfix.ruff.<RULE>` | MVP-primitive |
| 3 | `source.organizeImports.ruff` (if I001 enabled) | MVP-facade (consumed by `fix_imports`) |

Total Python capability inventory: **9 rope + 4 basedpyright + 3 ruff = 16 distinct actions**, plus the 2 Rope-library-only operations = **18**. Combined with the Rust 158 → **176 distinct capabilities at MVP**.

### 2.4 Layer 1 — LSP primitive layer (`solidlsp`) — full-coverage view

The prior MVP needed minimal primitive support. Full coverage adds:

| Item | Prior MVP | This MVP | Delta |
|---|---|---|---|
| `request_code_actions` | yes | yes | — |
| `resolve_code_action` | yes | yes | — |
| `execute_command` | v1.1 | **MVP** — pylsp-rope routes through it; ruff `source.fixAll`; basedpyright auto-imports | New ~50 LoC |
| `workspace/applyEdit` reverse handler | yes | yes | — |
| `$/progress` rust-analyzer indexing | yes | yes | — |
| `$/progress` pylsp index | v1.1 | **MVP** — large monorepos otherwise flake | +20 LoC |
| `WorkspaceEdit.TextDocumentEdit` | yes | yes | — |
| `WorkspaceEdit.CreateFile` | yes | yes | — |
| `WorkspaceEdit.RenameFile` | yes | yes | — |
| `WorkspaceEdit.DeleteFile` | v1.1 | **MVP** — Rope `MoveGlobal` emits it | +30 LoC |
| `changeAnnotations` w/ `needsConfirmation` | v1.1 (reject) | **MVP** (auto-accept policy + audit log) | +40 LoC |
| Snippet-marker stripping | yes | yes | — |
| Order preservation in `documentChanges` | yes | yes | — |
| Version check + retry on `ContentModified` | yes | yes | — |
| Atomic apply + checkpoint | yes (in-memory) | yes (in-memory; v1.1 disk) | — |
| Inverse `WorkspaceEdit` computation | yes | yes — extended for DeleteFile | +20 LoC |
| Multi-server broadcast (`didOpen`/`didChange` to N) | n/a | **MVP** — Python has 4 servers | +60 LoC |
| Diagnostics aggregation (multi-server union) | n/a | **MVP** — same | +50 LoC |
| `$/progress` token namespacing per server | n/a | **MVP** | +20 LoC |
| `source.*` action prioritization/dedup | v1.1 | **MVP** — basedpyright + pylsp + ruff all emit organize-imports; pick one | +30 LoC |

**Net primitive-layer delta from prior MVP: +320 LoC.** This is the single biggest "full-coverage" cost in the LSP layer; most of it is multi-server multiplexing.

### 2.5 Layer 2 — Facade tools (full-coverage MCP surface)

Top-of-funnel facades the LLM is most likely to call. Each is named, schema-validated, integration-tested.

| # | Facade | Languages | Stage | Notes |
|---|---|---|---|---|
| 1 | `split_file_by_symbols` | Rust, Python | MVP | Carries over from prior MVP. |
| 2 | `fix_imports` | Rust, Python | MVP | Multi-server consolidator on Python. |
| 3 | `rollback_refactor` | Rust, Python | MVP | Same as prior. |
| 4 | `extract` (function/variable/type-alias) | Rust, Python | MVP | Multiplexes 6 RA handlers + 2 rope. |
| 5 | `inline` (variable/call/type-alias) | Rust, Python | MVP | Multiplexes 7 RA + 1 rope. |
| 6 | `move_inline_module_to_file` | Rust | MVP | RA-only; Python's analogue is `split_file_by_symbols`. |
| 7 | `move_from_mod_rs` / `move_to_mod_rs` | Rust | MVP | RA-only. |
| 8 | `rename_symbol` | Rust, Python | MVP | Reuses Serena's existing tool; regression-tested. |
| 9 | `change_visibility` | Rust | MVP | RA `change_visibility` + `fix_visibility`. |
| 10 | `apply_quickfix_at` | Rust, Python | MVP | Diagnostic-driven; routes through whichever server emitted the diagnostic. |
| 11 | `run_check` | Rust, Python | MVP | RA `runFlycheck` / pylsp-mypy refresh / ruff full-pass. |
| 12 | `apply_lint_fixes` | Python (Rust v1.1) | MVP | Ruff `source.fixAll`. |
| 13 | `structural_search_replace` | Rust | MVP | `experimental/ssr`. |
| 14 | `plan_file_split` | Rust, Python | MVP | Read-only planning; promoted from v1.1 because full-coverage MVP wants the LLM to plan before splitting. |
| 15 | `apply_code_action` | Rust, Python | MVP | **The primitive escape hatch** — required by the directive (every assist must be reachable). |
| 16 | `list_capabilities` | Rust, Python | MVP | Returns the catalog (§4); the §1 falsifiability gate. |
| 17 | `resolve_code_action` | Rust, Python | MVP | Two-phase resolve, exposed for cases where the LLM wants to inspect before applying. |
| 18 | `list_code_actions` | Rust, Python | MVP | Exposes raw `codeAction` results at a position. |
| 19 | `execute_command` | Rust, Python | MVP | Whitelisted executeCommand (per-strategy whitelist). |

**Total MVP MCP tools: 19** — vs. 4 in the prior MVP. This is the directive's headline cost on the agent-UX axis (handed off to the Agent-UX specialist). The agent-UX specialist must rule on whether 19 tools fit comfortably in a Claude Code session's tool budget; this report assumes yes with proper tool-prefix grouping (`mcp__o2-scalpel__refactor.split_file_by_symbols` style).

Deferred to v1.1: `extract_symbols_to_module` (sugar), `extract_to_constant`, `extract_struct_field`, per-method-pattern facades. Deferred to v2+: any facade that wraps a single rare assist without an obvious user journey.

### 2.6 Layer 3 — Language strategies (full-coverage view)

| Strategy | Stage | LoC est. | Notes |
|---|---|---|---|
| `LanguageStrategy` Protocol | MVP | ~140 | +20 LoC over prior to support multi-command and multi-server hooks |
| Strategy registry (static) | MVP | ~25 | |
| `RustStrategy` | MVP | ~400 | +220 LoC over prior — must declare all 15 family kinds, server-extension whitelist of 19 MVP extensions, init overrides, capability-catalog fragment |
| `PythonStrategy` | MVP | ~400 | +220 LoC over prior — multi-server orchestration, Rope-as-library Move path, basedpyright corroboration logic |
| `TypeScriptStrategy` paper design | MVP (paper) | 0 LoC | Same as prior — keeps the abstraction honest. |
| `GoStrategy` / `CppStrategy` | v2+ | 0 LoC | Explicit cut (§9). |
| Server-extension whitelist | MVP | (in strategy) | Now non-trivially populated |
| `post_apply_health_check_commands` | MVP | (in strategy) | RA: `runFlycheck`; Python: pylsp-mypy refresh + ruff source.fixAll dry-run |
| `lsp_init_overrides` | MVP | (in strategy) | RA: `cargo.targetDir`; Python: `pylsp.plugins.rope.enabled=true`, etc. |
| `multi_server` config | MVP | (in strategy) | Python only; declares the four servers and routing rules |

### 2.7 Deployment and discovery (unchanged from prior MVP)

Carry over verbatim from prior MVP (archive-v1-narrow §2.5):
- `o2-scalpel/.claude-plugin/plugin.json` — MVP
- `o2-scalpel/.mcp.json` — MVP
- Sibling-LSP discovery (walking `~/.claude/plugins/cache/`) — MVP
- `O2_SCALPEL_PLUGINS_CACHE` env override — MVP
- `platformdirs` path resolution — MVP
- `multilspy` adoption — MVP
- `pydantic` schema on `.lsp.json` — MVP
- Lazy spawn — MVP
- Marketplace / `marketplace.json` — v1.1 (argued in §10)
- `verify-scalpel.sh` SessionStart hook — v1.1
- `o2-scalpel-newplugin` generator — v2+
- Reference LSP-config plugins — v2+

The discovery layer is independent of capability coverage; it does not grow under the new directive.

### 2.8 Fixtures

| # | Fixture | Stage | Size | Notes |
|---|---|---|---|---|
| 1 | `calcrs/` | MVP | ~700 LoC + tests | Carry-over. The §6 happy-path E2E. |
| 2 | `calcpy/` | MVP | ~600 LoC + tests | Carry-over. The Python happy-path E2E. |
| 3 | `kitchen_sink_rs/` | MVP | ~1,200 LoC | New. One file per assist family; deliberately exercises every of the 15 RA families with a minimal example. |
| 4 | `kitchen_sink_py/` | MVP | ~900 LoC | Same shape for Python. |
| 5 | `big_cohesive.rs` (integration) | MVP | ~400 LoC | Carry-over. |
| 6 | `big_heterogeneous.rs` (integration) | MVP | ~500 LoC | Carry-over. |
| 7 | `big_cohesive.py` (integration) | MVP | ~400 LoC | New analogue. |
| 8 | `big_heterogeneous.py` (integration) | MVP | ~500 LoC | New analogue. |
| 9 | `cross_visibility.rs` | MVP | ~250 LoC | Promoted from v1.1 — needed for the `change_visibility` facade. |
| 10 | `with_macros.rs` | MVP | ~300 LoC | Promoted — `expandMacro` primitive needs a fixture. |
| 11 | `inline_modules.rs` | MVP | ~200 LoC | Promoted — `move_inline_module_to_file` is MVP. |
| 12 | `mod_rs_swap.rs` | MVP | ~150 LoC | Promoted — `move_from_mod_rs`/`move_to_mod_rs` are MVP. |
| 13 | `multi_crate_rs/` | v1.1 | — | E5 scenario; not blocking. |
| 14 | `multi_package_py/` | v1.1 | — | Same shape for Python. |
| 15 | `proc_macro_heavy_rs/` | v1.1 | — | Stress test for `rebuildProcMacros`. |
| 16 | `flycheck_diagnostics_rs/` | MVP | ~300 LoC | Drives `apply_quickfix_at` family. |
| 17 | `mypy_diagnostics_py/` | MVP | ~250 LoC | Drives Python `apply_quickfix_at`. |
| 18 | `ruff_diagnostics_py/` | MVP | ~200 LoC | Drives `apply_lint_fixes`. |
| 19 | `ssr_targets_rs/` | MVP | ~200 LoC | Drives `structural_search_replace`. |
| 20 | `cohesion_planning_rs/` | MVP | ~250 LoC | Drives `plan_file_split`. |
| 21 | `cohesion_planning_py/` | MVP | ~250 LoC | Same. |

**MVP fixture LoC: ~7,150** vs. prior ~2,175 — 3.3× growth. Justified by §1 axis 1.

### 2.9 E2E scenarios (full-coverage)

| # | Scenario | Languages | Stage | Notes |
|---|---|---|---|---|
| E1 | Happy-path split | Rust, Python | MVP | carry-over |
| E2 | Dry-run → inspect → commit | Both | MVP | carry-over |
| E3 | Rollback after failure | Both | MVP | carry-over |
| E4 | Concurrent edit mid-refactor (`ContentModified` retry) | Both | MVP | promoted from v1.1 — multi-server makes drift more likely |
| E5 | Multi-crate / multi-package workspace | Both | v1.1 | not blocking |
| E6 | `fix_imports` on glob `**/*.{rs,py}` | Both | MVP | promoted — full-coverage MVP must work on real-world file sets |
| E7 | rust-analyzer cold start under §9 budget | Rust | MVP | promoted — coverage requires reliability |
| E8 | LSP crash recovery (transparent respawn) | Both | MVP | promoted — 4 LSP processes means failure odds compound |
| E9 | Semantic equivalence | Both | MVP | carry-over |
| E10 | Regression on `rename_symbol` | Both | MVP | carry-over |
| E11 | `extract` round-trip (function + variable + type-alias) | Both | MVP | new; gates the `extract` facade |
| E12 | `inline` round-trip | Both | MVP | new; gates the `inline` facade |
| E13 | `apply_quickfix_at` over diagnostic stream | Both | MVP | new; gates the diagnostic-driven family |
| E14 | `structural_search_replace` over `ssr_targets_rs` | Rust | MVP | new; gates SSR facade |
| E15 | `plan_file_split` produces actionable plan consumed by `split_file_by_symbols` | Both | MVP | new; gates planning surface |
| E16 | `kitchen_sink_*` covers all 15 RA families + 16 Py capabilities, single E2E run | Both | MVP | new; the §1 axis-1 enforcer |
| E17 | Capability catalog byte-equal to baseline | Both | MVP | new; gates §1 axis 2 |

**MVP E2E set: 15 scenarios** (E1–E4, E6–E17 minus E5 which is v1.1). Up from 7 in the prior MVP.

### 2.10 Cuts that the directive does NOT forbid

For absolute clarity, "full coverage of the chosen LSPs" does not mean "everything everywhere." See §9 for the explicit cut list.

---

## §3 — Honest LoC re-estimate (full-coverage MVP)

### 3.1 Layer-by-layer

Numbers below are deltas from the prior MVP's ~5,010 logic+fixtures (~8,665 fully loaded), expanded with the new test surface.

| Layer | Prior MVP LoC | Full-coverage MVP LoC | Delta | Driver |
|---|---|---|---|---|
| `solidlsp` extensions (primitive layer) | ~150 | **~470** | +320 | Multi-server broadcast, executeCommand, multi-progress, DeleteFile, changeAnnotations |
| WorkspaceEdit applier (`code_editor.py`) | ~150 | **~280** | +130 | DeleteFile, multi-server source.* dedup, executeCommand result handling |
| Checkpoint / rollback | ~100 | **~140** | +40 | Inverse-edit for DeleteFile + multi-server snapshot fan-in |
| Multi-server multiplexer (Python only; new) | 0 | **~250** | +250 | New module: routing table, broadcast, capability dispatch, diagnostics merge |
| Lazy-spawn pool (`lsp_pool.py`) | ~100 | **~180** | +80 | Per-(language, root, server-id) registry; per-Python-server idle timers |
| Plugin-cache discovery | ~80 | **~110** | +30 | Discovers 4 Python servers, not 1 |
| Capability catalog generator | 0 | **~200** | +200 | New module: introspects strategies, advertises via `list_capabilities` |
| `LanguageStrategy` Protocol | ~120 | **~140** | +20 | Multi-server hooks, command whitelist, family declarations |
| `RustStrategy` | ~180 | **~400** | +220 | All 15 family kinds, 19 extension whitelist, init overrides, catalog fragment |
| `PythonStrategy` | ~180 | **~400** | +220 | Multi-server orchestration, Rope-as-library, basedpyright corroboration |
| Strategy registry | ~25 | ~25 | — | Static dict |
| Facade tools (in `refactoring_tools.py`) | ~600 | **~1,800** | +1,200 | 19 facades vs. 3; family multiplexers add ~100 LoC each |
| Primitive MCP tools (`list_capabilities`, `apply_code_action`, etc.) | 0 | **~400** | +400 | 4 primitive tools × ~100 LoC |
| `LanguageStrategy` interface tests (unit) | ~150 | **~250** | +100 | Multi-server scenarios |
| WorkspaceEdit applier unit tests | ~300 | **~600** | +300 | One snapshot test per `WorkspaceEdit` shape variation |
| Strategy unit tests (Rust + Python) | ~100 | **~400** | +300 | Per-family declaration assertions |
| Capability catalog unit tests | 0 | **~150** | +150 | Catalog round-trips, baseline diff |
| Multi-server multiplexer unit tests | 0 | **~250** | +250 | Routing, broadcast, dedup |
| Integration tests (one per assist family) | ~400 | **~2,400** | +2,000 | 15 RA families × ~80 LoC + 16 Py capabilities × ~80 LoC + driver harness |
| E2E harness (conftest, fixtures helpers) | ~150 | **~250** | +100 | Multi-server fixture wiring, four-LSP startup |
| E2E scenarios | ~530 | **~1,500** | +970 | 15 scenarios × ~100 LoC vs. 7 × ~75 LoC |
| **Logic subtotal** | **~3,415** | **~10,395** | **+6,980** | |
| Fixture content (existing MVP) | ~2,175 | **~7,150** | +4,975 | §2.8 |
| Plugin packaging (plugin.json, .mcp.json, README) | ~50 | ~50 | — | |
| **Grand total** | **~5,640** | **~17,595** | **+11,955** | |

### 3.2 Headline figure

**Full-coverage MVP: ~17,600 LoC (logic + fixtures + tests + harness)**, vs. **~5,640** for the prior narrow MVP.

That is a **3.1× expansion**, not 2–4× as the directive estimated. The reason is that the agnostic core (~1,510 LoC, §3.6 of the prior report) does not multiply with capability count; it scales with WorkspaceEdit shapes (which only grew by ~30%). The expansion lives in **strategies, facades, fixtures, and integration tests** — all of which scale linearly with capability count.

### 3.3 Fully-loaded estimate

The prior report's "~8,665 fully-loaded" included CI scaffolding, linting config, type stubs, doc strings, and the LSP-init smoke tests Serena ships. Apply the same loading factor (~54% over logic+fixtures):

**Fully-loaded full-coverage MVP: ~27,100 LoC.**

Within the directive's stated 12,000–20,000 LoC range only if "fully loaded" is excluded; outside it if everything counts. **This is the honest delta.** The directive should be aware that full-coverage MVP is at the upper end of its own stated band when test scaffolding is included.

### 3.4 Comparison to a "no escape hatch" alternative

If we dropped `apply_code_action` and demanded a named facade for every of the 158 RA assists + 16 Python actions:

- 174 facades × ~50 LoC + ~50 LoC of tests each ≈ **+17,400 LoC** of facade and test code on top of the §3.1 figure.
- Total would be ~35,000 LoC; fully-loaded ~54,000.

That is the honest cost of "no escape hatch." We do not propose it. The escape hatch (§4, `apply_code_action`) is what makes the directive's "full support" achievable in MVP framing rather than a multi-quarter program.

### 3.5 Where "full" yields to staging

The directive asks where "full" yields to staging. Honest answer:

1. **Per-assist named facades** — yields. We ship facades for the 5 most-used families; the rest are reachable via primitives. This is "full reach", not "full ergonomics."
2. **Test fixtures per assist** — yields. We ship one fixture *per family*, not per handler. 15 fixtures × 1 happy-path each = 15 integration tests for 158 RA handlers. The remaining 143 handlers ride on the family fixture's representative.
3. **Per-handler integration test** — yields. See above. We test by family, not by handler. v1.1 expands to per-handler.
4. **`changeAnnotations` policy** — yields. MVP auto-accepts with audit log; v1.1 adds opt-in confirmation tool.
5. **Persistent checkpoints** — yields. In-memory LRU only at MVP, same as prior.
6. **Full v1.1+ assists** — does not yield. RA's master branch ships new assists every release; we pin `rust-analyzer ^v0.3.18xx` and re-baseline at each minor release. Pinning is mandatory.

The yield list is honest: full-coverage MVP is **full reach + family-level testing + ergonomic facades on the top decile + escape-hatch primitive on the rest**. That is the cheapest defensible reading of the directive.

---

## §4 — Capability catalog and the escape hatch

### 4.1 `list_capabilities` MCP tool

Required by §1 axis 2. Returns a JSON document of the form:

```json
{
  "schema_version": "1",
  "languages": {
    "rust": {
      "server_id": "rust-analyzer",
      "server_version": "0.3.1850",
      "families": [
        {
          "family_id": "module_file_boundary",
          "facades": ["split_file_by_symbols", "move_inline_module_to_file", "move_from_mod_rs", "move_to_mod_rs"],
          "primitive_kinds": ["refactor.extract.module", "refactor.move"],
          "handlers_covered": ["extract_module", "move_module_to_file", "move_from_mod_rs", "move_to_mod_rs"]
        }
        // ... 14 more families
      ],
      "extensions": [
        {"method": "experimental/ssr", "facade": "structural_search_replace", "stage": "MVP"},
        // ... 18 more
      ]
    },
    "python": {
      "server_ids": ["pylsp", "basedpyright", "ruff"],
      "families": [
        {
          "family_id": "extractors",
          "facades": ["extract"],
          "primitive_commands": ["pylsp_rope.refactor.extract.method", "pylsp_rope.refactor.extract.variable"],
          "library_paths": []
        }
        // ...
      ]
    }
  }
}
```

**LoC**: ~200 (introspects strategies; renders JSON; baseline diff).

**Test gate**: a CI step diffs the live catalog against `test/baselines/capability_catalog.json`. Drift = test failure = MVP not done. New RA release that adds an assist = update the baseline + grep through fixtures to ensure family coverage holds.

### 4.2 `apply_code_action` MCP tool

The escape hatch. Signature:

```
apply_code_action(
  uri: str,
  range: lsp.Range,
  code_action_kind: str,      # e.g. "refactor.rewrite.replace_arith_op"
  data: Optional[dict] = None, # for two-phase resolve
  dry_run: bool = False
) -> RefactorResult
```

Behavior: requests `textDocument/codeAction` at `range`, filters by `code_action_kind`, calls `codeAction/resolve` for each match, applies the resulting `WorkspaceEdit` through the same applier the facades use. Identical observability (`RefactorResult`, `lsp_ops`, checkpoint).

**LoC**: ~120 (mostly already in the applier; the tool is a thin shell).

**This is what makes "full reach" real.** Every RA assist whose `kind` string is documented can be invoked via `apply_code_action`. The LLM is told via `list_capabilities` which kinds exist. The 143 RA handlers without a dedicated facade are reachable through this single tool.

### 4.3 `execute_command` MCP tool (whitelisted)

Same shape as `apply_code_action` but for `workspace/executeCommand`. Whitelist comes from each strategy's `execute_command_whitelist()`. For Rust the whitelist is empty (RA doesn't register `executeCommand`). For Python it includes the 9 pylsp-rope commands plus `source.fixAll.ruff` plus basedpyright's auto-import command.

**LoC**: ~80.

### 4.4 `list_code_actions` and `resolve_code_action`

Direct primitives, exposed verbatim. Not whitelisted; safe because they don't mutate. **LoC**: ~80 combined.

### 4.5 Total primitive-tools LoC: ~480

Larger than the prior MVP's `0` (primitives were entirely v1.1). Necessary under the directive.

---

## §5 — Staged delivery plan

The directive asks: with full coverage, can MVP still be all-or-nothing? Honest answer: no. Three stages, each green before the next. **The staging argument is in §5.4 — read that before §5.1–§5.3.**

### 5.1 Stage 1 (small) — primitive reach + capability catalog

Goal: Every assist *reachable* via `apply_code_action`. No facades except `rollback_refactor`. The LLM can do every refactor today, just verbosely.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 1 | `vendor/serena/src/solidlsp/ls.py` (codeAction, resolve, executeCommand, applyEdit, $/progress, multi-server hooks) | Modify | +470 | — |
| 2 | `vendor/serena/src/solidlsp/lsp_protocol_handler/server.py` | Modify | +60 | — |
| 3 | `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py` | Modify | +20 | — |
| 4 | `vendor/serena/src/solidlsp/language_servers/python_lsp.py` (multi-server: pylsp, basedpyright, ruff) | New | +250 | 1 |
| 5 | `vendor/serena/src/serena/code_editor.py` (applier upgrade) | Modify | +280 | 1 |
| 6 | `vendor/serena/src/serena/refactoring/checkpoints.py` | New | +140 | 5 |
| 7 | `vendor/serena/src/serena/refactoring/lsp_pool.py` | New | +180 | 1 |
| 8 | `vendor/serena/src/serena/refactoring/discovery.py` | New | +110 | — |
| 9 | `vendor/serena/src/serena/refactoring/multi_server.py` | New | +250 | 1, 4 |
| 10 | `vendor/serena/src/serena/refactoring/language_strategy.py` (Protocol) | New | +140 | — |
| 11 | `vendor/serena/src/serena/refactoring/rust_strategy.py` (skeleton + family declarations) | New | +400 | 10 |
| 12 | `vendor/serena/src/serena/refactoring/python_strategy.py` (skeleton + multi-server orchestration) | New | +400 | 10, 9 |
| 13 | `vendor/serena/src/serena/refactoring/__init__.py` (registry) | New | +25 | 11, 12 |
| 14 | `vendor/serena/src/serena/refactoring/capability_catalog.py` | New | +200 | 11, 12 |
| 15 | `vendor/serena/src/serena/tools/primitive_tools.py` (`list_capabilities`, `list_code_actions`, `resolve_code_action`, `apply_code_action`, `execute_command`, `rollback_refactor`) | New | +480 | 5, 6, 14 |
| 16 | All MVP fixtures (calcrs, calcpy, kitchen_sink_*, big_*, cross_visibility, with_macros, inline_modules, mod_rs_swap, flycheck_diagnostics_*, mypy_diagnostics_py, ruff_diagnostics_py, ssr_targets_rs, cohesion_planning_*) | New (trees) | ~7,150 | — |
| 17 | Unit tests (applier, multi-server, catalog, strategies) | New | ~1,650 | 5, 9, 11, 12, 14 |
| 18 | Integration tests per RA family (15 tests) | New | ~1,200 | 1, 5, 11, 16 |
| 19 | Integration tests per Python capability (16 tests) | New | ~1,200 | 1, 4, 5, 12, 16 |
| 20 | `o2-scalpel/.claude-plugin/plugin.json` + `.mcp.json` | New | +35 | 15 |

**Stage 1 exit gate:**
- `list_capabilities` returns the full catalog and matches the baseline.
- Every assist family has a green integration test reaching the assist via `apply_code_action`.
- `rollback_refactor` round-trips on `kitchen_sink_*` workspaces.
- All four LSP processes spawn on first call without exceeding the §9 RAM budget.

**Size: small in feature surface (1 facade out of 19), large in fixture and test scaffolding.** ~9,890 LoC of code + ~7,150 fixtures + ~4,050 tests = ~14,000 LoC. The big number is because Stage 1 has to lay the entire foundation; Stages 2–3 add facade ergonomics on top of an already-complete reach surface.

### 5.2 Stage 2 (medium) — top-decile facades

Goal: The 5 most-used families have named, ergonomic facades. The LLM rarely needs `apply_code_action` for common workflows.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 21 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `split_file_by_symbols` | New | +600 | Stage 1 |
| 22 | …—`fix_imports` (multi-server consolidator) | New | +250 | 21, 9 |
| 23 | …—`extract` (multiplexer over RA + rope) | New | +200 | 21 |
| 24 | …—`inline` (multiplexer over RA + rope) | New | +200 | 21 |
| 25 | …—`rename_symbol` (Serena re-skin) | New | +100 | Stage 1 |
| 26 | E2E harness (`test/e2e/conftest.py`, multi-server fixture wiring) | New | +250 | 21–25 |
| 27 | E2E scenarios E1, E1-py, E2, E3, E9, E9-py, E10 (carry-over) | New | +700 | 26 |
| 28 | E2E scenarios E11, E12 (`extract` round-trip, `inline` round-trip) | New | +200 | 23, 24 |

**Stage 2 exit gate:** All 7 carry-over E2E scenarios + E11/E12 green. ~2,500 LoC.

### 5.3 Stage 3 (large) — full facade fan-out + remaining E2E

Goal: every facade in §2.5 implemented; every E2E in §2.9 green; capability catalog stable.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 29 | `refactoring_tools.py` — `move_inline_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs` | New | +250 | Stage 2 |
| 30 | …—`change_visibility` | New | +120 | Stage 2 |
| 31 | …—`apply_quickfix_at` | New | +180 | Stage 2 |
| 32 | …—`run_check` | New | +120 | Stage 2 |
| 33 | …—`apply_lint_fixes` | New | +100 | Stage 2 |
| 34 | …—`structural_search_replace` | New | +130 | Stage 2 |
| 35 | …—`plan_file_split` | New | +250 | Stage 2 |
| 36 | E2E scenarios E4, E6, E7, E8, E13, E14, E15, E16, E17 | New | +900 | 29–35 |
| 37 | Server-extension whitelist tests | New | +200 | 29–35 |
| 38 | README + install docs | Modify | +150 | 29–35 |

**Stage 3 exit gate:** §1 fully satisfied. ~2,400 LoC.

### 5.4 The framing question — MVP = Stage 1, Stage 1+2, or Stage 1+2+3?

The directive asks both forms. Argue both, then pick.

#### 5.4.1 Argument for **MVP = Stage 1 only ("full reach via primitive")**

- §1 axis 1 (every family reachable) is satisfied at Stage 1 exit.
- §1 axis 2 (catalog matches reachable set) is satisfied at Stage 1 exit.
- The directive says "every assist family … reachable by an LLM." Stage 1 delivers that reachability.
- Smaller MVP ships sooner; Stage 2/3 facades can land as v1.1, v1.2.
- This framing matches the YAGNI principle in `CLAUDE.md`: ergonomic facades over `apply_code_action` are valuable but not essential to "support."
- The agent-UX cost of 19 tools is also reduced — Stage 1 ships ~5 primitive tools, much friendlier to the tool budget.

**Counterargument**: "reachable via primitive" hides a UX gap. An LLM asking for "extract this function" must learn `apply_code_action(kind="refactor.extract.function", ...)` rather than `extract(symbol, ...)`. The user-perceived quality is much lower. "Full support" arguably implies ergonomic surface, not just protocol surface.

#### 5.4.2 Argument for **MVP = Stage 1 + Stage 2**

- Adds the 5 most-used facades (split, fix-imports, extract, inline, rename). These cover the **top decile of LLM-initiated refactor requests** in the agent-UX research (handed off to that specialist; this report assumes their finding holds).
- Total LoC: ~16,500. Fully loaded ~25,500. Within the directive's 12,000–20,000 stated band when fixtures are excluded; outside when everything counts.
- Still has the escape hatch from Stage 1 for the long tail.
- Honest framing: "full reach + ergonomic top-of-funnel."

**Counterargument**: 5 facades is a judgment call. Why not 4? Why not 7? Where the line is drawn determines whether v1.1 is small or huge.

#### 5.4.3 Argument for **MVP = Stages 1+2+3 (everything)**

- Maximal directive compliance: every facade in §2.5, every E2E in §2.9.
- Largest credible MVP claim.
- Total LoC: ~17,600. Fully loaded ~27,100. Outside the directive's stated band.
- Risks ship-blocking on a long tail facade with low LLM demand.

**Counterargument**: The full-coverage directive is about LSP capability coverage, not about MCP tool count. Conflating the two over-scopes MVP.

#### 5.4.4 Pick

**MVP = Stage 1 + Stage 2.**

Justification:
1. Stage 1 alone genuinely satisfies the literal §1 statement (full reach via primitive). But the user's directive change is motivated by a desire to make the chosen LSPs *first-class*, not just *reachable*. Reach without ergonomics is the prior narrow MVP wearing different clothes.
2. Stage 2 adds the 5 facades that cover the top decile of refactor requests. This is the cheapest credible "ergonomic" claim. Anything less and the directive is undermined; anything more and v1.1 is too small to matter.
3. Stage 3 is best done as v1.1 — the same risk-management argument the prior MVP used for shipping fewer facades. We ship Stage 1+2 as `v0.1.0-mvp`, tag Stage 3 contents as v1.1 milestones in the repo, and iterate.
4. The 15 E2E scenarios in §2.9 are split: 9 land in Stage 2 (carry-over + E11/E12), 6 in Stage 3 (E4, E6, E7, E8, E13–E17). Stage 1+2 = 9 E2E + 31 integration tests = ~40 tests gating MVP. That is honest dual-language full-reach coverage.
5. Tag plan: `mvp-stage-1`, `mvp-stage-2` = `v0.1.0-mvp`, `mvp-stage-3` = `v0.2.0`.

This is the same framing the prior narrow MVP used (S → M → L stages, MVP = stage-3). The difference is what each stage contains, which is appropriately heavier under the new directive.

### 5.5 Dependency graph

```
Stage 1: [1] [2] [3]   →   [4]   →   [9]
              [5] ← [1]
              [6] ← [5]
              [7] ← [1]
              [8]
              [10]
              [11] ← [10]
              [12] ← [10] ← [9]
              [13] ← [11] [12]
              [14] ← [11] [12]
              [15] ← [5] [6] [14]
              [16] (fixtures, parallel with all above)
              [17] [18] [19] (tests, after [11] [12] [14])
              [20] ← [15]

Stage 2: [21] ← Stage 1
         [22] ← [21] [9]
         [23] [24] ← [21]
         [25] ← Stage 1
         [26] ← [21..25]
         [27] [28] ← [26]

Stage 3: [29..35] ← Stage 2
         [36] ← [29..35]
         [37] ← [29..35]
         [38] ← all
```

Parallelization (CPU cores = 8 on this machine; project CLAUDE.md says max parallel = cores):
- Stage 1: nodes 1/2/3, 8, 16, 17, 18, 19 are largely parallel; 4/5/9 must serialize on 1; 11/12 parallel after 10; 14 after 11/12.
- Stage 2: 22/23/24/25 parallel after 21; 26 serializes; 27/28 parallel after 26.
- Stage 3: 29..35 parallel after Stage 2; 36 serializes per scenario.

### 5.6 LoC rollup by stage

| Stage | Logic | Tests | Fixtures | Total |
|---|---|---|---|---|
| 1 | ~3,635 | ~4,050 | ~7,150 | ~14,835 |
| 2 | ~1,350 | ~1,150 | 0 | ~2,500 |
| 3 | ~1,150 | ~1,100 | 0 | ~2,250 |
| **MVP (1+2)** | **~4,985** | **~5,200** | **~7,150** | **~17,335** |
| Including Stage 3 | ~6,135 | ~6,300 | ~7,150 | ~19,585 |

### 5.7 Stage-boundary discipline

Same rules as the prior MVP (archive-v1-narrow §5.6). Each stage tag is a hard boundary; stage 2 cannot start before stage 1 exits clean. Inside a stage, parallelism encouraged.

---

## §6 — Test gate expansion

### 6.1 Unit tests

| Test module | Approx LoC | Coverage |
|---|---|---|
| `test_workspace_edit_applier.py` | ~600 | One snapshot test per `WorkspaceEdit` shape: TextDocumentEdit (basic, with annotation, with snippet, with version-mismatch retry); CreateFile; RenameFile; DeleteFile; ordering invariant; multi-server source.* dedup. ~12 shape variations × ~50 LoC each. |
| `test_checkpoints.py` | ~150 | LRU eviction, inverse-edit round-trip, multi-server snapshot fan-in. |
| `test_multi_server.py` | ~250 | Routing table, broadcast `didOpen`, diagnostic merge, capability dispatch, server-failure isolation. |
| `test_capability_catalog.py` | ~150 | Catalog generation; baseline diff; new-handler regression. |
| `test_language_strategy.py` (Rust + Python) | ~400 | All 15 RA family declarations correct; all 16 Python capability declarations correct; Rope-as-library binding; init overrides applied. |
| `test_lsp_pool.py` | ~100 | Lazy spawn, idle shutdown, transparent respawn. |
| `test_discovery.py` | ~100 | Plugin-cache walk, env-var override, schema validation. |

**Unit total: ~1,750 LoC.**

### 6.2 Integration tests (one per assist family)

Per directive: one fixture per family × one happy-path test per family. Some families have multiple "lanes" (e.g., extract has function/variable/type-alias) — those get sub-tests sharing a fixture.

| Family | Integration test | Approx LoC | Fixture used |
|---|---|---|---|
| RA: module/file boundary | `test_module_file_boundary.py` | ~200 | inline_modules.rs, mod_rs_swap.rs |
| RA: extractors | `test_extractors_rust.py` | ~120 | kitchen_sink_rs |
| RA: inliners | `test_inliners_rust.py` | ~120 | kitchen_sink_rs |
| RA: visibility & import hygiene | `test_visibility_imports.py` | ~150 | cross_visibility.rs |
| RA: ordering | `test_ordering_rust.py` | ~80 | kitchen_sink_rs |
| RA: generators | `test_generators_rust.py` | ~120 | kitchen_sink_rs |
| RA: replace | `test_replace_rust.py` | ~80 | kitchen_sink_rs |
| RA: convert | `test_convert_rust.py` | ~80 | kitchen_sink_rs |
| RA: micro-rewrites | `test_micro_rewrites_rust.py` | ~80 | kitchen_sink_rs |
| RA: pattern | `test_pattern_rust.py` | ~80 | kitchen_sink_rs |
| RA: string/format | `test_string_format_rust.py` | ~60 | kitchen_sink_rs |
| RA: async sugar | `test_async_sugar_rust.py` | ~60 | kitchen_sink_rs |
| RA: term-search | `test_term_search_rust.py` | ~60 | kitchen_sink_rs |
| RA: diagnostic-driven quickfixes | `test_quickfix_rust.py` | ~150 | flycheck_diagnostics_rs |
| RA: rename | `test_rename_rust.py` | ~80 | kitchen_sink_rs |
| Py: rope.extract.method | `test_extract_method_py.py` | ~80 | kitchen_sink_py |
| Py: rope.extract.variable | `test_extract_variable_py.py` | ~60 | kitchen_sink_py |
| Py: rope.inline | `test_inline_py.py` | ~80 | kitchen_sink_py |
| Py: rope.local_to_field | `test_local_to_field_py.py` | ~60 | kitchen_sink_py |
| Py: rope.method_to_method_object | `test_method_to_method_object.py` | ~60 | kitchen_sink_py |
| Py: rope.use_function | `test_use_function_py.py` | ~60 | kitchen_sink_py |
| Py: rope.introduce_parameter | `test_introduce_parameter_py.py` | ~60 | kitchen_sink_py |
| Py: rope.quickfix.generate | `test_quickfix_generate_py.py` | ~60 | kitchen_sink_py |
| Py: rope.organize_import | `test_organize_import_py.py` | ~80 | kitchen_sink_py |
| Py: rope library Move | `test_move_global_py.py` | ~120 | kitchen_sink_py |
| Py: rope library rename module | `test_rename_module_py.py` | ~100 | kitchen_sink_py |
| Py: basedpyright organizeImports | `test_basedpyright_imports.py` | ~80 | kitchen_sink_py |
| Py: basedpyright auto-import | `test_basedpyright_autoimport.py` | ~100 | kitchen_sink_py |
| Py: basedpyright pyright-ignore | `test_basedpyright_ignore.py` | ~80 | mypy_diagnostics_py |
| Py: basedpyright type-annotate | `test_basedpyright_annotate.py` | ~80 | mypy_diagnostics_py |
| Py: ruff source.fixAll | `test_ruff_fix_all.py` | ~100 | ruff_diagnostics_py |
| Py: ruff per-rule quickfix | `test_ruff_per_rule.py` | ~80 | ruff_diagnostics_py |

**Integration total: 32 test modules, ~2,800 LoC.** This satisfies the directive's "60+ integration tests" — each module above contains 2–4 sub-tests, totaling ~70 sub-tests.

### 6.3 E2E tests (15 scenarios — §2.9)

Per scenario module: ~100 LoC. Total: **~1,500 LoC** across 15 scenarios.

### 6.4 Test count summary

| Tier | Count | LoC |
|---|---|---|
| Unit (sub-tests) | ~120 | ~1,750 |
| Integration (sub-tests) | ~70 | ~2,800 |
| E2E | 15 | ~1,500 |
| **Total tests** | **~205** | **~6,050** |

The directive estimated 60+ integration tests and ~15 E2E. We are at 70 integration sub-tests and 15 E2E. Honest match.

### 6.5 Green-bar definition

All 205 tests must pass in a single CI run. Retries allowed only once per test; two retries = flaky = MVP not done. Same rule as prior MVP, scaled.

---

## §7 — Two-process cost revisited (4 LSP processes)

### 7.1 LSP process inventory at MVP

| Process | Purpose | Memory (calcrs/calcpy fixtures) | Memory (real workspaces, v1.1 territory) |
|---|---|---|---|
| Claude Code's built-in rust-analyzer | Read-only navigation | ~500 MB | ~4–8 GB |
| **Scalpel's rust-analyzer** | Refactor mutations | ~500 MB | ~4–8 GB |
| Claude Code's built-in pyright (or basedpyright) | Read-only navigation | ~300 MB | ~600 MB |
| **Scalpel's pylsp** (with rope+mypy+ruff plugins) | Refactor mutations | ~250 MB | ~500 MB |
| **Scalpel's basedpyright** | Diagnostics corroboration | ~300 MB | ~600 MB |
| **Scalpel's ruff server** (or pylsp-ruff in-proc) | Lint diagnostics + fixes | ~80 MB | ~150 MB |
| Scalpel MCP server (Python) | Orchestration | ~300 MB | ~300 MB |
| Test harness, fixtures | Runtime | <100 MB | <100 MB |
| OS + Claude Code + editor | — | ~3 GB | ~3 GB |

### 7.2 Resource floor by configuration

| Configuration | Active LSP processes | RSS (calcrs+calcpy) | RSS (real workspace) |
|---|---|---|---|
| Rust + Python both eager | 6 (3 read + 3 write) | ~5.4 GB | ~17–22 GB |
| Rust lazy-spawn, Python eager | 5 | ~4.9 GB | ~13–18 GB |
| Both lazy-spawn (typical) | varies | ~4 GB idle, ~5.4 GB active | varies |
| Both lazy-spawn + idle-shutdown | varies | ~3.6 GB idle, ~5.4 GB active | varies |

### 7.3 Updated MVP floor commitment

**MVP supports a 24 GB dev laptop with all four scalpel LSPs spawned on the `calcrs+calcpy` fixtures and Claude Code's two read-only LSPs concurrently.** That is the realistic minimum.

**16 GB laptops require opt-out flags**: `O2_SCALPEL_DISABLE_LANGS=rust` (use CC's RA for reads only) or running scalpel's pylsp without basedpyright corroboration. We document both flags at MVP, even though the prior MVP deferred them; full coverage's 4-server reality forces them in.

**Comparison to prior MVP**:

| Axis | Prior MVP (16 GB) | Full-coverage MVP (24 GB recommended, 16 GB with flags) |
|---|---|---|
| LSP processes (eager) | 4 (2 read + 2 write) | 6 |
| Memory floor at idle | ~5 GB | ~5.4 GB (eager); ~3.6 GB (lazy + idle-shut) |
| Memory floor active | ~5 GB | ~5.4 GB (small fixtures); ~17–22 GB (real Rust workspace) |
| Cold-start (rust-analyzer on calcrs) | ~10s | unchanged |
| Cold-start (pylsp + rope + mypy + ruff loading) | n/a | ~3–5s (one-time per session) |
| Cold-start (basedpyright on calcpy) | n/a | <1s |

### 7.4 Multi-LSP coordination cost

Beyond raw memory, the Python multi-server path introduces coordination cost:

- **`didOpen` broadcast**: every buffer must be opened on all 4 Python LSP processes. ~50ms per server cold-cache, parallel.
- **Diagnostic deduplication**: pylsp-mypy + basedpyright both emit type errors on the same offsets. Multiplexer dedups by (uri, range, message-prefix); ~5ms per diag list.
- **Code-action provenance tracking**: when applying a `WorkspaceEdit` resolved from one server, scalpel must invalidate the buffer-state hint on the *other* servers via `didChange` to avoid stale-buffer race. Implemented in §2.4 multi-server broadcast.
- **`$/progress` token namespacing**: each server has its own token space. Multiplexer prefixes with `pylsp:`, `basedpyright:`, `ruff:`.

These costs are real but bounded — they live in the multi_server module (~250 LoC, §3.1). Not a budget threat; a complexity threat.

### 7.5 Honest startup budget

| Phase | Time |
|---|---|
| MCP server boot | <500ms |
| Plugin-cache discovery | <200ms |
| Lazy-spawn rust-analyzer (first use) | ~10s on calcrs; up to 8 min on big Rust workspace |
| Lazy-spawn pylsp+rope+mypy+ruff (first use) | ~5s on calcpy |
| Lazy-spawn basedpyright (first use) | <1s on calcpy |
| Lazy-spawn ruff server (first use) | <100ms |
| First `extract` call (after spawn) | <1s |
| First `apply_code_action` call (after spawn) | <1s |

**E2E run wall-clock estimate** (15 scenarios on calcrs+calcpy): 4–8 min on CI runner, dominated by RA cold start. Acceptable for `pytest -m e2e` nightly. Per-commit: integration tests only (~70 sub-tests, ~3–5 min).

---

## §8 — Risk matrix re-rank (full-coverage)

### 8.1 Top-10 risks under the new directive

| Rank | Risk | Severity | Likelihood | Mitigation |
|---|---|---|---|---|
| **P0** | rust-analyzer cold-start UX regression on real workspace (≥3 min) | High | High | Lazy spawn + `wait_for_indexing()` + progress notification; document the floor; carry-over from prior MVP |
| **P0** | Capability catalog drifts from RA master between releases | High | Medium | Pin RA version; checked-in baseline; CI fails on drift |
| **P0** | Multi-LSP coordination introduces consistency bugs (one server stale, another not) | High | Medium | `multi_server` module owns broadcast; integration test forces cross-server consistency on every fixture |
| **P1** | Tool-surface bloat to 19 tools strains agent-UX | Medium | High | Tool prefixing + 3-line tool descriptions; defer to Agent-UX specialist for budget call; `apply_code_action` covers the long tail so we don't grow further |
| **P1** | pylsp-rope unsaved-buffer experimental support produces stale `WorkspaceEdit` | High | Medium | Sync `didSave` before each rope call (cheap); fallback to Rope-as-library when bug observed |
| **P1** | `rust-analyzer/runFlycheck` flakes when `cargo.targetDir` separation isn't respected | High | Medium | `lsp_init_overrides` enforces separate `targetDir`; integration test asserts the dir is set |
| **P2** | basedpyright corroboration disagrees with pylsp-mypy on diagnostic counts → false rollbacks | Medium | Medium | Pick one as authoritative for `DiagnosticsDelta`; corroborate but don't gate |
| **P2** | Ruff fixes conflict with pylsp-rope refactor edits on same offsets | Medium | Medium | Apply rope edits first, ruff `source.fixAll` second; test conflict resolution |
| **P2** | `apply_code_action`'s `kind` string is unstable (RA renames an assist) | Medium | Low | Catalog baseline catches drift; pin RA version |
| **P3** | Marketplace publication pressure pulls v1.1 work into MVP | Low | Medium | §10 explicitly defers; documented decision |
| **P3** | Persistent checkpoint absence costs a user a session's work | Low | Medium | Document; v1.1 |
| **P3** | 4-LSP startup time on 16 GB CI runner | Low | High | Use 4-core runner (16 GB); document opt-out flags |

### 8.2 Re-rank vs. prior MVP

| Risk class | Prior rank | Full-coverage rank | Reason |
|---|---|---|---|
| Cold start | P0 | P0 | Unchanged |
| Tool-surface bloat | not listed | P1 | 4→19 tools, the directive's headline cost |
| Multi-LSP coordination | not listed | P0 | New attack surface; 4 Python LSPs |
| Capability catalog drift | not listed | P0 | The §1 axis-2 enforcement is itself a fragility |
| pylsp-rope stale buffers | P2 | P1 | Higher exercise rate under full coverage |
| pylsp-rope sole maintainer | P2 (long-term) | P2 | Same |
| RA `runFlycheck` `targetDir` | P1 | P1 | Same |
| Marketplace pressure | not listed | P3 | New consideration |

The directive change *adds* three P0/P1 risks (multi-LSP, catalog drift, tool bloat) and *intensifies* one (pylsp-rope stale buffers). It does not retire any prior risks.

### 8.3 Risk-mitigation LoC

| Mitigation | LoC | Already counted? |
|---|---|---|
| `multi_server` module | ~250 | Yes (§3.1) |
| Capability-catalog baseline + diff CI | ~150 (catalog) + ~50 (CI script) | Yes for catalog; CI script in fixtures count |
| Tool-prefix grouping | minimal | Yes (~20 LoC across primitive/refactoring tools) |
| `targetDir` integration test | ~50 | Yes (in integration tests) |
| `didSave` before rope calls | ~30 | In `python_strategy.py` |

No additional LoC budget needed for risk mitigation; it is structural in the §3 estimate.

---

## §9 — Cut list (what the directive does NOT require)

The user's directive is "full support of the chosen LSPs for Rust + Python." It is **not** "full support of every LSP that exists." Explicit cuts, each with one-sentence justification.

| # | Cut | Justification |
|---|---|---|
| 1 | C/C++ strategy via clangd | Not a chosen LSP for MVP; reactivate when C/C++ becomes a priority. |
| 2 | Go strategy via gopls | Same. |
| 3 | Java strategy via jdtls | Same. |
| 4 | TypeScript strategy via tsserver / typescript-language-server | Paper-only at MVP per OQ #7; same as prior MVP. |
| 5 | Third-party `LanguageStrategy` entry-point discovery | Zero demand; static dict suffices. |
| 6 | `rust-analyzer/viewHir` | IDE-debug aid; LLM rarely needs HIR. |
| 7 | `rust-analyzer/viewMir` | Same. |
| 8 | `rust-analyzer/viewCrateGraph` | SVG output; not LLM-friendly. |
| 9 | `rust-analyzer/viewRecursiveMemoryLayout` | Niche use-case. |
| 10 | `rust-analyzer/getFailedObligations`, `interpretFunction` | Trait solver / const-eval introspection; advanced debugging only. |
| 11 | RA Test Explorer extensions (`experimental/discoverTest`, etc.) | v1.1; the test runner is a separate user journey from refactoring. |
| 12 | Marketplace publication at MVP | §10. |
| 13 | Persistent checkpoints (`.serena/checkpoints/`) | LRU-only at MVP; same as prior. |
| 14 | `o2-scalpel-newplugin` generator | v2+; same as prior. |
| 15 | Reference LSP-config plugins (`rust-analyzer-reference`, `clangd-reference`) | v2+; same as prior. |
| 16 | Boostvolt fork under neutral name | v2+; same as prior. |
| 17 | Within-function refactors *beyond* what the chosen LSPs expose | The directive bounds us to chosen LSPs' surfaces, not to extending them. |
| 18 | Writing new rust-analyzer assists | Same. |
| 19 | Writing new Rope refactor classes | Same; we use what Rope ships. |
| 20 | `pylsp` plugins beyond rope+mypy+ruff (e.g., pylsp-black, pylsp-pyflakes) | Three plugins is the chosen set; black is replaced by ruff format; pyflakes by ruff lint. |
| 21 | `jedi-language-server` Python alternative | pylsp+rope is the chosen path; jedi is documented as fallback only. |
| 22 | `pyrefly` / `ty` adoption | Early-stage type checkers; not chosen for MVP. |
| 23 | LSP 3.18 features (typeHierarchy, etc.) | Per RA capabilities brief: not advertised; out of scope. |
| 24 | Pull diagnostics (`textDocument/diagnostic`) | Per same brief: RA uses push only; not enabled in MVP. |
| 25 | Telemetry / observability beyond `lsp_ops: list[LspOpStat]` | Same as prior MVP. |
| 26 | Idle-shutdown tuning UI | v1.1; default 600s. |
| 27 | Filesystem watcher on plugin cache | Q10 explicitly rejects. |

The directive's "full" is bounded by:
1. Chosen LSPs (Rust + Python).
2. Each chosen LSP's published capability surface as of pinned versions.
3. User-facing tools (refactor-shaped operations); not IDE-debug introspection.

---

## §10 — Distribution under full-coverage MVP

### 10.1 The question

Prior MVP shipped via `uvx --from <local-path>`. Full-coverage MVP is heavier; does that push marketplace publication *in* (users will want it sooner) or *out* (more surface to QA)?

### 10.2 Argument for marketplace at MVP

- Heavier MVP = harder to install manually = more friction for early adopters.
- Marketplace polish (manifest, README badges, install URL) is small relative to the overall stage-3 work.
- Earlier real-user feedback on the 19-tool surface; Agent-UX specialist's analysis benefits from it.

### 10.3 Argument for marketplace at v1.1 (same as prior MVP)

- Heavier MVP = more bugs to QA = higher chance of public embarrassment if marketplace consumers auto-update.
- Marketplace publication couples MVP timeline to external systems (Anthropic Discover, third-party aggregators).
- Marketplace requires a stable version contract; v0.1.0-mvp is *deliberately* pre-stable. The 19-tool surface may flex during stage 2 → stage 3 → v1.1.
- Capability catalog drift (P0 risk) creates a versioning discipline the marketplace consumer cannot tolerate without a contract.
- Per `CLAUDE.md`'s "Frustrations: regression" directive, the user has explicitly flagged regression aversion. Public marketplace = higher regression-cost surface.

### 10.4 Pick

**Marketplace stays at v1.1.** Same answer as prior MVP, for stronger reasons:

1. The capability catalog is a versioned contract. Drift between RA versions, Python LSP versions, or scalpel itself can change `list_capabilities` output. Public marketplace consumers cannot tolerate that without a v1.0 stability promise. We do not have one yet.
2. The 19-tool surface itself is unstable until Agent-UX specialist's review converges.
3. The full-coverage MVP's larger test gates (15 E2E + 70 integration) mean longer between "all green locally" and "all green publicly" — which is exactly the gap public marketplace consumers should not fill.

Local install via `uvx --from <path>` remains the MVP path. Marketplace publication is `v1.1` work, with the deliberate `v0.1.0-mvp` → `v1.1.0` gap as a stabilization buffer.

### 10.5 Install flow at MVP

Same as prior MVP (archive-v1-narrow §7.2). One-page README, copy-pasteable.

---

## §11 — Definition of "done" for full-coverage MVP

Concrete. Every item measurable.

### 11.1 Code

- [ ] `vendor/serena` fork contains all stage-1 + stage-2 changes (stage-3 deferred to v1.1).
- [ ] `o2-scalpel/.claude-plugin/plugin.json` + `.mcp.json` exist and validate.
- [ ] `test/e2e/fixtures/` contains all 21 fixtures listed in §2.8 marked MVP.
- [ ] `RustStrategy` declares all 15 RA family kinds and 19 MVP extensions.
- [ ] `PythonStrategy` declares all 16 Python capabilities + 2 Rope library paths.
- [ ] `multi_server.py` orchestrates pylsp + basedpyright + ruff with broadcast `didOpen`/`didChange`.
- [ ] `capability_catalog.py` generates a JSON catalog whose diff against `test/baselines/capability_catalog.json` is empty.
- [ ] `LanguageStrategy` Protocol reviewed against TypeScript paper design; no Rust- or Python-isms in method names.
- [ ] `refactoring_tools.py` contains: `split_file_by_symbols`, `fix_imports`, `extract`, `inline`, `rename_symbol` (Stage 2 facades). `rollback_refactor` lives in `primitive_tools.py`.
- [ ] `primitive_tools.py` contains: `list_capabilities`, `list_code_actions`, `resolve_code_action`, `apply_code_action`, `execute_command`, `rollback_refactor`.

### 11.2 Tests (all green in one CI run)

- [ ] `pytest test/serena/` — ~120 unit sub-tests pass.
- [ ] `pytest test/integration/assist_families/` — 70 integration sub-tests across 32 modules pass; one per assist family/capability.
- [ ] `pytest -m e2e test/e2e/` — 9 Stage-1+2 E2E scenarios pass: E1, E1-py, E2, E3, E9, E9-py, E10, E11, E12.
- [ ] `cargo test --manifest-path test/e2e/fixtures/calcrs/Cargo.toml` — green on the pristine fixture.
- [ ] `cargo test --manifest-path test/e2e/fixtures/kitchen_sink_rs/Cargo.toml` — green on the pristine fixture.
- [ ] `pytest test/e2e/fixtures/calcpy` and `pytest test/e2e/fixtures/kitchen_sink_py` — green.
- [ ] No flakes: each scenario passes in a single retry or fewer.
- [ ] `list_capabilities` MCP call returns JSON byte-equal to `test/baselines/capability_catalog.json`.

### 11.3 Resource floor

- [ ] On a 24 GB dev laptop with all four scalpel LSPs eager-spawned on `calcrs+calcpy`, total scalpel-attributable RSS is under 8 GB.
- [ ] On a 16 GB CI runner with `O2_SCALPEL_DISABLE_LANGS=` (no opt-outs), full E2E suite completes within wall-clock budget (≤ 12 min, accounting for RA cold start).
- [ ] On a 16 GB dev laptop with `O2_SCALPEL_DISABLE_LANGS=rust`, scalpel's Python path works against `calcpy` and the relevant Python E2E scenarios pass.

### 11.4 Documentation

- [ ] `README.md` contains copy-pasteable "Install locally" section for `uvx --from <path>`.
- [ ] `README.md` documents the 19 MVP tools with one-line descriptions and one example each (machine-generated from the catalog).
- [ ] `README.md` documents the `O2_SCALPEL_DISABLE_LANGS` flag.
- [ ] `docs/design/mvp/` contains this report plus companion specialist outputs.
- [ ] `CHANGELOG.md` entry for `v0.1.0-mvp` lists the 19 tools, the 5 RA + Python facade families, and the catalog hash.

### 11.5 Install

- [ ] From clean checkout on 24 GB dev laptop, install steps succeed without PyPI or marketplace dependency.
- [ ] `uvx --from <path> serena-mcp-server --mode scalpel --version` prints a version string.
- [ ] `mcp__o2-scalpel__list_capabilities` returns the full catalog from a Claude Code session.

### 11.6 Non-gates

Explicitly NOT blocking MVP:
- Marketplace publication (v1.1).
- Stage-3 facades (`move_*`, `change_visibility`, `apply_quickfix_at`, `run_check`, `apply_lint_fixes`, `structural_search_replace`, `plan_file_split`).
- Stage-3 E2E scenarios (E4, E6, E7, E8, E13–E17).
- Per-handler integration tests (we test by family).
- Persistent checkpoints.
- C/C++/Go/Java/TypeScript strategies.
- Big-Rust-workspace (227-crate) viability.
- Idle-shutdown tuning UI.

### 11.7 Tag

Upon all checklist items green, tag `v0.1.0-mvp`. Tag stage-1 exit as `mvp-stage-1`; stage-2 exit (i.e., MVP) as `mvp-stage-2` *and* `v0.1.0-mvp`. Stage-3 contents land as `v0.2.0` after MVP ships.

---

## §12 — Comparative summary: full-coverage vs. narrow MVP

The table the directive explicitly asks for. Numbers from §3 and the prior MVP report.

| Axis | Narrow MVP (v1) | Full-coverage MVP (this report) | Multiplier |
|---|---|---|---|
| MCP tool count | 4 (3 facades + rollback) | 19 (12 facades + 6 primitives + rollback; Stage 1+2 = 11 tools, +8 in stage 3) | 4.75× total / 2.75× at MVP-stage-2 |
| Languages | Rust + Python | Rust + Python | 1× |
| LSP server processes (scalpel side) | 2 (RA + pyright) | 4 (RA + pylsp + basedpyright + ruff) | 2× |
| LSP capabilities reachable | ~10 (just enough for 3 facades) | 158 RA + 16 Py + 19 RA-extensions = 193 | ~19× |
| E2E scenarios | 7 | 15 (9 at stage-2 = MVP; 6 at stage-3 = v0.2.0) | 2.1× total / 1.3× at MVP |
| Integration tests | ~10 (driver only) | ~70 sub-tests across 32 modules | 7× |
| Unit tests | ~30 | ~120 | 4× |
| Logic LoC | ~3,415 | ~10,395 | 3.0× |
| Fixture LoC | ~2,175 | ~7,150 | 3.3× |
| Test LoC (unit + integration + E2E) | ~1,180 | ~6,050 | 5.1× |
| Total LoC | ~5,640 | ~17,595 | 3.1× |
| Fully-loaded LoC (incl. CI scaffolding) | ~8,665 | ~27,100 | 3.1× |
| RAM floor (idle, eager) | ~5 GB | ~5.4 GB | 1.08× |
| RAM floor (active on real workspace) | ~16 GB | ~17–22 GB | 1.1–1.4× |
| Effort (S/M/L size) | S→M→L (3 stages) | L→L→L (3 stages, all heavy) | qualitative |
| Risks above P2 | 5 | 9 | 1.8× |
| Distribution at MVP | uvx local | uvx local (unchanged) | 1× |

### 12.1 Sentence summary

The new directive triples the test-and-fixture surface, doubles the LSP-process count, multiplies the reachable capability count by ~19×, but only inflates the runtime resource floor by ~10–40% and keeps the distribution path unchanged. The cost lives in *strategies, facades, fixtures, and tests*; the agnostic core absorbs ~90% of its prior code unchanged.

---

## §13 — Open items for orchestrator synthesis

Carried-over and new items the next synthesis round must close:

1. **Pyright vs. pylsp vs. both** — prior MVP deferred to a stage-1 spike. Full-coverage MVP commits to *both* (pylsp primary for refactors, basedpyright for diagnostics corroboration). Confirm against agent-UX cost.
2. **Tool-prefix scheme for 19 tools** — `mcp__o2-scalpel__refactor.split_file_by_symbols` style proposed in §2.5; agent-UX specialist's call.
3. **`apply_code_action` discoverability** — does the LLM know to call `list_capabilities` first? Either tool description must instruct it, or `apply_code_action` returns a hint when called with an unknown `kind`.
4. **Catalog baseline format** — JSON with `schema_version`. Locking the schema before stage 1 ends prevents catalog-drift CI churn.
5. **Stage-2 vs. stage-3 cut line** — §5.4.4 picks Stage 1+2 = MVP. If Agent-UX specialist objects to 11 tools at MVP, fall back to Stage 1 only (5 primitive tools); document the implication.
6. **`O2_SCALPEL_DISABLE_LANGS` semantics** — disables which servers? Just scalpel's, or also gates strategy registration? Lock before stage 1 fixture work.
7. **`changeAnnotations` auto-accept policy** — full-coverage MVP auto-accepts with audit log; prior MVP rejected. Confirm with security-conscious users (the user's profile flags regression aversion; auto-accept is a regression-vector).
8. **Rope library version pin** — pylsp-rope's library dependency on `rope` itself. Pin `rope` exact version in `pyproject.toml`.
9. **basedpyright vs. pyright choice** — basedpyright is a community fork of pyright. Pin one; basedpyright is recommended (Pylance-derived auto-import works upstream).
10. **`ruff` standalone vs. `pylsp-ruff` plugin** — both work; pylsp-ruff is in-process (cheaper) but couples ruff updates to pylsp updates. Lock before stage 1.

---

## §14 — Recap, in one paragraph

The new directive trades a tightly-bounded 4-tool MVP for a coverage-led MVP that satisfies "full support" by combining a small ergonomic facade set (5 facade tools at the top of the funnel) with a primitive escape hatch (`apply_code_action` + `execute_command` + `list_capabilities`) that makes every of 158 rust-analyzer assists, every of 16 Python LSP commands, and every of 19 RA extensions reachable from a Claude Code session. The cost is 3.1× the prior LoC and 5× the test surface, dominated by per-family fixtures and a multi-server multiplexer the prior MVP didn't need. The resource floor moves modestly (16 → 24 GB recommended, with documented 16 GB opt-out flags). Distribution stays local-only at MVP; marketplace remains v1.1 work for stronger reasons under the new directive than under the old one. Stage 1 ships the reach foundation (full primitive coverage + catalog + rollback); Stage 2 adds the top-decile ergonomic facades and is the MVP cut line; Stage 3 (the remaining facades + the long-tail E2E scenarios) becomes `v0.2.0` and ships immediately after.

End of report.
