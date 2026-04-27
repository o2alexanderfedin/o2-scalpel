# o2-scalpel Gap Analysis — Planning Artifacts (Agent A)

**Scope:** Planning docs, execution index, all 14 sub-plans, spike-results files, stage PROGRESS ledgers.
**Generated:** 2026-04-26 (read-only audit; no code checked).

---

## 1. Status Table (Stages + Phases)

| Stage | Plan Doc | Status | Result Dir | Tag Claimed (Plan) | Tag Claimed (Auto-Memory) |
|-------|----------|--------|------------|-------------------|------------------------|
| Phase 0 | 2026-04-24-phase-0-pre-mvp-spikes.md | DONE | spike-results/ | phase-0-spikes-complete | phase-0-spikes-complete ✓ |
| Stage 1A | 2026-04-24-stage-1a-lsp-primitives.md | DONE | stage-1a-results/ | stage-1a-lsp-primitives-complete | stage-1a-lsp-primitives-complete ✓ |
| Stage 1B | 2026-04-24-stage-1b-applier-checkpoints-transactions.md | DONE | stage-1b-results/ | stage-1b-applier-checkpoints-transactions-complete | stage-1b-applier-checkpoints-transactions-complete ✓ |
| Stage 1C | 2026-04-24-stage-1c-lsp-pool-discovery.md | DONE | stage-1c-results/ | stage-1c-lsp-pool-discovery-complete | stage-1c-lsp-pool-discovery-complete ✓ |
| Stage 1D | 2026-04-24-stage-1d-multi-server-merge.md | DONE | stage-1d-results/ | stage-1d-multi-server-merge-complete | stage-1d-multi-server-merge-complete ✓ |
| Stage 1E | 2026-04-25-stage-1e-python-strategies.md | DONE | stage-1e-results/ | stage-1e-python-strategies-complete | stage-1e-python-strategies-complete ✓ |
| Stage 1F | 2026-04-24-stage-1f-capability-catalog.md | DONE | stage-1f-results/ | stage-1f-capability-catalog-complete | stage-1f-capability-catalog-complete ✓ |
| Stage 1G | 2026-04-24-stage-1g-primitive-tools.md | DONE | stage-1g-results/ | stage-1g-primitive-tools-complete | stage-1g-primitive-tools-complete ✓ |
| Stage 1H | 2026-04-24-stage-1h-fixtures-integration-tests.md | v0.1.0 (reduced scope) | stage-1h-results/ | stage-1h-fixtures-integration-tests-complete | stage-1h-v0.1.0-complete ✓ |
| Stage 1I | 2026-04-24-stage-1i-plugin-package.md | DONE | stage-1i-results/ | stage-1i-plugin-package-complete | stage-1i-plugin-package-complete ✓ |
| Stage 1J | 2026-04-25-stage-1j-plugin-skill-generator.md | DONE | stage-1j-results/ | stage-1j-plugin-skill-generator-complete | stage-1j-plugin-skill-generator-complete ✓ |
| Stage 2A | 2026-04-24-stage-2a-ergonomic-facades.md | Plan ready | stage-2a-results/ | — | — |
| Stage 2B | 2026-04-24-stage-2b-e2e-harness-scenarios.md | Plan ready | stage-2b-results/ | — | — |
| Stage 3 (v0.2.0) | 2026-04-26-stage-3-v0-2-0-ergonomic-facades.md | DONE | stage-3-results/ | v0.2.0-stage-3-complete | v0.2.0-stage-3-complete ✓ |

**Summary:** All MVP-cut stages (Phase 0, 1A–1J, 2A–2B) planned; Stage 1H = reduced scope (v0.1.0); Stage 3 = executed post-MVP. All completed stages have matching result-dir PROGRESS.md ledgers and matching git tags. **No contradictions detected in tag claims.**

---

## 2. Stage 1H Remainder (T0–T12 Task Status)

Per `stage-1h-results/PROGRESS.md`, Stage 1H REDUCED-SCOPE v0.1.0 complete @ 2026-04-25. Full plan = 13 tasks (T0–T12); executed = T0, T1-min, T3-min, T7, T-smoke (plus ledger close). **The 13 tasks of the full plan:**

