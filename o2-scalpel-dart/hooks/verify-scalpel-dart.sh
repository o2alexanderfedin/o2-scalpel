#!/bin/sh
# SessionStart hook for o2-scalpel-dart - verifies LSP server is reachable.
set -eu

if ! command -v dart >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "dart" >&2
  printf 'Install hint: %s\n' "Dart SDK ships dart language-server — install Dart from dart.dev" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "dart" "dart"
