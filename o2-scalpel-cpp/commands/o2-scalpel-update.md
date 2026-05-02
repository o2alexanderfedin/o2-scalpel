---
description: Update the o2-scalpel engine to the latest commit on main and refresh the uvx cache
allowed-tools: ["Bash(uvx:*)", "Bash(uv:*)", "Bash(git:*)", "Bash(pgrep:*)", "Bash(mkdir:*)", "Bash(printf:*)", "Bash(date:*)", "Bash(grep:*)"]
---

# /o2-scalpel-update

Force-refresh the uvx-cached `o2-scalpel-engine` to the latest commit on `main` and signal that all running `scalpel-*` MCP servers should be restarted to pick up the new code. Also clears the update-available indicator from the status line.

The engine is fetched from `git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git` (no SHA pin → HEAD wins on each `--refresh`).

!`set -e
ENGINE_URL=git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git
CACHE_DIR="${HOME}/.cache/o2-scalpel"; mkdir -p "$CACHE_DIR"

echo "Step 1/4: probing currently-installed engine version"
CURRENT=$(uvx --from "$ENGINE_URL" scalpel --version 2>&1 | tail -1 || true)
echo "  $CURRENT"

echo "Step 2/4: checking upstream HEAD on $ENGINE_URL"
REMOTE_SHA=$(git ls-remote --quiet https://github.com/o2alexanderfedin/o2-scalpel-engine.git HEAD 2>/dev/null | cut -f1)
if [ -z "$REMOTE_SHA" ]; then echo "  ✗ could not reach upstream — check network"; exit 1; fi
echo "  upstream HEAD: ${REMOTE_SHA:0:12}"

echo "Step 3/4: forcing uvx cache refresh"
uvx --refresh --from "$ENGINE_URL" scalpel --version 2>&1 | tail -3

echo "Step 4/4: updating local cache (status-line indicator clears)"
NOW=$(date +%s)
printf '{"update_available":false,"installed_sha":"%s","upstream_sha":"%s","checked":%s}\n' "$REMOTE_SHA" "$REMOTE_SHA" "$NOW" > "$CACHE_DIR/update-check.json"
printf '%s\n' "$REMOTE_SHA" > "$CACHE_DIR/installed-sha"

echo
echo "Refresh complete. Now restart any running scalpel-* MCP servers so they load the new engine code:"
RUNNING=$(pgrep -fla "start-mcp-server.*--server-name scalpel-" 2>/dev/null || true)
if [ -n "$RUNNING" ]; then
    echo "$RUNNING" | head -10
    echo
    echo "Either: (a) restart Claude Code, or (b) kill the parent PIDs above (children + Claude Code will respawn them on next tool call)."
else
    echo "  (no scalpel-* MCP servers currently running — fresh sessions will pick up the new SHA automatically)"
fi
`
