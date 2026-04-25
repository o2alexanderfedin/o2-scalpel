# Phase 0 — Execution Progress Ledger

> **Purpose:** Durable across context resets. Each task entry records what was done, problems hit, and decisions made. Future sessions check this file FIRST before re-running anything. The TaskList tool tracks per-conversation status; this file tracks cross-conversation history.

**Plan:** [`docs/superpowers/plans/2026-04-24-phase-0-pre-mvp-spikes.md`](../2026-04-24-phase-0-pre-mvp-spikes.md)
**Branch:** `feature/phase-0-pre-mvp-spikes` (git-flow)
**Started:** 2026-04-24
**Author:** AI Hive(R)

---

## Status legend

- ⏳ pending — not started
- 🚧 in-progress — implementer dispatched
- 🔍 spec-review — implementer DONE, spec reviewer dispatched
- 🔬 quality-review — spec reviewer ✅, quality reviewer dispatched
- ✅ done — both reviews ✅, committed
- ⚠️ blocked — implementer escalated; needs decision
- 🔁 fix-loop — reviewer found issues; implementer fixing

## Per-task ledger

| # | Task | Status | Commit | Outcome / Notes |
|---|---|---|---|---|
| 1 | Bootstrap scaffolding + seed fixtures | ✅ | parent 4936ef8 / submod 32e7afdb | scaffolding + seed fixtures + sync conftest fix; both reviews ✅ |
| 2 | Spike S1 — `$/progress` forwarding (BLOCKING) | ✅ | parent 1c54f367 / submod 3e24e449 | Outcome **A**: 140-180 `$/progress` events with 7 rich token classes (rustAnalyzer/Fetching, Building CrateGraph, Loading proc-macros, cachePriming, Roots Scanned, Building compile-time-deps, rust-analyzer/flycheck/N) reach the wrapper dispatcher. Public-API tap is clobbered by `rust_analyzer.py:720` `do_nothing` + single-callback dispatcher → +30 LoC shim required (plan §13 fallback). |
| 3 | Spike S3 — `applyEdit` reverse-request (BLOCKING) | 🚧 | — | implementer dispatched |
| 4 | Spike P1 — pylsp-rope unsaved buffer (BLOCKING) | ⏳ | — | — |
| 5 | Spike P2 — organize-imports merge winner (BLOCKING) | ⏳ | — | — |
| 6 | Spike P5a — pylsp-mypy stale-rate (BLOCKING) | ⏳ | — | — |
| 7 | Spike S2 — snippetTextEdit:false honored | ⏳ | — | — |
| 8 | Spike S4 — `experimental/ssr` upper bound | ⏳ | — | — |
| 9 | Spike S5 — `expandMacro` on proc macros | ⏳ | — | — |
| 10 | Spike S6 — auto_import resolve shape | ⏳ | — | — |
| 11 | Spike P3 — Rope vs PEP 695/701/654 | ⏳ | — | — |
| 12 | Spike P4 — basedpyright relatedInformation | ⏳ | — | — |
| 13 | Spike P6 — three-server rename convergence | ⏳ | — | — |
| 14 | Spike P3a — basedpyright==1.39.3 baseline | ⏳ | — | — |
| 15 | Spike P-WB — workspace-boundary rule | ⏳ | — | — |
| 16 | Synthesis — SUMMARY.md | ⏳ | — | — |
| 17 | Phase 0 exit gate + tag | ⏳ | — | — |

## Decisions log (chronological)

