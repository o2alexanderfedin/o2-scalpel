#!/bin/sh
# SessionStart hook for o2-scalpel-typescript - verifies LSP server is reachable.
set -eu

if ! command -v vtsls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "vtsls" >&2
  printf 'Install hint: %s\n' "npm i -g typescript-language-server typescript" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "vtsls" "typescript"
