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

## Phase C — gates (status: READY TO PLAN)

Phase B uplift captured above. Phase C plan will introduce per-module
floors and `diff-cover --fail-under=90` on PR diffs. Triggered after
Phase B raises numbers. See spec §6 Phase C for
per-module floors (`tools` 80, `refactoring` 85/70, `plugins` 75,
`solidlsp` 70) + diff-cover at 90% on PR diffs.

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
