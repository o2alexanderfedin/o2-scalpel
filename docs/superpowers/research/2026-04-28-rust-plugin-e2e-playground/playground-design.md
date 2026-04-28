# Playground Design + CI Strategy

**Researcher**: Agent C (playground design)
**Date**: 2026-04-28

## TL;DR (3 bullets)

- Use a **subdirectory in the main repo** (`playground/rust/`) for the playground. It shares the submodule, gets CI for free, and keeps the fixture-to-test relationship visible — exactly what the `calcrs_e2e` fixture pattern already demonstrates.
- The hardest step in the E2E workflow is not install or boot; it is **programmatic MCP invocation and workspace-edit assertion** without spawning a full Claude CLI session. The existing `_McpDriver` / `ScalpelRuntime` pattern from `test/e2e/conftest.py` is the right template — replicate it, don't reinvent.
- The playground ships as **v1.2.2** (minor patch on the current v1.2 installer branch). It depends only on what already exists (rust-analyzer, cargo, the 12 Rust facades from Stage 3), with no v1.3 markdown or dynamic-capability spec prerequisites.

---

## 1. Hosting options

| Option | Pros | Cons | Score |
|---|---|---|---|
| **Separate repo** (`o2alexanderfedin/o2-scalpel-playground`) | Clean blast radius; public discoverable; independent CI matrix | Two repos to keep in sync; submodule pointer drift; install-from-GitHub test requires pulling two repos; YAGNI complexity until there are external contributors | 2/5 |
| **Orphan branch** (`playground/rust` branch) | Zero repository overhead; branch can be force-reset freely | Poor discoverability; GitHub branch navigation is not doc navigation; CI targeting an orphan branch is awkward (branch filter logic); violates DRY for fixture content shared with main | 1/5 |
| **Subdirectory** (`playground/rust/`) | Shares submodule at zero sync cost; CI job already exists (just add a matrix entry); fixture content co-located with tests that reference it; follows the `test/e2e/fixtures/calcrs_e2e/` pattern exactly | Slightly increases main-repo surface area; playground mutations during CI could race with other jobs if not isolated | **4/5** |
| **Submodule pulling a separate repo** | Maximal separation for external users wanting to fork just the playground | Two-layer submodule nesting on top of `vendor/serena` already being a submodule; `git submodule update --recursive` is already required; adding a third level invites confusion; does not simplify the actual install test | 1/5 |

**Recommendation**: subdirectory (`playground/rust/`) because it reuses the existing CI, shares the submodule state that the install test needs, and mirrors the `test/e2e/fixtures/calcrs_e2e/` precedent already established in `vendor/serena`. Promote to a separate repo only if external contributors need to submit playground fixtures independently.

---

## 2. Playground content for Rust

The playground should be a standalone Cargo workspace that is non-trivial enough to exercise all 12 Rust facades at least once, but compact enough to index quickly under rust-analyzer.

**Proposed shape** (`playground/rust/`):

```
playground/rust/
  Cargo.toml            # workspace root, resolver="2", rust-version="1.74"
  Cargo.lock            # committed (install test must not run `cargo update`)
  clippy.toml           # deny(clippy::unwrap_used), warn(clippy::pedantic)
  .gitignore            # /target
  README.md             # one-paragraph description; link to docs/install.md

  calc/                 # primary crate — exercises split, rename, extract, inline, visibility
    Cargo.toml
    src/
      lib.rs            # three inline modules (ast, parser, eval) — E1-style split target
      ops.rs            # Op enum with wildcard match — complete_match_arms target
      visibility.rs     # pub(super) items to promote/demote — change_visibility target

  lints/                # secondary crate — exercises verify_after_refactor, fix_lints, expand_macro
    Cargo.toml
    src/
      lib.rs            # intentional clippy::unwrap_used + snake_case warnings + debug!{} macro call

  types/                # tertiary crate — exercises change_type_shape, change_return_type,
    Cargo.toml          # extract_lifetime, generate_member, generate_trait_impl_scaffold,
    src/                # expand_glob_imports, tidy_structure, convert_module_layout
      lib.rs
```

**Per-facade fixture mapping** (all 12 Stage 3 Rust facades):

