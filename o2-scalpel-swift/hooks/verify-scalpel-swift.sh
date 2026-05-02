#!/bin/sh
# SessionStart hook for o2-scalpel-swift - verifies LSP server is reachable.
set -eu

if ! command -v sourcekit-lsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "sourcekit-lsp" >&2
  printf 'Install hint: %s\n' "Swift toolchain ships sourcekit-lsp — install Swift from swift.org" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "sourcekit-lsp" "swift"
