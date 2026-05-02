#!/bin/sh
# SessionStart hook for o2-scalpel-toml - verifies LSP server is reachable.
set -eu

if ! command -v taplo >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "taplo" >&2
  printf 'Install hint: %s\n' "cargo install --features lsp --locked taplo-cli" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "taplo" "toml"
