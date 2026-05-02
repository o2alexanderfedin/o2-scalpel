#!/bin/sh
# SessionStart hook for o2-scalpel-rego - verifies LSP server is reachable.
set -eu

if ! command -v regal >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "regal" >&2
  printf 'Install hint: %s\n' "see https://github.com/StyraInc/regal (binary download)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "regal" "rego"
