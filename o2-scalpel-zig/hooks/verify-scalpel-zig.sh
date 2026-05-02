#!/bin/sh
# SessionStart hook for o2-scalpel-zig - verifies LSP server is reachable.
set -eu

if ! command -v zls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "zls" >&2
  printf 'Install hint: %s\n' "see https://github.com/zigtools/zls (binary download or zig build)" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "zls" "zig"
