#!/bin/sh
# SessionStart hook for o2-scalpel-go - verifies LSP server is reachable.
set -eu

if ! command -v gopls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "gopls" >&2
  printf 'Install hint: %s\n' "go install golang.org/x/tools/gopls@latest" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "gopls" "go"
