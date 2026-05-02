#!/bin/sh
# SessionStart hook for o2-scalpel-terraform - verifies LSP server is reachable.
set -eu

if ! command -v terraform-ls >/dev/null 2>&1; then
  printf 'scalpel: LSP server "%s" not found on PATH.\n' "terraform-ls" >&2
  printf 'Install hint: %s\n' "brew install hashicorp/tap/terraform-ls  # macOS; or download from releases.hashicorp.com" >&2
  exit 2
fi
printf 'scalpel: %s ready (language=%s)\n' "terraform-ls" "terraform"
