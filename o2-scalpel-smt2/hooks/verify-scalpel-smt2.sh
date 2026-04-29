#!/bin/sh
# SessionStart hook for o2-scalpel-smt2 - verifies LSP server is reachable.
set -eu

if ! command -v dolmenls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "dolmenls" >&2
  printf 'Install hint: %s\n' "see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "dolmenls" "smt2"
