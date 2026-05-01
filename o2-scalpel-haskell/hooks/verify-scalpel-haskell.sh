#!/bin/sh
# SessionStart hook for o2-scalpel-haskell - verifies LSP server is reachable.
set -eu

if ! command -v haskell-language-server-wrapper >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "haskell-language-server-wrapper" >&2
  printf 'Install hint: %s\n' "ghcup install hls --set  # installs haskell-language-server via the Haskell toolchain manager" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "haskell-language-server-wrapper" "haskell"
