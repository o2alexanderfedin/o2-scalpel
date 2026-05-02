#!/bin/sh
# SessionStart hook for o2-scalpel-fsharp - verifies LSP server is reachable.
set -eu

if ! command -v fsautocomplete >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "fsautocomplete" >&2
  printf 'Install hint: %s\n' "dotnet tool install --global fsautocomplete" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "fsautocomplete" "fsharp"
