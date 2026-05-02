#!/bin/sh
# scalpel-statusline.sh — emits a one-line status segment when an
# o2-scalpel engine update is available. Shipped per plugin as a reference
# implementation; the recommended user setup is the inline statusLine.command
# snippet documented in
# docs/reviews/2026-05-01-scalpel-vs-serena-routing-audit/STATUSLINE.md
# (the inline form survives plugin uninstall).
#
# This script reads the per-plugin cache at ${CLAUDE_PLUGIN_DATA}/update-cache/
# when invoked from a plugin context, otherwise falls back to a glob across
# all installed scalpel-* plugin data dirs so any one plugin's copy of this
# script can serve as the user's statusLine.command.
#
# Output: empty when up-to-date; "⬆ /o2-scalpel-update" (yellow) when behind.
set -eu

CACHE=""
if [ -n "${CLAUDE_PLUGIN_DATA:-}" ] && [ -f "${CLAUDE_PLUGIN_DATA}/update-cache/update-check.json" ]; then
    CACHE="${CLAUDE_PLUGIN_DATA}/update-cache/update-check.json"
else
    # Glob fallback: pick the first plugin-data cache that exists. All
    # installed scalpel-* plugins write the same indicator state, so any
    # one is authoritative. When no scalpel-* plugin is installed, the
    # glob returns nothing and the script exits 0 with no output.
    for F in "$HOME"/.claude/plugins/data/o2-scalpel-*/update-cache/update-check.json; do
        if [ -f "$F" ]; then CACHE="$F"; break; fi
    done
fi

[ -n "$CACHE" ] || exit 0

if grep -q '"update_available":true' "$CACHE" 2>/dev/null; then
    # ANSI yellow + reset. UTF-8 ⬆ (e2 ac 86) for portability across shells.
    printf '\033[33m\xe2\xac\x86 /o2-scalpel-update\033[0m'
fi
exit 0
