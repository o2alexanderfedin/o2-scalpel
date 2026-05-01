#!/bin/sh
# SessionStart hook for o2-scalpel-perl - verifies LSP server is reachable.
set -eu

if ! command -v perl >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "perl" >&2
  printf 'Install hint: %s\n' "cpanm Perl::LanguageServer  # requires cpanm + a system Perl" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "perl" "perl"