| Date | Decision | Rationale | Affects |
|---|---|---|---|
| 2026-04-24 | Phase 0 executed via subagent-driven-development skill, serial dispatch (no parallel implementers). | Per skill rule: "Never dispatch multiple implementation subagents in parallel — conflicts." | All Phase 0 tasks |
| 2026-04-24 | Feature branch `phase-0-pre-mvp-spikes` (git-flow), not worktree. | Project CLAUDE.md mandates git-flow; worktree is the superpowers default but project convention takes precedence. | All Phase 0 commits |
| 2026-04-24 | Each spike test asserts `outcome` is truthy (always passes), not the optimistic outcome. | Spikes record evidence, not features. Failing the test would mean we couldn't continue; classifying A/B/C lets us proceed and feed Stage 1 design. | All spike tests |
| 2026-04-24 | Task 1 spike scaffolding committed inside `vendor/serena` submodule (on `main` branch, writable, not detached); parent commit records the bumped submodule SHA `6c704f2b`. | Submodule was on writable `main` branch at task start, so files were committed there per plan rather than escalating. Parent commit only carries the submodule pointer + `.gitkeep` + this ledger. | Task 1 + future submodule-touching tasks |
| 2026-04-24 | Submodule local git config pinned to `AI Hive(R) <af@o2.services>` after Task 1 (`git -C vendor/serena config user.{name,email}`). | Task 1 implementer found the submodule's local config defaulted to `o2alexanderfedin`, requiring `--amend --author` per commit. One-time fix prevents recurrence. | All future submodule-touching tasks |
| 2026-04-24 | **PROGRESS.md updates ship as separate commits, NOT amends.** Convention change after Task 1 surfaced an unavoidable SHA-drift cycle when amending the same commit to embed its own SHA. | Implementer correctly identified that every amend rewrites the SHA, so the embedded SHA goes stale immediately. Solution: implementer commits the work, then commits the PROGRESS.md update separately referencing the work commit. Two commits per task is acceptable. | All future tasks |
| 2026-04-24 | Spike test code blocks in plan Tasks 2-15 are **illustrative**, not authoritative. Each spike implementer must verify wrapper methods (`request_code_actions`, `notify_did_change`, `execute_command`, `server.on_notification`, etc.) against the actual `SolidLanguageServer` API before invoking them. | Quality reviewer caught that `start_session()` doesn't exist on the wrapper; broader audit suggests other plan-doc method names are speculative. Missing wrapper methods are themselves Phase 0 findings (they imply Stage 1A must add them). | Tasks 2–15 spike implementers |
| 2026-04-24 | Plan doc Task 1 Step 7 + spike API NOTE updated to reflect canonical sync `with srv.start_server(): yield srv` pattern (verified at `vendor/serena/src/solidlsp/ls.py:717` and existing `test/solidlsp/scala/test_scala_language_server.py:24`). | Same defect was baked into the plan; future re-reads would reproduce the bug. Fixed at source. | All future spike work |
| 2026-04-24 | `LanguageServerConfig` field is `code_language`, NOT `language`. Conftest fix folded into Task 2 submodule commit. | Task 1 conftest had `LanguageServerConfig(language=Language.RUST)` which raised `TypeError`. Verified canonical name at `src/solidlsp/ls_config.py:596` and confirmed in `test/solidlsp/scala/test_scala_language_server.py`. | Conftest + all future spike fixtures |
| 2026-04-24 | **Wrapper `$/progress` plumbing requires a +30 LoC notification-tap shim** (plan §13 fallback). The dispatcher at `solidlsp/ls_process.py:507` is single-callback-per-method (last-write-wins); `rust_analyzer.py:720` pre-registers `do_nothing` for `$/progress` during `_start_server()`, swallowing 140-180 rich progress events per init. Public-API client taps registered after `start_server()` yields see 0 events. The JSON-RPC layer DOES forward all packets — only the dispatch surface is the bottleneck. | Discovered during S1 by wrapping `server._notification_handler` BEFORE `start()` on a second instance (probe 2). Outcome A confirmed with rich token set: rustAnalyzer/{Fetching, Building CrateGraph, Loading proc-macros, cachePriming, Roots Scanned, Building compile-time-deps}, rust-analyzer/flycheck/N. | Stage 1A `wait_for_indexing()` design + S2/S3/S4/S5/S6 spike implementers (same dispatcher pattern affects every notification-listening spike) |
| 2026-04-24 | Spike tests on this host must `os.environ.setdefault("CARGO_BUILD_RUSTC", "rustc")` BEFORE booting rust-analyzer. | Host `~/.cargo/config.toml` has `[build] rustc = "rust-fv-driver"` which crashes on missing dylib (`librustc_driver-f9453740c55d2f61.dylib`), aborting `cargo metadata` during rust-analyzer's project-model load. Without the env override, `_start_server()` partially succeeds but emits 0 progress events. | All Rust spikes (S1-S6) |

## Problems / blockers log

(none yet)

## Spike outcome quick-reference

| Spike | Outcome | LoC delta vs. optimistic |
|---|---|---|
| S1 | A (with shim caveat) | +30 LoC (notification-tap shim per plan §13 fallback) |
| S2 | — | — |
| S3 | — | — |
| S4 | — | — |
| S5 | — | — |
| S6 | — | — |
| P1 | — | — |
| P2 | — | — |
| P3 | — | — |
| P3a | — | — |
| P4 | — | — |
| P5a | — | — |
| P6 | — | — |
| P-WB | — | — |
| **Total** | **TBD** | **TBD vs. budgeted +250 LoC** |

## Stage 1 entry verdict

⏳ pending — set after Task 16 (SUMMARY.md) completes.

---

## How to update this file

After every task transition (start → end, status change, commit, decision):

1. Update the **Per-task ledger** row (status emoji + commit hash + one-line outcome).
2. If a decision was made, append to **Decisions log**.
3. If a problem hit, append to **Problems / blockers log**.
4. If a spike completed, fill the **Spike outcome quick-reference** row.
5. Commit this file alongside the work.

Subagents must read this file first when (re-)dispatched and must update it before reporting DONE.