| Facade | Fixture target |
|---|---|
| `scalpel_split_file` | `calc/src/lib.rs` — split ast/parser/eval into siblings |
| `scalpel_rename` | `calc/src/lib.rs` — rename `eval` → `evaluate` across workspace |
| `scalpel_extract` | `calc/src/lib.rs` — extract arithmetic branch into helper |
| `scalpel_inline` | `calc/src/lib.rs` — inline `inline_call_callee`-style helper |
| `scalpel_change_visibility` | `calc/src/visibility.rs` — promote `pub(super)` → `pub` |
| `scalpel_complete_match_arms` | `calc/src/ops.rs` — expand wildcard `_` to explicit arms |
| `scalpel_change_return_type` | `types/src/lib.rs` — wrap `i64` return in `Result` |
| `scalpel_change_type_shape` | `types/src/lib.rs` — convert `struct Foo { x: i32 }` to tuple form |
| `scalpel_extract_lifetime` | `types/src/lib.rs` — elided lifetime → named lifetime |
| `scalpel_generate_member` | `types/src/lib.rs` — generate getter/setter on `User` struct |
| `scalpel_generate_trait_impl_scaffold` | `types/src/lib.rs` — scaffold `Display` for a type |
| `scalpel_expand_glob_imports` | `types/src/lib.rs` — `use types::*` → explicit items |
| `scalpel_expand_macro` | `lints/src/lib.rs` — `debug!{expr}` → expanded form |
| `scalpel_tidy_structure` | `types/src/lib.rs` — reorder impl items (methods before assoc types) |
| `scalpel_convert_module_layout` | `types/src/lib.rs` — move inline mod to file |
| `scalpel_verify_after_refactor` | any crate — run flycheck after applying a split |

The MVP content for v1.2.2 covers only the first 5 (split, rename, extract, inline, visibility) — they are the highest-value, lowest-RA-version-dependency set. The remaining 7 can land in v1.3 alongside additional fixture depth.

---

## 3. E2E test workflow

The test lives in `test/e2e/test_e2e_playground_rust_install.py`. It follows the `calcrs_e2e` pattern precisely.

**Steps:**

1. **CI pre-flight**: confirm `rust-analyzer` and `cargo` are on `PATH` (`shutil.which`); `pytest.skip` if missing (matches the existing `rust_analyzer_bin` fixture in `conftest.py:110`).

2. **Install from GitHub** (the new step): run `uvx --from git+https://github.com/o2alexanderfedin/o2-scalpel-engine@main serena-mcp` (or the equivalent `uv tool install`) in a subprocess; assert exit code 0 and that the `serena-mcp` entry point is resolvable.

3. **Clone the playground to `tmp_path`**: same as `calcrs_e2e_root` — `shutil.copytree(PLAYGROUND_BASELINE, dest)`. This is the refresh/reset mechanism: each test runs on a clean copy.

4. **Boot `ScalpelRuntime`** via the existing `scalpel_runtime` session fixture. The runtime discovers LSPs via `shutil.which` — no new mechanism needed.

5. **Invoke facades via `_McpDriver`**: call `split_file`, `rename`, and `verify_after_refactor` through the existing driver thin-wrapper. Assert `applied=True` and `checkpoint_id` is non-empty.

6. **Assert workspace-level correctness**: run `cargo test --quiet` in `dest`; assert exit code 0. This is the same `_run_cargo_test` helper already in `test_e2e_e1_split_file_rust.py`.

7. **Cleanup**: `tmp_path` is cleaned by pytest automatically.

**Hardest step**: Step 2 — the install-from-GitHub RPC. The difficulty is not mechanical but environmental: `uvx` from a fresh CI runner must pull the submodule-containing repository and resolve the package. The `vendor/serena` submodule path makes this non-trivial because `uvx --from git+URL` does not recurse submodules. The concrete solution is: the E2E test for *install from GitHub* must target a GitHub release archive or a published PyPI package, not a raw `git+URL`. Until the package is published on PyPI (v1.2 ships the installers but not PyPI publication — that is a v1.3 item per the roadmap), the install test must fall back to `uvx --from /path/to/vendor/serena` locally and be clearly marked `@pytest.mark.local_only` on CI until PyPI publication lands.

**Step 5 vs direct MCP RPC**: the `_McpDriver` pattern (instantiate `Tool.__new__`, bind `get_project_root`, call `apply`) is the correct approach — it is already used in 20 E2E scenarios, avoids spawning a `claude` CLI process (which requires auth and is not headless-safe), and produces deterministic, inspect-able results. Do not use raw JSON-RPC stdio invocation for these tests.

---

## 4. CI options

**Recommendation: both (a shared shell script, called from GitHub Actions and from a local make target).**

