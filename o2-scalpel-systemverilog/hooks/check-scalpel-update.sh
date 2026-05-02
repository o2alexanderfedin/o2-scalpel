#!/bin/sh
# SessionStart hook for o2-scalpel-systemverilog — checks GitHub for a newer engine commit
# and writes the update indicator into this plugin's data dir. Throttled so
# multiple sessions don't hammer the upstream.
#
# Cache lives under ${CLAUDE_PLUGIN_DATA}/update-cache/ — Claude Code's
# per-plugin scratch dir, automatically removed on plugin uninstall (research
# 2026-05-01: docs/reviews/2026-05-01-scalpel-vs-serena-routing-audit/REPORT.md
# § Phase D + question 7). When CLAUDE_PLUGIN_DATA is unset (e.g. running
# the script outside a plugin context), fall back to a per-user cache so the
# script remains useful for ad-hoc invocations.
set -eu

if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    CACHE_DIR="${CLAUDE_PLUGIN_DATA}/update-cache"
else
    CACHE_DIR="${HOME}/.cache/o2-scalpel"
fi
mkdir -p "$CACHE_DIR"
CACHE="$CACHE_DIR/update-check.json"
INSTALLED="$CACHE_DIR/installed-sha"
THROTTLE_SECONDS=21600  # 6h

# Throttle: skip if we checked recently
NOW=$(date +%s)
if [ -f "$CACHE" ]; then
    LAST=$(grep -o '"checked":[0-9]*' "$CACHE" 2>/dev/null | cut -d: -f2 || echo 0)
    if [ -n "$LAST" ] && [ $((NOW - LAST)) -lt $THROTTLE_SECONDS ]; then
        exit 0
    fi
fi

# Resolve upstream HEAD without authentication (public repo)
UPSTREAM=$(git ls-remote --quiet https://github.com/o2alexanderfedin/o2-scalpel-engine.git HEAD 2>/dev/null | cut -f1 || true)
if [ -z "$UPSTREAM" ]; then
    # Network failure — preserve existing cache, don't write empty
    exit 0
fi

# Read locally-installed SHA from the marker file written by /o2-scalpel-update.
# If absent (first session), seed it with upstream so the user doesn't see a
# false "update available" prompt before they've ever run /o2-scalpel-update.
LOCAL=""
if [ -f "$INSTALLED" ]; then
    LOCAL=$(cat "$INSTALLED" 2>/dev/null || echo "")
fi
if [ -z "$LOCAL" ]; then
    printf '%s\n' "$UPSTREAM" > "$INSTALLED"
    LOCAL="$UPSTREAM"
fi

if [ "$LOCAL" != "$UPSTREAM" ]; then
    AVAILABLE=true
else
    AVAILABLE=false
fi

printf '{"update_available":%s,"installed_sha":"%s","upstream_sha":"%s","checked":%s}\n' "$AVAILABLE" "$LOCAL" "$UPSTREAM" "$NOW" > "$CACHE"
exit 0
