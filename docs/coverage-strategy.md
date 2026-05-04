# Coverage strategy — operational dashboard

**Spec authority:** [`docs/superpowers/specs/2026-05-03-test-coverage-strategy-design.md`](superpowers/specs/2026-05-03-test-coverage-strategy-design.md)

This doc is the **living state** of coverage. Update it whenever Phase A
baseline rolls forward, Phase B closes a hit-list row, or Phase C gates
move floors.

## Phase A — baseline (captured 2026-05-03) ✅ COMPLETE

### Per-module coverage (non-e2e suite, `O2_SCALPEL_RUN_E2E` unset)

| Module | Line % | Branch % |
|---|---|---|
| `serena.tools` | 55.65% | 36.07% |
| `serena.refactoring` | 64.18% | 38.80% |
| `serena.plugins` | 91.36% | 75.00% |
| `solidlsp` | 74.14% | 48.75% |

**Aggregate (all instrumented modules combined):** 64.61% line, 21,064 statements, 6,433 missed.

**Test suite size:** 2,006 passed, 159 skipped, 9 xfailed, 10 xpassed (post-SQ1 fixture-coord fix).

Reproduce locally:

```bash
cd vendor/serena && \
  uv run pytest -n auto --cov --cov-branch --cov-report=term-missing \
    --ignore=test/e2e --ignore=test/spikes
```

**Caveat — `solidlsp` may be slightly underreported.** `coverage.py` warns
`Module solidlsp was previously imported, but not measured` on some
pytest-xdist workers. Workers can import the package before coverage
instruments it; affected branches show as missed. To get a single-process
reference number, re-run without `-n auto`:

```bash
cd vendor/serena && \
  uv run pytest --cov=solidlsp --cov-branch \
    --ignore=test/e2e --ignore=test/spikes test/solidlsp
```

The xdist numbers are accepted as Phase A baseline because they're stable
under the same CI configuration (PR-to-PR comparability matters more than
absolute precision in this phase).

### Vulture findings (dead-code surface, `--min-confidence 80`)

- **Total findings:** 3
- **Top files:**
  - `src/serena/tools/tools_base.py` — 2 findings
  - `src/solidlsp/language_servers/typescript_language_server.py` — 1 finding

Full list:

| File:line | Finding | Confidence |
|---|---|---|
| `src/serena/tools/tools_base.py:17` | unused import `MemoriesManager` | 90% |
| `src/serena/tools/tools_base.py:24` | unused import `SerenaAgent` | 90% |
| `src/solidlsp/language_servers/typescript_language_server.py:33` | unused variable `uid` | 100% |

Reproduce locally:

```bash
cd vendor/serena && uv run vulture \
  src/serena/tools src/serena/refactoring src/serena/plugins src/solidlsp \
  --min-confidence 80
```

**Phase A discipline:** findings catalogued only. Phase B (next plan)
decides delete-vs-annotate per-finding (spec §6 Phase B row B6).

### Side-quests surfaced during Phase A

- **SQ1 — fixture line-coord drift fixed** (engine commit `5540173b`,
  parent commit `08d88bf`). 4 pre-existing failures in
  `test/solidlsp/python/` traced to `models.py` and
  `examples/user_management.py` fixture file growth shifting class/method
  positions. Tests updated to use new 0-indexed coordinates. Surfaced by
  T3 baseline run; would have remained latent in pre-Phase-A CI matrix.

## Phase B — gap-fill (status: NOT STARTED)

Triggered after Phase A baseline is committed. See spec §6 Phase B for
the 7-row bug-history hit list (B1–B7). A separate plan
(`docs/superpowers/plans/<date>-test-coverage-phase-b.md`) will be drafted
once this baseline is in place.

The 3 catalogued vulture findings above feed directly into B6
(delete-or-annotate decision).

## Phase C — gates (status: NOT STARTED)

Triggered after Phase B raises numbers. See spec §6 Phase C for
per-module floors (`tools` 80, `refactoring` 85/70, `plugins` 75,
`solidlsp` 70) + diff-cover at 90% on PR diffs.

**Gap to Phase C floors (from Phase A baseline):**

| Module | Phase A line | Phase C line floor | Gap |
|---|---|---|---|
| `serena.tools` | 55.65% | 80% | **+24.35pp needed** |
| `serena.refactoring` | 64.18% | 85% | **+20.82pp needed** |
| `serena.plugins` | 91.36% | 75% | already over (+16.36pp headroom) |
| `solidlsp` | 74.14% | 70% | already over (+4.14pp headroom) |

`serena.refactoring` also needs branch coverage to climb from 38.80% to
70% (+31.20pp) — the largest single gap. Phase B's B3 (rollback inverse
applier property test) and B4 (WorkspaceEdit applier idempotence) target
this module directly and should close the bulk of that branch gap.

## Ratchet history

| Date | Module | Line % | Branch % | Trigger |
|---|---|---|---|---|
| 2026-05-03 | `serena.tools` | 55.65% | 36.07% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `serena.refactoring` | 64.18% | 38.80% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `serena.plugins` | 91.36% | 75.00% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `solidlsp` | 74.14% | 48.75% | Phase A baseline (spec 2026-05-03) |
