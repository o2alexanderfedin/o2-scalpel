# Coordinator Discussion Thread — Post v0.2.0 Follow-ups Review
**Date**: 2026-04-27
**Facilitator**: Coordinator agent
**Participants**: Specialist 1 (Code), Specialist 2 (Plan), Specialist 3 (Test), Specialist 4 (Doc)
**Tag reviewed**: `stage-v0.2.0-followups-complete` (parent `0435ac8`, submodule `a2cece4a`)

---

## Opening: what each specialist surfaced

**Specialist 1 (Code Quality)** — Touched code is clean: every modified module is 0/0/0 under pyright, TDD-grade tests, no production-breaking issues. Residual risks ranked: (1) `is_async_callable` Mock carve-out is too broad (any MagicMock instance silently passes the gate); (2) two dead helpers in `multi_server.py` (`_classify_overlap`, `_bucket_unknown_kind`) that are tested via spike tests but never wired into production; (3) `whole_file_range` dual-mode fixture has a silent-fallback footgun; (4) `compute_file_range` will crash on non-UTF-8 input without a typed contract; (5) ~75 pre-existing pyright errors elsewhere in `vendor/serena/src/` (none in touched dirs). DRY/type-ignore micro-issues in `multi_server.py:1042-1163`.

**Specialist 2 (Plan Coverage)** — All 5 v020-followup leaves shipped cleanly and reflected as CLOSED in `WHAT-REMAINS.md` §4. The biggest gap: **two atomic plans drafted on the same day are entirely UNEXECUTED**: `2026-04-26-decision-p5a-mypy.md` (5 tasks) and `2026-04-26-fix-inspect-getsource-flakes.md` (6 tasks). The legacy `2026-04-24-mvp-execution-index.md` ledger is frozen at planning-time labels (Stages 1A/1B/1H/1I/2A/2B all show "Plan ready" despite shipped tags). Three TREE plans are appropriately untouched (`stage-1h-continuation`, `v11-milestone`, `v2-language-strategies`). One stream-3 status banner is missing from `INDEX-post-v0.3.0.md`.

