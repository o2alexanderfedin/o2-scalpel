#!/bin/sh
# SessionStart hook for o2-scalpel-markdown - verifies LSP server is reachable.
set -eu

if ! command -v marksman >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "marksman" >&2
  printf 'Install hint: %s\n' "brew install marksman  # macOS; snap install marksman on Linux" >&2
  exit 1
fi
printf 'scalpel: %s ready (language=%s)\n' "marksman" "markdown"