The logic that runs the playground E2E should be a single pytest invocation wrapped in `scripts/e2e_playground.sh`:

```sh
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)/vendor/serena"
exec uv run pytest test/e2e/test_e2e_playground_rust_install.py -q -m e2e "$@"
```

**GitHub Actions** (`.github/workflows/playground.yml`):
- Trigger: `push` to `main`, `workflow_dispatch`.
- Matrix: `macos-latest` only for v1.2.2 (Linux adds `rustup` complexity without new coverage at this stage; add Ubuntu in v1.3).
- Install rust-analyzer via `rustup component add rust-analyzer`.
- Auth: none needed (all facades run in-process, no `claude` CLI auth required).
- Cache: `~/.cargo/registry` + `.venv` (uv cache) — same keys as the existing `pytest.yml`.
- Gate: set `O2_SCALPEL_RUN_E2E=1` to opt-in (same opt-in as the main E2E suite).

**Local make target** (`Makefile`):

```make
.PHONY: e2e-playground
e2e-playground:
	scripts/e2e_playground.sh
```

**What CI needs that local does not**: `GITHUB_PATH` manipulation to ensure `~/.rustup/toolchains/.../bin` is on PATH; the `rustup component add rust-analyzer` step; and the `O2_SCALPEL_RUN_E2E=1` env var (local devs can set it or pass `-m e2e` directly).

---

## 5. Refresh / reset policy

**Recommendation: option (c) — per-test scratch directory derived from the playground baseline.**

This is exactly what the `calcrs_e2e_root` fixture already does:

```python
@pytest.fixture
def playground_rust_root(tmp_path: Path) -> Path:
    dest = tmp_path / "playground_rust"
    shutil.copytree(PLAYGROUND_BASELINE, dest, dirs_exist_ok=False)
    target_dir = dest / "target"
    if target_dir.exists():
        shutil.rmtree(target_dir)
    return dest.resolve(strict=False)
```

Option (a) — always temp clone — is what this pattern implements. Option (b) — `git reset --hard` on the canonical tree — is risky in CI because concurrent jobs share the workspace. Option (c) from the prompt (scratch dir derived from baseline) is identical to option (a) as implemented here.

The `target/` directory deletion is load-bearing: without it, `shutil.copytree` can copy gigabytes of compiled artifacts, and rust-analyzer will attempt to re-use stale incremental build data from a different path, causing non-deterministic code-action results.

---

## 6. Failure-mode → README troubleshooting mapping

| Failure | Symptom | README guidance |
|---|---|---|
| F1: `rust-analyzer` not on PATH | `pytest.skip("rust-analyzer not on PATH")` or `FileNotFoundError` in `ScalpelRuntime` | Install via `rustup component add rust-analyzer`. Verify: `which rust-analyzer`. If `rustup` installed it but the bin dir is not on PATH, add `$(rustup show home)/toolchains/$(rustup show active-toolchain | cut -d' ' -f1)/bin` to `PATH`. |
| F2: `rustc_driver` dylib mismatch | `cargo test` fails with `cannot open shared object file` or `LoadError` | Reinstall toolchain: `rustup self uninstall && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh`. Then `rustup component add rust-analyzer`. |
| F3: `uvx` install fails (submodule not fetched) | `uvx --from git+URL serena-mcp` errors with `no module named serena` | The engine requires the submodule. Use `uvx --from ./vendor/serena serena-mcp` after running `git submodule update --init --recursive`. |
| F4: `applied=False` on `split_file` | Facade returns `{"applied": false, "failure": {"code": "NO_CODE_ACTIONS"}}` | rust-analyzer did not index the project before the request. The `ScalpelRuntime` preflight (RA preflight test, v0.2.0 followup-02) waits for RA to signal readiness; if the playground Cargo.toml is malformed or `target/` is corrupt, RA silently fails to index. Run `cargo build` in the playground directory first to confirm the project compiles. |
| F5: `cargo test` fails post-refactor | Test count drops or compilation error after split | The split facade applied a partial edit (some files written, one failed). Check `checkpoint_id` from the apply result and call `scalpel_rollback` with that ID to restore the original state. |
| F6: Capability catalog drift | `scalpel_capabilities_list` returns unexpected count | Re-baseline: `pytest test/spikes/test_stage_1f_t4_baseline_round_trip.py --update-catalog-baseline` from `vendor/serena/` and commit `test/spikes/golden/catalog_baseline.json`. |
| F7: `uv venv` / `uv sync` fails on Python version | `Requires-Python >=3.10` mismatch | Install Python 3.11 via `pyenv install 3.11` or `brew install python@3.11`. Set `PYTHON=python3.11 uv venv`. |

