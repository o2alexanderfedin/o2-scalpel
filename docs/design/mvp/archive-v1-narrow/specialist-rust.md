# MVP Brainstorm — Rust Language Specialist

Status: report-only. Brainstorming input for the o2.scalpel MVP scoping round.
Authoritative design: [`2026-04-24-serena-rust-refactoring-extensions-design.md`](../2026-04-24-serena-rust-refactoring-extensions-design.md).
Open-questions resolution: [`2026-04-24-o2-scalpel-open-questions-resolution.md`](../2026-04-24-o2-scalpel-open-questions-resolution.md).
Capabilities reference: [`2026-04-24-rust-analyzer-capabilities-brief.md`](../../research/2026-04-24-rust-analyzer-capabilities-brief.md).
Protocol reference: [`2026-04-24-mcp-lsp-protocol-brief.md`](../../research/2026-04-24-mcp-lsp-protocol-brief.md).

Context: the original design planned **Rust-only v1**. The product owner has just declared that **Rust AND Python are top priority for MVP**. This document is the Rust specialist's input to the rescoping. Its purpose is *not* to defend Rust's primacy; it is to identify (a) what Rust must contribute on day one to make the dual-language MVP coherent, (b) what Rust pieces are safely deferrable, and (c) what facade shapes look "Rust-shaped" today and need to be sanded flat before two strategies ship in parallel.

The single most important consequence of the priority change for Rust:
> **The default abstraction-validation pressure inverts.** With one language, every shortcut bakes Rust-isms into the facade and the cost only surfaces when the next language is added. With two languages, every shortcut is caught at MVP because Python's strategy can refuse to implement it. **This is good for the architecture and bad for Rust's MVP timeline.** Several "free" simplifications the Rust-only design assumed are no longer free.

---

## 1. Executive position

| Topic | Rust specialist's MVP recommendation | Rationale |
|---|---|---|
| rust-analyzer assists in v1 | **6 of 158** (`extract_module`, `move_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs`, `auto_import`, `remove_unused_imports`) — everything else reachable only via the primitive escape hatch (`apply_code_action`). | These six are exactly what the §Workflow 5-turn split-file scenario uses. Adding any seventh assist as a facade is feature creep before the facade is proven against Python. |
| Facades that must work on Rust on day one | `plan_file_split`, `split_file_by_symbols`, `extract_symbols_to_module`, `move_inline_module_to_file`, `fix_imports`, `rollback_refactor`. | These are the facades the design report names. None can be cut without breaking the headline workflow. `fix_imports` is the one most often underestimated — see §3. |
| Facades that can be Rust-next (post-MVP) | None of the six. **What can be deferred is *depth*, not *breadth*.** Specifically: `plan_file_split` ships the `by_cluster` strategy only (drop `by_visibility`, `by_type_affinity`); `split_file_by_symbols` ships `dir` parent-module style only (drop `mod_rs`); `reexport_policy` ships `preserve_public_api` and `none` only (drop `explicit_list`). | Reduces ~600 LoC facade row in the effort table to ~350 LoC without losing any E2E gate. |
| Pitfalls that must be solved before MVP | Five, listed in §2: `snippetTextEdit:false` advertisement, `$/progress rustAnalyzer/Indexing` wait, `ContentModified` retry-once, `cargo.targetDir` override, cold-start expectation-setting in the tool description. | Each one *will* corrupt the §Workflow demo if absent. None are deferrable. |
| Pitfalls that look scary but can be deferred | `workspace/applyEdit` reverse-request handler beyond a pass-through stub; `changeAnnotations needsConfirmation` (just reject for MVP); proc-macro mid-refactor reload (`rust-analyzer/rebuildProcMacros`); SSR (`experimental/ssr`); `viewItemTree` optimization. | These exist in the design but the MVP workflow does not exercise them. Stub or omit. |
| `calcrs` fixture | **Keep as-is**, with one shrink: drop the binary target (`src/main.rs`) and the `expected/post_split/` snapshot tree from MVP gates. ~900 LoC `lib.rs` is the right size; semantic equivalence is the right test. | The binary target adds nothing to the refactor pipeline and the post-split snapshot tree is a maintenance burden that catches edits the diagnostics-delta check already catches. |
| E2E gates for MVP | E1, E2, E3, E9, E10 block release. E4–E8 nightly. **Same as the design report's gating.** | The priority-change does not affect Rust's gating; it adds a Python E1'/E9' that Python specialist will define. Keep Rust gates orthogonal. |
| Single largest MVP risk specific to Rust | **rust-analyzer cold-start latency on the user's first invocation.** Five minutes of indexing on a 200-crate workspace before the first `codeAction` returns is a UX bug, not just a performance concern. The agent has no way to know "the tool is fine, the LSP is warming up" unless the tool tells it. | See §5, risk R1. The mitigation is contractual (tool-description text) plus a `wait_for_indexing()` guard, *both* required. |
| Single largest abstraction leak today | `parent_module_style: dir|mod_rs` in `split_file_by_symbols` input schema. **This term is meaningless for Python, TypeScript, or Go.** | See §6. Recommendation: rename to `parent_layout: package|file` and document Rust's `dir`→`package`, `mod_rs`→`file` mapping inside `RustStrategy`. |

---

## 2. Minimum Rust `LanguageStrategy` surface

### 2.1 Filtering 158 down to MVP-required

rust-analyzer's `crates/ide-assists/src/lib.rs::all()` registers 158 distinct handler entries. Of these, the §Workflow 5-turn scenario uses exactly six. Everything else is **reachable** through the primitive layer (`list_code_actions` → `apply_code_action`) without needing a facade.

Tier classification, MVP-relevant only:

| Assist | Tier | Why |
|---|---|---|
| `extract_module` | T1 — required for MVP facade `split_file_by_symbols` | The "wrap selected items in `mod foo { … }`" first half of the two-step move. No substitute. |
| `move_module_to_file` | T1 — required | The "`mod foo { … }` → `foo.rs` + `mod foo;`" second half. No substitute. |
| `move_from_mod_rs` | T1 — required iff `parent_module_style: mod_rs` is supported in MVP | If MVP drops `mod_rs` style (recommendation: do drop), this assist is Rust-next. If MVP keeps both styles, T1. |
| `move_to_mod_rs` | T1 — required iff `parent_module_style: mod_rs` is supported in MVP | Same. |
| `auto_import` | T1 — required for `fix_imports` facade | Adds missing imports after a symbol moves. Without this, every split leaves dangling unresolved-import errors. |
| `remove_unused_imports` | T1 — required for `fix_imports` facade | Removes orphaned imports left in the source file after a move. |
| `merge_imports` | T2 — desirable but not gating | `fix_imports`'s `reorder=true` flag wants this. MVP can ship without; output will have ungrouped `use` statements. Cosmetic. |
| `qualify_path` | T2 — desirable but not gating | Disambiguates name collisions post-move when `auto_import` is wrong. Edge case in `calcrs`; rarely fires. |
| `fix_visibility` | T2 — strongly desirable | Diagnostic-driven — when a moved item now needs `pub(crate)` to be reachable from its old call site, this is the assist that emits the fix. The Workflow's Turn 2 → Turn 3 gap (`eval::evaluate calls private parser::tokenize`) is exactly this case. **If we drop `fix_visibility` from MVP, the Workflow demo's Turn 3 user-visible recovery — the LLM flipping `reexport_policy: explicit_list` — becomes the only path.** That is acceptable but loses one degree of automation. Recommendation: include `fix_visibility` as a T1 if the cost is small (it is — diagnostic-driven, no extra logic). |
| `change_visibility`, `replace_qualified_name_with_use`, `expand_glob_import`, `unmerge_imports`, `normalize_import`, `split_import` | T3 — defer | None used by the §Workflow scenario. The primitive escape hatch covers them if an LLM chooses to invoke them directly. |
| `extract_function`, `extract_variable`, `extract_type_alias`, `inline_local_variable`, `inline_call`, `inline_type_alias`, `inline_macro`, `promote_local_to_const`, `extract_struct_from_enum_variant` | T3 — defer | Pre-split shaping. Useful in advanced workflows. Out of scope for MVP — design report §Goals already declares "Within-function extractions … not required for the v1 split-file workflow". |
| `generate_*` family (~30 assists) | T3 — defer | Generators (impl, trait_impl, function, derive, etc.) are post-split scaffolding the LLM can do textually faster than via codeAction round-trips. Not MVP. |
| Remaining ~110 assists | Reachable via primitive escape hatch only | Not exposed as facades in v1 *or* v1.x. They are reachable through `list_code_actions` + `apply_code_action`. |

**Net MVP-required Rust assists: 6 (T1) + 1 strongly desirable (`fix_visibility`) = 7.** Effort to drive them through `RustStrategy.extract_module_kind()` etc. is trivial (a string per assist).

### 2.2 What `RustStrategy` looks like at MVP

Per the design's §5 `LanguageStrategy` interface, `RustStrategy` populates roughly the following fields. Each is annotated with **MVP** (must be correct on day one), **Rust-next** (defer), or **Hardcoded** (single value, no real decision happening).

