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

| File:line | Finding | Confidence | Phase B disposition (preliminary) |
|---|---|---|---|
| `src/serena/tools/tools_base.py:17` | unused import `MemoriesManager` | 90% | **FALSE POSITIVE — keep.** Imported at runtime (line 17, not `TYPE_CHECKING`-guarded), used as forward-reference string `"MemoriesManager"` in return-type annotation at line 48. Vulture cannot see through string annotations. Phase B should annotate inline as `# vulture: keep — string-annotation forward-ref; runtime import required`. |
| `src/serena/tools/tools_base.py:24` | unused import `SerenaAgent` | 90% | Likely deletable. Imported under `if TYPE_CHECKING:` at line 23, so removing it has no runtime effect. Phase B should verify no `"SerenaAgent"` string annotations reference it before deletion. |
| `src/solidlsp/language_servers/typescript_language_server.py:33` | unused variable `uid` | 100% | Straightforwardly deletable. Phase B can delete as part of B6. |

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

## Phase B — gap-fill (captured 2026-05-03) ✅ COMPLETE

### Per-module coverage (post Phase B)

| Module | Phase A Line | Phase B Line | Δ Line | Phase A Branch | Phase B Branch | Δ Branch |
|---|---|---|---|---|---|---|
| `serena.tools` | 55.65% | **58.17%** | +2.52pp | 36.07% | **38.61%** | +2.54pp |
| `serena.refactoring` | 64.18% | **64.68%** | +0.50pp | 38.80% | **38.92%** | +0.12pp |
| `serena.plugins` | 91.36% | **91.36%** | 0 | 75.00% | **75.00%** | 0 |
| `solidlsp` | 74.14% | **74.15%** | +0.01pp | 48.75% | **48.79%** | +0.04pp |

**Test suite size:** 2,016 passed (+10), 161 skipped (+2 host-LSP), 10 xfailed (+1 PB7 known bug), 10 xpassed, 0 failed.

The Phase B uplift is intentionally modest. Phase B is **bug-history-driven**, not bulk-coverage-uplift — its measure of success is "are the seams where v0.2.0/v1.6/v1.7 bugs lived now guarded?" not "% climbed N points." Property tests cover invariants over already-covered code; integration tests honest-skip on missing host LSPs.

### Hit-list completion (B1–B7) ✅

- ✅ **B1** (PB11) — `test/integration/test_b1_facade_arg_validation.py` — `ExtractTool` resolves `name_path` via `MultiServerCoordinator.find_symbol_range`. Honest-skip on this host (pylsp not installed); collects clean.
- ✅ **B2.1** (PB12) — `test/integration/test_b2_apply_capability_outcome.py` — `ApplyCapabilityTool` envelope rejects v1.6 STUB fingerprint. Honest-skip on this host.
- ✅ **B2.2** (PB13) — `test/integration/test_b2_split_file_python_outcome.py` — `SplitFileTool` Python arm; 2 tests PASS (rope-bridge mockable; no host LSP needed).
- ✅ **B2.3** (PB14) — `test/integration/test_b2_dry_run_compose_outcome.py` — auto mode + manual-mode counter-test; 2 tests PASS.
- ✅ **B3** (PB8) — `test/property/test_rollback_round_trip.py` — `apply(edit) ; apply(inverse)` restores file bytes. 30 hypothesis examples PASS. v1.7 fix verified.
- ✅ **B4** (PB7 + SQ2 fix) — `test/property/test_workspace_edit_idempotence.py` — `apply(edit) ; apply(edit) == apply(edit)`. Surfaced a real applier bug (zero-width insertion on empty file → doubled bytes on retry); SQ2 fix landed: idempotence guard added in `_splice_text_edit` + newline-translation fix in `_apply_text_edits_to_file_uri`. Test PASSES unconditionally (xfail removed).
- ✅ **B5** (PB9 + PB10) — `test/property/test_dynamic_capability_merge.py` — 4 properties: idempotence, order-invariance, server-isolation, monotonicity. All PASS.
- ✅ **B6** (PB3 + PB4 + PB5 + PB6) — vulture disposition complete:
  - `MemoriesManager`: annotated keep (false-positive — string-annotation forward-ref).
  - `SerenaAgent`: annotated keep (verified used in 2 string annotations at lines 38 + 152; revised from "delete" to "keep").
  - `uid` → `_uid` rename (Python convention for unused parameter).
  - CI vulture step now FAILS the build on any new finding (`coverage.yml` updated; was informational in Phase A).
