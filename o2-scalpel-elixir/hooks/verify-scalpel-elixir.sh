#!/bin/sh
# SessionStart hook for o2-scalpel-elixir - verifies LSP server is reachable.
set -eu

if ! command -v elixir-ls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "elixir-ls" >&2
  printf 'Install hint: %s\n' "brew install elixir-ls  # macOS; build from github.com/elixir-lsp/elixir-ls otherwise" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "elixir-ls" "elixir"
