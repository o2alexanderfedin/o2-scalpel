#!/bin/sh
# SessionStart hook for o2-scalpel-rust - verifies LSP server is reachable.
set -eu

if ! command -v rust-analyzer >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "rust-analyzer" >&2
  printf 'Install hint: %s\n' "rustup component add rust-analyzer" >&2
  exit 1
fi
printf 'scalpel: %s ready (language=%s)\n' "rust-analyzer" "rust"
