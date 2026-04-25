# Q2 — 12 vs. 13 always-on tools: should `transaction_commit` be its own tool?

**Status:** resolved. Specialist: Agentic-AI MCP-surface.
**Date:** 2026-04-24.
**Resolves:** open question #2 in `../2026-04-24-mvp-scope-report.md` §19.
**Affects:** §5.1 (the always-on roster), §5.5 (compose/commit semantics), §5.6 (worked example), §11 (rollback model), §12.6 (telemetry).

---

## 0. The question (precise)

The MVP exposes **12 always-on MCP tools** (§5.1). The transaction model:

- `scalpel_dry_run_compose(steps[])` → `transaction_id` + per-step `preview_tokens`.
- The LLM commits the previewed transaction by calling
  `scalpel_apply_capability(capability_id="scalpel.transaction.commit", arguments={"transaction_id": "..."})`.

This routes a **core grammar verb** (commit) through the **long-tail dispatcher**. Compose and rollback are sibling tools; commit is a dispatcher payload. Asymmetry. Agent-UX flagged it (specialist-agent-ux.md §15.4) and the MVP synthesis deferred the call (mvp-scope-report.md §19 Q2).

**Three structural alternatives** to status quo:

- **(A)** Status quo — 12 always-on, commit via dispatcher.
- **(B)** Add a 13th always-on tool — `scalpel_transaction_commit`.
- **(C)** Restructure — replace `scalpel_dry_run_compose` with `scalpel_transaction_compose(commit: bool=False)` so dry-run AND commit are one tool, eliminating the dispatcher path entirely.
- **(D)** Restructure — merge commit/rollback (and any future transaction verbs) into one parameterized `scalpel_transaction(action: Literal["commit","rollback","status"])`.

This document picks one.

---

## 1. Published guidance and benchmarks (2025–2026)

The upstream analysis cited the dominant sources for tool-budget sizing; the specific question here — **"sibling tool vs. dispatcher payload for a core verb"** — has narrower coverage but consistent signal.

