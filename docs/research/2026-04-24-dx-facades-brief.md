# Specialist 4: DX / Facade Designer

**Mandate:** Design tools an LLM actually *wants* to call. One tool = one refactor as a human conceives it. No asking the LLM to orchestrate 14 LSP round-trips.

**Running scenario:** `crates/foo/src/massive.rs`, 1,200 lines, 40 `pub fn`, 10 `impl` blocks, 5 `struct`s, 3 `enum`s, tangled `use` statements, needs to become `massive/{types, api, internal, errors}.rs`.

---

## 1. Minimum Viable Facade Set

I argue for **six tools**, not five. Starting proposals are mostly right, but `preview_refactor` should not be a separate tool — it's a parameter. And we need one missing piece: `fix_imports_after_move`, because every other tool will leave broken `use` statements if we pretend rust-analyzer's auto-import always wins. It often doesn't for private items, `pub(crate)` items, and re-exports.

### 1.1 `plan_file_split` (read-only, non-mutating)

- **Purpose:** Analyze a file and propose a grouping of its top-level symbols into N submodules, based on call-graph clustering and type co-reference.
- **Inputs:**
  ```
  file: str                       # path relative to project root
  strategy: "by_visibility" | "by_cluster" | "by_type_affinity" = "by_cluster"
  max_groups: int = 5
  ```
- **Outputs:**
  ```
  {
    file: str,
    total_symbols: int,
    suggested_groups: [
      { module_name: str, rationale: str, symbols: [name_path] }
    ],
    unassigned: [name_path],        # symbols the planner couldn't cluster confidently
    cross_group_edges: [            # call/type edges that will become pub(crate) or re-exports
      { from: name_path, to: name_path, kind: "call"|"type_ref"|"trait_impl" }
    ],
    warnings: [str]
  }
  ```
