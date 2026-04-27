# Leaf 04 — `CARGO_BUILD_RUSTC` Developer-Host Workaround

> **STATUS: SHIPPED 2026-04-26** — see `stage-v0.2.0-followups-complete` tag (parent + submodule). Cross-reference: `docs/gap-analysis/WHAT-REMAINS.md` §4 line 107 + `docs/superpowers/plans/stage-1h-results/PROGRESS.md` §88.
>
> **Implementation deviations from this plan** (recorded post-shipment):
> - Plan prescribed `addopts = "-p test.conftest_dev_host"` in `pyproject.toml` — REJECTED at impl time because `addopts -p` is parsed before pytest adds the rootdir to `sys.path`. Actual mechanism: `pytest_plugins = ["test.conftest_dev_host"]` in `vendor/serena/test/conftest.py:32`. The plan's `addopts` code block (around lines 102-107) has been REPLACED below with the actual `pytest_plugins` mechanism.

**Goal.** Move the `os.environ.setdefault("CARGO_BUILD_RUSTC", "rustc")` shim out of conftest module-load and into a documented developer-host-only script, so CI runs cleanly without the env override and the workaround is no longer treated as production code. Closes WHAT-REMAINS.md §4 line 105 and `stage-1h-results/PROGRESS.md:88`.

**Architecture.** Today the workaround lives at `test/spikes/test_spike_s3_apply_edit_reverse.py:24` and `stage-1h-results/PROGRESS.md:35` records that conftest module-load applies it. CI hosts have a clean `~/.cargo/config.toml` and don't need it; the developer's host has `[build] rustc = "rust-fv-driver"` (a broken wrapper). We extract the shim into a single `scripts/dev_env_shim.sh` (POSIX) plus a pytest plugin entry point that activates **only** when `O2_SCALPEL_LOCAL_HOST=1` is set.

**Tech Stack.** POSIX shell, pytest plugin (`pyproject.toml` entry point). Reference `docs/superpowers/plans/spike-results/PROGRESS.md:60` (origin of the workaround).

**Source spec.** `stage-1h-results/PROGRESS.md:35,88`.

**Author.** AI Hive(R).

## File Structure

| Path | Action | Approx LoC |
|------|--------|------------|
| `scripts/dev_env_shim.sh` | new — POSIX env shim, `source`-able | ~25 |
| `vendor/serena/test/conftest_dev_host.py` | new — opt-in pytest plugin | ~30 |
| `vendor/serena/pyproject.toml` | edit — register optional plugin | ~3 |
| `vendor/serena/test/integration/conftest.py` | edit — remove inline `setdefault` at line 57 | ~3 (delta) |
| `vendor/serena/test/spikes/test_spike_s1_progress.py` | edit — remove inline `setdefault` at line 26 | ~3 (delta) |
| `vendor/serena/test/spikes/test_spike_s2_snippet_false.py` | edit — remove inline `setdefault` at line 24 | ~3 (delta) |
| `vendor/serena/test/spikes/test_spike_s3_apply_edit_reverse.py` | edit — remove inline `setdefault` at line 24 | ~3 (delta) |
| `vendor/serena/test/spikes/test_spike_s4_ssr_bounds.py` | edit — remove inline `setdefault` at line 18 | ~3 (delta) |
| `vendor/serena/test/spikes/test_spike_s5_expand_macro.py` | edit — remove inline `setdefault` at line 20 | ~3 (delta) |
| `vendor/serena/test/spikes/test_spike_s6_auto_import_shape.py` | edit — remove inline `setdefault` at line 18 | ~3 (delta) |
| `docs/dev/host-rustc-shim.md` | new — README for developers | ~30 |
| `vendor/serena/test/conftest_dev_host_test.py` | new — tests asserting opt-in semantics | ~80 |

## Tasks

### Task 1 — Failing test for opt-in plugin behavior

Create `vendor/serena/test/conftest_dev_host_test.py`:

```python
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


def _run_pytest(tmp_path: Path, env_overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    test_file = tmp_path / "test_dummy.py"
    test_file.write_text(textwrap.dedent("""
        import os
        def test_env():
            with open(os.environ.get('_O2_OUT', '/tmp/_o2.txt'), 'w') as f:
                f.write(os.environ.get('CARGO_BUILD_RUSTC', '__unset__'))
    """))
    out = tmp_path / "out.txt"
    env = {**os.environ, "_O2_OUT": str(out), **env_overrides}
    env.pop("CARGO_BUILD_RUSTC", None)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-q"],
        capture_output=True, text=True, env=env, cwd=tmp_path,
    )
    return proc, out


def test_plugin_inactive_without_env_var(tmp_path: Path) -> None:
    proc, out = _run_pytest(tmp_path, env_overrides={})
    assert proc.returncode == 0, proc.stderr
    assert out.read_text() == "__unset__"


def test_plugin_active_when_local_host_flag_set(tmp_path: Path) -> None:
    proc, out = _run_pytest(tmp_path, env_overrides={"O2_SCALPEL_LOCAL_HOST": "1"})
    assert proc.returncode == 0, proc.stderr
    assert out.read_text() == "rustc"
```

