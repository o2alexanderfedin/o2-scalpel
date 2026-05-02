#!/bin/sh
# SessionStart hook for o2-scalpel-ocaml — checks GitHub for a newer engine commit
# and writes ~/.cache/o2-scalpel/update-check.json so the status-line script
# can show the ⬆ /o2-scalpel-update indicator. Throttled to one network call
# per 6h across all scalpel-* plugins (the cache is shared by SHA file).
set -eu

CACHE_DIR="${HOME}/.cache/o2-scalpel"
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
