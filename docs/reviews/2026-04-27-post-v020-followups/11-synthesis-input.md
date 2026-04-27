# Synthesis Input for Wave 3 Pair Synthesizers
**Date**: 2026-04-27
**Source**: 4 specialist findings (`01-04-*.md`) + coordinator thread (`10-coordinator-thread.md`)
**Tag reviewed**: `stage-v0.2.0-followups-complete` (parent `0435ac8`, submodule `a2cece4a`)

---

## Issues to address in FINAL-REPORT.md (prioritized)

### CRITICAL (must surface in final report)

1. **pytest-asyncio is not installed in `vendor/serena/.venv`** — L03 integration test (`vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:122`) silently FAILS at runtime, plus ~35 pre-existing async spike tests. **The L03 "Amdahl-aware parallelism budget" closure claim in `WHAT-REMAINS.md:104` is unverified on this host.** Recommended action: `uv add --dev pytest-asyncio` + add `asyncio_mode = "auto"` to `vendor/serena/pyproject.toml [tool.pytest.ini_options]`. Source: **S3** §Critical.

2. **`docs/superpowers/plans/2026-04-26-decision-p5a-mypy.md` UNEXECUTED** — 5 tasks open. Three artifacts disagree in writing: `spike-results/P5a.md` says SHIP (verdict line says DROP but measurements say SHIP/B), `spike-results/PROGRESS.md:101` says DROP, code (`vendor/serena/src/solidlsp/language_servers/pylsp_server.py:154`) says DROP. Plan exists, fully scoped (~30 LoC + ~95 LoC governance tests). Recommended action: ratify SHIP or DROP, propagate to all 4 artifacts. Source: **S2** §B + **S4** §Spike-result re-runs (P5a) + **S3** indirect (L05 dependency).

3. **P5a.md is internally inconsistent** — `docs/superpowers/plans/spike-results/P5a.md:3` verdict says "Outcome C — DROP" while measurements at lines 9-12 (0% stale, p95=4.306s) actually meet Outcome B ("ship with documented warning") thresholds. Drift propagates to `SUMMARY.md:25`, `PROGRESS.md:31,70,101`, `stage-1h-results/PROGRESS.md:94`. Recommended action: same fix as Critical #2 (one decision resolves both faces of this issue). Source: **S4** §Spike-result re-runs.

### IMPORTANT

4. **`docs/superpowers/plans/2026-04-26-fix-inspect-getsource-flakes.md` UNEXECUTED** — 6 tasks open, ~155 LoC. All 6 sites still raw: `test_stage_3_t1_rust_wave_a.py:374`, `test_stage_3_t2_rust_wave_b.py:201`, `test_stage_3_t3_rust_wave_c.py:247`, `test_stage_3_t4_python_wave_a.py:181`, `test_stage_3_t5_python_wave_b.py:261`, `test_stage_2a_t9_registry_smoke.py:63`. Single-cause expected. Recommended action: execute the plan. Source: **S2** §C.

5. **`is_async_callable` Mock carve-out is too broad** — `vendor/serena/src/serena/refactoring/_async_check.py:69` (`isinstance(obj, Mock)`) silently passes ANY MagicMock instance as async-callable. Defeats the L03 "loud TypeError on raw sync misuse" gate for accidental Mock objects. Recommended action: replace with marker-attribute opt-in (`getattr(obj, "_o2_async_callable", False)`); update `test/spikes/test_v0_2_0_c_find_symbol_position.py` (3 sites) to set the marker. Source: **S1** Important #1.

6. **Dead helpers `_classify_overlap` + `_bucket_unknown_kind`** — `vendor/serena/src/serena/refactoring/multi_server.py:516, 562` are referenced ONLY by `test/spikes/test_stage_1d_t10_disagreements.py`, never wired into `merge_and_validate_code_actions` or `merge_code_actions` bucket key. §11.2 case-1 spec is silently absent. Recommended action: wire (preferred) or delete both helpers + spike test. YAGNI either way. Source: **S1** Important #2.

