# Code Quality Review — Post v0.2.0 Follow-ups

**Date**: 2026-04-27
**Specialist**: Code Quality
**Scope**: Touched-area code quality + pre-existing residue
**Tag reviewed**: `stage-v0.2.0-followups-complete` (parent `0435ac8`, submodule `a2cece4a`)

---

## Summary

The shipped batch (Leaves 02 / 03 / 04 / 05) is in good shape: every touched module is **0 / 0 / 0** under pyright, has TDD-grade tests, and the cross-leaf docs/scope concerns flagged previously are resolved. The remaining risks are confined to (a) **two pre-existing dead-code helpers** in `multi_server.py` that are tested via spike tests but never wired into production, (b) a **dual-mode test fixture** with a silent-fallback footgun, (c) a **MagicMock carve-out** that weakens the new async-callable guarantee for ANY caller that happens to hand the coordinator a Mock (not just the one cited test), (d) a known **non-UTF-8 blind spot** in `compute_file_range`, and (e) ~75 pre-existing pyright errors elsewhere in `vendor/serena/src/`, **none** in the touched directories.

Biggest residual risks, in order: (1) `is_async_callable` Mock carve-out is broader than its justification; (2) two dead helpers (`_classify_overlap`, `_bucket_unknown_kind`) keep growing test surface that production never exercises; (3) `compute_file_range` will raise `UnicodeDecodeError` (not a typed contract) on Latin-1 / mixed-encoding sources.

---

## Pre-existing residue (not addressed by recent batch)

| Severity | Location | Issue | Recommended action |
|---|---|---|---|
| **Medium** | `vendor/serena/src/serena/refactoring/multi_server.py:516` | `_classify_overlap` is dead in `src/` — only referenced by `test/spikes/test_stage_1d_t10_disagreements.py`. The spec it implements (§11.2 case 1) was never wired into `merge_and_validate_code_actions`. | Either (a) wire it into Stage 2 dedup so `subset_lossless` / `subset_lossy` actually drives a decision, or (b) delete it + the spike tests. The current state is "tested code that does nothing." |
| **Medium** | `vendor/serena/src/serena/refactoring/multi_server.py:562` | `_bucket_unknown_kind` is dead in `src/` — only referenced by the same spike test file. `merge_code_actions` already uses `_normalize_kind` for the priority lookup; this helper would only matter if the bucket key were `_bucket_unknown_kind(kind)` instead of `_normalize_kind(kind)`. | Same as above: wire or delete. The "kind:null/unrecognized → quickfix.other" §11.2 row is currently silently absent from the merger. |
| **Medium** | `vendor/serena/src/solidlsp/util/metals_db_utils.py:155, 185, 194` | 5 pre-existing pyright errors: 4 × `psutil possibly unbound` (psutil import is inside a `try/except ImportError` but used unconditionally) + 1 × `port for class tuple[()]`. | Move `psutil` to a real soft-dependency pattern: `try: import psutil except ImportError: psutil = None` and gate use behind `if psutil is None: raise RuntimeError(...)`. Independent of this batch — but listed because the cross-leaf review explicitly called these out. |
| **Low** | `vendor/serena/src/solidlsp/language_servers/rust_analyzer.py:747` | Pre-existing TODO from upstream Serena: "Should we wait for `language/status: ProjectStatus OK` before proceeding?" Not introduced by L02 but lives in the file L02 modified. | No action needed for v0.2.0 follow-ups — leave for a future RA-startup hardening pass. |

## Architectural risks from recent leaves (still open)

