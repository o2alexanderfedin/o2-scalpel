# Agent D — Tech-Debt & Flake Inventory for o2-scalpel/vendor/serena

**Date:** 2026-04-26  
**Scope:** Defects, debt markers, skipped tests, type-safety gaps, and CI exclusions under `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/`  
**Read-only analysis** — no code modifications.

---

## 1. Skipped Tests Inventory

### Summary
- **Total skips/xfails found:** 150+ across test suites
- **Categories:** environment/tool availability (110+), LSP reliability/flakiness (25+), WIP/stub features (5+), by-design conditional tests (10+)
- **E2E critical gaps:** 2 known (host-cargo, LSP-startup per project memory)

### Skips by Category

#### A. Tool/Environment Availability (110+ hits)
Most are conditional on installed tools/languages; these are **by-design**, not debt:

| File:Line | Test Name | Suite | Reason | Category |
|-----------|-----------|-------|--------|----------|
| conftest.py:251 | `clojure_cli_available` | solidlsp | Clojure CLI not installed | tool-availability |
| conftest.py:260 | Kotlin marker | solidlsp | Kotlin LSP JVM crashes on restart in CI | LSP-reliability |
| conftest.py:261 | Lean4 marker | solidlsp | Lean not installed | tool-availability |
| ocaml_basic.py:13 | OPAM check | solidlsp | OPAM unavailable | tool-availability |
| terraform_basic.py:19 | Terraform check | solidlsp | Terraform CLI unavailable | tool-availability |
| pascal_basic.py:25,30 | Pascal tests | solidlsp | pasls/fpc unavailable | tool-availability |
| zig_basic.py:20,144,243,271 | Zig tests (4x) | solidlsp | Windows skip (ZLS disabled) | platform-specific |
| nix_basic.py:18 | Nix tests | solidlsp | Windows skip (nil unavailable) | platform-specific |
| systemverilog_basic.py:268 | verible check | solidlsp | verible-verilog-ls unavailable | tool-availability |
| al_basic.py:14 | AL tests | solidlsp | AL tests disabled | tool-availability |
| clojure_basic.py:13,191 | Clojure (2x) | solidlsp | Clojure tests disabled | tool-availability |
| elixir_*.py:14,20 | Elixir suite (4x) | solidlsp | Elixir LS unavailable | tool-availability |
| dart_basic.py:61,154 | Dart (2x) | solidlsp | LS limitation (cross-file def) | LSP-limitation |
| perl_basic.py:12,54 | Perl (2x) | solidlsp | Perl LS Windows unsupported | platform-specific |
| vue_*.py (8x) | Vue symbol/rename (8x) | solidlsp | Symbol not found in fixture | test-fixture-gap |
| rust_analyzer_detection.py:135,164,193,247,301,549 | Rust detect (6x) | solidlsp | Platform-specific, ra not installed | platform-specific |
| cpp_basic.py:33,91 | C++ (2x) | solidlsp | clangd/ccls unavailable | tool-availability |
| swift_basic.py:24,104,127,149 | Swift (4x) | solidlsp | Swift unavailable or flaky in CI | platform-specific / LSP-reliability |
| csharp_basic.py:353 | C# tests | solidlsp | Repository not found | test-fixture-gap |
| julia_basic.py:11 | Julia tests | solidlsp | Julia unavailable | tool-availability |
| groovy_basic.py:25,30 | Groovy (2x) | solidlsp | Repository not found | test-fixture-gap |
| **TOTAL (subcategory A)** | **~110+** | | | |

#### B. LSP Reliability / Flakiness (25+ hits)
**These are DEBT — flaky tests that should either be fixed or made deterministic:**

| File:Line | Test Name | Suite | Reason | xfail/skip |
|-----------|-----------|-------|--------|-----------|
| nix_basic.py:121 | hover test | solidlsp | "Test is flaky" in CI | xfail |
| fsharp_basic.py:55,92,115,129 | F# tests (4x) | solidlsp | "Test is flaky" in CI; TODO #1040 | xfail |
| fsharp_basic.py:16 | F# suite | solidlsp | "F# language server is currently unreliable" | skipif(is_ci) |
| kotlin_basic.py:16 | Kotlin tests | solidlsp | "JVM restart unstable on CI" | skipif(is_ci) |
| swift_basic.py:104,127,149 | Swift (3x) | solidlsp | "Test is flaky in CI"; TODO #1040 | xfail(is_ci) |
| ansible_basic.py:56 | Ansible docs | solidlsp | "ansible LS lacks basic functionality" | xfail |
| erlang_ignored_dirs.py:28,45,72 | Erlang (3x) | solidlsp | "Known timeout on Ubuntu CI" | xfail(strict=False) |
| test_serena_agent.py:220,231,340 | Serena tests (3x) | serena | "LS unreliable"; TODO #1040 (F#, Rust, TS) | xfail |
| test_serena_agent.py:329 | TypeScript | serena | "TypeScript LS unreliable"; NOTE Testing; may be resolved by #1120 | xfail(False) |
| **TOTAL (subcategory B)** | **~25+** | | | |

