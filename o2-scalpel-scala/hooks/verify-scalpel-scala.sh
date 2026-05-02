#!/bin/sh
# SessionStart hook for o2-scalpel-scala - verifies LSP server is reachable.
set -eu

if ! command -v metals >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "metals" >&2
  printf 'Install hint: %s\n' "brew install coursier && cs install metals  # macOS" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "metals" "scala"
