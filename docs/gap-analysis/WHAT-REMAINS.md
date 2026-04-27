# o2-scalpel — What's Left to Do

> Final report from multi-agent gap analysis (4 researchers + coordinator + pair synthesis)
> Source of truth hierarchy: implemented code > passing tests > planning docs > design intent
> Date: 2026-04-26

---

## TL;DR

o2-scalpel is functionally complete through **v0.3.0**. Every MVP-cut stage (Phase 0 + Stages 1A–1J + 2A–2B) plus post-MVP Stage 3 (v0.2.0) plus the facade-application gap closure (v0.3.0) is landed and tagged: **37 MCP tools** across 14/15 capability domains live (8 always-on primitives + 6 Stage 2A facades + 23 Stage 3 specialty facades), 117 test files / ~694 test functions, no production `NotImplementedError`, and 40/40 E2E tests passing with zero skip/xfail in the e2e suite (C§Summary, C§11). Memory milestones tracked: `v0.1.0-mvp`, `v0.2.0-critical-path-complete`, `v0.2.0-stage-3-complete`, `v0.3.0-facade-application-complete`.

The biggest items still outstanding, in order of salience: (1) a **decision-to-reconcile** — `P5a.md` flipped from "DROP pylsp-mypy" to "SHIP with documented warning" without updating PROGRESS.md or the MVP cut freeze (A§4); (2) **live tech debt** — 6 `inspect.getsource(cls.apply)` flakes in Stage 2A/3 spikes (D§2), 1 documented E1-py flake (D§7), ~10 `# type: ignore` density (D§4), and CI workarounds for Erlang/Swift (D§6); (3) **honest MVP gap** — Stage 1H delivered ~9% of its planned fixture+integration-test surface (810/9,460 LoC), with 28 tests + 17 RA companion crates + 3 calcpy sub-fixtures explicitly routed to v0.2.0 continuation (A§2); (4) **post-MVP roadmap** — v1.1 marketplace + persistent checkpoints + Rust+clippy multi-server, then v2+ TypeScript / Go / C / C++ / Java strategies via the existing `o2-scalpel-newplugin` generator (A§7, B§5) (plus four watch-items: `lspee` 1.0 maturity, `gopls daemon` reuse, Anthropic native LSP-write, plugin-list API).

---

## State of the union

What is true today, drawn from the code-state audit (C) and corroborated by planning ledgers (A):

| Domain | Status | Evidence |
|---|---|---|
| Stage 1A — LSP primitives | shipped | tag `stage-1a-lsp-primitives-complete` (A§1) |
| Stage 1B — Applier + Checkpoint/Transaction store | shipped | tag `stage-1b-…-complete`; 13 spike tests pass (C§4) |
| Stage 1C — LSP pool + discovery | shipped | tag `stage-1c-lsp-pool-discovery-complete`; 9 spikes pass (C§5) |
| Stage 1D — Multi-server merge (4 invariants) | shipped | tag `stage-1d-multi-server-merge-complete`; 12 spikes pass (C§6) |
| Stage 1E — RustStrategy + PythonStrategy + 3 LSP adapters + Rope bridge | shipped | tag `stage-1e-python-strategies-complete`; 9 spikes (5 env-skip) (C§7) |
| Stage 1F — Capability catalog + drift CI + golden baseline | shipped | tag `stage-1f-capability-catalog-complete` (C§8) |
| Stage 1G — 8 always-on primitive MCP tools | shipped | tag `stage-1g-primitive-tools-complete` (C§1) |
| Stage 1H — Fixtures + integration tests | **partial — reduced scope** | v0.1.0 delivered T0/T1-min/T3-min/T7/T-smoke only; 810/9,460 LoC (~9%) (A§2) |
| Stage 1I — Plugin package + uvx smoke | shipped | tag `stage-1i-plugin-package-complete` (C§9) |
| Stage 1J — `o2-scalpel-newplugin` generator | shipped | tag `stage-1j-plugin-skill-generator-complete`; 13 spikes (C§10) |
| Stage 2A — 5 intent facades + transaction commit (6 tools) | shipped | 19 spike tests pass (C§2) |
| Stage 2B — E2E harness + MVP scenarios | **partial — naming/count differs; all 40 E2E pass** | plan promised "9 MVP scenarios"; codebase has ~7 MVP-labeled + 5 Stage 3 (E13–E16); **all 40 E2E pass, 0 skip/xfail** (C§Partial) |
| Stage 3 — 23 specialty facades + 4 Rust E2E + 4 Python E2E + README | shipped | tag `v0.2.0-stage-3-complete`; submodule SHA `4ae3d99e` for T6+T7 (A§3, C§3) |
| v0.3.0 — Facade-application gap closure | shipped | tag `v0.3.0-facade-application-complete`; pure-python WorkspaceEdit applier wired into 8 dispatch sites (C§4) |