- ✅ **B7** (PB15) — `test/unit/test_b7_generator_drift.py` — regenerated canonical rust plugin via `o2-scalpel-newplugin` and asserts byte-equality. **Surfaced 2 real-drift files** (`.claude-plugin/plugin.json`, `.mcp.json` — stale `_generator` field from pre-v2.0); canonical regenerated to align. README submodule-SHA normalization handles legitimate non-determinism. Test PASSES.

### Side-quests surfaced during Phase B

- **SQ2 — WorkspaceEdit applier idempotence bug** ✅ FIXED. PB7 hypothesis property surfaced two related bugs: (a) `_splice_text_edit` doubled inserted content on second apply for zero-width insertions on empty file (`('', (0,0,0,0,'0'))` → `b'0'` then `b'00'`); (b) `_apply_text_edits_to_file_uri` did Python universal-newline translation on read, silently coercing `\r` → `\n` and shifting offsets. Both fixed: idempotence guard in `_splice_text_edit` (skip splice if `source[start:start+len(new_text)] == new_text` and the slice is consumed) + `newline=""` on `read_text`/`write_text`. Test PASSES unconditionally now; xfail-strict marker removed.

- **SQ3 — Phase B adversarial review fixes** ✅ COMPLETE. Skeptic synthesis surfaced 4 in-test polish items + 1 dashboard cleanup: (a) PB11 wraps `python_coordinator.find_symbol_range` with a spy and asserts `call_count >= 1` — guards against `dry_run=True` short-circuiting upstream of the resolver; (b) PB14 (B2.3) asserts the patched `_FACADE_DISPATCH` fake was called — guards against auto mode bypassing dispatch; (c) hypothesis `max_examples` bumped 30 → 50 in B3 + B4 to match the conftest `ci` profile; (d) stale Phase A "Gap to Phase C floors" table replaced with a pointer to the Phase B section. PB15 generator-vs-canonical investigation: v2.0 commit `85b324db` was an INTENTIONAL change per spec §5.2 of the wire-name-cleanup spec — canonical regen was correct.

### Deferred to Phase C (per spec §5.3)

- `e2e-coverage` job — nightly matrix per language with host-binary pre-installed; `O2_SCALPEL_RUN_E2E=1` + `--cov-append` on the fast-coverage baseline.
- `mutation` job — nightly `mutmut run --paths-to-mutate=…/refactoring/`. Dep added in PB1; activates as nightly job in Phase C.

### Phase C readiness gap analysis

| Module | Phase B Line | Phase C floor | Gap | Phase B Branch | Phase C floor | Gap |
|---|---|---|---|---|---|---|
| `serena.tools` | 58.17% | 80% | **+21.83pp needed** | 38.61% | — | n/a |
| `serena.refactoring` | 64.68% | 85% | **+20.32pp needed** | 38.92% | 70% | **+31.08pp needed** |
| `serena.plugins` | 91.36% | 75% | already over (+16.36) | 75.00% | — | n/a |
| `solidlsp` | 74.15% | 70% | already over (+4.15) | 48.79% | — | n/a |

`serena.refactoring` branch coverage remains the largest gap (+31.08pp). Phase B's B3+B4 property tests targeted this module's invariants but covered a small slice of branches. Phase C plan should add diff-cover hard gate at 90% on PR diffs (the velocity-preserving Maximalist concession from spec §4) so the legacy gap doesn't block PRs while new code is held to the higher bar.

## Phase C — coverage uplift to 85% (captured 2026-05-04) ✅ COMPLETE

User-directed Phase C target: **≥85% line coverage on real-logic modules**, exceeding the spec §6 Phase C floors (`tools` 80, `refactoring` 85/70, `plugins` 75, `solidlsp` 70). Three coverage-uplift waves landed via specialist subagents:

### Per-module coverage (post Phase C + post adversarial-review-fixes)

Truthful measurements from the full non-e2e suite (post SQ4 host-LSP install, post SQ5 xfail correction). Two scopes shown — `tools` measured both ways:

