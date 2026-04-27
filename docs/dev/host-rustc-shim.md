# Developer-Host `CARGO_BUILD_RUSTC` Shim

**Audience:** o2.scalpel contributors whose global
`~/.cargo/config.toml` overrides the default `rustc` driver.
**Scope:** developer-host only. CI does **not** need this shim.

## Why this exists

If your `~/.cargo/config.toml` contains:

```toml
[build]
rustc = "rust-fv-driver"
```

then every `cargo` subprocess (including the one rust-analyzer spawns
during project-model load) inherits the broken `rust-fv-driver`
wrapper. On macOS this aborts immediately with a missing-dylib lookup
for `librustc_driver-<HASH>.dylib`, which in turn:

- crashes `cargo metadata` and prevents rust-analyzer from indexing,
- silently swallows `$/progress` events (0 events emitted instead of
  the usual 140–180 during cold start),
- causes any test that boots rust-analyzer to hang or partially boot.

The fix is a single environment variable: `CARGO_BUILD_RUSTC=rustc`.

## How it is wired

| Layer | Location | Behaviour |
|------|----------|-----------|
| Opt-in pytest plugin | `vendor/serena/test/conftest_dev_host.py` | Sets `CARGO_BUILD_RUSTC=rustc` only when `O2_SCALPEL_LOCAL_HOST=1`. Auto-loaded via `pytest_plugins = ["test.conftest_dev_host"]` declared in `vendor/serena/test/conftest.py` (the original `addopts = "-p test.conftest_dev_host"` approach failed because `addopts` is parsed before pytest adds the rootdir to `sys.path`, so the dotted import could not be resolved; `pytest_plugins` in the rootdir conftest runs after the bootstrap that puts the rootdir on `sys.path`). |
| Developer shell shim | `scripts/dev_env_shim.sh` | One-line `export O2_SCALPEL_LOCAL_HOST=1` for `source`-ing into your shell. |
| Documentation | this file | Single source of truth. |
| Plugin tests | `vendor/serena/test/conftest_dev_host_test.py` | Asserts both opt-in semantics. |

## Usage

```sh
. ./scripts/dev_env_shim.sh
uv run pytest vendor/serena/test/spikes/
```

CI never sources the shim, never sets `O2_SCALPEL_LOCAL_HOST`, and
therefore inherits a clean environment — exactly the behaviour we
want.

## Verification

The opt-in semantics are guarded by two unit tests:

```sh
cd vendor/serena
uv run pytest test/conftest_dev_host_test.py -x
```

Both must remain green: one asserts the plugin is **inactive** without
the flag, the other asserts it sets `CARGO_BUILD_RUSTC=rustc` when the
flag is set.

## History

- **Origin:** discovered during Stage 0 spike S3 (rust-analyzer
  workspace-edit reverse-request). See
  `docs/superpowers/plans/spike-results/PROGRESS.md:60`.
- **Initial workaround:** inline `os.environ.setdefault(...)` at the
  top of every Rust spike test plus `vendor/serena/test/integration/conftest.py`
  module-load, recorded in
  `docs/superpowers/plans/stage-1h-results/PROGRESS.md:35`.
- **Closure:** v0.2.0 follow-up #04 extracted the workaround into the
  opt-in plugin documented here. Inline `setdefault` calls deleted
  from all 7 sites; the integration-conftest docstring item 7 retains
  a reference for archaeology. See
  `docs/superpowers/plans/stage-1h-results/PROGRESS.md:88`.