**Debt subcategory B action items:**
- Issue #1040 referenced in 10+ test comments → root cause investigation needed
- Kotlin JVM restart issue (CI-specific) → may be GHA runner memory/concurrency
- F# language server reliability → external project issue; Stage 1 may remove F# from MVP

#### C. WIP / By-Design Skips (20+ hits)
Tests that are incomplete or conditionally enabled:

| File:Line | Test Name | Suite | Reason |
|-----------|-----------|-------|--------|
| test_stage_1c_t9_end_to_end.py:62,92,120 | E2E (3x) | spikes | Fixtures missing (seed, calcrs); "run Phase 0 first" |
| test_stage_1j_t11_make.py:17 | Make smoke | spikes | skipif(not has_o2_scalpel_plugin) |
| test_stage_1j_t12_e2e.py:23 | E2E T12 | spikes | skipif(ci=True and not supported_configs) |
| test_stage_1i_t6_uvx_smoke.py:37,43,45,59,62 | uvx smoke (5x) | spikes | "uvx/script/toml missing"; run T6 step 2 first |
| test_stage_1g_t4_apply_capability.py:62,83,122 | Capability (3x) | spikes | "Capability catalog empty in this build" |
| test_stage_1g_t3_capability_describe.py:34 | Capability describe | spikes | "Capability catalog empty in this build" |
| test_stage_1f_t4_baseline_round_trip.py:92 | Baseline trip | spikes | "pass --update-catalog-baseline to regenerate" |
| test_stage_1j_t10_golden.py:40 | Golden | spikes | "Updated snapshot" (git-workflow sentinel) |
| **E2E suite skips (conftest.py:83+)** | **E2E gate checks** | e2e | Markers + skipif checks for Stage 2B reqs |
| **TOTAL (subcategory C)** | **~20+** | | |

---

## 2. The 6 inspect.getsource Flakes (Project Memory)

### Located inspect.getsource Calls in Test Code

Grep found **exactly 6 uses in test spikes** (not in .venv):

| File:Line | Test Name | Context |
|-----------|-----------|---------|
| test_stage_3_t1_rust_wave_a.py:374 | `src = inspect.getsource(cls.apply)` | Fetches class method source for introspection |
| test_stage_3_t2_rust_wave_b.py:201 | `src = inspect.getsource(cls.apply)` | Fetches class method source for introspection |
| test_stage_3_t3_rust_wave_c.py:247 | `src = inspect.getsource(cls.apply)` | Fetches class method source for introspection |
| test_stage_3_t4_python_wave_a.py:181 | `src = inspect.getsource(cls.apply)` | Fetches class method source for introspection |
| test_stage_3_t5_python_wave_b.py:261 | `src = inspect.getsource(cls.apply)` | Fetches class method source for introspection |
| test_stage_2a_t9_registry_smoke.py:63 | `src = inspect.getsource(cls.apply)` | Fetches class method source for introspection |

**Root cause hypothesis:**
All 6 are identical patterns: fetching `cls.apply` source in Stage 2A/3 test fixtures. These are **tool metaclass inspection** calls where `apply` is a dynamically-generated refactoring method. Flakiness likely stems from:
1. **Dynamic code generation** — if `cls.apply` is synthesized or wrapped at test initialization, source introspection may fail or return wrapped stubs.
2. **Compiled/cached bytecode mismatch** — if tests run against both source and pyc, `getsource` may fail on `.pyc`-only loads.
3. **Decorator stacking** — if `cls.apply` is wrapped via `@property` or `@functools.wraps`, source line map corruption is common.

