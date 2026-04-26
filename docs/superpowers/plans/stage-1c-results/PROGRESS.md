# Stage 1C — LSP Pool + Discovery — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1c-lsp-pool-discovery (parent + submodule)
Author: AI Hive(R)
Built on: stage-1b-applier-checkpoints-transactions-complete

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0  | Bootstrap branches + ledger                                            | 8f0bcd1 | OK | — |
| T1  | LspPoolKey frozen dataclass + Path.resolve canonicalisation            | 6cf71af1 | OK | — |
| T2  | LspPool skeleton (acquire/release lazy spawn; per-key Lock)            | 13e46e1e + fix 430aedfd | OK | post-T2 fix `430aedfd` removed dead `_t1c_threading` import, corrected `_start_cm` return type to `AbstractContextManager[MagicMock]`, refactored `shutdown_all` to iterate `entries.values()` (drops unused `_key`), and added `del` consumption for `_stop`/`_ping` mock side-effect args (Pyright info-level cleanup; T1+T2 stayed 14/14 green). |
| T3  | Idle-shutdown reaper (O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS)            | b277d67e | OK | — |
| T4  | pool_pre_ping (workspace/symbol echo + spawn replacement)              | 6136a4b2 | OK | — |
| T5  | RAM-budget guard (psutil-or-fallback; WaitingForLspBudget)             | 09be2d2f | OK | — |
| T6  | discovery.py + O2_SCALPEL_DISABLE_LANGS filter                         | 3c3e9e53 | OK | — |
| T7  | Pool ↔ TransactionStore acquire-affinity                               | ffac2c25 | OK | — |
| T8  | Telemetry (.serena/pool-events.jsonl)                                  | e3bf68d2 | OK | — |
| T9  | End-to-end: 2 MVP LSPs + crash-replace + idle-reap under §16 ceiling   | 35c15dd4 | OK | basedpyright + ruff LSP integration deferred to Stage 1E after their adapters land (SUMMARY §5). On this host: rust-analyzer ~10 s, pylsp ~5 s, aggregate RSS <2 GB on calcrs_seed+calcpy_seed fixtures, well under 4 GB ceiling. All three sub-tests pass: spawn (2 active servers), crash-replace (pre-ping detects dead, respawns), idle-reap (compresses 2 s window, reaper reclaims). |
| T10 | Submodule ff-merge to main + parent pointer bump + tag                 | submodule main `5d4e4af6` / parent develop `4cc4c0a` | OK | Submodule ff-merged to `main` and pushed (ba7e62b1..5d4e4af6); parent develop merged via git-flow (`4cc4c0a`); tag `stage-1c-lsp-pool-discovery-complete` pushed; spike-suite 185/185 green. Step 4 (`git add vendor/serena`) was a no-op because the parent submodule pointer was already advanced to `5d4e4af6` by post-T9 commit `26cbfea`. |

## Decisions log

(append-only; one bullet per decision with date + rationale)

## Stage 1B entry baseline

- Submodule `main` head at Stage 1C start: `ba7e62b1` (Stage 1B T10/T13 inverse-synthesis fix; submodule had no Stage 1B tag locally — derived from feature-branch parent commit)
- Parent `develop` head at Stage 1C start: `3484bec` (`Merge branch 'feature/stage-1b-applier-checkpoints-transactions' into develop`)
- Stage 1B tag: `stage-1b-applier-checkpoints-transactions-complete`
- Stage 1A + 1B spike-suite green: 130/130 (per Stage 1B PROGRESS.md final verdict)

## Spike outcome quick-reference (carryover for context)

- Stage 1A T11 → `is_in_workspace()` adopted verbatim into Stage 1B applier; Stage 1C does not re-touch boundary checks.
- Stage 1A T10 → `override_initialize_params()` is the chokepoint Stage 1C uses to inject per-pool isolated cache paths (§16.5) at spawn.
- Stage 1B T11/T12 → `CheckpointStore.LRU(50)` + `TransactionStore.LRU(20)` are the substrate Stage 1C T7 binds to.
- §16.1/§16.2/§16.4/§16.5 → drive the four pool knobs (RAM ceiling, disable-langs, idle shutdown, cache isolation) wired in T3/T5/T6.

## Stage 1C — final verdict

- All 11 tasks (T0–T10) complete.
- Submodule `vendor/serena` main: `5d4e4af6`.
- Parent `develop` head: `4cc4c0a`.
- Tag: `stage-1c-lsp-pool-discovery-complete`.
- Spike-suite green: ~185+ (Phase 0 + Stage 1A + Stage 1B + Stage 1C).
- LoC delta vs Stage 1B: ~+290 logic (lsp_pool.py +180, discovery.py +110),
  ~+620 test, +2 production files (refactoring/lsp_pool.py,
  refactoring/discovery.py), +9 new test files, +24 LoC conftest fixture
  delta, +6 LoC __init__.py re-exports.

**Stage 1D entry approval**: PROCEED. The multi-server merge consumes
LspPool.acquire_for_transaction (T7) for transactional fan-out across the
three Python LSPs; Stage 1E's LanguageStrategy activation map consumes
discover_sibling_plugins (T6) + enabled_languages.
