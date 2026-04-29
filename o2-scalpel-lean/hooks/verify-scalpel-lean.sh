#!/bin/sh
# SessionStart hook for o2-scalpel-lean - verifies LSP server is reachable.
set -eu

if ! command -v lean >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "lean" >&2
  printf 'Install hint: %s\n' "see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "lean" "lean"
