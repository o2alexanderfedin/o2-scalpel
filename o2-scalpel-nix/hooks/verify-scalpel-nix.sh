#!/bin/sh
# SessionStart hook for o2-scalpel-nix - verifies LSP server is reachable.
set -eu

if ! command -v nixd >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "nixd" >&2
  printf 'Install hint: %s\n' "see https://github.com/nix-community/nixd (cargo or nix-env install)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "nixd" "nix"