7. **`whole_file_range` fixture dual-mode footgun** — `vendor/serena/test/integration/conftest.py:186-221`. Unparametrized callers silently get `(0,0)..(10_000,0)` fallback. Future tests against strict servers will hit `ValueError`. Plan-vs-impl drift (L02 plan prescribed single-mode; impl deviated). Recommended action: drop the fallback, migrate one legacy caller (`test_smoke_python_codeaction.py:22`) to `indirect=True` or direct `compute_file_range` call. Source: **S1** Important #3 + **S4** §Per-leaf plan files L02.

8. **No post-shipment STATUS banners on any of 5 v020-followup plan files** — `01-basedpyright-dynamic-capability.md`, `02-rust-analyzer-position-validation.md`, `03-multi-server-async-wrapping.md`, `04-cargo-build-rustc-workaround.md`, `05-e1-py-flake-rootcause.md` all read as still-pending. Recommended action: single-line STATUS banner per plan + addendum block recording deviations. Source: **S4** §Per-leaf plan files.

9. **L04 plan still prescribes the rejected `addopts` mechanism** — `docs/superpowers/plans/2026-04-26-v020-followups/04-cargo-build-rustc-workaround.md:102-107` shows `addopts = "-p test.conftest_dev_host"` which was rejected at impl time (parsed before pytest adds rootdir to `sys.path`). Actual mechanism uses `pytest_plugins = ["test.conftest_dev_host"]` in `vendor/serena/test/conftest.py:32`. The `cb0826b` "prose drift" commit patched only the shim doc. Recommended action: update plan code block to match implementation. Source: **S4** §Per-leaf plan files L04.

10. **No end-to-end booted-rust-analyzer test for L02 preflight** — all 3 tests in `vendor/serena/test/solidlsp/rust/test_rust_analyzer_detection.py:575-654` bypass `__init__` via `RustAnalyzer.__new__(RustAnalyzer)` and patch `super().request_code_actions`. A future refactor that swallows the preflight ValueError would not be caught. Recommended action: add test gated on `which rust-analyzer`, boot real RA, call with out-of-range `end`, assert ValueError raised with no LSP traffic. Source: **S3** Important #4.

11. **L05 strip-the-skip pattern not generalized** — 13 E2E facades (E2/E3/E4/E5/E8/E9/E10/E11/E13/E14/E15/E16) still carry the `pytest.skip` fallback that L05 stripped from E1-py. Recommended action: apply L05 treatment leaf-by-leaf (or batch into Stage 1H continuation). Source: **S3** Important #7.

12. **2 xpassed tests in `vendor/serena/test/serena/test_serena_agent.py`** — `lines 220, 231, 329, 340` carry `@pytest.mark.xfail` for #1040 LSP unreliability; 2 of 4 xpassed in current run. Recommended action: remove the xfail decorator from the 2 that xpassed; document why in commit. Source: **S3** Critical #2.

13. **No negative/mutation test for L05 determinism guard** — `vendor/serena/test/e2e/test_e2e_e1_py_determinism.py:49` assertion is unproven against the failure mode it claims to catch. Recommended action: add a test that monkeypatches `mcp_driver_python.split_file` to return `applied=False` once and asserts the parametrize iteration fails. Source: **S3** Critical #3.

14. **Plan-vs-impl drift in L01 + L03** — L01 plan references nonexistent `vendor/serena/src/solidlsp/language_server.py` (actual file is `ls.py`). L03 plan hard-codes `method_names=("request_code_actions", "resolve_code_action", "request_rename_symbol_edit")` but impl extracted `AWAITED_SERVER_METHODS` SoT constant. Recommended action: addendum block in each plan file. Source: **S4** §Per-leaf plan files L01, L03.

### MINOR

