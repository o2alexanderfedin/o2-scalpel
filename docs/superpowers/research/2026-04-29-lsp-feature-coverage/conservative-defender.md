# Conservative Defender — Current Scalpel Surface Is Sufficient

**Stance**: more facades = more bloat. Defend the status quo.
**Date**: 2026-04-29

---

## TL;DR (3 bullets)

- The existing 33 `scalpel_*` facades cover every major LSP write/refactor category (split/move, rename, extract/inline, generate, organize, transform, safety/diagnostics, markdown) with no obvious gap in the high-frequency tier.
- `scalpel_apply_capability` + `scalpel_capabilities_list` form a self-describing long-tail escape hatch that handles arbitrary `textDocument/codeAction` kinds without a single line of new facade code.
- CLAUDE.md mandates YAGNI and KISS explicitly; adding facades speculatively contradicts the project's own governing principles and multiplies test-surface across 11 languages with each addition.

---

## 1. Current 33-facade surface (categorized)

Counting by class name in
`vendor/serena/src/serena/tools/scalpel_facades.py`:

**Split / move (file-level restructuring)**
- `ScalpelSplitFileTool` (line 183) — splits a file into N modules by symbol groups
- `ScalpelConvertModuleLayoutTool` (line 1155) — `file ↔ package` layout conversion

**Rename**
- `ScalpelRenameTool` (line 635) — LSP `textDocument/rename` with cross-file tracking

**Extract / inline**
- `ScalpelExtractTool` (line 367) — function/variable/module extraction
- `ScalpelInlineTool` (line 514) — inline variable or function call
- `ScalpelExtractLifetimeTool` (line 1504) — Rust lifetime extraction
- `ScalpelExtractSectionTool` (line 2781) — markdown section extraction

**Generate / scaffold**
- `ScalpelGenerateTraitImplScaffoldTool` (line 1595) — trait/interface impl stubs
- `ScalpelGenerateMemberTool` (line 1644) — generate getter/setter/constructor members
- `ScalpelGenerateFromUndefinedTool` (line 2051) — generate symbol from a use-site
- `ScalpelCompleteMatchArmsTool` (line 1463) — fill in exhaustive match arms

**Organize / imports**
- `ScalpelImportsOrganizeTool` (line 883) — sort + deduplicate imports
- `ScalpelExpandGlobImportsTool` (line 1549) — expand `use foo::*` into explicit names
- `ScalpelAutoImportSpecializedTool` (line 2093) — context-aware single-import insertion
- `ScalpelConvertFromRelativeImportsTool` (line 2484) — Python relative→absolute imports
- `ScalpelOrganizeLinksTool` (line 2853) — markdown reference-link normalization

**Type / signature transforms**
- `ScalpelChangeTypeShapeTool` (line 1360) — `T → Option<T>`, `T → Vec<T>`, etc.
- `ScalpelChangeReturnTypeTool` (line 1418) — return-type change with propagation
- `ScalpelChangeVisibilityTool` (line 1207) — pub/pub(crate)/private visibility flip
- `ScalpelAnnotateReturnTypeTool` (line 2367) — infer + insert return type annotation (Python)
- `ScalpelConvertToAsyncTool` (line 2288) — sync→async conversion (Python)
- `ScalpelIntroduceParameterTool` (line 2004) — promote local to function parameter
- `ScalpelLocalToFieldTool` (line 1924) — promote local to struct/class field
- `ScalpelConvertToMethodObjectTool` (line 1884) — function → method-object class
- `ScalpelUseFunctionTool` (line 1964) — replace inline code with existing function call

**Macro / code expansion**
- `ScalpelExpandMacroTool` (line 1692) — expand a Rust macro in-place
- `ScalpelTidyStructureTool` (line 1254) — structural cleanup (dead code, field order)

**Safety / diagnostics / session**
- `ScalpelVerifyAfterRefactorTool` (line 1756) — post-refactor LSP diagnostics diff
- `ScalpelFixLintsTool` (line 2139) — apply `source.fixAll` / ruff / clippy
- `ScalpelIgnoreDiagnosticTool` (line 2227) — insert `#[allow(...)]` / `# noqa` / `# type: ignore`
- `ScalpelTransactionCommitTool` (line 3007) — commit a dry-run preview

**Markdown structural**
- `ScalpelRenameHeadingTool` (line 2618) — rename a heading + update internal links
- `ScalpelSplitDocTool` (line 2718) — split a markdown doc at heading boundaries

All seven refactoring intent categories are occupied. There is no glaring empty shelf.

---

## 2. The long-tail safety valve

`ScalpelApplyCapabilityTool` (primitives.py, line 273) is the escape hatch for everything not covered by a bespoke facade. Its mechanism:

1. The LLM calls `scalpel_capabilities_list` (primitives.py, line 71) — optionally filtered by `filter_kind` (e.g. `"refactor.extract"`) — and receives a JSON array of `CapabilityDescriptor` rows, each carrying `capability_id`, `kind`, `source_server`, and `preferred_facade`.

2. If `preferred_facade` is `null`, the LLM calls `scalpel_apply_capability(capability_id=..., file=..., range_or_name_path=...)`. The dispatcher at primitives.py line 228 calls `coord.merge_code_actions(file, start, end, only=[capability.kind])` — exactly the same pipeline that bespoke facades use internally.

3. The catalog is dynamic: `DynamicCapabilityRegistry` (landed in the dynamic-lsp-capability milestone) merges static catalog records with per-session LSP `client/registerCapability` announcements. A capability that exists in rust-analyzer today but has no facade is still reachable via `apply_capability` immediately, without a code change.

This means the set of reachable refactoring operations is strictly a superset of the 33 facades. Facade absence does not mean capability absence — it just means the LLM uses two tool calls instead of one.

---

## 3. Read-only LSP features that do not need scalpel facades

o2-scalpel's mandate is **write/refactor operations** (CLAUDE.md: "exposes LSP write/refactor operations as MCP tools"). The following LSP methods are read-only by definition and are already covered by Claude Code's built-in LSP umbrella:

| LSP method | Read/write | Scalpel role |
|---|---|---|
| `textDocument/definition` | read | out of scope |
| `textDocument/references` | read | out of scope |
| `textDocument/hover` | read | out of scope |
| `textDocument/documentSymbol` | read | out of scope |
| `callHierarchy/incomingCalls` | read | out of scope |
| `callHierarchy/outgoingCalls` | read | out of scope |
| `typeHierarchy/supertypes` | read | out of scope |
| `typeHierarchy/subtypes` | read | out of scope |
| `textDocument/semanticTokens` | read | out of scope |
| `textDocument/inlayHint` | read | out of scope |

Proposals to add `scalpel_call_hierarchy` or `scalpel_type_hierarchy` facades misread the project mandate. These are navigation primitives, not mutations. They belong in Claude Code's file/symbol navigation layer, not in a write-focused refactoring tool.

---

## 4. Per-LSP variation makes universal facades brittle

The 33 facades are already stressed by per-language variation. Examples from the code:

- `ScalpelSplitFileTool` (line 199): `language: Literal["rust", "python"] | None` — Go, TypeScript, Java, C++ are not wired. Any new file-manipulation facade inherits this constraint.
- `ScalpelExtractTool` (line 384): same two-language guard, plus separate `kind` strings: rust-analyzer uses `refactor.extract.function`, rope bridge uses `rope.refactor.extract` (primitives.py line 861). A nominally "universal" extract facade already has two diverging code paths.
- `ScalpelImportsOrganizeTool` (line 895): dispatches on `source.organizeImports` for TypeScript/Go, `source.fixAll.ruff` for Python (landed as E13-py dedup gap fix), and `source.organizeImports` for Rust. Three servers, three distinct kind strings, one facade that looks simple from the outside.

Now extrapolate to 11 languages (Rust, Python, TypeScript, Go, C/C++, Java, Lean 4, SMT2, Prolog, ProbLog, Markdown). Adding one new facade nominally requires:

- 1 facade class + docstring (router-facing)
- 1 `LanguageStrategy` entry per language that supports the operation
- 1 test module per language (unit + integration)
- 1 skill `.md` per plugin tree (o2-scalpel-rust, o2-scalpel-python, etc.)
- 1–2 catalog rows per language per server

Conservatively: **~40 file touches per new facade across all languages** — and most of those touches are stubs that emit `CAPABILITY_NOT_AVAILABLE` because the LSP simply does not expose the operation. The long-tail dispatcher absorbs all of that for free.

---

## 5. Concrete YAGNI verdicts

**`scalpel_extract_constant`**
Covered by `scalpel_extract` (line 367) with `kind="refactor.extract.constant"` passed through to the LSP. Alternatively reachable via `scalpel_apply_capability` with the appropriate catalog id. No new facade warranted.

**`scalpel_change_signature`**
Partial coverage already exists: `ScalpelChangeReturnTypeTool` (line 1418) handles the most-requested case (return type). `ScalpelIntroduceParameterTool` (line 2004) covers adding a parameter. Full change-signature (reorder, remove, add with default) is a jdtls-specific feature absent from rust-analyzer and pylsp entirely — a universal facade would be a thin wrapper over a single-language capability, exactly the anti-pattern `scalpel_apply_capability` was built to avoid.

**`scalpel_move_method` / `scalpel_move_field`**
Semantically overlap with `scalpel_split_file` (line 183) which moves named symbols to target modules, and `scalpel_local_to_field` (line 1924) which promotes a local to the enclosing struct. The missing piece (moving a method across types) is an OOP-specific operation with no cross-language LSP standard kind — it would be a bespoke jdtls/clangd facade at best.