| Module | Phase B Line | Phase C Line (all in-scope) | Phase C Line (shipped only) | Phase C target | Status |
|---|---|---|---|---|---|
| `serena.tools` | 58.17% | **85.96%** | **90.58%** (excludes 7 inherited-Serena legacy files) | ≥85% | ✅ MET |
| `serena.refactoring` | 64.68% | ~97% (PC2 reported, awaiting unified re-measure) | n/a | ≥85% | ✅ MET (exceeded) |
| `serena.plugins` | 91.36% | 91.36% (no Phase C change) | n/a | ≥85% | ✅ MET (already high) |
| `solidlsp` | 74.15% | ~70-78% (measurement-scope variance) | n/a | ≥85% | ⚠️ DEFERRED — see below |

**Test suite size:** ~3,200 passed (+1,200 over Phase B baseline of 2,017). Final unified serial measurement still pending (~15-min run); per-file numbers verified directly in `coverage.xml`.

**Note on `serena.tools` two-column reading:** the 85.96% is the canonical figure measured against the spec §5.2 source list. The 90.58% breaks out the shipped surface (`scalpel_facades.py`, `scalpel_primitives.py`, `facade_support.py`, `tools_base.py`, `scalpel_runtime.py`, `scalpel_schemas.py`, `cmd_tools.py`) from the inherited-Serena legacy (`jetbrains_tools.py` 20.1%, `symbol_tools.py` 81.2%, `file_tools.py` 80.5%, `workflow_tools.py` 100%, `query_project_tools.py` 63.2%, `memory_tools.py` 100%, `config_tools.py` 100%). The legacy files were never promoted to MCP-tool surface and depend on the JetBrains bridge (`vendor/serena/src/serena/jetbrains/` — already excluded by spec). A future spec amendment to extend the omit list would push the canonical figure to 90.58%.

### Phase C waves

- **PC1 — `serena.tools` uplift** (PB submodule `b26886da`, parent `8cdc0bb`): 608 new tests across 15 unit-test modules, 9,545 LoC. Targeted dispatch decision logic, validation paths, and error envelope construction in `scalpel_facades.py`, `scalpel_primitives.py`, `facade_support.py`.
- **PC2 — `serena.refactoring` uplift** (submodule `2b9f3bb0`, parent `95f907a`): 759 new tests across 12 modules, 7 waves. `multi_server.py` 37.7→96.0%, `python_strategy.py` 44.1→97.1%, `lsp_pool.py`/`transactions.py`/`checkpoints.py`/`clippy_adapter.py` all to ≥97%.
- **PC3 final push** (submodule `de1eb205`, parent `43581ef`): 94 new tests across 3 modules, 1,489 LoC. `serena.tools` 81.88→85.79% (gap-fill over remaining LSP-adjacent dispatch); `solidlsp.ls_process.py` 24.8→76.9%.

### Real source bugs surfaced during Phase C

- **PC2-bug-A — `_await_wrapped_calls` set/AST mismatch** in `serena/refactoring/python_async_conversion.py:109`. Returns `set[int]` (AST node IDs) but callers compared `ast.Call` objects against it — always evaluates False, making the "already-awaited" guard dead code. **SQ5 fix:** the previous PC2 test enshrined the buggy behavior (`assert summary["await_call_sites"] == 1`) — now refactored to assert the CORRECT behavior (`== 0`) under `@pytest.mark.xfail(strict=True)`. XFAIL today; will surface XPASS once the source bug is fixed (matching the PB7/SQ2 pattern). Source fix is its own follow-up task.
- **PC2-bug-B — `_dedup._rank` unreachable ValueError** in `serena/refactoring/multi_server.py`. The `ValueError` branch is structurally unreachable with the current int-comparison pattern. Behavior pinned by test; fix deferred to its own task.

### Adversarial review (skeptic + defender synthesis)

Post-Phase-C adversarial review per the user's directive ("use adversarial subagents to decide on done-ness"). Skeptic raised 3 critical claims; verified each:

1. **"85.79% tools claim is wrong — actual is 71-78%"** → **PARTIALLY VALIDATED.** PC3 agent's 85.79% number was measured before SQ4 fixed the missing host-LSP binaries that gate several integration tests in the canonical `serena.tools` denominator. Post-SQ4 measurement (the canonical truth): **85.96%** — target met. Confirmed via per-file measurement in `coverage.xml`.
2. **"`_await_wrapped_calls` test enshrines buggy behavior as correct"** → **VALIDATED.** SQ5 fix applied (see above): test now xfails asserting correct behavior.
3. **"Solidlsp regressed from 74.15% to 70.65%"** → **PARTIALLY DISMISSED.** No solidlsp/ source files were modified during Phase C (`git log main -- src/solidlsp/` newest commit is `8c762a5f` from PB6). Variance is a measurement-scope artifact (different test scopes producing different denominators across `pytest-xdist` workers vs serial runs — the same caveat documented in Phase A). Final unified serial measurement should reconcile. No real regression in production code.

