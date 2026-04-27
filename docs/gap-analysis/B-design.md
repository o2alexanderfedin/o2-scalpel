# o2-scalpel Design Intent Report — Agent B

**Scope:** Architectural and design documents only. No code audit; planning artifacts excluded.
**Sources:** README.md, CHANGELOG.md, CLAUDE.md, docs/design/*.md, docs/design/mvp/*.md (all open-questions resolutions), docs/install.md.
**Date:** 2026-04-26.

---

## 1. Vision Capabilities (Claimed Feature List)

### 1.1 Always-On MCP Tools (13 tools, MVP+Stage 2)
- `scalpel_split_file` (README.md:9; MVP scope report §5.1)
- `scalpel_extract` (README.md:10; MVP scope report §4.4.1)
- `scalpel_inline` (README.md:11; MVP scope report §4.3)
- `scalpel_rename` (README.md:9; MVP scope report §4.4.1)
- `scalpel_imports_organize` (README.md:9; MVP scope report §4.4.2)
- `scalpel_transaction_commit` (q2-12-vs-13-tools.md §5.1; promoted from dispatcher payload)
- `scalpel_capabilities_list` (README.md:13, §1G primitives)
- `scalpel_capability_describe` (README.md:13, §1G primitives)
- `scalpel_apply_capability` (README.md:13; long-tail dispatcher for 50+ assists)
- `scalpel_dry_run_compose` (MVP scope report §5.5)
- `scalpel_rollback` (README.md:13; single-checkpoint recovery)
- `scalpel_transaction_rollback` (q2-12-vs-13-tools.md §5.1)
- `scalpel_workspace_health` (MVP scope report §4.4.1)
- `scalpel_execute_command` (deferred, MVP scope report §4.5)

### 1.2 Deferred Specialty Facades (~11 tools, Stage 3 = v0.2.0)
**Rust facades (Wave A–C, 12 total):**
- `scalpel_rust_convert_module_layout` (install.md §What ships, Stage 3 Rust Wave A)
- `scalpel_rust_change_visibility` (install.md §What ships, Stage 3 Rust Wave A)
- `scalpel_rust_tidy_structure` (install.md §What ships, Stage 3 Rust Wave A)
- `scalpel_rust_change_type_shape` (install.md §What ships, Stage 3 Rust Wave A)
- `scalpel_rust_change_return_type` (install.md §What ships, Stage 3 Rust Wave B)
- `scalpel_rust_complete_match_arms` (install.md §What ships, Stage 3 Rust Wave B)
- `scalpel_rust_extract_lifetime` (install.md §What ships, Stage 3 Rust Wave B)
- `scalpel_rust_expand_glob_imports` (install.md §What ships, Stage 3 Rust Wave B)
- `scalpel_rust_generate_trait_impl_scaffold` (install.md §What ships, Stage 3 Rust Wave C)
- `scalpel_rust_generate_member` (install.md §What ships, Stage 3 Rust Wave C)
- `scalpel_rust_expand_macro` (install.md §What ships, Stage 3 Rust Wave C)
- `scalpel_rust_verify_after_refactor` (install.md §What ships, Stage 3 Rust Wave C)

**Python facades (Wave A–B, 8 total):**
- `scalpel_py_convert_to_method_object` (install.md §What ships, Stage 3 Python Wave A)
- `scalpel_py_local_to_field` (install.md §What ships, Stage 3 Python Wave A)
- `scalpel_py_use_function` (install.md §What ships, Stage 3 Python Wave A)
- `scalpel_py_introduce_parameter` (install.md §What ships, Stage 3 Python Wave A)
- `scalpel_py_generate_from_undefined` (install.md §What ships, Stage 3 Python Wave B)
- `scalpel_py_auto_import_specialized` (install.md §What ships, Stage 3 Python Wave B)
- `scalpel_py_fix_lints` (install.md §What ships, Stage 3 Python Wave B)
- `scalpel_py_ignore_diagnostic` (install.md §What ships, Stage 3 Python Wave B)

**Total at v0.2.0-stage-3-facades-complete: 13 always-on + 20 deferred = 34 MCP tools** (README.md:7, 13).

### 1.3 LSP Capability Coverage

**Rust (rust-analyzer):**
- 158 refactoring assists across 12 families reachable (MVP scope report §4.2): 
  - ~93 via ergonomic facades (split, extract, inline, rename, imports)
  - ~50 via long-tail dispatcher (`scalpel_apply_capability`)
  - ~15 overlap (quickfix diagnostics)
- 36 custom extensions (MVP scope report §4.3): 8 first-class facades, 27 typed pass-through, 1 explicit-block (`experimental/onEnter`)
- All ~52 LSP protocol methods wired (MVP scope report §4.5)

**Python:**
- 9 pylsp-rope commands (MVP scope report §4.4.1): extract.method, extract.variable, inline, local_to_field, method_to_method_object, use_function, introduce_parameter, quickfix.generate, organize_import
- 10 rope library-only ops (MoveGlobal, MoveModule, MoveMethod, ChangeSignature, EncapsulateField, IntroduceFactory, Restructure, relative_to_absolute, froms_to_imports, expand_stars)
- basedpyright: organizeImports, quickfix auto-import, diagnostic ignore, type annotation, commands (organize, restart, write-baseline, etc.)
- ruff: source.fixAll.ruff, per-rule quickfixes, source.organizeImports.ruff

### 1.4 Multi-Server Merge Invariants (§11.7 of design report)
Four invariants enforced when composing N LSP servers' edits into one transaction (MVP scope report §11):
1. Atomicity: in-memory snapshot, apply in order, restore on any failure
2. Version mismatch rejects entire edit (stale-version check per file)
3. Path-filter workspace-boundary enforcement (Q4 resolution, q4-changeannotations-auto-accept.md §7.1)
4. Change-annotation warning surface (Q4 resolution, q4-changeannotations-auto-accept.md §7.2–7.3)

### 1.5 Workspace-Boundary Enforcement (Q4 Resolution)
q4-changeannotations-auto-accept.md §7.1: any edit targeting path outside LSP-reported `workspaceFolders` rejects entire WorkspaceEdit atomically with `error_code = "EDIT_OUT_OF_WORKSPACE"`. Optional opt-in via `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` for vendored deps (§7.4).

### 1.6 Capability Catalog Drift CI
README.md §Capability discovery: pytest gate `test_stage_1f_t5_catalog_drift.py` enforces byte-equality between runtime catalog and checked-in baseline. Re-baseline via `--update-catalog-baseline` after LSP version bumps. Catalog hash exportable via `CapabilityCatalog.hash()` (SHA-256) for external drift detection.

### 1.7 Plugin/Skill Generator: `o2-scalpel-newplugin`
Q14 resolution (open-questions-resolution.md §Q14): CLI tool (~100 LoC Python + ~150 LoC templates) generates per-language Claude Code plugin directories. Input: `--language rust --out ./o2-scalpel-rust`. Output: boostvolt-shaped plugin tree with `.claude-plugin/plugin.json`, `.mcp.json`, `skills/`, `hooks/`. No bulk authoring; two reference plugins (rust-analyzer, clangd) shipped by hand; users/contributors generate rest on demand. Install hint: `o2-scalpel-newplugin <lang> <binary> <ext> [--install-hint "brew install …"] [--init-options options.json]` (install.md lines 54–62).

---

## 2. Open Questions Resolutions

| # | Question | Resolution Status | Deferred Items |
|---|---|---|---|
| Q10 | Cache-path stability & lazy spawn | Resolved (open-questions-resolution.md §Q10) | None — delivers lazy-spawn + pool_pre_ping, idle-shutdown, multilspy+platformdirs+pydantic |
| Q11 | Marketplace publication location | Resolved (open-questions-resolution.md §Q11) | Publication itself deferred to v1.1; layout finalized as multi-plugin repo at `o2alexanderfedin/claude-code-plugins` |
| Q12 | Two-LSP-process resource cost | Resolved (open-questions-resolution.md §Q12) | Per-language mitigations in place; v1.x may add aggressive pooling/multiplexing if `lspee` reaches 1.0 |
| Q13 (new) | Fork/rename feasibility | Resolved (open-questions-resolution.md §Q13) | Boostvolt: fork approved (MIT, attribution required); Piebald: private analysis only, file licensing inquiry, clean-room re-author |
| Q14 (new) | Bulk LSP-config plugins vs. generator | Resolved (open-questions-resolution.md §Q14) | Generator ships Stage 1J; bulk authoring explicitly rejected in favour of on-demand generation |
| Q1–Q4 (MVP open-questions) | pylsp-mypy, basedpyright pinning, ruff config, changeAnnotations | Resolved (docs/design/mvp/open-questions/*.md) | All pinned; Q4 yields workspace-boundary path filter (q4-changeannotations-auto-accept.md §7.1) |

All resolutions have corresponding specialist briefs under `/docs/research/` (cache-discovery-and-lazy-spawn, marketplace, two-process-problem, license-rename-feasibility; MVP Q1–Q4 under `open-questions/`).

---

## 3. Architecture-Level Promises NOT Scoped in MVP Plan

Cross-referencing MVP scope report §4.7 (out-of-scope canonical list) against the design's named dependencies and language strategies:

**Explicitly deferred to v2+ or post-MVP:**
- TypeScript / Go / clangd / Java `LanguageStrategy` plugins (paper design in OQ #7, design report §5 shows interface; v2+ scope)
- Test Explorer family (7 rust-analyzer methods, design report §4 explicitly skipped; v1.1)
- `viewHir`, `viewMir`, `viewCrateGraph`, `viewSyntaxTree`, `viewFileText`, `viewRecursiveMemoryLayout`, `getFailedObligations`, `interpretFunction` — reachable but unsurfaced (design report tables; primitive escape hatch only)
- Persistent disk checkpoints under `.serena/checkpoints/` durability (MVP uses LRU-only; v1.1)
- Stage 3 ergonomic facades post-v0.2.0 (design report Table §3 lists 12 v0.2.0 facades, 6+ additional patterns possible)
- Marketplace publication at `o2alexanderfedin/claude-code-plugins` (v1.1, open-questions-resolution.md Q11 rationale)

**Architectural promises made but implementation deferred:**
- Multi-client LSP multiplexing (design report §Q12 notes `lspee` pre-1.0; revisit if reaches 1.0 before scalpel v2)
- Anthropic native LSP-write integration (design report cites this as scalpel's deprecation trigger; horizon 6–18 months, tracked at anthropics/claude-code#24249, #1315, #32502)

---

## 4. Stages 2C / 4+ / v1.x Scope: Future-Dated Promises

Searching for version/stage labels in design docs:

| Feature / Promise | Version | Source | ~20-word context |
|---|---|---|---|
| Reference LSP-config plugins (rust-analyzer, clangd) | v2+ | MVP scope report §4.7 #11 | Hand-authored reference implementations; users generate rest on demand. |
| `o2-scalpel-newplugin` template generator | v2+ | MVP scope report §4.7 #10; design Q14 | Generator already exists in Stage 1J; v2+ scope ambiguous — likely shipped earlier. |
| TypeScript / Go strategy plugins | v2+ | design report §5 line 487; MVP scope §4.7 #1 | Paper design completed; additional languages pure plugin additions, no facade rewrites. |
| Java / C++ / Kotlin strategies | v2+ | Design §5 non-goals; MVP scope §4.7 #1 | Not mentioned in MVP scope; would follow pattern from additional strategies. |
| Marketplace publication to Claude marketplace | v1.1 | open-questions-resolution.md Q11, install.md §Out of scope | Multi-plugin repo layout finalized; distribution channel deferred after MVP. |
| Stage 3 ergonomic facades E13–E16 (Rust) + E4/5/8/11 (Python) | v0.2.0 | install.md §Out of scope; design Table §3 | 6 additional E2E scenarios; Stage 3 facades ship shortly after MVP. |
| `verify_after_refactor` composite (runnables + relatedTests + flycheck) | v0.2.0 | MVP scope §4.7 #7 | Combines rust-analyzer runtime discovery with diagnostics validation. |
| Persistent disk checkpoints (`.serena/checkpoints/` durability) | v1.1 | MVP scope §4.7 #8 | MVP uses in-memory LRU only; durability across sessions deferred. |
| Per-annotation confirm-handle (`scalpel_confirm_annotations(…)`) | v1.1 | q4-changeannotations-auto-accept.md §6.3 | Optional override when LLM passes `confirmation_mode="manual"` to compose. |
| gopls daemon reuse fix (golang/go#78668) | watch | open-questions-resolution.md §Open follow-ups | Upstream issue tracked; Go strategy degrades to per-workspace path until closed. |
| `lspee` multiplexer maturity (pre-1.0 today) | watch | open-questions-resolution.md §Open follow-ups | Architecturally correct; revisit two-process problem if reaches 1.0 + test suite. |
| Plugin-list API request (Anthropic) | watch | open-questions-resolution.md §Open follow-ups | Low-cost feature request (documented plugin-list API) filed with Anthropic. |

---

## 5. Per-Language Strategy Roadmap

### 5.1 Stage 1E Delivery Status
**Rust:** `RustStrategy` (full implementation, 14 refactoring assists reached, ~150 LoC interface implementation)
**Python:** *Skeleton* placeholder for pylsp + basedpyright + ruff integration (strategy interface scaffolded; three LSP clients wired in MVP scope report §4.4; implementations delivered as v0.2.0 stages)

### 5.2 Strategy Completion Path
Design report §5: strategy is a `Protocol` with ~15 methods (extract_module_kind, move_to_file_kind, module_declaration_syntax, module_filename_for, reexport_syntax, is_top_level_item, symbol_size_heuristic, execute_command_whitelist, post_apply_health_check_commands). RustStrategy implements all 15. Future strategies (TypeScript, Go, Python post-MVP) follow identical interface; no facade rewrites needed.

### 5.3 Additional Language Strategies Named
**Top priority:** TypeScript / vtsls (design report §Q #7, MVP scope §4.7 #1; paper-designed but implementation deferred)
**Mid priority:** Go / gopls (same; per-language mitigation: daemon reuse vs. fresh spawn)
**Future:** clangd (C++), jdtls (Java), Kotlin-language-server, Ada, Svelte, Vue, etc. — all via `o2-scalpel-newplugin` generator post-v1.0 (Q14 resolution).

### 5.4 Per-Language Mixin Extensions
None explicitly named as "mixins" in the design. The per-language approach is **strategy registration** (design §5, lines 393–397): facades detect language from file extension, look up registered strategy, delegate language-specific decisions. Example: `rust-analyzer.cargo.targetDir` override lives in `RustStrategy.lsp_init_overrides()` (design line 469); `pylsp`'s Rope library bridging lives in Python strategy.

---

## 6. Implementation-Quality Gates the Design Names

| Gate | File:Line | Description |
|---|---|---|
| **Capability catalog drift CI** | README.md §Capability discovery; MVP scope §4.7 #12 | `pytest test/spikes/test_stage_1f_t5_catalog_drift.py` enforces byte-equality; `CapabilityCatalog.hash()` SHA-256 exportable |
| **Golden baselines for applier tests** | MVP scope §4.6; install.md §Verify | ~80 unit tests covering WorkspaceEdit shape×option permutations; snapshot test fixtures under `tests/fixtures/` |
| **Snapshot tests for multi-LSP fan-in** | MVP scope §4.5 (multi-server merge); q4-changeannotations-auto-accept.md §8.3 | Atomic merge path runs once on converged edit; no per-server partial-failure leaks |
| **Four invariants (atomicity, version, path-filter, annotations)** | design report §11.7; q4-changeannotations-auto-accept.md §7.1–7.3 | Enforced in applier; §9 regression test suite verifies all four with/without annotations |
| **Priority + dedup-by-equivalence merge** | design report §11.6 (not yet quoted; specialist-scope implies) | When multiple LSPs emit same suggestion, highest priority wins; duplicates by semantic hash eliminated |
| **RAM-budget guard** | open-questions-resolution.md Q12; install.md §Prerequisites | 24 GB recommended; 16 GB with `O2_SCALPEL_DISABLE_LANGS` opt-out |
| **Transaction acquire-affinity** | design report §3.2 (SQLAlchemy pool_pre_ping analogue) | `is_alive()` pre-checkout probe; ~50 ms timeout; BrokenPipeError/ProcessLookupError/timeout → drop+respawn |
| **Telemetry hooks** | MVP scope §12.6 (not yet in design, deferred to implementation) | Every tool call logged with disposition (ok/err), LSP ops, duration; post-MVP analysis gates reversion/demotion decisions |
| **Workspace-boundary path filter** | q4-changeannotations-auto-accept.md §7.1; install.md §q4 | Reject entire WorkspaceEdit if any path outside LSP `workspaceFolders`; opt-in via `O2_SCALPEL_WORKSPACE_EXTRA_PATHS` |
| **Idempotency guarantees** | design report §3 (facades section); q2-12-vs-13-tools.md §5.2 | Transaction commit idempotent on second call; no double-apply hallucinations |
| **Checkpoint idempotency** | design report §3.6 (rollback_refactor) | Checkpoint consumed on first rollback; second call no-op returning empty list (prevent replay) |

---

## 7. Out-of-Scope Items by Design

**Explicitly marked "out of scope" in design or MVP scope report:**

| Item | Status | Source | Rationale |
|---|---|---|---|
| `experimental/onEnter` LSP method | explicit-block | MVP scope §4.3 #2; design §2 | Editor-keystroke semantics, snippet escape unfit for autonomous MCP server |
| Filesystem watcher on plugin cache | explicit-reject | open-questions-resolution.md Q10 | No watcher; snapshot at startup; refresh via `scalpel_reload_plugins` (matches Serena precedent) |
| Within-function extractions in v1 | MVP-primitive | design non-goals | `extract_function`, `extract_variable` reach-able via escape hatch, not first-class facade at MVP |
| `typeHierarchy` | non-goal | design §3 non-goals | Not offered by rust-analyzer; future strategies may opt in |
| Writing new rust-analyzer assists | non-goal | design §3 non-goals | Upstream contribution, not in-scope for scalpel |
| Streaming LSP ops / async tool apply | non-goal | design §3 non-goals | Serena synchronous today; maintain status quo |
| Native IDE integrations (VSCode, IntelliJ plugins) | v2+ | design deployment section | Scalpel is MCP-only; IDE plugins are separate effort |

---

## Summary

o2.scalpel design commits to **comprehensive LSP write coverage** for Rust + Python (all 158 rust-analyzer assists, all 18 Python LSP ops reachable; 34 always-on + deferred MCP tools at v0.2.0) via a **language-agnostic facade + strategy plugin architecture** that scales to TypeScript, Go, etc. in v2+ with zero facade rewrites. The design formalizes **three critical gates** (workspace-boundary filtering, atomic multi-LSP merge, capability catalog drift CI) and **four transaction invariants** (atomicity, version, path-filter, annotations) to prevent silent regressions. MVP cuts at Stage 1+2 (13 always-on tools + 5 ergonomic facades); Stage 3 (20 deferred specialty facades) ships v0.2.0 immediately post-MVP. Marketplace publication, additional language strategies, persistent checkpoints, and per-annotation confirms all deferred to v1.1+ per explicit resolution docs. The design is conservative on feature scope, aggressive on safety (workspace-boundary enforcement, audit logging, rollback recovery).

