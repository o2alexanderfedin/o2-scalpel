#!/bin/sh
# SessionStart hook for o2-scalpel-json - verifies LSP server is reachable.
set -eu

if ! command -v vscode-json-languageserver >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "vscode-json-languageserver" >&2
  printf 'Install hint: %s\n' "npm install -g vscode-langservers-extracted" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "vscode-json-languageserver" "json"