| Severity | Location | Risk | Why it matters |
|---|---|---|---|
| **High** | `vendor/serena/src/serena/refactoring/_async_check.py:62-76` (`is_async_callable`) | The `isinstance(obj, Mock)` carve-out (line 69) treats EVERY `Mock` / `MagicMock` instance as async-callable. Justification in the docstring cites *one* test file (`test_v0_2_0_c_find_symbol_position.py`). In practice the gate now silently passes ANY Mock-shaped object — including future production code that happens to construct a Mock by accident. | The whole point of L03 is to surface "raw sync server" misuse loudly. A Mock that returns a list (the literal failure mode the gate exists to catch) would slip through. **Tighten** by either (a) requiring a marker attribute (`_o2_async_mock = True`) the test sets explicitly, or (b) special-casing only in `_AWAITED_SERVER_METHODS`-named accesses on a Mock when those attributes haven't been pre-configured by the test. |
| **High** | `vendor/serena/test/integration/conftest.py:186-221` (`whole_file_range` fixture) | Dual-mode footgun: parametrized via `indirect=True` it returns a precise `(start, end)` from `compute_file_range`; **unparametrized** it returns `(0, 0)..(10_000, 0)`. Future tests that forget `indirect=True` against a strict server (rust-analyzer) will get the giant fallback and the `RustAnalyzer.request_code_actions` preflight will (correctly) raise `ValueError("position {...} out of range")`. The failure mode is loud, **but** the silent-fallback path is undiscoverable without reading the docstring. | Recommend: drop the unparametrized fallback — make `request.param` mandatory. The single legacy caller `test_smoke_python_codeaction.py:22` would have to switch to `indirect=True` or call `compute_file_range` directly. The "ruff clamps" justification for the fallback is fragile (other clamping LSPs may not). Single-mode > dual-mode here. |
| **Medium** | `vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py:276-292` | The parallelism budget asserts only "broadcast saves >= 10% of theoretical max save". This is generous enough to hide a real regression where parallelism degrades from 100% to ~12% of theoretical-max (still passes the gate). The docstring acknowledges the prior 50% midpoint flaked under combined-suite load. | Acceptable for now (the test mainly exists to prove "not round-robin"), but consider tightening the budget once `pylsp-rope` indexing dominance is amortised differently — or split into two assertions: (a) `parallel < 0.95 × serial` (regression detector) and (b) `parallel < max_single + 50ms` (parallelism-quality detector with a fixed-overhead head-room). |
| **Medium** | `vendor/serena/src/solidlsp/util/file_range.py:45` (`compute_file_range`) | `Path(path).read_text(encoding="utf-8")` will raise `UnicodeDecodeError` on Latin-1 / mixed-encoding source files. Not in the public contract — no `:raises UnicodeDecodeError:` line, no type guard. Rust source is conventionally UTF-8 so the rust-analyzer preflight is safe in practice, but the helper sits in `solidlsp/util/` and will be reused. | Add `UnicodeDecodeError` to the docstring's `:raises:` list, or (better) catch and rethrow as `ValueError(f"compute_file_range: {path} is not valid UTF-8 ({exc})")` with a deterministic exception type. Same change should fall back to byte-counting via `errors='surrogateescape'` for maximum permissiveness. |

## New smells / TODOs / FIXMEs found

| Severity | Location | Smell |
|---|---|---|
| **Low** | `vendor/serena/src/serena/refactoring/multi_server.py:897` | `except BaseException as exc:  # noqa: BLE001` inside `_one()`. Catching `BaseException` (not `Exception`) silently swallows `SystemExit` / `KeyboardInterrupt` and reports them as per-server errors. Other broad-excepts in the file use `Exception` — this one stands out. Either narrow to `Exception` or add a `raise` re-raise for `KeyboardInterrupt` / `SystemExit`. |
| **Low** | `vendor/serena/src/serena/refactoring/multi_server.py:1053, 1072, 1176` | Three `# type: ignore[arg-type]` on `provenance=provenance`. The fallback `else "pylsp-base"` makes the runtime value always one of the literal set, but pyright can't see it. Consider a small `_coerce_provenance(sid: str) -> ProvenanceLiteral` helper with a `cast` localised in one place — removes the three ignores and centralises the literal list (which also appears verbatim three times: lines 1042-1043, 1061-1062, 1162-1163 — DRY violation). |
| **Low** | `vendor/serena/src/serena/refactoring/multi_server.py:1042-1043, 1061-1062, 1162-1163` | The literal tuple `("pylsp-rope", "pylsp-base", "basedpyright", "ruff", "pylsp-mypy", "rust-analyzer")` is repeated three times to gate the `provenance` fallback. Should reference `typing.get_args(ProvenanceLiteral)` instead, so adding a server requires editing one place. |
| **Low** | `vendor/serena/src/serena/tools/scalpel_runtime.py:62-94` (`_AsyncAdapter.__getattr__`) | Every attribute lookup goes through `__getattr__` and rebuilds the closure on every call. Cheap, but a hot-path optimisation could `functools.cache` the coroutine wrapper per attribute. YAGNI-acceptable for now. |
| **Low** | `vendor/serena/test/conftest_dev_host.py:29` | `del config  # unused; required by pytest hook signature` is correct but unidiomatic — pytest hooks routinely accept `**kwargs` to absorb unused params. Not a blocker. |

## Pyright state across `src/`

