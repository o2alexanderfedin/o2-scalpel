#!/bin/sh
# SessionStart hook for o2-scalpel-elm - verifies LSP server is reachable.
set -eu

if ! command -v elm-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "elm-language-server" >&2
  printf 'Install hint: %s\n' "npm install -g @elm-tooling/elm-language-server" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "elm-language-server" "elm"
