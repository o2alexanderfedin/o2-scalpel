#!/bin/sh
# SessionStart hook for o2-scalpel-matlab - verifies LSP server is reachable.
set -eu

if ! command -v matlab-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "matlab-language-server" >&2
  printf 'Install hint: %s\n' "MathWorks MATLAB R2021b+ ships matlab-language-server — see plugin README" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "matlab-language-server" "matlab"