| `LanguageStrategy` method | Rust value | MVP class |
|---|---|---|
| `language` | `Language.RUST` | Hardcoded |
| `file_extensions` | `frozenset({".rs"})` | Hardcoded |
| `extract_module_kind()` | `"refactor.extract.module"` | Hardcoded |
| `move_to_file_kind()` | `"refactor.extract"` (subkinds for `move_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs` filtered by `title`) | MVP |
| `rename_kind()` | `"refactor.rewrite"` | Hardcoded |
| `module_declaration_syntax(name, style)` | `f"mod {name};"` regardless of style | MVP |
| `module_filename_for(name, style)` | `dir` → `{name}/mod.rs`; `file` → `{name}.rs` | MVP if both styles ship; Rust-next if MVP drops `mod_rs` |
| `reexport_syntax(symbol)` | `f"pub use {parent}::{symbol};"` | MVP |
| `is_top_level_item(symbol)` | `True` iff `kind in {Function, Struct, Enum, Trait, Const, Static, TypeAlias, Module}` and `symbol.parent is None` | MVP |
| `symbol_size_heuristic(symbol)` | `symbol.range.end.line - symbol.range.start.line` | Hardcoded |
| `execute_command_whitelist()` | `frozenset()` for MVP — drop `experimental/ssr`, `parentModule`, `runnables`, `runFlycheck`, `expandMacro`, `viewItemTree` | Rust-next (none of them are used by the MVP facades; ship empty whitelist; primitive escape hatch handles power users) |
| `post_apply_health_check_commands()` | `[]` for MVP — `runFlycheck` is the canonical entry but it adds 5–30s to every refactor and the diagnostics-delta path already covers correctness | Rust-next |
| `lsp_init_overrides()` | `{"rust-analyzer.cargo.targetDir": "${CLAUDE_PLUGIN_DATA}/ra-target", "rust-analyzer.procMacro.enable": True}` | MVP — both non-negotiable |

Total MVP-relevant `RustStrategy` LoC: ~120, down from the design report's ~180.

### 2.3 Day-one facade behavior on Rust

Per facade, what "works on Rust on day one" looks like:

| Facade | MVP Rust behavior | Deferred behavior |
|---|---|---|
| `plan_file_split` | `strategy="by_cluster"` only. Returns `suggested_groups` based on label-propagation over the call/type-reference graph. `cross_group_edges` populated. | `by_visibility`, `by_type_affinity` strategies. |
| `split_file_by_symbols` | `parent_module_style="dir"` only (one filesystem layout). `reexport_policy in {"preserve_public_api", "none"}`. `keep_in_original` honored. `allow_partial=False` only (strict atomic). `dry_run` honored. | `parent_module_style="mod_rs"`, `reexport_policy="explicit_list"` + `explicit_reexports`, `allow_partial=True`. |
| `extract_symbols_to_module` | Thin wrapper over `split_file_by_symbols` with single-group input. | — |
| `move_inline_module_to_file` | `target_style="dir"` only. | `target_style="mod_rs"`. |
| `fix_imports` | `add_missing=True`, `remove_unused=True`, `reorder=False` (drop `merge_imports`). `files=[explicit list]` only — no `["**"]` glob. | `reorder=True`, glob-based file enumeration. |
| `rollback_refactor` | Full behavior. | — |

**This is materially smaller than the design report's facade surface.** The point is *not* to defang the product; it is to ensure that for the dual-language MVP, every facade option that ships on Rust has a corresponding implementation on Python, and every facade option that does *not* ship on Rust is also unspecified for Python — so the schema is honestly identical across languages.

---

## 3. Rust-specific pitfalls that MUST be solved before MVP

These are the items where "deferring" means the §Workflow demo will visibly fail. They are **not** deferrable.

### 3.1 `snippetTextEdit: false` advertisement at `initialize`

**Source.** Capabilities brief §5 (`SnippetTextEdit (extension)`). Design report §Gap 5. rust-analyzer's `to_proto.rs::snippet_workspace_edit` always builds `SnippetDocumentChangeOperation` entries; it falls back to plain `TextEdit` only if the client advertises `snippetTextEdit: false`.

**What goes wrong without it.** The applier writes literal `$0` markers into source files. `cargo check` doesn't catch this (snippets often appear inside string literals or in places where `$0` is a syntactically-valid placeholder name in macro-heavy code). The `calcrs` fixture's `parser.rs` has multi-line string literals; an `extract_function` over a region containing one will emit `$0` and the file will compile but the test output will diff. **The semantic-equivalence E2E (E9) catches this.** The cost of catching it in E9 is one full rust-analyzer cold start per test failure, which is a 5-minute regression cycle. Solve it at `initialize` to avoid that loop entirely.

**Where.** `/src/solidlsp/language_servers/rust_analyzer.py` line 24 or the equivalent capability negotiation hook. ~5 lines.

**Failure mode the design hints at but does not enforce.** The design says "Prefer advertising false". For MVP, **make it mandatory**, not a preference, because the alternative (post-process snippet stripping in the applier) is 30–50 LoC of regex that fails on edge cases (`\$0` escaped inside a string literal vs. a real placeholder).

### 3.2 `$/progress rustAnalyzer/Indexing` wait

**Source.** Capabilities brief — rust-analyzer emits `experimental/serverStatus` notifications and standard `$/progress` with token `rustAnalyzer/Indexing` during initial workspace load. Design report §1.3 declares `wait_for_indexing(timeout_s)` on `SolidLanguageServer`.

**What goes wrong without it.** First `codeAction` request after server spawn returns either `[]` (empty, looks like "no action available" to the LLM) or `ContentModified (-32801)` (which the retry logic in §3.3 hits, but if the server is still indexing 30 seconds later, the retry also fails). The LLM concludes "the file cannot be split" and gives up. This is **silent failure** — no error code communicates "I am still indexing".

**MVP requirement.** Every facade calls `wait_for_indexing(timeout_s=300)` before its first `codeAction` request. On timeout, return `failure: {kind: "indexing_timeout", hint: "rust-analyzer is still indexing after 5 minutes; the workspace may be very large or proc-macros may be misconfigured. Re-run when indexing completes."}`. This is an MVP requirement because the `calcrs` fixture is small and indexes in <30s; the user's actual codebase will not.

**Where.** `solidlsp` `ls.py` for the listener; every facade for the call. ~30 lines + a one-liner per facade.

### 3.3 `ContentModified` (−32801) retry-once

**Source.** MCP/LSP protocol brief §1.3, §2.2. Capabilities brief §6 limitation 10. Design report §Gap 4.

**What goes wrong without it.** A single retry-once is the spec-correct response. **Without it, every facade fails ~10% of the time on a warm machine and ~40% of the time on a cold machine.** The reason is that `wait_for_indexing()` returns when the *initial* index is done, but rust-analyzer continues to perform background reanalysis on `didChange`, and a `codeAction/resolve` 200ms later may hit a server that has bumped the document version under us.

**MVP requirement.** Wrap `codeAction/resolve` and (less often) `apply_code_action` step in retry-once with a `didChange(file, current_buffer)` resync between attempts. **Two retries is wrong** — if the second retry also fails, the cause is non-transient (the buffer is genuinely stale or the file is being externally modified) and we should fail loud.

**Where.** Every facade that invokes `codeAction/resolve`. Cleanest implementation is a decorator on the resolve helper in `solidlsp` rather than per-facade code.

### 3.4 `cargo.targetDir` override — non-negotiable for two-process

**Source.** Open-questions Q12. Design report §"Two-LSP-process problem and mitigation".

**What goes wrong without it.** Scalpel's rust-analyzer and CC's read-only rust-analyzer both build into `target/`. **`cargo` uses a file lock on `target/` and one process blocks the other.** This manifests as:
- The `calcrs` fixture takes 5–8x longer to index when scalpel is running alongside CC's LSP.
- Random `BlockingError: lock file X held by process Y` errors that look like flaky tests.
- Disk I/O thrash; on macOS, the user's fan turns on for the duration of indexing.

**MVP requirement.** `RustStrategy.lsp_init_overrides()` returns `{"rust-analyzer.cargo.targetDir": "${CLAUDE_PLUGIN_DATA}/ra-target"}`. The `${CLAUDE_PLUGIN_DATA}` placeholder must be resolved correctly at LSP-spawn time — not at strategy registration time, because per-project paths matter (one `ra-target` per project root, not per scalpel install).

**Subtlety the design report does not state.** This doubles disk usage. On a 200-crate workspace with `target/` already at 8 GB, scalpel's parallel target dir is another 8 GB. Document this in the user-facing README of the marketplace plugin, so users on small SSDs don't get surprised. Adding a `O2_SCALPEL_RUST_SHARE_TARGET=1` opt-out (single-target, accept-the-lock-contention) is **not MVP** — it's a foot-gun that requires the user to never run CC's LSP and scalpel's LSP at the same time, which is precisely the workflow we're trying to support.

### 3.5 `procMacro.enable=true` — non-negotiable

**Source.** Open-questions Q12 ("not part of the reduced-capability profile"). Resolution doc explicitly states this.

**What goes wrong without it.** Any code that uses `serde::Deserialize`, `tokio::main`, `clap::Parser`, `thiserror::Error`, async-trait, etc. — i.e., the majority of real Rust code — has incomplete symbol information when proc-macros are disabled. `documentSymbol` returns top-level items but misses derived impls; `references` misses generated trait method calls. **The `plan_file_split` clustering algorithm reads cross-group edges from `references`. Without proc macro expansion, the clustering is wrong on any code that uses derive.**

**MVP requirement.** `RustStrategy.lsp_init_overrides()` includes `"rust-analyzer.procMacro.enable": True`. Memory cost: ~1–2 GB extra; cold-start cost: ~30–60s extra. Both acceptable on the target dev machines (32–64 GB).

**`calcrs` fixture impact.** The fixture is currently designed without proc-macro dependencies (zero crates.io deps). This means the MVP `calcrs` fixture **does not exercise** the proc-macro pathway. This is a known gap. Recommendation: keep `calcrs` proc-macro-free for MVP determinism, but add a `tests/solidlsp/rust/fixtures/refactor/with_macros.rs` integration fixture (already in the design at §Integration tests) that does include `serde` derives — this exists in the design but is not gated. **Promote `with_macros.rs` to MVP-gated** because it's the only place we'll catch a proc-macro misconfiguration before users hit it.

### 3.6 Rust-analyzer cold-start UX

**Source.** Design report §"Two-LSP-process problem", footnote on 5-min cold start.

