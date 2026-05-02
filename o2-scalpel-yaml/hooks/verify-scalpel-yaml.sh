#!/bin/sh
# SessionStart hook for o2-scalpel-yaml - verifies LSP server is reachable.
set -eu

if ! command -v yaml-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "yaml-language-server" >&2
  printf 'Install hint: %s\n' "npm install -g yaml-language-server" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "yaml-language-server" "yaml"
