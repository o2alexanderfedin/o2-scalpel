#!/bin/sh
# SessionStart hook for o2-scalpel-python - verifies LSP server is reachable.
set -eu

if ! command -v pylsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "pylsp" >&2
  printf 'Install hint: %s\n' "pipx install python-lsp-server" >&2
  exit 1
fi
printf 'scalpel: %s ready (language=%s)\n' "pylsp" "python"