---

## 7. Sequencing with v1.x roadmap

**Ship as v1.2.2** — no new prerequisites needed.

The 12 Stage 3 Rust facades shipped at `v0.2.0-stage-3-facades-complete`. The 5 LspInstallers (including `RustAnalyzerInstaller`) shipped at `v1.2-installer-extension-complete`. The marketplace.json consolidation that makes `claude plugin install o2-scalpel-rust` work shipped at `v1.2`.

What the playground does NOT need:
- v1.3 markdown LSPs — playground is Rust-only.
- The dynamic-capability spec (2026-04-28 research) — facades already have hard-coded capability dispatch; the dynamic registry is a capability-gate enhancement, not a correctness requirement.
- PyPI publication — the install test can use the local path until publication lands (mark the remote-URL step `@pytest.mark.slow` or gate it behind `O2_SCALPEL_TEST_REMOTE_INSTALL=1`).

What the playground does need (all already shipped):
- `rust-analyzer` on PATH (v0.2.0).
- `cargo` on PATH (v0.2.0 verify_after_refactor).
- `ScalpelRuntime` + `_McpDriver` harness (Stage 2B / `test/e2e/conftest.py`, already in `vendor/serena`).
- `RustAnalyzerInstaller` (v1.2, for the optional `scalpel_install_lsp_servers` smoke step).

**Suggested tag**: `v1.2.2-playground-rust-complete`. The playground is a non-breaking addition — no facade changes, no API changes — so a patch bump is appropriate.

---

## Open questions for the synthesis pair

1. **MVP scope for v1.2.2**: should the first playground ship with all 12 facade fixtures (large, richer value) or just the 5 high-value ones (split, rename, extract, inline, visibility) and land the remaining 7 in v1.3? The 5-facade scope fits in a single leaf; 12 facades needs at least 3 leaves.

2. **Install test gating**: should the remote-URL install step (`uvx --from git+URL`) be included in v1.2.2 (with a `O2_SCALPEL_TEST_REMOTE_INSTALL=1` opt-in gate) or deferred entirely to v1.3 when PyPI publication lands?

3. **Linux CI matrix**: macOS-only is safe (no extra rustc complexity) but leaves Linux coverage dark. Should the playground GH Actions matrix include `ubuntu-latest` from day 1, accepting that the `rustup`+`rust-analyzer` setup step adds ~3 minutes to CI?

4. **`calcrs_e2e` vs new playground**: the `test/e2e/fixtures/calcrs_e2e/` fixture already exercises split and other facades in the internal harness. Is the playground genuinely a *new* fixture tree (with its own `Cargo.toml` in `playground/rust/`), or should the playground simply be `calcrs_e2e` re-exported as a user-facing artifact? Reusing `calcrs_e2e` avoids duplication (DRY) but couples the user-facing fixture to internal test details.

5. **Mutation vs read-only facades**: some facades (`change_return_type`, `change_type_shape`) are idempotent only if the fixture starts from a known-clean state. Should the playground fixture be pinned to a read-only baseline committed in the repo, or should it carry a `reset.sh` script that restores the originals from git?

---

## Files referenced

- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/e2e/fixtures/calcrs_e2e/` — existing E2E Rust fixture (split target shape)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/e2e/conftest.py` — `calcrs_e2e_root`, `_McpDriver`, `scalpel_runtime` fixtures
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/e2e/test_e2e_e1_split_file_rust.py` — Rust E1 split scenario (workflow template)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/e2e/test_e2e_stage_3_rust_e13_e16.py` — Stage 3 long-tail Rust E2E (verify/visibility/match_arms)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/test/fixtures/calcrs/` — fixture library (18 companion crates, per-family refactor targets)
- `/Volumes/Unitek-B/Projects/o2-scalpel/vendor/serena/.github/workflows/pytest.yml` — existing CI workflow (cache, matrix, uv setup)
- `/Volumes/Unitek-B/Projects/o2-scalpel/docs/install.md` — current install guide (troubleshooting section extended in §6 above)
- `/Volumes/Unitek-B/Projects/o2-scalpel/o2-scalpel-rust/README.md` — generated plugin README
- `/Volumes/Unitek-B/Projects/o2-scalpel/docs/superpowers/plans/2026-04-26-INDEX-post-v0.3.0.md` — workstream index (v1.2 = last shipped stream)