**Evidence from source code:**
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/tools/scalpel_facades.py:1002` documents:  
  > "the safety call stays visible in `inspect.getsource(cls.apply)`)."  
  This confirms the pattern is intentional for safety analysis, suggesting the flake may stem from the safety-call injection itself.

**Project memory notes:** During v0.3.0 facade-application, these 6 were documented as pre-existing flakes. No commit message in the last 50 logs references "inspect.getsource" fix, suggesting they remain outstanding.

---

## 3. NotImplementedError / Stubs in Non-Test Code

### Found in Non-Venv, Non-Test Codebase

| File:Line | Code | Context | Severity |
|-----------|------|---------|----------|
| test/spikes/conftest.py:76 | `raise NotImplementedError("test stub — _ConcreteSLS is for unit-only use")` | Fixture class; test-only (not app code) | **TEST-ONLY** |

**Verdict:** Only 1 hit in test fixture; **no NotImplementedError in production scalpel code** (src/serena/tools/scalpel_*.py). 
All other hits are in `.venv` and upstream libraries.

---

## 4. Type-Safety Gaps

### Scalpel-Specific Type Ignores & Suppression Markers

**Type ignore count in scalpel files:**

```
scalpel_primitives.py:   2 × (# type: ignore), 2 × (# noqa)
scalpel_facades.py:      1 × docstring, 2 × (# noqa), 2 × (# type: ignore) [indirect]
query_project_tools.py:   1 × (# type: ignore)
symbol_tools.py:          2 × (# noqa), 3 × (# type: ignore)
tools_base.py:            1 × (# type: ignore)
```

**Sampling of notable suppression markers:**

| File:Line | Pattern | Reason |
|-----------|---------|--------|
| scalpel_primitives.py:345 | `except Exception as exc: # noqa: BLE001` | Surface as warning; broad except justified |
| scalpel_primitives.py:530 | `indexing_state=indexing_state, # type: ignore[arg-type]` | Likely variance mismatch in LSP union types |
| scalpel_facades.py:2157 | Docstring: `# pyright: ignore[...]` | Document on ignore-comment insertion tool |
| symbol_tools.py:232 | `s_dict["info"] = symbol_info # type: ignore[typeddict-unknown-key]` | Dynamic TypedDict key population |
| symbol_tools.py:306,311 | `symbol_dict_grouper.group(...) # type: ignore` | Function return type variance |
| tools_base.py:307 | `apply_ex(...) # type: ignore` on method signature | Likely **kwargs type variance |

**Cast calls:** 3 instances found:
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/src/serena/util/dataclass.py:13` — `cast(Field, cls.__dataclass_fields__[field_name])`
- No `cast()` in scalpel files themselves (imports from `typing` used elsewhere)

**Verdict:**
- **Type-ignore density:** ~10 hits across 5 scalpel source files (low; ~2 per file avg).
- **Most justified** — union-type variance, dynamic dict population, kwargs variance are common in LSP wrapper code.
- **No systematic safety gap** — count well under 50; suggests Pyright compliance is acceptable for MVP.
- **Action item:** None blocking MVP; Stage 1H includes Pyright pass.

---

## 5. Long-Tail Markers in Scalpel Code

### TODO/FIXME/HACK/XXX in scalpel_*.py files

**Result:** **ZERO hits** in production scalpel files.

Grep of `/vendor/serena/src/serena/tools/scalpel_*.py` returned no TODO/FIXME/HACK/XXX markers.

**In test spikes:**
- `test/spikes/test_stage_1c_t9_end_to_end.py:67` — `# TODO: basedpyright + ruff coverage lands in Stage 1E once their`  
  (This is a stage-sequencing note, not code debt.)

**Verdict:** Scalpel production code is clean of long-tail markers. Stage 1 planning documents hold the outstanding TODOs.

---

## 6. CI / Lint / Build Debt

### GitHub Actions Workflow Gaps

**File:** `/vendor/serena/.github/workflows/pytest.yml`

#### Commented-Out Sections (Explicit Exclusions)

| Line Range | Feature | Reason |
|-----------|---------|--------|
| 101–114 | Erlang LS installation | Commented: "Erlang currently not tested in CI, random hangings on macos, always hangs on ubuntu. In local tests, erlang seems to work though" |
| 154–157 | Swift installation via swift-actions | Commented: "Installation of swift with the action screws with installation of ruby on macOS for some reason. We can try again when version 3 of the action is released." |

**Impact:** 
- Erlang LS tests are **skipped in CI** (conftest markers + workflow exclusion).
- Swift tests **work locally** but GHA setup conflicts trigger alternative swiftly approach.

#### Conditional Skips in Workflow

| Test/Check | Condition | Implication |
|-----------|-----------|------------|
| Haskell HLS verification | `runner.os != 'Windows'` | HLS not verified on Windows |
| Free Pascal compiler | Platform-conditional install | Windows uses `fpc-ootb`; Linux/macOS use std package managers |
| Swift install (macOS/Linux) | `runner.os != 'Windows'` | Swift toolchain unavailable on Windows CI |
| Nix + nixd | `runner.os != 'Windows'` | Nix package manager not available on Windows |
| Perl::LanguageServer | `runner.os != 'Windows'` | Windows doesn't run Perl server natively |

**Verdict:**
- **No `continue-on-error: true`** in pytest job (strict pass/fail).
- **No test-exclusion filters** in `pytest.yml` (all tests run or skip conditionally).
- **Workflow is comprehensive** — installs 20+ language servers and toolchains.
- **Known gaps documented:**
  - Erlang LS hangs (commented-out; skipped by conftest).
  - Swift GHA conflicts (worked around via swiftly).
  - Haskell HLS version incompatibility (non-blocking warning).

### Pyproject.toml & Linting Config

**Key findings:**
- `uv run poe lint` (Step 79) runs pre-commit linting.
- `uv run poe type-check` (Step 581) runs mypy (Stage 1H per memory).
- No `--exclude` patterns specifically for scalpel code.

**Verdict:** CI enforces lint + type-check; no debt skips in linter config.

---

## 7. Recent Commits Mentioning Gaps/Debt

**Last 50 commits, filtered for gap/flake/skip/TODO/debt keywords:**

| Hash (abbrev) | Subject | Type |
|---------------|---------|------|
| `c9c650d` | Merge feature/v0.3.0-bump into develop — facade-application gap closed | gap-closed |
| `fe4fb87` | Merge develop into main — v0.2.0 critical-path 7/7 + H flake fix | flake-fix |
| `0a3404b` | Merge feature/v0.2.0-critical-path into develop — v0.2.0 critical-path 7/7 + H flake fix | flake-fix |
| `87a5617` | Merge develop into main — Stage 2B follow-up flake doc | flake-doc |
| `2ee21f8` | chore(stage-2b): document E1-py flake (gap #8) for v0.2.0 backlog | gap-doc |
| `97d612a` | stage-1h: bump submodule for Pyright cleanup (eddba6c5) | cleanup |

**Interpretation:**
- Recent work (`c9c650d`, `fe4fb87`) closed facades gap + fixed H-phase flake.
- Gap #8 (E1-py flake) **CLOSED** by v0.2.0 followup-05 (Leaf 05). The
  `pytest.skip` fallback at `test_e2e_e1_py_split_file_python.py:87-91` was
  replaced by an unconditional assertion; a 10-iteration determinism guard
  lives in `test/e2e/test_e2e_e1_py_determinism.py`. The flake did not
  reproduce on the Leaf 05 host (30/30 applies via
  `test/e2e/_e1_py_diagnostic.py`, ledger persisted at
  `test/e2e/_e1_py_diagnostic_ledger.json`), so no facade-side patch was
  required; the strip-the-skip change alone tightens the contract so any
  future regression fails loudly instead of skipping silently.
- Stage 1H includes Pyright cleanup task (in progress or pending).

---

## Summary Table: Known Gaps vs. Fixed

| Category | Count | Status | Action |
|----------|-------|--------|--------|
| **Tool/env skips** | ~110+ | By-design | Monitor platform coverage |
| **LSP reliability flakes** | ~25+ | DEBT | Issue #1040 root-cause; track F# removal decision |
| **inspect.getsource flakes** | 6 | DEBT | Stage 2A/3 fixtures; safety-call injection hypothesis |
| **WIP/fixture skips** | ~20+ | By-design | E2E host-cargo + LSP-startup gates documented |
| **NotImplementedError** | 1 | Test-only fixture stub | No action needed |
| **Type-ignore density** | ~10 in scalpel | Acceptable | Stage 1H Pyright pass will cover |
| **TODO/FIXME markers** | 0 in scalpel | Clean | — |
| **CI exclusions** | 2 (Erlang, Swift GHA) | Documented | Known workarounds in place |
| **E1-py flake (gap #8)** | 1 | **CLOSED** (v0.2.0 followup-05) | strip-the-skip + 10x determinism guard |

---

## Recommendations

1. **Priority 1: Issue #1040 investigation** — 10+ test references suggest systemic LSP reliability issue across F#, Swift, Nix, TypeScript. Root cause undiagnosed.

2. **Priority 2: inspect.getsource flake root cause** — All 6 Stage 2A/3 tests use identical pattern; likely single upstream cause (safety-call injection, decorator stacking, or bytecode mismatch).

3. **Priority 3: E2E E1-py flake (gap #8)** — **CLOSED** by v0.2.0 followup-05 (Leaf 05); see §7 for evidence. The strip-the-skip change at `test_e2e_e1_py_split_file_python.py` plus the 10x guard at `test_e2e_e1_py_determinism.py` make any future recurrence loud.

4. **Priority 4: Host-cargo + LSP-startup E2E gaps** — Known skipped scenarios; Stage 1 scoping decision needed (defer post-MVP or fix in Stage 1H).

5. **Stage 1H Pyright cleanup** — Type-safety coverage is acceptable (10 suppressions across scalpel files); Pyright pass will finalize compliance.

---

## Appendix: Full Skipped Test Count

- **Spike tests:** 20 (mostly fixture/WIP gates for Phase 0)
- **Solidlsp language tests:** 100+ (tool/platform availability)
- **E2E tests:** 30+ (host-cargo, LSP-startup gates; capability-catalog checks)
- **Total inventory:** **~150+ conditional test points**

**Of these:**
- ~110 are **by-design environmental** (not debt).
- ~25 are **LSP flakiness** (debt; tracked under #1040).
- ~15 are **WIP/fixture sequencing** (by-design for Phase 0).
