# MCP ↔ LSP Protocol Guide: rust-analyzer Refactorings via Serena

Specialist 3 — tactical implementer's reference. Assumes Serena wraps `multilspy`, which already owns a JSON-RPC LSP channel to `rust-analyzer`.

---

## 1. `textDocument/codeAction` flow

### 1.1 Request shape

```jsonc
{
  "jsonrpc": "2.0", "id": N, "method": "textDocument/codeAction",
  "params": {
    "textDocument": { "uri": "file:///abs/path/src/foo.rs" },
    "range": { "start": {"line": L, "character": C},
               "end":   {"line": L, "character": C} },
    "context": {
      "diagnostics": [ /* optional; relevant diagnostics for quickfix binding */ ],
      "only":        [ "refactor.extract", "refactor.extract.module" ],
      "triggerKind": 1  // 1=Invoked (user/tool), 2=Automatic
    }
  }
}
```

- `range` may be zero-width (cursor position) or a selection. For rust-analyzer, most assists key off cursor position; extract-module/extract-function require a selection.
- `context.only` is a **hierarchical filter**: `"refactor"` matches `refactor.extract`, `refactor.extract.module`, etc. Use it aggressively — it tells the server to skip computing irrelevant actions and dramatically reduces latency on large files.
- `context.diagnostics` is required when requesting `quickfix` actions that bind to a specific diagnostic (e.g., unresolved-import auto-import).

### 1.2 Response

`Array<Command | CodeAction>` or `null`.

```jsonc
{
  "title":  "Extract into module",
  "kind":   "refactor.extract.module",
  "edit":   null,                 // may be absent → needs resolve
  "command": null,                // or present for Command-style actions
  "data":   { /* opaque server state */ },
  "isPreferred": false,
  "disabled": { "reason": "..." } // if server says "don't run this"
}
```

- Never execute a `disabled` action — show `disabled.reason` as error.
- If both `edit` and `command` are present, LSP spec says apply `edit` **first**, then execute `command`.

### 1.3 Two-phase resolution

rust-analyzer returns a *lightweight* list (titles + kinds + `data` blobs, no `edit`). You must call:

```jsonc
{
  "method": "codeAction/resolve",
  "params": { /* the entire CodeAction object you picked, unchanged */ }
}
```

Response echoes the action with `edit` (a `WorkspaceEdit`) populated. Do **not** mutate the `data` field between list and resolve — it's opaque server state keyed to the file version.

### 1.4 Kind discrimination

Filter by prefix match (LSP spec §Code Action Kinds):

| Kind prefix | r-a examples |
|---|---|
| `quickfix` | add missing import, fix typo |
| `refactor.extract` | extract function, variable, module |
| `refactor.inline` | inline function, inline variable |
| `refactor.rewrite` | convert `if let` to `match`, flip binexpr |
| `source.organizeImports` | sort/merge imports |

### 1.5 Capability negotiation

At `initialize`, check server's `capabilities.codeActionProvider`:

```jsonc
{
  "codeActionProvider": {
    "codeActionKinds": ["quickfix", "refactor", "refactor.extract", ...],
    "resolveProvider": true   // CRITICAL — must be true to call codeAction/resolve
  }
}
```

If `codeActionProvider` is a plain `true` (no object), assume no kind filter and no resolve. rust-analyzer always returns the object form with `resolveProvider: true`.

---

## 2. `WorkspaceEdit` application semantics

### 2.1 Two shapes

```jsonc
"edit": {
  "changes":         { "file:///a.rs": [TextEdit, ...] },   // legacy, no versioning
  "documentChanges": [ TextDocumentEdit | CreateFile | RenameFile | DeleteFile, ...]
}
```

Prefer `documentChanges` — it's version-aware and supports file operations, which rust-analyzer **requires** for extract-module-to-file (it emits `CreateFile` + `TextDocumentEdit` + edits to parent).

### 2.2 TextDocumentEdit versioning

```jsonc
{ "textDocument": { "uri": "...", "version": 42 }, "edits": [TextEdit, ...] }
```

If `version` doesn't match the client's tracked version, **reject the edit**. Stale edit ⇒ re-request codeAction with fresh version. rust-analyzer is unforgiving here; it will compute offsets against the version it last saw via `didOpen`/`didChange`.

### 2.3 Ordering

- `documentChanges` operations **apply in array order**. Spec §3.16.
- Inside a single `TextDocumentEdit`, `edits` array is applied as if simultaneous — offsets are all relative to the pre-edit document. Serena must sort descending by `start` offset before applying to a string buffer to avoid offset drift. (`multilspy`/VS Code do this internally.)
- `CreateFile` must come before any `TextDocumentEdit` targeting that file.

### 2.4 Atomicity strategy

LSP gives zero atomicity guarantees. Options: (1) stage-to-temp + atomic `rename`; (2) require clean git tree + `checkout --` rollback; (3) in-memory snapshot + rewrite originals on failure.

**Recommended**: require clean git state; apply in array order with per-file snapshot buffer; on any `IOError`/version mismatch, restore snapshots. Fail loudly.

