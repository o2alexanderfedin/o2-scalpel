#!/bin/sh
# SessionStart hook for o2-scalpel-ada - verifies LSP server is reachable.
set -eu

if ! command -v ada_language_server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "ada_language_server" >&2
  printf 'Install hint: %s\n' "see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "ada_language_server" "ada"
