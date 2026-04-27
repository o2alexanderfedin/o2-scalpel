# FINAL REVIEW REPORT — Post v0.2.0 Follow-ups

**Date**: 2026-04-27
**Tag reviewed**: `stage-v0.2.0-followups-complete` (parent `0435ac8`, submodule `a2cece4a`)
**Author**: AI Hive(R)
**Provenance**: Synthesized output of a 3-round pair-programming review across 4 specialist inputs (code, plan, test, doc) + a coordinator thread. See Process footer.

---

## Executive Summary

The v0.2.0 follow-ups batch (Leaves 01-05) shipped cleanly: all four specialists independently confirm the leaves landed in code, plans, tags, and `WHAT-REMAINS.md`. **Closure stands MODULO two critical gaps**:

1. `pytest-asyncio` is missing from `vendor/serena/.venv`, which means L03's centerpiece parallelism integration test silently FAILS at runtime — the headline "Amdahl-aware budget" guarantee is unverified on this host (`vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:122`).
2. The `2026-04-26-decision-p5a-mypy.md` plan is fully drafted but UNEXECUTED, leaving three artifacts (`docs/superpowers/plans/spike-results/P5a.md`, `docs/superpowers/plans/spike-results/PROGRESS.md`, `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:154`) in active disagreement.