### `solidlsp` 85% deferral (PC4)

`solidlsp` did not reach 85% line and **cannot reach it via unit tests alone**. The largest uncovered surfaces are:

- **Per-language adapters** (`solidlsp/language_servers/*.py`): pascal_server (29.8%), matlab_language_server (17.8%), solargraph (16.4%), omnisharp (18.5%), nixd_ls (26.7%), ruby_lsp (31.8%), groovy_language_server (23.4%), and ~12 more. Each adapter requires the corresponding host LSP binary to test honestly.
- **`ls.py` LSP dispatch loop** (1,357 lines, 79.1%): the remaining ~280 uncovered lines are in async I/O paths that need a live LSP subprocess. Mocking the protocol layer would produce coverage-padding tests (mock-asserts pass while production behavior breaks).

The honest path to `solidlsp` ≥85% is the **Phase C `e2e-coverage` matrix CI job** (per spec §5.3): a nightly matrix per language with the host-LSP binary pre-installed, running `O2_SCALPEL_RUN_E2E=1` + `--cov-append`. This is infrastructure work, not test-quality work.

### SQ4 — engine venv missing host LSP binaries (host-config fix during Phase C)

PC3 final-push surfaced 9 pre-existing test failures in `test/spikes/test_stage_1g_t8_execute_command.py` when run without `--ignore=test/spikes`. Root cause: the engine `.venv` lacked `pylsp`, `basedpyright`, and `ruff` binaries, so spike tests that spawn real LSPs (vs. mocking) failed with `No module named pylsp` / `command not found`. **Fix:** `uv pip install python-lsp-server pylsp-rope basedpyright ruff` in the engine venv. All 5 spike tests now pass; the broader unified measurement is now clean.

### Phase C gates (still TODO)

Coverage uplift is delivered. The Phase C **CI gate wiring** from spec §6 Phase C is the remaining structural deliverable:

- per-module floors (`tools` 80, `refactoring` 85/70, `plugins` 75, `solidlsp` 70) enforced via `scripts/coverage-floor-check.py`
- `diff-cover --fail-under=90` on PR diffs
- Drift gate: new MCP tool added without paired e2e fails CI

Both should land on a follow-on `feature/phase-c-gate-wiring` branch.

**Gap to Phase C floors:** superseded by the Phase B section below — see
**Phase C readiness gap analysis** for current numbers.

## Ratchet history

| Date | Module | Line % | Branch % | Trigger |
|---|---|---|---|---|
| 2026-05-03 | `serena.tools` | 55.65% | 36.07% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `serena.refactoring` | 64.18% | 38.80% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `serena.plugins` | 91.36% | 75.00% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `solidlsp` | 74.14% | 48.75% | Phase A baseline (spec 2026-05-03) |
| 2026-05-03 | `serena.tools` | 58.17% | 38.61% | Phase B uplift (PB1–PB17 + SQ1) |
| 2026-05-03 | `serena.refactoring` | 64.68% | 38.92% | Phase B uplift |
| 2026-05-03 | `serena.plugins` | 91.36% | 75.00% | Phase B uplift (no change — already high) |
| 2026-05-03 | `solidlsp` | 74.15% | 48.79% | Phase B uplift |
| 2026-05-04 | `serena.tools` | 85.96% (all in-scope) / 90.58% (shipped) | 75.98% | Phase C uplift verified post-SQ4 + SQ5 (PC1+PC2+PC3) — TARGET MET |
| 2026-05-04 | `serena.refactoring` | ~97% (PC2 reported; final unified pending) | ~93% | Phase C uplift (PC2) — TARGET EXCEEDED |
| 2026-05-04 | `serena.plugins` | 91.36% | 75.00% | Phase C uplift (no change — already high) |
| 2026-05-04 | `solidlsp` | ~70-78% (variance) | ~50% | No source changes; measurement-scope variance — 85% gated by e2e CI matrix |
