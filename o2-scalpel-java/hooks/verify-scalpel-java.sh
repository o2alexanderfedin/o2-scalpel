#!/bin/sh
# SessionStart hook for o2-scalpel-java - verifies LSP server is reachable.
set -eu

if ! command -v jdtls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "jdtls" >&2
  printf 'Install hint: %s\n' "see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "jdtls" "java"
