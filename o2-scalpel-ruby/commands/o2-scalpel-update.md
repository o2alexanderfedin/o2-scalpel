---
description: Update the o2-scalpel engine to the latest commit on main and refresh the uvx cache
allowed-tools: ["Bash(uvx:*)", "Bash(uv:*)", "Bash(git:*)", "Bash(pgrep:*)", "Bash(mkdir:*)", "Bash(printf:*)", "Bash(date:*)", "Bash(grep:*)", "Bash(rm:*)", "Bash(ls:*)"]
---

# /o2-scalpel-update

Force-refresh the uvx-cached `o2-scalpel-engine` to the latest commit on `main`, signal that all running `scalpel-*` MCP servers should be restarted, and clear the update-available indicator from the status line for **all** enabled scalpel-* plugins (their per-plugin caches are written together so one invocation clears every indicator).

The engine is fetched from `git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git` (no SHA pin → HEAD wins on each `--refresh`). Per-plugin caches live under `${CLAUDE_PLUGIN_DATA}/update-cache/` — Claude Code's per-plugin scratch dir, auto-cleaned on plugin uninstall.

!`set -e
ENGINE_URL=git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git

echo "Step 1/4: probing currently-installed engine version"
CURRENT=$(uvx --from "$ENGINE_URL" scalpel --version 2>&1 | tail -1 || true)
echo "  $CURRENT"

echo "Step 2/4: checking upstream HEAD on $ENGINE_URL"
REMOTE_SHA=$(git ls-remote --quiet https://github.com/o2alexanderfedin/o2-scalpel-engine.git HEAD 2>/dev/null | cut -f1)
if [ -z "$REMOTE_SHA" ]; then echo "  ✗ could not reach upstream — check network"; exit 1; fi
echo "  upstream HEAD: ${REMOTE_SHA:0:12}"

echo "Step 3/4: forcing uvx cache refresh"
uvx --refresh --from "$ENGINE_URL" scalpel --version 2>&1 | tail -3

echo "Step 4/4: updating per-plugin caches (clears the status-line indicator everywhere)"
NOW=$(date +%s)
WROTE=0
# Glob across all installed scalpel-* plugin data dirs so a single
# /o2-scalpel-update clears the indicator for every enabled plugin at once.
for D in "$HOME"/.claude/plugins/data/o2-scalpel-*/update-cache/; do
    [ -d "$D" ] || continue
    printf '{"update_available":false,"installed_sha":"%s","upstream_sha":"%s","checked":%s}\n' "$REMOTE_SHA" "$REMOTE_SHA" "$NOW" > "$D/update-check.json"
    printf '%s\n' "$REMOTE_SHA" > "$D/installed-sha"
    WROTE=$((WROTE + 1))
done
# Also cover the slash command's own plugin-data dir (set when the body runs).
if [ -n "${CLAUDE_PLUGIN_DATA:-}" ]; then
    OWN_DIR="$CLAUDE_PLUGIN_DATA/update-cache"
    mkdir -p "$OWN_DIR"
    printf '{"update_available":false,"installed_sha":"%s","upstream_sha":"%s","checked":%s}\n' "$REMOTE_SHA" "$REMOTE_SHA" "$NOW" > "$OWN_DIR/update-check.json"
    printf '%s\n' "$REMOTE_SHA" > "$OWN_DIR/installed-sha"
fi
# One-time migration cleanup: pre-v1.12 wrote to ~/.cache/o2-scalpel/ which
# isn't auto-cleaned on uninstall. Remove it here so upgrading users don't
# leak the legacy cache forever.
rm -rf "$HOME/.cache/o2-scalpel" 2>/dev/null || true
echo "  cleared $WROTE plugin cache(s) + legacy ~/.cache/o2-scalpel/ if present"

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
