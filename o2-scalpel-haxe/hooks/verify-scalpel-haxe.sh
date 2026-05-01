#!/bin/sh
# SessionStart hook for o2-scalpel-haxe - verifies LSP server is reachable.
set -eu

if ! command -v haxe-language-server >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "haxe-language-server" >&2
  printf 'Install hint: %s\n' "npm install -g haxe-language-server  # plus Haxe + nekovm on PATH" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "haxe-language-server" "haxe"