### 2.5 Version check

Before applying, call `textDocument/didSave` or confirm no pending `didChange` is in flight. If Serena isn't a live editor, it should hold the canonical buffer and push `didChange` synchronously before requesting code actions.

### 2.6 `changeAnnotations`

```jsonc
"changeAnnotations": {
  "delete-imports": { "label": "Remove unused imports", "needsConfirmation": true }
}
```

Each TextEdit/file op can carry `annotationId`. Groups edits for user confirmation. For an MCP tool, surface annotations in the dry-run preview; default to applying all unless the LLM selects a subset.

---

## 3. `workspace/executeCommand`

When a `CodeAction` has `command` instead of `edit` (rust-analyzer does this for assists that need server-side computation post-user-input, e.g. some import inserts):

```jsonc
{ "method": "workspace/executeCommand",
  "params": { "command": "rust-analyzer.applySnippetWorkspaceEdit",
              "arguments": [...] } }
```

The server processes it and sends a **reverse request** (§4) back to the client to apply the resulting edit. The client's response to `executeCommand` is whatever the command returns (often `null`).

Commands relevant to refactor: `rust-analyzer.applySnippetWorkspaceEdit`. Others (`showReferences`, `runSingle`, `gotoLocation`) are not edit-bearing.

---

## 4. `workspace/applyEdit` reverse request

Server → client, method `workspace/applyEdit`. Client must implement the handler:

```jsonc
// server sends:
{ "method": "workspace/applyEdit",
  "params": { "label": "Extract into module", "edit": WorkspaceEdit } }

// client responds:
{ "result": { "applied": true, "failureReason": null, "failedChange": 0 } }
```

### How multilspy handles it today

`multilspy`'s base `LanguageServer` registers request handlers via its JSON-RPC shim. Current upstream (as of ~0.0.x) has a default `workspace/applyEdit` handler that **returns `{applied: false}`** — i.e. edits from commands are silently dropped. Serena should:

1. Override the handler at `LanguageServer.__init__`-time registration.
2. Delegate to the same WorkspaceEdit-applier used for `codeAction.edit`.
3. Respond `{applied: true}` only if all edits succeeded; otherwise `{applied: false, failedChange: <index>, failureReason: "..."}`.

Verify this in `serena/src/solidlsp/` before building — the handler hook may already exist under a different name.

---

## 5. MCP tool design for 2-phase LSP operations

- **Option A — monolithic** `apply_code_action(file, range, kind_prefix, title_match?)`: list→filter→resolve→apply in one call. Brittle (r-a title changes), poor recovery on `disabled` actions.
- **Option B — two-tool** `list_code_actions` + `apply_code_action_by_id`: UUID-keyed session cache with ~60s TTL (since `data` is version-sensitive). Best error recovery; two LLM turns; stale-ID footgun.
- **Option C — facades**: `extract_to_module(file, range, new_name)` etc. Each facade internally does list+resolve+apply with a hardcoded `kind_prefix`. Matches LLM intent; requires one tool per refactor.

**Recommended: C on top of B.** Facades for the top refactors (see §9), generic 2-tool pair as escape hatch. Skip A — it hides ambiguity LLMs need to see.

---

## 6. Multi-step "split file" orchestration

Goal: take `big.rs`, peel off a region into `submodule.rs`, wire up `mod submodule;`.

rust-analyzer offers two assists:
- `refactor.extract.module` — in-file extract (creates `mod foo { ... }` block)
- **`move_module_to_file`** — companion assist that moves an inline `mod foo { ... }` to `foo.rs`

Sequence:

1. Client sends `textDocument/didChange` with current buffer (ensure version is fresh).
2. `codeAction` on selection, `only: ["refactor.extract.module"]`.
3. Pick action, `codeAction/resolve`, apply the returned `WorkspaceEdit`. File now contains `mod <auto_name> { ... }`.
4. Compute the range of the newly inserted `mod` keyword (from the applied TextEdit), send `didChange`.
5. `codeAction` on that position, `only: ["refactor.extract"]`, pick the `move_module_to_file` action.
6. Resolve + apply. Produces `CreateFile` for `<auto_name>.rs` + edits to parent.
7. Optional: `textDocument/rename` on `<auto_name>` to the caller-supplied `new_name`.

### Chaining limitation

LSP has **no concept of dependent code actions**. Each round-trip is isolated, keyed to a document version. Serena must:
- Re-push `didChange` between steps.
- Re-derive target ranges from the previous edit's result, not from pre-edit offsets.

### Error modes

- **Stale version**: resolve returns edit against version N, but client is at N+1 → reject, reissue codeAction from step 2.
- **Assist no longer applicable** (e.g. after extract-module, move-module-to-file might not trigger because cursor position is off): recompute position from the parent file's post-edit text.
- **Cargo workspace refresh**: after `CreateFile`, rust-analyzer needs to re-read `Cargo.toml` / `mod.rs` topology. It does this via file-watcher, but there's a debounce (default ~300ms). Send `workspace/didChangeWatchedFiles` for the new file, then sleep 500ms before next assist, or poll `$/progress` for the `rustAnalyzer/Indexing` token to clear.

