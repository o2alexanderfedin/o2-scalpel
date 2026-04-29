# Pragmatic Surveyor — Empirical Coverage Data

**Stance**: ground the debate in numbers.
**Date**: 2026-04-29

---

## TL;DR (3 bullets)

- The catalog has 72 records across 11 languages, but **0 of 72 have `preferred_facade != null`** — the facade-to-catalog linkage field exists in schema but is unpopulated, so the catalog does not yet drive routing.
- Rust (6 kinds) and Python (7 kinds) are the only two languages with named scalpel facades; all 9 remaining languages (Go, TypeScript, Java, C++, C#, Lean, SMT2, Prolog, ProbLog — 59 catalog records) route exclusively through `scalpel_apply_capability`.
- The 33 facade tools cover rust/python well by intent, but 18 of them mention only "rust/python" in their docstrings — they are opaque to the LLM for Go/TS/Java/C++ users.

---

## 1. Per-language coverage table

Data sources: `test/spikes/data/capability_catalog_baseline.json` (72 records) and facade class list from `src/serena/tools/scalpel_facades.py` (33 tool classes + 11 primitive tools).

**Facade mapping logic**: A "wrapped facade" is a named `scalpel_*` tool whose docstring explicitly targets that language. "Long-tail-only" means all kinds funnel to `scalpel_apply_capability`. "Test-exercised" counts distinct `scalpel_*` names appearing in `test/e2e/`.

| Language | Primary LSP | Kinds in catalog | Named facades | Long-tail-only kinds | E2E-exercised facades |
|---|---|---|---|---|---|
| rust | rust-analyzer | 6 | ~18 (Rust-specific tools) | 0 | 11 |
| python | pylsp-rope + basedpyright + ruff | 7 | ~15 (Python-specific tools) | 0 | 6 |
| markdown | marksman | 0* | 4 | 0 | 4 |
| typescript | vtsls | 13 | 0 | 13 | 0 |
| go | gopls | 9 | 0 | 9 | 0 |
| java | jdtls | 16 | 0 | 16 | 0 |
| cpp | clangd | 7 | 0 | 7 | 0 |
| csharp | csharp-ls | 9 | 0 | 9 | 0 |
| lean | lean-server | 1 | 0 | 1 | 0 |
| smt2 | dolmenls | 1 | 0 | 1 | 0 |
| prolog | swipl-lsp | 2 | 0 | 2 | 0 |
| problog | problog-lsp | 1 | 0 | 1 | 0 |

*Markdown has no `code_action_allow_list` entries in the baseline (marksman does not advertise codeAction kinds); its 4 facades operate via LSP rename + workspace edits, not code-action dispatch.

**Summary arithmetic**: 72 catalog records total. 59 (82%) have zero named facades. Rust+Python account for 13 catalog records with rich facade coverage. The `preferred_facade` field is `null` for all 72 rows — the schema supports facade attribution but the wiring has not been done.

---

## 2. Tool-routing surface analysis

### Docstring length distribution (facade `apply` methods)

| Bucket | Count | Tools |
|---|---|---|
| < 300 chars | 1 | `ScalpelTransactionCommitTool` (244) |
| 300–450 | 14 | `ScalpelOrganizeLinks`, `ScalpelSplitDoc`, `ScalpelLocalToField`, `ScalpelAnnotateReturn`… |
| 450–600 | 13 | `ScalpelVerifyAfterRefactor`, `ScalpelExpandMacro`, `ScalpelTidyStructure`… |
| 600–850 | 5 | `ScalpelRename`, `ScalpelExtractLifetime`, `ScalpelImportsOrganize`, `ScalpelInline`, `ScalpelExtract` |

The long-tail dispatcher `ScalpelApplyCapabilityTool` has **611 chars** — longer than 29 of the 33 named facades. This is a routing-surface problem: the generic tool is comparably described to the specific ones, which reduces the signal-to-noise ratio for LLM selection.

### Language mention in docstrings

- 25 of 33 facades mention "rust" explicitly.
- 28 of 33 mention "python" explicitly.
- 4 of 33 mention "markdown."
- 0 facades mention "go," "java," "typescript," "cpp," or "csharp" by name.

The routing surface for the 9 Wave-3 languages is entirely concentrated in `scalpel_apply_capability` plus the two discovery tools (`scalpel_capabilities_list`, `scalpel_capability_describe`). An LLM receiving a Go or Java refactor request must self-navigate through the generic stack with no named intent signal.

### Primitive tool docstring lengths (for comparison)

`ScalpelApplyCapabilityTool`: 611 chars. `ScalpelDryRunComposeTool`: 602. `ScalpelCapabilitiesListTool`: 468. These are in the same length range as the mid-tier named facades, confirming no systematic length gap between "specific" and "generic" tools.

---

## 3. Upstream Serena's symbol-edit tools

`src/serena/tools/symbol_tools.py` exposes five write-side tools inherited from the Serena upstream:

| Serena tool | MCP name | Scalpel facade overlap |
|---|---|---|
| `RenameSymbolTool` | `rename_symbol` | **overlaps** `scalpel_rename` |
| `ReplaceSymbolBodyTool` | `replace_symbol_body` | no scalpel equivalent |
| `InsertAfterSymbolTool` | `insert_after_symbol` | no scalpel equivalent |
| `InsertBeforeSymbolTool` | `insert_before_symbol` | no scalpel equivalent |
| `SafeDeleteSymbol` | `safe_delete_symbol` | no scalpel equivalent |

These coexist alongside scalpel tools — they are all registered in the same MCP surface. The docstring analysis confirms the overlap: `RenameSymbolTool` (511 chars) vs `ScalpelRenameTool` (602 chars) — both present, both reasonably described, **no disambiguation guidance** between them.

The 4 non-overlapping Serena symbol tools (`replace_symbol_body`, `insert_after/before_symbol`, `safe_delete_symbol`) are **not replicated** as scalpel facades. They operate at the AST/symbol level rather than LSP code-action dispatch, so they are complementary rather than duplicated — but an LLM working on, say, a Go file must decide between `scalpel_apply_capability` (LSP code action) and `replace_symbol_body` (Serena AST edit) with no guidance on which is correct for which operation.

---

## 4. Top 3 measured gaps (data-driven)

### Gap 1: Wave-3 languages (59 catalog records, 0 facades) — largest numerical gap

TypeScript (13), Java (16), Go (9), C++ (7), C# (9) each have a non-trivial catalog surface with zero named facades. Java is the single largest: 16 kinds including `source.generate.constructor`, `source.generate.hashCodeEquals`, `source.generate.toString`, `source.generate.accessors`, `source.generate.overrideMethods`, `source.generate.delegateMethods` — high-value, highly-differentiated actions that `scalpel_apply_capability` absorbs opaquely. TypeScript's 13 kinds include `refactor.extract.constant`, `refactor.extract.type`, `refactor.move`, `refactor.rewrite`, `refactor.inline.variable` — semantically distinct operations collapsed into one dispatcher.

### Gap 2: `preferred_facade` field is schema-present but entirely null (72/72 records)

Every catalog record has `"preferred_facade": null`. The machinery to connect capability IDs to facade names exists but has never been exercised. This means `scalpel_capabilities_list` cannot tell an LLM "for this kind, call scalpel_extract" — it can only list kind IDs. The gap between the catalog's routing-hint slot and its actual population is 100%.

### Gap 3: `rename_symbol` vs `scalpel_rename` disambiguation is absent

Both tools are live, both target cross-file rename, both are similarly documented. There is no runtime guard, MCP priority flag, or docstring contrast directing the LLM to prefer one over the other. This is a latent routing-collision rather than a coverage gap, but it degrades precision: for a Rust rename the LLM may invoke `rename_symbol` (Serena AST path, no LSP checkpoint) or `scalpel_rename` (LSP textDocument/rename + checkpoint). Result correctness differs.

---

## 5. Synthesis input for the drafter

**Data verdict: the auditor (agent B) is numerically correct on the Wave-3 facade gap; the defender (agent A) is correct on the mechanism.** The catalog records 59 kinds across 9 languages with no named facade, confirming the expansion case is real, not theoretical. However, the more actionable finding is not "add 59 facades" — it is that the catalog's own `preferred_facade` field is the intended bridge and it has never been populated for *any* language. A targeted third path: (1) populate `preferred_facade` for the 13 Rust + 7 Python kinds that already have facades, making the catalog actively drive routing; (2) add 2–3 Java facades (constructor generation, extract method, organize imports) where the kinds are high-value and semantically unambiguous — this produces measurable LLM routing improvement without the combinatorial explosion the defender fears. Wholesale facade expansion for all 9 wave-3 languages at once is premature given the `preferred_facade` field has not been validated as a routing mechanism even for Rust/Python.

---

## Open questions

- What triggers `preferred_facade` population? The `build_capability_catalog` factory has a `preferred_facade=None` hardcode (line 319 of `capabilities.py`) with no mechanism to inject facade names. Is this intentional deferral or an omission?
- Is the `RenameSymbolTool` / `ScalpelRenameTool` coexistence intentional? Should one be hidden from the MCP surface when the other is present?
- Do Wave-3 languages (Go, Java, TS, C#, C++) have active playground fixtures? If not, any new facades cannot be E2E-verified, which makes expansion riskier than it appears.
- The Markdown strategy advertises 0 catalog kinds but 4 facades work. Is the catalog incomplete for Markdown, or does Markdown legitimately bypass the code-action mechanism entirely?

---

## Citations

- Catalog baseline: `vendor/serena/test/spikes/data/capability_catalog_baseline.json` (72 records, all `preferred_facade: null`)
- Catalog factory: `vendor/serena/src/serena/refactoring/capabilities.py` lines 255–323
- `preferred_facade` schema field: `capabilities.py` line 84; hardcoded `None` at line 319
- Facade tools: `vendor/serena/src/serena/tools/scalpel_facades.py` — 33 Tool subclasses
- Primitive tools: `vendor/serena/src/serena/tools/scalpel_primitives.py` — 11 Tool subclasses
- Serena symbol tools: `vendor/serena/src/serena/tools/symbol_tools.py` — 5 write-side tools
- Allow lists: `vendor/serena/src/serena/refactoring/language_strategy.py` (Python/Rust), `typescript_strategy.py`, `golang_strategy.py`, `java_strategy.py`, `cpp_strategy.py`
- E2E facade exercise list: `vendor/serena/test/e2e/` — 18 distinct `scalpel_*` names observed