15. **CHANGELOG.md frozen at v0.1.0** — 7 tags out of date (`v0.1.0-mvp`, `v0.2.0-critical-path-complete`, `v0.2.0-stage-3-complete`, `v0.3.0-facade-application-complete`, `stage-v0.2.0-followup-01-…-complete`, `stage-v0.2.0-followups-complete`). Source: **S4** §CHANGELOG.

16. **`mvp-execution-index.md:24-35` shows stages 1A/1B/1H/1I/2A/2B as "Plan ready"** despite shipped tags. Source: **S2** D1.

17. **MVP scope report headline numbers stale** — `mvp-scope-report.md:17` says "13 always-on / ~11 deferred-loading" vs today's 8+25=33 always-on. Recommended action: add a banner pointing to `WHAT-REMAINS.md` (do NOT mutate the historical doc). Source: **S4** §Design docs.

18. **CLAUDE.md `Last Updated: 2026-04-24`** — 2 days behind. Source: **S4** §CLAUDE.md.

19. **DRY violation: provenance literal tuple repeated 3x** — `multi_server.py:1042-1043, 1061-1062, 1162-1163`. Recommended action: replace with `typing.get_args(ProvenanceLiteral)` + small `_coerce_provenance` helper (removes 3 `# type: ignore[arg-type]` ignores). Source: **S1** Minor #5.

20. **Broad except in `_one()`** — `multi_server.py:897` uses `except BaseException` instead of `except Exception`; swallows `KeyboardInterrupt`/`SystemExit`. Source: **S1** Minor #6.

21. **`compute_file_range` UTF-8 contract undocumented** — `vendor/serena/src/solidlsp/util/file_range.py:45` will raise `UnicodeDecodeError` on Latin-1; no `:raises:` line. Recommended action: document or rethrow as typed `ValueError`. Source: **S1** Important #4 + **S3** L02 untested behaviour.

22. **L04 plugin truthy-value contract not pinned** — `vendor/serena/test/conftest_dev_host.py:30` uses `== "1"` exactly; no test confirms `=true` does NOT activate. Source: **S3** Minor #10.

23. **Tighten parallelism-budget assertion** — `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:282` only asserts ">=10% saving"; would miss a 100%→12% regression. Recommended action: split into regression-detector + parallelism-quality assertions. Source: **S1** Minor #7.

24. **Missing INDEX-post-v0.3.0.md status banner for Stream 3** — `2026-04-26-INDEX-post-v0.3.0.md` doesn't mark v020-followups as ✓ COMPLETE. Source: **S2** Important #4.

25. **36 in-test skips in Elixir/Erlang/Vue mask LSP/fixture drift** — `pytest.skip("Could not find ... function/symbol")` patterns in `test/solidlsp/elixir/`, `test/solidlsp/erlang/`, `test/solidlsp/vue/`. Recommended action: move presence check to session-scoped fixture that fails loudly once. Source: **S3** §Pre-existing skips.

26. **5 pre-existing pyright errors in `metals_db_utils.py:155, 185, 194`** — `psutil possibly unbound` (4) + `port for class tuple[()]` (1). Out of touched scope but cited by cross-leaf review. Source: **S1** §Pre-existing residue.

---

## Recommended report structure