---

## 7. Dry-run / preview

LSP has **no native dry-run flag**. But the two-phase design gives it to you for free:

- Call `codeAction` + `codeAction/resolve` → you hold the `WorkspaceEdit` object.
- Do **not** apply it. Instead, serialize it to a unified diff and return to caller.
- Cache the `WorkspaceEdit` under a preview ID.
- Second MCP call `confirm_edit(preview_id)` applies it.

Preview IDs expire when any `didChange` touches an affected file (invalidates the WorkspaceEdit's baseline versions).

This is a tiny wrapper — no LSP extensions needed.

---

## 8. Cancellation & timeouts

### 8.1 LSP cancellation

```jsonc
{ "method": "$/cancelRequest", "params": { "id": <original_request_id> } }
```

Server responds to the cancelled request with error `code: -32800` (`RequestCancelled`). rust-analyzer honors this.

### 8.2 rust-analyzer indexing

On startup / `Cargo.toml` change / large file creates, r-a indexes. During indexing:
- Most requests return empty results or `ContentModified` (`-32801`).
- Progress is reported via `$/progress` notifications with token `rustAnalyzer/Indexing`.

Implementer **must**:
- Wait for `{kind: "end"}` on the `rustAnalyzer/Indexing` token before firing codeAction on a freshly-loaded workspace.
- Retry once on `ContentModified`.
- Set per-request timeout to 30s for codeAction, 60s for resolve (extract-module can be slow on large files), infinite for initial index (report progress to MCP caller).

---

## 9. Recommended MCP tool surface

Python-style signatures. All tools return dicts; errors raise `McpError` with a structured `code`.

```python
# --- generic 2-phase escape hatch ---

def list_code_actions(
    file: str,                            # absolute path
    range: Range,                         # {"start": {"line","character"}, "end": ...}
    kinds: list[str] | None = None,       # e.g. ["refactor.extract", "quickfix"]
) -> list[CodeActionDescriptor]:
    """
    Returns: [{"id": str, "title": str, "kind": str,
               "disabled_reason": str | None, "is_preferred": bool}]
    IDs live for 60s or until file version changes.
    """

def preview_code_action(id: str) -> Preview:
    """
    Returns: {"preview_id": str, "diff": str (unified),
              "affected_files": [str], "creates": [str], "deletes": [str]}
    """

def apply_code_action(id_or_preview_id: str) -> ApplyResult:
    """
    Returns: {"applied": bool, "affected_files": [str],
              "created_files": [str], "errors": [str]}
    Rolls back on partial failure.
    """

# --- high-level facades ---

def extract_to_new_module(
    file: str, range: Range, new_module_name: str,
    dry_run: bool = False,
) -> ApplyResult | Preview:
    """
    Composes: extract-module → move-module-to-file → rename.
    """

def extract_to_function(file: str, range: Range, new_name: str, dry_run: bool = False): ...
def extract_to_variable(file: str, range: Range, new_name: str, dry_run: bool = False): ...
def inline_symbol(file: str, position: Position, dry_run: bool = False): ...
def rename_symbol(file: str, position: Position, new_name: str, dry_run: bool = False):
    """Uses textDocument/rename (NOT codeAction). Returns same ApplyResult shape."""

def organize_imports(file: str, dry_run: bool = False): ...

# --- safety / orchestration ---

def wait_for_indexing(timeout_s: float = 120) -> {"ready": bool, "progress": str | None}
def workspace_health() -> {"cargo_ok": bool, "diagnostics_count": int, "indexing": bool}
```

### Error code contract

| `code` | Meaning |
|---|---|
| `STALE_VERSION` | File changed between list and apply — re-list |
| `ASSIST_DISABLED` | Server returned `disabled.reason` |
| `NOT_APPLICABLE` | No action matched `kinds` at `range` |
| `INDEXING` | rust-analyzer still indexing; call `wait_for_indexing` |
| `APPLY_FAILED` | WorkspaceEdit application errored; rolled back |
| `PREVIEW_EXPIRED` | `preview_id` past TTL or invalidated by edit |

### What **not** to expose

- Raw `WorkspaceEdit` JSON — LLM will hallucinate edits.
- `executeCommand` passthrough — too sharp.
- Direct `codeAction/resolve` — only meaningful paired with list+apply.

---

### Implementer's shortlist

1. Verify `multilspy` has a `workspace/applyEdit` handler; replace if it's a no-op stub.
2. Build a `WorkspaceEditApplier` with snapshot-based rollback.
3. Implement `list → preview → apply` session with TTL'd IDs.
4. Wrap top refactors (extract module, extract function, inline, rename, organize imports) as facades.
5. Handle `$/progress` `rustAnalyzer/Indexing` token before first call per session.
6. Test with a fixture: `big.rs` (500+ lines) → extract three modules → build passes.
