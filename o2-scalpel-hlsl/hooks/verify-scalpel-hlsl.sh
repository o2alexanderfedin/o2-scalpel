#!/bin/sh
# SessionStart hook for o2-scalpel-hlsl - verifies LSP server is reachable.
set -eu

if ! command -v shader-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "shader-language-server" >&2
  printf 'Install hint: %s\n' "see https://github.com/antaalt/shader-language-server (binary download)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "shader-language-server" "hlsl"