```markdown
# Post v0.2.0 Follow-ups Review — Final Report
**Date**: 2026-04-27
**Tag reviewed**: stage-v0.2.0-followups-complete

## Executive Summary
- 1-paragraph: 5 leaves shipped; 3 critical findings would compromise the closure claim or block forward progress; ~10 important findings; rest are docs/code hygiene.
- Bottom line: closure stands MODULO pytest-asyncio fix + P5a decision.

## Critical Findings (3)
- Each as a numbered subsection with:
  - What it is (1-2 sentences)
  - Why it's critical (impact)
  - Recommended action (concrete command/edit)
  - Source specialist + file:line evidence
- Items 1, 2, 3 from the prioritized list above.

## Important Findings (organized by category)
### Code quality
- Items 5, 6, 7 (Mock carve-out, dead helpers, fixture footgun)
### Test coverage
- Items 10, 11, 12, 13 (booted-RA test, strip-the-skip, xpassed, mutation test)
### Plan/doc currency
- Items 8, 9, 14 (STATUS banners, L04 plan fix, plan-vs-impl drift)
### Process gap (the second-order finding)
- Item 4 (fix-inspect-getsource-flakes UNEXECUTED) AND a process note: two atomic plans drafted same day as INDEX both went unexecuted — recommend a "drafted-on-day-N must have status by day-N+7" convention.

## Minor Findings
- Items 15-26 as a bulleted list with one-line each.

## What's NOT Wrong (defensive section)
- Touched-area pyright is 0/0/0
- L01-L05 closure annotations in WHAT-REMAINS.md verified accurate
- new docs/dev/host-rustc-shim.md is accurate
- gitStatus M-flags on spike-result files are stale (working tree is clean)

## Recommended Action Sequence
1. pytest-asyncio install (one line, unblocks 36 tests + validates L03)
2. Execute decision-p5a-mypy (resolves 3 findings at once)
3. Execute fix-inspect-getsource-flakes
4. Code quality batch (Mock carve-out + dead helpers + dual-mode + DRY)
5. Plan-doc closure batch (STATUS banners + addenda + L04 fix)
6. Test depth batch (booted-RA + mutation + strip-the-skip pattern)
7. Docs hygiene (CHANGELOG + indices + banners)

## Out-of-scope (deferred to v0.3.0+)
- Stage 1H continuation (already routed)
- v1.1 marketplace items
- Pre-existing 75 pyright errors in vendor/serena/src/
- LSP issue #1040 ecosystem investigation
```

---

## Key facts to verify (the "tests" Wave 3 Agent B should write)

These are falsifiable claims that the synthesis report will hinge on. Agent B should verify each by reading the cited file/running the cited command:

1. **`pytest-asyncio` is missing from `vendor/serena/.venv`** — verify via `cd vendor/serena && uv pip list | grep -i asyncio`. Expect: empty or `anyio` only, NOT `pytest-asyncio`.

2. **L03 integration test fails silently when `pytest-asyncio` is absent** — verify via `cd vendor/serena && uv run pytest test/integration/test_multi_server_real_adapters_parallel.py::test_broadcast_runs_three_python_servers_in_parallel -v`. Expect: `PytestUnknownMarkWarning` + test failure with "async def functions are not natively supported".

3. **P5a.md verdict line contradicts its measurements** — read `docs/superpowers/plans/spike-results/P5a.md:3,9,12`. Expect: line 3 says "Outcome C - DROP", lines 9-12 show stale_rate=0.00% and p95=4.306s (which match Outcome B thresholds, not C).

4. **All 6 inspect.getsource sites are still raw** — `grep -n "inspect.getsource(cls.apply)" vendor/serena/test/spikes/test_stage_3_t1_rust_wave_a.py vendor/serena/test/spikes/test_stage_3_t2_rust_wave_b.py vendor/serena/test/spikes/test_stage_3_t3_rust_wave_c.py vendor/serena/test/spikes/test_stage_3_t4_python_wave_a.py vendor/serena/test/spikes/test_stage_3_t5_python_wave_b.py vendor/serena/test/spikes/test_stage_2a_t9_registry_smoke.py`. Expect: 6 hits (one per file).

5. **`fix-inspect-getsource-flakes.md` was never executed** — `grep -rn "attach_apply_source\|get_apply_source\|__wrapped_source__" vendor/serena/src vendor/serena/test`. Expect: zero hits.

6. **Dead helpers `_classify_overlap` and `_bucket_unknown_kind`** — `grep -rn "_classify_overlap\|_bucket_unknown_kind" vendor/serena/src vendor/serena/test`. Expect: 1 def + 1 spike-test reference each, ZERO production-code references.

