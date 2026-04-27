# Coordinator Outline — o2-scalpel "What's Left" Report

**Date:** 2026-04-26
**Sources:** A-plans.md, B-design.md, C-code.md, D-debt.md (all read in full).

---

## Reconciliation notes

1. **Stage 3 T6/T7/T9 consistency** (A§3 vs auto-memory): A confirms T6/T7/T9 fully landed with submodule SHAs `4ae3d99e` (T6+T7) and parent `73be3bd` (T9). C§3 corroborates 23 specialty facades + E2E coverage in test/e2e/. **No contradiction; auto-memory and code agree.**

2. **P5a outcome reversal — UNRESOLVED** (A§4): `docs/superpowers/plans/spike-results/P5a.md` flipped from "outcome C — DROP pylsp-mypy" to "outcome B — SHIP with documented warning" (stale_rate 8.33%→0.00%; p95 8.011s→2.668s). B§2 claims "all Q1–Q4 resolutions documented" but does NOT note the spike-result delta. C and D didn't surface any mypy pin in code. **Conflict: spike-result file vs. PROGRESS.md decision log §70 vs. MVP cut freeze.** → Bucket F.

3. **Capabilities-implemented vs. integration-test-surface tension** (A§2 vs C§Summary): C reports 14/15 domains fully implemented + 0 NotImplementedError in production scalpel code. A reports Stage 1H delivered ~9% of the planned 9,460 LoC (810/9,460), routing 28 tests + 17 RA companion crates + 3 calcpy sub-fixtures to v0.2.0 continuation. **Both true:** capabilities work end-to-end via spike + 40 E2E tests, but the *fixture+integration-test surface* the design promised (~70 sub-tests across 31 modules) is largely deferred. → Bucket A as the single largest honest gap.

