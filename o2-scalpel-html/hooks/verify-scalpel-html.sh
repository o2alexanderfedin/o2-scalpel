#!/bin/sh
# SessionStart hook for o2-scalpel-html - verifies LSP server is reachable.
set -eu

if ! command -v vscode-html-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "vscode-html-language-server" >&2
  printf 'Install hint: %s\n' "see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "vscode-html-language-server" "html"
