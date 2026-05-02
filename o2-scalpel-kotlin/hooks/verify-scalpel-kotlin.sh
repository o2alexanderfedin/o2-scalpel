#!/bin/sh
# SessionStart hook for o2-scalpel-kotlin - verifies LSP server is reachable.
set -eu

if ! command -v kotlin-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "kotlin-language-server" >&2
  printf 'Install hint: %s\n' "see https://github.com/fwcd/kotlin-language-server (release download)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "kotlin-language-server" "kotlin"
