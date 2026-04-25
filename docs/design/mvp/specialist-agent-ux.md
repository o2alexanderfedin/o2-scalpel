# MVP Agent/UX Specialist — o2.scalpel LLM-facing Tool Surface (v2: full LSP coverage)

**Specialist role:** Agentic-AI UX / MCP surface.
**Scope:** What the LLM caller actually sees under the **full-coverage** directive — every chosen LSP's task-level capabilities are reachable, without blowing past the practical tool-selection ceiling.
**Audience:** orchestrator + downstream implementers wiring the v2 MCP server.
**Status:** report-only. No code written.
**Date:** 2026-04-24.
**MVP languages:** Rust AND Python; surface is forward-extensible to TypeScript / Go / clangd.
**Supersedes:** `archive-v1-narrow/specialist-agent-ux.md` (4-tool collapse). That document is preserved as the narrower fallback.

Cross-reference:

- [main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — §3 facades, §4 server extensions, §5 LanguageStrategy, §Workflow.
- [archive-v1-narrow/specialist-agent-ux.md](archive-v1-narrow/specialist-agent-ux.md) — narrower prior position (4 tools).
- [archive-v1-narrow/2026-04-24-mvp-scope-report.md](archive-v1-narrow/2026-04-24-mvp-scope-report.md) — orchestrator's prior MVP scope.
- [dx-facades-brief](../../research/2026-04-24-dx-facades-brief.md) — upstream facade rationale.
- [mcp-lsp-protocol-brief](../../research/2026-04-24-mcp-lsp-protocol-brief.md) — error codes, two-phase resolve, indexing.

---

## 0. Executive summary

The previous MVP collapsed to 4 tools by chopping LSP depth. The new directive reverses that: **every chosen LSP's refactor surface must be reachable**. Naïve enumeration produces ~25–35 tools (~12–20 Rust facades + ~10–15 Python facades + cross-language plumbing), which past published evidence shows degrades LLM tool-selection accuracy by 10–30% before any work begins, and burns 50–134K context tokens on definitions alone.

The recommended ceiling is **~12 always-on tools** (within the safe band documented by Anthropic, GitHub Copilot, Block, and Speakeasy), with the rest reachable via two well-known patterns: **(E) hybrid** — a small fixed "happy path" facade set + a generic `apply_capability` primitive — combined with **(D) dynamic registration** via `defer_loading` so deferred tools are searchable but not loaded into the cold context. A "capabilities catalog" tool (`capabilities_list`) is the discovery surface for the long tail.

**Canonical MVP surface: 12 user-visible tools.** 5 always-on intent facades (`scalpel_split_file`, `scalpel_extract`, `scalpel_inline`, `scalpel_rename`, `scalpel_imports_organize`), 3 always-on primitives (`scalpel_apply_capability`, `scalpel_capabilities_list`, `scalpel_dry_run_compose`), 2 always-on safety tools (`scalpel_rollback`, `scalpel_transaction_rollback`), and 2 always-on diagnostics tools (`scalpel_workspace_health`, `scalpel_capability_describe`). Language-specific specialty facades (e.g., `scalpel_rust_lifetime_elide`, `scalpel_py_type_annotate`) are registered with `defer_loading: true` so they exist but only enter context when Tool Search retrieves them.

Naming uses an `intent_object` convention (`scalpel_<area>_<verb>`) so the LLM clusters tools by area at selection time. Docstrings are capped at 30 words. Errors expand from 6 codes to **10**, all with one-line repair patterns. `dry_run` becomes composable via `scalpel_dry_run_compose(steps[])`, returning a single `transaction_id` whose `commit` runs all steps atomically. Telemetry per call records `tool_name, language, capability_id, dry_run, disposition, checkpoint_lineage` so post-MVP we can prune cold tools.

This is the LLM-usable shape of full LSP coverage.

---

## 1. Total-tool-budget analysis

### 1.1 The published evidence

| Source | Finding | Implication for o2.scalpel |
|---|---|---|
| Anthropic Tool Search Tool docs | Selection accuracy "degrades significantly once you exceed 30–50 available tools." Internal Opus 4 MCP eval improved 49% → 74% with Tool Search; Opus 4.5 improved 79.5% → 88.1%. ([source](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)) | Hard ceiling ~30 always-on; aim much lower for cold-context safety. |
| GitHub Copilot | Cut tool count 40 → 13, observed measurable benchmark gains. ([source](https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide)) | 13 is a working production target. |
| Block (Linear MCP) | Rebuilt 30+ tools → 2 across three iterations. ([source](https://www.jenova.ai/en/resources/mcp-tool-scalability-problem)) | Aggressive consolidation pays off. |
| Speakeasy benchmark | All models show ~10% degradation as tool count grows 10 → 100; agentic Claude-4-class models cope better. ([source](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets)) | Each added tool has a measurable accuracy cost. |
| Production MCP setups | 5-server / 58-tool config burns ~55K tokens before user input; 134K observed pre-optimization. ([source](https://www.anthropic.com/engineering/code-execution-with-mcp)) | Tool definitions are the dominant context line item. |
| Jentic "MCP Tool Trap" | "5–7 tools represent the practical upper limit for consistent accuracy without specialized filtering." ([source](https://jentic.com/blog/the-mcp-tool-trap)) | 5–7 is the *no-mitigations* sweet spot. |
| MCPVerse / MCP-Bench | Single-turn accuracy under 20% on hard configurations; tool hallucination is the dominant failure mode. ([source](https://arxiv.org/html/2508.16260v2)) | Must design for hallucination-resistance, not raw count. |

### 1.2 Recommended ceilings

| Band | Always-on count | Tool-selection accuracy | Context cost | Notes |
|---|---|---|---|---|
| Tight (no mitigations) | ≤ 7 | Best | ~5–8K tokens | The narrow v1 MVP lived here. |
| **Recommended (mitigated)** | **≤ 12–15** | Very good with disciplined naming + Tool Search for the long tail | **~10–15K tokens** | Our target. |
| Risky | 20–30 | Visible degradation; needs Tool Search to recover | 20–35K | Avoid unless unavoidable. |
| Hostile | > 30 | Hallucinations dominate without filtering | 35K+ | Only viable with `defer_loading` everywhere. |

**Recommendation: target 12 always-on tools.** Specialty per-language assists ride on `defer_loading: true` and are reached via `capabilities_list` + `apply_capability`. This stays in the *Recommended* band cold and degrades to *Risky* only when Tool Search expands many specialty tools at once — which is naturally bounded by the LLM's task focus.

### 1.3 Why 12 and not 7

The narrow v1 hit 4–7 by amputating LSP depth. The new directive forbids that. The minimum viable always-on set under full coverage is:

- 5 intent facades (split, extract, inline, rename, organize-imports) — these are the verbs an LLM reaches for first.
- 1 generic capability dispatcher (`apply_capability`) — without this, every non-faceted assist needs its own tool, blowing past 30.
- 1 capabilities catalog (`capabilities_list`) — the LLM's discovery surface.
- 1 capability inspector (`capability_describe`) — pre-call confirmation.
- 1 dry-run composer (`dry_run_compose`) — preview chained refactors before any commit.
- 2 rollback tools (single-checkpoint, multi-step transaction).
- 1 health probe (`workspace_health`) — indexing readiness, LSP version, capability matrix.

= 12. Removing any of these forces the LLM to either (a) call a primitive it doesn't know about or (b) blindly chain `apply_capability` without inspection — both worse on the selection-accuracy axis than carrying the extra docstring.

---

## 2. Architecture options for full coverage

Five candidate shapes, evaluated against the same matrix.

### 2.1 The five options

| Option | Sketch | Always-on tools | Long-tail mechanism |
|---|---|---:|---|
| **A** | Generic `apply_code_action` + `list_code_actions` + a few facades | 5–7 | LLM picks raw LSP `kind` strings |
| **B** | Parameterized facades: `refactor_extract(kind, …)` where `kind` enumerates extract-* assists | 7–10 | Discriminated unions inside one tool |
| **C** | Per-language namespaces: `rust_refactor_*`, `python_refactor_*` as disjoint sets | 25–35 | Direct enumeration |
| **D** | Dynamic registration: `defer_loading: true`; tools appear based on `.lsp.json` discovery | 8–12 (hot) + N deferred | Anthropic Tool Search |
| **E** | Hybrid: small fixed high-level facades + `apply_capability(capability_id, …)` long-tail | 10–14 | Capability catalog + generic dispatcher |

### 2.2 Decision matrix

Scoring 1–5 (5 = best) on the brief's evaluation axes.

| Axis | A | B | C | D | E |
|---|---:|---:|---:|---:|---:|
| LLM selection accuracy (cold) | 4 | 4 | 1 | 4 | 4 |
| LLM selection accuracy (after Tool Search) | 3 | 3 | 4 | **5** | **5** |
| MCP protocol overhead | **5** | 4 | 1 | 3 | 3 |
| Discoverability for the LLM | 2 | 3 | 4 | 3 | **5** |
| Discoverability for users (docs, marketplaces) | 3 | 3 | **5** | 3 | 4 |
| Documentation cost | **5** | 3 | 1 | 2 | 3 |
| Cross-language consistency | **5** | 4 | 1 | 4 | **5** |
| Long-tail completeness | 2 | 3 | **5** | 4 | **5** |
| Hallucination risk (LLM invents kinds) | 1 | 2 | 4 | 4 | 4 |
| Forward-compatibility (new languages) | 3 | 3 | 1 | 4 | **5** |
| **Weighted total** (long-tail + accuracy weighted ×2) | 31 | 31 | 28 | **39** | **45** |

### 2.3 Recommendation: **E (Hybrid) backed by D (Dynamic registration)**

The hybrid wins because it gets the high-frequency happy path *named* (where docstrings + naming-scheme conventions can do real selection-accuracy work) and pushes the long tail into a discoverable catalog (`capabilities_list`) with a generic dispatcher (`apply_capability`). Adding D's `defer_loading: true` for specialty facades means we keep the option of named facades without paying their context cost upfront.

**Fallback: D pure.** If `apply_capability` proves under-discoverable in MVP testing (the LLM forgets it exists), promote the most-called specialty capabilities to always-on facades and demote less-called ones to `defer_loading`.

### 2.4 What's rejected and why

- **C is rejected.** 25+ always-on tools is a cold-context disaster. Anthropic's own evidence puts this firmly in the *Risky/Hostile* band.
- **B is rejected as a primary surface** (the discriminator does double duty — both a parameter and a tool-selection signal — which confuses LLMs per the MCP Tool Trap analysis), but kept as a *secondary* pattern: `scalpel_extract` is parameterized over `target ∈ {variable, function, module, type_alias, struct_from_enum_variant}`.
- **A alone** is rejected because requiring the LLM to author raw LSP `kind` strings is a hallucination magnet (per MCPVerse benchmarks). It's used only inside `apply_capability`, where the `capability_id` is a stable o2.scalpel-issued token, not the raw LSP kind.

---

## 3. Canonical MVP tool surface (full coverage)

### 3.1 The 12 always-on tools

| # | Name | Language | Docstring (≤30 words) | Priority | Architecture-option |
|--:|---|---|---|:---:|:---:|
| 1 | `scalpel_split_file` | both | Split a source file into N modules by moving named symbols. Returns diff + diagnostics_delta + preview_token. Atomic. | P0 | E (high-level facade) |
| 2 | `scalpel_extract` | both | Extract a symbol or selection into a new variable, function, module, or type. Pick `target` to choose. Atomic. | P0 | B inside E |
| 3 | `scalpel_inline` | both | Inline a function, variable, or type alias at its definition or all call-sites. Pick `target`. Atomic. | P0 | B inside E |
| 4 | `scalpel_rename` | both | Rename a symbol everywhere it is referenced. Cross-file. Returns checkpoint_id. Hallucination-resistant on name-paths. | P0 | E (high-level facade) |
| 5 | `scalpel_imports_organize` | both | Add missing, remove unused, reorder imports across files. Idempotent; safe to re-call. | P0 | E (high-level facade) |
| 6 | `scalpel_apply_capability` | both | Apply any registered capability by `capability_id` from `capabilities_list`. The long-tail dispatcher. Atomic. | P0 | A inside E |
| 7 | `scalpel_capabilities_list` | both | List capabilities for a language with optional filter. Returns capability_id + title + applies_to_kinds. | P0 | E (catalog) |
| 8 | `scalpel_capability_describe` | both | Return full schema, examples, and pre-conditions for one capability_id. Call before invoking unknown capabilities. | P0 | E (catalog) |
| 9 | `scalpel_dry_run_compose` | both | Preview a chain of refactor steps without committing any. Returns transaction_id; commit applies all steps atomically. | P0 | E (composability) |
| 10 | `scalpel_rollback` | both | Undo a refactor by checkpoint_id. Idempotent: second call is no-op. | P0 | primitive |
| 11 | `scalpel_transaction_rollback` | both | Undo all checkpoints in a transaction (from dry_run_compose) in reverse order. Idempotent. | P0 | primitive |
| 12 | `scalpel_workspace_health` | both | Probe LSP servers: indexing state, registered capabilities, version. Call before refactor sessions. | P0 | diagnostics |

### 3.2 Deferred specialty tools (`defer_loading: true`)

These are registered but do **not** load into cold context. The LLM finds them via Tool Search when relevant. Counts here are illustrative; final list follows from per-LSP capability inventory.

| # | Name | Language | Docstring (≤30 words) | Priority | Architecture-option |
|--:|---|---|---|:---:|:---:|
| 13 | `scalpel_rust_lifetime_elide` | rust | Apply rust-analyzer's lifetime elision/explicit assists to a function signature. Atomic. | P1 | D (deferred) |
| 14 | `scalpel_rust_impl_trait` | rust | Generate a missing `impl Trait` for a type via rust-analyzer's add-missing-impl-members assist. | P1 | D |
| 15 | `scalpel_rust_match_to_iflet` | rust | Convert `match` ↔ `if let` chains. rust-analyzer rewrite kind. | P2 | D |
| 16 | `scalpel_rust_qualify_path` | rust | Qualify or unqualify a path. Useful before/after import organization. | P2 | D |
| 17 | `scalpel_rust_promote_inline_module` | rust | Promote `mod foo {…}` to `foo.rs`. Rust-only equivalent of split. | P1 | D |
| 18 | `scalpel_rust_extract_struct_from_variant` | rust | Pull data of an enum variant out into a named struct. | P2 | D |
| 19 | `scalpel_py_async_ify` | python | Convert a sync function and its propagated callsites to async. Pyright/refurb-driven. | P1 | D |
| 20 | `scalpel_py_type_annotate` | python | Add or refine type hints on a function/class via pyright inference. Idempotent. | P1 | D |
| 21 | `scalpel_py_dataclass_from_dict` | python | Convert a dict-shaped class or factory into a `@dataclass`. | P2 | D |
| 22 | `scalpel_py_promote_method_to_function` | python | Promote a method to a module-level function (Pyright/Pyrefly assist). | P2 | D |
| 23 | `scalpel_execute_command` | both | Server-specific JSON-RPC pass-through, whitelisted per `LanguageStrategy`. Power-user escape hatch. | P2 | D |

**Total surface: 12 always-on + ~11 deferred = ~23 tools.** Hot context cost is bounded by the always-on 12 (~10–15K tokens). The deferred set can grow to 30+ over time without changing the cold-context cost.

### 3.3 Why this hits ≤15 visible

The brief asks for ≤15 user-visible tools. Two readings:

1. **User-visible to the LLM at any one time:** 12 (always-on) + however many Tool Search expanded (typically 1–3 per turn). Stays within band.
2. **User-visible in the marketplace listing / docs:** all 23, plus a "see also: capabilities catalog with N additional capabilities" pointer. Honest.

Both readings hold. We do not lie about what's there.

### 3.4 The capability catalog: where the rest live

`scalpel_capabilities_list(language="rust")` returns up to ~80 entries for rust-analyzer (158 assists filtered by relevance to refactoring intent) and ~50 entries for the Python LSP stack (pyright + ruff + pyrefly). Each entry is a small descriptor (§6.2), not a tool definition — total wire cost is one tool call, not 130 tool definitions. The LLM uses it like shell tab-completion.

---

## 4. Docstring economics

### 4.1 The token math

Anthropic's published numbers: ~1K tokens per typical MCP tool definition (name + description + JSON schema). 12 always-on tools × 1K = 12K tokens cold. 23 tools × 1K = 23K. Cutting docstrings hard wins ~3–5K back.

### 4.2 The 30-word docstring template

```
<verb-phrase>. <key-shape-or-mode-clause>. <atomicity-or-idempotency-clause>.
```

Three sentences, hard cap 30 words including punctuation. Examples already in §3.1. Rules:

- **First sentence: imperative verb.** "Split", "Extract", "Inline", "Rename", "Organize", "Apply", "List", "Describe", "Preview", "Undo", "Probe". The LLM tokenizes verbs first when choosing.
- **Second sentence: discriminator.** What sets this tool apart from siblings. For `scalpel_extract`: "Pick `target` to choose." That single clause routes the LLM to the right parameter.
- **Third sentence: contract bit.** "Atomic." or "Idempotent." or "Returns checkpoint_id." LLMs use these as retry-decision signals.

Anything longer goes to a `capability_describe(capability_id)` lookup or a SKILL.md page. Docstrings are *router signage*, not documentation.

### 4.3 The "describe once, use many" pattern

The 30-word docstring buys the LLM enough to *route*. To *invoke* a non-trivial tool the LLM either has prior knowledge or calls `scalpel_capability_describe(capability_id="…")` (for capability-bag cases) or examines the JSON schema. Schemas live in MCP's standard `inputSchema` field — not in the docstring — and are loaded lazily by Anthropic's tool-loading machinery for deferred tools.

### 4.4 Capabilities-catalog response schema

Compact. ≤80 chars per entry on the wire.

```json
{
  "language": "rust",
  "capabilities": [
    {
      "capability_id": "rust.refactor.extract.module",
      "title": "Extract symbols into module",
      "applies_to_kinds": ["function","struct","enum","impl","trait"],
      "lsp_kind": "refactor.extract.module",
      "preferred_facade": "scalpel_split_file"
    },
    {
      "capability_id": "rust.refactor.inline.function",
      "title": "Inline function at all call sites",
      "applies_to_kinds": ["function"],
      "lsp_kind": "refactor.inline",
      "preferred_facade": "scalpel_inline"
    }
  ]
}
```

`preferred_facade` lets the LLM short-circuit: if the capability has a high-level facade, the LLM should prefer it (better defaults, better errors, hallucination-resistant inputs).

### 4.5 Estimated token budget

| Cost | Tokens |
|---|---:|
| 12 always-on tool definitions @ ~1K each | 12,000 |
| Tool Search Tool itself | ~1,200 |
| Cold context for o2.scalpel | **~13.2K** |
| Per-call: capabilities_list(rust) response | ~3K (one-shot, cached by LLM in the turn) |
| Per-call: capability_describe(...) response | ~400 |
| Avg deferred-tool expand per turn | ~1K × 1–3 = 1–3K |

**Hot context typically 13–17K**, well under the 25K MCP-chatter pain point that production teams report.

---

## 5. Tool-selection prompting hints (naming scheme)

scalpel can't edit Anthropic's system prompt, but it owns the strings the model selects against.

### 5.1 The recommended scheme

**Pattern: `scalpel_<area>_<verb>` or `scalpel_<verb>_<object>`.**

| Cluster prefix | Tools | Why |
|---|---|---|
| `scalpel_split_*` / `scalpel_extract_*` / `scalpel_inline_*` / `scalpel_rename_*` | high-level intent verbs | LLM reaches for the verb; cluster keeps siblings nearby |
| `scalpel_imports_*` | `scalpel_imports_organize` | "imports" is the object; organize is the action |
| `scalpel_capabilities_*` / `scalpel_capability_*` | `_list`, `_describe` | catalog cluster — singular vs. plural is intentional, mirrors REST list/get |
| `scalpel_dry_run_*` | `scalpel_dry_run_compose` | dry-run cluster — leaves room for `_status`, `_abort` later |
| `scalpel_rollback`, `scalpel_transaction_rollback` | `_*rollback` suffix | safety cluster grouped by suffix |
| `scalpel_workspace_*` | `scalpel_workspace_health` | diagnostics cluster |
| `scalpel_apply_capability` | the dispatcher | unique; not in any cluster — distinct verb signals "fall back to me" |
| `scalpel_rust_*`, `scalpel_py_*` | language-specialty deferred set | language prefix tells the LLM "skip if file isn't this language" |

### 5.2 Anti-collision with Claude Code's built-in `LSP` umbrella

Claude Code ships an `LSP` tool with read-only operations using LSP method names (`definition`, `references`, `hover`, `documentSymbol`). Our tools must use **refactor-intent verbs**, not LSP method names. Banned tool names: `scalpel_definition`, `scalpel_references`, `scalpel_hover`, `scalpel_completion`, `scalpel_format` — these collide semantically with read-only built-ins and confuse the router.

### 5.3 Anti-collision with each other

No tool shares both a verb and an object with another. `scalpel_extract` (high-level facade, parameterized over `target`) is the only `extract*` always-on tool; deferred specialty extracts use `scalpel_<lang>_extract_<thing>` (e.g., `scalpel_rust_extract_struct_from_variant`) so the LLM can disambiguate.

### 5.4 Verb stop-list

These verbs are too generic and trigger over-broad LLM calls. **Banned at the always-on tier:** `move`, `refactor`, `transform`, `update`, `fix`, `change`, `do`, `run`. (`fix_imports` from v1 is renamed to `scalpel_imports_organize` precisely for this reason — "fix" invites every cleanup-shaped intent.)

### 5.5 Cluster sizes

Empirical guidance from the GitHub Copilot experience: ≤4 tools per intent cluster. Beyond that, the LLM treats them as interchangeable and routes randomly. Our biggest cluster is `scalpel_extract` (one always-on + a few deferred specialty extracts) → still well under 4 hot.

---

## 6. The capabilities catalog pattern

Like shell tab-completion, but the LLM is the shell.

### 6.1 The contract

```python
def scalpel_capabilities_list(
    language: Literal["rust", "python"] | None = None,  # null = all
    filter_kind: str | None = None,                     # e.g. "refactor.extract"
    applies_to_symbol_kind: str | None = None,          # e.g. "function"
) -> list[CapabilityDescriptor]:
    """List capabilities. Cheap, cached. The LLM's tab-completion."""

def scalpel_capability_describe(
    capability_id: str,
) -> CapabilityFullDescriptor:
    """Full schema + example + pre-conditions for one capability_id."""

def scalpel_apply_capability(
    capability_id: str,
    file: str,
    range_or_name_path: Range | str,
    params: dict = {},
    dry_run: bool = False,
    preview_token: str | None = None,
) -> RefactorResult:
    """Apply a capability. The long-tail dispatcher."""
```

### 6.2 Descriptor shapes

```python
class CapabilityDescriptor(BaseModel):
    capability_id: str             # "rust.refactor.extract.module"
    title: str                     # "Extract symbols into module"
    applies_to_kinds: list[str]    # ["function","struct","impl"]
    lsp_kind: str                  # "refactor.extract.module"
    preferred_facade: str | None   # "scalpel_split_file" or null

class CapabilityFullDescriptor(CapabilityDescriptor):
    description: str               # 1–2 sentences, freeform
    params_schema: dict            # JSON Schema for `params`
    requires: list[str]            # ["selection","name_path","cursor"]
    side_effects: list[str]        # ["creates_files","cross_file_edits"]
    example_invocation: dict       # full apply_capability call
    failure_modes: list[str]       # error codes likely to fire
```

### 6.3 Why this pattern beats per-capability tools

| Concern | Per-tool surface | Catalog + dispatcher |
|---|---|---|
| Cold-context tokens | 1K × N | 1K × 3 (the catalog tools) |
| Tool-selection accuracy | Degrades past 30 | Bounded — only catalog tools compete |
| New capability rollout | New tool definition + docs + version bump | Add row to catalog; zero schema change |
| Cross-language consistency | Per-language duplication | Single dispatcher, language-tagged ids |
| Hallucination | LLM invents tool names | LLM must echo a `capability_id` from `capabilities_list` |

### 6.4 The "preferred_facade" pull

When `capabilities_list` returns a row whose `preferred_facade` is non-null, scalpel's contract is: **using the dispatcher works, but the named facade is strictly better.** Better error messages, better dry-run preview, better hallucination resistance. The LLM is encouraged (in `scalpel_capabilities_list`'s docstring and in returned warnings) to call the facade where one exists.

This makes the always-on facade set a *cache* over the catalog. New facades get promoted from the catalog when telemetry shows high usage; cold facades get demoted to deferred. Self-healing.

### 6.5 Caching and freshness

- `capabilities_list(language=…)` is computed at MCP server startup and on `LanguageStrategy` reload. Cached per language. ~3K tokens uncompressed.
- Per-LSP indexing state can change which capabilities are *currently* applicable; the catalog reports static availability. Dynamic applicability is checked by `apply_capability` at invocation time and surfaces as `NOT_APPLICABLE` (§7).

---

## 7. Error-code taxonomy expansion (10 codes)

The narrow v1 had 6 codes; full coverage adds 4 for the new shapes.

| # | Code | When | Repair pattern (one line) | Retryable |
|--:|---|---|---|:---:|
| 1 | `STALE_VERSION` | File version drifted between operations | Re-issue the call; idempotent facades treat moved symbols as no-ops | yes |
| 2 | `NOT_APPLICABLE` | LSP has no action of requested kind here, or `disabled.reason` set | Read `reason`; widen range or change cursor; retry once | once |
| 3 | `INDEXING` | LSP cold-starting / re-indexing | Wait `estimated_wait_ms`; or call `scalpel_workspace_health` | yes after wait |
| 4 | `APPLY_FAILED` | WorkspaceEdit apply errored, rolled back | Inspect `failed_stage`; adjust `reexport_policy` to explicit and retry | conditional |
| 5 | `PREVIEW_EXPIRED` | `preview_token` past TTL or invalidated by file change | Re-issue the `dry_run=true` call | yes |
| 6 | `SYMBOL_NOT_FOUND` | Name-path resolved 0 or >1 (shape unified per v1) | Pick from `candidates[]`; retry with exact path | yes |
| 7 | **`CAPABILITY_NOT_AVAILABLE`** *(new)* | `capability_id` not registered for the file's language | Call `scalpel_capabilities_list(language=...)`; pick a registered id | yes |
| 8 | **`SERVER_REQUIRED`** *(new)* | Capability needs an LSP whose server is not reachable | Run `scalpel_workspace_health`; install/start the LSP plugin | conditional |
| 9 | **`MULTIPLEX_AMBIGUOUS`** *(new)* | Cross-language operation matched assists in 2+ LSPs | Pick `language` explicitly; or scope `files` to one language | yes |
| 10 | **`TRANSACTION_ABORTED`** *(new)* | A step in `dry_run_compose` failed; later steps did not run | Inspect `failed_step_index`; fix that step's params; recompose | yes |

### 7.1 Error response shape (unchanged from v1)

```json
{
  "error": "CAPABILITY_NOT_AVAILABLE",
  "message": "capability_id 'rust.refactor.lifetime.elide' not registered for python",
  "hint": "Call scalpel_capabilities_list(language='python') to discover available capabilities.",
  "retryable": true,
  "candidates": ["python.refactor.extract.function","python.refactor.inline.variable"]
}
```

### 7.2 The four new codes in detail

**`CAPABILITY_NOT_AVAILABLE`** — issued when `apply_capability` is called with a `capability_id` that doesn't exist for the resolved language. `candidates[]` carries the closest 5 ids by Levenshtein distance. The LLM's repair: re-call `capabilities_list` and pick again. This code distinguishes "the capability id is wrong" from "the capability is fine but doesn't apply here" (`NOT_APPLICABLE`).

**`SERVER_REQUIRED`** — issued when scalpel's `LanguageStrategy` resolves the file but the underlying LSP server is unreachable (not installed, crashed, or not configured in `.lsp.json`). Carries `language`, `lsp_name`, and an `install_hint`. Not recoverable in-turn; LLM should surface to user with the `install_hint`.

**`MULTIPLEX_AMBIGUOUS`** — issued by tools that span multiple files (e.g., `scalpel_imports_organize(files=["**"])` across a polyglot repo) when the file set spans multiple LSPs and the requested operation has different semantics per-language. The LLM's repair: pass `language=...` explicitly or narrow `files`. Tells the LLM "your call straddles languages; pick one."

**`TRANSACTION_ABORTED`** — issued by `scalpel_dry_run_compose` and its commit when a chained step fails. Carries `failed_step_index`, the per-step `failure` object, and a `partial_changes` summary up to the failed step. Earlier successful steps' edits are *not* applied (the whole transaction is virtual until commit).

### 7.3 The retryable flag — explicit table

LLMs misuse `retryable` if it isn't crisp. Codified:

| Code | retryable? | Same-turn retry budget |
|---|---|---:|
| `STALE_VERSION` | true | 2 |
| `NOT_APPLICABLE` | true | 1 |
| `INDEXING` | true | 1 (after wait) |
| `APPLY_FAILED` | conditional | 1 |
| `PREVIEW_EXPIRED` | true | 2 |
| `SYMBOL_NOT_FOUND` | true | 2 |
| `CAPABILITY_NOT_AVAILABLE` | true | 1 |
| `SERVER_REQUIRED` | conditional | 0 (escalate) |
| `MULTIPLEX_AMBIGUOUS` | true | 1 |
| `TRANSACTION_ABORTED` | true | 1 |

Cumulative retry budget per turn: ≤3 retries across all errors before the LLM should escalate to the user. This isn't enforceable by scalpel; it's documented in the always-on tools' SKILL.md (§12.4 of the v1 doc, ported).

---

## 8. `dry_run` and checkpoints for bulk assists

Full coverage means a refactor session might chain 5+ assists (extract-module → organize-imports → rename → inline-helper → organize-imports). `dry_run` must scale.

### 8.1 The two `dry_run` modes

**Single-call `dry_run=true`** (unchanged from v1). One tool, one preview, one `preview_token`. Commit with `dry_run=false` + `preview_token`. Byte-identical guarantee while token is valid (5-min TTL).

**Composed `dry_run` via `scalpel_dry_run_compose(steps[])`** (new for v2). Preview a sequence virtually; commit all-or-nothing.

### 8.2 The compose contract

```python
def scalpel_dry_run_compose(
    steps: list[ComposeStep],
    fail_fast: bool = True,
) -> ComposeResult:
    """Preview a chain of refactor steps. Commit applies all atomically."""

class ComposeStep(BaseModel):
    tool: str                          # e.g. "scalpel_split_file"
    args: dict                         # the tool's args, minus dry_run/preview_token

class ComposeResult(BaseModel):
    transaction_id: str                # use to commit or abort
    per_step: list[StepPreview]        # changes + diagnostics_delta per step
    aggregated_changes: list[FileChange]   # post-all-steps file shape
    aggregated_diagnostics_delta: DiagnosticsDelta   # final state
    expires_at: float                  # 5 min default
    warnings: list[str]
```

Commit:

```python
def scalpel_apply_capability(
    capability_id="scalpel.transaction.commit",
    params={"transaction_id": "txn_..."},
) -> RefactorResult:
    ...
```

Or, equivalently, by calling each step's tool with `dry_run=false` and a step-level `preview_token` carved out of the transaction. The transaction model is the LLM-facing primary; step-level tokens are an implementation escape hatch.

### 8.3 What "atomic" means in compose

- **Virtual application.** Each step is applied to an in-memory shadow workspace, not the on-disk files.
- **Per-step diagnostics.** Each step's `StepPreview` includes its diagnostics_delta computed against the shadow state of the *previous* step. The LLM sees how errors evolve across the chain.
- **Fail-fast.** Default behavior: first failing step ends the compose with `TRANSACTION_ABORTED`. `fail_fast=false` continues and reports every step's outcome (read-only; commit is still all-or-nothing).
- **Commit.** All steps' edits are applied in order, with intermediate checkpoints captured per step. Each step's checkpoint is bundled under one `transaction_id` so `scalpel_transaction_rollback` can undo the whole chain in reverse order.
- **Invalidation.** Any external file change in the affected set invalidates the transaction → `PREVIEW_EXPIRED`.

### 8.4 Why composable preview matters under full coverage

Without it, the LLM either:

1. Commits step 1 to learn step 2's preview, hoping nothing breaks — fragile, regression-prone (violates the global "frustrations: regression" directive); or
2. Manually simulates each step in its head — error-prone past 2 steps.

With it, the LLM gets one preview of the *final intended state*, makes a binary commit/abort call, and gets one rollback handle for the whole sequence.

### 8.5 Stacking limit

Composes can themselves nest in v1.1; for MVP, **no nested composes** (`steps[]` items must be regular tool calls, not `scalpel_dry_run_compose` calls). Bounds complexity; matches user observed patterns.

### 8.6 Token cost and TTL

A 5-step compose response can be ~10K tokens (5 × per-step preview ≈ 2K each). The TTL is short (5 min) precisely because longer holds risk file drift. If the LLM needs to think for >5 min between preview and commit, it should re-compose (idempotent on unchanged files).

---

## 9. Cross-language consistency

Full coverage exposes Rust-only capabilities (lifetimes, trait impl, macro expansion) and Python-only ones (async-ify, dataclass conversion, type-annotate). The surface must be honest about what works where without lying.

### 9.1 The shared / language-specific split

| Tier | Examples | Naming |
|---|---|---|
| **Universal facades** (always-on) | split_file, extract, inline, rename, imports_organize | `scalpel_<verb>` — language inferred from file extension |
| **Universal primitives** (always-on) | apply_capability, capabilities_list, capability_describe, dry_run_compose, rollback, workspace_health | `scalpel_<verb>` |
| **Language-specialty facades** (deferred) | rust_lifetime_elide, py_async_ify | `scalpel_<lang>_<verb>` |
| **Capabilities** (catalog rows, no tool) | rust.refactor.extract.struct_from_variant, python.refactor.dataclass_from_dict | `<lang>.<lsp_kind>` |

### 9.2 Detection contract

- Universal facades infer the language from `file`'s extension via `LanguageStrategy.file_extensions`.
- Language-specialty facades have the language baked in by name; calling `scalpel_rust_lifetime_elide` against a `.py` file → `CAPABILITY_NOT_AVAILABLE`.
- For workspace-spanning calls (`scalpel_imports_organize(files=["**"])`), scalpel resolves per-file languages and applies the corresponding strategy per file. If the assist's semantics differ across the matched languages → `MULTIPLEX_AMBIGUOUS`.

### 9.3 The `language` parameter

Universal facades accept an optional `language: Literal["rust","python"] | None = None`. When `None`, language is inferred. When set, scalpel asserts the file matches; mismatch → `CAPABILITY_NOT_AVAILABLE` ("language=python passed for foo.rs"). LLMs should leave it `None` unless multiplexing.

### 9.4 The shared/specific principle

**Tools are universal where the *intent* is universal.** Splitting a file is universal. Extracting a function is universal. Inlining is universal. Renaming is universal. Organizing imports is universal.

**Tools are language-specific where the *intent* is language-specific.** Lifetimes are Rust-only. Async-ify is Python-only. There is no "universal lifetime tool" because lifetimes don't exist in Python; pretending otherwise leaks Rust semantics. Likewise no universal async-ify.

**Capabilities (catalog rows) are always language-tagged** (`rust.…` / `python.…`) because they're 1:1 with LSP kinds.

---

## 10. Dynamic-registration prototype

`.lsp.json`-conditional tool advertising.

### 10.1 Discovery flow

At MCP server startup, scalpel walks `~/.claude/plugins/cache/**/.lsp.json` (per the main design's Deployment section), enumerates configured LSPs, and computes:

- **Reachable LSPs:** those whose binary resolves and answers `initialize`.
- **Strategy match:** each reachable LSP looked up in scalpel's `LanguageStrategy` registry.
- **Activated capabilities:** each strategy's exposed capability set.

### 10.2 Tool advertisement table

| Tool | Always-on? | Activates when |
|---|:---:|---|
| `scalpel_split_file` | yes | always |
| `scalpel_extract` | yes | always |
| `scalpel_inline` | yes | always |
| `scalpel_rename` | yes | always |
| `scalpel_imports_organize` | yes | always |
| `scalpel_apply_capability` | yes | always |
| `scalpel_capabilities_list` | yes | always |
| `scalpel_capability_describe` | yes | always |
| `scalpel_dry_run_compose` | yes | always |
| `scalpel_rollback` | yes | always |
| `scalpel_transaction_rollback` | yes | always |
| `scalpel_workspace_health` | yes | always |
| `scalpel_rust_lifetime_elide` | deferred | rust-analyzer reachable AND `RustStrategy` registered |
| `scalpel_rust_impl_trait` | deferred | rust-analyzer reachable AND `RustStrategy` registered |
| `scalpel_rust_match_to_iflet` | deferred | same |
| `scalpel_rust_qualify_path` | deferred | same |
| `scalpel_rust_promote_inline_module` | deferred | same |
| `scalpel_rust_extract_struct_from_variant` | deferred | same |
| `scalpel_py_async_ify` | deferred | pyright/pyrefly reachable AND `PythonStrategy` registered |
| `scalpel_py_type_annotate` | deferred | same |
| `scalpel_py_dataclass_from_dict` | deferred | same |
| `scalpel_py_promote_method_to_function` | deferred | same |
| `scalpel_execute_command` | deferred | always (when at least one strategy whitelists commands) |

### 10.3 Tool name × applicability matrix

| Tool | always-on | rust-only | python-only | both | LSP source |
|---|:---:|:---:|:---:|:---:|---|
| scalpel_split_file | ✓ | | | ✓ | rust-analyzer / pyright |
| scalpel_extract | ✓ | | | ✓ | rust-analyzer / pyright |
| scalpel_inline | ✓ | | | ✓ | rust-analyzer / pyright |
| scalpel_rename | ✓ | | | ✓ | rust-analyzer / pyright |
| scalpel_imports_organize | ✓ | | | ✓ | rust-analyzer / ruff |
| scalpel_apply_capability | ✓ | | | ✓ | any |
| scalpel_capabilities_list | ✓ | | | ✓ | n/a (catalog) |
| scalpel_capability_describe | ✓ | | | ✓ | n/a (catalog) |
| scalpel_dry_run_compose | ✓ | | | ✓ | n/a (composer) |
| scalpel_rollback | ✓ | | | ✓ | n/a |
| scalpel_transaction_rollback | ✓ | | | ✓ | n/a |
| scalpel_workspace_health | ✓ | | | ✓ | all |
| scalpel_rust_lifetime_elide | (deferred) | ✓ | | | rust-analyzer |
| scalpel_rust_impl_trait | (deferred) | ✓ | | | rust-analyzer |
| scalpel_rust_match_to_iflet | (deferred) | ✓ | | | rust-analyzer |
| scalpel_rust_qualify_path | (deferred) | ✓ | | | rust-analyzer |
| scalpel_rust_promote_inline_module | (deferred) | ✓ | | | rust-analyzer |
| scalpel_rust_extract_struct_from_variant | (deferred) | ✓ | | | rust-analyzer |
| scalpel_py_async_ify | (deferred) | | ✓ | | pyright/pyrefly |
| scalpel_py_type_annotate | (deferred) | | ✓ | | pyright |
| scalpel_py_dataclass_from_dict | (deferred) | | ✓ | | pyrefly/refurb |
| scalpel_py_promote_method_to_function | (deferred) | | ✓ | | pyright |
| scalpel_execute_command | (deferred) | | | ✓ | per-strategy whitelist |

### 10.4 Implementation sketch

```python
# scalpel/server.py (Python-side MCP)
def list_tools(...):
    base = ALWAYS_ON_TOOLS.copy()
    for lang, strategy in registry.activated_strategies():
        for tool in strategy.deferred_tools():
            base.append({**tool, "defer_loading": True})
    return base
```

`defer_loading: true` is the Anthropic Tool Search hook. Deferred tools are visible to Tool Search but not loaded into context until search resolves them.

### 10.5 Why dynamic registration is *necessary*, not just nice

Static-registration of all 23 tools always-on (or all 50+ as the surface grows) bumps cold context past 25K easily. The Anthropic data on Opus 4.5 (49% → 88% accuracy improvement with Tool Search) is the dominant signal.

### 10.6 Guard against over-deferral

Risk: if the LLM doesn't know a deferred tool exists, it never searches for it. Mitigation: `scalpel_capabilities_list` is always-on and surfaces deferred-tool capability ids with their `preferred_facade` set to the deferred tool name. The LLM that calls `capabilities_list` first thing (the recommended pattern in the SKILL.md) will see them.

---

## 11. Rollback under richer surface

A multi-step transaction (extract-module → organize-imports → rename across 5 files) needs a rollback handle that mirrors its structure.

### 11.1 The two rollback tools

**`scalpel_rollback(checkpoint_id)`** — single-checkpoint undo. Same as v1. Used after a single tool call. Idempotent.

**`scalpel_transaction_rollback(transaction_id)`** — multi-checkpoint undo. New for v2. Used after a `scalpel_dry_run_compose` commit. Replays each checkpoint's inverse edit in **reverse order** of step application. Idempotent.

### 11.2 The data model

```python
class Transaction(BaseModel):
    transaction_id: str
    checkpoint_ids: list[str]      # in step order
    committed_at: float
    rolled_back: bool = False

class Checkpoint(BaseModel):
    checkpoint_id: str
    transaction_id: str | None     # null for non-transactional commits
    inverse_edit: WorkspaceEdit
    file_snapshots: dict[str, str] # path -> content_hash
    captured_at: float
```

Each transactional commit captures one checkpoint per step. The transaction record carries the ordered list. Rollback: walk `checkpoint_ids` in reverse, apply each inverse edit, mark transaction `rolled_back=True`.

### 11.3 Failure during transaction rollback

If step N+1's inverse fails, transactional rollback **stops** and returns:

```json
{
  "applied": false,
  "restored_files": ["..."],
  "failure": {
    "stage": "step_3_inverse",
    "step_index": 3,
    "reason": "IO error",
    "recoverable": false
  },
  "transaction_id": "txn_abc",
  "remaining_checkpoint_ids": ["ckpt_2","ckpt_1"]
}
```

The LLM can manually call `scalpel_rollback` on each remaining checkpoint (from the response), but more importantly: scalpel **never silently leaves a partially-rolled-back transaction**. The LLM gets a structured failure with the residual handle. Manual git is the ultimate fallback.

### 11.4 Observability for transactions

Each step's `RefactorResult` already carries a `checkpoint_id`. The `TransactionResult` adds:

```python
class TransactionResult(BaseModel):
    transaction_id: str
    per_step: list[RefactorResult]
    aggregated_diagnostics_delta: DiagnosticsDelta
    duration_ms: int
    rules_fired: list[str]         # cross-step
```

The LLM uses `aggregated_diagnostics_delta` as the headline (final state), `per_step[i].diagnostics_delta` to debug which step introduced what, and `transaction_id` for rollback.

### 11.5 Lifetime and eviction

- Single checkpoints: LRU 50 entries (per v1).
- Transactions: LRU 20 entries; evicting a transaction also evicts its checkpoints.
- Eviction signal: `CHECKPOINT_EVICTED` (still v1.1 deferred; for v2 MVP, reuse `NOT_APPLICABLE` with `message: "checkpoint evicted; use git"`).

### 11.6 Cross-tool rollback (compose with mixed tools)

If the transaction's step list includes `scalpel_apply_capability` calls (long-tail), each call's checkpoint is treated identically to a facade-level checkpoint. Mixed-tool transactions are first-class.

---

## 12. Telemetry for iteration

Post-MVP, we need data on which of the 23 exposed tools actually get used so we can prune cold ones, promote hot ones from deferred to always-on, and refine docstrings.

### 12.1 The trace event

Per call, scalpel logs (to `.serena/telemetry/calls.jsonl` by default; redact-by-default; user-disable-able):

```json
{
  "ts": 1730000000.123,
  "session_id": "uuid",
  "tool_name": "scalpel_split_file",
  "language": "rust",
  "capability_id": null,
  "args_summary": {"file_kind": "rs", "groups_count": 4, "dry_run": true},
  "disposition": "ok",
  "error_code": null,
  "duration_ms": 1843,
  "checkpoint_id": "ckpt_7a3f",
  "transaction_id": null,
  "preview_token_used": false,
  "indexing_ready": true,
  "rules_fired": ["preview_token_valid"],
  "lsp_ops_total_ms": 1402,
  "tool_search_expanded": []
}
```

For `scalpel_apply_capability`, `capability_id` is the catalog id. For `scalpel_dry_run_compose`, the trace records `step_count` and `transaction_id`.

### 12.2 The fields and their use

| Field | Use for |
|---|---|
| `tool_name` | Tool-popularity histogram → promote/demote candidates |
| `capability_id` | Catalog-popularity histogram → promote to facade |
| `language` | Language mix; cross-language refactors |
| `disposition` (ok/err/no_op) | Success rate per tool |
| `error_code` | Error-pattern frequency → docstring hints |
| `duration_ms`, `lsp_ops_total_ms` | Perf regression detection |
| `dry_run` (in `args_summary`) | Preview-vs-commit ratio per tool — measures LLM's confidence |
| `rules_fired` | Internal-decision frequency → bug detection |
| `tool_search_expanded` | Which deferred tools were retrieved → confirms `defer_loading` is working |

### 12.3 Privacy posture

- **No file contents.** Only file extensions and structural counts.
- **No symbol names.** Hashed if needed.
- **Local-only by default.** `O2_SCALPEL_TELEMETRY=1` opts into anonymous upload; `=0` (default) keeps it local.
- **Never logs API keys, paths to home directories, or workspace names.**

### 12.4 Aggregation pipeline (post-MVP)

Out-of-scope for the MVP server, but the JSONL format is chosen so a simple `jq` + `duckdb` pipeline can produce:

- Top-N tools by call count (per language, per disposition).
- Capability promotion candidates: catalog rows with > N calls/week and high success rate but no preferred_facade.
- Cold tools: facades with < N calls/week — candidates for demotion to deferred.
- Error hotspots: error codes with above-baseline frequency on a specific tool.

### 12.5 What this enables

The MVP ships with educated guesses about which tools are always-on vs. deferred. Telemetry lets us confirm or correct those guesses with data. This is exactly the post-MVP iteration cycle the orchestrator's brief asks us to enable.

---

## 13. The plan→preview→commit→verify loop, generalized

The narrow v1 had a single workflow. v2 has a parametric one.

### 13.1 The generalized workflow

```
1. (optional) scalpel_workspace_health   ── confirm LSPs warm
2. (optional) scalpel_capabilities_list  ── if intent is non-trivial
3. Pick the right facade or apply_capability
4. Call with dry_run=true (single) or scalpel_dry_run_compose (chain)
5. Inspect changes + diagnostics_delta
6. Commit (dry_run=false + preview_token, or transaction commit)
7. (optional) external verify (cargo check / pytest)
8. On failure: scalpel_rollback or scalpel_transaction_rollback
```

### 13.2 Worked example: full split + tidy + rename across Rust + Python (mixed repo)

A repo with `crates/foo/src/lib.rs` (Rust) and `services/api.py` (Python). User asks: "factor `api.py`'s endpoint handlers into `services/api/handlers/`, and rename `lib.rs::Engine` to `Core` everywhere."

```
turn 1: scalpel_workspace_health()
        → {rust: ready, python: ready}

turn 2: scalpel_dry_run_compose([
          {tool: "scalpel_split_file",
           args: {file: "services/api.py",
                  groups: {"handlers": ["users","orders","admin"]}}},
          {tool: "scalpel_imports_organize",
           args: {files: ["services/api/**"]}},
          {tool: "scalpel_rename",
           args: {file: "crates/foo/src/lib.rs",
                  name_path: "Engine", new_name: "Core"}},
          {tool: "scalpel_imports_organize",
           args: {files: ["crates/foo/src/**"]}}
        ])
        → {transaction_id: "txn_x",
           per_step: [...],
           aggregated_diagnostics_delta: {before: 0, after: 0}}

turn 3: scalpel_apply_capability(
          capability_id="scalpel.transaction.commit",
          params={transaction_id: "txn_x"})
        → {applied: true, transaction_id: "txn_x", checkpoint_ids: [...]}

turn 4: external verify: cargo check && pytest
        → fails (test imports old "Engine")
        → fix the test or:

turn 5: scalpel_transaction_rollback(transaction_id="txn_x")
        → {applied: true, restored_files: [...]}
```

5 tool calls (3 scalpel + 2 external) for a cross-language, 4-step refactor. Within the always-on 12. No `defer_loading` expansion needed.

### 13.3 The same scenario without compose (legacy workflow)

Without `dry_run_compose`, this is 4 separate dry-runs and 4 commits = 8 turns + verify + 4 manual rollbacks if anything goes wrong = ~14 turns. Compose is a 3× turn-count savings.

---

## 14. Test coverage implications

Brief check against the main design's testing strategy.

### 14.1 Unit

- `scalpel_dry_run_compose` rejects nested compose (§8.5).
- `apply_capability` with unregistered id → `CAPABILITY_NOT_AVAILABLE` + candidates.
- `apply_capability` with valid id but wrong language → `CAPABILITY_NOT_AVAILABLE`.
- `scalpel_transaction_rollback` reverse-order replay; idempotent on second call.
- Each error code's hint string lints under the 30-word docstring rule (each `hint` ≤ 20 words).
- `defer_loading: true` advertisement only fires when the corresponding strategy is registered.

### 14.2 Integration

- Composed dry-run of split → organize → rename across the 5-file Rust fixture.
- Same shape across the Python fixture.
- Cross-language compose (`MULTIPLEX_AMBIGUOUS` path).
- Tool Search end-to-end: deferred tool gets retrieved and applied successfully.
- `capabilities_list` returns ≥80 rust capabilities, ≥50 python capabilities.

### 14.3 E2E

- §13.2 worked example end-to-end on a fixture mixed-language repo.
- Auto-rollback on diagnostics regression in compose middle step.
- Compose where step 3 fails → `TRANSACTION_ABORTED` with `failed_step_index=2`, no on-disk changes.
- Telemetry JSONL correctness: every call appears, redaction works.

### 14.4 What's outside MVP testing

- Performance under 30+ deferred tools (architectural cap not yet hit).
- Multi-session checkpoint persistence across MCP restart.
- Cross-workspace transactions.

---

## 15. Open questions for follow-up

1. **`apply_capability` discoverability.** Will LLMs reliably *call* `capabilities_list` first, or will they default to facades and miss the long tail? MVP telemetry will answer. Mitigation if no: add a SKILL.md "always start by calling capabilities_list" prompt; consider a once-per-session auto-injection.
2. **Per-language LSP fan-out.** Pyright vs. pyrefly vs. ruff — which is canonical for a given Python capability? `LanguageStrategy.python_strategy` decides; `capabilities_list` reports `lsp_source` per row to keep the LLM honest.
3. **Tool Search ranking.** Anthropic's BM25 ranker may not rank our `scalpel_rust_lifetime_elide` highly for "elide lifetime" queries. We may need to tune the tool's docstring and `keywords` field. Out-of-scope for MVP design; in-scope for post-MVP tuning.
4. **Transaction commit verb.** `scalpel_apply_capability(capability_id="scalpel.transaction.commit", ...)` is awkward. Alternatives: a 13th always-on tool `scalpel_transaction_commit`. Cost: one more tool definition. Decision deferred — measure how often LLMs use compose first.
5. **Should `scalpel_dry_run_compose` accept already-existing preview_tokens?** I.e., compose previously-previewed steps. Cleaner UX, but invalidation logic gets gnarly. Defer to v1.1.
6. **Cross-strategy capability ids.** Some intents (organize-imports) are cross-language. Catalog id options: shared (`refactor.imports.organize`) vs. per-language (`rust.refactor.imports.organize` + `python.refactor.imports.organize`). v2: per-language ids for honesty; the always-on facade abstracts over both.

---

## 16. Summary

Going to "full LSP coverage" without a tool surface explosion required two architectural moves: (1) a hybrid pattern where 12 named always-on tools cover the happy path and a generic `apply_capability` + catalog covers the long tail, and (2) Anthropic's `defer_loading` so per-language specialty facades exist but don't burn cold context. Naming cluster prefixes (`scalpel_<area>_<verb>`) help the LLM route. Docstrings are capped at 30 words; depth lives in the catalog. Errors expand from 6 to 10 codes for the new failure shapes (capability availability, multiplex ambiguity, transaction abort, server reachability). Composable dry-run + transactional rollback let the LLM preview and undo multi-step refactors atomically. Telemetry from day one tells us which tools to promote, demote, or rename in v1.1.

This is what full coverage looks like when it's still LLM-usable.

---

## Appendix A — Canonical MVP tool surface (consolidated table)

| name | language | docstring (≤30 words) | priority | architecture-option |
|---|---|---|:---:|:---:|
| `scalpel_split_file` | both | Split a source file into N modules by moving named symbols. Returns diff + diagnostics_delta + preview_token. Atomic. | P0 | E |
| `scalpel_extract` | both | Extract a symbol or selection into a new variable, function, module, or type. Pick `target` to choose. Atomic. | P0 | E (with B inside) |
| `scalpel_inline` | both | Inline a function, variable, or type alias at its definition or all call-sites. Pick `target`. Atomic. | P0 | E (with B inside) |
| `scalpel_rename` | both | Rename a symbol everywhere it is referenced. Cross-file. Returns checkpoint_id. Hallucination-resistant on name-paths. | P0 | E |
| `scalpel_imports_organize` | both | Add missing, remove unused, reorder imports across files. Idempotent; safe to re-call. | P0 | E |
| `scalpel_apply_capability` | both | Apply any registered capability by capability_id from capabilities_list. The long-tail dispatcher. Atomic. | P0 | A inside E |
| `scalpel_capabilities_list` | both | List capabilities for a language with optional filter. Returns capability_id + title + applies_to_kinds. | P0 | catalog |
| `scalpel_capability_describe` | both | Return full schema, examples, and pre-conditions for one capability_id. Call before invoking unknown capabilities. | P0 | catalog |
| `scalpel_dry_run_compose` | both | Preview a chain of refactor steps without committing any. Returns transaction_id; commit applies all atomically. | P0 | composer |
| `scalpel_rollback` | both | Undo a refactor by checkpoint_id. Idempotent: second call is no-op. | P0 | primitive |
| `scalpel_transaction_rollback` | both | Undo all checkpoints in a transaction (from dry_run_compose) in reverse order. Idempotent. | P0 | primitive |
| `scalpel_workspace_health` | both | Probe LSP servers: indexing state, registered capabilities, version. Call before refactor sessions. | P0 | diagnostics |
| `scalpel_rust_lifetime_elide` | rust | Apply rust-analyzer's lifetime elision/explicit assists to a function signature. Atomic. | P1 | D (deferred) |
| `scalpel_rust_impl_trait` | rust | Generate a missing impl Trait for a type via rust-analyzer's add-missing-impl-members assist. | P1 | D |
| `scalpel_rust_match_to_iflet` | rust | Convert match ↔ if let chains. rust-analyzer rewrite kind. | P2 | D |
| `scalpel_rust_qualify_path` | rust | Qualify or unqualify a path. Useful before/after import organization. | P2 | D |
| `scalpel_rust_promote_inline_module` | rust | Promote `mod foo {…}` to `foo.rs`. Rust-only equivalent of split. | P1 | D |
| `scalpel_rust_extract_struct_from_variant` | rust | Pull data of an enum variant out into a named struct. | P2 | D |
| `scalpel_py_async_ify` | python | Convert a sync function and its propagated callsites to async. Pyright/refurb-driven. | P1 | D |
| `scalpel_py_type_annotate` | python | Add or refine type hints on a function/class via pyright inference. Idempotent. | P1 | D |
| `scalpel_py_dataclass_from_dict` | python | Convert a dict-shaped class or factory into a `@dataclass`. | P2 | D |
| `scalpel_py_promote_method_to_function` | python | Promote a method to a module-level function (Pyright/Pyrefly assist). | P2 | D |
| `scalpel_execute_command` | both | Server-specific JSON-RPC pass-through, whitelisted per LanguageStrategy. Power-user escape hatch. | P2 | D |

12 always-on, 11 deferred = 23 total. Within the **Recommended (mitigated)** band of §1.2.

---

## Appendix B — Error-code quick-reference

| code | retryable | repair pattern |
|---|---|---|
| `STALE_VERSION` | yes (×2) | re-issue call |
| `NOT_APPLICABLE` | yes (×1) | adjust range/cursor; retry |
| `INDEXING` | yes (after wait) | wait estimated_wait_ms or call workspace_health |
| `APPLY_FAILED` | conditional | inspect failed_stage; adjust params |
| `PREVIEW_EXPIRED` | yes (×2) | re-run dry_run |
| `SYMBOL_NOT_FOUND` | yes (×2) | pick from candidates[] |
| `CAPABILITY_NOT_AVAILABLE` | yes (×1) | re-call capabilities_list |
| `SERVER_REQUIRED` | conditional | escalate; show install_hint |
| `MULTIPLEX_AMBIGUOUS` | yes (×1) | pass language= or narrow files |
| `TRANSACTION_ABORTED` | yes (×1) | inspect failed_step_index; recompose |

Cumulative same-turn retry budget: ≤3.

---

## Appendix C — Capabilities-catalog row schema

```python
class CapabilityDescriptor(BaseModel):
    capability_id: str             # "rust.refactor.extract.module"
    title: str                     # "Extract symbols into module"
    applies_to_kinds: list[str]    # ["function","struct","enum","impl","trait"]
    lsp_kind: str                  # "refactor.extract.module"
    lsp_source: str                # "rust-analyzer"
    preferred_facade: str | None   # "scalpel_split_file" or null

class CapabilityFullDescriptor(CapabilityDescriptor):
    description: str
    params_schema: dict
    requires: list[str]            # ["selection","name_path","cursor"]
    side_effects: list[str]
    example_invocation: dict
    failure_modes: list[str]
```

---

## Appendix D — Telemetry trace event schema

```python
class TraceEvent(BaseModel):
    ts: float
    session_id: str
    tool_name: str
    language: str | None
    capability_id: str | None
    args_summary: dict
    disposition: Literal["ok","err","no_op"]
    error_code: str | None
    duration_ms: int
    checkpoint_id: str | None
    transaction_id: str | None
    preview_token_used: bool
    indexing_ready: bool
    rules_fired: list[str]
    lsp_ops_total_ms: int
    tool_search_expanded: list[str]
```

JSONL on disk; `O2_SCALPEL_TELEMETRY=0` (default) = local-only.

---

## Appendix E — Sources

- Anthropic — Tool Search Tool docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- Anthropic — Code execution with MCP: https://www.anthropic.com/engineering/code-execution-with-mcp
- Anthropic — Advanced tool use: https://www.anthropic.com/engineering/advanced-tool-use
- Speakeasy — Progressive discovery vs. semantic search: https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets
- Jentic — The MCP Tool Trap: https://jentic.com/blog/the-mcp-tool-trap
- Jenova.ai — AI Tool Overload: https://www.jenova.ai/en/resources/mcp-tool-scalability-problem
- Lunar.dev — Preventing MCP Tool Overload: https://www.lunar.dev/post/why-is-there-mcp-tool-overload-and-how-to-solve-it-for-your-ai-agents
- atcyrus — MCP Tool Search guide: https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide
- Unified.to — Scaling MCP Tools with Defer Loading: https://unified.to/blog/scaling_mcp_tools_with_anthropic_defer_loading
- arxiv — MCPVerse benchmark: https://arxiv.org/html/2508.16260v2
- arxiv — MCP-Zero active tool discovery: https://arxiv.org/pdf/2506.01056

---

**End of report.**