4. **Skipped-test headline reconciliation** (D§1 vs auto-memory): D counts ~150+ skipped/xfail across the entire vendor/serena suite; ~110 are tool/env (not debt), ~25 are LSP-reliability flakes (issue #1040 cluster), ~20 are WIP/fixture sequencing. Auto-memory's "9 e2e skips + 6 inspect.getsource flakes" describes *only* the scalpel-owned subset (E2E + Stage 2A/3 spike). **Both correct at different scopes.** Authoritative headline: **scalpel-owned debt = 6 inspect.getsource flakes + 1 documented E1-py flake (gap #8) + ~10 type:ignores; ecosystem-owned debt (solidlsp upstream) = 25 LSP-reliability xfails under #1040.**

5. **inspect.getsource flakes** (D§2, C§Code Quality): D has the 6 file:lines (Stage 2A/3 introspection of `cls.apply` source for safety-call visibility check); C says "no production stubs". Both are simultaneously true — these are *test-side* flakes, not feature gaps. → Bucket E.

6. **Stage 2B "9 MVP scenarios" naming gap** (C§Partial): Plan named 9 MVP E2E scenarios; codebase has ~7 MVP-labeled + 5 Stage 3 (E13–E16). All 40 E2E tests pass with 0 xfail/skip in test/e2e/. **Cosmetic-naming gap, not behavioral.** → Bucket A (low size).

7. **Marketplace + v2+ language strategies** (A§7, B§4): A and B fully agree these are deferred-by-design (v1.1 marketplace; v2+ TS/Go/clangd/Java). → Buckets C and D, not "missing features."

---

## Headline state (one paragraph)

o2-scalpel is **functionally complete through v0.3.0**: Stages 1A–1J + 2A + 2B + Stage 3 (v0.2.0) + facade-application gap (v0.3.0) all landed and tagged; 37 MCP tools across 14/15 capability domains live (8 primitives + 6 Stage 2A facades + 23 Stage 3 specialty facades); 117 test files / ~694 test functions with no production NotImplementedError and only 6 acknowledged scalpel-owned test flakes (`inspect.getsource(cls.apply)` pattern in Stage 2A/3 spikes). The biggest *honest* gap is **Stage 1H continuation** — 28 deferred integration tests + 17 RA companion crates + 3 calcpy sub-fixtures, representing ~91% of the originally planned fixture-LoC, all explicitly routed to v0.2.0 (A§2). The biggest *unresolved decision* is **P5a outcome reversal** (DROP→SHIP mypy) — the spike-result file disagrees with PROGRESS.md and the MVP cut freeze, and no code/plan reflects the new claim (A§4). Marketplace publication and TypeScript/Go/Java/C++ strategies are deferred-by-design (v1.1 / v2+) and live in Buckets C/D, not the gap list proper.

---

## Bucket A — Honest MVP gaps

1. **Stage 1H continuation: 28 integration tests + 17 RA companion crates + 3 calcpy sub-fixtures**
   - Sources: A§2 (status table + scope-reduction rationale), C§11 (3 smokes only)
   - Evidence: `stage-1h-results/PROGRESS.md:32–33,73–81`; v0.1.0 delivered 810/9,460 LoC (~9%); routed T2, T4–T6, T8–T11 to v0.2.0
   - Size: **large** (~8,650 LoC fixtures + tests outstanding)
   - Blocks: depth-of-coverage claims for Rust assist families and Python multi-LSP merge; nothing structurally blocked

2. **Stage 2B E2E scenario naming/count alignment**
   - Sources: C§Partial-1 (Stage 2B), A§1 (plan-ready)
   - Evidence: plan promised "9 MVP scenarios"; code has ~7 MVP-labeled + 5 Stage 3; all 40 E2E pass, 0 xfail
   - Size: **small** (relabel + cross-reference plan to file names)
   - Blocks: none

---

## Bucket B — v0.2.0 follow-ups

1. **basedpyright dynamic-capability gap**
   - Sources: A§5 (stage-1h-results/PROGRESS.md:83–89), D§5 (no scalpel TODOs but documented in stage ledger)
   - Evidence: `stage-1h-results/PROGRESS.md:83–89`
   - Size: **medium**
   - Blocks: full Python multi-server determinism

2. **rust-analyzer position validation**
   - Sources: A§5 (stage-1h-results/PROGRESS.md:83–89)
   - Evidence: same ledger, line 84
   - Size: **medium**
   - Blocks: edge-case correctness for cursor-positioned assists

3. **Multi-server async wrapping**
   - Sources: A§5 (stage-1h-results/PROGRESS.md:83–89)
   - Evidence: same ledger, line 86
   - Size: **medium**
   - Blocks: parallelism in multi-LSP merge path

4. **CARGO_BUILD_RUSTC workaround**
   - Sources: A§5 (stage-1h-results/PROGRESS.md:83–89)
   - Evidence: same ledger, line 88
   - Size: **small**
   - Blocks: clean Rust-host build environment claim

5. **E1-py flake (gap #8)**
   - Sources: D§7 (commit `2ee21f8`), D§Recommendations-3
   - Evidence: chore commit "document E1-py flake (gap #8) for v0.2.0 backlog"
   - Size: **small**
   - Blocks: 100% E2E green claim under repeat runs

6. **Headline calcpy monolith (~950 LoC)**
   - Sources: A§6 (forward references)
   - Evidence: `stage-1h-results/PROGRESS.md:73–81`
   - Size: **medium** (~950 LoC fixture)
   - Blocks: full Python facade exercise surface

---

## Bucket C — v1.1 / marketplace

1. **Marketplace publication at `o2alexanderfedin/claude-code-plugins`**
   - Sources: A§5 (mvp-execution-index.md:7), B§4 (Q11 resolution)
   - Evidence: `docs/design/open-questions-resolution.md §Q11`; multi-plugin repo layout finalized, distribution channel deferred
   - Size: **medium**
   - Blocks: discoverability beyond `uvx --from <local-path>`

2. **Persistent disk checkpoints durability**
   - Sources: A§5 (stage-1b plan), B§4 (MVP scope §4.7 #8)
   - Evidence: MVP uses LRU-only; durability across sessions deferred
   - Size: **medium**
   - Blocks: cross-session rollback recovery

3. **Plugin reload tool / `scalpel_reload_plugins`**
   - Sources: A§5 (stage-1c plan), B§7 (Q10 resolution)
   - Evidence: `open-questions-resolution.md §Q10` — refresh via `scalpel_reload_plugins` named, not implemented
   - Size: **small**
   - Blocks: hot plugin updates

4. **Rust + clippy multi-server scenario**
   - Sources: A§5 (stage-1d plan)
   - Evidence: only Python multi-LSP at MVP per plan
   - Size: **medium**
   - Blocks: cross-language multi-LSP parity

5. **Engine config knob**
   - Sources: A§Summary
   - Evidence: project-memory note in v0.2.0 critical-path
   - Size: **small**

6. **Per-annotation confirm-handle (`scalpel_confirm_annotations`)**
   - Sources: B§4 (q4-changeannotations-auto-accept.md §6.3)
   - Evidence: optional override when LLM passes `confirmation_mode="manual"`
   - Size: **small**
   - Blocks: opt-in manual-review workflows

7. **3 Python facades (convert_to_async, annotate_return_type, convert_from_relative_imports)**
   - Sources: A§Summary
   - Evidence: project-memory note in v0.2.0 Stage 3 facades
   - Size: **medium** (3 facades)

8. **PEP 695/701/654 fixture variants**
   - Sources: A§5 (stage-1h plan line 81)
   - Evidence: deferred per scope-report §4.7 row 22
   - Size: **small**

---

## Bucket D — v2+ language strategies

1. **TypeScript / vtsls strategy**
   - Sources: A§7, B§5.3
   - Evidence: `mvp-execution-index.md:96`; design report §5 paper-designed
   - Size: **large** (full strategy + adapter + LSP wiring)
   - Blocks: TS coverage; nothing internal

2. **Go / gopls strategy** (note watch-item: gopls daemon reuse golang/go#78668)
   - Sources: A§7, B§4 (watch-item)
   - Evidence: per-language mitigation: daemon reuse vs. fresh spawn
   - Size: **large**

3. **C / C++ / clangd strategy**
   - Sources: A§7, B§5.3
   - Evidence: `mvp-execution-index.md:96`
   - Size: **large**

4. **Java / jdtls strategy**
   - Sources: A§7, B§5.3
   - Evidence: `mvp-execution-index.md:96`
   - Size: **large**

5. **Kotlin / Ada / Svelte / Vue and other long-tail strategies**
   - Sources: B§5.3
   - Evidence: all via `o2-scalpel-newplugin` generator post-v1.0
   - Size: **medium each** (generator already ships, so per-strategy effort is reduced)

---

## Bucket E — Tech debt (live)

1. **6 `inspect.getsource(cls.apply)` flakes in Stage 2A/3 spikes**
   - Sources: D§2 (file:line table), C§Code Quality (no prod stubs)
   - Evidence: `test_stage_3_t1_rust_wave_a.py:374`, `t2_rust_wave_b.py:201`, `t3_rust_wave_c.py:247`, `t4_python_wave_a.py:181`, `t5_python_wave_b.py:261`, `test_stage_2a_t9_registry_smoke.py:63`; root cause hypothesis: safety-call injection / decorator stacking / bytecode mismatch (`scalpel_facades.py:1002` confirms intentional pattern)
   - Size: **small** (single-cause investigation — likely 1 fix covers all 6)
   - Blocks: deterministic spike runs

2. **~10 type:ignore suppressions across 5 scalpel files**
   - Sources: D§4
   - Evidence: scalpel_primitives.py:530, scalpel_facades.py (2 indirect), symbol_tools.py:232/306/311, tools_base.py:307
   - Size: **small**
   - Blocks: full Pyright zero-error claim (Stage 1H Pyright pass scheduled per memory)

3. **CI workflow exclusions: Erlang LS install commented out, Swift GHA install conflicts**
   - Sources: D§6
   - Evidence: `.github/workflows/pytest.yml:101–114, 154–157`
   - Size: **medium** per language (upstream toolchain debt)
   - Blocks: nothing; documented workarounds in place

4. **Issue #1040 — systemic LSP-reliability xfails (10+ test references across F#, Swift, Nix, TypeScript)**
   - Sources: D§1.B (~25 hits), D§Recommendations-1
   - Evidence: 10+ test comments cross-reference #1040 (upstream solidlsp issue, not scalpel-owned)
   - Size: **large** (root-cause investigation across multiple LSP servers)
   - Blocks: nothing scalpel-owned but contaminates green-CI signal → see Bucket H

---

## Bucket F — Decisions to reconcile

1. **P5a outcome reversal: DROP pylsp-mypy (C) → SHIP with documented warning (B)**
   - Sources: A§4 (P5a.md delta), B§2 (claims all resolutions cross-referenced — silent on the reversal), absent in C/D
   - Evidence: `docs/superpowers/plans/spike-results/P5a.md` lines 6–9 show stale_rate 8.33%→0.00%; p95 8.011s→2.668s; outcome flipped. Disagrees with PROGRESS.md decision log §70 ("P5a → C — drop pylsp-mypy") and the MVP cut freeze. Code has no mypy pin per D's grep. Likely unsynchronized manual edit of spike-result.
   - Size: **small** (decision call + doc reconciliation; potentially small code change to enable mypy)
   - Blocks: any future "ship mypy by default" plan; Stage 2A/2B test definition

2. **Stage 2B "9 MVP scenarios" naming/count vs. shipped E13+ labels**
   - Sources: C§Partial-1
   - Evidence: plan promised 9 MVP-labeled scenarios; codebase has ~7 MVP + 5 Stage 3 (E13–E16); all pass
   - Size: **small** (label/cross-ref)
   - Blocks: none (also in Bucket A)

---

## Bucket G — Out of scope by design (informational, NOT a gap list)

- `experimental/onEnter` LSP method — explicit-block, MVP scope §4.3 #2 (B§7)
- Filesystem watcher on plugin cache — explicit-reject, OQ Q10 (B§7)
- Within-function extractions in v1 — primitive-only at MVP (B§7)
- `typeHierarchy` — non-goal (B§7)
- Writing new rust-analyzer assists upstream — non-goal (B§7)
- Streaming LSP ops / async tool apply — non-goal, status quo synchronous (B§7)
- Native IDE integrations (VSCode, IntelliJ) — v2+, MCP-only at MVP (B§7)
- `viewHir`/`viewMir`/`viewCrateGraph`/`viewSyntaxTree`/`viewFileText`/`viewRecursiveMemoryLayout`/`getFailedObligations`/`interpretFunction` — reachable via primitive escape hatch only (B§3)
- Test Explorer family (7 rust-analyzer methods) — v1.1 deferral (B§3)
- Bulk LSP-config plugins — explicitly rejected in favour of `o2-scalpel-newplugin` generator (B§2 Q14)

---

## Bucket H — Cross-cutting risks

1. **LSP issue #1040 systemic flakiness contaminates green-CI signal**
   - Sources: D§1.B, D§Recommendations-1
   - Evidence: 10+ test comments across F# / Swift / Nix / TypeScript / Rust tests cite #1040; ecosystem-owned, not scalpel-owned, but degrades trust in CI passes
   - Mitigation: aggregate root-cause investigation; consider quarantine-tier separation in pytest config

2. **Anthropic native LSP-write integration is the deprecation trigger**
   - Sources: B§3 (architectural promises deferred)
   - Evidence: design cites `anthropics/claude-code#24249, #1315, #32502`; horizon 6–18 months
   - Mitigation: optimize for clean handoff path; no immediate action

3. **`lspee` multiplexer maturity (pre-1.0 today)**
   - Sources: B§4 (watch-item)
   - Evidence: revisit two-process problem if `lspee` reaches 1.0 + test suite
   - Mitigation: watch-only; Q12 resolution mitigations already in place

4. **gopls daemon reuse upstream (golang/go#78668)**
   - Sources: B§4 (watch-item)
   - Evidence: Go strategy degrades to per-workspace path until upstream closes
   - Mitigation: tracked; Go strategy is v2+ anyway

5. **P5a unsynchronized manual edits risk silent decision drift**
   - Sources: A§4
   - Evidence: spike-result outcome flipped without ledger or code update
   - Mitigation: governance fix — require coupled change to PROGRESS.md decision log when spike outcomes shift

6. **Capability-vs-test-surface tension** (~9% Stage 1H delivered): production code is solid but coverage breadth from the original design report's 31-module / 70-sub-test promise is unmet
   - Sources: A§2, C§11
   - Mitigation: Bucket A item 1 (Stage 1H continuation) directly addresses this

---

## Recommended sequencing (top-of-mind for synthesis)

If the project picks up tomorrow, the rational order is:

1. **Resolve Bucket F-1 (P5a mypy decision) first** — small effort, unblocks Stage 2A/2B test definitions and prevents the reversal from contaminating any future spike. Pure docs/config call; no code change unless decision is "ship mypy."
2. **Tackle Bucket E-1 (6 inspect.getsource flakes)** — single-cause investigation; one fix likely clears all 6 and restores spike-suite determinism. Quick win, small size.
3. **Execute Bucket B-1..B-6 (v0.2.0 follow-ups)** — already named, scoped, and routed; clears the v0.2.0 backlog as a unit. Most are small/medium.
4. **Land Bucket A-1 (Stage 1H continuation)** — large, but the only structural breadth gap; ~8,650 LoC fixtures + 28 tests + 17 RA crates + 3 calcpy sub-fixtures. Schedule as a dedicated milestone after v0.2.0 follow-ups settle.
5. **Bucket C (v1.1 marketplace + persistent checkpoints + Rust+clippy multi-server)** — coherent v1.1 milestone after Stage 1H lands.
6. **Bucket D (v2+ language strategies)** — TS/Go first (highest user demand per design); generator already ships, so each is incremental.
7. **Bucket H-1 (#1040 root cause)** — schedule as ecosystem investigation in parallel with v1.1; not on the scalpel critical path.

**Rationale:** decisions before code; quick determinism wins before scope expansion; honest breadth gap (Stage 1H) before new milestone breadth (v1.1, v2+); ecosystem risks tracked but never block scalpel-owned forward progress.
