# Plan-vs-Code Coverage Review — Post v0.2.0 Follow-ups
**Date**: 2026-04-27
**Specialist**: Plan Coverage (Reviewer 2)

## Summary

The v0.2.0 follow-ups TREE (`2026-04-26-v020-followups/`) shipped 5/5 leaves cleanly — all five are reflected in code, in git tags, and as CLOSED entries in `docs/gap-analysis/WHAT-REMAINS.md` §4 (lines 102–114). However, **two atomic single-doc plans from the post-v0.3.0 portfolio remain entirely UNEXECUTED**: `2026-04-26-decision-p5a-mypy.md` and `2026-04-26-fix-inspect-getsource-flakes.md` — each authored on the same day as the post-v0.3.0 INDEX (`d66630b`) but never started in code. Three TREE plans are untouched as expected (`stage-1h-continuation`, `v11-milestone`, `v2-language-strategies`). The biggest plan-vs-reality drift is in the legacy `2026-04-24-mvp-execution-index.md` ledger, which still shows Stages 1A/1B/1H/1I/2A/2B as "Plan ready" even though they all carry shipped tags.

## Plan inventory (per directory)

Enumerated from `ls /Volumes/Unitek-B/Projects/o2-scalpel/docs/superpowers/plans/`:

| Plan dir / file | Status | Leaves shipped | Leaves remaining | Tag(s) |
|---|---|---|---|---|
| `2026-04-24-mvp-execution-index.md` | COMPLETE (rollup) | 11 sub-stages | 0 | `v0.1.0-mvp` |
| `2026-04-24-phase-0-pre-mvp-spikes.md` | COMPLETE | all spikes | 0 | `phase-0-spikes-complete` |
| `2026-04-24-stage-1a-lsp-primitives.md` | COMPLETE | T0..Tn | 0 | `stage-1a-lsp-primitives-complete` |
| `2026-04-24-stage-1b-applier-checkpoints-transactions.md` | COMPLETE | all | 0 | `stage-1b-applier-checkpoints-transactions-complete` |
| `2026-04-24-stage-1c-lsp-pool-discovery.md` | COMPLETE | all | 0 | `stage-1c-lsp-pool-discovery-complete` |
| `2026-04-24-stage-1d-multi-server-merge.md` | COMPLETE | all | 0 | `stage-1d-multi-server-merge-complete` |
| `2026-04-24-stage-1f-capability-catalog.md` | COMPLETE | all | 0 | `stage-1f-capability-catalog-complete` |
| `2026-04-24-stage-1g-primitive-tools.md` | COMPLETE | 8 tools | 0 | `stage-1g-primitive-tools-complete` |
| `2026-04-24-stage-1h-fixtures-integration-tests.md` | **PARTIAL — REDUCED v0.1.0 cut** | T0, T1-min, T3-min, T7, T-smoke | T2, T4–T6, T8–T11, calcpy monolith (~91% of plan) | `stage-1h-v0.1.0-complete` |
| `2026-04-24-stage-1i-plugin-package.md` | COMPLETE | T0..T7 | 0 | `stage-1i-plugin-package-complete` |
| `2026-04-24-stage-2a-ergonomic-facades.md` | COMPLETE | T0..T11 | 0 | `stage-2a-ergonomic-facades-complete` |
| `2026-04-24-stage-2b-e2e-harness-scenarios.md` | COMPLETE w/ caveat | 9 MVP + 5 Stage 3 (E13–E16) | "9 MVP scenarios" label/count differs (40/40 pass, 0 xfail) | `stage-2b-e2e-harness-scenarios-complete` |
| `2026-04-25-stage-1e-python-strategies.md` | COMPLETE | T0..T9 | 0 | `stage-1e-python-strategies-complete` |
| `2026-04-25-stage-1j-plugin-skill-generator.md` | COMPLETE | T0..T12 | 0 | `stage-1j-plugin-skill-generator-complete` |
| `2026-04-26-INDEX-post-v0.3.0.md` | INDEX (live) | refs streams 1–6 | — | n/a |
| `2026-04-26-decision-p5a-mypy.md` | **FUTURE — UNEXECUTED** | 0 | All 5 tasks | — |
| `2026-04-26-fix-inspect-getsource-flakes.md` | **FUTURE — UNEXECUTED** | 0 | All 6 tasks | — |
| `2026-04-26-stage-1h-continuation/` (6 leaves) | FUTURE | 0 | 01–06 | — |
| `2026-04-26-stage-3-v0-2-0-ergonomic-facades.md` | COMPLETE | T1..T9 | 0 | `v0.2.0-stage-3-complete`, `v0.2.0-stage-3-facades-complete` |
| `2026-04-26-v020-followups/` (5 leaves) | **COMPLETE** | 01, 02, 03, 04, 05 | 0 | `stage-v0.2.0-followups-complete`, `stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete` |
| `2026-04-26-v11-milestone/` (8 leaves) | FUTURE | 0 | 01–08 | — |
| `2026-04-26-v2-language-strategies/` (5 leaves) | FUTURE | 0 | 01–05 | — |