**Headline tool count:** 8 primitives + 6 Stage 2A facades + 23 Stage 3 specialty facades = **37 MCP tools** live (C§Summary).

**Honest caveat on Stage 2B:** the plan promised "9 MVP scenarios" by label; the codebase ships ~7 MVP + 5 Stage 3 (E13–E16) and all 40 pass — behaviorally complete, but the labeling/count differs from the plan (C§Partial).

---

## Outstanding work — by category

### 1. Decisions to reconcile (highest priority — small but blocking)

**P5a outcome reversal (DROP → SHIP pylsp-mypy).** The spike-result file `docs/superpowers/plans/spike-results/P5a.md` flipped from "outcome C — DROP pylsp-mypy" to "outcome B — SHIP with documented warning" without coordinating updates to `PROGRESS.md` or the MVP cut freeze (A§4). The measurement deltas:

- `stale_rate`: 8.33% → 0.00% (was 1/12, now 0/12)
- `p95` latency: 8.011s → 2.668s (cold-start within budget on re-run)

This contradicts `PROGRESS.md` decision log §70 ("P5a → C — drop pylsp-mypy"). Agent C and Agent D found **no mypy pin in code** — the Python toolchain still ships `pylsp + basedpyright + ruff` without mypy. So today three artifacts disagree: spike result says SHIP, ledger says DROP, code says DROP. Most likely cause: an unsynchronized manual edit of the spike-result file (A§4 hypothesis).

**Action implied.** The spike re-run evidence (0% stale, p95 within budget) leans toward ratifying SHIP and adding a small code change to enable mypy in the Python strategy; ratifying DROP would require explaining away the new measurement and is the path of least code change. Both are defensible — the project owner must call it. Either way, also update `PROGRESS.md` and the Stage 2A/2B test wiring assumption. **Size: small.** Blocks: any future "is mypy on the critical path?" question; clean spike-result determinism.

### 2. Live tech debt

#### The 6 `inspect.getsource(cls.apply)` flakes

All six are the same pattern — fetching the source of a dynamically-decorated `apply` method on a refactoring-tool class — and live in Stage 2A/3 spike fixtures (D§2):

| File:Line | Test |
|---|---|
| `test_stage_3_t1_rust_wave_a.py:374` | Stage 3 Rust Wave A |
| `test_stage_3_t2_rust_wave_b.py:201` | Stage 3 Rust Wave B |
| `test_stage_3_t3_rust_wave_c.py:247` | Stage 3 Rust Wave C |
| `test_stage_3_t4_python_wave_a.py:181` | Stage 3 Python Wave A |
| `test_stage_3_t5_python_wave_b.py:261` | Stage 3 Python Wave B |
| `test_stage_2a_t9_registry_smoke.py:63` | Stage 2A registry smoke |

**Hypothesis (D§2):** safety-call injection / decorator stacking / bytecode mismatch. `scalpel_facades.py:1002` documents: *"the safety call stays visible in `inspect.getsource(cls.apply)`"* — this confirms the pattern is intentional (the test inspects the safety-call wrapper) and points at the wrapper itself as the likely root cause. **Suggested investigation path (per D§2 hypothesis):** trace the safety-call wrapper at `scalpel_facades.py:1002`; one root-cause fix likely clears all six. Specific remediation TBD — candidates include `functools.WRAPPER_ASSIGNMENTS`-aware source extraction or attaching an explicit source attribute on the decorator, but neither is verified. **Size: small** (single-cause, one fix likely covers all six).

#### Other live debt