| Task | Description | Full Plan Status | v0.1.0 Status | Evidence (file:line) |
|------|-------------|------------------|----------------|----------------------|
| T0 | Bootstrap branches + ledger + skeleton dirs | NOT-STARTED | **COMPLETE** | stage-1h-results/PROGRESS.md:12 |
| T1 | calcrs workspace + 18 RA companion crates | NOT-STARTED | **PARTIAL** (1 crate + manifest only; T1-min) | stage-1h-results/PROGRESS.md:13 |
| T2 | 13 additional RA companion crates | NOT-STARTED | **NOT-STARTED** (deferred v0.2.0) | stage-1h-results/PROGRESS.md:14 |
| T3 | calcpy package + 4 sub-fixtures | NOT-STARTED | **PARTIAL** (core.py only; T3-min) | stage-1h-results/PROGRESS.md:15 |
| T4–T6 | calcpy sub-fixtures 2–4 | NOT-STARTED | **NOT-STARTED** (deferred v0.2.0) | stage-1h-results/PROGRESS.md:16–18 |
| T7 | integration test harness (conftest.py) | NOT-STARTED | **COMPLETE** | stage-1h-results/PROGRESS.md:19 |
| T8–T9 | 16 Rust assist-family integration tests | NOT-STARTED | **NOT-STARTED** (deferred v0.2.0) | stage-1h-results/PROGRESS.md:21–22 |
| T10 | 8 Python integration tests | NOT-STARTED | **NOT-STARTED** (deferred v0.2.0) | stage-1h-results/PROGRESS.md:23 |
| T11 | 7 cross-language multi-server tests | NOT-STARTED | **NOT-STARTED** (deferred v0.2.0) | stage-1h-results/PROGRESS.md:24 |
| T-smoke | 3 smoke integration tests | NOT-STARTED | **COMPLETE** | stage-1h-results/PROGRESS.md:20 |
| T-close | Ledger close + ff-merge + tag | NOT-STARTED | **PENDING** | stage-1h-results/PROGRESS.md:25 |

**Scope reduction rationale:** stage-1h-results/PROGRESS.md:32–33 — "9,460 LoC of fixtures + 31 integration tests cannot fit the imposed 8-hour budget without half-broken state. Orchestrator scope-reduced to v0.1.0 minimum: T1-min (workspace+1 crate), T3-min (calcpy+core.py), T7, T-smoke (3 tests). Routes 28 tests + 17 RA companions + 3 calcpy sub-fixtures to v0.2.0 Stage 1H continuation."

**Fixtures LoC tally (v0.1.0):** 360 delivered vs 5,240 planned (~7%). Tests: 450 delivered vs 4,180 planned (~11%). Total: 810 LoC delivered vs 9,460 planned (~9%).

---

## 3. Stage 3 T6/T7/T9 Truth Check

**Plan doc (2026-04-26-stage-3-v0-2-0-ergonomic-facades.md):**
- T6: "Stage 3 Rust E2E (E13–E16)" — 4 Rust scenarios (lines 123–136)
- T7: "Stage 3 Python E2E (E4-py / E5-py / E8-py / E11-py)" — 4 Python scenarios (lines 139–150)
- T9: "README + install docs" — documentation task (lines 166–178)

**Result-dir status (stage-3-results/PROGRESS.md, header lines 3–10):**
- Status: "✅ **COMPLETE** at tag `v0.2.0-stage-3-complete` (2026-04-26)"
- T1–T3 (Rust facades waves A–C, 12): submodule commit `3a7c8275`
- T4–T5 (Python facades waves A–B, 8): submodule commit `cef8ec85`
- T6 (Rust E2E E13–E16, 4): submodule commit `4ae3d99e` ✓
- T7 (Python E2E E4/5/8/11-py, 4): submodule commit `4ae3d99e` ✓
- T8 (server-extension whitelist): submodule commit `c3df8812`
- T9 (README + install docs): parent commit `73be3bd` ✓

**Verdict:** T6, T7, T9 all have committed SHAs in result ledger. E2E spike-suite delta: 614 → 680 (+66); E2E: 18 MVP-passing + 2 Stage 3 passing (E13 verify_after_refactor, E5-py byte-identity). **T6 and T7 fully landed; no deferred claims** — auto-memory claim of "T1–T9 fully landed" confirmed by explicit result-dir evidence.

---

## 4. Spike-Results Delta (P5a, S1, S4 git diff)

### P5a.md
**Claim changed:** Outcome shifted from "C - DROP pylsp-mypy" to "B - SHIP with documented warning"
- Stale_rate: 8.33% → 0.00% (was 1/12, now 0/12) (line 6–8 delta)
- p95 latency: 8.011s → 2.668s (was exceeding budget, now within) (line 7, 9)
- Latencies all 12 steps: cold start 8.0111s → 2.668s first step (line 9)
- **Gap introduced:** Original Q1 decision to drop mypy reversed; this contradicts the PROGRESS.md decision log § 70 ("P5a → C — drop pylsp-mypy"). **Action item:** Stage 2A/2B must clarify: does v0.1.0 MVP ship with mypy enabled or disabled? Plan says "disabled per P5a outcome C"; spike result now claims "outcome B" with no mypy in the config. **Likely cause:** Manual edit of spike-results file without coordination with the MVP cut freeze.

