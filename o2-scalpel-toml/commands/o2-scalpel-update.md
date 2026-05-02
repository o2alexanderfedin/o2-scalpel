---
description: Update the o2-scalpel engine to the latest commit on main and refresh the uvx cache (auto-kills stale MCP servers)
allowed-tools: ["Bash(uvx:*)", "Bash(uv:*)", "Bash(git:*)", "Bash(pgrep:*)", "Bash(pkill:*)", "Bash(kill:*)", "Bash(mkdir:*)", "Bash(printf:*)", "Bash(date:*)", "Bash(grep:*)", "Bash(rm:*)", "Bash(ls:*)"]
---

# /o2-scalpel-update

Force-refresh the uvx-cached `o2-scalpel-engine` to the latest commit on `main`, **auto-kill stale `scalpel-*` MCP servers** running from the previous cache snapshot (Claude Code respawns them on the next tool call from the freshly-refreshed cache), and clear the update-available indicator from the status line for **all** enabled scalpel-* plugins (their per-plugin caches are written together so one invocation clears every indicator).

The engine is fetched from `git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git` (no SHA pin → HEAD wins on each `--refresh`). Per-plugin caches live under `${CLAUDE_PLUGIN_DATA}/update-cache/` — Claude Code's per-plugin scratch dir, auto-cleaned on plugin uninstall.

!`set -e
# Tolerate non-matching globs in both bash and zsh (Claude Code may use either).
# Without these, the o2-scalpel-*/update-cache/ glob below aborts the whole
# script with 'no matches found' on first install when the data dirs don't
# exist yet.
shopt -s nullglob 2>/dev/null || true   # bash
setopt NULL_GLOB    2>/dev/null || true   # zsh
ENGINE_URL=git+https://github.com/o2alexanderfedin/o2-scalpel-engine.git

echo "Step 1/4: probing currently-installed engine version"
CURRENT=$(uvx --from "$ENGINE_URL" scalpel --version 2>&1 | tail -1 || true)
echo "  $CURRENT"

echo "Step 2/4: checking upstream HEAD on $ENGINE_URL"
REMOTE_SHA=$(git ls-remote --quiet https://github.com/o2alexanderfedin/o2-scalpel-engine.git HEAD 2>/dev/null | cut -f1)
if [ -z "$REMOTE_SHA" ]; then echo "  ✗ could not reach upstream — check network"; exit 1; fi
echo "  upstream HEAD: ${REMOTE_SHA:0:12}"

echo "Step 3/5: forcing uvx cache refresh"
uvx --refresh --from "$ENGINE_URL" scalpel --version 2>&1 | tail -3

echo "Step 4/5: killing stale scalpel-* MCP servers (Claude Code respawns them on next tool call)"
# Without this step, a running MCP server keeps its loaded-at-startup engine
# code even after --refresh updates the cache — so the next tool call still
# hits the OLD engine, leading to schema-mismatch / 'breaking schema change'
# errors. Killing the uvx-wrapper PIDs (parents of the python interpreter
# children) cascades the SIGTERM to the children. Claude Code will then
# respawn them on the next tool call, this time from the fresh cache.
STALE_PIDS=$(pgrep -f "uvx --from .*o2-scalpel-engine.*serena start-mcp-server --server-name scalpel-" 2>/dev/null || true)
if [ -n "$STALE_PIDS" ]; then
    KILLED=0
    for P in $STALE_PIDS; do
        kill "$P" 2>/dev/null && KILLED=$((KILLED + 1)) || true
    done
    echo "  killed $KILLED uvx wrapper(s); children inherit SIGTERM"
else
    echo "  (no scalpel-* MCP servers currently running)"
fi

echo "Step 5/5: updating per-plugin caches (clears the status-line indicator everywhere)"
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
echo "Refresh complete. Stale MCP servers were killed in step 4 — Claude Code will respawn them"
echo "automatically on the next scalpel-* tool call, this time from the freshly-cached engine."
`