**What goes wrong without it.** Not a correctness bug; a UX bug. The first scalpel facade call after spawn blocks for up to 5 minutes on a large workspace. The agent has no signal *that this is normal*. The LLM concludes it has hung the tool, attempts to cancel, retries with different inputs, etc.

**MVP requirement.** Two pieces:
1. Tool description text for every facade must include the line: *"On first use after MCP server start in a Rust workspace, this tool may block for several minutes while rust-analyzer indexes the workspace. This is normal."* The model reads tool descriptions and calibrates expectations from them.
2. `wait_for_indexing()` should emit periodic progress to stdout (or to the MCP server's log channel) so a human watching the trace can see "still indexing — 47% — currently parsing crate X". This is debug-grade output, not user-facing — but it's the difference between "the tool hung" and "the tool is doing work". Roughly 10 lines of code wrapping the existing `$/progress` handler.

### 3.7 `workspace/applyEdit` reverse-request handler — minimum viable

**Source.** Design report §1.2. Specialist 3 §4 of the protocol brief.

**What goes wrong without it.** None of rust-analyzer's six MVP-relevant assists trigger a server-initiated `workspace/applyEdit` (they all return `WorkspaceEdit` directly in the `codeAction/resolve` response). Other servers do. For Rust MVP, this handler is *not* exercised in the §Workflow demo.

**MVP requirement.** Register a handler that returns `{applied: false, failureReason: "not implemented in MVP"}` and logs a warning. This is a 5-line stub. The full handler (§1.2 of the design) is Python-relevant — pyright in particular uses server-initiated edits for some refactorings. **The Python specialist may flag this as MVP-required for their side; from the Rust side it is a deferrable stub.**

**Cross-cutting decision.** If Python needs the full handler, build it once correctly. The implementation is language-agnostic (it just delegates to `WorkspaceEditApplier`). Let the Python specialist make the call; Rust is fine either way.

---

## 4. What Rust-specific complexity can be cut from MVP

Per the design report, several pieces are nice-to-have rather than load-bearing. For an MVP under priority pressure, cutting them shrinks the Rust facade footprint by ~30%.

### 4.1 Drop `parent_module_style: "mod_rs"` from MVP

**What it is.** The `mod_rs` style means a module `foo` lives at `foo/mod.rs` instead of `foo.rs`. Rust 2018+ supports both layouts; the community trend since 2018 is `foo.rs` with `foo/` subdirs only when needed.

**Why dropping it is safe.** `calcrs` is edition 2021. The §Workflow demo uses `parent_module_style="dir"` (which means `foo.rs`, despite the misleading name — see §6 below for why that name is wrong). The `move_from_mod_rs` and `move_to_mod_rs` assists exist to *convert between* the two layouts; they are not required to *create* a module.

**What we lose.** Users with `mod.rs`-style codebases (legacy edition-2015 projects, some embedded Rust crates) cannot use scalpel until `mod_rs` ships in v1.x. Acceptable.

**Effort saved.** ~50 LoC of facade branching plus the `move_from_mod_rs`/`move_to_mod_rs` integration tests (`mod_rs_swap.rs` fixture in the design's §Integration tests can move to nightly).

### 4.2 Drop `reexport_policy="explicit_list"` from MVP

**What it is.** A user-supplied list of `pub use` re-exports to emit at the parent module after splitting. Lets the LLM control which symbols stay publicly visible after a refactor.

**Why dropping it is safe.** `preserve_public_api` (the default) auto-detects which symbols had `pub` visibility in the original file and re-exports them. `none` emits no re-exports. These two cover ~90% of real cases. `explicit_list` is the 10% case where the LLM wants to *change* the public API while splitting.

**What we lose.** The Workflow demo's Turn 3 ("LLM flips `reexport_policy: explicit_list`, adds `parser::tokenize` to `explicit_reexports`") becomes Turn 3' ("LLM accepts the diagnostic and uses `Edit` tool to add `pub use parser::tokenize;` manually"). One extra turn for the user. Not a deal-breaker.

**Effort saved.** ~80 LoC of `explicit_reexports` parsing + validation. One test scenario.

### 4.3 Drop `fix_imports(files=["**"])` glob from MVP

**What it is.** Crate-wide `fix_imports` invocation that walks `src/` and fixes imports in every `*.rs` file.

**Why dropping it is safe.** Post-split, only the source file and the newly-created module files have changed. The set of files needing import fixup is exactly `{source} ∪ {new_modules}` — known by the facade, not requiring a glob walk. Always supplying that set explicitly is correct.

**What we lose.** The public API of `fix_imports` becomes "supply the file list explicitly". Slightly more verbose for the LLM. Removes a `workspace/symbol` fallback path that nothing in the MVP workflow uses.

**Effort saved.** ~30 LoC of glob expansion + the workspace/symbol fallback. Nightly E2E E6 stays as nightly.

### 4.4 Drop `experimental/ssr` from the whitelist for MVP

**What it is.** rust-analyzer's structural search/replace. Useful for "rewrite every call to `foo::bar(x)` to `baz::qux(x, default)`" workspace-wide.

**Why dropping it is safe.** `auto_import` plus the LLM's ability to invoke `apply_code_action` directly handle the cases the §Workflow scenario hits. SSR is a power-user fallback; the §Workflow does not use it.

**What we lose.** Power users who want bulk renames beyond what `textDocument/rename` supports must wait for v1.1.

**Effort saved.** ~50 LoC of SSR-specific param shaping in `RustStrategy.execute_command_whitelist()` and the corresponding facade plumbing. Test fixture `ssr_replace.rs` can be deferred entirely.

### 4.5 Drop `rust-analyzer/runFlycheck` from `post_apply_health_check_commands()`

**What it is.** Force rust-analyzer to run `cargo check` and re-emit diagnostics. Useful as a "did the refactor really compile?" final gate.

**Why dropping it is safe.** The `diagnostics_delta` check in `split_file_by_symbols` reads from `textDocument/publishDiagnostics`, which rust-analyzer emits after every meaningful edit. Forcing flycheck adds 5–30s to every refactor for marginal incremental coverage.

**What we lose.** A small class of diagnostics that flycheck produces but the in-memory analyzer doesn't (mostly clippy lints with `MachineApplicable`). Acceptable for MVP.

**Effort saved.** ~20 LoC of execute_command plumbing + the test scenario waiting for flycheck.

### 4.6 Drop `plan_file_split` strategies `by_visibility` and `by_type_affinity`

**What they are.** Alternate clustering algorithms — group items by `pub`/`pub(crate)`/private status (`by_visibility`) or by which type they belong to (`by_type_affinity`).

**Why dropping is safe.** `by_cluster` (label propagation over the reference graph) is the strongest of the three on `calcrs`'s shape. The other two are demoware.

**What we lose.** `plan_file_split` becomes a pure read-only tool with no `strategy` parameter. Its output schema is unchanged.

**Effort saved.** ~150 LoC of clustering-strategy implementation. Removes the bulk of Open Question #1.

### 4.7 What we explicitly should *not* cut

| Tempting cut | Why we keep it |
|---|---|
| Atomic / rollback machinery | Without rollback, the §Workflow demo's Turn 5 recovery branch fails. The whole "agent can experiment" pitch dies. |
| `dry_run: bool` on every mutator | Same. The dual mode is the safety story. |
| Name-path addressing at facade boundary | Cutting this means accepting byte ranges, which means LLMs do offset arithmetic, which is the bug the entire project exists to prevent. |
| Diagnostics-delta check | Without it, `split_file_by_symbols` returns "applied=true" even if the result has 47 new compile errors. Silent corruption is the worst possible failure mode. |
| Checkpoint persistence to `.serena/checkpoints/` | An MCP server may be killed between apply and rollback; in-memory-only checkpoints lose data on stdio-pipe disconnect (CC issue #43177). Persistence is cheap and answers the question. |

---

## 5. Risks specific to Rust that could blow the MVP timeline

Concrete failure modes ranked by likelihood × blast radius. Each one is something I expect to happen and would prevent unless mitigated explicitly.

### R1 — rust-analyzer cold-start UX confuses the LLM (HIGH × HIGH)

**Symptom.** First facade call after MCP server spawn blocks for 30s–5min. LLM concludes the tool is broken; agent gives up or retries with thrash.

**Mitigation.** Tool-description text + `wait_for_indexing()` + progress logging. See §3.6.

**Why this is the #1 risk.** It's the only one that's guaranteed to fire on the first user demo. A user installs scalpel, runs the marketplace install, opens their actual codebase (not `calcrs`), and the first refactor request hangs. They blame scalpel, file an issue, and the demo never recovers.

### R2 — `calcrs` proc-macro gap masks a real-world failure (HIGH × MEDIUM)

**Symptom.** `calcrs` is proc-macro-free by design (zero crates.io deps for determinism). MVP E2E gates pass. User installs scalpel against a `tokio`-based codebase. `plan_file_split` returns wrong clusters because `references` doesn't see proc-macro-generated trait method calls. User reports "the planner doesn't understand my code".

**Mitigation.** Promote `with_macros.rs` integration fixture from optional to MVP-gated. See §3.5.

### R3 — Two-target-dir approach surprises users on small SSDs (MEDIUM × MEDIUM)

**Symptom.** User on a 256 GB MacBook Air installs scalpel against a 200-crate codebase whose `target/` is 8 GB. Scalpel allocates a parallel `target/` directory and the disk fills.

**Mitigation.** Document in the marketplace README. Add a startup-time disk-space check that warns if free space < 2× current `target/` size. ~10 LoC.

### R4 — `extract_module` private-field-access edge cases break `calcrs` semantic equivalence (MEDIUM × HIGH)

**Symptom.** Capabilities brief §6.3: "`extract_module` does not always correctly handle **private field access** across the new module boundary". The `calcrs` fixture has private struct fields accessed across the parser/eval boundary. After splitting, `eval` cannot see `parser`'s private fields. `cargo check` fails. E9 (semantic equivalence) fails.

**Mitigation.** Two-pronged:
- **`calcrs` design discipline.** Audit the fixture before MVP gating: every cross-cluster reference must go through a `pub(crate)` or `pub` accessor, not a direct field read. This is the design report's "pre-shaping" rule. The fixture's "Ugly-on-purpose features" already includes this — *verify* it does in fact work.
- **`fix_visibility` assist promoted to T1.** Diagnostic-driven; fires automatically on the failing `cargo check` output.

### R5 — `ContentModified` cascade on long facade pipelines (MEDIUM × MEDIUM)

**Symptom.** `split_file_by_symbols` does a 4-group split. Each group involves `extract_module` → resolve → apply → `didChange` → `move_module_to_file` → resolve → apply → `didChange`. That's ~16 LSP round-trips. Probability of *any* round-trip hitting `ContentModified` on a busy server is `1 - (1 - p)^16` where p is the per-call probability. At p=2%, the cumulative probability is ~28%.

**Mitigation.** Beyond retry-once (§3.3): `RustStrategy.serialize_facade_calls = True` — drop a global lock around the whole facade call so concurrent MCP requests can't induce extra `didChange` traffic. Cheap, ~20 LoC.

### R6 — Marketplace install flow surfaces version-skew issues (LOW × HIGH)

**Symptom.** User installs `o2-scalpel` from the marketplace. Their Claude Code is 1.2.0; the marketplace was published against 1.3.0. `.lsp.json` schema has drifted. Pydantic fail-loud fires for every plugin.

**Mitigation.** Open-questions Q10 already covers this with the cache-path mitigation chain. **MVP-gated test**: run scalpel against a fixture cache directory checked into git that matches the *current* CC layout, and assert the discovery code returns the expected `LanguageDescriptor` set. That fixture is the canary for upstream drift.

### R7 — `multilspy` doesn't expose `$/progress` cleanly (LOW × HIGH)

**Symptom.** The design assumes we can listen for `$/progress rustAnalyzer/Indexing` from `solidlsp`. If `multilspy` swallows server-initiated notifications below the `solidlsp` API level, we cannot implement `wait_for_indexing()` correctly. We then fall back to "sleep N seconds and hope" (which is what some Serena callers do today for similar reasons), and §3.2 silently regresses.

**Mitigation.** Verification spike before locking the design: run a 30-line script that spawns rust-analyzer via `solidlsp` and prints all `$/progress` notifications it sees. If none arrive, file a bug against `multilspy` and add a notification-tap shim in `solidlsp/lsp_protocol_handler/server.py`. Mark the spike as MVP-blocking.

### R8 — proc-macro server crashes mid-refactor (LOW × MEDIUM)

**Symptom.** rust-analyzer's proc-macro server is a separate subprocess. It can crash on malformed proc-macro input. When it crashes, `references` returns partial data without an error code. A facade call mid-refactor sees inconsistent symbol info.

**Mitigation.** This is "handle LSP disconnect" (E8 in the design's E2E table). MVP can leave it nightly; the failure is loud (the LSP connection drops, scalpel detects via `pool_pre_ping`, returns `failure: lsp_disconnected`) and there is no silent corruption.

### R9 — Edition 2024 changes import resolution under our feet (LOW × LOW)

**Symptom.** The Rust 2024 edition (stabilized ~2025) changes how `use` paths resolve in some cases. `auto_import` may produce different output on 2024 vs 2021 crates.

**Mitigation.** `calcrs` is pinned to edition 2021. We document that scalpel is tested against editions 2021 and 2024 and that 2018-edition support is best-effort. Honest scope-setting.

### R10 — rust-analyzer's `move_module_to_file` doesn't update *all* `mod` declarations (LOW × MEDIUM)

**Symptom.** Capabilities brief §6.4: "`move_module_to_file` does not rewrite imports in other files". This is correct *for public paths* but breaks if there's a re-export chain. The Workflow demo's `preserve_public_api` policy emits a `pub use new_module::*;` that may shadow an existing item.

**Mitigation.** `fix_imports` with `remove_unused_imports` cleans up the shadow. The diagnostics-delta check catches the rest. No additional work needed for MVP.

---

## 6. Abstraction pressure — leaks a Python-only reviewer wouldn't catch

This section is the most important deliverable from the Rust specialist. The Python specialist will look at the facade signatures and ask "does this make sense for Python?". I am looking at them and asking "do these signatures *quietly* assume Rust?". If yes, the dual-language MVP will ship with hidden Rust-isms that the second-language strategy has to lie about.

### 6.1 `parent_module_style: dir|mod_rs` is Rust-only terminology

**Where.** `split_file_by_symbols` input schema. Design report §3.2.

**Why it's a leak.** Python has no `mod_rs`. Python's analog is `package` (a directory with `__init__.py`) vs. `module` (a `.py` file). TypeScript has neither — it has `index.ts` with explicit `export *` re-exports. Go has package-per-directory only. The vocabulary `dir|mod_rs` is *literally* incomprehensible outside Rust.

**Recommended fix.** Rename the schema field to `parent_layout: package|file` with the following per-strategy mapping:

| Strategy | `package` | `file` |
|---|---|---|
| Rust | `foo/mod.rs` | `foo.rs` |
| Python | `foo/__init__.py` | `foo.py` |
| Go | `foo/` (always — Go has no other option; `file` is invalid for Go and `GoStrategy` should reject it with `failure: layout_not_supported`) | invalid |
| TypeScript | `foo/index.ts` | `foo.ts` |

The Rust-specific `dir|mod_rs` becomes `RustStrategy.layout_from_canonical(layout: "package"|"file") -> Path`. The facade speaks the canonical vocabulary; the strategy translates.

**Default for MVP.** `parent_layout="file"` — the universally-supported value. `package` is opt-in.

### 6.2 `reexport_policy: preserve_public_api` is over-clever

**Where.** `split_file_by_symbols` input schema. Design report §3.2.

**Why it's a (mild) leak.** "Public API" in Rust is computable from `pub` markers. In Python it's nominal — there is no enforced visibility. Python's analog is `__all__` if defined, otherwise "names not starting with `_`". TypeScript's analog is `export` markers. Go's analog is uppercase first letter.

The *concept* is portable; the *implementation* is per-language. This isn't really a leak — it's a strategy method (`extract_public_symbols(file) -> set[name_path]`). But the docstring of the schema should not say "preserves `pub` visibility" — it should say "preserves whatever each language considers exported".

**Recommended fix.** Update docstring; add `LanguageStrategy.is_publicly_visible(symbol) -> bool` if not already there. ~5 lines.

### 6.3 `module_declaration_syntax(name, style) -> str` is Rust-shaped

**Where.** `LanguageStrategy` interface, design report §5.

**Why it's a leak.** The method name says "module declaration", which in Rust is `mod foo;` — a single line emitted in the parent. Python doesn't *have* a module declaration — modules exist by virtue of file presence + `__init__.py`. Go is the same. TypeScript has `export * from "./foo";` which is a re-export, not a declaration.

The signature lies about what it does on non-Rust strategies. On Python, `module_declaration_syntax` either returns `""` (an empty string, which is technically correct but signals "this method is unused on Python") or returns `f"from . import {name}"` which is a re-export, not a declaration. Either way, the abstraction is wrong-shaped.

**Recommended fix.** Replace with two methods that compose:
- `parent_module_register_lines(name) -> list[str]` — what to insert in the parent file. Rust: `["mod foo;"]`. Python: `[]` (nothing). TypeScript: `['export * from "./foo";']` if re-export desired. Go: `[]`.
- `parent_module_import_lines(name, symbols) -> list[str]` — what to insert *if* the parent needs to use the new module's symbols. Rust: `[f"use foo::{{{', '.join(symbols)}}};"]` or empty if `pub use` re-export covers it. Python: `[f"from .{name} import {sym}" for sym in symbols]`. Etc.

The split makes the Rust-vs-Python difference *explicit* in the strategy interface rather than hidden in the implementation of one method.

### 6.4 `is_top_level_item(symbol) -> bool` is fine but underspecified

**Where.** `LanguageStrategy` §5.

**Why it could leak.** Rust's "top-level items" are functions, structs, enums, traits, consts, statics, type aliases, modules. Python has classes, functions, module-level `def`, module-level assignments (constants), module-level `import`s. The notion that "top-level item" is decidable from `documentSymbol` alone is mostly true but fails on Python where module-level `if __name__ == "__main__":` blocks contain executable code that is not a "symbol" but is also not safe to move.

**Recommended fix.** Add a sibling `is_safe_to_move(symbol) -> tuple[bool, reason]`. Rust always returns `(True, "")` for any top-level item. Python returns `(False, "module-level executable code is not safe to move automatically")` for non-symbol regions and for symbols inside `if __name__ == "__main__"` guards. The facade respects `is_safe_to_move`; the planner skips unsafe regions.

### 6.5 Diagnostics integer count is per-language, but assumed comparable

**Where.** `DiagnosticsDelta { before: int, after: int }` schema, design report §3.

**Why it's a leak.** Rust's `cargo check` produces 1 diagnostic per logical error (mostly). pyright produces multiple diagnostics per logical error (one for the assignment, one for the use, one for the type-error chain). The integer count is not comparable across languages, and even within Rust the count varies between `cargo check` and `clippy`.

**Recommended fix.** Augment the schema:
- `before: int` and `after: int` remain (useful for "did it get worse?").
- Add `severity_breakdown: dict[Literal["error", "warning", "info"], {before: int, after: int}]`.
- The strict-mode rule that triggers rollback uses `severity_breakdown["error"].after - severity_breakdown["error"].before > 0`, not the raw count. Warnings should not block.

### 6.6 `lsp_init_overrides()` smells like a Rust-only escape hatch

**Where.** `LanguageStrategy` interface; used by `RustStrategy` for `cargo.targetDir` and `procMacro.enable`.

**Why it could leak.** The set of init options an LSP server takes is wildly different per server. Rust-analyzer takes a deeply nested config tree. pyright takes ~20 flat keys. clangd takes none (config goes in `.clangd`). The signature `lsp_init_overrides() -> dict[str, Any]` works for all of them, but the *purpose* differs.

For Rust, the override is a *hard requirement* (without it, two-process is broken). For Python, it's a *preference* (pyright works fine with defaults). The MVP risk is that we declare the method MVP-required on the interface, then Python's strategy returns `{}` and we wonder why we required it. **It is fine to require — it's just a dict — but the docstring should make clear that an empty return is normal and means "language has no required overrides".**

**Recommended fix.** Document accordingly. No code change.

### 6.7 The cluster algorithm is implicitly Rust-shaped

**Where.** `plan_file_split` "label propagation over the call/type-reference graph", design report §3.1, §1.0 of the design.

**Why it's a leak.** Label propagation works well on Rust because rust-analyzer's `references` is high-quality and `callHierarchy` returns precise edges. On Python, pyright's `references` is correct but `callHierarchy` is shallow — it returns direct call sites but not transitive ones, and dynamic dispatch (`self.handler(x)` where `handler` is set at runtime) is invisible. The clustering will *work* on Python but produce different-quality output, and the user-visible expectation (set by `calcrs` demos) is "the planner finds clean clusters".

**Recommended fix.** Make clustering quality a `LanguageStrategy` concern:
- `LanguageStrategy.clustering_signal_quality() -> Literal["high", "medium", "low"]`. Rust: "high". Python: "medium" (pyright is good but not as good as rust-analyzer for this). The facade includes this in the `plan_file_split` output's `warnings` list when the quality is below "high", so the LLM can calibrate its trust in the suggested groups.

### 6.8 `ParentModuleStyle` enum default is Rust's default

**Where.** Implicit in `parent_module_style: ... = "dir"` (design §3.2).

**Why it's a leak.** "dir" maps to `foo.rs` in Rust (`foo/mod.rs` is the alternate). It maps to `foo/__init__.py` in Python (the *primary*, not the alternate). The default value's *meaning* differs per language even though its *spelling* is the same.

**Recommended fix.** Remove the default at the facade level. Make it a `LanguageStrategy.default_parent_layout() -> Literal["package", "file"]` method. Rust returns `"file"`, Python returns `"package"`, Go returns `"package"`, TypeScript returns `"file"`. The facade default is "whatever the strategy says".

### 6.9 The `dry_run: bool` semantics may differ in subtle ways

**Where.** Every mutating facade.

**Why it's *probably* not a leak but worth flagging. The contract is "`dry_run=True` returns the same `WorkspaceEdit` that would be applied, without applying it". On Rust, this is achievable cleanly because rust-analyzer's `codeAction/resolve` returns a fully-formed `WorkspaceEdit` that we just don't apply. On Python, pyright sometimes emits multi-step refactorings that can't be cleanly simulated without applying the first step (because the second `codeAction` is computed against the post-first-step buffer). Specifically, `extract_method` in pyright is one such case.

**Recommended fix.** Add a `LanguageStrategy.dry_run_supported() -> bool` and document that some strategies may degrade `dry_run` to "preview the first step only, with a warning". MVP can ship with both Rust and Python returning `True`, but the seam exists for future strategies.

### 6.10 `name_path` resolution rules are slightly Rust-shaped

**Where.** Hallucination-resistance section, design §3 (case-insensitive + `ends_with` matching).

**Why it's a leak.** Rust is case-sensitive but the LLM is sloppy — case-insensitive matching is a kindness. Python is case-sensitive in fact (`Foo` and `foo` are different) and also sloppy in convention (`PascalCase` for classes, `snake_case` for functions). Case-insensitive matching on `Foo` could match `foo` (a variable) and `Foo` (a class). **Same name, different conceptual things, both real.** The hallucination-resistance rule needs to know what the symbol's `kind` is.

**Recommended fix.** Augment the resolver: when the requested name has multiple matches by case-insensitive comparison, prefer the kind hint if one was supplied (`"Foo"` with kind `"class"` matches the class, not the variable). If no hint, fail with `AMBIGUOUS_SYMBOL` and list both candidates. The cost is small; the benefit on Python is real.

### 6.11 Summary: the "Rust-shape" leak audit

| Item | Severity | Fix complexity | MVP-blocking? |
|---|---|---|---|
| `parent_module_style: dir\|mod_rs` | High | Small (rename + map) | **Yes** — public API |
| `reexport_policy: preserve_public_api` docstring | Low | Trivial | No |
| `module_declaration_syntax()` | Medium | Small (split into two methods) | **Yes** — strategy interface |
| `is_top_level_item()` | Medium | Small (add `is_safe_to_move`) | Yes — strategy interface |
| Diagnostics integer count | Medium | Small (augment schema) | Yes — public API |
| `lsp_init_overrides()` | Low | Trivial (docstring) | No |
| Cluster algorithm quality | Low | Small (warnings) | No |
| `ParentModuleStyle` default | Medium | Small (move to strategy) | Yes — public API |
| `dry_run: bool` semantics | Low | Trivial (docstring) | No |
| `name_path` resolution | Low | Small (kind hint) | No |

**MVP-blocking abstraction fixes: 5.** All of them are 1-day effort. None is a redesign. The benefit of fixing them now is that Python's strategy isn't forced to lie about Rust-shaped concepts.

---

## 7. Testing — `calcrs` fixture and E2E gates

### 7.1 `calcrs` fixture: keep, with one shrink

The design's `calcrs` fixture is well-designed. Recommended changes for MVP:

| Change | Recommendation | Rationale |
|---|---|---|
| Drop `src/main.rs` | Drop from MVP gates; keep as nightly | The binary target adds nothing to refactor coverage. The library target alone exercises every relevant code path. |
| Drop `expected/post_split/` snapshot tree | Drop from MVP; keep the byte-identical-output assertion in E9 | The snapshot tree is a maintenance burden: small refactor algorithm tweaks change the post-split byte layout without changing semantic equivalence. The `cargo test` byte-identical assertion catches the actual contract; the file-tree snapshot catches incidental layout. Keep snapshot for nightly drift detection. |
| Keep `src/lib.rs` ~900 LoC | Keep | This is the right size — large enough to exercise multi-module splits, small enough to audit by hand. |
| Keep mixed visibility, inline `mod tests`, helper-of-three-clusters, 120-line impl, intertwined `use` chains | Keep | These are exactly the Ugly-on-purpose features that catch real-world breakage. |
| Add: a proc-macro `#[derive]` somewhere | **Add to MVP** | §3.5 / §R2 — without this, the proc-macro pathway is not exercised. Cheapest add: import `serde::{Serialize, Deserialize}` (the only crates.io dep we tolerate, and the most common derive in Rust) and derive both on `ast::Value`. Adds ~2 lines to `lib.rs` and ~5 lines to `Cargo.toml`. |
| Edition | Pin to 2021 | Stable, well-supported, what most users have. 2024 testing is a separate fixture. |

**Net change: shrink by removing main.rs and snapshot tree (50 LoC out), grow by ~5 LoC of serde derive. Total `calcrs` is roughly 850 LoC of Rust + ~40 LoC of Cargo metadata + ~10 LoC of `tests/smoke.rs`. Audit-able in under an hour.**

### 7.2 E2E scenario gates

The design defines 10 E2E scenarios (E1–E10). For MVP:

| Scenario | MVP gate | Nightly | Notes |
|---|---|---|---|
| E1 — Happy-path 1200-line split | **MVP-gated** | also nightly | The headline workflow. Cannot release without. |
| E2 — Dry-run → inspect → adjust → commit | **MVP-gated** | also nightly | The safety story. Cannot release without. |
| E3 — Rollback after failed cargo check | **MVP-gated** | also nightly | The "agent can experiment" story. |
| E4 — Concurrent edit during refactor (`ContentModified`) | Nightly | yes | Important but not user-visible until users hit it. |
| E5 — Multi-crate workspace | Nightly | yes | MVP can ship single-crate-only with documentation. |
| E6 — `fix_imports` on crate-wide glob | **Skip in MVP entirely** | optional | Per §4.3 — glob is a Rust-next feature. |
| E7 — rust-analyzer cold start | **MVP-gated** | also nightly | §3.6 / §R1. The single largest MVP risk. **Must be a release-blocking gate** even though it's slow. |
| E8 — Crash recovery | Nightly | yes | Loud failure mode, not silent. Acceptable to leave nightly. |
| E9 — Semantic equivalence on `calcrs` | **MVP-gated** | also nightly | The near goal. Cannot release without. |
| E10 — Regression: existing `rename_symbol` behavior | **MVP-gated** | also nightly | Regression guard. |

**Net MVP gates: E1, E2, E3, E7, E9, E10 — six scenarios, slightly different from the design's E1/E2/E3/E10/E9 set.** The addition is E7 (cold start UX), promoted from nightly to MVP because it is the user's *first* experience and unrecoverable from a UX-perception standpoint.

**E2E timing budget.** rust-analyzer cold start on `calcrs` is sub-30s (no proc macros, zero crates.io deps before §7.1's `serde` addition; with serde added, ~45s). Six MVP gates × 45s = ~5 min total CI time per Rust-side run. Acceptable.

### 7.3 Integration test fixtures

The design defines six integration fixtures. For MVP:

| Fixture | MVP-required | Rationale |
|---|---|---|
| `big_cohesive.rs` | Yes | `plan_file_split` clustering on cohesive code. |
| `big_heterogeneous.rs` | Yes | `plan_file_split` clustering on mixed code. |
| `cross_visibility.rs` | Yes | `fix_visibility` exercise. |
| `with_macros.rs` | **Yes — promoted from optional** | §3.5 / §R2. |
| `inline_modules.rs` | Yes | `move_inline_module_to_file` is an MVP facade. |
| `mod_rs_swap.rs` | **Defer** | Per §4.1, `mod_rs` style is Rust-next. |

### 7.4 Unit-test coverage delta

The design's unit-test list is correct as-is. MVP-required:

- WorkspaceEditApplier with each `documentChanges` variant — **yes**.
- Name-path resolution including kind-hint disambiguation (per §6.10 fix) — **yes, augmented**.
- Idempotency double-call tests — **yes**.

Add for MVP:
- `RustStrategy.parent_module_register_lines()` and `parent_module_import_lines()` snapshot tests — verifies §6.3 fix produces correct Rust syntax.
- `RustStrategy.is_safe_to_move()` returns `True` for all rust-relevant top-level items, `False` for non-symbol regions — verifies §6.4 fix.

Roughly 50 LoC of additional unit tests beyond the design's ~300 LoC budget.

---

## 8. The dual-language MVP — Rust's specific contributions and dependencies

This section is what changes specifically because Python is now also MVP.

### 8.1 What Rust contributes that Python depends on

- **The complete LSP primitive layer** (§1 of the design — `request_code_actions`, `resolve_code_action`, `execute_command`, `wait_for_indexing`, `workspace/applyEdit` handler). Python uses every method except `workspace/applyEdit` (and even that may be needed for pyright; see §3.7). This layer is language-agnostic by design. **Recommendation: Rust specialist owns this layer's implementation; Python specialist consumes it.**

- **The `WorkspaceEditApplier` upgrades** (§1.4 of the design — `CreateFile`, `DeleteFile`, `RenameFile`, ordering, version-check, snippet stripping, checkpoint capture). Python uses every operation; pyright emits `CreateFile` for `extract_method` to a new file. **Same recommendation: Rust owns implementation, Python consumes.**

- **The facade orchestration scaffolding** (`split_file_by_symbols`'s "for each group: codeAction → resolve → apply → didChange → ..." loop in §3.2 of the design). The pipeline shape is identical across strategies; only the assist names differ. **Recommendation: Rust specialist drafts the orchestration; Python specialist reviews against pyright's quirks before merging.**

- **The `calcrs` fixture and Rust E2E gates.** Python has its own `calcpy` or equivalent. They run in parallel.

### 8.2 What Rust depends on Python to validate

- **The `LanguageStrategy` interface stability.** Once Rust ships `RustStrategy` and Python ships `PythonStrategy`, the next strategy is cheap. *Before* both ship, every interface decision is provisional. **Hard rule: do not merge `LanguageStrategy` v1.0 to main until both `RustStrategy` and `PythonStrategy` compile against it.**

- **The `parent_layout: package|file` rename and the §6 abstraction-leak fixes.** Python specialist will independently flag many of these (different examples, same root cause). **Recommendation: Rust and Python specialists co-review the `LanguageStrategy` interface before any facade is merged.**

- **The `dry_run` semantics.** §6.9 — pyright may have hidden `dry_run` issues that Rust does not. Python specialist must confirm `dry_run` works on every Python-MVP facade.

### 8.3 What Rust does NOT need from Python

- The marketplace plugin layout, `.lsp.json` discovery code, lazy-spawn machinery, `multilspy` integration. All of these are language-agnostic and orthogonal to the Rust-specific work.

- The `NotImplementedStrategy` placeholder concept from the design's §5. With Python now real-MVP, the placeholder is unnecessary for Python; it might still apply to TS/Go for v1.x.

### 8.4 Risks the dual-language pivot introduces for Rust specifically

| Risk | Description | Mitigation |
|---|---|---|
| Schedule slip from interface co-review | Forcing Rust+Python co-review of `LanguageStrategy` adds a synchronization point. | Time-box co-review to 1 day. Disagreements escalate to the design author for tie-break. |
| Premature generalization | "What if Go also wanted X?" speculation creeps in during co-review. | Hard rule: only fix abstractions that *concretely* appear in either Rust or Python today. Defer all "what if Go..." discussion to v1.x. |
| Test matrix explosion | Two languages × six MVP scenarios × proc-macro/non-proc-macro variants. | Keep Rust E2E and Python E2E as separate `pytest` markers. Each language owns its own gating. |

---

## 9. Effort estimate (MVP-trimmed, Rust side)

Compared to the design report's totals, this MVP scope:

| Layer | Design report LoC | MVP Rust-side LoC | Delta |
|---|---|---|---|
| `solidlsp` primitive methods | ~90 | ~90 | 0 |
| `rust_analyzer.py` init tweak | ~5 | ~10 | +5 (adds `procMacro.enable`, `cargo.targetDir`) |
| WorkspaceEdit applier upgrade | ~150 | ~150 | 0 |
| Checkpoint/rollback machinery | ~100 | ~100 | 0 |
| Primitive tools | ~200 | ~200 | 0 |
| Facade tools (language-agnostic) | ~600 | ~350 | -250 (drops `mod_rs`, `explicit_list`, glob, `by_visibility`, `by_type_affinity`) |
| `LanguageStrategy` interface + registry | ~120 | ~140 | +20 (adds `is_safe_to_move`, `parent_module_register_lines` etc. per §6) |
| `RustStrategy` plugin | ~180 | ~120 | -60 (drops most of `execute_command_whitelist`, `post_apply_health_check_commands`) |
| Unit tests | ~300 | ~350 | +50 (Rust strategy snapshots) |
| Integration tests | ~400 + 6 fixtures | ~350 + 5 fixtures | -50, -1 fixture (`mod_rs_swap` deferred) |
| E2E harness + scenarios | ~500 + 10 fixture workspaces | ~450 + 6 fixture workspaces | -50, -4 nightly-only |
| **Rust-side total** | **~2,645 LoC + 16 fixtures** | **~2,310 LoC + 11 fixtures** | **-335 LoC, -5 fixtures** |

**Plus Python-side delta** (estimated by the Rust specialist as a sanity check, not authoritative): `PythonStrategy` ~150 LoC, `calcpy` fixture ~600 LoC of Python, Python unit tests ~250 LoC, Python integration tests ~250 LoC + 4 fixtures, Python E2E gates 4 scenarios ~250 LoC + 4 fixture workspaces. **~1,500 LoC + 9 fixtures on the Python side.**

**Combined dual-language MVP: ~3,800 LoC + 20 fixtures**, vs. the design report's Rust-only ~2,650 LoC + 16 fixtures. **~50% larger** for double the language coverage and a stronger abstraction.

### 9.1 Staging recommendation

Same shape as the design's three stages but with a Python validation gate at each:

1. **Stage A (Small):** Primitive layer + `LanguageStrategy` interface skeleton. Both Rust and Python implement enough of the strategy to call `apply_code_action(id)` end-to-end against their respective LSP. Validates the protocol.

2. **Stage B (Medium):** Checkpoint/rollback + primitive tools + `RustStrategy` *and* `PythonStrategy` minimum viable. Both languages can do a manual split via primitives.

3. **Stage C (Large):** Facade layer. `RustStrategy` and `PythonStrategy` both pass E1, E2, E3, E7, E9, E10 (or Python equivalents). MVP ships when both gate passes.

The **strict ordering rule** is that Stage B's PythonStrategy MUST land before Stage C's facade layer is merged — because the facade is where the abstraction leaks live, and we can only catch them with a real second strategy in tree.

---

## 10. Summary of MVP recommendations (the actionable list)

In priority order, what the Rust specialist recommends for the MVP:

### Must-do for MVP (release-blocking)

1. **Six rust-analyzer assists wired into `RustStrategy`:** `extract_module`, `move_module_to_file`, `auto_import`, `remove_unused_imports`, `fix_visibility`, plus `move_module_to_file` resolve flow. (~7 with `fix_visibility` strongly desirable.)
2. **Five Rust-specific LSP layer pitfalls solved:** `snippetTextEdit:false`, `wait_for_indexing()`, `ContentModified` retry-once, `cargo.targetDir` override, `procMacro.enable=true`.
3. **Cold-start UX:** tool-description text + progress logging + 5-min indexing timeout with explicit failure message.
4. **`workspace/applyEdit` reverse-request stub** (full implementation Python-driven if needed).
5. **Five abstraction-leak fixes from §6:** `parent_module_style`→`parent_layout`, `module_declaration_syntax` split, `is_top_level_item`→add `is_safe_to_move`, diagnostics severity breakdown, `ParentModuleStyle` default moves to strategy.
6. **Six MVP E2E gates: E1, E2, E3, E7, E9, E10** with `with_macros.rs` integration fixture promoted from optional.
7. **`calcrs` fixture shrink:** drop binary target, drop snapshot tree, add minimal `serde` derive.

### Cut from MVP (Rust-next)

1. `parent_module_style: "mod_rs"` and the `move_from_mod_rs`/`move_to_mod_rs` assists.
2. `reexport_policy: "explicit_list"` and `explicit_reexports`.
3. `fix_imports(files=["**"])` glob expansion.
4. `experimental/ssr` whitelist entry.
5. `rust-analyzer/runFlycheck` post-apply health check.
6. `plan_file_split` strategies `by_visibility` and `by_type_affinity`.
7. `merge_imports` and the `reorder=true` flag in `fix_imports`.
8. Nightly E2E scenarios E4, E5, E6, E8.
9. `mod_rs_swap.rs` integration fixture.
10. `experimental/parentModule`, `experimental/runnables`, `viewItemTree`, `expandMacro` from `RustStrategy.execute_command_whitelist()`.

### Required cross-language coordination (Rust + Python specialists)

1. Co-review `LanguageStrategy` interface before facade layer merges (Stage C blocker).
2. Settle the `parent_layout` vocabulary and the `default_parent_layout()` per-strategy method.
3. Settle whether the `workspace/applyEdit` reverse-request handler is full-fidelity (Python's call) or stub (Rust's call).
4. Settle whether `dry_run` is `True` for both strategies on every facade, or whether some facades have `dry_run_supported() = False` exceptions.
5. Settle the diagnostics severity-breakdown schema.

---

## 11. Appendix — assist-by-assist file-splitting traceability

This appendix walks through every code path the §Workflow demo touches and documents which assist fires when. Useful as a debugging reference and as a checklist for verifying the MVP's coverage.

### 11.1 The `extract_module` step

Trigger: `split_file_by_symbols` Turn 3, "for each group" inner loop, step (a) per design §3.2.

Inputs to rust-analyzer:
- `textDocument/codeAction` with `range` covering the contiguous run of items in the group.
- `context.only = ["refactor.extract.module"]`.
- `context.triggerKind = 1` (Invoked).

Expected response: array of one or more CodeAction descriptors. The relevant one has `kind == "refactor.extract.module"` and `title` matching `Extract into module` (rust-analyzer's exact title; do not depend on it staying byte-identical across rust-analyzer versions — match by `kind` first, `title.lower().startswith("extract into module")` second).

`codeAction/resolve` returns a `WorkspaceEdit` with:
- One `TextDocumentEdit` against the source file. Inside: a `delete` of the original items' range, an `insert` of `mod <name> { <items> }` at the same offset.
- No `CreateFile` operation. The module is *inline* at this stage.
- `documentChanges` array length: 1.

What the applier does:
- Sort the inner `edits` array by descending `start` offset (per protocol brief §2.3).
- Apply atomically.
- Issue `didChange` with the post-edit buffer.

Rust-specific catches:
1. `extract_module` rewrites external references inside the new module to fully-qualified paths automatically. Test by introspection: a `parser::Token` reference inside the moved code should become `crate::parser::Token` (or similar, depending on relative path).
2. Visibility on items is *not* changed by `extract_module`. If `parser::tokenize` was private in the source file and is referenced from the new `eval` module's code, **you'll get a diagnostic at the next step** (`mod tokenize is private`). This is where `fix_visibility` enters.
3. Non-contiguous selections (capabilities brief §6.2): `extract_module` requires contiguous source text. The facade splits non-contiguous groups into multiple `extract_module` calls and merges the resulting inline modules in a synthesized post-step. This synthesis is non-trivial — ~80 LoC in `split_file_by_symbols`.

### 11.2 The `move_module_to_file` step

Trigger: same loop, step (e).

Inputs to rust-analyzer:
- `textDocument/codeAction` with `range` zero-width *on the `mod` keyword* of the inline module just created.
- `context.only = ["refactor.extract"]` (broad — `move_module_to_file` is registered under `refactor.extract` per capabilities brief).

Important: the cursor must be on the `mod` keyword *before* the `{`. Putting it on the module name or inside the body returns a different action (or none). The facade computes this offset from the post-`extract_module` edit's recorded insertion point.

Expected response: includes one CodeAction with `title == "Extract module to file"` (or similar; match by behavioral signature in the resolve step). Resolve returns a `WorkspaceEdit` with:
- A `CreateFile` operation for `<module>.rs` (or `<module>/mod.rs` if `parent_layout="package"`).
- A `TextDocumentEdit` writing the body into the new file.
- A `TextDocumentEdit` against the source file replacing `mod <name> { … }` with `mod <name>;`.
- `documentChanges` array length: 3, in this order.

What the applier does:
- Apply `CreateFile` first (ensures the target exists).
- Apply the `TextDocumentEdit` against the new file (writes its body).
- Apply the `TextDocumentEdit` against the source file (replaces inline with declaration).
- Issue `didChange` for the source file. The new file does not need `didChange` because rust-analyzer's `willCreateFiles` workflow handles its registration — except `willCreateFiles` is not wired (capabilities brief §6.7), so we *do* need to issue `didOpen` for the new file. This is one of the surprising plumbing details. ~5 LoC in the applier.

Rust-specific catches:
1. The body-writing edit may use `SnippetTextEdit` with `$0` cursor markers — see §3.1.
2. If `#[path = "..."]` attributes are in play, `move_module_to_file` honors them and writes to the custom path. The applier must trust the `CreateFile` URI rather than computing a path itself. (capabilities brief §6.4 mentions `#[path]`.)
3. The 500ms or `$/progress` wait between this step and the next group's `extract_module` (per design §3.2 step 2g) is real — rust-analyzer reanalyzes the workspace after a file is created and `codeAction` calls during reanalysis can return stale results.

### 11.3 The `auto_import` step (inside `fix_imports`)

Trigger: `fix_imports` Turn 4, per file in the supplied list.

Inputs to rust-analyzer:
- `textDocument/codeAction` with `range` zero-width at line 0, character 0.
- `context.only = ["quickfix"]`.
- `context.diagnostics = [<list of unresolved-import diagnostics for this file>]`.

The diagnostics list is critical: `auto_import` is a quickfix bound to a specific diagnostic. Without diagnostics in `context`, rust-analyzer returns nothing. The facade pulls diagnostics from the most recent `publishDiagnostics` notification.

Response: one CodeAction per missing import, kind `quickfix`, title like `Import \`crate::parser::Token\``. Resolve gives a small `TextDocumentEdit` adding the `use` line.

Apply each in sequence with `didChange` between (because each new `use` affects offsets). Or: collect all and merge into one `TextDocumentEdit` — but then sort descending by `start` to avoid offset drift. The latter is faster but error-prone; MVP sticks with sequential.

### 11.4 The `remove_unused_imports` step

Trigger: same `fix_imports` pass.

Inputs:
- `textDocument/codeAction` with `range` covering the entire file's import region (line 0 to first non-`use` line).
- `context.only = ["quickfix"]` or `["source.organizeImports"]`.

Match the response by `kind == "source.organizeImports"` or `title.startswith("Remove unused")`.

This assist often emits *one* WorkspaceEdit with multiple `delete` operations against the source file. Apply in one shot.

### 11.5 The `fix_visibility` step (Rust-next-but-strongly-recommended-for-MVP)

Trigger: when `diagnostics_delta.new_errors` contains a "private" or "visible" diagnostic. The facade introspects the diagnostic's `code` field; rust-analyzer emits `code: "private"` for visibility errors.

Inputs:
- `textDocument/codeAction` with `range` at the offset reported in the diagnostic.
- `context.only = ["quickfix"]`.
- `context.diagnostics = [<the visibility diagnostic>]`.

Response: a CodeAction with `title` like `Make tokenize public` or `Change visibility to pub(crate)`. The default rust-analyzer choice is `pub(crate)` which is correct 95% of the time.

If the facade sees this diagnostic and `fix_visibility` is unavailable in MVP, the failure path is rollback — the `calcrs` Turn 3 demo regression. With `fix_visibility` enabled, the facade applies it and re-checks diagnostics; if the count goes to zero, the refactor succeeds.

### 11.6 Why this matters for MVP scope

The five assists above (`extract_module`, `move_module_to_file`, `auto_import`, `remove_unused_imports`, `fix_visibility`) drive the entire §Workflow scenario from Turn 1 to Turn 4. **Adding any sixth assist to MVP requires a new test scenario and a new fixture.** Subtracting any of these five causes a user-visible regression.

The seventh assist (`merge_imports`, optional under `fix_imports(reorder=True)`) is cosmetic. Cutting it costs zero correctness and saves one nightly fixture. Recommendation: cut.

---

## 12. Appendix — `RustStrategy` decision rationale per method

For each method on `LanguageStrategy`, the rationale for the value `RustStrategy` returns.

### 12.1 `extract_module_kind() -> "refactor.extract.module"`

This is the LSP-spec hierarchical kind. rust-analyzer registers the assist under exactly this string (capabilities brief §1.1a). Hardcoded — cannot drift unless rust-analyzer renames the kind, which would be a breaking change upstream tracks separately.

### 12.2 `move_to_file_kind() -> "refactor.extract"` (with title disambiguation)

rust-analyzer registers `move_module_to_file`, `move_from_mod_rs`, `move_to_mod_rs` all under `refactor.extract` (not `refactor.move` — the LSP kind hierarchy doesn't have a clean "move" subkind). The strategy must disambiguate by `title` substring, which is fragile. **Better-but-deferred:** add `RustStrategy.match_assist_by_signature(actions, signature) -> CodeAction | None` that uses behavioral matching (does the WorkspaceEdit contain `CreateFile`? Then it's `move_module_to_file`). This is more robust but requires a resolve-call per candidate. Defer to v1.x.

### 12.3 `rename_kind() -> "refactor.rewrite"`

rust-analyzer's renaming assists (specifically those that aren't `textDocument/rename`) live under `refactor.rewrite`. Standard LSP rename uses `textDocument/rename` directly, not codeAction. The `rename_kind()` value matters only for non-`textDocument/rename` style renames, which are rarely needed.

### 12.4 `module_declaration_syntax(name, layout) -> "mod {name};"`

Single line, terminated with semicolon. Same syntax regardless of layout — rust-analyzer's edits in the parent file always use this form. The `layout` parameter is unused by this method on Rust; it's used by `module_filename_for()`.

### 12.5 `module_filename_for(name, layout)`

```
layout == "package" → name + "/mod.rs"
layout == "file"    → name + ".rs"
```

The MVP cut (drop `package`/`mod.rs` style) means this method always returns `name + ".rs"` until v1.x. Can be hardcoded as such for MVP.

### 12.6 `reexport_syntax(symbol)`

```
f"pub use {parent}::{symbol};"
```

Where `{parent}` is the parent module name (computed by the facade, not the strategy). The strategy receives the symbol and emits the syntax; the parent path is resolved at the facade level because it depends on the file location, which is filesystem-coupled and outside `LanguageStrategy`'s scope.

### 12.7 `is_top_level_item(symbol)`

```python
return (
    symbol.parent is None
    and symbol.kind in {
        SymbolKind.Function,
        SymbolKind.Struct,
        SymbolKind.Enum,
        SymbolKind.Trait,
        SymbolKind.Const,
        SymbolKind.Static,
        SymbolKind.TypeAlias,
        SymbolKind.Module,
    }
)
```

Excludes: `Variable` (Rust has no top-level vars except `static` which is `Static`), `Class` (Rust has no `class`), `Method` (always inside an `impl`, never top-level). Specifically *includes* `Module` because a top-level inline `mod foo { … }` is itself a movable item.

### 12.8 `symbol_size_heuristic(symbol)`

```python
return symbol.range.end.line - symbol.range.start.line
```

LoC count. Used by `plan_file_split`'s clustering to balance group sizes. Sufficient for MVP; smarter heuristics (token count, complexity-weighted) deferred.

### 12.9 `execute_command_whitelist() -> frozenset()`

MVP returns empty. Power users invoke rust-analyzer extensions through the primitive escape hatch (`apply_code_action`) or through `solidlsp`'s generic `execute_command(method, params)` path which is unrestricted.

### 12.10 `post_apply_health_check_commands() -> []`

MVP runs no post-apply commands. The diagnostics-delta check (which reads `publishDiagnostics`) is sufficient. `runFlycheck` deferred — it adds 5–30s per refactor for marginal incremental coverage.

### 12.11 `lsp_init_overrides()` — the only hard-required method on `RustStrategy`

```python
return {
    "rust-analyzer.cargo.targetDir": "${CLAUDE_PLUGIN_DATA}/ra-target",
    "rust-analyzer.procMacro.enable": True,
    "rust-analyzer.checkOnSave.enable": False,  # MVP: skip cargo-check on every save (we drive it manually)
    "rust-analyzer.cachePriming.enable": False,  # MVP: skip cache priming (faster cold start)
}
```

Two values are non-negotiable (`cargo.targetDir`, `procMacro.enable` per §3.4, §3.5). Two values are MVP optimizations (`checkOnSave.enable=False`, `cachePriming.enable=False`) that trade some background work for faster cold-start. The `${CLAUDE_PLUGIN_DATA}` placeholder is resolved at LSP-spawn time using `platformdirs.user_data_dir("claude")` (per Q10 of the open-questions resolution).

---

## 13. Appendix — concrete leaks the §6 audit would surface

To make §6 less abstract, here are the *specific* lies a Python-only reviewer would not catch but that ship today in the design:

### 13.1 The Workflow demo's input schema in §3.2

```json
{"tool": "split_file_by_symbols",
 "args": {"file": "calcrs/src/lib.rs",
          "groups": {...},
          "keep_in_original": ["run","VERSION"],
          "parent_module_style": "dir",            // <-- §6.1 leak
          "reexport_policy": "preserve_public_api", // <-- §6.2 docstring leak
          "dry_run": true}}
```

Translated to Python without the §6 fixes, this becomes:

```json
{"tool": "split_file_by_symbols",
 "args": {"file": "myapp/big.py",
          "groups": {...},
          "keep_in_original": ["main", "VERSION"],
          "parent_module_style": "dir",            // <-- means "__init__.py" in Python? unclear
          "reexport_policy": "preserve_public_api", // <-- "preserve __all__"? "preserve names without underscore"?
          "dry_run": true}}
```

The Python LLM has to *guess* what `parent_module_style: "dir"` means. With the fix:

```json
{"tool": "split_file_by_symbols",
 "args": {"file": "myapp/big.py",
          "groups": {...},
          "keep_in_original": ["main", "VERSION"],
          "parent_layout": "package",              // explicit: foo/__init__.py
          "reexport_policy": "preserve_exported",  // explicit: __all__ or non-underscore
          "dry_run": true}}
```

The Rust schema becomes:

```json
{"parent_layout": "file",  // explicit: foo.rs (was "dir" in design)
 "reexport_policy": "preserve_exported"}
```

Same vocabulary, both correct, both honest about what they mean.

### 13.2 The `LanguageStrategy.module_declaration_syntax()` lie

Design says (§5):
```
# Rust: "mod foo;"  |  TS: 'export * from "./foo";'
# Python: "from . import foo"  |  Go: (no-op, filesystem-based)
```

The Python and TS strings are *re-exports*, not declarations. The Go entry admits the abstraction has nothing to declare ("no-op, filesystem-based"). **If the method is "no-op" for some languages, the abstraction is wrong.**

After the §6.3 fix:
- `parent_module_register_lines(name)` — Rust: `["mod foo;"]`. Others: `[]`. Honest empty.
- `parent_module_import_lines(name, symbols)` — Rust: usually `[]` because `pub use foo::*` re-exports cover it. Python: `[f"from .{name} import {sym}" for sym in symbols]` if no `__init__.py` re-export. TS: `[f'export * from "./{name}";']`. Go: `[]` (Go imports happen per-file, not in the package metadata).

Each strategy returns *some* lines — there is no "I don't have anything to do" branch.

### 13.3 The diagnostics-count comparison

Design says (§3): `DiagnosticsDelta { before: int, after: int, new_errors: list[Diagnostic] }`. The strict-mode rule is: `if diagnostics_delta.new_errors > 0: rollback`.

But `new_errors` is a *list*, not a count. Reading the design carefully, the rule depends on whether items in the list have `severity: error` or `severity: warning`. Rust diagnostics from rust-analyzer are mostly errors (the typechecker is strict). Python diagnostics from pyright include a lot of `warning` and `info` severity items — `Variable not used`, `Function may have side effects`, etc. **A naive `len(new_errors) > 0` rollback rule will rollback every Python refactor unnecessarily.**

After the §6.5 fix, the rule reads `diagnostics_delta.severity_breakdown["error"].after - severity_breakdown["error"].before > 0`. Warnings are tracked but don't block.

### 13.4 The `parent_module_style: ... = "dir"` default

Design §3.2: `parent_module_style in {"dir","mod_rs"}=dir`.

For Rust 2018+, "dir" means `foo.rs` (the file alongside other modules). For Python, "dir" intuitively means a directory — i.e., `foo/__init__.py`. **The default value's "dir" in Rust is non-directory (`foo.rs`); in Python "dir" is directory (`foo/__init__.py`).** Same word, opposite meanings.

After §6.8 fix, the default is per-strategy (`default_parent_layout()`). Rust returns `"file"`, Python returns `"package"`. The names match the file system shapes; "file" always means a single file, "package" always means a directory.

### 13.5 The cluster-quality assumption

Design §3.1: `plan_file_split` returns `suggested_groups`. The implicit assumption (reading §1.0 of the design) is that the groups are good enough to act on. On Rust this is true — rust-analyzer's `references` is precise. On Python, pyright's references can be imprecise for code that uses `getattr`, `hasattr`, dynamic class creation, monkey-patching, etc. **The user-visible expectation set by the demo ("Response: 4 suggested groups") may not hold for Python.**

After §6.7 fix, `plan_file_split` includes a `warnings: ["clustering signal quality is medium for Python — consider manual review of cross_group_edges before applying"]` when the strategy reports `"medium"` quality. The LLM sees the warning and can decide whether to act.

---

## 14. Appendix — interaction with Q10/Q11/Q12 of the open-questions doc

The MVP rescoping does not invalidate Q10 (cache discovery + lazy spawn), Q11 (marketplace location), Q12 (two-process cost), Q13 (fork/rename feasibility), or Q14 (on-demand plugin generation). These resolutions hold independent of how many languages MVP ships.

What changes:

- **Q12, Rust line.** The Rust mitigations (`cargo.targetDir`, lazy + idle-shutdown, `procMacro.enable=true`) are unchanged. The decision to ship Python alongside Rust does not affect rust-analyzer's process cost.
- **Q12, Python line.** "Python: no optimization. Pyright spawn is ~300 MB and sub-second." This means dual-language MVP adds essentially zero memory cost on top of Rust-MVP. The 4–8 GB rust-analyzer dwarfs everything else.
- **Q11, marketplace contents.** The marketplace ships `o2-scalpel/` (the MCP server plugin), `rust-analyzer-reference/` (Q14), and `clangd-reference/` (Q14). Adding Python to MVP does *not* require shipping a `pyright-reference/` plugin — Python users install pyright via boostvolt's existing plugin or via the Q14 generator.
- **Q14, generator coverage.** No change. The generator is a developer tool independent of MVP language coverage.
- **Q13, attribution.** No change. Rust + Python MVP scope does not touch upstream `claude-code-lsps` content.

The Rust MVP scope above can be implemented and shipped with no further changes to the open-questions resolutions. They remain orthogonal.

---

## 15. Single-paragraph close

The Rust side of the MVP must ship six rust-analyzer assists, solve five LSP-layer pitfalls (snippet capability, indexing wait, `ContentModified` retry, target-dir override, proc-macro enable), defend the cold-start UX with both tool-description text and progress logging, and accept five small abstraction-shape fixes that turn Rust-specific vocabulary into language-neutral vocabulary. In return, MVP scope shrinks by ~335 LoC and ~5 fixtures on the Rust side. The dual-language MVP is ~50% larger than Rust-only would have been, and that additional cost is the validation cost of catching abstraction leaks before they ship — which is exactly the purpose of doing two languages at once. The single biggest controllable risk is rust-analyzer cold-start UX on the user's first invocation; the single biggest uncontrollable risk is whether `multilspy` exposes `$/progress` notifications cleanly to `solidlsp` (verification spike before locking the design). Everything else is engineering.