- **LSP issue #1040 — systemic flakiness** across F# / Swift / Nix / TypeScript / Erlang / Kotlin (D§1.B, ~25 hits cite #1040 in test comments). This is **ecosystem-owned** (upstream solidlsp), not scalpel-owned, but it contaminates the green-CI signal because tests for those languages are marked `xfail(is_ci)` or `skipif(is_ci)`. **Size: large** (root-cause across multiple LSPs). **Mitigation:** quarantine-tier separation in pytest config; aggregate root-cause investigation.
- **E1-py flake (gap #8)** — documented at commit `2ee21f8` ("chore(stage-2b): document E1-py flake (gap #8) for v0.2.0 backlog") (D§7). Not yet root-caused. **Size: small.** Blocks: 100%-deterministic E2E claim under repeat runs.
- **~10 `# type: ignore` density across 5 scalpel files** (D§4): `scalpel_primitives.py:530`, `scalpel_facades.py` (2 indirect), `symbol_tools.py:232,306,311`, `tools_base.py:307`. Most are union-type variance or kwargs-variance — justified, but trackable. Stage 1H's Pyright pass (per project memory) will finalize compliance. **Size: small.**
- **CI workflow exclusions** (D§6, `.github/workflows/pytest.yml:101–114, 154–157`): Erlang LS install commented out ("hangs on ubuntu, random hangs on macos"); Swift GHA install conflicts with ruby setup, worked around via swiftly. Both documented; no action required, but they cap the green-CI signal for those languages. **Size: medium per language** (upstream toolchain debt).

### 3. Honest MVP gaps (deferred from MVP cut, scoped by plan)

**Stage 1H continuation — the largest structural gap.** The original Stage 1H plan called for 13 tasks (T0–T12) totalling ~9,460 LoC of fixtures + integration tests across 31 modules with ~70 sub-tests. The v0.1.0 cut delivered only T0, T1-min, T3-min, T7, and T-smoke — 810 LoC (~9% of plan); the remainder was explicitly routed to a v0.2.0 Stage 1H continuation (A§2, `stage-1h-results/PROGRESS.md:32–33,73–81`).

Specifically deferred:

- **T2** — 17 RA companion crates (the `calcrs` workspace was bootstrapped with 1 crate only)
- **T4–T6** — 3 calcpy sub-fixtures (the `calcpy` package shipped with `core.py` only)
- **T8–T9** — 16 Rust assist-family integration tests
- **T10** — 8 Python integration tests
- **T11** — 7 cross-language multi-server tests
- **Headline `calcpy` monolith** (~950 LoC) for full Python facade exercise (A§6)

**What landing the rest buys:** per-assist-family integration coverage that the MVP currently only proves end-to-end via the spike + 40 E2E tests. Production code is solid (all 14/15 domains implemented, no `NotImplementedError`); the *coverage breadth* the original design report promised is unmet. **Size: large** (~8,650 LoC fixtures + tests). **Blocks:** depth-of-coverage claims for Rust assist families and Python multi-LSP merge; nothing structurally blocked.

**Stage 2B scenario relabel.** The plan promised "9 MVP scenarios"; the codebase has ~7 MVP-labeled + 5 Stage 3 (E13–E16). All 40 E2E pass with 0 xfail. Cosmetic label/cross-reference cleanup. **Size: small. Blocks: none.**

### 4. v0.2.0 follow-ups (next-up, planned)

Four documented follow-ups from `stage-1h-results/PROGRESS.md:83–89` (A§5), plus two project-memory notes:

- **basedpyright dynamic-capability gap** — _CLOSED 2026-04-26 (tag `stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete`)._ `DynamicCapabilityRegistry` records `client/registerCapability` events keyed by per-server `server_id`; `LanguageHealth.dynamic_capabilities` (tuple) surfaces them in the `workspace_health` MCP tool and adds them into `capabilities_count`. 8 tests cover registry, integration, and per-server keying. Wired for basedpyright + pylsp; future concrete servers (ruff, rust-analyzer, jdtls, …) opt in by setting `server_id: ClassVar[str]`. _Footnote:_ basedpyright registrations will surface in the python `LanguageHealth` only after the static capability catalog (Stage 1F `capability_catalog_baseline.json`) gains basedpyright `source_server` attribution — the registration mechanism is wired and verified at the handler level (`test_register_capability_records.py`); the catalog evolution is a separate v0.2.0+ concern.
- **rust-analyzer position validation** — edge-case correctness for cursor-positioned assists. **Size: medium.** Blocks: edge-case correctness claim.
- **Multi-server async wrapping** — parallelism in the multi-LSP merge path. **Size: medium.** Blocks: parallelism in merge.
- **CARGO_BUILD_RUSTC workaround** — clean Rust-host build environment claim. **Size: small.**
- **E1-py flake (gap #8)** — see §2 above.
- **Headline calcpy monolith (~950 LoC)** — see §3 above; routed alongside Stage 1H continuation.

### 5. v1.1 / marketplace

From coordinator Bucket C; eight items (A§5, B§4):

- **Marketplace publication at `o2alexanderfedin/claude-code-plugins`** — multi-plugin repo layout finalized (Q11 resolution, B§4), distribution channel deferred. Today: `uvx --from <local-path>`. **Size: medium.**
- **Persistent disk checkpoints durability** across sessions — MVP uses LRU only. **Size: medium.**
- **Plugin reload tool / `scalpel_reload_plugins`** — named in Q10 resolution, not implemented. **Size: small.**
- **Rust + clippy multi-server scenario** — only Python multi-LSP at MVP. **Size: medium.**
- **Engine config knob** — project-memory note from v0.2.0 critical-path. **Size: small.**
- **Per-annotation confirm-handle (`scalpel_confirm_annotations`)** — opt-in manual-review workflow (q4-changeannotations-auto-accept §6.3). **Size: small.**
- **3 Python facades** (`convert_to_async`, `annotate_return_type`, `convert_from_relative_imports`) — project-memory note from v0.2.0 Stage 3. **Size: medium.**
- **PEP 695/701/654 fixture variants** — scope-report §4.7 row 22. **Size: small.**

### 6. v2+ language strategies

TypeScript / vtsls, Go / gopls, C / C++ / clangd, Java / jdtls (A§7, B§5.3, `mvp-execution-index.md:96`). Stage 1J's `o2-scalpel-newplugin` generator means each is a **pure plugin addition with zero facade rewrites** (B§5: "additional languages pure plugin additions, no facade rewrites needed" — strategies follow the same 15-method `Protocol`) (Q13 resolution permits Boostvolt-shaped plugin trees with attribution). Long-tail languages (Kotlin, Ada, Svelte, Vue, etc.) flow through the same generator. **Size: large** for each first-class strategy; **medium** for generator-driven long-tail.

**Watch items:** gopls daemon reuse (golang/go#78668) — Go strategy degrades to per-workspace path until upstream closes (B§4).

---

## Cross-cutting risks

1. **LSP issue #1040 contaminates green-CI signal** (D§1.B, D§Recommendations-1). Ten-plus test comments across F# / Swift / Nix / TypeScript / Rust cite #1040; ecosystem-owned, but degrades trust in CI passes. *Mitigation:* aggregate root-cause investigation; consider quarantine-tier separation in pytest config.
2. **Anthropic native LSP-write integration is the long-horizon deprecation trigger** (B§3, citing `anthropics/claude-code#24249`, `#1315`, `#32502`; horizon 6–18 months). *Mitigation:* optimize for clean handoff path; no immediate action.
3. **`lspee` multiplexer maturity** is pre-1.0 today (B§4). If it reaches 1.0 + has a test suite, revisit the two-process problem. *Mitigation:* watch-only.
4. **P5a unsynchronized manual edits** raise a governance risk: spike-result outcomes can drift silently from the decision log (A§4). *Mitigation:* require coupled change to PROGRESS.md decision log when spike outcomes shift.
5. **Capability-vs-test-surface tension** — production code is solid; coverage breadth from the original 31-module / 70-sub-test promise is unmet (A§2, C§11). *Mitigation:* Stage 1H continuation directly addresses this.
6. **Plugin-list API request filed with Anthropic** (B§4 watch-item) — low-cost feature request for documented plugin discovery; tracked, no action.

---

## Out of scope by design (for completeness)

Quoted/paraphrased from `B§7`:

- `experimental/onEnter` LSP method — explicit-block (editor-keystroke semantics unfit for autonomous MCP)
- Filesystem watcher on plugin cache — explicit-reject (refresh via `scalpel_reload_plugins`, matches Serena precedent)
- Within-function extractions in v1 — primitive-only at MVP
- `typeHierarchy` — non-goal (not offered by rust-analyzer)
- Writing new rust-analyzer assists upstream — non-goal
- Streaming LSP ops / async tool apply — non-goal, status quo synchronous
- Native IDE integrations (VSCode, IntelliJ) — v2+, MCP-only at MVP
- `viewHir` / `viewMir` / `viewCrateGraph` / `viewSyntaxTree` / `viewFileText` / `viewRecursiveMemoryLayout` / `getFailedObligations` / `interpretFunction` — reachable via primitive escape hatch only (B§3)
- Test Explorer family (7 rust-analyzer methods) — v1.1 deferral (B§3)
- Bulk LSP-config plugins — explicitly rejected in favour of `o2-scalpel-newplugin` generator (B§2 Q14)

---

## Recommended sequencing

If the project picks up tomorrow, the rational order is:

1. **Resolve P5a mypy decision** (§1). *Why first:* small-size, decision-only (likely no code change), unblocks Stage 2A/2B test definitions and prevents the reversal from contaminating any future spike. Do this before anything that touches the Python strategy.
2. **Fix the 6 `inspect.getsource` flakes** (§2). *Why next:* single-cause investigation; one fix likely clears all six and restores spike-suite determinism. Quick win, small size, immediately improves trust in the spike suite.
3. **Execute the v0.2.0 follow-ups** (§4). *Why next:* already named, scoped, and routed; clears the v0.2.0 backlog as a unit. Most are small/medium and unblock named coverage claims (multi-server async, basedpyright dynamic-capability, RA position validation, CARGO_BUILD_RUSTC, E1-py flake).
4. **Land Stage 1H continuation** (§3). *Why next:* large, but the only structural breadth gap; ~8,650 LoC fixtures + 28 tests + 17 RA companion crates + 3 calcpy sub-fixtures. Schedule as a dedicated milestone after v0.2.0 follow-ups settle so the integration-test surface catches up to production-code breadth.
5. **v1.1 milestone** (§5). *Why next:* coherent grouping — marketplace publish + persistent checkpoints + Rust+clippy multi-server + 3 Python facades + PEP variant fixtures + per-annotation confirm-handle. Wait until Stage 1H lands so the v1.1 work has full coverage breadth underneath it.
6. **v2+ language strategies** (§6). *Why last:* TS/Go first (highest user demand per design); generator already ships, so each is incremental rather than architectural. Each new strategy follows the existing 15-method `Protocol` (B§5.2) with zero facade rewrites.
7. **Issue #1040 root-cause** (cross-cutting risks #1) — schedule as ecosystem investigation **in parallel** with v1.1; not on the scalpel critical path but degrades CI trust until done.

**Rationale:** decisions before code; quick determinism wins before scope expansion; honest breadth gap (Stage 1H) before new milestone breadth (v1.1, v2+); ecosystem risks tracked but never block scalpel-owned forward progress.

---

## Sources

All sibling files in this directory (`docs/gap-analysis/`):

- `COORDINATOR-OUTLINE.md` — authoritative 8-bucket structure (A–H) + reconciliation notes + headline + sequencing
- `A-plans.md` — planning-artifact audit: 14 sub-plans + 14 result-dir ledgers + 2 spike summaries; identifies P5a reversal
- `B-design.md` — design-intent audit: README, CHANGELOG, design report, Q1–Q14 resolutions, install.md
- `C-code.md` — code-state audit: 14/15 domains implemented, 0 production stubs, 117 test files / ~694 functions
- `D-debt.md` — tech-debt + flake inventory: 150+ skipped tests categorized; 6 inspect.getsource flakes; ~10 type:ignores; CI exclusions
- `REPORT-DRAFT-V1.md`, `REPORT-REVIEW.md` — pair-programming artifacts (driver draft + navigator review) preserved for traceability

---

*Author: AI Hive(R)*
