#!/bin/sh
# SessionStart hook for o2-scalpel-solidity - verifies LSP server is reachable.
set -eu

if ! command -v nomicfoundation-solidity-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "nomicfoundation-solidity-language-server" >&2
  printf 'Install hint: %s\n' "npm install -g @nomicfoundation/solidity-language-server" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "nomicfoundation-solidity-language-server" "solidity"
