# Stage 1C — LSP Pool + Discovery — Progress Ledger

Started: 2026-04-25
Branch: feature/stage-1c-lsp-pool-discovery (parent + submodule)
Author: AI Hive(R)
Built on: stage-1b-applier-checkpoints-transactions-complete

| Task | Description | Branch SHA (submodule) | Outcome | Follow-up |
|---|---|---|---|---|
| T0  | Bootstrap branches + ledger                                            | 8f0bcd1 | OK | — |
| T1  | LspPoolKey frozen dataclass + Path.resolve canonicalisation            | 6cf71af1 | OK | — |
| T2  | LspPool skeleton (acquire/release lazy spawn; per-key Lock)            | 13e46e1e | OK | — |
| T3  | Idle-shutdown reaper (O2_SCALPEL_LSP_IDLE_SHUTDOWN_SECONDS)            | _pending_ | _pending_ | — |
| T4  | pool_pre_ping (workspace/symbol echo + spawn replacement)              | _pending_ | _pending_ | — |
| T5  | RAM-budget guard (psutil-or-fallback; WaitingForLspBudget)             | _pending_ | _pending_ | — |
| T6  | discovery.py + O2_SCALPEL_DISABLE_LANGS filter                         | _pending_ | _pending_ | — |
| T7  | Pool ↔ TransactionStore acquire-affinity                               | _pending_ | _pending_ | — |
| T8  | Telemetry (.serena/pool-events.jsonl)                                  | _pending_ | _pending_ | — |
| T9  | End-to-end: 4 MVP LSPs + crash-replace + idle-reap under §16 ceiling   | _pending_ | _pending_ | — |
| T10 | Submodule ff-merge to main + parent pointer bump + tag                 | _pending_ | _pending_ | — |

## Decisions log

(append-only; one bullet per decision with date + rationale)

## Stage 1B entry baseline

- Submodule `main` head at Stage 1C start: <fill in via `git -C vendor/serena rev-parse main` at T0 close>
- Parent `develop` head at Stage 1C start: <fill in via `git rev-parse develop`>
- Stage 1B tag: `stage-1b-applier-checkpoints-transactions-complete`
- Stage 1A + 1B spike-suite green: 130/130 (per Stage 1B PROGRESS.md final verdict)

## Spike outcome quick-reference (carryover for context)

- Stage 1A T11 → `is_in_workspace()` adopted verbatim into Stage 1B applier; Stage 1C does not re-touch boundary checks.
- Stage 1A T10 → `override_initialize_params()` is the chokepoint Stage 1C uses to inject per-pool isolated cache paths (§16.5) at spawn.
- Stage 1B T11/T12 → `CheckpointStore.LRU(50)` + `TransactionStore.LRU(20)` are the substrate Stage 1C T7 binds to.
- §16.1/§16.2/§16.4/§16.5 → drive the four pool knobs (RAM ceiling, disable-langs, idle shutdown, cache isolation) wired in T3/T5/T6.
