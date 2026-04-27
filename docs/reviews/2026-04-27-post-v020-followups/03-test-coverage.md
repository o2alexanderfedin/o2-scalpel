# Test Coverage Review — Post v0.2.0 Follow-ups
**Date**: 2026-04-27
**Specialist**: Test Coverage

## Summary

The 60+ new tests for the v0.2.0 follow-ups (L02/L03/L04/L05) are themselves well-written and pass when run in isolation (48/48 across the four new unit-test files; 10/10 for the L05 determinism guard). However, **a critical infrastructure gap masks parallelism evidence**: `pytest-asyncio` is not installed in the `vendor/serena` venv, so every `@pytest.mark.asyncio` test — including L03's centerpiece integration test `test_broadcast_runs_three_python_servers_in_parallel` — silently FAILS at runtime instead of providing the parallelism guarantee the leaf was supposed to lock down. The new tests also lean heavily on mock-based behavior (especially L02 preflight bypassing `__init__`, and the entire L02 rust-analyzer detection class) without an end-to-end booted-server confirmation, and L05 lacks a negative/mutation test that would prove the determinism assertion can actually catch a regression.

## Test suite snapshot

- **Total tests collected**: 2018 (`uv run pytest --collect-only -q`)
- **Focused subset run** (`test/serena test/solidlsp/util test/solidlsp/rust/test_rust_analyzer_detection.py test/conftest_dev_host_test.py test/spikes -m "not e2e"`):
  - **Passed**: 1197
  - **Failed**: **50** — all due to a missing `pytest-asyncio` plugin in the venv, NOT product-code bugs (see Critical finding below)
  - **Skipped**: 8 (legitimate — see "Pre-existing skips" section)
  - **xfailed**: 1 (legitimate — `test_serena_agent.py::TestSerenaAgent` for unreliable F#/Rust LSPs)
  - **xpassed**: **2** — flipped to passing; should be re-evaluated for promoting to plain pass
  - **Wall-clock**: 655s (~11min)
- **New-files-only subset** (the four follow-up test files): 48 passed in 15.43s (zero failures, zero skips)
- **Determinism guard** (`test_e2e_e1_py_determinism.py`): 10/10 passed in 0.43s
- **Slowest tests**: not captured by default — `--durations=10` reporting was suppressed because of the failure tail; Stage 1D fakes + spike T11 dominate when running the full set.

### Critical: pytest-asyncio is not installed

- `vendor/serena/.venv` lists `anyio 4.13.0` and `nest-asyncio 1.6.0` but **NOT `pytest-asyncio`** (uv pip list).
- `vendor/serena/pyproject.toml` `[tool.pytest.ini_options]` does NOT set `asyncio_mode = "auto"` and does not list `pytest-asyncio` as a runtime dep.
- Every `@pytest.mark.asyncio` test fails at runtime with: `async def functions are not natively supported. You need to install a suitable plugin for your async framework, for example: anyio, pytest-asyncio, ...` — and pytest only reports `PytestUnknownMarkWarning` at collection, not a hard error.
- Affected NEW tests:
  - `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:122` — the **only** integration test that proves L03 multi-server async wrapping actually parallelises real adapters. Currently FAILS silently, so the L03 "Amdahl-aware budget" guarantee is unverified on this host.
- Affected pre-existing tests (28 spike tests + 7 v0.2.0-C tests):
  - `test/spikes/test_stage_1d_t0_fixture_smoke.py` (4 tests)
  - `test/spikes/test_stage_1d_t2_broadcast.py` (5 tests)
  - `test/spikes/test_stage_1d_t6_merge_code_actions.py` (6 tests)
  - `test/spikes/test_stage_1d_t7_invariants.py` (1 test)
  - `test/spikes/test_stage_1d_t8_merge_rename.py` (4 tests)
  - `test/spikes/test_stage_1d_t11_e2e_three_server_replay.py` (6 tests)
  - `test/spikes/test_v0_2_0_c_find_symbol_position.py` (7 tests)
  - `test/spikes/test_spike_s6_auto_import_shape.py` (1 test)
- This is the largest test-coverage finding: the project ships **35+ async tests that can never green** under the published venv setup, and the L03 follow-up **introduced one more** without verifying the runner config.

## Coverage gaps in shipped code (per leaf)

### L02 `compute_file_range`
File: `vendor/serena/src/solidlsp/util/file_range.py:25-61`
Test file: `vendor/serena/test/solidlsp/util/test_file_range.py` (9 tests)

Untested behaviours:
- **Non-UTF-8 encodings** — `Path.read_text(encoding="utf-8")` (line 45) silently mis-decodes Latin-1 / Windows-1252 source files with non-ASCII bytes; no test exercises a `UnicodeDecodeError` path.
- **Symlinks** — no test confirms whether `Path.read_text` follows a symlink to a target in a different directory or what happens when the symlink target is missing (would raise `FileNotFoundError` from a different surface; the user-facing behaviour is unverified).
- **Permissions errors** — no test creates a file with `chmod 000` or otherwise unreadable content and asserts the surface error type.
- **Directory-instead-of-file** — `read_text(directory)` raises `IsADirectoryError`; the helper does not document or test this.
- **Very large files / binary files** — no upper-bound test; whole file read into memory has no streaming alternative.
- **UTF-16 character counting** — the docstring (line 38-40) says "Encoding is the LSP default UTF-16; for ASCII-only fixtures the byte count matches"; no test exists that uses a multi-byte UTF-8 character (e.g. emoji) to confirm the helper currently mis-counts in UTF-16-units (the LSP-correct behaviour). This is a documented limitation, but a `pytest.mark.xfail` test would lock the gap so the fix is testable.
- **Mixed line endings in one file** — only homogeneous CRLF and homogeneous LF are tested (lines 55-68); a mixed-LF/CRLF file (common on cross-platform repos) is not exercised.
- **CRLF + lone CR interaction** — `replace("\r\n", "\n").replace("\r", "\n")` (line 54) handles ordering correctly, but no test asserts that ordering with a `\r\r\n` corner case.

### L02 RustAnalyzer preflight (`request_code_actions` override)
File: `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py:211-243`
Test file: `vendor/serena/test/solidlsp/rust/test_rust_analyzer_detection.py:575-654` (3 tests)

Untested behaviours:
- **End-to-end with booted rust-analyzer** — all three preflight tests bypass `__init__` via `RustAnalyzer.__new__(RustAnalyzer)` (line 589) and patch `super().request_code_actions` (`type(adapter).__mro__[1]`). There is **no test** that boots rust-analyzer for real and confirms the preflight raises `ValueError` BEFORE any wire round-trip happens. Without this, a future refactor that reorders the override (e.g. wraps `super()` in a try/except that swallows ValueError) would not be caught by the unit tests.
- **`start` position past EOF** — only `end` is preflighted; an out-of-range `start` would still hit the wire and trigger rust-analyzer's own rejection. The override deliberately validates only `end` (per docstring), but no test pins this contract — a future broadening of the preflight to include `start` would not break any test.
- **Negative coordinates** — `end={"line": -1, "character": 0}` passes through (Python tuple comparison handles negatives) but the test corpus does not pin behaviour.
- **Missing keys** — `end` dict without `"line"` or `"character"` would raise `KeyError`; the user-visible error surface is unverified.
- **Non-rust files** — passing `file="/tmp/foo.py"` (or a non-existent file) goes straight to `compute_file_range` which raises `FileNotFoundError`; no test confirms this is the right surface vs. wrapping it in a more diagnostic `ValueError`.
- The skip path for `rust-analyzer not installed` (`test_rust_analyzer_detection.py:549`) means the integration class never runs locally; no CI evidence is captured.

### L03 `_async_check`
File: `vendor/serena/src/serena/refactoring/_async_check.py:41-105`
Test files: `vendor/serena/test/serena/refactoring/test_multi_server_async_check.py` (12 tests), `test_multi_server_init_validation.py` (6 tests)

Untested edge cases (per the spec brief):
- **Callable class with sync `__call__` but async `__init__`** — pathological but legal; the detector returns `False` (correct because await-time cares about `__call__`), but no test exists to pin this.
- **`functools.partial(async_func)`** — `inspect.iscoroutinefunction(functools.partial(async_fn))` returns **False** in Python ≤ 3.7 and **True** in 3.8+ ONLY for `partial` of a coroutine function. The detector inherits this behaviour but no test pins it, so a future Python upgrade could silently flip the contract.
- **`functools.wraps`-decorated coroutines** — wrapped via `@functools.wraps(async_fn)` should still introspect as async; not tested.
- **Lambdas** — `lambda: 1` returns False (via `callable()` + no `__call__` async); not pinned.
- **Async generator function (`async def f(): yield`)** — `inspect.iscoroutinefunction` returns False for `isasyncgenfunction`; the detector treats it as sync and would raise `TypeError` from the gate — but `broadcast` does NOT iterate, it `await`s, so this is the **correct** behaviour. The test corpus does not assert this, so a permissive change wouldn't be caught.
- **Subclass of `Mock` that overrides `__call__` to be sync** — `isinstance(obj, Mock)` short-circuits to True (`_async_check.py:69`); a subclass that wants strict-sync behaviour cannot opt out, and no test documents this trade-off.
- **`AsyncMock`** vs. `MagicMock` — neither is differentiated; no test confirms the gate behaves identically for both.
- **Bound method on an instance whose class defines `async def`** — covered by `_AsyncOnly.request_code_actions` (lines 43-54). Bound methods on a metaclass or class-level callable are not.

### L03 multi-server parallelism
File: `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py`

Untested behaviours:
- **Currently FAILING due to missing pytest-asyncio** (see Critical finding above) — so the parallelism guarantee for the only path that currently works (Python LSP trio) is **not verified on this host**.
- **Rust + clippy multi-server** — explicitly called out in the L03 plan as v1.1 follow-up. The README's L03 line 11 ("Blocks: 'Rust+clippy multi-server' v1.1 claim") is not yet covered. Only Python servers (pylsp + basedpyright + ruff) appear in `_PYTHON_SERVERS` (lines 68-87).
- **Mixed-language broadcast** — what happens when one server is Rust and another is Python? No test.
- **Single-server broadcast** — degenerate but legal; no test.
- **Empty server pool broadcast** — covered in init test (`test_init_accepts_empty_pool`) but not in broadcast.
- **Slow-start LSP** — basedpyright warm-up is mitigated by an explicit warm-up pass (lines 184-199); no test asserts what happens when one server times out during measurement (existing `_t2_broadcast.py::test_broadcast_one_timeout` is in the asyncio-broken set).
- **Race condition: two concurrent broadcasts** — no test issues two broadcasts in parallel against the same coordinator; race conditions would only show under load.
- **Server crashes mid-broadcast** — kill -9 the LSP process during a broadcast call; no test for this.

### L04 dev-host plugin
File: `vendor/serena/test/conftest_dev_host.py`
Test file: `vendor/serena/test/conftest_dev_host_test.py` (2 tests)

Untested behaviours:
- **Cold-start ordering** — the plugin is loaded via `pytest_plugins = ["test.conftest_dev_host"]` in `vendor/serena/test/conftest.py:32`. There is no test that verifies the plugin loads even when `serena.tools.scalpel_runtime` isn't yet importable (e.g., on a fresh checkout before any dependency install). Per L04 spec line 31 the plugin only touches env vars, so this is low-risk, but there's also no test that the plugin survives a `serena` import failure during pytest_configure.
- **Ambiguous truthy values** — only `O2_SCALPEL_LOCAL_HOST=1` is tested. What about `=true`, `=yes`, `=ON`? The current code (`conftest_dev_host.py:30`) uses `== "1"` exactly; this is documented but not pinned by a test that asserts `O2_SCALPEL_LOCAL_HOST=true` does NOT activate.
- **Pre-existing `CARGO_BUILD_RUSTC` value** — the plugin uses `setdefault` so an existing value wins; no test verifies this path. A user with `CARGO_BUILD_RUSTC=foo` exported globally would see `foo`, not `rustc` — and there's no test to lock this contract.
- **Non-pytest contexts** — the plugin is pytest-specific; no test confirms what happens if loaded standalone (would no-op at import time, since `pytest_configure` is hook-only — but unverified).

### L05 E1-py determinism guard
File: `vendor/serena/test/e2e/test_e2e_e1_py_determinism.py`

Untested behaviours:
- **Negative / mutation test**: there is no test demonstrating the assertion at line 49 (`assert payload.get("applied") is True`) actually FAILS when `applied=False` is returned. A mutation-test-style smoke (e.g., monkeypatch the facade to return `applied=False` once, confirm the parametrize iteration fails loudly) would prove the guard catches what it claims to catch. As written, if `mcp_driver_python.split_file` were reverted to the pre-Stage-2B always-`applied=False` behaviour, the test would fail — but that's an indirect proof.
- **Cross-fixture determinism** — only one fixture (`calcpy_e2e_root`) and one canonical `groups` payload are exercised; the determinism claim is "this canonical 4-way split is deterministic," not "the splitter is deterministic in general."
- **N=10 vs higher iteration counts** — the diagnostic harness at `test/e2e/_e1_py_diagnostic.py` ran 30 iterations to justify the strip-the-skip change; the in-suite guard is parametrized for only 10. If the flake rate is e.g. 2%, 10 iterations have a ~18% miss rate; this is a deliberate trade-off but worth pinning in a comment with the empirical pass-rate ledger.
- **Run-to-run side-effects** — each parametrized invocation of `test_e1_py_split_applies_every_run` runs against a fresh `mcp_driver_python` fixture? Not asserted; if the fixture is session-scoped, the second iteration is testing a dirty state that's already been split. Worth checking the fixture scope.
- **Concurrency** — no test that runs the determinism guard in parallel with another e2e test against the same checkpoint dir.
- **Different `parent_layout` / `reexport_policy`** — the determinism contract is locked only for `parent_layout="file"` + `reexport_policy="preserve_public_api"`; no test pins the matrix.

## Mock-heaviness audit

| Test file | Risk | Note |
|---|---|---|
| `test_rust_analyzer_detection.py` (TestRustAnalyzerDetection class, lines 32-518) | **HIGH** | All 12 detection tests use 4-6 nested `with patch(...)` contexts. Behaviour verification reduces to "the function returned the path we mocked back." There is **no test that exercises the real filesystem** of a representative install layout. The `TestRustAnalyzerDetectionIntegration` class (line 521) is the only real-fs test, and it's `pytest.skip`-gated. |
| `test_rust_analyzer_detection.py::TestRustAnalyzerPreflightPositionValidation` (lines 575-654) | MEDIUM | Bypasses `__init__` via `__new__` and patches `super().request_code_actions`. Behaviour is verified (preflight raises before wire), but `parent_call.assert_not_called()` is itself a mock-interaction assertion. An end-to-end booted-server smoke would be stronger. |
| `test_multi_server_async_check.py` | LOW | Uses real `_SyncOnly` / `_AsyncOnly` classes, real `_AsyncAdapter` instances. `MagicMock` only appears in the documented opt-out path. Behaviour-driven. |
| `test_multi_server_init_validation.py` | LOW | Same pattern — real classes, real coordinator instantiation. Behaviour-driven. |
| `test_multi_server_real_adapters_parallel.py` | LOW | Real LSP processes booted via `ExitStack`, real `_AsyncAdapter`, real wire calls. Strongest behavioural test in the batch — and currently FAILING silently due to missing pytest-asyncio. |
| `test_file_range.py` | LOW | All tests write real files via `tmp_path` and assert real return values. Pure behaviour. |
| `test_conftest_dev_host_test.py` | LOW | Spawns a child pytest via `subprocess.run` to verify env-var contract. Strongest possible behaviour verification for a pytest plugin. |
| `test_e2e_e1_py_determinism.py` | LOW | Real driver, real facade, real apply. The only weakness is the lack of a negative-test as noted above. |

## Pre-existing skips / xfails

Total `pytest.skip` / `xfail` decorators: ~80+ across `test/`. Categorised:

### Legitimate (environment / platform / opt-in)

- All `@pytest.mark.skipif(shutil.which("...") is None and not is_ci, ...)` skips for missing toolchains: `opam`, `fpc`, `terraform`, `verible-verilog-ls`, `regal`, `elm`, `R`. **Keep.**
- All `@pytest.mark.skipif(IS_WINDOWS, ...)` skips for unix-only paths in `test_rust_analyzer_detection.py` and `test_zip.py`. **Keep.**
- `test/integration/conftest.py:102` and `test/e2e/conftest.py:95`: skip if required binary not on PATH. **Keep** — partial dev environments shouldn't fail the gate.
- `test/spikes/test_stage_1i_t6_uvx_smoke.py:37,43,45,59`: skip if `uvx` or smoke script missing. **Keep.**
- `test/spikes/test_stage_1g_t4_apply_capability.py:62,83,122` + `test_stage_1g_t3_capability_describe.py:34`: skip when capability catalog is empty. **Keep** — degenerate state, not a regression.
- `test/spikes/test_stage_1c_t9_end_to_end.py:62,92,120`: skip if Phase 0 seed fixtures missing. **Keep.**
- `test/spikes/test_stage_1f_t4_baseline_round_trip.py:92`: skip the regenerate path unless flag passed. **Keep.**
- `test/spikes/test_stage_1a_t11_is_in_workspace.py:60`: skip on platform without symlink support. **Keep.**
- `test/serena/util/test_exception.py:31`: skip when `os.uname` unavailable. **Keep.**
- `test/serena/test_symbol_editing.py:454`: skipif win32 for nixd. **Keep.**

### Possibly masking / worth re-evaluating

- **`test/solidlsp/elixir/`** (`test_elixir_symbol_retrieval.py`, `test_elixir_basic.py`, `test_elixir_ignored_dirs.py`, `test_elixir_integration.py`): 14 in-test `pytest.skip("Could not find ... function/symbol")` calls. These hide fixture drift behind a soft skip — if the LSP stops returning ANY symbols for these fixtures, every test silently skips and the gate is green. **Recommend**: tighten to a `pytest.fail` once the fixture is stable, or move the symbol-presence check to a session-scoped fixture that fails loudly once.
- **`test/solidlsp/erlang/test_erlang_symbol_retrieval.py`** (10 in-test skips, lines 46-428): same pattern as elixir.
- **`test/solidlsp/vue/`** (12 in-test skips): "test fixture may need updating" — the skip reason itself flags drift that should be addressed, not papered over.
- **`test/solidlsp/dart/test_dart_basic.py:61,154`**: "Language server doesn't support definition lookup for this case" — should be `xfail(strict=True)` so a future LSP improvement flips loudly.
- **`test/serena/test_serena_agent.py:220,231,329,340`**: 4 `xfail`s for F#, Rust, TypeScript LSP unreliability (issue #1040). Two of these xpassed in our run (the `2 xpassed` count) — **these have flipped and should be promoted to plain pass**, otherwise future regressions go silent.
- **`test/solidlsp/elixir/test_elixir_symbol_retrieval.py:260`**: `xfail(reason="Flaky test, sometimes fails with an Expert-internal error")` — non-strict xfail; if it ever passes consistently the contract should tighten.
- **`test/solidlsp/nix/test_nix_basic.py:121`** + **`test/solidlsp/fsharp/test_fsharp_basic.py:55,92,115,129`**: `xfail(is_ci, reason="Test is flaky")`. Each ties to issue #1040; CI-only xfail means local devs see real pass/fail, but CI is the gating signal — these should be tracked for stabilisation.
- **`test/e2e/test_wall_clock_budget.py:40,53`**: skip if no `wall_clock_record` entries. If no e2e ran, this passes vacuously — **masking**: should fail with a clear "no telemetry collected" once e2e is mandatory.
- **`test/e2e/test_e2e_stage_3_*`** (Python and Rust E13-E16, 13 skip sites total): facade returns `applied!=True` → skip. This is the same pattern Leaf 05 just stripped from the E1-py path. The remaining E2/E3/E4/E5/E8/E9/E10/E11/E13/E14/E15/E16 facades are still `pytest.skip`-protected. **Recommend**: apply the L05 treatment (mutation-style determinism guard + strip skip) leaf-by-leaf to lock the contract.
- **`test/integration/test_multi_server_real_adapters_parallel.py:115`**: `pytest.xfail` when binaries missing — per the test docstring, this is the spec-mandated treatment. **Keep but verify**: the xfail message says "This test requires all three booted to prove parallelism" — fine, but this xfail is moot today because the test fails earlier on missing pytest-asyncio.

## Missing test categories

1. **Concurrency / race conditions** — no test issues two `coord.broadcast` calls concurrently against the same coordinator; no test races a checkpoint apply against a checkpoint rollback; no test triggers the L02 preflight from two threads simultaneously.
2. **Cold-start / first-call ordering** — L04 plugin is auto-loaded by `pytest_plugins`; no test verifies what happens if the plugin import itself fails (e.g., a future refactor introduces a circular import). No test for the L02 helper being called before any project is initialised.
3. **Cross-language multi-server** — L03 plan explicitly defers Rust+clippy. No test exercises a multi-language pool (mixed Python + Rust adapters).
4. **Performance regression guards** — only L03's parallelism budget exists. There is no:
   - Walltime budget per LSP startup
   - Memory ceiling per coordinator
   - Drift assertion that `compute_file_range` stays O(file size) (e.g., a 10MB file budget)
5. **Error-path / fault-injection** — no test kills an LSP process mid-broadcast, no test simulates `JSONDecodeError` from a wire response, no test confirms the L02 preflight surfaces the right error type when `compute_file_range` itself raises.
6. **Property-based tests** — `compute_file_range` is a perfect candidate for `hypothesis` (random text → invariants: start always `(0,0)`, end position is monotone in file size, etc.). None present.
7. **Negative tests for new gates** — L03's `assert_servers_async_callable` has only positive + happy-path negative coverage; no fuzz over server method names, no test that confirms the loud-error message would survive a future refactor that drops the `_AsyncAdapter` hint.
8. **Coverage instrumentation** — no `pytest-cov` config visible; the project has no coverage-floor gate. Without one, "60+ new tests" is a count, not a coverage delta.

## Recommendations (prioritized)

### Critical (do next)

1. **Install `pytest-asyncio` in `vendor/serena/.venv` and set `asyncio_mode = "auto"` in `pyproject.toml`.** Without this, the L03 integration test (`test_multi_server_real_adapters_parallel.py`) provides ZERO parallelism evidence on this host — and ~35 pre-existing async tests are silently red. This is a one-line config fix that unblocks the entire async test corpus. Verify with:
   `uv add --dev pytest-asyncio && uv run pytest test/integration/test_multi_server_real_adapters_parallel.py`
2. **Promote the 2 xpassed tests** (in `test_serena_agent.py`) to plain pass by removing the `@pytest.mark.xfail` decorator. Document why in the commit message. Otherwise a future regression in F#/Rust/TS support will be invisible.
3. **Add a negative/mutation test for L05 determinism guard.** A test that monkeypatches `mcp_driver_python.split_file` to return `applied=False` once and asserts the parametrize iteration fails loudly. Locks the assertion's load-bearing-ness (~10 lines).

### Important (next sprint)

4. **End-to-end booted-rust-analyzer test for L02 preflight** — boot rust-analyzer (gated on `which rust-analyzer`), call `request_code_actions` with an out-of-range `end`, and assert `ValueError` is raised with no LSP traffic. Currently all 3 preflight tests bypass `__init__` via `__new__`.
5. **L03 cross-language test** (Rust + clippy) — covers the v1.1 claim the README explicitly blocks.
6. **L02 non-UTF-8 / encoding tests** for `compute_file_range` — at minimum a Latin-1 file test to lock the `UnicodeDecodeError` surface. Add an xfail UTF-16 character-counting test to track the documented limitation.
7. **Strip skip pattern from remaining E2E facades** — apply L05's treatment to E2/E3/E4/E5/E8/E9/E10/E11/E13/E14/E15/E16 facades leaf by leaf. 13 skip sites currently mask facade flakes.
8. **Tighten Elixir/Erlang/Vue fixture-presence skips** — move the "could not find symbol X" check to a session-scoped fixture that fails once if drifted. 36 in-test skips currently mask LSP/fixture drift.

### Minor

9. **Hypothesis property-based tests for `compute_file_range`** — random text in, invariants out. ~30 lines, free regression coverage.
10. **L04 plugin truthy-value lock** — add a test for `O2_SCALPEL_LOCAL_HOST=true` (NOT activate) and `O2_SCALPEL_LOCAL_HOST=` (NOT activate) to pin the strict-`"1"` contract.
11. **L03 detector edge-case lock** — add 5 tests (`functools.partial`, lambda, async generator function, callable class with sync `__call__`, AsyncMock vs MagicMock differentiation). ~30 lines total.
12. **Add `pytest-cov` and a coverage floor** — even a 50% floor on `vendor/serena/src/serena/refactoring/` would surface untested merge / broadcast paths.
13. **`--durations=10` in CI default** — slowest-test reporting is currently absent from the commit-trail; promote to default so regressions in test wall-clock are visible.

## File-level pointers (for the coordinator)

- L02 helper source: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/solidlsp/util/file_range.py`
- L02 preflight source: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/solidlsp/language_servers/rust_analyzer.py:211-243`
- L03 detector source: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/_async_check.py`
- L04 plugin source: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/conftest_dev_host.py`
- L05 determinism guard: `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/e2e/test_e2e_e1_py_determinism.py`
- pyproject (missing asyncio_mode): `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/pyproject.toml` (`[tool.pytest.ini_options]` block)
- Root conftest (auto-loads dev-host plugin): `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/conftest.py:32`