**Totals.** 13 historical plan files + 1 INDEX + 2 atomic decision/fix docs + 4 TREE dirs (24 leaves) = **44 plan artifacts**. Shipped: ~18 (Stages 1A–1J except 1H, Stages 2A/2B, Stage 3, all 5 v020-followup leaves). Outstanding: 2 atomic + 19 TREE leaves (6 in stage-1h-continuation, 8 in v11-milestone, 5 in v2-language-strategies).

## Plans declared COMPLETE but with uncovered leaves

### Finding 1 — `2026-04-24-stage-2b-e2e-harness-scenarios.md` (label drift, behaviorally complete)

Plan promised "9 MVP scenarios" but ships ~7 MVP-labeled + 5 Stage 3 (E13–E16). All 40 pass with 0 xfail in the e2e suite. Already documented honestly in `docs/gap-analysis/WHAT-REMAINS.md:33,40` (state-of-the-union table caveat). Cosmetic only.

### Finding 2 — `2026-04-24-stage-1h-fixtures-integration-tests.md` (ledger-reduced; partial cut tagged)

The plan promises 13 tasks T0–T12 / ~9,460 LoC across 31 test modules. Per `docs/superpowers/plans/stage-1h-results/PROGRESS.md:8,13–25,32–34`, the v0.1.0 cut delivered only T0, T1-min, T3-min, T7, and T-smoke (~810 LoC, ~9% of plan). The deferred ~91% is properly routed to `2026-04-26-stage-1h-continuation/` (6 leaves) and called out in `docs/gap-analysis/WHAT-REMAINS.md:81–94`. **No drift** — the ledger is honest. Tag `stage-1h-v0.1.0-complete` correctly carries the `-v0.1.0-` qualifier to signal the reduced scope.

## Plans declared PARTIAL — what's still to execute

### A. `2026-04-26-stage-1h-continuation/` (6 leaves, all unstarted)

Per `docs/superpowers/plans/2026-04-26-stage-1h-continuation/README.md:11–18`:

| Leaf | Goal | Size | Blocker |
|---|---|---|---|
| 01 | T2 — 17 RA companion crates | ~3,230 fixture LoC | `v020-followups/04` (CARGO_BUILD_RUSTC) — **CLOSED** so unblocked |
| 02 | T4–T6 calcpy sub-fixtures | ~530 fixture LoC | none |
| 03 | T8–T9 — 16 Rust assist integration tests | ~2,120 test LoC | leaf 01 |
| 04 | T10 — 8 Python integration tests | ~950 test LoC | leaf 02 + `v020-followups/01` (basedpyright dyn-cap) — **CLOSED**, so unblocked once leaf 02 lands |
| 05 | T11 — 7 cross-language tests | ~910 test LoC | leaves 01+02 + `v020-followups/03` (multi-server async) — **CLOSED**, so unblocked once leaves 01+02 land |
| 06 | calcpy monolith (~950 LoC headline) | ~1,105 fixture LoC | leaf 02 |

