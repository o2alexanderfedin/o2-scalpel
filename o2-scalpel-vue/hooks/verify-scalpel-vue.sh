#!/bin/sh
# SessionStart hook for o2-scalpel-vue - verifies LSP server is reachable.
set -eu

if ! command -v vue-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "vue-language-server" >&2
  printf 'Install hint: %s\n' "npm install -g @vue/language-server" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "vue-language-server" "vue"
