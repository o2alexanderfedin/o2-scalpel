#!/bin/sh
# SessionStart hook for o2-scalpel-r - verifies LSP server is reachable.
set -eu

if ! command -v R >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "R" >&2
  printf 'Install hint: %s\n' "Rscript -e 'install.packages("languageserver")'" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "R" "r"