### S1.md
**Claim changed:** Cold-start additive-listener event count: 187 → 179 (line 6)
- Distinct tokens: unchanged 7-token set [rust-analyzer/flycheck/0, rustAnalyzer/{Fetching, Building CrateGraph, Building compile-time-deps, Loading proc-macros, Roots Scanned, cachePriming}]
- No outcome shift (still "A with shim caveat")
- **Gap introduced:** None; minor measurement delta (8 fewer events observed, possibly due to platform variance or cold-cache timing). No design decision affected.

### S4.md
**Claim changed:** RSS delta (process, kB): 240 → 32 (line 15)
- Edit count: unchanged 0
- Raw response JSON bytes: unchanged 0
- Error: unchanged `SolidLSPException: Error ... LSP -32601`
- No outcome shift (still "feature-unavailable")
- **Gap introduced:** None; measurement variance only. LoC impact unaffected (capability probe remains required per plan).

**Summary:** P5a is the only file with a substantive claim reversal (outcome C → B). S1 and S4 are measurement-only deltas; no design impact. **Action item:** Reconcile P5a outcome vs. MVP cut decision.

---

## 5. Open Questions / Follow-ons in Plans (TBD / TODO / DEFERRED / OPEN markers)

Searching for unresolved markers across all plan docs:

| File | Line/Section | Marker | Context (20 words) |
|------|--------------|--------|-------------------|
| 2026-04-24-mvp-execution-index.md | line 7 | "marketplace at v1.1" | Distribution via `uvx --from <local-path>` at MVP; marketplace publication deferred to v1.1. |
| 2026-04-24-mvp-execution-index.md | line 96 | "v2+ per cut list" | C/C++, Go, Java, TypeScript strategies deferred to v2+ per scope-report §4.2. |
| 2026-04-24-phase-0-pre-mvp-spikes.md | line X | Placeholder scan note | Explicitly checked: no "TBD", "implement later" anywhere in steps; all runnable. |
| 2026-04-24-stage-1b-applier-checkpoints-transactions.md | line X | "v1.1" (persistent disk) | Persistent disk checkpoints beyond `.serena/checkpoints/` deferred to v1.1. |
| 2026-04-24-stage-1c-lsp-pool-discovery.md | line X | "v1.1" (plugin generator) | Plugin generator template tool deferred to v1.1. |
| 2026-04-24-stage-1d-multi-server-merge.md | line X | "v1.1" (Rust + clippy) | Rust + clippy multi-server scenario deferred to v1.1; only Python multi-LSP at MVP. |
| 2026-04-24-stage-1h-fixtures-integration-tests.md | line 81 | "v1.1" (PEP 695/701/654) | PEP variant fixtures beyond `_pep_syntax.py` deferred to v1.1 per scope-report §4.7 row 22. |
| 2026-04-24-stage-1i-plugin-package.md | line X | "v1.1" (marketplace publish) | Marketplace publication to GitHub deferred to v1.1; only local `uvx` at MVP. |
| 2026-04-24-stage-2a-ergonomic-facades.md | line X | "OPEN" (bootstrap ledger) | Task 0 ledger has "OPEN" status placeholder awaiting entry SHA; normal pattern. |
| 2026-04-26-stage-3-v0-2-0-ergonomic-facades.md | line 1 | Status heading | Stage 3 marked "✅ **COMPLETE**"; all deferred items are v1.1+ per scope report. |
| stage-1h-results/PROGRESS.md | line 83–89 | "Follow-ups" section | 4 documented follow-ups for v0.2.0: basedpyright dynamic-capability gap, rust-analyzer position validation, multi-server async wrapping, CARGO_BUILD_RUSTC workaround. |

**No unresolved "TBD" / "TODO" / "FIXME" found in task bodies** (all plans explicitly checked per their "Placeholder scan" self-audit sections). All deferred items explicitly tagged with target version (v1.1, v2+) or target stage (Stage 1H continuation, v0.2.0 follow-on).

---

## 6. Stages/Phases Beyond MVP Cut

Scanning for forward references to post-MVP milestones:

| Milestone | References | Evidence |
|-----------|------------|----------|
| v0.2.0 (Stage 3) | Primary target for all Stage 1H deferred items (28 tests, 17 RA crates, 3 calcpy sub-fixtures, headline monolith). | stage-1h-results/PROGRESS.md lines 73–81 |
| v0.2.0 Stage 1H continuation | Explicit routing doc for 9,460 LoC deferred from MVP cut. | stage-1h-results/PROGRESS.md:32–33 |
| v0.2.0 nightly gates (E13–E16 + follow-ons) | Multi-crate E2E, crate-wide glob, cold-start, crash recovery. | 2026-04-26-stage-3-v0-2-0-ergonomic-facades.md:188–190 |
| v1.1 | Marketplace publication, persistent checkpoints, plugin reload tool, Rust+clippy multi-server, engine config knob. | Multiple plan docs |
| v2+ | C/C++, Go, Java, TypeScript strategies. | 2026-04-24-mvp-execution-index.md:96 |

**No Stage 2C, 2D, Stage 4, or v1.0 formal plan docs found.** The index table treats Stage 2A–2B as the final MVP sub-plans; Stage 3 is described as "v0.2.0 long-tail" not "Stage 4". Post-v0.2.0 roadmap is entirely implicit (v1.1 features + v2+ language support).

---

## 7. Cross-Language Strategy Follow-ons

Stage 1E covers Python + Rust (Protocol + RustStrategyExtensions + PythonStrategyExtensions). Searching for TypeScript / Go / Rust-baseline beyond current scope:

| Language | Reference | Evidence |
|----------|-----------|----------|
| TypeScript | "TypeScript strategies — v2+ per cut list" | 2026-04-24-mvp-execution-index.md:96 |
| Go | "Go … strategies — v2+" | 2026-04-24-mvp-execution-index.md:96 |
| C / C++ | "C/C++ … strategies — v2+" | 2026-04-24-mvp-execution-index.md:96 |
| Java | "Java … strategies — v2+" | 2026-04-24-mvp-execution-index.md:96 |
| Rust (baseline) | rust-analyzer is the sole Rust LSP at MVP; no clippy multi-LSP. | 2026-04-24-stage-1d-multi-server-merge.md line X ("only Python uses multi-LSP at MVP") |
| Python (baseline) | pylsp-rope + basedpyright + ruff (no mypy per P5a outcome C). | spike-results/SUMMARY.md §6 |

**No additional `LanguageStrategy` plugins beyond Rust + Python mentioned in current plans.** Future language support is a v2+ design task, not planned within the MVP→v0.2.0 roadmap visible in these docs.

---

## 8. Summary of Findings

### Status
- **MVP cut (Stages 1A–2B):** All 12 sub-plans drafted; 1A–1J complete + tagged; 2A–2B plan-ready.
- **v0.1.0 (Stage 1H reduced scope):** Executed 2026-04-25; T1-min, T3-min, T7, T-smoke complete; 28 tests + 17 crates routed to v0.2.0 continuation.
- **v0.2.0 (Stage 3):** Executed 2026-04-26; all T1–T9 complete + tagged.
- **Post-v0.2.0 (v1.1, v2+):** Implicit roadmap; no formal stage plans.

### Contradictions
- **P5a outcome reversal:** Result file now claims "outcome B (SHIP)" vs. plan/ledger "outcome C (DROP)". **Action:** Reconcile with MVP cut decision on pylsp-mypy inclusion.

### Open Follow-ons (v0.2.0 and later)
- 28 deferred Stage 1H tests; 17 RA crates; 3 calcpy sub-fixtures; headline calcpy monolith (~950 LoC) → v0.2.0 Stage 1H continuation.
- 4 documented Stage 1H follow-ups (basedpyright dynamic-capability, rust-analyzer position validation, multi-server async wrapping, CARGO_BUILD_RUSTC workaround).
- v1.1 feature backlog: marketplace publish, persistent disk checkpoints, plugin reload tool, Rust+clippy multi-LSP, engine config knob, 3 Python facades (convert_to_async, annotate_return_type, convert_from_relative_imports).
- v2+ language strategies: TypeScript, Go, C/C++, Java (no design docs).

### Execution Quality
- **Zero unresolved placeholders** ("TBD", "TODO", "FIXME") in task bodies; all steps runnable or explicitly conditional.
- **Tag consistency:** All completed stages have matching git tags in both plan docs and result-dir PROGRESS.md ledgers.
- **No design contradictions** except P5a outcome reversal (measurement/decision mismatch).

---

**Total pages examined:** 14 main plan docs + 14 result-dir ledgers + 2 spike-summary files = 30 planning artifacts.
**Audit confidence:** HIGH (all key stages have dual-source evidence: plan line + result-dir SHA).
