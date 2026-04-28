#!/usr/bin/env bash
# v1.2.2 Phase 4 — playground E2E entrypoint
# Used by both `make e2e-playground` (local) and .github/workflows/playground.yml (CI).
#
# Usage:   scripts/e2e_playground.sh [extra pytest args...]
# Stdout:  pytest output
# Stderr:  diagnostic chatter
# Exit:    0 on success; non-zero on any failure
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> e2e_playground: cwd=$REPO_ROOT"
echo "==> e2e_playground: checking prerequisites"

command -v uv          >/dev/null || { echo "ERROR: uv not on PATH"; exit 2; }
command -v cargo       >/dev/null || { echo "WARN: cargo not on PATH — playground tests will skip"; }
command -v rust-analyzer >/dev/null || { echo "WARN: rust-analyzer not on PATH — playground tests will skip"; }

echo "==> e2e_playground: regression-gate the 4 P0 install fixes (SC-1)"
# Per spec § 8 risk 7 — minimal regression gate; matches the SC-1 5-line check.
test -f .claude-plugin/marketplace.json
test -f o2-scalpel-rust/hooks/hooks.json
grep -q "exit 2" o2-scalpel-rust/hooks/verify-scalpel-rust.sh
grep -q "o2alexanderfedin/o2-scalpel-engine" o2-scalpel-rust/.mcp.json
! git grep -q "o2services" -- ':!docs/' ':!*.md' || { echo "ERROR: stale o2services reference found"; exit 2; }
echo "==> e2e_playground: P0 regression gate PASSED"

echo "==> e2e_playground: invoking pytest with O2_SCALPEL_RUN_E2E=1"
cd vendor/serena
O2_SCALPEL_RUN_E2E=1 uv run pytest test/e2e/test_e2e_playground_rust.py -v "$@"

echo "==> e2e_playground: complete"
