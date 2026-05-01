#!/bin/sh
# SessionStart hook for o2-scalpel-powershell - verifies LSP server is reachable.
set -eu

if ! command -v pwsh >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "pwsh" >&2
  printf 'Install hint: %s\n' "Install-Module -Name PowerShellEditorServices  # from a pwsh prompt" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "pwsh" "powershell"
