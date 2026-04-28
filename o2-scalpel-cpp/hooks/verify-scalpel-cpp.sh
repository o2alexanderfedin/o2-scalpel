#!/bin/sh
# SessionStart hook for o2-scalpel-cpp - verifies LSP server is reachable.
set -eu

if ! command -v clangd >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "clangd" >&2
  printf 'Install hint: %s\n' "see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "clangd" "cpp"