Both fixes are small (one config line; ~30 LoC + ~95 LoC tests). Beyond the criticals, the synthesis surfaces **10 important** issues (mostly code-quality polish, plan-vs-impl drift, and a leverage opportunity to generalize L05's strip-the-skip pattern to 13 other facades) and **12 minor** docs-hygiene items.

**Bottom line**: shipping the closure as-is is **NOT recommended**. Land pytest-asyncio first to validate the L03 claim, ratify the P5a decision second, then proceed to important/minor cleanup.

---

## Where We Stand

- **v0.2.0 follow-ups batch (Leaves 01/02/03/04/05) shipped**: confirmed by all 4 specialists. `WHAT-REMAINS.md:102-114` correctly cites paths and tags. Submodule + parent tags match (`stage-v0.2.0-followups-complete`).
- **Outstanding work surfaced by review**: **2 Critical** / **10 Important** / **12 Minor** + **3 cross-cutting themes** + **1 process scope note**.
- **Tests/code/plans/docs alignment**: Code is clean (0/0/0 pyright on all touched files, with zero ★-info hints). Tests pass in isolation but the async corpus is silently red. Plans are stale (no post-shipment STATUS banners; L04 prescribes a rejected mechanism). Docs closure was applied to `WHAT-REMAINS.md` and `D-debt.md` but CHANGELOG, MVP scope report, and per-leaf plan files were not refreshed.

---

## What's NOT Wrong (Closure Stands)

Defensive ledger — items the specialists positively confirmed are clean. A casual reader of the Critical/Important sections should not infer the closure is broken; the foundation is solid.

1. **Touched-area pyright is 0/0/0** — Specialist 1 (code) confirms zero errors on every file touched by Leaves 02-05.
2. **Zero ★-info hints in touched files** — Specialist 1 explicitly records "no ★ pyright info hints in the touched files (clean per the project's 'all errors must be fixed' rule)." This is the user's stricter convention per `feedback_pyright_diagnostics.md` and is the load-bearing closure signal.
3. **L01–L05 closure annotations in `WHAT-REMAINS.md` are accurate** — Specialists 2 (plan) and 4 (doc) independently verified each path/tag/SHA reference resolves.
4. **`docs/dev/host-rustc-shim.md` is accurate** — Specialist 4 confirms the new dev doc matches the implementation in `vendor/serena/test/conftest_dev_host.py`.
5. **Working-tree status flags are non-substantive divergences**:
   - The 3 spike-result files (`docs/superpowers/plans/spike-results/{P5a,S1,S4}.md`) carry stale workdir `M`-flags but inspection shows no real content divergence.
   - The `vendor/serena` submodule `M`-flag is the **expected** post-tag pointer (working SHA `a2cece4a` past `stage-v0.2.0-followups-complete`); not noise.

If a reader sees only the Critical/Important list and skips this section, they will overweight the work remaining. The five items above hold.

---

## Critical Issues (must fix before next stage)

### C1: `pytest-asyncio` not installed — L03 closure claim unverified

- **What**: `vendor/serena/.venv` has `anyio` + `nest-asyncio` but NOT `pytest-asyncio`. `vendor/serena/pyproject.toml [tool.pytest.ini_options]` does not set `asyncio_mode = "auto"`. As a result, every `@pytest.mark.asyncio` test fails at runtime with "async def functions are not natively supported", but pytest only emits `PytestUnknownMarkWarning` at collection — silent failure.
- **Evidence**: Specialist 3 (`docs/reviews/2026-04-27-post-v020-followups/03-test-coverage.md:23-39`); coordinator confirmation in Theme 2 + Conflict 1 (`10-coordinator-thread.md`).
  - `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:122` — the **only** integration test proving L03 multi-server parallelism — silently FAILS.
  - 35+ pre-existing async spike tests also silently red (Stage 1D fakes + spike T11 + v0.2.0-C suite).
  - `WHAT-REMAINS.md:104` claims "1 integration" runs as part of L03 closure; it does not.
- **Recommended action**: One-line fix. `cd vendor/serena && uv add --dev pytest-asyncio` and add `asyncio_mode = "auto"` to `pyproject.toml [tool.pytest.ini_options]`. Then re-run the integration test to validate.
- **Effort**: **S** (one config edit + verify).
- **Owner suggestion**: any agent with venv write access; verify via `superpowers:verification-before-completion`.

### C2: P5a triple-convergence — `decision-p5a-mypy.md` UNEXECUTED + spike-result internally inconsistent

- **What**: This is **one problem with three visible faces** (per coordinator cross-finding insight 1):
  1. **Plan**: `docs/superpowers/plans/2026-04-26-decision-p5a-mypy.md` has 5 tasks, all open (Specialist 2 §B, ~30 LoC + ~95 LoC governance tests).
  2. **Doc**: `docs/superpowers/plans/spike-results/P5a.md:3` verdict line says "Outcome C — DROP", but lines 9-12 measurements (0% stale, p95=4.306s) match Outcome B's "ship with documented warning" thresholds (Specialist 4, `04-doc-currency.md:145-160`).
  3. **Code**: `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:15,154` still says `pylsp_mypy enabled: False` per the original Outcome C; no `P5A_MYPY_DECISION` constant; no `solidlsp/decisions/` dir (Specialist 2 verification).
  - Drift propagates to `SUMMARY.md:25`, `PROGRESS.md:31,70,101`, `stage-1h-results/PROGRESS.md:94`.
  - L05 was supposed to depend on P5a ratification per `v020-followups/README.md:13` (Specialist 3 indirect).
  - Coordinator converging-signals citation: `10-coordinator-thread.md:23-29`.
- **Recommended action**: Execute the plan: ratify SHIP-with-warning (B) or hold-DROP (C) with explicit "verdict held despite re-run measurements; rationale: …" annotation, then propagate to all 4 doc artifacts + lock the verdict in `vendor/serena/src/solidlsp/decisions/p5a_mypy.py` per the plan's Task 1.
- **Effort**: **S-M** (5 tasks, mostly governance + cross-artifact propagation).
- **Owner suggestion**: requires a HUMAN decision call (see Open Questions §Q1) before execution.

---

## Important Issues (should fix soon)

### Code Quality

#### I1: `is_async_callable` Mock carve-out is too broad

- **Evidence**: Specialist 1 Important #1; `vendor/serena/src/serena/refactoring/_async_check.py:69`. `isinstance(obj, Mock)` silently passes ANY MagicMock instance, defeating the L03 "loud TypeError on raw sync misuse" gate for any future code that accidentally constructs a Mock.
- **Action**: Replace with marker-attribute opt-in: `getattr(obj, "_o2_async_callable", False)`. Update `vendor/serena/test/spikes/test_v0_2_0_c_find_symbol_position.py` (3 sites) to set the marker.
- **Effort**: **S** (~10 LoC + 3 test updates).

#### I2: Dead helpers `_classify_overlap` + `_bucket_unknown_kind` (TRIZ separation violation)

- **Evidence**: Specialist 1 Important #2; `vendor/serena/src/serena/refactoring/multi_server.py:516,562`. Both are referenced ONLY by `vendor/serena/test/spikes/test_stage_1d_t10_disagreements.py` — never wired into `merge_and_validate_code_actions` or `merge_code_actions` bucket key. §11.2 case-1 spec is silently absent from production.
- **Action**: Wire them in (preferred — restore the §11.2 invariant) OR delete both helpers + spike test. YAGNI either way. (See Open Questions §Q2.)
- **Effort**: **S** (delete) or **M** (wire properly, with new tests).

#### I3: `whole_file_range` dual-mode fixture footgun + plan-vs-impl drift

- **Evidence**: Specialist 1 Important #3 + Specialist 4 §Per-leaf L02. `vendor/serena/test/integration/conftest.py:186-221`. Unparametrized callers silently get `(0,0)..(10_000,0)` fallback — future tests against strict servers will hit `ValueError` at runtime. L02 plan prescribed single-mode; impl deviated to dual-mode without documenting the deviation.
- **Action**: Drop unparametrized fallback; migrate the one legacy caller in `vendor/serena/test/integration/test_smoke_python_codeaction.py` (verified to consume `whole_file_range` at line 22 + line 32) to `indirect=True` or a direct `compute_file_range` call.
- **Effort**: **S** (~5 LoC removal + 1 caller migration).

### Test Coverage

#### I4: 13-facade strip-the-skip pattern (L05 leverage opportunity)

- **What**: L05 fixed E1-py determinism by stripping a `pytest.skip("applied!=True")` fallback and adding a 10-iteration determinism guard. **The same anti-pattern lives in 13 other facade tests** (E2/E3/E4/E5/E8/E9/E10/E11/E13/E14/E15/E16) which still silently skip when `applied!=True`, masking the same class of flake L05 just diagnosed.
- **Evidence**: Specialist 3 §Pre-existing skips Important #7 (`03-test-coverage.md:188`); coordinator Theme 7 (`10-coordinator-thread.md:77`); synthesis input item 11 (`11-synthesis-input.md:34`). All three sources tag this **Important**, not Critical.
- **Action**: Apply L05 treatment leaf-by-leaf — strip skip + add N-iteration determinism guard per facade. Or batch into a "Stage 1H continuation prep" sub-leaf via map/reduce subagent (independent files, no shared state).
- **Effort**: **M** (13 facades × ~10 LoC each = ~130 LoC + verification runs).

#### I5: No end-to-end booted-rust-analyzer test for L02 preflight

- **Evidence**: Specialist 3 Important #4. All 3 preflight tests in `vendor/serena/test/solidlsp/rust/test_rust_analyzer_detection.py:575-654` bypass `__init__` via `RustAnalyzer.__new__(RustAnalyzer)` and patch `super().request_code_actions`. No real-LSP wire test exists. Mock-heaviness audit gives this class **HIGH** risk (Specialist 3 §Mock-heaviness audit).
- **Action**: Add test gated on `which rust-analyzer`; boot real RA, call with out-of-range `end`, assert `ValueError` raised with no LSP traffic.
- **Effort**: **S** (~30 LoC + CI gate).

#### I6: Promote 2 xpassed tests in `test_serena_agent.py`

- **Evidence**: Specialist 3 Critical #2; coordinator Conflict 4. `vendor/serena/test/serena/test_serena_agent.py:220,231,329,340` carry `@pytest.mark.xfail` for #1040 LSP unreliability; 2 of 4 xpassed in current run. Other 2 still xfail legitimately.
- **Action**: Remove the xfail decorator from the 2 that xpassed; document why in the commit. Locks the new contract — future regressions in F#/Rust/TS LSP support fail loudly.
- **Effort**: **S** (~4 LoC).

#### I7: No negative/mutation test for L05 determinism guard

- **Evidence**: Specialist 3 Critical #3. `vendor/serena/test/e2e/test_e2e_e1_py_determinism.py:49` assertion is unproven against the failure mode it claims to catch.
- **Action**: Monkeypatch `mcp_driver_python.split_file` to return `applied=False` once; assert the parametrize iteration fails loudly.
- **Effort**: **S** (~10 LoC).

### Plan / Doc Currency

#### I8: No post-shipment STATUS banners on any of 5 v020-followup plan files

- **Evidence**: Specialist 4 §Per-leaf plan files. All 5 plans (`01-basedpyright-dynamic-capability.md` through `05-e1-py-flake-rootcause.md`) read as still-pending. A future reader of plan-only will reproduce work that has already shipped.
- **Action**: Single-line STATUS banner per plan ("STATUS: SHIPPED 2026-04-26 — see `stage-1h-results/PROGRESS.md:NN`") + addendum block per plan recording deviations (L01 `ls.py` not `language_server.py`; L02 dual-mode fixture; L03 `AWAITED_SERVER_METHODS` SoT + threshold-wording shift per I9; L04 `pytest_plugins` not `addopts`; L05 no facade patch was needed).
- **Note on sequencing**: per `2026-04-26-v020-followups/README.md:9,13` leaf table, only L01 + L05 declare `decision-p5a-mypy` as `Depends-on`. The L02/L03/L04 banners are P5a-independent and can land in Wave 1 alongside C1. Optionally split into **I8a** (P5a-independent: L02/L03/L04) and **I8b** (P5a-dependent: L01/L05) for sharper sequencing.
- **Effort**: **S** (~5 lines × 5 plans = ~25 LoC).

#### I9: L04 plan still prescribes the rejected `addopts` mechanism

- **Evidence**: Specialist 4 §Per-leaf plan files L04. `docs/superpowers/plans/2026-04-26-v020-followups/04-cargo-build-rustc-workaround.md:102-107` shows `addopts = "-p test.conftest_dev_host"` (rejected at impl time because `addopts` is parsed before pytest adds rootdir to `sys.path`). Actual mechanism: `pytest_plugins = ["test.conftest_dev_host"]` in `vendor/serena/test/conftest.py:32`. `cb0826b` patched only the shim doc.
- **Action**: Update plan code block to mirror the implementation (subsumes part of I8's L04 addendum).
- **Effort**: **S** (~5 LoC edit).

#### I10: `2026-04-26-fix-inspect-getsource-flakes.md` UNEXECUTED (second atomic plan unaddressed)

- **Evidence**: Specialist 2 §C; `docs/gap-analysis/D-debt.md:111`. All 6 sites still raw, all under `vendor/serena/test/spikes/`: `test_stage_3_t1_rust_wave_a.py:374`, `test_stage_3_t2_rust_wave_b.py:201`, `test_stage_3_t3_rust_wave_c.py:247`, `test_stage_3_t4_python_wave_a.py:181`, `test_stage_3_t5_python_wave_b.py:261`, `test_stage_2a_t9_registry_smoke.py:63`. Plan is fully scoped (~155 LoC, 6 tasks). `grep` for `attach_apply_source|get_apply_source|__wrapped_source__` returns zero hits in src + test.
- **Action**: Execute the plan as drafted. Single-cause expected (`inspect.getsource` failing on dynamically-decorated `cls.apply`).
- **Effort**: **S** (~155 LoC, single root cause).

---

## Minor Issues (carry to v0.3.0/v1.1 backlog)

- **M1**: Plan-vs-impl drift in L01 — plan references nonexistent `vendor/serena/src/solidlsp/language_server.py` (actual: `ls.py`). One-line addendum (Specialist 4).
- **M2**: Plan-vs-impl drift in L03 — plan hard-codes `method_names=("request_code_actions", "resolve_code_action", "request_rename_symbol_edit")` but impl extracted `AWAITED_SERVER_METHODS` SoT constant. Additionally, plan parallelism threshold reads `parallel_elapsed < serial_total * 0.7` (line 208) while impl ships an "Amdahl-aware budget" wording — same intent likely, but threshold equivalence unverified per Specialist 4 `04-doc-currency.md:106`. One-line addendum captures both.
- **M3**: CHANGELOG.md frozen at `[0.1.0]` — **7 tags** out of date (verified against `git tag` on 2026-04-27): `v0.1.0-mvp`, `v0.2.0-critical-path-complete`, `v0.2.0-stage-3-complete`, `v0.2.0-stage-3-facades-complete`, `v0.3.0-facade-application-complete`, `stage-v0.2.0-followup-01-basedpyright-dynamic-capability-complete`, `stage-v0.2.0-followups-complete`. The two stage-3 tags represent distinct phase boundaries (facades-only batch vs. full stage-3 close-out per project memory `project_v0_2_0_stage_3_facades_complete`); both belong in the CHANGELOG. User-facing source of truth (Specialist 4).
- **M4**: `mvp-execution-index.md:24-35` shows stages 1A/1B/1H/1I/2A/2B as "Plan ready" despite shipped tags. Refresh status column or deprecate file with a banner (Specialist 2 D1).
- **M5**: MVP scope report headline numbers stale — `docs/design/mvp/2026-04-24-mvp-scope-report.md:17` says "13 always-on / ~11 deferred-loading" vs registry-confirmed today's **8 primitives + 25 facades = 33 always-on** (verified against `vendor/serena/src/serena/tools/scalpel_primitives.py` and `vendor/serena/src/serena/tools/scalpel_facades.py`). Add banner pointing to `WHAT-REMAINS.md`; do NOT mutate the historical record (Specialist 4).
- **M6**: `INDEX-post-v0.3.0.md` missing Stream 3 ✓ COMPLETE banner (Specialist 2 D2).
- **M7**: `CLAUDE.md:89` `Last Updated: 2026-04-24` — 2-3 days behind (Specialist 4).
- **M8**: Code-quality polishes (Specialist 1 Minor):
  - DRY the provenance literal tuple repeated 3× in `vendor/serena/src/serena/refactoring/multi_server.py:1042-1043, 1061-1062, 1162-1163` → use `typing.get_args(ProvenanceLiteral)`; removes 3 `# type: ignore[arg-type]` ignores.
  - Narrow `except BaseException` to `except Exception` in `vendor/serena/src/serena/refactoring/multi_server.py:897` (`_one()`) so `KeyboardInterrupt`/`SystemExit` propagate.
  - Document `compute_file_range` UTF-8 contract in `vendor/serena/src/solidlsp/util/file_range.py:45` (`:raises UnicodeDecodeError:` or rewrap as typed `ValueError`).
- **M9**: Tighten parallelism-budget assertion in `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:282` — split into regression-detector (`parallel < 0.95×serial`) + parallelism-quality (`parallel < max_single + 50ms`) so a 100%→12% regression would be caught (Specialist 1 Minor #7).
- **M10**: 36 in-test skips in Elixir/Erlang/Vue mask LSP/fixture drift — move presence check to session-scoped fixture that fails loudly once (Specialist 3 §Pre-existing skips).
- **M11**: 5 pre-existing pyright errors in `vendor/serena/src/solidlsp/util/metals_db_utils.py:155,185,194` (`psutil possibly unbound` ×4 + `port for class tuple[()]`). Out of touched scope; bundle into a future "pyright residue cleanup" leaf (Specialist 1).
- **M12**: L04 plugin truthy-value contract not pinned — `vendor/serena/test/conftest_dev_host.py:30` uses `== "1"` exactly; no test confirms `=true` does NOT activate (Specialist 3 Minor #10).

---

## Cross-Cutting Patterns

### Pattern 1: Production code shaped by test convenience (TRIZ separation violation)

Specialist 1 surfaced three instances that share a shape:

- `is_async_callable` Mock carve-out exists for one test file (I1).
- Dead helpers `_classify_overlap` + `_bucket_unknown_kind` exist only because spike tests exercise them (I2).
- `whole_file_range` dual-mode fallback exists for one legacy caller (I3).

All three merge production constraints with test constraints into a single code path. **Architectural watch-item**: enforce a separation principle — production code should not have test-only branches; tests should adapt to production code's contract, not the reverse.

### Pattern 2: Two atomic single-doc plans drafted same day, both unexecuted (process gap)

Both `2026-04-26-decision-p5a-mypy.md` (C2) and `2026-04-26-fix-inspect-getsource-flakes.md` (I10) were drafted on 2026-04-26 alongside the post-v0.3.0 INDEX, and neither has been touched. The TREE plans (`v020-followups/`) executed cleanly; the atomic plans went silently un-actioned.

**Recommendation**: adopt a "drafted-on-day-N must have status update by day-N+7" convention for atomic plan files (TREE plans have their own per-leaf cadence and are exempt). See Open Question §Q3.

### Pattern 3: Verification-by-implementation-existence vs. verification-by-test-green

Specialist 2 verified L03 closure by reading `WHAT-REMAINS.md` claims against existing source files (passes). Specialist 3 verified by running tests (FAILS — pytest-asyncio missing). **Specialist 2's methodology has a blind spot for runtime infrastructure issues**.

**Recommendation**: closure claims in `WHAT-REMAINS.md` should require both an implementation pointer AND a passing-test pointer. Define the syntactic shape concretely — e.g., a `tests:` line listing test-file paths next to the existing source-file `path:` line — so future closure entries are mechanically auditable.

### Process scope note (not a fourth pattern): L01 was not deeply audited

Specialist 1 explicitly limits scope to the v020-followups batch (L02-L05); L01 (basedpyright dynamic-cap) shipped under its own prior tag and was not deeply audited by any specialist. Specialist 4 noticed the `language_server.py` vs `ls.py` plan drift in passing. **Watch-item**: if the basedpyright dynamic-cap claim ever needs re-verification (e.g., during catalog-evolution work), a fresh audit is warranted. (Coordinator cross-finding insight 5, `10-coordinator-thread.md:127-128`.)

---

## Recommended Execution Order

### Wave 1 (sequential — must run in order)

1. **C1: pytest-asyncio install** (one-line config; unblocks 36 tests + validates L03 immediately).
2. **C2: Execute decision-p5a-mypy** (resolves 3 findings at once: plan + spike-result + code; needs human decision SHIP-vs-DROP first per Open Question §Q1).
3. **I10: Execute fix-inspect-getsource-flakes** (small, single-cause, fully scoped — second unexecuted atomic plan; benefits from C1 landing first so any async sites run).

### Wave 1 (parallel — can run alongside the sequential chain above)

- **I8a (L02/L03/L04 STATUS banners + addenda)** — P5a-independent per `2026-04-26-v020-followups/README.md:9,13`; pure plan-vs-impl drift recordings (dual-mode fixture, AWAITED_SERVER_METHODS SoT, pytest_plugins-not-addopts). Can land immediately, no decision wait.
- **I9** (L04 plan `addopts` → `pytest_plugins` correction) — independent doc fix.
- **M1, M2** (L01/L03 plan addenda) — independent doc fixes.

### Wave 2 (parallelizable — independent files, no shared state, dispatch via map/reduce subagents within CPU-core limit)

4. **I1+I2+I3: Code-quality batch** (Mock carve-out tightening + dead-helper resolution + dual-mode fallback removal — three TRIZ separation fixes in one batch).
5. **I8b: L01 + L05 STATUS banner addenda** (P5a-dependent; awaits C2 ratification).
6. **I5+I6+I7: Test-depth batch** (booted-RA test + xpass promotion + L05 mutation test).
7. **I4: Strip-the-skip across 13 facades** (apply L05 model — single map/reduce subagent across independent test files).
8. **M3+M4+M5+M6+M7: Docs hygiene** (CHANGELOG + INDEX banner + scope-report banner + execution-index refresh + CLAUDE.md date).
9. **M8+M9+M10+M11+M12: Long-tail polish** (deferrable to v0.3.0+).

### Dependency edges

- **C1 → C2** (verifying P5a-related test runs requires async harness).
- **C1 → I4** (strip-the-skip touches async-marked facade tests).
- **C2 → I8b** (L01 + L05 banner addenda content depends on the ratified P5a outcome). **Note**: L02/L03/L04 banners (I8a) are P5a-independent and live in Wave 1.
- All other Wave-2 batches independent of each other.

---

## Out-of-Scope (explicitly punted)

- **Stage 1H continuation tree** (6 leaves, ~8,845 LoC) — fully unblocked but its own milestone.
- **v11-milestone tree** (8 leaves) — gated on Stage 1H continuation.
- **v2-language-strategies tree** (5 leaves) — gated on v11-milestone.
- **75 pre-existing pyright errors in `vendor/serena/src/`** — none in touched dirs; separate "pyright residue cleanup" leaf.
- **LSP issue #1040 ecosystem investigation** — upstream, watch-only.
- **Test depth gaps carried forward** (Specialist 3 §Missing test categories, `03-test-coverage.md:161-172`) — six categories not absorbed into Critical/Important above; named here so they don't silently drop:
  - Concurrency / race tests on `multi_server.py` per-server gather pool — **M**.
  - Cold-start ordering tests for capability discovery vs first request — **M**.
  - Cross-language multi-server tests (Rust + clippy) — **L** (already v1.1 scope per L03 plan).
  - Performance regression guards beyond the single L03 budget assertion — **S** (M9 only sharpens it).
  - Error-path / fault-injection tests for LSP-process crash mid-request — **M**.
  - Hypothesis property-based tests for `compute_file_range` UTF-8 boundary cases — **S**.
- **Coverage instrumentation** — no `coverage.py` integration in CI; deferrable per Specialist 3.
- **`docs/dev/multi-server-coordinator.md` + `docs/dev/lsp-preflight-validation.md`** — useful new dev docs but not closure-blocking.
- **`vendor/serena/README-OVERLAY.md`** — only matters if engine fork is cloned standalone.
- **Anthropic native LSP-write integration** — long-horizon watch-only.

---

## Open Questions for the Human

### Q1: P5a — SHIP/B or HOLD-DROP/C?

The post-Stage-1E re-run measurements (0% stale, p95 = 4.306s) now meet Outcome B's "ship with documented warning" thresholds, NOT the original Outcome C's "drop pylsp-mypy" thresholds. The plan-of-record is DROP (in code). The spike-result file's verdict line is internally inconsistent with its own measurements.

**Decision needed**: Ratify SHIP-with-warning (B) — propagate throughout 4 doc artifacts + add `pylsp_mypy.enabled = True`; OR hold-DROP (C) with explicit annotation "verdict held despite re-run measurements; rationale: …".

This is a measurement-vs-original-policy call that needs a human; either choice is defensible but the "limbo" state must end.

### Q2: Should I2 wire the dead helpers, or delete them?

Wiring restores the §11.2 case-1 spec invariant (`subset_lossless`/`subset_lossy` actually drives a merge decision). Deleting follows YAGNI strictly. The spec has been written but not enforced; deciding which way to go requires a YAGNI-vs-completeness call.

### Q3: Convention adoption — "atomic plans must have a day-N+7 status check"?

Pattern 2 is a process gap; the fix is convention rather than code. Adopting it is a project-process decision. (Diagnosed in Pattern 2 — atomic plans only, not TREE plans; TREE plans have built-in per-leaf cadence so they're exempt by design. Convention proposal sourced from `11-synthesis-input.md:97`.)

---

## Process

This report is the synthesized output of a 3-round pair-programming review.

**File structure** (under `docs/reviews/2026-04-27-post-v020-followups/`):

- `01-code-quality.md`, `02-plan-currency.md`, `03-test-coverage.md`, `04-doc-currency.md` — 4 specialist deep-dives (code, plan, test, doc).
- `10-coordinator-thread.md` — coordinator pass cross-checking the 4 specialists, surfacing themes + conflicts.
- `11-synthesis-input.md` — coordinator-curated input feeding the synthesis pair.
- `20-draft-1.md` → `21-challenges-1.md` → `20-draft-2.md` → `21-challenges-2.md` — pair-programming rounds (Synthesizer A drafts, Synthesizer B challenges).
- `FINAL-REPORT.md` — this file.

**Severity calibration** locked at: 2 Critical / 10 Important / 12 Minor + 3 cross-cutting patterns + 1 process scope note. Every finding cites a specialist file and line number.

---

*Author: AI Hive(R)*
