#!/bin/sh
# scalpel-statusline.sh — emits a one-line status segment for Claude Code's
# statusLine when an o2-scalpel engine update is available. Shipped per
# plugin so users can wire any one of them as their statusLine.command.
#
# Usage: add to ~/.claude/settings.json:
#   "statusLine": {
#     "type": "command",
#     "command": "${HOME}/.claude/plugins/marketplaces/o2-scalpel/o2-scalpel-ocaml/hooks/scalpel-statusline.sh"
#   }
#
# Output: empty when up-to-date; "⬆ /o2-scalpel-update" (yellow) when behind.
# The cache file is written by hooks/check-scalpel-update.sh on SessionStart
# and refreshed by /o2-scalpel-update on demand.
set -eu

CACHE="${HOME}/.cache/o2-scalpel/update-check.json"
[ -f "$CACHE" ] || exit 0

if grep -q '"update_available":true' "$CACHE" 2>/dev/null; then
    # ANSI yellow (\033[33m) + reset (\033[0m). Keep ASCII for portability.
    printf '\033[33m\xe2\xac\x86 /o2-scalpel-update\033[0m'
fi
exit 0
