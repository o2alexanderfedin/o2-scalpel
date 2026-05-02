#!/bin/sh
# SessionStart hook for o2-scalpel-groovy - verifies LSP server is reachable.
set -eu

if ! command -v groovy-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "groovy-language-server" >&2
  printf 'Install hint: %s\n' "see https://github.com/GroovyLanguageServer/groovy-language-server (jar download)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "groovy-language-server" "groovy"
