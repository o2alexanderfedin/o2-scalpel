# MVP Agent/UX Specialist — o2.scalpel LLM-facing Tool Surface

**Specialist role:** Agentic-AI UX / MCP surface.
**Scope:** What the LLM caller actually sees. Tool shapes, names, error taxonomy, dry-run contract, rollback UX, hallucination safety net, docstrings, cross-language flag strategy, observability.
**Audience:** orchestrator + downstream implementers wiring the MVP MCP server.
**Status:** report-only. No code written.
**Date:** 2026-04-24.
**MVP languages:** Rust AND Python (single tool surface drives both).

Cross-reference:
- [main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — §3 facades, §Workflow, §Gap 4, §Risks, Appendix C.
- [open-questions-resolution](../2026-04-24-o2-scalpel-open-questions-resolution.md) — §Q12 on per-language flags.
- [dx-facades-brief](../../research/2026-04-24-dx-facades-brief.md) — upstream facade rationale.
- [mcp-lsp-protocol-brief](../../research/2026-04-24-mcp-lsp-protocol-brief.md) — error codes, two-phase resolve.
- [plugin-extension-surface-brief](../../research/2026-04-24-plugin-extension-surface-brief.md) — MCP namespacing.

---

## 0. Executive summary (for humans skimming)

The MVP tool surface collapses from 10 (6 facades + 4 primitives) to **5**: **3 facades** (`plan_split`, `split_file`, `fix_imports`) plus **2 primitives** (`apply_code_action`, `rollback`). That set delivers the 5-turn split-file workflow end-to-end on Rust and Python. `extract_symbols_to_module`, `move_inline_module_to_file`, `list_code_actions`, `resolve_code_action`, `execute_command` all ship in v1.1. Naming drops the `mcp__o2-scalpel__` prefix load on the LLM by keeping verbs short and distinctive from Claude Code's read-only `LSP` umbrella. Error taxonomy shrinks from 8 codes to **5 essential** + 3 deferred; every essential code gets a one-line LLM-facing recovery pattern. `dry_run=True` returns a byte-identical `changes` payload with `applied=false` and a short-lived `preview_token` — not a `checkpoint_id` — whose invalidation contract is explicit. `split_file(dry_run=True)` absorbs `plan_file_split`'s read-only role for MVP, because the single-tool story wins on token budget and LLM-selection clarity; `plan_file_split` returns as a separate tool in v1.1 when the heuristic planner earns its keep. Cross-language goes **same name, language-tagged flags**: the target language is inferred from the file path, and language-specific parameters live under a `language_options` nested field prefixed with the language key (`rust:`, `py:`). Observability keeps `lsp_ops`, `duration_ms`, `warnings`, adds `indexing_ready: bool` and `rule_fired: str[]` so the LLM can learn what worked.

Three MVP facade docstrings are written in §8, each under 90 words, each disambiguating from CC's `LSP` tool.

---

## 1. Minimum viable tool surface for MVP

### 1.1 The question

The main design ships 6 facades + 4 primitives — 10 tools. Can we deliver the 5-turn split-file workflow with less? The workflow (from main design §Workflow) is:

1. Plan file split.
2. Dry-run the split.
3. Adjust and commit.
4. Tidy imports.
5. Verify (external `cargo check` / `pytest`) or rollback.

Turns 1, 2, 3 all touch the same file-splitting intent. Turn 4 is cleanup. Turn 5 is recovery.

### 1.2 Rank-ordering all 10 tools

One pass through the 10, ranked by marginal contribution to the MVP happy path:

| Rank | Tool | Why the LLM calls it | MVP verdict |
|-----:|------|-----------------------|-------------|
| 1 | `split_file_by_symbols` | Star of the show — does turns 2 and 3 (dry-run + commit). Without it, there is no product. | **P0 — ship** |
| 2 | `fix_imports` | Turn 4. Without it, every split leaves dangling `use` / `import` statements. High-ROI cleanup the LLM can't easily improvise. | **P0 — ship** |
| 3 | `rollback_refactor` | Recovery path. Makes the whole product safe-to-try. Tiny, stateless-for-the-LLM, high-trust win. | **P0 — ship** |
| 4 | `plan_file_split` | Turn 1. **But** absorbable into `split_file(dry_run=True)` for MVP — see §6. Independent planner ships v1.1 when the clustering heuristic earns its keep against simple "ask the LLM to propose groups" baseline. | **P1 — defer** |
| 5 | `apply_code_action` (primitive) | Escape hatch. When a facade fails or the LLM wants a single rust-analyzer/pyright assist (e.g., "inline this variable"), this is the answer. Pair with one `list_code_actions` call the facade can emit inline in its error response. | **P0 — ship** (as minimal primitive pair with resolve folded in) |
| 6 | `extract_symbols_to_module` | Thin wrapper over `split_file_by_symbols` with `groups = {new_module: symbols}`. KISS says: don't ship a wrapper if the facade takes the same work in 3 extra keystrokes. | **P1 — defer** |
| 7 | `list_code_actions` (primitive) | Needed to obtain the `id` that `apply_code_action` consumes. For MVP, fold "list + resolve + apply" into a single `apply_code_action(file, range, kind)` call; expose two-step separately in v1.1 when the LLM needs to inspect alternatives. | **P1 — defer** (merged into `apply_code_action` for MVP) |
| 8 | `move_inline_module_to_file` | Narrow. Rust-specific (`mod foo {}` → `foo.rs`). Python has no equivalent. YAGNI for MVP; the LLM can hand-edit or use `split_file` with a one-element group. | **P2 — defer** |
| 9 | `resolve_code_action` (primitive) | Only useful in a two-phase list→resolve→apply exposed to the LLM. MVP merges the three; this tool re-emerges in v1.1 when the LLM needs to hold a `WorkspaceEdit` preview across turns. | **P2 — defer** |
| 10 | `execute_command` (primitive) | Pass-through to server-specific JSON-RPC (`rust-analyzer/runFlycheck`, `experimental/ssr`). Advanced escape hatch. Not on the critical path; ship when a real user asks. | **P2 — defer** |

### 1.3 Resulting MVP surface (5 tools)

| Tool | Shape | Notes |
|------|------|-------|
| `plan_split` | read-only (absorbed into `split_file(dry_run=True)`) | Not a separate tool in MVP. See §6. |
| `split_file` | facade, mutating | P0. Dry-run + commit in one tool. Turns 2+3 (and turn 1 via dry-run). |
| `fix_imports` | facade, mutating | P0. Turn 4. |
| `apply_code_action` | primitive, mutating | P0. Escape hatch. Bundles list+resolve+apply for MVP. |
| `rollback` | primitive, mutating | P0. Recovery. |

Four calls on the happy path (`split_file(dry_run=True)` → `split_file(dry_run=False)` → `fix_imports` → verify-externally) — still the 5-turn workflow, one turn shorter because planning rides inside the dry-run. Rollback is a 5th turn only if something fails.

### 1.4 "Aha" moment vs. v1.1

**MVP aha moment:** user asks the agent to "split `calcrs/src/lib.rs` into ast, parser, eval, errors modules." Agent calls 3 tools, shows a diff, commits, runs `cargo check`, done. Same user asks the same agent to "split `myapp/processor.py` into three modules by concern." Same 3 tools. Same diff-shape output. Aha.

**v1.1 adds:** the dedicated planner (`plan_split`) once we have evidence that LLMs misgroup without help; the surgical `extract_symbols_to_module` wrapper; the explicit two-phase code-action loop; the Rust-specific `move_inline_module_to_file`; the `execute_command` escape hatch.

**TRIZ segmentation note.** The same primitive (WorkspaceEdit applier + checkpoint store) backs every tool. Dropping tools doesn't shrink the implementation engine; it shrinks only the LLM-facing surface area. This is pure YAGNI on the tool list, not on the system.

---

## 2. Tool naming and namespace

### 2.1 The problem

`mcp__o2-scalpel__split_file_by_symbols` is 35 characters. MCP namespacing is non-negotiable (`mcp__<server>__<tool>` from [plugins-reference](https://code.claude.com/docs/en/plugins-reference#mcp-servers)). The tool name after the double-underscores is all we control. Claude Code ships its own `LSP` umbrella tool with 9 read-only operations; if our names overlap, the LLM routes wrong.

### 2.2 Constraints

- **Unique verbs vs. CC's `LSP`.** CC's tool uses LSP-protocol method names (`definition`, `references`, `hover`, `documentSymbol`, etc.). Our tools should use refactor-intent verbs (`split`, `fix`, `rollback`) not LSP method names. That distinction is the LLM's disambiguation signal.
- **Token cost.** Every tool name appears in the LLM's tool-selection prompt once, typically tokenized as 1 token per ~4 chars. `split_file_by_symbols` = ~6 tokens; `split_file` = ~3. Across 5 tools, the compression buys ~15 tokens per turn, which is peanuts — but across 1000 users × 10 turns × 30 sessions/day, compounds. Favor short when unambiguous.
- **Collision with the LLM's imagination.** Verbs like `move` or `refactor` are too generic; the LLM will try to call them for things we don't support. Verbs like `split_file` or `fix_imports` are narrow enough to self-document.
- **Same shape per language.** MVP covers Rust and Python. Tool name MUST NOT include the language (`split_rust_file` is wrong — forces doubled tool count).

### 2.3 Recommended convention: `<verb>[_<object>]`

| MVP tool | Design name | MVP name (recommended) | Δ tokens |
|----------|-------------|-------------------------|---------:|
| Plan split | `plan_file_split` | (absorbed into `split_file` dry-run for MVP; exposed as `plan_split` in v1.1) | — |
| Split file | `split_file_by_symbols` | `split_file` | −4 |
| Fix imports | `fix_imports` | `fix_imports` | 0 |
| Rollback | `rollback_refactor` | `rollback` | −2 |
| Apply code action | `apply_code_action` | `apply_code_action` | 0 |

v1.1 additions follow the same pattern:

| v1.1 tool | Name |
|-----------|------|
| Dedicated planner | `plan_split` |
| Surgical extract | `extract_to_module` |
| Inline-module promotion | `promote_inline_module` (Rust-only; Python gets no-op) |
| List code actions | `list_code_actions` |
| Resolve code action | `resolve_code_action` |
| Execute server command | `execute_command` |

### 2.4 Why not use `scalpel_*` prefix inside the namespace

Option considered: `mcp__o2-scalpel__scalpel_split_file` — redundant and double-negatives the namespace. Rejected.

### 2.5 Anti-collision test

Hypothetical LLM prompt: "use the LSP tool to find references of `foo::Bar::baz` and then split the file that defines it." With our names:

- `mcp__claude-code-lsp__references` (CC's built-in) — clearly read-only.
- `mcp__o2-scalpel__split_file` — clearly write-intent, distinct vocabulary.

LLM confusability: low. If we named ours `refactor_file` or `code_action`, the overlap with CC's ecosystem would degrade tool-selection accuracy.

### 2.6 The `mcp__o2-scalpel__` prefix itself

Not ours to shorten — MCP hard-codes the shape. But: the server name `o2-scalpel` is 10 characters, which dominates the prefix. Changing to `o2s` or `scalpel` shaves ~7 characters per tool call. **Recommendation:** keep `o2-scalpel` in the `.mcp.json` server name for brand clarity (per Q11 resolution, the marketplace is `o2alexanderfedin/claude-code-plugins`). The token cost is real but small; brand continuity wins at this stage.

---

## 3. Error-code taxonomy for MVP

### 3.1 The 8 design-doc codes

From main design §2 primitive tools + Specialist 4 §7:

| Code | Origin | MVP verdict |
|------|--------|-------------|
| `STALE_VERSION` | LSP document version drift (Gap 4) | **Essential — P0** |
| `ASSIST_DISABLED` | Server returned `disabled.reason` | **P1 — defer**, fold into `NOT_APPLICABLE` |
| `NOT_APPLICABLE` | No action matched `kinds` at `range` | **Essential — P0** |
| `INDEXING` | rust-analyzer / pyright still indexing | **Essential — P0** |
| `APPLY_FAILED` | WorkspaceEdit apply errored, rolled back | **Essential — P0** |
| `PREVIEW_EXPIRED` | Dry-run `preview_token` past TTL | **Essential — P0** (for dry-run UX) |
| `AMBIGUOUS_SYMBOL` | Name-path matched >1 candidate | **Essential — P0** (see §7) |
| `SYMBOL_NOT_FOUND` | Name-path matched 0 candidates | **Essential — P0** (see §7) |

### 3.2 MVP set: 6 essential codes, 2 deferred

The MVP ships **6**: `STALE_VERSION`, `NOT_APPLICABLE`, `INDEXING`, `APPLY_FAILED`, `PREVIEW_EXPIRED`, `AMBIGUOUS_SYMBOL`, `SYMBOL_NOT_FOUND` — yes that's 7; `ASSIST_DISABLED` and one more collapse. Final count:

1. `STALE_VERSION`
2. `NOT_APPLICABLE` (absorbs `ASSIST_DISABLED`)
3. `INDEXING`
4. `APPLY_FAILED`
5. `PREVIEW_EXPIRED`
6. `SYMBOL_NOT_FOUND` (ambiguous vs. not-found are sibling shapes — same recovery path, differing only by candidate count; collapse to one code + `candidates[]`)

That's **6 codes**. Ship. Defer the split between ambiguous and not-found to v1.1 if telemetry shows LLMs want different recovery (early evidence says no: both need "re-resolve the symbol name," same retry).

### 3.3 LLM-facing runbook (one page)

Every error response has the shape:

```json
{
  "error": "SYMBOL_NOT_FOUND",
  "message": "Short human-readable reason",
  "hint": "Actionable next step the LLM can execute",
  "retryable": true,
  "candidates": ["foo::bar::baz", "foo::Baz::baz"]  // code-specific fields
}
```

The LLM consumes `error`, `hint`, `retryable` first; `candidates` / `wait_ms` / other code-specific fields next. The runbook:

| Code | What happened | What the LLM should do | Retryable same turn? |
|------|---------------|------------------------|:-:|
| `STALE_VERSION` | File changed between dry-run and commit (or between two facade calls). Preview token invalidated. | Re-issue the original tool call (fresh state). The tool is idempotent (§8 of DX brief); already-moved symbols become no-ops. | Yes |
| `NOT_APPLICABLE` | LSP server has no action of the requested kind at the given position, OR the action exists but is `disabled` (e.g., cursor not inside a function). | Inspect the `reason` field; often it says "select a function body first" or similar. Adjust inputs (widen range, pick a different symbol), retry once. If still not applicable, surface to the user. | Yes, once |
| `INDEXING` | Language server is cold-starting or re-indexing after a file change. Response includes `estimated_wait_ms`. | Wait (sleep via agent scheduler, not in-tool) for ~`estimated_wait_ms`, then retry. Or: call `scalpel_reload_plugins` if the LLM suspects the server crashed. | Yes, after wait |
| `APPLY_FAILED` | Edit was partially applied and rolled back, OR rollback itself failed (rare). `failed_stage` tells the LLM where. | Read `failed_stage` and `failed_symbol`. If recoverable (e.g., "new diagnostic in target file"), adjust `reexport_policy` to `explicit_list` and retry. If unrecoverable, surface. | Conditional |
| `PREVIEW_EXPIRED` | The `preview_token` from a previous `dry_run=True` call is no longer valid (TTL 5min, or file changed). | Re-issue the `dry_run=True` call to get a fresh token; then commit with that new token. | Yes |
| `SYMBOL_NOT_FOUND` | LLM-supplied name-path didn't resolve (either 0 or >1 matches). `candidates[]` lists nearby options (top-5 by edit distance + ends-with match). | If exactly one candidate looks right, retry with that exact string. If zero candidates, the symbol genuinely doesn't exist; surface to user. If >1, use additional context (call-site, imports in file) to pick. | Yes |

**Turn-level retry policy.** The LLM is expected to retry once on any `retryable: true` error within the same conversation turn. After a second failure, escalate to the user. This isn't enforced by scalpel — it's a convention documented in the tool docstrings (see §8) so the LLM's tool-selection prompt carries the expectation.

**One forbidden pattern.** Never return a successful-looking response when the edit partially failed. `APPLY_FAILED` is the contract; half-successes are a regression hazard (per global directive: "frustrations: regression"). The design's atomic-default rule (Specialist 4 §3) makes this easy.

---

## 4. `dry_run` semantics

### 4.1 The contract (verbatim, for LLM consumption)

> When called with `dry_run: true`, `split_file` and `fix_imports` return a `RefactorResult` whose `changes` field is **byte-identical** to what `dry_run: false` would produce on the same inputs against the same file versions, PROVIDED no file in `affected_paths` is modified between the two calls. The server validates this precondition via `preview_token`; if any affected file changes, the second call fails with `PREVIEW_EXPIRED` and the LLM must re-issue the `dry_run: true` call.

Three components: byte-identical semantics, file-stability precondition, invalidation mechanism.

### 4.2 Byte-identical — under what conditions

"Byte-identical" requires:

- Same input parameters.
- Same LSP server state (no indexing in flight, no workspace refresh).
- Same file contents across all files touched.
- Same workspace settings (no `Cargo.toml` / `pyproject.toml` edits).

If any of these drift, scalpel rejects the commit with `PREVIEW_EXPIRED` and the LLM re-runs. The byte-identity guarantee holds **only when the preview token is still valid.**

### 4.3 Implementation: `preview_token`

On `dry_run=True`:

1. Capture file contents + version vector for every file in `affected_paths`.
2. Compute the `WorkspaceEdit` (via `codeAction` + `codeAction/resolve`, or facade pipeline).
3. Serialize the `WorkspaceEdit` + version vector under a `preview_token` (UUID, 5-minute TTL, in-memory with LRU spill).
4. Return `RefactorResult` with `applied=false`, `preview_token: "prev_abc123"`, `changes: [...]`, `diagnostics_delta: {...}`.

On commit (`dry_run=False, preview_token: "prev_abc123"`):

1. Look up token. If missing or TTL expired → `PREVIEW_EXPIRED`.
2. Compare current file contents + versions against captured snapshot. If any differ → `PREVIEW_EXPIRED` (invalidated by external edit).
3. Apply the cached `WorkspaceEdit`. Produces **byte-identical** result to what dry-run promised.
4. Consume the token (subsequent use → `PREVIEW_EXPIRED`).

On commit **without** `preview_token`: re-run the entire pipeline from scratch; the result may differ from any earlier dry-run (because file state may have drifted). Documented but non-default path.

### 4.4 What if a file changes mid-token

That's the `PREVIEW_EXPIRED` case. Three sub-cases:

| Sub-case | What scalpel does |
|----------|-------------------|
| File edited by user in their editor | Detected via captured version + file-content hash mismatch. `PREVIEW_EXPIRED`. |
| File edited by another agent tool (Edit/Write) between dry-run and commit | Same mechanism. `PREVIEW_EXPIRED`. |
| File auto-changed by LSP server (e.g., rustfmt-on-save) | Same mechanism. `PREVIEW_EXPIRED`. |
| No change, but TTL expired | `PREVIEW_EXPIRED` with `reason: "ttl_exceeded"`. |

In all four, the LLM's recovery is identical: re-issue the `dry_run=True` call, which re-captures state. This is deliberate — the LLM doesn't need to distinguish "file changed" from "time passed." Both mean "your preview is stale."

### 4.5 What changes` looks like

Per main design Appendix C: `list[FileChange]`, each `{path, kind: create|modify|delete, hunks: list[Hunk]}`. Hunks are unified-diff-shaped — the LLM can parse or summarize. Scalpel does NOT render the full post-edit file text in `changes` for token-budget reasons; the hunks are enough.

### 4.6 `diagnostics_delta` in dry-run

`dry_run=True` **does** compute `diagnostics_delta`. That's the key reason the LLM calls dry-run at all: to see whether the split introduces compile errors before committing. Scalpel applies the `WorkspaceEdit` in a sandboxed in-memory buffer view over the workspace, re-runs `textDocument/diagnostic` on affected files, computes `{before, after, new_errors}`. Then reverts the sandbox. The user's on-disk files are unchanged.

### 4.7 The contract summary, in LLM-consumable form

(Goes into the `split_file` docstring — see §8.)

```
dry_run=true: returns changes + diagnostics_delta + preview_token (TTL 5min).
              No on-disk modification. preview_token invalidates if any
              affected file changes. Re-run if PREVIEW_EXPIRED.
dry_run=false + preview_token: commits the dry-run result byte-identically.
dry_run=false (no token): re-runs pipeline; result may differ from any
                          earlier dry-run.
```

---

## 5. Checkpoint/rollback UX

### 5.1 Two separate concepts

Tangled in the design today. Let's split them cleanly for the LLM:

- **`preview_token`** — for `dry_run=True` ↔ `dry_run=False` handoff. Short TTL (5 min). Content: serialized `WorkspaceEdit` + version snapshot. No on-disk state. Consumed on commit.
- **`checkpoint_id`** — for `rollback` after a successful commit. Longer TTL (LRU, 10 in-memory, 50 on disk per main-design Risks table). Content: inverse `WorkspaceEdit` + pre-edit file snapshots. Consumed on rollback.

The LLM should never confuse them. Docstrings in §8 are explicit: preview tokens are input to commits; checkpoint IDs are input to rollback.

### 5.2 When the LLM calls `rollback`

Documented triggers, LLM-facing:

1. User says "undo that" or "revert the refactor."
2. `cargo check` / `pytest` / `ruff` / external-verify step fails after a commit.
3. LLM's own plan-verify loop concludes the refactor broke semantics (e.g., a test suite started failing).
4. User requests a different split strategy after seeing the committed result.

The LLM calls `rollback(checkpoint_id=...)`. Scalpel applies the inverse edit, restores pre-refactor state, consumes the checkpoint.

### 5.3 When scalpel auto-rollbacks

Scalpel **auto-rollbacks** (i.e., commits the operation atomically or not at all, no partial state) in exactly these cases:

1. `WorkspaceEdit` partial-apply IO error → inverse applied, `APPLY_FAILED` returned.
2. Strict mode (default): `diagnostics_delta.new_errors > 0` after apply → inverse applied, `APPLY_FAILED` returned with `new_errors[]` populated.
3. LSP `ContentModified` mid-sequence after one retry → inverse applied, `STALE_VERSION` returned.

Auto-rollback always happens **before** scalpel returns to the LLM. From the LLM's perspective, the operation never happened — file state is pre-call state — but the error response carries a `checkpoint_id: null` (nothing to manually rollback) and sufficient diagnostics for the LLM to adjust and retry.

### 5.4 What the LLM sees when auto-rollback fires

```json
{
  "applied": false,
  "changes": [],
  "checkpoint_id": null,
  "failure": {
    "stage": "diagnostics_check",
    "symbol": null,
    "reason": "2 new errors introduced; auto-rolled-back",
    "recoverable": true
  },
  "diagnostics_delta": {
    "before": 0,
    "after": 0,
    "new_errors_that_would_have_appeared": [
      {"file": "calcrs/src/eval.rs", "line": 42,
       "msg": "cannot find function `tokenize` in crate `parser`"}
    ]
  },
  "warnings": ["auto_rolled_back"],
  "lsp_ops": [...],
  "duration_ms": 1843
}
```

Key UX details:
- `applied: false` is the headline.
- `new_errors_that_would_have_appeared` (renamed from `new_errors` in the auto-rollback case) makes the counterfactual explicit — the LLM sees what broke, without needing to roll back manually.
- `failure.recoverable: true` invites a retry with adjusted parameters.
- `warnings: ["auto_rolled_back"]` is a grep-able signal for observability.

### 5.5 What the LLM sees when opt-in (manual) rollback fires

The LLM called `rollback(checkpoint_id="ckpt_7a3f")` explicitly:

```json
{
  "applied": true,
  "restored_files": ["calcrs/src/lib.rs", "calcrs/src/ast.rs",
                     "calcrs/src/parser.rs", "calcrs/src/eval.rs",
                     "calcrs/src/errors.rs"],
  "checkpoint_id_consumed": "ckpt_7a3f",
  "warnings": [],
  "lsp_ops": [...],
  "duration_ms": 127
}
```

Key difference: `applied: true` (the rollback itself succeeded), no `failure` block, and `restored_files` tells the LLM which files are back to their pre-refactor state. The original `checkpoint_id` is now invalid — subsequent calls with the same ID → `{ok: true, restored_files: [], no_op: true}` (per Specialist 4 §8 idempotency rule).

### 5.6 How the LLM knows a checkpoint_id is still valid

No probe tool. Rule: **checkpoint_id stays valid until (a) the LLM calls `rollback` on it, or (b) 50+ newer checkpoints exist (LRU eviction).**

Case (a) is the LLM's own state — it knows when it rolled back. Case (b) is statistical: across a session, the LLM makes maybe 5–10 refactors; LRU eviction of a checkpoint from 50+ refactors ago is exceptional. If `rollback` is called on an evicted ID, scalpel returns:

```json
{
  "applied": false,
  "error": "CHECKPOINT_EVICTED",
  "message": "checkpoint_id not found; may have been evicted by LRU policy",
  "hint": "Refactor is older than the 50-most-recent; manual rollback via git is the only path."
}
```

(A new code — `CHECKPOINT_EVICTED` — deferred to v1.1 unless MVP testing shows frequent LRU collisions. For MVP, reuse `NOT_APPLICABLE` with message "checkpoint not found".)

### 5.7 Relationship to git

Scalpel does NOT require a clean git tree. Checkpoints are scalpel-managed, not git-managed. But: users who rely on git as their real rollback mechanism are fine — scalpel's edits go through normal file writes, so `git diff` / `git checkout --` work as expected. Scalpel's `rollback` is the faster / more-granular path; git is always the fallback.

(This departs from Specialist 3 §2.4's "require clean git state" proposal. MVP rationale: requiring clean git friction is a regression hazard for agents mid-flow. We still recommend it in the skill docstring; we don't enforce.)

---

## 6. The plan→diff→commit loop

### 6.1 The question

Is `plan_file_split` (read-only) a separate tool, or should it be absorbed into `split_file_by_symbols(dry_run=True)`?

### 6.2 Case for a separate `plan_file_split`

**Pro:**

1. **Different intents.** Planning is "propose groupings"; splitting is "execute this grouping." Conflating them asks the LLM to mentally split the facade's two modes.
2. **Different outputs.** Planner returns `{suggested_groups, unassigned, cross_group_edges}`; splitter returns `{changes, diagnostics_delta, preview_token}`. Schema overlap is small; forcing one tool to emit both is noisy.
3. **Cheaper.** Planner is read-only — no `WorkspaceEdit` computation, no sandbox apply, no diagnostics re-run. LLM can call it freely during exploration without worrying about preview tokens.
4. **Aligns with turn 1 of the designed workflow.** The main design's §Workflow uses `plan_file_split` for turn 1 explicitly.
5. **Clustering heuristic gets room to breathe.** If the planner is a distinct tool, we can improve it (label propagation → community detection → LLM-assisted) without touching `split_file`.

### 6.3 Case for absorbing into `split_file(dry_run=True)`

**Pro:**

1. **One tool, two modes, one mental model.** LLM learns "call `split_file` with `dry_run=True` to see what would happen; commit when happy." Even simpler than learning "call `plan_split`, then `split_file(dry_run=True)`, then `split_file(dry_run=False)`."
2. **MVP token budget.** 3 turns become 2. The LLM proposes its own grouping in the first `dry_run=True` call, sees the diagnostic delta, iterates.
3. **The heuristic planner is unproven.** Rust symbol clustering via `callHierarchy` + community detection is interesting but not obviously better than the LLM's own context-aware grouping. MVP evidence should decide.
4. **KISS / YAGNI.** The planner adds surface area without a clear "the LLM couldn't do this otherwise" win.
5. **Cross-language clarity.** For Python, file-splitting is mostly about moving functions/classes — the LLM is already great at that from context. A heuristic planner is unlikely to beat prompting for Python.

### 6.4 Pick for MVP: absorb

**MVP = option B (absorb).** Ship `split_file` only; the LLM does its own planning from file contents (which it already reads).

Rationale:

- MVP goal is the aha moment, which depends on a tight loop (2 turns to a good dry-run, 1 commit). The planner adds a turn without solving a provable problem.
- If planner-absent performance is poor (LLMs propose bad groupings, waste dry-runs), we ship `plan_split` in v1.1 as a pure upgrade — additive, no breaking change to `split_file`.
- TRIZ contradiction principle: the planner wants "read-only + shows cluster structure"; the splitter wants "dry-run + shows diff." The contradiction is resolved by recognizing they are two *modes* of the same operation (exploration vs. execution), not two separate operations. Absorb into one.

### 6.5 v1.1 re-introduction plan

When `plan_split` returns, it will:

- Stay read-only (no preview token, no diagnostics re-run).
- Output `{suggested_groups, cross_group_edges, unassigned, warnings}` as the main design specifies.
- Coexist with `split_file(dry_run=True)` — they solve different sub-problems.
- Ship iff MVP telemetry shows LLMs waste 2+ dry-runs on average before converging on a good grouping.

---

## 7. Hallucination resistance

### 7.1 The boundary

Facades accept **name-paths only** (main design §3, Specialist 4 §5). Byte ranges don't reach the LLM. But name-paths are LLM-authored strings — they will drift:

- Case: `Foo::bar` vs. `foo::Bar` vs. `FOO::BAR`.
- Scope: `Bar::do_thing` when the actual path is `foo::Bar::do_thing`.
- Typos: `tokkenize` for `tokenize`.
- Wrong separator: `Foo.bar` (Python-style) for `Foo::bar` (Rust-style) — especially with cross-language MVP.
- Private qualification: `foo::bar` for `foo::bar::baz` (truncated).

### 7.2 Minimum safety net

**Three-stage resolution** (per Specialist 4 §7, extended for Python):

1. **Exact match** against the file's `documentSymbol` output.
2. **Case-insensitive match** (cheap, catches most drift).
3. **Ends-with match** (e.g., `Bar::do_thing` matches `foo::Bar::do_thing`).

For Python specifically, add:
4. **Separator-normalized match**: try `foo::bar` and `foo.bar` as equivalent. Scalpel internally canonicalizes on `::` (LSP convention); the matcher accepts either.

If exactly one match after all stages: proceed, record in `resolved_symbols: [{requested, resolved}]`, include a warning if the requested string wasn't exact.

If zero matches: `SYMBOL_NOT_FOUND` with a `candidates[]` list (top-5 by Levenshtein distance against all `documentSymbol` entries in the file).

If >1 matches: same `SYMBOL_NOT_FOUND` code (§3 consolidation) but `candidates[]` contains the top-5 ambiguous matches.

### 7.3 Exact response shape

```json
{
  "error": "SYMBOL_NOT_FOUND",
  "message": "Symbol 'Bar::do_thing' not found in crates/foo/src/massive.rs",
  "hint": "Did you mean 'foo::Bar::do_thing'? See candidates.",
  "retryable": true,
  "requested": "Bar::do_thing",
  "candidates": [
    {"name_path": "foo::Bar::do_thing", "kind": "method", "line": 142,
     "match_reason": "ends_with + case-exact"},
    {"name_path": "foo::Baz::do_thing", "kind": "method", "line": 287,
     "match_reason": "ends_with + case-exact"},
    {"name_path": "foo::bar::do_thing", "kind": "function", "line": 412,
     "match_reason": "case-insensitive + ends_with"}
  ]
}
```

Key fields:

- `requested` preserves the LLM's exact string (diagnostics, not prettified).
- `candidates` are LLM-consumable — `name_path` is directly retryable as a facade input.
- `match_reason` explains why the candidate surfaced (trust signal for the LLM).
- `hint` is a one-line instruction that pattern-matches what LLMs already do ("Did you mean X?").

### 7.4 Cross-group rule: fail-loud, never silent

**Never silently substitute.** If exactly one exact-match candidate exists, proceed and record in `resolved_symbols`. If only case-insensitive or ends-with candidates exist, **fail** with `SYMBOL_NOT_FOUND` even if there's exactly one — the LLM retries with the suggested `name_path`. This extra turn is cheap and keeps the LLM honest.

(Departs from Specialist 4 §7 which allows auto-correction on single fuzzy match. Rationale: MVP trust > convenience. We loosen in v1.1 when we have data.)

### 7.5 Cross-language edge case

If the LLM passes `Foo.bar` against a Rust file, scalpel could:
- (a) treat `.` and `::` as equivalent and resolve normally, or
- (b) fail with `SYMBOL_NOT_FOUND` + hint "Rust uses `::` for path separator."

**MVP: option (a).** Silent normalization because the failure-case UX is worse (LLM retries with correct separator — one wasted turn). For Python, same normalization. Internally canonicalize on `::`.

---

## 8. Tool docstrings and schemas for LLM consumption

Each MVP facade gets a ≤90-word docstring optimized for the LLM's tool-selection prompt. Requirements:

1. First sentence: what the tool does, in verb-forward terms.
2. Second sentence: which language(s) supported.
3. Third sentence: when the LLM should call it (disambiguate from CC's `LSP`).
4. Fourth sentence: key parameter or output to know.
5. No marketing, no multi-paragraph, no examples (those live in skills/READMEs).

### 8.1 `split_file`

```
Split a single source file into multiple submodules by moving named
symbols into new files and updating the parent module declaration.
Supports Rust (.rs) and Python (.py). Use when the user asks to
"split", "break up", "decompose", or "modularize" a large file —
NOT when they ask to find or inspect code (use the LSP tool for
that). Returns a changes list, a diagnostics_delta, and a
preview_token when dry_run=true; returns a checkpoint_id when
committed. Atomic: rolls back if new compile errors appear.
```

Word count: 86. Disambiguation signals: "split/break up/decompose" (intent verbs), "NOT when" (negative example), "preview_token vs. checkpoint_id" (output discriminators).

### 8.2 `fix_imports`

```
Sweep a set of files (or the whole workspace) to correct broken
import/use statements after a structural refactor, add missing
imports, remove unused imports, and reorder them. Supports Rust
(.rs) and Python (.py). Call immediately after split_file or any
other structural move; do NOT call before (no broken state exists
yet). Returns count of files modified and remaining diagnostics;
safe to call repeatedly (idempotent). Defaults apply all three
operations; disable individually via add_missing, remove_unused,
reorder flags.
```

Word count: 81. Disambiguation: "after a structural refactor" (when), "do NOT call before" (negative), "idempotent" (key UX fact — LLM can re-call without worry).

### 8.3 `rollback`

```
Undo a prior refactor by its checkpoint_id. Restores all files
touched by that refactor to their pre-refactor contents. Supports
Rust and Python (any file type the original refactor touched).
Call when the user says "undo" / "revert" after a commit, or when
post-refactor verification (cargo check, pytest, etc.) reveals a
semantic break. Takes one argument: checkpoint_id (returned by the
successful split_file / fix_imports / apply_code_action call).
Idempotent: second rollback with the same id is a no-op returning
{applied: true, restored_files: []}.
```

Word count: 85. Disambiguation: "by its checkpoint_id" (unambiguous input), "after a commit" (temporal positioning), "idempotent no-op" (retry safety).

### 8.4 Minimum MCP surface table

| Tool | Inputs (summary) | Output (summary) | Priority | MVP verdict |
|------|------------------|-------------------|:--------:|:-----------:|
| `mcp__o2-scalpel__split_file` | `file: str`, `groups: dict[str, list[str]]`, `parent_module_style: "dir"\|"mod_rs"\|"package"\|"module" = "dir"`, `keep_in_original: list[str] = []`, `reexport_policy: "preserve_public_api"\|"none"\|"explicit_list" = "preserve_public_api"`, `explicit_reexports: list[str] = []`, `language_options: dict = {}`, `dry_run: bool = false`, `preview_token: str\|null = null`, `allow_partial: bool = false` | `RefactorResult{applied, changes, diagnostics_delta, preview_token?, checkpoint_id?, resolved_symbols, warnings, lsp_ops, duration_ms, failure?}` | **P0** | Ship |
| `mcp__o2-scalpel__fix_imports` | `files: list[str]` (supports `"**"`), `add_missing: bool = true`, `remove_unused: bool = true`, `reorder: bool = true`, `dry_run: bool = false`, `preview_token: str\|null = null` | `RefactorResult` (same shape as above, plus `imports_added: int`, `imports_removed: int`, `files_modified: int`) | **P0** | Ship |
| `mcp__o2-scalpel__rollback` | `checkpoint_id: str` | `{applied: bool, restored_files: list[str], checkpoint_id_consumed: str, warnings, lsp_ops, duration_ms}` | **P0** | Ship |
| `mcp__o2-scalpel__apply_code_action` | `file: str`, `range: Range`, `kind: str` (LSP codeAction kind), `title_contains: str\|null = null`, `dry_run: bool = false`, `preview_token: str\|null = null` | `RefactorResult` | **P0** | Ship (bundles list+resolve+apply for MVP) |
| `mcp__o2-scalpel__plan_split` | `file: str`, `strategy: "by_cluster"\|"by_visibility"\|"by_type_affinity" = "by_cluster"`, `max_groups: int = 5` | `PlanResult{suggested_groups, unassigned, cross_group_edges, warnings}` | **P1** | Defer (absorbed into `split_file(dry_run=True)` for MVP) |
| `mcp__o2-scalpel__extract_to_module` | `file: str`, `symbols: list[str]`, `new_module: str`, `dry_run: bool = false` | `RefactorResult` | **P1** | Defer (wrapper over `split_file`) |
| `mcp__o2-scalpel__list_code_actions` | `file: str`, `range: Range`, `kinds: list[str]\|null = null` | `list[CodeActionDescriptor]` | **P1** | Defer (folded into `apply_code_action`) |
| `mcp__o2-scalpel__resolve_code_action` | `id: str` | `ResolvedAction` | **P2** | Defer |
| `mcp__o2-scalpel__promote_inline_module` | `file: str`, `module_name: str`, `target_style: "dir"\|"mod_rs" = "dir"`, `dry_run: bool = false` | `RefactorResult` | **P2** | Defer (Rust-only, narrow) |
| `mcp__o2-scalpel__execute_command` | `command: str`, `arguments: list[Any]\|null = null` | `Any` | **P2** | Defer |

### 8.5 Schema conventions the LLM learns once

- **Name-paths** everywhere: `foo::Bar::baz` (Rust) or `foo.Bar.baz` normalized to `::` (Python).
- **Preview tokens** are inputs to commits; `checkpoint_id`s are inputs to rollback.
- **`dry_run=True` returns `preview_token`; `dry_run=False` returns `checkpoint_id`.** Mutually exclusive; they never appear together.
- **`RefactorResult`** is the canonical success/failure shape. Facades and `apply_code_action` all return it. The LLM learns one schema for all mutating operations.
- **Errors** are `{error, message, hint, retryable, ...}` — flat JSON, not nested. Parseable in one glance.

---

## 9. Cross-language tool-selection UX

### 9.1 Same name for Rust and Python: argue for

**Pro (same name):**

1. **Tool-selection cost.** LLMs tokenize tool names once per session. Two tools (`split_rust_file` + `split_python_file`) doubles that cost and doubles the schema-loading cost (deferred-loading — see [plugin-extension-surface-brief](../../research/2026-04-24-plugin-extension-surface-brief.md) §1.2).
2. **Intent-name fidelity.** The user says "split this file," not "apply a Rust refactor." The tool name should match intent, not implementation.
3. **Language-agnostic skill authoring.** SKILL.md files in the plugin become portable across languages without conditional branches.
4. **Future-proofing.** Adding Go, TypeScript, Java doesn't bloat the tool count linearly. Tool count stays at 5 forever; the `LanguageStrategy` plugin handles per-language differences (main design §5).
5. **Main design §3 prescribes it.** "The file is deliberately language-free; every language-specific decision is delegated to an injected `LanguageStrategy`."

### 9.2 Same name for Rust and Python: argue against

**Con (same name):**

1. **Hidden surface area.** `split_file(file="main.py", parent_module_style="mod_rs")` is silently wrong — `mod_rs` is Rust jargon. Same-name tools leak language semantics through parameters.
2. **Error message specificity.** Errors from a Rust-specific failure (e.g., macro expansion tripping) surface with a generic tool name, masking that the failure is Rust-only.
3. **LLM debugging.** When a tool call fails, the LLM consults docstring + examples. Same-name tools with per-language quirks force the LLM to infer "this applies in Rust, not Python." Per-language tools make the scope explicit.

### 9.3 Decision: same name, language-tagged parameters

**MVP: same name** (per main design), **but** language-specific parameters live under a `language_options: dict` field, keyed by language prefix:

```json
{
  "tool": "split_file",
  "args": {
    "file": "crates/foo/src/massive.rs",
    "groups": {...},
    "parent_module_style": "dir",   // generic, both languages
    "language_options": {
      "rust": {
        "mod_rs_override": false,
        "reexport_keyword": "pub use"
      },
      "python": {
        "init_style": "explicit_reexport",
        "preserve_docstrings": true
      }
    }
  }
}
```

Scalpel reads only the sub-dict matching the detected language (from file extension). Unused keys are ignored without error; unknown keys within the detected language → `warnings: ["unknown language_option: <key>"]` (not fatal).

**Detection is automatic.** File extension → `LanguageStrategy` lookup (per main design §5). The LLM does not specify the language explicitly; scalpel infers. If the file extension is unknown, facade returns `language_unknown` (main design §Deployment, strategy-registration mismatch).

### 9.4 The signal the LLM uses to know Rust-vs-Python flags

Three mechanisms, in order of trust:

1. **Docstring enumeration.** The `split_file` docstring lists generic parameters + a terse pointer: "Language-specific options live under `language_options.<language>`; see the language strategy docs for full keys." This is the primary tool-selection signal.
2. **Schema.** JSON Schema for `language_options` declares the per-language sub-schemas (oneOf discriminator). LLMs that honor the schema will self-validate.
3. **Error feedback.** Passing `rust` keys for a `.py` file → `warnings: ["unused language_option for non-matching language: rust"]`. Runtime correction.

**TRIZ separation principle.** The contradiction "same tool name for two languages with different parameters" resolves by *separating in parameter space* rather than in tool-name space. The tool name carries intent; the parameters carry implementation details. Clean.

### 9.5 v1.1 reconsideration trigger

If MVP telemetry shows the LLM frequently passes Rust flags to Python files (or vice versa) despite the warnings, reconsider per-language tool names for v1.1. Evidence-driven.

---

## 10. Observability from the LLM's perspective

### 10.1 What the LLM already sees

Main design Appendix C's `RefactorResult` carries:
- `lsp_ops: list[{method, count, total_ms}]` — per-LSP-method timing.
- `duration_ms: int` — total facade duration.
- `warnings: list[str]` — human-readable caveats.
- `diagnostics_delta: {before, after, new_errors}` — the most important signal.
- `resolved_symbols: list[{requested, resolved}]` — name-path corrections.

### 10.2 Minimum set for cross-turn learning

The LLM learns when it can correlate call-shape inputs with outcomes. MVP adds two fields to `RefactorResult`:

**1. `indexing_ready: bool`**

Whether the LSP server was fully indexed when the call ran. If `false`, treat timing / success as unreliable — the LLM should retry later (or call a `wait_for_indexing` tool — deferred to v1.1) before drawing conclusions. Without this, the LLM can't distinguish "this refactor is slow" from "rust-analyzer was cold."

**2. `rules_fired: list[str]`**

Which internal decision points mattered. Examples:
- `"name_path_fuzzy_matched:case_insensitive"` — we accepted a case-drift.
- `"reexport_policy:preserve_public_api"` — we generated re-exports based on policy default.
- `"auto_rolled_back:diagnostics"` — rollback fired because of new errors.
- `"preview_token_valid"` — commit succeeded against a valid token.
- `"fallback_extract_module_chain"` — we fell back to the two-step assist chain (Gap 1 workaround).

This is telemetry for the LLM, not just for humans. Across turns, the LLM learns "when I see `fallback_extract_module_chain` it means the splitter took the slow path — my next call should expect similar latency."

### 10.3 What NOT to expose

Per Specialist 3 §9 and Specialist 4 §Observability:

- **Raw `WorkspaceEdit` JSON.** The LLM hallucinates edits. Expose diff-hunks, not LSP JSON.
- **Internal checkpoint storage paths.** Surfaces filesystem structure the LLM shouldn't touch.
- **Per-symbol LSP trace.** Too noisy. The aggregated `lsp_ops` table is enough.
- **LSP server stderr.** Goes to the scalpel log file, not the LLM response.

### 10.4 Complete `RefactorResult` for MVP

```python
class RefactorResult(BaseModel):
    applied: bool
    changes: list[FileChange]
    diagnostics_delta: DiagnosticsDelta
    preview_token: str | None         # present iff dry_run=True and success
    checkpoint_id: str | None         # present iff dry_run=False and success
    resolved_symbols: list[ResolvedSymbol]
    warnings: list[str]
    failure: FailureInfo | None = None
    lsp_ops: list[LspOpStat]
    duration_ms: int
    # NEW for MVP observability:
    indexing_ready: bool
    rules_fired: list[str]
```

Four bytes of schema change, meaningful cross-turn learning signal. Worth the budget.

### 10.5 Rollback observability

`rollback`'s success shape (§5.5) adds no new signals beyond `restored_files` and `duration_ms`. The LLM already knows *why* it rolled back (because it decided to). Don't over-instrument.

---

## 11. Minimum MCP surface — consolidated table

(Duplicates §8.4, enriched with priority rationale for the summary reader.)

| # | Tool | In-schema (summary) | Out-schema (summary) | Priority | MVP | Rationale |
|--:|------|---------------------|----------------------|:--:|:--:|-----------|
| 1 | `split_file` | file + groups + policy + dry_run + preview_token | RefactorResult | **P0** | Ship | Star of the show; delivers turns 1-3 of the 5-turn workflow via dry-run-first loop. |
| 2 | `fix_imports` | files (supports `**`) + per-operation flags | RefactorResult + import counts | **P0** | Ship | Every split leaves dangling imports; cleanup is non-negotiable. |
| 3 | `rollback` | checkpoint_id | restored_files + consumed id | **P0** | Ship | Safety net. Makes the whole product "safe to try." |
| 4 | `apply_code_action` | file + range + kind + title_contains + dry_run | RefactorResult | **P0** | Ship | Escape hatch for anything the 3 facades don't cover (rename, inline, etc.). MVP bundles list+resolve+apply. |
| 5 | `plan_split` | file + strategy + max_groups | PlanResult | P1 | Defer | Absorbed into `split_file(dry_run=True)` for MVP; ships v1.1 if telemetry shows LLM wastes dry-runs. |
| 6 | `extract_to_module` | file + symbols + new_module | RefactorResult | P1 | Defer | Thin wrapper over `split_file`; KISS says don't ship. |
| 7 | `list_code_actions` | file + range + kinds | list[CodeActionDescriptor] | P1 | Defer | Folded into `apply_code_action` for MVP; two-phase flow returns in v1.1. |
| 8 | `resolve_code_action` | id | ResolvedAction | P2 | Defer | Only needed once two-phase flow is exposed. |
| 9 | `promote_inline_module` | file + module_name + target_style | RefactorResult | P2 | Defer | Rust-only; no Python analogue; narrow. |
| 10 | `execute_command` | command + arguments | Any | P2 | Defer | Server-specific JSON-RPC escape hatch; advanced. |

**MVP surface = 4 tools (3 facades + 1 primitive).** Rollback is the 4th. Total: 4 tools the LLM learns.

Wait — that's 4, not 5. The count difference is because `apply_code_action` for MVP is a single bundled tool, not the three primitives from the original design. Re-count:

- `split_file` (facade)
- `fix_imports` (facade)
- `rollback` (primitive)
- `apply_code_action` (primitive, bundled)

= **4 tools.** Even more aggressive than the "3 facades + 2 primitives" ask in the brief. The brief's "2 primitives" implies rollback + one more primitive; `apply_code_action` is that primitive, bundled tighter than the main design sketches.

If the orchestrator prefers to split `apply_code_action` back into `list_code_actions` + `apply_code_action`, that's a 5-tool MVP (still achievable). The bundled version is recommended because the LLM rarely wants the two-phase flow at MVP (they want "do this refactor" intent); v1.1 splits them back out.

---

## 12. Loose ends and MVP testing implications

### 12.1 Test coverage the MVP surface requires

Mapped to main design §Testing Strategy:

- **Unit tests.** `split_file(dry_run=True)` returns byte-identical result to subsequent `split_file(dry_run=False, preview_token=...)` on an unchanged fixture. Name-path resolution: 3 cases (exact, case-drift, ends-with), one per stage, one `AMBIGUOUS` multi-match. Checkpoint LRU eviction.
- **Integration tests.** `calcrs` fixture (Rust): 4 modules out of a 900-LoC file; `diagnostics_delta` transitions 0→0 post-split. **Add a Python fixture** (`pylcr`? small arithmetic-evaluator in Python mirroring `calcrs`): 3 modules out of a ~500-LoC `lib.py`. Both fixtures must pass byte-identical dry-run-to-commit.
- **E2E tests.** The 5-turn workflow, per language: plan (mental) → dry-run → commit → fix_imports → verify. Rollback branch: introduce a deliberate error (e.g., private-cross-module call), confirm auto-rollback fires, `new_errors_that_would_have_appeared` is populated.

### 12.2 Skill authoring for MVP

The plugin's `skills/` directory should ship **one** skill: `refactor-playbook.md`. Body is a prompt template that encourages the LLM to:

1. Call `split_file(dry_run=true)` first.
2. Inspect `diagnostics_delta`.
3. If errors: adjust `reexport_policy` → `explicit_list` with explicit names.
4. Commit (`dry_run=false` with `preview_token`).
5. Call `fix_imports` crate/package-wide.
6. Externally verify (`cargo check` / `pytest`).
7. If verify fails: `rollback(checkpoint_id)`.

The skill is the authoritative playbook — tool docstrings are terse by design; the skill fills the gap.

### 12.3 What MVP does NOT include

Explicit non-goals for the LLM-facing surface in MVP:

- Interactive clarification prompts from scalpel (scalpel never asks the LLM a question; it returns `SYMBOL_NOT_FOUND` + candidates and lets the LLM decide).
- Cross-workspace refactors (single workspace only).
- `$/progress` streaming to the LLM (scalpel blocks until the facade completes; indexing waits are opaque except via `indexing_ready: false`).
- Undo-beyond-checkpoint (git is the answer for older state).
- User-visible permission prompts (scalpel uses MCP's stdout; permission is granted by CC at plugin-install time).

### 12.4 Compatibility with the existing Serena tool surface

Main design §3 notes the new facades coexist with Serena's existing `find_referencing_symbols`, `replace_symbol_body`, etc. MVP does not break this — the scalpel facades are additions. LLMs running Serena in its current form keep their existing tools and gain the scalpel 4.

---

## 13. Open questions for follow-up specialists

1. **Python module-style parameter values.** `parent_module_style` defaults to `"dir"` (Rust semantics). Python has no true dir-vs-single-file equivalent (packages vs. modules). Should the default be language-aware (`"dir"` for `.rs`, `"module"` for `.py`)? Deferred to the Python-strategy specialist.
2. **`fix_imports` Python aggressiveness.** Python's `isort` + `ruff` handle most of this already. Should `fix_imports` shell out to `ruff --fix` when it detects a Python project, or replicate the logic via pyright code actions? Python-strategy specialist.
3. **Preview-token TTL tuning.** 5 minutes is a guess. Measure real LLM turn-duration distributions during MVP testing; adjust.
4. **Rollback eviction signaling.** Do we ship `CHECKPOINT_EVICTED` in MVP or collapse it into `NOT_APPLICABLE`? Answered "collapse" above; revisit if LLM confusion shows up.
5. **Claude Code built-in LSP tool collision.** If/when CC ships `LSP.rename` natively, `apply_code_action(kind="refactor.rewrite")` partially overlaps. Maintainer-facing, not LLM-facing; no MVP action required.

---

## 14. Summary: the MVP LLM experience in one diagram

```
User: "split massive.rs into sensible modules"
  │
  ▼
LLM reads massive.rs (via CC's Read tool) ─── proposes groups in its own plan
  │
  ▼
LLM → split_file(file, groups, dry_run=True)
  │   ◀── scalpel returns { preview_token, changes, diagnostics_delta }
  ▼
LLM inspects changes + diagnostics_delta
  │   ├─ if 0 new errors → commit
  │   └─ if N new errors → adjust groups / reexport_policy → re-dry-run
  ▼
LLM → split_file(..., dry_run=False, preview_token=...)
  │   ◀── scalpel returns { checkpoint_id, diagnostics_delta: 0→0 }
  ▼
LLM → fix_imports(files=["src/**"])
  │   ◀── scalpel returns { imports_added, imports_removed }
  ▼
LLM → external verify (cargo check / pytest)  ── OK → done
                                                 └ fail → rollback(checkpoint_id)
```

4 tools. 3-4 calls on the happy path. Same shape for Rust and Python. Atomic with rollback. Preview-token-driven dry-run-to-commit. Hallucination-resistant name-path resolution. Observable via `diagnostics_delta`, `rules_fired`, `indexing_ready`.

That is the MVP the LLM experiences.

---

## Appendix A — Field-by-field reference for MVP `RefactorResult`

| Field | Type | Present when | LLM usage |
|-------|------|--------------|-----------|
| `applied` | bool | always | Headline — did the edit commit? |
| `changes` | `list[FileChange]` | success or dry_run | LLM inspects to understand impact |
| `diagnostics_delta` | `{before, after, new_errors}` | always | **Single most important signal** — did we break the build? |
| `preview_token` | `str \| null` | iff dry_run=True and success | LLM passes to subsequent commit call |
| `checkpoint_id` | `str \| null` | iff dry_run=False and applied=True | LLM stores for possible future rollback |
| `resolved_symbols` | `list[{requested, resolved}]` | when name-path was normalized | LLM learns correct spellings |
| `warnings` | `list[str]` | always | Non-fatal caveats |
| `failure` | `{stage, symbol, reason, recoverable}` | iff applied=False and retryable | LLM's repair pattern signal |
| `lsp_ops` | `list[{method, count, total_ms}]` | always | Observability — perf costs per op |
| `duration_ms` | int | always | Observability — total |
| `indexing_ready` | bool | always | **New MVP field.** Tells LLM whether the LSP was warm |
| `rules_fired` | `list[str]` | always (may be empty) | **New MVP field.** Tells LLM which internal decisions triggered |

---

## Appendix B — Field-by-field reference for error responses

| Field | Type | Always | LLM usage |
|-------|------|:------:|-----------|
| `error` | string (enum) | Yes | Dispatch key for retry/repair logic |
| `message` | string | Yes | Human-readable one-liner |
| `hint` | string | Yes | Actionable next step |
| `retryable` | bool | Yes | Whether to retry same-turn vs. escalate |
| `candidates` | list | On `SYMBOL_NOT_FOUND` | Suggested corrections |
| `estimated_wait_ms` | int | On `INDEXING` | Back-off timing |
| `failed_stage` | string | On `APPLY_FAILED` | Where in the pipeline we failed |
| `reason` | string | On `NOT_APPLICABLE` | LSP server's `disabled.reason` or equivalent |

Six error codes × four always-present fields + a handful of code-specific extras = a taxonomy the LLM can learn from the docstrings + one runbook page (§3.3).

---

**End of report.**