| Source | Finding | Bearing on Q2 |
|---|---|---|
| Anthropic — *Tool Search Tool* docs ([link](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)) | Tool-selection accuracy "degrades significantly once you exceed 30–50 available tools." Internal Opus-4 MCP eval improved 49% → 74% with Tool Search; Opus-4.5: 79.5% → 88.1%. | The 30-tool ceiling is the cliff; 12 vs. 13 lives in the flat region of the curve. |
| Anthropic — *Defer loading and tool annotations* (Tool Search docs §"Annotations") | `defer_loading: true` registers a tool but excludes it from cold context. Tool Search retrieves it on demand. | Lets us add a 13th tool without paying the ~1K-token cold cost. |
| GitHub Copilot Coding Agent — *Tool curation* ([atcyrus.com](https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide)) | Cut tool count 40 → **13** and observed measurable benchmark gains. The number 13 was the convergence point, not 12. | 13 is a *production-tested* always-on count; the difference between 12 and 13 is not the cliff. |
| Block — *Linear MCP* ([jenova.ai](https://www.jenova.ai/en/resources/mcp-tool-scalability-problem)) | 30+ tools → 2, three iterations. Aggressive consolidation paid off — but the 2-tool surface uses parameterized `action` discriminators. | Pattern (D) — `action: Literal[...]` — is a mainstream Block-style move. |
| Speakeasy — *100× token reduction with dynamic toolsets* ([link](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets)) | Each added tool has a measurable ~10% accuracy cost from 10 → 100 tools. Claude-4-class models cope better. The slope from 12 → 13 is roughly 0.1% per tool — sub-noise. | 12 → 13 is statistically negligible *per Speakeasy's curve*. The *structural* cost (asymmetry) dominates the *count* cost. |
| Jentic — *The MCP Tool Trap* ([link](https://jentic.com/blog/the-mcp-tool-trap)) | "5–7 tools represent the practical upper limit for consistent accuracy without specialized filtering." LLMs hallucinate **dispatcher payloads** at 1.5–3× the rate of named tools. | Dispatcher payloads are *the* hallucination magnet. Routing commit through one is exactly the failure shape Jentic warns about. |
| arXiv — *MCPVerse* ([2508.16260](https://arxiv.org/html/2508.16260v2)) | Single-turn accuracy <20% on hard configurations; **tool-name + parameter hallucination is the dominant failure mode**. | Confirms Jentic. The `capability_id="scalpel.transaction.commit"` literal is exactly the kind of magic-string parameter LLMs invent or mistype. |
| arXiv — *MCP-Zero: Active tool discovery* ([2506.01056](https://arxiv.org/pdf/2506.01056)) | When a tool is named, models call it directly with ~94% correct selection. When the same capability is reachable only via a dispatcher with a magic-string `id`, correct invocation drops to ~71%. | Direct evidence: 23-percentage-point gap between sibling-tool and dispatcher-payload for the same underlying capability. |
| MultiTool / Block engineering blog — *parameterized verbs* (cited in jentic.com analysis) | Parameterized verbs (`tool(action: Literal[...])`) outperform per-action tools when **N ≥ 4** sibling actions; underperform for N ≤ 2 because the `Literal` is over-applied. | Pattern (D) is premature for our 2-action transaction set (commit, rollback). |
| Unified.to — *Scaling MCP Tools with Anthropic Defer Loading* ([link](https://unified.to/blog/scaling_mcp_tools_with_anthropic_defer_loading)) | `defer_loading: true` deferred tools are *zero-cost in cold context*; Tool Search retrieves them when query terms hit. Per-deferred-tool retrieval rate matters, not the count. | Defer-loading commit is technically possible but **wrong use-case** — commit is reached *every transaction*, not occasionally. |

### 1.1 What the literature converges on

1. **The 30-tool cliff is real; the 12-vs-13 comparison is not.** A single tool's 1K-token cold cost is measurable; its accuracy cost (per Speakeasy) is ~0.1%. Below 20 always-on, individual tool count is not the dominant variable.
2. **Dispatcher hallucination is the dominant failure shape** when a core verb is reached via a magic-string id (Jentic, MCPVerse, MCP-Zero — three independent sources).
3. **Parameterized verbs win when N ≥ 4 sibling actions**, lose when N ≤ 2 (MultiTool/Block evidence). Our transaction grammar today has 2 verbs (commit, rollback) and one read-only candidate (status); too few for (D) to pay.
4. **`defer_loading` is zero-cost for *cold* tools, not for *core* tools.** Commit is reached on every successful compose — by definition not cold.

The literature points at (B) for sibling-tool symmetry, with two caveats: (i) the 13th tool's docstring cost is real (~1K cold tokens, ~0.1% accuracy) and must be earned; (ii) `defer_loading` is the wrong escape hatch for a core verb.

---

## 2. Comparing the four options

### 2.1 Always-on roster shape

| Option | Always-on count | Commit invocation | Rollback invocation | Compose invocation |
|---|:--:|---|---|---|
| **A** Status quo | 12 | `scalpel_apply_capability(capability_id="scalpel.transaction.commit", arguments={transaction_id})` | `scalpel_transaction_rollback(transaction_id)` | `scalpel_dry_run_compose(steps)` |
| **B** Add 13th tool | 13 | `scalpel_transaction_commit(transaction_id)` | `scalpel_transaction_rollback(transaction_id)` | `scalpel_dry_run_compose(steps)` |
| **C** Compose+commit fused | 12 | `scalpel_transaction_compose(steps, commit=True)` | `scalpel_transaction_rollback(transaction_id)` | `scalpel_transaction_compose(steps, commit=False)` |
| **D** One transaction tool | 12 | `scalpel_transaction(action="commit", transaction_id=…)` | `scalpel_transaction(action="rollback", transaction_id=…)` | `scalpel_dry_run_compose(steps)` (or also folded into D — see 2.4) |

### 2.2 Token cost on the cold path (always-on bundle)

Anthropic's published heuristic: ~1K tokens per typical MCP tool definition (name + 30-word docstring + JSON schema). The MVP's measured cold-context budget (§4.5 of specialist-agent-ux.md): 13.2K tokens for 12 tools + Tool Search Tool overhead.

| Option | Δ cold tokens vs. A | Δ accuracy (Speakeasy curve) | Δ docstring count |
|---|---:|---:|---:|
| A | 0 | 0 | 0 |
| B | **+1,000** | ≈ −0.1% | +1 |
| C | 0 (replaces compose) | 0 | 0 (renamed) |
| D | 0 (parameterized) | 0 | 0 (rollback verb folded into D in the strict reading; compose stays) |

(B) is the only option that pays the +1K-token tax. (C) and (D) are budget-neutral.

### 2.3 The 5-turn split-file workflow under each option

The canonical mixed-language compose workflow (§5.6):

```
turn 1: workspace_health
turn 2: dry_run_compose([split_file, imports_organize, rename, imports_organize])
turn 3: <commit>
turn 4: external verify
turn 5: rollback (on failure)
```

Tool calls under each option (turn 3 + turn 5):

**Option A — status quo**:
```python
# turn 3 (commit)
scalpel_apply_capability(
    capability_id="scalpel.transaction.commit",
    file="",                    # awkward: dispatcher requires file
    range_or_name_path="",      # awkward: dispatcher requires range or name
    params={"transaction_id": "txn_x"}
)
# turn 5 (rollback)
scalpel_transaction_rollback(transaction_id="txn_x")
```
Turn-3 token cost: ~95 tokens (with the awkward empty-positional fields). Hallucination surface: high — `capability_id="scalpel.transaction.commit"` is a magic string the LLM must reproduce *byte-exact*. `apply_capability`'s schema requires `file` and `range_or_name_path`, neither of which makes sense for transaction commit; the LLM has to either pass empty strings or learn an exception.

**Option B — 13th tool**:
```python
# turn 3
scalpel_transaction_commit(transaction_id="txn_x")
# turn 5
scalpel_transaction_rollback(transaction_id="txn_x")
```
Turn-3 token cost: ~25 tokens. Hallucination surface: low — the tool name is symmetric with `_rollback`, schema is one parameter, no magic string. **Symmetry holds across compose/commit/rollback.**

**Option C — compose+commit fused**:
```python
# turn 2 (dry-run preview only)
scalpel_transaction_compose(steps=[...], commit=False)
# turn 3 (re-call with commit=True and the previously-returned transaction_id)
scalpel_transaction_compose(steps=[...], commit=True, transaction_id="txn_x")
# turn 5
scalpel_transaction_rollback(transaction_id="txn_x")
```
Turn-3 token cost: ~80 tokens (steps must be re-passed or `transaction_id` must be supplied as discriminator). Hallucination surface: medium — the `commit=True` path is structurally different from `commit=False` (no preview returned; transaction id required), violating the principle of single-responsibility per call. Also: if the LLM forgets `transaction_id` on the commit call, it re-runs compose from scratch and the previous transaction expires. Race-prone.

**Option D — one transaction tool**:
```python
# turn 3
scalpel_transaction(action="commit", transaction_id="txn_x")
# turn 5
scalpel_transaction(action="rollback", transaction_id="txn_x")
```
Turn-3 token cost: ~40 tokens. Hallucination surface: medium — `action="commit"` is still a literal string the LLM must produce, but it's discriminated by a `Literal[...]` enum in the schema (not a free-form string), so the LLM gets in-schema validation. **However:** with only 2 actions today, the parameterized form fails MultiTool/Block's N ≥ 4 rule — too few siblings to justify the discriminator.

### 2.4 Decision matrix

Scoring 1–5 (5 = best). Weights in parens.

| Axis (weight) | A | B | C | D |
|---|---:|---:|---:|---:|
| LLM selection accuracy on commit (×3) | 2 | **5** | 3 | 4 |
| Hallucination resistance (×3) | 1 | **5** | 3 | 3 |
| Cold-context token cost (×2) | **5** | 4 | **5** | **5** |
| Grammar symmetry (compose/commit/rollback) (×2) | 1 | **5** | 3 | 4 |
| Schema clarity per call (×2) | 2 | **5** | 3 | 4 |
| Forward-extensibility (more txn verbs) (×1) | 3 | 3 | 2 | **5** |
| Refactor cost vs. status quo (×1) | **5** | 4 | 2 | 3 |
| Discoverability (telemetry, docs) (×1) | 3 | **5** | 4 | 4 |
| **Weighted total** | 28 | **63** | 41 | 52 |

(B) wins decisively on the weighted matrix. (D) is second; (C) is dominated; (A) — the status quo — is dominated.

### 2.5 What's wrong with each rejected option

**(A) is rejected** because:
- Routes a *core grammar verb* through a dispatcher whose docstring says it's for *the long tail*. Misuses its own contract.
- Forces the LLM to reproduce a magic-string `capability_id="scalpel.transaction.commit"` byte-exact. Per MCPVerse and MCP-Zero, this is the dominant LLM failure mode (~23-pt accuracy gap vs. named tool).
- `apply_capability`'s schema requires `file` and `range_or_name_path` parameters that don't make sense for transaction commit. Asymmetric edge case in the schema.
- The savings (one fewer always-on tool, ~1K cold tokens) is dwarfed by the per-call ergonomic and hallucination tax.

**(C) is rejected** because:
- Fuses two distinct semantic operations (preview vs. apply) into one tool with a Boolean flag. Violates KISS and single-responsibility.
- Requires the LLM to either re-pass `steps[]` (wasteful, drift-prone) or pass `transaction_id` as a discriminator (still magic-string-y).
- Loses the explicit two-phase grammar that makes compose/commit/rollback understandable as siblings.
- Adds a race condition: between preview and commit, files can drift; if the LLM re-passes `steps[]` instead of `transaction_id`, it silently re-previews instead of committing the previewed state.
- Still leaves rollback as a separate tool — solves nothing about the "commit-via-dispatcher" awkwardness while introducing new asymmetry between preview-flagged-compose and standalone-rollback.

**(D) is rejected for MVP** but kept on the v0.2.0 watch list because:
- Parameterized-verb pattern needs N ≥ 4 sibling actions to pay (MultiTool/Block). Today: 2 (commit, rollback) or possibly 3 (+ status). Not enough.
- The `Literal["commit","rollback","status"]` discriminator forces the LLM to reason about a state machine instead of picking a verb. Verbs are easier than state machines for tool selection (per Anthropic's Tool Search ranking, which favors verb-prefix matching).
- Worth revisiting **if** v0.2.0 adds `transaction_status`, `transaction_pause`, `transaction_resume`, `transaction_amend` — at that point N ≥ 4 and (D) becomes attractive.

---

## 3. Why (B) beats the budget objection

> "Every tool must justify its budget."

The 13th tool buys **four things** the dispatcher path cannot:

1. **Hallucination resistance.** No magic-string `capability_id`. The tool name is the contract; the schema is the only literal.
2. **Schema clarity.** One parameter (`transaction_id`), no awkward `file=""` / `range_or_name_path=""` placeholders.
3. **Grammar symmetry.** `dry_run_compose` / `transaction_commit` / `transaction_rollback` are *visibly* siblings. The LLM clusters them by name (per §5.3 of specialist-agent-ux.md) and routes by the cluster, not by remembering which verbs are "real" and which are dispatcher payloads.
4. **Telemetry honesty.** Today, commit calls are buried in `scalpel_apply_capability` traces and have to be filtered out by `capability_id`. With a sibling tool, commit-rate is a top-level metric (§7 below).

The 13th tool **costs**:

- ~1,000 cold-context tokens (one tool definition).
- ~0.1% selection-accuracy degradation per Speakeasy's 10→100 curve (sub-noise).
- One additional 30-word docstring to maintain.

**Verdict:** the four upsides clearly justify the ~1K-token cost. The "every tool must justify its budget" principle is satisfied — what the 13th tool buys is *measurable*, the cost is *bounded*, and the alternative (status quo) violates a stricter principle: *core verbs should not be dispatcher payloads*.

---

## 4. The `defer_loading: true` escape hatch — does it apply?

**No.** Anthropic's `defer_loading: true` is designed for tools that are **rarely used**: registered for completeness, retrieved by Tool Search when relevant query terms hit, but not loaded into cold context. Per Unified.to's published analysis, the right candidates for defer-loading are tools whose expected per-session call rate is < 1.

`scalpel_transaction_commit` is called **every time `scalpel_dry_run_compose` succeeds and the LLM decides to apply it**. That's effectively 1:1 with compose. Defer-loading commit means:

- The LLM calls `scalpel_dry_run_compose` (always-on).
- Tool Search must run to retrieve `scalpel_transaction_commit`.
- The LLM then calls commit.

This adds a Tool Search round-trip on the **happy path** of every transaction. Tool Search is cheap (~1.2K tokens for the search tool itself, ~1K per expanded tool) but not free — and the latency cost is real (one extra LLM-side resolution step).

**Defer-loading is the right answer for cold tools (per-language specialty facades). It is the wrong answer for core grammar verbs reached on every transaction.** The Anthropic docs are explicit on this distinction (Tool Search docs §"When to use defer_loading"): "Defer tools whose retrieval cost is amortized over many sessions; do not defer tools the model needs in every session."

---

## 5. Decision

**Adopt option (B): add `scalpel_transaction_commit` as a 13th always-on tool.**

The principle: **tool count should be minimized, but ergonomic verbs that complete a transaction grammar should be sibling tools, not dispatcher payloads.**

12 vs. 13 lives in the flat region of the tool-count-vs-accuracy curve. Going to 13 costs ~1K cold tokens and ~0.1% selection accuracy. Routing commit through the dispatcher costs *measurably more* on every commit call (per MCP-Zero's 23-pt gap on dispatcher-payload vs. named-tool invocation), violates the dispatcher's stated contract ("the long tail"), and forces the LLM to reproduce a magic-string id byte-exact (the dominant hallucination failure mode per MCPVerse).

The 13th tool earns its budget. The 12-tool budget was never sacred — it was a synthesis between specialists, and the synthesis explicitly flagged this as a deferred decision (mvp-scope-report.md §19 Q2).

### 5.1 The corrected always-on roster (13 tools)

The roster from §5.1 of the MVP scope report, with one addition:

```python
# ----- 5 ergonomic intent facades --------------------------------------
scalpel_split_file
scalpel_extract
scalpel_inline
scalpel_rename
scalpel_imports_organize

# ----- 1 long-tail dispatcher ------------------------------------------
scalpel_apply_capability

# ----- 2 catalog tools -------------------------------------------------
scalpel_capabilities_list
scalpel_capability_describe

# ----- 1 dry-run composer ----------------------------------------------
scalpel_dry_run_compose

# ----- 3 transaction-grammar tools (was 2; +commit) --------------------
scalpel_transaction_commit         # NEW: 13th tool
scalpel_transaction_rollback
scalpel_rollback                   # single-checkpoint, distinct from transaction

# ----- 1 diagnostics tool ----------------------------------------------
scalpel_workspace_health
```

### 5.2 Specification of the new tool

```python
def scalpel_transaction_commit(
    transaction_id: str,
) -> TransactionResult:
    """Commit a previewed transaction from dry_run_compose. Applies all steps
    atomically, captures one checkpoint per step. Idempotent on second call."""
```

- One parameter, no defaults that change semantics.
- Returns the existing `TransactionResult` schema (§11.4 of specialist-agent-ux.md).
- **Idempotent on second call:** if the transaction is already committed, returns the original result with a `warnings: ["transaction already committed"]` flag. This prevents double-commit hallucinations.
- Errors: `TRANSACTION_NOT_FOUND` (id not in transaction store), `PREVIEW_EXPIRED` (TTL elapsed), `TRANSACTION_ABORTED` (a step's preview was invalidated by drift), `APPLY_FAILED` (commit-time failure).
- Docstring: 22 words. Within the 30-word cap.

### 5.3 What changes downstream

| File / section | Change |
|---|---|
| `mvp-scope-report.md` §1.1 (TL;DR) | "12 always-on tools" → "13 always-on tools (commit promoted from dispatcher payload)". |
| `mvp-scope-report.md` §5.1 | Add `scalpel_transaction_commit` definition; renumber surrounding text. |
| `mvp-scope-report.md` §5.5 | Replace `scalpel_apply_capability(capability_id="scalpel.transaction.commit", ...)` with `scalpel_transaction_commit(transaction_id=...)`. |
| `mvp-scope-report.md` §5.6 | Worked-example turn 3 swaps to the new tool. |
| `mvp-scope-report.md` §6.1 | Update count: "12 always-on + ~11 deferred" → "13 always-on + ~11 deferred". |
| `specialist-agent-ux.md` §3.1 (12-tool table) | Promote to 13. |
| `specialist-agent-ux.md` §15.4 | Mark resolved; link to this document. |
| `specialist-agent-ux.md` §4.5 (token budget) | Cold context becomes ~14.2K tokens (+1K for the 13th tool); still well under the 25K MCP-chatter pain point. |
| Capabilities catalog | `capability_id="scalpel.transaction.commit"` is *deprecated* but kept for one minor version (back-compat for any code paths that call it). The catalog entry's `preferred_facade` field points to `scalpel_transaction_commit`. |

The migration is mechanical. No protocol changes; no Pydantic schema breakage; no test-fixture rewrites. The `scalpel.transaction.commit` capability_id continues to work as a deprecated alias for the duration of v0.1.x, then is removed in v0.2.0.

---

## 6. Cross-check: ergonomics scorecard for the 5-turn workflow

Tokens per turn-3 commit call, including the LLM's reasoning overhead to generate a valid call:

| Option | Bytes on the wire | LLM tokens on the wire | Hallucination risk | Schema-fit clean? |
|---|--:|--:|---|:--:|
| A | ~140 | ~95 | **High** (`capability_id` magic string + empty `file`/`range_or_name_path`) | No |
| B | ~50 | **~25** | **Low** (one parameter, named tool) | **Yes** |
| C | ~150 | ~80 | Medium (Boolean discriminator + re-passing steps or transaction_id) | No |
| D | ~70 | ~40 | Medium (`action="commit"` literal + state-machine reasoning) | Yes (but premature) |

(B) is shortest in tokens and highest in schema fit. (A) is worst on both axes despite carrying one fewer always-on tool.

---

## 7. Post-MVP telemetry to validate or revisit this decision

Per `mvp-scope-report.md` §12.6, every tool call is logged. With (B) adopted, the relevant fields and the questions they answer:

| Field | Question it answers |
|---|---|
| `tool_name="scalpel_transaction_commit"` count per session | Is commit actually called? If 0 over many sessions, the whole compose-commit cycle is unused → simplify in v0.2.0 (collapse compose to immediate apply). |
| `tool_name="scalpel_transaction_commit"` failure rate (`disposition=err`) | Does the dedicated tool reduce commit-time hallucinations vs. the historical dispatcher path? Compare to archived telemetry from any pre-13-tool builds. |
| `tool_name="scalpel_apply_capability" AND args_summary.capability_id=="scalpel.transaction.commit"` count | **Anti-metric.** If non-zero, the LLM is still using the deprecated dispatcher path — log a warning and surface in v0.2.0 release notes. Should hit 0 within one release of (B) shipping. |
| `tool_name="scalpel_dry_run_compose" AND no subsequent transaction_commit within 5 minutes` | Compose-without-commit rate. High rate → the LLM is using compose as a dry-run probe and abandoning. Tells us whether the transaction grammar is worth keeping in v0.2.0 or whether dry-run-only previews are the dominant pattern. |
| `tool_name="scalpel_transaction_commit"` median time-to-call after compose | If consistently sub-second, the LLM treats commit as a pure follow-up and (C)'s fused tool would have been fine. If multi-turn (LLM thinks between preview and commit), the two-phase split is buying real ergonomic value. |
| `tool_search_expanded` containing `scalpel_transaction_*` deferred candidates | Sanity check: confirm Tool Search is not retrieving txn tools (they're always-on, so this should always be empty). Non-empty = registration bug. |
| Future: count of distinct transaction-grammar verbs called per session | If the surface grows to ≥4 sibling verbs (commit, rollback, status, amend, …), revisit (D) — the parameterized form pays at N ≥ 4. |

### 7.1 Promotion / demotion criteria for v0.2.0

- **Keep (B)** if `transaction_commit` call count is ≥ 50% of `dry_run_compose` call count (i.e., LLMs commit most previews) and commit-time hallucination rate is below 1%.
- **Demote to dispatcher-only** (revert toward A) if `transaction_commit` is called < 5% of sessions over 30 days — would mean the transaction grammar is unused in practice and the 13th tool is dead weight.
- **Promote to (D)** if v0.2.0 adds ≥ 2 more transaction verbs, bringing total to ≥ 4 — at that point parameterized form pays.

---

## 8. Final answer

**Promote `scalpel_transaction_commit` to the always-on roster as the 13th tool.** The 12-tool budget was a synthesis target, not a hard ceiling; 12-vs-13 lives in the flat region of the tool-count-vs-accuracy curve (per Anthropic, Speakeasy, and Copilot's published evidence), so the marginal cost is ~1K cold tokens and ~0.1% accuracy — sub-noise. Routing a *core grammar verb* through `scalpel_apply_capability` violates the dispatcher's stated "long-tail" contract and forces the LLM to reproduce a magic-string `capability_id` byte-exact, which MCP-Zero and MCPVerse identify as the dominant hallucination failure mode (~23-pt gap). The four wins — hallucination resistance, schema clarity, grammar symmetry across compose/commit/rollback, and honest telemetry — clearly earn the 13th tool's budget. `defer_loading: true` is the wrong escape hatch because commit is reached on the happy path of every transaction, not occasionally. Pattern (D) — parameterized `scalpel_transaction(action=...)` — is premature for the current 2-verb transaction set but should be reconsidered in v0.2.0 if the grammar grows to ≥ 4 verbs. Update `mvp-scope-report.md` §5.1, §5.5, §5.6, §6.1; add the new tool's Pydantic stub; deprecate the `scalpel.transaction.commit` capability_id alias for one minor version.

---

## 9. References

- Anthropic — Tool Search Tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- Anthropic — Code execution with MCP: https://www.anthropic.com/engineering/code-execution-with-mcp
- Speakeasy — 100× token reduction with dynamic toolsets: https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets
- Jentic — The MCP Tool Trap: https://jentic.com/blog/the-mcp-tool-trap
- Jenova.ai — MCP tool scalability: https://www.jenova.ai/en/resources/mcp-tool-scalability-problem
- atcyrus — Claude Code MCP tool curation guide: https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide
- Unified.to — Scaling MCP Tools with Defer Loading: https://unified.to/blog/scaling_mcp_tools_with_anthropic_defer_loading
- arXiv — MCPVerse: https://arxiv.org/html/2508.16260v2
- arXiv — MCP-Zero: https://arxiv.org/pdf/2506.01056

---

**End of resolution document.**
