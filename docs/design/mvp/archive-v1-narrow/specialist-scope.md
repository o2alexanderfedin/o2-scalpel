# MVP Scope — Engineering Delivery Specialist View

Status: report-only. Brainstorm input for the MVP scope round. Not authoritative by itself; companions in this directory synthesize across specialist perspectives.

Scope-discipline lens. Ruthless triage applied throughout. No time estimates per project `CLAUDE.md`; sizing via small/medium/large plus LoC counts.

Cross-references:
- [Main design](../2026-04-24-serena-rust-refactoring-extensions-design.md) — authoritative architecture.
- [Open-questions resolution](../2026-04-24-o2-scalpel-open-questions-resolution.md) — Q10/Q11/Q12/Q13/Q14 decisions already in place.
- Research briefs: [cache-discovery](../../research/2026-04-24-cache-discovery-brief.md), [two-process](../../research/2026-04-24-two-process-brief.md), [marketplace](../../research/2026-04-24-marketplace-brief.md), [license-rename](../../research/2026-04-24-license-rename-brief.md).

---

## §1 — Falsifiable MVP statement

> **Scalpel MVP is done when `split_file_by_symbols` + `fix_imports` + `rollback_refactor` successfully refactor `calcrs/src/lib.rs` (Rust fixture) and `calcpy/calcpy/__init__.py` (Python fixture) into ≥3 modules each with `cargo test` / `pytest` byte-identical output to the pre-refactor baseline, driven through a stdio MCP client (`pytest -m e2e`) against a scalpel MCP server installed via `uvx --from <local-path>`.**

One sentence. Falsifiable on five axes:
1. Two languages covered (Rust AND Python).
2. Two specific fixtures named (`calcrs` exists; `calcpy` must be authored for MVP).
3. Two mutating facades + one recovery facade exercised end-to-end (not just compiled).
4. Semantic equivalence measured by test output byte-comparison, not diagnostics count.
5. A specific, reproducible distribution path (`uvx --from <path>`) — not "marketplace install" at MVP.

If any of those five fail, MVP is not done. If all five pass, MVP is done regardless of what else remains unfinished.

---

## §2 — Feature triage matrix

Legend:
- **MVP** = blocks the §1 statement. Cut = MVP cannot ship.
- **v1.1** = follows MVP immediately; small/medium add-on; defers one concrete risk.
- **v2+** = genuinely optional; may never ship; captured only so nobody relitigates.

### 2.1 Layer 1 — LSP primitive layer (`solidlsp`)

| Item | Stage | Justification |
|---|---|---|
| `request_code_actions` on `SolidLanguageServer` | MVP | Every facade ultimately issues this; no facade works without it. |
| `resolve_code_action` | MVP | `codeAction/resolve` is the only path rust-analyzer exposes to real refactorings. |
| `execute_command` primitive | v1.1 | rust-analyzer doesn't register it; pyright uses it mostly for organize-imports which we get via `codeAction` anyway. Defer. |
| `workspace/applyEdit` reverse-request handler | MVP | Without it, server-initiated edits silently drop; fails the rollback/atomicity property. Blocks E3. |
| `$/progress rustAnalyzer/Indexing` tracker + `wait_for_indexing()` | MVP (Rust) | Without it, first `codeAction` on rust-analyzer returns empty or `ContentModified`; flakes E1/E2/E7. |
| `$/progress` parsing beyond indexing-done | v2+ | Partial indexing progress bars, percent-complete telemetry, etc. Not needed to gate on "ready". |
| `WorkspaceEdit` applier: `TextDocumentEdit` | MVP | Every facade produces these. |
| `WorkspaceEdit` applier: `CreateFile` | MVP | `move_module_to_file` returns this; E1 blocked without. |
| `WorkspaceEdit` applier: `RenameFile` | MVP | `move_from_mod_rs` / `move_to_mod_rs` need it (Rust); also needed if Python strategy moves `__init__.py` between layouts. |
| `WorkspaceEdit` applier: `DeleteFile` | v1.1 | No MVP facade emits DeleteFile. Keep the stub to fail-loud on encounter; full implementation later. |
| `changeAnnotations` with `needsConfirmation` | v1.1 | MVP policy: reject annotated edits; one warning line in applier; no UI affordance. |
| Order preservation inside `documentChanges` | MVP | Correctness bug without it. |
| Version check on `TextDocumentEdit` | MVP | Prevents E4 flakes; silent corruption vector otherwise. |
| Snippet-marker stripping | MVP (Rust) | Advertise `snippetTextEdit:false`; 5 lines. Cheap, must ship. |
| Atomic apply (in-memory snapshot + restore) | MVP | Rollback/E3 blocks directly. |
| Checkpoint store — in-memory LRU (10 entries) | MVP | Required for E3. |
| Checkpoint store — persistent disk (`.serena/checkpoints/`) | v1.1 | MVP lives in-memory only. Session crash = lose checkpoints; acceptable tradeoff for ship. |
| Inverse `WorkspaceEdit` computation | MVP | Rollback mechanism. |

### 2.2 Layer 2 — Facade tools (language-agnostic MCP surface)

