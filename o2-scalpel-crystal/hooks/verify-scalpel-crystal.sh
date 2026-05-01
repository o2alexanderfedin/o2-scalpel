#!/bin/sh
# SessionStart hook for o2-scalpel-crystal - verifies LSP server is reachable.
set -eu

if ! command -v crystalline >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "crystalline" >&2
  printf 'Install hint: %s\n' "brew install crystalline  # macOS; or shards build from github.com/elbywan/crystalline" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "crystalline" "crystal"
