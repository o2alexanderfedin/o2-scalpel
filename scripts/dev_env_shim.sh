#!/usr/bin/env sh
# o2.scalpel developer-host environment shim.
#
# Source this file in your shell BEFORE running tests if your global
# ~/.cargo/config.toml has [build] rustc = "rust-fv-driver" (a broken
# wrapper that aborts cargo metadata during rust-analyzer project-model
# load on missing dylib `librustc_driver-*.dylib`). CI hosts have a
# clean cargo config and do NOT need this.
#
# Usage:
#   . ./scripts/dev_env_shim.sh
#   uv run pytest vendor/serena/test/spikes/
#
# What it does:
#   Exports O2_SCALPEL_LOCAL_HOST=1 so that the opt-in pytest plugin
#   `test.conftest_dev_host` activates and sets CARGO_BUILD_RUSTC=rustc
#   inside the test process (and any rust-analyzer subprocess that
#   inherits its env).
#
# Single source of truth for context: docs/dev/host-rustc-shim.md
export O2_SCALPEL_LOCAL_HOST=1
echo "[o2.scalpel] developer-host shim active: O2_SCALPEL_LOCAL_HOST=1"