Total honest leaf-body sum: **~8,845 LoC** (per README:22 — note +195 LoC honest delta vs the INDEX's "~8,650 LoC"). All 5 v020-followup preconditions are now CLOSED, so this tree is fully unblocked. Status: **fully ready to execute**.

### B. `2026-04-26-decision-p5a-mypy.md` — UNEXECUTED atomic plan

Plan exists with 5 tasks (TDD lock + pylsp-mypy enable + PROGRESS.md supersede + CHANGELOG warning + cross-artifact lock). Verified against code:

- `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:15` still reads `pylsp-mypy is DELIBERATELY NOT enabled here — Phase 0 P5a verdict C.`
- `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:154` still reads `"pylsp_mypy": {"enabled": False},`.
- `grep` for `P5A_MYPY_DECISION` / `solidlsp/decisions/` returns zero hits in the submodule.
- `docs/superpowers/plans/spike-results/PROGRESS.md:101` quick-reference row still reads `| P5a | C (drop pylsp-mypy) | …`.

Three artifacts disagree exactly as `docs/gap-analysis/WHAT-REMAINS.md:46–55` warned: `P5a.md` says SHIP, ledger says DROP, code says DROP. **Status: not started.** Size: small (5 tasks, ≤30 LoC production + ~95 LoC governance tests).

### C. `2026-04-26-fix-inspect-getsource-flakes.md` — UNEXECUTED atomic plan

Plan exists with 6 tasks (regression test + helpers + Scalpel*Tool wiring + 6-site migration + 10-rerun verification + roll-up). Verified against code:

- `grep -rn "inspect.getsource(cls.apply)" vendor/serena/test/spikes/` confirms all 6 sites still raw: `test_stage_3_t1_rust_wave_a.py:374`, `test_stage_3_t2_rust_wave_b.py:201`, `test_stage_3_t3_rust_wave_c.py:247`, `test_stage_3_t4_python_wave_a.py:181`, `test_stage_3_t5_python_wave_b.py:261`, `test_stage_2a_t9_registry_smoke.py:63`.
- `grep -rn "attach_apply_source\|get_apply_source\|__wrapped_source__" vendor/serena/src vendor/serena/test` returns **zero hits**.
- `docs/gap-analysis/D-debt.md:111` already notes: "*No commit message in the last 50 logs references 'inspect.getsource' fix, suggesting they remain outstanding.*"

**Status: not started.** Size: small (~155 LoC, ~22 ≤5-LoC steps across 6 tasks).

## Plans declared FUTURE — what's queued for next stages

### `2026-04-26-v11-milestone/` (8 leaves)

All `Status: PLANNED` (none of the leaves carry a status header — only the `v2-language-strategies` set does). Per README: 01 marketplace-publication, 02 persistent-disk-checkpoints, 03 scalpel-reload-plugins, 04 rust-clippy-multi-server, 05 engine-config-knob, 06 scalpel-confirm-annotations, 07 three-python-facades, 08 pep-695-701-654-fixtures. **Hard cross-stream gate:** `stage-1h-continuation` MUST land first (README:5 — "intentionally non-negotiable"). Per WHAT-REMAINS.md §Recommended-sequencing item 5.

### `2026-04-26-v2-language-strategies/` (5 leaves, all `Status: PLANNED`)

01 typescript-vtsls (~1,900 LoC, includes leaf-01 Task 2.5 Protocol-extension 4→15 members), 02 go-gopls (~1,700 LoC), 03 c-cpp-clangd (~1,800 LoC), 04 java-jdtls (~1,800 LoC), 05 longtail-generator-flow (~600 LoC). Linear chain 01→02→03→04→05. Hard upstream precondition: `v11-milestone` (README:64).

## Drift between WHAT-REMAINS.md and reality

| Topic | What WHAT-REMAINS says | Reality | Drift severity |
|---|---|---|---|
| §1 P5a SHIP/DROP reversal | "must call it" — flagged as outstanding decision | Plan `2026-04-26-decision-p5a-mypy.md` drafted but unexecuted; 3 artifacts still disagree | **None — accurate, but plan unaddressed** |
| §2 6 inspect.getsource flakes | "Size: small (single-cause, one fix likely covers all six)" — listed as outstanding | Plan `2026-04-26-fix-inspect-getsource-flakes.md` drafted but unexecuted; all 6 sites still raw | **None — accurate; plan exists but is unstarted** |
| §3 Stage 1H gap | "~91% deferred to v0.2.0 'Stage 1H continuation'" | Matches `stage-1h-continuation/README.md` | **None** |
| §4 v0.2.0 follow-ups (5 items) | All 5 marked CLOSED with tags + line references (lines 102–114) | All 5 confirmed shipped; submodule tag `stage-v0.2.0-followups-complete` present + parent tags match | **None — perfectly synchronized** |
| §5 v1.1 marketplace (8 items) | Listed as future | Matches `v11-milestone/` plan dir | **None** |
| §6 v2+ language strategies | 4 first-class + long-tail | Matches `v2-language-strategies/` plan dir | **None** |
| §Sources | Lists `WHAT-REMAINS.md` siblings | All 6 referenced files present in `docs/gap-analysis/` | **None** |

**Single noteworthy drift in summary:** WHAT-REMAINS.md §TL;DR (line 13) still mentions the P5a reversal and 6 inspect.getsource flakes as "biggest items still outstanding" — that wording remains correct because the *plans* exist but neither has been executed. The doc accurately reflects state.

## Drift between INDEX docs and reality

### Finding D1 — `2026-04-24-mvp-execution-index.md` is stale

`docs/superpowers/plans/2026-04-24-mvp-execution-index.md:24–35` shows status columns frozen at planning time. Stages 1A, 1B, 1H, 1I, 2A, 2B are still labeled "Plan ready" or "Plan ready (drafted 2026-04-26; …)" despite all carrying shipped tags. Examples:

- Line 24: Stage 1A `**Plan ready**` — actual: shipped under `stage-1a-lsp-primitives-complete`.
- Line 25: Stage 1B `**Plan ready**` — actual: shipped under `stage-1b-applier-checkpoints-transactions-complete`.
- Line 32: Stage 1H `**Plan ready** (drafted 2026-04-26; 6,061 lines)` — actual: shipped under `stage-1h-v0.1.0-complete` (reduced cut) + continuation tree drafted.
- Line 33: Stage 1I `**Plan ready**` — actual: shipped under `stage-1i-plugin-package-complete`.
- Line 34: Stage 2A `**Plan ready**` — actual: shipped under `stage-2a-ergonomic-facades-complete`.
- Line 35: Stage 2B `**Plan ready**` — actual: shipped under `stage-2b-e2e-harness-scenarios-complete`.

This is the single largest stale-status surface in the planning corpus.

### Finding D2 — `2026-04-26-INDEX-post-v0.3.0.md` is current

The post-v0.3.0 INDEX (line 22 catalog) is internally consistent: every cited dependency (`decision-p5a-mypy`, `v020-followups`, `stage-1h-continuation`, `v11-milestone`, `v2-language-strategies`, `fix-inspect-getsource-flakes`) resolves to a real file/dir. No dangling references. INDEX itself does NOT carry per-stream "shipped" status updates — it remains a forward-planning artifact. Stream 3 (`v020-followups`) is the only one of the six that should now be marked DONE, but INDEX never claimed it was — so this is "stale by omission" rather than active misinformation.

### Finding D3 — Non-existent `INDEX-stage-1h.md`

Reviewer task spec mentioned a `2026-04-26-INDEX-stage-1h.md`. **Verified absent.** `find` of plans dir returns only `2026-04-26-INDEX-post-v0.3.0.md`. The stage-1h continuation tree has its own `README.md` inside `2026-04-26-stage-1h-continuation/` which serves the equivalent role; no separate INDEX file exists or is needed.

### Finding D4 — `stage-1h-results/PROGRESS.md` Concerns block accurately reflects v020-followups closures

Lines 85–88 list the four v020-followup items that originated as Stage 1H concerns; all four read `_CLOSED 2026-04-26 (tag …)_` with tag refs that match `git tag` output. **No drift.**

## Recommendations (prioritized)

### Critical

1. **Execute `2026-04-26-decision-p5a-mypy.md`** (5 tasks, small). The reversal has been outstanding since 2026-04-26 with three artifacts disagreeing in writing (P5a.md vs PROGRESS.md vs `pylsp_server.py:154`). Per WHAT-REMAINS.md §Recommended-sequencing item 1, this is the top-priority next action. Ratifying SHIP also unblocks `v020-followups/05-e1-py-flake` retroactive coherence (the leaf was executed but the spec depended on the P5a decision per `v020-followups/README.md:13`).

2. **Execute `2026-04-26-fix-inspect-getsource-flakes.md`** (6 tasks, ~155 LoC). Per WHAT-REMAINS.md §Recommended-sequencing item 2 — quick-win determinism fix; one root cause expected to clear all 6 sites. Plan is fully detailed and pre-reviewed.

### Important

3. **Refresh `2026-04-24-mvp-execution-index.md` status column.** Update lines 24–35 to mark Stages 1A, 1B, 1H, 1I, 2A, 2B with their respective shipped tags (matching the live convention in lines 26–31 for 1C/1D/1E/1F/1G/1J). Pure docs change. Or, alternative: deprecate the file with a single banner pointing readers to `WHAT-REMAINS.md` and tag history.

4. **Add a status banner to `2026-04-26-INDEX-post-v0.3.0.md`** marking Stream 3 (`v020-followups`) as ✓ COMPLETE (tag `stage-v0.2.0-followups-complete`). Streams 1, 2, 4–6 remain pending. Keeps the live INDEX a source of truth at a glance.

### Minor

5. **Reconcile leaf-count notation in `stage-1h-continuation/README.md:24`.** README footnotes that the MASTER's "~28 tests" should be reconciled to **31** (16 + 8 + 7) or footnoted; the post-v0.3.0 INDEX still cites `28` indirectly via WHAT-REMAINS. Prefer adding a one-line footnote at INDEX line 27 to disambiguate the 28-vs-31 discrepancy.

6. **Add `Status:` headers to `v11-milestone/` leaves.** The `v2-language-strategies/` leaves all carry `Status: PLANNED` headers (per `01-typescript-vtsls-strategy.md:3`, etc.); the v11-milestone leaves do not. Aligns the two future-tree representations.

7. **Consider canonicalizing the "INDEX-stage-1h" path** referenced in some workflow scripts. The reviewer's task spec mentioned this file by name; while it doesn't exist (Finding D3 above), if any tooling/skill references it, point those at `2026-04-26-stage-1h-continuation/README.md` instead.

---

*Author: AI Hive(R)*
