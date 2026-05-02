#!/bin/sh
# SessionStart hook for o2-scalpel-luau - verifies LSP server is reachable.
set -eu

if ! command -v luau-lsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "luau-lsp" >&2
  printf 'Install hint: %s\n' "see https://github.com/JohnnyMorganz/luau-lsp (release download)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "luau-lsp" "luau"