- **Touched-area only** (`src/serena/refactoring/`, `src/serena/tools/scalpel_runtime.py`, `src/serena/tools/scalpel_facades.py`, `src/solidlsp/util/file_range.py`, `src/solidlsp/language_servers/rust_analyzer.py`): **0 errors / 0 warnings / 0 informations**.
- **Whole `vendor/serena/src/`**: **75 errors / 0 warnings / 0 informations** — entirely pre-existing residue from upstream Serena, none introduced by this batch. Categorised:
  - 12 × `reportTypedDictNotRequiredAccess` on LSP wire-type access (`textDocumentSync`, `triggerCharacters`, `resolveProvider`, etc.) — protocol-level optional fields.
  - 11 × `reportPossiblyUnboundVariable` (fortran / fsharp / julia / pascal / metals_db_utils — try/except imports used unconditionally).
  - 9 × `reportAttributeAccessIssue` on optional Apple frameworks (`pywebview` / `dashboard` NSApplication imports).
  - 6 × `reportMissingImports` for the optional `agno` integration (entirely deferred).
  - 5 × `reportOptionalMemberAccess` on `solidlsp/ls_process.py` (`process.returncode` / `process.stderr` without None-guards).
  - Remaining 32 spread across upstream adapters (TypeScript / Vue / Solargraph / Bash / Clangd / etc.) — known upstream debt.
- **No ★ pyright info hints** in the touched files (clean per the project's "all errors must be fixed" rule).

## Test fixtures touched but not reverted

- `docs/superpowers/plans/spike-results/P5a.md`, `S1.md`, `S4.md`: parent working tree shows these as `M` in the gitStatus snapshot, but a fresh `git status` on both parent and submodule reports **clean** (`nothing to commit, working tree clean`). The `M` status was stale from the gitStatus capture; the spike re-runs were committed in `a53adb2`. **No fixture residue.**
- `vendor/serena/test/integration/conftest.py:186-221`: not a residue — the `whole_file_range` fixture was *intentionally* converted to dual-mode by L02. Footgun risk listed above under "Architectural risks."
- `vendor/serena/test/conftest.py:32`: `pytest_plugins = ["test.conftest_dev_host"]` is the new opt-in plugin wiring from L04. Not residue — committed and tested via `test/conftest_dev_host_test.py`.

## Recommendations (prioritized)

### Critical
*(none — no production-breaking issues)*

### Important
1. **Tighten `is_async_callable` Mock carve-out** (`vendor/serena/src/serena/refactoring/_async_check.py:69`). Replace `isinstance(obj, Mock)` with a marker-attribute opt-in, e.g. `getattr(obj, "_o2_async_callable", False)`, and update `test_v0_2_0_c_find_symbol_position.py` (3 sites) to set the marker. Restores the gate's "loud TypeError on raw sync misuse" guarantee for accidental Mock objects in production.
2. **Resolve dead helpers** (`multi_server.py:516`, `:562`). Either (a) wire `_classify_overlap` into Stage-2 dedup so the §11.2 case-1 spec actually applies, and `_bucket_unknown_kind` into `merge_code_actions`'s bucket key, or (b) delete both helpers + their spike test (`test_stage_1d_t10_disagreements.py`). Current state is "tested but unused" — fails YAGNI both ways.
3. **Drop `whole_file_range` unparametrized fallback** (`vendor/serena/test/integration/conftest.py:215-218`). Migrate the one legacy caller to `indirect=True` (or to a direct `compute_file_range` call). Removes a silent-fallback footgun the next test author will hit.
4. **Document `compute_file_range` UTF-8 contract** (`vendor/serena/src/solidlsp/util/file_range.py:25-45`). Add `:raises UnicodeDecodeError:` to the docstring or wrap with a typed `ValueError` re-raise. Prevents callers from being surprised by the latent decode failure.

### Minor
5. **DRY the provenance literal tuple** (`multi_server.py:1042-1043, 1061-1062, 1162-1163`). Replace three copies with `typing.get_args(ProvenanceLiteral)`; remove the three `# type: ignore[arg-type]` ignores via a small `_coerce_provenance` helper.
6. **Narrow the broad except** (`multi_server.py:897`). Change `except BaseException` to `except Exception` in `_one()` so `KeyboardInterrupt` / `SystemExit` propagate as expected. Aligns with the file's other broad-excepts.
7. **Tighten the parallelism-budget assertion** (`test_multi_server_real_adapters_parallel.py:282`). Add a complementary `parallel < 0.95 × serial` assertion so a regression from 100% to 12% of theoretical-max would be caught.
8. **Sweep the 5 pre-existing pyright errors in `metals_db_utils.py`** (lines 155, 185, 194). Out of scope for v0.2.0 follow-ups but listed because the cross-leaf reviewer mentioned them. Recommend a separate "pyright residue cleanup" leaf — bundle with the other 70 src/ errors if desired.

---

**Files referenced** (all absolute paths):
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/_async_check.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/refactoring/multi_server.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_runtime.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_facades.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/solidlsp/util/file_range.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/solidlsp/util/metals_db_utils.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/solidlsp/language_servers/rust_analyzer.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/integration/conftest.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/integration/test_multi_server_real_adapters_parallel.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/serena/refactoring/test_multi_server_async_check.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/spikes/test_v0_2_0_c_find_symbol_position.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/spikes/test_stage_1d_t10_disagreements.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/conftest_dev_host.py`
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/conftest_dev_host_test.py`
