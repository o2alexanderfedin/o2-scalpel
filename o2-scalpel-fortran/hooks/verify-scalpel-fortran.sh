#!/bin/sh
# SessionStart hook for o2-scalpel-fortran - verifies LSP server is reachable.
set -eu

if ! command -v fortls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "fortls" >&2
  printf 'Install hint: %s\n' "pip install fortls" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "fortls" "fortran"