**`scalpel_pull_up` / `scalpel_push_down`**
Strictly OOP hierarchy operations. Only jdtls exposes them (`refactor.move.staticMember`, `refactor.pullUp`). Rust has no inheritance; Python has no formal interface. Building a facade that works for one language out of 11 is YAGNI by definition. These belong in `scalpel_apply_capability` until at least three concrete user requests surface.

**`scalpel_surround_with`**
This is template insertion (try/catch, if/else, for loop wrapper). It is not a standard LSP `textDocument/codeAction` kind across servers. Claude Code can accomplish this with `replace_symbol_body` + a string template; no LSP involvement needed. Adding a facade would bypass the LSP entirely, making it a text-manipulation helper dressed as an LSP tool — a category error.

---

## 6. Maintenance cost per added facade

Concrete file-touch accounting for one new facade added across all 11 languages today:

| Artifact | Count |
|---|---|
| Facade class in `scalpel_facades.py` | 1 |
| `LanguageStrategy` dispatch entries | up to 11 |
| Unit test modules | up to 11 |
| E2E test scenario files | up to 11 |
| Skill `.md` files (one per plugin tree) | up to 11 |
| Catalog JSON rows | up to 22 (some LSPs expose the kind on multiple servers) |
| `preferred_facade` backlinks in catalog | up to 11 |

That is **~40–77 file touches** for one facade, of which the majority are boilerplate stubs emitting `CAPABILITY_NOT_AVAILABLE`. The drift CI added in Stage 1F will flag every catalog row that lacks a test — so these stubs immediately generate CI debt.

Contrast: adding a catalog row for a new `refactor.*` kind costs 1 JSON edit and zero code. The LLM routes to `scalpel_apply_capability` automatically when `preferred_facade` is null.

---

## 7. Recommendation to the synthesis pair

Hold the line at 33 facades. The surface is already the largest in the MCP refactoring tool space for multi-language support. Invest instead in:

1. **Better LLM-routing heuristics for `scalpel_apply_capability`**: the `preferred_facade` field in each `CapabilityDescriptor` already guides the LLM to a bespoke facade when one exists. Improving the docstring quality and example coverage of `scalpel_capabilities_list` returns more routing accuracy per unit of work than any new facade.

2. **Catalog hygiene via drift CI**: the Stage 1F drift CI gate ensures catalog records stay in sync with what LSPs actually advertise. Keeping this green is cheaper than writing new facades and gives the long-tail dispatcher accurate data.

3. **Per-language gap-fill only on demonstrated demand**: the rule of thumb is three independent user requests for the same operation before promoting it from `scalpel_apply_capability` to a bespoke facade. Anything below that threshold is speculative.

---

## Open questions for the synthesis pair

- Which "missing" facades have users actually requested? The adversarial brief lists `scalpel_pull_up`, `scalpel_surround_with`, etc., but these appear to be theoretical wishlist items rather than logged user friction.
- What is the measured LLM tool-routing accuracy for the existing 33 facades? If routing precision is below ~90 %, adding more facades reduces it further by splitting the probability mass across more docstrings competing for attention in the same context window.
- Would a richer `filter_kind` taxonomy on `scalpel_capabilities_list` eliminate the need for any proposed facade entirely? That is a 5-line change versus a 40-file-touch facade.

---

## Citations

| Claim | File | Lines |
|---|---|---|
| 33 facade classes | `vendor/serena/src/serena/tools/scalpel_facades.py` | 183, 367, 514, 635, 883, 1155, 1207, 1254, 1360, 1418, 1463, 1504, 1549, 1595, 1644, 1692, 1756, 1884, 1924, 1964, 2004, 2051, 2093, 2139, 2227, 2288, 2367, 2484, 2618, 2718, 2781, 2853, 3007 |
| `scalpel_apply_capability` dispatcher | `vendor/serena/src/serena/tools/scalpel_primitives.py` | 273–325 |
| `scalpel_capabilities_list` + `filter_kind` | `vendor/serena/src/serena/tools/scalpel_primitives.py` | 71–106 |
| `merge_code_actions(only=[capability.kind])` | `vendor/serena/src/serena/tools/scalpel_primitives.py` | 228–232 |
| `preferred_facade` field in CapabilityDescriptor | `vendor/serena/src/serena/tools/scalpel_primitives.py` | 104, 129 |
| `language: Literal["rust", "python"]` restriction | `vendor/serena/src/serena/tools/scalpel_facades.py` | 199, 384, 527, 646 |
| `rope.refactor.*` kind strings | `vendor/serena/src/serena/tools/scalpel_primitives.py` | 861–863 |
| YAGNI + KISS mandate | `CLAUDE.md` | 34–36 |
| Project write/refactor mandate | `CLAUDE.md` | 5 |
