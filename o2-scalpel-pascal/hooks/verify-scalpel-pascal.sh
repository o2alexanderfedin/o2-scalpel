#!/bin/sh
# SessionStart hook for o2-scalpel-pascal - verifies LSP server is reachable.
set -eu

if ! command -v pasls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "pasls" >&2
  printf 'Install hint: %s\n' "see https://github.com/genericptr/pascal-language-server (build from source)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "pasls" "pascal"
