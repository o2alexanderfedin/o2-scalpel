#!/bin/sh
# SessionStart hook for o2-scalpel-erlang - verifies LSP server is reachable.
set -eu

if ! command -v erlang_ls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "erlang_ls" >&2
  printf 'Install hint: %s\n' "brew install erlang_ls  # macOS; build from github.com/erlang-ls/erlang_ls otherwise" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "erlang_ls" "erlang"
