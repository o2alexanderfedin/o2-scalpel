#!/bin/sh
# SessionStart hook for o2-scalpel-ruby - verifies LSP server is reachable.
set -eu

if ! command -v ruby-lsp >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "ruby-lsp" >&2
  printf 'Install hint: %s\n' "gem install --user-install ruby-lsp  # add user gem bindir to PATH" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "ruby-lsp" "ruby"