Run — fails (plugin not present). Stage only.

### Task 2 — Implement opt-in plugin

Create `vendor/serena/test/conftest_dev_host.py`:

```python
"""Developer-host pytest plugin.

Activates ONLY when O2_SCALPEL_LOCAL_HOST=1. Sets CARGO_BUILD_RUSTC=rustc
to defeat the developer's global ~/.cargo/config.toml `rust-fv-driver`
wrapper (broken dyld lookup). CI does not set the flag, so its environment
remains clean.

See docs/dev/host-rustc-shim.md for context.
"""
from __future__ import annotations

import os


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    if os.environ.get("O2_SCALPEL_LOCAL_HOST") == "1":
        os.environ.setdefault("CARGO_BUILD_RUSTC", "rustc")
```

Edit `vendor/serena/pyproject.toml` `[tool.pytest.ini_options]` block:

> **Plan superseded by impl** — see STATUS addendum above for rejection rationale.

```toml
# Plan PRESCRIBED (rejected at impl time — see addendum above):
# [tool.pytest.ini_options]
# addopts = "-p test.conftest_dev_host"
```

```python
# Plan ACTUAL (shipped):
# vendor/serena/test/conftest.py:
pytest_plugins = ["test.conftest_dev_host"]
```

Run `uv run pytest vendor/serena/test/conftest_dev_host_test.py -x` — both green. Commit `feat(stage-v0.2.0-followup-04a): opt-in pytest plugin for developer-host CARGO_BUILD_RUSTC shim`.

### Task 3 — Remove inline `setdefault` calls

Delete the `os.environ.setdefault("CARGO_BUILD_RUSTC", "rustc")` line from each of the following exact locations (verified by `grep -n "CARGO_BUILD_RUSTC" vendor/serena/test/`; line numbers are post-Stage-1H):

1. `vendor/serena/test/integration/conftest.py:57` — module-load shim (per `stage-1h-results/PROGRESS.md:35`).
2. `vendor/serena/test/spikes/test_spike_s1_progress.py:26`.
3. `vendor/serena/test/spikes/test_spike_s2_snippet_false.py:24`.
4. `vendor/serena/test/spikes/test_spike_s3_apply_edit_reverse.py:24`.
5. `vendor/serena/test/spikes/test_spike_s4_ssr_bounds.py:18`.
6. `vendor/serena/test/spikes/test_spike_s5_expand_macro.py:20`.
7. `vendor/serena/test/spikes/test_spike_s6_auto_import_shape.py:18`.

Run the full Rust spike suite under `O2_SCALPEL_LOCAL_HOST=1 uv run pytest vendor/serena/test/spikes/ -x` — green. Run again **without** the flag on a clean CI image and confirm any path that previously failed continues to fail (proving the workaround is host-specific and not masked).

Verify with `grep -rn "CARGO_BUILD_RUSTC" vendor/serena/test/ --include='*.py'` — only the docstring at `vendor/serena/test/integration/conftest.py:33` (item 7 in the docstring numbered list) should survive, and that string is documentation not code.

Commit `refactor(stage-v0.2.0-followup-04b): drop inline CARGO_BUILD_RUSTC setdefault calls`.

### Task 4 — Developer-facing shim script

Create `scripts/dev_env_shim.sh`:

```sh
#!/usr/bin/env sh
# o2.scalpel developer-host shim.
# Source this file in your shell before running tests if your global
# ~/.cargo/config.toml has [build] rustc = "rust-fv-driver" (a broken
# wrapper). CI does not need this.
#
# Usage:
#   . ./scripts/dev_env_shim.sh
#   uv run pytest vendor/serena/test/spikes/

export O2_SCALPEL_LOCAL_HOST=1
echo "[o2.scalpel] developer-host shim active: O2_SCALPEL_LOCAL_HOST=1"
```

Make executable; commit.

### Task 5 — Documentation

Create `docs/dev/host-rustc-shim.md` referencing `spike-results/PROGRESS.md:60` (origin) and `stage-1h-results/PROGRESS.md:88` (closure note). Single source of truth — link from each test file's docstring rather than duplicating.

### Task 6 — Self-review and tag

Run `uv run pytest vendor/serena/test/conftest_dev_host_test.py -x` and `O2_SCALPEL_LOCAL_HOST=1 uv run pytest vendor/serena/test/spikes/ -x` — both green. `git tag stage-v0.2.0-followup-04-cargo-build-rustc-workaround-complete`.

## Self-Review Checklist

- [ ] CI run (no env var) does not import the shim.
- [ ] Local-host run with `O2_SCALPEL_LOCAL_HOST=1` sets `CARGO_BUILD_RUSTC=rustc`.
- [ ] No inline `os.environ.setdefault` for `CARGO_BUILD_RUSTC` survives in the codebase (`grep -rn 'CARGO_BUILD_RUSTC' vendor/serena/test/ --include='*.py'` returns only the docstring at `integration/conftest.py:33`).
- [ ] Single SoT doc; no duplication; author = AI Hive(R).