| Facade | Stage | Justification |
|---|---|---|
| `split_file_by_symbols` | MVP | The primary value proposition. The §1 statement names it directly. |
| `fix_imports` | MVP | Every `split_*` produces dangling `use` / `import` statements; without `fix_imports` the refactored code doesn't compile/pass. Directly gates E1+E9. |
| `rollback_refactor` | MVP | Safety net. Without it we cannot honestly claim "atomic". E3 blocks. |
| `plan_file_split` | v1.1 | LLM can construct the `groups` dict directly from `documentSymbol` (already exposed by CC's built-in LSP). Not strictly required to ship the split. Medium value, defer. |
| `extract_symbols_to_module` | v1.1 | Thin wrapper over `split_file_by_symbols` with `groups={new_module: symbols}`. Sugar; LLM can call the primary facade the same way. Defer. |
| `move_inline_module_to_file` | v1.1 | Narrow surgical facade. Rust-specific shape today; waiting until we stabilize on two-language contract reduces risk of baking Rust-isms in. |

### 2.3 Primitive tools (escape hatch)

| Primitive | Stage | Justification |
|---|---|---|
| `list_code_actions` | v1.1 | MVP expects facade to succeed; LLM escape hatch can wait. |
| `resolve_code_action` | v1.1 | Same. |
| `apply_code_action` | v1.1 | Same. |
| `execute_command` | v2+ | Server-specific. No MVP facade depends on it. |

**Rationale for cutting the whole primitive layer out of MVP**: the facades already call the underlying LSP methods internally. Exposing them as separate MCP tools is a surface-area expansion, not a new capability. If the facade works on §1's two fixtures, the primitives are free to expose post-MVP. If the facade doesn't work, exposing its guts to the LLM won't fix it — the bug is in the applier or the strategy.

### 2.4 Layer 3 — Language strategies

| Strategy | Stage | Justification |
|---|---|---|
| `LanguageStrategy` Protocol / interface | MVP | Required by `split_file_by_symbols` to compile. |
| Registry (static dict) | MVP | One line of code; required to resolve strategy by language. |
| `RustStrategy` | MVP | Language priority change dictates it. |
| `PythonStrategy` | MVP | Language priority change dictates it. |
| `TypeScriptStrategy` paper design | MVP (paper-only) | Required to validate the abstraction against a third shape without implementing it. Prevents baking Rust+Python-isms into the facade. |
| `GoStrategy`, `TSStrategy` implementations | v1.1 | Not required for §1. |
| `NotImplementedStrategy` placeholders for top-20 | v2+ | Noise; replace with clean `language_unsupported` failure from the facade. |
| Server-extension whitelist (`execute_command_whitelist`) | v1.1 | MVP facades never call whitelisted methods; the whitelist is unused code at MVP. |
| `post_apply_health_check_commands` | v1.1 | MVP's semantic-equivalence test runs `cargo test` / `pytest` externally; no in-process health check needed. |
| `lsp_init_overrides` (e.g., `cargo.targetDir`) | MVP | Without it, scalpel's rust-analyzer contends on the same `target/` as CC's. Corrupts E1 intermittently. |
| Entry-point-based third-party strategy discovery | v2+ | Zero demand today; static dict is fine. |

### 2.5 Deployment

| Item | Stage | Justification |
|---|---|---|
| `o2-scalpel` plugin directory (`.claude-plugin/plugin.json` + `.mcp.json`) | MVP | The `uvx --from <path>` install target. |
| `SessionStart` verify hook (`hooks/verify-scalpel.sh`) | v1.1 | Nice ops affordance. Users will feedback-loop the hard way at MVP; acceptable. |
| Marketplace repo `o2alexanderfedin/claude-code-plugins` | v1.1 | §1 explicitly ships via local `uvx --from <path>` — no marketplace dependency at MVP. Details §7. |
| `marketplace.json` | v1.1 | Same. |
| `o2-scalpel-newplugin` template generator (Q14) | v2+ | Zero MVP users need to generate plugins; two reference plugins are v1.1 work at earliest. |
| Two reference LSP-config plugins (`rust-analyzer-reference`, `clangd-reference`) | v2+ | We already rely on user-installed CC LSP plugins (boostvolt) for read. Scalpel doesn't need its own reference plugins to ship. |
| Sibling-LSP discovery (walking `~/.claude/plugins/cache/`) | MVP (minimal) | Required so the scalpel binary can find `rust-analyzer` and a Python LSP without explicit config. |
| Env-var override `O2_SCALPEL_PLUGINS_CACHE` | MVP | One `os.environ.get` line; insurance against host-layout churn during MVP testing. |
| `platformdirs` path resolution | MVP | Already a 1-line dep; cross-platform correctness. |
| Config-file override `~/.config/o2.scalpel/config.toml` | v1.1 | MVP uses env-var only; config file is the second escape hatch. |
| `scalpel_reload_plugins` MCP tool | v1.1 | MVP re-scans on process start; users restart the server if they install a new LSP plugin mid-session. |

### 2.6 Cache discovery & lazy spawn

| Item | Stage | Justification |
|---|---|---|
| `multilspy` adoption (LSP client) | MVP | Serena already proves it; hand-rolling is wasted MVP budget. |
| `pydantic` schema on `.lsp.json` | MVP | Fail-loud is table stakes for the §1 fixture CI. |
| Lazy spawn on first use | MVP | Without it, the MCP server eagerly spawns rust-analyzer at boot — at 4–8 GB on a 16 GB laptop this fails the §9 resource floor in minutes. |
| `is_alive()` pre-checkout probe | v1.1 | MVP uses one-shot lifecycle per MCP session; long-lived pooling semantics can wait. |
| Idle-shutdown after N minutes | v1.1 | MVP tests don't sit idle; this is a production-run concern. |
| `(language, project_root)` registry | MVP | Required for reuse within a single session. |

### 2.7 Marketplace & distribution

| Item | Stage | Justification |
|---|---|---|
| Local install via `uvx --from <path> serena-mcp-server --mode scalpel` | MVP | §1 names this exact path. |
| `o2-scalpel` plugin.json for local install | MVP | The plugin harness Claude Code reads. |
| `vendor/serena/` submodule pointing at fork | MVP | The actual executable comes from here. |
| Public marketplace at `o2alexanderfedin/claude-code-plugins` | v1.1 | Post-MVP public release. |
| Published version tag `v0.1.0` on the marketplace | v1.1 | Same. |
| `boostvolt` fork under neutral name (`o2-lsp-marketplace`) | v2+ | Per Q13 we're allowed to — but MVP doesn't need it. We piggyback on the user's existing boostvolt install. |
| Piebald-derived clean-room manifests | v2+ | Same. Zero MVP value. |
| `o2-scalpel-newplugin` generator | v2+ | Same. |
| Vendor-exclusion CI guard (Piebald) | v1.1 | Must exist before any public release (Q13). Not a gate for the local-install MVP. |

### 2.8 Fixtures

| Item | Stage | Justification |
|---|---|---|
| `calcrs` Rust fixture (`/test/e2e/fixtures/calcrs/`) | MVP | §1 names it; already fully specified in the design §Testing Strategy. |
| `calcpy` Python fixture (`/test/e2e/fixtures/calcpy/`) | MVP | §1 names it; does not exist yet; must be authored. Shape mirrors calcrs: ~500–700 LoC single-module arithmetic evaluator, zero external deps, ~25 pytest tests. |
| `big_cohesive.rs` / `big_heterogeneous.rs` integration fixtures | MVP | Needed for integration-test coverage of the planning shape in isolation from E2E (faster CI feedback). |
| `cross_visibility.rs` | v1.1 | Visibility-promotion edge case. Nice-to-have; MVP fixture-crate split exercises only the happy path. |
| `with_macros.rs` | v1.1 | Proc-macro robustness. Defer. |
| `inline_modules.rs` | v1.1 | Feeds `move_inline_module_to_file` (v1.1). |
| `mod_rs_swap.rs` | v1.1 | Feeds `move_from_mod_rs` / `move_to_mod_rs` (v1.1). |
| `calcpy` — `pyproject.toml` + `tests/` | MVP | Required to run `pytest` for semantic equivalence. |
| Multi-crate / multi-package fixture | v1.1 | E5 scenario; not blocking. |

### 2.9 E2E scenarios

| # | Scenario | Stage | Justification |
|---|---|---|---|
| E1 | Happy-path split (Rust) | MVP | §1 gate. |
| E1-py | Happy-path split (Python) | MVP | §1 gate — Python equivalent. |
| E2 | Dry-run → inspect → commit | MVP | Atomicity contract verification. Cheap; must ship. |
| E3 | Rollback after failed check | MVP | Safety property. §1 rollback claim. |
| E9 | Semantic equivalence (Rust) | MVP | `cargo test` byte-identical. §1 directly. |
| E9-py | Semantic equivalence (Python) | MVP | `pytest` byte-identical. §1 directly. |
| E10 | Regression on `rename_symbol` | MVP | Serena's existing primitive must not break; user-profile directive (frustrations: regression). |
| E4 | Concurrent edit mid-refactor | v1.1 | `ContentModified` retry is implemented at MVP; explicit race-condition E2E can wait. |
| E5 | Multi-crate / multi-package workspace | v1.1 | MVP fixture is single-package. |
| E6 | `fix_imports` on glob | v1.1 | MVP calls `fix_imports` on the enumerated file list. Glob expansion is icing. |
| E7 | rust-analyzer cold start | v1.1 | `wait_for_indexing()` is MVP; explicit cold-start E2E measurement can wait. |
| E8 | LSP crash recovery | v1.1 | MVP covers clean shutdown; kill-mid-refactor is an ops edge case. |

**MVP E2E set: E1, E1-py, E2, E3, E9, E9-py, E10. Seven scenarios. Must all be green to ship.**

---

## §3 — Two-language cost analysis (Rust + Python vs Rust-only)

### 3.1 Baseline: the 2,450 LoC estimate

From the main design's §Effort Estimate:

| Layer | Files | LoC | Language-agnostic? |
|---|---|---|---|
| `solidlsp` primitive methods | 2 | ~90 | Fully agnostic |
| `rust_analyzer.py` init tweak | 1 | ~5 | Rust-specific |
| WorkspaceEdit applier upgrade | 1 | ~150 | Fully agnostic |
| Checkpoint/rollback machinery | 1 | ~100 | Fully agnostic |
| Primitive tools | 1 | ~200 | Fully agnostic (v1.1 per §2 above) |
| Facade tools | 1 | ~600 | Fully agnostic by construction |
| `LanguageStrategy` interface + registry | 2 | ~120 | Fully agnostic |
| `RustStrategy` plugin | 1 | ~180 | Rust-specific |
| Unit tests | 1 | ~300 | Mostly agnostic |
| Integration tests | 1 + 6 fixtures | ~400 + fixtures | Split: driver agnostic, fixtures Rust-only |
| E2E harness + scenarios | 1 + 10 + conftest | ~500 + workspaces | Split: harness agnostic, fixtures Rust-only |

**Language-agnostic LoC in the baseline**: ~1,660 (lines 1, 3, 4, 5, 6, 7, 9 + ~80% of 10+11). That's **≈68% of the 2,450 LoC baseline is already language-agnostic**. Adding a second language does not double the codebase — it adds the strategy plus the fixture plus the scenario pair.

### 3.2 Concrete Python delta

| Element | New files / LoC | Notes |
|---|---|---|
| `PythonStrategy` class | 1 file, ~180 LoC | Proportional to `RustStrategy`. Python's module layout is simpler (no `mod foo;` declarations — the filesystem IS the declaration) but re-export syntax and `__init__.py` handling add equal complexity back. Estimate-preserving. |
| `pyright` / `pylsp` init integration in `solidlsp` | Existing in Serena | Serena already supports pyright. The language server driver is already there; no new solidlsp file. |
| `calcpy` fixture directory | 1 fixture workspace, ~600 LoC | `pyproject.toml` (~15 LoC), `calcpy/__init__.py` (~550 LoC — monolithic on purpose), `tests/test_smoke.py` (~30 LoC). Matches calcrs shape. |
| Python-specific E2E scenario pair (E1-py, E9-py) | Embedded in existing E2E harness, ~40 LoC per scenario | Same harness, new fixture constant, new expected-output snapshots. Two scenarios × ~40 LoC = 80 LoC. |
| Python-specific integration fixture (`big_heterogeneous.py`) | 1 fixture, ~500 LoC | Integration-test level; mirrors the Rust counterpart. |
| Python-specific unit test cases | Embedded in `test_refactoring.py`, ~50 LoC | Name-path resolution edge cases Python-specific (e.g., `__init__.py` vs module.py addressing). |
| Python-specific docstring / README callout in `PythonStrategy` | <10 LoC | |

**Python delta total: ~180 + 600 + 80 + 500 + 50 + 10 ≈ 1,420 LoC**, across ~5 new files.

**Compared to 2,450 LoC Rust-only baseline**: Python MVP addition is **+58%** of the Rust-only codebase. That is significantly less than doubling (which would be +100%), because the 68% agnostic core is reused verbatim.

### 3.3 Is `PythonStrategy` really ~180 LoC, or more?

The question is whether Python's shape stresses the `LanguageStrategy` Protocol the same way Rust does. Walking the Protocol methods:

| Method | Rust impl | Python impl | Python LoC estimate |
|---|---|---|---|
| `extract_module_kind()` | `"refactor.extract.module"` | pyright: `"refactor.extract.function"` is misleading — pyright does not have "extract module". The Python story is filesystem-native. This method likely returns `None` and the facade falls back to a Python-specific path (see §3.4 below). | 5 LoC (single return). |
| `move_to_file_kind()` | `"refactor.move"` (rust-analyzer's path) | `None` — pyright/pylsp have no such code action | 5 LoC |
| `rename_kind()` | `"refactor.rewrite"` | `"refactor.rewrite"` | 5 LoC |
| `module_declaration_syntax()` | `"mod foo;"` | Returns `""` (Python modules are filesystem-defined; no declaration inside the parent). Some callers require `from . import foo` in `__init__.py`; strategy handles that. | ~25 LoC incl. `__init__.py` edge-case. |
| `module_filename_for()` | `foo/mod.rs` or `foo.rs` | `calcpy/foo.py` or `calcpy/foo/__init__.py` (package-style) | ~20 LoC |
| `reexport_syntax()` | `"pub use foo::Bar;"` | `"from .foo import Bar"` or `__all__` list handling | ~30 LoC (the `__all__` branch is non-trivial). |
| `is_top_level_item()` | filter by `DocumentSymbol.kind` ∈ {function, class, struct, enum, impl} | filter by `DocumentSymbol.kind` ∈ {function, class} | ~15 LoC |
| `symbol_size_heuristic()` | LoC span | LoC span | ~10 LoC |
| `execute_command_whitelist()` | rust-analyzer extensions | `frozenset()` — pylsp/pyright whitelist empty for MVP | 2 LoC |
| `post_apply_health_check_commands()` | `runFlycheck` | `[]` — MVP runs `pytest` externally, not via LSP | 2 LoC |
| `lsp_init_overrides()` | `cargo.targetDir` override | None needed — pyright has no on-disk artifacts | 5 LoC |

Subtotal: ~124 LoC pure Protocol. Plus:
- File-layout decision logic (package vs module style): ~30 LoC.
- `__init__.py` rewriting helper: ~30 LoC.

**Python total: ~180 LoC.** Close enough to the proportional-to-Rust estimate that the 1,420 LoC Python-MVP delta stands.

### 3.4 Hidden cost: `move_to_file_kind() == None` path

This is the biggest abstraction-stress point. Rust's facade orchestration relies on `move_module_to_file` doing the rename + `mod foo;` rewiring. Python has no such LSP assist. The facade must handle `move_to_file_kind() is None` by:

1. Using the WorkspaceEditApplier's `CreateFile` + text-copy path directly (computed from `documentSymbol` ranges read by CC's LSP).
2. Generating the import-rewrite edits itself, sourced from the strategy's `reexport_syntax()` and the discovered references.

This is a non-trivial addition to the facade — probably **+80 LoC inside `refactoring_tools.py`** (a composition branch for strategies that don't have a server-side move assist). It also applies retroactively to Go, TypeScript, and every future non-rust-analyzer language, so it is not wasted work.

**Revised Python-MVP delta: +1,420 LoC (strategy + fixture + scenarios) + ~80 LoC (facade's no-server-assist branch) = ~1,500 LoC.**

That +80 LoC facade branch is arguably **anti-cost**: its existence forces the facade to be genuinely language-agnostic instead of a thin wrapper around rust-analyzer. This is the point of having Python in MVP.

### 3.5 Summary

| Option | LoC | Files changed / new | Agnostic % |
|---|---|---|---|
| Rust-only MVP | 2,450 | ~18 | 68% |
| Rust + Python MVP | ~3,950 | ~23 | 75% |
| Python-only delta | +1,500 (+61%) | +5 | — |

The two-language MVP is **not** double-Rust; it is roughly Rust-plus-61%. The headline cost is the fixture (`calcpy` at ~600 LoC) and the integration-level test fixture; the strategy itself is modest.

### 3.6 What the agnostic 68% actually contains

This number deserves more than a percentage; the LoC budget choices below depend on it.

| Module | LoC | Why agnostic |
|---|---|---|
| `WorkspaceEditApplier` (`code_editor.py` extensions) | ~150 | LSP `WorkspaceEdit` is a protocol-level shape; CreateFile/RenameFile/TextDocumentEdit/changeAnnotations apply identically regardless of source language. |
| Checkpoint/rollback (in-mem LRU + inverse edit) | ~100 | Operates on `WorkspaceEdit` snapshots, not source code. |
| `SolidLanguageServer` extensions (request_code_actions, resolve_code_action, $/progress) | ~90 | LSP methods are protocol-level. Only the **interpretation** of returned `CodeAction.kind` strings is language-specific, and that lives in the strategy. |
| Facade `split_file_by_symbols` orchestration | ~600 | All Rust-isms are delegated to `RustStrategy`. Branches on `move_to_file_kind() is None` add cost but no language dependency. |
| Facade `fix_imports` orchestration | ~120 (subset of 600) | Calls `codeAction` with `kinds=["source.organizeImports", "quickfix"]` — both standard LSP kinds. |
| `LanguageStrategy` Protocol declaration | ~120 | Pure interface; no implementation. |
| Lazy-spawn pool (`lsp_pool.py`) | ~100 | Wraps multilspy generically. |
| Plugin-cache discovery | ~80 | Operates on `.lsp.json` shape only. |
| Test harness (E2E driver, conftest) | ~150 | Uses MCP stdio client; no language assumption. |

Grand subtotal: ~1,510 fully agnostic LoC. Add ~150 LoC of unit tests that are language-neutral (Protocol-shape tests, applier-shape tests, checkpoint round-trips) and we land at ~1,660 — the 68% claim. **Inverting the metric**: 32% is language-specific, mostly fixtures and the two strategies. Adding a language touches ~32% of the codebase, not 100%. This is the math that makes Option A defensible.

### 3.7 Counter-check: is `RustStrategy` really 180 LoC?

Same exercise as §3.3, applied to Rust:

| Method | Implementation | LoC |
|---|---|---|
| `extract_module_kind()` | `return "refactor.extract.module"` | 1 |
| `move_to_file_kind()` | `return "refactor.move"` | 1 |
| `rename_kind()` | `return "refactor.rewrite"` | 1 |
| `module_declaration_syntax()` | branches on `ParentModuleStyle.{dir, mod_rs}`, returns `f"mod {name};"` plus visibility prefix | ~25 |
| `module_filename_for()` | `dir`: `Path(parent) / module / "mod.rs"`; `mod_rs`: `Path(parent) / f"{module}.rs"` | ~20 |
| `reexport_syntax()` | `f"pub use {module}::{symbol};"` plus public-API preservation logic | ~35 |
| `is_top_level_item()` | `kind in {Function, Struct, Enum, Trait, Impl, Const, Static, Module}` | ~20 |
| `symbol_size_heuristic()` | LoC span | ~10 |
| `execute_command_whitelist()` | frozen set of 6 RA extensions | ~10 |
| `post_apply_health_check_commands()` | `[ExecuteCommand("rust-analyzer/runFlycheck")]` (deferred to v1.1; MVP returns `[]`) | ~5 |
| `lsp_init_overrides()` | dict with `cargo.targetDir` | ~15 |
| Module-level docstring + imports + class skeleton | — | ~35 |

Total: ~178 LoC. The 180 LoC estimate holds within rounding. By symmetry, the 180 LoC PythonStrategy estimate is plausible. **Both estimates are bounded by the size of the Protocol, not by language complexity** — which is what we want from a small, fixed-shape strategy seam.

---

## §4 — Risk analysis: two-language MVP vs. Rust-only MVP

### 4.1 Option A — Rust + Python at MVP (current ask)

**Pros:**
- Validates the `LanguageStrategy` abstraction against two genuinely different languages. Python's filesystem-is-the-module property forces the facade to handle `move_to_file_kind() is None` at MVP. This is exactly the kind of abstraction-stress test that paper design (Open Question #7 in the main design) flagged as "cheap to do, expensive to skip".
- Commits to the dual-language contract publicly. Post-MVP, adding TS / Go / C++ is plugin work, not facade work.
- Matches the product-priority change (Python is top priority alongside Rust). Shipping Rust-only and calling it MVP contradicts the product brief.
- Zero Rust-analyzer-specific assumptions can sneak into the facade (CI catches them via E1-py / E9-py).

**Cons:**
- +61% LoC / +~1,500 LoC. Direct delivery-cost increase.
- Doubles the E2E fixture surface area. `calcpy` must be authored from scratch (calcrs already exists).
- Doubles the LSP-driver configuration surface: pyright init options, pytest baseline, `__init__.py` edge cases.
- Python's LSP story is fragmented (pyright, pylsp, basedpyright, ruff-lsp). MVP must pin one. Pyright is the obvious choice (used by Serena today) but commits scalpel to whatever pyright's code-action surface provides — which, as §3.4 notes, is thin.
- The `move_to_file_kind() is None` path is genuinely new facade code, with its own bug surface and its own test cases.

### 4.2 Option B — Rust-only MVP, Python at v1.1

**Pros:**
- Smaller MVP: 2,450 LoC, one fixture, one language server to debug.
- Faster to the first honest "it works" demo.
- Less risk that a Python-only bug (pyright init, `__init__.py` edge cases) blocks the Rust-primary value proposition.

**Cons:**
- **The facade can be silently Rust-biased.** Without a second strategy exercising it at CI time, "language-agnostic" is a hope, not a property. The main design anticipated this exact failure mode in Open Question #7 ("Shipping only RustStrategy risks designing the interface around Rust's shape") and proposed a paper-design mitigation. Paper design is cheap; it is also strictly weaker than a second real implementation.
- Retrofitting a second language at v1.1 means re-opening the facade for structural edits. That breaks the v1.0-stability promise we'd have implicitly made.
- Contradicts the product-priority change. Shipping Rust-only as MVP and calling Python "next" is a credibility mismatch.
- The $/progress, WorkspaceEdit, and lazy-spawn machinery is fully exercised by Rust alone; the extra Python fixture doesn't cost that machinery any more. The extra cost is isolated to the strategy + fixture, which §3 showed is +61%, not +100%.

### 4.3 Recommendation

**Ship Option A: Rust + Python at MVP.**

The +61% LoC cost is real but bounded. The abstraction-validation payoff is the single highest-leverage design insurance we can buy — an MVP that bakes in Rust assumptions is an MVP that will be rewritten, not extended, when any second language arrives. The design already flagged this risk (OQ #7) without committing to a mitigation; the product-priority change now forces the mitigation.

Conditions on accepting the recommendation:
1. `calcpy` fixture authoring is on the critical path and starts in stage-1 (see §5). No compiler gate; it must exist before `PythonStrategy` lands.
2. The facade's no-server-assist branch is implemented in the small stage as a visible, named path, not buried in an `if strategy.move_to_file_kind() is None:` hidden inside `split_file_by_symbols`.
3. The TypeScript strategy remains paper-only at MVP — adding a third language buys nothing the first two don't already buy.

Honest statement of residual risk: pyright's code-action surface is thinner than rust-analyzer's. If pyright refuses to emit any useful `refactor.*` actions on our Python fixture, the Python MVP falls back to filesystem-based module moves computed entirely from CC's built-in `documentSymbol` — the facade's no-server-assist branch becomes the *primary* Python path, not a fallback. That is acceptable (it's still LSP-informed, just not LSP-driven), but it is a design divergence worth stating aloud.

### 4.4 Decision criteria, in order

If a future synthesis round wants to revisit this recommendation, here are the criteria in priority order:

1. **Does Python MVP add >2× the Rust-only LoC?** If yes, reconsider. Today: no (+61%).
2. **Does pyright emit any code action on `calcpy` during a stage-1 spike?** If no (zero useful kinds), the Python path becomes facade-orchestrated text edits and the abstraction-validation argument weakens (we'd be validating "facade can compose without LSP help" rather than "facade adapts to two LSPs"). Still valuable, but a smaller win.
3. **Does the §1 statement hold value if Python is dropped?** Marginally yes — the design becomes "Rust refactoring tool for Claude Code" rather than "language-agnostic refactoring tool for Claude Code". The product brand changes; the engineering quality is comparable.
4. **Does Rust-only ship meaningfully sooner?** §5's stage-3 size is dominated by the facade orchestration (~600 LoC, large), not by the Python strategy (~180 LoC, small). Skipping Python saves ~1,500 LoC of stage-1/3 work — meaningful but not transformative; stage-2 (medium) is unchanged either way.

By these criteria, Option A holds today. If criterion (2) goes against us during stage 1, Option A is still defensible (the no-server-assist branch was always going to be needed for Go and TS), but the framing shifts from "validates the strategy seam" to "validates the seam plus the no-LSP-help fallback".

### 4.5 What the recommendation is NOT

This recommendation does **not** say "Python is as important as Rust." It says "Python is sufficiently important and sufficiently cheap that excluding it from MVP is a worse engineering tradeoff than including it." The product priority claim (both are top priority) is accepted as input; the engineering response is to find the cheapest two-language MVP shape and ship that.

This recommendation also does **not** generalize to "every additional language is +61%." The first additional language pays the full strategy cost plus the full fixture cost plus the full E2E pair cost. The *second* additional language (TypeScript at v1.1) pays only strategy + fixture + E2E pair, since the fixture-authoring patterns and the no-server-assist branch already exist. Expect TS at v1.1 to be ~+800 LoC, not +1,500. By v1.2 (Go) the marginal cost flattens further.

---

## §5 — Staging plan (small → medium → large) for dual-language MVP

Three stages, each green before the next starts. Each stage ends with a tag: `mvp-stage-1`, `mvp-stage-2`, `mvp-stage-3`. Stage 3 tag = MVP.

### 5.1 Stage 1 (small): foundation + strategy contract

Goal: primitives compile, strategy Protocol locked, fixtures exist. Nothing end-to-end yet.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 1 | `vendor/serena/src/solidlsp/ls.py` | Modify | +60 | — |
| 2 | `vendor/serena/src/solidlsp/lsp_protocol_handler/server.py` | Modify | +30 | — |
| 3 | `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py` | Modify | +5 | — |
| 4 | `vendor/serena/src/serena/refactoring/__init__.py` | New | +15 (registry) | — |
| 5 | `vendor/serena/src/serena/refactoring/language_strategy.py` | New | +120 (Protocol) | — |
| 6 | `vendor/serena/src/serena/refactoring/rust_strategy.py` | New | +180 | 5 |
| 7 | `vendor/serena/src/serena/refactoring/python_strategy.py` | New | +180 | 5 |
| 8 | `test/e2e/fixtures/calcrs/` (already specced) | New (tree) | +900 Rust + 30 Cargo.toml + 30 tests | — |
| 9 | `test/e2e/fixtures/calcpy/` | New (tree) | +550 Python + 15 pyproject + 30 tests | — |
| 10 | `test/serena/test_language_strategy.py` | New | +150 | 5, 6, 7 |

Stage-1 exit gate: `pytest test/serena/test_language_strategy.py` green. `cargo test --manifest-path test/e2e/fixtures/calcrs/Cargo.toml` green. `pytest test/e2e/fixtures/calcpy` green.

Size: **small** (~2,265 LoC but most are fixtures; logic is ~590 LoC).

### 5.2 Stage 2 (medium): WorkspaceEdit applier + checkpoint + primitive integration

Goal: can apply a real `WorkspaceEdit` and roll it back. No facades yet.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 11 | `vendor/serena/src/serena/code_editor.py` | Modify | +150 (CreateFile/RenameFile, ordering, snippet, version check) | 1, 2 |
| 12 | `vendor/serena/src/serena/refactoring/checkpoints.py` | New | +100 (in-memory LRU + inverse edit) | 11 |
| 13 | `test/serena/test_workspace_edit_applier.py` | New | +300 (syrupy snapshot tests) | 11, 12 |
| 14 | `test/solidlsp/rust/fixtures/refactor/big_heterogeneous.rs` | New | +500 | — |
| 15 | `test/solidlsp/rust/test_rust_integration.py` | New | +200 (not-yet-facade, direct primitive call) | 1, 2, 11 |
| 16 | Lazy-spawn: `vendor/serena/src/serena/refactoring/lsp_pool.py` | New | +100 (multilspy wrapper + registry) | — |
| 17 | Plugin-cache discovery: `vendor/serena/src/serena/refactoring/discovery.py` | New | +80 (pathlib + pydantic + env var) | — |

Stage-2 exit gate: `pytest test/serena/test_workspace_edit_applier.py test/solidlsp/rust/test_rust_integration.py` green. WorkspaceEdit round-trip demonstrated on a synthetic fixture. No facade invoked.

Size: **medium** (~1,430 LoC).

### 5.3 Stage 3 (large): facades + MVP E2E

Goal: §1 statement satisfied.

| # | File | Type | LoC | Depends on |
|---|---|---|---|---|
| 18 | `vendor/serena/src/serena/tools/refactoring_tools.py` | New | +600 (facades) | 6, 7, 11, 12 |
| 19 | Language-neutral "no server-assist" branch (within 18) | — | +80 (inline) | 18 |
| 20 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `fix_imports` | — | Part of 18 (~120 LoC of the 600) | 18 |
| 21 | `vendor/serena/src/serena/tools/refactoring_tools.py` — `rollback_refactor` | — | Part of 18 (~40 LoC) | 12, 18 |
| 22 | `o2-scalpel/.claude-plugin/plugin.json` | New | +20 | — |
| 23 | `o2-scalpel/.mcp.json` | New | +15 | — |
| 24 | `test/e2e/conftest.py` | New | +150 | 22, 23 |
| 25 | `test/e2e/test_calcrs_e2e.py` (E1, E2, E3, E9, E10) | New | +250 | all above |
| 26 | `test/e2e/test_calcpy_e2e.py` (E1-py, E9-py) | New | +200 | all above |
| 27 | `test/e2e/test_rollback.py` (E3 deep-dive) | New | +80 | 25, 26 |

Stage-3 exit gate: `pytest -m e2e` runs all 7 MVP scenarios green (E1, E1-py, E2, E3, E9, E9-py, E10). Package installable as `uvx --from <path>`. Tag as `v0.1.0-mvp`.

Size: **large** (~1,315 LoC, dominated by the facade orchestration in #18).

### 5.4 Dependency graph

```
stage 1:  [1][2][3]  [4][5]→[6]→    [8]
                         [5]→[7]→    [9]
                                    [10]
            ↓
stage 2:  [11]→[12]→[13]
          [14]→[15]
          [16]  [17]
            ↓
stage 3:  [18]→[19][20][21]
          [22][23]→[24]→[25][26][27]
```

Parallelization opportunities (per project CLAUDE.md "Parallel Execution"):
- Within stage 1: files 1–3 independent; 5/6/7 independent after 5 lands; 8/9 independent fixtures.
- Within stage 2: 11/12/13 sequential; 14/15 parallel with 16/17.
- Within stage 3: 22/23 parallel with 18; 25/26 parallel after 18 lands.

CPU-core limit respected: stages 1 and 2 have 5+ independent subtasks; map-reduce with per-file workers is appropriate. Stage 3 serializes on #18 — the 600-LoC facade is one coherent refactor and cannot be parallelized across sub-subagents without conflict.

### 5.5 Total MVP LoC

| Stage | LoC (logic) | LoC (fixtures) | Total |
|---|---|---|---|
| 1 | ~590 | ~1,675 | ~2,265 |
| 2 | ~930 | ~500 | ~1,430 |
| 3 | ~1,315 | 0 | ~1,315 |
| **MVP total** | **~2,835 logic** | **~2,175 fixtures** | **~5,010 LoC** |

Comparison to §3's ~3,950: the delta is the explicit accounting of plugin packaging, discovery, lazy-spawn, and checkpoint modules that the main design folded into "~2,450 LoC + 300 fixtures". The numbers agree once those are unfolded.

### 5.6 Stage-boundary discipline

Each stage tag is a hard boundary. The discipline costs:
- Stage 1 cannot start stage-2 work even if a developer "has spare capacity" before all stage-1 exit gates are green. Reason: stage 2 depends on stage-1 contracts (Protocol shape, fixture content); changing them mid-stage-2 cascades.
- Stage 2 cannot start stage-3 work for the same reason. The facade orchestration depends on the WorkspaceEditApplier's exact interface.
- Inside a stage, parallelism is encouraged (per project CLAUDE.md "Parallel Execution"). Across stages, sequential.

This discipline is the cheapest way to keep §1's falsifiability honest. If we slip and start mixing stage-2 work into stage-1 because "it's all going to be one PR anyway", we lose the gating on Protocol stability and the §3.6 abstraction-percentage argument starts to leak.

### 5.7 What does NOT belong in any MVP stage

For clarity, the following items are deferred from staging entirely (not "wait until stage 3" — they don't appear in stage 3 either):

- Anything from §8's cut list. Rebuilding stage-3 to include `plan_file_split` is a feature reopening, not a stage shift.
- The `o2-scalpel-newplugin` generator, even as a 100-LoC tool. It doesn't gate §1.
- The marketplace publication, the marketplace.json file, marketplace README polish.
- C++/Go/TS strategy bodies (only TS paper-design is required, and that is design work, not code).
- Performance tuning. MVP commits to functional correctness; the §9 resource floor is the acceptance level. Tuning idle-shutdown intervals, optimizing `documentSymbol` query batching, or paging through large `WorkspaceEdit` previews is post-MVP.
- Telemetry / observability beyond the existing `lsp_ops: list[LspOpStat]` already in `RefactorResult`. No metrics endpoint, no log aggregation, no traces beyond the per-scenario JSONL files the E2E driver already writes (those are required for E2E debuggability, hence already in stage 3).

---

## §6 — Test gates for MVP-done

Seven E2E scenarios, each tied to a concrete fixture and a concrete `pytest` invocation.

### 6.1 Rust gates (calcrs fixture)

| Scenario | Command | Pass condition |
|---|---|---|
| E1 | `pytest -m e2e test/e2e/test_calcrs_e2e.py::test_happy_path_split` | Post-state tree matches `expected/post_split/`; `cargo check --workspace` exits 0; 4 module files created, original reduced to <200 LoC with `pub use` chain preserved. |
| E2 | `...::test_dry_run_inspect_commit` | `dry_run=true` returns same `FileChange` list as `dry_run=false`; no filesystem change between the two calls (content-hash of scratch dir unchanged); diagnostics delta reported identically. |
| E3 | `...::test_rollback_after_failure` | Simulate broken `reexport_policy`, assert `applied=false` and `failure.kind="new_errors_post_apply"`; call `rollback_refactor`; assert scratch dir content-hash byte-identical to pre-refactor baseline. |
| E9 | `...::test_semantic_equivalence` | Refactor → `cargo test` output captured → diff against `expected/baseline.txt`; must be byte-identical including ordering and timing elision. |
| E10 | `...::test_rename_symbol_regression` | Existing Serena `rename_symbol` E2E (already passing upstream) passes verbatim against our fork. |

### 6.2 Python gates (calcpy fixture)

| Scenario | Command | Pass condition |
|---|---|---|
| E1-py | `pytest -m e2e test/e2e/test_calcpy_e2e.py::test_happy_path_split` | Post-state tree matches `expected/post_split/`; `pytest` exits 0; ≥3 module files created under `calcpy/` package; `__init__.py` re-exports preserved. |
| E9-py | `...::test_semantic_equivalence` | Refactor → `pytest -p no:cacheprovider --no-header` output captured → diff against `expected/baseline.txt`; must be byte-identical. |

### 6.3 Green-bar definition

All 7 must pass **in a single CI run on a single machine** (not cherry-picked across runs). A single flaky test is not acceptable for the MVP claim. Retries allowed only once per test; two retries = flaky = MVP not done.

### 6.4 `calcpy` fixture outline (not yet authored)

```
test/e2e/fixtures/calcpy/
├── pyproject.toml              # name = "calcpy-fixture", version = "0.0.0"
├── calcpy/
│   └── __init__.py             # ~550 LoC, deliberately monolithic
├── tests/
│   └── test_smoke.py           # ~30 LoC baseline
└── expected/
    ├── post_split/             # expected file tree + contents after E1-py
    └── baseline.txt            # frozen pytest output
```

The `__init__.py` mirrors `calcrs`'s `lib.rs` shape:
- Four implicit clusters: `ast` (AST dataclasses), `errors` (exception types), `parser` (tokenizer + recursive-descent parser), `eval` (tree walker).
- Public API: `run(expr: str) -> Value`, `VERSION: str`.
- Private helpers referenced across clusters.
- One class with ~100 LoC body (`Parser`).
- Intentionally wide `import` chain at top of file.

Author effort: small (~600 LoC total). Zero external deps (no `lark`, no `pyparsing`) to match calcrs's deterministic, dep-free property.

---

## §7 — Marketplace and plugin delivery at MVP

### 7.1 Recommendation: local `uvx --from <path>` at MVP; marketplace at v1.1

The falsifiable MVP (§1) deliberately names `uvx --from <path>` as the distribution step. Rationale:

1. **Marketplace is a publishing decision, not a capability.** Once the plugin installs locally, publishing to `o2alexanderfedin/claude-code-plugins` is metadata (`marketplace.json` entry, git tag, README polish). None of that tests whether the scalpel actually refactors code.
2. **Marketplace couples MVP to external systems.** Claude Code's plugin registry caches, Anthropic's Discover tab, third-party aggregators (claudemarketplaces.com) — MVP should not depend on any of these to demonstrate value.
3. **Marketplace requires a stable version number.** MVP is pre-1.0. Bumping `marketplace.json` on every stage-3 retest is noise.

### 7.2 MVP install flow (documented in README)

```bash
# One-time: clone scalpel locally
git clone --recurse-submodules https://github.com/o2alexanderfedin/o2-scalpel.git ~/dev/o2-scalpel

# Register the plugin with Claude Code
mkdir -p ~/.claude/plugins/o2-scalpel
ln -s ~/dev/o2-scalpel/o2-scalpel/.claude-plugin ~/.claude/plugins/o2-scalpel/.claude-plugin
ln -s ~/dev/o2-scalpel/o2-scalpel/.mcp.json ~/.claude/plugins/o2-scalpel/.mcp.json

# Reload
/reload-plugins
```

The `.mcp.json` runs `uvx --from ~/dev/o2-scalpel/vendor/serena serena-mcp-server --mode scalpel`. No PyPI dependency, no marketplace dependency.

### 7.3 Minimum MVP packaging

| Artifact | Stage | Notes |
|---|---|---|
| `o2-scalpel/.claude-plugin/plugin.json` | MVP | Required by Claude Code to recognize the plugin. |
| `o2-scalpel/.mcp.json` | MVP | Registers the MCP server command. |
| `o2-scalpel/README.md` | MVP | Single-page install + usage. |
| `vendor/serena/` as git submodule | MVP | The binary source. |
| PyPI release of the Serena fork | v1.1 | Can run from git submodule at MVP. |
| `o2-scalpel/hooks/verify-scalpel.sh` | v1.1 | Ops affordance; defer. |
| Marketplace `marketplace.json` | v1.1 | Publishing step. |
| Marketplace `README.md` with install badges | v1.1 | Same. |
| GitHub Actions release workflow | v1.1 | Tag-push → release tarball. |
| Piebald-exclusion CI guard | v1.1 | Blocks v1.1 public release (per Q13 §Open follow-ups); not MVP. |

### 7.4 Why not publish to the marketplace at MVP anyway?

Cost is low (~one afternoon's work) but the risk is that marketplace URL stability becomes a constraint before the API is stable. If we publish at MVP and then rename a facade in v1.1, marketplace consumers (who auto-update) hit a broken contract. Publishing at v1.1 with a deliberate `v0.1.0` tag and documented API gives a one-version grace period between "can install" and "safe to auto-update".

---

## §8 — Cut list (things the design mentions that should be explicitly OUT of MVP)

Named, so nobody relitigates during implementation.

| Feature | Design reference | MVP-cut rationale |
|---|---|---|
| `workspace/symbol` cross-crate globbing in `fix_imports(files=["**"])` | Facade §3.5 | MVP enumerates files explicitly. The `**` glob is a convenience; walking the filesystem from the user input is sufficient. |
| C/C++ strategy with shared `clangd --index-file=` | Two-process Q12 | Rust + Python only at MVP. C/C++ doesn't block §1. |
| Go strategy using `gopls -remote=auto` | Two-process Q12 | Same. |
| TypeScript strategy | Main design OQ #7 | Paper-only at MVP per §2.4; no code. |
| Third-party `LanguageStrategy` entry-points | Main design OQ #9 | Zero demand; static dict suffices. |
| Persistent checkpoints (`.serena/checkpoints/`) | Main design §1.4 | In-memory LRU only at MVP; lose checkpoints on crash (acceptable). |
| `changeAnnotations` with UI confirmation | Main design Gap 6 | MVP rejects annotated edits with a warning. |
| `$/progress` parsing beyond "indexing done" | Main design §1.3 | Progress bars, percent-complete telemetry — not needed. MVP uses a binary ready/not-ready signal. |
| Server-extension whitelist calls (`experimental/ssr`, `runFlycheck`, etc.) | Main design §4, Appendix A | Facades never call them at MVP. Whitelist can be empty in each strategy. |
| `execute_command` primitive MCP tool | Main design §2.4 | v1.1. MVP doesn't expose primitives at all. |
| `list_code_actions`, `resolve_code_action`, `apply_code_action` primitives | Main design §2.1–2.3 | Same. Escape hatch deferred. |
| `plan_file_split` | Main design §3.1 | v1.1. LLM computes groups from CC's `documentSymbol`. |
| `extract_symbols_to_module`, `move_inline_module_to_file` | Main design §3.3, §3.4 | v1.1. `split_file_by_symbols` covers the §1 claim. |
| Multi-crate / multi-package fixture (E5) | Main design §Testing | v1.1. Single-package fixtures at MVP. |
| Concurrent-edit race (E4) | Main design §Testing | v1.1. `ContentModified` retry exists in MVP code; the explicit E2E can wait. |
| Cold-start timing assertion (E7) | Main design §Testing | v1.1. |
| Crash-recovery (E8) | Main design §Testing | v1.1. |
| Watchdog / filesystem watcher on plugin cache | Q10 | Explicitly rejected at MVP per resolution doc. Stays rejected. |
| `scalpel_reload_plugins` MCP tool | Q10 | v1.1. MVP re-scans on server start only. |
| `O2_SCALPEL_DISABLE_LANGS` opt-out | Q12 | v1.1. MVP on 16+ GB laptop; low-memory profile is post-MVP. |
| `O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS` tuning | Q12 | v1.1. Default 600s is fine. |
| `config.toml` config-file override | Q10 | v1.1. Env var only at MVP. |
| `o2-scalpel-newplugin` generator | Q14 | v2+. Zero MVP value. |
| Reference LSP-config plugins (`rust-analyzer-reference`, `clangd-reference`) | Q14 | v2+. |
| Boostvolt fork under neutral name | Q13 | v2+. MVP uses user's existing CC LSP plugins. |
| Piebald clean-room re-author | Q13 | v2+. |
| Anthropic feature-request filing ("plugin-list API") | Q10 §Open follow-ups | Can be filed anytime; not MVP code. Parallel admin task. |
| Second `LanguageStrategy` paper design for TS | Main design OQ #7 | Required as review gate before stage-3 facade merge; no shipped code. |
| Upstream PR to `oraios/serena` for WorkspaceEdit applier upgrades | Main design OQ #6 | After MVP stabilizes. |
| Product rename (package `src/serena/` → `src/o2_scalpel/`) | Main design OQ #8 | After MVP. |

### 8.1 Things NOT in the design that stay cut anyway

- No within-function extractions (`extract_function`, `extract_variable`). Main design §Non-Goals already excludes them.
- No `typeHierarchy`. Same.
- No streaming MCP tool results. Same.
- No writing new rust-analyzer assists. Same.

---

## §9 — Resource budget

### 9.1 MVP floor commitment

**MVP targets a 16 GB dev laptop with both LSPs spawned (CC's built-in rust-analyzer + scalpel's rust-analyzer), holding the `calcrs` fixture (small) open.**

Reasoning:
- `calcrs` is a single-crate fixture. rust-analyzer's footprint on it is ~500 MB per instance, not the 4–8 GB the 227-crate `hupyy` workspace warned about.
- `calcpy` is tiny (~600 LoC, zero deps). Pyright footprint is ~300 MB per instance.
- 16 GB baseline leaves ample headroom even with 2× rust-analyzer (1 GB) + 2× pyright (600 MB) + the MCP server itself (~300 MB) + Claude Code + OS.

### 9.2 MVP does NOT commit to

- Running on a 227-crate workspace at MVP. Large-workspace support is v1.1 at the earliest, gated by explicit opt-in flag testing.
- Running on 8 GB machines. Not a supported floor. Document in README.
- Running on CI runners with <16 GB. MVP E2E on CI runs on standard GitHub-hosted runners (7 GB today, 16 GB for `ubuntu-latest-4-cores`). If the smaller runner fails, use the 4-core variant; do not chase 7 GB viability.

### 9.3 Memory breakdown on the MVP floor (16 GB dev laptop)

| Component | MVP | v1.1 large-workspace |
|---|---|---|
| OS + Claude Code + VS Code | ~3 GB | ~3 GB |
| CC's built-in rust-analyzer on `calcrs` | ~500 MB | ~4–8 GB on real workspace |
| Scalpel's rust-analyzer on `calcrs` | ~500 MB | ~4–8 GB — **this is the pain point** |
| CC's built-in pyright | ~300 MB | ~300 MB |
| Scalpel's pyright | ~300 MB | ~300 MB |
| Scalpel MCP server Python process | ~300 MB | ~300 MB |
| Test harness, fixtures | <100 MB | <100 MB |
| **Total** | **~5.0 GB** | **~16–20 GB** |

MVP comfortable. v1.1 is where the `O2_SCALPEL_DISABLE_LANGS=rust` opt-out starts earning its keep.

### 9.4 Disk budget

- `vendor/serena/` clone: ~200 MB.
- `rust-analyzer` binary (downloaded by `DependencyProvider`): ~40 MB.
- Pyright install (npm): ~200 MB.
- Scalpel's scratch `cargo.targetDir` override: ~2 GB on `calcrs` (negligible compared to a real workspace's 10–20 GB).
- Checkpoint storage: in-memory only at MVP; 0 disk.

Total disk: ~2.5 GB. Fine on any dev laptop.

### 9.5 Time budget (wall-clock, not effort)

Per project CLAUDE.md, do not estimate time. But the E2E gates have observable wall-clock floors we must design around:

- rust-analyzer cold start on `calcrs`: observable, fits in the E7 scenario's 60s cap.
- pyright cold start on `calcpy`: sub-second (empirically, Pyright has no persistent index).
- Full MVP E2E run (7 scenarios × ~10–60s each): ~3–7 min on the CI runner. Acceptable for a `nightly` marker; `pytest -m e2e` runs on-demand not per-commit.

---

## §10 — Definition of "done" for MVP

Concrete. Every item measurable.

### 10.1 Code

- [ ] `vendor/serena` fork contains all stage-1, stage-2, stage-3 changes.
- [ ] `o2-scalpel/.claude-plugin/plugin.json` + `o2-scalpel/.mcp.json` exist and validate against Claude Code's plugin schema.
- [ ] `test/e2e/fixtures/calcrs/` and `test/e2e/fixtures/calcpy/` exist with `baseline.txt` captured from pre-refactor test runs.
- [ ] `PythonStrategy` and `RustStrategy` registered in `serena.refactoring.__init__`.
- [ ] `LanguageStrategy` Protocol reviewed against TypeScript paper design; no Rust-specific method names or docstrings.
- [ ] `src/serena/tools/refactoring_tools.py` contains `split_file_by_symbols`, `fix_imports`, `rollback_refactor`. No other facades (no `plan_file_split`, no `extract_symbols_to_module`, no `move_inline_module_to_file`).

### 10.2 Tests (all green in one CI run)

- [ ] `pytest test/serena/` — all unit tests pass.
- [ ] `pytest test/solidlsp/rust/` — integration tests pass.
- [ ] `pytest -m e2e test/e2e/test_calcrs_e2e.py::{test_happy_path_split,test_dry_run_inspect_commit,test_rollback_after_failure,test_semantic_equivalence,test_rename_symbol_regression}` — 5 Rust scenarios green.
- [ ] `pytest -m e2e test/e2e/test_calcpy_e2e.py::{test_happy_path_split,test_semantic_equivalence}` — 2 Python scenarios green.
- [ ] No flakes: each scenario passes in a single retry or fewer.
- [ ] `cargo test --manifest-path test/e2e/fixtures/calcrs/Cargo.toml` green on the pristine fixture (regression guard).
- [ ] `pytest test/e2e/fixtures/calcpy` green on the pristine fixture.

### 10.3 Documentation

- [ ] `README.md` contains a copy-pasteable "Install locally" section for the `uvx --from <path>` flow.
- [ ] `docs/design/mvp/` contains this report plus companion specialist outputs.
- [ ] `CHANGELOG.md` has an entry for `v0.1.0-mvp`.
- [ ] The two Python fixture files (`calcpy/calcpy/__init__.py`, `tests/test_smoke.py`) have a top-of-file docstring declaring "synthetic fixture for o2.scalpel MVP E2E — do not import in production".

### 10.4 Install

- [ ] From a clean checkout on a 16 GB dev laptop, a user can run:
  1. `git clone --recurse-submodules …`
  2. `ln -s …` (as documented in §7.2).
  3. `/reload-plugins` in Claude Code.
  4. Open `calcrs/` in a Claude Code session.
  5. Invoke `mcp__o2-scalpel__split_file_by_symbols` and observe the refactor.
- [ ] Install succeeds without PyPI, without the marketplace, without a network connection other than the initial git clone.
- [ ] `uvx --from <path> serena-mcp-server --mode scalpel --version` prints a version string.

### 10.5 Non-gates

Explicitly NOT blocking MVP:
- Marketplace publication.
- PyPI release.
- `calcrs`/`calcpy` being available as library packages (they stay test-fixture-only).
- Any C++, Go, TypeScript, Java, or other-language functionality.
- Documentation of any facade we didn't ship (plan_file_split, etc. — v1.1 docs with v1.1 code).
- Big-workspace (227-crate) viability.
- Idle-shutdown tuning.
- Persistent checkpoints.
- CI guard for vendored Piebald exclusion (that blocks v1.1, not MVP).

### 10.6 Tag

Upon all checklist items green, tag `v0.1.0-mvp`. Branch: `develop` → `main` merge via git-flow release (per project CLAUDE.md git workflow). No PR (solo development). Push tag; announce in a separate post-MVP step.

---

## §11 — Falsifiable MVP statement (re-stated for orchestrator)

> **Scalpel MVP is done when `split_file_by_symbols` + `fix_imports` + `rollback_refactor` successfully refactor `calcrs/src/lib.rs` (Rust fixture) and `calcpy/calcpy/__init__.py` (Python fixture) into ≥3 modules each with `cargo test` / `pytest` byte-identical output to the pre-refactor baseline, driven through a stdio MCP client (`pytest -m e2e`) against a scalpel MCP server installed via `uvx --from <local-path>`.**

Not done until both languages pass. Not done if the marketplace is published but E9-py fails. Not done if E1 passes once in three runs. Not done if the install requires PyPI.

Everything else in the main design — primitives exposed as MCP tools, `plan_file_split`, `extract_symbols_to_module`, persistent checkpoints, the marketplace, the plugin-generator, the TypeScript strategy, the C/C++ strategy, `scalpel_reload_plugins`, the boostvolt fork, Piebald licensing followups — is v1.1 or later. This report enumerates the cuts so nobody relitigates them when stage 3 starts.

---

## §12 — Open items for the orchestrator's synthesis

These are deferred to the next synthesis round, not resolved here:

1. **Pyright vs. pylsp for the Python MVP.** Pyright is the Serena default and has richer inference; pylsp has a more complete `codeAction` surface. If pyright's code-action surface is too thin at MVP (§4.3 residual risk), pylsp may be the better MVP commitment with a note to evaluate pyright at v1.1. Flag for a hands-on spike during stage 1.
2. **Whether `calcpy` should be a package (`calcpy/__init__.py` + submodules) or a single module (`calcpy.py`).** §6.4 assumes package because it's the richer test shape. A single-module fixture would bias the Python strategy toward filesystem-trivial cases. Lock this before stage-1 fixture authoring.
3. **Whether the facade's "no-server-assist" branch is its own module or inline in `split_file_by_symbols`.** §3.4 argues for a named, visible path. Companion specialists should confirm this design ergonomic — if they disagree, one of us is wrong.
4. **Whether `rollback_refactor` is a tool or an automatic behavior.** §2.2 assumes tool (LLM-callable). An alternative: rollback happens automatically on any `failure` and the LLM never explicitly calls it. The main design chose tool; confirm that for MVP.
5. **`calcrs` E9 baseline file's line-ending handling across Linux/macOS CI.** `cargo test` output has timing fields that need eliding; the elision regex should be reviewed. Not blocking for staging, but surface it before stage 3 to avoid last-minute E9 flakes.

---

## §13 — Summary tables

### 13.1 MVP vs. deferred, at a glance

| Category | MVP items | Deferred items |
|---|---|---|
| Primitives (LSP layer) | request_code_actions, resolve_code_action, applyEdit handler, $/progress gate, WorkspaceEdit applier (TextDocumentEdit, CreateFile, RenameFile), atomic apply, in-mem checkpoint | execute_command, DeleteFile, changeAnnotations, persistent checkpoints |
| Primitive MCP tools | none | list_code_actions, resolve_code_action, apply_code_action, execute_command |
| Facade MCP tools | split_file_by_symbols, fix_imports, rollback_refactor | plan_file_split, extract_symbols_to_module, move_inline_module_to_file |
| Strategies | RustStrategy, PythonStrategy | TypeScriptStrategy (paper-only at MVP), GoStrategy, C/C++ Strategy, third-party strategies |
| Fixtures | calcrs, calcpy, big_heterogeneous.rs | cross_visibility, with_macros, inline_modules, mod_rs_swap, multi-crate |
| E2E | E1, E1-py, E2, E3, E9, E9-py, E10 | E4, E5, E6, E7, E8 |
| Discovery | pathlib glob, env-var override, platformdirs, pydantic schema | config.toml override, scalpel_reload_plugins, filesystem watch (never) |
| Lazy spawn | first-use spawn, per-(lang, root) registry | is_alive probe, idle shutdown, pool semantics |
| Packaging | .mcp.json, plugin.json, local uvx --from install | PyPI release, marketplace.json, verify-scalpel.sh, newplugin generator, reference LSP plugins |

### 13.2 LoC rollup

| Bucket | LoC |
|---|---|
| MVP logic (Rust-agnostic) | ~2,095 |
| MVP logic (Rust-specific) | ~185 |
| MVP logic (Python-specific) | ~260 (incl. no-server-assist branch prorated) |
| MVP test logic | ~1,180 |
| MVP fixture content | ~2,175 |
| **MVP grand total** | **~5,895** |

(The exact breakdown in §3 and §5 sums to ~5,010 because §3 excluded test logic from its "baseline"; both are correct for their scope.)

### 13.3 Staging recap

| Stage | Size | Exit gate | Tag |
|---|---|---|---|
| 1 | small | Strategy Protocol locked; fixtures compile/test. | `mvp-stage-1` |
| 2 | medium | WorkspaceEdit applier round-trips; checkpoint round-trips. | `mvp-stage-2` |
| 3 | large | 7 E2E scenarios green. §1 statement satisfied. | `v0.1.0-mvp` |

---

## §14 — Closing note

The most defensible form of MVP is one that commits to a property (dual-language abstraction holds) rather than a volume (N facades × M languages = N·M features). This report's triage optimizes for the property: ship the three facades that prove split-and-rollback, on the two languages that prove the strategy seam, against the one distribution path that proves installability — and leave every other feature the main design contemplated for after the property is green in CI. The Rust-only alternative ships sooner but risks a v1.1 rewrite when Python lands; given that Python is now top priority, that risk is no longer acceptable.

End of report.