- **Internally invokes:** `documentSymbol` + `callHierarchy/incomingCalls` for every top-level fn + `references` for every type. Builds a graph, runs a cheap community-detection pass (label propagation is enough; we're not publishing a paper).
- **Failure modes:** rust-analyzer not ready -> returns `warnings: ["indexing in progress, retry in ~Ns"]`, no partial plan. Never throws.

### 1.2 `split_file_by_symbols` (mutating, bulk)

- **Purpose:** Atomically split a file into N submodules given an explicit assignment map. This is the star of the show.
- **Inputs:**
  ```
  file: str
  parent_module_style: "dir" | "mod_rs" = "dir"   # foo.rs vs foo/mod.rs
  groups: { module_name: [name_path] }            # must cover all moved symbols
  keep_in_original: [name_path] = []              # symbols that stay in file
  dry_run: bool = false
  reexport_policy: "preserve_public_api" | "none" | "explicit_list" = "preserve_public_api"
  ```
- **Outputs:**
  ```
  {
    applied: bool,                 # false if dry_run or failure
    changes: [FileChange],         # list of {path, kind: create|modify|delete, hunks}
    moved_symbols: [{ name_path, from, to }],
    updated_references: int,       # call sites rewritten
    new_reexports: [ { path, item } ],
    diagnostics_delta: {           # rust-analyzer errors before vs. after
      before: int, after: int, new_errors: [Diagnostic]
    },
    checkpoint_id: str | null      # for rollback, null if dry_run
  }
  ```
- **Internally (in order):**
  1. `documentSymbol(file)` — verify every `name_path` resolves.
  2. For each group: create target file, insert `pub mod <name>;` in parent.
  3. For each symbol: `textDocument/prepareCallHierarchy` -> build reference inventory *before* moving.
  4. For each symbol: rust-analyzer `move_item` code action, or fallback to our own cut-paste if RA can't do it (trait impls are the trap).
  5. `workspace/executeCommand: rust-analyzer.reorderImports` on all touched files.
  6. Re-run our reference inventory; rewrite any `use` path that RA missed (the fix_imports sub-step).
  7. `textDocument/diagnostic` pass on all touched files; if new errors introduced, either rollback (atomic mode) or return them annotated.
- **Failure modes:** see §3.

### 1.3 `extract_symbols_to_module` (mutating, surgical)

- **Purpose:** The scalpel version. Move a small named set to one new module. Useful when the LLM already knows exactly what it wants.
- **Inputs:**
  ```
  file: str
  symbols: [name_path]
  new_module: str                   # "errors" or "nested::errors"
  dry_run: bool = false
  ```
- **Output:** same shape as `split_file_by_symbols` but simpler.
- **Internally:** same pipeline as §1.2 with `groups = { new_module: symbols }`. It's literally a thin wrapper — and that's fine. KISS: the LLM doesn't have to know it's a wrapper.

### 1.4 `move_inline_module_to_file` (mutating, narrow)

- **Purpose:** Promote `mod foo { ... }` in a file to its own `foo.rs`. Thin wrapper over RA's existing `move_module_to_file` assist.
- **Inputs:**
  ```
  file: str
  module_name: str
  target_style: "dir" | "mod_rs" = "dir"
  dry_run: bool = false
  ```
- **Output:** standard `FileChange[]` + `checkpoint_id`.
- **Internally:** one RA code action + one `reorderImports`. Tiny.

### 1.5 `fix_imports` (mutating, cleanup)

- **Purpose:** After any structural move — ours or rust-analyzer's — sweep a file or set of files and correct broken `use` paths, dedupe, reorder, promote privacy where needed.
- **Inputs:**
  ```
  files: [str]                      # or "**" for workspace
  add_missing: bool = true
  remove_unused: bool = true
  reorder: bool = true
  ```
- **Output:** `{ files_modified: int, imports_added: int, imports_removed: int, remaining_errors: [Diagnostic] }`
- **Internally:** RA `rust-analyzer.reorderImports` + our own unresolved-path walker that uses `workspace/symbol` to find the new home of moved items.

### 1.6 `rollback_refactor` (mutating, recovery)

- **Purpose:** Undo the last facade call by `checkpoint_id`.
- **Inputs:** `{ checkpoint_id: str }`
- **Output:** `{ restored_files: [str], ok: bool }`
- **Internally:** replay the inverse WorkspaceEdit we stored at apply-time (§3).

### What I dropped

- **`preview_refactor`** — redundant. `dry_run: bool` on each mutator is strictly better (§4).
- **A `merge_modules_to_file` tool** — YAGNI. The reverse direction isn't the 80% use case for file-splitting work.

---

## 2. Composition vs. Atomic Ops

**Position: facades are thick, but built from the same primitives the LLM can call directly. Not black-box.**

Two reasons:

1. **TRIZ segmentation.** The same primitive (`documentSymbol`, `references`, RA's `move_item`) is used by the planner, the splitter, and the fix-imports tool. Exposing them avoids duplicating orchestration logic and lets the LLM do the 20% of weird refactors we didn't facade.
2. **Debuggability.** When `split_file_by_symbols` fails, the LLM needs to fall back to calling `find_referencing_symbols` + `replace_symbol_body` directly (Serena's existing tools). If the facade were black-box, the LLM would be stuck.

**But** — the facades are *not* "the LLM calls 7 primitives in a sequence." The facade owns the transaction, the checkpoint, and the diagnostics delta. You can't recreate those by calling primitives one by one, and that's the point.

Rule of thumb: **facade = transaction boundary + intent naming + sensible defaults**. Primitive = single LSP round-trip.

---

## 3. Failure Recovery UX

Multi-step refactors fail. The question is whether the tool is *atomic* or *best-effort*.

**My position: atomic by default, `allow_partial: bool = false` opt-in for power users.**

Mechanism:

- Before any mutation, facade captures a **checkpoint**: `{checkpoint_id, inverse_edit: WorkspaceEdit, file_snapshots: {path: content_hash}}`. Stored in an in-memory LRU + spilled to `.serena/checkpoints/`.
- During apply: if any step fails **or** if `diagnostics_delta.new_errors > 0` in strict mode, facade applies the inverse edit and returns:
  ```
  {
    applied: false,
    failure: {
      stage: "move_symbol" | "rewrite_refs" | "diagnostics_check",
      symbol: name_path | null,
      reason: str,
      recoverable: bool
    },
    checkpoint_id: str,     # still valid, file state == pre-call state
    suggested_action: str   # "retry with allow_partial=true" | "run plan_file_split first" | ...
  }
  ```
- With `allow_partial: true`: the tool commits what succeeded, returns a `resume_token` and the list of unfinished items. The LLM can call the tool again with `resume_from: token`.

**Why atomic default:** LLMs are bad at cleanup. A half-moved symbol with dangling references is worse than no move. The "frustrations: regression" directive in the global profile says it outright — don't create regression hazards.

---

## 4. Preview / Confirm Flow

**`dry_run: bool` on every mutator. No separate `preview_*` variant.**

Why:

- **One surface area.** LLM learns one tool shape. `preview_X` doubles the tool catalog and invites drift ("why does `preview_split` return `suggested_groups` but `split` returns `moved_symbols`?").
- **Same output schema.** `dry_run=true` returns exactly what `dry_run=false` would have returned, except `applied: false` and `checkpoint_id: null`. The LLM inspects `changes` and `diagnostics_delta.new_errors`. If good, it flips the flag and re-calls.
- **Agent workflow fit.** Claude/GPT agents love "show me what you'd do, then do it." A single parameter matches that loop.

`plan_file_split` stays as its own tool because it does *more* than a dry-run split — it proposes the groups in the first place. That's planning, not previewing.

---

## 5. Symbol Name-Paths vs. Byte Ranges

**Rule: accept name-paths at the facade boundary. Convert to ranges internally.**

Serena's name-path system (`foo::Bar::method`) is:
- Stable across whitespace/formatting changes.
- What the LLM already sees in `documentSymbol` output.
- Trivially unambiguous within a file (RA gives us the position).

Byte ranges leak into the API in exactly one case: **selections inside a function body** (e.g., extracting an expression to a variable). That's not our use case here — file-splitting works at top-level granularity. So **no byte ranges in the six tools above**.

If we ever add `extract_expression_to_variable`, it takes `{file, range}`. That's a deliberate boundary, not accidental.

---

## 6. Naming Convention

Serena uses `verb_noun_qualifier`: `replace_symbol_body`, `find_referencing_symbols`, `insert_after_symbol`. The new tools should match:

| New tool                        | Pattern fit                              |
|---------------------------------|------------------------------------------|
| `plan_file_split`               | verb_object_qualifier                    |
| `split_file_by_symbols`         | verb_object_by_dimension                 |
| `extract_symbols_to_module`     | verb_object_to_destination               |
| `move_inline_module_to_file`    | verb_object_to_destination               |
| `fix_imports`                   | verb_object                              |
| `rollback_refactor`             | verb_object                              |

Consistent. No tool says `do_X` or `X_helper`. No `symbol` where we mean `module`. The verbs cluster around a small vocabulary: `plan / split / extract / move / fix / rollback`.

---

## 7. Hallucination Resistance

LLMs will pass `foo::Bar::do_thing` when the actual path is `foo::bar::do_thing` (case drift) or `Bar::do_thing` (scope drop).

**Strategy: fuzz-match on input, fail-loud on ambiguity.**

- Normalize case-insensitively and try exact match first, then case-insensitive, then `ends_with` match against the file's `documentSymbol` tree.
- If exactly one match: proceed, note the correction in the response (`resolved_symbols: [{requested, resolved}]`).
- If zero or >1 matches: **fail immediately** with:
  ```
  {
    error: "symbol_not_found" | "ambiguous_symbol",
    requested: "Bar::do_thing",
    candidates: ["foo::bar::do_thing", "foo::Baz::do_thing"],
    hint: "did you mean 'foo::bar::do_thing'?"
  }
  ```

Never silently pick one. The cclsp "just find something that sort of matches" approach is a regression hazard. One correction level (case/scope) is pragmatic; free-form fuzzy matching on function names is a foot-gun.

---

## 8. Idempotency & Re-entrancy

- `plan_file_split`: pure, idempotent by definition.
- `split_file_by_symbols`: **not naturally idempotent** (second call finds the symbols already moved). Make it so by: (a) if every symbol in `groups` is already at its target location, return `{applied: true, changes: [], no_op: true}` instead of erroring. (b) if *some* are already moved and others not, treat the moved ones as no-ops and proceed on the rest.
- `extract_symbols_to_module`: same rule.
- `move_inline_module_to_file`: second call returns `{applied: true, no_op: true}` because the inline module no longer exists.
- `fix_imports`: naturally idempotent.
- `rollback_refactor`: rolling back twice must be a no-op; checkpoint is consumed on first rollback.

**Rename-during-move is out of scope.** If the LLM renamed a symbol between calls, the second call gets `symbol_not_found` with candidates. Don't try to auto-match across renames; that's hallucination-resistance territory and needs explicit intent.

---

## 9. Observability

Every facade response includes:

```
{
  tool: str,
  duration_ms: int,
  lsp_ops: [{ method: str, count: int, total_ms: int }],
  rust_analyzer_ready: bool,
  diagnostics_delta: { before: int, after: int, new_errors: [Diagnostic] },
  resolved_symbols: [{ requested: str, resolved: name_path }],
  warnings: [str]
}
```

Why: when the LLM plans its next turn, it should see *what it cost*, *what the compiler thinks now*, and *whether the server is warm*. `diagnostics_delta` is the single most important field — it tells the LLM whether it just broke the build.

---

## Formal Signatures (Python, Pydantic-style)

```python
class FileChange(BaseModel):
    path: str
    kind: Literal["create", "modify", "delete"]
    hunks: list[Hunk]                      # unified-diff-ish

class DiagnosticsDelta(BaseModel):
    before: int
    after: int
    new_errors: list[Diagnostic]

class RefactorResult(BaseModel):
    applied: bool
    changes: list[FileChange]
    diagnostics_delta: DiagnosticsDelta
    checkpoint_id: str | None
    resolved_symbols: list[ResolvedSymbol]
    warnings: list[str]
    failure: FailureInfo | None = None

def plan_file_split(
    file: str,
    strategy: Literal["by_visibility", "by_cluster", "by_type_affinity"] = "by_cluster",
    max_groups: int = 5,
) -> PlanResult: ...

def split_file_by_symbols(
    file: str,
    groups: dict[str, list[str]],           # {module_name: [name_path]}
    parent_module_style: Literal["dir", "mod_rs"] = "dir",
    keep_in_original: list[str] = [],
    reexport_policy: Literal["preserve_public_api", "none", "explicit_list"] = "preserve_public_api",
    allow_partial: bool = False,
    dry_run: bool = False,
) -> RefactorResult: ...

def extract_symbols_to_module(
    file: str,
    symbols: list[str],
    new_module: str,
    dry_run: bool = False,
) -> RefactorResult: ...

def move_inline_module_to_file(
    file: str,
    module_name: str,
    target_style: Literal["dir", "mod_rs"] = "dir",
    dry_run: bool = False,
) -> RefactorResult: ...

def fix_imports(
    files: list[str],
    add_missing: bool = True,
    remove_unused: bool = True,
    reorder: bool = True,
) -> RefactorResult: ...

def rollback_refactor(checkpoint_id: str) -> RefactorResult: ...
```

---

## Worked Example: Splitting `crates/foo/src/massive.rs`

LLM call sequence — 4 tool calls total, not 40:

**Call 1 — understand the file:**
```json
{"tool": "plan_file_split",
 "args": {"file": "crates/foo/src/massive.rs", "strategy": "by_cluster", "max_groups": 4}}
```
Response proposes `{types, api, internal, errors}` with 38 of 48 top-level items assigned, 10 unassigned (cross-cutting helpers), and 23 cross-group edges flagged.

**Call 2 — dry-run the split:**
```json
{"tool": "split_file_by_symbols",
 "args": {
   "file": "crates/foo/src/massive.rs",
   "groups": {
     "types":    ["Config", "Session", "Request", "Response", "ErrorKind"],
     "errors":   ["AppError", "from_io", "from_parse"],
     "api":      ["handle_request", "serve", "shutdown", "..." ],
     "internal": ["cache_lookup", "dispatch", "..." ]
   },
   "keep_in_original": ["init", "VERSION"],
   "parent_module_style": "dir",
   "reexport_policy": "preserve_public_api",
   "dry_run": true
 }}
```
Response: `applied: false`, 5 `FileChange` entries, `diagnostics_delta: {before: 0, after: 2, new_errors: [...]}`. LLM sees two new errors — `cache_lookup` is called from `api::handle_request` but is private in `internal`.

**Call 3 — adjust and commit.** LLM either (a) moves `cache_lookup` to `api`, or (b) adds it to `reexport_policy: "explicit_list"`. Picks (b), flips `dry_run: false`:
```json
{"tool": "split_file_by_symbols",
 "args": {"...": "...",
          "reexport_policy": "explicit_list",
          "explicit_reexports": ["internal::cache_lookup"],
          "dry_run": false}}
```
Response: `applied: true`, `checkpoint_id: "ckpt_7a3f"`, `diagnostics_delta: {before: 0, after: 0}`. Done.

**Call 4 — tidy imports across the crate:**
```json
{"tool": "fix_imports", "args": {"files": ["crates/foo/src/**"]}}
```

Four calls. Zero range arithmetic. Zero manual `use` surgery. Atomic with rollback available via `ckpt_7a3f`.

---

**Bottom line:** Six tools, name-paths everywhere, `dry_run` on mutators, atomic-by-default with opt-in partial, fail-loud with candidates on ambiguity, and always return a `diagnostics_delta` so the LLM knows whether it just broke the build. This is what a refactor API feels like when it's designed for an agent, not a human clicking through VS Code menus.
