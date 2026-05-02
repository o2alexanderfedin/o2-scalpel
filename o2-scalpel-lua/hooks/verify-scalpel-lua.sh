#!/bin/sh
# SessionStart hook for o2-scalpel-lua - verifies LSP server is reachable.
set -eu

if ! command -v lua-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "lua-language-server" >&2
  printf 'Install hint: %s\n' "brew install lua-language-server  # macOS; see github.com/LuaLS/lua-language-server" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "lua-language-server" "lua"