7. **L04 plan still prescribes `addopts`** — read `docs/superpowers/plans/2026-04-26-v020-followups/04-cargo-build-rustc-workaround.md:102-107`. Expect: `addopts = "-p test.conftest_dev_host"` (rejected approach) instead of the actual `pytest_plugins` mechanism.

8. **`pylsp_server.py:154` still says `pylsp_mypy enabled: False`** — read `vendor/serena/src/solidlsp/language_servers/pylsp_server.py:15,154`. Expect: line 15 docstring "pylsp-mypy is DELIBERATELY NOT enabled here — Phase 0 P5a verdict C", line 154 `"pylsp_mypy": {"enabled": False}`.

9. **`is_async_callable` accepts ANY Mock instance** — read `vendor/serena/src/serena/refactoring/_async_check.py:62-76`. Expect: `if isinstance(obj, Mock): return True` (no marker check).

10. **L05 strip-the-skip pattern is the right model for the 13 untreated facades** — spot-check by reading `vendor/serena/test/e2e/test_e2e_stage_3_*.py` for `pytest.skip` patterns. Expect: same shape as the pre-L05 `test_e2e_e1_py_split_file_python.py:87-91` block — `applied!=True → skip`.

11. **2 xpassed tests in `test_serena_agent.py`** — `cd vendor/serena && uv run pytest test/serena/test_serena_agent.py -v 2>&1 | grep -i xpass`. Expect: 2 XPASS reports.

12. **No STATUS banner on any v020-followup plan file** — `head -5` each of `01-basedpyright-dynamic-capability.md`, `02-...md`, `03-...md`, `04-...md`, `05-...md` in `docs/superpowers/plans/2026-04-26-v020-followups/`. Expect: no "STATUS: SHIPPED" / "COMPLETE" markers.

13. **CHANGELOG.md only has [0.1.0] block** — `grep -n "^## \[" CHANGELOG.md`. Expect: single entry `[0.1.0]`.

---

## Out-of-scope for this report

These are real findings but belong in v0.3.0+/v1.1 backlog, not this synthesis:

- **Stage 1H continuation tree** — 6 leaves, ~8,845 LoC, fully scoped in `2026-04-26-stage-1h-continuation/README.md`. All 5 v020-followup preconditions are CLOSED so it's unblocked, but executing it is its own milestone.
- **v11-milestone tree** — 8 leaves, marketplace + persistent checkpoints + Rust+clippy + 3 facades + PEP variants. Hard-gated on Stage 1H continuation per `WHAT-REMAINS.md` §Recommended-sequencing item 5.
- **v2-language-strategies tree** — 5 leaves (TS, Go, C/C++, Java, longtail). Hard-gated on v11-milestone.
- **75 pre-existing pyright errors in `vendor/serena/src/`** — none in touched dirs. Recommended for a separate "pyright residue cleanup" leaf, not blocking v020-followups closure.
- **LSP issue #1040** — ecosystem-owned (upstream solidlsp), 25+ test comments. Cross-cutting risk #1 in `WHAT-REMAINS.md` already tracked.
- **Anthropic native LSP-write integration** — long-horizon deprecation trigger, watch-only.
- **`lspee` 1.0 maturity, `gopls daemon` reuse, plugin-list API** — watch-only items already tracked in `WHAT-REMAINS.md` cross-cutting risks.
- **Hypothesis property-based tests for `compute_file_range`** — nice-to-have, not blocking.
- **`docs/dev/multi-server-coordinator.md` + `docs/dev/lsp-preflight-validation.md`** — useful new dev docs but not closure-blocking.
- **`vendor/serena/README-OVERLAY.md`** — only matters if the engine fork is cloned standalone.

---

*Author: AI Hive(R) — Coordinator agent*
