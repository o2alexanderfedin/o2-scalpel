# 02 — rust-analyzer Capabilities Inventory

Source of truth: https://github.com/rust-lang/rust-analyzer (master).
Target question: what does rust-analyzer expose today that helps "split a large Rust file into modules" from an MCP/LSP client?

---

## 1. Code Actions / Assists

All assists live in `crates/ide-assists/src/handlers/`. The authoritative registry is the `all()` function in `crates/ide-assists/src/lib.rs`
(https://github.com/rust-lang/rust-analyzer/blob/master/crates/ide-assists/src/lib.rs). Count: **158** distinct handler entries.

Delivered to clients via standard `textDocument/codeAction`. Kinds advertised: `EMPTY`, `QUICKFIX`, `REFACTOR`, `REFACTOR_EXTRACT`, `REFACTOR_INLINE`, `REFACTOR_REWRITE`. Resolution is two-phase: the initial response carries lightweight `CodeAction` records with `data = { id, code_action_params, version }`; the client calls `codeAction/resolve` to obtain the `edit`.

### 1a. File-splitting relevant assists (flagged)

All handler paths below are `crates/ide-assists/src/handlers/<name>.rs`.

**Module/file boundary:**
- `extract_module` — selection of items → inline `mod <name> { ... }`; qualifies external refs, rewrites `use`s, raises vis to `pub(crate)` where needed. **Inline only — does not create a file.** Contiguous selection only; private-to-module access edge cases imperfect.
- `move_module_to_file` — cursor on `mod foo {` (before `{`) → `WorkspaceEdit` with `CreateFile` op + replacement `mod foo;`. Preserves vis, attrs, `#[path]`, raw idents, nested dirs. Does **not** rewrite imports elsewhere (public paths don't change).
- `move_from_mod_rs` — selection covers entire `mod.rs` body → single `move_file` op: `foo/mod.rs` → `foo.rs` (atomic rename).
- `move_to_mod_rs` — symmetric: `foo.rs` → `foo/mod.rs`.

**Extractors (pre-split shaping):**
- `extract_function`, `extract_variable`, `extract_type_alias`, `extract_struct_from_enum_variant`, `extract_expressions_from_format_string`.
- `promote_local_to_const` — lifts `let` to `const` (needed so items survive extraction).

**Inliners (dissolve glue before re-splitting):**
- `inline_local_variable`, `inline_call` / `inline_into_callers`, `inline_type_alias` / `inline_type_alias_uses`, `inline_macro`, `inline_const_as_literal`.

**Visibility & import hygiene (post-split cleanup):**
- `change_visibility` (cycles vis on item), `fix_visibility` (diagnostic-driven raise at definition).
- `auto_import`, `qualify_path`, `replace_qualified_name_with_use`, `remove_unused_imports`.
- `merge_imports` / `unmerge_imports` / `normalize_import` / `split_import`.
- `expand_glob_import` / `expand_glob_reexport` — useful to see concrete items behind `use foo::*`.

**Ordering helpers:** `reorder_impl_items`, `sort_items`, `reorder_fields`.
**Scaffolders:** `generate_impl`, `generate_trait_impl`, `generate_impl_trait` — for newly-moved types.

### 1b. Remaining assists — summary

The other ~125 assists transform individual expressions/statements (e.g. `convert_bool_then_to_if`, `apply_demorgan`, `flip_binexpr`, `wrap_return_type`, `term_search`, `toggle_async_sugar`, the full `generate_*` and `replace_*` families). Not file-splitting. Full names enumerated in the `all()` function.

---

## 2. Standard LSP Methods Supported

Source: `crates/rust-analyzer/src/lsp/capabilities.rs` (https://github.com/rust-lang/rust-analyzer/blob/master/crates/rust-analyzer/src/lsp/capabilities.rs).

| Method | Supported | Options |
|---|---|---|
| `textDocument/prepareRename` + `textDocument/rename` | yes | `prepare_provider: Some(true)` |
| `textDocument/codeAction` + `codeAction/resolve` | yes | `resolve_provider: Some(true)`, kinds: EMPTY, QUICKFIX, REFACTOR, REFACTOR_EXTRACT, REFACTOR_INLINE, REFACTOR_REWRITE |
| `workspace/executeCommand` | **not registered as a server capability** — rust-analyzer surfaces commands embedded inside `CodeAction.command` and via LSP extensions, not via `executeCommand` |
| `callHierarchy/*` | yes | `Simple(true)` |
| `typeHierarchy/*` | **no** (absent from server_capabilities) |
| `workspace/symbol` | yes | `OneOf::Left(true)`; plus `workspaceSymbolScopeKindFiltering` client capability for scope/kind filters |
| `textDocument/documentSymbol` | yes | |
| `textDocument/inlayHint` + `inlayHint/resolve` | yes | resolve supported |
| `textDocument/semanticTokens/{full,range,full/delta}` | yes | delta mode enabled |
| `textDocument/references` | yes | |
| `textDocument/implementation` | yes | |
| `textDocument/typeDefinition` | yes | |
| `textDocument/definition` | yes | |
| `textDocument/declaration` | yes | `Simple(true)` |
| `textDocument/hover` | yes | |
| `textDocument/completion` + `completionItem/resolve` | yes | triggers `[":", ".", "'", "("]`; resolve gated on client |
| `textDocument/signatureHelp` | yes | triggers `["(", ",", "<"]` |
| `textDocument/documentHighlight` | yes | |
| `textDocument/documentLink` | no |
| `textDocument/foldingRange` | yes | |
| `textDocument/selectionRange` | yes | |
| `textDocument/linkedEditingRange` | no |
| `textDocument/formatting` | yes | |
| `textDocument/rangeFormatting` | conditional (rustfmt) |
| `workspace/willRenameFiles` | **yes**, with filter `**/*.rs` and `**` folders — this is how module renames update `mod` declarations |
| `workspace/{did,will}{Create,Delete}Files` | **no** |
| `positionEncoding` | negotiates UTF-8 → UTF-32 → UTF-16 |

Handlers for each are in `crates/rust-analyzer/src/handlers/request.rs` and `notification.rs` (https://github.com/rust-lang/rust-analyzer/tree/master/crates/rust-analyzer/src/handlers).

---

## 3. rust-analyzer Custom LSP Extensions

Wire-level spec: `docs/book/src/contributing/lsp-extensions.md`
(https://github.com/rust-lang/rust-analyzer/blob/master/docs/book/src/contributing/lsp-extensions.md).
Client glue: `editors/code/src/commands.ts` and `lsp_ext.ts`. Note: these are plain JSON-RPC methods, **not** `workspace/executeCommand` payloads.

### `experimental/*` (negotiated via `experimental` client caps)

| Method | Purpose | I/O |
|---|---|---|
| `experimental/parentModule` | Jump to parent `mod foo;` | `TextDocumentPositionParams` → `Location[]` |
| `experimental/joinLines` | Smart join over ranges | `JoinLinesParams` → `TextEdit[]` |
| `experimental/onEnter` | Context-aware Enter (doc-comment continuation, etc.) | `TDPP` → `SnippetTextEdit[]` |
| `experimental/matchingBrace` | Brace pair finder | positions → positions |
| `experimental/ssr` | Structural search/replace | `SsrParams` → `WorkspaceEdit` |
| `experimental/runnables` | Discover `cargo test/run/check` targets | `RunnablesParams` → `Runnable[]` |
| `experimental/externalDocs` | Docs URL for symbol | `TDPP` → string/null |
| `experimental/openCargoToml` | Locate owning `Cargo.toml` | params → `Location` |
| `experimental/moveItem` | Move item up/down within a scope | `MoveItemParams` (direction) → `SnippetTextEdit[]` |
| `experimental/serverStatus` (notif) | health/quiescent/message | |
| `experimental/discoverTest`, `runTest`, `endRunTest`, `abortRunTest`, `changeTestState`, `appendOutputToRunTest`, `discoveredTests` | Test Explorer | |

### `rust-analyzer/*` (always available)

| Method | Purpose |
|---|---|
| `rust-analyzer/analyzerStatus` | Diagnostic dump |
| `rust-analyzer/reloadWorkspace` | Re-run `cargo metadata` |
| `rust-analyzer/rebuildProcMacros` | Rebuild proc-macros |
| `rust-analyzer/runFlycheck`, `cancelFlycheck`, `clearFlycheck` | `cargo check` control |
| `rust-analyzer/viewSyntaxTree` | JSON syntax tree of file |
| `rust-analyzer/viewHir` / `viewMir` | HIR/MIR dump for function at position |
| `rust-analyzer/viewFileText` | File as the server sees it (after macro expansion context) |
| `rust-analyzer/viewItemTree` | Item-tree dump per file |
| `rust-analyzer/viewCrateGraph` | SVG crate graph |
| `rust-analyzer/expandMacro` | Expand macro at cursor |
| `rust-analyzer/relatedTests` | Tests that cover a symbol |
| `rust-analyzer/fetchDependencyList` | Workspace crates + versions + paths |
| `rust-analyzer/viewRecursiveMemoryLayout` | Type memory layout tree |
| `rust-analyzer/getFailedObligations`, `interpretFunction` | Trait solver / const-eval introspection |
| `rust-analyzer/childModules` | (VSCode command; uses experimental namespace on server) |

---

## 4. Diagnostics & Quick-Fixes

- **Push model**: `textDocument/publishDiagnostics` is used (pull diagnostics are **not** enabled). Source: `crates/rust-analyzer/src/diagnostics.rs` and `crates/ide-diagnostics/`.
- Each diagnostic may carry inline `data` referencing an assist; the matching **quick-fix is surfaced through `textDocument/codeAction`** with `kind = quickfix` rather than inside the diagnostic itself. Fixes are resolved through the same `codeAction/resolve` two-phase flow.
- rust-analyzer also ingests **cargo check / clippy** diagnostics via flycheck and re-emits them; fixes from clippy (`MachineApplicable`) are lifted into code actions.

---

## 5. WorkspaceEdit Shape

Builder: `crates/rust-analyzer/src/lsp/to_proto.rs::snippet_workspace_edit`
(https://github.com/rust-lang/rust-analyzer/blob/master/crates/rust-analyzer/src/lsp/to_proto.rs).

- **Always uses `documentChanges`** (never the legacy `changes` map), with entries of type `SnippetDocumentChangeOperation` — a rust-analyzer extension over `DocumentChangeOperation`.
- **File operations emitted**: `ResourceOp::Create` and `ResourceOp::Rename`. `Delete` is **not** emitted by any current assist; `move_from_mod_rs` / `move_to_mod_rs` use `Rename`, `move_module_to_file` uses `Create`.
- **SnippetTextEdit** (extension): text edits carry an optional `insertTextFormat = Snippet` and `annotationId`. Required so cursor placeholders survive in assists like `generate_function`. Falls back to plain `TextEdit` for clients without the `snippetTextEdit` cap.
- **changeAnnotations**: emitted when the client advertises `workspace.workspaceEdit.changeAnnotationSupport`. Edits that touch files **outside the workspace** (e.g. sysroot, registry dependencies) get an `"OutsideWorkspace"` annotation with `needs_confirmation = true`. Assists may attach their own labels.
- **Ordering quirk**: the builder runs file-system ops first, then text edits, then remaining file-system ops. Clients that split application order can desync.
- **Code-action resolution** is mandatory for most refactors: the first response has no `edit` field — `data = { id, code_action_params, version }` and the client must call `codeAction/resolve`. The `version` is checked against the document version at resolve time; a mismatch produces `ContentModified`.

---

## 6. Known Limitations / Gaps Relevant to File-Splitting

1. **No "move top-level item to another file"** assist. `extract_module` creates an inline module; `move_module_to_file` only works on an *existing* inline `mod foo { … }`. The two-step "wrap-then-extract" chain is the only path. Confirmed by inspection of `handlers/` — no `move_item_to_file`, `move_to_file`, or equivalent exists (as of master, Apr 2026).
2. `extract_module` **requires contiguous selection** — cannot cherry-pick non-adjacent items.
3. `extract_module` does not always correctly handle **private field access** across the new module boundary; post-extraction diagnostics may surface that the user must resolve.
4. `move_module_to_file` **does not rewrite imports in other files**, because public paths do not change — but if `#[path]` is in play, the client must handle custom layouts.
5. **No `workspace/executeCommand`** advertised. Clients must invoke rust-analyzer extensions directly by LSP method name; cannot round-trip arbitrary commands carried in `CodeAction.command`.
6. **No `typeHierarchy`** (LSP 3.17 feature). Structural type relationships must be reconstructed from `implementation` + `references`.
7. **No `willCreateFiles` / `didCreateFiles` / `willDeleteFiles`** — only `willRenameFiles` is wired. Creating a new `.rs` file externally will not auto-generate the `mod` declaration in the parent.
8. **No pull diagnostics** — clients must listen for push.
9. **Rename** across crate boundaries works, but **does not rename the file** when renaming a module (clients must do the FS op and rely on `willRenameFiles` to fix `mod` decls).
10. Assist **resolution requires the same server state**: if the file is edited between `codeAction` and `codeAction/resolve`, the assist is discarded (`ContentModified`). This matters for an MCP server that may batch operations.

---

## Priority Ranking for Serena Integration

Goal: "safely split a large Rust file into modules" driven from an MCP server.

### Tier 1 — essential, low risk

1. **`textDocument/codeAction` + `codeAction/resolve` pipeline** — the only path to every refactoring assist. Must implement the two-phase resolve flow, including `data` round-tripping and version tracking.
2. **`move_module_to_file` assist** — direct "inline mod → file" operation. Deterministic, emits clean `CreateFile` + text edit. Easiest win for file-splitting.
3. **`extract_module` assist** — the workhorse for cutting a flat file into submodules. Must be driven with a precise range selection; pair with (2) to get separate files.
4. **`textDocument/rename` + `prepareRename`** — for renaming the newly-created module or items that collide. Standard LSP, no surprises.
5. **`workspace/willRenameFiles`** — when Serena renames a `.rs` file externally, this call updates `mod` declarations. Cheap, critical for hygiene.
6. **`auto_import` / `qualify_path` / `fix_visibility` / `remove_unused_imports` assists** — mandatory cleanup after any move. All diagnostic- or reference-driven; easy to request via code action at the specific offset.
7. **`textDocument/publishDiagnostics` listener** — Serena must consume diagnostics to know which offsets need `auto_import` or `fix_visibility` applied post-split.

### Tier 2 — high leverage, moderate complexity

8. **`textDocument/documentSymbol` + `workspace/symbol`** — to plan the split (identify top-level items, sizes, cohesion).
9. **`textDocument/references` + `callHierarchy`** — to validate cohesion before extracting (do these items really belong together?).
10. **`extract_function` / `extract_variable` / `inline_*` assists** — pre-split normalization (reduce duplication, surface shared state).
11. **`rust-analyzer/viewItemTree`** — single-call structural enumeration of a file; faster than walking `documentSymbol` trees.
12. **`experimental/ssr`** — structural search/replace across the workspace. Powerful for bulk path rewrites if default assist updates miss anything.
13. **`textDocument/inlayHint`** (types, lifetimes, param names) — useful for verifying that extracted code preserves semantics.

### Tier 3 — nice to have

14. **`experimental/runnables`** — post-split, trigger `cargo check` / test runs.
15. **`rust-analyzer/runFlycheck`** — force a diagnostic pass after applying a multi-step workspace edit.
16. **`rust-analyzer/expandMacro`**, **`viewHir`**, **`viewMir`** — debugging aids when a refactor triggers macro-related surprises.
17. **`experimental/moveItem`** — within-file reordering; marginal for cross-file splits.

### Tricky to drive from an MCP server — flag items

- **Two-phase `codeAction/resolve`**: the MCP tool must hold the initial `CodeAction` token (with `data`) and submit a follow-up resolve. Document versions must be tracked; otherwise `ContentModified`. Simple REPL-style "apply action" won't work.
- **`SnippetTextEdit` with `$0` placeholders**: non-VSCode clients must strip snippet markers. Serena either needs to advertise `snippetTextEdit: false` or post-process.
- **`changeAnnotations` for out-of-workspace edits**: requires user-confirmation flow. An autonomous MCP agent must decide policy (auto-accept? reject?) explicitly.
- **Ordering of `documentChanges`**: file-system ops are interleaved with text edits. Naive clients that sort by URI will break `move_module_to_file`.
- **The "move top-level item to another file" gap**: no single assist. Serena must compose: wrap items in `mod tmp { ... }` (synthesized edit) → invoke `move_module_to_file` → optionally `move_to_mod_rs`. Each step requires its own resolve cycle. This is the single biggest gap to design around.
- **`willRenameFiles` is advisory**: the client must apply the returned edit alongside the rename; rust-analyzer does not perform the FS op itself.
- **No `executeCommand`**: any "command" surfaced inside a `CodeAction.command` is client-side only. Ignore `command`; always prefer `edit`.
- **Custom methods are plain JSON-RPC**: wiring them through an MCP-to-LSP bridge requires the bridge to forward unknown methods verbatim, not restrict to a whitelist.

