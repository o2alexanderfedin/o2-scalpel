#!/bin/sh
# SessionStart hook for o2-scalpel-msl - verifies LSP server is reachable.
set -eu

if ! command -v msl-lsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "msl-lsp" >&2
  printf 'Install hint: %s\n' "see plugin README (custom pygls server for mIRC scripting)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "msl-lsp" "msl"
