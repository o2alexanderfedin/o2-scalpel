#!/bin/sh
# SessionStart hook for o2-scalpel-ansible - verifies LSP server is reachable.
set -eu

if ! command -v ansible-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "ansible-language-server" >&2
  printf 'Install hint: %s\n' "npm install -g @ansible/ansible-language-server" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "ansible-language-server" "ansible"