**Specialist 3 (Test Coverage)** — 60+ new tests are well-written and pass in isolation, BUT a **critical infrastructure gap masks parallelism evidence**: `pytest-asyncio` is NOT installed in `vendor/serena/.venv`, so 36 async tests (including L03's centerpiece `test_broadcast_runs_three_python_servers_in_parallel`) silently FAIL at runtime. This means the L03 "Amdahl-aware budget" guarantee is **unverified on this host**. Other gaps: L02 tests bypass `__init__` via `__new__` (no end-to-end booted-RA test); L05 lacks a negative/mutation test; rust-analyzer detection class is mock-heavy with no real-fs verification; 13 E2E facades still carry the same `pytest.skip` pattern L05 just stripped; 36 in-test skips in Elixir/Erlang/Vue mask LSP/fixture drift; 2 xpassed tests in `test_serena_agent.py` should be promoted.

**Specialist 4 (Doc Currency)** — Doc-closure commit (`34f7766`) correctly marked all 5 leaves CLOSED in `WHAT-REMAINS.md` and `stage-1h-results/PROGRESS.md`. New `docs/dev/host-rustc-shim.md` is accurate. But: (1) **per-leaf plan files were never annotated with post-shipment STATUS markers** — they read as still-pending; (2) **L04 plan still prescribes the rejected `addopts` mechanism** (only the shim doc was patched); (3) **P5a.md is internally inconsistent** — verdict line says "DROP" while measurements (0% stale, p95=4.306s) support "SHIP/B"; (4) **CHANGELOG.md frozen at v0.1.0** — 7 tags out of date; (5) MVP scope report's headline numbers (13/24) stale vs today's 8+25=33; (6) Plan-vs-impl drift in L01 (`ls.py` vs the plan's `language_server.py`), L02 (dual-mode vs single-mode), L03 (`AWAITED_SERVER_METHODS` SoT vs hard-coded tuple), L05 (no facade patch vs prescribed 15-LoC fix).

---

## Cross-cutting themes

### Theme 1: P5a unresolved decision is the single most cited issue
- **S1 says**: not directly cited (out of code-touched scope).
- **S2 says**: `2026-04-26-decision-p5a-mypy.md` UNEXECUTED — all 5 tasks open. Three artifacts disagree (P5a.md SHIP, PROGRESS.md DROP, code DROP). Top-priority sequencing item per `WHAT-REMAINS.md` §1.
- **S3 says**: indirectly — L05 was supposed to depend on P5a ratification per `v020-followups/README.md:13`.
- **S4 says**: P5a.md is internally inconsistent — "verdict says DROP, measurements say SHIP/B." Drift propagates to `SUMMARY.md:25`, `PROGRESS.md:31,70,101`, `stage-1h-results/PROGRESS.md:94`.
- **Coordinator analysis**: This is the **same problem viewed from three angles**: S2 sees it as an unexecuted plan; S4 sees it as documentation drift; S3 sees it as an unfulfilled L05 precondition. The plan exists, the contradiction exists in the spike-result file, and no code change has been made. The plan is small (~30 LoC + ~95 LoC governance tests) and unblocks downstream determinism.
- **Priority**: **CRITICAL** — converges three specialists.

### Theme 2: pytest-asyncio gap silently kills parallelism evidence
- **S1 says**: not surfaced (code is correct in isolation).
- **S2 says**: not surfaced (plan-vs-code coverage doesn't probe runtime).
- **S3 says**: **The single biggest finding in the entire review.** `pytest-asyncio` is missing from `vendor/serena/.venv`. The L03 integration test that proves multi-server parallelism FAILS silently. ~35 pre-existing async spike tests are also silently red. PytestUnknownMarkWarning is the only signal.
- **S4 says**: not surfaced (docs don't mention runner config).
- **Coordinator analysis**: This is a **single-specialist finding** but it flips the L03 closure claim. `WHAT-REMAINS.md:104` says "Real-adapter parallelism evidence test … boots pylsp + basedpyright + ruff and asserts Amdahl-aware parallelism budget. 18 tests (11 helper + 6 init-validation + 1 integration)." That last "1 integration" never actually runs. **One-line config fix** (`uv add --dev pytest-asyncio` + `asyncio_mode = "auto"` in pyproject) restores 36 tests and the L03 guarantee.
- **Priority**: **CRITICAL** — falsifies a published closure claim.

### Theme 3: Plan/code/doc tri-drift on shipped leaves
- **S1 says**: notes the dual-mode `whole_file_range` fixture as a footgun (L02 implementation deviated from any documented contract).
- **S2 says**: legacy MVP execution index shows 6 stages frozen at "Plan ready" despite shipped tags.
- **S3 says**: L05 strip-the-skip pattern was applied to ONE facade; 13 other facades still have the old pattern (the plan didn't anticipate this leverage opportunity).
- **S4 says**: Per-leaf plan-vs-impl drift on L01 (`ls.py` vs `language_server.py` in plan), L02 (dual-mode vs single-mode), L03 (`AWAITED_SERVER_METHODS` SoT vs hard-coded tuple), L04 (`pytest_plugins` vs `addopts`), L05 (no facade patch vs prescribed 15-LoC fix). NO leaf plan got a post-shipment STATUS banner.
- **Coordinator analysis**: All 5 leaves successfully shipped, but the planning artifacts now lie about what was built. A future reader of the plan files alone will reproduce the rejected approach (especially L04's `addopts`). This is **systemic**, not per-leaf — implies a missing closure-step convention. The cheapest fix is a one-line STATUS banner per plan + addendum block recording deviations.
- **Priority**: **IMPORTANT** — confuses future readers; doesn't break code.

### Theme 4: Mock-heaviness vs end-to-end booted-server verification
- **S1 says**: `is_async_callable` Mock carve-out is too broad — should require an explicit marker attribute.
- **S2 says**: not directly surfaced.
- **S3 says**: `TestRustAnalyzerDetection` (12 tests) is **HIGH** mock-risk — all use 4-6 nested `with patch(...)` contexts, behaviour reduces to "function returned the mocked path." `TestRustAnalyzerPreflightPositionValidation` bypasses `__init__` via `__new__`. The only real-fs class is `pytest.skip`-gated.
- **S4 says**: not directly surfaced.
- **Coordinator analysis**: S1 and S3 converge from different angles — S1 saw the Mock carve-out as a production-risk "future code that accidentally constructs a Mock could pass the gate"; S3 saw the same shape as test-quality risk "no real-fs / no booted-server verification." Both point at the same gap: **the new code is verified through mocks, not through reality**. Restoring the booted-server smoke test (gated on `which rust-analyzer`) and tightening the Mock carve-out to a marker attribute would close both at once.
- **Priority**: **IMPORTANT** — degrades trust in green-CI signal.

### Theme 5: Dead-code in production source proves itself only via spike tests
- **S1 says**: `_classify_overlap` (`multi_server.py:516`) and `_bucket_unknown_kind` (`:562`) are dead in `src/` — only referenced by `test/spikes/test_stage_1d_t10_disagreements.py`. Spec they implement (§11.2 case 1) was never wired into `merge_and_validate_code_actions`. State is "tested code that does nothing."
- **S2 says**: not surfaced (plan-vs-code doesn't read implementation depth).
- **S3 says**: not surfaced (test corpus is in scope but spike-test → src reachability is not).
- **S4 says**: not surfaced.
- **Coordinator analysis**: Single-specialist finding but it's a YAGNI violation in both directions: either (a) wire the helpers in for real and let the §11.2 invariants drive merge decisions, or (b) delete helpers + spike tests. Current state is the worst of both worlds — test surface grows, no production behaviour.
- **Priority**: **IMPORTANT** — small fix (delete or wire); fails YAGNI either way.

### Theme 6: 6 inspect.getsource flakes — second unexecuted atomic plan
- **S1 says**: not in scope (touched-area focus).
- **S2 says**: `2026-04-26-fix-inspect-getsource-flakes.md` UNEXECUTED — all 6 sites still raw. Plan is fully detailed (~155 LoC). Per `WHAT-REMAINS.md` §Recommended-sequencing item 2.
- **S3 says**: indirectly — these flakes are part of the "13 E2E facades still carry the L05-stripped pattern" pile.
- **S4 says**: not surfaced (D-debt.md notes them but doesn't audit plan execution).
- **Coordinator analysis**: Same shape as Theme 1 — a small, fully-scoped atomic plan exists but was never executed. Both `decision-p5a-mypy` and `fix-inspect-getsource-flakes` were drafted on 2026-04-26 (same day as INDEX) and are listed as next-up in the recommended sequencing. Neither has been touched. **Pattern emerging**: the v020-followups TREE was executed cleanly, but the two atomic single-doc plans were skipped.
- **Priority**: **IMPORTANT** — quick determinism win; one fix likely covers all six.

### Theme 7: L05 strip-the-skip is a leverage pattern not yet generalized
- **S1 says**: not surfaced.
- **S2 says**: not surfaced.
- **S3 says**: 13 other E2E facades (E2/E3/E4/E5/E8/E9/E10/E11/E13/E14/E15/E16) still carry the same `pytest.skip` pattern L05 just stripped. Recommends applying the L05 treatment leaf by leaf.
- **S4 says**: not surfaced.
- **Coordinator analysis**: L05 closed E1-py determinism with two moves: (1) strip the silent skip → unconditional assertion, (2) add a 10-iteration determinism guard. **Same playbook applies to 13 more facades** — each is a small leaf. Worth surfacing as a recommended v0.2.0+ batch (or rolled into Stage 1H continuation).
- **Priority**: **IMPORTANT** — pattern reuse opportunity.

### Theme 8: CHANGELOG / MVP-scope-report / CLAUDE.md staleness cluster
- **S1 says**: not in scope.
- **S2 says**: legacy `mvp-execution-index.md` lines 24–35 show stages 1A/1B/1H/1I/2A/2B as "Plan ready" despite shipped tags.
- **S3 says**: not in scope.
- **S4 says**: CHANGELOG.md frozen at v0.1.0 — 7 tags out of date; MVP scope report says "13 always-on / 24 total tools" vs today's 8+25=33; CLAUDE.md `Last Updated` field is 2 days behind.
- **Coordinator analysis**: Three docs that show planning-time numbers / labels and were never refreshed after MVP cut. Cosmetic but degrades the "single source of truth" principle. CHANGELOG is the highest-value fix because it's user-facing.
- **Priority**: **MINOR** — docs hygiene.

---

## Conflicts / disagreements between specialists

### Conflict 1: Is the L03 closure claim valid?
- **S1 + S4** treat L03 as cleanly shipped (S1: 0/0/0 pyright on touched files; S4: WHAT-REMAINS.md L03 entry verified accurate).
- **S3** says the L03 integration test that backs the parallelism claim **never actually runs** (silent failure due to missing pytest-asyncio).
- **Coordinator's ruling**: S3 is right. The closure is functionally valid (the unit tests + init-validation tests pass; the implementation is correct), but the **headline parallelism evidence is not proven on this host**. The closure note in `WHAT-REMAINS.md:104` should be footnoted: "*the integration test silently fails until `pytest-asyncio` is installed; see test-coverage review §Critical*." Fix the venv first, then the closure stands.

### Conflict 2: Is the dual-mode `whole_file_range` fixture acceptable?
- **S1** flags it as an Important footgun and recommends dropping the fallback.
- **S4** notes the plan prescribed single-mode but the implementation deviated to dual-mode without documentation; treats it as plan-vs-impl drift.
- **Coordinator's ruling**: Both are right; they're complementary. The implementation deviation is real (S4) AND the resulting design has a footgun (S1). Recommend: (a) decide single vs dual based on the one legacy caller (`test_smoke_python_codeaction.py:22`) — either migrate it to `indirect=True` or to a direct `compute_file_range` call; (b) update L02 plan with a STATUS+DEVIATION addendum recording the decision.

### Conflict 3: Is the MVP scope report stale or by-design preserved?
- **S2** mentions the legacy `mvp-execution-index.md` (different file) needs status updates.
- **S4** explicitly says MVP scope report is "report-only — preserved as historical decision record. Recommendation: do NOT mutate it. Instead, add a single banner note."
- **Coordinator's ruling**: S4's guidance applies to `mvp-scope-report.md` (preserve). S2's guidance applies to `mvp-execution-index.md` (refresh status column). They are talking about two different files; not a real conflict. Recommend both: banner on scope-report, status refresh on execution-index.

### Conflict 4: Should xfail markers in `test_serena_agent.py` be promoted?
- **S3** says the 2 xpassed tests should be promoted to plain pass (otherwise future regressions in F#/Rust/TS go silent).
- **No other specialist** addressed.
- **Coordinator's ruling**: S3's call stands. The xpasses are evidence that issue #1040 LSP-flakiness has improved on this host. Promoting locks the new contract; if #1040 regresses, the test fails loudly instead of xpassing silently. Note: only do this for the 2 that xpassed today, not all 4 xfails — the other 2 are still legitimately flaky.

---

## Surfacing what's NOT in any individual finding

### Cross-finding insight 1: The two unexecuted atomic plans + P5a doc contradiction = ONE problem
S2 catalogues the unexecuted plans. S4 catalogues the P5a doc contradiction. **They are the same problem** — `decision-p5a-mypy` is the plan whose execution would resolve the P5a doc contradiction. So the synthesis report should treat these as ONE critical item with two visible faces (plan exists; doc inconsistent), not two separate findings.

### Cross-finding insight 2: pytest-asyncio gap means S2's "L03 CLOSED" verification is incomplete
S2 verified L03 closure by checking that the implementation files exist and that `WHAT-REMAINS.md` cites them correctly. S3 verified by running the test suite and discovered the silent failure. **S2's verification methodology has a blind spot** for runtime infrastructure issues that pass static checks. The synthesis report should note that "CLOSED" claims need a "ran the verifying test in green" criterion, not just "implementation exists."

### Cross-finding insight 3: L05 strip-the-skip + 13 untreated facades + the 6 inspect.getsource flakes are all the same shape
S3 surfaced the 13 untreated facades. S2 surfaced the 6 inspect.getsource flakes. S4 surfaced the WHAT-REMAINS sequencing recommendation. All three are **determinism debt** in the test suite, all are small per-site fixes, all share the "silent skip masks a real flake" pattern. The synthesis report should consolidate them as a "determinism-debt sweep" recommendation.

### Cross-finding insight 4: The Mock carve-out + dead helpers + dual-mode fallback are all "code paths that exist for tests, not for production"
S1 surfaced all three. They share a shape: **production code shaped by test convenience**. The Mock carve-out exists for one test file. The dead helpers exist only because spike tests exercise them. The dual-mode fallback exists for one legacy caller. All three are TRIZ "separation principle" violations — production constraints and test constraints have been merged into single code paths. Synthesis report could call this out as an architectural pattern to watch.

### Cross-finding insight 5: No specialist audited L01 tests
S1, S3, S4 all touch L01 in passing but none audit the test corpus or the implementation depth (S1 explicitly limits to the touched files of the v020-followups batch; L01 was a separate prior tag `stage-v0.2.0-followup-01-...`). S4 notes the plan referenced a non-existent `language_server.py` (the file is `ls.py`). The synthesis should note that L01's plan-vs-impl drift was not deeply audited; flag for follow-up if the basedpyright dynamic-cap claim ever needs to be re-verified.

---

## Coordinator's prioritized agenda for Wave 3

1. **Install pytest-asyncio + set asyncio_mode** — restores 36 tests, validates the L03 closure claim. One-line config. (S3)
2. **Execute decision-p5a-mypy** — resolves Theme 1 (3-way convergence: S2 plan, S4 doc, S3 indirect). Small (5 tasks). (S2 + S4 + S3)
3. **Execute fix-inspect-getsource-flakes** — second unexecuted atomic plan; small, single-cause. (S2 + S3)
4. **Tighten is_async_callable Mock carve-out** — replace `isinstance(obj, Mock)` with a marker attribute. Restores the L03 gate's "loud TypeError on raw sync misuse" guarantee. (S1)
5. **Resolve dead helpers in multi_server.py** — wire or delete `_classify_overlap` + `_bucket_unknown_kind` + their spike test. (S1)
6. **Drop whole_file_range unparametrized fallback** — migrate the one legacy caller; remove the silent-fallback footgun. (S1 + S4)
7. **Add post-shipment STATUS banners + DEVIATION addenda** to all 5 v020-followup plan files. Document L01 (`ls.py`), L02 (dual-mode), L03 (SoT constant), L04 (`pytest_plugins`), L05 (no facade patch). (S4)
8. **Add end-to-end booted-rust-analyzer test for L02 preflight** — gated on `which rust-analyzer`. Replaces mock-only verification. (S3)
9. **Promote 2 xpassed tests in `test_serena_agent.py`** — locks the contract. (S3)
10. **Apply L05 strip-the-skip pattern to 13 remaining E2E facades** — leaf-by-leaf or batched into Stage 1H continuation. (S3)
11. **Add negative/mutation test for L05 determinism guard** — proves the assertion catches what it claims. (S3)
12. **Refresh CHANGELOG.md, mvp-execution-index.md status column, MVP scope report banner, CLAUDE.md date** — docs hygiene cluster. (S2 + S4)
13. **DRY the provenance literal tuple + narrow BaseException + L02 UTF-8 contract docs** — small code-quality polishes. (S1)

---

*Author: AI Hive(R) — Coordinator agent*
