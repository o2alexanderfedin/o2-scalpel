#!/bin/sh
# SessionStart hook for o2-scalpel-systemverilog - verifies LSP server is reachable.
set -eu

if ! command -v verible-verilog-ls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "verible-verilog-ls" >&2
  printf 'Install hint: %s\n' "brew install verible  # macOS; prebuilt at github.com/chipsalliance/verible/releases" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "verible-verilog-ls" "systemverilog"
