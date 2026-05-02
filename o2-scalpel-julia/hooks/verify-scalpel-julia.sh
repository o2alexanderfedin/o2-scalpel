#!/bin/sh
# SessionStart hook for o2-scalpel-julia - verifies LSP server is reachable.
set -eu

if ! command -v julia >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "julia" >&2
  printf 'Install hint: %s\n' "julia --project=@languageserver -e 'using Pkg; Pkg.add("LanguageServer")'" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "julia" "julia"
